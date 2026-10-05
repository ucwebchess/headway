"""GRR-01 Part A regression tests (frozen reference project contract).

Acceptance tests covered here: TEST P2-REG-G001 ... TEST P2-REG-G005.
"""

from __future__ import annotations

import json
import pathlib

from railway_headway_sim import ProjectController
from railway_headway_sim.infrastructure import grr_audit, grr_fixtures
from railway_headway_sim.io.project_io import import_project_from_data, project_hash, to_json_text
from railway_headway_sim.models.enums import Direction, ValidationScope
from railway_headway_sim.validation import codes

from .phase2_support import (
    catalogue,
    compile_document,
    diagnostics_with_code,
    entry,
    grr_document,
    has_code,
    layer_of,
    load_project,
    roundtrip_text,
    validate,
)

EXAMPLES_PATH = pathlib.Path(__file__).resolve().parents[2] / "examples" / "GRR-01.json"
FROZEN_PATH = pathlib.Path(__file__).resolve().parents[2] / "docs" / "GRR-01_FROZEN_PHYSICAL_v1.0.json"


# ---------------------------------------------------------------------------
# TEST P2-REG-G001
# ---------------------------------------------------------------------------
def test_p2_reg_g001_grr01_loads_with_the_frozen_inventory():
    """TEST P2-REG-G001 - GRR-01 loads with exactly the frozen object counts and no errors."""
    outcome = validate(grr_document())
    result = outcome.result
    assert result.status.value == "VALID", [d.format_line() for d in result.diagnostics]
    assert (result.error_count, result.warning_count) == (0, 0)
    assert result.scope is ValidationScope.PHASE2_PHYSICAL_INFRASTRUCTURE

    layer = layer_of(grr_document())
    counts = {
        key: len(layer[key])
        for key in grr_fixtures.GRR01_EXPECTED_COUNTS
        if key != "vertical_profile_points"
    }
    counts["vertical_profile_points"] = sum(len(p["points"]) for p in layer["vertical_profiles"])
    assert counts == grr_fixtures.GRR01_EXPECTED_COUNTS
    assert counts == {
        "alignments": 1,
        "track_groups": 2,
        "horizontal_geometry": 7,
        "vertical_profile_points": 13,
        "speed_restrictions": 8,
        "nodes": 50,
        "tracks": 59,
        "stations": 4,
        "platforms": 9,
        "stopping_marks": 14,
        "observation_points": 9,
    }

    # one layer only, id LYR-MAIN, declared physical
    assert len(outcome.project.infrastructure) == 1
    assert layer["id"] == grr_fixtures.LAYER_ID == "LYR-MAIN"
    assert layer["physical_mode"] == "PHYSICAL"

    # the GRR inventory diagnostics are clean for the frozen document
    assert grr_audit.inventory_diagnostics(grr_document()) == []
    # ... and they fire when the frozen contract is broken
    broken = grr_document()
    del broken["infrastructure"][0]["nodes"][0]
    broken_ids = {diagnostic.code for diagnostic in grr_audit.inventory_diagnostics(broken)}
    assert broken_ids == {"VAL-GRR-001", "VAL-GRR-002"}
    broken = grr_document()
    broken["provenance"].pop("approved_amendments")
    assert "VAL-GRR-003" in {d.code for d in grr_audit.inventory_diagnostics(broken)}


# ---------------------------------------------------------------------------
# TEST P2-REG-G002
# ---------------------------------------------------------------------------
def test_p2_reg_g002_regional_inventory():
    """TEST P2-REG-G002 - regional node/edge counts (6/18/8/12/6 and 8/4/23/8/12/4)."""
    layer = layer_of(grr_document())
    node_ids = {node["id"] for node in layer["nodes"]}
    track_ids = {track["id"] for track in layer["tracks"]}
    declared_node_ids = {item for ids in grr_fixtures.REGION_NODE_IDS.values() for item in ids}
    declared_track_ids = {item for ids in grr_fixtures.REGION_TRACK_IDS.values() for item in ids}

    assert declared_node_ids == node_ids
    assert declared_track_ids == track_ids
    assert {region: len(ids) for region, ids in grr_fixtures.REGION_NODE_IDS.items()} == {
        "Alpha": 6, "Central": 18, "XC-24": 8, "Valley": 12, "Delta": 6,
    }
    assert {region: len(ids) for region, ids in grr_fixtures.REGION_TRACK_IDS.items()} == {
        "Open line": 8, "Alpha": 4, "Central": 23, "XC-24": 8, "Valley": 12, "Delta": 4,
    }
    assert sum(len(ids) for ids in grr_fixtures.REGION_NODE_IDS.values()) == 50
    assert sum(len(ids) for ids in grr_fixtures.REGION_TRACK_IDS.values()) == 59

    # the topology itself is one connected component of exactly 50 nodes / 59 edges
    topology = compile_document().topology()
    assert topology.is_connected()
    assert len(topology.node_ids()) == 50
    assert len(topology.track_ids()) == 59

    # every track endpoint is a declared node (nothing invented on load)
    endpoints = {
        endpoint
        for track in layer["tracks"]
        for endpoint in (track["from_node"], track["to_node"])
    }
    assert endpoints == node_ids

    # the two track groups declare their frozen directionality and normal direction
    groups = {group["id"]: group for group in layer["track_groups"]}
    assert set(groups) == {"TG-ML1", "TG-ML2"}
    assert groups["TG-ML1"]["normal_direction"] == "FORWARD"
    assert groups["TG-ML2"]["normal_direction"] == "REVERSE"
    assert all(group["directionality"] == "BOTH" for group in groups.values())

    # the final Central east crossing names are used; no provisional name survives
    assert all(name in track_ids for name in grr_fixtures.CENTRAL_EAST_CROSS_EDGE_NAMES)
    assert not [name for name in grr_fixtures.FORBIDDEN_PROVISIONAL_EDGE_NAMES if name in track_ids]


# ---------------------------------------------------------------------------
# TEST P2-REG-G003
# ---------------------------------------------------------------------------
def test_p2_reg_g003_global_registry_uniqueness_and_draft_guard():
    """TEST P2-REG-G003 - globally unique registered IDs; a broken draft cannot be exported."""
    compiled = compile_document()
    ids = tuple(registered.object_id for registered in compiled.registry.iter_registrations())
    assert len(ids) == len(set(ids)) == 177
    assert compiled.registry.size() == 177
    assert compiled.registry.duplicates() == ()
    assert sorted(compiled.registry.type_counts()) == sorted(
        [
            "alignment", "track_group", "horizontal_geometry_section", "vertical_profile",
            "vertical_profile_point", "speed_restriction", "node", "track", "station",
            "platform", "stopping_mark", "observation_point",
        ]
    )
    assert set(compiled.registry.type_counts()) == set(
        [
            "alignment", "track_group", "horizontal_geometry_section", "vertical_profile",
            "vertical_profile_point", "speed_restriction", "node", "track", "station",
            "platform", "stopping_mark", "observation_point",
        ]
    )
    assert compiled.type_counts()["tracks"] == 59 and compiled.type_counts()["nodes"] == 50

    # a duplicate *inside* one catalogue is an error
    document = grr_document()
    duplicate = dict(entry(document, "nodes", "N-CEN-W"))
    layer_of(document)["nodes"].append(duplicate)
    inside = diagnostics_with_code(validate(document).result, codes.VAL_REGISTRY_001)
    assert inside and inside[0].object_id == "N-CEN-W"

    # a cross-type duplicate is an error as well (declared VAL-REG-011 supersession)
    document = grr_document()
    entry(document, "platforms", "PLT-ALP-P1")["id"] = "STA-CEN"
    outgoing = validate(document)
    cross = diagnostics_with_code(outgoing.result, codes.VAL_REGISTRY_001)
    assert cross and cross[0].object_id == "STA-CEN"
    assert outgoing.result.status.value == "INVALID"

    # the controller draft mechanism (APP-EDIT-002) refuses to commit or export the broken draft
    controller = ProjectController()
    controller.replace_project(load_project(grr_document()), message="GRR-01 loaded")
    controller.validate_project()
    hash_before = controller.current_project_hash
    controller.stage_draft(document, description="duplicate station id")
    assert controller.draft_blocks_export is True
    assert has_code(controller.commit_draft(), codes.APP_EDIT_002)
    assert controller.export_json(download=False, directory="/tmp") is None
    assert controller.current_project_hash == hash_before
    controller.discard_draft()
    assert controller.draft_pending is False
    assert controller.export_json(download=False, directory="/tmp") is not None


# ---------------------------------------------------------------------------
# TEST P2-REG-G004
# ---------------------------------------------------------------------------
def test_p2_reg_g004_section_ba_contradiction_scan_is_clean():
    """TEST P2-REG-G004 - the Section BA contradiction scan reports no contradiction."""
    findings = grr_audit.scan_contradictions()
    assert len(findings) == 13
    assert [finding.check_id for finding in findings] == [
        "BA-01", "BA-02", "BA-03", "BA-04", "BA-05", "BA-06", "BA-07",
        "BA-08", "BA-09", "BA-10", "BA-11", "BA-12", "BA-13",
    ]
    summary = grr_audit.scan_summary()
    assert summary["contradictions"] == []
    assert summary["checks"] == 13
    assert all(finding.severity == "OK" for finding in findings)
    for finding in findings:
        assert finding.evidence, f"{finding.check_id} must carry evidence"

    # the scan is read-only: a second run gives byte-identical results and the
    # fixture is unchanged afterwards
    before = json.dumps(grr_fixtures.build_grr01_document(), sort_keys=True)
    assert json.dumps(grr_fixtures.build_grr01_document(), sort_keys=True) == before
    assert grr_audit.format_findings() == grr_audit.format_findings()


# ---------------------------------------------------------------------------
# TEST P2-REG-G005
# ---------------------------------------------------------------------------
def test_p2_reg_g005_grr01_load_stability_and_evidence_files():
    """TEST P2-REG-G005 - loading/export is stable; timestamps, hash and amendments hold."""
    document = grr_document()
    outcomes = import_project_from_data(document)
    assert outcomes.ok and outcomes.project is not None
    project = outcomes.project

    text_a = to_json_text(project)
    again = import_project_from_data(json.loads(text_a))
    assert again.project is not None
    text_b = to_json_text(again.project)
    assert text_a == text_b, "import -> export -> import -> export must be byte-stable"

    # loading must not rewrite created_utc/modified_utc
    assert project.project.created_utc == grr_fixtures.GRR01_CREATED_UTC
    assert project.project.modified_utc == grr_fixtures.GRR01_MODIFIED_UTC
    assert again.project.project.created_utc == grr_fixtures.GRR01_CREATED_UTC
    assert again.project.project.modified_utc == grr_fixtures.GRR01_MODIFIED_UTC

    # switching the application direction never changes the stored document or its hash
    controller = ProjectController()
    controller.replace_project(project, message="loaded")
    hash_before = controller.current_project_hash
    controller.set_direction(Direction.REVERSE)
    controller.set_direction(Direction.FORWARD)
    assert controller.current_project_hash == hash_before == project_hash(project)
    assert to_json_text(controller.project) == text_a

    # the documented approved amendment is recorded and applied
    provenance = document["provenance"]
    amendments = {item["id"]: item for item in provenance["approved_amendments"]}
    assert set(amendments) == {"GRR-AMD-001", "GRR-AMD-003", "GRR-AMD-004"}
    assert amendments["GRR-AMD-001"]["from"] == grr_fixtures.FROZEN_STOP_V_P1_R_POSITION_M == 220.0
    assert amendments["GRR-AMD-001"]["to"] == 250.0
    mark = entry(document, "stopping_marks", grr_fixtures.STOP_V_P1_R_ID)
    assert mark["position_m"] == 250.0

    # GRR-AMD-004: the frozen Valley P2 boundary is a platform value, not a constant
    platform = entry(document, "platforms", "PLT-VAL-P2")
    assert (platform["usable_start_m"], platform["usable_end_m"]) == (100.0, 500.0)
    assert platform["usable_length_m"] == 400.0
    assert amendments["GRR-AMD-004"]["object_id"] == "PLT-VAL-P2"
    assert entry(
        json.loads(FROZEN_PATH.read_text(encoding="utf-8")) if FROZEN_PATH.exists() else document,
        "platforms",
        "PLT-VAL-P2",
    )["usable_end_m"] == 500.0

    # the reference train lengths are fixture/test data, never project data
    assert (grr_fixtures.HSR_REF_LENGTH_M, grr_fixtures.REG_REF_LENGTH_M) == (202.0, 160.0)
    exported = json.loads(text_a)
    assert "train_length" not in json.dumps(exported)
    assert "202.0" not in text_a and "160.0" not in text_a

    # the delivered evidence files exist and differ only in the recorded amendment
    if EXAMPLES_PATH.exists() and FROZEN_PATH.exists():
        example_text = EXAMPLES_PATH.read_text(encoding="utf-8")
        frozen_text = FROZEN_PATH.read_text(encoding="utf-8")
        example_document = json.loads(example_text)
        frozen_document_json = json.loads(frozen_text)
        assert example_text.strip() == roundtrip_text(grr_document()).strip()
        assert "approved_amendments" in example_document["provenance"]
        assert "approved_amendments" not in frozen_document_json["provenance"]
        assert (
            entry(frozen_document_json, "stopping_marks", grr_fixtures.STOP_V_P1_R_ID)["position_m"]
            == 220.0
        )
        assert (
            entry(example_document, "stopping_marks", grr_fixtures.STOP_V_P1_R_ID)["position_m"]
            == 250.0
        )
        example_without = json.loads(example_text)
        frozen_without = json.loads(frozen_text)
        example_without["provenance"] = {}
        frozen_without["provenance"] = {}
        entry(example_without, "stopping_marks", grr_fixtures.STOP_V_P1_R_ID)["position_m"] = 220.0
        assert example_without == frozen_without, (
            "the frozen evidence file must differ from GRR-01.json only in the approved amendment"
        )

    # the frozen fixture (used by tests and the docs) still matches the delivered file set
    assert catalogue(grr_document(), "stations")[0]["id"] == "STA-ALPHA"
    assert len(catalogue(grr_document(), "observation_points")) == 9
