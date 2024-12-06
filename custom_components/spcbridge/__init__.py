"""Support for acre/Vanderbilt SPC alarm system connected via Lundix's SPC Bridge"""

import logging

_LOGGER = logging.getLogger(__name__)

from copy import deepcopy

import httpx
import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.const import (
    ATTR_CODE,
    ATTR_DEVICE_ID,
    CONF_CODE,
    CONF_IP_ADDRESS,
    CONF_PORT,
    EVENT_HOMEASSISTANT_STOP,
    Platform,
)
from homeassistant.core import (
    Event,
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
)
from homeassistant.exceptions import ConfigEntryNotReady, ServiceValidationError
from homeassistant.helpers import (
    aiohttp_client,
    config_validation as cv,
    device_registry as dr,
    entity_platform,
    entity_registry as er,
)
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.httpx_client import get_async_client as get_http_client
from homeassistant.helpers.service import async_register_admin_service
from pyspcbridge import SpcBridge
from pyspcbridge.area import Area
from pyspcbridge.door import Door
from pyspcbridge.output import Output
from pyspcbridge.panel import Panel
from pyspcbridge.zone import Zone

from .const import (
    ATTR_COMMAND,
    CONF_AREAS_INCLUDE_DATA,
    CONF_DOORS_INCLUDE_DATA,
    CONF_GET_PASSWORD,
    CONF_GET_USERNAME,
    CONF_OUTPUTS_INCLUDE_DATA,
    CONF_PUT_PASSWORD,
    CONF_PUT_USERNAME,
    CONF_USERS_DATA,
    CONF_WS_PASSWORD,
    CONF_WS_USERNAME,
    CONF_ZONES_INCLUDE_DATA,
    DOMAIN,
)
from .utils import get_host

DATA_API = "spc_api"

SIGNAL_UPDATE_PANEL = "spc_update_panel"
SIGNAL_UPDATE_AREA = "spc_update_area"
SIGNAL_UPDATE_ZONE = "spc_update_zone"
SIGNAL_UPDATE_OUTPUT = "spc_update_output"
SIGNAL_UPDATE_DOOR = "spc_update_door"

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.SENSOR,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the SPC component"""

    async def async_update_callback(command, panel_id, spc_objects=None):
        if command == "reload":
            device_registry = dr.async_get(hass)
            if device := device_registry.async_get_device(
                identifiers={(DOMAIN, f"{panel_id}-panel-1")}
            ):
                await hass.config_entries.async_reload(device.primary_config_entry)

        if command == "update":
            for _object in spc_objects:
                if isinstance(_object, Panel):
                    async_dispatcher_send(
                        hass, f"{SIGNAL_UPDATE_PANEL}-{panel_id}", _object.id
                    )
                elif isinstance(_object, Area):
                    async_dispatcher_send(
                        hass, f"{SIGNAL_UPDATE_AREA}-{panel_id}", _object.id
                    )

                elif isinstance(_object, Zone):
                    async_dispatcher_send(
                        hass, f"{SIGNAL_UPDATE_ZONE}-{panel_id}", _object.id
                    )
                elif isinstance(_object, Output):
                    async_dispatcher_send(
                        hass, f"{SIGNAL_UPDATE_OUTPUT}-{panel_id}", _object.id
                    )
                elif isinstance(_object, Door):
                    async_dispatcher_send(
                        hass, f"{SIGNAL_UPDATE_DOOR}-{panel_id}", _object.id
                    )

    async def async_panel_command(call: ServiceCall) -> None:
        """Panel command"""
        device_id = call.data[ATTR_DEVICE_ID]
        device_registry = dr.async_get(hass)
        if (device_info := device_registry.async_get(device_id)) is None:
            raise vol.Invalid("Invalid device ID specified")
        [unique_id] = [
            identity[1] for identity in device_info.identifiers if identity[0] == DOMAIN
        ]
        id = unique_id.split("-")
        if id[1] == "panel":
            command = call.data[ATTR_COMMAND]
            code = call.data[ATTR_CODE]
            spc = hass.data[DOMAIN][device_info.primary_config_entry]
            err = await spc._panel.async_command(command, code)
            if isinstance(err, dict):
                if err.get("code", 0) > 0:
                    raise ServiceValidationError(err["message"])
            if isinstance(err, list):
                for e in err.values():
                    if e.get("code", 0) > 0:
                        raise ServiceValidationError(e["message"])

    async def async_area_command(call: ServiceCall) -> None:
        """Area command"""
        device_id = call.data[ATTR_DEVICE_ID]
        device_registry = dr.async_get(hass)
        if (device_info := device_registry.async_get(device_id)) is None:
            raise vol.Invalid("Invalid device ID specified")

        [unique_id] = [
            identity[1] for identity in device_info.identifiers if identity[0] == DOMAIN
        ]
        id = unique_id.split("-")
        if id[1] == "area" and int(id[2]) > 0:
            command = call.data[ATTR_COMMAND]
            code = call.data[ATTR_CODE]
            spc = hass.data[DOMAIN][device_info.primary_config_entry]
            err = await spc._areas[int(id[2])].async_command(command, code)
            if err["code"] > 0:
                raise ServiceValidationError(err["message"])

    async def async_zone_command(call: ServiceCall) -> None:
        """Zone command"""
        device_id = call.data[ATTR_DEVICE_ID]
        device_registry = dr.async_get(hass)
        if (device_info := device_registry.async_get(device_id)) is None:
            raise vol.Invalid("Invalid device ID specified")
        [unique_id] = [
            identity[1] for identity in device_info.identifiers if identity[0] == DOMAIN
        ]
        id = unique_id.split("-")
        if id[1] == "zone" and int(id[2]) > 0:
            command = call.data[ATTR_COMMAND]
            code = call.data[ATTR_CODE]
            spc = hass.data[DOMAIN][device_info.primary_config_entry]
            err = await spc._zones[int(id[2])].async_command(command, code)
            if err["code"] > 0:
                raise ServiceValidationError(err["message"])

    async def async_output_command(call: ServiceCall) -> None:
        """Output command"""
        device_id = call.data[ATTR_DEVICE_ID]
        device_registry = dr.async_get(hass)
        if (device_info := device_registry.async_get(device_id)) is None:
            raise vol.Invalid("Invalid device ID specified")
        [unique_id] = [
            identity[1] for identity in device_info.identifiers if identity[0] == DOMAIN
        ]
        id = unique_id.split("-")
        if id[1] == "output" and int(id[2]) > 0:
            command = call.data[ATTR_COMMAND]
            code = call.data[ATTR_CODE]
            spc = hass.data[DOMAIN][device_info.primary_config_entry]
            err = await spc._outputs[int(id[2])].async_command(command, code)
            if err["code"] > 0:
                raise ServiceValidationError(err["message"])

    async def async_door_command(call: ServiceCall) -> None:
        """Door command"""
        device_id = call.data[ATTR_DEVICE_ID]
        device_registry = dr.async_get(hass)
        if (device_info := device_registry.async_get(device_id)) is None:
            raise vol.Invalid("Invalid device ID specified")
        [unique_id] = [
            identity[1] for identity in device_info.identifiers if identity[0] == DOMAIN
        ]
        id = unique_id.split("-")
        if id[1] == "door" and int(id[2]) > 0:
            command = call.data[ATTR_COMMAND]
            code = call.data[ATTR_CODE]
            spc = hass.data[DOMAIN][device_info.primary_config_entry]
            err = await spc._doors[int(id[2])].async_command(command, code)
            if err["code"] > 0:
                raise ServiceValidationError(err["message"])

    async def async_get_panel_arm_status(call: ServiceCall) -> dict | None:
        """Get area arm status"""
        arm_mode = ""
        _arm_mode = call.data["arm_mode"]
        if _arm_mode.startswith("set_a"):
            arm_mode = "set_a"
        elif _arm_mode.startswith("set_b"):
            arm_mode = "set_b"
        elif _arm_mode.startswith("set"):
            arm_mode = "set"
        elif _arm_mode.startswith("disarm"):
            arm_mode = "disarm"

        device_id = call.data[ATTR_DEVICE_ID]
        device_registry = dr.async_get(hass)
        if (device_info := device_registry.async_get(device_id)) is None:
            raise vol.Invalid("Invalid device ID specified")
        [unique_id] = [
            identity[1] for identity in device_info.identifiers if identity[0] == DOMAIN
        ]
        id = unique_id.split("-")
        if arm_mode != "" and id[1] == "panel":
            try:
                spc = hass.data[DOMAIN][device_info.primary_config_entry]
                data = await spc.async_get_arm_status(arm_mode)
                return {"area": {item["area_id"]: item["reasons"] for item in data}}
            except Exception as err:
                raise ServiceValidationError(err)

    async def async_get_area_arm_status(call: ServiceCall) -> dict | None:
        """Get area arm status"""
        arm_mode = ""
        _arm_mode = call.data["arm_mode"]
        if _arm_mode.startswith("set_a"):
            arm_mode = "set_a"
        elif _arm_mode.startswith("set_b"):
            arm_mode = "set_b"
        elif _arm_mode.startswith("set"):
            arm_mode = "set"
        elif _arm_mode.startswith("disarm"):
            arm_mode = "disarm"

        device_id = call.data[ATTR_DEVICE_ID]
        device_registry = dr.async_get(hass)
        if (device_info := device_registry.async_get(device_id)) is None:
            raise vol.Invalid("Invalid device ID specified")
        [unique_id] = [
            identity[1] for identity in device_info.identifiers if identity[0] == DOMAIN
        ]
        id = unique_id.split("-")
        if arm_mode != "" and id[1] == "area" and int(id[2]) > 0:
            try:
                spc = hass.data[DOMAIN][device_info.primary_config_entry]
                data = await spc.async_get_arm_status(arm_mode, int(id[2]))
                return {"area": {item["area_id"]: item["reasons"] for item in data}}
            except Exception as err:
                raise ServiceValidationError(err)

    # Websockets client
    session = aiohttp_client.async_get_clientsession(hass, verify_ssl=False)

    # HTTP client
    http_client = get_http_client(hass, verify_ssl=False)

    # SPC Bridge data and communication object
    spc = SpcBridge(
        gw_ip_address=entry.options[CONF_IP_ADDRESS],
        gw_port=entry.options[CONF_PORT],
        credentials={
            CONF_GET_USERNAME: entry.options[CONF_GET_USERNAME],
            CONF_GET_PASSWORD: entry.options[CONF_GET_PASSWORD],
            CONF_PUT_USERNAME: entry.options[CONF_PUT_USERNAME],
            CONF_PUT_PASSWORD: entry.options[CONF_PUT_PASSWORD],
            CONF_WS_USERNAME: entry.options[CONF_WS_USERNAME],
            CONF_WS_PASSWORD: entry.options[CONF_WS_PASSWORD],
        },
        users_config=entry.options[CONF_USERS_DATA],
        loop=hass.loop,
        session=session,
        http_client=http_client,
        async_callback=async_update_callback,
    )

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = spc

    # Load SPC configuration and current status
    try:
        await spc.async_load_config()
    except Exception as err:
        _LOGGER.error("Failed to load configuration from SPC. Retrying. Err: %s", err)
        raise ConfigEntryNotReady

    # Register SPC Bridge
    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.unique_id)},
        manufacturer="Lundix IT",
        model="SPC Bridge",
        name="SPC Bridge",
        configuration_url=f"http://{get_host(entry.options[CONF_IP_ADDRESS])}",
    )

    # Remove devices that have been manually excluded or changed in the
    # configure flow
    await async_remove_changed_devices(hass, entry)

    # Create new devices and recreate changed devices with the new settings.
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # start listening for incoming events over websocket
    spc.ws_start()

    # Register service calls
    if not hass.services.has_service(DOMAIN, "panel_command"):
        async_register_admin_service(
            hass,
            DOMAIN,
            "panel_command",
            async_panel_command,
            vol.Schema(
                {
                    vol.Required(ATTR_DEVICE_ID): cv.string,
                    vol.Required(ATTR_CODE, default=""): cv.string,
                    vol.Required(ATTR_COMMAND): cv.string,
                }
            ),
        )
    if not hass.services.has_service(DOMAIN, "area_command"):
        async_register_admin_service(
            hass,
            DOMAIN,
            "area_command",
            async_area_command,
            vol.Schema(
                {
                    vol.Required(ATTR_DEVICE_ID): cv.string,
                    vol.Required(ATTR_CODE, default=""): cv.string,
                    vol.Required(ATTR_COMMAND): cv.string,
                }
            ),
        )
    if not hass.services.has_service(DOMAIN, "zone_command"):
        async_register_admin_service(
            hass,
            DOMAIN,
            "zone_command",
            async_zone_command,
            vol.Schema(
                {
                    vol.Required(ATTR_DEVICE_ID): cv.string,
                    vol.Required(ATTR_CODE, default=""): cv.string,
                    vol.Required(ATTR_COMMAND): cv.string,
                }
            ),
        )
    if not hass.services.has_service(DOMAIN, "output_command"):
        async_register_admin_service(
            hass,
            DOMAIN,
            "output_command",
            async_output_command,
            vol.Schema(
                {
                    vol.Required(ATTR_DEVICE_ID): cv.string,
                    vol.Required(ATTR_CODE, default=""): cv.string,
                    vol.Required(ATTR_COMMAND): cv.string,
                }
            ),
        )
    if not hass.services.has_service(DOMAIN, "door_command"):
        async_register_admin_service(
            hass,
            DOMAIN,
            "door_command",
            async_door_command,
            vol.Schema(
                {
                    vol.Required(ATTR_DEVICE_ID): cv.string,
                    vol.Required(ATTR_CODE, default=""): cv.string,
                    vol.Required(ATTR_COMMAND): cv.string,
                }
            ),
        )

    if not hass.services.has_service(DOMAIN, "get_panel_arm_status"):
        hass.services.async_register(
            DOMAIN,
            "get_panel_arm_status",
            async_get_panel_arm_status,
            vol.Schema(
                {
                    vol.Required(ATTR_DEVICE_ID): cv.string,
                    vol.Required("arm_mode"): cv.string,
                }
            ),
            supports_response=SupportsResponse.ONLY,
        )

    if not hass.services.has_service(DOMAIN, "get_area_arm_status"):
        hass.services.async_register(
            DOMAIN,
            "get_area_arm_status",
            async_get_area_arm_status,
            vol.Schema(
                {
                    vol.Required(ATTR_DEVICE_ID): cv.string,
                    vol.Required("arm_mode"): cv.string,
                }
            ),
            supports_response=SupportsResponse.ONLY,
        )

    async def async_websocket_close(_: Event | None = None) -> None:
        """Close websocket connection to the Bridge."""
        if spc is not None:
            spc.ws_stop()

    entry.async_on_unload(
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, async_websocket_close)
    )
    entry.async_on_unload(async_websocket_close)

    current_options = {**entry.options}

    async def async_reload_entry(hass: HomeAssistant, new_entry: ConfigEntry) -> bool:
        """Handle configuration changes"""
        nonlocal current_options
        new_options = {**new_entry.options}

        if new_options == current_options:
            return

        spc.ws_stop()
        await hass.config_entries.async_reload(entry.entry_id)

    # Listen on configuration changes
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a SPC config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    loaded_entries = [
        entry
        for entry in hass.config_entries.async_entries(DOMAIN)
        if entry.state == ConfigEntryState.LOADED
    ]
    if len(loaded_entries) == 1:
        # If this is the last loaded instance of SPC, deregister any services
        hass.services.async_remove(DOMAIN, "panel_command")
        hass.services.async_remove(DOMAIN, "area_command")
        hass.services.async_remove(DOMAIN, "zone_command")
        hass.services.async_remove(DOMAIN, "output_command")
        hass.services.async_remove(DOMAIN, "door_command")
        hass.services.async_remove(DOMAIN, "get_panel_arm_status")
        hass.services.async_remove(DOMAIN, "get_area_arm_status")

    return unload_ok


async def async_remove_changed_devices(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Remove changed devices"""
    device_registry = dr.async_get(hass)
    entity_registry = er.async_get(hass)
    try:
        for k, v in entry.options[CONF_AREAS_INCLUDE_DATA].items():
            if v != "include":
                device_unique_id = f"{entry.unique_id}-area-{k}"
                if device := device_registry.async_get_device(
                    identifiers={(DOMAIN, device_unique_id)}
                ):
                    device_registry.async_remove_device(device.id)

        for k, v in entry.options[CONF_ZONES_INCLUDE_DATA].items():
            device_unique_id = f"{entry.unique_id}-zone-{k}"
            entity_unique_id = f"{entry.unique_id}-zone-{k}-state"
            if device := device_registry.async_get_device(
                identifiers={(DOMAIN, device_unique_id)}
            ):
                for ent in er.async_entries_for_device(
                    entity_registry, device.id, True
                ):
                    if ent.unique_id == entity_unique_id:
                        if v == "exclude" or v != ent.original_device_class:
                            device_registry.async_remove_device(device.id)

        for k, v in entry.options[CONF_OUTPUTS_INCLUDE_DATA].items():
            if v != "include":
                device_unique_id = f"{entry.unique_id}-output-{k}"
                if device := device_registry.async_get_device(
                    identifiers={(DOMAIN, device_unique_id)}
                ):
                    device_registry.async_remove_device(device.id)

        for k, v in entry.options[CONF_DOORS_INCLUDE_DATA].items():
            if v != "include":
                device_unique_id = f"{entry.unique_id}-door-{k}"
                if device := device_registry.async_get_device(
                    identifiers={(DOMAIN, device_unique_id)}
                ):
                    device_registry.async_remove_device(device.id)

        return True
    except Exception as err:
        _LOGGER.warning("ERROR Remove Changed Devices: %s", err)

    return False
