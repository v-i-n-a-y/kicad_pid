# Copyright 2026 Vinay Williams

"""
Build the symbol registry, a to-scale PDF reference of every symbol.

Needs kicad-cli on the PATH and the Python packages reportlab, pillow and
svglib (pip install reportlab pillow svglib).  With svglib the symbol drawings
are vector.  Without it the build warns and falls back to 400 dpi rasters,
which also need rsvg-convert on the PATH.
"""

import io
import subprocess
import sys
from pathlib import Path
from xml.sax.saxutils import escape

from registry_data import Symbol, category_title, export_symbols, prefix_table
from reportlab.graphics.shapes import Drawing, Group
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Image,
    KeepTogether,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
)

TITLE = "P&ID Symbol Registry"
SUBTITLE = "KiCad symbol library for rocket propulsion fluid systems"
AUTHOR = "Vinay Williams"

# Palette
TEXT = colors.HexColor("#1F2933")
SECONDARY = colors.HexColor("#6B7280")
HAIRLINE = colors.HexColor("#D2D6DC")
ACCENT = colors.HexColor("#1F4E79")

PAGE_W, PAGE_H = A4
MARGIN = 15 * mm
CONTENT_W = PAGE_W - 2 * MARGIN
# Running header and footer sit inside the 15 mm margin; the body frame
# starts below the header rule and ends above the footer rule.
HEADER_RULE_Y = PAGE_H - MARGIN - 8 * mm
FOOTER_RULE_Y = MARGIN + 8 * mm
FRAME_TOP = HEADER_RULE_Y - 6 * mm
FRAME_BOTTOM = FOOTER_RULE_Y + 6 * mm

COLUMNS = 4
COLUMN_W = CONTENT_W / COLUMNS
CELL_PAD = 2 * mm
# One common physical scale: 1 mm on the symbol is SCALE mm on the page.
SCALE = 1.25
MAX_DESCRIPTION_LINES = 3

FONT_DIR = Path(__file__).resolve().parent.parent / "fonts"
FONT_FILES = {
    "Plex": "IBMPlexSans-Regular.ttf",
    "Plex-Medium": "IBMPlexSans-Medium.ttf",
    "Plex-SemiBold": "IBMPlexSans-SemiBold.ttf",
}
FONTS = {"regular": "Plex", "medium": "Plex-Medium", "semibold": "Plex-SemiBold"}


def register_fonts() -> None:
    """
    Register IBM Plex Sans, falling back to Helvetica with a warning

    Plex is vendored in fonts/ as TrueType; reportlab cannot use CFF outlines
    """
    if all((FONT_DIR / f).is_file() for f in FONT_FILES.values()):
        for name, f in FONT_FILES.items():
            pdfmetrics.registerFont(TTFont(name, str(FONT_DIR / f)))
        return
    print(
        f"Warning: IBM Plex Sans not found in {FONT_DIR}; using Helvetica.",
        file=sys.stderr,
    )
    FONTS.update(
        regular="Helvetica", medium="Helvetica-Bold", semibold="Helvetica-Bold"
    )


def revision() -> tuple:
    """
    Read the revision of the library from git

    Returns

    tuple
        Short commit hash and commit date (D Month YYYY), or ("unknown", "") outside git
    """
    repo = Path(__file__).resolve().parent.parent
    try:
        out = subprocess.run(
            ["git", "-C", str(repo), "log", "-1", "--format=%h %cs"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.split()
        year, month, day = out[1].split("-")
    except (OSError, subprocess.CalledProcessError, IndexError, ValueError):
        return "unknown", ""
    months = [
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ]
    return out[0], f"{int(day)} {months[int(month) - 1]} {year}"


def make_styles() -> dict:
    """
    Build the paragraph styles of the document

    Returns

    dict
        Style name to ParagraphStyle
    """
    f = FONTS

    def style(name, **kw):
        base = {
            "fontName": f["regular"],
            "textColor": TEXT,
            "fontSize": 8,
            "leading": 10,
        }
        base.update(kw)
        return ParagraphStyle(name, **base)

    return {
        "title": style("title", fontName=f["semibold"], fontSize=30, leading=34),
        "subtitle": style("subtitle", fontSize=12.5, leading=17, textColor=SECONDARY),
        "h1": style(
            "h1", fontName=f["semibold"], fontSize=13, leading=16, textColor=ACCENT
        ),
        "h2": style(
            "h2", fontName=f["semibold"], fontSize=10, leading=13, textColor=ACCENT
        ),
        "body": style("body", fontSize=8.5, leading=12),
        "label": style("label", fontSize=8, leading=11, textColor=SECONDARY),
        "value": style("value", fontName=f["medium"], fontSize=8.5, leading=11),
        "small": style("small", fontSize=7.5, leading=10),
        "small_r": style("small_r", fontSize=7.5, leading=10, alignment=TA_RIGHT),
        "prefix": style("prefix", fontName=f["semibold"], fontSize=8, leading=10),
        "name": style(
            "name", fontName=f["semibold"], fontSize=8, leading=10, alignment=TA_CENTER
        ),
        "ref": style(
            "ref",
            fontName=f["medium"],
            fontSize=6.5,
            leading=8,
            textColor=ACCENT,
            alignment=TA_CENTER,
        ),
        "desc": style(
            "desc",
            fontSize=7,
            leading=9,
            textColor=SECONDARY,
            alignment=TA_CENTER,
        ),
    }


def fit_lines(text: str, st: ParagraphStyle, width: float, max_lines: int) -> str:
    """
    Trim text so it wraps to at most max_lines lines

    Arguments

    text - str
        Plain text to fit
    st - ParagraphStyle
        Style the text will be set in
    width - float
        Available width in points
    max_lines - int
        Longest acceptable wrapped length

    Returns

    str
        The text, shortened with an ellipsis if it was too long
    """
    words = text.split()
    candidate = " ".join(words)
    while True:
        p = Paragraph(escape(candidate), st)
        p.wrap(width, 1000)
        if len(p.blPara.lines) <= max_lines or not words:
            return candidate
        words.pop()
        candidate = " ".join(words).rstrip(",;:") + "…"


def pack_rows(symbols: "list[Symbol]") -> "list[list[tuple]]":
    """
    Pack symbols into rows of COLUMNS equal columns

    A symbol too wide for one column spans as many as it needs, so no symbol is
    ever scaled or clipped

    Arguments

    symbols - list[Symbol]
        Symbols of one category in display order

    Returns

    list[list[tuple]]
        Rows of (symbol, columns spanned)
    """
    rows, row, used = [], [], 0
    for s in symbols:
        span = 1
        while (
            s.width_mm * mm * SCALE + 2 * CELL_PAD > span * COLUMN_W and span < COLUMNS
        ):
            span += 1
        if used + span > COLUMNS:
            rows.append(row)
            row, used = [], 0
        row.append((s, span))
        used += span
    if row:
        rows.append(row)
    return rows


def symbol_drawing(s: Symbol, w_pt: float, h_pt: float):
    """
    Make the flowable that draws one symbol at the registry scale

    Arguments

    s - Symbol
        Symbol to draw, vector or raster
    w_pt - float
        Width on the page in points
    h_pt - float
        Height on the page in points

    Returns

    Flowable
        A new Drawing for a vector symbol, an Image for a raster one
    """
    if s.drawing is None:
        return Image(io.BytesIO(s.png), width=w_pt, height=h_pt)
    flowable = Drawing(w_pt, h_pt)
    flowable.add(Group(s.drawing, transform=(SCALE, 0, 0, SCALE, 0, 0)))
    flowable.hAlign = "CENTER"
    return flowable


def symbol_row(row: "list[tuple]", st: dict, category: str) -> Table:
    """
    Lay out one grid row as a single table that is never split

    The drawing row is as tall as the tallest drawing, so captions line up
    across the row; names, tags and descriptions each have a row of their own
    for the same reason

    Arguments

    row - list[tuple]
        (symbol, columns spanned) pairs
    st - dict
        Paragraph styles
    category - str
        Category slug, used for the running header

    Returns

    Table
        The row, carrying its category for the running header
    """
    drawings, names, refs, descs, cmds = [], [], [], [], []
    col = 0
    for s, span in row:
        width = span * COLUMN_W - 2 * CELL_PAD
        w_pt, h_pt = s.width_mm * mm * SCALE, s.height_mm * mm * SCALE
        drawings += [symbol_drawing(s, w_pt, h_pt)]
        nm = escape(s.name).replace(" - ", " - ")
        names += [Paragraph(nm, st["name"])]
        refs += [
            Paragraph(f"Ref {escape(s.reference)}" if s.reference else "", st["ref"])
        ]
        text = fit_lines(s.description, st["desc"], width, MAX_DESCRIPTION_LINES)
        descs += [Paragraph(escape(text), st["desc"])]
        end = col + span - 1
        if span > 1:
            for r in range(4):
                cmds.append(("SPAN", (col, r), (end, r)))
        if end < COLUMNS - 1:
            cmds.append(("LINEAFTER", (end, 0), (end, -1), 0.4, HAIRLINE))
        col = end + 1
        # Placeholders hold the spanned columns so every table row has 4 cells
        for lst in (drawings, names, refs, descs):
            lst.extend([""] * (span - 1))
    for lst in (drawings, names, refs, descs):
        lst.extend([""] * (COLUMNS - len(lst)))
    tallest = max(s.height_mm for s, _ in row) * mm * SCALE
    table = Table(
        [drawings, names, refs, descs],
        colWidths=[COLUMN_W] * COLUMNS,
        rowHeights=[tallest + 8 * mm, None, None, None],
    )
    table.setStyle(
        [
            ("ALIGN", (0, 0), (-1, 0), "CENTER"),
            ("VALIGN", (0, 0), (-1, 0), "MIDDLE"),
            ("VALIGN", (0, 1), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), CELL_PAD),
            ("RIGHTPADDING", (0, 0), (-1, -1), CELL_PAD),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 3), (-1, 3), 3 * mm),
            ("TOPPADDING", (0, 2), (-1, 2), 0.5 * mm),
            ("TOPPADDING", (0, 3), (-1, 3), 0.8 * mm),
            ("LINEBELOW", (0, -1), (-1, -1), 0.4, HAIRLINE),
        ]
        + cmds
    )
    table.section = category
    return table


def heading(title: str, key: str, st: dict) -> Table:
    """
    Build an accent heading with an accent rule, kept with what follows it

    Arguments

    title - str
        Heading text
    key - str
        Bookmark key used by the contents page and the PDF outline
    st - dict
        Paragraph styles

    Returns

    Table
        Heading flowable carrying its section name for the running header
    """
    t = Table([[Paragraph(escape(title), st["h1"])]], colWidths=[CONTENT_W])
    t.setStyle(
        [
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2 * mm),
            ("LINEBELOW", (0, 0), (-1, -1), 0.9, ACCENT),
        ]
    )
    t.keepWithNext = True
    t.spaceBefore = 7 * mm
    t.spaceAfter = 1 * mm
    t.section = title
    t.bookmark = (key, title)
    return t


def cover_story(st: dict, symbols: "list[Symbol]", categories: int, rev: tuple) -> list:
    """
    Build the cover page

    Arguments

    st - dict
        Paragraph styles
    symbols - list[Symbol]
        All symbols, for the count
    categories - int
        Number of categories
    rev - tuple
        Short hash and commit date

    Returns

    list
        Flowables for the cover page
    """
    rev_text = rev[0] + (f", {rev[1]}" if rev[1] else "")
    facts = [
        ("Symbols", str(len(symbols))),
        ("Categories", str(categories)),
        (
            "Drawing scale",
            f"{SCALE:g} : 1 for every symbol (1 mm on a symbol is {SCALE:g} mm on the page, printed at 100 per cent)",
        ),
        ("Revision", rev_text),
        ("Maintained by", AUTHOR),
        ("Licence", "MIT licence"),
    ]
    facts_t = Table(
        [
            [Paragraph(k, st["label"]), Paragraph(escape(v), st["value"])]
            for k, v in facts
        ],
        colWidths=[34 * mm, CONTENT_W - 34 * mm],
    )
    facts_t.setStyle(
        [
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 2.2 * mm),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2.2 * mm),
            ("LINEBELOW", (0, 0), (-1, -1), 0.4, HAIRLINE),
            ("LINEABOVE", (0, 0), (-1, 0), 0.4, HAIRLINE),
        ]
    )
    notes = [
        "All connection points lie on whole millimetres. Use a 1 mm connection grid.",
        "Two-port inline symbols connect at x = \u00b18 mm.",
        (
            "Pins are numbered for flow direction: 1\u00a0IN, 2\u00a0OUT, 3\u00a0BRANCH, "
            "4\u00a0BRANCH2. Tanks use 1\u00a0TOP and 2\u00a0BOTTOM, single ports 1\u00a0PORT."
        ),
        "Reference prefixes follow ISA 5.1. KiCad appends the loop number (V1, PT3).",
        "Instrument letters are held in the editable Function field.",
    ]
    rows = [[Paragraph("GENERAL NOTES", st["label"]), ""]]
    for i, n in enumerate(notes, 1):
        rows.append([Paragraph(f"{i}.", st["body"]), Paragraph(escape(n), st["body"])])
    panel = Table(rows, colWidths=[8 * mm, CONTENT_W - 8 * mm])
    panel.setStyle(
        [
            ("SPAN", (0, 0), (-1, 0)),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 1.2 * mm),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 1.2 * mm),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 2.5 * mm),
            ("LINEBELOW", (0, 0), (-1, 0), 0.4, HAIRLINE),
        ]
    )
    rule = Table([[""]], colWidths=[28 * mm], rowHeights=[1])
    rule.setStyle([("LINEBELOW", (0, 0), (-1, -1), 2.2, ACCENT)])
    rule.hAlign = "LEFT"
    return [
        Spacer(1, 48 * mm),
        Paragraph(escape(TITLE), st["title"]),
        Spacer(1, 5 * mm),
        rule,
        Spacer(1, 5 * mm),
        Paragraph(escape(SUBTITLE), st["subtitle"]),
        Spacer(1, 30 * mm),
        facts_t,
        Spacer(1, 16 * mm),
        panel,
    ]


def contents_story(
    st: dict, cats: "list[tuple]", pages: dict, prefixes: "list[tuple]"
) -> list:
    """
    Build the contents page and the reference prefix table

    Arguments

    st - dict
        Paragraph styles
    cats - list[tuple]
        (slug, title, symbol count) in document order
    pages - dict
        Slug to page number, from the first pass; "prefixes" is the prefix table
    prefixes - list[tuple]
        (prefix, used for) rows

    Returns

    list
        Flowables for the contents page
    """
    rows = [
        [
            Paragraph(
                f'<a href="#cat_{slug}" color="#1F2933">{escape(title)}</a>',
                st["small"],
            ),
            Paragraph(str(count), st["small_r"]),
            Paragraph(str(pages.get(slug, "")), st["small_r"]),
        ]
        for slug, title, count in cats
    ]
    rows.insert(
        0,
        [
            Paragraph(
                '<a href="#prefixes" color="#1F2933">Reference prefixes</a>',
                st["small"],
            ),
            Paragraph("", st["small_r"]),
            Paragraph(str(pages.get("prefixes", "")), st["small_r"]),
        ],
    )
    head = [
        Paragraph("Category", st["label"]),
        Paragraph(
            "Symbols", ParagraphStyle("lr", parent=st["label"], alignment=TA_RIGHT)
        ),
        Paragraph(
            "Page", ParagraphStyle("lr2", parent=st["label"], alignment=TA_RIGHT)
        ),
    ]
    toc = Table([head] + rows, colWidths=[CONTENT_W - 40 * mm, 20 * mm, 20 * mm])
    toc.setStyle(table_style(header=True))
    ptable = Table(
        [[Paragraph("Prefix", st["label"]), Paragraph("Used for", st["label"])]]
        + [
            [Paragraph(escape(p), st["prefix"]), Paragraph(escape(u), st["small"])]
            for p, u in prefixes
        ],
        colWidths=[22 * mm, CONTENT_W - 22 * mm],
        repeatRows=1,
    )
    ptable.setStyle(table_style(header=True))
    h_contents = heading("Contents", "contents", st)
    h_contents.spaceBefore = 0
    h_prefix = heading("Reference prefixes", "prefixes", st)
    h_prefix.spaceBefore = 0
    return [
        h_contents,
        toc,
        PageBreak(),
        h_prefix,
        Paragraph(
            "Each symbol carries an ISA 5.1 style Reference prefix; KiCad appends "
            "the annotation number.",
            ParagraphStyle(
                "note", parent=st["small"], textColor=SECONDARY, spaceAfter=2 * mm
            ),
        ),
        ptable,
        PageBreak(),
    ]


def table_style(header: bool) -> list:
    """
    Compact hairline table style shared by the contents tables

    Arguments

    header - bool
        True if the first row is a header row

    Returns

    list
        Table style commands
    """
    cmds = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2 * mm),
        ("TOPPADDING", (0, 0), (-1, -1), 1.3 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.3 * mm),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, HAIRLINE),
    ]
    if header:
        cmds.append(("LINEBELOW", (0, 0), (-1, 0), 0.8, ACCENT))
    return cmds


class RegistryDoc(BaseDocTemplate):
    """
    A4 document with a running header and footer

    Records the page each heading lands on and the section shown in each header
    """

    def __init__(self, target, total_pages: int, rev: tuple, **kw):
        super().__init__(target, pagesize=A4, **kw)
        self.total_pages = total_pages
        self.rev = rev
        self.heading_pages: dict = {}
        self.page_section: dict = {}
        frame = Frame(
            MARGIN,
            FRAME_BOTTOM,
            CONTENT_W,
            FRAME_TOP - FRAME_BOTTOM,
            leftPadding=0,
            rightPadding=0,
            topPadding=0,
            bottomPadding=0,
            id="body",
        )
        self.addPageTemplates(
            [
                PageTemplate(id="cover", frames=[frame], onPageEnd=self.draw_cover),
                PageTemplate(id="body", frames=[frame], onPageEnd=self.draw_running),
            ]
        )

    def afterFlowable(self, flowable) -> None:
        """
        Record headings and sections, and add bookmarks

        Arguments

        flowable - Flowable
            Flowable that has just been placed
        """
        section = getattr(flowable, "section", None)
        if section and self.page not in self.page_section:
            self.page_section[self.page] = section
        mark = getattr(flowable, "bookmark", None)
        if mark:
            key, title = mark
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(title, key, 0)
            self.heading_pages[key] = self.page

    def draw_cover(self, canv, doc) -> None:
        """
        Page end callback for the cover, which has no header or footer

        Arguments

        canv - Canvas
            Canvas of the page
        doc - BaseDocTemplate
            This document
        """
        canv.setTitle(TITLE)

    def draw_running(self, canv, doc) -> None:
        """
        Page end callback drawing the running header and footer

        Arguments

        canv - Canvas
            Canvas of the page
        doc - BaseDocTemplate
            This document
        """
        # A page with no heading of its own continues the previous section
        page = doc.page
        section = self.page_section.get(page)
        if section is None:
            section = self.page_section.get(page - 1, "")
            self.page_section[page] = section
        canv.saveState()
        canv.setStrokeColor(HAIRLINE)
        canv.setLineWidth(0.4)
        canv.line(MARGIN, HEADER_RULE_Y, PAGE_W - MARGIN, HEADER_RULE_Y)
        canv.line(MARGIN, FOOTER_RULE_Y, PAGE_W - MARGIN, FOOTER_RULE_Y)
        spaced(
            canv,
            FONTS["medium"],
            7.5,
            SECONDARY,
            0.5,
            MARGIN,
            HEADER_RULE_Y + 2.2 * mm,
            TITLE.upper(),
        )
        spaced(
            canv,
            FONTS["medium"],
            7.5,
            ACCENT,
            0.5,
            PAGE_W - MARGIN,
            HEADER_RULE_Y + 2.2 * mm,
            section.upper(),
            right=True,
        )
        rev_text = (
            "Revision " + self.rev[0] + (f", {self.rev[1]}" if self.rev[1] else "")
        )
        spaced(
            canv,
            FONTS["regular"],
            7,
            SECONDARY,
            0,
            MARGIN,
            FOOTER_RULE_Y - 4.2 * mm,
            rev_text,
        )
        spaced(
            canv,
            FONTS["regular"],
            7,
            SECONDARY,
            0,
            PAGE_W - MARGIN,
            FOOTER_RULE_Y - 4.2 * mm,
            f"Page {page} of {self.total_pages}",
            right=True,
        )
        canv.restoreState()


def spaced(canv, font, size, colour, space, x, y, text, right=False) -> None:
    """
    Draw one line of letter spaced text

    Arguments

    canv - Canvas
        Canvas to draw on
    font - str
        Registered font name
    size - float
        Font size in points
    colour - Color
        Text colour
    space - float
        Extra space between letters in points
    x - float
        Left edge, or right edge when right is set
    y - float
        Baseline
    text - str
        Text to draw
    right - bool
        Right align at x
    """
    width = pdfmetrics.stringWidth(text, font, size) + space * len(text)
    t = canv.beginText(x - width if right else x, y)
    t.setFont(font, size)
    t.setFillColor(colour)
    t.setCharSpace(space)
    t.textOut(text)
    canv.drawText(t)


def build_story(
    symbols: "list[Symbol]", pages: dict, rev: tuple, st: dict
) -> "tuple[list, list]":
    """
    Build every flowable of the document

    Arguments

    symbols - list[Symbol]
        Symbols in registry order
    pages - dict
        Slug to page number from the first pass
    rev - tuple
        Short hash and commit date
    st - dict
        Paragraph styles

    Returns

    tuple
        The story and the (slug, title, count) list of categories
    """
    by_cat: dict[str, list] = {}
    for s in symbols:
        by_cat.setdefault(s.category, []).append(s)
    cats = [(c, category_title(c), len(v)) for c, v in by_cat.items()]
    cat_pages = {slug: pages.get(f"cat_{slug}", "") for slug in by_cat}
    cat_pages["prefixes"] = pages.get("prefixes", "")
    story = cover_story(st, symbols, len(cats), rev)
    # The cover uses the header-free template, everything after it the other
    story += [NextPageTemplate("body"), PageBreak()]
    story += contents_story(st, cats, cat_pages, prefix_table(symbols))
    for slug, title, _ in cats:
        rows = [symbol_row(r, st, title) for r in pack_rows(by_cat[slug])]
        # The heading always travels with the first row, never alone at a page foot
        story.append(KeepTogether([heading(title, f"cat_{slug}", st), rows[0]]))
        story += [KeepTogether([r]) for r in rows[1:]]
    return story, cats


def build_pdf(story: list, target, total: int, rev: tuple) -> RegistryDoc:
    """
    Run one layout pass

    Arguments

    story - list
        Flowables (consumed by the build)
    target - str | file
        Output path or file object
    total - int
        Total page count shown in the footer
    rev - tuple
        Short hash and commit date

    Returns

    RegistryDoc
        The finished document, holding page numbers
    """
    doc = RegistryDoc(
        target,
        total,
        rev,
        title=TITLE,
        author=AUTHOR,
        subject=SUBTITLE,
        creator="scripts/registry.py",
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=MARGIN,
    )
    doc.build(story)
    return doc


def build_registry(output_path: str, symbols_dir: Path) -> None:
    """
    Build the registry PDF in two passes so that the contents page and the
    footer carry the final page numbers

    Arguments

    output_path - str
        PDF to write
    symbols_dir - Path
        Directory holding the symbol files
    """
    register_fonts()
    symbols = export_symbols(symbols_dir)
    if not symbols:
        print("No symbols found.", file=sys.stderr)
        sys.exit(1)
    st = make_styles()
    rev = revision()
    story, _ = build_story(symbols, {}, rev, st)
    first = build_pdf(story, io.BytesIO(), 0, rev)
    total = first.page
    story, _ = build_story(symbols, first.heading_pages, rev, st)
    final = build_pdf(story, output_path, total, rev)
    if final.page != total or final.heading_pages != first.heading_pages:
        print("Warning: page numbers moved between passes.", file=sys.stderr)
    print(f"Registry written to {output_path} ({total} pages, scale {SCALE:g} : 1)")


def usage() -> None:
    """
    Usage

    Prints the script's usage
    """
    print(
        f"Usage: {sys.argv[0]} <plots directory> <output pdf path> [symbols directory]\n"
        "  The plots directory is accepted for compatibility and not used; symbols\n"
        "  are exported afresh. The symbols directory defaults to symbols/ next to it."
    )
    sys.exit(1)


if __name__ == "__main__":
    print("Rocketry P&ID KiCAD - Symbol Registry\n")

    if len(sys.argv) not in (3, 4):
        usage()

    plots_dir = Path(sys.argv[1]).resolve()
    sym_dir = Path(sys.argv[3]) if len(sys.argv) == 4 else plots_dir.parent / "symbols"
    if not sym_dir.is_dir():
        print(f"Symbols directory '{sym_dir}' does not exist.", file=sys.stderr)
        sys.exit(1)

    build_registry(sys.argv[2], sym_dir)
