#!/usr/bin/env python3
"""Export deduplicated P4 V2 observations after objective frame selection."""

import csv
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
ROOT = REPO / "experiments/final_paper/04_mappoint_gt_eval"
METHODS = ("Semantic", "Temporal")
ASSOCIATIONS = {
    "fr3_walking_xyz": REPO / "dataset_associations/fr3_walking_xyz_associate.txt",
    "fr3_walking_rpy": REPO / "dataset_associations/fr3_walking_rpy_associate.txt",
    "fr3_walking_halfsphere": REPO / "dataset_associations/fr3_walking_halfsphere_associate.txt",
}


def timestamps(path):
    values = []
    for line in path.read_text().splitlines():
        if line.strip() and not line.lstrip().startswith("#"):
            values.append(line.split()[0])
    return values


def main():
    selected = {sequence: set() for sequence in ASSOCIATIONS}
    with (ROOT / "selected_frames_v2.csv").open(newline="") as stream:
        for row in csv.DictReader(stream):
            selected[row["sequence"]].add(int(row["frame_id"]))
    exact = {sequence: timestamps(path) for sequence, path in ASSOCIATIONS.items()}
    fields = ["method", "sequence", "run_id", "frame_id", "timestamp", "map_point_id",
              "u", "v", "class_id", "semantic_state", "temporal_state",
              "temporal_score", "threshold"]
    target = ROOT / "mappoint_observations_v2.csv"
    with target.open("w", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        for method in METHODS:
            for sequence in ASSOCIATIONS:
                source = ROOT / "runs" / method / sequence / "run_01/mappoint_projection_raw.csv"
                final = {}
                with source.open(newline="") as stream:
                    for row in csv.DictReader(stream):
                        frame_id = int(row["frame_id"])
                        if frame_id in selected[sequence]:
                            final[(frame_id, int(row["map_point_id"]))] = row
                for key in sorted(final):
                    row = final[key]
                    frame_id = key[0]
                    row["timestamp"] = exact[sequence][frame_id]
                    writer.writerow({"method": method, "sequence": sequence,
                                     "run_id": "run_01", **row})


if __name__ == "__main__":
    main()
