import datetime
import logging
import re
import shutil
from pathlib import Path
from typing import Any

from chaos_utils.text_utils import read_json, save_json

from sing_box_config.models import BaseConfig, SelfhostDetourEntry, SubscriptionConfig
from sing_box_config.parser import SUPPORTED_FORMATS, get_parser
from sing_box_config.subscription import get_source

logger = logging.getLogger(__name__)


def patch_intra_subscription_detours(proxies: list[dict[str, Any]], name: str) -> None:
    """
    Update ``detour`` fields that reference other proxies within this subscription.

    This is only meaningful for sing-box format subscriptions, where individual
    proxy nodes may chain through another node in the same subscription via the
    ``detour`` field (e.g. a relay node pointing at an entry node).  Must be
    called *before* ``apply_name_prefix`` so comparisons still work against the
    original tags.

    Args:
        proxies: Proxy list as returned by the parser (modified in-place).
        name: Subscription name — the same prefix that will be applied to tags.
    """
    original_tags = {p["tag"] for p in proxies}
    for proxy in proxies:
        if "detour" in proxy and proxy["detour"] in original_tags:
            proxy["detour"] = f"{name} - {proxy['detour']}"


def apply_name_prefix(proxies: list[dict[str, Any]], name: str) -> None:
    """
    Prepend ``"{name} - "`` to the ``tag`` of every proxy.

    Mutates the list in-place; group-type filtering is the responsibility of each
    ``SubscriptionParser``.  For sing-box subscriptions that may use intra-
    subscription ``detour`` references, call ``patch_intra_subscription_detours``
    first.

    Args:
        proxies: Proxy list to rename (modified in-place).
        name: Subscription name used as the tag prefix.
    """
    for proxy in proxies:
        proxy["tag"] = f"{name} - {proxy['tag']}"


def get_proxies_from_subscriptions(
    name: str, subscription: SubscriptionConfig
) -> list[dict[str, Any]]:
    """
    Parse subscription and extract proxy configurations.

    Args:
        name: Subscription name for proxy tag prefix
        subscription: Typed subscription configuration model

    Returns:
        List of proxy configuration dicts
    """
    if not subscription.enabled:
        return []

    source = get_source(subscription.type)
    if source is None:
        logger.warning("Unsupported subscription type: %s", subscription.type)
        return []

    try:
        contents = source.fetch(subscription)
    except Exception as e:
        logger.error("Failed to fetch subscription %s: %s", name, e)
        return []

    parser = get_parser(subscription.sub_format)
    if parser is None:
        logger.warning(
            "Unsupported subscription format: %s (supported: %s)",
            subscription.sub_format,
            ", ".join(SUPPORTED_FORMATS.keys()),
        )
        return []

    proxies = []
    for content in contents:
        proxies.extend(parser.parse(content))
    if subscription.sub_format == "sing-box":
        patch_intra_subscription_detours(proxies, name)
    apply_name_prefix(proxies, name)

    if not subscription.exclude:
        return proxies

    return [
        p
        for p in proxies
        if not re.search(subscription.exclude, p["tag"], re.IGNORECASE)
    ]


def build_selfhost_detours(
    selfhost_proxies: list[dict[str, Any]],
    selfhost_detour: list[SelfhostDetourEntry],
) -> list[dict[str, Any]]:
    """
    Duplicate self-hosted proxies with detour chaining.

    For each selfhost proxy, creates a copy whose tag gets a ``-detour`` suffix
    and whose ``detour`` field is set to the upstream selector for that region.
    The region is determined by matching the proxy tag against each ``tag_filter``
    regex in *selfhost_detour*.

    Args:
        selfhost_proxies: Self-hosted proxy configs to duplicate.
        selfhost_detour: List of :class:`SelfhostDetourEntry` region-to-detour mappings.
            Comes from ``_selfhost_detour`` embedded in base.json by Ansible.

    Returns:
        List of new detour proxy copies (caller should extend the main proxy list).
    """
    detour_proxies = []
    for proxy in selfhost_proxies:
        for item in selfhost_detour:
            if not re.search(item.tag_filter, proxy["tag"], re.IGNORECASE):
                continue
            detour_proxy = proxy.copy()
            detour_proxy["tag"] = f"{proxy['tag']}-detour"
            detour_proxy["detour"] = item.detour
            detour_proxies.append(detour_proxy)
            break
    return detour_proxies


def populate_outbound_groups(
    outbounds: list[dict[str, Any]], proxies: list[dict[str, Any]]
) -> None:
    """
    Populate outbound groups with matching proxies based on filter/exclude patterns.

    Both ``filter`` and ``exclude`` are single regex strings.

    Args:
        outbounds: List of outbound group configurations (modified in-place)
        proxies: List of available proxy configurations
    """
    for outbound in outbounds:
        if not isinstance(outbound.get("outbounds"), list):
            continue
        if all(key not in outbound for key in ["exclude", "filter"]):
            continue

        exclude_pattern: str | None = outbound.pop("exclude", None)
        filter_pattern: str | None = outbound.pop("filter", None)

        for proxy in proxies:
            if exclude_pattern and re.search(
                exclude_pattern, proxy["tag"], re.IGNORECASE
            ):
                continue
            if filter_pattern and re.search(
                filter_pattern, proxy["tag"], re.IGNORECASE
            ):
                outbound["outbounds"].append(proxy["tag"])


def remove_invalid_outbounds(outbounds: list[dict[str, Any]]) -> None:
    """
    Remove outbound groups that have no valid proxies.

    Args:
        outbounds: List of outbound configurations (modified in-place)
    """
    while True:
        invalid_tags = set()
        for proxy_group in outbounds[:]:
            if not isinstance(proxy_group.get("outbounds"), list):
                continue
            if len(proxy_group["outbounds"]) == 0:
                logger.info("removing outbound = %s", proxy_group)
                outbounds.remove(proxy_group)
                invalid_tags.add(proxy_group["tag"])

        logger.info("invalid_tags = %s", invalid_tags)
        if not invalid_tags:
            break

        for proxy_group in outbounds:
            if not isinstance(proxy_group.get("outbounds"), list):
                continue
            proxy_group["outbounds"] = [
                tag for tag in proxy_group["outbounds"] if tag not in invalid_tags
            ]


def load_proxies(
    subscriptions_config: dict[str, SubscriptionConfig],
    proxies_path: Path,
    use_cache: bool,
) -> list[dict[str, Any]]:
    if use_cache and proxies_path and proxies_path.exists():
        try:
            proxies = read_json(proxies_path)
            if isinstance(proxies, list):
                logger.info(
                    "Loaded %d proxies from cache: %s", len(proxies), proxies_path
                )
                return proxies
            logger.warning("Cached proxies file content is not a list, ignoring cache")
        except Exception as e:
            logger.warning("Failed to load proxies from cache: %s", e)

    proxies = [
        proxy
        for name, subscription in subscriptions_config.items()
        for proxy in get_proxies_from_subscriptions(
            name=name, subscription=subscription
        )
    ]

    if proxies_path:
        proxies_path.parent.mkdir(parents=True, exist_ok=True)
        save_json(proxies_path, proxies)  # type: ignore
        logger.info("Saved %d proxies to cache: %s", len(proxies), proxies_path)

    return proxies


def save_config_from_subscriptions(
    base_config: BaseConfig,
    subscriptions_config: dict[str, SubscriptionConfig],
    output_path: Path,
    proxies_path: Path,
    use_cache: bool = False,
    backup_output: bool = True,
) -> None:
    """
    Generate final sing-box configuration by merging base config with subscription proxies.

    Args:
        base_config: Validated base configuration model
        subscriptions_config: Validated subscriptions configuration
        output_path: Path to save the generated config
        proxies_path: Path to load/save proxies cache
        use_cache: Whether to use cached proxies if available
        backup_output: Whether to backup existing output file before overwriting
    """
    proxies = load_proxies(subscriptions_config, proxies_path, use_cache)
    if not proxies:
        logger.warning("No proxies found from subscriptions")

    # Read internal metadata fields from the typed model.
    selfhost_tag_pattern = base_config.selfhost_tag_pattern
    selfhost_detour = base_config.selfhost_detour
    # Take a mutable copy of outbounds to avoid mutating the model.
    outbounds: list[dict[str, Any]] = list(base_config.outbounds)

    if selfhost_detour:
        selfhost_re = re.compile(selfhost_tag_pattern, re.IGNORECASE)
        selfhost_proxies = [p for p in proxies if selfhost_re.search(p["tag"])]
        if not selfhost_proxies:
            logger.warning(
                "sing_box_selfhost_detour is configured but no selfhost proxies found "
                "(tag pattern: %r); selfhost groups will be empty and removed",
                selfhost_tag_pattern,
            )
        logger.debug(
            "Processing selfhost_detour for selfhost_proxies: %s",
            [p["tag"] for p in selfhost_proxies],
        )
        proxies.extend(build_selfhost_detours(selfhost_proxies, selfhost_detour))

    populate_outbound_groups(outbounds, proxies)
    remove_invalid_outbounds(outbounds)
    outbounds += proxies

    # Build output dict: exclude internal metadata fields, inject final outbounds.
    config_dict = base_config.model_dump(
        by_alias=False,
        exclude={"selfhost_tag_pattern", "selfhost_detour", "outbounds"},
    )
    config_dict["outbounds"] = outbounds

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if backup_output and output_path.exists():
        now = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_suffix = f".{now}{output_path.suffix}"
        shutil.copy2(output_path, output_path.with_suffix(backup_suffix))
        logger.info(
            "Saved %s to %s", output_path, output_path.with_suffix(backup_suffix)
        )

    save_json(output_path, config_dict, sort_keys=False)
    logger.info("Configuration saved to %s", output_path)
