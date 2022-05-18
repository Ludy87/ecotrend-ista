"""Support for reading status from ecotren-ists."""
from __future__ import annotations

import logging

from datetime import timedelta
from typing import Any, Dict, List
from .entity import EcoEntity

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import ENERGY_KILO_WATT_HOUR
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.util import Throttle

from .const import (
    CONF_CONTROLLER,
    CONF_TYPE_HEATING,
    CONF_TYPE_HEATWATER,
    CONF_UNIT_HEATING,
    CONF_UNIT_WARMWATER,
    CONF_UPDATE_FREQUENCY,
    CONF_YEAR,
    CONF_YEARMONTH,
    DOMAIN,
    UNIT_SUPPORT_HEATING,
    UNIT_SUPPORT_WARMWATER,
)

from pyecotrend_ista import pyecotrend_ista as ista

_LOGGER = logging.getLogger(__name__)

SENSOR_TYPES: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key=CONF_TYPE_HEATWATER,
        name="Warmwasser",
        native_unit_of_measurement=ENERGY_KILO_WATT_HOUR,
        device_class=CONF_TYPE_HEATWATER,
        state_class=SensorStateClass.TOTAL,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:water",
    ),
    SensorEntityDescription(
        key=CONF_TYPE_HEATING,
        name="Heizung",
        native_unit_of_measurement=ENERGY_KILO_WATT_HOUR,
        device_class=CONF_TYPE_HEATING,
        state_class=SensorStateClass.TOTAL,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:radiator",
    ),
)


async def async_setup_platform(
    hass: HomeAssistant,
    conf: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    if discovery_info is None:
        return
    controller: ista.PyEcotrendIsta = hass.data[DOMAIN][discovery_info[CONF_CONTROLLER]]
    _LOGGER.debug(f"PyEcotrendIsta version: {controller.getVersion()}")
    unitheating = hass.data[CONF_UNIT_HEATING][discovery_info[CONF_CONTROLLER]]
    unitwarmwater = hass.data[CONF_UNIT_WARMWATER][discovery_info[CONF_CONTROLLER]]
    updateTime = hass.data[CONF_UPDATE_FREQUENCY][discovery_info[CONF_CONTROLLER]]
    year: List[int] = hass.data[CONF_YEAR][discovery_info[CONF_CONTROLLER]]
    yearmonth: List[str] = hass.data[CONF_YEARMONTH][discovery_info[CONF_CONTROLLER]]

    device_id: List[str] = []

    consums: List[Dict[str, Any]] = await controller.getConsumsNow()

    sc: str = controller.getSupportCode().lower()

    entities: List[Any] = []

    support_types: List[str] = await controller.getTypes()
    _LOGGER.debug(f"PyEcotrendIsta supported types: {support_types}")

    def setUnit():
        unit_type = CONF_UNIT_HEATING.split("_")[1]
        if unit_type == description.key:
            unit = "" if unitheating == UNIT_SUPPORT_HEATING[1] else unitheating
        unit_type = CONF_UNIT_WARMWATER.split("_")[1]
        if unit_type == description.key:
            unit = "" if unitwarmwater == UNIT_SUPPORT_WARMWATER[1] else unitwarmwater
        return unit

    for description in SENSOR_TYPES:
        if consums:
            for consum in consums:
                if description.key == consum.get("type", ""):
                    if not device_id or consum.get("entity_id", "") not in device_id:
                        entities.append(EcoSensor(controller, description, consum, updateTime, setUnit()))
                        device_id.append(consum.get("entity_id", ""))
            _LOGGER.debug("load consums")
        if yearmonth:
            for ym in yearmonth:
                ymL: List[str] = ym.split(".")
                if len(ymL) != 2:
                    _LOGGER.error("wrong format! just format in yyyy.m")
                    continue
                yyyy = int(ymL[0])
                m = int(ymL[1])

                consumsyearmonth: Dict[str, Any] = await controller.getConsumById(
                    "{}_{}_{}_{}".format(description.key, yyyy, m, sc)
                )  # warmwasser_yyyy_m_xxxxxxxxx
                if consumsyearmonth:
                    if description.key == consumsyearmonth.get("type", ""):
                        if not device_id or consumsyearmonth.get("entity_id", "") not in device_id:
                            entities.append(
                                EcoYearMonthSensor(controller, description, consumsyearmonth, updateTime, yyyy, m, setUnit())
                            )
                            device_id.append(consumsyearmonth.get("entity_id", ""))
            _LOGGER.debug("load yearmonth")
        if year:
            for y in year:
                consumsyear: List[Dict[str, Any]] = await controller.getConsumsByYear(y)
                if consumsyear:
                    for consum in consumsyear:
                        if description.key == consum.get("type", ""):
                            if not device_id or consum.get("entity_id", "") not in device_id:
                                entities.append(EcoYearSensor(controller, description, consum, updateTime, y, setUnit()))
                                device_id.append(consum.get("entity_id", ""))
            _LOGGER.debug("load year")

    add_entities(entities, True)


class EcoYearSensor(EcoEntity, SensorEntity, RestoreEntity):
    def __init__(
        self,
        controller: ista.PyEcotrendIsta,
        description: SensorEntityDescription,
        consum: Dict[str, Any],
        updateTime: timedelta,
        year: int,
        unit: str,
    ) -> None:
        super().__init__(controller, description, consum, unit)
        self.scan_interval = updateTime
        self.async_update = Throttle(self.scan_interval)(self._async_update)
        _LOGGER.debug(f"EcoYearSensor set Sensor: {self.entity_description.key} | update interval: {updateTime}")

        self._year = year

    async def _async_update(self) -> None:
        consum: Dict[str, Any] = await self._controller.getConsumById(self._name)  # warmwasser_yyyy_m_xxxxxxxxx
        if self.entity_description.key == consum.get("type", ""):
            _value = consum.get("value{}".format(self._unit), "-1")
            _value = None if _value == "None" else _value
            if _value:
                self._attr_native_value = float(str(_value).replace(",", "."))
            else:
                _LOGGER.error(await self._controller.getTypes())
            _LOGGER.debug(
                "Updating EcoYearSensor: %s | Verbrauch: %s",
                self._name,
                str(self._attr_native_value),
            )


class EcoYearMonthSensor(EcoEntity, SensorEntity, RestoreEntity):
    def __init__(
        self,
        controller: ista.PyEcotrendIsta,
        description: SensorEntityDescription,
        consum: Dict[str, Any],
        updateTime: timedelta,
        year: int,
        month: int,
        unit: str,
    ) -> None:
        self._attr_icon = description.icon
        super().__init__(controller, description, consum, unit)
        self.scan_interval = updateTime
        self.async_update = Throttle(self.scan_interval)(self._async_update)
        _LOGGER.debug(f"EcoYearMonthSensor set Sensor: {self.entity_description.key} | update interval: {updateTime}")

        self._year = year
        self._month = month

    async def _async_update(self) -> None:
        consum: Dict[str, Any] = await self._controller.getConsumById(self._name)  # warmwasser_yyyy_m_xxxxxxxxx
        if self.entity_description.key == consum.get("type", ""):
            _value = consum.get("value{}".format(self._unit), "-1")
            _value = None if _value == "None" else _value
            if _value:
                self._attr_native_value = float(str(_value).replace(",", "."))
            else:
                _LOGGER.error(await self._controller.getTypes())
            _LOGGER.debug(
                "Updating EcoYearMonthSensor: %s | Verbrauch: %s",
                self._name,
                str(self._attr_native_value),
            )


class EcoSensor(EcoEntity, SensorEntity, RestoreEntity):
    def __init__(
        self,
        controller: ista.PyEcotrendIsta,
        description: SensorEntityDescription,
        consum: Dict[str, Any],
        updateTime: timedelta,
        unit: str,
    ) -> None:
        self._attr_icon = description.icon
        super().__init__(controller, description, consum, unit)
        self.scan_interval = updateTime
        self.async_update = Throttle(self.scan_interval)(self._async_update)
        _LOGGER.debug(f"set EcoSensor: {self.entity_description.key} | update interval: {updateTime}")

    async def _async_update(self) -> None:
        consum: Dict[str, Any] = await self._controller.getConsumById(self._name, True)  # warmwasser_xxxxxxxxx
        if self.entity_description.key == consum.get("type", ""):
            _value = consum.get("value{}".format(self._unit), "-1")
            _value = None if _value == "None" else _value
            if _value:
                self._attr_native_value = float(str(_value).replace(",", "."))
            else:
                _LOGGER.error(await self._controller.getTypes())
            _LOGGER.debug(
                "Updating EcoSensor: %s | Verbrauch: %s",
                self._name,
                str(self._attr_native_value),
            )
