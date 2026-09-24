# Concern → skill map (expanded)

Use this table to decide which skill in this plugin to hand off to once you've
identified what the user is actually asking for. Each row expands on the
short version in `SKILL.md`.

| Concern | Route to | Why |
|---|---|---|
| "Add a module", "new feature/domain", "scaffold the X module" | `react-module-scaffold` | Creates the seven-folder module skeleton and wires it into the store and router. |
| "Call the API", "add an endpoint", "manage state", "cache invalidation", "Redux slice" | `react-data-layer` | Establishes the RTK Query (server state) vs. slice (client state) split and the composing hook. |
| "Share state across the module", "avoid prop drilling", "module-scoped context", "Context vs store" | `react-module-context` | Applies the props/context/store decision rule and provides the safe context factory. |
| "Add a route", "set up routing", "protect a page", "lazy-load pages" | `react-routing` | Sets up `React.lazy`, `PrivateRoute`, path constants, and typed `useParams`. |
| "Write tests", "test this component/hook/slice" | `react-testing` | Vitest unit tests and RTL+MSW integration tests — the pyramid's base only. Any browser-driven test, "add e2e" included, routes to a sibling `e2e-testing` plugin instead, at any depth. |
| "New React project", "set up the project", "configure vite/tsconfig" | `react-project-bootstrap` | Stands up a greenfield project with the conventions the other skills assume already in place. |
| "Structure my frontend", "where does this UI code belong", "set up the app architecture" | Stay in `frontend-architecture` | This is the orchestrator itself — apply the three-zone model directly. |
| "What should I name this file/component/hook", "naming convention", "file naming" | `react-naming-conventions` | Concrete case-style and suffix rules for every module subfolder. |
| "Add a button/dialog/dropdown component", "install a component", "set up shadcn", "which component library" | `react-component-library` | Standardizes on shadcn/ui for generic primitives in `shared/components/ui/`, composed into domain components. |
| "Review this component", "is this good React", "why is this re-rendering", "performance issue in this component" | `react-best-practices` | Component-level hygiene checklist — Rules of Hooks, memoization, list keys, accessibility, error boundaries. |
| "Should I extract this into a component", "this looks duplicated", "DRY this up", "share this logic between components", "these two components are almost identical" | `react-component-composition` | The decision layer above `react-component-library`: rule of three, component vs. hook vs. composition-via-children, module-local vs. `shared/` placement, spotting silent duplication, and when duplication is fine to leave alone. |

If a request spans more than one concern (e.g. "add a products module with a
search page and tests"), sequence the skills: `react-module-scaffold` first to
create the skeleton, then `react-data-layer` for the data hook, then
`react-component-library` for any generic UI primitives the page needs, then
`react-routing` to wire the page in, then `react-testing` for coverage. Apply
`react-naming-conventions`, `react-best-practices`, and `react-component-composition`
throughout as hygiene checks, not as a separate step in the sequence.
