#!/usr/bin/env python3
"""diff_schema.py

Diff two OpenAPI 3.x documents (`--previous` and `--current`), classify every
change to `paths` and `components.schemas` as additive or breaking, print a
human-readable report, and exit non-zero if any breaking change is found
unless `--allow-breaking` is passed.

Intended to be wired into CI as the contract diff gate: run on every backend
PR, comparing the previously committed `openapi.json` against the one just
regenerated from the current code.

Classification rules (see references/breaking-change-policy.md for the full
rationale):

  Breaking:
    - removed endpoint (path removed, or method removed from an existing path)
    - removed field from a schema
    - changed field type
    - new required field added to a schema
    - field moved from optional to required
    - enum value removed (narrowed enum)
    - schema removed entirely

  Additive (non-breaking):
    - new endpoint (new path, or new method on an existing path)
    - new optional field added to a schema
    - new enum value added
    - new schema added
    - field moved from required to optional (loosening)

Usage:
    python3 diff_schema.py --previous old_openapi.json --current new_openapi.json
    python3 diff_schema.py --previous old_openapi.json --current new_openapi.json --allow-breaking
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from typing import Any, Dict, List, Set, Tuple

BREAKING = "BREAKING"
ADDITIVE = "ADDITIVE"

HTTP_METHODS = {"get", "put", "post", "delete", "options", "head", "patch", "trace"}


@dataclass
class Change:
    kind: str  # BREAKING or ADDITIVE
    area: str  # "path" or "schema"
    description: str


def load_openapi(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def diff_paths(previous: Dict[str, Any], current: Dict[str, Any]) -> List[Change]:
    changes: List[Change] = []
    prev_paths = previous.get("paths", {}) or {}
    curr_paths = current.get("paths", {}) or {}

    prev_ops: Set[Tuple[str, str]] = set()
    for path, methods in prev_paths.items():
        if not isinstance(methods, dict):
            continue
        for method in methods:
            if method.lower() in HTTP_METHODS:
                prev_ops.add((path, method.lower()))

    curr_ops: Set[Tuple[str, str]] = set()
    for path, methods in curr_paths.items():
        if not isinstance(methods, dict):
            continue
        for method in methods:
            if method.lower() in HTTP_METHODS:
                curr_ops.add((path, method.lower()))

    removed = sorted(prev_ops - curr_ops)
    added = sorted(curr_ops - prev_ops)

    for path, method in removed:
        changes.append(Change(
            BREAKING, "path",
            f"Removed endpoint: {method.upper()} {path}"
        ))

    for path, method in added:
        changes.append(Change(
            ADDITIVE, "path",
            f"New endpoint: {method.upper()} {path}"
        ))

    # Response status code changes for operations present in both.
    for path, method in sorted(prev_ops & curr_ops):
        prev_op = prev_paths[path][method]
        curr_op = curr_paths[path][method]
        prev_responses = set((prev_op.get("responses") or {}).keys())
        curr_responses = set((curr_op.get("responses") or {}).keys())

        removed_statuses = sorted(prev_responses - curr_responses)
        added_statuses = sorted(curr_responses - prev_responses)

        for status in removed_statuses:
            changes.append(Change(
                BREAKING, "path",
                f"{method.upper()} {path}: removed documented response status {status}"
            ))
        for status in added_statuses:
            changes.append(Change(
                ADDITIVE, "path",
                f"{method.upper()} {path}: new documented response status {status}"
            ))

    return changes


def resolve_ref_name(schema: Dict[str, Any]) -> str:
    ref = schema.get("$ref", "")
    prefix = "#/components/schemas/"
    return ref[len(prefix):] if ref.startswith(prefix) else ref


def basic_type_signature(schema: Dict[str, Any]) -> str:
    """A coarse signature used to detect type changes on a property."""
    if not isinstance(schema, dict):
        return "unknown"
    if "$ref" in schema:
        return f"ref:{resolve_ref_name(schema)}"
    if "enum" in schema:
        return "enum:" + ",".join(sorted(str(v) for v in schema["enum"]))
    t = schema.get("type", "any")
    if t == "array":
        items = schema.get("items", {})
        return f"array<{basic_type_signature(items)}>"
    return str(t)


def diff_schema_properties(name: str, prev_schema: Dict[str, Any], curr_schema: Dict[str, Any]) -> List[Change]:
    changes: List[Change] = []

    prev_props = prev_schema.get("properties", {}) or {}
    curr_props = curr_schema.get("properties", {}) or {}
    prev_required = set(prev_schema.get("required", []) or [])
    curr_required = set(curr_schema.get("required", []) or [])

    prev_keys = set(prev_props.keys())
    curr_keys = set(curr_props.keys())

    for field in sorted(prev_keys - curr_keys):
        changes.append(Change(
            BREAKING, "schema",
            f"{name}: removed field '{field}'"
        ))

    for field in sorted(curr_keys - prev_keys):
        if field in curr_required:
            changes.append(Change(
                BREAKING, "schema",
                f"{name}: new REQUIRED field '{field}' (would break existing clients not sending it)"
            ))
        else:
            changes.append(Change(
                ADDITIVE, "schema",
                f"{name}: new optional field '{field}'"
            ))

    for field in sorted(prev_keys & curr_keys):
        prev_sig = basic_type_signature(prev_props[field])
        curr_sig = basic_type_signature(curr_props[field])
        if prev_sig != curr_sig:
            # Distinguish enum-value-only changes from real type changes.
            if prev_sig.startswith("enum:") and curr_sig.startswith("enum:"):
                prev_vals = set(prev_sig[len("enum:"):].split(","))
                curr_vals = set(curr_sig[len("enum:"):].split(","))
                removed_vals = prev_vals - curr_vals
                added_vals = curr_vals - prev_vals
                for v in sorted(removed_vals):
                    changes.append(Change(
                        BREAKING, "schema",
                        f"{name}.{field}: removed enum value '{v}' (narrowed enum)"
                    ))
                for v in sorted(added_vals):
                    changes.append(Change(
                        ADDITIVE, "schema",
                        f"{name}.{field}: new enum value '{v}'"
                    ))
            else:
                changes.append(Change(
                    BREAKING, "schema",
                    f"{name}.{field}: type changed ({prev_sig} -> {curr_sig})"
                ))

        was_required = field in prev_required
        is_required = field in curr_required
        if not was_required and is_required:
            changes.append(Change(
                BREAKING, "schema",
                f"{name}.{field}: became required (was optional)"
            ))
        elif was_required and not is_required:
            changes.append(Change(
                ADDITIVE, "schema",
                f"{name}.{field}: became optional (was required)"
            ))

        prev_nullable = bool(prev_props[field].get("nullable"))
        curr_nullable = bool(curr_props[field].get("nullable"))
        if prev_nullable and not curr_nullable:
            changes.append(Change(
                BREAKING, "schema",
                f"{name}.{field}: no longer nullable (removed 'null' from allowed values)"
            ))
        elif not prev_nullable and curr_nullable:
            changes.append(Change(
                ADDITIVE, "schema",
                f"{name}.{field}: now nullable"
            ))

    return changes


def diff_schemas(previous: Dict[str, Any], current: Dict[str, Any]) -> List[Change]:
    changes: List[Change] = []
    prev_schemas = previous.get("components", {}).get("schemas", {}) or {}
    curr_schemas = current.get("components", {}).get("schemas", {}) or {}

    prev_names = set(prev_schemas.keys())
    curr_names = set(curr_schemas.keys())

    for name in sorted(prev_names - curr_names):
        changes.append(Change(
            BREAKING, "schema",
            f"Removed schema: {name}"
        ))

    for name in sorted(curr_names - prev_names):
        changes.append(Change(
            ADDITIVE, "schema",
            f"New schema: {name}"
        ))

    for name in sorted(prev_names & curr_names):
        changes.extend(diff_schema_properties(name, prev_schemas[name], curr_schemas[name]))

    return changes


def print_report(changes: List[Change]) -> None:
    breaking = [c for c in changes if c.kind == BREAKING]
    additive = [c for c in changes if c.kind == ADDITIVE]

    print("=" * 70)
    print("API CONTRACT DIFF REPORT")
    print("=" * 70)

    if not changes:
        print("No changes detected between previous and current schema.")
        return

    if additive:
        print(f"\nADDITIVE changes ({len(additive)}) — safe, pass silently:")
        for c in additive:
            print(f"  [+] {c.description}")

    if breaking:
        print(f"\nBREAKING changes ({len(breaking)}) — require a version bump + changelog entry:")
        for c in breaking:
            print(f"  [!] {c.description}")

    print("\n" + "-" * 70)
    print(f"Summary: {len(additive)} additive, {len(breaking)} breaking")
    print("-" * 70)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Diff two openapi.json documents and classify changes as additive or breaking."
    )
    parser.add_argument("--previous", required=True, help="Path to the previously committed openapi.json.")
    parser.add_argument("--current", required=True, help="Path to the newly regenerated openapi.json.")
    parser.add_argument(
        "--allow-breaking",
        action="store_true",
        help="Do not fail (exit non-zero) even if breaking changes are found. "
             "Use only for a PR that also performs the required version bump + changelog entry.",
    )
    args = parser.parse_args()

    for label, path in (("--previous", args.previous), ("--current", args.current)):
        try:
            open(path, "r", encoding="utf-8").close()
        except OSError as exc:
            print(f"error: could not open {label} file '{path}': {exc}", file=sys.stderr)
            return 2

    previous = load_openapi(args.previous)
    current = load_openapi(args.current)

    changes: List[Change] = []
    changes.extend(diff_paths(previous, current))
    changes.extend(diff_schemas(previous, current))

    print_report(changes)

    has_breaking = any(c.kind == BREAKING for c in changes)

    if has_breaking and not args.allow_breaking:
        print(
            "\nFAIL: breaking change(s) detected without --allow-breaking. "
            "Bump the API version and add a changelog entry, or re-run with "
            "--allow-breaking once that's done.",
            file=sys.stderr,
        )
        return 1

    if has_breaking and args.allow_breaking:
        print("\nWARNING: breaking change(s) detected but --allow-breaking was set; not failing the build.")

    print("\nOK: no unapproved breaking changes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
