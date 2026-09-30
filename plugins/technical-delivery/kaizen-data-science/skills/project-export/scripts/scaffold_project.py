"""Create the mandatory Kaizen Analytix data-science project structure.

The directory layout is fixed and may not be altered. Every folder is created even
when empty (preserved with a .gitkeep) so users can add files (e.g. visualizations)
later without breaking the convention. Idempotent: safe to re-run.
"""

import os
import textwrap

# (relative_path, is_dir)
DIRS = [
    "data", "data/external", "data/interim", "data/processed", "data/raw",
    "models", "notebooks", "scripts",
    "src", "src/data", "src/models", "src/visualization",
]


def _w(path, text):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def _gitkeep_if_empty(d):
    if os.path.isdir(d) and not any(
        n for n in os.listdir(d) if n != ".gitkeep"
    ):
        open(os.path.join(d, ".gitkeep"), "a").close()


def create_project(root, project_name="data-science-project", description="",
                   author="", license_holder="Kaizen Analytix LLC", year=2026):
    """Scaffold the full mandatory structure at `root`. Returns a summary dict."""
    os.makedirs(root, exist_ok=True)
    for d in DIRS:
        os.makedirs(os.path.join(root, d), exist_ok=True)

    # --- top-level files ---
    _w(os.path.join(root, "LICENSE"), textwrap.dedent(f"""\
        Copyright (c) {year} {license_holder}. All Rights Reserved.

        CONFIDENTIAL & PROPRIETARY.

        This project and all associated code, data, and documentation are the
        confidential and proprietary property of {license_holder}. Unauthorized
        copying, distribution, or use, in whole or in part, is prohibited without
        the express written permission of {license_holder}.
    """))

    _w(os.path.join(root, "README.md"), textwrap.dedent(f"""\
        # {project_name}

        {description or "Reproducible data-science project generated from an analysis session."}

        ## Reproducing the analysis

        ```bash
        python -m venv .venv && source .venv/bin/activate   # Windows: .venv\\Scripts\\activate
        pip install -r requirements.txt
        pip install -e .            # makes `src` importable
        jupyter notebook            # then open the notebook under notebooks/
        ```

        Run the notebook top to bottom to regenerate every reported value. The raw
        data in `data/raw/` is immutable; any transformed data is written to
        `data/interim/` or `data/processed/`.

        ## Structure

        See the project tree below; the layout is the mandatory Kaizen Analytix
        data-science structure and must not be altered. Empty folders are kept (via
        `.gitkeep`) so files can be added later without breaking the convention.

        ---
        (c) {year} {license_holder} | All Rights Reserved. CONFIDENTIAL & PROPRIETARY
    """))

    # `config` is a top-level FILE per the mandatory structure ("Project config file")
    _w(os.path.join(root, "config"), textwrap.dedent(f"""\
        # Project configuration
        project_name: {project_name}
        author: {author}
        paths:
          data_raw: data/raw
          data_interim: data/interim
          data_processed: data/processed
          models: models
        random_seed: 0
    """))

    if not os.path.exists(os.path.join(root, "requirements.txt")):
        _w(os.path.join(root, "requirements.txt"),
           "# Generated with: pip-chill > requirements.txt\n")

    _w(os.path.join(root, "setup.py"), textwrap.dedent(f"""\
        from setuptools import find_packages, setup

        setup(
            name="src",
            packages=find_packages(),
            version="0.1.0",
            description="{(description or project_name).replace(chr(34), '')}",
            author="{author or license_holder}",
        )
    """))

    _w(os.path.join(root, "src", "__init__.py"), "")
    for sub in ("data", "models", "visualization"):
        init = os.path.join(root, "src", sub, "__init__.py")
        if not os.path.exists(init):
            _w(init, "")

    # preserve empties
    for d in DIRS:
        _gitkeep_if_empty(os.path.join(root, d))

    return {"root": os.path.abspath(root),
            "dirs_created": [d for d in DIRS],
            "files_created": ["LICENSE", "README.md", "config", "requirements.txt",
                              "setup.py", "src/__init__.py"]}


if __name__ == "__main__":
    import sys
    r = sys.argv[1] if len(sys.argv) > 1 else "project"
    print(create_project(r, project_name=os.path.basename(os.path.abspath(r))))
