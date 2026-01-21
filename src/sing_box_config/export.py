import copy
import logging
import re
from pathlib import Path
from typing import Any

import httpx
import tenacity
from chaos_utils.text_utils import read_json, save_json

from sing_box_config.parser import SUPPORTED_FORMATS, get_parser

logger = logging.getLogger(__name__)


@tenacity.retry(
    stop=tenacity.stop_after_attempt(5),
    wait=tenacity.wait_exponential_jitter(initial=1, max=30),
    before_sleep=tenacity.before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
def fetch_url_with_retries(url: str, **kwargs: Any) -> httpx.Response:
    """
    Fetch URL with exponential backoff retry strategy.

    Args:
        url: The URL to fetch
        **kwargs: Additional arguments to pass to httpx.get()

    Returns:
        httpx.Response object

    Raises:
        httpx.HTTPError: If all retry attempts fail
    """
    resp = httpx.get(url, **kwargs)
    resp.raise_for_status()
    return resp


def get_proxies_from_subscriptions(
    name: str, subscription: dict[str, Any]
) -> list[dict[str, Any]]:
    """
    Parse subscription URL and extract proxy configurations.

    Args:
        name: Subscription name for proxy tag prefix
        subscription: Subscription configuration dict

    Returns:
        List of proxy configuration dicts
    """
    proxies = []
    if not subscription.get("enabled", True):
        return proxies

    sub_type = subscription.get("type", "").lower()
    # Default format is sing-box if not specified
    sub_format = subscription.get("format", "sing-box").lower()

    content = ""

    if sub_type not in ["inline", "local", "remote"]:
        logger.warning("Unsupported subscription type: %s", sub_type)
        return proxies

    if sub_type == "inline":
        if sub_format == "sing-box" and "outbounds" in subscription:
            proxies = subscription["outbounds"]
        elif "content" in subscription:
            content = subscription["content"]
        else:
            logger.warning(
                "Inline subscription %s missing 'outbounds' or 'content'", name
            )
            return []

    elif sub_type == "local":
        path = Path(subscription["path"])
        if not path.exists():
            logger.error("Local subscription file not found: %s", path)
            return []
        try:
            content = path.read_text(encoding="utf-8")
        except Exception as e:
            logger.error("Failed to read local subscription %s: %s", name, e)
            return []

    elif sub_type == "remote":
        url = subscription.get("url")
        if not url:
            logger.error("Remote subscription %s missing 'url'", name)
            return []
        try:
            resp = fetch_url_with_retries(url, follow_redirects=True)
            content = resp.text
            logger.info("resp.text = %s", resp.text[:100])
        except httpx.HTTPError as err:
            logger.error("Failed to fetch subscription %s: %s", name, err)
            return []

    if not proxies and content:
        parser = get_parser(sub_format)
        if parser:
            proxies = parser.parse(content)
            # Prefix tags for non-native formats or if requested?
            # Replicating old behavior: non sing-box sub_format gets prefixed.
            if sub_format != "sing-box":
                for proxy in proxies:
                    proxy["tag"] = f"{name} - {proxy['tag']}"
        else:
            logger.warning(
                "Unsupported subscription format: %s (supported: %s)",
                sub_format,
                ", ".join(SUPPORTED_FORMATS.keys()),
            )
            return []

    # Filter proxies
    exclude_patterns = subscription.get("exclude", [])
    if exclude_patterns:
        filtered_proxies = []
        for proxy in proxies:
            if any(re.search(p, proxy["tag"], re.IGNORECASE) for p in exclude_patterns):
                logger.debug("Excluding proxy: %s", proxy["tag"])
                continue
            filtered_proxies.append(proxy)
        proxies = filtered_proxies

    return proxies


def filter_valid_proxies(
    outbounds: list[dict[str, Any]], proxies: list[dict[str, Any]]
) -> None:
    """
    Filter proxies and populate outbound groups based on filter/exclude patterns.

    Args:
        outbounds: List of outbound group configurations (modified in-place)
        proxies: List of available proxy configurations
    """
    for outbound in outbounds:
        if all(k not in outbound.keys() for k in ["exclude", "filter"]):
            continue

        exclude_patterns = outbound.pop("exclude", [])
        filter_patterns = outbound.pop("filter", [])

        for proxy in proxies:
            if any(re.search(p, proxy["tag"], re.IGNORECASE) for p in exclude_patterns):
                continue

            if any(re.search(p, proxy["tag"], re.IGNORECASE) for p in filter_patterns):
                outbound["outbounds"].append(proxy["tag"])


def remove_invalid_outbounds(outbounds: list[dict[str, Any]]) -> None:
    """
    Remove outbound groups that have no valid proxies.

    Args:
        outbounds: List of outbound configurations (modified in-place)
    """
    while True:
        invalid_tags = set()
        # Use copy to avoid modifying list during iteration
        for proxy_group in copy.deepcopy(outbounds):
            # Keep real proxy server, only processing proxy_group
            if "outbounds" not in proxy_group.keys():
                continue
            if not isinstance(proxy_group["outbounds"], list):
                continue

            # Remove proxy_group without "outbounds", also mark tag as invalid
            if len(proxy_group["outbounds"]) == 0:
                logger.info("removing outbound = %s", proxy_group)
                outbounds.remove(proxy_group)
                invalid_tags.add(proxy_group["tag"])

        logger.info("invalid_tags = %s", invalid_tags)
        if not invalid_tags:
            break

        # Remove invalid tags from all outbounds' "outbounds" lists
        for proxy_group in outbounds:
            # Keep real proxy server, only processing proxy_group
            if "outbounds" not in proxy_group.keys():
                continue
            if not isinstance(proxy_group["outbounds"], list):
                continue

            proxy_group["outbounds"] = [
                tag for tag in proxy_group["outbounds"] if tag not in invalid_tags
            ]


def save_config_from_subscriptions(
    base_config: dict[str, Any],
    subscriptions_config: dict[str, Any],
    output_path: Path,
    proxies_path: Path,
    use_cache: bool = False,
) -> None:
    """
    Generate final sing-box configuration by merging base config with subscription proxies.

    Args:
        base_config: Base configuration dict
        subscriptions_config: Subscriptions configuration dict
        output_path: Path to save the generated config
        proxies_path: Path to load/save proxies cache
        use_cache: Whether to use cached proxies if available
    """
    proxies = []

    if use_cache and proxies_path and proxies_path.exists():
        try:
            proxies = read_json(proxies_path)
            if not isinstance(proxies, list):
                logger.warning(
                    "Cached proxies file content is not a list, ignoring cache"
                )
                proxies = []
            else:
                logger.info(
                    "Loaded %d proxies from cache: %s", len(proxies), proxies_path
                )
        except Exception as e:
            logger.warning("Failed to load proxies from cache: %s", e)

    if not proxies:
        for name, subscription in subscriptions_config.items():
            proxies += get_proxies_from_subscriptions(name, subscription)

        if proxies_path:
            proxies_path.parent.mkdir(parents=True, exist_ok=True)
            save_json(proxies_path, proxies)
            logger.info("Saved %d proxies to cache: %s", len(proxies), proxies_path)

    if not proxies:
        logger.warning("No proxies found from subscriptions")

    outbounds = base_config.pop("outbounds")

    # Modify outbounds directly
    filter_valid_proxies(outbounds, proxies)
    remove_invalid_outbounds(outbounds)

    outbounds += proxies
    base_config["outbounds"] = outbounds

    output_path.parent.mkdir(parents=True, exist_ok=True)

    save_json(output_path, base_config, sort_keys=False)
    logger.info("Configuration saved to %s", output_path)
