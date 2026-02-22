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
- `evening`: `brightness_pct: 45`, `color_temp_kelvin: 2700`
- `night`: `brightness_pct: 10`, `color_temp_kelvin: 2000`

## Automations (Current)

### Sunset Common Areas On (Seasonal)
- ID: `lighting_common_evening_sunset_on_seasonal`
- Trigger: sunset anchor at `-01:00:00`
- Action: call `script.lighting_apply_profile_core` with combined target areas:
  - Common areas (including `attic_lounge`)
  - Plus separate Lounge target `living_room`
- Profile/action:
  - `action: on`
  - `profile: evening`
  - `transition: 3`
- Seasonal pre-sunset offsets are applied by `script.lighting_wait_seasonal_offset` with `offset_direction: minus`:
  - Summer (Jun-Aug): 15 minutes before sunset
  - Spring/Autumn (Mar-May, Sep-Nov): 30 minutes before sunset
  - Winter (Dec-Feb): 60 minutes before sunset
- Offsets are centralized in script defaults; automation passes direction only.

### 02:00 Overnight Shutdown
- ID: `lighting_overnight_shutdown_0200`
- Trigger: `02:00:00`
- Actions:
  - call `script.lighting_common_areas` with `action: off`
  - call `script.lighting_outside` with `action: off`

Bedroom lights are intentionally not forced off.
Lounge is not in `script.lighting_common_areas`; it is separately targeted only by the sunset-on automation.

### 06:20 Weekday Pre-Sunrise On
- ID: `lighting_common_weekday_morning_0620_presunrise`
- Trigger: `06:20:00`
- Conditions:
  - weekday is Monday-Thursday
  - time is before sunrise
- Action:
  - call `script.lighting_common_areas` with:
    - `action: on`
    - `profile: day`
    - `transition: 2`

### Daily Seasonal Post-Sunrise Off
- ID: `lighting_all_lights_off_after_sunrise_seasonal`
- Trigger: sunrise
- Condition:
  - none (runs every day)
- Action:
  - seasonal delay via `script.lighting_wait_seasonal_offset` with `offset_direction: plus`:
    - Summer (Jun-Aug): 15 minutes
    - Spring/Autumn (Mar-May, Sep-Nov): 30 minutes
    - Winter (Dec-Feb): 60 minutes
  - call `light.turn_off` targeting `entity_id: all` with `transition: 2`
- Offsets are centralized in script defaults; automation passes direction only.
- Mode: `restart` (manual re-runs replace any in-progress delayed run).

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
