"""Google Colab UI layer: application shell and pages.

The UI is a consumer/editor of the canonical project model:

    UI  ->  ProjectController  ->  Project model / validation / serialization

No model or validation module imports anything from this package, and no
engineering state is kept in widget values.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Union

from ..app.project_controller import ProjectController
from ..models.enums import Direction
from ..version import APP_NAME
from .app_shell import NAVIGATION_TITLES, AppShell
from .infrastructure_page import InfrastructurePage
from .project_page import ProjectPage
from .rolling_stock_page import RollingStockPage
from .stations_page import StationsPage
from .validation_page import ValidationAuditPage

#: Navigation entries that are functional pages in this phase.
#: Everything else in :data:`~railway_headway_sim.ui.app_shell.NAVIGATION_TITLES`
#: is an explicit "planned for a later development phase" placeholder.
FUNCTIONAL_PAGES: tuple[str, ...] = (
    "Project",
    "Infrastructure",
    "Stations & Platforms",
    "Rolling Stock",
    "Validation & Audit",
)

__all__ = [
    "AppShell",
    "FUNCTIONAL_PAGES",
    "InfrastructurePage",
    "NAVIGATION_TITLES",
    "ProjectPage",
    "RollingStockPage",
    "StationsPage",
    "ValidationAuditPage",
    "launch_app",
]

#: Name of the static HTML snapshot written when ``embed=False``.
STATIC_SNAPSHOT_NAME = "railway_headway_sim_app.html"


def launch_app(
    controller: Optional[ProjectController] = None,
    *,
    embed: bool = True,
    snapshot_path: Optional[Union[str, Path]] = None,
    direction: Direction = Direction.FORWARD,
) -> AppShell:
    """Build (and display) the Phase-1 application in the current Colab output cell.

    Parameters
    ----------
    controller
        Optional pre-built controller (e.g. one that already holds a project).
        A controller with a new project template is created when omitted.
    embed
        ``True`` (default) displays the interactive application in the notebook
        output. ``False`` writes a static HTML snapshot instead - useful for
        documentation, but a snapshot cannot call back into the kernel.
    snapshot_path
        Where to write the snapshot when ``embed=False``.
    direction
        Initial application direction selection (FORWARD by default).

    Returns
    -------
    AppShell
        The shell object, exposing ``.widget``, ``.controller`` and
        ``.select_tab(name)`` for notebook/programmatic use.
    """
    if controller is None:
        controller = ProjectController.new_project(direction=direction)
    shell = AppShell(controller)

    if embed:
        from IPython.display import display

        display(shell.widget)
        return shell

    from ipywidgets.embed import embed_minimal_html

    target = Path(snapshot_path) if snapshot_path is not None else Path(STATIC_SNAPSHOT_NAME)
    embed_minimal_html(str(target), views=[shell.widget], title=APP_NAME)
    from IPython.display import display as _display

    _display(
        {
            "text/plain": (
                f"Static snapshot written to {target}. Interactive use requires embed=True "
                "(the widgets need the notebook kernel)."
            )
        }
    )
    return shell
