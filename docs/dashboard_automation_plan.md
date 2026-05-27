# Home Assistant Dashboard And Automation Plan

Created: 2026-05-27

This plan breaks future dashboard and automation work into small reviewable changes. Each item should be implemented, validated, deployed, and reviewed before moving to the next one.

## Principles

- Keep Home Assistant UI dashboards admin-focused because family control currently happens through Alexa and HomeKit.
- Prefer alert-only automations before adding automatic corrective actions.
- Avoid notification spam: use daily checks or delayed triggers for non-urgent issues.
- Keep dashboards YAML-managed unless there is a specific reason to use storage mode.
- Validate every YAML change with `ha core check` and `make verify`.
- Update `docs/change_log.md` for each live Home Assistant change.

## Naming Conventions

Dashboard filenames and IDs:

- `home-health` -> `dashboards/home_health.yaml`
- `utilities` -> `dashboards/utilities.yaml`
- `heating-diagnostics` -> `dashboards/heating_diagnostics.yaml`
- `voice-bridges` -> `dashboards/voice_bridges.yaml`

Automation ID prefixes:

- `system_*` for backup, Watchman, update, and infrastructure health checks
- `hot_water_*` for hot water and pump checks
- `heating_*` for Tado room diagnostics and alerts
- `ev_*` for Ohme, Renault, and Octopus charging checks
- `network_*` for fixed infrastructure availability checks

Dashboard policy:

- Admin dashboards may include update entities, diagnostic sensors, and control buttons.
- Any dashboard with appliance stop/power controls must remain `require_admin: true`.
- Family-facing controls should continue to be managed primarily through Alexa and HomeKit exposure lists.

## Implementation Order

### 1. Home Health Dashboard

Purpose:
- Provide a single admin view for system reliability.

Status:
- Implemented on 2026-05-27.

Include:
- Backup last successful, next scheduled, attempted, and manager state.
- Watchman status, missing entities, missing actions, last parse, and report button.
- Home Assistant Core, Supervisor, OS, Matter Server, Terminal & SSH updates.
- HACS, Meross LAN, Octopus Energy, and Watchman updates.
- UniFi gateway state, uptime, CPU, memory, and firmware.

Files:
- `snapshots/homeassistant/configuration.yaml`
- `snapshots/homeassistant/dashboards/home_health.yaml`
- `docs/homeassistant_configuration_reference.md`
- `docs/change_log.md`

Validation:
- `ha core check`
- restart Core or reload Lovelace as required
- `make verify`
- confirm dashboard appears in sidebar

Review focus:
- Is this the right first page for admin checks?
- Are any entities noisy, missing, or not useful?

### 2. Backup Stale Alert

Purpose:
- Alert if automatic backups stop completing.

Behavior:
- Daily check around `09:00`.
- Persistent notification if the last successful backup is older than 36 hours.
- Persistent notification if backup manager state is unhealthy.
- Dismiss or clear the alert when healthy.

Files:
- `snapshots/homeassistant/automations.yaml`
- `docs/change_log.md`

Review focus:
- Is 36 hours the right threshold?
- Should this stay as persistent notification or use mobile notify?

### 3. Watchman Alert

Purpose:
- Catch broken entity and action references after changes.

Behavior:
- Alert when `sensor.watchman_missing_entities` or `sensor.watchman_missing_actions` is above zero.
- Prefer a daily summary first unless immediate alerts prove useful.
- Include counts and a prompt to create/review the Watchman report.

Files:
- `snapshots/homeassistant/automations.yaml`
- `docs/change_log.md`

Review focus:
- Immediate alert vs daily summary.
- Whether ignored labels need tuning.

### 4. Energy / EV / Utilities Dashboard

Purpose:
- Show operational state for Octopus, Ohme, Renault, gas, water, and hot water.

Include:
- Electricity current, previous, and next rates.
- Gas current rate and previous consumption/cost.
- Octopus off-peak and Intelligent Dispatching status.
- Ohme charger mode, power, energy, vehicle battery, and charge slots.
- Renault battery, range, charge state, target charge, and charge controls if safe.
- Water usage and cost.
- Hot water demand, pump state, and pump timer.

Files:
- `snapshots/homeassistant/configuration.yaml`
- `snapshots/homeassistant/dashboards/utilities.yaml`
- `docs/homeassistant_configuration_reference.md`
- `docs/change_log.md`

Review focus:
- Does the dashboard answer what is happening with utilities right now?
- Which controls should be visible vs status-only?

### 5. Hot Water Pump Watchdog

Purpose:
- Detect pump failures or unexpected runtime without changing current control behavior.

Behavior:
- Alert if `binary_sensor.hot_water_power` is on but `switch.hot_water_pump` remains off for 2 minutes.
- Alert if `switch.hot_water_pump` remains on beyond an expected maximum.
- Do not auto-correct in the first implementation.

Files:
- `snapshots/homeassistant/automations.yaml`
- `docs/change_log.md`

Review focus:
- Alert wording and thresholds.
- Whether later auto-correction is justified.

### 6. Heating Diagnostics Dashboard

Purpose:
- Debug Tado room behavior quickly.

Include per room:
- Climate entity.
- Temperature and humidity.
- Heating demand/power.
- Window state.
- Overlay/manual override.
- Connectivity.

Suggested views:
- Overview.
- Rooms currently heating.
- Open windows.
- Connectivity and manual overrides.

Files:
- `snapshots/homeassistant/configuration.yaml`
- `snapshots/homeassistant/dashboards/heating_diagnostics.yaml`
- `docs/homeassistant_configuration_reference.md`
- `docs/change_log.md`

Review focus:
- Room grouping and scanability.
- Whether quick actions are useful or too risky.

### 7. Tado Heating Alerts

Purpose:
- Surface heating problems that are easy to miss.

Behavior:
- Alert if a room is heating while its window sensor is open for 5 minutes.
- Alert if a Tado room is disconnected or unavailable.
- Optional later check: manual overlay active too long.

Files:
- `snapshots/homeassistant/automations.yaml`
- `docs/change_log.md`

Review focus:
- Tune thresholds to avoid noise.
- Keep alert-only unless there is a clear reason to automate changes.

### 8. EV Charge Readiness Alert

Purpose:
- Avoid missed overnight charging.

Behavior:
- Evening check, for example `20:00`.
- Alert if Renault battery is below a chosen threshold and the charging setup is not ready.
- Include Ohme mode, Renault charge state, and Octopus dispatch/off-peak state in the message.

Files:
- `snapshots/homeassistant/automations.yaml`
- optional helper in `snapshots/homeassistant/configuration.yaml`
- `docs/change_log.md`

Review focus:
- Choose threshold, likely 40% or 50%.
- Confirm Renault and Ohme entity states are reliable enough.

### 9. Critical Infrastructure Offline Alert

Purpose:
- Detect fixed infrastructure failures.

Watch fixed devices only:
- Home Assistant host.
- Hue Bridge.
- Tado bridge.
- NAS.
- Ohme charger.
- Home Connect appliances.
- Dryer.
- UniFi gateway and important APs.
- Meross water pump switch.

Behavior:
- Alert after 10-15 minutes offline for critical devices.
- Prefer daily summary for less critical fixed devices.
- Exclude phones, tablets, watches, and guest/mobile devices.

Files:
- `snapshots/homeassistant/automations.yaml`
- `docs/change_log.md`

Review focus:
- Watched entity list.
- Immediate vs summary alerts.

### 10. Voice Exposure / Bridge Audit Dashboard

Purpose:
- Manage the family-facing Alexa and HomeKit layer.

Include:
- HomeKit bridge sections for Lights, Climate, AC, and Kitchen Heating.
- Alexa exposed entities.
- Entities intentionally excluded from voice platforms.
- Naming rules.
- Bridge ports and pairing notes.

Files:
- `snapshots/homeassistant/configuration.yaml`
- `snapshots/homeassistant/dashboards/voice_bridges.yaml`
- `docs/homeassistant_configuration_reference.md`
- `docs/change_log.md`

Review focus:
- Whether it reflects the intended family UX.
- Whether exposed names remain stable and easy to speak.

### 11. Appliances Dashboard Refinement

Purpose:
- Improve the existing admin-only Appliances dashboard.

Changes:
- Keep `require_admin: true`.
- Split status from controls.
- Move stop, power, child-lock, and programme controls into a lower or separate admin-control view.
- Make the at-a-glance section faster to scan.

Files:
- `snapshots/homeassistant/dashboards/appliances.yaml`
- `docs/change_log.md`

Review focus:
- Faster status scanning.
- Dangerous controls are less prominent.

## Per-Item Checklist

For each implementation item:

1. Confirm scope before editing.
2. Create or confirm a recoverable backup before live mutation.
3. Edit local snapshots/docs.
4. Deploy to live Home Assistant.
5. Run `ha core check`.
6. Reload/restart as needed.
7. Run `make verify`.
8. Update `docs/change_log.md`.
9. Leave manual behavior checks clearly listed.
