"""Infrastructure page (Phase 3): editable typed catalogues + validated inspection view.

The page is both an **editor** and the Phase-2 **inspector**.  Two rules shape it:

* every editor writes through the Phase-2 draft mechanism
  (``ProjectController.stage_draft`` + the ``APP-EDIT-002`` commit gate) - no widget
  ever writes to the committed project, and an INVALID draft blocks commit and export;
* every number shown is either **stored** (INPUT provenance) or produced by the
  package layer (DERIVED provenance: mapping, compiler, topology, preview series).
  The only derived values the UI itself may produce are the gradient between
  adjacent elevation points and the already-stored radius - both are drawn by
  :mod:`railway_headway_sim.ui.preview_panel` from
  :mod:`railway_headway_sim.infrastructure.preview_series`.

Sub-tabs: **Line | Tracks | Geometry | Speed | Schematic**.  The Phase-2 read-only
panels stay available in the same sub-tab as the catalogue they describe, so the
page keeps its inspection capability and its attribute contract
(``_inventory``, ``_overview``, ``_nodes``, ``_edges``, ``_speed``,
``_topology_summary``, ``_sequence_input``, ``_handle_sequence_check``,
``_sequence_result``).
"""

from __future__ import annotations

from typing import Any, Callable, Optional

import ipywidgets as widgets

from ..app.project_controller import ProjectController
from ..models.enums import Severity
from . import formatting as fmt
from .editing import InfrastructureEditor
from .page_editors import (
    DraftStatusBar,
    EditorMode,
    InfrastructureEditors,
    ProjectJsonPanel,
    ValidationSummary,
)
from .project_page import panel_box

#: Header row of the typed inventory table.
INVENTORY_HEADERS: tuple[str, ...] = ("Typed catalogue", "Objects")
#: Header row of the topology node table.
NODE_HEADERS: tuple[str, ...] = ("Node", "Type", "Chainage", "Station", "Degree")
#: Header row of the topology edge table.
EDGE_HEADERS: tuple[str, ...] = ("Track", "From node", "To node", "Length", "Group", "Chainage map")
#: Header row of the speed restriction table.
SPEED_HEADERS: tuple[str, ...] = ("Restriction", "Start km", "End km", "Speed km/h", "Direction", "Type")


class InfrastructurePage:
    """Infrastructure editors plus the typed inventory, registry and topology inspector."""

    def __init__(
        self,
        controller: ProjectController,
        *,
        mode: Optional[EditorMode] = None,
    ) -> None:
        self._controller = controller
        self._unsubscribe: Optional[Callable[[], None]] = None
        self._mode = mode if mode is not None else EditorMode()
        self._build()
        self._unsubscribe = controller.subscribe(self.refresh)
        self.refresh()

    # -- construction ------------------------------------------------------
    def _build(self) -> None:
        self._legacy_notice = widgets.HTML(value="")
        self._editor = InfrastructureEditor(self._controller)
        self._draft_bar = DraftStatusBar(self._controller, self._editor)
        self._validation = ValidationSummary(
            self._controller, self._editor, on_focus=self.focus_object
        )

        self._overview = widgets.HTML(value="")
        self._inventory = widgets.HTML(value="")
        self._registry = widgets.HTML(value="")
        self._alignment = widgets.HTML(value="")
        self._geometry = widgets.HTML(value="")
        self._speed = widgets.HTML(value="")
        self._topology_summary = widgets.HTML(value="")
        self._nodes = widgets.HTML(value="")
        self._edges = widgets.HTML(value="")

        self._sequence_input = widgets.Text(
            value="",
            placeholder="e.g. TR-C-E-X-U1, TR-O-CEN-VAL-ML1",
            description="Edge sequence:",
            layout=widgets.Layout(width="640px"),
            continuous_update=False,
            tooltip="Continuity check of a sequence of track edges (node identity only).",
        )
        self._sequence_button = widgets.Button(
            description="Check edge sequence",
            button_style="info",
            layout=widgets.Layout(width="180px", margin="0px 0px 0px 8px"),
        )
        self._sequence_button.on_click(self._handle_sequence_check)
        self._sequence_result = widgets.HTML(value="")
        self._sequence_row = widgets.HBox(
            [self._sequence_input, self._sequence_button],
            layout=widgets.Layout(align_items="center", flex_flow="row wrap"),
        )

        self._editors = InfrastructureEditors(
            self._controller,
            mode_provider=self._mode,
            on_status=self._set_status,
            extra_panels={
                "Line": (
                    panel_box(
                        "Alignment reference (read-only summary)",
                        [self._alignment],
                        subtitle="Phase-2 reference view - the editor above changes the stored catalogue",
                    ),
                ),
                "Tracks": (
                    panel_box("Nodes", [self._nodes], subtitle="typed topology nodes"),
                    panel_box("Tracks", [self._edges], subtitle="physical track edges"),
                    panel_box(
                        "Topology inspector",
                        [self._topology_summary, self._sequence_row, self._sequence_result],
                        subtitle="connectivity by node identity only - never by chainage equality",
                    ),
                ),
                "Geometry": (
                    panel_box(
                        "Geometry coverage (read-only summary)",
                        [self._geometry],
                        subtitle="Phase-2 view of the stored sections and profiles",
                    ),
                ),
                "Speed": (
                    panel_box(
                        "Stored speed restrictions (read-only table)",
                        [self._speed],
                        subtitle="exactly as stored - the preview above applies the direction filter",
                    ),
                ),
            },
        )
        self._json_panel = ProjectJsonPanel(
            self._controller, title="Project JSON (import / export)"
        )

        self._widget = widgets.VBox(
            [
                self._legacy_notice,
                self._draft_bar.widget,
                self._validation.widget,
                panel_box(
                    "Infrastructure overview",
                    [self._overview],
                    subtitle="layer contract: infrastructure is an array of layer objects",
                ),
                panel_box(
                    "Typed catalogue inventory",
                    [self._inventory],
                    subtitle="counts only - no engineering results",
                ),
                panel_box(
                    "Engineering registry (global ID uniqueness)",
                    [self._registry],
                    subtitle="all registered object IDs are unique across the whole project",
                ),
                self._editors.widget,
                self._json_panel.widget,
            ],
            layout=widgets.Layout(margin="8px 0px 0px 0px"),
        )

    # -- event handlers ----------------------------------------------------
    def _set_status(self, message: str) -> None:
        """Publish an editor message into the shell status line."""
        self._controller.report_ui_message(message)

    def _handle_sequence_check(self, _button: widgets.Button) -> None:
        """Run the package edge-sequence continuity check (no UI computation)."""
        compiled = self._controller.compiled_infrastructure
        if compiled is None or not compiled.physical:
            self._sequence_result.value = fmt.message_html(
                "No typed physical infrastructure is loaded.", severity=Severity.INFO
            )
            return
        raw = self._sequence_input.value or ""
        edge_ids = [part.strip() for part in raw.replace(";", ",").split(",") if part.strip()]
        topology = compiled.topology()
        check = topology.check_edge_sequence(edge_ids)
        self._sequence_result.value = fmt.message_html(
            check.describe(),
            severity=Severity.INFO if check.is_continuous else Severity.WARNING,
        )

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

    # -- rendering ---------------------------------------------------------
    def refresh(self) -> None:
        """Re-render every panel from the current controller state."""
        compiled = self._controller.compiled_infrastructure
        physical = bool(compiled is not None and compiled.physical)

        if compiled is None:
            self._legacy_notice.value = fmt.message_html(
                "No project is loaded.", severity=Severity.INFO
            )
        elif physical:
            self._legacy_notice.value = fmt.message_html(
                "This project declares typed physical infrastructure: the catalogues below are "
                "editable (staged drafts only, APP-EDIT-002) and are validated semantically. "
                "Phase-1 opaque records are preserved unchanged, and JSON import/export stays "
                "authoritative.",
                severity=Severity.INFO,
            )
        else:
            self._legacy_notice.value = fmt.message_html(
                "This project contains no typed physical infrastructure (Phase-1/legacy "
                "project): the opaque catalogues are preserved but not interpreted. Parse "
                "and validation reports are on the Validation & Audit page.",
                severity=Severity.WARNING,
            )

        self._overview.value = fmt.kv_table_html(self._controller.infrastructure_rows())
        self._inventory.value = fmt.summary_grid_html(
            self._controller.typed_inventory_rows(), columns=4
        ) if physical else fmt.section_note_html(
            "The typed catalogue inventory is available for physical projects only."
        )
        self._registry.value = (
            fmt.data_table_html(("Registered object type", "Count"), self._controller.registry_rows())
            if physical
            else fmt.section_note_html("No typed registry is available for this project.")
        )
        self._alignment.value = self._alignment_html()
        self._geometry.value = self._geometry_html()
        self._speed.value = self._speed_html()
        self._topology_summary.value = fmt.kv_table_html(self._controller.topology_summary_rows())
        self._nodes.value = fmt.data_table_html(
            NODE_HEADERS, self._controller.node_rows(), empty_text="No typed nodes."
        )
        self._edges.value = fmt.data_table_html(
            EDGE_HEADERS, self._controller.edge_rows(), empty_text="No typed track edges."
        )
        self._editors.refresh()

    # -- html fragments ----------------------------------------------------
    def _alignment_html(self) -> str:
        """Render the alignment summary (or an explicit note when absent)."""
        compiled = self._controller.compiled_infrastructure
        if compiled is None or not compiled.physical:
            return fmt.section_note_html("No typed alignment data.")
        alignments = compiled.catalogue("alignments")
        if not alignments:
            return fmt.section_note_html("No typed alignment data.")
        rows: list[tuple[str, Any]] = []
        for alignment in alignments:
            rows.append(("Alignment", f"{alignment.id} - {alignment.name or '(unnamed)'}"))
            rows.append(
                (
                    "Chainage range",
                    f"{alignment.start_chainage_km:g} - {alignment.end_chainage_km:g} km",
                )
            )
        for group in compiled.catalogue("track_groups"):
            rows.append(
                (
                    f"Track group {group.id}",
                    f"{group.name or '(unnamed)'} ({group.directionality.value}, normal "
                    f"{getattr(group.normal_direction, 'value', '-')})",
                )
            )
        return fmt.kv_table_html(rows)

    def _geometry_html(self) -> str:
        """Render the horizontal geometry / vertical profile coverage summary."""
        compiled = self._controller.compiled_infrastructure
        if compiled is None or not compiled.physical:
            return fmt.section_note_html("No typed geometry data.")
        sections = compiled.catalogue("horizontal_geometry")
        profiles = compiled.catalogue("vertical_profiles")
        rows: list[tuple[str, Any]] = []
        for section in sections:
            detail = section.type.value
            if section.type.value == "CURVE":
                detail = (
                    f"CURVE (radius {section.radius_m:g} m, "
                    f"{getattr(section.handedness, 'value', '-')})"
                )
            rows.append(
                (
                    section.id,
                    f"{section.start_chainage_km:g} - {section.end_chainage_km:g} km, {detail}",
                )
            )
        for profile in profiles:
            points = compiled.profile_point_pairs(profile.id)
            first = points[0][0] if points else None
            last = points[-1][0] if points else None
            rows.append(
                (
                    f"Profile {profile.id}",
                    f"{profile.source_mode.value}, {len(points)} point(s), "
                    + (
                        f"{first.chainage_km:g} km -> {last.chainage_km:g} km"
                        if first is not None and last is not None
                        else "no points"
                    ),
                )
            )
        return fmt.kv_table_html(rows)

    def _speed_html(self) -> str:
        """Render the speed restriction table."""
        compiled = self._controller.compiled_infrastructure
        if compiled is None or not compiled.physical:
            return fmt.section_note_html("No typed speed restrictions.")
        rows = [
            (
                restriction.id,
                f"{restriction.start_chainage_km:g}",
                f"{restriction.end_chainage_km:g}",
                f"{restriction.speed_kmh:g}",
                restriction.direction.value,
                restriction.type.value,
            )
            for restriction in compiled.catalogue("speed_restrictions")
        ]
        return fmt.data_table_html(SPEED_HEADERS, rows, empty_text="No typed speed restrictions.")

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
            + ". Every change is staged as a draft (APP-EDIT-002); JSON export stays authoritative."
        )
