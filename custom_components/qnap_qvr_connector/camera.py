"""Camera platform for QNAP QVR Connector.

Copyright (c) 2026 Silas Mariusz.
Permission to copy/modify is granted for non-commercial use only.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.camera import Camera, CameraEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from pyqvrpro_client import QVRProClient

from .const import DOMAIN
from .coordinator import QVRCoordinator

_LOGGER = logging.getLogger(__name__)
def _extract_stream_ids_from_defs(stream_defs: list[dict[str, Any]]) -> list[int]:
    """Return stream ids reported by QVR stream definitions."""
    stream_ids: list[int] = []
    for stream_info in stream_defs:
        if not isinstance(stream_info, dict):
            continue
        stream = stream_info.get("stream")
        if not isinstance(stream, int):
            continue
        stream_ids.append(stream)
    return sorted(set(stream_ids))


def _extract_stream_ids_from_camera_payload(camera: dict[str, Any]) -> list[int]:
    """Fallback extraction from /camera/list payload."""
    stream_state = camera.get("stream_state", [])
    stream_defs = [item for item in stream_state if isinstance(item, dict)]
    return _extract_stream_ids_from_defs(stream_defs)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up QVR cameras from config entry."""
    data = hass.data[DOMAIN].get(entry.entry_id)
    if not data:
        return
    client: QVRProClient = data["client"]
    coordinator = data.get("coordinator")
    if not coordinator:
        return
    cameras = coordinator.data.get("cameras", [])
    entities: list[QVRCameraEntity] = []
    for cam in cameras:
        stream_ids: list[int] = []
        guid = cam.get("guid")
        stream_defs: list[dict[str, Any]] = []
        if isinstance(guid, str) and guid:
            try:
                stream_defs = await client.get_streams(guid)
                stream_ids = _extract_stream_ids_from_defs(stream_defs)
            except Exception as err:
                _LOGGER.debug("Stream discovery failed for %s: %s", guid, err)
        if not stream_ids:
            stream_ids = _extract_stream_ids_from_camera_payload(cam)

        # Resolve and deduplicate by effective source URL to avoid stream_2/3 mirroring stream_1.
        if isinstance(guid, str) and guid and stream_ids:
            unique_stream_ids: list[int] = []
            seen_sources: set[str] = set()
            for stream_id in stream_ids:
                source_url: str | None = None
                for protocol in ("hls", "rtsp"):
                    try:
                        source_url = await client.get_live_stream_uri(guid, stream_id, protocol=protocol)
                        break
                    except Exception:
                        continue
                if source_url:
                    if source_url in seen_sources:
                        continue
                    seen_sources.add(source_url)
                    unique_stream_ids.append(stream_id)
            if unique_stream_ids:
                stream_ids = unique_stream_ids

        if not stream_ids:
            # Safe fallback for cameras exposing only one stream.
            stream_ids = [0]
        for stream_id in sorted(set(stream_ids)):
            entities.append(QVRCameraEntity(coordinator, client, entry, cam, stream_id))
    async_add_entities(entities)


class QVRCameraEntity(Camera):
    """Representation of a QVR camera."""

    def __init__(
        self,
        coordinator: QVRCoordinator,
        client: QVRProClient,
        entry: ConfigEntry,
        camera: dict,
        stream_id: int,
    ) -> None:
        super().__init__()
        self._coordinator = coordinator
        self._client = client
        self._entry = entry
        self._camera = camera
        self._stream_id = stream_id
        self._guid = camera.get("guid", "")
        self._name = camera.get("name", f"Camera {camera.get('channel_index', '?')}")
        stream_number = self._stream_id + 1
        # Keep predictable entity naming for users and dashboards.
        self._attr_name = f"{self._name} stream {stream_number}"
        self._attr_unique_id = f"qvr_{self._guid}_stream_{stream_number}"
        self._attr_supported_features = CameraEntityFeature.STREAM

    @property
    def device_info(self) -> dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, self._guid)},
            "name": self._name,
            "manufacturer": self._camera.get("brand", "QNAP"),
            "model": self._camera.get("model", "QVR Camera"),
        }

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose QVR mapping and stream metadata for ACC auto-binding."""
        return {
            "qvr_entry_id": self._entry.entry_id,
            "qvr_guid": self._guid,
            "qvr_stream": self._stream_id,
            "qvr_stream_number": self._stream_id + 1,
            "qvr_host": self._entry.data.get(CONF_HOST),
        }

    async def async_camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:
        """Return bytes of camera image."""
        # CameraEntity pulls fresh snapshots directly from QVR on demand.
        try:
            return await self._client.get_snapshot(self._guid)
        except Exception as e:
            _LOGGER.error("Snapshot failed for %s: %s", self._guid, e)
            return None

    async def stream_source(self) -> str | None:
        """Return a stream URL for Home Assistant camera.play_stream."""
        requested_stream = self._stream_id

        async def _resolve_stream_url(stream_id: int) -> str | None:
            """Resolve HLS-first then RTSP for one stream id."""
            try:
                return await self._client.get_live_stream_uri(
                    self._guid,
                    stream_id,
                    protocol="hls",
                )
            except Exception as e:
                _LOGGER.warning(
                    "HLS source failed for %s stream %s: %s",
                    self._guid,
                    stream_id,
                    e,
                )
            try:
                return await self._client.get_live_stream_uri(
                    self._guid,
                    stream_id,
                    protocol="rtsp",
                )
            except Exception as e:
                _LOGGER.warning(
                    "RTSP fallback source failed for %s stream %s: %s",
                    self._guid,
                    stream_id,
                    e,
                )
                return None

        source = await _resolve_stream_url(requested_stream)
        if source:
            return source

        # If sub-stream cannot be opened, fallback to main stream to avoid play_stream errors.
        if requested_stream != 0:
            return await _resolve_stream_url(0)
        return None
