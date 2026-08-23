#!/usr/bin/env python3
"""Render the locked latest Figure 1 from its editable draw.io source only."""
from __future__ import annotations

import html
import re
import shutil
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree as ET

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.offsetbox import AnnotationBbox, HPacker, TextArea
from matplotlib.patches import FancyArrowPatch, Rectangle
from PIL import Image, ImageChops

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "experiments/final_paper/paper_figures_tables"
BASE = "fig1_system_framework"
SOURCE = OUT / f"{BASE}.drawio"
CN_FONT = font_manager.FontProperties(fname="/home/djn/.local/share/fonts/FZSSK.TTF")
EN_FONT = font_manager.FontProperties(family="Times New Roman")
FORMATS = ("drawio", "svg", "eps", "tif", "png")
PIXEL_SIZE = (3314, 2392)
DPI = 600


def style_dict(style: str) -> dict[str, str]:
    result = {}
    for item in style.split(";"):
        if "=" in item:
            key, value = item.split("=", 1); result[key] = value
    return result


def text_lines(value: str) -> list[str]:
    value = html.unescape(value)
    divs = re.findall(r"<div[^>]*>(.*?)</div>", value, flags=re.S)
    if not divs: divs = [value]
    return [html.unescape(re.sub(r"<[^>]+>", "", line)).strip() for line in divs]


def backup_files() -> Path:
    backup = OUT / "backup" / datetime.now().strftime("fig1_drawio_source_%Y%m%d_%H%M%S")
    backup.mkdir(parents=True, exist_ok=False)
    for suffix in FORMATS:
        source = OUT / f"{BASE}.{suffix}"
        if source.exists(): shutil.copy2(source, backup / source.name)
    return backup


def parse_source():
    tree = ET.parse(SOURCE); model = tree.find(".//mxGraphModel")
    width = float(model.get("pageWidth")); height = float(model.get("pageHeight"))
    nodes = {}; edges = []
    for cell in tree.findall(".//mxCell"):
        geo = cell.find("mxGeometry")
        if cell.get("vertex") == "1" and geo is not None:
            nodes[cell.get("id")] = {
                "x": float(geo.get("x", 0)), "y": float(geo.get("y", 0)),
                "w": float(geo.get("width", 0)), "h": float(geo.get("height", 0)),
                "lines": text_lines(cell.get("value", "")), "style": style_dict(cell.get("style", "")),
            }
        elif cell.get("edge") == "1":
            edges.append({"source": cell.get("source"), "target": cell.get("target"), "style": style_dict(cell.get("style", ""))})
    return tree, width, height, nodes, edges


def boundary_point(node, toward):
    cx=node["x"]+node["w"]/2;cy=node["y"]+node["h"]/2;dx=toward[0]-cx;dy=toward[1]-cy
    if dx == 0 and dy == 0:return cx,cy
    tx=node["w"]/(2*abs(dx)) if dx else float("inf");ty=node["h"]/(2*abs(dy)) if dy else float("inf");scale=min(tx,ty)
    return cx+dx*scale,cy+dy*scale


def mixed_parts(text: str):
    match = re.match(r"^(RGB-D|ORB-SLAM2|ORB)(.*)$", text)
    if match:return [(match.group(1),EN_FONT),(match.group(2),CN_FONT)]
    return [(text,CN_FONT)]


def add_centered_text(ax, x, y, text, size=7.5):
    parts=[TextArea(part,textprops={"fontproperties":font,"fontsize":size}) for part,font in mixed_parts(text)]
    ax.add_artist(AnnotationBbox(HPacker(children=parts,align="center",pad=0,sep=0),(x,y),frameon=False,box_alignment=(.5,.5)))


def build_from_drawio(width, height, nodes, edges):
    fig=plt.figure(figsize=(PIXEL_SIZE[0]/DPI,PIXEL_SIZE[1]/DPI),facecolor="white")
    ax=fig.add_axes([0,0,1,1]);ax.set_xlim(0,width);ax.set_ylim(height,0);ax.axis("off");ax.set_facecolor("white")
    for edge in edges:
        source=nodes[edge["source"]];target=nodes[edge["target"]];sc=(source["x"]+source["w"]/2,source["y"]+source["h"]/2);tc=(target["x"]+target["w"]/2,target["y"]+target["h"]/2)
        start=boundary_point(source,tc);end=boundary_point(target,sc)
        ax.add_patch(FancyArrowPatch(start,end,arrowstyle="-|>",mutation_scale=8,linewidth=1.4,color="#000000",shrinkA=1,shrinkB=1,zorder=1))
    for node in nodes.values():
        style=node["style"];stroke=style.get("strokeColor","#000000");line_width=float(style.get("strokeWidth","1.6"))
        ax.add_patch(Rectangle((node["x"],node["y"]),node["w"],node["h"],facecolor="#ffffff",edgecolor=stroke,linewidth=line_width,zorder=2))
        cx=node["x"]+node["w"]/2;cy=node["y"]+node["h"]/2
        if len(node["lines"])==2:
            add_centered_text(ax,cx,node["y"]+node["h"]*.34,node["lines"][0],7.5)
            add_centered_text(ax,cx,node["y"]+node["h"]*.70,node["lines"][1],7.5)
        elif node["lines"]:add_centered_text(ax,cx,cy,node["lines"][0],7.5)
    return fig


def declare_svg_fonts(path: Path):
    svg=path.read_text(encoding="utf-8");pattern=re.compile(r'(<text style=")([^"]+)("[^>]*>)(.*?)(</text>)')
    def replace(match):
        content=match.group(4);font="Times New Roman" if re.search(r"(?:RGB-D|ORB)",content) else "FZShuSong-Z01"
        style=re.sub(r"font: ([0-9.]+px) [^;]+;",rf"font: \1 '{font}';",match.group(2))
        return match.group(1)+style+match.group(3)+content+match.group(5)
    path.write_text(pattern.sub(replace,svg),encoding="utf-8")


def export(fig):
    svg=OUT/f"{BASE}.svg";eps=OUT/f"{BASE}.eps";png=OUT/f"{BASE}.png";tif=OUT/f"{BASE}.tif"
    mpl.rcParams["svg.fonttype"]="none"
    fig.savefig(svg,format="svg",dpi=DPI,facecolor="white",transparent=False)
    fig.savefig(eps,format="eps",dpi=DPI,facecolor="white",transparent=False)
    fig.savefig(png,format="png",dpi=DPI,facecolor="white",transparent=False)
    plt.close(fig);declare_svg_fonts(svg)
    with Image.open(png) as source:
        rgb=Image.new("RGB",source.size,"white")
        if source.mode=="RGBA":rgb.paste(source,mask=source.getchannel("A"))
        else:rgb.paste(source.convert("RGB"))
        rgb.save(png,dpi=(DPI,DPI),optimize=True)
        rgb.convert("CMYK").save(tif,format="TIFF",dpi=(DPI,DPI),compression="tiff_lzw")


def inspect():
    tif=OUT/f"{BASE}.tif"
    with Image.open(tif) as image:
        cmyk=image.convert("CMYK");bbox=ImageChops.difference(cmyk,Image.new("CMYK",image.size,(0,0,0,0))).getbbox();corners=[cmyk.getpixel(point) for point in ((0,0),(image.width-1,0),(0,image.height-1),(image.width-1,image.height-1))]
        return image.size,tuple(float(v) for v in image.info["dpi"]),image.mode,bbox,all(value==(0,0,0,0) for value in corners)


def main():
    _,width,height,nodes,edges=parse_source()
    required={"目标与地图点关联","目标空间位置获取","目标级语义信息管理","类别·空间位置·关联地图点","当前语义观测","时间一致性动态证据累积","动态状态判定","动态地图点约束","ORB-SLAM2跟踪与位姿估计","相机位姿"}
    actual={line for node in nodes.values() for line in node["lines"]}
    missing=required-actual
    if missing:raise RuntimeError(f"The drawio source is not the locked latest version; missing: {sorted(missing)}")
    core=[node for node in nodes.values() if node["lines"] and node["lines"][0] in {"目标级语义信息管理","时间一致性动态证据累积","动态地图点约束"}]
    core_styles={(node["style"].get("strokeColor"),node["style"].get("strokeWidth")) for node in core}
    if len(core)!=3 or len(core_styles)!=1:raise RuntimeError("Core green border styles are inconsistent in drawio source")
    backup=backup_files();export(build_from_drawio(width,height,nodes,edges));SOURCE.touch()
    size,dpi,mode,bbox,white=inspect();print(f"backup={backup}");print(f"nodes={len(nodes)} edges={len(edges)} core_style={core_styles}");print(f"tif={size} dpi={dpi} mode={mode} bbox={bbox} white={white}")


if __name__=="__main__":main()
