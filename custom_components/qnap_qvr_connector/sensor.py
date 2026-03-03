"""Sensor platform for QNAP QVR Connector - events and telemetry.

Copyright (c) 2026 Silas Mariusz.
Permission to copy/modify is granted for non-commercial use only.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import QVREventsCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up QVR sensors from config entry."""
    data = hass.data[DOMAIN].get(entry.entry_id)
    if not data:
        return
    coordinator = data.get("events_coordinator")
    if not coordinator:
        return
    entities: list[SensorEntity] = [QVREventsTotalSensor(coordinator, entry)]
    for event_type in sorted(coordinator.data.get("type_counts", {}).keys()):
        entities.append(QVRMetadataTypeSensor(coordinator, entry, event_type))
    async_add_entities(entities)


def _to_iso(ts_ms: int | str | None) -> str:
    """Convert timestamp in ms to ISO string."""
    if ts_ms is None:
        return ""
    try:
        return datetime.fromtimestamp(int(ts_ms) / 1000).isoformat()
    except (TypeError, ValueError):
        return str(ts_ms)


class QVREventsTotalSensor(CoordinatorEntity[QVREventsCoordinator], SensorEntity):
    """Sensor showing total metadata events in current horizon."""

    def __init__(self, coordinator: QVREventsCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._coordinator = coordinator
        self._entry = entry
        self._attr_name = "QVR Metadata Events"
        self._attr_unique_id = f"qvr_events_{entry.entry_id}"
        self._attr_icon = "mdi:database-search"

    @property
    def native_value(self) -> str:
        """Return count of metadata events."""
        data = self._coordinator.data
        items = data.get("items", [])
        return str(len(items))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return summary and latest events."""
        data = self._coordinator.data
        items = data.get("items", [])[:10]
        attrs: dict[str, Any] = {
            "source": data.get("source", "metadata"),
            "total_items": data.get("totalItems", 0),
            "type_counts": data.get("type_counts", {}),
        }
        last_events = []
        for evt in items:
            last_events.append(
                {
                    "type": evt.get("event_type", "unknown"),
                    "time": _to_iso(evt.get("UTC_time")),
                    "content": str(evt.get("content", ""))[:100],
                }
            )
        attrs["recent_events"] = last_events
        return attrs


class QVRMetadataTypeSensor(CoordinatorEntity[QVREventsCoordinator], SensorEntity):
    """Text sensor with latest event message for a single metadata type."""

    def __init__(
        self, coordinator: QVREventsCoordinator, entry: ConfigEntry, event_type: str
    ) -> None:
        super().__init__(coordinator)
        self._coordinator = coordinator
        self._entry = entry
        self._event_type = event_type
        pretty = event_type.replace("_", " ").title()
        self._attr_name = f"QVR {pretty} Event"
        self._attr_unique_id = f"qvr_event_type_{entry.entry_id}_{event_type}"
        self._attr_icon = "mdi:tag-text"

    @property
    def native_value(self) -> str:
        """Return latest event message for this event type."""
        latest = self._coordinator.data.get("latest_by_type", {}).get(self._event_type, {})
        return str(latest.get("content", ""))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return counters and last timestamp for this event type."""
        data = self._coordinator.data
        latest = data.get("latest_by_type", {}).get(self._event_type, {})
        return {
            "event_type": self._event_type,
            "count": data.get("type_counts", {}).get(self._event_type, 0),
            "last_time": _to_iso(latest.get("UTC_time")),
            "metadata_id": latest.get("metadata_id", ""),
        }
