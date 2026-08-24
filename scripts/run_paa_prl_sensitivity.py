#!/usr/bin/env python3
"""Run the independent Draft-9 temporal-parameter sensitivity protocol."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from paa_prl_common import (REPO, SETTINGS, association_path, dataset_path,
                            git_output, parse_semantic_defaults, sha256, write_json)


FACTORS = (0.5, 0.75, 1.0, 1.25, 1.5)
PARAMETERS = ("threshold", "increment", "decay")
BASELINE_COMMIT = "94071a20d4ce220d225654e7a2b59c90d684bb58"


def timestamp() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def command_for(case_dir: Path, sequence: str, device: str,
                parameter: str, factor: float,
                defaults: dict[str, dict[str, float]]) -> list[str]:
    ordinary = defaults[parameter]["normal_dynamic_class"] * factor
    person = defaults[parameter]["person"] * factor
    command = [
        sys.executable, str(REPO / "scripts/run_tum_rgbd_experiment.py"),
        "--sequence", sequence, "--method", "dynamic",
        "--dataset", str(dataset_path(sequence)),
        "--association", str(association_path(sequence)),
        "--settings", str(SETTINGS), "--out-dir", str(case_dir),
        "--device", device,
    ]
    flags = {
        "threshold": ("--dynamic-theta", "--person-dynamic-theta"),
        "increment": ("--dynamic-increment", "--person-dynamic-increment"),
        "decay": ("--dynamic-lambda", "--person-dynamic-lambda"),
    }[parameter]
    return command + [flags[0], str(ordinary), flags[1], str(person)]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=REPO / "results/paa_prl_sensitivity")
    parser.add_argument("--sequence", default="fr3_walking_xyz",
                        choices=["fr3_walking_xyz"])
    parser.add_argument("--runs", type=int, default=1)
    parser.add_argument("--device", default="0")
    parser.add_argument("--execute", action="store_true",
                        help="Without this flag only write the auditable experiment matrix.")
    args = parser.parse_args()
    defaults = parse_semantic_defaults()
    expected = {"threshold": (3.0, 2.0), "increment": (1.0, 1.0),
                "decay": (0.95, 0.90)}
    for name, values in expected.items():
        actual = (defaults[name]["normal_dynamic_class"], defaults[name]["person"])
        if actual != values:
            raise RuntimeError(f"Draft-9 frozen {name} mismatch: expected {values}, parsed {actual}")

    root = args.root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    matrix = []
    for parameter in PARAMETERS:
        for factor in FACTORS:
            for run_id in range(1, args.runs + 1):
                case_dir = root / parameter / f"factor_{factor:g}" / f"run_{run_id:02d}"
                command = command_for(case_dir, args.sequence, args.device,
                                      parameter, factor, defaults)
                row = {
                    "parameter": parameter, "factor": factor, "run_id": run_id,
                    "configuration": "Temporal", "sequence": args.sequence,
                    "defaults_parsed_from": str(REPO / "include/SemanticConfig.h"),
                    "defaults_parsed": defaults,
                    "ordinary_value": defaults[parameter]["normal_dynamic_class"] * factor,
                    "person_value": defaults[parameter]["person"] * factor,
                    "other_parameters": "unchanged Draft-9 defaults",
                    "baseline_commit": BASELINE_COMMIT,
                    "current_git_commit": git_output("rev-parse", "HEAD"),
                    "semantic_config_sha256": sha256(REPO / "include/SemanticConfig.h"),
                    "command": command, "case_dir": str(case_dir),
                }
                matrix.append(row)
                if not args.execute:
                    continue
                if case_dir.exists():
                    raise RuntimeError(f"Refusing to overwrite sensitivity case: {case_dir}")
                case_dir.mkdir(parents=True)
                write_json(case_dir / "sensitivity_metadata.json", row)
                env = os.environ.copy()
                env["ORB_SLAM2_SOCKET_PATH"] = (
                    f"/tmp/paa_prl_sensitivity_{parameter}_{factor:g}_{run_id}_{os.getpid()}.sock")
                started = timestamp()
                with (case_dir / "driver.log").open("w", encoding="utf-8") as log:
                    process = subprocess.run(command, cwd=REPO, env=env, stdout=log,
                                             stderr=subprocess.STDOUT, text=True)
                write_json(case_dir / "sensitivity_status.json", {
                    "status": "success" if process.returncode == 0 else "failed",
                    "return_code": process.returncode, "started_at": started,
                    "finished_at": timestamp(), "failed_run_preserved": process.returncode != 0,
                })
    write_json(root / "sensitivity_matrix.json", {
        "generated_at": timestamp(), "execute": args.execute,
        "defaults_parsed": defaults, "cases": matrix,
    })
    print(f"wrote {len(matrix)} cases to {root / 'sensitivity_matrix.json'}")
    if not args.execute:
        print("plan only; no sensitivity experiment was started")


if __name__ == "__main__":
    main()
