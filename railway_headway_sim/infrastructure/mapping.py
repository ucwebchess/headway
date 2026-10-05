"""Track-local position <-> physical chainage mapping (static utility).

Phase 2 supports the LINEAR chainage map only:

* local ``position_m == 0`` maps to ``chainage_map.start_km``;
* local ``position_m == track.length_m`` maps to ``chainage_map.end_km``;
* positions in between map by straight-line interpolation.

No train movement, no timing and no physics is computed here - this is a pure
static coordinate conversion used by validation, the UI and the static
footprint checks.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..models.enums import ChainageMapMode

if TYPE_CHECKING:  # pragma: no cover - typing only
    from ..models.infrastructure import Track

#: Tolerance (in metres) applied to position bounds checks.
POSITION_TOLERANCE_M = 1e-6

#: Tolerance (in kilometres) applied to chainage bounds checks.
CHAINAGE_TOLERANCE_KM = 1e-9


class ChainageMapError(ValueError):
    """Raised when a position/chainage cannot be mapped (documented precondition)."""


def _require_linear(track: "Track") -> None:
    """Raise when a track uses an unsupported chainage-map mode."""
    mode = track.chainage_map.mode
    if getattr(mode, "value", mode) != ChainageMapMode.LINEAR.value:
        raise ChainageMapError(
            f"Track '{track.id}' uses chainage map mode {getattr(mode, 'value', mode)!r}; "
            f"only '{ChainageMapMode.LINEAR.value}' is supported in Phase 2."
        )


def track_length_m(track: "Track") -> float:
    """Return the physical length of *track* in metres."""
    return float(track.length_m)


def chainage_span_km(track: "Track") -> float:
    """Return the signed chainage span covered by *track* (end - start)."""
    return float(track.chainage_map.end_km) - float(track.chainage_map.start_km)


def edge_position_to_chainage(track: "Track", position_m: float) -> float:
    """Map a track-local position in metres to a physical chainage in kilometres.

    Raises
    ------
    ChainageMapError
        When the map mode is unsupported, the track has zero length, or the
        position lies outside ``[0, length_m]``.
    """
    _require_linear(track)
    length = track_length_m(track)
    if length <= 0:
        raise ChainageMapError(
            f"Track '{track.id}' has non-positive length_m ({track.length_m}); "
            "positions cannot be mapped."
        )
    position = float(position_m)
    if position < -POSITION_TOLERANCE_M or position > length + POSITION_TOLERANCE_M:
        raise ChainageMapError(
            f"Position {position_m} m is outside track '{track.id}' bounds [0, {length}] m."
        )
    start_km = float(track.chainage_map.start_km)
    end_km = float(track.chainage_map.end_km)
    fraction = position / length
    return start_km + fraction * (end_km - start_km)


def chainage_to_edge_position(track: "Track", chainage_km: float) -> float:
    """Map a physical chainage in kilometres back to a track-local position.

    The inverse is unambiguous for a LINEAR map with a non-zero chainage span.
    """
    _require_linear(track)
    span = chainage_span_km(track)
    if abs(span) <= CHAINAGE_TOLERANCE_KM:
        raise ChainageMapError(
            f"Track '{track.id}' maps a degenerate chainage span "
            f"({track.chainage_map.start_km} -> {track.chainage_map.end_km} km); "
            "the inverse mapping is ambiguous."
        )
    start_km = float(track.chainage_map.start_km)
    end_km = float(track.chainage_map.end_km)
    chainage = float(chainage_km)
    low, high = (start_km, end_km) if start_km <= end_km else (end_km, start_km)
    if chainage < low - CHAINAGE_TOLERANCE_KM or chainage > high + CHAINAGE_TOLERANCE_KM:
        raise ChainageMapError(
            f"Chainage {chainage_km} km is outside track '{track.id}' mapped range "
            f"[{low}, {high}] km."
        )
    return (chainage - start_km) / span * track_length_m(track)


def is_position_within_track(track: "Track", position_m: float) -> bool:
    """Return whether a local position lies within the physical track bounds."""
    length = track_length_m(track)
    return -POSITION_TOLERANCE_M <= float(position_m) <= length + POSITION_TOLERANCE_M


def mapped_position_delta_m(track: "Track") -> float:
    """Return ``physical length - chainage-projected length`` for *track*.

    A non-zero value is legitimate (a diagonal track covers a shorter chainage
    span than its physical length) and must never be a validation failure
    (Section N / TEST P2-027).
    """
    projected_m = abs(chainage_span_km(track)) * 1000.0
    return track_length_m(track) - projected_m
