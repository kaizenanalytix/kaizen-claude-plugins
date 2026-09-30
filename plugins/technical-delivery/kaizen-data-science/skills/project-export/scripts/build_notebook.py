"""Build a Jupyter notebook from an ordered list of cells, and execute it to verify
it runs and reproduces values. Keeps reproduction honest: the notebook must actually
run top to bottom.

Cell format: a list of dicts like
    {"cell_type": "markdown", "source": "## Heading\\nnarrative..."}
    {"cell_type": "code", "source": "import pandas as pd\\n..."}

Requires nbformat and nbclient (install on demand if missing).
"""

import os
import sys
import importlib
import subprocess


def _ensure(pkg, import_name=None):
    name = import_name or pkg
    try:
        return importlib.import_module(name)
    except Exception:
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", pkg,
                            "--break-system-packages", "-q"],
                           check=True, capture_output=True, timeout=900)
            return importlib.import_module(name)
        except Exception as e:
            raise RuntimeError(
                f"could not import or install {pkg} ({e}); notebook tooling unavailable "
                f"in this environment.")


def build_notebook(path, cells, kernel_name="python3"):
    """Write a valid .ipynb at `path` from the cell list. Does not execute."""
    nbf = _ensure("nbformat")
    nb = nbf.v4.new_notebook()
    nb.metadata["kernelspec"] = {"name": kernel_name, "display_name": "Python 3",
                                 "language": "python"}
    out = []
    for c in cells:
        t = c.get("cell_type", "code")
        src = c.get("source", "")
        out.append(nbf.v4.new_markdown_cell(src) if t == "markdown"
                   else nbf.v4.new_code_cell(src))
    nb.cells = out
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        nbf.write(nb, f)
    return {"path": os.path.abspath(path), "n_cells": len(out)}


def execute_notebook(path, timeout=900, kernel_name="python3"):
    """Execute the notebook in place (storing outputs). Returns run status + any error.

    A clean run with no errors is the verification that the notebook reproduces its
    values; reconcile the executed outputs against the reported numbers afterward.
    """
    nbf = _ensure("nbformat")
    _ensure("nbclient")
    from nbclient import NotebookClient
    from nbclient.exceptions import CellExecutionError
    nb = nbf.read(path, as_version=4)
    client = NotebookClient(nb, timeout=timeout, kernel_name=kernel_name,
                            resources={"metadata": {"path": os.path.dirname(os.path.abspath(path))}})
    try:
        client.execute()
        status = {"executed": True, "error": None}
    except CellExecutionError as e:
        status = {"executed": False, "error": str(e)[:500]}
    with open(path, "w", encoding="utf-8") as f:
        nbf.write(nb, f)
    return status


def build_and_verify(path, cells, timeout=900, kernel_name="python3"):
    build_notebook(path, cells, kernel_name)
    return execute_notebook(path, timeout, kernel_name)


if __name__ == "__main__":
    demo = [
        {"cell_type": "markdown", "source": "# Demo\nReproducibility check."},
        {"cell_type": "code", "source": "x = 2 + 2\nprint('x =', x)\nassert x == 4"},
    ]
    print(build_and_verify(sys.argv[1] if len(sys.argv) > 1 else "demo.ipynb", demo))
