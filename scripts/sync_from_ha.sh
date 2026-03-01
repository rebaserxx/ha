#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

HA_HOST="${HA_HOST:-root@192.168.1.191}"
HA_CONFIG_DIR="${HA_CONFIG_DIR:-/homeassistant}"
SNAPSHOT_DIR="${SNAPSHOT_DIR:-${REPO_ROOT}/snapshots/homeassistant}"
SSH_OPTS=(-o BatchMode=yes -o ConnectTimeout=10)

FILES=(
  "configuration.yaml"
  "automations.yaml"
  "scripts.yaml"
  "scenes.yaml"
  "dashboards/appliances.yaml"
)

usage() {
  cat <<'EOF'
Usage:
  scripts/sync_from_ha.sh sync
  scripts/sync_from_ha.sh verify

Environment overrides:
  HA_HOST        SSH target (default: root@192.168.1.191)
  HA_CONFIG_DIR  Home Assistant config directory (default: /homeassistant)
  SNAPSHOT_DIR   Local snapshot path (default: snapshots/homeassistant)
EOF
}

fetch_file() {
  local remote_file="$1"
  local local_file="$2"
  mkdir -p "$(dirname "${local_file}")"
  ssh "${SSH_OPTS[@]}" "${HA_HOST}" "cat '${HA_CONFIG_DIR}/${remote_file}'" > "${local_file}"
}

fetch_info() {
  local out_dir="$1"
  ssh "${SSH_OPTS[@]}" "${HA_HOST}" "ha core info" > "${out_dir}/ha_core_info.txt"
  ssh "${SSH_OPTS[@]}" "${HA_HOST}" "ha info" > "${out_dir}/ha_info.txt"
}

sync_snapshots() {
  mkdir -p "${SNAPSHOT_DIR}"

  for file in "${FILES[@]}"; do
    local tmp_file
    tmp_file="$(mktemp)"
    fetch_file "${file}" "${tmp_file}"
    mkdir -p "$(dirname "${SNAPSHOT_DIR}/${file}")"
    mv "${tmp_file}" "${SNAPSHOT_DIR}/${file}"
  done

  fetch_info "${SNAPSHOT_DIR}"
  date -u +"%Y-%m-%dT%H:%M:%SZ" > "${SNAPSHOT_DIR}/_synced_at_utc.txt"
  echo "Synced snapshots to ${SNAPSHOT_DIR}"
}

verify_snapshots() {
  local tmp_dir
  local drift=0
  tmp_dir="$(mktemp -d)"
  trap "rm -rf '${tmp_dir}'" EXIT

  for file in "${FILES[@]}"; do
    fetch_file "${file}" "${tmp_dir}/${file}"
    if [[ ! -f "${SNAPSHOT_DIR}/${file}" ]]; then
      echo "Missing local snapshot: ${SNAPSHOT_DIR}/${file}"
      drift=1
      continue
    fi
    if ! diff -u "${SNAPSHOT_DIR}/${file}" "${tmp_dir}/${file}"; then
      drift=1
    fi
  done

  fetch_info "${tmp_dir}"
  for info_file in ha_core_info.txt ha_info.txt; do
    if [[ ! -f "${SNAPSHOT_DIR}/${info_file}" ]]; then
      echo "Missing local snapshot: ${SNAPSHOT_DIR}/${info_file}"
      drift=1
      continue
    fi
    if ! diff -u "${SNAPSHOT_DIR}/${info_file}" "${tmp_dir}/${info_file}"; then
      drift=1
    fi
  done

  if [[ "${drift}" -ne 0 ]]; then
    echo "Drift detected between live Home Assistant and ${SNAPSHOT_DIR}."
    exit 1
  fi

  echo "No drift detected against ${SNAPSHOT_DIR}."
}

main() {
  local cmd="${1:-}"
  case "${cmd}" in
    sync)
      sync_snapshots
      ;;
    verify)
      verify_snapshots
      ;;
    *)
      usage
      exit 1
      ;;
  esac
}

main "${1:-}"
