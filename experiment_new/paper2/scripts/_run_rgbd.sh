#!/usr/bin/env bash

set -euo pipefail

paper2_config_value() {
    local config_file="$1"
    local sequence_name="$2"
    local key="$3"

    awk -v target="${sequence_name}" -v wanted="${key}" '
        /^sequences:[[:space:]]*$/ { in_sequences = 1; next }
        in_sequences && /^[[:space:]]{2}[[:alnum:]_]+:[[:space:]]*$/ {
            current = $0
            sub(/^[[:space:]]+/, "", current)
            sub(/:[[:space:]]*$/, "", current)
            next
        }
        in_sequences && current == target && $0 ~ "^[[:space:]]{4}" wanted ":[[:space:]]*" {
            value = $0
            sub("^[[:space:]]{4}" wanted ":[[:space:]]*", "", value)
            gsub(/^"|"$/, "", value)
            print value
            exit
        }
    ' "${config_file}"
}

paper2_expand_path() {
    local value="$1"
    local project_root="$2"
    printf '%s\n' "${value//\$\{PROJECT_ROOT\}/${project_root}}"
}

run_rgbd_experiment() {
    if [[ $# -lt 4 || $# -gt 8 ]]; then
        echo "Usage: run_<mode>.sh VOCABULARY SETTINGS SEQUENCE ASSOCIATION [RUN_NAME]" >&2
        echo "   or: run_<mode>.sh SEQUENCE_NAME [RUN_NAME]" >&2
        return 2
    fi

    local experiment_name="$1"
    local semantic_mode="$2"
    local slam_binary="$3"

    local script_dir
    script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    local paper2_dir
    paper2_dir="$(cd "${script_dir}/.." && pwd)"
    local project_root
    project_root="$(cd "${paper2_dir}/../.." && pwd)"
    local config_file="${PAPER2_SEQUENCE_CONFIG:-${paper2_dir}/configs/tum_sequences.yaml}"
    local sequence_name="custom"
    local vocabulary
    local settings
    local sequence
    local association
    local run_name

    if [[ $# -eq 4 || $# -eq 5 ]]; then
        sequence_name="$4"
        run_name="${5:-$(date +%Y%m%d_%H%M%S)}"
        if [[ ! -f "${config_file}" ]]; then
            echo "Sequence configuration does not exist: ${config_file}" >&2
            return 2
        fi

        vocabulary="${project_root}/Vocabulary/ORBvoc.txt"
        settings="$(paper2_config_value "${config_file}" "${sequence_name}" "yaml_path")"
        sequence="$(paper2_config_value "${config_file}" "${sequence_name}" "dataset_path")"
        association="$(paper2_config_value "${config_file}" "${sequence_name}" "association_path")"
        if [[ -z "${settings}" || -z "${sequence}" || -z "${association}" ]]; then
            echo "Unknown or incomplete sequence configuration: ${sequence_name}" >&2
            return 2
        fi
        settings="$(paper2_expand_path "${settings}" "${project_root}")"
        sequence="$(paper2_expand_path "${sequence}" "${project_root}")"
        association="$(paper2_expand_path "${association}" "${project_root}")"
    elif [[ $# -eq 7 || $# -eq 8 ]]; then
        vocabulary="$4"
        settings="$5"
        sequence="$6"
        association="$7"
        run_name="${8:-$(date +%Y%m%d_%H%M%S)}"
    else
        echo "Usage: run_<mode>.sh VOCABULARY SETTINGS SEQUENCE ASSOCIATION [RUN_NAME]" >&2
        echo "   or: run_<mode>.sh SEQUENCE_NAME [RUN_NAME]" >&2
        return 2
    fi

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
        echo "sequence_name=${sequence_name}"
        echo "sequence_config=${config_file}"
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
