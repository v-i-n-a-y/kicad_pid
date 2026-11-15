# Copyright 2026 Vinay Williams

"""
Round-trip S-expression reader and writer for KiCad symbol files.

scripts/sexp.py drops the distinction between quoted strings and bare atoms,
so it cannot write KiCad 8 style output (quoted property names and values).
This module keeps that distinction: a bare atom is a plain ``str`` and a
quoted string is a ``Str`` (a ``str`` subclass).  Numbers stay as the exact
text they were read with, so graphics survive a round trip unchanged.
"""

import re


class Str(str):
    """A quoted string.  The text is held exactly as written between the quotes."""


_TOKEN = re.compile(r'\(|\)|"((?:[^"\\]|\\.)*)"|[^\s()"]+', re.DOTALL)


def parse(text):
    """Parse text holding one S-expression into nested lists."""
    stack = [[]]
    for match in _TOKEN.finditer(text):
        token = match.group(0)
        if token == "(":
            stack.append([])
        elif token == ")":
            if len(stack) < 2:
                raise ValueError("unbalanced ')'")
            node = stack.pop()
            stack[-1].append(node)
        elif token.startswith('"'):
            stack[-1].append(Str(match.group(1)))
        else:
            stack[-1].append(token)
    if len(stack) != 1:
        raise ValueError("unbalanced '('")
    if len(stack[0]) != 1 or not isinstance(stack[0][0], list):
        raise ValueError("expected exactly one top-level expression")
    return stack[0][0]


def dump(node, depth=0):
    """Write nested lists in the layout used by the repository's symbol files."""
    parts = []
    for item in node:
        if isinstance(item, list):
            parts.append(dump(item, depth + 1))
        elif isinstance(item, Str):
            parts.append(f'"{item}"')
        else:
            parts.append(item)
    out = "\n{}({})".format("  " * depth, " ".join(parts)).splitlines()
    return "\n".join(line.rstrip() for line in out)


def read_file(path):
    with open(path, "r", encoding="utf-8") as f:
        return parse(f.read())


def write_file(path, tree):
    with open(path, "w", encoding="utf-8") as f:
        f.write(dump(tree) + "\n")


def children(node, name):
    """Yield the child lists of node whose first element is name."""
    for child in node:
        if isinstance(child, list) and child and child[0] == name:
            yield child


def child(node, name):
    """Return the first child list of node called name, or None."""
    return next(children(node, name), None)


def walk(node):
    """Yield node and every list nested inside it."""
    yield node
    for item in node:
        if isinstance(item, list):
            yield from walk(item)


def symbols(tree):
    """Yield the top-level symbol definitions of a library tree."""
    return children(tree, "symbol")


def properties(symbol):
    """Return {property name: value} for the symbol's own properties."""
    return {p[1]: p[2] for p in children(symbol, "property") if len(p) >= 3}


def pins(symbol):
    """Return every pin of a symbol, including those in its unit sub-symbols."""
    return [n for n in walk(symbol) if n and n[0] == "pin"]


def pin_at(pin):
    """Return (x, y, angle) of a pin as floats."""
    at = child(pin, "at")
    return tuple(float(v) for v in at[1:4])


def pin_field(pin, name):
    """Return the text of a pin's name or number, or None if absent."""
    node = child(pin, name)
    if node is None or len(node) < 2 or isinstance(node[1], list):
        return None
    return str(node[1])
