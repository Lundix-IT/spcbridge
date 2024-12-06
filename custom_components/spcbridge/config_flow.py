"""Config flow for SPC integration."""

from __future__ import annotations

import ipaddress
import logging
from copy import deepcopy
from typing import Any

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant import config_entries, exceptions
from homeassistant.const import CONF_IP_ADDRESS, CONF_PORT
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import aiohttp_client
from homeassistant.helpers.httpx_client import get_async_client as get_http_client
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)
from pyspcbridge import SpcBridge
from pyspcbridge.const import ZoneType

from .const import (
    CONF_AREAS_INCLUDE_DATA,
    CONF_DOORS_INCLUDE_DATA,
    CONF_GET_PASSWORD,
    CONF_GET_USERNAME,
    CONF_OUTPUTS_INCLUDE_DATA,
    CONF_PUT_PASSWORD,
    CONF_PUT_USERNAME,
    CONF_USER_IDENTIFY_BY_ID,
    CONF_USER_IDENTIFY_BY_MAP,
    CONF_USER_IDENTIFY_METHOD,
    CONF_USERS_DATA,
    CONF_WS_PASSWORD,
    CONF_WS_USERNAME,
    CONF_ZONES_INCLUDE_DATA,
    DEFAULT_BRIDGE_GET_PASSWORD,
    DEFAULT_BRIDGE_GET_USERNAME,
    DEFAULT_BRIDGE_PORT,
    DEFAULT_BRIDGE_PUT_PASSWORD,
    DEFAULT_BRIDGE_PUT_USERNAME,
    DEFAULT_BRIDGE_WS_PASSWORD,
    DEFAULT_BRIDGE_WS_USERNAME,
    DOMAIN,
)

# from .hub import Hub

_LOGGER = logging.getLogger(__name__)

ZONE_OPTIONS = [
    {"value": "exclude", "label": "Don't include"},
    {"value": "motion", "label": "Include as a Motion sensor"},
    {"value": "door", "label": "Include as a Door contact sensor"},
    {"value": "window", "label": "Include as a Window contact sensor"},
    {"value": "smoke", "label": "Include as a Smoke sensor"},
    {"value": "other", "label": "Include as a Other sensor"},
]
DEFAULT_ZONE_OPTION = "motion"
DEFAULT_FIRE_ZONE_OPTION = "smoke"


def generate_schema(object_type, spc_objects) -> vol.Schema:
    """Generate schema."""
    schema: dict[vol.Marker, Any] = {}

    if object_type == "spc_users":
        for _o in spc_objects:
            id = _o["id"]
            name = _o["name"]
            schema[vol.Optional(f"label_{id}")] = f"User {id}, {name}"
            schema[vol.Optional(f"pincode_{id}", default="")] = TextSelector(
                TextSelectorConfig(
                    prefix="Keypad Code: ", type=TextSelectorType.PASSWORD
                )
            )
            schema[vol.Optional(f"password_{id}", default="")] = TextSelector(
                TextSelectorConfig(
                    prefix="SPC Password: ", type=TextSelectorType.PASSWORD
                )
            )

    if object_type == "alarm_areas":
        options = []
        defaults = []
        for _o in spc_objects:
            id = _o["id"]
            name = _o["name"]
            options.append({"value": f"area_{id}", "label": name})
            defaults.append(f"area_{id}")

        schema[vol.Required("include_areas", default=defaults)] = SelectSelector(
            SelectSelectorConfig(
                multiple=True,
                mode="list",
                options=options,
            )
        )

    if object_type == "alarm_zones":
        for _o in spc_objects:
            id = _o["id"]
            name = _o["name"]
            type = _o["type"]
            options = [
                {"value": "exclude", "label": f"{name}[{id}] - Don't include"},
                {"value": "motion", "label": f"{name}[{id}] - Motion sensor"},
                {"value": "door", "label": f"{name}[{id}] - Door contact sensor"},
                {"value": "window", "label": f"{name}[{id}] - Window contact sensor"},
                {"value": "smoke", "label": f"{name}[{id}] - Smoke sensor"},
                {"value": "other", "label": f"{name}[{id}] - Other sensor"},
            ]
            if ZoneType(type) == ZoneType.FIRE:
                default_zone_option = DEFAULT_FIRE_ZONE_OPTION
            else:
                default_zone_option = DEFAULT_ZONE_OPTION

            schema[vol.Required(f"include_{id}", default=default_zone_option)] = (
                SelectSelector(
                    SelectSelectorConfig(
                        options=options,
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                )
            )

    if object_type == "outputs":
        options = []
        defaults = []
        if len(spc_objects) == 0:
            schema[vol.Optional("no_outputs")] = ""
        else:
            for _o in spc_objects:
                id = _o["id"]
                name = _o["name"]
                options.append({"value": f"output_{id}", "label": name})
                defaults.append(f"output_{id}")

            schema[vol.Required("include_outputs", default=defaults)] = SelectSelector(
                SelectSelectorConfig(
                    multiple=True,
                    mode="list",
                    options=options,
                )
            )

    if object_type == "doors":
        options = []
        defaults = []
        if len(spc_objects) == 0:
            schema[vol.Optional("no_doors")] = ""
        else:
            for _o in spc_objects:
                id = _o["id"]
                name = _o["name"]
                options.append({"value": f"door_{id}", "label": name})
                defaults.append(f"door_{id}")

            schema[vol.Required("include_doors", default=defaults)] = SelectSelector(
                SelectSelectorConfig(
                    multiple=True,
                    mode="list",
                    options=options,
                )
            )

    return vol.Schema(schema)


def generate_option_schema(object_type, objects) -> vol.Schema:
    """Generate option schema."""
    schema: dict[vol.Marker, Any] = {}

    if object_type == "spc_users":
        for _o in objects.values():
            id = _o.get("id")
            if id is not None:
                name = _o.get("name", "")
                schema[vol.Optional(f"label_{id}")] = f"User {id}, {name}"
                schema[
                    vol.Optional(f"pincode_{id}", default=_o.get("ha_pincode", ""))
                ] = TextSelector(
                    TextSelectorConfig(
                        prefix="Keypad Code: ",
                        type=TextSelectorType.PASSWORD,
                    )
                )
                schema[
                    vol.Optional(f"password_{id}", default=_o.get("spc_password", ""))
                ] = TextSelector(
                    TextSelectorConfig(
                        prefix="SPC Password: ", type=TextSelectorType.PASSWORD
                    )
                )

    if object_type == "alarm_areas":
        options = []
        defaults = []
        for _o in objects.values():
            id = _o.get("id")
            if id is not None:
                name = _o.get("name")
                options.append({"value": f"area_{id}", "label": name})
                if _o.get("include"):
                    defaults.append(f"area_{id}")

        schema[vol.Required("include_areas", default=defaults)] = SelectSelector(
            SelectSelectorConfig(
                multiple=True,
                mode="list",
                options=options,
            )
        )

    if object_type == "alarm_zones":
        for _o in objects.values():
            id = _o.get("id")
            if id is not None:
                name = _o.get("name")
                options = [
                    {"value": "exclude", "label": f"{name}[{id}] - Don't include"},
                    {"value": "motion", "label": f"{name}[{id}] - Motion sensor"},
                    {"value": "door", "label": f"{name}[{id}] - Door contact sensor"},
                    {
                        "value": "window",
                        "label": f"{name}[{id}] - Window contact sensor",
                    },
                    {"value": "smoke", "label": f"{name}[{id}] - Smoke sensor"},
                    {"value": "other", "label": f"{name}[{id}] - Other sensor"},
                ]
                default_zone_option = _o.get("include")

                schema[vol.Required(f"include_{id}", default=default_zone_option)] = (
                    SelectSelector(
                        SelectSelectorConfig(
                            options=options,
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    )
                )

    if object_type == "outputs":
        options = []
        defaults = []

        if len(objects.values()) == 0:
            schema[vol.Optional("no_outputs")] = ""
        else:
            for _o in objects.values():
                id = _o.get("id")
                if id is not None:
                    name = _o.get("name")
                    options.append({"value": f"output_{id}", "label": name})
                    if _o.get("include"):
                        defaults.append(f"output_{id}")

            schema[vol.Required("include_outputs", default=defaults)] = SelectSelector(
                SelectSelectorConfig(
                    multiple=True,
                    mode="list",
                    options=options,
                )
            )

    if object_type == "doors":
        options = []
        defaults = []

        if len(objects.values()) == 0:
            schema[vol.Optional("no_doors")] = ""
        else:
            for _o in objects.values():
                id = _o.get("id")
                if id is not None:
                    name = _o.get("name")
                    options.append({"value": f"door_{id}", "label": name})
                    if _o.get("include"):
                        defaults.append(f"door_{id}")

            schema[vol.Required("include_doors", default=defaults)] = SelectSelector(
                SelectSelectorConfig(
                    multiple=True,
                    mode="list",
                    options=options,
                )
            )

    return vol.Schema(schema)


def zone_type_to_name(zone_type) -> str:
    return ZoneType(zone_type).name.replace("_", " ").title()


def include_mode_to_name(include_mode) -> str:
    match include_mode:
        case "include":
            return "<b>Include</b>"
        case "exclude":
            return "<b>Exclude</b>"
        case "motion":
            return "<b>Include as a Motion sensor</b>"
        case "door":
            return "<b>Include as a Door sensor</b>"
        case "window":
            return "<b>Include as a Window sensor</b>"
        case "smoke":
            return "<b>Include as a Smoke sensor</b>"
        case "other":
            return "<b>Include as a Other sensor</b>"
        case _:
            return "Unknown"


def generate_html(step_id, objects) -> str:
    p = objects.get("panel")
    u = objects.get("users")
    a = objects.get("areas")
    z = objects.get("zones")
    o = objects.get("outputs")
    d = objects.get("doors")
    html = ""
    if step_id == "discovered":
        html = f"""
                <div>
                  <h3>Panel</h3>
                  <table width=100%>
                    <tr><td>Serial number:</td><td>{p.get("serial", "-")}</td></tr>
                    <tr><td width=30%>Type:</td><td>{p.get("type", "-")}</td></tr>
                    <tr><td>Model:</td><td>{p.get("model", "-")}</td></tr>
                  </table>
                </div>
                <br>
                <div>
                  <h3>Users</h3>
                  <table width=100%>
                    <tbody>
                       {"".join([f"<tr><td width=20%>{str(_u.get("id","-"))}</td><td>{_u.get("name", "-")}</td></tr>" for _u in u])}
                    </tbody>
                  </table>
                </div>
                <br>
                <div>
                  <h3>Alarm Areas</h3>
                  <table width=100%>
                    <tbody>
                       {"".join([f"<tr><td width=20%>{str(_a.get("id","-"))}</td><td>{_a.get("name", "-")}</td></tr>" for _a in a])}
                    </tbody>
                  </table>
                </div>
                <br>
                <div>
                  <h3>Alarm Zones</h3>
                  <table width=100%>
                    <tbody>
                       {"".join([f"<tr><td width=20%>{str(_z.get("id","-"))}</td><td width=40%>{_z.get("name", "-")}</td><td>{zone_type_to_name(_z.get("type"))}</td></tr>" for _z in z])}
                    </tbody>
                  </table>
                </div>
                <br>
                <div>
                  <h3>Outputs</h3>
                  <table width=100%>
                    <tbody>
                       {"".join([f"<tr><td width=20%>{str(_o.get("id","-"))}</td><td>{_o.get("name", "-")}</td></tr>" for _o in o])}
                    </tbody>
                  </table>
                </div>
                <br>
                <div>
                  <h3>Door Locks</h3>
                  <table width=100%>
                    <tbody>
                       {"".join([f"<tr><td width=20%>{str(_d.get("id","-"))}</td><td>{_d.get("name", "-")}</td></tr>" for _d in d])}
                    </tbody>
                  </table>
                </div>
                """

    if step_id == "confirm":
        html = f"""
                <div>
                  <h3>Panel</h3>
                  <table width=100%>
                    <tr><td>Serial number:</td><td>{p.get("serial", "-")}</td></tr>
                  </table>
                </div>
                <br>
                <div>
                  <h3>Alarm Areas</h3>
                  <table width=100%>
                    <tbody>
                       {"".join([f"<tr><td width=15%>{str(_a.get("id","-"))}</td><td width=40%>{_a.get("name", "-")}</td><td>{include_mode_to_name(_a.get("include_mode", ""))}</td></tr>" for _a in a])}
                    </tbody>
                  </table>
                </div>
                <br>
                <div>
                  <h3>Alarm Zones</h3>
                  <table width=100%>
                    <tbody>
                       {"".join([f"<tr><td width=15%>{str(_z.get("id","-"))}</td><td width=40%>{_z.get("name", "-")}</td><td>{include_mode_to_name(_z.get("include_mode", ""))}</td></tr>" for _z in z])}
                    </tbody>
                  </table>
                </div>
                <br>
                <div>
                  <h3>Outputs</h3>
                  <table width=100%>
                    <tbody>
                       {"".join([f"<tr><td width=15%>{str(_o.get("id","-"))}</td><td width=40%>{_o.get("name", "-")}</td><td>{include_mode_to_name(_o.get("include_mode", ""))}</td></tr>" for _o in o])}
                    </tbody>
                  </table>
                </div>
                <br>
                <div>
                  <h3>Door Locks</h3>
                  <table width=100%>
                    <tbody>
                       {"".join([f"<tr><td width=15%>{str(_d.get("id","-"))}</td><td width=40%>{_d.get("name", "-")}</td><td>{include_mode_to_name(_d.get("include_mode", ""))}</td></tr>" for _d in d])}
                    </tbody>
                  </table>
                </div>
                """

    return "".join(line.strip() for line in html.splitlines())


async def test_connection(hass: HomeAssistant, bridge_data: dict):
    try:
        session = aiohttp_client.async_get_clientsession(hass, verify_ssl=False)
        http_client = get_http_client(hass, verify_ssl=False)

        spc = SpcBridge(
            gw_ip_address=bridge_data[CONF_IP_ADDRESS],
            gw_port=bridge_data[CONF_PORT],
            credentials={
                CONF_GET_USERNAME: bridge_data[CONF_GET_USERNAME],
                CONF_GET_PASSWORD: bridge_data[CONF_GET_PASSWORD],
                CONF_PUT_USERNAME: bridge_data[CONF_PUT_USERNAME],
                CONF_PUT_PASSWORD: bridge_data[CONF_PUT_PASSWORD],
                CONF_WS_USERNAME: bridge_data[CONF_WS_USERNAME],
                CONF_WS_PASSWORD: bridge_data[CONF_WS_PASSWORD],
            },
            users_config={},
            loop=hass.loop,
            session=session,
            http_client=http_client,
            async_callback=None,
        )

        spc_panel_id = await spc.test_connection()
        if spc_panel_id is None:
            raise CannotConnect
        return spc_panel_id

    except Exception as err:
        _LOGGER.error("Test connection failed")
        if err:
            _LOGGER.error(err)
        raise CannotConnect from err


def validate_spc_users_data(data: dict):
    """Validate SPC user data"""
    errors = {}
    HA_PINCODE_SCHEMA = vol.All(vol.Coerce(int), vol.Range(min=0, max=9999999999))
    SPC_PASSWORD_SCHEMA = vol.All(vol.Coerce(str), vol.Length(min=1, max=16))
    for user in data.values():
        id = user.get("id")
        _name = user.get("name", "")
        ha_pincode = user.get("ha_pincode", "")
        if ha_pincode != "":
            try:
                HA_PINCODE_SCHEMA(ha_pincode)
            except Exception:
                errors[f"pincode_{id}"] = "Invalid Keypad code (1 to 10 digits)"

        spc_password = user.get("spc_password", "")
        if spc_password != "":
            try:
                SPC_PASSWORD_SCHEMA(spc_password)
            except Exception:
                errors[f"password_{id}"] = "Invalid SPC Password (1 to 16 characters)"

    return errors


class SpcConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SPC."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_PUSH

    def __init__(self) -> None:
        """Initialize the config flow."""
        self.data = {}
        self.options = {
            CONF_IP_ADDRESS: "",
            CONF_PORT: DEFAULT_BRIDGE_PORT,
            CONF_GET_USERNAME: DEFAULT_BRIDGE_GET_USERNAME,
            CONF_GET_PASSWORD: DEFAULT_BRIDGE_GET_PASSWORD,
            CONF_PUT_USERNAME: DEFAULT_BRIDGE_PUT_USERNAME,
            CONF_PUT_PASSWORD: DEFAULT_BRIDGE_PUT_PASSWORD,
            CONF_WS_USERNAME: DEFAULT_BRIDGE_WS_USERNAME,
            CONF_WS_PASSWORD: DEFAULT_BRIDGE_WS_PASSWORD,
            CONF_USER_IDENTIFY_METHOD: "",
            CONF_USERS_DATA: {},
            CONF_AREAS_INCLUDE_DATA: {},
            CONF_ZONES_INCLUDE_DATA: {},
            CONF_OUTPUTS_INCLUDE_DATA: {},
            CONF_DOORS_INCLUDE_DATA: {},
        }
        self.spc_data = {}

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            try:
                ipaddress.ip_address(user_input[CONF_IP_ADDRESS])
            except ValueError:
                errors[CONF_IP_ADDRESS] = "invalid_ip_address"

            if not errors:
                self.options[CONF_IP_ADDRESS] = user_input[CONF_IP_ADDRESS]
                self.options[CONF_PORT] = user_input[CONF_PORT]
                return await self.async_step_bridge_credentials()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_IP_ADDRESS, default=self.options[CONF_IP_ADDRESS]
                    ): cv.string,
                    vol.Required(CONF_PORT, default=self.options[CONF_PORT]): cv.port,
                }
            ),
            errors=errors,
        )

    async def async_step_bridge_credentials(self, user_input=None):
        """Handle the credentials step."""
        errors = {}
        if user_input is not None:
            try:
                bridge_data = {
                    CONF_IP_ADDRESS: self.options[CONF_IP_ADDRESS],
                    CONF_PORT: self.options[CONF_PORT],
                    CONF_GET_USERNAME: user_input[CONF_GET_USERNAME],
                    CONF_GET_PASSWORD: user_input[CONF_GET_PASSWORD],
                    CONF_PUT_USERNAME: user_input[CONF_PUT_USERNAME],
                    CONF_PUT_PASSWORD: user_input[CONF_PUT_PASSWORD],
                    CONF_WS_USERNAME: user_input[CONF_WS_USERNAME],
                    CONF_WS_PASSWORD: user_input[CONF_WS_PASSWORD],
                }

                _spc_data = await test_connection(self.hass, bridge_data)
                if not _spc_data:
                    raise CannotConnect

                _panel_serial = _spc_data["panel"].get("serial")
                if not _panel_serial:
                    raise CannotConnect

                await self.async_set_unique_id(_panel_serial)
                self._abort_if_unique_id_configured()

            except CannotConnect:
                errors["base"] = "cannot_connect"

            if not errors:
                self.options.update(bridge_data)
                self.spc_data = _spc_data
                return await self.async_step_discovered()

        return self.async_show_form(
            step_id="bridge_credentials",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_GET_USERNAME, default=self.options[CONF_GET_USERNAME]
                    ): cv.string,
                    vol.Required(
                        CONF_GET_PASSWORD, default=self.options[CONF_GET_PASSWORD]
                    ): cv.string,
                    vol.Required(
                        CONF_PUT_USERNAME, default=self.options[CONF_PUT_USERNAME]
                    ): cv.string,
                    vol.Required(
                        CONF_PUT_PASSWORD, default=self.options[CONF_PUT_PASSWORD]
                    ): cv.string,
                    vol.Required(
                        CONF_WS_USERNAME, default=self.options[CONF_WS_USERNAME]
                    ): cv.string,
                    vol.Required(
                        CONF_WS_PASSWORD, default=self.options[CONF_WS_PASSWORD]
                    ): cv.string,
                }
            ),
            errors=errors,
        )

    async def async_step_discovered(self, user_input=None):
        """Handle the discovered step."""
        errors = {}
        if user_input is not None:
            if not errors:
                return await self.async_step_user_identify_method()

        return self.async_show_form(
            step_id="discovered",
            data_schema=None,
            errors=errors,
            description_placeholders={
                "html": generate_html("discovered", self.spc_data)
            },
        )

    async def async_step_user_identify_method(self, user_input=None):
        """Handle user identify method step."""
        errors = {}
        if user_input is not None:
            if not errors:
                self.options[CONF_USER_IDENTIFY_METHOD] = user_input[
                    CONF_USER_IDENTIFY_METHOD
                ]
                self.options[CONF_USERS_DATA] = {}
                if self.options[CONF_USER_IDENTIFY_METHOD] == CONF_USER_IDENTIFY_BY_ID:
                    return await self.async_step_alarm_areas()
                else:
                    return await self.async_step_spc_users()

        return self.async_show_form(
            step_id="user_identify_method",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_USER_IDENTIFY_METHOD, default=CONF_USER_IDENTIFY_BY_ID
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=[
                                {
                                    "value": CONF_USER_IDENTIFY_BY_ID,
                                    "label": "Include SPC User ID in keypad code",
                                },
                                {
                                    "value": CONF_USER_IDENTIFY_BY_MAP,
                                    "label": "Link keypad codes to SPC users",
                                },
                            ]
                        )
                    )
                }
            ),
            errors=errors,
        )

    async def async_step_spc_users(self, user_input=None):
        """Handle SPC users step."""
        errors = {}
        if user_input is not None:
            if not errors:
                users_data = {}
                for user in self.spc_data["users"]:
                    ud = {
                        "id": user.id,
                        "name": user.get("name"),
                        "ha_pincode": user_input.get(f"pincode_{user.id}", ""),
                        "spc_password": user_input.get(f"password_{user.id}", ""),
                    }
                    users_data[str(user.id)] = ud

                errors = validate_spc_users_data(users_data)
                if not errors:
                    self.options[CONF_USERS_DATA] = users_data
                    return await self.async_step_alarm_areas()
                else:
                    return self.async_show_form(
                        step_id="spc_users",
                        data_schema=generate_option_schema("spc_users", users_data),
                        errors=errors,
                    )

        return self.async_show_form(
            step_id="spc_users",
            data_schema=generate_schema("spc_users", self.spc_data.get("users")),
            errors=errors,
        )

    async def async_step_alarm_areas(self, user_input=None):
        """Handle the alarm areas select step."""
        errors = {}
        if user_input is not None:
            for area in self.spc_data["areas"]:
                if f"area_{area["id"]}" in user_input["include_areas"]:
                    area["include_mode"] = "include"
                else:
                    area["include_mode"] = "exclude"
                self.options[CONF_AREAS_INCLUDE_DATA][str(area["id"])] = area[
                    "include_mode"
                ]

            if not errors:
                return await self.async_step_alarm_zones()

        return self.async_show_form(
            step_id="alarm_areas",
            data_schema=generate_schema("alarm_areas", self.spc_data.get("areas")),
            errors=errors,
        )

    async def async_step_alarm_zones(self, user_input=None):
        """Handle the alarm zones select step."""
        errors = {}
        if user_input is not None:
            for zone in self.spc_data["zones"]:
                zone["include_mode"] = user_input.get(
                    f"include_{zone["id"]}", "exclude"
                )
                self.options[CONF_ZONES_INCLUDE_DATA][str(zone["id"])] = zone[
                    "include_mode"
                ]

            if not errors:
                return await self.async_step_outputs()

        return self.async_show_form(
            step_id="alarm_zones",
            data_schema=generate_schema("alarm_zones", self.spc_data.get("zones")),
            errors=errors,
        )

    async def async_step_outputs(self, user_input=None):
        """Handle the outputs select step."""
        errors = {}
        if user_input is not None:
            for output in self.spc_data["outputs"]:
                if f"output_{output["id"]}" in user_input["include_outputs"]:
                    output["include_mode"] = "include"
                else:
                    output["include_mode"] = "exclude"
                self.options[CONF_OUTPUTS_INCLUDE_DATA][str(output["id"])] = output[
                    "include_mode"
                ]

            if not errors:
                return await self.async_step_doors()

        return self.async_show_form(
            step_id="outputs",
            data_schema=generate_schema("outputs", self.spc_data.get("outputs")),
            errors=errors,
        )

    async def async_step_doors(self, user_input=None):
        """Handle the door locks select step."""
        errors = {}
        if user_input is not None:
            for door in self.spc_data["doors"]:
                if f"door_{door["id"]}" in user_input["include_doors"]:
                    door["include_mode"] = "include"
                else:
                    door["include_mode"] = "exclude"
                self.options[CONF_DOORS_INCLUDE_DATA][str(door["id"])] = door[
                    "include_mode"
                ]

            if not errors:
                return await self.async_step_confirm()

        return self.async_show_form(
            step_id="doors",
            data_schema=generate_schema("doors", self.spc_data.get("doors")),
            errors=errors,
        )

    async def async_step_confirm(self, user_input=None):
        """Handle the confirm step."""
        errors = {}
        if user_input is not None:
            if not errors:
                return self.async_create_entry(
                    title=f"SPC Bridge [{self.spc_data["panel"].get("serial")}]",
                    data=self.data,
                    options=self.options,
                )

        return self.async_show_form(
            step_id="confirm",
            data_schema=None,
            errors=errors,
            description_placeholders={"html": generate_html("confirm", self.spc_data)},
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle a option flow for SPC."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry
        self.config_data = config_entry.data

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        return self.async_show_menu(
            step_id="init",
            menu_options=[
                "option_user_identify_method",
                "option_bridge",
                "option_alarm_areas",
                "option_alarm_zones",
                "option_outputs",
                "option_doors",
            ],
        )

    async def async_step_option_user_identify_method(self, user_input=None):
        """Handle the user identify method option step."""
        if user_input is not None:
            if user_input[CONF_USER_IDENTIFY_METHOD] == CONF_USER_IDENTIFY_BY_ID:
                options = deepcopy({**self.config_entry.options})
                options.update(user_input)
                options[CONF_USERS_DATA] = {}
                return self.async_create_entry(title="", data=options)
            else:
                return await self.async_step_option_spc_users()

        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_USER_IDENTIFY_METHOD,
                    default=self.config_entry.options.get(
                        CONF_USER_IDENTIFY_METHOD, CONF_USER_IDENTIFY_BY_ID
                    ),
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=[
                            {
                                "value": CONF_USER_IDENTIFY_BY_ID,
                                "label": "Include the SPC User ID in the Keypad Code",
                            },
                            {
                                "value": CONF_USER_IDENTIFY_BY_MAP,
                                "label": "Link Keypad Codes to SPC users",
                            },
                        ]
                    )
                )
            }
        )

        return self.async_show_form(
            step_id="option_user_identify_method",
            data_schema=data_schema,
            errors={},
        )

    async def async_step_option_spc_users(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the spc users option step."""
        spc = self.hass.data[DOMAIN][self.config_entry.entry_id]
        errors = {}
        if user_input is not None:
            users_data = {}
            for user in spc.users.values():
                d = {"id": user.id, "name": user.name}
                d["ha_pincode"] = user_input.get(f"pincode_{user.id}", "")
                d["spc_password"] = user_input.get(f"password_{user.id}", "")
                users_data[str(user.id)] = d

            errors = validate_spc_users_data(users_data)
            if not errors:
                options = deepcopy({**self.config_entry.options})
                options[CONF_USER_IDENTIFY_METHOD] = CONF_USER_IDENTIFY_BY_MAP
                options[CONF_USERS_DATA] = users_data
                return self.async_create_entry(title="", data=options)
            else:
                return self.async_show_form(
                    step_id="option_spc_users",
                    data_schema=generate_option_schema("spc_users", users_data),
                    errors=errors,
                )

        _users_data = self.config_entry.options[CONF_USERS_DATA]
        users_data = {}
        for user in spc.users.values():
            d = {"id": user.id, "name": user.name}
            if ud := _users_data.get(str(user.id)):
                d["ha_pincode"] = ud.get("ha_pincode", "")
                d["spc_password"] = ud.get("spc_password", "")
            else:
                d["ha_pincode"] = ""
                d["spc_password"] = ""
            users_data[str(user.id)] = d

        return self.async_show_form(
            step_id="option_spc_users",
            data_schema=generate_option_schema("spc_users", users_data),
            errors=errors,
        )

    async def async_step_option_bridge(self, user_input=None):
        """Handle the bridge option step."""
        errors = {}
        default_ip_address = self.config_entry.options[CONF_IP_ADDRESS]

        if user_input is not None:
            try:
                ipaddress.ip_address(user_input[CONF_IP_ADDRESS])
            except ValueError:
                errors[CONF_IP_ADDRESS] = "invalid_ip_address"
                default_ip_address = user_input[CONF_IP_ADDRESS]

            if not errors:
                self.bridge_data = user_input
                return await self.async_step_option_bridge_credentials()

        return self.async_show_form(
            step_id="option_bridge",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_IP_ADDRESS, default=default_ip_address
                    ): cv.string,
                    vol.Required(
                        CONF_PORT, default=self.config_entry.options[CONF_PORT]
                    ): cv.port,
                }
            ),
            errors=errors,
        )

    async def async_step_option_bridge_credentials(self, user_input=None):
        """Handle the bridge credentials option step."""
        errors = {}
        default_values = {
            CONF_GET_USERNAME: self.config_entry.options[CONF_GET_USERNAME],
            CONF_GET_PASSWORD: self.config_entry.options[CONF_GET_PASSWORD],
            CONF_PUT_USERNAME: self.config_entry.options[CONF_PUT_USERNAME],
            CONF_PUT_PASSWORD: self.config_entry.options[CONF_PUT_PASSWORD],
            CONF_WS_USERNAME: self.config_entry.options[CONF_WS_USERNAME],
            CONF_WS_PASSWORD: self.config_entry.options[CONF_WS_PASSWORD],
        }

        if user_input is not None:
            try:
                default_values.update(user_input)
                self.bridge_data.update(user_input)
                _spc_data = await test_connection(self.hass, self.bridge_data)
                if _spc_data is None or _spc_data.get("panel") is None:
                    raise CannotConnect

                _panel_serial = _spc_data["panel"].get("serial")
                if (
                    _panel_serial is None
                    or _panel_serial != self.config_entry.unique_id
                ):
                    raise CannotConnect

            except CannotConnect:
                errors["base"] = "cannot_connect"

            if not errors:
                options = deepcopy({**self.config_entry.options})
                options.update(self.bridge_data)
                return self.async_create_entry(title="", data=options)

        return self.async_show_form(
            step_id="option_bridge_credentials",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_GET_USERNAME, default=default_values[CONF_GET_USERNAME]
                    ): cv.string,
                    vol.Required(
                        CONF_GET_PASSWORD, default=default_values[CONF_GET_PASSWORD]
                    ): cv.string,
                    vol.Required(
                        CONF_PUT_USERNAME, default=default_values[CONF_PUT_USERNAME]
                    ): cv.string,
                    vol.Required(
                        CONF_PUT_PASSWORD, default=default_values[CONF_PUT_PASSWORD]
                    ): cv.string,
                    vol.Required(
                        CONF_WS_USERNAME, default=default_values[CONF_WS_USERNAME]
                    ): cv.string,
                    vol.Required(
                        CONF_WS_PASSWORD, default=default_values[CONF_WS_PASSWORD]
                    ): cv.string,
                }
            ),
            errors=errors,
        )

    async def async_step_option_alarm_areas(self, user_input=None):
        """Handle the alarm areas option step."""
        spc = self.hass.data[DOMAIN][self.config_entry.entry_id]
        if user_input is not None:
            options = deepcopy({**self.config_entry.options})
            for area in spc.areas.values():
                if f"area_{area.id}" in user_input["include_areas"]:
                    options[CONF_AREAS_INCLUDE_DATA][str(area.id)] = "include"
                else:
                    options[CONF_AREAS_INCLUDE_DATA][str(area.id)] = "exclude"
            return self.async_create_entry(title="", data=options)

        areas_data = {}
        options = self.config_entry.options
        for area in spc.areas.values():
            d = {
                "id": area.id,
                "name": area.name,
            }
            if options[CONF_AREAS_INCLUDE_DATA].get(str(area.id), "") == "include":
                d["include"] = True
            else:
                d["include"] = False

            areas_data[str(area.id)] = d

        return self.async_show_form(
            step_id="option_alarm_areas",
            data_schema=generate_option_schema("alarm_areas", areas_data),
            errors={},
        )

    async def async_step_option_alarm_zones(self, user_input=None):
        """Handle the alarm zones option step."""
        spc = self.hass.data[DOMAIN][self.config_entry.entry_id]
        if user_input is not None:
            options = deepcopy({**self.config_entry.options})
            for zone in spc.zones.values():
                if mode := user_input.get(f"include_{zone.id}"):
                    options[CONF_ZONES_INCLUDE_DATA][str(zone.id)] = mode
                else:
                    options[CONF_ZONES_INCLUDE_DATA][str(zone.id)] = "exclude"
            return self.async_create_entry(title="", data=options)

        zones_data = {}
        options = self.config_entry.options
        for zone in spc.zones.values():
            d = {
                "id": zone.id,
                "name": zone.name,
            }
            if mode := options[CONF_ZONES_INCLUDE_DATA].get(str(zone.id)):
                d["include"] = mode
            else:
                d["include"] = "exclude"

            zones_data[str(zone.id)] = d

        return self.async_show_form(
            step_id="option_alarm_zones",
            data_schema=generate_option_schema("alarm_zones", zones_data),
            errors={},
        )

    async def async_step_option_outputs(self, user_input=None):
        """Handle the outputs option step."""
        spc = self.hass.data[DOMAIN][self.config_entry.entry_id]
        if user_input is not None:
            options = deepcopy({**self.config_entry.options})
            for output in spc.outputs.values():
                if f"output_{output.id}" in user_input["include_outputs"]:
                    options[CONF_OUTPUTS_INCLUDE_DATA][str(output.id)] = "include"
                else:
                    options[CONF_OUTPUTS_INCLUDE_DATA][str(output.id)] = "exclude"
            return self.async_create_entry(title="", data=options)

        outputs_data = {}
        options = self.config_entry.options
        for output in spc.outputs.values():
            d = {
                "id": output.id,
                "name": output.name,
            }
            if options[CONF_OUTPUTS_INCLUDE_DATA].get(str(output.id), "") == "include":
                d["include"] = True
            else:
                d["include"] = False

            outputs_data[str(output.id)] = d

        return self.async_show_form(
            step_id="option_outputs",
            data_schema=generate_option_schema("outputs", outputs_data),
            errors={},
        )

    async def async_step_option_doors(self, user_input=None):
        """Handle the doors option step."""
        spc = self.hass.data[DOMAIN][self.config_entry.entry_id]
        if user_input is not None:
            options = deepcopy({**self.config_entry.options})
            for door in spc.doors.values():
                if f"door_{door.id}" in user_input["include_doors"]:
                    options[CONF_DOORS_INCLUDE_DATA][str(door.id)] = "include"
                else:
                    options[CONF_DOORS_INCLUDE_DATA][str(door.id)] = "exclude"
            return self.async_create_entry(title="", data=options)

        doors_data = {}
        options = self.config_entry.options
        for door in spc.doors.values():
            d = {
                "id": door.id,
                "name": door.name,
            }
            if options[CONF_DOORS_INCLUDE_DATA].get(str(door.id), "") == "include":
                d["include"] = True
            else:
                d["include"] = False

            doors_data[str(door.id)] = d

        return self.async_show_form(
            step_id="option_doors",
            data_schema=generate_option_schema("doors", doors_data),
            errors={},
        )


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidIpAddress(exceptions.HomeAssistantError):
    """Error to indicate there is an invalid ip address."""


class InvalidKeypadCode(exceptions.HomeAssistantError):
    """Error to indicate there is an invalid Keypad code."""


class InvalidUserPassword(exceptions.HomeAssistantError):
    """Error to indicate there is an invalid user password."""
