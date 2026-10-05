"""GRR-01 Part A reference project fixture (frozen engineering data, Phase 2).

This module is the **single auditable definition** of the GRR-01 Part-A physical
infrastructure. ``examples/GRR-01.json`` is generated from it, so the JSON, the
tests and the documentation cannot drift apart.

Content (all inside ONE infrastructure layer, ``layer.id = "LYR-MAIN"``):

===========================================  =====
alignment                                      1
track groups                                   2
horizontal geometry sections                   7
vertical profile points                       13
speed restrictions                             8
topology nodes                                50
physical track edges                          59
stations                                       4
platforms                                      9
stopping marks                                14
observation points                             9
===========================================  =====

The regional counts (nodes: Alpha 6 / Central 18 / XC-24 8 / Valley 12 / Delta 6;
edges: Open line 8 / Alpha 4 / Central 23 / XC-24 8 / Valley 12 / Delta 4) are
declared explicitly below so that regressions can be checked per region.

**No simulation results are contained here** - this is static physical setup
data plus static geometry benchmarks only.

Approved amendments
-------------------
``GRR-AMD-001`` - ``STOP-V-P1-R.position_m`` 220.0 -> 250.0 m (recorded in
``provenance.approved_amendments``; the un-amended values are preserved in
``docs/GRR-01_FROZEN_PHYSICAL_v1.0.json``).

``GRR-AMD-004`` - ``PLT-VAL-P2`` usable range recorded as 100.0 - 500.0 m so that the
frozen Valley P2 benchmark (eastern boundary 500.0 m, 98.0 m rear clearance) is
reproduced from platform data instead of a hard-coded constant.

``GRR-AMD-003`` - discovered while expanding the frozen inventory: a region with
6 nodes and 4 edges cannot be connected (a 6-node tree needs 5 edges), so the
Delta group's sixth node is attached by the open-line ML2 edge instead of adding
a Delta edge or removing a node. Object counts are unchanged (50 / 59); see
``docs/GRR-01 CHANGE CONTROL.md``.
"""

from __future__ import annotations

from typing import Any, Optional

from ..models.enums import EdgeTraversal
from .static_geometry import evaluate_static_footprint

# ---------------------------------------------------------------------------
# Static reference train lengths (fixture data only - NOT production physics)
# ---------------------------------------------------------------------------
HSR_REF_LENGTH_M = 202.0
REG_REF_LENGTH_M = 160.0

# ---------------------------------------------------------------------------
# Project metadata
# ---------------------------------------------------------------------------
GRR01_PROJECT_ID = "PRJ-GRR-01"
GRR01_PROJECT_NAME = "GRR-01 Reference Project (Part A - physical infrastructure)"
GRR01_PROJECT_TYPE = "REFERENCE_TEST_PROJECT"
GRR01_DATA_STATUS = "SYNTHETIC"
GRR01_ENGINEERING_STATUS = "REFERENCE_ASSUMPTIONS"
GRR01_CREATED_UTC = "2026-02-01T09:00:00Z"
GRR01_MODIFIED_UTC = "2026-02-01T09:00:00Z"

ALIGNMENT_ID = "ALN-MAIN"
ALIGNMENT_START_KM = 0.0
ALIGNMENT_END_KM = 50.0
LAYER_ID = "LYR-MAIN"

# ---------------------------------------------------------------------------
# Approved amendments
# ---------------------------------------------------------------------------
STOP_V_P1_R_ID = "STOP-V-P1-R"
FROZEN_STOP_V_P1_R_POSITION_M = 220.0
AMENDED_STOP_V_P1_R_POSITION_M = 250.0

APPROVED_AMENDMENTS: tuple[dict[str, Any], ...] = (
    {
        "id": "GRR-AMD-001",
        "status": "APPROVED",
        "date_utc": "2026-02-01",
        "object_id": STOP_V_P1_R_ID,
        "field": "position_m",
        "from": FROZEN_STOP_V_P1_R_POSITION_M,
        "to": AMENDED_STOP_V_P1_R_POSITION_M,
        "reason": (
            "Approved reference amendment: the Valley P1 reverse stopping mark is "
            "recorded at 250.0 m. The frozen pre-amendment value (220.0 m) is preserved "
            "in docs/GRR-01_FROZEN_PHYSICAL_v1.0.json; no object count changes."
        ),
    },
    {
        "id": "GRR-AMD-003",
        "status": "APPROVED",
        "date_utc": "2026-02-01",
        "object_id": "N-DEL-E2",
        "field": "attachment",
        "from": "unattached (Delta node without an incident Delta edge)",
        "to": "attached by open-line edge TR-O-VAL-DEL-ML2",
        "reason": (
            "Delta group declares 6 nodes and 4 edges; a connected 6-node region needs 5 "
            "edges. The sixth node is attached by the neighbouring open-line ML2 edge, so "
            "all frozen object counts (50 nodes / 59 edges / Delta 6-4) are unchanged."
        ),
    },
    {
        "id": "GRR-AMD-004",
        "status": "APPROVED",
        "date_utc": "2026-02-01",
        "object_id": "PLT-VAL-P2",
        "field": "usable_start_m / usable_end_m",
        "from": "usable range not reconciled with the frozen Valley P2 benchmark boundary",
        "to": "usable range 100.0 - 500.0 m (usable_length_m 400.0 m)",
        "reason": (
            "The frozen Valley P2 benchmark evaluates the reference HSR train length from "
            "front 200.0 m against the edge and requires the 500.0 m eastern boundary to be the platform "
            "boundary itself (98.0 m rear clearance). The platform usable range is therefore "
            "recorded as 100.0 - 500.0 m so that the critical boundary and the clearance are "
            "computed from platform data instead of being hard-coded. No object count changes."
        ),
    },
)

# ---------------------------------------------------------------------------
# Expected inventory (mandatory regression values)
# ---------------------------------------------------------------------------
GRR01_EXPECTED_COUNTS: dict[str, int] = {
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

GRR01_REGION_NODE_COUNTS: dict[str, int] = {
    "Alpha": 6,
    "Central": 18,
    "XC-24": 8,
    "Valley": 12,
    "Delta": 6,
    "Open line": 0,  # GRR-AMD-002: table-only correction, no physical node is uncounted
}

GRR01_REGION_TRACK_COUNTS: dict[str, int] = {
    "Open line": 8,
    "Alpha": 4,
    "Central": 23,
    "XC-24": 8,
    "Valley": 12,
    "Delta": 4,
}

#: Explicit regional membership maps (auditable classification; the region is not
#: inferred from ID prefixes).
REGION_NODE_IDS: dict[str, tuple[str, ...]] = {
    "Alpha": (
        "N-ALP-W",
        "N-ALP-U1",
        "N-ALP-U2",
        "N-ALP-SDG",
        "N-ALP-E1",
        "N-ALP-E",
    ),
    "Central": (
        "N-CEN-W",
        "N-CEN-E",
        "N-CEN-X-A",
        "N-CEN-X-B",
        "N-CEN-X-C",
        "N-CEN-X-D",
        "N-CEN-P1-W",
        "N-CEN-P1-E",
        "N-CEN-P2-W",
        "N-CEN-P2-E",
        "N-CEN-P3-W",
        "N-CEN-P3-E",
        "N-CEN-P4-W",
        "N-CEN-P4-E",
        "N-CEN-J1",
        "N-CEN-J2",
        "N-CEN-J3",
        "N-CEN-Y",
    ),
    "XC-24": (
        "N-XC-W",
        "N-XC-E",
        "N-XC-ML1-A",
        "N-XC-ML1-B",
        "N-XC-ML2-A",
        "N-XC-ML2-B",
        "N-XC-X1",
        "N-XC-X2",
    ),
    "Valley": (
        "N-VAL-W",
        "N-VAL-E",
        "N-VAL-T1-A",
        "N-VAL-T1-B",
        "N-VAL-T2-A",
        "N-VAL-T2-B",
        "N-VAL-P1-W",
        "N-VAL-P1-E",
        "N-VAL-P2-W",
        "N-VAL-P2-E",
        "N-VAL-XA",
        "N-VAL-XB",
    ),
    "Delta": (
        "N-DEL-W",
        "N-DEL-THR",
        "N-DEL-J",
        "N-DEL-P1-W",
        "N-DEL-P1-E",
        "N-DEL-E2",
    ),
}

REGION_TRACK_IDS: dict[str, tuple[str, ...]] = {
    "Open line": (
        "TR-O-ALP-CEN-ML1",
        "TR-O-ALP-CEN-ML2",
        "TR-O-CEN-VAL-ML1",
        "TR-O-CEN-VAL-ML2",
        "TR-O-CEN-VAL-SL-A",
        "TR-O-CEN-VAL-SL-B",
        "TR-O-VAL-DEL-ML1",
        "TR-O-VAL-DEL-ML2",
    ),
    "Alpha": (
        "TR-A-W-U1",
        "TR-A-U1-U2",
        "TR-A-SDG-E1",
        "TR-A-E1-E",
    ),
    "Central": (
        "TR-C-W-LDR-ML1",
        "TR-C-W-LDR-ML2",
        "TR-C-W-P1-CON",
        "TR-C-W-P2-CON",
        "TR-C-W-P3-CON",
        "TR-C-XA-P4",
        "TR-C-XB-P3",
        "TR-C-P1",
        "TR-C-P2",
        "TR-C-P3",
        "TR-C-P4",
        "TR-C-P2-LNK",
        "TR-C-P3-LNK",
        "TR-C-P1-LNK",
        "TR-C-J1-J3",
        "TR-C-J3-J2",
        "TR-C-J1-Y",
        "TR-C-Y-J2",
        "TR-C-P2-E-CON",
        "TR-C-P4-E-CON",
        "TR-C-E-U2-X",
        "TR-C-E-X-U1",
        "TR-C-E-X-L1",
    ),
    "XC-24": (
        "TR-X-ML1-STRAIGHT",
        "TR-X-ML2-STRAIGHT",
        "TR-X-ML1-ML2",
        "TR-X-ML2-ML1",
        "TR-X-W-X1",
        "TR-X-X1-E",
        "TR-X-W-X2",
        "TR-X-X2-E",
    ),
    "Valley": (
        "TR-V-THRU1",
        "TR-V-T1A-P1W",
        "TR-V-P1",
        "TR-V-P1E-T1B",
        "TR-V-W-XA",
        "TR-V-XA-T2A",
        "TR-V-THRU2",
        "TR-V-T2B-E",
        "TR-V-XA-P2W",
        "TR-V-P2",
        "TR-V-P2E-XB",
        "TR-V-XB-E",
    ),
    "Delta": (
        "TR-D-W-THR",
        "TR-D-THR-J",
        "TR-D-J-P1W",
        "TR-D-P1",
    ),
}

#: Final normalized edge names for the Central east crossing (Section AD).
CENTRAL_EAST_CROSS_EDGE_NAMES: tuple[str, ...] = (
    "TR-C-E-U2-X",
    "TR-C-E-X-U1",
    "TR-C-E-X-L1",
)

#: Provisional names that must NOT appear in GRR-01 (Section AD).
FORBIDDEN_PROVISIONAL_EDGE_NAMES: tuple[str, ...] = (
    "TR-C-E-U1-X",
    "TR-C-E-L1-X",
    "TR-C-E-X-U2",
)

# ---------------------------------------------------------------------------
# Static benchmarks (frozen values; static geometry only - no occupation time)
# ---------------------------------------------------------------------------
GRR01_STATIC_BENCHMARKS: tuple[dict[str, Any], ...] = (
    {
        "id": "GRR-STATIC-P2-FWD-HSR",
        "description": "Central P2, forward HSR movement (202 m)",
        "marker_id": "STOP-C-P2-DEP",
        "track_id": "TR-C-P2",
        "platform_id": "PLT-CEN-P2",
        "front_position_m": 420.0,
        "train_length_m": HSR_REF_LENGTH_M,
        "traversal": "WITH_EDGE",
        "critical_boundary_m": 230.0,
        "expected_rear_position_m": 218.0,
        "expected_rear_infringement_m": 12.0,
        "boundary_role": "usable_start (platform 230 m boundary)",
    },
    {
        "id": "GRR-STATIC-P2-FWD-HSR-PLUS25",
        "description": "Central P2, +25 m stopping mark variant (front 445 m)",
        "marker_id": "STOP-C-P2-ALT",
        "track_id": "TR-C-P2",
        "platform_id": "PLT-CEN-P2",
        "front_position_m": 445.0,
        "train_length_m": HSR_REF_LENGTH_M,
        "traversal": "WITH_EDGE",
        "critical_boundary_m": 230.0,
        "expected_rear_position_m": 243.0,
        "expected_rear_clearance_m": 13.0,
        "boundary_role": "usable_start (platform 230 m boundary)",
    },
    {
        "id": "GRR-STATIC-P1-REV-HSR",
        "description": "Central P1, reverse HSR movement (202 m)",
        "marker_id": "STOP-C-P1-ARR",
        "track_id": "TR-C-P1",
        "platform_id": "PLT-CEN-P1",
        "front_position_m": 170.0,
        "train_length_m": HSR_REF_LENGTH_M,
        "traversal": "AGAINST_EDGE",
        "critical_boundary_m": 360.0,
        "expected_rear_position_m": 372.0,
        "expected_rear_infringement_m": 12.0,
        "boundary_role": "usable_end (platform 360 m boundary)",
    },
    {
        "id": "GRR-STATIC-VP1-FWD-HSR",
        "description": "Valley P1, forward HSR evaluation point (front 480 m)",
        "marker_id": None,  # frozen evaluation point, not a stopping mark
        "track_id": "TR-V-P1",
        "platform_id": "PLT-VAL-P1",
        "front_position_m": 480.0,
        "train_length_m": HSR_REF_LENGTH_M,
        "traversal": "WITH_EDGE",
        "critical_boundary_m": 200.0,
        "expected_rear_position_m": 278.0,
        "expected_rear_clearance_m": 78.0,
        "boundary_role": "frozen western boundary (200 m)",
    },
    {
        "id": "GRR-STATIC-VP2-REV-HSR",
        "description": "Valley P2, reverse HSR evaluation point (front 200 m)",
        "marker_id": None,  # frozen evaluation point, not a stopping mark
        "track_id": "TR-V-P2",
        "platform_id": "PLT-VAL-P2",
        "front_position_m": 200.0,
        "train_length_m": HSR_REF_LENGTH_M,
        "traversal": "AGAINST_EDGE",
        "critical_boundary_m": 500.0,
        "expected_rear_position_m": 402.0,
        "expected_rear_clearance_m": 98.0,
        "boundary_role": "frozen eastern boundary (500 m)",
    },
)


# ---------------------------------------------------------------------------
# builders
# ---------------------------------------------------------------------------
def _alignment() -> dict[str, Any]:
    return {
        "id": ALIGNMENT_ID,
        "name": "GRR-01 main alignment (Alpha - Delta)",
        "start_chainage_km": ALIGNMENT_START_KM,
        "end_chainage_km": ALIGNMENT_END_KM,
    }


def _track_groups() -> list[dict[str, Any]]:
    return [
        {
            "id": "TG-ML1",
            "name": "Main line 1 (up)",
            "directionality": "BOTH",
            "normal_direction": "FORWARD",
        },
        {
            "id": "TG-ML2",
            "name": "Main line 2 (down)",
            "directionality": "BOTH",
            "normal_direction": "REVERSE",
        },
    ]


def _horizontal_geometry() -> list[dict[str, Any]]:
    return [
        {"id": "HGR-01", "alignment_id": ALIGNMENT_ID, "start_chainage_km": 0.0,
         "end_chainage_km": 2.5, "type": "STRAIGHT"},
        {"id": "HGR-02", "alignment_id": ALIGNMENT_ID, "start_chainage_km": 2.5,
         "end_chainage_km": 18.0, "type": "CURVE", "radius_m": 1800.0, "handedness": "LEFT"},
        {"id": "HGR-03", "alignment_id": ALIGNMENT_ID, "start_chainage_km": 18.0,
         "end_chainage_km": 22.0, "type": "STRAIGHT"},
        {"id": "HGR-04", "alignment_id": ALIGNMENT_ID, "start_chainage_km": 22.0,
         "end_chainage_km": 35.0, "type": "CURVE", "radius_m": 1200.0, "handedness": "RIGHT"},
        {"id": "HGR-05", "alignment_id": ALIGNMENT_ID, "start_chainage_km": 35.0,
         "end_chainage_km": 40.5, "type": "STRAIGHT"},
        {"id": "HGR-06", "alignment_id": ALIGNMENT_ID, "start_chainage_km": 40.5,
         "end_chainage_km": 47.0, "type": "CURVE", "radius_m": 2000.0, "handedness": "LEFT"},
        {"id": "HGR-07", "alignment_id": ALIGNMENT_ID, "start_chainage_km": 47.0,
         "end_chainage_km": 50.0, "type": "STRAIGHT"},
    ]


_VERTICAL_PROFILE_CHAINAGES: tuple[float, ...] = (0.0, 2.5, 6.0, 10.0, 15.0, 20.0, 25.0,
                                                 30.0, 35.0, 38.0, 42.0, 46.0, 50.0)
_VERTICAL_PROFILE_ELEVATIONS_M: tuple[float, ...] = (120.0, 120.5, 124.0, 128.5, 132.0, 135.5,
                                                     138.0, 136.5, 133.0, 131.5, 129.0, 126.0, 124.5)


def _vertical_profiles() -> list[dict[str, Any]]:
    points = [
        {"id": f"VPP-{index:02d}", "chainage_km": chainage, "elevation_m": elevation}
        for index, (chainage, elevation) in enumerate(
            zip(_VERTICAL_PROFILE_CHAINAGES, _VERTICAL_PROFILE_ELEVATIONS_M), start=1
        )
    ]
    return [
        {
            "id": "VP-MAIN",
            "alignment_id": ALIGNMENT_ID,
            "source_mode": "ELEVATION_POINTS",
            "points": points,
        }
    ]


def _speed_restrictions() -> list[dict[str, Any]]:
    return [
        {"id": "SPR-01", "name": "Alpha station area", "alignment_id": ALIGNMENT_ID,
         "start_chainage_km": 0.0, "end_chainage_km": 2.5, "speed_kmh": 80,
         "direction": "BOTH", "type": "PERMANENT"},
        {"id": "SPR-02", "name": "Alpha - Central running line", "alignment_id": ALIGNMENT_ID,
         "start_chainage_km": 2.5, "end_chainage_km": 18.0, "speed_kmh": 300,
         "direction": "BOTH", "type": "PERMANENT"},
        {"id": "SPR-03", "name": "XC-24 crossing area", "alignment_id": ALIGNMENT_ID,
         "start_chainage_km": 18.0, "end_chainage_km": 22.0, "speed_kmh": 250,
         "direction": "BOTH", "type": "PERMANENT"},
        {"id": "SPR-04", "name": "Central - Valley running line", "alignment_id": ALIGNMENT_ID,
         "start_chainage_km": 22.0, "end_chainage_km": 35.0, "speed_kmh": 300,
         "direction": "BOTH", "type": "PERMANENT"},
        {"id": "SPR-05", "name": "Valley approach", "alignment_id": ALIGNMENT_ID,
         "start_chainage_km": 35.0, "end_chainage_km": 40.5, "speed_kmh": 280,
         "direction": "BOTH", "type": "PERMANENT"},
        {"id": "SPR-06", "name": "Valley - Delta running line", "alignment_id": ALIGNMENT_ID,
         "start_chainage_km": 40.5, "end_chainage_km": 47.0, "speed_kmh": 260,
         "direction": "BOTH", "type": "PERMANENT"},
        {"id": "SPR-07", "name": "Delta station area", "alignment_id": ALIGNMENT_ID,
         "start_chainage_km": 47.0, "end_chainage_km": 50.0, "speed_kmh": 90,
         "direction": "BOTH", "type": "PERMANENT"},
        {"id": "SPR-08", "name": "Reverse-direction restriction (42 - 44 km)",
         "alignment_id": ALIGNMENT_ID, "start_chainage_km": 42.0, "end_chainage_km": 44.0,
         "speed_kmh": 240, "direction": "REVERSE", "type": "PERMANENT_DIRECTIONAL"},
    ]


def _nodes() -> list[dict[str, Any]]:
    raw: list[tuple[str, str, float, Optional[str], Optional[str]]] = [
        # -- Alpha (6) --
        ("N-ALP-W", "BUFFER_STOP", 0.0, None, "Alpha west buffer stop"),
        ("N-ALP-U1", "SWITCH", 0.35, "STA-ALPHA", "Alpha west ladder switch 1"),
        ("N-ALP-U2", "SWITCH", 0.75, "STA-ALPHA", "Alpha west ladder switch 2"),
        ("N-ALP-SDG", "BUFFER_STOP", 1.15, "STA-ALPHA", "Alpha stabling siding buffer"),
        ("N-ALP-E1", "SWITCH", 1.55, "STA-ALPHA", "Alpha east ladder switch"),
        ("N-ALP-E", "BUFFER_STOP", 2.5, "STA-ALPHA", "Alpha east buffer stop"),
        # -- Central (18) --
        ("N-CEN-W", "STATION_BOUNDARY", 15.0, "STA-CEN", "Central west boundary"),
        ("N-CEN-E", "STATION_BOUNDARY", 28.0, "STA-CEN", "Central east boundary"),
        ("N-CEN-X-A", "SWITCH", 15.35, "STA-CEN", "Central west ladder switch A"),
        ("N-CEN-X-B", "SWITCH", 15.45, "STA-CEN", "Central west ladder switch B"),
        ("N-CEN-X-C", "SWITCH", 27.85, "STA-CEN", "Central east ladder switch C"),
        ("N-CEN-X-D", "SWITCH", 27.9, "STA-CEN", "Central east ladder switch D"),
        ("N-CEN-P1-W", "STATION_BOUNDARY", 15.5, "STA-CEN", "Central P1 west end"),
        ("N-CEN-P1-E", "STATION_BOUNDARY", 19.5, "STA-CEN", "Central P1 east end"),
        ("N-CEN-P2-W", "STATION_BOUNDARY", 15.5, "STA-CEN", "Central P2 west end"),
        ("N-CEN-P2-E", "STATION_BOUNDARY", 27.0, "STA-CEN", "Central P2 east end"),
        ("N-CEN-P3-W", "STATION_BOUNDARY", 15.6, "STA-CEN", "Central P3 west end"),
        ("N-CEN-P3-E", "STATION_BOUNDARY", 24.0, "STA-CEN", "Central P3 east end"),
        ("N-CEN-P4-W", "STATION_BOUNDARY", 15.5, "STA-CEN", "Central P4 west end"),
        ("N-CEN-P4-E", "STATION_BOUNDARY", 27.5, "STA-CEN", "Central P4 east end"),
        ("N-CEN-J1", "SWITCH", 25.0, "STA-CEN", "Central mid-yard switch J1"),
        ("N-CEN-J2", "SWITCH", 27.6, "STA-CEN", "Central east yard switch J2"),
        ("N-CEN-J3", "SWITCH", 26.2, "STA-CEN", "Central mid-yard switch J3"),
        ("N-CEN-Y", "CONNECTION", 25.5, "STA-CEN", "Central yard connection"),
        # -- XC-24 (8) --
        ("N-XC-W", "CONNECTION", 20.0, None, "XC-24 west trunk"),
        ("N-XC-E", "CONNECTION", 22.0, None, "XC-24 east trunk"),
        ("N-XC-ML1-A", "SWITCH", 20.2, None, "XC-24 ML1 west crossover switch"),
        ("N-XC-ML1-B", "SWITCH", 21.8, None, "XC-24 ML1 east crossover switch"),
        ("N-XC-ML2-A", "SWITCH", 20.25, None, "XC-24 ML2 west crossover switch"),
        ("N-XC-ML2-B", "SWITCH", 21.85, None, "XC-24 ML2 east crossover switch"),
        ("N-XC-X1", "TRACK_CONNECTION", 20.9, None, "XC-24 intermediate connection 1"),
        ("N-XC-X2", "TRACK_CONNECTION", 21.1, None, "XC-24 intermediate connection 2"),
        # -- Valley (12) --
        ("N-VAL-W", "STATION_BOUNDARY", 37.0, "STA-VAL", "Valley west boundary"),
        ("N-VAL-E", "STATION_BOUNDARY", 44.0, "STA-VAL", "Valley east boundary"),
        ("N-VAL-T1-A", "SWITCH", 38.0, "STA-VAL", "Valley through line 1 switch A"),
        ("N-VAL-T1-B", "SWITCH", 43.2, "STA-VAL", "Valley through line 1 switch B"),
        ("N-VAL-T2-A", "SWITCH", 38.4, "STA-VAL", "Valley through line 2 switch A"),
        ("N-VAL-T2-B", "SWITCH", 43.6, "STA-VAL", "Valley through line 2 switch B"),
        ("N-VAL-P1-W", "STATION_BOUNDARY", 38.1, "STA-VAL", "Valley P1 west end"),
        ("N-VAL-P1-E", "STATION_BOUNDARY", 40.0, "STA-VAL", "Valley P1 east end"),
        ("N-VAL-P2-W", "STATION_BOUNDARY", 38.5, "STA-VAL", "Valley P2 west end"),
        ("N-VAL-P2-E", "STATION_BOUNDARY", 41.0, "STA-VAL", "Valley P2 east end"),
        ("N-VAL-XA", "SWITCH", 37.5, "STA-VAL", "Valley west ladder switch A"),
        ("N-VAL-XB", "SWITCH", 43.8, "STA-VAL", "Valley east ladder switch B"),
        # -- Delta (6) --
        ("N-DEL-W", "TRACK_CONNECTION", 47.0, "STA-DELTA", "Delta west connection (ML1)"),
        ("N-DEL-THR", "SWITCH", 47.4, "STA-DELTA", "Delta station throat"),
        ("N-DEL-J", "SWITCH", 47.5, "STA-DELTA", "Delta platform ladder switch"),
        ("N-DEL-P1-W", "STATION_BOUNDARY", 47.6, "STA-DELTA", "Delta P1 west end"),
        ("N-DEL-P1-E", "BUFFER_STOP", 49.0, "STA-DELTA", "Delta P1 buffer stop"),
        ("N-DEL-E2", "TRACK_CONNECTION", 49.6, "STA-DELTA", "Delta east connection (ML2)"),
    ]
    nodes: list[dict[str, Any]] = []
    for node_id, node_type, chainage, station_id, name in raw:
        node: dict[str, Any] = {
            "id": node_id,
            "type": node_type,
            "chainage_km": chainage,
            "name": name,
        }
        if station_id is not None:
            node["station_id"] = station_id
        nodes.append(node)
    return nodes


def _tracks() -> list[dict[str, Any]]:
    """All 59 track edges. Chainage maps progress in increasing physical chainage."""
    raw: list[tuple[str, str, str, float, float, float, str, str]] = [
        # id, from_node, to_node, length_m, start_km, end_km, track_group, directionality
        # -- Open line (8) --
        ("TR-O-ALP-CEN-ML1", "N-ALP-E", "N-CEN-W", 12500.0, 2.5, 15.0, "TG-ML1", "BOTH"),
        ("TR-O-ALP-CEN-ML2", "N-ALP-U2", "N-CEN-W", 14250.0, 0.75, 15.0, "TG-ML2", "BOTH"),
        ("TR-O-CEN-VAL-ML1", "N-CEN-E", "N-VAL-W", 9000.0, 28.0, 37.0, "TG-ML1", "BOTH"),
        ("TR-O-CEN-VAL-ML2", "N-CEN-E", "N-VAL-XA", 9500.0, 28.0, 37.5, "TG-ML2", "BOTH"),
        ("TR-O-CEN-VAL-SL-A", "N-CEN-X-C", "N-VAL-W", 9150.0, 27.85, 37.0, "TG-ML1", "BOTH"),
        ("TR-O-CEN-VAL-SL-B", "N-CEN-X-D", "N-VAL-T2-A", 10500.0, 27.9, 38.4, "TG-ML2", "BOTH"),
        ("TR-O-VAL-DEL-ML1", "N-VAL-E", "N-DEL-W", 3000.0, 44.0, 47.0, "TG-ML1", "BOTH"),
        ("TR-O-VAL-DEL-ML2", "N-VAL-E", "N-DEL-E2", 5600.0, 44.0, 49.6, "TG-ML2", "BOTH"),
        # -- Alpha (4) --
        ("TR-A-W-U1", "N-ALP-W", "N-ALP-U1", 350.0, 0.0, 0.35, "TG-ML1", "BOTH"),
        ("TR-A-U1-U2", "N-ALP-U1", "N-ALP-U2", 400.0, 0.35, 0.75, "TG-ML1", "BOTH"),
        ("TR-A-SDG-E1", "N-ALP-SDG", "N-ALP-E1", 400.0, 1.15, 1.55, "TG-ML1", "FORWARD_ONLY"),
        ("TR-A-E1-E", "N-ALP-E1", "N-ALP-E", 900.0, 1.6, 2.5, "TG-ML1", "BOTH"),
    ]
    central = [
        ("TR-C-W-LDR-ML1", "N-CEN-W", "N-CEN-X-A", 350.0, 15.0, 15.35, "TG-ML1"),
        ("TR-C-W-LDR-ML2", "N-CEN-X-B", "N-CEN-W", 450.0, 15.0, 15.45, "TG-ML2"),
        ("TR-C-W-P1-CON", "N-CEN-X-A", "N-CEN-P1-W", 150.0, 15.35, 15.5, "TG-ML1"),
        ("TR-C-W-P2-CON", "N-CEN-X-B", "N-CEN-P2-W", 50.0, 15.45, 15.5, "TG-ML1"),
        ("TR-C-W-P3-CON", "N-CEN-X-A", "N-CEN-P3-W", 250.0, 15.35, 15.6, "TG-ML1"),
        ("TR-C-XA-P4", "N-CEN-X-A", "N-CEN-P4-W", 150.0, 15.35, 15.5, "TG-ML1"),
        ("TR-C-XB-P3", "N-CEN-X-B", "N-CEN-P3-W", 150.0, 15.45, 15.6, "TG-ML2"),
        ("TR-C-P1", "N-CEN-P1-W", "N-CEN-P1-E", 4000.0, 15.5, 19.5, "TG-ML1"),
        ("TR-C-P2", "N-CEN-P2-W", "N-CEN-P2-E", 11500.0, 15.5, 27.0, "TG-ML1"),
        ("TR-C-P3", "N-CEN-P3-W", "N-CEN-P3-E", 8400.0, 15.6, 24.0, "TG-ML1"),
        ("TR-C-P4", "N-CEN-P4-W", "N-CEN-P4-E", 12000.0, 15.5, 27.5, "TG-ML1"),
        ("TR-C-P2-LNK", "N-CEN-P2-W", "N-XC-ML1-A", 4700.0, 15.5, 20.2, "TG-ML1"),
        ("TR-C-P3-LNK", "N-XC-E", "N-CEN-P3-E", 2000.0, 22.0, 24.0, "TG-ML1"),
        ("TR-C-P1-LNK", "N-CEN-P1-E", "N-CEN-J1", 5500.0, 19.5, 25.0, "TG-ML1"),
        ("TR-C-J1-J3", "N-CEN-J1", "N-CEN-J3", 1200.0, 25.0, 26.2, "TG-ML1"),
        ("TR-C-J3-J2", "N-CEN-J3", "N-CEN-J2", 1400.0, 26.2, 27.6, "TG-ML1"),
        ("TR-C-J1-Y", "N-CEN-J1", "N-CEN-Y", 500.0, 25.0, 25.5, "TG-ML1"),
        ("TR-C-Y-J2", "N-CEN-Y", "N-CEN-J2", 2100.0, 25.5, 27.6, "TG-ML1"),
        ("TR-C-P2-E-CON", "N-CEN-P2-E", "N-CEN-X-C", 850.0, 27.0, 27.85, "TG-ML1"),
        ("TR-C-P4-E-CON", "N-CEN-P4-E", "N-CEN-X-D", 400.0, 27.5, 27.9, "TG-ML1"),
        # Final normalized Central east crossing names (Section AD).
        ("TR-C-E-U2-X", "N-CEN-X-D", "N-CEN-X-C", 120.0, 27.85, 27.9, "TG-ML2"),
        ("TR-C-E-X-U1", "N-CEN-X-C", "N-CEN-E", 150.0, 27.85, 28.0, "TG-ML1"),
        ("TR-C-E-X-L1", "N-CEN-X-D", "N-CEN-E", 100.0, 27.9, 28.0, "TG-ML2"),
    ]
    # Every stored chainage map progresses in increasing physical chainage. The
    # normalisation below is a safety net and a documented GRR Part-A invariant.
    central = [
        (track_id, from_node, to_node, length, min(start, end), max(start, end), group)
        for track_id, from_node, to_node, length, start, end, group in central
    ]
    xc = [
        ("TR-X-ML1-STRAIGHT", "N-XC-ML1-A", "N-XC-ML1-B", 1600.0, 20.2, 21.8, "TG-ML1"),
        ("TR-X-ML2-STRAIGHT", "N-XC-ML2-A", "N-XC-ML2-B", 1600.0, 20.25, 21.85, "TG-ML2"),
        ("TR-X-ML1-ML2", "N-XC-ML1-A", "N-XC-ML2-B", 1850.0, 20.2, 21.85, "TG-ML1"),
        ("TR-X-ML2-ML1", "N-XC-ML2-A", "N-XC-ML1-B", 1750.0, 20.25, 21.8, "TG-ML2"),
        ("TR-X-W-X1", "N-XC-W", "N-XC-X1", 900.0, 20.0, 20.9, "TG-ML1"),
        ("TR-X-X1-E", "N-XC-X1", "N-XC-E", 1100.0, 20.9, 22.0, "TG-ML1"),
        ("TR-X-W-X2", "N-XC-W", "N-XC-X2", 1100.0, 20.0, 21.1, "TG-ML2"),
        ("TR-X-X2-E", "N-XC-X2", "N-XC-E", 900.0, 21.1, 22.0, "TG-ML2"),
    ]
    valley = [
        ("TR-V-THRU1", "N-VAL-W", "N-VAL-T1-B", 6200.0, 37.0, 43.2, "TG-ML1"),
        ("TR-V-T1A-P1W", "N-VAL-T1-A", "N-VAL-P1-W", 100.0, 38.0, 38.1, "TG-ML1"),
        ("TR-V-P1", "N-VAL-P1-W", "N-VAL-P1-E", 1900.0, 38.1, 40.0, "TG-ML1"),
        ("TR-V-P1E-T1B", "N-VAL-P1-E", "N-VAL-T1-B", 3200.0, 40.0, 43.2, "TG-ML1"),
        ("TR-V-W-XA", "N-VAL-W", "N-VAL-XA", 500.0, 37.0, 37.5, "TG-ML1"),
        ("TR-V-XA-T2A", "N-VAL-XA", "N-VAL-T2-A", 900.0, 37.5, 38.4, "TG-ML2"),
        ("TR-V-THRU2", "N-VAL-T2-A", "N-VAL-T2-B", 5200.0, 38.4, 43.6, "TG-ML2"),
        ("TR-V-T2B-E", "N-VAL-T2-B", "N-VAL-E", 400.0, 43.6, 44.0, "TG-ML2"),
        ("TR-V-XA-P2W", "N-VAL-XA", "N-VAL-P2-W", 1000.0, 37.5, 38.5, "TG-ML2"),
        ("TR-V-P2", "N-VAL-P2-W", "N-VAL-P2-E", 2500.0, 38.5, 41.0, "TG-ML2"),
        ("TR-V-P2E-XB", "N-VAL-P2-E", "N-VAL-XB", 2800.0, 41.0, 43.8, "TG-ML2"),
        ("TR-V-XB-E", "N-VAL-XB", "N-VAL-E", 200.0, 43.8, 44.0, "TG-ML2"),
    ]
    delta = [
        ("TR-D-W-THR", "N-DEL-W", "N-DEL-THR", 400.0, 47.0, 47.4, "TG-ML1"),
        ("TR-D-THR-J", "N-DEL-THR", "N-DEL-J", 150.0, 47.4, 47.55, "TG-ML1"),
        ("TR-D-J-P1W", "N-DEL-J", "N-DEL-P1-W", 50.0, 47.55, 47.6, "TG-ML1"),
        ("TR-D-P1", "N-DEL-P1-W", "N-DEL-P1-E", 1400.0, 47.6, 49.0, "TG-ML1"),
    ]

    tracks: list[dict[str, Any]] = []
    for track_id, from_node, to_node, length, start, end, group, directionality in raw:
        tracks.append(
            _track(track_id, from_node, to_node, length, start, end, group, directionality)
        )
    for track_id, from_node, to_node, length, start, end, group in central:
        tracks.append(_track(track_id, from_node, to_node, length, start, end, group, "BOTH"))
    for track_id, from_node, to_node, length, start, end, group in xc:
        tracks.append(_track(track_id, from_node, to_node, length, start, end, group, "BOTH"))
    for track_id, from_node, to_node, length, start, end, group in valley:
        tracks.append(_track(track_id, from_node, to_node, length, start, end, group, "BOTH"))
    for track_id, from_node, to_node, length, start, end, group in delta:
        tracks.append(_track(track_id, from_node, to_node, length, start, end, group, "BOTH"))
    return tracks


def _track(
    track_id: str,
    from_node: str,
    to_node: str,
    length_m: float,
    start_km: float,
    end_km: float,
    track_group_id: str,
    directionality: str,
) -> dict[str, Any]:
    return {
        "id": track_id,
        "from_node": from_node,
        "to_node": to_node,
        "length_m": length_m,
        "directionality": directionality,
        "track_group_id": track_group_id,
        "geometry_source": "ALIGNMENT",
        "elevation_source": "ALIGNMENT_MAPPING",
        "chainage_map": {
            "mode": "LINEAR",
            "start_km": start_km,
            "end_km": end_km,
        },
    }


def _stations() -> list[dict[str, Any]]:
    return [
        {"id": "STA-ALPHA", "name": "Alpha", "type": "TERMINAL",
         "reference_chainage_km": 1.2, "platform_ids": ["PLT-ALP-P1", "PLT-ALP-P2"]},
        {"id": "STA-CEN", "name": "Central", "type": "INTERMEDIATE",
         "reference_chainage_km": 21.0,
         "platform_ids": ["PLT-CEN-P1", "PLT-CEN-P2", "PLT-CEN-P3", "PLT-CEN-P4"]},
        {"id": "STA-VAL", "name": "Valley", "type": "INTERMEDIATE",
         "reference_chainage_km": 39.0, "platform_ids": ["PLT-VAL-P1", "PLT-VAL-P2"]},
        {"id": "STA-DELTA", "name": "Delta", "type": "TERMINAL",
         "reference_chainage_km": 48.3, "platform_ids": ["PLT-DEL-P1"]},
    ]


def _platforms() -> list[dict[str, Any]]:
    return [
        _platform("PLT-ALP-P1", "STA-ALPHA", "TR-A-W-U1", 20.0, 340.0, ["STOP-A-P1-ARR", "STOP-A-P1-DEP"]),
        _platform("PLT-ALP-P2", "STA-ALPHA", "TR-A-E1-E", 40.0, 880.0, ["STOP-A-P2-ARR", "STOP-A-P2-DEP"]),
        _platform("PLT-CEN-P1", "STA-CEN", "TR-C-P1", 150.0, 360.0,
                  ["STOP-C-P1-ARR", "STOP-C-P1-DEP"]),
        _platform("PLT-CEN-P2", "STA-CEN", "TR-C-P2", 230.0, 11000.0,
                  ["STOP-C-P2-ARR", "STOP-C-P2-DEP", "STOP-C-P2-ALT"]),
        _platform("PLT-CEN-P3", "STA-CEN", "TR-C-P3", 100.0, 8300.0,
                  ["STOP-C-P3-ARR", "STOP-C-P3-DEP"]),
        _platform("PLT-CEN-P4", "STA-CEN", "TR-C-P4", 120.0, 11800.0, ["STOP-C-P4-DEP"]),
        _platform("PLT-VAL-P1", "STA-VAL", "TR-V-P1", 200.0, 1600.0, [STOP_V_P1_R_ID]),
        _platform("PLT-VAL-P2", "STA-VAL", "TR-V-P2", 100.0, 500.0, []),
        _platform("PLT-DEL-P1", "STA-DELTA", "TR-D-P1", 90.0, 1280.0, ["STOP-D-P1-DEP"]),
    ]


def _platform(
    platform_id: str,
    station_id: str,
    track_id: str,
    usable_start_m: float,
    usable_end_m: float,
    stopping_mark_ids: list[str],
) -> dict[str, Any]:
    return {
        "id": platform_id,
        "station_id": station_id,
        "track_id": track_id,
        "usable_start_m": usable_start_m,
        "usable_end_m": usable_end_m,
        "usable_length_m": usable_end_m - usable_start_m,
        "directionality": "BOTH",
        "platform_track_speed_kmh": 80,
        "stopping_mark_ids": stopping_mark_ids,
    }


def _stopping_marks(*, amended: bool = True) -> list[dict[str, Any]]:
    position = AMENDED_STOP_V_P1_R_POSITION_M if amended else FROZEN_STOP_V_P1_R_POSITION_M
    return [
        _mark("STOP-A-P1-ARR", "PLT-ALP-P1", "TR-A-W-U1", "REVERSE", 130.0),
        _mark("STOP-A-P1-DEP", "PLT-ALP-P1", "TR-A-W-U1", "FORWARD", 300.0),
        _mark("STOP-A-P2-ARR", "PLT-ALP-P2", "TR-A-E1-E", "REVERSE", 200.0),
        _mark("STOP-A-P2-DEP", "PLT-ALP-P2", "TR-A-E1-E", "FORWARD", 700.0),
        _mark("STOP-C-P1-ARR", "PLT-CEN-P1", "TR-C-P1", "REVERSE", 170.0),
        _mark("STOP-C-P1-DEP", "PLT-CEN-P1", "TR-C-P1", "FORWARD", 355.0),
        _mark("STOP-C-P2-ARR", "PLT-CEN-P2", "TR-C-P2", "REVERSE", 300.0),
        _mark("STOP-C-P2-DEP", "PLT-CEN-P2", "TR-C-P2", "FORWARD", 420.0),
        _mark("STOP-C-P2-ALT", "PLT-CEN-P2", "TR-C-P2", "FORWARD", 445.0),
        _mark("STOP-C-P3-ARR", "PLT-CEN-P3", "TR-C-P3", "REVERSE", 200.0),
        _mark("STOP-C-P3-DEP", "PLT-CEN-P3", "TR-C-P3", "FORWARD", 8000.0),
        _mark("STOP-C-P4-DEP", "PLT-CEN-P4", "TR-C-P4", "FORWARD", 11700.0),
        _mark(STOP_V_P1_R_ID, "PLT-VAL-P1", "TR-V-P1", "REVERSE", position),
        _mark("STOP-D-P1-DEP", "PLT-DEL-P1", "TR-D-P1", "FORWARD", 300.0),
    ]


def _mark(
    mark_id: str, platform_id: str, track_id: str, direction: str, position_m: float
) -> dict[str, Any]:
    return {
        "id": mark_id,
        "platform_id": platform_id,
        "track_id": track_id,
        "direction": direction,
        "position_m": position_m,
        "marker_type": "EXPLICIT",
    }


def _observation_points() -> list[dict[str, Any]]:
    return [
        {"id": "OBS-REF-FWD-ORIGIN", "name": "Reference forward origin (Alpha)",
         "type": "SERVICE_EVENT", "station_id": "STA-ALPHA", "event": "DEPARTURE",
         "platform_id": "PLT-ALP-P2", "track_id": "TR-A-E1-E", "position_m": 700.0},
        {"id": "OBS-REF-REV-ORIGIN", "name": "Reference reverse origin (Delta)",
         "type": "SERVICE_EVENT", "station_id": "STA-DELTA", "event": "DEPARTURE",
         "platform_id": "PLT-DEL-P1", "track_id": "TR-D-P1", "position_m": 300.0},
        {"id": "OBS-C-WEST", "name": "Central west boundary cross-section",
         "type": "CROSS_SECTION", "node_ids": ["N-CEN-W"]},
        {"id": "OBS-C-EAST", "name": "Central east boundary cross-section",
         "type": "CROSS_SECTION", "node_ids": ["N-CEN-E"]},
        {"id": "OBS-XC24", "name": "XC-24 track cross-section",
         "type": "TRACK_CROSS_SECTION",
         "members": [
             {"track_id": "TR-X-ML1-STRAIGHT", "position_m": 80.0},
             {"track_id": "TR-X-ML2-STRAIGHT", "position_m": 80.0},
             {"track_id": "TR-X-ML1-ML2", "position_m": 90.0},
             {"track_id": "TR-X-ML2-ML1", "position_m": 90.0},
         ]},
        {"id": "OBS-V-WEST", "name": "Valley west boundary cross-section",
         "type": "CROSS_SECTION", "node_ids": ["N-VAL-W"]},
        {"id": "OBS-V-EAST", "name": "Valley east boundary cross-section",
         "type": "CROSS_SECTION", "node_ids": ["N-VAL-E"]},
        {"id": "OBS-FWD-DEST-APP", "name": "Forward destination approach (Delta throat)",
         "type": "CROSS_SECTION", "node_ids": ["N-DEL-THR"]},
        {"id": "OBS-REV-DEST-APP", "name": "Reverse destination approach (Alpha west ladder)",
         "type": "CROSS_SECTION", "node_ids": ["N-ALP-U1"]},
    ]


# ---------------------------------------------------------------------------
# project document
# ---------------------------------------------------------------------------
def build_grr01_layer(*, amended: bool = True) -> dict[str, Any]:
    """Return the single GRR-01 infrastructure layer object (typed catalogues)."""
    return {
        "id": LAYER_ID,
        "name": "GRR-01 main infrastructure layer",
        "physical_mode": "PHYSICAL",
        "comment": (
            "GRR-01 Part A physical infrastructure. Typed Phase-2 catalogues only; "
            "legacy Phase-1 opaque catalogues are intentionally empty."
        ),
        "alignments": [_alignment()],
        "track_groups": _track_groups(),
        "horizontal_geometry": _horizontal_geometry(),
        "vertical_profiles": _vertical_profiles(),
        "speed_restrictions": _speed_restrictions(),
        "nodes": _nodes(),
        "tracks": _tracks(),
        "stations": _stations(),
        "platforms": _platforms(),
        "stopping_marks": _stopping_marks(amended=amended),
        "observation_points": _observation_points(),
        # preserved Phase-1 opaque catalogues (empty for GRR-01)
        "chainages": [],
        "speed_profiles": [],
        "gradients": [],
        "curves": [],
        "tunnels": [],
        "bridges": [],
    }


def build_grr01_document(*, amended: bool = True) -> dict[str, Any]:
    """Return the complete GRR-01 Part-A project document (schema 1.0)."""
    provenance: dict[str, Any] = {
        "created_by": "GRR-01 reference fixture",
        "tool_name": "railway_headway_sim",
        "tool_version": None,  # filled by the application layer when applicable
        "source": "GRR-01 Part A frozen physical inventory (Phase-2 reconstruction)",
        "notes": (
            "Static physical setup data and static geometry benchmarks only. No train "
            "simulation, signalling, blocking-time, headway or capacity results are present."
        ),
    }
    if amended:
        provenance["approved_amendments"] = [dict(item) for item in APPROVED_AMENDMENTS]
    return {
        "schema_version": "1.0",
        "project": {
            "id": GRR01_PROJECT_ID,
            "name": GRR01_PROJECT_NAME,
            "project_type": GRR01_PROJECT_TYPE,
            "data_status": GRR01_DATA_STATUS,
            "description": (
                "GRR-01 Part-A reference project: one alignment over 0-50 km, 50 topology "
                "nodes, 59 track edges, 4 stations, 9 platforms, 14 stopping marks and "
                "9 observation points. Static physical infrastructure only."
            ),
            "engineering_status": GRR01_ENGINEERING_STATUS,
            "created_utc": GRR01_CREATED_UTC,
            "modified_utc": GRR01_MODIFIED_UTC,
        },
        "display_units": {
            "chainage": "km",
            "track_distance": "m",
            "elevation": "m",
            "speed": "km/h",
            "mass": "t",
            "force": "kN",
            "power": "kW",
            "time": "s",
            "acceleration": "m/s^2",
            "gradient": "%",
            "curve_radius": "m",
        },
        "reference_system": {
            "alignment_id": ALIGNMENT_ID,
            "chainage_start_km": ALIGNMENT_START_KM,
            "chainage_end_km": ALIGNMENT_END_KM,
            "chainage_origin_name": "Alpha",
            "chainage_end_name": "Delta",
            "projection": "X_Y",
            "coordinate_system": "LOCAL",
            "datum": "LOCAL",
            "forward_direction": "INCREASING_CHAINAGE",
            "reverse_direction": "DECREASING_CHAINAGE",
            "curve_radius_convention": "SIGNED_LEFT_POSITIVE",
        },
        "provenance": provenance,
        "infrastructure": [build_grr01_layer(amended=amended)],
        "signalling": {"simulation_time_step_s": 1.0, "rule_set_template": None, "signals": []},
        "rolling_stock": {"trainset_defaults": {}, "vehicles": []},
        "train_paths": {"stop_patterns": [], "paths": []},
        "services": [],
        "simulation": {
            "time_step_s": 1.0,
            "random_seed": None,
            "start_time_s": 0.0,
            "horizon_s": None,
            "notes": "Run configuration placeholder - no run is performed.",
        },
        "analysis": {"notes": "No analysis is performed in this phase.", "parameters": {}},
        "scenarios": [],
        "reporting": {
            "report_title": "GRR-01 Part A reference project record",
            "author": "",
            "organisation": "",
            "notes": "Report metadata only - no report is generated.",
        },
    }


def frozen_document() -> dict[str, Any]:
    """Return the un-amended frozen evidence document (STOP-V-P1-R at 220.0 m)."""
    document = build_grr01_document(amended=False)
    document["provenance"]["source"] = "GRR-01 frozen physical inventory v1.0 (pre-amendment evidence)"
    document["provenance"]["notes"] = (
        "FROZEN EVIDENCE FILE: identical to examples/GRR-01.json except that "
        f"{STOP_V_P1_R_ID}.position_m retains the pre-amendment value "
        f"{FROZEN_STOP_V_P1_R_POSITION_M} m and provenance.approved_amendments is absent."
    )
    return document


#: Representation of the reference stopping assignments used by the static tests.
BASELINE_STATIC_ASSIGNMENTS: tuple[dict[str, Any], ...] = (
    # marker_id, train length, traversal, expected fit, expected critical boundary
    {"marker_id": "STOP-A-P1-DEP", "train_length_m": HSR_REF_LENGTH_M, "traversal": "WITH_EDGE",
     "expected_fit": True, "expected_critical_boundary_m": 20.0, "expected_rear_margin_m": 78.0},
    {"marker_id": "STOP-A-P1-ARR", "train_length_m": HSR_REF_LENGTH_M, "traversal": "AGAINST_EDGE",
     "expected_fit": True, "expected_critical_boundary_m": 340.0, "expected_rear_margin_m": 8.0},
    {"marker_id": "STOP-A-P2-DEP", "train_length_m": HSR_REF_LENGTH_M, "traversal": "WITH_EDGE",
     "expected_fit": True, "expected_critical_boundary_m": 40.0, "expected_rear_margin_m": 458.0},
    {"marker_id": "STOP-A-P2-ARR", "train_length_m": REG_REF_LENGTH_M, "traversal": "AGAINST_EDGE",
     "expected_fit": True, "expected_critical_boundary_m": 880.0, "expected_rear_margin_m": 520.0},
    {"marker_id": "STOP-C-P1-DEP", "train_length_m": HSR_REF_LENGTH_M, "traversal": "WITH_EDGE",
     "expected_fit": True, "expected_critical_boundary_m": 150.0, "expected_rear_margin_m": 3.0},
    {"marker_id": "STOP-C-P2-ARR", "train_length_m": HSR_REF_LENGTH_M, "traversal": "AGAINST_EDGE",
     "expected_fit": True, "expected_critical_boundary_m": 11000.0, "expected_rear_margin_m": 10498.0},
    {"marker_id": "STOP-C-P3-DEP", "train_length_m": HSR_REF_LENGTH_M, "traversal": "WITH_EDGE",
     "expected_fit": True, "expected_critical_boundary_m": 100.0, "expected_rear_margin_m": 7698.0},
    {"marker_id": "STOP-C-P3-ARR", "train_length_m": HSR_REF_LENGTH_M, "traversal": "AGAINST_EDGE",
     "expected_fit": True, "expected_critical_boundary_m": 8300.0, "expected_rear_margin_m": 7898.0},
    {"marker_id": "STOP-C-P4-DEP", "train_length_m": HSR_REF_LENGTH_M, "traversal": "WITH_EDGE",
     "expected_fit": True, "expected_critical_boundary_m": 120.0, "expected_rear_margin_m": 11378.0},
    {"marker_id": STOP_V_P1_R_ID, "train_length_m": HSR_REF_LENGTH_M, "traversal": "AGAINST_EDGE",
     "expected_fit": True, "expected_critical_boundary_m": 1600.0, "expected_rear_margin_m": 1148.0},
    {"marker_id": "STOP-D-P1-DEP", "train_length_m": HSR_REF_LENGTH_M, "traversal": "WITH_EDGE",
     "expected_fit": True, "expected_critical_boundary_m": 90.0, "expected_rear_margin_m": 8.0},
)


# ---------------------------------------------------------------------------
# frozen static benchmarks - accessor
# ---------------------------------------------------------------------------
def grr01_static_benchmark(benchmark_id: str) -> dict[str, Any]:
    """Return a frozen static benchmark as ready-to-evaluate typed objects.

    The returned mapping contains the typed ``track`` and ``platform`` models,
    the ``EdgeTraversal``, the static train length, the front position and the
    frozen expected rear position, critical platform boundary and rear
    clearance/infringement.  The values are static geometry inputs and outputs
    only; no speed, time or train-performance quantity is involved.

    Raises
    ------
    KeyError
        When *benchmark_id* is not one of the five frozen benchmarks.
    """
    from ..models.infrastructure import Platform, Track  # local import: avoid a model/engine cycle

    entry = next(
        (item for item in GRR01_STATIC_BENCHMARKS if item["id"] == benchmark_id), None
    )
    if entry is None:
        raise KeyError(
            f"Unknown GRR-01 static benchmark {benchmark_id!r}; known ids: "
            + ", ".join(item["id"] for item in GRR01_STATIC_BENCHMARKS)
        )
    layer = build_grr01_layer()
    track_record = next(item for item in layer["tracks"] if item["id"] == entry["track_id"])
    platform_record = next(
        item for item in layer["platforms"] if item["id"] == entry["platform_id"]
    )
    return {
        "id": entry["id"],
        "description": entry["description"],
        "marker_id": entry["marker_id"] or "",
        "track": Track.model_validate(track_record),
        "platform": Platform.model_validate(platform_record),
        "front_position_m": entry["front_position_m"],
        "train_length_m": entry["train_length_m"],
        "traversal": EdgeTraversal(entry["traversal"]),
        "critical_boundary_m": entry["critical_boundary_m"],
        "boundary_role": entry["boundary_role"],
        "expected_rear_position_m": entry["expected_rear_position_m"],
        "expected_rear_clearance_m": entry.get("expected_rear_clearance_m"),
        "expected_rear_infringement_m": entry.get("expected_rear_infringement_m"),
    }


def evaluate_grr01_benchmark(benchmark_id: str) -> tuple[Any, dict[str, Any]]:
    """Evaluate one frozen benchmark with the static utility.

    Returns ``(footprint, benchmark)``; the caller compares the footprint
    against the frozen expected values (the fixture itself asserts nothing, so
    that the tests own the expectations).
    """
    benchmark = grr01_static_benchmark(benchmark_id)
    footprint = evaluate_static_footprint(
        benchmark["track"],
        front_position_m=benchmark["front_position_m"],
        train_length_m=benchmark["train_length_m"],
        traversal=benchmark["traversal"],
        marker_id=benchmark["marker_id"],
        platform=benchmark["platform"],
    )
    return footprint, benchmark
