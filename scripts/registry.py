# Copyright 2024 Kingston University Rocket Engineering

import os
import sys
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Image,
    Table,
    TableStyle,
    PageBreak,
)
from reportlab.lib.enums import TA_CENTER


PAGE_W, PAGE_H = A4
MARGIN = 18 * mm
COLS = 3
SYM_PX = 240  # rsvg-convert raster size (px)
SYM_PT = 52 * mm  # display size in PDF


def svg_to_png_bytes(svg_path: str) -> Optional[bytes]:
    result = subprocess.run(
        [
            "rsvg-convert",
            "-f",
            "png",
            "-w",
            str(SYM_PX),
            "-h",
            str(SYM_PX),
            "--keep-aspect-ratio",
            svg_path,
        ],
        capture_output=True,
    )
    return result.stdout if result.returncode == 0 else None


def collect_symbols(plots_dir: str) -> "list[tuple[str, str, str]]":
    """Return (category, name, svg_path) sorted by category then name."""
    symbols = []
    for root, _, files in os.walk(plots_dir):
        rel = os.path.relpath(root, plots_dir)
        if rel == ".":
            continue
        for f in sorted(files):
            if f.endswith(".svg"):
                symbols.append((rel, Path(f).stem, os.path.join(root, f)))
    symbols.sort(key=lambda x: (x[0], x[1]))
    return symbols


def category_title(slug: str) -> str:
    return slug.replace("-", " ").title()


def build_registry(plots_dir: str, output_path: str) -> None:
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

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=MARGIN,
    )

    col_w = (PAGE_W - 2 * MARGIN) / COLS
    tmp_files: list[str] = []

    def make_symbol_cell(svg_path: str, name: str) -> list:
        png = svg_to_png_bytes(svg_path)
        if png is None:
            return [Paragraph(f"[{name}]", name_style)]
        fd, tmp = tempfile.mkstemp(suffix=".png")
        os.close(fd)
        Path(tmp).write_bytes(png)
        tmp_files.append(tmp)
        return [
            Image(tmp, width=SYM_PT, height=SYM_PT),
            Spacer(1, 1 * mm),
            Paragraph(name, name_style),
        ]

    story: list = []

    # Title page
    story.append(Spacer(1, 50 * mm))
    story.append(Paragraph("P&amp;ID KiCAD Symbol Registry", title_style))
    story.append(
        Paragraph(
            "Aerospace Piping &amp; Instrumentation Diagram Symbols", subtitle_style
        )
    )
    story.append(PageBreak())

    symbols = collect_symbols(plots_dir)
    if not symbols:
        print("No SVG symbols found.", file=sys.stderr)
        return

    # Group by category
    by_cat: dict[str, list] = {}
    for cat, name, path in symbols:
        by_cat.setdefault(cat, []).append((name, path))

    for cat in sorted(by_cat):
        story.append(Paragraph(category_title(cat), cat_style))

        items = by_cat[cat]
        # Build rows of COLS cells
        for i in range(0, len(items), COLS):
            chunk = items[i : i + COLS]
            row = [make_symbol_cell(path, name) for name, path in chunk]
            # Pad short rows
            while len(row) < COLS:
                row.append("")
            t = Table(
                [row],
                colWidths=[col_w] * COLS,
                rowHeights=[SYM_PT + 10 * mm],
            )
            t.setStyle(
                TableStyle(
                    [
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ]
                )
            )
            story.append(t)
            story.append(Spacer(1, 3 * mm))

        story.append(Spacer(1, 4 * mm))

    doc.build(story)

    for f in tmp_files:
        try:
            os.unlink(f)
        except OSError:
            pass

    print(f"Registry written to {output_path}")


def usage() -> None:
    print(f"Usage: {sys.argv[0]} <plots directory> <output pdf path>")
    sys.exit(1)


if __name__ == "__main__":
    print("Rocketry P&ID KiCAD - Symbol Registry\n")

    if len(sys.argv) != 3:
        usage()

    plots_dir = sys.argv[1]
    output_path = sys.argv[2]

    if not os.path.isdir(plots_dir):
        print(f"Plots directory '{plots_dir}' does not exist.", file=sys.stderr)
        sys.exit(1)

    build_registry(plots_dir, output_path)
