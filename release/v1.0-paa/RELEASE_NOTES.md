# Release notes — v1.0-paa

Release date: 2026-09-19

## Manuscript

Exact manuscript file:

```text
paer2/mva_PAA_submission_FINAL_v2.docx
SHA-256: 508293121d7927d08bc7f7ae56870f5e150acf5f94a2a7e4952f76dc58df90cd
```

Title: *Persistent MapPoint-Level Temporal Evidence Fusion for RGB-D SLAM in
Dynamic Environments*.

## Frozen method

V4 `GEOMETRY_PROTECTED` combines persistent MapPoint-owned p/u/h state with
bounded measurement adaptation in tracking `PoseOptimization`. V3 uses the
same belief state with `BELIEF_ONLY` measurement reliability. Local BA, Global
BA, and loop closing are outside the V4 adaptation scope.

## Experiment protocols

- Internal: Vanilla, Legacy Temporal, V3 BELIEF_ONLY, and V4
  GEOMETRY_PROTECTED on TUM walking_xyz/static/rpy and Bonn
  person_tracking/synchronous/crowd. Predetermined runs are retained; no
  best-run selection is used.
- External: local DS-SLAM OUR RUN, three runs on each of the same six
  sequences. The exact upstream revision is not verifiable.
- Runtime: one warm-up and three measured serial runs per method-sequence cell,
  lightweight logging, TUM walking_xyz and Bonn person_tracking only.

Authoritative trajectory evaluator:

```text
scripts/evaluate_tum_metrics.py
SHA-256: cfdd35d556afcd5d080fe109396f5ffa7da1810a5e2c26a656c648216db24b13
```

## Known limitations

1. Accuracy and runtime binaries are platform-specific Linux x86-64 artifacts
   and remain explicitly separated.
2. The local DS-SLAM source tree lacked Git metadata, so its results remain
   labeled OUR RUN rather than an exact official-release reproduction.
3. Runtime measurements are hardware- and logging-mode-specific.
4. Datasets, checkpoints, and raw bulk runs are not redistributed.
5. Localization/coverage effects are sequence dependent; the release does not
   support a universal localization-superiority claim.

Reproducibility classification: **PARTIAL**. The source, accuracy/runtime
payloads, official YOLO checkpoint, protocol, evaluator, associations, hashes,
and result provenance are frozen. The external DS-SLAM comparison remains
partially reproducible because its local source tree lacks verifiable upstream
revision metadata.
