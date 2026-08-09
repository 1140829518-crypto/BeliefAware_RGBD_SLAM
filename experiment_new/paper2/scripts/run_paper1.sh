#!/usr/bin/env bash

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_root="$(cd "${script_dir}/../../.." && pwd)"
source "${script_dir}/_run_rgbd.sh"

if [[ $# -ne 1 && $# -ne 2 && $# -ne 4 && $# -ne 5 ]]; then
    echo "Usage: run_paper1.sh VOCABULARY SETTINGS SEQUENCE ASSOCIATION [RUN_NAME]" >&2
    echo "   or: run_paper1.sh SEQUENCE_NAME [RUN_NAME]" >&2
    exit 2
fi

socket_path="${ORB_SLAM2_SOCKET_PATH:-/home/djn/server_socket}"
yolo_dir="${project_root}/yolov5_RemoveDynamic"
yolo_script="${yolo_dir}/detect_speedup_send.py"
yolo_weights="${yolo_dir}/yolov5s.pt"
results_root="${PAPER2_RESULTS_ROOT:-${project_root}/experiment_new/paper2/results}"
yolo_pid=""
yolo_log_tmp=""

if [[ $# -le 2 ]]; then
    sequence_name="$1"
    run_name="${2:-$(date +%Y%m%d_%H%M%S)}"
    config_file="${PAPER2_SEQUENCE_CONFIG:-${project_root}/experiment_new/paper2/configs/tum_sequences.yaml}"
    sequence_path="$(paper2_config_value "${config_file}" "${sequence_name}" "dataset_path")"
    if [[ -z "${sequence_path}" ]]; then
        echo "Unknown or incomplete sequence configuration: ${sequence_name}" >&2
        exit 2
    fi
    sequence_path="$(paper2_expand_path "${sequence_path}" "${project_root}")"
    run_arguments=("${sequence_name}" "${run_name}")
else
    sequence_path="$3"
    run_name="${5:-$(date +%Y%m%d_%H%M%S)}"
    run_arguments=("$1" "$2" "$3" "$4" "${run_name}")
fi

output_dir="${results_root}/paper1/${run_name}"
yolo_source="${sequence_path}/rgb"

cleanup_yolo() {
    local exit_status=$?
    trap - EXIT INT TERM

    if [[ -n "${yolo_pid}" ]] && kill -0 "${yolo_pid}" 2>/dev/null; then
        kill "${yolo_pid}" 2>/dev/null || true
        wait "${yolo_pid}" 2>/dev/null || true
    fi

    if [[ -n "${yolo_log_tmp}" && -f "${yolo_log_tmp}" ]]; then
        if [[ -d "${output_dir}" && ! -e "${output_dir}/yolo.log" ]]; then
            mv "${yolo_log_tmp}" "${output_dir}/yolo.log"
        else
            rm -f "${yolo_log_tmp}"
        fi
    fi

    rm -f "${socket_path}"
    exit "${exit_status}"
}

trap cleanup_yolo EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

if [[ ! -f "${yolo_script}" ]]; then
    echo "YOLO detector script does not exist: ${yolo_script}" >&2
    exit 2
fi
if [[ ! -f "${yolo_weights}" ]]; then
    echo "YOLO weights do not exist: ${yolo_weights}" >&2
    exit 2
fi
if [[ ! -d "${yolo_source}" ]]; then
    echo "YOLO image source does not exist: ${yolo_source}" >&2
    exit 2
fi
if [[ -e "${output_dir}" ]]; then
    echo "Result directory already exists; choose another RUN_NAME: ${output_dir}" >&2
    exit 2
fi

mkdir -p "${results_root}/paper1"
yolo_log_tmp="$(mktemp "${results_root}/paper1/.yolo.XXXXXX.log")"

rm -f "${socket_path}"
(
    cd "${yolo_dir}"
    exec env ORB_SLAM2_SOCKET_PATH="${socket_path}" \
        python3 -u "${yolo_script}" \
        --weights "${yolo_weights}" \
        --source "${yolo_source}" \
        --device 0
) >"${yolo_log_tmp}" 2>&1 &
yolo_pid=$!

socket_timeout="${PAPER2_YOLO_SOCKET_TIMEOUT:-60}"
if [[ ! "${socket_timeout}" =~ ^[1-9][0-9]*$ ]]; then
    echo "PAPER2_YOLO_SOCKET_TIMEOUT must be a positive integer" >&2
    exit 2
fi

echo "Starting YOLO detector for ${sequence_path}"
echo "Waiting for YOLO socket: ${socket_path}"
for ((elapsed = 0; elapsed < socket_timeout; ++elapsed)); do
    if [[ -S "${socket_path}" ]]; then
        break
    fi
    if ! kill -0 "${yolo_pid}" 2>/dev/null; then
        echo "YOLO detector exited before creating the socket:" >&2
        sed -n '1,120p' "${yolo_log_tmp}" >&2
        exit 1
    fi
    sleep 1
done

if [[ ! -S "${socket_path}" ]]; then
    echo "Timed out after ${socket_timeout}s waiting for YOLO socket" >&2
    sed -n '1,120p' "${yolo_log_tmp}" >&2
    exit 1
fi

sed -n '1,120p' "${yolo_log_tmp}"
export ORB_SLAM2_SOCKET_PATH="${socket_path}"
run_rgbd_experiment \
    "paper1" \
    "${PAPER2_SEMANTIC_MODE:-2}" \
    "${PAPER2_PAPER1_BINARY:-${project_root}/Examples/RGB-D/rgbd_tum}" \
    "${run_arguments[@]}"
