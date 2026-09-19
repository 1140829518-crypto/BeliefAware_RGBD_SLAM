# Runtime code audit

Audit date: 2026-09-17. Branch `belief_v4_geometry_protected`, HEAD `3eddbedbf1e6f7c4e55055ac75d3ad7d19f22710`. This file records the pre-instrumentation state.

## Current timing

- `ExperimentTiming` uses `std::chrono::steady_clock`, a per-frame double array, a mutex-protected accumulator, and writes `runtime_breakdown.csv` plus `runtime_summary.csv` only after sequence completion.
- Existing components: tracking total, semantic detection, legacy temporal-evidence update, object-dynamic adapter, dynamic-map filter, and end-to-end frame.
- `rgbd_tum` initializes the timing buffer, sets the current frame, times semantic detection and tracking, accumulates end-to-end time, and writes reports after shutdown.
- Current timing logs contain no per-measurement I/O. Separate optimizer measurement and belief logs are heavy diagnostics and can be disabled for runtime runs.

## Frozen method paths

- V3: `UNCERTAINTY_MODE=PERSISTENT`, `MEASUREMENT_POLICY=BELIEF_ONLY`; `Optimizer::PoseOptimization` consumes `Frame::mvMeasurementReliability` at `src/Optimizer.cc:536-539`.
- V4: the same PERSISTENT update with `GEOMETRY_PROTECTED`; it obtains one coherent MapPoint snapshot and recomputes `r_b` at `src/Optimizer.cc:540-552`.
- Mono geometry policy: base residual and threshold 5.991 at `src/Optimizer.cc:598-610`.
- Stereo/RGB-D geometry policy: base residual and threshold 7.815 at `src/Optimizer.cc:677-689`.
- Persistent belief computation is in `DynamicMapFilter::UpdateBelief`, with MapPoint write-back at `DynamicMapFilter.cc:175-177` in strict mappoint-carrier mode and `:464-473` in `UpdatePoint`.

## Missing timing

- Pure persistent MapPoint belief update time and call count.
- Geometry-protection policy-local time, call count, and protected count.
- Full `Optimizer::PoseOptimization` time and call count.
- Existing CSV contains only component seconds, not per-frame call/event counts.

## Proposed instrumentation location

1. Extend the existing `ExperimentTiming` schema without renaming existing fields. Add `BeliefUpdate`, `GeometryProtection`, and `PoseOptimization`, plus per-frame call/event counters.
2. Time MapPoint-local `UpdateBelief` plus `SetDynamicBelief` only, excluding association traversal and logging. Accumulate locally during `UpdateMapView` and flush once per view/frame.
3. At `PoseOptimization` function entry use the existing RAII steady-clock timer for total duration and one call.
4. Around the existing V4 base-residual/policy/information-scaling statements, take steady-clock timestamps, accumulate in local doubles, and flush once when `PoseOptimization` exits. Do not recompute q or reliability.
5. Keep heavy belief and optimizer-measurement log environment variables unset in the runtime runner.

## Behavioral risk

- Steady-clock reads add observation overhead but do not alter arithmetic inputs or branches.
- Locking once per measurement would materially perturb runtime; therefore policy timing is accumulated locally and flushed once per PoseOptimization call.
- V4-V3 end-to-end differences include both geometry-policy work and the existing coherent-snapshot/recomputation path; only the policy-local timer estimates the narrowly instrumented geometry block.
- The existing worktree is dirty from prior frozen-method development. Instrumentation changes must be limited to timing infrastructure and call sites, and final status/diff must preserve all pre-existing changes.

## Dataset and runner readiness

- TUM `fr3_walking_xyz`, association, TUM3 settings, and ground truth exist.
- Bonn `rgbd_bonn_person_tracking`, association, Bonn settings, and ground truth exist.
- The formal runner maps Vanilla to `baseline`, Legacy to `legacy-temporal`, and V3/V4 to `belief-active` with `MEMORY_CARRIER=mappoint`; V3/V4 differ by `ORB_SLAM2_MEASUREMENT_POLICY`.

Audit result: instrumentation can be added without changing the frozen algorithm. Proceed to validation gate.
