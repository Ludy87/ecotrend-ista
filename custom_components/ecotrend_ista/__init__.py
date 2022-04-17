""" ecotrend-ista """
from __future__ import annotations

import logging
import voluptuous as vol

from datetime import timedelta

from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.helpers import discovery
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import (
    CONF_CONTROLLER,
    CONF_EMAIL,
    CONF_PASSWORD,
    CONF_UPDATE_FREQUENCY,
    DEFAULT_SCAN_INTERVAL_TIME,
    DOMAIN,
)

from pyecotrend_ista import pyecotrend_ista as ista

PLATFORMS = [SENSOR_DOMAIN]
DEFAULT_SCAN_INTERVAL = timedelta(seconds=DEFAULT_SCAN_INTERVAL_TIME)

_LOGGER = logging.getLogger(__name__)

CONTROLLER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): cv.time_period,
    }
)

CONFIG_SCHEMA = vol.Schema(
    {DOMAIN: vol.Schema(vol.All(cv.ensure_list, [CONTROLLER_SCHEMA]))},
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass, config):
    hass.data[CONF_EMAIL] = []
    hass.data[CONF_PASSWORD] = []
    hass.data[CONF_UPDATE_FREQUENCY] = []
    hass.data[DOMAIN] = []
    success = False
    for controller_config in config[DOMAIN]:
        success = success or await _setup_controller(hass, controller_config, config)
    return success


async def _setup_controller(hass: HomeAssistant, controller_config, config: ConfigType) -> bool:
    email: str = controller_config[CONF_EMAIL]
    password: str = controller_config[CONF_PASSWORD]
    eco = ista.PyEcotrendIsta(email=email, password=password)
    await eco.login()
    position = len(hass.data[DOMAIN])
    hass.data[CONF_EMAIL].append(email)
    hass.data[CONF_PASSWORD].append(password)
    hass.data[CONF_UPDATE_FREQUENCY].append(controller_config[CONF_SCAN_INTERVAL])
    hass.data[DOMAIN].append(eco)

    for platform in PLATFORMS:
        hass.async_create_task(
            discovery.async_load_platform(
                hass,
                platform,
                DOMAIN,
                {CONF_CONTROLLER: position, **controller_config},
                config,
            )
        )
    return True
