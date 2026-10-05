"""Geometry along a compiled route (Phase 4B): elevation, gradient and curve radius.

Given a Phase-4A
:class:`~railway_headway_sim.infrastructure.compiled_network.RouteCoordinateSystem`,
:class:`RouteGeometry` answers three questions for any route distance ``s`` in
``[0, route_length_m]``:

* :meth:`RouteGeometry.elevation_at` — the physical elevation there, in metres ``[m]``;
* :meth:`RouteGeometry.gradient_at` — the effective gradient there, in per mille
  ``[permille]``, **signed by the direction of travel**;
* :meth:`RouteGeometry.curve_radius_at` — the stored curve radius there, in metres
  ``[m]``, or ``None`` on a straight section.

and one footprint-aware convenience:

* :meth:`RouteGeometry.footprint_gradient` — the effective gradient over the footprint
  of a train of a given length ``[m]`` whose front is at ``s``, in ``[permille]``.

Everything is read from the project's own stored ``vertical_profiles`` (source mode
``ELEVATION_POINTS``) and ``horizontal_geometry`` catalogues, through the Phase-3
derivation helpers of :mod:`.preview_series`; nothing is computed that the stored data
does not imply.  The only arithmetic beyond interpolation is the length-weighted mean of
:meth:`RouteGeometry.footprint_gradient` (Phase 4B, §D5).

The physical railway fixes the signs, not the direction of travel:

* elevation is a property of the railway, so FORWARD and REVERSE return the same value
  at the same physical location;
* the gradient is directional, because the vertical profile is stored against
  **increasing physical chainage** — a route whose chainage decreases with ``s`` returns
  the opposite sign;
* a curve radius is a magnitude, so FORWARD and REVERSE return the same value, and the
  handedness (``handedness``) is deliberately not part of this API.

A defect of the *data* is reported, never repaired: a missing or too-short vertical
profile, a horizontal geometry that does not cover the route, or a curve section without
a stored radius is a diagnostic on :attr:`RouteGeometry.diagnostics` (existing
``VAL-GEOM`` codes only), and a query that the data cannot answer raises
:class:`~railway_headway_sim.infrastructure.compiled_network.RouteCoordinateError`.
Nothing is ever clamped and no placeholder value is ever returned.

Scope (Phase 4B): the only computed engineering values are the interpolated elevation,
the stored-data gradient, the stored radius and the footprint mean of that gradient.
This module contains no force, no speed, no time - no resistance, no traction, no
braking, no acceleration, no trajectory and no integration - and no signalling, no
headway, no capacity and no timetable.
"""

from __future__ import annotations

from typing import Any, Optional, Sequence

from ..models.diagnostics import Diagnostic
from ..models.enums import DiagnosticCategory, Severity
from ..validation import codes
from .compiled_network import RouteCoordinateError, RouteCoordinateSystem
from .preview_series import curvature_segments, elevation_series, gradient_segments

#: Reported units of the quantities of this module (Phase 4B, §F6).
ELEVATION_UNIT = "m"
GRADIENT_UNIT = "permille"
RADIUS_UNIT = "m"

#: Chainage tolerance used by the coverage checks and the segment lookups (1 mm, km).
COVERAGE_TOLERANCE_KM = 1e-6

#: Distance (metres) used to read the chainage just inside a route segment.
_SEGMENT_PROBE_M = 1e-3

#: Distance (metres) below which two route-distance breakpoints are the same point.
_BREAKPOINT_EPS_M = 1e-9

#: The two infinities, used to test a route-distance argument for finiteness without
#: importing the numeric library the module deliberately does not depend on.
_NEGATIVE_INFINITY = float("-inf")
_POSITIVE_INFINITY = float("inf")


def _sign(value: float) -> float:
    """Return ``+1.0``, ``-1.0`` or ``0.0`` for the sign of *value*."""
    if value > 0.0:
        return 1.0
    if value < 0.0:
        return -1.0
    return 0.0


class RouteGeometry:
    """Elevation, gradient and curve radius along one compiled route (Phase 4B).

    Parameters
    ----------
    project
        The loaded, validated project (the canonical internal model).  It is read
        only: :class:`RouteGeometry` never writes to it and never mutates it.
    route_system
        A Phase-4A :class:`~railway_headway_sim.infrastructure.compiled_network.RouteCoordinateSystem`.
        The instance is direction-agnostic here: the same class serves a FORWARD and a
        REVERSE coordinate system, because the direction is already a property of the
        route system (Phase 4A) and the stored geometry is a property of the railway.

    The instance is read-only after construction: every query derives its answer from the
    values captured in :meth:`__init__` plus the route system's own mapping.
    """

    def __init__(self, project: Any, route_system: RouteCoordinateSystem) -> None:
        segments = tuple(getattr(route_system, "segments", ()) or ())
        if not segments and not hasattr(route_system, "at_route_distance"):
            raise TypeError(
                "route_system must be a Phase-4A RouteCoordinateSystem"
            )

        # -- the route's own chainage anchors, read through the Phase-4A mapping --------
        #: Per route segment ``(start_s, end_s, probe_s_start, probe_s_end,
        #: probe_chainage_start_km, probe_chainage_end_km, chainage_start_km,
        #: chainage_end_km)``.  The chainage is read just inside each segment through
        #: the Phase-4A mapping (the segment boundaries themselves belong to the
        #: neighbouring segment), and the segment's own boundary chainages are the
        #: affine extension of those two probes, which is exact for a LINEAR
        #: ``chainage_map``.
        windows: list[tuple[float, float, float, float, float, float, float, float]] = []
        signs: list[float] = []
        for segment in segments:
            probe = min(_SEGMENT_PROBE_M, segment.length_m / 2.0)
            start_s_m = float(segment.start_s_m)
            end_s_m = float(segment.end_s_m)
            probe_start_s_m = start_s_m + probe
            probe_end_s_m = end_s_m - probe
            probe_chainage_start_km = float(
                route_system.at_route_distance(probe_start_s_m).chainage_km
            )
            probe_chainage_end_km = float(
                route_system.at_route_distance(probe_end_s_m).chainage_km
            )
            probe_span_m = probe_end_s_m - probe_start_s_m
            probe_span_km = probe_chainage_end_km - probe_chainage_start_km
            if probe_span_m > 0.0:
                per_meter_km = probe_span_km / probe_span_m
                chainage_start_km = probe_chainage_start_km - probe * per_meter_km
                chainage_end_km = probe_chainage_end_km + probe * per_meter_km
            else:
                chainage_start_km = probe_chainage_start_km
                chainage_end_km = probe_chainage_end_km
            windows.append(
                (
                    start_s_m,
                    end_s_m,
                    probe_start_s_m,
                    probe_end_s_m,
                    probe_chainage_start_km,
                    probe_chainage_end_km,
                    chainage_start_km,
                    chainage_end_km,
                )
            )
            signs.append(_sign(probe_chainage_end_km - probe_chainage_start_km))

        anchors = [value for window in windows for value in (window[6], window[7])]
        chainage_min_km = min(anchors) if anchors else None
        chainage_max_km = max(anchors) if anchors else None

        # -- the layer and the alignment the route belongs to --------------------------
        first_edge_id = segments[0].edge_id if segments else None
        layers = list(getattr(project, "infrastructure", ()) or ())
        layer = next(
            (
                candidate
                for candidate in layers
                if any(
                    track.get("id") == first_edge_id
                    for track in (candidate.get("tracks") or [])
                )
            ),
            None,
        )
        if layer is None:
            raise ValueError(
                "the project does not declare the infrastructure layer of the compiled "
                f"route (edge {first_edge_id!r}); RouteGeometry cannot be constructed"
            )
        declared_alignments = sorted(
            str(alignment.get("id"))
            for alignment in (layer.get("alignments") or [])
            if alignment.get("id")
        )
        reference = getattr(project, "reference_system", None)
        preferred_alignment = getattr(reference, "alignment_id", None)
        alignment_id: Optional[str] = None
        if preferred_alignment in declared_alignments:
            alignment_id = str(preferred_alignment)
        elif declared_alignments:
            alignment_id = declared_alignments[0]

        # -- the stored geometry catalogues of that alignment --------------------------
        profiles = [
            profile
            for profile in (layer.get("vertical_profiles") or [])
            if alignment_id is not None
            and str(profile.get("alignment_id")) == alignment_id
        ]
        sections = [
            section
            for section in (layer.get("horizontal_geometry") or [])
            if alignment_id is not None
            and str(section.get("alignment_id")) == alignment_id
        ]
        raw_points = (profiles[0].get("points") or []) if profiles else []
        points_km_m = elevation_series(raw_points)
        gradients = tuple(
            (segment.start_km, segment.end_km, segment.gradient_permille)
            for segment in gradient_segments(raw_points)
        )
        stored_sections = curvature_segments(sections)

        # -- diagnostics: what the stored data can and cannot answer -------------------
        diagnostics: list[Diagnostic] = []
        target = alignment_id or (layer.get("id") or "(unknown alignment)")
        if not profiles:
            diagnostics.append(
                _geometry_diagnostic(
                    codes.VAL_GEOM_006,
                    f"No vertical profile is declared for alignment '{target}'; elevation "
                    "and gradient cannot be read along this route.",
                    target,
                    {"catalogue": "vertical_profiles", "alignment_id": alignment_id},
                    "Declare a vertical profile with source_mode ELEVATION_POINTS for the "
                    "alignment.",
                )
            )
        elif len(points_km_m) < 2:
            diagnostics.append(
                _geometry_diagnostic(
                    codes.VAL_GEOM_006,
                    f"Vertical profile '{profiles[0].get('id')}' has {len(points_km_m)} "
                    "usable elevation point(s); at least two are required to read an "
                    "elevation or a gradient.",
                    str(profiles[0].get("id") or target),
                    {"catalogue": "vertical_profiles", "point_count": len(points_km_m)},
                    "Provide at least two elevation points.",
                )
            )
        elif (
            chainage_min_km is not None
            and chainage_max_km is not None
            and (
                points_km_m[0][0] > chainage_min_km + COVERAGE_TOLERANCE_KM
                or points_km_m[-1][0] < chainage_max_km - COVERAGE_TOLERANCE_KM
            )
        ):
            diagnostics.append(
                _geometry_diagnostic(
                    codes.VAL_GEOM_006,
                    f"Vertical profile '{profiles[0].get('id')}' covers chainage "
                    f"[{points_km_m[0][0]:g}, {points_km_m[-1][0]:g}] km but the route runs "
                    f"[{chainage_min_km:g}, {chainage_max_km:g}] km; the profile does not "
                    "cover the route.",
                    target,
                    {
                        "catalogue": "vertical_profiles",
                        "covered_km": [points_km_m[0][0], points_km_m[-1][0]],
                        "route_km": [chainage_min_km, chainage_max_km],
                    },
                    "Extend the vertical profile over the full chainage range of the route.",
                )
            )
        if not stored_sections:
            diagnostics.append(
                _geometry_diagnostic(
                    codes.VAL_GEOM_004,
                    f"No horizontal geometry section is declared for alignment "
                    f"'{target}'; the curve radius cannot be read along this route.",
                    target,
                    {"catalogue": "horizontal_geometry", "alignment_id": alignment_id},
                    "Declare the horizontal geometry sections of the alignment.",
                )
            )
        elif chainage_min_km is not None and chainage_max_km is not None:
            gaps = _coverage_gaps(stored_sections, chainage_min_km, chainage_max_km)
            if gaps:
                diagnostics.append(
                    _geometry_diagnostic(
                        codes.VAL_GEOM_004,
                        f"Horizontal geometry of alignment '{target}' does not cover the "
                        "route: no section covers "
                        + ", ".join(f"[{start:g}, {end:g}]" for start, end in gaps)
                        + " km.",
                        target,
                        {
                            "catalogue": "horizontal_geometry",
                            "gaps_km": [[start, end] for start, end in gaps],
                        },
                        "Extend or complete the horizontal geometry sections.",
                    )
                )
            for section in stored_sections:
                overlaps_route = (
                    section.end_km > chainage_min_km + COVERAGE_TOLERANCE_KM
                    and section.start_km < chainage_max_km - COVERAGE_TOLERANCE_KM
                )
                if section.section_type == "CURVE" and section.radius_m is None and overlaps_route:
                    diagnostics.append(
                        _geometry_diagnostic(
                            codes.VAL_GEOM_001,
                            f"Horizontal geometry section '{section.id}' is a CURVE without "
                            "a usable radius_m on this route; no radius is invented for it.",
                            section.id or target,
                            {
                                "catalogue": "horizontal_geometry",
                                "section_type": section.section_type,
                            },
                            "Provide the stored radius_m of the curve section.",
                        )
                    )

        # -- read-only state ------------------------------------------------------------
        self._project = project
        self._route_system = route_system
        self._path_id = str(getattr(route_system, "path_id", ""))
        self._direction = getattr(route_system, "direction", None)
        self._route_length_m = float(getattr(route_system, "route_length_m", 0.0))
        self._layer_id = str(layer.get("id") or "")
        self._alignment_id = alignment_id
        self._windows = tuple(windows)
        self._signs = tuple(signs)
        self._chainage_min_km = chainage_min_km
        self._chainage_max_km = chainage_max_km
        self._points_km_m = tuple(points_km_m)
        self._gradients = gradients
        self._sections = tuple(
            (
                section.start_km,
                section.end_km,
                section.radius_m if section.section_type == "CURVE" else None,
            )
            for section in stored_sections
        )
        self._diagnostics = tuple(diagnostics)

    # -- read-only surface ----------------------------------------------------------
    @property
    def path_id(self) -> str:
        """Return the id of the declared train path whose route is described."""
        return self._path_id

    @property
    def direction(self) -> Any:
        """Return the compiled direction of travel (``FORWARD`` or ``REVERSE``)."""
        return self._direction

    @property
    def route_length_m(self) -> float:
        """Return the length of the described route in metres."""
        return self._route_length_m

    @property
    def layer_id(self) -> str:
        """Return the id of the infrastructure layer that holds the route."""
        return self._layer_id

    @property
    def alignment_id(self) -> Optional[str]:
        """Return the id of the alignment whose stored geometry is read."""
        return self._alignment_id

    @property
    def diagnostics(self) -> tuple[Diagnostic, ...]:
        """Return every geometry diagnostic recorded while constructing this object."""
        return self._diagnostics

    # -- queries --------------------------------------------------------------------
    def elevation_at(self, s_m: float) -> float:
        """Return the physical elevation ``[m]`` at route distance *s_m*.

        The elevation of the alignment is piecewise linear between consecutive stored
        elevation points (``source_mode = ELEVATION_POINTS``), so the value at a stored
        point is exactly the stored ``elevation_m`` and the value between two points is
        the linear interpolation of the two.

        Raises
        ------
        RouteCoordinateError
            When *s_m* lies outside ``[0, route_length_m]``, or when the stored vertical
            profile does not cover the chainage of that position.
        """
        chainage_km = self._chainage_at(s_m)
        points = self._points_km_m
        if len(points) < 2:
            raise RouteCoordinateError(
                f"No usable vertical profile for alignment "
                f"'{self._alignment_id}' covers chainage {chainage_km:g} km "
                f"(route '{self._path_id}'); no elevation is fabricated."
            )
        if (
            chainage_km < points[0][0] - COVERAGE_TOLERANCE_KM
            or chainage_km > points[-1][0] + COVERAGE_TOLERANCE_KM
        ):
            raise RouteCoordinateError(
                f"Chainage {chainage_km:g} km lies outside the stored vertical profile "
                f"[{points[0][0]:g}, {points[-1][0]:g}] km; no elevation is fabricated."
            )
        for (start_km, start_elevation_m), (end_km, end_elevation_m) in zip(
            points, points[1:]
        ):
            if start_km - COVERAGE_TOLERANCE_KM <= chainage_km <= end_km + COVERAGE_TOLERANCE_KM:
                if end_km == start_km:
                    return end_elevation_m
                fraction = (chainage_km - start_km) / (end_km - start_km)
                return start_elevation_m + fraction * (end_elevation_m - start_elevation_m)
        raise RouteCoordinateError(
            f"No vertical profile segment contains chainage {chainage_km:g} km."
        )

    def gradient_at(self, s_m: float) -> float:
        """Return the effective gradient ``[permille]`` at route distance *s_m*.

        The gradient is the stored-data gradient of the vertical profile segment that
        contains the chainage of that position — ``(elevation difference [m]) /
        (distance [km])`` — and it is **piecewise constant**: no interpolation takes
        place inside a segment.  The sign follows the direction of travel: a route whose
        chainage increases with ``s`` reports the profile's own sign, a route whose
        chainage decreases with ``s`` reports the opposite sign, so FORWARD and REVERSE
        of one physical corridor return opposite-signed values at the same physical
        location.

        Raises
        ------
        RouteCoordinateError
            When *s_m* lies outside ``[0, route_length_m]``, when the stored vertical
            profile does not cover that chainage, or when the chainage of that position
            cannot be resolved against ``s``.
        """
        chainage_km = self._chainage_at(s_m)
        piece = self._gradient_at_chainage(chainage_km)
        if piece is None:
            raise RouteCoordinateError(
                f"No stored gradient covers chainage {chainage_km:g} km (route "
                f"'{self._path_id}'); no gradient is fabricated."
            )
        return self._chainage_sign_at(s_m) * piece

    def curve_radius_at(self, s_m: float) -> Optional[float]:
        """Return the stored curve radius ``[m]`` at route distance *s_m*, else ``None``.

        The radius is the ``radius_m`` of the horizontal geometry section that contains
        the chainage of that position.  Sections of type ``STRAIGHT`` carry no radius and
        return ``None`` — never ``0.0`` and never a sentinel float.  The radius is a
        magnitude: FORWARD and REVERSE return the same value at the same physical
        location.  Handedness is not part of this API.

        Raises
        ------
        RouteCoordinateError
            When *s_m* lies outside ``[0, route_length_m]``, or when no stored horizontal
            geometry section covers that chainage.
        """
        chainage_km = self._chainage_at(s_m)
        last_index = len(self._sections) - 1
        for index, (start_km, end_km, radius_m) in enumerate(self._sections):
            if chainage_km < start_km - COVERAGE_TOLERANCE_KM:
                continue
            if chainage_km < end_km - COVERAGE_TOLERANCE_KM:
                return radius_m
            if index == last_index and chainage_km <= end_km + COVERAGE_TOLERANCE_KM:
                return radius_m
        raise RouteCoordinateError(
            f"No stored horizontal geometry section covers chainage {chainage_km:g} km "
            f"(route '{self._path_id}'); no radius is fabricated."
        )

    def footprint_gradient(self, s_m: float, train_length_m: float) -> float:
        """Return the gradient ``[permille]`` averaged over a train footprint.

        The footprint of a train whose **front** is at *s_m* spans
        ``[s_m - train_length_m, s_m]`` in route distance and advances in the direction
        of travel; the returned value is the length-weighted mean of the piecewise
        constant :meth:`gradient_at` over that interval, so it equals
        :meth:`gradient_at` exactly when the whole footprint lies inside one gradient
        segment and the exact weighted mean of the adjacent segment gradients when it
        straddles a transition.

        Raises
        ------
        ValueError
            When *train_length_m* is not a positive number.
        RouteCoordinateError
            When the front or any part of the footprint lies outside
            ``[0, route_length_m]`` — the footprint is never clamped into the route.
        """
        if isinstance(train_length_m, bool) or not isinstance(train_length_m, (int, float)):
            raise ValueError(
                f"train_length_m must be a positive number of metres, got {train_length_m!r}"
            )
        length_m = float(train_length_m)
        if length_m <= 0.0:
            raise ValueError(
                f"train_length_m must be positive, got {length_m} m; the footprint of a "
                "train of that length is undefined."
            )
        front_m = float(s_m)
        if front_m < 0.0 or front_m > self._route_length_m:
            raise RouteCoordinateError(
                f"Route distance {front_m} m is outside the route [0, "
                f"{self._route_length_m}] m of '{self._path_id}'."
            )
        rear_m = front_m - length_m
        if rear_m < 0.0:
            raise RouteCoordinateError(
                f"A footprint of {length_m} m with its front at {front_m} m would start at "
                f"{rear_m} m, before the route origin of '{self._path_id}'; it is not "
                "clamped into the route."
            )
        boundaries = [rear_m, front_m]
        boundaries.extend(
            self._gradient_breakpoints_m(rear_m, front_m)
        )
        ordered = sorted(boundaries)
        deduped: list[float] = []
        for value in ordered:
            if not deduped or abs(value - deduped[-1]) > _BREAKPOINT_EPS_M:
                deduped.append(value)
        if len(deduped) == 2:
            return self.gradient_at(front_m)
        weighted = 0.0
        for low_m, high_m in zip(deduped, deduped[1:]):
            middle_m = 0.5 * (low_m + high_m)
            weighted += (high_m - low_m) * self.gradient_at(middle_m)
        return weighted / length_m

    def curve_radius_segments_in(
        self, s_start_m: float, s_end_m: float
    ) -> tuple[tuple[float, Optional[float]], ...]:
        """Return the ordered sub-intervals of ``[s_start_m, s_end_m]`` of constant radius.

        Every item of the returned tuple is ``(length_m, radius_m)``: the length of one
        sub-interval in route distance and the **stored** radius ``[m]`` that is constant
        over it, or ``None`` when that sub-interval lies on a straight section.  Adjacent
        sub-intervals whose stored radius is the same are reported as one, so the tuple is
        the coarsest partition of the interval on which the stored radius is constant, in
        increasing route-distance order, and the lengths sum to ``s_end_m - s_start_m``
        (exactly, up to floating-point addition).

        The method is purely geometric: it reports the raw stored radii and applies **no**
        resistance model to them - no mass, no force, no speed and no grade enter here.

        Raises
        ------
        ValueError
            When ``s_end_m <= s_start_m`` (the interval is empty or reversed).
        RouteCoordinateError
            When any part of the interval lies outside ``[0, route_length_m]`` - the same
            convention :meth:`footprint_gradient` uses for an out-of-range footprint: the
            interval is never clamped into the route.
        """
        if (
            isinstance(s_start_m, bool)
            or not isinstance(s_start_m, (int, float))
            or isinstance(s_end_m, bool)
            or not isinstance(s_end_m, (int, float))
        ):
            raise ValueError(
                f"s_start_m and s_end_m must be numbers of metres, got {s_start_m!r} and "
                f"{s_end_m!r}"
            )
        start_m = float(s_start_m)
        end_m = float(s_end_m)
        if not (
            _NEGATIVE_INFINITY < start_m < _POSITIVE_INFINITY
            and _NEGATIVE_INFINITY < end_m < _POSITIVE_INFINITY
        ):
            raise ValueError(
                f"s_start_m and s_end_m must be finite, got {s_start_m!r} and {s_end_m!r}"
            )
        if end_m <= start_m:
            raise ValueError(
                f"s_end_m must be greater than s_start_m, got s_start_m = {start_m} m and "
                f"s_end_m = {end_m} m; the interval of a reversed or empty span is undefined."
            )
        if start_m < 0.0 or end_m > self._route_length_m:
            raise RouteCoordinateError(
                f"The interval [{start_m}, {end_m}] m is outside the route [0, "
                f"{self._route_length_m}] m of '{self._path_id}'; it is not clamped into "
                "the route."
            )
        boundaries = [start_m, end_m]
        boundaries.extend(self._radius_breakpoints_m(start_m, end_m))
        ordered = sorted(boundaries)
        deduped: list[float] = []
        for value in ordered:
            if not deduped or abs(value - deduped[-1]) > _BREAKPOINT_EPS_M:
                deduped.append(value)
        segments: list[tuple[float, Optional[float]]] = []
        for low_m, high_m in zip(deduped, deduped[1:]):
            if high_m - low_m <= 0.0:
                continue
            radius_m = self.curve_radius_at(0.5 * (low_m + high_m))
            if segments and segments[-1][1] == radius_m:
                segments[-1] = (segments[-1][0] + (high_m - low_m), radius_m)
            else:
                segments.append((high_m - low_m, radius_m))
        return tuple(segments)

    # -- internals ------------------------------------------------------------------
    def _segment_index_at(self, s_m: float) -> int:
        """Return the index of the route segment that carries route distance *s_m*."""
        for index, window in enumerate(self._windows):
            if window[0] <= s_m < window[1]:
                return index
        if self._windows and abs(s_m - self._windows[-1][1]) <= COVERAGE_TOLERANCE_KM:
            return len(self._windows) - 1
        raise RouteCoordinateError(
            f"Route distance {s_m} m is outside the route of '{self._path_id}'."
        )

    def _chainage_at(self, s_m: float) -> float:
        """Return the physical chainage ``[km]`` of route distance *s_m* (Phase 4A)."""
        value = self._route_system.at_route_distance(float(s_m))
        return float(value.chainage_km)

    def _chainage_sign_at(self, s_m: float) -> float:
        """Return the sign of the chainage change per metre of travel at *s_m*."""
        sign = self._signs[self._segment_index_at(float(s_m))]
        if sign == 0.0:
            raise RouteCoordinateError(
                f"The chainage of the route at {s_m} m does not advance with the route "
                "distance, so a directional gradient cannot be resolved there."
            )
        return sign

    def _gradient_at_chainage(self, chainage_km: float) -> Optional[float]:
        """Return the stored profile gradient ``[permille]`` at *chainage_km*.

        The segment that contains the chainage is the half-open window
        ``[start, end)``, so a chainage exactly on a stored elevation point belongs to
        the segment that *starts* there; the last segment includes its own end.
        """
        last_index = len(self._gradients) - 1
        for index, (start_km, end_km, gradient_permille) in enumerate(self._gradients):
            if chainage_km < start_km - COVERAGE_TOLERANCE_KM:
                continue
            if chainage_km < end_km - COVERAGE_TOLERANCE_KM:
                return gradient_permille
            if index == last_index and chainage_km <= end_km + COVERAGE_TOLERANCE_KM:
                return gradient_permille
        return None

    def _gradient_breakpoints_m(self, low_s_m: float, high_s_m: float) -> list[float]:
        """Return the route distances inside ``(low, high)`` where the gradient may change.

        Breakpoints are (a) the boundaries between two route segments, because the sign
        of the chainage change can differ per edge, and (b) the stored elevation points
        mapped back to route distance through the route's own piecewise-linear chainage
        mapping.
        """
        breakpoints: list[float] = []
        for window in self._windows:
            start_s_m, end_s_m = window[0], window[1]
            if end_s_m <= low_s_m or start_s_m >= high_s_m:
                continue
            for boundary_m in (start_s_m, end_s_m):
                if low_s_m + _BREAKPOINT_EPS_M < boundary_m < high_s_m - _BREAKPOINT_EPS_M:
                    breakpoints.append(boundary_m)
            probe_start_s_m, probe_end_s_m = window[2], window[3]
            probe_start_km, probe_end_km = window[4], window[5]
            probe_span_km = probe_end_km - probe_start_km
            if probe_span_km == 0.0 or probe_end_s_m <= probe_start_s_m:
                continue
            chainage_low_km = min(probe_start_km, probe_end_km)
            chainage_high_km = max(probe_start_km, probe_end_km)
            for point_km, _elevation_m in self._points_km_m:
                if not (
                    chainage_low_km + COVERAGE_TOLERANCE_KM
                    < point_km
                    < chainage_high_km - COVERAGE_TOLERANCE_KM
                ):
                    continue
                # the chainage is affine in the route distance inside one segment, so
                # the inverse of the probe pair is exact - nothing is approximated
                offset_m = (
                    (point_km - probe_start_km)
                    / probe_span_km
                    * (probe_end_s_m - probe_start_s_m)
                )
                candidate_m = probe_start_s_m + offset_m
                if low_s_m + _BREAKPOINT_EPS_M < candidate_m < high_s_m - _BREAKPOINT_EPS_M:
                    breakpoints.append(candidate_m)
        return breakpoints

    def _radius_breakpoints_m(self, low_s_m: float, high_s_m: float) -> list[float]:
        """Return the route distances inside ``(low, high)`` where the stored radius may change.

        Breakpoints are (a) the boundaries between two route segments, because two physical
        positions that meet at such a boundary need not agree in chainage, and (b) the
        stored horizontal-geometry section boundaries mapped back to route distance through
        the route's own piecewise-linear chainage mapping (exact inside one segment, because
        the chainage is affine in the route distance there).  Nothing is approximated.
        """
        breakpoints: list[float] = []
        for window in self._windows:
            start_s_m, end_s_m = window[0], window[1]
            if end_s_m <= low_s_m or start_s_m >= high_s_m:
                continue
            for boundary_m in (start_s_m, end_s_m):
                if low_s_m + _BREAKPOINT_EPS_M < boundary_m < high_s_m - _BREAKPOINT_EPS_M:
                    breakpoints.append(boundary_m)
            probe_start_s_m, probe_end_s_m = window[2], window[3]
            probe_start_km, probe_end_km = window[4], window[5]
            probe_span_km = probe_end_km - probe_start_km
            if probe_span_km == 0.0 or probe_end_s_m <= probe_start_s_m:
                continue
            chainage_low_km = min(probe_start_km, probe_end_km)
            chainage_high_km = max(probe_start_km, probe_end_km)
            for section_start_km, section_end_km, _radius_m in self._sections:
                for point_km in (section_start_km, section_end_km):
                    if not (
                        chainage_low_km + COVERAGE_TOLERANCE_KM
                        < point_km
                        < chainage_high_km - COVERAGE_TOLERANCE_KM
                    ):
                        continue
                    # the chainage is affine in the route distance inside one segment, so
                    # the inverse of the probe pair is exact - nothing is approximated
                    offset_m = (
                        (point_km - probe_start_km)
                        / probe_span_km
                        * (probe_end_s_m - probe_start_s_m)
                    )
                    candidate_m = probe_start_s_m + offset_m
                    if (
                        low_s_m + _BREAKPOINT_EPS_M
                        < candidate_m
                        < high_s_m - _BREAKPOINT_EPS_M
                    ):
                        breakpoints.append(candidate_m)
        return breakpoints


def _geometry_diagnostic(
    code: str,
    message: str,
    object_id: str,
    context: dict[str, Any],
    suggested_action: str,
) -> Diagnostic:
    """Return one GEOMETRY diagnostic of the existing ``VAL-GEOM`` code family."""
    return Diagnostic(
        code=code,
        severity=Severity.ERROR,
        category=DiagnosticCategory.GEOMETRY,
        message=message,
        object_id=object_id,
        context=context,
        suggested_action=suggested_action,
    )


def _coverage_gaps(
    sections: Sequence[Any], chainage_min_km: float, chainage_max_km: float
) -> list[tuple[float, float]]:
    """Return the chainage gaps ``(from_km, to_km)`` of a section list over a range."""
    gaps: list[tuple[float, float]] = []
    cursor = chainage_min_km
    for section in sorted(sections, key=lambda item: (item.start_km, item.end_km)):
        if section.start_km > cursor + COVERAGE_TOLERANCE_KM:
            gaps.append((cursor, section.start_km))
        cursor = max(cursor, section.end_km)
    if cursor < chainage_max_km - COVERAGE_TOLERANCE_KM:
        gaps.append((cursor, chainage_max_km))
    return gaps
