# Ansible 变量说明

本文档详细说明了 `roles/sing_box_defaults/` 中定义的 Ansible 变量.

- **可覆盖变量** 定义在 `roles/sing_box_defaults/defaults/main.yaml`, 可在 `group_vars` / `host_vars` 中覆盖.
- **高优先级预设值** 定义在 `roles/sing_box_defaults/vars/main.yaml`. 由于 Ansible [变量优先级](https://docs.ansible.com/projects/ansible/latest/playbook_guide/playbooks_variables.html#variable-precedence-where-should-i-put-a-variable) 规则, role `vars/` 高于 `host_vars`、`group_vars`、playbook vars, 一般来讲建议通过 `--extra-vars` (`-e`) 覆盖.

## 核心配置逻辑

此项目在 `sing-box` 的配置上采用了一套特定的 DNS 和路由分流逻辑, 主要体现在 `dns.servers`, `dns.rules`, `route.rules` 和 `route.rule_sets` 的配合上.

### DNS 配置 (`dns.servers` & `dns.rules`)

DNS 解析策略的核心在于区分**可信 DNS**(Remote DoT/DoH, 用于代理流量)和**直连 DNS**(Local DNS, 用于国内或内网流量).

- **`dns_hosts`**: 预定义的 hosts 记录.
  - 包含公共 DNS 服务器(如 AliDNS, Cloudflare DNS)的 IP 地址.
  - 作用是作为 `domain_resolver`, 为 `dns_direct` 和 `dns_proxy` 提供解析服务, 确保 sing-box 启动时能直接连接到这些 DoT/DoH 服务器.
- **`dns_direct`**: 直连 DNS 服务器(默认 tag).
  - 通常配置为国内公共 DNS 的 DoT 服务(如 AliDNS).
  - 配置了 `domain_resolver: dns_hosts`.
  - 用于解析国内域名(`geosite-cn`).
- **`dns_proxy`**: 代理 DNS 服务器.
  - 通常配置为国外公共 DNS 的 DoT 服务(如 1.1.1.1).
  - 配置了 `domain_resolver: dns_hosts` 以及 `detour: PROXY`, 强制走代理出站.
  - 作为 `dns.final` 的默认值, 用于解析未命中国内规则的域名.
- **`dns_fakeip`**: FakeIP 范围.
  - 用于需要返回 FakeIP 的场景(如 `geosite-gfw`, `geosite-google` 等).

### 路由配置 (`route.rules` & `route.rule_sets`)

路由规则决定了流量经过哪个 Outbound.

- **Rule Sets**: 使用 `route.rule_set` 引用外部或生成的规则集.
  - **Remote Rule Sets**: 从 GitHub 自动下载的 `srs` 二进制规则集(如 `geoip-cn`, `geosite-gfw`).
  - **Custom Headless Rule Sets**: 在 Ansible 变量中定义的内联规则集.
    - `custom-rejected-rule-set`: 包含用户自定义的拒绝规则.
    - `custom-internal-rule-set`: 包含用户自定义的内网规则.
    - `custom-bypassed-rule-set`: 包含用户自定义的放行规则.
- **路由优先级**:
  1.  **Hijack DNS**: 拦截所有 DNS 流量(`port: 53` 或 `protocol: dns`)送入内置 DNS 服务器.
  2.  **Reject Rules**: 拒绝 `custom-rejected-rule-set` 中的目标.
  3.  **Direct Rules**: 放行 `custom-internal-rule-set` 和 `custom-bypassed-rule-set` 中的目标.
  4.  **Filtering Rules**: 基于 Geosite/GeoIP 进行分流.
      - `geosite-private`, `geosite-cn` -> `DIRECT`
      - `geosite-gfw`, `geosite-google` 等 -> `PROXY`
- **Default Domain Resolver**:
  - `route.default_domain_resolver` 设置为 `dns_direct`.
  - 这非常关键: 因为 `dns_proxy` 需要通过代理连接, 而代理节点本身的域名解析不能依赖于 `dns_proxy`(会死循环), 必须使用直连 DNS 解析代理服务器域名.

### 自定义规则的使用规范

为了保持配置的整洁, 项目提供了三个主要的自定义规则集变量:

1.  **`sing_box_custom_rejected_rule_set_rules`**: 用于屏蔽广告或恶意域名.
2.  **`sing_box_custom_internal_rule_set_rules`**: 用于指定内网域名.
3.  **`sing_box_custom_bypassed_rule_set_rules`**: 用于指定必须直连 (Bypassed) 的域名(不包含在默认 cn 列表中的).

**注意**: 在上述 `_rules`列表变量中, **不允许直接使用 `ip_cidr`**.

- 如果需要屏蔽 IP 段, 请使用 `sing_box_custom_rejected_ip4` 或 `sing_box_custom_rejected_ip6`.
- 如果需要放行 IP 段, 请使用 `sing_box_custom_bypassed_ip4` 或 `sing_box_custom_bypassed_ip6`.

---

## 变量列表

### 用户配置变量 (`defaults/main.yaml`)

以下变量定义在 `roles/sing_box_defaults/defaults/main.yaml` 中, 预期在 `group_vars` / `host_vars` 中按需覆盖.

| 变量名                                      | 类型    | 默认值                                   | 示例值                          | 描述                                                   |
| :------------------------------------------ | :------ | :--------------------------------------- | :------------------------------ | :----------------------------------------------------- |
| `sing_box_mode`                             | string  | `gateway`                                | `local`                         | sing-box 运行模式 (mixed, local, gateway)              |
| `sing_box_subscriptions`                    | dict    | `{}`                                     | 见 `defaults/main.yaml`         | 订阅配置字典, 支持 remote, local, inline 等多种类型    |
| `sing_box_validate_subscription_urls`       | boolean | `false`                                  | `true`                          | 是否在部署前检查订阅 URL 的连通性                      |
| `sing_box_apt_packages_state`               | string  | `present`                                | `latest`                        | sing-box APT 软件包状态 (`present` 或 `latest`)        |
| `sing_box_apt_packages`                     | list    | `[sing-box]`                             | `[sing-box-beta]`               | 需要安装的软件包列表                                   |
| `sing_box_pip_install_source`               | string  | `pypi`                                   | `local`                         | sing-box-config 安装来源 (`pypi`, `testpypi`, `local`) |
| `sing_box_config_timer_enabled`             | boolean | `true`                                   | -                               | 是否启用 sing-box-config.timer                         |
| `sing_box_config_timer_interval`            | string  | `1d`                                     | `6h`                            | sing-box-config.timer 触发间隔                         |
| `sing_box_config_timer_state`               | string  | `started`                                | -                               | sing-box-config.timer 期望状态                         |
| `sing_box_config_service_state`             | string  | `started`                                | -                               | sing-box-config.service 期望状态                       |
| `sing_box_liveness_probe_deploy`            | boolean | `false`                                  | `true`                          | 是否在目标主机上部署 liveness probe systemd unit       |
| `sing_box_liveness_probe_enabled`           | boolean | `false`                                  | -                               | liveness probe 是否开机自启 (deploy=true 时有效)       |
| `sing_box_liveness_probe_state`             | string  | `stopped`                                | `started`                       | liveness probe 期望状态 (deploy=true 时有效)           |
| `sing_box_liveness_probe_url`               | string  | `https://www.google.com/generate_204`    | -                               | 探活目标 URL                                           |
| `sing_box_liveness_probe_expected_status`   | list    | `[204]`                                  | `[200]`                         | 探活成功的 HTTP 状态码列表                             |
| `sing_box_liveness_probe_interval`          | integer | `60`                                     | -                               | 探活间隔 (秒)                                          |
| `sing_box_liveness_probe_timeout`           | integer | `30`                                     | -                               | 单次探活超时 (秒)                                      |
| `sing_box_liveness_probe_failure_threshold` | integer | `5`                                      | -                               | 触发 action 所需连续失败次数                           |
| `sing_box_liveness_probe_success_threshold` | integer | `1`                                      | -                               | 记录恢复事件所需连续成功次数                           |
| `sing_box_liveness_probe_action`            | list    | `[systemctl, restart, sing-box.service]` | -                               | 达到 failure_threshold 时执行的命令                    |
| `sing_box_liveness_probe_action_threshold`  | integer | `3`                                      | -                               | action 最大触发次数上限 (探活恢复后重置)               |
| `sing_box_github_proxy`                     | string  | `""`                                     | `https://gh.example.com/`       | GitHub 代理前缀, 用于加速规则集/UI 下载                |
| `sing_box_log_level`                        | string  | `warn`                                   | `info`                          | sing-box 日志等级                                      |
| `sing_box_clash_api_secret`                 | string  | `""`                                     | `Secret123`                     | Clash API 密钥 (留空则不鉴权)                          |
| `sing_box_clash_api_external_ui_reinstall`  | boolean | `false`                                  | `true`                          | 是否强制重新下载安装 Clash UI (yacd)                   |
| `sing_box_dns_internal_servers`             | list    | `[]`                                     | `["192.168.1.1"]`               | 内网 DNS 服务器 IP 列表                                |
| `sing_box_dns_final`                        | string  | `dns_proxy`                              | -                               | 默认 DNS 出站 tag (未命中规则的域名使用此解析器)       |
| `sing_box_custom_rejected_rule_set_rules`   | list    | `[]`                                     | `[{"domain_suffix": "ad.com"}]` | 自定义拒绝规则 (不含 IP, 用于屏蔽广告/恶意域名)        |
| `sing_box_custom_rejected_ip4`              | list    | `[]`                                     | `["10.0.0.0/8"]`                | 自定义拒绝 IPv4 CIDR (同时应用到 nftables)             |
| `sing_box_custom_rejected_ip6`              | list    | `[]`                                     | -                               | 自定义拒绝 IPv6 CIDR (同时应用到 nftables)             |
| `sing_box_custom_internal_rule_set_rules`   | list    | `[]`                                     | `[{"domain_suffix": "lan"}]`    | 自定义内网域名规则 (走 DIRECT + dns_internal)          |
| `sing_box_custom_bypassed_rule_set_rules`   | list    | `[]`                                     | `[{"domain": "example.com"}]`   | 自定义强制直连规则 (不含 IP)                           |
| `sing_box_custom_bypassed_ip4`              | list    | `[]`                                     | -                               | 自定义强制直连 IPv4 CIDR (同时应用到 nftables)         |
| `sing_box_custom_bypassed_ip6`              | list    | `[]`                                     | -                               | 自定义强制直连 IPv6 CIDR (同时应用到 nftables)         |
| `sing_box_selfhost_detour_enabled`          | boolean | `false`                                  | `true`                          | 是否为自建节点生成 `-detour` 链式代理副本              |

### 高优先级预设值 (`vars/main.yaml`)

以下变量定义在 `roles/sing_box_defaults/vars/main.yaml` 中, 提供了有完整注释的预设值. 由于 role `vars/` 的优先级高于 `host_vars`、`group_vars`、play vars, **不能**通过常规变量层覆盖; 若确实需要调整, 请在执行 ansible-playbook 时使用 `--extra-vars` (`-e`) 或 `--extra-vars=@path/to/overrides.yaml`.

| 变量名                                                 | 类型    | 默认值                         | 描述                                                        |
| :----------------------------------------------------- | :------ | :----------------------------- | :---------------------------------------------------------- |
| `sing_box_mixed_port`                                  | integer | `7890`                         | HTTP/SOCKS 混合代理端口                                     |
| `sing_box_tproxy_port`                                 | integer | `7895`                         | 透明代理 (TPROXY) 端口                                      |
| `sing_box_proxy_route_table`                           | integer | `224`                          | iproute2 路由表 ID                                          |
| `sing_box_proxy_mark`                                  | integer | `224`                          | 需代理流量的 fwmark 值                                      |
| `sing_box_route_default_mark`                          | integer | `225`                          | sing-box 自身出站流量的 fwmark 值 (防回环)                  |
| `sing_box_nftables_flow_offload`                       | boolean | `true`                         | 是否启用 nftables flow offloading                           |
| `sing_box_tcp_bbr_enabled`                             | boolean | `true`                         | 是否启用 TCP BBR 拥塞控制                                   |
| `sing_box_sysctl_nf_conntrack`                         | boolean | `true`                         | 是否调整 nf_conntrack 内核参数                              |
| `sing_box_sysctl_nf_conntrack_buckets`                 | integer | `65536`                        | conntrack 哈希表桶数                                        |
| `sing_box_sysctl_nf_conntrack_max`                     | integer | `262144`                       | conntrack 最大连接数                                        |
| `sing_box_sysctl_nf_conntrack_tcp_timeout_established` | integer | `3600`                         | TCP 已建立连接超时 (秒)                                     |
| `sing_box_cache_file_enabled`                          | boolean | `true`                         | 是否启用 sing-box 缓存文件                                  |
| `sing_box_cache_file_store_fakeip`                     | boolean | `true`                         | 是否缓存 FakeIP 映射                                        |
| `sing_box_cache_file_store_rdrc`                       | boolean | `true`                         | 是否缓存拒收响应                                            |
| `sing_box_dns_strategy`                                | string  | `prefer_ipv4`                  | DNS 解析策略 (`prefer_ipv4`, `prefer_ipv6`, `ipv4_only` 等) |
| `sing_box_dns_disable_cache`                           | boolean | `false`                        | 禁用 DNS 缓存                                               |
| `sing_box_dns_disable_expire`                          | boolean | `false`                        | 禁用 DNS 缓存过期                                           |
| `sing_box_dns_independent_cache`                       | boolean | `false`                        | 各服务器独立缓存                                            |
| `sing_box_dns_cache_capacity`                          | integer | `65535`                        | DNS 缓存条目上限                                            |
| `sing_box_route_final`                                 | string  | `FINAL`                        | 路由兜底 Outbound tag                                       |
| `sing_box_route_default_domain_resolver`               | string  | `dns_direct`                   | Outbound 域名解析器 (不能为代理出站, 否则死循环)            |
| `sing_box_route_auto_detect_interface`                 | boolean | `true`                         | 自动检测出口接口                                            |
| `sing_box_custom_rejected_rule_set`                    | string  | `custom-rejected-rule-set`     | 自定义拒绝规则集的 tag 名                                   |
| `sing_box_custom_internal_rule_set`                    | string  | `custom-internal-rule-set`     | 自定义内网规则集的 tag 名                                   |
| `sing_box_custom_internal_rule_set_dns`                | string  | `dns_internal`                 | 内网规则集使用的 DNS tag                                    |
| `sing_box_custom_bypassed_rule_set`                    | string  | `custom-bypassed-rule-set`     | 自定义放行规则集的 tag 名                                   |
| `sing_box_custom_bypassed_rule_set_dns`                | string  | `dns_direct`                   | 放行规则集使用的 DNS tag                                    |
| `sing_box_remote_rule_set_url_prefix`                  | string  | `...github.com/.../sing/geo/`  | 远程规则集 URL 前缀 (受 `sing_box_github_proxy` 影响)       |
| `sing_box_remote_rule_set_update_interval`             | string  | `30d`                          | 远程规则集更新间隔                                          |
| `sing_box_remote_rule_sets`                            | list    | `[geoip-cn, geosite-gfw, ...]` | 启用的远程规则集列表                                        |
| `sing_box_basic_dns_rules`                             | list    | `[...]`                        | 基础 DNS 分流规则 (cn/private 直连, gfw/google 等走 fakeip) |
| `sing_box_basic_route_rules`                           | list    | `[...]`                        | 基础路由规则 (DNS 劫持, SSH 直连等)                         |
| `sing_box_filtering_route_rules`                       | list    | `[...]`                        | 应用层过滤/分流规则 (geoip/geosite → DIRECT/PROXY/AI 等)    |
| `sing_box_proxy_groups`                                | list    | `[PROXY, FINAL, AI, ...]`      | 顶层 Proxy Group (Selector) 列表                            |
| `sing_box_selfhost_tag_pattern`                        | string  | `selfhost\|自建`               | 识别自建节点 tag 的正则模式                                 |
| `sing_box_region_groups`                               | list    | `[{tag, regex}, ...]`          | 各地区组配置 (tag/regex); 模板直接由此生成 auto/selector/selfhost 三套分组 (SG/HK/JP/TW/US/EU/KR 等) |
