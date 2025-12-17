#!/bin/bash

set -euo pipefail

SCRIPT_FILE="$(readlink -f "$0")"
SCRIPT_NAME="$(basename "${SCRIPT_FILE}")"

# Configuration
declare -g NFTABLES_CONF="/etc/nftables.conf"
declare -g BACKUP_CONF="${NFTABLES_CONF}.disabled"

# Logging configuration
declare -g LOG_LEVEL="INFO"
declare -g LOG_FORMAT="simple"

# Log level priorities
declare -g -A LOG_PRIORITY=(
    ["DEBUG"]=10
    ["INFO"]=20
    ["WARNING"]=30
    ["ERROR"]=40
    ["CRITICAL"]=50
)

# Logging functions
log_color() {
    local color="$1"
    shift
    if [[ -t 2 ]]; then
        printf "\x1b[0;%sm%s\x1b[0m\n" "${color}" "$*" >&2
    else
        printf "%s\n" "$*" >&2
    fi
}

log_message() {
    local color="$1"
    local level="$2"
    shift 2

    if [[ "${LOG_PRIORITY[$level]}" -lt "${LOG_PRIORITY[$LOG_LEVEL]}" ]]; then
        return 0
    fi

    local message="$*"
    case "${LOG_FORMAT}" in
        simple)
            log_color "${color}" "${message}"
            ;;
        level)
            log_color "${color}" "[${level}] ${message}"
            ;;
        full)
            local timestamp
            timestamp="$(date -u +%Y-%m-%dT%H:%M:%S+0000)"
            log_color "${color}" "[${timestamp}][${level}] ${message}"
            ;;
        *)
            log_color "${color}" "${message}"
            ;;
    esac
}

log_error() {
    local RED=31
    log_message "${RED}" "ERROR" "$@"
}

log_info() {
    local GREEN=32
    log_message "${GREEN}" "INFO" "$@"
}

log_warning() {
    local YELLOW=33
    log_message "${YELLOW}" "WARNING" "$@"
}

log_debug() {
    local BLUE=34
    log_message "${BLUE}" "DEBUG" "$@"
}

log_critical() {
    local CYAN=36
    log_message "${CYAN}" "CRITICAL" "$@"
}

# Set log level with validation
set_log_level() {
    local level="${1^^}"
    if [[ -n "${LOG_PRIORITY[${level}]:-}" ]]; then
        LOG_LEVEL="${level}"
    else
        log_error "Invalid log level: ${1}. Valid levels: ERROR, WARNING, INFO, DEBUG"
        exit 1
    fi
}

# Set log format with validation
set_log_format() {
    case "$1" in
        simple | level | full)
            LOG_FORMAT="$1"
            ;;
        *)
            log_error "Invalid log format: ${1}. Valid formats: simple, level, full"
            exit 1
            ;;
    esac
}

# Check if required commands are available
require_command() {
    local missing=()
    for c in "$@"; do
        if ! command -v "$c" >/dev/null 2>&1; then
            missing+=("$c")
        fi
    done

    if [[ ${#missing[@]} -gt 0 ]]; then
        log_error "Required command(s) not installed: ${missing[*]}"
        log_error "Please install the missing dependencies and try again"
        exit 1
    fi
}

# Check if running with required privileges
check_privileges() {
    if [[ "${EUID}" -ne 0 ]]; then
        log_error "This script must be run as root or with sudo"
        log_error "Please run: sudo ${SCRIPT_NAME} $*"
        exit 1
    fi
}

# Cleanup handler
cleanup() {
    local exit_code=$?
    exit "${exit_code}"
}

trap cleanup EXIT INT TERM

# Show usage information
usage() {
    local exit_code="${1:-0}"
    cat <<EOF
USAGE:
    ${SCRIPT_NAME} [OPTIONS] COMMAND

    Manage sing-box transparent proxy mode (local mode only).
    This script must be run as root or with sudo.

OPTIONS:
    -h, --help                Show this help message
    --log-level LEVEL         Set log level (ERROR, WARNING, INFO, DEBUG)
                              Default: INFO
    --log-format FORMAT       Set log output format (simple, level, full)
                              Default: simple
    -f, --force               Skip confirmation prompts

COMMANDS:
    enable                    Enable transparent proxy nftables rules
    disable                   Disable transparent proxy nftables rules
    status                    Show current nftables status

NOTES:
    This tool only affects local mode installations. Gateway mode should not
    be toggled as it serves the entire network.

EXAMPLES:
    sudo ${SCRIPT_NAME} enable
    sudo ${SCRIPT_NAME} disable --force
    sudo ${SCRIPT_NAME} status
    sudo ${SCRIPT_NAME} --log-level DEBUG enable

EOF
    exit "${exit_code}"
}

# Parse command line arguments
parse_args() {
    local args
    local options="hf"
    local longoptions="help,log-level:,log-format:,force"
    if ! args=$(getopt --options="${options}" --longoptions="${longoptions}" --name="${SCRIPT_NAME}" -- "$@"); then
        usage 1
    fi

    eval set -- "${args}"
    declare -g -a REST_ARGS=()
    declare -g FORCE_MODE=false

    while true; do
        case "$1" in
            -h | --help)
                usage 0
                ;;
            --log-level)
                set_log_level "$2"
                shift 2
                ;;
            --log-format)
                set_log_format "$2"
                shift 2
                ;;
            -f | --force)
                FORCE_MODE=true
                shift
                ;;
            --)
                shift
                break
                ;;
            *)
                log_error "Unexpected option: $1"
                usage 1
                ;;
        esac
    done

    REST_ARGS=("$@")
}

# Check if running in local mode
check_local_mode() {
    log_debug "Checking sing-box mode"

    if ! systemctl is-enabled sing-box.service &>/dev/null; then
        log_error "sing-box.service is not enabled"
        return 1
    fi

    # Check for prerouting chain (gateway mode indicator)
    if nft list table inet sing_box_tproxy 2>/dev/null | grep -q "chain prerouting_tproxy"; then
        log_warning "This appears to be a gateway mode installation"
        log_warning "Toggling transparent proxy for gateway mode is not recommended"

        if [[ "${FORCE_MODE}" == "false" ]]; then
            read -rp "Continue anyway? [y/N] " confirm
            if [[ "${confirm,,}" != "y" ]]; then
                log_info "Operation cancelled"
                return 1
            fi
        else
            log_warning "Proceeding due to --force flag"
        fi
    fi
}

# Enable transparent proxy
enable_tproxy() {
    log_debug "Attempting to enable transparent proxy"

    if [[ ! -f "${BACKUP_CONF}" ]]; then
        if [[ -f "${NFTABLES_CONF}" ]]; then
            log_info "Transparent proxy is already enabled"
        else
            log_error "No backup configuration found at ${BACKUP_CONF}"
            exit 1
        fi
        return 0
    fi

    log_info "Restoring nftables configuration"
    mv "${BACKUP_CONF}" "${NFTABLES_CONF}"

    log_info "Restarting nftables service"
    systemctl restart nftables.service

    log_info "Transparent proxy enabled successfully"
}

# Disable transparent proxy
disable_tproxy() {
    log_debug "Attempting to disable transparent proxy"

    if [[ ! -f "${NFTABLES_CONF}" ]]; then
        log_info "Transparent proxy is already disabled"
        return 0
    fi

    log_info "Backing up nftables configuration"
    mv "${NFTABLES_CONF}" "${BACKUP_CONF}"

    log_info "Flushing nftables ruleset"
    nft flush ruleset

    log_info "Transparent proxy disabled successfully"
}

# Show current status
show_status() {
    log_info "=== sing-box Service Status ==="
    systemctl status sing-box.service --no-pager || true
    echo ""

    log_info "=== Nftables Rules ==="
    if nft list table inet sing_box_tproxy 2>/dev/null; then
        log_debug "Nftables rules loaded"
    else
        log_warning "No nftables rules loaded"
    fi
    echo ""

    log_info "=== Configuration Files ==="
    if [[ -f "${NFTABLES_CONF}" ]]; then
        log_info "Active config: ${NFTABLES_CONF}"
    fi
    if [[ -f "${BACKUP_CONF}" ]]; then
        log_info "Backup config: ${BACKUP_CONF}"
    fi
}

main() {
    check_privileges "$@"
    require_command getopt nft systemctl

    parse_args "$@"

    if [[ ${#REST_ARGS[@]} -ne 1 ]]; then
        log_error "Expected exactly one command"
        usage 1
    fi

    local command="${REST_ARGS[0]}"
    log_debug "Executing command: ${command}"

    case "${command}" in
        enable)
            check_local_mode
            enable_tproxy
            ;;
        disable)
            check_local_mode
            disable_tproxy
            ;;
        status)
            show_status
            ;;
        *)
            log_error "Unknown command: ${command}"
            usage 1
            ;;
    esac
}

main "$@"
