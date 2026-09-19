#!/usr/bin/env python3
"""Aggregate the frozen V3 CLEAN/PERSISTENT TUM experiment outputs."""

import argparse
import bisect
import csv
import json
import math
import re
import statistics
from collections import defaultdict
from pathlib import Path


SEQUENCES = ("fr3_walking_xyz", "fr3_walking_static", "fr3_walking_rpy")
MODES = ("clean", "persistent")
REQUIRED_CONFIG = {
    "ACTIVE_MODE": "1",
    "BELIEF_ENABLED": "1",
    "RELIABILITY_ENABLED": "1",
    "LEGACY_TEMPORAL_WEIGHT_ENABLED": "0",
    "LEGACY_TEMPORAL_HARD_REJECTION_ENABLED": "0",
}


def fmean(xs):
    return statistics.fmean(xs) if xs else math.nan


def sample_std(xs):
    return statistics.stdev(xs) if len(xs) > 1 else 0.0


def percentile(xs, q):
    if not xs:
        return math.nan
    ys = sorted(xs)
    x = (len(ys) - 1) * q
    lo, hi = math.floor(x), math.ceil(x)
    return ys[lo] if lo == hi else ys[lo] * (hi - x) + ys[hi] * (x - lo)


def ranks(xs):
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    out = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i + 1
        while j < len(order) and xs[order[j]] == xs[order[i]]:
            j += 1
        rank = (i + 1 + j) / 2.0
        for k in range(i, j):
            out[order[k]] = rank
        i = j
    return out


def pearson(xs, ys):
    if len(xs) < 2:
        return math.nan
    mx, my = fmean(xs), fmean(ys)
    dx = [x - mx for x in xs]
    dy = [y - my for y in ys]
    den = math.sqrt(sum(x*x for x in dx) * sum(y*y for y in dy))
    return sum(x*y for x, y in zip(dx, dy)) / den if den else math.nan


def spearman(xs, ys):
    return pearson(ranks(xs), ranks(ys))


def read_assoc(path):
    vals = []
    with path.open() as f:
        for line in f:
            s = line.strip()
            if s and not s.startswith("#"):
                vals.append(float(s.split()[0]))
    return vals


def read_traj(path):
    vals = []
    with path.open() as f:
        for line in f:
            s = line.strip()
            if s and not s.startswith("#"):
                vals.append(float(s.split()[0]))
    return sorted(vals)


def coverage(assoc, traj, tolerance=0.02):
    present = []
    for t in assoc:
        i = bisect.bisect_left(traj, t)
        d = min([abs(traj[j] - t) for j in (i - 1, i) if 0 <= j < len(traj)], default=math.inf)
        present.append(d <= tolerance)
    gaps = 0
    inside_gap = False
    for ok in present:
        if not ok and not inside_gap:
            gaps += 1
            inside_gap = True
        elif ok:
            inside_gap = False
    valid = sum(present)
    return valid, gaps, valid / len(assoc), 1.0 - valid / len(assoc)


def write_csv(path, rows, fields=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = list(rows[0]) if rows else []
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def read_effective_belief(path, run_id):
    final = {}
    with path.open() as f:
        for row in csv.DictReader(f):
            key = (int(row["frame_id"]), int(row["map_point_id"]))
            final[key] = row
    histories = defaultdict(list)
    for row in final.values():
        item = {
            "run": run_id,
            "frame": int(row["frame_id"]),
            "mp": int(row["map_point_id"]),
            "z": int(float(row["observation"])),
            "p": float(row["after_observation_p"]),
            "u": float(row["after_observation_u"]),
            "r": float(row["final_reliability"]),
            "raw": float(row["raw_conflict"]),
            "persistent": float(row["persistent_conflict"]),
            "h": float(row["persistence_after"]),
        }
        histories[item["mp"]].append(item)
    effective = []
    mp_info = []
    for mp, hist in histories.items():
        hist.sort(key=lambda x: x["frame"])
        switches = sum(a["z"] != b["z"] for a, b in zip(hist, hist[1:]))
        kind = "stable" if len(hist) >= 6 and switches == 0 else (
            "conflicting" if len(hist) >= 6 and switches >= 3 else "other")
        mp_info.append({"run": run_id, "mp": mp, "observations": len(hist), "switches": switches,
                        "adjacent_pairs": max(0, len(hist)-1), "kind": kind})
        for age, item in enumerate(hist, 1):
            item["age"] = age
            item["kind"] = kind
            effective.append(item)
    return effective, mp_info


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--associations", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    run_rows, all_obs, all_mps, integrity = [], [], [], []
    for seq in SEQUENCES:
        assoc = read_assoc(args.associations / f"{seq}_associate.txt")
        for mode in MODES:
            for run_num in range(1, 4):
                run_id = f"run_{run_num:02d}"
                d = args.root / seq / mode / run_id
                required = [d/"CameraTrajectory.txt", d/"slam.log", d/"belief_updates.csv",
                            d/"ablation_frames.csv", d/"eval/metrics.json"]
                files_ok = all(p.is_file() and p.stat().st_size > 0 for p in required)
                log = (d/"slam.log").read_text(errors="replace")
                config_line = next((x for x in log.splitlines() if "[BeliefConfiguration]" in x), "")
                cfg = dict(re.findall(r"([A-Z_]+)=([^ ]+)", config_line))
                expected_mode = mode.upper()
                config_ok = all(cfg.get(k) == v for k, v in REQUIRED_CONFIG.items()) and cfg.get("UNCERTAINTY_MODE") == expected_mode
                metrics = json.loads((d/"eval/metrics.json").read_text())
                valid, gaps, tsr, pmr = coverage(assoc, read_traj(d/"CameraTrajectory.txt"))
                with (d/"ablation_frames.csv").open() as f:
                    frames = list(csv.DictReader(f))
                initial = [float(x["initial_correspondences"]) for x in frames]
                inliers = [float(x["final_inliers"]) for x in frames]
                accept = [float(x["optimization_acceptance"]) for x in frames]
                obs, mps = read_effective_belief(d/"belief_updates.csv", run_id)
                for x in obs:
                    x.update(sequence=seq, mode=mode)
                for x in mps:
                    x.update(sequence=seq, mode=mode)
                all_obs.extend(obs)
                all_mps.extend(mps)
                finite = all(math.isfinite(x[k]) for x in obs for k in ("p", "u", "r", "raw", "persistent", "h"))
                bounded = all(0 <= x[k] <= 1 for x in obs for k in ("p", "u", "r", "raw", "persistent", "h"))
                run_rows.append({
                    "sequence": seq, "mode": mode, "run": run_id,
                    "ATE_RMSE": metrics["ate"]["rmse"],
                    "RPE_translation": metrics["rpe_trans"]["rmse"],
                    "RPE_rotation_deg": metrics["rpe_rot_deg"]["rmse"],
                    "TSR": tsr, "PMR": pmr, "gaps": gaps,
                    "initial_correspondences": fmean(initial), "final_inliers": fmean(inliers),
                    "optimization_acceptance": fmean(accept), "valid_poses": valid,
                    "association_frames": len(assoc), "frame_log_rows": len(frames),
                    "belief_observations": len(obs), "belief_mappoints": len(mps),
                    "files_ok": int(files_ok), "config_ok": int(config_ok),
                    "finite": int(finite), "bounded": int(bounded),
                })
                integrity.append({"sequence": seq, "mode": mode, "run": run_id,
                                  "files_ok": files_ok, "config_ok": config_ok,
                                  "finite": finite, "bounded": bounded, "configuration": cfg})

    write_csv(args.out/"per_run_metrics.csv", run_rows)
    summary = []
    metric_names = ("ATE_RMSE", "RPE_translation", "RPE_rotation_deg", "TSR", "PMR", "gaps",
                    "initial_correspondences", "final_inliers", "optimization_acceptance")
    for seq in SEQUENCES:
        for mode in MODES:
            rows = [r for r in run_rows if r["sequence"] == seq and r["mode"] == mode]
            out = {"sequence": seq, "mode": mode, "n": len(rows)}
            for name in metric_names:
                vals = [float(r[name]) for r in rows]
                out[name+"_mean"] = fmean(vals)
                out[name+"_std"] = sample_std(vals)
            summary.append(out)
    write_csv(args.out/"slam_summary.csv", summary)
    summary_index = {(x["sequence"], x["mode"]): x for x in summary}
    comparisons = []
    for seq in SEQUENCES:
        c, p = summary_index[seq,"clean"], summary_index[seq,"persistent"]
        row = {"sequence": seq}
        for name in metric_names:
            cv, pv = c[name+"_mean"], p[name+"_mean"]
            row[name+"_difference"] = pv-cv
            row[name+"_relative_percent"] = (pv/cv-1)*100 if cv else math.nan
        comparisons.append(row)
    write_csv(args.out/"slam_mode_comparison.csv", comparisons)

    representation, age_rows, activation, prevalence = [], [], [], []
    for seq in SEQUENCES:
        for mode in MODES:
            obs = [x for x in all_obs if x["sequence"] == seq and x["mode"] == mode]
            mps = [x for x in all_mps if x["sequence"] == seq and x["mode"] == mode]
            for kind in ("stable", "conflicting"):
                z = [x for x in obs if x["kind"] == kind]
                q = [x for x in mps if x["kind"] == kind]
                representation.append({"sequence": seq, "mode": mode, "history": kind,
                    "mappoint_count": len(q), "observation_count": len(z),
                    "mean_u": fmean([x["u"] for x in z]), "mean_reliability": fmean([x["r"] for x in z]),
                    "mean_h": fmean([x["h"] for x in z]), "mean_raw_conflict": fmean([x["raw"] for x in z]),
                    "mean_persistent_conflict": fmean([x["persistent"] for x in z])})
            stable = [x for x in obs if x["kind"] == "stable"]
            for label, pred in (("1-5", lambda k: k <= 5), ("6-10", lambda k: 6 <= k <= 10), (">10", lambda k: k > 10)):
                z = [x for x in stable if pred(x["age"])]
                age_rows.append({"sequence": seq, "mode": mode, "age": label, "count": len(z),
                    "mean_u": fmean([x["u"] for x in z]), "mean_reliability": fmean([x["r"] for x in z]),
                    "mean_raw_conflict": fmean([x["raw"] for x in z]),
                    "mean_persistent_conflict": fmean([x["persistent"] for x in z])})
            hs = [x["h"] for x in obs]
            activation.append({"sequence": seq, "mode": mode, "count": len(hs),
                "mean_h": fmean(hs), "median_h": percentile(hs, .5), "P90_h": percentile(hs, .9),
                "P95_h": percentile(hs, .95), "h_ge_0.3_ratio": sum(x >= .3 for x in hs)/len(hs),
                "h_ge_0.5_ratio": sum(x >= .5 for x in hs)/len(hs)})
            pairs = sum(x["adjacent_pairs"] for x in mps)
            switches = sum(x["switches"] for x in mps)
            prevalence.append({"sequence": seq, "mode": mode,
                "stable_mappoints": sum(x["kind"] == "stable" for x in mps),
                "conflicting_mappoints": sum(x["kind"] == "conflicting" for x in mps),
                "stable_observations": sum(x["kind"] == "stable" for x in obs),
                "conflicting_observations": sum(x["kind"] == "conflicting" for x in obs),
                "z_switches": switches, "adjacent_pairs": pairs,
                "switch_rate": switches/pairs if pairs else math.nan})
    write_csv(args.out/"representation_summary.csv", representation)
    write_csv(args.out/"stable_age_summary.csv", age_rows)
    age_index = {(x["sequence"], x["mode"], x["age"]): x for x in age_rows}
    age_deltas = []
    for seq in SEQUENCES:
        for age in ("1-5", "6-10", ">10"):
            c, p = age_index[seq,"clean",age], age_index[seq,"persistent",age]
            age_deltas.append({"sequence": seq, "age": age,
                "clean_mean_u": c["mean_u"], "persistent_mean_u": p["mean_u"],
                "delta_u": p["mean_u"]-c["mean_u"],
                "clean_mean_reliability": c["mean_reliability"],
                "persistent_mean_reliability": p["mean_reliability"],
                "clean_raw_conflict": c["mean_raw_conflict"], "persistent_raw_conflict": p["mean_raw_conflict"],
                "clean_persistent_conflict": c["mean_persistent_conflict"],
                "persistent_persistent_conflict": p["mean_persistent_conflict"]})
    write_csv(args.out/"stable_age_comparison.csv", age_deltas)
    write_csv(args.out/"persistence_activation.csv", activation)
    write_csv(args.out/"switching_prevalence.csv", prevalence)

    rep_index = {(x["sequence"], x["mode"], x["history"]): x for x in representation}
    selectivity = []
    for seq in SEQUENCES:
        ds = rep_index[seq,"persistent","stable"]["mean_u"] - rep_index[seq,"clean","stable"]["mean_u"]
        dc = rep_index[seq,"persistent","conflicting"]["mean_u"] - rep_index[seq,"clean","conflicting"]["mean_u"]
        selectivity.append({"sequence": seq, "delta_u_stable": ds, "delta_u_conflicting": dc,
                            "selectivity_S": dc-ds})
    write_csv(args.out/"selectivity.csv", selectivity)

    calibration, quartiles = [], []
    for seq in SEQUENCES:
        for mode in MODES:
            obs = [x for x in all_obs if x["sequence"] == seq and x["mode"] == mode]
            brier = [(x["p"]-x["z"])**2 for x in obs]
            disagreement = [abs(x["z"]-x["p"]) for x in obs]
            calibration.append({"sequence": seq, "mode": mode, "count": len(obs),
                "brier_score": fmean(brier), "spearman_u_abs_z_minus_p": spearman([x["u"] for x in obs], disagreement)})
            ordered = sorted(zip(obs, brier), key=lambda t: t[0]["u"])
            n = len(ordered)
            for qi in range(4):
                part = ordered[qi*n//4:(qi+1)*n//4]
                quartiles.append({"sequence": seq, "mode": mode, "quartile": f"Q{qi+1}", "count": len(part),
                    "mean_u": fmean([x[0]["u"] for x in part]), "mean_brier": fmean([x[1] for x in part])})
    write_csv(args.out/"calibration.csv", calibration)
    write_csv(args.out/"calibration_quartiles.csv", quartiles)
    (args.out/"integrity.json").write_text(json.dumps(integrity, indent=2) + "\n")

    report = ["# Frozen V3 cross-sequence analysis", "",
              f"Runs: {len(run_rows)}/18; complete artifacts: {sum(x['files_ok'] for x in integrity)}/18; "
              f"configuration valid: {sum(x['config_ok'] for x in integrity)}/18; finite/bounded: "
              f"{sum(x['finite'] and x['bounded'] for x in integrity)}/18.", "", "## Selectivity", "",
              "| Sequence | delta U stable | delta U conflicting | S |", "|---|---:|---:|---:|"]
    for x in selectivity:
        report.append(f"| {x['sequence']} | {x['delta_u_stable']:.6f} | {x['delta_u_conflicting']:.6f} | {x['selectivity_S']:.6f} |")
    report += ["", "The observation label z is an internal system label, not independent dynamic-state ground truth.", ""]
    (args.out/"report.md").write_text("\n".join(report))


if __name__ == "__main__":
    main()
