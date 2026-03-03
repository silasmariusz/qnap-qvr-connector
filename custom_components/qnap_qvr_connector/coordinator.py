"""DataUpdateCoordinator for QNAP QVR Connector.

Copyright (c) 2026 Silas Mariusz.
Permission to copy/modify is granted for non-commercial use only.
"""

from __future__ import annotations

import logging
import time
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from pyqvrpro_client import ApiAuthError, QVRProClient

from .const import DOMAIN
from .metadata import normalize_metadata_payload

_LOGGER = logging.getLogger(__name__)


class QVRCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator for camera list and status."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: QVRProClient,
        entry_id: str,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=60),
        )
        self._client = client
        self._entry_id = entry_id

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            cameras = await self._client.get_cameras()
            return {"cameras": cameras}
        except ApiAuthError as err:
            # Keep coordinator alive and let HA mark entities unavailable.
            raise UpdateFailed("Authentication failed") from err


class QVREventsCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator for Metadata Vault events."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: QVRProClient,
        entry_id: str,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_events",
            update_interval=timedelta(seconds=120),
        )
        self._client = client
        self._entry_id = entry_id

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            # Keep a practical horizon for text sensors while avoiding huge payloads.
            end_time = int(time.time() * 1000)
            start_time = end_time - (24 * 3600 * 1000)
            payload = await self._client.get_metadata_events(
                start_time=start_time,
                end_time=end_time,
                max_result=100,
            )
            return normalize_metadata_payload(payload)
        except ApiAuthError as err:
            raise UpdateFailed("Authentication failed") from err
