#!/usr/bin/env python3

"""Evaluate the latest complete Paper2 trajectories with evo."""

import argparse
import csv
import json
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path


SEQUENCES = (
    "fr3_walking_xyz",
    "fr3_walking_rpy",
    "fr3_walking_halfsphere",
    "fr3_sitting_xyz",
    "fr3_sitting_rpy",
    "fr3_sitting_halfsphere",
)
OUTPUT_NAME = "trajectory_evaluation.csv"


def latest_trajectory(final_root, sequence):
    candidates = list((final_root / sequence).glob("*/CameraTrajectory.txt"))
    for trajectory in final_root.glob("*/CameraTrajectory.txt"):
        run_log = trajectory.with_name("run.log")
        if not run_log.is_file():
            continue
        expected = "sequence_name={}".format(sequence)
        if expected in run_log.read_text(encoding="utf-8", errors="replace").splitlines():
            candidates.append(trajectory)
    return max(candidates, key=lambda path: path.stat().st_mtime) if candidates else None


def read_evo_stat(result_archive, name):
    with zipfile.ZipFile(str(result_archive)) as archive:
        stats = json.loads(archive.read("stats.json").decode("utf-8"))
    return float(stats[name])


def run_evo(command, archive):
    completed = subprocess.run(
        command + ["--save_results", str(archive)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "command failed ({}):\n{}".format(
                " ".join(command), completed.stdout.strip()
            )
        )


def evaluate(groundtruth, trajectory, temporary_root):
    ape_archive = temporary_root / "ape.zip"
    rpe_trans_archive = temporary_root / "rpe_trans.zip"
    rpe_rot_archive = temporary_root / "rpe_rot.zip"

    run_evo(
        ["evo_ape", "tum", str(groundtruth), str(trajectory), "--align"],
        ape_archive,
    )
    run_evo(
        [
            "evo_rpe",
            "tum",
            str(groundtruth),
            str(trajectory),
            "--align",
            "--pose_relation",
            "trans_part",
        ],
        rpe_trans_archive,
    )
    run_evo(
        [
            "evo_rpe",
            "tum",
            str(groundtruth),
            str(trajectory),
            "--align",
            "--pose_relation",
            "angle_deg",
        ],
        rpe_rot_archive,
    )
    return {
        "ATE_RMSE": read_evo_stat(ape_archive, "rmse"),
        "ATE_mean": read_evo_stat(ape_archive, "mean"),
        "RPE_trans": read_evo_stat(rpe_trans_archive, "rmse"),
        "RPE_rot": read_evo_stat(rpe_rot_archive, "rmse"),
    }


def main():
    project_root = Path(__file__).resolve().parents[1]
    default_final_root = (
        project_root / "experiment_new" / "paper2" / "results" / "final"
    )
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=default_final_root)
    parser.add_argument(
        "--dataset-root", type=Path, default=Path("/home/djn/datasets/TUMRGBD")
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    for executable in ("evo_ape", "evo_rpe"):
        if shutil.which(executable) is None:
            raise SystemExit("required executable not found: {}".format(executable))

    final_root = args.results.resolve()
    output_path = (args.output or final_root / OUTPUT_NAME).resolve()
    rows = []
    skipped = []

    for sequence in SEQUENCES:
        trajectory = latest_trajectory(final_root, sequence)
        groundtruth = (
            args.dataset_root
            / "rgbd_dataset_freiburg3_{}".format(sequence[4:])
            / "groundtruth.txt"
        )
        if trajectory is None:
            skipped.append("{}: CameraTrajectory.txt not found".format(sequence))
            continue
        if not groundtruth.is_file():
            skipped.append("{}: {} not found".format(sequence, groundtruth))
            continue

        with tempfile.TemporaryDirectory(prefix="paper2_evo_") as directory:
            metrics = evaluate(groundtruth, trajectory, Path(directory))
        row = {"sequence": sequence}
        row.update({name: "{:.9f}".format(value) for name, value in metrics.items()})
        rows.append(row)
        print("Evaluated {} from {}".format(sequence, trajectory.parent))

    fieldnames = ["sequence", "ATE_RMSE", "ATE_mean", "RPE_trans", "RPE_rot"]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    for message in skipped:
        print("Skipped {}".format(message))
    print("Wrote {} evaluations to {}".format(len(rows), output_path))


if __name__ == "__main__":
    main()
