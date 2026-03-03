"""Config flow for QNAP QVR Connector.

Copyright (c) 2026 Silas Mariusz.
Permission to copy/modify is granted for non-commercial use only.
"""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from pyqvrpro_client import ApiAuthError, QVRProClient
from pyqvrpro_client.discovery import get_interface_prefix, probe_discovery_endpoint

from .const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_PORT_SSL,
    CONF_PREFIX,
    CONF_USE_SSL,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
    API_DISCOVERY_PATH,
    DEFAULT_PORT,
    DEFAULT_PORT_SSL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


async def _try_probe(host: str, port: int, use_ssl: bool = False) -> dict:
    """Probe /qvrentry with fallback ports."""
    _LOGGER.debug("Starting topology probe via endpoint: %s", API_DISCOVERY_PATH)
    for p, ssl in [(port, use_ssl), (8080, False), (80, False), (443, True)]:
        try:
            # Discovery endpoint is unauthenticated and tells us SSL/prefix topology.
            return await probe_discovery_endpoint(host, p, use_ssl=ssl, verify_ssl=False)
        except Exception as e:
            _LOGGER.debug("Probe %s:%d failed: %s", host, p, e)
            continue
    raise CannotConnect("Could not connect to QVR")


async def _validate_auth(host: str, port: int, user: str, password: str, prefix: str) -> None:
    """Validate credentials and permissions."""
    client = QVRProClient(
        host=host,
        port=port,
        user=user,
        password=password,
        prefix=prefix,
        verify_ssl=False,
    )
    try:
        await client.get_cameras()
    except ApiAuthError as err:
        raise InvalidAuth from err
    finally:
        await client.close()


class QVRConnectorFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle QNAP QVR Connector config flow."""

    VERSION = 1

    def __init__(self) -> None:
        self._discovered_ip: str | None = None
        self._probe_data: dict | None = None

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        """Handle initial step."""
        errors = {}
        if user_input:
            host = user_input[CONF_HOST]
            port = int(user_input.get(CONF_PORT, DEFAULT_PORT))
            port_ssl = int(user_input.get(CONF_PORT_SSL, DEFAULT_PORT_SSL))
            use_ssl = user_input.get(CONF_USE_SSL, False)
            username = user_input[CONF_USERNAME]
            password = user_input[CONF_PASSWORD]

            try:
                probe = await _try_probe(host, port_ssl if use_ssl else port, use_ssl)
                prefix = get_interface_prefix(probe)
                if probe.get("force_ssl"):
                    use_ssl = True
                    port = int(probe.get("https_port", port_ssl))
                else:
                    port = int(probe.get("http_port", port))

                await _validate_auth(host, port, username, password, prefix)

                return self.async_create_entry(
                    title=f"QVR @ {host}",
                    data={
                        CONF_HOST: host,
                        CONF_PORT: port,
                        CONF_PORT_SSL: port_ssl,
                        CONF_USE_SSL: use_ssl,
                        CONF_USERNAME: username,
                        CONF_PASSWORD: password,
                        CONF_PREFIX: prefix,
                        CONF_VERIFY_SSL: False,
                    },
                )
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception as e:
                _LOGGER.exception("Unexpected error")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST): str,
                    vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
                    vol.Required(CONF_PORT_SSL, default=DEFAULT_PORT_SSL): int,
                    vol.Required(CONF_USE_SSL, default=False): bool,
                    vol.Required(CONF_USERNAME): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )

    async def async_step_reauth(self, entry_data: dict) -> FlowResult:
        """Handle reauth."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict | None = None) -> FlowResult:
        """Handle reauth confirm."""
        errors = {}
        if user_input:
            entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
            if not entry:
                return self.async_abort(reason="reauth_entry_missing")
            try:
                await _validate_auth(
                    entry.data[CONF_HOST],
                    entry.data[CONF_PORT_SSL] if entry.data.get(CONF_USE_SSL) else entry.data[CONF_PORT],
                    user_input[CONF_USERNAME],
                    user_input[CONF_PASSWORD],
                    entry.data.get(CONF_PREFIX, "qvrsurveillance"),
                )
                self.hass.config_entries.async_update_entry(
                    entry,
                    data={**entry.data, CONF_USERNAME: user_input[CONF_USERNAME], CONF_PASSWORD: user_input[CONF_PASSWORD]},
                )
                await self.hass.config_entries.async_reload(entry.entry_id)
                return self.async_abort(reason="reauth_successful")
            except InvalidAuth:
                errors["base"] = "invalid_auth"

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USERNAME): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
