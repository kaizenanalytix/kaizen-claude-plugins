# Responsive breakpoints — what belongs in the `@responsive` subset

## Why four projects, not "test everything at every size"

There is no such thing as testing "all pixel sizes" — screens exist on a
continuum, not a fixed list. What actually catches responsive bugs is a
small number of representative breakpoints picked to match how the CSS
itself changes behavior, plus the two rendering engines that genuinely
differ in the wild:

| Project | Emulates | Why this one |
|---|---|---|
| `responsive-mobile-chrome` | Pixel 5 (Chrome/Android) | The dominant mobile rendering engine outside iOS. |
| `responsive-mobile-safari` | iPhone 13 (Safari/iOS) | WebKit's mobile viewport/touch handling genuinely differs from Chromium's — this is not redundant with the desktop `smoke-webkit` project. |
| `responsive-tablet` | iPad Mini | Catches the "in-between" breakpoint a lot of layouts get wrong — too wide for the mobile layout, too narrow for the desktop one. |
| `responsive-desktop` | 1280×800 | A real laptop-class desktop viewport, not just whatever the default browser window happens to be. |

Four sizes, two engines on mobile — not an attempt to enumerate every
possible device. If the project has a documented breakpoint these don't
cover (e.g. a specific problem tablet size support has flagged), add one
more project rather than trying to cover the space exhaustively.

## What earns the `@responsive` tag

Tag a spec `@responsive` only when the UI **genuinely behaves or renders
differently** across breakpoints — not just reflows via normal CSS with no
behavioral difference:

- A navigation that collapses into a hamburger menu below a breakpoint.
- A layout that switches from a multi-column grid to a single column.
- Content that's hidden/shown conditionally by viewport (e.g. a sidebar
  that becomes a bottom sheet on mobile).
- Touch-specific interactions that don't exist on desktop (swipe, long-press).

**Don't** tag a spec `@responsive` just because the page "is responsive" in
the general CSS sense — if the only thing that changes is spacing or font
size reflowing normally, that's a visual-regression concern (a screenshot
diff tool), not something worth a full cross-device Playwright run. Running
every spec through four device projects for no behavioral difference is
exactly the "test everything, every device" trap this matrix is designed to
avoid.

## Writing the actual assertions

See `playwright-test-implementation`'s `references/responsive-testing.md`
for the Playwright patterns — asserting the mobile nav's collapsed state,
switching between `test.use({ viewport })` for an ad hoc check versus a
tagged spec for a project that runs in CI, and touch-event testing.

---
_Last reviewed: 2026-08-07_
