"""Project page: New Project, Import JSON, Validate, Export JSON and editable metadata.

The page is a *consumer/editor* of the controller state: widgets read from
:class:`~railway_headway_sim.app.project_controller.ProjectController` and call
controller methods. Nothing is stored in widget values as project state.
"""

from __future__ import annotations

from typing import Any, Callable, Optional

import ipywidgets as widgets

from ..app.project_controller import ProjectController
from ..models.enums import Severity
from ..models.project import Project
from . import formatting as fmt

#: UI field name -> message key understood by ``controller.update_metadata``.
FIELD_KEYS: dict[str, str] = {
    "project_id": "id",
    "project_name": "name",
    "description": "description",
    "origin_name": "chainage_origin_name",
    "end_name": "chainage_end_name",
    "chainage_start": "chainage_start_km",
    "chainage_end": "chainage_end_km",
}

#: Field order and labels of the editable metadata form.
FIELD_ORDER: tuple[tuple[str, str, str], ...] = (
    ("project_id", "Project ID", "Machine identifier, e.g. PRJ-4f9c1a7b2d3e"),
    ("project_name", "Project Name", "Display name (editable; never used as a key)"),
    ("description", "Description", "Free text project description"),
    ("origin_name", "Origin Name", "Chainage origin terminal, e.g. Alpha"),
    ("end_name", "End Name", "Chainage end terminal, e.g. Delta"),
    ("chainage_start", "Chainage Start", "km, e.g. 0.0"),
    ("chainage_end", "Chainage End", "km, e.g. 250.0"),
)

_DESCRIPTION_WIDTH = "210px"


def panel_box(title: str, children: list[widgets.Widget], *, tone: str = "navy", subtitle: str = "") -> widgets.VBox:
    """Build a bordered panel containing *children* under a coloured header."""
    return widgets.VBox(
        [widgets.HTML(fmt.panel_header_html(title, tone=tone, subtitle=subtitle)), *children],
        layout=widgets.Layout(margin="0px 0px 10px 0px", **fmt.border_layout_style()),
    )


def form_row(label: str, control: widgets.Widget) -> widgets.HBox:
    """Build one label/control row of the metadata form."""
    label_widget = widgets.HTML(
        f'<div style="font-size:12px;color:{fmt.PALETTE["muted"]};font-family:Helvetica,Arial,sans-serif;'
        f'padding-top:5px;">{fmt.esc(label)}</div>',
        layout=widgets.Layout(width=_DESCRIPTION_WIDTH),
    )
    return widgets.HBox(
        [label_widget, control],
        layout=widgets.Layout(align_items="flex-start", margin="2px 0px 2px 0px"),
    )


class ProjectPage:
    """The Phase-1 Project page."""

    def __init__(self, controller: ProjectController) -> None:
        self._controller = controller
        self._loading = False
        self._dirty = False
        self._unsubscribe: Optional[Callable[[], None]] = None
        self._build()
        self._unsubscribe = controller.subscribe(self.refresh)
        self.refresh()

    # -- construction ------------------------------------------------------
    def _build(self) -> None:
        self._new_button = widgets.Button(
            description="New Project", button_style="info", icon="file",
            layout=widgets.Layout(width="150px", margin="0px 8px 6px 0px"),
            tooltip="Create a minimal valid schema-1.0 project template.",
        )
        self._validate_button = widgets.Button(
            description="Validate Project", button_style="primary",
            layout=widgets.Layout(width="170px", margin="0px 8px 6px 0px"),
            tooltip="Run Phase-1 structural/basic semantic validation on the current project.",
        )
        self._export_button = widgets.Button(
            description="Export JSON", button_style="success", icon="download",
            layout=widgets.Layout(width="140px", margin="0px 8px 6px 0px"),
            tooltip="Download the canonical project JSON (Colab browser download + file written).",
        )
        self._import_button = widgets.Button(
            description="Import JSON", button_style="warning", icon="upload",
            layout=widgets.Layout(width="140px", margin="0px 8px 6px 0px"),
            tooltip="Import the JSON file selected in the upload widget below.",
        )
        self._upload = widgets.FileUpload(
            accept=".json", multiple=False, description="Select .json file",
            layout=widgets.Layout(width="240px", margin="0px 8px 6px 0px"),
        )
        self._actions_row = widgets.HBox(
            [self._new_button, self._validate_button, self._export_button],
            layout=widgets.Layout(flex_flow="row wrap", margin="0px 0px 8px 0px"),
        )
        self._import_row = widgets.HBox(
            [self._upload, self._import_button],
            layout=widgets.Layout(align_items="center"),
        )

        self._fields: dict[str, widgets.Text] = {}
        rows: list[widgets.Widget] = []
        for name, label, placeholder in FIELD_ORDER:
            control = widgets.Textarea(placeholder=placeholder) if name == "description" else widgets.Text(placeholder=placeholder)
            control.layout = widgets.Layout(width="560px", height="60px" if name == "description" else "auto")
            control.continuous_update = False
            control.observe(self._on_field_edited, names="value")
            self._fields[name] = control
            rows.append(form_row(label, control))

        self._save_button = widgets.Button(
            description="Save metadata", button_style="primary", icon="save",
            layout=widgets.Layout(width="170px", margin="0px 8px 6px 0px"),
            tooltip="Write the edited values into the canonical project model.",
        )
        self._reload_button = widgets.Button(
            description="Discard edits", layout=widgets.Layout(width="140px", margin="0px 8px 6px 0px"),
            tooltip="Reload the field values from the canonical project model.",
        )
        self._form_note = widgets.HTML(value="")
        self._form_buttons = widgets.HBox(
            [self._save_button, self._reload_button],
            layout=widgets.Layout(align_items="center"),
        )

        self._summary = widgets.HTML(value="")
        self._counts = widgets.HTML(value="")
        self._typed_counts = widgets.HTML(value="")

        self._new_button.on_click(self._handle_new)
        self._import_button.on_click(self._handle_import)
        self._validate_button.on_click(self._handle_validate)
        self._export_button.on_click(self._handle_export)
        self._save_button.on_click(self._handle_save)
        self._reload_button.on_click(self._handle_reload)

        phase_note = widgets.HTML(
            f'<div style="font-size:11px;color:{fmt.PALETTE["muted"]};font-family:Helvetica,Arial,sans-serif;">'
            "This page creates, imports, validates and exports the project container. The "
            "physical-infrastructure pages render stored data and static geometry checks; no "
            "train dynamics, signalling, headway or capacity calculation is performed.</div>"
        )

        controls_panel = panel_box(
            "Project data source",
            [self._actions_row, self._import_row, phase_note],
            subtitle="new / import / validate / export",
        )
        metadata_panel = panel_box(
            "Project metadata and reference system",
            [*rows, self._form_note, self._form_buttons],
            subtitle="editable fields of the canonical model",
        )
        summary_panel = panel_box("Project summary", [self._summary], subtitle="from the canonical model")
        counts_panel = panel_box(
            "Container contents",
            [self._counts],
            subtitle="plain object counts - no engineering results",
        )
        typed_counts_panel = panel_box(
            "Typed infrastructure inventory (Phase 2)",
            [self._typed_counts],
            subtitle="typed catalogues inside the infrastructure layers - counts only",
        )

        self._widget = widgets.VBox(
            [controls_panel, metadata_panel, summary_panel, counts_panel, typed_counts_panel],
            layout=widgets.Layout(margin="8px 0px 0px 0px"),
        )

    # -- event handlers ----------------------------------------------------
    def _handle_new(self, _button: widgets.Button) -> None:
        """Create a new project from the template (controller does the work)."""
        self._controller.create_new_project()

    def _handle_import(self, _button: widgets.Button) -> None:
        """Import the selected file through the controller."""
        self._controller.import_json_upload(self._upload.value)
        self._clear_upload()

    def _handle_validate(self, _button: widgets.Button) -> None:
        """Validate the current project."""
        self._controller.validate_project()

    def _handle_export(self, _button: widgets.Button) -> None:
        """Export the current project as JSON."""
        self._controller.export_json()

    def _handle_save(self, _button: widgets.Button) -> None:
        """Push the edited values into the canonical project model."""
        self._controller.update_metadata(
            **{key: self._fields[name].value for name, key in FIELD_KEYS.items()}
        )

    def _handle_reload(self, _button: widgets.Button) -> None:
        """Discard edits by reloading widget values from the model."""
        self.refresh()

    def _on_field_edited(self, change: dict[str, Any]) -> None:
        """Flag unsaved edits (the model is only written on 'Save metadata')."""
        if self._loading:
            return
        self._dirty = True
        self._form_note.value = self._note_html()

    def _clear_upload(self) -> None:
        """Best-effort reset of the upload widget so the same file can be re-imported."""
        try:
            self._upload.value = ()
        except (TypeError, ValueError, AttributeError):
            # Not all ipywidgets/file-upload states allow clearing; harmless.
            pass

    # -- rendering ---------------------------------------------------------
    def refresh(self) -> None:
        """Re-render the page from the current controller state."""
        self._loading = True
        try:
            project = self._controller.project
            has_project = project is not None
            for name, control in self._fields.items():
                control.value = self._field_value(project, name) or ""
            self._dirty = False
            self._summary.value = fmt.kv_table_html(self._controller.summary_rows())
            self._counts.value = fmt.summary_grid_html(self._controller.object_count_rows())
            typed_rows = self._controller.typed_inventory_rows()
            self._typed_counts.value = (
                fmt.summary_grid_html(typed_rows, columns=4)
                if typed_rows
                else fmt.section_note_html(
                    "This project declares no typed physical infrastructure: the infrastructure "
                    "layers are preserved as Phase-1 containers without typed catalogues."
                )
            )
            self._form_note.value = self._note_html()
            for control in self._fields.values():
                control.disabled = not has_project
            self._save_button.disabled = not has_project
            self._reload_button.disabled = not has_project
            self._validate_button.disabled = not has_project
            self._export_button.disabled = not has_project
        finally:
            self._loading = False

    def _note_html(self) -> str:
        """Return the small note under the metadata form."""
        if self._dirty:
            return fmt.message_html(
                "Unsaved edits in the form - press 'Save metadata' to write them into the "
                "canonical project model, or 'Discard edits'.",
                severity=Severity.WARNING,
            )
        if self._controller.project is None:
            return fmt.message_html(
                "No project loaded. Press 'New Project' or import a project JSON file.",
                severity=Severity.INFO,
            )
        return fmt.message_html(
            "Form values are read from the canonical project model; they are only written back "
            "when you press 'Save metadata'.",
            severity=Severity.INFO,
        )

    @staticmethod
    def _field_value(project: Optional[Project], name: str) -> str:
        """Read the display string of one form field from the project."""
        if project is None:
            return ""
        if name == "project_id":
            return project.project.id or ""
        if name == "project_name":
            return project.project.name or ""
        if name == "description":
            return project.project.description or ""
        if name == "origin_name":
            return project.reference_system.chainage_origin_name or ""
        if name == "end_name":
            return project.reference_system.chainage_end_name or ""
        if name == "chainage_start":
            value = project.reference_system.chainage_start_km
            return "" if value is None else str(value)
        if name == "chainage_end":
            value = project.reference_system.chainage_end_km
            return "" if value is None else str(value)
        raise KeyError(name)

    @property
    def widget(self) -> widgets.Widget:
        """Return the root widget of this page."""
        return self._widget
