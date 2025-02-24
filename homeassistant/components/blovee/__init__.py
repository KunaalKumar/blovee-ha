"""Blovee integration."""
import asyncio
import logging

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant

from .blovee import Blovee
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)
CONFIG_SCHEMA = vol.Schema({DOMAIN: vol.Schema({})}, extra=vol.ALLOW_EXTRA)

PLATFORMS = ["light"]


def setup(hass, config):
    """This setup does nothing, we use the async setup."""
    _LOGGER.info("Blovee setup called")
    hass.states.set("blovee.state", "setup called")
    return True


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the Blovee component."""
    _LOGGER.info("Blovee async setup called")
    hass.states.async_set("blovee.state", "async_setup called")
    hass.data[DOMAIN] = {}
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Blovee from a config entry."""

    _LOGGER.info("Blovee async setup entry called")

    # get vars from ConfigFlow/OptionsFlow
    config = entry.data
    options = entry.options
    api_key = options.get(CONF_API_KEY, config.get(CONF_API_KEY, ""))

    # Setup connection with devices/cloud
    hub = Blovee(api_key)

    # keep reference for disposing
    hass.data[DOMAIN] = {}
    hass.data[DOMAIN]["hub"] = hub

    # Verify that passed in configuration works
    await hub.get_devices()

    for component in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, component)
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""

    unload_ok = all(
        await asyncio.gather(
            *[
                _unload_component_entry(hass, entry, component)
                for component in PLATFORMS
            ]
        )
    )

    if unload_ok:
        hass.data[DOMAIN].pop("hub")

    return unload_ok


async def _unload_component_entry(
    hass: HomeAssistant, entry: ConfigEntry, component: str
) -> bool:
    """Unload an entry for a specific component."""
    success = False
    try:
        success = await hass.config_entries.async_forward_entry_unload(entry, component)
    except ValueError:
        # probably ValueError: Config entry was never loaded!
        return success
    except Exception as ex:
        _LOGGER.warning(
            "Continuing on exception when unloading %s component's entry: %s",
            component,
            ex,
        )
    return success
