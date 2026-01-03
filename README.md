# sing-box-tproxy

![GitHub Actions Workflow Status](https://img.shields.io/github/actions/workflow/status/ak1ra-lab/sing-box-tproxy/.github%2Fworkflows%2Fpublish-to-pypi.yaml)
![PyPI - Downloads](https://img.shields.io/pypi/dm/sing-box-config)
![PyPI - Version](https://img.shields.io/pypi/v/sing-box-config)
[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/ak1ra-lab/sing-box-tproxy)

使用 Ansible 自动部署 [SagerNet/sing-box](https://github.com/SagerNet/sing-box) TPROXY 透明代理.

## 特性

- 🚀 三种部署模式: mixed (代理) / local (本机透明代理) / gateway (网关)
- 🔄 自动订阅更新与节点管理
- ⚙️ systemd 服务与配置热重载
- 🛡️ nftables + fwmark 策略路由
- 📦 Python 配置生成工具 ([PyPI](https://pypi.org/project/sing-box-config/))

## 部署模式

| 模式      | 场景     | 透明代理 | IP 转发 | TPROXY 监听 |
| --------- | -------- | -------- | ------- | ----------- |
| `mixed`   | 手动代理 | ❌       | ❌      | N/A         |
| `local`   | 工作站   | ✅ 本机  | ❌      | 127.0.0.1   |
| `gateway` | 网关     | ✅ 全网  | ✅      | 0.0.0.0     |

注意:

- ansible playbook 中的 vars 优先级高于 `host_vars`
- gateway 模式下 TPROXY 必须监听 0.0.0.0 以处理来自局域网设备的流量.

## 快速开始

### 前置要求

- 目标主机: Debian/Ubuntu Linux
- Ansible core >= 2.18

### sing-box 透明代理网关部署

1. 克隆仓库, Python 项目使用 uv 构建, 主机中需安装 uv

   ```shell
   git clone https://github.com/ak1ra-lab/sing-box-tproxy.git
   cd sing-box-tproxy/
   ```

2. 配置 inventory

   ```shell
   vim inventory/hosts.yaml
   ```

   内容示例:

   ```yaml
   sing-box-tproxy:
     hosts:
       pve-sing-box-tproxy-254:
   ```

3. 准备 group_vars 并在其中添加订阅信息

   ```shell
   vim playbooks/group_vars/sing-box-tproxy/main.yaml
   ```

   内容示例:

   ```yaml
   sing_box_config_subscriptions:
     provider01:
       type: remote
       format: sip002
       enabled: true
       url: "https://example.com/api/subscribe?token=xxx"
   ```

4. 执行部署

   ```shell
   ansible-playbook playbooks/sing_box_tproxy.yaml -v
   ```

5. 验证服务

   ```shell
   ssh pve-sing-box-tproxy-254

   systemctl status sing-box*
   nft list ruleset
   ip rule
   ip route show table 224
   ```

## sing-box 服务端部署

本项目也提供了快速部署 sing-box 服务端的功能 (Shadowsocks, Trojan, Hysteria2 等).

1. 配置 inventory

   ```yaml
   sing-box-server:
     hosts:
       vps-node01:
   ```

2. 在 group_vars 准备公共配置项, 在 host_vars 中准备服务器特有的配置项

   ```shell
   vim playbooks/group_vars/sing-box-server/main.yaml
   vim playbooks/host_vars/vps-node01/main.yaml
   ```

   如下面与服务器无关的 ansible vars 可定义在 group_vars 中,

   ```yaml
   sing_box_server_user_count: 1

   # Enable protocols
   sing_box_server_enable_shadowsocks: true
   sing_box_server_enable_trojan: true
   sing_box_server_enable_hysteria2: true
   sing_box_server_enable_vless: false
   sing_box_server_enable_tuic: false

   # TLS with ACME DNS-01
   sing_box_server_tls_mode: acme
   sing_box_server_acme_email: "acme@example.com"
   sing_box_server_acme_use_dns01: true
   sing_box_server_acme_dns01_provider: cloudflare
   sing_box_server_acme_dns01_cloudflare_api_token: "<replace-with-your-cloudflare-token>"
   ```

   而服务器特有的 vars 如 region 和 hostname 则可定义在 host_vars 中,

   ```yaml
   sing_box_server_region: us
   sing_box_server_hostname: "vps-node01.example.com"
   ```

3. 执行部署, playbook 会在 config/client_outbounds 目录下生成客户端配置文件,

   ```shell
   ansible-playbook playbooks/sing_box_server.yaml -v
   ```

   后续可以把当前服务器的配置添加到 `sing_box_config_subscriptions` 中, 如,

   ```shell
   vim playbooks/group_vars/sing-box-tproxy/main.yaml
   ```

   ```yaml
   sing_box_config_subscriptions:
     vps-node01:
       type: local
       format: sing-box
       enabled: true
       path: "config/client_outbounds/vps-node01.outbounds.json"
   ```

## 文档

详细文档请参考:

- `docs/architecture.md`
  - 架构设计, 透明代理原理, fwmark 机制, nftables 规则详解

## 项目结构

```
sing-box-tproxy/
├── src/sing_box_config/     # Python 配置生成工具
├── playbooks/               # playbooks 目录
│   ├── sing_box_tproxy.yaml # sing-box 透明代理 playbook
│   └── sing_box_server.yaml # sing-box 服务端部署 playbook
├── roles/                   # Ansible 角色
│   ├── sing_box_install/    # 安装 sing-box
│   ├── sing_box_config/     # 安装 Python 配置生成工具
│   ├── sing_box_tproxy/     # 透明代理 (nftables/策略路由)
│   └── sing_box_server/     # 创建 sing-box 服务端配置文件
├── docs/                    # 文档
│   └── architecture.md      # 架构设计文档
└── README.md                # 本文件
```

## License

MIT License. See `LICENSE` file for details.

## 参考资料

- [sing-box 官方文档](https://sing-box.sagernet.org/)
- [sing-box tproxy inbound](https://sing-box.sagernet.org/configuration/inbound/tproxy/)
- [sing-box tproxy 透明代理教程](https://lhy.life/20231012-sing-box-tproxy/)
- [nftables wiki](https://wiki.nftables.org/)
- [SIP002 URI Scheme](https://github.com/shadowsocks/shadowsocks-org/wiki/SIP002-URI-Scheme)
- [Ansible Documentation](https://docs.ansible.com/)
