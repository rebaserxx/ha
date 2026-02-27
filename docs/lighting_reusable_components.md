# Reusable Lighting Components

Last verified against live Home Assistant config on 2026-02-22.

## Goal
Provide reusable lighting scripts that can be called from automations without repeating area targets and profile logic.

## Files In Use
- `/config/scripts.yaml`
- `/config/automations.yaml`

## Script Architecture

Important:
- Automation YAML entries should include `id`.
- Script entries in `scripts.yaml` must not include `id` (Home Assistant rejects it).

### 1) Core Script
- Entity: `script.lighting_apply_profile_core`
- Purpose: Generic reusable light action engine.
- Mode: `restart`
- Inputs:
  - `target_areas` (list of HA `area_id` values)
  - `profile` (`day`, `evening`, `night`)
  - `action` (`on`, `off`)
  - `transition` (seconds)

Behavior:
- If `action: off` -> `light.turn_off` for each target area.
- If `action: on` -> `light.turn_on` using profile defaults.

### 2) Wrapper Scripts
- `script.lighting_common_areas`
- `script.lighting_bedrooms`
- `script.lighting_outside`

All wrappers call `script.lighting_apply_profile_core` and only differ by fixed `target_areas`.

### 3) Seasonal Offset Helper
- `script.lighting_wait_seasonal_offset`
- Purpose: reusable seasonal offset logic for sunrise/sunset automations.
- Inputs:
  - `offset_direction`:
    - `plus`: add time after event (morning)
    - `minus`: subtract time before event via an anchor trigger (evening)
  - `anchor_minutes` (used for `minus`; current sunset anchor is 60)
  - `summer_minutes` (Jun-Aug)
  - `shoulder_minutes` (Mar-May, Sep-Nov)
  - `winter_minutes` (Dec-Feb)

## Area Membership (Current)

### Common Areas (`script.lighting_common_areas`)
- `attic_lounge` (Attic Lounge)
- `dining_room` (Dining Room)
- `kitchen` (Kitchen)
- `hallway` (Hallway)
- `landing` (Landing)
- `side_hall` (Side Hall)

### Bedrooms (`script.lighting_bedrooms`)
- `bedroom` (Main Bedroom)
- `ren_s_bedroom` (Ren's Bedroom)
- `nathaniel_s_bedroom` (Nathaniel's Bedroom)

Excluded by design:
- `guest_bedroom`

### Outside (`script.lighting_outside`)
- `front_porch` (Front Porch)

## Profile Defaults (Current)
- `day`: `brightness_pct: 100`, `color_temp_kelvin: 4000`
- `evening`: `brightness_pct: 80`, `color_temp_kelvin: 2700`
- `night`: `brightness_pct: 10`, `color_temp_kelvin: 2000`

## Automations (Current)

### Sunset Common Areas On (Seasonal)
- ID: `lighting_common_evening_sunset_on_seasonal`
- Trigger: sunset anchor at `-01:00:00`
- Action: turn on combined evening targets at full brightness:
  - Area targets: common areas (`attic_lounge`, `dining_room`, `kitchen`, `hallway`, `landing`, `side_hall`) plus Lounge (`living_room`)
  - Explicit entity: `light.office_filament` (David's Office filament)
  - Settings: `brightness_pct: 100`, `color_temp_kelvin: 2700`, `transition: 3`
- Seasonal pre-sunset offsets are applied by `script.lighting_wait_seasonal_offset` with `offset_direction: minus`:
  - Summer (Jun-Aug): 15 minutes before sunset
  - Spring/Autumn (Mar-May, Sep-Nov): 30 minutes before sunset
  - Winter (Dec-Feb): 45 minutes before sunset
- Offsets are centralized in script defaults; automation passes direction only.

### 02:00 Overnight Shutdown
- ID: `lighting_overnight_shutdown_0200`
- Trigger: `02:00:00`
- Actions:
  - call `script.lighting_common_areas` with `action: off`
  - call `script.lighting_outside` with `action: off`

Bedroom lights are intentionally not forced off.
Lounge is not in `script.lighting_common_areas`; it is separately targeted only by the sunset-on automation.

### Weekday Pre-Sunrise On (Split Times)
- IDs:
  - `lighting_common_weekday_morning_0620_presunrise`
  - `lighting_common_friday_morning_0650_presunrise`
- Behavior:
  - Monday-Thursday at `06:20`: turn on common areas before sunrise
  - Friday at `06:50`: turn on common areas before sunrise
- Conditions:
  - day-specific weekday condition (`Mon-Thu` or `Fri`, depending on automation)
  - time is before sunrise
- Action:
  - turn on common areas (`attic_lounge`, `dining_room`, `kitchen`, `hallway`, `landing`, `side_hall`)
  - settings: `brightness_pct: 80`, `color_temp_kelvin: 4000`, `transition: 2`

### Evening Dim To 80% At 19:00
- ID: `lighting_evening_dim_1900`
- Trigger: `19:00:00` (daily)
- Action:
  - build a list of currently-on light entities in evening target areas:
    - common set + Lounge + Front Porch
    - plus `light.office_filament`
  - apply: `brightness_pct: 80`, `color_temp_kelvin: 2700`, `transition: 3`
- Guard:
  - only runs `light.turn_on` when at least one target light is already on
  - does not turn on lights that are currently off

### Daily Seasonal Post-Sunrise Off
- ID: `lighting_all_lights_off_after_sunrise_seasonal`
- Trigger: sunrise
- Condition:
  - none (runs every day)
- Action:
  - seasonal delay via `script.lighting_wait_seasonal_offset` with `offset_direction: plus`:
    - Summer (Jun-Aug): 15 minutes
    - Spring/Autumn (Mar-May, Sep-Nov): 30 minutes
    - Winter (Dec-Feb): 45 minutes
  - call `light.turn_off` targeting `entity_id: all` with `transition: 2`
- Offsets are centralized in script defaults; automation passes direction only.
- Mode: `restart` (manual re-runs replace any in-progress delayed run).

### Late Evening Common + Lounge Dim (Week Split)
- IDs:
  - `lighting_common_lounge_dim_2215_sun_thu`
  - `lighting_common_lounge_dim_2330_fri_sat`
- Behavior:
  - Sunday-Thursday at `22:15`: set common areas + Lounge to `brightness_pct: 15`
  - Friday-Saturday at `23:30`: set common areas + Lounge to `brightness_pct: 15`
- Target areas:
  - common set (`attic_lounge`, `dining_room`, `kitchen`, `hallway`, `landing`, `side_hall`)
  - plus Lounge (`living_room`)

### Late Evening Common + Lounge Off (Week Split)
- IDs:
  - `lighting_common_lounge_off_2300_sun_thu`
  - `lighting_common_lounge_off_2359_fri_sat`
- Behavior:
  - Sunday-Thursday at `23:00`: turn off common areas + Lounge
  - Friday-Saturday at `23:59`: turn off common areas + Lounge
- Target areas:
  - common set (`attic_lounge`, `dining_room`, `kitchen`, `hallway`, `landing`, `side_hall`)
  - plus Lounge (`living_room`)

### Front Porch Evening/Night Schedule
- IDs:
  - `lighting_front_porch_on_at_sunset`
  - `lighting_front_porch_off_2300`
- Behavior:
  - At sunset: turn on front porch lights at `brightness_pct: 100`, `color_temp_kelvin: 2700`
  - At `23:00`: turn off front porch lights

### Front Porch Early Morning Schedule
- IDs:
  - `lighting_front_porch_on_0620_presunrise`
  - `lighting_front_porch_off_at_sunrise`
- Behavior:
  - At `06:20`: turn on front porch lights only if before sunrise at `brightness_pct: 80`, `color_temp_kelvin: 4000`
  - At sunrise: turn off front porch lights

## Change Guide

### Common changes and exact edit points
- Change profile defaults -> `/config/scripts.yaml` under `lighting_apply_profile_core`.
- Add/remove areas from a set -> wrapper script section in `/config/scripts.yaml`.
- Change timing -> target automation in `/config/automations.yaml`.
- Add additional schedule -> add new automation that calls existing wrappers.

### Example requests to Codex
- "Update `lighting_common_evening_sunset_on_seasonal` seasonal delays."
- "Add `attic_lounge` to common areas wrapper."
- "Make `night` profile 5% brightness at 1800K."

## Validation Checklist After Changes
1. Run `ha core check`.
2. Reload scripts and automations (or restart core).
3. Manually run affected automation actions from UI.
4. Confirm target areas only, especially bedroom exclusions.
