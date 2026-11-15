# Copyright 2026 Vinay Williams

import kisexp

REQUIRED = 0.1


def stroke_widths(symbol):
    """
    Collect the width of every stroke in a symbol

    Arguments

    symbol - list
        A symbol node, including its unit sub-symbols

    Returns

    widths - list
        Width text of each stroke, None where a stroke has no width
    """

    widths = []
    for node in kisexp.walk(symbol):
        if node and node[0] == "stroke":
            width = kisexp.child(node, "width")
            widths.append(width[1] if width and len(width) > 1 else None)
    return widths


def is_required(text):
    """
    Test a stroke width against the required one

    Arguments

    text - str
        Width as written in the file

    Returns

    result - bool
        True if it equals 0.1
    """

    try:
        return abs(float(text) - REQUIRED) < 1e-9
    except (TypeError, ValueError):
        return False


def check(symbol):
    """
    Stroke width rule: every stroke in a symbol is 0.1 wide

    Arguments

    symbol - list
        A symbol node

    Returns

    messages - list
        One message per distinct width that is not 0.1, empty if all are fine
    """

    counts = {}
    for text in stroke_widths(symbol):
        if not is_required(text):
            counts[text] = counts.get(text, 0) + 1
    messages = []
    for text, count in sorted(counts.items(), key=lambda kv: str(kv[0])):
        label = "stroke without a width" if text is None else f"stroke width {text}"
        messages.append(f"{label}, expected {REQUIRED} ({count} occurrence(s))")
    return messages
