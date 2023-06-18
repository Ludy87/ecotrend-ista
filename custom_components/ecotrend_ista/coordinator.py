"""Coordinator for ista EcoTrend Version 2"""
from __future__ import annotations

import asyncio
import datetime
import logging
from datetime import timedelta

from pyecotrend_ista.helper_object import CustomRaw
from pyecotrend_ista.pyecotrend_ista import PyEcotrendIsta
from .config_flow import login_account

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import CONF_UPDATE_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class IstaDataUpdateCoordinator(DataUpdateCoordinator):
    """Coordinator for ista EcoTrend Version 2."""

    controller: PyEcotrendIsta

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize ista EcoTrend Version 2 data updater."""
        self._entry = entry
        super().__init__(
            hass=hass,
            logger=_LOGGER,
            name=f"{DOMAIN}-{entry.entry_id}",
            update_method=self._async_update_data,
            update_interval=timedelta(hours=self._entry.options.get(CONF_UPDATE_INTERVAL, 24)),
        )

    async def set_controller(self) -> None:
        """
        Set up the PyEcotrendIsta controller.

        This method initializes the PyEcotrendIsta controller instance with the provided email, password,
        and other necessary configurations.
        """
        data = self._entry.data
        self.controller = login_account(self.hass, data, self._entry.options.get("dev_demo", False))

    async def init(self) -> None:
        """Initialize the controller and perform the login."""
        await self.set_controller()
        await self.controller.login()

    async def _async_update_data(self):
        """Update the data from ista EcoTrend Version 2."""
        try:
            await self.init()
            consum_raw: CustomRaw = CustomRaw.from_dict(
                await self.controller.consum_raw(select_year=[datetime.datetime.now().year])
            )
            self.data = consum_raw
            self.async_set_updated_data(self.data)
            return self.data
        except asyncio.TimeoutError:
            pass
