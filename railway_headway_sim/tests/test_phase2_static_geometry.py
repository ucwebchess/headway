"""Phase-2 tests: the static train-footprint utility (Sections Y/Z/AM).

Acceptance tests covered here: TEST P2-021 ... TEST P2-024.

Static geometry only: nothing in this module computes time, speed, acceleration,
braking, occupation, headway or capacity.
"""

from __future__ import annotations

import pytest

from railway_headway_sim.infrastructure import grr_fixtures
from railway_headway_sim.infrastructure.mapping import (
    ChainageMapError,
    chainage_to_edge_position,
    edge_position_to_chainage,
)
from railway_headway_sim.infrastructure.static_geometry import (
    compute_static_footprint,
    evaluate_static_footprint,
    traversal_for_direction,
)
from railway_headway_sim.models.enums import EdgeTraversal, Direction
from railway_headway_sim.models.infrastructure import Platform, StoppingMark, Track

from .phase2_support import catalogue, compile_document, entry, grr_document, layer_of, validate


def _typed(document):
    """Return ``(tracks, platforms, marks)`` dictionaries of typed models."""
    compiled = compile_document(document)
    return (
        {track.id: track for track in compiled.catalogue("tracks")},
        {platform.id: platform for platform in compiled.catalogue("platforms")},
        {mark.id: mark for mark in compiled.catalogue("stopping_marks")},
    )


# ---------------------------------------------------------------------------
# TEST P2-021
# ---------------------------------------------------------------------------
def test_p2_021_orientation_rules_and_fit_flags():
    """TEST P2-021 - WITH_EDGE: rear = front - L; AGAINST_EDGE: rear = front + L."""
    tracks, platforms, marks = _typed(grr_document())
    mark = marks["STOP-C-P2-DEP"]
    track = tracks[mark.track_id]
    platform = platforms[mark.platform_id]

    with_edge = compute_static_footprint(track, mark, 202.0, EdgeTraversal.WITH_EDGE, platform=platform)
    assert with_edge.front_position_m == 420.0
    assert with_edge.rear_position_m == 218.0
    # the train fits inside the *track* but infringes the usable platform range by 12 m
    assert with_edge.fit_in_track is True
    assert with_edge.fit_in_usable_platform is False
    assert with_edge.critical_boundary_m == 230.0  # usable_start is critical WITH_EDGE
    assert with_edge.rear_margin_m == pytest.approx(-12.0)
    assert with_edge.rear_infringement_m == pytest.approx(12.0)
    assert with_edge.rear_clearance_m == 0.0
    assert "rear infringement 12 m" in with_edge.describe()

    against_edge = compute_static_footprint(track, mark, 202.0, EdgeTraversal.AGAINST_EDGE, platform=platform)
    assert against_edge.rear_position_m == 622.0
    assert against_edge.critical_boundary_m == 11000.0  # usable_end is critical AGAINST_EDGE
    assert against_edge.fit_in_usable_platform is True

    # fit_in_track is a static bounds check of the occupied segment
    long_train = compute_static_footprint(track, mark, 12000.0, EdgeTraversal.WITH_EDGE, platform=platform)
    assert long_train.fit_in_track is False
    assert long_train.fit_in_usable_platform is False

    # documented precondition: a non-positive static length is an input error
    with pytest.raises(ValueError):
        compute_static_footprint(track, mark, 0.0, EdgeTraversal.WITH_EDGE)
    with pytest.raises(ValueError):
        evaluate_static_footprint(track, front_position_m=1.0, train_length_m=-1.0,
                                  traversal=EdgeTraversal.WITH_EDGE)


# ---------------------------------------------------------------------------
# TEST P2-022
# ---------------------------------------------------------------------------
def test_p2_022_frozen_static_benchmarks():
    """TEST P2-022 - the five frozen static benchmarks reproduce exactly."""
    tracks, platforms, _marks = _typed(grr_document())
    observed = []
    for benchmark in grr_fixtures.GRR01_STATIC_BENCHMARKS:
        platform = platforms[benchmark["platform_id"]]
        result = evaluate_static_footprint(
            tracks[benchmark["track_id"]],
            front_position_m=benchmark["front_position_m"],
            train_length_m=benchmark["train_length_m"],
            traversal=EdgeTraversal(benchmark["traversal"]),
            marker_id=benchmark["id"],
            platform=platform,
        )
        assert result.front_position_m == benchmark["front_position_m"]
        assert result.rear_position_m == benchmark["expected_rear_position_m"]
        assert result.critical_boundary_m == benchmark["critical_boundary_m"]
        if "expected_rear_infringement_m" in benchmark:
            assert result.rear_infringement_m == benchmark["expected_rear_infringement_m"]
            observed.append(f"{result.rear_infringement_m:g} m infringement")
        else:
            assert result.rear_clearance_m == benchmark["expected_rear_clearance_m"]
            observed.append(f"{result.rear_clearance_m:g} m clearance")

    assert observed == [
        "12 m infringement",
        "13 m clearance",
        "12 m infringement",
        "78 m clearance",
        "98 m clearance",
    ]


# ---------------------------------------------------------------------------
# TEST P2-023
# ---------------------------------------------------------------------------
def test_p2_023_footprint_chainage_mapping_and_notes():
    """TEST P2-023 - front/rear chainages are mapped; unmappable positions are reported."""
    tracks, platforms, marks = _typed(grr_document())
    mark = marks["STOP-C-P2-DEP"]
    track = tracks[mark.track_id]
    platform = platforms[mark.platform_id]

    footprint = compute_static_footprint(track, mark, 202.0, EdgeTraversal.WITH_EDGE, platform=platform)
    assert footprint.front_chainage_km == pytest.approx(15.5 + 0.420, abs=1e-9)
    assert footprint.rear_chainage_km == pytest.approx(15.5 + 0.218, abs=1e-9)
    assert footprint.notes == ()

    # a position outside the mapped range is reported as a note, never silently mapped
    beyond = evaluate_static_footprint(
        track, front_position_m=12500.0, train_length_m=202.0, traversal=EdgeTraversal.WITH_EDGE,
        marker_id="EVAL-BEYOND", platform=platform,
    )
    assert beyond.front_chainage_km is None
    assert beyond.notes and "could not be mapped" in beyond.notes[0]

    # the mapping itself is exact and invertible (1e-9 km chainage tolerance)
    for position in (0.0, 1.0, 420.0, track.length_m):
        chainage = edge_position_to_chainage(track, position)
        assert chainage_to_edge_position(track, chainage) == pytest.approx(position, abs=1e-6)

    with pytest.raises(ChainageMapError):
        edge_position_to_chainage(track, -1.0)


# ---------------------------------------------------------------------------
# TEST P2-024
# ---------------------------------------------------------------------------
def test_p2_024_marker_direction_maps_to_traversal_and_baseline_table():
    """TEST P2-024 - FORWARD -> WITH_EDGE, REVERSE -> AGAINST_EDGE; baseline table holds."""
    assert traversal_for_direction(Direction.FORWARD) is EdgeTraversal.WITH_EDGE
    assert traversal_for_direction(Direction.REVERSE) is EdgeTraversal.AGAINST_EDGE
    assert traversal_for_direction("FORWARD") is EdgeTraversal.WITH_EDGE
    assert traversal_for_direction("REVERSE") is EdgeTraversal.AGAINST_EDGE

    tracks, platforms, marks = _typed(grr_document())
    for assignment in grr_fixtures.BASELINE_STATIC_ASSIGNMENTS:
        mark = marks[assignment["marker_id"]]
        traversal = traversal_for_direction(mark.direction)
        assert traversal is EdgeTraversal(assignment["traversal"]), assignment["marker_id"]
        result = compute_static_footprint(
            tracks[mark.track_id], mark, assignment["train_length_m"], traversal,
            platform=platforms[mark.platform_id],
        )
        assert result.fit_in_usable_platform is assignment["expected_fit"], assignment["marker_id"]
        assert result.critical_boundary_m == assignment["expected_critical_boundary_m"]
        assert result.rear_margin_m == pytest.approx(assignment["expected_rear_margin_m"], abs=1e-9)

    # the amended Valley P1 reverse mark is the value used by the fixture ...
    assert marks[grr_fixtures.STOP_V_P1_R_ID].position_m == 250.0
    # ... while the frozen pre-amendment evidence file keeps 220.0 m
    document = grr_document()
    entry(document, "stopping_marks", grr_fixtures.STOP_V_P1_R_ID)["position_m"] = 220.0
    frozen = entry(document, "stopping_marks", grr_fixtures.STOP_V_P1_R_ID)
    assert frozen["position_m"] == 220.0
    assert validate(document).result.error_count == 0  # both values are physically consistent


def test_phase2_static_geometry_has_no_dynamics():
    """Regression - the static geometry module exposes no time/dynamics API."""
    import railway_headway_sim.infrastructure.static_geometry as module

    forbidden = ("time", "speed", "acceleration", "brake", "braking", "occupation", "headway")
    public = [name for name in dir(module) if not name.startswith("_")]
    assert not [name for name in public if any(word in name.lower() for word in forbidden)]
    assert Platform.model_validate(
        {"id": "P", "station_id": "S", "track_id": "T", "usable_start_m": 0.0, "usable_end_m": 1.0,
         "usable_length_m": 1.0, "directionality": "BOTH"}
    ).id == "P"
    assert Track.model_validate(layer_of(grr_document())["tracks"][0]).length_m > 0
    assert StoppingMark.model_validate(layer_of(grr_document())["stopping_marks"][0]).position_m >= 0
    assert [mark["id"] for mark in catalogue(grr_document(), "stopping_marks")][:2] == [
        "STOP-A-P1-ARR", "STOP-A-P1-DEP",
    ]
