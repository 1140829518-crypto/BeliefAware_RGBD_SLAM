#!/usr/bin/env python3
"""Generate editable Visio Fig.1 system framework and preview exports.

The VSDX file is generated as an Open Packaging Convention archive with Visio
page XML. Rectangles, text blocks, and arrows are stored as separate Visio
shapes rather than one embedded raster image.
"""

from __future__ import annotations

import html
import math
import os
import subprocess
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Tuple


ROOT = Path(__file__).resolve().parent
VSDX_PATH = ROOT / "Fig1_System_Framework.vsdx"
SVG_PATH = ROOT / "Fig1_System_Framework.svg"
PDF_PATH = ROOT / "Fig1_System_Framework.pdf"
PNG_PATH = ROOT / "Fig1_System_Framework.png"
NOTES_PATH = ROOT / "Fig1_System_Framework_notes.md"

PAGE_W = 17.4
PAGE_H = 4.9
PX_PER_IN = 96

NS = "http://schemas.microsoft.com/office/visio/2012/main"
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"


@dataclass(frozen=True)
class Box:
    key: str
    title: str
    lines: Tuple[str, ...]
    x: float
    y: float
    w: float
    h: float
    fill: str
    line: str
    stroke: float = 1.2


@dataclass(frozen=True)
class Arrow:
    start: str
    end: str
    color: str = "#222222"
    dashed: bool = False
    label: str = ""
    offset: float = 0.0


def rgb_to_visio(hex_color: str) -> str:
    return hex_color.upper()


def esc(text: str) -> str:
    return html.escape(text, quote=False)


def display_title(title: str) -> Tuple[str, ...]:
    wraps = {
        "ORB-SLAM2 RGB-D Frontend": ("ORB-SLAM2 RGB-D", "Frontend"),
        "Temporal Dynamic Evidence Model": ("Temporal Dynamic Evidence", "Model"),
        "Dynamic Point Suppression": ("Dynamic Point", "Suppression"),
        "YOLOv5 Semantic Detection": ("YOLOv5 Semantic", "Detection"),
        "Backend Optimization": ("Backend", "Optimization"),
        "Object-level Semantic Map": ("Object-level", "Semantic Map"),
    }
    return wraps.get(title, (title,))


BOXES: List[Box] = [
    Box(
        "input",
        "RGB-D Input",
        ("RGB Image", "Depth Image"),
        0.35,
        2.28,
        1.75,
        1.05,
        "#DDEAF7",
        "#4F81BD",
    ),
    Box(
        "frontend",
        "ORB-SLAM2 RGB-D Frontend",
        ("Feature Extraction", "Feature Matching", "Pose Tracking"),
        2.55,
        2.15,
        2.60,
        1.38,
        "#DDEAF7",
        "#4F81BD",
    ),
    Box(
        "yolo",
        "YOLOv5 Semantic Detection",
        ("Object Category", "Confidence", "Semantic Mask"),
        2.55,
        0.36,
        2.60,
        1.42,
        "#FCE4D6",
        "#ED7D31",
    ),
    Box(
        "semantic",
        "Semantic Observation",
        ("Category and mask", "confidence observation"),
        5.72,
        0.54,
        2.15,
        0.98,
        "#FCE4D6",
        "#ED7D31",
    ),
    Box(
        "temporal",
        "Temporal Dynamic Evidence Model",
        ("Dynamic Evidence Score", "λ Decay", "γ Increment", "θ Threshold", "Dynamic State Decision"),
        5.62,
        1.92,
        2.78,
        2.05,
        "#E2F0D9",
        "#70AD47",
        1.8,
    ),
    Box(
        "suppression",
        "Dynamic Point Suppression",
        ("Dynamic Point Removal", "Feature Filtering", "Matching Constraint", "Tracking Constraint"),
        8.95,
        1.92,
        2.55,
        1.78,
        "#E2F0D9",
        "#70AD47",
    ),
    Box(
        "backend",
        "Backend Optimization",
        ("Local Mapping", "Loop Closing", "Graph Optimization"),
        12.10,
        2.12,
        2.18,
        1.42,
        "#EDEDED",
        "#7F7F7F",
    ),
    Box(
        "map",
        "Object-level Semantic Map",
        ("Object Category", "3D Position", "Object Observation Association", "Dynamic State"),
        11.88,
        0.32,
        2.72,
        1.62,
        "#EADCF8",
        "#8064A2",
    ),
    Box(
        "outputs",
        "Final Outputs",
        ("Camera Trajectory", "Static/Dynamic Map Points", "Object-level Semantic", "Information"),
        15.18,
        1.72,
        1.90,
        1.72,
        "#EDEDED",
        "#7F7F7F",
    ),
]

ARROWS: List[Arrow] = [
    Arrow("input", "frontend"),
    Arrow("frontend", "temporal"),
    Arrow("temporal", "suppression"),
    Arrow("suppression", "backend"),
    Arrow("backend", "map"),
    Arrow("map", "outputs"),
    Arrow("input", "yolo", "#ED7D31", True),
    Arrow("yolo", "semantic", "#ED7D31", True),
    Arrow("semantic", "temporal", "#ED7D31", True),
    Arrow("temporal", "temporal", "#70AD47", True, "Temporal Consistency"),
]


def box_center(box: Box) -> Tuple[float, float]:
    return box.x + box.w / 2, box.y + box.h / 2


def port(box: Box, side: str) -> Tuple[float, float]:
    if side == "left":
        return box.x, box.y + box.h / 2
    if side == "right":
        return box.x + box.w, box.y + box.h / 2
    if side == "top":
        return box.x + box.w / 2, box.y + box.h
    if side == "bottom":
        return box.x + box.w / 2, box.y
    raise ValueError(side)


BOX_BY_KEY = {b.key: b for b in BOXES}


def arrow_points(arrow: Arrow) -> Tuple[Tuple[float, float], Tuple[float, float]]:
    if arrow.start == arrow.end:
        b = BOX_BY_KEY[arrow.start]
        return (b.x + b.w * 0.72, b.y + b.h + 0.08), (b.x + b.w * 0.42, b.y + b.h + 0.08)
    a = BOX_BY_KEY[arrow.start]
    b = BOX_BY_KEY[arrow.end]
    ax, ay = box_center(a)
    bx, by = box_center(b)
    dx = bx - ax
    dy = by - ay
    if abs(dx) >= abs(dy):
        start = port(a, "right" if dx > 0 else "left")
        end = port(b, "left" if dx > 0 else "right")
    else:
        start = port(a, "top" if dy > 0 else "bottom")
        end = port(b, "bottom" if dy > 0 else "top")
    return start, end


def text_lines_for_svg(box: Box) -> str:
    cx = (box.x + box.w / 2) * PX_PER_IN
    y = (PAGE_H - box.y - 0.24) * PX_PER_IN
    out = []
    for title_line in display_title(box.title):
        out.append(
            f'<text x="{cx:.1f}" y="{y:.1f}" text-anchor="middle" font-family="Times New Roman, Liberation Serif, serif" font-size="12" font-weight="700" fill="#111111">{esc(title_line)}</text>'
        )
        y += 17
    y += 4
    for line in box.lines:
        out.append(
            f'<text x="{cx:.1f}" y="{y:.1f}" text-anchor="middle" font-family="Times New Roman, Liberation Serif, serif" font-size="9.5" fill="#111111">{esc(line)}</text>'
        )
        y += 17
    return "\n".join(out)


def generate_svg() -> None:
    width = PAGE_W * PX_PER_IN
    height = PAGE_H * PX_PER_IN
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.0f}" height="{height:.0f}" viewBox="0 0 {width:.0f} {height:.0f}">',
        '<defs>',
        '<marker id="arrowBlack" markerWidth="9" markerHeight="7" refX="8" refY="3.5" orient="auto"><polygon points="0 0, 9 3.5, 0 7" fill="#222222"/></marker>',
        '<marker id="arrowOrange" markerWidth="9" markerHeight="7" refX="8" refY="3.5" orient="auto"><polygon points="0 0, 9 3.5, 0 7" fill="#ED7D31"/></marker>',
        '<marker id="arrowGreen" markerWidth="9" markerHeight="7" refX="8" refY="3.5" orient="auto"><polygon points="0 0, 9 3.5, 0 7" fill="#70AD47"/></marker>',
        "</defs>",
        '<rect x="0" y="0" width="100%" height="100%" fill="#ffffff"/>',
    ]
    for arrow in ARROWS:
        if arrow.start == arrow.end:
            b = BOX_BY_KEY[arrow.start]
            x1 = (b.x + b.w * 0.78) * PX_PER_IN
            y1 = (PAGE_H - b.y - b.h - 0.10) * PX_PER_IN
            x2 = (b.x + b.w * 0.42) * PX_PER_IN
            y2 = y1
            marker = "arrowGreen"
            parts.append(
                f'<path d="M{x1:.1f},{y1:.1f} C{x1 + 45:.1f},{y1 - 42:.1f} {x2 - 45:.1f},{y2 - 42:.1f} {x2:.1f},{y2:.1f}" fill="none" stroke="{arrow.color}" stroke-width="1.4" stroke-dasharray="6 4" marker-end="url(#{marker})"/>'
            )
            parts.append(
                f'<text x="{(b.x + b.w / 2) * PX_PER_IN:.1f}" y="{y1 - 46:.1f}" text-anchor="middle" font-family="Times New Roman, Liberation Serif, serif" font-size="9" fill="{arrow.color}">{esc(arrow.label)}</text>'
            )
            continue
        (x1, y1), (x2, y2) = arrow_points(arrow)
        sx, sy = x1 * PX_PER_IN, (PAGE_H - y1) * PX_PER_IN
        ex, ey = x2 * PX_PER_IN, (PAGE_H - y2) * PX_PER_IN
        marker = "arrowBlack" if arrow.color == "#222222" else "arrowOrange"
        dash = ' stroke-dasharray="6 4"' if arrow.dashed else ""
        parts.append(
            f'<line x1="{sx:.1f}" y1="{sy:.1f}" x2="{ex:.1f}" y2="{ey:.1f}" stroke="{arrow.color}" stroke-width="1.4"{dash} marker-end="url(#{marker})"/>'
        )
    for box in BOXES:
        x = box.x * PX_PER_IN
        y = (PAGE_H - box.y - box.h) * PX_PER_IN
        w = box.w * PX_PER_IN
        h = box.h * PX_PER_IN
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="4" ry="4" fill="{box.fill}" stroke="{box.line}" stroke-width="{box.stroke}"/>'
        )
        parts.append(text_lines_for_svg(box))
    parts.append("</svg>")
    SVG_PATH.write_text("\n".join(parts), encoding="utf-8")


def visio_cell(name: str, value: object, unit: str = "") -> str:
    u = f' U="{unit}"' if unit else ""
    return f'<Cell N="{name}" V="{value}"{u}/>'


def visio_text(box: Box) -> str:
    lines = [*display_title(box.title), *box.lines]
    return "<Text>" + "&#10;".join(esc(line) for line in lines) + "</Text>"


def rect_shape(shape_id: int, box: Box) -> str:
    pinx = box.x + box.w / 2
    piny = box.y + box.h / 2
    title_size = "12 pt"
    body_size = "9.5 pt"
    return f'''<Shape ID="{shape_id}" NameU="{esc(box.key)}" Name="{esc(box.title)}" Type="Shape">
  <XForm>
    {visio_cell("PinX", pinx, "IN")}
    {visio_cell("PinY", piny, "IN")}
    {visio_cell("Width", box.w, "IN")}
    {visio_cell("Height", box.h, "IN")}
    {visio_cell("LocPinX", box.w / 2, "IN")}
    {visio_cell("LocPinY", box.h / 2, "IN")}
  </XForm>
  {visio_cell("FillForegnd", rgb_to_visio(box.fill))}
  {visio_cell("LineColor", rgb_to_visio(box.line))}
  {visio_cell("LineWeight", box.stroke / 72, "IN")}
  <Section N="Character">
    <Row IX="0">{visio_cell("Font", 0)}{visio_cell("Size", title_size)}{visio_cell("Style", 1)}</Row>
    <Row IX="1">{visio_cell("Font", 0)}{visio_cell("Size", body_size)}{visio_cell("Style", 0)}</Row>
  </Section>
  <Section N="Paragraph"><Row IX="0">{visio_cell("HorzAlign", 1)}</Row></Section>
  <Section N="Geometry" IX="0">
    <Cell N="NoFill" V="0"/><Cell N="NoLine" V="0"/>
    <Row T="MoveTo" IX="1">{visio_cell("X", 0, "IN")}{visio_cell("Y", 0, "IN")}</Row>
    <Row T="LineTo" IX="2">{visio_cell("X", box.w, "IN")}{visio_cell("Y", 0, "IN")}</Row>
    <Row T="LineTo" IX="3">{visio_cell("X", box.w, "IN")}{visio_cell("Y", box.h, "IN")}</Row>
    <Row T="LineTo" IX="4">{visio_cell("X", 0, "IN")}{visio_cell("Y", box.h, "IN")}</Row>
    <Row T="LineTo" IX="5">{visio_cell("X", 0, "IN")}{visio_cell("Y", 0, "IN")}</Row>
  </Section>
  {visio_text(box)}
</Shape>'''


def line_shape(shape_id: int, arrow: Arrow) -> str:
    if arrow.start == arrow.end:
        b = BOX_BY_KEY[arrow.start]
        x1 = b.x + b.w * 0.78
        y1 = b.y + b.h + 0.10
        x2 = b.x + b.w * 0.42
        y2 = b.y + b.h + 0.10
    else:
        (x1, y1), (x2, y2) = arrow_points(arrow)
    pinx = (x1 + x2) / 2
    piny = (y1 + y2) / 2
    width = max(abs(x2 - x1), 0.01)
    height = max(abs(y2 - y1), 0.01)
    dx = x2 - x1
    dy = y2 - y1
    angle = math.atan2(dy, dx)
    line_pattern = 2 if arrow.dashed else 1
    end_arrow = 4
    return f'''<Shape ID="{shape_id}" NameU="Arrow{shape_id}" Type="Shape">
  <XForm>
    {visio_cell("PinX", pinx, "IN")}
    {visio_cell("PinY", piny, "IN")}
    {visio_cell("Width", max(math.hypot(dx, dy), 0.01), "IN")}
    {visio_cell("Height", 0, "IN")}
    {visio_cell("LocPinX", max(math.hypot(dx, dy), 0.01) / 2, "IN")}
    {visio_cell("LocPinY", 0, "IN")}
    {visio_cell("Angle", angle, "RAD")}
  </XForm>
  {visio_cell("LineColor", rgb_to_visio(arrow.color))}
  {visio_cell("LineWeight", 1.2 / 72, "IN")}
  {visio_cell("LinePattern", line_pattern)}
  {visio_cell("EndArrow", end_arrow)}
  <Section N="Geometry" IX="0">
    <Cell N="NoFill" V="1"/><Cell N="NoLine" V="0"/>
    <Row T="MoveTo" IX="1">{visio_cell("X", 0, "IN")}{visio_cell("Y", 0, "IN")}</Row>
    <Row T="LineTo" IX="2">{visio_cell("X", max(math.hypot(dx, dy), 0.01), "IN")}{visio_cell("Y", 0, "IN")}</Row>
  </Section>
</Shape>'''


def text_shape(shape_id: int, text: str, x: float, y: float, w: float, h: float, color: str) -> str:
    return f'''<Shape ID="{shape_id}" NameU="Label{shape_id}" Type="Shape">
  <XForm>
    {visio_cell("PinX", x, "IN")}
    {visio_cell("PinY", y, "IN")}
    {visio_cell("Width", w, "IN")}
    {visio_cell("Height", h, "IN")}
    {visio_cell("LocPinX", w / 2, "IN")}
    {visio_cell("LocPinY", h / 2, "IN")}
  </XForm>
  {visio_cell("FillPattern", 0)}
  {visio_cell("LinePattern", 0)}
  {visio_cell("Char.Color", rgb_to_visio(color))}
  <Section N="Character"><Row IX="0">{visio_cell("Font", 0)}{visio_cell("Size", "9 pt")}</Row></Section>
  <Section N="Paragraph"><Row IX="0">{visio_cell("HorzAlign", 1)}</Row></Section>
  <Text>{esc(text)}</Text>
</Shape>'''


def visio_page_xml() -> str:
    shapes = []
    shape_id = 1
    for arrow in ARROWS:
        shapes.append(line_shape(shape_id, arrow))
        shape_id += 1
    for box in BOXES:
        shapes.append(rect_shape(shape_id, box))
        shape_id += 1
    temporal = BOX_BY_KEY["temporal"]
    shapes.append(
        text_shape(
            shape_id,
            "Temporal Consistency",
            temporal.x + temporal.w / 2,
            temporal.y + temporal.h + 0.52,
            1.75,
            0.22,
            "#70AD47",
        )
    )
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<PageContents xmlns="{NS}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <Shapes>
    {"".join(shapes)}
  </Shapes>
</PageContents>'''


def write_vsdx() -> None:
    content_types = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/visio/document.xml" ContentType="application/vnd.ms-visio.drawing.main+xml"/>
  <Override PartName="/visio/pages/pages.xml" ContentType="application/vnd.ms-visio.pages+xml"/>
  <Override PartName="/visio/pages/page1.xml" ContentType="application/vnd.ms-visio.page+xml"/>
</Types>'''
    root_rels = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="{REL_NS}">
  <Relationship Id="rId1" Type="http://schemas.microsoft.com/visio/2010/relationships/document" Target="visio/document.xml"/>
</Relationships>'''
    document_xml = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<VisioDocument xmlns="{NS}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <DocumentSettings/>
  <Colors/>
  <FaceNames>
    <FaceName ID="0" NameU="Times New Roman" UnicodeRanges="0" CharSets="0" Panos="02020603050405020304" Flags="325"/>
  </FaceNames>
  <StyleSheets/>
  <DocumentSheet>
    <Cell N="PageWidth" V="{PAGE_W}" U="IN"/>
    <Cell N="PageHeight" V="{PAGE_H}" U="IN"/>
  </DocumentSheet>
  <Pages>
    <Page ID="0" NameU="Page-1" Name="Page-1" ViewScale="1.0" ViewCenterX="{PAGE_W / 2}" ViewCenterY="{PAGE_H / 2}" r:id="rId1">
      <PageSheet>
        <Cell N="PageWidth" V="{PAGE_W}" U="IN"/>
        <Cell N="PageHeight" V="{PAGE_H}" U="IN"/>
      </PageSheet>
    </Page>
  </Pages>
</VisioDocument>'''
    document_rels = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="{REL_NS}">
  <Relationship Id="rId1" Type="http://schemas.microsoft.com/visio/2010/relationships/pages" Target="pages/pages.xml"/>
</Relationships>'''
    pages_xml = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<PagesContents xmlns="{NS}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <PageContents ID="0" NameU="Page-1" Name="Page-1" r:id="rId1"/>
</PagesContents>'''
    pages_rels = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="{REL_NS}">
  <Relationship Id="rId1" Type="http://schemas.microsoft.com/visio/2010/relationships/page" Target="page1.xml"/>
</Relationships>'''
    with zipfile.ZipFile(VSDX_PATH, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types)
        zf.writestr("_rels/.rels", root_rels)
        zf.writestr("visio/document.xml", document_xml)
        zf.writestr("visio/_rels/document.xml.rels", document_rels)
        zf.writestr("visio/pages/pages.xml", pages_xml)
        zf.writestr("visio/pages/_rels/pages.xml.rels", pages_rels)
        zf.writestr("visio/pages/page1.xml", visio_page_xml())


def export_previews() -> None:
    cache = ROOT / ".matplotlib_cache"
    cache.mkdir(parents=True, exist_ok=True)
    os.environ["MPLCONFIGDIR"] = str(cache)
    import matplotlib.pyplot as plt
    from matplotlib import font_manager
    from matplotlib.patches import FancyArrowPatch, Rectangle

    available_fonts = {f.name for f in font_manager.fontManager.ttflist}
    font = "Times New Roman" if "Times New Roman" in available_fonts else "Liberation Serif"
    fig, ax = plt.subplots(figsize=(PAGE_W, PAGE_H))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    ax.set_xlim(0, PAGE_W)
    ax.set_ylim(0, PAGE_H)
    ax.axis("off")

    def add_arrow(arrow: Arrow) -> None:
        if arrow.start == arrow.end:
            b = BOX_BY_KEY[arrow.start]
            start = (b.x + b.w * 0.78, b.y + b.h + 0.10)
            end = (b.x + b.w * 0.42, b.y + b.h + 0.10)
            patch = FancyArrowPatch(
                start,
                end,
                connectionstyle="arc3,rad=0.45",
                arrowstyle="-|>",
                mutation_scale=11,
                linewidth=1.4,
                linestyle=(0, (4, 3)),
                color=arrow.color,
            )
            ax.add_patch(patch)
            ax.text(
                b.x + b.w / 2,
                b.y + b.h + 0.52,
                arrow.label,
                ha="center",
                va="center",
                fontsize=9,
                color=arrow.color,
                fontfamily=font,
            )
            return
        start, end = arrow_points(arrow)
        patch = FancyArrowPatch(
            start,
            end,
            arrowstyle="-|>",
            mutation_scale=11,
            linewidth=1.4,
            linestyle=(0, (4, 3)) if arrow.dashed else "-",
            color=arrow.color,
            shrinkA=2,
            shrinkB=2,
        )
        ax.add_patch(patch)

    for arrow in ARROWS:
        add_arrow(arrow)

    for box in BOXES:
        rect = Rectangle((box.x, box.y), box.w, box.h, facecolor=box.fill, edgecolor=box.line, linewidth=box.stroke)
        ax.add_patch(rect)
        ax.text(
            box.x + box.w / 2,
            box.y + box.h - 0.22,
            "\n".join(display_title(box.title)),
            ha="center",
            va="top",
            fontsize=12,
            fontweight="bold",
            fontfamily=font,
            color="#111111",
            linespacing=0.9,
        )
        y = box.y + box.h - (0.48 if len(display_title(box.title)) == 1 else 0.72)
        for line in box.lines:
            ax.text(
                box.x + box.w / 2,
                y,
                line,
                ha="center",
                va="top",
                fontsize=9.5,
                fontfamily=font,
                color="#111111",
            )
            y -= 0.25
    fig.savefig(PDF_PATH, bbox_inches="tight", pad_inches=0.02)
    fig.savefig(PNG_PATH, dpi=600, bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)


def write_notes() -> None:
    NOTES_PATH.write_text(
        """# Fig.1 System Framework Generation Notes

## Files

- `Fig1_System_Framework.vsdx`: editable Visio source generated from Visio XML shapes.
- `Fig1_System_Framework.pdf`: vector preview exported from SVG.
- `Fig1_System_Framework.png`: 600 dpi raster preview exported from SVG.

## Method Correspondence

- RGB-D Input corresponds to image and depth input.
- ORB-SLAM2 RGB-D Frontend contains only Feature Extraction, Feature Matching, and Pose Tracking.
- YOLOv5 Semantic Detection contains Object Category, Confidence, and Semantic Mask.
- Semantic Observation feeds semantic evidence into the temporal model.
- Temporal Dynamic Evidence Model is visually highlighted as the core contribution and contains Dynamic Evidence Score, λ Decay, γ Increment, θ Threshold, and Dynamic State Decision.
- Dynamic Point Suppression contains Dynamic Point Removal, Feature Filtering, Matching Constraint, and Tracking Constraint.
- Backend Optimization contains Local Mapping, Loop Closing, and Graph Optimization.
- Object-level Semantic Map contains Object Category, 3D Position, Object Observation Association, and Dynamic State.
- Final Outputs contain Camera Trajectory, Static/Dynamic Map Points, and Object-level Semantic Information.

## Compliance Check

- Editable VSDX source is retained.
- No raster screenshot is embedded as the Visio content.
- The figure does not include Kalman Filter, Optical Flow, Transformer, Object ID Tracking, ID Association, Re-identification, or Dynamic Object Tracking.
- `ID Association` was deliberately not used; the map module uses `Object Observation Association`.
- White background, no gradient, no shadow.
- Text is in English and uses Times New Roman in the Visio font declaration.
""",
        encoding="utf-8",
    )


def main() -> None:
    generate_svg()
    write_vsdx()
    export_previews()
    write_notes()
    print(VSDX_PATH)
    print(PDF_PATH)
    print(PNG_PATH)
    print(NOTES_PATH)


if __name__ == "__main__":
    main()
