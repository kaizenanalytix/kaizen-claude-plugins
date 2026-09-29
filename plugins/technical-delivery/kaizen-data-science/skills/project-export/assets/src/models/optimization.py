"""Optimization helpers: linear programming (LP), mixed-integer LP (MILP), and
non-linear programming (NLP). Engine is scipy.optimize (linprog/milp/minimize),
which is always available; PuLP is a nicer modeling layer if installed but not required.

Optimization is PRESCRIPTIVE — it finds the best decision given an objective and
constraints — not descriptive or predictive. It does not learn from data; data only
parameterizes the objective/constraints. Results are reported with the solver STATUS:
a number from an infeasible or failed solve is not an answer. LP/MILP return global
optima; non-convex NLP returns only a LOCAL optimum (flagged). Nothing here mutates input.
"""

import numpy as np

try:
    from scipy.optimize import linprog, milp, minimize, LinearConstraint, Bounds
    _HAS_SCIPY = True
except Exception:
    _HAS_SCIPY = False


def solve_lp(c, A_ub=None, b_ub=None, A_eq=None, b_eq=None, bounds=None, maximize=False):
    """Linear program. Minimizes c·x by default (set maximize=True to maximize).

    bounds: list of (low, high) per variable, None for +/-inf. Default x >= 0.
    """
    if not _HAS_SCIPY:
        return {"error": "scipy required"}
    c = np.asarray(c, float)
    obj = -c if maximize else c
    res = linprog(obj, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq,
                  bounds=bounds, method="highs")
    out = {"success": bool(res.success), "status": res.message,
           "solution": [round(float(v), 6) for v in res.x] if res.x is not None else None,
           "optimal_value": (round(float(-res.fun if maximize else res.fun), 6)
                             if res.fun is not None else None)}
    try:  # shadow prices (dual values) for inequality constraints, if present
        if res.success and getattr(res, "ineqlin", None) is not None:
            out["shadow_prices_ineq"] = [round(float(v), 6) for v in res.ineqlin.marginals]
    except Exception:
        pass
    out["note"] = ("global optimum for a linear program." if res.success else
                   "no optimal solution — check feasibility (infeasible) or whether the problem is unbounded.")
    return out


def solve_milp(c, integrality, A_ub=None, b_ub=None, A_eq=None, b_eq=None,
               bounds=None, maximize=False):
    """Mixed-integer linear program. `integrality`: per-variable 0 (continuous),
    1 (integer), or 2 (binary-ish via bounds). MILP is NP-hard — may be slow/large.
    """
    if not _HAS_SCIPY:
        return {"error": "scipy required"}
    c = np.asarray(c, float)
    obj = -c if maximize else c
    cons = []
    if A_ub is not None:
        A_ub = np.atleast_2d(A_ub)
        cons.append(LinearConstraint(A_ub, -np.inf, np.asarray(b_ub, float)))
    if A_eq is not None:
        A_eq = np.atleast_2d(A_eq)
        cons.append(LinearConstraint(A_eq, np.asarray(b_eq, float), np.asarray(b_eq, float)))
    if bounds is not None:
        lb = [(-np.inf if b[0] is None else b[0]) for b in bounds]
        ub = [(np.inf if b[1] is None else b[1]) for b in bounds]
        bnds = Bounds(lb, ub)
    else:
        bnds = Bounds(0, np.inf)
    res = milp(c=obj, constraints=cons if cons else None,
               integrality=np.asarray(integrality), bounds=bnds)
    ok = bool(res.success)
    return {"success": ok, "status": res.message,
            "solution": [round(float(v), 6) for v in res.x] if (ok and res.x is not None) else None,
            "optimal_value": (round(float(-res.fun if maximize else res.fun), 6)
                              if (ok and res.fun is not None) else None),
            "note": ("global optimum for the MILP." if ok else
                     "no optimal solution — likely infeasible or unbounded; check constraints.")}


def solve_nonlinear(objective, x0, bounds=None, constraints=None, maximize=False, n_restarts=1, seed=0):
    """Non-linear program via scipy.optimize.minimize. `objective` is a callable x->float;
    `constraints` are scipy-style dicts. Returns the best of n_restarts random starts.

    WARNING: for non-convex problems this finds a LOCAL optimum, not necessarily global.
    """
    if not _HAS_SCIPY:
        return {"error": "scipy required"}
    rng = np.random.default_rng(seed)
    x0 = np.asarray(x0, float)
    fun = (lambda x: -objective(x)) if maximize else (lambda x: objective(x))
    best = None
    for r in range(max(1, n_restarts)):
        start = x0 if r == 0 else x0 + rng.normal(0, 1, size=x0.shape)
        try:
            res = minimize(fun, start, method="SLSQP", bounds=bounds, constraints=constraints or ())
        except Exception:
            continue
        if res.success and (best is None or res.fun < best.fun):
            best = res
    if best is None:
        return {"success": False, "note": "no feasible/converged solution found; try different starts, bounds, or method."}
    val = float(-best.fun if maximize else best.fun)
    return {"success": True, "solution": [round(float(v), 6) for v in best.x],
            "optimal_value": round(val, 6), "n_restarts": n_restarts,
            "note": "LOCAL optimum (SLSQP). For non-convex problems use several restarts and treat as local unless convexity is established."}
