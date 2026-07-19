"""Diagnostics support for ista EcoTrend."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_URL, DOMAIN
from .coordinator import IstaDataUpdateCoordinator


def _czech_diagnostics(data: Any) -> dict[str, Any]:
    """Return a privacy-safe summary of Czech account data."""
    if not isinstance(data, dict):
        return {"meter_count": 0, "meter_types": [], "aggregates": {}}

    meters = data.get("meters")
    meter_items = meters if isinstance(meters, list) else []
    meter_types = sorted(
        {str(meter["type"]) for meter in meter_items if isinstance(meter, dict) and meter.get("type") is not None}
    )

    aggregate_summary: dict[str, dict[str, Any]] = {}
    aggregates = data.get("aggregates")
    if isinstance(aggregates, dict):
        for consumption_type, aggregate in aggregates.items():
            if not isinstance(consumption_type, str) or not isinstance(aggregate, dict):
                continue
            daily = aggregate.get("daily")
            monthly = aggregate.get("monthly")
            aggregate_summary[consumption_type] = {
                "unit": aggregate.get("unit"),
                "daily_reading_count": len(daily) if isinstance(daily, list) else 0,
                "monthly_reading_count": len(monthly) if isinstance(monthly, list) else 0,
                "has_latest_daily_value": aggregate.get("daily_value") is not None,
                "has_latest_monthly_value": aggregate.get("monthly_value") is not None,
            }

    return {
        "meter_count": len(meter_items),
        "meter_types": meter_types,
        "aggregates": aggregate_summary,
    }


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator: IstaDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    if entry.options.get(CONF_URL) == "cz_url":
        return _czech_diagnostics(coordinator.data)
    return coordinator.data
