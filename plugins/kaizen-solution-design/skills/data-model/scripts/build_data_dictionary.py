#!/usr/bin/env python3
"""Build the Data Dictionary workbook from the same JSON spec used by render_erd.py.

One worksheet per table, plus a summary "Index" sheet listing every table with a jump-link to its
sheet. Requires openpyxl (`pip install openpyxl --break-system-packages`).

Usage:
    python build_data_dictionary.py --spec SPEC.json --out "data-model/Data Dictionary.xlsx"

Spec shape — see render_erd.py's docstring for the full shape; this script only reads
`entities[].name` and `entities[].attributes[]`. Each attribute may include:
  name, type, pk (bool), fk (bool), fk_ref ("table.column"), nullable (bool),
  business_definition, source_system, scd_type, sample_value, notes
"""
import argparse, json, re, sys

COLUMNS = [
    ("Table Name", 18),
    ("Column Name", 24),
    ("Data Type", 18),
    ("PK / FK", 12),
    ("Nullable", 10),
    ("Business Definition", 45),
    ("Source System", 16),
    ("SCD Type", 12),
    ("Sample Value", 18),
    ("Notes", 30),
]

HEADER_FILL = "0A2342"  # Kaizen navy
HEADER_FONT_COLOR = "FFFFFF"


def safe_sheet_name(name, used):
    """Excel sheet names: <=31 chars, no []:*?/\\, must be unique."""
    cleaned = re.sub(r"[\[\]\:\*\?/\\]", "_", name)[:31]
    base = cleaned
    n = 1
    while cleaned in used:
        suffix = "_%d" % n
        cleaned = base[: 31 - len(suffix)] + suffix
        n += 1
    used.add(cleaned)
    return cleaned


def pk_fk_label(attr):
    parts = []
    if attr.get("pk"):
        parts.append("PK")
    if attr.get("fk"):
        ref = attr.get("fk_ref", "")
        parts.append("FK -> %s" % ref if ref else "FK")
    return ", ".join(parts)


def main():
    ap = argparse.ArgumentParser(description="Build the Data Dictionary workbook from a JSON spec.")
    ap.add_argument("--spec", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment
        from openpyxl.worksheet.hyperlink import Hyperlink
        from openpyxl.utils import get_column_letter
    except ImportError:
        print("openpyxl is required: pip install openpyxl --break-system-packages", file=sys.stderr)
        sys.exit(1)

    with open(args.spec, encoding="utf-8") as f:
        spec = json.load(f)

    entities = spec.get("entities", [])
    title = spec.get("title", "Data Model")

    wb = Workbook()
    index_ws = wb.active
    index_ws.title = "Index"

    index_ws["A1"] = title
    index_ws["A1"].font = Font(bold=True, size=14)
    index_ws["A3"] = "Table Name"
    index_ws["B3"] = "Kind"
    index_ws["C3"] = "# Columns"
    for c in ("A3", "B3", "C3"):
        index_ws[c].font = Font(bold=True, color=HEADER_FONT_COLOR)
        index_ws[c].fill = PatternFill("solid", fgColor=HEADER_FILL)
    index_ws.column_dimensions["A"].width = 28
    index_ws.column_dimensions["B"].width = 14
    index_ws.column_dimensions["C"].width = 12

    used_sheet_names = {"Index"}
    row_num = 4
    for entity in entities:
        name = entity["name"]
        attrs = entity.get("attributes", [])
        sheet_name = safe_sheet_name(name, used_sheet_names)
        ws = wb.create_sheet(sheet_name)

        # header row
        for col_idx, (col_name, width) in enumerate(COLUMNS, start=1):
            cell = ws.cell(row=1, column=col_idx, value=col_name)
            cell.font = Font(bold=True, color=HEADER_FONT_COLOR)
            cell.fill = PatternFill("solid", fgColor=HEADER_FILL)
            ws.column_dimensions[get_column_letter(col_idx)].width = width

        for r, attr in enumerate(attrs, start=2):
            ws.cell(row=r, column=1, value=name)
            ws.cell(row=r, column=2, value=attr.get("name", ""))
            ws.cell(row=r, column=3, value=attr.get("type", ""))
            ws.cell(row=r, column=4, value=pk_fk_label(attr))
            ws.cell(row=r, column=5, value="N" if attr.get("nullable") is False else ("Y" if attr.get("nullable") else ""))
            ws.cell(row=r, column=6, value=attr.get("business_definition", ""))
            ws.cell(row=r, column=7, value=attr.get("source_system", ""))
            ws.cell(row=r, column=8, value=attr.get("scd_type", ""))
            ws.cell(row=r, column=9, value=attr.get("sample_value", ""))
            ws.cell(row=r, column=10, value=attr.get("notes", ""))
            for col_idx in range(1, len(COLUMNS) + 1):
                ws.cell(row=r, column=col_idx).alignment = Alignment(wrap_text=True, vertical="top")

        ws.freeze_panes = "A2"

        # index row with a link to the sheet
        idx_cell = index_ws.cell(row=row_num, column=1, value=name)
        idx_cell.hyperlink = "#'%s'!A1" % sheet_name
        idx_cell.font = Font(color="0563C1", underline="single")
        index_ws.cell(row=row_num, column=2, value=entity.get("kind", "table"))
        index_ws.cell(row=row_num, column=3, value=len(attrs))
        row_num += 1

    wb.save(args.out)
    print("Data dictionary written: %s (%d tables)" % (args.out, len(entities)))


if __name__ == "__main__":
    main()
