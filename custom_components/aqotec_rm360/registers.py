"""Register map of the aqotec RM360 controller and how to decode it.

Kept free of Home Assistant imports so it can be tested on its own.

Addresses are the raw holding register numbers the controller documents, read
with function code 03; they are not offset by one. The circuit blocks are not
evenly spaced (HC2 starts at 43054, HC3 at 43088, HC4 at 43134), so addresses
are listed one by one and never derived from each other.

Sources, in order of precedence: aqotec's own register list for the NPS-S
variant, then the Loxone template "EN_aqotec_RM360.02b_TCP_v1" for the few
registers aqotec does not list. Where the two disagree, aqotec wins; where a
register only exists in the template, its entry says so.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass

INT16 = "int16"
UINT16 = "uint16"
FLOAT32 = "float32"

WIDTH = {INT16: 1, UINT16: 1, FLOAT32: 2}

# What a probe input reports instead of a temperature, already scaled to °C.
PROBE_FAULTS = {
    253.0: "short_circuit",
    254.0: "open_circuit",
    255.0: "not_configured",
}

# Registers closer together than this are fetched in one request. Reading
# across a gap touches addresses the controller may not define; if it refuses
# them, the block falls back to single reads (see the coordinator).
MAX_GAP = 8
MAX_BLOCK = 60


@dataclass(frozen=True, kw_only=True)
class Register:
    """One value the controller exposes."""

    key: str
    address: int
    data_type: str = INT16
    scale: float = 1.0
    # A temperature probe input, which reports 253/254/255 for a fault.
    probe: bool = False
    # Code-to-option table for status and mode registers.
    options: dict[int, str] | None = None

    @property
    def width(self) -> int:
        """Return how many 16-bit registers the value occupies."""
        return WIDTH[self.data_type]


def _opts(*names: str, start: int = 0) -> dict[int, str]:
    return {start + i: name for i, name in enumerate(names)}


MIXER = _opts("idle", "opening", "closing")

CIRCUIT_MODE = _opts("auto", "day", "setback", "party", "off")

CIRCUIT_STATUS = _opts(
    "day",
    "setback",
    "party",
    "usage_period",
    "off_outdoor_temperature",
    "off_room_temperature",
    "off_dhw_priority",
    "off_buffer_too_cold",
    "off_external",
    "off_non_usage_period",
    "frost_protection",
    "screed_drying",
    "manual",
)

REGISTERS: tuple[Register, ...] = (
    # --- station (HK0) ---------------------------------------------------
    Register(key="outdoor_temperature", address=43000, scale=0.1, probe=True),
    Register(key="primary_return", address=43001, scale=0.1, probe=True),
    Register(key="secondary_flow", address=43002, scale=0.1, probe=True),
    Register(key="secondary_return", address=43003, scale=0.1, probe=True),
    Register(key="secondary_flow_target", address=43004, scale=0.1),
    Register(key="primary_valve_action", address=43005, options=MIXER),
    Register(key="primary_valve", address=43007),
    Register(key="return_limit", address=43009, scale=0.1),
    Register(
        key="station_status",
        address=43010,
        options=_opts(
            "off", "normal", "return_limit", "power_limit", "external_off", "manual"
        ),
    ),
    # --- heat meter (M-Bus device 1) -------------------------------------
    Register(key="heat_energy", address=43750, data_type=FLOAT32),
    Register(key="heat_volume", address=43752, data_type=FLOAT32),
    Register(key="heat_power", address=43754, data_type=FLOAT32),
    Register(key="heat_flow_rate", address=43756, data_type=FLOAT32),
    Register(key="heat_meter_flow", address=43758, scale=0.01),
    Register(key="heat_meter_return", address=43759, scale=0.01),
    Register(key="heat_meter_delta", address=43760, scale=0.01),
    # Loxone template only.
    Register(key="heat_meter_error", address=43767, data_type=UINT16),
    # --- buffer: SpKr.1 is its hot water zone, SpKr.2 the heating zone ---
    Register(key="buffer_level_1", address=43354, scale=0.1, probe=True),
    Register(key="buffer_top", address=43377, scale=0.1, probe=True),
    Register(key="buffer_level_3", address=43266, scale=0.1, probe=True),
    Register(key="buffer_level_4", address=43268, scale=0.1, probe=True),
    Register(key="buffer_bottom", address=43378, scale=0.1, probe=True),
    Register(key="dhw_zone_charge_target", address=43360),
    Register(
        key="dhw_zone_status",
        address=43363,
        options=_opts(
            "off_charged",
            "frost_protection",
            "charge_pause",
            "minimum_temperature",
            "scheduled",
            "manual_once",
            "contact",
            "forced_by_visu",
            "disinfection_auto",
            "disinfection_contact",
            "disinfection_manual",
            "disinfection_manual_temperature",
            "manual",
        ),
    ),
    # Whole degrees, unlike the probes.
    Register(key="buffer_charge_target", address=43383),
    Register(key="buffer_charge_pump", address=43384),
    Register(key="buffer_charge_valve", address=43385),
    # Loxone template only. The template labels 43391 as tenths of a degree;
    # it is whole degrees — every charge ends with the bottom probe one or two
    # tenths above the raw value.
    Register(key="buffer_top_target", address=43390, scale=0.1),
    Register(key="buffer_bottom_cutoff", address=43391),
    Register(key="buffer_charge_status", address=43392),
    # --- HC1 circulation -------------------------------------------------
    Register(key="circulation_temperature", address=43027, scale=0.1, probe=True),
    Register(key="circulation_pump", address=43029),
    Register(
        key="circulation_status",
        address=43032,
        options=_opts(
            "off", "normal", "temperature_cutoff", "disinfection", "frost_protection",
            start=20,
        ),
    ),
    # --- HC2, first mixed circuit ----------------------------------------
    Register(key="hc2_flow", address=43054, scale=0.1, probe=True),
    Register(key="hc2_flow_target", address=43055, scale=0.1),
    Register(key="hc2_return", address=43056, scale=0.1, probe=True),
    Register(key="hc2_pump", address=43058),
    Register(key="hc2_mixer", address=43059, options=MIXER),
    Register(key="hc2_status", address=43060, options=CIRCUIT_STATUS),
    Register(key="hc2_mode", address=41197, options=CIRCUIT_MODE),
    Register(key="hc2_correction_day", address=41222, data_type=FLOAT32),
    Register(key="hc2_correction_night", address=41224, data_type=FLOAT32),
    # --- HC3, fresh water module -----------------------------------------
    # Flow and target are Loxone template only; this variant has no probe there.
    Register(key="fwm_flow", address=43088, scale=0.1, probe=True),
    Register(key="fwm_flow_target", address=43089, scale=0.1),
    Register(key="dhw_outlet", address=43090, scale=0.1, probe=True),
    # Loxone template only: plain on/off, unlike the speed in 43093.
    Register(key="fwm_pump", address=43092),
    Register(key="fwm_pump_speed", address=43093),
    # Loxone template only.
    Register(key="fwm_flow_switch", address=43115),
    Register(
        key="fwm_status",
        address=43117,
        options=_opts(
            "off",
            "normal",
            "normal_reduced",
            "disinfection_contact",
            "disinfection_period",
            "disinfection_mode",
            "off_overtemperature",
        ),
    ),
    # Unit unconfirmed: aqotec gives none, the Loxone template says l/min.
    Register(key="fwm_flow_rate", address=43125),
    # --- HC4, second mixed circuit ---------------------------------------
    Register(key="hc4_flow", address=43134, scale=0.1, probe=True),
    Register(key="hc4_flow_target", address=43135, scale=0.1),
    Register(key="hc4_return", address=43136, scale=0.1, probe=True),
    Register(key="hc4_pump", address=43138),
    Register(key="hc4_mixer", address=43141, options=MIXER),
    Register(key="hc4_status", address=43143, options=CIRCUIT_STATUS),
    Register(key="hc4_mode", address=41199, options=CIRCUIT_MODE),
    Register(key="hc4_correction_day", address=41230, data_type=FLOAT32),
    Register(key="hc4_correction_night", address=41232, data_type=FLOAT32),
    # --- whole controller ------------------------------------------------
    Register(
        key="station_mode",
        address=41195,
        options=_opts("auto", "heating_only", "dhw_only", "off"),
    ),
    Register(key="correction_day", address=41214, data_type=FLOAT32),
    Register(key="correction_night", address=41216, data_type=FLOAT32),
    Register(key="fault_byte_1", address=43503, data_type=UINT16),
    Register(key="fault_byte_2", address=43504, data_type=UINT16),
    Register(key="fault_byte_3", address=43505, data_type=UINT16),
    Register(key="fault_byte_4", address=43506, data_type=UINT16),
)

REGISTERS_BY_KEY = {register.key: register for register in REGISTERS}

FAULT_BYTE_KEYS = ("fault_byte_1", "fault_byte_2", "fault_byte_3", "fault_byte_4")

# Fault numbers as the controller counts them: bit 0 of fault byte n is
# fault 16·(n−1)+1. Numbers above 45 need controller version 360.02b.
FAULTS: dict[int, str] = {
    1: "Station in return limitation for more than 30 min",
    2: "Station in power limitation for more than 30 min",
    3: "Valve does not close",
    4: "Overtemperature external energy source",
    5: "Overtemperature burner",
    6: "Undertemperature fresh water module",
    7: "Charging module 1 in return limitation for more than 30 min",
    8: "Charging module 2 in return limitation for more than 30 min",
    9: "Heat meter 1 error",
    10: "M-Bus device 2-40 error",
    11: "Station flow target not reached",
    **{11 + hc: f"HC{hc} flow target not reached" for hc in range(2, 9)},
    **{
        19 + i: f"Probe {probe} measurement error"
        for i, probe in enumerate(
            (
                "T10", "T11", "T12", "T13", "T14", "T15", "T16", "T17", "T20",
                "T23", "T24", "3TMP", "3FBT", "4TMP", "4FBT", "5TMP", "5FBT",
                "6TMP", "6FBT", "7TMP", "7FBT", "8TMP", "8FBT",
            )
        )
    },
    42: "FBR360 communication error",
    43: "Sub-controller communication error",
    44: "SpKr.1 disinfection not reached",
    45: "SpKr.2 disinfection not reached",
    46: "Secondary minimum pressure undershot",
    47: "Fault input 1",
    48: "Fault input 2",
    49: "Fault input 3",
    50: "External fault (Modbus or visualisation)",
    51: "Visualisation output 1",
    52: "Visualisation output 2",
    53: "Visualisation output 3",
    54: "Station 2 flow target not reached",
    55: "SpKr.1 target not reached",
    56: "SpKr.2 target not reached",
    57: "HC1 flow target not reached",
}


@dataclass(frozen=True)
class Block:
    """A run of registers fetched with a single request."""

    start: int
    count: int
    registers: tuple[Register, ...]


def plan_blocks(
    registers: tuple[Register, ...] = REGISTERS,
    max_gap: int = MAX_GAP,
    max_block: int = MAX_BLOCK,
) -> list[Block]:
    """Group registers into as few requests as reasonable."""
    blocks: list[Block] = []
    current: list[Register] = []
    start = end = 0

    for register in sorted(registers, key=lambda r: r.address):
        reg_end = register.address + register.width
        if current and (
            register.address - end > max_gap or reg_end - start > max_block
        ):
            blocks.append(Block(start, end - start, tuple(current)))
            current = []
        if not current:
            start = register.address
            end = reg_end
        current.append(register)
        end = max(end, reg_end)

    if current:
        blocks.append(Block(start, end - start, tuple(current)))
    return blocks


def decode(register: Register, words: list[int]) -> float | int:
    """Turn the raw 16-bit words of one register into its scaled value."""
    if register.data_type == FLOAT32:
        # Big endian, high word first — as aqotec documents it.
        return struct.unpack(">f", struct.pack(">HH", words[0], words[1]))[0]
    raw = words[0]
    if register.data_type == INT16 and raw >= 0x8000:
        raw -= 0x10000
    if register.scale == 1:
        return raw
    return round(raw * register.scale, 2)


def probe_fault(register: Register, value: float | int | None) -> str | None:
    """Return why a probe input carries no temperature, or None if it does."""
    if not register.probe or value is None:
        return None
    return PROBE_FAULTS.get(float(value))


def decode_block(block: Block, words: list[int]) -> dict[str, float | int]:
    """Decode every register of a block from the words read for it."""
    values: dict[str, float | int] = {}
    for register in block.registers:
        offset = register.address - block.start
        values[register.key] = decode(
            register, words[offset : offset + register.width]
        )
    return values


def active_faults(values: dict[str, float | int | None]) -> list[int] | None:
    """Return the numbers of all active faults, or None if a byte is missing."""
    faults: list[int] = []
    for index, key in enumerate(FAULT_BYTE_KEYS):
        byte = values.get(key)
        if byte is None:
            return None
        faults.extend(
            16 * index + bit + 1 for bit in range(16) if int(byte) >> bit & 1
        )
    return faults
