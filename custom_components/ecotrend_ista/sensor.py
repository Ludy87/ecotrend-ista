from __future__ import annotations

import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass
)
from homeassistant.const import ENERGY_KILO_WATT_HOUR
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .const import (
    CONF_CONTROLLER,
    CONF_EMAIL,
    CONF_PASSWORD,
    CONF_TYPE_HEATING,
    CONF_TYPE_HEATWATER,
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
    discovery_info: DiscoveryInfoType | None = None
) -> None:
    if discovery_info is None:
        return
    controller: ista.PyEcotrendIsta = hass.data[DOMAIN][discovery_info[CONF_CONTROLLER]]
    consums: list = await controller.consum_small()
    sc: str = controller.getSupportCode()

    entities = []

    for description in SENSOR_TYPES:
        for consum in consums:
            if "type" in consum:
                if description.key in consum["type"]:
                    entities.append(EcoSensor(description, consum, sc, controller))

    add_entities(entities, True)


class EcoSensor(SensorEntity, RestoreEntity):
    def __init__(
        self,
        description: SensorEntityDescription,
        consum: list,
        supportCode: str,
        controller: ista.PyEcotrendIsta,
    ) -> None:
        self._attr_name = f"{description.name} {supportCode}".title()
        self._attr_unique_id = f"{DOMAIN}.{description.key}_{supportCode}"
        self._attr_unit_of_measurement = description.native_unit_of_measurement
        self._controller = controller
        self.entity_description = description
        self._consum = consum
        self._attr_native_value = self._consum["valuekwh"]
        self._supportCode = supportCode
        _LOGGER.debug(f"set Sensor: {self.entity_description.key}")

    async def async_update(self) -> None:
        consums: list = await self._controller.consum_small()
        for consum in consums:
            if "type" in consum:
                if self.entity_description.key in consum["type"]:
                    self._attr_native_value = consum["valuekwh"]
                    _LOGGER.debug("Updating sensor: %s | Verbrauch: %s", self._attr_name, str(self._attr_native_value))

    @property
    def device_info(self) -> DeviceInfo:
        """Return a device description for device registry."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._supportCode)},
            manufacturer="ista",
            name=self._attr_name,
        )
