# Source Ingestion Protocols (Status Report)

Beyond the project plan, Jira, and the RAID Log, the EL/PM can point the status
report at recent source material so the report reflects what actually happened
this period — updates from emails, meeting transcripts, Minutes of Meeting, or any
project document. Read the section for whichever source(s) the user chose.

The extraction target here is **status content**, not a RAID log. From each source
pull the things that fill the dashboard regions:

- **Accomplishments** — what got done / advanced / signed off this period.
- **Next priorities** — what the team committed to do next.
- **Risks / issues / blockers** — anything flagged that threatens delivery.
- **Discussion topics & decisions needed** — open questions, escalations, decisions
  the client or leadership owe.
- **Milestone slippage** — any date changes or forecast shifts mentioned.

Attribute owners and dates where stated, and keep wording faithful to the source
(guardrail G3). Status boxes are short, so distil to scannable one-liners.

---

## 1. Outlook emails — scoped search only

**Never scan the whole mailbox.** Follow this decision tree every time:

1. **Ask for an Outlook category (tag) first.** Kaizen ELs tag project mail with an
   Outlook category, so that is the primary scope:
   > "Which Outlook category should I search for status updates? (e.g. the category
   > you tag this project's mail with)"
2. **If the user has no category, fall back to subject:**
   > "No category — give me the email subject (or a few subject keywords) and I'll
   > restrict the search to matching messages."
3. **Search only that scope**, using the connected Outlook/M365 email search tool
   (e.g. `outlook_email_search`) with the category filter or subject query. Cap it
   to a recent window and a small result count, and confirm the matched messages
   with the user before extracting.

If no Outlook/M365 connector is authorized, say so and offer the fallback: the user
pastes the relevant email text into chat, or saves a copy into a PDP folder and
points you at it. Do not reach mail by any other means.

---

## 2. Teams meeting transcripts

**Ask for the meeting name first — never search all transcripts blindly.** Before
searching:
> "What's the name of the meeting? I'll narrow the transcript search to that
> meeting only."

Then restrict the search to matching meetings (add a date if several share the
name), confirm the match, and only then fetch and extract.

Two ways in — the user picked one or both:

- **User provides file or path.** They upload a transcript in chat or point to a
  `.docx`/`.vtt`/`.txt` transcript in a PDP folder. Read it directly (no search).
- **Pull via connector.** If a meeting/transcript connector is authorized (e.g.
  `list_meetings` + `get_meeting_transcript`, or the `meeting-brief` skill's
  Teams-transcript flow), ask for the meeting name per the rule above, search by it,
  fetch the matching transcript, and confirm before extracting. If no connector is
  authorized, say so and use the file/path route instead.

From the transcript, pull decisions agreed, commitments made ("X to do Y by
Friday"), blockers raised, and any milestone/date changes discussed.

---

## 3. Minutes of Meeting (MoM)

MoMs are already structured — usually with explicit Decisions and Action Items
sections. The user provides the MoM as a file in chat or a path in a PDP folder
(`.docx`, `.pdf`, `.md`). Map its sections into the status regions: decisions →
Discussion Topics / decisions needed, action items → Accomplishments (if done) or
Next Priorities (if upcoming), risks/issues raised → Project Risks.

---

## 4. Any other PDP document

The user may point at any file in the PDP folders (a prior status report, a client
email saved as a file, a demo recap, a spreadsheet of open items). Read it with the
appropriate tool and apply the same distil-into-status-regions logic.

---

## Reconciling with Jira and the RAID Log

These narrative sources supplement — they don't override — the structured data.
When an email or transcript conflicts with Jira or the RAID Log (e.g. an item marked
done verbally but still open in Jira), surface the discrepancy in the report or flag
it to the user rather than silently picking one. The RAID Log remains the system of
record for risks; use narrative sources to enrich, not replace, it.
