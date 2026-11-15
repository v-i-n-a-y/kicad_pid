# Rocketry PI&D KiCAD Library

This repository contains a set of P&ID symbols as KiCAD symbols. The symbol set was created for use in rocketry by UK university rocketry teams:

- Kingston University London (KURE)
- Sheffield University (Sunride)
- Glasgow University (GU Rocketry)

We put together this symbol set to standardise our P&ID diagrams for easier collaborations and coherence.

## Installation

[Download the latest release](https://github.com/v-i-n-a-y/kicad_pid/releases/latest). It works with KiCad 8.0 and later on Windows, macOS and Linux. Pick the file for your system, where VERSION is the release number.

| System | File to download | How to run |
| --- | --- | --- |
| Any, no Python needed | kicad_pid-VERSION.zip | In KiCad, Plugin and Content Manager, Install from File |
| Windows | kicad_pid-VERSION-windows.zip | Unzip it and double-click install.bat |
| macOS | kicad_pid-VERSION-macos.zip | Unzip it and double-click install.command, or if macOS refuses, type `sh` and a space in Terminal, drag install.command in and press Enter |
| Linux | kicad_pid-VERSION-linux.tar.gz | Unpack it and run ./install.sh |

The system downloads need Python 3. Each also holds pid_registry.pdf, a to-scale reference of every symbol, and a checksum of every file is in SHA256SUMS.txt.

### Route 1, KiCad package (recommended)

The package needs no Python and is installed and removed from inside KiCad.

1. Download kicad_pid-VERSION.zip from the release page. Do not unzip it.
2. In the KiCad main window open Plugin and Content Manager.
3. Choose Install from File and pick the zip.
4. Open the symbol chooser in the schematic editor and look for the P&ID symbols.

To remove it, find Rocketry P&ID Symbols in the Installed tab of the same window and uninstall it.

KiCad adds a prefix to the names of libraries that come from packages (PCM_ by default, set in Preferences under Packages and Updates), so this route normally lists the library as PCM_pid_kicad. Routes 2 and 3 name it pid_kicad. Choose one route and stay with it, because symbols placed from one name will not follow a library with the other.

### Route 2, installer script

If you have cloned this repository, or unpacked a system download, one command installs the library for your user account and adds it to the global symbol library table of every KiCad version it finds (the table is backed up first, and running it again changes nothing). Close KiCad first and restart it afterwards.

Windows, in a command prompt:

```
py -3 scripts\install.py
```

macOS, in Terminal:

```
python3 scripts/install.py
```

Linux, in a terminal:

```
python3 scripts/install.py
```

In an unpacked system download the script sits beside the launcher, so use install.py in place of scripts/install.py. The install.bat and install.sh launchers at the top of the repository do the same thing. Add `--dry-run` to see what would change without changing anything, `--uninstall` to remove the library and its table entries, `--kicad-version 9.0` to touch one KiCad version only, or `--nickname NAME` to use another library name.

### Route 3, by hand

1. Download pid_kicad.kicad_sym and keep it somewhere permanent.
2. In KiCad choose Preferences, Manage Symbol Libraries.
3. On the Global Libraries tab choose Add existing library to table (the folder icon), pick pid_kicad.kicad_sym and set the nickname to pid_kicad.
4. Choose OK.

To use it in a single project, do the same on the Project Specific Libraries tab.

## Maintenance

Since that original collaboration, the library has been updated and taken forward by Vinay Williams, in a personal capacity for his own projects. He is no longer a member of KURE, and this work is not affiliated with or endorsed by KURE or any of the university teams above. Every commit in this repository's history is his. The 2026 revision was carried out by him alone. It added pin numbering, ISA-style reference prefixes, descriptions and keywords, a common connection grid, automated linting, a to-scale symbol registry, and the sized tank, gas cylinder and Swagelok sample cylinder families.

## Symbols

There is one .kicad_sym file per symbol which is contained in the symbols folder. To use, add the relevant .kicad_sym files to your project library.

Alternatively you can download the pid_kicad.kicad_sym file which includes all symbols (automatically keep up-to-date)


## Templates

`templates/pid_A3.kicad_wks` is an A3 P&ID drawing sheet with a title block and revision table. In the schematic, open File, Page Settings and choose it as the drawing sheet file. Title, Revision, Issue Date and Company come from Page Settings, and Sheet x of y is automatic. Comment 1 is the project, comment 2 the drawing number, comments 3 to 5 are drawn, checked and approved by, and comment 6 is the revision description.

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
| ENG | Engine | Engines, injectors and igniters |
| FIT | Fitting | Blind flanges, bulkheads, caps, crosses, elbows, flanges, flexible hoses, plugs, reducers, tees and unions |
| PYV | Pyrotechnic valve | Normally closed and normally open pyro valves |
| SQB | Squib | Squibs |
| TT | Temperature transmitter | Temperature transmitters |
| TI | Temperature indicator | Local temperature displays |
| TS | Temperature switch | Temperature switches |
| PDT | Differential pressure transmitter | DP transmitters (1 HP, 2 LP) |
| PDI | Differential pressure indicator | DP gauges (1 HP, 2 LP) |
| WT | Weight transmitter | Load cells |
| AT | Analyser transmitter | Oxygen detectors |
| FE | Flow element | Turbine, venturi and orifice plate elements |
| C | Compressor | Gas boosters |
| VP | Vacuum pump | Vacuum pumps |
| E | Heat exchanger | Coil and shell and tube exchangers, cooling jackets |
| FA | Flame arrestor | Flame arrestors |
| UMB | Umbilical | Vehicle to ground support equipment disconnects |
| OPC | Off-sheet connector | Lines continuing to or from another sheet |
| LN | Line number | Line number tags |
| IB | Interface boundary | Interface boundary markers |
| LEG | Legend | Line type legends |

## Collaborations

We are open to contribution to the symbol set. Please follow the conventions above. Every symbol also carries a Description and a hidden ki_keywords property, which make it easier to find in the KiCad symbol chooser.

Two make targets help contributors. Run `make normalise` after editing a symbol to apply the conventions (Reference prefix, Description, keywords, stroke width 0.1, pin numbers and names, hidden pin labels) and `make lint` to check them. The lint also runs as a pre-commit hook and fails the commit if any rule is broken. A new symbol needs an entry in the table at the top of `scripts/normalise.py` before the normaliser will accept it.

`make registry` builds `pid_registry.pdf`, a to-scale reference of every symbol. It exports the symbols afresh with `kicad-cli` (the `plots/` argument is not used) and needs the Python packages `reportlab`, `pillow` and `svglib` (`pip install reportlab pillow svglib`), which draw the symbols as vectors. `rsvg-convert` is only needed as the raster fallback. The page font is IBM Plex Sans, vendored in `fonts/` under the SIL Open Font Licence (`fonts/OFL.txt`); the build falls back to Helvetica with a warning if the font files are missing.

`make package` builds the release files into `dist/`, which are the KiCad package, one download per operating system and `SHA256SUMS.txt`. The version comes from the `VERSION` file. Pushing a tag that matches it, such as `v1.0.0`, makes the release workflow lint the symbols, build those files and publish them as a GitHub release.

Note: By contributing you agree to license it under the same MIT license as the rest of kicad_pid

## License

All content is licensed under the MIT license, see the license file.

## Roadmap

- Solenoid actuators and fail-position markings (FC, FO and FL)
- Actuated three-way and angle valves
- More instruments, such as TT and TI, PDT, load cell, temperature switch, flow elements and an O2 detector
- Equipment, such as COPV, dewar, gas booster, vacuum pump, heat exchanger and flame arrestor
- Engine-side symbols, such as injector, igniter and cooling jacket
- Interface and annotation symbols, such as union, flange, bulkhead, umbilical, off-sheet connector, line-number tag and a line-type legend
- A schematic sheet template with a title block
- Submission to the KiCad PCM public repository
- Vector drawings, rather than raster, in the registry PDF
- A lint check for degenerate geometry
