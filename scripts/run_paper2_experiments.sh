#!/usr/bin/env bash

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_root="$(cd "${script_dir}/.." && pwd)"
paper2_root="${project_root}/experiment_new/paper2"
final_root="${paper2_root}/results/final"
staging_root="${paper2_root}/results/.paper2_final_staging"
runner="${paper2_root}/scripts/run_active.sh"
config_file="${PAPER2_SEQUENCE_CONFIG:-${paper2_root}/configs/tum_sequences.yaml}"
source "${paper2_root}/scripts/_run_rgbd.sh"

readonly sequences=(
    "fr3_walking_xyz"
    "fr3_walking_rpy"
    "fr3_walking_halfsphere"
    "fr3_sitting_xyz"
    "fr3_sitting_rpy"
    "fr3_sitting_halfsphere"
)

selected_sequences=("${sequences[@]}")
if [[ $# -gt 0 ]]; then
    selected_sequences=("$@")
    for requested_sequence in "${selected_sequences[@]}"; do
        known=false
        for sequence in "${sequences[@]}"; do
            if [[ "${requested_sequence}" == "${sequence}" ]]; then
                known=true
                break
            fi
        done
        if [[ "${known}" != true ]]; then
            echo "Unknown Paper2 sequence: ${requested_sequence}" >&2
            exit 2
        fi
    done
fi

configuration_valid=true
for sequence in "${selected_sequences[@]}"; do
    dataset_path="$(paper2_config_value "${config_file}" "${sequence}" "dataset_path")"
    association_path="$(paper2_config_value "${config_file}" "${sequence}" "association_path")"
    dataset_path="$(paper2_expand_path "${dataset_path}" "${project_root}")"
    association_path="$(paper2_expand_path "${association_path}" "${project_root}")"
    if [[ ! -d "${dataset_path}" ]]; then
        echo "Missing dataset for ${sequence}: ${dataset_path}" >&2
        configuration_valid=false
    fi
    if [[ ! -f "${association_path}" ]]; then
        echo "Missing association for ${sequence}: ${association_path}" >&2
        configuration_valid=false
    fi
done
if [[ "${configuration_valid}" != true ]]; then
    exit 2
fi

for sequence in "${selected_sequences[@]}"; do
    timestamp="$(date +%Y%m%d_%H%M%S)"
    sequence_root="${final_root}/${sequence}"
    run_name="${timestamp}"

    mkdir -p "${sequence_root}"
    echo "[Paper2Final] sequence=${sequence} timestamp=${timestamp}"
    PAPER2_RESULTS_ROOT="${staging_root}" \
        "${runner}" "${sequence}" "${run_name}"

    staged_output="${staging_root}/active/${run_name}"
    output_dir="${sequence_root}/${run_name}"
    if [[ -e "${output_dir}" ]]; then
        echo "Final result directory already exists: ${output_dir}" >&2
        exit 1
    fi
    mv "${staged_output}" "${output_dir}"
    for artifact in \
        run.log \
        CameraTrajectory.txt \
        KeyFrameTrajectory.txt \
        SemanticObjects.txt \
        SemanticDynamicStatistics.txt; do
        if [[ ! -s "${output_dir}/${artifact}" ]]; then
            echo "Missing experiment artifact: ${output_dir}/${artifact}" >&2
            exit 1
        fi
    done
done
