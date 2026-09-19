# PAA code-release audit

Audit date: 2026-09-19

## Completeness

| Requirement | Status | Evidence |
|---|---|---|
| Public landing page | PASS | `README.md` links the reproducibility entry points |
| License notice | PASS WITH LIMITATION | `LICENSE` declares GPL-3.0-or-later and preserves third-party licensing; publishers may prefer bundling the full GPL text rather than its canonical URL |
| Reproducibility guide | PASS | `reproducibility.md` |
| Python environment | PASS | `environment.yml` |
| Public configs | PASS | `configs/` contains method switches, path template, and Bonn calibration |
| Experiment command | PASS | `reproduce_paa_results.sh` is dry-run-first and covers V3, V4, and DS-SLAM trajectory evaluation |
| Evaluator entry point | PASS | `evaluation/evaluate_trajectory.sh` wraps the frozen evaluator |
| Experiment protocol index | PASS | `experiments/README.md` |
| Frozen provenance | PASS | `RESULTS.md` records accuracy, runtime, evaluator, external-baseline, and result hashes |
| Dataset redistribution avoided | PASS | datasets are path-only external requirements |
| Large binary redistribution avoided | PASS | binaries/models/results remain ignored and are not added by this package |
| Manuscript modified | NO | no DOCX was edited |
| Algorithm modified | NO | no source/algorithm file was edited by this task |
| Experiment results modified | NO | no CSV, trajectory, log, or evaluator was edited |

## Validation performed

- `bash -n reproduce_paa_results.sh`: **PASS**.
- `bash -n evaluation/evaluate_trajectory.sh`: **PASS**.
- `./reproduce_paa_results.sh --plan`: **PASS**; it enumerated 36 internal
  V3/V4 commands without launching SLAM.
- Public Bonn calibration versus frozen campaign calibration: **PASS**; all 46
  parsed key/value pairs are identical.
- Existing-output protection: **PASS by inspection**; `--run` exits before an
  existing internal run directory can be overwritten.
- The three authoritative result-file hashes and evaluator hash were recomputed
  and match `RESULTS.md`.
- Hashes in `RESULTS.md` were read from the retained formal manifests and
  authoritative result files rather than recomputed or inferred from the paper.

## Important reproducibility limitations

1. **Accuracy binary availability.** The formal accuracy executable and shared
   library are identified by SHA-256, but compiled binaries are intentionally
   excluded from the public package. The current local executable is the
   separately instrumented runtime build and has a different hash. Exact
   binary reproduction therefore depends on rebuilding in the recorded native
   environment or separately archiving the frozen accuracy artifacts.
2. **Uncommitted frozen implementation.** At audit time, the V4 source changes
   exist in a dirty worktree on `belief_v4_geometry_protected` rather than a
   clean public release commit/tag. Before publication, create an authorized
   immutable release commit/tag without changing algorithm behavior.
3. **Semantic assets.** The YOLOv5 inference tree and model weights are external
   and are not redistributed. Their exact upstream revision and model download
   instructions should be archived in a release manifest where licensing
   permits.
4. **DS-SLAM provenance.** The local DS-SLAM tree lacks Git metadata; its exact
   upstream revision is not verifiable. The paper correctly labels these
   results OUR RUN. The public script evaluates DS-SLAM trajectories but cannot
   guarantee reconstruction of that unknown source revision.
5. **Bonn associations.** Association files are dataset-side artifacts. Public
   release should provide a deterministic association-generation command or
   publish their hashes where dataset licensing permits.
6. **Native environment.** Pangolin is locally installed but its precise commit
   is not recorded. GPU driver, CUDA, cuDNN, PyTorch, and YOLO dependency
   versions are not fully frozen in the current manifests.
7. **Conda versus native build.** `environment.yml` covers analysis/orchestration
   packages; it does not replace the native C++/Pangolin/OpenCV build.
8. **Result availability.** Bulk raw runs are intentionally excluded. For full
   auditability, deposit immutable manifests, per-run metrics, and trajectories
   in a DOI-bearing archive without replacing the repository's authoritative
   result CSVs.
9. **Legacy evaluator plot label.** The frozen numeric evaluator labels one
   trajectory plot curve `DS-SLAM` internally. This does not alter ATE/RPE
   values, but plots generated for V3/V4 should not be reused without correcting
   that cosmetic label in a future, versioned evaluator release. The evaluator
   is intentionally unchanged here to preserve its frozen hash.
10. **Legacy documentation remains.** Historical Paper1/Paper2 notes and
    experiment directories remain in the working tree. Public users should
    follow the release links at the top of `README.md`; a release commit should
    include only intended tracked files and rely on `.gitignore` for local data,
    builds, binaries, and outputs.

## Reproducibility status

**PARTIAL, with a complete public workflow skeleton.** Evaluation and protocol
reproduction are documented and executable. Exact end-to-end artifact
reproduction still requires publication of an immutable V4 source revision,
semantic-asset provenance, Bonn association provenance, and complete native
dependency versions.
