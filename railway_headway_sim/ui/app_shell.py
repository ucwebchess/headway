"""Google Colab application shell.

Layout of the shell::

    header           - application name, project name, versions, validation status
    direction control- prominent FORWARD / REVERSE selector (application state only)
    status bar       - last action message with explicit severity text
    navigation tabs  - Project | Infrastructure | ... | Validation & Audit
    footer           - versions, canonical hashes, freshness

Functional pages: ``Project``, ``Infrastructure`` (catalogue editors, topology
inspector and schematic), ``Stations & Platforms`` (station-side catalogue
editors, static footprint view and train-fit checker), ``Rolling Stock`` (the
read-only view of the loaded rolling-stock catalogue, Phase 6B) and
``Validation & Audit``. The six remaining pages stay explicit "planned for a
later development phase" placeholders.

The shell only renders controller state; it never computes engineering values.  It
also carries the STANDARD / ADVANCED editor-mode switch, which the two editor pages
share so that a single control decides how many columns their tables show.
"""

from __future__ import annotations

from typing import Callable, Optional

import ipywidgets as widgets

from ..app.project_controller import ProjectController
from ..models.enums import Direction, SELECTABLE_DIRECTIONS
from ..version import APP_NAME, APP_PHASE, APP_VERSION, DEFAULT_PROJECT_SCHEMA_VERSION
from . import formatting as fmt
from .infrastructure_page import InfrastructurePage
from .page_editors import EditorMode
from .placeholder_pages import PLANNED_PAGES, placeholder_widget
from .project_page import ProjectPage, panel_box
from .rolling_stock_page import RollingStockPage
from .stations_page import StationsPage
from .validation_page import ValidationAuditPage

#: Navigation order of the application shell.
NAVIGATION_TITLES: tuple[str, ...] = (
    "Project",
    "Infrastructure",
    "Stations & Platforms",
    "Signalling",
    "Rolling Stock",
    "Services & Timetable",
    "Simulation",
    "Results",
    "Scenarios",
    "Report",
    "Validation & Audit",
)

_QUICK_GUIDE_HTML = f"""
<details style="font-family:Helvetica,Arial,sans-serif;">
  <summary style="cursor:pointer;font-size:12px;color:{fmt.PALETTE['navy']};font-weight:700;">
    How to use this Phase-1 application (click to expand)
  </summary>
  <div style="font-size:12px;color:{fmt.PALETTE['ink']};margin-top:7px;line-height:1.5;">
    <ol style="margin:0 0 0 18px;padding:0;">
      <li><b>New Project</b> creates a minimal valid schema-1.0 project template.</li>
      <li>Edit <b>Project ID, Project Name, Description, Origin Name, End Name</b> and the
          <b>chainage start/end</b> values, then press <b>Save metadata</b>.</li>
      <li><b>Validate Project</b> runs the Phase-1 structural/basic semantic checks; open the
          <b>Validation &amp; Audit</b> tab for the diagnostic table, hashes and versions.</li>
      <li><b>Export JSON</b> writes the canonical project JSON and starts a Colab browser
          download. <b>Import JSON</b> reads a .json file selected in the upload widget.</li>
      <li>The <b>FORWARD / REVERSE</b> selector changes the application/run direction only. It
          never rewrites the stored project data - the project hash stays identical, and the
          previews simply follow the selected direction.</li>
      <li>The <b>STANDARD / ADVANCED</b> switch adds the optional/low-level columns to the
          editor tables; sub-tab selections are kept for the session.</li>
      <li><b>Infrastructure</b> has the sub-tabs <b>Line | Tracks | Geometry | Speed |
          Schematic</b>: the typed catalogues are edited in place, the topology inspector and
          the read-only Phase-2 tables stay available, and the schematic is generated from the
          loaded model and can jump to any object's row.</li>
      <li><b>Stations &amp; Platforms</b> has the sub-tabs <b>Stations | Platforms | Stopping
          Marks | Observation Points</b> with the static footprint view and the train-fit
          check (FIT / TOO_LONG / MARKER_OUTSIDE_USABLE).</li>
      <li><b>Rolling Stock</b> has the read-only sub-tabs <b>Overview | Traction | Resistance |
          Braking</b>: it shows the stock types of the loaded catalogue and the effort and
          running-resistance curves the physics package samples. Nothing on that page is
          editable and no train moves.</li>
      <li>Editing never writes to the project directly: every change is a <b>staged draft</b>
          (APP-EDIT-002) shown in the draft bar with the hash before/after. Commit replaces the
          project; discard leaves it untouched. An INVALID draft blocks commit and export.
          JSON import/export stays available and authoritative.</li>
    </ol>
    <div style="margin-top:6px;color:{fmt.PALETTE['muted']};">
      The application contains no train simulation, train dynamics, signalling, headway or
      capacity calculation. Pages for those functions state clearly that they are not
      implemented yet.
    </div>
  </div>
</details>
"""


class AppShell:
    """The Phase-1 Colab application shell."""

    def __init__(
        self,
        controller: Optional[ProjectController] = None,
        *,
        mode: Optional[EditorMode] = None,
    ) -> None:
        self._controller = controller if controller is not None else ProjectController.new_project()
        self._mode = mode if mode is not None else EditorMode()
        self._project_page = ProjectPage(self._controller)
        self._infrastructure_page = InfrastructurePage(self._controller, mode=self._mode)
        self._stations_page = StationsPage(self._controller, mode=self._mode)
        self._rolling_stock_page = RollingStockPage()
        self._audit_page = ValidationAuditPage(self._controller)
        self._unsubscribe: Optional[Callable[[], None]] = None
        self._build()
        self._unsubscribe = self._controller.subscribe(self.refresh)
        self.refresh()

    # -- construction ------------------------------------------------------
    def _build(self) -> None:
        self._header = widgets.HTML(value="")
        self._status_line = widgets.HTML(value="")
        self._direction_status = widgets.HTML(value="")

        self._forward_button = widgets.Button(
            description="FORWARD",
            button_style="info",
            layout=widgets.Layout(min_width="300px", height="42px", margin="0px 10px 6px 0px"),
            tooltip="Run/analysis direction FORWARD (increasing chainage).",
        )
        self._reverse_button = widgets.Button(
            description="REVERSE",
            button_style="",
            layout=widgets.Layout(min_width="300px", height="42px", margin="0px 10px 6px 0px"),
            tooltip="Run/analysis direction REVERSE (decreasing chainage).",
        )
        self._forward_button.on_click(lambda _b: self._controller.set_direction(Direction.FORWARD))
        self._reverse_button.on_click(lambda _b: self._controller.set_direction(Direction.REVERSE))

        direction_buttons = widgets.HBox(
            [self._forward_button, self._reverse_button],
            layout=widgets.Layout(flex_flow="row wrap"),
        )
        direction_panel = panel_box(
            "Simulation direction (application selection)",
            [direction_buttons, self._direction_status],
            subtitle="stored project data is not modified",
        )

        self._mode_toggle = self._mode.toggle_widget()
        self._mode_status = widgets.HTML(value="")
        mode_panel = panel_box(
            "Editor mode (STANDARD / ADVANCED)",
            [self._mode_toggle, self._mode_status],
            subtitle="one switch for every editor table on the Infrastructure and Stations pages",
        )

        # Build the navigation tabs in exactly the declared order.
        placeholder_by_title = {title: placeholder_widget(title) for title in PLANNED_PAGES}
        ordered_pages: list[widgets.Widget] = []
        for title in NAVIGATION_TITLES:
            if title == "Project":
                ordered_pages.append(self._project_page.widget)
            elif title == "Infrastructure":
                ordered_pages.append(self._infrastructure_page.widget)
            elif title == "Stations & Platforms":
                ordered_pages.append(self._stations_page.widget)
            elif title == "Rolling Stock":
                ordered_pages.append(self._rolling_stock_page.widget)
            elif title == "Validation & Audit":
                ordered_pages.append(self._audit_page.widget)
            else:
                ordered_pages.append(placeholder_by_title[title])
        self._tabs = widgets.Tab(children=ordered_pages)
        for index, title in enumerate(NAVIGATION_TITLES):
            self._tabs.set_title(index, title)

        self._footer = widgets.HTML(value="")
        guide_panel = panel_box("Quick guide", [widgets.HTML(_QUICK_GUIDE_HTML)])

        self._widget = widgets.VBox(
            [
                self._header,
                direction_panel,
                mode_panel,
                guide_panel,
                self._status_line,
                self._tabs,
                self._footer,
            ],
            layout=widgets.Layout(padding="6px", margin="0px"),
        )

    # -- rendering ---------------------------------------------------------
    def refresh(self) -> None:
        """Re-render every shell element from the current controller state."""
        state = self._controller.state
        project = self._controller.project
        direction = state.direction

        project_label = project.project.name if project is not None else "(no project loaded)"
        scope_text = state.assurance_scope or "SCOPE NOT DETERMINED"
        chips = [
            (f"APP v{APP_VERSION}", "navy"),
            (f"SCHEMA v{state.schema_version or DEFAULT_PROJECT_SCHEMA_VERSION}", "navy"),
            (scope_text, "steel"),
        ]
        status_text = state.validation_status or "NOT YET VALIDATED"
        self._header.value = fmt.header_html(
            app_name=APP_NAME,
            phase_text=APP_PHASE,
            project_name=project_label,
            chips=chips,
            status_text=f"VALIDATION: {status_text}",
            status_tone=fmt.tone_for_status(state.validation_status),
            freshness_text=state.freshness_text,
            freshness_tone="warn" if state.modified_since_validation else (
                "ok" if state.validation_status else "muted"
            ),
            direction_text=direction.value,
        )

        self._forward_button.description = ("▶ " if direction is Direction.FORWARD else "▷ ") + fmt.direction_label(
            project, Direction.FORWARD
        )
        self._reverse_button.description = ("▶ " if direction is Direction.REVERSE else "▷ ") + fmt.direction_label(
            project, Direction.REVERSE
        )
        self._forward_button.button_style = "info" if direction is Direction.FORWARD else ""
        self._reverse_button.button_style = "primary" if direction is Direction.REVERSE else ""
        self._direction_status.value = fmt.direction_bar_html(
            active_label=fmt.direction_label(project, direction),
            caption=fmt.direction_caption(project, direction),
            note=(
                "Changing this selector updates the application/run selection only - the stored "
                "project document (including all infrastructure containers) is never rewritten."
            ),
        )

        self._status_line.value = fmt.message_html(
            state.last_message or "Ready.", severity=state.last_message_severity
        )

        self._mode_status.value = fmt.section_note_html(
            f"Editor mode {self._mode.mode}: "
            + (
                "core engineering columns only."
                if self._mode.mode == "STANDARD"
                else "all editable columns, including optional/low-level ones."
            )
            + " Changing the mode re-renders the tables in place and discards no draft."
        )

        footer_rows = [
            ("App version", APP_VERSION),
            ("Schema version", state.schema_version or DEFAULT_PROJECT_SCHEMA_VERSION),
            ("Direction", direction.value),
            ("Freshness", state.freshness_text),
            ("Current hash", state.short_current_hash() or "(no project)"),
            ("Validated hash", state.short_validated_hash() or "(not validated yet)"),
            ("Selectable directions", " / ".join(d.value for d in SELECTABLE_DIRECTIONS)),
            ("Assurance scope", state.assurance_scope or "(not determined)"),
            ("Draft staged", "yes (blocks export)" if state.draft_blocks_export else ("yes" if state.draft_pending else "no")),
        ]
        self._footer.value = fmt.footer_html(footer_rows)

    @property
    def widget(self) -> widgets.Widget:
        """Return the root widget of the application shell."""
        return self._widget

    @property
    def controller(self) -> ProjectController:
        """Return the controller driving this shell."""
        return self._controller

    def select_tab(self, title: str) -> None:
        """Select a navigation tab by title (used by notebooks/tests)."""
        if title not in NAVIGATION_TITLES:
            raise KeyError(f"Unknown tab {title!r}; available: {list(NAVIGATION_TITLES)}")
        self._tabs.selected_index = list(NAVIGATION_TITLES).index(title)

    @property
    def editor_mode(self) -> EditorMode:
        """Return the STANDARD / ADVANCED switch shared with the editor pages."""
        return self._mode

    def set_editor_mode(self, mode: str) -> None:
        """Set the editor mode programmatically (used by notebooks/tests)."""
        self._mode.set_mode(mode)
