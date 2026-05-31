# Copyright 2024 Kingston University Rocket Engineering

import os
import sys

from utils import file_changed


def export_symbol(symbol, outdir):
    command = f"kicad-cli sym export svg '{symbol}' --output '{outdir}'"
    exit_code = os.system(command)

    if exit_code != 0:
        print(f"Failed to export {symbol}")
        return

    _strip_unit_suffix(symbol, outdir)
    print(f"Exported {symbol} to '{outdir}'\n")


def _strip_unit_suffix(symbol_path, outdir):
    """kicad-cli writes <Name>_unitN.svg; drop the _unit1 suffix for
    single-unit symbols. Multi-unit symbols keep their _unitN names so units
    stay distinguishable."""
    base = os.path.splitext(os.path.basename(symbol_path))[0]
    prefix = f"{base}_unit"
    units = sorted(
        f for f in os.listdir(outdir) if f.startswith(prefix) and f.endswith(".svg")
    )
    if len(units) == 1 and units[0] == f"{base}_unit1.svg":
        src = os.path.join(outdir, units[0])
        dst = os.path.join(outdir, f"{base}.svg")
        os.replace(src, dst)


def export(symboldir, output_dir):
    """
    Export library symbols as SVGs, mirroring symboldir's subdir structure
    under output_dir.
    """

    jobs = []
    for root, _, files in os.walk(symboldir):
        for f in files:
            sym_path = os.path.join(root, f)
            if f.endswith(".kicad_sym") and file_changed(sym_path):
                rel = os.path.relpath(root, symboldir)
                out_dir = output_dir if rel == "." else os.path.join(output_dir, rel)
                os.makedirs(out_dir, exist_ok=True)
                jobs.append((sym_path, out_dir))

    if not jobs:
        print(f"No changed symbols found in '{symboldir}'")
        return False

    for sym_path, out_dir in jobs:
        export_symbol(sym_path, out_dir)

    print(f"All changed symbols in {symboldir} exported to {output_dir}")
    return True


def generate_readme(plots_dir):
    """
    Generates README showing current symbols, grouped by subdirectory.
    """

    entries = []
    for root, _, files in os.walk(plots_dir):
        rel = os.path.relpath(root, plots_dir)
        section = "Uncategorised" if rel == "." else rel
        svgs = sorted(f for f in files if f.endswith(".svg"))
        if svgs:
            entries.append((section, rel, svgs))

    if not entries:
        print("No SVG files found in the specified folder.")
        return

    entries.sort(key=lambda e: (e[0] != "Uncategorised", e[0]))

    lines = ["# PI&D KiCAD Symbols\n"]
    for section, rel, svgs in entries:
        lines.append(f"## {section}\n")
        for svg in svgs:
            src = svg if rel == "." else f"{rel}/{svg}"
            lines.append(f"### {svg}")
            lines.append(f"<img src='{src}' width='500' height='500'>")
        lines.append("")

    readme_path = os.path.join(plots_dir, "README.md")
    with open(readme_path, "w") as f:
        f.write("\n".join(lines))

    print(f"README.md generated at {readme_path}")


def usage():
    """
    Usage

    Prints the script's usage
    """

    print("Usage: {} <symbol path> <output directory>".format(sys.argv[0]))
    sys.exit(1)


if __name__ == "__main__":
    print("Rocketry P&ID KiCAD - Plotting\n")

    if len(sys.argv) != 3:
        usage()
    else:
        symboldir = sys.argv[1]
        outdir = sys.argv[2]

        print(f"Individual Symbol Path: {symboldir}")
        print(f"Output Path: {outdir}\n")

    if not os.path.isdir(outdir):
        print(f"The output directory '{outdir}' does not exist.", file=sys.stderr)
        sys.exit(1)

    if not os.path.isdir(symboldir):
        print(f"The symbols directory '{symboldir}' does not exist.", file=sys.stderr)
        sys.exit(1)

    if export(symboldir, outdir):
        generate_readme(outdir)
