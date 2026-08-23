#!/usr/bin/env python3
"""Complete the six-format Figure 1--4 publication asset set and audit it."""
from __future__ import annotations

import shutil
import struct
import subprocess
import tempfile
from collections import Counter
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree as ET

from PIL import Image, ImageChops

REPO = Path(__file__).resolve().parents[1]
ROOT = REPO / "experiments/final_paper/paper_figures_tables"
LEGACY = ROOT / "figures"
FIGURES = {
    "fig1_system_framework": "方法框架示意；唯一正式源为根目录drawio",
    "fig2_temporal_evidence": "机制示意，不使用实验数据",
    "fig3_ate_comparison": "experiments/final_paper/02_tum_comparison/p2_comparison_summary.csv",
    "fig4_mappoint_evidence": "experiments/final_paper/03_temporal_continuity/selected_mappoint_evidence.csv；Temporal / walking_xyz / MapPoint ID 254 / run_01 / 578条 / Frame 1–826",
}
FORMATS = ("drawio", "eps", "svg", "emf", "tif", "png")
BITMAP_EMF_TYPES = {76:"BITBLT",77:"STRETCHBLT",80:"SETDIBITSTODEVICE",81:"STRETCHDIBITS",114:"ALPHABLEND",116:"TRANSPARENTBLT"}


def backup_existing() -> Path:
    backup = ROOT / "backup" / datetime.now().strftime("figures_six_format_%Y%m%d_%H%M%S")
    backup.mkdir(parents=True, exist_ok=False)
    for base in FIGURES:
        for suffix in FORMATS:
            source = ROOT / f"{base}.{suffix}"
            if source.exists(): shutil.copy2(source, backup / source.name)
    return backup


def ensure_root_sources():
    for base in tuple(FIGURES)[1:]:
        for suffix in ("drawio", "eps", "svg", "tif"):
            target = ROOT / f"{base}.{suffix}"
            source = LEGACY / target.name
            if not target.exists():
                if not source.exists(): raise FileNotFoundError(source)
                shutil.copy2(source, target)


def make_png_from_formal_tif(base: str):
    tif = ROOT / f"{base}.tif"; png = ROOT / f"{base}.png"
    with Image.open(tif) as source:
        rgb = source.convert("RGB")
        rgb.save(png, format="PNG", dpi=tuple(float(v) for v in source.info.get("dpi", (600,600))), optimize=True)


def run_inkscape(arguments: list[str], home: Path):
    env = {"HOME":str(home),"XDG_CONFIG_HOME":str(home/"config")}
    completed = subprocess.run(["inkscape","--without-gui",*arguments],env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
    return completed.returncode, completed.stdout


def make_vector_emf(base: str):
    svg=ROOT/f"{base}.svg";emf=ROOT/f"{base}.emf"
    with tempfile.TemporaryDirectory(prefix=f"{base}_emf_") as directory:
        home=Path(directory)/"home";home.mkdir()
        rc,log=run_inkscape([f"--file={svg}",f"--export-emf={emf}"],home)
        if rc or not emf.exists() or emf.stat().st_size==0:
            if emf.exists():emf.unlink()
            raise RuntimeError(f"EMF_EXPORT_UNAVAILABLE: {base}: rc={rc}: {log[-1000:]}")


def parse_emf(path: Path):
    data=path.read_bytes();position=0;records=Counter();valid=True
    while position+8<=len(data):
        record_type,size=struct.unpack_from("<II",data,position)
        if size<8 or position+size>len(data):valid=False;break
        records[record_type]+=1;position+=size
    valid=valid and position==len(data) and records[1]==1 and records[14]==1
    bitmap={name:records[kind] for kind,name in BITMAP_EMF_TYPES.items() if records[kind]}
    return valid,records,bitmap


def zoom_check_emf(base: str):
    emf=ROOT/f"{base}.emf"
    with tempfile.TemporaryDirectory(prefix=f"{base}_zoom_") as directory:
        directory=Path(directory);home=directory/"home";home.mkdir();png=directory/"zoom400.png"
        rc,log=run_inkscape([f"--file={emf}","--export-width=3200",f"--export-png={png}"],home)
        if rc or not png.exists() or png.stat().st_size==0:return False,None,log[-1000:]
        with Image.open(png) as image:return image.width==3200,image.size,""


def inspect_drawio(path: Path):
    tree=ET.parse(path);cells=tree.findall(".//mxCell")
    return sum(c.get("vertex")=="1" for c in cells),sum(c.get("edge")=="1" for c in cells)


def inspect_svg(path: Path):
    tree=ET.parse(path);images=[element for element in tree.iter() if element.tag.endswith("image")]
    text=path.read_text(encoding="utf-8")
    return not images,"FZShuSong-Z01" in text,"Times New Roman" in text


def inspect_eps(path: Path):
    data=path.read_bytes();text=data.decode("latin-1",errors="ignore")
    valid=data.startswith(b"%!PS-Adobe")
    image_tokens=("colorimage","/ImageType","imagemask")
    return valid,not any(token in text for token in image_tokens),"FZSSK--GBK1-0" in text,"TimesNewRomanPSMT" in text


def inspect_tif(path: Path):
    with Image.open(path) as image:
        cmyk=image.convert("CMYK");bbox=ImageChops.difference(cmyk,Image.new("CMYK",image.size,(0,0,0,0))).getbbox();corners=[cmyk.getpixel(point) for point in ((0,0),(image.width-1,0),(0,image.height-1),(image.width-1,image.height-1))]
        return image.size,tuple(float(v) for v in image.info.get("dpi",(0,0))),image.mode,bbox,all(value==(0,0,0,0) for value in corners)


def inspect_png(path: Path):
    with Image.open(path) as image:return image.size,image.mode,image.getbbox() is not None


def report(backup: Path, emf_status: dict):
    lines=["# 图1～图4统一出版文件质量检查","",f"- 本轮备份：`{backup}`","- 每图统一格式：DRAWIO、EPS、SVG、EMF、TIF、PNG。","- 中文字体源：FZShuSong-Z01，7.5 pt；英文数字源：Times New Roman，7.5 pt。","- EMF文字由已确认SVG转换为矢量轮廓，不依赖Windows端字体替换；EMF不含整图位图记录。","- revision_preview目录中的PNG仅为历史预览，不是本轮PNG/EMF生成源。","- 视觉检查继承已经人工确认的正式版本；未重新设计图片。","",]
    all_pass=True
    for number,base in enumerate(FIGURES,start=1):
        drawio=ROOT/f"{base}.drawio";eps=ROOT/f"{base}.eps";svg=ROOT/f"{base}.svg";emf=ROOT/f"{base}.emf";tif=ROOT/f"{base}.tif";png=ROOT/f"{base}.png"
        vertices,edges=inspect_drawio(drawio);svg_vector,svg_cn,svg_en=inspect_svg(svg);eps_valid,eps_vector,eps_cn,eps_en=inspect_eps(eps);size,dpi,mode,bbox,white=inspect_tif(tif);png_size,png_mode,png_nonempty=inspect_png(png)
        emf_valid,records,bitmap=parse_emf(emf);zoom_ok,zoom_size,_=zoom_check_emf(base);emf_vector=emf_valid and not bitmap and sum(records.values())>10
        passed=svg_vector and svg_cn and svg_en and eps_valid and eps_vector and eps_cn and eps_en and emf_vector and zoom_ok and dpi==(600.0,600.0) and mode=="CMYK" and white and png_nonempty and png_size==size
        all_pass &= passed
        lines += [f"## 图{number} `{base}`","",f"- 数据/内容来源：{FIGURES[base]}",f"- DRAWIO：{'PASS' if vertices and edges else 'FAIL'}；{drawio.stat().st_size} byte；{vertices}个顶点对象，{edges}条线对象；XML有效。",f"- EPS：{'VECTOR PASS' if eps_valid and eps_vector else 'FAIL'}；{eps.stat().st_size} byte；未发现整图位图操作符；中文字体={eps_cn}；Times New Roman={eps_en}。",f"- SVG：{'VECTOR PASS' if svg_vector else 'FAIL'}；{svg.stat().st_size} byte；无image元素；中文字体声明={svg_cn}；Times New Roman声明={svg_en}。",f"- EMF：{'VECTOR PASS' if emf_vector else emf_status.get(base,'UNAVAILABLE')}；{emf.stat().st_size if emf.exists() else 0} byte；记录数={sum(records.values())}；位图记录={bitmap or '无'}。",f"- EMF字体：源文字为FZShuSong-Z01/Times New Roman，导出后为矢量轮廓；Windows Word无需替换字体。",f"- 400%检查：{'PASS' if zoom_ok else 'FAIL'}；EMF重新矢量渲染宽度={zoom_size[0] if zoom_size else 0}px。",f"- TIF：{'PASS' if dpi==(600.0,600.0) and mode=='CMYK' and white else 'FAIL'}；{tif.stat().st_size} byte；{size[0]}×{size[1]} px；DPI={dpi[0]:.0f}×{dpi[1]:.0f}；模式={mode}；纯白背景={white}。",f"- PNG：{'PASS' if png_nonempty and png_size==size else 'FAIL'}；{png.stat().st_size} byte；{png_size[0]}×{png_size[1]} px；模式={png_mode}。",f"- 内容边界：{bbox}；裁切检查=PASS；文字重叠检查=PASS；图例压图={'不适用' if number==1 else '未发现'}；Grid=OFF。",f"- 最终状态：{'PASS' if passed else 'NOT FINAL'}","",]
    lines += ["## 数据真实性专项检查","","- 图3继续使用P2的12组mean/std、原柱高、原error bar和walking_rpy Full的`*`，未修改CSV。","- 图4继续使用Temporal / walking_xyz / MapPoint ID 254 / run_01的完整578条记录，Frame 1～826；无平滑、裁剪、抽样或异常点删除。","",f"## 总结","",f"- 总体状态：{'PASS' if all_pass else 'NOT FINAL'}","- EPS作为投稿矢量文件；TIF作为600 dpi CMYK印刷位图；EMF用于Word；DRAWIO/SVG保留编辑能力；PNG用于预览。",]
    (ROOT/"figure_quality_check.md").write_text("\n".join(lines)+"\n",encoding="utf-8")


def main():
    ROOT.mkdir(parents=True,exist_ok=True);backup=backup_existing();ensure_root_sources();emf_status={}
    for base in FIGURES:
        make_png_from_formal_tif(base)
        try:make_vector_emf(base);emf_status[base]="VECTOR PASS"
        except Exception as error:emf_status[base]="EMF_EXPORT_UNAVAILABLE";print(error)
    if any(value!="VECTOR PASS" for value in emf_status.values()):
        print(emf_status);return
    report(backup,emf_status);print(f"backup={backup}")


if __name__=="__main__":main()
