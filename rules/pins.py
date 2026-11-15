# Copyright 2026 Vinay Williams

"""Pin rules: grid, two-port spacing, numbers, names and type."""

import kisexp

# Folders whose two-port symbols must connect at x = -8 and x = 8.
INLINE_CATEGORIES = {
    "filters",
    "pumps",
    "burst-disks",
    "valves",
    "regulators",
    "restrictions",
    "quick-disconnects",
    "pyrotechnics",
    "instruments",
}
INLINE_X = 8


def _label(index, pin):
    number = kisexp.pin_field(pin, "number")
    return f"pin {number}" if number else f"pin #{index + 1}"


def _whole(value):
    return abs(value - round(value)) < 1e-9


def check_grid(symbol):
    """Every pin connection point must sit on a whole millimetre."""
    messages = []
    for i, pin in enumerate(kisexp.pins(symbol)):
        x, y, _ = kisexp.pin_at(pin)
        if not (_whole(x) and _whole(y)):
            messages.append(
                f"{_label(i, pin)} connection point ({x:g}, {y:g}) is not on whole mm"
            )
    return messages


def check_inline_spacing(symbol, category):
    """A two-pin symbol with both pins on y=0 must connect at x=-8 and x=8."""
    if category not in INLINE_CATEGORIES:
        return []
    pins = kisexp.pins(symbol)
    if len(pins) != 2:
        return []
    points = [kisexp.pin_at(p) for p in pins]
    if any(y != 0 for _, y, _ in points):
        return []
    xs = sorted(x for x, _, _ in points)
    if xs != [-INLINE_X, INLINE_X]:
        message = (
            f"two-port pins must connect at x=-{INLINE_X} and x={INLINE_X}, "
            f"found x={xs[0]:g} and x={xs[1]:g}"
        )
        return [message]
    return []


def check_numbers(symbol):
    """Pin numbers must be non-empty and unique within the symbol."""
    messages = []
    seen = {}
    for i, pin in enumerate(kisexp.pins(symbol)):
        number = kisexp.pin_field(pin, "number")
        if not number:
            messages.append(f"pin #{i + 1} has an empty number")
            continue
        if number in seen:
            messages.append(f"pin number {number} is used more than once")
        seen[number] = i
    return messages


def check_names(symbol):
    """Pin names must be non-empty."""
    messages = []
    for i, pin in enumerate(kisexp.pins(symbol)):
        if not kisexp.pin_field(pin, "name"):
            messages.append(f"{_label(i, pin)} has an empty name")
    return messages


def check_type(symbol):
    """Pins must be of type passive."""
    messages = []
    for i, pin in enumerate(kisexp.pins(symbol)):
        if pin[1] != "passive":
            messages.append(f"{_label(i, pin)} has type {pin[1]}, expected passive")
    return messages


def check(symbol, category):
    return (
        check_grid(symbol)
        + check_inline_spacing(symbol, category)
        + check_numbers(symbol)
        + check_names(symbol)
        + check_type(symbol)
    )
