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
    {"ss", "vmess", "trojan", "vless", "socks5", "http", "anytls"}
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
            "anytls": self._convert_anytls,
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

    def _tls(
        self,
        raw: dict[str, Any],
        sni_key: str = "sni",
        *,
        force_enabled: bool = False,
        include_alpn: bool = False,
        include_utls: bool = False,
    ) -> dict[str, Any] | None:
        if not force_enabled and not raw.get("tls"):
            return None
        tls: dict[str, Any] = {"enabled": True}
        if raw.get("skip-cert-verify"):
            tls["insecure"] = True
        sni = raw.get(sni_key) or raw.get("servername") or raw.get("sni") or ""
        if sni:
            tls["server_name"] = sni
        if include_alpn and (alpn := raw.get("alpn")):
            if isinstance(alpn, list):
                tls["alpn"] = [str(value) for value in alpn if str(value)]
            else:
                tls["alpn"] = [str(alpn)]
        if include_utls and (
            fingerprint := raw.get("client-fingerprint")
            or raw.get("client_fingerprint")
        ):
            tls["utls"] = {"enabled": True, "fingerprint": str(fingerprint)}
        return tls

    def _duration(self, raw_value: Any) -> str | None:
        if raw_value is None or raw_value == "":
            return None
        if isinstance(raw_value, bool):
            return None
        if isinstance(raw_value, int):
            return f"{raw_value}s"
        if isinstance(raw_value, float):
            if raw_value.is_integer():
                return f"{int(raw_value)}s"
            return f"{raw_value}s"

        value = str(raw_value).strip()
        if not value:
            return None
        if value.isdecimal():
            return f"{value}s"
        return value

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
        if flow := raw.get("flow"):
            proxy["flow"] = flow
        tls = self._tls(raw, sni_key="servername")
        if tls:
            proxy["tls"] = tls
        transport = self._transport(raw)
        if transport:
            proxy["transport"] = transport
        return proxy

    def _convert_socks5(self, raw: dict[str, Any]) -> dict[str, Any]:
        proxy: dict[str, Any] = {**self._base(raw), "type": "socks", "version": "5"}
        if username := raw.get("username"):
            proxy["username"] = username
        if password := raw.get("password"):
            proxy["password"] = str(password)
        tls = self._tls(raw)
        if tls:
            proxy["tls"] = tls
        return proxy

    def _convert_http(self, raw: dict[str, Any]) -> dict[str, Any]:
        proxy: dict[str, Any] = {**self._base(raw), "type": "http"}
        if username := raw.get("username"):
            proxy["username"] = username
        if password := raw.get("password"):
            proxy["password"] = str(password)
        tls = self._tls(raw)
        if tls:
            proxy["tls"] = tls
        return proxy

    def _convert_anytls(self, raw: dict[str, Any]) -> dict[str, Any]:
        proxy: dict[str, Any] = {
            **self._base(raw),
            "type": "anytls",
            "password": str(raw.get("password", "")),
            "tls": self._tls(
                raw,
                force_enabled=True,
                include_alpn=True,
                include_utls=True,
            ),
        }

        if (
            value := self._duration(raw.get("idle-session-check-interval"))
        ) is not None:
            proxy["idle_session_check_interval"] = value
        if (value := self._duration(raw.get("idle-session-timeout"))) is not None:
            proxy["idle_session_timeout"] = value

        min_idle_session = raw.get("min-idle-session")
        if min_idle_session is not None:
            proxy["min_idle_session"] = int(min_idle_session)

        return proxy
