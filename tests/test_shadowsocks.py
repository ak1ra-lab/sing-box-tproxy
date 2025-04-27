from sing_box_config.parser.shadowsocks import decode_sip002_to_singbox


def test_decode_invalid_scheme():
    uri = "http://YWVzLTEyOC1nY206OTI2NDAzNTEtOTViMS00NjJjLTkzNzgtYTRjZDAzOWY0Yzlh@server01.example.com:2333/?plugin=simple-obfs%3Bobfs%3Dhttp%3Bobfs-host%3Dexample.com#example-server01"
    assert decode_sip002_to_singbox(uri) == {}


def test_decode_invalid_userinfo():
    uri = "ss://invaliduserinfo@server01.example.com:2333/?plugin=simple-obfs%3Bobfs%3Dhttp%3Bobfs-host%3Dexample.com#example-server01"
    assert decode_sip002_to_singbox(uri) == {}


def test_decode_unsupported_plugin():
    uri = "ss://YWVzLTEyOC1nY206OTI2NDAzNTEtOTViMS00NjJjLTkzNzgtYTRjZDAzOWY0Yzlh@server01.example.com:2333/?plugin=unsupported-plugin%3Bobfs%3Dhttp%3Bobfs-host%3Dexample.com#example-server01"
    assert decode_sip002_to_singbox(uri) == {}


def test_decode_without_plugin():
    uri = "ss://YWVzLTEyOC1nY206OTI2NDAzNTEtOTViMS00NjJjLTkzNzgtYTRjZDAzOWY0Yzlh@server01.example.com:2333/#example-server01"
    tag_prefix = "test-"
    expected_config = {
        "type": "shadowsocks",
        "tag": "test-example-server01",
        "server": "server01.example.com",
        "server_port": 2333,
        "method": "aes-128-gcm",
        "password": "92640351-95b1-462c-9378-a4cd039f4c9a",
        "plugin": "",
        "plugin_opts": "",
    }
    assert decode_sip002_to_singbox(uri, tag_prefix) == expected_config


def test_decode_valid_sip002_uri():
    uri = "ss://YWVzLTEyOC1nY206OTI2NDAzNTEtOTViMS00NjJjLTkzNzgtYTRjZDAzOWY0Yzlh@server01.example.com:2333/?plugin=simple-obfs%3Bobfs%3Dhttp%3Bobfs-host%3Dexample.com#example-server01"
    tag_prefix = "test-"
    expected_config = {
        "type": "shadowsocks",
        "tag": "test-example-server01",
        "server": "server01.example.com",
        "server_port": 2333,
        "method": "aes-128-gcm",
        "password": "92640351-95b1-462c-9378-a4cd039f4c9a",
        "plugin": "obfs-local",
        "plugin_opts": "obfs=http;obfs-host=example.com",
    }
    assert decode_sip002_to_singbox(uri, tag_prefix) == expected_config
