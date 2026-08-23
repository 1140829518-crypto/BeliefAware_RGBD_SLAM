#!/usr/bin/env python3
"""Build a temporary contact sheet for visual audit of the locked first 13 P4 masks."""

import csv
from pathlib import Path
import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1] / "experiments/final_paper/04_mappoint_gt_eval"
rows = list(csv.DictReader((ROOT / "selected_frames_v2.csv").open()))[:13]
tiles = []
for row in rows:
    stem = f"frame_{int(row['frame_id']):04d}"
    directory = ROOT / "annotation_v2" / row["sequence"]
    image = cv2.imread(str(directory / f"{stem}_rgb.png"))
    mask = cv2.imread(str(directory / f"{stem}_gt.png"), cv2.IMREAD_GRAYSCALE)
    overlay = image.copy()
    green = np.zeros_like(image); green[:, :, 1] = 255
    overlay[mask > 0] = cv2.addWeighted(image, 0.35, green, 0.65, 0)[mask > 0]
    cv2.putText(overlay, stem, (8, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 0, 255), 2)
    tiles.append(cv2.resize(overlay, (320, 240)))
canvas = np.full((4 * 240, 4 * 320, 3), 255, np.uint8)
for index, tile in enumerate(tiles):
    y, x = divmod(index, 4)
    canvas[y*240:(y+1)*240, x*320:(x+1)*320] = tile
cv2.imwrite("/tmp/p4_first13_overlay.png", canvas)
