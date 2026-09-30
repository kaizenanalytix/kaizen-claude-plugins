// SessionStart hook: puts the working agreement in context BEFORE any editing starts.
//
// This is a hook rather than a skill on purpose. A skill loads when its description
// matches a request, which is too late for a rule about what NOT to do mid-task —
// nobody phrases a request as "remind me not to run the build yet". The `working-agreement`
// skill carries the reasoning; this carries the rules themselves.
//
// Deliberately terse: this text is paid for on every session, so it states the rules and
// points at the skill for the why. Must never throw — a SessionStart hook that fails is
// worse than no hook — hence no filesystem, git, or network access here.

console.log(
  [
    "Working agreement for this session (from the architecture-foundations plugin):",
    "",
    "1. VERIFY IN ONE BATCH, AND ASK FIRST. Finish all edits for the task before running",
    "   anything. Then ask before any build, lint, or type-check — never start one",
    "   unprompted, including after a single edit. Once the user approves, run build and",
    "   lint together, fix what they surface, and report both.",
    "2. FLAG PRE-EXISTING ISSUES, DON'T SILENTLY FIX THEM. Duplicates, dead code, or",
    "   off-convention files near your change get surfaced with a concrete suggestion, for",
    "   the user to decide. Don't fix them unasked, and don't let them balloon the task.",
    "3. RECOMMEND A MODEL TIER when restating understanding or asking a clarifying",
    "   question — one line, suited to the task. Not on every reply.",
    "4. NEVER ASSUME A DETAIL — ASK. Before scaffolding or implementing anything",
    "   non-trivial, check the repo for existing technical documentation (README,",
    "   /docs, ADRs, linked specs) and read it. For anything a choice depends on that",
    "   isn't already pinned down by that documentation or an explicit answer in this",
    "   conversation — which library, which pattern, which stack detail — ask the user",
    "   directly rather than picking a default silently.",
    "",
    "Read the `working-agreement` skill for the reasoning and the edge cases.",
  ].join("\n")
);

process.exit(0);
