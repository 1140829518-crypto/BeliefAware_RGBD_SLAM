#!/usr/bin/env python3
"""Download/configure/run Bonn RGB-D Dynamic Dataset experiments.

The Bonn dataset is TUM RGB-D formatted, so the existing RGB-D front-ends and
trajectory evaluator can be reused. This script is resumable: downloaded
archives, extracted sequences, SLAM runs, and metrics are skipped when present.
"""

from __future__ import annotations

import argparse
import csv
import os
import re
import shutil
import subprocess
import sys
import tarfile
import time
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple


ROOT = Path(__file__).resolve().parents[2]
EXP = ROOT / "experiment_new"
DATASET_ROOT = EXP / "dataset/bonn_rgbd_dynamic"
ARCHIVE_DIR = DATASET_ROOT / "archives"
RESULT_DIR = EXP / "results"
RUN_ROOT = RESULT_DIR / "bonn_runs"
SCRIPT_DIR = EXP / "scripts"
os.environ.setdefault("MPLCONFIGDIR", str(EXP / ".matplotlib_cache"))

BONN_PAGE = "https://www.ipb.uni-bonn.de/data/rgbd-dynamic-dataset/"
TARGET_ALIASES = {
    "walking": ["walking", "person_tracking", "synchronous"],
    "sitting": ["sitting", "synchronous", "balloon"],
    "crowd": ["crowd", "person_tracking2", "moving"],
}
DEFAULT_DOWNLOAD_NAMES = ["rgbd_bonn_person_tracking", "rgbd_bonn_synchronous", "rgbd_bonn_crowd"]
METHODS = ["ORB-SLAM3", "DS-SLAM", "Dyna-SLAM", "Ours"]


def method_slug(method: str) -> str:
    return method.lower().replace("-", "_").replace(" ", "_")


def write_bonn_yaml(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = """%YAML:1.0

File.version: "1.0"
Camera.type: "PinHole"

Camera.fx: 542.822841
Camera.fy: 542.576870
Camera.cx: 315.593520
Camera.cy: 237.756098

Camera1.fx: 542.822841
Camera1.fy: 542.576870
Camera1.cx: 315.593520
Camera1.cy: 237.756098

Camera.k1: 0.039903
Camera.k2: -0.099343
Camera.p1: -0.000730
Camera.p2: -0.000144
Camera.k3: 0.0

Camera1.k1: 0.039903
Camera1.k2: -0.099343
Camera1.p1: -0.000730
Camera1.p2: -0.000144
Camera1.k3: 0.0

Camera.width: 640
Camera.height: 480
Camera.fps: 30
Camera.bf: 40.0
Camera.RGB: 1
ThDepth: 40.0
DepthMapFactor: 5000.0
Stereo.ThDepth: 40.0
Stereo.b: 0.07369
RGBD.DepthMapFactor: 5000.0

ORBextractor.nFeatures: 1000
ORBextractor.scaleFactor: 1.2
ORBextractor.nLevels: 8
ORBextractor.iniThFAST: 20
ORBextractor.minThFAST: 7

Viewer.KeyFrameSize: 0.05
Viewer.KeyFrameLineWidth: 1.0
Viewer.GraphLineWidth: 0.9
Viewer.PointSize: 2.0
Viewer.CameraSize: 0.08
Viewer.CameraLineWidth: 3.0
Viewer.ViewpointX: 0.0
Viewer.ViewpointY: -0.7
Viewer.ViewpointZ: -1.8
Viewer.ViewpointF: 500.0
PointCloudMapping.Resolution: 0.05
"""
    path.write_text(text, encoding="utf-8")


def scrape_download_links() -> Dict[str, str]:
    with urllib.request.urlopen(BONN_PAGE, timeout=30) as response:
        html = response.read().decode("utf-8", errors="ignore")
    links = re.findall(r'href=["\']([^"\']+)["\']', html)
    by_name: Dict[str, str] = {}
    for href in links:
        url = urllib.parse.urljoin(BONN_PAGE, href)
        name = Path(urllib.parse.urlparse(url).path).name
        stem = re.sub(r"\.(zip|tgz|tar\.gz|tar)$", "", name)
        if "rgbd_bonn" in stem and re.search(r"\.(zip|tgz|tar\.gz|tar)$", name):
            by_name[stem] = url
    return by_name


def download_archives(names: Sequence[str]) -> None:
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    links = scrape_download_links()
    missing = [name for name in names if name not in links]
    if missing:
        raise RuntimeError(f"Could not find Bonn download links for: {', '.join(missing)}")
    for name in names:
        url = links[name]
        suffix = "".join(Path(urllib.parse.urlparse(url).path).suffixes) or ".zip"
        out = ARCHIVE_DIR / f"{name}{suffix}"
        if out.exists() and out.stat().st_size > 0:
            print(f"[skip download] {out}")
            continue
        print(f"[download] {name} <- {url}", flush=True)
        download_file(url, out)


def download_file(url: str, out: Path) -> None:
    candidates = [url]
    if url.startswith("https://"):
        candidates.append("http://" + url[len("https://") :])
    last_error: Exception | None = None
    for candidate in candidates:
        for attempt in range(3):
            try:
                request = urllib.request.Request(candidate, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(request, timeout=60) as response, out.open("wb") as f:
                    shutil.copyfileobj(response, f)
                if out.stat().st_size > 0:
                    return
            except Exception as exc:
                last_error = exc
                if out.exists() and out.stat().st_size == 0:
                    out.unlink()
                print(f"[retry] {candidate} attempt {attempt + 1}: {exc}", flush=True)
                time.sleep(2.0)
    raise RuntimeError(f"Download failed for {url}: {last_error}")


def extract_archives() -> None:
    for archive in ARCHIVE_DIR.glob("*"):
        if archive.suffix.lower() == ".zip":
            marker = DATASET_ROOT / f".extracted_{archive.stem}"
            if marker.exists():
                continue
            print(f"[extract] {archive}", flush=True)
            with zipfile.ZipFile(archive) as zf:
                zf.extractall(DATASET_ROOT)
            marker.write_text(str(time.time()), encoding="utf-8")
        elif archive.suffix.lower() in {".tgz", ".gz", ".tar"} or archive.name.endswith(".tar.gz"):
            marker = DATASET_ROOT / f".extracted_{archive.name.replace('.', '_')}"
            if marker.exists():
                continue
            print(f"[extract] {archive}", flush=True)
            with tarfile.open(archive) as tf:
                tf.extractall(DATASET_ROOT)
            marker.write_text(str(time.time()), encoding="utf-8")


def discover_sequences(root: Path) -> List[Path]:
    found: List[Path] = []
    for path in root.rglob("groundtruth.txt"):
        seq = path.parent
        if (seq / "rgb.txt").exists() and (seq / "depth.txt").exists():
            found.append(seq)
    return sorted(set(found), key=lambda p: p.name)


def choose_sequences(sequences: Sequence[Path]) -> List[Tuple[str, Path]]:
    chosen: List[Tuple[str, Path]] = []
    used: set[Path] = set()
    for alias, patterns in TARGET_ALIASES.items():
        match = None
        for pattern in patterns:
            candidates = [seq for seq in sequences if pattern in seq.name.lower() and seq not in used]
            if candidates:
                match = candidates[0]
                break
        if match is not None:
            chosen.append((alias, match))
            used.add(match)
    if len(chosen) < 3:
        for seq in sequences:
            if seq not in used and "static" not in seq.name.lower():
                chosen.append((seq.name.replace("rgbd_bonn_", ""), seq))
                used.add(seq)
            if len(chosen) >= 3:
                break
    return chosen[:3]


def read_timestamps(path: Path) -> List[Tuple[float, str]]:
    rows: List[Tuple[float, str]] = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) >= 2:
            try:
                rows.append((float(parts[0]), parts[1]))
            except ValueError:
                continue
    return rows


def make_association(sequence_dir: Path) -> Path:
    out = sequence_dir / "associate.txt"
    if out.exists() and out.stat().st_size > 0:
        return out
    rgb = read_timestamps(sequence_dir / "rgb.txt")
    depth = read_timestamps(sequence_dir / "depth.txt")
    lines: List[str] = []
    j = 0
    for tr, rgb_file in rgb:
        while j + 1 < len(depth) and abs(depth[j + 1][0] - tr) < abs(depth[j][0] - tr):
            j += 1
        if depth and abs(depth[j][0] - tr) <= 0.04:
            lines.append(f"{tr:.6f} {rgb_file} {depth[j][0]:.6f} {depth[j][1]}")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def count_frames(sequence_dir: Path) -> int:
    return len(read_timestamps(sequence_dir / "rgb.txt"))


def run_logged(cmd: Sequence[str], cwd: Path, env: Dict[str, str], log_path: Path, timeout: float | None = None) -> float:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    start = time.time()
    with log_path.open("w", encoding="utf-8") as log:
        log.write("$ " + " ".join(cmd) + "\n")
        log.flush()
        subprocess.run(list(cmd), cwd=cwd, env=env, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=timeout)
    return time.time() - start


def write_runtime(run_dir: Path, elapsed: float, frames: int) -> None:
    fps = frames / elapsed if elapsed > 0 else 0.0
    (run_dir / "runtime.txt").write_text(f"wall_time {elapsed:.6f}\nframes {frames}\nfps {fps:.6f}\n", encoding="utf-8")


def copy_if_exists(src: Path, dst: Path) -> None:
    if src.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def collect_trajectory(out_dir: Path, candidates: Iterable[Path], min_mtime: float) -> None:
    current = out_dir / "CameraTrajectory.txt"
    if current.exists() and current.stat().st_mtime >= min_mtime:
        return
    existing = [path for path in candidates if path.exists() and path.stat().st_size > 0 and path.stat().st_mtime >= min_mtime]
    if not existing:
        return
    latest = max(existing, key=lambda path: path.stat().st_mtime)
    copy_if_exists(latest, current)


def command_for(method: str, sequence: Path, association: Path, settings: Path, out_dir: Path) -> Tuple[List[str], Path, Dict[str, str]]:
    env = os.environ.copy()
    env["MPLCONFIGDIR"] = str(EXP / ".matplotlib_cache")
    env["ORB_SLAM2_OUTPUT_DIR"] = str(out_dir)
    if method == "ORB-SLAM3":
        repo = Path("/home/djn/YOLO_ORB_SLAM3")
        exe = repo / "Examples/RGB-D/rgbd_tum"
        voc = repo / "Vocabulary/ORBvoc.txt"
        return [str(exe), str(voc), str(settings), str(sequence), str(association)], out_dir, env
    if method == "DS-SLAM":
        return [
            str(ROOT / "baselines/DS-SLAM-master/build/ds_rgbd_tum"),
            str(ROOT / "Vocabulary/ORBvoc.txt"),
            str(settings),
            str(sequence),
            str(association),
            str(ROOT / "baselines/DS-SLAM-master/Examples/ROS/ORB_SLAM2_PointMap_SegNetM/prototxts/segnet_pascal.prototxt"),
            str(ROOT / "baselines/DS-SLAM-master/Examples/ROS/ORB_SLAM2_PointMap_SegNetM/models/segnet_pascal.caffemodel"),
            str(ROOT / "baselines/DS-SLAM-master/Examples/ROS/ORB_SLAM2_PointMap_SegNetM/tools/pascal.png"),
            str(out_dir),
        ], ROOT, env
    if method == "Dyna-SLAM":
        exe = ROOT / "baselines/DynaSLAM-master/Examples/RGB-D/rgbd_tum"
        voc = ROOT / "baselines/DynaSLAM-master/Vocabulary/ORBvoc.txt"
        return [str(exe), str(voc), str(settings), str(sequence), str(association)], out_dir, env
    env["ORB_SLAM2_SEMANTIC_MODE"] = "2"
    env["ORB_SLAM2_OBJECT_MAP"] = "1"
    env["ORB_SLAM2_SOCKET_PATH"] = str(out_dir / "semantic_socket")
    return [
        sys.executable,
        str(ROOT / "scripts/run_tum_rgbd_experiment.py"),
        "--sequence",
        sequence.name,
        "--method",
        "full",
        "--dataset",
        str(sequence),
        "--association",
        str(association),
        "--settings",
        str(settings),
        "--out-dir",
        str(out_dir),
        "--device",
        "cpu",
    ], ROOT, env


def run_method(method: str, alias: str, sequence: Path, settings: Path, dry_run: bool, timeout: float | None) -> None:
    association = make_association(sequence)
    out_dir = RUN_ROOT / alias / method_slug(method)
    if (out_dir / "eval/metrics.json").exists():
        print(f"[skip] {alias} {method}", flush=True)
        return
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd, cwd, env = command_for(method, sequence, association, settings, out_dir)
    exe = Path(cmd[0])
    if not exe.exists():
        (out_dir / "failed.txt").write_text(f"missing executable: {exe}\n", encoding="utf-8")
        print(f"[missing] {method}: {exe}", flush=True)
        return
    if dry_run:
        (out_dir / "command.txt").write_text(" ".join(cmd) + "\n", encoding="utf-8")
        print(f"[dry-run] {alias} {method}", flush=True)
        return
    print(f"[run] {alias} {method}", flush=True)
    run_start = time.time()
    try:
        elapsed = run_logged(cmd, cwd, env, out_dir / "run.log", timeout=timeout)
    except subprocess.CalledProcessError as exc:
        (out_dir / "failed.txt").write_text(f"{exc}\n", encoding="utf-8")
        print(f"[failed] {alias} {method}: {exc}", flush=True)
        return
    except subprocess.TimeoutExpired as exc:
        (out_dir / "failed.txt").write_text(f"timeout after {exc.timeout:.1f}s\n", encoding="utf-8")
        print(f"[timeout] {alias} {method}: {exc.timeout:.1f}s", flush=True)
        return
    if method == "ORB-SLAM3":
        collect_trajectory(
            out_dir,
            [
                out_dir / "CameraTrajectory.txt",
                Path("/home/djn/YOLO_ORB_SLAM3/CameraTrajectory.txt"),
                ROOT / "CameraTrajectory.txt",
            ],
            run_start - 1.0,
        )
    elif method == "Dyna-SLAM":
        collect_trajectory(
            out_dir,
            [
                out_dir / "CameraTrajectory.txt",
                ROOT / "baselines/DynaSLAM-master/Examples/RGB-D/CameraTrajectory.txt",
                ROOT / "CameraTrajectory.txt",
            ],
            run_start - 1.0,
        )
    else:
        collect_trajectory(out_dir, [out_dir / "CameraTrajectory.txt", ROOT / "CameraTrajectory.txt"], run_start - 1.0)
    traj = out_dir / "CameraTrajectory.txt"
    if not traj.exists() or traj.stat().st_mtime < run_start - 1.0:
        (out_dir / "failed.txt").write_text("missing trajectory from current run\n", encoding="utf-8")
        print(f"[failed] {alias} {method}: missing trajectory from current run", flush=True)
        return
    write_runtime(out_dir, elapsed, count_frames(sequence))


def write_manifest(chosen: Sequence[Tuple[str, Path]]) -> Path:
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = RESULT_DIR / "bonn_selected_sequences.csv"
    with manifest.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["Dataset", "SequenceName", "Path", "Frames", "Association"])
        writer.writeheader()
        for alias, seq in chosen:
            assoc = make_association(seq)
            writer.writerow({"Dataset": alias, "SequenceName": seq.name, "Path": str(seq), "Frames": count_frames(seq), "Association": str(assoc)})
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Configure and run Bonn RGB-D Dynamic Dataset experiments.")
    parser.add_argument("--dataset-root", type=Path, default=DATASET_ROOT)
    parser.add_argument("--download", action="store_true", help="Download selected Bonn sequences from the official page.")
    parser.add_argument("--download-only", action="store_true", help="Download and extract, then stop before SLAM.")
    parser.add_argument("--dry-run", action="store_true", help="Prepare manifests and command files without executing SLAM.")
    parser.add_argument("--methods", nargs="*", default=METHODS)
    parser.add_argument("--timeout", type=float, default=0.0, help="Per sequence/method timeout in seconds. Use 0 for no timeout.")
    args = parser.parse_args()

    args.dataset_root.mkdir(parents=True, exist_ok=True)
    write_bonn_yaml(args.dataset_root / "Bonn.yaml")

    if args.download or args.download_only:
        download_archives(DEFAULT_DOWNLOAD_NAMES)
        extract_archives()

    sequences = discover_sequences(args.dataset_root)
    chosen = choose_sequences(sequences)
    if len(chosen) < 3:
        print("[warn] Fewer than three Bonn dynamic sequences found. Use --download or place data under experiment_new/dataset/bonn_rgbd_dynamic.", flush=True)
    manifest = write_manifest(chosen)

    if args.download_only:
        print(f"Prepared Bonn data manifest: {manifest}")
        return

    settings = args.dataset_root / "Bonn.yaml"
    timeout = args.timeout if args.timeout > 0 else None
    for alias, sequence in chosen:
        for method in args.methods:
            run_method(method, alias, sequence, settings, dry_run=args.dry_run, timeout=timeout)

    subprocess.run([sys.executable, str(SCRIPT_DIR / "evaluate_bonn.py"), "--manifest", str(manifest), "--run-root", str(RUN_ROOT)], cwd=ROOT, check=True)
    subprocess.run([sys.executable, str(SCRIPT_DIR / "plot_bonn_results.py"), "--manifest", str(manifest), "--run-root", str(RUN_ROOT)], cwd=ROOT, check=True)


if __name__ == "__main__":
    main()
