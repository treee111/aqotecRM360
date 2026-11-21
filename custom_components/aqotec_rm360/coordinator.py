"""Data coordinator for the aqotec RM360 integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client import RM360Client, RM360ConnectionError, RM360RegisterError
from .const import DOMAIN, UPDATE_INTERVAL
from .registers import Block, plan_blocks

_LOGGER = logging.getLogger(__name__)


class RM360Coordinator(DataUpdateCoordinator[dict[str, float | int]]):
    """Polls every register block of the controller each cycle."""

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, client: RM360Client
    ) -> None:
        """Initialise the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
            config_entry=entry,
        )
        self.client = client
        self.blocks: list[Block] = plan_blocks()
        # Blocks the controller refused to serve in one piece, presumably
        # because they span addresses it does not define. Read singly from
        # then on rather than failing the same request every cycle.
        self.split_blocks: set[int] = set()

    async def _async_update_data(self) -> dict[str, float | int]:
        """Fetch all registers."""
        data: dict[str, float | int] = {}
        for block in self.blocks:
            split = block.start in self.split_blocks
            try:
                data.update(await self.client.async_read_block(block, split))
            except RM360RegisterError as err:
                _LOGGER.info(
                    "Reading %s registers at %s singly from now on: %s",
                    block.count,
                    block.start,
                    err,
                )
                self.split_blocks.add(block.start)
                try:
                    data.update(await self.client.async_read_block(block, True))
                except RM360ConnectionError as conn_err:
                    raise UpdateFailed(str(conn_err)) from conn_err
            except RM360ConnectionError as err:
                raise UpdateFailed(str(err)) from err
        return data
