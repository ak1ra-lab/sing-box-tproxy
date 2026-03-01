# sing-box-tproxy

[![GitHub Actions Workflow Status](https://img.shields.io/github/actions/workflow/status/ak1ra-lab/sing-box-tproxy/.github%2Fworkflows%2Fpublish-to-pypi.yaml)](https://github.com/ak1ra-lab/sing-box-tproxy/actions/workflows/publish-to-pypi.yaml)
[![PyPI - Version](https://img.shields.io/pypi/v/sing-box-config)](https://pypi.org/project/sing-box-config/)
[![PyPI - Version](https://img.shields.io/pypi/v/sing-box-config?label=test-pypi&pypiBaseUrl=https%3A%2F%2Ftest.pypi.org)](https://test.pypi.org/project/sing-box-config/)
[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/ak1ra-lab/sing-box-tproxy)

使用 Ansible 自动部署 [SagerNet/sing-box](https://github.com/SagerNet/sing-box) TPROXY 透明代理.

## 特性

- 🚀 支持三种 sing-box 客户端部署模式
- 🔄 支持节点订阅与更新
- 🔨 支持 sing-box 服务端部署

## 快速开始

### 前置要求

- 目标主机: Debian/Ubuntu Linux
- Ansible core >= 2.18

### sing-box-tproxy 旁路网关部署 (sidecar gateway)

在安装了 Ansible 的主机上 git clone 本仓库,

```shell
git clone https://github.com/ak1ra-lab/sing-box-tproxy.git
cd sing-box-tproxy/
```

参考示例 Ansible inventory 编辑适用于自己环境的 inventory,

```shell
# 复制示例 Ansible inventory
cp inventory/hosts.example.yaml inventory/hosts.yaml

# 对示例 Ansible inventory 做必要变更
vim inventory/hosts.yaml
```

为 sing-box-tproxy 创建 group_vars,
与具体服务器无关的 公共配置项 可定义在 group_vars 中, 如节点订阅信息 (`sing_box_subscriptions: {}`),
而服务器特有的 私有配置项 则需要定义在 host_vars 中, sing-box-tproxy 场景中可能不需要 host_vars,

```shell
# 复制 roles/sing_box_defaults 中提供的默认配置作为 group_vars 模板
mkdir -p playbooks/group_vars/sing-box-tproxy
cp roles/sing_box_defaults/defaults/main.yaml playbooks/group_vars/sing-box-tproxy/main.yaml

# 对 group_vars 做必要变更 (可根据需要删除保持默认值的配置项)
vim playbooks/group_vars/sing-box-tproxy/main.yaml
```

完成变更后, 生成 group_vars 相对于默认配置的 patch 文件, 以便后续同步上游变更时复用:

```shell
./group_vars.sh gen tproxy
```

当 `roles/sing_box_defaults/defaults/main.yaml` 有上游变更需要同步时:

```shell
./group_vars.sh sync tproxy
```

执行 playbook 部署 sing-box-tproxy 透明代理,

```shell
ansible-playbook playbooks/sing_box_tproxy.yaml -v
```

登录 sing-box-tproxy node 验证服务状态,
重点关注 sing-box 各 systemd service 状态, nftables ruleset, ip rule 与 ip route 等,

```shell
ssh sing-box-tproxy-node01

systemctl status sing-box*
nft list ruleset
ip rule
ip route show table 224
```

## sing-box-server 服务端部署

本项目也提供了快速部署 sing-box 服务端的功能 (Shadowsocks, Trojan, Hysteria2 等).

参考示例 Ansible inventory 编辑适用于自己环境的 inventory, 与上面步骤一致不再赘述;

为 sing-box-server 创建 group_vars, 与具体服务器无关的 公共配置项 可定义在 group_vars 中, 而服务器特有的 私有配置项 如 region 和 hostname 则需要定义在 host_vars 中,

```shell
# 复制 roles/sing_box_server 中提供的默认配置作为 group_vars 模板
mkdir -p playbooks/group_vars/sing-box-server
cp roles/sing_box_server/defaults/main.yaml playbooks/group_vars/sing-box-server/main.yaml

# 对 group_vars 做必要变更
vim playbooks/group_vars/sing-box-server/main.yaml
```

完成变更后生成 patch 文件; 当上游默认值有变更时执行 sync 重新应用差异:

```shell
./group_vars.sh gen server   # 生成 / 刷新 patch
./group_vars.sh sync server  # 同步上游变更后重新应用 patch
```

```shell
# 创建 host_vars (如需覆盖通用配置)
mkdir -p playbooks/host_vars/sing-box-server-node01

# touch playbooks/host_vars/sing-box-server-node01/main.yaml
# 对 host_vars 做必要变更
# vim playbooks/host_vars/sing-box-server-node01/main.yaml
```

执行 playbook, playbooks/sing_box_server.yaml 会在 config/client_outbounds 目录下生成客户端配置文件,

```shell
ansible-playbook playbooks/sing_box_server.yaml -v
```

playbooks/sing_box_tproxy.yaml 在执行时会尝试将 config/client_outbounds 目录复制到 sing-box-tproxy 主机的 /var/lib/sing-box 目录下,
因此可以把当前刚部署好的 sing-box-server 的 静态客户端配置 添加到 `sing_box_subscriptions` 中,

```shell
vim playbooks/group_vars/sing-box-tproxy/main.yaml
```

如下, 路径相对于 sing-box 的 WorkingDirectory 即 /var/lib/sing-box,

```yaml
sing_box_subscriptions:
  sing-box-server-node01:
    type: local
    format: sing-box
    enabled: true
    path: "config/client_outbounds/sing-box-server-node01.outbounds.json"
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
│   ├── sing_box_defaults/   # ansible vars 配置项
│   ├── sing_box_validation/ # 校验 ansible vars 的 validation tasks
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
