# Outstanding Home Assistant Review Steps

Created: 2026-05-24

These items remain after implementing the Home Assistant reliability fixes in commit `581a02e`.

## Remaining Actions

- Manually test the hot-water pump flow: Tado demand starts the pump, `timer.hot_water_pump_runtime` starts, and timer finish turns the pump off.
- Fix the Anglian Water integration authentication. Recent logs show an expired refresh token and setup failure.
- Check the Apple TV integration if still used. Earlier logs showed repeated connection failures to `192.168.1.50:7000`.
- Optionally add labels such as `common_lighting`, `admin_control`, `appliance_status`, and `voice_exposed` for future organization.

## Notes

- Home Assistant remote access is intended to be through Home Assistant Cloud only.
- Home Assistant automatic backups are configured for both local Supervisor storage and Home Assistant Cloud (`hassio.local`, `cloud.cloud`); last confirmed completed automatic backup was `2026-05-27T04:54:15+01:00`.
- Recorder retention is now YAML-managed with a 21-day purge window and exclusions for common diagnostic signal/uptime sensors.
- The water pump entity has been renamed to `switch.hot_water_pump`; YAML should use that canonical entity ID.
- Terminal & SSH is currently acceptable for admin use: key configured, password empty, and TCP forwarding disabled.
