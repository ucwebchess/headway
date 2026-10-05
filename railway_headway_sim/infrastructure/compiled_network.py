"""Compiled network and route coordinates (Phase 4A).

Turns one validated project into a run-direction route-coordinate system:

* :class:`CompiledNetwork` - the physical edges of the validated project plus the
  train paths it declares, together with every diagnostic produced while reading
  them;
* :class:`RouteCoordinateSystem` - one route-distance axis ``s`` [m] for one
  ``(train_path, direction)`` pair;
* :class:`RoutePosition` - a position on that axis: edge identity, traversal,
  track-local position and the mapped physical chainage.

Operator contract (frozen by the master engineering specification):

* route distance ``s`` is measured in metres, ``s = 0`` at the operational origin
  of the path, and it always increases in the train's direction of travel;
* a railway position is authoritative as ``(edge_id, local_position_m)``.  The
  physical chainage is a *mapped reporting coordinate* obtained from the edge's
  ``chainage_map``; it never replaces edge identity and never changes when the
  simulation direction changes - the route-coordinate mapping changes instead;
* the loaded project is never rewritten.  Compiling the same physical edges for
  the other direction only reverses the edge order and complements the traversal
  of each entry, so chainage is preserved by construction.

A declared train path is data in ``train_paths.paths`` of the project document:

.. code-block:: text

    {"id": "H1-F",
     "edges": [{"edge_id": "TR-A-W-U1", "traversal": "WITH_EDGE"}, ...]}

Every entry is validated as declared.  An entry that cannot be resolved is
reported through the standard diagnostic model and the route is refused - it is
never silently dropped, reordered or replaced.

**Where the declared paths are read from.**  :func:`compile_network` always takes
the *project* first (it supplies the physical edges).  The declared paths come from
the project's own ``train_paths.paths``, or - when the project declares none, or
when a companion document is used - from ``paths_source``:

* a mapping carrying ``train_paths.paths`` (a companion document, or a project
  document) or a bare ``paths`` list;
* JSON text of such a document;
* a :class:`pathlib.Path` (or a string naming an existing file) holding that JSON.

The companion document of the reference railway is ``examples/GRR-01-paths.json``:
the frozen ``examples/GRR-01.json`` stays byte-identical and keeps
``train_paths.paths == []``, and the declared paths ``PATH-H1-F`` / ``PATH-H1-R``
are read from the companion file instead.  Whatever the source, the declared data
is read by exactly the same code path and validated exactly the same way.

Phase 4A maps coordinates only.  It computes no force, no speed, no time and no
other motion quantity, and it imports no numeric library: the arithmetic here is
edge lengths, sums, and the LINEAR chainage transform already provided by
:mod:`.mapping`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Sequence

from ..models.diagnostics import Diagnostic
from ..models.enums import DiagnosticCategory, Direction, EdgeTraversal, Severity
from ..models.infrastructure import Track, TopologyNode
from ..validation import codes
from .compiler import CompiledInfrastructure, compile_infrastructure
from .mapping import (
    CHAINAGE_TOLERANCE_KM,
    POSITION_TOLERANCE_M,
    chainage_to_edge_position,
    edge_position_to_chainage,
)
from .topology import InfrastructureTopology

#: Document field names of a declared train path (Phase-4A interchange form).
PATH_ID_FIELD = "id"
PATH_EDGES_FIELD = "edges"
PATH_EDGE_ID_FIELD = "edge_id"
PATH_TRAVERSAL_FIELD = "traversal"

#: The two declared traversal values of a path entry.
DECLARED_TRAVERSALS: tuple[EdgeTraversal, ...] = (
    EdgeTraversal.WITH_EDGE,
    EdgeTraversal.AGAINST_EDGE,
)

#: The two supported simulation directions.
SUPPORTED_DIRECTIONS: tuple[Direction, ...] = (Direction.FORWARD, Direction.REVERSE)

#: The ``train_paths`` container name of the project document; a declared-paths
#: companion document carries the same container (and no infrastructure).
PATH_CONTAINER_FIELD = "train_paths"


def _value_of(raw: Any) -> Any:
    """Return the plain value of an enum-like *raw* input."""
    return getattr(raw, "value", raw)


def normalize_direction(raw: Any) -> Optional[Direction]:
    """Return the supported :class:`Direction` for *raw*, or ``None``.

    ``raw`` may be a :class:`Direction`, or its string value in any letter case.
    No other value is accepted - a direction the project does not declare is
    reported, never guessed.
    """
    value = _value_of(raw)
    if isinstance(value, str):
        candidate = value.strip().upper()
        for direction in SUPPORTED_DIRECTIONS:
            if candidate == direction.value:
                return direction
    return None


def complementary_traversal(traversal: EdgeTraversal) -> EdgeTraversal:
    """Return the traversal that walks the same physical edge the other way."""
    return (
        EdgeTraversal.AGAINST_EDGE
        if traversal is EdgeTraversal.WITH_EDGE
        else EdgeTraversal.WITH_EDGE
    )


def _declared_traversal(raw: Any) -> Optional[EdgeTraversal]:
    """Return the declared traversal for *raw*, or ``None`` when unsupported."""
    value = _value_of(raw)
    if isinstance(value, str):
        candidate = value.strip().upper()
        for traversal in DECLARED_TRAVERSALS:
            if candidate == traversal.value:
                return traversal
    return None


@dataclass(frozen=True)
class RoutePosition:
    """A position on a compiled route (Phase-4A value type).

    ``local_position_m`` is the distance along the edge in the *edge's stored*
    direction, which is how the physical railway identifies a position; the
    physical chainage is the mapped value of that position.
    """

    edge_id: str
    traversal: EdgeTraversal
    local_position_m: float
    chainage_km: float

    def describe(self) -> str:
        """Return a compact one-line text form (used by tests and reports)."""
        return (
            f"{self.edge_id} {self.traversal.value} "
            f"{self.local_position_m:.3f} m -> {self.chainage_km:.6f} km"
        )


@dataclass(frozen=True)
class RouteSegment:
    """One edge of a compiled route, with its route-distance window."""

    edge_id: str
    traversal: EdgeTraversal
    start_s_m: float
    length_m: float

    @property
    def end_s_m(self) -> float:
        """Return the route distance at the exit of this segment."""
        return self.start_s_m + self.length_m


@dataclass(frozen=True)
class PathEdgeRef:
    """One entry of a declared train path, exactly as the project declares it."""

    edge_id: str
    traversal: Optional[EdgeTraversal]
    index: int


class RouteCoordinateError(ValueError):
    """Raised when a route coordinate cannot be resolved.

    The message states the fact; ``diagnostic`` carries the same finding through
    the standard diagnostic model.  A route distance is never fabricated.
    """

    def __init__(self, message: str, *, diagnostic: Optional[Diagnostic] = None) -> None:
        super().__init__(message)
        self.diagnostic = diagnostic


def _diagnostic(
    code: str,
    severity: Severity,
    category: DiagnosticCategory,
    message: str,
    *,
    object_id: Optional[str] = None,
    context: Optional[dict[str, Any]] = None,
    suggested_action: Optional[str] = None,
) -> Diagnostic:
    """Build one diagnostic for a compiled-network finding."""
    return Diagnostic(
        code=code,
        severity=severity,
        category=category,
        message=message,
        object_id=object_id,
        context=context,
        suggested_action=suggested_action,
    )


class RouteCoordinateSystem:
    """Route distance ``s`` [m] for one declared path in one direction (Phase 4A).

    The instance is built once and then read-only.  ``s = 0`` is the operational
    origin of the path *in the compiled direction* and ``s`` increases in the
    direction of travel; there is no sign flag, because the direction is a
    property of the instance.
    """

    def __init__(
        self,
        *,
        path_id: str,
        direction: Direction,
        segments: Sequence[RouteSegment],
        tracks: dict[str, Track],
        diagnostics: tuple[Diagnostic, ...] = (),
    ) -> None:
        self._path_id = path_id
        self._direction = direction
        self._segments = tuple(segments)
        self._tracks = dict(tracks)
        self._diagnostics = tuple(diagnostics)

    # -- read-only surface -------------------------------------------------
    @property
    def path_id(self) -> str:
        """Return the id of the declared train path this route was compiled from."""
        return self._path_id

    @property
    def direction(self) -> Direction:
        """Return ``FORWARD`` or ``REVERSE`` - the compiled direction of travel."""
        return self._direction

    @property
    def route_length_m(self) -> float:
        """Return the length of the route in metres (``s`` runs ``0 .. length``)."""
        if not self._segments:
            return 0.0
        return self._segments[-1].end_s_m

    @property
    def segments(self) -> tuple[RouteSegment, ...]:
        """Return the compiled edge sequence, in the direction of travel."""
        return self._segments

    @property
    def diagnostics(self) -> tuple[Diagnostic, ...]:
        """Return every diagnostic recorded while this route was compiled."""
        return self._diagnostics

    def edge_ids(self) -> tuple[str, ...]:
        """Return the edge ids of the route, in the direction of travel."""
        return tuple(segment.edge_id for segment in self._segments)

    # -- lookups -----------------------------------------------------------
    def edge_at(self, s_m: float) -> str:
        """Return the edge of the route that carries route distance *s_m*."""
        index, _ = self._segment_at(s_m)
        return self._segments[index].edge_id

    def at_route_distance(self, s_m: float) -> RoutePosition:
        """Return the :class:`RoutePosition` at route distance *s_m*.

        Raises
        ------
        RouteCoordinateError
            When *s_m* lies outside ``[0, route_length_m]`` (a tolerance of
            ``POSITION_TOLERANCE_M`` applies at both ends and is clamped).
        """
        index, offset_m = self._segment_at(s_m)
        segment = self._segments[index]
        if segment.traversal is EdgeTraversal.WITH_EDGE:
            local_position_m = offset_m
        else:
            local_position_m = segment.length_m - offset_m
        track = self._tracks[segment.edge_id]
        return RoutePosition(
            edge_id=segment.edge_id,
            traversal=segment.traversal,
            local_position_m=local_position_m,
            chainage_km=edge_position_to_chainage(track, local_position_m),
        )

    def chainage_to_route_distance(self, chainage_km: float) -> float:
        """Return the route distance ``s`` [m] of physical *chainage_km*.

        The chainage is resolved against the mapped range of each edge in the
        direction of travel.  A chainage that is not on this route is refused:
        the call raises :class:`RouteCoordinateError` (carrying the finding as a
        diagnostic) instead of fabricating a route distance.
        """
        for segment in self._segments:
            track = self._tracks[segment.edge_id]
            low_km, high_km = self._mapped_chainage_window(track)
            chainage = float(chainage_km)
            if chainage < low_km - CHAINAGE_TOLERANCE_KM or chainage > high_km + CHAINAGE_TOLERANCE_KM:
                continue
            position_m = chainage_to_edge_position(track, chainage)
            offset_m = (
                position_m
                if segment.traversal is EdgeTraversal.WITH_EDGE
                else segment.length_m - position_m
            )
            return segment.start_s_m + offset_m
        raise RouteCoordinateError(
            f"Chainage {float(chainage_km)} km is not on the route of path "
            f"'{self._path_id}' ({self._direction.value}); no route distance was computed.",
            diagnostic=_diagnostic(
                codes.VAL_REGISTRY_003,
                Severity.INFO,
                DiagnosticCategory.REGISTRY,
                (
                    f"Chainage {float(chainage_km)} km does not resolve on the route of path "
                    f"'{self._path_id}' ({self._direction.value}); the query was refused "
                    "rather than answered with an invented route distance."
                ),
                object_id=self._path_id,
                context={
                    "chainage_km": float(chainage_km),
                    "direction": self._direction.value,
                    "route_length_m": self.route_length_m,
                },
            ),
        )

    # -- internals ---------------------------------------------------------
    def _segment_at(self, s_m: float) -> tuple[int, float]:
        """Return ``(segment index, offset inside that segment)`` for *s_m*."""
        if not self._segments:
            raise RouteCoordinateError(
                f"Path '{self._path_id}' ({self._direction.value}) has no edges; "
                "no route distance can be resolved."
            )
        try:
            value = float(s_m)
        except (TypeError, ValueError) as exc:  # pragma: no cover - defensive
            raise RouteCoordinateError(
                f"Route distance {s_m!r} is not a number."
            ) from exc
        total = self.route_length_m
        if value < -POSITION_TOLERANCE_M or value > total + POSITION_TOLERANCE_M:
            raise RouteCoordinateError(
                f"Route distance {value} m is outside the route of path '{self._path_id}' "
                f"({self._direction.value}), which spans 0 .. {total} m."
            )
        if value <= 0.0:
            return 0, 0.0
        for index, segment in enumerate(self._segments):
            if value <= segment.end_s_m + POSITION_TOLERANCE_M:
                if index < len(self._segments) - 1 and value > segment.end_s_m:
                    # A value inside the closing tolerance belongs to the next edge.
                    return index + 1, value - self._segments[index + 1].start_s_m
                return index, min(value, segment.end_s_m) - segment.start_s_m
        last = len(self._segments) - 1
        return last, self._segments[last].length_m

    @staticmethod
    def _mapped_chainage_window(track: Track) -> tuple[float, float]:
        """Return the ``(low, high)`` mapped chainage range of *track*."""
        start_km = float(track.chainage_map.start_km)
        end_km = float(track.chainage_map.end_km)
        return (start_km, end_km) if start_km <= end_km else (end_km, start_km)


class CompiledNetwork:
    """The physical edges and declared train paths of one validated project.

    Produced by :func:`compile_network` and then read-only.  One instance per run
    (``D4``); route-coordinate systems are created per ``(train_path, direction)``
    through :meth:`route`.
    """

    def __init__(
        self,
        *,
        tracks: dict[str, Track],
        nodes: dict[str, TopologyNode],
        topology: InfrastructureTopology,
        declarations: dict[str, tuple[PathEdgeRef, ...]],
        diagnostics: tuple[Diagnostic, ...],
    ) -> None:
        self._tracks = dict(tracks)
        self._nodes = dict(nodes)
        self._topology = topology
        self._declarations = dict(declarations)
        self._diagnostics = tuple(diagnostics)

    # -- read-only surface -------------------------------------------------
    @property
    def diagnostics(self) -> tuple[Diagnostic, ...]:
        """Return every diagnostic produced while the network was compiled."""
        return self._diagnostics

    @property
    def path_ids(self) -> tuple[str, ...]:
        """Return the ids of the train paths declared by the project, in order."""
        return tuple(self._declarations)

    @property
    def edge_ids(self) -> tuple[str, ...]:
        """Return the ids of the physical edges of the network, in order."""
        return tuple(self._tracks)

    def declared_edges(self, path_id: str) -> tuple[PathEdgeRef, ...]:
        """Return the declared entries of *path_id* (empty when not declared)."""
        return self._declarations.get(path_id, ())

    def diagnostics_for(self, path_id: str) -> tuple[Diagnostic, ...]:
        """Return the diagnostics recorded for one declared path."""
        return tuple(d for d in self._diagnostics if d.object_id == path_id)

    def track(self, edge_id: str) -> Optional[Track]:
        """Return the physical edge with *edge_id*, or ``None``."""
        return self._tracks.get(edge_id)

    def node(self, node_id: str) -> Optional[TopologyNode]:
        """Return the topology node with *node_id*, or ``None``."""
        return self._nodes.get(node_id)

    # -- compilation -------------------------------------------------------
    def route(self, path_id: str, direction: Any = Direction.FORWARD) -> RouteCoordinateSystem:
        """Compile one declared path into a :class:`RouteCoordinateSystem`.

        ``FORWARD`` uses each declared entry as written; ``REVERSE`` walks the
        same physical edges in the reversed order with the complementary
        traversal.  Nothing in the loaded project is written.

        Raises
        ------
        RouteCoordinateError
            When the direction is not ``FORWARD``/``REVERSE``, when *path_id* is
            not declared, or when the declared path itself carries a reported
            defect (unknown edge, unusable traversal, sequence break).
        """
        resolved_direction = normalize_direction(direction)
        if resolved_direction is None:
            raw = _value_of(direction)
            raise RouteCoordinateError(
                f"Direction {raw!r} is not FORWARD or REVERSE; no route can be compiled.",
                diagnostic=_diagnostic(
                    codes.VAL_DIR_001,
                    Severity.ERROR,
                    DiagnosticCategory.DIR,
                    (
                        f"Direction value {raw!r} is missing or not a supported enumeration "
                        "value (expected FORWARD or REVERSE)."
                    ),
                    object_id=path_id or None,
                    context={"direction": raw},
                    suggested_action="Use FORWARD or REVERSE.",
                ),
            )
        if path_id not in self._declarations:
            raise RouteCoordinateError(
                f"Train path '{path_id}' is not declared by the project; "
                f"declared paths: {', '.join(self.path_ids) or '(none)'}.",
                diagnostic=_diagnostic(
                    codes.VAL_REGISTRY_003,
                    Severity.ERROR,
                    DiagnosticCategory.REGISTRY,
                    (
                        f"Train path reference '{path_id}' does not resolve to a declared "
                        f"train path ({', '.join(self.path_ids) or 'none declared'})."
                    ),
                    object_id=path_id or None,
                    context={"declared_path_ids": list(self.path_ids)},
                    suggested_action="Declare the train path in train_paths.paths or correct the id.",
                ),
            )
        refs = self._declarations[path_id]
        path_diagnostics = self.diagnostics_for(path_id)
        blocking = [d for d in path_diagnostics if d.severity is Severity.ERROR]
        if blocking:
            first = blocking[0]
            raise RouteCoordinateError(
                f"Train path '{path_id}' cannot be compiled: {first.message}",
                diagnostic=first,
            )

        ordered = list(refs)
        if resolved_direction is Direction.REVERSE:
            ordered = [
                PathEdgeRef(
                    edge_id=ref.edge_id,
                    traversal=complementary_traversal(ref.traversal),  # type: ignore[arg-type]
                    index=len(refs) - 1 - ref.index,
                )
                for ref in reversed(refs)
            ]

        segments: list[RouteSegment] = []
        start_s_m = 0.0
        tracks: dict[str, Track] = {}
        for ref in ordered:
            track = self._tracks[ref.edge_id]
            tracks[ref.edge_id] = track
            length_m = float(track.length_m)
            segments.append(
                RouteSegment(
                    edge_id=ref.edge_id,
                    traversal=ref.traversal,  # type: ignore[arg-type]
                    start_s_m=start_s_m,
                    length_m=length_m,
                )
            )
            start_s_m += length_m
        return RouteCoordinateSystem(
            path_id=path_id,
            direction=resolved_direction,
            segments=segments,
            tracks=tracks,
            diagnostics=path_diagnostics,
        )

    # -- node continuity helpers (used by compilation and by reporting) ----
    def entry_node(self, edge_id: str, traversal: EdgeTraversal) -> Optional[str]:
        """Return the node a train reaches *first* on *edge_id* with *traversal*."""
        track = self._tracks.get(edge_id)
        if track is None:
            return None
        return track.from_node if traversal is EdgeTraversal.WITH_EDGE else track.to_node

    def exit_node(self, edge_id: str, traversal: EdgeTraversal) -> Optional[str]:
        """Return the node a train reaches *last* on *edge_id* with *traversal*."""
        track = self._tracks.get(edge_id)
        if track is None:
            return None
        return track.to_node if traversal is EdgeTraversal.WITH_EDGE else track.from_node


def _read_declarations(
    raw_paths: Any,
    tracks: dict[str, Track],
) -> tuple[dict[str, tuple[PathEdgeRef, ...]], list[Diagnostic]]:
    """Read ``train_paths.paths`` into path declarations plus diagnostics."""
    declarations: dict[str, tuple[PathEdgeRef, ...]] = {}
    diagnostics: list[Diagnostic] = []
    if raw_paths is None:
        return declarations, diagnostics
    if not isinstance(raw_paths, list):
        diagnostics.append(
            _diagnostic(
                codes.VAL_ID_002,
                Severity.ERROR,
                DiagnosticCategory.ID,
                "train_paths.paths is not a list; no train path could be read.",
                object_id="train_paths.paths",
                context={"type": type(raw_paths).__name__},
            )
        )
        return declarations, diagnostics

    for position, record in enumerate(raw_paths):
        if not isinstance(record, dict):
            diagnostics.append(
                _diagnostic(
                    codes.VAL_ID_002,
                    Severity.ERROR,
                    DiagnosticCategory.ID,
                    f"Train path #{position} is not an object; it was not read.",
                    object_id=f"train_paths.paths[{position}]",
                    context={"type": type(record).__name__},
                )
            )
            continue
        path_id = record.get(PATH_ID_FIELD)
        if not isinstance(path_id, str) or not path_id.strip():
            diagnostics.append(
                _diagnostic(
                    codes.VAL_ID_002,
                    Severity.ERROR,
                    DiagnosticCategory.ID,
                    f"Train path #{position} carries no usable id; it was not read.",
                    object_id=f"train_paths.paths[{position}]",
                    context={"id": path_id},
                )
            )
            continue
        path_id = path_id.strip()
        if path_id in declarations:
            diagnostics.append(
                _diagnostic(
                    codes.VAL_ID_001,
                    Severity.ERROR,
                    DiagnosticCategory.ID,
                    f"Train path id '{path_id}' is declared more than once.",
                    object_id=path_id,
                )
            )
            continue

        raw_edges = record.get(PATH_EDGES_FIELD)
        if not isinstance(raw_edges, list) or not raw_edges:
            diagnostics.append(
                _diagnostic(
                    codes.VAL_TOPO_007,
                    Severity.ERROR,
                    DiagnosticCategory.TOPOLOGY,
                    (
                        f"Train path '{path_id}' declares no usable edge sequence "
                        f"({type(raw_edges).__name__}); a route cannot be compiled."
                    ),
                    object_id=path_id,
                    context={"edges": raw_edges},
                )
            )
            continue

        refs: list[PathEdgeRef] = []
        for index, raw_entry in enumerate(raw_edges):
            if not isinstance(raw_entry, dict):
                diagnostics.append(
                    _diagnostic(
                        codes.VAL_ID_002,
                        Severity.ERROR,
                        DiagnosticCategory.ID,
                        (
                            f"Train path '{path_id}' entry {index} is not an object; "
                            "the declared entry was not replaced."
                        ),
                        object_id=path_id,
                        context={"index": index, "type": type(raw_entry).__name__},
                    )
                )
                continue
            edge_id = raw_entry.get(PATH_EDGE_ID_FIELD)
            if not isinstance(edge_id, str) or not edge_id.strip():
                diagnostics.append(
                    _diagnostic(
                        codes.VAL_ID_002,
                        Severity.ERROR,
                        DiagnosticCategory.ID,
                        (
                            f"Train path '{path_id}' entry {index} carries no usable "
                            f"edge_id ({edge_id!r}); the entry was not replaced."
                        ),
                        object_id=path_id,
                        context={"index": index, "edge_id": edge_id},
                    )
                )
                continue
            edge_id = edge_id.strip()
            if edge_id not in tracks:
                diagnostics.append(
                    _diagnostic(
                        codes.VAL_REGISTRY_003,
                        Severity.ERROR,
                        DiagnosticCategory.REGISTRY,
                        (
                            f"Train path '{path_id}' entry {index} references edge "
                            f"'{edge_id}', which does not resolve to a registered track."
                        ),
                        object_id=path_id,
                        context={"index": index, "edge_id": edge_id},
                        suggested_action="Correct the edge_id or register the missing track.",
                    )
                )
                continue
            traversal = _declared_traversal(raw_entry.get(PATH_TRAVERSAL_FIELD))
            if traversal is None:
                diagnostics.append(
                    _diagnostic(
                        codes.VAL_ENUM_001,
                        Severity.ERROR,
                        DiagnosticCategory.ENUM,
                        (
                            f"Train path '{path_id}' entry {index} declares traversal "
                            f"{raw_entry.get(PATH_TRAVERSAL_FIELD)!r}, which is not "
                            "WITH_EDGE or AGAINST_EDGE."
                        ),
                        object_id=path_id,
                        context={
                            "index": index,
                            "edge_id": edge_id,
                            "traversal": raw_entry.get(PATH_TRAVERSAL_FIELD),
                        },
                        suggested_action="Declare WITH_EDGE or AGAINST_EDGE for every entry.",
                    )
                )
                continue
            refs.append(PathEdgeRef(edge_id=edge_id, traversal=traversal, index=index))

        if len(refs) != len(raw_edges):
            # An entry could not be read: the sequence is incomplete, so the path
            # is recorded with the entries that were read (for reporting) and is
            # refused by route() because it carries an ERROR diagnostic.
            declarations[path_id] = tuple(refs)
            continue

        continuous, break_message = _sequence_is_continuous(refs, tracks)
        if not continuous:
            diagnostics.append(
                _diagnostic(
                    codes.VAL_TOPO_007,
                    Severity.ERROR,
                    DiagnosticCategory.TOPOLOGY,
                    (
                        f"Train path '{path_id}' has an edge-sequence break: {break_message}"
                    ),
                    object_id=path_id,
                    context={"edge_ids": [ref.edge_id for ref in refs]},
                    suggested_action=(
                        "Correct the declared edge order, or add the missing connecting edge."
                    ),
                )
            )
        declarations[path_id] = tuple(refs)
    return declarations, diagnostics


def _sequence_is_continuous(
    refs: Sequence[PathEdgeRef],
    tracks: dict[str, Track],
) -> tuple[bool, str]:
    """Return whether consecutive entries meet at one topology node."""
    for previous, current in zip(refs, refs[1:]):
        prev_track = tracks[previous.edge_id]
        cur_track = tracks[current.edge_id]
        prev_exit = (
            prev_track.to_node
            if previous.traversal is EdgeTraversal.WITH_EDGE
            else prev_track.from_node
        )
        cur_entry = (
            cur_track.from_node
            if current.traversal is EdgeTraversal.WITH_EDGE
            else cur_track.to_node
        )
        if prev_exit != cur_entry:
            return (
                False,
                (
                    f"entry {current.index} ('{current.edge_id}') enters at {cur_entry} "
                    f"but entry {previous.index} ('{previous.edge_id}') exits at {prev_exit}"
                ),
            )
    return True, ""


def _paths_from_mapping(source: Any) -> tuple[Optional[list], Optional[str]]:
    """Return ``(raw paths, problem)`` from a mapping/document-like *source*."""
    container = source.get(PATH_CONTAINER_FIELD, source)
    if isinstance(container, dict) and "paths" in container:
        container = container["paths"]
    if isinstance(container, list):
        return container, None
    return None, (
        "the declared-paths source carries no '"
        f"{PATH_CONTAINER_FIELD}.paths' list (found {type(container).__name__})."
    )


def read_declared_paths(source: Any) -> tuple[Optional[list], Optional[str]]:
    """Read the declared-paths list of a companion document or project document.

    *source* may be a mapping, JSON text, a :class:`pathlib.Path`, or a string
    naming an existing JSON file.  Returns ``(paths, problem)``: exactly one of
    the two is ``None``.  No value is ever guessed, repaired or dropped here.
    """
    if source is None:
        return None, "no declared-paths source was supplied."
    if isinstance(source, dict):
        return _paths_from_mapping(source)
    if isinstance(source, (bytes, bytearray)):
        source = bytes(source).decode("utf-8", errors="strict")
    if isinstance(source, Path):
        try:
            return _paths_from_mapping(json.loads(source.read_text(encoding="utf-8")))
        except (OSError, ValueError) as exc:
            return None, f"the declared-paths file '{source}' could not be read: {exc}."
    if isinstance(source, str):
        text = source
        try:
            return _paths_from_mapping(json.loads(text))
        except ValueError:
            candidate = Path(text)
            if "\n" not in text and len(text) < 512 and candidate.is_file():
                try:
                    return _paths_from_mapping(json.loads(candidate.read_text(encoding="utf-8")))
                except (OSError, ValueError) as exc:
                    return None, f"the declared-paths file '{text}' could not be read: {exc}."
        return None, "the declared-paths text is not a readable JSON document."
    return None, f"unsupported declared-paths source ({type(source).__name__})."


def compile_network(project: Any, *, paths_source: Any = None) -> CompiledNetwork:
    """Compile the physical network and the declared train paths of *project*.

    ``project`` is a validated Phase-2/Phase-3 :class:`~railway_headway_sim.models.project.Project`
    (or anything exposing ``infrastructure`` and ``train_paths`` in the same
    shape).  The call is read-only: it never writes to the project, to the
    document it came from, or to any cached dictionary derived from them.

    ``paths_source`` may be omitted (the project's own ``train_paths.paths`` is
    read, as before) or may be a companion declared-paths document - a mapping,
    JSON text, or a :class:`pathlib.Path` holding ``examples/GRR-01-paths.json``.
    The *project* always supplies the physical edges; only the declared paths come
    from the companion document.  An unreadable source is reported through the
    standard diagnostic model and no path is invented for it.

    The returned :class:`CompiledNetwork` carries every diagnostic produced while
    reading the declared paths; a declared path that carries an ERROR diagnostic
    is refused by :meth:`CompiledNetwork.route` rather than silently repaired.
    """
    infrastructure = getattr(project, "infrastructure", None)
    if not isinstance(infrastructure, list):
        raise RouteCoordinateError(
            "The project does not expose an infrastructure array; no network can be compiled."
        )
    compiled: CompiledInfrastructure = compile_infrastructure(infrastructure)
    tracks: dict[str, Track] = compiled.by_id("tracks")
    nodes: dict[str, TopologyNode] = compiled.by_id("nodes")
    topology = InfrastructureTopology.from_objects(nodes.values(), tracks.values())

    if paths_source is None:
        train_paths = getattr(project, "train_paths", None)
        raw_paths = getattr(train_paths, "paths", None) if train_paths is not None else None
    else:
        raw_paths, problem = read_declared_paths(paths_source)
        if problem is not None:
            diagnostics = [
                _diagnostic(
                    codes.VAL_REGISTRY_003,
                    Severity.ERROR,
                    DiagnosticCategory.REGISTRY,
                    (
                        "The declared-paths source could not be read, so no train path was "
                        f"compiled from it: {problem}"
                    ),
                    object_id="paths_source",
                    context={"source_kind": type(paths_source).__name__},
                    suggested_action=(
                        "Supply a companion document with a 'train_paths.paths' list, its JSON "
                        "text, or the path of such a file."
                    ),
                )
            ]
            return CompiledNetwork(
                tracks=tracks,
                nodes=nodes,
                topology=topology,
                declarations={},
                diagnostics=tuple(diagnostics),
            )
    declarations, diagnostics = _read_declarations(raw_paths, tracks)
    return CompiledNetwork(
        tracks=tracks,
        nodes=nodes,
        topology=topology,
        declarations=declarations,
        diagnostics=tuple(sorted(diagnostics, key=lambda diagnostic: diagnostic.sort_key())),
    )
