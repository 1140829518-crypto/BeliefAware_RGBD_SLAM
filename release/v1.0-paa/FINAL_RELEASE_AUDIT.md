# Final release audit — v1.0-paa-final

Audit date: 2026-09-19

## Scope integrity

| Verification | Result |
|---|---|
| Algorithm modified during finalization | **NO** |
| Experiment implementation or outputs modified | **NO** |
| CSV files modified | **NO** |
| Manuscript DOCX modified | **NO** |
| Evaluator modified | **NO** |
| Accuracy executable included | **YES** |
| Accuracy library included | **YES** |
| Runtime executable/library kept separate | **YES** |

## Accuracy payload verification

| Artifact | SHA-256 | Result |
|---|---|---|
| `binaries/accuracy/rgbd_tum.accuracy` | `0079490eaf05c513ce18b5de95f66e54c98ba30e47511d17bd5a26ae4fcbddc9` | PASS |
| `binaries/accuracy/libORB_SLAM2.accuracy.so` | `85a1ec7d6c2786ad2fd2497ce0de2710c725a693ebd6b4d46c3bea63628c8687` | PASS |

The payloads were recovered by relinking preserved formal-build object files
without recompiling or modifying source. The resulting hashes exactly match the
pre-experiment manifest.

## Semantic checkpoint verification

- Official source:
  `https://github.com/ultralytics/yolov5/releases/download/v3.1/yolov5s.pt`
- Filename: `yolov5s.pt`
- Size: 15,184,789 bytes
- SHA-256:
  `3cb5c452360bc5c1dfd19ab0aca46f5e15a64af028846867310313a966cfe920`
- Official download versus frozen local checkpoint: byte-identical.

## Protected artifacts

The evaluator, internal comparison CSV, DS-SLAM comparison CSV, runtime CSV,
and manuscript hashes in `PROTECTED_ARTIFACTS.sha256` all pass. None is part of
the final release diff.

## Release decision

Accuracy binary included: **YES**.

Reproducibility status: **PARTIAL**.

Internal V3/V4 reproduction now has complete source, executable/library,
checkpoint, association, evaluator, protocol, and environment provenance. The
remaining limitation is external: the local DS-SLAM tree used for the OUR RUN
comparison lacked Git metadata, so its exact upstream revision cannot be
verified. This limitation is retained rather than concealed by a FULL label.
