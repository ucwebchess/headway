"""Editing panels shared by the Phase-3 pages (Line/Tracks/Geometry/Speed/Stations…).

Everything here is *presentation and orchestration*: the panels call the Phase-2
draft mechanism (:class:`~railway_headway_sim.ui.editing.InfrastructureEditor`,
which stages through ``ProjectController.stage_draft`` / ``APP-EDIT-002``) and the
package utilities that already exist.  No engineering value is computed in a
widget callback - the only derived numbers shown are the ones the package layer
produced (mapping, static footprints, preview series).

Panels
------
* :class:`EditorMode` - the STANDARD / ADVANCED switch shared by shell and pages;
* :class:`DraftStatusBar` - STAGED / COMMITTED / REJECTED plus hash before/after;
* :class:`ValidationSummary` - error/warning/info counts per reporting category
  with click-to-focus;
* :class:`ProjectJsonPanel` - JSON import/export (authoritative, draft aware);
* :class:`TrainFitChecker` - FIT / TOO_LONG / MARKER_OUTSIDE_USABLE;
* :class:`SubTabHost` - sub-tab container that keeps its selection for the session;
* :class:`InfrastructureEditors` / :class:`StationsEditors` - the two sub-tab sets.
"""

from __future__ import annotations

from typing import Any, Callable, Mapping, Optional, Sequence

import ipywidgets as widgets

from ..app.project_controller import ProjectController
from ..infrastructure import grr_fixtures
from ..infrastructure import preview_series as series
from ..infrastructure.static_geometry import compute_static_footprint, traversal_for_direction
from ..io.project_io import document_hash
from ..models.enums import Severity
from . import field_help
from . import formatting as fmt
from . import schematic_render
from .editing import (
    REFERENCE_SYSTEM_EDITABLE,
    REFERENCE_SYSTEM_FIXED,
    CatalogueEdit,
    InfrastructureEditor,
    Provenance,
    ScopedEditor,
)
from .editor_specs import ID_PREFIXES, FieldKind, fields_of, spec_of
from .preview_panel import GeometryPreview, SpeedPreview, preview_note
from .project_page import panel_box
from .table_editor import TableEditor

#: The two editor modes (STANDARD hides the advanced columns of every table).
STANDARD = "STANDARD"
ADVANCED = "ADVANCED"

#: Catalogue -> sub-tab title of the Infrastructure page.
INFRASTRUCTURE_TABS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Line", ("alignments",)),
    ("Tracks", ("track_groups", "nodes", "tracks")),
    ("Geometry", ("horizontal_geometry", "vertical_profiles", "vertical_profile_points")),
    ("Speed", ("speed_restrictions",)),
    ("Schematic", ()),
)

#: Catalogue -> sub-tab title of the Stations & Platforms page.
STATIONS_TABS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Stations", ("stations",)),
    ("Platforms", ("platforms",)),
    ("Stopping Marks", ("stopping_marks",)),
    ("Observation Points", ("observation_points",)),
)


class EditorMode:
    """The STANDARD / ADVANCED switch shared by the shell and the editor pages."""

    def __init__(self, mode: str = STANDARD) -> None:
        self._mode = mode if mode in (STANDARD, ADVANCED) else STANDARD
        self._listeners: list[Callable[[str], None]] = []

    @property
    def mode(self) -> str:
        """Return the current editor mode (the callable used as ``mode_provider``)."""
        return self._mode

    def __call__(self) -> str:
        """Return the current mode (so the object itself can be the provider)."""
        return self._mode

    def set_mode(self, mode: str) -> None:
        """Set the mode and notify every listener."""
        if mode not in (STANDARD, ADVANCED) or mode == self._mode:
            return
        self._mode = mode
        for listener in list(self._listeners):
            listener(self._mode)

    def subscribe(self, listener: Callable[[str], None]) -> Callable[[], None]:
        """Register a listener and return an unsubscribe callable."""
        self._listeners.append(listener)

        def _unsubscribe() -> None:
            if listener in self._listeners:
                self._listeners.remove(listener)

        return _unsubscribe

    def toggle_widget(self) -> widgets.Widget:
        """Return the toggle control used in the application header."""
        toggle = widgets.ToggleButtons(
            options=[STANDARD, ADVANCED],
            value=self._mode,
            description="Editor mode:",
            tooltips=[
                "STANDARD - core engineering fields of every catalogue.",
                "ADVANCED - additionally shows optional/low-level fields (no hidden behaviour).",
            ],
            layout=widgets.Layout(width="330px"),
        )
        toggle.observe(lambda change: self.set_mode(change["new"]), names="value")

        def _follow(mode: str) -> None:
            if toggle.value != mode:
                toggle.value = mode

        self.subscribe(_follow)
        return toggle


def catalogue_of_object(editor: InfrastructureEditor, object_id: str) -> str:
    """Return the catalogue that holds *object_id* (``''`` when it is not editable)."""
    from .editing import NESTED_CATALOGUES, editable_catalogues

    for catalogue in editable_catalogues():
        if catalogue in NESTED_CATALOGUES:
            owner_catalogue, field = NESTED_CATALOGUES[catalogue]
            for owner in editor.entries(owner_catalogue):
                for point in owner.get(field) or []:
                    if isinstance(point, dict) and point.get("id") == object_id:
                        return catalogue
            continue
        if object_id in editor.ids(catalogue):
            return catalogue
    return ""


class SubTabHost:
    """A sub-tab container that remembers its selection within the session."""

    def __init__(self, title: str, entries: Sequence[tuple[str, widgets.Widget]]) -> None:
        self._titles = tuple(name for name, _widget in entries)
        self._tabs = widgets.Tab(children=[widget for _name, widget in entries])
        for index, (name, _widget) in enumerate(entries):
            self._tabs.set_title(index, name)
        self._note = widgets.HTML(value="")
        self._widget = widgets.VBox([widgets.HTML(fmt.section_note_html(title)), self._tabs])

    @property
    def widget(self) -> widgets.Widget:
        """Return the root widget of the host."""
        return self._widget

    @property
    def tabs(self) -> widgets.Tab:
        """Return the underlying ``widgets.Tab``."""
        return self._tabs

    def titles(self) -> tuple[str, ...]:
        """Return the sub-tab titles."""
        return self._titles

    def selected_title(self) -> str:
        """Return the title of the visible sub-tab."""
        index = self._tabs.selected_index
        if index is None or index < 0 or index >= len(self._titles):
            return self._titles[0] if self._titles else ""
        return self._titles[index]

    def select(self, title: str) -> bool:
        """Show the sub-tab *title*; returns ``False`` when the title is unknown."""
        if title not in self._titles:
            return False
        self._tabs.selected_index = self._titles.index(title)
        return True

    def index_of(self, title: str) -> int:
        """Return the index of a sub-tab title (``-1`` when unknown)."""
        return self._titles.index(title) if title in self._titles else -1


class DraftStatusBar:
    """Draft status of the editors: status, reason, hash before/after, commit actions."""

    def __init__(self, controller: ProjectController, editor: InfrastructureEditor) -> None:
        self._controller = controller
        self._editor = editor
        self._status = widgets.HTML(value="")
        self._detail = widgets.HTML(value="")
        self._commit = widgets.Button(
            description="Commit draft",
            button_style="success",
            layout=widgets.Layout(width="150px"),
            tooltip="Validate and commit the staged draft (APP-EDIT-002 gate).",
        )
        self._discard = widgets.Button(
            description="Discard draft",
            button_style="warning",
            layout=widgets.Layout(width="150px"),
            tooltip="Throw the staged draft away and keep the committed project.",
        )
        self._commit.on_click(self._handle_commit)
        self._discard.on_click(self._handle_discard)
        self._widget = panel_box(
            "Draft status (APP-EDIT-002)",
            [
                self._status,
                widgets.HBox([self._commit, self._discard]),
                self._detail,
            ],
            subtitle="no editor writes to the committed project directly",
        )
        self._unsubscribe = controller.subscribe(self.refresh)
        self.refresh()

    @property
    def widget(self) -> widgets.Widget:
        """Return the root widget of the status bar."""
        return self._widget

    def hash_before(self) -> str:
        """Return the short hash of the committed project."""
        value = self._controller.current_project_hash or ""
        return value[:16] if value else "(none)"

    def hash_after(self) -> str:
        """Return the short hash of the staged draft (empty when nothing is staged)."""
        staged = getattr(self._controller, "_draft_document", None)
        if not isinstance(staged, dict):
            return ""
        return document_hash(staged)[:16]

    def status_text(self) -> str:
        """Return the STAGED / COMMITTED / REJECTED status word."""
        state = self._controller.state
        if not state.draft_pending:
            return "COMMITTED"
        status = (state.draft_status or "UNKNOWN").upper()
        return "REJECTED" if status == "INVALID" else "STAGED"

    def _handle_commit(self, _button: widgets.Button) -> None:
        """Commit the staged draft through the Phase-2 gate."""
        self._editor.commit_and_report()
        self.refresh()

    def _handle_discard(self, _button: widgets.Button) -> None:
        """Discard the staged draft (the project is untouched)."""
        self._editor.discard_and_report()
        self.refresh()

    def refresh(self) -> None:
        """Re-render the status line, the reason and the hash before/after."""
        state = self._controller.state
        status = self.status_text()
        severity = {
            "COMMITTED": Severity.INFO,
            "STAGED": Severity.INFO,
            "REJECTED": Severity.ERROR,
        }[status]
        reason = ""
        if status == "REJECTED":
            reason = " reason APP-EDIT-002: the staged draft is INVALID (commit and export blocked)."
        elif status == "STAGED":
            reason = f" draft status {state.draft_status or 'UNKNOWN'}."
        self._status.value = fmt.message_html(
            f"{status} - {self._editor.pending_change_count()} pending change(s) in the draft."
            f"{reason}",
            severity=severity,
        )
        after = self.hash_after()
        rows = [
            ("Hash before (committed)", self.hash_before()),
            ("Hash after (staged draft)", after or "(no draft staged)"),
            ("Export allowed", "no - INVALID draft staged (APP-EDIT-002)"
             if self._controller.draft_blocks_export else "yes"),
        ]
        self._detail.value = fmt.kv_table_html(rows) + fmt.section_note_html(
            "Committing re-validates the whole document and replaces the project; discarding "
            "restores the committed project byte-for-byte."
        )
        self._commit.disabled = not state.draft_pending
        self._discard.disabled = not state.draft_pending


class ValidationSummary:
    """Error / warning / info counts per reporting category, with click-to-focus."""

    def __init__(
        self,
        controller: ProjectController,
        editor: InfrastructureEditor,
        *,
        on_focus: Optional[Callable[[str], None]] = None,
    ) -> None:
        self._controller = controller
        self._editor = editor
        self._on_focus = on_focus
        self._counts = widgets.HTML(value="")
        self._headline = widgets.HTML(value="")
        self._targets = widgets.Select(options=[], rows=6, layout=widgets.Layout(width="340px"))
        self._focus_button = widgets.Button(
            description="Focus object", layout=widgets.Layout(width="140px")
        )
        self._focus_button.on_click(self._handle_focus)
        self._detail = widgets.HTML(value="")
        self._widget = panel_box(
            "Validation summary",
            [
                self._headline,
                self._counts,
                widgets.HBox([self._targets, self._focus_button]),
                self._detail,
            ],
            subtitle="counts by schema / geometry / topology / operations - reused Phase-1/2 codes",
        )
        self._unsubscribe = controller.subscribe(self.refresh)
        self.refresh()

    @property
    def widget(self) -> widgets.Widget:
        """Return the root widget of the summary."""
        return self._widget

    def source_label(self) -> str:
        """Return whether the counts describe the draft or the committed project."""
        return "staged draft" if self._controller.draft_pending else "committed project"

    def _handle_focus(self, _button: widgets.Button) -> None:
        """Focus the selected object in its editor."""
        if self._on_focus is not None and self._targets.value:
            self._on_focus(str(self._targets.value))

    def refresh(self) -> None:
        """Re-render the summary from the active validation result."""
        result = (
            self._controller.draft_result
            if self._controller.draft_pending
            else self._controller.validation
        )
        buckets = self._editor.diagnostics_by_category()
        self._headline.value = fmt.message_html(
            (
                f"{self.source_label()}: "
                + (result.summary_with_scope() if result is not None else "not validated yet")
            ),
            severity=(
                Severity.ERROR
                if result is not None and result.has_errors()
                else Severity.WARNING
                if result is not None and result.has_warnings()
                else Severity.INFO
            ),
        )
        rows = [
            (
                f"{name.title()}",
                f"{values['errors']} error(s), {values['warnings']} warning(s), "
                f"{values['info']} info",
            )
            for name, values in buckets.items()
        ]
        self._counts.value = fmt.kv_table_html(rows)

        options: list[tuple[str, str]] = []
        detail_rows: list[tuple[str, str, str, str, str]] = []
        diagnostics = result.diagnostics if result is not None else []
        for diagnostic in diagnostics:
            severity = str(getattr(diagnostic.severity, "value", diagnostic.severity))
            category = str(getattr(diagnostic.category, "value", diagnostic.category))
            object_id = diagnostic.object_id or ""
            detail_rows.append(
                (
                    severity,
                    category,
                    diagnostic.code,
                    object_id or "(project)",
                    diagnostic.message[:90],
                )
            )
            if object_id:
                options.append((f"{severity} {diagnostic.code} {object_id}", object_id))
        seen: set[str] = set()
        unique: list[tuple[str, str]] = []
        for label, value in options:
            if value in seen:
                continue
            seen.add(value)
            unique.append((label, value))
        self._targets.options = unique
        self._detail.value = fmt.data_table_html(
            ("Severity", "Category", "Code", "Object", "Message"),
            detail_rows,
            empty_text="No diagnostics: the active document is clean.",
        )


class ProjectJsonPanel:
    """JSON import/export panel (authoritative; blocked while an INVALID draft is staged)."""

    def __init__(self, controller: ProjectController, *, title: str = "Project JSON") -> None:
        self._controller = controller
        self._upload = widgets.FileUpload(
            accept=".json",
            multiple=False,
            description="Choose JSON",
            layout=widgets.Layout(width="240px"),
            tooltip="Upload a project JSON document. The uploaded file is treated as data only.",
        )
        self._import_button = widgets.Button(
            description="Import", button_style="info", layout=widgets.Layout(width="110px")
        )
        self._export_button = widgets.Button(
            description="Export", button_style="success", layout=widgets.Layout(width="110px")
        )
        self._import_button.on_click(self._handle_import)
        self._export_button.on_click(self._handle_export)
        self._message = widgets.HTML(value="")
        self._widget = panel_box(
            title,
            [
                widgets.HBox([self._upload, self._import_button, self._export_button]),
                self._message,
            ],
            subtitle="import/export stay available - they are never replaced by the editors",
        )
        self._unsubscribe = controller.subscribe(self.refresh)
        self.refresh()

    @property
    def widget(self) -> widgets.Widget:
        """Return the root widget of the panel."""
        return self._widget

    def _handle_import(self, _button: widgets.Button) -> None:
        """Import the uploaded JSON through the Phase-2 controller path."""
        self._controller.import_json_upload(self._upload.value)
        try:
            self._upload.value = ()
        except Exception:  # pragma: no cover - older ipywidgets clear differently
            self._upload.value = {}
        self.refresh()

    def _handle_export(self, _button: widgets.Button) -> None:
        """Export the committed project (refused while an INVALID draft is staged)."""
        self._controller.export_json()
        self.refresh()

    def refresh(self) -> None:
        """Show the last import/export message and the export gate."""
        state = self._controller.state
        blocked = self._controller.draft_blocks_export
        severity = Severity.ERROR if blocked else Severity.INFO
        message = state.last_message or "No import or export has been run yet."
        if blocked:
            message = (
                "Export is blocked while the staged draft is INVALID "
                "(commit or discard it first). " + message
            )
        self._message.value = fmt.message_html(message, severity=severity)
        self._export_button.disabled = self._controller.project is None or blocked


class TrainFitChecker:
    """Stopping-mark fit checker: FIT / TOO_LONG / MARKER_OUTSIDE_USABLE."""

    def __init__(self, controller: ProjectController) -> None:
        self._controller = controller
        self._marker = widgets.Dropdown(
            options=[],
            description="Stopping mark:",
            layout=widgets.Layout(width="420px"),
            tooltip="Stopping mark whose stored position is checked. Nothing is written to the project.",
        )
        self._length = widgets.FloatText(
            value=float(grr_fixtures.HSR_REF_LENGTH_M),
            description="Train length [m]:",
            layout=widgets.Layout(width="260px"),
            continuous_update=False,
            tooltip=(
                "Static evaluation length (fixtures/reference values). An evaluation input: it is "
                "never stored in the project document and no dynamics are computed."
            ),
        )
        self._check = widgets.Button(
            description="Check fit", button_style="info", layout=widgets.Layout(width="130px")
        )
        self._check.on_click(self._handle_check)
        self._result = widgets.HTML(value="")
        self._detail = widgets.HTML(value="")
        self._widget = panel_box(
            "Train-fit / rear-clearance check",
            [
                widgets.HBox([self._marker, self._length, self._check]),
                self._result,
                self._detail,
            ],
            subtitle="static geometry from the Phase-2 utility - no dynamics, no new code",
        )
        self._unsubscribe = controller.subscribe(self.refresh)
        self.refresh()

    @property
    def widget(self) -> widgets.Widget:
        """Return the root widget of the checker."""
        return self._widget

    def set_evaluation_length(self, length_m: float) -> None:
        """Set the static evaluation length and re-run the check (never stored)."""
        self._length.value = float(length_m)
        self.refresh()

    def evaluation_length(self) -> float:
        """Return the static evaluation length currently used (metres)."""
        return float(self._length.value)

    def outcome(self) -> str:
        """Return the classification of the current selection (``''`` when not evaluable)."""
        footprint = self._evaluate()
        if footprint is None:
            return ""
        return series.train_fit_outcome(footprint)

    def _evaluate(self) -> Any:
        """Return the package-computed static footprint of the current selection."""
        compiled = self._controller.compiled_infrastructure
        if compiled is None or not compiled.physical or not self._marker.value:
            return None
        marks = {mark.id: mark for mark in compiled.catalogue("stopping_marks")}
        mark = marks.get(str(self._marker.value))
        if mark is None:
            return None
        track = compiled.by_id("tracks").get(mark.track_id)
        if track is None:
            return None
        platform = None
        if getattr(mark, "platform_id", None):
            platform = compiled.by_id("platforms").get(mark.platform_id)
        length = float(self._length.value)
        if length <= 0:
            return None
        return compute_static_footprint(
            track, mark, length, traversal_for_direction(mark.direction), platform=platform
        )

    def _handle_check(self, _button: widgets.Button) -> None:
        """Run the check and render the outcome."""
        self.refresh(force=True)

    def refresh(self, *, force: bool = False) -> None:
        """Refresh the marker list and (re-)render the current outcome."""
        del force
        compiled = self._controller.compiled_infrastructure
        marks = (
            [mark.id for mark in compiled.catalogue("stopping_marks")]
            if compiled is not None and compiled.physical
            else []
        )
        self._marker.options = marks
        if marks and not self._marker.value:
            self._marker.value = marks[0]
        if not marks:
            self._result.value = fmt.message_html(
                "No typed stopping marks are available in this project.", severity=Severity.INFO
            )
            self._detail.value = ""
            return
        footprint = self._evaluate()
        if footprint is None:
            self._result.value = fmt.message_html(
                "The check needs a positive train length and resolvable references.",
                severity=Severity.WARNING,
            )
            self._detail.value = ""
            return
        outcome = series.train_fit_outcome(footprint)
        severity = {
            series.FIT: Severity.INFO,
            series.TOO_LONG: Severity.WARNING,
            series.MARKER_OUTSIDE_USABLE: Severity.ERROR,
        }[outcome]
        self._result.value = fmt.message_html(outcome, severity=severity)
        rows = [
            ("Outcome", outcome),
            ("Train length [m]", f"{footprint.train_length_m:g}"),
            ("Traversal", footprint.traversal.value),
            ("Front position [m]", f"{footprint.front_position_m:g}"),
            ("Rear position [m]", f"{footprint.rear_position_m:g}"),
            ("Fits in track", "yes" if footprint.fit_in_track else "no"),
            ("Fits in usable platform range", "yes" if footprint.fit_in_usable_platform else "no"),
            (
                "Critical boundary [m]",
                "-" if footprint.critical_boundary_m is None else f"{footprint.critical_boundary_m:g}",
            ),
            ("Rear clearance [m]", f"{footprint.rear_clearance_m:g}"),
            ("Rear infringement [m]", f"{footprint.rear_infringement_m:g}"),
        ]
        self._detail.value = (
            fmt.kv_table_html(rows)
            + fmt.section_note_html(footprint.describe())
            + (
                fmt.section_note_html("Notes: " + "; ".join(footprint.notes))
                if footprint.notes
                else ""
            )
        )


class NestedCataloguePanel:
    """Editor for a catalogue stored inside an owner (vertical profile points)."""

    def __init__(
        self,
        controller: ProjectController,
        *,
        catalogue: str,
        owner_catalogue: str,
        title: str,
        subtitle: str = "",
        mode_provider: Optional[Callable[[], str]] = None,
        on_status: Optional[Callable[[str], None]] = None,
        on_focus: Optional[Callable[[str], None]] = None,
    ) -> None:
        self._controller = controller
        self._catalogue = catalogue
        self._owner_catalogue = owner_catalogue
        self._mode_provider = mode_provider
        self._on_status = on_status
        self._on_focus = on_focus
        self._owner = widgets.Dropdown(
            options=[], description=f"{owner_catalogue[:-1].title()}:",
            layout=widgets.Layout(width="320px"),
            tooltip="Owning object whose nested entries are edited.",
        )
        self._owner.observe(lambda change: self._rebuild(), names="value")
        self._host = widgets.VBox([])
        self._tables: dict[str, TableEditor] = {}
        self._widget = panel_box(
            title, [self._owner, self._host], subtitle=subtitle
        )
        self._unsubscribe = controller.subscribe(self.refresh)
        self.refresh()

    @property
    def widget(self) -> widgets.Widget:
        """Return the root widget of the panel."""
        return self._widget

    def owner_id(self) -> str:
        """Return the id of the selected owner object."""
        return str(self._owner.value or "")

    def table(self) -> Optional[TableEditor]:
        """Return the table editor of the selected owner (``None`` when absent)."""
        return self._tables.get(self.owner_id())

    def tables(self) -> dict[str, TableEditor]:
        """Return the table editor of every owner that has been shown (keyed by owner id)."""
        return dict(self._tables)

    def current_entries(self) -> tuple[dict[str, Any], ...]:
        """Return the nested entries of the selected owner."""
        editor = ScopedEditor(self._controller, catalogue=self._catalogue, owner_id=self.owner_id())
        return tuple(editor.entries(self._catalogue))

    def refresh(self) -> None:
        """Refresh the owner list without losing the current selection."""
        base = InfrastructureEditor(self._controller)
        try:
            owners = base.ids(self._owner_catalogue)
        except (KeyError, ValueError):  # pragma: no cover - defensive
            owners = ()
        self._owner.options = owners
        if owners and self._owner.value not in owners:
            self._owner.value = owners[0]
        if not owners:
            self._host.children = [
                widgets.HTML(
                    fmt.message_html(
                        f"No {self._owner_catalogue} object exists to hold these entries.",
                        severity=Severity.WARNING,
                    )
                )
            ]
            return
        self._rebuild()

    def _rebuild(self) -> None:
        """Build (or rebuild) the table editor of the selected owner."""
        owner_id = self.owner_id()
        table = self._tables.get(owner_id)
        if table is None:
            scoped = ScopedEditor(
                self._controller, catalogue=self._catalogue, owner_id=owner_id
            )
            table = TableEditor(
                self._controller,
                self._catalogue,
                editor=scoped,
                mode_provider=self._mode_provider,
                on_status=self._on_status,
                on_focus=self._on_focus,
            )
            self._tables[owner_id] = table
        else:
            table.refresh()
        note = widgets.HTML(
            fmt.section_note_html(
                f"Entries are nested inside {owner_id} (document path "
                f"infrastructure[0].{self._owner_catalogue}[i].points); the draft mechanism and "
                "validation are the same as for a top-level catalogue."
            )
        )
        self._host.children = [note, table.widget]


class ReferenceSystemEditor:
    """Editor for the ``reference_system`` section (Line sub-tab)."""

    def __init__(
        self,
        controller: ProjectController,
        editor: InfrastructureEditor,
        *,
        on_status: Optional[Callable[[str], None]] = None,
    ) -> None:
        self._controller = controller
        self._editor = editor
        self._on_status = on_status
        self._controls: dict[str, widgets.Widget] = {}
        rows: list[widgets.Widget] = []
        for field_name in REFERENCE_SYSTEM_EDITABLE:
            spec = _reference_spec(field_name)
            value = editor.reference_value(field_name)
            widget = _reference_widget(field_name, spec, value, editor)
            widget.observe(
                lambda change, name=field_name: self._handle_change(name, change), names="value"
            )
            self._controls[field_name] = widget
            rows.append(
                widgets.VBox(
                    [
                        widgets.HTML(
                            f'<div style="font-size:11px;color:{fmt.PALETTE["navy"]};font-weight:700;" '
                            f'title="{fmt.esc(field_help.reference_system_tooltip(field_name))}">'
                            f"{fmt.esc(field_name)} {fmt.esc(spec.unit)}</div>"
                        ),
                        widget,
                        widgets.HTML(
                            f'<div style="font-size:9px;color:{fmt.PALETTE["muted"]};">'
                            '<span style="border:1px solid '
                            f'{fmt.TONE_COLOURS["ok"]};border-radius:3px;padding:0 3px;">'
                            f"{Provenance.INPUT.value}</span> "
                            f"{fmt.esc(field_help.reference_system_tooltip(field_name))}</div>"
                        ),
                    ],
                    layout=widgets.Layout(width="290px"),
                )
            )
        fixed_rows = [
            (
                field_name,
                f"{editor.reference_value(field_name)} (SCHEMA-FIXED - not editable)",
            )
            for field_name in REFERENCE_SYSTEM_FIXED
        ]
        self._message = widgets.HTML(value="")
        self._widget = panel_box(
            "Reference system",
            [
                widgets.HBox(rows, layout=widgets.Layout(flex_flow="row wrap")),
                widgets.HTML(fmt.kv_table_html(fixed_rows)),
                self._message,
            ],
            subtitle="chainage/alignment reference of the project (project section, Line level)",
        )
        self._unsubscribe = controller.subscribe(self.refresh)
        self.refresh()

    @property
    def widget(self) -> widgets.Widget:
        """Return the root widget of the editor."""
        return self._widget

    def _handle_change(self, field_name: str, change: dict[str, Any]) -> None:
        """Stage one reference-system field change."""
        current = self._editor.reference_value(field_name)
        value = change.get("new")
        if isinstance(current, (int, float)) and not isinstance(current, bool):
            try:
                value = float(value)
            except (TypeError, ValueError):
                return
        if value == current:
            return
        outcome: CatalogueEdit = self._editor.stage_reference_field(field_name, value)
        self._message.value = fmt.message_html(
            outcome.message, severity=Severity.INFO if outcome.ok else Severity.ERROR
        )
        if self._on_status is not None:
            self._on_status(outcome.message)

    def refresh(self) -> None:
        """Re-render the controls from the working document."""
        for field_name, widget in self._controls.items():
            value = self._editor.reference_value(field_name)
            if isinstance(widget, widgets.Dropdown):
                text = "" if value is None else str(getattr(value, "value", value))
                if text not in [str(option) for option in widget.options]:
                    widget.options = (*widget.options, text)
                widget.value = text
            elif isinstance(widget, widgets.FloatText):
                widget.value = float(value) if isinstance(value, (int, float)) else 0.0
            else:
                widget.value = "" if value is None else str(value)


def _reference_spec(field_name: str) -> Any:
    """Return a field specification for a reference-system field."""
    from .editor_specs import FieldSpec
    from ..models import enums as model_enums

    kinds = {
        "alignment_id": (FieldKind.REFERENCE, "alignments"),
        "chainage_start_km": (FieldKind.NUMBER, None),
        "chainage_end_km": (FieldKind.NUMBER, None),
        "chainage_origin_name": (FieldKind.TEXT, None),
        "chainage_end_name": (FieldKind.TEXT, None),
        "projection": (FieldKind.ENUM, model_enums.ProjectionType),
        "coordinate_system": (FieldKind.TEXT, None),
        "datum": (FieldKind.TEXT, None),
        "curve_radius_convention": (FieldKind.ENUM, model_enums.CurveRadiusConvention),
    }
    kind, target = kinds[field_name]
    return FieldSpec(
        name=field_name,
        catalogue="reference_system",
        kind=kind,
        reference=target if kind is FieldKind.REFERENCE else None,
        enum=target if kind is FieldKind.ENUM else None,
        optional=True,
    )


def _reference_widget(
    field_name: str, spec: Any, value: Any, editor: InfrastructureEditor
) -> widgets.Widget:
    """Build the widget of one reference-system field."""
    if spec.kind is FieldKind.REFERENCE:
        options = [""] + list(editor.ids("alignments"))
        current = "" if value is None else str(value)
        if current and current not in options:
            options.append(current)
        return widgets.Dropdown(options=options, value=current, layout=widgets.Layout(width="100%"),
                                tooltip=field_help.reference_system_tooltip(field_name))
    if spec.kind is FieldKind.NUMBER:
        return widgets.FloatText(
            value=float(value) if isinstance(value, (int, float)) else 0.0,
            layout=widgets.Layout(width="100%"),
            continuous_update=False,
            tooltip=field_help.reference_system_tooltip(field_name),
        )
    if spec.kind is FieldKind.ENUM:
        choices = [""] + list(spec.enum_values)
        current = "" if value is None else str(getattr(value, "value", value))
        if current and current not in choices:
            choices.append(current)
        return widgets.Dropdown(options=choices, value=current, layout=widgets.Layout(width="100%"),
                                tooltip=field_help.reference_system_tooltip(field_name))
    return widgets.Text(
        value="" if value is None else str(value),
        layout=widgets.Layout(width="100%"),
        continuous_update=False,
        tooltip=field_help.reference_system_tooltip(field_name),
    )


class InfrastructureEditors:
    """Line / Tracks / Geometry / Speed / Schematic sub-tabs."""

    def __init__(
        self,
        controller: ProjectController,
        *,
        mode_provider: Optional[Callable[[], str]] = None,
        on_status: Optional[Callable[[str], None]] = None,
        on_change: Optional[Callable[[], None]] = None,
        extra_panels: Optional[Mapping[str, Sequence[widgets.Widget]]] = None,
    ) -> None:
        self._controller = controller
        self._mode_provider = mode_provider
        self._on_status = on_status
        self._on_change = on_change
        self._extra = {title: list(panels) for title, panels in (extra_panels or {}).items()}
        self.editor = InfrastructureEditor(controller)
        self._tables: dict[str, TableEditor] = {}

        def _table(catalogue: str, title: str, subtitle: str) -> widgets.Widget:
            table = TableEditor(
                self._controller,
                catalogue,
                mode_provider=self._mode_provider,
                on_status=self._on_status,
                on_focus=self._handle_focus,
            )
            self._tables[catalogue] = table
            return panel_box(title, [table.widget], subtitle=subtitle)

        self.reference_editor = ReferenceSystemEditor(
            controller, self.editor, on_status=self._on_status
        )
        self.profile_points = NestedCataloguePanel(
            controller,
            catalogue="vertical_profile_points",
            owner_catalogue="vertical_profiles",
            title="Vertical profile points",
            subtitle="nested catalogue: points of the selected vertical profile",
            mode_provider=self._mode_provider,
            on_status=self._on_status,
            on_focus=self._handle_focus,
        )
        self.geometry_preview = GeometryPreview(controller)
        self.speed_preview = SpeedPreview(controller)
        self.schematic = SchematicPageProxy(
            controller,
            editor=self.editor,
            on_status=self._on_status,
            on_open_object=self._handle_open_object,
        )

        line_tab = widgets.VBox(
            [
                _table("alignments", "Alignments", "line-level catalogue (reference system below)"),
                self.reference_editor.widget,
                *self._extra.get("Line", ()),
            ]
        )
        tracks_tab = widgets.VBox(
            [
                _table("track_groups", "Track groups", "grouping and directionality of the tracks"),
                _table("nodes", "Topology nodes", "node identity - chainage equality is never used"),
                _table(
                    "tracks",
                    "Track edges",
                    "length_m is the stored length; chainage_map maps the track onto chainage",
                ),
                *self._extra.get("Tracks", ()),
            ]
        )
        geometry_tab = widgets.VBox(
            [
                _table("horizontal_geometry", "Horizontal geometry", "straight and curve sections"),
                _table("vertical_profiles", "Vertical profiles", "elevation source per alignment"),
                self.profile_points.widget,
                self.geometry_preview.widget,
                preview_note(),
                *self._extra.get("Geometry", ()),
            ]
        )
        speed_tab = widgets.VBox(
            [
                _table("speed_restrictions", "Speed restrictions", "Permanent, temporary and directional"),
                self.speed_preview.widget,
                *self._extra.get("Speed", ()),
            ]
        )
        schematic_tab = widgets.VBox([self.schematic.widget, *self._extra.get("Schematic", ())])
        self.host = SubTabHost(
            "Editor sub-tabs: choose the catalogue to edit; the JSON export stays authoritative.",
            [
                ("Line", line_tab),
                ("Tracks", tracks_tab),
                ("Geometry", geometry_tab),
                ("Speed", speed_tab),
                ("Schematic", schematic_tab),
            ],
        )

    @property
    def widget(self) -> widgets.Widget:
        """Return the root widget of the editor set."""
        return self.host.widget

    # -- routing -----------------------------------------------------------
    def tables(self) -> dict[str, TableEditor]:
        """Return the table editors keyed by catalogue."""
        return dict(self._tables)

    def focus(self, object_id: str) -> bool:
        """Select the sub-tab and row that holds *object_id* (click-to-focus)."""
        return self._handle_focus(object_id)

    def _tab_title_for(self, catalogue: str) -> str:
        """Return the sub-tab title that owns a catalogue."""
        for title, catalogues in INFRASTRUCTURE_TABS:
            if catalogue in catalogues:
                return title
        return ""

    def _handle_focus(self, object_id: str) -> bool:
        """Focus an object in the editor that owns it."""
        catalogue = catalogue_of_object(self.editor, object_id)
        title = self._tab_title_for(catalogue)
        if not title:
            if self._on_status is not None:
                self._on_status(f"focus: {object_id} is not editable on this page")
            return False
        self.host.select(title)
        if catalogue == "vertical_profile_points":
            for table in self.profile_points.tables().values():
                if object_id in table.rows():
                    table.set_focus(object_id)
                    break
        else:
            table = self._tables.get(catalogue)
            if table is not None:
                table.set_focus(object_id)
        if self._on_status is not None:
            self._on_status(f"focus: {object_id} ({catalogue}) on sub-tab {title}")
        return True

    def _handle_open_object(self, kind: str, object_id: str) -> None:
        """Open an object selected in the schematic."""
        catalogue = schematic_render.KIND_TO_CATALOGUE.get(kind, "")
        if not catalogue:
            catalogue = catalogue_of_object(self.editor, object_id)
        title = self._tab_title_for(catalogue)
        if title:
            self.host.select(title)
        self._handle_focus(object_id)

    def refresh(self) -> None:
        """Re-render every table and preview."""
        for table in self._tables.values():
            table.refresh()
        self.profile_points.refresh()
        self.reference_editor.refresh()
        self.geometry_preview.refresh()
        self.speed_preview.refresh()
        self.schematic.refresh()


class SchematicPageProxy:
    """Thin wrapper that forwards to :class:`~railway_headway_sim.ui.schematic_page.SchematicPage`."""

    def __init__(
        self,
        controller: ProjectController,
        *,
        editor: InfrastructureEditor,
        on_status: Optional[Callable[[str], None]] = None,
        on_open_object: Optional[Callable[[str, str], None]] = None,
    ) -> None:
        from .schematic_page import SchematicPage

        self._page = SchematicPage(
            controller, editor=editor, on_status=on_status, on_open_object=on_open_object
        )

    @property
    def widget(self) -> widgets.Widget:
        """Return the schematic page root widget."""
        return self._page.widget

    def refresh(self) -> None:
        """Re-render the schematic."""
        self._page.refresh()

    def focus(self, object_id: str) -> None:
        """Select an object on the schematic."""
        self._page.focus(object_id)

    def view(self) -> Any:
        """Return the schematic view (selection and layer accessors)."""
        return self._page.view


class StationsEditors:
    """Stations / Platforms / Stopping Marks / Observation Points sub-tabs."""

    def __init__(
        self,
        controller: ProjectController,
        *,
        mode_provider: Optional[Callable[[], str]] = None,
        on_status: Optional[Callable[[str], None]] = None,
        on_change: Optional[Callable[[], None]] = None,
        extra_panels: Optional[Mapping[str, Sequence[widgets.Widget]]] = None,
    ) -> None:
        self._controller = controller
        self._mode_provider = mode_provider
        self._on_status = on_status
        self._on_change = on_change
        self._extra = {title: list(panels) for title, panels in (extra_panels or {}).items()}
        self.editor = InfrastructureEditor(controller)
        self._tables: dict[str, TableEditor] = {}

        def _table(catalogue: str, title: str, subtitle: str) -> widgets.Widget:
            table = TableEditor(
                self._controller,
                catalogue,
                mode_provider=self._mode_provider,
                on_status=self._on_status,
                on_focus=self._handle_focus,
            )
            self._tables[catalogue] = table
            return panel_box(title, [table.widget], subtitle=subtitle)

        self.train_fit = TrainFitChecker(controller)
        stations_tab = widgets.VBox(
            [
                _table("stations", "Stations", "typed station catalogue"),
                *self._extra.get("Stations", ()),
            ]
        )
        platforms_tab = widgets.VBox(
            [
                _table(
                    "platforms",
                    "Platforms",
                    "usable range inside the track length (usable_length_m is stored, not derived)",
                ),
                *self._extra.get("Platforms", ()),
            ]
        )
        marks_tab = widgets.VBox(
            [
                _table(
                    "stopping_marks",
                    "Stopping marks",
                    "authoritative location = track_id + position_m; the chainage is derived",
                ),
                widgets.HTML(
                    fmt.section_note_html(
                        "Derived row values (for example the mapped chainage of a stopping mark) "
                        "carry the DERIVED provenance chip and come from the Phase-2 mapping "
                        "utility - they are never typed here."
                    )
                ),
                *self._extra.get("Stopping Marks", ()),
                self.train_fit.widget,
            ]
        )
        observations_tab = widgets.VBox(
            [
                _table("observation_points", "Observation points", "static reference points"),
                *self._extra.get("Observation Points", ()),
            ]
        )
        self.host = SubTabHost(
            "Editor sub-tabs: stations, platforms, stopping marks and observation points.",
            [
                ("Stations", stations_tab),
                ("Platforms", platforms_tab),
                ("Stopping Marks", marks_tab),
                ("Observation Points", observations_tab),
            ],
        )

    @property
    def widget(self) -> widgets.Widget:
        """Return the root widget of the editor set."""
        return self.host.widget

    def tables(self) -> dict[str, TableEditor]:
        """Return the table editors keyed by catalogue."""
        return dict(self._tables)

    def _tab_title_for(self, catalogue: str) -> str:
        """Return the sub-tab title that owns a catalogue."""
        for title, catalogues in STATIONS_TABS:
            if catalogue in catalogues:
                return title
        return ""

    def focus(self, object_id: str) -> bool:
        """Select the sub-tab and row that holds *object_id*."""
        return self._handle_focus(object_id)

    def _handle_focus(self, object_id: str) -> bool:
        """Focus an object in the editor that owns it."""
        catalogue = catalogue_of_object(self.editor, object_id)
        title = self._tab_title_for(catalogue)
        if not title:
            if self._on_status is not None:
                self._on_status(f"focus: {object_id} is not editable on this page")
            return False
        self.host.select(title)
        table = self._tables.get(catalogue)
        if table is not None:
            table.set_focus(object_id)
        if self._on_status is not None:
            self._on_status(f"focus: {object_id} ({catalogue}) on sub-tab {title}")
        return True

    def refresh(self) -> None:
        """Re-render every table and the fit checker."""
        for table in self._tables.values():
            table.refresh()
        self.train_fit.refresh()


def catalogue_headers(catalogue: str, mode: str = STANDARD) -> tuple[str, ...]:
    """Return the headers of a catalogue in a mode (small helper for the pages)."""
    return tuple(spec.header for spec in fields_of(catalogue, mode=mode))


def id_prefix(catalogue: str) -> str:
    """Return the default id prefix of a catalogue."""
    return ID_PREFIXES.get(catalogue, "OBJ")


def spec_for(catalogue: str, field_name: str) -> Any:
    """Return the field specification of a catalogue field."""
    return spec_of(catalogue, field_name)
