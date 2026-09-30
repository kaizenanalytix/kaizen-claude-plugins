// Shared transcript reading for the gates that need to prove a human actually saw
// something before it happened.
//
// THE WHOLE POINT. Everything a model can write by itself — a state file, a marker
// in a command, a note in a description — is an ATTESTATION it can satisfy inside
// the same turn without a human ever seeing anything. The one thing it cannot
// fabricate is a USER TURN. So both gates ask the same question of the transcript:
// did a real user turn happen at the right moment?
//
// Extracted from preview-gate.js when write-gate.js needed the identical logic.
// Duplicating a three-line git() helper is fine; duplicating this is not — a fix to
// the entry-shape handling has to land in one place or one gate silently stops
// enforcing while the other keeps working.

"use strict";

const fs = require("fs");

// Entry shape has changed across Claude Code versions (entry.message.content vs
// entry.content). Handle both; anything else yields "" and the caller fails open.
function textOf(entry) {
  const msg = entry && (entry.message || entry);
  const content = msg && msg.content;
  if (typeof content === "string") return content;
  if (Array.isArray(content)) {
    return content
      .filter((b) => b && b.type === "text" && typeof b.text === "string")
      .map((b) => b.text)
      .join("\n");
  }
  return "";
}

function roleOf(entry) {
  const e = entry || {};
  return (e.message && e.message.role) || e.role || e.type || "";
}

// CRITICAL: tool results are ALSO recorded as type:"user". A real user turn is one
// whose content is a plain string, or whose FIRST block is type:"text". Getting
// this wrong makes every gate built on it a silent no-op, because every tool result
// would look like the user answering.
//
// EQUALLY CRITICAL (0.9.0): the harness also records text it injects as type:"user"
// with a text first block — image reads, <system-reminder>s, skill loads, command
// stdout, compaction summaries, interrupt notices. They carry isMeta /
// isCompactSummary, or a recognisable prefix. Counting them was the bug behind "it
// blocks normal code later in the session": each one slid the write-gate window past
// an approval the user had already given, and it also let a system message stand in
// for the user answering a database preview.
//
// A real prompt can arrive with a <system-reminder> block in FRONT of it in the same
// message, so reminders are stripped rather than disqualifying the whole entry: the
// turn is real if any text survives that isn't itself harness-injected.
const INJECTED_PREFIX =
  /^\s*(<local-command-stdout>|<local-command-stderr>|\[Request interrupted|\[Image: source:|Base directory for this skill|Caveat: The messages below|This session is being continued)/;
const REMINDER_BLOCK = /<system-reminder>[\s\S]*?(<\/system-reminder>|$)/g;

function isHumanText(s) {
  const t = String(s || "").replace(REMINDER_BLOCK, "").trim();
  return t.length > 0 && !INJECTED_PREFIX.test(t);
}

function isRealUserTurn(entry) {
  if (roleOf(entry) !== "user") return false;
  if (entry && (entry.isMeta || entry.isCompactSummary || entry.isVisibleInTranscriptOnly)) return false;
  const msg = (entry && entry.message) || entry;
  const content = msg && msg.content;
  if (typeof content === "string") return isHumanText(content);
  if (Array.isArray(content)) {
    if (!content.length || !content[0] || content[0].type !== "text") return false;
    return content.some((b) => b && b.type === "text" && isHumanText(b.text));
  }
  return false;
}

// Reads the tail of the JSONL and returns the entries that parsed. Returns null on
// any I/O or shape problem so callers can fail open rather than guess.
function readTail(transcriptPath, bytes) {
  if (!transcriptPath || !fs.existsSync(transcriptPath)) return null;
  try {
    const size = fs.statSync(transcriptPath).size;
    const start = Math.max(0, size - (bytes || 200000));
    const fd = fs.openSync(transcriptPath, "r");
    try {
      const len = size - start;
      const buf = Buffer.alloc(len);
      fs.readSync(fd, buf, 0, len, start);
      const lines = buf.toString("utf8").split("\n");
      if (start > 0) lines.shift(); // first line is probably partial
      const out = [];
      for (const l of lines) {
        const s = l.trim();
        if (!s) continue;
        try {
          out.push(JSON.parse(s));
        } catch {
          // a partial or non-JSON line is skipped, not fatal
        }
      }
      return out;
    } finally {
      fs.closeSync(fd);
    }
  } catch {
    return null;
  }
}

// Indices of every real user turn, oldest first.
function userTurnIndices(entries) {
  const out = [];
  for (let i = 0; i < entries.length; i++) if (isRealUserTurn(entries[i])) out.push(i);
  return out;
}

// Normalise for comparison: collapse whitespace, so a preview that wrapped a
// command across lines still matches the single-line command being run.
function norm(s) {
  return String(s).replace(/\s+/g, " ").trim();
}

module.exports = { textOf, roleOf, isRealUserTurn, readTail, userTurnIndices, norm };
