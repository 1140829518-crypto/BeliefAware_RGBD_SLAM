#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 3 ]]; then
  echo "Usage: $0 GROUNDTRUTH.txt CameraTrajectory.txt OUTPUT_DIR" >&2
  exit 2
fi

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec python3 "${repo_dir}/scripts/evaluate_tum_metrics.py" \
  --gt "$1" --est "$2" --out-dir "$3"
