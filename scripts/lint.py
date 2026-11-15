# Copyright 2026 Vinay Williams

"""
Lint the symbol sources.

Prints one line per violation in the form

    <file>: <message>

and exits 1 if there are any.
"""

import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scripts"))
sys.path.insert(0, REPO)

import kisexp
from normalise import PREFIXES

from rules import geometry, linewidth, pins, properties


def find_files(root):
    """
    Find every symbol file under a directory

    Arguments

    root - str
        Directory to search, recursively

    Returns

    files - list
        Full paths of the .kicad_sym files, sorted
    """

    files = []
    for dirpath, _, names in os.walk(root):
        files.extend(
            os.path.join(dirpath, n) for n in names if n.endswith(".kicad_sym")
        )
    return sorted(files)


def lint_file(path, root):
    """
    Check one symbol file against every lint rule

    A file that cannot be parsed, or that holds no symbol, is reported as a
    violation rather than raised.

    Arguments

    path - str
        The symbol file to check
    root - str
        The symbols directory the file sits under, used to find its category

    Returns

    messages - list
        Violation messages, empty if the file passes
    """

    try:
        tree = kisexp.read_file(path)
    except (ValueError, OSError) as exc:
        return [f"cannot parse ({exc})"]
    category = os.path.relpath(os.path.dirname(path), root).split(os.sep)[0]
    symbols = list(kisexp.symbols(tree))
    if not symbols:
        return ["no symbol found"]
    messages = []
    for symbol in symbols:
        messages += linewidth.check(symbol)
        messages += geometry.check(symbol)
        messages += pins.check(symbol, category)
        messages += properties.check(symbol, PREFIXES)
    return messages


def main(symbols_dir):
    """
    Lint every symbol file under a directory and print the violations

    Arguments

    symbols_dir - str
        Directory holding the symbol sources

    Returns

    status - int
        0 if there are no violations, 1 if there are any or no files were found
    """

    files = find_files(symbols_dir)
    if not files:
        print(f"{symbols_dir}: no .kicad_sym files found")
        return 1
    count = 0
    for path in files:
        for message in lint_file(path, symbols_dir):
            print(f"{path}: {message}")
            count += 1
    return 1 if count else 0


if __name__ == "__main__":
    print("Rocketry P&ID KiCAD - Lint Symbols\n")

    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <symbols directory>", file=sys.stderr)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
