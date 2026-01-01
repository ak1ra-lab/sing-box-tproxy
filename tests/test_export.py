import base64
import json
from unittest.mock import MagicMock, patch

from sing_box_config.export import get_proxies_from_subscriptions


def test_inline_singbox():
    sub = {
        "type": "inline",
        "format": "sing-box",
        "outbounds": [{"tag": "proxy1", "type": "shadowsocks"}],
    }
    proxies = get_proxies_from_subscriptions("test", sub)
    assert len(proxies) == 1
    assert proxies[0]["tag"] == "proxy1"


def test_inline_sip002():
    uri = "ss://YWVzLTEyOC1nY206cGFzc3dvcmQ@1.2.3.4:8388#Example"
    content = base64.b64encode(uri.encode()).decode()
    sub = {"type": "inline", "format": "sip002", "content": content}
    proxies = get_proxies_from_subscriptions("test", sub)
    assert len(proxies) == 1
    # SIP002 format adds prefix
    assert proxies[0]["tag"] == "test - Example"


@patch("pathlib.Path.exists")
@patch("pathlib.Path.read_text")
def test_local_singbox(mock_read, mock_exists):
    mock_exists.return_value = True
    mock_read.return_value = json.dumps([{"tag": "proxy1", "type": "shadowsocks"}])

    sub = {"type": "local", "format": "sing-box", "path": "/tmp/proxies.json"}
    proxies = get_proxies_from_subscriptions("test", sub)
    assert len(proxies) == 1
    assert proxies[0]["tag"] == "proxy1"


@patch("sing_box_config.export.fetch_url_with_retries")
def test_remote_singbox(mock_fetch):
    mock_resp = MagicMock()
    mock_resp.text = json.dumps([{"tag": "proxy1", "type": "shadowsocks"}])
    mock_fetch.return_value = mock_resp

    sub = {"type": "remote", "format": "sing-box", "url": "http://example.com/sub"}
    proxies = get_proxies_from_subscriptions("test", sub)
    assert len(proxies) == 1
    assert proxies[0]["tag"] == "proxy1"


def test_exclude_filter():
    sub = {
        "type": "inline",
        "format": "sing-box",
        "outbounds": [
            {"tag": "KeepMe", "type": "shadowsocks"},
            {"tag": "ExcludeMe", "type": "shadowsocks"},
        ],
        "exclude": ["Exclude"],
    }
    proxies = get_proxies_from_subscriptions("test", sub)
    assert len(proxies) == 1
    assert proxies[0]["tag"] == "KeepMe"
