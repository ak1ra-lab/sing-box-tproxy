import base64
import json
from unittest.mock import MagicMock, patch

from sing_box_config.export import (
    apply_name_prefix,
    build_selfhost_detours,
    get_proxies_from_subscriptions,
    patch_intra_subscription_detours,
    populate_outbound_groups,
    remove_invalid_outbounds,
)


def test_inline_singbox():
    sub = {
        "type": "inline",
        "format": "sing-box",
        "outbounds": [{"tag": "proxy1", "type": "shadowsocks"}],
    }
    proxies = get_proxies_from_subscriptions("test", sub)
    assert len(proxies) == 1
    assert proxies[0]["tag"] == "test - proxy1"


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
    assert proxies[0]["tag"] == "test - proxy1"


@patch("pathlib.Path.exists")
@patch("pathlib.Path.read_text")
def test_local_singbox_paths(mock_read, mock_exists):
    mock_exists.return_value = True
    mock_read.side_effect = [
        json.dumps([{"tag": "proxy1", "type": "shadowsocks"}]),
        json.dumps([{"tag": "proxy2", "type": "shadowsocks"}]),
    ]

    sub = {
        "type": "local",
        "format": "sing-box",
        "paths": ["/tmp/proxies1.json", "/tmp/proxies2.json"],
    }
    proxies = get_proxies_from_subscriptions("test", sub)
    assert len(proxies) == 2
    assert proxies[0]["tag"] == "test - proxy1"
    assert proxies[1]["tag"] == "test - proxy2"


@patch("sing_box_config.subscription.remote.fetch_url_with_retries")
def test_remote_singbox(mock_fetch):
    mock_resp = MagicMock()
    mock_resp.text = json.dumps([{"tag": "proxy1", "type": "shadowsocks"}])
    mock_fetch.return_value = mock_resp

    sub = {"type": "remote", "format": "sing-box", "url": "http://example.com/sub"}
    proxies = get_proxies_from_subscriptions("test", sub)
    assert len(proxies) == 1
    assert proxies[0]["tag"] == "test - proxy1"


@patch("sing_box_config.subscription.remote.fetch_url_with_retries")
def test_remote_singbox_urls(mock_fetch):
    resp1, resp2 = MagicMock(), MagicMock()
    resp1.text = json.dumps([{"tag": "proxy1", "type": "shadowsocks"}])
    resp2.text = json.dumps([{"tag": "proxy2", "type": "shadowsocks"}])
    mock_fetch.side_effect = [resp1, resp2]

    sub = {
        "type": "remote",
        "format": "sing-box",
        "urls": ["http://example.com/sub1", "http://example.com/sub2"],
    }
    proxies = get_proxies_from_subscriptions("test", sub)
    assert len(proxies) == 2
    assert proxies[0]["tag"] == "test - proxy1"
    assert proxies[1]["tag"] == "test - proxy2"


@patch("pathlib.Path.exists")
@patch("pathlib.Path.read_text")
def test_local_singbox_path_and_paths_merged_deduplicated(mock_read, mock_exists):
    """path + paths together: union in order, duplicates removed."""
    mock_exists.return_value = True
    mock_read.side_effect = [
        json.dumps([{"tag": "proxy1", "type": "shadowsocks"}]),
        json.dumps([{"tag": "proxy2", "type": "shadowsocks"}]),
    ]

    sub = {
        "type": "local",
        "format": "sing-box",
        # paths lists proxy1 and proxy2; path duplicates proxy1 — should be ignored
        "paths": ["/tmp/proxies1.json", "/tmp/proxies2.json"],
        "path": "/tmp/proxies1.json",
    }
    proxies = get_proxies_from_subscriptions("test", sub)
    assert len(proxies) == 2
    assert proxies[0]["tag"] == "test - proxy1"
    assert proxies[1]["tag"] == "test - proxy2"


@patch("sing_box_config.subscription.remote.fetch_url_with_retries")
def test_remote_singbox_url_and_urls_merged_deduplicated(mock_fetch):
    """url + urls together: union in order, duplicates removed."""
    resp1, resp2 = MagicMock(), MagicMock()
    resp1.text = json.dumps([{"tag": "proxy1", "type": "shadowsocks"}])
    resp2.text = json.dumps([{"tag": "proxy2", "type": "shadowsocks"}])
    mock_fetch.side_effect = [resp1, resp2]

    sub = {
        "type": "remote",
        "format": "sing-box",
        # urls lists sub1 and sub2; url duplicates sub1 — should be ignored
        "urls": ["http://example.com/sub1", "http://example.com/sub2"],
        "url": "http://example.com/sub1",
    }
    proxies = get_proxies_from_subscriptions("test", sub)
    assert len(proxies) == 2
    assert proxies[0]["tag"] == "test - proxy1"
    assert proxies[1]["tag"] == "test - proxy2"


def test_exclude_filter():
    sub = {
        "type": "inline",
        "format": "sing-box",
        "outbounds": [
            {"tag": "KeepMe", "type": "shadowsocks"},
            {"tag": "ExcludeMe", "type": "shadowsocks"},
        ],
        "exclude": "Exclude",
    }
    proxies = get_proxies_from_subscriptions("test", sub)
    assert len(proxies) == 1
    assert proxies[0]["tag"] == "test - KeepMe"


# apply_name_prefix


def test_apply_name_prefix_renames_tags():
    proxies = [
        {"tag": "node-01", "type": "shadowsocks"},
        {"tag": "node-02", "type": "vmess"},
    ]
    apply_name_prefix(proxies, "myprovider")
    assert proxies[0]["tag"] == "myprovider - node-01"
    assert proxies[1]["tag"] == "myprovider - node-02"


# patch_intra_subscription_detours


def test_patch_intra_subscription_detours_updates_detour_reference():
    """detour pointing at another proxy in the same subscription gets the prefix."""
    proxies = [
        {"tag": "relay-01", "type": "vless", "detour": "entry-01"},
        {"tag": "entry-01", "type": "shadowsocks"},
    ]
    patch_intra_subscription_detours(proxies, "myprovider")
    relay = next(p for p in proxies if p["tag"] == "relay-01")
    assert relay["detour"] == "myprovider - entry-01"


def test_patch_intra_subscription_detours_ignores_external_detour():
    """detour referencing a tag not in this subscription is left unchanged."""
    proxies = [{"tag": "node-01", "type": "vless", "detour": "warp"}]
    patch_intra_subscription_detours(proxies, "myprovider")
    assert proxies[0]["detour"] == "warp"


# duplicate_selfhost_detour

SELFHOST_DETOUR_MAP = [
    {"filter": "SG|Singapore|狮城", "detour": "🇸🇬 狮城节点"},
    {"filter": "US|United States|美国", "detour": "🇺🇸 美国节点"},
]


def test_build_selfhost_detours_basic():
    proxies = [
        {"type": "shadowsocks", "tag": "selfhost-sg-01"},
        {"type": "shadowsocks", "tag": "selfhost-us-02"},
    ]
    result = build_selfhost_detours(proxies, SELFHOST_DETOUR_MAP)

    assert len(result) == 2
    sg_copy = next(p for p in result if "sg" in p["tag"])
    us_copy = next(p for p in result if "us" in p["tag"])

    assert sg_copy["tag"] == "selfhost-sg-01-detour"
    assert sg_copy["detour"] == "🇸🇬 狮城节点"
    assert us_copy["tag"] == "selfhost-us-02-detour"
    assert us_copy["detour"] == "🇺🇸 美国节点"


def test_build_selfhost_detours_preserves_original():
    """The original proxy dicts must not be mutated."""
    original = {"type": "shadowsocks", "tag": "selfhost-sg-01", "server": "1.2.3.4"}
    result = build_selfhost_detours([original], SELFHOST_DETOUR_MAP)

    # Original unchanged
    assert "detour" not in original
    assert original["tag"] == "selfhost-sg-01"

    # Copy is independent
    assert result[0] is not original
    assert result[0]["server"] == "1.2.3.4"


def test_build_selfhost_detours_no_region_match():
    """Proxies with no matching region are silently skipped."""
    proxies = [{"type": "shadowsocks", "tag": "selfhost-unknown-01"}]
    result = build_selfhost_detours(proxies, SELFHOST_DETOUR_MAP)
    assert result == []


def test_build_selfhost_detours_empty_inputs():
    assert build_selfhost_detours([], SELFHOST_DETOUR_MAP) == []
    assert build_selfhost_detours([{"tag": "selfhost-sg-01"}], []) == []


# remove_invalid_outbounds


def test_remove_invalid_outbounds_empty_selfhost_groups():
    """Empty selfhost group and its orphan reference in parent group are both cleaned up."""
    outbounds = [
        {"tag": "🇸🇬 狮城节点 - 自建", "type": "selector", "outbounds": []},
        {
            "tag": "PROXY",
            "type": "selector",
            "outbounds": ["🇸🇬 狮城节点 - 自建", "DIRECT"],
        },
    ]
    remove_invalid_outbounds(outbounds)
    tags = [o["tag"] for o in outbounds]
    assert "🇸🇬 狮城节点 - 自建" not in tags
    proxy_group = next(o for o in outbounds if o["tag"] == "PROXY")
    assert "🇸🇬 狮城节点 - 自建" not in proxy_group["outbounds"]
    assert "DIRECT" in proxy_group["outbounds"]


# filter_valid_proxies
def _make_outbound(tag: str, filter_pat: str = None, exclude_pat: str = None) -> dict:
    ob: dict = {"tag": tag, "type": "selector", "outbounds": []}
    if filter_pat is not None:
        ob["filter"] = filter_pat
    if exclude_pat is not None:
        ob["exclude"] = exclude_pat
    return ob


PROXIES = [
    {"tag": "sg-provider-01", "type": "shadowsocks"},
    {"tag": "us-provider-02", "type": "shadowsocks"},
    {"tag": "selfhost-sg-01", "type": "shadowsocks"},
]


def test_populate_outbound_groups_filter_only():
    outbound = _make_outbound("SG nodes", filter_pat="sg")
    populate_outbound_groups([outbound], PROXIES)
    assert outbound["outbounds"] == ["sg-provider-01", "selfhost-sg-01"]


def test_populate_outbound_groups_exclude():
    outbound = _make_outbound("SG provider", filter_pat="sg", exclude_pat="selfhost")
    populate_outbound_groups([outbound], PROXIES)
    assert outbound["outbounds"] == ["sg-provider-01"]


def test_populate_outbound_groups_no_filter_no_exclude():
    """Outbounds without filter/exclude keys are left untouched."""
    outbound = {"tag": "PROXY", "type": "selector", "outbounds": []}
    populate_outbound_groups([outbound], PROXIES)
    assert outbound["outbounds"] == []


def test_populate_outbound_groups_pops_keys():
    """filter and exclude keys must be removed from the outbound dict."""
    outbound = _make_outbound("test", filter_pat="sg", exclude_pat="selfhost")
    populate_outbound_groups([outbound], PROXIES)
    assert "filter" not in outbound
    assert "exclude" not in outbound
    assert build_selfhost_detours([{"tag": "selfhost-sg-01"}], {}) == []
