# Bonn RGB-D association protocol

The formal Bonn runs used `rgb.txt` and `depth.txt` supplied with each sequence.
For each RGB timestamp, the generator advances monotonically through the depth
list to the nearest depth timestamp. A pair is emitted when the absolute time
difference is at most **0.04 s**. Timestamps are written with six decimals as:

```text
rgb_timestamp rgb_path depth_timestamp depth_path
```

This is the exact behavior implemented in
`experiment_new/scripts/run_bonn_experiment.py::make_association` and reproduced
without algorithm changes in `generate_bonn_association.py` in this directory.

Generate one file with:

```bash
python3 release/v1.0-paa/generate_bonn_association.py \
  --sequence /path/to/rgbd_bonn_person_tracking \
  --out /path/to/rgbd_bonn_person_tracking/associate.txt
```

Frozen association hashes and row counts:

| Sequence | Rows | SHA-256 |
|---|---:|---|
| `rgbd_bonn_person_tracking` | 580 | `bef821d66e0265e279fcbabbfd6a1f854d279c21c648de1e598414e2184438ac` |
| `rgbd_bonn_synchronous` | 332 | `e4da77c76a5aa47af256d1af41a392db8e829531cca5a71d862e31fa3c6b61eb` |
| `rgbd_bonn_crowd` | 928 | `99be3358f1413a4fc70f9f335ef9c72bf5681c1957db31fd18c03d47f5bbcdf8` |

After generation, the hash must match before the file is used to reproduce the
formal protocol. If it does not, retain the generated file and report the
dataset/file-list difference; do not edit rows manually to force a match.
