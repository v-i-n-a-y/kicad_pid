# Copyright 2026 Vinay Williams

"""
Pin rules: grid, two-port spacing, numbers, names and type.
"""

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
    "equipment",
}
INLINE_X = 8


def _label(index, pin):
    """
    Name a pin in a lint message

    Arguments

    index - int
        Position of the pin in its symbol, counted from zero
    pin - list
        A pin node

    Returns

    label - str
        "pin N" using the pin number, or "pin #N" counted from one if the pin
        has no number
    """

    number = kisexp.pin_field(pin, "number")
    return f"pin {number}" if number else f"pin #{index + 1}"


def _whole(value):
    """
    Test whether a coordinate sits on a whole millimetre

    Arguments

    value - float
        The coordinate in millimetres

    Returns

    result - bool
        True if the value is within 1e-9 of a whole number
    """

    return abs(value - round(value)) < 1e-9


def check_grid(symbol):
    """
    Check that every pin connection point sits on a whole millimetre

    Arguments

    symbol - list
        A symbol node

    Returns

    messages - list
        One message for each pin that is off the grid
    """

    messages = []
    for i, pin in enumerate(kisexp.pins(symbol)):
        x, y, _ = kisexp.pin_at(pin)
        if not (_whole(x) and _whole(y)):
            messages.append(
                f"{_label(i, pin)} connection point ({x:g}, {y:g}) is not on whole mm"
            )
    return messages


def check_inline_spacing(symbol, category):
    """
    Check that two-port symbols in the inline categories connect at x = -8 and x = 8

    Only symbols in INLINE_CATEGORIES with exactly two pins, both on y = 0, are
    checked. Any other symbol passes.

    Arguments

    symbol - list
        A symbol node
    category - str
        The category folder the symbol sits in

    Returns

    messages - list
        One message if the two pins are misplaced, otherwise empty
    """

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
    """
    Check that pin numbers are non-empty and unique within the symbol

    Arguments

    symbol - list
        A symbol node

    Returns

    messages - list
        One message for each empty or repeated pin number
    """

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
    """
    Check that every pin has a non-empty name

    Arguments

    symbol - list
        A symbol node

    Returns

    messages - list
        One message for each pin with an empty name
    """

    messages = []
    for i, pin in enumerate(kisexp.pins(symbol)):
        if not kisexp.pin_field(pin, "name"):
            messages.append(f"{_label(i, pin)} has an empty name")
    return messages


def check_type(symbol):
    """
    Check that every pin is of type passive

    Arguments

    symbol - list
        A symbol node

    Returns

    messages - list
        One message for each pin of another type
    """

    messages = []
    for i, pin in enumerate(kisexp.pins(symbol)):
        if pin[1] != "passive":
            messages.append(f"{_label(i, pin)} has type {pin[1]}, expected passive")
    return messages


def check(symbol, category):
    """
    Run every pin rule against one symbol

    Arguments

    symbol - list
        A symbol node
    category - str
        The category folder the symbol sits in

    Returns

    messages - list
        All violation messages from the pin rules
    """

    return (
        check_grid(symbol)
        + check_inline_spacing(symbol, category)
        + check_numbers(symbol)
        + check_names(symbol)
        + check_type(symbol)
    )
