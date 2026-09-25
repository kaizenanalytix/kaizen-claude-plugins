"""kvprep -- the shared library behind the kvantum-data-prep skills.

Import it by adding the plugin's ``lib/`` directory to ``sys.path``::

    import sys; sys.path.insert(0, "<plugin>/lib")
    from kvprep import intake, reconcile, validate, template_fill, dashboard
    from kvprep.calendar_fiscal import build_445_calendar, disaggregate_monthly_to_weekly

Every function here is deterministic and testable, and none of them mutate the
file they were given. Transformations return a new frame plus a change log,
which is what makes a load auditable a quarter later.
"""

from . import (  # noqa: F401
    calendar_fiscal,
    config,
    dashboard,
    intake,
    lag,
    pipeline,
    reconcile,
    review,
    review_html,
    review_xlsx,
    template_fill,
    validate,
)

__all__ = [
    "calendar_fiscal",
    "config",
    "dashboard",
    "intake",
    "lag",
    "pipeline",
    "reconcile",
    "review",
    "review_html",
    "review_xlsx",
    "template_fill",
    "validate",
]
__version__ = "0.4.0"
