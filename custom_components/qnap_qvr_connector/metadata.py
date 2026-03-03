"""Metadata Vault parsing helpers for QNAP QVR Connector.

Copyright (c) 2026 Silas Mariusz.
Permission to copy/modify is granted for non-commercial use only.
"""

from __future__ import annotations

from typing import Any


def extract_metadata_list(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract metadata event list from Metadata Vault response payload."""
    status = payload.get("ReturnStatus", {})
    extra = status.get("extra", {})
    items = extra.get("metadata_list", [])
    if isinstance(items, list):
        return [item for item in items if isinstance(item, dict)]
    return []


def _pick_text(payload: dict[str, Any], keys: list[str]) -> str:
    """Return first non-empty string-like value for any key."""
    for key in keys:
        value = payload.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def _pick_int(payload: dict[str, Any], keys: list[str]) -> int | None:
    """Return first key that can be parsed to int."""
    for key in keys:
        value = payload.get(key)
        if value is None:
            continue
        try:
            return int(str(value))
        except (TypeError, ValueError):
            continue
    return None


def normalize_metadata_event(event: dict[str, Any], index: int = 0) -> dict[str, Any]:
    """Normalize a metadata event into a timeline/sensor-friendly shape."""
    event_type = _pick_text(
        event,
        ["event_type", "event_name", "type", "object_type", "classification", "label"],
    ) or "unknown"

    content = _pick_text(
        event,
        ["content", "description", "message", "label", "event_name", "object_name"],
    ) or event_type

    ts = _pick_int(
        event,
        [
            "UTC_time",
            "UTC_time_s",
            "start_time_stamp",
            "start_time",
            "event_time",
            "timestamp",
            "time",
        ],
    )

    return {
        "event_type": event_type.lower(),
        "content": content,
        "UTC_time": ts or 0,
        "metadata_id": _pick_text(event, ["metadata_id", "id", "event_id", "uuid"])
        or f"metadata_{index}",
        "raw": event,
    }


def normalize_metadata_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Normalize Metadata Vault response into integration/common event shape."""
    metadata_items = extract_metadata_list(payload)
    items = [normalize_metadata_event(evt, idx) for idx, evt in enumerate(metadata_items)]
    items.sort(key=lambda item: int(item.get("UTC_time", 0)), reverse=True)

    type_counts: dict[str, int] = {}
    latest_by_type: dict[str, dict[str, Any]] = {}
    for item in items:
        event_type = str(item.get("event_type", "unknown"))
        type_counts[event_type] = type_counts.get(event_type, 0) + 1
        latest_by_type.setdefault(event_type, item)

    return {
        "source": "metadata",
        "items": items,
        "totalItems": len(items),
        "type_counts": type_counts,
        "latest_by_type": latest_by_type,
        "raw": payload,
    }
