"""Static infrastructure topology graph utility.

Deterministic adjacency representation over typed nodes/tracks. Connectivity is
established **only** by node identity - chainage equality is never used as a
connectivity criterion (Section W).

Deliberately no routing algorithms yet: this module offers adjacency,
components, incident-edge queries and edge-sequence continuity checks, which is
what Phase-2 validation and the UI need.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Iterable, Iterator, Optional

from ..models.base import ContainerBase
from ..models.enums import Directionality

if TYPE_CHECKING:  # pragma: no cover - typing only
    from ..models.infrastructure import TopologyNode


@dataclass(frozen=True)
class EdgesFromNode:
    """Edges incident to a node, grouped by orientation."""

    node_id: str
    outgoing: tuple[str, ...]
    incoming: tuple[str, ...]

    @property
    def all_edges(self) -> tuple[str, ...]:
        """Return outgoing then incoming edge IDs."""
        return self.outgoing + self.incoming

    @property
    def degree(self) -> int:
        """Return the number of incident edges (self-loops counted once per side)."""
        return len(self.outgoing) + len(self.incoming)


@dataclass(frozen=True)
class ConnectivityReport:
    """Result of the connected-component inspection."""

    component_count: int
    largest_component: tuple[str, ...]
    components: tuple[tuple[str, ...], ...]
    isolated_nodes: tuple[str, ...]

    @property
    def is_connected(self) -> bool:
        """Return ``True`` when every node belongs to one component."""
        return self.component_count <= 1

    def describe(self) -> str:
        """Return a short human description of the connectivity."""
        return (
            f"{self.component_count} connected component(s); largest has "
            f"{len(self.largest_component)} node(s); "
            f"{len(self.isolated_nodes)} isolated node(s)"
        )


@dataclass(frozen=True)
class EdgeSequenceCheck:
    """Result of verifying a supplied edge sequence for node continuity."""

    is_continuous: bool
    breaks: tuple[str, ...]
    missing_edges: tuple[str, ...]
    path_nodes: tuple[str, ...] = ()

    def describe(self) -> str:
        """Return a short human description of the sequence check."""
        if self.is_continuous:
            return f"edge sequence is continuous ({len(self.path_nodes)} node(s) visited)"
        parts = []
        if self.missing_edges:
            parts.append("unknown edges: " + ", ".join(self.missing_edges))
        if self.breaks:
            parts.append("continuity breaks: " + ", ".join(self.breaks))
        return "; ".join(parts)


@dataclass
class InfrastructureTopology:
    """Adjacency graph over the tracks of one compiled infrastructure.

    Tracks are treated as *directed* edges (``from_node`` -> ``to_node``) for
    containment queries, while traversal eligibility follows the declared
    ``directionality``:

    ``BOTH``         - traversable in both orientations
    ``FORWARD_ONLY`` - traversable in the stored orientation only
    ``REVERSE_ONLY`` - traversable against the stored orientation only

    Traversal eligibility deliberately does **not** affect connected components
    or edge-sequence continuity: those are physical-connectivity properties,
    while eligibility is operational metadata.
    """

    nodes: dict[str, "TopologyNode"] = field(default_factory=dict)
    tracks: dict[str, ContainerBase] = field(default_factory=dict)
    _outgoing: dict[str, list[str]] = field(default_factory=dict)
    _incoming: dict[str, list[str]] = field(default_factory=dict)

    # -- construction ------------------------------------------------------
    def add_node(self, node: "TopologyNode") -> None:
        """Add a topology node."""
        self.nodes[node.id] = node
        self._outgoing.setdefault(node.id, [])
        self._incoming.setdefault(node.id, [])

    def add_track(self, track: ContainerBase) -> None:
        """Add a track edge (endpoints are registered as adjacency entries)."""
        self.tracks[track.id] = track
        self._outgoing.setdefault(track.from_node, []).append(track.id)
        self._incoming.setdefault(track.to_node, []).append(track.id)

    @classmethod
    def from_objects(
        cls,
        nodes: Iterable["TopologyNode"],
        tracks: Iterable[ContainerBase],
    ) -> "InfrastructureTopology":
        """Build a topology from typed nodes and tracks."""
        topology = cls()
        for node in nodes:
            topology.add_node(node)
        for track in tracks:
            topology.add_track(track)
        return topology

    # -- queries -----------------------------------------------------------
    def node(self, node_id: str) -> Optional["TopologyNode"]:
        """Return the node with *node_id*, or ``None``."""
        return self.nodes.get(node_id)

    def track(self, track_id: str) -> Optional[ContainerBase]:
        """Return the track with *track_id*, or ``None``."""
        return self.tracks.get(track_id)

    def node_ids(self) -> tuple[str, ...]:
        """Return all node IDs in insertion order."""
        return tuple(self.nodes)

    def track_ids(self) -> tuple[str, ...]:
        """Return all track IDs in insertion order."""
        return tuple(self.tracks)

    def edges_from_node(self, node_id: str) -> EdgesFromNode:
        """Return the edges incident to *node_id* (outgoing and incoming)."""
        return EdgesFromNode(
            node_id=node_id,
            outgoing=tuple(self._outgoing.get(node_id, ())),
            incoming=tuple(self._incoming.get(node_id, ())),
        )

    def incident_edges(self, node_id: str) -> tuple[str, ...]:
        """Return every edge ID incident to *node_id* (outgoing then incoming)."""
        return self.edges_from_node(node_id).all_edges

    def is_traversable(self, track_id: str, with_edge: bool) -> bool:
        """Return whether a track may be traversed in the given orientation."""
        track = self.tracks.get(track_id)
        if track is None:
            return False
        directionality = getattr(track.directionality, "value", track.directionality)
        if directionality == Directionality.BOTH.value:
            return True
        if with_edge:
            return directionality == Directionality.FORWARD_ONLY.value
        return directionality == Directionality.REVERSE_ONLY.value

    def traversable_edges(self, node_id: str, *, with_edge: bool) -> tuple[str, ...]:
        """Return incident edges of *node_id* traversable in the given orientation."""
        return tuple(
            track_id
            for track_id in self.incident_edges(node_id)
            if self.is_traversable(track_id, with_edge)
        )

    # -- component inspection ---------------------------------------------
    def component_of(self, node_id: str) -> tuple[str, ...]:
        """Return all node IDs of the undirected component containing *node_id*."""
        if node_id not in self._outgoing and node_id not in self._incoming:
            return ()
        visited: set[str] = set()
        stack = [node_id]
        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)
            for track_id in self.incident_edges(current):
                track = self.tracks[track_id]
                neighbour = track.to_node if track.from_node == current else track.from_node
                stack.append(neighbour)
        return tuple(node for node in self._outgoing if node in visited)

    def connectivity(self) -> ConnectivityReport:
        """Return the connected-component report over all graph nodes."""
        adjacency_nodes = [node for node in self._outgoing]
        seen: set[str] = set()
        components: list[tuple[str, ...]] = []
        for node_id in adjacency_nodes:
            if node_id in seen:
                continue
            component = self.component_of(node_id)
            seen.update(component)
            components.append(component)
        isolated = tuple(node for node in components if len(node) == 1)
        largest = max(components, key=len) if components else ()
        return ConnectivityReport(
            component_count=len(components),
            largest_component=largest,
            components=tuple(components),
            isolated_nodes=tuple(node for component in isolated for node in component),
        )

    def is_connected(self) -> bool:
        """Return ``True`` when the whole infrastructure forms one component."""
        return self.connectivity().is_connected

    # -- sequence checks ---------------------------------------------------
    def check_edge_sequence(self, edge_ids: Iterable[str]) -> EdgeSequenceCheck:
        """Verify that a supplied edge sequence is continuous (node continuity).

        Only node identity establishes continuity: consecutive edges must share
        the node reached by the previous edge (in the stored orientation of the
        sequence). Chainage proximity is never used.
        """
        sequence = list(edge_ids)
        missing = tuple(edge_id for edge_id in sequence if edge_id not in self.tracks)
        if not sequence:
            return EdgeSequenceCheck(is_continuous=False, breaks=("empty sequence",), missing_edges=missing)

        breaks: list[str] = []
        current_node: Optional[str] = None
        path_nodes: list[str] = []
        for index, edge_id in enumerate(sequence):
            track = self.tracks.get(edge_id)
            if track is None:
                breaks.append(f"edge {index} ('{edge_id}') is unknown")
                current_node = None
                continue
            if current_node is None:
                current_node = track.from_node
                path_nodes.append(current_node)
            if track.from_node != current_node:
                # The edge may still be traversable as a reverse-oriented step
                # of the sequence; that is a continuity break only when the
                # previous edge did not end at this edge's to_node either.
                breaks.append(
                    f"edge {index} ('{edge_id}') starts at {track.from_node} "
                    f"but the sequence reached {current_node}"
                )
                current_node = track.to_node
                path_nodes.append(current_node)
                continue
            current_node = track.to_node
            path_nodes.append(current_node)
        return EdgeSequenceCheck(
            is_continuous=not breaks and not missing,
            breaks=tuple(breaks),
            missing_edges=missing,
            path_nodes=tuple(path_nodes),
        )

    def check_undirected_sequence(self, edge_ids: Iterable[str]) -> EdgeSequenceCheck:
        """Verify continuity when edges may be traversed in either stored orientation.

        Used for BOTH-direction infrastructure checks (Section AT): the physical
        chain is continuous when consecutive edges share *a* node, in either
        orientation.
        """
        sequence = list(edge_ids)
        missing = tuple(edge_id for edge_id in sequence if edge_id not in self.tracks)
        if not sequence:
            return EdgeSequenceCheck(is_continuous=False, breaks=("empty sequence",), missing_edges=missing)

        breaks: list[str] = []
        path_nodes: list[str] = []
        first = self.tracks[sequence[0]]
        path_nodes.extend([first.from_node, first.to_node])
        for index, edge_id in enumerate(sequence[1:], start=1):
            previous = self.tracks[sequence[index - 1]]
            track = self.tracks.get(edge_id)
            if track is None:
                breaks.append(f"edge {index} ('{edge_id}') is unknown")
                continue
            shared = {
                previous.from_node,
                previous.to_node,
            } & {track.from_node, track.to_node}
            if not shared:
                breaks.append(
                    f"edge {index} ('{edge_id}') shares no node with the previous edge "
                    f"('{previous.id}')"
                )
                continue
            if previous.to_node in (track.from_node, track.to_node):
                next_node = track.to_node if previous.to_node == track.from_node else track.from_node
            else:
                next_node = track.from_node if previous.to_node == track.to_node else track.to_node
            path_nodes.append(next_node)
        return EdgeSequenceCheck(
            is_continuous=not breaks and not missing,
            breaks=tuple(breaks),
            missing_edges=missing,
            path_nodes=tuple(path_nodes),
        )

    # -- reporting ---------------------------------------------------------
    def summary_rows(self) -> list[tuple[str, object]]:
        """Return UI-ready summary rows of the graph."""
        report = self.connectivity()
        return [
            ("Nodes", len(self.nodes)),
            ("Track edges", len(self.tracks)),
            ("Connected components", report.component_count),
            ("Largest component (nodes)", len(report.largest_component)),
            ("Isolated nodes", len(report.isolated_nodes)),
            ("Infrastructure connected", "yes" if report.is_connected else "no"),
        ]

    def __iter__(self) -> Iterator[str]:
        """Iterate over node IDs."""
        return iter(self.nodes)
