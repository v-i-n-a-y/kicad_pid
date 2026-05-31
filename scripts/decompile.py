# Copyright 2024 Kingston University Rocket Engineering

import sys
import os
import sexp


def find_existing_paths(outdir):
    """Map symbol-name -> existing .kicad_sym path under outdir (recursive)."""
    paths = {}
    for root, _, files in os.walk(outdir):
        for f in files:
            if f.endswith(".kicad_sym"):
                paths[f[: -len(".kicad_sym")]] = os.path.join(root, f)
    return paths


def split_lib(libpath, outdir):
    """
    Split Monolith Library

    Arguments

    libpath - str
        Path to monolith library
    outdir - str
        Directory to output individual footprints
    """

    with open(libpath, "r") as f:
        lib_data = sexp.parse(f.read(), parse_nums=True)

    header = lib_data[:4]
    existing = find_existing_paths(outdir)

    components = []
    current_lib = None

    for entry in lib_data[4:]:
        if isinstance(entry, list) and entry[0] == "symbol":
            symbol = entry[1]
            if current_lib and current_lib != symbol:
                save_lib(header, current_lib, components, outdir, existing)
                components.clear()
            current_lib = symbol
            components.append(entry)
        else:
            components.append(entry)

    if components:
        save_lib(header, current_lib, components, outdir, existing)


def save_lib(header, lib_name, components, outdir, existing):
    """
    Save a single symbol back to its existing location if known,
    else into outdir's root.
    """
    lib_file = existing.get(lib_name, os.path.join(outdir, f"{lib_name}.kicad_sym"))
    os.makedirs(os.path.dirname(lib_file), exist_ok=True)

    print("Writing: " + lib_file)
    with open(lib_file, "w") as f:
        f.write(sexp.generate([*header, components[0]]))


def usage():
    """
    Usgae

    Prints the script's usage
    """

    print("Usage: {} <compiled lib path> <output directory>".format(sys.argv[0]))
    sys.exit(1)


if __name__ == "__main__":
    print("Rocketry P&ID KiCAD - Decompile Monolith\n")

    if len(sys.argv) != 3:
        usage()
    else:
        libpath = sys.argv[1]
        outdir = sys.argv[2]

        if not os.path.exists(libpath):
            print(f"Error: The file {libpath} does not exist.", file=sys.stderr)
            sys.exit(1)

        if not os.path.isdir(outdir):
            print(f"Error: The directory {outdir} does not exist.", file=sys.stderr)
            sys.exit(1)

        split_lib(libpath, outdir)
        print(f"Library has been split and saved to {outdir}\n\n")
