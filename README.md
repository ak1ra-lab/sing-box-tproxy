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

## 快速开始

### 前置要求

- 目标主机: Debian/Ubuntu Linux
- Ansible core >= 2.18

### 基本部署

1. 克隆仓库

   ```shell
   git clone https://github.com/ak1ra-lab/sing-box-tproxy.git
   cd sing-box-tproxy
   ```

2. 配置 inventory

   编辑 `~/.ansible/inventory/hosts.yaml`:

   ```yaml
   all:
     hosts:
       gateway:
         ansible_host: 10.0.42.253
         ansible_user: debian
   ```

3. 添加订阅

   ```shell
   ansible-vault create host_vars/gateway.yml
   ```

   内容示例:

   ```yaml
   sing_box_config_subscriptions:
     provider:
       type: SIP002
       enabled: true
       url: "https://example.com/api/subscribe?token=xxx"
   ```

4. 执行部署

   ```shell
   ansible-playbook site.yaml --ask-vault-pass
   ```

5. 验证服务

   ```shell
   ssh gateway
   systemctl status sing-box
   ```

## 部署模式

| 模式      | 场景     | 透明代理 | IP 转发 | TPROXY 监听 |
| --------- | -------- | -------- | ------- | ----------- |
| `mixed`   | 手动代理 | ❌       | ❌      | N/A         |
| `local`   | 工作站   | ✅ 本机  | ❌      | 127.0.0.1   |
| `gateway` | 网关     | ✅ 全网  | ✅      | 0.0.0.0     |

配置方式: 在 `site.yaml` 或 `host_vars/` 目录下设置 `sing_box_mode` 变量.

> 注意:
>
> - Ansible Playbook 中的 vars 优先级高于 `host_vars/`.
> - gateway 模式下 TPROXY 必须监听 0.0.0.0 以处理来自局域网设备的流量.

## 文档

详细文档请参考:

- `docs/architecture.md`
  - 架构设计, 透明代理原理, fwmark 机制, nftables 规则详解

## 项目结构

```
sing-box-tproxy/
├── src/sing_box_config/     # Python 配置生成工具
├── roles/                   # Ansible 角色
│   ├── sing_box_install/    # 安装 sing-box
│   ├── sing_box_config/     # 配置管理
│   └── sing_box_tproxy/     # 透明代理 (nftables/策略路由)
├── docs/                    # 文档
│   └── architecture.md      # 架构设计文档
├── site.yaml                # Playbook 入口
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
