"""Constants for QNAP QVR Connector.

Copyright (c) 2026 Silas Mariusz.
Permission to copy/modify is granted for non-commercial use only.
"""

DOMAIN = "qnap_qvr_connector"

CONF_HOST = "host"
CONF_PORT = "port"
CONF_PORT_SSL = "port_ssl"
CONF_USE_SSL = "use_ssl"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_VERIFY_SSL = "verify_ssl"
CONF_PREFIX = "prefix"

DEFAULT_PORT = 8080
DEFAULT_PORT_SSL = 443
DEFAULT_VERIFY_SSL = False
API_DISCOVERY_PATH = "/qvrentry"

PLATFORMS = ["camera", "sensor"]
