# Final code release audit — v1.0-paa

## Protected-scope verification

| Check | Result |
|---|---|
| SLAM algorithm modified during release finalization | **NO** |
| Experiments modified during release finalization | **NO** |
| CSV results modified during release finalization | **NO** |
| Evaluator modified during release finalization | **NO** |
| Manuscript DOCX modified during release finalization | **NO** |

The protected artifacts are enumerated in `PROTECTED_ARTIFACTS.sha256`. Their
hashes are compared again immediately before the release commit/tag.

## Release completeness

| Item | Status |
|---|---|
| V4 source snapshot | PASS after release commit/tag |
| Accuracy/runtime binary separation | PASS |
| Runtime binary payload | PASS |
| Formal accuracy binary payload | **MISSING**; expected hashes retained |
| Evaluator hash | PASS |
| YOLO source revision and weight hash | PASS |
| Exact YOLO checkpoint download provenance | PARTIAL |
| Bonn generation algorithm and hashes | PASS |
| Native/Python environment versions | PASS WITH DRIVER LIMITATION |
| Dataset redistribution avoided | PASS |
| Result CSV replacement avoided | PASS |

## Decision

Reproducibility status: **PARTIAL**.

The package is suitable for transparent public release, but FULL binary-level
reproduction requires recovery of the two formal accuracy artifacts matching
the recorded hashes. The runtime artifacts must never be presented as those
accuracy binaries. Exact checkpoint download provenance and the DS-SLAM
upstream revision also remain unresolved.
