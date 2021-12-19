import logging

import voluptuous as vol

from homeassistant import config_entries, exceptions
from homeassistant.const import CONF_API_KEY, CONF_DELAY
from homeassistant.core import HomeAssistant, callback
import homeassistant.helpers.config_validation as cv

from .blovee import Blovee
from .const import (
    CONF_DISABLE_ATTRIBUTE_UPDATES,
    CONF_OFFLINE_IS_OFF,
    CONF_USE_ASSUMED_STATE,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


async def validate_api_key(user_input):
    api_key = user_input[CONF_API_KEY]
    hub = Blovee(api_key)
    _, error = hub.get_devices()
    if error:
        raise CannotConnect(error)


@config_entries.HANDLERS.register(DOMAIN)
class BloveeFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            try:
                await validate_api_key(user_input)
            except CannotConnect as e:
                _LOGGER.exception("Cannot connect: %s", e)
                errors[CONF_API_KEY] = "cannot connect"
            except Exception as e:
                _LOGGER.exception("Unexpected exception: %s", e)
                errors["base"] = "unknown"

            if not errors:
                return self.async_create_entry(title=DOMAIN, data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_API_KEY): cv.string,
                    vol.Optional(CONF_DELAY, default=10): cv.positive_int,
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow."""
        return BloveeOptionsFlowHandler(config_entry)


class BloveeOptionsFlowHandler(config_entries.OptionsFlow):
    VERSION = 1

    def __init__(self, config_entry) -> None:
        self.config_entry = config_entry
        self.options = dict(config_entry.options)

    async def async_step_user(self, user_input=None):
        """Manage the options."""
        # get the current value for API key for comparison and default value
        old_api_key = self.config_entry.options.get(
            CONF_API_KEY, self.config_entry.data.get(CONF_API_KEY, "")
        )

        errors = {}
        if user_input is not None:
            # check if API Key changed and is valid
            try:
                api_key = user_input[CONF_API_KEY]
                if old_api_key != api_key:
                    await validate_api_key(user_input)

            except CannotConnect as e:
                _LOGGER.exception("Cannot connect: %s", e)
                errors[CONF_API_KEY] = "cannot_connect"
            except Exception as e:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception: %s", e)
                errors["base"] = "unknown"

            if not errors:
                # update options flow values
                self.options.update(user_input)
                return await self._update_options()
                # for later - extend with options you don't want in config but option flow
                # return await self.async_step_options_2()

        options_schema = vol.Schema(
            {
                # to config flow
                vol.Required(
                    CONF_API_KEY,
                    default=old_api_key,
                ): cv.string,
                vol.Optional(
                    CONF_DELAY,
                    default=self.config_entry.options.get(
                        CONF_DELAY, self.config_entry.data.get(CONF_DELAY, 10)
                    ),
                ): cv.positive_int,
                # to options flow
                vol.Required(
                    CONF_USE_ASSUMED_STATE,
                    default=self.config_entry.options.get(CONF_USE_ASSUMED_STATE, True),
                ): cv.boolean,
                vol.Required(
                    CONF_OFFLINE_IS_OFF,
                    default=self.config_entry.options.get(CONF_OFFLINE_IS_OFF, False),
                ): cv.boolean,
                # TODO: validator doesn't work, change to list?
                vol.Optional(
                    CONF_DISABLE_ATTRIBUTE_UPDATES,
                    default=self.config_entry.options.get(
                        CONF_DISABLE_ATTRIBUTE_UPDATES, ""
                    ),
                ): cv.string,
            },
        )

        return self.async_show_form(
            step_id="user",
            data_schema=options_schema,
            errors=errors,
        )

    async def _update_options(self):
        """Update config entry options."""
        return self.async_create_entry(title=DOMAIN, data=self.options)


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""
