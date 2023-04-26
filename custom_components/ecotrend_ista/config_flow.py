"""Config flow for ecotrend-ista Version 2."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from pyecotrend_ista.exception_classes import Error, LoginError
from pyecotrend_ista.pyecotrend_ista import PyEcotrendIsta

import homeassistant.helpers.config_validation as cv
from homeassistant import config_entries, core
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD

from .const import DEMO_EMAIL, DEMO_PASSWORD, DOMAIN, MANUFACTURER

_LOGGER = logging.getLogger(__name__)


async def validate_input(hass: core.HomeAssistant, data: dict[str, Any]) -> dict[str, str]:
    """Validate the user input allows us to connect.
    Data has the keys from DATA_SCHEMA with values provided by the user.
    """

    account = PyEcotrendIsta(
        email=data.get(CONF_EMAIL, None),
        password=data.get(CONF_PASSWORD, None),
        logger=_LOGGER,
        hass_dir=hass.config.path("custom_components/ecotrend_ista"),
    )

    try:
        log = await account.login()
    except LoginError as error:
        _LOGGER.error(error)
        raise Error(error)

    return {"title": f"{MANUFACTURER} {account.getSupportCode()}"}


DATA_SCHEMA_EMAIL = {
    vol.Required(CONF_EMAIL, default=DEMO_EMAIL): cv.string,  # type: ignore
    vol.Required(CONF_PASSWORD, default=DEMO_PASSWORD): cv.string,  # type: ignore
}


class IstaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for ecotrend-ista Version 2."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""

        errors: dict[str, str] = {}

        if user_input is not None:
            unique_id = f"{user_input[CONF_EMAIL]}"
            self.entry = await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()

            info = None

            try:
                info = await validate_input(self.hass, user_input)
            except Error:
                errors["base"] = "auth_inval"

            if info:
                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(step_id="user", data_schema=vol.Schema(DATA_SCHEMA_EMAIL), errors=errors, last_step=False)
