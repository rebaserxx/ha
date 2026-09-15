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
- `cloud.alexa:` for the explicit Home Assistant Cloud Alexa exposure list (include list only since 2026-09-15; names come from `customize`)
- `recorder:` for bounded history retention and high-churn exclusions (diagnostic sensor globs, unnamed UniFi trackers, iPhone/iPad companion sensors, Hue dimmer events, sun timestamp sensors)
- `homekit:` for the active production HomeKit bridges (`HA Lights`, `HA Climate`)
- `lovelace:` for the tracked YAML appliance dashboard (`Appliances`)
- `automation: !include automations.yaml`
- `script: !include scripts.yaml`
- `scene: !include scenes.yaml`
- `input_number:` (`tado_gas_meter_baseline_m3`, `tado_gas_meter_last_submitted_m3`)
- `input_boolean:` (`hot_water_boost`, `goodnight`, `lighting_automations_paused` - voice-facing virtual switches, added 2026-09-15)
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

## Disabled Entities Of Note
- `sensor.e_ny1_climate_temperature` (My Honda+) disabled 2026-09-15: enum sensor receiving numeric
  values, raised an error on every coordinator update. Re-enable only after an upstream fix.
- `media_player.s95qr` (stale Cast duplicate of `media_player.lg_speaker_s95qr_0793`) and
  `media_player.lg_webos_tv` (Cast duplicate of the webOS `media_player.lounge_tv`) disabled 2026-09-15.
- Meross `light.*_dnd` (4) and `switch.*_config_overtemp_enable` (4) disabled 2026-09-15: plug LED
  and firmware options that would otherwise look like lights/switches to voice assistants.

## Google Home Exposure Reference
- Managed in the entity registry / Settings > Voice assistants > Expose, NOT in YAML: on HA 2026.9 a
  `cloud: google_assistant:` block is rejected and stops the cloud integration loading (seen 2026-09-15).
- Exposed set (31, 2026-09-15): the 12 room light groups, all 15 climate entities (12 Tado, Kitchen
  Heating, both Meaco ACs), both oven cavity temperatures, `input_boolean.hot_water_boost`,
  `input_boolean.goodnight`. Aliases come from the entity registry. Rooms come from HA areas.

## Assist (Conversation) Exposure Policy
- Tier 1 (all assistants): the 12 room light groups + Elgato, 15 climate entities, hot water.
- Tier 2 (Assist/HomeKit admin): `switch.hot_water_pump`.
- Also exposed to Assist only: Tado room temperature/humidity/window sensors, the two Hue motion
  sensors, the standard Hue room scenes, the four live media players, the shopping list, and the
  eight appliance status template sensors (with aliases such as "dishwasher", "dryer", "left oven").
- Never exposed: individual bulbs, child locks, appliance power/programme switches, EV controls,
  Meross plugs, diagnostics. Trimmed 192 -> 117 on 2026-09-15.

## Custom Integrations Installed (Live Server)
Verified on 2026-09-01 from `/homeassistant/custom_components`:
- `hacs`
- `meross_lan`
- `myhondaplus` (My Honda+; Honda e:Ny1, ~43 entities under the `e_ny1_*` slug)
- `octopus_energy`
- `watchman`

Operational note:
- Custom integrations are expected and currently in use; startup warnings about "not tested by Home Assistant" are normal for these components.

## Tuya Local Quirks
- `/config/tuya_quirks/qn_lgibckbiszegmjlo.py` (Ecostrad Klasse iQ kitchen heater), added 2026-09-15,
  tracked at `snapshots/homeassistant/tuya_quirks/` and covered by `make verify`.
- Removes the `mode` datapoint: Tuya's spec mis-declares it and the cloud API refuses mode writes,
  which made `climate.ecostrad_klasse_iq` report `unknown` whenever on. HA now derives off/heat from
  the switch datapoint. The heater must be left in COMFORT mode via the Tuya/Smart Life app.
- Quirks reload with the Tuya integration (no restart). Reload the HA Kitchen Heating HomeKit bridge
  after changing the climate entity's features.
- The two MeacoCool AC units (`wuqmedatpig5n1cb`, category `kt`) need no quirk; their spec is consistent.

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
- 2026-09-15 (audit Phase 1): HA backup slug `666a6dd7` (`pre_phase1_20260915`), plus
  `configuration.yaml.bak.1789479665` and `automations.yaml.bak.1789479665`. Ad-hoc `.bak.*`
  files from 2026-05 through 2026-09-03 are still on the server awaiting explicit cleanup.
- HTTP settings (`ip_ban_enabled`, `login_attempts_threshold`) are storage-managed in
  `.storage/http` on this HA version; a YAML `http:` block is ignored and raises a repair.

Policy reference:
- See `docs/codex_change_playbook.md` backup lifecycle policy for retention and cleanup.

## Current Automation Inventory
Verified on 2026-09-15 from `/config/automations.yaml` (28 automations):
- Lighting (12, see `docs/lighting_reusable_components.md`): `lighting_evening_set_on_at_dusk`,
  `lighting_evening_dim_1900`, `lighting_evening_set_dim_late`, `lighting_evening_set_off_late`,
  `lighting_overnight_shutdown_0200`, `lighting_common_morning_presunrise`,
  `lighting_common_off_after_sunrise`, `lighting_front_porch_on_at_sunset`,
  `lighting_front_porch_off_2300`, `lighting_front_porch_on_0620_presunrise`,
  `lighting_front_porch_off_at_sunrise`, `lighting_front_porch_motion_overnight`
- Hot water (7): `hot_water_pump_follow_tado_on_for_1h`, `hot_water_pump_off_when_runtime_finishes`,
  `hot_water_pump_manual_auto_off_30m`, `hot_water_boost_switch_on`, `hot_water_boost_switch_off`,
  `hot_water_boost_switch_mirror`, `house_goodnight` (house, not hot water, but added with them)
- Tado gas (2): `tado_gas_meter_reading_weekly_from_octopus`, `tado_gas_meter_submission_overdue_alert`
- Health (3): `octopus_energy_gas_rollover_health_daily_check`, `system_backup_stale_daily_check`,
  `system_watchman_daily_check`
- EV (4): `ev_ohme_sync_renault_state_of_charge`, `ev_ohme_auto_approve_renault_charge`,
  `ev_ohme_sync_honda_state_of_charge`, `ev_ohme_auto_approve_honda_charge`

All 12 scheduled/lighting automations except `lighting_front_porch_motion_overnight` carry the
condition `input_boolean.lighting_automations_paused == off`.

## Current Script Inventory
- `lighting_apply_profile_core` (profile table: day, morning, evening_full, evening, late, night)
- `lighting_common_areas`, `lighting_evening_set`, `lighting_bedrooms`, `lighting_outside`
- `lighting_dim_if_on`
- `lighting_wait_seasonal_offset` (retired 2026-09-15, uncalled; delete after 2026-09-22)
- `tado_gas_set_manual_baseline`
- `tado_hot_water_auto`, `tado_hot_water_off`, `tado_hot_water_boost`

## Current Dashboard Inventory
- Storage dashboards:
  - `Map` (`lovelace.map`)
- YAML dashboards:
  - `Home Health`
    - file: `/config/dashboards/home_health.yaml`
    - purpose: admin-only system health view for backups, Watchman, updates, and network gateway status
    - custom integration updates tracked: HACS, Meross LAN, My Honda+, Octopus Energy, Watchman
  - `Utilities`
    - file: `/config/dashboards/utilities.yaml`
    - purpose: admin-only operational view for Octopus, Ohme, Renault, Honda, water, gas, and hot water
    - cards: At A Glance, Electricity, Gas, Octoplus, EV Charging, Renault Scenic,
      Honda e:Ny1, Honda e:Ny1 Vehicle, Honda e:Ny1 This Month, EV Controls, Water, Hot Water
    - EV note: the Ohme charger is shared between the Renault Scenic and the Honda e:Ny1.
      Both cars now have their own HA entities, so Ohme's own readings
      (`sensor.ohme_home_pro_vehicle_battery` and friends) describe whichever car
      `select.ohme_home_pro_vehicle` currently names - that select is on the EV Charging
      card for exactly this reason. Prefer the per-car sensors when you need a specific car.
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
- `nathaniel_s_bedroom` -> Nathaniel's Bedroom (first floor; formerly Ren's Bedroom, area migrated 2026-09-15)
- `guest_bedroom` -> Guest Bedroom
- `david_s_office` -> David's Office
- `landing` -> Landing
- `attic_bedroom` -> Attic Bedroom (attic; formerly Nathaniel's Bedroom, area migrated 2026-09-15)
- `attic_lounge` -> Attic Lounge
- `hot_water` -> Utilities

Entity id history (ids are deliberately unchanged so HomeKit/Alexa pairings survive):
- `light.ren_s_bedroom`, `climate.ren_s_bedroom`, `switch.ren_s_bedroom_child_lock`,
  `binary_sensor.ren_s_bedroom_window`, `sensor.ren_s_bedroom_*`, `light.rens_bedroom_lamp_*`,
  `climate.meacocool_mc_series_12000_pro_2` = **Nathaniel's Bedroom** (first floor).
- `climate.nathaniels_bedroom`, `switch.nathaniels_bedroom_child_lock`,
  `binary_sensor.nathaniels_bedroom_window`, `sensor.nathaniels_bedroom_*`,
  `climate.nathaniel_meacocool_mc_series_12000_pro` = **Attic Bedroom**.
- `media_player.ren_s_bedroom_display` moved to the Dining Room on 2026-09-15.

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
    - `light.ren_s_bedroom` (Nathaniel's Bedroom Lights)
    - `light.sarahs_office`
    - `light.side_hall`
    - `input_boolean.hot_water_boost`, `input_boolean.goodnight`, `input_boolean.lighting_automations_paused` (virtual switches, 2026-09-15)
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
    - `climate.nathaniels_bedroom` (Attic Bedroom Heating)
    - `climate.ren_s_bedroom` (Nathaniel's Bedroom Heating)
    - `climate.sarahs_office`
    - `climate.toilet`
    - `water_heater.hot_water`
- Current production air-conditioning bridge is YAML-managed:
  - `HA Air Conditioning`
  - port `21066`
  - include entities:
    - `climate.nathaniel_meacocool_mc_series_12000_pro` (Attic Bedroom AC)
    - `climate.meacocool_mc_series_12000_pro_2` (Nathaniel's Bedroom AC)
- Current production kitchen electric heating bridge is YAML-managed:
  - `HA Kitchen Heating`
  - port `21067`
  - include entities:
    - `climate.ecostrad_klasse_iq`
- Canonical naming rules:
  - room lights -> `Room Lights`
  - Tado thermostats -> `Room Heating`
  - Meaco air conditioners -> `Room AC`
  - Ecostrad kitchen heater -> `Kitchen Heating` (renamed from `Kitchen Ecostrad Heater` 2026-09-15)
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
- Home Assistant Cloud Alexa exposure is YAML-managed under `cloud.alexa` (filter only; the per-entity `entity_config` names were removed 2026-09-15 because they duplicated `customize`).
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
  - `water_heater.hot_water` (to be removed once the boost switch has proven itself)
  - `input_boolean.hot_water_boost`, `input_boolean.goodnight` (2026-09-15)
  - `climate.ecostrad_klasse_iq`, `climate.nathaniel_meacocool_mc_series_12000_pro`, `climate.meacocool_mc_series_12000_pro_2`, `sensor.left_oven_current_oven_cavity_temperature`, `sensor.right_oven_current_oven_cavity_temperature` (Phase 3V, 2026-09-15; replace the vendor skills)
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
- The timer is declared with `restore: true` (2026-09-15) so a core restart mid-run does not strand the pump.
- `hot_water_pump_off_when_runtime_finishes` turns the pump off when the timer finishes or is cancelled (both `timer.finished` and `timer.cancelled` events, 2026-09-15).
- `hot_water_pump_manual_auto_off_30m` still protects manual/physical starts, but does not turn the pump off while `binary_sensor.hot_water_power` is on.
- Current pump entity is `switch.hot_water_pump`.

## Hot Water Boost Switch (voice-facing)
- `input_boolean.hot_water_boost` is the family-facing control on Alexa, HomeKit and Assist (Google after Phase 3V).
- On -> `hot_water_boost_switch_on` runs `script.tado_hot_water_boost` (60 min), unless Tado is already boosting.
- Off -> `hot_water_boost_switch_off` runs `script.tado_hot_water_auto`, only if a manual overlay is active.
- `hot_water_boost_switch_mirror` keeps the switch truthful: on when `water_heater.hot_water` is `heat` with `binary_sensor.hot_water_overlay` on, off otherwise (covers boosts started or expired from the Tado app).
- `input_boolean.goodnight` (momentary, `house_goodnight`) and `input_boolean.lighting_automations_paused` are the other two virtual switches; see the change log 2026-09-15 Phase 3.

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

## Energy Dashboard
- Grid: `octopus_energy:electricity_16l0037350_1100021054904_previous_accumulative_consumption` (+ `_cost`)
- Gas: `octopus_energy:gas_e6s10414361656_2215950002_previous_accumulative_consumption_kwh` (+ `_cost`)
- Water: `sensor.water_meter_latest_reading`
- Individual electricity devices (only one; no other device-level power metering exists):
  - `sensor.utilities_ohme_home_pro_charger_energy` - UI Integral (Riemann sum) helper, added 2026-09-15
    - source `sensor.ohme_home_pro_power` (kW), method `left`, unit time `h`, round 3,
      `max_sub_interval` 1 minute; attached to the Ohme device, hence the `utilities_` prefix
    - measured charger draw, so it covers every session (smart, boost, `max_charge`); it cannot count
      energy while HA is down or the Ohme cloud is unreachable
- Why not the Ohme integration's energy sensor: `sensor.ohme_home_pro_energy` was removed upstream
  (home-assistant/core PR #174664, merged 2026-07-13, breaking change). It reported an estimate of
  energy in the car battery, not charger consumption - its last recorded day totals exceeded whole-house
  grid import (2026-08-07: 132 kWh vs 83 kWh). Its long-term statistics stop at 2026-08-14 21:00 UTC and
  were left in place; they are no longer referenced by the Energy dashboard.
- Why not Octopus: `binary_sensor.octopus_energy_00000000_0009_4000_8020_000000016ba7_intelligent_dispatching`
  carries `completed_dispatches[].charge_in_kwh` (what the Octopus app shows), but only as a ~3-day rolling
  attribute list, only for Octopus-scheduled slots, and not as a kWh statistic. On 2026-09-13/14 it read
  19.09 / 38.64 kWh against 17.56 / 38.55 kWh measured by the helper's source - a useful cross-check only.

## Octopus Gas Rollover Monitoring
- Automation: `octopus_energy_gas_rollover_health_daily_check`
- Schedule: daily at `23:45` (moved from `19:00` on 2026-07-16 — previous-day data typically arrives 19:10–23:43, so the check now usually runs after it lands)
- Primary sensor:
  - `sensor.octopus_energy_gas_e6s10414361656_2215950002_previous_accumulative_consumption_kwh`
- Validation (timezone-safe, lag-tolerant since 2026-07-16):
  - converts sensor `last_reset` to the **local** date (`as_datetime | as_local`) before comparing — a plain string slice reads the UTC date, which is one day behind during BST and caused daily false alarms
  - computes `gas_days_behind` = expected date (yesterday) minus local last_reset date
  - alerts only when 2+ days behind (1 day of DCC lag is normal and self-heals via statistics backfill)
  - treats unknown/unavailable kWh sensor state as failure
- Failure action:
  - creates persistent notification `octopus_energy_gas_rollover_health`
  - includes days behind, expected date, observed local date, and current kWh/m3 states
- Recovery action:
  - dismisses notification `octopus_energy_gas_rollover_health`

## Change Control Notes
When requesting changes, specify:
- Which file should change (`scripts.yaml`, `automations.yaml`, or both)
- Which script/automation IDs are affected
- Intended behavior and exact schedule time/offset
- Any explicit area include/exclude rules
