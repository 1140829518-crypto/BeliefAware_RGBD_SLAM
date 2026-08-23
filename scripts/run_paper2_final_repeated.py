#!/usr/bin/env python3
"""Run the final repeated Paper2 experiments without changing SLAM sources.

The driver creates isolated build phases for the compile-time ObjectDynamic
switches and delegates every real run to ``run_tum_rgbd_experiment.py``.
Existing result directories are never overwritten; failed attempts are kept.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
from datetime import datetime
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
RUNNER = REPO / "scripts/run_tum_rgbd_experiment.py"
SEQUENCES = {
    "fr3_walking_xyz": (
        Path("/home/djn/datasets/TUMRGBD/rgbd_dataset_freiburg3_walking_xyz"),
        REPO / "dataset_associations/fr3_walking_xyz_associate.txt",
    ),
    "fr3_walking_rpy": (
        Path("/home/djn/datasets/TUMRGBD/rgbd_dataset_freiburg3_walking_rpy"),
        REPO / "dataset_associations/fr3_walking_rpy_associate.txt",
    ),
    "fr3_walking_halfsphere": (
        Path("/home/djn/datasets/TUMRGBD/rgbd_dataset_freiburg3_walking_halfsphere"),
        REPO / "dataset_associations/fr3_walking_halfsphere_associate.txt",
    ),
}
SETTINGS = REPO / "Examples/RGB-D/TUM3.yaml"
BUILD_VARIANTS = {
    "no_object": (0, 0),
    "shadow": (1, 0),
    "full": (1, 1),
}


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def run_checked(cmd: list[str], *, log: Path | None = None) -> int:
    if log is None:
        return subprocess.run(cmd, cwd=REPO).returncode
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("w", encoding="utf-8") as stream:
        proc = subprocess.run(cmd, cwd=REPO, stdout=stream, stderr=subprocess.STDOUT, text=True)
    return proc.returncode


def build(variant: str, root: Path) -> None:
    shadow, active = BUILD_VARIANTS[variant]
    build_dir = REPO / f"build_final_repeated_{variant}"
    flags = (
        f"-DENABLE_OBJECT_DYNAMIC_SHADOW_MODE={shadow} "
        f"-DENABLE_OBJECT_DYNAMIC_ACTIVE_MODE={active}"
    )
    log = root / "metadata" / f"build_{variant}.log"
    configure = ["cmake", "-S", str(REPO), "-B", str(build_dir), f"-DCMAKE_CXX_FLAGS={flags}"]
    if run_checked(configure, log=log) != 0:
        raise RuntimeError(f"CMake configure failed for {variant}; see {log}")
    with log.open("a", encoding="utf-8") as stream:
        result = subprocess.run(
            ["cmake", "--build", str(build_dir), "-j8", "--target", "rgbd_tum"],
            cwd=REPO,
            stdout=stream,
            stderr=subprocess.STDOUT,
            text=True,
        )
    if result.returncode != 0:
        raise RuntimeError(f"Build failed for {variant}; see {log}")


def invoke(root: Path, group: str, method_label: str, runner_method: str,
           sequence: str, run_id: int, extra: list[str] | None = None) -> None:
    dataset, association = SEQUENCES[sequence]
    out = root / group / method_label / sequence / f"run_{run_id:02d}"
    if out.exists():
        config_path = out / "run_config.json"
        try:
            existing = json.loads(config_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            existing = {}
        if existing.get("status") == "success":
            print(f"SKIP existing success: {out}", flush=True)
            return
        suffix = datetime.now().strftime("%Y%m%d_%H%M%S")
        interrupted = out.with_name(f"{out.name}_interrupted_{suffix}")
        out.rename(interrupted)
        print(f"ARCHIVE incomplete: {interrupted}", flush=True)
    out.mkdir(parents=True)
    cmd = [
        sys.executable, str(RUNNER),
        "--sequence", sequence,
        "--method", runner_method,
        "--dataset", str(dataset),
        "--association", str(association),
        "--settings", str(SETTINGS),
        "--out-dir", str(out),
        "--device", "0",
    ]
    if extra:
        cmd.extend(extra)
    config = {
        "started_at": now(), "git_commit": git_commit(), "group": group,
        "method": method_label, "runner_method": runner_method,
        "sequence": sequence, "run_id": run_id, "dataset": str(dataset),
        "association": str(association), "settings": str(SETTINGS),
        "command": cmd, "environment_overrides": extra or [],
    }
    (out / "run_config.json").write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    print(f"RUN {group}/{method_label}/{sequence}/run_{run_id:02d}", flush=True)
    proc = subprocess.run(cmd, cwd=REPO, text=True, capture_output=True)
    (out / "driver.stdout.log").write_text(proc.stdout, encoding="utf-8")
    (out / "driver.stderr.log").write_text(proc.stderr, encoding="utf-8")
    if (out / "slam.log").exists() and not (out / "run.log").exists():
        (out / "run.log").write_text((out / "slam.log").read_text(encoding="utf-8", errors="replace"), encoding="utf-8")
    config.update({"finished_at": now(), "return_code": proc.returncode,
                   "status": "success" if proc.returncode == 0 else "failed"})
    (out / "run_config.json").write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    print(f"DONE rc={proc.returncode}: {out}", flush=True)


def git_commit() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()


def write_metadata(root: Path) -> None:
    meta = root / "metadata"
    meta.mkdir(parents=True, exist_ok=True)
    status = subprocess.check_output(["git", "status", "--short"], cwd=REPO, text=True)
    information = {
        "created_at": now(), "git_commit": git_commit(), "git_status_short": status,
        "host": platform.node(), "platform": platform.platform(),
        "python": sys.version, "settings": str(SETTINGS),
        "evaluation": "scripts/evaluate_tum_metrics.py; max timestamp difference 0.02 s; SE(3) alignment",
        "final_method": "Full (semantic mode 2, ObjectDynamic shadow=1, active=1)",
        "ablation_full_reuse": "First three final Full repetitions are the Full ablation rows.",
    }
    (meta / "experiment_environment.json").write_text(json.dumps(information, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--phase", choices=["all", "no_object", "shadow", "full", "sensitivity"], default="all")
    args = parser.parse_args()
    root = args.root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    write_metadata(root)

    if args.phase in {"all", "no_object"}:
        build("no_object", root)
        for label, runner_method in (("Baseline", "orb"), ("Semantic", "hard"), ("Temporal", "dynamic")):
            for sequence in SEQUENCES:
                for run_id in range(1, 4):
                    invoke(root, "ablation", label, runner_method, sequence, run_id)

    if args.phase in {"all", "shadow"}:
        build("shadow", root)
        for sequence in SEQUENCES:
            for run_id in range(1, 4):
                invoke(root, "ablation", "Object", "full", sequence, run_id)

    if args.phase in {"all", "full"}:
        build("full", root)
        for sequence in SEQUENCES:
            for run_id in range(1, 6):
                invoke(root, "final_performance", "Full", "full", sequence, run_id)

    if args.phase in {"all", "sensitivity"}:
        build("full", root)
        sequence = "fr3_walking_xyz"
        for idx, value in enumerate((0.70, 0.80, 0.85, 0.90, 0.95), 1):
            invoke(root, "sensitivity", f"lambda_{value:.2f}", "full", sequence, idx,
                   ["--dynamic-lambda", f"{value:.2f}"])
        for idx, value in enumerate((0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 5.0), 1):
            invoke(root, "sensitivity", f"theta_{value:.1f}", "full", sequence, idx,
                   ["--dynamic-theta", f"{value:.1f}", "--person-dynamic-theta", "1.0"])


if __name__ == "__main__":
    main()
