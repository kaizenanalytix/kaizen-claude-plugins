#!/usr/bin/env python3
"""
pdp_onboard.py — Deterministic engine for the kaizen-pdp-foundation `project-onboarding` skill.

Creates / repairs a Kaizen PDP project folder structure and the Excel artifacts that track it.
The LLM (per SKILL.md) handles judgment — detecting greenfield vs brownfield and classifying
which existing file maps to which deliverable. This script handles the mechanical work:
folder scaffolding, Excel generation, file moves (versioned, never overwriting per G1), and
manifest logging.

Subcommands
-----------
  scaffold      Create the 0-8 folder structure + per-phase checklists + Report Card + Quality
                seeds. Idempotent: never overwrites existing files (versions per G1).

  scan          Walk the project root and emit a JSON inventory of every file plus a report of
                which compliant folders already exist. Used by the LLM to build a mapping.json.

  apply-reorg   Given a mapping.json (produced by the LLM from a scan), ensure folders exist,
                move each mapped file into its correct phase folder (G1-versioned), then
                regenerate all checklists, the Report Card (incl. Gap Analysis + Reorg Manifest),
                and the Quality artifacts. Supports --dry-run.

All Excel formatting follows Kaizen conventions: navy (#0A2342) header, white bold text,
alternating row bands, frozen header rows.

Single source of truth for the PDP taxonomy is PHASES below, kept in sync with
kaizen-pdp-phases/references/pdp-checklist.md.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

try:
    from openpyxl import Workbook, load_workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter
except ImportError:  # pragma: no cover
    sys.stderr.write(
        "openpyxl is required. Install with: pip install openpyxl --break-system-packages\n"
    )
    raise

# --------------------------------------------------------------------------------------
# Styling constants (Kaizen brand)
# --------------------------------------------------------------------------------------
NAVY = "0A2342"
BAND = "F2F2F2"
GREEN = "C6EFCE"
AMBER = "FFEB9C"
RED = "FFC7CE"
WHITE = "FFFFFF"

HEADER_FILL = PatternFill("solid", fgColor=NAVY)
HEADER_FONT = Font(color=WHITE, bold=True, size=11)
BAND_FILL = PatternFill("solid", fgColor=BAND)
TITLE_FONT = Font(color=NAVY, bold=True, size=14)
SUBTITLE_FONT = Font(color=NAVY, bold=True, size=11)
WRAP = Alignment(vertical="top", wrap_text=True)
TOP = Alignment(vertical="top")
_THIN = Side(style="thin", color="D9D9D9")
BORDER = Border(left=_THIN, right=_THIN, top=_THIN, bottom=_THIN)


# --------------------------------------------------------------------------------------
# PDP taxonomy — single source of truth (mirror of pdp-checklist.md)
# --------------------------------------------------------------------------------------
# Engagement types from the June-22 source sheet. Each deliverable carries an applicability
# flag per type; the active engagement type (chosen at scaffold/reorg time) drives the
# "Mandatory" column and the gate math. "deliverable-based" is the baseline — in the source
# sheet its column is identical to the base Mandatory column.
ENGAGEMENT_ORDER = ["deliverable-based", "capability-pod", "managed-analytics", "gcc"]
ENGAGEMENT_LABELS = {
    "deliverable-based": "Deliverable-based",
    "capability-pod": "Capability Pod",
    "managed-analytics": "Managed Analytics",
    "gcc": "GCC",
}
ENGAGEMENT_FULL_LABELS = {
    "deliverable-based": "Deliverable-based Projects",
    "capability-pod": "Capability Pod Engagements",
    "managed-analytics": "Managed Analytics & Support Services",
    "gcc": "GCC Engagements",
}
DEFAULT_ENGAGEMENT = "deliverable-based"
LAYOUTS = ("full", "compact")
DEFAULT_LAYOUT = "full"  # standardized card shows all 4 engagement-type columns


@dataclass
class Deliverable:
    id: str
    name: str
    mandatory: bool
    ext: str  # suggested file extension hint for the "Expected Filename" column
    # Applicability per engagement type (engagement key -> bool). Populated from the
    # 4-char code passed to _D ("YNYY" = deliverable-based/capability-pod/managed-analytics/gcc).
    applies: dict = field(default_factory=dict)

    def is_mandatory(self, engagement: str = DEFAULT_ENGAGEMENT) -> bool:
        """Whether this deliverable is mandatory for the given engagement type."""
        if self.applies:
            return self.applies.get(engagement, self.mandatory)
        return self.mandatory


@dataclass
class Task:
    id: str
    name: str
    mandatory: bool


@dataclass
class Phase:
    index: int
    folder: str
    name: str
    deliverables: list = field(default_factory=list)
    tasks: list = field(default_factory=list)


def _ap(code: Optional[str]) -> dict:
    """Expand a 4-char applicability code (e.g. 'YNYY') into an engagement-type dict.
    Char order = ENGAGEMENT_ORDER (deliverable-based, capability-pod, managed-analytics, gcc).
    None means 'not defined in source sheet' -> not applicable for any type."""
    if not code:
        return {k: False for k in ENGAGEMENT_ORDER}
    return {ENGAGEMENT_ORDER[i]: (c.upper() == "Y") for i, c in enumerate(code)}


def _D(i, n, ap, e):
    """ap = 4-char applicability code; base `mandatory` = the deliverable-based flag (1st char)."""
    applies = _ap(ap)
    return Deliverable(i, n, applies["deliverable-based"], e, applies)


def _T(i, n, m):
    return Task(i, n, m)


PHASES: list = [
    Phase(0, "0. Sales Alignment", "Sales Alignment",
          [_D("D1", "NDA", "YYYY", "pdf"),
           _D("D2", "Opportunity summary", "YYYY", "docx"),
           _D("D3", "Project scope & estimation summary", "NNNN", "docx"),
           _D("D4", "High-level solution overview diagram", "YYYY", "pptx"),
           _D("D5", "P3 Project Economics", "YYYY", "xlsx"),
           _D("D6", "Deal review committee submission", "NNNN", "pptx"),
           _D("D7", "Client proposal", "YYYY", "pptx"),
           _D("D8", "Data request document", "NNNN", "docx"),
           _D("D9", "MSA", "YYYY", "pdf"),
           _D("D10", "SOW", "YYYY", "pdf")],
          [_T("T1", "Project scoping and estimations", True),
           _T("T2", "Review case studies for proposal", False),
           _T("T3", "Review Useful PPT Slides & Graphics", False),
           _T("T4", "Draft & send data request document", True),
           _T("T5", "Agree dates for data procurement", True),
           _T("T6", "Draft SOW", True),
           _T("T7", "Build P3 economics", True),
           _T("T8", "Deal review committee meeting", True),
           _T("T9", "Update Ruddr", True)]),
    Phase(1, "1. Sales Handoff & Transition", "Sales Handoff & Transition",
          [_D("D11", "Internal Kickoff PPT", "YYYY", "pptx"),
           _D("D12", "Project Charter", "NNNN", "docx"),
           _D("D13", "Project technical checklist", "YNYY", "xlsx")],
          [_T("T10", "Sales knowledge transfer to delivery team", True),
           _T("T11", "Jira Set Up", True),
           _T("T12", "Receive Data samples", False),
           _T("T13", "Identify team members", True),
           _T("T14", "Review Agile Best Practices Guidelines", False),
           _T("T15", "Draft Kickoff PPT", True),
           _T("T16", "Complete Internal Kickoff w/ Project team", True)]),
    Phase(2, "2. Plan", "Plan",
          [_D("D14", "Enter User stories in JIRA", "NNNN", "—"),
           _D("D15", "Kickoff document and minutes", "YYYY", "pptx"),
           _D("D16", "Status Report", "YYYY", "xlsx"),
           _D("D17", "Project Plan/WBS", "YNYY", "xlsx")],
          [_T("T18", "Environment set up and access", True),
           _T("T19", "Review Agile Story Guidelines", False),
           _T("T20", "Review Alteryx Guidelines (as applicable)", False),
           _T("T21", "Kickoff Meeting", True),
           _T("T22", "Project Governance Sign Off", False),
           _T("T23", "Agree Project Plans", True)]),
    Phase(3, "3. Analyze", "Analyze",
          [_D("D18", "Business Requirements, with sign off", "YNYY", "docx"),
           _D("D19", "Validated Data Set", "YNNN", "xlsx"),
           _D("D20", "Change Request Template", "YYYY", "docx")],
          [_T("T24", "Requirements Signoff", False),
           _T("T25", "Data Validation Signoff", False),
           _T("T26", "Draft Technical Design", True)]),
    Phase(4, "4. Design", "Design",
          [_D("D21", "Technical Design", "YNNN", "docx"),
           _D("D22", "End to End Flows and Data Flow Diagrams", "YNNN", "pptx"),
           _D("D23", "Test Plans", "YNNN", "xlsx"),
           _D("D24", "Training Plans", "YNNN", "docx")],
          [_T("T27", "Produce detailed Solution Overview diagram", False),
           _T("T28", "Draft Test Plans", True),
           _T("T29", "Draft Training Plans", True)]),
    Phase(5, "5. Develop", "Develop",
          [_D("D25", "Sprint Log", "YNNN", "xlsx"),
           _D("D26", "Issue Log", "YNNY", "xlsx"),
           _D("D27", "Definition of done", "YNNN", "docx"),
           _D("D28", "Testing sign off", "YNNN", "docx")],
          [_T("T30", "Solution Development & Calibration", True),
           _T("T31", "Unit, integration and user testing", True),
           _T("T32", "Conduct sprint / milestone review", True),
           _T("T33", "Monthly Kaizen Project Review", True),
           _T("T34", "Training preparation", False)]),
    Phase(6, "6. Deploy", "Deploy",
          [_D("D29", "Deployment/handoff checklist", "YNYY", "docx"),
           _D("D30", "Project Sign Off", "YYYY", "docx"),
           _D("D31", "Project Close Out", "YYYY", "docx"),
           _D("D32", "Kaizen Case Study", "YYYY", "pptx")],
          [_T("T36", "User Training", False),
           _T("T37", "Deploy Solution", True),
           _T("T38", "Review support plan", True),
           _T("T39", "Project Retrospective", False),
           _T("T40", "Archive all project deliverables", True)]),
    Phase(7, "7. Project Governance", "Project Governance",
          [_D("D33", "RAID Log", "YYYY", "xlsx"),
           _D("D34", "RACI Chart", "YNYY", "xlsx"),
           _D("D35", "Value Tracker", "YYYY", "xlsx"),
           _D("D36", "Business Continuity Plan (BCP)", "YYYY", "pptx"),
           _D("D37", "Updated project governance scorecard", "YYYY", "xlsx")],
          []),
    Phase(8, "8. Quality", "Quality",
          [_D("D38", "Customer Satisfaction Survey (CSAT)", "YYYY", "xlsx"),
           _D("D39", "Quality Plan", "NNNN", "docx"),
           _D("D40", "Project Metrics", "NNNN", "xlsx"),
           _D("D41", "Risk assessment Sheet", "NNNN", "xlsx")],
          []),
]

GOVERNANCE_FOLDER = "7. Project Governance"
QUALITY_FOLDER = "8. Quality"

PHASE_FOLDERS = [p.folder for p in PHASES]
# Phases 0–8 are all in PHASES (7 Governance and 8 Quality now carry tracked deliverables);
# dedupe defensively in case the folder constants are appended elsewhere.
ALL_FOLDERS = list(dict.fromkeys(PHASE_FOLDERS + [GOVERNANCE_FOLDER, QUALITY_FOLDER]))

# Map a phase index (0-8) to its folder name.
FOLDER_BY_INDEX = {p.index: p.folder for p in PHASES}
FOLDER_BY_INDEX[7] = GOVERNANCE_FOLDER
FOLDER_BY_INDEX[8] = QUALITY_FOLDER

# Lookup a Deliverable by id (ids are globally unique thanks to the b-suffixes above).
DELIVERABLE_BY_ID = {d.id: (p, d) for p in PHASES for d in p.deliverables}


# --------------------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------------------
def _now() -> str:
    return _dt.datetime.now().strftime("%Y-%m-%d %H:%M")


def expected_filename(project_id: str, d: Deliverable) -> str:
    """F3 naming: '[ProjectID] - [Deliverable Name].ext'."""
    if d.ext == "—":
        return "(tracked in Jira — no file)"
    return f"{project_id} - {d.name}.{d.ext}"


# --------------------------------------------------------------------------------------
# Reconciliation — make the Report Card reflect what is ON DISK, not just this run's moves
# --------------------------------------------------------------------------------------
# Why this exists: the "Present?" / "Actual File(s)" columns used to be populated only from
# the move manifest. Any deliverable file that was ALREADY sitting in the correct phase
# folder (or in a subfolder of it, e.g. "2. Plan/status reports/…") was therefore invisible
# to the card — it showed Present?=N with a blank Actual File(s), even though the file was
# physically right where it belonged. The reconciliation pass below closes that gap: after
# the moves are applied, it walks each phase folder (recursively) and registers files that
# map to a deliverable so the card mirrors reality. It is deliberately NON-DESTRUCTIVE (it
# records, it never moves or renames) so it is safe to run every time, including on re-runs
# that are really just "refresh my Report Card". Matching is taxonomy-agnostic: it works off
# the deliverable NAMES in PHASES, so it needs no changes when the D-numbering changes.

# Generic words that carry no signal for matching a filename to a deliverable name.
_MATCH_STOPWORDS = {
    "and", "of", "the", "with", "a", "an", "to", "in", "for", "on", "by",
    "sign", "off", "document", "documents", "doc", "template", "final", "draft",
    "project", "updated", "copy", "version",
}

# Filenames the tool itself generates — never treat a tracker as a deliverable.
_TRACKER_SUFFIXES = (
    "- Phase Checklist.xlsx",
    "- Project Report Card.xlsx",
    "- Folder Placement & Naming Audit.xlsx",
    "- Onboarding Audit Trail.xlsx",
)
_TRACKER_EXACT = {"Quality - README.md"}


def _sig_tokens(text: str) -> set:
    """Significant lower-case word tokens of a string, minus generic stopwords."""
    return {t for t in re.split(r"[^a-z0-9]+", text.lower()) if t and t not in _MATCH_STOPWORDS}


def _match_deliverable(filename: str, project_id: str, phase_delivs: list):
    """Best deliverable in this phase that a file plausibly satisfies, or None.

    Two conservative signals, in order of confidence:
      1. Exact F3 name match ('<PROJECT_ID> - <Deliverable Name>.<ext>') — unambiguous,
         and makes re-runs idempotent for files the skill itself renamed.
      2. Token-subset match: every significant word of the deliverable name appears in the
         filename (so 'Weekly Status Report wk10.xlsx' matches the 'Status Report'
         deliverable). Among competing matches the most specific (most tokens) wins.
         Requiring the *full* set keeps this from firing on loose keyword overlap.
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


def reconcile_existing(root: Path, project_id: str, assignments: dict) -> list:
    """Register files already living in phase folders (incl. nested subfolders) against
    their deliverable, so the Report Card reflects on-disk reality. Mutates `assignments`
    in place and returns a list of reconciliation records for the audit trail. Read-only on
    the filesystem — nothing is moved or renamed."""
    reconciled = []
    seen = {name for names in assignments.values() for name in names}
    for p in PHASES:
        folder = root / p.folder
        if not folder.is_dir():
            continue
        for dirpath, dirnames, filenames in os.walk(folder):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for fn in filenames:
                if fn in SKIP_FILES or fn in _TRACKER_EXACT:
                    continue
                if any(fn.endswith(sfx) for sfx in _TRACKER_SUFFIXES):
                    continue
                # relative path within the phase folder — shows the user where it actually is
                rel = str((Path(dirpath) / fn).relative_to(folder)).replace("\\", "/")
                if fn in seen or rel in seen:
                    continue
                d = _match_deliverable(fn, project_id, p.deliverables)
                if not d:
                    continue
                assignments.setdefault(d.id, []).append(rel)
                seen.add(fn)
                seen.add(rel)
                reconciled.append({
                    "old": rel, "new": rel, "phase": f"Phase {p.index}",
                    "folder": p.folder,
                    "deliverable": f"{d.id} {d.name}".strip(),
                    "action": "registered (already in place)",
                    "reason": "File already located in the correct phase folder",
                    "ts": _now(),
                })
    return reconciled


def versioned_destination(dest_dir: Path, basename: str) -> Path:
    """Apply G1: never overwrite. If basename exists, append ' v2', ' v3', ... before the ext."""
    candidate = dest_dir / basename
    if not candidate.exists():
        return candidate
    stem = Path(basename).stem
    suffix = Path(basename).suffix
    v = 2
    while True:
        candidate = dest_dir / f"{stem} v{v}{suffix}"
        if not candidate.exists():
            return candidate
        v += 1


def prune_empty_dirs(root: Path) -> list:
    """Remove non-compliant directories that were emptied by the reorg. Never touches the
    9 PDP folders, and never removes a directory that still contains files (e.g. an
    unclassified file left in place)."""
    pruned = []
    for dirpath, dirnames, filenames in os.walk(root, topdown=False):
        d = Path(dirpath)
        if d == root:
            continue
        rel = d.relative_to(root)
        if rel.parts[0] in ALL_FOLDERS:
            continue  # never prune inside the compliant structure
        try:
            if not any(d.iterdir()):
                d.rmdir()
                pruned.append(str(rel).replace("\\", "/"))
        except OSError:
            pass
    return pruned


def ensure_folders(root: Path, log: Optional[list] = None) -> list:
    created = []
    for folder in ALL_FOLDERS:
        path = root / folder
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            created.append(folder)
            if log is not None:
                log.append({"action": "create-folder", "target": folder, "ts": _now()})
    return created


# --------------------------------------------------------------------------------------
# Excel building blocks
# --------------------------------------------------------------------------------------
def _style_header(ws, row: int, ncols: int):
    for c in range(1, ncols + 1):
        cell = ws.cell(row=row, column=c)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(vertical="center", wrap_text=True)
        cell.border = BORDER


def _write_table(ws, start_row: int, headers: list, rows: list,
                 widths: Optional[list] = None, status_col: Optional[int] = None,
                 present_col: Optional[int] = None):
    """Write a header + data rows starting at start_row. Returns the next free row."""
    ncols = len(headers)
    for j, h in enumerate(headers, start=1):
        ws.cell(row=start_row, column=j, value=h)
    _style_header(ws, start_row, ncols)
    r = start_row + 1
    for i, row in enumerate(rows):
        for j, val in enumerate(row, start=1):
            cell = ws.cell(row=r, column=j, value=val)
            cell.alignment = WRAP
            cell.border = BORDER
            if i % 2 == 1:
                cell.fill = BAND_FILL
        if status_col is not None:
            _color_status(ws.cell(row=r, column=status_col))
        if present_col is not None:
            _color_present(ws.cell(row=r, column=present_col))
        r += 1
    if widths:
        for j, w in enumerate(widths, start=1):
            ws.column_dimensions[get_column_letter(j)].width = w
    ws.freeze_panes = ws.cell(row=start_row + 1, column=1)
    return r


def _color_status(cell):
    v = str(cell.value or "").strip().lower()
    if v in ("complete", "done", "closed", "approved"):
        cell.fill = PatternFill("solid", fgColor=GREEN)
    elif v in ("in progress", "in-progress", "wip", "draft"):
        cell.fill = PatternFill("solid", fgColor=AMBER)
    elif v in ("not started", "missing", "open", "blocked"):
        cell.fill = PatternFill("solid", fgColor=RED)


def _color_present(cell):
    v = str(cell.value or "").strip().lower()
    if v in ("y", "yes", "present"):
        cell.fill = PatternFill("solid", fgColor=GREEN)
    elif v in ("n", "no", "missing"):
        cell.fill = PatternFill("solid", fgColor=RED)


# --------------------------------------------------------------------------------------
# Deliverable-table layout (shared by checklist + report card)
# --------------------------------------------------------------------------------------
def _deliverable_columns(layout: str, engagement: str, with_phase: bool):
    """Build the deliverable-table header/width spec for the chosen layout.

    Returns (headers, widths, status_col, present_col, active_col). Indices are 1-based;
    active_col is the engagement column that drives the gate (None in compact layout).

    - compact: a single 'Mandatory' column reflecting the active engagement type.
    - full:    one column per engagement type; the active one is marked '▶' and drives gates.
    """
    headers = ["ID"]
    widths = [8]
    if with_phase:
        headers.append("Phase")
        widths.append(9)
    headers += ["Deliverable", "Stakeholders"]
    widths += [34, 20]
    active_col = None
    if layout == "full":
        for k in ENGAGEMENT_ORDER:
            label = ENGAGEMENT_LABELS[k]
            if k == engagement:
                label = "▶ " + label
                active_col = len(headers) + 1
            headers.append(label)
            widths.append(15)
    else:
        headers.append("Mandatory")
        widths.append(11)
    headers += ["Expected Filename (F3)", "Present?", "Actual File(s)", "Status", "Notes"]
    widths += [40, 9, 30, 13, 30]
    present_col = headers.index("Present?") + 1
    status_col = headers.index("Status") + 1
    return headers, widths, status_col, present_col, active_col


def _deliverable_row(d: Deliverable, project_id: str, assignments: dict,
                     layout: str, engagement: str, phase_label: Optional[str] = None):
    actual = assignments.get(d.id, [])
    present = "Y" if actual else "N"
    mand = d.is_mandatory(engagement)
    status = "Complete" if actual else ("Not Started" if mand else "")
    row = [d.id]
    if phase_label is not None:
        row.append(phase_label)
    row += [d.name, ""]  # Stakeholders left blank — filled per project
    if layout == "full":
        for k in ENGAGEMENT_ORDER:
            row.append("Y" if d.applies.get(k) else "N")
    else:
        row.append("Y" if mand else "N")
    row += [expected_filename(project_id, d), present, "\n".join(actual), status, ""]
    return row


def _color_yn_column(ws, first_data_row: int, last_data_row: int, col: int):
    """Apply Y/N green/red shading down a column (used for the active engagement column)."""
    for r in range(first_data_row, last_data_row):
        _color_present(ws.cell(row=r, column=col))


# --------------------------------------------------------------------------------------
# Checklist workbook (one per phase folder)
# --------------------------------------------------------------------------------------
def build_phase_checklist(phase: Phase, project_id: str, assignments: dict,
                          engagement: str = DEFAULT_ENGAGEMENT,
                          layout: str = DEFAULT_LAYOUT) -> Workbook:
    """assignments: {deliverable_id: [actual_filename, ...]} for files known to satisfy it."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Checklist"

    ws.cell(row=1, column=1, value=f"{project_id}").font = TITLE_FONT
    ws.cell(row=2, column=1,
            value=f"Phase {phase.index} — {phase.name}  ·  Folder: {phase.folder}").font = SUBTITLE_FONT
    ws.cell(row=3, column=1,
            value=f"Engagement type: {ENGAGEMENT_FULL_LABELS[engagement]}.  "
                  "Mark Present? = Y once the file is saved here. "
                  "Versions per guardrail G1 (never overwrite).").font = Font(italic=True, size=9)

    # Deliverables table
    ws.cell(row=5, column=1, value="Deliverables").font = SUBTITLE_FONT
    d_headers, d_widths, status_col, present_col, active_col = _deliverable_columns(
        layout, engagement, with_phase=False)
    d_rows = [_deliverable_row(d, project_id, assignments, layout, engagement)
              for d in phase.deliverables]
    next_row = _write_table(ws, 6, d_headers, d_rows, widths=d_widths,
                            status_col=status_col, present_col=present_col)
    if active_col:
        _color_yn_column(ws, 7, next_row, active_col)

    # Tasks table
    t_start = next_row + 1
    ws.cell(row=t_start, column=1, value="Tasks").font = SUBTITLE_FONT
    t_headers = ["ID", "Task", "Mandatory", "Status", "Owner", "Notes"]
    t_rows = [[t.id, t.name, "Y" if t.mandatory else "N",
               "Not Started" if t.mandatory else "", "", ""] for t in phase.tasks]
    _write_table(ws, t_start + 1, t_headers, t_rows,
                 widths=[8, 44, 11, 13, 18, 26], status_col=4)
    ws.freeze_panes = "A1"
    return wb


# --------------------------------------------------------------------------------------
# Project Report Card workbook (Governance folder)
# --------------------------------------------------------------------------------------
def _gate_status(mandatory_total: int, mandatory_present: int) -> str:
    if mandatory_total == 0:
        return "n/a"
    if mandatory_present >= mandatory_total:
        return "PASS"
    return f"{mandatory_present}/{mandatory_total} done"


def build_report_card(project_id: str, assignments: dict,
                      manifest: Optional[list] = None,
                      gaps: Optional[list] = None,
                      mode: str = "greenfield",
                      engagement: str = DEFAULT_ENGAGEMENT,
                      layout: str = DEFAULT_LAYOUT) -> Workbook:
    wb = Workbook()

    # ---- Dashboard ----
    ws = wb.active
    ws.title = "Dashboard"
    ws.cell(row=1, column=1, value=f"{project_id} — Project Report Card").font = TITLE_FONT
    ws.cell(row=2, column=1,
            value=f"Engagement type: {ENGAGEMENT_FULL_LABELS[engagement]}   ·   "
                  f"Mode: {mode}   ·   Generated: {_now()}").font = Font(italic=True, size=9)
    ws.cell(row=3, column=1,
            value="'Mandatory' and gate status reflect the engagement type above. "
                  "Change it by re-running with --engagement-type.").font = Font(italic=True, size=9)

    headers = ["Phase", "Folder", "Deliverables", "Mandatory",
               "Present", "Mandatory Present", "% Mandatory", "Gate Status"]
    rows = []
    tot_d = tot_m = tot_present = tot_mpresent = 0
    for p in PHASES:
        n_d = len(p.deliverables)
        n_m = sum(1 for d in p.deliverables if d.is_mandatory(engagement))
        present = sum(1 for d in p.deliverables if assignments.get(d.id))
        m_present = sum(1 for d in p.deliverables
                        if d.is_mandatory(engagement) and assignments.get(d.id))
        pct = f"{round(100 * m_present / n_m)}%" if n_m else "n/a"
        rows.append([f"Phase {p.index}", p.name, n_d, n_m, present, m_present, pct,
                     _gate_status(n_m, m_present)])
        tot_d += n_d
        tot_m += n_m
        tot_present += present
        tot_mpresent += m_present
    rows.append(["", "TOTAL", tot_d, tot_m, tot_present, tot_mpresent,
                 f"{round(100 * tot_mpresent / tot_m)}%" if tot_m else "n/a",
                 _gate_status(tot_m, tot_mpresent)])
    _write_table(ws, 5, headers, rows, widths=[10, 28, 13, 11, 9, 18, 12, 14], status_col=8)
    # bold the total row
    total_r = 5 + len(rows)
    for c in range(1, len(headers) + 1):
        ws.cell(row=total_r, column=c).font = Font(bold=True)

    # ---- Deliverables ----
    ws2 = wb.create_sheet("Deliverables")
    ws2.cell(row=1, column=1, value="All Deliverables (D1–D41)").font = TITLE_FONT
    d_headers, d_widths, status_col, present_col, active_col = _deliverable_columns(
        layout, engagement, with_phase=True)
    d_rows = []
    for p in PHASES:
        for d in p.deliverables:
            d_rows.append(_deliverable_row(d, project_id, assignments, layout, engagement,
                                           phase_label=f"Phase {p.index}"))
    next_row = _write_table(ws2, 3, d_headers, d_rows, widths=d_widths,
                            status_col=status_col, present_col=present_col)
    if active_col:
        _color_yn_column(ws2, 4, next_row, active_col)

    # ---- Tasks ----
    ws3 = wb.create_sheet("Tasks")
    ws3.cell(row=1, column=1, value="All Tasks (T1–T40)").font = TITLE_FONT
    t_headers = ["ID", "Phase", "Task", "Mandatory", "Status", "Owner", "Notes"]
    t_rows = []
    for p in PHASES:
        for t in p.tasks:
            t_rows.append([t.id, f"Phase {p.index}", t.name, "Y" if t.mandatory else "N",
                           "Not Started" if t.mandatory else "", "", ""])
    _write_table(ws3, 3, t_headers, t_rows,
                 widths=[8, 9, 46, 11, 13, 18, 24], status_col=5)

    # ---- Gap Analysis (brownfield) ----
    if gaps is not None:
        wsg = wb.create_sheet("Gap Analysis")
        wsg.cell(row=1, column=1, value="Gap Analysis").font = TITLE_FONT
        wsg.cell(row=2, column=1,
                 value="Missing mandatory deliverables, unclassified files, and placement / "
                       "naming issues found during onboarding.").font = Font(italic=True, size=9)
        g_headers = ["Type", "ID / File", "Detail", "Severity", "Recommendation"]
        _write_table(wsg, 4, g_headers, gaps, widths=[22, 32, 46, 12, 46], status_col=4)

    # ---- Reorg Manifest (brownfield) ----
    if manifest is not None:
        wsm = wb.create_sheet("Reorg Manifest")
        wsm.cell(row=1, column=1, value="Reorg Manifest").font = TITLE_FONT
        wsm.cell(row=2, column=1,
                 value="Audit trail of every file moved during onboarding.").font = Font(italic=True, size=9)
        m_headers = ["Old Path", "New Path", "Phase", "Deliverable", "Action", "Reason", "Timestamp"]
        m_rows = [[m.get("old", ""), m.get("new", ""), m.get("phase", ""),
                   m.get("deliverable", ""), m.get("action", ""), m.get("reason", ""),
                   m.get("ts", "")] for m in manifest]
        _write_table(wsm, 4, m_headers, m_rows, widths=[40, 40, 9, 24, 16, 36, 16])

    return wb


# --------------------------------------------------------------------------------------
# Quality workbooks
# --------------------------------------------------------------------------------------
def build_placement_audit(project_id: str, audit_rows: list) -> Workbook:
    wb = Workbook()
    ws = wb.active
    ws.title = "Placement & Naming"
    ws.cell(row=1, column=1, value=f"{project_id} — Folder Placement & Naming Audit").font = TITLE_FONT
    ws.cell(row=2, column=1,
            value="Verifies each file sits in the correct phase folder (F2) and matches the "
                  "naming convention (F3). Re-run the audit after any file changes.").font = Font(italic=True, size=9)
    headers = ["File", "Current Folder", "Expected Folder", "In Correct Folder?",
               "Naming Compliant (F3)?", "Issue", "Recommendation"]
    _write_table(ws, 4, headers, audit_rows, widths=[34, 22, 22, 16, 20, 34, 40])
    return wb


def build_audit_trail(project_id: str, scaffold_log: list, manifest: list) -> Workbook:
    wb = Workbook()
    ws = wb.active
    ws.title = "Onboarding Log"
    ws.cell(row=1, column=1, value=f"{project_id} — Onboarding / Reorg Audit Trail").font = TITLE_FONT
    ws.cell(row=2, column=1, value=f"Generated: {_now()}").font = Font(italic=True, size=9)
    headers = ["Action", "Target", "Detail", "Timestamp"]
    rows = [[e.get("action", ""), e.get("target", ""), e.get("detail", ""), e.get("ts", "")]
            for e in scaffold_log]
    next_row = _write_table(ws, 4, headers, rows, widths=[22, 40, 40, 18])

    if manifest:
        ws.cell(row=next_row + 1, column=1, value="File Moves").font = SUBTITLE_FONT
        m_headers = ["Old Path", "New Path", "Deliverable", "Action", "Reason", "Timestamp"]
        m_rows = [[m.get("old", ""), m.get("new", ""), m.get("deliverable", ""),
                   m.get("action", ""), m.get("reason", ""), m.get("ts", "")] for m in manifest]
        _write_table(ws, next_row + 2, m_headers, m_rows, widths=[40, 40, 24, 16, 36, 18])
    return wb


QUALITY_README = """# 8. Quality — Folder Charter

This folder houses quality checks that verify deliverables across phases 0–8 are correct,
complete, and correctly placed. Seeded artifacts:

- **{pid} - Folder Placement & Naming Audit.xlsx** — verifies each file is in the right phase
  folder (F2) and matches the naming convention (F3). Re-run after any file changes.
- **{pid} - Onboarding Audit Trail.xlsx** — record of what onboarding created and moved.

## Recommended additions (create as the project matures)

1. **Phase-Gate Exit Checklist** — the gate conditions from `kaizen-pdp-phases` as a per-transition
   sign-off sheet (Sales Alignment → Handoff, Handoff → Plan, ... → Closed).
2. **Peer Review / QA Sign-off Log** — reviewer, date, and status per deliverable.
3. **Definition of Done** — acceptance criteria per deliverable type (doc / model / dashboard / code).
4. **Version-Control / Change Log** — ties to guardrail G1; record every version bump and why.
5. **Data Quality Validation Log** — checks against the Validated Data Set (D19).
6. **Test & UAT Evidence Index** — pointers to test results supporting T31.

_Quality is a living folder — the audit and gate checklists should be re-run at every phase gate._
"""


# --------------------------------------------------------------------------------------
# Generation orchestration (shared by scaffold + apply-reorg)
# --------------------------------------------------------------------------------------
def write_versioned(path_dir: Path, basename: str, wb: Workbook, log: list,
                    overwrite_same: bool = True) -> Path:
    """
    Write a workbook. For regenerated tracking artifacts (checklists, report card) we want to
    refresh in place rather than spawn v2/v3 every run, so overwrite_same=True replaces an
    existing same-named file. (These are tool-generated, not user deliverables — G1 protects
    user content, not the tracker itself.)
    """
    dest = path_dir / basename
    if dest.exists() and not overwrite_same:
        dest = versioned_destination(path_dir, basename)
    wb.save(dest)
    log.append({"action": "write-file", "target": str(dest.name),
                "detail": str(path_dir.name), "ts": _now()})
    return dest


def generate_artifacts(root: Path, project_id: str, assignments: dict,
                       manifest: Optional[list], gaps: Optional[list],
                       audit_rows: list, scaffold_log: list, mode: str,
                       engagement: str = DEFAULT_ENGAGEMENT, layout: str = DEFAULT_LAYOUT):
    # Per-phase checklists
    for p in PHASES:
        # only the deliverable ids belonging to this phase
        phase_assign = {d.id: assignments.get(d.id, []) for d in p.deliverables}
        wb = build_phase_checklist(p, project_id, phase_assign,
                                   engagement=engagement, layout=layout)
        write_versioned(root / p.folder, f"{project_id} - Phase Checklist.xlsx", wb, scaffold_log)

    # Report Card -> Governance
    rc = build_report_card(project_id, assignments, manifest=manifest, gaps=gaps, mode=mode,
                           engagement=engagement, layout=layout)
    write_versioned(root / GOVERNANCE_FOLDER, f"{project_id} - Project Report Card.xlsx",
                    rc, scaffold_log)

    # Quality seeds
    audit = build_placement_audit(project_id, audit_rows)
    write_versioned(root / QUALITY_FOLDER, f"{project_id} - Folder Placement & Naming Audit.xlsx",
                    audit, scaffold_log)
    trail = build_audit_trail(project_id, scaffold_log, manifest or [])
    write_versioned(root / QUALITY_FOLDER, f"{project_id} - Onboarding Audit Trail.xlsx",
                    trail, scaffold_log)
    readme = root / QUALITY_FOLDER / "Quality - README.md"
    if not readme.exists():
        readme.write_text(QUALITY_README.format(pid=project_id), encoding="utf-8")
        scaffold_log.append({"action": "write-file", "target": "Quality - README.md",
                             "detail": QUALITY_FOLDER, "ts": _now()})


# --------------------------------------------------------------------------------------
# Subcommand: scaffold
# --------------------------------------------------------------------------------------
def cmd_scaffold(args):
    root = Path(args.root).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    project_id = args.project_id or root.name

    engagement = getattr(args, "engagement_type", DEFAULT_ENGAGEMENT) or DEFAULT_ENGAGEMENT
    layout = getattr(args, "layout", DEFAULT_LAYOUT) or DEFAULT_LAYOUT

    scaffold_log = []
    created = ensure_folders(root, scaffold_log)
    # Reconcile any files already sitting in the phase folders so a scaffold re-run behaves
    # as a "refresh my Report Card" — a truly empty greenfield project simply reconciles zero.
    assignments: dict = {}
    reconciled = reconcile_existing(root, project_id, assignments)
    generate_artifacts(root, project_id, assignments=assignments,
                       manifest=(reconciled or None), gaps=None,
                       audit_rows=[], scaffold_log=scaffold_log, mode="greenfield",
                       engagement=engagement, layout=layout)

    summary = {
        "mode": "greenfield",
        "root": str(root),
        "project_id": project_id,
        "engagement_type": engagement,
        "layout": layout,
        "folders_created": created,
        "folders_total": len(ALL_FOLDERS),
        "files_registered_in_place": len(reconciled),
        "files_written": [e["target"] for e in scaffold_log if e["action"] == "write-file"],
    }
    print(json.dumps(summary, indent=2))


# --------------------------------------------------------------------------------------
# Subcommand: scan
# --------------------------------------------------------------------------------------
SKIP_DIRS = {".git", "__pycache__", ".kaizen", "_pre-PDP-backup"}
SKIP_FILES = {".DS_Store", "Thumbs.db", ".kaizen-project.json"}


def cmd_scan(args):
    root = Path(args.root).expanduser().resolve()
    if not root.exists():
        sys.stderr.write(f"Root does not exist: {root}\n")
        sys.exit(1)

    compliant = {f: (root / f).is_dir() for f in ALL_FOLDERS}
    is_greenfield = not any(compliant.values())

    files = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            if fn in SKIP_FILES:
                continue
            full = Path(dirpath) / fn
            rel = full.relative_to(root)
            top = rel.parts[0] if len(rel.parts) > 1 else ""
            try:
                st = full.stat()
                size = st.st_size
                mtime = _dt.datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M")
            except OSError:
                size, mtime = None, None
            files.append({
                "relpath": str(rel).replace("\\", "/"),
                "name": fn,
                "ext": full.suffix.lower().lstrip("."),
                "top_folder": top,
                "in_compliant_folder": top in ALL_FOLDERS,
                "size": size,
                "modified": mtime,
            })

    result = {
        "root": str(root),
        "suggested_project_id": root.name,
        "is_greenfield": is_greenfield,
        "compliant_folders_present": compliant,
        "file_count": len(files),
        "files": files,
        "taxonomy_hint": {
            d.id: {"name": d.name, "phase": p.index, "folder": p.folder,
                   "mandatory": d.mandatory, "applies": d.applies}
            for p in PHASES for d in p.deliverables
        },
    }
    out = json.dumps(result, indent=2)
    if args.out:
        Path(args.out).write_text(out, encoding="utf-8")
        print(f"Scan written to {args.out}  ({len(files)} files, "
              f"greenfield={is_greenfield})")
    else:
        print(out)


# --------------------------------------------------------------------------------------
# Subcommand: apply-reorg
# --------------------------------------------------------------------------------------
def cmd_apply_reorg(args):
    root = Path(args.root).expanduser().resolve()
    project_id = args.project_id or root.name
    engagement = getattr(args, "engagement_type", DEFAULT_ENGAGEMENT) or DEFAULT_ENGAGEMENT
    layout = getattr(args, "layout", DEFAULT_LAYOUT) or DEFAULT_LAYOUT
    mapping = json.loads(Path(args.mapping).read_text(encoding="utf-8"))
    moves = mapping.get("moves", [])
    dry = args.dry_run

    scaffold_log = []
    if not dry:
        if args.archive:
            backup = root / "_pre-PDP-backup"
            # (kept simple: archive flag reserved; default mode is move-only per user choice)
        ensure_folders(root, scaffold_log)

    manifest = []
    assignments: dict = {}
    gaps = []
    audit_rows = []

    for mv in moves:
        src_rel = mv.get("src")
        phase_idx = mv.get("phase")
        deliv_id = mv.get("deliverable_id")
        reason = mv.get("reason", "")
        new_name = mv.get("new_name")  # optional compliant rename

        src = (root / src_rel).resolve() if src_rel else None
        deliv_name = ""
        if deliv_id and deliv_id in DELIVERABLE_BY_ID:
            deliv_name = DELIVERABLE_BY_ID[deliv_id][1].name

        # Unclassified -> leave in place, log as gap.
        if phase_idx is None or src is None:
            gaps.append(["Unclassified file", src_rel or "?", reason or "Could not map to a deliverable",
                         "Medium", "Review and place manually, or confirm it is not a deliverable."])
            audit_rows.append([Path(src_rel).name if src_rel else "?",
                               (src_rel.split("/")[0] if src_rel and "/" in src_rel else "(root)"),
                               "(unassigned)", "N", "N", "Unclassified during onboarding",
                               "Manual review"])
            continue

        dest_dir = root / FOLDER_BY_INDEX[int(phase_idx)]
        basename = new_name or (src.name if src else "unknown")
        action = "move"
        if new_name and src and new_name != src.name:
            action = "move+rename"

        if not src or not src.exists():
            gaps.append(["Missing source", src_rel or "?", "Mapping referenced a file that does not exist",
                         "High", "Re-run scan; fix mapping."])
            continue

        dest = versioned_destination(dest_dir, basename)
        if dest.name != basename:
            action += "+versioned"

        if not dry:
            shutil.move(str(src), str(dest))

        manifest.append({
            "old": src_rel, "new": str(dest.relative_to(root)).replace("\\", "/"),
            "phase": f"Phase {phase_idx}", "deliverable": f"{deliv_id} {deliv_name}".strip(),
            "action": action, "reason": reason, "ts": _now(),
        })
        if deliv_id:
            assignments.setdefault(deliv_id, []).append(dest.name)

        # placement audit row (post-move it is correct by construction)
        naming_ok = "Y" if basename.startswith(f"{project_id} - ") else "N"
        audit_rows.append([dest.name, FOLDER_BY_INDEX[int(phase_idx)], FOLDER_BY_INDEX[int(phase_idx)],
                           "Y", naming_ok,
                           "" if naming_ok == "Y" else "Filename does not match F3 convention",
                           "" if naming_ok == "Y" else f"Rename to '{project_id} - <Deliverable>.{Path(basename).suffix.lstrip('.')}'"])

    # Reconcile files already correctly placed (incl. in nested subfolders) so the Report
    # Card reflects what is on disk, not just this run's moves. Read-only — safe in dry-run,
    # where it previews already-placed files as present. Runs before gap analysis so the
    # "missing mandatory" list accounts for what is genuinely already there.
    reconciled = reconcile_existing(root, project_id, assignments)
    for rec in reconciled:
        name = rec["old"].split("/")[-1]
        ext = name.rsplit(".", 1)[-1] if "." in name else ""
        naming_ok = "Y" if name.startswith(f"{project_id} - ") else "N"
        audit_rows.append([rec["old"], rec.get("folder", ""), rec.get("folder", ""),
                           "Y", naming_ok,
                           "" if naming_ok == "Y" else "Already correctly placed; filename does not match F3 convention",
                           "" if naming_ok == "Y" else f"Optional: rename to '{project_id} - <Deliverable>.{ext}'"])

    # Gap analysis: missing mandatory deliverables (per the active engagement type)
    for p in PHASES:
        for d in p.deliverables:
            if d.is_mandatory(engagement) and not assignments.get(d.id):
                gaps.append(["Missing mandatory deliverable", d.id,
                             f"Phase {p.index} — {d.name}", "High",
                             f"Produce {d.name} and place in '{p.folder}'."])

    if dry:
        print(json.dumps({
            "mode": "brownfield (DRY RUN — no files moved)",
            "project_id": project_id,
            "planned_moves": manifest,
            "already_placed_registered": reconciled,
            "gaps": gaps,
        }, indent=2))
        return

    # The Reorg Manifest sheet records both actual moves and files registered in place.
    generate_artifacts(root, project_id, assignments, manifest=manifest + reconciled, gaps=gaps,
                       audit_rows=audit_rows, scaffold_log=scaffold_log, mode="brownfield",
                       engagement=engagement, layout=layout)

    pruned = prune_empty_dirs(root)
    for d in pruned:
        scaffold_log.append({"action": "prune-empty-folder", "target": d, "ts": _now()})

    print(json.dumps({
        "mode": "brownfield",
        "root": str(root),
        "project_id": project_id,
        "files_moved": len(manifest),
        "files_registered_in_place": len(reconciled),
        "unclassified_or_gaps": len(gaps),
        "files_written": [e["target"] for e in scaffold_log if e["action"] == "write-file"],
    }, indent=2))


# --------------------------------------------------------------------------------------
# Subcommands: build-review / read-review (editable Excel mapping review)
# --------------------------------------------------------------------------------------
# The proposed mapping is rendered as an editable .xlsx with dropdowns (Proposed Phase /
# Proposed Deliverable / Exclude?). The user edits it in Excel and saves; `read-review` parses
# it back into a mapping.json that apply-reorg consumes. Fully local — no web artifact, no
# host-specific round-trip.
REVIEW_SHEET = "Reorg Plan"
LEAVE_OPT = "— Leave in place —"
NONE_OPT = "— None —"
REVIEW_HEADERS = ["Source File", "Current Folder", "Proposed Phase",
                  "Proposed Deliverable", "Exclude?", "Reason"]
REVIEW_DATA_ROW = 6  # data rows start here (rows 1-4 title/instructions, row 5 header)


def _phase_label(phase_idx) -> str:
    return LEAVE_OPT if phase_idx is None else FOLDER_BY_INDEX[int(phase_idx)]


def _deliverable_label(did, engagement) -> str:
    if not did or did not in DELIVERABLE_BY_ID:
        return NONE_OPT
    p, d = DELIVERABLE_BY_ID[did]
    star = " *" if d.is_mandatory(engagement) else ""
    return f"{did}: {d.name} [P{p.index}]{star}"


def build_reorg_plan(project_id: str, engagement: str, moves: list) -> Workbook:
    from openpyxl.worksheet.datavalidation import DataValidation

    wb = Workbook()
    ws = wb.active
    ws.title = REVIEW_SHEET

    # Hidden sheet holding the dropdown source lists.
    lists = wb.create_sheet("Lists")
    phase_opts = [LEAVE_OPT] + [p.folder for p in PHASES]
    deliv_opts = [NONE_OPT] + [_deliverable_label(d.id, engagement)
                              for p in PHASES for d in p.deliverables]
    yn_opts = ["N", "Y"]
    for i, v in enumerate(phase_opts, start=1):
        lists.cell(row=i, column=1, value=v)
    for i, v in enumerate(deliv_opts, start=1):
        lists.cell(row=i, column=2, value=v)
    for i, v in enumerate(yn_opts, start=1):
        lists.cell(row=i, column=3, value=v)
    lists.sheet_state = "hidden"

    # Title + instructions.
    ws.cell(row=1, column=1, value=f"{project_id} — Reorg Plan").font = TITLE_FONT
    ws.cell(row=2, column=1,
            value="Review each row. Use the dropdowns to change Proposed Phase / Proposed "
                  "Deliverable, set Exclude? = Y to leave a file out of the move, then SAVE. "
                  "Claude reads this file back to drive the reorganisation.").font = Font(italic=True, size=9)
    ws.cell(row=3, column=1,
            value=f"Engagement type: {ENGAGEMENT_FULL_LABELS.get(engagement, engagement)}.  "
                  "Mandatory deliverables for this engagement are marked * in the dropdown.  "
                  f"'{LEAVE_OPT}' = keep the file where it is (logged as unclassified).").font = Font(italic=True, size=9)

    # Header.
    for j, h in enumerate(REVIEW_HEADERS, start=1):
        ws.cell(row=5, column=j, value=h)
    _style_header(ws, 5, len(REVIEW_HEADERS))

    # Rows.
    r = REVIEW_DATA_ROW
    for mv in moves:
        src = mv.get("src", "")
        folder = src[:src.rfind("/") + 1] if "/" in src else "(root)"
        row_vals = [src, folder, _phase_label(mv.get("phase")),
                    _deliverable_label(mv.get("deliverable_id"), engagement),
                    "N", mv.get("reason", "")]
        for j, val in enumerate(row_vals, start=1):
            cell = ws.cell(row=r, column=j, value=val)
            cell.alignment = WRAP
            cell.border = BORDER
            if (r - REVIEW_DATA_ROW) % 2 == 1:
                cell.fill = BAND_FILL
        r += 1
    last = r - 1

    # Dropdowns (data validation) referencing the hidden Lists sheet.
    if last >= REVIEW_DATA_ROW:
        dv_phase = DataValidation(type="list", formula1=f"=Lists!$A$1:$A${len(phase_opts)}", allow_blank=True)
        dv_deliv = DataValidation(type="list", formula1=f"=Lists!$B$1:$B${len(deliv_opts)}", allow_blank=True)
        dv_excl = DataValidation(type="list", formula1=f"=Lists!$C$1:$C${len(yn_opts)}", allow_blank=True)
        ws.add_data_validation(dv_phase)
        ws.add_data_validation(dv_deliv)
        ws.add_data_validation(dv_excl)
        dv_phase.add(f"C{REVIEW_DATA_ROW}:C{last}")
        dv_deliv.add(f"D{REVIEW_DATA_ROW}:D{last}")
        dv_excl.add(f"E{REVIEW_DATA_ROW}:E{last}")

    for j, w in enumerate([46, 24, 26, 40, 9, 40], start=1):
        ws.column_dimensions[get_column_letter(j)].width = w
    ws.freeze_panes = "A6"
    return wb


def cmd_build_review(args):
    """Render the proposed mapping as an editable Reorg Plan .xlsx."""
    engagement = getattr(args, "engagement_type", DEFAULT_ENGAGEMENT) or DEFAULT_ENGAGEMENT
    project_id = args.project_id or (Path(args.root).name if args.root else "Project")

    mapping = json.loads(Path(args.mapping).read_text(encoding="utf-8"))
    moves = mapping.get("moves", [])

    wb = build_reorg_plan(project_id, engagement, moves)
    out = Path(args.out).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out)

    print(json.dumps({
        "out": str(out),
        "project_id": project_id,
        "engagement_type": engagement,
        "files_in_plan": len(moves),
        "moving": sum(1 for m in moves if m.get("phase") is not None),
        "leave_in_place": sum(1 for m in moves if m.get("phase") is None),
    }, indent=2))


def cmd_read_review(args):
    """Parse an edited Reorg Plan .xlsx back into a mapping.json for apply-reorg."""
    engagement = getattr(args, "engagement_type", DEFAULT_ENGAGEMENT) or DEFAULT_ENGAGEMENT
    wb = load_workbook(Path(args.xlsx).expanduser().resolve())
    if REVIEW_SHEET not in wb.sheetnames:
        sys.stderr.write(f"Sheet '{REVIEW_SHEET}' not found in {args.xlsx}\n")
        sys.exit(1)
    ws = wb[REVIEW_SHEET]

    moves = []
    excluded = 0
    for row in ws.iter_rows(min_row=REVIEW_DATA_ROW, values_only=True):
        src = row[0]
        if not src or not str(src).strip():
            continue
        phase_label = (row[2] or "").strip() if len(row) > 2 and row[2] else ""
        did_label = (row[3] or "").strip() if len(row) > 3 and row[3] else ""
        exclude = (str(row[4]).strip().upper() if len(row) > 4 and row[4] else "N")
        reason = (row[5] if len(row) > 5 and row[5] else "") or ""

        if exclude == "Y":
            excluded += 1
            continue

        # Deliverable: label looks like "D10: SOW [P0] *".
        did = None
        if did_label and did_label != NONE_OPT:
            did = did_label.split(":", 1)[0].strip() or None
            if did and did not in DELIVERABLE_BY_ID:
                did = None  # ignore an unrecognised id

        # Phase: prefer the deliverable's own phase (authoritative); else parse the phase label.
        phase = None
        if did:
            phase = DELIVERABLE_BY_ID[did][0].index
        elif phase_label and phase_label != LEAVE_OPT:
            head = phase_label.split(".", 1)[0].strip()
            if head.isdigit():
                phase = int(head)

        moves.append({"src": str(src), "phase": phase,
                      "deliverable_id": did, "reason": str(reason)})

    out = Path(args.out).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"moves": moves}, indent=2, ensure_ascii=False), encoding="utf-8")

    print(json.dumps({
        "out": str(out),
        "moves": len(moves),
        "moving": sum(1 for m in moves if m["phase"] is not None),
        "leave_in_place": sum(1 for m in moves if m["phase"] is None),
        "excluded": excluded,
    }, indent=2))


# --------------------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------------------
def _add_template_opts(p):
    """Engagement-type + layout options shared by scaffold and apply-reorg."""
    p.add_argument("--engagement-type", choices=ENGAGEMENT_ORDER, default=DEFAULT_ENGAGEMENT,
                   help="Engagement type that drives the Mandatory column / gate math "
                        f"(default: {DEFAULT_ENGAGEMENT}).")
    p.add_argument("--layout", choices=LAYOUTS, default=DEFAULT_LAYOUT,
                   help="compact = single Mandatory column for the chosen engagement type; "
                        "full = one column per engagement type with the active one marked "
                        f"(default: {DEFAULT_LAYOUT}).")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Kaizen PDP onboarding engine")
    sub = parser.add_subparsers(dest="command", required=True)

    p_sc = sub.add_parser("scaffold", help="Create folder structure + tracking artifacts (greenfield)")
    p_sc.add_argument("--root", required=True, help="Project root folder")
    p_sc.add_argument("--project-id", help="Project ID (default: root folder name)")
    _add_template_opts(p_sc)
    p_sc.set_defaults(func=cmd_scaffold)

    p_scan = sub.add_parser("scan", help="Inventory existing files for classification")
    p_scan.add_argument("--root", required=True)
    p_scan.add_argument("--out", help="Write JSON to this path instead of stdout")
    p_scan.set_defaults(func=cmd_scan)

    p_re = sub.add_parser("apply-reorg", help="Move mapped files + regenerate artifacts (brownfield)")
    p_re.add_argument("--root", required=True)
    p_re.add_argument("--project-id", help="Project ID (default: root folder name)")
    p_re.add_argument("--mapping", required=True, help="mapping.json produced from a scan")
    p_re.add_argument("--dry-run", action="store_true", help="Preview moves without touching files")
    p_re.add_argument("--archive", action="store_true", help="(reserved) snapshot before moving")
    _add_template_opts(p_re)
    p_re.set_defaults(func=cmd_apply_reorg)

    p_br = sub.add_parser("build-review",
                          help="Render the proposed mapping as an editable Reorg Plan .xlsx")
    p_br.add_argument("--mapping", required=True, help="mapping.json produced from a scan")
    p_br.add_argument("--out", required=True, help="Output .xlsx path for the editable plan")
    p_br.add_argument("--root", help="Project root (used only to default the Project ID)")
    p_br.add_argument("--project-id", help="Project ID (default: root folder name)")
    p_br.add_argument("--engagement-type", choices=ENGAGEMENT_ORDER, default=DEFAULT_ENGAGEMENT,
                      help=f"Engagement type (marks mandatory deliverables; default: {DEFAULT_ENGAGEMENT}).")
    p_br.set_defaults(func=cmd_build_review)

    p_rr = sub.add_parser("read-review",
                          help="Parse an edited Reorg Plan .xlsx back into a mapping.json")
    p_rr.add_argument("--xlsx", required=True, help="The edited Reorg Plan .xlsx")
    p_rr.add_argument("--out", required=True, help="Output mapping.json path")
    p_rr.set_defaults(func=cmd_read_review)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
