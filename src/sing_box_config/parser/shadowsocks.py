# https://github.com/shadowsocks/shadowsocks-org/wiki/SIP002-URI-Scheme
# https://sing-box.sagernet.org/configuration/outbound/shadowsocks/

import logging
import urllib.parse
from typing import Any, Optional

from chaos_utils.text_utils import b64decode

from sing_box_config.parser.base import SubscriptionParser, URIParser

logger = logging.getLogger(__name__)


# https://shadowsocks.org/doc/sip003.html
supported_plugins = ["obfs-local", "v2ray-plugin"]


class ShadowsocksURIParser(URIParser):
    def parse(self, uri: str) -> Optional[dict[str, Any]]:
        """
        Decodes a Shadowsocks SIP002 URI into a sing-box shadowsocks outbound configuration.

        Args:
            uri: The Shadowsocks SIP002 URI string.

        Returns:
            A dictionary representing the sing-box shadowsocks outbound configuration.
        """
        try:
            parsed_uri = urllib.parse.urlparse(uri)
        except Exception:
            logger.warning("Failed to parse SIP002 URI: %s", uri)
            return None

        if parsed_uri.scheme != "ss":
            logger.warning("Invalid scheme. Expected 'ss'")
            return None

        try:
            userinfo_encoded = parsed_uri.netloc.split("@")[0]
            userinfo_decoded = b64decode(userinfo_encoded)
            method, password = userinfo_decoded.split(":", 1)
        except Exception:
            logger.warning("Invalid userinfo in %s", uri)
            return None

        try:
            hostname_port = parsed_uri.netloc.split("@")[1]
            hostname, port_str = hostname_port.split(":")
            port = int(port_str)
        except (IndexError, ValueError):
            logger.warning("Invalid host/port in %s", uri)
            return None

        outbound_config = {
            "type": "shadowsocks",
            "tag": urllib.parse.unquote(parsed_uri.fragment),
            "server": hostname,
            "server_port": port,
            "method": method,
            "password": password,
            "plugin": "",
            "plugin_opts": "",
        }

        if not parsed_uri.query:
            return outbound_config

        query_params = urllib.parse.parse_qs(parsed_uri.query)
        if "plugin" in query_params:
            plugin_value = query_params["plugin"][0]
            plugin_parts = plugin_value.split(";", 1)

            # https://github.com/tindy2013/subconverter/issues/671
            if plugin_parts[0] == "simple-obfs":
                plugin_parts[0] = "obfs-local"

            # Only obfs-local and v2ray-plugin are supported.
            # https://sing-box.sagernet.org/configuration/outbound/shadowsocks/#plugin
            if plugin_parts[0] not in supported_plugins:
                logger.warning("sing-box doesn't support plugin %s", plugin_parts[0])
                return None

            outbound_config["plugin"] = plugin_parts[0]
            if len(plugin_parts) > 1:
                outbound_config["plugin_opts"] = plugin_parts[1]

        return outbound_config


class SIP002SubscriptionParser(SubscriptionParser):
    def parse(self, content: str) -> list[dict[str, Any]]:
        proxies = []
        try:
            decoded = b64decode(content)
        except Exception as err:
            logger.warning("Failed to decode subscription: %s", err)
            return []

        proxies_lines = decoded.splitlines()
        parser = ShadowsocksURIParser()

        for line in proxies_lines:
            if not line.strip():
                continue
            proxy = parser.parse(line)
            if proxy:
                proxies.append(proxy)

        return proxies
