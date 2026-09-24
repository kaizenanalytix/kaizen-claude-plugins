#!/usr/bin/env python3
"""
update_raid_log.py — safely populate or update a Kaizen RAID Log workbook.

This is the single, shared engine used by the raid-raci-setup skill for BOTH
first-time setup and ongoing updates. Keeping the "don't clobber the log"
logic in one tested place means every run behaves the same:

  * IDs continue from the max already used per sheet (never restart at 1).
  * Existing rows and manual EL/client edits are preserved.
  * Formulas, header rows, dropdowns and formatting from the template survive
    (we load with openpyxl defaults and only touch data cells).
  * New rows carry a provenance tag in their Notes column so the log is
    auditable AND so re-running the same source doesn't create duplicates.

It does NOT decide *what* to extract — that judgement lives with the skill.
This script just takes already-extracted items as JSON and writes them safely.

--------------------------------------------------------------------------
USAGE
--------------------------------------------------------------------------
  # Setup (fresh copy of the template): clear the template's example rows first
  python update_raid_log.py --workbook "<RAID>.xlsx" --items items.json \
      --source-tag "KT Brief" --clear-examples

  # Update (existing log): append new items, skip anything already ingested
  python update_raid_log.py --workbook "<RAID>.xlsx" --items items.json \
      --source-tag 'Email "Re: data access" 2026-07-10'

  # Apply EL-approved changes to existing rows (status/owner/etc.)
  python update_raid_log.py --workbook "<RAID>.xlsx" --updates updates.json

  # Dry run: report what WOULD change without writing (for the EL preview gate)
  python update_raid_log.py --workbook "<RAID>.xlsx" --items items.json \
      --source-tag "MoM 2026-07-08" --dry-run

--------------------------------------------------------------------------
items.json SHAPE  (every field optional except the sheet's content key)
--------------------------------------------------------------------------
{
  "header": {"project_name": "...", "kaizen_pm": "...", "client_pm": "..."},
  "staff":  ["Blair", "Bobby", ...],
  "risks":    [{"date":"2026-07-10","created_by":"..","description":"..",
                "likelihood":"Medium","impact":"High","owner":"..",
                "strategy":"Mitigation","mitigating_action":"..",
                "contingent_action":"..","progress":"..","status":"Open",
                "notes":".."}],
  "actions":  [{"category":"..","date":"..","requested_by":"..",
                "priority":"High","description":"..","owner":"..",
                "expected_resolution":"..","status":"Open",
                "date_resolved":"..","notes":".."}],
  "issues":   [ ...same fields as actions... ],
  "decisions":[{"date":"..","category":"..","decision":"..","details":"..",
                "status":"Confirmed","comments":".."}]
}

updates.json SHAPE (approved edits to existing rows, matched by sheet + ID):
  [{"sheet":"Risks","id":3,"set":{"status":"Complete","progress":"Closed 7/11"}}]
"""

import argparse
import datetime as _dt
import json
import re
import sys

try:
    import openpyxl
except ImportError:
    sys.exit("openpyxl not installed. Run: pip install openpyxl --break-system-packages")

HEADER_ROW = 7          # column headers live on row 7 in every log sheet
DATA_START = 8          # data rows begin on row 8

# Per-sheet column maps. "content_key" is the column that marks a row as "used";
# an empty content cell means the row is available for a new entry.
SHEETS = {
    "Risks": {
        "content_key": 4,       # D = Risk description
        "notes_col": 13,        # M = Notes (where provenance is stamped)
        "id_col": 1,
        "fields": {
            "date": 2, "created_by": 3, "description": 4, "likelihood": 5,
            "impact": 6, "owner": 7, "strategy": 8, "mitigating_action": 9,
            "contingent_action": 10, "progress": 11, "status": 12, "notes": 13,
        },
    },
    "Actions": {
        "content_key": 6,       # F = Description
        "notes_col": 11,        # K = Notes / Details
        "id_col": 1,
        "fields": {
            "category": 2, "date": 3, "requested_by": 4, "priority": 5,
            "description": 6, "owner": 7, "expected_resolution": 8,
            "status": 9, "date_resolved": 10, "notes": 11,
        },
    },
    "Issues": {
        "content_key": 6,
        "notes_col": 11,
        "id_col": 1,
        "fields": {
            "category": 2, "date": 3, "requested_by": 4, "priority": 5,
            "description": 6, "owner": 7, "expected_resolution": 8,
            "status": 9, "date_resolved": 10, "notes": 11,
        },
    },
    "Decisions": {
        "content_key": 4,       # D = Decision
        "notes_col": 7,         # G = Additional Comments
        "id_col": 1,
        "fields": {
            "date": 2, "category": 3, "decision": 4, "details": 5,
            "status": 6, "comments": 7,
        },
    },
}
# Which JSON list feeds which sheet, and the content field within each item.
LIST_TO_SHEET = {
    "risks": ("Risks", "description"),
    "actions": ("Actions", "description"),
    "issues": ("Issues", "description"),
    "decisions": ("Decisions", "decision"),
}


def _norm(text):
    """Normalize free text for duplicate detection."""
    return re.sub(r"\s+", " ", str(text or "").strip().lower())


def _is_formula(cell):
    return isinstance(cell.value, str) and cell.value.startswith("=")


def _used_rows(ws, content_col):
    """Row numbers (>= DATA_START) whose content cell is non-empty."""
    rows = []
    for r in range(DATA_START, ws.max_row + 1):
        v = ws.cell(r, content_col).value
        if v not in (None, ""):
            rows.append(r)
    return rows


def _existing_signatures(ws, cfg):
    """Set of normalized content strings AND provenance tags already present."""
    sigs, tags = set(), set()
    for r in _used_rows(ws, cfg["content_key"]):
        sigs.add(_norm(ws.cell(r, cfg["content_key"]).value))
        note = ws.cell(r, cfg["notes_col"]).value
        for m in re.findall(r"\[Source:[^\]]*\]", str(note or "")):
            tags.add(m.strip())
    return sigs, tags


def _next_row_and_id(ws, cfg):
    """First writable data row and the next sequential ID."""
    used = _used_rows(ws, cfg["content_key"])
    if used:
        next_row = max(used) + 1
    else:
        next_row = DATA_START
    # IDs may be pre-seeded in the template even on empty rows; derive the max
    # *real* id from used rows, else fall back to count.
    max_id = 0
    for r in used:
        v = ws.cell(r, cfg["id_col"]).value
        if isinstance(v, (int, float)):
            max_id = max(max_id, int(v))
    return next_row, max_id + 1


def _clear_examples(ws, cfg):
    """Blank out the template's demo data rows (keep headers & formulas)."""
    for r in range(DATA_START, ws.max_row + 1):
        for c in range(1, ws.max_column + 1):
            cell = ws.cell(r, c)
            if _is_formula(cell):
                continue
            cell.value = None


def _provenance(source_tag):
    if not source_tag:
        return ""
    today = _dt.date.today().isoformat()
    tag = source_tag if source_tag.startswith("[Source:") else f"[Source: {source_tag}]"
    return tag if "20" in source_tag else f"{tag[:-1]} ({today})]"


def apply_items(wb, items, source_tag, clear_examples, dry_run):
    report = {"added": {}, "skipped_duplicates": {}, "staff_added": [], "header": {}}

    # Header cells on the Risks sheet feed the other tabs by formula.
    hdr = items.get("header") or {}
    if hdr and "Risks" in wb.sheetnames:
        ws = wb["Risks"]
        cellmap = {"project_name": "B2", "kaizen_pm": "B3", "client_pm": "B4"}
        for key, ref in cellmap.items():
            if hdr.get(key):
                if not dry_run:
                    ws[ref] = hdr[key]
                report["header"][ref] = hdr[key]

    # Staff -> Lookup column A (dropdown source). Append, keep unique.
    staff = items.get("staff") or []
    if staff and "Lookup" in wb.sheetnames:
        ws = wb["Lookup"]
        existing = {_norm(ws.cell(r, 1).value) for r in range(2, ws.max_row + 1)}
        row = ws.max_row + 1
        # find first empty in col A instead of appending past the block
        for r in range(2, ws.max_row + 2):
            if ws.cell(r, 1).value in (None, ""):
                row = r
                break
        for name in staff:
            if _norm(name) and _norm(name) not in existing:
                if not dry_run:
                    ws.cell(row, 1).value = name
                existing.add(_norm(name))
                report["staff_added"].append(name)
                row += 1

    prov = _provenance(source_tag)

    for list_key, (sheet_name, content_field) in LIST_TO_SHEET.items():
        entries = items.get(list_key) or []
        if sheet_name not in wb.sheetnames:
            continue
        ws = wb[sheet_name]
        cfg = SHEETS[sheet_name]

        if clear_examples:
            _clear_examples(ws, cfg)

        sigs, tags = _existing_signatures(ws, cfg)
        next_row, next_id = _next_row_and_id(ws, cfg)
        added, skipped = [], []

        for item in entries:
            content = item.get(content_field) or item.get("description") or item.get("decision")
            sig = _norm(content)
            # Duplicate if same content already present, or same provenance tag
            # already recorded (i.e. this exact source was ingested before).
            if sig and sig in sigs:
                skipped.append(content)
                continue
            if prov and prov in tags:
                skipped.append(content)
                continue

            if not dry_run:
                ws.cell(next_row, cfg["id_col"]).value = next_id
                for field, col in cfg["fields"].items():
                    if field in item and item[field] not in (None, ""):
                        ws.cell(next_row, col).value = item[field]
                # Stamp provenance into the notes column (append if user gave notes).
                if prov:
                    ncol = cfg["notes_col"]
                    cur = ws.cell(next_row, ncol).value
                    ws.cell(next_row, ncol).value = f"{cur} {prov}".strip() if cur else prov

            sigs.add(sig)
            added.append(content)
            next_row += 1
            next_id += 1

        report["added"][sheet_name] = added
        report["skipped_duplicates"][sheet_name] = skipped

    return report


def apply_updates(wb, updates, dry_run):
    """Apply EL-approved edits to existing rows, matched by sheet + ID."""
    report = {"updated": [], "not_found": []}
    for upd in updates:
        sheet_name = upd["sheet"]
        target_id = upd["id"]
        changes = upd.get("set", {})
        if sheet_name not in wb.sheetnames:
            report["not_found"].append(upd)
            continue
        ws = wb[sheet_name]
        cfg = SHEETS[sheet_name]
        found = False
        for r in range(DATA_START, ws.max_row + 1):
            v = ws.cell(r, cfg["id_col"]).value
            if isinstance(v, (int, float)) and int(v) == int(target_id) \
               and ws.cell(r, cfg["content_key"]).value not in (None, ""):
                for field, val in changes.items():
                    col = cfg["fields"].get(field)
                    if col:
                        if not dry_run:
                            ws.cell(r, col).value = val
                report["updated"].append({"sheet": sheet_name, "id": target_id, "set": changes})
                found = True
                break
        if not found:
            report["not_found"].append(upd)
    return report


def main():
    ap = argparse.ArgumentParser(description="Populate/update a Kaizen RAID Log safely.")
    ap.add_argument("--workbook", required=True, help="Path to the RAID Log .xlsx to modify.")
    ap.add_argument("--items", help="Path to items JSON to append.")
    ap.add_argument("--updates", help="Path to updates JSON (edits to existing rows).")
    ap.add_argument("--source-tag", default="",
                    help='Provenance label, e.g. \'Email "Re: data access" 2026-07-10\'.')
    ap.add_argument("--clear-examples", action="store_true",
                    help="Blank the template's demo rows first (use on fresh setup).")
    ap.add_argument("--dry-run", action="store_true",
                    help="Report what would change without writing (for the EL preview).")
    args = ap.parse_args()

    if not args.items and not args.updates:
        ap.error("Provide --items and/or --updates.")

    wb = openpyxl.load_workbook(args.workbook)
    out = {"workbook": args.workbook, "dry_run": args.dry_run}

    if args.items:
        with open(args.items, encoding="utf-8") as fh:
            items = json.load(fh)
        out["items_report"] = apply_items(
            wb, items, args.source_tag, args.clear_examples, args.dry_run
        )
    if args.updates:
        with open(args.updates, encoding="utf-8") as fh:
            updates = json.load(fh)
        out["updates_report"] = apply_updates(wb, updates, args.dry_run)

    if not args.dry_run:
        wb.save(args.workbook)

    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
