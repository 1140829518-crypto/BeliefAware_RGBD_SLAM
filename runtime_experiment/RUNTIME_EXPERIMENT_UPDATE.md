# Final runtime-only experiment

Date: 2026-09-17. Status: **PASS**. This campaign is separate from the
frozen accuracy/integrity campaign and uses lightweight runtime logging.

## 1. Source changes and timer definitions

Only runtime instrumentation and runtime-runner behavior were added:

- `include/ExperimentTiming.h`, `src/ExperimentTiming.cc`: added in-memory
  aggregate seconds/call/event counters and CSV columns for belief update,
  geometry protection, and PoseOptimization. Existing component names and
  meanings are preserved.
- `paper2_development/modules/ObjectDynamic/DynamicMapFilter.cc`: measures only
  the production MapPoint `UpdateBelief` computation plus persistent
  `SetDynamicBelief` write-back. Association/search, container traversal, and
  logging are excluded. Multiple updates are accumulated and flushed once per
  map view.
- `src/Optimizer.cc`: measures `Optimizer::PoseOptimization` from function
  entry to return. A separate V4-only timer surrounds the existing base
  residual, q/protection branch, effective reliability, and information-scale
  decision. It observes the existing protected decision and does not recompute
  policy quantities.
- `scripts/run_tum_rgbd_experiment.py`: an opt-in
  `ORB_SLAM2_RUNTIME_LIGHTWEIGHT=1` path unsets heavy belief, frame-ablation,
  and per-measurement optimizer logs. Default formal-benchmark behavior is
  unchanged.
- `runtime_experiment/run_runtime_benchmark.py` and
  `runtime_experiment/analyze_runtime.py`: isolated serial campaign and offline
  analysis. These are experiment infrastructure, not SLAM algorithm code.

All new clocks are `std::chrono::steady_clock`. Values are double-precision
seconds, accumulated in memory; no edge-loop or belief-update disk I/O was
introduced. PoseOptimization is a Tracking subcomponent and geometry policy is
a PoseOptimization subcomponent, so they must not be summed as independent
parts.

## 2. Validation

Instrumentation validation: **PASS**. Both existing executables
`test_dynamic_map_filter` and `test_optimizer_measurement_log` returned zero.
The production synthetic PERSISTENT outputs for A--J were byte-equivalent at
CSV precision to the authoritative frozen V3 analysis files. This verifies the
deterministic p/u/h/reliability/conflict trajectories and frozen policy
arithmetic; it does not claim bitwise trajectory determinism for threaded
SLAM. See `runtime_instrumentation_validation.md`.

## 3. Protocol and system

- Sequences: TUM `fr3_walking_xyz`; Bonn `rgbd_bonn_person_tracking`.
- Methods: Vanilla, Legacy Temporal, V3 PERSISTENT/BELIEF_ONLY, and V4
  PERSISTENT/GEOMETRY_PROTECTED, through the existing formal method mapping.
- Repetitions per sequence/method: one excluded warm-up plus three measured
  runs. All runs were strictly serial.
- Outcome: 32/32 execution attempts succeeded: 8 warm-ups and 24 measured
  runs. No infrastructure or algorithm failure occurred.
- Sanity only: every run produced a trajectory, finite runtime CSV, and
  evaluator output. Runtime trajectories are not substituted into the frozen
  accuracy table.
- Logging: `RUNTIME_LOGGING_MODE=LIGHTWEIGHT`; heavy belief, frame-ablation,
  and optimizer-measurement logs were absent in all runs.
- CPU: Intel Core i7-10870H, 8 cores/16 logical CPUs. OS/kernel: WSL2 Linux
  6.18.33.2. Compiler: g++ 9.4.0; Release build; OpenCV 4.2.0.
- Semantic inference: CUDA:0, NVIDIA GeForce RTX 3060 Laptop GPU (reported by
  the YOLO logs), using the same semantic runner/configuration for Legacy,
  V3, and V4. Thread-control environment variables were recorded in
  `runtime_protocol.json`; none were newly forced by this campaign.
- Statistics use the existing steady-state flag (first 30 frames excluded)
  and report mean ± sample standard deviation over three runs.

## 4. Runtime results

All entries are ms/frame except FPS. Full component/call-count fields are in
`runtime_per_run.csv` and `runtime_summary.csv`.

| Sequence | Method | Tracking | Semantic | Belief update | Geometry policy | PoseOptimization | End-to-end | FPS |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| TUM xyz | Vanilla | 49.546 ± 0.650 | 0 | 0 | 0 | 2.563 ± 0.337 | 62.307 ± 0.709 | 16.051 ± 0.184 |
| TUM xyz | Legacy Temporal | 50.939 ± 1.234 | 72.000 ± 0.219 | 0 | 0 | 4.288 ± 0.049 | 136.086 ± 1.353 | 7.349 ± 0.073 |
| TUM xyz | V3 BELIEF_ONLY | 43.778 ± 1.250 | 72.421 ± 0.354 | 0.0367 ± 0.0002 | 0 | 3.659 ± 0.009 | 128.746 ± 1.346 | 7.768 ± 0.081 |
| TUM xyz | V4 GEOMETRY_PROTECTED | 43.053 ± 1.087 | 72.141 ± 0.341 | 0.0373 ± 0.0004 | 0.1967 ± 0.0025 | 4.133 ± 0.050 | 127.332 ± 1.463 | 7.854 ± 0.090 |
| Bonn person | Vanilla | 40.164 ± 0.805 | 0 | 0 | 0 | 5.947 ± 0.113 | 51.095 ± 1.008 | 19.577 ± 0.385 |
| Bonn person | Legacy Temporal | 48.114 ± 0.235 | 867.435 ± 0.468 | 0 | 0 | 7.028 ± 0.024 | 927.899 ± 0.181 | 1.078 ± 0.000 |
| Bonn person | V3 BELIEF_ONLY | 46.543 ± 0.611 | 868.302 ± 0.817 | 0.0352 ± 0.0007 | 0 | 6.889 ± 0.194 | 927.193 ± 1.768 | 1.079 ± 0.002 |
| Bonn person | V4 GEOMETRY_PROTECTED | 49.341 ± 0.383 | 867.775 ± 0.474 | 0.0300 ± 0.0034 | 0.3421 ± 0.0074 | 7.857 ± 0.200 | 929.951 ± 0.035 | 1.075 ± 0.000 |

The semantic detector dominates the semantic-method end-to-end time,
especially on Bonn. Vanilla does not run that detector; therefore a
Vanilla--V4 difference is not a belief/geometry-policy overhead estimate.

## 5. V4 versus V3 incremental measurements

| Sequence | End-to-end Δ (V4−V3) | Relative | PoseOptimization Δ | Relative | Policy-local V4 cost | % V4 PoseOpt | % V4 end-to-end |
|---|---:|---:|---:|---:|---:|---:|---:|
| TUM xyz | −1.414 ms/frame | −1.099% | +0.474 ms/frame | +12.953% | 0.1967 ms/frame | 4.760% | 0.154% |
| Bonn person | +2.758 ms/frame | +0.297% | +0.968 ms/frame | +14.045% | 0.3421 ms/frame | 4.354% | 0.0368% |

The policy-local measurement is the narrow estimate of geometry-protection
computation. The observed V4−V3 PoseOptimization/end-to-end differences also
include the coherent MapPoint snapshot/recomputation path, different
measurement/MapPoint populations caused by stochastic trajectory evolution,
and ordinary run variability. In particular, belief-update calls/frame differ:
TUM V3 44.34 versus V4 47.78; Bonn V3 45.04 versus V4 36.58. Therefore the
whole V4−V3 difference cannot be attributed causally to geometry protection.
The negative TUM end-to-end difference is not interpreted as a speedup.

The pure measured belief-update cost was 0.0367 ms/frame (V3) and 0.0373
ms/frame (V4) on TUM, and 0.0352 and 0.0300 ms/frame on Bonn. The mismatch on
Bonn accompanies a different call count/MapPoint population and is not treated
as a per-update algorithmic speed change.

## 6. Claim assessment and limitations

The data support the narrow statement that the **instrumented policy-local
geometry computation** was below 0.35 ms/frame on these two sequences and was
below 0.16% of measured end-to-end time for the semantic pipeline. They do not
support a general real-time claim, a speedup claim, or an unrestricted
"negligible/minimal overhead" claim across hardware and datasets. A careful
"low policy-local computational cost under the reported setup" statement is
supported if accompanied by the actual values and protocol.

Section 5.6 can be updated with these runtime-only results, provided it clearly
separates policy-local cost, PoseOptimization change, and end-to-end change;
states n=3, hardware, warm-up and lightweight logging; and does not mix these
runs into the frozen localization-accuracy table.

Limitations: n=3; a single CPU/GPU system; only two dynamic sequences; threaded
SLAM stochasticity; GPU semantic latency is dataset/image-content dependent;
timer observation overhead is included; and V3/V4 differ in both measurement
policy and reliability data-access path. The results are implementation/runtime
evidence, not an algorithmic complexity proof.

## 7. PAPER_READY_RUNTIME_PARAGRAPH

Runtime was evaluated separately from the accuracy campaign on TUM
fr3_walking_xyz and Bonn rgbd_bonn_person_tracking using one excluded warm-up
and three measured runs per method and sequence. On an Intel i7-10870H CPU with
an RTX 3060 Laptop GPU for semantic inference, the policy-local
geometry-protection computation required 0.197 ± 0.002 ms/frame on TUM and
0.342 ± 0.007 ms/frame on Bonn. The corresponding V4−V3 changes were +0.474
ms/frame and +0.968 ms/frame in PoseOptimization, and −1.414 ms/frame and
+2.758 ms/frame end to end, respectively. Because V3 and V4 differ in both
measurement-policy computation and the reliability snapshot/access path, and
their stochastic runs can produce different measurement populations, the
end-to-end differences are reported as implementation-level incremental
measurements rather than attributed solely to geometry protection. Under this
setup, the policy-local computation accounted for 0.154% and 0.0368% of V4
end-to-end time on TUM and Bonn, respectively.

## 8. Artifact integrity

Runtime-instrumented artifacts (not replacements for the frozen accuracy
artifacts):

- `rgbd_tum`: `331a3609e265e16e28b9c51015e288f4ac3671d05dc4f61f3468923a5dc1a471`
- `libORB_SLAM2.so`: `de0c8a80dd7618874a6a0c6af6858ebd54dfaf3705cff63e365d53ab13cfa074`
- evaluator (unchanged): `cfdd35d556afcd5d080fe109396f5ffa7da1810a5e2c26a656c648216db24b13`

The manuscript DOCX and final accuracy comparison CSV hashes were checked
before/after and remain `f9ba529c...a0c3b` and `6d46679c...f519`, respectively.
No commit was created.
