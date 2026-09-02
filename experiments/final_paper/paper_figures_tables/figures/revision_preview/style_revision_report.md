# Style revision report

> **OLD PREVIEW NOTICE:** `fig1_system_framework_preview.png` is an obsolete Figure 1 preview retained only for historical comparison. It is not the current formal Figure 1 and must not be used in the paper. The sole formal source is `../../fig1_system_framework.drawio`, with formal exports stored beside that source.

Only preview PNG files were generated. Existing formal drawio/SVG/EPS/TIF files were not overwritten.

## Unified style

- Font status: `FONT_MISSING: 方正书宋`. This is an environment limitation and does not block preview generation. The current Chinese fallback must not be described as fully journal-compliant.
- Background: pure white.
- Grid: disabled (`ax.grid(False)`) for Figures 2–4.
- Axes: black solid bottom/left spines; top/right spines removed.
- Font: Times New Roman for English text, numbers and variables. Available system Chinese fallback is used only for previews; final export must be repeated after installing 方正书宋.
- Colors: ORB-SLAM2/Baseline `#1f77b4`; Semantic `#ff7f0e`; Temporal/Ours `#2ca02c`; Full `#d62728`; auxiliary state marker `#9467bd`.
- No gradients, shadows, rounded cards, gray axes backgrounds or background state bands.

## Figure provenance and checks

- Figure 1: method schematic based on the current implemented pipeline; no experimental data. Traditional rectangular blocks, black arrows and restrained core-module borders.
- Figure 2: conceptual illustration, not experimental data. Green temporal evidence, red threshold, blue dynamic observations. Grid disabled.
- Figure 3: read directly from `/home/djn/123/ORB_SLAM2_AddSemantic/experiments/final_paper/02_tum_comparison/p2_comparison_summary.csv`. Means and standard deviations are unchanged; black error bars are shown. Full/walking_rpy has `*`. Grid disabled.
- Figure 4: read directly from `/home/djn/123/ORB_SLAM2_AddSemantic/experiments/final_paper/03_temporal_continuity/selected_mappoint_evidence.csv`. Filter fixed to method `Temporal`, sequence `fr3_walking_xyz`, MapPoint ID `254`, run `run_01`.
- Figure 4 rows used: 578; full available frame span: 1–826; dynamic score range: 0.000000–20.000000.
- Figure 4 smoothing: **No**.
- Figure 4 cropping: **No**; every source row for the fixed method/sequence/MapPoint/run is plotted.
- Editable source retained: `scripts/generate_paper_figure_revision_preview.py`. Formal drawio/SVG sources are not overwritten during preview review.
- Formal 600 dpi CMYK lock: **Not performed in this preview stage**.

## P2 values used by Figure 3

| Sequence | ORB-SLAM2 | Semantic | Temporal | Full |
|---|---|---|---|---|
| walking_xyz | 0.835129±0.222270 | 0.504876±0.055832 | 0.562268±0.082441 | 0.538911±0.042124 |
| walking_rpy | 1.164329±0.152318 | 0.749207±0.035709 | 0.756381±0.058433 | 0.465345±0.395890 |
| walking_halfsphere | 0.644462±0.072637 | 0.329266±0.177200 | 0.356207±0.215751 | 0.443035±0.209126 |
