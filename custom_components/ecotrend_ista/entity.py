"""Entity ecotrend-ista."""
from __future__ import annotations

import logging
import datetime

from typing import Any, Dict, List, Mapping

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.typing import StateType

from pyecotrend_ista import pyecotrend_ista as ista

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class EcoEntity(SensorEntity, RestoreEntity):
    def __init__(
        self,
        controller: ista.PyEcotrendIsta,
        description: SensorEntityDescription,
        consum: Dict[str, Any],
        unit: str,
        consumSmall: List[Dict[str, Any]],
    ) -> None:
        self._controller = controller
        self._supportCode = controller.getSupportCode()
        self.entity_description = description
        self._consum = consum
        self._consumSmall = consumSmall
        try:
            self._attr_name = "{}".format(self._consum.get("entity_id"))
        except Exception:
            raise Exception("no entity_id, check your settings or ecotrend-isata has no data")
        self._attr_unique_id = self._attr_name
        self._attr_last_reset = datetime.datetime.now()
        self._unit = unit

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return the unit of measurement of this entity, if any."""
        return self._consum.get("unit{}".format(self._unit))

    @property
    def native_value(self) -> StateType:
        """Return the value reported by the sensor."""
        _value = self._consum.get("value{}".format(self._unit), "-1")
        _value = None if _value == "None" else _value
        if _value:
            return float(str(_value).replace(",", "."))
        return _value

    @property
    def device_info(self) -> DeviceInfo:
        """Return a device description for device registry."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._attr_unique_id)},
            manufacturer="ista",
            name=self._attr_name,
        )

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        """Return entity specific state attributes.
        Implemented by platform classes. Convention for attribute names
        is lowercase snake_case.
        """
        history_kwh = {}
        history = {}
        for s in self._consumSmall:
            if self.entity_description.key == (s.get("type", "")) and self._consum.get("entity_id", "-") != s.get(
                "entity_id", "#"
            ):
                history_kwh.update(
                    {
                        "{}-{} kwh".format(s.get("date", {}).get("year", ""), s.get("date", {}).get("month", "")): s.get(
                            "valuekwh", -1.0
                        )
                    }
                )
                history.update(
                    {
                        "{}-{} {}".format(
                            s.get("date", {}).get("year", ""), s.get("date", {}).get("month", ""), s.get("unit", "")
                        ): s.get("value", -1.0)
                    }
                )
        return {
            "unit": self._consum.get("unit", ""),
            "value": float(str(self._consum.get("value", "-1")).replace(",", ".")),
            **history,
            "unitkwh": self._consum.get("unitkwh", ""),
            "valuekwh": float(str(self._consum.get("valuekwh", "-1")).replace(",", ".")),
            **history_kwh,
        }

    @property
    def device_class(self) -> str | None:
        """Return the class of this device, from component DEVICE_CLASSES."""
        return self.entity_description.key
