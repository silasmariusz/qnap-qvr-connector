"""WebSocket API for QNAP QVR Connector - used by Advanced Camera Card.

Copyright (c) 2026 Silas Mariusz.
Permission to copy/modify is granted for non-commercial use only.
"""

from __future__ import annotations

import logging
import time
from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .metadata import normalize_metadata_payload

_LOGGER = logging.getLogger(__name__)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "qnap_qvr_connector/events",
        vol.Required("entry_id"): str,
        vol.Optional("start_time"): int,
        vol.Optional("end_time"): int,
        vol.Optional("max_result", default=50): int,
        vol.Optional("camera_guid"): str,
        vol.Optional("source", default="auto"): str,
    }
)
@websocket_api.async_response
async def ws_events(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Return Metadata Vault events for timeline."""
    entry_id = msg["entry_id"]
    data = hass.data.get(DOMAIN, {}).get(entry_id)
    if not data:
        connection.send_error(msg["id"], "not_found", "Entry not found")
        return
    client = data.get("client")
    if not client:
        connection.send_error(msg["id"], "no_client", "Client not available")
        return
    try:
        start_time = msg.get("start_time") or 0
        end_time = msg.get("end_time") or 0
        if end_time <= 0 or start_time <= 0 or end_time <= start_time:
            end_time = int(time.time() * 1000)
            start_time = end_time - (24 * 60 * 60 * 1000)
        payload = await client.get_metadata_events(
            start_time=start_time,
            end_time=end_time,
            max_result=msg.get("max_result", 50),
            global_channel_id=msg.get("camera_guid"),
        )
        normalized = normalize_metadata_payload(payload)
        if msg.get("source", "auto") != "metadata" and normalized.get("totalItems", 0) == 0:
            logs = await client.get_logs(
                log_type=3,
                max_result=msg.get("max_result", 50),
                start_time=start_time,
                end_time=end_time,
                global_channel_id=msg.get("camera_guid"),
            )
            connection.send_result(msg["id"], logs)
            return
        connection.send_result(msg["id"], normalized)
    except Exception as e:
        _LOGGER.exception("WebSocket events failed: %s", e)
        connection.send_error(msg["id"], "error", str(e))


@websocket_api.websocket_command(
    {
        vol.Required("type"): "qnap_qvr_connector/recording_url",
        vol.Required("entry_id"): str,
        vol.Required("guid"): str,
        vol.Required("start"): int,
        vol.Required("end"): int,
        vol.Optional("stream", default=0): int,
    }
)
@websocket_api.async_response
async def ws_recording_url(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Return proxy URL for recording playback."""
    entry_id = msg["entry_id"]
    base = hass.config.api.base_url or ""
    url = f"{base}/api/qnap_qvr_connector/recording/{entry_id}/{msg['guid']}/{msg.get('stream', 0)}?start={msg['start']}&end={msg['end']}"
    connection.send_result(msg["id"], {"url": url})


async def async_register_websocket_handlers(hass: HomeAssistant) -> None:
    """Register WebSocket commands."""
    websocket_api.async_register_command(hass, ws_events)
    websocket_api.async_register_command(hass, ws_recording_url)
