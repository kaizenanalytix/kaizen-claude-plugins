---
name: react-best-practices
description: >
  Reviews a React component against a concrete, opinionated checklist —
  hooks rules, purity, memoization, keys, derived state, error boundaries,
  and accessibility. Use when the user says things like "review this
  component", "is this good React", "React best practices", "why is this
  re-rendering", "why is this slow", "this component feels laggy", "make this
  accessible", "screen reader support", "keyboard navigation", "is this a11y
  compliant", or "performance issue in this component".
---

# React Best Practices

Apply this skill when reviewing a component, diagnosing a re-render or
performance complaint, or asked generally whether some React code is
"good." This is a checklist of concrete rules to check against, not a
tutorial — walk the code against each item below and call out violations by
name.

## 1. Rules of Hooks

- Only call hooks at the top level of a component or custom hook — never
  inside a condition, loop, or nested function.
- Never call a hook after an early `return`. If a component needs to bail
  out conditionally, call all hooks first, then branch.

```tsx
// Bad: hook after early return
if (!user) return null;
const [open, setOpen] = useState(false);

// Good: hooks first, branch after
const [open, setOpen] = useState(false);
if (!user) return null;
```

## 2. Keep render pure

No side effects, no mutating props or state directly during render. Side
effects belong in `useEffect` — or, more often in this architecture, in the
module's data-layer hook (`react-data-layer`) rather than sprinkled directly
into a component. If a component's render body calls `fetch`, dispatches an
action, or mutates a prop object, that's a violation regardless of whether
it's wrapped in `useEffect` somewhere else in the same file.

## 3. Memoization is a targeted fix, not a default

Don't wrap every component in `React.memo` or every value in `useMemo` /
`useCallback` preemptively. Measure first with the React DevTools Profiler,
identify the specific expensive computation or the specific prop causing a
child's unnecessary re-render, then memoize that one thing. Blanket
memoization adds complexity (stale-closure bugs, harder-to-read dependency
arrays) and can itself hurt performance (comparison overhead on values that
were cheap to recompute anyway). If asked to "optimize" a component with no
profiling evidence of a problem, push back and ask what's actually slow
before adding memoization.

## 4. List keys

Use a stable, unique id for `key` — never the array index if the list can
reorder, filter, or have items inserted/removed. Index keys cause React to
misattribute state (e.g. an input's local text) to the wrong row after a
reorder.

## 5. Derived state — the most common anti-pattern to flag

Don't use `useState` + `useEffect` to sync one piece of state from another.
Compute the derived value directly during render (wrap in `useMemo` only if
the computation is actually expensive). Treat `useEffect` used purely to
keep two state variables in sync as a smell worth flagging every time it
appears.

## 6. Error boundaries

Wrap route-level or module-level page trees in an error boundary so one
module's crash doesn't blank the whole app. This is a `core/` concern for the
app-wide boundary (wraps the whole router), with optional module-level
boundaries where isolating one module's failure from the rest of the app
matters.

## 7. Accessibility baseline

- Every interactive element is a real `<button>`, `<a>`, or `<input>` — not a
  `<div onClick>`.
- Every form input has an associated `<label>`.
- Modals and dialogs need focus trapping and `Escape`-to-close.

shadcn/Radix primitives (`react-component-library`) already implement all
three correctly out of the box — this is itself a reason to prefer composing
them over hand-rolling interactive elements, rather than re-solving
accessibility per component.

## 8. State placement — cross-reference, don't re-litigate

This skill covers component-level hygiene, not where state should live. For
prop drilling and the props-vs-context-vs-store decision, hand off to
`react-module-context` and `react-data-layer` rather than re-explaining
state architecture here.

## 9. Controlled vs. uncontrolled inputs

Pick one per form and don't mix them within the same form. Prefer controlled
inputs for anything validated or submitted (react-hook-form-style patterns),
since mixing controlled and uncontrolled inputs in one form is a common
source of "why isn't this value updating" bugs.

## 10. Reference file

Read `references/anti-patterns.md` for a bad/good code snippet for each rule
above — use it to produce concrete before/after examples in a review rather
than describing the fix abstractly.

---
_Last reviewed: 2026-08-05_
