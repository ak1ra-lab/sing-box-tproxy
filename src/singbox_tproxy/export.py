import logging
import re
from pathlib import Path

import httpx

from singbox_tproxy.parser.shadowsocks import decode_sip002_to_singbox
from singbox_tproxy.utils import b64decode, save_json

logger = logging.getLogger(__name__)


def save_config_from_subscriptions(
    base_config: dict, subscriptions_config: dict, output: Path
) -> None:
    subscriptions = subscriptions_config.pop("subscriptions")
    outbounds = subscriptions_config.pop("outbounds")

    proxies = []
    for name, subscription in subscriptions.items():
        tag_prefix = name + " - "
        if subscription["type"] == "SIP002":
            proxies_raw = httpx.get(subscription["url"])
            proxies_lines = b64decode(proxies_raw.text).splitlines()
            for line in proxies_lines:
                proxy = decode_sip002_to_singbox(line, tag_prefix)
                if proxy:
                    proxies.append(proxy)

    if logger.level == logging.DEBUG:
        save_json(output.with_suffix(".proxies.json"), proxies)

    # filter outbounds
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

    outbounds += proxies
    if logger.level == logging.DEBUG:
        save_json(output.with_suffix(".outbounds.json"), outbounds)

    base_config["outbounds"] += outbounds
    save_json(output, base_config)
