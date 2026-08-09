#!/usr/bin/env bash

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

readonly sequences=(
    "fr3_sitting_static"
    "fr3_walking_xyz"
    "fr3_walking_rpy"
    "fr3_walking_static"
)

readonly methods=(
    "baseline"
    "paper1"
    "shadow"
    "active"
)

selected_sequences=("${sequences[@]}")
if [[ $# -gt 1 ]]; then
    echo "Usage: run_all_tum.sh [SEQUENCE_NAME]" >&2
    exit 2
fi
if [[ $# -eq 1 ]]; then
    requested_sequence="$1"
    sequence_found=false
    for known_sequence in "${sequences[@]}"; do
        if [[ "${requested_sequence}" == "${known_sequence}" ]]; then
            sequence_found=true
            break
        fi
    done
    if [[ "${sequence_found}" != true ]]; then
        echo "Unknown sequence: ${requested_sequence}" >&2
        exit 2
    fi
    selected_sequences=("${requested_sequence}")
fi

for sequence_name in "${selected_sequences[@]}"; do
    for method_name in "${methods[@]}"; do
        timestamp="$(date +%Y%m%d_%H%M%S)"
        run_name="${sequence_name}_${timestamp}"
        runner="${script_dir}/run_${method_name}.sh"

        echo "[Paper2Batch] sequence=${sequence_name} method=${method_name} timestamp=${timestamp}"
        "${runner}" "${sequence_name}" "${run_name}"
    done
done
