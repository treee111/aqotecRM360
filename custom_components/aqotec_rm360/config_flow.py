"""Config flow for the aqotec RM360 integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT

from .client import RM360Client, RM360ConnectionError, RM360RegisterError
from .const import (
    CONF_DEVICE_ID,
    DEFAULT_DEVICE_ID,
    DEFAULT_NAME,
    DEFAULT_PORT,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


def _connection_schema(defaults: dict[str, Any]) -> dict[Any, Any]:
    return {
        vol.Required(CONF_HOST, default=defaults.get(CONF_HOST, vol.UNDEFINED)): str,
        vol.Required(CONF_PORT, default=defaults.get(CONF_PORT, DEFAULT_PORT)): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=65535)
        ),
        vol.Required(
            CONF_DEVICE_ID, default=defaults.get(CONF_DEVICE_ID, DEFAULT_DEVICE_ID)
        ): vol.All(vol.Coerce(int), vol.Range(min=0, max=247)),
    }


async def _async_validate(data: dict[str, Any]) -> str | None:
    """Return an error key, or None when the controller answers."""
    client = RM360Client(data[CONF_HOST], data[CONF_PORT], data[CONF_DEVICE_ID])
    try:
        await client.async_validate()
    except RM360ConnectionError:
        return "cannot_connect"
    except RM360RegisterError:
        return "not_rm360"
    except Exception:  # noqa: BLE001 - surface as a generic error
        _LOGGER.exception("Unexpected error validating the controller")
        return "unknown"
    return None


class RM360ConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle setting up an RM360 controller."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for the controller's address."""
        errors: dict[str, str] = {}

        if user_input is not None:
            user_input[CONF_HOST] = user_input[CONF_HOST].strip()
            self._async_abort_entries_match({CONF_HOST: user_input[CONF_HOST]})
            error = await _async_validate(user_input)
            if error is None:
                name = user_input.pop(CONF_NAME, DEFAULT_NAME)
                return self.async_create_entry(title=name, data=user_input)
            errors["base"] = error

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_NAME, default=DEFAULT_NAME): str,
                    **_connection_schema(user_input or {}),
                }
            ),
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Change the address, for instance after the controller got a new IP."""
        errors: dict[str, str] = {}
        entry = self._get_reconfigure_entry()

        if user_input is not None:
            user_input[CONF_HOST] = user_input[CONF_HOST].strip()
            # The running entry holds the controller's only connection slot;
            # free it for the test, the reload reopens it either way.
            await entry.runtime_data.client.async_close()
            error = await _async_validate(user_input)
            if error is None:
                return self.async_update_reload_and_abort(
                    entry, data_updates=user_input
                )
            errors["base"] = error

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(_connection_schema(user_input or dict(entry.data))),
            errors=errors,
        )
