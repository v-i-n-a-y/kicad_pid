# Copyright 2026 Vinay Williams

"""
Normalise the symbol sources so every symbol follows the library conventions.

For each .kicad_sym file under the given directory this rewrites, in place
and idempotently

* the Reference property (ISA style prefix, see SYMBOLS below),
* the Description and ki_keywords properties (both hidden),
* on_board no, in_bom yes,
* every stroke width to 0.1,
* every pin to type passive with a unique number and a name (1 IN, 2 OUT ...),
* hidden pin names and numbers on the schematic.

Graphics are left untouched apart from the stroke width.  Nothing is written
if any symbol has no table entry or any pin cannot be classified.
"""

import copy
import os
import sys

import kisexp
from kisexp import Str

STROKE_WIDTH = "0.1000"

ACTUATORS = {
    "": ("V", "no actuator", "unactuated"),
    "Manual": ("HV", "manually operated", "manual hand"),
    "Hydraulic": ("XV", "hydraulically actuated", "hydraulic actuated"),
    "Pneumatic": ("XV", "pneumatically actuated", "pneumatic actuated"),
    "Servo": ("XV", "servo actuated", "servo actuated"),
}
VALVE_TYPES = ("Ball", "Butterfly", "Diaphragm", "Gate", "Globe", "Needle")

# symbol name -> (Reference prefix, Description, ki_keywords)
SYMBOLS = {}


def _add(name, prefix, description, keywords):
    if name in SYMBOLS:
        raise ValueError("duplicate table entry: " + name)
    SYMBOLS[name] = (prefix, description, keywords)


for _type in VALVE_TYPES:
    for _variant, (_prefix, _text, _words) in ACTUATORS.items():
        _name = "Valve - " + _type + (" " + _variant if _variant else "")
        _kw = f"valve {_type.lower()} {_words} {_prefix.lower()}"
        _add(_name, _prefix, f"{_type} valve, {_text}", _kw)

_add("Valve - 3 Way", "V", "Three-way valve, no actuator", "valve three way 3 tee v")
_add(
    "Valve - 3 Way Ball",
    "V",
    "Three-way ball valve, no actuator",
    "valve three way 3 ball v",
)
_add(
    "Valve - 3 Way Globe",
    "V",
    "Three-way globe valve, no actuator",
    "valve three way 3 globe v",
)
_add("Valve - 4 Way", "V", "Four-way valve, no actuator", "valve four way 4 cross v")
_add(
    "Valve - Angle Ball",
    "V",
    "Angle ball valve, no actuator",
    "valve angle right-angle ball v",
)
_add(
    "Valve - Angle Globe",
    "V",
    "Angle globe valve, no actuator",
    "valve angle right-angle globe v",
)
_add(
    "Valve - Check",
    "CV",
    "Check valve, permits flow in one direction only",
    "valve check non-return one-way cv",
)
_add(
    "Valve - Pressure Relief",
    "PRV",
    "Pressure relief valve, vents through its side port above set pressure",
    "valve pressure relief safety prv",
)
_add(
    "Valve - Pressure and Vacuum Relief",
    "PVRV",
    "Pressure and vacuum relief valve, protects against over and under pressure",
    "valve pressure vacuum relief safety pvrv",
)
_add(
    "Pressure Regulator",
    "PCV",
    "Pressure regulator, holds a steady downstream pressure",
    "regulator pressure control downstream pcv",
)
_add(
    "Back Pressure Regulator",
    "BPR",
    "Back pressure regulator, holds a steady upstream pressure",
    "regulator back pressure upstream bpr",
)

_add(
    "Pressure Transducer",
    "PT",
    "Pressure transducer, electrical pressure sensor",
    "instrument pressure transducer sensor pt",
)
_add(
    "Pressure Indicator",
    "PI",
    "Pressure indicator, local pressure display",
    "instrument pressure indicator display pi",
)
_add(
    "Pressure Gauge",
    "PI",
    "Pressure gauge, local pressure display",
    "instrument pressure gauge display pi",
)
_add(
    "Pressure Switch",
    "PS",
    "Pressure switch, contact that changes state at a set pressure",
    "instrument pressure switch ps",
)
_add(
    "RTD",
    "TE",
    "Resistance temperature detector, temperature sensor",
    "instrument temperature rtd pt100 sensor te",
)
_add(
    "Thermocouple",
    "TE",
    "Thermocouple, temperature sensor",
    "instrument temperature thermocouple sensor te",
)
_add(
    "Flow Transmitter",
    "FT",
    "Flow transmitter, electrical flow sensor",
    "instrument flow transmitter sensor ft",
)
_add(
    "Coriolis Flow Meter",
    "FT",
    "Coriolis flow meter, inline mass flow sensor",
    "instrument flow coriolis meter mass ft",
)
_add(
    "Flow Indicator",
    "FI",
    "Flow indicator, local flow display",
    "instrument flow indicator display fi",
)
_add(
    "Level Transmitter",
    "LT",
    "Level transmitter, electrical level sensor",
    "instrument level transmitter sensor lt",
)
_add(
    "Level Indicator",
    "LI",
    "Level indicator, local level display",
    "instrument level indicator display li",
)

_add("Tank", "TK", "Vertical tank", "tank vessel vertical tk")
_add("Tank - Horizontal", "TK", "Horizontal tank", "tank vessel horizontal tk")
_add("Tank - Large", "TK", "Large vertical tank", "tank vessel large vertical tk")
_add("Tank - Small", "TK", "Small vertical tank", "tank vessel small vertical tk")
_add("Tank - Sphere", "TK", "Spherical tank", "tank vessel sphere spherical tk")
_add("Bottle", "CYL", "Gas bottle", "bottle cylinder gas vessel cyl")
_add(
    "Bottle - Dip Tube",
    "CYL",
    "Gas bottle with a dip tube",
    "bottle cylinder dip tube liquid vessel cyl",
)
_add("Bottle - Large", "CYL", "Large gas bottle", "bottle cylinder large gas cyl")
_add("Bottle - Small", "CYL", "Small gas bottle", "bottle cylinder small gas cyl")
_add(
    "Sample Cylinder",
    "CYL",
    "Sample cylinder, inline",
    "sample cylinder vessel inline cyl",
)
_add(
    "Sample Cylinder - Large",
    "CYL",
    "Large sample cylinder, inline",
    "sample cylinder large vessel inline cyl",
)
_add(
    "Sample Cylinder - Small",
    "CYL",
    "Small sample cylinder, inline",
    "sample cylinder small vessel inline cyl",
)

_add(
    "Quick Disconnect - Both Sealed",
    "QD",
    "Quick disconnect, both sides seal when uncoupled",
    "quick disconnect coupling sealed both qd",
)
_add(
    "Quick Disconnect - Destination Sealed",
    "QD",
    "Quick disconnect, destination side seals when uncoupled",
    "quick disconnect coupling sealed destination qd",
)
_add(
    "Quick Disconnect - No Sealing",
    "QD",
    "Quick disconnect, neither side seals when uncoupled",
    "quick disconnect coupling unsealed qd",
)
_add(
    "Quick Disconnect - Source Sealed",
    "QD",
    "Quick disconnect, source side seals when uncoupled",
    "quick disconnect coupling sealed source qd",
)
_add(
    "Burst Disk - Pressure",
    "BD",
    "Burst disk, ruptures above a set pressure",
    "burst disk rupture bursting pressure bd",
)
_add(
    "Burst Disk - Vacuum",
    "BD",
    "Burst disk, ruptures under a set vacuum",
    "burst disk rupture bursting vacuum bd",
)
_add("Filter", "FLT", "Inline filter", "filter strainer inline flt")
_add("Filter - Conical", "FLT", "Conical inline filter", "filter strainer conical flt")
_add("Pump", "P", "Pump", "pump p")
_add(
    "Restriction Orifice",
    "RO",
    "Restriction orifice, fixed flow restriction",
    "restriction orifice ro",
)
_add(
    "Cavitating Venturi",
    "CAV",
    "Cavitating venturi, holds a fixed flow rate",
    "cavitating venturi flow restriction cav",
)
_add("Vent - Covered", "VENT", "Vent to atmosphere, covered", "vent atmosphere covered")
_add(
    "Vent - Uncovered",
    "VENT",
    "Vent to atmosphere, uncovered",
    "vent atmosphere uncovered open",
)
_add(
    "Engine - Bipropellant",
    "ENG",
    "Bipropellant rocket engine",
    "engine rocket bipropellant thruster eng",
)
_add(
    "Engine - Hybrid",
    "ENG",
    "Hybrid rocket engine",
    "engine rocket hybrid thruster eng",
)
_add("Engine - Solid", "ENG", "Solid rocket motor", "engine rocket solid motor eng")
_add("Cap", "FIT", "Pipe cap, closes the end of a line", "fitting cap end plug fit")
_add("Cross", "FIT", "Four-way cross fitting", "fitting cross four way fit")
_add("Elbow", "FIT", "Right-angle elbow fitting", "fitting elbow bend fit")
_add("Flexible Hose", "FIT", "Flexible hose", "fitting hose flexible fit")
_add("Reducer", "FIT", "Reducer fitting, joins two line sizes", "fitting reducer fit")
_add("Tee", "FIT", "Three-way tee fitting", "fitting tee three way fit")
_add(
    "Pyro Valve NC",
    "PYV",
    "Pyrotechnic valve, normally closed",
    "valve pyro pyrotechnic normally closed nc pyv",
)
_add(
    "Pyro Valve NO",
    "PYV",
    "Pyrotechnic valve, normally open",
    "valve pyro pyrotechnic normally open no pyv",
)
_add("Squib", "SQB", "Squib, pyrotechnic initiator", "squib pyrotechnic initiator sqb")

PREFIXES = {entry[0] for entry in SYMBOLS.values()}

# Fallback for vessel size variants not in the table, matched on the name start.
VESSEL_PATTERNS = (
    ("Tank", "TK"),
    ("Bottle", "CYL"),
    ("Gas Cylinder", "CYL"),
    ("Sample Cylinder", "CYL"),
)


def lookup(name):
    """Return (prefix, description, keywords) for a symbol name, or None."""
    if name in SYMBOLS:
        return SYMBOLS[name]
    for start, prefix in VESSEL_PATTERNS:
        if name == start or name.startswith(start + " "):
            parts = [part.strip() for part in name.split(" - ") if part.strip()]
            text = ", ".join(part.lower() for part in parts)
            description = text[0].upper() + text[1:]
            words = ["vessel"]
            for word in text.replace(",", " ").split():
                if word not in words:
                    words.append(word)
            words.append(prefix.lower())
            return prefix, description, " ".join(words)
    return None


# Prefixes whose single pin is a process connection rather than a plain port.
INSTRUMENT_PREFIXES = {"PT", "PI", "PS", "TE", "FT", "FI", "LT", "LI"}
RELIEF_PREFIXES = {"PRV", "PVRV"}
ENGINE_PREFIXES = {"ENG"}


class NormaliseError(Exception):
    pass


def plan_pins(prefix, pins):
    """
    Return [(number, name)] for the pins, in the same order as the pins list.

    Pins are classified by the connection point (x, y) of their (at x y angle).
    """
    n = len(pins)
    at = [kisexp.pin_at(p)[:2] for p in pins]
    plan = [None] * n
    if n == 0:
        return plan
    if n == 1:
        if prefix in ENGINE_PREFIXES:
            return [("1", "IN")]
        return [("1", "PROCESS" if prefix in INSTRUMENT_PREFIXES else "PORT")]
    if prefix in ENGINE_PREFIXES:
        for rank, i in enumerate(sorted(range(n), key=lambda i: at[i]), start=1):
            plan[i] = (str(rank), f"IN{rank}")
        return plan

    left = [i for i in range(n) if at[i][1] == 0 and at[i][0] < 0]
    right = [i for i in range(n) if at[i][1] == 0 and at[i][0] > 0]
    if len(left) == 1 and len(right) <= 1:
        assigned = left + right
        plan[left[0]] = ("1", "IN")
        if right:
            plan[right[0]] = ("2", "OUT")
        rest = sorted(
            (i for i in range(n) if i not in assigned),
            key=lambda i: (-at[i][1], at[i][0]),
        )
        number = len(assigned) + 1
        if prefix in RELIEF_PREFIXES:
            names = ["VENT"] + [f"VENT{k}" for k in range(2, len(rest) + 1)]
        elif not right and len(rest) == 1:
            names = ["OUT"]  # elbow and angle valves
        else:
            names = ["BRANCH"] + [f"BRANCH{k}" for k in range(2, len(rest) + 1)]
        for i, name in zip(rest, names):
            plan[i] = (str(number), name)
            number += 1
        return plan
    if n == 2 and all(x == 0 and y != 0 for x, y in at):
        top, bottom = sorted(range(n), key=lambda i: -at[i][1])
        plan[top] = ("1", "TOP")
        plan[bottom] = ("2", "BOTTOM")
        return plan
    raise NormaliseError("cannot classify pins at " + repr(at))


def _set_string_node(parent, name, value, template):
    """Set parent's (name "value" ...) child, creating it from template."""
    node = kisexp.child(parent, name)
    if node is None:
        node = [name, Str(""), copy.deepcopy(template)]
        parent.append(node)
    node[1] = Str(value)


def _ensure_hidden(prop):
    effects = kisexp.child(prop, "effects")
    if effects is None:
        effects = ["effects", ["font", ["size", "1.2700", "1.2700"]]]
        prop.append(effects)
    hide = kisexp.child(effects, "hide")
    if hide is None:
        effects.append(["hide", "yes"])
    else:
        hide[1:] = ["yes"]


def _set_property(symbol, key, value, after_key):
    """Set a property's value, creating it (hidden) after after_key if needed."""
    props = list(kisexp.children(symbol, "property"))
    prop = next((p for p in props if p[1] == key), None)
    if prop is None:
        source = next((p for p in props if p[1] == after_key), props[-1])
        prop = copy.deepcopy(source)
        prop[1] = Str(key)
        position = next(i for i, node in enumerate(symbol) if node is source)
        symbol.insert(position + 1, prop)
    prop[2:3] = [Str(value)]
    return prop


def normalise_symbol(symbol, filename):
    """Normalise one top-level symbol node in place.  Returns the pin table."""
    name = str(symbol[1])
    entry = lookup(name)
    if entry is None:
        raise NormaliseError(f"{filename}: no table entry for symbol {name!r}")
    prefix, description, keywords = entry

    # flags and pin visibility, in KiCad 8 order directly after the symbol name
    flags = {}
    for flag in ("exclude_from_sim", "in_bom"):
        node = kisexp.child(symbol, flag)
        flags[flag] = node[1] if node is not None and len(node) > 1 else None
    for old in ("pin_numbers", "pin_names", "exclude_from_sim", "in_bom", "on_board"):
        for node in list(kisexp.children(symbol, old)):
            symbol.remove(node)
    head = [
        ["pin_numbers", ["hide", "yes"]],
        ["pin_names", ["offset", "0"], ["hide", "yes"]],
        ["exclude_from_sim", flags["exclude_from_sim"] or "no"],
        ["in_bom", flags["in_bom"] or "yes"],
        ["on_board", "no"],
    ]
    symbol[2:2] = head

    # properties
    for prop in kisexp.children(symbol, "property"):
        prop[1] = Str(prop[1])
        prop[2] = Str(prop[2])
    _set_property(symbol, "Reference", prefix, "Reference")
    description_prop = _set_property(symbol, "Description", description, "Datasheet")
    _ensure_hidden(description_prop)
    keywords_prop = _set_property(symbol, "ki_keywords", keywords, "Description")
    _ensure_hidden(keywords_prop)

    # stroke widths
    for node in kisexp.walk(symbol):
        if node and node[0] == "width" and len(node) == 2:
            node[1] = STROKE_WIDTH

    # pins
    pins = kisexp.pins(symbol)
    plan = plan_pins(prefix, pins)
    numbers = [number for number, _ in plan]
    if len(set(numbers)) != len(numbers):
        raise NormaliseError(f"{filename}: duplicate pin numbers {numbers}")
    for pin, (number, pin_name) in zip(pins, plan):
        pin[1] = "passive"
        template = ["effects", ["font", ["size", "1.2700", "1.2700"]]]
        _set_string_node(pin, "name", pin_name, template)
        _set_string_node(pin, "number", number, template)
    table = [(kisexp.pin_at(p), n, nm) for p, (n, nm) in zip(pins, plan)]
    return sorted(table, key=lambda row: int(row[1])), prefix


def find_files(root):
    files = []
    for dirpath, _, names in os.walk(root):
        for name in names:
            if name.endswith(".kicad_sym"):
                files.append(os.path.join(dirpath, name))
    return sorted(files)


def fmt_pin(at, number, name):
    x, y, _ = at
    return f"{number} {name} ({x:g},{y:g})"


def main(symbols_dir):
    files = find_files(symbols_dir)
    if not files:
        print("No .kicad_sym files found in " + symbols_dir, file=sys.stderr)
        return 1

    errors = []
    trees = []
    rows = []
    for path in files:
        try:
            tree = kisexp.read_file(path)
        except (ValueError, OSError) as exc:
            errors.append(f"{path}: cannot parse ({exc})")
            continue
        for symbol in kisexp.symbols(tree):
            try:
                table, prefix = normalise_symbol(symbol, path)
            except NormaliseError as exc:
                errors.append(str(exc))
                continue
            rows.append((str(symbol[1]), prefix, table))
        trees.append((path, tree))

    if errors:
        print("Nothing written.  Problems found:", file=sys.stderr)
        for message in errors:
            print("  " + message, file=sys.stderr)
        return 1

    changed = 0
    for path, tree in trees:
        new = kisexp.dump(tree) + "\n"
        with open(path, "r", encoding="utf-8") as f:
            old = f.read()
        if old != new:
            changed += 1
            with open(path, "w", encoding="utf-8") as f:
                f.write(new)

    print("{:<42} {:<5} pins".format("symbol", "ref"))
    for name, prefix, table in rows:
        pins = "; ".join(fmt_pin(*row) for row in table) or "none"
        print(f"{name:<42} {prefix:<5} {pins}")
    print(f"\n{len(files)} files checked, {changed} rewritten")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <symbols directory>", file=sys.stderr)
        sys.exit(1)
    sys.exit(main(sys.argv[1]))
