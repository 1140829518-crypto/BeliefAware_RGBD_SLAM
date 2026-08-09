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

for sequence_name in "${sequences[@]}"; do
    for method_name in "${methods[@]}"; do
        timestamp="$(date +%Y%m%d_%H%M%S)"
        run_name="${sequence_name}_${timestamp}"
        runner="${script_dir}/run_${method_name}.sh"

        echo "[Paper2Batch] sequence=${sequence_name} method=${method_name} timestamp=${timestamp}"
        "${runner}" "${sequence_name}" "${run_name}"
    done
done
