"""Camera platform for QNAP QVR Connector.

Copyright (c) 2026 Silas Mariusz.
Permission to copy/modify is granted for non-commercial use only.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.camera import Camera
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from pyqvrpro_client import QVRProClient

from .const import DOMAIN
from .coordinator import QVRCoordinator

_LOGGER = logging.getLogger(__name__)


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
        stream_state = cam.get("stream_state", [])
        stream_ids: list[int] = []
        if isinstance(stream_state, list):
            for stream_info in stream_state:
                if isinstance(stream_info, dict) and isinstance(stream_info.get("stream"), int):
                    stream_ids.append(int(stream_info["stream"]))
        if not stream_ids:
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
        if self._stream_id == 0:
            self._attr_name = self._name
        elif self._stream_id == 1:
            self._attr_name = f"{self._name} Sub"
        else:
            self._attr_name = f"{self._name} Stream {self._stream_id + 1}"
        self._attr_unique_id = f"qvr_{self._guid}_stream_{self._stream_id}"

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

    async def async_stream_source(self) -> str | None:
        """Return a high-quality HLS source for HA stream worker."""
        try:
            return await self._client.get_live_stream_uri(
                self._guid,
                self._stream_id,
                protocol="hls",
            )
        except Exception as e:
            _LOGGER.warning(
                "HLS source failed for %s stream %s: %s",
                self._guid,
                self._stream_id,
                e,
            )
            return None
