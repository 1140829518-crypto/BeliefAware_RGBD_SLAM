#!/usr/bin/env python3
"""Shared plotting style for paper figures."""

from __future__ import annotations

import csv
import os
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = ROOT / "Paper_Figure_Data"
PLOT_ROOT = ROOT / "Paper_Figure_Plot"
OUTPUT_ROOT = PLOT_ROOT / "output"
MPL_CACHE = PLOT_ROOT / ".matplotlib_cache"
MPL_CACHE.mkdir(parents=True, exist_ok=True)
os.environ["MPLCONFIGDIR"] = str(MPL_CACHE)

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager


def register_times_new_roman() -> None:
    for font_path in [
        Path.home() / ".fonts" / "times.ttf",
        Path.home() / ".fonts" / "timesbd.ttf",
        Path.home() / ".fonts" / "timesi.ttf",
        Path.home() / ".fonts" / "timesbi.ttf",
        Path("/mnt/c/Windows/Fonts/times.ttf"),
        Path("/mnt/c/Windows/Fonts/timesbd.ttf"),
        Path("/mnt/c/Windows/Fonts/timesi.ttf"),
        Path("/mnt/c/Windows/Fonts/timesbi.ttf"),
    ]:
        if font_path.exists():
            font_manager.fontManager.addfont(str(font_path))


register_times_new_roman()
FONT_NAME = "Times New Roman"


def apply_style() -> None:
    mpl.rcParams.update(
        {
            "font.family": "Times New Roman",
            "font.serif": ["Times New Roman"],
            "font.size": 10.0,
            "axes.titlesize": 10.0,
            "axes.labelsize": 10.5,
            "legend.fontsize": 9.0,
            "xtick.labelsize": 9.0,
            "ytick.labelsize": 9.0,
            "mathtext.fontset": "stix",
            "axes.unicode_minus": False,
            "axes.linewidth": 1.0,
            "xtick.major.width": 1.0,
            "ytick.major.width": 1.0,
            "xtick.major.size": 3.0,
            "ytick.major.size": 3.0,
            "lines.linewidth": 1.5,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.grid": False,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "savefig.dpi": 600,
            "savefig.bbox": "tight",
        }
    )


def read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def load_tum_trajectory(path: Path) -> np.ndarray:
    rows: List[List[float]] = []
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 4:
            continue
        try:
            rows.append([float(parts[0]), float(parts[1]), float(parts[2]), float(parts[3])])
        except ValueError:
            continue
    return np.asarray(rows, dtype=float)


def save_figure(fig: plt.Figure, name: str) -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    for ext in ["eps", "pdf", "png"]:
        kwargs = {"dpi": 600} if ext == "png" else {}
        fig.savefig(OUTPUT_ROOT / f"{name}.{ext}", **kwargs)
    inkscape = shutil.which("inkscape")
    if inkscape:
        env = os.environ.copy()
        env["DISPLAY"] = ""
        env["XDG_CONFIG_HOME"] = str(PLOT_ROOT / ".config")
        (PLOT_ROOT / ".config").mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [
                inkscape,
                "-z",
                str(OUTPUT_ROOT / f"{name}.pdf"),
                f"--export-emf={OUTPUT_ROOT / f'{name}.emf'}",
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        )
    plt.close(fig)


def add_panel_label(ax: plt.Axes, text: str) -> None:
    ax.set_title(text, fontweight="bold", pad=4)
    ax.grid(False)


def finite_float(value: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return np.nan
