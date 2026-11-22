"""PDF survey report.

Layout in the "engineering blueprint" style of DESIGN.md: near-monochrome, one sans-serif
family, hairline borders, rounded panels and generous spacing, with colour only in the graphs
and a thin accent strip at the top. Every text is in the requested language, and every line
goes through clean_text so the report never contains long dashes.
"""

from __future__ import annotations

import io
import os
from datetime import datetime
from typing import List, Optional

import matplotlib
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.platypus import (
    Paragraph as _ReportLabParagraph,
    BaseDocTemplate,
    Flowable,
    Frame,
    Image as RLImage,
    KeepTogether,
    PageTemplate,
    Spacer,
    Table,
    TableStyle,
)

from analysis.comparison import compare_with_file, compare_with_target
from analysis.statistics import calculate_statistics
from i18n.translations import display_device, display_note, tr, use_language
from models.project import LuminationProject
from reporting.chart_exporter import export_charts_image, export_room_map_image
from utils.app_info import APP_NAME

# The report never contains long dashes: em dash, en dash, figure dash, horizontal bar and the
# typographic minus are all written as a plain hyphen, including in names and notes typed by users.
_LONG_DASHES = str.maketrans({"—": "-", "–": "-", "‒": "-", "―": "-", "−": "-", "⸺": "-", "⸻": "-"})


def clean_text(text: str) -> str:
    """Replace every long dash with a hyphen."""
    return str(text).translate(_LONG_DASHES)


def Paragraph(text, style, *args, **kwargs):
    """Every line of the report goes through clean_text."""
    return _ReportLabParagraph(clean_text(text), style, *args, **kwargs)


# ---------------------------------------------------------------- design tokens (DESIGN.md)
INK = colors.HexColor("#1b1b1b")        # primary text
STEEL = colors.HexColor("#60646c")      # secondary text
ASH = colors.HexColor("#7c7c7c")        # tertiary text
HAIRLINE = colors.HexColor("#e0e1e6")   # 1 px borders and rules
CANVAS = colors.HexColor("#f4f4f5")     # soft panel tint (print-friendly version of the gray canvas)
WHITE = colors.white
GRADIENT = (colors.HexColor("#19a05f"), colors.HexColor("#0d7f8c"))  # the one accent strip

PAGE_W, PAGE_H = A4
MARGIN = 18 * mm
CONTENT_W = PAGE_W - 2 * MARGIN
RADIUS = 6  # points; panels and cards

FONT_DIR = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
FONTS = {"regular": "LuxUI", "light": "LuxUI-Light", "semibold": "LuxUI-Semibold", "bold": "LuxUI-Bold"}


def _register_fonts() -> None:
    """Segoe UI (Windows) stands in for Inter; DejaVu (bundled with matplotlib) if it is missing."""
    if FONTS["regular"] in pdfmetrics.getRegisteredFontNames():
        return
    files = {"regular": "segoeui.ttf", "light": "segoeuil.ttf", "semibold": "seguisb.ttf", "bold": "segoeuib.ttf"}
    fallback = os.path.join(matplotlib.get_data_path(), "fonts", "ttf")
    fallback_files = {"regular": "DejaVuSans.ttf", "light": "DejaVuSans.ttf",
                      "semibold": "DejaVuSans-Bold.ttf", "bold": "DejaVuSans-Bold.ttf"}
    for key, name in FONTS.items():
        path = os.path.join(FONT_DIR, files[key])
        if not os.path.isfile(path):
            path = os.path.join(fallback, fallback_files[key])
        pdfmetrics.registerFont(TTFont(name, path))
    from reportlab.lib.fonts import addMapping

    addMapping(FONTS["regular"], 0, 0, FONTS["regular"])
    addMapping(FONTS["regular"], 1, 0, FONTS["semibold"])
    addMapping(FONTS["regular"], 0, 1, FONTS["regular"])
    addMapping(FONTS["regular"], 1, 1, FONTS["semibold"])


def _style(name: str, size: float, color=INK, font: str = "regular", leading: Optional[float] = None, **kw) -> ParagraphStyle:
    return ParagraphStyle(name, fontName=FONTS[font], fontSize=size, leading=leading or size * 1.45, textColor=color, **kw)


# ---------------------------------------------------------------- small building blocks

class TrackedText(Flowable):
    """One line of text with letter spacing (used for the title and the small uppercase labels)."""

    def __init__(self, text: str, size: float, font: str, color, tracking: float, space_after: float = 0) -> None:
        super().__init__()
        self.text = clean_text(text)
        self.size, self.font, self.color, self.tracking = size, FONTS[font], color, tracking
        self.space_after = space_after

    def wrap(self, avail_w, avail_h):
        self.width = avail_w
        return avail_w, self.size * 1.15 + self.space_after

    def draw(self):
        text = self.canv.beginText(0, self.space_after + self.size * 0.22)
        text.setFont(self.font, self.size)
        text.setCharSpace(self.tracking)
        text.setFillColor(self.color)
        text.textLine(self.text)
        text.setCharSpace(0)
        self.canv.drawText(text)


def _upper(text: str) -> str:
    return text.upper().replace("Σ", "σ")  # keep sigma as the standard-deviation symbol


def _label(text: str) -> TrackedText:
    return TrackedText(_upper(text), 7.2, "semibold", STEEL, 0.9)


def _small_label(text: str):
    """Uppercase caption that wraps inside narrow panel columns."""
    return Paragraph(_upper(text), _style("caption", 6.8, STEEL, "semibold", leading=8.6))


class _Heading(Flowable):
    """Section heading placeholder; _keep_headings replaces it with its parts plus the next block."""

    def __init__(self, parts: List) -> None:
        super().__init__()
        self.parts = parts

    def wrap(self, *_args):
        return 0, 0

    def draw(self):
        pass


def _section(title: str, number: int) -> List:
    """Section heading: small step number, title, hairline rule (kept with what follows)."""
    return [_Heading([
        Spacer(1, 16),
        _label(f"{number:02d}"),
        Spacer(1, 2),
        Paragraph(title, _style("section", 13.5, INK, "semibold", leading=17)),
        Spacer(1, 6),
        Table([[""]], colWidths=[CONTENT_W], rowHeights=[0.1],
              style=TableStyle([("LINEABOVE", (0, 0), (-1, -1), 0.6, HAIRLINE)])),
        Spacer(1, 10),
    ])]


def _keep_headings(story: List) -> List:
    """Expand headings; each part is marked "keep with next" so a heading never ends a page."""
    result: List = []
    for item in story:
        if isinstance(item, _Heading):
            for part in item.parts:
                part.keepWithNext = 1
            result.extend(item.parts)
        else:
            result.append(item)
    return result


def _panel(rows, col_widths, fill=WHITE, padding=7, extra=None) -> Table:
    """Rounded panel with a hairline border."""
    table = Table(rows, colWidths=col_widths)
    commands = [
        ("BACKGROUND", (0, 0), (-1, -1), fill),
        ("BOX", (0, 0), (-1, -1), 0.6, HAIRLINE),
        ("ROUNDEDCORNERS", [RADIUS, RADIUS, RADIUS, RADIUS]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), padding + 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), padding + 3),
        ("TOPPADDING", (0, 0), (-1, -1), padding),
        ("BOTTOMPADDING", (0, 0), (-1, -1), padding),
    ]
    table.setStyle(TableStyle(commands + (extra or [])))
    return table


def _kv(label: str, value: str) -> List:
    """Label above value (used inside panels)."""
    return [_small_label(label.rstrip(":")), Spacer(1, 3), Paragraph(value, _style("kv", 10, INK, "regular", leading=13))]


def _metric_card(label: str, value: str, unit: str, note: str, width: float, big: bool = True) -> Table:
    value_size = 21 if big else 15
    value_html = (f"<font name='{FONTS['semibold']}' size='{value_size}'>{value}</font>"
                  f"<font name='{FONTS['regular']}' size='{value_size * 0.5:.1f}' color='#60646c'>&nbsp;{unit}</font>")
    cell = [
        _small_label(label),
        Spacer(1, 5),
        Paragraph(value_html, _style("metric", value_size, INK, leading=value_size * 1.15)),
        Spacer(1, 3),
        Paragraph(note or "&nbsp;", _style("metric_note", 8, ASH, leading=10)),
    ]
    return _panel([[cell]], [width], padding=8)


def _card_row(cards, gap: float = 8) -> Table:
    widths = []
    row = []
    for index, card in enumerate(cards):
        if index:
            row.append("")
            widths.append(gap)
        row.append(card)
        widths.append(card._colWidths[0])
    return Table([row], colWidths=widths, style=TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))


def _image(data: bytes, width: float) -> RLImage:
    from PIL import Image as PILImage

    w_px, h_px = PILImage.open(io.BytesIO(data)).size
    return RLImage(io.BytesIO(data), width=width, height=width * h_px / w_px)


def _logo_png() -> Optional[bytes]:
    base = getattr(__import__("sys"), "_MEIPASS", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    path = os.path.join(base, "assets", "luxious.ico")
    if not os.path.isfile(path):
        return None
    from PIL import Image as PILImage

    icon = PILImage.open(path)
    icon.size = max(icon.info.get("sizes", [icon.size]))
    buf = io.BytesIO()
    icon.convert("RGBA").save(buf, format="PNG")
    return buf.getvalue()


# ---------------------------------------------------------------- page decoration

class _NumberedCanvas(rl_canvas.Canvas):
    """Two-pass canvas so the footer can say "Page X of Y"."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._pages = []

    def showPage(self):
        self._pages.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total = len(self._pages)
        for state in self._pages:
            self.__dict__.update(state)
            self.setFont(FONTS["regular"], 7.5)
            self.setFillColor(ASH)
            self.drawRightString(PAGE_W - MARGIN, 11 * mm, clean_text(tr("pdf2_page", page=self._pageNumber, total=total)))
            super().showPage()
        super().save()


def _decorate(canvas, doc, project: LuminationProject, logo: Optional[bytes], generated: str) -> None:
    canvas.saveState()
    # Accent strip: the only interface colour, a thin gradient along the top edge.
    steps = 120
    for i in range(steps):
        t = i / (steps - 1)
        r = GRADIENT[0].red + (GRADIENT[1].red - GRADIENT[0].red) * t
        g = GRADIENT[0].green + (GRADIENT[1].green - GRADIENT[0].green) * t
        b = GRADIENT[0].blue + (GRADIENT[1].blue - GRADIENT[0].blue) * t
        canvas.setFillColor(colors.Color(r, g, b))
        canvas.rect(PAGE_W * i / steps, PAGE_H - 3.2, PAGE_W / steps + 0.5, 3.2, stroke=0, fill=1)
    # Header: logo + wordmark left, document type right, hairline below.
    top = PAGE_H - 13 * mm
    x = MARGIN
    if logo:
        from reportlab.lib.utils import ImageReader

        canvas.drawImage(ImageReader(io.BytesIO(logo)), x, top - 3, width=14, height=14, mask="auto")
        x += 19
    text = canvas.beginText(x, top + 1)
    text.setFont(FONTS["semibold"], 9.5)
    text.setCharSpace(1.6)
    text.setFillColor(INK)
    text.textLine(APP_NAME.upper())
    text.setCharSpace(0)
    canvas.drawText(text)
    canvas.setFont(FONTS["regular"], 8)
    canvas.setFillColor(STEEL)
    canvas.drawRightString(PAGE_W - MARGIN, top + 1, clean_text(tr("pdf2_kicker")))
    canvas.setStrokeColor(HAIRLINE)
    canvas.setLineWidth(0.6)
    canvas.line(MARGIN, top - 7, PAGE_W - MARGIN, top - 7)
    # Footer: hairline, project and date left (page number added by _NumberedCanvas).
    canvas.line(MARGIN, 15 * mm, PAGE_W - MARGIN, 15 * mm)
    canvas.setFont(FONTS["regular"], 7.5)
    canvas.setFillColor(ASH)
    canvas.drawString(MARGIN, 11 * mm, clean_text(f"{project.name}  ·  {generated}"))
    canvas.restoreState()


# ---------------------------------------------------------------- the report

def generate_pdf_report(project: LuminationProject, output_path: str, lang: Optional[str] = None) -> str:
    """Write the survey report; ``lang`` selects its language (default: the app's language)."""
    # Matplotlib draws negative numbers with a long typographic minus; use a hyphen in the images.
    with use_language(lang), matplotlib.rc_context({"axes.unicode_minus": False}):
        return _build(project, output_path)


def _build(project: LuminationProject, output_path: str) -> str:
    _register_fonts()
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    generated = datetime.now().strftime("%Y-%m-%d %H:%M")
    logo = _logo_png()
    doc = BaseDocTemplate(output_path, pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN,
                          topMargin=24 * mm, bottomMargin=21 * mm,
                          title=clean_text(project.name), author=clean_text(project.author or APP_NAME))
    frame = Frame(MARGIN, 21 * mm, CONTENT_W, PAGE_H - 45 * mm, id="body", leftPadding=0, rightPadding=0,
                  topPadding=0, bottomPadding=0)
    doc.addPageTemplates([PageTemplate(id="page", frames=[frame],
                                       onPage=lambda c, d: _decorate(c, d, project, logo, generated))])

    body = _style("body", 9.5, STEEL, leading=14)
    small = _style("small", 8, ASH, leading=11)
    room = project.room
    stats = calculate_statistics(project.points)
    story: List = []

    # ---- Title block
    story += [
        Spacer(1, 4),
        _label(tr("pdf2_kicker")),
        Spacer(1, 6),
        TrackedText(project.name or tr("pdf_default_title"), 26, "semibold", INK, -0.8, space_after=4),
        Paragraph(f"{room.name}  ·  {tr('pdf_survey_date').rstrip(':')} {generated}", _style("subtitle", 10.5, STEEL, leading=15)),
        Spacer(1, 14),
    ]
    meta = [
        _kv(tr("pdf_author"), project.author or tr("pdf_not_specified")),
        _kv(tr("pdf_room_dims"), tr("pdf_room_dims_value", length=f"{room.length:.2f}", width=f"{room.width:.2f}")),
        _kv(tr("pdf_floor_area"), f"{room.area:.2f} m²"),
        _kv(tr("pdf_wall_margin"), f"{room.wall_margin:.2f} m"),
        _kv(tr("pdf_points_total"), tr("pdf_points_value", total=len(project.points),
                                      measured=len(project.get_measured_points()))),
    ]
    col = CONTENT_W / 5
    story.append(_panel([meta], [col] * 5, fill=CANVAS, padding=9,
                        extra=[("LINEAFTER", (0, 0), (-2, -1), 0.6, HAIRLINE)]))

    # ---- 01 Results
    story += _section(tr("pdf_analysis"), 1)
    if stats:
        gap = 8
        big_w = (CONTENT_W - 3 * gap) / 4

        def at(point_id, coords):
            location = f"({coords[0]:.2f}, {coords[1]:.2f}) m" if coords else ""
            return tr("pdf_at", point=point_id or "", location=location)

        story.append(_card_row([
            _metric_card(tr("kpi_card_avg"), f"{stats.e_avg:.1f}", "lx", tr("kpi_sub_count", count=stats.count), big_w),
            _metric_card(tr("kpi_card_u0"), f"{stats.uniformity_u0:.3f}", "", tr("kpi_sub_u0"), big_w),
            _metric_card(tr("kpi_card_min"), f"{stats.e_min:.1f}", "lx", at(stats.min_point_id, stats.min_coords), big_w),
            _metric_card(tr("kpi_card_max"), f"{stats.e_max:.1f}", "lx", at(stats.max_point_id, stats.max_coords), big_w),
        ], gap))
        story.append(Spacer(1, gap))
        story.append(_card_row([
            _metric_card(tr("kpi_card_u1"), f"{stats.uniformity_u1:.3f}", "", tr("kpi_sub_u1"), big_w, big=False),
            _metric_card(tr("kpi_card_std"), f"{stats.std_dev:.1f}", "lx", tr("kpi_sub_cv", cv=f"{stats.std_dev / stats.e_avg * 100:.1f}") if stats.e_avg else "", big_w, big=False),
            _metric_card(tr("kpi_card_median"), f"{stats.median:.1f}", "lx", tr("kpi_sub_percentile"), big_w, big=False),
            _metric_card(tr("kpi_card_range"), f"{stats.range_val:.1f}", "lx", tr("kpi_sub_range"), big_w, big=False),
        ], gap))
    else:
        story.append(Paragraph(tr("pdf_no_stats"), body))

    section = 1

    # ---- 02 Target (only when a target is set)
    if project.target_lux and project.target_lux > 0:
        target = compare_with_target(project.points, project.target_lux)
        if target:
            section += 1
            story += _section(tr("pdf_target_section"), section)
            share = target.percentage_above_or_equal / 100.0
            bar = Table([["", ""]], colWidths=[max(0.5, CONTENT_W * share), max(0.5, CONTENT_W * (1 - share))],
                        rowHeights=[5], style=TableStyle([
                            ("BACKGROUND", (0, 0), (0, 0), INK), ("BACKGROUND", (1, 0), (1, 0), HAIRLINE),
                            ("ROUNDEDCORNERS", [2.5, 2.5, 2.5, 2.5]),
                            ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                            ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
            cells = [
                _kv(tr("pdf_target_ref"), f"{target.target_lux:.0f} lx"),
                _kv(tr("pdf_points_evaluated"), str(target.points_evaluated)),
                _kv(tr("pdf_points_below"), f"{target.points_below_target} ({target.percentage_below_target:.1f}%)"),
                _kv(tr("pdf_points_above"), f"{target.points_above_or_equal_target} ({target.percentage_above_or_equal:.1f}%)"),
                _kv(tr("pdf_mean_abs_dev"), f"{target.avg_absolute_deviation:.1f} lx"),
            ]
            story.append(KeepTogether([
                _panel([cells], [CONTENT_W / 5] * 5, padding=9,
                       extra=[("LINEAFTER", (0, 0), (-2, -1), 0.6, HAIRLINE)]),
                Spacer(1, 8), bar, Spacer(1, 6),
                Paragraph(tr("pdf_notice", text=target.summary_text), small),
            ]))

    # ---- 03 Comparison (only when the survey was compared with a file)
    file_comp = compare_with_file(project.points)
    if file_comp is not None:
        section += 1
        story += _section(tr("pdf_cmp_section"), section)
        if file_comp.has_depreciation:
            headline, headline_note = f"{file_comp.depreciation_pct:.1f}", "%"
        else:
            headline, headline_note = "0.0", "%"
        hero = [
            _label(tr("pdf_cmp_depreciation")),
            Spacer(1, 6),
            Paragraph(f"<font name='{FONTS['semibold']}' size='34'>{headline}</font>"
                      f"<font size='15' color='#60646c'>&nbsp;{headline_note}</font>", _style("hero", 34, INK, leading=38)),
            Spacer(1, 4),
            Paragraph(tr("pdf_cmp_no_depreciation", pct=f"{file_comp.difference_pct:.1f}") if not file_comp.has_depreciation
                      else f"{file_comp.difference_lux:+.1f} lx ({file_comp.difference_pct:+.1f}%)", small),
        ]
        details = [
            [_kv(tr("pdf_cmp_file"), project.comparison_file or "-"), _kv(tr("pdf_cmp_points"), str(file_comp.points_compared))],
            [_kv(tr("pdf_cmp_compared_avg"), f"{file_comp.compared_avg:.1f} lx"), _kv(tr("pdf_cmp_current_avg"), f"{file_comp.current_avg:.1f} lx")],
            [_kv(tr("pdf_cmp_difference"), f"{file_comp.difference_lux:+.1f} lx ({file_comp.difference_pct:+.1f}%)"), ""],
        ]
        left_w = CONTENT_W * 0.36
        right = Table(details, colWidths=[(CONTENT_W - left_w) / 2 - 1] * 2, style=TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 12),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 9), ("TOPPADDING", (0, 0), (-1, -1), 0)]))
        story.append(_panel([[hero, right]], [left_w, CONTENT_W - left_w], padding=12,
                            extra=[("LINEAFTER", (0, 0), (0, -1), 0.6, HAIRLINE),
                                   ("BACKGROUND", (0, 0), (0, -1), CANVAS)]))

    # ---- Map
    section += 1
    story += _section(tr("pdf_map_section"), section)
    map_png = export_room_map_image(project, dpi=220, width_in=7.0, height_in=4.6)
    story.append(_panel([[_image(map_png, CONTENT_W - 24)]], [CONTENT_W], padding=10))
    story += [Spacer(1, 6), Paragraph(tr("pdf_methodology"), small)]

    # ---- Distribution
    section += 1
    story += _section(tr("pdf_distribution_section"), section)
    charts_png = export_charts_image(project, dpi=220)
    story.append(_panel([[_image(charts_png, CONTENT_W - 24)]], [CONTENT_W], padding=10))

    # ---- Point list
    section += 1
    story += _section(tr("pdf_schedule_section"), section)
    show_compared = any(p.expected_lux is not None for p in project.points)
    head = _style("th", 7.2, STEEL, "semibold", leading=9)
    cell = _style("td", 8.6, INK, leading=11)
    num = _style("tdn", 8.6, INK, leading=11, alignment=TA_RIGHT)
    headn = _style("thn", 7.2, STEEL, "semibold", leading=9, alignment=TA_RIGHT)
    header = [Paragraph(tr("pdf_col_point").upper(), head), Paragraph(tr("col_x").upper(), headn),
              Paragraph(tr("col_y").upper(), headn), Paragraph(tr("pdf_col_measured").upper(), headn)]
    widths = [1.7, 1.7, 1.7, 2.6]
    if show_compared:
        header += [Paragraph(tr("pdf_col_expected").upper(), headn), Paragraph(tr("pdf_col_delta").upper(), headn)]
        widths += [2.6, 2.6]
    header.append(Paragraph(tr("pdf_col_notes").upper(), head))
    rows = [header]
    for p in project.points:
        notes = display_note(p.notes)
        if p.device_name:
            device = display_device(p.device_name)
            notes = f"{device} · {notes}" if notes else device
        row = [Paragraph(f"<font name='{FONTS['semibold']}'>{p.id}</font>", cell), Paragraph(f"{p.x:.2f}", num),
               Paragraph(f"{p.y:.2f}", num), Paragraph(f"{p.lux:.1f}" if p.lux is not None else "-", num)]
        if show_compared:
            row += [Paragraph(f"{p.expected_lux:.1f}" if p.expected_lux is not None else "-", num),
                    Paragraph(f"{p.delta_lux:+.1f}" if p.delta_lux is not None else "-", num)]
        row.append(Paragraph(("! " if p.is_possible_outlier else "") + (notes or ""), _style("tdnote", 8, STEEL, leading=10.5)))
        rows.append(row)
    unit = (CONTENT_W - 0) / (sum(widths) + 4.6)
    col_widths = [w * unit for w in widths] + [4.6 * unit]
    table = Table(rows, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("LINEBELOW", (0, 0), (-1, 0), 0.8, INK),
        ("LINEBELOW", (0, 1), (-1, -1), 0.4, HAIRLINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 4.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(table)

    doc.build(_keep_headings(story), canvasmaker=_NumberedCanvas)
    return output_path
