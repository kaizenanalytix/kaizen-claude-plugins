---
name: react-component-composition
description: >
  Decides when domain/composite components should share code at all, and
  which mechanism to use when they should — composition via `children`, a
  custom hook, or (rarely) a render prop. Use when the user says things like
  "should I extract this into a component", "this looks duplicated", "DRY
  this up", "share this logic between components", or "these two components
  are almost identical".
---

# React Component Composition

Apply this skill when deciding **whether** two similar-looking pieces of
domain/composite code (things living in `modules/<domain>/components/` —
`ProductCard`-style components, not generic primitives) should be merged
into a shared abstraction, and **which** abstraction to reach for. This is
the decision layer that sits above `react-component-library` (which covers
generic shadcn/ui primitives in `shared/components/ui/`) — don't restate
that content here; cross-reference it when the shared thing turns out to be
a primitive rather than a domain composite.

## 1. The rule of three

Two similar-looking components or snippets are not yet a duplication
problem. A **third** occurrence is the signal to extract, not the first or
second. Extracting too early usually guesses the wrong abstraction: the
resulting shared component accumulates a pile of conditional props trying
to serve cases that don't actually share behavior — only appearance. That's
the premature-abstraction trap, and it's worse than the duplication it
was meant to remove.

Caveat: the rule of three is about *incidental* similarity, not deliberate
reuse. If two components share business meaning from the very first
occurrence — they represent the same domain concept and would change for
the same reason — extract immediately regardless of count. Don't wait for a
third copy of something that was never going to diverge.

## 2. The extraction decision tree

Walk these in order when asked to review, extract, or DRY up code:

1. **Business meaning or just resemblance?** Do the two things represent the
   same domain concept with the same reason to change, or do they just look
   or read similarly right now? If it's only resemblance, they may be
   allowed to diverge — forcing a shared abstraction onto coincidentally
   similar code is a common over-DRY mistake (see §5).
2. **Shared meaning + shared markup+logic → extract a component.** Use
   composition (`children`, named slot props) when the reusable part is
   markup plus a bit of accompanying logic.
3. **Shared logic, different markup → extract a custom hook, not a
   component.** If the components render completely different JSX but do
   the same three things internally (fetch the same shape of data, handle
   the same event, derive the same value), the hook is the right call, not
   a shared component with a render prop or a `renderX` prop.
4. **One component injects markup into another's slot → composition, not a
   boolean prop.** When a wrapper needs to control structure while letting
   a caller control content, use `children` or a named slot prop
   (`header`, `footer`). Flag `showFooter`, `variant="withHeader"`, and
   similar boolean/enum props that toggle internal JSX as a smell — that's
   prop explosion, and the fix is composition.
5. **Render props / HOCs are legacy.** Both predate hooks. Prefer a custom
   hook plus composition over either. Only reach for a render prop if a
   third-party library's API requires it — don't introduce one voluntarily
   in first-party code.

## 3. Where the extracted thing lives

- Reused within **one module only** → it stays in that module's
  `components/` or `hooks/` folder. Reuse twice inside the same module is
  not, by itself, a reason to promote to `shared/`.
- Reused **across modules** → promote to `shared/`, per the
  `clean-architecture` shared-zone rule — but only the truly generic part.
  `shared/` must stay zero-business-logic: a `ProductCard`-specific
  composite never belongs there, even if two modules happen to use it. Only
  something like a generic `Card` primitive belongs in `shared/`; the
  domain-specific wrapping around it stays in the module.

## 4. Actively look for silent duplication

When reviewing a module, or when adding a new component similar to an
existing one, don't wait to be told about duplication — look for it. It
often doesn't look like copy-paste:

- The same three-line `formatCurrency` or date-parsing snippet inlined
  across several hooks or components instead of one shared utility.
- Two components with different names (`UserAvatar`, `ProfilePicture`)
  rendering near-identical markup.
- A piece of derived-state logic (filtering, sorting) recomputed slightly
  differently in two hooks instead of living in one shared selector/hook.

Treat any of these as a rule-of-three or business-meaning question exactly
as in §1–2, not as an automatic "extract now."

## 5. When duplication is fine — permission not to extract

Similar-looking code that belongs to domains that will legitimately evolve
differently should stay duplicated. Example: checkout's `AddressForm` and a
shipping module's `AddressForm` may have identical fields today but will
accrue different validation rules as each domain evolves independently.
Forcing them into one shared component creates a worse problem — a coupling
between two domains that have no real reason to change together — than the
duplication it removes. Don't read the rest of this skill as "always
extract": divergent-by-design similarity is a legitimate reason to leave
duplication alone.

## 6. Reference file

Read `references/decision-tree.md` for the decision tree laid out as a
numbered flowchart with yes/no branches, plus three worked TSX examples:
prop-explosion refactored into composition, duplicated markup with shared
logic refactored into a custom hook, and a legitimate-duplication case with
the comment explaining why it isn't extracted. Use that file as the
concrete template when producing a before/after in a review.

---
_Last reviewed: 2026-08-05_
