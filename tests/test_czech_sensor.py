"""Tests for Czech ista sensor entities."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from custom_components.ecotrend_ista.czech_sensor import (
    CzechAggregateSensor,
    CzechPhysicalMeterSensor,
    create_czech_sensor_entities,
)
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass


class DummyController:
    """Expose stable account metadata for entity creation."""

    def get_support_code(self) -> str:
        """Return the account identifier."""
        return "cz-42"

    def get_uuids(self) -> list[str]:
        """Return the account UUID fallback."""
        return ["cz-42"]

    def get_version(self) -> str:
        """Return a display version."""
        return "CZ Nordic 3.2.1"


class DummyCoordinator:
    """Hold the Czech payload used by coordinator entities."""

    def __init__(self, payload: dict[str, Any]) -> None:
        """Initialize coordinator state."""
        self.controller = DummyController()
        self.czech_data = payload
        self.data = payload


def _payload() -> dict[str, Any]:
    """Return five physical meters and all three aggregate types."""
    meters = [
        {
            "id": "101",
            "type": "heating",
            "meter_type": "hca",
            "meter_number": "H-1",
            "installation_number": "1",
            "room": "Obývací pokoj",
            "label": "Topení",
            "category": "Rozdělovač",
            "unit": "díl",
            "value": "120.5",
            "last_consumption": "8.5",
            "reading_date": "2026-07-10T00:00:00",
        },
        {
            "id": "102",
            "type": "heating",
            "room": "Ložnice",
            "unit": "díl",
            "value": "80",
        },
        {
            "id": "103",
            "type": "heating",
            "room": "Pokoj",
            "unit": "díl",
            "value": "60",
        },
        {
            "id": "201",
            "type": "warmwater",
            "room": "Koupelna",
            "unit": "m3",
            "value": "12.3",
        },
        {
            "id": "202",
            "type": "water",
            "room": "Koupelna",
            "unit": "m³",
            "value": "24",
        },
    ]
    aggregates = {
        "heating": {
            "unit": "díl",
            "daily": [{"date": "2026-07-15", "value": "3.5"}],
            "monthly": [{"year": 2026, "month": 7, "value": "20"}],
            "daily_value": "3.5",
            "daily_date": "2026-07-15",
            "monthly_value": "20",
            "monthly_year": 2026,
            "monthly_month": 7,
        },
        "warmwater": {
            "unit": "m³",
            "daily": [{"date": "2026-07-15", "value": "0.2"}],
            "monthly": [{"year": 2026, "month": 7, "value": "1.2"}],
            "daily_value": "0.2",
            "daily_date": "2026-07-15",
            "monthly_value": "1.2",
            "monthly_year": 2026,
            "monthly_month": 7,
        },
        "water": {
            "unit": "m³",
            "daily": [{"date": "2026-07-15", "value": "0.4"}],
            "monthly": [{"year": 2026, "month": 7, "value": "2.4"}],
            "daily_value": "0.4",
            "daily_date": "2026-07-15",
            "monthly_value": "2.4",
            "monthly_year": 2026,
            "monthly_month": 7,
        },
    }
    return {"meters": meters, "aggregates": aggregates}


def test_create_czech_entities_exposes_five_meters_and_six_aggregates() -> None:
    """The Czech account should create the requested 11 stable entities."""
    coordinator = DummyCoordinator(_payload())

    entities = create_czech_sensor_entities(coordinator)
    physical = [entity for entity in entities if isinstance(entity, CzechPhysicalMeterSensor)]
    aggregates = [entity for entity in entities if isinstance(entity, CzechAggregateSensor)]

    assert len(entities) == 11
    assert len(physical) == 5
    assert len(aggregates) == 6
    assert len({entity._attr_unique_id for entity in entities}) == 11
    assert all(
        entity._attr_device_info["identifiers"] == {("ecotrend_ista", "cz-42")}
        for entity in entities
    )


def test_physical_meter_values_and_metadata_follow_coordinator_updates() -> None:
    """Physical sensors should update dynamically without recreating entities."""
    coordinator = DummyCoordinator(_payload())
    entities = create_czech_sensor_entities(coordinator)
    heating = next(
        entity
        for entity in entities
        if isinstance(entity, CzechPhysicalMeterSensor) and entity._meter_id == "101"
    )
    warmwater = next(
        entity
        for entity in entities
        if isinstance(entity, CzechPhysicalMeterSensor) and entity._meter_id == "201"
    )

    assert heating.native_value == 120.5
    assert heating.native_unit_of_measurement == "díl"
    assert heating._attr_state_class is SensorStateClass.TOTAL_INCREASING
    assert heating.extra_state_attributes["room"] == "Obývací pokoj"
    assert "daily" not in heating.extra_state_attributes
    assert warmwater.native_unit_of_measurement == "m³"
    assert warmwater._attr_device_class is SensorDeviceClass.WATER

    coordinator.czech_data["meters"][0]["value"] = "130.25"
    assert heating.native_value == 130.25


def test_aggregate_sensors_report_period_values_without_history_attributes() -> None:
    """Daily and monthly sensors should expose only their latest interval."""
    coordinator = DummyCoordinator(_payload())
    entities = create_czech_sensor_entities(coordinator)
    daily = next(
        entity
        for entity in entities
        if isinstance(entity, CzechAggregateSensor)
        and entity._consumption_type == "heating"
        and entity._period == "daily"
    )
    monthly = next(
        entity
        for entity in entities
        if isinstance(entity, CzechAggregateSensor)
        and entity._consumption_type == "water"
        and entity._period == "monthly"
    )

    assert daily.native_value == 3.5
    assert daily._attr_state_class is SensorStateClass.TOTAL
    assert daily.last_reset == datetime(2026, 7, 15, tzinfo=UTC)
    assert daily.extra_state_attributes == {
        "consumption_type": "heating",
        "period": "daily",
        "latest_period": "2026-07-15",
        "external_statistic_id": "ecotrend_ista:cz_42_heating_daily",
    }
    assert monthly.native_value == 2.4
    assert monthly.native_unit_of_measurement == "m³"
    assert monthly.last_reset == datetime(2026, 7, 1, tzinfo=UTC)
    assert "daily" not in monthly.extra_state_attributes
    assert "monthly" not in monthly.extra_state_attributes

    coordinator.czech_data["aggregates"]["water"]["monthly_value"] = "3.1"
    assert monthly.native_value == 3.1
