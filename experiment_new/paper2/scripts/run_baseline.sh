#!/usr/bin/env bash

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_root="$(cd "${script_dir}/../../.." && pwd)"
source "${script_dir}/_run_rgbd.sh"

run_rgbd_experiment \
    "baseline" \
    "0" \
    "${PAPER2_BASELINE_BINARY:-${project_root}/Examples/RGB-D/rgbd_tum}" \
    "$@"
