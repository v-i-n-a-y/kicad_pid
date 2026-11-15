# Copyright 2026 Vinay Williams

"""
Data side of the symbol registry: read the symbol library, order it for an
engineering reader, export each symbol to a cropped vector drawing and derive
the reference prefix table.  The page layout lives in registry.py.

Drawings are vector (svglib turns each kicad-cli SVG into a reportlab group).
If svglib is not installed the export falls back, with a warning, to a cropped
400 dpi raster made with rsvg-convert.
"""

import io
import re
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import NamedTuple

import kisexp
from PIL import Image

try:
    from lxml import etree
    from reportlab.graphics.shapes import Group
    from svglib.svglib import svg2rlg
except ImportError:  # vector route unavailable, raster fallback is used
    etree = Group = svg2rlg = None

SVG_NS = "{http://www.w3.org/2000/svg}"
MM_TO_PT = 72 / 25.4
RASTER_DPI = 400
CROP_MARGIN_MM = 1.0  # fixed margin around the drawn content, every symbol

# Engineering order of the category folders; unknown folders follow, A to Z.
CATEGORY_ORDER = [
    "vessels",
    "valves",
    "regulators",
    "pyrotechnics",
    "burst-disks",
    "restrictions",
    "filters",
    "pumps",
    "quick-disconnects",
    "fittings",
    "instruments",
    "vents",
    "engines",
]

SIZE_RANK = {"small": 0, "medium": 1, "large": 2}
# Words that mark a variant of a base symbol (used for the prefix table only).
VARIANT_WORDS = {
    "hydraulic",
    "manual",
    "pneumatic",
    "servo",
    "dip",
    "outage",
    "tube",
    "single-ended",
    "small",
    "medium",
    "large",
}
ACTUATOR_WORDS = ("hydraulic", "manual", "pneumatic", "servo")
# Acronyms that keep their case when a family name is lower-cased.
KEEP_CASE = {"RTD", "NC", "NO"}


class Symbol(NamedTuple):
    category: str
    name: str
    reference: str
    description: str
    png: "bytes | None"  # cropped 400 dpi raster, only in the raster fallback
    drawing: object  # cropped reportlab Group in points, None in the raster fallback
    width_mm: float
    height_mm: float


class SymbolInfo(NamedTuple):
    category: str
    name: str
    path: Path
    reference: str
    description: str


def category_title(slug: str) -> str:
    """
    Turn a category folder name into a display title

    Arguments

    slug - str
        Folder name, for example quick-disconnects

    Returns

    str
        Title case title, for example Quick Disconnects
    """
    return slug.replace("-", " ").title()


def category_key(slug: str) -> tuple:
    """
    Sort key placing category folders in engineering order

    Arguments

    slug - str
        Category folder name

    Returns

    tuple
        Key that sorts known categories first, in CATEGORY_ORDER, then the rest A to Z
    """
    if slug in CATEGORY_ORDER:
        return (0, CATEGORY_ORDER.index(slug), slug)
    return (1, 0, slug)


def name_key(name: str) -> tuple:
    """
    Natural, size aware sort key for symbol names

    Numbers ascend (2 L before 10 L), Small, Medium, Large keep that order and a
    base symbol sorts before its variants because its word list is a prefix of theirs

    Arguments

    name - str
        Symbol name

    Returns

    tuple
        Key to sort by
    """
    key = []
    for word in re.split(r"[\s]+|\s-\s", name.lower()):
        if not word or word in ("-", "and"):
            continue
        if word.isdigit():
            key.append((0, int(word), ""))
        elif word in SIZE_RANK:
            key.append((1, SIZE_RANK[word], ""))
        else:
            key.append((2, 0, word))
    return tuple(key)


def read_info(path: Path, category: str) -> SymbolInfo:
    """
    Read the Reference and Description of a symbol file

    Arguments

    path - Path
        Symbol file to read
    category - str
        Category folder the file sits in

    Returns

    SymbolInfo
        Name, reference prefix and description of the symbol
    """
    tree = kisexp.read_file(str(path))
    sym = next(kisexp.symbols(tree), None)
    props = kisexp.properties(sym) if sym else {}
    return SymbolInfo(
        category,
        path.stem,
        path,
        str(props.get("Reference", "")).strip(),
        str(props.get("Description", "")).strip(),
    )


def list_symbols(symbols_dir: Path) -> "list[SymbolInfo]":
    """
    List every symbol file in registry order

    Arguments

    symbols_dir - Path
        Directory holding one sub directory per category

    Returns

    list[SymbolInfo]
        Symbols sorted by category order, then natural name order
    """
    infos = []
    for cat_dir in sorted(p for p in symbols_dir.iterdir() if p.is_dir()):
        for f in cat_dir.glob("*.kicad_sym"):
            infos.append(read_info(f, cat_dir.name))
    infos.sort(key=lambda s: (category_key(s.category), name_key(s.name), s.name))
    return infos


def hide_reference(src: Path, dst: Path) -> None:
    """
    Write a copy of a symbol file whose Reference property is hidden

    Arguments

    src - Path
        Symbol file to copy
    dst - Path
        Where to write the modified copy
    """
    tree = kisexp.read_file(str(src))
    for sym in kisexp.symbols(tree):
        for prop in kisexp.children(sym, "property"):
            if len(prop) < 3 or prop[1] != "Reference":
                continue
            effects = kisexp.child(prop, "effects")
            if effects is None:
                effects = ["effects"]
                prop.append(effects)
            if kisexp.child(effects, "hide") is None:
                effects.append(["hide", "yes"])
    kisexp.write_file(str(dst), tree)


def max_stroke(node) -> float:
    """
    Find the widest stroke in a reportlab shape tree

    Arguments

    node - Group | Shape
        Shape or group to search

    Returns

    float
        Widest stroke width in points, 0 if nothing is stroked
    """
    widest = 0.0
    if getattr(node, "strokeColor", None) is not None:
        widest = float(getattr(node, "strokeWidth", 0) or 0)
    for child in getattr(node, "contents", []):
        widest = max(widest, max_stroke(child))
    return widest


def crop_vector(svg: Path) -> "tuple[None, object, float, float] | None":
    """
    Convert an exported SVG to a vector drawing cropped to its drawn content

    The crop is the bounds of the geometry grown by half the widest stroke, which
    is what the raster route measures, plus the same fixed margin.  The SVG's own
    text elements are dropped first because kicad-cli writes them invisible
    (opacity 0) beside the stroked glyph outlines that actually show

    Arguments

    svg - Path
        SVG written by kicad-cli

    Returns

    tuple | None
        None for the raster, a Group translated so the crop box starts at the
        origin, width in mm and height in mm, or None if nothing could be drawn
    """
    parser = etree.XMLParser(load_dtd=False, resolve_entities=False, no_network=True)
    tree = etree.parse(str(svg), parser)
    for text in list(tree.getroot().iter(SVG_NS + "text")):
        text.getparent().remove(text)
    drawing = svg2rlg(io.BytesIO(etree.tostring(tree)))
    if drawing is None or not drawing.contents:
        return None
    bounds = drawing.getBounds()
    if bounds is None or (bounds[2] <= bounds[0] and bounds[3] <= bounds[1]):
        return None
    pad = CROP_MARGIN_MM * MM_TO_PT + max_stroke(drawing) / 2
    left, bottom, right, top = bounds
    width = right - left + 2 * pad
    height = top - bottom + 2 * pad
    group = Group(*drawing.contents, transform=(1, 0, 0, 1, pad - left, pad - bottom))
    return None, group, width / MM_TO_PT, height / MM_TO_PT


def crop_to_content(svg: Path) -> "tuple[bytes, float, float] | None":
    """
    Rasterise an exported SVG and crop it to its drawn content plus a fixed margin

    The physical size follows from the pixel density because rsvg-convert honours
    the millimetre width and height of the SVG

    Arguments

    svg - Path
        SVG written by kicad-cli

    Returns

    tuple | None
        PNG bytes, None for the vector drawing, width in mm and height in mm, or
        None if nothing could be drawn
    """
    proc = subprocess.run(
        ["rsvg-convert", "-f", "png", "-d", str(RASTER_DPI), "-p", str(RASTER_DPI)]
        + [str(svg)],
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        return None
    img = Image.open(io.BytesIO(proc.stdout)).convert("RGBA")
    box = img.getchannel("A").getbbox()
    if box is None:
        return None
    pad = round(CROP_MARGIN_MM / 25.4 * RASTER_DPI)
    left, top, right, bottom = box
    size = (right - left + 2 * pad, bottom - top + 2 * pad)
    # Pure black strokes on a transparent ground, so no box shows on the page
    alpha = Image.new("L", size, 0)
    alpha.paste(img.getchannel("A").crop(box), (pad, pad))
    canvas = Image.merge("LA", (Image.new("L", size, 0), alpha))
    out = io.BytesIO()
    canvas.save(out, format="PNG", optimize=True, dpi=(RASTER_DPI, RASTER_DPI))
    mm = 25.4 / RASTER_DPI
    return out.getvalue(), None, canvas.width * mm, canvas.height * mm


def export_one(info: SymbolInfo, work: Path) -> "list[Symbol]":
    """
    Export one library file in black and white with its Reference hidden

    Arguments

    info - SymbolInfo
        Symbol to export
    work - Path
        Temporary directory to work in

    Returns

    list[Symbol]
        One cropped symbol per unit
    """
    folder = work / f"{info.category}__{info.name}".replace(" ", "_")
    folder.mkdir(parents=True)
    tmp_sym = folder / "lib.kicad_sym"
    hide_reference(info.path, tmp_sym)
    out_dir = folder / "svg"
    proc = subprocess.run(
        ["kicad-cli", "sym", "export", "svg", "--black-and-white"]
        + [str(tmp_sym), "-o", str(out_dir)],
        capture_output=True,
        check=False,
    )
    svgs = sorted(out_dir.glob("*.svg")) if out_dir.is_dir() else []
    if proc.returncode != 0 or not svgs:
        print(f"Warning: kicad-cli failed for {info.path}", file=sys.stderr)
        return []
    symbols = []
    for svg in svgs:
        cropped = crop_vector(svg) if svg2rlg else crop_to_content(svg)
        if cropped is None:
            print(f"Warning: nothing drawn for {info.path}", file=sys.stderr)
            continue
        name = info.name
        unit = re.search(r"_unit(\d+)$", svg.stem)
        if len(svgs) > 1 and unit:
            name = f"{info.name} (unit {unit.group(1)})"
        symbols.append(
            Symbol(info.category, name, info.reference, info.description, *cropped)
        )
    return symbols


def export_symbols(symbols_dir: Path) -> "list[Symbol]":
    """
    Export every symbol into a temporary directory, leaving plots/ untouched

    Arguments

    symbols_dir - Path
        Directory holding one sub directory per category

    Returns

    list[Symbol]
        Cropped symbols in registry order
    """
    if shutil.which("kicad-cli") is None:
        raise SystemExit("kicad-cli is required to build the registry")
    if svg2rlg is None:
        print(
            "Warning: svglib is not installed, so the drawings are rasterised at "
            f"{RASTER_DPI} dpi instead of vector (pip install svglib)",
            file=sys.stderr,
        )
        if shutil.which("rsvg-convert") is None:
            raise SystemExit("svglib or rsvg-convert is required to draw the registry")
    infos = list_symbols(symbols_dir)
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(lambda i: export_one(i, work), infos))
    return [s for group in results for s in group]


def families(names: "list[str]") -> str:
    """
    Describe concisely what a set of symbol names covers

    Names are grouped by their first segment ("Valve - Ball Manual" belongs to
    "Valve") and size or actuator words are dropped

    Arguments

    names - list[str]
        Symbol names sharing a reference prefix

    Returns

    str
        Comma separated list of symbol families
    """
    groups: dict[str, list[str]] = {}
    actuators: dict[str, list[str]] = {}
    for name in names:
        head, _, tail = name.partition(" - ")
        words = [w for w in re.split(r"\s+|\s-\s", tail) if w]
        keep, skip_next = [], False
        for i, w in enumerate(words):
            lw = w.lower()
            if skip_next:
                skip_next = False
                continue
            if lw.isdigit() and i + 1 < len(words) and words[i + 1] == "L":
                skip_next = True  # a volume such as "10 L"
                continue
            if lw in VARIANT_WORDS or w == "-":
                continue
            keep.append(w)
        sub = " ".join(keep)
        sub = sub if sub in KEEP_CASE else sub.lower()
        subs = groups.setdefault(head, [])
        if sub and sub not in subs:
            subs.append(sub)
        for w in words:
            if w.lower() in ACTUATOR_WORDS and w.lower() not in actuators.setdefault(
                head, []
            ):
                actuators[head].append(w.lower())
    parts = []
    for head, subs in groups.items():
        label = head
        acts = actuators.get(head, [])
        if acts == ["manual"]:
            label += ", manual"
        elif acts:
            label += (
                ", "
                + " or ".join(
                    [", ".join(acts[:-1]), acts[-1]] if len(acts) > 1 else acts
                )
                + " actuated"
            )
        parts.append(f"{label} ({', '.join(subs)})" if subs else label)
    return ", ".join(parts)


def prefix_table(symbols: "list[Symbol]") -> "list[tuple[str, str]]":
    """
    Build the reference prefix table from the symbols' own data

    Arguments

    symbols - list[Symbol]
        Symbols in registry order

    Returns

    list[tuple]
        Prefix and used for text, in order of first use
    """
    order: list[str] = []
    names: dict[str, list[str]] = {}
    for s in symbols:
        if not s.reference:
            continue
        if s.reference not in names:
            order.append(s.reference)
        names.setdefault(s.reference, []).append(s.name)
    return [(p, families(names[p])) for p in order]
