"""Modbus TCP access to the RM360 controller."""

from __future__ import annotations

import asyncio
import logging

from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ModbusException

from .registers import REGISTERS_BY_KEY, Block, decode_block

_LOGGER = logging.getLogger(__name__)

TIMEOUT = 5


class RM360Error(Exception):
    """The controller could not be read."""


class RM360ConnectionError(RM360Error):
    """The controller did not accept or keep the connection."""


class RM360RegisterError(RM360Error):
    """The controller answered, but refused the registers asked for."""


class RM360Client:
    """Reads registers over one long-lived connection.

    The controller serves exactly one Modbus TCP client at a time: while one
    is connected, every further connection is reset at once. So the
    connection is opened once and reused, never opened per request, and
    nothing else may poll the controller alongside this integration.
    """

    def __init__(self, host: str, port: int, device_id: int) -> None:
        """Initialise the client; nothing is opened yet."""
        self.host = host
        self.port = port
        self.device_id = device_id
        self._client = AsyncModbusTcpClient(
            host, port=port, timeout=TIMEOUT, retries=1
        )
        self._lock = asyncio.Lock()

    async def async_close(self) -> None:
        """Close the connection, freeing the controller's only slot."""
        self._client.close()

    async def _async_ensure_connected(self) -> None:
        if self._client.connected:
            return
        if not await self._client.connect():
            raise RM360ConnectionError(
                f"Cannot connect to {self.host}:{self.port}. The controller "
                "accepts a single Modbus client; is another one connected?"
            )

    async def async_read(self, address: int, count: int) -> list[int]:
        """Read holding registers with function code 03."""
        async with self._lock:
            await self._async_ensure_connected()
            try:
                result = await self._client.read_holding_registers(
                    address, count=count, device_id=self.device_id
                )
            except ModbusException as err:
                # A dropped link surfaces here; reconnect on the next call.
                self._client.close()
                raise RM360ConnectionError(str(err)) from err

        if result.isError():
            raise RM360RegisterError(
                f"Controller refused {count} register(s) at {address}: {result}"
            )
        if len(result.registers) < count:
            raise RM360RegisterError(
                f"Controller returned {len(result.registers)} of {count} "
                f"register(s) at {address}"
            )
        return list(result.registers)

    async def async_read_block(
        self, block: Block, split: bool
    ) -> dict[str, float | int]:
        """Read a block in one request, or register by register when split."""
        if not split:
            return decode_block(block, await self.async_read(block.start, block.count))

        values: dict[str, float | int] = {}
        for register in block.registers:
            single = Block(register.address, register.width, (register,))
            try:
                words = await self.async_read(register.address, register.width)
            except RM360RegisterError as err:
                _LOGGER.debug("Skipping %s: %s", register.key, err)
                continue
            values.update(decode_block(single, words))
        return values

    async def async_validate(self) -> None:
        """Read the outdoor temperature, to prove this is an RM360."""
        register = REGISTERS_BY_KEY["outdoor_temperature"]
        try:
            await self.async_read(register.address, register.width)
        finally:
            await self.async_close()
