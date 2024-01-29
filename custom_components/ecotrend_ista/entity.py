"""Entity definitions for Ecotrend sensors."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import EntityCategory, UnitOfEnergy, UnitOfVolume

from .const import (
    CONF_TYPE_HEATING,
    CONF_TYPE_HEATING_CASH,
    CONF_TYPE_HEATING_CUSTOM,
    CONF_TYPE_HEATWATER,
    CONF_TYPE_HEATWATER_CASH,
    CONF_TYPE_HEATWATER_CUSTOM,
    CONF_TYPE_WATER,
    CONF_TYPE_WATER_CASH,
    CONF_TYPE_WATER_CUSTOM,
)


@dataclass
class EcotrendRequiredKeysMixin:
    """Mixin class for required keys in Ecotrend sensor entity descriptions."""

    data_type: Literal["heating", "warmwater", "water"]
    costs_or_cosums: Literal["consums", "costs"]


@dataclass
class EcotrendSensorEntityDescription(SensorEntityDescription, EcotrendRequiredKeysMixin):
    """Describes an Ecotrend sensor entity."""


SENSOR_TYPES: tuple[EcotrendSensorEntityDescription, ...] = (
    EcotrendSensorEntityDescription(
        key=CONF_TYPE_HEATWATER,
        data_type=CONF_TYPE_HEATWATER,
        native_unit_of_measurement=UnitOfVolume.CUBIC_METERS,
        device_class=SensorDeviceClass.WATER,
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:thermometer-water",
        costs_or_cosums="consums",
    ),
    EcotrendSensorEntityDescription(
        key=CONF_TYPE_HEATWATER_CASH,
        data_type=CONF_TYPE_HEATWATER,
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:cash",
        costs_or_cosums="costs",
    ),
    EcotrendSensorEntityDescription(
        key=CONF_TYPE_HEATWATER_CUSTOM,
        data_type=CONF_TYPE_HEATWATER,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:thermometer-water",
        costs_or_cosums="consums",
    ),
    EcotrendSensorEntityDescription(
        key=CONF_TYPE_WATER,
        data_type=CONF_TYPE_WATER,
        native_unit_of_measurement=UnitOfVolume.CUBIC_METERS,
        device_class=SensorDeviceClass.WATER,
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:water",
        costs_or_cosums="consums",
    ),
    EcotrendSensorEntityDescription(
        key=CONF_TYPE_WATER_CASH,
        data_type=CONF_TYPE_WATER,
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:cash",
        costs_or_cosums="costs",
    ),
    EcotrendSensorEntityDescription(
        key=CONF_TYPE_WATER_CUSTOM,
        data_type=CONF_TYPE_WATER,
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:water",
        costs_or_cosums="consums",
    ),
    EcotrendSensorEntityDescription(
        key=CONF_TYPE_HEATING,
        data_type=CONF_TYPE_HEATING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:radiator",
        costs_or_cosums="consums",
    ),
    EcotrendSensorEntityDescription(
        key=CONF_TYPE_HEATING_CASH,
        data_type=CONF_TYPE_HEATING,
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:cash",
        costs_or_cosums="costs",
    ),
    EcotrendSensorEntityDescription(
        key=CONF_TYPE_HEATING_CUSTOM,
        data_type=CONF_TYPE_HEATING,
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:radiator",
        costs_or_cosums="consums",
    ),
)
