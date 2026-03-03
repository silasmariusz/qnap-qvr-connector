"""Camera platform for QNAP QVR Connector.

Copyright (c) 2026 Silas Mariusz.
Permission to copy/modify is granted for non-commercial use only.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.camera import Camera
from homeassistant.config_entries import ConfigEntry
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
    entities = [QVRCameraEntity(coordinator, client, cam) for cam in cameras]
    async_add_entities(entities)


class QVRCameraEntity(Camera):
    """Representation of a QVR camera."""

    def __init__(self, coordinator: QVRCoordinator, client: QVRProClient, camera: dict) -> None:
        super().__init__()
        self._coordinator = coordinator
        self._client = client
        self._camera = camera
        self._guid = camera.get("guid", "")
        self._name = camera.get("name", f"Camera {camera.get('channel_index', '?')}")
        self._attr_name = self._name
        self._attr_unique_id = f"qvr_{self._guid}"

    @property
    def device_info(self) -> dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, self._guid)},
            "name": self._name,
            "manufacturer": self._camera.get("brand", "QNAP"),
            "model": self._camera.get("model", "QVR Camera"),
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
