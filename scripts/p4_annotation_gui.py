#!/usr/bin/env python3
"""Local manual-mask GUI for P4 MapPoint dynamic-state ground truth."""

from __future__ import annotations

import argparse
import csv
import os
from pathlib import Path
import tempfile
import tkinter as tk
from tkinter import messagebox, ttk

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageTk


REPO = Path(__file__).resolve().parents[1]
DEFAULT_ROOT = REPO / "experiments/final_paper/04_mappoint_gt_eval"


class AnnotationApp:
    DISPLAY_MAX_WIDTH = 1050
    DISPLAY_MAX_HEIGHT = 610
    CONTEXT_MAX_WIDTH = 1150
    CONTEXT_MAX_HEIGHT = 210
    OVERLAY_ALPHA = 105
    GT_COLOR = (0, 200, 0)
    IGNORE_COLOR = (255, 210, 0)

    def __init__(self, window: tk.Tk, root: Path):
        self.window = window
        self.root = root
        self.annotation_root = root / "annotation_v2"
        self.selected_csv = root / "selected_frames_v2.csv"
        self.progress_csv = root / "annotation_progress.csv"
        self.items = self._load_items()
        if len(self.items) != 120:
            raise RuntimeError(f"expected 120 selected frames, found {len(self.items)}")
        self.progress = self._load_progress()
        self._ensure_progress_rows()

        self.index = 0
        self.mode = "gt"
        self.tool = "brush"
        self.eraser = False
        self.brush_size = 12
        self.dragging = False
        self.last_point = None
        self.polygon_points = []
        self.undo_stack = []
        self.dirty = False
        self.scale = 1.0
        self.display_size = (1, 1)
        self.rgb = None
        self.gt = None
        self.ignore = None
        self.main_photo = None
        self.context_photo = None

        self._build_ui()
        self._bind_keys()
        self._load_current()
        self.window.protocol("WM_DELETE_WINDOW", self._close)

    def _load_items(self):
        with self.selected_csv.open(newline="", encoding="utf-8-sig") as stream:
            return list(csv.DictReader(stream))

    def _load_progress(self):
        progress = {}
        if self.progress_csv.exists():
            with self.progress_csv.open(newline="", encoding="utf-8-sig") as stream:
                for row in csv.DictReader(stream):
                    progress[(row["sequence"], int(row["frame_id"]))] = {
                        "gt_nonzero_pixels": int(row.get("gt_nonzero_pixels", 0) or 0),
                        "ignore_nonzero_pixels": int(row.get("ignore_nonzero_pixels", 0) or 0),
                        "completed": int(row.get("completed", 0) or 0),
                    }
        return progress

    def _ensure_progress_rows(self):
        for item in self.items:
            key = (item["sequence"], int(item["frame_id"]))
            if key in self.progress:
                continue
            paths = self._paths(item)
            gt = cv2.imread(str(paths["gt"]), cv2.IMREAD_GRAYSCALE)
            ignore = cv2.imread(str(paths["ignore"]), cv2.IMREAD_GRAYSCALE)
            if gt is None or ignore is None:
                raise RuntimeError(f"missing mask template: {key}")
            self.progress[key] = {
                "gt_nonzero_pixels": int(np.count_nonzero(gt)),
                "ignore_nonzero_pixels": int(np.count_nonzero(ignore)),
                "completed": 0,
            }
        self._write_progress()

    def _build_ui(self):
        self.window.title("P4 MapPoint Dynamic GT Annotation")
        self.window.geometry("1200x940")

        top = ttk.Frame(self.window, padding=5)
        top.pack(fill=tk.X)
        self.progress_label = ttk.Label(top, text="", font=("TkDefaultFont", 11, "bold"))
        self.progress_label.pack(side=tk.LEFT, padx=5)
        self.mode_label = ttk.Label(top, text="")
        self.mode_label.pack(side=tk.LEFT, padx=18)
        self.completed_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(top, text="标注完成", variable=self.completed_var,
                        command=self._completion_changed).pack(side=tk.LEFT, padx=12)

        ttk.Button(top, text="GT (G)", command=lambda: self._set_mode("gt")).pack(side=tk.LEFT, padx=2)
        ttk.Button(top, text="Ignore (I)", command=lambda: self._set_mode("ignore")).pack(side=tk.LEFT, padx=2)
        ttk.Button(top, text="橡皮擦 (E)", command=self._toggle_eraser).pack(side=tk.LEFT, padx=2)
        ttk.Button(top, text="画笔 (B)", command=lambda: self._set_tool("brush")).pack(side=tk.LEFT, padx=2)
        ttk.Button(top, text="多边形 (M)", command=lambda: self._set_tool("polygon")).pack(side=tk.LEFT, padx=2)
        ttk.Button(top, text="撤销 (Z)", command=self._undo).pack(side=tk.LEFT, padx=2)
        ttk.Button(top, text="保存 (S)", command=self._save).pack(side=tk.LEFT, padx=2)

        self.context_canvas = tk.Canvas(self.window, bg="white", highlightthickness=1,
                                        highlightbackground="black", height=self.CONTEXT_MAX_HEIGHT)
        self.context_canvas.pack(fill=tk.X, padx=8, pady=(2, 5))

        self.main_canvas = tk.Canvas(self.window, bg="black", highlightthickness=1,
                                     highlightbackground="black", cursor="crosshair")
        self.main_canvas.pack(expand=True, fill=tk.BOTH, padx=8, pady=3)
        self.main_canvas.bind("<ButtonPress-1>", self._mouse_down)
        self.main_canvas.bind("<B1-Motion>", self._mouse_drag)
        self.main_canvas.bind("<ButtonRelease-1>", self._mouse_up)

        bottom = ttk.Frame(self.window, padding=5)
        bottom.pack(fill=tk.X)
        ttk.Button(bottom, text="上一张 (P/←)", command=self._previous).pack(side=tk.LEFT, padx=4)
        ttk.Button(bottom, text="保存并下一张 (N/→)", command=self._next).pack(side=tk.LEFT, padx=4)
        self.status_label = ttk.Label(bottom, text="")
        self.status_label.pack(side=tk.LEFT, padx=18)

    def _bind_keys(self):
        bindings = {
            "g": lambda _: self._set_mode("gt"),
            "i": lambda _: self._set_mode("ignore"),
            "e": lambda _: self._toggle_eraser(),
            "b": lambda _: self._set_tool("brush"),
            "m": lambda _: self._set_tool("polygon"),
            "z": lambda _: self._undo(),
            "s": lambda _: self._save(),
            "n": lambda _: self._next(),
            "p": lambda _: self._previous(),
            "<Right>": lambda _: self._next(),
            "<Left>": lambda _: self._previous(),
            "<Return>": lambda _: self._finish_polygon(),
            "<Escape>": lambda _: self._cancel_polygon(),
            "<plus>": lambda _: self._change_brush(2),
            "<equal>": lambda _: self._change_brush(2),
            "<minus>": lambda _: self._change_brush(-2),
        }
        for key, callback in bindings.items():
            if key.startswith("<"):
                self.window.bind(key, callback)
            else:
                self.window.bind(f"<KeyPress-{key}>", callback)
                if key.isalpha():
                    self.window.bind(f"<KeyPress-{key.upper()}>", callback)

    def _paths(self, item):
        sequence = item["sequence"]
        frame_id = int(item["frame_id"])
        stem = f"frame_{frame_id:04d}"
        directory = self.annotation_root / sequence
        return {
            "rgb": directory / f"{stem}_rgb.png",
            "context": directory / f"{stem}_context.png",
            "gt": directory / f"{stem}_gt.png",
            "ignore": directory / f"{stem}_ignore.png",
        }

    @staticmethod
    def _read_binary_mask(path: Path, shape):
        mask = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
        if mask is None:
            raise RuntimeError(f"cannot read mask: {path}")
        if mask.shape != shape:
            raise RuntimeError(f"mask size mismatch: {path}: {mask.shape} != {shape}")
        values = set(np.unique(mask).tolist())
        if not values.issubset({0, 255}):
            raise RuntimeError(f"mask contains values other than 0/255: {path}: {values}")
        return mask

    def _load_current(self):
        self._cancel_polygon()
        item = self.items[self.index]
        paths = self._paths(item)
        self.rgb = cv2.imread(str(paths["rgb"]), cv2.IMREAD_COLOR)
        context = cv2.imread(str(paths["context"]), cv2.IMREAD_COLOR)
        if self.rgb is None or context is None:
            raise RuntimeError(f"missing RGB/context for {item['sequence']} frame {item['frame_id']}")
        shape = self.rgb.shape[:2]
        self.gt = self._read_binary_mask(paths["gt"], shape)
        self.ignore = self._read_binary_mask(paths["ignore"], shape)
        record = self.progress.get((item["sequence"], int(item["frame_id"])), {})
        self.completed_var.set(bool(record.get("completed", 0)))
        self.undo_stack.clear()
        self.dirty = False
        self._render_context(context)
        self._render_main()
        self._update_labels("已加载")

    def _render_context(self, context):
        rgb = cv2.cvtColor(context, cv2.COLOR_BGR2RGB)
        image = Image.fromarray(rgb)
        scale = min(self.CONTEXT_MAX_WIDTH / image.width,
                    self.CONTEXT_MAX_HEIGHT / image.height, 1.0)
        size = (max(1, round(image.width * scale)), max(1, round(image.height * scale)))
        image = image.resize(size, Image.Resampling.LANCZOS)
        self.context_photo = ImageTk.PhotoImage(image)
        self.context_canvas.config(height=size[1], scrollregion=(0, 0, size[0], size[1]))
        self.context_canvas.delete("all")
        self.context_canvas.create_image(self.CONTEXT_MAX_WIDTH / 2, 0,
                                         image=self.context_photo, anchor=tk.N)

    def _composite(self):
        base = Image.fromarray(cv2.cvtColor(self.rgb, cv2.COLOR_BGR2RGB)).convert("RGBA")
        overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
        pixels = np.zeros((base.height, base.width, 4), dtype=np.uint8)
        pixels[self.gt == 255] = (*self.GT_COLOR, self.OVERLAY_ALPHA)
        pixels[self.ignore == 255] = (*self.IGNORE_COLOR, self.OVERLAY_ALPHA)
        overlay = Image.fromarray(pixels, "RGBA")
        return Image.alpha_composite(base, overlay).convert("RGB")

    def _render_main(self):
        image = self._composite()
        self.scale = min(self.DISPLAY_MAX_WIDTH / image.width,
                         self.DISPLAY_MAX_HEIGHT / image.height, 1.5)
        self.display_size = (round(image.width * self.scale), round(image.height * self.scale))
        image = image.resize(self.display_size, Image.Resampling.LANCZOS)
        self.main_photo = ImageTk.PhotoImage(image)
        self.main_canvas.delete("all")
        self.main_canvas.config(width=self.display_size[0], height=self.display_size[1],
                                scrollregion=(0, 0, *self.display_size))
        self.main_canvas.create_image(0, 0, image=self.main_photo, anchor=tk.NW, tags="image")
        self._draw_polygon_preview()

    def _canvas_to_image(self, event):
        x = int(round(self.main_canvas.canvasx(event.x) / self.scale))
        y = int(round(self.main_canvas.canvasy(event.y) / self.scale))
        height, width = self.gt.shape
        return max(0, min(width - 1, x)), max(0, min(height - 1, y))

    def _active_mask(self):
        return self.gt if self.mode == "gt" else self.ignore

    def _push_undo(self):
        self.undo_stack.append((self.gt.copy(), self.ignore.copy()))
        if len(self.undo_stack) > 30:
            self.undo_stack.pop(0)

    def _mouse_down(self, event):
        point = self._canvas_to_image(event)
        if self.tool == "polygon":
            if not self.polygon_points:
                self._push_undo()
            self.polygon_points.append(point)
            self.dirty = True
            self._render_main()
            return
        self._push_undo()
        self.dragging = True
        self.last_point = point
        self._paint_line(point, point)

    def _mouse_drag(self, event):
        if self.tool != "brush" or not self.dragging:
            return
        point = self._canvas_to_image(event)
        self._paint_line(self.last_point, point)
        self.last_point = point

    def _mouse_up(self, _event):
        self.dragging = False
        self.last_point = None

    def _paint_line(self, start, end):
        value = 0 if self.eraser else 255
        cv2.line(self._active_mask(), start, end, value, self.brush_size, cv2.LINE_8)
        self.dirty = True
        self._render_main()

    def _draw_polygon_preview(self):
        if not self.polygon_points:
            return
        coords = []
        for x, y in self.polygon_points:
            coords.extend((x * self.scale, y * self.scale))
        color = "#00aa00" if self.mode == "gt" else "#d6a800"
        if len(coords) >= 4:
            self.main_canvas.create_line(*coords, fill=color, width=2, tags="polygon")
        for i in range(0, len(coords), 2):
            x, y = coords[i], coords[i + 1]
            self.main_canvas.create_oval(x - 3, y - 3, x + 3, y + 3,
                                         outline=color, fill="white", tags="polygon")

    def _finish_polygon(self):
        if self.tool != "polygon" or len(self.polygon_points) < 3:
            self._update_labels("多边形至少需要3个点")
            return
        points = np.array(self.polygon_points, dtype=np.int32)
        value = 0 if self.eraser else 255
        cv2.fillPoly(self._active_mask(), [points], value, lineType=cv2.LINE_8)
        self.polygon_points = []
        self.dirty = True
        self._render_main()
        self._update_labels("多边形已填充")

    def _cancel_polygon(self):
        if self.polygon_points and self.undo_stack:
            # No mask pixels have been committed yet; discard its pending undo snapshot.
            self.undo_stack.pop()
        self.polygon_points = []
        if self.rgb is not None:
            self._render_main()

    def _undo(self):
        if self.polygon_points:
            self.polygon_points.pop()
            if not self.polygon_points and self.undo_stack:
                self.undo_stack.pop()
            self._render_main()
            return
        if not self.undo_stack:
            self._update_labels("没有可撤销操作")
            return
        self.gt, self.ignore = self.undo_stack.pop()
        self.dirty = True
        self._render_main()
        self._update_labels("已撤销")

    def _set_mode(self, mode):
        if self.polygon_points:
            self._cancel_polygon()
        self.mode = mode
        self.eraser = False
        self._update_labels("切换图层")

    def _set_tool(self, tool):
        if self.polygon_points:
            self._cancel_polygon()
        self.tool = tool
        self._update_labels("切换工具")

    def _toggle_eraser(self):
        self.eraser = not self.eraser
        self._update_labels("橡皮擦已开启" if self.eraser else "橡皮擦已关闭")

    def _change_brush(self, delta):
        self.brush_size = max(1, min(100, self.brush_size + delta))
        self._update_labels("调整画笔")

    def _completion_changed(self):
        self.dirty = True
        self._update_labels("完成状态已修改，按S保存")

    @staticmethod
    def _atomic_mask_write(path: Path, mask):
        binary = np.where(mask > 0, 255, 0).astype(np.uint8)
        fd, temporary_name = tempfile.mkstemp(prefix=path.stem + ".", suffix=".png", dir=path.parent)
        os.close(fd)
        temporary = Path(temporary_name)
        try:
            if not cv2.imwrite(str(temporary), binary):
                raise RuntimeError(f"failed to write mask: {temporary}")
            verify = cv2.imread(str(temporary), cv2.IMREAD_UNCHANGED)
            if verify is None or verify.dtype != np.uint8 or verify.ndim != 2:
                raise RuntimeError(f"invalid saved mask format: {temporary}")
            if verify.shape != binary.shape or not set(np.unique(verify)).issubset({0, 255}):
                raise RuntimeError(f"invalid saved mask values/size: {temporary}")
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)

    def _write_progress(self):
        rows = []
        for item in self.items:
            key = (item["sequence"], int(item["frame_id"]))
            record = self.progress.get(key, {"gt_nonzero_pixels": 0,
                                             "ignore_nonzero_pixels": 0,
                                             "completed": 0})
            rows.append({"sequence": key[0], "frame_id": key[1], **record})
        fd, name = tempfile.mkstemp(prefix="annotation_progress.", suffix=".csv", dir=self.root)
        os.close(fd)
        temporary = Path(name)
        try:
            with temporary.open("w", newline="", encoding="utf-8") as stream:
                fields = ["sequence", "frame_id", "gt_nonzero_pixels",
                          "ignore_nonzero_pixels", "completed"]
                writer = csv.DictWriter(stream, fieldnames=fields)
                writer.writeheader(); writer.writerows(rows)
            os.replace(temporary, self.progress_csv)
        finally:
            temporary.unlink(missing_ok=True)

    def _save(self):
        if self.polygon_points:
            if len(self.polygon_points) >= 3:
                self._finish_polygon()
            else:
                self._cancel_polygon()
        item = self.items[self.index]
        paths = self._paths(item)
        self._atomic_mask_write(paths["gt"], self.gt)
        self._atomic_mask_write(paths["ignore"], self.ignore)
        key = (item["sequence"], int(item["frame_id"]))
        self.progress[key] = {
            "gt_nonzero_pixels": int(np.count_nonzero(self.gt)),
            "ignore_nonzero_pixels": int(np.count_nonzero(self.ignore)),
            "completed": int(self.completed_var.get()),
        }
        self._write_progress()
        self.dirty = False
        self._update_labels("已保存")
        return True

    def _next(self):
        if not self._save():
            return
        if self.index + 1 < len(self.items):
            self.index += 1
            self._load_current()
        else:
            messagebox.showinfo("P4标注", "已经到达最后一帧。")

    def _previous(self):
        if not self._confirm_unsaved():
            return
        if self.index > 0:
            self.index -= 1
            self._load_current()

    def _confirm_unsaved(self):
        if not self.dirty:
            return True
        result = messagebox.askyesnocancel("未保存修改", "保存当前修改后继续吗？")
        if result is None:
            return False
        if result:
            return self._save()
        return True

    def _close(self):
        if self._confirm_unsaved():
            self.window.destroy()

    def _update_labels(self, status=""):
        item = self.items[self.index]
        self.progress_label.config(
            text=f"{self.index + 1} / {len(self.items)}    {item['sequence']}    frame {int(item['frame_id']):04d}")
        action = "Erase" if self.eraser else "Draw"
        self.mode_label.config(
            text=f"Layer: {self.mode.upper()} | Tool: {self.tool} | {action} | Brush: {self.brush_size}px")
        self.status_label.config(text=status)


def validate_dataset(root: Path):
    selected = root / "selected_frames_v2.csv"
    with selected.open(newline="", encoding="utf-8-sig") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != 120:
        raise RuntimeError(f"expected 120 rows, found {len(rows)}")
    counts = {"rgb": 0, "context": 0, "gt": 0, "ignore": 0}
    for row in rows:
        directory = root / "annotation_v2" / row["sequence"]
        stem = f"frame_{int(row['frame_id']):04d}"
        images = {
            "rgb": cv2.imread(str(directory / f"{stem}_rgb.png"), cv2.IMREAD_COLOR),
            "context": cv2.imread(str(directory / f"{stem}_context.png"), cv2.IMREAD_COLOR),
            "gt": cv2.imread(str(directory / f"{stem}_gt.png"), cv2.IMREAD_UNCHANGED),
            "ignore": cv2.imread(str(directory / f"{stem}_ignore.png"), cv2.IMREAD_UNCHANGED),
        }
        if any(image is None for image in images.values()):
            raise RuntimeError(f"missing image for {row['sequence']} {stem}")
        shape = images["rgb"].shape[:2]
        for key in ("gt", "ignore"):
            mask = images[key]
            if mask.ndim != 2 or mask.dtype != np.uint8 or mask.shape != shape:
                raise RuntimeError(f"invalid {key} format for {row['sequence']} {stem}")
            if not set(np.unique(mask)).issubset({0, 255}):
                raise RuntimeError(f"non-binary {key} for {row['sequence']} {stem}")
        for key in counts:
            counts[key] += 1
    print("P4 annotation dataset check: PASS")
    print("frames=120", " ".join(f"{key}={value}" for key, value in counts.items()))


def initialize_progress(root: Path):
    target = root / "annotation_progress.csv"
    existing = {}
    if target.exists():
        with target.open(newline="", encoding="utf-8-sig") as stream:
            for row in csv.DictReader(stream):
                existing[(row["sequence"], int(row["frame_id"]))] = int(row.get("completed", 0) or 0)
    with (root / "selected_frames_v2.csv").open(newline="", encoding="utf-8-sig") as stream:
        selected = list(csv.DictReader(stream))
    rows = []
    for item in selected:
        sequence, frame_id = item["sequence"], int(item["frame_id"])
        directory = root / "annotation_v2" / sequence
        stem = f"frame_{frame_id:04d}"
        gt = cv2.imread(str(directory / f"{stem}_gt.png"), cv2.IMREAD_GRAYSCALE)
        ignore = cv2.imread(str(directory / f"{stem}_ignore.png"), cv2.IMREAD_GRAYSCALE)
        if gt is None or ignore is None:
            raise RuntimeError(f"missing mask for {sequence} {stem}")
        rows.append({"sequence": sequence, "frame_id": frame_id,
                     "gt_nonzero_pixels": int(np.count_nonzero(gt)),
                     "ignore_nonzero_pixels": int(np.count_nonzero(ignore)),
                     "completed": existing.get((sequence, frame_id), 0)})
    fd, name = tempfile.mkstemp(prefix="annotation_progress.", suffix=".csv", dir=root)
    os.close(fd)
    temporary = Path(name)
    try:
        with temporary.open("w", newline="", encoding="utf-8") as stream:
            fields = ["sequence", "frame_id", "gt_nonzero_pixels",
                      "ignore_nonzero_pixels", "completed"]
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader(); writer.writerows(rows)
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)
    print(f"initialized {target} with {len(rows)} rows")


def main():
    parser = argparse.ArgumentParser(description="P4 local manual mask annotation GUI")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT,
                        help="P4 experiment root containing selected_frames_v2.csv and annotation_v2/")
    parser.add_argument("--check", action="store_true",
                        help="validate the 120-frame annotation dataset without opening a GUI")
    parser.add_argument("--initialize-progress", action="store_true",
                        help="create/update annotation_progress.csv without opening a GUI")
    args = parser.parse_args()
    if args.check:
        validate_dataset(args.root.resolve())
        return
    if args.initialize_progress:
        initialize_progress(args.root.resolve())
        return
    window = tk.Tk()
    try:
        AnnotationApp(window, args.root.resolve())
    except Exception as exc:
        window.withdraw()
        messagebox.showerror("P4标注工具启动失败", str(exc))
        window.destroy()
        raise
    window.mainloop()


if __name__ == "__main__":
    main()
