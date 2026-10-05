"""Validation & Audit page: status, counts, diagnostics table, hashes and versions."""

from __future__ import annotations

from typing import Callable, Optional, Sequence

import ipywidgets as widgets

from ..app.project_controller import ProjectController
from ..models.diagnostics import Diagnostic
from ..models.enums import DiagnosticCategory, Severity
from ..version import APP_VERSION, DEFAULT_PROJECT_SCHEMA_VERSION, SUPPORTED_PROJECT_SCHEMA_VERSIONS
from . import formatting as fmt
from .project_page import panel_box

#: Filter option for "no filter applied".
_ALL = "All"


def _filter_label(text: str) -> widgets.HTML:
    """Return a small muted label widget for the filter row."""
    return widgets.HTML(
        f'<div style="font-size:12px;color:{fmt.PALETTE["muted"]};'
        f'font-family:Helvetica,Arial,sans-serif;padding-top:5px;">{fmt.esc(text)}</div>'
    )


class ValidationAuditPage:
    """The Phase-1 Validation & Audit page."""

    def __init__(self, controller: ProjectController) -> None:
        self._controller = controller
        self._unsubscribe: Optional[Callable[[], None]] = None
        self._build()
        self._unsubscribe = controller.subscribe(self.refresh)
        self.refresh()

    # -- construction ------------------------------------------------------
    def _build(self) -> None:
        self._status_html = widgets.HTML(value="")
        self._counts_html = widgets.HTML(value="")
        self._table_html = widgets.HTML(value="")
        self._state_html = widgets.HTML(value="")
        self._hashes_html = widgets.HTML(value="")

        self._severity_filter = widgets.Dropdown(
            options=[_ALL, Severity.ERROR.value, Severity.WARNING.value, Severity.INFO.value],
            value=_ALL,
            layout=widgets.Layout(width="120px", margin="0px 12px 0px 0px"),
        )
        self._category_filter = widgets.Dropdown(
            options=[_ALL, *[category.value for category in DiagnosticCategory]],
            value=_ALL,
            layout=widgets.Layout(width="170px", margin="0px 12px 0px 0px"),
        )
        self._search = widgets.Text(
            value="",
            placeholder="code, object id or message text",
            continuous_update=False,
            layout=widgets.Layout(width="320px", margin="0px 12px 0px 0px"),
        )
        for control in (self._severity_filter, self._category_filter, self._search):
            control.observe(self._on_filter_changed, names="value")

        filters = widgets.HBox(
            [
                _filter_label("Severity"),
                self._severity_filter,
                _filter_label("Category"),
                self._category_filter,
                _filter_label("Search"),
                self._search,
            ],
            layout=widgets.Layout(flex_flow="row wrap", align_items="center"),
        )
        self._filter_note = widgets.HTML(value="")

        not_validated_note = widgets.HTML(
            f'<div style="font-size:11px;color:{fmt.PALETTE["muted"]};'
            'font-family:Helvetica,Arial,sans-serif;">'
            "Phase-1 validation covers structure, identifiers, the chainage reference system and "
            "enumerations. Railway topology, signalling, physics and headway semantics are "
            "deliberately not validated yet. The project model is validated through its own "
            "canonical serialization, so this audit describes exactly what would be exported."
            "</div>"
        )

        self._widget = widgets.VBox(
            [
                panel_box("Validation status", [self._status_html, self._counts_html]),
                panel_box(
                    "Diagnostics",
                    [filters, self._filter_note, self._table_html, not_validated_note],
                    subtitle="structured findings with stable codes",
                ),
                panel_box("Project state and hashes", [self._state_html]),
                panel_box(
                    "Version information",
                    [
                        self._hashes_html,
                        widgets.HTML(
                            fmt.kv_table_html(
                                [
                                    ("Application version", APP_VERSION),
                                    (
                                        "Supported project schema versions",
                                        ", ".join(SUPPORTED_PROJECT_SCHEMA_VERSIONS),
                                    ),
                                    (
                                        "Default schema version (new projects)",
                                        DEFAULT_PROJECT_SCHEMA_VERSION,
                                    ),
                                    (
                                        "Assurance scope of this run",
                                        self._controller.state.assurance_scope
                                        or "(not determined)",
                                    ),
                                    (
                                        "Result hashes",
                                        "Prepared but not implemented - simulation results are "
                                        "outside Phase 1.",
                                    ),
                                ]
                            )
                        ),
                    ],
                ),
            ],
            layout=widgets.Layout(margin="8px 0px 0px 0px"),
        )

    # -- events ------------------------------------------------------------
    def _on_filter_changed(self, _change: dict[str, object]) -> None:
        """Re-render the diagnostics table when a filter changes."""
        self._render_table()

    # -- rendering ---------------------------------------------------------
    def refresh(self) -> None:
        """Re-render the page from the current controller state."""
        state = self._controller.state
        validation = self._controller.validation

        tone = fmt.tone_for_status(state.validation_status)
        freshness_tone = "warn" if state.modified_since_validation else (
            "ok" if state.validation_status else "muted"
        )
        status_text = state.validation_status or "NOT YET VALIDATED"
        status_bits = [
            fmt.badge(f"STATUS: {status_text}", tone),
            fmt.badge(f"FRESHNESS: {state.freshness_text}", freshness_tone),
        ]
        self._status_html.value = (
            '<div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;'
            'font-family:Helvetica,Arial,sans-serif;">' + "".join(status_bits) + "</div>"
        )

        if validation is None:
            counts_body = (
                f'<div style="font-size:12px;color:{fmt.PALETTE["muted"]};'
                'font-family:Helvetica,Arial,sans-serif;">No validation has been run in this '
                "session yet.</div>"
            )
        else:
            counts_body = fmt.summary_grid_html(
                [
                    ("Errors", validation.error_count),
                    ("Warnings", validation.warning_count),
                    ("Info items", validation.info_count),
                ],
                columns=3,
            )
        self._counts_html.value = counts_body

        self._render_table()
        self._state_html.value = fmt.kv_table_html(self._controller.state_rows(), monospace_values=True)
        self._hashes_html.value = fmt.kv_table_html(
            [
                ("Current project hash (SHA-256)", state.current_project_hash or "(no project)"),
                ("Last validated hash (SHA-256)", state.last_validated_hash or "(not validated yet)"),
                ("Hash scope", "canonical project content only - UI/direction state is excluded"),
            ],
            monospace_values=True,
        )

    def _render_table(self) -> None:
        """Render the (filtered) diagnostics table and its filter note."""
        diagnostics: Sequence[Diagnostic] = self._controller.diagnostics
        filtered = [d for d in diagnostics if self._passes_filters(d)]
        total = len(diagnostics)
        shown = len(filtered)
        if total == 0:
            note = "No diagnostics recorded."
        elif shown == total:
            note = f"Showing all {total} diagnostic(s)."
        else:
            note = f"Showing {shown} of {total} diagnostic(s) with the current filters."
        self._filter_note.value = fmt.message_html(note, severity=Severity.INFO)
        self._table_html.value = fmt.diagnostics_table_html(filtered)

    def _passes_filters(self, diagnostic: Diagnostic) -> bool:
        """Return whether a diagnostic passes the current filter controls."""
        severity = self._severity_filter.value
        if severity != _ALL and diagnostic.severity.value != severity:
            return False
        category = self._category_filter.value
        if category != _ALL and diagnostic.category.value != category:
            return False
        needle = (self._search.value or "").strip().lower()
        if needle:
            haystack = " ".join(
                [
                    diagnostic.code,
                    diagnostic.object_id or "",
                    diagnostic.message,
                    diagnostic.suggested_action or "",
                ]
            ).lower()
            if needle not in haystack:
                return False
        return True

    @property
    def widget(self) -> widgets.Widget:
        """Return the root widget of this page."""
        return self._widget
