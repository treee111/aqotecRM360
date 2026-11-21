"""Diagnostics support for the aqotec RM360 integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant

from . import RM360ConfigEntry

TO_REDACT = {CONF_HOST}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: RM360ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data
    return {
        "entry": async_redact_data(dict(entry.data), TO_REDACT),
        "blocks": [
            {
                "start": block.start,
                "count": block.count,
                "split": block.start in coordinator.split_blocks,
            }
            for block in coordinator.blocks
        ],
        "data": coordinator.data,
    }
