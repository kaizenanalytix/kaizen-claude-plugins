# Optimization Example

A worked example of the prescriptive, formulation-first workflow.

## Example user request

> I have 50 hours of labor and 18 units of material this week. Product A nets $3/unit and uses 1 hr + 3 material; Product B nets $5/unit and uses 2 hr + 2 material (material cap 18, and B's hours cap at 12). How many of each should I make?

## Expected module path

```
Analysis Planning
Optimization
Reporting
Verification Before Completion
```

(EDA/quality steps are light here — this is a decision problem, not a dataset analysis.)

## Expected behavior

1. **Formulate explicitly and confirm** — decision variables: x = units of A, y = units of B. Objective: maximize 3x + 5y. Constraints: x ≤ 4 (example capacity), 2y ≤ 12, 3x + 2y ≤ 18, x, y ≥ 0. Restate the formulation back to the user before solving — this is the modeling step, and a wrong constraint means a wrong answer.

2. **Choose the type** — all linear, continuous → **linear program** (`solve_lp`). If units had to be whole, it would be a MILP (`solve_milp`, integer variables).

3. **Solve** — `solve_lp(c=[3,5], A_ub=[[1,0],[0,2],[3,2]], b_ub=[4,12,18], maximize=True)` → x = 2, y = 6, **optimal profit = 36**, with status "optimal."

4. **Report with status and sensitivity** — state it's the global optimum for the LP; report shadow prices (which constraint is binding — here the material/limits), since "which constraint is holding you back" is usually the actionable insight. Note the optimum is deterministic given these numbers.

5. **Handle failure honestly** — if the constraints had been contradictory, the solver returns infeasible; in that case say so and help relax a constraint, rather than reporting a number.

6. **Verification** — solver status is "optimal" (not infeasible/unbounded); the reported solution satisfies every constraint; the formulation was confirmed; the result is framed as optimal-under-this-model, not optimal-in-reality.

## Key teaching points

- Optimization is prescriptive and formulation-first: confirm objective + variables + constraints before solving.
- LP/MILP give global optima; non-convex NLP gives only a local one — say which.
- Always report solver status; an infeasible/unbounded solve is not an answer. Shadow prices are often the real insight.

## Note on scope

This is the optimization family within the modeling skill.
