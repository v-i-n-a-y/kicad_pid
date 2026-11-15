# Copyright 2026 Vinay Williams

"""
Geometry rule: no degenerate graphics (collapsed polylines, rectangles, circles
and arcs), which draw nothing or a stray dot.
"""

import kisexp

TOLERANCE = 1e-6


def _number(node, name, index=1):
    """
    Read one numeric value from a named child of a node

    Arguments

    node - list
        The graphic node, for example a circle
    name - str
        Head keyword of the child to read, for example radius
    index - int
        Position of the value inside the child, 1 for the first

    Returns

    value - float
        The value, or None if the child or value is missing or not a number
    """

    item = kisexp.child(node, name)
    if item is None or len(item) <= index:
        return None
    try:
        return float(item[index])
    except (TypeError, ValueError):
        return None


def _point(node, name):
    """
    Read an x, y pair from a named child of a node

    Arguments

    node - list
        The graphic node, for example an arc
    name - str
        Head keyword of the child to read, for example start

    Returns

    point - tuple
        (x, y), or None if the child or either value is missing or not a number
    """

    x, y = _number(node, name, 1), _number(node, name, 2)
    if x is None or y is None:
        return None
    return (x, y)


def _same(a, b):
    """
    Test whether two points coincide

    Arguments

    a - tuple
        First (x, y) point
    b - tuple
        Second (x, y) point

    Returns

    result - bool
        True if both coordinates agree within the tolerance
    """

    return abs(a[0] - b[0]) <= TOLERANCE and abs(a[1] - b[1]) <= TOLERANCE


def _polyline_points(node):
    """
    Collect the vertices of a polyline

    Arguments

    node - list
        A polyline node

    Returns

    points - list
        (x, y) of each xy entry that holds two numbers, in order
    """

    pts = kisexp.child(node, "pts")
    points = []
    for xy in kisexp.children(pts or [], "xy"):
        try:
            points.append((float(xy[1]), float(xy[2])))
        except (IndexError, TypeError, ValueError):
            continue
    return points


def check_graphic(node):
    """
    Test one graphic node for degenerate geometry

    Arguments

    node - list
        Any node of a symbol, nodes that are not graphics pass

    Returns

    message - str
        What is wrong, or None if the node is fine or is not a graphic
    """

    kind = node[0] if node else None
    if kind == "polyline":
        points = _polyline_points(node)
        if not any(not _same(points[0], p) for p in points[1:]):
            return f"polyline with fewer than two distinct points ({len(points)} given)"
    elif kind == "rectangle":
        start, end = _point(node, "start"), _point(node, "end")
        if start and end:
            flat = [
                axis
                for axis, a, b in (
                    ("width", start[0], end[0]),
                    ("height", start[1], end[1]),
                )
                if abs(a - b) <= TOLERANCE
            ]
            if flat:
                return f"rectangle with zero {' and '.join(flat)} at ({start[0]:g}, {start[1]:g})"
    elif kind == "circle":
        radius = _number(node, "radius")
        if radius is not None and radius <= TOLERANCE:
            centre = _point(node, "center")
            where = f" at ({centre[0]:g}, {centre[1]:g})" if centre else ""
            return f"circle with zero radius{where}"
    elif kind == "arc":
        start, mid, end = (_point(node, n) for n in ("start", "mid", "end"))
        if start and mid and end and _same(start, mid) and _same(mid, end):
            return f"arc with coincident start, mid and end at ({start[0]:g}, {start[1]:g})"
    return None


def check(symbol):
    """
    Geometry rule: no polyline, rectangle, circle or arc is degenerate

    Arguments

    symbol - list
        A symbol node, including its unit sub-symbols

    Returns

    messages - list
        One message per degenerate graphic, empty if all are fine
    """

    messages = []
    for node in kisexp.walk(symbol):
        message = check_graphic(node)
        if message:
            messages.append(message)
    return messages
