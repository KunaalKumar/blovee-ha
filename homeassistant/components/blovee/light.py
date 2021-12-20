from datetime import timedelta
from enum import unique
import logging
from typing import Union

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    SUPPORT_BRIGHTNESS,
    LightEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_DELAY
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .blovee import Blovee
from .const import CONF_USE_ASSUMED_STATE, DOMAIN
from .dtos import BloveeDevice

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry, async_add_entities: AddEntitiesCallback
):
    _LOGGER.debug("Setting up Blovee lights")
    config = entry.data
    options = entry.options
    hub: Blovee = hass.data[DOMAIN]["hub"]

    update_interval = timedelta(
        seconds=options.get(CONF_DELAY, config.get(CONF_DELAY, 10))
    )

    coordinator = BloveeDataUpdateCoordinator(
        hass, _LOGGER, update_interval=update_interval, config_entry=entry
    )

    # Fetch initial data so we have data when entities subscribe.
    hub.events.new_device += lambda device: async_add_entities(
        [BloveeLightEntity(hub, entry.title, coordinator, device)],
        update_before_add=False,
    )
    await coordinator.async_refresh()

    # Add devices.
    for device in hub.devices.values():
        async_add_entities(
            [BloveeLightEntity(hub, entry.title, coordinator, device)],
            update_before_add=False,
        )


class BloveeDataUpdateCoordinator(DataUpdateCoordinator):
    """Device state update handler."""

    def __init__(
        self,
        hass: HomeAssistant,
        logger,
        update_interval=None,
        *,
        config_entry: ConfigEntry,
    ):
        """Initialize global data updater."""
        self._config_entry = config_entry

        super().__init__(
            hass,
            logger,
            name=DOMAIN,
            update_interval=update_interval,
            update_method=self._async_update,
        )

    @property
    def use_assumed_state(self):
        """Use assumed states."""
        return self._config_entry.options.get(CONF_USE_ASSUMED_STATE, True)

    async def _async_update(self):
        """Fetch data."""
        self.logger.debug("_async_update")
        if DOMAIN not in self.hass.data:
            raise UpdateFailed("Blovee instance not available")
        hub: Blovee = self.hass.data[DOMAIN]["hub"]

        device_states = await hub.get_states()
        for device in device_states:
            if device.err:
                self.logger.warning("update failed for %s: %s", device.name, device.err)
        return device_states


class BloveeLightEntity(LightEntity):
    def __init__(
        self,
        hub: Blovee,
        title: str,
        coordinator: BloveeDataUpdateCoordinator,
        device: BloveeDevice,
    ):
        self._hub = hub
        self._title = title
        self._coordinator = coordinator
        self._device = device

    @property
    def entity_registry_enabled_default(self):
        """Return if the entity should be enabled when first added to the entity registry."""
        return True

    async def async_added_to_hass(self):
        """Connect to dispatcher listening for entity data notifications."""
        _LOGGER.info("Added new device!: %s (%s)", self._device.name, self._title)
        self._coordinator.async_add_listener(self.async_write_ha_state)

    @property
    def supported_features(self):
        """Flag supported features."""
        support_flags = 0
        support_flags |= SUPPORT_BRIGHTNESS
        # if self._device.support_color:
        #     support_flags |= SUPPORT_COLOR
        # if self._device.support_color_tem:
        #     support_flags |= SUPPORT_COLOR_TEMP
        return support_flags

    @property
    def _state(self):
        """Lights internal state."""
        return self._device

    @property
    def unique_id(self):
        return f"blovee_{self._device.mac}"

    @property
    def name(self):
        return self._device.name

    @property
    def device_id(self):
        return self._device.mac

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self.device_id)},
            name=self._device.name,
            manufacturer="Blovee",
            model=self._device.model,
            via_device=(DOMAIN, "Blovee API"),
        )

    @property
    def assumed_state(self):
        """
        Return true if the state is assumed.
        This can be disabled in options.
        """
        return True

    @property
    def is_on(self):
        return self._device.is_on

    @property
    def brightness(self) -> int:
        _LOGGER.info("BRIGTHENSS: %d", self._device.brightness)
        return self._device.brightness

    async def async_turn_on(self, **kwargs) -> None:
        """Turn on lamp."""
        _LOGGER.debug(
            "async_turn_on for Blovee lamp %s, kwargs: %s", self._device, kwargs
        )
        self._device = await self._hub.toggle_power(self._device, True)
        if ATTR_BRIGHTNESS in kwargs:
            brightness = kwargs.pop(ATTR_BRIGHTNESS)
            self._device = await self._hub.set_brightness(self._device, brightness)

    async def async_turn_off(self, **kwargs):
        """Turn on lamp."""
        _LOGGER.debug(
            "async_turn_off for Blovee lamp %s, kwargs: %s", self._device, kwargs
        )
        self._device = await self._hub.toggle_power(self._device, False)
