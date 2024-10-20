"""A SPC zone entity base class."""

from __future__ import annotations

from pyspcbridge.zone import Zone

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity

from . import (
    SIGNAL_UPDATE_PANEL,
    SIGNAL_UPDATE_AREA, 
    SIGNAL_UPDATE_ZONE,
    SIGNAL_UPDATE_OUTPUT,
    SIGNAL_UPDATE_DOOR
)    
from .const import DOMAIN

class SpcPanelEntity(Entity):
    """Spc panel entity base class."""

    _attr_should_poll = False
    _attr_has_entity_name = True

    def __init__( self, entry: ConfigEntry, panel: Panel, suffix: str) -> None:
        """Init the panel."""
        super().__init__()
        self._entry = entry
        self._panel = panel
        device_unique_id = f"{entry.unique_id}-panel-1"
        self._attr_unique_id = f"{device_unique_id}-{suffix}"
        self._attr_device_info = DeviceInfo(
            identifiers = {(DOMAIN, device_unique_id)},
            name = panel.type,
            model = f"SPC Panel",
            serial_number = panel.serial,
            sw_version = panel.firmware,
            manufacturer = "Vanderbilt",
            via_device = (DOMAIN, entry.unique_id),
        )

    async def async_added_to_hass(self) -> None:
        """ Subscribe to updates"""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{SIGNAL_UPDATE_PANEL}-{self._entry.unique_id}",
                self._update_callback,
            )
        )

    @callback
    def _update_callback(self, id) -> None:
        """Call update method."""
        if self._panel.id == id:
            self.async_schedule_update_ha_state(True)

class SpcAreaEntity(Entity):
    """Spc area entity base class."""

    _attr_should_poll = False
    _attr_has_entity_name = True

    def __init__( self, entry: ConfigEntry, area: Area, suffix: str) -> None:
        """Init the area."""
        super().__init__()
        self._entry = entry
        self._area = area
        device_unique_id = f"{entry.unique_id}-area-{area.id}"
        self._attr_unique_id = f"{device_unique_id}-{suffix}"
        self._attr_device_info = DeviceInfo(
            identifiers = {(DOMAIN, device_unique_id)},
            name = area.name,
            model = f"SPC Alarm Area",
            manufacturer = "Vanderbilt",
            via_device = (DOMAIN, entry.unique_id),
        )

    async def async_added_to_hass(self) -> None:
        """ Subscribe to updates"""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{SIGNAL_UPDATE_AREA}-{self._entry.unique_id}",
                self._update_callback,
            )
        )

    @callback
    def _update_callback(self, id) -> None:
        """Call update method."""
        if self._area.id == id:
            self.async_schedule_update_ha_state(True)

class SpcZoneEntity(Entity):
    """Spc zone entity base class."""

    _attr_should_poll = False
    _attr_has_entity_name = True

    def __init__( self, entry: ConfigEntry, zone: Zone, suffix: str) -> None:
        """Init the zone."""
        super().__init__()
        self._entry = entry
        self._zone = zone
        device_unique_id = f"{entry.unique_id}-zone-{zone.id}"
        self._attr_unique_id = f"{device_unique_id}-{suffix}"
        self._attr_device_info = DeviceInfo(
            identifiers = {(DOMAIN, device_unique_id)},
            name = zone.name,
            model = f"SPC Alarm Zone",
            manufacturer = "Vanderbilt",
            via_device = (DOMAIN, entry.unique_id),
        )

    async def async_added_to_hass(self) -> None:
        """ Subscribe to updates"""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{SIGNAL_UPDATE_ZONE}-{self._entry.unique_id}",
                self._update_callback,
            )
        )

    @callback
    def _update_callback(self, id) -> None:
        """Call update method."""
        if self._zone.id == id:
            self.async_schedule_update_ha_state(True)

class SpcOutputEntity(Entity):
    """Spc output entity base class."""

    _attr_should_poll = False
    _attr_has_entity_name = True

    def __init__( self, entry: ConfigEntry, output: Output, suffix: str) -> None:
        """Init the output."""
        super().__init__()
        self._entry = entry
        self._output = output
        device_unique_id = f"{entry.unique_id}-output-{output.id}"
        self._attr_unique_id = f"{device_unique_id}-{suffix}"
        self._attr_device_info = DeviceInfo(
            identifiers = {(DOMAIN, device_unique_id)},
            name = output.name,
            model = f"SPC Output",
            manufacturer = "Vanderbilt",
            via_device = (DOMAIN, entry.unique_id),
        )

    async def async_added_to_hass(self) -> None:
        """ Subscribe to updates"""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{SIGNAL_UPDATE_OUTPUT}-{self._entry.unique_id}",
                self._update_callback,
            )
        )

    @callback
    def _update_callback(self, id) -> None:
        """Call update method."""
        if self._output.id == id:
            self.async_schedule_update_ha_state(True)

class SpcDoorEntity(Entity):
    """Spc door entity base class."""

    _attr_should_poll = False
    _attr_has_entity_name = True

    def __init__( self, entry: ConfigEntry, door: Door, suffix: str) -> None:
        """Init the output."""
        super().__init__()
        self._entry = entry
        self._door = door
        device_unique_id = f"{entry.unique_id}-door-{door.id}"
        self._attr_unique_id = f"{device_unique_id}-{suffix}"
        self._attr_device_info = DeviceInfo(
            identifiers = {(DOMAIN, device_unique_id)},
            name = door.name,
            model = f"SPC Door",
            manufacturer = "Vanderbilt",
            via_device = (DOMAIN, entry.unique_id),
        )

    async def async_added_to_hass(self) -> None:
        """ Subscribe to updates"""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{SIGNAL_UPDATE_DOOR}-{self._entry.unique_id}",
                self._update_callback,
            )
        )

    @callback
    def _update_callback(self, id) -> None:
        """Call update method."""
        if self._door.id == id:
            self.async_schedule_update_ha_state(True)
