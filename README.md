# Home Assistant Project

This repository is used to support Home Assistant setup, configuration, and operational workflows.

## Purpose
- Keep notes and runbooks for managing Home Assistant.
- Document how Codex should interact with Home Assistant across sessions.
- Store project-specific guidance for troubleshooting and ongoing improvements.

## Key Document
- `HOMEASSISTANT_CODEX_COMMUNICATION.md` - rules and workflow for how Codex communicates with Home Assistant (MCP, API, SSH), including verification and troubleshooting conventions.

## Configuration Docs
- `docs/lighting_reusable_components.md` - source-of-truth for reusable lighting scripts, area sets, profiles, and schedules.
- `docs/homeassistant_configuration_reference.md` - current HA include layout, file ownership, automation/script inventory, and area ID reference.
- `docs/codex_change_playbook.md` - request templates and change policy for future Codex updates.
- `docs/change_log.md` - chronological record of config changes, validation status, and rollback notes.

## Live Sync And Drift Verification
- `scripts/sync_from_ha.sh` - sync or verify this repo's Home Assistant snapshots against the live server.
- `snapshots/homeassistant/` - source-controlled snapshots of:
  - `configuration.yaml`
  - `automations.yaml`
  - `scripts.yaml`
  - `scenes.yaml`
  - `ha_core_info.txt`
  - `ha_info.txt`
- `Makefile` targets:
  - `make sync-ha` - refresh snapshots from live Home Assistant.
  - `make verify` - compare live Home Assistant files against tracked snapshots and fail on drift.
