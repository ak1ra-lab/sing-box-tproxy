# sing-box-tproxy

[English](https://github.com/ak1ra-lab/sing-box-tproxy/blob/master/README.md) | [简体中文](https://github.com/ak1ra-lab/sing-box-tproxy/blob/master/README.zh-CN.md)

## Project Overview

This project uses Ansible to configure [SagerNet/sing-box](https://github.com/SagerNet/sing-box) as a transparent proxy in [Tproxy](https://sing-box.sagernet.org/configuration/inbound/tproxy/) mode, which can be used as a bypass gateway.

## Project Structure

### playbook.yaml and Ansible roles

- [playbook.yaml](https://github.com/ak1ra-lab/sing-box-tproxy/blob/master/playbook.yaml) is the entry file for ansible-playbook.
  - The tasks in the playbook use `import_role` to statically import the Ansible roles in the project.
  - Using Ansible roles to encapsulate complex tasks simplifies the structure of the playbook.
- [roles/sing_box_install](https://github.com/ak1ra-lab/sing-box-tproxy/blob/master/roles/sing_box_install/)
  - Used to set up the apt repository for sing-box on the remote host and install sing-box.
- [roles/sing_box_config](https://github.com/ak1ra-lab/sing-box-tproxy/blob/master/roles/sing_box_config/)
  - Creates a proxy user and working directory on the remote host.
  - Installs the `sing-box-config` command-line tool.
  - Configures the `sing-box-config-updater.timer` to periodically execute the `sing-box-config` tool, enabling updates to the sing-box `config.json`.
- [roles/sing_box_tproxy](https://github.com/ak1ra-lab/sing-box-tproxy/blob/master/roles/sing_box_tproxy/)
  - Configures the remote host as a transparent proxy in Tproxy mode.
  - Includes loading necessary kernel modules, enabling IP forwarding, and configuring nftables firewall rules.
  - Configures `sing-box-reload.path` to monitor changes to the `/etc/sing-box/config.json` file and reload the sing-box process when changes occur.

### `sing-box-config` and src/sing_box_config

Since [SagerNet/sing-box](https://github.com/SagerNet/sing-box) does not support proxy-providers like [Dreamacro/clash](https://github.com/Dreamacro/clash), you need to handle proxy node updates yourself when using third-party proxy nodes. The project [SagerNet/serenity](https://github.com/SagerNet/serenity) implements a configuration generator for sing-box, but due to its lack of documentation and configuration examples, it is difficult to create a working configuration file. Additionally, custom proxy group requirements led to the development of a configuration generator tailored to current needs.

`sing-box-config` requires two configuration files in the `config/` directory:

- [config/base.json](https://github.com/ak1ra-lab/sing-box-tproxy/blob/master/config/base.json)
  - The base configuration file for sing-box, including `dns`, `route`, and `inbounds` sections.
- [config/subscriptions.json](https://github.com/ak1ra-lab/sing-box-tproxy/blob/master/config/subscriptions.json)
  - The `subscriptions` section is not part of sing-box but is a custom section for the `sing-box-config` tool.
  - Currently, the `type` in `subscriptions` only supports the [SIP002](https://github.com/shadowsocks/shadowsocks-org/wiki/SIP002-URI-Scheme) format, with plans to extend support based on future needs.
  - The `outbounds` section contains some predefined proxy groups and proxy groups grouped by region, which automatically creates `selector` and `urltest` types of `outbounds`.

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
         "exclude": ["过期|Expire|\\d+(\\.\\d+)? ?GB|流量|Traffic|QQ群|官网|Premium"],
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
