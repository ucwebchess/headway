"""Phase-2 tests: typed physical infrastructure models, geometry and alignment rules.

Acceptance tests covered here: TEST P2-001 ... TEST P2-007.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from railway_headway_sim.infrastructure import grr_fixtures
from railway_headway_sim.models.enums import DiagnosticCategory, EdgeTraversal, ValidationScope
from railway_headway_sim.models.infrastructure import (
    CATALOGUE_SPEC,
    LEGACY_CATALOGUE_KEYS,
    PHASE2_CATALOGUE_KEYS,
    Alignment,
    HorizontalGeometrySection,
    Platform,
    SpeedRestriction,
    Station,
    StoppingMark,
    Track,
    TrackGroup,
    VerticalProfile,
)
from railway_headway_sim.validation import codes

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
# TEST P2-001
# ---------------------------------------------------------------------------
def test_p2_001_all_typed_catalogues_parse_with_unit_suffixed_fields():
    """TEST P2-001 - every typed catalogue parses into strict unit-suffixed models."""
    document = grr_document()
    layer = layer_of(document)

    assert set(PHASE2_CATALOGUE_KEYS) == {
        "alignments",
        "track_groups",
        "horizontal_geometry",
        "vertical_profiles",
        "speed_restrictions",
        "nodes",
        "tracks",
        "stations",
        "platforms",
        "stopping_marks",
        "observation_points",
    }
    for key, (label, model, object_type) in CATALOGUE_SPEC.items():
        assert isinstance(label, str) and label
        assert isinstance(object_type, str) and object_type
        entries = layer[key]
        assert entries, f"{key} must not be empty in GRR-01"
        for record in entries:
            parsed = model.model_validate(record)
            assert parsed.id == record["id"]

    # A unit suffix is part of the field name: naming a value 'length' or 'speed_kph'
    # does not satisfy 'length_m' / 'speed_kmh'.
    with pytest.raises(ValidationError):
        Track.model_validate(
            {
                "id": "TR-X",
                "from_node": "A",
                "to_node": "B",
                "length": 100.0,  # unit suffix missing -> length_m is absent
                "directionality": "BOTH",
                "chainage_map": {"mode": "LINEAR", "start_km": 0.0, "end_km": 0.1},
            }
        )
    with pytest.raises(ValidationError):
        SpeedRestriction.model_validate(
            {"id": "SPR-X", "alignment_id": "ALN-MAIN", "start_chainage_km": 0.0,
             "end_chainage_km": 1.0, "speed_kph": 100, "direction": "BOTH", "type": "PERMANENT"}
        )
    with pytest.raises(ValidationError):
        Alignment.model_validate({"id": "ALN-X", "start_chainage_km": 0.0, "end_chainage_km": "1.0"})

    # Unknown *extension* fields are preserved (Phase-1 rule): they are kept, not dropped.
    extended = Alignment.model_validate(
        {"id": "ALN-X", "start_chainage_km": 0.0, "end_chainage_km": 1.0, "future_note": "kept"}
    )
    assert extended.future_note == "kept"


# ---------------------------------------------------------------------------
# TEST P2-002
# ---------------------------------------------------------------------------
def test_p2_002_display_units_are_a_preference_only():
    """TEST P2-002 - display_units never changes stored values (unit suffixes rule)."""
    document = grr_document()
    baseline = compile_document(document)
    baseline_track = baseline.by_id("tracks")["TR-C-P2"]

    document["display_units"]["track_distance"] = "km"
    document["display_units"]["speed"] = "m/s"
    changed = compile_document(document)
    changed_track = changed.by_id("tracks")["TR-C-P2"]

    assert baseline_track.length_m == changed_track.length_m == 11500.0
    assert baseline_track.chainage_map.start_km == changed_track.chainage_map.start_km
    speed = changed.by_id("speed_restrictions")["SPR-02"]
    assert speed.speed_kmh == 300  # still km/h in the model, regardless of the preference


# ---------------------------------------------------------------------------
# TEST P2-003
# ---------------------------------------------------------------------------
def test_p2_003_alignment_requires_end_greater_than_start():
    """TEST P2-003 - alignment end > start is enforced; a reversed alignment is INVALID."""
    document = grr_document()
    layer_of(document)["alignments"][0]["end_chainage_km"] = 0.0
    outcome = validate(document)
    assert has_code(outcome.result, codes.VAL_GEOM_002)
    assert outcome.result.status.value == "INVALID"

    document = grr_document()
    layer_of(document)["alignments"][0]["end_chainage_km"] = -5.0  # reversed
    assert has_code(validate(document).result, codes.VAL_GEOM_002)

    # the rule is a *validation* rule: the typed model still parses the data so that
    # the diagnostic can quote the exact object instead of raising during import.
    parsed = Alignment.model_validate(
        {"id": "ALN-BAD", "start_chainage_km": 10.0, "end_chainage_km": 10.0}
    )
    assert parsed.start_chainage_km == parsed.end_chainage_km == 10.0


# ---------------------------------------------------------------------------
# TEST P2-004
# ---------------------------------------------------------------------------
def test_p2_004_reference_system_alignment_id_must_resolve():
    """TEST P2-004 - reference_system.alignment_id must resolve to an alignment."""
    document = grr_document()
    assert document["reference_system"]["alignment_id"] == grr_fixtures.ALIGNMENT_ID
    alignment = compile_document(document).by_id("alignments")[grr_fixtures.ALIGNMENT_ID]
    assert alignment.start_chainage_km == 0.0
    assert alignment.end_chainage_km == 50.0

    document = grr_document()
    document["reference_system"]["alignment_id"] = "ALN-DOES-NOT-EXIST"
    outcome = validate(document)
    unresolved = diagnostics_with_code(outcome.result, codes.VAL_REGISTRY_003)
    assert unresolved, "an unresolvable reference_system.alignment_id must be reported"
    assert "ALN-DOES-NOT-EXIST" in unresolved[0].message
    assert outcome.result.has_errors()


# ---------------------------------------------------------------------------
# TEST P2-005
# ---------------------------------------------------------------------------
def test_p2_005_horizontal_geometry_curve_and_range_rules():
    """TEST P2-005 - curves need radius_m > 0 plus handedness and must stay in the alignment."""
    document = grr_document()
    curve = entry(document, "horizontal_geometry", "HGR-02")
    assert curve["type"] == "CURVE" and curve["radius_m"] > 0 and curve["handedness"] in {"LEFT", "RIGHT"}

    # a curve without a radius is rejected (VAL-GEOM-001)
    document = grr_document()
    entry(document, "horizontal_geometry", "HGR-02").pop("radius_m")
    outcome = validate(document)
    missing_radius = diagnostics_with_code(outcome.result, codes.VAL_GEOM_001)
    assert missing_radius and "HGR-02" in missing_radius[0].message

    # a zero / negative radius is equally rejected
    document = grr_document()
    entry(document, "horizontal_geometry", "HGR-02")["radius_m"] = 0.0
    assert has_code(validate(document).result, codes.VAL_GEOM_001)

    # a curve without handedness is rejected
    document = grr_document()
    entry(document, "horizontal_geometry", "HGR-02").pop("handedness")
    missing_handedness = diagnostics_with_code(validate(document).result, codes.VAL_GEOM_001)
    assert missing_handedness and "handedness" in missing_handedness[0].message

    # a section outside the alignment is rejected
    document = grr_document()
    entry(document, "horizontal_geometry", "HGR-01")["end_chainage_km"] = 60.0
    assert has_code(validate(document).result, codes.VAL_GEOM_002)

    assert HorizontalGeometrySection.model_validate(
        {"id": "HGR-X", "alignment_id": "ALN-MAIN", "start_chainage_km": 1.0,
         "end_chainage_km": 2.0, "type": "STRAIGHT"}
    ).radius_m is None


# ---------------------------------------------------------------------------
# TEST P2-006
# ---------------------------------------------------------------------------
def test_p2_006_geometry_overlap_and_coverage_rules():
    """TEST P2-006 - overlapping sections and coverage gaps are both ERRORs."""
    document = grr_document()
    entry(document, "horizontal_geometry", "HGR-02")["start_chainage_km"] = 2.0  # overlaps HGR-01
    outcome = validate(document)
    assert has_code(outcome.result, codes.VAL_GEOM_003)

    document = grr_document()
    entry(document, "horizontal_geometry", "HGR-03")["start_chainage_km"] = 19.0  # gap 18-19
    outcome = validate(document)
    assert has_code(outcome.result, codes.VAL_GEOM_004)

    document = grr_document()
    entry(document, "horizontal_geometry", "HGR-07")["end_chainage_km"] = 49.0  # stops short
    outcome = validate(document)
    assert has_code(outcome.result, codes.VAL_GEOM_004)


# ---------------------------------------------------------------------------
# TEST P2-007
# ---------------------------------------------------------------------------
def test_p2_007_vertical_profile_rules():
    """TEST P2-007 - ELEVATION_POINTS: >= 2 points, strictly increasing unique chainage, in-range."""
    document = grr_document()
    profile = layer_of(document)["vertical_profiles"][0]
    assert profile["source_mode"] == "ELEVATION_POINTS"
    assert len(profile["points"]) == 13

    document = grr_document()
    point = layer_of(document)["vertical_profiles"][0]["points"][3]
    point["chainage_km"] = 2.5  # duplicate + out of order
    outcome = validate(document)
    assert has_code(outcome.result, codes.VAL_GEOM_005)

    document = grr_document()
    layer_of(document)["vertical_profiles"][0]["points"] = [
        {"id": "VPP-01", "chainage_km": 1.0, "elevation_m": 100.0}
    ]
    assert has_code(validate(document).result, codes.VAL_GEOM_006)

    document = grr_document()
    layer_of(document)["vertical_profiles"][0]["points"][0]["chainage_km"] = 60.0
    assert has_code(validate(document).result, codes.VAL_GEOM_002)

    assert VerticalProfile.model_validate(
        {"id": "VP-X", "alignment_id": "ALN-MAIN", "source_mode": "ELEVATION_POINTS",
         "points": [{"id": "VPP-X1", "chainage_km": 0.0, "elevation_m": 1.0},
                    {"id": "VPP-X2", "chainage_km": 1.0, "elevation_m": 2.0}]}
    ).id == "VP-X"


def test_phase2_models_out_of_scope_guards():
    """Regression - Phase-2 models contain no dynamics/legacy-incompatible fields."""
    assert set(PHASE2_CATALOGUE_KEYS).isdisjoint(LEGACY_CATALOGUE_KEYS)
    assert EdgeTraversal.WITH_EDGE.value == "WITH_EDGE"
    assert ValidationScope.PHASE2_PHYSICAL_INFRASTRUCTURE.value == "PHASE-2 PHYSICAL INFRASTRUCTURE"
    assert DiagnosticCategory.INFRASTRUCTURE.value == "INFRASTRUCTURE"
    # GRR-01 does not contain the opaque (legacy) catalogues as non-empty data
    layer = layer_of(grr_document())
    for key in LEGACY_CATALOGUE_KEYS:
        assert layer[key] == []
    # sanity: the four GRR stations and the two track groups are typed correctly
    assert {station["id"] for station in catalogue(grr_document(), "stations")} == {
        "STA-ALPHA", "STA-CEN", "STA-VAL", "STA-DELTA",
    }
    assert [group["id"] for group in catalogue(grr_document(), "track_groups")] == ["TG-ML1", "TG-ML2"]
    assert Station.model_validate(
        {"id": "S1", "type": "TERMINAL", "reference_chainage_km": 0.0}
    ).type.value == "TERMINAL"
    assert Platform.model_validate(
        {"id": "P1", "station_id": "S1", "track_id": "T1", "usable_start_m": 0.0,
         "usable_end_m": 10.0, "usable_length_m": 10.0, "directionality": "BOTH"}
    ).usable_length_m == 10.0
    assert StoppingMark.model_validate(
        {"id": "M1", "platform_id": "P1", "track_id": "T1", "direction": "FORWARD", "position_m": 1.0}
    ).position_m == 1.0
    assert SpeedRestriction.model_validate(
        {"id": "SR1", "alignment_id": "ALN-MAIN", "start_chainage_km": 0.0, "end_chainage_km": 1.0,
         "speed_kmh": 100, "direction": "BOTH", "type": "PERMANENT"}
    ).speed_kmh == 100
    assert TrackGroup.model_validate({"id": "TG1", "directionality": "BOTH"}).id == "TG1"
    assert Platform.model_validate(
        {"id": "P2", "station_id": "S1", "track_id": "T1", "usable_start_m": 0.0,
         "usable_end_m": 5.0, "usable_length_m": 5.0, "directionality": "BOTH",
         "resource_id": "RES-FUTURE"}
    ).resource_id == "RES-FUTURE"
