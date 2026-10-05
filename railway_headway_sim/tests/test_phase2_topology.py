"""Phase-2 tests: speed restrictions, nodes, tracks, chainage maps, topology, registry.

Acceptance tests covered here: TEST P2-008 ... TEST P2-016.
"""

from __future__ import annotations

from railway_headway_sim.models.enums import Severity

from .phase2_support import (
    catalogue,
    compile_document,
    diagnostics_with_code,
    entry,
    grr_document,
    has_code,
    layer_of,
    validate,
)


# ---------------------------------------------------------------------------
# TEST P2-008
# ---------------------------------------------------------------------------
def test_p2_008_speed_restriction_rules():
    """TEST P2-008 - speed > 0, range inside the alignment, valid direction and type."""
    document = grr_document()
    restrictions = catalogue(document, "speed_restrictions")
    assert len(restrictions) == 8
    for restriction in restrictions:
        assert restriction["speed_kmh"] > 0
        assert restriction["direction"] in {"FORWARD", "REVERSE", "BOTH"}
        assert restriction["type"] in {"PERMANENT", "PERMANENT_DIRECTIONAL", "TEMPORARY"}

    document = grr_document()
    entry(document, "speed_restrictions", "SPR-01")["speed_kmh"] = 0
    assert has_code(validate(document).result, "VAL-GEOM-007")

    document = grr_document()
    entry(document, "speed_restrictions", "SPR-01")["end_chainage_km"] = 60.0
    assert has_code(validate(document).result, "VAL-GEOM-007")

    document = grr_document()
    entry(document, "speed_restrictions", "SPR-01")["direction"] = "SIDEWAYS"
    outcome = validate(document)
    assert has_code(outcome.result, "VAL-INFR-002") or has_code(outcome.result, "VAL-ENUM-001")
    assert outcome.result.has_errors()


# ---------------------------------------------------------------------------
# TEST P2-009
# ---------------------------------------------------------------------------
def test_p2_009_node_rules():
    """TEST P2-009 - node chainage inside the alignment; optional station_id must resolve."""
    document = grr_document()
    nodes = catalogue(document, "nodes")
    assert len(nodes) == 50
    assert {node["type"] for node in nodes} <= {
        "BUFFER_STOP", "SWITCH", "CONNECTION", "TRACK_CONNECTION", "STATION_BOUNDARY",
    }

    document = grr_document()
    entry(document, "nodes", "N-ALP-W")["chainage_km"] = 60.0
    out_of_range = diagnostics_with_code(validate(document).result, "VAL-TOPO-004")
    assert out_of_range and "N-ALP-W" in out_of_range[0].message

    document = grr_document()
    entry(document, "nodes", "N-ALP-W")["chainage_km"] = -1.0
    assert has_code(validate(document).result, "VAL-TOPO-004")

    document = grr_document()
    entry(document, "nodes", "N-ALP-U1")["station_id"] = "STA-UNKNOWN"
    unknown_station = diagnostics_with_code(validate(document).result, "VAL-TOPO-006")
    assert unknown_station and "STA-UNKNOWN" in unknown_station[0].message

    document = grr_document()
    entry(document, "nodes", "N-ALP-W")["type"] = "MAGIC_NODE"
    assert validate(document).result.has_errors()


# ---------------------------------------------------------------------------
# TEST P2-010
# ---------------------------------------------------------------------------
def test_p2_010_track_rules():
    """TEST P2-010 - endpoints exist and differ, length_m > 0, group resolves, map in-range."""
    document = grr_document()
    tracks = catalogue(document, "tracks")
    assert len(tracks) == 59
    node_ids = {node["id"] for node in catalogue(document, "nodes")}
    for track in tracks:
        assert track["from_node"] in node_ids and track["to_node"] in node_ids
        assert track["from_node"] != track["to_node"]
        assert track["length_m"] > 0
        assert track["chainage_map"]["mode"] == "LINEAR"
        assert 0.0 <= track["chainage_map"]["start_km"] < track["chainage_map"]["end_km"] <= 50.0

    document = grr_document()
    entry(document, "tracks", "TR-C-P2")["from_node"] = "N-NOT-THERE"
    outcome = validate(document)
    assert has_code(outcome.result, "VAL-TOPO-001")

    document = grr_document()
    entry(document, "tracks", "TR-C-P2")["to_node"] = entry(document, "tracks", "TR-C-P2")["from_node"]
    assert has_code(validate(document).result, "VAL-TOPO-002")

    document = grr_document()
    entry(document, "tracks", "TR-C-P2")["length_m"] = 0.0
    assert has_code(validate(document).result, "VAL-TOPO-003")

    document = grr_document()
    entry(document, "tracks", "TR-C-P2")["track_group_id"] = "TG-UNKNOWN"
    assert has_code(validate(document).result, "VAL-TOPO-005")

    # a zero-length (degenerate) map is not invertible and is rejected
    document = grr_document()
    entry(document, "tracks", "TR-C-P2")["chainage_map"] = {
        "mode": "LINEAR", "start_km": 20.0, "end_km": 20.0,
    }
    assert has_code(validate(document).result, "VAL-TOPO-004")

    # a *decreasing* map is legal (a track laid out in decreasing chainage); GRR-01
    # itself never uses one - see the frozen Part-A invariant checked by BA-13.
    document = grr_document()
    entry(document, "tracks", "TR-C-P2")["chainage_map"] = {
        "mode": "LINEAR", "start_km": 30.0, "end_km": 20.0,
    }
    assert not has_code(validate(document).result, "VAL-TOPO-004")

    document = grr_document()
    entry(document, "tracks", "TR-C-P2")["chainage_map"] = {
        "mode": "LINEAR", "start_km": 45.0, "end_km": 55.0,
    }
    assert has_code(validate(document).result, "VAL-TOPO-004")


# ---------------------------------------------------------------------------
# TEST P2-011
# ---------------------------------------------------------------------------
def test_p2_011_parallel_chainage_and_projection_mismatch_are_legal():
    """TEST P2-011 - parallel/overlapping chainage is not a conflict; length != projection is legal."""
    document = grr_document()
    tracks = {track["id"]: track for track in catalogue(document, "tracks")}

    ml1 = tracks["TR-X-ML1-STRAIGHT"]
    ml2 = tracks["TR-X-ML2-STRAIGHT"]
    assert ml1["chainage_map"]["start_km"] <= ml2["chainage_map"]["start_km"]
    assert ml1["chainage_map"]["end_km"] >= ml2["chainage_map"]["start_km"]  # overlapping range

    # a physical length that differs from the chainage projection is legal: the
    # projection measures the alignment, the track has its own physical length.
    document = grr_document()
    speed_line = entry(document, "tracks", "TR-O-ALP-CEN-ML1")
    projection_m = (speed_line["chainage_map"]["end_km"] - speed_line["chainage_map"]["start_km"]) * 1000
    speed_line["length_m"] = projection_m + 140.0  # e.g. curvature/vertical alignment
    stretched = validate(document).result
    assert stretched.error_count == 0
    assert not has_code(stretched, "VAL-TOPO-003")
    assert not has_code(stretched, "VAL-TOPO-004")

    document = grr_document()
    result = validate(document).result
    assert result.error_count == 0
    assert not has_code(result, "VAL-TOPO-004")
    assert not has_code(result, "VAL-TOPO-007")

    # a deliberately parallel duplicate (same nodes, same chainage) stays legal
    document = grr_document()
    duplicate = dict(entry(document, "tracks", "TR-C-P2"))
    duplicate["id"] = "TR-C-P2-PARALLEL"
    layer_of(document)["tracks"].append(duplicate)
    parallel_result = validate(document).result
    assert not has_code(parallel_result, "VAL-TOPO-004")
    assert not has_code(parallel_result, "VAL-REGISTRY-001")


# ---------------------------------------------------------------------------
# TEST P2-012
# ---------------------------------------------------------------------------
def test_p2_012_legacy_chainages_reconciled_with_chainage_map():
    """TEST P2-012 - legacy chainages[] must match Track.chainage_map within 1e-9 km."""
    document = grr_document()
    layer_of(document)["chainages"] = [
        {"id": "CHG-TR-C-P2-START", "track_id": "TR-C-P2", "chainage_km": 15.5},
        {"id": "CHG-TR-C-P2-END", "track_id": "TR-C-P2", "chainage_km": 27.0},
    ]
    result = validate(document).result
    assert not has_code(result, "VAL-TOPO-008")

    # 1e-9 km (1 micrometre) is the tolerance: a larger deviation is an ERROR
    document = grr_document()
    layer_of(document)["chainages"] = [
        {"id": "CHG-TR-C-P2-END", "track_id": "TR-C-P2", "chainage_km": 27.0 + 1e-6},
    ]
    inconsistent = diagnostics_with_code(validate(document).result, "VAL-TOPO-008")
    assert inconsistent, "an inconsistent legacy chainage must be reported"

    # VAL-REF-001 stays scoped to reference_system.chainage_start/end only
    document = grr_document()
    document["reference_system"]["chainage_end_km"] = -1.0
    assert has_code(validate(document).result, "VAL-REF-001")

    document = grr_document()
    layer_of(document)["chainages"] = [
        {"id": "CHG-A", "track_id": "TR-C-P2", "chainage_km": 100.0},
    ]
    result = validate(document).result
    assert not has_code(result, "VAL-REF-001")
    assert has_code(result, "VAL-TOPO-008")


# ---------------------------------------------------------------------------
# TEST P2-013
# ---------------------------------------------------------------------------
def test_p2_013_topology_adjacency_and_connectivity():
    """TEST P2-013 - adjacency/connectivity use node identity only (never chainage equality)."""
    compiled = compile_document()
    topology = compiled.topology()

    assert len(topology.nodes) == 50
    assert len(topology.tracks) == 59
    assert topology.is_connected()
    report = topology.connectivity()
    assert report.component_count == 1
    assert len(report.largest_component) == 50
    assert report.isolated_nodes == ()

    # the two Alpha buffer stops and both line ends are degree 1, nothing is isolated
    degrees = {node_id: topology.edges_from_node(node_id).degree for node_id in topology.node_ids()}
    assert degrees["N-ALP-SDG"] == 1
    assert degrees["N-DEL-E2"] == 1
    assert min(degrees.values()) == 1

    # duplicate chainages at different nodes do not create connectivity
    document = grr_document()
    entry(document, "nodes", "N-VAL-T1-A")["chainage_km"] = 43.8  # same chainage as N-VAL-XB
    compiled = compile_document(document)
    report = compiled.topology().connectivity()
    assert report.component_count == 1, "chainage equality must not merge or split nodes"

    # ... and a broken node reference is reported as a topology error, not silently repaired
    document = grr_document()
    entry(document, "tracks", "TR-V-XB-E")["to_node"] = "N-NOWHERE"
    assert has_code(validate(document).result, "VAL-TOPO-001")


# ---------------------------------------------------------------------------
# TEST P2-014
# ---------------------------------------------------------------------------
def test_p2_014_edge_sequence_continuity_check():
    """TEST P2-014 - edge sequences are checked for continuity by node identity."""
    topology = compile_document().topology()

    continuous = topology.check_edge_sequence(["TR-C-E-X-U1", "TR-O-CEN-VAL-ML1"])
    assert continuous.is_continuous

    broken = topology.check_edge_sequence(["TR-C-P1", "TR-O-CEN-VAL-ML1"])
    assert not broken.is_continuous
    assert broken.breaks

    unknown = topology.check_edge_sequence(["TR-DOES-NOT-EXIST"])
    assert not unknown.is_continuous
    assert unknown.missing_edges

    # undirected checking accepts a sequence walked against the stored orientation
    reversed_sequence = topology.check_undirected_sequence(["TR-A-W-U1", "TR-A-U1-U2"])
    assert reversed_sequence.is_continuous


# ---------------------------------------------------------------------------
# TEST P2-015
# ---------------------------------------------------------------------------
def test_p2_015_opaque_records_in_a_physical_project():
    """TEST P2-015 - an opaque record with an 'id' is an ERROR (VAL-PHASE-002) plus a WARNING."""
    document = grr_document()
    layer_of(document)["tunnels"] = [{"id": "TUN-01", "name": "legacy tunnel"}]
    outcome = validate(document)
    assert has_code(outcome.result, "VAL-PHASE-002")
    assert has_code(outcome.result, "VAL-INFR-020")
    assert outcome.result.has_errors()
    warnings = diagnostics_with_code(outcome.result, "VAL-INFR-020")
    assert warnings and warnings[0].severity is Severity.WARNING

    # the record is still *preserved* (no silent repair/drop)
    from .phase2_support import load_project, roundtrip_text

    text = roundtrip_text(document)
    assert "TUN-01" in text

    # opaque records *without* an id stay legal and untouched
    document = grr_document()
    layer_of(document)["tunnels"] = [{"name": "no id here", "length_m": 500.0}]
    result = validate(document).result
    assert not has_code(result, "VAL-PHASE-002")
    assert not has_code(result, "VAL-INFR-020")
    assert result.error_count == 0
    assert load_project(document) is not None


# ---------------------------------------------------------------------------
# TEST P2-016
# ---------------------------------------------------------------------------
def test_p2_016_unknown_extension_fields_are_preserved_everywhere():
    """TEST P2-016 - unknown extension fields survive import -> export at every level."""
    from .phase2_support import load_project, roundtrip_text

    document = grr_document()
    layer = layer_of(document)
    layer["future_layer_field"] = {"a": 1}
    entry(document, "tracks", "TR-C-P2")["future_track_field"] = "kept"
    entry(document, "stations", "STA-CEN")["future_station_field"] = [1, 2, 3]
    layer["vertical_profiles"][0]["points"][0]["future_point_field"] = True

    text = roundtrip_text(document)
    assert "future_layer_field" in text
    assert "future_track_field" in text
    assert "future_station_field" in text
    assert "future_point_field" in text

    import json

    again = roundtrip_text(json.loads(text))
    assert again == text  # import -> export -> import -> export is byte-stable

    project = load_project(document)
    assert project is not None
