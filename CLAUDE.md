# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

This is **not an application codebase** — it is an operational/config repository for managing a live Home Assistant (HA) installation. It holds:
- Source-controlled snapshots of the live HA YAML config (`snapshots/homeassistant/`)
- Markdown runbooks/policy docs that define how config changes should be planned, made, and recorded (`docs/`)
- A sync/verify script and Makefile that diff this repo against the live server over SSH

There is no application build, lint, or test suite. "Correctness" here means: the tracked snapshots match the live server, and HA itself validates the config (`ha core check`, run on the live server, not in this repo).

## Commands

```bash
make sync-ha   # pull configuration.yaml, automations.yaml, scripts.yaml, scenes.yaml,
               # dashboards/appliances.yaml, and ha core/info text from the live server
               # into snapshots/homeassistant/, overwriting local snapshots
make verify    # fetch the same files live and diff against snapshots/homeassistant/;
               # exits non-zero if there is drift
```

Both call `scripts/sync_from_ha.sh` (`sync` / `verify` subcommands) which SSHes to the HA host. Overridable via env vars: `HA_HOST` (default `root@192.168.1.191`), `HA_CONFIG_DIR` (default `/homeassistant`), `SNAPSHOT_DIR` (default `snapshots/homeassistant`).

`make verify` should be run before answering drift/audit questions and before committing repo updates, per `docs/codex_change_playbook.md`.

## Working model for making HA config changes

This repo assumes changes flow: **live HA server ⇄ this repo**, with the repo as source of truth for review/history and the actual HA host (`192.168.1.191`, config root `/config`) as the runtime. Full rules live in `HOMEASSISTANT_CODEX_COMMUNICATION.md` and `docs/codex_change_playbook.md` — read both before making a live change. Key points:

- **Integration priority**: MCP tools first, then HA REST/WebSocket API, then SSH as a last resort for file-level or diagnostic work.
- **Standard workflow**: read current state → apply the smallest possible change → read back and verify → report exactly what changed and what was verified.
- **Backup lifecycle**: before any file-level `/config/*.yaml` or `.storage/*` mutation, create a recoverable backup (HA backup slug preferred, or a `.bak.<epoch>` file copy). Log backup details and rollback steps in `docs/change_log.md`. Never delete a same-session backup before validation succeeds; ad-hoc `.bak.*` files older than 7 days can be cleaned up, but deletions must be explicit and logged.
- **Validation after any YAML edit**: run `ha core check` on the live server, then reload/restart the affected component, then `make verify` from this repo.
- **Change log requirement**: every HA config change (or an explicit "no config change" note) gets an entry in `docs/change_log.md` — date, summary, files changed, validation status, rollback notes. This file is large (2000+ lines) and append-only; add new entries rather than rewriting history.
- Never print `HOMEASSISTANT_TOKEN` or other secrets in output; rotate immediately if one leaks into chat/logs.

## Config architecture (live HA server)

Reference doc: `docs/homeassistant_configuration_reference.md` (authoritative, updated after each verified change). Highlights:

- `configuration.yaml` is a root include map that *also* inlines several concerns directly (HomeKit customize names, Alexa cloud exposure list, recorder retention/exclusions, HomeKit bridge definitions, helper entities) — it is not purely a thin includes file, so check it directly rather than assuming logic lives only in the included files.
- `automation: !include automations.yaml`, `script: !include scripts.yaml`, `scene: !include scenes.yaml` are the three main includes.
- Three YAML-managed Lovelace dashboards under `/config/dashboards/`: `home_health.yaml`, `utilities.yaml`, `appliances.yaml` (admin-only; family-facing control happens through Alexa/HomeKit, not the HA UI).
- Four YAML-managed HomeKit bridges (`HA Lights` :21064, `HA Climate` :21065, `HA Air Conditioning` :21066, `HA Kitchen Heating` :21067) with explicit per-bridge include entity lists — see `docs/homekit_bridge_migration.md` for rollout/validation and the reference doc for the current canonical entity lists.
- Area IDs are the preferred targeting mechanism (`target.area_id`) over hardcoded entity lists, unless explicit entity pinning is required. The area ID → room name map is in the reference doc.

### Lighting subsystem (most actively developed area)

Full spec: `docs/lighting_reusable_components.md`. Architecture is a core engine + thin wrappers, all in `scripts.yaml`/`automations.yaml`:

- `script.lighting_apply_profile_core` — generic engine (`mode: restart`) taking `target_areas`, `profile` (`day`/`evening`/`night`), `action` (`on`/`off`), `transition`. Profile brightness/color-temp defaults live here.
- `script.lighting_common_areas`, `script.lighting_bedrooms`, `script.lighting_outside` — wrappers that call the core script with fixed `target_areas`; this is where area-set membership changes go.
- `script.lighting_wait_seasonal_offset` — shared seasonal pre/post sunrise-sunset delay logic (summer/shoulder/winter minute offsets), called by automations rather than duplicated per-automation.
- Automations compose these scripts on a schedule (sunset-on, 02:00 shutdown, weekday/Friday pre-sunrise, 19:00 evening dim, sunrise-off, late-evening dim/off splits, front porch schedule). Bedrooms and task/filament lights are intentionally excluded from several of the blanket on/off automations — check the "intentionally not forced off" notes before changing scope.
- Constraint: automation entries need `id`; **script entries in `scripts.yaml` must not have `id`** (HA rejects it).
- Change guide (which file/section to edit for profile defaults vs. area membership vs. timing) is in the "Change Guide" section of that doc — follow it rather than guessing where a lighting change belongs.

### Other live automations of note

- Tado gas meter sync (`tado_gas_meter_reading_weekly_from_octopus`) checks daily at 18:00 and submits at most weekly. It derives the cumulative register from Octopus's backfilled long-term *statistics*, not the daily-usage sensors: SQL sensor `sensor.octopus_gas_statistics_total` + `input_number.tado_gas_meter_baseline_m3` -> template sensor `sensor.tado_gas_meter_register_derived`, submitted as an integer dated at the statistics horizon (so late-arriving DCC data is tolerated). State is carried in `input_number.tado_gas_meter_last_submitted_m3` / `input_datetime.tado_gas_meter_last_submission_date`; `tado_gas_meter_submission_overdue_alert` (19:00) warns after 10 days without a submission. Manual correction via `script.tado_gas_set_manual_baseline`. Full detail in `docs/homeassistant_configuration_reference.md`.
- EV charge auto-approval — one automation per car, `ev_ohme_auto_approve_renault_charge` and `ev_ohme_auto_approve_honda_charge` (added 2026-09-01) — presses `button.ohme_home_pro_approve_charge` when that car is plugged in at home, so sessions do not wait for a tap in the app. **These two are the only EV automations permitted to cause charging; never add a charge-causing action anywhere else.** Approval grants permission, not power: Ohme/Intelligent Octopus Go still schedule the slot, and IOG pays the off-peak rate including on daytime dispatches - provided the charger is not in `max_charge`, which the automation explicitly refuses to approve. Note `select.ohme_home_pro_charge_mode` is `unavailable` during `pending_approval`, so that guard is written as a negation, not as a `smart_charge` requirement. Never add charge-causing actions to the state-of-charge sync below.
- Renault state-of-charge sync to Ohme (`ev_ohme_sync_renault_state_of_charge`) pushes the Renault's battery percentage into `number.utilities_ohme_home_pro_state_of_charge_input` while it is plugged in at home, because Ohme has disabled its own Renault integration. That number maps to `PUT /v1/car/{id}/state-of-charge` and touches no session endpoint, so it cannot start, approve or resume a charge - Intelligent Octopus Go keeps control of timing. The charger is shared with a Honda e:Ny1, so the automation identifies the Renault via its own plug + location sensors and selects it in Ohme first (Ohme applies state-of-charge to the selected vehicle). Do not extend it to `charge_mode`, `approve_charge` or `target_percentage`. See item 12 in `docs/dashboard_automation_plan.md`.
- Honda e:Ny1 equivalents (`ev_ohme_sync_honda_state_of_charge`, `ev_ohme_auto_approve_honda_charge`, added 2026-09-01) mirror the Renault pair for the second car on the shared charger, with three deliberate differences. (1) **Freshness gating**: Honda cloud data can be many hours stale, so both automations press `button.e_ny1_refresh_from_car` and require `sensor.e_ny1_last_updated` to be within 5 minutes before trusting any Honda reading, aborting on a 2-minute timeout rather than acting on a stale value. (2) **The Renault wins ties**: both Honda automations stand down while the Renault reports plugged in at home. The Renault automations deliberately have no reciprocal Honda guard — adding one would let stale Honda data block known-good Renault behaviour. (3) A 15-minute `time_pattern` tick forces a Honda refresh mid-charge, gated on the Honda already being the selected vehicle and Ohme being `charging`, because the Honda does not stream updates the way the Renault does. Identification uses `device_tracker.e_ny1_location` (GPS), not `sensor.e_ny1_home_away` — those two disagree.
- Hot water pump is driven by Tado demand + `timer.hot_water_pump_runtime`; manual/physical starts get a 30-minute auto-off safety net that backs off while `binary_sensor.hot_water_power` is on.
- Octopus gas rollover health check (`octopus_energy_gas_rollover_health_daily_check`) and HA Watchman / backup-staleness alerts are admin health checks — see `docs/dashboard_automation_plan.md` for the staged plan and status of these (each item lists purpose, status, files touched, and review focus).

## Conventions when proposing/making changes

- Automation IDs: `snake_case`, prefixed by subsystem (`lighting_*`, `hot_water_*`, `tado_*`, and per `docs/dashboard_automation_plan.md`'s newer convention: `system_*`, `heating_*`, `ev_*`, `network_*`).
- Reuse existing scripts/wrappers before adding new duplicated logic; add a new wrapper before copy-pasting core logic.
- Prefer alert-only automations over automatic corrective actions unless explicitly asked; avoid notification spam by using daily/delayed checks for non-urgent issues.
- When a request conflicts with `docs/lighting_reusable_components.md`'s documented contract, either update that doc in the same change or explicitly state why it's unchanged.
- `docs/outstanding_homeassistant_review_steps.md` tracks open manual review items — check it for pending human follow-ups before assuming an area is fully closed out.
