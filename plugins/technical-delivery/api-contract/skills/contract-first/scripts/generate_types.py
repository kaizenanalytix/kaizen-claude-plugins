#!/usr/bin/env python3
"""generate_types.py

Generate TypeScript interfaces from an OpenAPI 3.x `components.schemas`
section.

For every schema found under `components.schemas` in the given
`openapi.json`, this script writes one `.ts` file into the output directory
containing an `export interface <Name> { ... }` declaration, with imports
for any nested schemas referenced via `$ref`.

Every generated file starts with:

    // AUTO-GENERATED — do not edit. Source: <input file>
    // Regenerate with generate_types.py

Generated files are meant to be committed to version control and consumed
as read-only vendored types. Never hand-edit them — fix the source OpenAPI
schema (or the backend model that produces it) and regenerate instead.

Usage:
    python3 generate_types.py --input openapi.json --out ./generated/types
    python3 generate_types.py --input openapi.json --out ./generated/types --index

OpenAPI -> TypeScript type mapping:
    string                          -> string
    integer / number                -> number
    boolean                         -> boolean
    array (items: T)                -> T[]
    object / $ref                   -> nested interface reference
    nullable: true                  -> "| null" appended
    enum: [...]                     -> string literal union
    field not in `required`         -> optional property ("?")
    anything unrecognized           -> unknown
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import sys
from typing import Any, Dict, List, Set, Tuple

REF_PREFIX = "#/components/schemas/"


def load_openapi(path: str) -> Dict[str, Any]:
    """Load and parse an openapi.json file."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def ref_name(ref: str) -> str:
    """Extract the schema name from a `#/components/schemas/Name` ref."""
    if not ref.startswith(REF_PREFIX):
        raise ValueError(f"Unsupported $ref (only local component schemas are supported): {ref}")
    return ref[len(REF_PREFIX):]


def ts_identifier(name: str) -> str:
    """Sanitize a schema name into a valid TS identifier."""
    safe = re.sub(r"[^0-9A-Za-z_]", "_", name)
    if safe and safe[0].isdigit():
        safe = f"_{safe}"
    return safe or "Anonymous"


def schema_type_to_ts(schema: Dict[str, Any], deps: Set[str]) -> str:
    """
    Convert a single OpenAPI schema (or property) node into a TypeScript
    type expression. Adds any referenced schema names to `deps` so the
    caller can emit the right imports.
    """
    if not isinstance(schema, dict):
        return "unknown"

    if "$ref" in schema:
        name = ts_identifier(ref_name(schema["$ref"]))
        deps.add(name)
        return name

    # Combinators
    if "allOf" in schema:
        parts = [schema_type_to_ts(s, deps) for s in schema["allOf"]]
        return "(" + " & ".join(parts) + ")" if parts else "unknown"
    if "oneOf" in schema or "anyOf" in schema:
        key = "oneOf" if "oneOf" in schema else "anyOf"
        parts = [schema_type_to_ts(s, deps) for s in schema[key]]
        return "(" + " | ".join(parts) + ")" if parts else "unknown"

    if "enum" in schema:
        values = schema["enum"]
        literals = []
        for v in values:
            if isinstance(v, str):
                literals.append(json.dumps(v))
            elif v is None:
                literals.append("null")
            else:
                literals.append(json.dumps(v))
        base = " | ".join(literals) if literals else "unknown"
        return base

    schema_type = schema.get("type")

    if schema_type == "string":
        base = "string"
    elif schema_type in ("integer", "number"):
        base = "number"
    elif schema_type == "boolean":
        base = "boolean"
    elif schema_type == "array":
        items = schema.get("items", {})
        item_type = schema_type_to_ts(items, deps)
        base = f"{item_type}[]"
    elif schema_type == "object" or "properties" in schema:
        # Inline anonymous object — render as a TS inline object type.
        base = render_inline_object(schema, deps)
    elif schema_type is None and "$ref" not in schema:
        base = "unknown"
    else:
        base = "unknown"

    if schema.get("nullable"):
        base = f"{base} | null"

    return base


def render_inline_object(schema: Dict[str, Any], deps: Set[str]) -> str:
    """Render an anonymous inline object schema as a TS object type literal."""
    props = schema.get("properties", {})
    required = set(schema.get("required", []))
    if not props:
        return "Record<string, unknown>"
    lines = []
    for prop_name, prop_schema in props.items():
        optional = "" if prop_name in required else "?"
        ts_type = schema_type_to_ts(prop_schema, deps)
        lines.append(f"  {prop_name}{optional}: {ts_type};")
    return "{\n" + "\n".join(lines) + "\n}"


def render_interface(name: str, schema: Dict[str, Any]) -> Tuple[str, Set[str]]:
    """
    Render a single top-level schema as a TS `interface` (for object
    schemas) or a `type` alias (for enums, unions, primitives, arrays).
    Returns (declaration_source, set_of_referenced_schema_names).
    """
    deps: Set[str] = set()
    safe_name = ts_identifier(name)

    if "enum" in schema:
        ts_type = schema_type_to_ts(schema, deps)
        decl = f"export type {safe_name} = {ts_type};"
        return decl, deps

    schema_type = schema.get("type")
    if schema_type == "object" or "properties" in schema or (schema_type is None and "allOf" not in schema and "oneOf" not in schema and "anyOf" not in schema and "$ref" not in schema):
        props = schema.get("properties", {})
        required = set(schema.get("required", []))
        if not props:
            decl = f"export interface {safe_name} {{}}"
            return decl, deps
        lines = [f"export interface {safe_name} {{"]
        for prop_name, prop_schema in props.items():
            optional = "" if prop_name in required else "?"
            ts_type = schema_type_to_ts(prop_schema, deps)
            lines.append(f"  {prop_name}{optional}: {ts_type};")
        lines.append("}")
        decl = "\n".join(lines)
        return decl, deps

    # Fallback: array / allOf / oneOf / anyOf / $ref / primitive at top level
    ts_type = schema_type_to_ts(schema, deps)
    decl = f"export type {safe_name} = {ts_type};"
    return decl, deps


def build_file_content(name: str, schema: Dict[str, Any], source_file: str) -> Tuple[str, Set[str]]:
    decl, deps = render_interface(name, schema)
    deps.discard(ts_identifier(name))  # don't self-import

    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    header = (
        f"// AUTO-GENERATED — do not edit. Source: {source_file}\n"
        f"// Regenerate with generate_types.py (generated {timestamp})\n"
    )

    import_lines: List[str] = []
    for dep in sorted(deps):
        import_lines.append(f'import type {{ {dep} }} from "./{dep}";')

    body_parts = [header]
    if import_lines:
        body_parts.append("\n".join(import_lines) + "\n")
    body_parts.append(decl + "\n")

    return "\n".join(body_parts), deps


def generate(input_path: str, out_dir: str, index: bool) -> List[str]:
    spec = load_openapi(input_path)
    schemas = spec.get("components", {}).get("schemas", {})

    if not schemas:
        print(f"warning: no schemas found under components.schemas in {input_path}", file=sys.stderr)

    os.makedirs(out_dir, exist_ok=True)

    written: List[str] = []
    for name, schema in schemas.items():
        safe_name = ts_identifier(name)
        content, _deps = build_file_content(name, schema, os.path.basename(input_path))
        out_path = os.path.join(out_dir, f"{safe_name}.ts")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(content)
        written.append(out_path)

    if index and schemas:
        index_lines = [
            "// AUTO-GENERATED — do not edit. Source: " + os.path.basename(input_path),
            "// Regenerate with generate_types.py",
            "",
        ]
        for name in schemas:
            safe_name = ts_identifier(name)
            index_lines.append(f'export * from "./{safe_name}";')
        index_path = os.path.join(out_dir, "index.ts")
        with open(index_path, "w", encoding="utf-8") as f:
            f.write("\n".join(index_lines) + "\n")
        written.append(index_path)

    return written


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate TypeScript interfaces from an OpenAPI components.schemas section."
    )
    parser.add_argument("--input", required=True, help="Path to the openapi.json file.")
    parser.add_argument("--out", required=True, help="Output directory for generated .ts files.")
    parser.add_argument(
        "--index",
        action="store_true",
        help="Also emit an index.ts that re-exports every generated schema.",
    )
    args = parser.parse_args()

    if not os.path.isfile(args.input):
        print(f"error: input file not found: {args.input}", file=sys.stderr)
        return 1

    written = generate(args.input, args.out, args.index)
    print(f"Generated {len(written)} file(s) in {args.out}:")
    for path in written:
        print(f"  {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
