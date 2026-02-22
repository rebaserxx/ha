# Reusable Lighting Components

Last verified against live Home Assistant config on 2026-02-22.

## Goal
Provide reusable lighting scripts that can be called from automations without repeating area targets and profile logic.

## Files In Use
- `/config/scripts.yaml`
- `/config/automations.yaml`

## Script Architecture

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

## Area Membership (Current)

### Common Areas (`script.lighting_common_areas`)
- `living_room` (Lounge)
- `dining_room` (Dining Room)
- `kitchen` (Kitchen)
- `hallway` (Hallway)
- `landing` (Landing)
- `side_hall` (Side Hall)

### Bedrooms (`script.lighting_bedrooms`)
- `bedroom` (Main Bedroom)
- `ren_s_bedrrom` (Ren's Bedroom)
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

### Dusk Common Areas On
- ID: `lighting_common_evening_dusk_on`
- Trigger: sunset offset `-00:15:00`
- Action: call `script.lighting_common_areas` with
  - `action: on`
  - `profile: evening`
  - `transition: 3`

### 02:00 Overnight Shutdown
- ID: `lighting_overnight_shutdown_0200`
- Trigger: `02:00:00`
- Actions:
  - call `script.lighting_common_areas` with `action: off`
  - call `script.lighting_outside` with `action: off`

Bedroom lights are intentionally not forced off.

## Change Guide

### Common changes and exact edit points
- Change profile defaults -> `/config/scripts.yaml` under `lighting_apply_profile_core`.
- Add/remove areas from a set -> wrapper script section in `/config/scripts.yaml`.
- Change timing -> target automation in `/config/automations.yaml`.
- Add additional schedule -> add new automation that calls existing wrappers.

### Example requests to Codex
- "Update `lighting_common_evening_dusk_on` to trigger at sunset with no offset."
- "Add `attic_lounge` to common areas wrapper."
- "Make `night` profile 5% brightness at 1800K."

## Validation Checklist After Changes
1. Run `ha core check`.
2. Reload scripts and automations (or restart core).
3. Manually run affected automation actions from UI.
4. Confirm target areas only, especially bedroom exclusions.
