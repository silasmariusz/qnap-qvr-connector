"""HTTP view for proxying QVR recordings to frontend.

Copyright (c) 2026 Silas Mariusz.
Permission to copy/modify is granted for non-commercial use only.
"""

from __future__ import annotations

import logging

from aiohttp import web

from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class QVRRecordingProxyView(HomeAssistantView):
    """Proxy recording requests to QVR (requires auth)."""

    url = "/api/qnap_qvr_connector/recording/{entry_id}/{guid}/{stream}"
    name = "api:qnap_qvr_connector:recording"

    async def get(self, request: web.Request) -> web.StreamResponse:
        """Stream recording from QVR."""
        match = request.match_info
        entry_id = match.get("entry_id", "")
        guid = match.get("guid", "")
        stream = match.get("stream", "0")
        start = request.query.get("start")
        end = request.query.get("end")
        if not start or not end:
            return web.Response(status=400, text="Missing start/end params (milliseconds)")
        try:
            start_ms = int(start)
            end_ms = int(end)
        except ValueError:
            return web.Response(status=400, text="Invalid start/end")
        try:
            stream_id = int(stream)
        except ValueError:
            stream_id = 0

        hass: HomeAssistant = request.app["hass"]
        data = hass.data.get(DOMAIN, {}).get(entry_id)
        if not data:
            return web.Response(status=404, text="Entry not found")
        client = data.get("client")
        if not client:
            return web.Response(status=404, text="Client not found")

        try:
            recording = await client.get_recording(
                guid, stream_id, start_time=start_ms, end_time=end_ms
            )
        except Exception as e:
            _LOGGER.exception("Recording proxy failed: %s", e)
            return web.Response(status=502, text=str(e))

        return web.Response(
            body=recording,
            content_type="video/mp4",
            headers={"Content-Disposition": "inline"},
        )
