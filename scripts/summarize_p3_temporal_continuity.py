#!/usr/bin/env python3
"""Summarize P3 frame-level and stable-MapPoint temporal continuity evidence."""

from __future__ import annotations
import csv, json, math, statistics
from collections import defaultdict
from pathlib import Path

REPO=Path(__file__).resolve().parents[1]
ROOT=REPO/"experiments/final_paper/03_temporal_continuity"
METHODS=("Semantic","Temporal")
SEQS={
 "fr3_walking_xyz":(REPO/"dataset_associations/fr3_walking_xyz_associate.txt",827),
 "fr3_walking_rpy":(REPO/"dataset_associations/fr3_walking_rpy_associate.txt",866),
 "fr3_walking_halfsphere":(REPO/"dataset_associations/fr3_walking_halfsphere_associate.txt",1021)}

def trajectory_stamps(path):
 out=[]
 if path.exists():
  for line in path.read_text(errors="ignore").splitlines():
   z=line.split()
   if len(z)>=8:
    try: out.append(float(z[0]))
    except ValueError: pass
 return out

def coverage(assoc,traj):
 a=[]
 for line in assoc.read_text(errors="ignore").splitlines():
  z=line.split()
  if z and not line.lstrip().startswith("#"):
   try:a.append(float(z[0]))
   except ValueError:pass
 t=trajectory_stamps(traj); hit=[False]*len(a); j=0
 for i,x in enumerate(a):
  while j+1<len(t) and abs(t[j+1]-x)<abs(t[j]-x):j+=1
  if t and abs(t[j]-x)<=.02:hit[i]=True
 gaps=0; inside=False
 for h in hit:
  if not h and not inside:gaps+=1;inside=True
  elif h:inside=False
 return len(t),gaps,(len(t)/len(a) if a else math.nan),(1-len(t)/len(a) if a else math.nan)

def frame_stats(path):
 # Cull may execute more than once for a frame; use the maximum observed count per frame.
 out={}
 if not path.exists():return out
 with path.open(newline="") as f:
  for row in csv.DictReader(f,delimiter=" "):
   try:fr=int(row["frame_id"]); d=int(row["dynamic_map_points"]); s=int(row["suppressed_map_points"])
   except (ValueError,KeyError):continue
   old=out.get(fr,(0,0));out[fr]=(max(old[0],d),max(old[1],s))
 return out

def evidence(path):
 """Collapse repeated updates to the final event for each stable MapPoint in each frame."""
 if not path.exists():return {},{},0,0
 final={}; classes={}
 with path.open(newline="") as f:
  for row in csv.DictReader(f):
   try:
    fr=int(row["frame_id"]);mp=int(row["map_point_id"]);cl=int(row["class_id"])
    hit=int(row["dynamic_hit"]);score=float(row["dynamic_score"]);state=int(row["dynamic_state"]);sup=int(row["suppressed"])
   except (ValueError,KeyError):continue
   if cl>=0:classes[mp]=cl
   final[(fr,mp)]=(cl,hit,score,state,sup)
 by_mp=defaultdict(list)
 for (fr,mp),v in final.items():by_mp[mp].append((fr,)+v)
 switches=transitions=0
 for observations in by_mp.values():
  observations.sort(); prev=None
  for item in observations:
   state=item[4]
   if prev is not None:transitions+=1;switches+=state!=prev
   prev=state
 return final,classes,switches,transitions

def runtime(run,conf):
 vals={}
 p=run/"runtime.txt"
 if p.exists():
  for line in p.read_text(errors="ignore").splitlines():
   z=line.split()
   if len(z)>=2:vals[z[0]]=z[1]
 try:tfps=float(vals.get("fps","nan"))
 except ValueError:tfps=math.nan
 try:sec=float(conf.get("runtime_seconds",math.nan))
 except (ValueError,TypeError):sec=math.nan
 return tfps,sec

def load_runs():
 rows=[]; frames=[]; selected=[]
 for method in METHODS:
  for seq,(assoc,total) in SEQS.items():
   selection_done=False
   for rid in range(1,6):
    run=ROOT/method/seq/f"run_{rid:02d}"; cp=run/"run_config.json"
    conf=json.loads(cp.read_text()) if cp.exists() else {}
    valid,gaps,tsr,pmr=coverage(assoc,run/"CameraTrajectory.txt")
    metric_path=run/"eval/metrics.json"; metrics=json.loads(metric_path.read_text()) if metric_path.exists() else {}
    legal=bool(metrics and valid>=2); ate=metrics.get("ate",{}) if legal else {}; rpe=metrics.get("rpe_trans",{}) if legal else {}
    fs=frame_stats(run/"SemanticDynamicStatistics.txt")
    final,classes,switches,transitions=evidence(run/"mappoint_evidence_raw.csv")
    sf=switches/transitions if transitions else math.nan
    tfps,sec=runtime(run,conf)
    frame_ev=defaultdict(lambda:[0,0,0])
    for (fr,mp),(_,_,_,state,sup) in final.items():
     frame_ev[fr][0]+=1;frame_ev[fr][1]+=state;frame_ev[fr][2]+=sup
    all_frames=sorted(set(fs)|set(frame_ev))
    rows.append({"method":method,"sequence":seq,"run_id":f"run_{rid:02d}","raw_process_status":conf.get("raw_process_status","unknown"),"experiment_completion_status":conf.get("experiment_completion_status","incomplete"),"exit_code":conf.get("exit_code",""),"association_total_frames":total,"trajectory_valid_poses":valid,"ATE_RMSE":float(ate.get("rmse",math.nan)),"RPE_translation_RMSE":float(rpe.get("rmse",math.nan)),"tracking_gap_episodes":gaps,"TSR":tsr,"PMR":pmr,"Tracking_FPS":tfps,"runtime_seconds":sec,"frame_log_frames":len(all_frames),"dynamic_map_points_mean":statistics.fmean(frame_ev[fr][1] for fr in all_frames) if all_frames else math.nan,"suppressed_map_points_mean":statistics.fmean(frame_ev[fr][2] for fr in all_frames) if all_frames else math.nan,"cull_dynamic_map_points_mean":statistics.fmean(fs.get(fr,(0,0))[0] for fr in all_frames) if all_frames else math.nan,"cull_suppressed_map_points_mean":statistics.fmean(fs.get(fr,(0,0))[1] for fr in all_frames) if all_frames else math.nan,"mappoint_state_switches":switches,"mappoint_state_transition_opportunities":transitions,"Switching_Frequency":sf,"has_evidence":int(bool(final)),"has_legal_evaluation":int(legal),"run_dir":str(run)})
    for fr in all_frames:
     d,s=fs.get(fr,(0,0)); observed,dyn,supev=frame_ev.get(fr,(0,0,0))
     frames.append({"method":method,"sequence":seq,"run_id":f"run_{rid:02d}","frame_id":fr,"dynamic_map_points":d,"suppressed_map_points":s,"observed_unique_map_points":observed,"effective_dynamic_map_points":dyn,"evidence_suppressed_map_points":supev})
    if not selection_done and legal and final:
     counts=defaultdict(set); ever=defaultdict(bool)
     for (fr,mp),(_,_,_,state,_) in final.items():counts[mp].add(fr);ever[mp]|=bool(state)
     candidates=[mp for mp in counts if ever[mp]]
     if candidates:
      chosen=min(candidates,key=lambda mp:(-len(counts[mp]),mp)); last_class=classes.get(chosen,-1)
      for (fr,mp),(cl,hit,score,state,sup) in sorted(final.items()):
       if mp!=chosen:continue
       if cl>=0:last_class=cl
       selected.append({"method":method,"sequence":seq,"run_id":f"run_{rid:02d}","selection_rule":"most distinct observed frames among MapPoints ever dynamic; tie=smallest ID","frame_id":fr,"map_point_id":mp,"class_id":last_class,"class":"person" if last_class==3 else "unknown" if last_class<0 else f"class_{last_class}","dynamic_hit":hit,"dynamic_score":score,"dynamic_state":state,"suppressed":sup})
      selection_done=True
 return rows,frames,selected

def finite(rows,key):return [float(x[key]) for x in rows if isinstance(x[key],(int,float)) and math.isfinite(float(x[key]))]
def mean(x):return statistics.fmean(x) if x else math.nan
def std(x):return statistics.stdev(x) if len(x)>1 else (0.0 if len(x)==1 else math.nan)
def summarize(rows):
 out=[]
 for method in METHODS:
  for seq in SEQS:
   g=[x for x in rows if x["method"]==method and x["sequence"]==seq]; legal=[x for x in g if x["has_legal_evaluation"]]
   completed=[x for x in g if x["experiment_completion_status"]=="completed"]; evidence_rows=[x for x in g if x["has_evidence"]]
   d={"method":method,"sequence":seq,"n_total":len(g),"n_completed":len(completed),"n_legal_evaluation":len(legal),"n_evidence":len(evidence_rows)}
   for key in ("ATE_RMSE","RPE_translation_RMSE","tracking_gap_episodes","TSR","PMR","Tracking_FPS","dynamic_map_points_mean","suppressed_map_points_mean","mappoint_state_switches","Switching_Frequency"):
    src=legal if key in ("ATE_RMSE","RPE_translation_RMSE") else evidence_rows if key in ("dynamic_map_points_mean","suppressed_map_points_mean","mappoint_state_switches","Switching_Frequency") else completed
    vals=finite(src,key);d[key+"_mean"]=mean(vals);d[key+"_std"]=std(vals)
   out.append(d)
 return out

def write(path,rows):
 path.parent.mkdir(parents=True,exist_ok=True)
 if not rows:return
 with path.open("w",newline="",encoding="utf-8-sig") as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader()
  for row in rows:w.writerow({k:("" if isinstance(v,float) and not math.isfinite(v) else f"{v:.9f}" if isinstance(v,float) else v) for k,v in row.items()})

def report(summary,runs):
 ix={(x["method"],x["sequence"]):x for x in summary}
 lines=["# P3 时间一致性动态证据连续性验证报告","","## 实验定义","","- 比较对象：Semantic (`SemanticMode=1, Shadow=0, Active=0`) 与 Temporal (`SemanticMode=2, Shadow=0, Active=0`)。","- 为获得稳定 MapPoint ID 级证据，增加了由 `ORB_SLAM2_MAPPOINT_EVIDENCE_LOG` 显式启用的只读日志；它不改变分数、阈值、匹配、抑制或控制流。由于 P2 日志只有帧级汇总，P3 对固定 30 个 run ID 进行了补跑。","- MapPoint 在一次帧处理中可能被多个匹配路径更新；统计时按 `(frame_id, map_point_id)` 保留日志顺序中的最终状态。","- **Switching Frequency 定义**：对每个稳定 `MapPoint::mnId`，按其被观测帧排序，计算相邻两次观测的二值有效动态状态是否改变；`SF = 全部点的状态改变次数 / 全部点的相邻观测对数`。这不是目标 ID 级切换，也不把未观测帧补成静态。Semantic 的有效动态状态是当前帧 `dynamic_hit`，Temporal 的有效动态状态是累积分数达到类别阈值。","- `temporal_evidence_frame_log.csv` 同时保留两类口径：原 Cull 阶段计数与点级日志按稳定 ID 去重后的最终状态。主表采用后者，因为匹配阶段可能早于 Cull 完成状态更新或抑制。","","## 结果汇总","","| Method | Sequence | completed/legal | Switching Frequency | switches | dynamic MPs/frame | suppressed MPs/frame | gaps | TSR | PMR | RPE trans | ATE (aux.) |","|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
 for method in METHODS:
  for seq in SEQS:
   x=ix[method,seq];lines.append(f"| {method} | {seq} | {x['n_completed']}/{x['n_legal_evaluation']} | {x['Switching_Frequency_mean']:.6f} ± {x['Switching_Frequency_std']:.6f} | {x['mappoint_state_switches_mean']:.1f} ± {x['mappoint_state_switches_std']:.1f} | {x['dynamic_map_points_mean_mean']:.3f} ± {x['dynamic_map_points_mean_std']:.3f} | {x['suppressed_map_points_mean_mean']:.3f} ± {x['suppressed_map_points_mean_std']:.3f} | {x['tracking_gap_episodes_mean']:.2f} ± {x['tracking_gap_episodes_std']:.2f} | {x['TSR_mean']:.6f} ± {x['TSR_std']:.6f} | {x['PMR_mean']:.6f} ± {x['PMR_std']:.6f} | {x['RPE_translation_RMSE_mean']:.6f} ± {x['RPE_translation_RMSE_std']:.6f} | {x['ATE_RMSE_mean']:.6f} ± {x['ATE_RMSE_std']:.6f} |")
 lines += ["","## Semantic → Temporal 变化","","| Sequence | SF change | gaps change | TSR change | RPE change | ATE change |","|---|---:|---:|---:|---:|---:|"]
 for seq in SEQS:
  s,t=ix["Semantic",seq],ix["Temporal",seq]
  lines.append(f"| {seq} | {t['Switching_Frequency_mean']-s['Switching_Frequency_mean']:+.6f} | {t['tracking_gap_episodes_mean']-s['tracking_gap_episodes_mean']:+.2f} | {(t['TSR_mean']-s['TSR_mean'])*100:+.2f} pp | {(t['RPE_translation_RMSE_mean']/s['RPE_translation_RMSE_mean']-1)*100:+.2f}% | {(t['ATE_RMSE_mean']/s['ATE_RMSE_mean']-1)*100:+.2f}% |")
 lines += ["","## 结论（仅据本次数据）",""]
 lowered=[q for q in SEQS if ix['Temporal',q]['Switching_Frequency_mean']<ix['Semantic',q]['Switching_Frequency_mean']]
 gaplow=[q for q in SEQS if ix['Temporal',q]['tracking_gap_episodes_mean']<ix['Semantic',q]['tracking_gap_episodes_mean']]
 tsrup=[q for q in SEQS if ix['Temporal',q]['TSR_mean']>ix['Semantic',q]['TSR_mean']]
 rpeup=[q for q in SEQS if ix['Temporal',q]['RPE_translation_RMSE_mean']<ix['Semantic',q]['RPE_translation_RMSE_mean']]
 atew=[q for q in SEQS if ix['Temporal',q]['ATE_RMSE_mean']>=ix['Semantic',q]['ATE_RMSE_mean']]
 lines += [f"1. Temporal 降低 MapPoint Switching Frequency 的序列：{', '.join(lowered) if lowered else '无'}；其余序列不支持该结论。",f"2. tracking gaps 减少的序列：{', '.join(gaplow) if gaplow else '无'}。",f"3. TSR 提高的序列：{', '.join(tsrup) if tsrup else '无'}。",f"4. RPE translation 改善的序列：{', '.join(rpeup) if rpeup else '无'}。",f"5. ATE 未改善的序列：{', '.join(atew) if atew else '无'}。这些序列是否仍有连续性收益，必须同时查看 SF、gaps 和 TSR，不能由 ATE 单独推断。","6. 三个序列的变化方向若不一致，则结论是场景依赖，而不是稳定改善。","","## 运行完整性","",f"- 固定 run 总数：{len(runs)}；completed：{sum(x['experiment_completion_status']=='completed' for x in runs)}；legal evaluation：{sum(x['has_legal_evaluation'] for x in runs)}。","- Semantic/walking_xyz run_01 因受限环境禁止创建 Unix socket 而 `exit_1/incomplete`；run_02 是首次启动被停止时留下的固定目录，状态保持 `unknown/incomplete`。二者未被替换，误差统计不按 0 处理。","","## 选点规则","","`selected_mappoint_evidence.csv` 对每个 method × sequence 使用首个具有合法评价和证据的固定 run，选择“曾至少一次为动态，且不同观测帧数最多”的 MapPoint；并列时选择最小 `mnId`。未人工挑选曲线。","","P3 到此结束，未启动 P4。",""]
 (ROOT/"p3_temporal_continuity_report.md").write_text("\n".join(lines),encoding="utf-8")

def main():
 runs,frames,selected=load_runs();summary=summarize(runs)
 write(ROOT/"p3_temporal_continuity_runs.csv",runs);write(ROOT/"p3_temporal_continuity_summary.csv",summary);write(ROOT/"temporal_evidence_frame_log.csv",frames);write(ROOT/"selected_mappoint_evidence.csv",selected);report(summary,runs)
if __name__=="__main__":main()
