# Source Ingestion Protocols

This reference tells the `raid-raci-setup` skill how to pull RAID-relevant content
out of the different source types the EL/PM can point at. The goal is always the
same: turn free-form source material into the structured item lists that
`scripts/update_raid_log.py` writes into the log (see that script's docstring for
the exact JSON shape). Read the section for whichever source(s) the user chose.

Every source type ends the same way: you produce items tagged with a **provenance
label** so the log stays auditable and re-runs don't create duplicates. The label
is a short human-readable string, e.g. `Email "Re: data access" 2026-07-10`,
`MoM 2026-07-08`, `Teams standup 2026-07-09`, `KT Brief`. Pass it to the script as
`--source-tag`; the script stamps it into each new row's Notes column.

---

## 1. Outlook emails — scoped search only

**Never scan the whole mailbox.** Unbounded inbox reads are slow, noisy, and a
privacy problem — the EL only wants RAID signal from a known slice of mail. Follow
this decision tree every time:

1. **Ask for an Outlook category (tag) first.** Kaizen ELs tag project mail with an
   Outlook category, so that is the primary scope. Ask:
   > "Which Outlook category should I search for RAID items? (e.g. the category you
   > tag this project's mail with)"
2. **If the user has no category, fall back to subject.** Ask:
   > "No category — give me the email subject (or a few subject keywords) to search
   > for, and I'll restrict the search to matching messages."
3. **Search only that scope.** Use the connected Outlook / M365 email search tool
   (e.g. `outlook_email_search`) with the category as a filter, or the subject as
   the query. Cap the search — a recent time window and a small result count — and
   confirm the matched message list with the user before extracting, so they can
   see the search stayed narrow.

If no Outlook/M365 email connector is authorized in the session, say so and offer
the fallback: the user pastes the relevant email text into chat, or saves the
`.msg`/`.eml`/exported copy into a PDP folder and points you at it. Do **not** try
to reach mail by any other means.

From each in-scope email, extract: newly surfaced **risks**, **action items /
to-dos** (who owns what by when), **issues** already occurring, and any **decisions**
recorded. Map them to the four sheets and set `--source-tag` to
`Email "<subject>" <date>`.

---

## 2. Teams meeting transcripts

**Never search all transcripts blindly — ask for the meeting name first.** Just
like the email rule, transcript search must be scoped. Before searching, ask:
> "What's the name of the meeting? I'll narrow the transcript search to that
> meeting only."
Then restrict the search to matching meetings, confirm the matched meeting(s)
with the user, and only then fetch and extract.

Two ways in — the user picked one or both:

- **User provides file or path.** They upload a transcript in chat or point to a
  `.docx`/`.vtt`/`.txt` transcript in a PDP folder. Read it directly (no search
  needed).
- **Pull via connector.** If a meeting/transcript connector is authorized (e.g.
  `list_meetings` + `get_meeting_transcript`, or the `meeting-brief` skill's
  Teams-transcript flow), first ask for the **meeting name** (per the rule above),
  then search by that name (add a date if several meetings share the name), fetch
  the matching transcript, and confirm before extracting. If no such connector is
  authorized, say so and use the file/path route instead.

Transcripts are dense and conversational. Focus extraction on: **decisions** that
were agreed ("we'll go with X"), **actions** assigned aloud ("Priya to send the
sample data by Friday"), **risks/issues** flagged ("we're blocked on access").
Attribute owners and dates where spoken. Tag `Teams <meeting name> <date>`.

---

## 3. Minutes of Meeting (MoM)

MoMs are already structured summaries, usually with explicit Decisions and Action
Items sections — the highest-signal source. The user provides the MoM as a file in
chat or a path in a PDP folder (`.docx`, `.pdf`, `.md`). Read it and map its
sections directly: MoM "Decisions" → Decisions sheet, "Action Items" → Actions
sheet, any "Risks/Issues raised" → Risks/Issues. Tag `MoM <date>`.

---

## 4. Any other PDP document

The user may point at any file in the PDP folders (status reports, requirement
docs, client emails saved as files, spreadsheets of open items, etc.). Read the
file with the appropriate tool for its type, then apply the same
extract-and-map logic. Use a descriptive `--source-tag` naming the document.

---

## Extraction quality bar

- Copy descriptions, names, and dates **verbatim** from the source (guardrail G3) —
  do not paraphrase risk wording or invent owners.
- If a field isn't stated in the source, leave it blank rather than guessing; the
  EL preview will flag blanks for follow-up.
- If the source says an existing item changed (a risk is now closed, an action is
  done), do **not** silently edit the log. Collect these as *proposed changes*
  (sheet + existing ID + fields to set) and present them for EL approval; apply
  only approved ones via the script's `--updates` path.
- When unsure whether something is a Risk vs an Issue: a risk is a *future*
  possibility; an issue is *already happening*. Decisions are agreements; actions
  are to-dos.
