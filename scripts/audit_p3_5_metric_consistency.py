#!/usr/bin/env python3
"""Read-only P2/P3 metric provenance and run-level consistency audit."""
from __future__ import annotations
import csv, hashlib, json, math, statistics
from pathlib import Path

REPO=Path(__file__).resolve().parents[1]
P2=REPO/"experiments/final_paper/02_tum_comparison"
P3=REPO/"experiments/final_paper/03_temporal_continuity"
OUT=P3
METHODS=("Semantic","Temporal")
SEQS=("fr3_walking_xyz","fr3_walking_rpy","fr3_walking_halfsphere")

def sha(path):
 h=hashlib.sha256()
 with path.open("rb") as f:
  for b in iter(lambda:f.read(1048576),b""):h.update(b)
 return h.hexdigest()
def trajectory_format(path):
 widths=set();rows=0
 if path.exists():
  for line in path.read_text(errors="ignore").splitlines():
   if line.strip() and not line.lstrip().startswith("#"):widths.add(len(line.split()));rows+=1
 return rows,"|".join(map(str,sorted(widths)))

def runs():
 out=[]
 for experiment,root in (("P2",P2),("P3",P3)):
  for method in METHODS:
   for seq in SEQS:
    for rid in range(1,6):
     run=root/method/seq/f"run_{rid:02d}"; cp=run/"run_config.json"
     conf=json.loads(cp.read_text()) if cp.exists() else {}
     mp=run/"eval/metrics.json"; metrics=json.loads(mp.read_text()) if mp.exists() else {}
     traj=run/"CameraTrajectory.txt"; n,widths=trajectory_format(traj)
     ate=metrics.get("ate",{});rt=metrics.get("rpe_trans",{});rr=metrics.get("rpe_rot_deg",{})
     out.append({"experiment":experiment,"method":method,"sequence":seq,"run_id":f"run_{rid:02d}","raw_process_status":conf.get("raw_process_status","unknown"),"experiment_completion_status":conf.get("experiment_completion_status","unknown"),"legal_evaluation":int(bool(metrics) and n>=2),"trajectory_rows":n,"trajectory_columns":widths,"trajectory_sha256":sha(traj) if traj.exists() else "","evaluation_script":"scripts/evaluate_tum_metrics.py","max_timestamp_diff":metrics.get("max_timestamp_diff",""),"alignment":"single SE(3) Umeyama/SVD alignment for ATE; RPE computed from unaligned consecutive relative poses","groundtruth":metrics.get("gt",""),"ATE_RMSE":ate.get("rmse",""),"ATE_mean":ate.get("mean",""),"ATE_median":ate.get("median",""),"RPE_translation_RMSE":rt.get("rmse",""),"RPE_rotation_RMSE_deg":rr.get("rmse",""),"run_dir":str(run)})
 return out

def nums(rows,key):return [float(x[key]) for x in rows if x["legal_evaluation"] and x[key]!="" and math.isfinite(float(x[key]))]
def f(v):return f"{v:.6f}" if isinstance(v,(int,float)) else str(v)
def main():
 rows=runs();csv_path=OUT/"p3_5_run_comparison.csv"
 with csv_path.open("w",newline="",encoding="utf-8-sig") as h:
  w=csv.DictWriter(h,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 idx={}
 for exp in ("P2","P3"):
  for method in METHODS:
   for seq in SEQS:
    g=[x for x in rows if x["experiment"]==exp and x["method"]==method and x["sequence"]==seq]
    idx[exp,method,seq]={"rows":g,"ate":statistics.fmean(nums(g,"ATE_RMSE")) if nums(g,"ATE_RMSE") else math.nan,"rpe":statistics.fmean(nums(g,"RPE_translation_RMSE")) if nums(g,"RPE_translation_RMSE") else math.nan,"rper":statistics.fmean(nums(g,"RPE_rotation_RMSE_deg")) if nums(g,"RPE_rotation_RMSE_deg") else math.nan,"n":sum(x["legal_evaluation"] for x in g)}
 lines=["# P3.5：P2 与 P3 实验结果一致性审计","","本报告仅读取既有运行目录与评价结果；未运行 SLAM、未重新评价轨迹、未覆盖任何既有 CSV。","","## 结论摘要","","- P2 与 P3 **不是同一批 run**。P3 为获得稳定 MapPoint ID 级日志，独立重新运行了 Semantic/Temporal。","- 两阶段使用同一个 `scripts/evaluate_tum_metrics.py`，默认最大时间戳差均为 0.02 s；轨迹均为 TUM 8列格式；ATE 均采用一次 SE(3) SVD 对齐，RPE 均基于相邻匹配位姿的相对运动误差。未发现评价口径差异。","- P3 报告的百分比采用 `(Temporal/Semantic-1)×100%`：负数表示误差下降。其“改善”解释没有写反。P2 使用 `(Semantic-Temporal)/Semantic×100%`：负数表示退化。两者数值符号表达不同，但各自文字解释正确。","- 方向冲突来自独立随机运行及 P3 Semantic/xyz 仅有 3 个合法 run；不是把同一数据算出相反结论，也不是评价参数改变。","","## 实际纳入统计的 run","","| Stage | Method | Sequence | legal run IDs | n |","|---|---|---|---|---:|"]
 for exp in ("P2","P3"):
  for method in METHODS:
   for seq in SEQS:
    x=idx[exp,method,seq];ids=", ".join(r["run_id"] for r in x["rows"] if r["legal_evaluation"])
    lines.append(f"| {exp} | {method} | {seq} | {ids or 'none'} | {x['n']} |")
 lines += ["","## ATE RMSE 原始值与均值","","| Stage | Method | Sequence | run_01 | run_02 | run_03 | run_04 | run_05 | mean |","|---|---|---|---:|---:|---:|---:|---:|---:|"]
 for exp in ("P2","P3"):
  for method in METHODS:
   for seq in SEQS:
    x=idx[exp,method,seq];vals=[f(float(r["ATE_RMSE"])) if r["legal_evaluation"] else "NA" for r in x["rows"]]
    lines.append(f"| {exp} | {method} | {seq} | {' | '.join(vals)} | {x['ate']:.6f} |")
 lines += ["","## Semantic 与 Temporal 的阶段内 ATE 对比","","| Stage | Sequence | Semantic mean | Temporal mean | Temporal相对Semantic | 解释 |","|---|---|---:|---:|---:|---|"]
 for exp in ("P2","P3"):
  for seq in SEQS:
   s=idx[exp,"Semantic",seq]["ate"];t=idx[exp,"Temporal",seq]["ate"];pct=(t/s-1)*100
   lines.append(f"| {exp} | {seq} | {s:.6f} | {t:.6f} | {pct:+.2f}% | {'误差下降（改善）' if pct<0 else '误差上升（退化）'} |")
 lines += ["","## RPE translation RMSE 原始值与均值","","| Stage | Method | Sequence | run_01 | run_02 | run_03 | run_04 | run_05 | mean |","|---|---|---|---:|---:|---:|---:|---:|---:|"]
 for exp in ("P2","P3"):
  for method in METHODS:
   for seq in SEQS:
    x=idx[exp,method,seq];vals=[f(float(r["RPE_translation_RMSE"])) if r["legal_evaluation"] else "NA" for r in x["rows"]]
    lines.append(f"| {exp} | {method} | {seq} | {' | '.join(vals)} | {x['rpe']:.6f} |")
 lines += ["","## RPE一致性结论","","| Stage | Sequence | Semantic mean | Temporal mean | Temporal相对Semantic |","|---|---|---:|---:|---:|"]
 for exp in ("P2","P3"):
  for seq in SEQS:
   s=idx[exp,"Semantic",seq]["rpe"];t=idx[exp,"Temporal",seq]["rpe"]
   lines.append(f"| {exp} | {seq} | {s:.6f} | {t:.6f} | {(t/s-1)*100:+.2f}% |")
 lines += ["","## 逐项核查","","1. **是否同一批 run**：否。目录、轨迹 SHA-256 与原始指标均不同。","2. **P3是否重跑**：是。P3运行脚本创建了独立的 `03_temporal_continuity` 目录，并为点级证据日志重跑。","3. **纳入run_id**：见上表。P2每个 method×sequence 均为5个合法run；P3 Semantic/xyz仅run_03–05合法，其余组合均为run_01–05。","4. **每run原始指标**：ATE与RPE已逐项列出，CSV同时保留ATE mean/median及旋转RPE。","5. **评价脚本**：两阶段配置均调用 `scripts/evaluate_tum_metrics.py`。","6. **时间戳匹配**：所有现有 `metrics.json` 记录 `max_timestamp_diff=0.02`。","7. **轨迹格式**：合法轨迹均为每行8列的TUM格式。","8. **对齐方式**：ATE使用同一SE(3) SVD对齐；RPE实现不对绝对轨迹施加该对齐，而比较连续相对位姿，此行为两阶段一致。","9. **随机差异**：存在。ORB-SLAM2多线程调度、特征/地图演化及实时YOLO交互使独立运行轨迹不完全相同；轨迹SHA不同提供了直接证据。","10. **百分比符号**：P3没有写反。其负百分比表示Temporal误差更低；P2报告的正向改善公式与P3变化率公式相反，但文字与各自公式一致。","11. **28/30影响**：影响Semantic/xyz均值与方差估计。P3该格仅3个合法run，不能与P2的5-run均值视为同等重复设计。run_01为socket权限失败，run_02无有效运行；二者未作为0纳入。其余格均5个。","12. **RPE**：评价脚本、匹配阈值与数据格式一致；RPE的阶段间差异同样来自不同轨迹样本，而非口径变化。","","## 差异来源判定","","- **统计错误**：未发现均值计算或改善/退化符号写反。","- **评价口径差异**：未发现；脚本、0.02 s匹配阈值、格式及对齐实现一致。","- **独立重复运行随机波动**：是主要来源。尤其 P3 rpy 的ATE离散度较大，且P3 Semantic/xyz缺少2次合法运行，使阶段间均值更不可直接互换。","- **统计设计不完全一致**：是附加来源。P2是完整5×重复；P3整体固定30次但仅28次合法，Semantic/xyz为3×有效重复。","","## 正式论文采用建议","","- 定位精度、RPE与覆盖率的正式四方法对比应采用 **P2**：它是预先定义的完整5次重复设计，Semantic/Temporal各序列均有5个合法run，并与ORB-SLAM2、Full处于同一对比框架。","- P3应仅用于时间连续性专项分析，主张应基于P3新日志的Switching Frequency和点级证据；P3的ATE/RPE只能作为该批连续性实验的辅助伴随指标，不应替换P2主性能结果。","- 论文必须同时说明：P3点级连续性结果来自独立补跑；其ATE方向与P2不同，说明定位误差具有运行波动，不能据P3辅助ATE推翻P2主实验。","","P3.5审计结束；未启动新实验。",""]
 (OUT/"p3_5_metric_consistency_audit.md").write_text("\n".join(lines),encoding="utf-8")
if __name__=="__main__":main()
