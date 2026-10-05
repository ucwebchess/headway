"""Phase-5B acceptance tests: resistance and force along a compiled route.

TEST P5-025 ... TEST P5-042.

Scope of this module (master specification, Stage 5B):

* the delivered Phase-4B geometry module gains **one additive method**,
  ``RouteGeometry.curve_radius_segments_in(s_start_m, s_end_m)``: the ordered
  sub-intervals of a route-distance interval on which the stored curve radius is constant,
  each reported as ``(length_m, radius_m_or_None)`` - purely geometric, no resistance
  model applied to the radii (TEST P5-027, TEST P5-028);
* ``railway_headway_sim/physics/along_route.py`` is new and exposes four read-only
  functions that evaluate the Stage-5A utilities along a compiled route:
  ``davis_resistance_at_n`` (position-independent), ``gradient_force_at_n`` (signed, over
  a train footprint), ``curve_resistance_at_n`` (length-weighted over the same footprint)
  and ``total_resistance_at_n`` (their literal sum) - all in newtons, all pure
  (TEST P5-025, TEST P5-026, TEST P5-029 ... TEST P5-037);
* the frozen sign convention of Stage 5A is preserved: the running-resistance term and the
  curvature term are non-negative magnitudes, the grade term is the one signed quantity,
  and the total is their literal sum; at the same physical train body the grade term is
  opposite-signed between the two directions of travel while the curvature term is equal
  (TEST P5-031, TEST P5-035);
* errors are propagated, never repaired: a non-positive train length and a footprint
  outside the route raise the geometry's own errors and no placeholder value is returned
  (TEST P5-028, TEST P5-039);
* the new module imports no numeric library and carries no Section-D token outside the
  allowed ones, and the five Stage-5A tokens stay confined to the ``physics`` package
  (TEST P5-041, TEST P5-042).

Every expected value is recomputed inside the test from the frozen project's own stored
catalogues and from the Stage-5A functions (never hand-typed as a constant the data must
match), and no test writes to any protected artefact.
"""

from __future__ import annotations

import ast
import copy
import hashlib
import importlib
import inspect
import json
import re
import sys
from pathlib import Path
from typing import Any

import pytest

from railway_headway_sim.infrastructure import RouteGeometry
from railway_headway_sim.infrastructure.compiled_network import (
    RouteCoordinateError,
    compile_network,
)
from railway_headway_sim.infrastructure.mapping import edge_position_to_chainage
from railway_headway_sim.io.project_io import (
    document_hash,
    import_project_from_data,
    to_normalized_dict,
)
from railway_headway_sim.models.enums import Direction, EdgeTraversal
from railway_headway_sim.models.infrastructure import Track
from railway_headway_sim.physics import (
    along_route as along_route_module,
)
from railway_headway_sim.physics import resistance as resistance_module

_REPO_ROOT = Path(__file__).resolve().parents[2]
_PACKAGE_DIR = _REPO_ROOT / "railway_headway_sim"
_PHYSICS_DIR = _PACKAGE_DIR / "physics"
_MODULE_PATH = _PHYSICS_DIR / "along_route.py"
_PROTECTED_GRR01 = _REPO_ROOT / "examples" / "GRR-01.json"
_COMPANION = _REPO_ROOT / "examples" / "GRR-01-paths.json"
_SECTION_D_PATTERNS = _REPO_ROOT / "docs" / "SECTION_D_PATTERNS.md"
_CONFTEST = _PACKAGE_DIR / "tests" / "conftest.py"
_INVENTORY_BUILDER = _REPO_ROOT / "build_test_inventory.py"
_INVENTORY = _REPO_ROOT / "docs" / "TEST_INVENTORY.md"

#: sha256 of the protected reference project file (must not change; checked here).
PROTECTED_GRR01_SHA256 = "ad0a26265d4e072aeedcc69161bef90f200c20b4efb12a4d56a5276c4a4f7a56"

#: sha256 of the declared-paths companion file (must not change in Phase 5B).
COMPANION_SHA256 = "c62c3ee6d910457a6f59533c2b92b4e65a0cd8c64dff49fe8e6796ed829fac86"

#: Canonical document hash of the reference project (must not change).
CANONICAL_GRR01_HASH = "5189aaa2340c17022666ef44772c7d34f99b2fea9ee9609bb7b7513238ef4dbe"

#: The frozen HSR dataset of the specification: mass [kg], train length [m] and the Davis
#: coefficients A [kN], B [kN / (km/h)], C [kN / (km/h)**2].
HSR_MASS_KG = 485000.0
HSR_TRAIN_LENGTH_M = 202.0
HSR_SPEED_KMH = 320.0
HSR_DAVIS_A = 2.506
HSR_DAVIS_B = 0.04065
HSR_DAVIS_C = 0.00043

#: The alignment and the declared path the H1 corridor reads.
ALIGNMENT_ID = "ALN-MAIN"
PATH_ID = "PATH-H1-F"

#: The chainages of the Phase-4B §15 sample set — the same physical locations, for
#: comparability (the first one sits exactly on the route origin, where a train body of
#: 202.0 m reaches 202.0 m outside the route and is therefore reported, not clamped).
SAMPLE_CHAINAGES_KM: tuple[float, ...] = (
    1.600,
    8.710,
    15.820,
    25.300,
    34.780,
    41.890,
    49.000,
)

#: The four public functions of the Stage-5B module, with their declared parameter names.
EXPECTED_SIGNATURES: dict[str, tuple[str, ...]] = {
    "davis_resistance_at_n": ("speed_kmh", "davis_a", "davis_b", "davis_c"),
    "gradient_force_at_n": ("geometry", "mass_kg", "s_m", "train_length_m"),
    "curve_resistance_at_n": ("geometry", "mass_kg", "s_m", "train_length_m"),
    "total_resistance_at_n": (
        "geometry",
        "mass_kg",
        "train_length_m",
        "s_m",
        "speed_kmh",
        "davis_a",
        "davis_b",
        "davis_c",
    ),
}

#: The unit token every parameter must document (the geometry is a read-only object).
UNIT_TOKEN_IN_DOCSTRING: dict[str, str] = {
    "speed_kmh": "km/h",
    "davis_a": "kN",
    "davis_b": "kN / (km/h)",
    "davis_c": "kN / (km/h)**2",
    "mass_kg": "kg",
    "s_m": "m",
    "train_length_m": "m",
    "geometry": "read-only",
}

#: Probe (metres) used when an exact stored boundary is sampled just inside.
_EPS_M = 1e-6


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _module() -> Any:
    """Return the imported Stage-5B module."""
    return importlib.import_module("railway_headway_sim.physics.along_route")


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


def _tracks(document: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Return the layer's tracks keyed by id."""
    return {track["id"]: track for track in _layer(document)["tracks"]}


def _profile_points(document: dict[str, Any]) -> tuple[tuple[float, float], ...]:
    """Return the stored ``(chainage_km, elevation_m)`` points of the alignment, sorted."""
    profile = next(
        item
        for item in _layer(document)["vertical_profiles"]
        if item["alignment_id"] == ALIGNMENT_ID
    )
    return tuple(
        sorted(
            (float(point["chainage_km"]), float(point["elevation_m"]))
            for point in profile["points"]
        )
    )


def _horizontal_sections(document: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    """Return the stored horizontal-geometry sections of the alignment, sorted by start."""
    return tuple(
        sorted(
            (
                section
                for section in _layer(document)["horizontal_geometry"]
                if section["alignment_id"] == ALIGNMENT_ID
            ),
            key=lambda section: float(section["start_chainage_km"]),
        )
    )


def _stored_radii(document: dict[str, Any]) -> set[float]:
    """Return the set of stored radii of the alignment's CURVE sections."""
    return {
        float(section["radius_m"])
        for section in _horizontal_sections(document)
        if section["type"] == "CURVE"
    }


def _network(project: Any) -> Any:
    """Compile a project with the declared-paths companion file of the H1 corridor."""
    return compile_network(project, paths_source=_COMPANION.read_text(encoding="utf-8"))


def _direction_of(path_id: str) -> Direction:
    """Return the direction that PATH-H1-F / PATH-H1-R are declared in."""
    return Direction.FORWARD if path_id.endswith("F") else Direction.REVERSE


def _route(project: Any, path_id: str = PATH_ID, direction: Direction = Direction.FORWARD) -> Any:
    """Return one compiled route coordinate system of the H1 corridor."""
    return _network(project).route(path_id, direction)


def _geometry(
    project: Any, path_id: str = PATH_ID, direction: Direction = Direction.FORWARD
) -> RouteGeometry:
    """Return the route geometry of one declared path and direction."""
    network = _network(project)
    assert network.diagnostics == ()
    return RouteGeometry(project, network.route(path_id, direction))


def _s_of_chainage_km(document: dict[str, Any], route: Any, chainage_km: float) -> float:
    """Return the route distance ``[m]`` of a physical chainage on a compiled route.

    The route's own tracks are read through the Phase-2 mapping, so the value is derived
    from the project's data and the compiled traversals — nothing is hand-typed.
    """
    tracks = _tracks(document)
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
        if -1e-6 <= fraction <= 1.0 + 1e-6:
            offset_m = fraction * (segment.end_s_m - segment.start_s_m)
            if -1e-3 <= offset_m <= (segment.end_s_m - segment.start_s_m) + 1e-3:
                return segment.start_s_m + min(
                    max(offset_m, 0.0), segment.end_s_m - segment.start_s_m
                )
    raise AssertionError(f"chainage {chainage_km} km is not on route {route.path_id!r}")


def _route_chainage_span_km(document: dict[str, Any], route: Any) -> tuple[float, float]:
    """Return the chainage span ``(min_km, max_km)`` a compiled route covers.

    The span is derived from the project's own tracks and the compiled traversals through
    the Phase-2 position/chainage mapping — nothing is hand-typed.
    """
    tracks = _tracks(document)
    chainages: list[float] = []
    for segment in route.segments:
        track = Track.model_validate(tracks[segment.edge_id])
        if segment.traversal is EdgeTraversal.WITH_EDGE:
            low_m, high_m = 0.0, float(track.length_m)
        else:
            low_m, high_m = float(track.length_m), 0.0
        chainages.append(edge_position_to_chainage(track, low_m))
        chainages.append(edge_position_to_chainage(track, high_m))
    return min(chainages), max(chainages)


def _same_body_reverse_s_m(route_length_m: float, s_forward_m: float, train_length_m: float) -> float:
    """Return the reverse route distance whose train body covers the forward one.

    The frozen footprint convention (``[front_s - train_length_m, front_s]`` in route
    distance, and route distance increasing in the direction of travel) means that the
    *same physical train body* seen from the other direction has its front ``train_length_m``
    further along the reverse route — the mapping already used by the delivered
    footprint test P4-040: ``s_reverse = L - s_forward + train_length_m``.
    """
    return route_length_m - s_forward_m + train_length_m


def _with_changed_profile(points: list[tuple[float, float]]) -> dict[str, Any]:
    """Return a copy of the frozen document whose vertical profile has *points*."""
    document = copy.deepcopy(_grr_document())
    profile = next(
        item
        for item in _layer(document)["vertical_profiles"]
        if item["alignment_id"] == ALIGNMENT_ID
    )
    profile["points"] = [
        {
            "id": f"VPP-TEST-{index + 1:02d}",
            "chainage_km": chainage_km,
            "elevation_m": elevation_m,
        }
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


def _declared_names(path: Path) -> list[str]:
    """Return every declared function / async function / class name of one module file."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return [
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    ]


def _prose_of(path: Path) -> str:
    """Return the docstrings and the ``#`` comments of one module file, as plain text."""
    source = path.read_text(encoding="utf-8")
    docstrings: list[str] = []
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(
            node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
        ):
            docstring = ast.get_docstring(node, clean=False)
            if docstring:
                docstrings.append(docstring)
    comments = [
        line.split("#", 1)[1] for line in source.splitlines() if "#" in line
    ]
    return "\n".join(docstrings + comments)


def _import_edges(path: Path) -> set[str]:
    """Return the import surface of one module file, in the P4-046 notation."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            imported.add("." * node.level + (node.module or ""))
        elif isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
    return imported


# ---------------------------------------------------------------------------
# P5-025 - the module, its API and its acceptance table
# ---------------------------------------------------------------------------
def test_p5_025_module_exposes_the_documented_api_and_is_registered():
    """TEST P5-025 - the module exists, exposes the four functions, and the table is registered."""
    assert _MODULE_PATH.is_file(), "railway_headway_sim/physics/along_route.py must exist"
    module = _module()
    package = importlib.import_module("railway_headway_sim.physics")
    assert "Phase-5B" in (module.__doc__ or ""), "the module states its own stage"

    for name, parameters in EXPECTED_SIGNATURES.items():
        function = getattr(module, name)
        assert callable(function), name
        signature = inspect.signature(function)
        assert tuple(signature.parameters) == parameters, name
        assert signature.return_annotation in (float, "float"), name
        assert name.endswith("_n"), f"{name} must carry the force unit in its name"
        docstring = inspect.getdoc(function) or ""
        assert docstring.startswith("Return"), name
        assert "[N]" in docstring, f"{name} must state the unit of its result"
        for parameter in parameters:
            assert parameter in docstring, f"{name}: {parameter} is not documented"
            assert UNIT_TOKEN_IN_DOCSTRING[parameter] in docstring, (
                f"{name}: the unit of {parameter} is not documented"
            )
        assert getattr(package, name) is function, f"physics.{name} is not re-exported"

    # the eight acceptance tables are printed one per delivered stage, Phase-5B last
    conftest_text = _CONFTEST.read_text(encoding="utf-8")
    assert "PHASE-5B TESTS (TEST P5-025 ... TEST P5-042)" in conftest_text
    for earlier in (
        "PHASE-1 ACCEPTANCE TESTS (TEST P1-001 ... TEST P1-012)",
        "PHASE-2 TESTS (TEST P2-001 ... TEST P2-028)",
        "GRR-01 REGISTRY REGRESSIONS (TEST P2-REG-G001 ... TEST P2-REG-G005)",
        "PHASE-3 TESTS (TEST P3-001 ... TEST P3-026)",
        "PHASE-4A TESTS (TEST P4-001 ... TEST P4-030)",
        "PHASE-4B TESTS (TEST P4-031 ... TEST P4-048)",
        "PHASE-5A TESTS (TEST P5-001 ... TEST P5-024)",
    ):
        assert earlier in conftest_text, earlier
    builder_text = _INVENTORY_BUILDER.read_text(encoding="utf-8")
    assert '"phase5b"' in builder_text
    assert "test_phase5b_along_route.py" in builder_text
    assert "Phase-5B suite (TEST P5-025 … TEST P5-042)" in builder_text


# ---------------------------------------------------------------------------
# P5-026 - the position-independent term forwards to Stage 5A
# ---------------------------------------------------------------------------
def test_p5_026_running_resistance_forwards_to_the_stage_5a_function():
    """TEST P5-026 - the running-resistance term is the Stage-5A value, recomputed."""
    module = _module()
    for speed_kmh in (0.0, 1.0, 120.0, 200.0, 320.0, 400.0):
        for coefficients in (
            (HSR_DAVIS_A, HSR_DAVIS_B, HSR_DAVIS_C),
            (0.0, 0.0, 0.0),
            (9.9, 0.0131, 0.000081),
        ):
            expected = resistance_module.davis_resistance_n(speed_kmh, *coefficients)
            observed = module.davis_resistance_at_n(speed_kmh, *coefficients)
            assert observed == expected, (speed_kmh, coefficients)
    # the frozen HSR case at 320 km/h, recomputed from the Stage-5A function
    assert module.davis_resistance_at_n(
        HSR_SPEED_KMH, HSR_DAVIS_A, HSR_DAVIS_B, HSR_DAVIS_C
    ) == resistance_module.davis_resistance_n(
        HSR_SPEED_KMH, HSR_DAVIS_A, HSR_DAVIS_B, HSR_DAVIS_C
    )
    # the Stage-5A validation is not re-implemented and not softened
    for bad in (
        (-1.0, HSR_DAVIS_A, HSR_DAVIS_B, HSR_DAVIS_C),
        (HSR_SPEED_KMH, -1.0, HSR_DAVIS_B, HSR_DAVIS_C),
        (float("nan"), HSR_DAVIS_A, HSR_DAVIS_B, HSR_DAVIS_C),
    ):
        with pytest.raises(ValueError):
            module.davis_resistance_at_n(*bad)
        with pytest.raises(ValueError):
            resistance_module.davis_resistance_n(*bad)


# ---------------------------------------------------------------------------
# P5-027 - the additive geometry method partitions the interval
# ---------------------------------------------------------------------------
def test_p5_027_radius_segments_partition_the_interval_from_the_stored_catalogue():
    """TEST P5-027 - the sub-intervals are ordered, sum to the span, and report stored radii."""
    document = _grr_document()
    assert _protected_file_sha256() == PROTECTED_GRR01_SHA256
    project = _load(document)
    geometry = _geometry(project)
    route_length_m = geometry.route_length_m
    stored_radii = _stored_radii(document)
    assert stored_radii == {1800.0, 1200.0, 2000.0}, stored_radii

    spans = ((0.0, route_length_m), (0.0, 900.0), (500.0, 20_000.0), (16_400.0, 33_400.0))
    for s_start_m, s_end_m in spans:
        segments = geometry.curve_radius_segments_in(s_start_m, s_end_m)
        assert isinstance(segments, tuple) and segments
        assert all(len(item) == 2 for item in segments)
        assert all(isinstance(item[0], float) for item in segments)
        assert sum(length_m for length_m, _radius_m in segments) == pytest.approx(
            s_end_m - s_start_m, abs=1e-9
        ), (s_start_m, s_end_m)
        for _length_m, radius_m in segments:
            assert radius_m is None or radius_m in stored_radii, radius_m
        # the partition is the coarsest one: no two neighbours repeat a radius
        assert all(
            first[1] != second[1] for first, second in zip(segments, segments[1:])
        ), segments
        # every reported length is positive and no sub-interval is empty
        assert all(length_m > 0.0 for length_m, _radius_m in segments)

    # the whole corridor is the stored catalogue clipped to the route's own chainage span:
    # the leading partial section first, then one sub-interval per stored boundary
    route = _route(project)
    span_low_km, span_high_km = _route_chainage_span_km(document, route)
    expected_radii: list[Any] = []
    expected_lengths: list[float] = []
    for section in _horizontal_sections(document):
        start_km = float(section["start_chainage_km"])
        end_km = float(section["end_chainage_km"])
        if end_km <= span_low_km or start_km >= span_high_km:
            continue
        expected_radii.append(
            None if section["type"] != "CURVE" else float(section["radius_m"])
        )
        expected_lengths.append(
            (min(end_km, span_high_km) - max(start_km, span_low_km)) * 1000.0
        )
    segments = geometry.curve_radius_segments_in(0.0, route_length_m)
    radii = [radius_m for _length_m, radius_m in segments]
    lengths = [length_m for length_m, _radius_m in segments]
    assert radii == expected_radii, radii
    assert lengths == pytest.approx(expected_lengths, abs=1e-6)
    assert sum(lengths) == pytest.approx(route_length_m, abs=1e-9)
    # a sub-interval that lies on a straight section is reported as (length_m, None)
    straight_lengths = [
        length_m
        for length_m, radius_m in geometry.curve_radius_segments_in(0.0, 900.0)
        if radius_m is None
    ]
    assert straight_lengths == [900.0]


# ---------------------------------------------------------------------------
# P5-028 - the interval errors: ValueError, and the delivered out-of-range convention
# ---------------------------------------------------------------------------
def test_p5_028_interval_errors_use_the_delivered_conventions():
    """TEST P5-028 - ValueError for a reversed interval; the footprint range convention."""
    project = _load(_grr_document())
    network = _network(project)
    geometry = RouteGeometry(project, network.route(PATH_ID, Direction.FORWARD))
    route_length_m = geometry.route_length_m

    for s_start_m, s_end_m in (
        (1000.0, 1000.0),
        (1000.0, 999.999),
        (5000.0, 100.0),
        (0.0, 0.0),
    ):
        with pytest.raises(ValueError):
            geometry.curve_radius_segments_in(s_start_m, s_end_m)

    # out of range: the same exception type the delivered footprint query raises
    for s_start_m, s_end_m in (
        (-1.0, 100.0),
        (-202.0, 0.0 - 0.001),
        (0.0, route_length_m + 1.0),
        (route_length_m - 10.0, route_length_m + 10.0),
    ):
        with pytest.raises(RouteCoordinateError):
            geometry.curve_radius_segments_in(s_start_m, s_end_m)
    with pytest.raises(RouteCoordinateError):
        geometry.footprint_gradient(0.0, HSR_TRAIN_LENGTH_M)
    with pytest.raises(RouteCoordinateError):
        geometry.footprint_gradient(route_length_m + 1.0, 1.0)

    # the interval is never clamped: a span that only just fits is answered in full
    edge_m = 0.5
    segments = geometry.curve_radius_segments_in(0.0, edge_m)
    assert sum(length_m for length_m, _radius_m in segments) == pytest.approx(edge_m, abs=1e-9)
    segments = geometry.curve_radius_segments_in(route_length_m - edge_m, route_length_m)
    assert sum(length_m for length_m, _radius_m in segments) == pytest.approx(edge_m, abs=1e-9)

    # and the new method answers a degenerate one-point-free interval only as an error
    with pytest.raises(ValueError):
        geometry.curve_radius_segments_in(100.0, 100.0)


# ---------------------------------------------------------------------------
# P5-029 ... P5-031 - the signed grade term
# ---------------------------------------------------------------------------
def test_p5_029_level_straight_footprint_returns_exactly_zero():
    """TEST P5-029 - on level track on a straight the grade force is exactly 0.0."""
    document = _with_changed_profile([(0.0, 100.0), (50.0, 100.0)])
    project = _load(document)
    geometry = _geometry(project)
    route = _route(project)
    # the footprint stays inside the stored STRAIGHT section HGR-01 ([0.0, 2.5] km)
    for chainage_km in (2.0, 2.2, 2.4):
        s_m = _s_of_chainage_km(document, route, chainage_km)
        assert _same_body_reverse_s_m(
            geometry.route_length_m, s_m, HSR_TRAIN_LENGTH_M
        ) <= geometry.route_length_m
        assert geometry.footprint_gradient(s_m, HSR_TRAIN_LENGTH_M) == 0.0
        assert _module().gradient_force_at_n(geometry, HSR_MASS_KG, s_m, HSR_TRAIN_LENGTH_M) == 0.0
    # the whole stored profile is level, so the grade is 0.0 wherever it is sampled
    # (every sampled front leaves room for the 202.0 m body inside [0, L])
    for s_m in (HSR_TRAIN_LENGTH_M, 1000.0, 20_000.0, geometry.route_length_m - 1.0):
        assert geometry.footprint_gradient(s_m, HSR_TRAIN_LENGTH_M) == 0.0
        assert _module().gradient_force_at_n(geometry, HSR_MASS_KG, s_m, HSR_TRAIN_LENGTH_M) == 0.0


def test_p5_030_grade_force_is_the_footprint_gradient_in_newtons():
    """TEST P5-030 - inside one stored gradient segment: m * g * (gradient / 1000), recomputed."""
    document = _grr_document()
    project = _load(document)
    geometry = _geometry(project)
    route = _route(project)
    points = _profile_points(document)
    span_low_km, span_high_km = _route_chainage_span_km(document, route)
    margin_km = HSR_TRAIN_LENGTH_M / 1000.0
    checked = 0
    for (low_km, low_m), (high_km, high_m) in zip(points, points[1:]):
        chainage_km = 0.5 * (low_km + high_km)
        # keep the 202.0 m body inside the stored segment and inside the route
        if high_km - low_km < 0.6 or not (
            span_low_km + margin_km < chainage_km < span_high_km
        ):
            continue
        s_m = _s_of_chainage_km(document, route, chainage_km)
        footprint_gradient = geometry.footprint_gradient(s_m, HSR_TRAIN_LENGTH_M)
        assert footprint_gradient == pytest.approx(
            (high_m - low_m) / (high_km - low_km), abs=1e-12
        )
        expected = HSR_MASS_KG * resistance_module.GRAVITY_MPS2 * (footprint_gradient / 1000.0)
        observed = _module().gradient_force_at_n(geometry, HSR_MASS_KG, s_m, HSR_TRAIN_LENGTH_M)
        assert observed == expected, chainage_km
        checked += 1
    assert checked >= 8, "the corridor must offer at least eight interior profile segments"


def test_p5_031_grade_force_is_direction_aware_for_the_same_train_body():
    """TEST P5-031 - FORWARD and REVERSE are opposite-signed for the same physical body."""
    document = _grr_document()
    project = _load(document)
    module = _module()
    forward_route = _route(project, PATH_ID, Direction.FORWARD)
    reverse_route = _route(project, PATH_ID, Direction.REVERSE)
    forward = RouteGeometry(project, forward_route)
    reverse = RouteGeometry(project, reverse_route)
    route_length_m = forward.route_length_m
    assert reverse.route_length_m == route_length_m

    non_zero = 0
    for chainage_km in SAMPLE_CHAINAGES_KM[1:]:
        s_forward_m = _s_of_chainage_km(document, forward_route, chainage_km)
        s_reverse_m = _same_body_reverse_s_m(route_length_m, s_forward_m, HSR_TRAIN_LENGTH_M)
        assert s_forward_m + s_reverse_m == pytest.approx(
            route_length_m + HSR_TRAIN_LENGTH_M, abs=1e-9
        )
        forward_force = module.gradient_force_at_n(
            forward, HSR_MASS_KG, s_forward_m, HSR_TRAIN_LENGTH_M
        )
        reverse_force = module.gradient_force_at_n(
            reverse, HSR_MASS_KG, s_reverse_m, HSR_TRAIN_LENGTH_M
        )
        assert forward_force == -reverse_force, chainage_km
        assert abs(forward_force) == pytest.approx(abs(reverse_force), rel=1e-9)
        if forward_force != 0.0:
            non_zero += 1
    assert non_zero >= 5, "the sampled corridor must cross non-flat gradient segments"

    # the same physical body means the same footprint: the delivered convention agrees
    for fraction in (0.2, 0.5, 0.8):
        s_forward_m = fraction * route_length_m
        s_reverse_m = _same_body_reverse_s_m(
            route_length_m, s_forward_m, HSR_TRAIN_LENGTH_M
        )
        assert forward.footprint_gradient(
            s_forward_m, HSR_TRAIN_LENGTH_M
        ) == -reverse.footprint_gradient(s_reverse_m, HSR_TRAIN_LENGTH_M)


# ---------------------------------------------------------------------------
# P5-032 ... P5-035 - the curvature term
# ---------------------------------------------------------------------------
def test_p5_032_straight_footprint_costs_no_curvature_force():
    """TEST P5-032 - a footprint wholly on straight sections returns exactly 0.0."""
    document = _grr_document()
    project = _load(document)
    geometry = _geometry(project)
    route = _route(project)
    straights_km = [
        (float(section["start_chainage_km"]), float(section["end_chainage_km"]))
        for section in _horizontal_sections(document)
        if section["type"] == "STRAIGHT"
    ]
    span_low_km, span_high_km = _route_chainage_span_km(document, route)
    margin_km = HSR_TRAIN_LENGTH_M / 1000.0
    checked = 0
    for start_km, end_km in straights_km:
        # the sampled front needs its 202.0 m body inside the straight and the route
        low_km = max(start_km, span_low_km + margin_km)
        high_km = min(end_km, span_high_km)
        if high_km - low_km < 0.3:
            continue
        chainage_km = 0.5 * (low_km + high_km)
        s_m = _s_of_chainage_km(document, route, chainage_km)
        segments = geometry.curve_radius_segments_in(s_m - HSR_TRAIN_LENGTH_M, s_m)
        assert all(radius_m is None for _length_m, radius_m in segments), chainage_km
        assert _module().curve_resistance_at_n(
            geometry, HSR_MASS_KG, s_m, HSR_TRAIN_LENGTH_M
        ) == 0.0
        checked += 1
    assert checked >= 4, straights_km


def test_p5_033_curve_footprint_is_the_stage_5a_single_radius_value():
    """TEST P5-033 - wholly inside one curve: m * g * W(R) / 1000, recomputed from R."""
    document = _grr_document()
    project = _load(document)
    module = _module()
    geometry = _geometry(project)
    route = _route(project)
    curves = [
        (float(section["start_chainage_km"]), float(section["end_chainage_km"]), float(section["radius_m"]))
        for section in _horizontal_sections(document)
        if section["type"] == "CURVE"
    ]
    assert len(curves) == 3
    span_low_km, span_high_km = _route_chainage_span_km(document, route)
    margin_km = HSR_TRAIN_LENGTH_M / 1000.0
    for start_km, end_km, radius_m in curves:
        low_km = max(start_km, span_low_km + margin_km)
        high_km = min(end_km, span_high_km)
        assert high_km - low_km > 0.3, (start_km, end_km)
        chainage_km = 0.5 * (low_km + high_km)
        s_m = _s_of_chainage_km(document, route, chainage_km)
        segments = geometry.curve_radius_segments_in(s_m - HSR_TRAIN_LENGTH_M, s_m)
        assert segments == ((HSR_TRAIN_LENGTH_M, radius_m),), (chainage_km, segments)
        permille = resistance_module.roeckl_equivalent_gradient_permille(radius_m)
        expected = HSR_MASS_KG * resistance_module.GRAVITY_MPS2 * permille / 1000.0
        observed = module.curve_resistance_at_n(geometry, HSR_MASS_KG, s_m, HSR_TRAIN_LENGTH_M)
        assert observed == expected, radius_m
        assert observed == resistance_module.roeckl_curve_resistance_n(HSR_MASS_KG, radius_m)


def test_p5_034_straddling_footprint_is_the_length_weighted_mean():
    """TEST P5-034 - a footprint across a straight/curve boundary: weighted mean, recomputed."""
    document = _grr_document()
    project = _load(document)
    module = _module()
    geometry = _geometry(project)
    route = _route(project)
    # the HGR-01 (STRAIGHT) / HGR-02 (CURVE, R = 1800 m) boundary is at chainage 2.5 km
    boundary_km = float(_horizontal_sections(document)[1]["start_chainage_km"])
    assert boundary_km == 2.5
    s_boundary_m = _s_of_chainage_km(document, route, boundary_km)
    s_front_m = s_boundary_m + 100.0
    segments = geometry.curve_radius_segments_in(s_front_m - HSR_TRAIN_LENGTH_M, s_front_m)
    assert [radius_m for _length_m, radius_m in segments] == [None, 1800.0]
    straight_m, curve_m = (length_m for length_m, _radius_m in segments)
    assert straight_m == pytest.approx(102.0, abs=1e-9)
    assert curve_m == pytest.approx(100.0, abs=1e-9)
    assert straight_m + curve_m == HSR_TRAIN_LENGTH_M
    permille = resistance_module.roeckl_equivalent_gradient_permille(1800.0)
    weighted_permille = (straight_m * 0.0 + curve_m * permille) / HSR_TRAIN_LENGTH_M
    expected = HSR_MASS_KG * resistance_module.GRAVITY_MPS2 * weighted_permille / 1000.0
    observed = module.curve_resistance_at_n(geometry, HSR_MASS_KG, s_front_m, HSR_TRAIN_LENGTH_M)
    assert observed == expected
    # strictly between the two ends: the straight contributes nothing, so 0 < F < F(R)
    full_curve = module.curve_resistance_at_n(geometry, HSR_MASS_KG, s_boundary_m + 500.0, HSR_TRAIN_LENGTH_M)
    assert 0.0 < observed < full_curve
    # the same arithmetic recomputed from the two half-lengths: a 50/50 split of the mean
    half_m = 0.5 * HSR_TRAIN_LENGTH_M
    s_half_m = s_boundary_m + half_m
    assert geometry.curve_radius_segments_in(s_half_m - HSR_TRAIN_LENGTH_M, s_half_m) == (
        (half_m, None),
        (half_m, 1800.0),
    )
    assert module.curve_resistance_at_n(
        geometry, HSR_MASS_KG, s_half_m, HSR_TRAIN_LENGTH_M
    ) == pytest.approx(0.5 * full_curve, rel=1e-15)


def test_p5_035_curvature_is_non_negative_and_direction_independent():
    """TEST P5-035 - non-negative everywhere, and equal in both directions of travel."""
    document = _grr_document()
    project = _load(document)
    module = _module()
    forward_route = _route(project, PATH_ID, Direction.FORWARD)
    reverse_route = _route(project, PATH_ID, Direction.REVERSE)
    forward = RouteGeometry(project, forward_route)
    reverse = RouteGeometry(project, reverse_route)
    route_length_m = forward.route_length_m

    non_zero = 0
    step_m = HSR_TRAIN_LENGTH_M
    s_m = HSR_TRAIN_LENGTH_M
    while s_m <= route_length_m:
        forward_force = module.curve_resistance_at_n(
            forward, HSR_MASS_KG, s_m, HSR_TRAIN_LENGTH_M
        )
        assert forward_force >= 0.0, s_m
        reverse_force = module.curve_resistance_at_n(
            reverse,
            HSR_MASS_KG,
            _same_body_reverse_s_m(route_length_m, s_m, HSR_TRAIN_LENGTH_M),
            HSR_TRAIN_LENGTH_M,
        )
        # the same physical body, read from the other direction: the two partitions can
        # differ in the last bits of the intermediate lengths, so the equality is asserted
        # as an engineering identity (1e-9 relative), not as a bit-for-bit coincidence
        assert forward_force == pytest.approx(reverse_force, rel=1e-9, abs=1e-9), s_m
        if forward_force > 0.0:
            non_zero += 1
        s_m += step_m
    assert non_zero > 0, "the corridor must cross curved sections"


# ---------------------------------------------------------------------------
# P5-036 ... P5-038 - the total
# ---------------------------------------------------------------------------
def test_p5_036_total_is_the_literal_sum_recomputed():
    """TEST P5-036 - the total is running + grade + curvature, recomputed by the test."""
    document = _grr_document()
    project = _load(document)
    module = _module()
    geometry = _geometry(project)
    route = _route(project)
    checked = 0
    for chainage_km in SAMPLE_CHAINAGES_KM[1:]:
        for speed_kmh in (0.0, 160.0, HSR_SPEED_KMH):
            for mass_kg in (HSR_MASS_KG, 0.5 * HSR_MASS_KG):
                for train_length_m in (HSR_TRAIN_LENGTH_M, 100.0):
                    s_m = _s_of_chainage_km(document, route, chainage_km)
                    if train_length_m > s_m:
                        continue
                    expected = (
                        module.davis_resistance_at_n(
                            speed_kmh, HSR_DAVIS_A, HSR_DAVIS_B, HSR_DAVIS_C
                        )
                        + module.gradient_force_at_n(geometry, mass_kg, s_m, train_length_m)
                        + module.curve_resistance_at_n(geometry, mass_kg, s_m, train_length_m)
                    )
                    observed = module.total_resistance_at_n(
                        geometry,
                        mass_kg,
                        train_length_m,
                        s_m,
                        speed_kmh,
                        HSR_DAVIS_A,
                        HSR_DAVIS_B,
                        HSR_DAVIS_C,
                    )
                    assert observed == expected, (chainage_km, speed_kmh, mass_kg, train_length_m)
                    checked += 1
    assert checked >= 25, checked


def test_p5_037_total_on_level_straight_track_is_the_running_resistance_alone():
    """TEST P5-037 - level and straight: the total is the position-independent term."""
    document = _with_changed_profile([(0.0, 250.0), (50.0, 250.0)])
    project = _load(document)
    module = _module()
    geometry = _geometry(project)
    route = _route(project)
    s_m = _s_of_chainage_km(document, route, 2.0)
    expected = module.davis_resistance_at_n(
        HSR_SPEED_KMH, HSR_DAVIS_A, HSR_DAVIS_B, HSR_DAVIS_C
    )
    assert module.gradient_force_at_n(geometry, HSR_MASS_KG, s_m, HSR_TRAIN_LENGTH_M) == 0.0
    assert module.curve_resistance_at_n(geometry, HSR_MASS_KG, s_m, HSR_TRAIN_LENGTH_M) == 0.0
    assert (
        module.total_resistance_at_n(
            geometry,
            HSR_MASS_KG,
            HSR_TRAIN_LENGTH_M,
            s_m,
            HSR_SPEED_KMH,
            HSR_DAVIS_A,
            HSR_DAVIS_B,
            HSR_DAVIS_C,
        )
        == expected
    )


def test_p5_038_total_can_be_negative_on_a_steep_synthetic_descent():
    """TEST P5-038 - a steep enough descent outweighs both resistance magnitudes."""
    document = _with_changed_profile([(0.0, 2000.0), (20.0, 200.0), (50.0, 0.0)])
    project = _load(document)
    module = _module()
    geometry = _geometry(project)
    route = _route(project)
    assert geometry.diagnostics == ()
    # the first stored profile segment descends 1800 m over 20 km = -90 permille
    assert geometry.footprint_gradient(
        _s_of_chainage_km(document, route, 10.0), HSR_TRAIN_LENGTH_M
    ) == pytest.approx((200.0 - 2000.0) / 20.0, abs=1e-12)
    s_m = _s_of_chainage_km(document, route, 10.0)
    davis = module.davis_resistance_at_n(HSR_SPEED_KMH, HSR_DAVIS_A, HSR_DAVIS_B, HSR_DAVIS_C)
    grade = module.gradient_force_at_n(geometry, HSR_MASS_KG, s_m, HSR_TRAIN_LENGTH_M)
    curve = module.curve_resistance_at_n(geometry, HSR_MASS_KG, s_m, HSR_TRAIN_LENGTH_M)
    assert grade < 0.0 and curve >= 0.0 and davis > 0.0
    total = module.total_resistance_at_n(
        geometry,
        HSR_MASS_KG,
        HSR_TRAIN_LENGTH_M,
        s_m,
        HSR_SPEED_KMH,
        HSR_DAVIS_A,
        HSR_DAVIS_B,
        HSR_DAVIS_C,
    )
    assert total == davis + grade + curve
    assert total < 0.0, total
    # and the frozen project itself was not touched by the synthetic case
    assert _protected_file_sha256() == PROTECTED_GRR01_SHA256


# ---------------------------------------------------------------------------
# P5-039 - the errors are propagated, never swallowed
# ---------------------------------------------------------------------------
def test_p5_039_errors_are_propagated_and_nothing_is_substituted():
    """TEST P5-039 - non-positive length, out-of-range footprint and bad mass all report."""
    document = _grr_document()
    project = _load(document)
    module = _module()
    geometry = _geometry(project)
    route_length_m = geometry.route_length_m
    route = _route(project)
    s_m = _s_of_chainage_km(document, route, 20.0)

    for bad_length_m in (0.0, -1.0, -HSR_TRAIN_LENGTH_M):
        for call in (
            lambda length_m=bad_length_m: module.gradient_force_at_n(
                geometry, HSR_MASS_KG, s_m, length_m
            ),
            lambda length_m=bad_length_m: module.curve_resistance_at_n(
                geometry, HSR_MASS_KG, s_m, length_m
            ),
            lambda length_m=bad_length_m: module.total_resistance_at_n(
                geometry, HSR_MASS_KG, length_m, s_m, HSR_SPEED_KMH, HSR_DAVIS_A, HSR_DAVIS_B, HSR_DAVIS_C
            ),
        ):
            with pytest.raises(ValueError):
                call()

    for bad_s_m in (-1.0, -HSR_TRAIN_LENGTH_M, route_length_m + 0.5):
        with pytest.raises(RouteCoordinateError):
            module.gradient_force_at_n(geometry, HSR_MASS_KG, bad_s_m, HSR_TRAIN_LENGTH_M)
        with pytest.raises(RouteCoordinateError):
            module.curve_resistance_at_n(geometry, HSR_MASS_KG, bad_s_m, HSR_TRAIN_LENGTH_M)
        with pytest.raises(RouteCoordinateError):
            module.total_resistance_at_n(
                geometry, HSR_MASS_KG, HSR_TRAIN_LENGTH_M, bad_s_m, HSR_SPEED_KMH,
                HSR_DAVIS_A, HSR_DAVIS_B, HSR_DAVIS_C,
            )
    # the geometry refuses, it never clamps: the front 101 m from the origin is fine,
    # the front at the origin is not (the footprint would start 202.0 m before the route)
    module.gradient_force_at_n(geometry, HSR_MASS_KG, HSR_TRAIN_LENGTH_M, HSR_TRAIN_LENGTH_M)
    with pytest.raises(RouteCoordinateError):
        module.gradient_force_at_n(geometry, HSR_MASS_KG, 0.0, HSR_TRAIN_LENGTH_M)

    # the mass error is the Stage-5A error, word for word
    for bad_mass_kg in (0.0, -1.0):
        with pytest.raises(ValueError) as observed:
            module.curve_resistance_at_n(geometry, bad_mass_kg, s_m, HSR_TRAIN_LENGTH_M)
        with pytest.raises(ValueError) as expected:
            resistance_module.roeckl_curve_resistance_n(bad_mass_kg, None)
        assert str(observed.value) == str(expected.value)
    # a bad mass is reported even where the footprint is entirely straight (no radius used)
    straight_s_m = _s_of_chainage_km(document, _route(project), 2.0)
    with pytest.raises(ValueError):
        module.curve_resistance_at_n(geometry, -1.0, straight_s_m, HSR_TRAIN_LENGTH_M)


# ---------------------------------------------------------------------------
# P5-040 - purity: identical inputs, identical output, no project touched
# ---------------------------------------------------------------------------
def test_p5_040_calls_are_pure_and_the_loaded_project_is_unchanged():
    """TEST P5-040 - bit-identical repeats; canonical and companion hashes unchanged."""
    document = _grr_document()
    hash_before = hashlib.sha256(
        json.dumps(to_normalized_dict(_load(document)), sort_keys=True).encode("utf-8")
    ).hexdigest()
    project = _load(document)
    module = _module()
    network = _network(project)
    forward = RouteGeometry(project, network.route(PATH_ID, Direction.FORWARD))
    reverse = RouteGeometry(project, network.route(PATH_ID, Direction.REVERSE))
    route_length_m = forward.route_length_m
    # chainage 25.0 km lies inside the stored CURVE section HGR-04 (R = 1200.0 m)
    s_m = _s_of_chainage_km(document, network.route(PATH_ID, Direction.FORWARD), 25.0)
    s_reverse_m = _same_body_reverse_s_m(route_length_m, s_m, HSR_TRAIN_LENGTH_M)

    calls = (
        lambda: module.davis_resistance_at_n(HSR_SPEED_KMH, HSR_DAVIS_A, HSR_DAVIS_B, HSR_DAVIS_C),
        lambda: module.gradient_force_at_n(forward, HSR_MASS_KG, s_m, HSR_TRAIN_LENGTH_M),
        lambda: module.curve_resistance_at_n(forward, HSR_MASS_KG, s_m, HSR_TRAIN_LENGTH_M),
        lambda: module.total_resistance_at_n(
            forward, HSR_MASS_KG, HSR_TRAIN_LENGTH_M, s_m, HSR_SPEED_KMH,
            HSR_DAVIS_A, HSR_DAVIS_B, HSR_DAVIS_C,
        ),
        lambda: forward.curve_radius_segments_in(s_m - HSR_TRAIN_LENGTH_M, s_m),
        lambda: module.gradient_force_at_n(reverse, HSR_MASS_KG, s_reverse_m, HSR_TRAIN_LENGTH_M),
    )
    for call in calls:
        first = call()
        second = call()
        assert first == second
        if isinstance(first, float):
            # bit-for-bit: float.hex() distinguishes every bit, including +0.0/-0.0
            assert first.hex() == second.hex()

    hash_after = hashlib.sha256(
        json.dumps(to_normalized_dict(project), sort_keys=True).encode("utf-8")
    ).hexdigest()
    assert hash_before == hash_after
    assert document_hash(to_normalized_dict(project)) == CANONICAL_GRR01_HASH
    assert _companion_sha256() == COMPANION_SHA256
    # the route and the geometry still answer exactly as before the calls
    assert network.path_ids == (PATH_ID, "PATH-H1-R")
    assert forward.curve_radius_segments_in(s_m - HSR_TRAIN_LENGTH_M, s_m) == (
        (HSR_TRAIN_LENGTH_M, 1200.0),
    )


# ---------------------------------------------------------------------------
# P5-041 - the import surface of the new module
# ---------------------------------------------------------------------------
def test_p5_041_new_module_imports_no_numeric_library():
    """TEST P5-041 - standard library plus the package's own modules, nothing else."""
    assert _MODULE_PATH.is_file()
    imported = _import_edges(_MODULE_PATH)
    assert imported == {"__future__", "typing", "."}, sorted(imported)
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

    tree = ast.parse(_MODULE_PATH.read_text(encoding="utf-8"))
    relative_names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots = [alias.name.split(".")[0] for alias in node.names]
            assert roots and all(root in sys.stdlib_module_names for root in roots), roots
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                # a relative import inside the physics package: `from . import resistance`
                assert node.module is None and node.level == 1, node.module
                relative_names.extend(alias.name for alias in node.names)
                continue
            root = (node.module or "").split(".")[0]
            assert root in sys.stdlib_module_names, node.module
            assert root != "railway_headway_sim", node.module
    assert relative_names == ["resistance"], relative_names

    # importing the module is side-effect free and the package reaches it consistently
    module = importlib.import_module("railway_headway_sim.physics.along_route")
    assert module is along_route_module
    package = importlib.import_module("railway_headway_sim.physics")
    assert package.along_route is module
    assert sys.modules["railway_headway_sim.physics.along_route"] is module
    # the module declares no mutable module-level state
    for name, value in vars(module).items():
        if name.startswith("__") or inspect.ismodule(value) or inspect.isfunction(value):
            continue
        assert not isinstance(value, (dict, list, set)), name


# ---------------------------------------------------------------------------
# P5-042 - the Section-D scan and the counted suite
# ---------------------------------------------------------------------------
def test_p5_042_section_d_scan_and_the_registered_phase5b_table():
    """TEST P5-042 - no Section-D token outside the allowed ones; the table is counted."""
    s1_tokens = _section_tokens("## 2. S1")
    s3_tokens = _section_tokens("## 4. S3")
    allowed_tokens = _section_tokens("## 2.1")
    assert len(s1_tokens) == 9 and len(s3_tokens) == 7, (s1_tokens, s3_tokens)
    assert allowed_tokens == (
        "Davis",
        "Roeckl",
        "rolling resistance",
        "curve resistance",
        "gradient force",
    ), allowed_tokens
    assert not (set(token.lower() for token in allowed_tokens) & set(s1_tokens))

    # (a) no forbidden token is declared in the new module
    declared_names = _declared_names(_MODULE_PATH)
    forbidden = [
        name
        for name in declared_names
        for token in s1_tokens + s3_tokens
        if token in name.lower()
    ]
    assert forbidden == [], forbidden

    # (b) the prose of the new module keeps to plain language: none of the five allowed
    # tokens appears in a docstring or a comment (§F6); only the mandated function names
    # carry one, and only "davis" - inside the required public name davis_resistance_at_n
    prose = _prose_of(_MODULE_PATH)
    # the mandated names of §D2 have to be documented, so the parameters they name are
    # stripped - and only those exact identifiers; any other occurrence of an allowed token
    # in a docstring or a comment is a finding
    stripped = prose
    for mandated_name in ("davis_resistance_at_n", "davis_a", "davis_b", "davis_c"):
        stripped = stripped.replace(mandated_name, "")
    for token in allowed_tokens:
        assert token.lower() not in stripped.lower(), token
    assert "davis" in prose.lower(), "the mandated name must be the only carrier"
    carrying = sorted(
        name for name in declared_names if any(t.lower() in name.lower() for t in allowed_tokens)
    )
    assert carrying == ["davis_resistance_at_n"], carrying

    # (c) the five allowed tokens still live only inside the physics package (the surface
    # of TEST P2-028 / TEST P5-023, declared adaptation A1/A2 of Stage 5B)
    allowed_package = _PACKAGE_DIR / "physics"
    offenders: list[str] = []
    for path in sorted(_PACKAGE_DIR.rglob("*.py")):
        if "tests" in path.parts or path.name in {"codes.py", "grr_audit.py"}:
            continue
        for name in _declared_names(path):
            if any(token.lower() in name.lower() for token in allowed_tokens):
                if allowed_package not in path.parents:
                    offenders.append(f"{path.relative_to(_PACKAGE_DIR)}:{name}")
    assert offenders == [], offenders
    in_package = sorted(
        name
        for path in sorted(allowed_package.glob("*.py"))
        for name in _declared_names(path)
        if any(token.lower() in name.lower() for token in allowed_tokens)
    )
    assert in_package == [
        "davis_resistance_at_n",
        "davis_resistance_n",
        "is_roeckl_radius_usable",
        "roeckl_curve_resistance_n",
        "roeckl_equivalent_gradient_permille",
    ], in_package

    # (d) the Phase-5B suite is registered, counted, and the inventory quotes the total
    source = Path(__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    acceptance_ids: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_p5_"):
            assert isinstance(node.body[0], ast.Expr) and isinstance(
                node.body[0].value, ast.Constant
            ), node.name
            text = str(node.body[0].value.value)
            match = re.search(r"\bP5-\d{3}\b", text)
            assert match, node.name
            acceptance_ids.append(match.group(0))
    assert sorted(set(acceptance_ids)) == [
        f"P5-{number:03d}" for number in range(25, 43)
    ], sorted(set(acceptance_ids))
    assert len(acceptance_ids) == 18
    # Declared adaptation A6 (Phase 6A): the two literal pins of the Stage-5B inventory text
    # ("... = `217` collected items", "Total (all eight suites) | `217`") cannot survive a later
    # stage, because docs/TEST_INVENTORY.md is a generated file whose totals and suite count
    # follow the collected suite. They are replaced by an exact structural check of the same
    # facts - the canonical decomposition must sum to its own stated total, the totals row must
    # state that same number and count its suites, and the Phase-5B suite must still be listed
    # with its own range and rows. (Adaptation A4 is the Phase-5A counterpart of this check; no
    # expectation of this test is changed, dropped or loosened.)
    inventory = _INVENTORY.read_text(encoding="utf-8")
    assert "| Phase-5B suite (TEST P5-025 … TEST P5-042) | 18 |" in inventory
    assert "### Phase-5B suite (TEST P5-025 … TEST P5-042) — 18/18 rows" in inventory
    assert "| `P5-042` |" in inventory
    decomposition = re.search(r"`(\d+(?: \+ \d+)+) = (\d+)` collected items", inventory)
    assert decomposition, "the canonical decomposition string is missing"
    parts = [int(part) for part in decomposition.group(1).split(" + ")]
    total = int(decomposition.group(2))
    assert sum(parts) == total, (parts, total)
    totals_row = re.search(
        r"\| \*\*Total \(all (\w+) suites\)\*\* \| \*\*(\d+)\*\* \|", inventory
    )
    assert totals_row, "the totals row is missing"
    # Declared adaptation A10 (Phase 6B): the totals row of the generated inventory now
    # counts ten suites; the map gained the matching word and nothing else changed.
    number_words = {"five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}
    assert number_words[totals_row.group(1)] == len(parts), totals_row.group(0)
    assert int(totals_row.group(2)) == total, totals_row.group(0)
