# AGENTS.md — Project Guide for AI Coding Agents

Read this file before making any changes. See `README.md` for full project details.

## What This Project Does

**sing-box-tproxy** is a hybrid Ansible + Python project that automates deployment of
[SagerNet/sing-box](https://github.com/SagerNet/sing-box) as a transparent proxy
(TPROXY) on Debian/Ubuntu Linux. It ships a `sing-box-config` Python CLI package
(entry points: `sing-box-config`, `sing-box-liveness-probe`) alongside Ansible roles.

## Python Environment — CRITICAL

The environment manager is **[uv](https://github.com/astral-sh/uv)**.

- ALWAYS run Python commands with `uv run <command>`.
- NEVER use `.venv/bin/python`, `pip install`, `conda`, `pipenv`, or `poetry`.
- Install/sync dev dependencies: `uv sync --group dev`
- Run tests: `uv run pytest -v` — do NOT use `python -m pytest`.
- Lint + format: `./ruff.sh` (wraps `uv run ruff check` and `uv run ruff format`).

## Conventions

- **Ansible variables** follow the pattern `sing_box_<subsystem>_<parameter>`.
- **`roles/sing_box_defaults/defaults/main.yaml`** is the single source of truth for
  all default Ansible variable values. Define new parameters here first, then reference
  them in role tasks or Jinja2 templates. `playbooks/group_vars/` and
  `playbooks/host_vars/` are the only override layers.
- **Python source** lives in `src/sing_box_config/`; the CLI entry points are
  `main.py` (`sing-box-config`) and `probe.py` (`sing-box-liveness-probe`).

## Testing Guidelines

- Tests live in `tests/` and mirror `src/sing_box_config/` module names.
- Run the full suite after every change: `uv run pytest -v`
- When modifying a function signature, update all call sites in `src/` **and** `tests/`
  in the same commit.
- Mock all external I/O (HTTP, subprocess) — do NOT make real network calls in tests.

## Common Operations

```shell
uv run pytest -v                                      # run tests
./ruff.sh                                             # lint + format
uv sync --group dev                                   # sync dev dependencies
ansible-playbook playbooks/sing_box_tproxy.yaml -v    # deploy tproxy client
ansible-playbook playbooks/sing_box_server.yaml -v    # deploy server
uv run mkdocs serve                                   # docs preview
```
