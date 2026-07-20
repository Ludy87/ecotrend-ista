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

_METER_TRANSLATION_KEYS = {
    "heating": "czech_heating_meter",
    "warmwater": "czech_warm_water_meter",
    "water": "czech_cold_water_meter",
}
_AGGREGATE_TRANSLATION_KEYS = {
    ("heating", "daily"): "czech_heating_daily",
    ("heating", "monthly"): "czech_heating_monthly",
    ("warmwater", "daily"): "czech_warm_water_daily",
    ("warmwater", "monthly"): "czech_warm_water_monthly",
    ("water", "daily"): "czech_cold_water_daily",
    ("water", "monthly"): "czech_cold_water_monthly",
}
_HEATING_NATIVE_UNIT_TRANSLATION_KEYS = {
    "meter": "czech_heating_meter_native_unit",
    "daily": "czech_heating_daily_native_unit",
    "monthly": "czech_heating_monthly_native_unit",
}
_WATER_TYPES = {"warmwater", "water"}
_CUBIC_METRE_UNITS = {
    "cbm",
    "cubicmeter",
    "cubicmetre",
    "m3",
    "m³",
}
_HEATING_UNIT_ALIASES = {
    "díl",
    "dílků",
    "jednotka",
    "jednotky",
    "jednotek",
    "unit",
    "units",
}
_HEATING_UNIT = "jednotek"


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
    """Normalize Czech API units for Home Assistant."""
    if unit is None:
        return None
    value = str(unit).strip()
    if not value:
        return None
    compact = re.sub(r"[\s._()/-]+", "", value.casefold())
    if consumption_type in _WATER_TYPES and compact in _CUBIC_METRE_UNITS:
        return UnitOfVolume.CUBIC_METERS
    if consumption_type == "heating" and compact in _HEATING_UNIT_ALIASES:
        return _HEATING_UNIT
    return value


def _latest_data_date(aggregate: dict[str, Any]) -> date | None:
    """Return the latest daily date represented by an aggregate."""
    raw_date = aggregate.get("daily_date")
    if not raw_date:
        return None
    try:
        return date.fromisoformat(str(raw_date))
    except ValueError:
        return None


def _data_delay_days(data_date: date | None) -> int | None:
    """Return how many local calendar days the available data trails today."""
    if data_date is None:
        return None
    today = datetime.now(tz=dt_util.DEFAULT_TIME_ZONE).date()
    return max(0, (today - data_date).days)


def _defined_attributes(values: dict[str, Any]) -> dict[str, Any]:
    """Remove empty metadata values from state attributes."""
    return {key: value for key, value in values.items() if value not in (None, "")}


def _available_consumption_types(data: dict[str, Any]) -> set[str]:
    """Return consumption types represented by meters or aggregate data."""
    consumption_types: set[str] = set()
    meters = data.get("meters")
    if isinstance(meters, list):
        consumption_types.update(
            str(meter["type"]) for meter in meters if isinstance(meter, dict) and meter.get("type") in _METER_TRANSLATION_KEYS
        )

    aggregates = data.get("aggregates")
    if isinstance(aggregates, dict):
        consumption_types.update(
            consumption_type for consumption_type in aggregates if consumption_type in _METER_TRANSLATION_KEYS
        )
    return consumption_types


def _meter_lookup(coordinator: IstaDataUpdateCoordinator) -> dict[tuple[str, str], dict[str, Any]]:
    """Return an O(1) meter lookup cached for the current coordinator payload."""
    meters = _czech_data(coordinator).get("meters", [])
    if not isinstance(meters, list):
        return {}

    cache = getattr(coordinator, "_czech_meter_lookup_cache", None)
    if isinstance(cache, tuple) and len(cache) == 2 and cache[0] is meters:
        return cache[1]

    lookup = {
        (str(meter.get("type")), str(meter.get("id"))): meter
        for meter in meters
        if isinstance(meter, dict) and meter.get("id") is not None
    }
    coordinator._czech_meter_lookup_cache = (meters, lookup)
    return lookup


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
        self._attr_unique_id = f"{_unique_id_part(self._account_id)}_meter_{self._consumption_type}_{unique_meter_id}"

        meter_number = meter.get("meter_number")
        detail = meter.get("room") or meter.get("label") or meter_number or self._meter_id
        if meter_number and meter_number != detail:
            detail = f"{detail} ({meter_number})"
        self._uses_translated_heating_unit = (
            self._consumption_type == "heating" and _unit(meter.get("unit"), self._consumption_type) == _HEATING_UNIT
        )
        self._attr_translation_key = (
            _METER_TRANSLATION_KEYS[self._consumption_type]
            if self._consumption_type != "heating" or self._uses_translated_heating_unit
            else _HEATING_NATIVE_UNIT_TRANSLATION_KEYS["meter"]
        )
        self._attr_translation_placeholders = {"detail": str(detail)}
        if self._consumption_type in _WATER_TYPES:
            self._attr_device_class = SensorDeviceClass.WATER

    @property
    def _meter(self) -> dict[str, Any]:
        """Return the latest data for this physical meter."""
        return _meter_lookup(self.coordinator).get((self._consumption_type, self._meter_id), {})

    @property
    def native_value(self) -> StateType:
        """Return the latest physical meter reading."""
        return _number(self._meter.get("value"))

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return the meter unit."""
        unit = _unit(self._meter.get("unit"), self._consumption_type)
        return None if self._uses_translated_heating_unit else unit

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

    def __init__(
        self,
        coordinator: IstaDataUpdateCoordinator,
        consumption_type: str,
        period: str,
        translation_key: str,
    ) -> None:
        """Initialize an aggregate sensor."""
        super().__init__(coordinator)
        self._consumption_type = consumption_type
        self._period = period
        self._attr_unique_id = f"{_unique_id_part(self._account_id)}_{consumption_type}_{period}"
        aggregates = _czech_data(coordinator).get("aggregates", {})
        initial_aggregate = aggregates.get(consumption_type, {}) if isinstance(aggregates, dict) else {}
        self._uses_translated_heating_unit = (
            consumption_type == "heating"
            and isinstance(initial_aggregate, dict)
            and _unit(initial_aggregate.get("unit"), consumption_type) == _HEATING_UNIT
        )
        self._attr_translation_key = (
            translation_key
            if consumption_type != "heating" or self._uses_translated_heating_unit
            else _HEATING_NATIVE_UNIT_TRANSLATION_KEYS[period]
        )
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
        unit = _unit(self._aggregate.get("unit"), self._consumption_type)
        return None if self._uses_translated_heating_unit else unit

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return aggregate metadata without embedding historical readings."""
        aggregate = self._aggregate
        data_through = _latest_data_date(aggregate)
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
                "data_through": data_through.isoformat() if data_through else None,
                "delay_days": _data_delay_days(data_through),
                "external_statistic_id": statistic_id(
                    self._account_id,
                    self._consumption_type,
                ),
            }
        )


class CzechDataFreshnessSensor(CzechEcotrendSensorEntity):
    """Latest date through which all available consumption types have data."""

    _attr_device_class = SensorDeviceClass.DATE
    _attr_translation_key = "czech_data_through"

    def __init__(self, coordinator: IstaDataUpdateCoordinator) -> None:
        """Initialize the data freshness sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{_unique_id_part(self._account_id)}_data_through"

    @property
    def _dates_by_type(self) -> dict[str, date | None]:
        """Return the latest date for every expected consumption type."""
        data = _czech_data(self.coordinator)
        aggregates = data.get("aggregates", {})
        if not isinstance(aggregates, dict):
            aggregates = {}

        return {
            consumption_type: (
                _latest_data_date(aggregate) if isinstance((aggregate := aggregates.get(consumption_type)), dict) else None
            )
            for consumption_type in _available_consumption_types(data)
        }

    @property
    def native_value(self) -> date | None:
        """Return the oldest latest date so the value is valid for every type."""
        dates = list(self._dates_by_type.values())
        if not dates or any(data_date is None for data_date in dates):
            return None
        return min(data_date for data_date in dates if data_date is not None)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose per-type freshness and the effective delay."""
        dates = self._dates_by_type
        data_through = self.native_value
        return _defined_attributes(
            {
                "delay_days": _data_delay_days(data_through),
                "heating_data_through": dates.get("heating").isoformat() if dates.get("heating") else None,
                "hot_water_data_through": dates.get("warmwater").isoformat() if dates.get("warmwater") else None,
                "cold_water_data_through": dates.get("water").isoformat() if dates.get("water") else None,
            }
        )


def create_czech_sensor_entities(
    coordinator: IstaDataUpdateCoordinator,
) -> list[CzechEcotrendSensorEntity]:
    """Create physical and aggregate sensor entities for a Czech account."""
    entities: list[CzechEcotrendSensorEntity] = []
    data = _czech_data(coordinator)
    meters = data.get("meters", [])
    seen_meters: set[tuple[str, str]] = set()
    if isinstance(meters, list):
        for meter in meters:
            if not isinstance(meter, dict) or meter.get("id") is None or meter.get("type") not in _METER_TRANSLATION_KEYS:
                continue
            meter_key = (str(meter["type"]), str(meter["id"]))
            if meter_key in seen_meters:
                continue
            seen_meters.add(meter_key)
            entities.append(CzechPhysicalMeterSensor(coordinator, meter))

    available_types = _available_consumption_types(data)
    entities.extend(
        CzechAggregateSensor(coordinator, consumption_type, period, translation_key)
        for (consumption_type, period), translation_key in _AGGREGATE_TRANSLATION_KEYS.items()
        if consumption_type in available_types
    )
    entities.append(CzechDataFreshnessSensor(coordinator))
    return entities
