"""Support for SPC alarm status and states"""

from __future__ import annotations

import logging
_LOGGER = logging.getLogger(__name__)

from pyspcbridge import SpcBridge
from pyspcbridge.panel import Panel
from pyspcbridge.area import Area
from pyspcbridge.zone import Zone
from pyspcbridge.output import Output
import voluptuous as vol

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_platform
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.config_validation import make_entity_service_schema
from homeassistant.const import (
     CONF_CODE,
     ATTR_ENTITY_ID,
)

from .const import (
     DOMAIN,
     CONF_AREAS_INCLUDE_DATA,
     CONF_ZONES_INCLUDE_DATA,
     CONF_OUTPUTS_INCLUDE_DATA,
)
from .entity import (
     SpcPanelEntity,
     SpcAreaEntity,
     SpcZoneEntity,
     SpcOutputEntity,
)

def _get_device_class(include_mode) -> BinarySensorDeviceClass | None:
    return {
        "exclude": None,
        "motion": BinarySensorDeviceClass.MOTION,
        "door": BinarySensorDeviceClass.DOOR,
        "window": BinarySensorDeviceClass.WINDOW,
        "smoke": BinarySensorDeviceClass.SMOKE,
        "other": "none",
    }.get(include_mode)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback
) -> None:
    """Set up SPC binary sensors based on config entry."""
    api: SpcBridge = hass.data[DOMAIN][entry.entry_id]
    entities = []
    entities.append( SpcPanelIntrusionBinarySensor(entry, api.panel) )
    entities.append( SpcPanelFireBinarySensor(entry, api.panel) )
    entities.append( SpcPanelTamperBinarySensor(entry, api.panel) )
    entities.append( SpcPanelProblemBinarySensor(entry, api.panel) )
    entities.append( SpcPanelVerifiedBinarySensor(entry, api.panel) )

    included_areas = entry.options[CONF_AREAS_INCLUDE_DATA]
    for area in api.areas.values():
        if included_areas.get(str(area.id)) == "include":
            entities.append( SpcAreaIntrusionBinarySensor(entry, area) )
            entities.append( SpcAreaFireBinarySensor(entry, area) )
            entities.append( SpcAreaTamperBinarySensor(entry, area) )
            entities.append( SpcAreaProblemBinarySensor(entry, area) )
            entities.append( SpcAreaVerifiedBinarySensor(entry, area) )

    included_zones = entry.options[CONF_ZONES_INCLUDE_DATA]
    for zone in api.zones.values():
        if id := included_zones.get(str(zone.id)):
            if device_class := _get_device_class(id):
                entities.append( SpcZoneStateBinarySensor(entry, zone, device_class) )
                entities.append( SpcZoneAlarmBinarySensor(entry, zone) )
                entities.append( SpcZoneTamperBinarySensor(entry, zone) )
                entities.append( SpcZoneProblemBinarySensor(entry, zone) )
                entities.append( SpcZoneInhibitedBinarySensor(entry, zone) )
                entities.append( SpcZoneIsolatedBinarySensor(entry, zone) )

    included_outputs = entry.options[CONF_OUTPUTS_INCLUDE_DATA]
    for output in api.outputs.values():
        if included_outputs.get(str(output.id)) == "include":
            entities.append( SpcOutputStateBinarySensor(entry, output) )

    async_add_entities(entities)

class SpcPanelIntrusionBinarySensor(SpcPanelEntity, BinarySensorEntity):
    """Representation of intrusion status of a SPC panel."""

    _attr_translation_key = "panel_intrusion"

    def __init__(self, entry: ConfigEntry, panel: Panel) -> None:
        """Initialize the sensor device."""
        super().__init__(entry=entry, panel=panel, suffix="intrusion")
        self._attr_device_class = None    # There is no specific class for alarm

    @property
    def is_on(self) -> bool:
        _LOGGER.debug("Entity: %s, State: %s", self._attr_unique_id, self._panel.intrusion)
        return self._panel.intrusion

class SpcPanelFireBinarySensor(SpcPanelEntity, BinarySensorEntity):
    """Representation of fire status of a SPC panel."""

    _attr_translation_key = "panel_fire"

    def __init__(self, entry: ConfigEntry, panel: Panel) -> None:
        """Initialize the sensor device."""
        super().__init__(entry=entry, panel=panel, suffix="fire")
        self._attr_device_class = None    # There is no specific class for alarm

    @property
    def is_on(self) -> bool:
        _LOGGER.debug("Entity: %s, State: %s", self._attr_unique_id, self._panel.fire)
        return self._panel.fire

class SpcPanelTamperBinarySensor(SpcPanelEntity, BinarySensorEntity):
    """Representation of tamper status of a SPC panel."""

    _attr_translation_key = "panel_tamper"

    def __init__(self, entry: ConfigEntry, panel: Panel) -> None:
        """Initialize the sensor device."""
        super().__init__(entry=entry, panel=panel, suffix="tamper")
        self._attr_device_class = None    # There is no specific class for alarm

    @property
    def is_on(self) -> bool:
        _LOGGER.debug("Entity: %s, State: %s", self._attr_unique_id, self._panel.tamper)
        return self._panel.tamper

class SpcPanelProblemBinarySensor(SpcPanelEntity, BinarySensorEntity):
    """Representation of problem status of a SPC panel."""

    _attr_translation_key = "panel_problem"

    def __init__(self, entry: ConfigEntry, panel: Panel) -> None:
        """Initialize the sensor device."""
        super().__init__(entry=entry, panel=panel, suffix="problem")
        self._attr_device_class = None    # There is no specific class for alarm

    @property
    def is_on(self) -> bool:
        _LOGGER.debug("Entity: %s, State: %s", self._attr_unique_id, self._panel.problem)
        return self._panel.problem

class SpcPanelVerifiedBinarySensor(SpcPanelEntity, BinarySensorEntity):
    """Representation of verified status of a SPC panel."""

    _attr_translation_key = "panel_verified"

    def __init__(self, entry: ConfigEntry, panel: Panel) -> None:
        """Initialize the sensor device."""
        super().__init__(entry=entry, panel=panel, suffix="verified")
        self._attr_device_class = None    # There is no specific class for alarm

    @property
    def is_on(self) -> bool:
        _LOGGER.debug("Entity: %s, State: %s", self._attr_unique_id, self._panel.verified)
        return self._panel.verified


class SpcAreaIntrusionBinarySensor(SpcAreaEntity, BinarySensorEntity):
    """Representation of intrusion status of a SPC area."""

    _attr_translation_key = "area_intrusion"

    def __init__(self, entry: ConfigEntry, area: Area) -> None:
        """Initialize the sensor device."""
        super().__init__(entry=entry, area=area, suffix="intrusion")
        self._attr_device_class = None    # There is no specific class for alarm

    @property
    def is_on(self) -> bool:
        _LOGGER.debug("Entity: %s, State: %s", self._attr_unique_id, self._area.intrusion)
        return self._area.intrusion

class SpcAreaFireBinarySensor(SpcAreaEntity, BinarySensorEntity):
    """Representation of fire status of a SPC area."""

    _attr_translation_key = "area_fire"

    def __init__(self, entry: ConfigEntry, area: Area) -> None:
        """Initialize the sensor device."""
        super().__init__(entry=entry, area=area, suffix="fire")
        self._attr_device_class = None    # There is no specific class for alarm

    @property
    def is_on(self) -> bool:
        _LOGGER.debug("Entity: %s, State: %s", self._attr_unique_id, self._area.fire)
        return self._area.fire

class SpcAreaTamperBinarySensor(SpcAreaEntity, BinarySensorEntity):
    """Representation of tamper status of a SPC area."""

    _attr_translation_key = "area_tamper"

    def __init__(self, entry: ConfigEntry, area: Area) -> None:
        """Initialize the sensor device."""
        super().__init__(entry=entry, area=area, suffix="tamper")
        self._attr_device_class = None    # There is no specific class for alarm

    @property
    def is_on(self) -> bool:
        _LOGGER.debug("Entity: %s, State: %s", self._attr_unique_id, self._area.tamper)
        return self._area.tamper

class SpcAreaProblemBinarySensor(SpcAreaEntity, BinarySensorEntity):
    """Representation of problem status of a SPC area."""

    _attr_translation_key = "area_problem"

    def __init__(self, entry: ConfigEntry, area: Area) -> None:
        """Initialize the sensor device."""
        super().__init__(entry=entry, area=area, suffix="problem")
        self._attr_device_class = None    # There is no specific class for alarm

    @property
    def is_on(self) -> bool:
        _LOGGER.debug("Entity: %s, State: %s", self._attr_unique_id, self._area.problem)
        return self._area.problem

class SpcAreaVerifiedBinarySensor(SpcAreaEntity, BinarySensorEntity):
    """Representation of verified status of a SPC area."""

    _attr_translation_key = "area_verified"

    def __init__(self, entry: ConfigEntry, area: Area) -> None:
        """Initialize the sensor device."""
        super().__init__(entry=entry, area=area, suffix="verified")
        self._attr_device_class = None    # There is no specific class for alarm

    @property
    def is_on(self) -> bool:
        _LOGGER.debug("Entity: %s, State: %s", self._attr_unique_id, self._area.verified)
        return self._area.verified

class SpcZoneStateBinarySensor(SpcZoneEntity, BinarySensorEntity):
    """Representation of state of a SPC zone."""

    def __init__(self, entry: ConfigEntry, zone: Zone, device_class) -> None:
        """Initialize the sensor device."""
        super().__init__(entry=entry, zone=zone, suffix="state")
        self._attr_device_class = device_class

    @property
    def extra_state_attributes(self):
        return {
            "unique_id": self._attr_unique_id,
            "name": self._zone.name,
            "input": self._zone.input,
            "inhibited": self._zone.inhibited,
            "isolated": self._zone.isolated,
            "alarm_status": self._zone.alarm_status,
            "area_name": self._zone._area.name,
        }

    @property
    def is_on(self) -> bool:
        _LOGGER.debug("Entity: %s, State: %s", self._attr_unique_id, self._zone.state)
        return self._zone.state

class SpcZoneAlarmBinarySensor(SpcZoneEntity, BinarySensorEntity):
    """Representation of alarm status of a SPC zone."""

    _attr_translation_key = "zone_alarm"

    def __init__(self, entry: ConfigEntry, zone: Zone) -> None:
        """Initialize the sensor device."""
        super().__init__(entry=entry, zone=zone, suffix="alarm")
        self._attr_device_class = None    # There is no specific class for alarm

    @property
    def is_on(self) -> bool:
        _LOGGER.debug("Entity: %s, Intrusion: %s, Fire: %s", self._attr_unique_id, self._zone.intrusion, self._zone.fire)
        return self._zone.intrusion or self._zone.fire

class SpcZoneTamperBinarySensor(SpcZoneEntity, BinarySensorEntity):
    """Representation of tamper status of a SPC zone."""

    _attr_translation_key = "zone_tamper"

    def __init__(self, entry: ConfigEntry, zone: Zone) -> None:
        """Initialize the sensor device."""
        super().__init__(entry=entry, zone=zone, suffix="tamper")
        self._attr_device_class = None 

    @property
    def is_on(self) -> bool:
        _LOGGER.debug("Entity: %s, State: %s", self._attr_unique_id, self._zone.tamper)
        return self._zone.tamper

class SpcZoneProblemBinarySensor(SpcZoneEntity, BinarySensorEntity):
    """Representation of problem status of a SPC zone."""

    _attr_translation_key = "zone_problem"

    def __init__(self, entry: ConfigEntry, zone: Zone) -> None:
        """Initialize the sensor device."""
        super().__init__(entry=entry, zone=zone, suffix="problem")
        self._attr_device_class = None

    @property
    def is_on(self) -> bool:
        _LOGGER.debug("Entity: %s, State: %s", self._attr_unique_id, self._zone.problem)
        return self._zone.problem

class SpcZoneInhibitedBinarySensor(SpcZoneEntity, BinarySensorEntity):
    """Representation of inhibit status of a SPC zone."""

    _attr_translation_key = "zone_inhibited"

    def __init__(self, entry: ConfigEntry, zone: Zone) -> None:
        """Initialize the sensor device."""
        super().__init__(entry=entry, zone=zone, suffix="inhibited")
        self._attr_device_class = None

    @property
    def is_on(self) -> bool:
        _LOGGER.debug("Entity: %s, State: %s", self._attr_unique_id, self._zone.inhibited)
        return self._zone.inhibited

class SpcZoneIsolatedBinarySensor(SpcZoneEntity, BinarySensorEntity):
    """Representation of isolate status of a SPC zone."""

    _attr_translation_key = "zone_isolated"

    def __init__(self, entry: ConfigEntry, zone: Zone) -> None:
        """Initialize the sensor device."""
        super().__init__(entry=entry, zone=zone, suffix="isolated")
        self._attr_device_class = None

    @property
    def is_on(self) -> bool:
        _LOGGER.debug("Entity: %s, State: %s", self._attr_unique_id, self._zone.isolated)
        return self._zone.isolated

class SpcOutputStateBinarySensor(SpcOutputEntity, BinarySensorEntity):
    """Representation of the state of a SPC output."""

    _attr_translation_key = "output_state"

    def __init__(self, entry: ConfigEntry, output: Output) -> None:
        """Initialize the sensor device."""
        super().__init__(entry=entry, output=output, suffix="state")
        self._attr_device_class = None    # There is no specific class for alarm

    @property
    def is_on(self) -> bool:
        _LOGGER.debug("Entity: %s, State: %s", self._attr_unique_id, self._output.state)
        return self._output.state

    @property
    def extra_state_attributes(self):
        return {
            "unique_id": self._attr_unique_id,
            "name": self._output.name,
            "state": self._output.state,
        }
