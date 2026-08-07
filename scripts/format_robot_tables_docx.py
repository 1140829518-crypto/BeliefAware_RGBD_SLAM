#!/usr/bin/env python3
"""Format numbered paper tables in a DOCX as Robot-journal three-line tables.

The script only edits table/caption formatting and English caption prefixes.
It keeps all table cell text unchanged.
"""

from __future__ import annotations

import re
import shutil
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "修订版 - 副本.docx"
OUTPUT = ROOT / "修订版 - 副本_表格三线表.docx"
REPORT = ROOT / "table_format_check.txt"

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W}

ET.register_namespace("w", W)
ET.register_namespace("r", "http://schemas.openxmlformats.org/officeDocument/2006/relationships")
ET.register_namespace("wp", "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing")
ET.register_namespace("a", "http://schemas.openxmlformats.org/drawingml/2006/main")
ET.register_namespace("pic", "http://schemas.openxmlformats.org/drawingml/2006/picture")
ET.register_namespace("w14", "http://schemas.microsoft.com/office/word/2010/wordml")
ET.register_namespace("mc", "http://schemas.openxmlformats.org/markup-compatibility/2006")


def qn(tag: str) -> str:
    return f"{{{W}}}{tag}"


def attr(name: str) -> str:
    return qn(name)


def block_tag(elem: ET.Element) -> str:
    return elem.tag.rsplit("}", 1)[-1]


def text_of(elem: ET.Element) -> str:
    return "".join(t.text or "" for t in elem.findall(".//w:t", NS)).strip()


def direct_cell_texts(tbl: ET.Element) -> list[list[str]]:
    rows: list[list[str]] = []
    for tr in tbl.findall("w:tr", NS):
        row = []
        for tc in tr.findall("w:tc", NS):
            row.append(text_of(tc))
        rows.append(row)
    return rows


def ensure_child(parent: ET.Element, tag: str, first: bool = False) -> ET.Element:
    child = parent.find(f"w:{tag}", NS)
    if child is None:
        child = ET.Element(qn(tag))
        if first:
            parent.insert(0, child)
        else:
            parent.append(child)
    return child


def ensure_props(elem: ET.Element, prop_tag: str) -> ET.Element:
    props = elem.find(f"w:{prop_tag}", NS)
    if props is None:
        props = ET.Element(qn(prop_tag))
        elem.insert(0, props)
    return props


def remove_child(parent: ET.Element, tag: str) -> None:
    for child in list(parent):
        if child.tag == qn(tag):
            parent.remove(child)


def set_border(border_parent: ET.Element, edge: str, val: str, size: int | None = None) -> None:
    remove_child(border_parent, edge)
    node = ET.SubElement(border_parent, qn(edge))
    node.set(attr("val"), val)
    if val != "nil":
        node.set(attr("sz"), str(size or 4))
        node.set(attr("space"), "0")
        node.set(attr("color"), "000000")


def set_run_font(run: ET.Element, half_points: int) -> None:
    rpr = run.find("w:rPr", NS)
    if rpr is None:
        rpr = ET.Element(qn("rPr"))
        run.insert(0, rpr)
    rfonts = rpr.find("w:rFonts", NS)
    if rfonts is None:
        rfonts = ET.SubElement(rpr, qn("rFonts"))
    rfonts.set(attr("ascii"), "Times New Roman")
    rfonts.set(attr("hAnsi"), "Times New Roman")
    rfonts.set(attr("cs"), "Times New Roman")
    rfonts.set(attr("eastAsia"), "宋体")
    for size_tag in ("sz", "szCs"):
        size = rpr.find(f"w:{size_tag}", NS)
        if size is None:
            size = ET.SubElement(rpr, qn(size_tag))
        size.set(attr("val"), str(half_points))


def set_scope_font(scope: ET.Element, half_points: int) -> None:
    for run in scope.findall(".//w:r", NS):
        set_run_font(run, half_points)


def set_paragraph_text(paragraph: ET.Element, text: str) -> None:
    texts = paragraph.findall(".//w:t", NS)
    if not texts:
        run = ET.SubElement(paragraph, qn("r"))
        t = ET.SubElement(run, qn("t"))
        t.text = text
        return
    texts[0].text = text
    for t in texts[1:]:
        t.text = ""


def set_paragraph_center(paragraph: ET.Element) -> None:
    ppr = ensure_props(paragraph, "pPr")
    jc = ppr.find("w:jc", NS)
    if jc is None:
        jc = ET.SubElement(ppr, qn("jc"))
    jc.set(attr("val"), "center")


def set_cell_nowrap(tc: ET.Element) -> None:
    tcpr = ensure_props(tc, "tcPr")
    if tcpr.find("w:noWrap", NS) is None:
        ET.SubElement(tcpr, qn("noWrap"))


def set_cell_width(tc: ET.Element, width_dxa: int) -> None:
    tcpr = ensure_props(tc, "tcPr")
    tcw = tcpr.find("w:tcW", NS)
    if tcw is None:
        tcw = ET.SubElement(tcpr, qn("tcW"))
    tcw.set(attr("w"), str(width_dxa))
    tcw.set(attr("type"), "dxa")


def set_table_widths(tbl: ET.Element, paper_no: str, col_count: int) -> None:
    if paper_no.startswith("3"):
        widths = [1700] + [1150] * (col_count - 1)
    elif paper_no == "8":
        widths = [2350] + [1450] * (col_count - 1)
    elif paper_no == "9":
        widths = [2100] + [1600] * (col_count - 1)
    elif col_count >= 6:
        widths = [1800] + [1300] * (col_count - 1)
    else:
        widths = [2200] + [1700] * (col_count - 1)
    for tr in tbl.findall("w:tr", NS):
        cells = tr.findall("w:tc", NS)
        for idx, tc in enumerate(cells):
            set_cell_width(tc, widths[min(idx, len(widths) - 1)])


def format_three_line_table(tbl: ET.Element, paper_no: str) -> None:
    tblpr = ensure_props(tbl, "tblPr")
    borders = tblpr.find("w:tblBorders", NS)
    if borders is None:
        borders = ET.SubElement(tblpr, qn("tblBorders"))
    set_border(borders, "top", "single", 6)
    set_border(borders, "left", "nil")
    set_border(borders, "bottom", "single", 6)
    set_border(borders, "right", "nil")
    set_border(borders, "insideH", "nil")
    set_border(borders, "insideV", "nil")
    layout = tblpr.find("w:tblLayout", NS)
    if layout is None:
        layout = ET.SubElement(tblpr, qn("tblLayout"))
    layout.set(attr("type"), "fixed")

    rows = tbl.findall("w:tr", NS)
    col_count = max((len(tr.findall("w:tc", NS)) for tr in rows), default=0)
    set_table_widths(tbl, paper_no, col_count)

    for ridx, tr in enumerate(rows):
        for cidx, tc in enumerate(tr.findall("w:tc", NS)):
            tcpr = ensure_props(tc, "tcPr")
            remove_child(tcpr, "tcBorders")
            if ridx == 0:
                tcb = ET.SubElement(tcpr, qn("tcBorders"))
                set_border(tcb, "bottom", "single", 4)
            if ridx > 0 or cidx == 0:
                set_cell_nowrap(tc)
            valign = tcpr.find("w:vAlign", NS)
            if valign is None:
                valign = ET.SubElement(tcpr, qn("vAlign"))
            valign.set(attr("val"), "center")
            for p in tc.findall(".//w:p", NS):
                set_paragraph_center(p)
            set_scope_font(tc, 18)


def is_english_caption(text: str) -> bool:
    return bool(re.match(r"^(?:Table\s+\d+|Tab\.\d+)", text.strip()))


def nearest_previous_english_caption(children: list[ET.Element], index: int, max_scan: int = 6) -> str:
    for j in range(index - 1, max(-1, index - max_scan - 1), -1):
        if block_tag(children[j]) != "p":
            continue
        txt = text_of(children[j])
        if not txt:
            continue
        if is_english_caption(txt):
            return txt
        if re.match(r"^表\d+", txt):
            return ""
    return ""


def normalize_english_caption(text: str) -> str:
    return re.sub(r"^Table\s+(\d+)\.?\s*", r"Tab.\1 ", text.strip())


def normalize_chinese_caption(text: str) -> str:
    stripped = text.strip()
    stripped = re.sub(r"^表(\d+)(?![\s（(])", r"表\1 ", stripped)
    return stripped


def main() -> None:
    if not SOURCE.exists():
        raise FileNotFoundError(SOURCE)
    with TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        with zipfile.ZipFile(SOURCE) as zin:
            zin.extractall(tmpdir)

        doc_xml = tmpdir / "word" / "document.xml"
        tree = ET.parse(doc_xml)
        root = tree.getroot()
        body = root.find("w:body", NS)
        if body is None:
            raise RuntimeError("word/body not found")

        children = list(body)
        table_infos: list[dict[str, object]] = []
        caption_updates: list[tuple[str, str]] = []

        for i, child in enumerate(children):
            if block_tag(child) != "p":
                continue
            txt = text_of(child)
            new_txt = None
            if is_english_caption(txt):
                new_txt = normalize_english_caption(txt)
            elif re.match(r"^表\d+", txt):
                next_txt = text_of(children[i + 1]) if i + 1 < len(children) else ""
                if is_english_caption(next_txt):
                    new_txt = normalize_chinese_caption(txt)
            if new_txt and new_txt != txt:
                caption_updates.append((txt, new_txt))
                set_paragraph_text(child, new_txt)
            if new_txt or is_english_caption(txt) or re.match(r"^表\d+", txt):
                set_scope_font(child, 24)
                set_paragraph_center(child)

        for i, child in enumerate(children):
            if block_tag(child) != "tbl":
                continue
            prev_txt = nearest_previous_english_caption(children, i)
            if not is_english_caption(prev_txt):
                continue
            m = re.match(r"^Tab\.(\d+(?:\([ab]\))?)", prev_txt)
            paper_no = m.group(1) if m else "unknown"
            before = direct_cell_texts(child)
            format_three_line_table(child, paper_no)
            after = direct_cell_texts(child)
            table_infos.append(
                {
                    "paper_no": paper_no,
                    "caption": prev_txt,
                    "rows": len(before),
                    "cols": max((len(r) for r in before), default=0),
                    "data_unchanged": before == after,
                }
            )

        tree.write(doc_xml, encoding="UTF-8", xml_declaration=True)
        with zipfile.ZipFile(OUTPUT, "w", zipfile.ZIP_DEFLATED) as zout:
            for path in tmpdir.rglob("*"):
                if path.is_file():
                    zout.write(path, path.relative_to(tmpdir))

    # Re-open the output XML for border checks.
    with zipfile.ZipFile(OUTPUT) as z:
        out_root = ET.fromstring(z.read("word/document.xml"))
    out_body = out_root.find("w:body", NS)
    out_children = list(out_body) if out_body is not None else []
    border_findings = []
    formatted_count = 0
    for i, child in enumerate(out_children):
        if block_tag(child) != "tbl":
            continue
        prev_txt = nearest_previous_english_caption(out_children, i)
        if not is_english_caption(prev_txt):
            continue
        formatted_count += 1
        tbl_borders = child.find("w:tblPr/w:tblBorders", NS)
        vertical = []
        if tbl_borders is not None:
            for edge in ("left", "right", "insideV"):
                node = tbl_borders.find(f"w:{edge}", NS)
                vertical.append(node is not None and node.get(attr("val")) != "nil")
        cell_vertical = False
        for tc_borders in child.findall(".//w:tcBorders", NS):
            for edge in ("left", "right", "insideV"):
                node = tc_borders.find(f"w:{edge}", NS)
                if node is not None and node.get(attr("val")) != "nil":
                    cell_vertical = True
        border_findings.append((prev_txt, not any(vertical) and not cell_vertical))

    report_lines = [
        "Table Format Check Report",
        "",
        f"Source document: {SOURCE}",
        f"Revised document: {OUTPUT}",
        f"Numbered paper tables formatted: {len(table_infos)}",
        "",
        "1. Caption normalization",
    ]
    if caption_updates:
        report_lines.extend([f"- {old} -> {new}" for old, new in caption_updates])
    else:
        report_lines.append("- No caption text needed replacement.")
    report_lines.extend(["", "2. Table list and three-line status"])
    for info in table_infos:
        report_lines.append(
            f"- Tab.{info['paper_no']}: rows={info['rows']}, cols={info['cols']}, "
            f"data unchanged={'Yes' if info['data_unchanged'] else 'No'}, "
            "three-line borders=Top 0.75 pt / header 0.50 pt / bottom 0.75 pt"
        )
    report_lines.extend(["", "3. Vertical border check"])
    for caption, ok in border_findings:
        report_lines.append(f"- {caption}: {'No vertical borders detected' if ok else 'Vertical border remains'}")
    report_lines.extend(
        [
            "",
            "4. Number wrapping control",
            "- Data-row cells and first-column method/name cells were set to no-wrap.",
            "- Table 3(a), Table 3(b), Table 8, and Table 9 received wider first columns to reduce method-name wrapping.",
            "- Header cells remain allowed to wrap where necessary, especially long sequence names.",
            "",
            "5. Font check",
            "- Table body/header: 9 pt; Latin letters, numbers and symbols use Times New Roman; Chinese text uses SimSun.",
            "- Table captions: 12 pt (小四); Latin letters, numbers and symbols use Times New Roman; Chinese text uses SimSun.",
            "",
            "6. Scope",
            "- No table cell text, experimental value, unit, method name, decimal precision, or table order was changed.",
            "- Formula layout tables and the algorithm pseudo-code table were not converted, to avoid damaging equation/algorithm formatting.",
        ]
    )
    REPORT.write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    print(OUTPUT)
    print(REPORT)


if __name__ == "__main__":
    main()
