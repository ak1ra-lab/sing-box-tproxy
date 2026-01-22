# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.8.0] - 2026-01-22

### Added

- Migrate `sing_box_dns_rules` into sing_box_defaults
- Ansible variables `custom_bypassed_ip4` and `custom_bypassed_ip6` for custom bypass rules.
- Nftables flowtable offload support for reserved private IPs.
- Support for including external nftables configuration files.
- Configuration validation tasks for `sing_box_config` and `sing_box_tproxy` roles.
- Proxy caching mechanism in `sing_box_config` to optimize config generation.
- `nf_conntrack` kernel module loading task.
- Option to force reinstall Clash API external UI.
- Example configuration files for Ansible inventory, group_vars, and host_vars.
- Named GitHub Actions workflows.

### Changed

- Reorganized `sing_box_remote_rule_sets` and `sing_box_dns_rules`
- Renamed all Ansible YAML files from `.yml` to `.yaml`.
- Changed default `sing_box_log_level` to `warn`.
- Switched default `sing_box_config_install_source` to `pypi`.
- Updated `tcp_bbr` task to support custom sysctl configuration file.
- Updated client outbound path handling to use Ansible FQDN.
- Added packet counters to nftables rules.
- Standardized `nftables.conf` comments to English.
- Refactored `sing_box_tproxy` playbook and moved helper tasks.

### Fixed

- Improved priority of `DIRECT` route rules.
- Restricted `dns_fakeip` DNS rules to `A` and `AAAA` record types.
- Fixed conflict between `udp_over_tcp` and multiplexing in Shadowsocks outbounds.
- Fixed JSON serialization to preserve order in `sing-box` configuration.

## [0.7.0] - 2026-01-02

### Added

- New `sing_box_server` role for multi-protocol server deployment.
- IPv6 support in netplan and nftables configuration.
- Local subscription type support.
- Modular configuration templates using Jinja2 macros in `roles/sing_box_config`.
- Detailed architecture documentation with Mermaid diagrams.

### Changed

- Refactored `sing_box_config` templates to use reusable includes (`dns.j2`, `inbounds.j2`, etc.).
- Restructured Ansible playbooks into `playbooks/` directory.
- Replaced `decode_sip002_to_singbox` with object-oriented `ShadowsocksParser`.
- Removed `sing-box-tproxy-toggle.sh` script.
- Updated `nftables.conf.j2` rules ordering and logic.

## [0.6.0] - 2025-12-22

### Added

- Mode-based deployment support in `sing_box_defaults`.
- `sing-box-tproxy-toggle.sh` script for switching TProxy modes (later removed in 0.7.0).
- Pre-flight validation checks in `tasks/pre_flight_checks.yml`.
- `nftables.service` management with `ExecStartPre` checks.
- Architecture documentation (`docs/architecture.md`).

### Changed

- Modularized `sing_box_install` tasks.
- Renamed `cmd.py` to `main.py` in `src/sing_box_config`.
- Improved `export.py` with type hints and better error handling.

## [0.5.0] - 2025-11-01

### Changed

- Migrated project dependency management from PDM to uv.
- Renamed `playbook.yaml` to `site.yaml`.
- Refactored `sing_box_defaults` role structure.
- Updated `sing_box_config` role to build wheel using `uv`.

## [0.4.0] - 2025-08-04

### Added

- TCP BBR support in `roles/sing_box_tproxy`.
- `remove_invalid_outbounds` logic in configuration export.

### Changed

- Converted `base.json` and `subscriptions.json` to Jinja2 templates (`.j2`).
- Simplified `roles/sing_box_config` and `roles/sing_box_tproxy`.
- Refactored configuration role to support local package building.

## [0.3.0] - 2025-08-04

### Added

- Retry logic for HTTP requests in `fetch_url_with_retries`.
- `ExecStartPre` validation in `sing-box-reload.service`.

## [0.2.1] - 2025-08-04

### Fixed

- Hardcoded network interface in Netplan configuration.
- `nftables.conf.j2` syntax and logic issues.

## [0.2.0] - 2025-08-04

### Added

- `git-cliff` configuration.
- Proxy user execution for `sing-box-config-updater`.
- Marking of proxy user traffic in nftables.

### Changed

- Changed default apt repository package to `sing-box-beta`.
- Ensured `sing-box` package is present (not just latest).

## [0.1.6] - 2025-04-28

### Changed

- Disabled logfile logging in `src/sing_box_config`.
- Added `pre-commit` configuration.

## [0.1.5] - 2025-04-27

### Fixed

- Python package build includes to contain Ansible roles and examples.

## [0.1.3] - 2025-04-27

### Removed

- Chinese README (`README.zh-CN.md`).

## [0.1.2] - 2025-04-27

### Changed

- Renamed Python package to `sing_box_config`.
- Renamed Ansible roles to use `sing_box_` prefix.
- Added `sing-box-reload.path` systemd unit.

## [0.1.1] - 2025-04-25

### Changed

- Updated project URLs and documentation.

## [0.1.0] - 2025-04-25

### Added

- Initial release.
- Basic Ansible roles: `singbox_install`, `singbox_tproxy`, `singbox_config`.
- Python package `singbox_config` for configuration management.
- Basic TProxy and configuration update logic.
