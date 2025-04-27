# https://github.com/shadowsocks/shadowsocks-org/wiki/SIP002-URI-Scheme
# https://sing-box.sagernet.org/configuration/outbound/shadowsocks/

import logging
import urllib.parse

from sing_box_config.utils import b64decode

logger = logging.getLogger(__name__)


# https://shadowsocks.org/doc/sip003.html
supported_plugins = ["obfs-local", "v2ray-plugin"]


def decode_sip002_to_singbox(uri: str, tag_prefix: str = "") -> dict:
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
        logger.warning("Failed to parse SIP002 URI: %s", parsed_uri)
        return {}

    if parsed_uri.scheme != "ss":
        logger.warning("Invalid scheme. Expected 'ss'")
        return {}

    userinfo_encoded = parsed_uri.netloc.split("@")[0]
    try:
        userinfo_decoded = b64decode(userinfo_encoded)
        method, password = userinfo_decoded.split(":", 1)
    except Exception:
        logger.warning("Invalid userinfo %s", userinfo_encoded)
        return {}

    hostname_port = parsed_uri.netloc.split("@")[1]
    hostname, port_str = hostname_port.split(":")
    try:
        port = int(port_str)
    except ValueError:
        logger.warning("Invalid port %s", port_str)
        return {}

    outbound_config = {
        "type": "shadowsocks",
        "tag": tag_prefix + urllib.parse.unquote(parsed_uri.fragment),
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
            return {}

        outbound_config["plugin"] = plugin_parts[0]
        if len(plugin_parts) > 1:
            outbound_config["plugin_opts"] = plugin_parts[1]

    return outbound_config
