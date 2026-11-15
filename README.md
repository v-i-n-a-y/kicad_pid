# Rocketry PI&D KiCAD Library

This repository contains a set of P&ID symbols as KiCAD symbols. The symbol set was created for use in rocketry by UK university rocketry teams:

- Kingston University London (KURE)
- Sheffield University (Sunride)
- Glasgow University (GU Rocketry)

We put together this symbol set to standardise our P&ID diagrams for easier collaborations and coherence.

## Maintenance

Since that original collaboration, the library has been updated and taken forward by Vinay Williams, in a personal capacity for his own projects. He is no longer a member of KURE, and this work is not affiliated with or endorsed by KURE or any of the university teams above. Every commit in this repository's history is his. The 2026 revision was carried out by him alone. It added pin numbering, ISA-style reference prefixes, descriptions and keywords, a common connection grid, automated linting, a to-scale symbol registry, and the sized tank, gas cylinder and Swagelok sample cylinder families.

## Symbols

There is one .kicad_sym file per symbol which is contained in the symbols folder. To use, add the relevant .kicad_sym files to your project library.

Alternatively you can download the pid_kicad.kicad_sym file which includes all symbols (automatically keep up-to-date)


## Symbol conventions

Geometry. Each symbol body fits the 10 mm guide box. Two-port inline symbols (valves, pumps, filters and so on) connect at x = -8 mm and x = +8 mm, which gives a 16 mm connection box. Every pin connection point sits on a whole millimetre, so set the schematic connection grid to 1 mm and wires will always land on a pin. Larger items such as tanks and bottles use 20 mm and 50 mm guide boxes in place of the 10 mm one, and keep their connection points on whole millimetres.

Pins. Pins are numbered and named so that a netlist shows flow direction. Inline symbols use 1 IN and 2 OUT, tees and crosses add 3 BRANCH and 4 BRANCH2, relief valves name their vertical outlet VENT, tanks use 1 TOP and 2 BOTTOM, and single-port symbols use 1 PORT (1 PROCESS on instruments). Pin names and numbers are hidden on the schematic. All pins are of type passive.

Instruments. The letters shown inside an instrument bubble come from an editable Function field, so change it to match your own tag, for example from PT to PDT.

### Reference prefixes

The Reference property of each symbol is an ISA style prefix. KiCad appends the annotation number, so the first ball valve placed is V1.

| Prefix | Plain name | Used for |
| --- | --- | --- |
| V | Valve | Valves with no actuator, including three-way, four-way and angle valves |
| HV | Hand valve | Manually operated valves |
| XV | Actuated valve | Hydraulic, pneumatic and servo actuated valves |
| CV | Check valve | Check valves |
| PRV | Pressure relief valve | Pressure relief valves |
| PVRV | Pressure and vacuum relief valve | Pressure and vacuum relief valves |
| PCV | Pressure control valve | Pressure regulators |
| BPR | Back pressure regulator | Back pressure regulators |
| PT | Pressure transmitter | Pressure transducers |
| PI | Pressure indicator | Pressure indicators |
| PS | Pressure switch | Pressure switches |
| TE | Temperature element | RTDs and thermocouples |
| FT | Flow transmitter | Flow transmitters and Coriolis flow meters |
| FI | Flow indicator | Flow indicators |
| LT | Level transmitter | Level transmitters |
| LI | Level indicator | Level indicators |
| TK | Tank | Tanks of all shapes |
| CYL | Cylinder | Gas bottles and sample cylinders |
| QD | Quick disconnect | Quick disconnect couplings |
| BD | Burst disk | Pressure and vacuum burst disks |
| FLT | Filter | Filters |
| P | Pump | Pumps |
| RO | Restriction orifice | Restriction orifices |
| CAV | Cavitating venturi | Cavitating venturis |
| VENT | Vent | Covered and uncovered vents |
| ENG | Engine | Bipropellant, hybrid and solid engines |
| FIT | Fitting | Caps, crosses, elbows, flexible hoses, reducers and tees |
| PYV | Pyrotechnic valve | Normally closed and normally open pyro valves |
| SQB | Squib | Squibs |

## Collaborations

We are open to contribution to the symbol set. Please follow the conventions above. Every symbol also carries a Description and a hidden ki_keywords property, which make it easier to find in the KiCad symbol chooser.

Two make targets help contributors. Run `make normalise` after editing a symbol to apply the conventions (Reference prefix, Description, keywords, stroke width 0.1, pin numbers and names, hidden pin labels) and `make lint` to check them. The lint also runs as a pre-commit hook and fails the commit if any rule is broken. A new symbol needs an entry in the table at the top of `scripts/normalise.py` before the normaliser will accept it.

Note: By contributing you agree to license it under the same MIT license as the rest of kicad_pid

## License

All content is licensed under the MIT license, see the license file.

## In progress

- Script to plot (finish)
- Script to generate README with images for quick viewing (better)
- Footprint rules to ensure standardisation (implement)
- Precommits so individual symbols and the library are up to date (implement)
- CI/CD (implement)
- Addition of templates (add)
