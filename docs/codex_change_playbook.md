# Codex Change Playbook (Home Assistant)

Use this file as the default workflow for making future HA config changes through Codex.

## How To Request A Change
Use this format:

```md
Goal:
Scope:
In scope:
Out of scope:
Target files:
Constraints:
Validation required:
```

## Good Request Examples

### Example 1: Adjust dusk timing
Goal: Move common area evening lights to exactly sunset.
Scope: Existing dusk automation only.
In scope: Update trigger offset.
Out of scope: Profile changes.
Target files: `/config/automations.yaml`
Validation required: `ha core check`

### Example 2: Add a new room to common areas
Goal: Include Attic Lounge in common area lighting.
Scope: Common wrapper script.
In scope: Add one `area_id`.
Out of scope: New automation schedules.
Target files: `/config/scripts.yaml`
Validation required: `ha core check` + manual run of wrapper script.

## Implementation Policy
1. Reuse existing scripts first.
2. Add wrappers before adding new duplicated logic.
3. Keep naming stable and explicit:
   - Automation IDs in snake_case
   - Script names scoped by purpose
4. Prefer area-based targeting unless you explicitly request entity-based targeting.

## Validation Policy
After any change, Codex should:
1. Read back changed YAML sections.
2. Run `ha core check`.
3. Report exactly what changed.
4. Report any step it could not perform (for example, reload limitations).

## Backup Lifecycle Policy
When making file-level HA edits (especially `/config/*.yaml` or `/config/.storage/*`):
1. Create a recoverable backup before mutation:
   - preferred: Home Assistant backup slug
   - optional: file copy with suffix `.bak.<epoch>`
2. Record backup details in `docs/change_log.md`:
   - backup slug and/or exact backup filenames
   - rollback sequence
3. Retention for ad-hoc `.bak.*` files:
   - keep the most recent backup set per edited file
   - remove backups older than 7 days after validation is complete
4. Cleanup must be explicit and logged:
   - list deleted backup files in `docs/change_log.md`
   - never delete backups created in the same session before validation succeeds

## Drift Verification Policy
Use repo tooling to keep docs and snapshots aligned with the server:
1. `make sync-ha` after approved server-side config changes.
2. `make verify` before review/audit responses and before pushing repo updates.
3. If drift exists:
   - either sync snapshots as part of the change, or
   - explain why drift is intentional and leave a note in `docs/change_log.md`.

## Current Lighting Feature Contract
Reference: `docs/lighting_reusable_components.md`

If a request conflicts with that contract, Codex should either:
- update the contract doc as part of the same change, or
- explicitly state why the contract is unchanged.

## Optional Request Template For Multi-Feature Changes
```md
Feature:
Business rule:
Trigger:
Targets:
Default behavior:
Exceptions:
Rollback plan:
```
