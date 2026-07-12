# Home Assistant Configuration Reference

Last verified on 2026-07-12.

## System Snapshot
- Core version: `2026.7.1` (`2026.7.2` available as of 2026-07-12)
- Host in this environment: `192.168.1.191`
- Main config root on HA host: `/config`

## Top-Level Configuration Layout
`/config/configuration.yaml` currently includes:
- `default_config:`
- `homeassistant.customize:` for canonical HomeKit-exported room names
- `cloud.alexa:` for the explicit Home Assistant Cloud Alexa exposure list
- `recorder:` for bounded history retention and high-churn diagnostic sensor exclusions
- `homekit:` for the active production HomeKit bridges (`HA Lights`, `HA Climate`)
- `lovelace:` for the tracked YAML appliance dashboard (`Appliances`)
- `frontend` themes from `themes/` via `!include_dir_merge_named`
- `automation: !include automations.yaml`
- `script: !include scripts.yaml`
- `scene: !include scenes.yaml`
- `input_number:` (`tado_gas_meter_baseline_m3`, `tado_gas_meter_last_submitted_m3`)
- `sql:` (`sensor.octopus_gas_statistics_total` - cumulative gas total from backfilled Octopus statistics)
- `template:` sensors (Tado gas derived register, Home Connect appliance labels)
- `input_datetime:` (`tado_gas_meter_last_submission_date`)
- `timer:` (`hot_water_pump_runtime`)

## Config Files and Ownership
- `/config/configuration.yaml`
  - Root include map only (keep minimal).
- `/config/configuration.yaml`
  - Also defines HomeKit-facing friendly-name customizations for exported room lights and Tado climates.
- `/config/configuration.yaml`
  - Also defines the Home Assistant Cloud Alexa include list and per-entity names.
- `/config/configuration.yaml`
  - Also defines recorder retention and exclusions.
- `/config/configuration.yaml`
  - Also defines the current YAML-managed HomeKit bridge include lists.
- `/config/automations.yaml`
  - Contains light schedule automations.
- `/config/scripts.yaml`
  - Contains reusable light scripts and wrappers.
- `/config/scenes.yaml`
  - Present, currently empty.
- `/config/dashboards/appliances.yaml`
  - YAML Lovelace dashboard for Home Connect appliances.
- `/config/configuration.yaml`
  - Also defines helper entities used by the Tado gas meter automation.
- `/config/configuration.yaml`
  - Also defines the hot water pump runtime timer helper.

## Custom Integrations Installed (Live Server)
Verified on 2026-02-22 from `/homeassistant/custom_components`:
- `hacs`
- `meross_lan`
- `octopus_energy`
- `watchman`

Operational note:
- Custom integrations are expected and currently in use; startup warnings about "not tested by Home Assistant" are normal for these components.

## Repairs Snapshot (Live Server)
Verified on 2026-02-22 from `/homeassistant/.storage/repairs.issue_registry`:
- `tado` -> `water_heater_fallback_Hot Water` (dismissed for `2026.2.3`)
- `octopus_energy` -> `saving_session_binary_sensor_deprecated` (dismissed for `2026.2.3`)
- `octopus_energy` -> `greenness_forecast_session_binary_sensor_deprecated` (dismissed for `2026.2.3`)
- `octopus_energy` -> `free_electricity_session_binary_sensor_deprecated` (dismissed for `2026.2.3`)

## Backup And Rollback Artifacts On Server
Backup status verified on 2026-05-27:
- Automatic backups are configured with both local Supervisor storage and Home Assistant Cloud:
  - `hassio.local`
  - `cloud.cloud`
- Last completed automatic backup: `2026-05-27T04:54:15+01:00`.
- Automatic backup retention is configured for 3 copies.
- A local full pre-change backup was created for the 2026-05-27 pump/recorder cleanup:
  - slug: `64e63c68`
- Current ad-hoc backup files retained on the live server:
  - `/homeassistant/.storage/core.entity_registry.bak.1779908696`
  - `/homeassistant/automations.yaml.bak.1779908696`
  - `/homeassistant/configuration.yaml.bak.1779905655`
  - `/homeassistant/configuration.yaml.bak.1779906578`
  - `/homeassistant/configuration.yaml.bak.1779908696`
- Old ad-hoc `.bak.*` files were cleaned on 2026-05-27 after confirming available HA backups.

Policy reference:
- See `docs/codex_change_playbook.md` backup lifecycle policy for retention and cleanup.

## Current Automation Inventory
- `lighting_common_evening_sunset_on_seasonal`
- `lighting_overnight_shutdown_0200`
- `lighting_common_weekday_morning_0620_presunrise`
- `lighting_common_friday_morning_0650_presunrise`
- `lighting_evening_dim_1900`
- `lighting_all_lights_off_after_sunrise_seasonal`
- `lighting_common_lounge_dim_2215_sun_thu`
- `lighting_common_lounge_dim_2330_fri_sat`
- `lighting_common_lounge_off_2300_sun_thu`
- `lighting_common_lounge_off_2359_fri_sat`
- `lighting_front_porch_on_at_sunset`
- `lighting_front_porch_off_2300`
- `lighting_front_porch_on_0620_presunrise`
- `lighting_front_porch_off_at_sunrise`
- `hot_water_pump_follow_tado_on_for_1h`
- `hot_water_pump_off_when_runtime_finishes`
- `hot_water_pump_manual_auto_off_30m`
- `tado_gas_meter_reading_weekly_from_octopus`
- `tado_gas_meter_submission_overdue_alert`
- `octopus_energy_gas_rollover_health_daily_check`

## Current Script Inventory
- `lighting_apply_profile_core`
- `lighting_common_areas`
- `lighting_bedrooms`
- `lighting_outside`
- `lighting_wait_seasonal_offset`
- `tado_gas_set_manual_baseline`
- `tado_hot_water_auto`
- `tado_hot_water_off`
- `tado_hot_water_boost`

## Current Dashboard Inventory
- Storage dashboards:
  - `Map` (`lovelace.map`)
- YAML dashboards:
  - `Home Health`
    - file: `/config/dashboards/home_health.yaml`
    - purpose: admin-only system health view for backups, Watchman, updates, and network gateway status
  - `Utilities`
    - file: `/config/dashboards/utilities.yaml`
    - purpose: admin-only operational view for Octopus, Ohme, Renault, water, gas, and hot water
  - `Appliances`
    - file: `/config/dashboards/appliances.yaml`
    - purpose: ovens, dishwasher, and dryer status, remaining time, and admin-only controls

## Area ID Reference
Use these exact IDs when targeting by area.

- `living_room` -> Lounge
- `kitchen` -> Kitchen
- `bedroom` -> Main Bedroom
- `dining_room` -> Dining Room
- `sarah_s_office` -> Sarah's Office
- `hallway` -> Hallway
- `garage` -> Garage
- `toilet` -> Toilet
- `side_hall` -> Side Hall
- `front_porch` -> Front Porch
- `ren_s_bedroom` -> Ren's Bedroom
- `guest_bedroom` -> Guest Bedroom
- `david_s_office` -> David's Office
- `landing` -> Landing
- `nathaniel_s_bedroom` -> Nathaniel's Bedroom
- `attic_lounge` -> Attic Lounge
- `hot_water` -> Utilities

## HomeKit Bridge Export Reference
- Current production light bridge is YAML-managed:
  - `HA Lights`
  - port `21064`
  - include entities:
    - `light.attic_lounge`
    - `light.davids_office`
    - `light.dining_room`
    - `light.elgato_key_light_air`
    - `light.front_porch`
    - `light.guest_bedroom`
    - `light.hallway`
    - `light.landing`
    - `light.lounge`
    - `light.main_bedroom`
    - `light.ren_s_bedroom`
    - `light.sarahs_office`
    - `light.side_hall`
- Current production climate bridge is YAML-managed:
  - `HA Climate`
  - port `21065`
  - include entities:
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
- Current production air-conditioning bridge is YAML-managed:
  - `HA Air Conditioning`
  - port `21066`
  - include entities:
    - `climate.nathaniel_meacocool_mc_series_12000_pro`
    - `climate.meacocool_mc_series_12000_pro_2`
- Current production kitchen electric heating bridge is YAML-managed:
  - `HA Kitchen Heating`
  - port `21067`
  - include entities:
    - `climate.ecostrad_klasse_iq`
- Canonical naming rules:
  - room lights -> `Room Lights`
  - Tado thermostats -> `Room Heating`
  - Meaco air conditioners -> `Room AC`
  - Ecostrad kitchen heater -> `Kitchen Ecostrad Heater`
- Canonical room-light entities to expose:
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
- Additional HomeKit-only light entities currently exposed:
  - `light.elgato_key_light_air`
- Canonical Tado climate entities to expose:
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
- Canonical Meaco AC climate entities to expose:
  - `climate.nathaniel_meacocool_mc_series_12000_pro`
  - `climate.meacocool_mc_series_12000_pro_2`
- Canonical kitchen electric heater entity to expose:
  - `climate.ecostrad_klasse_iq`
- See `docs/homekit_bridge_migration.md` for the rollout order, exclude list, and validation checklist.

## Alexa Exposure Reference
- Home Assistant Cloud Alexa exposure is YAML-managed under `cloud.alexa`.
- Current Alexa include entities:
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
- Deliberately excluded from Alexa in the initial pass:
  - media players and TVs
  - Home Connect appliances
  - Meaco / other non-Tado climate devices
  - helper switches, child locks, sensors, and scenes

## Rules For Future Changes Via Codex
1. Prefer changing wrappers over duplicating logic.
2. Keep reusable defaults centralized in core script.
3. Use `target.area_id` instead of hardcoded light entity lists unless explicit pinning is required.
4. Validate with `ha core check` after YAML edits.
5. Reload scripts/automations or restart HA core to apply.

## Known Operational Issues (Observed 2026-02-27)
- `pychromecast` socket disconnect errors for `LG webOS TV (192.168.1.55:8009)` recur in core logs.
- `anglian_water` config flow raised `AttributeError: 'NoneType' object has no attribute 'get'` during account lookup.
- `tuya` warning for invalid enum value `frost` on product id `lgibckbiszegmjlo`.
- Octopus gas daily consumption rollover (`last_reset`) has shown intermittent missed day transitions, causing Energy dashboard day gaps.

Tracking guidance:
- Treat this list as operational debt; keep it current when issues are resolved or newly observed.

## Tado Gas Meter Reading Sync
- Automation: `tado_gas_meter_reading_weekly_from_octopus`
- Schedule: checked daily at `18:00`, submits at most weekly
- Register derivation (statistics-based, reworked 2026-07-12):
  - SQL sensor `sensor.octopus_gas_statistics_total` reads the latest cumulative `sum` (m³) of the backfilled external statistic `octopus_energy:gas_e6s10414361656_2215950002_previous_accumulative_consumption` from the recorder DB, with `last_stat_ts` attribute for freshness.
  - Template sensor `sensor.tado_gas_meter_register_derived` = `input_number.tado_gas_meter_baseline_m3` + statistics total.
  - Late/backfilled Octopus DCC data raises the statistic retroactively, so the register self-heals; no per-day accumulation state exists to corrupt.
- Submission conditions (all required, else retry next day):
  - derived register sensor available
  - at least 7 days since last submission
  - integer register greater than `input_number.tado_gas_meter_last_submitted_m3`
  - (no freshness condition: readings are dated at their data horizon, so DCC lag only delays, never distorts)
- Submission mechanism (dated, added 2026-07-12):
  - `shell_command.tado_submit_dated_meter_reading` -> `/config/scripts/tado_meter_reading.py --submit <int reading> --date <YYYY-MM-DD>`
  - reading date = end of the last statistics row (`last_stat_ts` + 1h, local date)
  - the script POSTs to the Tado Energy Insights API (`energy-insights.tado.com`, home `582180`) using its own OAuth device-code grant stored at `/config/.tado_meter_token.json` (chmod 600, never in git)
  - IMPORTANT: the script must never use the HA tado integration's refresh token - Tado rotates refresh tokens on use and sharing it breaks the integration's login; re-authorize the script with `python3 /config/scripts/tado_meter_reading.py --login` if its own grant dies (exit code 2, surfaced in the failure notification)
  - helpers update only on submission success; failure raises persistent notification `tado_gas_meter_submission_failed` and retries next day
  - `shell_command.tado_submit_dated_meter_reading_dry_run` exists for safe end-to-end testing (auth + home resolution, no POST)
  - note: `tado.add_meter_reading` (HA `2026.7.1`) is no longer used - it has no date parameter and always dates readings on submission day
- Helpers:
  - `input_number.tado_gas_meter_baseline_m3` (fixed anchor: physical register minus statistics total at anchor time)
  - `input_number.tado_gas_meter_last_submitted_m3` (monotonic submission guard)
  - `input_datetime.tado_gas_meter_last_submission_date` (cadence guard)
- Monitoring:
  - `tado_gas_meter_submission_overdue_alert` (daily 19:00): persistent notification if no submission for more than 10 days, auto-dismissed when healthy.
- Maintenance caveat:
  - The SQL sensor queries recorder `statistics`/`statistics_meta` tables directly; an HA schema change could break it. Failure direction is safe (no submission) and surfaces via the overdue alert.
- Manual correction / re-anchoring:
  - Script: `tado_gas_set_manual_baseline`
  - Usage: run from UI with `manual_reading` (actual physical meter register, integer) and optional `submission_date`
  - Behavior: sets `input_number.tado_gas_meter_baseline_m3` = reading minus current statistics total, so the derived register equals the physical meter; posts a confirmation notification.

## Hot Water Pump Runtime
- The Tado hot water demand automation starts the Meross water pump and `timer.hot_water_pump_runtime` for one hour.
- `hot_water_pump_off_when_runtime_finishes` turns the pump off when the timer finishes.
- `hot_water_pump_manual_auto_off_30m` still protects manual/physical starts, but does not turn the pump off while `binary_sensor.hot_water_power` is on.
- Current pump entity is `switch.hot_water_pump`.

## Tado Hot Water Control
- Canonical hot water entity:
  - `water_heater.hot_water`
- Tado-specific hot water actions available in HA `2026.2.3`:
  - `water_heater.set_operation_mode` -> return to `auto`
  - `water_heater.turn_off`
  - `tado.set_water_heater_timer`
- Added helper scripts:
  - `tado_hot_water_auto`
  - `tado_hot_water_off`
  - `tado_hot_water_boost`
- Usage:
  - run `tado_hot_water_boost` with `duration_minutes` to mimic Tado app timed boost
  - run `tado_hot_water_auto` to return to schedule mode
  - run `tado_hot_water_off` to force off

Operational note:
- The generic Home Assistant `water_heater` representation does not match the Tado app model exactly.
- Tado’s own HomeKit support does not support hot water control, so Apple Home may not present this entity in a useful way even when exposed through HA.

## Octopus Gas Rollover Monitoring
- Automation: `octopus_energy_gas_rollover_health_daily_check`
- Schedule: daily at `19:00`
- Primary sensor:
  - `sensor.octopus_energy_gas_e6s10414361656_2215950002_previous_accumulative_consumption_kwh`
- Validation:
  - compares sensor `last_reset` date to yesterday (`YYYY-MM-DD`)
  - treats unknown/unavailable kWh sensor state as failure
- Failure action:
  - creates persistent notification `octopus_energy_gas_rollover_health`
  - includes expected date, observed date, and current kWh/m3 states
- Recovery action:
  - dismisses notification `octopus_energy_gas_rollover_health`

## Change Control Notes
When requesting changes, specify:
- Which file should change (`scripts.yaml`, `automations.yaml`, or both)
- Which script/automation IDs are affected
- Intended behavior and exact schedule time/offset
- Any explicit area include/exclude rules
