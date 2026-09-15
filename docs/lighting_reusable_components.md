# Reusable Lighting Components

Last verified against live Home Assistant config on 2026-09-15 (audit Phase 4).

## Goal
Provide reusable lighting scripts that can be called from automations without repeating area targets and profile logic.

## Files In Use
- `/config/scripts.yaml`
- `/config/automations.yaml`

## Script Architecture

Important:
- Automation YAML entries should include `id`.
- Script entries in `scripts.yaml` must not include `id` (Home Assistant rejects it).
- Numbers (brightness, colour temperature) live ONLY in the profile table of the core script.
  Automations pass a profile name and call a wrapper; they never contain brightness values.
- Every scheduled lighting automation checks `input_boolean.lighting_automations_paused` (added
  2026-09-15). The front porch motion automation and the Goodnight switch deliberately do not.

### 1) Core Script
- Entity: `script.lighting_apply_profile_core`
- Purpose: generic reusable light engine.
- Mode: `restart`
- Inputs:
  - `target_areas` (list of HA `area_id` values)
  - `profile` (`day`, `morning`, `evening_full`, `evening`, `late`, `night`)
  - `action` (`on`, `off`)
  - `transition` (seconds)

Behavior:
- If `action: off` -> one `light.turn_off` for all target areas.
- If `action: on` -> one `light.turn_on` for all target areas using the profile table.

### 2) Wrapper Scripts
- `script.lighting_common_areas` - common areas without Lounge
- `script.lighting_evening_set` - common areas plus Lounge (the evening set; added 2026-09-15)
- `script.lighting_bedrooms` - never called by a schedule; kept for voice/scene use
- `script.lighting_outside` - front porch

All wrappers call `script.lighting_apply_profile_core` and only differ by fixed `target_areas`.

### 3) Dim-If-On Script
- `script.lighting_dim_if_on` (added 2026-09-15)
- Inputs: `target_areas` (list), `extra_entities` (list), `profile` (`evening` or `late`), `transition`.
- Applies the profile only to lights in those areas that are already on. Never turns anything on.
- Used by the 19:00 dim and the late-evening dim.

### 4) Retired: Seasonal Offset Helper
- `script.lighting_wait_seasonal_offset` is no longer called by anything. Dusk and dawn
  automations trigger on sun elevation instead (see below). Kept until 2026-09-22 as a rollback
  aid, then delete it.

## Area Membership (Current)

### Common Areas (`script.lighting_common_areas`)
- `attic_lounge` (Attic Lounge)
- `dining_room` (Dining Room)
- `kitchen` (Kitchen)
- `hallway` (Hallway)
- `landing` (Landing)
- `side_hall` (Side Hall)

### Evening Set (`script.lighting_evening_set`)
- the common areas above plus `living_room` (Lounge)

### Bedrooms (`script.lighting_bedrooms`)
- `bedroom` (Main Bedroom)
- `nathaniel_s_bedroom` (Nathaniel's Bedroom, first floor; formerly Ren's Bedroom, area migrated 2026-09-15)
- `attic_bedroom` (Attic Bedroom; formerly Nathaniel's Bedroom)

Excluded by design:
- `guest_bedroom`

### Outside (`script.lighting_outside`)
- `front_porch` (Front Porch)

## Profile Table (Current)
| profile | brightness_pct | color_temp_kelvin | used by |
|---|---|---|---|
| `day` | 100 | 4000 | (manual) |
| `morning` | 80 | 4000 | pre-sunrise on (common areas, porch) |
| `evening_full` | 100 | 2700 | dusk on before 19:00, porch at sunset |
| `evening` | 80 | 2700 | dusk on after 19:00, 19:00 dim |
| `late` | 15 | 2700 | late-evening dim |
| `night` | 10 | 2000 | (manual / bedrooms) |

## Sun Elevation Thresholds
- Dusk on: `sun.sun` elevation `below: 4` with `rising: false`. At 52.3 N this is roughly
  15 minutes before sunset in June, 30 at the equinoxes and 35 in December - the same shape the
  old seasonal table approximated, without any delay that a restart could lose.
- Dawn off: elevation `above: 5` with `rising: true`.
- Tune the two numbers in the automations if the family notices lights coming on too early/late.
- Note: HA's sunrise/sunset events fire at elevation -0.833 (refraction), so "N minutes before
  sunset" is a positive elevation.

## Automations (Current, 12)

| id | trigger | condition | action |
|---|---|---|---|
| `lighting_evening_set_on_at_dusk` | elevation below 4 | not paused, not rising | evening set on: `evening_full` before 19:00, `evening` after; office filament 100%/80% |
| `lighting_evening_dim_1900` | 19:00 | not paused | `lighting_dim_if_on` evening on evening set + porch + office filament |
| `lighting_evening_set_dim_late` | 22:15 (Sun-Thu) / 23:30 (Fri-Sat) via trigger ids | not paused, weekday matches trigger | `lighting_dim_if_on` late on evening set |
| `lighting_evening_set_off_late` | 23:00 (Sun-Thu) / 23:59 (Fri-Sat) | not paused, weekday matches trigger | evening set off, office filament off |
| `lighting_overnight_shutdown_0200` | 02:00 | not paused | evening set off, outside off, office filament off |
| `lighting_common_morning_presunrise` | 06:20 (Mon-Thu) / 06:50 (Fri) | not paused, before sunrise, weekday matches trigger | common areas on `morning` |
| `lighting_common_off_after_sunrise` | elevation above 5 | not paused, rising | evening set off, outside off |
| `lighting_front_porch_on_at_sunset` | sunset | not paused | outside on `evening_full` |
| `lighting_front_porch_off_2300` | 23:00 | not paused | outside off |
| `lighting_front_porch_on_0620_presunrise` | 06:20 | not paused, before sunrise | outside on `morning` |
| `lighting_front_porch_off_at_sunrise` | sunrise | not paused | outside off |
| `lighting_front_porch_motion_overnight` | `binary_sensor.hue_outdoor_motion_sensor_1_motion` on | 23:00-06:20 | porch 50% 2000 K, off 3 min after motion clears (20 min timeout) unless the 06:20 schedule has taken over |

Bedroom lights are never touched by a schedule. Lounge is part of the evening set, not the
common-areas wrapper, so the pre-sunrise morning automation leaves it off.

Removed on 2026-09-15 (replaced by the table above): `lighting_common_evening_sunset_on_seasonal`,
`lighting_common_weekday_morning_0620_presunrise`, `lighting_common_friday_morning_0650_presunrise`,
`lighting_all_lights_off_after_sunrise_seasonal`, `lighting_common_lounge_dim_2215_sun_thu`,
`lighting_common_lounge_dim_2330_fri_sat`, `lighting_common_lounge_off_2300_sun_thu`,
`lighting_common_lounge_off_2359_fri_sat`.

## Change Guide

### Common changes and exact edit points
- Change a brightness or colour temperature -> the profile table in `lighting_apply_profile_core` (`/config/scripts.yaml`).
- Add/remove areas from a set -> the wrapper script in `/config/scripts.yaml`.
- Change a clock time or an elevation threshold -> the automation in `/config/automations.yaml`.
- Add a schedule -> a new automation that calls a wrapper with a profile name and carries the paused condition.

### Example requests
- "Make `late` 10% instead of 15%."
- "Add `garage` to the common areas wrapper."
- "Move the late dim to 22:30 on weeknights."

## Validation Checklist After Changes
1. Run `ha core check`.
2. Reload scripts and automations (or restart core).
3. Run the affected wrapper from Developer Tools with an explicit `profile` and `action` and confirm the targets.
4. Confirm bedroom exclusions.
5. `make verify` and a change-log entry.
