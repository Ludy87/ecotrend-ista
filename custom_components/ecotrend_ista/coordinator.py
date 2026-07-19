"""Coordinator for ista EcoTrend Version 3."""

from __future__ import annotations

import datetime
from datetime import timedelta
import json
import logging
import os
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from pyecotrend_ista.helper_object_de import CustomRaw
from pyecotrend_ista.pyecotrend_ista import PyEcotrendIsta
import requests

from .config_flow import login_account
from .const import CONF_UPDATE_INTERVAL, CONF_URL, DOMAIN
from .czech_statistics import async_sync_czech_statistics

_LOGGER = logging.getLogger(__name__)


async def create_directory_file(hass: HomeAssistant, consum_raw: CustomRaw, support_code: str):
    """Create a directory and a file with JSON content."""
    paths = [hass.config.path("www")]

    def mkdir() -> None:
        """Create directories if they do not exist."""
        for path in paths:
            if not os.path.exists(path):
                _LOGGER.debug("Creating directory: %s", path)
                os.makedirs(path, exist_ok=True)

    def make_file() -> None:
        """Create a JSON file with the data."""
        file_name = f"{DOMAIN}_{support_code}.json"
        media_path = hass.config.path("www")
        json_object = json.dumps(consum_raw.to_dict(), indent=4)
        with open(f"{media_path}/{file_name}", mode="w", encoding="utf-8") as f_lie:
            f_lie.write(json_object)

    await hass.async_add_executor_job(mkdir)
    await hass.async_add_executor_job(make_file)


class IstaDataUpdateCoordinator(DataUpdateCoordinator):
    """Coordinator for ista EcoTrend Version 3."""

    controller: PyEcotrendIsta

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize ista EcoTrend Version 3 data updater."""
        self._entry = entry
        self.czech_data: dict[str, Any] | None = None
        super().__init__(
            hass=hass,
            logger=_LOGGER,
            name=f"{DOMAIN}-{entry.entry_id}",
            update_method=self._async_update_data,
            update_interval=timedelta(hours=self._entry.options.get(CONF_UPDATE_INTERVAL, 24)),
        )

    def set_controller(self) -> None:
        """Set up the PyEcotrendIsta controller.

        This method initializes the PyEcotrendIsta controller instance with the provided email, password,
        and other necessary configurations.
        """
        data = dict(self._entry.data)
        data[CONF_URL] = self._entry.options.get(CONF_URL, "de_url")
        self.controller = login_account(
            self.hass,
            data,
            self._entry.options.get("dev_demo", False),
        )

    async def init(self) -> None:
        """Initialize the controller and perform the login."""
        self.set_controller()
        await self.hass.async_add_executor_job(self.controller.login)

    async def _async_update_data(self):
        """Update the data from ista EcoTrend Version 3."""
        try:
            if self.data is None:
                self.data = {}
            is_czech = self._entry.options.get(CONF_URL, "de_url") == "cz_url"
            reuse_initial_login = (
                is_czech
                and self.czech_data is None
                and hasattr(self, "controller")
                and self.controller.access_token is not None
            )
            if not reuse_initial_login:
                await self.init()

            if is_czech:
                self.czech_data = await self.hass.async_add_executor_job(self.controller.get_home_assistant_data)
                await async_sync_czech_statistics(
                    self.hass,
                    self.controller.get_support_code(),
                    self.czech_data.get("aggregates", {}),
                )
                return self.czech_data

            for uuid in self.controller.get_uuids():
                _consum_raw: dict[str, Any] = await self.hass.async_add_executor_job(
                    self.controller.consum_raw,
                    [
                        datetime.datetime.now().year,
                        datetime.datetime.now().year - 1,
                    ],
                    None,
                    True,
                    uuid,
                )
                if not isinstance(_consum_raw, dict):
                    return self.data[uuid]
                consum_raw: CustomRaw = CustomRaw.from_dict(_consum_raw)

                await create_directory_file(
                    self.hass,
                    consum_raw,
                    self.controller.get_support_code(),
                )
                self.data[uuid] = consum_raw
            self.async_set_updated_data(self.data)
            return self.data
        except requests.Timeout as error:
            raise UpdateFailed("Timeout while communicating with ista EcoTrend") from error
