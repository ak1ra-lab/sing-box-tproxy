import copy
import logging
import re
from pathlib import Path
from typing import Any

import httpx
import tenacity
from chaos_utils.text_utils import b64decode, save_json

from sing_box_config.parser.shadowsocks import decode_sip002_to_singbox

logger = logging.getLogger(__name__)

SUPPORTED_TYPES = ["SIP002"]


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
    if subscription["type"].upper() not in SUPPORTED_TYPES:
        logger.warning(
            "Unsupported subscription type: %s (supported: %s)",
            subscription["type"],
            ", ".join(SUPPORTED_TYPES),
        )
        return proxies

    try:
        resp = fetch_url_with_retries(subscription["url"], follow_redirects=True)
    except httpx.HTTPError as err:
        logger.error("Failed to fetch subscription %s: %s", name, err)
        return proxies

    logger.info("resp.text = %s", resp.text[:100])

    exclude = subscription.pop("exclude", [])
    if subscription["type"].upper() == "SIP002":
        try:
            proxies_lines = b64decode(resp.text).splitlines()
        except UnicodeDecodeError as err:
            logger.warning("Failed to decode subscription %s: %s", name, err)
            proxies_lines = []
        logger.debug("url = %s, proxies_lines = %s", subscription["url"], proxies_lines)

        for line in proxies_lines:
            proxy = decode_sip002_to_singbox(line, name + " - ")
            if not proxy:
                continue
            if any(re.search(p, proxy["tag"], re.IGNORECASE) for p in exclude):
                logger.debug("Excluding proxy: %s", proxy["tag"])
                continue
            proxies.append(proxy)

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

        exclude = outbound.pop("exclude", [])
        filter_patterns = outbound.pop("filter", [])

        for proxy in proxies:
            if any(re.search(p, proxy["tag"], re.IGNORECASE) for p in exclude):
                continue

            if any(re.search(p, proxy["tag"], re.IGNORECASE) for p in filter_patterns):
                outbound["outbounds"].append(proxy["tag"])


def remove_invalid_outbounds(outbounds: list[dict[str, Any]]) -> None:
    """
    Remove outbound groups that have no valid proxies.

    Args:
        outbounds: List of outbound configurations (modified in-place)
    """
    invalid_tags = set()
    logger.debug("outbounds = %s", outbounds)

    # Use copy to avoid modifying list during iteration
    for outbound in copy.deepcopy(outbounds):
        if "outbounds" not in outbound.keys():
            continue
        if not isinstance(outbound["outbounds"], list):
            continue
        if len(outbound["outbounds"]) == 0:
            logger.info("removing outbound = %s", outbound)
            outbounds.remove(outbound)
            invalid_tags.add(outbound["tag"])

    logger.info("invalid_tags = %s", invalid_tags)
    if not invalid_tags:
        return

    # Remove invalid tags from all outbounds' "outbounds" lists
    for outbound in outbounds:
        if "outbounds" not in outbound.keys():
            continue
        if not isinstance(outbound["outbounds"], list):
            continue

        outbound["outbounds"] = [
            tag for tag in outbound["outbounds"] if tag not in invalid_tags
        ]


def save_config_from_subscriptions(
    base_config: dict[str, Any],
    subscriptions_config: dict[str, Any],
    output_path: Path,
) -> None:
    """
    Generate final sing-box configuration by merging base config with subscription proxies.

    Args:
        base_config: Base configuration dict
        subscriptions_config: Subscriptions configuration dict
        output_path: Path to save the generated config
    """
    proxies = []
    for name, subscription in subscriptions_config.items():
        proxies += get_proxies_from_subscriptions(name, subscription)

    if not proxies:
        logger.warning("No proxies found from subscriptions")

    outbounds = base_config.pop("outbounds")

    # Modify outbounds directly
    filter_valid_proxies(outbounds, proxies)
    remove_invalid_outbounds(outbounds)

    outbounds += proxies
    base_config["outbounds"] = outbounds

    if not output_path.parent.exists():
        output_path.parent.mkdir(parents=True, exist_ok=True)

    save_json(output_path, base_config)
    logger.info("Configuration saved to %s", output_path)
