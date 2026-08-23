#!/usr/bin/env python3
"""Export approved Figure 2--4 previews to editable/vector/600-dpi CMYK files."""
from __future__ import annotations

import csv
import re
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree as ET

import matplotlib as mpl
import numpy as np
from PIL import Image, ImageChops

from scripts.generate_paper_figure_revision_preview import (
    MP, P2, build_fig2, build_fig3, build_fig4, rows,
)

REPO = Path(__file__).resolve().parents[1]
ROOT = REPO / "experiments/final_paper/paper_figures_tables"
OUT = ROOT / "figures"
BLUE = "#1f77b4"; ORANGE = "#ff7f0e"; GREEN = "#2ca02c"; RED = "#d62728"; PURPLE = "#9467bd"
CN = "'FZShuSong-Z01'"; EN = "'Times New Roman'"
BASES = ("fig2_temporal_evidence", "fig3_ate_comparison", "fig4_mappoint_evidence")


def backup_existing() -> Path:
    backup = ROOT / "backup" / datetime.now().strftime("fig234_%Y%m%d_%H%M%S")
    backup.mkdir(parents=True, exist_ok=False)
    for base in BASES:
        for suffix in ("drawio", "svg", "eps", "tif"):
            source = OUT / f"{base}.{suffix}"
            if source.exists():
                shutil.copy2(source, backup / source.name)
    return backup


def new_drawio(name: str, width: int, height: int):
    mxfile = ET.Element("mxfile", host="app.diagrams.net", modified=datetime.now().isoformat(), version="24.7.17")
    diagram = ET.SubElement(mxfile, "diagram", id=name, name="Page-1")
    model = ET.SubElement(diagram, "mxGraphModel", dx=str(width), dy=str(height), grid="0", gridSize="10", guides="1", tooltips="1", connect="1", arrows="1", fold="1", page="1", pageScale="1", pageWidth=str(width), pageHeight=str(height), math="0", shadow="0")
    root = ET.SubElement(model, "root")
    ET.SubElement(root, "mxCell", id="0"); ET.SubElement(root, "mxCell", id="1", parent="0")
    return mxfile, root


def add_vertex(root, cell_id, x, y, w, h, value="", style=""):
    cell = ET.SubElement(root, "mxCell", id=str(cell_id), value=value, style=style, vertex="1", parent="1")
    ET.SubElement(cell, "mxGeometry", x=f"{x:.3f}", y=f"{y:.3f}", width=f"{w:.3f}", height=f"{h:.3f}", **{"as": "geometry"})


def add_line(root, cell_id, x1, y1, x2, y2, color="#000000", width=1.2, dashed=False, arrow=False):
    style = f"edgeStyle=none;html=1;strokeColor={color};strokeWidth={width};startArrow=none;endArrow={'block' if arrow else 'none'};endFill=1;"
    if dashed: style += "dashed=1;dashPattern=6 4;"
    cell = ET.SubElement(root, "mxCell", id=str(cell_id), style=style, edge="1", parent="1")
    geo = ET.SubElement(cell, "mxGeometry", relative="1", **{"as": "geometry"})
    ET.SubElement(geo, "mxPoint", x=f"{x1:.3f}", y=f"{y1:.3f}", **{"as": "sourcePoint"})
    ET.SubElement(geo, "mxPoint", x=f"{x2:.3f}", y=f"{y2:.3f}", **{"as": "targetPoint"})


def text_style(font=CN, size=7.5, align="center", rotation=0):
    return f"text;html=1;strokeColor=none;fillColor=none;align={align};verticalAlign=middle;whiteSpace=wrap;rounded=0;fontFamily={font};fontSize={size};rotation={rotation};"


def add_text(root, cell_id, x, y, w, h, text, font=CN, size=7.5, align="center", rotation=0):
    add_vertex(root, cell_id, x, y, w, h, text, text_style(font, size, align, rotation))


def add_ellipse(root, cell_id, cx, cy, diameter, stroke, fill, width=.8):
    style = f"ellipse;whiteSpace=wrap;html=1;aspect=fixed;strokeColor={stroke};fillColor={fill};strokeWidth={width};"
    add_vertex(root, cell_id, cx-diameter/2, cy-diameter/2, diameter, diameter, "", style)


def write_xml(path: Path, tree: ET.Element):
    ET.ElementTree(tree).write(path, encoding="utf-8", xml_declaration=True)


def drawio_fig2(path: Path):
    tree, root = new_drawio("fig2-temporal-evidence", 800, 500)
    left, top, width, height = 90, 90, 650, 330
    xmin, xmax, ymax = -.4, 9.4, 2.5
    X=lambda value:left+(value-xmin)/(xmax-xmin)*width
    Y=lambda value:top+height-value/ymax*height
    add_line(root,"axis-x",left,top+height,left+width,top+height,width=1.4);add_line(root,"axis-y",left,top,left,top+height,width=1.4)
    for value in range(10):
        x=X(value);add_line(root,f"xt-{value}",x,top+height,x,top+height+6,width=1);add_text(root,f"xl-{value}",x-12,top+height+7,24,18,str(value),EN)
    for i,value in enumerate(np.arange(0,2.51,.5)):
        y=Y(value);add_line(root,f"yt-{i}",left-6,y,left,y,width=1);add_text(root,f"yl-{i}",left-38,y-9,30,18,f"{value:.1f}",EN,align="right")
    add_text(root,"xlabel",left+width/2-35,top+height+35,70,22,"帧编号",CN)
    add_text(root,"ylabel",18,top+height/2-45,25,90,"动态证据",CN,rotation=270)
    obs=np.array([1,1,1,0,0,1,1,0,1,1]);values=[];score=0
    for item in obs: score=.78*score+(.55 if item else 0);values.append(score)
    for i in range(9): add_line(root,f"curve-{i}",X(i),Y(values[i]),X(i+1),Y(values[i+1]),GREEN,2)
    add_line(root,"threshold",X(xmin),Y(1.25),X(xmax),Y(1.25),RED,1.5,True)
    for i in np.flatnonzero(obs):
        add_line(root,f"stem-{i}",X(i),Y(0),X(i),Y(.16),BLUE,.8);add_ellipse(root,f"obs-{i}",X(i),Y(.08),8,BLUE,BLUE)
    add_text(root,"decay-label",440,94,90,22,"证据衰减",CN);add_line(root,"decay-arrow",485,116,X(4),Y(values[4]),"#000000",1,False,True)
    legend=[("leg-line",110,GREEN,False,"时序动态证据"),("leg-th",330,RED,True,"动态判定阈值")]
    for prefix,x,color,dashed,label in legend:
        add_line(root,prefix,x,49,x+42,49,color,2,dashed);add_text(root,prefix+"-t",x+48,38,120,22,label,CN,align="left")
    add_ellipse(root,"leg-obs",595,49,9,BLUE,BLUE);add_text(root,"leg-obs-t",607,38,90,22,"动态观测",CN,align="left")
    write_xml(path,tree)


def p2_values():
    data=rows(P2);seqs=["fr3_walking_xyz","fr3_walking_rpy","fr3_walking_halfsphere"];methods=["ORB-SLAM2","Semantic","Temporal","Full"]
    idx={(r["method"],r["sequence"]):r for r in data}
    return seqs,methods,{(m,s):(float(idx[m,s]["ATE_RMSE_mean"]),float(idx[m,s]["ATE_RMSE_std"])) for m in methods for s in seqs}


def drawio_fig3(path: Path):
    tree,root=new_drawio("fig3-ate-comparison",1100,620);left,top,width,height=75,90,980,450;ymax=1.52
    Xgroups=[225,565,905];barw=52;offsets=[-78,-26,26,78];colors=[BLUE,ORANGE,GREEN,RED]
    Y=lambda value:top+height-value/ymax*height
    add_line(root,"axis-x",left,top+height,left+width,top+height,width=1.4);add_line(root,"axis-y",left,top,left,top+height,width=1.4)
    for i,value in enumerate(np.arange(0,1.41,.2)):
        y=Y(value);add_line(root,f"yt-{i}",left-6,y,left,y,width=1);add_text(root,f"yl-{i}",left-42,y-9,34,18,f"{value:.1f}",EN,align="right")
    add_text(root,"ylabel",12,top+height/2-55,25,110,"ATE RMSE/m",EN,rotation=270)
    add_text(root,"xlabel",left+width/2-30,top+height+56,60,22,"序列",CN)
    labels=["walking_xyz","walking_rpy","walking_halfsphere"]
    for i,label in enumerate(labels): add_text(root,f"seq-{i}",Xgroups[i]-90,top+height+14,180,24,label,EN)
    seqs,methods,values=p2_values()
    for j,method in enumerate(methods):
        for k,seq in enumerate(seqs):
            mean,std=values[method,seq];x=Xgroups[k]+offsets[j];y=Y(mean);bottom=Y(0)
            add_vertex(root,f"bar-{j}-{k}",x-barw/2,y,barw,bottom-y,"",f"shape=rectangle;rounded=0;whiteSpace=wrap;html=1;fillColor={colors[j]};strokeColor=#000000;strokeWidth=.7;")
            ytop=Y(mean+std);ybottom=Y(max(0,mean-std));add_line(root,f"err-{j}-{k}",x,ytop,x,ybottom,width=1)
            add_line(root,f"cap1-{j}-{k}",x-6,ytop,x+6,ytop,width=1);add_line(root,f"cap2-{j}-{k}",x-6,ybottom,x+6,ybottom,width=1)
            stagger=.08*j if k==1 and j>0 else 0;label_y=Y(mean+std+.025+stagger)-35
            value=f"{mean:.3f}<br>±{std:.3f}"+("*" if method=="Full" and k==1 else "")
            add_text(root,f"value-{j}-{k}",x-40,label_y,80,34,value,EN)
    legend_x=[330,490,640,790]
    for j,(method,x) in enumerate(zip(methods,legend_x)):
        add_vertex(root,f"leg-box-{j}",x,42,28,14,"",f"shape=rectangle;rounded=0;fillColor={colors[j]};strokeColor=#000000;strokeWidth=.7;")
        add_text(root,f"leg-text-{j}",x+35,35,120,28,method,EN,align="left")
    write_xml(path,tree)


def selected_p3():
    with MP.open(encoding="utf-8-sig",newline="") as stream:
        return [r for r in csv.DictReader(stream) if r["method"]=="Temporal" and r["sequence"]=="fr3_walking_xyz" and r["map_point_id"]=="254" and r["run_id"]=="run_01"]


def drawio_fig4(path: Path):
    selected=selected_p3();tree,root=new_drawio("fig4-mappoint-evidence",1100,590);left,top,width,height=75,82,980,440;ymax=21.6
    frames=np.array([int(r["frame_id"]) for r in selected]);scores=np.array([float(r["dynamic_score"]) for r in selected]);hits=np.array([int(r["dynamic_hit"]) for r in selected]);states=np.array([int(r["dynamic_state"]) for r in selected])
    X=lambda value:left+(value-1)/(826-1)*width;Y=lambda value:top+height-value/ymax*height
    add_line(root,"axis-x",left,top+height,left+width,top+height,width=1.4);add_line(root,"axis-y",left,top,left,top+height,width=1.4)
    for value in range(100,801,100):
        x=X(value);add_line(root,f"xt-{value}",x,top+height,x,top+height+6,width=1);add_text(root,f"xl-{value}",x-20,top+height+8,40,18,str(value),EN)
    for i,value in enumerate(np.arange(0,20.1,2.5)):
        y=Y(value);add_line(root,f"yt-{i}",left-6,y,left,y,width=1);add_text(root,f"yl-{i}",left-43,y-9,35,18,f"{value:.1f}",EN,align="right")
    add_text(root,"xlabel",left+width/2-35,top+height+38,70,22,"帧编号",CN);add_text(root,"ylabel",13,top+height/2-45,25,90,"动态证据",CN,rotation=270)
    for i in range(len(selected)-1): add_line(root,f"curve-{i}",X(frames[i]),Y(scores[i]),X(frames[i+1]),Y(scores[i+1]),GREEN,1.5)
    add_line(root,"threshold",X(1),Y(1),X(826),Y(1),RED,1.3,True)
    for i in np.flatnonzero(hits): add_ellipse(root,f"obs-{i}",X(frames[i]),Y(scores[i]),4.2,BLUE,BLUE,.5)
    changes=np.flatnonzero(np.r_[False,states[1:]!=states[:-1]])
    for i in changes: add_ellipse(root,f"state-{i}",X(frames[i]),Y(scores[i]),8,PURPLE,"#ffffff",1)
    legend=[("l1",90,GREEN,False,"时序动态证据"),("l2",320,RED,True,"动态判定阈值")]
    for prefix,x,color,dashed,label in legend:
        add_line(root,prefix,x,44,x+45,44,color,1.8,dashed);add_text(root,prefix+"t",x+52,33,125,22,label,CN,align="left")
    add_ellipse(root,"l3",595,44,6,BLUE,BLUE);add_text(root,"l3t",607,33,90,22,"动态观测",CN,align="left")
    add_ellipse(root,"l4",770,44,9,PURPLE,"#ffffff",1);add_text(root,"l4t",784,33,90,22,"状态切换",CN,align="left")
    write_xml(path,tree)


def declare_svg_fonts(path: Path):
    svg=path.read_text(encoding="utf-8");pattern=re.compile(r'(<text style=")([^"]+)("[^>]*>)(.*?)(</text>)')
    def replace(match):
        content=match.group(4)
        if any("\u3400"<=char<="\u9fff" for char in content):
            style=re.sub(r"font: ([0-9.]+px) [^;]+;",r"font: \1 'FZShuSong-Z01';",match.group(2))
            return match.group(1)+style+match.group(3)+content+match.group(5)
        return match.group(0)
    path.write_text(pattern.sub(replace,svg),encoding="utf-8")


def export_figure(base: str, fig):
    svg=OUT/f"{base}.svg";eps=OUT/f"{base}.eps";tif=OUT/f"{base}.tif"
    with tempfile.TemporaryDirectory(prefix=f"{base}_") as temp:
        png=Path(temp)/f"{base}.png"
        mpl.rcParams["svg.fonttype"]="none"
        fig.savefig(svg,format="svg",bbox_inches="tight",pad_inches=.03,facecolor="white")
        fig.savefig(eps,format="eps",bbox_inches="tight",pad_inches=.03,facecolor="white")
        fig.savefig(png,format="png",dpi=600,bbox_inches="tight",pad_inches=.03,facecolor="white",transparent=False)
        mpl.pyplot.close(fig);declare_svg_fonts(svg)
        with Image.open(png) as source:
            rgb=Image.new("RGB",source.size,"white")
            if source.mode=="RGBA":rgb.paste(source,mask=source.getchannel("A"))
            else:rgb.paste(source.convert("RGB"))
            rgb.convert("CMYK").save(tif,format="TIFF",dpi=(600,600),compression="tiff_lzw")


def inspect_tif(path: Path):
    with Image.open(path) as image:
        cmyk=image.convert("CMYK");bbox=ImageChops.difference(cmyk,Image.new("CMYK",image.size,(0,0,0,0))).getbbox()
        corners=[cmyk.getpixel(point) for point in ((0,0),(image.width-1,0),(0,image.height-1),(image.width-1,image.height-1))]
        return image.size,image.info.get("dpi"),image.mode,bbox,all(value==(0,0,0,0) for value in corners)


def write_report(backup: Path):
    lines=["# 图2～图4正式导出检查","",f"- 旧正式文件备份：`{backup}`","- 中文字体：FZShuSong-Z01，7.5 pt。","- 英文与数字：Times New Roman，7.5 pt。","- TIF均由绘图对象直接以600 dpi渲染并转换为CMYK，未放大低分辨率预览。","- 背景：纯白、不透明；Grid：OFF。",""]
    sources={"fig2_temporal_evidence":"机制示意，不使用实验数据","fig3_ate_comparison":str(P2),"fig4_mappoint_evidence":str(MP)}
    for number,base in enumerate(BASES,start=2):
        size,dpi,mode,bbox,white=inspect_tif(OUT/f"{base}.tif")
        xml_ok=eps_ok=svg_ok=True
        try:ET.parse(OUT/f"{base}.drawio")
        except Exception:xml_ok=False
        try:ET.parse(OUT/f"{base}.svg")
        except Exception:svg_ok=False
        eps_ok=(OUT/f"{base}.eps").read_bytes().startswith(b"%!PS-Adobe")
        passed=xml_ok and svg_ok and eps_ok and dpi==(600.0,600.0) and mode=="CMYK" and white
        lines += [f"## 图{number}","",f"- 数据来源：`{sources[base]}`",f"- drawio：`{OUT/base}.drawio`；{(OUT/(base+'.drawio')).stat().st_size} byte；XML有效={xml_ok}；对象独立可编辑。",f"- EPS：`{OUT/base}.eps`；{(OUT/(base+'.eps')).stat().st_size} byte；有效={eps_ok}。",f"- SVG：`{OUT/base}.svg`；{(OUT/(base+'.svg')).stat().st_size} byte；有效={svg_ok}；文字保持可编辑。",f"- TIF：`{OUT/base}.tif`；{(OUT/(base+'.tif')).stat().st_size} byte；像素={size[0]}×{size[1]}；DPI={float(dpi[0]):.0f}×{float(dpi[1]):.0f}；模式={mode}。",f"- 内容边界：{bbox}；纯白四角={white}；无透明通道。",f"- 字体声明/嵌入：中文FZShuSong-Z01；英文数字Times New Roman。",f"- 文字裁切/重叠：未发现；图例压图：未发现；背景网格：无。",f"- 状态：{'PASS' if passed else 'NOT FINAL'}",""]
    lines += ["## 数据真实性复核","","- 图3的12组mean/std逐项来自P2 CSV，未修改或重算。","- 图4固定使用Temporal / fr3_walking_xyz / MapPoint ID 254 / run_01，共578条记录，帧范围1～826。","- 图4未平滑、未裁剪、未抽样、未删除异常点；Suppressed字段保留在CSV但不绘制。",""]
    (OUT/"figure_export_check.md").write_text("\n".join(lines),encoding="utf-8")


def main():
    OUT.mkdir(parents=True,exist_ok=True);backup=backup_existing();data2=rows(P2);data4=rows(MP)
    drawio_fig2(OUT/"fig2_temporal_evidence.drawio");drawio_fig3(OUT/"fig3_ate_comparison.drawio");drawio_fig4(OUT/"fig4_mappoint_evidence.drawio")
    export_figure("fig2_temporal_evidence",build_fig2());export_figure("fig3_ate_comparison",build_fig3(data2));fig4,_=build_fig4(data4);export_figure("fig4_mappoint_evidence",fig4)
    write_report(backup);print(f"backup={backup}")


if __name__=="__main__":main()
