# Optimization

Use this module when the user wants to **find the best decision** — maximize or minimize an objective subject to constraints — rather than describe, test, or predict. Examples: allocate a budget for maximum return, plan production within capacity, choose which projects to fund, minimize cost while meeting demand.

Helpers live in `scripts/optimization.py` (`solve_lp`, `solve_milp`, `solve_nonlinear`), built on scipy.optimize (`linprog`, `milp`, `minimize`), which is always available; PuLP is a friendlier modeling layer if installed but not required.

## Optimization is different from the rest of the skill

This is **prescriptive**, not descriptive or predictive. Three consequences worth stating to the user:

- It does **not learn from data.** Data only *parameterizes* the objective and constraints (e.g., per-unit profits, resource limits). The model is the formulation, not a fit.
- The answer is **only as good as the formulation.** Decision variables, objective, and constraints are the whole model — and getting them right is the judgment. A missing constraint yields an "optimum" that's infeasible in reality; a wrong objective optimizes the wrong thing. **Confirm the formulation with the user before solving** (per `references/data-transformation-policy.md`).
- There is usually **one optimum to report**, with a solver status — not a distribution or a p-value.

## Picking the problem type

See `references/model-catalog.md` for the annotated optimization menu.


- **Linear program (LP)** (`solve_lp`) — objective and constraints all linear, continuous variables. Solved to a **global optimum** efficiently. Most resource-allocation/blending/transport problems start here.
- **Mixed-integer LP (MILP)** (`solve_milp`) — some variables must be integer or binary (yes/no decisions, counts, "build it or not"). Still linear; **global optimum**, but **NP-hard** — can be slow or intractable for large instances. Flag the cost.
- **Non-linear program (NLP)** (`solve_nonlinear`) — non-linear objective or constraints. scipy returns a **local optimum only**; for non-convex problems that may not be the global best. Use several restarts (`n_restarts`) and **state that the result is local unless convexity is established**.

When in doubt, formulate linearly if you can — LP/MILP give global guarantees that NLP does not.

## Report the solver status honestly

- Always report **status**: optimal, infeasible, or unbounded. **A number from an infeasible or failed solve is not an answer** — if `success` is false, say the problem is infeasible/unbounded and help the user revisit the constraints, rather than presenting `optimal_value`.
- **Infeasible** means the constraints contradict (no solution satisfies them) — surface which constraints to relax. **Unbounded** means the objective can improve without limit — usually a missing constraint.

## Sensitivity and assumptions

- The optimum is conditional on the input numbers. Report **shadow prices / sensitivity** where available (`solve_lp` returns inequality marginals) — they tell you how the optimum responds to relaxing a constraint, often the most useful business insight.
- State the modeling assumptions plainly: it's a **deterministic** optimum given the inputs; uncertainty in those inputs is not captured unless explicitly modeled (stochastic/robust optimization is out of scope here).
- The recommendation is "optimal under this model," not "optimal in reality" — reality is only as well captured as the constraints.

## Scope

This covers deterministic LP, MILP, and NLP. Stochastic/robust optimization and large-scale specialized solvers are out of scope. With optimization done, the four modeling families on top of the modeling foundation are complete.
