# Source Ingestion Protocol

How to extract modeling-relevant content from meeting notes, emails, MoM, and other project
documents. Follow a disciplined extraction pattern — scoped search, never a blind trawl, and a
clear line between what gets modeled automatically versus what gets surfaced for approval.

## Scoped Search Rules (never skip these)

- **Outlook email**: ask for the category/tag first. If none exists, ask for a subject to search
  by. Never scan the whole mailbox looking for "anything data-related" — that's both slow and a
  privacy risk.
- **Teams/meeting transcripts**: ask for the meeting name first, then search that specific
  meeting's transcript. Never search across all transcripts blindly.
- **MoM / other project documents**: only read files the user explicitly provides or points to.

Confirm the concrete source with the user before extracting, every time.

## What Counts as a Modeling Signal

Look for:
- An entity or "thing" the business tracks (customer, order, shipment, invoice...)
- An attribute/field mentioned as something that needs to be stored or reported on
- A relationship between two entities ("every order has one customer but a customer can have
  many orders")
- Volume, frequency, or grain hints ("we get about 10,000 of these a day," "one row per line
  item," "this changes maybe once a year") — these matter for physical/dimensional decisions
  like clustering and fact grain
- A named source system ("this comes from SAP," "pulled from Salesforce") — relevant for the
  Source System column in the data dictionary

## Confidence Policy: Clear Requirement vs. Passing Mention

This is the most important judgment call in this skill, so take it seriously rather than
defaulting to "just include everything" or "just include what's certain."

**Clear requirement** — build directly into the model, no approval gate needed:
- Explicit asks: "we need to track X," "must store Y," "the report requires Z"
- Anything a client stakeholder stated as a requirement, even briefly, with clear intent
- Anything already confirmed in the Business Requirements Document or Solution Overview

**Passing mention** — do not silently add. Hold it and surface it as a call-out at the end of
the run instead:
- Offhand asides ("oh, someone mentioned we might also need...")
- Something said by a person without clear authority to set a requirement, in an uncertain tone
- A single unconfirmed comment with no follow-up or agreement in the source

### Example

> **Client:** "We also need to track when a customer's loyalty tier changes, so we can see their
> history over time."
>
> **PM:** "Got it, we'll note that. Oh, also — Sarah mentioned in passing that some customers have
> a middle name field we should probably capture too."

The first sentence is a clear requirement — it becomes an SCD Type 2 attribute on the `customer`
dimension directly. The second is a passing mention — it goes into the call-out list at the end
of the run ("I also noticed these mentioned in passing — want me to add them?") rather than being
silently modeled.

When genuinely unsure which bucket something falls into, default to **passing mention** — it's
cheaper for the user to approve an addition than to discover an unrequested field was silently
added to their model.

## Provenance

For every item pulled from a source — clear or passing — note where it came from (e.g. `MoM
2026-07-14`, `Email "Re: loyalty program" 2026-07-10`) so the data dictionary's Notes column and
the call-out list can cite the source.
