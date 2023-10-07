"""Config flow for ista EcoTrend Version 2."""
from __future__ import annotations

import copy
import logging
from typing import Any

from homeassistant import config_entries, core
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
)
from pyecotrend_ista.exception_classes import LoginError
from pyecotrend_ista.pyecotrend_ista import PyEcotrendIsta
import requests
import voluptuous as vol

from .const import CONF_MFA, CONF_UPDATE_INTERVAL, CONF_URL, DOMAIN, MANUFACTURER
from .const_schema import DATA_SCHEMA_EMAIL, URL_SELECTOR

_LOGGER = logging.getLogger(__name__)


@staticmethod
@core.callback
def login_account(hass: core.HomeAssistant, data: dict, demo: bool = False) -> PyEcotrendIsta:
    """Log into an Ecotrend-Ista account and return an account instance."""
    account = PyEcotrendIsta(
        email=data.get(CONF_EMAIL, None),
        password=data.get(CONF_PASSWORD, None),
        logger=_LOGGER,
        hass_dir=(hass.config.path("custom_components/ecotrend_ista") if demo else None),
        totp=data.get(CONF_MFA, "").replace(" ", ""),
        session=requests.Session(),
    )
    return account


async def validate_input(hass: core.HomeAssistant, data: dict[str, Any]) -> dict[str, str]:
    """Validate the user input allows us to connect.
    Data has the keys from DATA_SCHEMA_EMAIL with values provided by the user.
    """  # noqa: D205
    if CONF_URL not in data or data[CONF_URL] != "de_url":
        raise NotSupportedURL()

    # pylint: disable=no-value-for-parameter
    try:
        vol.Email()(data.get(CONF_EMAIL))
    except vol.Invalid as error:
        raise vol.Invalid(error) from error

    account = login_account(hass, data)

    login_info = None
    try:
        login_info = await hass.async_add_executor_job(account.login)
    except LoginError as error:
        _LOGGER.error(error)
        raise LoginError(error) from error
    except requests.ConnectionError as error:
        _LOGGER.error(error)
        raise requests.ConnectionError from error
    except requests.ReadTimeout as error:
        _LOGGER.error(error)
        raise requests.ReadTimeout from error
    except requests.Timeout as error:
        _LOGGER.error(error)
        raise requests.Timeout from error

    return {
        "title": f"{MANUFACTURER} {account.getSupportCode()} {'' if not login_info or login_info != 'Demo' else login_info}"
    }


class NotSupportedURL(Exception):
    """Custom error class for not supported URL."""


class IstaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for ista EcoTrend Version 2."""

    VERSION = 1

    @staticmethod
    @core.callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Get the options flow for this handler."""
        return IstaOptionsFlowHandler(config_entry)

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        return await self.async_step_german(user_input=user_input)

    async def async_step_german(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            unique_id = f"{user_input[CONF_EMAIL]}"
            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()

            info = None

            try:
                info = await validate_input(self.hass, user_input)
            except LoginError:
                errors["base"] = "auth_inval"
            except NotSupportedURL:
                errors["base"] = "not_allowed"
            except vol.Invalid:
                errors["base"] = "no_email"
            except requests.ConnectionError:
                errors["base"] = "cannot_connect"
            except (requests.ReadTimeout, requests.Timeout):
                errors["base"] = "timeout_connect"
            except Exception:  # pylint: disable=broad-except
                errors["base"] = "unknown"

            if info:
                return self.async_create_entry(
                    title=info["title"],
                    data={
                        CONF_EMAIL: user_input[CONF_EMAIL],
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                        CONF_MFA: user_input.get(CONF_MFA, "").replace(" ", ""),
                    },
                    options={
                        CONF_URL: user_input[CONF_URL],
                        CONF_UPDATE_INTERVAL: user_input[CONF_UPDATE_INTERVAL],
                        # "dev_demo": user_input["dev_demo"],
                    },
                )

        return self.async_show_form(
            step_id="german",
            data_schema=vol.Schema(DATA_SCHEMA_EMAIL),
            errors=errors,
            last_step=True,
        )

    async def async_step_import(self, import_data: dict[str, Any]):
        """Import ista EcoTrend Version 2 config from configuration.yaml."""

        _import_data = copy.deepcopy(import_data)
        _import_data[CONF_PASSWORD] = "*****"
        if import_data is None:
            _LOGGER.error(import_data)
            return self.async_abort(reason="No configuration to import.")
        self._async_abort_entries_match({CONF_EMAIL: import_data[CONF_EMAIL]})
        # Verarbeite die importierten Konfigurationsdaten weiter
        import_data[CONF_URL] = "de_url"
        import_data[CONF_UPDATE_INTERVAL] = 24
        import_data[CONF_MFA] = ""
        _LOGGER.debug("Starting import of sensor from configuration.yaml - %s", _import_data)
        return await self.async_step_german(import_data)


def validate_options_input(user_input: dict[str, Any]) -> dict[str, str]:
    """Validate the user input allows us to connect. Data has the keys from DATA_SCHEMA with values provided by the user."""

    errors = {}
    if CONF_URL not in user_input or user_input[CONF_URL] != "de_url":
        errors["base"] = "not_allowed"
    return errors


class IstaOptionsFlowHandler(config_entries.OptionsFlowWithConfigEntry):
    """Handle a option flow."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle options flow."""
        options = self.options
        errors: dict[str, str] = {}
        data_schema = vol.Schema(
            {
                vol.Required(CONF_URL, default=options.get(CONF_URL, "de_url")): URL_SELECTOR,
                vol.Required(CONF_UPDATE_INTERVAL, default=options.get(CONF_UPDATE_INTERVAL, 24)): NumberSelector(
                    NumberSelectorConfig(mode=NumberSelectorMode.SLIDER, min=1, max=24)
                ),
                # vol.Optional("dev_demo", default=options.get("dev_demo", False)): BooleanSelector(),
            }
        )
        if user_input is not None:
            errors = validate_options_input(user_input)

            if not errors:
                return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(step_id="init", data_schema=data_schema, errors=errors, last_step=True)
