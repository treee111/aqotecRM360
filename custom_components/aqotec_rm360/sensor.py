"""Sensor platform for the aqotec RM360 integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    Platform,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfVolume,
    UnitOfVolumeFlowRate,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import RM360ConfigEntry
from .entity import RM360Entity
from .registers import FAULTS, REGISTERS_BY_KEY, active_faults, probe_fault


@dataclass(frozen=True, kw_only=True)
class RM360SensorDescription(SensorEntityDescription):
    """Describes a sensor backed by one register."""


def _temperature(key: str, precision: int = 1, **kwargs: Any) -> RM360SensorDescription:
    return RM360SensorDescription(
        key=key,
        translation_key=key,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=precision,
        **kwargs,
    )


def _percent(key: str, **kwargs: Any) -> RM360SensorDescription:
    return RM360SensorDescription(
        key=key,
        translation_key=key,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        **kwargs,
    )


def _enum(key: str, **kwargs: Any) -> RM360SensorDescription:
    options = REGISTERS_BY_KEY[key].options
    assert options is not None
    return RM360SensorDescription(
        key=key,
        translation_key=key,
        device_class=SensorDeviceClass.ENUM,
        options=list(options.values()),
        **kwargs,
    )


def _correction(key: str) -> RM360SensorDescription:
    # Steps on the controller's own correction scale, not kelvin: one step
    # moves the flow target by several kelvin, depending on the heating curve.
    return RM360SensorDescription(
        key=key,
        translation_key=key,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    )


def _diagnostic(key: str) -> RM360SensorDescription:
    return RM360SensorDescription(
        key=key,
        translation_key=key,
        entity_category=EntityCategory.DIAGNOSTIC,
    )


SENSORS: tuple[RM360SensorDescription, ...] = (
    # station
    _temperature("outdoor_temperature"),
    _temperature("primary_return"),
    _temperature("secondary_flow"),
    _temperature("secondary_return"),
    _temperature("secondary_flow_target"),
    _enum("primary_valve_action", entity_category=EntityCategory.DIAGNOSTIC),
    _percent("primary_valve"),
    _temperature("return_limit"),
    _enum("station_status"),
    _enum("station_mode"),
    _correction("correction_day"),
    _correction("correction_night"),
    # heat meter
    RM360SensorDescription(
        key="heat_energy",
        translation_key="heat_energy",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=0,
    ),
    RM360SensorDescription(
        key="heat_volume",
        translation_key="heat_volume",
        native_unit_of_measurement=UnitOfVolume.CUBIC_METERS,
        device_class=SensorDeviceClass.WATER,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=2,
    ),
    RM360SensorDescription(
        key="heat_power",
        translation_key="heat_power",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    RM360SensorDescription(
        key="heat_flow_rate",
        translation_key="heat_flow_rate",
        native_unit_of_measurement=UnitOfVolumeFlowRate.LITERS_PER_HOUR,
        device_class=SensorDeviceClass.VOLUME_FLOW_RATE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
    _temperature("heat_meter_flow"),
    _temperature("heat_meter_return"),
    # A difference: kelvin under the temperature device class would be
    # converted as an absolute temperature.
    RM360SensorDescription(
        key="heat_meter_delta",
        translation_key="heat_meter_delta",
        native_unit_of_measurement="K",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    _diagnostic("heat_meter_error"),
    # buffer
    _temperature("buffer_level_1"),
    _temperature("buffer_top"),
    _temperature("buffer_level_3"),
    _temperature("buffer_level_4"),
    _temperature("buffer_bottom"),
    _temperature("buffer_top_target"),
    _temperature("buffer_bottom_cutoff", precision=0),
    _temperature("buffer_charge_target", precision=0),
    _percent("buffer_charge_valve"),
    _diagnostic("buffer_charge_status"),
    _temperature("dhw_zone_charge_target", precision=0),
    _enum("dhw_zone_status"),
    # circulation
    _temperature("circulation_temperature"),
    _enum("circulation_status"),
    # HC2
    _temperature("hc2_flow"),
    _temperature("hc2_flow_target"),
    _temperature("hc2_return"),
    _enum("hc2_mixer", entity_category=EntityCategory.DIAGNOSTIC),
    _enum("hc2_status"),
    _enum("hc2_mode"),
    _correction("hc2_correction_day"),
    _correction("hc2_correction_night"),
    # fresh water module
    _temperature("fwm_flow"),
    _temperature("fwm_flow_target"),
    _temperature("dhw_outlet"),
    _percent("fwm_pump_speed"),
    _enum("fwm_status"),
    RM360SensorDescription(
        key="fwm_flow_rate",
        translation_key="fwm_flow_rate",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    # HC4
    _temperature("hc4_flow"),
    _temperature("hc4_flow_target"),
    _temperature("hc4_return"),
    _enum("hc4_mixer", entity_category=EntityCategory.DIAGNOSTIC),
    _enum("hc4_status"),
    _enum("hc4_mode"),
    _correction("hc4_correction_day"),
    _correction("hc4_correction_night"),
    # faults
    _diagnostic("fault_byte_1"),
    _diagnostic("fault_byte_2"),
    _diagnostic("fault_byte_3"),
    _diagnostic("fault_byte_4"),
)

FAULTS_SENSOR = RM360SensorDescription(
    key="faults",
    translation_key="faults",
    state_class=SensorStateClass.MEASUREMENT,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: RM360ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the RM360 sensors."""
    coordinator = entry.runtime_data
    entities: list[SensorEntity] = [
        RM360Sensor(coordinator, description, Platform.SENSOR)
        for description in SENSORS
    ]
    entities.append(RM360FaultsSensor(coordinator, FAULTS_SENSOR, Platform.SENSOR))
    async_add_entities(entities)


class RM360Sensor(RM360Entity, SensorEntity):
    """A single register of the controller."""

    entity_description: RM360SensorDescription

    @property
    def native_value(self) -> float | int | str | None:
        """Return the value, translated to an option for status registers."""
        raw = self.raw_value
        register = REGISTERS_BY_KEY[self.entity_description.key]
        if register.options is not None:
            return None if raw is None else register.options.get(int(raw))
        if probe_fault(register, raw):
            return None
        return raw

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Explain a missing value: a probe fault or an undocumented code."""
        raw = self.raw_value
        register = REGISTERS_BY_KEY[self.entity_description.key]
        if raw is None:
            return None
        if register.options is not None:
            return {"code": int(raw)}
        if fault := probe_fault(register, raw):
            return {"probe_fault": fault}
        return None


class RM360FaultsSensor(RM360Entity, SensorEntity):
    """How many faults are active, with their numbers and descriptions."""

    @property
    def raw_value(self) -> float | int | None:
        """Derived from the four fault bytes rather than read directly."""
        faults = self._faults
        return None if faults is None else len(faults)

    @property
    def _faults(self) -> list[int] | None:
        if not self.coordinator.data:
            return None
        return active_faults(self.coordinator.data)

    @property
    def native_value(self) -> int | None:
        """Return the number of active faults."""
        faults = self._faults
        return None if faults is None else len(faults)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """List the active faults."""
        faults = self._faults
        if faults is None:
            return None
        return {
            "faults": [
                f"{number}: {FAULTS.get(number, 'undocumented')}" for number in faults
            ]
        }

