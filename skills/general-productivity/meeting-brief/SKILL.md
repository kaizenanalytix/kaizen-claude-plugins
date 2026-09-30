---
name: meeting-brief
description: >-
  Produce a daily or weekly meeting brief from Microsoft Teams recorded meeting
  transcripts, and keep a rolling personal action tracker, both saved to the
  user's OneDrive project folder. Use this whenever the user asks for a meeting
  brief, meeting summary, recap of their meetings, "what happened in my meetings
  today", a weekly meetings roundup, or to pull action items and decisions out of
  recent meetings. Trigger on daily or weekly cadence, and on any phrasing about
  summarizing, recapping, or extracting decisions and action items from meetings,
  even if the words "brief" or "transcript" are not used. This skill reads
  recorded meeting transcripts only, and always works on the running user's own
  meetings.
---

# Meeting brief

Turn the user's recorded Microsoft Teams meeting transcripts into a clear Word brief,
and maintain a rolling Excel action tracker that accumulates across runs. The skill
runs in two modes, daily and weekly. It always operates on the running user's own
calendar and transcripts, and writes everything to that user's own OneDrive.

## What you need before running (baseline, do not change)

This skill assumes the one-time setup is already in place. Treat these as fixed
prerequisites, not things to reconfigure:

- A Cowork project (for example "My productivity project")
- The Microsoft 365 connector is on, so meetings, the calendar, and transcripts can be read
- The personal OneDrive is connected, with the project folder available for output

If any prerequisite is missing, say so plainly and stop, rather than guessing or
working around it.

## Files this skill maintains

All inside the user's project folder in OneDrive:

- Dated Word briefs (daily and weekly).
- `Action-tracker.xlsx`, one rolling Excel tracker that accumulates across runs.
- A `Recurring/` area, with one folder per recurring meeting, holding dated occurrence files.
- `recurring-meetings.json`, a small ledger that remembers which recurring meetings have a
  folder and which the user has opted out of.

## Important: transcripts only

The skill reads recorded meeting transcripts. It does not work from individual call
records or from calendar entries alone. A transcript exists only when the meeting was
recorded or transcription was turned on, and when retention has kept it. If a meeting
in the window has no transcript, skip it and note it in the brief. Never invent meeting
content that is not in a transcript.

## Core principle: treat every meeting with equal weight

By default, summarize every meeting in the window the same way. Do not rank meetings,
do not label any meeting important or unimportant, and do not decide what mattered to
the user. Each meeting is summarized on its own terms and every action item is captured.
A meeting that contained little will naturally produce a short entry; a meeting that
contained a lot will produce a longer one. That difference reflects content, not a
judgment of value.

The only exception is the volume valve in Step 5, which changes how much narrative prose
a meeting gets on a genuinely heavy day. It never changes action capture, and it never
ranks meetings by importance.

## Step 1: Decide the mode and the date window

Work out whether this is a daily or weekly run, then set the window:

- Daily: covers today, from the start of the day to now. If the user names a specific
  date, use that single day instead.
- Weekly: covers the current work week, Monday through today. If the user names a range
  or says "last 7 days", use that instead.

If the cadence is unclear, default to daily for today, and state which window you used
so the user can correct it.

## Step 2: Find the meetings in the window

Use the Microsoft 365 connector to list the user's meetings inside the window from the
calendar. Keep only real meetings (skip cancelled or declined entries and personal holds
with no other attendees). For each meeting, record its calendar event title, its start
time, and its recurrence information (whether it belongs to a recurring series, and that
series identifier). The title is used for naming, the recurrence information for Step 4b.

## Step 3: Pull the transcript for each meeting

For each meeting, retrieve its transcript through the Microsoft 365 connector.

- If a transcript is available, read it.
- If no transcript is available, do not fail the run. Record the meeting under
  "Meetings without a transcript" with a one line reason (most often: the meeting was
  not recorded), and continue.

For weekly runs, before re-reading every transcript, check the daily briefs already in
the project folder for the same week. If they are present, build the weekly roll-up from
those briefs so the daily and weekly views stay consistent and the run is faster. Fall
back to reading transcripts directly for any day that has no daily brief.

## Step 4: Summarize each meeting and name it by its calendar title

Summarize from the transcript only, capturing what is actually present. For each meeting capture:

- Decisions: what was agreed or concluded.
- Action items: the task, the owner if one is identifiable, and a due date if one is stated.
- Follow-ups: open questions, things deferred, and anything left unresolved.

Name each meeting section using the meeting's calendar event title. Handle these cases:

- Two meetings with the same title in one window: keep both, and add the start time to
  tell them apart.
- A title with characters that are not safe in a filename: sanitize it for any filename,
  but always keep the real, unedited title inside the document.
- A very long title: you may shorten it in a filename, but show the full title in the body.
- A recurring meeting that shares a title across days: the meeting date and the tracker's
  source column keep these distinct.

Keep the language plain and factual. Do not editorialize or add advice that was not in
the meeting.

## Step 4b: Recurring meetings get their own folder, flagged once

Some meetings recur, such as a daily standup or a weekly sync. Decide whether a meeting is
recurring from the calendar's recurrence information for the series, not from its title.
Title matching is unreliable, and a renamed or rescheduled series is still the same series.

Use the `recurring-meetings.json` ledger to remember each recurring meeting the skill has
seen. Key each entry by the calendar series identifier, and store the meeting title (for
the folder name and the flag) and a status of either `folder` (it has its own folder) or
`opted-out` (the user does not want a folder for it).

For each recurring meeting in the window, check the ledger:

- Opted out: do nothing special. Summarize it in the brief like any other meeting, and
  never create or offer a folder for it again.
- Already has a folder: write this occurrence into that folder (see layout below). Do not
  prompt.
- Not seen before: create a folder for it, write this occurrence in, record it in the
  ledger with status `folder`, and flag it once to the user (see "Flagging" below).

Folder and file layout for recurring meetings:

```
My productivity project/
  Recurring/
    Daily standup/
      2026-06-29.docx
      2026-06-30.docx
```

The folder is named by the event title (sanitized for the filesystem, with the full title
kept inside the document). Each occurrence is a dated file. The meeting also still appears
in that day's brief as normal, so the brief stays complete and each folder builds a
running history.

Flagging a new recurring folder:

- The first time a recurring meeting gets a folder, note it in the run's summary, for
  example: "Created a new folder for the recurring meeting 'Daily standup'. Leave it as is,
  or tell me if it should not have its own folder."
- Keep the flag lightweight and non-blocking, since the skill may run unattended or on a
  schedule. Do not pause and wait for an answer. The user acts whenever they next look.
- Flag only once per recurring meeting. Never repeat it.

Honoring an opt-out:

- If the user says a recurring meeting should not have its own folder, set its ledger
  status to `opted-out`. From then on, include it in the briefs only, and never create or
  offer a folder for it again.
- Do not delete anything. If a folder already exists with past occurrences, leave those
  files in place and stop adding to it. You may mention that the old folder is no longer
  being updated, and leave removal to the user.

## Step 5: Volume handling (only on genuinely heavy days)

Most days, do nothing here: give every meeting full, equal treatment. Only when the
combined material across the window is large enough that the brief would become unwieldy
should you tighten the narrative. When that happens:

- Tighten based on how much each meeting actually contained, not on importance. Meetings
  with more discussion points, action items, or agenda items keep more of their prose;
  meetings with little to report compress to a line or two. This is proportional to
  content volume, never a ranking of which meeting was important.
- The trigger is total content to summarize, not the raw meeting count. Many short syncs
  should not trigger compression; a few dense sessions might.
- Action capture is never affected. Every action item from every meeting still goes into
  the tracker in full, no matter how busy the day was. Compression only ever shortens the
  narrative prose in the Word brief.
- Every meeting still appears in the brief, even when compressed, so nothing is hidden.

## Step 6: Write the Word brief and save it

Produce a Word (.docx) document using the structure below, then save it to the project
folder in OneDrive.

- Daily filename: Meetings-brief-YYYY-MM-DD.docx
- Weekly filename: Meetings-weekly-YYYY-Www.docx (ISO week, for example 2026-W27)

For any recurring meeting that has a folder, also save that meeting's write-up as a dated
file inside its folder under `Recurring/`, in addition to including it in the brief.

Start with a short summary band so a busy reader can stop after it on most days:

```
Meeting brief: [date]

At a glance
- [N] meetings in scope, [M] with transcripts, [K] without.
- [number] new action items captured ([number] are yours).
- Key decisions: [one line each, only the few that stand out, or "None"].

Meetings (in time order)

[Calendar event title] ([start time])
Decisions
- ... (or None)
Action items
- [task] (owner: [name], yours: yes/no, due: [date if stated])
Follow-ups
- ... (or None)

Meetings without a transcript
- [Calendar event title] ([start time]) - not recorded
```

If a section has nothing in it for a meeting, write "None" under that heading rather than
removing it, so the brief reads the same way every time.

The weekly brief uses the same idea, with the body organized as: themes across the week,
consolidated decisions, action items grouped by owner with the user's own items first,
still-open items, the list of meetings covered, and meetings without a transcript.

## Step 7: Update the rolling action tracker (Excel)

Maintain one rolling tracker per user, not a new file per run. This is the durable record;
the Word brief is the readable narrative.

- Filename: Action-tracker.xlsx in the project folder. Never date it; it accumulates.
- If it does not exist yet, create it with the columns below. If it exists, open it,
  append new items, and preserve everything already there.

Columns:

- ID: a stable key for the item, so the same action is recognized across runs.
- Date captured
- Source meeting: the calendar event title
- Meeting date
- Action
- Owner
- Mine: Yes if the action is the user's own to do, No if it is someone else's or delegated.
- Due date: if stated, otherwise blank.
- Status: Open, In progress, Done, or Delegated. New items default to Open.
- Notes

Deduplication and preserving the user's edits:

- Build the ID from a normalized form of the action (lowercased, trimmed, punctuation and
  extra spaces collapsed) combined with the owner. Use it to tell whether an item is new.
- If an item with that ID already exists, do not add a second row. You may fill in a newly
  stated due date if the existing one was blank, but never overwrite the Status or Notes,
  since the user may have edited those. The user's edits always win.
- If the ID is new, add a new row with Status set to Open.
- Set Mine to Yes only when the action is clearly the user's own. When ownership is
  genuinely unclear, record the owner as "unclear" and set Mine to No rather than guessing.

After the files are written, tell the user the brief filename, confirm the tracker was
updated, surface any new recurring folder flags from Step 4b, and give a one line summary
(for example: "6 meetings, 5 with transcripts, 4 new action items, 2 of them yours").

## Handling the empty and partial cases

Always produce a record, so the user never wonders whether the run failed:

- No meetings in the window: produce a short brief that says there were no meetings in
  scope, and leave the tracker unchanged.
- Meetings found but none had transcripts: produce the brief with a full "Meetings without
  a transcript" list, and remind the user that recording or transcription needs to be on.
- A very long transcript: summarize faithfully rather than truncating, and capture every
  distinct action item even if the prose is condensed.

## Scope and privacy

This skill runs against the running user's own calendar and transcripts only, and writes
only to that user's own OneDrive. It does not read other people's meetings and does not
produce shared output. If asked to summarize meetings the user did not attend or own,
decline and explain why. Controls for excluding sensitive meetings are documented
separately in the privacy and data-handling guide rather than here, so this skill stays
focused on producing the brief and tracker.

## Scheduling

This skill does not run itself on a timer. It produces the brief and tracker when invoked.
Setting it to run automatically each morning or each week is an environment capability and
is covered in a separate scheduling guide, kept apart from this skill so it can be updated
without changing the skill.

## Next level: send action items to Jira (optional, off by default)

When the user has connected a personal Jira board and asks for it, create issues for the
action items. Reuse the tracker's ID as the deduplication key so the same item is never
created twice and so the Word brief, the Excel tracker, and the Jira board all stay in
agreement. Tag each issue with its source meeting so it traces back. Only run this when
the user asks, since it writes to an external system.
