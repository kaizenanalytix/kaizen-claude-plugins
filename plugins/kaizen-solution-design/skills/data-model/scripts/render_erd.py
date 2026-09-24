#!/usr/bin/env python3
"""Render an ER diagram from a JSON spec into an editable draw.io file (+ optional PNG preview).

This renderer is specific to the `data-model` skill — it is a fork/adaptation of the general
JSON-spec -> draw.io pattern used elsewhere in the kaizen-solution-design plugin, kept
independent so this skill can evolve its own layout and styling without affecting (or being
affected by) other diagram-rendering skills.

Usage:
    python render_erd.py --spec SPEC.json --out "data-model/ERD.drawio" [--png OUT.png] [--no-png]

Spec shape (see also build_data_dictionary.py, which consumes the same spec):

{
  "title": "Customer Loyalty Data Model",
  "entities": [
    {
      "name": "dim_customer",
      "kind": "dim",              // "dim" | "fact" | "table" | "bridge"  (styling hint only)
      "attributes": [
        {
          "name": "customer_sk", "type": "NUMBER(38,0)",
          "pk": true, "fk": false, "nullable": false,
          "business_definition": "Surrogate key for the customer dimension.",
          "source_system": "SAP", "scd_type": "Type 2",
          "sample_value": "10042", "notes": ""
        }
        // ... more attributes
      ]
    }
    // ... more entities
  ],
  "relationships": [
    {
      "from": "fact_order", "to": "dim_customer",
      "from_attr": "customer_sk", "to_attr": "customer_sk",
      "cardinality": "many-to-one", "label": "placed by"
    }
  ]
}

Pure standard library except the optional Pillow-based PNG preview.
"""
import argparse, json, os, sys, html, math

KIND_COLORS = {
    "dim": ("#DAE8FC", "#6C8EBF"),
    "fact": ("#D5E8D4", "#82B366"),
    "bridge": ("#FFE6CC", "#D79B00"),
    "table": ("#F5F5F5", "#666666"),
}

ENTITY_WIDTH = 240
ROW_HEIGHT = 22
HEADER_HEIGHT = 30
COLS_PER_ROW = 3
COL_GAP = 80
ROW_GAP = 60


def esc(s):
    return html.escape(str(s), quote=True)


def entity_height(entity):
    return HEADER_HEIGHT + ROW_HEIGHT * max(1, len(entity.get("attributes", [])))


def build_entity_label(entity):
    """HTML label rendering the entity as a table — PK/FK flagged, type shown."""
    name = esc(entity["name"])
    fill, stroke = KIND_COLORS.get(entity.get("kind", "table"), KIND_COLORS["table"])
    rows = []
    for attr in entity.get("attributes", []):
        flag = ""
        if attr.get("pk"):
            flag += "PK "
        if attr.get("fk"):
            flag += "FK"
        flag = flag.strip()
        rows.append(
            '<tr>'
            '<td align="left" style="padding:2px 6px;font-weight:%s;">%s</td>'
            '<td align="left" style="padding:2px 6px;color:#555;font-size:10px;">%s</td>'
            '<td align="left" style="padding:2px 6px;color:#900;font-size:10px;">%s</td>'
            '</tr>' % (
                "bold" if attr.get("pk") else "normal",
                esc(attr["name"]),
                esc(attr.get("type", "")),
                flag,
            )
        )
    table_html = (
        '<table style="width:100%;border-collapse:collapse;font-family:Helvetica;font-size:11px;">'
        + "".join(rows)
        + "</table>"
    )
    header_html = (
        '<div style="background:%s;border-bottom:2px solid %s;padding:4px;font-weight:bold;'
        'font-family:Helvetica;font-size:12px;">%s</div>' % (fill, stroke, name)
    )
    return header_html + table_html, stroke


def main():
    ap = argparse.ArgumentParser(description="Render an ER diagram as a draw.io file (+PNG preview).")
    ap.add_argument("--spec", required=True)
    ap.add_argument("--out", required=True, help="Output .drawio path")
    ap.add_argument("--png", default=None, help="PNG preview path (default: alongside --out)")
    ap.add_argument("--no-png", action="store_true", help="Skip the PNG preview")
    args = ap.parse_args()

    with open(args.spec, encoding="utf-8") as f:
        spec = json.load(f)

    entities = spec.get("entities", [])
    relationships = spec.get("relationships", [])
    title = spec.get("title", "Data Model")

    # --- Grid layout ---
    positions = {}
    for i, entity in enumerate(entities):
        col = i % COLS_PER_ROW
        row = i // COLS_PER_ROW
        x = col * (ENTITY_WIDTH + COL_GAP) + 40
        y = row * 260 + 40  # generous row pitch; refined below per-row max height
        positions[entity["name"]] = (x, y)

    # Recompute y using per-row max height so tall entities don't overlap the next row
    row_heights = {}
    for i, entity in enumerate(entities):
        row = i // COLS_PER_ROW
        row_heights[row] = max(row_heights.get(row, 0), entity_height(entity))
    cum_y = {}
    running = 40
    for row in sorted(row_heights):
        cum_y[row] = running
        running += row_heights[row] + ROW_GAP
    for i, entity in enumerate(entities):
        col = i % COLS_PER_ROW
        row = i // COLS_PER_ROW
        x = col * (ENTITY_WIDTH + COL_GAP) + 40
        y = cum_y[row]
        positions[entity["name"]] = (x, y)

    # --- Build mxGraph XML ---
    cells = []
    cell_id = 2  # 0 and 1 are reserved root cells
    entity_cell_id = {}

    for entity in entities:
        name = entity["name"]
        x, y = positions[name]
        h = entity_height(entity)
        label_html, stroke = build_entity_label(entity)
        cid = "entity_%d" % cell_id
        cell_id += 1
        entity_cell_id[name] = cid
        cells.append(
            '<mxCell id="%s" value="%s" style="shape=none;html=1;whiteSpace=wrap;verticalAlign=top;'
            'align=left;strokeColor=%s;fillColor=none;spacing=0;overflow=fill;" vertex="1" parent="1">'
            '<mxGeometry x="%d" y="%d" width="%d" height="%d" as="geometry"/></mxCell>'
            % (cid, esc(label_html), stroke, x, y, ENTITY_WIDTH, h)
        )
        # add a plain border rectangle behind/around it since shape=none has no outline
        cells.append(
            '<mxCell id="%s_border" style="rounded=0;whiteSpace=wrap;html=1;fillColor=none;'
            'strokeColor=%s;strokeWidth=1.5;" vertex="1" parent="1">'
            '<mxGeometry x="%d" y="%d" width="%d" height="%d" as="geometry"/></mxCell>'
            % (cid, stroke, x, y, ENTITY_WIDTH, h)
        )

    for i, rel in enumerate(relationships):
        src = entity_cell_id.get(rel["from"])
        tgt = entity_cell_id.get(rel["to"])
        if not src or not tgt:
            print("Warning: relationship references unknown entity: %s" % rel, file=sys.stderr)
            continue
        label = esc(rel.get("label", rel.get("cardinality", "")))
        eid = "edge_%d" % i
        cells.append(
            '<mxCell id="%s" value="%s" style="edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;'
            'endArrow=none;startArrow=none;fontSize=10;" edge="1" parent="1" source="%s" target="%s">'
            '<mxGeometry relative="1" as="geometry"/></mxCell>' % (eid, label, src, tgt)
        )

    xml = (
        '<mxfile host="app.diagrams.net"><diagram name="%s" id="erd">'
        '<mxGraphModel dx="800" dy="600" grid="1" gridSize="10" guides="1" tooltips="1" '
        'connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="1600" pageHeight="1200" '
        'math="0" shadow="0"><root>'
        '<mxCell id="0"/><mxCell id="1" parent="0"/>'
        "%s"
        "</root></mxGraphModel></diagram></mxfile>"
    ) % (esc(title), "".join(cells))

    with open(args.out, "w", encoding="utf-8") as f:
        f.write(xml)
    print("Rendered draw.io: %s" % args.out)

    if not args.no_png:
        png_path = args.png or (os.path.splitext(args.out)[0] + ".png")
        try:
            render_png_preview(entities, positions, relationships, entity_cell_id, png_path)
            print("Rendered PNG preview: %s" % png_path)
        except ImportError:
            print("PNG preview skipped (Pillow not installed); .drawio written.", file=sys.stderr)


def render_png_preview(entities, positions, relationships, entity_cell_id, png_path):
    from PIL import Image, ImageDraw, ImageFont

    max_x = max((positions[e["name"]][0] + ENTITY_WIDTH for e in entities), default=800) + 40
    max_y = max((positions[e["name"]][1] + entity_height(e) for e in entities), default=600) + 40
    img = Image.new("RGB", (int(max_x), int(max_y)), "white")
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.load_default()
    except Exception:
        font = None

    box = {}
    for entity in entities:
        name = entity["name"]
        x, y = positions[name]
        h = entity_height(entity)
        fill, stroke = KIND_COLORS.get(entity.get("kind", "table"), KIND_COLORS["table"])
        draw.rectangle([x, y, x + ENTITY_WIDTH, y + HEADER_HEIGHT], fill=fill, outline=stroke, width=2)
        draw.text((x + 6, y + 8), name, fill="black", font=font)
        draw.rectangle([x, y + HEADER_HEIGHT, x + ENTITY_WIDTH, y + h], outline=stroke, width=1)
        for j, attr in enumerate(entity.get("attributes", [])):
            ry = y + HEADER_HEIGHT + j * ROW_HEIGHT
            flag = ("PK " if attr.get("pk") else "") + ("FK" if attr.get("fk") else "")
            draw.text((x + 6, ry + 4), "%s  %s" % (attr["name"], flag.strip()), fill="black", font=font)
        box[name] = (x, y, x + ENTITY_WIDTH, y + h)

    for rel in relationships:
        a = box.get(rel["from"])
        b = box.get(rel["to"])
        if not a or not b:
            continue
        ax, ay = (a[0] + a[2]) / 2, (a[1] + a[3]) / 2
        bx, by = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
        draw.line([ax, ay, bx, by], fill="black", width=1)
        mx, my = (ax + bx) / 2, (ay + by) / 2
        draw.text((mx, my), rel.get("label", rel.get("cardinality", "")), fill="black", font=font)

    img.save(png_path)


if __name__ == "__main__":
    main()
