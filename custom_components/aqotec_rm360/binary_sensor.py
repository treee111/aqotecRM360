"""Binary sensor platform for the aqotec RM360 integration."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import RM360ConfigEntry
from .entity import RM360Entity


def _running(key: str) -> BinarySensorEntityDescription:
    return BinarySensorEntityDescription(
        key=key,
        translation_key=key,
        device_class=BinarySensorDeviceClass.RUNNING,
    )


BINARY_SENSORS: tuple[BinarySensorEntityDescription, ...] = (
    _running("buffer_charge_pump"),
    _running("circulation_pump"),
    _running("hc2_pump"),
    _running("fwm_pump"),
    _running("hc4_pump"),
    # On while hot water is drawn at the fresh water module.
    BinarySensorEntityDescription(
        key="fwm_flow_switch",
        translation_key="fwm_flow_switch",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: RM360ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the RM360 binary sensors."""
    coordinator = entry.runtime_data
    async_add_entities(
        RM360BinarySensor(coordinator, description, Platform.BINARY_SENSOR)
        for description in BINARY_SENSORS
    )


class RM360BinarySensor(RM360Entity, BinarySensorEntity):
    """An output or input of the controller that is either on or off."""

    @property
    def is_on(self) -> bool | None:
        """Return whether the output is switched on."""
        raw = self.raw_value
        return None if raw is None else bool(raw)
