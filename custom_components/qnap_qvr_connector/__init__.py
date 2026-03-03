"""QNAP QVR Connector integration.

Copyright (c) 2026 Silas Mariusz.
Permission to copy/modify is granted for non-commercial use only.
"""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_USERNAME,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from pyqvrpro_client import ApiAuthError, QVRProClient

from .const import (
    CONF_PORT_SSL,
    CONF_PREFIX,
    CONF_USE_SSL,
    CONF_VERIFY_SSL,
    DEFAULT_PORT,
    DEFAULT_PORT_SSL,
    DOMAIN,
    PLATFORMS,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up QNAP QVR Connector from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    host = entry.data[CONF_HOST]
    port = entry.data.get(CONF_PORT, DEFAULT_PORT)
    port_ssl = entry.data.get(CONF_PORT_SSL, DEFAULT_PORT_SSL)
    use_ssl = entry.data.get(CONF_USE_SSL, False)
    username = entry.data[CONF_USERNAME]
    password = entry.data[CONF_PASSWORD]
    prefix = entry.data.get(CONF_PREFIX, "qvrsurveillance")
    verify_ssl = entry.data.get(CONF_VERIFY_SSL, False)

    client = QVRProClient(
        host=host,
        port=port_ssl if use_ssl else port,
        user=username,
        password=password,
        use_ssl=use_ssl,
        prefix=prefix,
        verify_ssl=verify_ssl,
    )

    try:
        cameras = await client.get_cameras()
        _LOGGER.info("Connected to QVR: %d cameras", len(cameras))
    except ApiAuthError as err:
        # Bubble auth failures up to HA so reauth can be triggered.
        raise ConfigEntryAuthFailed from err

    from .coordinator import QVRCoordinator, QVREventsCoordinator

    coordinator = QVRCoordinator(hass, client, entry.entry_id)
    events_coordinator = QVREventsCoordinator(hass, client, entry.entry_id)
    await coordinator.async_config_entry_first_refresh()
    await events_coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = {
        "client": client,
        "cameras": cameras,
        "coordinator": coordinator,
        "events_coordinator": events_coordinator,
    }

    from .events_api import QVREventsView
    from .recording_proxy import QVRRecordingProxyView
    from .websocket_api import async_register_websocket_handlers

    hass.http.register_view(QVRRecordingProxyView())
    hass.http.register_view(QVREventsView())
    await async_register_websocket_handlers(hass)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        data = hass.data[DOMAIN].pop(entry.entry_id, None)
        if data and "client" in data:
            await data["client"].close()
    return unload_ok


async def async_reauth_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle reauth."""
    # Handled by config_flow async_step_reauth
    pass
