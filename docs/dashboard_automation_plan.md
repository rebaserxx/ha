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
- `energy-utilities` -> `dashboards/utilities.yaml`
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

Status:
- Implemented on 2026-05-27.

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

Status:
- Implemented on 2026-05-28.

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

Status:
- Implemented on 2026-05-28.

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

### 12. Renault State-of-Charge Sync to Ohme

Purpose:
- Keep Ohme's charge planning accurate now that Ohme has disabled its own Renault
  integration, without ever requesting power.

Status:
- Implemented on 2026-08-31 (`ev_ohme_sync_renault_state_of_charge`).

Behavior:
- Triggers when `sensor.ohme_home_pro_status` leaves `unplugged`, and again whenever
  `sensor.renault_scenic_e_tech_battery` refreshes while still plugged in (the Renault
  cloud is often hours stale at the moment of plug-in, so the second trigger is what
  usually lands the accurate figure).
- Writes only `number.utilities_ohme_home_pro_state_of_charge_input`, which the core
  integration maps to `PUT /v1/car/{id}/state-of-charge`. It never touches
  `select.ohme_home_pro_charge_mode`, `button.ohme_home_pro_approve_charge` or
  `number.ohme_home_pro_target_percentage`, so it cannot start, approve or resume a charge.
- Selects `Renault Scenic (2023-2025)` in Ohme first, because Ohme applies state-of-charge
  to the currently selected vehicle (`client._cars[0]`).

Files:
- `snapshots/homeassistant/automations.yaml`
- `docs/change_log.md`

Review focus:
- The charger is shared with a Honda e:Ny1, which as of 2026-09-01 has its own Home
  Assistant presence (My Honda+ custom integration, `e_ny1_*` entities) and its own paired
  automations - see item 13. The Renault is still identified solely by
  `binary_sensor.renault_scenic_e_tech_plug` = `on` AND
  `device_tracker.renault_scenic_e_tech_location` = `home`, deliberately unchanged: adding a
  Honda guard here would let stale Honda data block known-good Renault behaviour. Exclusion
  is enforced on the Honda side instead, so the Renault wins any tie. Confirm on the first real
  plug-in that the Renault plug sensor actually flips - it has not changed since the
  2026-08-28 restart, so it is unproven.
- The automation leaves `Renault` selected in Ohme afterwards. A subsequent Honda plug-in
  still needs the vehicle switched manually in the Ohme app, exactly as before.
- `number.utilities_ohme_home_pro_state_of_charge_input` is `entity_registry_enabled_default=False`
  upstream; it was enabled manually. A future integration change could re-disable it.

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

## 13. Honda e:Ny1 EV automations (added 2026-09-01)

Purpose:
- Give the Honda e:Ny1 the same two behaviours the Renault has on the shared Ohme charger:
  auto-approve a pending session, and keep Ohme's state-of-charge figure correct.

Status:
- Deployed to `/config/automations.yaml` and passing `ha core check`.
- NOT YET LOADED: the automation reload was blocked by the sandbox, so
  `automation.ev_*_honda_*` do not exist as entities yet. Needs a reload or restart.
- Unproven end to end. No real Honda plug-in has been observed.

Files touched:
- `/config/automations.yaml`
- `snapshots/homeassistant/automations.yaml`
- `docs/change_log.md`

Automations:
- `ev_ohme_sync_honda_state_of_charge` - state-of-charge write only, cannot cause charging.
- `ev_ohme_auto_approve_honda_charge` - DELIBERATELY causes charging, same contract as the
  Renault equivalent.

Review focus:
- The Honda integration was installed 2026-09-01 ~19:41 with no recorded history.
  `sensor.e_ny1_plug_status` has never been observed leaving `unplugged`, so plug detection
  is unproven, exactly as the Renault's was on 2026-08-28. Watch the first real plug-in.
- Honda cloud data was measured 6h50m stale while HA had just polled the integration. Both
  automations force `button.e_ny1_refresh_from_car` and require
  `sensor.e_ny1_last_updated` within 5 minutes, aborting after a 2-minute timeout. A forced
  refresh returned in ~15s when the car had been parked ~7h - confirm this still holds when
  the car has been asleep longer.
- `device_tracker.e_ny1_location` (GPS, `in_zones: [zone.home]`) is used for the at-home
  test. `sensor.e_ny1_home_away` disagreed with it (`away` vs `home`) at the time of
  writing and is deliberately not used. Worth understanding which is authoritative.
- The 15-minute mid-charge refresh tick is gated on the Honda already being selected in Ohme
  AND Ohme `charging`, so it should never wake the car during a Renault session. Confirm.
- Intelligent Octopus Go is registered to the charge point, not a vehicle
  (`provider: OHME`, `vehicle_battery_size_in_kwh: None`), so the Honda should get the same
  off-peak dispatch treatment. Confirm on a real session before relying on it.

### Update 2026-09-02 - wrong-car identification fixed

- The Honda automations from 2026-09-01 were never loaded until 2026-09-02; the reload had
  been blocked. Symptom the user saw: Honda plugged in, nothing happened.
- Separately, `ev_ohme_auto_approve_renault_charge` was found to have approved a HONDA
  session at 17:23:11 on 2026-09-02, confirmed by automation trace. The Renault's plug
  sensor was stale `on` for 46s after being unplugged, and the SoC-match wait passed against
  the outgoing Renault figure before Ohme updated to the Honda's.
- All four EV automations now use a shared "settle then decide" gate, and both SoC-match
  waits require the Ohme vehicle select to name the expected car. See the 2026-09-02 entry
  in `docs/change_log.md` for full evidence and rationale.
- Proven end to end for the SYNC path on live data (Honda selected in Ohme, SoC written 81,
  Ohme re-planned to slots 18:24-18:30 / 01:00-01:30 / 02:00-02:31, target 90% by 06:00).
- Still unproven: the APPROVE path on a real `pending_approval` session for either car under
  the new settle gate. Watch the next plug-in of each car.
