# Clash proxy format → sing-box outbound format
# https://github.com/Dreamacro/clash/wiki/configuration
# https://sing-box.sagernet.org/configuration/outbound/

import logging
from typing import Any

import yaml

from sing_box_config.parser.base import SubscriptionParser

logger = logging.getLogger(__name__)

# Clash proxy types we know how to convert
_SUPPORTED_TYPES: frozenset[str] = frozenset(
    {"ss", "vmess", "trojan", "vless", "socks5", "http"}
)


class ClashSubscriptionParser(SubscriptionParser):
    def parse(self, content: str) -> list[dict[str, Any]]:
        try:
            data = yaml.safe_load(content)
        except yaml.YAMLError as err:
            logger.warning("Failed to decode Clash subscription: %s", err)
            return []

        if not isinstance(data, dict):
            logger.warning("Invalid Clash subscription format")
            return []

        raw_proxies = data.get("proxies", [])
        if not isinstance(raw_proxies, list):
            logger.warning("Clash subscription 'proxies' field is not a list")
            return []

        proxies = []
        for raw in raw_proxies:
            proxy = self._convert(raw)
            if proxy is not None:
                proxies.append(proxy)
        return proxies

    # ------------------------------------------------------------------
    # Dispatcher
    # ------------------------------------------------------------------

    def _convert(self, raw: dict[str, Any]) -> dict[str, Any] | None:
        clash_type = str(raw.get("type", "")).lower()
        if clash_type not in _SUPPORTED_TYPES:
            logger.debug("Skipping unsupported Clash proxy type: %s", clash_type)
            return None
        converters = {
            "ss": self._convert_ss,
            "vmess": self._convert_vmess,
            "trojan": self._convert_trojan,
            "vless": self._convert_vless,
            "socks5": self._convert_socks5,
            "http": self._convert_http,
        }
        try:
            return converters[clash_type](raw)
        except Exception as err:
            logger.warning("Failed to convert Clash proxy %r: %s", raw.get("name"), err)
            return None

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    def _base(self, raw: dict[str, Any]) -> dict[str, Any]:
        return {
            "tag": raw.get("name", ""),
            "server": raw.get("server", ""),
            "server_port": int(raw.get("port", 0)),
        }

    def _tls(self, raw: dict[str, Any], sni_key: str = "sni") -> dict[str, Any] | None:
        if not raw.get("tls"):
            return None
        tls: dict[str, Any] = {"enabled": True}
        if raw.get("skip-cert-verify"):
            tls["insecure"] = True
        sni = raw.get(sni_key) or raw.get("servername") or raw.get("sni") or ""
        if sni:
            tls["server_name"] = sni
        return tls

    def _transport(self, raw: dict[str, Any]) -> dict[str, Any] | None:
        network = str(raw.get("network", "")).lower()
        if not network or network == "tcp":
            return None

        if network == "ws":
            opts: dict[str, Any] = raw.get("ws-opts", {}) or {}
            t: dict[str, Any] = {"type": "ws"}
            if opts.get("path"):
                t["path"] = opts["path"]
            if opts.get("headers"):
                t["headers"] = dict(opts["headers"])
            return t

        if network == "grpc":
            opts = raw.get("grpc-opts", {}) or {}
            return {"type": "grpc", "service_name": opts.get("grpc-service-name", "")}

        if network == "h2":
            opts = raw.get("h2-opts", {}) or {}
            t: dict[str, Any] = {"type": "http"}
            if opts.get("host"):
                t["host"] = list(opts["host"])
            if opts.get("path"):
                t["path"] = opts["path"]
            return t

        logger.debug("Unsupported Clash network type: %s", network)
        return None

    # ------------------------------------------------------------------
    # Per-type converters
    # ------------------------------------------------------------------

    def _convert_ss(self, raw: dict[str, Any]) -> dict[str, Any]:
        proxy: dict[str, Any] = {
            **self._base(raw),
            "type": "shadowsocks",
            "method": raw.get("cipher", ""),
            "password": str(raw.get("password", "")),
        }

        plugin = str(raw.get("plugin", "")).lower()
        plugin_opts: dict[str, Any] = raw.get("plugin-opts", {}) or {}
        if plugin == "obfs":
            mode = plugin_opts.get("mode", "")
            host = plugin_opts.get("host", "")
            proxy["plugin"] = "obfs-local"
            proxy["plugin_opts"] = f"obfs={mode}" + (
                f";obfs-host={host}" if host else ""
            )
        elif plugin == "v2ray-plugin":
            proxy["plugin"] = "v2ray-plugin"
            proxy["plugin_opts"] = f"mode={plugin_opts.get('mode', 'websocket')}"

        return proxy

    def _convert_vmess(self, raw: dict[str, Any]) -> dict[str, Any]:
        proxy: dict[str, Any] = {
            **self._base(raw),
            "type": "vmess",
            "uuid": raw.get("uuid", ""),
            "alter_id": int(raw.get("alterId", 0)),
            "security": raw.get("cipher", "auto"),
        }
        tls = self._tls(raw, sni_key="servername")
        if tls:
            proxy["tls"] = tls
        transport = self._transport(raw)
        if transport:
            proxy["transport"] = transport
        return proxy

    def _convert_trojan(self, raw: dict[str, Any]) -> dict[str, Any]:
        # Trojan always uses TLS
        proxy: dict[str, Any] = {
            **self._base(raw),
            "type": "trojan",
            "password": str(raw.get("password", "")),
            "tls": {
                "enabled": True,
                "insecure": bool(raw.get("skip-cert-verify", False)),
                "server_name": raw.get("sni", "") or raw.get("servername", ""),
            },
        }
        transport = self._transport(raw)
        if transport:
            proxy["transport"] = transport
        return proxy

    def _convert_vless(self, raw: dict[str, Any]) -> dict[str, Any]:
        proxy: dict[str, Any] = {
            **self._base(raw),
            "type": "vless",
            "uuid": raw.get("uuid", ""),
        }
        if raw.get("flow"):
            proxy["flow"] = raw["flow"]
        tls = self._tls(raw, sni_key="servername")
        if tls:
            proxy["tls"] = tls
        transport = self._transport(raw)
        if transport:
            proxy["transport"] = transport
        return proxy

    def _convert_socks5(self, raw: dict[str, Any]) -> dict[str, Any]:
        proxy: dict[str, Any] = {**self._base(raw), "type": "socks", "version": "5"}
        if raw.get("username"):
            proxy["username"] = raw["username"]
        if raw.get("password"):
            proxy["password"] = str(raw["password"])
        tls = self._tls(raw)
        if tls:
            proxy["tls"] = tls
        return proxy

    def _convert_http(self, raw: dict[str, Any]) -> dict[str, Any]:
        proxy: dict[str, Any] = {**self._base(raw), "type": "http"}
        if raw.get("username"):
            proxy["username"] = raw["username"]
        if raw.get("password"):
            proxy["password"] = str(raw["password"])
        tls = self._tls(raw)
        if tls:
            proxy["tls"] = tls
        return proxy
