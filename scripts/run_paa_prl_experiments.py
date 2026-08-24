#!/usr/bin/env python3
"""Run the four PAA/PRL configurations without overwriting any attempt."""

from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from paa_prl_common import (BUILD_VARIANTS, CONFIGURATIONS, CONFIGURATION_SPECS,
                            REPO, SEQUENCE_NAMES, SETTINGS, association_path,
                            data_lines, dataset_path, git_output,
                            parse_semantic_defaults, sha256, write_json)


RUNNER = REPO / "scripts/run_tum_rgbd_experiment.py"


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def build_variant(variant: str, root: Path, jobs: int) -> Dict[str, object]:
    shadow, active = BUILD_VARIANTS[variant]
    build_dir = REPO / f"build_paa_prl_{variant}"
    flags = (f"-DENABLE_OBJECT_DYNAMIC_SHADOW_MODE={shadow} "
             f"-DENABLE_OBJECT_DYNAMIC_ACTIVE_MODE={active}")
    log = root / "metadata" / f"build_{variant}.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    commands = [
        ["cmake", "-S", str(REPO), "-B", str(build_dir), f"-DCMAKE_CXX_FLAGS={flags}"],
        ["cmake", "--build", str(build_dir), "--clean-first", f"-j{jobs}",
         "--target", "rgbd_tum"],
    ]
    with log.open("w", encoding="utf-8") as stream:
        for command in commands:
            stream.write("COMMAND: " + " ".join(command) + "\n")
            stream.flush()
            subprocess.run(command, cwd=REPO, stdout=stream, stderr=subprocess.STDOUT,
                           text=True, check=True)
    binary = REPO / "Examples/RGB-D/rgbd_tum"
    library = REPO / "lib/libORB_SLAM2.so"
    result = {"variant": variant, "shadow": shadow, "active": active,
              "cmake_cxx_flags": flags, "build_dir": str(build_dir),
              "binary_sha256": sha256(binary), "library_sha256": sha256(library),
              "built_at": now()}
    write_json(root / "metadata" / f"build_{variant}.json", result)
    return result


def next_attempt(run_dir: Path, retry_failed: bool, force_new_attempt: bool) -> Path | None:
    attempts = sorted(path for path in run_dir.glob("attempt_*") if path.is_dir())
    if not attempts:
        return run_dir / "attempt_01"
    if force_new_attempt:
        return run_dir / f"attempt_{len(attempts) + 1:02d}"
    for attempt in attempts:
        status = attempt / "status.json"
        if status.exists() and json.loads(status.read_text()).get("status") == "success":
            return None
    if not retry_failed:
        return None
    return run_dir / f"attempt_{len(attempts) + 1:02d}"


def validate_input(sequence: str) -> tuple[Path, Path]:
    dataset = dataset_path(sequence)
    association = association_path(sequence)
    missing = [path for path in (dataset / "rgb.txt", dataset / "depth.txt",
                                  dataset / "groundtruth.txt", association)
               if not path.exists() or not path.stat().st_size]
    if missing:
        raise RuntimeError(f"{sequence} missing input(s): {', '.join(map(str, missing))}")
    return dataset, association


def run_attempt(root: Path, configuration: str, sequence: str, run_id: int,
                device: str, build_info: Dict[str, object], retry_failed: bool,
                force_new_attempt: bool) -> None:
    run_dir = root / configuration / sequence / f"run_{run_id:02d}"
    attempt = next_attempt(run_dir, retry_failed, force_new_attempt)
    if attempt is None:
        print(f"SKIP preserved run: {run_dir}", flush=True)
        return
    dataset, association = validate_input(sequence)
    attempt.mkdir(parents=True, exist_ok=False)
    spec = CONFIGURATION_SPECS[configuration]
    defaults = parse_semantic_defaults()
    socket_path = Path(f"/tmp/paa_prl_{configuration.lower().replace('-', '_')}_{sequence}_{run_id:02d}_{os.getpid()}.sock")
    command = [
        sys.executable, str(RUNNER), "--sequence", sequence,
        "--method", str(spec["runner_method"]), "--dataset", str(dataset),
        "--association", str(association), "--settings", str(SETTINGS),
        "--out-dir", str(attempt), "--device", device,
    ]
    config = {
        "protocol": "PAA/PRL Draft 9 extension", "configuration": configuration,
        "configuration_spec": spec, "sequence": sequence, "run_id": run_id,
        "attempt_id": attempt.name, "started_at": now(), "command": command,
        "dataset": str(dataset), "association": str(association),
        "association_rows": data_lines(association), "settings": str(SETTINGS),
        "git_commit": git_output("rev-parse", "HEAD"),
        "git_status_short": git_output("status", "--short"),
        "semantic_defaults_parsed": defaults, "parameter_overrides": {},
        "runtime_instrumentation_status": "component timing expected; verified after run",
        "runtime_warmup_excluded_frames_actual": None,
        "runtime_warmup_excluded_frames_required": 30,
        "trajectory_evaluation_scope": "all frames; runtime warm-up never removes trajectory frames",
        "build": build_info,
        "pipeline_script_hashes": {
            name: sha256(REPO / "scripts" / name)
            for name in ("paa_prl_common.py", "run_paa_prl_experiments.py",
                         "run_tum_rgbd_experiment.py", "evaluate_tum_metrics.py")
        },
        "hashes": {"settings": sha256(SETTINGS), "association": sha256(association),
                   "yolo_weights": sha256(REPO / "yolov5_RemoveDynamic/weights/yolov5s.pt")},
    }
    write_json(attempt / "run_config.json", config)
    env = os.environ.copy()
    env["ORB_SLAM2_SOCKET_PATH"] = str(socket_path)
    if configuration != "ORB-SLAM2":
        env["ORB_SLAM2_MAPPOINT_EVIDENCE_LOG"] = str(attempt / "mappoint_evidence_raw.csv")
    else:
        env.pop("ORB_SLAM2_MAPPOINT_EVIDENCE_LOG", None)
    for variable in ("ORB_SLAM2_DYNAMIC_LAMBDA", "ORB_SLAM2_DYNAMIC_THETA",
                     "ORB_SLAM2_PERSON_DYNAMIC_THETA", "ORB_SLAM2_DYNAMIC_INCREMENT",
                     "ORB_SLAM2_PERSON_DYNAMIC_INCREMENT"):
        env.pop(variable, None)
    start = time.monotonic()
    print(f"RUN {configuration}/{sequence}/run_{run_id:02d}/{attempt.name}", flush=True)
    with (attempt / "driver.stdout.log").open("w", encoding="utf-8") as stdout, \
         (attempt / "driver.stderr.log").open("w", encoding="utf-8") as stderr:
        process = subprocess.run(command, cwd=REPO, env=env, stdout=stdout, stderr=stderr,
                                 text=True)
    elapsed = time.monotonic() - start
    trajectory = attempt / "CameraTrajectory.txt"
    metrics = attempt / "eval/metrics.json"
    success = process.returncode == 0 and trajectory.exists() and trajectory.stat().st_size > 0 and metrics.exists()
    runtime_summary = attempt / "runtime_summary.csv"
    runtime_breakdown = attempt / "runtime_breakdown.csv"
    timing_complete = runtime_summary.exists() and runtime_breakdown.exists()
    status = {"status": "success" if success else "failed", "return_code": process.returncode,
              "finished_at": now(), "wall_time_seconds": elapsed,
              "trajectory_exists": trajectory.exists(), "metrics_exists": metrics.exists(),
              "failure_preserved": not success,
              "runtime_component_reports_exist": timing_complete}
    write_json(attempt / "status.json", status)
    config.update({"finished_at": status["finished_at"], "return_code": process.returncode,
                   "status": status["status"], "wall_time_seconds": elapsed,
                   "runtime_instrumentation_status":
                       "component timing available" if timing_complete else "component timing missing",
                   "runtime_warmup_excluded_frames_actual": 30 if timing_complete else 0})
    write_json(attempt / "run_config.json", config)
    try:
        socket_path.unlink()
    except FileNotFoundError:
        pass
    print(f"DONE {status['status']} rc={process.returncode}: {attempt}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=REPO / "results/paa_prl")
    parser.add_argument("--sequences", nargs="+", choices=SEQUENCE_NAMES)
    parser.add_argument("--all-sequences", action="store_true")
    parser.add_argument("--configurations", nargs="+", choices=CONFIGURATIONS,
                        default=list(CONFIGURATIONS))
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--device", default="0")
    parser.add_argument("--jobs", type=int, default=8)
    parser.add_argument("--build-only", action="store_true")
    parser.add_argument("--no-build", action="store_true")
    parser.add_argument("--retry-failed", action="store_true")
    parser.add_argument("--force-new-attempt", action="store_true",
                        help="Append an audited attempt even when a success exists; never overwrites.")
    args = parser.parse_args()
    if args.runs < 1:
        parser.error("--runs must be positive")
    if not args.all_sequences and not args.sequences and not args.build_only:
        parser.error("provide --sequences or --all-sequences")
    sequences = list(SEQUENCE_NAMES if args.all_sequences else (args.sequences or []))
    root = args.root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    environment = {"created_at": now(), "git_commit": git_output("rev-parse", "HEAD"),
                   "git_status_short": git_output("status", "--short"),
                   "host": platform.node(), "platform": platform.platform(),
                   "python": sys.version, "configurations": CONFIGURATION_SPECS,
                   "semantic_defaults_parsed": parse_semantic_defaults(),
                   "runtime_instrumentation_status": "component timing enabled in rgbd_tum",
                   "runtime_warmup_excluded_frames_actual": 30,
                   "runtime_warmup_excluded_frames_required": 30}
    write_json(root / "metadata/experiment_environment.json", environment)

    variants = []
    for configuration in args.configurations:
        variant = str(CONFIGURATION_SPECS[configuration]["build_variant"])
        if variant not in variants:
            variants.append(variant)
    for variant in variants:
        info_path = root / "metadata" / f"build_{variant}.json"
        if args.no_build:
            if not info_path.exists():
                raise RuntimeError(f"--no-build requested but build manifest is missing: {info_path}")
            build_info = json.loads(info_path.read_text())
            current_binary = sha256(REPO / "Examples/RGB-D/rgbd_tum")
            current_library = sha256(REPO / "lib/libORB_SLAM2.so")
            if current_binary != build_info.get("binary_sha256") or current_library != build_info.get("library_sha256"):
                raise RuntimeError(
                    f"--no-build artifact mismatch for {variant}; rebuild before running "
                    f"(binary={current_binary}, library={current_library})"
                )
        else:
            build_info = build_variant(variant, root, args.jobs)
        if args.build_only:
            continue
        for configuration in args.configurations:
            if CONFIGURATION_SPECS[configuration]["build_variant"] != variant:
                continue
            for sequence in sequences:
                for run_id in range(1, args.runs + 1):
                    run_attempt(root, configuration, sequence, run_id, args.device,
                                build_info, args.retry_failed, args.force_new_attempt)


if __name__ == "__main__":
    main()
