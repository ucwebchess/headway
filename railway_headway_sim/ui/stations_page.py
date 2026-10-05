"""Stations & Platforms page (Phase 3): editable station-side catalogues + static footprint view.

Editing covers the four station-side catalogues (stations, platforms, stopping
marks, observation points) through the Phase-2 draft mechanism, exactly like the
Infrastructure page.  The Phase-2 inspection capability is kept in the same
sub-tabs:

* the station / platform / stopping-mark / observation tables (``_stations``,
  ``_platforms``, ``_marks``, ``_observations``);
* the static footprint evaluation (``_footprints``) computed by
  :func:`railway_headway_sim.infrastructure.static_geometry.compute_static_footprint`
  for a chosen static evaluation length, which is an *evaluation input* and never
  stored;
* the train-fit checker (FIT / TOO_LONG / MARKER_OUTSIDE_USABLE), which classifies
  the package-computed footprint without doing any geometry of its own.

Sub-tabs: **Stations | Platforms | Stopping Marks | Observation Points**.
No train dynamics (speed, acceleration, braking, occupation, headway) is computed
anywhere on this page.
"""

from __future__ import annotations

from typing import Any, Optional

import ipywidgets as widgets

from ..app.project_controller import ProjectController
from ..infrastructure import grr_fixtures
from ..models.enums import Severity
from . import formatting as fmt
from .editing import InfrastructureEditor
from .page_editors import (
    DraftStatusBar,
    EditorMode,
    StationsEditors,
    ValidationSummary,
)
from .project_page import panel_box

#: Header row of the station table.
STATION_HEADERS: tuple[str, ...] = ("Station", "Name", "Type", "Reference chainage", "Platforms")
#: Header row of the platform table.
PLATFORM_HEADERS: tuple[str, ...] = ("Platform", "Station", "Track", "Usable start", "Usable end", "Usable length")
#: Header row of the stopping-mark table.
MARK_HEADERS: tuple[str, ...] = ("Stopping mark", "Platform", "Track", "Position", "Direction")
#: Header row of the static footprint table.
FOOTPRINT_HEADERS: tuple[str, ...] = ("Stopping mark", "Front / rear", "Critical boundary", "Static fit")

#: Reference evaluation lengths offered by the page (fixture values, not project data).
REFERENCE_EVALUATION_LENGTHS: tuple[tuple[str, float], ...] = (
    (f"HSR reference ({grr_fixtures.HSR_REF_LENGTH_M:g} m)", grr_fixtures.HSR_REF_LENGTH_M),
    (f"REG reference ({grr_fixtures.REG_REF_LENGTH_M:g} m)", grr_fixtures.REG_REF_LENGTH_M),
)


class StationsPage:
    """Editable stations, platforms, stopping marks and observation points."""

    def __init__(
        self,
        controller: ProjectController,
        *,
        mode: Optional[EditorMode] = None,
    ) -> None:
        self._controller = controller
        self._unsubscribe: Optional[Any] = None
        self._mode = mode if mode is not None else EditorMode()
        self._build()
        self._unsubscribe = controller.subscribe(self.refresh)
        self.refresh()

    # -- construction ------------------------------------------------------
    def _build(self) -> None:
        self._notice = widgets.HTML(value="")
        self._editor = InfrastructureEditor(self._controller)
        self._draft_bar = DraftStatusBar(self._controller, self._editor)
        self._validation = ValidationSummary(
            self._controller, self._editor, on_focus=self.focus_object
        )

        self._stations = widgets.HTML(value="")
        self._platforms = widgets.HTML(value="")
        self._marks = widgets.HTML(value="")
        self._observations = widgets.HTML(value="")

        self._length_selector = widgets.Dropdown(
            options=[(label, value) for label, value in REFERENCE_EVALUATION_LENGTHS],
            value=grr_fixtures.HSR_REF_LENGTH_M,
            description="Evaluation length:",
            layout=widgets.Layout(width="420px"),
            tooltip=(
                "Static train length used for the static footprint evaluation. This is an "
                "evaluation input - it is never stored in the project document."
            ),
        )
        self._length_selector.observe(self._handle_length_change, names="value")
        self._footprints = widgets.HTML(value="")
        self._footprint_note = widgets.HTML(
            value=fmt.section_note_html(
                "Static geometry only: front/rear positions, track fit and usable-platform fit "
                "for a chosen static train length. No time, speed, acceleration, braking, "
                "occupation or headway is computed."
            )
        )

        self._editors = StationsEditors(
            self._controller,
            mode_provider=self._mode,
            on_status=self._set_status,
            extra_panels={
                "Stations": (
                    panel_box(
                        "Station catalogue (read-only table)",
                        [self._stations],
                        subtitle="stored values - edit them in the table above",
                    ),
                ),
                "Platforms": (
                    panel_box(
                        "Platform catalogue (read-only table)",
                        [self._platforms],
                        subtitle="usable range inside the track length",
                    ),
                ),
                "Stopping Marks": (
                    panel_box(
                        "Stopping marks (read-only table)",
                        [self._marks],
                        subtitle="authoritative location = track_id + position_m (chainage is derived)",
                    ),
                    panel_box(
                        "Static footprint evaluation",
                        [self._length_selector, self._footprints, self._footprint_note],
                        subtitle="Phase-2 static geometry check of the stopping marks",
                    ),
                ),
                "Observation Points": (
                    panel_box(
                        "Observation points (read-only table)",
                        [self._observations],
                        subtitle="static reference points used by later phases",
                    ),
                ),
            },
        )

        self._widget = widgets.VBox(
            [
                self._notice,
                self._draft_bar.widget,
                self._validation.widget,
                self._editors.widget,
            ],
            layout=widgets.Layout(margin="8px 0px 0px 0px"),
        )

    # -- event handlers ----------------------------------------------------
    def _set_status(self, message: str) -> None:
        """Publish an editor message into the shell status line."""
        self._controller.report_ui_message(message)

    def _handle_length_change(self, _change: dict[str, Any]) -> None:
        """Re-render the static footprint table and the train-fit check for the new length."""
        self._render_footprints()
        self._editors.train_fit.set_evaluation_length(float(self._length_selector.value))

    # -- focus routing -----------------------------------------------------
    def focus_object(self, object_id: str) -> bool:
        """Show the sub-tab and editor row that holds *object_id* (click-to-focus)."""
        return self._editors.focus(object_id)

    def select_sub_tab(self, title: str) -> bool:
        """Select an editor sub-tab by title (used by the shell and tests)."""
        return self._editors.host.select(title)

    def sub_tab_titles(self) -> tuple[str, ...]:
        """Return the editor sub-tab titles in display order."""
        return self._editors.host.titles()

    def selected_sub_tab(self) -> str:
        """Return the visible editor sub-tab title."""
        return self._editors.host.selected_title()

    def field_values(self) -> dict[str, Any]:
        """Return the current widget values of the striking page-level controls."""
        return {"evaluation_length_m": float(self._length_selector.value)}

    def fit_outcome(self) -> str:
        """Return the current train-fit outcome of the checker (FIT / TOO_LONG / ...)."""
        return self._editors.train_fit.outcome()

    # -- rendering ---------------------------------------------------------
    def refresh(self) -> None:
        """Re-render every panel from the current controller state."""
        physical = self._controller.is_physical_project
        if self._controller.project is None:
            self._notice.value = fmt.message_html("No project is loaded.", severity=Severity.INFO)
        elif physical:
            self._notice.value = fmt.message_html(
                "Typed station/platform data of the loaded physical project. Editing is staged "
                "as a draft (APP-EDIT-002); the committed project is only changed by Commit.",
                severity=Severity.INFO,
            )
        else:
            self._notice.value = fmt.message_html(
                "This project contains no typed physical infrastructure: station, platform and "
                "stopping-mark catalogues are available for physical projects only.",
                severity=Severity.WARNING,
            )

        self._stations.value = fmt.data_table_html(
            STATION_HEADERS, self._controller.station_rows(), empty_text="No typed stations."
        )
        self._platforms.value = fmt.data_table_html(
            PLATFORM_HEADERS, self._controller.platform_rows(), empty_text="No typed platforms."
        )
        self._marks.value = fmt.data_table_html(
            MARK_HEADERS, self._controller.stopping_mark_rows(), empty_text="No typed stopping marks."
        )
        self._observations.value = self._observations_html()
        self._render_footprints()
        self._editors.refresh()

    def _render_footprints(self) -> None:
        """Render the static footprint evaluation table."""
        physical = self._controller.is_physical_project
        if not physical:
            self._footprints.value = fmt.section_note_html(
                "The static footprint evaluation needs typed physical infrastructure."
            )
            return
        rows = self._controller.static_footprint_rows(float(self._length_selector.value))
        self._footprints.value = fmt.data_table_html(
            FOOTPRINT_HEADERS, rows, empty_text="No stopping marks to evaluate."
        )

    def _observations_html(self) -> str:
        """Render the observation point summary."""
        compiled = self._controller.compiled_infrastructure
        if compiled is None or not compiled.physical:
            return fmt.section_note_html("No typed observation points.")
        rows: list[tuple[str, str, str]] = []
        for observation in compiled.catalogue("observation_points"):
            detail = observation.type.value
            if getattr(observation, "station_id", None):
                detail += f", station {observation.station_id}"
            if getattr(observation, "event", None):
                detail += f", {observation.event.value}"
            if getattr(observation, "node_ids", None):
                detail += f", nodes {', '.join(observation.node_ids)}"
            member_count = len(getattr(observation, "members", []) or [])
            if member_count:
                detail += f", {member_count} track member(s)"
            rows.append((observation.id, observation.name or "", detail))
        return fmt.data_table_html(("Observation point", "Name", "Details"), rows)

    # -- accessors ---------------------------------------------------------
    @property
    def widget(self) -> widgets.Widget:
        """Return the root widget of this page."""
        return self._widget

    @property
    def editor(self) -> InfrastructureEditor:
        """Return the infrastructure editor used by this page."""
        return self._editor

    def editor_tables(self) -> dict[str, Any]:
        """Return the table editors of the page keyed by catalogue."""
        return self._editors.tables()

    def help_text(self) -> str:
        """Return a textual description of the page for the quick guide."""
        return (
            "Sub-tabs: "
            + ", ".join(self.sub_tab_titles())
            + ". The train-fit checker reports FIT / TOO_LONG / MARKER_OUTSIDE_USABLE."
        )
