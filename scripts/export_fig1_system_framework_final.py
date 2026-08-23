#!/usr/bin/env python3
"""Export the approved Figure 1 without changing its visual geometry."""
from __future__ import annotations

import re
import shutil
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree as ET

import matplotlib as mpl
from PIL import Image

from scripts.generate_paper_figure_revision_preview import build_fig1


REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "experiments/final_paper/paper_figures_tables"
BASE = "fig1_system_framework"
GREEN = "#2ca02c"


def backup_existing() -> Path | None:
    targets = [OUT / f"{BASE}.{suffix}" for suffix in ("drawio", "svg", "eps", "tif", "png")]
    existing = [path for path in targets if path.exists()]
    if not existing:
        return None
    backup = OUT / "backup" / datetime.now().strftime("fig1_%Y%m%d_%H%M%S")
    backup.mkdir(parents=True, exist_ok=False)
    for path in existing:
        shutil.copy2(path, backup / path.name)
    return backup


def html_label(parts: list[tuple[str, str]], second_line: list[tuple[str, str]] | None = None) -> str:
    def line(items: list[tuple[str, str]]) -> str:
        return "".join(f'<span style="font-family: {font};">{text}</span>' for text, font in items)
    value = f"<div>{line(parts)}</div>"
    if second_line:
        value += f'<div style="font-size: 7.5pt;">{line(second_line)}</div>'
    return value


def write_drawio(path: Path) -> None:
    mxfile = ET.Element("mxfile", host="app.diagrams.net", modified=datetime.now().isoformat(), version="24.7.17")
    diagram = ET.SubElement(mxfile, "diagram", id="fig1-system-framework", name="Page-1")
    model = ET.SubElement(
        diagram,
        "mxGraphModel",
        dx="1000", dy="700", grid="0", gridSize="10", guides="1", tooltips="1",
        connect="1", arrows="1", fold="1", page="1", pageScale="1",
        pageWidth="1000", pageHeight="740", math="0", shadow="0",
    )
    root = ET.SubElement(model, "root")
    ET.SubElement(root, "mxCell", id="0")
    ET.SubElement(root, "mxCell", id="1", parent="0")

    latin = "'Times New Roman'"
    chinese = "'FZShuSong-Z01'"
    common = "shape=rectangle;rounded=0;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeWidth=1.6;fontSize=7.5;align=center;verticalAlign=middle;shadow=0;glass=0;"
    core = common + f"strokeColor={GREEN};"
    normal = common + "strokeColor=#000000;"

    nodes = {
        "rgbd": (376, 22, 248, 29, html_label([("RGB-D", latin), ("图像", chinese)]), normal),
        "orb": (153, 86, 227, 34, html_label([("ORB", latin), ("特征提取", chinese)]), normal),
        "detect": (620, 86, 227, 34, html_label([("目标检测", chinese)]), normal),
        "assoc": (153, 151, 227, 34, html_label([("目标与地图点关联", chinese)]), normal),
        "bbox": (620, 151, 227, 34, html_label([("类别与检测区域", chinese)]), normal),
        "position": (620, 216, 227, 34, html_label([("目标空间位置获取", chinese)]), normal),
        "manage": (359, 279, 282, 47,
                   html_label([("目标级语义信息管理", chinese)],
                              [("类别·空间位置·关联地图点", chinese)]), core),
        "observation": (359, 350, 282, 34, html_label([("当前语义观测", chinese)]), normal),
        "temporal": (359, 415, 282, 34, html_label([("时间一致性动态证据累积", chinese)]), core),
        "decision": (359, 480, 282, 34, html_label([("动态状态判定", chinese)]), normal),
        "constraint": (359, 545, 282, 34, html_label([("动态地图点约束", chinese)]), core),
        "tracking": (359, 610, 282, 34,
                     html_label([("ORB-SLAM2", latin), ("跟踪与位姿估计", chinese)]), normal),
        "pose": (359, 675, 282, 34, html_label([("相机位姿", chinese)]), normal),
    }
    for node_id, (x, y, w, h, value, style) in nodes.items():
        cell = ET.SubElement(root, "mxCell", id=node_id, value=value, style=style, vertex="1", parent="1")
        ET.SubElement(cell, "mxGeometry", x=str(x), y=str(y), width=str(w), height=str(h), **{"as": "geometry"})

    edge_style = "edgeStyle=none;rounded=0;html=1;strokeColor=#000000;strokeWidth=1.4;endArrow=block;endFill=1;"
    edges = [
        ("rgbd", "orb"), ("rgbd", "detect"), ("orb", "assoc"), ("detect", "bbox"),
        ("bbox", "position"), ("assoc", "manage"), ("position", "manage"),
        ("manage", "observation"), ("observation", "temporal"), ("temporal", "decision"),
        ("decision", "constraint"), ("constraint", "tracking"), ("tracking", "pose"),
    ]
    for index, (source, target) in enumerate(edges, start=1):
        cell = ET.SubElement(root, "mxCell", id=f"e{index}", style=edge_style, edge="1", parent="1", source=source, target=target)
        ET.SubElement(cell, "mxGeometry", relative="1", **{"as": "geometry"})

    ET.ElementTree(mxfile).write(path, encoding="utf-8", xml_declaration=True)


def export_visuals() -> None:
    mpl.rcParams["svg.fonttype"] = "none"
    fig = build_fig1()
    svg_path = OUT / f"{BASE}.svg"
    png_path = OUT / f"{BASE}.png"
    fig.savefig(svg_path, format="svg", bbox_inches="tight", pad_inches=0.03, facecolor="white")
    fig.savefig(OUT / f"{BASE}.eps", format="eps", bbox_inches="tight", pad_inches=0.03, facecolor="white")
    fig.savefig(png_path, format="png", dpi=600, bbox_inches="tight", pad_inches=0.03, facecolor="white", transparent=False)
    mpl.pyplot.close(fig)

    # FontProperties(fname=...) renders the requested font, while Matplotlib's
    # SVG backend records a generic family name. Keep text editable and declare
    # the installed Chinese family explicitly for every Chinese text element.
    svg = svg_path.read_text(encoding="utf-8")
    text_pattern = re.compile(r'(<text style=")([^"]+)("[^>]*>)(.*?)(</text>)')
    def declare_chinese_font(match: re.Match) -> str:
        content = match.group(4)
        if not any("\u3400" <= char <= "\u9fff" for char in content):
            return match.group(0)
        style = re.sub(r"font: ([0-9.]+px) [^;]+;", r"font: \1 'FZShuSong-Z01';", match.group(2))
        return match.group(1) + style + match.group(3) + content + match.group(5)
    svg_path.write_text(text_pattern.sub(declare_chinese_font, svg), encoding="utf-8")

    with Image.open(png_path) as source:
        rgb = Image.new("RGB", source.size, "white")
        if source.mode == "RGBA":
            rgb.paste(source, mask=source.getchannel("A"))
        else:
            rgb.paste(source.convert("RGB"))
        rgb.save(png_path, dpi=(600, 600), optimize=True)
        rgb.convert("CMYK").save(
            OUT / f"{BASE}.tif", format="TIFF", dpi=(600, 600), compression="tiff_lzw"
        )


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    backup = backup_existing()
    write_drawio(OUT / f"{BASE}.drawio")
    export_visuals()
    (OUT / "figure_captions.txt").write_text(
        "图1 系统总体框架\nFig. 1 Overall system framework\n", encoding="utf-8"
    )
    print(f"backup={backup if backup else 'none'}")


if __name__ == "__main__":
    main()
