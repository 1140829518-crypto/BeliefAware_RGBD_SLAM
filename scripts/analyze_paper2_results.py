#!/usr/bin/env python3

"""Summarize final Paper2 semantic statistics into one CSV file."""

import argparse
import csv
import re
from pathlib import Path


STATISTICS_NAME = "SemanticDynamicStatistics.txt"
OUTPUT_NAME = "paper2_dynamic_statistics.csv"
MEAN_TRACKING_PATTERN = re.compile(
    r"mean tracking time:\s*([0-9]+(?:\.[0-9]+)?)"
)


def read_statistics(path):
    frames = {}
    with path.open("r", encoding="utf-8") as stream:
        header = stream.readline().split()
        required = {"frame_id", "dynamic_objects", "static_objects"}
        if not required.issubset(header):
            raise ValueError("missing required columns in {}".format(path))

        indices = {name: header.index(name) for name in required}
        for line_number, line in enumerate(stream, start=2):
            fields = line.split()
            if not fields:
                continue
            try:
                frame_id = int(fields[indices["frame_id"]])
                dynamic_objects = int(fields[indices["dynamic_objects"]])
                static_objects = int(fields[indices["static_objects"]])
            except (ValueError, IndexError) as error:
                raise ValueError(
                    "invalid statistics row {}:{}".format(path, line_number)
                ) from error
            frames[frame_id] = (dynamic_objects, static_objects)
    return frames


def read_tracking_time(run_log):
    if not run_log.is_file():
        return ""
    match = MEAN_TRACKING_PATTERN.search(
        run_log.read_text(encoding="utf-8", errors="replace")
    )
    return match.group(1) if match else ""


def sequence_name(final_root, statistics_path):
    relative = statistics_path.relative_to(final_root)
    return relative.parts[0] if relative.parts else "unknown"


def collect_rows(final_root):
    rows = []
    for statistics_path in sorted(final_root.rglob(STATISTICS_NAME)):
        frames = read_statistics(statistics_path)
        frame_count = len(frames)
        dynamic_count = sum(value[0] for value in frames.values())
        static_count = sum(value[1] for value in frames.values())
        average_dynamic = (
            float(dynamic_count) / frame_count if frame_count else 0.0
        )
        rows.append(
            {
                "sequence": sequence_name(final_root, statistics_path),
                "frame_count": frame_count,
                "dynamic_object_count": dynamic_count,
                "static_object_count": static_count,
                "average_dynamic_objects": "{:.6f}".format(average_dynamic),
                "tracking_time": read_tracking_time(
                    statistics_path.with_name("run.log")
                ),
            }
        )
    return rows


def main():
    project_root = Path(__file__).resolve().parents[1]
    default_final_root = (
        project_root / "experiment_new" / "paper2" / "results" / "final"
    )
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=default_final_root)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    final_root = args.results.resolve()
    output_path = (args.output or final_root / OUTPUT_NAME).resolve()
    rows = collect_rows(final_root)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "sequence",
        "frame_count",
        "dynamic_object_count",
        "static_object_count",
        "average_dynamic_objects",
        "tracking_time",
    ]
    with output_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print("Wrote {} runs to {}".format(len(rows), output_path))


if __name__ == "__main__":
    main()
