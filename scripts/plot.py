# Copyright 2024 Kingston University Rocket Engineering
# Copyright 2026 Vinay Williams

import os
import re
import sys

from utils import file_changed


def _remove_previous(symbol_path, outdir):
    """Drop earlier exports of this symbol so a changed unit count cannot
    leave orphaned <Name>.svg or <Name>_unitN.svg files behind."""
    base = os.path.splitext(os.path.basename(symbol_path))[0]
    for f in os.listdir(outdir):
        stem, ext = os.path.splitext(f)
        if ext == ".svg" and (
            stem == base or re.fullmatch(re.escape(base) + r"_unit\d+", stem)
        ):
            os.remove(os.path.join(outdir, f))


def export_symbol(symbol, outdir):
    _remove_previous(symbol, outdir)
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


def export(symboldir, output_dir, export_all=False):
    """
    Export library symbols as SVGs, mirroring symboldir's subdir structure
    under output_dir. Only symbols with uncommitted git changes are exported
    unless export_all is set.
    """

    jobs = []
    for root, _, files in os.walk(symboldir):
        for f in sorted(files):
            sym_path = os.path.join(root, f)
            if f.endswith(".kicad_sym") and (export_all or file_changed(sym_path)):
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


_UNIT_SUFFIX = re.compile(r"^(.*)_unit\d+$")


def _has_source(svg_name, src_dir):
    """True if svg_name (<Name>.svg or <Name>_unitN.svg) still has a
    <Name>.kicad_sym in src_dir."""
    stem = os.path.splitext(svg_name)[0]
    candidates = [stem]
    m = _UNIT_SUFFIX.match(stem)
    if m:
        candidates.append(m.group(1))
    return any(
        os.path.isfile(os.path.join(src_dir, c + ".kicad_sym")) for c in candidates
    )


def remove_stale(symboldir, output_dir):
    """
    Delete every SVG under output_dir whose source .kicad_sym no longer exists
    in the matching subdirectory of symboldir, then delete category
    directories left empty (output_dir itself is kept). Returns the number of
    SVGs removed.
    """

    removed = 0
    for root, dirs, files in os.walk(output_dir, topdown=False):
        rel = os.path.relpath(root, output_dir)
        src_dir = symboldir if rel == "." else os.path.join(symboldir, rel)
        for f in files:
            if f.endswith(".svg") and not _has_source(f, src_dir):
                os.remove(os.path.join(root, f))
                print(f"Removed stale {os.path.join(rel, f) if rel != '.' else f}")
                removed += 1
        if rel != "." and not os.listdir(root):
            os.rmdir(root)
            print(f"Removed empty directory {rel}")
    return removed


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

    print(
        f"Usage: {sys.argv[0]} [--all] <symbol path> <output directory>\n"
        "  --all  export every symbol, not only those with git changes"
    )
    sys.exit(1)


if __name__ == "__main__":
    print("Rocketry P&ID KiCAD - Plotting\n")

    args = sys.argv[1:]
    export_all = "--all" in args
    args = [a for a in args if a != "--all"]
    if len(args) != 2:
        usage()

    symboldir, outdir = args
    print(f"Individual Symbol Path: {symboldir}")
    print(f"Output Path: {outdir}\n")

    if not os.path.isdir(outdir):
        print(f"The output directory '{outdir}' does not exist.", file=sys.stderr)
        sys.exit(1)

    if not os.path.isdir(symboldir):
        print(f"The symbols directory '{symboldir}' does not exist.", file=sys.stderr)
        sys.exit(1)

    removed = remove_stale(symboldir, outdir)
    exported = export(symboldir, outdir, export_all)
    if exported or removed:
        generate_readme(outdir)
