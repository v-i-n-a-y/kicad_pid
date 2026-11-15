# Copyright 2026 Vinay Williams

import os
import sys

import kisexp
import utils


def collect(root):
    """
    Gather the symbols of every source file

    Symbols are sorted by name rather than path, so the library order does not
    depend on the category folder a symbol sits in.

    Arguments

    root - str
        Directory containing the symbol sources

    Returns

    nodes - list
        Symbol nodes, sorted by name
    """

    nodes = []
    origin = {}
    for path in utils.symbol_files(root):
        try:
            tree = kisexp.read_file(path)
        except (OSError, ValueError) as exc:
            raise ValueError(f"{path}: cannot parse ({exc})") from exc
        for node in kisexp.symbols(tree):
            name = str(node[1])
            if name in origin:
                raise ValueError(f"{path}: symbol {name!r} is also in {origin[name]}")
            origin[name] = path
            nodes.append(node)
    if not nodes:
        raise ValueError(f"{root}: no symbols found")
    return sorted(nodes, key=lambda node: str(node[1]))


def compile_library(root):
    """
    Build the monolithic library text

    Arguments

    root - str
        Directory containing the symbol sources

    Returns

    text - str
        The KiCad 8 library
    """

    return utils.library_text(utils.library_tree(collect(root)))


def usage():
    """
    Usage

    Prints the script's usage
    """

    print(f"Usage: {sys.argv[0]} <symbols directory> <output lib path>")
    sys.exit(2)


if __name__ == "__main__":
    print("Rocketry P&ID KiCAD - Compile Monolith\n")

    if len(sys.argv) != 3:
        usage()
    symbolsdir, outlib = sys.argv[1:]

    if not os.path.isdir(symbolsdir):
        print(
            f"Error: Source directory '{symbolsdir}' does not exist.", file=sys.stderr
        )
        sys.exit(1)
    outdir = os.path.dirname(os.path.abspath(outlib))
    if not os.path.isdir(outdir):
        print(f"Error: Output directory '{outdir}' does not exist.", file=sys.stderr)
        sys.exit(1)

    try:
        text = compile_library(symbolsdir)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
    utils.write_text(outlib, text)
    print(f"Compiled {text.count(chr(10) + '  (symbol ')} symbols into {outlib}")
