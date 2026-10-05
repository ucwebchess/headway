"""Generic editable catalogue table (Phase-3 §G2, §G11, §J).

One ``TableEditor`` renders one typed catalogue as a table:

* a header row with the exact field names and their unit suffixes,
* one row of widgets per object, each carrying a one-line tooltip,
* an error/warning badge per row (text, never colour alone),
* add / delete buttons per table,
* a provenance label per column (INPUT / DERIVED),
* visibility of low-level fields driven by the STANDARD / ADVANCED switch.

Every change goes through :class:`~railway_headway_sim.ui.editing.InfrastructureEditor`,
which stages it into the existing Phase-2 draft mechanism.  The widget never writes
to the project model and never performs an engineering calculation.
"""

from __future__ import annotations

from typing import Any, Callable, Optional, Sequence

import ipywidgets as widgets

from ..app.project_controller import ProjectController
from ..models.enums import Severity
from . import formatting as fmt
from .editing import CatalogueEdit, InfrastructureEditor, Provenance
from .editor_specs import ID_PREFIXES, FieldKind, FieldSpec, fields_of, spec_of
from .project_page import panel_box


def _widget_for(spec: FieldSpec, value: Any, options: Sequence[str]) -> widgets.Widget:
    """Build the editing widget of one field."""
    if spec.kind is FieldKind.ENUM:
        choices = list(spec.enum_values)
        current = str(getattr(value, "value", value)) if value is not None else ""
        if current not in choices:
            choices.append(current or "")
        return widgets.Dropdown(
            options=choices,
            value=current if current in choices else choices[0],
            layout=widgets.Layout(width="100%"),
            tooltip=spec.tooltip,
        )
    if spec.kind in (FieldKind.REFERENCE,):
        choices = [""] + list(options)
        current = "" if value is None else str(value)
        if current not in choices:
            choices.append(current)
        return widgets.Dropdown(
            options=choices,
            value=current,
            layout=widgets.Layout(width="100%"),
            tooltip=spec.tooltip,
        )
    if spec.kind in (FieldKind.INTEGER, FieldKind.NUMBER):
        number = float(value) if isinstance(value, (int, float)) else 0.0
        step = spec.step if spec.step is not None else 1.0
        if spec.kind is FieldKind.INTEGER or float(step).is_integer():
            return widgets.FloatText(
                value=number,
                step=step,
                layout=widgets.Layout(width="100%"),
                tooltip=spec.tooltip,
                continuous_update=False,
            )
        return widgets.FloatText(
            value=number,
            step=step,
            layout=widgets.Layout(width="100%"),
            tooltip=spec.tooltip,
            continuous_update=False,
        )
    text = "" if value is None else str(value)
    return widgets.Text(
        value=text,
        layout=widgets.Layout(width="100%"),
        tooltip=spec.tooltip,
        continuous_update=False,
    )


def _as_value(spec: FieldSpec, raw: Any, original: Any) -> Any:
    """Convert a widget value into the stored representation of the field."""
    if spec.kind in (FieldKind.NUMBER, FieldKind.INTEGER):
        number = float(raw)
        if spec.kind is FieldKind.INTEGER:
            return int(number)
        return number
    if spec.kind in (FieldKind.ENUM, FieldKind.REFERENCE):
        text = "" if raw is None else str(raw)
        if spec.optional and text == "":
            return None
        return text
    if spec.kind in (FieldKind.ID_LIST, FieldKind.MEMBER_LIST):
        if isinstance(original, list):
            return list(original)
        text = "" if raw is None else str(raw)
        return [part.strip() for part in text.split(",") if part.strip()]
    text = "" if raw is None else str(raw)
    if spec.optional and text == "":
        return None
    return text


def close_widget_tree(widget: widgets.Widget) -> None:
    """Close *widget*, every widget below it, and their styling widgets.

    ``ipywidgets`` keeps a strong reference to every widget that is created and
    releases it when the widget is closed, so a table that simply replaces its rows
    on every re-render would grow the memory of the kernel for the whole session
    (each row carries its own layouts and styles).  Closing the discarded tree
    keeps a long editing session flat.

    Only the documented, public ``ipywidgets`` API is used.  The tree is walked
    downwards through the public attributes a widget exposes: ``children`` of a
    container, the ``layout`` / ``style`` widgets every widget carries (they are
    widgets too), and ``value`` when a widget holds another widget.  Each widget
    then releases itself through its own public ``Widget.close()`` method.  No
    private ``ipywidgets`` name is imported or read anywhere in this package.

    Order: children before their container, and every widget is closed exactly once
    per call (a styling widget shared by two rows is closed once).  The function is
    safe on a leaf widget, on a container whose children are containers, on a widget
    that has already been closed, and on a widget that does not expose ``children``
    at all: it never raises, and closing an already closed widget is a no-op because
    ``Widget.close()`` returns immediately once the widget owns no comm.  It never
    consults the widget's parent link, which is not available in every ipywidgets
    version.

    This is resource management only: no widget value, model value, validation
    result or stored project data is affected, and a closed widget is never shown
    again (it is the tree that was just replaced).
    """
    _close_widget_tree(widget, set())


def _close_widget_tree(widget: widgets.Widget, seen: set[int]) -> None:
    """Depth-first close of *widget* and everything it owns, each widget exactly once."""
    if not isinstance(widget, widgets.Widget) or id(widget) in seen:
        return
    seen.add(id(widget))
    for child in list(getattr(widget, "children", ()) or ()):
        _close_widget_tree(child, seen)
    for attribute in ("layout", "style", "value"):
        try:
            nested = getattr(widget, attribute, None)
        except Exception:  # pragma: no cover - defensive: a widget may refuse an attribute
            nested = None
        if isinstance(nested, widgets.Widget):
            _close_widget_tree(nested, seen)
    _deregister(widget)


def _deregister(widget: widgets.Widget) -> None:
    """Close one widget through the public ``ipywidgets`` API.

    ``Widget.close()`` is the documented way to release a widget: it closes the
    widget's comm and removes the widget from the ``ipywidgets`` widget registry,
    which is what keeps the memory of a long editing session flat.  The call is
    idempotent - ``Widget.close()`` returns immediately once the widget owns no
    comm - and a failure to close is swallowed: releasing a discarded tree must
    never break a re-render.
    """
    try:
        widget.close()
    except Exception:  # pragma: no cover - closing must never break a re-render
        pass


class TableEditor:
    """Editable table for one typed catalogue of the loaded project."""

    def __init__(
        self,
        controller: ProjectController,
        catalogue: str,
        *,
        editor: Optional[InfrastructureEditor] = None,
        mode_provider: Optional[Callable[[], str]] = None,
        on_status: Optional[Callable[[str], None]] = None,
        on_focus: Optional[Callable[[str], None]] = None,
        columns: int = 4,
    ) -> None:
        self._controller = controller
        self._catalogue = catalogue
        self._editor = editor if editor is not None else InfrastructureEditor(controller)
        self._mode_provider = mode_provider if mode_provider is not None else (lambda: "ADVANCED")
        self._on_status = on_status
        self._on_focus = on_focus
        self._columns = columns
        self._row_widgets: dict[str, dict[str, widgets.Widget]] = {}
        self._row_badges: dict[str, widgets.HTML] = {}
        self._delete_buttons: dict[str, widgets.Button] = {}
        self._row_roots: list[widgets.Widget] = []
        self._focus_id: str = ""
        self._build()
        self.refresh()

    # -- construction ------------------------------------------------------
    def _build(self) -> None:
        self._header = widgets.HTML(value="")
        self._rows_box = widgets.VBox([], layout=widgets.Layout(gap="2px"))
        self._add_button = widgets.Button(
            description=f"+ Add {self._catalogue} row",
            button_style="success",
            layout=widgets.Layout(width="220px"),
            tooltip=(
                f"Add a new row to the {self._catalogue} catalogue. The new row is staged as a "
                "draft and validated before it can be committed."
            ),
        )
        self._add_button.on_click(self._handle_add)
        self._new_id = widgets.Text(
            value="",
            placeholder=f"new {ID_PREFIXES.get(self._catalogue, 'ID')}-...",
            description="New ID:",
            layout=widgets.Layout(width="320px"),
            tooltip="Identifier of the row to add; must be unique across the whole project.",
        )
        self._massage = widgets.HTML(value="")
        self._widget = widgets.VBox(
            [
                self._header,
                self._rows_box,
                widgets.HBox(
                    [self._new_id, self._add_button, self._massage],
                    layout=widgets.Layout(align_items="center", flex_flow="row wrap"),
                ),
            ]
        )

    # -- public accessors --------------------------------------------------
    @property
    def widget(self) -> widgets.Widget:
        """Return the root widget of this table."""
        return self._widget

    @property
    def catalogue(self) -> str:
        """Return the catalogue key edited by this table."""
        return self._catalogue

    def rows(self) -> tuple[str, ...]:
        """Return the ids of the rows currently shown, in document order."""
        return tuple(self._row_widgets)

    def row_widgets(self, object_id: str) -> dict[str, widgets.Widget]:
        """Return the widgets of one row (empty when the row is not shown)."""
        return dict(self._row_widgets.get(object_id, {}))

    def headers(self) -> tuple[str, ...]:
        """Return the visible column headers, including unit suffixes."""
        return tuple(spec.header for spec in self.visible_fields())

    def visible_fields(self) -> tuple[FieldSpec, ...]:
        """Return the fields visible in the current editor mode."""
        return fields_of(self._catalogue, mode=self._mode_provider())

    def badge_of(self, object_id: str) -> str:
        """Return the error/warning badge text of one row."""
        return self._editor.error_badge(object_id)

    def set_focus(self, object_id: str) -> None:
        """Focus a row (used by the schematic and the validation summary)."""
        self._focus_id = object_id
        self.refresh()

    def focused_id(self) -> str:
        """Return the currently focused row id (``''`` when none)."""
        return self._focus_id

    # -- editing -----------------------------------------------------------
    def stage_field(self, object_id: str, field_name: str, value: Any) -> CatalogueEdit:
        """Stage one field change and report the outcome."""
        spec = spec_of(self._catalogue, field_name)
        if spec is None:
            raise KeyError(f"{self._catalogue}.{field_name} is not an editable field")
        outcome = self._editor.stage_field(self._catalogue, object_id, field_name, value)
        self._report(outcome)
        return outcome

    def stage_values(self, object_id: str, values: dict[str, Any]) -> CatalogueEdit:
        """Stage several fields of one row in a single draft."""
        return self.stage_fields(object_id, values)

    def stage_fields(self, object_id: str, values: dict[str, Any]) -> CatalogueEdit:
        """Stage several fields of one row in a single draft."""
        outcome = self._editor.stage_entry(self._catalogue, values, object_id=object_id)
        self._report(outcome)
        return outcome

    def add_row(self, values: Optional[dict[str, Any]] = None, *, object_id: str = "") -> CatalogueEdit:
        """Add a row (explicit values, or catalogue defaults + a generated id)."""
        payload = dict(values or {})
        if object_id:
            payload["id"] = object_id
        if not payload.get("id"):
            payload["id"] = self.next_id()
        outcome = self._editor.stage_entry(self._catalogue, payload)
        self._report(outcome)
        return outcome

    def delete_row(self, object_id: str) -> CatalogueEdit:
        """Delete a row; refused while other objects reference it."""
        outcome = self._editor.delete_entry(self._catalogue, object_id)
        self._report(outcome)
        return outcome

    def next_id(self, *, prefix: Optional[str] = None) -> str:
        """Return an unused id for a new row of this catalogue."""
        stem = prefix or ID_PREFIXES.get(self._catalogue, "OBJ")
        existing = set(self._editor.ids(self._catalogue))
        index = 1
        while f"{stem}-NEW-{index:02d}" in existing:
            index += 1
        return f"{stem}-NEW-{index:02d}"

    # -- handlers ----------------------------------------------------------
    def _handle_add(self, _button: widgets.Button) -> None:
        """Add a row from the id field (default values are staged as-is)."""
        outcome = self.add_row(object_id=(self._new_id.value or "").strip())
        if outcome.ok:
            self._new_id.value = ""

    def _handle_delete(self, object_id: str) -> None:
        """Delete a row after the refusal check."""
        self.delete_row(object_id)

    def _handle_change(self, object_id: str, field_name: str, change: dict[str, Any]) -> None:
        """Stage a widget change (never writes to the model directly)."""
        spec = spec_of(self._catalogue, field_name)
        if spec is None:  # pragma: no cover - defensive
            return
        original = self._original_value(object_id, field_name)
        value = _as_value(spec, change.get("new"), original)
        if value == original:
            return
        self.stage_field(object_id, field_name, value)

    def _original_value(self, object_id: str, field_name: str) -> Any:
        """Return the stored value of a field in the working document."""
        record = self._editor.entry(self._catalogue, object_id)
        if record is None:
            return None
        parent, leaf = field_name.partition(".")
        if leaf and parent in record and isinstance(record[parent], dict):
            return record[parent].get(leaf)
        return record.get(field_name)

    def _report(self, outcome: CatalogueEdit) -> None:
        """Show the edit outcome on the panel and in the application status line."""
        severity = Severity.INFO if outcome.ok else Severity.ERROR
        self._massage.value = fmt.message_html(outcome.message, severity=severity)
        if self._on_status is not None:
            self._on_status(outcome.message)
        self.refresh()

    # -- rendering ---------------------------------------------------------
    def refresh(self) -> None:
        """Re-render the table from the working document."""
        fields = self.visible_fields()
        self._header.value = self._header_html(fields)
        for root in self._row_roots:
            close_widget_tree(root)
        self._row_roots = []
        rows = []
        self._row_widgets = {}
        self._row_badges = {}
        self._delete_buttons = {}
        for record in self._editor.entries(self._catalogue):
            object_id = str(record.get("id"))
            rows.append(self._row_widget(object_id, record, fields))
        if not rows:
            rows.append(
                widgets.HTML(
                    fmt.data_table_html(
                        tuple(spec.header for spec in fields),
                        (),
                        empty_text=f"No rows in {self._catalogue}.",
                    )
                )
            )
        self._rows_box.children = rows
        self._add_button.description = f"+ Add {self._catalogue} row"

    def _row_widget(
        self, object_id: str, record: dict[str, Any], fields: Sequence[FieldSpec]
    ) -> widgets.Widget:
        """Build one editable row."""
        options = self._reference_options(fields)
        cells: list[widgets.Widget] = []
        row_widgets: dict[str, widgets.Widget] = {}
        for spec in fields:
            value = self._value_of(record, spec.name)
            widget = _widget_for(spec, value, options.get(spec.reference or "", ()))
            widget.observe(
                lambda change, oid=object_id, name=spec.name: self._handle_change(oid, name, change),
                names="value",
            )
            row_widgets[spec.name] = widget
            cells.append(
                widgets.VBox(
                    [
                        widget,
                        widgets.HTML(self._provenance_html(spec)),
                    ],
                    layout=widgets.Layout(width=f"{max(80, 720 // max(len(fields), 1))}px"),
                )
            )
        badge = widgets.HTML(value=self._badge_html(object_id))
        self._row_badges[object_id] = badge
        delete_button = widgets.Button(
            description="Delete",
            button_style="danger",
            layout=widgets.Layout(width="82px"),
            tooltip="Delete this row. Blocked when other objects still reference it.",
        )
        delete_button.on_click(lambda _b, oid=object_id: self._handle_delete(oid))
        self._delete_buttons[object_id] = delete_button
        focus_button = widgets.Button(
            description="Select",
            layout=widgets.Layout(width="82px"),
            tooltip="Focus this object (also highlights it in the schematic).",
        )
        focus_button.on_click(lambda _b, oid=object_id: self._focus(oid))
        marker = "◀ focused" if object_id == self._focus_id else ""
        self._row_widgets[object_id] = row_widgets
        root = widgets.VBox(
            [
                widgets.HBox(
                    [
                        widgets.HTML(self._id_cell_html(object_id)),
                        *cells,
                        badge,
                        focus_button,
                        delete_button,
                    ],
                    layout=widgets.Layout(
                        align_items="flex-start", flex_flow="row wrap", overflow="auto"
                    ),
                ),
                widgets.HTML(
                    f'<div style="font-size:10px;color:{fmt.PALETTE["muted"]};margin:1px 0 4px 4px;">'
                    f"{fmt.esc(marker)}</div>"
                ),
            ],
            layout=fmt.border_layout_style(fmt.PALETTE["line"]),
        )
        self._row_roots.append(root)
        return root

    def _value_of(self, record: dict[str, Any], field_name: str) -> Any:
        """Read a (possibly nested) field from a raw entry."""
        parent, _, leaf = field_name.partition(".")
        if leaf and isinstance(record.get(parent), dict):
            return record[parent].get(leaf)
        return record.get(field_name)

    def _reference_options(self, fields: Sequence[FieldSpec]) -> dict[str, tuple[str, ...]]:
        """Return the selectable ids per referenced catalogue."""
        options: dict[str, tuple[str, ...]] = {}
        for spec in fields:
            if spec.reference and spec.reference not in options:
                options[spec.reference] = self._editor.ids(spec.reference)
        return options

    def _focus(self, object_id: str) -> None:
        """Focus a row and notify the shell."""
        self._focus_id = object_id
        if self._on_focus is not None:
            self._on_focus(object_id)
        self.refresh()

    # -- html fragments ----------------------------------------------------
    def _header_html(self, fields: Sequence[FieldSpec]) -> str:
        """Render the table caption: catalogue, mode, row count and draft status."""
        mode = self._mode_provider()
        hidden = len(fields_of(self._catalogue, mode="ADVANCED")) - len(fields)
        note = (
            f" - {hidden} advanced field(s) hidden in STANDARD mode"
            if hidden > 0
            else ""
        )
        return fmt.section_note_html(
            f"{self._catalogue}: {len(self._editor.entries(self._catalogue))} row(s), "
            f"mode {mode}{note}. Units are shown in the column headers; every change is staged "
            "as a draft (APP-EDIT-002) and never writes to the committed project directly."
        )

    def _id_cell_html(self, object_id: str) -> str:
        """Render the read-only id cell of a row."""
        return (
            f'<div style="width:150px;font-size:11px;font-weight:700;color:{fmt.PALETTE["navy"]};'
            f'padding-top:6px;font-family:Helvetica,Arial,sans-serif;">{fmt.esc(object_id)}</div>'
        )

    def _badge_html(self, object_id: str) -> str:
        """Render the validation badge of a row (text, not colour alone)."""
        diagnostics = self._editor.diagnostics_for(object_id)
        if not diagnostics:
            return (
                f'<div style="width:150px;font-size:10px;color:{fmt.PALETTE["muted"]};padding-top:6px;">'
                "OK</div>"
            )
        parts: list[str] = ['<div style="width:150px;font-size:10px;padding-top:4px;">']
        for diagnostic in diagnostics[:3]:
            tone = fmt.tone_for_severity(diagnostic.severity)
            label = {"ok": "OK", "warn": "WARNING", "info": "INFO", "error": "ERROR"}.get(tone, "INFO")
            parts.append(
                f'<div style="margin-bottom:2px;">'
                f'<span style="background:{fmt.PALETTE.get(tone, fmt.PALETTE["muted"])};color:#fff;'
                f'border-radius:3px;padding:0 4px;font-weight:700;">{label}</span> '
                f"{fmt.esc(diagnostic.code)}</div>"
                f'<div style="color:{fmt.PALETTE["muted"]};">{fmt.esc(diagnostic.message[:120])}</div>'
            )
        parts.append("</div>")
        return "".join(parts)

    def _provenance_html(self, spec: FieldSpec) -> str:
        """Render the provenance label of a column cell."""
        provenance = self._editor.provenance(self._catalogue, spec.name)
        tone = "ok" if provenance is Provenance.INPUT else "info"
        return (
            f'<div style="font-size:9px;color:{fmt.PALETTE["muted"]};margin-top:1px;" '
            f'title="{fmt.esc(spec.tooltip)}">'
            f'<span style="border:1px solid {fmt.PALETTE.get(tone, fmt.PALETTE["muted"])};'
            f'border-radius:3px;padding:0 3px;">{provenance.value}</span> '
            f"{fmt.esc(spec.unit or '')}</div>"
        )


def editor_panel(
    controller: ProjectController,
    catalogue: str,
    *,
    title: str,
    subtitle: str = "",
    editor: Optional[InfrastructureEditor] = None,
    mode_provider: Optional[Callable[[], str]] = None,
    on_status: Optional[Callable[[str], None]] = None,
    on_focus: Optional[Callable[[str], None]] = None,
) -> tuple[TableEditor, widgets.Widget]:
    """Return a table editor and the panel box that contains it."""
    table = TableEditor(
        controller,
        catalogue,
        editor=editor,
        mode_provider=mode_provider,
        on_status=on_status,
        on_focus=on_focus,
    )
    return table, panel_box(title, [table.widget], subtitle=subtitle)
