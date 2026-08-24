#!/usr/bin/env python3
"""Generate paper CSV/LaTeX tables exclusively from experiment outputs."""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Callable

from paa_prl_common import REPO, write_json


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists() or not path.stat().st_size:
        return []
    with path.open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def value(row: dict[str, str], key: str) -> str:
    raw = row.get(key, "")
    if raw == "":
        return ""
    try:
        number = float(raw)
        return f"{number:.3f}" if math.isfinite(number) else ""
    except ValueError:
        return raw


def mean_std(row: dict[str, str], metric: str) -> str:
    mean = value(row, f"{metric}_mean")
    std = value(row, f"{metric}_std")
    return f"{mean} ± {std}" if mean and std else ""


def tex_escape(text: str) -> str:
    return (text.replace("\\", r"\textbackslash{}")
                .replace("_", r"\_").replace("%", r"\%")
                .replace("&", r"\&").replace("±", r"$\pm$"))


def emit(out: Path, stem: str, caption: str, headers: list[str],
         rows: list[list[str]]) -> None:
    csv_path = out / f"{stem}.csv"
    with csv_path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.writer(stream)
        writer.writerow(headers)
        writer.writerows(rows)
    alignment = "l" + "c" * (len(headers) - 1)
    lines = [r"\begin{table}[t]", r"\centering", rf"\caption{{{caption}}}",
             rf"\label{{tab:{stem}}}", rf"\begin{{tabular}}{{{alignment}}}",
             r"\hline", " & ".join(map(tex_escape, headers)) + r" \\", r"\hline"]
    lines.extend(" & ".join(tex_escape(cell) for cell in row) + r" \\" for row in rows)
    lines += [r"\hline", r"\end{tabular}", r"\end{table}"]
    (out / f"{stem}.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-root", type=Path, default=REPO / "results/paa_prl")
    parser.add_argument("--sensitivity-root", type=Path,
                        default=REPO / "results/paa_prl_sensitivity")
    parser.add_argument("--baseline-root", type=Path,
                        default=REPO / "results/paa_prl_baselines")
    parser.add_argument("--out", type=Path,
                        default=REPO / "results/paa_prl/paper_tables")
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    generated: list[str] = []
    skipped: dict[str, str] = {}
    summary_path = args.results_root / "summary/configuration_sequence_summary.csv"
    summaries = read_csv(summary_path)

    if summaries:
        common = lambda row: [row.get("configuration", ""), row.get("sequence", "")]
        emit(out, "accuracy_coverage", "Accuracy and Tracking Coverage",
             ["Configuration", "Sequence", "ATE RMSE", "RPE trans.", "RPE rot.", "TSR", "PMR"],
             [common(row) + [mean_std(row, metric) for metric in
              ("ATE_RMSE", "RPE_translation_RMSE", "RPE_rotation_RMSE_deg", "TSR", "PMR")]
              for row in summaries])
        generated.append("accuracy_coverage")
        emit(out, "ablation", "Configuration Ablation",
             ["Configuration", "Sequence", "ATE RMSE", "TSR", "PMR", "SF"],
             [common(row) + [mean_std(row, metric) for metric in
              ("ATE_RMSE", "TSR", "PMR", "SF")] for row in summaries])
        generated.append("ablation")
        emit(out, "runtime", "Runtime Breakdown and Throughput",
             ["Configuration", "Sequence", "Tracking", "Semantic", "Temporal", "Adapter", "Filter", "Tracking FPS", "End-to-end FPS"],
             [common(row) + [mean_std(row, metric) for metric in
              ("Tracking_time_per_frame", "Semantic_detection_time_per_frame",
               "Temporal_evidence_update_time_per_frame", "ObjectDynamic_Adapter_time_per_frame",
               "DynamicMapFilter_time_per_frame", "Tracking_FPS", "EndToEnd_FPS")]
              for row in summaries])
        generated.append("runtime")
        emit(out, "failure_tracking_completeness", "Tracking Completeness and Failures",
             ["Configuration", "Sequence", "Runs", "Success", "Incomplete", "Failure", "TSR", "Gaps"],
             [common(row) + [row.get(key, "") for key in
              ("n_fixed_runs", "n_process_success", "n_tracking_incomplete", "n_tracking_failure")]
              + [mean_std(row, "TSR"), mean_std(row, "tracking_gap_episodes")]
              for row in summaries])
        generated.append("failure_tracking_completeness")
    else:
        for name in ("accuracy_coverage", "ablation", "runtime", "failure_tracking_completeness"):
            skipped[name] = f"missing or empty {summary_path}"

    sensitivity_path = args.sensitivity_root / "summary/sensitivity_summary.csv"
    sensitivity = read_csv(sensitivity_path)
    if sensitivity:
        headers = list(sensitivity[0])
        emit(out, "sensitivity", "Temporal Parameter Sensitivity", headers,
             [[value(row, header) for header in headers] for row in sensitivity])
        generated.append("sensitivity")
    else:
        skipped["sensitivity"] = f"missing or empty {sensitivity_path}"

    baseline_path = args.baseline_root / "baseline_comparison.csv"
    baselines = read_csv(baseline_path)
    if baselines:
        headers = list(baselines[0])
        emit(out, "baseline_comparison", "Comparison with Independent Baselines", headers,
             [[value(row, header) for header in headers] for row in baselines])
        generated.append("baseline_comparison")
    else:
        skipped["baseline_comparison"] = f"missing or empty {baseline_path}; readiness is not a metric result"

    manifest = {"source_files": [str(summary_path), str(sensitivity_path), str(baseline_path)],
                "generated": generated, "skipped": skipped,
                "hardcoded_experiment_results": False}
    write_json(out / "table_generation_manifest.json", manifest)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
