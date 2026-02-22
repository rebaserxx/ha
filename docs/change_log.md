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
