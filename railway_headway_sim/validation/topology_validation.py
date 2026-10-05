"""Phase-2 topology validation: nodes, edges, track groups and chainage maps.

Connectivity and sequence checks live here too; they use node identity only and
never chainage equality (Section W).
"""

from __future__ import annotations

from typing import Any, Iterable, Optional

from ..infrastructure.compiler import CompiledInfrastructure
from ..infrastructure.mapping import CHAINAGE_TOLERANCE_KM
from ..infrastructure.topology import InfrastructureTopology
from ..models.diagnostics import Diagnostic
from ..models.enums import DiagnosticCategory, Severity
from . import codes
from .infrastructure_support import (
    is_finite_number,
    pairs_of,
    reference_alignment,
)

#: Baseline policy: a physical project's infrastructure must be connected
#: (Section W). Documented default of this build; disable only deliberately.
REQUIRE_CONNECTED_INFRASTRUCTURE = True


# ---------------------------------------------------------------------------
# topology
# ---------------------------------------------------------------------------
def _check_nodes(compiled: CompiledInfrastructure) -> list[Diagnostic]:
    """Node chainage bounds and station references."""
    diagnostics: list[Diagnostic] = []
    bound_alignment = reference_alignment(compiled)
    for node, path in pairs_of(compiled, "nodes"):
        if node.station_id is not None and not compiled.registry.has_type_of(node.station_id, "station"):
            diagnostics.append(
                Diagnostic(
                    code=codes.VAL_TOPO_006,
                    severity=Severity.ERROR,
                    category=DiagnosticCategory.TOPOLOGY,
                    message=(
                        f"Topology node '{node.id}' references station '{node.station_id}' "
                        "which is not a registered station."
                    ),
                    object_id=node.id,
                    context={"field": f"{path}.station_id", "reference": node.station_id},
                    suggested_action="Create the station or correct node.station_id.",
                )
            )
        if bound_alignment is not None:
            chainage = float(node.chainage_km)
            if (
                chainage < float(bound_alignment.start_chainage_km) - CHAINAGE_TOLERANCE_KM
                or chainage > float(bound_alignment.end_chainage_km) + CHAINAGE_TOLERANCE_KM
            ):
                diagnostics.append(
                    Diagnostic(
                        code=codes.VAL_TOPO_004,
                        severity=Severity.ERROR,
                        category=DiagnosticCategory.TOPOLOGY,
                        message=(
                            f"Topology node '{node.id}' at {node.chainage_km} km lies outside the "
                            f"reference alignment '{bound_alignment.id}' "
                            f"[{bound_alignment.start_chainage_km}, {bound_alignment.end_chainage_km}] km."
                        ),
                        object_id=node.id,
                        context={"field": f"{path}.chainage_km"},
                        suggested_action="Move the node inside the reference alignment.",
                    )
                )
    return diagnostics


def _check_tracks(compiled: CompiledInfrastructure) -> list[Diagnostic]:
    """Edge endpoints, lengths, directionality, track group and chainage map."""
    diagnostics: list[Diagnostic] = []
    bound_alignment = reference_alignment(compiled)
    for track, path in pairs_of(compiled, "tracks"):
        for field_name in ("from_node", "to_node"):
            node_id = getattr(track, field_name)
            if not compiled.registry.has_type_of(node_id, "node"):
                diagnostics.append(
                    Diagnostic(
                        code=codes.VAL_TOPO_001,
                        severity=Severity.ERROR,
                        category=DiagnosticCategory.TOPOLOGY,
                        message=(
                            f"Track '{track.id}' {field_name} '{node_id}' does not resolve to a "
                            "registered topology node."
                        ),
                        object_id=track.id,
                        context={"field": f"{path}.{field_name}", "reference": node_id},
                        suggested_action="Create the node or correct the endpoint reference.",
                    )
                )
        if track.from_node == track.to_node:
            diagnostics.append(
                Diagnostic(
                    code=codes.VAL_TOPO_002,
                    severity=Severity.ERROR,
                    category=DiagnosticCategory.TOPOLOGY,
                    message=f"Track '{track.id}' has the same node at both ends ('{track.from_node}').",
                    object_id=track.id,
                    context={"field": path, "node": track.from_node},
                    suggested_action="Connect the track between two distinct nodes.",
                )
            )
        length = track.length_m
        if not isinstance(length, (int, float)) or isinstance(length, bool) or float(length) <= 0:
            diagnostics.append(
                Diagnostic(
                    code=codes.VAL_TOPO_003,
                    severity=Severity.ERROR,
                    category=DiagnosticCategory.TOPOLOGY,
                    message=f"Track '{track.id}' has length_m = {length!r} (must be > 0).",
                    object_id=track.id,
                    context={"field": f"{path}.length_m", "found": length},
                    suggested_action="Provide a positive physical length in metres.",
                )
            )
        if track.track_group_id is not None and not compiled.registry.has_type_of(
            track.track_group_id, "track_group"
        ):
            diagnostics.append(
                Diagnostic(
                    code=codes.VAL_TOPO_005,
                    severity=Severity.ERROR,
                    category=DiagnosticCategory.TOPOLOGY,
                    message=(
                        f"Track '{track.id}' references track group '{track.track_group_id}' "
                        "which is not registered."
                    ),
                    object_id=track.id,
                    context={"field": f"{path}.track_group_id", "reference": track.track_group_id},
                    suggested_action="Create the track group or correct track.track_group_id.",
                )
            )
        diagnostics.extend(
            _check_chainage_map(track, path, bound_alignment)
        )
    return diagnostics


def _check_chainage_map(track: Any, path: str, bound_alignment: Optional[Any]) -> list[Diagnostic]:
    """Validate the LINEAR chainage map of one track."""
    diagnostics: list[Diagnostic] = []
    chainage_map = track.chainage_map
    start = chainage_map.start_km
    end = chainage_map.end_km
    if not is_finite_number(start) or not is_finite_number(end):
        diagnostics.append(
            Diagnostic(
                code=codes.VAL_TOPO_004,
                severity=Severity.ERROR,
                category=DiagnosticCategory.TOPOLOGY,
                message=(
                    f"Track '{track.id}' chainage_map has non-finite values "
                    f"(start_km={start!r}, end_km={end!r})."
                ),
                object_id=track.id,
                context={"field": f"{path}.chainage_map"},
                suggested_action="Provide finite chainage map values in kilometres.",
            )
        )
        return diagnostics
    if abs(float(end) - float(start)) <= CHAINAGE_TOLERANCE_KM:
        diagnostics.append(
            Diagnostic(
                code=codes.VAL_TOPO_004,
                severity=Severity.ERROR,
                category=DiagnosticCategory.TOPOLOGY,
                message=(
                    f"Track '{track.id}' chainage_map covers a degenerate range "
                    f"({start} -> {end} km); position-to-chainage mapping is not invertible. "
                    "A decreasing map (start_km > end_km) is accepted as a track laid out in "
                    "decreasing chainage, but a zero-length range is not."
                ),
                object_id=track.id,
                context={"field": f"{path}.chainage_map", "start_km": start, "end_km": end},
                suggested_action="Provide a non-degenerate chainage map range.",
            )
        )
    if bound_alignment is not None:
        low = float(bound_alignment.start_chainage_km)
        high = float(bound_alignment.end_chainage_km)
        for field_name, value in (("start_km", float(start)), ("end_km", float(end))):
            if value < low - CHAINAGE_TOLERANCE_KM or value > high + CHAINAGE_TOLERANCE_KM:
                diagnostics.append(
                    Diagnostic(
                        code=codes.VAL_TOPO_004,
                        severity=Severity.ERROR,
                        category=DiagnosticCategory.TOPOLOGY,
                        message=(
                            f"Track '{track.id}' chainage_map.{field_name} = {value} km lies outside "
                            f"the reference alignment '{bound_alignment.id}' [{low}, {high}] km."
                        ),
                        object_id=track.id,
                        context={"field": f"{path}.chainage_map.{field_name}", "found": value},
                        suggested_action="Move the mapped chainage inside the alignment range.",
                    )
                )
    return diagnostics


def _check_chainage_reconciliation(compiled: CompiledInfrastructure) -> list[Diagnostic]:
    """Reconcile Phase-1 ``chainages[]`` records with typed track chainage maps.

    Documented, deterministic rule (tolerance ``CHAINAGE_TOLERANCE_KM`` = 1e-9 km,
    i.e. one micrometre):

    * a legacy record that names a track (``track_id``) and carries
      ``chainage_km`` must place that chainage exactly on a mapped boundary of the
      named track (``chainage_map.start_km`` or ``chainage_map.end_km``);
    * a legacy record that carries ``start_km``/``end_km`` must match the named
      track's mapped range on both sides;
    * any deviation larger than the tolerance is an ERROR (``VAL-TOPO-008``);
    * records that do not resolve to a typed track are opaque extension data and
      are deliberately left unreconciled (they are preserved, not rewritten).

    ``VAL-REF-001`` is unaffected: it stays scoped to
    ``reference_system.chainage_start_km``/``chainage_end_km``.
    """
    diagnostics: list[Diagnostic] = []
    tracks_by_id = compiled.by_id("tracks")
    for catalogue, _layer_path, path, record in compiled.legacy_records:
        if catalogue != "chainages" or not isinstance(record, dict):
            continue
        track_id = record.get("track_id") or record.get("edge_id")
        if not isinstance(track_id, str) or track_id not in tracks_by_id:
            continue
        track = tracks_by_id[track_id]
        start = float(track.chainage_map.start_km)
        end = float(track.chainage_map.end_km)
        pairs: list[tuple[str, float, float]] = []
        if "start_km" in record or "end_km" in record:
            if "start_km" in record:
                pairs.append(("start_km", _as_number(record.get("start_km")), start))
            if "end_km" in record:
                pairs.append(("end_km", _as_number(record.get("end_km")), end))
        elif "chainage_km" in record:
            value = _as_number(record.get("chainage_km"))
            nearest = start if abs(value - start) <= abs(value - end) else end
            pairs.append(("chainage_km", value, nearest))
        for field_name, legacy_value, mapped_value in pairs:
            if legacy_value is None:
                diagnostics.append(
                    _reconciliation_diagnostic(
                        track_id,
                        path,
                        field_name,
                        None,
                        mapped_value,
                        "the value is not a number",
                    )
                )
                continue
            if abs(legacy_value - mapped_value) > CHAINAGE_TOLERANCE_KM:
                diagnostics.append(
                    _reconciliation_diagnostic(
                        track_id, path, field_name, legacy_value, mapped_value, ""
                    )
                )
    return diagnostics


def _as_number(value: object) -> Optional[float]:
    """Return *value* as a float when it is a JSON number, else ``None``."""
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _reconciliation_diagnostic(
    track_id: str,
    path: str,
    field_name: str,
    legacy_value: Optional[float],
    mapped_value: float,
    note: str,
) -> Diagnostic:
    """Build one VAL-TOPO-008 reconciliation diagnostic."""
    detail = note or (
        f"legacy {field_name}={legacy_value!r} km vs mapped {mapped_value!r} km "
        f"(tolerance {CHAINAGE_TOLERANCE_KM} km)"
    )
    return Diagnostic(
        code=codes.VAL_TOPO_008,
        severity=Severity.ERROR,
        category=DiagnosticCategory.TOPOLOGY,
        message=(
            f"Track '{track_id}' is inconsistent with the Phase-1 infrastructure "
            f"chainages[] record at {path}: {detail}."
        ),
        object_id=track_id,
        context={
            "field": f"{path}.{field_name}",
            "legacy_value_km": legacy_value,
            "mapped_value_km": mapped_value,
            "tolerance_km": CHAINAGE_TOLERANCE_KM,
        },
        suggested_action=(
            "Reconcile the legacy chainages[] entry with the typed track chainage map, or "
            "remove the legacy entry once the track carries the authoritative mapping."
        ),
    )


def build_topology(compiled: CompiledInfrastructure) -> InfrastructureTopology:
    """Build the static topology graph of a compiled infrastructure."""
    return InfrastructureTopology.from_objects(
        nodes=compiled.catalogue("nodes"),
        tracks=compiled.catalogue("tracks"),
    )


def check_required_connectivity(
    compiled: CompiledInfrastructure,
    *,
    require_connected: bool = REQUIRE_CONNECTED_INFRASTRUCTURE,
) -> list[Diagnostic]:
    """Verify that the baseline infrastructure forms one connected graph."""
    if not compiled.physical or not require_connected:
        return []
    topology = build_topology(compiled)
    if not topology.nodes:
        return []
    report = topology.connectivity()
    if report.is_connected:
        return []
    return [
        Diagnostic(
            code=codes.VAL_TOPO_007,
            severity=Severity.ERROR,
            category=DiagnosticCategory.TOPOLOGY,
            message=(
                "The infrastructure graph is not connected: "
                f"{report.component_count} components ({report.describe()})."
            ),
            context={
                "component_count": report.component_count,
                "components": [list(component) for component in report.components],
                "isolated_nodes": list(report.isolated_nodes),
            },
            suggested_action=(
                "Connect the components with track edges between registered nodes "
                "(connectivity is established by node identity, never by chainage)."
            ),
        )
    ]


def validate_edge_sequence(
    compiled: CompiledInfrastructure, edge_ids: Iterable[str]
) -> tuple[Diagnostic, ...]:
    """Check one supplied edge sequence for node continuity (Section W / AT)."""
    topology = build_topology(compiled)
    check = topology.check_undirected_sequence(edge_ids)
    if check.is_continuous:
        return ()
    return (
        Diagnostic(
            code=codes.VAL_TOPO_007,
            severity=Severity.ERROR,
            category=DiagnosticCategory.TOPOLOGY,
            message=f"The supplied edge sequence is not continuous: {check.describe()}.",
            context={
                "edges": list(edge_ids),
                "breaks": list(check.breaks),
                "missing_edges": list(check.missing_edges),
            },
            suggested_action="Supply a sequence whose consecutive edges share the connecting node.",
        ),
    )


def validate_topology(compiled: CompiledInfrastructure) -> list[Diagnostic]:
    """Run every topology check of the physical infrastructure."""
    diagnostics: list[Diagnostic] = []
    diagnostics.extend(_check_nodes(compiled))
    diagnostics.extend(_check_tracks(compiled))
    diagnostics.extend(_check_chainage_reconciliation(compiled))
    diagnostics.extend(check_required_connectivity(compiled))
    return diagnostics
