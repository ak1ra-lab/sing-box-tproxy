# Changelog

All notable changes to this project will be documented in this file.

## [0.5.0] - 2025-11-01

### 🚀 Features

- migrate pdm to uv and many more

### 🚜 Refactor

- impl roles/sing_box_defaults/defaults/main.yml

### ⚙️ Miscellaneous Tasks

- impl sing_box_config_updater_service_state on roles/sing_box_config
- rename playbook.yaml to site.yaml
- update pdm.lock
- update setup_logger
- add enabled option on subscriptions
- add status shields.io badges
- remove download_detour on config/base.json.j2
- update dns_fakeip on config/base.json.j2
- rename pdm_wheel.yml to dist_wheel.yml

## [0.4.0] - 2025-08-04

### 🚀 Features

- impl tcp_bbr_enabled on roles/sing_box_tproxy
- impl remove_invalid_outbounds on src/sing_box_config

### 🚜 Refactor

- handle config/{base,subscriptions}.json as jinja2 template
- simplify roles/sing_box_config
- simplify roles/sing_box_tproxy

### 📚 Documentation

- update README.md

### ⚙️ Miscellaneous Tasks

- add sing_box_config_updater_timer_enabled on playbook.yaml
- impl tasks/pdm_wheel.yml on roles/sing_box_config
- impl sing_box_config_install_source on roles/sing_box_config
- bump version

## [0.3.0] - 2025-08-04

### 🚀 Features

- impl fetch_url_with_retries on httpx.get()

### 🐛 Bug Fixes

- add ExecStartPre= on sing-box-reload.service

### ⚙️ Miscellaneous Tasks

- bump version

## [0.2.1] - 2025-08-04

### 🐛 Bug Fixes

- fix hard coded netplan default INTERFACE

### ⚙️ Miscellaneous Tasks

- typo fix on ansible.cfg
- fixup and improvement
- fixup nftables.conf.j2
- bump version

## [0.2.0] - 2025-08-04

### 🚀 Features

- *(ansible)* use proxy user to exec sing-box-config-updater.timer
- *(ansible)* ensure sing-box package present instead of latest
- *(ansible)* set apt_repo_packages to sing-box instead of sing-box-beta
- *(ansible)* set apt_repo_packages default to sing-box-beta on playbook.yaml
- *(ansible)* mark proxy user traffic and reorder nft rules

### 📚 Documentation

- add git-cliff generated CHANGELOG.md

### ⚙️ Miscellaneous Tasks

- *(config)* remove route.default_mark on config/base.json
- add git-cliff config cliff.toml

## [0.1.6] - 2025-04-28

### 🚀 Features

- *(src)* disable logfile logging

### ⚙️ Miscellaneous Tasks

- pdm update
- add pre-commit as dev dependencies
- add .pre-commit-config.yaml
- remove verbose output on nox lint session

## [0.1.5] - 2025-04-27

### 📚 Documentation

- update README.md

### ⚙️ Miscellaneous Tasks

- include Ansible roles and config example in Python .whl
- fix pdm.build.includes

## [0.1.3] - 2025-04-27

### 📚 Documentation

- remove English README.md

### ⚙️ Miscellaneous Tasks

- update .gitignore to ignore .pdm-python

## [0.1.2] - 2025-04-27

### 🚀 Features

- *(ansible)* install sing-box-config from PyPI
- *(ansible)* ensure sing-box.service restarted
- *(src)* relocate code to src/sing_box_config
- *(ansible)* relocate ansible roles
- *(ansible)* use fullpath in sing-box-config-updater.service

### ⚙️ Miscellaneous Tasks

- build package distributions on tests.yaml
- update .github/workflows/pypi-publish.yaml

## [0.1.1] - 2025-04-25

### 📚 Documentation

- add project.urls in pyproject.toml
- replace urls in README.md

### ⚙️ Miscellaneous Tasks

- revert disable shallow clone

## [0.1.0] - 2025-04-25

### 🚀 Features

- *(src)* pdm init
- *(src)* chore: init commit on src/singbox_tproxy
- *(src)* add add subscriptions.exclude support
- *(src)* add verbose on save_config_from_subscriptions
- *(src)* python package rename
- *(src)* add default value on cli --help
- *(src)* fix cmd output.parent dir not exists
- *(ansible)* add ansible.cfg
- *(ansible)* implement roles/singbox_install
- *(ansible)* implement roles/singbox_tproxy
- *(ansible)* implement roles/singbox_config
- *(ansible)* add ansible playbook.yaml
- *(ansible)* use root user to exec sing-box-config-updater.timer
- *(ansible)* add sing-box-reload.path to watch /etc/sing-box/config.json changes on roles/singbox_tproxy
- *(ansible)* implement more handler on roles/singbox_tproxy
- *(src)* use logger.warning instead of raise ValueError
- *(ansible)* ensure template notify more accurate
- *(ansible)* dont change systemd service unit ownership
- *(src)* pass argparse.Namespace on cmd.py
- *(ansible)* reuse roles/singbox_install
- *(src)* add error handling on resp.text decode
- *(src)* implement logging.setup_logger
- *(ansible)* ensure run_once on pdm build task
- *(src)* set default value for tag_prefix in decode_sip002_to_singbox function

### 📚 Documentation

- update README.md
- add README.zh-CN.md
- translate README.zh-CN.md into English
- replace full-width punctuations with half-width on README.zh-CN.md
- update README.zh-CN.md
- update README.md

### 🧪 Testing

- add unit tests for decode_sip002_to_singbox function

### ⚙️ Miscellaneous Tasks

- init commit
- add noxfile.py and ruff.toml
- *(config)* add config/base.json
- *(config)* add example config/subscriptions.json
- *(config)* fix dns_resolver detour to an empty direct
- add .github/workflows
- *(config)* replace route.rule_set github-proxy on config/base.json
- *(config)* append urltest proxy group
- add .github/prompts/*.md to .gitignore
- disable shallow clone

### 💼 Other

- fix project.name to sing-box-config

<!-- generated by git-cliff -->
