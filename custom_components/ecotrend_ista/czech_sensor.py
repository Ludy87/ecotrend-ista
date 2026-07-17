"""Sensor entities for Czech ista EcoTrend accounts."""

from __future__ import annotations

from datetime import date, datetime
import re
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import UnitOfVolume
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN, MANUFACTURER
from .coordinator import IstaDataUpdateCoordinator
from .czech_statistics import statistic_id

_CONSUMPTION_NAMES = {
    "heating": "Topení",
    "warmwater": "Teplá voda",
    "water": "Studená voda",
}
_PERIOD_NAMES = {
    "daily": "denní",
    "monthly": "měsíční",
}
_WATER_TYPES = {"warmwater", "water"}
_CUBIC_METRE_UNITS = {
    "cbm",
    "cubicmeter",
    "cubicmetre",
    "m3",
    "m³",
}


def _czech_data(coordinator: IstaDataUpdateCoordinator) -> dict[str, Any]:
    """Return the Czech payload regardless of its coordinator storage location."""
    czech_data = getattr(coordinator, "czech_data", None)
    if isinstance(czech_data, dict):
        return czech_data

    coordinator_data = coordinator.data
    if not isinstance(coordinator_data, dict):
        return {}
    if "meters" in coordinator_data or "aggregates" in coordinator_data:
        return coordinator_data

    for value in coordinator_data.values():
        if isinstance(value, dict) and ("meters" in value or "aggregates" in value):
            return value
    return {}


def _account_id(coordinator: IstaDataUpdateCoordinator) -> str:
    """Return the stable account identifier used by every Czech entity."""
    support_code = coordinator.controller.get_support_code()
    if support_code:
        return str(support_code)

    uuids = coordinator.controller.get_uuids()
    if uuids:
        return str(uuids[0])
    return coordinator.config_entry.entry_id


def _unique_id_part(value: Any) -> str:
    """Normalize an API identifier for use inside an entity unique ID."""
    normalized = re.sub(r"[^a-z0-9]+", "_", str(value).casefold()).strip("_")
    return normalized or "unknown"


def _number(value: Any) -> StateType:
    """Convert API numeric strings to sensor-compatible values."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return value
    try:
        return float(str(value).strip().replace(",", "."))
    except ValueError:
        return None


def _unit(unit: Any, consumption_type: str) -> str | None:
    """Normalize Czech water-volume units to the Home Assistant unit."""
    if unit is None:
        return None
    value = str(unit).strip()
    if not value:
        return None
    compact = re.sub(r"[\s._-]+", "", value.casefold())
    if consumption_type in _WATER_TYPES and compact in _CUBIC_METRE_UNITS:
        return UnitOfVolume.CUBIC_METERS
    return value


def _period_start(aggregate: dict[str, Any], period: str) -> datetime | None:
    """Return the local start of the latest represented interval."""
    if period == "daily":
        raw_date = aggregate.get("daily_date")
        if not raw_date:
            return None
        try:
            interval_date = date.fromisoformat(str(raw_date))
        except ValueError:
            return None
        return datetime(
            interval_date.year,
            interval_date.month,
            interval_date.day,
            tzinfo=dt_util.DEFAULT_TIME_ZONE,
        )

    try:
        year = int(aggregate["monthly_year"])
        month = int(aggregate["monthly_month"])
        return datetime(year, month, 1, tzinfo=dt_util.DEFAULT_TIME_ZONE)
    except (KeyError, TypeError, ValueError):
        return None


def _defined_attributes(values: dict[str, Any]) -> dict[str, Any]:
    """Remove empty metadata values from state attributes."""
    return {key: value for key, value in values.items() if value not in (None, "")}


class CzechEcotrendSensorEntity(CoordinatorEntity[IstaDataUpdateCoordinator], SensorEntity):
    """Base class shared by Czech ista sensor entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: IstaDataUpdateCoordinator) -> None:
        """Initialize a Czech ista sensor entity."""
        super().__init__(coordinator)
        account_id = _account_id(coordinator)
        self._account_id = account_id
        self._attr_attribution = "Data provided by https://ecotrend.ista.cz/"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, account_id)},
            manufacturer=MANUFACTURER,
            model="ista EcoTrend Czech Republic",
            name="ista EcoTrend CZ",
            sw_version=coordinator.controller.get_version(),
        )


class CzechPhysicalMeterSensor(CzechEcotrendSensorEntity):
    """Current reading of one physical Czech ista meter."""

    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(
        self,
        coordinator: IstaDataUpdateCoordinator,
        meter: dict[str, Any],
    ) -> None:
        """Initialize a physical meter sensor."""
        super().__init__(coordinator)
        self._meter_id = str(meter["id"])
        self._consumption_type = str(meter["type"])
        unique_meter_id = _unique_id_part(self._meter_id)
        self._attr_unique_id = (
            f"{_unique_id_part(self._account_id)}_meter_{self._consumption_type}_{unique_meter_id}"
        )

        type_name = _CONSUMPTION_NAMES.get(self._consumption_type, self._consumption_type.title())
        meter_number = meter.get("meter_number")
        detail = meter.get("room") or meter.get("label") or meter_number or self._meter_id
        if meter_number and meter_number != detail:
            detail = f"{detail} ({meter_number})"
        self._attr_name = f"{type_name} {detail}"
        if self._consumption_type in _WATER_TYPES:
            self._attr_device_class = SensorDeviceClass.WATER

    @property
    def _meter(self) -> dict[str, Any]:
        """Return the latest data for this physical meter."""
        meters = _czech_data(self.coordinator).get("meters", [])
        if not isinstance(meters, list):
            return {}
        for meter in meters:
            if (
                isinstance(meter, dict)
                and str(meter.get("id")) == self._meter_id
                and str(meter.get("type")) == self._consumption_type
            ):
                return meter
        return {}

    @property
    def native_value(self) -> StateType:
        """Return the latest physical meter reading."""
        return _number(self._meter.get("value"))

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return the meter unit."""
        return _unit(self._meter.get("unit"), self._consumption_type)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return physical meter metadata without embedding history."""
        meter = self._meter
        return _defined_attributes(
            {
                "meter_id": self._meter_id,
                "meter_type": meter.get("meter_type"),
                "meter_number": meter.get("meter_number"),
                "installation_number": meter.get("installation_number"),
                "room": meter.get("room"),
                "label": meter.get("label"),
                "category": meter.get("category"),
                "reading_date": meter.get("reading_date"),
                "last_consumption": meter.get("last_consumption"),
                "activation_date": meter.get("activation_date"),
                "deactivation_date": meter.get("deactivation_date"),
            }
        )


class CzechAggregateSensor(CzechEcotrendSensorEntity):
    """Daily or monthly Czech ista consumption aggregate."""

    _attr_state_class = SensorStateClass.TOTAL

    def __init__(
        self,
        coordinator: IstaDataUpdateCoordinator,
        consumption_type: str,
        period: str,
    ) -> None:
        """Initialize an aggregate sensor."""
        super().__init__(coordinator)
        self._consumption_type = consumption_type
        self._period = period
        self._attr_unique_id = (
            f"{_unique_id_part(self._account_id)}_{consumption_type}_{period}"
        )
        type_name = _CONSUMPTION_NAMES[consumption_type]
        self._attr_name = f"{type_name} {_PERIOD_NAMES[period]}"
        if consumption_type in _WATER_TYPES:
            self._attr_device_class = SensorDeviceClass.WATER

    @property
    def _aggregate(self) -> dict[str, Any]:
        """Return the latest aggregate data for this entity."""
        aggregates = _czech_data(self.coordinator).get("aggregates", {})
        if not isinstance(aggregates, dict):
            return {}
        aggregate = aggregates.get(self._consumption_type)
        return aggregate if isinstance(aggregate, dict) else {}

    @property
    def native_value(self) -> StateType:
        """Return the latest interval consumption."""
        return _number(self._aggregate.get(f"{self._period}_value"))

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return the aggregate unit."""
        return _unit(self._aggregate.get("unit"), self._consumption_type)

    @property
    def last_reset(self) -> datetime | None:
        """Return the start of the represented daily or monthly interval."""
        return _period_start(self._aggregate, self._period)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return aggregate metadata without embedding historical readings."""
        aggregate = self._aggregate
        if self._period == "daily":
            latest_period = aggregate.get("daily_date")
        else:
            year = aggregate.get("monthly_year")
            month = aggregate.get("monthly_month")
            latest_period = f"{year:04}-{month:02}" if isinstance(year, int) and isinstance(month, int) else None
        return _defined_attributes(
            {
                "consumption_type": self._consumption_type,
                "period": self._period,
                "latest_period": latest_period,
                "external_statistic_id": statistic_id(
                    self._account_id,
                    self._consumption_type,
                ),
            }
        )


def create_czech_sensor_entities(
    coordinator: IstaDataUpdateCoordinator,
) -> list[CzechEcotrendSensorEntity]:
    """Create physical and aggregate sensor entities for a Czech account."""
    entities: list[CzechEcotrendSensorEntity] = []
    meters = _czech_data(coordinator).get("meters", [])
    seen_meters: set[tuple[str, str]] = set()
    if isinstance(meters, list):
        for meter in meters:
            if not isinstance(meter, dict) or meter.get("id") is None or meter.get("type") is None:
                continue
            meter_key = (str(meter["type"]), str(meter["id"]))
            if meter_key in seen_meters:
                continue
            seen_meters.add(meter_key)
            entities.append(CzechPhysicalMeterSensor(coordinator, meter))

    entities.extend(
        CzechAggregateSensor(coordinator, consumption_type, period)
        for consumption_type in _CONSUMPTION_NAMES
        for period in _PERIOD_NAMES
    )
    return entities
