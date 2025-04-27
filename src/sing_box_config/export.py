import argparse
import logging
import re
from pathlib import Path

import httpx

from sing_box_config.parser.shadowsocks import decode_sip002_to_singbox
from sing_box_config.utils import b64decode, read_json, save_json

logger = logging.getLogger(__name__)

supported_types = ["SIP002"]


def get_proxies_from_subscriptions(name: str, subscription: dict) -> list:
    proxies = []
    if subscription["type"].upper() not in supported_types:
        return proxies

    exclude = subscription.pop("exclude", [])
    if subscription["type"].upper() == "SIP002":
        resp = httpx.get(subscription["url"], timeout=120)
        try:
            proxies_lines = b64decode(resp.text).splitlines()
        except UnicodeDecodeError as err:
            logger.warning(err)
            logger.warning("resp.text = %s", resp.text)
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


def filter_outbounds_from_proxies(outbounds: list, proxies: list) -> None:
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


def save_config_from_subscriptions(args: argparse.Namespace) -> None:
    base_config = read_json(Path(args.base))
    subscriptions_config = read_json(Path(args.subscriptions))
    output = Path(args.output)

    proxies = []
    subscriptions = subscriptions_config.pop("subscriptions")
    for name, subscription in subscriptions.items():
        proxies += get_proxies_from_subscriptions(name, subscription)

    outbounds = subscriptions_config.pop("outbounds")
    filter_outbounds_from_proxies(outbounds, proxies)

    outbounds += proxies
    base_config["outbounds"] += outbounds

    if not output.parent.exists():
        output.parent.mkdir(parents=True)

    save_json(output, base_config)
