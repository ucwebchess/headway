"""Phase-4A acceptance tests: compiled network and route coordinates.

TEST P4-001 ... TEST P4-030.

Scope of this module (master specification, Phase 4A):

* ``compile_network`` turns one validated project into a read-only
  :class:`~railway_headway_sim.infrastructure.compiled_network.CompiledNetwork`
  (physical edges plus the train paths the project declares) and, per
  ``(train_path, direction)``, one
  :class:`~railway_headway_sim.infrastructure.compiled_network.RouteCoordinateSystem`
  carrying route distance ``s`` [m] and the mapped physical chainage [km].
* ``FORWARD`` uses every declared entry as written; ``REVERSE`` walks the same
  physical edges in the reversed order with the complementary traversal.  The
  loaded project, its document and the protected ``examples/GRR-01.json`` are
  never written.
* Every defect a declared path can carry (unresolved ``edge_id``, missing
  ``edge_id``, unusable ``traversal``, sequence break, empty sequence, duplicate
  path id, unusable direction) is reported through existing diagnostic codes and
  the path is refused; nothing is silently repaired or dropped.

**Declared-path data.**  Two different things are kept strictly apart here:

* the reference railway's **declared train paths** ``PATH-H1-F`` / ``PATH-H1-R``
  live in the companion file ``examples/GRR-01-paths.json`` and are read from it
  with ``compile_network(project, paths_source=...)`` (``TEST P4-023`` /
  ``P4-024``).  The frozen ``examples/GRR-01.json`` (protected, hash-checked
  here) stays byte-identical and still declares ``train_paths.paths == []``
  itself;
* this module's own **test-corridor** paths are named ``TEST-CORRIDOR-A-D`` and
  ``TEST-CORRIDOR-D-A`` so that they can never be confused with a reference
  service path.  ``TEST_CORRIDOR_EDGE_IDS`` below is the physical edge sequence
  of the Alpha-West -> Delta-P1-East corridor of the reference project, and the
  traversal of every entry is derived from the project's own track endpoints,
  never hand-typed.  ``TEST P4-025`` is the regression that this corridor still
  measures exactly 49 000.000 m between its two original endpoint edges.

Nothing is written into the protected file or into any fixture of the reference
project.

The tiny synthetic fixture (D6, ``_fixture_document``) is built inside this
module and contains the two anomalous chainage conditions the specification
requires: an edge whose ``length_m`` exceeds its chainage projection
(``FX-E2``: 2 650 m over 1.000 km) and an edge whose ``chainage_map`` is
opposite-oriented (``FX-E3``: 3.000 km at its first node, 2.000 km at its last,
i.e. the chainage decreases along the stored from->to direction).
"""

from __future__ import annotations

import ast
import copy
import dataclasses
import hashlib
import importlib
import json
import re
import sys
from pathlib import Path
from typing import Any

import pytest

from railway_headway_sim.infrastructure import (
    CompiledNetwork,
    RouteCoordinateError,
    RouteCoordinateSystem,
    RoutePosition,
    RouteSegment,
    compile_network,
    complementary_traversal,
    normalize_direction,
)
from railway_headway_sim.infrastructure import grr_fixtures
from railway_headway_sim.infrastructure.compiler import compile_infrastructure
from railway_headway_sim.infrastructure.mapping import (
    CHAINAGE_TOLERANCE_KM,
    POSITION_TOLERANCE_M,
    edge_position_to_chainage,
)
from railway_headway_sim.infrastructure.topology import InfrastructureTopology
from railway_headway_sim.io.project_io import (
    document_hash,
    import_project_from_data,
    import_project_from_file,
    to_normalized_dict,
)
from railway_headway_sim.models.enums import DiagnosticCategory, Direction, EdgeTraversal, Severity
from railway_headway_sim.models.project import Project

_REPO_ROOT = Path(__file__).resolve().parents[2]
_PROTECTED_GRR01 = _REPO_ROOT / "examples" / "GRR-01.json"
_NETWORK_MODULE = _REPO_ROOT / "railway_headway_sim" / "infrastructure" / "compiled_network.py"
_SECTION_D_PATTERNS = _REPO_ROOT / "docs" / "SECTION_D_PATTERNS.md"

#: sha256 of the protected reference project file (must not change; checked here).
PROTECTED_GRR01_SHA256 = "ad0a26265d4e072aeedcc69161bef90f200c20b4efb12a4d56a5276c4a4f7a56"

#: Canonical document hash of the reference project (must not change).
CANONICAL_GRR01_HASH = "5189aaa2340c17022666ef44772c7d34f99b2fea9ee9609bb7b7513238ef4dbe"

#: Edge sequence of the test corridor TEST-CORRIDOR-A-D (Alpha-West -> Delta-P1-East),
#: built inside this module as test data (see the module docstring).  Every step
#: traverses WITH_EDGE.  The reference railway's own paths are PATH-H1-F / PATH-H1-R
#: and live in examples/GRR-01-paths.json.
TEST_CORRIDOR_EDGE_IDS: tuple[str, ...] = (
    "TR-A-W-U1",
    "TR-A-U1-U2",
    "TR-O-ALP-CEN-ML2",
    "TR-C-W-LDR-ML1",
    "TR-C-XA-P4",
    "TR-C-P4",
    "TR-C-P4-E-CON",
    "TR-O-CEN-VAL-SL-B",
    "TR-V-THRU2",
    "TR-V-T2B-E",
    "TR-O-VAL-DEL-ML1",
    "TR-D-W-THR",
    "TR-D-THR-J",
    "TR-D-J-P1W",
    "TR-D-P1",
)
REFERENCE_PATH_IDS: tuple[str, ...] = ("PATH-H1-F", "PATH-H1-R")
REFERENCE_PATHS_FILE = "examples/GRR-01-paths.json"
TEST_CORRIDOR_START_NODE = "N-ALP-W"
TEST_CORRIDOR_END_NODE = "N-DEL-P1-E"
TEST_CORRIDOR_A_D_ID = "TEST-CORRIDOR-A-D"
TEST_CORRIDOR_D_A_ID = "TEST-CORRIDOR-D-A"
TEST_CORRIDOR_LENGTH_M = 49000.0

FIXTURE_LAYER_ID = "LYR-FIX"
FIXTURE_ALIGNMENT_ID = "ALN-FIX"
FIXTURE_PATH_ID = "FX-P1"
FIXTURE_REVERSE_PATH_ID = "FX-P1R"
FIXTURE_EDGE_ORDER: tuple[str, ...] = ("FX-E1", "FX-E2", "FX-E3")
FIXTURE_ROUTE_LENGTH_M = 4650.0
FIXTURE_EDGE_LENGTHS_M = {"FX-E1": 1000.0, "FX-E2": 2650.0, "FX-E3": 1000.0}
FIXTURE_CHAINAGE_MAPS_KM = {"FX-E1": (0.0, 1.0), "FX-E2": (1.0, 3.0), "FX-E3": (3.0, 2.0)}

#: A declared path that is a legal *reversal* move: it enters N-CEN-X-C on
#: ``TR-C-E-U2-X`` (WITH_EDGE) and leaves along ``TR-C-P2-E-CON`` (AGAINST_EDGE).
REVERSAL_MOVE_PATH_ID = "REV-DEMO"
REVERSAL_MOVE_EDGE_IDS: tuple[str, ...] = ("TR-C-E-U2-X", "TR-C-P2-E-CON")
REVERSAL_MOVE_LENGTH_M = 970.0

#: Sampled offset (metres) used to stay just inside a segment when reading the
#: chainage of a segment end-point (the boundary itself belongs to the edge
#: that is being left, so the sample is taken from within the edge).
_EPS_M = 1e-4


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _protected_file_sha256() -> str:
    """Return the sha256 of the protected reference project file."""
    return hashlib.sha256(_PROTECTED_GRR01.read_bytes()).hexdigest()


def _declared_entries(
    edge_ids: tuple[str, ...], tracks: dict[str, dict[str, Any]], start_node: str
) -> list[dict[str, str]]:
    """Return the declared entries of a walk over *edge_ids* from *start_node*.

    The traversal of every entry is derived from the project's own track
    endpoints: no WITH_EDGE/AGAINST_EDGE value is hand-typed in this module.
    """
    entries: list[dict[str, str]] = []
    current = start_node
    for edge_id in edge_ids:
        track = tracks[edge_id]
        with_edge = track["from_node"] == current
        entries.append(
            {
                "edge_id": edge_id,
                "traversal": (
                    EdgeTraversal.WITH_EDGE.value if with_edge else EdgeTraversal.AGAINST_EDGE.value
                ),
            }
        )
        current = track["to_node"] if with_edge else track["from_node"]
    return entries


def _complementary_entries(entries: list[dict[str, str]]) -> list[dict[str, str]]:
    """Return the reversed walk of *entries* with complementary traversals."""
    return [
        {
            "edge_id": entry["edge_id"],
            "traversal": complementary_traversal(EdgeTraversal(entry["traversal"])).value,
        }
        for entry in reversed(entries)
    ]


def _fixture_layer() -> dict[str, Any]:
    """Return the synthetic Phase-4A coordinate fixture layer."""
    return {
        "id": FIXTURE_LAYER_ID,
        "name": "Phase-4A coordinate fixture (synthetic)",
        "physical_mode": "PHYSICAL",
        "comment": "synthetic coordinate fixture - not reference project data",
        "alignments": [
            {
                "id": FIXTURE_ALIGNMENT_ID,
                "name": "fixture alignment",
                "start_chainage_km": 0.0,
                "end_chainage_km": 4.0,
            }
        ],
        "nodes": [
            {"id": "NX-A", "type": "BUFFER_STOP", "chainage_km": 0.0, "name": "fixture origin"},
            {"id": "NX-B", "type": "CONNECTION", "chainage_km": 1.0, "name": "fixture B"},
            {"id": "NX-C", "type": "CONNECTION", "chainage_km": 3.0, "name": "fixture C"},
            {"id": "NX-D", "type": "BUFFER_STOP", "chainage_km": 2.0, "name": "fixture D"},
        ],
        "tracks": [
            {
                "id": "FX-E1",
                "from_node": "NX-A",
                "to_node": "NX-B",
                "length_m": FIXTURE_EDGE_LENGTHS_M["FX-E1"],
                "directionality": "BOTH",
                "chainage_map": {"mode": "LINEAR", "start_km": 0.0, "end_km": 1.0},
            },
            {
                "id": "FX-E2",
                "from_node": "NX-B",
                "to_node": "NX-C",
                "length_m": FIXTURE_EDGE_LENGTHS_M["FX-E2"],
                "directionality": "BOTH",
                "chainage_map": {"mode": "LINEAR", "start_km": 1.0, "end_km": 3.0},
            },
            {
                "id": "FX-E3",
                "from_node": "NX-C",
                "to_node": "NX-D",
                "length_m": FIXTURE_EDGE_LENGTHS_M["FX-E3"],
                "directionality": "BOTH",
                "chainage_map": {"mode": "LINEAR", "start_km": 3.0, "end_km": 2.0},
            },
        ],
    }


def _clean_paths() -> list[dict[str, Any]]:
    """Return the two well-formed declared paths of the fixture."""
    return [
        {
            "id": FIXTURE_PATH_ID,
            "edges": [
                {"edge_id": edge_id, "traversal": EdgeTraversal.WITH_EDGE.value}
                for edge_id in FIXTURE_EDGE_ORDER
            ],
        },
        {
            "id": FIXTURE_REVERSE_PATH_ID,
            "edges": [
                {"edge_id": edge_id, "traversal": EdgeTraversal.AGAINST_EDGE.value}
                for edge_id in reversed(FIXTURE_EDGE_ORDER)
            ],
        },
    ]


def _defect_paths() -> list[dict[str, Any]]:
    """Return the fixture's declared paths plus one path per D5 defect."""
    paths = _clean_paths()
    paths.extend(
        [
            {
                "id": "FX-GAP",
                "edges": [
                    {"edge_id": "FX-E1", "traversal": EdgeTraversal.WITH_EDGE.value},
                    {"edge_id": "FX-E3", "traversal": EdgeTraversal.WITH_EDGE.value},
                ],
            },
            {
                "id": "FX-UNKNOWN",
                "edges": [
                    {"edge_id": "FX-E1", "traversal": EdgeTraversal.WITH_EDGE.value},
                    {"edge_id": "FX-NOPE", "traversal": EdgeTraversal.WITH_EDGE.value},
                ],
            },
            {"id": "FX-BADTRAV", "edges": [{"edge_id": "FX-E1", "traversal": "SIDEWAYS"}]},
            {"id": "FX-NOID", "edges": [{"traversal": EdgeTraversal.WITH_EDGE.value}]},
            {"id": "FX-EMPTY", "edges": []},
            # duplicate path id (deliberate: D5 "never silently repaired")
            {"id": FIXTURE_PATH_ID, "edges": [{"edge_id": "FX-E1", "traversal": "WITH_EDGE"}]},
        ]
    )
    return paths


def _fixture_document(paths: list[dict[str, Any]]) -> dict[str, Any]:
    """Return a fixture project document declaring *paths*."""
    document = to_normalized_dict(Project.new())
    document["reference_system"]["alignment_id"] = FIXTURE_ALIGNMENT_ID
    document["reference_system"]["chainage_start_km"] = 0.0
    document["reference_system"]["chainage_end_km"] = 4.0
    document["infrastructure"] = [_fixture_layer()]
    document["train_paths"]["paths"] = copy.deepcopy(paths)
    return document


def _load(document: dict[str, Any]) -> Any:
    """Import *document* and return the validated project."""
    outcome = import_project_from_data(document, source_name="<phase4a test>")
    assert outcome.ok, outcome.status_text
    return outcome.project


def _fixture_network(paths: list[dict[str, Any]] | None = None) -> CompiledNetwork:
    """Compile the synthetic fixture network (clean paths by default)."""
    return compile_network(_load(_fixture_document(paths if paths is not None else _clean_paths())))


def _grr_document(declare_paths: bool = True) -> dict[str, Any]:
    """Return the reference project document, optionally declaring the test corridor."""
    document = copy.deepcopy(grr_fixtures.build_grr01_document())
    if declare_paths:
        tracks = {track["id"]: track for track in document["infrastructure"][0]["tracks"]}
        forward = _declared_entries(TEST_CORRIDOR_EDGE_IDS, tracks, TEST_CORRIDOR_START_NODE)
        document["train_paths"]["paths"] = [
            {"id": TEST_CORRIDOR_A_D_ID, "edges": forward},
            {"id": TEST_CORRIDOR_D_A_ID, "edges": _complementary_entries(forward)},
        ]
    return document


def _grr_network() -> CompiledNetwork:
    """Compile the reference network with the test corridor declared."""
    return compile_network(_load(_grr_document()))


def _chainage_endpoints(rcs: RouteCoordinateSystem) -> dict[str, tuple[float, float]]:
    """Return ``{edge_id: (chainage at entry, chainage at exit)}`` of one route."""
    endpoints: dict[str, tuple[float, float]] = {}
    for segment in rcs.segments:
        entry = rcs.at_route_distance(segment.start_s_m + _EPS_M)
        exit_position = rcs.at_route_distance(segment.end_s_m - _EPS_M)
        assert entry.edge_id == segment.edge_id, (entry.edge_id, segment.edge_id)
        assert exit_position.edge_id == segment.edge_id, (exit_position.edge_id, segment.edge_id)
        endpoints[segment.edge_id] = (entry.chainage_km, exit_position.chainage_km)
    return endpoints


def _section_tokens(heading: str) -> tuple[str, ...]:
    """Return the token list of one ``docs/SECTION_D_PATTERNS.md`` section."""
    text = _SECTION_D_PATTERNS.read_text(encoding="utf-8")
    start = text.index(heading)
    end = text.index("\n## ", start + 1)
    body = text[start:end].split("\n", 1)[1]
    paragraph = body.strip().split("\n\n", 1)[0]
    return tuple(re.findall(r"`([^`]+)`", paragraph))


# ---------------------------------------------------------------------------
# P4-001 ... P4-010 - the compiled network of the reference project
# ---------------------------------------------------------------------------
def test_p4_001_compiled_network_from_reference_project():
    """TEST P4-001 - compile the reference network without touching the project."""
    assert _PROTECTED_GRR01.exists(), "the protected reference project must be present"
    file_before = _protected_file_sha256()
    assert file_before == PROTECTED_GRR01_SHA256

    on_disk = import_project_from_file(_PROTECTED_GRR01)
    assert on_disk.ok, on_disk.status_text
    assert document_hash(to_normalized_dict(on_disk.project)) == CANONICAL_GRR01_HASH

    document = _grr_document()
    project = _load(document)
    assert document_hash(to_normalized_dict(_load(_grr_document(declare_paths=False)))) == (
        CANONICAL_GRR01_HASH
    )
    before = to_normalized_dict(project)

    network = compile_network(project)
    assert isinstance(network, CompiledNetwork)
    assert len(network.edge_ids) == 59, "the reference project has 59 physical tracks"
    assert network.track("TR-C-P2") is not None
    assert network.track("TR-NOT-A-TRACK") is None
    assert network.node("N-ALP-W") is not None
    assert network.node("N-NOT-A-NODE") is None
    assert network.diagnostics == ()

    assert to_normalized_dict(project) == before, "compiling must not write to the project"
    assert document_hash(to_normalized_dict(project)) == document_hash(before)
    assert _protected_file_sha256() == file_before == PROTECTED_GRR01_SHA256


def test_p4_002_declared_paths_are_read_exactly_as_declared():
    """TEST P4-002 - the network reads exactly the train paths the project declares."""
    network = _grr_network()
    assert network.path_ids == (TEST_CORRIDOR_A_D_ID, TEST_CORRIDOR_D_A_ID)

    forward = network.declared_edges(TEST_CORRIDOR_A_D_ID)
    assert len(forward) == len(TEST_CORRIDOR_EDGE_IDS) == 15
    assert tuple(ref.edge_id for ref in forward) == TEST_CORRIDOR_EDGE_IDS
    assert tuple(ref.index for ref in forward) == tuple(range(15))
    assert {ref.traversal for ref in forward} == {EdgeTraversal.WITH_EDGE}

    reverse = network.declared_edges(TEST_CORRIDOR_D_A_ID)
    assert tuple(ref.edge_id for ref in reverse) == tuple(reversed(TEST_CORRIDOR_EDGE_IDS))
    assert {ref.traversal for ref in reverse} == {EdgeTraversal.AGAINST_EDGE}
    assert network.declared_edges("NOT-DECLARED") == ()
    assert network.diagnostics_for("NOT-DECLARED") == ()


def test_p4_003_forward_follows_the_declared_traversal():
    """TEST P4-003 - FORWARD uses the declared traversal; s runs 0 -> L_F."""
    rcs = _grr_network().route(TEST_CORRIDOR_A_D_ID)
    assert rcs.direction is Direction.FORWARD
    assert rcs.path_id == TEST_CORRIDOR_A_D_ID
    assert rcs.route_length_m == pytest.approx(TEST_CORRIDOR_LENGTH_M, abs=1e-6)
    assert rcs.edge_ids() == TEST_CORRIDOR_EDGE_IDS
    assert {segment.traversal for segment in rcs.segments} == {EdgeTraversal.WITH_EDGE}
    starts = [segment.start_s_m for segment in rcs.segments]
    assert starts[0] == 0.0
    assert all(later > earlier for earlier, later in zip(starts, starts[1:]))

    origin = rcs.at_route_distance(0.0)
    assert origin.edge_id == TEST_CORRIDOR_EDGE_IDS[0]
    assert origin.traversal is EdgeTraversal.WITH_EDGE
    assert origin.local_position_m == pytest.approx(0.0, abs=POSITION_TOLERANCE_M)
    assert origin.chainage_km == pytest.approx(0.0, abs=CHAINAGE_TOLERANCE_KM)

    terminus = rcs.at_route_distance(rcs.route_length_m)
    assert terminus.edge_id == TEST_CORRIDOR_EDGE_IDS[-1]
    assert terminus.local_position_m == pytest.approx(1400.0, abs=POSITION_TOLERANCE_M)
    assert terminus.chainage_km == pytest.approx(49.0, abs=CHAINAGE_TOLERANCE_KM)

    chainages = [rcs.at_route_distance(s).chainage_km for s in range(0, 49001, 500)]
    assert all(later >= earlier for earlier, later in zip(chainages, chainages[1:]))


def test_p4_004_reverse_reverses_order_and_complements_traversal():
    """TEST P4-004 - REVERSE: same physical edges, reversed order, complementary traversal."""
    network = _grr_network()
    reverse = network.route(TEST_CORRIDOR_A_D_ID, Direction.REVERSE)
    assert reverse.direction is Direction.REVERSE
    assert reverse.path_id == TEST_CORRIDOR_A_D_ID
    assert reverse.edge_ids() == tuple(reversed(TEST_CORRIDOR_EDGE_IDS))
    assert {segment.traversal for segment in reverse.segments} == {EdgeTraversal.AGAINST_EDGE}
    assert reverse.route_length_m == pytest.approx(TEST_CORRIDOR_LENGTH_M, abs=1e-6)
    assert set(reverse.edge_ids()) == set(TEST_CORRIDOR_EDGE_IDS), "same physical edges"

    origin = reverse.at_route_distance(0.0)
    assert origin.edge_id == TEST_CORRIDOR_EDGE_IDS[-1]
    assert origin.local_position_m == pytest.approx(1400.0, abs=POSITION_TOLERANCE_M)
    assert origin.chainage_km == pytest.approx(49.0, abs=CHAINAGE_TOLERANCE_KM)
    terminus = reverse.at_route_distance(reverse.route_length_m)
    assert terminus.edge_id == TEST_CORRIDOR_EDGE_IDS[0]
    assert terminus.local_position_m == pytest.approx(0.0, abs=POSITION_TOLERANCE_M)
    assert terminus.chainage_km == pytest.approx(0.0, abs=CHAINAGE_TOLERANCE_KM)

    # the declared reverse path compiles to the same two route systems
    declared_reverse = network.route(TEST_CORRIDOR_D_A_ID, Direction.FORWARD)
    assert declared_reverse.edge_ids() == reverse.edge_ids()
    assert [segment.traversal for segment in declared_reverse.segments] == [
        segment.traversal for segment in reverse.segments
    ]
    declared_forward_again = network.route(TEST_CORRIDOR_D_A_ID, Direction.REVERSE)
    assert declared_forward_again.edge_ids() == TEST_CORRIDOR_EDGE_IDS
    assert declared_forward_again.route_length_m == reverse.route_length_m


def test_p4_005_both_directions_use_the_declared_chainage_maps():
    """TEST P4-005 - both directions resolve the same chainage_map values per edge."""
    network = _grr_network()
    tracks = {edge_id: network.track(edge_id) for edge_id in TEST_CORRIDOR_EDGE_IDS}
    assert all(track is not None for track in tracks.values())

    forward = _chainage_endpoints(network.route(TEST_CORRIDOR_A_D_ID, Direction.FORWARD))
    reverse = _chainage_endpoints(network.route(TEST_CORRIDOR_A_D_ID, Direction.REVERSE))
    assert set(forward) == set(reverse) == set(TEST_CORRIDOR_EDGE_IDS)

    for edge_id, track in tracks.items():
        declared_start = float(track.chainage_map.start_km)
        declared_end = float(track.chainage_map.end_km)
        forward_entry, forward_exit = forward[edge_id]
        reverse_entry, reverse_exit = reverse[edge_id]
        assert forward_entry == pytest.approx(declared_start, abs=1e-6), edge_id
        assert forward_exit == pytest.approx(declared_end, abs=1e-6), edge_id
        assert reverse_entry == pytest.approx(declared_end, abs=1e-6), edge_id
        assert reverse_exit == pytest.approx(declared_start, abs=1e-6), edge_id
        # the two directions expose the same pair of chainage_map values
        assert {round(forward_entry, 9), round(forward_exit, 9)} == {
            round(reverse_entry, 9),
            round(reverse_exit, 9),
        }, edge_id


def test_p4_006_track_identity_is_authoritative_and_chainage_is_derived():
    """TEST P4-006 - (edge_id, local_position_m) identifies the position; chainage is mapped."""
    network = _grr_network()
    for direction in (Direction.FORWARD, Direction.REVERSE):
        rcs = network.route(TEST_CORRIDOR_A_D_ID, direction)
        for segment in rcs.segments:
            for s_m in (
                segment.start_s_m + _EPS_M,
                segment.start_s_m + segment.length_m / 2.0,
                segment.end_s_m - _EPS_M,
            ):
                position = rcs.at_route_distance(s_m)
                assert position.edge_id == segment.edge_id
                assert position.traversal is segment.traversal
                assert 0.0 <= position.local_position_m <= segment.length_m + POSITION_TOLERANCE_M
                track = network.track(position.edge_id)
                derived = edge_position_to_chainage(track, position.local_position_m)
                assert position.chainage_km == pytest.approx(derived, abs=1e-12)
                if segment.traversal is EdgeTraversal.WITH_EDGE:
                    assert position.local_position_m == pytest.approx(s_m - segment.start_s_m, abs=1e-9)
                else:
                    assert position.local_position_m == pytest.approx(
                        segment.length_m - (s_m - segment.start_s_m), abs=1e-9
                    )


def test_p4_007_route_distance_is_bounded_and_never_negative():
    """TEST P4-007 - s is bounded to [0, route_length]; outside values are refused."""
    rcs = _grr_network().route(TEST_CORRIDOR_A_D_ID)
    total = rcs.route_length_m

    assert rcs.at_route_distance(0.0).local_position_m == pytest.approx(0.0)
    assert rcs.at_route_distance(total).edge_id == TEST_CORRIDOR_EDGE_IDS[-1]
    assert rcs.at_route_distance(-POSITION_TOLERANCE_M).local_position_m == pytest.approx(0.0)
    assert rcs.at_route_distance(total + POSITION_TOLERANCE_M).edge_id == TEST_CORRIDOR_EDGE_IDS[-1]

    for outside in (-1.0, total + 1.0, 1e9):
        with pytest.raises(RouteCoordinateError) as excinfo:
            rcs.at_route_distance(outside)
        assert "outside the route" in str(excinfo.value)

    assert rcs.route_length_m == total, "a refused query must not change the system"


def test_p4_008_edge_at_resolves_every_segment_in_travel_order():
    """TEST P4-008 - edge_at() resolves each segment and stays in travel order."""
    for direction in (Direction.FORWARD, Direction.REVERSE):
        rcs = _grr_network().route(TEST_CORRIDOR_D_A_ID, direction)
        assert rcs.edge_at(0.0) == rcs.edge_ids()[0]
        assert rcs.edge_at(rcs.route_length_m) == rcs.edge_ids()[-1]
        for segment in rcs.segments:
            assert rcs.edge_at(segment.start_s_m + _EPS_M) == segment.edge_id
            assert rcs.edge_at(segment.end_s_m - _EPS_M) == segment.edge_id
        sampled = [rcs.edge_at(s) for s in range(0, int(rcs.route_length_m) + 1, 250)]
        assert set(sampled) <= set(rcs.edge_ids())
        order = {edge_id: index for index, edge_id in enumerate(rcs.edge_ids())}
        indices = [order[edge_id] for edge_id in sampled]
        assert all(later >= earlier for earlier, later in zip(indices, indices[1:]))


def test_p4_009_chainage_to_route_distance_round_trips():
    """TEST P4-009 - chainage -> s -> chainage round-trips on the reference path."""
    rcs = _grr_network().route(TEST_CORRIDOR_A_D_ID)
    samples = [0.0, 1.0, 100.0, 5000.0, 24500.0, 48000.0, rcs.route_length_m]
    samples.extend(
        segment.start_s_m + segment.length_m / 2.0 for segment in rcs.segments
    )
    for s_m in samples:
        position = rcs.at_route_distance(s_m)
        returned = rcs.chainage_to_route_distance(position.chainage_km)
        assert returned == pytest.approx(s_m, abs=1e-6), position.describe()

    reverse = _grr_network().route(TEST_CORRIDOR_A_D_ID, Direction.REVERSE)
    for s_m in (0.0, 1000.0, 24500.0, reverse.route_length_m):
        position = reverse.at_route_distance(s_m)
        assert reverse.chainage_to_route_distance(position.chainage_km) == pytest.approx(
            s_m, abs=1e-6
        )


def test_p4_010_chainage_off_the_path_is_refused_not_invented():
    """TEST P4-010 - a chainage that is not on the path is refused, never fabricated."""
    rcs = _grr_network().route(TEST_CORRIDOR_A_D_ID)
    for chainage_km in (60.0, -5.0):
        with pytest.raises(RouteCoordinateError) as excinfo:
            rcs.chainage_to_route_distance(chainage_km)
        error = excinfo.value
        assert "not on the route" in str(error)
        assert error.diagnostic is not None
        assert error.diagnostic.code == "VAL-REGISTRY-003"
        assert error.diagnostic.severity is Severity.INFO
        assert error.diagnostic.category is DiagnosticCategory.REGISTRY
        assert error.diagnostic.object_id == TEST_CORRIDOR_A_D_ID
        assert error.diagnostic.context["chainage_km"] == pytest.approx(chainage_km)

    fixture = _fixture_network().route(FIXTURE_PATH_ID)
    with pytest.raises(RouteCoordinateError):
        fixture.chainage_to_route_distance(99.0)


# ---------------------------------------------------------------------------
# P4-011 ... P4-013 - the synthetic fixture (D6)
# ---------------------------------------------------------------------------
def test_p4_011_fixture_forward_and_reverse_run_zero_to_route_length():
    """TEST P4-011 - the fixture runs 0 -> L_F forward and 0 -> L_R reverse."""
    document = _fixture_document(_clean_paths())
    project = _load(document)
    before = copy.deepcopy(to_normalized_dict(project))
    network = compile_network(project)

    forward = network.route(FIXTURE_PATH_ID, Direction.FORWARD)
    reverse = network.route(FIXTURE_PATH_ID, Direction.REVERSE)
    assert forward.route_length_m == pytest.approx(FIXTURE_ROUTE_LENGTH_M, abs=1e-6)
    assert reverse.route_length_m == pytest.approx(FIXTURE_ROUTE_LENGTH_M, abs=1e-6)
    assert forward.edge_ids() == FIXTURE_EDGE_ORDER
    assert reverse.edge_ids() == tuple(reversed(FIXTURE_EDGE_ORDER))
    assert forward.direction is Direction.FORWARD and reverse.direction is Direction.REVERSE

    assert forward.at_route_distance(0.0).chainage_km == pytest.approx(0.0, abs=1e-9)
    assert forward.at_route_distance(forward.route_length_m).chainage_km == pytest.approx(
        2.0, abs=1e-9
    )
    assert reverse.at_route_distance(0.0).chainage_km == pytest.approx(2.0, abs=1e-9)
    assert reverse.at_route_distance(reverse.route_length_m).chainage_km == pytest.approx(
        0.0, abs=1e-9
    )

    # the declared reverse path compiles to the same route as the forward path reversed
    declared = network.route(FIXTURE_REVERSE_PATH_ID, Direction.FORWARD)
    assert declared.edge_ids() == reverse.edge_ids()
    assert [segment.traversal for segment in declared.segments] == [
        segment.traversal for segment in reverse.segments
    ]
    assert to_normalized_dict(project) == before


def test_p4_012_fixture_edge_longer_than_its_chainage_projection():
    """TEST P4-012 - route distance and chainage stay separate measures."""
    network = _fixture_network()
    rcs = network.route(FIXTURE_PATH_ID, Direction.FORWARD)
    segment = rcs.segments[1]
    assert segment.edge_id == "FX-E2"
    assert segment.length_m == pytest.approx(2650.0)

    entry = rcs.at_route_distance(segment.start_s_m + _EPS_M)
    exit_position = rcs.at_route_distance(segment.end_s_m - _EPS_M)
    chainage_advance_km = exit_position.chainage_km - entry.chainage_km
    assert chainage_advance_km == pytest.approx(2.0, abs=1e-6)
    assert segment.length_m - chainage_advance_km * 1000.0 == pytest.approx(650.0, abs=1e-3)
    assert segment.length_m != pytest.approx(chainage_advance_km * 1000.0)

    # the declared length_m is what the route distance advances by (no repair)
    assert rcs.edge_at(segment.start_s_m + 1.0) == "FX-E2"
    assert rcs.edge_at(segment.end_s_m - 1.0) == "FX-E2"
    assert not any("FX-E2" in (diagnostic.message or "") for diagnostic in network.diagnostics)


def test_p4_013_fixture_opposite_oriented_chainage_map_is_honoured():
    """TEST P4-013 - an opposite-oriented chainage_map is honoured, not repaired."""
    network = _fixture_network()
    rcs = network.route(FIXTURE_PATH_ID, Direction.FORWARD)
    segment = rcs.segments[2]
    assert segment.edge_id == "FX-E3"
    assert FIXTURE_CHAINAGE_MAPS_KM["FX-E3"] == (3.0, 2.0), "declared map start > end"

    with_edge = _chainage_endpoints(rcs)["FX-E3"]
    assert with_edge[0] == pytest.approx(3.0, abs=1e-6)
    assert with_edge[1] == pytest.approx(2.0, abs=1e-6)
    assert with_edge[1] < with_edge[0], "the declared map governs: chainage decreases"

    reverse = network.route(FIXTURE_PATH_ID, Direction.REVERSE)
    against_edge = _chainage_endpoints(reverse)["FX-E3"]
    assert against_edge[0] == pytest.approx(2.0, abs=1e-6)
    assert against_edge[1] == pytest.approx(3.0, abs=1e-6)
    assert reverse.segments[0].traversal is EdgeTraversal.AGAINST_EDGE
    assert reverse.segments[0].length_m == pytest.approx(1000.0)

    # the chainage of the node shared by FX-E2 and FX-E3 resolves to the same s,
    # although the turned-around map puts 2.500 km on two segments: the documented
    # rule is the first match in travel order, and (edge_id, local_position_m)
    # remains authoritative.
    assert rcs.chainage_to_route_distance(3.0) == pytest.approx(3650.0, abs=1e-6)
    assert rcs.chainage_to_route_distance(2.5) == pytest.approx(2987.5, abs=1e-6)
    assert rcs.edge_at(rcs.chainage_to_route_distance(2.5)) == "FX-E2"

    # the declared map itself is untouched and no diagnostic was raised for it
    layer = _fixture_document(_clean_paths())["infrastructure"][0]
    declared = {track["id"]: track["chainage_map"] for track in layer["tracks"]}
    assert declared["FX-E3"] == {"mode": "LINEAR", "start_km": 3.0, "end_km": 2.0}
    assert network.diagnostics == ()


# ---------------------------------------------------------------------------
# P4-014 ... P4-016 - read-only compilation (D4) and the coordinate contract
# ---------------------------------------------------------------------------
def test_p4_014_compiling_and_routing_never_write():
    """TEST P4-014 - FORWARD/REVERSE write neither the project, the file nor the hash."""
    file_before = _protected_file_sha256()
    document = _grr_document()
    project = _load(document)
    normalized_before = copy.deepcopy(to_normalized_dict(project))
    hash_before = document_hash(normalized_before)
    declared_before = copy.deepcopy(document["train_paths"]["paths"])

    for _ in range(2):
        network = compile_network(project)
        for path_id in (TEST_CORRIDOR_A_D_ID, TEST_CORRIDOR_D_A_ID):
            for direction in (Direction.FORWARD, Direction.REVERSE):
                rcs = network.route(path_id, direction)
                rcs.at_route_distance(rcs.route_length_m / 2.0)
                rcs.edge_at(1234.5)
                rcs.chainage_to_route_distance(10.0)
        assert network.path_ids == (TEST_CORRIDOR_A_D_ID, TEST_CORRIDOR_D_A_ID)

    assert to_normalized_dict(project) == normalized_before, "the project was written"
    assert document_hash(to_normalized_dict(project)) == hash_before
    assert document_hash(to_normalized_dict(_load(_grr_document(declare_paths=False)))) == (
        CANONICAL_GRR01_HASH
    ), "the reference project data itself is unchanged"
    assert document["train_paths"]["paths"] == declared_before, "the document was written"
    assert _protected_file_sha256() == file_before == PROTECTED_GRR01_SHA256

    # cached dictionaries of the compiled network are not mutated by routing either
    network = compile_network(project)
    declared_edges = network.declared_edges(TEST_CORRIDOR_A_D_ID)
    network.route(TEST_CORRIDOR_A_D_ID, Direction.REVERSE)
    assert network.declared_edges(TEST_CORRIDOR_A_D_ID) == declared_edges


def test_p4_015_compiled_network_and_coordinates_are_read_only():
    """TEST P4-015 - one compilation per run; the coordinate systems are read-only."""
    network = _grr_network()
    rcs = network.route(TEST_CORRIDOR_A_D_ID)
    assert isinstance(rcs, RouteCoordinateSystem)

    with pytest.raises(AttributeError):
        rcs.route_length_m = 1.0
    with pytest.raises(AttributeError):
        rcs.segments = ()
    with pytest.raises(AttributeError):
        rcs.direction = Direction.REVERSE
    with pytest.raises(dataclasses.FrozenInstanceError):
        rcs.segments[0].edge_id = "TR-NOT-A-TRACK"
    with pytest.raises(dataclasses.FrozenInstanceError):
        rcs.at_route_distance(0.0).chainage_km = 0.0
    assert isinstance(rcs.segments, tuple)
    assert isinstance(network.declared_edges(TEST_CORRIDOR_A_D_ID), tuple)
    assert isinstance(network.path_ids, tuple)
    assert rcs.diagnostics == network.diagnostics_for(TEST_CORRIDOR_A_D_ID)

    again = network.route(TEST_CORRIDOR_A_D_ID)
    assert again is not rcs, "each route() call returns its own read-only system"
    assert again.edge_ids() == rcs.edge_ids()
    assert again.route_length_m == rcs.route_length_m
    assert again.at_route_distance(0.0) == rcs.at_route_distance(0.0)


def test_p4_016_route_system_carries_no_direction_flag_or_negative_s():
    """TEST P4-016 - the direction is a property of the system, s never goes negative."""
    assert [field.name for field in dataclasses.fields(RouteSegment)] == [
        "edge_id",
        "traversal",
        "start_s_m",
        "length_m",
    ]
    assert [field.name for field in dataclasses.fields(RoutePosition)] == [
        "edge_id",
        "traversal",
        "local_position_m",
        "chainage_km",
    ]
    assert not any(
        "direction" in field.name or "sign" in field.name
        for field in dataclasses.fields(RouteSegment) + dataclasses.fields(RoutePosition)
    )
    assert not dataclasses.is_dataclass(RouteCoordinateSystem)

    network = _grr_network()
    forward = network.route(TEST_CORRIDOR_A_D_ID)
    reverse = network.route(TEST_CORRIDOR_A_D_ID, Direction.REVERSE)
    assert all(name.startswith("_") for name in vars(forward)), "the system keeps private state only"
    assert forward.direction is Direction.FORWARD
    assert reverse.direction is Direction.REVERSE
    assert forward.route_length_m == reverse.route_length_m
    for rcs in (forward, reverse):
        starts = [segment.start_s_m for segment in rcs.segments]
        assert starts[0] == 0.0
        assert all(start >= 0.0 for start in starts)
        assert all(later > earlier for earlier, later in zip(starts, starts[1:]))
        assert all(
            rcs.at_route_distance(s_m).local_position_m >= 0.0
            for s_m in range(0, int(rcs.route_length_m) + 1, 1000)
        )

    assert normalize_direction("forward") is Direction.FORWARD
    assert normalize_direction(Direction.REVERSE) is Direction.REVERSE
    assert normalize_direction(" REVERSE ") is Direction.REVERSE
    assert normalize_direction("SIDEWAYS") is None
    assert normalize_direction(None) is None


# ---------------------------------------------------------------------------
# P4-017 ... P4-020 - D5 diagnostics: reported, never repaired
# ---------------------------------------------------------------------------
def test_p4_017_unresolved_edge_is_reported_and_the_path_is_refused():
    """TEST P4-017 - an unresolved edge_id is reported (VAL-REGISTRY-003) and refused."""
    network = _fixture_network(_defect_paths())
    diagnostics = network.diagnostics_for("FX-UNKNOWN")
    assert [diagnostic.code for diagnostic in diagnostics] == ["VAL-REGISTRY-003"]
    finding = diagnostics[0]
    assert finding.severity is Severity.ERROR
    assert finding.category is DiagnosticCategory.REGISTRY
    assert finding.context["edge_id"] == "FX-NOPE"
    assert finding.object_id == "FX-UNKNOWN"

    refs = network.declared_edges("FX-UNKNOWN")
    assert [ref.edge_id for ref in refs] == ["FX-E1"], "the unusable entry is not replaced"
    with pytest.raises(RouteCoordinateError) as excinfo:
        network.route("FX-UNKNOWN")
    assert excinfo.value.diagnostic.code == "VAL-REGISTRY-003"
    assert "cannot be compiled" in str(excinfo.value)


def test_p4_018_sequence_break_is_reported_and_the_path_is_refused():
    """TEST P4-018 - a sequence break is reported (VAL-TOPO-007) and refused."""
    network = _fixture_network(_defect_paths())
    diagnostics = network.diagnostics_for("FX-GAP")
    assert [diagnostic.code for diagnostic in diagnostics] == ["VAL-TOPO-007"]
    finding = diagnostics[0]
    assert finding.severity is Severity.ERROR
    assert finding.category is DiagnosticCategory.TOPOLOGY
    assert "edge-sequence break" in finding.message
    assert "NX-C" in finding.message and "NX-B" in finding.message
    with pytest.raises(RouteCoordinateError) as excinfo:
        network.route("FX-GAP")
    assert excinfo.value.diagnostic.code == "VAL-TOPO-007"

    # continuity is decided in train order, not by the stored orientation: a legal
    # reversal move (WITH_EDGE then AGAINST_EDGE at the shared node) compiles here,
    # while the stored-orientation sequence check would call it a break.
    document = _grr_document(declare_paths=False)
    document["train_paths"]["paths"] = [
        {
            "id": REVERSAL_MOVE_PATH_ID,
            "edges": [
                {"edge_id": REVERSAL_MOVE_EDGE_IDS[0], "traversal": "WITH_EDGE"},
                {"edge_id": REVERSAL_MOVE_EDGE_IDS[1], "traversal": "AGAINST_EDGE"},
            ],
        }
    ]
    network = compile_network(_load(document))
    assert network.diagnostics == ()
    rcs = network.route(REVERSAL_MOVE_PATH_ID)
    assert rcs.edge_ids() == REVERSAL_MOVE_EDGE_IDS
    assert [segment.traversal for segment in rcs.segments] == [
        EdgeTraversal.WITH_EDGE,
        EdgeTraversal.AGAINST_EDGE,
    ]
    assert rcs.route_length_m == pytest.approx(REVERSAL_MOVE_LENGTH_M, abs=1e-6)

    compiled = compile_infrastructure(document["infrastructure"])
    topology = InfrastructureTopology.from_objects(
        compiled.by_id("nodes").values(), compiled.by_id("tracks").values()
    )
    assert topology.check_edge_sequence(REVERSAL_MOVE_EDGE_IDS).is_continuous is False
    assert topology.check_undirected_sequence(REVERSAL_MOVE_EDGE_IDS).is_continuous is True


def test_p4_019_declared_traversal_and_direction_values_are_validated():
    """TEST P4-019 - an unusable traversal (VAL-ENUM-001) or direction (VAL-DIR-001) is reported."""
    network = _fixture_network(_defect_paths())
    diagnostics = network.diagnostics_for("FX-BADTRAV")
    assert [diagnostic.code for diagnostic in diagnostics] == ["VAL-ENUM-001"]
    finding = diagnostics[0]
    assert finding.severity is Severity.ERROR
    assert finding.category is DiagnosticCategory.ENUM
    assert finding.context["traversal"] == "SIDEWAYS"
    assert finding.context["index"] == 0
    with pytest.raises(RouteCoordinateError) as excinfo:
        network.route("FX-BADTRAV")
    assert excinfo.value.diagnostic.code == "VAL-ENUM-001"

    clean = _fixture_network()
    for direction in ("SIDEWAYS", None, "", 1):
        with pytest.raises(RouteCoordinateError) as excinfo:
            clean.route(FIXTURE_PATH_ID, direction)
        assert excinfo.value.diagnostic.code == "VAL-DIR-001"
        assert excinfo.value.diagnostic.severity is Severity.ERROR
        assert excinfo.value.diagnostic.category is DiagnosticCategory.DIR

    with pytest.raises(RouteCoordinateError) as excinfo:
        clean.route("NOT-DECLARED")
    assert excinfo.value.diagnostic.code == "VAL-REGISTRY-003"
    assert excinfo.value.diagnostic.severity is Severity.ERROR
    assert excinfo.value.diagnostic.context["declared_path_ids"] == list(clean.path_ids)


def test_p4_020_missing_ids_and_empty_sequences_are_reported():
    """TEST P4-020 - missing/duplicate ids and empty sequences are reported, never repaired."""
    network = _fixture_network(_defect_paths())

    missing = network.diagnostics_for("FX-NOID")
    assert [diagnostic.code for diagnostic in missing] == ["VAL-ID-002"]
    assert missing[0].severity is Severity.ERROR
    assert missing[0].context["edge_id"] is None
    with pytest.raises(RouteCoordinateError) as excinfo:
        network.route("FX-NOID")
    assert excinfo.value.diagnostic.code == "VAL-ID-002"

    empty = [d for d in network.diagnostics if d.object_id == "FX-EMPTY"]
    assert [diagnostic.code for diagnostic in empty] == ["VAL-TOPO-007"]
    assert "FX-EMPTY" not in network.path_ids, "an empty sequence is not registered"
    with pytest.raises(RouteCoordinateError) as excinfo:
        network.route("FX-EMPTY")
    assert excinfo.value.diagnostic.code == "VAL-REGISTRY-003"

    duplicate = network.diagnostics_for(FIXTURE_PATH_ID)
    assert [diagnostic.code for diagnostic in duplicate] == ["VAL-ID-001"]
    assert duplicate[0].severity is Severity.ERROR
    assert duplicate[0].category is DiagnosticCategory.ID
    with pytest.raises(RouteCoordinateError) as excinfo:
        network.route(FIXTURE_PATH_ID)
    assert excinfo.value.diagnostic.code == "VAL-ID-001"


# ---------------------------------------------------------------------------
# P4-021 ... P4-022 - scope and dependency guards
# ---------------------------------------------------------------------------
def test_p4_021_network_module_stays_outside_the_out_of_scope_patterns():
    """TEST P4-021 - the new module carries no Section-D pattern (S1 names, S3 public names)."""
    assert _NETWORK_MODULE.exists(), "the Phase-4A module must exist"
    module = importlib.import_module("railway_headway_sim.infrastructure.compiled_network")

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

    tree = ast.parse(_NETWORK_MODULE.read_text(encoding="utf-8"))
    declared_names = [
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    ]
    assert declared_names, "the scan must look at a populated module"
    offending_names = sorted(
        {
            name
            for name in declared_names
            for token in s1_tokens
            if token in name.lower()
        }
    )
    assert offending_names == [], f"S1 names present: {offending_names}"

    public_names = [name for name in dir(module) if not name.startswith("_")]
    offending_public = sorted(
        {name for name in public_names for token in s3_tokens if token in name.lower()}
    )
    assert offending_public == [], f"S3 public names present: {offending_public}"

    field_names = [
        field.name
        for cls in (RoutePosition, RouteSegment)
        for field in dataclasses.fields(cls)
    ]
    offending_fields = sorted(
        {name for name in field_names for token in s1_tokens + s3_tokens if token in name.lower()}
    )
    assert offending_fields == [], f"forbidden field names present: {offending_fields}"

    docstring = module.__doc__ or ""
    assert "Phase 4A" in docstring
    assert "no force, no speed, no time" in docstring, "the module states its own scope"


def test_p4_022_network_module_has_no_new_dependencies_and_no_cycle():
    """TEST P4-022 - no numeric dependency, no validation facade import, no cycle."""
    tree = ast.parse(_NETWORK_MODULE.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            imported.add("." * node.level + (node.module or ""))
        elif isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
    assert imported == {
        "__future__",
        "dataclasses",
        "json",
        "pathlib",
        "typing",
        "..models.diagnostics",
        "..models.enums",
        "..models.infrastructure",
        "..validation",
        ".compiler",
        ".mapping",
        ".topology",
    }, f"unexpected import surface: {sorted(imported)}"
    assert not {"numpy", "scipy", "pandas", "math", "statistics", "random"} & imported

    validation_imports = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and (node.module or "") == "validation"
    ]
    assert len(validation_imports) == 1, "the module may touch the validation package once"
    assert [alias.name for alias in validation_imports[0].names] == ["codes"], (
        "only the diagnostic-code catalogue may be imported; the validation facade "
        "(validators, result model) must not be"
    )

    facade = importlib.import_module("railway_headway_sim.infrastructure")
    for name in (
        "CompiledNetwork",
        "RouteCoordinateSystem",
        "RoutePosition",
        "RouteSegment",
        "PathEdgeRef",
        "RouteCoordinateError",
        "compile_network",
        "complementary_traversal",
        "normalize_direction",
        "DECLARED_TRAVERSALS",
        "SUPPORTED_DIRECTIONS",
    ):
        assert hasattr(facade, name), name
        assert name in facade.__all__, name

    # no validation <-> infrastructure cycle: the validation package never names the
    # compiled-network module, so the dependency runs one way only (validation ->
    # infrastructure.compiler), and both packages import cleanly in this process.
    validation_sources = sorted((_REPO_ROOT / "railway_headway_sim" / "validation").rglob("*.py"))
    assert validation_sources, "the validation package must exist"
    for path in validation_sources:
        validation_tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(validation_tree):
            if isinstance(node, ast.ImportFrom):
                target = "." * node.level + (node.module or "")
                assert "compiled_network" not in target, (path.name, target)
            elif isinstance(node, ast.Import):
                assert not any("compiled_network" in alias.name for alias in node.names), path.name
    assert importlib.import_module("railway_headway_sim.validation") is not None
    assert importlib.import_module("railway_headway_sim.infrastructure") is not None
    assert sys.modules["railway_headway_sim.infrastructure.compiled_network"] is not None


# ---------------------------------------------------------------------------
# P4-023 ... P4-030 - the declared-paths companion file (Phase-4A corrections)
# ---------------------------------------------------------------------------
def _companion_document() -> dict[str, Any]:
    """Return the companion declared-paths document as data (C1)."""
    path = _REPO_ROOT / REFERENCE_PATHS_FILE
    assert path.is_file(), f"{REFERENCE_PATHS_FILE} must exist"
    return json.loads(path.read_text(encoding="utf-8"))


def _reference_network() -> CompiledNetwork:
    """Compile the reference project with the companion file's declared paths."""
    project = _load(_grr_document(declare_paths=False))
    return compile_network(project, paths_source=(_REPO_ROOT / REFERENCE_PATHS_FILE).read_text(encoding="utf-8"))


def _platform_edge(layer: dict[str, Any], platform_id: str) -> str:
    """Return the track id of a platform, read from the project's own record."""
    platform = next(item for item in layer["platforms"] if item["id"] == platform_id)
    return platform["track_id"]


def _observation(layer: dict[str, Any], observation_id: str) -> dict[str, Any]:
    """Return one observation point of the project's own record."""
    return next(item for item in layer["observation_points"] if item["id"] == observation_id)


def _derived_start_node(edge_ids: tuple[str, ...], tracks: dict[str, dict[str, Any]]) -> str:
    """Derive the start node of an edge walk from the project's own endpoints."""
    first, second = tracks[edge_ids[0]], tracks[edge_ids[1]]
    shared = {first["from_node"], first["to_node"]} & {second["from_node"], second["to_node"]}
    assert len(shared) == 1, "two consecutive edges must share exactly one topology node"
    endpoints_start = {first["from_node"], first["to_node"]} - shared
    assert len(endpoints_start) == 1
    return endpoints_start.pop()


def _derived_traversals(
    edge_ids: tuple[str, ...], start_node: str, tracks: dict[str, dict[str, Any]]
) -> list[str]:
    """Derive every traversal of an edge walk from the project's own endpoints."""
    traversals: list[str] = []
    current = start_node
    for edge_id in edge_ids:
        track = tracks[edge_id]
        if track["from_node"] == current:
            traversals.append("WITH_EDGE")
            current = track["to_node"]
        else:
            assert track["to_node"] == current, (edge_id, current)
            traversals.append("AGAINST_EDGE")
            current = track["from_node"]
    return traversals


def _nodes_of(network: CompiledNetwork, rcs: RouteCoordinateSystem) -> list[str]:
    """Return the node sequence a compiled route passes through."""
    nodes: list[str] = []
    for segment in rcs.segments:
        entry = network.entry_node(segment.edge_id, segment.traversal)
        if not nodes:
            nodes.append(entry)
        nodes.append(network.exit_node(segment.edge_id, segment.traversal))
    return nodes


def test_p4_023_companion_file_declares_the_reference_paths():
    """TEST P4-023 - the companion file loads and declares exactly PATH-H1-F/PATH-H1-R."""
    companion_path = _REPO_ROOT / REFERENCE_PATHS_FILE
    assert companion_path.is_file(), f"{REFERENCE_PATHS_FILE} must exist"
    companion = _companion_document()
    assert companion["schema_version"] == "1.0"
    assert "infrastructure" not in companion, "the companion carries no infrastructure of its own"
    declared = [record["id"] for record in companion["train_paths"]["paths"]]
    assert declared == list(REFERENCE_PATH_IDS) == ["PATH-H1-F", "PATH-H1-R"]

    # the frozen project still declares no train path of its own, and is unchanged
    assert _protected_file_sha256() == PROTECTED_GRR01_SHA256
    document = _grr_document(declare_paths=False)
    assert document["train_paths"]["paths"] == []
    assert document_hash(to_normalized_dict(_load(document))) == CANONICAL_GRR01_HASH
    assert companion["project_file_sha256"] == PROTECTED_GRR01_SHA256
    assert companion["project_canonical_hash"] == CANONICAL_GRR01_HASH

    # the reader accepts the companion in all three documented forms, with no diagnostics
    text = companion_path.read_text(encoding="utf-8")
    project = _load(_grr_document(declare_paths=False))
    for label, source in (
        ("mapping", companion),
        ("json text", text),
        ("file path", companion_path),
    ):
        network = compile_network(project, paths_source=source)
        assert network.path_ids == REFERENCE_PATH_IDS, label
        assert network.diagnostics == (), label
        assert all(network.declared_edges(path_id) for path_id in REFERENCE_PATH_IDS), label

    # compiling without a source still reads only the project: it declares nothing here
    assert compile_network(project).path_ids == ()
    assert compile_network(project).diagnostics == ()

    # an unreadable source is reported, never silently ignored
    for bad in ("not json at all", {}, "examples/does-not-exist.json"):
        rejected = compile_network(project, paths_source=bad)
        assert rejected.path_ids == ()
        assert [d.code for d in rejected.diagnostics] == ["VAL-REGISTRY-003"]
        assert rejected.diagnostics[0].severity is Severity.ERROR

    # the companion ids are reserved service names and never collide with the test corridor
    assert set(REFERENCE_PATH_IDS).isdisjoint({TEST_CORRIDOR_A_D_ID, TEST_CORRIDOR_D_A_ID})
    assert all(path_id.startswith("PATH-") for path_id in REFERENCE_PATH_IDS)
    assert TEST_CORRIDOR_A_D_ID.startswith("TEST-CORRIDOR-")
    assert TEST_CORRIDOR_D_A_ID.startswith("TEST-CORRIDOR-")


def test_p4_024_reference_paths_run_platform_edge_to_platform_edge():
    """TEST P4-024 - PATH-H1-F/PATH-H1-R are the real terminal-to-terminal walks."""
    layer = _grr_document(declare_paths=False)["infrastructure"][0]
    tracks = {track["id"]: track for track in layer["tracks"]}
    network = _reference_network()
    assert network.path_ids == REFERENCE_PATH_IDS
    assert network.diagnostics == ()

    central_platform_edges = {
        _platform_edge(layer, platform["id"])
        for platform in layer["platforms"]
        if platform["station_id"] == "STA-CEN"
    }
    alpha_p1_edge = _platform_edge(layer, "PLT-ALP-P1")
    alpha_p2_edge = _platform_edge(layer, "PLT-ALP-P2")
    delta_p1_edge = _platform_edge(layer, "PLT-DEL-P1")
    companion = _companion_document()
    records = {record["id"]: record for record in companion["train_paths"]["paths"]}

    # the endpoints are the project's own declared reference origins/destination approaches
    forward_origin = _observation(layer, "OBS-REF-FWD-ORIGIN")
    reverse_origin = _observation(layer, "OBS-REF-REV-ORIGIN")
    reverse_destination_approach = _observation(layer, "OBS-REV-DEST-APP")
    assert forward_origin["platform_id"] == "PLT-ALP-P2"
    assert reverse_origin["platform_id"] == "PLT-DEL-P1"

    expectations = {
        "PATH-H1-F": (alpha_p2_edge, delta_p1_edge),
        "PATH-H1-R": (delta_p1_edge, alpha_p2_edge),
    }
    for path_id, (start_edge, end_edge) in expectations.items():
        declared = network.declared_edges(path_id)
        edge_ids = tuple(ref.edge_id for ref in declared)
        assert edge_ids[0] == start_edge, path_id
        assert edge_ids[-1] == end_edge, path_id
        assert central_platform_edges & set(edge_ids), f"{path_id} must run through Central"
        assert alpha_p1_edge not in edge_ids, "the rule selects the shorter Alpha P1/P2 lane"

        # every traversal is derived from the project's own track endpoints
        start_node = _derived_start_node(edge_ids, tracks)
        derived = _derived_traversals(edge_ids, start_node, tracks)
        assert [ref.traversal.value for ref in declared] == derived, path_id

        # the route runs 0 -> L along its own travel direction, length derived from the project
        rcs = network.route(path_id)
        expected_length_m = sum(tracks[edge_id]["length_m"] for edge_id in edge_ids)
        assert rcs.route_length_m == pytest.approx(expected_length_m, abs=1e-6)
        assert len(edge_ids) == records[path_id]["edge_count"]
        assert rcs.route_length_m == pytest.approx(
            records[path_id]["computed_length_m"], abs=1e-6
        )
        assert rcs.route_length_m > 0.0
        assert rcs.edge_ids() == edge_ids
        assert rcs.at_route_distance(0.0).edge_id == start_edge
        assert rcs.at_route_distance(rcs.route_length_m).edge_id == end_edge
        assert network.entry_node(start_edge, rcs.segments[0].traversal) is not None

        # this is a terminal-to-terminal walk, not the abbreviated test corridor
        assert rcs.edge_ids() != TEST_CORRIDOR_EDGE_IDS, path_id

        # the route is the same physical walk in both directions, and it never writes
        reverse = network.route(path_id, Direction.REVERSE)
        assert reverse.edge_ids() == tuple(reversed(edge_ids))
        assert reverse.route_length_m == rcs.route_length_m
        assert set(reverse.edge_ids()) == set(rcs.edge_ids())
    # the two paths are the two running orders of one physical corridor: each starts where the
    # declared reference origin of its direction says, and each ends on the other's start edge
    forward = network.route("PATH-H1-F")
    reverse = network.route("PATH-H1-R")
    assert forward.segments[0].edge_id == forward_origin["track_id"] == alpha_p2_edge
    assert forward.segments[-1].edge_id == reverse_origin["track_id"] == delta_p1_edge
    assert reverse.segments[0].edge_id == forward.segments[-1].edge_id
    assert reverse.segments[-1].edge_id == forward.segments[0].edge_id
    assert "N-DEL-THR" in _nodes_of(network, forward), "forward destination approach N-DEL-THR"
    assert "N-DEL-THR" in _nodes_of(network, reverse), "the reverse runs the same corridor"

    # the project also declares a reverse destination approach on the Alpha west ladder
    # (N-ALP-U1). The single-corridor selection rule starts and ends on the Alpha P2 platform
    # edge, so that observation point is a declared observation of the project, not a node of
    # the reference corridor: recorded here, not repaired in the frozen project.
    assert reverse_destination_approach["node_ids"] == ["N-ALP-U1"]
    assert "N-ALP-U1" not in _nodes_of(network, reverse)

    # the companion walks stay distinct from the test corridor and share one length
    assert forward.route_length_m != TEST_CORRIDOR_LENGTH_M
    assert reverse.route_length_m == forward.route_length_m
    assert forward.edge_ids() != TEST_CORRIDOR_EDGE_IDS
    assert reverse.edge_ids() != TEST_CORRIDOR_EDGE_IDS


def test_p4_025_test_corridor_keeps_the_original_49_km_walk():
    """TEST P4-025 - the renamed test-corridor paths keep their 49 000 m walk."""
    assert TEST_CORRIDOR_A_D_ID == "TEST-CORRIDOR-A-D"
    assert TEST_CORRIDOR_D_A_ID == "TEST-CORRIDOR-D-A"
    assert TEST_CORRIDOR_LENGTH_M == 49000.0
    network = _grr_network()
    assert network.path_ids == (TEST_CORRIDOR_A_D_ID, TEST_CORRIDOR_D_A_ID)

    forward = network.route(TEST_CORRIDOR_A_D_ID)
    assert forward.route_length_m == TEST_CORRIDOR_LENGTH_M
    assert forward.edge_ids() == TEST_CORRIDOR_EDGE_IDS
    assert forward.edge_ids()[0] == "TR-A-W-U1"
    assert forward.edge_ids()[-1] == "TR-D-P1"
    assert forward.at_route_distance(0.0).chainage_km == pytest.approx(0.0, abs=1e-9)
    assert forward.at_route_distance(forward.route_length_m).chainage_km == pytest.approx(
        49.0, abs=1e-9
    )

    reverse = network.route(TEST_CORRIDOR_D_A_ID)
    assert reverse.route_length_m == TEST_CORRIDOR_LENGTH_M
    assert reverse.edge_ids() == tuple(reversed(TEST_CORRIDOR_EDGE_IDS))
    assert reverse.at_route_distance(0.0).chainage_km == pytest.approx(49.0, abs=1e-9)
    assert reverse.at_route_distance(reverse.route_length_m).chainage_km == pytest.approx(
        0.0, abs=1e-9
    )

    # the corridor length is the sum of the project's own edge lengths (no new number)
    layer = _grr_document(declare_paths=False)["infrastructure"][0]
    tracks = {track["id"]: track for track in layer["tracks"]}
    assert sum(tracks[edge_id]["length_m"] for edge_id in TEST_CORRIDOR_EDGE_IDS) == (
        TEST_CORRIDOR_LENGTH_M
    )


def test_p4_026_app_phase_names_the_current_phase():
    """TEST P4-026 - APP_PHASE names the current phase and matches APP_VERSION."""
    from railway_headway_sim import version as version_module
    from railway_headway_sim.app.project_controller import ProjectController
    from railway_headway_sim.ui.formatting import header_html

    assert version_module.APP_VERSION == "0.9.0"
    assert version_module.get_app_version() == version_module.APP_VERSION
    assert version_module.SUPPORTED_PROJECT_SCHEMA_VERSIONS == ("1.0",)

    label = version_module.APP_PHASE
    assert "Phase 6B" in label, label
    assert "Phase 6A" not in label, "the label must not claim the previous phase"
    assert "Phase 7" not in label, "the label must not claim a stage the project has not reached"

    # the application reports the same version and shows the same label in its header
    controller = ProjectController()
    assert controller.state.app_version == version_module.APP_VERSION
    header = header_html(
        app_name=version_module.APP_NAME,
        phase_text=label,
        project_name="(no project loaded)",
        chips=[(f"APP v{version_module.APP_VERSION}", "navy")],
        status_text="VALIDATION: NOT YET VALIDATED",
        status_tone="muted",
        freshness_text="",
        freshness_tone="muted",
        direction_text="FORWARD",
    )
    assert label in header
    assert "APP v0.9.0" in header


# ---------------------------------------------------------------------------
# P4-027 ... P4-030 - the two declared paths are one corridor, run both ways
# (Phase-4A correction #2)
# ---------------------------------------------------------------------------
COMPLEMENTARY_TRAVERSAL = {"WITH_EDGE": "AGAINST_EDGE", "AGAINST_EDGE": "WITH_EDGE"}


def _companion_records() -> dict[str, dict[str, Any]]:
    """Return the companion's path records keyed by path id."""
    companion = _companion_document()
    return {record["id"]: record for record in companion["train_paths"]["paths"]}


def test_p4_027_reference_paths_are_entry_by_entry_reverses():
    """TEST P4-027 - PATH-H1-R is the exact reverse of PATH-H1-F, entry by entry."""
    records = _companion_records()
    forward_edges = records["PATH-H1-F"]["edges"]
    reverse_edges = records["PATH-H1-R"]["edges"]
    assert len(forward_edges) == len(reverse_edges) > 0
    assert sorted(entry["edge_id"] for entry in forward_edges) == sorted(
        entry["edge_id"] for entry in reverse_edges
    ), "the two paths must carry the same multiset of edge ids"

    for position, (forward_entry, reverse_entry) in enumerate(
        zip(forward_edges, reversed(reverse_edges))
    ):
        assert reverse_entry["edge_id"] == forward_entry["edge_id"], position
        assert (
            COMPLEMENTARY_TRAVERSAL[reverse_entry["traversal"]] == forward_entry["traversal"]
        ), position

    # the compiled network carries the same relation, read from the two ends inward
    network = _reference_network()
    assert network.diagnostics == ()
    forward = network.route("PATH-H1-F")
    reverse = network.route("PATH-H1-R")
    assert forward.edge_ids() == tuple(reversed(reverse.edge_ids()))
    assert [segment.traversal.value for segment in forward.segments] == [
        COMPLEMENTARY_TRAVERSAL[segment.traversal.value]
        for segment in reversed(reverse.segments)
    ]


def test_p4_028_reference_paths_share_length_and_swap_terminals():
    """TEST P4-028 - equal length (bit for bit), equal edge count, swapped terminals."""
    records = _companion_records()
    forward_record, reverse_record = records["PATH-H1-F"], records["PATH-H1-R"]
    assert forward_record["edge_count"] == reverse_record["edge_count"]
    assert forward_record["edge_count"] == len(forward_record["edges"]) == len(
        reverse_record["edges"]
    )
    assert forward_record["computed_length_m"] == reverse_record["computed_length_m"]
    assert forward_record["start_node"] == reverse_record["end_node"]
    assert forward_record["end_node"] == reverse_record["start_node"]

    network = _reference_network()
    forward = network.route("PATH-H1-F")
    reverse = network.route("PATH-H1-R")
    assert forward.route_length_m == reverse.route_length_m, "equal route length, bit for bit"
    assert forward.route_length_m == float(forward_record["computed_length_m"])
    assert len(forward.segments) == len(reverse.segments) == forward_record["edge_count"]
    assert forward.segments[0].edge_id == reverse.segments[-1].edge_id
    assert forward.segments[-1].edge_id == reverse.segments[0].edge_id

    # the declared terminal nodes are the project's own endpoints of those platform edges
    layer = _grr_document(declare_paths=False)["infrastructure"][0]
    tracks = {track["id"]: track for track in layer["tracks"]}
    forward_edge_ids = forward.edge_ids()
    assert _derived_start_node(forward_edge_ids, tracks) == forward_record["start_node"]
    assert (
        _derived_start_node(tuple(reversed(forward_edge_ids)), tracks)
        == reverse_record["start_node"]
    )


def test_p4_029_compiled_routes_traverse_the_same_edges_in_opposite_order():
    """TEST P4-029 - FORWARD of both paths is the same physical edge sequence, reversed."""
    network = _reference_network()
    forward = network.route("PATH-H1-F")
    reverse = network.route("PATH-H1-R")
    length_m = forward.route_length_m
    assert reverse.route_length_m == length_m

    def sampled(rcs: RouteCoordinateSystem) -> list[str]:
        """Sample every segment of a route at its own mid route distance."""
        return [
            rcs.edge_at(0.5 * (segment.start_s_m + segment.end_s_m))
            for segment in rcs.segments
        ]

    forward_samples = sampled(forward)
    reverse_samples = sampled(reverse)
    assert forward_samples == list(forward.edge_ids())
    assert forward_samples == list(reversed(reverse_samples))

    # and the same physical point carries the same edge in the mirrored route distance
    for segment in forward.segments:
        middle = 0.5 * (segment.start_s_m + segment.end_s_m)
        assert reverse.edge_at(length_m - middle) == forward.edge_at(middle)
    assert reverse.edge_at(0.0) == forward.edge_at(length_m) == forward.segments[-1].edge_id
    assert reverse.edge_at(length_m) == forward.edge_at(0.0) == forward.segments[0].edge_id


def test_p4_030_corrected_companion_compiles_without_diagnostics():
    """TEST P4-030 - no diagnostic is emitted for the corrected companion file."""
    network = _reference_network()
    assert network.diagnostics == ()
    for path_id in REFERENCE_PATH_IDS:
        assert network.diagnostics_for(path_id) == (), path_id
        declared = network.declared_edges(path_id)
        assert declared and all(ref.traversal is not None for ref in declared), path_id
        rcs = network.route(path_id)
        assert rcs.diagnostics == (), path_id
        assert rcs.route_length_m > 0.0, path_id

    # the same holds for the companion read as a mapping and as a file path
    project = _load(_grr_document(declare_paths=False))
    for source in (_companion_document(), _REPO_ROOT / REFERENCE_PATHS_FILE):
        other = compile_network(project, paths_source=source)
        assert other.path_ids == REFERENCE_PATH_IDS
        assert other.diagnostics == ()
