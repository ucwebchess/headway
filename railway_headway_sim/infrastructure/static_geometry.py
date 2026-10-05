"""Static train-footprint utility (validation geometry only - NOT train dynamics).

Given a track, a stopping marker, a static train length and the movement
orientation relative to the stored edge, this module answers a purely static
question: *where would the front and rear of the train be, and does it fit?*

Orientation rule (Section Y):

* ``WITH_EDGE``    - the train is moving in the stored edge direction:
  ``rear_local = front_local - train_length``
* ``AGAINST_EDGE`` - the train is moving against the stored edge direction:
  ``rear_local = front_local + train_length``

Nothing here computes time, speed, acceleration, braking or occupation. The
result carries the static ``critical_boundary_m`` (the platform boundary the
train is checked against) so that clearance/infringement numbers can be quoted
exactly as specified by the GRR benchmarks.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from ..models.enums import EdgeTraversal
from .mapping import POSITION_TOLERANCE_M, ChainageMapError, edge_position_to_chainage

if TYPE_CHECKING:  # pragma: no cover - typing only
    from ..models.infrastructure import Platform, StoppingMark, Track


@dataclass(frozen=True)
class StaticFootprint:
    """Static footprint of a standing train at a stopping marker."""

    track_id: str
    marker_id: str
    platform_id: Optional[str]
    train_length_m: float
    traversal: EdgeTraversal
    front_position_m: float
    rear_position_m: float
    occupied_min_m: float
    occupied_max_m: float
    track_length_m: float
    fit_in_track: bool
    fit_in_usable_platform: bool
    critical_boundary_m: Optional[float]
    rear_margin_m: Optional[float]
    front_margin_m: Optional[float]
    usable_start_m: Optional[float]
    usable_end_m: Optional[float]
    front_chainage_km: Optional[float]
    rear_chainage_km: Optional[float]
    notes: tuple[str, ...] = ()

    @property
    def rear_infringement_m(self) -> float:
        """Return the positive rear infringement relative to the critical boundary."""
        if self.rear_margin_m is None or self.rear_margin_m >= 0:
            return 0.0
        return -self.rear_margin_m

    @property
    def rear_clearance_m(self) -> float:
        """Return the positive rear clearance relative to the critical boundary."""
        return max(0.0, self.rear_margin_m or 0.0)

    def describe(self) -> str:
        """Return a one-line human description of the static footprint."""
        if self.rear_margin_m is None:
            clearance = "no usable-platform check available"
        elif self.rear_margin_m < 0:
            clearance = f"rear infringement {self.rear_infringement_m:g} m"
        else:
            clearance = f"rear clearance {self.rear_clearance_m:g} m"
        return (
            f"{self.marker_id} on {self.track_id} ({self.traversal.value}, "
            f"{self.train_length_m:g} m): front {self.front_position_m:g} m, "
            f"rear {self.rear_position_m:g} m - {clearance}"
        )


def evaluate_static_footprint(
    track: "Track",
    *,
    front_position_m: float,
    train_length_m: float,
    traversal: EdgeTraversal,
    marker_id: str = "",
    platform: Optional["Platform"] = None,
) -> StaticFootprint:
    """Compute the static footprint from an explicit front position on *track*.

    This is the core utility. It takes exactly the inputs named by the frozen
    static benchmarks (track, front position, static train length, traversal) so
    that an evaluation point does not need a stopping marker to be measured.

    Raises
    ------
    ValueError
        When ``train_length_m`` is not positive or ``front_position_m`` is not a
        finite number (documented preconditions; programming/input errors, not
        project-data diagnostics).
    """
    if not isinstance(train_length_m, (int, float)) or isinstance(train_length_m, bool):
        raise ValueError(f"train_length_m must be a number, got {train_length_m!r}.")
    if float(train_length_m) <= 0:
        raise ValueError(f"train_length_m must be positive, got {train_length_m!r}.")
    if not isinstance(front_position_m, (int, float)) or isinstance(front_position_m, bool):
        raise ValueError(f"front_position_m must be a number, got {front_position_m!r}.")

    length = float(train_length_m)
    front = float(front_position_m)
    if traversal is EdgeTraversal.WITH_EDGE:
        rear = front - length
    else:
        rear = front + length

    occupied_min = min(front, rear)
    occupied_max = max(front, rear)
    track_length = float(track.length_m)
    fit_in_track = (
        occupied_min >= -POSITION_TOLERANCE_M and occupied_max <= track_length + POSITION_TOLERANCE_M
    )

    notes: list[str] = []
    critical_boundary: Optional[float] = None
    rear_margin: Optional[float] = None
    front_margin: Optional[float] = None
    usable_start: Optional[float] = None
    usable_end: Optional[float] = None

    if platform is not None:
        usable_start = float(platform.usable_start_m)
        usable_end = float(platform.usable_end_m)
        if traversal is EdgeTraversal.WITH_EDGE:
            # Moving with the stored edge: the rear must still be inside the
            # usable range, i.e. the upstream (start) boundary is critical.
            critical_boundary = usable_start
            rear_margin = rear - usable_start
            front_margin = usable_end - front
        else:
            # Moving against the stored edge: the downstream (end) boundary of
            # the usable range is critical for the rear.
            critical_boundary = usable_end
            rear_margin = usable_end - rear
            front_margin = front - usable_start
        if platform.track_id != track.id:
            notes.append(
                f"platform {platform.id} is declared on track {platform.track_id}, "
                f"not on {track.id}"
            )

    fit_in_usable_platform = bool(
        rear_margin is not None
        and front_margin is not None
        and rear_margin >= -POSITION_TOLERANCE_M
        and front_margin >= -POSITION_TOLERANCE_M
    )

    front_chainage: Optional[float] = None
    rear_chainage: Optional[float] = None
    for label, position in (("front", front), ("rear", rear)):
        try:
            mapped = edge_position_to_chainage(track, position)
        except ChainageMapError as exc:
            notes.append(f"{label} position could not be mapped to chainage: {exc}")
            continue
        if label == "front":
            front_chainage = mapped
        else:
            rear_chainage = mapped

    return StaticFootprint(
        track_id=track.id,
        marker_id=marker_id or (platform.id if platform is not None else ""),
        platform_id=platform.id if platform is not None else None,
        train_length_m=length,
        traversal=traversal,
        front_position_m=front,
        rear_position_m=rear,
        occupied_min_m=occupied_min,
        occupied_max_m=occupied_max,
        track_length_m=track_length,
        fit_in_track=fit_in_track,
        fit_in_usable_platform=fit_in_usable_platform,
        critical_boundary_m=critical_boundary,
        rear_margin_m=rear_margin,
        front_margin_m=front_margin,
        usable_start_m=usable_start,
        usable_end_m=usable_end,
        front_chainage_km=front_chainage,
        rear_chainage_km=rear_chainage,
        notes=tuple(notes),
    )


def compute_static_footprint(
    track: "Track",
    marker: "StoppingMark",
    train_length_m: float,
    traversal: EdgeTraversal,
    *,
    platform: Optional["Platform"] = None,
) -> StaticFootprint:
    """Compute the static footprint of a train standing at *marker* on *track*.

    Parameters
    ----------
    track
        Typed track edge the marker belongs to.
    marker
        Typed stopping marker (its ``position_m`` is the train's front position).
    train_length_m
        Static train length (fixture/reference length; no physics is involved).
    traversal
        ``WITH_EDGE`` or ``AGAINST_EDGE`` movement orientation.
    platform
        Optional platform; when given, the usable-range check and the critical
        boundary are computed from it.

    Raises
    ------
    ValueError
        When ``train_length_m`` is not positive (documented precondition; this is
        a programming/input error, not a project-data diagnostic).
    """
    return evaluate_static_footprint(
        track,
        front_position_m=float(marker.position_m),
        train_length_m=train_length_m,
        traversal=traversal,
        marker_id=marker.id,
        platform=platform,
    )


def traversal_for_direction(marker_direction: object) -> EdgeTraversal:
    """Return the movement orientation matching a marker's declared direction.

    Phase-2 GRR stores every track with increasing physical chainage, so a
    FORWARD marker is traversed WITH_EDGE and a REVERSE marker AGAINST_EDGE.
    The direction values themselves stay railway-direction semantics; only this
    helper connects them to the stored edge orientation.
    """
    value = getattr(marker_direction, "value", marker_direction)
    return EdgeTraversal.WITH_EDGE if value == "FORWARD" else EdgeTraversal.AGAINST_EDGE
