from __future__ import annotations

import logging

from datetime import timedelta

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import ENERGY_KILO_WATT_HOUR
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.util import Throttle

from .const import (
    CONF_CONTROLLER,
    CONF_TYPE_HEATING,
    CONF_TYPE_HEATWATER,
    CONF_UPDATE_FREQUENCY,
    DOMAIN,
)

from pyecotrend_ista import pyecotrend_ista as ista

_LOGGER = logging.getLogger(__name__)

SENSOR_TYPES: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key=CONF_TYPE_HEATWATER,
        name="Warmwasser",
        native_unit_of_measurement=ENERGY_KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key=CONF_TYPE_HEATING,
        name="Heizung",
        native_unit_of_measurement=ENERGY_KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        entity_category=EntityCategory.DIAGNOSTIC,
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
    consums: list = await controller.consum_small()
    updateTime = hass.data[CONF_UPDATE_FREQUENCY][discovery_info[CONF_CONTROLLER]]
    sc: str = controller.getSupportCode()

    entities = []

    for description in SENSOR_TYPES:
        for consum in consums:
            if "type" in consum:
                if description.key in consum["type"]:
                    entities.append(EcoSensor(description, consum, sc, controller, updateTime))

    add_entities(entities, True)


class EcoSensor(SensorEntity, RestoreEntity):
    def __init__(
        self,
        description: SensorEntityDescription,
        consum: list,
        supportCode: str,
        controller: ista.PyEcotrendIsta,
        updateTime: timedelta,
    ) -> None:
        self._attr_name = f"{description.name} {supportCode}".title()
        self._attr_unique_id = f"{DOMAIN}.{description.key}_{supportCode}"
        self._attr_unit_of_measurement = description.native_unit_of_measurement
        self._controller = controller
        self.entity_description = description
        self._consum = consum
        self._attr_native_value = self._consum["valuekwh"]
        self._supportCode = supportCode
        self.scan_interval = updateTime
        self.async_update = Throttle(self.scan_interval)(self._async_update)
        _LOGGER.debug(f"set Sensor: {self.entity_description.key} | update interval: {updateTime}")

    @property
    def device_info(self) -> DeviceInfo:
        """Return a device description for device registry."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._supportCode)},
            manufacturer="ista",
            name=self._attr_name,
        )

    async def _async_update(self) -> None:
        consums: list = await self._controller.consum_small()
        for consum in consums:
            if "type" in consum:
                if self.entity_description.key in consum["type"]:
                    self._attr_native_value = consum["valuekwh"]
                    _LOGGER.debug(
                        "Updating sensor: %s | Verbrauch: %s",
                        self._attr_name,
                        str(self._attr_native_value),
                    )
