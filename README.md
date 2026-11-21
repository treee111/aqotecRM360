# aqotec RM360 for Home Assistant

[![HACS custom repository][hacs-badge]][hacs-url]
[![HACS validation][hacs-ci-badge]][hacs-ci-url]
[![hassfest][hassfest-badge]][hassfest-url]
[![License: MIT][license-badge]](LICENSE)

Home Assistant integration for the **aqotec RM360** controller, as found in aqotec
district heating substations (aqoClick and others). Reads the controller over
Modbus TCP: station and heat meter, buffer, hot water, and the mixed heating
circuits, with status codes as readable states instead of numbers.

Read-only. Nothing is written to the controller.

## Entities

| Group | Entities |
|---|---|
| Station | outdoor, primary return, secondary flow/return and target, primary valve, return temperature limit, status, mode, general day/night correction |
| Heat meter | energy (`total_increasing`, ready for the energy dashboard), volume, power, flow rate, flow/return temperature, temperature difference |
| Buffer | five levels (T13, T23, 7TMP, 7FBT, T24), top target, bottom cut-off, charge target, charge pump, charge valve |
| Hot water | fresh water module status, pump, pump speed, outlet temperature, hot water draw, circulation temperature, pump and status |
| HC2 / HC4 | flow, flow target, return, pump, mixer, status, mode, day/night correction |
| Faults | number of active faults, listed by number and description (in aqotec's German wording when Home Assistant runs in German); the four raw fault bytes as diagnostics |

Status and mode registers become enum sensors (*Day*, *Setback*, *Off: external /
frost protection*, …), with the raw code kept as the `code` attribute. Pumps are
binary sensors.

A probe input with nothing connected does not report 254 °C: the controller's
fault values 253 (short circuit), 254 (open circuit) and 255 (not configured)
turn the sensor *unknown*, and the reason is in its `probe_fault` attribute.

Entity ids are fixed and language independent: `sensor.rm360_<key>`, e.g.
`sensor.rm360_buffer_top` or `binary_sensor.rm360_hc2_pump`.

## Before you start

On the controller (service level 3):

- parameter **914** "Modbusabfrage" = **TCPIP**
- a fixed IP address (parameter 773)
- reading happens on **port 502**

**The controller serves exactly one Modbus TCP client.** While one is connected,
every further connection is reset immediately. Remove any other Modbus
configuration for the controller (a YAML `modbus:` entry, Node-RED, a Loxone
Miniserver…) before setting this integration up, or both will fail
intermittently.

Modbus runs on one interface only. If the operator reads the controller through
the aqotec protocol on COM-A, Modbus TCP over Ethernet is the combination that
leaves that untouched; Modbus RTU on COM-A would not.

## Installation

### HACS

1. HACS → ⋮ → *Custom repositories*
2. Add `https://github.com/treee111/aqotecRM360`, category *Integration*
3. Install "aqotec RM360", then restart Home Assistant

### Manual

Copy `custom_components/aqotec_rm360/` into `<config>/custom_components/` and
restart Home Assistant.

## Setup

*Settings → Devices & Services → Add Integration → aqotec RM360*, then enter the
controller's IP address. Port 502 and unit id 1 are the defaults. A changed IP
address can be entered later through *Reconfigure*, without losing anything.

## Moving over from a YAML `modbus:` setup

History follows the entity id, not the integration. Renaming an entity moves its
recorded states and long-term statistics along with it, so an existing setup can
be carried over:

1. Rename each old entity to the id this integration will use, e.g.
   `sensor.heating_buffer_top` → `sensor.rm360_buffer_top`. Do this while the old
   entities still exist; the history moves with them.
2. Remove the `modbus:` entry for the controller and restart. The renamed
   entities are now orphaned; delete them from the entity registry. Their
   history stays in the database.
3. Add this integration. Its entities are created with exactly those ids and
   continue the existing series.

The order matters. Renaming *after* the integration has created its entities
fails for the statistics, because the target id is then already taken.

Only sensor-to-sensor moves keep their history. Pumps become binary sensors
here, and a change of domain cannot carry history over. Status sensors that used
to hold numbers hold text from the switch on; the old numbers stay visible in
the history before that date.

## How it works

The registers are listed one by one in `registers.py`, with their source. They
come from aqotec's register list for the controller; a few that aqotec does not
list come from the Loxone template "EN_aqotec_RM360.02b_TCP_v1" and are marked
as such. The circuit blocks are not evenly spaced, so addresses are never derived
from each other.

Every 30 s the integration reads all registers over one persistent connection,
grouped into twelve requests. If the controller refuses a group — because it
spans addresses it does not define — that group is read register by register
from then on, and a single refused register leaves only its own entity
unavailable.

Two findings that differ from the Loxone template:

- **43391**, the buffer's bottom cut-off temperature, is in whole degrees, not
  tenths: every charge ends with the bottom probe a few tenths above the raw
  value.
- **43117** is the fresh water module status. The template's candidate, 43097,
  never changes.

Fault byte *n*, bit *b* is fault number 16·(*n*−1)+*b*+1.

## Writing

Not supported yet. aqotec allows changing a register at most once every ten
minutes (about 150 times a day), each change read back and verified, because
every write goes straight to the controller's EEPROM. A later version may add
this with that limit built in.

## Development

```
python3 tests/test_registers.py
```

Runs without Home Assistant or pymodbus.

[hacs-badge]: https://img.shields.io/badge/HACS-Custom-41BDF5.svg
[hacs-url]: https://hacs.xyz/docs/faq/custom_repositories
[hacs-ci-badge]: https://github.com/treee111/aqotecRM360/actions/workflows/validate.yaml/badge.svg
[hacs-ci-url]: https://github.com/treee111/aqotecRM360/actions/workflows/validate.yaml
[hassfest-badge]: https://github.com/treee111/aqotecRM360/actions/workflows/hassfest.yaml/badge.svg
[hassfest-url]: https://github.com/treee111/aqotecRM360/actions/workflows/hassfest.yaml
[license-badge]: https://img.shields.io/badge/License-MIT-yellow.svg
