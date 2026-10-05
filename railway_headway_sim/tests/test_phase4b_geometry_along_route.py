"""Phase-4B acceptance tests: geometry along a compiled route.

TEST P4-031 ... TEST P4-048.

Scope of this module (master specification, Phase 4B):

* :class:`~railway_headway_sim.infrastructure.geometry_along_route.RouteGeometry`
  answers, for any route distance ``s`` of a Phase-4A
  :class:`~railway_headway_sim.infrastructure.compiled_network.RouteCoordinateSystem`,
  what the physical elevation ``[m]``, the effective gradient ``[permille]`` in the
  direction of travel and the stored curve radius ``[m]`` (or ``None``) are, plus the
  length-weighted mean of the gradient over a train footprint ``[permille]``.

The tests below cover the acceptance criteria of Phase 4B: construction from the frozen
GRR-01 project, interpolation against the stored vertical profile ``VP-MAIN``, the
direction rules (elevation equal, gradient opposite-signed, radius equal), the
piecewise-constant gradient, the footprint weighted mean, the error and diagnostic
behaviour, the read-only guarantees, the dependency/scope scans and the suite
registration.

Every expected value is derived from the frozen project's own stored catalogues inside
the test (never hand-typed as a constant that the data must match), and no test writes to
any protected artefact.
"""

from __future__ import annotations

import ast
import copy
import dataclasses
import hashlib
import importlib
import json
import re
from pathlib import Path
from typing import Any

import pytest

from railway_headway_sim.infrastructure import RouteGeometry
from railway_headway_sim.infrastructure.compiled_network import (
    RouteCoordinateError,
    RouteCoordinateSystem,
    compile_network,
)
from railway_headway_sim.infrastructure.geometry_along_route import (
    COVERAGE_TOLERANCE_KM,
    ELEVATION_UNIT,
    GRADIENT_UNIT,
    RADIUS_UNIT,
)
from railway_headway_sim.infrastructure.mapping import edge_position_to_chainage
from railway_headway_sim.io.project_io import (
    document_hash,
    import_project_from_data,
    to_normalized_dict,
)
from railway_headway_sim.models.enums import Direction, EdgeTraversal, Severity
from railway_headway_sim.models.infrastructure import Track

_REPO_ROOT = Path(__file__).resolve().parents[2]
_PROTECTED_GRR01 = _REPO_ROOT / "examples" / "GRR-01.json"
_COMPANION = _REPO_ROOT / "examples" / "GRR-01-paths.json"
_GEOMETRY_MODULE = (
    _REPO_ROOT / "railway_headway_sim" / "infrastructure" / "geometry_along_route.py"
)
_SECTION_D_PATTERNS = _REPO_ROOT / "docs" / "SECTION_D_PATTERNS.md"
_CONFTEST = _REPO_ROOT / "railway_headway_sim" / "tests" / "conftest.py"
_INVENTORY_BUILDER = _REPO_ROOT / "build_test_inventory.py"

#: sha256 of the protected reference project file (must not change; checked here).
PROTECTED_GRR01_SHA256 = "ad0a26265d4e072aeedcc69161bef90f200c20b4efb12a4d56a5276c4a4f7a56"

#: Canonical document hash of the reference project (must not change).
CANONICAL_GRR01_HASH = "5189aaa2340c17022666ef44772c7d34f99b2fea9ee9609bb7b7513238ef4dbe"

#: sha256 of the declared-paths companion file (must not change in Phase 4B).
COMPANION_SHA256 = "c62c3ee6d910457a6f59533c2b92b4e65a0cd8c64dff49fe8e6796ed829fac86"

#: The alignment whose stored geometry the H1 corridor reads.
ALIGNMENT_ID = "ALN-MAIN"
VERTICAL_PROFILE_ID = "VP-MAIN"

#: The two declared paths of the H1 corridor (one physical corridor, two directions).
REFERENCE_PATH_IDS: tuple[str, ...] = ("PATH-H1-F", "PATH-H1-R")

#: Probe (metres) used to read a route position just inside a route segment.
_EPS_M = 1e-3


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _protected_file_sha256() -> str:
    """Return the sha256 of the protected reference project file."""
    return hashlib.sha256(_PROTECTED_GRR01.read_bytes()).hexdigest()


def _companion_sha256() -> str:
    """Return the sha256 of the declared-paths companion file."""
    return hashlib.sha256(_COMPANION.read_bytes()).hexdigest()


def _grr_document() -> dict[str, Any]:
    """Return the frozen reference project as plain data."""
    return json.loads(_PROTECTED_GRR01.read_text(encoding="utf-8"))


def _load(document: dict[str, Any]) -> Any:
    """Import a project document and assert that it loads."""
    outcome = import_project_from_data(document)
    assert outcome.ok, outcome.summary_text()
    return outcome.project


def _layer(document: dict[str, Any]) -> dict[str, Any]:
    """Return the single infrastructure layer of a project document."""
    return document["infrastructure"][0]


def _tracks(layer: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Return the layer's tracks keyed by id."""
    return {track["id"]: track for track in layer["tracks"]}


def _profile(document: dict[str, Any]) -> dict[str, Any]:
    """Return the stored vertical profile of the reference alignment."""
    layer = _layer(document)
    profile = next(
        item
        for item in layer["vertical_profiles"]
        if item["alignment_id"] == ALIGNMENT_ID
    )
    return profile


def _profile_points(document: dict[str, Any]) -> tuple[tuple[float, float], ...]:
    """Return the stored ``(chainage_km, elevation_m)`` points, sorted by chainage."""
    return tuple(
        sorted(
            (float(point["chainage_km"]), float(point["elevation_m"]))
            for point in _profile(document)["points"]
        )
    )


def _sections(document: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    """Return the stored horizontal geometry sections of the reference alignment."""
    return tuple(
        section
        for section in _layer(document)["horizontal_geometry"]
        if section["alignment_id"] == ALIGNMENT_ID
    )


def _reference_network(project: Any) -> Any:
    """Compile a project with the declared-paths companion file of the H1 corridor."""
    return compile_network(project, paths_source=_COMPANION.read_text(encoding="utf-8"))


def _geometry(
    project: Any, path_id: str = REFERENCE_PATH_IDS[0], direction: Direction = Direction.FORWARD
) -> RouteGeometry:
    """Return the route geometry of one declared path and direction."""
    network = _reference_network(project)
    assert network.diagnostics == ()
    return RouteGeometry(project, network.route(path_id, direction))


def _chainage_span_km(
    document: dict[str, Any], segments: Any
) -> tuple[float, float]:
    """Return the chainage span ``(min_km, max_km)`` the route covers.

    The span is derived from the project's own tracks and the compiled route's
    traversals through the Phase-2 position/chainage mapping.
    """
    tracks = _tracks(_layer(document))
    chainages: list[float] = []
    for segment in segments:
        track = Track.model_validate(tracks[segment.edge_id])
        if segment.traversal is EdgeTraversal.WITH_EDGE:
            low_m, high_m = 0.0, float(track.length_m)
        else:
            low_m, high_m = float(track.length_m), 0.0
        chainages.append(edge_position_to_chainage(track, low_m))
        chainages.append(edge_position_to_chainage(track, high_m))
    return min(chainages), max(chainages)


def _route_distance_of_chainage_km(
    document: dict[str, Any], route: RouteCoordinateSystem, chainage_km: float
) -> float:
    """Return the route distance ``[m]`` of a physical chainage on a compiled route.

    The route's own tracks are read through the Phase-2 mapping, so the value is derived
    from the project's data and the compiled traversals — nothing is hand-typed.
    """
    tracks = _tracks(_layer(document))
    for segment in route.segments:
        track = Track.model_validate(tracks[segment.edge_id])
        length_m = float(track.length_m)
        if segment.traversal is EdgeTraversal.WITH_EDGE:
            start_m, end_m = 0.0, length_m
        else:
            start_m, end_m = length_m, 0.0
        chainage_start_km = edge_position_to_chainage(track, start_m)
        chainage_end_km = edge_position_to_chainage(track, end_m)
        span_km = chainage_end_km - chainage_start_km
        if span_km == 0.0:
            continue
        fraction = (chainage_km - chainage_start_km) / span_km
        if -COVERAGE_TOLERANCE_KM <= fraction <= 1.0 + COVERAGE_TOLERANCE_KM:
            offset_m = fraction * (segment.end_s_m - segment.start_s_m)
            if -_EPS_M <= offset_m <= (segment.end_s_m - segment.start_s_m) + _EPS_M:
                return segment.start_s_m + min(
                    max(offset_m, 0.0), segment.end_s_m - segment.start_s_m
                )
    raise AssertionError(f"chainage {chainage_km} km is not on route {route.path_id!r}")


def _stored_gradient_between(
    document: dict[str, Any], start_km: float, end_km: float
) -> float:
    """Return the stored-data gradient ``[permille]`` between two profile chainages."""
    points = _profile_points(document)
    for (low_km, low_m), (high_km, high_m) in zip(points, points[1:]):
        if abs(low_km - start_km) < COVERAGE_TOLERANCE_KM and abs(high_km - end_km) < COVERAGE_TOLERANCE_KM:
            return (high_m - low_m) / (high_km - low_km)
    raise AssertionError(f"no stored profile segment between {start_km} and {end_km} km")


def _with_changed_profile(
    points: list[tuple[float, float]],
) -> dict[str, Any]:
    """Return a copy of the frozen document whose vertical profile has *points*."""
    document = copy.deepcopy(_grr_document())
    profile = _profile(document)
    profile["points"] = [
        {"id": f"VPP-TEST-{index + 1:02d}", "chainage_km": chainage_km, "elevation_m": elevation_m}
        for index, (chainage_km, elevation_m) in enumerate(points)
    ]
    return document


def _section_tokens(heading: str) -> tuple[str, ...]:
    """Return the token list of one ``docs/SECTION_D_PATTERNS.md`` section."""
    text = _SECTION_D_PATTERNS.read_text(encoding="utf-8")
    start = text.index(heading)
    end = text.index("\n## ", start + 1)
    body = text[start:end].split("\n", 1)[1]
    paragraph = body.strip().split("\n\n", 1)[0]
    return tuple(re.findall(r"`([^`]+)`", paragraph))


# ---------------------------------------------------------------------------
# P4-031 ... P4-034 - construction and the direction rules
# ---------------------------------------------------------------------------
def test_p4_031_route_geometry_constructs_from_the_reference_corridor():
    """TEST P4-031 - RouteGeometry builds from the frozen project and an H1 route, cleanly."""
    assert _GEOMETRY_MODULE.is_file(), "the Phase-4B module must exist"
    assert _protected_file_sha256() == PROTECTED_GRR01_SHA256
    document = _grr_document()
    project = _load(document)
    network = _reference_network(project)
    assert network.diagnostics == ()
    assert network.path_ids == REFERENCE_PATH_IDS

    assert ELEVATION_UNIT == "m" and GRADIENT_UNIT == "permille" and RADIUS_UNIT == "m"
    facade = importlib.import_module("railway_headway_sim.infrastructure")
    assert facade.RouteGeometry is RouteGeometry

    for path_id in REFERENCE_PATH_IDS:
        for direction in (Direction.FORWARD, Direction.REVERSE):
            route = network.route(path_id, direction)
            geometry = RouteGeometry(project, route)
            assert geometry.diagnostics == (), (path_id, direction)
            assert isinstance(geometry, RouteGeometry)
            assert geometry.path_id == path_id
            assert geometry.direction is direction
            assert geometry.route_length_m == route.route_length_m
            assert geometry.alignment_id == ALIGNMENT_ID
            assert geometry.layer_id == _layer(document)["id"]
            # every query answered by the stored data, at both ends of the route
            for s_m in (0.0, geometry.route_length_m):
                assert isinstance(geometry.elevation_at(s_m), float)
                assert isinstance(geometry.gradient_at(s_m), float)
                assert geometry.curve_radius_at(s_m) is None or isinstance(
                    geometry.curve_radius_at(s_m), float
                )


def test_p4_032_elevation_is_the_interpolation_of_the_stored_profile():
    """TEST P4-032 - elevation_at is the stored profile's linear interpolation."""
    document = _grr_document()
    project = _load(document)
    geometry = _geometry(project)
    route = _reference_network(project).route(REFERENCE_PATH_IDS[0])
    points = _profile_points(document)
    span_low_km, span_high_km = _chainage_span_km(document, route.segments)

    # at every stored elevation point inside the corridor: exactly the stored elevation
    checked_points = 0
    for chainage_km, elevation_m in points:
        if not (span_low_km <= chainage_km <= span_high_km):
            continue
        s_m = _route_distance_of_chainage_km(document, route, chainage_km)
        assert geometry.elevation_at(s_m) == pytest.approx(elevation_m, abs=1e-9)
        checked_points += 1
    assert checked_points >= 8, "the corridor must cross most of the stored profile points"

    # between two stored points: the linear interpolation of those two points
    checked_between = 0
    for (low_km, low_m), (high_km, high_m) in zip(points, points[1:]):
        chainage_km = 0.5 * (low_km + high_km)
        if not (span_low_km <= chainage_km <= span_high_km):
            continue
        expected_m = low_m + (chainage_km - low_km) / (high_km - low_km) * (high_m - low_m)
        s_m = _route_distance_of_chainage_km(document, route, chainage_km)
        assert geometry.elevation_at(s_m) == pytest.approx(expected_m, abs=1e-9)
        checked_between += 1
    assert checked_between >= 8

    # inside one segment the elevation is strictly monotone in the profile's own sense
    flat = _with_changed_profile([(0.0, 100.0), (50.0, 120.0)])
    flat_project = _load(flat)
    flat_geometry = _geometry(flat_project)
    flat_route = _reference_network(flat_project).route(REFERENCE_PATH_IDS[0])
    for fraction in (0.1, 0.5, 0.9):
        chainage_km = fraction * 50.0
        s_m = _route_distance_of_chainage_km(flat, flat_route, chainage_km)
        assert flat_geometry.elevation_at(s_m) == pytest.approx(100.0 + 0.4 * chainage_km, abs=1e-9)


def test_p4_033_elevation_is_direction_independent():
    """TEST P4-033 - the same physical location returns the same elevation both ways."""
    document = _grr_document()
    project = _load(document)
    network = _reference_network(project)
    forward = RouteGeometry(project, network.route(REFERENCE_PATH_IDS[0], Direction.FORWARD))
    reverse = RouteGeometry(project, network.route(REFERENCE_PATH_IDS[0], Direction.REVERSE))
    length_m = forward.route_length_m
    assert reverse.route_length_m == length_m

    samples = [0.0, 0.25 * length_m, 0.5 * length_m, 0.75 * length_m, length_m]
    samples += [
        _route_distance_of_chainage_km(document, network.route(REFERENCE_PATH_IDS[0]), chainage_km)
        for chainage_km, _elevation_m in _profile_points(document)
        if 1.6 <= chainage_km <= 49.0
    ]
    for s_forward_m in samples:
        s_reverse_m = length_m - s_forward_m
        assert forward.elevation_at(s_forward_m) == pytest.approx(
            reverse.elevation_at(s_reverse_m), abs=1e-9
        )


def test_p4_034_gradient_is_direction_aware():
    """TEST P4-034 - the same physical location returns opposite-signed gradients."""
    document = _grr_document()
    project = _load(document)
    network = _reference_network(project)
    route = network.route(REFERENCE_PATH_IDS[0])
    forward = RouteGeometry(project, network.route(REFERENCE_PATH_IDS[0], Direction.FORWARD))
    reverse = RouteGeometry(project, network.route(REFERENCE_PATH_IDS[0], Direction.REVERSE))
    length_m = forward.route_length_m

    non_zero = 0
    for fraction in (0.05, 0.2, 0.4, 0.6, 0.8, 0.95):
        s_forward_m = fraction * length_m
        s_reverse_m = length_m - s_forward_m
        forward_gradient = forward.gradient_at(s_forward_m)
        reverse_gradient = reverse.gradient_at(s_reverse_m)
        assert forward_gradient == pytest.approx(-reverse_gradient, abs=1e-12)
        if abs(forward_gradient) > 0.0:
            non_zero += 1
    assert non_zero >= 5, "the corridor must cross non-flat gradient segments"

    # inside one stored segment the pair is exactly opposite, not merely close
    for chainage_km, _elevation_m in _profile_points(document)[1:-1]:
        s_forward_m = _route_distance_of_chainage_km(document, route, chainage_km + 0.5)
        s_reverse_m = _route_distance_of_chainage_km(
            document, network.route(REFERENCE_PATH_IDS[0], Direction.REVERSE), chainage_km + 0.5
        )
        assert forward.gradient_at(s_forward_m) == -reverse.gradient_at(s_reverse_m)

    # REVERSE of the same corridor reports the mirror of its own chainage direction
    reverse_route = network.route(REFERENCE_PATH_IDS[0], Direction.REVERSE)
    assert _chainage_span_km(document, reverse_route.segments)[0] < _chainage_span_km(
        document, reverse_route.segments
    )[1]


# ---------------------------------------------------------------------------
# P4-035 ... P4-039 - the piecewise-constant gradient and the radius
# ---------------------------------------------------------------------------
def test_p4_035_gradient_is_piecewise_constant_between_stored_points():
    """TEST P4-035 - the gradient uses its stored segment and is not interpolated."""
    document = _grr_document()
    project = _load(document)
    network = _reference_network(project)
    route = network.route(REFERENCE_PATH_IDS[0])
    geometry = RouteGeometry(project, route)
    points = _profile_points(document)
    span_low_km, span_high_km = _chainage_span_km(document, route.segments)

    checked = 0
    for (low_km, low_m), (high_km, high_m) in zip(points, points[1:]):
        stored = (high_m - low_m) / (high_km - low_km)
        assert stored == pytest.approx(
            _stored_gradient_between(document, low_km, high_km), abs=1e-12
        )
        if not (span_low_km < low_km and high_km < span_high_km):
            continue
        values = []
        for fraction in (0.25, 0.5, 0.75):
            chainage_km = low_km + fraction * (high_km - low_km)
            s_m = _route_distance_of_chainage_km(document, route, chainage_km)
            value = geometry.gradient_at(s_m)
            assert value == pytest.approx(stored, abs=1e-12), (low_km, high_km, fraction)
            values.append(value)
        assert values[0] == values[1] == values[2], "no interpolation inside a segment"
        checked += 1
    assert checked >= 8, "the corridor must cross most of the stored profile segments"

    # two adjacent segments must report two different stored gradients
    distinct = {
        _stored_gradient_between(document, low_km, high_km)
        for (low_km, _a), (high_km, _b) in zip(points, points[1:])
        if span_low_km < low_km and high_km < span_high_km
    }
    assert len(distinct) > 1


def test_p4_036_gradient_is_zero_where_two_points_share_an_elevation():
    """TEST P4-036 - a flat stored segment yields exactly 0.0 per mille."""
    flat_points = [(0.0, 120.0), (2.5, 120.5), (6.0, 120.5), (10.0, 128.5), (50.0, 124.5)]
    document = _with_changed_profile(flat_points)
    project = _load(document)
    route = _reference_network(project).route(REFERENCE_PATH_IDS[0])
    geometry = RouteGeometry(project, route)
    assert geometry.diagnostics == ()
    assert _stored_gradient_between(document, 2.5, 6.0) == 0.0

    for chainage_km in (2.6, 4.0, 5.9):
        s_m = _route_distance_of_chainage_km(document, route, chainage_km)
        assert geometry.gradient_at(s_m) == 0.0
        assert geometry.elevation_at(s_m) == pytest.approx(120.5, abs=1e-9)

    # the neighbouring segments keep their own stored gradients
    for chainage_km, expected in ((2.0, 0.2), (4.0, 0.0), (8.0, 2.0)):
        s_m = _route_distance_of_chainage_km(document, route, chainage_km)
        assert geometry.gradient_at(s_m) == pytest.approx(expected, abs=1e-12)

    # the frozen file on disk is untouched by this synthetic case
    assert _protected_file_sha256() == PROTECTED_GRR01_SHA256


def test_p4_037_curve_radius_returns_the_stored_radius_on_curves():
    """TEST P4-037 - the stored radius is returned wherever a CURVE section covers."""
    document = _grr_document()
    project = _load(document)
    route = _reference_network(project).route(REFERENCE_PATH_IDS[0])
    geometry = RouteGeometry(project, route)
    curves = [section for section in _sections(document) if section["type"] == "CURVE"]
    assert len(curves) == 3, [section["id"] for section in curves]

    checked: list[tuple[str, float]] = []
    for section in curves:
        midpoint_km = 0.5 * (section["start_chainage_km"] + section["end_chainage_km"])
        s_m = _route_distance_of_chainage_km(document, route, midpoint_km)
        radius = geometry.curve_radius_at(s_m)
        assert radius == pytest.approx(float(section["radius_m"]), abs=1e-12), section["id"]
        checked.append((section["id"], radius))
    # the frozen project's own stored radii (evidence, not an expectation to match)
    assert [radius for _section_id, radius in checked] == [1800.0, 1200.0, 2000.0]
    assert [section["id"] for section in curves] == ["HGR-02", "HGR-04", "HGR-06"]


def test_p4_038_curve_radius_is_none_on_straights_never_a_sentinel():
    """TEST P4-038 - a STRAIGHT section returns None, never a sentinel float."""
    document = _grr_document()
    project = _load(document)
    route = _reference_network(project).route(REFERENCE_PATH_IDS[0])
    geometry = RouteGeometry(project, route)
    straights = [section for section in _sections(document) if section["type"] == "STRAIGHT"]
    assert len(straights) == 4

    for section in straights:
        low_km = max(section["start_chainage_km"], 1.6)
        high_km = min(section["end_chainage_km"], 49.0)
        if low_km >= high_km:
            continue
        chainage_km = 0.5 * (low_km + high_km)
        s_m = _route_distance_of_chainage_km(document, route, chainage_km)
        radius = geometry.curve_radius_at(s_m)
        assert radius is None, section["id"]
        assert not isinstance(radius, (int, float)), "no numeric sentinel may be returned"

    # the corridor begins and ends on straight sections
    assert geometry.curve_radius_at(0.0) is None
    assert geometry.curve_radius_at(geometry.route_length_m) is None


def test_p4_039_curve_radius_is_direction_independent():
    """TEST P4-039 - the radius is a magnitude: both directions return the same value."""
    document = _grr_document()
    project = _load(document)
    network = _reference_network(project)
    route = network.route(REFERENCE_PATH_IDS[0])
    forward = RouteGeometry(project, network.route(REFERENCE_PATH_IDS[0], Direction.FORWARD))
    reverse = RouteGeometry(project, network.route(REFERENCE_PATH_IDS[0], Direction.REVERSE))
    length_m = forward.route_length_m

    curve_positions = 0
    straight_positions = 0
    for section in _sections(document):
        low_km = max(section["start_chainage_km"], 1.6)
        high_km = min(section["end_chainage_km"], 49.0)
        if low_km >= high_km:
            continue
        chainage_km = 0.5 * (low_km + high_km)
        s_forward_m = _route_distance_of_chainage_km(document, route, chainage_km)
        s_reverse_m = length_m - s_forward_m
        assert forward.curve_radius_at(s_forward_m) == reverse.curve_radius_at(s_reverse_m)
        if section["type"] == "CURVE":
            curve_positions += 1
        else:
            straight_positions += 1
    assert curve_positions == 3 and straight_positions >= 2


# ---------------------------------------------------------------------------
# P4-040 ... P4-043 - the footprint gradient, errors and ranges
# ---------------------------------------------------------------------------
def test_p4_040_footprint_gradient_is_exact_inside_one_segment():
    """TEST P4-040 - a footprint inside one segment returns gradient_at exactly."""
    document = _grr_document()
    project = _load(document)
    route = _reference_network(project).route(REFERENCE_PATH_IDS[0])
    geometry = RouteGeometry(project, route)
    points = _profile_points(document)

    span_low_km, span_high_km = _chainage_span_km(document, route.segments)
    checked = 0
    for (low_km, _low_m), (high_km, _high_m) in zip(points, points[1:]):
        chainage_km = 0.5 * (low_km + high_km)
        segment_km = high_km - low_km
        if segment_km < 0.2 or not (span_low_km < chainage_km < span_high_km):
            continue
        s_m = _route_distance_of_chainage_km(document, route, chainage_km)
        # a footprint of 100 m stays far inside any of these segments
        assert geometry.footprint_gradient(s_m, 100.0) == geometry.gradient_at(s_m)
        assert geometry.footprint_gradient(s_m, 1000.0) == geometry.gradient_at(s_m)
        checked += 1
    assert checked >= 8

    # the footprint average travels with the direction of travel
    network = _reference_network(project)
    reverse = RouteGeometry(project, network.route(REFERENCE_PATH_IDS[0], Direction.REVERSE))
    length_m = geometry.route_length_m
    for fraction in (0.2, 0.5, 0.8):
        s_forward_m = fraction * length_m
        s_reverse_front_m = length_m - s_forward_m + 500.0
        assert geometry.footprint_gradient(s_forward_m, 500.0) == pytest.approx(
            -reverse.footprint_gradient(s_reverse_front_m, 500.0), abs=1e-12
        )


def test_p4_041_footprint_gradient_averages_across_a_transition():
    """TEST P4-041 - a straddling footprint returns the length-weighted mean."""
    document = _with_changed_profile([(0.0, 100.0), (20.0, 110.0), (50.0, 140.0)])
    project = _load(document)
    route = _reference_network(project).route(REFERENCE_PATH_IDS[0])
    geometry = RouteGeometry(project, route)
    assert geometry.diagnostics == ()
    first_gradient = _stored_gradient_between(document, 0.0, 20.0)
    second_gradient = _stored_gradient_between(document, 20.0, 50.0)
    assert first_gradient == pytest.approx(0.5, abs=1e-12)
    assert second_gradient == pytest.approx(1.0, abs=1e-12)

    # a footprint of 4 000 m with its front at chainage 22.0 km: 2 000 m + 2 000 m
    front_km = 22.0
    train_length_m = 4000.0
    s_front_m = _route_distance_of_chainage_km(document, route, front_km)
    expected = (2000.0 * first_gradient + 2000.0 * second_gradient) / train_length_m
    assert geometry.footprint_gradient(s_front_m, train_length_m) == pytest.approx(
        expected, abs=1e-12
    )
    assert geometry.footprint_gradient(s_front_m, train_length_m) == pytest.approx(0.75, abs=1e-12)

    # wholly inside one segment it is that segment's gradient, both sides of the break
    s_inside_first_m = _route_distance_of_chainage_km(document, route, 10.0)
    s_inside_second_m = _route_distance_of_chainage_km(document, route, 30.0)
    assert geometry.footprint_gradient(s_inside_first_m, train_length_m) == pytest.approx(
        first_gradient, abs=1e-12
    )
    assert geometry.footprint_gradient(s_inside_second_m, train_length_m) == pytest.approx(
        second_gradient, abs=1e-12
    )

    # a footprint that only just crosses the boundary is still the weighted mean:
    # the front at chainage 20.5 km spans [16.5, 20.5] km -> 3 500 m + 500 m
    s_just_after_m = _route_distance_of_chainage_km(document, route, 20.5)
    expected_just = (3500.0 * first_gradient + 500.0 * second_gradient) / train_length_m
    assert geometry.footprint_gradient(s_just_after_m, train_length_m) == pytest.approx(
        expected_just, abs=1e-12
    )
    assert geometry.footprint_gradient(s_just_after_m, train_length_m) == pytest.approx(
        0.5625, abs=1e-12
    )


def test_p4_042_footprint_gradient_refuses_a_non_positive_train_length():
    """TEST P4-042 - a non-positive train length raises ValueError."""
    project = _load(_grr_document())
    geometry = _geometry(project)
    s_m = 0.5 * geometry.route_length_m
    for bad_length in (0.0, -1.0, -250.0, -1e-9):
        with pytest.raises(ValueError) as error:
            geometry.footprint_gradient(s_m, bad_length)
        assert "train_length_m" in str(error.value)
    assert geometry.footprint_gradient(s_m, 1e-3) == geometry.gradient_at(s_m)


def test_p4_043_out_of_range_queries_raise_and_never_clamp():
    """TEST P4-043 - a route distance outside [0, L] raises RouteCoordinateError."""
    project = _load(_grr_document())
    geometry = _geometry(project)
    length_m = geometry.route_length_m
    for s_m in (-1.0, -0.001, length_m + 0.001, length_m + 1.0, length_m + 1000.0):
        for query in (geometry.elevation_at, geometry.gradient_at, geometry.curve_radius_at):
            with pytest.raises(RouteCoordinateError):
                query(s_m)
    # the footprint is never clamped into the route either
    with pytest.raises(RouteCoordinateError):
        geometry.footprint_gradient(length_m + 1.0, 100.0)
    with pytest.raises(RouteCoordinateError):
        geometry.footprint_gradient(50.0, 100.0)
    # a footprint that would start before the route origin is refused, not clamped
    with pytest.raises(RouteCoordinateError) as error:
        geometry.footprint_gradient(0.0, 100.0)
    assert "route origin" in str(error.value)

    # the legal route distances are answered, not refused
    for s_m in (0.0, length_m):
        assert isinstance(geometry.elevation_at(s_m), float)
        assert isinstance(geometry.gradient_at(s_m), float)
    assert geometry.footprint_gradient(length_m, 100.0) == pytest.approx(
        geometry.gradient_at(length_m), abs=1e-9
    )


# ---------------------------------------------------------------------------
# P4-044 ... P4-047 - reported incompleteness, read-only, and the scope scans
# ---------------------------------------------------------------------------
def test_p4_044_missing_catalogues_are_reported_and_refuse_to_answer():
    """TEST P4-044 - a project without a catalogue reports and raises, never invents."""
    from railway_headway_sim.validation import codes

    assert codes.VAL_GEOM_004 == "VAL-GEOM-004"
    assert codes.VAL_GEOM_006 == "VAL-GEOM-006"

    without_profile = copy.deepcopy(_grr_document())
    _layer(without_profile)["vertical_profiles"] = []
    project = _load(without_profile)
    geometry = _geometry(project)
    assert [diagnostic.code for diagnostic in geometry.diagnostics] == [codes.VAL_GEOM_006]
    assert geometry.diagnostics[0].severity is Severity.ERROR
    s_m = 0.5 * geometry.route_length_m
    with pytest.raises(RouteCoordinateError):
        geometry.elevation_at(s_m)
    with pytest.raises(RouteCoordinateError):
        geometry.gradient_at(s_m)
    # the catalogue that is present still answers: the report is per catalogue
    assert geometry.curve_radius_at(
        _route_distance_of_chainage_km(
            without_profile,
            _reference_network(project).route(REFERENCE_PATH_IDS[0]),
            10.0,
        )
    ) == pytest.approx(1800.0, abs=1e-12)

    without_geometry = copy.deepcopy(_grr_document())
    _layer(without_geometry)["horizontal_geometry"] = []
    project = _load(without_geometry)
    geometry = _geometry(project)
    assert [diagnostic.code for diagnostic in geometry.diagnostics] == [codes.VAL_GEOM_004]
    with pytest.raises(RouteCoordinateError):
        geometry.curve_radius_at(s_m)
    assert isinstance(geometry.elevation_at(s_m), float)
    assert isinstance(geometry.gradient_at(s_m), float)

    # a profile that does not cover the route is reported as well (F7), and queries
    # beyond its coverage raise instead of being extrapolated
    short_profile = _with_changed_profile([(0.0, 100.0), (20.0, 110.0)])
    project = _load(short_profile)
    geometry = _geometry(project)
    assert [diagnostic.code for diagnostic in geometry.diagnostics] == [codes.VAL_GEOM_006]
    assert isinstance(geometry.elevation_at(0.0), float)
    with pytest.raises(RouteCoordinateError):
        geometry.elevation_at(geometry.route_length_m)


def test_p4_045_route_geometry_does_not_mutate_the_project():
    """TEST P4-045 - the project and the companion file are unchanged by reading."""
    assert _protected_file_sha256() == PROTECTED_GRR01_SHA256
    assert _companion_sha256() == COMPANION_SHA256
    document = _grr_document()
    project = _load(document)
    before_hash = document_hash(to_normalized_dict(project))
    before_layer = json.dumps(_layer(document), sort_keys=True)
    network = _reference_network(project)
    for path_id in REFERENCE_PATH_IDS:
        for direction in (Direction.FORWARD, Direction.REVERSE):
            geometry = RouteGeometry(project, network.route(path_id, direction))
            for s_m in (0.0, 0.25 * geometry.route_length_m, geometry.route_length_m):
                geometry.elevation_at(s_m)
                geometry.gradient_at(s_m)
                geometry.curve_radius_at(s_m)
            geometry.footprint_gradient(0.5 * geometry.route_length_m, 1000.0)
    assert before_hash == CANONICAL_GRR01_HASH
    assert document_hash(to_normalized_dict(project)) == CANONICAL_GRR01_HASH
    assert json.dumps(_layer(document), sort_keys=True) == before_layer
    assert _protected_file_sha256() == PROTECTED_GRR01_SHA256
    assert _companion_sha256() == COMPANION_SHA256

    # the frozen document on disk still declares no train path of its own
    assert _grr_document()["train_paths"]["paths"] == []


def test_p4_046_geometry_module_has_no_numeric_dependency():
    """TEST P4-046 - the Phase-4B module imports only the standard library and the package."""
    assert _GEOMETRY_MODULE.is_file()
    tree = ast.parse(_GEOMETRY_MODULE.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            imported.add("." * node.level + (node.module or ""))
        elif isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
    assert imported == {
        "__future__",
        "typing",
        "..models.diagnostics",
        "..models.enums",
        "..validation",
        ".compiled_network",
        ".preview_series",
    }, f"unexpected import surface: {sorted(imported)}"
    assert not {
        "math",
        "numpy",
        "scipy",
        "pandas",
        "statistics",
        "random",
        "decimal",
        "fractions",
    } & imported
    assert not {".project_io", "..io", "..app", "..ui"} & imported, "layer direction"

    # the module imports cleanly on its own, and the package facade exposes it
    module = importlib.import_module("railway_headway_sim.infrastructure.geometry_along_route")
    assert module.RouteGeometry is RouteGeometry
    facade = importlib.import_module("railway_headway_sim.infrastructure")
    assert "RouteGeometry" in facade.__all__
    # no module of the package constructs a curve radius or an elevation by itself
    package_root = _REPO_ROOT / "railway_headway_sim"
    importers = [
        path.relative_to(_REPO_ROOT).as_posix()
        for path in sorted(package_root.rglob("*.py"))
        if "geometry_along_route" in path.read_text(encoding="utf-8")
        and path.name != "geometry_along_route.py"
    ]
    assert sorted(importers) == sorted(
        [
            "railway_headway_sim/infrastructure/__init__.py",
            "railway_headway_sim/tests/test_phase4b_geometry_along_route.py",
        ]
    ), importers


def test_p4_047_geometry_module_stays_outside_the_out_of_scope_patterns():
    """TEST P4-047 - the Phase-4B module carries no Section-D token."""
    assert _GEOMETRY_MODULE.is_file()
    module = importlib.import_module("railway_headway_sim.infrastructure.geometry_along_route")
    s1_tokens = _section_tokens("## 2. S1")
    s3_tokens = _section_tokens("## 4. S3")
    assert len(s1_tokens) == 9 and len(s3_tokens) == 7, (s1_tokens, s3_tokens)
    # Phase 5A moved "davis" and "roeckl" to the allowed list (docs/SECTION_D_PATTERNS.md
    # §2.1): assert the allowed list explicitly rather than rely on "no longer fails".
    allowed_tokens = _section_tokens("## 2.1")
    assert allowed_tokens == (
        "Davis",
        "Roeckl",
        "rolling resistance",
        "curve resistance",
        "gradient force",
    ), allowed_tokens
    assert not (set(token.lower() for token in allowed_tokens) & set(s1_tokens))

    tree = ast.parse(_GEOMETRY_MODULE.read_text(encoding="utf-8"))
    declared_names = [
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
        or isinstance(node, ast.AsyncFunctionDef)
        or isinstance(node, ast.ClassDef)
    ]
    assert declared_names, "the scan must look at a populated module"
    offending_names = sorted(
        {name for name in declared_names for token in s1_tokens if token in name.lower()}
    )
    assert offending_names == [], f"S1 names present: {offending_names}"

    public_names = [name for name in dir(module) if not name.startswith("_")]
    offending_public = sorted(
        {name for name in public_names for token in s1_tokens + s3_tokens if token in name.lower()}
    )
    assert offending_public == [], f"forbidden public names present: {offending_public}"

    interface_names = [name for name in dir(RouteGeometry) if not name.startswith("_")]
    if dataclasses.is_dataclass(RouteGeometry):
        interface_names.extend(field.name for field in dataclasses.fields(RouteGeometry))
    offending_interface = sorted(
        {name for name in interface_names for token in s1_tokens + s3_tokens if token in name.lower()}
    )
    assert offending_interface == [], f"forbidden interface names: {offending_interface}"

    docstring = module.__doc__ or ""
    assert "Phase 4B" in docstring
    assert "no force, no speed, no time" in docstring, "the module states its own scope"


# ---------------------------------------------------------------------------
# P4-048 - the suite registration
# ---------------------------------------------------------------------------
def test_p4_048_phase4b_suite_is_registered_and_counted():
    """TEST P4-048 - the Phase-4B table is registered; the earlier tables are unchanged."""
    source = Path(__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    acceptance_ids: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_p4_"):
            if isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant):
                text = str(node.body[0].value.value)
                match = re.search(r"\bP4-\d{3}\b", text)
                assert match, node.name
                acceptance_ids.append(match.group(0))
    assert sorted(acceptance_ids) == [f"P4-{number:03d}" for number in range(31, 49)]
    assert len(acceptance_ids) == 18

    conftest_text = _CONFTEST.read_text(encoding="utf-8")
    assert "PHASE-4B TESTS (TEST P4-031 ... TEST P4-048)" in conftest_text
    for earlier in (
        "PHASE-1 ACCEPTANCE TESTS (TEST P1-001 ... TEST P1-012)",
        "PHASE-2 TESTS (TEST P2-001 ... TEST P2-028)",
        "GRR-01 REGISTRY REGRESSIONS (TEST P2-REG-G001 ... TEST P2-REG-G005)",
        "PHASE-3 TESTS (TEST P3-001 ... TEST P3-026)",
        "PHASE-4A TESTS (TEST P4-001 ... TEST P4-030)",
    ):
        assert earlier in conftest_text, earlier
    assert "test_phase4b_geometry_along_route" not in conftest_text.split("PHASE-4B")[0], (
        "the earlier tables must not list the Phase-4B module"
    )

    builder_text = _INVENTORY_BUILDER.read_text(encoding="utf-8")
    assert '"phase4b"' in builder_text
    assert "test_phase4b_geometry_along_route.py" in builder_text
    assert "Phase-4B suite (TEST P4-031 … TEST P4-048)" in builder_text
    assert 'totals["phase4b"]' in builder_text

    # the Phase-4A module still declares its own range, unchanged
    phase4a_source = (
        _REPO_ROOT / "railway_headway_sim" / "tests" / "test_phase4a_route_coordinate.py"
    ).read_text(encoding="utf-8")
    assert "TEST P4-001 ... TEST P4-030." in phase4a_source
    assert "# P4-023 ... P4-030 - the declared-paths companion file" in phase4a_source
