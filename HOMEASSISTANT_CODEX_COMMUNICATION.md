# Home Assistant Communication Guide for Codex

This document defines how Codex should communicate with Home Assistant in future sessions.

## Goals
- Prefer safe, repeatable, verifiable operations.
- Use the most direct integration first.
- Always confirm changes with a read-back check.

## Priority Order
1. MCP (preferred)
2. Home Assistant API (REST/WebSocket)
3. SSH (fallback for diagnostics or file-level tasks)

## Environment Assumptions
- Home Assistant host: `192.168.1.191`
- Home Assistant base URL: `http://192.168.1.191:8123`
- SSH target: `root@192.168.1.191`
- Codex MCP server name: `homeassistant`

## Authentication
- Use `HOMEASSISTANT_TOKEN` env var for API/WebSocket auth.
- Never print token values in output.
- If token is exposed in chat/logs, rotate it in Home Assistant and update shell profile.

## Standard Workflow
1. Read current state/config first.
2. Apply smallest possible change.
3. Read back and verify expected values.
4. Report exactly what changed and what was verified.

## MCP Usage Rules
- Use MCP tools first for device state/actions.
- Prefer `GetLiveContext` before conditional automation changes.
- If MCP lacks required capability (for example, Energy prefs), switch to API.

## API Usage Rules
- REST for simple health checks.
- WebSocket API for advanced config domains (for example, `energy/get_prefs`, `energy/save_prefs`).
- Always verify with a follow-up read (`get_*`) after save.

## SSH Usage Rules
- Use SSH only when MCP/API cannot complete the task.
- Prefer read-only commands for investigation first.
- For changes made through SSH, verify outcome through API or HA CLI.

## Energy Dashboard Conventions
- Octopus Energy should use external statistic IDs (`octopus_energy:...`) where required.
- Device consumption example: `sensor.ohme_home_pro_energy`.
- Water consumption example: `sensor.water_meter_latest_reading`.
- After writing prefs, verify via `energy/get_prefs`.

## Troubleshooting Checklist
- If dashboard is empty:
  - Confirm statistic IDs exist (`recorder/list_statistic_ids`).
  - Confirm samples exist (`recorder/statistics_during_period`).
  - Check selected date range in Energy dashboard.
  - Confirm new sensors have produced at least one long-term statistics point.

## Output Style for Future Sessions
- State plan briefly.
- Show what was checked.
- Show what was changed.
- Show verification result.
- Include next action only if needed.

## Quick Commands
- Test MCP connectivity by calling date/time and live context.
- Test API health:
  - `GET /api/` with bearer token.
- SSH health:
  - `ha info`
  - `ha core info`
