#!/usr/bin/env python3
"""
generate_report_card.py — read-only scanner for the Kaizen PDP Project Report Card.

This is a standalone counterpart to project-onboarding/scripts/pdp_onboard.py. It does
NOT import that module and does not create folders, move files, or rename anything — it
only scans whatever phase folders already exist and (re)writes one Excel tracker:

    <PROJECT_ROOT>/7. Project Governance/<PROJECT_ID> - Project Report Card.xlsx

Why a separate script instead of calling into pdp_onboard.py: this tool is meant to be a
fast, dependency-free re-scan someone can run repeatedly (after every sprint, before a
status meeting, etc.) without pulling in the heavier onboarding/reorg workflow. It
deliberately re-encodes the same D1-D41 taxonomy from
kaizen-pdp-phases/references/pdp-checklist.md — if that reference changes, update PHASES
below to match (see the same note in pdp_onboard.py; the two are kept in sync by hand).

Usage:
    python generate_report_card.py --root "<PROJECT_ROOT>" \
        [--project-id "<PROJECT_ID>"] \
        [--engagement-type deliverable-based|capability-pod|managed-analytics|gcc] \
        [--out "<explicit output .xlsx path>"]

Prints a JSON summary to stdout: output path, per-phase folder presence, mandatory
completion counts, and any issues flagged (missing folders, unclassified files).
"""

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
except ImportError:
    print(json.dumps({
        "error": "openpyxl not installed. Run: pip install openpyxl --break-system-packages"
    }))
    sys.exit(1)

# --------------------------------------------------------------------------------------
# Taxonomy — mirrors kaizen-pdp-phases/references/pdp-checklist.md
# --------------------------------------------------------------------------------------
ENGAGEMENT_ORDER = ["deliverable-based", "capability-pod", "managed-analytics", "gcc"]
ENGAGEMENT_LABELS = {
    "deliverable-based": "Deliverable-based",
    "capability-pod": "Capability Pod",
    "managed-analytics": "Managed Analytics",
    "gcc": "GCC",
}
DEFAULT_ENGAGEMENT = "deliverable-based"


@dataclass
class Deliverable:
    id: str
    name: str
    ext: str  # suggested extension for the Expected Filename (F3) column; "—" = no file (e.g. tracked in Jira)
    applies: dict = field(default_factory=dict)

    def is_mandatory(self, engagement: str) -> bool:
        return self.applies.get(engagement, False)


def _ap(code: str) -> dict:
    return {ENGAGEMENT_ORDER[i]: (c.upper() == "Y") for i, c in enumerate(code)}


def _D(i, n, code, ext):
    return Deliverable(i, n, ext, _ap(code))


@dataclass
class Phase:
    index: int
    folder: str
    name: str
    deliverables: list


# code order = deliverable-based, capability-pod, managed-analytics, gcc (see pdp-checklist.md)
PHASES = [
    Phase(0, "0. Sales Alignment", "Sales Alignment", [
        _D("D1", "NDA", "YYYY", "pdf"),
        _D("D2", "Opportunity summary", "YYYY", "docx"),
        _D("D3", "Project scope & estimation summary", "NNNN", "docx"),
        _D("D4", "High-level solution overview diagram", "YYYY", "pptx"),
        _D("D5", "P3 Project Economics", "YYYY", "xlsx"),
        _D("D6", "Deal review committee submission", "NNNN", "pptx"),
        _D("D7", "Client proposal", "YYYY", "pptx"),
        _D("D8", "Data request document", "NNNN", "docx"),
        _D("D9", "MSA", "YYYY", "pdf"),
        _D("D10", "SOW", "YYYY", "pdf"),
    ]),
    Phase(1, "1. Sales Handoff & Transition", "Sales Handoff & Transition", [
        _D("D11", "Internal Kickoff PPT", "YYYY", "pptx"),
        _D("D12", "Project Charter", "NNNN", "docx"),
        _D("D13", "Project technical checklist", "YNYY", "xlsx"),
    ]),
    Phase(2, "2. Plan", "Plan", [
        _D("D14", "Enter User stories in JIRA", "NNNN", "—"),
        _D("D15", "Kickoff document and minutes", "YYYY", "pptx"),
        _D("D16", "Status Report", "YYYY", "xlsx"),
        _D("D17", "Project Plan/WBS", "YNYY", "xlsx"),
    ]),
    Phase(3, "3. Analyze", "Analyze", [
        _D("D18", "Business Requirements, with sign off", "YNYY", "docx"),
        _D("D19", "Validated Data Set", "YNNN", "xlsx"),
        _D("D20", "Change Request Template", "YYYY", "docx"),
    ]),
    Phase(4, "4. Design", "Design", [
        _D("D21", "Technical Design", "YNNN", "docx"),
        _D("D22", "End to End Flows and Data Flow Diagrams", "YNNN", "pptx"),
        _D("D23", "Test Plans", "YNNN", "xlsx"),
        _D("D24", "Training Plans", "YNNN", "docx"),
    ]),
    Phase(5, "5. Develop", "Develop", [
        _D("D25", "Sprint Log", "YNNN", "xlsx"),
        _D("D26", "Issue Log", "YNNY", "xlsx"),
        _D("D27", "Definition of done", "YNNN", "docx"),
        _D("D28", "Testing sign off", "YNNN", "docx"),
    ]),
    Phase(6, "6. Deploy", "Deploy", [
        _D("D29", "Deployment/handoff checklist", "YNYY", "docx"),
        _D("D30", "Project Sign Off", "YYYY", "docx"),
        _D("D31", "Project Close Out", "YYYY", "docx"),
        _D("D32", "Kaizen Case Study", "YYYY", "pptx"),
    ]),
    Phase(7, "7. Project Governance", "Project Governance", [
        _D("D33", "RAID Log", "YYYY", "xlsx"),
        _D("D34", "RACI Chart", "YNYY", "xlsx"),
        _D("D35", "Value Tracker", "YYYY", "xlsx"),
        _D("D36", "Business Continuity Plan (BCP)", "YYYY", "pptx"),
        _D("D37", "Updated project governance scorecard", "YYYY", "xlsx"),
    ]),
    Phase(8, "8. Quality", "Quality", [
        _D("D38", "Customer Satisfaction Survey (CSAT)", "YYYY", "xlsx"),
        _D("D39", "Quality Plan", "NNNN", "docx"),
        _D("D40", "Project Metrics", "NNNN", "xlsx"),
        _D("D41", "Risk assessment Sheet", "NNNN", "xlsx"),
    ]),
]

# --------------------------------------------------------------------------------------
# Styling — same palette used elsewhere in the plugin so every generated workbook looks
# consistent, whether it came from this script or pdp_onboard.py.
# --------------------------------------------------------------------------------------
NAVY = "0A2342"
BAND = "F2F2F2"
GREEN = "C6EFCE"
AMBER = "FFEB9C"
RED = "FFC7CE"

HEADER_FILL = PatternFill("solid", fgColor=NAVY)
HEADER_FONT = Font(color="FFFFFF", bold=True)
BAND_FILL = PatternFill("solid", fgColor=BAND)
TITLE_FONT = Font(color=NAVY, bold=True, size=14)
SUBTITLE_FONT = Font(color=NAVY, bold=True, size=11)
WRAP = Alignment(wrap_text=True, vertical="top")
THIN = Side(style="thin", color="D9D9D9")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)

SKIP_DIRS = {".git", "__pycache__", ".DS_Store"}
SKIP_FILE_PREFIXES = ("~$", ".~")
SKIP_FILE_NAMES = {".DS_Store", "Thumbs.db", ".kaizen-project.json", "Quality - README.md"}
# Never treat a tool-generated tracker as a deliverable file (this script's own output,
# or a tracker from pdp_onboard.py) — otherwise re-runs would "discover" the Report Card
# itself as a deliverable.
TRACKER_SUFFIXES = (
    "- Project Report Card.xlsx",
    "- Phase Checklist.xlsx",
    "- Folder Placement & Naming Audit.xlsx",
    "- Onboarding Audit Trail.xlsx",
    "- Reorg Plan.xlsx",
)

_MATCH_STOPWORDS = {
    "and", "of", "the", "with", "a", "an", "to", "in", "for", "on", "by",
    "sign", "off", "document", "documents", "doc", "template", "final", "draft",
    "project", "updated", "copy", "version",
}


def _sig_tokens(text: str) -> set:
    return {t for t in re.split(r"[^a-z0-9]+", text.lower()) if t and t not in _MATCH_STOPWORDS}


def expected_filename(project_id: str, d: Deliverable) -> str:
    if d.ext == "—":
        return "(tracked in Jira — no file)"
    return f"{project_id} - {d.name}.{d.ext}"


def _is_skippable(filename: str) -> bool:
    if filename in SKIP_FILE_NAMES:
        return True
    if filename.startswith(SKIP_FILE_PREFIXES):
        return True
    if any(filename.endswith(suf) for suf in TRACKER_SUFFIXES):
        return True
    return False


def _match_deliverable(filename: str, project_id: str, phase_delivs):
    """Best deliverable this file plausibly satisfies, or None. Two conservative signals:
    exact F3 name match, then a token-subset match (every significant word of the
    deliverable name appears in the filename). Read-only — never renames or moves.
    """
    for d in phase_delivs:
        if d.ext != "—" and filename == expected_filename(project_id, d):
            return d
    ftok = _sig_tokens(Path(filename).stem)
    if not ftok:
        return None
    best, best_n = None, 0
    for d in phase_delivs:
        if d.ext == "—":
            continue
        dtok = _sig_tokens(d.name)
        if dtok and dtok.issubset(ftok) and len(dtok) > best_n:
            best, best_n = d, len(dtok)
    return best


def scan_phase(root: Path, phase: Phase, project_id: str):
    """Scan one phase folder (recursively). Returns:
    - folder_exists: bool
    - assignments: {deliverable_id: [filenames]}
    - unclassified: [relative file paths] — files present but matched to no deliverable
    """
    folder = root / phase.folder
    assignments = {d.id: [] for d in phase.deliverables}
    unclassified = []
    if not folder.is_dir():
        return False, assignments, unclassified

    for dirpath, dirnames, filenames in os.walk(folder):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            if _is_skippable(fn):
                continue
            match = _match_deliverable(fn, project_id, phase.deliverables)
            rel = str(Path(dirpath, fn).relative_to(folder))
            if match:
                assignments[match.id].append(rel)
            else:
                unclassified.append(rel)
    return True, assignments, unclassified


def resolve_project_id(root: Path, override: Optional[str]) -> str:
    if override:
        return override
    cfg = root / ".kaizen-project.json"
    if cfg.is_file():
        try:
            data = json.loads(cfg.read_text(encoding="utf-8"))
            if data.get("PROJECT_ID"):
                return data["PROJECT_ID"]
        except (json.JSONDecodeError, OSError):
            pass
    return root.name


def resolve_engagement_type(root: Path, override: Optional[str]) -> str:
    if override:
        return override
    cfg = root / ".kaizen-project.json"
    if cfg.is_file():
        try:
            data = json.loads(cfg.read_text(encoding="utf-8"))
            et = data.get("engagement_type") or data.get("ENGAGEMENT_TYPE")
            if et in ENGAGEMENT_ORDER:
                return et
        except (json.JSONDecodeError, OSError):
            pass
    return DEFAULT_ENGAGEMENT


# --------------------------------------------------------------------------------------
# Workbook building
# --------------------------------------------------------------------------------------
def _style_header_row(ws, row: int, ncols: int):
    for c in range(1, ncols + 1):
        cell = ws.cell(row=row, column=c)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = BORDER


def _color_gate(cell, present, mandatory):
    if mandatory == 0:
        cell.value = "n/a"
        return
    if present >= mandatory:
        cell.fill = PatternFill("solid", fgColor=GREEN)
    elif present == 0:
        cell.fill = PatternFill("solid", fgColor=RED)
    else:
        cell.fill = PatternFill("solid", fgColor=AMBER)


def build_workbook(project_id: str, engagement: str, root_exists_flags, scan_results,
                    generated_at: str, root_label: str) -> Workbook:
    wb = Workbook()

    # ---------------- Dashboard ----------------
    ws = wb.active
    ws.title = "Dashboard"
    ws["A1"] = f"{project_id} — Project Report Card"
    ws["A1"].font = TITLE_FONT
    ws["A2"] = (f"Engagement type: {ENGAGEMENT_LABELS[engagement]}   |   "
                f"Generated: {generated_at}   |   Root: {root_label}")
    ws["A2"].font = SUBTITLE_FONT
    ws["A3"] = ("Read-only scan — reflects what is currently on disk. No files were moved, "
                "renamed, or created by this run.")
    ws["A3"].font = Font(italic=True, color="595959", size=9)

    headers = ["Phase", "Folder", "Deliverables", "Mandatory", "Present", "Mandatory Present",
               "% Mandatory", "Gate Status", "Folder Status", "Unclassified Files"]
    header_row = 5
    for i, h in enumerate(headers, start=1):
        ws.cell(row=header_row, column=i, value=h)
    _style_header_row(ws, header_row, len(headers))

    widths = [22, 26, 12, 11, 9, 17, 12, 13, 13, 17]
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w

    r = header_row + 1
    tot_delivs = tot_mand = tot_present = tot_mand_present = tot_unclassified = 0
    for phase in PHASES:
        folder_exists, assignments, unclassified = scan_results[phase.index]
        n_delivs = len(phase.deliverables)
        n_mand = sum(1 for d in phase.deliverables if d.is_mandatory(engagement))
        n_present = sum(1 for d in phase.deliverables if assignments[d.id])
        n_mand_present = sum(1 for d in phase.deliverables
                              if d.is_mandatory(engagement) and assignments[d.id])
        pct = f"{round(100 * n_mand_present / n_mand)}%" if n_mand else "n/a"
        gate = "PASS" if (n_mand == 0 or n_mand_present >= n_mand) else f"{n_mand_present}/{n_mand} done"

        row_vals = [phase.name, phase.folder, n_delivs, n_mand, n_present, n_mand_present,
                    pct, gate, ("OK" if folder_exists else "⚠ Missing"), len(unclassified)]
        for i, v in enumerate(row_vals, start=1):
            cell = ws.cell(row=r, column=i, value=v)
            cell.border = BORDER
            if phase.index % 2 == 0:
                cell.fill = BAND_FILL
        _color_gate(ws.cell(row=r, column=8), n_mand_present, n_mand)
        if not folder_exists:
            ws.cell(row=r, column=9).fill = PatternFill("solid", fgColor=RED)
        elif unclassified:
            ws.cell(row=r, column=10).fill = PatternFill("solid", fgColor=AMBER)

        tot_delivs += n_delivs
        tot_mand += n_mand
        tot_present += n_present
        tot_mand_present += n_mand_present
        tot_unclassified += len(unclassified)
        r += 1

    total_pct = f"{round(100 * tot_mand_present / tot_mand)}%" if tot_mand else "n/a"
    total_gate = "PASS" if tot_mand_present >= tot_mand else f"{tot_mand_present}/{tot_mand} done"
    bold = Font(bold=True)
    tot_row = [("TOTAL", None), (None, None), (tot_delivs, None), (tot_mand, None),
               (tot_present, None), (tot_mand_present, None), (total_pct, None),
               (total_gate, None), (None, None), (tot_unclassified, None)]
    for i, (v, _) in enumerate(tot_row, start=1):
        cell = ws.cell(row=r, column=i, value=v)
        cell.font = bold
        cell.border = BORDER
    ws.freeze_panes = ws.cell(row=header_row + 1, column=1).coordinate

    # ---------------- Deliverables ----------------
    ws2 = wb.create_sheet("Deliverables")
    ws2["A1"] = "All Deliverables (D1–D41)"
    ws2["A1"].font = TITLE_FONT
    ws2["A2"] = "Stakeholders and Notes are left blank for the team to fill in per project."
    ws2["A2"].font = Font(italic=True, color="595959", size=9)

    d_headers = ["ID", "Phase", "Deliverable", "Stakeholders"]
    active_col = None
    for k in ENGAGEMENT_ORDER:
        label = ENGAGEMENT_LABELS[k]
        if k == engagement:
            label = "▶ " + label
            active_col = len(d_headers) + 1
        d_headers.append(label)
    d_headers += ["Expected Filename (F3)", "Present?", "Actual File(s)", "Status", "Notes"]
    d_widths = [6, 22, 38, 16, 15, 15, 15, 8, 40, 9, 34, 13, 30]

    d_header_row = 4
    for i, h in enumerate(d_headers, start=1):
        ws2.cell(row=d_header_row, column=i, value=h)
    _style_header_row(ws2, d_header_row, len(d_headers))
    for i, w in enumerate(d_widths, start=1):
        ws2.column_dimensions[get_column_letter(i)].width = w

    present_col = d_headers.index("Present?") + 1
    status_col = d_headers.index("Status") + 1
    notes_col = d_headers.index("Notes") + 1

    r = d_header_row + 1
    for phase in PHASES:
        folder_exists, assignments, _ = scan_results[phase.index]
        for d in phase.deliverables:
            actual = assignments[d.id]
            present = "Y" if actual else "N"
            mand = d.is_mandatory(engagement)
            if actual:
                status = "Complete"
            elif not folder_exists:
                status = "Folder missing"
            elif mand:
                status = "Not Started"
            else:
                status = ""
            note = "" if folder_exists else f"'{phase.folder}' not found on disk"

            row = [d.id, phase.name, d.name, ""]
            for k in ENGAGEMENT_ORDER:
                row.append("Y" if d.applies.get(k) else "N")
            row += [expected_filename(project_id, d), present, "\n".join(actual), status, note]
            for i, v in enumerate(row, start=1):
                cell = ws2.cell(row=r, column=i, value=v)
                cell.border = BORDER
                cell.alignment = WRAP
                if phase.index % 2 == 0:
                    cell.fill = BAND_FILL
            pcell = ws2.cell(row=r, column=present_col)
            if present == "Y":
                pcell.fill = PatternFill("solid", fgColor=GREEN)
            elif mand:
                pcell.fill = PatternFill("solid", fgColor=RED)
            if not folder_exists:
                ws2.cell(row=r, column=notes_col).fill = PatternFill("solid", fgColor=AMBER)
            r += 1
    ws2.freeze_panes = ws2.cell(row=d_header_row + 1, column=1).coordinate

    return wb


def main(argv=None):
    parser = argparse.ArgumentParser(description="Scan a Kaizen PDP project and (re)generate the Project Report Card")
    parser.add_argument("--root", required=True, help="Project root folder (contains the numbered phase folders)")
    parser.add_argument("--project-id", help="Project ID (F1). Default: .kaizen-project.json, else root folder name.")
    parser.add_argument("--engagement-type", choices=ENGAGEMENT_ORDER,
                         help=f"Engagement type driving mandatory/gate math. Default: .kaizen-project.json, else {DEFAULT_ENGAGEMENT}.")
    parser.add_argument("--out", help="Explicit output .xlsx path. Default: "
                                       "'<root>/7. Project Governance/<PROJECT_ID> - Project Report Card.xlsx' "
                                       "if that folder exists, else '<root>/<PROJECT_ID> - Project Report Card.xlsx'.")
    args = parser.parse_args(argv)

    root = Path(args.root).expanduser().resolve()
    if not root.is_dir():
        print(json.dumps({"error": f"Root folder not found: {root}"}))
        sys.exit(1)

    project_id = resolve_project_id(root, args.project_id)
    engagement = resolve_engagement_type(root, args.engagement_type)

    scan_results = {}
    folders_found = 0
    for phase in PHASES:
        folder_exists, assignments, unclassified = scan_phase(root, phase, project_id)
        scan_results[phase.index] = (folder_exists, assignments, unclassified)
        if folder_exists:
            folders_found += 1

    governance_dir = root / "7. Project Governance"
    if args.out:
        out_path = Path(args.out).expanduser().resolve()
    elif governance_dir.is_dir():
        out_path = governance_dir / f"{project_id} - Project Report Card.xlsx"
    else:
        out_path = root / f"{project_id} - Project Report Card.xlsx"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    wb = build_workbook(project_id, engagement, None, scan_results, generated_at, str(root))
    wb.save(out_path)

    missing_folders = [p.folder for p in PHASES if not scan_results[p.index][0]]
    unclassified_total = sum(len(scan_results[p.index][2]) for p in PHASES)
    mand_total = sum(1 for p in PHASES for d in p.deliverables if d.is_mandatory(engagement))
    mand_present = sum(1 for p in PHASES for d in p.deliverables
                        if d.is_mandatory(engagement) and scan_results[p.index][1][d.id])

    summary = {
        "project_id": project_id,
        "engagement_type": engagement,
        "root": str(root),
        "output_path": str(out_path),
        "folders_found": folders_found,
        "folders_total": len(PHASES),
        "missing_folders": missing_folders,
        "mandatory_total": mand_total,
        "mandatory_present": mand_present,
        "unclassified_files_total": unclassified_total,
        "unclassified_by_phase": {
            p.folder: scan_results[p.index][2] for p in PHASES if scan_results[p.index][2]
        },
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
