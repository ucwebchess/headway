"""Placeholder pages for navigation entries that belong to later phases.

These pages contain **no** engineering functionality, no fake calculations and no
placeholder result values. They state clearly what is not implemented yet.

Declared supersessions (``UI-REG-009``): ``Infrastructure`` and
``Stations & Platforms`` became functional pages in Phase 2
(:mod:`~railway_headway_sim.ui.infrastructure_page`,
:mod:`~railway_headway_sim.ui.stations_page`) and ``Rolling Stock`` became a
functional read-only page in Phase 6B
(:mod:`~railway_headway_sim.ui.rolling_stock_page`); none of them is listed here any
more, and the six entries below remain explicit placeholders. See
:data:`~railway_headway_sim.ui.FUNCTIONAL_PAGES`.
"""

from __future__ import annotations

import ipywidgets as widgets

from ..version import APP_PHASE
from . import formatting as fmt

#: Planned content per navigation entry (documentation of later phases only).
#: Six entries remain; ``Rolling Stock`` left this set in Phase 6B.
PLANNED_PAGES: dict[str, tuple[str, ...]] = {
    "Signalling": (
        "Signal positions, block sections and movement-authority concepts",
        "Route/resource locking concepts used by later blocking-time analysis",
        "Signalling rule-set configuration",
    ),
    "Services & Timetable": (
        "Service groups, stop patterns and train paths",
        "Timetable definitions and service-level parameters",
        "Service-level validation rules",
    ),
    "Simulation": (
        "Microscopic single-train and multi-train simulation configuration",
        "Time-stepping setup and random-seed handling",
        "Simulation run execution and progress reporting",
    ),
    "Results": (
        "Train trajectories, speed/energy profiles and blocking-time decompositions",
        "Technical headway and capacity results (H(i,j), UIC 406-style analysis)",
        "Sensitivity/Monte-Carlo result exploration",
    ),
    "Scenarios": (
        "Scenario definitions and scenario comparison",
        "Parameter variation sets",
        "Result comparison across scenarios",
    ),
    "Report": (
        "PDF engineering report generation",
        "Table/figure selection and report metadata",
        "Audit trail inclusion",
    ),
}


def placeholder_widget(title: str) -> widgets.HTML:
    """Build the placeholder page body for *title*."""
    items = PLANNED_PAGES.get(title, ("Content defined in a later development phase.",))
    return widgets.HTML(
        value=fmt.placeholder_html(title, items, phase_note=f"Not part of {APP_PHASE}."),
        layout=widgets.Layout(margin="8px 0px 0px 0px"),
    )


def build_placeholder_pages() -> dict[str, widgets.HTML]:
    """Return one placeholder widget per planned navigation entry."""
    return {title: placeholder_widget(title) for title in PLANNED_PAGES}
