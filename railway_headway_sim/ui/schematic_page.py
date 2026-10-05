"""Infrastructure schematic sub-tab (Phase-3 §G7).

The schematic is generated from the canonical model - it is a *view* of the
catalogues, never a second definition of the layout.  Objects are coloured by
catalogue, every drawn id is simultaneously offered as a selection target (so a
click surface exists without JavaScript), and objects that carry an ERROR
diagnostic are marked with the text ``!`` plus the diagnostic code.

Layer control
-------------
The eight required layers are always listed.  Four of them have a Phase-3
renderer (Tracks, Stations, Platforms, Speed); the remaining four are shown as
**visibly disabled** with the reason stated in the widget - they are never drawn
or faked:

* Signals - the signalling catalogue exists but has no Phase-3 renderer;
* TVPs/Resources - ``resource_id`` values are stored but not resolved;
* Routes - ``train_paths`` holds no Phase-3 renderer;
* Simulation Occupancy - no simulation engine exists (out of programme scope).
"""

from __future__ import annotations

from typing import Any, Callable, Optional

import ipywidgets as widgets

from ..app.project_controller import ProjectController
from ..models.enums import Severity
from . import formatting as fmt
from . import schematic_render
from . import svg_render
from .editing import InfrastructureEditor
from .project_page import panel_box


class SchematicView:
    """Interactive schematic of one infrastructure layer."""

    def __init__(
        self,
        controller: ProjectController,
        *,
        editor: Optional[InfrastructureEditor] = None,
        on_status: Optional[Callable[[str], None]] = None,
        on_open_object: Optional[Callable[[str, str], None]] = None,
        title: str = "Infrastructure schematic",
    ) -> None:
        self._controller = controller
        self._editor = editor if editor is not None else InfrastructureEditor(controller)
        self._on_status = on_status
        self._on_open_object = on_open_object
        self._selected_id = ""

        self._layer_flags: dict[str, widgets.Checkbox] = {}
        layer_rows: list[widgets.Widget] = []
        for name in schematic_render.SCHEMATIC_LAYERS:
            active = name in schematic_render.ACTIVE_LAYERS
            checkbox = widgets.Checkbox(
                value=active,
                description=name,
                disabled=not active,
                indent=False,
                layout=widgets.Layout(width="240px"),
                tooltip=(
                    f"Layer '{name}' is rendered from the canonical model."
                    if active
                    else f"Layer '{name}' is inactive: "
                    f"{schematic_render.INACTIVE_LAYER_REASONS[name]}"
                ),
            )
            checkbox.observe(
                lambda change, layer=name: self._handle_layer(layer, change), names="value"
            )
            self._layer_flags[name] = checkbox

            suffix = (
                ""
                if active
                else f" - DISABLED ({schematic_render.INACTIVE_LAYER_REASONS[name]})"
            )
            layer_rows.append(
                widgets.HBox(
                    [
                        checkbox,
                        widgets.HTML(
                            f'<div style="font-size:10px;color:{fmt.PALETTE["muted"]};padding-top:6px;">'
                            f"{fmt.esc(suffix)}</div>"
                        ),
                    ]
                )
            )

        self._layer_state = widgets.HTML(value="")

        self._svg_host = widgets.HTML(value="")
        self._caption = widgets.HTML(value="")
        self._counts = widgets.HTML(value="")
        self._open_note = widgets.HTML(value="")

        self._target_select = widgets.Select(
            options=[],
            rows=10,
            layout=widgets.Layout(width="360px"),
            description="Object:",
        )
        self._open_button = widgets.Button(
            description="Open in editor",
            layout=widgets.Layout(width="150px"),
            tooltip="Switch to the editor sub-tab that owns the selected object and focus its row.",
        )
        self._open_button.on_click(self._handle_open)
        self._target_select.observe(self._handle_select, names="value")

        self._widget = panel_box(
            title,
            [
                widgets.HBox(
                    [
                        widgets.VBox(
                            [
                                widgets.HTML(
                                    f'<div style="font-size:12px;font-weight:700;color:{fmt.PALETTE["navy"]};">Layers</div>'
                                ),
                                *layer_rows,
                                self._layer_state,
                            ],
                            layout=widgets.Layout(width="560px"),
                        ),
                        widgets.VBox(
                            [
                                widgets.HTML(
                                    f'<div style="font-size:12px;font-weight:700;color:{fmt.PALETTE["navy"]};">Objects (click surface)</div>'
                                ),
                                widgets.HBox([self._target_select, self._open_button]),
                                self._open_note,
                            ]
                        ),
                    ],
                    layout=widgets.Layout(align_items="flex-start", flex_flow="row wrap"),
                ),
                self._caption,
                self._svg_host,
                self._counts,
            ],
            subtitle="generated from the canonical model - no separate drawing definition",
        )
        self.refresh()

    @property
    def widget(self) -> widgets.Widget:
        """Return the root widget of the schematic view."""
        return self._widget

    def layer_flags(self) -> dict[str, bool]:
        """Return the current visibility flag of every layer."""
        return {name: box.value for name, box in self._layer_flags.items()}

    def layer_states(self) -> dict[str, str]:
        """Return ACTIVE/INACTIVE per layer (the honest state, not the checkbox)."""
        return {
            name: ("ACTIVE" if name in schematic_render.ACTIVE_LAYERS else "INACTIVE")
            for name in schematic_render.SCHEMATIC_LAYERS
        }

    def inactive_layers(self) -> tuple[str, ...]:
        """Return the layers that have no Phase-3 renderer."""
        return tuple(
            name
            for name in schematic_render.SCHEMATIC_LAYERS
            if name not in schematic_render.ACTIVE_LAYERS
        )

    def selected_id(self) -> str:
        """Return the id currently selected on the click surface."""
        return self._selected_id

    def drawing(self) -> schematic_render.SchematicDrawing:
        """Return the drawing currently displayed."""
        return self._drawing

    def _handle_layer(self, layer: str, change: dict[str, Any]) -> None:
        """Re-render when a layer checkbox changes."""
        del change
        if layer not in schematic_render.ACTIVE_LAYERS:
            return
        if self._on_status is not None:
            self._on_status(f"schematic layer '{layer}' set to {self._layer_flags[layer].value}")
        self.refresh()

    def _handle_select(self, change: dict[str, Any]) -> None:
        """Record a selection made on the click surface."""
        del change
        self._selected_id = self._target_select.value or ""
        self.refresh()

    def _handle_open(self, _button: widgets.Button) -> None:
        """Open the selected object in its editor (when a target is selected)."""
        if not self._selected_id:
            if self._on_status is not None:
                self._on_status("schematic: no object selected")
            return
        target = self._drawing.target_for(self._selected_id)
        kind = target.kind if target is not None else ""
        if self._on_open_object is not None:
            self._on_open_object(kind, self._selected_id)

    def select_object(self, object_id: str) -> None:
        """Select an object programmatically (used by the validation summary)."""
        self._selected_id = object_id
        self.refresh()

    def refresh(self) -> None:
        """Re-render the schematic from the working document."""
        layer = self._editor.layer()
        errors, codes = self._error_marks()
        drawing = schematic_render.render_schematic(
            layer,
            layers=self.layer_flags(),
            error_ids=errors,
            error_codes=codes,
            selected_id=self._selected_id,
            direction=self._controller.direction.value,
        )
        self._drawing = drawing

        self._svg_host.value = (
            '<div style="overflow-x:auto;width:100%;">' + drawing.svg + "</div>"
        )

        options = [
            (f"{target.object_id}  ({target.kind})", target.object_id)
            for target in drawing.hit_targets
        ]
        self._target_select.options = options
        if self._selected_id and any(value == self._selected_id for _label, value in options):
            self._target_select.value = self._selected_id

        states = self.layer_states()
        self._layer_state.value = fmt.section_note_html(
            "Layer states: "
            + ", ".join(f"{name}={state}" for name, state in states.items())
            + ". Disabled layers have no Phase-3 renderer and are not faked."
        )
        self._caption.value = fmt.section_note_html(
            f"Direction: {self._controller.direction.value}"
            " (the schematic itself is direction independent; the direction only labels the drawing). Drawn: "
            + ", ".join(f"{kind}: {count}" for kind, count in sorted(drawing.counts.items()))
            + ". Chainage range "
            + f"{drawing.chainage_range[0]:g} - {drawing.chainage_range[1]:g} km."
        )

        count_rows: list[tuple[str, str, str]] = []
        for kind, count in sorted(drawing.counts.items()):
            singular = {
                "nodes": "node",
                "observation_points": "observation_point",
                "platforms": "platform",
                "speed_restrictions": "speed_restriction",
                "stations": "station",
                "stopping_marks": "stopping_mark",
                "tracks": "track",
            }.get(kind, kind)
            count_rows.append(
                (kind, str(count), schematic_render.KIND_TO_CATALOGUE.get(singular, "-"))
            )
        self._counts.value = fmt.data_table_html(
            ("Element", "Drawn count", "Source catalogue"),
            tuple(count_rows),
            empty_text="Nothing to draw in the selected layers.",
        )

        self._open_note.value = fmt.section_note_html(
            f"{len(drawing.hit_targets)} object(s) selectable. Every drawn element carries "
            "data-object-id and is listed in the 'Object' control above; choose one and press "
            "'Open in editor' to jump to its row (or use the validation summary’s focus action)."
        )

    def _error_marks(self) -> tuple[tuple[str, ...], dict[str, str]]:
        """Return the ids (and codes) of objects carrying ERROR diagnostics."""
        result = (
            self._controller.draft_result
            if self._controller.draft_pending
            else self._controller.validation
        )
        if result is None:
            return (), {}
        ids: list[str] = []
        codes: dict[str, str] = {}
        for diagnostic in result.diagnostics:
            if diagnostic.severity is not Severity.ERROR:
                continue
            object_id = diagnostic.object_id
            if not object_id:
                continue
            ids.append(object_id)
            codes.setdefault(object_id, diagnostic.code)
        return tuple(dict.fromkeys(ids)), codes


class SchematicPage:
    """The Schematic sub-tab: the schematic view plus its legend."""

    def __init__(
        self,
        controller: ProjectController,
        *,
        editor: Optional[InfrastructureEditor] = None,
        on_status: Optional[Callable[[str], None]] = None,
        on_open_object: Optional[Callable[[str, str], None]] = None,
    ) -> None:
        self._editor = editor if editor is not None else InfrastructureEditor(controller)

        self.view = SchematicView(
            controller,
            editor=self._editor,
            on_status=on_status,
            on_open_object=on_open_object,
        )

        self._legend = widgets.HTML(
            svg_render.legend_svg(
                [
                    ("track", svg_render.PALETTE["track"]),
                    ("station", svg_render.PALETTE["station"]),
                    ("platform", svg_render.PALETTE["platform"]),
                    ("node / stopping mark", svg_render.PALETTE["node"]),
                    ("speed restriction", svg_render.PALETTE["speed"]),
                    ("selected object", svg_render.PALETTE["selection"]),
                    ("ERROR mark (text '!')", svg_render.PALETTE["error"]),
                ],
                width=980,
                title="Schematic legend",
            )
        )
        self._status_note = widgets.HTML(
            fmt.message_html(
                "The schematic is a read-only view generated from the canonical model. "
                "Editing happens in the catalogue sub-tabs; nothing can be changed by "
                "clicking the drawing.",
                severity=Severity.INFO,
            )
        )
        self._widget = widgets.VBox([self._status_note, self.view.widget, self._legend])
        self.refresh()

    @property
    def widget(self) -> widgets.Widget:
        """Return the root widget of the sub-tab."""
        return self._widget

    def refresh(self) -> None:
        """Re-render the schematic view."""
        self.view.refresh()

    def focus(self, object_id: str) -> None:
        """Select an object on the schematic (click-to-focus entry point)."""
        self.view.select_object(object_id)


def schematic_widget(
    controller: ProjectController,
    *,
    editor: Optional[InfrastructureEditor] = None,
    on_status: Optional[Callable[[str], None]] = None,
    on_open_object: Optional[Callable[[str, str], None]] = None,
) -> SchematicView:
    """Return a schematic view bound to *controller*."""
    return SchematicView(
        controller, editor=editor, on_status=on_status, on_open_object=on_open_object
    )
