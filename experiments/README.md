# PAA experiment protocol index

The public release uses the following protocol families:

1. **Internal controlled comparison** — Vanilla, Legacy Temporal, V3
   BELIEF_ONLY, and V4 GEOMETRY_PROTECTED on six sequences. The authoritative
   summary is identified by hash in `../RESULTS.md`.
2. **External comparison** — local DS-SLAM OUR RUN, three predetermined runs
   on the same six sequences, evaluated with the same trajectory evaluator.
   Exact DS-SLAM upstream revision is not verifiable.
3. **Runtime** — one warm-up plus three measured runs per cell, strictly
   serial and lightweight logging, on TUM walking_xyz and Bonn person_tracking.

`../reproduce_paa_results.sh` is the public dry-run-first entry point. Generated
run directories belong outside the repository and are not included here.
