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

## 2026-08-31 - Sync Renault state of charge to Ohme on plug-in

Summary:
- Ohme has disabled its own Renault integration, so Ohme no longer knows the car's real
  battery level and sizes its charge plan from what it *thinks* it has added.
- Added `ev_ohme_sync_renault_state_of_charge` to push the Renault's true percentage into
  Ohme while it is plugged in at home. Informational only - it cannot start a charge.

Files changed:
- /config/automations.yaml (new automation appended)
- /config/.storage/core.entity_registry (enabled one disabled-by-default entity)
- CLAUDE.md, docs/dashboard_automation_plan.md (new item 12)
- docs/change_log.md
- snapshots/homeassistant/* (re-synced from live)

Details:

1. Enabled the entity that already existed for this
   - HA 2026.8.3 ships `ohme==1.9.1`, whose number platform defines a `state_of_charge_input`
     entity for exactly this purpose. It is `entity_registry_enabled_default=False` upstream,
     so it had never appeared.
   - Enabled `number.utilities_ohme_home_pro_state_of_charge_input` via
     `config/entity_registry/update` (disabled_by -> None), then reloaded the ohme config
     entry. Entity is live: min 0, max 100, step 1, unit %.
   - Its upstream `available_fn` is `client.status.value != "unplugged"`, so the entity only
     exists while a car is connected. The "only when plugged in" requirement is therefore
     enforced by the integration, not just by automation conditions.

2. Confirmed it cannot cause a charge (this was the explicit requirement)
   - `OhmeApiClient.async_set_state_of_charge` issues exactly one request:
       PUT /v1/car/{car_id}/state-of-charge   {"currentChargePercent": N}
   - It never touches /chargeSessions/{serial}/approve, /resume, /stop, or max-charge.
     Those are separate methods bound to separate entities (button.approve_charge,
     select.charge_mode). The automation writes only the number, so it cannot request power.
   - `switch.ohme_home_pro_require_approval` is on, so on a fresh plug-in the write lands
     while the session is still PENDING_APPROVAL - a hard gate before any delivery.
   - Caveat recorded: telling Ohme mid-session that the battery is emptier than it thought
     may make it recompute and use more of its already-allowed window. That is correct
     behaviour, not a new charge, but it is a behaviour change.

3. Shared-charger handling
   - The Ohme account lists two vehicles, `Honda e:Ny1 (2023-)` (selected at the time) and
     `Renault Scenic (2023-2025)`. There are no Honda entities in HA at all.
   - Ohme applies state-of-charge to the *selected* vehicle: the library resolves
     `current_vehicle_id = self._cars[0]`, and documents "the selected vehicle is the first
     one in this list". Writing without switching would have written the Renault's figure
     onto the Honda's record.
   - The automation therefore selects the Renault first (`PUT /v1/car/{id}/select`, also
     incapable of starting a charge), then waits 30s. The vehicle select is backed by the
     30-minute device-info coordinator and its post-set refresh is debounced, so the delay
     is needed for `_cars[0]` to be the Renault before the write.
   - The Renault is identified as the car on the cable by BOTH
     `binary_sensor.renault_scenic_e_tech_plug` = on AND
     `device_tracker.renault_scenic_e_tech_location` = home. The location check exists
     because the Renault plugged in at work would otherwise make us switch Ohme to the
     Renault while the Honda is on the home charger.

4. Staleness handling
   - `sensor.renault_scenic_e_tech_battery` had not updated since 2026-08-29T10:40 - only
     5 samples in 3 days. The Renault cloud refreshes when the car phones home, not on demand.
   - So the automation triggers on the Ohme plug-in AND on the Renault battery sensor
     changing. The second trigger is what usually lands the accurate figure, once the car
     reports in shortly after being plugged in.
   - It skips the API write when Ohme already agrees to the nearest whole percent.

Coordinator cadence noted for future work:
- Ohme charge-session coordinator: 30 seconds (status, battery, mode, SoC value).
- Ohme device-info coordinator: 30 minutes (vehicle list/selection, `_cars`).

Validation:
- [x] `ha core check` - "Command completed successfully."
- [x] `automation.reload`; `automation.ev_sync_renault_state_of_charge_to_ohme` = on.
- [x] Guard templates rendered against live state via /api/template:
      ohme_status=unplugged, renault_plug=off, renault_loc=home, vehicle=Honda e:Ny1,
      SOC_GUARD=True (renault=85.0, ohme=84.0). Automation correctly inert while unplugged,
      and the 1% discrepancy confirms the underlying problem is real.
- [x] `make verify` - "No drift detected."
- [ ] MANUAL: first real plug-in of the Renault. Confirm
      `binary_sensor.renault_scenic_e_tech_plug` actually flips to `on` (it has not changed
      since the 2026-08-28 restart, so it is unproven), that the Ohme vehicle switches to
      Renault, that `number.utilities_ohme_home_pro_state_of_charge_input` becomes available
      and takes the value, and that no charge starts outside the Octopus-dispatched slots.

Rollback:
- Backup taken before mutation: `/homeassistant/automations.yaml.bak.1788181389` (on the HA host).
- Disable or delete `ev_ohme_sync_renault_state_of_charge` in automations.yaml, reload automations.
- Optionally re-disable `number.utilities_ohme_home_pro_state_of_charge_input` in
  Settings > Entities, and reselect the Honda in `select.ohme_home_pro_vehicle`.
- Earlier backups from today (epoch 1788180038) remain; per repo policy these `.bak.*` files
  may be cleaned up after 7 days with the deletion logged.

Known limitation:
- The automation leaves `Renault Scenic (2023-2025)` selected in Ohme after it runs. A
  subsequent Honda plug-in still needs the vehicle switched manually in the Ohme app - the
  same manual step as before, just from a different starting point.

Requested by:
- Project user

Implemented by:
- Claude Code

---

## 2026-08-31 - Clear Watchman missing-entity backlog; diagnose stalled Octopus gas feed

Summary:
- Investigated two persistent notifications: "Watchman Found Home Assistant Issues" (10 missing entities) and "Octopus Energy Gas Rollover Check Failed".
- Watchman backlog resolved: 10 -> 0 missing entities. Three distinct causes, three distinct fixes.
- Octopus gas rollover alert confirmed CORRECT and upstream. No config change made for it.

Files changed:
- /config/dashboards/utilities.yaml (removed 2 dead entity rows)
- /config/.storage/core.config_entries (Watchman `ignored_items`, via the integration's own options flow - not a raw file edit)
- CLAUDE.md (corrected stale Tado gas sync description)
- docs/change_log.md
- snapshots/homeassistant/* (re-synced from live)

Details:

1. Anglian Water (5 water_meter sensors unavailable)
   - Config entry `anglian_water` was in `state=setup_error`, `reason=auth_expired`.
   - A config-entry reload did NOT clear it (stored token could not refresh).
   - Re-authenticated by the project user via the UI. All 5 sensors now reporting
     (`sensor.water_meter_latest_reading` = 931.651).

2. Ohme (3 entities: `sensor.ohme_home_pro_energy`, `select.ohme_home_pro_charge_mode`,
   `sensor.ohme_home_pro_charge_slots`)
   - Not broken: these are charge-session-scoped and go unavailable/unknown while
     `sensor.ohme_home_pro_status` is `unplugged`. Integration is `loaded`; the other
     14 Ohme entities are healthy.
   - Added all three to Watchman `ignored_items` (30 -> 33 entries), matching the existing
     precedent of `button.ohme_home_pro_approve_charge` already being ignored.
   - Applied through the Watchman options flow API (POST /api/config/config_entries/options/flow),
     which is the supported path; `.storage` was not hand-edited.

3. Octopus legacy entities (2)
   - On octopus_energy 19.0.1, `binary_sensor.octopus_energy_a_e86380df_octoplus_saving_sessions`
     and `calendar.octopus_energy_a_e86380df_greener_nights` are no longer created by the
     integration (only a vestigial REFRESH_RATE_IN_MINUTES_GREENNESS_FORECAST constant remains).
     Both are permanently-unavailable orphans.
   - Removed both rows from the Octoplus card in `dashboards/utilities.yaml` (lines 76-77, 80-81).
   - Working replacements were already present on the card and remain:
     `calendar.octopus_energy_a_e86380df_octoplus_saving_sessions` (state `off`) and
     `event.octopus_energy_a_e86380df_octoplus_saving_session_events`.

4. Octopus gas rollover check - NO CONFIG CHANGE (alert is accurate)
   - Queried the Octopus API directly for half-hourly readings, BST-aligned local days:
       2026-08-27  gas 48/48  elec 48/48
       2026-08-28  gas 34/48 (stops 16:30)   elec 48/48
       2026-08-29  gas 35/48 (starts 07:00)  elec 48/48
       2026-08-30  gas 1 reading   elec 1 reading
       2026-08-31  gas 0           elec 0
   - Two gaps: a gas-only hole 28 Aug 17:00 -> 29 Aug 06:30, then BOTH meters stopped
     reporting after 30 Aug 00:30 BST (DCC/WAN comms outage).
   - The integration only publishes a complete day, so
     `sensor...gas..._previous_accumulative_consumption_kwh` is correctly pinned at
     27 Aug (1.651 m3 / 18.336 kWh). `supports_live_consumption` is false, so no Home Mini fallback.
   - Downstream impact is contained by design: `sensor.octopus_gas_statistics_total` (102.778)
     and `sensor.tado_gas_meter_register_derived` (27049.036) are frozen at 28 Aug; the weekly
     Tado automation dates readings at the statistics horizon so it will simply submit an
     older-dated reading once data recovers. `tado_gas_meter_submission_overdue_alert` would
     not fire until ~8 Sept (last submission 28 Aug + 10 days).
   - Action if unresolved in a few days: contact Octopus about smart-meter comms. Not an HA issue.

Also noted (NOT actioned - see Outstanding below):
- Four orphaned entity-registry entries remain, all permanently `unavailable` and now referenced
  by nothing: `input_number.tado_gas_meter_register_m3` and
  `automation.tado_submit_daily_gas_meter_reading_from_octopus` (leftovers from the 2026-07-12
  statistics-derived rework, `config_entry_id: None`), plus the two dead Octopus entities above
  (`platform: octopus_energy`, still attached to the loaded config entry but not recreated).
- HA upgraded 2026.7.2 -> 2026.8.3, HassOS 18.1 -> 18.2, Supervisor 2026.07.3 -> 2026.08.0,
  Docker 29.5.3 -> 29.6.2. Snapshots re-synced to match.

Validation:
- [x] `ha core check` - "Command completed successfully."
- [x] Utilities dashboard force-reloaded from disk (WS `lovelace/config`, `force: true`); 66 entity
      refs parsed, no dead refs remaining.
- [x] Watchman report regenerated (`button.watchman_create_report_file`):
      `sensor.watchman_missing_entities` 10 -> 0, `sensor.watchman_missing_actions` 0.
- [x] `automation.system_watchman_daily_check` re-triggered; it dismissed its own notification.
- [x] `make verify` - "No drift detected."
- Notes:
  - Both original notifications are now clear. The gas rollover check re-evaluates at 23:45 and
    will legitimately re-raise while Octopus data remains incomplete - that is expected and correct.

Rollback:
- Backups taken before any mutation (epoch 1788180038, on the HA host):
  - `/homeassistant/dashboards/utilities.yaml.bak.1788180038`
  - `/homeassistant/.storage/core.config_entries.bak.1788180038`
  - `/homeassistant/.storage/core.entity_registry.bak.1788180038`
- Dashboard: restore the `.bak.1788180038` copy, then force-reload the dashboard.
- Watchman ignore list: re-run the options flow and delete the three `sensor.ohme_*`/`select.ohme_*`
  entries from `ignored_items`, or restore the `core.config_entries` backup and restart core.
- Per repo policy these `.bak.*` files may be cleaned up after 7 days (i.e. on/after 2026-09-07),
  with the deletion logged.

Outstanding:
- Removal of the four orphaned entity-registry entries was blocked by the local tooling's
  permission classifier and was NOT performed. They are cosmetic clutter only (no YAML or
  dashboard references remain). Removal is reversible - each has a stable `unique_id`, so if an
  integration ever recreates them they return with the same entity_id.

Requested by:
- Project user

Implemented by:
- Claude Code

---

## 2026-07-16 - Move gas rollover health check from 19:00 to 23:45

Summary:
- Sensor history since 2026-07-01 shows previous-day Octopus gas data arrives next-day evening between 19:10 and 23:43 (usually ~22:30), so the 19:00 check almost always ran before that day's data landed. Moved the daily check to 23:45 so it normally runs after arrival.
- The 2-day staleness tolerance added earlier today is kept as the safety net for multi-day DCC gaps (two observed this month: 07-02/07-03 and 07-09/07-10).

Files changed:
- /config/automations.yaml
- docs/homeassistant_configuration_reference.md
- docs/change_log.md

Details:
- `octopus_energy_gas_rollover_health_daily_check` trigger `at` changed `19:00:00` -> `23:45:00`. No logic changes.

Validation:
- [x] `ha core check`
- [x] Reload automations via REST API
- [x] Read back trigger via `/api/config/automation/config`: `{'trigger': 'time', 'at': '23:45:00'}`
- [x] `make verify` clean

Rollback:
- Restore `/homeassistant/automations.yaml.bak.1784185343` (created this session), run `ha core check`, reload automations.

Requested by:
- David

Implemented by:
- Claude Code

---

## 2026-07-16 - Fix BST timezone bug and add lag tolerance to gas rollover health check

Summary:
- `octopus_energy_gas_rollover_health_daily_check` fired every evening since the clocks changed to BST: it extracted the `last_reset` date with a string slice (`raw[0:10]`), which reads the UTC date. Octopus reports `last_reset` as local midnight (e.g. `2026-07-13T23:00:00+00:00` = 2026-07-14 local), so during BST the check read one day behind and could never pass, even with on-time data.
- Additionally, Octopus/DCC gas data routinely lands late evening (observed 22:33 on 2026-07-15 for the 14th), after the 19:00 check, so a 1-day lag is normal and self-heals via statistics backfill.

Files changed:
- /config/automations.yaml
- docs/homeassistant_configuration_reference.md
- docs/change_log.md

Details:
- `gas_last_reset_date` now derived via `(gas_last_reset_raw | as_datetime | as_local).date()` instead of `gas_last_reset_raw[0:10]`.
- New `gas_days_behind` variable = expected date (yesterday, local) minus local last_reset date; unknown last_reset maps to 999.
- Alert condition changed from strict date equality to `gas_days_behind >= 2` (1 day of DCC lag tolerated); unknown/unavailable kWh state still alerts.
- Notification message now reports days behind plus expected/observed local dates.
- Old behavior -> new behavior: daily false alarm during BST -> alerts only when data is genuinely 2+ days stale or the sensor is unavailable.

Validation:
- [x] `ha core check`
- [x] Reload automations via REST API
- [x] Template API render: `local_date=2026-07-14 expected=2026-07-15 days_behind=1` (matches live sensor `last_reset: 2026-07-13T23:00:00+00:00`)
- [x] Manual `automation.trigger`: healthy path taken, persistent notification `octopus_energy_gas_rollover_health` dismissed (state read returns 404)
- [x] `make sync-ha` + `make verify` clean
- Notes: HA had been upgraded to 2026.7.2 since last sync; version info snapshots refreshed in the same sync.

Rollback:
- Restore `/homeassistant/automations.yaml.bak.1784184750` (created this session) over `/homeassistant/automations.yaml`, run `ha core check`, reload automations.
- Backup cleanup: none this session (permission denied for deleting May 2026 `.bak` files; `automations.yaml.bak.1779908696/.1779911495/.1779997812` remain past the 7-day retention window and can be removed manually).

Requested by:
- David

Implemented by:
- Claude Code

---

## 2026-07-12 - Add dated Tado meter-reading submissions via Energy Insights API

Summary:
- Replaced the undated `tado.add_meter_reading` action (which HA 2026.7.1 always dates "today") with a dated submission to the Tado Energy Insights API, so weekly readings are dated at the exact end of the underlying Octopus statistics data.
- The submission script owns an independent Tado OAuth device-code grant; it never touches the HA tado integration's rotating refresh token (sharing that token would break the integration's login).

Files changed:
- /config/scripts/tado_meter_reading.py (new)
- /config/configuration.yaml
- /config/automations.yaml
- repo: scripts/sync_from_ha.sh (added the new script to sync/verify list)

Details:
- New stdlib-only script `/config/scripts/tado_meter_reading.py`: `--login` one-time device-code authorization; `--submit N --date YYYY-MM-DD [--dry-run]` refreshes/rotates its own token and POSTs to `energy-insights.tado.com/api/homes/582180/meterReadings`.
- Token state at `/config/.tado_meter_token.json` (chmod 600, never synced to git). Exit code 2 signals a dead grant needing re-login; exit 1 transient failure.
- Added `shell_command.tado_submit_dated_meter_reading` (+ `_dry_run` variant) to configuration.yaml.
- Reworked `tado_gas_meter_reading_weekly_from_octopus`: reading date = end of last statistics row (`last_stat_ts` + 1h, local date); helpers update only on returncode 0; failure creates persistent notification `tado_gas_meter_submission_failed` (dismissed on next success) and retries the next day.
- Dropped the 4-day freshness condition: readings dated at their data horizon are accurate regardless of DCC lag, and the monotonic guard already blocks stale resubmission.
- One-time device-code login approved by David 2026-07-12; grant kept alive by weekly use (Tado idle expiry ~30 days).

Validation:
- [x] `ha core check`
- [x] Restart core (new `shell_command` domain)
- [x] Dry-run via API: `returncode 0`, "would POST reading=27007 date=2026-07-09 to home 582180" (token refresh + rotation exercised inside the core container)
- [x] Date template verified: reading=27007 date=2026-07-09
- [x] `make verify` clean; error log clean
- Notes: first real submission expected on/after 2026-07-17.

Rollback:
- Revert automation's actions to `tado.add_meter_reading` (see previous entry's YAML in git history), remove `shell_command:` block, restart core.
- Optionally delete `/homeassistant/scripts/tado_meter_reading.py` and `/homeassistant/.tado_meter_token.json` and revoke the grant in the Tado app.

Requested by:
- David

Implemented by:
- Claude Code

---

## 2026-07-12 - Rework Tado gas meter sync to statistics-derived register with weekly cadence

Summary:
- Replaced the fragile daily delta-accumulation gas register with a register derived from the Octopus integration's backfilled long-term statistics, and moved Tado submissions from daily to weekly.
- The old design sampled `previous_accumulative_consumption_m3` at 16:00 and assumed it was yesterday's data; late DCC data caused double-counting and missed days were unrecoverable. The new register self-heals because the external statistic (`octopus_energy:gas_..._previous_accumulative_consumption`) is backfilled retroactively by the integration.

Files changed:
- /config/configuration.yaml
- /config/automations.yaml
- /config/scripts.yaml

Details:
- Added `sql:` sensor `sensor.octopus_gas_statistics_total` reading the latest statistics `sum` (m³) plus `last_stat_ts` attribute from the recorder DB.
- Added template sensor `sensor.tado_gas_meter_register_derived` = `input_number.tado_gas_meter_baseline_m3` + statistics total.
- Replaced helper `input_number.tado_gas_meter_register_m3` (running accumulator) with `input_number.tado_gas_meter_baseline_m3` (fixed anchor) and added `input_number.tado_gas_meter_last_submitted_m3` (monotonic submission guard). Kept `input_datetime.tado_gas_meter_last_submission_date`.
- Removed automation `tado_gas_meter_reading_daily_from_octopus`; added `tado_gas_meter_reading_weekly_from_octopus` (checks daily at 18:00, submits only when >=7 days since last submission, statistics data <=4 days old, and integer register increased; failed preconditions retry the next day).
- Added automation `tado_gas_meter_submission_overdue_alert` (daily 19:00, persistent notification if no submission for >10 days, auto-dismisses when healthy).
- Reworked script `tado_gas_set_manual_baseline` to re-anchor from an actual physical meter reading (baseline = reading - statistics total).
- Cutover values preserved register continuity: old register 27007.466, statistics total 61.208 -> baseline 26946.258, last submitted 27007; derived register read back 27007.466 exactly.
- Note: `tado.add_meter_reading` in HA 2026.7.1 has no date parameter, so readings remain dated on submission day; a dated-submission path via the Tado Energy Insights API is planned as a follow-up.
- Maintenance caveat: the SQL sensor queries recorder `statistics`/`statistics_meta` tables directly; an HA schema change could break it, in which case submissions stop safely and the overdue alert fires within 10 days.

Validation:
- [x] `ha core check`
- [x] Restart core (required for new `sql` domain)
- [x] Read-back: SQL sensor 61.208 with fresh `last_stat_ts`, derived register 27007.466, both automations `on`, helpers set
- [x] `make verify` clean
- Notes: HA error log clean for sql/template/tado_gas after restart. Old helper `input_number.tado_gas_meter_register_m3` now an orphaned unavailable entity with no remaining references.

Rollback:
- Restore `/homeassistant/configuration.yaml.bak.1783852820`, `/homeassistant/automations.yaml.bak.1783852820`, `/homeassistant/scripts.yaml.bak.1783852820`.
- Restart core, then set `input_number.tado_gas_meter_register_m3` back to 27007.466 and `input_datetime.tado_gas_meter_last_submission_date` to 2026-07-10.

Requested by:
- David

Implemented by:
- Claude Code

---

## 2026-05-28 - Add Utilities dashboard

Summary:
- Added an admin-only YAML Utilities dashboard for Octopus, Ohme, Renault, water, gas, and hot water operations.
- Registered the dashboard in Lovelace with sidebar visibility.
- Updated the dashboard implementation plan and configuration reference.

Files changed:
- snapshots/homeassistant/configuration.yaml
- snapshots/homeassistant/dashboards/utilities.yaml
- docs/homeassistant_configuration_reference.md
- docs/dashboard_automation_plan.md
- docs/change_log.md

Details:
- Added YAML dashboard:
  - id: `energy-utilities`
  - title: `Utilities`
  - file: `/config/dashboards/utilities.yaml`
  - admin-only: `require_admin: true`
- Dashboard sections:
  - At A Glance
  - Electricity
  - Gas
  - Octoplus
  - EV Charging
  - Renault Scenic
  - EV Controls
  - Water
  - Hot Water
- Included Octopus tariff/usage/cost entities, Ohme charger status and controls, Renault charging/range entities, Anglian Water entities, Tado hot water demand/connectivity, and the hot water pump/timer.

Validation:
- [x] Confirmed referenced entities exist in the entity registry
- [x] Backup remote `/homeassistant/configuration.yaml`
- [x] `ha core check`
- [x] Restart Home Assistant Core
- [x] Live read-back of dashboard registration and dashboard YAML
- [x] `make verify`
- [ ] Manual UI review completed
- Notes:
  - Configuration backup created: `/homeassistant/configuration.yaml.bak.1779998997`
  - First `ha core check` failed because Lovelace dashboard URL keys must contain a hyphen; changed dashboard id from `utilities` to `energy-utilities`.
  - `ha core check` completed successfully after correcting the dashboard id.
  - Restarted Home Assistant Core successfully so the new Lovelace dashboard registration loads.
  - Live read-back confirmed `energy-utilities` in `/homeassistant/configuration.yaml`.
  - Live read-back confirmed `/homeassistant/dashboards/utilities.yaml` exists with `title: Utilities`.
  - `make verify` reported no drift.

Rollback:
- Restore `/homeassistant/configuration.yaml.bak.1779998997` to `/homeassistant/configuration.yaml`.
- Remove `/homeassistant/dashboards/utilities.yaml`.
- Restart Home Assistant Core.

Requested by:
- Project user

Implemented by:
- Codex

---

## 2026-05-28 - Add Watchman daily alert

Summary:
- Added a daily persistent-notification health check for Watchman missing entities/actions.
- Marked the Watchman alert stage as implemented in the dashboard and automation plan.

Files changed:
- snapshots/homeassistant/automations.yaml
- docs/dashboard_automation_plan.md
- docs/change_log.md

Details:
- Added automation `system_watchman_daily_check`.
- Runs daily at `09:05`, shortly after the backup stale check.
- Creates persistent notification `system_watchman_health` if:
  - `sensor.watchman_missing_entities` is above zero
  - `sensor.watchman_missing_actions` is above zero
  - Watchman status/count sensors are unavailable
- Dismisses `system_watchman_health` automatically when Watchman reports no issues.
- Notification message includes Watchman status, missing entity count, missing action count, last parse, and parse duration.

Validation:
- [x] Backup remote `/homeassistant/automations.yaml`
- [x] `ha core check`
- [x] Restart Home Assistant Core
- [x] Live read-back of automation
- [x] `make verify`
- [ ] Manual trigger/test completed
- Notes:
  - Automation backup created: `/homeassistant/automations.yaml.bak.1779997812`
  - `ha core check` completed successfully after deployment.
  - Restarted Home Assistant Core successfully because this host's `ha` CLI does not provide an automation reload command.
  - Live read-back confirmed `system_watchman_daily_check` and notification id `system_watchman_health` in `/homeassistant/automations.yaml`.
  - `make verify` reported no drift.

Rollback:
- Restore `/homeassistant/automations.yaml.bak.1779997812` to `/homeassistant/automations.yaml`.
- Restart Home Assistant Core.

Requested by:
- Project user

Implemented by:
- Codex

---

## 2026-05-27 - Add backup stale daily alert

Summary:
- Added a daily persistent-notification health check for automatic Home Assistant backups.
- Marked the backup stale alert stage as implemented in the dashboard and automation plan.

Files changed:
- snapshots/homeassistant/automations.yaml
- docs/dashboard_automation_plan.md
- docs/change_log.md

Details:
- Added automation `system_backup_stale_daily_check`.
- Runs daily at `09:00`.
- Creates persistent notification `system_backup_health` if:
  - `sensor.backup_last_successful_automatic_backup` is missing or older than 36 hours
  - `sensor.backup_backup_manager_state` is unavailable or error-like
- Dismisses `system_backup_health` automatically when the backup check is healthy.
- Notification message includes last successful backup, backup age, last attempted backup, next scheduled backup, and backup manager state.

Validation:
- [x] Backup remote `/homeassistant/automations.yaml`
- [x] `ha core check`
- [x] Restart Home Assistant Core
- [x] Live read-back of automation
- [x] `make verify`
- [ ] Manual trigger/test completed
- Notes:
  - Automation backup created: `/homeassistant/automations.yaml.bak.1779911495`
  - `ha core check` completed successfully after deployment.
  - Restarted Home Assistant Core successfully because this host's `ha` CLI does not provide an automation reload command.
  - Live read-back confirmed `system_backup_stale_daily_check` and notification id `system_backup_health` in `/homeassistant/automations.yaml`.
  - `make verify` reported no drift.

Rollback:
- Restore `/homeassistant/automations.yaml.bak.1779911495` to `/homeassistant/automations.yaml`.
- Restart Home Assistant Core.

Requested by:
- Project user

Implemented by:
- Codex

---

## 2026-05-27 - Add Home Health dashboard

Summary:
- Added an admin-only YAML Home Health dashboard for system reliability checks.
- Registered the dashboard in Lovelace with sidebar visibility.
- Updated the dashboard implementation plan and configuration reference.

Files changed:
- snapshots/homeassistant/configuration.yaml
- snapshots/homeassistant/dashboards/home_health.yaml
- docs/homeassistant_configuration_reference.md
- docs/dashboard_automation_plan.md
- docs/change_log.md

Details:
- Added YAML dashboard:
  - id: `home-health`
  - title: `Home Health`
  - file: `/config/dashboards/home_health.yaml`
  - admin-only: `require_admin: true`
- Dashboard sections:
  - At A Glance
  - Backups
  - Watchman
  - Home Assistant Updates
  - Custom Integration Updates
  - Network Gateway
- Included backup manager sensors, Watchman status/counts/report button, HA update entities, HACS custom integration update entities, and UCG Fiber health/update entities.

Validation:
- [x] Confirmed referenced entities exist in the entity registry
- [x] Backup remote `/homeassistant/configuration.yaml`
- [x] `ha core check`
- [x] Restart Home Assistant Core
- [x] Live read-back of dashboard registration and dashboard YAML
- [x] `make verify`
- [ ] Manual UI review completed
- Notes:
  - Configuration backup created: `/homeassistant/configuration.yaml.bak.1779911047`
  - `ha core check` completed successfully after deployment.
  - Restarted Home Assistant Core successfully so the new Lovelace dashboard registration loads.
  - Live read-back confirmed `home-health` in `/homeassistant/configuration.yaml`.
  - Live read-back confirmed `/homeassistant/dashboards/home_health.yaml` exists with `title: Home Health`.
  - `make verify` reported no drift.

Rollback:
- Restore `/homeassistant/configuration.yaml.bak.1779911047` to `/homeassistant/configuration.yaml`.
- Remove `/homeassistant/dashboards/home_health.yaml`.
- Restart Home Assistant Core.

Requested by:
- Project user

Implemented by:
- Codex

---

## 2026-05-27 - Rename hot water pump, add recorder retention, and clean stale backups

Summary:
- Renamed the Meross water pump entity from the generated integration ID to `switch.hot_water_pump`.
- Updated hot-water pump automations to use the canonical entity ID.
- Added bounded recorder retention and diagnostic sensor exclusions.
- Updated operational docs to include Watchman and current backup cleanup state.
- Removed stale ad-hoc `.bak.*` files older than seven days after confirming HA backups.

Files changed:
- snapshots/homeassistant/configuration.yaml
- snapshots/homeassistant/automations.yaml
- docs/homeassistant_configuration_reference.md
- docs/outstanding_homeassistant_review_steps.md
- docs/change_log.md
- live `/homeassistant/.storage/core.entity_registry`

Details:
- Added `recorder.purge_keep_days: 21` and `commit_interval: 30`.
- Excluded common high-churn diagnostic entity globs:
  - `sensor.*_rssi`
  - `sensor.*_linkquality`
  - `sensor.*_signal_strength`
  - `sensor.*_last_seen`
  - `sensor.*_uptime`
- Updated these automations to use `switch.hot_water_pump`:
  - `hot_water_pump_follow_tado_on_for_1h`
  - `hot_water_pump_off_when_runtime_finishes`
  - `hot_water_pump_manual_auto_off_30m`
- Confirmed custom integrations now documented include:
  - `hacs`
  - `meross_lan`
  - `octopus_energy`
  - `watchman`
- Deleted stale ad-hoc backup files:
  - `/homeassistant/.storage/core.area_registry.bak.1771765942`
  - `/homeassistant/.storage/core.config_entries.bak.`
  - `/homeassistant/.storage/core.config_entries.bak.1772359078`
  - `/homeassistant/.storage/core.device_registry.bak.`
  - `/homeassistant/.storage/core.device_registry.bak.1771765942`
  - `/homeassistant/.storage/core.device_registry.bak.1771766500`
  - `/homeassistant/.storage/core.device_registry.bak.1772359078`
  - `/homeassistant/.storage/core.entity_registry.bak.1771782666`
  - `/homeassistant/.storage/core.entity_registry.bak.1771782865`
  - `/homeassistant/.storage/homekit.01KJM7GT7ZSA1YFHAQNT6XMRX8.aids.bak.1772359078`
  - `/homeassistant/.storage/homekit.01KJM7GT7ZSA1YFHAQNT6XMRX8.iids.bak.1772359078`
  - `/homeassistant/.storage/homekit.01KJM7GT7ZSA1YFHAQNT6XMRX8.state.bak.1772359078`
  - `/homeassistant/automations.yaml.bak.1771878515`
  - `/homeassistant/automations.yaml.bak.1771880143`
  - `/homeassistant/automations.yaml.bak.1771959359`
  - `/homeassistant/automations.yaml.bak.1772212188`
  - `/homeassistant/automations.yaml.bak.1772733807`
  - `/homeassistant/configuration.yaml.bak.1771959359`
  - `/homeassistant/configuration.yaml.bak.1772351853`
  - `/homeassistant/configuration.yaml.bak.1772352870`
  - `/homeassistant/configuration.yaml.bak.1772353477`
  - `/homeassistant/configuration.yaml.bak.1772357168`
  - `/homeassistant/configuration.yaml.bak.1772358943`
  - `/homeassistant/configuration.yaml.bak.1772361253`
  - `/homeassistant/configuration.yaml.bak.1772361703`
  - `/homeassistant/configuration.yaml.bak.1772366020`
  - `/homeassistant/configuration.yaml.bak.1775466707`
  - `/homeassistant/scripts.yaml.bak.1771761051`
  - `/homeassistant/scripts.yaml.bak.1771765942`
  - `/homeassistant/scripts.yaml.bak.1771960650`
  - `/homeassistant/scripts.yaml.bak.1772358418`

Validation:
- [x] Confirmed available HA backups
- [x] Created fresh full HA backup before mutation
- [x] Created file-level backups before live edits
- [x] `ha core check`
- [x] Restart Home Assistant Core
- [x] `make verify`
- [ ] Manual hot-water pump test completed
- Notes:
  - Confirmed automatic backups are configured for both local Supervisor storage and Home Assistant Cloud (`hassio.local`, `cloud.cloud`).
  - Confirmed the last completed automatic backup was `2026-05-27T04:54:15+01:00`.
  - Confirmed backup slug `974412a6` exists from automatic backup on 2026-05-27.
  - Created pre-change backup slug: `64e63c68`.
  - Created file backups:
    - `/homeassistant/configuration.yaml.bak.1779908696`
    - `/homeassistant/automations.yaml.bak.1779908696`
    - `/homeassistant/.storage/core.entity_registry.bak.1779908696`
  - `ha core check` completed successfully before and after the registry rename.
  - Restarted Home Assistant Core successfully after editing the entity registry.
  - Live read-back confirmed `recorder:` in `/homeassistant/configuration.yaml`.
  - Live read-back confirmed hot-water pump automations use `switch.hot_water_pump`.
  - Live entity registry read-back confirmed the Meross outlet entity is now `switch.hot_water_pump`.
  - Remaining ad-hoc `.bak.*` files are today's rollback files only:
    - `/homeassistant/.storage/core.entity_registry.bak.1779908696`
    - `/homeassistant/automations.yaml.bak.1779908696`
    - `/homeassistant/configuration.yaml.bak.1779905655`
    - `/homeassistant/configuration.yaml.bak.1779906578`
    - `/homeassistant/configuration.yaml.bak.1779908696`

Rollback:
- Preferred: restore HA backup slug `64e63c68`.
- File-level rollback:
  - stop Home Assistant Core
  - restore `/homeassistant/.storage/core.entity_registry.bak.1779908696` to `/homeassistant/.storage/core.entity_registry`
  - restore `/homeassistant/configuration.yaml.bak.1779908696` to `/homeassistant/configuration.yaml`
  - restore `/homeassistant/automations.yaml.bak.1779908696` to `/homeassistant/automations.yaml`
  - start Home Assistant Core

Requested by:
- Project user

Implemented by:
- Codex

---

## 2026-05-27 - Expose kitchen Ecostrad heater through HomeKit

Summary:
- Added a dedicated HomeKit bridge for the kitchen Ecostrad Klasse iQ electric heater.
- Kept the Ecostrad heater separate from the existing Tado heating bridge because it is a different integration and currently reports an `unknown` climate state.
- Added an explicit HomeKit-facing name so Apple Home and Siri can distinguish it from the Tado room heating controls.

Files changed:
- snapshots/homeassistant/configuration.yaml
- docs/homeassistant_configuration_reference.md
- docs/homekit_bridge_migration.md
- docs/change_log.md

Details:
- Added HomeKit friendly-name customization:
  - `climate.ecostrad_klasse_iq` -> `Kitchen Ecostrad Heater`
- Added YAML-managed HomeKit bridge:
  - name: `HA Kitchen Heating`
  - port: `21067`
  - include entities:
    - `climate.ecostrad_klasse_iq`
- Documented that Apple Home is expected to expose this as a simple heating thermostat with off/heat and target temperature. The Ecostrad `eco` preset may not appear.

Validation:
- [x] Backup remote `/homeassistant/configuration.yaml`
- [x] `ha core check`
- [x] Restart Home Assistant Core
- [x] `make verify`
- [ ] Manual Apple Home pairing/test completed
- Notes:
  - Backup created: `/homeassistant/configuration.yaml.bak.1779906578`
  - `ha core check` completed successfully.
  - Restarted Home Assistant Core successfully.
  - Synced snapshots from live Home Assistant after deployment.
  - `make verify` reported no drift after syncing.
  - Live state confirmed `climate.ecostrad_klasse_iq` is named `Kitchen Ecostrad Heater` with `off`/`heat` modes.

Rollback:
- Restore `/homeassistant/configuration.yaml.bak.1779906578` to `/homeassistant/configuration.yaml`, or remove the `HA Kitchen Heating` HomeKit bridge and the Ecostrad friendly-name customization from `/homeassistant/configuration.yaml`.
- Restart Home Assistant Core.

Requested by:
- Project user

Implemented by:
- Codex

---

## 2026-05-27 - Expose bedroom Meaco AC units through HomeKit

Summary:
- Added a dedicated HomeKit bridge for Ren's and Nathaniel's Meaco air-conditioning units.
- Kept AC controls separate from the existing Tado heating bridge to avoid pairing/cache issues.
- Added explicit HomeKit-facing names so Apple Home and Siri can distinguish AC from room heating.

Files changed:
- snapshots/homeassistant/configuration.yaml
- docs/homeassistant_configuration_reference.md
- docs/homekit_bridge_migration.md
- docs/change_log.md

Details:
- Added HomeKit friendly-name customizations:
  - `climate.nathaniel_meacocool_mc_series_12000_pro` -> `Nathaniel's Bedroom AC`
  - `climate.meacocool_mc_series_12000_pro_2` -> `Ren's Bedroom AC`
- Added YAML-managed HomeKit bridge:
  - name: `HA Air Conditioning`
  - port: `21066`
  - include entities:
    - `climate.nathaniel_meacocool_mc_series_12000_pro`
    - `climate.meacocool_mc_series_12000_pro_2`
- Documented that Apple Home is expected to expose these as simple cooling thermostat controls with off/cool and target temperature, not necessarily advanced Meaco features.

Validation:
- [x] Backup remote `/homeassistant/configuration.yaml`
- [x] `ha core check`
- [x] Restart Home Assistant Core
- [x] `make verify`
- [ ] Manual Apple Home pairing/test completed
- Notes:
  - Backup created: `/homeassistant/configuration.yaml.bak.1779905655`
  - `ha core check` completed successfully.
  - Restarted Home Assistant Core successfully.
  - Synced snapshots from live Home Assistant after deployment because `ha_info.txt` had stale supervisor metadata (`2026.05.0` -> `2026.05.1`).
  - `make verify` reported no drift after syncing.
  - Live state confirmed `climate.nathaniel_meacocool_mc_series_12000_pro` is named `Nathaniel's Bedroom AC` with `off`/`cool` modes.
  - Live state confirmed `climate.meacocool_mc_series_12000_pro_2` is named `Ren's Bedroom AC` with `off`/`cool` modes.

Rollback:
- Restore `/homeassistant/configuration.yaml.bak.1779905655` to `/homeassistant/configuration.yaml`, or remove the `HA Air Conditioning` HomeKit bridge and the two Meaco friendly-name customizations from `/homeassistant/configuration.yaml`.
- Restart Home Assistant Core.

Requested by:
- Project user

Implemented by:
- Codex

---

## 2026-05-24 - Implement Home Assistant review reliability fixes

Summary:
- Replaced the Tado-triggered hot water pump raw one-hour delay with a visible timer helper and timer-finished off automation.
- Changed the post-sunrise light shutdown from all lights to explicit common/outdoor areas.
- Made the appliance dashboard admin-only because it contains appliance power/stop/control entities.
- Updated operational docs to reflect the current HA version, pump helper, and dashboard control policy.

Files changed:
- snapshots/homeassistant/configuration.yaml
- snapshots/homeassistant/automations.yaml
- docs/homeassistant_configuration_reference.md
- docs/lighting_reusable_components.md
- docs/change_log.md

Details:
- Added `timer.hot_water_pump_runtime` with a one-hour duration.
- Updated `hot_water_pump_follow_tado_on_for_1h`:
  - old behavior: turn pump on, wait one hour inside the automation, then turn pump off
  - new behavior: turn pump on and start `timer.hot_water_pump_runtime`
- Added `hot_water_pump_off_when_runtime_finishes` to turn the pump off when the timer finishes.
- Updated `hot_water_pump_manual_auto_off_30m` so the 30-minute manual fallback does not turn the pump off while Tado hot water demand is on.
- Updated `lighting_all_lights_off_after_sunrise_seasonal` to target common/outdoor areas instead of `entity_id: all`.
- Changed the `kitchen-appliances` Lovelace dashboard to `require_admin: true`.
- Left the water pump entity ID unchanged for deployment safety; rename `switch.smart_switch_2210176177851451030248e1e9aba3d4_outlet` to `switch.hot_water_pump` in the HA UI/entity registry when convenient, then update YAML references.

Validation:
- [x] Created full HA backup before mutation
- [x] `ha core check`
- [x] Reload scripts/automations or restart core
- [x] `make verify`
- [ ] Manual test run completed
- Notes:
  - Pre-change backup slug: `7e1b9a23`
  - `ha core check` completed successfully after deploying the staged YAML.
  - Restarted Home Assistant Core successfully to load the YAML timer helper and dashboard metadata.
  - Verified `timer.hot_water_pump_runtime` exists and is idle.
  - Verified `automation.hot_water_turn_water_pump_off_when_runtime_finishes` exists and is enabled.
  - `make verify` reported no drift after syncing snapshots from live HA.
  - HA still reports the `no_current_backup` repair after this local full backup; off-host/protected backup setup remains a manual follow-up.

Rollback:
- Restore backup slug `7e1b9a23`, or revert the changed YAML sections and restart Home Assistant Core.
- To rollback only the pump behavior, remove `timer.hot_water_pump_runtime`, remove `hot_water_pump_off_when_runtime_finishes`, and restore the one-hour delay inside `hot_water_pump_follow_tado_on_for_1h`.
- To rollback only the sunrise lighting change, restore `entity_id: all` in `lighting_all_lights_off_after_sunrise_seasonal`.

Requested by:
- Project user

Implemented by:
- Codex

---

## 2026-04-06 - Expose Elgato Key Light Air through HomeKit

Summary:
- Synced the repo snapshots from live Home Assistant before editing.
- Added the Elgato Key Light Air light entity to the YAML-managed `HA Lights` HomeKit bridge.
- Updated the configuration reference to reflect the expanded HomeKit light export list.

Files changed:
- snapshots/homeassistant/configuration.yaml
- docs/homeassistant_configuration_reference.md
- docs/change_log.md

Details:
- Refreshed local snapshots with `make sync-ha`.
- Confirmed the live entity id from Home Assistant state:
  - `light.elgato_key_light_air`
- Added `light.elgato_key_light_air` to:
  - `homekit`
  - bridge `HA Lights`
  - `filter.include_entities`
- Documented the extra non-room HomeKit light in the configuration reference.

Validation:
- [x] Backup remote `/homeassistant/configuration.yaml`
- [ ] `ha core check`
- [x] Restart Home Assistant Core
- [x] `make verify`
- Notes:
  - Backup created: `/homeassistant/configuration.yaml.bak.1775466707`
  - `ha core check` failed on a pre-existing automation validator error (`KeyError: 'triggers'`) unrelated to this `configuration.yaml` change.
  - Home Assistant Core restarted successfully after deployment and the live config read-back confirmed `light.elgato_key_light_air` in the `HA Lights` bridge.

Rollback:
- Restore `/homeassistant/configuration.yaml.bak.1775466707` to `/homeassistant/configuration.yaml`.
- Remove `light.elgato_key_light_air` from the `HA Lights` include list.
- Restart Home Assistant Core.

Requested by:
- Project user

Implemented by:
- Codex

---

## 2026-04-03 - Include David's Office filament in nightly lights-off automations

Summary:
- Added David's Office filament light to the nightly lights-off routines so it shuts down with the rest of the house lighting.

Files changed:
- snapshots/homeassistant/automations.yaml
- docs/lighting_reusable_components.md
- docs/change_log.md

Details:
- Updated `lighting_common_lounge_off_2300_sun_thu`:
  - added explicit `light.turn_off` for `light.office_filament`
- Updated `lighting_common_lounge_off_2359_fri_sat`:
  - added explicit `light.turn_off` for `light.office_filament`
- Updated `lighting_overnight_shutdown_0200`:
  - added explicit `light.turn_off` for `light.office_filament`
- Existing bedroom exclusions remain unchanged.

Validation:
- [ ] `ha core check`
- [x] Reload scripts/automations or restart core
- [ ] Manual test run completed
- Notes:
  - Deployed updated `/homeassistant/automations.yaml`.
  - `ha core check` on Home Assistant 2026.4.0 returned an internal validator `KeyError: 'triggers'` after parsing the automation list, so it did not provide a reliable pass/fail signal for this change.
  - Restarted Home Assistant Core successfully.
  - Post-restart live `automations.yaml` contains `light.office_filament` in `lighting_overnight_shutdown_0200`, `lighting_common_lounge_off_2300_sun_thu`, and `lighting_common_lounge_off_2359_fri_sat`.
  - `make verify` no longer showed automation drift; remaining drift is only in stale `ha_core_info.txt` and `ha_info.txt` snapshots.

Rollback:
- Remove the explicit `light.office_filament` off actions from the three nightly lighting automations above.

Requested by:
- Project user

Implemented by:
- Codex

---

## 2026-03-01 - Add manual water pump 30-minute auto-off automation

Summary:
- Added an automation to turn off the hot water pump 30 minutes after a manual/physical turn-on.
- Automation-triggered pump activations are excluded so existing scheduled logic is not interrupted.

Files changed:
- snapshots/homeassistant/automations.yaml
- docs/homeassistant_configuration_reference.md
- docs/change_log.md

Details:
- Added automation `hot_water_pump_manual_auto_off_30m`:
  - trigger: `switch.smart_switch_2210176177851451030248e1e9aba3d4_outlet` from `off` to `on`
  - condition: `trigger.to_state.context.parent_id is none` (manual/physical context)
  - action: wait `00:30:00`, then turn pump off if still on
  - mode: `restart` so repeated manual toggles reset the timer
- Kept existing `hot_water_pump_follow_tado_on_for_1h` unchanged.

Validation:
- [x] `ha core check`
- [x] Reload scripts/automations or restart core
- [ ] Manual test run completed
- Notes:
  - Deployed updated `/homeassistant/automations.yaml`.
  - `ha core check` completed successfully on the HA host.
  - Reloaded automations via API.
  - Verified snapshot-to-live parity with `make verify` (no drift).

Rollback:
- Remove automation `hot_water_pump_manual_auto_off_30m` from `/config/automations.yaml`.
- Reload automations.

Requested by:
- Project user

Implemented by:
- Codex

---

## 2026-03-01 - Add explicit Alexa exposure filter for Home Assistant Cloud

Summary:
- Added a YAML-managed Home Assistant Cloud Alexa exposure filter.
- Limited the initial Alexa discovery set to canonical room lights, canonical Tado room heating entities, and hot water.
- Kept TVs, appliances, helper switches, scenes, and non-Tado climate devices out of Alexa for a cleaner first-time import.

Files changed:
- snapshots/homeassistant/configuration.yaml
- docs/homeassistant_configuration_reference.md
- docs/change_log.md

Details:
- Added `cloud.alexa.filter.include_entities` in `configuration.yaml` for:
  - canonical room light entities
  - canonical Tado climate entities
  - `water_heater.hot_water`
- Added `cloud.alexa.entity_config` names so Alexa sees stable, room-oriented names.
- Deliberately excluded:
  - Home Connect appliances
  - media players / TVs
  - Meaco / other non-Tado climate devices
  - helper switches, sensors, and scenes

Validation:
- [x] `ha core check`
- [x] Reload scripts/automations or restart core
- [ ] Manual test run completed
- Notes:
  - Deployed updated `/homeassistant/configuration.yaml`.
  - `ha core check` completed successfully on the HA host.
  - Restarted Home Assistant Core and confirmed the live config contains `cloud.alexa`.
  - Verified snapshot-to-live parity with `make verify` (no drift).

Rollback:
- Remove the `cloud:` Alexa block from `/config/configuration.yaml`.
- Restart Home Assistant Core.

Requested by:
- Project user

Implemented by:
- Codex

---

## 2026-03-01 - Add appliance dashboard for Home Connect appliances

Summary:
- Added a dedicated Lovelace appliance dashboard for the two ovens and dishwasher.
- Added template sensors that convert raw Home Connect programme IDs and finish timestamps into readable programme names and time-remaining values.
- Extended the HA sync tooling to track the new dashboard file.
- Renamed the dashboard to `Appliances` and added the LG tumble dryer.

Files changed:
- snapshots/homeassistant/configuration.yaml
- snapshots/homeassistant/dashboards/kitchen_appliances.yaml
- snapshots/homeassistant/dashboards/appliances.yaml
- scripts/sync_from_ha.sh
- docs/homeassistant_configuration_reference.md
- docs/change_log.md

Details:
- Added `lovelace.dashboards.kitchen-appliances` in `configuration.yaml`:
  - title: `Appliances`
  - icon: `mdi:home-automation`
  - file: `dashboards/appliances.yaml`
- Added template sensors:
  - `sensor.left_oven_programme`
  - `sensor.left_oven_time_remaining`
  - `sensor.right_oven_programme`
  - `sensor.right_oven_time_remaining`
  - `sensor.dishwasher_programme`
  - `sensor.dishwasher_time_remaining`
  - `sensor.dryer_status`
  - `sensor.dryer_time_remaining`
- Added a new dashboard view with:
  - at-a-glance remaining time and status
  - dedicated cards for left oven, right oven, dishwasher, and dryer
  - safe controls already exposed by Home Connect, including power, programme selection, and stop/pause actions where available
- Updated `scripts/sync_from_ha.sh` so nested dashboard files are fetched and verified cleanly.

Validation:
- [x] `ha core check`
- [x] Reload scripts/automations or restart core
- [ ] Manual test run completed
- Notes:
  - Deployed updated `/homeassistant/configuration.yaml`.
  - Deployed `/homeassistant/dashboards/appliances.yaml`.
  - `ha core check` completed successfully on the HA host.
  - Restarted Home Assistant Core and confirmed the new template sensors were created.
  - Verified snapshot-to-live parity with `make verify` (no drift).

Rollback:
- Remove the `lovelace:` and `template:` additions from `/config/configuration.yaml`.
- Remove `/config/dashboards/appliances.yaml`.
- Restore the prior `scripts/sync_from_ha.sh` file list if dashboard tracking is no longer wanted.

Requested by:
- Project user

Implemented by:
- Codex

---

## 2026-03-01 - Remove HomeKit pilot bridge after production cutover

Summary:
- Removed the temporary `HA Pilot Lights` bridge after the production light bridge was paired and validated.
- Kept `HA Lights` and `HA Climate` as the active YAML-managed HomeKit bridges.

Files changed:
- snapshots/homeassistant/configuration.yaml
- docs/homeassistant_configuration_reference.md
- docs/homekit_bridge_migration.md
- docs/change_log.md

Details:
- Removed the YAML-managed HomeKit pilot bridge:
  - `name: HA Pilot Lights`
  - `port: 21063`
  - previous include entities:
    - `light.sarahs_office`
    - `light.guest_bedroom`
    - `light.ren_s_bedroom`
- Left active bridges unchanged:
  - `HA Lights` on `21064`
  - `HA Climate` on `21065`
- Updated the HomeKit migration docs and configuration reference to reflect the pilot bridge removal.

Validation:
- [x] `ha core check`
- [x] Reload scripts/automations or restart core
- [ ] Manual test run completed
- Notes:
  - Deployed updated `/homeassistant/configuration.yaml` without the `HA Pilot Lights` bridge.
  - `ha core check` completed successfully on the HA host.
  - Restarted Home Assistant Core and confirmed `HA Pilot Lights` was no longer present in `.storage/core.config_entries` or `.storage/core.device_registry`.
  - Archived stale pilot bridge state files:
    - `homekit.01KJM7GT7ZSA1YFHAQNT6XMRX8.aids.removed.1772359078`
    - `homekit.01KJM7GT7ZSA1YFHAQNT6XMRX8.iids.removed.1772359078`
    - `homekit.01KJM7GT7ZSA1YFHAQNT6XMRX8.state.removed.1772359078`
  - Verified `HA Lights` and `HA Climate` remained present after cleanup.
  - Verified snapshot-to-live parity with `make verify` (no drift).

Rollback:
- Re-add the `HA Pilot Lights` YAML block to `/homeassistant/configuration.yaml` and restart Home Assistant Core.

Requested by:
- Project user

Implemented by:
- Codex

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

## 2026-03-01 - Add explicit Tado hot water control scripts

Summary:
- Added explicit Home Assistant scripts for Tado hot water so the user can control hot water in a way that more closely matches the Tado app.
- Documented that Apple HomeKit does not natively support Tado hot water control, so the bridged water-heater entity may remain awkward in Apple Home.

Files changed:
- snapshots/homeassistant/scripts.yaml
- docs/homeassistant_configuration_reference.md
- docs/homekit_bridge_migration.md
- docs/change_log.md

Details:
- Added script `tado_hot_water_auto`:
  - returns `water_heater.hot_water` to `auto` schedule mode via `water_heater.set_operation_mode`
- Added script `tado_hot_water_off`:
  - turns `water_heater.hot_water` off via `water_heater.turn_off`
- Added script `tado_hot_water_boost`:
  - calls `tado.set_water_heater_timer`
  - accepts `duration_minutes`
  - defaults to `60` minutes
- Documented the new scripts in the configuration reference and HomeKit migration runbook.

Validation:
- [ ] `ha core check`
- [ ] Reload scripts/automations or restart core
- [ ] Manual test run completed
- Notes:
  - Intended to provide Tado-style `auto`, `off`, and timed boost controls in Home Assistant.

Rollback:
- Remove `tado_hot_water_auto`, `tado_hot_water_off`, and `tado_hot_water_boost` from `/homeassistant/scripts.yaml` and reload scripts.

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
