# Copyright 2026 Vinay Williams

"""
Round-trip S-expression reader and writer for KiCad symbol files.

Plain S-expression parsers drop the difference between quoted strings and
bare atoms, which KiCad 8 needs in order to write quoted property names and
values. This module keeps that difference: a bare atom is a plain str and a
quoted string is a Str, a str subclass. Numbers stay as the exact text they
were read with, so graphics survive a round trip unchanged.
"""

import re


class Str(str):
    """
    A quoted string, held exactly as written between the quotes
    """


_TOKEN = re.compile(r'\(|\)|"((?:[^"\\]|\\.)*)"|[^\s()"]+', re.DOTALL)


def parse(text):
    """
    Parse text holding one S-expression into nested lists

    Arguments

    text - str
        Source text holding exactly one top-level expression

    Returns

    tree - list
        The expression as nested lists of atoms
    """

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
    """
    Serialise nested lists in the layout the repository's symbol files use

    Arguments

    node - list
        The expression to serialise
    depth - int
        Nesting level of the node, indented by two spaces per level

    Returns

    text - str
        The serialised expression, starting with a line break
    """

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
    """
    Read and parse one S-expression file

    Arguments

    path - str
        File to read, as UTF-8

    Returns

    tree - list
        The parsed expression, as returned by parse
    """

    with open(path, "r", encoding="utf-8") as f:
        return parse(f.read())


def write_file(path, tree):
    """
    Write a tree to a file as UTF-8, followed by a line break

    Arguments

    path - str
        File to write, replaced if it already exists
    tree - list
        The expression to serialise with dump
    """

    with open(path, "w", encoding="utf-8") as f:
        f.write(dump(tree) + "\n")


def children(node, name):
    """
    Yield the child lists of a node whose first element is name

    Arguments

    node - list
        The node to search, its direct children only
    name - str
        The head keyword to match

    Returns

    matches - generator
        Each matching child list, in order
    """

    for child in node:
        if isinstance(child, list) and child and child[0] == name:
            yield child


def child(node, name):
    """
    Find the first child list of a node with the given name

    Arguments

    node - list
        The node to search, its direct children only
    name - str
        The head keyword to match

    Returns

    child - list
        The first matching child list, or None if there is none
    """

    return next(children(node, name), None)


def walk(node):
    """
    Walk a node and every list nested inside it

    Arguments

    node - list
        The root of the walk

    Returns

    nodes - generator
        The node itself, then each nested list depth first
    """

    yield node
    for item in node:
        if isinstance(item, list):
            yield from walk(item)


def symbols(tree):
    """
    Find the top-level symbol definitions of a library tree

    Arguments

    tree - list
        A kicad_symbol_lib tree

    Returns

    symbols - generator
        Each symbol child list, in file order
    """

    return children(tree, "symbol")


def properties(symbol):
    """
    Collect the properties a symbol defines for itself

    Arguments

    symbol - list
        A symbol node

    Returns

    properties - dict
        Property name mapped to value, for each property that has both
    """

    return {p[1]: p[2] for p in children(symbol, "property") if len(p) >= 3}


def pins(symbol):
    """
    Find every pin of a symbol, including those in its unit sub-symbols

    Arguments

    symbol - list
        A symbol node

    Returns

    pins - list
        Each pin node
    """

    return [n for n in walk(symbol) if n and n[0] == "pin"]


def pin_at(pin):
    """
    Read the connection point and angle of a pin

    Arguments

    pin - list
        A pin node

    Returns

    position - tuple
        (x, y, angle) as floats
    """

    at = child(pin, "at")
    return tuple(float(v) for v in at[1:4])


def pin_field(pin, name):
    """
    Read the text of a pin's name or number

    Arguments

    pin - list
        A pin node
    name - str
        The child to read, either name or number

    Returns

    text - str
        The text of the field, or None if the field is absent or has no value
    """

    node = child(pin, name)
    if node is None or len(node) < 2 or isinstance(node[1], list):
        return None
    return str(node[1])
