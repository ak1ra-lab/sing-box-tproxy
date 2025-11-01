import copy
import logging
import re
from pathlib import Path

import httpx
import tenacity
from chaos_utils.text_utils import b64decode, save_json

from sing_box_config.parser.shadowsocks import decode_sip002_to_singbox

logger = logging.getLogger(__name__)

supported_types = ["SIP002"]


@tenacity.retry(
    stop=tenacity.stop_after_attempt(5),
    wait=tenacity.wait_exponential_jitter(initial=1, max=30),
    before_sleep=tenacity.before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
def fetch_url_with_retries(url: str, **kwargs) -> httpx.Response:
    resp = httpx.get(url, **kwargs)
    resp.raise_for_status()
    return resp


def get_proxies_from_subscriptions(name: str, subscription: dict) -> list:
    proxies = []
    if not subscription.get("enabled", True):
        return proxies
    if subscription["type"].upper() not in supported_types:
        return proxies

    resp = fetch_url_with_retries(subscription["url"], follow_redirects=True)

    logger.info("resp.text = %s", resp.text[:100])
    if not resp:
        return proxies

    exclude = subscription.pop("exclude", [])
    if subscription["type"].upper() == "SIP002":
        try:
            proxies_lines = b64decode(resp.text).splitlines()
        except UnicodeDecodeError as err:
            logger.warning(err)
            proxies_lines = []
        logger.debug("url = %s, proxies_lines = %s", subscription["url"], proxies_lines)

        for line in proxies_lines:
            proxy = decode_sip002_to_singbox(line, name + " - ")
            if not proxy:
                continue
            if any(re.search(p, proxy["tag"], re.IGNORECASE) for p in exclude):
                continue
            proxies.append(proxy)

    return proxies


def filter_valid_proxies(outbounds: list, proxies: list) -> None:
    for outbound in outbounds:
        if all(k not in outbound.keys() for k in ["exclude", "filter"]):
            continue

        exclude = outbound.pop("exclude", [])
        filter = outbound.pop("filter", [])

        for proxy in proxies:
            if any(re.search(p, proxy["tag"], re.IGNORECASE) for p in exclude):
                continue

            if any(re.search(p, proxy["tag"], re.IGNORECASE) for p in filter):
                outbound["outbounds"].append(proxy["tag"])


def remove_invalid_outbounds(outbounds: list) -> None:
    invalid_tags = set()
    logger.debug("outbounds = %s", outbounds)
    # 遍历 lists 时修改 lists 的长度 (如移除某些成员)，可能会导致 IndexError 或者跳过某些元素
    # 这里需要使用 copy.deepcopy() 来避免这个问题
    for outbound in copy.deepcopy(outbounds):
        if "outbounds" not in outbound.keys():
            continue
        if not isinstance(outbound["outbounds"], list):
            continue
        if len(outbound["outbounds"]) == 0:
            logger.info("removing outbound = %s", outbound)
            # 这里移除的是 copy.deepcopy() 之前的 outbounds
            outbounds.remove(outbound)
            invalid_tags.add(outbound["tag"])

    logger.info("invalid_tags = %s", invalid_tags)
    if not invalid_tags:
        return

    # Remove invalid tags from all outbounds' "outbounds" lists
    logger.debug("outbounds = %s", outbounds)
    for outbound in outbounds:
        if "outbounds" not in outbound.keys():
            continue
        if not isinstance(outbound["outbounds"], list):
            continue
        outbound["outbounds"] = [
            tag for tag in outbound["outbounds"] if tag not in invalid_tags
        ]


def save_config_from_subscriptions(
    base_config: dict, subscriptions_config: dict, output_path: Path
) -> None:
    proxies = []
    subscriptions = subscriptions_config.pop("subscriptions")
    for name, subscription in subscriptions.items():
        proxies += get_proxies_from_subscriptions(name, subscription)

    outbounds = subscriptions_config.pop("outbounds")

    # modify outbounds directly
    filter_valid_proxies(outbounds, proxies)
    remove_invalid_outbounds(outbounds)

    outbounds += proxies
    base_config["outbounds"] += outbounds

    if not output_path.parent.exists():
        output_path.parent.mkdir(parents=True, exist_ok=True)

    save_json(output_path, base_config)
