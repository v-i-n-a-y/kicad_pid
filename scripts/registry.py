# Copyright 2026 Vinay Williams

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import NamedTuple
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch, mm
from reportlab.platypus import (
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

PAGE_W, PAGE_H = A4
MARGIN = 18 * mm
USABLE_W = PAGE_W - 2 * MARGIN
USABLE_H = PAGE_H - 2 * MARGIN

# Every symbol is drawn at the same physical scale: one millimetre on the
# symbol is SCALE millimetres on the page. SCALE is chosen from the symbols
# themselves (see choose_scale) but never exceeds MAX_SCALE.
MAX_SCALE = 1.5
MAX_HEIGHT_FRACTION = 0.6  # the tallest symbol may use this much of a page
MIN_CELL_W = 34 * mm  # narrowest cell, so labels stay readable
CELL_GAP = 2 * mm
RASTER_DPI = 300

UNIT_TO_MM = {"mm": 1.0, "cm": 10.0, "in": 25.4, "pt": 25.4 / 72, "px": 25.4 / 96}
UNIT_SUFFIX = re.compile(r"^(.*)_unit\d+$")


class Symbol(NamedTuple):
    category: str
    name: str
    svg_path: str
    width_mm: float
    height_mm: float
    reference: str
    description: str


def parse_svg_size_mm(svg_path: str) -> tuple | None:
    """Return (width, height) in mm from the SVG root element. Uses the
    width/height attributes and their units; falls back to the viewBox, which
    kicad-cli writes in mm."""
    with open(svg_path, encoding="utf-8", errors="replace") as fh:
        head = fh.read(4096)
    m = re.search(r"<svg\b[^>]*>", head, re.DOTALL)
    if not m:
        return None
    tag = m.group(0)

    def attr(name: str) -> str | None:
        a = re.search(rf'\s{name}\s*=\s*"([^"]*)"', tag)
        return a.group(1).strip() if a else None

    def to_mm(value: str | None) -> float | None:
        if not value:
            return None
        v = re.fullmatch(r"([0-9.eE+-]+)\s*([a-z%]*)", value)
        if not v or v.group(2) == "%":
            return None
        unit = v.group(2) or "px"
        return float(v.group(1)) * UNIT_TO_MM[unit] if unit in UNIT_TO_MM else None

    w, h = to_mm(attr("width")), to_mm(attr("height"))
    if w and h:
        return w, h
    vb = attr("viewBox")
    if vb:
        parts = [float(x) for x in re.split(r"[\s,]+", vb) if x]
        if len(parts) == 4 and parts[2] > 0 and parts[3] > 0:
            return parts[2], parts[3]
    return None


def _prop(text: str, key: str) -> str:
    m = re.search(
        rf'\(property\s+"?{key}"?\s+(?:"((?:[^"\\]|\\.)*)"|([^\s()"]+))', text
    )
    if not m:
        return ""
    value = m.group(1) if m.group(1) is not None else m.group(2)
    return re.sub(r"\\(.)", r"\1", value).strip()


def read_properties(sym_path: str) -> tuple:
    """Return (reference, description) of the first symbol in a .kicad_sym;
    either may be empty or absent."""
    text = Path(sym_path).read_text(encoding="utf-8", errors="replace")
    return _prop(text, "Reference"), _prop(text, "Description")


def derive_symbols_dir(plots_dir: str) -> str:
    """symbols/ next to plots/ (the repository layout)."""
    return os.path.join(
        os.path.dirname(os.path.abspath(plots_dir.rstrip("/\\"))), "symbols"
    )


def collect_symbols(plots_dir: str, symbols_dir: str) -> "list[Symbol]":
    """Return one Symbol per SVG, built only from .kicad_sym files that exist
    in symbols_dir (so stale plots are ignored). Sorted by category then name."""
    symbols: list[Symbol] = []
    for cat in sorted(os.listdir(symbols_dir)):
        cat_dir = os.path.join(symbols_dir, cat)
        if not os.path.isdir(cat_dir):
            continue
        plot_dir = os.path.join(plots_dir, cat)
        svgs = (
            sorted(f for f in os.listdir(plot_dir) if f.endswith(".svg"))
            if os.path.isdir(plot_dir)
            else []
        )
        for f in sorted(os.listdir(cat_dir)):
            if not f.endswith(".kicad_sym"):
                continue
            base = Path(f).stem
            ref, desc = read_properties(os.path.join(cat_dir, f))
            found = [
                s
                for s in svgs
                if Path(s).stem == base
                or (
                    UNIT_SUFFIX.match(Path(s).stem)
                    and UNIT_SUFFIX.match(Path(s).stem).group(1) == base
                )
            ]
            if not found:
                print(f"Warning: no plot for {cat}/{f}", file=sys.stderr)
            for s in found:
                path = os.path.join(plot_dir, s)
                size = parse_svg_size_mm(path)
                if size is None:
                    print(f"Warning: cannot read size of {path}", file=sys.stderr)
                    continue
                symbols.append(Symbol(cat, Path(s).stem, path, *size, ref, desc))
    symbols.sort(key=lambda x: (x.category, x.name))
    return symbols


def choose_scale(symbols: "list[Symbol]") -> float:
    """One page-mm per symbol-mm factor for every symbol. Capped at MAX_SCALE;
    reduced if the widest symbol would not fit the page width or the tallest
    would use more than MAX_HEIGHT_FRACTION of the page height."""
    max_w = max(s.width_mm for s in symbols) * mm
    max_h = max(s.height_mm for s in symbols) * mm
    return min(MAX_SCALE, USABLE_W / max_w, MAX_HEIGHT_FRACTION * USABLE_H / max_h)


def svg_to_png_bytes(svg_path: str, px_w: int, px_h: int) -> bytes | None:
    result = subprocess.run(
        ["rsvg-convert", "-f", "png", "-w", str(px_w), "-h", str(px_h), svg_path],
        capture_output=True,
        check=False,
    )
    return result.stdout if result.returncode == 0 else None


def category_title(slug: str) -> str:
    return slug.replace("-", " ").title()


def pack_rows(cells: "list[tuple[Symbol, float]]") -> "list[list[tuple]]":
    """Greedy row packing; each cell is (symbol, cell width in points). A
    symbol wider than the page takes a row of its own."""
    rows: list[list[tuple]] = []
    row: list[tuple] = []
    used = 0.0
    for cell in cells:
        w = cell[1] + CELL_GAP
        if row and used + w > USABLE_W:
            rows.append(row)
            row, used = [], 0.0
        row.append(cell)
        used += w
    if row:
        rows.append(row)
    return rows


def build_registry(plots_dir: str, output_path: str, symbols_dir: str) -> None:
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "RegTitle",
        parent=styles["Title"],
        fontSize=28,
        leading=34,
        spaceAfter=4 * mm,
        textColor=colors.HexColor("#1a1a2e"),
    )
    subtitle_style = ParagraphStyle(
        "RegSubtitle",
        parent=styles["Normal"],
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#555555"),
    )
    cat_style = ParagraphStyle(
        "CatHead",
        parent=styles["Heading1"],
        fontSize=13,
        leading=16,
        spaceBefore=6 * mm,
        spaceAfter=3 * mm,
        textColor=colors.HexColor("#2c3e50"),
        borderPad=(0, 0, 2, 0),
    )
    name_style = ParagraphStyle(
        "SymName",
        parent=styles["Normal"],
        fontSize=7.5,
        leading=10,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#333333"),
    )
    meta_style = ParagraphStyle(
        "SymMeta",
        parent=name_style,
        fontSize=6.5,
        leading=8,
        textColor=colors.HexColor("#666666"),
    )

    symbols = collect_symbols(plots_dir, symbols_dir)
    if not symbols:
        print("No SVG symbols found.", file=sys.stderr)
        return

    scale = choose_scale(symbols)
    print(f"Scale: {scale:.3f} (1 mm on the symbol = {scale:.3f} mm on the page)")

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=MARGIN,
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        counter = 0

        def make_image(sym: Symbol):
            """Return an Image at the common scale, or a placeholder Paragraph."""
            nonlocal counter
            dw = sym.width_mm * mm * scale
            dh = sym.height_mm * mm * scale
            px_w = max(1, round(dw / inch * RASTER_DPI))
            px_h = max(1, round(dh / inch * RASTER_DPI))
            png = svg_to_png_bytes(sym.svg_path, px_w, px_h)
            if png is None:
                print(f"Warning: could not rasterise {sym.svg_path}", file=sys.stderr)
                return Paragraph(f"[{escape(sym.name)}]", name_style), 10 * mm
            counter += 1
            tmp = os.path.join(tmpdir, f"{counter}.png")
            Path(tmp).write_bytes(png)
            return Image(tmp, width=dw, height=dh), dh

        def make_row(row: "list[tuple]") -> Table:
            images, labels, widths, heights = [], [], [], []
            for sym, cell_w in row:
                img, h = make_image(sym)
                images.append(img)
                heights.append(h)
                widths.append(cell_w + CELL_GAP)
                label = [Paragraph(escape(sym.name), name_style)]
                if sym.reference:
                    label.append(Paragraph(f"Ref: {escape(sym.reference)}", meta_style))
                if sym.description:
                    label.append(Paragraph(escape(sym.description), meta_style))
                labels.append(label)
            t = Table(
                [images, labels],
                colWidths=widths,
                rowHeights=[max(heights) + 2 * mm, None],
            )
            t.setStyle(
                TableStyle(
                    [
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("VALIGN", (0, 0), (-1, 0), "MIDDLE"),
                        ("VALIGN", (0, 1), (-1, 1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 1 * mm),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 1 * mm),
                        ("TOPPADDING", (0, 0), (-1, -1), 1 * mm),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 1 * mm),
                    ]
                )
            )
            return t

        story: list = []

        # Title page
        story.append(Spacer(1, 50 * mm))
        story.append(Paragraph("P&amp;ID KiCAD Symbol Registry", title_style))
        story.append(
            Paragraph(
                "Aerospace Piping &amp; Instrumentation Diagram Symbols",
                subtitle_style,
            )
        )
        story.append(Spacer(1, 4 * mm))
        story.append(
            Paragraph(
                f"All symbols are drawn at one common scale of {scale:.2f} : 1 "
                "(page size to symbol size), so relative sizes are true.",
                subtitle_style,
            )
        )
        story.append(PageBreak())

        by_cat: dict[str, list] = {}
        for sym in symbols:
            by_cat.setdefault(sym.category, []).append(sym)

        for cat in sorted(by_cat):
            cells = [(s, max(s.width_mm * mm * scale, MIN_CELL_W)) for s in by_cat[cat]]
            rows = pack_rows(cells)
            heading = Paragraph(category_title(cat), cat_style)
            story.append(KeepTogether([heading, make_row(rows[0])]))
            for row in rows[1:]:
                story.append(make_row(row))
            story.append(Spacer(1, 4 * mm))

        doc.build(story)

    print(f"Registry written to {output_path}")


def usage() -> None:
    print(
        f"Usage: {sys.argv[0]} <plots directory> <output pdf path> [symbols directory]\n"
        "  The symbols directory defaults to symbols/ next to the plots directory."
    )
    sys.exit(1)


if __name__ == "__main__":
    print("Rocketry P&ID KiCAD - Symbol Registry\n")

    if len(sys.argv) not in (3, 4):
        usage()

    plots_dir = sys.argv[1]
    output_path = sys.argv[2]
    symbols_dir = sys.argv[3] if len(sys.argv) == 4 else derive_symbols_dir(plots_dir)

    if not os.path.isdir(plots_dir):
        print(f"Plots directory '{plots_dir}' does not exist.", file=sys.stderr)
        sys.exit(1)

    if not os.path.isdir(symbols_dir):
        print(
            f"Symbols directory '{symbols_dir}' does not exist; "
            "pass it as the third argument.",
            file=sys.stderr,
        )
        sys.exit(1)

    build_registry(plots_dir, output_path, symbols_dir)
