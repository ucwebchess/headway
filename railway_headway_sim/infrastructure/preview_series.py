"""Synchronised preview series for the Phase-3 UI (pure derivation, no widgets).

This module turns stored typed-catalogue values into the **only** derived series the
Phase-3 editors display, and nothing else:

* elevation series - the stored vertical profile points, unchanged;
* gradient series - the elevation difference between two *adjacent* stored points
  divided by the physical distance between them (permitted by the Phase-3 scope,
  §G5: "gradient between two adjacent elevation points");
* curvature series - the stored ``radius_m`` of the horizontal geometry sections
  (no new calculation: the value is already stored);
* effective speed series - the stored speed restrictions filtered by the
  application direction with the **most restrictive wins** rule applied to the
  restriction segments (permitted by §G8).

Nothing here is train dynamics: no speed, acceleration, braking, resistance,
time, occupation, headway or capacity quantity is produced.  The functions take
plain values (or typed catalogue objects) and return immutable dataclasses that a
renderer can draw; no widget, controller or model state is imported.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Optional, Sequence

from .mapping import POSITION_TOLERANCE_M

#: Chainage distance below which two points are treated as coincident (km).
CHAINAGE_EPS_KM = 1e-9


def _value(item: Any, field: str) -> Any:
    """Return ``item[field]`` for dicts or ``item.field`` for typed objects."""
    if isinstance(item, dict):
        return item.get(field)
    return getattr(item, field, None)


def _number(value: Any) -> Optional[float]:
    """Return *value* as a float, or ``None`` when it is not a finite number."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    if number != number or number in (float("inf"), float("-inf")):
        return None
    return number


def _enum(value: Any) -> str:
    """Return the plain string of an enum value or a string."""
    return str(getattr(value, "value", value) or "")


@dataclass(frozen=True)
class GradientSegment:
    """Gradient between two adjacent stored elevation points.

    ``gradient_permille`` is ``(elevation difference [m]) / (distance [km])``, the
    stored-data definition of a gradient in per mille.  For a REVERSE preview the
    segment order is reversed and the sign is flipped so that the series is shown
    in the direction of travel; **no stored value is modified**.
    """

    start_km: float
    end_km: float
    from_elevation_m: float
    to_elevation_m: float
    distance_km: float
    gradient_permille: float

    def describe(self) -> str:
        """Return a one-line human readable description with units."""
        return (
            f"{self.start_km:g} - {self.end_km:g} km: "
            f"{self.gradient_permille:+.1f} per mille"
        )


@dataclass(frozen=True)
class CurvatureSegment:
    """Horizontal geometry section with its stored curve radius."""

    id: str
    start_km: float
    end_km: float
    section_type: str
    radius_m: Optional[float]
    handedness: Optional[str]

    def describe(self) -> str:
        """Return a one-line human readable description with units."""
        if self.section_type == "CURVE" and self.radius_m is not None:
            handed = f" {self.handedness}" if self.handedness else ""
            return f"{self.start_km:g} - {self.end_km:g} km: CURVE{handed} radius {self.radius_m:g} m"
        return f"{self.start_km:g} - {self.end_km:g} km: STRAIGHT"


@dataclass(frozen=True)
class SpeedSegment:
    """Effective permissible speed over a chainage range for one direction."""

    start_km: float
    end_km: float
    speed_kmh: Optional[float]
    restriction_ids: tuple[str, ...] = ()

    def describe(self) -> str:
        """Return a one-line human readable description with units."""
        if self.speed_kmh is None:
            return f"{self.start_km:g} - {self.end_km:g} km: no restriction"
        return f"{self.start_km:g} - {self.end_km:g} km: {self.speed_kmh:g} km/h"


def elevation_series(points: Iterable[Any]) -> tuple[tuple[float, float], ...]:
    """Return ``(chainage_km, elevation_m)`` pairs sorted by chainage."""
    series: list[tuple[float, float]] = []
    for point in points:
        chainage = _number(_value(point, "chainage_km"))
        elevation = _number(_value(point, "elevation_m"))
        if chainage is None or elevation is None:
            continue
        series.append((chainage, elevation))
    series.sort(key=lambda item: item[0])
    return tuple(series)


def gradient_segments(
    points: Iterable[Any], *, direction: Any = "FORWARD"
) -> tuple[GradientSegment, ...]:
    """Return the gradient between adjacent elevation points.

    Parameters
    ----------
    points
        Vertical profile points (typed objects or plain dicts).
    direction
        ``FORWARD`` (default) or ``REVERSE``; for ``REVERSE`` the segments are
        returned in reverse travel order with a negated gradient sign.  The
        stored values are never modified.
    """
    series = elevation_series(points)
    segments: list[GradientSegment] = []
    for (start_km, start_m), (end_km, end_m) in zip(series, series[1:]):
        distance = end_km - start_km
        if abs(distance) < CHAINAGE_EPS_KM:
            continue
        segments.append(
            GradientSegment(
                start_km=start_km,
                end_km=end_km,
                from_elevation_m=start_m,
                to_elevation_m=end_m,
                distance_km=distance,
                gradient_permille=(end_m - start_m) / distance,
            )
        )
    if _enum(direction).upper() == "REVERSE":
        return tuple(
            GradientSegment(
                start_km=segment.start_km,
                end_km=segment.end_km,
                from_elevation_m=segment.from_elevation_m,
                to_elevation_m=segment.to_elevation_m,
                distance_km=segment.distance_km,
                gradient_permille=-segment.gradient_permille,
            )
            for segment in reversed(segments)
        )
    return tuple(segments)


def curvature_segments(sections: Iterable[Any]) -> tuple[CurvatureSegment, ...]:
    """Return the horizontal geometry sections with their stored radius."""
    result: list[CurvatureSegment] = []
    for section in sections:
        start_km = _number(_value(section, "start_chainage_km"))
        end_km = _number(_value(section, "end_chainage_km"))
        if start_km is None or end_km is None:
            continue
        section_type = _enum(_value(section, "type")) or "STRAIGHT"
        handedness = _enum(_value(section, "handedness")) or None
        result.append(
            CurvatureSegment(
                id=str(_value(section, "id") or ""),
                start_km=start_km,
                end_km=end_km,
                section_type=section_type,
                radius_m=_number(_value(section, "radius_m")),
                handedness=handedness,
            )
        )
    result.sort(key=lambda item: (item.start_km, item.end_km))
    return tuple(result)


def _applies(restriction_direction: str, direction: str) -> bool:
    """Return whether a restriction direction applies to the selected direction."""
    restriction_direction = (restriction_direction or "").upper()
    direction = (direction or "").upper()
    if direction == "BOTH":
        return True
    if restriction_direction == "BOTH":
        return True
    return restriction_direction == direction


def _eligible_restrictions(
    restrictions: Iterable[Any], direction: Any
) -> list[tuple[str, float, float, float]]:
    """Return ``(id, start_km, end_km, speed_kmh)`` of the applicable restrictions."""
    eligible: list[tuple[str, float, float, float]] = []
    for restriction in restrictions:
        if not _applies(_enum(_value(restriction, "direction")), _enum(direction)):
            continue
        start_km = _number(_value(restriction, "start_chainage_km"))
        end_km = _number(_value(restriction, "end_chainage_km"))
        speed = _number(_value(restriction, "speed_kmh"))
        if start_km is None or end_km is None or speed is None or speed <= 0:
            continue
        if end_km - start_km < CHAINAGE_EPS_KM:
            continue
        eligible.append((str(_value(restriction, "id") or ""), start_km, end_km, speed))
    return eligible


def effective_speed_segments(
    restrictions: Iterable[Any], *, direction: Any = "FORWARD"
) -> tuple[SpeedSegment, ...]:
    """Return the effective permissible speed profile for one direction.

    Restrictions that do not apply to *direction* are filtered out
    (``BOTH`` applies to both travel directions) and, over the sampled
    breakpoints, the **most restrictive (lowest) speed wins**.  Where no
    restriction covers a chainage the segment carries ``speed_kmh = None``.
    """
    eligible = _eligible_restrictions(restrictions, direction)
    if not eligible:
        return ()
    breakpoints = sorted({start for _i, start, _e, _s in eligible} | {end for _i, _s, end, _v in eligible})
    segments: list[SpeedSegment] = []
    for start_km, end_km in zip(breakpoints, breakpoints[1:]):
        if end_km - start_km < CHAINAGE_EPS_KM:
            continue
        midpoint = (start_km + end_km) / 2.0
        covering = [
            (speed, restriction_id)
            for restriction_id, start, end, speed in eligible
            if start - CHAINAGE_EPS_KM <= midpoint <= end + CHAINAGE_EPS_KM
        ]
        if not covering:
            segments.append(SpeedSegment(start_km=start_km, end_km=end_km, speed_kmh=None))
            continue
        best_speed = min(speed for speed, _id in covering)
        ids = tuple(sorted(restriction_id for speed, restriction_id in covering if speed == best_speed))
        segments.append(
            SpeedSegment(start_km=start_km, end_km=end_km, speed_kmh=best_speed, restriction_ids=ids)
        )
    return tuple(segments)


def effective_speed_at(segments: Sequence[SpeedSegment], chainage_km: float) -> Optional[float]:
    """Return the effective speed at *chainage_km* (``None`` when unrestricted)."""
    for segment in segments:
        if segment.start_km - CHAINAGE_EPS_KM <= chainage_km <= segment.end_km + CHAINAGE_EPS_KM:
            return segment.speed_kmh
    return None


# ---------------------------------------------------------------------------
# Train-fit classification (Phase-3 §G6)
# ---------------------------------------------------------------------------
#: Outcome of the stopping-mark / train-fit checker.
FIT = "FIT"
#: The train is longer than the usable platform range (or leaves the track).
TOO_LONG = "TOO_LONG"
#: The stopping mark itself lies outside the usable platform range.
MARKER_OUTSIDE_USABLE = "MARKER_OUTSIDE_USABLE"

def marker_within_usable(
    marker_position_m: Optional[float],
    usable_start_m: Optional[float],
    usable_end_m: Optional[float],
    *,
    tolerance_m: float = POSITION_TOLERANCE_M,
) -> Optional[bool]:
    """Return whether a stopping mark lies inside the usable platform range.

    ``None`` means the question cannot be answered because a value is missing.
    No new engineering rule is introduced: the usable range is a *stored* value
    and this function only compares positions.
    """
    position = _number(marker_position_m)
    start = _number(usable_start_m)
    end = _number(usable_end_m)
    if position is None or start is None or end is None:
        return None
    low, high = (start, end) if start <= end else (end, start)
    return (low - tolerance_m) <= position <= (high + tolerance_m)


def train_fit_outcome(footprint: Any) -> str:
    """Classify a Phase-2 static footprint as FIT / TOO_LONG / MARKER_OUTSIDE_USABLE.

    The classification reads only values the package already computed:

    * the marker position against the stored usable range decides
      :data:`MARKER_OUTSIDE_USABLE`;
    * otherwise the stored ``fit_in_track`` / ``fit_in_usable_platform`` flags of
      the footprint decide between :data:`FIT` and :data:`TOO_LONG`.

    No distance, margin or timing value is produced here.
    """
    within = marker_within_usable(
        getattr(footprint, "front_position_m", None),
        getattr(footprint, "usable_start_m", None),
        getattr(footprint, "usable_end_m", None),
    )
    if within is False:
        return MARKER_OUTSIDE_USABLE
    if not getattr(footprint, "fit_in_track", True):
        return TOO_LONG
    if getattr(footprint, "usable_start_m", None) is not None and not getattr(
        footprint, "fit_in_usable_platform", True
    ):
        return TOO_LONG
    return FIT
