"""Offline tests for the register map and its decoding.

Runs without Home Assistant or pymodbus installed:

    python3 tests/test_registers.py
"""

import importlib.util
import json
import sys
from pathlib import Path

COMPONENT = Path(__file__).resolve().parents[1] / "custom_components" / "aqotec_rm360"

spec = importlib.util.spec_from_file_location("registers", COMPONENT / "registers.py")
R = importlib.util.module_from_spec(spec)
sys.modules["registers"] = R
spec.loader.exec_module(R)


def test_addresses_unique():
    addresses = [r.address for r in R.REGISTERS]
    assert len(addresses) == len(set(addresses))
    assert len(R.REGISTERS_BY_KEY) == len(R.REGISTERS)


def test_blocks_cover_every_register_once():
    blocks = R.plan_blocks()
    keys = [r.key for b in blocks for r in b.registers]
    assert sorted(keys) == sorted(R.REGISTERS_BY_KEY)
    for block in blocks:
        assert block.count <= R.MAX_BLOCK
        for register in block.registers:
            assert block.start <= register.address
            assert register.address + register.width <= block.start + block.count


def test_float32_is_big_endian_high_word_first():
    energy = R.REGISTERS_BY_KEY["heat_energy"]
    assert R.decode(energy, [0x444C, 0x0000]) == 816.0


def test_int16_signed_and_scaled():
    outdoor = R.REGISTERS_BY_KEY["outdoor_temperature"]
    assert R.decode(outdoor, [92]) == 9.2
    assert R.decode(outdoor, [0x10000 - 4]) == -0.4


def test_whole_degree_registers_are_not_scaled():
    # Measured: charges end at 41.3–41.9 °C at the bottom probe for raw 41.
    assert R.decode(R.REGISTERS_BY_KEY["buffer_bottom_cutoff"], [41]) == 41


def test_probe_faults():
    t20 = R.REGISTERS_BY_KEY["hc2_return"]
    assert R.probe_fault(t20, R.decode(t20, [2550])) == "not_configured"
    assert R.probe_fault(t20, R.decode(t20, [2540])) == "open_circuit"
    assert R.probe_fault(t20, R.decode(t20, [2530])) == "short_circuit"
    assert R.probe_fault(t20, R.decode(t20, [241])) is None
    # 99.0 °C on a setpoint is a value, not a fault.
    limit = R.REGISTERS_BY_KEY["return_limit"]
    assert R.probe_fault(limit, 254.0) is None


def test_fault_bytes():
    # Read from a real controller with several probes not connected.
    values = {"fault_byte_1": 0, "fault_byte_2": 9280, "fault_byte_3": 2559,
              "fault_byte_4": 0}
    assert R.active_faults(values) == [23, 27, 30, 33, 34, 35, 36, 37, 38, 39,
                                       40, 41, 44]
    assert R.active_faults({**values, "fault_byte_4": None}) is None
    assert all(n in R.FAULTS for n in R.active_faults(values))


def test_decode_block_offsets():
    block = next(b for b in R.plan_blocks() if b.start == 43000)
    words = [0] * block.count
    words[0] = 92          # 43000
    words[10] = 2          # 43010
    values = R.decode_block(block, words)
    assert values["outdoor_temperature"] == 9.2
    assert values["station_status"] == 2


def test_every_entity_and_option_is_translated():
    for path in [COMPONENT / "strings.json", *(COMPONENT / "translations").glob("*.json")]:
        entity = json.loads(path.read_text())["entity"]
        names = set(entity["sensor"]) | set(entity["binary_sensor"])
        missing = set(R.REGISTERS_BY_KEY) - names
        assert not missing, (path.name, missing)
        for register in R.REGISTERS:
            if register.options:
                states = entity["sensor"][register.key]["state"]
                assert set(states) == set(register.options.values()), (
                    path.name, register.key)


if __name__ == "__main__":
    failed = 0
    for name, func in sorted(globals().items()):
        if name.startswith("test_") and callable(func):
            try:
                func()
                print(f"ok   {name}")
            except AssertionError as err:
                failed += 1
                print(f"FAIL {name}: {err!r}")
    sys.exit(1 if failed else 0)
