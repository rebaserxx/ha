# Home Assistant Change Log

Use this file to track every Home Assistant configuration change made via Codex or manually.

## Entry Template

Copy this block for each change:

```md
## YYYY-MM-DD - Short title

Summary:
- What changed and why.

Files changed:
- /config/... (or repo doc files)

Details:
- Specific scripts/automations/entities affected.
- Old behavior -> new behavior.

Validation:
- [ ] `ha core check`
- [ ] Reload scripts/automations or restart core
- [ ] Manual test run completed
- Notes:

Rollback:
- Exact steps to restore prior behavior.

Requested by:
- Name/source (optional)

Implemented by:
- Codex / manual
```

---

## 2026-03-01 - Prepare HomeKit bridge migration naming and runbook

Summary:
- Added canonical HomeKit-facing friendly names for room-level light and Tado climate entities.
- Added a HomeKit bridge migration runbook with exact include lists, exclude lists, and rollout batches for the UI-managed bridges.
- Added a YAML-managed pilot HomeKit bridge for the first three room-light entities.
- Added a YAML-managed production `HA Lights` bridge for the full canonical room-light set.
- Added a YAML-managed production `HA Climate` bridge for the canonical Tado room climates plus hot water.

Files changed:
- snapshots/homeassistant/configuration.yaml
- docs/homekit_bridge_migration.md
- docs/homeassistant_configuration_reference.md
- README.md
- docs/change_log.md

Details:
- Added `homeassistant.customize` entries in `configuration.yaml` for HomeKit-exported entities.
- Added a YAML-managed `homekit:` pilot bridge:
  - `name: HA Pilot Lights`
  - `port: 21063`
  - `include_entities`:
    - `light.sarahs_office`
    - `light.guest_bedroom`
    - `light.ren_s_bedroom`
- Added a YAML-managed `homekit:` production light bridge:
  - `name: HA Lights`
  - `port: 21064`
  - `include_entities`:
    - `light.attic_lounge`
    - `light.davids_office`
    - `light.dining_room`
    - `light.front_porch`
    - `light.guest_bedroom`
    - `light.hallway`
    - `light.landing`
    - `light.lounge`
    - `light.main_bedroom`
    - `light.ren_s_bedroom`
    - `light.sarahs_office`
    - `light.side_hall`
- Added a YAML-managed `homekit:` production climate bridge:
  - `name: HA Climate`
  - `port: 21065`
  - `include_entities`:
    - `climate.attic_lounge`
    - `climate.davids_office`
    - `climate.dining_room`
    - `climate.guest_bedroom`
    - `climate.hallway`
    - `climate.landing`
    - `climate.lounge`
    - `climate.main_bedroom`
    - `climate.nathaniels_bedroom`
    - `climate.ren_s_bedroom`
    - `climate.sarahs_office`
    - `climate.toilet`
    - `water_heater.hot_water`
- Room-level lighting entities now have explicit `Room Lights` friendly names:
  - `light.attic_lounge`
  - `light.davids_office`
  - `light.dining_room`
  - `light.front_porch`
  - `light.guest_bedroom`
  - `light.hallway`
  - `light.landing`
  - `light.lounge`
  - `light.main_bedroom`
  - `light.ren_s_bedroom`
  - `light.sarahs_office`
  - `light.side_hall`
- Tado room-level climate entities now have explicit `Room Heating` friendly names:
  - `climate.attic_lounge`
  - `climate.davids_office`
  - `climate.dining_room`
  - `climate.guest_bedroom`
  - `climate.hallway`
  - `climate.landing`
  - `climate.lounge`
  - `climate.main_bedroom`
  - `climate.nathaniels_bedroom`
  - `climate.ren_s_bedroom`
  - `climate.sarahs_office`
  - `climate.toilet`
- Added `docs/homekit_bridge_migration.md` as the source of truth for:
  - exact bridge include lists
  - explicit entity exclusions
  - phased rollout order
  - validation checklist
- Implemented the pilot bridge in YAML because it is the supported automatable path for an exact include list from this repo.

Validation:
- [x] `ha core check`
- [x] Reload scripts/automations or restart core
- [ ] Manual test run completed
- Notes:
  - Snapshot-to-live parity was clean before starting (`make verify`).
  - Deployed updated `/homeassistant/configuration.yaml` with the HomeKit naming customizations.
  - `ha core check` completed successfully on the HA host.
  - Restarted Home Assistant Core to apply the new `homeassistant.customize` names.
  - Added and deployed a YAML-managed HomeKit pilot bridge named `HA Pilot Lights` on port `21063`.
  - Home Assistant imported the pilot bridge as config entry `01KJM7GT7ZSA1YFHAQNT6XMRX8` at `2026-03-01T08:16:29+00:00`.
  - Added and deployed a YAML-managed HomeKit production light bridge named `HA Lights` on port `21064`.
  - Home Assistant imported the production light bridge as config entry `01KJM82Q0N183PN4PB4106XJGY` at `2026-03-01T08:26:15+00:00`.
  - Added and deployed a YAML-managed HomeKit production climate bridge named `HA Climate` on port `21065`.
  - Home Assistant imported the production climate bridge as config entry `01KJMBKDHN9CMHHATPTR765HWE` at `2026-03-01T09:27:49+00:00`.
  - Verified snapshot-to-live parity after deploy with `make verify` (no drift).

Rollback:
- Remove the `homeassistant.customize` block entries for the HomeKit-exported entities from `/homeassistant/configuration.yaml`.
- Revert the HomeKit migration runbook and reference docs if they are no longer wanted.

Requested by:
- Project user

Implemented by:
- Codex

---

## 2026-02-27 - Add Octopus gas rollover health-check automation

Summary:
- Implemented a non-invasive monitor for Octopus gas daily rollover so missing `last_reset` day changes are surfaced immediately.
- Chosen remediation path is wait-and-monitor (no historical data backfill).

Files changed:
- snapshots/homeassistant/automations.yaml
- docs/homeassistant_configuration_reference.md
- docs/change_log.md

Details:
- Added automation:
  - `octopus_energy_gas_rollover_health_daily_check`
- Trigger:
  - daily at `19:00:00`
- Monitored sensor:
  - `sensor.octopus_energy_gas_e6s10414361656_2215950002_previous_accumulative_consumption_kwh`
- Health condition:
  - expected `last_reset` date = yesterday (`YYYY-MM-DD`)
  - failure when kWh sensor is unknown/unavailable or `last_reset` date does not match yesterday
- Failure behavior:
  - creates persistent notification:
    - `notification_id: octopus_energy_gas_rollover_health`
    - includes expected date, observed date, and current gas kWh/m3 states
- Recovery behavior:
  - dismisses notification `octopus_energy_gas_rollover_health` automatically when data is healthy

Validation:
- [x] `ha core check`
- [x] Reload scripts/automations or restart core
- [x] Manual test run completed
- Notes:
  - Monitor is intentionally read-only and does not modify sensors/statistics.
  - Deployed updated `/homeassistant/automations.yaml` and ran `ha core check` successfully.
  - Reloaded automations via `automation.reload` service (`[]` response).
  - Manual trigger executed successfully; automation `last_triggered` updated to `2026-02-27T17:32:02+00:00`.
  - Notification state check returned `404` for `persistent_notification.octopus_energy_gas_rollover_health` (expected healthy-path result).
  - Verified snapshot-to-live parity with `make verify` (no drift).

Rollback:
- Remove `octopus_energy_gas_rollover_health_daily_check` from `/homeassistant/automations.yaml` and reload automations.

Requested by:
- Project user

Implemented by:
- Codex

---

## 2026-02-27 - Add Friday 06:50 common-area pre-sunrise lighting

Summary:
- Kept common-area morning lights on at `06:20` for Monday-Thursday and added a separate Friday run at `06:50`.
- Kept front porch morning schedule unchanged.

Files changed:
- snapshots/homeassistant/automations.yaml
- docs/lighting_reusable_components.md
- docs/homeassistant_configuration_reference.md
- docs/change_log.md

Details:
- Kept existing automation `lighting_common_weekday_morning_0620_presunrise` unchanged:
  - trigger `06:20:00`
  - weekday condition `mon`, `tue`, `wed`, `thu`
  - condition `before: sunrise`
- Added new automation `lighting_common_friday_morning_0650_presunrise`:
  - trigger `06:50:00`
  - weekday condition `fri`
  - condition `before: sunrise`
  - action target and settings match existing common-area morning behavior
- Did not change front porch automation `lighting_front_porch_on_0620_presunrise`.

Validation:
- [x] `ha core check`
- [x] Reload scripts/automations or restart core
- [ ] Manual test run completed
- Notes:
  - Deployed `/homeassistant/automations.yaml` and ran `ha core check` successfully.
  - Reloaded automations via `automation.reload` service.
  - Verified no drift with `make verify`.

Rollback:
- Remove automation `lighting_common_friday_morning_0650_presunrise` from `/homeassistant/automations.yaml`.

Requested by:
- Project user

Implemented by:
- Codex

---

## 2026-02-24 - Add UI form script for manual Tado gas baseline correction

Summary:
- Added a script with input fields so manual gas meter corrections can be entered from a Home Assistant form instead of manual helper edits.

Files changed:
- snapshots/homeassistant/scripts.yaml
- docs/homeassistant_configuration_reference.md
- docs/change_log.md

Details:
- Added script:
  - `tado_gas_set_manual_baseline`
- Script inputs (form fields):
  - `manual_reading` (required whole number)
  - `submission_date` (optional date; defaults to today when omitted)
- Script behavior:
  - reads current helper `input_number.tado_gas_meter_register_m3`
  - preserves fractional carry from helper
  - sets corrected helper baseline to `manual_reading + fractional_carry`
  - updates `input_datetime.tado_gas_meter_last_submission_date`
  - creates a confirmation `persistent_notification`
- Updated config reference:
  - script inventory includes `tado_gas_set_manual_baseline`
  - Tado gas section documents form usage

Validation:
- [x] `ha core check`
- [x] Reload scripts/automations or restart core
- [ ] Manual test run completed
- Notes:
  - Deployed `/homeassistant/scripts.yaml`, reloaded scripts via `script.reload`, and verified `script.tado_gas_set_manual_baseline` is available.

Rollback:
- Remove `tado_gas_set_manual_baseline` from `/homeassistant/scripts.yaml`.

Requested by:
- Project user

Implemented by:
- Codex

---

## 2026-02-24 - Fix Tado daily gas submission resets after restart

Summary:
- Fixed repeated `invalid new reading` failures in the daily Tado gas submission automation by removing helper reset behavior on core restart.
- Recovered with a one-time manual catch-up meter submission.

Files changed:
- snapshots/homeassistant/automations.yaml
- snapshots/homeassistant/configuration.yaml
- docs/change_log.md

Details:
- Root cause:
  - `input_number.tado_gas_meter_register_m3` and `input_datetime.tado_gas_meter_last_submission_date` were configured with `initial` values.
  - After core restarts, helpers reset to those fixed initial values, causing computed Tado readings to move backward and fail with:
    - `invalid new reading`
- Evidence from history:
  - Helper register advanced successfully to `26521.044` on `2026-02-22`, then reset back to `26512.0` after restart.
  - Automation failures logged at `2026-02-23 16:00` and `2026-02-24 16:00`.
- Permanent fix:
  - Removed `initial` from:
    - `input_number.tado_gas_meter_register_m3`
    - `input_datetime.tado_gas_meter_last_submission_date`
  - This allows HA restore-state to persist helper values across restarts.
- Robustness improvement in `tado_gas_meter_reading_daily_from_octopus`:
  - Added guard so `tado.add_meter_reading` only runs when computed integer reading increases over previous integer.
  - When integer does not increase, automation still updates helper register/date so fractional consumption carries forward.
- Recovery action:
  - Submitted one-time catch-up Tado reading via service call:
    - `tado.add_meter_reading`
    - `config_entry: 01KJ0N1WQ9792EY1JBD0HYA63E`
    - `reading: 26533`
  - Service response returned success (`[]`).

Validation:
- [ ] `ha core check`
- [ ] Reload scripts/automations or restart core
- [ ] Manual test run completed
- Notes:
  - Next step after deploy is to set helper states to post-catch-up baseline and verify persistence across restart.

Rollback:
- Re-add helper `initial` values in `/homeassistant/configuration.yaml` for the two Tado helpers (not recommended).

Requested by:
- Project user

Implemented by:
- Codex

---

## 2026-02-23 - Fix hot water pump trigger to use Tado power demand sensor

Summary:
- Investigated missed hot-water pump runs and replaced the trigger signal so the automation follows actual Tado hot-water demand.

Files changed:
- snapshots/homeassistant/automations.yaml
- docs/change_log.md

Details:
- Root cause found from live HA history:
  - `water_heater.hot_water` stayed `auto` during real hot-water demand windows on `2026-02-23` (`05:56` and `17:00` UTC), so the previous state-transition condition did not fire.
  - The previous automation did fire at `2026-02-22T17:38:37Z` during Tado recovery (`unavailable -> auto`), which is a false-positive pattern.
- Updated automation `hot_water_pump_follow_tado_on_for_1h`:
  - trigger changed from `water_heater.hot_water` state-change template to:
    - `binary_sensor.hot_water_power`
    - `from: "off"`
    - `to: "on"`
  - added guard condition:
    - pump switch must currently be `off` before starting the run
  - mode changed:
    - `restart` -> `single` to avoid delay restarts from brief sensor dropouts while pump is already running

Validation:
- [x] `ha core check`
- [x] Reload scripts/automations or restart core
- [ ] Manual test run completed
- Notes:
  - Live API investigation completed on 2026-02-23:
    - `binary_sensor.hot_water_power` showed on/off demand transitions
    - `water_heater.hot_water` remained `auto` across the same window
  - Deployment validation completed on 2026-02-23:
    - uploaded updated `/homeassistant/automations.yaml`
    - `ha core check` passed
    - `ha core restart` completed successfully
    - deployed file MD5 matches snapshot MD5 (`8c2c8403e79f2becb4abe59bf99bf436`)

Rollback:
- In `/homeassistant/automations.yaml`, restore `hot_water_pump_follow_tado_on_for_1h` trigger/condition to previous `water_heater.hot_water` template logic and `mode: restart`.

Requested by:
- Project user

Implemented by:
- Codex

---

## 2026-02-23 - Set morning lights to 80% and add evening 100% -> 80% schedule

Summary:
- Updated morning lighting automations to turn on at 80%.
- Updated evening start automations to turn on at 100%, then added a 19:00 dim step to 80% for currently-on evening target lights.

Files changed:
- snapshots/homeassistant/automations.yaml
- docs/lighting_reusable_components.md
- docs/homeassistant_configuration_reference.md
- docs/change_log.md

Details:
- Updated `lighting_common_weekday_morning_0620_presunrise`:
  - replaced `script.lighting_common_areas` (`profile: day`) with direct `light.turn_on`
  - new settings: `brightness_pct: 80`, `color_temp_kelvin: 4000`, `transition: 2`
- Updated `lighting_front_porch_on_0620_presunrise`:
  - replaced script wrapper call with direct `light.turn_on` at `brightness_pct: 80`, `color_temp_kelvin: 4000`, `transition: 2`
- Updated `lighting_common_evening_sunset_on_seasonal`:
  - common + lounge area action now starts at `brightness_pct: 100`, `color_temp_kelvin: 2700`, `transition: 3`
  - `light.office_filament` now starts at `brightness_pct: 100` (from 80)
- Updated `lighting_front_porch_on_at_sunset`:
  - now starts at `brightness_pct: 100`, `color_temp_kelvin: 2700`, `transition: 2`
- Added new automation `lighting_evening_dim_1900`:
  - trigger: daily `19:00:00`
  - builds a runtime list of currently-on light entities in evening target areas (`attic_lounge`, `dining_room`, `kitchen`, `hallway`, `landing`, `side_hall`, `living_room`, `front_porch`) plus `light.office_filament`
  - applies `brightness_pct: 80`, `color_temp_kelvin: 2700`, `transition: 3` to that list
  - includes guard condition to skip action when no target lights are currently on

Validation:
- [x] `ha core check`
- [x] Reload scripts/automations or restart core
- [ ] Manual test run completed
- Notes:
  - Local environment did not have a YAML parser (`python3` missing `PyYAML`), so local YAML parse was not run.
  - Live validation completed on 2026-02-23:
    - `ha core check` passed
    - `ha core restart` completed successfully
    - deployed `/homeassistant/automations.yaml` MD5 matches snapshot MD5

Rollback:
- Revert `snapshots/homeassistant/automations.yaml` to previous values for:
  - `lighting_common_weekday_morning_0620_presunrise`
  - `lighting_common_evening_sunset_on_seasonal`
  - `lighting_front_porch_on_at_sunset`
  - `lighting_front_porch_on_0620_presunrise`
- Remove automation `lighting_evening_dim_1900`.

Requested by:
- Project user

Implemented by:
- Codex

---

## 2026-02-22 - Include David's Office filament in sunset evening-on automation

Summary:
- Added David's Office filament light to the seasonal sunset evening-on routine.

Files changed:
- /homeassistant/automations.yaml
- snapshots/homeassistant/automations.yaml
- docs/lighting_reusable_components.md
- docs/change_log.md

Details:
- Updated automation:
  - `lighting_common_evening_sunset_on_seasonal`
- Added explicit action after profile-based area activation:
  - `light.turn_on` -> `light.office_filament`
  - settings: `brightness_pct: 80`, `color_temp_kelvin: 2700`, `transition: 3`
- Existing common-area + Lounge target behavior remains unchanged.

Validation:
- [ ] `ha core check`
- [ ] Reload scripts/automations or restart core
- [ ] Manual test run completed
- Notes:
  - Change is scoped only to the sunset evening-on automation.

Rollback:
- Remove the `light.office_filament` action block from `lighting_common_evening_sunset_on_seasonal`.

Requested by:
- Project user

Implemented by:
- Codex

---

## 2026-02-22 - Increase evening lighting profile brightness to 80%

Summary:
- Updated the shared evening lighting profile brightness from 45% to 80%.

Files changed:
- /homeassistant/scripts.yaml
- snapshots/homeassistant/scripts.yaml
- docs/lighting_reusable_components.md
- docs/change_log.md

Details:
- Updated script:
  - `lighting_apply_profile_core`
- Profile default change:
  - `evening` brightness `45` -> `80`
  - color temperature unchanged at `2700K`
- Impact:
  - Any automation/script that uses `profile: evening` via the reusable lighting framework now sets lights to 80% by default.

Validation:
- [ ] `ha core check`
- [ ] Reload scripts/automations or restart core
- [ ] Manual test run completed
- Notes:
  - Change is centralized in one script; no automation ID changes required.

Rollback:
- Set `brightness_pct` for evening/default branch in `/homeassistant/scripts.yaml` back to `45`.

Requested by:
- Project user

Implemented by:
- Codex

---

## 2026-02-22 - Reduce winter seasonal offset default to 45 minutes

Summary:
- Updated the shared seasonal lighting helper so winter offset defaults use 45 minutes instead of 60 minutes.

Files changed:
- /homeassistant/scripts.yaml
- snapshots/homeassistant/scripts.yaml
- docs/lighting_reusable_components.md
- docs/change_log.md

Details:
- Updated script:
  - `lighting_wait_seasonal_offset`
- Changed winter defaults:
  - `winter_minutes` example: `60` -> `45`
  - runtime default: `winter_minutes | default(45) | int(45)`
- Effect:
  - Sunset seasonal-minus automation now runs 15 minutes later in winter than before.
  - Sunrise seasonal-plus off runs 15 minutes earlier in winter than before.

Validation:
- [ ] `ha core check`
- [ ] Reload scripts/automations or restart core
- [ ] Manual test run completed
- Notes:
  - This change relies on central script defaults; no automation IDs needed modification.

Rollback:
- Restore `winter_minutes` script default from `45` back to `60` in `/homeassistant/scripts.yaml`.

Requested by:
- Project user

Implemented by:
- Codex

---

## 2026-02-22 - Fix Tado gas submission to use cumulative register value

Summary:
- Reworked the Tado gas meter automation so it submits a derived cumulative meter register value, not raw daily gas usage.

Files changed:
- /homeassistant/automations.yaml
- /homeassistant/configuration.yaml
- snapshots/homeassistant/automations.yaml
- snapshots/homeassistant/configuration.yaml
- docs/homeassistant_configuration_reference.md
- docs/change_log.md

Details:
- Updated automation:
  - `tado_gas_meter_reading_daily_from_octopus`
- Previous behavior:
  - Sent `sensor.octopus_energy_gas_e6s10414361656_2215950002_previous_accumulative_consumption_m3` directly to Tado.
  - This is daily usage and not a true meter register.
- New behavior:
  - Adds daily usage to a stored helper register and submits the resulting cumulative reading.
  - Uses current Tado service schema for HA `2026.2.3`:
    - `tado.add_meter_reading` with `config_entry` + `reading`
    - removed unsupported keys `utility` and `date` (error seen: `extra keys not allowed @ data['utility']`)
  - Helper entities:
    - `input_number.tado_gas_meter_register_m3` (initial `26512`)
    - `input_datetime.tado_gas_meter_last_submission_date` (initial `2026-02-21`)
  - Includes idempotency guard so the same day is not submitted twice.
  - Tado `reading` is submitted as an integer (no decimals).

Validation:
- [x] `ha core check`
- [x] Reload scripts/automations or restart core
- [ ] Manual test run completed
- Notes:
  - Current Octopus gas entities do not expose an absolute meter register entity in this HA instance.

Rollback:
- Revert `tado_gas_meter_reading_daily_from_octopus` to direct sensor posting and remove helper definitions from `/homeassistant/configuration.yaml`.

Requested by:
- Project user

Implemented by:
- Codex

---

## 2026-02-22 - Add daily Octopus-to-Tado gas meter submission

Summary:
- Added a daily automation that submits gas meter readings to Tado using the Octopus Energy `previous_accumulative_consumption_m3` sensor.

Files changed:
- /homeassistant/automations.yaml
- snapshots/homeassistant/automations.yaml
- docs/homeassistant_configuration_reference.md
- docs/change_log.md

Details:
- Added automation ID:
  - `tado_gas_meter_reading_daily_from_octopus`
- Trigger:
  - Daily at `16:00:00`
- Conditions:
  - Source sensor must not be unknown/unavailable.
  - Source sensor must parse as a non-negative number.
- Action:
  - `tado.add_meter_reading`
  - `utility: gas`
  - `reading` from:
    - `sensor.octopus_energy_gas_e6s10414361656_2215950002_previous_accumulative_consumption_m3`
  - `date` set to yesterday (`YYYY-MM-DD`) to match Octopus `previous_*` data semantics.
- Mode:
  - `single`

Validation:
- [ ] `ha core check`
- [ ] Reload scripts/automations or restart core
- [ ] Manual test run completed
- Notes:
  - Live server registry confirms source sensor exists and provides numeric `m3` values.

Rollback:
- Remove automation `tado_gas_meter_reading_daily_from_octopus` from `/homeassistant/automations.yaml` and reload automations.

Requested by:
- Project user

Implemented by:
- Codex

---

## 2026-02-22 - Add hot water to pump follow automation (1 hour run)

Summary:
- Added automation to run the Meross water pump for one hour whenever Tado hot water is turned on from an off state.

Files changed:
- /homeassistant/automations.yaml
- snapshots/homeassistant/automations.yaml
- docs/homeassistant_configuration_reference.md
- docs/change_log.md

Details:
- Added automation ID:
  - `hot_water_pump_follow_tado_on_for_1h`
- Trigger:
  - `water_heater.hot_water` state change event
  - guard condition allows only transitions from not-on -> on-like:
    - from state not in `auto`, `heat`, `on`
    - to state in `auto`, `heat`, `on`
- Actions:
  - `switch.turn_on` -> `switch.smart_switch_2210176177851451030248e1e9aba3d4_outlet` (Water Pump)
  - delay `01:00:00`
  - `switch.turn_off` -> same entity
- Mode:
  - `restart` (if retriggered while running, the 1-hour window restarts from the latest trigger)

Validation:
- [x] `ha core check`
- [ ] Reload scripts/automations or restart core
- [ ] Manual test run completed
- Notes:
  - Server-side config check completed successfully after automation update.

Rollback:
- Restore previous `/homeassistant/automations.yaml` from backup or prior git/snapshot copy.

Requested by:
- Project user

Implemented by:
- Codex

---

## 2026-02-22 - Add front porch sunset/morning schedules and naming cleanup

Summary:
- Added front porch automations for sunset-on, 23:00-off, 06:20 pre-sunrise-on, and sunrise-off.
- Reviewed automation naming clarity and adjusted one alias to better match behavior scope.

Files changed:
- /homeassistant/automations.yaml
- snapshots/homeassistant/automations.yaml
- docs/homeassistant_configuration_reference.md
- docs/lighting_reusable_components.md
- docs/change_log.md

Details:
- Added:
  - `lighting_front_porch_on_at_sunset`
  - `lighting_front_porch_off_2300`
  - `lighting_front_porch_on_0620_presunrise`
  - `lighting_front_porch_off_at_sunrise`
- Front porch actions use `script.lighting_outside` for consistent outside-light control.
- Naming clarity audit:
  - Updated alias for `lighting_common_weekday_morning_0620_presunrise` from:
    - `Lighting - Common Areas On 06:20 Weekdays Pre-Sunrise`
    - to `Lighting - Common Areas On 06:20 Mon-Thu Pre-Sunrise`
  - Other automation aliases were reviewed and retained as sufficiently descriptive.

Validation:
- [x] `ha core check`
- [ ] Reload scripts/automations or restart core
- [ ] Manual test run completed
- Notes:
  - Server-side config check completed successfully after applying updated `automations.yaml`.

Rollback:
- Restore previous `/homeassistant/automations.yaml` from backup or prior git/snapshot copy.

Requested by:
- Project user

Implemented by:
- Codex

---

## 2026-02-22 - Reusable lighting framework

Summary:
- Added reusable lighting scripts and scheduled automations for dusk on + 02:00 shutdown.

Files changed:
- /config/scripts.yaml
- /config/automations.yaml
- docs/lighting_reusable_components.md
- docs/homeassistant_configuration_reference.md
- docs/codex_change_playbook.md

Details:
- Added core script: `lighting_apply_profile_core`.
- Added wrappers: `lighting_common_areas`, `lighting_bedrooms`, `lighting_outside`.
- Added automations:
  - `lighting_common_evening_dusk_on`
  - `lighting_overnight_shutdown_0200`

Validation:
- [x] `ha core check`
- [ ] Reload scripts/automations or restart core
- [ ] Manual test run completed
- Notes:
  - CLI on this host did not support `ha service call`; reload must be done in UI or by restart.

Rollback:
- Restore previous versions of `/config/scripts.yaml` and `/config/automations.yaml`.

Requested by:
- Project user

Implemented by:
- Codex

---

## 2026-02-22 - Add late-evening common+lounge dim/off schedules

Summary:
- Added requested late-evening dim and off schedules for common areas plus Lounge with separate weekday/weekend times.
- Confirmed sunset-on seasonal automation already included Lounge (`living_room`), so no extra target change was needed there.

Files changed:
- /homeassistant/automations.yaml
- snapshots/homeassistant/automations.yaml
- docs/homeassistant_configuration_reference.md
- docs/lighting_reusable_components.md
- docs/change_log.md

Details:
- Added dim automations:
  - `lighting_common_lounge_dim_2215_sun_thu` -> 22:15 on Sun-Thu to `brightness_pct: 15`
  - `lighting_common_lounge_dim_2330_fri_sat` -> 23:30 on Fri-Sat to `brightness_pct: 15`
- Added off automations:
  - `lighting_common_lounge_off_2300_sun_thu` -> 23:00 on Sun-Thu
  - `lighting_common_lounge_off_2359_fri_sat` -> 23:59 on Fri-Sat
- All new automations target:
  - Common areas (`attic_lounge`, `dining_room`, `kitchen`, `hallway`, `landing`, `side_hall`)
  - Plus Lounge (`living_room`)

Validation:
- [x] `ha core check`
- [ ] Reload scripts/automations or restart core
- [ ] Manual test run completed
- Notes:
  - Server-side config check completed successfully after applying updated `automations.yaml`.

Rollback:
- Restore previous `/homeassistant/automations.yaml` from backup or prior git/snapshot copy.

Requested by:
- Project user

Implemented by:
- Codex

---

## 2026-02-22 - Migrate Ren area ID typo to `ren_s_bedroom`

Summary:
- Migrated Ren's Bedroom internal `area_id` from typo `ren_s_bedrrom` to `ren_s_bedroom` while keeping visible name `Ren's Bedroom`.

Files changed:
- /config/scripts.yaml
- /config/.storage/core.area_registry
- /config/.storage/core.device_registry
- docs/change_log.md

Details:
- Created full pre-change backup:
  - slug: `6aa713ce`
  - name: `pre-ren-areaid-migration-2026-02-22`
- Applied ID migration to active files from `ren_s_bedrrom` to `ren_s_bedroom` in:
  - `/config/scripts.yaml`
  - `/config/.storage/core.area_registry`
  - `/config/.storage/core.device_registry`
- Confirmed on follow-up that `core.device_registry` still contained old IDs, then performed a second corrective pass:
  - temporarily set `ha core options --watchdog=false`
  - stopped core, patched `/config/.storage/core.device_registry`, and restarted core
  - restored `ha core options --watchdog=true`
- Confirmed area registry now reports:
  - `id: "ren_s_bedroom"`
  - `name: "Ren's Bedroom"`
- Created file-level rollback copies:
  - `/config/.storage/core.area_registry.bak.1771765942`
  - `/config/.storage/core.device_registry.bak.1771765942`
  - `/config/scripts.yaml.bak.1771765942`
  - `/config/.storage/core.device_registry.bak.1771766500`

Validation:
- [x] `ha core check`
- [x] Reload scripts/automations or restart core
- [ ] Manual test run completed
- Notes:
  - `ha core check --raw-json` returned `{\"result\":\"ok\",\"data\":{}}`.
  - `ha core stats --raw-json` returned `{\"result\":\"ok\", ...}` after restart.
  - No remaining `ren_s_bedrrom` references found in active text config/registry files.

Rollback:
- Option 1 (preferred): restore full backup `6aa713ce`.
- Option 2: stop core, restore `.bak.1771765942` and/or `.bak.1771766500` files over current files, then start core.

Requested by:
- Project user

Implemented by:
- Codex

---

## 2026-02-22 - Fix script field type errors in lighting core

Summary:
- Fixed Home Assistant script schema errors preventing `script.lighting_apply_profile_core` from loading.

Files changed:
- /config/scripts.yaml
- docs/change_log.md

Details:
- Quoted `on`/`off` options in `fields.action.selector.select.options` to force string type.
- Changed `fields.target_areas.example` from a YAML list to a string example.
- Quoted `on`/`off` examples in wrapper fields for consistency and to avoid YAML boolean coercion.

Validation:
- [x] `ha core check`
- [ ] Reload scripts/automations or restart core
- [ ] Manual test run completed
- Notes:
  - `ha core check` completed successfully after applying the fix.

Rollback:
- Revert `/config/scripts.yaml` to the previous revision before this fix.

Requested by:
- Project user

Implemented by:
- Codex

---

## 2026-02-22 - Fix overnight shutdown action coercion bug

Summary:
- Fixed a logic bug where YAML boolean coercion could cause `action: off` to be treated as `on`.

Files changed:
- /config/scripts.yaml
- /config/automations.yaml
- docs/change_log.md

Details:
- In `/config/automations.yaml`, quoted `action` values (`\"on\"` / `\"off\"`) so they remain strings.
- In `/config/scripts.yaml`, removed `default(..., true)` usage in wrapper calls that could coerce falsey values to `on`.
- In `/config/scripts.yaml`, added defensive normalization in `lighting_apply_profile_core`:
  - normalize action to `on`/`off` from string/boolean input
  - normalize profile with fallback to `evening`
  - normalize transition with integer fallback

Validation:
- [x] `ha core check`
- [ ] Reload scripts/automations or restart core
- [ ] Manual test run completed
- Notes:
  - Validation passed after applying fixes.

Rollback:
- Restore prior versions of `/config/scripts.yaml` and `/config/automations.yaml`.

Requested by:
- Project user

Implemented by:
- Codex

---

## 2026-02-22 - Add weekday 06:20 pre-sunrise on and seasonal sunrise off

Summary:
- Added morning common-area lighting automation for Monday-Thursday at 06:20 (only before sunrise).
- Added a seasonal sunrise-based off automation with variable delays by season.

Files changed:
- /config/automations.yaml
- docs/lighting_reusable_components.md
- docs/homeassistant_configuration_reference.md
- docs/change_log.md

Details:
- Added `lighting_common_weekday_morning_0620_presunrise`:
  - trigger at `06:20:00`
  - condition: weekday Monday-Thursday
  - condition: before sunrise
  - action: `script.lighting_common_areas` with `action: \"on\"`, `profile: \"day\"`
- Added `lighting_common_weekday_morning_off_after_sunrise_seasonal`:
  - trigger at sunrise
  - condition: weekday Monday-Thursday
  - delays:
    - summer (Jun-Aug): `00:15:00`
    - spring/autumn (Mar-May, Sep-Nov): `00:30:00`
    - winter (Dec-Feb): `01:00:00`
  - action: `script.lighting_common_areas` with `action: \"off\"`

Validation:
- [x] `ha core check`
- [ ] Reload scripts/automations or restart core
- [ ] Manual test run completed
- Notes:
  - Config validation completed successfully after automation update.

Rollback:
- Restore prior version of `/config/automations.yaml`.

Requested by:
- Project user

Implemented by:
- Codex

---

## 2026-02-22 - Change seasonal post-sunrise off to run daily

Summary:
- Updated seasonal sunrise-based common-area lights off automation to run every day instead of weekdays only.

Files changed:
- /config/automations.yaml
- docs/lighting_reusable_components.md
- docs/change_log.md

Details:
- In `lighting_common_weekday_morning_off_after_sunrise_seasonal`:
  - removed weekday condition (`mon`-`thu`)
  - now runs daily at sunrise with existing seasonal delays:
    - summer: `00:15:00`
    - spring/autumn: `00:30:00`
    - winter: `01:00:00`
- Kept `lighting_common_weekday_morning_0620_presunrise` unchanged (still Monday-Thursday only).

Validation:
- [x] `ha core check`
- [ ] Reload scripts/automations or restart core
- [ ] Manual test run completed
- Notes:
  - Config validation completed successfully after update.

Rollback:
- Restore prior version of `/config/automations.yaml`.

Requested by:
- Project user

Implemented by:
- Codex

---

## 2026-02-22 - Rename dusk to sunset and reuse seasonal delay script

Summary:
- Renamed the dusk common-area automation to sunset naming.
- Extracted seasonal timing into reusable script logic and applied it to both sunset-on and sunrise-off automations.

Files changed:
- /config/scripts.yaml
- /config/automations.yaml
- docs/lighting_reusable_components.md
- docs/homeassistant_configuration_reference.md
- docs/change_log.md

Details:
- Added new helper script: `lighting_wait_seasonal_delay`.
- Replaced `lighting_common_evening_dusk_on` with `lighting_common_evening_sunset_on_seasonal`.
- Sunset automation now calls seasonal-delay helper before turning on common-area lights.
- Sunrise-off automation now calls the same seasonal-delay helper before turning off common-area lights.
- Seasonal delays remain:
  - summer: `00:15:00`
  - spring/autumn: `00:30:00`
  - winter: `01:00:00`

Validation:
- [x] `ha core check`
- [ ] Reload scripts/automations or restart core
- [ ] Manual test run completed
- Notes:
  - Config validation completed successfully after script and automation updates.

Rollback:
- Restore prior versions of `/config/scripts.yaml` and `/config/automations.yaml`.

Requested by:
- Project user

Implemented by:
- Codex

---

## 2026-02-22 - Move sunset seasonal timing to pre-sunset offsets

Summary:
- Updated sunset automation so common-area lights turn on before sunset using seasonal offsets.

Files changed:
- /config/automations.yaml
- docs/lighting_reusable_components.md
- docs/change_log.md

Details:
- In `lighting_common_evening_sunset_on_seasonal`:
  - replaced sunset trigger + post-trigger delay with three pre-sunset triggers:
    - summer: `-00:15:00`
    - spring/autumn: `-00:30:00`
    - winter: `-01:00:00`
  - added trigger-id/month guard condition so only the matching seasonal trigger runs.
- Kept sunrise seasonal off automation unchanged and still using `script.lighting_wait_seasonal_delay`.

Validation:
- [x] `ha core check`
- [ ] Reload scripts/automations or restart core
- [ ] Manual test run completed
- Notes:
  - Config validation completed successfully after update.

Rollback:
- Restore prior version of `/config/automations.yaml`.

Requested by:
- Project user

Implemented by:
- Codex

---

## 2026-02-22 - Unify sunrise/sunset offsets in common plus/minus script

Summary:
- Moved seasonal timing control for sunrise and sunset into one common script with explicit plus/minus offset behavior.

Files changed:
- /config/scripts.yaml
- /config/automations.yaml
- docs/lighting_reusable_components.md
- docs/homeassistant_configuration_reference.md
- docs/change_log.md

Details:
- Replaced `lighting_wait_seasonal_delay` with `lighting_wait_seasonal_offset`.
- New common script supports:
  - `offset_direction: plus` for morning (add time after sunrise).
  - `offset_direction: minus` for evening (turn on earlier before sunset using an anchor trigger).
- Updated sunrise-off automation to call helper with `offset_direction: plus`.
- Updated sunset-on automation to:
  - trigger at anchor `sunset -01:00:00`
  - call helper with `offset_direction: minus`
  - then turn common lights on.
- Centralized seasonal offset values in script defaults so automations no longer duplicate minute values.

Validation:
- [x] `ha core check`
- [ ] Reload scripts/automations or restart core
- [ ] Manual test run completed
- Notes:
  - Config validation completed successfully after helper refactor.

Rollback:
- Restore prior versions of `/config/scripts.yaml` and `/config/automations.yaml`.

Requested by:
- Project user

Implemented by:
- Codex

---

## 2026-02-22 - Replace Lounge with Attic Lounge in common set and add Lounge to sunset-on

Summary:
- Removed Lounge from the reusable common-area set and added Attic Lounge.
- Added Lounge as a separate target specifically for sunset-on lighting.

Files changed:
- /config/scripts.yaml
- /config/automations.yaml
- docs/lighting_reusable_components.md
- docs/change_log.md

Details:
- Updated `script.lighting_common_areas` target list:
  - removed `living_room`
  - added `attic_lounge`
- Updated `lighting_common_evening_sunset_on_seasonal` action:
  - now calls `script.lighting_apply_profile_core` with combined areas:
    - common set (including `attic_lounge`)
    - separate `living_room` (Lounge)
- Kept sunrise/morning/off automations unchanged apart from inherited common-area membership changes.

Validation:
- [x] `ha core check`
- [ ] Reload scripts/automations or restart core
- [ ] Manual test run completed
- Notes:
  - Config validation completed successfully after area-target update.

Rollback:
- Restore prior versions of `/config/scripts.yaml` and `/config/automations.yaml`.

Requested by:
- Project user

Implemented by:
- Codex

---

## 2026-02-22 - Rename sunrise off automation and switch to all-lights off

Summary:
- Renamed the seasonal post-sunrise off automation.
- Changed behavior from turning off common-area lights to turning off all lights.

Files changed:
- /config/automations.yaml
- docs/lighting_reusable_components.md
- docs/homeassistant_configuration_reference.md
- docs/change_log.md

Details:
- Renamed:
  - `lighting_common_weekday_morning_off_after_sunrise_seasonal`
  - -> `lighting_all_lights_off_after_sunrise_seasonal`
- Updated action flow:
  - keep seasonal wait via `script.lighting_wait_seasonal_offset` with `offset_direction: plus`
  - then call `light.turn_off` with `transition: 2` (all lights)

Validation:
- [x] `ha core check`
- [ ] Reload scripts/automations or restart core
- [ ] Manual test run completed
- Notes:
  - Config validation completed successfully after rename and behavior change.

Rollback:
- Restore prior version of `/config/automations.yaml`.

Requested by:
- Project user

Implemented by:
- Codex

---

## 2026-02-22 - Add explicit script IDs to remove UI migration warnings

Summary:
- Added explicit `id` fields to YAML scripts so Home Assistant can map/edit them in UI without migration prompts.

Files changed:
- /config/scripts.yaml
- docs/change_log.md

Details:
- Added `id` values to:
  - `lighting_apply_profile_core`
  - `lighting_common_areas`
  - `lighting_bedrooms`
  - `lighting_outside`
  - `lighting_wait_seasonal_offset`
- IDs match each script key name for stability.

Validation:
- [x] `ha core check`
- [ ] Reload scripts/automations or restart core
- [ ] Manual test run completed
- Notes:
  - Config validation completed successfully after adding script IDs.

Rollback:
- Restore prior version of `/config/scripts.yaml`.

Requested by:
- Project user

Implemented by:
- Codex

---

## 2026-02-22 - Remove invalid script IDs after HA schema error

Summary:
- Removed `id` fields from scripts after Home Assistant rejected them.

Files changed:
- /config/scripts.yaml
- docs/lighting_reusable_components.md
- docs/change_log.md

Details:
- Error observed:
  - `extra keys not allowed @ data['id']`
- Removed `id` keys from all script definitions in `/config/scripts.yaml`.
- Clarified docs rule:
  - automations should have `id`
  - scripts in `scripts.yaml` must not have `id`

Validation:
- [x] `ha core check`
- [ ] Reload scripts/automations or restart core
- [ ] Manual test run completed
- Notes:
  - Config validation completed successfully after removing script IDs.

Rollback:
- Restore prior version of `/config/scripts.yaml`.

Requested by:
- Project user

Implemented by:
- Codex

---

## 2026-02-22 - Fix all-lights sunrise automation target and rerun behavior

Summary:
- Fixed the post-sunrise all-lights automation so it can successfully turn off lights.
- Changed mode to avoid "Already running" blocking during manual tests.

Files changed:
- /config/automations.yaml
- docs/lighting_reusable_components.md
- docs/change_log.md

Details:
- In `lighting_all_lights_off_after_sunrise_seasonal`:
  - changed `light.turn_off` call to include explicit target:
    - `target.entity_id: all`
  - changed automation `mode` from `single` to `restart`.
- Root cause from HA log:
  - `must contain at least one of entity_id, device_id, area_id, floor_id, label_id`

Validation:
- [x] `ha core check`
- [ ] Reload scripts/automations or restart core
- [ ] Manual test run completed
- Notes:
  - Config validation completed successfully after target and mode changes.

Rollback:
- Restore prior version of `/config/automations.yaml`.

Requested by:
- Project user

Implemented by:
- Codex
