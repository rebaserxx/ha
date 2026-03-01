# HomeKit Bridge Migration Runbook

Last updated on 2026-03-01.

## Intent

This HomeKit rollout currently starts with a YAML-managed pilot bridge so the initial include list is explicit and reproducible from the repo. The repo defines the canonical exported names and the pilot bridge in [snapshots/homeassistant/configuration.yaml](/home/rebaser/ha/snapshots/homeassistant/configuration.yaml).

The export model is intentionally simple:
- Lighting: expose one room-level control per room, named `Room Lights`
- Tado climate: expose one room-level thermostat per room, named `Room Heating`
- Do not expose individual bulbs, Tado helper entities, or appliance helper entities

## Bridge Layout

Current state:

1. `HA Pilot Lights`
   - YAML-managed
   - Include-mode only via `filter.include_entities`
   - Temporary bridge for validation in a separate Apple Home
2. `HA Lights`
   - YAML-managed
   - Include-mode only via `filter.include_entities`
   - Production bridge for room lighting controls
   - Ready for pairing into the main Apple Home when you decide to cut over
3. `HA Climate`
   - YAML-managed
   - Include-mode only via `filter.include_entities`
   - Production bridge for Tado room heating controls plus hot water
   - Ready for pairing into the main Apple Home when you decide to cut over

Planned later entries:
4. Accessory-mode entries for TVs/receivers
   - One per supported `media_player`

## Light Bridge Entity List

Include only these room-level light entities:

- `light.attic_lounge` -> `Attic Lounge Lights`
- `light.davids_office` -> `David's Office Lights`
- `light.dining_room` -> `Dining Room Lights`
- `light.front_porch` -> `Front Porch Lights`
- `light.guest_bedroom` -> `Guest Bedroom Lights`
- `light.hallway` -> `Hallway Lights`
- `light.landing` -> `Landing Lights`
- `light.lounge` -> `Lounge Lights`
- `light.main_bedroom` -> `Main Bedroom Lights`
- `light.ren_s_bedroom` -> `Ren's Bedroom Lights`
- `light.sarahs_office` -> `Sarah's Office Lights`
- `light.side_hall` -> `Side Hall Lights`

`HA Lights` now includes this full canonical room-light set in YAML on port `21064`.

Do not include these individual or non-canonical lights:
- `light.dining_room_ceiling`
- `light.dining_room_shelf_lamp`
- `light.dining_room_sideboard_lamp`
- `light.guest_room_shelf_light`
- `light.hallway_front_door_pendant`
- `light.hallway_pendant`
- `light.hue_ambiance_spot_1`
- `light.hue_ambiance_spot_2`
- `light.hue_ambiance_spot_3`
- `light.hue_filament_bulb_attic_1`
- `light.hue_filament_bulb_attic_2`
- `light.hue_play_left`
- `light.hue_play_right`
- `light.landing_pendant`
- `light.lava_lamp`
- `light.lounge_floor_shade`
- `light.lounge_leaning`
- `light.lounge_sideboard_lamp`
- `light.lounge_sidelamp`
- `light.office_filament`
- `light.rens_bedroom_lamp_1`
- `light.rens_bedroom_lamp_2`
- `light.sarahs_office_floor_lamp`
- `light.sarahs_office_lights_outlet`
- `light.downstairs`
- `light.battery_charger`

## Climate Bridge Entity List

Include only these Tado room-level climate entities plus hot water:

- `climate.attic_lounge` -> `Attic Lounge Heating`
- `climate.davids_office` -> `David's Office Heating`
- `climate.dining_room` -> `Dining Room Heating`
- `climate.guest_bedroom` -> `Guest Bedroom Heating`
- `climate.hallway` -> `Hallway Heating`
- `climate.landing` -> `Landing Heating`
- `climate.lounge` -> `Lounge Heating`
- `climate.main_bedroom` -> `Main Bedroom Heating`
- `climate.nathaniels_bedroom` -> `Nathaniel's Bedroom Heating`
- `climate.ren_s_bedroom` -> `Ren's Bedroom Heating`
- `climate.sarahs_office` -> `Sarah's Office Heating`
- `climate.toilet` -> `Toilet Heating`
- `water_heater.hot_water` -> `Hot Water`

`HA Climate` now includes this full set in YAML on port `21065`.

Hot water note:
- Home Assistant can expose `water_heater.hot_water` through HomeKit Bridge.
- Tado’s native HomeKit support does not support hot water control, so the Apple Home presentation may still feel unlike the Tado app.
- If the exported hot water accessory is not useful in Apple Home, prefer using the HA scripts `tado_hot_water_auto`, `tado_hot_water_off`, and `tado_hot_water_boost` in Home Assistant instead of relying on the bridged water-heater accessory.

Do not include these non-Tado climate entities:
- `climate.ecostrad_klasse_iq`
- `climate.nathaniel_meacocool_mc_series_12000_pro`

Do not include Tado helper entities:
- `* Child lock`
- `* Window`
- `* Temperature`
- `* Humidity`

## Suggested Rollout Order

### Pilot Lights

Use a separate temporary Apple Home first with:
- `light.sarahs_office`
- `light.guest_bedroom`
- `light.ren_s_bedroom`

This pilot bridge is already defined in YAML as `HA Pilot Lights`.

### Production Lights Bridge

`HA Lights` is already defined in YAML and includes the full room-light set. Pair it only when you are ready to start the production room-by-room cutover in your main Apple Home.

### Production Lights

Batch 1:
- `light.sarahs_office`
- `light.guest_bedroom`
- `light.ren_s_bedroom`

Batch 2:
- `light.main_bedroom`
- `light.davids_office`

Batch 3:
- `light.dining_room`
- `light.hallway`
- `light.landing`
- `light.side_hall`
- `light.front_porch`

Batch 4:
- `light.lounge`
- `light.attic_lounge`

### Climate

`HA Climate` is already defined in YAML and includes all canonical Tado room climates plus `water_heater.hot_water`. Pair it when you are ready to start the production climate cutover in your main Apple Home.

Batch 1:
- `climate.davids_office`
- `climate.guest_bedroom`
- `climate.sarahs_office`

Batch 2:
- `climate.main_bedroom`
- `climate.ren_s_bedroom`
- `climate.nathaniels_bedroom`

Batch 3:
- `climate.dining_room`
- `climate.hallway`
- `climate.landing`
- `climate.toilet`

Batch 4:
- `climate.lounge`
- `climate.attic_lounge`
- `water_heater.hot_water`

## Validation Checklist

Before pairing:
- Confirm the customized names appear in Home Assistant as expected
- Confirm no broad HomeKit bridge already exists
- Confirm the bridge will be configured in include mode

For each migrated room:
- Confirm the accessory appears with the exact target name
- Confirm room assignment in Apple Home
- Confirm on/off and brightness for lights
- Confirm current temperature and target temperature for heating
- Remove the old/native accessory only after the HA-backed one passes validation

## Operational Notes

- Finalize the friendly names before first HomeKit pairing because HomeKit can retain the initial exported name.
- The initial pilot bridge is YAML-managed. If you later switch to UI-managed production bridges, delete the YAML pilot bridge first to avoid parallel HomeKit instances for the same migration stage.
- The current light bridges are YAML-managed:
- The current bridges are YAML-managed:
  - `HA Pilot Lights` on port `21063`
  - `HA Lights` on port `21064`
  - `HA Climate` on port `21065`
- If a single entity causes instability, remove only that entity from the bridge and continue with the rest.
