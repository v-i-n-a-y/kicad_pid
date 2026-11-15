# Copyright 2026 Vinay Williams

import os
import re
import shutil
import subprocess
import sys
import tempfile
from urllib.parse import quote

import utils

GALLERY_TITLE = "P&ID symbol gallery"
IMAGE_WIDTH = 500
UNIT_TAIL = re.compile(r"_unit\d+$")


class ExportError(RuntimeError):
    """
    kicad-cli could not export a symbol file
    """


def plot_dir_for(source, symbolsdir, outdir):
    """
    Find the plots folder that mirrors a source file's category folder

    Arguments

    source - str
        Path of a symbol file
    symbolsdir - str
        Directory containing the symbol sources
    outdir - str
        Directory holding the plots

    Returns

    folder - str
        The matching folder under outdir
    """

    category = os.path.relpath(os.path.dirname(source), symbolsdir)
    return outdir if category == "." else os.path.join(outdir, category)


def belongs_to(svg_name, base):
    """
    Test whether a plot was exported from a given symbol

    Arguments

    svg_name - str
        File name of the plot
    base - str
        Symbol name

    Returns

    result - bool
        True for <base>.svg and <base>_unitN.svg
    """

    stem = os.path.splitext(svg_name)[0]
    return svg_name.endswith(".svg") and (
        stem == base
        or (stem.startswith(base) and UNIT_TAIL.fullmatch(stem[len(base) :]))
    )


def export_symbol(source, dest, kicad_cli):
    """
    Export one symbol file, replacing its earlier plots

    The _unit1 suffix is dropped for single-unit symbols; multi-unit symbols
    keep _unitN so the units stay distinguishable.

    Arguments

    source - str
        Path of the symbol file
    dest - str
        Folder to put the plots in
    kicad_cli - str
        Path of the kicad-cli executable
    """

    base = utils.symbol_name(source)
    with tempfile.TemporaryDirectory() as scratch:
        done = subprocess.run(
            [kicad_cli, "sym", "export", "svg", source, "--output", scratch],
            capture_output=True,
            text=True,
            check=False,
        )
        made = sorted(n for n in os.listdir(scratch) if n.endswith(".svg"))
        if done.returncode != 0 or not made:
            detail = (done.stderr or done.stdout).strip()
            raise ExportError(f"{source}: kicad-cli export failed {detail}".strip())
        os.makedirs(dest, exist_ok=True)
        for old in os.listdir(dest):
            if belongs_to(old, base):
                os.remove(os.path.join(dest, old))
        for name in made:
            target = base + ".svg" if made == [f"{base}_unit1.svg"] else name
            shutil.move(os.path.join(scratch, name), os.path.join(dest, target))


def has_source(svg_name, source_dir):
    """
    Test whether a symbol file still exists for a plot

    Arguments

    svg_name - str
        File name of the plot
    source_dir - str
        Category folder that should hold the symbol file

    Returns

    result - bool
        True if the source file exists
    """

    stem = os.path.splitext(svg_name)[0]
    names = {stem, UNIT_TAIL.sub("", stem)}
    return any(
        os.path.isfile(os.path.join(source_dir, n + utils.SYMBOL_SUFFIX)) for n in names
    )


def remove_stale(symbolsdir, outdir):
    """
    Delete plots with no source file, then empty category folders

    Arguments

    symbolsdir - str
        Directory containing the symbol sources
    outdir - str
        Directory holding the plots, which is itself never removed

    Returns

    removed - int
        Number of plots deleted
    """

    removed = 0
    for folder, _, names in os.walk(outdir, topdown=False):
        rel = os.path.relpath(folder, outdir)
        source_dir = symbolsdir if rel == "." else os.path.join(symbolsdir, rel)
        for name in names:
            if name.endswith(".svg") and not has_source(name, source_dir):
                os.remove(os.path.join(folder, name))
                print(f"Removed stale {os.path.normpath(os.path.join(rel, name))}")
                removed += 1
        if rel != "." and not os.listdir(folder):
            os.rmdir(folder)
            print(f"Removed empty directory {rel}")
    return removed


def gallery(outdir):
    """
    Build the README gallery, grouped by category

    Arguments

    outdir - str
        Directory holding the plots

    Returns

    text - str
        Markdown, or None if there are no plots
    """

    sections = {}
    for folder, _, names in os.walk(outdir):
        rel = os.path.relpath(folder, outdir)
        svgs = sorted(n for n in names if n.endswith(".svg"))
        if svgs:
            sections["" if rel == "." else rel.replace(os.sep, "/")] = svgs
    if not sections:
        return None
    lines = [f"# {GALLERY_TITLE}", ""]
    # plots in the root come first, then the categories in order
    for rel in sorted(sections, key=lambda r: (r != "", r)):
        lines += [f"## {rel or 'Uncategorised'}", ""]
        for svg in sections[rel]:
            url = quote(f"{rel}/{svg}" if rel else svg)
            lines += [
                f"### {os.path.splitext(svg)[0]}",
                "",
                f'<img src="{url}" width="{IMAGE_WIDTH}">',
                "",
            ]
    return "\n".join(lines)


def export(symbolsdir, outdir, export_all=False):
    """
    Export symbols as SVGs, mirroring the category folders under outdir

    Arguments

    symbolsdir - str
        Directory containing the symbol sources
    outdir - str
        Directory to write the plots into
    export_all - bool
        Export every symbol, not only those git reports as changed

    Returns

    failures - int
        Number of symbol files that could not be exported
    """

    kicad_cli = shutil.which("kicad-cli")
    if kicad_cli is None:
        raise ExportError("kicad-cli is not installed or not on PATH")
    sources = utils.symbol_files(symbolsdir)
    if not export_all:
        changed = utils.changed_paths(symbolsdir)
        sources = [s for s in sources if utils.file_changed(s, changed)]

    os.makedirs(outdir, exist_ok=True)
    removed = remove_stale(symbolsdir, outdir)
    failures = 0
    for source in sources:
        try:
            export_symbol(source, plot_dir_for(source, symbolsdir, outdir), kicad_cli)
            print(f"Exported {source}")
        except ExportError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            failures += 1
    if not sources:
        print(f"No changed symbols found in '{symbolsdir}'")

    readme = os.path.join(outdir, "README.md")
    if sources or removed or not os.path.exists(readme):
        text = gallery(outdir)
        if text is not None:
            utils.write_text(readme, text)
            print(f"README.md generated at {readme}")
    return failures


def usage():
    """
    Usage

    Prints the script's usage
    """

    print(
        f"Usage: {sys.argv[0]} [--all] <symbols directory> <output directory>\n"
        "  --all  export every symbol, not only those with git changes"
    )
    sys.exit(2)


if __name__ == "__main__":
    print("Rocketry P&ID KiCAD - Plotting\n")

    args = sys.argv[1:]
    export_all = "--all" in args
    args = [a for a in args if a != "--all"]
    if len(args) != 2:
        usage()
    symbolsdir, outdir = args

    if not os.path.isdir(symbolsdir):
        print(
            f"Error: The symbols directory '{symbolsdir}' does not exist.",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        failed = export(symbolsdir, outdir, export_all)
    except (ExportError, utils.GitError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
    sys.exit(1 if failed else 0)
