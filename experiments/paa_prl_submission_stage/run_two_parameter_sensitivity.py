#!/usr/bin/env python3
"""Run decay and threshold one-factor sensitivity without changing defaults."""

from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))
from paa_prl_common import (SETTINGS, association_path, dataset_path, git_output,
                            parse_semantic_defaults, sha256, write_json)

FACTORS = (0.5, 0.75, 1.0, 1.25, 1.5)
PARAMETERS = ("decay", "threshold")


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path,
                        default=REPO / "results/paa_prl_submission_stage/sensitivity")
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--device", default="0")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if args.runs != 5:
        parser.error("formal sensitivity protocol requires exactly --runs 5")
    root = args.root.resolve(); root.mkdir(parents=True, exist_ok=True)
    defaults = parse_semantic_defaults()
    expected = {"threshold": {"normal_dynamic_class": 3.0, "person": 2.0},
                "increment": {"normal_dynamic_class": 1.0, "person": 1.0},
                "decay": {"normal_dynamic_class": 0.95, "person": 0.90}}
    if defaults != expected:
        raise RuntimeError(f"frozen default mismatch: parsed={defaults}, expected={expected}")
    sequence = "fr3_walking_xyz"
    cases = []
    for parameter in PARAMETERS:
        for factor in FACTORS:
            requested = {key: defaults[parameter][key] * factor for key in defaults[parameter]}
            effective = ({key: min(0.999, max(0.0, value)) for key, value in requested.items()}
                         if parameter == "decay" else requested.copy())
            for run_id in range(1, 6):
                out = root / parameter / f"factor_{factor:g}" / f"run_{run_id:02d}"
                command = [sys.executable, str(REPO / "scripts/run_tum_rgbd_experiment.py"),
                           "--sequence", sequence, "--method", "dynamic",
                           "--dataset", str(dataset_path(sequence)),
                           "--association", str(association_path(sequence)),
                           "--settings", str(SETTINGS), "--out-dir", str(out),
                           "--device", args.device]
                flags = {"decay": ("--dynamic-lambda", "--person-dynamic-lambda"),
                         "threshold": ("--dynamic-theta", "--person-dynamic-theta")}[parameter]
                command += [flags[0], str(requested["normal_dynamic_class"]),
                            flags[1], str(requested["person"])]
                metadata = {"parameter": parameter, "factor": factor, "run_id": run_id,
                            "sequence": sequence, "configuration": "Temporal",
                            "defaults_parsed": defaults, "requested_values": requested,
                            "effective_values_after_source_clamp": effective,
                            "unchanged_increment_defaults": defaults["increment"],
                            "semantic_config_sha256": sha256(REPO / "include/SemanticConfig.h"),
                            "executable_sha256": sha256(REPO / "Examples/RGB-D/rgbd_tum"),
                            "core_library_sha256": sha256(REPO / "lib/libORB_SLAM2.so"),
                            "build_variant": "no_object",
                            "association_sha256": sha256(association_path(sequence)),
                            "settings_sha256": sha256(SETTINGS), "git_commit": git_output("rev-parse", "HEAD"),
                            "git_status_short": git_output("status", "--short"),
                            "command": command, "created_at": now(), "out_dir": str(out)}
                cases.append(metadata)
                if not args.execute:
                    continue
                if out.exists():
                    raise RuntimeError(f"refusing to overwrite existing sensitivity run: {out}")
                out.mkdir(parents=True)
                write_json(out / "sensitivity_metadata.json", metadata)
                env = os.environ.copy()
                env["ORB_SLAM2_SOCKET_PATH"] = f"/tmp/paa_sens_{parameter}_{factor:g}_{run_id}_{os.getpid()}.sock"
                env["ORB_SLAM2_MAPPOINT_EVIDENCE_LOG"] = str(out / "mappoint_evidence_raw.csv")
                started = now()
                with (out / "driver.log").open("w", encoding="utf-8") as log:
                    process = subprocess.run(command, cwd=REPO, env=env, stdout=log,
                                             stderr=subprocess.STDOUT, text=True)
                write_json(out / "sensitivity_status.json",
                           {"status": "success" if process.returncode == 0 else "failed",
                            "return_code": process.returncode, "started_at": started,
                            "finished_at": now(), "failed_run_preserved": process.returncode != 0})
    write_json(root / "sensitivity_protocol.json",
               {"created_at": now(), "git_commit": git_output("rev-parse", "HEAD"),
                "defaults_parsed": defaults, "parameters": PARAMETERS, "factors": FACTORS,
                "runs_per_case": 5, "execute": args.execute, "cases": cases})
    print(f"cases={len(cases)} execute={args.execute} root={root}")


if __name__ == "__main__":
    main()
