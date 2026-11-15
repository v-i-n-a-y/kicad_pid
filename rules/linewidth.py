# Copyright 2024 Kingston University Rocket Engineering
# Copyright 2026 Vinay Williams

"""Stroke width rule: every stroke in a symbol is 0.1 mm."""

import kisexp

STROKE_WIDTH = 0.1


def check(symbol):
    """Return a message for each stroke width other than 0.1."""
    found = {}
    for node in kisexp.walk(symbol):
        if node and node[0] == "width" and len(node) == 2:
            found[node[1]] = found.get(node[1], 0) + 1
    messages = []
    for text, count in sorted(found.items()):
        try:
            ok = abs(float(text) - STROKE_WIDTH) < 1e-9
        except ValueError:
            ok = False
        if not ok:
            messages.append(
                f"stroke width {text} is not {STROKE_WIDTH} ({count} occurrence(s))"
            )
    return messages
