"""REST API for events - used by Advanced Camera Card.

Copyright (c) 2026 Silas Mariusz.
Permission to copy/modify is granted for non-commercial use only.
"""

from __future__ import annotations

import logging
from aiohttp import web

from homeassistant.components.http import HomeAssistantView

from .const import DOMAIN
from .metadata import normalize_metadata_payload

_LOGGER = logging.getLogger(__name__)


class QVREventsView(HomeAssistantView):
    """GET /api/qnap_qvr_connector/events - returns JSON events for card."""

    url = "/api/qnap_qvr_connector/events"
    name = "api:qnap_qvr_connector:events"

    async def get(self, request: web.Request) -> web.Response:
        """Return Metadata Vault events as JSON."""
        hass = request.app["hass"]
        entry_id = request.query.get("entry_id")
        if not entry_id:
            return web.json_response({"error": "entry_id required"}, status=400)
        data = hass.data.get(DOMAIN, {}).get(entry_id)
        if not data:
            return web.json_response({"error": "Entry not found"}, status=404)
        client = data.get("client")
        if not client:
            return web.json_response({"error": "Client not available"}, status=503)
        try:
            start = int(request.query.get("start_time", 0))
            end = int(request.query.get("end_time", 0))
            max_result = int(request.query.get("max_result", 100))
        except (TypeError, ValueError):
            return web.json_response(
                {"error": "Invalid start_time, end_time or max_result"},
                status=400,
            )
        camera_guid = request.query.get("camera_guid")
        source = request.query.get("source", "auto")
        try:
            payload = await client.get_metadata_events(
                start_time=start,
                end_time=end,
                max_result=max_result,
                global_channel_id=camera_guid,
            )
            normalized = normalize_metadata_payload(payload)

            if source != "metadata" and normalized.get("totalItems", 0) == 0:
                logs = await client.get_logs(
                    log_type=3,
                    max_result=max_result,
                    start_time=start,
                    end_time=end,
                    global_channel_id=camera_guid,
                )
                return web.json_response(logs)

            return web.json_response(normalized)
        except Exception as e:
            _LOGGER.exception("Events API failed: %s", e)
            return web.json_response({"error": str(e)}, status=500)
