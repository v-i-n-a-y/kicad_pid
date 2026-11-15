# Copyright 2026 Vinay Williams

import os
import sys

import kisexp
import utils


def destinations(root):
    """
    Find where each symbol already lives

    Arguments

    root - str
        Directory containing the symbol sources

    Returns

    known - dict
        Symbol name mapped to the file that holds it
    """

    known = {}
    for path in utils.symbol_files(root):
        known.setdefault(utils.symbol_name(path), path)
    return known


def split_lib(libpath, outdir):
    """
    Split the monolith library into one file per symbol

    A symbol that already has a file under outdir goes back to that file. A new
    symbol goes to outdir/uncategorised, to be moved into a category by hand.

    Arguments

    libpath - str
        Path to the monolith library
    outdir - str
        Directory containing the symbol sources

    Returns

    counts - tuple
        Files written and files left unchanged
    """

    tree = kisexp.read_file(libpath)
    if not tree or tree[0] != "kicad_symbol_lib":
        raise ValueError(f"{libpath}: not a KiCad symbol library")
    known = destinations(outdir)
    written = unchanged = 0
    for node in kisexp.symbols(tree):
        name = str(node[1])
        if not name or any(c in name for c in "/\\\0"):
            raise ValueError(f"symbol name {name!r} cannot be used as a file name")
        default = os.path.join(outdir, utils.UNCATEGORISED, name + utils.SYMBOL_SUFFIX)
        path = known.get(name, default)
        text = kisexp.dump(utils.library_tree([node], quote_generator=False)) + "\n"
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as f:
                if f.read() == text:
                    unchanged += 1
                    continue
        os.makedirs(os.path.dirname(path), exist_ok=True)
        utils.write_text(path, text)
        written += 1
        print(f"Writing: {path}")
    return written, unchanged


def usage():
    """
    Usage

    Prints the script's usage
    """

    print(f"Usage: {sys.argv[0]} <compiled lib path> <symbols directory>")
    sys.exit(2)


if __name__ == "__main__":
    print("Rocketry P&ID KiCAD - Decompile Monolith\n")

    if len(sys.argv) != 3:
        usage()
    libpath, outdir = sys.argv[1:]

    if not os.path.isfile(libpath):
        print(f"Error: The file {libpath} does not exist.", file=sys.stderr)
        sys.exit(1)
    if not os.path.isdir(outdir):
        print(f"Error: The directory {outdir} does not exist.", file=sys.stderr)
        sys.exit(1)

    try:
        written, unchanged = split_lib(libpath, outdir)
    except (OSError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
    print(f"Library split into {outdir}: {written} written, {unchanged} unchanged")
