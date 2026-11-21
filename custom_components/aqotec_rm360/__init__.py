"""The aqotec RM360 integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant

from .client import RM360Client
from .const import CONF_DEVICE_ID
from .coordinator import RM360Coordinator

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.SENSOR]

type RM360ConfigEntry = ConfigEntry[RM360Coordinator]


async def async_setup_entry(hass: HomeAssistant, entry: RM360ConfigEntry) -> bool:
    """Set up the controller from a config entry."""
    client = RM360Client(
        entry.data[CONF_HOST], entry.data[CONF_PORT], entry.data[CONF_DEVICE_ID]
    )
    coordinator = RM360Coordinator(hass, entry, client)
    # Release the controller's single connection slot on every way out,
    # including a failed first refresh.
    entry.async_on_unload(client.async_close)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: RM360ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
