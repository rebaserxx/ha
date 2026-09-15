"""Quirk for the Ecostrad Klasse iQ electric heater (product_id lgibckbiszegmjlo).

Two defects, both verified on 2026-09-15 (Home Assistant 2026.9.2, tuya-device-handlers 0.0.27):

1. Tuya's cloud specification declares the ``mode`` datapoint (dpid 4) with the enum
   range ["eco"] only, while the heater actually reports "comfort", "eco" and "frost".
   Extending the range with add_dpid_enum made the presets readable, but the Tuya
   sharing API still REJECTS any write of "comfort" or "frost" (ApiRequestException
   2008, "value not supported"), so Home Assistant cannot change the mode at all.

2. The library's DefaultHVACModeWrapper claims any ``mode`` enum datapoint even when
   none of its values are HVAC modes, and HA's climate.hvac_mode then maps the value
   through a fixed table. "comfort"/"frost" are not in it, so whenever the switch is
   on the entity reports hvac state ``unknown``. Alexa, Google Home and HomeKit treat
   an unknown thermostat as broken.

Since the mode can only be read, never written, the datapoint is removed here. Home
Assistant then derives hvac mode from the ``switch`` datapoint (off/heat) and exposes
the target temperature, which is everything the voice assistants need.

Operational rule: the heater must be left in COMFORT mode (set once in the Tuya /
Smart Life app or on the unit). In frost mode "heat" only holds the anti-frost
temperature and Home Assistant cannot tell.

Added locally under <config>/tuya_quirks/ (audit Phase 3V); tracked in the repo at
snapshots/homeassistant/tuya_quirks/.
"""

from tuya_device_handlers import TUYA_QUIRKS_REGISTRY
from tuya_device_handlers.builder import DeviceQuirk

(
    DeviceQuirk()
    .applies_to(product_id="lgibckbiszegmjlo")
    .remove_dpid(dpid=4, dpcode="mode")
    .register(TUYA_QUIRKS_REGISTRY)
)
