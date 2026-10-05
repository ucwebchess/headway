"""Phase-2 tests: stations, platforms, stopping marks and observation points.

Acceptance tests covered here: TEST P2-017 ... TEST P2-020.
"""

from __future__ import annotations

from railway_headway_sim.infrastructure.mapping import POSITION_TOLERANCE_M

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
# TEST P2-017
# ---------------------------------------------------------------------------
def test_p2_017_station_rules():
    """TEST P2-017 - platform ids resolve and belong to the station; no duplicates."""
    document = grr_document()
    stations = catalogue(document, "stations")
    assert [station["id"] for station in stations] == ["STA-ALPHA", "STA-CEN", "STA-VAL", "STA-DELTA"]
    types = {station["type"] for station in stations}
    assert types <= {"TERMINAL", "INTERMEDIATE"}
    assert sum(1 for station in stations if station["type"] == "TERMINAL") == 2

    platform_ids = {platform["id"] for platform in catalogue(document, "platforms")}
    for station in stations:
        assert set(station["platform_ids"]) <= platform_ids

    # an unknown platform reference is reported
    document = grr_document()
    entry(document, "stations", "STA-CEN")["platform_ids"].append("PLT-NOWHERE")
    unknown = diagnostics_with_code(validate(document).result, "VAL-STATION-002")
    assert unknown and "PLT-NOWHERE" in unknown[0].message

    # a platform of another station is reported
    document = grr_document()
    entry(document, "stations", "STA-ALPHA")["platform_ids"].append("PLT-VAL-P1")
    foreign = diagnostics_with_code(validate(document).result, "VAL-STATION-002")
    assert foreign, "a foreign platform reference must be reported"

    # the same platform listed twice is reported
    document = grr_document()
    entry(document, "stations", "STA-ALPHA")["platform_ids"].append("PLT-ALP-P1")
    assert has_code(validate(document).result, "VAL-STATION-003")


# ---------------------------------------------------------------------------
# TEST P2-018
# ---------------------------------------------------------------------------
def test_p2_018_platform_rules():
    """TEST P2-018 - usable range inside the track, length reconciliation, references."""
    document = grr_document()
    platforms = catalogue(document, "platforms")
    assert len(platforms) == 9
    tracks = {track["id"]: track for track in catalogue(document, "tracks")}
    for platform in platforms:
        track_length = tracks[platform["track_id"]]["length_m"]
        assert 0.0 <= platform["usable_start_m"] < platform["usable_end_m"] <= track_length
        assert abs(
            platform["usable_length_m"] - (platform["usable_end_m"] - platform["usable_start_m"])
        ) <= POSITION_TOLERANCE_M

    document = grr_document()
    entry(document, "platforms", "PLT-CEN-P2")["station_id"] = "STA-NOWHERE"
    assert has_code(validate(document).result, "VAL-PLATFORM-001")

    document = grr_document()
    entry(document, "platforms", "PLT-CEN-P2")["track_id"] = "TR-NOWHERE"
    assert has_code(validate(document).result, "VAL-PLATFORM-002")

    document = grr_document()
    entry(document, "platforms", "PLT-CEN-P2")["usable_end_m"] = 12000.0  # > length_m
    assert has_code(validate(document).result, "VAL-PLATFORM-003")

    document = grr_document()
    entry(document, "platforms", "PLT-CEN-P2")["usable_length_m"] = 10000.0
    assert has_code(validate(document).result, "VAL-PLATFORM-004")

    document = grr_document()
    entry(document, "platforms", "PLT-CEN-P2")["stopping_mark_ids"].append("STOP-NOWHERE")
    assert has_code(validate(document).result, "VAL-PLATFORM-005")

    # resource_id is an optional forward reference and is deliberately *not* resolved
    document = grr_document()
    entry(document, "platforms", "PLT-CEN-P2")["resource_id"] = "RES-LATER-PHASE"
    result = validate(document).result
    assert result.error_count == 0
    assert not has_code(result, "VAL-PLATFORM-002")


# ---------------------------------------------------------------------------
# TEST P2-019
# ---------------------------------------------------------------------------
def test_p2_019_stopping_mark_rules():
    """TEST P2-019 - mark track, position bounds, usable range, direction; chainage derived."""
    document = grr_document()
    marks = catalogue(document, "stopping_marks")
    assert len(marks) == 14
    tracks = {track["id"]: track for track in catalogue(document, "tracks")}
    platforms = {platform["id"]: platform for platform in catalogue(document, "platforms")}
    for mark in marks:
        platform = platforms[mark["platform_id"]]
        assert mark["track_id"] == platform["track_id"]
        assert 0.0 <= mark["position_m"] <= tracks[mark["track_id"]]["length_m"]
        assert platform["usable_start_m"] <= mark["position_m"] <= platform["usable_end_m"]
        assert mark["direction"] in {"FORWARD", "REVERSE"}

    document = grr_document()
    entry(document, "stopping_marks", "STOP-C-P2-DEP")["platform_id"] = "PLT-NOWHERE"
    assert has_code(validate(document).result, "VAL-STOP-001")

    document = grr_document()
    entry(document, "stopping_marks", "STOP-C-P2-DEP")["track_id"] = "TR-A-W-U1"
    assert has_code(validate(document).result, "VAL-STOP-002")

    document = grr_document()
    entry(document, "stopping_marks", "STOP-C-P2-DEP")["position_m"] = 12000.0
    assert has_code(validate(document).result, "VAL-STOP-003")

    document = grr_document()
    entry(document, "stopping_marks", "STOP-C-P2-DEP")["position_m"] = 100.0  # below usable start
    assert has_code(validate(document).result, "VAL-STOP-004")

    document = grr_document()
    entry(document, "stopping_marks", "STOP-C-P2-DEP")["track_id"] = "TR-NOWHERE"
    assert has_code(validate(document).result, "VAL-STOP-005")

    # the authorised location is track_id + position_m; the chainage is derived
    compiled = compile_document()
    mark = compiled.by_id("stopping_marks")["STOP-C-P2-DEP"]
    track = compiled.by_id("tracks")[mark.track_id]
    from railway_headway_sim.infrastructure.mapping import edge_position_to_chainage

    derived = edge_position_to_chainage(track, mark.position_m)
    assert abs(derived - (15.5 + mark.position_m / 1000.0)) < 1e-9
    assert "chainage" not in mark.model_dump()  # no stored, authoritative chainage field


# ---------------------------------------------------------------------------
# TEST P2-020
# ---------------------------------------------------------------------------
def test_p2_020_observation_point_rules():
    """TEST P2-020 - SERVICE_EVENT / CROSS_SECTION / TRACK_CROSS_SECTION members."""
    document = grr_document()
    observations = catalogue(document, "observation_points")
    assert len(observations) == 9
    types = {observation["type"] for observation in observations}
    assert types == {"SERVICE_EVENT", "CROSS_SECTION", "TRACK_CROSS_SECTION"}

    station_observations = [o for o in observations if o["type"] == "SERVICE_EVENT"]
    assert len(station_observations) == 2
    for observation in station_observations:
        assert observation["station_id"].startswith("STA-")
        assert observation["event"] in {"ARRIVAL", "DEPARTURE", "PASSING", "ORIGIN", "DESTINATION"}

    cross_sections = [o for o in observations if o["type"] == "CROSS_SECTION"]
    assert cross_sections and all(o["node_ids"] for o in cross_sections)

    xc24 = next(o for o in observations if o["id"] == "OBS-XC24")
    assert [member["track_id"] for member in xc24["members"]] == [
        "TR-X-ML1-STRAIGHT",
        "TR-X-ML2-STRAIGHT",
        "TR-X-ML1-ML2",
        "TR-X-ML2-ML1",
    ]
    assert [member["position_m"] for member in xc24["members"]] == [80.0, 80.0, 90.0, 90.0]

    # an unknown station reference is reported
    document = grr_document()
    entry(document, "observation_points", "OBS-REF-FWD-ORIGIN")["station_id"] = "STA-NOWHERE"
    assert has_code(validate(document).result, "VAL-OBS-001")

    # a cross-section node that does not exist is reported
    document = grr_document()
    entry(document, "observation_points", "OBS-C-WEST")["node_ids"] = ["N-NOWHERE"]
    assert has_code(validate(document).result, "VAL-OBS-001")

    # a track cross-section member outside the track is reported
    document = grr_document()
    entry(document, "observation_points", "OBS-XC24")["members"][0]["position_m"] = 5000.0
    assert has_code(validate(document).result, "VAL-OBS-002")

    # a member on an unknown track is reported
    document = grr_document()
    entry(document, "observation_points", "OBS-XC24")["members"][0]["track_id"] = "TR-NOWHERE"
    assert has_code(validate(document).result, "VAL-OBS-001")

    # an incomplete definition is reported
    document = grr_document()
    observation = entry(document, "observation_points", "OBS-REF-FWD-ORIGIN")
    observation.pop("station_id")
    assert has_code(validate(document).result, "VAL-OBS-003")

    document = grr_document()
    layer_of(document)["observation_points"] = [
        {"id": "OBS-EMPTY", "type": "TRACK_CROSS_SECTION", "members": []}
    ]
    assert has_code(validate(document).result, "VAL-OBS-003")
