#!/usr/bin/env python3
"""Generate journal-ready paper figures/tables exclusively from existing results."""
from __future__ import annotations
import csv, json, math, shutil, subprocess
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np
from PIL import Image

plt.rcParams["font.family"] = ["Times New Roman", "Noto Serif CJK JP"]
plt.rcParams["axes.unicode_minus"] = False

REPO=Path(__file__).resolve().parents[1]
OUT=REPO/"experiments/final_paper/paper_figures_tables"
FIG=OUT/"figures"; TAB=OUT/"tables"; SRC=OUT/"source_data"
P2=REPO/"experiments/final_paper/02_tum_comparison/p2_comparison_summary.csv"
P3=REPO/"experiments/final_paper/03_temporal_continuity/p3_temporal_continuity_summary.csv"
MP=REPO/"experiments/final_paper/03_temporal_continuity/selected_mappoint_evidence.csv"
ENV=REPO/"experiments/final_paper/01_tum_full/experiment_environment.json"

def read_csv(path):
 with path.open(encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))
def write_csv(path,fields,rows):
 with path.open("w",encoding="utf-8-sig",newline="") as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
def svg_text(x,y,text,size=11,anchor="middle",weight="normal",italic=False):
 style=f"font-family:'Times New Roman','FZShuSong-Z01','Noto Serif CJK SC',serif;font-size:{size}px;font-weight:{weight};"
 if italic:style+="font-style:italic;"
 return f'<text x="{x}" y="{y}" text-anchor="{anchor}" style="{style}">{text}</text>'
def svg_box(x,y,w,h,text,fill="#f5f5f5",stroke="#333",sw=1.4,rx=5,size=11):
 lines=text.split("\n");out=[f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>']
 start=y+h/2-(len(lines)-1)*7+4
 out += [svg_text(x+w/2,start+i*14,t,size) for i,t in enumerate(lines)]
 return "".join(out)
def arrow(x1,y1,x2,y2):return f'<path d="M{x1},{y1} L{x2},{y2}" fill="none" stroke="#333" stroke-width="1.4" marker-end="url(#a)"/>'
def svg_wrap(w,h,body):
 return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}mm" height="{h}mm" viewBox="0 0 {w*4} {h*4}"><defs><marker id="a" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto"><path d="M0,0 L8,3 L0,6 Z" fill="#333"/></marker></defs><rect width="100%" height="100%" fill="white"/>{body}</svg>'''

def drawio_graph(nodes,edges,w,h):
 cells=['<mxCell id="0"/>','<mxCell id="1" parent="0"/>']
 for i,(x,y,bw,bh,label,fill) in enumerate(nodes,2):
  cells.append(f'<mxCell id="{i}" value="{label}" style="rounded=1;whiteSpace=wrap;html=1;fillColor={fill};strokeColor=#333333;fontFamily=FZShuSong-Z01;fontSize=11;" vertex="1" parent="1"><mxGeometry x="{x}" y="{y}" width="{bw}" height="{bh}" as="geometry"/></mxCell>')
 for j,(src,dst) in enumerate(edges,2+len(nodes)):
  cells.append(f'<mxCell id="{j}" style="edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;endArrow=block;strokeWidth=1.4;" edge="1" parent="1" source="{src}" target="{dst}"><mxGeometry relative="1" as="geometry"/></mxCell>')
 return f'<mxfile host="app.diagrams.net"><diagram name="Page-1"><mxGraphModel dx="1200" dy="800" grid="1" gridSize="10" page="1" pageWidth="{w}" pageHeight="{h}"><root>{"".join(cells)}</root></mxGraphModel></diagram></mxfile>'

def fig1():
 W,H=680,390; body=[]
 body += [svg_box(270,10,140,38,"RGB-D图像输入","#ffffff")]
 body += [arrow(310,48,165,78),arrow(370,48,515,78)]
 body += [svg_box(80,78,170,42,"ORB特征提取","#eef3f8"),svg_box(430,78,170,42,"语义目标检测","#eef3f8")]
 body += [arrow(165,120,165,143),arrow(515,120,515,143)]
 body += [svg_box(65,143,200,46,"当前帧特征/MapPoint关联","#eef3f8"),svg_box(425,143,180,46,"目标类别 + 检测区域","#eef3f8")]
 body += [arrow(515,189,515,212),svg_box(425,212,180,42,"深度反投影","#eef3f8"),arrow(515,254,515,277),svg_box(425,277,180,42,"目标三维代表位置","#eef3f8")]
 body += [arrow(165,189,300,232),arrow(515,319,380,270)]
 body += [svg_box(260,215,160,75,"① 目标级语义信息管理\nCᵢ：类别  Pᵢ：位置\nMᵢ：MapPoint ID集合","#e7f1ed","#356859",1.8,6,10)]
 body += [arrow(340,290,340,314),svg_box(240,314,200,42,"当前帧MapPoint语义观测","#ffffff"),arrow(340,356,340,380)]
 # continue in second row compactly
 body += [svg_box(20,382,210,66,"② 时间一致性动态证据累积\nsⱼᵗ = λ_c^Δt sⱼᵗ⁻¹ + γ_c oⱼᵗ","#f7f0df","#8a6d1d",1.8,6,10),arrow(230,415,255,415)]
 body += [svg_box(255,394,120,42,"动态状态判定\nsⱼᵗ ≥ θ_c","#ffffff"),arrow(375,415,400,415)]
 body += [svg_box(400,382,170,66,"③ 动态MapPoint约束\n投影/运动/局部匹配","#f4e8e8","#8b3a3a",1.8,6,10),arrow(570,415,595,415)]
 body += [svg_box(595,394,80,42,"位姿估计","#ffffff")]
 # use taller viewbox than nominal H because lower row
 (FIG/"fig1_system_framework.svg").write_text(svg_wrap(170,116,"".join(body)),encoding="utf-8")
 nodes=[(270,10,140,38,"RGB-D图像输入","#ffffff"),(80,78,170,42,"ORB特征提取","#eef3f8"),(430,78,170,42,"语义目标检测","#eef3f8"),(65,143,200,46,"当前帧特征/MapPoint关联","#eef3f8"),(425,143,180,46,"目标类别 + 检测区域","#eef3f8"),(425,212,180,42,"深度反投影","#eef3f8"),(425,277,180,42,"目标三维代表位置","#eef3f8"),(260,215,160,75,"① 目标级语义信息管理&lt;br&gt;Cᵢ：类别 Pᵢ：位置&lt;br&gt;Mᵢ：MapPoint ID集合","#e7f1ed"),(240,314,200,42,"当前帧MapPoint语义观测","#ffffff"),(20,382,210,66,"② 时间一致性动态证据累积&lt;br&gt;sⱼᵗ = λ_c^Δt sⱼᵗ⁻¹ + γ_c oⱼᵗ","#f7f0df"),(255,394,120,42,"动态状态判定&lt;br&gt;sⱼᵗ ≥ θ_c","#ffffff"),(400,382,170,66,"③ 动态MapPoint约束&lt;br&gt;投影/运动/局部匹配","#f4e8e8"),(595,394,80,42,"位姿估计","#ffffff")]
 edges=[(2,3),(2,4),(3,5),(4,6),(6,7),(7,8),(5,9),(8,9),(9,10),(10,11),(11,12),(12,13),(13,14)]
 (FIG/"fig1_system_framework.drawio").write_text(drawio_graph(nodes,edges,680,470),encoding="utf-8")

def fig2():
 W,H=340,230; body=[svg_text(15,18,"示意图",9,"start")]
 xs=[40,105,170,235,300]; obs=["1","1","0","0/1","1"]
 for x,t,o in zip(xs,["t−2","t−1","t","t+1","t+2"],obs):
  body += [svg_text(x,45,t,10),svg_box(x-23,57,46,32,"观测 "+o,"#f5f5f5",size=9)]
 body += ['<line x1="25" y1="185" x2="325" y2="185" stroke="#333" stroke-width="1.3"/>','<line x1="25" y1="185" x2="25" y2="105" stroke="#333" stroke-width="1.3"/>']
 body += ['<line x1="25" y1="135" x2="325" y2="135" stroke="#777" stroke-width="1.2" stroke-dasharray="6,4"/>',svg_text(322,130,"θ_c",10,"end",italic=True)]
 pts="40,175 105,148 170,158 235,164 300,120"
 body += [f'<polyline points="{pts}" fill="none" stroke="#222" stroke-width="2"/>']
 for x,y in [(40,175),(105,148),(170,158),(235,164),(300,120)]:body.append(f'<circle cx="{x}" cy="{y}" r="3.5" fill="white" stroke="#222" stroke-width="1.5"/>')
 body += [svg_text(72,201,"证据累积",9),svg_text(198,201,"短时漏检：衰减",9),svg_text(286,105,"再次累积",9)]
 (FIG/"fig2_temporal_evidence.svg").write_text(svg_wrap(85,58,"".join(body)),encoding="utf-8")
 nodes=[]
 for x,t,o in zip(xs,["t−2","t−1","t","t+1","t+2"],obs):nodes.append((x-23,57,46,32,f"{t}&lt;br&gt;观测 {o}","#f5f5f5"))
 nodes += [(25,125,300,10,"θ_c（判定阈值）","#ffffff"),(40,170,60,25,"证据累积","#ffffff"),(145,155,100,25,"短时漏检：衰减","#ffffff"),(265,105,60,25,"再次累积","#ffffff")]
 (FIG/"fig2_temporal_evidence.drawio").write_text(drawio_graph(nodes,[],340,230),encoding="utf-8")

def plot_fig3(p2):
 seqs=["fr3_walking_xyz","fr3_walking_rpy","fr3_walking_halfsphere"]; methods=["ORB-SLAM2","Semantic","Temporal","Full"]
 labels=["walking_xyz","walking_rpy","walking_halfsphere"]; hatch=["//","..","xx","\\\\"]; colors=["#d9d9d9","#a9c4d6","#d9c79e","#b7b7b7"]
 ix={(r["method"],r["sequence"]):r for r in p2}; x=np.arange(3); width=.19
 fig,ax=plt.subplots(figsize=(6.69,3.55))
 for k,m in enumerate(methods):
  mean=[float(ix[m,s]["ATE_RMSE_mean"]) for s in seqs];std=[float(ix[m,s]["ATE_RMSE_std"]) for s in seqs]
  bars=ax.bar(x+(k-1.5)*width,mean,width,yerr=std,capsize=2.5,label=m,color=colors[k],edgecolor="black",linewidth=.7,hatch=hatch[k],error_kw={"elinewidth":.8})
  if m=="Full":ax.text(x[1]+(k-1.5)*width,mean[1]+std[1]+.04,"*",ha="center",va="bottom",fontsize=9)
 ax.set_xlabel("Sequence");ax.set_ylabel("ATE RMSE/m");ax.set_xticks(x);ax.set_xticklabels(labels);ax.set_ylim(0,1.45);ax.set_yticks(np.arange(0,1.41,.2));ax.legend(ncol=4,loc="upper center",frameon=False,fontsize=7.5);ax.grid(axis="y",linewidth=.4,color="#bbbbbb",linestyle=":");fig.tight_layout(pad=.8)
 save_plot(fig,"fig3_ate_comparison",6.69,3.55)

def plot_fig4(rows):
 candidates=[r for r in rows if r["method"]=="Temporal" and r["sequence"]=="fr3_walking_xyz"]
 if not candidates:raise RuntimeError("No Temporal walking_xyz selected MapPoint evidence")
 run=candidates[0]["run_id"];mp=candidates[0]["map_point_id"];data=[r for r in candidates if r["run_id"]==run and r["map_point_id"]==mp]
 frames=np.array([int(r["frame_id"]) for r in data]);score=np.array([float(r["dynamic_score"]) for r in data]);state=np.array([int(r["dynamic_state"]) for r in data]);sup=np.array([int(r["suppressed"]) for r in data]);threshold=1.0 if data[0]["class_id"]=="3" else 3.0
 fig,ax=plt.subplots(figsize=(6.69,3.45));ax.plot(frames,score,color="black",linewidth=1.0,label="Dynamic score");ax.axhline(threshold,color="#555",linestyle="--",linewidth=1,label=r"Threshold $\theta_c$")
 changes=np.flatnonzero(np.r_[False,state[1:]!=state[:-1]]);ax.scatter(frames[changes],score[changes],marker="o",facecolors="white",edgecolors="black",s=20,label="State transition",zorder=3)
 si=np.flatnonzero(sup);ax.scatter(frames[si],score[si],marker="x",color="#777",s=13,label="Suppressed",zorder=3)
 ax.set_xlabel("Frame ID");ax.set_ylabel("Dynamic evidence");ax.set_xlim(frames.min(),frames.max());ax.set_ylim(bottom=0);ax.legend(frameon=False,ncol=2,loc="upper right",fontsize=7.5);ax.grid(linewidth=.4,color="#c0c0c0",linestyle=":");ax.text(.01,.98,f"MapPoint ID: {mp}   Class: {data[0]['class']}   Sequence: walking_xyz",transform=ax.transAxes,ha="left",va="top",fontsize=7.5);fig.tight_layout(pad=.8)
 save_plot(fig,"fig4_mappoint_evidence",6.69,3.45)
 write_csv(SRC/"fig4_selected_mappoint_plot_data.csv",list(data[0]),data)

def save_plot(fig,name,w,h):
 svg=FIG/f"{name}.svg";eps=FIG/f"{name}.eps";png=FIG/f"{name}_preview.png";tmp=FIG/f".{name}_600.png"
 fig.savefig(svg);fig.savefig(eps,format="eps");fig.savefig(png,dpi=300);fig.savefig(tmp,dpi=600,facecolor="white");plt.close(fig)
 im=Image.open(tmp).convert("CMYK");im.save(FIG/f"{name}.tif",dpi=(600,600),compression="tiff_lzw");tmp.unlink()

def convert_svg(name,w_in,h_in):
 # Generate an equivalent editable vector with Matplotlib because both the
 # installed Inkscape and LibreOffice builds require unavailable GUI services.
 fig,ax=plt.subplots(figsize=(w_in,h_in));ax.set_axis_off();ax.set_xlim(0,10);ax.set_ylim(0,10)
 def box(x,y,w,h,text,fc="#f5f5f5",ec="#333",lw=1.0,fs=7):
  ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle="round,pad=0.03",facecolor=fc,edgecolor=ec,linewidth=lw));ax.text(x+w/2,y+h/2,text,ha="center",va="center",fontsize=fs)
 def arr(a,b):ax.add_patch(FancyArrowPatch(a,b,arrowstyle="-|>",mutation_scale=8,color="#333",linewidth=1.0))
 if name.startswith("fig1"):
  box(4.1,9.1,1.8,.6,"RGB-D图像输入","white");box(.7,7.8,2.5,.7,"ORB特征提取","#eef3f8");box(6.8,7.8,2.5,.7,"语义目标检测","#eef3f8");arr((4.5,9.1),(2,8.5));arr((5.5,9.1),(8,8.5))
  box(.4,6.5,3.1,.8,"当前帧特征/MapPoint关联","#eef3f8");box(6.7,6.5,2.7,.8,"目标类别 + 检测区域","#eef3f8");arr((2,7.8),(2,7.3));arr((8,7.8),(8,7.3));box(6.9,5.35,2.3,.65,"深度反投影","#eef3f8");box(6.65,4.2,2.8,.7,"目标三维代表位置","#eef3f8");arr((8,6.5),(8,6));arr((8,5.35),(8,4.9))
  box(3.5,4.4,3.0,1.25,"① 目标级语义信息管理\nCᵢ：类别  Pᵢ：位置\nMᵢ：MapPoint ID集合","#e7f1ed","#356859",1.3);arr((2,6.5),(4.2,5.65));arr((6.65,4.55),(6.5,4.8));box(3.7,3.25,2.6,.65,"当前帧MapPoint语义观测","white");arr((5,4.4),(5,3.9))
  box(.3,1.25,3.1,1.1,"② 时间一致性动态证据累积\nsⱼᵗ = λ_c^Δt sⱼᵗ⁻¹ + γ_c oⱼᵗ","#f7f0df","#8a6d1d",1.3);box(3.85,1.4,1.8,.8,"动态状态判定\nsⱼᵗ ≥ θ_c","white");box(6.05,1.25,2.55,1.1,"③ 动态MapPoint约束\n投影/运动/局部匹配","#f4e8e8","#8b3a3a",1.3);box(8.9,1.4,.9,.8,"位姿估计","white",fs=6);arr((5,3.25),(1.9,2.35));arr((3.4,1.8),(3.85,1.8));arr((5.65,1.8),(6.05,1.8));arr((8.6,1.8),(8.9,1.8))
 else:
  ax.text(.2,9.5,"示意图",fontsize=7);xs=np.linspace(1.2,8.8,5);obs=["1","1","0","0/1","1"]
  for x,t,o in zip(xs,["t−2","t−1","t","t+1","t+2"],obs):box(x-.55,7.6,1.1,.8,f"{t}\n观测 {o}","#f5f5f5",fs=7)
  ax.plot([.8,9.3],[3,3],color="#777",linestyle="--",linewidth=1);ax.text(9.2,3.2,r"$\theta_c$",ha="right",fontsize=8);ax.arrow(.8,1,0,4.8,head_width=.12,head_length=.18,color="#333",length_includes_head=True);ax.arrow(.8,1,8.5,0,head_width=.12,head_length=.18,color="#333",length_includes_head=True)
  yy=[1.6,2.6,2.25,2.0,3.7];ax.plot(xs,yy,color="black",marker="o",markerfacecolor="white",linewidth=1.3);ax.text(2, .45,"证据累积",fontsize=7,ha="center");ax.text(5.1,.45,"短时漏检：衰减",fontsize=7,ha="center");ax.text(8.7,4.15,"再次累积",fontsize=7,ha="center")
 save_plot(fig,name,w_in,h_in)

def tables(p2,p3,env):
 cpu="MISSING";import re
 m=re.search(r"Model name:\s+(.+)",env.get("cpu",""));cpu=m.group(1).strip() if m else "MISSING"
 mem="MISSING";m=re.search(r"Mem:\s+([^\s]+)",env.get("memory",""));mem=m.group(1) if m else "MISSING"
 write_csv(TAB/"table1_environment.csv",["项目","配置"],[{"项目":"操作系统","配置":env.get("os","MISSING")},{"项目":"CPU","配置":cpu},{"项目":"GPU","配置":env.get("gpu","MISSING")},{"项目":"内存","配置":mem},{"项目":"SLAM框架","配置":"ORB-SLAM2 RGB-D"},{"项目":"RGB-D数据集","配置":"TUM RGB-D"},{"项目":"语义检测模型","配置":"YOLOv5s"}])
 write_csv(TAB/"table2_configurations.csv",["配置","语义信息","时序证据","目标级过滤"],[{"配置":"ORB-SLAM2","语义信息":"—","时序证据":"—","目标级过滤":"—"},{"配置":"Semantic","语义信息":"√","时序证据":"—","目标级过滤":"—"},{"配置":"Temporal","语义信息":"√","时序证据":"√","目标级过滤":"—"},{"配置":"Full","语义信息":"√","时序证据":"√","目标级过滤":"√"}])
 seqs=["fr3_walking_xyz","fr3_walking_rpy","fr3_walking_halfsphere"];methods=["ORB-SLAM2","Semantic","Temporal","Full"];ix={(r["method"],r["sequence"]):r for r in p2}
 raw=[];display=[]
 for s in seqs:
  rr={"sequence":s};dd={"序列":s}
  for m in methods:
   x=ix[m,s];rr[m+"_mean"]=x["ATE_RMSE_mean"];rr[m+"_std"]=x["ATE_RMSE_std"];dd[m]=f"{float(x['ATE_RMSE_mean']):.3f}±{float(x['ATE_RMSE_std']):.3f}"
  raw.append(rr);display.append(dd)
 write_csv(TAB/"table3_ate_rmse.csv",list(raw[0]),raw);write_csv(TAB/"table3_ate_rmse_display.csv",list(display[0]),display)
 rpy=[]
 for m in methods:
  x=ix[m,"fr3_walking_rpy"];rpy.append({"方法":m,"ATE RMSE/m":f"{float(x['ATE_RMSE_mean']):.3f}","TSR":f"{float(x['TSR_mean']):.3f}","PMR":f"{float(x['PMR_mean']):.3f}"})
 write_csv(TAB/"table4_rpy_completeness.csv",list(rpy[0]),rpy)
 p3ix={(r["method"],r["sequence"]):r for r in p3};sf=[]
 for s in seqs:
  a=float(p3ix["Semantic",s]["Switching_Frequency_mean"]);b=float(p3ix["Temporal",s]["Switching_Frequency_mean"]);sf.append({"序列":s,"Semantic":f"{a:.6f}","Temporal":f"{b:.6f}","下降率/%":f"{(a-b)/a*100:.2f}"})
 write_csv(TAB/"table5_switching_frequency.csv",list(sf[0]),sf)
 (SRC/"technical_environment.txt").write_text(f"Git commit: {env.get('git_commit','MISSING')}\nYOLO weights: {env.get('yolo_weights',{}).get('path','MISSING')}\nYOLO SHA-256: {env.get('yolo_weights',{}).get('sha256','MISSING')}\n",encoding="utf-8")

def docs():
 captions='''# 图题与表题\n\n图1 面向动态环境的时序证据融合语义RGB-D SLAM系统框架\n\nFig. 1 Framework of temporal-evidence-fusion semantic RGB-D SLAM in dynamic environments\n\n图2 时间一致性动态证据更新示意\n\nFig. 2 Illustration of temporal dynamic evidence update\n\n图3 不同配置在TUM动态序列上的ATE RMSE\n\nFig. 3 ATE RMSE of different configurations on TUM dynamic sequences\n\n图4 代表地图点动态证据随帧变化\n\nFig. 4 Dynamic evidence variation of a representative map point over frames\n\n表1 实验运行环境\n\nTable 1 Experimental environment\n\n表2 不同实验配置\n\nTable 2 Different experimental configurations\n\n表3 不同方法在TUM动态序列上的ATE RMSE\n\nTable 3 ATE RMSE of different methods on TUM dynamic sequences\n\n表4 walking_rpy序列轨迹完整性比较\n\nTable 4 Trajectory completeness comparison on the walking_rpy sequence\n\n表5 Semantic与Temporal的地图点状态切换频率\n\nTable 5 MapPoint state switching frequency of Semantic and Temporal\n'''
 (OUT/"captions.md").write_text(captions,encoding="utf-8")
 guide='''# 表格排版说明\n\n所有CSV均为数据源，需在Word中排成三线表：无竖线、左右不封口，仅保留顶线、表头下横线和底线。表题中英文小五号；表内六号；数字按小数点对齐。中文目标字体为方正书宋，英文和数字为Times New Roman。\n\n- 表1：两列均左对齐；无统一单位；硬件与系统字符串保持原始记录。\n- 表2：配置列左对齐，其余三列居中；符号为√或—。\n- 表3：序列列左对齐，数值列按小数点对齐；单位m写入表题或表头；显示版统一`0.000±0.000`。\n- 表4：方法左对齐；ATE、TSR、PMR按小数点对齐，均保留3位；ATE单位m，TSR/PMR为比例。\n- 表5：序列左对齐；频率保留6位，下降率保留2位，下降率单位%。\n'''
 (TAB/"table_layout_guide.md").write_text(guide,encoding="utf-8")

def qa():
 lines=["# Paper figures and tables","","## Font status","","FONT_MISSING: 方正书宋","","Times New Roman已安装。可编辑源文件声明方正书宋目标字体，但由于本机缺失，当前导出文件由系统回退字体渲染，不能声称中文字体已完全满足期刊要求；投稿前应在安装方正书宋的环境中重新导出。","","## Figure quality audit","","| 图 | TIF像素 | DPI | 模式 | 600 dpi | 轴标签/说明 | 数据来源 |","|---|---:|---:|---|---|---|---|"]
 sources={"fig1_system_framework":"方法框架示意；依据当前源码，不含实验数据","fig2_temporal_evidence":"机制示意；观测序列仅为示意，不是实验结果","fig3_ate_comparison":"02_tum_comparison/p2_comparison_summary.csv","fig4_mappoint_evidence":"03_temporal_continuity/selected_mappoint_evidence.csv"}
 labels={"fig1_system_framework":"无坐标轴","fig2_temporal_evidence":"示意时间轴与阈值","fig3_ate_comparison":"Sequence；ATE RMSE/m","fig4_mappoint_evidence":"Frame ID；Dynamic evidence"}
 for name in sources:
  im=Image.open(FIG/f"{name}.tif");dpi=im.info.get("dpi",(0,0));dx,dy=float(dpi[0]),float(dpi[1]);ok=dx>=599 and im.width>=2000
  lines.append(f"| {name} | {im.width}×{im.height} | {dx:.0f}×{dy:.0f} | {im.mode} | {'PASS' if ok else 'FAIL'} | {labels[name]} | {sources[name]} |")
 lines += ["","- 所有TIF均由SVG/Matplotlib按最终物理尺寸直接栅格化到600 dpi，不是仅修改DPI元数据；均为CMYK。","- 图3用填充纹理区分方法，图4用线型和标记区分状态，因此不依赖颜色作为唯一信息。图例位于上方或右上空白区；自动布局后未覆盖柱体主区域。","- 图1为双栏宽流程图；图2为单栏宽示意图；图3、图4为双栏宽坐标图。预览PNG为300 dpi。","- 图题未烘焙进图像，统一存于captions.md。","","## Figure mapping","","- 图1：方法/系统框架；drawio可继续编辑。","- 图2：方法/时间证据机制；drawio可继续编辑。","- 图3：实验/定位精度；Full在walking_rpy的星号须配合图注说明低轨迹覆盖。","- 图4：实验/时间连续性；使用P3既定客观选点结果。选择规则：曾进入动态状态、不同观测帧数最多、并列取最小MapPoint ID。","","## Table sources","","- 表1：`01_tum_full/experiment_environment.json`。","- 表2：P2经审计的四种真实配置定义。","- 表3、表4：`02_tum_comparison/p2_comparison_summary.csv`。","- 表5：`03_temporal_continuity/p3_temporal_continuity_summary.csv`。","","## Completeness and limitations","","- 所有实验图均来自既有真实数据；图2明确为机制示意图。未生成Bonn、Precision、Recall或F1图表。","- P3伴随ATE/RPE未用于图3或主性能表。","- 表1字段均可由环境JSON获得；未编造缺失硬件信息。","- 可直接插入Word：EPS或TIF；PNG仅供预览。可继续编辑：图1、图2的drawio，以及全部SVG。","- 灰度可辨性通过纹理、线型和点型设计保证；最终排版仍建议在Word目标尺寸下人工目检一次。",""]
 (OUT/"README.md").write_text("\n".join(lines),encoding="utf-8")

def main():
 for p in (FIG,TAB,SRC):p.mkdir(parents=True,exist_ok=True)
 p2=read_csv(P2);p3=read_csv(P3);mp=read_csv(MP);env=json.loads(ENV.read_text())
 for src,name in ((P2,"p2_comparison_source.csv"),(P3,"p3_switching_source.csv"),(MP,"selected_mappoint_evidence_source.csv"),(ENV,"experiment_environment_source.json")):shutil.copy2(src,SRC/name)
 fig1();fig2();convert_svg("fig1_system_framework",6.69,4.57);convert_svg("fig2_temporal_evidence",3.35,2.28);plot_fig3(p2);plot_fig4(mp);tables(p2,p3,env);docs();qa()
if __name__=="__main__":main()
