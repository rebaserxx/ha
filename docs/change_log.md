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
