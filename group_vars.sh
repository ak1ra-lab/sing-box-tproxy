#!/usr/bin/env bash
# Manage group_vars patches for sing-box-tproxy and sing-box-server.
#
# Usage:
#   ./group_vars.sh gen   [tproxy|server|all]   # generate / refresh patch files
#   ./group_vars.sh sync  [tproxy|server|all]   # cp defaults then apply patch

set -o errexit

ALL_GROUPS=(tproxy server)

# ── lookup table via case ─────────────────────────────────────────────────────
group_src() {
    case "${1}" in
        tproxy) echo "roles/sing_box_defaults/defaults/main.yaml" ;;
        server) echo "roles/sing_box_server/defaults/main.yaml" ;;
    esac
}
group_tgt() {
    case "${1}" in
        tproxy) echo "playbooks/group_vars/sing-box-tproxy/main.yaml" ;;
        server) echo "playbooks/group_vars/sing-box-server/main.yaml" ;;
    esac
}
group_patch() {
    case "${1}" in
        tproxy) echo "playbooks/group_vars/sing-box-tproxy.patch" ;;
        server) echo "playbooks/group_vars/sing-box-server.patch" ;;
    esac
}

# ── helpers ──────────────────────────────────────────────────────────────────
gen_patch() {
    local group="${1}"
    local src tgt patch
    src="$(group_src "${group}")"
    tgt="$(group_tgt "${group}")"
    patch="$(group_patch "${group}")"

    if [[ ! -f "${tgt}" ]]; then
        echo "SKIP ${group}: ${tgt} does not exist (run initial setup first)" >&2
        return
    fi

    # diff exits 1 when files differ; that is expected and not an error here
    diff "${src}" "${tgt}" >"${patch}" || true
    echo "GEN  ${patch}"
}

sync_patch() {
    local group="${1}"
    local src tgt patch
    src="$(group_src "${group}")"
    tgt="$(group_tgt "${group}")"
    patch="$(group_patch "${group}")"

    if [[ ! -f "${patch}" ]]; then
        echo "SKIP ${group}: ${patch} does not exist (run 'gen' first)" >&2
        return
    fi

    cp -v "${src}" "${tgt}"
    patch -p1 "${tgt}" <"${patch}"
}

run_for() {
    local cmd="${1}" target="${2}"
    if [[ "${target}" == "all" ]]; then
        for g in "${ALL_GROUPS[@]}"; do "${cmd}_patch" "${g}"; done
    else
        "${cmd}_patch" "${target}"
    fi
}

# ── main ─────────────────────────────────────────────────────────────────────
CMD="${1:-}"
TARGET="${2:-all}"

case "${CMD}" in
    gen) run_for gen "${TARGET}" ;;
    sync) run_for sync "${TARGET}" ;;
    *)
        echo "Usage: ${0} <gen|sync> [tproxy|server|all]" >&2
        exit 1
        ;;
esac
