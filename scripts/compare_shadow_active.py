#!/usr/bin/env python3

"""Generate the Paper2 Shadow-versus-Active ATE comparison table."""

import argparse
import csv
from pathlib import Path


SEQUENCES = (
    "fr3_walking_xyz",
    "fr3_walking_rpy",
    "fr3_walking_halfsphere",
)


def read_ate(path):
    values = {}
    with path.open("r", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            values[row["sequence"]] = float(row["ATE_RMSE"])
    return values


def main():
    project_root = Path(__file__).resolve().parents[1]
    results_root = project_root / "experiment_new" / "paper2" / "results"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--shadow",
        type=Path,
        default=results_root / "final" / "trajectory_evaluation.csv",
    )
    parser.add_argument(
        "--active",
        type=Path,
        default=results_root / "active" / "trajectory_evaluation.csv",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=results_root / "active" / "table_shadow_vs_active.tex",
    )
    args = parser.parse_args()

    shadow = read_ate(args.shadow)
    active = read_ate(args.active)
    missing = [name for name in SEQUENCES if name not in shadow or name not in active]
    if missing:
        raise SystemExit("missing ATE results for: {}".format(", ".join(missing)))

    rows = []
    for sequence in SEQUENCES:
        improvement = 100.0 * (shadow[sequence] - active[sequence]) / shadow[sequence]
        rows.append((sequence[4:].replace("_", "\\_"), shadow[sequence], active[sequence], improvement))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as stream:
        stream.write("% Positive improvement means that Active Mode reduced ATE RMSE.\n")
        stream.write("\\begin{table}[t]\n")
        stream.write("  \\centering\n")
        stream.write("  \\caption{Shadow and Active Mode trajectory accuracy comparison.}\n")
        stream.write("  \\label{tab:shadow_vs_active}\n")
        stream.write("  \\begin{tabular}{lrrr}\n")
        stream.write("    \\toprule\n")
        stream.write("    Sequence & Shadow ATE (m) & Active ATE (m) & Improvement (\\%) \\\\\n")
        stream.write("    \\midrule\n")
        for sequence, shadow_ate, active_ate, improvement in rows:
            stream.write(
                "    {} & {:.6f} & {:.6f} & {:+.2f} \\\\\n".format(
                    sequence, shadow_ate, active_ate, improvement
                )
            )
        stream.write("    \\bottomrule\n")
        stream.write("  \\end{tabular}\n")
        stream.write("\\end{table}\n")
    print("Wrote {}".format(args.output.resolve()))


if __name__ == "__main__":
    main()
