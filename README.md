# sing-box-tproxy

[![GitHub Actions Workflow Status](https://img.shields.io/github/actions/workflow/status/ak1ra-lab/sing-box-tproxy/.github%2Fworkflows%2Fpublish-to-pypi.yaml)](https://github.com/ak1ra-lab/sing-box-tproxy/actions/workflows/publish-to-pypi.yaml)
[![PyPI - Version](https://img.shields.io/pypi/v/sing-box-config)](https://pypi.org/project/sing-box-config/)
[![PyPI - Version](https://img.shields.io/pypi/v/sing-box-config?label=test-pypi&pypiBaseUrl=https%3A%2F%2Ftest.pypi.org)](https://test.pypi.org/project/sing-box-config/)
[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/ak1ra-lab/sing-box-tproxy)

使用 Ansible 自动部署 [SagerNet/sing-box](https://github.com/SagerNet/sing-box) TPROXY 透明代理.

## 特性

- 支持三种客户端部署模式: `gateway` (旁路网关), `local` (本机代理), `mixed` (混合代理)
- 支持多种订阅格式: sing-box 原生格式, SIP002 (Shadowsocks)
- 支持 sing-box 服务端部署: Shadowsocks, Trojan, Hysteria2, VLESS, TUIC
- 内置 `sing-box-liveness-probe`: 定期探活, 超过阈值后自动重启服务

## 前置要求

- 目标主机: Debian/Ubuntu Linux
- Ansible core >= 2.18

## 快速开始

```shell
git clone https://github.com/ak1ra-lab/sing-box-tproxy.git
cd sing-box-tproxy/

# 复制并编辑 inventory
cp inventory/hosts.example.yaml inventory/hosts.yaml
vim inventory/hosts.yaml

# 创建并编辑 group_vars
mkdir -p playbooks/group_vars/sing-box-tproxy
cp roles/sing_box_defaults/defaults/main.yaml playbooks/group_vars/sing-box-tproxy/main.yaml
vim playbooks/group_vars/sing-box-tproxy/main.yaml

# 生成 group_vars patch 文件
./group_vars.sh gen tproxy

# 部署
ansible-playbook playbooks/sing_box_tproxy.yaml -v
```

详细部署指南:

- [透明代理 (tproxy) 部署](docs/deploy-tproxy.md)
- [服务端 (server) 部署](docs/deploy-server.md)
- [重置 sing-box 部署](docs/reset.md)
- [Ansible 变量说明](docs/ansible_vars.md)
- [架构设计与透明代理原理](docs/architecture.md)

## 项目结构

```
sing-box-tproxy/
├── src/sing_box_config/     # Python 配置生成工具 (sing-box-config / sing-box-liveness-probe)
├── playbooks/               # Ansible playbooks
│   ├── group_vars/          # 各 inventory 组的公共变量
│   ├── host_vars/           # 主机级别的变量覆盖
│   ├── sing_box_tproxy.yaml # 部署 sing-box 透明代理
│   ├── sing_box_server.yaml # 部署 sing-box 服务端
│   └── sing_box_reset.yaml  # 重置 (撤销) sing-box 部署
├── roles/                   # Ansible 角色
│   ├── sing_box_defaults/   # 所有变量的默认值 (单一数据源)
│   ├── sing_box_validation/ # 校验 Ansible 变量的合法性
│   ├── sing_box_install/    # 通过 SagerNet APT 仓库安装 sing-box
│   ├── sing_box_config/     # 安装 sing-box-config 并配置定时更新
│   ├── sing_box_tproxy/     # 配置 nftables 与路由策略 (透明代理)
│   ├── sing_box_server/     # 生成服务端配置文件及客户端出站配置
│   └── sing_box_reset/      # 撤销 tproxy / server 部署
├── config/                  # 本地生成的配置文件
│   └── client_outbounds/    # sing_box_server 生成的客户端出站文件
├── inventory/               # Ansible inventory
│   └── hosts.yaml           # 目标主机列表
└── docs/                    # 文档
    ├── deploy-tproxy.md     # 透明代理 (tproxy) 部署指南
    ├── deploy-server.md     # 服务端 (server) 部署指南
    ├── reset.md             # 重置 sing-box 部署
    ├── architecture.md      # 架构设计, 透明代理原理, fwmark 与 nftables 详解
    └── ansible_vars.md      # 所有 Ansible 变量说明
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
