# sing-box-tproxy

[English](./README.md) | [简体中文](./README.zh-CN.md)

## Project Overview

This project uses Ansible to configure [SagerNet/sing-box](https://github.com/SagerNet/sing-box) as a transparent proxy in [Tproxy](https://sing-box.sagernet.org/configuration/inbound/tproxy/) mode, which can be used as a bypass gateway.

## Project Principles

### playbook.yaml and Ansible roles

- [playbook.yaml](./playbook.yaml) is the entry file for ansible-playbook.
  - The tasks in the playbook use `import_role` to statically import the Ansible roles in the project.
  - Using roles to encapsulate complex tasks simplifies the structure of the playbook, which is a recommended practice.
- [roles/singbox_install](./roles/singbox_install/)
  - Used to set up the apt repository for sing-box on the remote host and install sing-box.
- [roles/singbox_config](./roles/singbox_config/)
  - Used to configure the basic environment on the remote host.
  - Installs the `sing-box-config` command-line tool.
- [roles/singbox_tproxy](./roles/singbox_tproxy/)
  - Used to configure the remote host as a transparent proxy in Tproxy mode.
  - Includes loading necessary kernel modules, enabling IP forwarding, and configuring nftables firewall rules.

### `sing-box-config`

Since [SagerNet/sing-box](https://github.com/SagerNet/sing-box) does not support proxy-providers like [Dreamacro/clash](https://github.com/Dreamacro/clash), you need to handle proxy node updates yourself when using third-party proxy nodes. Although [SagerNet/serenity](https://github.com/SagerNet/serenity) is a configuration generator for sing-box, due to its complexity and custom requirements, this project developed a simple tool called `sing-box-config`.

The code for `sing-box-config` is located in the [src/singbox_config](./src/singbox_config/) directory and uses [pdm](https://github.com/pdm-project/pdm) to manage Python project dependencies.

This tool requires two configuration files in the `config` directory:

- [config/base.json](./config/base.json)
  - The base configuration file for sing-box, including `dns`, `route`, and `inbounds` sections.
- [config/subscriptions.json](./config/subscriptions.json)
  - Used to configure proxy providers and the `outbounds` section.
  - Currently, the `type` in `subscriptions` only supports the [SIP002](https://github.com/shadowsocks/shadowsocks-org/wiki/SIP002-URI-Scheme) format, with plans to extend support based on future needs.
  - The `outbounds` section includes predefined proxy groups and region-based proxy groups.
  - Region-based proxy groups filter nodes obtained from `subscriptions.url` using regular expressions in the `filter` list.
  - Region-based proxy groups automatically create `selector` and `urltest` types of `outbounds`.

## Usage Guide

To use this project successfully, you need some basic knowledge of Linux and Ansible. If you are unfamiliar with Ansible, you can refer to [Getting started with Ansible](https://docs.ansible.com/ansible/latest/getting_started/index.html) for a quick introduction.

1. Install Ansible:
   Use `pipx` to install Ansible. Refer to [Installing and upgrading Ansible with pipx](https://docs.ansible.com/ansible/latest/installation_guide/intro_installation.html#installing-and-upgrading-ansible-with-pipx) for detailed steps.

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

2. Configure your Linux virtual machine, SSH credentials, and [Ansible Inventory](https://docs.ansible.com/ansible/latest/inventory_guide/intro_inventory.html). Below is an example:

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

3. Verify the connection to the host:

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

4. Modify the `subscriptions` section in the `config/subscriptions.json` file. Replace the example configuration with real values for `example` and `url`. Currently, only SIP002 is supported for `type`.

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

5. Install `sing-box-config`:
   Use `pipx` to install and run `sing-box-config` to generate the initial configuration file. Use the `--help` option to view help information:

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

6. Execute the installation:

   ```ShellSession
   $ ansible-playbook playbook.yaml -e 'playbook_hosts=pve-sing-box-tproxy'
   ```

## References

- [sing-box](https://github.com/SagerNet/sing-box)
- [Tproxy](https://sing-box.sagernet.org/configuration/inbound/tproxy/)
- [sing-box tproxy](https://lhy.life/20231012-sing-box-tproxy/)
