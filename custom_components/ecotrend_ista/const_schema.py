"""Const schema for ista EcoTrend Version 2."""
from __future__ import annotations

from homeassistant.const import CONF_EMAIL, CONF_PASSWORD, CONF_SCAN_INTERVAL
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)
import voluptuous as vol

from .const import (
    CONF_MFA,
    CONF_UNIT,
    CONF_UNIT_HEATING,
    CONF_UNIT_WARMWATER,
    CONF_UPDATE_INTERVAL,
    CONF_URL,
    CONF_YEAR,
    CONF_YEARMONTH,
)

URL_SELECTORS = {
    "de_url": "https://ecotrend.ista.de/",
    # "nl_url": "https://mijn.ista.nl/",
    # "fr_url": "https://ma-consommation.ista.lu/",
}

URL_SELECTOR: SelectSelector = SelectSelector(
    SelectSelectorConfig(
        options=[SelectOptionDict(value=k, label=v) for k, v in URL_SELECTORS.items()],
        multiple=False,
        mode=SelectSelectorMode.DROPDOWN,
    )
)

DATA_SCHEMA_EMAIL = {
    vol.Required(CONF_EMAIL): TextSelector(TextSelectorConfig(type=TextSelectorType.EMAIL, multiline=False)),
    vol.Required(CONF_PASSWORD): TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD, multiline=False)),
    vol.Required(CONF_URL, default="de_url"): URL_SELECTOR,
    vol.Optional(CONF_MFA, default=""): TextSelector(TextSelectorConfig(type=TextSelectorType.TEXT, multiline=False)),
    vol.Required(CONF_UPDATE_INTERVAL, default=24): NumberSelector(
        NumberSelectorConfig(mode=NumberSelectorMode.SLIDER, min=1, max=24)
    ),
    # vol.Optional("dev_demo", default=False): BooleanSelector()
}

# remove Deprecated config
DEFAULT_DATA_SCHEMA = {
    vol.Remove(CONF_UNIT_HEATING): vol.Any(str, None),
    vol.Remove(CONF_UNIT_WARMWATER): vol.Any(str, None),
    vol.Remove(CONF_YEAR): vol.Any(str, list, dict, None),
    vol.Remove(CONF_YEARMONTH): vol.Any(str, list, dict, None),
    vol.Remove(CONF_SCAN_INTERVAL): vol.Any(int, None),
    vol.Remove(CONF_UNIT): vol.Any(str, None),
}

DEFAULT_DATA_SCHEMA.update(DATA_SCHEMA_EMAIL)
