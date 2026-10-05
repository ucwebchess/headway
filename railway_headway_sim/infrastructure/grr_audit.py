"""GRR-01 Part A contradiction scan (Section BA) and frozen-count audit.

This module re-reads the frozen fixture in :mod:`grr_fixtures` and checks it
against every *declared* GRR-01 statement (object counts, regional counts,
mandatory connectivity, mandated names, platform/stopping-mark references,
static benchmark arithmetic, geometric coverage, direction/type composition) so
that a contradiction is **reported**, never silently absorbed.

The scan writes nothing and changes nothing: it only *reads* the fixture and
returns structured findings.  The Phase-2 test suite uses it
(``P2-REG-G004``), and ``docs/GRR-01 CHANGE CONTROL.md`` records its output.

Finding severities
------------------
``CONTRADICTION``
    A declared GRR-01 statement is not satisfiable by the frozen data as given
    (an approved amendment or an explicit change-control entry is required).
``RESOLVED_BY_AMENDMENT``
    A documented contradiction fixed by an approved amendment whose object
    counts are unchanged.
``OK``
    The declared statement holds exactly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from ..models.diagnostics import Diagnostic
from ..models.enums import DiagnosticCategory, Severity
from . import grr_fixtures as fx

#: Declared GRR-01 regional inventory (nodes / edges) - the audit's ground truth.
DECLARED_REGION_INVENTORY: dict[str, tuple[int, int]] = {
    "Alpha": (6, 4),
    "Central": (18, 23),
    "XC-24": (8, 8),
    "Valley": (12, 12),
    "Delta": (6, 4),
    "Open line": (0, 8),
}

#: Mandatory corridors that must be traversable (undirected reachability).
MANDATORY_CORRIDORS: tuple[tuple[str, str, str], ...] = (
    ("ALPHA-EAST", "N-ALP-W", "N-ALP-E", "Alpha terminal approach"),
    ("OPEN-ALPHA-CENTRAL", "N-ALP-W", "N-CEN-W", "Alpha - Central open line"),
    ("OPEN-CENTRAL-VALLEY", "N-CEN-E", "N-VAL-W", "Central - Valley open line"),
    ("OPEN-VALLEY-DELTA", "N-VAL-E", "N-DEL-E2", "Valley - Delta (ML2 line end)"),
    ("CENTRAL-THROUGH", "N-CEN-W", "N-CEN-E", "Central through running lines"),
    ("CENTRAL-P1", "N-CEN-P1-W", "N-CEN-P1-E", "Central P1 platform track"),
    ("CENTRAL-P2", "N-CEN-P2-W", "N-CEN-P2-E", "Central P2 platform track"),
    ("CENTRAL-P3", "N-CEN-P3-W", "N-CEN-P3-E", "Central P3 platform track"),
    ("CENTRAL-P4", "N-CEN-P4-W", "N-CEN-P4-E", "Central P4 platform track"),
    ("XC24-THROUGH", "N-XC-W", "N-XC-E", "XC-24 through running lines"),
    ("XC24-CENTRAL", "N-CEN-W", "N-XC-E", "Central - XC-24 running lines"),
    ("VALLEY-THROUGH", "N-VAL-W", "N-VAL-E", "Valley through running lines"),
    ("VALLEY-P1", "N-VAL-P1-W", "N-VAL-P1-E", "Valley P1 platform track"),
    ("VALLEY-P2", "N-VAL-P2-W", "N-VAL-P2-E", "Valley P2 platform track"),
    ("DELTA-P1", "N-DEL-W", "N-DEL-P1-E", "Delta west connection - P1 buffer stop"),
)

#: Out-of-scope result keys that must never appear in a Phase-2 reference project.
FORBIDDEN_RESULT_KEYS: tuple[str, ...] = (
    "headway",
    "headway_s",
    "headway_result",
    "blocking_time",
    "capacity",
    "occupancy",
    "occupation_time",
    "timetable",
    "arrival_time",
    "departure_time",
    "residual_occupancy",
    "speed_envelope",
    "monte_carlo",
    "uic406",
)


@dataclass(frozen=True)
class AuditFinding:
    """One Section-BA audit result."""

    check_id: str
    title: str
    severity: str
    detail: str
    evidence: dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        """Return ``True`` when the check found no unresolved contradiction."""
        return self.severity != "CONTRADICTION"

    def format_line(self) -> str:
        """Return a one-line text form for console/report output."""
        return f"[{self.severity:<22}] {self.check_id} {self.title}: {self.detail}"


def _finding(check_id: str, title: str, ok: bool, detail_ok: str, detail_bad: str,
             evidence: dict[str, Any], *, severity_when_bad: str = "CONTRADICTION") -> AuditFinding:
    return AuditFinding(
        check_id=check_id,
        title=title,
        severity="OK" if ok else severity_when_bad,
        detail=detail_ok if ok else detail_bad,
        evidence=evidence,
    )


# ---------------------------------------------------------------------------
# individual checks
# ---------------------------------------------------------------------------
def _layer() -> dict[str, Any]:
    return fx.build_grr01_layer()


def _check_counts(layer: dict[str, Any]) -> AuditFinding:
    counts = {key: len(layer[key]) for key in fx.GRR01_EXPECTED_COUNTS if key != "vertical_profile_points"}
    counts["vertical_profile_points"] = sum(len(p["points"]) for p in layer["vertical_profiles"])
    mismatches = {
        key: (counts[key], fx.GRR01_EXPECTED_COUNTS[key])
        for key in fx.GRR01_EXPECTED_COUNTS
        if counts[key] != fx.GRR01_EXPECTED_COUNTS[key]
    }
    return _finding(
        "BA-01",
        "Frozen object counts",
        not mismatches,
        "All 11 declared GRR-01 object counts match exactly.",
        f"Declared counts do not match: {mismatches}.",
        {"observed": counts, "declared": dict(fx.GRR01_EXPECTED_COUNTS)},
    )


def _check_regional_inventory(layer: dict[str, Any]) -> AuditFinding:
    node_ids = {node["id"] for node in layer["nodes"]}
    track_ids = {track["id"] for track in layer["tracks"]}
    declared_nodes = {key: len(ids) for key, ids in fx.REGION_NODE_IDS.items()}
    declared_tracks = {key: len(ids) for key, ids in fx.REGION_TRACK_IDS.items()}

    problems: list[str] = []
    if set(ids for values in fx.REGION_NODE_IDS.values() for ids in values) != node_ids:
        problems.append("region node lists are not an exact partition of the node catalogue")
    if set(ids for values in fx.REGION_TRACK_IDS.values() for ids in values) != track_ids:
        problems.append("region edge lists are not an exact partition of the track catalogue")
    for region, (nodes, edges) in DECLARED_REGION_INVENTORY.items():
        if declared_nodes.get(region, 0) != nodes:
            problems.append(f"{region} nodes {declared_nodes.get(region, 0)} != declared {nodes}")
        if declared_tracks.get(region, 0) != edges:
            problems.append(f"{region} edges {declared_tracks.get(region, 0)} != declared {edges}")

    return _finding(
        "BA-02",
        "Regional inventory (nodes / edges, sum = 50 / 59)",
        not problems,
        "Every region matches its declared node/edge count and the regions partition the catalogues exactly.",
        "; ".join(problems),
        {"declared": DECLARED_REGION_INVENTORY, "observed_nodes": declared_nodes,
         "observed_edges": declared_tracks},
    )


def _check_incidence(layer: dict[str, Any]) -> AuditFinding:
    node_ids = [node["id"] for node in layer["nodes"]]
    incident: dict[str, int] = {node_id: 0 for node_id in node_ids}
    dangling: list[str] = []
    for track in layer["tracks"]:
        for endpoint in (track["from_node"], track["to_node"]):
            if endpoint not in incident:
                dangling.append(f"{track['id']} -> {endpoint}")
            else:
                incident[endpoint] += 1

    isolated = sorted(node_id for node_id, degree in incident.items() if degree == 0)
    return _finding(
        "BA-03",
        "Node incidence (no invented or dangling nodes)",
        not isolated and not dangling,
        "Every one of the 50 declared nodes is incident to at least one track and every track endpoint resolves.",
        f"isolated nodes: {isolated}; unresolved endpoints: {dangling}",
        {"min_degree": min(incident.values()) if incident else 0,
         "buffer_or_line_end_nodes": sorted(k for k, v in incident.items() if v == 1)},
    )


def _check_connectivity(layer: dict[str, Any]) -> AuditFinding:
    adjacency: dict[str, set[str]] = {}
    for track in layer["tracks"]:
        adjacency.setdefault(track["from_node"], set()).add(track["to_node"])
        adjacency.setdefault(track["to_node"], set()).add(track["from_node"])

    start = sorted(adjacency)[0]
    seen = {start}
    stack = [start]
    while stack:
        node = stack.pop()
        for neighbour in adjacency.get(node, ()):  # deterministic, no graph library
            if neighbour not in seen:
                seen.add(neighbour)
                stack.append(neighbour)

    def reachable(source: str, target: str) -> bool:
        visited = {source}
        queue = [source]
        while queue:
            node = queue.pop(0)
            if node == target:
                return True
            for neighbour in sorted(adjacency.get(node, ())):
                if neighbour not in visited:
                    visited.add(neighbour)
                    queue.append(neighbour)
        return False

    unreachable = [name for name, a, b, _ in MANDATORY_CORRIDORS if not reachable(a, b)]
    all_nodes = set(adjacency)
    # Buffer stops and line ends are legitimately degree 1, but nothing may be
    # disconnected: with 50 nodes and 59 edges the graph must still be connected.
    return _finding(
        "BA-04",
        "Physical connectivity (all 50 nodes in one component)",
        len(seen) == len(all_nodes) and not unreachable,
        "The whole GRR-01 network is one connected component and all 15 mandatory corridors are traversable.",
        (f"{len(seen)}/{len(all_nodes)} nodes reachable from {start}; "
         f"untraversable corridors: {unreachable}"),
        {"component_size": len(seen), "node_count": len(all_nodes),
         "corridors_checked": len(MANDATORY_CORRIDORS)},
    )


def _check_mandated_names(layer: dict[str, Any]) -> AuditFinding:
    track_ids = {track["id"] for track in layer["tracks"]}
    node_ids = {node["id"] for node in layer["nodes"]}
    missing_edges = [name for name in fx.CENTRAL_EAST_CROSS_EDGE_NAMES if name not in track_ids]
    present_provisional = [name for name in fx.FORBIDDEN_PROVISIONAL_EDGE_NAMES if name in track_ids]
    required_nodes = {"STA-ALPHA", "STA-CEN", "STA-VAL", "STA-DELTA"}
    missing_stations = sorted(required_nodes - {station["id"] for station in layer["stations"]})
    groups = {group["id"]: group for group in layer["track_groups"]}
    wrong_groups = sorted(
        group_id
        for group_id, expected_normal, expected_directionality in (
            ("TG-ML1", "FORWARD", "BOTH"),
            ("TG-ML2", "REVERSE", "BOTH"),
        )
        if group_id not in groups
        or groups[group_id].get("normal_direction") != expected_normal
        or groups[group_id].get("directionality") != expected_directionality
    )
    return _finding(
        "BA-05",
        "Mandated edge/node names (Section AD), station identifiers and track-group directions",
        not missing_edges and not present_provisional and not missing_stations and not wrong_groups,
        "Final Central east crossing names are used, no provisional name survives, all four station IDs "
        "match and both track groups declare their frozen normal direction (TG-ML1 FORWARD, TG-ML2 REVERSE).",
        f"missing edges: {missing_edges}; provisional names present: {present_provisional}; "
        f"missing stations: {missing_stations}; groups with a wrong normal direction or directionality: "
        f"{wrong_groups}",
        {"track_count": len(track_ids), "node_count": len(node_ids), "track_groups": len(groups)},
    )


def _check_references(layer: dict[str, Any]) -> AuditFinding:
    problems: list[str] = []
    track_by_id = {track["id"]: track for track in layer["tracks"]}
    platforms = layer["platforms"]
    marks = layer["stopping_marks"]

    for station in layer["stations"]:
        for platform_id in station["platform_ids"]:
            if platform_id not in {platform["id"] for platform in platforms}:
                problems.append(f"{station['id']} -> unknown platform {platform_id}")
    for platform in platforms:
        track = track_by_id.get(platform["track_id"])
        if track is None:
            problems.append(f"{platform['id']} -> unknown track {platform['track_id']}")
            continue
        if not 0.0 <= platform["usable_start_m"] < platform["usable_end_m"] <= track["length_m"]:
            problems.append(f"{platform['id']} usable range outside track length {track['length_m']}")
    for mark in marks:
        track = track_by_id.get(mark["track_id"])
        if track is None:
            problems.append(f"{mark['id']} -> unknown track {mark['track_id']}")
            continue
        if not 0.0 <= mark["position_m"] <= track["length_m"]:
            problems.append(f"{mark['id']} position {mark['position_m']} outside track {track['length_m']}")
        platform = next((p for p in platforms if p["id"] == mark["platform_id"]), None)
        if platform is None:
            problems.append(f"{mark['id']} -> unknown platform {mark['platform_id']}")
        else:
            if platform["track_id"] != mark["track_id"]:
                problems.append(f"{mark['id']} track differs from its platform track")
            if not platform["usable_start_m"] <= mark["position_m"] <= platform["usable_end_m"]:
                problems.append(f"{mark['id']} position outside usable platform range")
    mark_ids = {mark["id"] for mark in marks}
    for platform in platforms:
        for mark_id in platform["stopping_mark_ids"]:
            if mark_id not in mark_ids:
                problems.append(f"{platform['id']} -> unknown stopping mark {mark_id}")
    return _finding(
        "BA-06",
        "Station / platform / stopping-mark reference integrity",
        not problems,
        "All station, platform, track and stopping-mark references resolve and every range is inside its track.",
        "; ".join(problems),
        {"stations": len(layer["stations"]), "platforms": len(platforms),
         "stopping_marks": len(marks),
         "amended_mark": {mark["id"]: mark["position_m"] for mark in marks if mark["id"] == fx.STOP_V_P1_R_ID}},
    )


def _check_geometry(layer: dict[str, Any]) -> AuditFinding:
    problems: list[str] = []
    sections = layer["horizontal_geometry"]
    alignment_start, alignment_end = fx.ALIGNMENT_START_KM, fx.ALIGNMENT_END_KM
    if sections[0]["start_chainage_km"] != alignment_start or sections[-1]["end_chainage_km"] != alignment_end:
        problems.append("horizontal geometry does not span the full alignment")
    for first, second in zip(sections, sections[1:]):
        if first["end_chainage_km"] != second["start_chainage_km"]:
            problems.append(f"coverage gap/overlap between {first['id']} and {second['id']}")
    for section in sections:
        if not alignment_start <= section["start_chainage_km"] < section["end_chainage_km"] <= alignment_end:
            problems.append(f"{section['id']} outside the alignment")
        if section["type"] == "CURVE" and not (section.get("radius_m") and section.get("handedness")):
            problems.append(f"{section['id']} is a curve without radius/handedness")

    profiles = layer["vertical_profiles"]
    for profile in profiles:
        chainages = [point["chainage_km"] for point in profile["points"]]
        if len(chainages) < 2 or chainages != sorted(set(chainages)):
            problems.append(f"{profile['id']} chainages are not strictly increasing/unique")
        for point in profile["points"]:
            if not alignment_start <= point["chainage_km"] <= alignment_end:
                problems.append(f"{point['id']} outside the alignment")
            if point["elevation_m"] is None:
                problems.append(f"{point['id']} without elevation")
    return _finding(
        "BA-07",
        "Geometry coverage (continuous 0-50 km, vertical profile strictly increasing)",
        not problems,
        "Horizontal geometry covers 0.000-50.000 km without gaps or overlaps; the vertical profile is strictly increasing and inside the alignment.",
        "; ".join(problems),
        {"sections": len(sections), "profile_points": sum(len(p["points"]) for p in profiles)},
    )


def _check_speed_restrictions(layer: dict[str, Any]) -> AuditFinding:
    restrictions = layer["speed_restrictions"]
    both_permanent = [
        r for r in restrictions
        if r["direction"] == "BOTH" and r["type"].startswith("PERMANENT")
    ]
    reverse = [r for r in restrictions if r["direction"] == "REVERSE"]
    problems: list[str] = []
    if len(restrictions) != 8:
        problems.append(f"{len(restrictions)} restrictions instead of 8")
    if len(both_permanent) != 7:
        problems.append(f"{len(both_permanent)} BOTH/permanent restrictions instead of 7")
    if len(reverse) != 1 or not (
        reverse and reverse[0]["start_chainage_km"] == 42.0
        and reverse[0]["end_chainage_km"] == 44.0
        and reverse[0]["speed_kmh"] == 240
    ):
        problems.append("the single REVERSE restriction is not 42-44 km at 240 km/h")
    for restriction in restrictions:
        if not 0.0 <= restriction["start_chainage_km"] < restriction["end_chainage_km"] <= 50.0:
            problems.append(f"{restriction['id']} is outside the alignment")
        if not restriction["speed_kmh"] > 0:
            problems.append(f"{restriction['id']} has a non-positive speed")
    return _finding(
        "BA-08",
        "Speed-restriction composition (7 permanent BOTH + 1 reverse 42-44 km @ 240 km/h)",
        not problems,
        "Speed restrictions match the declared composition exactly.",
        "; ".join(problems),
        {"count": len(restrictions), "both_permanent": len(both_permanent),
         "reverse": [(r["id"], r["start_chainage_km"], r["end_chainage_km"], r["speed_kmh"]) for r in reverse]},
    )


def _check_new_nodes(layer: dict[str, Any]) -> AuditFinding:
    """Formerly-uncounted track endpoints are declared explicitly (GRR-AMD-003)."""
    declared_nodes = set(fx.GRR01_EXPECTED_COUNTS)  # catalogue presence only
    del declared_nodes  # the check below is about node ids, not catalogues
    node_ids = {node["id"] for node in layer["nodes"]}
    endpoints = {endpoint for track in layer["tracks"] for endpoint in (track["from_node"], track["to_node"])}
    required = {"N-VAL-XA", "N-VAL-T2-A", "N-XC-ML1-A", "N-XC-E", "N-CEN-X-C", "N-CEN-X-D", "N-DEL-E2"}
    missing = sorted(required - node_ids)
    unexplained = sorted(endpoints - node_ids)
    extra = sorted(node_ids - endpoints)
    return _finding(
        "BA-09",
        "Every track endpoint is a declared, counted node (no invented nodes on load)",
        not missing and not unexplained and not extra,
        "The 59 edges reference exactly the 50 declared nodes; the endpoints that the frozen regional tables count implicitly are declared explicitly.",
        f"missing mandatory nodes: {missing}; endpoints without a declared node: {unexplained}; "
        f"declared nodes without an edge: {extra}",
        {"declared_nodes": len(node_ids), "referenced_endpoints": len(endpoints),
         "explicitly_declared_endpoints": sorted(required)},
    )


def _check_chainage_maps(layer: dict[str, Any]) -> AuditFinding:
    """GRR-01 stores every track with increasing physical chainage (frozen invariant)."""
    problems: list[str] = []
    for track in layer["tracks"]:
        chainage_map = track["chainage_map"]
        if chainage_map["mode"] != "LINEAR":
            problems.append(f"{track['id']} uses mode {chainage_map['mode']} instead of LINEAR")
        if not (
            0.0
            <= chainage_map["start_km"]
            < chainage_map["end_km"]
            <= fx.ALIGNMENT_END_KM
        ):
            problems.append(
                f"{track['id']} map {chainage_map['start_km']}-{chainage_map['end_km']} km is "
                "not increasing inside the alignment"
            )
    return _finding(
        "BA-13",
        "Every track chainage map is LINEAR and increases inside the alignment",
        not problems,
        "All 59 track chainage maps are LINEAR, strictly increasing and inside 0.000-50.000 km.",
        "; ".join(problems),
        {"tracks": len(layer["tracks"])},
    )


def _check_flat_registry(layer: dict[str, Any]) -> AuditFinding:
    """Registered IDs must be globally unique across every typed catalogue."""
    catalogues: list[tuple[str, list[dict[str, Any]]]] = [
        (key, layer[key])
        for key in fx.GRR01_EXPECTED_COUNTS
        if key != "vertical_profile_points"
    ]
    catalogues.append(("vertical_profiles", layer["vertical_profiles"]))
    for profile in layer["vertical_profiles"]:
        catalogues.append(("vertical_profile_points", profile["points"]))

    seen: dict[str, str] = {}
    duplicates: list[str] = []
    for key, records in catalogues:
        for record in records:
            object_id = record["id"]
            if object_id in seen:
                duplicates.append(f"{object_id} ({seen[object_id]} vs {key})")
            seen[object_id] = key
    return _finding(
        "BA-10",
        "Global registry uniqueness across all typed catalogues",
        not duplicates,
        f"All {len(seen)} registered engineering object IDs are globally unique "
        "across 12 typed catalogues (profiles and their points included).",
        f"duplicate registered IDs: {duplicates}",
        {"registered_objects": len(seen), "catalogues": len(catalogues)},
    )


def _check_benchmarks(layer: dict[str, Any]) -> AuditFinding:
    """Recompute the frozen static benchmarks with the static footprint utility."""
    from ..models.enums import EdgeTraversal
    from ..models.infrastructure import Platform, Track
    from .static_geometry import evaluate_static_footprint

    track_by_id = {track["id"]: track for track in layer["tracks"]}
    platform_by_id = {platform["id"]: platform for platform in layer["platforms"]}
    problems: list[str] = []
    for benchmark in fx.GRR01_STATIC_BENCHMARKS:
        platform = Platform.model_validate(platform_by_id[benchmark["platform_id"]])
        traversal = EdgeTraversal(benchmark["traversal"])
        result = evaluate_static_footprint(
            Track.model_validate(track_by_id[benchmark["track_id"]]),
            front_position_m=benchmark["front_position_m"],
            train_length_m=benchmark["train_length_m"],
            traversal=traversal,
            marker_id=benchmark["id"],
            platform=platform,
        )
        if result.rear_position_m != benchmark["expected_rear_position_m"]:
            problems.append(
                f"{benchmark['id']} rear {result.rear_position_m} != "
                f"{benchmark['expected_rear_position_m']}"
            )
        key = (
            "expected_rear_infringement_m"
            if "expected_rear_infringement_m" in benchmark
            else "expected_rear_clearance_m"
        )
        observed = (
            result.rear_infringement_m if key.endswith("infringement_m") else result.rear_clearance_m
        )
        if abs(observed - benchmark[key]) > 1e-9:
            problems.append(f"{benchmark['id']} {key} {observed} != {benchmark[key]}")
    return _finding(
        "BA-11",
        "Frozen static benchmarks (5) reproduced by the static footprint utility",
        not problems,
        "All five frozen static benchmarks reproduce exactly (12 m / 13 m / 12 m / 78 m / 98 m).",
        "; ".join(problems),
        {"benchmarks": [b["id"] for b in fx.GRR01_STATIC_BENCHMARKS]},
    )


def _check_out_of_scope(document: dict[str, Any]) -> AuditFinding:
    """No train-dynamics/simulation/headway content may exist in the document."""
    found: list[str] = []

    def walk(value: Any, path: str) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                if str(key).lower() in FORBIDDEN_RESULT_KEYS:
                    found.append(f"{path}.{key}")
                walk(item, f"{path}.{key}")
        elif isinstance(value, list):
            for index, item in enumerate(value):
                walk(item, f"{path}[{index}]")

    walk(document, "$")
    return _finding(
        "BA-12",
        "Section D out-of-scope guard (no simulated results in the reference project)",
        not found,
        "The reference project contains static physical data only: no headway, blocking, occupation, timetable or capacity result.",
        f"out-of-scope result keys present: {sorted(set(found))}",
        {"forbidden_keys_checked": len(FORBIDDEN_RESULT_KEYS)},
    )


CHECKS: tuple[Callable[..., AuditFinding], ...] = (
    _check_counts,
    _check_regional_inventory,
    _check_incidence,
    _check_connectivity,
    _check_mandated_names,
    _check_references,
    _check_geometry,
    _check_speed_restrictions,
    _check_new_nodes,
    _check_flat_registry,
    _check_benchmarks,
    _check_out_of_scope,
    _check_chainage_maps,
)

#: Checks whose data-driven correction is recorded as an approved amendment.
AMENDED_CHECKS: dict[str, str] = {
    "BA-04": "GRR-AMD-003 (Delta 6 nodes / 4 edges cannot be connected internally)",
    "BA-06": "GRR-AMD-001 (STOP-V-P1-R 220.0 -> 250.0 m); GRR-AMD-004 (PLT-VAL-P2 usable range)",
    "BA-09": "GRR-AMD-003 (explicit declaration of formerly uncounted endpoints)",
}


# ---------------------------------------------------------------------------
# GRR-01 inventory diagnostics (VAL-GRR-001 ... VAL-GRR-004)
# ---------------------------------------------------------------------------
def inventory_diagnostics(document: dict[str, Any]) -> list[Diagnostic]:
    """Return the GRR-01 inventory diagnostics of a *document* (frozen contract).

    These checks belong to the GRR-01 reference project contract, not to the
    generic project validator: they are run by the reference-project build and by
    the Phase-2 regression tests (``P2-REG-G001``/``G002``), so that a change to
    the frozen inventory is always reported (``VAL-GRR-001``/``002``), an approved
    amendment that is not recorded is caught (``VAL-GRR-003``), and a wrong layer
    structure is caught (``VAL-GRR-004``).
    """
    diagnostics: list[Diagnostic] = []
    infrastructure = document.get("infrastructure")
    layers = infrastructure if isinstance(infrastructure, list) else []
    layer = layers[0] if layers and isinstance(layers[0], dict) else {}

    # VAL-GRR-004 - layer structure
    if len(layers) != 1 or not isinstance(layer, dict):
        diagnostics.append(
            _grr_diagnostic(
                "VAL-GRR-004",
                f"GRR-01 must contain exactly one infrastructure layer, found {len(layers)}.",
                {"layers": len(layers)},
                "Restore the single layer LYR-MAIN.",
            )
        )
    else:
        if layer.get("id") != fx.LAYER_ID:
            diagnostics.append(
                _grr_diagnostic(
                    "VAL-GRR-004",
                    f"GRR-01 layer id is {layer.get('id')!r}, expected {fx.LAYER_ID!r}.",
                    {"layer_id": layer.get("id")},
                    f"Restore layer id {fx.LAYER_ID}.",
                )
            )
        if layer.get("physical_mode") != "PHYSICAL":
            diagnostics.append(
                _grr_diagnostic(
                    "VAL-GRR-004",
                    "GRR-01 layer does not declare physical_mode 'PHYSICAL'.",
                    {"physical_mode": layer.get("physical_mode")},
                    "Declare physical_mode PHYSICAL on the GRR-01 layer.",
                )
            )

    # VAL-GRR-001 - frozen object counts
    observed = {
        key: len(layer.get(key) or []) for key in fx.GRR01_EXPECTED_COUNTS
    }
    observed["vertical_profile_points"] = sum(
        len(profile.get("points") or []) for profile in (layer.get("vertical_profiles") or [])
    )
    for key, expected in fx.GRR01_EXPECTED_COUNTS.items():
        if observed[key] != expected:
            diagnostics.append(
                _grr_diagnostic(
                    "VAL-GRR-001",
                    f"GRR-01 {key} count is {observed[key]}, expected {expected}.",
                    {"catalogue": key, "observed": observed[key], "expected": expected},
                    "Record an approved amendment in the GRR-01 change control before changing counts.",
                )
            )

    # VAL-GRR-002 - regional inventory
    node_ids = {node.get("id") for node in (layer.get("nodes") or []) if isinstance(node, dict)}
    track_ids = {track.get("id") for track in (layer.get("tracks") or []) if isinstance(track, dict)}
    declared_node_ids = {item for ids in fx.REGION_NODE_IDS.values() for item in ids}
    declared_track_ids = {item for ids in fx.REGION_TRACK_IDS.values() for item in ids}
    if declared_node_ids != node_ids:
        diagnostics.append(
            _grr_diagnostic(
                "VAL-GRR-002",
                "GRR-01 regional node lists do not partition the node catalogue.",
                {
                    "missing": sorted(declared_node_ids - node_ids),
                    "undeclared": sorted(node_ids - declared_node_ids),
                },
                "Every node must belong to exactly one declared region.",
            )
        )
    if declared_track_ids != track_ids:
        diagnostics.append(
            _grr_diagnostic(
                "VAL-GRR-002",
                "GRR-01 regional edge lists do not partition the track catalogue.",
                {
                    "missing": sorted(declared_track_ids - track_ids),
                    "undeclared": sorted(track_ids - declared_track_ids),
                },
                "Every track must belong to exactly one declared region.",
            )
        )

    # VAL-GRR-003 - approved amendments recorded
    provenance = document.get("provenance") if isinstance(document.get("provenance"), dict) else {}
    amendments = provenance.get("approved_amendments") or []
    recorded_ids = {
        amendment.get("id") for amendment in amendments if isinstance(amendment, dict)
    }
    marks = {
        mark.get("id"): mark for mark in (layer.get("stopping_marks") or []) if isinstance(mark, dict)
    }
    mark = marks.get(fx.STOP_V_P1_R_ID)
    if mark is not None and float(mark.get("position_m", 0.0)) != fx.FROZEN_STOP_V_P1_R_POSITION_M:
        if "GRR-AMD-001" not in recorded_ids:
            diagnostics.append(
                _grr_diagnostic(
                    "VAL-GRR-003",
                    (
                        f"{fx.STOP_V_P1_R_ID} is at {mark.get('position_m')} m but the approved "
                        "amendment GRR-AMD-001 is not recorded in provenance.approved_amendments."
                    ),
                    {
                        "object_id": fx.STOP_V_P1_R_ID,
                        "observed_position_m": mark.get("position_m"),
                        "recorded_amendments": sorted(item for item in recorded_ids if item),
                    },
                    "Record the amendment in the GRR-01 change control and in provenance.",
                )
            )
    return diagnostics


def _grr_diagnostic(code: str, message: str, context: dict[str, Any],
                    suggested_action: str) -> Diagnostic:
    """Build one GRR-01 inventory diagnostic."""
    return Diagnostic(
        code=code,
        severity=Severity.ERROR,
        category=DiagnosticCategory.GRR,
        message=message,
        context=context,
        suggested_action=suggested_action,
    )


def scan_contradictions() -> list[AuditFinding]:
    """Run every Section-BA check against the frozen fixture (read-only)."""
    layer = _layer()
    document = fx.build_grr01_document()
    findings: list[AuditFinding] = []
    for check in CHECKS:
        subject = document if check is _check_out_of_scope else layer
        findings.append(check(subject))
    return findings


def scan_summary() -> dict[str, Any]:
    """Return a compact, machine-readable summary of the contradiction scan."""
    findings = scan_contradictions()
    return {
        "checks": len(findings),
        "contradictions": [f.check_id for f in findings if f.severity == "CONTRADICTION"],
        "findings": [
            {
                "check_id": f.check_id,
                "title": f.title,
                "severity": f.severity,
                "detail": f.detail,
                "evidence": f.evidence,
            }
            for f in findings
        ],
    }


def format_findings(findings: Optional[list[AuditFinding]] = None) -> str:
    """Return the scan result as printable text (used by tests and the CLI)."""
    lines = ["GRR-01 Part A contradiction scan (Section BA)", "=" * 60]
    for finding in findings if findings is not None else scan_contradictions():
        lines.append(finding.format_line())
        if finding.severity != "OK" and finding.check_id in AMENDED_CHECKS:
            lines.append(f"    -> resolved by {AMENDED_CHECKS[finding.check_id]}")
    return "\n".join(lines)
