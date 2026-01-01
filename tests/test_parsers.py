import base64
import json

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
