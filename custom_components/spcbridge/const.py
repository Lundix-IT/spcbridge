"""Define constants for the SPC component."""

import logging

LOGGER = logging.getLogger(__package__)

DOMAIN = "spcbridge"

CONF_SECURE_COM = "secure_com"
CONF_GET_USERNAME = "get_username"
CONF_GET_PASSWORD = "get_password"
CONF_PUT_USERNAME = "put_username"
CONF_PUT_PASSWORD = "put_password"
CONF_WS_USERNAME = "ws_username"
CONF_WS_PASSWORD = "ws_password"
CONF_USERS_DATA = "users_data"
CONF_AREAS_INCLUDE_DATA = "areas_include_data"
CONF_ZONES_INCLUDE_DATA = "zones_include_data"
CONF_OUTPUTS_INCLUDE_DATA = "outputs_include_data"
CONF_DOORS_INCLUDE_DATA = "doors_include_data"

CONF_USER_IDENTIFY_METHOD = "user_identify_method"
CONF_USER_IDENTIFY_BY_ID = "user_identify_by_id"
CONF_USER_IDENTIFY_BY_MAP = "user_identify_by_map"

DEFAULT_BRIDGE_PORT = 8088
DEFAULT_BRIDGE_GET_USERNAME = "get_user"
DEFAULT_BRIDGE_GET_PASSWORD = "get_pwd"
DEFAULT_BRIDGE_PUT_USERNAME = "put_user"
DEFAULT_BRIDGE_PUT_PASSWORD = "put_pwd"
DEFAULT_BRIDGE_WS_USERNAME = "ws_user"
DEFAULT_BRIDGE_WS_PASSWORD = "ws_pwd"
DEFAULT_CONF_CODE = ""

ATTR_ENTRY_DELAY_AWAY = "entry_delay_away"
ATTR_ENTRY_DELAY_HOME = "entry_delay_home"
ATTR_EXIT_DELAY_AWAY = "exit_delay_away"
ATTR_EXIT_DELAY_HOME = "exit_delay_home"

ATTR_COMMAND = "command"
