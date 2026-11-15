# Copyright 2026 Vinay Williams

"""
Lint the symbol sources.  Prints one line per violation as

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

from rules import linewidth, pins, properties


def find_files(root):
    files = []
    for dirpath, _, names in os.walk(root):
        files.extend(
            os.path.join(dirpath, n) for n in names if n.endswith(".kicad_sym")
        )
    return sorted(files)


def lint_file(path, root):
    """Return the violation messages for one symbol file."""
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
        messages += pins.check(symbol, category)
        messages += properties.check(symbol, PREFIXES)
    return messages


def main(symbols_dir):
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
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <symbols directory>", file=sys.stderr)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
