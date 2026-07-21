"""Tests for Czech ista sensor entities."""

from __future__ import annotations

from datetime import date
from typing import Any, cast

from custom_components.ecotrend_ista.coordinator import IstaDataUpdateCoordinator
from custom_components.ecotrend_ista.czech_sensor import (
    CzechAggregateSensor,
    CzechDataFreshnessSensor,
    CzechPhysicalMeterSensor,
    create_czech_sensor_entities,
)
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
import pytest


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


def _coordinator(payload: dict[str, Any]) -> IstaDataUpdateCoordinator:
    """Return the structurally compatible sensor coordinator test double."""
    return cast(IstaDataUpdateCoordinator, DummyCoordinator(payload))


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
            "unit": "(jednotky)",
            "value": "120.5",
            "last_consumption": "8.5",
            "reading_date": "2026-07-10T00:00:00",
        },
        {
            "id": "102",
            "type": "heating",
            "room": "Ložnice",
            "unit": "(jednotky)",
            "value": "80",
        },
        {
            "id": "103",
            "type": "heating",
            "room": "Pokoj",
            "unit": "(jednotky)",
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
            "unit": "Dílků",
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
    coordinator = _coordinator(_payload())

    entities = create_czech_sensor_entities(coordinator)
    physical = [entity for entity in entities if isinstance(entity, CzechPhysicalMeterSensor)]
    aggregates = [entity for entity in entities if isinstance(entity, CzechAggregateSensor)]

    freshness = [entity for entity in entities if isinstance(entity, CzechDataFreshnessSensor)]

    assert len(entities) == 12
    assert len(physical) == 5
    assert len(aggregates) == 6
    assert len(freshness) == 1
    assert len({entity._attr_unique_id for entity in entities}) == 12
    assert all(entity._attr_device_info["identifiers"] == {("ecotrend_ista", "cz-42")} for entity in entities)


def test_physical_meter_values_and_metadata_follow_coordinator_updates() -> None:
    """Physical sensors should update dynamically without recreating entities."""
    coordinator = _coordinator(_payload())
    entities = create_czech_sensor_entities(coordinator)
    heating = next(entity for entity in entities if isinstance(entity, CzechPhysicalMeterSensor) and entity._meter_id == "101")
    warmwater = next(
        entity for entity in entities if isinstance(entity, CzechPhysicalMeterSensor) and entity._meter_id == "201"
    )

    assert heating.native_value == pytest.approx(120.5)
    assert heating._attr_translation_key == "czech_heating_meter"
    assert heating._attr_translation_placeholders == {"detail": "Obývací pokoj (H-1)"}
    assert heating.native_unit_of_measurement is None
    assert heating._attr_state_class is SensorStateClass.TOTAL_INCREASING
    assert heating.extra_state_attributes["room"] == "Obývací pokoj"
    assert "daily" not in heating.extra_state_attributes
    assert warmwater.native_unit_of_measurement == "m³"
    assert warmwater._attr_device_class is SensorDeviceClass.WATER

    coordinator.czech_data["meters"] = [
        {**meter, "value": "130.25"} if meter["id"] == "101" else meter for meter in coordinator.czech_data["meters"]
    ]
    assert heating.native_value == pytest.approx(130.25)


def test_aggregate_sensors_report_period_values_without_history_attributes() -> None:
    """Daily and monthly sensors should expose only their latest interval."""
    coordinator = _coordinator(_payload())
    entities = create_czech_sensor_entities(coordinator)
    daily = next(
        entity
        for entity in entities
        if isinstance(entity, CzechAggregateSensor) and entity._consumption_type == "heating" and entity._period == "daily"
    )
    monthly = next(
        entity
        for entity in entities
        if isinstance(entity, CzechAggregateSensor) and entity._consumption_type == "water" and entity._period == "monthly"
    )

    assert daily.native_value == pytest.approx(3.5)
    assert daily._attr_translation_key == "czech_heating_daily"
    assert daily.native_unit_of_measurement is None
    assert not hasattr(daily, "_attr_state_class")
    assert not hasattr(daily, "last_reset")
    daily_attributes = daily.extra_state_attributes
    assert daily_attributes["consumption_type"] == "heating"
    assert daily_attributes["period"] == "daily"
    assert daily_attributes["latest_period"] == "2026-07-15"
    assert daily_attributes["data_through"] == "2026-07-15"
    assert isinstance(daily_attributes["delay_days"], int)
    assert daily_attributes["external_statistic_id"] == "ecotrend_ista:cz_42_heating_daily"
    assert monthly.native_value == pytest.approx(2.4)
    assert monthly._attr_translation_key == "czech_cold_water_monthly"
    assert monthly.native_unit_of_measurement == "m³"
    assert "daily" not in monthly.extra_state_attributes
    assert "monthly" not in monthly.extra_state_attributes

    coordinator.czech_data["aggregates"]["water"]["monthly_value"] = "3.1"
    assert monthly.native_value == pytest.approx(3.1)


def test_data_freshness_uses_oldest_latest_date_across_consumption_types() -> None:
    """The displayed cutoff date must be valid for every available type."""
    payload = _payload()
    payload["aggregates"]["heating"]["daily_date"] = "2026-07-14"
    coordinator = _coordinator(payload)
    freshness = next(
        entity for entity in create_czech_sensor_entities(coordinator) if isinstance(entity, CzechDataFreshnessSensor)
    )

    assert freshness.native_value == date(2026, 7, 14)
    assert freshness._attr_device_class is SensorDeviceClass.DATE
    assert freshness._attr_translation_key == "czech_data_through"
    assert freshness.extra_state_attributes["heating_data_through"] == "2026-07-14"
    assert freshness.extra_state_attributes["hot_water_data_through"] == "2026-07-15"
    assert freshness.extra_state_attributes["cold_water_data_through"] == "2026-07-15"
    assert isinstance(freshness.extra_state_attributes["delay_days"], int)


def test_data_freshness_is_unknown_when_an_expected_type_has_no_history() -> None:
    """The shared cutoff must not hide a missing history for an installed type."""
    payload = _payload()
    del payload["aggregates"]["heating"]
    coordinator = _coordinator(payload)
    freshness = next(
        entity for entity in create_czech_sensor_entities(coordinator) if isinstance(entity, CzechDataFreshnessSensor)
    )

    assert freshness.native_value is None
    assert "heating_data_through" not in freshness.extra_state_attributes


def test_aggregate_entities_are_only_created_for_installed_consumption_types() -> None:
    """Accounts without a medium should not receive permanently unknown entities."""
    payload = _payload()
    payload["meters"] = [meter for meter in payload["meters"] if meter["type"] == "water"]
    payload["aggregates"] = {"water": payload["aggregates"]["water"]}

    entities = create_czech_sensor_entities(_coordinator(payload))
    aggregates = [entity for entity in entities if isinstance(entity, CzechAggregateSensor)]

    assert len(entities) == 4
    assert {(entity._consumption_type, entity._period) for entity in aggregates} == {
        ("water", "daily"),
        ("water", "monthly"),
    }


def test_heating_energy_meter_keeps_its_native_unit() -> None:
    """A non-allocation heating meter must not be relabeled as allocation units."""
    payload = _payload()
    for meter in payload["meters"]:
        if meter["type"] == "heating":
            meter["unit"] = "kWh"
    payload["aggregates"]["heating"]["unit"] = "kWh"

    entities = create_czech_sensor_entities(_coordinator(payload))
    meter = next(entity for entity in entities if isinstance(entity, CzechPhysicalMeterSensor))
    daily = next(
        entity
        for entity in entities
        if isinstance(entity, CzechAggregateSensor) and entity._consumption_type == "heating" and entity._period == "daily"
    )

    assert meter._attr_translation_key == "czech_heating_meter_native_unit"
    assert meter.native_unit_of_measurement == "kWh"
    assert daily._attr_translation_key == "czech_heating_daily_native_unit"
    assert daily.native_unit_of_measurement == "kWh"
