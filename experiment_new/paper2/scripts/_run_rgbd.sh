#!/usr/bin/env bash

set -euo pipefail

run_rgbd_experiment() {
    if [[ $# -lt 7 || $# -gt 8 ]]; then
        echo "Usage: run_<mode>.sh VOCABULARY SETTINGS SEQUENCE ASSOCIATION [RUN_NAME]" >&2
        return 2
    fi

    local experiment_name="$1"
    local semantic_mode="$2"
    local slam_binary="$3"
    local vocabulary="$4"
    local settings="$5"
    local sequence="$6"
    local association="$7"
    local run_name="${8:-$(date +%Y%m%d_%H%M%S)}"

    local script_dir
    script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    local paper2_dir
    paper2_dir="$(cd "${script_dir}/.." && pwd)"
    local results_root="${PAPER2_RESULTS_ROOT:-${paper2_dir}/results}"
    local output_dir="${results_root}/${experiment_name}/${run_name}"

    if [[ ! -x "${slam_binary}" ]]; then
        echo "SLAM binary is not executable: ${slam_binary}" >&2
        return 2
    fi
    for input_path in "${vocabulary}" "${settings}" "${sequence}" "${association}"; do
        if [[ ! -e "${input_path}" ]]; then
            echo "Required input does not exist: ${input_path}" >&2
            return 2
        fi
    done
    if [[ -e "${output_dir}" ]]; then
        echo "Result directory already exists; choose another RUN_NAME: ${output_dir}" >&2
        return 2
    fi

    mkdir -p "${output_dir}"
    {
        echo "experiment=${experiment_name}"
        echo "run_name=${run_name}"
        echo "binary=${slam_binary}"
        echo "semantic_mode=${semantic_mode}"
        echo "vocabulary=${vocabulary}"
        echo "settings=${settings}"
        echo "sequence=${sequence}"
        echo "association=${association}"
        echo "output_dir=${output_dir}"
        echo "started_at=$(date --iso-8601=seconds)"
        ORB_SLAM2_SEMANTIC_MODE="${semantic_mode}" \
        ORB_SLAM2_OUTPUT_DIR="${output_dir}" \
            "${slam_binary}" "${vocabulary}" "${settings}" \
            "${sequence}" "${association}"
    } 2>&1 | tee "${output_dir}/run.log"
}
