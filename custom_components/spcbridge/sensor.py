"""SPC"""
from __future__ import annotations

import logging
_LOGGER = logging.getLogger(__name__)

from pyspcbridge import SpcBridge
from pyspcbridge.panel import Panel
from pyspcbridge.area import Area
from pyspcbridge.const import ArmMode
from pyspcbridge.door import Door
import voluptuous as vol

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.util.json import json_loads
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
    CONF_DOORS_INCLUDE_DATA,
    CONF_AREAS_INCLUDE_DATA
)
from .entity import SpcPanelEntity, SpcAreaEntity, SpcDoorEntity
from .utils import arm_mode_to_name, door_mode_to_name

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback
) -> None:
    """Set up SPC sensors based on config entry."""
    api: SpcBridge = hass.data[DOMAIN][entry.entry_id]
    entities = []
    entities.append( SpcPanelArmModeSensor(entry, api.panel) )
    entities.append( SpcPanelEventSensor(entry, api.panel) )

    for area in api.areas.values():
        if entry.options[CONF_AREAS_INCLUDE_DATA].get(str(area.id)) == "include":
            entities.append( SpcAreaArmModeSensor(entry, area) )

    for door in api.doors.values():
        if entry.options[CONF_DOORS_INCLUDE_DATA].get(str(door.id)) == "include":
            entities.append( SpcDoorModeSensor(entry, door) )
            entities.append( SpcDoorEntryGrantedSensor(entry, door) )
            entities.append( SpcDoorEntryDeniedSensor(entry, door) )
            entities.append( SpcDoorExitGrantedSensor(entry, door) )
            entities.append( SpcDoorExitDeniedSensor(entry, door) )

    async_add_entities(entities)

class SpcPanelArmModeSensor(SpcPanelEntity, SensorEntity):
    """Representation of SPC panel arm mode."""

    _attr_translation_key = "panel_arm_mode"

    def __init__(self, entry: ConfigEntry, panel: Panel) -> None:
        """Initialize the sensor device."""
        super().__init__(entry=entry, panel=panel, suffix="arm_mode")
        self._attr_device_class = SensorDeviceClass.ENUM
        self._attr_options = [
           "disarmed",
           "partset_a",
           "partset_b",
           "armed",
           "partset_a_partly",
           "partset_b_partly",
           "armed_partly",
           "unknown"
        ]

    @property
    def native_value(self) -> str | None:
        return arm_mode_to_name(self._panel.mode)

    @property
    def extra_state_attributes(self):
        return {
            "title": "System",
            "unique_id": self._attr_unique_id,
            "arm_mode": self._panel.mode,
            "mode": self._panel.mode,
            "alarm_status": self._panel.alarm_status,
            "partset_a_enabled": self._panel.a_enabled,
            "partset_a_name": self._panel.a_name,
            "partset_b_enabled": self._panel.b_enabled,
            "partset_b_name": self._panel.b_name,
            "exittime": self._panel.exittime,
            "entrytime": self._panel.entrytime,
            "spc_event": self._panel.event,
            "area_ids": [a.id for a in self._panel._areas],
        }

    @property
    def changed_by(self) -> str:
        """Return the user who last changed panel arm mode"""
        return self._panel.changed_by

class SpcPanelEventSensor(SpcPanelEntity, SensorEntity):
    """Representation of sia events from SPC panel."""

    _attr_translation_key = "panel_event"

    def __init__(self, entry: ConfigEntry, panel: Panel) -> None:
        """Initialize the sensor device."""
        super().__init__(entry=entry, panel=panel, suffix="event")
        self._attr_device_class = None    # There is no specific class for alarm

    @property
    def native_value(self) -> str | None:
        value = ""
        if self._panel.event != "":
            m = []
            event = json_loads(self._panel.event)
            keys = ["ev_desc", "area_name", "zone_name", "mg_name", "door_name"]
            for key in keys:
                if (v := event.get(key)):
                   m.append(v)
            value = " - ".join(m)
        return value

class SpcAreaArmModeSensor(SpcAreaEntity, SensorEntity):
    """Representation of SPC area arm mode."""

    _attr_translation_key = "area_arm_mode"

    def __init__(self, entry: ConfigEntry, area: Area) -> None:
        """Initialize the sensor device."""
        super().__init__(entry=entry, area=area, suffix="arm_mode")
        self._attr_device_class = SensorDeviceClass.ENUM
        self._attr_options = [
           "disarmed",
           "partset_a",
           "partset_b",
           "armed",
           "unknown"
        ]

    @property
    def native_value(self) -> str | None:
        return arm_mode_to_name(self._area.mode)

    @property
    def extra_state_attributes(self):
        return {
            "unique_id": self._attr_unique_id,
            "title": self._area.name or f"Area {self._area.id}",
            "mode": self._area.mode,
            "alarm_status": self._area.alarm_status,
            "partset_a_enabled": self._area.a_enabled,
            "partset_a_name": self._area.a_name,
            "partset_b_enabled": self._area.b_enabled,
            "partset_b_name": self._area.b_name,
            "exittime": self._area.exittime,
            "entrytime": self._area.entrytime,
            "zone_ids": [z.id for z in self._area.zones],
            "last_disarmed_user": self._area.unset_user,
            "last_armed_user": self._area.set_user,
        }

    @property
    def changed_by(self) -> str:
        """Return the user who last changed arm mode"""
        return self._area.changed_by

    @property
    def last_disarmed_user(self) -> str:
        """Return the user who last disarmed the area"""
        return self._area.unset_user

    @property
    def last_armed_user(self) -> str:
        """Return the user who last armed the area"""
        return self._area.set_user

class SpcDoorModeSensor(SpcDoorEntity, SensorEntity):
    """Representation of door mode."""

    _attr_translation_key = "door_mode"

    def __init__(self, entry: ConfigEntry, door: Door) -> None:
        """Initialize the sensor device."""
        super().__init__(entry=entry, door=door, suffix="mode")
        self._attr_device_class = SensorDeviceClass.ENUM
        self._attr_options = [
           "unlocked",
           "normal",
           "locked",
           "unknown"
        ]

    @property
    def native_value(self) -> str | None:
        return door_mode_to_name(self._door.mode)

    @property
    def extra_state_attributes(self):
        return {
            "unique_id": self._attr_unique_id,
            "name": self._door.name,
            "mode": self._door.mode,
        }

class SpcDoorEntryGrantedSensor(SpcDoorEntity, SensorEntity):
    """Representation of entry granted user."""

    _attr_translation_key = "entry_granted"

    def __init__(self, entry: ConfigEntry, door: Door) -> None:
        """Initialize the sensor device."""
        super().__init__(entry=entry, door=door, suffix="entry_granted")
        self._attr_device_class = None    # There is no specific class for alarm

    @property
    def native_value(self) -> str | None:
        return self._door.entry_granted

class SpcDoorEntryDeniedSensor(SpcDoorEntity, SensorEntity):
    """Representation of entry denied user."""

    _attr_translation_key = "entry_denied"

    def __init__(self, entry: ConfigEntry, door: Door) -> None:
        """Initialize the sensor device."""
        super().__init__(entry=entry, door=door, suffix="entry_denied")
        self._attr_device_class = None    # There is no specific class for alarm

    @property
    def native_value(self) -> str | None:
        return self._door.entry_denied

class SpcDoorExitGrantedSensor(SpcDoorEntity, SensorEntity):
    """Representation of exit granted user."""

    _attr_translation_key = "exit_granted"

    def __init__(self, entry: ConfigEntry, door: Door) -> None:
        """Initialize the sensor device."""
        super().__init__(entry=entry, door=door, suffix="exit_granted")
        self._attr_device_class = None    # There is no specific class for alarm

    @property
    def native_value(self) -> str | None:
        return self._door.exit_granted

class SpcDoorExitDeniedSensor(SpcDoorEntity, SensorEntity):
    """Representation of exit denied user."""

    _attr_translation_key = "exit_denied"

    def __init__(self, entry: ConfigEntry, door: Door) -> None:
        """Initialize the sensor device."""
        super().__init__(entry=entry, door=door, suffix="exit_denied")
        self._attr_device_class = None    # There is no specific class for alarm

    @property
    def native_value(self) -> str | None:
        return self._door.exit_denied
