# Authoring a draw.io technical architecture diagram (XML patterns)

How to hand-author a valid, renderable `.drawio` tiered architecture diagram with real tech-stack
iconography. draw.io files are `mxGraphModel` XML; all `mxgraph.*` stencils below are built into
draw.io / diagrams.net (no external image fetch needed).

## 1 · File skeleton + title + frame

```xml
<mxfile host="app.diagrams.net">
  <diagram id="arch1" name="Technical Architecture">
    <mxGraphModel dx="1400" dy="900" grid="0" page="1" pageWidth="1200" pageHeight="1000"
        math="0" shadow="0">
      <root>
        <mxCell id="0"/>
        <mxCell id="1" parent="0"/>
        <!-- outer frame -->
        <mxCell id="frame" value=""
            style="rounded=0;html=1;fillColor=none;strokeColor=#002F6C;strokeWidth=2;"
            vertex="1" parent="1">
          <mxGeometry x="20" y="20" width="1160" height="960" as="geometry"/>
        </mxCell>
        <mxCell id="title" value="Technical Architecture — &lt;Project&gt;"
            style="text;html=1;fontSize=18;fontStyle=1;fontColor=#002F6C;align=center;"
            vertex="1" parent="1">
          <mxGeometry x="40" y="30" width="1120" height="30" as="geometry"/>
        </mxCell>
        <!-- tier swimlanes + component nodes here -->
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>
```

## 2 · Tier as a grouped subgraph (swimlane container)

Each tier is a `swimlane` — a titled container with a coloured header band. Child components set
`parent="<tier id>"` and their geometry is **relative to the swimlane's top-left**.

```xml
<mxCell id="tier_client" value="CLIENT / PRESENTATION"
    style="swimlane;startSize=30;html=1;horizontal=1;fontStyle=1;fontSize=13;fontColor=#FFFFFF;
    fillColor=#EAF0F7;strokeColor=#002F6C;swimlaneFillColor=#EAF0F7;
    swimlaneLine=1;rounded=0;" vertex="1" parent="1">
  <mxGeometry x="60" y="80" width="1080" height="150" as="geometry"/>
</mxCell>
<!-- a component INSIDE the client tier (parent = tier_client, x/y relative to it) -->
<mxCell id="c_web" value="Web App&#10;[React]"
    style="rounded=1;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#61DAFB;strokeWidth=2;
    fontSize=12;fontColor=#1A2B3C;verticalAlign=middle;" vertex="1" parent="tier_client">
  <mxGeometry x="40" y="60" width="150" height="60" as="geometry"/>
</mxCell>
```

Give the header band a per-tier colour so tiers read apart, e.g. Client `#002F6C`, Networking
`#3B6EA5`, Application `#1F7A5A`, Data `#7A4FA0`, External `#8A6D3B`, Security band `#8A94A0`
(set it via `strokeColor`/header; keep bodies light `#EAF0F7`/`#F5F8FB`). Stack tiers top → bottom
in flow order and keep equal widths.

## 3 · Tech icons — prefer a real stencil

draw.io ships thousands of vendor stencils. Use them for cloud services and common infra. Pattern
(AWS example — the resource icon sits above the label):

```xml
<mxCell id="d_s3" value="Object Store&#10;[S3]"
    style="sketch=0;html=1;aspect=fixed;fontSize=11;fontColor=#232F3E;verticalLabelPosition=bottom;
    verticalAlign=top;align=center;outlineConnect=0;shape=mxgraph.aws4.resourceIcon;
    resIcon=mxgraph.aws4.simple_storage_service;fillColor=#7AA116;strokeColor=none;"
    vertex="1" parent="tier_data">
  <mxGeometry x="40" y="45" width="60" height="60" as="geometry"/>
</mxCell>
```

Handy stencil IDs (swap into `shape=`/`resIcon=`):

| Need | Stencil |
|---|---|
| AWS service icon | `shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.<svc>` — e.g. `lambda`, `rds`, `aurora`, `dynamodb`, `simple_storage_service`, `api_gateway`, `cloudfront`, `elastic_container_service`, `fargate`, `simple_queue_service`, `cognito`, `sagemaker`, `elasticache` |
| Azure service icon | `shape=mxgraph.azure.<svc>` or the mscae set (`shape=mxgraph.mscae.<...>`) — e.g. `app_service`, `sql_database`, `blob_storage`, `functions` |
| GCP service icon | `shape=mxgraph.gcp2.<svc>` — e.g. `cloud_functions`, `cloud_sql`, `cloud_storage`, `bigquery`, `pub_sub` |
| Kubernetes | `shape=mxgraph.kubernetes.<...>` (pod, deploy, svc) |
| Generic database | `shape=cylinder3;whiteSpace=wrap;html=1;fillColor=#E7EEF6;strokeColor=#002F6C;` |
| Generic cache / queue | rounded box + brand colour (below), or the AWS/Azure equivalent |
| Generic cloud boundary | `ellipse;shape=cloud;whiteSpace=wrap;html=1;` |
| User / actor | `shape=umlActor;` or `shape=mxgraph.aws4.user;` |

**Data stores are always cylinders** (or the provider's DB icon). Keep all icon nodes the same
size (e.g. 60×60) for a tidy grid.

## 4 · Tech with no built-in stencil — brand-colour labelled node

For products draw.io has no icon for (React, FastAPI, PostgreSQL, …), use a clean white rounded box
with a **2px brand-coloured border** and the tech name in `[brackets]`. Optionally add a small
brand-colour chip. This renders everywhere with no image fetch.

```xml
<mxCell id="a_api" value="Order API&#10;[FastAPI]"
    style="rounded=1;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#009688;strokeWidth=2;
    fontSize=12;fontColor=#1A2B3C;" vertex="1" parent="tier_app">
  <mxGeometry x="40" y="55" width="150" height="60" as="geometry"/>
</mxCell>
```

Brand-colour reference (`strokeColor`):

| Tech | Hex | Tech | Hex |
|---|---|---|---|
| React | `#61DAFB` | PostgreSQL | `#336791` |
| Angular | `#DD0031` | MySQL | `#4479A1` |
| Vue | `#42B883` | MongoDB | `#47A248` |
| Next.js | `#111111` | Redis | `#DC382D` |
| Node.js | `#339933` | Snowflake | `#29B5E8` |
| Python | `#3776AB` | Elasticsearch | `#005571` |
| FastAPI | `#009688` | Kafka | `#231F20` |
| Django | `#092E20` | RabbitMQ | `#FF6600` |
| Spring Boot | `#6DB33F` | GraphQL | `#E10098` |
| .NET | `#512BD4` | Docker | `#2496ED` |
| Java | `#F89820` | Kubernetes | `#326CE5` |
| Go | `#00ADD8` | Terraform | `#7B42BC` |
| nginx | `#009639` | Stripe | `#635BFF` |
| Databricks | `#FF3621` | Airflow | `#017CEE` |

If a product isn't listed, use Kaizen blue `#002F6C` as the border and rely on the `[tech]` label.

## 5 · Connectors — show direction and protocol

Connect components (and tiers) with labelled arrows in the dominant flow direction. Reference the
component ids as `source`/`target` so arrows stay attached when nodes move.

```xml
<mxCell id="e1" value="HTTPS" style="html=1;endArrow=block;rounded=0;strokeColor=#000000;
    fontSize=10;" edge="1" parent="1" source="c_web" target="a_api">
  <mxGeometry relative="1" as="geometry"/>
</mxCell>
```

Label arrows with the protocol/data (`HTTPS`, `REST/JSON`, `gRPC`, `SQL`, `events`, `S3 PUT`).
Keep the main path uni-directional; draw a dashed arrow for async/eventing.

## 6 · Cross-cutting band (optional)

Auth/identity, secrets, observability, CI/CD don't sit in the request path — place them in a thin
side or bottom band (`swimlane`, header `#8A94A0`) with the relevant tech nodes, and connect with
dashed arrows only where a real dependency exists.

## 7 · Build order & checks

1. Frame + title. 2. Tier swimlanes top → bottom (equal width, flow order). 3. Component nodes
inside each tier (icons where a stencil exists, brand-colour boxes otherwise; stores as cylinders).
4. Labelled directional arrows. 5. Cross-cutting band. 6. Legend if needed. 7. Validate well-formed
XML (balanced tags, unique ids, child geometry relative to its swimlane parent) and open once in
draw.io to check spacing and that every icon resolves.

Escaping in `value`: `&#10;` = line break, `&amp;` = `&`, `&lt;`/`&gt;` = `<`/`>`.
