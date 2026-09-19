# ORB-SLAM2 Paper2 PAA release v1.0-paa

This directory freezes the reproducibility metadata for the manuscript
*Persistent MapPoint-Level Temporal Evidence Fusion for RGB-D SLAM in Dynamic
Environments*.

Contents:

- `RELEASE_NOTES.md`: manuscript, method, protocol, and limitations.
- `binary_sha256_manifest.json`: distinct accuracy/runtime artifact records.
- `binaries/accuracy/`: hashes for the formal accuracy artifacts. The original
  files are not present and are not replaced by another build.
- `binaries/runtime/`: the separately instrumented runtime executable and
  shared library.
- `YOLO_WEIGHTS.md`: semantic code/weight provenance and checksums.
- `BONN_ASSOCIATIONS.md`: deterministic association protocol and hashes.
- `generate_bonn_association.py`: standalone implementation of that protocol.
- `ENVIRONMENT.md`: recorded native, Python, CUDA, and hardware environment.
- `PROTECTED_ARTIFACTS.sha256`: hashes of evaluator, result summaries, and the
  exact manuscript used for this release.
- `FINAL_CODE_RELEASE_AUDIT.md`: final integrity and readiness decision.

The release metadata does not contain datasets, experiment outputs, the YOLO
checkpoint, or the formal accuracy binaries.
