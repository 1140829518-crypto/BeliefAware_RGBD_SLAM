#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
action="${1:---plan}"
target="${2:-internal}"

usage() {
  echo "Usage: $0 --plan | --run {internal|v3|v4|dsslam-eval}"
  echo "Required for --run: TUM_ROOT, BONN_ROOT, OUTPUT_ROOT"
  echo "Additionally for dsslam-eval: DS_SLAM_RESULTS_ROOT"
}

if [[ "$action" != "--plan" && "$action" != "--run" ]]; then usage; exit 2; fi
if [[ "$action" == "--run" && "$target" != "internal" && "$target" != "v3" && "$target" != "v4" && "$target" != "dsslam-eval" ]]; then usage; exit 2; fi

run_or_print() {
  if [[ "$action" == "--plan" ]]; then printf 'PLAN:'; printf ' %q' "$@"; printf '\n';
  else "$@"; fi
}

tum_root="${TUM_ROOT:-/path/to/TUMRGBD}"
bonn_root="${BONN_ROOT:-/path/to/bonn_rgbd_dynamic}"
output_root="${OUTPUT_ROOT:-/path/to/paa_outputs}"
device="${YOLO_DEVICE:-0}"

if [[ "$action" == "--run" ]]; then
  for v in TUM_ROOT BONN_ROOT OUTPUT_ROOT; do
    [[ -n "${!v:-}" ]] || { echo "$v is required" >&2; exit 2; }
  done
  if [[ "$target" != "dsslam-eval" ]]; then
    [[ -x "${repo_dir}/Examples/RGB-D/rgbd_tum" ]] || { echo "Build rgbd_tum first" >&2; exit 2; }
    [[ -f "${repo_dir}/Vocabulary/ORBvoc.txt" ]] || { echo "ORB vocabulary missing" >&2; exit 2; }
  fi
fi

sequences=(fr3_walking_xyz fr3_walking_static fr3_walking_rpy rgbd_bonn_person_tracking rgbd_bonn_synchronous rgbd_bonn_crowd)

dataset_for() {
  case "$1" in
    fr3_walking_xyz) echo "${tum_root}/rgbd_dataset_freiburg3_walking_xyz" ;;
    fr3_walking_static) echo "${tum_root}/rgbd_dataset_freiburg3_walking_static" ;;
    fr3_walking_rpy) echo "${tum_root}/rgbd_dataset_freiburg3_walking_rpy" ;;
    *) echo "${bonn_root}/$1" ;;
  esac
}
association_for() {
  case "$1" in
    fr3_*) echo "${repo_dir}/dataset_associations/${1}_associate.txt" ;;
    *) echo "${bonn_root}/$1/associate.txt" ;;
  esac
}
settings_for() {
  case "$1" in fr3_*) echo "${repo_dir}/Examples/RGB-D/TUM3.yaml" ;; *) echo "${repo_dir}/configs/Bonn.yaml" ;; esac
}

run_internal_method() {
  local label="$1" policy="$2" seq run out
  for seq in "${sequences[@]}"; do
    for run in 1 2 3; do
      out="${output_root}/internal/${label}/${seq}/run_$(printf '%02d' "$run")"
      if [[ "$action" == "--run" && -e "$out" ]]; then
        echo "Refusing to overwrite existing run directory: $out" >&2
        exit 3
      fi
      run_or_print env \
        ORB_SLAM2_ACTIVE_MODE_ENABLED=1 \
        ORB_SLAM2_BELIEF_ENABLED=1 \
        ORB_SLAM2_RELIABILITY_ENABLED=1 \
        ORB_SLAM2_LEGACY_TEMPORAL_WEIGHT_ENABLED=0 \
        ORB_SLAM2_LEGACY_TEMPORAL_HARD_REJECTION_ENABLED=0 \
        ORB_SLAM2_MEMORY_CARRIER=mappoint \
        ORB_SLAM2_UNCERTAINTY_MODE=PERSISTENT \
        ORB_SLAM2_CONFLICT_AWARE_UNCERTAINTY_ENABLED=1 \
        ORB_SLAM2_MEASUREMENT_POLICY="$policy" \
        python3 "${repo_dir}/scripts/run_tum_rgbd_experiment.py" \
        --sequence "$seq" --method belief-active \
        --dataset "$(dataset_for "$seq")" \
        --association "$(association_for "$seq")" \
        --settings "$(settings_for "$seq")" \
        --out-dir "$out" --device "$device" --socket-timeout 300
    done
  done
}

evaluate_dsslam() {
  [[ -n "${DS_SLAM_RESULTS_ROOT:-}" || "$action" == "--plan" ]] || { echo "DS_SLAM_RESULTS_ROOT is required" >&2; exit 2; }
  local root="${DS_SLAM_RESULTS_ROOT:-/path/to/dsslam_six_sequence/runs}" seq run traj out
  for seq in "${sequences[@]}"; do
    for run in 1 2 3; do
      traj="${root}/${seq}/run_$(printf '%02d' "$run")/CameraTrajectory.txt"
      out="${output_root}/dsslam_eval/${seq}/run_$(printf '%02d' "$run")"
      run_or_print "${repo_dir}/evaluation/evaluate_trajectory.sh" \
        "$(dataset_for "$seq")/groundtruth.txt" "$traj" "$out"
    done
  done
}

case "$target" in
  internal) run_internal_method v3_belief_only BELIEF_ONLY; run_internal_method v4_geometry_protected GEOMETRY_PROTECTED ;;
  v3) run_internal_method v3_belief_only BELIEF_ONLY ;;
  v4) run_internal_method v4_geometry_protected GEOMETRY_PROTECTED ;;
  dsslam-eval) evaluate_dsslam ;;
esac

if [[ "$action" == "--plan" ]]; then
  echo "Dry run only. Supply dataset roots and use --run to execute."
fi
