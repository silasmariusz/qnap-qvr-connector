"""Media Source support for QNAP QVR Connector.

Copyright (c) 2026 Silas Mariusz.
Permission to copy/modify is granted for non-commercial use only.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.media_source.error import BrowseError
from homeassistant.components.media_source.models import (
    BrowseMediaSource,
    MediaSource,
    MediaSourceItem,
    PlayMedia,
)
from homeassistant.core import HomeAssistant

from .const import DOMAIN


async def async_get_media_source(hass: HomeAssistant) -> MediaSource:
    """Return QVR media source implementation."""
    return QVRMediaSource(hass)


class QVRMediaSource(MediaSource):
    """Browse QVR events and resolve to recording proxy playback."""

    def __init__(self, hass: HomeAssistant) -> None:
        super().__init__(DOMAIN)
        self.hass = hass

    async def async_resolve_media(self, item: MediaSourceItem) -> PlayMedia:
        """Resolve media source identifier into a playable URL."""
        if not item.identifier:
            raise BrowseError("Missing media identifier")
        try:
            entry_id, guid, timestamp, stream = item.identifier.split("|")
            ts = int(timestamp)
            stream_id = int(stream)
        except (TypeError, ValueError) as err:
            raise BrowseError(f"Invalid media identifier: {item.identifier}") from err

        start = ts - 5000
        end = ts + 5000
        url = (
            f"/api/qnap_qvr_connector/recording/{entry_id}/{guid}/{stream_id}"
            f"?start={start}&end={end}"
        )
        return PlayMedia(url, "video/mp4")

    async def async_browse_media(self, item: MediaSourceItem) -> BrowseMediaSource:
        """Build Media Source tree: server -> camera -> events."""
        if item.identifier is None:
            return self._build_servers_directory()

        parts = item.identifier.split("|")
        if len(parts) == 1:
            return await self._build_cameras_directory(parts[0])
        if len(parts) == 2:
            return await self._build_events_directory(parts[0], parts[1])
        raise BrowseError("Unsupported media source level")

    def _build_servers_directory(self) -> BrowseMediaSource:
        """Build top-level directory with all configured QVR entries."""
        children: list[BrowseMediaSource] = []
        for entry_id in self.hass.data.get(DOMAIN, {}):
            entry = self.hass.config_entries.async_get_entry(entry_id)
            title = entry.title if entry else entry_id
            children.append(
                BrowseMediaSource(
                    domain=DOMAIN,
                    identifier=entry_id,
                    media_class="directory",
                    media_content_type="directory",
                    title=title,
                    can_play=False,
                    can_expand=True,
                )
            )
        return BrowseMediaSource(
            domain=DOMAIN,
            identifier=None,
            media_class="directory",
            media_content_type="directory",
            title="QVR Recordings",
            can_play=False,
            can_expand=True,
            children=children,
        )

    async def _build_cameras_directory(self, entry_id: str) -> BrowseMediaSource:
        """Build camera directory for one server."""
        data = self.hass.data.get(DOMAIN, {}).get(entry_id)
        if not data:
            raise BrowseError("Entry not found")
        coordinator = data.get("coordinator")
        cameras = coordinator.data.get("cameras", []) if coordinator else []
        children: list[BrowseMediaSource] = []
        for camera in cameras:
            guid = str(camera.get("guid", ""))
            if not guid:
                continue
            name = str(camera.get("name", guid))
            children.append(
                BrowseMediaSource(
                    domain=DOMAIN,
                    identifier=f"{entry_id}|{guid}",
                    media_class="directory",
                    media_content_type="directory",
                    title=name,
                    can_play=False,
                    can_expand=True,
                )
            )
        return BrowseMediaSource(
            domain=DOMAIN,
            identifier=entry_id,
            media_class="directory",
            media_content_type="directory",
            title="Cameras",
            can_play=False,
            can_expand=True,
            children=children,
        )

    async def _build_events_directory(self, entry_id: str, guid: str) -> BrowseMediaSource:
        """Build event nodes from surveillance logs for one camera."""
        data = self.hass.data.get(DOMAIN, {}).get(entry_id)
        if not data:
            raise BrowseError("Entry not found")
        client = data.get("client")
        if not client:
            raise BrowseError("Client not available")

        payload: dict[str, Any] = await client.get_logs(
            log_type=3,
            max_result=50,
            global_channel_id=guid,
        )
        items = payload.get("items", payload.get("item", []))
        children: list[BrowseMediaSource] = []
        for event in items:
            ts = event.get("UTC_time") or event.get("UTC_time_s")
            if ts is None:
                continue
            try:
                timestamp = int(ts)
            except (TypeError, ValueError):
                continue
            title_dt = datetime.fromtimestamp(timestamp / 1000).strftime("%Y-%m-%d %H:%M:%S")
            children.append(
                BrowseMediaSource(
                    domain=DOMAIN,
                    identifier=f"{entry_id}|{guid}|{timestamp}|0",
                    media_class="video",
                    media_content_type="video/mp4",
                    title=f"{title_dt} - {str(event.get('content', 'Event'))[:80]}",
                    can_play=True,
                    can_expand=False,
                )
            )
        return BrowseMediaSource(
            domain=DOMAIN,
            identifier=f"{entry_id}|{guid}",
            media_class="directory",
            media_content_type="directory",
            title="Events",
            can_play=False,
            can_expand=True,
            children=children,
        )
