import pandas as pd
from pathlib import Path


ROOT = Path(
    "experiments/final_paper/04_mappoint_gt_eval/runs"
)

rows = []


# Semantic / Temporal
for method in ["Semantic", "Temporal"]:

    method_dir = ROOT / method

    if not method_dir.exists():
        continue

    for seq_dir in method_dir.iterdir():

        csv_path = (
            seq_dir /
            "run_01" /
            "tracking_mappoint_count.csv"
        )

        if csv_path.exists():

            df = pd.read_csv(csv_path)

            rows.append({
                "method": method,
                "sequence": seq_dir.name,
                "avg_tracking_mappoint":
                    round(df["mappoint_count"].mean(), 2)
            })


# Full
full_dir = ROOT / "Full"

if full_dir.exists():

    for csv_path in full_dir.glob("*tracking_mappoint_count.csv"):

        df = pd.read_csv(csv_path)

        name = csv_path.name.replace(
            "_tracking_mappoint_count.csv",
            ""
        )

        rows.append({
            "method": "Full",
            "sequence": name,
            "avg_tracking_mappoint":
                round(df["mappoint_count"].mean(), 2)
        })


result = pd.DataFrame(rows)


out = (
    ROOT /
    "average_mappoint_count.csv"
)


result.to_csv(
    out,
    index=False
)


print(result.to_string(index=False))

print("\nsaved:", out)
