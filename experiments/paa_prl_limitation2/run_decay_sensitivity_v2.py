#!/usr/bin/env python3
"""Run the preregistered forgetting-rate decay sensitivity (Temporal only)."""
from __future__ import annotations

import argparse, json, os, re, subprocess, sys, time
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))
from paa_prl_common import SETTINGS, association_path, dataset_path, git_output, parse_semantic_defaults, sha256, write_json

SEQUENCE = "fr3_walking_xyz"
CASES = (("fast", 2.0), ("moderately_fast", 1.5), ("default", 1.0), ("slow", .5), ("very_slow", .2))

def now(): return datetime.now().astimezone().isoformat(timespec="seconds")

def compile_probe(target: Path) -> None:
    source = REPO / "experiments/paa_prl_limitation2/runtime_decay_probe.cc"
    subprocess.run(["g++", "-std=c++11", "-O2", "-I", str(REPO / "include"), str(source), "-o", str(target)], check=True)

def probe(binary: Path, ordinary: float, person: float) -> dict[str, float]:
    env = os.environ.copy()
    env["ORB_SLAM2_DYNAMIC_LAMBDA"] = format(ordinary, ".12g")
    env["ORB_SLAM2_PERSON_DYNAMIC_LAMBDA"] = format(person, ".12g")
    output = subprocess.check_output([str(binary)], env=env, text=True)
    values = dict(line.split("=", 1) for line in output.splitlines() if "=" in line)
    return {key: float(value) for key, value in values.items()}

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=REPO / "results/paa_prl_limitation2/sensitivity_decay_v2")
    ap.add_argument("--runs", type=int, default=5)
    ap.add_argument("--device", default="0")
    ap.add_argument("--execute", action="store_true")
    args = ap.parse_args()
    if args.runs != 5: ap.error("protocol requires exactly five predetermined runs")
    root = args.root.resolve()
    if args.execute and root.exists() and any(root.iterdir()):
        raise RuntimeError(f"refusing to overwrite non-empty formal output: {root}")
    root.mkdir(parents=True, exist_ok=True)
    metadata_dir = root / "metadata"; metadata_dir.mkdir(exist_ok=True)
    probe_binary = metadata_dir / "runtime_decay_probe"
    compile_probe(probe_binary)

    config = REPO / "include/SemanticConfig.h"
    defaults = parse_semantic_defaults(config)["decay"]
    ordinary_default, person_default = defaults["normal_dynamic_class"], defaults["person"]
    clamp_match = re.search(r"decay\s*>\s*([0-9.]+)f", config.read_text())
    if not clamp_match: raise RuntimeError("cannot parse decay clamp from SemanticConfig.h")
    clamp_limit = float(clamp_match.group(1))
    settings = []
    for label, factor in CASES:
        requested_o = 1.0 - factor * (1.0 - ordinary_default)
        requested_p = 1.0 - factor * (1.0 - person_default)
        effective = probe(probe_binary, requested_o, requested_p)
        clamped = abs(effective["ordinary"] - requested_o) > 5e-7 or abs(effective["person"] - requested_p) > 5e-7
        settings.append({"setting": label, "forgetting_rate_factor": factor,
                         "ordinary_decay_requested": requested_o, "person_decay_requested": requested_p,
                         "ordinary_decay_effective": effective["ordinary"], "person_decay_effective": effective["person"],
                         "clamp_applied": clamped})
    for key in ("ordinary_decay_effective", "person_decay_effective"):
        values = [round(float(s[key]), 8) for s in settings]
        if len(set(values)) != 5: raise RuntimeError(f"duplicate effective values: {key}={values}")
        if any(value >= clamp_limit for value in values): raise RuntimeError(f"effective decay reaches clamp: {key}={values}")
    if any(s["clamp_applied"] for s in settings): raise RuntimeError("runtime probe differs from requested value; stopping before SLAM")

    common = {"created_at": now(), "git_commit": git_output("rev-parse", "HEAD"),
              "git_status_short": git_output("status", "--short"), "source_defaults": defaults,
              "source_file": str(config), "source_sha256": sha256(config),
              "forgetting_rate_formula": "lambda_effective = 1 - factor * (1 - lambda_default)",
              "factors": [factor for _, factor in CASES], "settings": settings, "clamp_limit": clamp_limit,
              "all_clamp_applied_false": True, "sequence": SEQUENCE, "run_ids": list(range(1, 6)),
              "failed_incomplete_policy": "preserve; do not replace or select", "executable_sha256": sha256(REPO / "Examples/RGB-D/rgbd_tum"),
              "core_library_sha256": sha256(REPO / "lib/libORB_SLAM2.so"), "settings_sha256": sha256(SETTINGS),
              "association_sha256": sha256(association_path(SEQUENCE)), "dataset": str(dataset_path(SEQUENCE)), "execute": args.execute}
    write_json(root / "decay_protocol.json", common)
    if not args.execute:
        print(json.dumps(settings, indent=2)); return

    for setting in settings:
        for run_id in range(1, 6):
            out = root / "settings" / setting["setting"] / f"run_{run_id:02d}"
            if out.exists(): raise RuntimeError(f"refusing overwrite: {out}")
            out.mkdir(parents=True)
            command = [sys.executable, str(REPO / "scripts/run_tum_rgbd_experiment.py"), "--sequence", SEQUENCE,
                       "--method", "dynamic", "--dataset", str(dataset_path(SEQUENCE)), "--association", str(association_path(SEQUENCE)),
                       "--settings", str(SETTINGS), "--out-dir", str(out), "--device", args.device,
                       "--dynamic-lambda", format(setting["ordinary_decay_requested"], ".12g"),
                       "--person-dynamic-lambda", format(setting["person_decay_requested"], ".12g")]
            meta = {**setting, "sequence": SEQUENCE, "configuration": "Temporal", "run_id": run_id,
                    "command": command, "created_at": now(), "git_commit": common["git_commit"], "hashes": {
                    "semantic_config": common["source_sha256"], "executable": common["executable_sha256"],
                    "core_library": common["core_library_sha256"], "association": common["association_sha256"], "settings": common["settings_sha256"]}}
            write_json(out / "decay_metadata.json", meta)
            env = os.environ.copy(); socket = f"/tmp/paa_decay_v2_{setting['setting']}_{run_id}_{os.getpid()}.sock"
            env["ORB_SLAM2_SOCKET_PATH"] = socket
            env["ORB_SLAM2_MAPPOINT_EVIDENCE_LOG"] = str(out / "mappoint_evidence_raw.csv")
            env["ORB_SLAM2_MAPPOINT_PROJECTION_LOG"] = str(out / "mappoint_projection_raw.csv")
            started = now(); begin = time.monotonic()
            with (out / "driver.log").open("w", encoding="utf-8") as log:
                proc = subprocess.run(command, cwd=REPO, env=env, stdout=log, stderr=subprocess.STDOUT, text=True)
            write_json(out / "decay_status.json", {"status": "success" if proc.returncode == 0 else "failed",
                       "return_code": proc.returncode, "started_at": started, "finished_at": now(),
                       "wall_time_seconds": time.monotonic()-begin, "failed_run_preserved": proc.returncode != 0})
            print(f"{setting['setting']} run_{run_id:02d}: rc={proc.returncode}", flush=True)

if __name__ == "__main__": main()
