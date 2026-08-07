#!/usr/bin/env python3
"""Prepare paper-ready TSR table from existing TSR statistics."""

from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TSR_ROOT = ROOT / "results" / "tracking_success_rate"
BY_SEQUENCE = TSR_ROOT / "tracking_success_rate_by_sequence.csv"
OUT_CSV = TSR_ROOT / "Table8_tracking_success_rate_by_sequence.csv"
OUT_MD = TSR_ROOT / "Table8_tracking_success_rate_by_sequence.md"
OUT_TEX = TSR_ROOT / "table8_tsr_by_sequence.tex"
OUT_TEXT = TSR_ROOT / "table8_tsr_analysis.md"

METHODS = ["Baseline", "Semantic Mask", "Temporal Consistency", "Object Map", "Full Model"]
SEQUENCES = [
    ("fr3_walking_xyz", "fr3 walking xyz"),
    ("fr3_walking_rpy", "fr3 walking rpy"),
    ("fr3_walking_halfsphere", "fr3 walking halfsphere"),
]


def latex_escape(text: str) -> str:
    return text.replace("_", r"\_").replace("%", r"\%")


def main() -> None:
    if not BY_SEQUENCE.exists():
        raise FileNotFoundError(f"Missing source file: {BY_SEQUENCE}")

    rows = {}
    with BY_SEQUENCE.open(newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            rows[(row["Method"], row["Sequence"])] = row

    table = []
    for method in METHODS:
        out = {"Method": method}
        values = []
        for seq_key, seq_label in SEQUENCES:
            value = rows[(method, seq_key)]["TSR(%)"]
            out[seq_label] = value
            values.append(value)
        method_summary = TSR_ROOT / "Table8_tracking_success_rate.csv"
        average = "NA"
        if method_summary.exists():
            with method_summary.open(newline="", encoding="utf-8-sig") as f:
                for r in csv.DictReader(f):
                    if r["Method"] == method:
                        average = r["TSR(%)"]
                        break
        out["Average"] = average
        table.append(out)

    fields = ["Method"] + [label for _, label in SEQUENCES] + ["Average"]
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(table)

    md = [
        "| Method | fr3 walking xyz | fr3 walking rpy | fr3 walking halfsphere | Average |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in table:
        md.append(
            f"| {row['Method']} | {row['fr3 walking xyz']} | {row['fr3 walking rpy']} | "
            f"{row['fr3 walking halfsphere']} | {row['Average']} |"
        )
    md.extend(
        [
            "",
            "注：TSR 表示 Tracking Success Rate，计算为有效位姿输出帧数与输入 RGB-D 帧数之比。"
            "表中结果为每个序列3次独立运行的均值±标准差，Average 为三个序列共9次运行的统计结果。",
        ]
    )
    OUT_MD.write_text("\n".join(md) + "\n", encoding="utf-8")

    tex = [
        r"\begin{table*}[t]",
        r"\centering",
        r"\caption{Tracking Success Rate comparison on TUM dynamic sequences}",
        r"\label{tab:tracking_success_rate}",
        r"\begin{tabular}{lcccc}",
        r"\toprule",
        r"Method & fr3 walking xyz & fr3 walking rpy & fr3 walking halfsphere & Average \\",
        r"\midrule",
    ]
    for row in table:
        vals = [latex_escape(str(row[field])).replace("±", r"$\pm$") for field in fields[1:]]
        tex.append(f"{latex_escape(row['Method'])} & " + " & ".join(vals) + r" \\")
    tex.extend(
        [
            r"\bottomrule",
            r"\end{tabular}",
            r"\end{table*}",
            "",
        ]
    )
    OUT_TEX.write_text("\n".join(tex), encoding="utf-8")

    analysis = """# Table 8 TSR Analysis

从不同序列的跟踪成功率可以看出，各模块配置对连续跟踪能力的影响具有明显场景依赖性。在 `fr3_walking_xyz` 序列中，Temporal Consistency 和 Full Model 均保持较高 TSR，说明动态证据建模在该类平移运动场景中没有明显破坏轨迹输出完整性。然而，在 `fr3_walking_rpy` 序列中，Temporal Consistency 和 Full Model 的 TSR 明显下降，表明当相机存在较强旋转运动且场景中包含动态干扰时，较严格的动态点抑制可能减少可用于稳定跟踪的特征约束，从而导致有效位姿输出减少。

该结果说明，动态抑制与轨迹完整性之间存在权衡关系。时间一致性相关模块能够降低动态误匹配对相对位姿估计的影响，但在部分高动态或快速姿态变化场景下，也可能因抑制过多观测而降低 Tracking Success Rate。因此，ATE 和 RPE 不宜脱离 TSR 单独解释。尤其在 TSR 较低的序列上，较小的 ATE/RPE 主要反映成功跟踪片段的误差水平，并不能直接等价于完整序列上的连续跟踪能力提升。

论文中可将该实验作为方法适用范围的补充说明：本文方法在动态环境下更关注降低动态误匹配带来的轨迹突变，并改善相对轨迹稳定性；同时，实验结果也表明动态信息抑制强度需要在鲁棒性与轨迹完整性之间进行平衡。
"""
    OUT_TEXT.write_text(analysis, encoding="utf-8")

    print(f"CSV: {OUT_CSV}")
    print(f"Markdown: {OUT_MD}")
    print(f"LaTeX: {OUT_TEX}")
    print(f"Analysis: {OUT_TEXT}")


if __name__ == "__main__":
    main()
