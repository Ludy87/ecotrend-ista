"""Const for ista EcoTrend Version 2."""
from __future__ import annotations

from typing import Final

DOMAIN = "ecotrend_ista"
MANUFACTURER: Final = "Ista"

DEVICE_NAME: Final = "ista EcoTrend®"

# DEMO_EMAIL = "demo@ista.de"
# DEMO_PASSWORD = "Ausprobieren!"

DATA_HASS_CONFIG: Final = "hass_config"

TRACKER_UPDATE_STR: Final = f"{DOMAIN}_tracker_update"

# Deprecated config
CONF_UNIT = "unit"
CONF_UNIT_HEATING = "unit_heating"
CONF_UNIT_WARMWATER = "unit_warmwater"
CONF_YEARMONTH = "yearmonth"
CONF_YEAR = "year"
# Deprecated config

CONF_URL: Final = "URL"
CONF_UPDATE_INTERVAL: Final = "update_interval"

CONF_TYPE_HEATING: Final = "heating"
CONF_TYPE_HEATING_CASH: Final = "heating_costs"
CONF_TYPE_HEATING_CUSTOM: Final = "heating_custom"

CONF_TYPE_HEATWATER: Final = "warmwater"
CONF_TYPE_HEATWATER_CASH: Final = "warmwater_costs"
CONF_TYPE_HEATWATER_CUSTOM: Final = "warmwater_custom"

CONF_TYPE_WATER: Final = "water"
CONF_TYPE_WATER_CASH: Final = "water_costs"
CONF_TYPE_WATER_CUSTOM: Final = "water_custom"
