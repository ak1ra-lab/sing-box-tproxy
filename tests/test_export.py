import base64
import json
from unittest.mock import MagicMock, patch

from sing_box_config.export import (
    duplicate_selfhost_detour,
    get_proxies_from_subscriptions,
)


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


# ---------------------------------------------------------------------------
# duplicate_selfhost_detour
# ---------------------------------------------------------------------------

SELFHOST_DETOUR_MAP = {
    "SG|Singapore|狮城": "🇸🇬 狮城节点",
    "US|United States|美国": "🇺🇸 美国节点",
}


def test_duplicate_selfhost_detour_basic():
    proxies = [
        {"type": "shadowsocks", "tag": "selfhost-sg-01"},
        {"type": "shadowsocks", "tag": "selfhost-us-02"},
    ]
    result = duplicate_selfhost_detour(proxies, SELFHOST_DETOUR_MAP)

    assert len(result) == 2
    sg_copy = next(p for p in result if "sg" in p["tag"])
    us_copy = next(p for p in result if "us" in p["tag"])

    assert sg_copy["tag"] == "selfhost-sg-01-detour"
    assert sg_copy["detour"] == "🇸🇬 狮城节点"
    assert us_copy["tag"] == "selfhost-us-02-detour"
    assert us_copy["detour"] == "🇺🇸 美国节点"


def test_duplicate_selfhost_detour_preserves_original():
    """The original proxy dicts must not be mutated."""
    original = {"type": "shadowsocks", "tag": "selfhost-sg-01", "server": "1.2.3.4"}
    result = duplicate_selfhost_detour([original], SELFHOST_DETOUR_MAP)

    # Original unchanged
    assert "detour" not in original
    assert original["tag"] == "selfhost-sg-01"

    # Copy is independent
    assert result[0] is not original
    assert result[0]["server"] == "1.2.3.4"


def test_duplicate_selfhost_detour_no_region_match():
    """Proxies with no matching region are silently skipped."""
    proxies = [{"type": "shadowsocks", "tag": "selfhost-unknown-01"}]
    result = duplicate_selfhost_detour(proxies, SELFHOST_DETOUR_MAP)
    assert result == []


def test_duplicate_selfhost_detour_empty_inputs():
    assert duplicate_selfhost_detour([], SELFHOST_DETOUR_MAP) == []
    assert duplicate_selfhost_detour([{"tag": "selfhost-sg-01"}], {}) == []
