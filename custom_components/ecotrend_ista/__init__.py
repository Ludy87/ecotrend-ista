"""ista EcoTrend Version 3."""

from __future__ import annotations

import logging

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD, Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.typing import ConfigType

from .const import DATA_HASS_CONFIG, DOMAIN
from .const_schema import DEFAULT_DATA_SCHEMA
from .coordinator import IstaDataUpdateCoordinator

PLATFORMS = [Platform.SENSOR]

_LOGGER = logging.getLogger(__name__)


CONFIG_SCHEMA = vol.Schema(
    {DOMAIN: vol.Schema(DEFAULT_DATA_SCHEMA)},
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: HomeAssistant, hass_config: ConfigType) -> bool:
    """Set up the ista EcoTrend Version 3 component."""
    _LOGGER.debug("Set up the ista EcoTrend Version 3 component")
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][DATA_HASS_CONFIG] = hass_config
    if DOMAIN in hass_config:
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": config_entries.SOURCE_IMPORT},
                data={
                    CONF_EMAIL: hass_config[DOMAIN][CONF_EMAIL],
                    CONF_PASSWORD: hass_config[DOMAIN][CONF_PASSWORD],
                },
            )
        )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Configure based on config entry."""
    _LOGGER.debug("Configure based on config entry %s", entry.entry_id)
    coordinator = IstaDataUpdateCoordinator(hass, entry)
    await coordinator.init()
    for uuid in coordinator.controller.getUUIDs():
        await _async_migrate_entries(
            hass,
            entry,
            uuid,
            coordinator.controller.getSupportCode(),
        )
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(options_update_listener))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("Unload a config entry")
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


async def options_update_listener(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    """Handle options update."""
    _LOGGER.debug("Configuration options updated, reloading ista EcoTrend 3 integration")
    await hass.config_entries.async_reload(config_entry.entry_id)


async def _async_migrate_entries(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    new_uid: str,
    support_code: str,
) -> bool:
    """Migrate old entry."""
    entity_registry = er.async_get(hass)

    @callback
    def update_unique_id(entry: er.RegistryEntry) -> dict[str, str] | None:
        if support_code in str(entry.unique_id):
            # heating_custom_{support_code} old
            # heating_custom_{new_uid} new
            new_unique_id = str(entry.unique_id).replace(support_code, new_uid).replace("-", "_").replace(" ", "_").lower()
            _LOGGER.debug(
                "change unique_id - entity: '%s' unique_id from '%s' to '%s'",
                entry.entity_id,
                entry.unique_id,
                new_unique_id,
            )
            if existing_entity_id := entity_registry.async_get_entity_id(entry.domain, entry.platform, new_unique_id):
                _LOGGER.debug("Cannot change unique_id to '%s', already exists for '%s'", new_unique_id, existing_entity_id)
                return None
            return {"new_unique_id": new_unique_id}
        return None

    await er.async_migrate_entries(hass, config_entry.entry_id, update_unique_id)

    return True
