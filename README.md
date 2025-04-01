# sing-box-tproxy

## What is this?

This project uses Ansible to configure [SagerNet/sing-box](https://github.com/SagerNet/sing-box) as a [Tproxy](https://sing-box.sagernet.org/configuration/inbound/tproxy/) transparent proxy bypass gateway. Currently, the Ansible roles only support Debian Linux.

## Quick start

1. Install Ansible using `pipx` if it is not already installed.
2. Set up your Linux VM, SSH credentials, and Ansible inventory.
3. Run `ansible-playbook playbook.yaml`.

## What do we have?

- A Python 3 CLI script, `sing-box-config`:
  - Used to generate new sing-box configurations.
- Ansible roles to install, configure, and set up sing-box as a Tproxy gateway:
  - For details on the Ansible roles, refer to the [./roles](./roles/) directory.

## Reference

- [sing-box](https://github.com/SagerNet/sing-box)
- [Tproxy](https://sing-box.sagernet.org/configuration/inbound/tproxy/)
- [sing-box tproxy](https://lhy.life/20231012-sing-box-tproxy/)
