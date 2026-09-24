# Authoring a draw.io sequence diagram (XML patterns)

How to hand-author a valid, renderable `.drawio` UML **sequence** diagram. draw.io files are
`mxGraphModel` XML. Everything below opens in draw.io / diagrams.net with no plugins.

## 1 · File skeleton

```xml
<mxfile host="app.diagrams.net">
  <diagram id="seq1" name="Create Order">
    <mxGraphModel dx="1200" dy="800" grid="0" gridSize="10" guides="1" tooltips="1"
        connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="1100"
        pageHeight="850" math="0" shadow="0">
      <root>
        <mxCell id="0"/>
        <mxCell id="1" parent="0"/>
        <!-- title, lifelines, activations, messages, frames go here -->
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>
```

Every visible cell sets `parent="1"`, `vertex="1"` (nodes) or `edge="1"` (arrows), and an
`<mxGeometry .../>`. Give each cell a unique `id`.

## 2 · Title (frame header)

```xml
<mxCell id="title" value="Create Order — API Sequence"
    style="text;html=1;fontSize=16;fontStyle=1;fontColor=#002F6C;align=left;verticalAlign=middle;"
    vertex="1" parent="1">
  <mxGeometry x="40" y="20" width="600" height="30" as="geometry"/>
</mxCell>
```

## 3 · Lifelines (participants)

One per participant, evenly spaced across the top (caller left, deepest dependency right). The
`umlLifeline` shape draws the header box AND a dashed line down the full height of its geometry —
so set the **height** to the full diagram length you need (e.g. 640).

```xml
<mxCell id="ll_client" value="Client&#10;[Web App]"
    style="shape=umlLifeline;perimeter=lifelinePerimeter;whiteSpace=wrap;html=1;container=1;
    collapsible=0;recursiveResize=0;outlineConnect=0;fillColor=#E7EEF6;strokeColor=#002F6C;
    fontColor=#1A2B3C;fontStyle=1;fontSize=12;" vertex="1" parent="1">
  <mxGeometry x="60" y="70" width="140" height="640" as="geometry"/>
</mxCell>
<mxCell id="ll_api" value="API&#10;[Gateway]"
    style="shape=umlLifeline;perimeter=lifelinePerimeter;whiteSpace=wrap;html=1;container=1;
    collapsible=0;recursiveResize=0;outlineConnect=0;fillColor=#E7EEF6;strokeColor=#002F6C;
    fontColor=#1A2B3C;fontStyle=1;fontSize=12;" vertex="1" parent="1">
  <mxGeometry x="300" y="70" width="140" height="640" as="geometry"/>
</mxCell>
<!-- repeat for Auth, OrderService, PostgreSQL, External API … spacing ~240px apart -->
```

A **data store** lifeline reads better with a cylinder header — use the same lifeline but
`fillColor=#002F6C;fontColor=#FFFFFF;` so stores stand out, or add a small cylinder node above it.

## 4 · Activation bars (optional but preferred)

A thin rectangle sitting on a lifeline's centre for the span it is active. Centre x = lifeline
x + width/2 − 5 (bar width 10).

```xml
<mxCell id="act_api1" value=""
    style="html=1;points=[];perimeter=orthogonalPerimeter;fillColor=#DAE3F0;strokeColor=#002F6C;"
    vertex="1" parent="1">
  <mxGeometry x="365" y="120" width="10" height="220" as="geometry"/>
</mxCell>
```

## 5 · Messages (the arrows)

Messages are **edges**. Use absolute source/target points on the two lifelines' centre-x at the
same `y` (time). Every message MUST carry a `value` (label).

**Synchronous call** — solid line, filled block head:

```xml
<mxCell id="m1" value="POST /orders {cart}"
    style="html=1;verticalAlign=bottom;endArrow=block;rounded=0;strokeColor=#000000;fontSize=11;"
    edge="1" parent="1">
  <mxGeometry relative="1" as="geometry">
    <mxPoint x="130" y="120" as="sourcePoint"/>
    <mxPoint x="370" y="120" as="targetPoint"/>
  </mxGeometry>
</mxCell>
```

**Return / response** — dashed line, open head (point it back, right → left):

```xml
<mxCell id="m2" value="201 Created {orderId}"
    style="html=1;verticalAlign=bottom;endArrow=open;dashed=1;rounded=0;strokeColor=#000000;
    fontSize=11;" edge="1" parent="1">
  <mxGeometry relative="1" as="geometry">
    <mxPoint x="370" y="330" as="sourcePoint"/>
    <mxPoint x="130" y="330" as="targetPoint"/>
  </mxGeometry>
</mxCell>
```

**Self-message** (a participant calls itself) — a little U-shaped hop on the same lifeline:

```xml
<mxCell id="m3" value="validate payload"
    style="html=1;endArrow=block;rounded=1;strokeColor=#000000;fontSize=11;
    exitX=0.5;exitY=0;entryX=0.5;entryY=0;" edge="1" parent="1">
  <mxGeometry relative="1" as="geometry">
    <mxPoint x="370" y="150" as="sourcePoint"/>
    <mxPoint x="410" y="180" as="targetPoint"/>
    <Array as="points"><mxPoint x="430" y="150"/><mxPoint x="430" y="180"/></Array>
  </mxGeometry>
</mxCell>
```

**Async / fire-and-forget** — dashed line, open head, label it (e.g. `publish OrderCreated`).

Space successive messages ~30–45px apart vertically so labels don't collide. Keep `y` increasing
down the page — never route a call upward.

## 6 · Combined fragments (alt / opt / loop)

Draw a labelled rectangle enclosing the messages it governs, with a small "tab" for the operator
and the guard in `[brackets]`.

```xml
<!-- the frame body -->
<mxCell id="frame_alt" value=""
    style="rounded=0;html=1;fillColor=none;strokeColor=#5A6B7B;dashed=0;verticalAlign=top;"
    vertex="1" parent="1">
  <mxGeometry x="90" y="360" width="520" height="180" as="geometry"/>
</mxCell>
<!-- the operator tab (top-left) -->
<mxCell id="frame_alt_tab" value="alt&#10;[valid token]"
    style="shape=mxgraph.sysml.pentagon;html=1;fontSize=10;fontStyle=1;fontColor=#002F6C;
    fillColor=#E7EEF6;strokeColor=#5A6B7B;align=left;spacingLeft=6;" vertex="1" parent="1">
  <mxGeometry x="90" y="360" width="90" height="26" as="geometry"/>
</mxCell>
<!-- divider for the else branch: a dashed horizontal line + a [guard] label -->
<mxCell id="frame_alt_div"
    style="html=1;endArrow=none;dashed=1;strokeColor=#5A6B7B;" edge="1" parent="1">
  <mxGeometry relative="1" as="geometry">
    <mxPoint x="90" y="455" as="sourcePoint"/>
    <mxPoint x="610" y="455" as="targetPoint"/>
  </mxGeometry>
</mxCell>
```

Put the success messages above the divider, the `[else]` / error messages below it. A **loop**
frame is the same rectangle with the tab reading `loop&#10;[until complete]`; **opt** with
`opt&#10;[if …]`.

## 7 · Palette & type (match the plugin house style)

| Role | Value |
|---|---|
| Lifeline header fill / stroke | `#E7EEF6` / `#002F6C` |
| Data-store lifeline fill / text | `#002F6C` / `#FFFFFF` |
| Activation bar | `#DAE3F0` / `#002F6C` |
| Message arrows | `#000000` |
| Frame stroke / tab | `#5A6B7B` / tab fill `#E7EEF6` |
| Title text | `#002F6C`, bold, 16 |
| Message labels | `#1A2B3C`, 11 |

Use `&#10;` inside `value` for a line break, `&amp;` for `&`, `&lt;`/`&gt;` for `<`/`>`.

## 8 · Build order (recommended)

1. Title. 2. All lifelines (fix their centre-x = geometry x + 70). 3. Activation bars.
4. Messages top → bottom, each labelled, alternating call (solid) / return (dashed).
5. Any alt/opt/loop frames drawn last so they sit behind the messages (or set a low z-order).
6. Validate the XML is well-formed before saving (balanced tags, unique ids, every edge has a
   label). Open once in draw.io to eyeball spacing.
