"""Presentation-only SVG helpers for the Phase-3 previews and schematic.

Everything in this module is **drawing**, not engineering: it maps numbers that the
package layer already produced (preview series, chainages, element ids) onto pixel
coordinates and emits SVG text.  The module deliberately contains no reference to
the project model, the controller or any validation rule, so it cannot introduce a
calculation into the editing path.

The Phase-3 rule §I ("the only derived values permitted in the UI") is honoured by
keeping the engineering derivations in
:mod:`railway_headway_sim.infrastructure.preview_series` and the drawing here.
"""

from __future__ import annotations

import html
from dataclasses import dataclass
from typing import Iterable, Optional, Sequence

#: Default drawing palette (text is always added next to colour - never colour alone).
PALETTE: dict[str, str] = {
    "ink": "#1B1B1B",
    "muted": "#5A6472",
    "grid": "#DDE3EA",
    "axis": "#94A3B8",
    "track": "#20507E",
    "station": "#0E7490",
    "platform": "#7C3AED",
    "node": "#0F766E",
    "speed": "#B45309",
    "curve": "#BE185D",
    "elevation": "#1D4ED8",
    "gradient": "#047857",
    "error": "#B91C1C",
    "warn": "#B45309",
    "ok": "#15803D",
    "selection": "#111827",
}


def esc(value: object) -> str:
    """Escape text for safe inclusion in SVG/HTML."""
    return html.escape(str(value), quote=True)


@dataclass(frozen=True)
class ChartBounds:
    """Pixel bounds and value ranges of one chart."""

    width: int = 900
    height: int = 130
    left: int = 60
    right: int = 20
    top: int = 14
    bottom: int = 26

    @property
    def plot_width(self) -> int:
        """Return the drawable width in pixels."""
        return self.width - self.left - self.right

    @property
    def plot_height(self) -> int:
        """Return the drawable height in pixels."""
        return self.height - self.top - self.bottom


def _scale(value: float, low: float, high: float, start_px: float, end_px: float) -> float:
    """Map *value* from ``[low, high]`` onto ``[start_px, end_px]`` (drawing only)."""
    if high <= low:
        return start_px
    ratio = (value - low) / (high - low)
    return start_px + ratio * (end_px - start_px)


def _fmt(value: Optional[float], digits: int = 1) -> str:
    """Format a number for a chart label."""
    if value is None:
        return "n/a"
    return f"{value:.{digits}f}"


def chart_frame(
    bounds: ChartBounds,
    *,
    title: str,
    subtitle: str = "",
    low: float,
    high: float,
    unit: str,
    ticks: int = 6,
) -> list[str]:
    """Return the SVG lines of a chart frame with grid and unit-labelled axis."""
    lines: list[str] = []
    lines.append(f'<rect x="0" y="0" width="{bounds.width}" height="{bounds.height}" fill="#FFFFFF"/>')
    title_text = esc(title) + (f"  - {esc(subtitle)}" if subtitle else "")
    lines.append(
        f'<text x="{bounds.left}" y="11" font-size="11" font-weight="700" fill="{PALETTE["ink"]}" '
        f'font-family="Helvetica,Arial,sans-serif">{title_text}</text>'
    )
    for step in range(ticks + 1):
        ratio = step / ticks
        x_px = bounds.left + ratio * bounds.plot_width
        value = low + ratio * (high - low)
        lines.append(
            f'<line x1="{x_px:.1f}" y1="{bounds.top}" x2="{x_px:.1f}" '
            f'y2="{bounds.top + bounds.plot_height}" stroke="{PALETTE["grid"]}" stroke-width="1"/>'
        )
        lines.append(
            f'<text x="{x_px:.1f}" y="{bounds.height - 8}" font-size="9" fill="{PALETTE["muted"]}" '
            f'text-anchor="middle" font-family="Helvetica,Arial,sans-serif">{value:g}</text>'
        )
    lines.append(
        f'<text x="{bounds.left}" y="{bounds.height - 8}" font-size="9" fill="{PALETTE["muted"]}" '
        f'text-anchor="start" font-family="Helvetica,Arial,sans-serif">chainage [km]</text>'
    )
    lines.append(
        f'<text x="{bounds.left - 6}" y="{bounds.top + 10}" font-size="9" fill="{PALETTE["muted"]}" '
        f'text-anchor="end" font-family="Helvetica,Arial,sans-serif">{esc(unit)}</text>'
    )
    return lines


def line_chart(
    samples: Sequence[tuple[float, float]],
    *,
    low_chainage: float,
    high_chainage: float,
    low_value: float,
    high_value: float,
    title: str,
    unit: str,
    colour: str = PALETTE["elevation"],
    subtitle: str = "",
    bounds: Optional[ChartBounds] = None,
) -> str:
    """Return an SVG line chart of ``(chainage_km, value)`` samples (presentation only)."""
    box = bounds or ChartBounds()
    lines = chart_frame(
        box, title=title, subtitle=subtitle, low=low_chainage, high=high_chainage, unit=unit
    )
    if len(samples) >= 2:
        points = " ".join(
            f"{_scale(chainage, low_chainage, high_chainage, box.left, box.left + box.plot_width):.1f},"
            f"{_scale(value, low_value, high_value, box.top + box.plot_height, box.top):.1f}"
            for chainage, value in samples
        )
        lines.append(
            f'<polyline points="{points}" fill="none" stroke="{colour}" stroke-width="2"/>'
        )
    elif len(samples) == 1:
        chainage, value = samples[0]
        x_px = _scale(chainage, low_chainage, high_chainage, box.left, box.left + box.plot_width)
        y_px = _scale(value, low_value, high_value, box.top + box.plot_height, box.top)
        lines.append(f'<circle cx="{x_px:.1f}" cy="{y_px:.1f}" r="3" fill="{colour}"/>')
    else:
        lines.append(
            f'<text x="{box.left + 8}" y="{box.top + 18}" font-size="10" fill="{PALETTE["muted"]}" '
            f'font-family="Helvetica,Arial,sans-serif">no data</text>'
        )
    lines.append("</svg>")
    return "\n".join(lines)


def segment_chart(
    segments: Iterable[tuple[float, float, Optional[float], str]],
    *,
    low_chainage: float,
    high_chainage: float,
    low_value: float,
    high_value: float,
    title: str,
    unit: str,
    colour: str = PALETTE["speed"],
    subtitle: str = "",
    bounds: Optional[ChartBounds] = None,
) -> str:
    """Return an SVG step chart of ``(start_km, end_km, value, label)`` segments."""
    box = bounds or ChartBounds()
    lines = chart_frame(
        box, title=title, subtitle=subtitle, low=low_chainage, high=high_chainage, unit=unit
    )
    any_segment = False
    for start_km, end_km, value, label in segments:
        if value is None:
            continue
        any_segment = True
        x1 = _scale(start_km, low_chainage, high_chainage, box.left, box.left + box.plot_width)
        x2 = _scale(end_km, low_chainage, high_chainage, box.left, box.left + box.plot_width)
        y = _scale(value, low_value, high_value, box.top + box.plot_height, box.top)
        lines.append(
            f'<line x1="{x1:.1f}" y1="{y:.1f}" x2="{x2:.1f}" y2="{y:.1f}" stroke="{colour}" '
            f'stroke-width="3"/>'
        )
        lines.append(
            f'<text x="{x1 + 3:.1f}" y="{y - 4:.1f}" font-size="9" fill="{PALETTE["ink"]}" '
            f'font-family="Helvetica,Arial,sans-serif">{esc(label)}</text>'
        )
    if not any_segment:
        lines.append(
            f'<text x="{box.left + 8}" y="{box.top + 18}" font-size="10" fill="{PALETTE["muted"]}" '
            f'font-family="Helvetica,Arial,sans-serif">no segment applies to this direction</text>'
        )
    lines.append("</svg>")
    return "\n".join(lines)


def bar_chart(
    bars: Sequence[tuple[float, float, float, str]],
    *,
    low_chainage: float,
    high_chainage: float,
    low_value: float,
    high_value: float,
    title: str,
    unit: str,
    colour: str = PALETTE["curve"],
    subtitle: str = "",
    bounds: Optional[ChartBounds] = None,
) -> str:
    """Return an SVG bar chart of ``(start_km, end_km, value, label)`` bars."""
    box = bounds or ChartBounds()
    lines = chart_frame(
        box, title=title, subtitle=subtitle, low=low_chainage, high=high_chainage, unit=unit
    )
    base = box.top + box.plot_height
    for start_km, end_km, value, label in bars:
        x1 = _scale(start_km, low_chainage, high_chainage, box.left, box.left + box.plot_width)
        x2 = _scale(end_km, low_chainage, high_chainage, box.left, box.left + box.plot_width)
        y = _scale(value, low_value, high_value, base, box.top)
        lines.append(
            f'<rect x="{x1:.1f}" y="{y:.1f}" width="{max(x2 - x1, 1.0):.1f}" '
            f'height="{max(base - y, 1.0):.1f}" fill="{colour}" fill-opacity="0.55" '
            f'stroke="{colour}" stroke-width="1"/>'
        )
        lines.append(
            f'<text x="{x1 + 2:.1f}" y="{max(y - 3, box.top + 9):.1f}" font-size="9" '
            f'fill="{PALETTE["ink"]}" font-family="Helvetica,Arial,sans-serif">{esc(label)}</text>'
        )
    lines.append("</svg>")
    return "\n".join(lines)


def svg_open(width: int, height: int, *, title: str = "") -> str:
    """Return the opening SVG tag (with an accessible title)."""
    title_tag = f"<title>{esc(title)}</title>" if title else ""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img">{title_tag}'
    )


def message_svg(text: str, *, width: int = 900, height: int = 60) -> str:
    """Return a small SVG that carries a text message (used for empty states)."""
    return (
        svg_open(width, height, title=text)
        + f'<rect x="0" y="0" width="{width}" height="{height}" fill="#FFFFFF"/>'
        + f'<text x="8" y="{height // 2}" font-size="11" fill="{PALETTE["muted"]}" '
        + 'font-family="Helvetica,Arial,sans-serif">'
        + esc(text)
        + "</text></svg>"
    )


def legend_svg(
    entries: Sequence[tuple[str, str]],
    *,
    width: int = 900,
    height: int = 26,
    title: str = "",
) -> str:
    """Return an SVG legend with a colour swatch and a text label per entry."""
    parts: list[str] = [svg_open(width, height, title=title or "legend")]
    x = 8
    for label, colour in entries:
        parts.append(f'<rect x="{x}" y="7" width="12" height="12" fill="{colour}"/>')
        parts.append(
            f'<text x="{x + 17}" y="17" font-size="10" fill="{PALETTE["ink"]}" '
            f'font-family="Helvetica,Arial,sans-serif">{esc(label)}</text>'
        )
        x += 22 + 7 * len(label)
    parts.append("</svg>")
    return "\n".join(parts)
