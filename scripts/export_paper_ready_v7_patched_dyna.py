#!/usr/bin/env python3
"""Export paper tables with patched Dyna-SLAM retry results."""

from __future__ import annotations

from pathlib import Path

import export_paper_ready_v5_completed_baselines as v5


OUT_DIR = Path("paper_ready_outputs_v7")
TABLE_DIR = OUT_DIR / "tables"


def add_baseline_rows(rows):
    v5.add_baseline_rows(rows)

    retry_overrides = {
        "fr3_walking_xyz": Path("baseline_runs_retry/dyna_slam/fr3_walking_xyz"),
        "fr1_desk": Path("baseline_runs_retry3_patched/dyna_slam/fr1_desk"),
        "fr3_walking_halfsphere": Path("baseline_runs_retry4_patched/dyna_slam/fr3_walking_halfsphere"),
    }
    for sequence, run_dir in retry_overrides.items():
        v5.add_metrics(rows, sequence, "Dyna-SLAM", "patched_retry", run_dir)


def main() -> None:
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    rows = v5.read_standard_rows(Path("evaluation_tables/standard_runs_summary.csv"))
    add_baseline_rows(rows)
    v5.write_summary(OUT_DIR / "summary_completed_baselines.csv", rows)
    for metric, title, stem in v5.METRICS:
        table = v5.build_table(rows, metric)
        v5.write_markdown(TABLE_DIR / f"{stem}.md", title, table)
        v5.write_csv(TABLE_DIR / f"{stem}.csv", table)
    print(f"Wrote patched Dyna-SLAM tables to {OUT_DIR}")


if __name__ == "__main__":
    main()
