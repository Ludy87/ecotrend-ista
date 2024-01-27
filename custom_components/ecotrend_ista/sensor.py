"""Support for reading status from ecotren-ists."""
from __future__ import annotations

import datetime
import logging
from collections.abc import Callable
from typing import Any, cast

from homeassistant.components.sensor import RestoreSensor, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from pyecotrend_ista.helper_object_de import CustomRaw
from pyecotrend_ista.pyecotrend_ista import PyEcotrendIsta

from .const import (
    CONF_TYPE_HEATING_CUSTOM,
    CONF_TYPE_WATER_CUSTOM,
    CONF_URL,
    DEVICE_NAME,
    DOMAIN,
    MANUFACTURER,
    TRACKER_UPDATE_STR,
)
from .const_schema import URL_SELECTORS
from .coordinator import IstaDataUpdateCoordinator
from .entity import SENSOR_TYPES, EcotrendSensorEntityDescription

_LOGGER = logging.getLogger(__name__)


class EcotrendBaseEntityV3(CoordinatorEntity[IstaDataUpdateCoordinator], RestoreSensor):
    """Base entity class for ista EcoTrend Version 3."""

    _attr_force_update = False

    def __init__(self, coordinator: IstaDataUpdateCoordinator, controller: PyEcotrendIsta, uuid: str) -> None:
        """Initialize the ista EcoTrend Version 3 base entity."""
        super().__init__(coordinator)
        self._attr_attribution = f"Data provided by {URL_SELECTORS.get(self.coordinator.config_entry.options.get(CONF_URL))}"
        self._support_code = controller._supportCode
        self.uuid = uuid
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{self.uuid}")},
            manufacturer=f"{MANUFACTURER} {self.uuid}",
            model="ista consumption & costs",
            name=f"{DEVICE_NAME} {self.uuid} {'' if controller._accessToken != 'Demo' else 'Demo'}",
            sw_version=controller.getVersion(),
            hw_version=controller._a_tosUpdated,
            via_device=(DOMAIN, f"{self.uuid}"),
        )
        self._unsub_dispatchers: list[Callable[[], None]] = []

    async def async_added_to_hass(self) -> None:
        """Run when the entity is added to Home Assistant."""
        await super().async_added_to_hass()
        if state := await self.async_get_last_sensor_data():
            self._attr_native_value = cast(float, state.native_value)
        self._unsub_dispatchers.append(async_dispatcher_connect(self.hass, TRACKER_UPDATE_STR, self.update))

    async def async_will_remove_from_hass(self) -> None:
        """Clean up before removing the entity."""
        for unsub in self._unsub_dispatchers[:]:
            unsub()
            self._unsub_dispatchers.remove(unsub)
        _LOGGER.debug("When entity is remove on hass")
        await self.hass.async_add_executor_job(self.coordinator.controller.logout)
        self._unsub_dispatchers = []

    async def update(self):
        """Perform an update."""
        _LOGGER.debug("update data in Coordinator")


class EcotrendSensorV3(EcotrendBaseEntityV3, SensorEntity):
    """Sensor entity class for ista EcoTrend Version 3."""

    def __init__(
        self,
        coordinator: IstaDataUpdateCoordinator,
        controller: PyEcotrendIsta,
        last: dict[str, Any],
        description: EcotrendSensorEntityDescription,
        uuid: str,
    ) -> None:
        """Initialize the ista EcoTrend Version 3 sensor."""
        self.entity_description = description
        super().__init__(coordinator, controller, uuid)

        if not last:
            return

        self._attr_name: str = f"{description.key}_{self.uuid}".replace("_", " ").title()
        self._attr_unique_id = f"{description.key}_{self.uuid}"
        self.consum_value = last.get(description.data_type)
        if description.costs_or_cosums == "costs":
            self._attr_native_unit_of_measurement = last.get("unit", None)  # Währung
        elif description.key == CONF_TYPE_WATER_CUSTOM:
            self._attr_native_unit_of_measurement = last.get("w", None)  # (Kalt-)Wasser
        elif description.key == CONF_TYPE_HEATING_CUSTOM:
            self._attr_native_unit_of_measurement = last.get("h", None)  # Heizung

        # pylint: disable=logging-fstring-interpolation
        if hasattr(self, "_attr_native_unit_of_measurement"):
            _LOGGER.debug(f"{description.data_type} {self.consum_value} {self._attr_native_unit_of_measurement}")  # noqa: G004
        elif hasattr(self, "unit_of_measurement"):
            _LOGGER.debug(f"{description.data_type} {self.consum_value} {self.unit_of_measurement}")  # noqa: G004

    @property
    def native_value(self) -> StateType:
        """Return the native value of the sensor."""
        return self.consum_value

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the extra state attributes of the sensor."""
        data = super().extra_state_attributes or {}
        if self.coordinator.data[self.uuid]:
            return dict(data, **self.coordinator.data[self.uuid].to_dict())
        return dict(data, **{})


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the ista EcoTrend Version 3 sensors from the config entry."""
    coordinator: IstaDataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    controller = coordinator.controller

    for uuid in controller.getUUIDs():
        entities: list = []
        consum_raw: CustomRaw = CustomRaw.from_dict(
            await hass.async_add_executor_job(
                controller.consum_raw,
                [
                    datetime.datetime.now().year,
                    datetime.datetime.now().year - 1,
                ],
                None,
                True,
                uuid,
            )
        )
        consum_dict = consum_raw.to_dict()
        last_value = consum_dict.get("last_value", None)
        last_custom_value = consum_dict.get("last_custom_value", None)
        last_costs = consum_dict.get("last_costs", None)
        for description in SENSOR_TYPES:
            descr: EcotrendSensorEntityDescription = description
            if not hasattr(consum_raw, "consum_types") or not consum_raw.consum_types:
                continue
            for consum_type in consum_raw.consum_types:
                if descr.data_type != consum_type:
                    continue
                if descr.costs_or_cosums == "consums" and (last_value or last_custom_value):
                    entities.append(
                        EcotrendSensorV3(
                            coordinator,
                            controller,
                            (
                                last_custom_value
                                if descr.key in ("warmwater_custom", "water_custom", "heating_custom")
                                else last_value
                            ),
                            descr,
                            uuid,
                        )
                    )
                elif descr.costs_or_cosums == "costs" and last_costs:
                    entities.append(
                        EcotrendSensorV3(
                            coordinator,
                            controller,
                            last_costs,
                            descr,
                            uuid,
                        )
                    )

    async_add_entities(entities)
