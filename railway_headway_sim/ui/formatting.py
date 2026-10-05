"""Pure HTML/text formatting helpers for the Colab UI.

This module contains **no** widget code and **no** engineering logic: it turns
model/controller data into HTML strings. Keeping it pure makes it testable
without a notebook front-end.

Visual language (never colour alone - every status also carries text):

* dark railway blue - normal engineering headers
* green             - VALID
* amber             - WARNING / attention / modified
* red               - ERROR / INVALID
"""

from __future__ import annotations

import html
from typing import Iterable, Optional, Sequence

from ..models.diagnostics import Diagnostic
from ..models.enums import ChainageDirection, Direction, Severity, ValidationStatus
from ..models.project import Project

#: Application palette (single place for the Phase-1 visual language).
PALETTE: dict[str, str] = {
    "navy": "#0B2E4F",
    "navy_dark": "#071F36",
    "steel": "#1E5A8A",
    "steel_light": "#E7EFF6",
    "green": "#1B7F4B",
    "amber": "#A96A00",
    "red": "#B3261E",
    "ink": "#12212E",
    "muted": "#5A6B7B",
    "line": "#C9D4DE",
    "panel": "#F7FAFC",
    "white": "#FFFFFF",
}

#: Tone -> colour key.
TONE_COLOURS: dict[str, str] = {
    "info": PALETTE["steel"],
    "ok": PALETTE["green"],
    "warn": PALETTE["amber"],
    "error": PALETTE["red"],
    "muted": PALETTE["muted"],
    "navy": PALETTE["navy"],
}

#: Validation status -> tone.
STATUS_TONES: dict[str, str] = {
    ValidationStatus.VALID.value: "ok",
    ValidationStatus.VALID_WITH_WARNINGS.value: "warn",
    ValidationStatus.INVALID.value: "error",
}

#: Severity -> tone.
SEVERITY_TONES: dict[str, str] = {
    Severity.INFO.value: "info",
    Severity.WARNING.value: "warn",
    Severity.ERROR.value: "error",
}

#: Chainage direction -> friendly text.
_CHAINAGE_SENSE: dict[str, str] = {
    ChainageDirection.INCREASING_CHAINAGE.value: "increasing chainage",
    ChainageDirection.DECREASING_CHAINAGE.value: "decreasing chainage",
}


def esc(value: object) -> str:
    """HTML-escape *value* for safe embedding in generated markup."""
    return html.escape("" if value is None else str(value), quote=True)


def tone_for_status(status: Optional[str]) -> str:
    """Return the palette tone of a validation status string."""
    if not status:
        return "muted"
    return STATUS_TONES.get(str(status), "muted")


def tone_for_severity(severity: Severity) -> str:
    """Return the palette tone of a diagnostic severity."""
    return SEVERITY_TONES.get(getattr(severity, "value", str(severity)), "muted")


def badge(text: str, tone: str = "info", *, small: bool = False) -> str:
    """Return an inline HTML status badge (colour + text)."""
    colour = TONE_COLOURS.get(tone, PALETTE["steel"])
    size = "10px" if small else "11px"
    return (
        f'<span style="display:inline-block;background:{colour};color:#fff;border-radius:10px;'
        f'padding:2px 10px;font-size:{size};font-weight:600;letter-spacing:0.04em;'
        f'white-space:nowrap;">{esc(text)}</span>'
    )


def outline_chip(text: str, tone: str = "navy") -> str:
    """Return a light outlined chip (used for versions and identifiers)."""
    colour = TONE_COLOURS.get(tone, PALETTE["navy"])
    return (
        f'<span style="display:inline-block;border:1px solid {colour};color:{colour};'
        f'border-radius:10px;padding:1px 9px;font-size:11px;font-weight:600;'
        f'background:#fff;white-space:nowrap;">{esc(text)}</span>'
    )


def direction_label(project: Optional[Project], direction: Direction) -> str:
    """Return the friendly label of a direction, e.g. ``FORWARD · Alpha → Delta``."""
    origin, end = terminal_names(project)
    if direction is Direction.FORWARD:
        return f"FORWARD · {origin} → {end}"
    if direction is Direction.REVERSE:
        return f"REVERSE · {end} → {origin}"
    return direction.value


def direction_caption(project: Optional[Project], direction: Direction) -> str:
    """Return a secondary line describing what a direction means for this project."""
    start, end = chainage_bounds_text(project)
    sense = _chainage_sense_for(project, direction)
    return f"{sense} · chainage {start} → {end}"


def terminal_names(project: Optional[Project]) -> tuple[str, str]:
    """Return ``(origin, end)`` terminal names with readable fallbacks."""
    if project is None:
        return ("chainage start", "chainage end")
    reference = project.reference_system
    origin = (reference.chainage_origin_name or "").strip() or "chainage start"
    end = (reference.chainage_end_name or "").strip() or "chainage end"
    return origin, end


def chainage_bounds_text(project: Optional[Project]) -> tuple[str, str]:
    """Return the chainage bounds as display strings."""
    if project is None:
        return ("(not set)", "(not set)")
    reference = project.reference_system
    unit = project.display_units.chainage or "km"
    start = "(not set)" if reference.chainage_start_km is None else f"{reference.chainage_start_km} {unit}"
    end = "(not set)" if reference.chainage_end_km is None else f"{reference.chainage_end_km} {unit}"
    return (start, end)


def _chainage_sense_for(project: Optional[Project], direction: Direction) -> str:
    """Return the chainage sense text of *direction* for *project*."""
    if project is None:
        return "increasing chainage" if direction is Direction.FORWARD else "decreasing chainage"
    reference = project.reference_system
    value = (
        reference.forward_direction if direction is Direction.FORWARD else reference.reverse_direction
    )
    key = getattr(value, "value", value)
    if isinstance(key, str) and key in _CHAINAGE_SENSE:
        return _CHAINAGE_SENSE[key]
    return "chainage sense not set"


# ---------------------------------------------------------------------------
# page fragments
# ---------------------------------------------------------------------------
def header_html(
    *,
    app_name: str,
    phase_text: str,
    project_name: str,
    chips: Sequence[tuple[str, str]],
    status_text: str,
    status_tone: str,
    freshness_text: str,
    freshness_tone: str,
    direction_text: str,
) -> str:
    """Build the application header strip (dark railway blue)."""
    chip_html = " ".join(outline_chip(text, tone) for text, tone in chips)
    return f"""
<div style="background:{PALETTE['navy']};color:#fff;border-radius:8px;padding:14px 18px;
            font-family:Helvetica,Arial,sans-serif;">
  <div style="display:flex;flex-wrap:wrap;align-items:baseline;gap:10px;">
    <div style="font-size:19px;font-weight:700;letter-spacing:0.01em;">{esc(app_name)}</div>
    <div style="font-size:12px;opacity:0.85;">{esc(phase_text)}</div>
  </div>
  <div style="margin-top:6px;font-size:13px;opacity:0.95;">
    Project: <b>{esc(project_name)}</b>
  </div>
  <div style="margin-top:9px;display:flex;flex-wrap:wrap;gap:8px;align-items:center;">
    {badge(status_text, status_tone)}
    {badge(freshness_text, freshness_tone)}
    {outline_chip('Direction: ' + direction_text, 'navy')}
    {chip_html}
  </div>
</div>
"""


def direction_bar_html(active_label: str, caption: str, note: str = "") -> str:
    """Build the caption row that sits under the direction buttons."""
    note_html = f'<div style="font-size:11px;color:{PALETTE["muted"]};margin-top:3px;">{esc(note)}</div>' if note else ""
    return f"""
<div style="border-left:4px solid {PALETTE['steel']};background:{PALETTE['steel_light']};
            padding:7px 11px;border-radius:4px;font-family:Helvetica,Arial,sans-serif;">
  <div style="font-size:13px;color:{PALETTE['ink']};">
    <b>Active direction:</b> {esc(active_label)}
    <span style="color:{PALETTE['muted']};">({esc(caption)})</span>
  </div>
  {note_html}
</div>
"""


def panel_header_html(title: str, *, tone: str = "navy", subtitle: str = "") -> str:
    """Render the header bar of a UI panel (used by the widget-based pages)."""
    colour = TONE_COLOURS.get(tone, PALETTE["navy"])
    subtitle_html = (
        f'<span style="font-weight:400;text-transform:none;letter-spacing:0;opacity:0.9;">'
        f"— {esc(subtitle)}</span>"
        if subtitle
        else ""
    )
    return (
        f'<div style="background:{colour};color:#fff;padding:6px 12px;font-size:12px;font-weight:700;'
        f'letter-spacing:0.05em;text-transform:uppercase;font-family:Helvetica,Arial,sans-serif;'
        f'border-radius:5px 5px 0 0;">{esc(title)} {subtitle_html}</div>'
    )


def panel(title: str, body_html: str, *, tone: str = "navy") -> str:
    """Wrap *body_html* in a titled panel."""
    return f"""
<div style="border:1px solid {PALETTE['line']};border-radius:6px;overflow:hidden;
            font-family:Helvetica,Arial,sans-serif;background:#fff;">
  {panel_header_html(title, tone=tone)}
  <div style="padding:11px 13px;">{body_html}</div>
</div>
"""


def kv_table_html(rows: Iterable[tuple[str, object]], *, monospace_values: bool = False) -> str:
    """Render key/value rows as a compact table."""
    body = "".join(
        f'<tr><td style="padding:3px 14px 3px 0;color:{PALETTE["muted"]};font-size:12px;'
        f'white-space:nowrap;vertical-align:top;">{esc(key)}</td>'
        f'<td style="padding:3px 0;color:{PALETTE["ink"]};font-size:12px;'
        f'{"font-family:monospace;word-break:break-all;" if monospace_values else ""}">'
        f"{esc(value)}</td></tr>"
        for key, value in rows
    )
    return f'<table style="border-collapse:collapse;">{body}</table>'


def summary_grid_html(rows: Sequence[tuple[str, int]], columns: int = 3) -> str:
    """Render object counts as a compact grid of tiles."""
    if not rows:
        return f'<div style="font-size:12px;color:{PALETTE["muted"]};">No project loaded.</div>'
    tiles = "".join(
        f'<div style="border:1px solid {PALETTE["line"]};border-radius:5px;padding:6px 9px;'
        f'background:{PALETTE["panel"]};">'
        f'<div style="font-size:11px;color:{PALETTE["muted"]};">{esc(label)}</div>'
        f'<div style="font-size:16px;font-weight:700;color:{PALETTE["ink"]};">{count}</div></div>'
        for label, count in rows
    )
    return (
        f'<div style="display:grid;grid-template-columns:repeat({columns},minmax(120px,1fr));'
        f'gap:7px;font-family:Helvetica,Arial,sans-serif;">{tiles}</div>'
    )


def data_table_html(
    headers: Sequence[str], rows: Sequence[Sequence[object]], *, empty_text: str = "No entries."
) -> str:
    """Render a simple read-only data table (used by the Phase-2 pages).

    Pure presentation: the caller supplies already-computed values; no
    engineering value is derived here.
    """
    if not rows:
        return (
            f'<div style="font-size:12px;color:{PALETTE["muted"]};font-family:Helvetica,Arial,sans-serif;">'
            f"{esc(empty_text)}</div>"
        )
    head = "".join(
        f'<th style="text-align:left;padding:4px 9px;font-size:11px;color:{PALETTE["navy"]};'
        f'border-bottom:1px solid {PALETTE["line"]};white-space:nowrap;">{esc(title)}</th>'
        for title in headers
    )
    body = "".join(
        "<tr>"
        + "".join(
            f'<td style="padding:4px 9px;font-size:11px;color:{PALETTE["ink"]};'
            f'font-family:monospace;vertical-align:top;white-space:nowrap;">{esc(value)}</td>'
            for value in row
        )
        + "</tr>"
        for row in rows
    )
    return (
        '<div style="overflow-x:auto;font-family:Helvetica,Arial,sans-serif;">'
        f'<table style="border-collapse:collapse;">'
        f'<tr style="background:{PALETTE["steel_light"]};">{head}</tr>{body}</table></div>'
    )


def section_note_html(text: str) -> str:
    """Render a small explanatory note under a panel."""
    return (
        f'<div style="font-size:11px;color:{PALETTE["muted"]};font-family:Helvetica,Arial,sans-serif;'
        f'margin-top:6px;">{esc(text)}</div>'
    )


def message_html(message: str, severity: Severity) -> str:
    """Render a status message line with a coloured accent and explicit severity text."""
    tone = tone_for_severity(severity)
    colour = TONE_COLOURS.get(tone, PALETTE["steel"])
    return (
        f'<div style="border-left:4px solid {colour};background:{PALETTE["panel"]};'
        f'padding:6px 10px;border-radius:4px;font-family:Helvetica,Arial,sans-serif;font-size:12px;'
        f'color:{PALETTE["ink"]};">'
        f'<b style="color:{colour};">{esc(getattr(severity, "value", severity))}</b> · {esc(message)}</div>'
    )


def diagnostics_table_html(diagnostics: Sequence[Diagnostic]) -> str:
    """Render the diagnostics list as a table (severity, code, category, object, ...)."""
    header = (
        f'<tr style="background:{PALETTE["steel_light"]};">'
        + "".join(
            f'<th style="text-align:left;padding:5px 8px;font-size:11px;color:{PALETTE["navy"]};'
            f'border-bottom:1px solid {PALETTE["line"]};white-space:nowrap;">{esc(title)}</th>'
            for title in ("Severity", "Code", "Category", "Object", "Message", "Suggested action")
        )
        + "</tr>"
    )
    if not diagnostics:
        return (
            f'<div style="font-size:12px;color:{PALETTE["green"]};font-family:Helvetica,Arial,sans-serif;">'
            "No diagnostics - nothing to report.</div>"
        )
    rows = []
    for diagnostic in diagnostics:
        tone = tone_for_severity(diagnostic.severity)
        rows.append(
            "<tr>"
            f'<td style="padding:5px 8px;vertical-align:top;">{badge(diagnostic.severity.value, tone, small=True)}</td>'
            f'<td style="padding:5px 8px;font-size:11px;font-family:monospace;vertical-align:top;'
            f'color:{PALETTE["ink"]};">{esc(diagnostic.code)}</td>'
            f'<td style="padding:5px 8px;font-size:11px;vertical-align:top;color:{PALETTE["muted"]};">'
            f"{esc(diagnostic.category.value)}</td>"
            f'<td style="padding:5px 8px;font-size:11px;font-family:monospace;vertical-align:top;'
            f'color:{PALETTE["ink"]};">{esc(diagnostic.object_id or "-")}</td>'
            f'<td style="padding:5px 8px;font-size:12px;vertical-align:top;color:{PALETTE["ink"]};">'
            f"{esc(diagnostic.message)}</td>"
            f'<td style="padding:5px 8px;font-size:11px;vertical-align:top;color:{PALETTE["muted"]};">'
            f"{esc(diagnostic.suggested_action or '-')}</td>"
            "</tr>"
        )
    return (
        '<div style="overflow-x:auto;font-family:Helvetica,Arial,sans-serif;">'
        f'<table style="border-collapse:collapse;width:100%;">{header}{"".join(rows)}</table></div>'
    )


def placeholder_html(title: str, planned_items: Sequence[str], phase_note: str) -> str:
    """Render a clearly-marked placeholder for a later-phase page."""
    items = "".join(f"<li>{esc(item)}</li>" for item in planned_items)
    return f"""
<div style="font-family:Helvetica,Arial,sans-serif;border:1px dashed {PALETTE['line']};
            border-radius:6px;padding:14px 16px;background:{PALETTE['panel']};">
  <div style="font-size:15px;font-weight:700;color:{PALETTE['navy']};">{esc(title)}</div>
  <div style="margin:8px 0;">{badge('PLANNED FOR LATER DEVELOPMENT PHASE', 'warn')}</div>
  <div style="font-size:12px;color:{PALETTE['ink']};">
    This page contains no engineering functionality yet. It performs no calculations and
    produces no results, and it does not create placeholder result values.
  </div>
  <div style="font-size:12px;color:{PALETTE['ink']};margin-top:8px;">
    <b>Planned content (not implemented):</b>
    <ul style="margin:4px 0 0 18px;">{items}</ul>
  </div>
  <div style="font-size:11px;color:{PALETTE['muted']};margin-top:8px;">{esc(phase_note)}</div>
</div>
"""


def border_layout_style(colour: str | None = None) -> dict[str, str]:
    """Return ``widgets.Layout`` keyword overrides for a 1px border.

    ipywidgets exposes ``border_top/left/right/bottom`` (there is no shorthand
    ``border`` trait), so panels are bordered per side. Passing an unsupported
    trait name would be silently dropped by traitlets, which is why the styles
    are centralised here.
    """
    line = f"1px solid {colour or PALETTE['line']}"
    return {
        "border_top": line,
        "border_left": line,
        "border_right": line,
        "border_bottom": line,
    }


def footer_html(rows: Sequence[tuple[str, object]]) -> str:
    """Render the footer/audit strip."""
    inner = "".join(
        f'<span style="margin-right:16px;font-size:11px;color:{PALETTE["muted"]};">'
        f"{esc(key)}: <b style=\"color:{PALETTE['ink']};font-weight:600;\">{esc(value)}</b></span>"
        for key, value in rows
    )
    return (
        f'<div style="border-top:1px solid {PALETTE["line"]};padding-top:7px;'
        f'font-family:Helvetica,Arial,sans-serif;">{inner}</div>'
    )
