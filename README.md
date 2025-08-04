# sing-box-tproxy

## 项目简介

本项目使用 Ansible 将 [SagerNet/sing-box](https://github.com/SagerNet/sing-box) 配置为 [Tproxy](https://sing-box.sagernet.org/configuration/inbound/tproxy/) 模式透明代理.

## 项目结构

### PyPI package [sing-box-config](https://pypi.org/project/sing-box-config/)

sing-box-config 只是整个项目中用于生成 sing-box 配置文件的一部分.

由于 [SagerNet/sing-box](https://github.com/SagerNet/sing-box) 不像 [Dreamacro/clash](https://github.com/Dreamacro/clash) 那样支持 proxy-providers, 因此在使用第三方的代理节点时, 需要自行处理节点更新. 再加上我有一些自定义 routes 和 proxy groups 的需求, 于是编写了这个 sing-box-config, 用于定时更新 sing-box 配置文件.

sing-box-config 需要读取 `config/` 目录下的两个 Jinja2 template, Ansible 将其渲染为 .json 文件作为 sing-box-config 工具的输入文件, 根据 subscriptions.url 获取到 proxies 后将两个 .json 文件合并为最终的 /etc/sing-box/config.json 文件.

- [config/base.json.j2](./config/base.json.j2)
  - sing-box 的基础配置文件, 包含 `dns`, `route` 和 `inbounds` 等不容易发生变更的配置段
- [config/subscriptions.json.j2](./config/subscriptions.json.j2)
  - `subscriptions` 配置是 sing-box-config 工具的自定义配置段, 合并最终配置文件前会被移除
  - `subscriptions.type` 当前仅支持 Shadowsocks `SIP002`, 后续如有需求可另行适配
  - `outbounds` 配置段中包含一些按地区分组与预定义的 proxy groups

### playbook.yaml 与 Ansible roles

- [playbook.yaml](./playbook.yaml) 是 ansible-playbook 的入口文件.
  - 在 playbook 的 tasks 中使用 `import_role` 静态导入了项目中的 Ansible roles.
  - 使用 Ansible roles 封装复杂任务可以简化 playbook 的结构.
- [roles/sing_box_install](./roles/sing_box_install/)
  - 用于在远程主机上设置 sing-box 的 apt 仓库并安装 sing-box.
- [roles/sing_box_config](./roles/sing_box_config/)
  - 在远程主机上创建 proxy 用户和工作目录
  - 安装 sing-box-config 命令行工具
  - 可选配置 sing-box-config-updater.timer 以实现定时更新 sing-box config.json
- [roles/sing_box_tproxy](./roles/sing_box_tproxy/)
  - 用于将远程主机配置为 Tproxy 模式的透明代理.
  - 包括加载必要的内核模块, 启用 IP 转发, 配置 nftables 防火墙规则, 开启 TCP BBR 拥塞控制协议等.
  - 配置 sing-box-reload.path 监听 /etc/sing-box/config.json 文件的变化, 如发生变化则 reload sing-box 进程

## 使用指南

要顺利使用本项目, 需要具备一定的 Linux 和 Ansible 基础. 如果您对 Ansible 完全不了解, 可以参考 [Getting started with Ansible](https://docs.ansible.com/ansible/latest/getting_started/index.html) 快速入门.

1. 安装 Ansible:
   使用 `pipx` 安装 Ansible, 具体步骤请参考 [Installing and upgrading Ansible with pipx](https://docs.ansible.com/ansible/latest/installation_guide/intro_installation.html#installing-and-upgrading-ansible-with-pipx), 注意安装后将 `${HOME}/.local/bin` 目录加入系统 PATH,

   ```ShellSession
   $ pipx install --include-deps ansible
     installed package ansible 11.5.0, installed using Python 3.11.2
   ```

2. 配置 Linux 虚拟机, SSH credentials 和 [Ansible Inventory](https://docs.ansible.com/ansible/latest/inventory_guide/intro_inventory.html). 以下是示例配置:

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

3. 验证主机连接:

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

4. 修改 `config/subscriptions.json.j2` 文件中的 `subscriptions` 配置段, 注意将示例配置中的 example 和 url 替换为真实的值, 目前 type 仅支持 Shadowsocks `SIP002`.

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

5. 执行 playbook.yaml:

   ```ShellSession
   $ ansible-playbook playbook.yaml -e 'playbook_hosts=pve-sing-box-tproxy'
   ```

## 参考资料

- [sing-box](https://github.com/SagerNet/sing-box)
- [Tproxy](https://sing-box.sagernet.org/configuration/inbound/tproxy/)
- [sing-box tproxy](https://lhy.life/20231012-sing-box-tproxy/)
- [SagerNet/serenity](https://github.com/SagerNet/serenity)
- [SIP002](https://github.com/shadowsocks/shadowsocks-org/wiki/SIP002-URI-Scheme)
