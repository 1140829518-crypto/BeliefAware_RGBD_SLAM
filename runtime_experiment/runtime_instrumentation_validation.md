# Runtime instrumentation validation

Validation date: 2026-09-17. Result: **PASS**.

## Build

- Release build configured in `build_runtime` with the frozen active/shadow compile definitions.
- `libORB_SLAM2.so`, `rgbd_tum`, `test_dynamic_map_filter`,
  `synthetic_belief_conflict`, and `test_optimizer_measurement_log` built
  successfully. Compiler output contained pre-existing deprecation warnings but
  no build error.

## Regression and deterministic equivalence

- `test_dynamic_map_filter`: PASS (exit 0). This exercises persistent
  MapPoint belief updates, gap handling, replacement/fusion, and mode behavior.
- `test_optimizer_measurement_log`: PASS (exit 0). This exercises the frozen
  optimizer measurement-policy arithmetic and logging contract.
- The production `synthetic_belief_conflict` executable was run in PERSISTENT
  mode. Every generated analysis CSV for sequences A--J was compared with the
  authoritative frozen output in
  `experiment_new/paper2_belief_eval/output/synthetic_belief_v3/persistent`.
  Recursive `diff` returned no difference. Thus p, u, h, reliability, raw and
  persistent conflict, transition behavior, and measurement counts remain
  exactly equal at the CSV precision used by the existing deterministic test.
- The timer call sites only observe already-computed values. Geometry timing
  uses the existing policy branch and its existing protected decision; it does
  not recompute q, r_b, r_dyn, or r_eff.
- `git diff --check` on all instrumentation and lightweight-runner changes:
  PASS.

## Timing invariants

- New clocks use `std::chrono::steady_clock`.
- Durations are stored as `double` seconds.
- Belief and geometry measurements accumulate in memory and flush once per
  MapPoint view or PoseOptimization call; there is no per-measurement disk I/O.
- Heavy belief, optimizer-measurement, and ablation-frame logs are disabled
  only when the new runtime-only environment flag is explicitly enabled. The
  formal runner's default behavior is unchanged.

The instrumentation validation gate therefore passes, and the isolated
runtime-only benchmark may proceed. This is a unit/synthetic behavioral check;
it does not claim bitwise trajectory determinism for threaded SLAM runs.
