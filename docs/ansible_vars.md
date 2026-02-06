# Ansible 变量说明

本文档详细说明了 `roles/sing_box_defaults/defaults/main.yaml` 中定义的 Ansible 变量.

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

以下变量均定义在 `roles/sing_box_defaults/defaults/main.yaml` 中.

| 变量名                                                 | 类型    | 默认值                           | 示例值                          | 描述                                                |
| :----------------------------------------------------- | :------ | :------------------------------- | :------------------------------ | :-------------------------------------------------- |
| `sing_box_mode`                                        | string  | `gateway`                        | `local`                         | sing-box 运行模式 (mixed, local, gateway)           |
| `sing_box_mode_available`                              | list    | `["mixed", "local", "gateway"]`  | -                               | 支持的运行模式列表(常量)                            |
| `sing_box_subscriptions`                               | dict    | `{}`                             | 见 `defaults/main.yaml`         | 订阅配置字典, 支持 remote, local, inline 等多种类型 |
| `sing_box_validate_subscription_urls`                  | boolean | `false`                          | `true`                          | 是否在部署前检查订阅 URL 的连通性                   |
| `sing_box_user`                                        | dict    | `{name: proxy, ...}`             | -                               | 运行 sing-box 的系统用户信息                        |
| `sing_box_group`                                       | dict    | `{name: proxy, ...}`             | -                               | 运行 sing-box 的系统用户组信息                      |
| `sing_box_etc_dir`                                     | string  | `/etc/sing-box`                  | -                               | 配置文件目录                                        |
| `sing_box_log_dir`                                     | string  | `/var/log/sing-box`              | -                               | 日志文件目录                                        |
| `sing_box_state_dir`                                   | string  | `/var/lib/sing-box`              | -                               | 状态/缓存文件目录                                   |
| `sing_box_etc_config_file`                             | string  | `.../config.json`                | -                               | 主配置文件路径                                      |
| `sing_box_state_venv_dir`                              | string  | `.../.venv`                      | -                               | Python 虚拟环境路径                                 |
| `sing_box_state_config_dir`                            | string  | `.../config`                     | -                               | 生成的配置文件存放目录                              |
| `sing_box_state_acme_dir`                              | string  | `.../acme`                       | -                               | ACME 证书目录                                       |
| `sing_box_local_repo_root`                             | string  | `...`                            | -                               | 本地 Git 仓库根目录                                 |
| `sing_box_local_config_dir`                            | string  | `.../config`                     | -                               | 本地配置生成目录                                    |
| `sing_box_local_client_outbounds`                      | string  | `.../client_outbounds`           | -                               | 客户端配置输出目录                                  |
| `sing_box_apt_key_url`                                 | string  | `https://sing-box.app/gpg.key`   | -                               | APT GPG Key URL                                     |
| `sing_box_apt_keyrings_dest`                           | string  | `/etc/apt/keyrings/sagernet.asc` | -                               | Keyring 保存路径                                    |
| `sing_box_apt_repo`                                    | string  | `sagernet`                       | -                               | APT 源名称                                          |
| `sing_box_apt_repo_uris`                               | string  | `https://deb.sagernet.org/`      | -                               | APT 源地址                                          |
| `sing_box_apt_packages_state`                          | string  | `present`                        | `latest`                        | 软件包状态                                          |
| `sing_box_apt_packages`                                | list    | `[sing-box]`                     | -                               | 需要安装的软件包列表                                |
| `sing_box_pip_install_source`                          | string  | `pypi`                           | `local`                         | Python 配置生成脚本的安装来源                       |
| `sing_box_pip_extra_args`                              | dict    | `{...}`                          | -                               | pip 安装额外参数                                    |
| `sing_box_updater_timer_enabled`                       | boolean | `true`                           | -                               | 是否启用自动更新 Timer                              |
| `sing_box_updater_timer_interval`                      | string  | `1d`                             | -                               | 自动更新间隔                                        |
| `sing_box_updater_timer_state`                         | string  | `started`                        | -                               | Timer 运行状态                                      |
| `sing_box_updater_service_state`                       | string  | `started`                        | -                               | Service 运行状态                                    |
| `sing_box_updater_service_active_state`                | list    | `["started", "restarted"]`       | -                               | 判定服务活跃的状态列表                              |
| `sing_box_github_proxy`                                | string  | `""`                             | `https://ghproxy.com/`          | GitHub 代理前缀, 用于加速规则下载                   |
| `sing_box_log_level`                                   | string  | `warn`                           | `info`                          | sing-box 日志等级                                   |
| `sing_box_mixed_port`                                  | integer | `7890`                           | -                               | HTTP/SOCKS 混合代理端口                             |
| `sing_box_tproxy_port`                                 | integer | `7895`                           | -                               | 透明代理端口                                        |
| `sing_box_cache_file_enabled`                          | boolean | `true`                           | -                               | 是否启用缓存文件                                    |
| `sing_box_cache_file_store_fakeip`                     | boolean | `true`                           | -                               | 是否缓存 FakeIP                                     |
| `sing_box_cache_file_store_rdrc`                       | boolean | `true`                           | -                               | 是否缓存拒收响应                                    |
| `sing_box_clash_api_secret`                            | string  | `""`                             | `Secret123`                     | Clash API 密钥                                      |
| `sing_box_clash_api_external_controller`               | string  | `0.0.0.0:9090`                   | -                               | Clash API 监听地址                                  |
| `sing_box_clash_api_external_ui`                       | string  | `yacd`                           | -                               | Clash API UI 目录名                                 |
| `sing_box_clash_api_external_ui_download_url`          | string  | `...`                            | -                               | Clash UI 下载地址                                   |
| `sing_box_clash_api_external_ui_reinstall`             | boolean | `false`                          | -                               | 是否强制重装 UI                                     |
| `sing_box_proxy_route_table`                           | integer | `224`                            | -                               | 路由表 ID                                           |
| `sing_box_proxy_mark`                                  | integer | `224`                            | -                               | fwmark 值                                           |
| `sing_box_route_default_mark`                          | integer | `225`                            | -                               | 默认路由 mark 值                                    |
| `sing_box_nftables_flow_offload`                       | boolean | `true`                           | -                               | 是否启用 nftables flow offloading                   |
| `sing_box_tcp_bbr_enabled`                             | boolean | `true`                           | -                               | 是否启用 TCP BBR                                    |
| `sing_box_sysctl_nf_conntrack`                         | boolean | `true`                           | -                               | 是否优化 conntrack 内核参数                         |
| `sing_box_sysctl_nf_conntrack_buckets`                 | integer | `65536`                          | -                               | conntrack buckets 大小                              |
| `sing_box_sysctl_nf_conntrack_max`                     | integer | `262144`                         | -                               | conntrack max 大小                                  |
| `sing_box_sysctl_nf_conntrack_tcp_timeout_established` | integer | `86400`                          | -                               | TCP 建立连接超时时间                                |
| `sing_box_dns_hosts_predefined`                        | dict    | `{...}`                          | 见 `defaults/main.yaml`         | 预定义的 hosts 记录                                 |
| `sing_box_dns_public_dns_servers`                      | list    | `[...]`                          | 见 `defaults/main.yaml`         | 公共 DNS 服务器列表 (DoT/DoH)                       |
| `sing_box_dns_internal_tag`                            | string  | `dns_internal`                   | -                               | 内网 DNS 服务器标签                                 |
| `sing_box_dns_internal_servers`                        | list    | `[]`                             | `["192.168.1.1"]`               | 内网 DNS 服务器 IP 列表                             |
| `sing_box_dns_final`                                   | string  | `dns_proxy`                      | -                               | 默认 DNS 出站 tag                                   |
| `sing_box_dns_strategy`                                | string  | `prefer_ipv4`                    | -                               | DNS 解析策略                                        |
| `sing_box_dns_disable_cache`                           | boolean | `false`                          | -                               | 禁用 DNS 缓存                                       |
| `sing_box_dns_disable_expire`                          | boolean | `false`                          | -                               | 禁用 DNS 过期                                       |
| `sing_box_dns_independent_cache`                       | boolean | `false`                          | -                               | 独立 DNS 缓存                                       |
| `sing_box_dns_cache_capacity`                          | integer | `65535`                          | -                               | DNS 缓存容量                                        |
| `sing_box_route_final`                                 | string  | `FINAL`                          | -                               | 路由兜底规则的 Outbound Tag                         |
| `sing_box_route_default_domain_resolver`               | string  | `dns_direct`                     | -                               | 用于解析 Outbound 域名的解析器                      |
| `sing_box_route_auto_detect_interface`                 | boolean | `true`                           | -                               | 自动检测接口                                        |
| `sing_box_custom_rejected_rule_set`                    | string  | `custom-rejected-rule-set`       | -                               | 自定义拒绝规则集 Tag                                |
| `sing_box_custom_rejected_rule_set_rules`              | list    | `[]`                             | `[{"domain_suffix": "ad.com"}]` | 自定义拒绝规则 (不含 IP)                            |
| `sing_box_custom_rejected_ip4`                         | list    | `[]`                             | `["10.0.0.0/8"]`                | 自定义拒绝 IPv4 CIDR                                |
| `sing_box_custom_rejected_ip6`                         | list    | `[]`                             | -                               | 自定义拒绝 IPv6 CIDR                                |
| `sing_box_custom_internal_rule_set`                    | string  | `custom-internal-rule-set`       | -                               | 自定义内网规则集 Tag                                |
| `sing_box_custom_internal_rule_set_dns`                | string  | `dns_internal`                   | -                               | 自定义内网规则集使用的 DNS                          |
| `sing_box_custom_internal_rule_set_rules`              | list    | `[]`                             | `[{"domain_suffix": "lan"}]`    | 自定义内网规则                                      |
| `sing_box_custom_bypassed_rule_set`                    | string  | `custom-bypassed-rule-set`       | -                               | 自定义放行规则集 Tag (Bypassed)                     |
| `sing_box_custom_bypassed_rule_set_dns`                | string  | `dns_direct`                     | -                               | 自定义放行规则集使用的 DNS (Bypassed)               |
| `sing_box_custom_bypassed_rule_set_rules`              | list    | `[]`                             | `[{"domain": "example.com"}]`   | 自定义放行规则 (不含 IP)                            |
| `sing_box_custom_bypassed_ip4`                         | list    | `[]`                             | -                               | 自定义放行 IPv4 CIDR (Bypassed)                     |
| `sing_box_custom_bypassed_ip6`                         | list    | `[]`                             | -                               | 自定义放行 IPv6 CIDR (Bypassed)                     |
| `sing_box_remote_rule_set_url_prefix`                  | string  | `...`                            | -                               | 远程规则集下载 URL 前缀                             |
| `sing_box_remote_rule_set_update_interval`             | string  | `30d`                            | -                               | 远程规则集更新间隔                                  |
| `sing_box_remote_rule_sets`                            | list    | `[...]`                          | 见 `defaults/main.yaml`         | 启用的远程规则集列表                                |
| `sing_box_basic_dns_rules`                             | list    | `[...]`                          | 见 `defaults/main.yaml`         | 基础 DNS 分流规则                                   |
| `sing_box_basic_route_rules`                           | list    | `[...]`                          | 见 `defaults/main.yaml`         | 基础路由分流规则 (DNS 劫持等)                       |
| `sing_box_filtering_route_rules`                       | list    | `[...]`                          | 见 `defaults/main.yaml`         | 应用层过滤/分流规则                                 |
| `sing_box_proxy_groups`                                | list    | `[...]`                          | 见 `defaults/main.yaml`         | 这里定义 Proxy Groups (Selector 列表)               |
| `sing_box_auto_groups`                                 | list    | `[...]`                          | 见 `defaults/main.yaml`         | 基于正则自动分组的配置                              |
| `sing_box_selector_groups`                             | list    | `[...]`                          | 见 `defaults/main.yaml`         | 基于正则的手动选择分组配置                          |

### 内部变量 (Template Internal)

以下变量由其他变量计算得出, 通常只能只读, 不建议修改.

| 变量名                             | 描述                                           |
| :--------------------------------- | :--------------------------------------------- |
| `_sing_box_enable_tproxy`          | 是否启用 TProxy 功能 (mixed 模式为 false)      |
| `_sing_box_enable_nftables`        | 是否配置 nftables (mixed 模式为 false)         |
| `_sing_box_enable_ip_forward`      | 是否开启 IP Forwarding (仅 gateway 模式开启)   |
| `_sing_box_enable_netplan_routing` | 是否配置 Netplan 策略路由 (mixed 模式为 false) |
| `_sing_box_enable_ipv6`            | 是否检测到 IPv6 接口                           |
