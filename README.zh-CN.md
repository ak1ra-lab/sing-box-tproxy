# sing-box-tproxy

[English](./README.md) | [简体中文](./README.zh-CN.md)

## 项目简介

本项目通过 Ansible 将 [SagerNet/sing-box](https://github.com/SagerNet/sing-box) 配置为 [Tproxy](https://sing-box.sagernet.org/configuration/inbound/tproxy/) 模式的透明代理，可用作旁路网关。

## 项目原理

### playbook.yaml 与 Ansible roles

- [playbook.yaml](./playbook.yaml) 是 ansible-playbook 的入口文件。
  - 在 playbook 的 tasks 中使用 `import_role` 静态导入了项目中的 Ansible roles。
  - 使用 roles 封装复杂任务可以简化 playbook 的结构，推荐采用这种方式。
- [roles/singbox_install](./roles/singbox_install/)
  - 用于在远程主机上设置 sing-box 的 apt 仓库并安装 sing-box。
- [roles/singbox_config](./roles/singbox_config/)
  - 用于配置远程主机的基础环境。
  - 安装 `sing-box-config` 命令行工具。
- [roles/singbox_tproxy](./roles/singbox_tproxy/)
  - 用于将远程主机配置为 Tproxy 模式的透明代理。
  - 包括加载必要的内核模块、启用 IP 转发、配置 nftables 防火墙规则等。

### `sing-box-config`

由于 [SagerNet/sing-box](https://github.com/SagerNet/sing-box) 不像 [Dreamacro/clash](https://github.com/Dreamacro/clash) 那样支持 proxy-providers，因此在使用第三方代理节点时，需要自行解决节点更新问题。虽然 [SagerNet/serenity](https://github.com/SagerNet/serenity) 实现了一个 sing-box 的配置生成器，但由于它缺乏配置示例以及我自身存在的自定义需求，本项目使用 Python 编写了一个更简单的 sing-box 配置生成器。

`sing-box-config` 的代码位于 [src/singbox_config](./src/singbox_config/) 目录，使用 [pdm](https://github.com/pdm-project/pdm) 管理 Python 项目依赖。

此工具需要读取 `config` 目录下的两个配置文件：

- [config/base.json](./config/base.json)
  - sing-box 的基础配置文件，包括 `dns`、`route` 和 `inbounds` 等配置段。
- [config/subscriptions.json](./config/subscriptions.json)
  - 用于配置代理服务商和 `outbounds` 配置段。
  - 当前 `subscriptions` 的 `type` 仅支持 [SIP002](https://github.com/shadowsocks/shadowsocks-org/wiki/SIP002-URI-Scheme) 格式，后续可根据需求扩展支持。
  - `outbounds` 配置段包含预定义的 proxy groups 和按地区分组的 proxy groups。
  - 按地区分组的 proxy groups 通过 `filter` 列表中的正则表达式过滤从 `subscriptions.url` 获取的节点。
  - 按地区分组的 proxy groups 会自动创建 `selector` 和 `urltest` 类型的 `outbounds`。

## 使用指南

要顺利使用本项目，需要具备一定的 Linux 和 Ansible 基础。如果您对 Ansible 完全不了解，可以参考 [Getting started with Ansible](https://docs.ansible.com/ansible/latest/getting_started/index.html) 快速入门。

1. 安装 Ansible：
   使用 `pipx` 安装 Ansible，具体步骤请参考 [Installing and upgrading Ansible with pipx](https://docs.ansible.com/ansible/latest/installation_guide/intro_installation.html#installing-and-upgrading-ansible-with-pipx)。

   ```ShellSession
   $ pipx install --include-deps ansible
     installed package ansible 11.5.0, installed using Python 3.11.2
     These apps are now globally available
       - ansible
       - ansible-community
       - ansible-config
       - ansible-console
       - ansible-doc
       - ansible-galaxy
       - ansible-inventory
       - ansible-playbook
       - ansible-pull
       - ansible-test
       - ansible-vault
   ⚠️  Note: '/home/username/.local/bin' is not on your PATH environment variable. These apps will not be globally accessible until your PATH is updated. Run `pipx ensurepath` to automatically add it, or manually modify your PATH in your shell's config file (i.e. ~/.bashrc).
   done! ✨ 🌟 ✨
   ```

2. 配置 Linux 虚拟机、SSH 凭据和 [Ansible Inventory](https://docs.ansible.com/ansible/latest/inventory_guide/intro_inventory.html)。以下是示例：

   ```yaml
   # ~/.ansible/inventory/pve-sing-box-tproxy.yaml
   all:
     hosts:
       pve-sing-box-tproxy-253:
         ansible_host: 10.42.0.253
         ansible_user: debian

   pve-sing-box-tproxy:
     hosts:
       pve-sing-box-tproxy-253:
   ```

3. 验证主机连接：

   ```ShellSession
   $ ansible -m ping pve-sing-box-tproxy
   pve-sing-box-tproxy-253 | SUCCESS => {
       "ansible_facts": {
           "discovered_interpreter_python": "/usr/bin/python3"
       },
       "changed": false,
       "ping": "pong"
   }
   ```

4. 修改 `config/subscriptions.json` 文件中的 `subscriptions` 配置段，注意将示例配置中的 example 和 url 替换为真实的值，目前 type 仅支持 SIP002。

   ```json
   {
     "subscriptions": {
       "example": {
         "type": "SIP002",
         "exclude": [
           "过期|Expire|\\d+(\\.\\d+)? ?GB|流量|Traffic|QQ群|官网|Premium"
         ],
         "url": "https://sub.example.com/subscriptions.txt"
       }
     }
   }
   ```

5. 安装 `sing-box-config`：
   使用 `pipx` 安装，并运行 `sing-box-config` 生成初始配置文件。可通过 `--help` 查看帮助信息：

   ```ShellSession
   $ pipx install --include-deps sing-box-config

   $ sing-box-config --help
   usage: sing-box-config [-h] [-b base.json] [-s subscriptions.json] [-o config.json]

   The configuration generator for sing-box

   options:
     -h, --help            show this help message and exit
     -b base.json, --base base.json
                           sing-box base config, default: config/base.json
     -s subscriptions.json, --subscriptions subscriptions.json
                           sing-box subscriptions config with subscriptions and outbounds, default: config/subscriptions.json
     -o config.json, --output config.json
                           sing-box output config, default: config/config.json

   $ sing-box-config
   ```

6. 执行安装：

   ```ShellSession
   $ ansible-playbook playbook.yaml -e 'playbook_hosts=pve-sing-box-tproxy'
   ```

## 参考资料

- [sing-box](https://github.com/SagerNet/sing-box)
- [Tproxy](https://sing-box.sagernet.org/configuration/inbound/tproxy/)
- [sing-box tproxy](https://lhy.life/20231012-sing-box-tproxy/)
