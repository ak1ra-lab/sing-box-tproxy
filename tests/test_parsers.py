import base64
import json

import yaml

from sing_box_config.parser.clash import ClashSubscriptionParser
from sing_box_config.parser.shadowsocks import SIP002SubscriptionParser
from sing_box_config.parser.sing_box import SingBoxSubscriptionParser


def test_sip002_parser_valid():
    # ss://YWVzLTEyOC1nY206cGFzc3dvcmQ@1.2.3.4:8388#Example1
    # ss://YWVzLTEyOC1nY206cGFzc3dvcmQ@5.6.7.8:8388#Example2
    uri1 = "ss://YWVzLTEyOC1nY206cGFzc3dvcmQ@1.2.3.4:8388#Example1"
    uri2 = "ss://YWVzLTEyOC1nY206cGFzc3dvcmQ@5.6.7.8:8388#Example2"
    content = base64.b64encode(f"{uri1}\n{uri2}".encode()).decode()

    proxies = SIP002SubscriptionParser().parse(content)
    assert len(proxies) == 2
    assert proxies[0]["tag"] == "Example1"
    assert proxies[1]["tag"] == "Example2"


def test_sip002_parser_invalid_base64():
    proxies = SIP002SubscriptionParser().parse("invalid-base64")
    assert proxies == []


def test_singbox_parser_list():
    data = [
        {"type": "shadowsocks", "tag": "proxy1"},
        {"type": "vmess", "tag": "proxy2"},
    ]
    content = json.dumps(data)
    proxies = SingBoxSubscriptionParser().parse(content)
    assert len(proxies) == 2
    assert proxies[0]["tag"] == "proxy1"


def test_singbox_parser_dict_with_outbounds():
    data = {"outbounds": [{"type": "shadowsocks", "tag": "proxy1"}]}
    content = json.dumps(data)
    proxies = SingBoxSubscriptionParser().parse(content)
    assert len(proxies) == 1
    assert proxies[0]["tag"] == "proxy1"


def test_singbox_parser_invalid_json():
    proxies = SingBoxSubscriptionParser().parse("invalid-json")
    assert proxies == []


def test_singbox_parser_filters_group_types():
    data = [
        {"type": "shadowsocks", "tag": "real-node"},
        {"type": "selector", "tag": "PROXY", "outbounds": []},
        {"type": "urltest", "tag": "Auto", "outbounds": []},
    ]
    proxies = SingBoxSubscriptionParser().parse(json.dumps(data))
    assert len(proxies) == 1
    assert proxies[0]["tag"] == "real-node"


# ClashSubscriptionParser


def _clash_yaml(*proxies: dict) -> str:
    return yaml.dump({"proxies": list(proxies)})


def test_clash_parser_ss_basic():
    raw = {
        "name": "HK-01",
        "type": "ss",
        "server": "1.2.3.4",
        "port": 8388,
        "cipher": "chacha20-ietf-poly1305",
        "password": "secret",
    }
    proxies = ClashSubscriptionParser().parse(_clash_yaml(raw))
    assert len(proxies) == 1
    p = proxies[0]
    assert p["type"] == "shadowsocks"
    assert p["tag"] == "HK-01"
    assert p["server"] == "1.2.3.4"
    assert p["server_port"] == 8388
    assert p["method"] == "chacha20-ietf-poly1305"
    assert p["password"] == "secret"


def test_clash_parser_ss_obfs_plugin():
    raw = {
        "name": "HK-obfs",
        "type": "ss",
        "server": "1.2.3.4",
        "port": 443,
        "cipher": "aes-128-gcm",
        "password": "pw",
        "plugin": "obfs",
        "plugin-opts": {"mode": "tls", "host": "cloudfront.net"},
    }
    proxies = ClashSubscriptionParser().parse(_clash_yaml(raw))
    p = proxies[0]
    assert p["plugin"] == "obfs-local"
    assert "obfs=tls" in p["plugin_opts"]
    assert "obfs-host=cloudfront.net" in p["plugin_opts"]


def test_clash_parser_vmess_ws_tls():
    raw = {
        "name": "US-vmess",
        "type": "vmess",
        "server": "example.com",
        "port": 443,
        "uuid": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        "alterId": 0,
        "cipher": "auto",
        "tls": True,
        "network": "ws",
        "ws-opts": {"path": "/path", "headers": {"Host": "example.com"}},
    }
    proxies = ClashSubscriptionParser().parse(_clash_yaml(raw))
    p = proxies[0]
    assert p["type"] == "vmess"
    assert p["uuid"] == "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    assert p["alter_id"] == 0
    assert p["tls"]["enabled"] is True
    assert p["transport"]["type"] == "ws"
    assert p["transport"]["path"] == "/path"
    assert p["transport"]["headers"]["Host"] == "example.com"


def test_clash_parser_trojan():
    raw = {
        "name": "JP-trojan",
        "type": "trojan",
        "server": "jp.example.com",
        "port": 443,
        "password": "trojan-pw",
        "sni": "jp.example.com",
        "skip-cert-verify": False,
    }
    proxies = ClashSubscriptionParser().parse(_clash_yaml(raw))
    p = proxies[0]
    assert p["type"] == "trojan"
    assert p["password"] == "trojan-pw"
    assert p["tls"]["enabled"] is True
    assert p["tls"]["server_name"] == "jp.example.com"
    assert p["tls"].get("insecure", False) is False


def test_clash_parser_anytls():
    raw = {
        "name": "HK-anytls",
        "type": "anytls",
        "server": "hk-01.example.com",
        "port": 20300,
        "client-fingerprint": "chrome",
        "idle-session-check-interval": 30,
        "idle-session-timeout": 30,
        "min-idle-session": 0,
        "alpn": ["h2"],
        "password": "secret",
        "sni": "cloudfront-cn.jdcloud.com",
        "skip-cert-verify": True,
    }
    proxies = ClashSubscriptionParser().parse(_clash_yaml(raw))
    p = proxies[0]
    assert p["type"] == "anytls"
    assert p["tag"] == "HK-anytls"
    assert p["server"] == "hk-01.example.com"
    assert p["server_port"] == 20300
    assert p["password"] == "secret"
    assert p["idle_session_check_interval"] == "30s"
    assert p["idle_session_timeout"] == "30s"
    assert p["min_idle_session"] == 0
    assert p["tls"]["enabled"] is True
    assert p["tls"]["server_name"] == "cloudfront-cn.jdcloud.com"
    assert p["tls"]["insecure"] is True
    assert p["tls"]["alpn"] == ["h2"]
    assert p["tls"]["utls"] == {"enabled": True, "fingerprint": "chrome"}


def test_clash_parser_skips_unsupported_type():
    raw_ssr = {"name": "SSR-01", "type": "ssr", "server": "1.2.3.4", "port": 1080}
    raw_ss = {
        "name": "SS-01",
        "type": "ss",
        "server": "1.2.3.4",
        "port": 8388,
        "cipher": "aes-128-gcm",
        "password": "pw",
    }
    proxies = ClashSubscriptionParser().parse(_clash_yaml(raw_ssr, raw_ss))
    assert len(proxies) == 1
    assert proxies[0]["tag"] == "SS-01"


def test_clash_parser_invalid_yaml():
    proxies = ClashSubscriptionParser().parse(": invalid: yaml: {{{{")
    assert proxies == []


def test_clash_parser_no_proxies_key():
    proxies = ClashSubscriptionParser().parse(yaml.dump({"proxy-groups": []}))
    assert proxies == []
