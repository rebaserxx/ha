# Smart Home Audit - 2026-09-15

Scope: Home Assistant core config, automations, scripts, helpers, entity/area registries, Alexa (Home Assistant Cloud), Google Home (Home Assistant Cloud), HomeKit bridges, Assist exposure, integrations and live log health.

Method (read-only, nothing changed):
- `make verify` run first. YAML snapshots match the live server exactly; the only drift is the HA version (`2026.8.3` snapshot vs `2026.9.2` live).
- Read `configuration.yaml`, `automations.yaml` (27 automations), `scripts.yaml` (9 scripts), the three YAML dashboards and all runbooks.
- Pulled the live entity, device, area, floor and exposed-entity registries, repairs registry, energy prefs and assist pipelines (credential files such as `.storage/cloud` were only grepped for boolean flags; no tokens were read).
- Pulled all 748 live states via the REST API and 20,000 lines of core log via `ha host logs`.
- `ha core check` on the live server passes.

Things this audit could NOT see, and which you should check by hand: Alexa app routines/groups and which other skills (Hue, Tado, Meross) are linked; Google Home app rooms and linked services; Apple Home rooms, scenes and whether the Hue bridge / Tado bridge are *also* paired natively; Hue app native automations and motion rules; Tado app schedules; Watchman's list of the 3 missing entities it currently reports.

---

## 1. High-Level Assessment

**Verdict: Home Assistant genuinely is the brain for lighting, hot water and EV approval, and the voice layers are thin and explicitly filtered. That is the hard part and it is done well.** The problems are mostly about hygiene, duplication and a few reliability holes, not architecture.

Scorecard:

| Area | Verdict | Biggest issue |
|---|---|---|
| HA as the brain | Good | Heating schedules still live in the Tado app (acceptable, but document it); Hue still owns the Attic motion rule if one exists |
| Alexa | Good, small cleanups | `water_heater.hot_water` exposed as a mode-only thermostat is awkward; names duplicated in 3 places; 2 exposed lights are dead on the network |
| Google Home | **Broken** | Google is enabled in HA Cloud but zero entities are exposed. Every Google Home query gets "Sorry, I can't do that" or "device not found" |
| HomeKit | Good | Elgato light flaps (21 connection errors in 5 days); Guest Bedroom Lights group has one member and it is unavailable; hot water accessory is a thermostat with no temperature |
| Assist (Cloud voice pipeline) | **Over-exposed** | 148 entities exposed, including `switch.e_ny1_charging`, oven/dishwasher power, all 11 Tado child locks, 42 Hue scenes and 9 dead scenes |
| Automations | Good logic, duplicated structure | Every "lights on" automation bypasses the profile engine and inlines its own targets and brightness; the 22:15/23:30 dims *turn on* lights that were off |
| Reliability | Two real holes | `timer.hot_water_pump_runtime` has no `restore: true` (restart mid-run leaves the pump on); seasonal offsets are `delay`-based so a restart in the window drops the on/off |
| Integrations | Noisy | My Honda+ throws one error every 10 minutes (781 in the log window); Renault has an open re-auth repair; 2 of 4 Meross plugs are unavailable, one of them powers the Hue bridge |
| Registry hygiene | Untidy | 14 orphaned registry entries from deleted YAML (3 automations, 1 script, 9 scenes, 1 helper); duplicate Cast entities for the TV and soundbar; 86 UniFi device trackers |
| Security | Check | Public IP scanner reached `/api/config` on 2026-09-13; no `http:` IP-ban config; verify no port-forward on the gateway |

Top 10 actions, in order of value:

1. Decide whether Google Home is used. If yes, add a `google_assistant:` block under `cloud:` mirroring the Alexa list (section 7.3). If no, turn Google off in Settings > Home Assistant Cloud so it stops syncing an empty device list.
2. Add `restore: true` to `timer.hot_water_pump_runtime` (section 7.2). One-line fix for a pump-runs-forever failure mode.
3. Curate Assist exposure: unexpose child locks, appliance power/programme switches, EV switches, Meross DND "lights", the 9 dead scenes (section 2.9, 6.2).
4. Fix the 22:15 / 23:30 dim automations so they only dim lights that are already on (section 7.5). Today they turn rooms back on at 15%.
5. Replace the hand-rolled seasonal-offset waits with sun-elevation triggers (section 7.6). Simpler, self-adjusting, and survives restarts.
6. Make the "on" automations use the profile engine: add `evening_full`, `morning`, `late` profiles to the core script and route the six inline `light.turn_on` calls through the wrappers (section 7.4).
7. Introduce three virtual devices that work identically on Alexa, Google and HomeKit: `input_boolean.hot_water_boost`, `input_boolean.goodnight`, `input_boolean.lighting_automations_paused` (section 7.7). Retire the raw `water_heater.hot_water` exposure.
8. Repair the physical layer: Meross plugs "Hue Bridge Power" and "Sarah's office lights" are unavailable; `light.guest_room_shelf_light` and `light.hue_filament_bulb_attic_2` are unavailable; the Elgato light is intermittently unreachable. Exposed "Guest Bedroom Lights" is currently a dead accessory on every assistant.
9. Disable `sensor.e_ny1_climate_temperature` (My Honda+ enum bug, 781 errors), complete the Renault re-auth repair, delete the orphaned registry entries.
10. Collapse naming to one source of truth (keep `customize:`, drop the 90-line Alexa `entity_config` block that repeats it) and add Assist aliases for the possessive names.

Added later on 2026-09-15: Ren has moved out to university. "Ren's Bedroom" becomes "Nathaniel's Bedroom" and the current attic "Nathaniel's Bedroom" becomes "Attic Bedroom". The full rename plan is section 10 and it is scheduled as Phase 2R below, before any new voice devices are exposed.

---

## 2. Home Assistant Core Audit

### 2.1 YAML structure

What is good:
- `default_config:`, three clean includes, YAML dashboards with `require_admin: true`, recorder bounded to 21 days, explicit include-mode filters everywhere. Modern syntax (`triggers:`/`trigger:`/`action:`) in automations.
- The repo + `make verify` discipline is unusual and valuable. Keep it.

Issues:

| # | Problem | Why it matters | Fix |
|---|---|---|---|
| C1 | `frontend: themes: !include_dir_merge_named themes` but `/config/themes` does not exist on the server | Harmless today (HA tolerates an empty merge) but it is a dangling reference and any future `ha core check` strictness change will bite | Delete the two lines, or `mkdir /config/themes` |
| C2 | Room names are defined in three places: `homeassistant.customize` (friendly_name), `cloud.alexa.entity_config.name` (identical strings), and the entity registry (`light.lounge` has a registry name "Lounge Lights" on top of the customize entry) | Any rename must be made in 2-3 places; drift produces different names on Alexa vs HomeKit | Keep `customize:` as the single source (it is git-tracked). Delete the whole `cloud.alexa.entity_config` block (Alexa uses `friendly_name` by default). Clear the registry name on `light.lounge` |
| C3 | `scripts.yaml` still uses `service:` in the five lighting scripts while everything else uses `action:` | Not deprecated yet, but it is the old keyword and the mix confuses reviewers | Replace `service:` with `action:` (mechanical) |
| C4 | `cloud:` has an `alexa:` block but no `google_assistant:` block while Google is enabled | See section 4 | Add the block or disable Google |
| C5 | `input_number` units are `m3` while the template sensors use `m³` | Cosmetic, but the Utilities dashboard shows two spellings | Use `m³` on both helpers |
| C6 | `configuration.yaml` is described in the reference doc as "root include map only (keep minimal)" but it now carries 427 lines of inline concerns | Doc and reality disagree; the file is the hardest one to review | Either update the doc (cheapest) or move `homekit`, `cloud`, `template`, helpers into `packages/` (section 8). If you use packages, add them to `scripts/sync_from_ha.sh` |
| C7 | HTTP settings are storage-managed since 2026.8 (`.storage/http`): `ip_ban_enabled: true` but `login_attempts_threshold: -1`, so no automatic banning. The log shows an unauthenticated request from a public IP (64.89.161.85) to `/api/config` on 2026-09-13 | Either the Nabu Casa remote URL is being scanned (likely) or the gateway has a port-forward. Bans cost nothing | Done in Phase 1: threshold set to 10 in the UI and promoted (a YAML `http:` block is ignored and raises a repair). Still confirm on the UCG Fiber that 8123 is not forwarded |

### 2.2 Deprecated or legacy config

- `customize:` for friendly names is legacy-but-supported. It is the right tool here because it is git-tracked. Do not migrate to registry names unless you are prepared to lose git history of names.
- `service:` keyword (C3).
- Repairs currently open on the server: My Honda+ `units_changed` for `sensor.left_oven_current_oven_cavity_temperature` (needs the repair flow run once), two Octopus `meter_added` prompts, a Renault **re-authentication** prompt (`config_entry_reauth_renault_*`), and ten HACS "restart required" prompts that a restart clears.
- Repairs already dismissed that matter: `tado water_heater_fallback` (see 3.3 for why the Tado fallback matters to voice).

### 2.3 Automations (27)

Design summary: schedule automations call shared scripts for *off*, but every *on* path inlines its own area list and brightness. The profile engine (`day`/`evening`/`night`) is therefore used by nothing in production; the wrappers are only used for "off".

| # | Automation | Problem | Why it matters | Fix |
|---|---|---|---|---|
| A1 | `lighting_common_evening_sunset_on_seasonal`, `_0620_presunrise`, `_0650_presunrise`, `_dim_2215`, `_dim_2330`, `lighting_front_porch_on_*` | Six copies of the same six-area list and inline `brightness_pct`/`color_temp_kelvin` | Adding a room means editing 8 places; the documented "change profile defaults in the core script" path does nothing | Add `evening_full`, `morning`, `late` profiles to `lighting_apply_profile_core`, then call the wrappers (7.4) |
| A2 | `lighting_common_lounge_dim_2215_sun_thu`, `_2330_fri_sat` | `light.turn_on` with `brightness_pct: 15` on whole areas **turns on lights that are off** | Someone switches the dining room off at 21:00; at 22:15 it comes back on at 15%. The 19:00 automation already solved this with a "currently on" filter; these two did not copy it | Use the same filtered-entity pattern via one shared script (7.5) |
| A3 | `lighting_common_evening_sunset_on_seasonal` + `lighting_evening_dim_1900` | Sunset-on is always 100%. In summer sunset is after 19:00, so the 19:00 dim has already run and lights stay at 100% until 22:15. In winter they come on at ~15:30 at 100% and dim at 19:00 | Different evening experience by season, almost certainly unintended | Make the sunset-on pick `evening_full` before 19:00 and `evening` after (7.4) |
| A4 | Seasonal offsets via `script.lighting_wait_seasonal_offset` (a `delay` of 0-60 min) | A restart, reload or `automation.reload` inside the window kills the run. Sunset −1h trigger + wait also means the automation is "running" for up to an hour every evening | Lights don't come on / don't go off on the evening you restarted HA for an update | Trigger on `sun.sun` elevation instead (7.6). No delay, no season table, self-adjusting to latitude and date |
| A5 | `lighting_common_weekday_morning_0620_presunrise` / `_0650_presunrise`; `_dim_2215` / `_2330`; `_off_2300` / `_2359` | Three pairs that differ only by time and weekday | Twice the surface area to keep in sync | Merge each pair with two triggers, trigger ids and a `condition: trigger` (7.4) |
| A6 | `lighting_all_lights_off_after_sunrise_seasonal` | Alias says "All Lights" but it targets common + porch only (the doc explains the history) | Misleading name in traces and the UI | Rename alias to "Common + Porch Off After Sunrise" |
| A7 | `lighting_front_porch_motion_overnight` | The template trigger matches *both* `binary_sensor.front_porch_motion` (Hue "room" aggregate) and `binary_sensor.hue_outdoor_motion_sensor_1_motion` (the physical sensor). Also: motion at 06:15 that clears after 06:20 leaves the porch at 50% (the off-step conditions fail) until sunrise-off | Redundant double-trigger; small brightness edge case | Pin to the physical sensor with a plain `state` trigger; drop the post-wait time condition and just turn off unless the 06:20 schedule has taken over (7.6) |
| A8 | `hot_water_pump_off_when_runtime_finishes` | Listens to `timer.finished` only. `timer.cancelled` (dashboard "cancel") leaves the pump on | Minor; the 30-minute manual guard does not cover this case because the pump was started by an automation | Trigger on both `timer.finished` and `timer.cancelled` |
| A9 | `hot_water_pump_follow_tado_on_for_1h` | No watchdog (dashboard plan item 5 still open). Nothing alerts if the pump switch fails to turn on, or stays on beyond 1h | The pump is a Meross plug on the LAN; if `meross_lan` loses it the pump silently never runs | Add the alert-only watchdog in 7.8 |
| A10 | Four `ev_*` automations | The claim-gate Jinja (10 lines) is pasted 8 times; each automation is ~110 lines; two `/5` ticks and one `/15` tick. Every Renault run also presses the Honda refresh button, so the Honda is woken every ≤15 min while the Renault charges | Correctness is fine (the incident notes are excellent), but this is the least maintainable code in the system and the Honda wake-ups are gratuitous | Move the claim logic into two template binary sensors plus a settled "car on charger" sensor with `delay_on: 60s` (7.10). Automations then become ~30 lines each and the settle/re-check is implicit |
| A11 | `ev_ohme_sync_*` | `mode: single` + `max_exceeded: silent` with runs that can hold for 9 minutes (6 min gate + 1 min settle + 2 min wait) | Correct, but a plug-in trigger that lands during a retry-tick run is silently dropped; the next tick catches it, adding up to 5 minutes | With template sensors (7.10) the wait disappears and `mode: queued` becomes safe |
| A12 | All alert automations (`system_*`, `tado_*_alert`, `octopus_*`) | Persistent notifications only; `notify.mobile_app_davids_iphone` exists and is unused | Persistent notifications are only seen when someone opens HA | Add `script.notify_admin` that does both, and call it everywhere (7.8). Keep the daily cadence you already chose |

Automations that should be scripts: none. The schedule/trigger layer is correctly automations. The *bodies* of A1 should be script calls.
Scripts that should be automations: none. `tado_hot_water_*` and `tado_gas_set_manual_baseline` are correctly on-demand.

### 2.4 Scripts (9)

- `lighting_apply_profile_core`: sound. `mode: restart` is right for a shared engine. Add the three profiles above. Consider accepting a `brightness_pct`/`color_temp_kelvin` override so one-off tweaks do not need a new profile.
- `lighting_wait_seasonal_offset`: retire after A4 (keep until the elevation triggers have been observed for a week).
- `lighting_common_areas`, `lighting_bedrooms`, `lighting_outside`: fine. `lighting_bedrooms` is called by nothing; keep it for voice/scene use.
- `tado_hot_water_boost`: this is the thing family members actually want from voice. Expose it (7.7).
- Orphan: `script.lighting_wait_seasonal_delay` exists only in the registry (`unavailable`). Delete.

### 2.5 Helpers

Present: 2 `input_number`, 1 `input_datetime`, 1 `timer`. No `input_boolean`, no `input_select`, one `person`.

Missing helpers that the architecture wants:
- `timer.hot_water_pump_runtime` needs `restore: true` (R1).
- `input_boolean.hot_water_boost` - a real on/off "device" for all three assistants instead of a mode-only water heater.
- `input_boolean.goodnight` - momentary trigger for a Siri/Alexa/Google "Goodnight" scene that runs HA logic.
- `input_boolean.lighting_automations_paused` - guest/holiday switch checked by every lighting automation (today there is no way to pause the schedule without disabling 15 automations).
- `person.*` for Sarah, Ren and Nathaniel, and a `binary_sensor.anyone_home` group. The five Tado geofence trackers are all `unavailable` since the 2026-09-13 restart, so presence today is David's iPhone only. UniFi already tracks Sarah's, Ren's and Nathaniel's iPhones.
- Orphan: `input_number.tado_gas_meter_register_m3` is registry-only (`unavailable`). Delete.

### 2.6 Race conditions and restart fragility

| # | Where | Failure | Fix |
|---|---|---|---|
| R1 | `timer.hot_water_pump_runtime` | Timers do not survive a restart unless `restore: true`. Restart during the hour: `timer.finished` never fires, pump runs until the next Tado demand cycle restarts the timer (could be next morning) | `restore: true` |
| R2 | Seasonal `delay` waits (A4), 30-minute manual pump guard, 20-minute motion wait | All `delay`/`wait` based; lost on restart/reload | Elevation triggers for lighting; accept for the pump guard (30 min, low harm) or switch to a timer with `restore` |
| R3 | 22:15 dim vs manual off (A2) | Lights re-lit at 15% | Filter to lights that are on |
| R4 | `hot_water_pump_manual_auto_off_30m` relies on `trigger.to_state.context.parent_id is none` | Correct for physical/UI/voice starts; an automation start has a parent context. Note that a HomeKit or Alexa start has no parent id and *is* treated as manual, which is what you want | None |
| R5 | EV approve automations | Already handled by the settle + re-check. The remaining gap is A11 (silent drop) | 7.10 |

### 2.7 Polling and load

- `sql:` sensor polls the recorder every 30 s for a value that changes at most hourly. Acceptable cost, but it is the only thing hitting the DB constantly. There is no YAML `scan_interval` for `sql`; if it ever shows in the DB profiler, move it to a UI SQL entry and untick polling, then update it from the gas rollover automation with `homeassistant.update_entity`.
- Four `time_pattern` ticks (`/5`, `/5`, `/5`, `/15`). Cheap because of the conditions, but 7.10 removes the need for three of them.
- UniFi: 86 `device_tracker` entities (printers, consoles, Nest Protects, 14 unnamed MACs) each writing state changes to the recorder. Turn off "Track network clients" in the UniFi integration options, or keep it on and add the recorder exclusion in 7.9. Presence for people can come from the mobile app and a handful of explicitly enabled iPhones.
- Mobile app: 40 iPhone/iPad sensors are `unavailable` (sensors the app is not permitted to report). They are harmless but clutter; disable the ones you never use in the companion app settings.
- My Honda+ has `switch.e_ny1_auto_refresh_from_car` on *and* the EV automations force a refresh every ≤15 min while a car is plugged in. The car is on mains so battery drain is not the concern; API rate limiting is. 7.10 reduces the forced refreshes to the Honda's own runs.

### 2.8 Integrations

Live log, last ~5 days, by source:

| Source | Count | Meaning | Action |
|---|---|---|---|
| `custom_components.myhondaplus` | 781 errors | `sensor.e_ny1_climate_temperature` is declared as an enum sensor but reports `17`; every coordinator update (10 min) throws | Disable that one entity in the registry (stops the listener); report upstream |
| `octopus_energy.api_client` / `intelligent_dispatches` | 74 warn + 68 err + 44 warn | "Unable to fetch planned dispatches" bursts (Octopus API side). Integration falls back to cached dispatches | Nothing to fix locally; be aware `binary_sensor...intelligent_dispatching` can be stale during bursts |
| `renault.renault_vehicle` | 50 errors | `err.func.wired.unauthorized` on location fetches + an open re-auth repair | **Complete the re-auth repair.** If the location tracker goes stale, the Renault claim gate can never pass and Renault sessions stop being auto-approved |
| `pychromecast` | 35 errors | Cast keeps trying the LG TV and soundbar when they are off. There are two Cast entities for the TV (`media_player.lg_webos_tv` duplicates `media_player.lounge_tv` from webOS) and two for the soundbar (`media_player.s95qr` is a stale duplicate of `media_player.lg_speaker_s95qr_0793`) | Delete the stale soundbar entity; disable the Cast TV entity (webOS is the better integration for the TV). Cast will stop opening sockets to disabled entities |
| `unifi` / `aiounifi` | 34 + 7 errors | TrafficRules/TrafficRoutes/ObjectOrientedNetworkConfigs "unexpected error" and websocket handshake 502/200 around 2026-09-11 17:09 (gateway update?) | Watch after the next HA/UniFi update; not actionable now |
| `elgato` | 21 errors | Key Light Air intermittently unreachable | It is in the HomeKit Lights bridge, so it flaps as "No Response". Give it a DHCP reservation, or remove it from the bridge (it has native HomeKit if it is the Air model) |
| `webostv` / `apple_tv` | 6 + 6 | TV / Apple TV asleep | Normal. Optional: `wake_on_lan` so `media_player.lounge_tv` can turn on |
| `alexa.state_report` | 2 | Timeouts reporting `light.davids_office` | Transient |
| `http.ban` | 1 | Public IP probe (2.1 C7) | Enable bans |
| `tuya` | 1 warn | Ecostrad reports mode `frost` which the Tuya schema doesn't know | Cosmetic; the climate entity still works with `off`/`heat` and preset `eco` |

Integrations to remove or disable:
- `google_translate` TTS (Cloud TTS is the preferred pipeline and set as default).
- `met` (already disabled by user; delete the entry, `metoffice` is the weather source).
- `radio_browser`, `shopping_list`: harmless; delete if unused.
- `nest` and `upnp` are already "ignored", fine.
- Meross `light.*_dnd` (4 entities, the plug's LED do-not-disturb mode exposed as a *light*) and `switch.*_config_overtemp_enable` (4): disable. They are lights and switches in the eyes of every assistant and only your explicit filters keep them out.

Integrations to add:
- `group` (light group) for Sarah's Office: `light.sarahs_office` is a Hue room containing only the floor lamp; the Meross-driven `light.sarahs_office_lights_outlet` (switch_as_x) is separate and currently unavailable. Once the plug is back, an HA light group of both becomes the exposed "Sarah's Office Lights".
- `template` binary sensors for the EV claim gate (7.10).
- `person` entities for the household (2.5).
- `wake_on_lan` if you want the TV controllable from voice.
- Optional: the UI "Statistics"/"Utility meter" helpers are not needed; the SQL approach works.

Not recommended: Alexa Media Player, Google Home community integrations, or an LLM conversation agent. They add cloud dependencies without moving logic into HA.

### 2.9 Registry hygiene

Orphaned registry entries (exist only in the registry, state `unavailable`, referenced by nothing):
- `automation.lighting_common_areas_off_after_sunrise_seasonal_daily`
- `automation.lighting_common_areas_on_at_dusk`
- `automation.tado_submit_daily_gas_meter_reading_from_octopus`
- `script.lighting_wait_seasonal_delay`
- `input_number.tado_gas_meter_register_m3`
- `scene.lighting_evening_attic_lounge`, `_dining_room`, `_front_porch`, `_hallway`, `_landing`, `_lounge`, `_main_bedroom`, `_ren_s_bedroom`, `_side_hall` (nine scenes from an earlier `scenes.yaml`; all nine are currently **exposed to Assist**)

Delete all 14 from Settings > Devices & services > Entities (filter: unavailable). Watchman currently reports 3 missing entities; run the report to see whether any of these are the cause.

Duplicates: `media_player.s95qr` vs `media_player.lg_speaker_s95qr_0793` (same device UID family, one dead); `media_player.lg_webos_tv` (Cast) vs `media_player.lounge_tv` (webOS); `binary_sensor.front_porch_motion` (Hue room aggregate) vs `binary_sensor.hue_outdoor_motion_sensor_1_motion`.

Area assignments to fix: `light.elgato_key_light_air` is in "Utilities" (it is a desk light; HomeKit will suggest the wrong room); `device_tracker.e_ny1_location` and the Renault tracker are in "Utilities" (fine). The area whose *id* is `hot_water` is named "Utilities"; you cannot rename an area id, but note it in the reference doc so nobody targets `area_id: utilities`.

Entity ID conventions are inconsistent (`ren_s_bedroom` vs `rens_bedroom_lamp_1`, `sarahs_office` vs area `sarah_s_office`, `davids_office` vs area `david_s_office`). Do **not** mass-rename: HomeKit pairings and Alexa device IDs key off entity ids and you would re-pair everything. Adopt the rule "new entities use the area id spelling" and leave the old ones.

Dead hardware currently exposed to voice:
- `light.guest_bedroom` = Hue room with one member, `light.guest_room_shelf_light`, which is `unavailable`. "Guest Bedroom Lights" is a dead accessory on Alexa, HomeKit and Assist.
- `light.attic_lounge` = two filament bulbs, one (`hue_filament_bulb_attic_2`) `unavailable`. Half-lit room.
- Meross "Hue Bridge Power" plug (`switch.smart_switch_...3c8_outlet`) is `unavailable`. This plug powers the Hue bridge, i.e. every light in the house. It should never be voice-exposed (it is not) and ideally should not be a smart plug at all.
- Meross "Sarah's office lights" plug is `unavailable`, so `light.sarahs_office_lights_outlet` is dead.
- Both Meaco AC units are `unavailable` (Tuya cloud; presumably unplugged for winter). HomeKit shows "No Response" for the whole "HA Air Conditioning" bridge until spring. Acceptable, but tell the family.

### 2.10 Security

- HA Cloud remote access is on (`remote_enabled: true`). One unauthenticated probe from a public IP reached the HTTP layer. Add IP banning (7.9) and confirm no NAT rule on the UCG Fiber.
- Terminal & SSH add-on: key auth, TCP forwarding off. Fine.
- The `HOMEASSISTANT_TOKEN` env var is set on the workstation for the REST API. Rotate it if this workstation is ever shared.
- `.tado_meter_token.json` is chmod 600 and outside git. Fine.

---

## 3. Alexa Audit

Configuration: Home Assistant Cloud, YAML-filtered (`cloud.alexa.filter.include_entities`), 25 entities: 12 room light groups, 12 Tado zones, `water_heater.hot_water`. Report-state is on (default). Devices in the house: Echo Clock, Echo Show, Fire TV Stick.

### 3.1 Exposed entity review

| Entity | Alexa sees | Verdict |
|---|---|---|
| 12 `light.*` room groups | LIGHT with brightness + colour temperature | Correct. Exactly the right granularity (room groups, no bulbs) |
| 12 `climate.*` Tado zones | THERMOSTAT, modes HEAT/AUTO/OFF, 5-25 °C | Correct. Note "AUTO" = Tado schedule, "HEAT" = manual overlay |
| `water_heater.hot_water` | Thermostat-style device with modes AUTO/HEAT/OFF and **no target temperature** (Tado hot water has `supported_features: 2`, operation mode only) | Awkward. "Alexa, turn on the hot water" sets mode HEAT = permanent manual heat until someone sets it back. Replace with a boost switch (7.7) |
| Guest Bedroom Lights | A LIGHT whose only bulb is offline | Dead device until the bulb is fixed |

Entities that should be exposed but are not:
- A **Hot Water Boost** control (script or input_boolean). This is the most common family request and today needs the Tado app.
- Optionally 3-4 Hue scenes as Alexa scenes ("Lounge Relax", "Dining Room Read"). Alexa handles `scene.*` well. Not more than a handful, or "I don't know that one" rises because of near-duplicate names.
- Not `switch.hot_water_pump`, appliances, child locks, EV controls. Correctly excluded.

### 3.2 Naming

- Pattern `Room Lights` / `Room Heating` is right for Alexa: unique, two-token, no brand names.
- Possessives (`David's`, `Sarah's`, `Nathaniel's`) are usually fine on Alexa. "Ren's" was the risky one (ASR often hears "Wren's" or "Rens") and it disappears with the room rename in section 10; "Nathaniel's" is long but distinctive. Alexa has no alias mechanism through HA. If a name misfires in testing, the least disruptive fix is an Alexa **group** with the room's name containing that light and thermostat; groups get their own ASR handling.
- "Side Hall Lights" vs "Hallway Lights": "hall lights" is ambiguous. Test both phrases. If it collides, rename Side Hall to something spatially distinct (e.g. "Back Hall Lights").
- "Attic Lounge Lights" vs "Lounge Lights": Alexa prefers exact matches, so this is fine.
- "Toilet Heating" is fine in the UK.

### 3.3 Device categories and behaviour

- No `display_categories` overrides are needed; HA picks LIGHT and THERMOSTAT.
- Tado fallback is `TADO_DEFAULT`, which means a voice-set temperature expires according to the Tado app's default overlay setting. Make sure that app setting is "until next automatic change", not "manual", otherwise every "Alexa, set lounge heating to 21" becomes a permanent override and Tado stops being the schedule brain.
- Remove the `entity_config` block: the `name` values duplicate `customize`, and `description: Room lighting` is only shown in the Alexa app's device detail.

### 3.4 Routines and duplicated logic

- Alexa routines cannot be read from HA. Policy: the only routines allowed are voice phrase → HA scene/switch (e.g. "Alexa, goodnight" → turn on `Goodnight`). No schedules, no device-to-device routines in Alexa.
- If the Hue, Tado or Meross Alexa skills are still linked, every room exists twice ("Lounge" from Hue, "Lounge Lights" from HA) and Alexa will sometimes control the native one, bypassing HA. Unlink them; keep only Home Assistant. Checked in Phase 0: Hue and Tado are **not** linked (good). Tuya, SmartLife, Meross, Home Connect and LG ThinQ are, and are unlinked in Phase 3V after HA takes over the AC units and the kitchen heater. Media skills (Apple Music/Podcasts, BBC News/Sounds, Plex, ITVX, Xbox) are unrelated and stay.

### 3.5 Reducing "I don't know that one"

1. Unlink other skills (above).
2. Put each Echo in an Alexa group with that room's `Room Lights` and `Room Heating`, so "turn on the lights" / "set the heating to 20" work without the room name.
3. Keep the exposed set small and stable; every rename forces Alexa to re-discover and old names linger.
4. Expose the three virtual devices (7.7) so "goodnight", "boost the hot water", "pause the lights" are single-device commands rather than sentences Alexa must parse.

---

## 4. Google Home Audit

State: `google_enabled: true` in HA Cloud, no `google_assistant:` YAML block, and in the exposed-entities registry **no entity has `cloud.google_assistant: should_expose: true`** (every controllable entity is explicitly `false`; the remaining 268 have no setting and `expose_new` is off). Devices in the house: Google Nest Hub, Google Home Mini, a Cast "Google speaker" in the dining room, and Ren's bedroom display.

Result: Google Home is linked to a Home Assistant that offers it zero devices. Every "Hey Google, turn on the lounge lights" that reaches HA is answered with "Sorry, it looks like that device hasn't been set up yet" (or, if the Hue/Tado native Google links are still present, Google controls those directly and HA is bypassed).

### 4.1 Decision

- If the household uses Google Home for control: add the YAML block in 7.3 (same 24 lights/zones, minus the water heater, plus the virtual devices). Google reads `area` as the room hint automatically, so rooms line up in the Google Home app without per-entity config. Google supports `aliases` per entity, which Alexa does not, so this is where "Ren's" and "Sarah's" get spoken alternatives.
- If Google Home is only used for music/timers: switch Google off in Settings > Home Assistant Cloud. Leaving it on with nothing exposed just causes periodic empty SYNC requests.

Decided in Phase 0 (2026-09-15): the household wants Google Home controlling through HA. The Google Home app currently links Philips Hue, Tuya/SmartLife/Meross and Home Connect/LG ThinQ directly; those are unlinked in Phase 3V once the HA devices are verified.

### 4.2 Traits and device types (if you expose)

| Entity | Google type / traits | Notes |
|---|---|---|
| `light.*` room groups | LIGHT: OnOff, Brightness, ColorSetting (colour temperature) | Fine. `light.attic_lounge` and `light.side_hall` are brightness-only and are reported correctly |
| `climate.*` Tado | THERMOSTAT: TemperatureSetting, modes off/heat/auto | Tado presets (home/away) are not mapped; that is fine |
| `climate.ecostrad_klasse_iq` | THERMOSTAT off/heat (presets removed by the local Tuya quirk; heater must stay in Comfort mode) | Fine after the 2026-09-15 quirk |
| Meaco AC | THERMOSTAT off/cool | Unavailable in winter; Google shows "offline" |
| `water_heater.hot_water` | Supported as a water heater with TemperatureSetting, but Tado exposes no target temperature | Same awkwardness as Alexa. Do not expose; use the boost switch |
| `input_boolean.*` | SWITCH | Ideal for the virtual devices |
| `script.*` | SCENE | "Hey Google, activate Hot Water Boost" |

Unsupported: `timer`, `input_number`, `event`, `device_tracker`, `binary_sensor` are not Google device types; nothing you would want exposed falls in those anyway.

### 4.3 Naming and reliability

- Use the same names as Alexa/HomeKit. Add `aliases` for possessives and the hall ambiguity (7.3).
- Google's "Sorry, I can't do that yet" comes from three causes: no devices synced (current state), a device type without the requested trait (e.g. asking a brightness-only light for a colour), or duplicated devices from a second linked service. The fix for the first two is the YAML block; the third is unlinking Hue/Tado from Google Home.
- After changing the YAML, say "Hey Google, sync my devices" or use `google_assistant.request_sync` from Developer Tools.

---

## 5. HomeKit Audit

Configuration: four YAML bridges (`HA Lights` :21064, `HA Climate` :21065, `HA Air Conditioning` :21066, `HA Kitchen Heating` :21067), include-mode, 29 accessories total. All four bridges are paired (4 controllers each). An older bridge's state files (`homekit.01KJM7GT...removed.*`) are left over and can be deleted.

### 5.1 Exposed entities

| Bridge | Entities | Verdict |
|---|---|---|
| HA Lights | 12 room groups + `light.elgato_key_light_air` | Room groups correct. Elgato: 21 unreachable errors in 5 days, wrong area (Utilities), and the Air model has native HomeKit. Either fix its network reservation or drop it from the bridge and pair it natively |
| HA Climate | 12 Tado zones + `water_heater.hot_water` | Zones correct (Heat/Auto/Off, 5-25 °C). Hot water becomes a HomeKit Thermostat with no adjustable temperature; Siri answers "set to what temperature?" Replace with a switch (7.7) |
| HA Air Conditioning | 2 Meaco units | Both unavailable now; correct to keep separate so the whole "no response" is isolated |
| HA Kitchen Heating | Ecostrad | Works as Heat/Off thermostat. Naming: everything else is `Room Heating`; this one is `Kitchen Ecostrad Heater`. Since it *is* the kitchen's heating, `Kitchen Heating` is the consistent name and lets Siri handle "set the kitchen heating to 20". Rename before any re-pair, otherwise HomeKit keeps the old name |

Four bridges vs one: 29 accessories fit easily in one bridge, but your split isolates cloud-flaky Tuya devices from the Hue/Tado bridges and keeps re-pairing blast radius small. Keep it.

### 5.2 Naming for Siri

- `Room Lights` in room `Room` is the HomeKit-friendly pattern: "turn off the lounge lights" and "turn off the lights in the lounge" both work, and a HomePod/Apple TV in that room makes "turn off the lights" work.
- Confirm in the Home app that each accessory is in the matching room. HA suggests the area at pairing time but the Home app does not update it afterwards; the Elgato light will have landed in "Utilities" or "Default Room".
- Apostrophes are fine for Siri.

### 5.3 Device-class / accessory-type mismatches

- `water_heater` → Thermostat (see above).
- `switch.hot_water_pump` is not exposed; if you ever expose it, HomeKit needs `entity_config: type: switch` (default) rather than `outlet` so it does not appear as a power point.
- `script.*` appear as momentary switches, `input_boolean.*` as switches. Both are the right primitives for scene-style triggers.

### 5.4 HomeKit-friendly virtual devices and scene-based triggers

HomeKit scenes live in Apple Home, so the way to let a Siri scene run HA logic is: Siri scene → toggles an HA-exposed switch → HA automation. Provide (7.7):
- `input_boolean.goodnight` exposed as a switch. Home app scene "Goodnight" turns it on; HA automation runs `lighting_common_areas off`, `lighting_outside off`, office filament off, then resets the boolean. Works identically from Alexa ("turn on goodnight") and Google.
- `input_boolean.hot_water_boost` exposed as a switch, mirrored to Tado state so the tile shows the truth.
- `input_boolean.lighting_automations_paused` exposed only on the HomeKit bridge (admin household members) so a holiday or party can pause the schedule from a phone.

Add an `entity_config` to the bridge for these so they get the intended names without touching `customize`.

### 5.5 Siri reliability

- Every accessory that is `unavailable` in HA shows "No Response" and slows the Home app's status refresh. Today: Guest Bedroom Lights (dead bulb), both AC units, Elgato intermittently.
- Keep the HA host on a wired connection and mDNS reachable from the Apple TV hub (the UniFi log shows nothing wrong here).
- After changing any exposed name, restart the bridge (reload the HomeKit entry); names sent at first pairing are retained by iOS, so rename *before* pairing new accessories.

---

## 6. Integration Architecture Fixes (cross-cutting)

### 6.1 One exposure policy

Tier 1, family voice (Alexa + Google + HomeKit): 12 `Room Lights`, 12 `Room Heating`, `Kitchen Heating`, 2 `Room AC`, `Hot Water Boost`, `Goodnight`. Optional: 3-4 Hue scenes.
Tier 2, admin voice (HomeKit only, and Assist on the admin phone): `Lighting Automations Paused`, `Water Pump`.
Tier 3, never voice: bulbs, plugs, child locks, appliance power/programme controls, EV controls, DND/overtemp entities, diagnostics.

Assist exposure today covers Tier 1 + most of Tier 3. Trim it to Tier 1 + Tier 2 (the "Expose" tab under Settings > Voice assistants, or the `conversation` options per entity).

### 6.2 One naming source

`customize:` in `configuration.yaml` is the source of truth for every Tier 1/2 name. Remove the Alexa `entity_config` names. Put aliases (Assist and Google support them; Alexa and HomeKit do not) in the entity registry `aliases` field and in the Google `entity_config`.

### 6.3 One "brain" contract per domain

| Domain | Brain | Voice assistants may | Voice assistants may not |
|---|---|---|---|
| Lighting | HA automations + profile engine | Turn rooms on/off/dim, activate Goodnight, pause automations | Have their own schedules (delete Hue "Automation: Evening Downstairs/Upstairs" in the Hue app; disable Alexa/Google scheduled routines) |
| Heating | Tado schedules (in the Tado app) with HA as the override channel | Set a temporary temperature; HA + Tado fallback expire it | Change modes permanently |
| Hot water | HA (`hot_water_boost` → `tado_hot_water_boost`) | Boost / cancel boost | Touch the water heater mode directly |
| EV | HA approve automations + Ohme/IOG scheduling | Nothing | Start, stop or approve charging |
| Appliances | Home Connect / ThinQ apps | Nothing | Anything |

### 6.4 Presence

Create `person` entities for Sarah, Nathaniel and (optionally) Ren using the UniFi iPhone trackers; Ren is at university, so a `person.ren` only matters for holiday visits and is harmless to include (and the Companion app where installed), plus `binary_sensor.anyone_home`. Then add `condition: state anyone_home on` to the sunset-on automation only (alert-first philosophy; nothing else changes). The Tado geofence trackers are unavailable and should not be relied on.

---

## 7. YAML / JSON Examples

All snippets are drop-in for the current file layout. Validate with `ha core check`, reload the affected domain, then `make verify`, and log in `docs/change_log.md` per the playbook.

### 7.1 configuration.yaml: naming and cloud cleanup

Remove `cloud.alexa.entity_config` entirely. The block becomes:

```yaml
cloud:
  alexa:
    filter:
      include_entities:
        - light.attic_lounge
        - light.davids_office
        - light.dining_room
        - light.front_porch
        - light.guest_bedroom
        - light.hallway
        - light.landing
        - light.lounge
        - light.main_bedroom
        - light.ren_s_bedroom
        - light.sarahs_office
        - light.side_hall
        - climate.attic_lounge
        - climate.davids_office
        - climate.dining_room
        - climate.guest_bedroom
        - climate.hallway
        - climate.landing
        - climate.lounge
        - climate.main_bedroom
        - climate.nathaniels_bedroom
        - climate.ren_s_bedroom
        - climate.sarahs_office
        - climate.toilet
        - climate.ecostrad_klasse_iq
        - climate.nathaniel_meacocool_mc_series_12000_pro   # Attic Bedroom AC (Phase 0: replaces the Tuya/SmartLife skill)
        - climate.meacocool_mc_series_12000_pro_2           # Nathaniel's Bedroom AC
        - sensor.left_oven_current_oven_cavity_temperature  # oven temperature by voice (7.12)
        - sensor.right_oven_current_oven_cavity_temperature
        - input_boolean.hot_water_boost
        - input_boolean.goodnight
        # water_heater.hot_water removed: mode-only device, replaced by the boost switch
```

Add to `homeassistant.customize` (and rename the Ecostrad for consistency; do this before re-pairing the kitchen bridge):

```yaml
    climate.ecostrad_klasse_iq:
      friendly_name: Kitchen Heating
    input_boolean.hot_water_boost:
      friendly_name: Hot Water Boost
      icon: mdi:water-boiler
    input_boolean.goodnight:
      friendly_name: Goodnight
      icon: mdi:weather-night
    input_boolean.lighting_automations_paused:
      friendly_name: Lighting Automations Paused
      icon: mdi:pause-circle

    # Room rename 2026-09 (section 10). Entity ids are historical and deliberately unchanged:
    # *ren_s_bedroom* entities are Nathaniel's Bedroom (first floor);
    # *nathaniels_bedroom* / *nathaniel_meacocool* entities are the Attic Bedroom.
    light.ren_s_bedroom:
      friendly_name: Nathaniel's Bedroom Lights
    climate.ren_s_bedroom:
      friendly_name: Nathaniel's Bedroom Heating
    climate.meacocool_mc_series_12000_pro_2:
      friendly_name: Nathaniel's Bedroom AC
    climate.nathaniels_bedroom:
      friendly_name: Attic Bedroom Heating
    climate.nathaniel_meacocool_mc_series_12000_pro:
      friendly_name: Attic Bedroom AC
```

Delete the `frontend:` block (no themes directory exists) or create the directory.

### 7.2 Helpers

```yaml
timer:
  hot_water_pump_runtime:
    name: Hot Water Pump Runtime
    duration: "01:00:00"
    restore: true          # survives restarts; without this the pump can run until the next Tado cycle

input_boolean:
  hot_water_boost:
    name: Hot Water Boost
    icon: mdi:water-boiler
  goodnight:
    name: Goodnight
    icon: mdi:weather-night
  lighting_automations_paused:
    name: Lighting Automations Paused
    icon: mdi:pause-circle

input_number:
  tado_gas_meter_baseline_m3:
    name: Tado Gas Meter Baseline m3
    min: -999999
    max: 999999
    step: 0.001
    mode: box
    unit_of_measurement: "m³"
  tado_gas_meter_last_submitted_m3:
    name: Tado Gas Meter Last Submitted m3
    min: 0
    max: 999999
    step: 1
    mode: box
    unit_of_measurement: "m³"
```

### 7.3 Google Home exposure (only if Google is used)

**Not valid as YAML on HA 2026.9 - see the correction under Phase 3V. Use this only as the exposure list; apply it in Settings > Voice assistants > Expose, with aliases in the entity registry.**

```yaml
cloud:
  google_assistant:
    filter:
      include_entities:
        - light.attic_lounge
        - light.davids_office
        - light.dining_room
        - light.front_porch
        - light.guest_bedroom
        - light.hallway
        - light.landing
        - light.lounge
        - light.main_bedroom
        - light.ren_s_bedroom
        - light.sarahs_office
        - light.side_hall
        - climate.attic_lounge
        - climate.davids_office
        - climate.dining_room
        - climate.guest_bedroom
        - climate.hallway
        - climate.landing
        - climate.lounge
        - climate.main_bedroom
        - climate.nathaniels_bedroom
        - climate.ren_s_bedroom
        - climate.sarahs_office
        - climate.toilet
        - climate.ecostrad_klasse_iq
        - climate.nathaniel_meacocool_mc_series_12000_pro
        - climate.meacocool_mc_series_12000_pro_2
        - input_boolean.hot_water_boost
        - input_boolean.goodnight
    entity_config:
      # Google supports aliases; use them for the names ASR gets wrong.
      light.ren_s_bedroom:          # Nathaniel's Bedroom after the section 10 rename
        aliases: ["Nathaniels Bedroom Lights", "Nathaniel Bedroom Lights"]
      climate.ren_s_bedroom:
        aliases: ["Nathaniels Bedroom Heating", "Nathaniel Bedroom Heating"]
      climate.nathaniels_bedroom:   # Attic Bedroom after the rename
        aliases: ["Attic Room Heating", "Spare Bedroom Heating"]
      light.side_hall:
        aliases: ["Back Hall Lights", "Side Hallway Lights"]
      light.davids_office:
        aliases: ["Dave's Office Lights", "David Office Lights"]
      climate.davids_office:
        aliases: ["Dave's Office Heating"]
      input_boolean.hot_water_boost:
        aliases: ["Hot Water", "Boost Hot Water"]
```

Rooms come from HA areas automatically. After deploying, call `google_assistant.request_sync` from Developer Tools > Actions.

If Google is *not* used: Settings > Home Assistant Cloud > Google Assistant > disable. No YAML.

### 7.4 Lighting: profiles in the engine, wrappers everywhere, merged pairs

Add three profiles to `lighting_apply_profile_core` (replace the `selected_profile` variable and the `choose` block):

```yaml
    - variables:
        selected_areas: "{{ target_areas | default([], true) }}"
        selected_profile: >-
          {% set p = (profile | default('evening') | string | lower) %}
          {{ p if p in ['day', 'morning', 'evening_full', 'evening', 'late', 'night'] else 'evening' }}
        selected_action: "{{ 'off' if (action | default('on') | string | lower) in ['off', 'false', '0'] else 'on' }}"
        selected_transition: "{{ transition | default(2) | int(2) }}"
        # Single table of profile defaults. Change numbers here, nowhere else.
        profile_table:
          day:          {brightness_pct: 100, color_temp_kelvin: 4000}
          morning:      {brightness_pct: 80,  color_temp_kelvin: 4000}
          evening_full: {brightness_pct: 100, color_temp_kelvin: 2700}
          evening:      {brightness_pct: 80,  color_temp_kelvin: 2700}
          late:         {brightness_pct: 15,  color_temp_kelvin: 2700}
          night:        {brightness_pct: 10,  color_temp_kelvin: 2000}
        chosen: "{{ profile_table[selected_profile] }}"
    - condition: template
      value_template: "{{ selected_areas | count > 0 }}"
    - choose:
        - conditions: "{{ selected_action == 'off' }}"
          sequence:
            - action: light.turn_off
              target:
                area_id: "{{ selected_areas }}"
              data:
                transition: "{{ selected_transition }}"
      default:
        - action: light.turn_on
          target:
            area_id: "{{ selected_areas }}"
          data:
            brightness_pct: "{{ chosen.brightness_pct }}"
            color_temp_kelvin: "{{ chosen.color_temp_kelvin }}"
            transition: "{{ selected_transition }}"
```

(`area_id` accepts a list, so the `repeat` loop is unnecessary.)

Add a wrapper for the evening set (common + lounge) so the sunset/late-evening automations stop repeating the list:

```yaml
lighting_evening_set:
  alias: Lighting Evening Set
  description: Common areas plus Lounge; the set used by all evening schedules.
  mode: restart
  fields:
    profile: {description: "profile name", example: "evening"}
    action: {description: "on or off", example: "on"}
    transition: {description: "seconds", example: 2}
  sequence:
    - action: script.lighting_apply_profile_core
      data:
        target_areas:
          - attic_lounge
          - dining_room
          - kitchen
          - hallway
          - landing
          - side_hall
          - living_room
        profile: "{{ profile | default('evening') }}"
        action: "{{ action | default('on') }}"
        transition: "{{ transition | default(2) }}"
```

Merged morning automation (replaces `_0620_presunrise` and `_0650_presunrise`):

```yaml
- id: lighting_common_morning_presunrise
  alias: Lighting - Common Areas On Pre-Sunrise (Mon-Thu 06:20, Fri 06:50)
  triggers:
    - trigger: time
      at: "06:20:00"
      id: mon_thu
    - trigger: time
      at: "06:50:00"
      id: fri
  conditions:
    - condition: state
      entity_id: input_boolean.lighting_automations_paused
      state: "off"
    - condition: sun
      before: sunrise
    - condition: or
      conditions:
        - condition: and
          conditions:
            - condition: trigger
              id: mon_thu
            - condition: time
              weekday: [mon, tue, wed, thu]
        - condition: and
          conditions:
            - condition: trigger
              id: fri
            - condition: time
              weekday: [fri]
  actions:
    - action: script.lighting_common_areas
      data: {profile: morning, action: "on", transition: 2}
  mode: single
```

Sunset-on with the summer fix (A3), using the elevation trigger from 7.6:

```yaml
- id: lighting_evening_set_on_at_dusk
  alias: Lighting - Evening Set On At Dusk
  description: Comes on when the sun drops below 4 degrees (roughly 15-45 min before sunset depending on season). Full brightness before 19:00, evening profile after.
  triggers:
    - trigger: numeric_state
      entity_id: sun.sun
      attribute: elevation
      below: 4
  conditions:
    - condition: state
      entity_id: input_boolean.lighting_automations_paused
      state: "off"
    - condition: state
      entity_id: sun.sun
      attribute: rising
      state: false
  actions:
    - action: script.lighting_evening_set
      data:
        profile: "{{ 'evening_full' if now().hour < 19 else 'evening' }}"
        action: "on"
        transition: 3
    - action: light.turn_on
      target: {entity_id: light.office_filament}
      data:
        brightness_pct: "{{ 100 if now().hour < 19 else 80 }}"
        color_temp_kelvin: 2700
        transition: 3
  mode: single
```

Merged late-evening off (replaces `_off_2300_sun_thu` and `_off_2359_fri_sat`):

```yaml
- id: lighting_evening_set_off_late
  alias: Lighting - Evening Set Off (Sun-Thu 23:00, Fri-Sat 23:59)
  triggers:
    - trigger: time
      at: "23:00:00"
      id: weeknight
    - trigger: time
      at: "23:59:00"
      id: weekend
  conditions:
    - condition: or
      conditions:
        - condition: and
          conditions:
            - {condition: trigger, id: weeknight}
            - {condition: time, weekday: [sun, mon, tue, wed, thu]}
        - condition: and
          conditions:
            - {condition: trigger, id: weekend}
            - {condition: time, weekday: [fri, sat]}
  actions:
    - action: script.lighting_evening_set
      data: {action: "off", transition: 3}
    - action: light.turn_off
      target: {entity_id: light.office_filament}
      data: {transition: 3}
  mode: single
```

### 7.5 Dim-only-if-on script (fixes A2, reused by 19:00 and 22:15/23:30)

```yaml
lighting_dim_if_on:
  alias: Lighting Dim If On
  description: Apply a profile only to lights in the given areas that are already on. Never turns anything on.
  mode: restart
  fields:
    target_areas: {description: "area ids", example: "living_room"}
    extra_entities: {description: "optional extra light entity ids", example: "light.office_filament"}
    profile: {description: "evening or late", example: "late"}
    transition: {description: "seconds", example: 3}
  sequence:
    - variables:
        table:
          evening: {brightness_pct: 80, color_temp_kelvin: 2700}
          late:    {brightness_pct: 15, color_temp_kelvin: 2700}
        chosen: "{{ table[profile | default('evening')] }}"
        on_lights: >-
          {% set ns = namespace(ids=[]) %}
          {% for a in (target_areas | default([], true)) %}
            {% set ns.ids = ns.ids + area_entities(a) %}
          {% endfor %}
          {% set ns.ids = ns.ids + (extra_entities | default([], true)) %}
          {{ expand(ns.ids) | selectattr('domain','eq','light') | selectattr('state','eq','on') | map(attribute='entity_id') | list }}
    - condition: template
      value_template: "{{ on_lights | count > 0 }}"
    - action: light.turn_on
      target:
        entity_id: "{{ on_lights }}"
      data:
        brightness_pct: "{{ chosen.brightness_pct }}"
        color_temp_kelvin: "{{ chosen.color_temp_kelvin }}"
        transition: "{{ transition | default(3) }}"
```

Merged late dim (replaces `_dim_2215_sun_thu` and `_dim_2330_fri_sat`):

```yaml
- id: lighting_evening_set_dim_late
  alias: Lighting - Evening Set Dim To 15% (Sun-Thu 22:15, Fri-Sat 23:30)
  triggers:
    - {trigger: time, at: "22:15:00", id: weeknight}
    - {trigger: time, at: "23:30:00", id: weekend}
  conditions:
    - condition: or
      conditions:
        - condition: and
          conditions:
            - {condition: trigger, id: weeknight}
            - {condition: time, weekday: [sun, mon, tue, wed, thu]}
        - condition: and
          conditions:
            - {condition: trigger, id: weekend}
            - {condition: time, weekday: [fri, sat]}
  actions:
    - action: script.lighting_dim_if_on
      data:
        target_areas: [attic_lounge, dining_room, kitchen, hallway, landing, side_hall, living_room]
        profile: late
        transition: 4
  mode: single
```

The 19:00 automation becomes a three-line call to the same script with `profile: evening` and `extra_entities: [light.office_filament]`.

### 7.6 Sun elevation instead of seasonal delays (fixes A4/R2)

Morning off (replaces `lighting_all_lights_off_after_sunrise_seasonal` and `lighting_front_porch_off_at_sunrise`):

```yaml
- id: lighting_common_off_after_sunrise
  alias: Lighting - Common + Porch Off After Sunrise
  description: Off once the sun is 6 degrees up (about 15 min after sunrise in June, 45 in December at this latitude). No delay, so a restart cannot lose it.
  triggers:
    - trigger: numeric_state
      entity_id: sun.sun
      attribute: elevation
      above: 6
  conditions:
    - condition: state
      entity_id: sun.sun
      attribute: rising
      state: true
  actions:
    - action: script.lighting_evening_set
      data: {action: "off", transition: 2}
    - action: script.lighting_outside
      data: {action: "off", transition: 2}
  mode: single
```

Tune `below: 4` / `above: 6` by watching `sun.sun` elevation on two or three evenings; then delete `script.lighting_wait_seasonal_offset`. The front porch sunset-on can use the same `below` trigger with a `rising: false` condition.

Front porch motion, pinned to the physical sensor:

```yaml
- id: lighting_front_porch_motion_overnight
  alias: Lighting - Front Porch Motion Overnight
  triggers:
    - trigger: state
      entity_id: binary_sensor.hue_outdoor_motion_sensor_1_motion
      to: "on"
  conditions:
    - condition: time
      after: "23:00:00"
      before: "06:20:00"
  actions:
    - action: light.turn_on
      target: {area_id: front_porch}
      data: {brightness_pct: 50, color_temp_kelvin: 2000, transition: 1}
    - wait_for_trigger:
        - trigger: state
          entity_id: binary_sensor.hue_outdoor_motion_sensor_1_motion
          to: "off"
          for: "00:03:00"
      timeout: "00:20:00"
      continue_on_timeout: true
    # If the 06:20 schedule has taken over meanwhile, leave it to that schedule.
    - condition: template
      value_template: "{{ now().strftime('%H:%M') < '06:20' or now().strftime('%H:%M') >= '23:00' }}"
    - action: script.lighting_outside
      data: {action: "off", transition: 2}
  mode: restart
```

### 7.7 Virtual devices that behave the same on every assistant

Hot water boost switch, mirrored both ways:

```yaml
- id: hot_water_boost_switch_on
  alias: Hot Water - Boost Switch On
  triggers:
    - trigger: state
      entity_id: input_boolean.hot_water_boost
      to: "on"
  actions:
    - action: script.tado_hot_water_boost
      data: {duration_minutes: 60}
  mode: single

- id: hot_water_boost_switch_off
  alias: Hot Water - Boost Switch Off
  triggers:
    - trigger: state
      entity_id: input_boolean.hot_water_boost
      to: "off"
  conditions:
    # Only act if Tado is actually in a manual/boost overlay; otherwise this is just the mirror resetting.
    - condition: state
      entity_id: binary_sensor.hot_water_overlay
      state: "on"
  actions:
    - action: script.tado_hot_water_auto
  mode: single

- id: hot_water_boost_switch_mirror
  alias: Hot Water - Mirror Tado Overlay Into Boost Switch
  description: Keeps the tile truthful when the boost is started or expires from the Tado app.
  triggers:
    - trigger: state
      entity_id: binary_sensor.hot_water_overlay
      to: ["on", "off"]
  actions:
    - action: "input_boolean.turn_{{ trigger.to_state.state }}"
      target: {entity_id: input_boolean.hot_water_boost}
  mode: queued
```

Goodnight momentary scene:

```yaml
- id: house_goodnight
  alias: House - Goodnight
  triggers:
    - trigger: state
      entity_id: input_boolean.goodnight
      to: "on"
  actions:
    - action: script.lighting_evening_set
      data: {action: "off", transition: 3}
    - action: script.lighting_outside
      data: {action: "off", transition: 2}
    - action: light.turn_off
      target: {entity_id: light.office_filament}
    - delay: "00:00:05"
    - action: input_boolean.turn_off
      target: {entity_id: input_boolean.goodnight}
  mode: single
```

Expose on HomeKit by adding to the Lights bridge (with explicit names so `customize` is not required for these):

```yaml
homekit:
  - name: HA Lights
    port: 21064
    filter:
      include_entities:
        - light.attic_lounge
        # ... existing list ...
        - input_boolean.hot_water_boost
        - input_boolean.goodnight
        - input_boolean.lighting_automations_paused
    entity_config:
      input_boolean.hot_water_boost: {name: Hot Water Boost}
      input_boolean.goodnight: {name: Goodnight}
      input_boolean.lighting_automations_paused: {name: Lighting Automations Paused}
```

Then add this condition to every scheduled lighting automation (not to the Goodnight one):

```yaml
    - condition: state
      entity_id: input_boolean.lighting_automations_paused
      state: "off"
```

### 7.8 Admin notification script and pump watchdog

```yaml
notify_admin:
  alias: Notify Admin
  description: Persistent notification plus push to David's iPhone. All health checks call this.
  mode: queued
  fields:
    notification_id: {description: "stable id so repeats replace, not stack", example: "system_backup_health"}
    title: {description: "title", example: "Backup stale"}
    message: {description: "body", example: "..."}
  sequence:
    - action: persistent_notification.create
      data:
        notification_id: "{{ notification_id }}"
        title: "{{ title }}"
        message: "{{ message }}"
    - action: notify.mobile_app_davids_iphone
      data:
        title: "{{ title }}"
        message: "{{ message }}"
        data:
          tag: "{{ notification_id }}"
```

```yaml
- id: hot_water_pump_watchdog
  alias: Hot Water - Pump Watchdog (alert only)
  triggers:
    - trigger: state
      entity_id: binary_sensor.hot_water_power
      to: "on"
      for: "00:02:00"
      id: no_pump
    - trigger: state
      entity_id: switch.hot_water_pump
      to: "on"
      for: "01:15:00"
      id: overrun
    - trigger: state
      entity_id: switch.hot_water_pump
      to: "unavailable"
      for: "00:10:00"
      id: offline
  conditions:
    - condition: or
      conditions:
        - condition: and
          conditions:
            - {condition: trigger, id: no_pump}
            - {condition: state, entity_id: switch.hot_water_pump, state: "off"}
        - {condition: trigger, id: overrun}
        - {condition: trigger, id: offline}
  actions:
    - action: script.notify_admin
      data:
        notification_id: hot_water_pump_watchdog
        title: Hot water pump check
        message: >-
          {{ trigger.id }}: Tado demand {{ states('binary_sensor.hot_water_power') }},
          pump {{ states('switch.hot_water_pump') }},
          timer {{ states('timer.hot_water_pump_runtime') }}.
  mode: queued
```

Also change `hot_water_pump_off_when_runtime_finishes` to:

```yaml
  triggers:
    - trigger: event
      event_type: [timer.finished, timer.cancelled]
      event_data:
        entity_id: timer.hot_water_pump_runtime
```

### 7.9 http, recorder

```yaml
# http: is NOT configurable in YAML on 2026.9 (storage-managed; YAML raises a repair).
# Set ip_ban_enabled / login_attempts_threshold in the UI HTTP settings instead.

recorder:
  purge_keep_days: 21
  commit_interval: 30
  exclude:
    entity_globs:
      - sensor.*_rssi
      - sensor.*_linkquality
      - sensor.*_signal_strength
      - sensor.*_last_seen
      - sensor.*_uptime
      - device_tracker.unifi_default_*
      - sensor.davids_iphone_*
      - sensor.ipad_*
      - event.dimmer_*
    entities:
      - sensor.sun_next_dawn
      - sensor.sun_next_dusk
      - sensor.sun_next_midnight
      - sensor.sun_next_noon
      - sensor.sun_next_rising
      - sensor.sun_next_setting
```

### 7.10 EV claim gate as template sensors

```yaml
template:
  - binary_sensor:
      - name: EV Renault Claims Charger
        unique_id: ev_renault_claims_charger
        state: >-
          {{ is_state('binary_sensor.renault_scenic_e_tech_plug', 'on')
             and is_state('device_tracker.renault_scenic_e_tech_location', 'home') }}
      - name: EV Honda Claims Charger
        unique_id: ev_honda_claims_charger
        # Stale Honda data is not a claim (2026-09-03 incident).
        state: >-
          {% set t = states('sensor.e_ny1_last_updated') | as_datetime %}
          {{ t is not none and (now() - t).total_seconds() < 1800
             and states('sensor.e_ny1_plug_status') in ['plugged_in', 'connected']
             and is_state('device_tracker.e_ny1_location', 'home') }}
  - sensor:
      - name: EV Car On Charger
        unique_id: ev_car_on_charger
        # The 60 s settle from the automations is expressed as a stable-for window in the
        # automations' triggers/conditions ("for: 00:01:00"), so this sensor is instantaneous.
        state: >-
          {% set r = is_state('binary_sensor.ev_renault_claims_charger', 'on') %}
          {% set h = is_state('binary_sensor.ev_honda_claims_charger', 'on') %}
          {% if states('sensor.ohme_home_pro_status') in ['unplugged', 'unavailable', 'unknown'] %}none
          {% elif r and not h %}renault
          {% elif h and not r %}honda
          {% else %}unresolved{% endif %}
```

The Renault approve automation then becomes:

```yaml
- id: ev_ohme_auto_approve_renault_charge
  alias: EV - Auto-Approve Ohme Charge for Renault
  triggers:
    - trigger: state
      entity_id: sensor.ev_car_on_charger
      to: renault
      for: "00:01:00"          # the settle window, now declarative
      id: identified
    - trigger: time_pattern
      minutes: "/5"
      id: retry_tick
  conditions:
    - condition: state
      entity_id: sensor.ohme_home_pro_status
      state: pending_approval
    - condition: state
      entity_id: sensor.ev_car_on_charger
      state: renault
      for: "00:01:00"
    - condition: not
      conditions:
        - condition: state
          entity_id: select.ohme_home_pro_charge_mode
          state: max_charge
  actions:
    - wait_template: >-
        {% set r = states('sensor.renault_scenic_e_tech_battery') | float(-1) %}
        {% set o = states('sensor.ohme_home_pro_vehicle_battery') | float(-2) %}
        {{ is_state('select.ohme_home_pro_vehicle', 'Renault Scenic (2023-2025)')
           and 0 <= r <= 100 and (r | round(0) | int) == (o | round(0) | int) }}
      timeout: "00:05:00"
      continue_on_timeout: true
    - condition: state
      entity_id: sensor.ohme_home_pro_status
      state: pending_approval
    - action: button.press
      target: {entity_id: button.ohme_home_pro_approve_charge}
  mode: single
  max_exceeded: silent
```

The Honda refresh press moves into a single small automation: when Ohme leaves `unplugged` (or every 15 min while `charging`/`pending_approval`), press `button.e_ny1_refresh_from_car` with `continue_on_error: true`. That keeps the freshness behaviour, drops the duplicated gate from four places to zero, and the Renault path no longer wakes the Honda on every retry. Keep the existing incident notes in the descriptions.

### 7.11 Presence

```yaml
# Create the persons in Settings > People (they are storage-backed), then:
template:
  - binary_sensor:
      - name: Anyone Home
        unique_id: anyone_home
        device_class: presence
        state: >-
          {{ expand('person.david_richards', 'person.sarah', 'person.ren', 'person.nathaniel')
             | selectattr('state', 'eq', 'home') | list | count > 0 }}
```

### 7.12 Appliance status through HA (Phase 0 decision)

What each assistant can actually do with appliance data:
- **Alexa and Google** accept temperature sensors (the two oven cavity temperatures, added to the lists above) and little else that is useful here. The Home Connect door sensors are enum `sensor` entities, not `binary_sensor`, so they cannot be contact sensors, and the "time remaining" template sensors are text. Do not try to push programme status through them; it will only produce "I don't know that one".
- **Assist** (Companion app, and any future voice satellite) can answer with any exposed sensor: "how long is left on the dishwasher?", "what is the dryer doing?". Expose these eight template sensors to Assist and give them spoken aliases:

```yaml
# Entity registry aliases (Settings > Voice assistants > Expose > entity > Aliases), not YAML:
#   sensor.dishwasher_time_remaining   -> "dishwasher", "dishwasher time left"
#   sensor.dishwasher_programme        -> "dishwasher programme"
#   sensor.dryer_time_remaining        -> "dryer", "tumble dryer", "dryer time left"
#   sensor.dryer_status                -> "dryer status"
#   sensor.left_oven_time_remaining    -> "left oven", "left oven time left"
#   sensor.right_oven_time_remaining   -> "right oven", "right oven time left"
#   sensor.left_oven_programme         -> "left oven programme"
#   sensor.right_oven_programme        -> "right oven programme"
```

- **Push notifications** are the reliable "status" channel. One automation covers all four appliances:

```yaml
- id: appliances_finished_notify
  alias: Appliances - Notify When A Programme Finishes
  triggers:
    - trigger: state
      entity_id: sensor.dishwasher_operation_state
      to: finished
      id: Dishwasher
    - trigger: state
      entity_id: sensor.left_oven_operation_state
      to: finished
      id: Left oven
    - trigger: state
      entity_id: sensor.right_oven_operation_state
      to: finished
      id: Right oven
    - trigger: state
      entity_id: sensor.dryer_current_status
      to: end          # LG ThinQ reports `end`; confirm the exact value in the dryer's history first
      id: Dryer
  actions:
    - action: script.notify_admin
      data:
        notification_id: "appliance_{{ trigger.id | slugify }}"
        title: "{{ trigger.id }} finished"
        message: "{{ trigger.id }} finished at {{ now().strftime('%H:%M') }}."
  mode: queued
```

Starting a programme by voice stays out of scope: Home Connect needs "remote start" armed on the appliance each time, and the LG dryer needs the same, so a voice command would fail more often than it works.

---

## 8. Final Recommended Architecture

```
                 ┌─────────────────────────────────────────────┐
                 │  Home Assistant (the brain)                  │
 Alexa ───────►  │  Tier-1 exposure list  ── Room Lights x12    │
 (Cloud, YAML)   │                        ── Room Heating x13   │
 Google ──────►  │                        ── Room AC x2         │
 (Cloud, YAML)   │                        ── Hot Water Boost    │
 HomeKit ─────►  │                        ── Goodnight          │
 (4 bridges)     │                        ── Automations Paused │
 Assist ──────►  │  (same list + Water Pump for admins)         │
                 │                                              │
                 │  Lighting engine: profile table → wrappers   │
                 │  → sun-elevation + clock automations         │
                 │  Hot water: Tado demand → pump + restore     │
                 │  timer; boost switch mirrors Tado overlay    │
                 │  EV: template claim sensors → 4 short        │
                 │  automations (approve x2, SoC x2)            │
                 │  Health: notify_admin → phone + persistent   │
                 └───────┬──────────┬──────────┬────────────────┘
                         │          │          │
                   Hue (LAN)   Tado (cloud) Meross (LAN) Tuya (cloud) Ohme/Renault/Honda (cloud)
```

Rules:
1. Names live in `customize:`. Aliases live in the registry and the Google block. Nothing else names anything.
2. Exposure lists are YAML for all three assistants and are the same list plus per-platform extras.
3. Voice assistants only ever touch Tier-1 devices. Any "do several things" request is a virtual switch that HA acts on.
4. Every scheduled lighting automation calls a wrapper with a profile and checks `lighting_automations_paused`.
5. No `delay` longer than a few seconds in a scheduled automation; use triggers (`for:`, elevation) or a `restore: true` timer.
6. Every alert goes through `script.notify_admin`.
7. Hue, Tado, Meross, Tuya native apps hold no schedules or motion rules (Tado's heating schedule is the documented exception).

File layout (optional packages move, keeps `configuration.yaml` a true include map):

```
/config/configuration.yaml        default_config, includes, packages: !include_dir_named packages
/config/packages/voice.yaml       customize (names), cloud, homekit
/config/packages/helpers.yaml     input_boolean, input_number, input_datetime, timer
/config/packages/templates.yaml   template sensors (appliances, gas register, EV claim, presence)
/config/packages/system.yaml      recorder, http, sql, shell_command, lovelace
/config/automations.yaml
/config/scripts.yaml
/config/dashboards/*.yaml
```

If you adopt it, add `packages/*.yaml` to `FILES` in `scripts/sync_from_ha.sh`.

---

## 9. Step-by-Step Improvement Plan

Each step: backup (HA backup slug), edit, `ha core check`, reload, `make verify`, change-log entry. Steps are ordered so each is independently reversible.

**Phase 0 - decisions (resolved 2026-09-15, no config change)**
- Google Home: **wanted, not yet integrated with HA.** Today the Google Home app links Philips Hue, Tuya/SmartLife/Meross and Home Connect/LG ThinQ directly to devices. Plan: deploy 7.3, sync, verify every HA device appears with the right room, then unlink those direct services (Phase 3V).
- Alexa skills linked: Home Assistant, Tuya, SmartLife, Meross, Home Connect, LG ThinQ, plus media skills (Apple Music/Podcasts, BBC, Plex, ITVX, Xbox) which are fine. **Hue and Tado are not linked**, which is the important one. The only voice use of the vendor skills is the two Meaco AC units and the kitchen Ecostrad heater, so those three climate entities join the HA Alexa list (7.1) before Tuya, SmartLife and Meross are unlinked. Home Connect and LG ThinQ are also unlinked; appliance status moves to HA (7.12).
- Apple Home: only the four HA bridges are paired. Nothing to remove. The Elgato light stays in the HA Lights bridge; fix its network reservation.
- Hue app: the two evening automations and the Attic motion rule are deleted. HA owns all lighting logic.
- Tado app: manual changes end at "next automatic change" in some rooms and on a timer in others. Both expire, so voice-set temperatures cannot become permanent. No change.
- Room rename: both Meaco AC units stay where they are, so the rename is names and areas only. Ren's personal Hue scenes (Disturbia, Galaxy, Singapore, Soho, Vapor wave) are deleted. The Google display from Ren's room moves to the **Dining Room**.

**Phase 1 - reliability (done 2026-09-15, see change log)**
1. [x] `timer.hot_water_pump_runtime: restore: true` (7.2). Reloaded and read back.
2. [x] `hot_water_pump_off_when_runtime_finishes` also on `timer.cancelled` (7.8).
3. [x] Disabled `sensor.e_ny1_climate_temperature`. The Renault re-auth, oven `units_changed` and HACS repairs had already cleared with an earlier restart; repairs list is empty. Renault still logs intermittent per-endpoint `unauthorized` errors while its data updates: watch, and complete the repair if it returns.
4. [ ] Hardware (hands-on): Meross "Hue Bridge Power" (192.168.1.251) and "Sarah's office lights" (192.168.1.37) are off the network entirely, not just unreachable by the integration; `light.guest_room_shelf_light` and `light.hue_filament_bulb_attic_2` unavailable in Hue; Elgato currently reachable, still give it a DHCP reservation.
5. [x] HTTP bans: **YAML is not the way in 2026.9.** HTTP settings live in `.storage/http` (migrated 2026-08-14); the YAML block only raised repair `yaml_still_present_after_migration` and was removed. The threshold was set to 10 in the UI (user's choice, with UniFi IPS/IDS as the second layer). Note for future changes: the UI applies HTTP settings as a pending trial with a 15-minute revert; `http/config/promote` over WebSocket makes it permanent. [ ] Gateway port-forward check still open.

**Phase 2 - hygiene (done 2026-09-15, see change log)**
6. [x] 14 orphaned registry entries deleted; `media_player.s95qr` and the Cast `media_player.lg_webos_tv` disabled; 8 Meross DND/overtemp entities disabled; `google_translate` and `met` config entries deleted.
7. [x] Assist exposure trimmed 192 -> 117 (Tier 1 + Tier 2 + the standard Hue room scenes + Tado room temperature/humidity/window sensors + the 8 appliance status sensors). Aliases added for Sarah's/David's office and Side Hall and the appliance sensors. [ ] Nathaniel's-room aliases after Phase 2R.
8. [x] `light.elgato_key_light_air` device moved to Sarah's Office (answered 2026-09-15). Apple Home room still needs dragging by hand.
9. [x] Alexa `entity_config` block deleted (names verified unchanged after restart); `light.lounge` registry name cleared; `frontend.themes` removed.
10. [x] Recorder exclusions applied. [ ] UniFi client tracking: **manual decision**.

Manual review items collected from Phases 1-2 (nothing here was changed):
- Elgato Key Light Air: area moved to Sarah's Office (done). Still give 192.168.1.112 a DHCP reservation on the UCG Fiber and drag it into Sarah's Office in Apple Home.
- UniFi integration options: decide whether to keep "track network clients" (86 device trackers). If yes, the recorder exclusion for the 14 unnamed `unifi_default_*` MACs is already in place; the named ones still record.
- Watchman reports 5 "missing" entities, all expected: the Ohme state-of-charge input (only exists while plugged in), both Meaco AC units (winter), and `sensor.octopus_energy_a_e86380df_wheel_of_fortune_spins_electricity` / `_gas` on the Utilities dashboard, which read `unknown`. Either add these to Watchman's ignore list or, for the wheel-of-fortune pair, check whether Octopus still provides them and drop the two dashboard rows if not.
- Meross plugs "Hue Bridge Power" (192.168.1.251) and "Sarah's office lights" (192.168.1.37) are off the network entirely; meross_lan logs MQTT timeouts for them at every startup.
- Hue: `light.guest_room_shelf_light` and `light.hue_filament_bulb_attic_2` unavailable (Guest Bedroom Lights is a dead accessory on every assistant until the first is fixed).
- UCG Fiber: no port-forward to 8123 confirmed by the project user 2026-09-15 (IPS/IDS on; login ban threshold 10). Closed.
- Renault: intermittent per-endpoint `unauthorized` errors while data keeps updating; complete the re-auth repair if it reappears.
- Companion app Assist spot-check: "how long is left on the dishwasher", "turn on Daves office lights"; confirm appliance and EV switches are no longer offered.

**Phase 2R - room rename (HA side done 2026-09-15, app side outstanding)**
R1. [ ] **You**: Tado app: rename zone "Nathaniel's Bedroom" to "Attic Bedroom" first, then "Ren's Bedroom" to "Nathaniel's Bedroom" (this also fixes the child lock / window / temperature entity names in HA). Hue app: rename room "Ren's Bedroom" to "Nathaniel's Bedroom", rename the "Dimmer Ren's room" dimmer, delete the scenes Disturbia, Galaxy, Singapore, Soho, Vapor wave.
R2. [x] Areas migrated: `attic_bedroom` created (3 devices), old `nathaniel_s_bedroom` deleted, "Nathaniel's Bedroom" recreated and reissued the id `nathaniel_s_bedroom` (9 devices), `ren_s_bedroom` deleted. Nest Hub moved to Dining Room.
R3. [x] `customize` names, `lighting_bedrooms` wrapper, core config/script/HomeKit reloads, `make verify`.
R4. [x] Docs updated (reference, HomeKit migration, lighting, change log).
R5. [ ] **You**: Apple Home: rename rooms (attic first), then check the four accessories show "Nathaniel's Bedroom Lights/Heating/AC" and "Attic Bedroom Heating/AC"; rename them by hand if iOS kept the old names; drag the Elgato light into Sarah's Office. Alexa: "Alexa, discover devices", then regroup. Google Home: rename the display to "Dining Room display" and the rooms (and delete the unavailable `media_player.google_speaker` in HA if it is the same device). Assist aliases are already in place. Test phrases in 10.6.

**Phase 3 - virtual devices (done 2026-09-15, see change log)**
11. [x] `input_boolean.hot_water_boost`, `goodnight`, `lighting_automations_paused` with their automations; paused condition on all 14 scheduled lighting automations; Alexa list += the two family switches; HA Lights bridge += all three; Assist += all three with aliases. `water_heater.hot_water` stays on Alexa/HomeKit for one more week. Google waits for Phase 3V.
12. [x] Ecostrad renamed "Kitchen Heating". If Apple Home kept "Kitchen Ecostrad Heater", rename the accessory by hand.
13. [x] Goodnight live-tested. [ ] **You**: test Hot Water Boost from a voice assistant when hot water is wanted (on -> Tado shows a 60-minute timer; off -> back to schedule; a boost started in the Tado app turns the switch on by itself). In Apple Home the three new switches appear under the HA Lights bridge; assign rooms (Hot Water Boost -> Utilities or Kitchen, Goodnight and Lighting Automations Paused -> wherever the household finds them). Create an Apple Home scene "Goodnight" that turns the Goodnight switch on if you want it in Siri's scene list.

**Phase 3V - voice cutover (HA side done 2026-09-15; app side outstanding)**
V1. [x] Alexa list deployed with Kitchen Heating, both AC units, the two oven temperatures, Hot Water Boost and Goodnight. [ ] **You**: "Alexa, discover devices"; check each new device appears once; then unlink Tuya, SmartLife, Meross, Home Connect and LG ThinQ under Skills and delete leftover duplicate devices.
V2. [x] Google: 31 entities exposed to `cloud.google_assistant` through the exposed-entities API (see the correction below; the YAML block in 7.3 is NOT valid on 2026.9 and briefly took the cloud integration down). [ ] **You**: in the Google Home app link "Home Assistant Cloud by Nabu Casa" under Works with Google (it has never been linked), let the devices sync, assign rooms (HA areas are sent as room hints), then unlink Philips Hue, Tuya/SmartLife, Meross, Home Connect and LG ThinQ and remove orphaned devices.
V3. [ ] **You**: retest the phrase list at the end of section 9 on Alexa, Google and Siri.

**Kitchen Heating (learned 2026-09-15)**: the Ecostrad's Tuya spec mis-declares its `mode` enum and the Tuya cloud refuses mode writes, which made HA report the thermostat as `unknown` whenever it was on. Fixed with a local quirk (`/config/tuya_quirks/qn_lgibckbiszegmjlo.py`, tracked in the repo) that removes the mode datapoint so HA derives heat/off from the switch. [ ] **You**: put the heater in COMFORT mode in the Tuya/Smart Life app (it is in frost mode now) and leave it there; HA and the assistants then handle on/off and the temperature. The Meaco AC units need no quirk (their spec is consistent: switch, target 16-32 C, current temperature, fault bitmap; no fan/mode datapoints are advertised, so HA shows off/cool only).

**Correction to 7.3 (learned 2026-09-15)**: Home Assistant 2026.9 rejects `cloud: google_assistant:` in YAML ("invalid option for cloud") and `ha core check` does not catch it. Google exposure for HA Cloud is managed in Settings > Voice assistants > Expose (or via `homeassistant/expose_entity` for `cloud.google_assistant`), and aliases live in the entity registry, which Google reads. Alexa YAML filtering still works. The 7.3 block is kept only as the list of what to expose.

**Phase 4 - lighting refactor (done 2026-09-15, see change log)**
14. [x] Profile table in the core script; `lighting_evening_set` and `lighting_dim_if_on` added; wrappers use `action:`.
15. [x] 15 lighting automations -> 12: merged pairs with trigger ids, `dim_if_on` for both dims, wrappers with profile names everywhere, porch motion pinned to the physical sensor. Orphaned registry entries removed.
16. [x] Elevation triggers replaced the seasonal delays in one step (below 4 dusk / above 5 dawn) rather than running both for three days: the seasonal script's numbers translate to roughly the same elevations, and the delay-based version could not coexist cleanly. `lighting_wait_seasonal_offset` is kept, uncalled, until 2026-09-22. [ ] **You**: watch the next two or three dusks and dawns and say if the timing feels early or late; the two numbers are in the automations.
17. [x] `docs/lighting_reusable_components.md` rewritten.
First dusk under the new trigger: fired 18:49 BST at elevation 3.7 (sunset 19:20), all evening-set lights on at 100%. The Hue smart plug `light.battery_charger` (Lounge, light domain) was being switched with the room by both old and new schedules; its device now sits in the Utilities area so area targeting skips it.

**Phase 5 - EV simplification (1 hour, watch two real plug-ins)**
18. Add the template claim sensors (7.10). Watch them for a day against the existing automations (they should agree).
19. Replace the four automations with the short forms; keep the descriptions' incident history. Validate on the next real plug-in of each car.

**Phase 6 - presence and health (optional)**
20. Persons for Sarah/Nathaniel (and Ren for visits), `binary_sensor.anyone_home`; add the condition to the dusk automation only.
21. `script.notify_admin` and the pump watchdog (7.8); route the five existing health checks through it.
22. Voice-exposure dashboard (plan item 10) generated from the same YAML lists so drift is visible.

**Testing checklist per assistant after each phase**
- Alexa: "turn on/off <room> lights", "dim <room> lights to 30", "set <room> heating to 20", "turn on hot water boost", "turn on goodnight". Check the Alexa app device list has exactly 27 devices (after Phase 3) and no duplicates.
- Google (if enabled): same phrases; "sync my devices"; check rooms in the Google Home app.
- HomeKit: each accessory responds within 2 s; no "No Response" except the AC units in winter; Goodnight scene in Apple Home toggles the switch and lights go off.
- Assist (Companion app): "what's the temperature in the lounge", "turn off the dining room lights"; confirm nothing appliance- or EV-related is offered.

**Maintenance**
- `make verify` before every session; `make sync-ha` after every change.
- Quarterly: re-run the unavailable-entity filter, Watchman report, and the repairs list.
- Any new device: assign an area, decide its tier, add to the YAML lists (or not), update `customize`, then pair/sync.

---

## 10. Room Rename: Ren's Bedroom becomes Nathaniel's Bedroom, Nathaniel's Bedroom becomes Attic Bedroom

Added 2026-09-15 after the main audit. Ren has moved out to university. Nathaniel takes over Ren's first-floor room, and the attic room he leaves becomes a spare room called "Attic Bedroom".

### 10.1 Principles

1. **Entity ids do not change.** `light.ren_s_bedroom` stays `light.ren_s_bedroom`. Changing the entity id of a bridged entity makes HomeKit create a new accessory (room assignment and Apple Home scenes for it are lost) and makes Alexa create a new device (old one must be deleted from the app, groups rebuilt). Names and areas are what people see; ids are plumbing. Record the mapping in the reference doc and in a YAML comment so nobody is surprised later.
2. **Area ids are fixed properly**, not just renamed, because area ids are your primary targeting mechanism (`lighting_bedrooms`, the reference doc's area map, every future automation). A names-only rename would leave `area_id: nathaniel_s_bedroom` pointing at the attic forever. There is precedent: the 2026-02-22 "Migrate Ren area ID typo" change did exactly this kind of move.
3. **Order matters.** Rename the attic room first everywhere (Tado, HA, Apple Home), then Ren's room, so no system ever holds two rooms called "Nathaniel's Bedroom" at once.
4. **Rename before exposing anything new.** This is why it is Phase 2R, ahead of the virtual devices in Phase 3.

### 10.2 Inventory of what carries each room's name

Ren's Bedroom today (area id `ren_s_bedroom`, First floor) - becomes **Nathaniel's Bedroom**:

| Entity | Source of the name | Exposed to | Action |
|---|---|---|---|
| `light.ren_s_bedroom` (Hue room group) | `customize` "Ren's Bedroom Lights" (Hue room name underneath) | Alexa, HomeKit Lights, Assist | customize -> "Nathaniel's Bedroom Lights"; rename Hue room in the Hue app |
| `light.rens_bedroom_lamp_1`, `_lamp_2`, `light.lava_lamp` | Hue app | Assist only | Optional rename in Hue app; move area |
| `climate.ren_s_bedroom` (Tado zone) | `customize` "Ren's Bedroom Heating" | Alexa, HomeKit Climate, Assist | customize -> "Nathaniel's Bedroom Heating"; rename zone in the Tado app |
| `switch.ren_s_bedroom_child_lock`, `binary_sensor.ren_s_bedroom_window`, `sensor.ren_s_bedroom_temperature`/`_humidity`, `select.ren_s_bedroom_ren_s_bedroom_heating_circuit` | Tado zone name | Assist (child lock, window, temp) | Follow the Tado zone rename automatically; move area |
| `climate.meacocool_mc_series_12000_pro_2` (Meaco AC) | `customize` "Ren's Bedroom AC" | HomeKit AC | customize -> "Nathaniel's Bedroom AC" (assumes the unit stays in the room) |
| `scene.ren_s_bedroom_*` (12 Hue scenes: Concentrate, Disturbia, Energise, Galaxy, Nightlight, Read, Relax, Singapore, Soho, Vapor wave, ...) | Hue room + scene name | Assist | Names follow the Hue room rename. Delete the personal ones (Disturbia, Galaxy, Singapore, Soho, Vapor wave) in the Hue app unless Nathaniel wants them; that also trims Assist exposure |
| `media_player.ren_s_bedroom_display` (Cast) | Google Home app device name | Assist | Moves to the Dining Room (Phase 0). Rename to "Dining Room display" in the Google Home app, set the HA area to Dining Room. `media_player.google_speaker` is already an *unavailable* Cast entity in the Dining Room; if it is a stale entry for this or an older device, delete it |
| `event.dimmer_rens_room_button_1..4`, `sensor.dimmer_rens_room_battery` | Hue dimmer name "Dimmer Rens room" | none | Rename the dimmer in the Hue app |
| `device_tracker.ren` (Tado), `device_tracker.rens_iphone`, `device_tracker.rens_pc`, `device_tracker.macbook_air` ("Rens-Air") | Tado / UniFi | none | Leave. Ren's devices will appear on the network only during visits |

Nathaniel's Bedroom today (area id `nathaniel_s_bedroom`, Attic floor) - becomes **Attic Bedroom**:

| Entity | Source of the name | Exposed to | Action |
|---|---|---|---|
| `climate.nathaniels_bedroom` (Tado zone) | `customize` "Nathaniel's Bedroom Heating" | Alexa, HomeKit Climate, Assist | customize -> "Attic Bedroom Heating"; rename zone in the Tado app **first** |
| `switch.nathaniels_bedroom_child_lock`, `binary_sensor.nathaniels_bedroom_window`, `sensor.nathaniels_bedroom_temperature`/`_humidity`, `select.nathaniel_s_bedroom_nathaniels_bedroom_heating_circuit` | Tado zone name | Assist (child lock, window, temp) | Follow the Tado rename; move area |
| `climate.nathaniel_meacocool_mc_series_12000_pro` (Meaco AC) | `customize` "Nathaniel's Bedroom AC" | HomeKit AC | customize -> "Attic Bedroom AC" (assumes the unit stays in the attic) |
| No light entities | - | - | The attic bedroom has no Hue room in HA today, so it has no voice-controllable lighting. If it gets bulbs later, create the Hue room as "Attic Bedroom" and add `light.attic_bedroom` to the lists |
| `device_tracker.nathaniel_s_iphone`, `device_tracker.nathaniel_s_pc` (UniFi) | UniFi | none | Leave; used by `person.nathaniel` in Phase 6 |

If the AC unit that is physically in the attic moves downstairs with Nathaniel, do not rename the climate entities; instead swap the two Tuya devices' areas and keep each entity's customize name tied to the *room it is in*. Decide this in Phase 0.

### 10.3 Area migration (UI, in this order)

1. Settings > Areas: create **Attic Bedroom** (id will be `attic_bedroom`), floor Attic.
2. Open the old **Nathaniel's Bedroom** area. Move every device to Attic Bedroom: the Tado zone device, the Meaco AC device, and anything else listed. Check entities that carry their own area override (the entity's own settings dialog) as well as devices.
3. Delete the old Nathaniel's Bedroom area (`nathaniel_s_bedroom`). HA refuses if anything is still assigned, which is the safety net.
4. Create **Nathaniel's Bedroom**, floor First floor. Because the old id was freed in step 3, HA assigns `nathaniel_s_bedroom` again. Confirm in `.storage/core.area_registry` or Developer Tools > Template with `{{ area_id("Nathaniel's Bedroom") }}`.
5. Open **Ren's Bedroom**, move every device and entity to Nathaniel's Bedroom: Hue room group `light.ren_s_bedroom`, the three bulbs, the dimmer, the Tado zone device, the Meaco AC device, the Cast display.
6. Delete Ren's Bedroom (`ren_s_bedroom`).
7. Check with `{{ area_entities('nathaniel_s_bedroom') }}` and `{{ area_entities('attic_bedroom') }}` in Developer Tools > Template that both lists look right and that `{{ area_entities('ren_s_bedroom') }}` is empty.

Result: area ids `nathaniel_s_bedroom` (first floor) and `attic_bedroom` (attic) mean what they say. Entity ids keep their history.

### 10.4 YAML changes

`configuration.yaml` `customize:` - the five names in 7.1 (already updated there). If the Alexa `entity_config` block has not yet been deleted (Phase 2 step 9), update the same four `climate`/`light` names in it too, or delete it now.

`scripts.yaml` `lighting_bedrooms` wrapper:

```yaml
lighting_bedrooms:
  alias: Lighting Bedrooms
  description: Wrapper for bedrooms excluding Guest Bedroom (Main, Nathaniel's, Attic).
  mode: restart
  fields:
    profile: {description: "day, evening, or night.", example: "night"}
    action: {description: "on or off.", example: "on"}
    transition: {description: "Transition time in seconds.", example: 2}
  sequence:
    - action: script.lighting_apply_profile_core
      data:
        target_areas:
          - bedroom              # Main Bedroom
          - nathaniel_s_bedroom  # first floor, formerly Ren's Bedroom
          - attic_bedroom        # attic, formerly Nathaniel's Bedroom
        profile: "{{ profile | default('evening') }}"
        action: "{{ action | default('on') }}"
        transition: "{{ transition | default(2) }}"
```

No automation references either area id today (bedrooms are deliberately excluded from the blanket schedules), so nothing else in `automations.yaml` changes.

`homekit:` bridges: no change to the include lists (entity ids are unchanged). Reload the four HomeKit entries after the customize change so the accessories advertise the new names.

### 10.5 Documentation changes (same commit)

- `docs/homeassistant_configuration_reference.md`: Area ID Reference -> `nathaniel_s_bedroom -> Nathaniel's Bedroom (first floor; formerly Ren's Bedroom)`, `attic_bedroom -> Attic Bedroom (formerly Nathaniel's Bedroom)`, remove `ren_s_bedroom`. Update the HomeKit Bridge Export Reference and Alexa Exposure Reference name lists. Add an "Entity id history" note: `*ren_s_bedroom*` entities = Nathaniel's Bedroom, `*nathaniels_bedroom*` / `nathaniel_meacocool*` = Attic Bedroom.
- `docs/homekit_bridge_migration.md`: the Light and Climate bridge entity lists and the AC list carry the arrow names; update the right-hand names only.
- `docs/lighting_reusable_components.md`: Bedrooms membership -> `bedroom`, `nathaniel_s_bedroom`, `attic_bedroom`.
- `docs/change_log.md`: one entry covering the Tado/Hue app renames, area migration, YAML edits, HomeKit reload, Alexa re-discovery, rollback (restore `configuration.yaml`/`scripts.yaml` backups; areas can be recreated by hand).
- `CLAUDE.md` does not name the rooms; no change.

### 10.6 Assistant-side work and tests

Apple Home (names given at pairing are cached by iOS, so these are manual):
- Rooms: rename "Nathaniel's Bedroom" to "Attic Bedroom" first, then "Ren's Bedroom" to "Nathaniel's Bedroom".
- Accessories: after the HomeKit reload, check whether the four accessories (two Heating, one Lights, two AC) picked up the new names; if not, rename them in the accessory settings to match `customize` exactly.
- Siri tests: "turn on Nathaniel's bedroom lights", "set Nathaniel's bedroom heating to 19", "set the attic bedroom heating to 16", "turn off the lights in Nathaniel's bedroom".

Alexa:
- Say "Alexa, discover devices" (or Devices > Discover in the app). HA reports the new friendly names and Alexa updates the existing devices in place because the entity ids are unchanged.
- Move the devices between Alexa groups: put the Echo that lives in the room, "Nathaniel's Bedroom Lights" and "Nathaniel's Bedroom Heating" into a group named "Nathaniel's Bedroom"; put "Attic Bedroom Heating" into an "Attic Bedroom" group.
- Tests: "Alexa, turn on Nathaniel's bedroom lights", "Alexa, set attic bedroom heating to 16", and from the room's Echo just "Alexa, turn off the lights".

Google Home (only if enabled in Phase 0): rename the rooms in the Google Home app, run `google_assistant.request_sync`, then "Hey Google, sync my devices". The aliases in 7.3 already use the new names.

Assist: after Phase 2 step 7, aliases for `light.ren_s_bedroom` and `climate.ren_s_bedroom` should be "Nathaniels bedroom lights" / "Nathaniels bedroom heating" (no apostrophe variant helps typed queries).

### 10.7 Rollback

Names: revert `customize` and reload HomeKit / re-discover Alexa. Areas: the migration is reversible by repeating 10.3 with the names swapped back; entity ids never changed, so nothing downstream breaks. Tado and Hue app names are renamed back by hand.
