"""Synchronised preview panels (Phase-3 §G5, §G8).

Both panels draw series that the package layer produced
(:mod:`railway_headway_sim.infrastructure.preview_series`); the widgets only call
the renderer.  They follow the application direction without modifying stored data:

* the geometry preview shows elevation, the gradient between adjacent elevation
  points and the stored curve radius;
* the speed preview shows the effective permissible speed per chainage for the
  selected direction, applying "most restrictive wins" to the restriction segments.

Neither panel displays a dynamics quantity (no speed profile, acceleration,
braking, time, occupation, headway or capacity value).
"""

from __future__ import annotations

from typing import Any, Sequence

import ipywidgets as widgets

from ..app.project_controller import ProjectController
from ..infrastructure import preview_series as series
from ..models.enums import Severity
from . import formatting as fmt
from . import svg_render
from .project_page import panel_box


def _bounds_for(values: Sequence[float], *, pad: float = 0.05) -> tuple[float, float]:
    """Return a padded ``(low, high)`` display range for drawing (presentation only)."""
    if not values:
        return 0.0, 1.0
    low = min(values)
    high = max(values)
    if high - low < 1e-9:
        span = max(abs(high), 1.0) * 0.1
        return low - span, high + span
    margin = (high - low) * pad
    return low - margin, high + margin


def _layer_of(project: Any) -> dict[str, Any]:
    """Return the raw infrastructure layer of a loaded project (empty when none)."""
    if project is None:
        return {}
    for layer in getattr(project, "infrastructure", None) or []:
        if isinstance(layer, dict):
            return layer
    return {}


class GeometryPreview:
    """Elevation / gradient / curvature preview of the loaded alignment."""

    def __init__(self, controller: ProjectController) -> None:
        self._controller = controller
        self._elevation = widgets.HTML(value="")
        self._gradient = widgets.HTML(value="")
        self._curvature = widgets.HTML(value="")
        self._caption = widgets.HTML(value="")
        self._table = widgets.HTML(value="")
        self._widget = panel_box(
            "Synchronised longitudinal preview",
            [self._caption, self._elevation, self._gradient, self._curvature, self._table],
            subtitle="elevation, gradient between adjacent points and stored curve radius",
        )
        self._unsubscribe = controller.subscribe(self.refresh)
        self.refresh()

    @property
    def widget(self) -> widgets.Widget:
        """Return the root widget of the preview."""
        return self._widget

    # -- data --------------------------------------------------------------
    def layer(self) -> dict[str, Any]:
        """Return the raw infrastructure layer of the loaded project."""
        return _layer_of(self._controller.project)

    def elevation_points(self) -> tuple[tuple[float, float], ...]:
        """Return the stored elevation points of the loaded layer."""
        points: list[Any] = []
        for profile in self.layer().get("vertical_profiles") or []:
            if isinstance(profile, dict):
                points.extend(profile.get("points") or [])
        return series.elevation_series(points)

    def gradient_segments(self) -> tuple[series.GradientSegment, ...]:
        """Return the gradient series for the current direction."""
        points: list[Any] = []
        for profile in self.layer().get("vertical_profiles") or []:
            if isinstance(profile, dict):
                points.extend(profile.get("points") or [])
        return series.gradient_segments(points, direction=self._controller.direction)

    def curvature_segments(self) -> tuple[series.CurvatureSegment, ...]:
        """Return the curvature series of the loaded layer."""
        return series.curvature_segments(self.layer().get("horizontal_geometry") or [])

    # -- rendering ---------------------------------------------------------
    def refresh(self) -> None:
        """Re-render all three charts for the current direction."""
        direction = self._controller.direction.value
        elevations = self.elevation_points()
        gradients = self.gradient_segments()
        curves = self.curvature_segments()
        chainages = [chainage for chainage, _ in elevations]
        low_chainage, high_chainage = _bounds_for(chainages)
        box = svg_render.ChartBounds()

        if elevations:
            low_value, high_value = _bounds_for([value for _, value in elevations])
            self._elevation.value = svg_render.line_chart(
                elevations,
                low_chainage=low_chainage,
                high_chainage=high_chainage,
                low_value=low_value,
                high_value=high_value,
                title="Elevation",
                unit="elevation [m]",
                subtitle=f"{direction} travel order, {len(elevations)} stored point(s)",
                bounds=box,
            )
        else:
            self._elevation.value = svg_render.message_svg("No vertical profile points stored.")

        if gradients:
            low_value, high_value = _bounds_for(
                [segment.gradient_permille for segment in gradients] + [0.0]
            )
            self._gradient.value = svg_render.segment_chart(
                [
                    (
                        segment.start_km,
                        segment.end_km,
                        segment.gradient_permille,
                        f"{segment.gradient_permille:+.1f} permille",
                    )
                    for segment in gradients
                ],
                low_chainage=low_chainage,
                high_chainage=high_chainage,
                low_value=low_value,
                high_value=high_value,
                title="Gradient between adjacent elevation points",
                unit="gradient [permille]",
                colour=svg_render.PALETTE["gradient"],
                subtitle=(
                    f"{direction} travel order (REVERSE flips the sign for display only; "
                    "stored values are unchanged)"
                ),
                bounds=box,
            )
        else:
            self._gradient.value = svg_render.message_svg(
                "No adjacent elevation points to derive a gradient from."
            )

        if curves:
            radii = [segment.radius_m for segment in curves if segment.radius_m]
            low_value, high_value = _bounds_for(radii or [1.0])
            self._curvature.value = svg_render.bar_chart(
                [
                    (
                        segment.start_km,
                        segment.end_km,
                        segment.radius_m or 0.0,
                        f"{segment.id} {segment.section_type}"
                        + (f" R{segment.radius_m:g}" if segment.radius_m else ""),
                    )
                    for segment in curves
                ],
                low_chainage=low_chainage,
                high_chainage=high_chainage,
                low_value=low_value,
                high_value=high_value,
                title="Curvature / stored curve radius",
                unit="radius [m]",
                colour=svg_render.PALETTE["curve"],
                subtitle="stored radius value, drawn by section",
                bounds=box,
            )
        else:
            self._curvature.value = svg_render.message_svg("No horizontal geometry sections stored.")

        self._caption.value = fmt.section_note_html(
            "Preview direction: "
            f"{direction}. Series are drawn from the stored catalogues; the only derived value "
            "is the gradient between adjacent elevation points. Switching the direction changes "
            "the display only - the project hash does not change."
        )
        self._table.value = fmt.data_table_html(
            ("Segment [km]", "Gradient [permille]", "Distance [km]"),
            tuple(
                (
                    f"{segment.start_km:g} - {segment.end_km:g}",
                    f"{segment.gradient_permille:+.2f}",
                    f"{segment.distance_km:g}",
                )
                for segment in gradients
            ),
            empty_text="No gradient segments.",
        )


class SpeedPreview:
    """Effective permissible speed vs chainage for the selected direction."""

    def __init__(self, controller: ProjectController) -> None:
        self._controller = controller
        self._chart = widgets.HTML(value="")
        self._caption = widgets.HTML(value="")
        self._table = widgets.HTML(value="")
        self._widget = panel_box(
            "Effective permissible speed",
            [self._caption, self._chart, self._table],
            subtitle="direction filter + most restrictive wins (stored values only)",
        )
        self._unsubscribe = controller.subscribe(self.refresh)
        self.refresh()

    @property
    def widget(self) -> widgets.Widget:
        """Return the root widget of the preview."""
        return self._widget

    def segments(self) -> tuple[series.SpeedSegment, ...]:
        """Return the effective speed segments for the current direction."""
        restrictions: list[Any] = []
        for layer in getattr(self._controller.project, "infrastructure", None) or []:
            if isinstance(layer, dict):
                restrictions.extend(layer.get("speed_restrictions") or [])
        return series.effective_speed_segments(
            restrictions, direction=self._controller.direction
        )

    def refresh(self) -> None:
        """Re-render the speed chart for the current direction."""
        direction = self._controller.direction.value
        segments = self.segments()
        chainages = [value for segment in segments for value in (segment.start_km, segment.end_km)]
        low_chainage, high_chainage = _bounds_for(chainages)
        speeds = [segment.speed_kmh for segment in segments if segment.speed_kmh is not None]
        low_value, high_value = _bounds_for(speeds or [0.0, 1.0])
        box = svg_render.ChartBounds()

        if segments:
            self._chart.value = svg_render.segment_chart(
                [
                    (segment.start_km, segment.end_km, segment.speed_kmh, f"{segment.speed_kmh:g} km/h")
                    for segment in segments
                ],
                low_chainage=low_chainage,
                high_chainage=high_chainage,
                low_value=low_value,
                high_value=high_value,
                title="Effective permissible speed",
                unit="speed [km/h]",
                subtitle=f"{direction} direction, {len(segments)} segment(s)",
                bounds=box,
            )
        else:
            self._chart.value = svg_render.message_svg(
                f"No speed restriction applies to the {direction} direction."
            )

        self._caption.value = fmt.section_note_html(
            f"Direction: {direction}. FORWARD/REVERSE restrictions are filtered by travel "
            "direction (BOTH applies to both); where restrictions overlap the lowest speed wins. "
            "No speed profile, acceleration or braking value is derived."
        )
        self._table.value = fmt.data_table_html(
            ("Segment [km]", "Effective speed [km/h]", "Restrictions"),
            tuple(
                (
                    f"{segment.start_km:g} - {segment.end_km:g}",
                    "unrestricted" if segment.speed_kmh is None else f"{segment.speed_kmh:g}",
                    ", ".join(segment.restriction_ids) or "-",
                )
                for segment in segments
            ),
            empty_text="No applicable speed restriction.",
        )


def preview_note() -> widgets.HTML:
    """Return the standard note displayed beside the previews."""
    return widgets.HTML(
        fmt.message_html(
            "Previews visualise stored data (plus the gradient between adjacent elevation "
            "points). They contain no train dynamics, no traction, no braking and no "
            "speed-envelope value.",
            severity=Severity.INFO,
        )
    )
