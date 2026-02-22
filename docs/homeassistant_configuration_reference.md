# Home Assistant Configuration Reference

Last verified on 2026-02-22.

## System Snapshot
- Core version: `2026.2.3`
- Host in this environment: `192.168.1.191`
- Main config root on HA host: `/config`

## Top-Level Configuration Layout
`/config/configuration.yaml` currently includes:
- `default_config:`
- `frontend` themes from `themes/` via `!include_dir_merge_named`
- `automation: !include automations.yaml`
- `script: !include scripts.yaml`
- `scene: !include scenes.yaml`

## Config Files and Ownership
- `/config/configuration.yaml`
  - Root include map only (keep minimal).
- `/config/automations.yaml`
  - Contains light schedule automations.
- `/config/scripts.yaml`
  - Contains reusable light scripts and wrappers.
- `/config/scenes.yaml`
  - Present, currently empty.

## Custom Integrations Installed (Live Server)
Verified on 2026-02-22 from `/homeassistant/custom_components`:
- `hacs`
- `meross_lan`
- `octopus_energy`

Operational note:
- Custom integrations are expected and currently in use; startup warnings about "not tested by Home Assistant" are normal for these components.

## Repairs Snapshot (Live Server)
Verified on 2026-02-22 from `/homeassistant/.storage/repairs.issue_registry`:
- `tado` -> `water_heater_fallback_Hot Water` (dismissed for `2026.2.3`)
- `octopus_energy` -> `saving_session_binary_sensor_deprecated` (dismissed for `2026.2.3`)
- `octopus_energy` -> `greenness_forecast_session_binary_sensor_deprecated` (dismissed for `2026.2.3`)
- `octopus_energy` -> `free_electricity_session_binary_sensor_deprecated` (dismissed for `2026.2.3`)

## Backup And Rollback Artifacts On Server
Current ad-hoc backup files observed on 2026-02-22:
- `/homeassistant/scripts.yaml.bak.1771761051`
- `/homeassistant/scripts.yaml.bak.1771765942`
- `/homeassistant/.storage/core.area_registry.bak.1771765942`
- `/homeassistant/.storage/core.device_registry.bak.1771765942`
- `/homeassistant/.storage/core.device_registry.bak.1771766500`

Policy reference:
- See `docs/codex_change_playbook.md` backup lifecycle policy for retention and cleanup.

## Current Automation Inventory
- `lighting_common_evening_sunset_on_seasonal`
- `lighting_overnight_shutdown_0200`
- `lighting_common_weekday_morning_0620_presunrise`
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

## Current Script Inventory
- `lighting_apply_profile_core`
- `lighting_common_areas`
- `lighting_bedrooms`
- `lighting_outside`
- `lighting_wait_seasonal_offset`

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

## Rules For Future Changes Via Codex
1. Prefer changing wrappers over duplicating logic.
2. Keep reusable defaults centralized in core script.
3. Use `target.area_id` instead of hardcoded light entity lists unless explicit pinning is required.
4. Validate with `ha core check` after YAML edits.
5. Reload scripts/automations or restart HA core to apply.

## Known Operational Issues (Observed 2026-02-22)
- `pychromecast` socket disconnect errors for `LG webOS TV (192.168.1.55:8009)` recur in core logs.
- `anglian_water` config flow raised `AttributeError: 'NoneType' object has no attribute 'get'` during account lookup.
- `tuya` warning for invalid enum value `frost` on product id `lgibckbiszegmjlo`.

Tracking guidance:
- Treat this list as operational debt; keep it current when issues are resolved or newly observed.

## Change Control Notes
When requesting changes, specify:
- Which file should change (`scripts.yaml`, `automations.yaml`, or both)
- Which script/automation IDs are affected
- Intended behavior and exact schedule time/offset
- Any explicit area include/exclude rules
