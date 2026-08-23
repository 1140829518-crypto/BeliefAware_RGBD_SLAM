#!/usr/bin/env python3
"""Generate non-destructive traditional CV/SLAM-style figure previews."""
from __future__ import annotations
import csv
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.offsetbox import AnnotationBbox, HPacker, TextArea
from matplotlib.patches import Rectangle, FancyArrowPatch
import numpy as np

REPO=Path(__file__).resolve().parents[1]
ROOT=REPO/"experiments/final_paper/paper_figures_tables"
OUT=ROOT/"figures/revision_preview"
P2=REPO/"experiments/final_paper/02_tum_comparison/p2_comparison_summary.csv"
MP=REPO/"experiments/final_paper/03_temporal_continuity/selected_mappoint_evidence.csv"
BLUE="#1f77b4"; ORANGE="#ff7f0e"; GREEN="#2ca02c"; RED="#d62728"; PURPLE="#9467bd"
CN_FONT_PATH=Path("/home/djn/.local/share/fonts/FZSSK.TTF")
CN_FONT=font_manager.FontProperties(fname=str(CN_FONT_PATH))
EN_FONT=font_manager.FontProperties(family="Times New Roman")
CN_LEGEND_FONT=CN_FONT.copy();CN_LEGEND_FONT.set_size(7.5)

plt.rcParams.update({"font.family":"Times New Roman","font.size":7.5,"axes.labelsize":7.5,"xtick.labelsize":7.5,"ytick.labelsize":7.5,"legend.fontsize":7.5,"axes.linewidth":0.8,"figure.facecolor":"white","axes.facecolor":"white","savefig.facecolor":"white","axes.grid":False})

def rows(path):
 with path.open(encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))
def clean_axes(ax):
 ax.grid(False);ax.set_facecolor("white");ax.spines["top"].set_visible(False);ax.spines["right"].set_visible(False)
 for side in ("left","bottom"):ax.spines[side].set_color("black");ax.spines[side].set_linewidth(.8)
 ax.tick_params(direction="out",width=.8,length=3,color="black")
def save(fig,name):
 fig.savefig(OUT/name,dpi=220,bbox_inches="tight",facecolor="white");plt.close(fig)

def build_fig1():
 fig,ax=plt.subplots(figsize=(7.05,5.1));ax.set_xlim(0,14);ax.set_ylim(0,14);ax.axis("off")
 def label(x,y,text,fs=7.5):
  mixed={
   "RGB-D图像":[("RGB-D",EN_FONT),("图像",CN_FONT)],
   "ORB特征提取":[("ORB",EN_FONT),("特征提取",CN_FONT)],
   "ORB-SLAM2跟踪与位姿估计":[("ORB-SLAM2",EN_FONT),("跟踪与位姿估计",CN_FONT)],
  }
  if text in mixed:
   areas=[TextArea(part,textprops={"fontproperties":prop,"fontsize":fs}) for part,prop in mixed[text]]
   ax.add_artist(AnnotationBbox(HPacker(children=areas,align="center",pad=0,sep=0),(x,y),frameon=False,box_alignment=(.5,.5)))
  else:
   ax.text(x,y,text,ha="center",va="center",fontsize=fs,fontproperties=CN_FONT)
 def box(x,y,w,h,text,edge="black",fill="white",lw=1.0,fs=7.5):
  ax.add_patch(Rectangle((x,y),w,h,facecolor=fill,edgecolor=edge,linewidth=lw));label(x+w/2,y+h/2,text,fs)
 def semantic_management_box(x,y,w,h):
  ax.add_patch(Rectangle((x,y),w,h,facecolor="white",edgecolor=GREEN,linewidth=1.1))
  ax.text(x+w/2,y+h*.68,"目标级语义信息管理",ha="center",va="center",fontsize=7.5,fontproperties=CN_FONT)
  ax.text(x+w/2,y+h*.25,"类别·空间位置·关联地图点",ha="center",va="center",fontsize=7.5,fontproperties=CN_FONT)
 def arr(x1,y1,x2,y2):ax.add_patch(FancyArrowPatch((x1,y1),(x2,y2),arrowstyle="-|>",mutation_scale=9,linewidth=.9,color="black",shrinkA=1,shrinkB=1))
 # Upper dual branch.
 box(5.25,13.1,3.5,.55,"RGB-D图像")
 arr(7,13.1,3.7,12.25);arr(7,13.1,10.3,12.25)
 box(2.1,11.55,3.2,.65,"ORB特征提取");box(8.7,11.55,3.2,.65,"目标检测")
 arr(3.7,11.55,3.7,10.95);arr(10.3,11.55,10.3,10.95)
 box(2.1,10.25,3.2,.65,"目标与地图点关联");box(8.7,10.25,3.2,.65,"类别与检测区域")
 arr(10.3,10.25,10.3,9.65);box(8.7,8.95,3.2,.65,"目标空间位置获取")
 # Merge into the vertical main pipeline.
 arr(3.7,10.25,5.5,8.29);arr(10.3,8.95,8.5,8.29)
 semantic_management_box(5.0,7.35,4.0,.94)
 arr(7,7.35,7,6.83);box(5.0,6.15,4.0,.65,"当前语义观测")
 arr(7,6.15,7,5.63);box(5.0,4.95,4.0,.65,"时间一致性动态证据累积",GREEN,"white",1.1)
 arr(7,4.95,7,4.43);box(5.0,3.75,4.0,.65,"动态状态判定")
 arr(7,3.75,7,3.23);box(5.0,2.55,4.0,.65,"动态地图点约束",GREEN,"white",1.1)
 arr(7,2.55,7,2.03);box(5.0,1.35,4.0,.65,"ORB-SLAM2跟踪与位姿估计")
 arr(7,1.35,7,.83);box(5.0,.15,4.0,.65,"相机位姿")
 return fig

def fig1():
 fig=build_fig1()
 save(fig,"fig1_system_framework_preview.png")

def build_fig2():
 fig,ax=plt.subplots(figsize=(4.2,2.55));clean_axes(ax)
 x=np.arange(0,10);obs=np.array([1,1,1,0,0,1,1,0,1,1]);ev=[];s=0
 for o in obs:
  s=.78*s+(.55 if o else 0);ev.append(s)
 ev=np.array(ev);threshold=1.25
 ax.plot(x,ev,color=GREEN,linewidth=1.5,label="时序动态证据")
 ax.axhline(threshold,color=RED,linestyle="--",linewidth=1.1,label="动态判定阈值")
 ax.scatter(x[obs==1],np.full(np.sum(obs==1),.08),s=15,color=BLUE,label="动态观测",zorder=3)
 ax.vlines(x[obs==1],0,.16,color=BLUE,linewidth=.7)
 ax.annotate("证据衰减",xy=(4,ev[4]),xytext=(4.7,2.22),arrowprops={"arrowstyle":"->","lw":.7},fontsize=7.5,fontproperties=CN_FONT)
 ax.set_xlabel("帧编号",fontproperties=CN_FONT,fontsize=7.5);ax.set_ylabel("动态证据",fontproperties=CN_FONT,fontsize=7.5);ax.set_xlim(-.4,9.4);ax.set_ylim(0,max(ev.max()+.2,2.5));ax.set_xticks(x);ax.legend(frameon=False,prop=CN_LEGEND_FONT,loc="lower left",bbox_to_anchor=(0,1.01),ncol=3,borderaxespad=0,columnspacing=.9,handlelength=1.8)
 fig.subplots_adjust(top=.82)
 return fig

def fig2():
 fig=build_fig2()
 save(fig,"fig2_temporal_evidence_preview.png")

def build_fig3(data):
 seqs=["fr3_walking_xyz","fr3_walking_rpy","fr3_walking_halfsphere"];labels=["walking_xyz","walking_rpy","walking_halfsphere"];methods=["ORB-SLAM2","Semantic","Temporal","Full"];colors=[BLUE,ORANGE,GREEN,RED]
 ix={(r["method"],r["sequence"]):r for r in data};x=np.arange(3);width=.18
 fig,ax=plt.subplots(figsize=(7.05,3.45));clean_axes(ax)
 for j,(method,color) in enumerate(zip(methods,colors)):
  means=np.array([float(ix[method,s]["ATE_RMSE_mean"]) for s in seqs]);stds=np.array([float(ix[method,s]["ATE_RMSE_std"]) for s in seqs]);pos=x+(j-1.5)*width
  ax.bar(pos,means,width,color=color,edgecolor="black",linewidth=.55,label=method,zorder=2)
  ax.errorbar(pos,means,yerr=stds,fmt="none",ecolor="black",elinewidth=.65,capsize=2.2,capthick=.65,zorder=3)
  for k,(px,m,s) in enumerate(zip(pos,means,stds)):
   text=f"{m:.3f}\n±{s:.3f}" + ("*" if method=="Full" and k==1 else "")
   stagger=(.08*j if k==1 and j>0 else 0)
   ax.text(px,m+s+.025+stagger,text,ha="center",va="bottom",fontsize=7.5,linespacing=.9)
 ax.set_xlabel("序列",fontproperties=CN_FONT,fontsize=7.5);ax.set_ylabel("ATE RMSE/m");ax.set_xticks(x);ax.set_xticklabels(labels);ax.set_ylim(0,1.52);ax.legend(ncol=4,frameon=False,loc="lower center",bbox_to_anchor=(.5,1.01),fontsize=7.5,columnspacing=1.2,handlelength=1.4,borderaxespad=0)
 fig.subplots_adjust(top=.84)
 return fig

def fig3(data):
 fig=build_fig3(data)
 save(fig,"fig3_ate_comparison_preview.png")

def build_fig4(data):
 selected=[r for r in data if r["method"]=="Temporal" and r["sequence"]=="fr3_walking_xyz" and r["map_point_id"]=="254" and r["run_id"]=="run_01"]
 if not selected:raise RuntimeError("Expected Temporal/walking_xyz/MapPoint 254 data not found")
 run="run_01"
 frame=np.array([int(r["frame_id"]) for r in selected]);score=np.array([float(r["dynamic_score"]) for r in selected]);hit=np.array([int(r["dynamic_hit"]) for r in selected]);state=np.array([int(r["dynamic_state"]) for r in selected]);supp=np.array([int(r["suppressed"]) for r in selected]);threshold=1.0
 fig,ax=plt.subplots(figsize=(7.05,3.35));clean_axes(ax)
 ax.plot(frame,score,color=GREEN,linewidth=1.15,label="时序动态证据",zorder=2)
 ax.axhline(threshold,color=RED,linestyle="--",linewidth=1,label="动态判定阈值")
 hi=np.flatnonzero(hit);ax.scatter(frame[hi],score[hi],s=5,color=BLUE,label="动态观测",zorder=3)
 changes=np.flatnonzero(np.r_[False,state[1:]!=state[:-1]]);ax.scatter(frame[changes],score[changes],s=12,marker="o",facecolor="white",edgecolor=PURPLE,linewidth=.7,label="状态切换",zorder=4)
 ax.set_xlabel("帧编号",fontproperties=CN_FONT,fontsize=7.5);ax.set_ylabel("动态证据",fontproperties=CN_FONT,fontsize=7.5);ax.set_xlim(frame.min(),frame.max());ax.set_ylim(0,score.max()*1.08);ax.legend(frameon=False,ncol=4,loc="lower left",bbox_to_anchor=(0,1.01),prop=CN_LEGEND_FONT,columnspacing=1.1,handlelength=2,borderaxespad=0)
 fig.subplots_adjust(top=.84)
 return fig,{"run":run,"rows":len(selected),"frame_min":int(frame.min()),"frame_max":int(frame.max()),"score_min":float(score.min()),"score_max":float(score.max())}

def fig4(data):
 fig,meta=build_fig4(data)
 save(fig,"fig4_mappoint_evidence_preview.png")
 return meta

def main():
 OUT.mkdir(parents=True,exist_ok=True);p2=rows(P2);mp=rows(MP);fig1();fig2();fig3(p2);meta=fig4(mp)
 report=f'''# Style revision report

Only preview PNG files were generated. Existing formal drawio/SVG/EPS/TIF files were not overwritten.

## Unified style

- Font status: `FONT_MISSING: 方正书宋`. This is an environment limitation and does not block preview generation. The current Chinese fallback must not be described as fully journal-compliant.
- Background: pure white.
- Grid: disabled (`ax.grid(False)`) for Figures 2–4.
- Axes: black solid bottom/left spines; top/right spines removed.
- Font: Times New Roman for English text, numbers and variables. Available system Chinese fallback is used only for previews; final export must be repeated after installing 方正书宋.
- Colors: ORB-SLAM2/Baseline `{BLUE}`; Semantic `{ORANGE}`; Temporal/Ours `{GREEN}`; Full `{RED}`; auxiliary state marker `{PURPLE}`.
- No gradients, shadows, rounded cards, gray axes backgrounds or background state bands.

## Figure provenance and checks

- Figure 1: method schematic based on the current implemented pipeline; no experimental data. Traditional rectangular blocks, black arrows and restrained core-module borders.
- Figure 2: conceptual illustration, not experimental data. Green temporal evidence, red threshold, blue dynamic observations. Grid disabled.
- Figure 3: read directly from `{P2}`. Means and standard deviations are unchanged; black error bars are shown. Full/walking_rpy has `*`. Grid disabled.
- Figure 4: read directly from `{MP}`. Filter fixed to method `Temporal`, sequence `fr3_walking_xyz`, MapPoint ID `254`, run `{meta['run']}`.
- Figure 4 rows used: {meta['rows']}; full available frame span: {meta['frame_min']}–{meta['frame_max']}; dynamic score range: {meta['score_min']:.6f}–{meta['score_max']:.6f}.
- Figure 4 smoothing: **No**.
- Figure 4 cropping: **No**; every source row for the fixed method/sequence/MapPoint/run is plotted.
- Editable source retained: `scripts/generate_paper_figure_revision_preview.py`. Formal drawio/SVG sources are not overwritten during preview review.
- Formal 600 dpi CMYK lock: **Not performed in this preview stage**.

## P2 values used by Figure 3

| Sequence | ORB-SLAM2 | Semantic | Temporal | Full |
|---|---|---|---|---|
| walking_xyz | 0.835129±0.222270 | 0.504876±0.055832 | 0.562268±0.082441 | 0.538911±0.042124 |
| walking_rpy | 1.164329±0.152318 | 0.749207±0.035709 | 0.756381±0.058433 | 0.465345±0.395890 |
| walking_halfsphere | 0.644462±0.072637 | 0.329266±0.177200 | 0.356207±0.215751 | 0.443035±0.209126 |
'''
 (OUT/"style_revision_report.md").write_text(report,encoding="utf-8")
if __name__=="__main__":main()
