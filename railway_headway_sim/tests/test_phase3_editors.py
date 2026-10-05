"""Phase-3 acceptance tests: TEST P3-001 … TEST P3-026 (Infrastructure UI).

The suite covers the Phase-3 deliverables exactly as specified:

==================  ===========================================================
TEST P3-001 … 004   version authority, field specs/units, tooltips, editor mode
TEST P3-005 … 011   the editing path: staging, commit/discard, APP-EDIT-002,
                    add/delete with reference refusal, nested catalogue,
                    reference system
TEST P3-012 … 016   the previews and the train-fit checker (derived values only
                    from the package layer)
TEST P3-017 … 019   the schematic: generated from the canonical model, layer
                    control with visibly disabled layers, click-to-focus
TEST P3-020 … 024   sub-tab routing/retention, the Phase-2 page contract, the
                    validation surface, JSON round-trip, and the proof that the
                    UI contains no engineering calculation
TEST P3-025 … 026   ipywidgets public-API regression (bugfix 0.3.1): no private
                    ipywidgets name anywhere in the package, and
                    close_widget_tree releases a real widget tree through the
                    public Widget.close() only
==================  ===========================================================

Every test asserts an explicit PASS/FAIL condition; none of them relaxes or
replaces a Phase-1/Phase-2 expectation.
"""

from __future__ import annotations

import ast
import copy
import json
import pathlib

import pytest

import railway_headway_sim
from railway_headway_sim import version as version_module
from railway_headway_sim.app.project_controller import ProjectController
from railway_headway_sim.infrastructure import grr_fixtures, preview_series
from railway_headway_sim.infrastructure.static_geometry import (
    compute_static_footprint,
    evaluate_static_footprint,
    traversal_for_direction,
)
from railway_headway_sim.io.project_io import document_hash, import_project_from_file, to_normalized_dict
from railway_headway_sim.ui import editing as editing_module
from railway_headway_sim.ui import field_help
from railway_headway_sim.ui.editor_specs import EDITOR_FIELDS, all_engineering_fields, fields_of, spec_of
from railway_headway_sim.validation import codes as code_catalogue

PACKAGE_ROOT = pathlib.Path(railway_headway_sim.__file__).parent
UI_ROOT = PACKAGE_ROOT / "ui"

#: The canonical hash of GRR-01 (frozen Phase-2 reference project).
GRR01_CANONICAL_HASH_PREFIX = "5189aaa2340c1702"


def _controller_with_grr01() -> ProjectController:
    """Return a validated controller holding GRR-01."""
    controller = ProjectController()
    controller.replace_project(
        import_project_from_file("examples/GRR-01.json").project, message="GRR-01 loaded"
    )
    controller.validate_project()
    return controller


def _dummy_footprint(
    *,
    front_position_m: float,
    usable_start_m: float | None,
    usable_end_m: float | None,
    fit_in_track: bool = True,
    fit_in_usable_platform: bool = True,
):
    """Return a minimal footprint-shaped object for the classifier test."""
    from railway_headway_sim.infrastructure.static_geometry import StaticFootprint
    from railway_headway_sim.models.enums import EdgeTraversal

    return StaticFootprint(
        track_id="TR-X",
        marker_id="STOP-X",
        platform_id="PLT-X" if usable_start_m is not None else None,
        train_length_m=100.0,
        traversal=EdgeTraversal.WITH_EDGE,
        front_position_m=front_position_m,
        rear_position_m=front_position_m - 100.0,
        occupied_min_m=front_position_m - 100.0,
        occupied_max_m=front_position_m,
        track_length_m=1000.0,
        fit_in_track=fit_in_track,
        fit_in_usable_platform=fit_in_usable_platform,
        critical_boundary_m=usable_start_m,
        rear_margin_m=0.0,
        front_margin_m=0.0,
        usable_start_m=usable_start_m,
        usable_end_m=usable_end_m,
        front_chainage_km=None,
        rear_chainage_km=None,
    )


# ---------------------------------------------------------------------------
# TEST P3-001
# ---------------------------------------------------------------------------
def test_p3_001_app_version_is_0_3_0_from_the_single_authority():
    """TEST P3-001 - app version 0.9.0 lives in version.py only; schema stays 1.0."""
    assert version_module.APP_VERSION == "0.9.0"
    assert version_module.get_app_version() == "0.9.0"
    assert version_module.SUPPORTED_PROJECT_SCHEMA_VERSIONS == ("1.0",)
    assert version_module.DEFAULT_PROJECT_SCHEMA_VERSION == "1.0"

    # No other module of the package carries the app version literal.
    offenders: list[str] = []
    for path in sorted(PACKAGE_ROOT.rglob("*.py")):
        if path.name == "version.py" or "tests" in path.parts:
            continue
        if "0.9.0" in path.read_text(encoding="utf-8"):
            offenders.append(path.relative_to(PACKAGE_ROOT).as_posix())
    assert offenders == [], f"the app version literal appears outside version.py: {offenders}"

    controller = ProjectController()
    controller.create_new_project(name="Version Check")
    assert controller.state.app_version == version_module.APP_VERSION
    assert controller.state.schema_version == "1.0"
    assert controller.state.app_version == "0.9.0"


# ---------------------------------------------------------------------------
# TEST P3-002
# ---------------------------------------------------------------------------
def test_p3_002_every_engineering_column_carries_a_unit_suffix():
    """TEST P3-002 - the editor column headers carry the unit of their field."""
    engineering = all_engineering_fields()
    assert len(engineering) == 21, "the typed catalogues expose 21 unit-bearing fields"
    for catalogue, field_name in engineering:
        spec = spec_of(catalogue, field_name)
        assert spec is not None, f"{catalogue}.{field_name} has no field specification"
        assert spec.unit, f"{catalogue}.{field_name} carries no unit"
        assert f"[{spec.unit}]" in spec.header, f"{catalogue}.{field_name} header lacks the unit"

    assert spec_of("alignments", "start_chainage_km").header == "start_chainage_km [km]"
    assert spec_of("tracks", "length_m").header == "length_m [m]"
    assert spec_of("speed_restrictions", "speed_kmh").header == "speed_kmh [km/h]"
    assert spec_of("vertical_profile_points", "elevation_m").header == "elevation_m [m]"
    assert spec_of("stopping_marks", "position_m").header == "position_m [m]"

    # id/text/enum fields carry no unit and no bracket suffix.
    assert spec_of("nodes", "type").header == "type"
    assert spec_of("tracks", "id").unit == ""
    assert spec_of("tracks", "id").header == "id"

    # every editable catalogue is present in the editor spec table
    assert set(editing_module.editable_catalogues()) == set(EDITOR_FIELDS)
    assert "vertical_profile_points" in EDITOR_FIELDS


# ---------------------------------------------------------------------------
# TEST P3-003
# ---------------------------------------------------------------------------
def test_p3_003_every_editable_field_has_a_tooltip_from_one_file():
    """TEST P3-003 - all tooltips come from ui/field_help.py (single source)."""
    pytest.importorskip("ipywidgets")
    from railway_headway_sim.ui.table_editor import TableEditor

    missing = field_help.missing_tooltips(list(all_engineering_fields()))
    assert missing == []
    for catalogue, specs in EDITOR_FIELDS.items():
        for spec in specs:
            assert field_help.has_tooltip(catalogue, spec.name), f"{catalogue}.{spec.name}"
            assert spec.tooltip.strip(), f"{catalogue}.{spec.name} tooltip is empty"

    assert field_help.reference_system_tooltip("chainage_origin_name").strip()
    assert field_help.describe_source("alignments", "start_chainage_km")

    # the widget layer uses exactly this text (no second tooltip store)
    controller = _controller_with_grr01()
    table = TableEditor(controller, "tracks")
    tooltip = table.row_widgets("TR-C-P2")["length_m"].tooltip
    assert tooltip == field_help.field_tooltip("tracks", "length_m")

    # every field of the reference system is documented too
    for field_name in editing_module.REFERENCE_SYSTEM_EDITABLE + editing_module.REFERENCE_SYSTEM_FIXED:
        assert field_help.reference_system_tooltip(field_name).strip(), field_name


# ---------------------------------------------------------------------------
# TEST P3-004
# ---------------------------------------------------------------------------
def test_p3_004_standard_and_advanced_modes_share_one_switch():
    """TEST P3-004 - STANDARD/ADVANCED hides only optional columns and is shared."""
    pytest.importorskip("ipywidgets")
    from railway_headway_sim.ui.page_editors import ADVANCED, STANDARD, EditorMode
    from railway_headway_sim.ui.table_editor import TableEditor

    mode = EditorMode()
    assert mode.mode == STANDARD
    seen: list[str] = []
    mode.subscribe(seen.append)
    mode.set_mode(ADVANCED)
    assert mode.mode == ADVANCED and seen == [ADVANCED]
    mode.set_mode(ADVANCED)  # no change -> no notification
    assert seen == [ADVANCED]

    standard = fields_of("observation_points", mode=STANDARD)
    advanced = fields_of("observation_points", mode=ADVANCED)
    assert len(standard) < len(advanced)
    assert {spec.name for spec in standard} <= {spec.name for spec in advanced}
    assert all(not spec.advanced for spec in standard)

    controller = _controller_with_grr01()
    table = TableEditor(controller, "observation_points", mode_provider=mode)
    assert len(table.visible_fields()) == len(advanced)
    mode.set_mode(STANDARD)
    table.refresh()
    assert len(table.visible_fields()) == len(standard)
    assert len(table.headers()) == len(standard)


# ---------------------------------------------------------------------------
# TEST P3-005
# ---------------------------------------------------------------------------
def test_p3_005_staging_never_touches_the_committed_project():
    """TEST P3-005 - a staged edit leaves the committed project and hash untouched."""
    controller = _controller_with_grr01()
    before_hash = controller.current_project_hash
    before_document = to_normalized_dict(controller.project)

    editor = editing_module.InfrastructureEditor(controller)
    outcome = editor.stage_field("speed_restrictions", "SPR-08", "speed_kmh", 45.0)
    assert outcome.ok and outcome.staged
    assert controller.draft_pending
    assert editor.pending_change_count() == 1
    assert editor.draft_status_text().startswith("STAGED")

    assert controller.current_project_hash == before_hash
    assert to_normalized_dict(controller.project) == before_document
    assert controller.state.draft_blocks_export is False  # the draft is valid, but not committed

    controller.discard_draft()
    assert controller.current_project_hash == before_hash


# ---------------------------------------------------------------------------
# TEST P3-006
# ---------------------------------------------------------------------------
def test_p3_006_commit_replaces_and_discard_restores_byte_stable_state():
    """TEST P3-006 - commit applies the draft; discard keeps the canonical hash."""
    controller = _controller_with_grr01()
    canonical = controller.current_project_hash
    assert canonical.startswith(GRR01_CANONICAL_HASH_PREFIX)

    editor = editing_module.InfrastructureEditor(controller)
    assert editor.stage_field("speed_restrictions", "SPR-08", "speed_kmh", 45.0).ok
    committed = controller.commit_draft()
    assert committed.status.value == "VALID"
    assert not controller.draft_pending
    assert controller.current_project_hash != canonical
    stored = [r for r in controller.compiled_infrastructure.catalogue("speed_restrictions") if r.id == "SPR-08"]
    assert stored and stored[0].speed_kmh == 45.0
    committed_hash = controller.current_project_hash

    # a second edit is discarded: the project returns to the committed state
    assert editor.stage_field("speed_restrictions", "SPR-08", "speed_kmh", 20.0).ok
    assert editor.discard_and_report()
    assert not controller.draft_pending
    assert controller.current_project_hash == committed_hash

    # loading the frozen project again and discarding an untouched draft is a no-op
    fresh = _controller_with_grr01()
    assert fresh.current_project_hash == canonical
    fresh.stage_draft(to_normalized_dict(fresh.project), description="no-op")
    fresh.discard_draft()
    assert fresh.current_project_hash == canonical


# ---------------------------------------------------------------------------
# TEST P3-007
# ---------------------------------------------------------------------------
def test_p3_007_invalid_edit_is_rejected_with_a_reused_phase2_code():
    """TEST P3-007 - invalid edits reuse Phase-1/2 codes and block commit/export."""
    controller = _controller_with_grr01()
    baseline = controller.current_project_hash
    editor = editing_module.InfrastructureEditor(controller)

    outcome = editor.stage_field("speed_restrictions", "SPR-08", "speed_kmh", -5.0)
    assert outcome.ok is False and outcome.staged is True
    assert outcome.code == code_catalogue.VAL_GEOM_007
    assert code_catalogue.VAL_GEOM_007 in outcome.codes()
    assert all(code in code_catalogue.ALL_DIAGNOSTIC_CODES for code in outcome.codes())
    assert "APP-EDIT-002" in editor.draft_status_text()

    assert controller.draft_blocks_export is True
    rejected = controller.commit_draft()
    assert any(d.code == code_catalogue.APP_EDIT_002 for d in rejected.diagnostics)
    assert controller.export_json(download=False) is None
    assert controller.state.last_action == "export_rejected"
    assert controller.current_project_hash == baseline

    # the rejected draft stays staged until it is discarded or corrected
    controller.discard_draft()
    assert controller.current_project_hash == baseline


# ---------------------------------------------------------------------------
# TEST P3-008
# ---------------------------------------------------------------------------
def test_p3_008_add_delete_rows_and_reference_refusal():
    """TEST P3-008 - rows can be added and deleted; a referenced row refuses deletion."""
    pytest.importorskip("ipywidgets")
    from railway_headway_sim.ui.table_editor import TableEditor

    controller = _controller_with_grr01()
    controller.discard_draft()
    canonical = controller.current_project_hash
    assert canonical.startswith(GRR01_CANONICAL_HASH_PREFIX)
    table = TableEditor(controller, "speed_restrictions")

    added = table.add_row(
        object_id="SPR-NEW-01",
        values={
            "alignment_id": "ALN-MAIN",
            "start_chainage_km": 0.5,
            "end_chainage_km": 1.5,
            "speed_kmh": 120.0,
            "direction": "BOTH",
            "type": "TEMPORARY",
        },
    )
    assert added.staged is True
    assert added.ok is True, added.message
    assert "SPR-NEW-01" in table.rows()
    assert "SPR-NEW-01" in table._editor.ids("speed_restrictions")
    assert controller.commit_draft().has_errors() is False
    stored = [r for r in controller.compiled_infrastructure.catalogue("speed_restrictions") if r.id == "SPR-NEW-01"]
    assert len(stored) == 1 and stored[0].speed_kmh == 120.0

    removed = table.delete_row("SPR-NEW-01")
    assert removed.ok is True, removed.message
    assert "SPR-NEW-01" not in table.rows()
    assert controller.commit_draft().has_errors() is False
    assert controller.current_project_hash == canonical, "add + delete must be reversible"

    # an added node that no track connects is staged but correctly reported as a
    # broken topology (reused Phase-2 code) instead of being silently accepted
    nodes = TableEditor(controller, "nodes")
    staged_node = nodes.add_row(object_id="N-NEW-01", values={"type": "SWITCH", "chainage_km": 12.0})
    assert staged_node.staged is True and staged_node.ok is False
    assert staged_node.code == code_catalogue.VAL_TOPO_007
    assert nodes.delete_row("N-NEW-01").ok is True
    controller.discard_draft()
    assert controller.current_project_hash == canonical

    # a referenced node cannot be deleted, and the attempt stages nothing
    refused = nodes.delete_row("N-CEN-E")
    assert refused.ok is False and refused.staged is False
    assert "refused" in refused.message
    assert "TR-O-CEN-VAL-ML1" in refused.message  # a referencing track is named
    assert controller.draft_pending is False
    assert controller.current_project_hash == canonical

    # the same rule holds for a platform that stopping marks point at
    platforms = TableEditor(controller, "platforms")
    blocked = platforms.delete_row("PLT-CEN-P2")
    assert blocked.ok is False
    assert "stopping_marks" in blocked.message or "STOP-" in blocked.message


# ---------------------------------------------------------------------------
# TEST P3-009
# ---------------------------------------------------------------------------
def test_p3_009_deleting_an_alignment_names_every_referencing_object():
    """TEST P3-009 - deletion refusal names the referencing objects, incl. the reference system."""
    controller = _controller_with_grr01()
    controller.discard_draft()
    editor = editing_module.InfrastructureEditor(controller)

    references = editor.references_to("alignments", "ALN-MAIN")
    sources = {reference.source_catalogue for reference in references}
    assert {"horizontal_geometry", "vertical_profiles", "speed_restrictions"} <= sources
    assert "<reference_system>" in sources
    assert all(reference.describe() for reference in references)

    refused = editor.delete_entry("alignments", "ALN-MAIN")
    assert refused.ok is False and refused.staged is False
    assert "refused" in refused.message
    assert "reference_system" in refused.message
    assert controller.draft_pending is False
    assert controller.current_project_hash.startswith(GRR01_CANONICAL_HASH_PREFIX)


# ---------------------------------------------------------------------------
# TEST P3-010
# ---------------------------------------------------------------------------
def test_p3_010_nested_vertical_profile_points_are_edited_in_place():
    """TEST P3-010 - profile points are edited inside their owning profile."""
    controller = _controller_with_grr01()
    controller.discard_draft()
    scoped = editing_module.ScopedEditor(
        controller, catalogue="vertical_profile_points", owner_id="VP-MAIN"
    )
    assert scoped.owner_catalogue == "vertical_profiles"
    assert scoped.container_field == "points"
    assert scoped.owner_ids() == ("VP-MAIN",)
    points = scoped.entries("vertical_profile_points")
    assert len(points) == 13
    first_id = points[0]["id"]
    assert scoped.ids("vertical_profile_points")[0] == first_id

    assert scoped.stage_field("vertical_profile_points", first_id, "elevation_m", 123.5).ok
    staged = controller._draft_document["infrastructure"][0]["vertical_profiles"][0]["points"]
    assert staged[0]["elevation_m"] == 123.5
    assert staged[0]["id"] == first_id

    # a new point is placed by its own chainage so the stored order is kept
    assert scoped.stage_entry(
        "vertical_profile_points", {"id": "VPP-90", "chainage_km": 44.5, "elevation_m": 130.0}
    ).ok
    ordered = scoped.ids("vertical_profile_points")
    assert "VPP-90" in ordered
    chainages = [point["chainage_km"] for point in scoped.entries("vertical_profile_points")]
    assert chainages == sorted(chainages), "the stored order stays strictly increasing"
    assert chainages[ordered.index("VPP-90")] == 44.5
    assert scoped.delete_entry("vertical_profile_points", "VPP-90").ok
    assert "VPP-90" not in scoped.ids("vertical_profile_points")

    # a malformed point (missing elevation) is rejected with a reused Phase-2 code
    bad = scoped.stage_entry("vertical_profile_points", {"id": "VPP-91", "chainage_km": 47.5})
    assert bad.ok is False
    assert all(code in code_catalogue.ALL_DIAGNOSTIC_CODES for code in bad.codes())
    controller.discard_draft()

    # the committed project never saw any of it
    assert controller.current_project_hash.startswith(GRR01_CANONICAL_HASH_PREFIX)
    assert controller.project.infrastructure[0]["vertical_profiles"][0]["points"][0]["elevation_m"] == 120.0


# ---------------------------------------------------------------------------
# TEST P3-011
# ---------------------------------------------------------------------------
def test_p3_011_reference_system_fields_are_editable_except_schema_fixed_ones():
    """TEST P3-011 - Line-level reference system editing, with fixed fields refused."""
    controller = _controller_with_grr01()
    controller.discard_draft()
    editor = editing_module.InfrastructureEditor(controller)
    reference = editor.reference_system()
    assert reference.get("alignment_id") == "ALN-MAIN"
    assert reference.get("forward_direction") == "INCREASING_CHAINAGE"

    assert editor.stage_reference_field("chainage_origin_name", "Alpha Central").ok
    staged = controller._draft_document["reference_system"]
    assert staged["chainage_origin_name"] == "Alpha Central"
    assert editor.reference_value("chainage_origin_name") == "Alpha Central"

    for fixed in ("forward_direction", "reverse_direction"):
        refused = editor.stage_reference_field(fixed, "DECREASING_CHAINAGE")
        assert refused.ok is False and refused.staged is False
        assert "not editable" in refused.message
    unknown = editor.stage_reference_field("not_a_field", 1)
    assert unknown.ok is False

    # the pushed draft is still a valid document
    assert controller.draft_result is not None
    assert controller.draft_result.has_errors() is False
    controller.discard_draft()
    assert controller.current_project_hash.startswith(GRR01_CANONICAL_HASH_PREFIX)


# ---------------------------------------------------------------------------
# TEST P3-012
# ---------------------------------------------------------------------------
def test_p3_012_gradient_preview_follows_the_direction_without_mutating_data():
    """TEST P3-012 - gradient between adjacent points; FORWARD/REVERSE is display only."""
    controller = _controller_with_grr01()
    canonical = controller.current_project_hash
    points = controller.project.infrastructure[0]["vertical_profiles"][0]["points"]

    forward = preview_series.gradient_segments(points, direction="FORWARD")
    reverse = preview_series.gradient_segments(points, direction="REVERSE")
    assert len(forward) == len(points) - 1 == 12
    assert len(reverse) == len(forward)
    assert [(s.start_km, s.end_km) for s in reverse] == [
        (s.start_km, s.end_km) for s in reversed(forward)
    ]

    for index, segment in enumerate(forward):
        start = points[index]
        end = points[index + 1]
        expected = (end["elevation_m"] - start["elevation_m"]) / (end["chainage_km"] - start["chainage_km"])
        assert segment.start_km == start["chainage_km"]
        assert segment.end_km == end["chainage_km"]
        assert segment.gradient_permille == pytest.approx(expected)
        assert reverse[len(forward) - 1 - index].gradient_permille == pytest.approx(-expected)

    # the preview series never mutates the stored points, and switching the
    # controller direction does not change the project or its hash
    assert points == controller.project.infrastructure[0]["vertical_profiles"][0]["points"]
    from railway_headway_sim.models.enums import Direction

    controller.set_direction(Direction.REVERSE)
    assert controller.direction is Direction.REVERSE
    assert controller.current_project_hash == canonical
    controller.set_direction(Direction.FORWARD)
    assert controller.current_project_hash == canonical


# ---------------------------------------------------------------------------
# TEST P3-013
# ---------------------------------------------------------------------------
def test_p3_013_curvature_preview_uses_only_the_stored_radius():
    """TEST P3-013 - the curvature series carries stored radius/handedness, nothing derived."""
    controller = _controller_with_grr01()
    sections = controller.project.infrastructure[0]["horizontal_geometry"]
    series = preview_series.curvature_segments(sections)
    assert len(series) == len(sections)

    by_id = {section["id"]: section for section in sections}
    for segment in series:
        stored = by_id[segment.id]
        assert segment.start_km == stored["start_chainage_km"]
        assert segment.end_km == stored["end_chainage_km"]
        assert segment.section_type == stored["type"]
        assert segment.radius_m == stored.get("radius_m")
        assert segment.handedness == stored.get("handedness")
        if stored["type"] == "STRAIGHT":
            assert segment.radius_m is None
            assert "STRAIGHT" in segment.describe()
        else:
            assert segment.radius_m is not None and segment.radius_m > 0
            assert f"{segment.radius_m:g}" in segment.describe()

    # a curve without a radius yields no radius in the series either (no invention)
    synthetic = [{"id": "HGR-X", "start_chainage_km": 0.0, "end_chainage_km": 1.0, "type": "CURVE"}]
    derived = preview_series.curvature_segments(synthetic)
    assert derived[0].radius_m is None
    assert "radius" not in derived[0].describe()


# ---------------------------------------------------------------------------
# TEST P3-014
# ---------------------------------------------------------------------------
def test_p3_014_effective_speed_is_direction_filtered_and_most_restrictive_wins():
    """TEST P3-014 - effective speed per direction; the lowest limit wins."""
    controller = _controller_with_grr01()
    restrictions = controller.project.infrastructure[0]["speed_restrictions"]

    forward = preview_series.effective_speed_segments(restrictions, direction="FORWARD")
    reverse = preview_series.effective_speed_segments(restrictions, direction="REVERSE")
    forward_ids = {rid for segment in forward for rid in segment.restriction_ids}
    reverse_ids = {rid for segment in reverse for rid in segment.restriction_ids}
    assert "SPR-08" not in forward_ids, "SPR-08 is declared for REVERSE only"
    assert "SPR-08" in reverse_ids
    sprint = [s for s in reverse if "SPR-08" in s.restriction_ids]
    assert len(sprint) == 1
    assert (sprint[0].start_km, sprint[0].end_km) == (42.0, 44.0)
    assert sprint[0].speed_kmh == 240.0
    assert preview_series.effective_speed_at(reverse, 43.0) == 240.0
    assert preview_series.effective_speed_at(forward, 43.0) == 260.0  # SPR-06 only

    # most restrictive wins, independent of the fixture: 100 over 60 over 80 -> 60
    overlapping = [
        {"id": "A", "start_chainage_km": 0.0, "end_chainage_km": 2.0, "speed_kmh": 100.0, "direction": "BOTH"},
        {"id": "B", "start_chainage_km": 1.0, "end_chainage_km": 3.0, "speed_kmh": 60.0, "direction": "BOTH"},
        {"id": "C", "start_chainage_km": 1.5, "end_chainage_km": 4.0, "speed_kmh": 80.0, "direction": "BOTH"},
    ]
    segments = preview_series.effective_speed_segments(overlapping, direction="FORWARD")
    assert preview_series.effective_speed_at(segments, 0.5) == 100.0
    assert preview_series.effective_speed_at(segments, 1.25) == 60.0
    assert preview_series.effective_speed_at(segments, 2.5) == 60.0
    assert preview_series.effective_speed_at(segments, 3.5) == 80.0
    # BOTH/PERMANENT_DIRECTIONAL semantics come from the stored direction value
    directional = [
        {"id": "D", "start_chainage_km": 0.0, "end_chainage_km": 1.0, "speed_kmh": 90.0,
         "direction": "FORWARD"},
    ]
    assert preview_series.effective_speed_segments(directional, direction="FORWARD")
    assert preview_series.effective_speed_segments(directional, direction="REVERSE") == ()


# ---------------------------------------------------------------------------
# TEST P3-015
# ---------------------------------------------------------------------------
def test_p3_015_train_fit_classification_covers_the_three_outcomes():
    """TEST P3-015 - FIT / TOO_LONG / MARKER_OUTSIDE_USABLE classification."""
    assert preview_series.train_fit_outcome(
        _dummy_footprint(front_position_m=200.0, usable_start_m=100.0, usable_end_m=400.0)
    ) == preview_series.FIT
    assert preview_series.train_fit_outcome(
        _dummy_footprint(
            front_position_m=200.0, usable_start_m=100.0, usable_end_m=400.0,
            fit_in_usable_platform=False,
        )
    ) == preview_series.TOO_LONG
    assert preview_series.train_fit_outcome(
        _dummy_footprint(
            front_position_m=200.0, usable_start_m=100.0, usable_end_m=400.0, fit_in_track=False
        )
    ) == preview_series.TOO_LONG
    assert preview_series.train_fit_outcome(
        _dummy_footprint(front_position_m=50.0, usable_start_m=100.0, usable_end_m=400.0)
    ) == preview_series.MARKER_OUTSIDE_USABLE
    assert preview_series.marker_within_usable(None, 0.0, 10.0) is None

    # real GRR-01 data: the frozen marks classify as recorded
    controller = _controller_with_grr01()
    compiled = controller.compiled_infrastructure
    outcomes: dict[str, str] = {}
    for mark in compiled.catalogue("stopping_marks"):
        track = compiled.by_id("tracks")[mark.track_id]
        platform = compiled.by_id("platforms").get(mark.platform_id) if mark.platform_id else None
        footprint = compute_static_footprint(
            track,
            mark,
            grr_fixtures.HSR_REF_LENGTH_M,
            traversal_for_direction(mark.direction),
            platform=platform,
        )
        outcomes[mark.id] = preview_series.train_fit_outcome(footprint)
    assert outcomes["STOP-A-P1-DEP"] == preview_series.FIT
    assert outcomes["STOP-A-P1-ARR"] == preview_series.FIT
    assert outcomes["STOP-C-P2-DEP"] == preview_series.TOO_LONG
    assert outcomes["STOP-C-P1-ARR"] == preview_series.TOO_LONG
    assert sum(1 for value in outcomes.values() if value == preview_series.FIT) == 12

    # MARKER_OUTSIDE_USABLE on real geometry: move the front position outside the
    # usable range through the package utility (no UI code involved)
    mark = compiled.by_id("stopping_marks")["STOP-A-P1-DEP"]
    track = compiled.by_id("tracks")[mark.track_id]
    platform = compiled.by_id("platforms")[mark.platform_id]
    outside = evaluate_static_footprint(
        track,
        front_position_m=platform.usable_start_m - 1.0,
        train_length_m=grr_fixtures.HSR_REF_LENGTH_M,
        traversal=traversal_for_direction(mark.direction),
        marker_id=mark.id,
        platform=platform,
    )
    assert preview_series.train_fit_outcome(outside) == preview_series.MARKER_OUTSIDE_USABLE


# ---------------------------------------------------------------------------
# TEST P3-016
# ---------------------------------------------------------------------------
def test_p3_016_train_fit_checker_widget_is_read_only_and_uses_the_package_utility():
    """TEST P3-016 - the checker shows the package result; the length is never stored."""
    pytest.importorskip("ipywidgets")
    from railway_headway_sim.ui.stations_page import StationsPage

    controller = _controller_with_grr01()
    canonical = controller.current_project_hash
    page = StationsPage(controller)
    checker = page._editors.train_fit
    assert checker.evaluation_length() == float(grr_fixtures.HSR_REF_LENGTH_M)

    checker._marker.value = "STOP-A-P1-DEP"
    checker.refresh()
    assert checker.outcome() == preview_series.FIT

    checker._marker.value = "STOP-C-P2-DEP"
    checker.refresh()
    assert checker.outcome() == preview_series.TOO_LONG
    assert "TOO_LONG" in checker._result.value

    # the page's evaluation-length control drives both the footprint table and the check
    page._length_selector.value = float(grr_fixtures.REG_REF_LENGTH_M)
    assert page.field_values()["evaluation_length_m"] == float(grr_fixtures.REG_REF_LENGTH_M)
    assert checker.evaluation_length() == float(grr_fixtures.REG_REF_LENGTH_M)
    assert checker.outcome() in (preview_series.FIT, preview_series.TOO_LONG)

    # the evaluation length is application state only
    assert controller.current_project_hash == canonical
    assert "train_length" not in json.dumps(to_normalized_dict(controller.project))


# ---------------------------------------------------------------------------
# TEST P3-017
# ---------------------------------------------------------------------------
def test_p3_017_schematic_is_generated_from_the_canonical_model():
    """TEST P3-017 - every drawn element exists in the loaded document."""
    from railway_headway_sim.ui import schematic_render

    controller = _controller_with_grr01()
    layer = controller.project.infrastructure[0]
    drawing = schematic_render.render_schematic(layer, direction="FORWARD")

    expected = {
        "tracks": len(layer["tracks"]),
        "stations": len(layer["stations"]),
        "platforms": len(layer["platforms"]),
        "stopping_marks": len(layer["stopping_marks"]),
        "nodes": len(layer["nodes"]),
        "speed_restrictions": len(layer["speed_restrictions"]),
        "observation_points": len(layer["observation_points"]),
    }
    assert dict(drawing.counts) == expected

    catalogues = {
        "track": "tracks",
        "station": "stations",
        "platform": "platforms",
        "stopping_mark": "stopping_marks",
        "node": "nodes",
        "speed_restriction": "speed_restrictions",
        "observation_point": "observation_points",
    }
    for target in drawing.hit_targets:
        catalogue = catalogues[target.kind]
        ids = {record["id"] for record in layer[catalogue]}
        assert target.object_id in ids, f"{target.kind} {target.object_id} is not in the model"
        assert f'data-object-id="{target.object_id}"' in drawing.svg
        assert target.catalogue == catalogue

    assert drawing.chainage_range == (0.0, 50.0)
    assert drawing.target_for("TR-C-P2") is not None
    assert drawing.target_for("does-not-exist") is None
    assert "LYR-MAIN".lower() not in drawing.svg  # the drawing holds no layer name


# ---------------------------------------------------------------------------
# TEST P3-018
# ---------------------------------------------------------------------------
def test_p3_018_layer_control_reports_inactive_layers_without_drawing_them():
    """TEST P3-018 - four layers render; the four others are visibly disabled."""
    pytest.importorskip("ipywidgets")
    from railway_headway_sim.ui import schematic_render
    from railway_headway_sim.ui.schematic_page import SchematicView

    assert schematic_render.SCHEMATIC_LAYERS == (
        "Tracks", "Stations", "Platforms", "Signals", "TVPs/Resources", "Speed",
        "Routes", "Simulation Occupancy",
    )
    assert schematic_render.ACTIVE_LAYERS == ("Tracks", "Stations", "Platforms", "Speed")
    for name, reason in schematic_render.INACTIVE_LAYER_REASONS.items():
        assert name in schematic_render.SCHEMATIC_LAYERS
        assert "inactive in Phase 3" in reason

    controller = _controller_with_grr01()
    view = SchematicView(controller)
    for name, box in view._layer_flags.items():
        if name in schematic_render.ACTIVE_LAYERS:
            assert box.disabled is False and box.value is True
            assert "rendered from the canonical model" in box.tooltip
        else:
            assert box.disabled is True and box.value is False
            assert "inactive" in box.tooltip
    assert view.inactive_layers() == (
        "Signals", "TVPs/Resources", "Routes", "Simulation Occupancy",
    )
    assert view.layer_states()["Signals"] == "INACTIVE"
    assert "Signals=INACTIVE" in view._layer_state.value
    assert "Disabled layers have no Phase-3 renderer" in view._layer_state.value

    layer = controller.project.infrastructure[0]
    forced = schematic_render.render_schematic(
        layer, layers={name: True for name in schematic_render.SCHEMATIC_LAYERS}
    )
    default = schematic_render.render_schematic(layer)
    assert dict(forced.counts) == dict(default.counts), "inactive layers must add nothing"
    assert "Disabled layers (no Phase-3 renderer): Signals" in forced.svg

    hidden = schematic_render.render_schematic(layer, layers={"Tracks": False, "Stations": False})
    assert hidden.counts.get("tracks") is None and hidden.counts.get("stations") is None
    assert hidden.counts.get("platforms") is not None


# ---------------------------------------------------------------------------
# TEST P3-019
# ---------------------------------------------------------------------------
def test_p3_019_click_surface_focuses_objects_and_marks_errors_with_text():
    """TEST P3-019 - schematic selection routes to the owning editor row."""
    pytest.importorskip("ipywidgets")
    from railway_headway_sim.ui import schematic_render
    from railway_headway_sim.ui.infrastructure_page import InfrastructurePage
    from railway_headway_sim.ui.stations_page import StationsPage

    controller = _controller_with_grr01()
    page = InfrastructurePage(controller)
    assert page.focus_object("TR-C-P2") is True
    assert page.selected_sub_tab() == "Tracks"
    assert page.editor_tables()["tracks"].focused_id() == "TR-C-P2"

    assert page.focus_object("SPR-08") is True
    assert page.selected_sub_tab() == "Speed"
    assert page.focus_object("VPP-01") is True
    assert page.selected_sub_tab() == "Geometry"

    # a station does not exist on the infrastructure page: the page says so instead
    # of silently doing nothing
    assert page.focus_object("STA-ALPHA") is False

    stations = StationsPage(controller)
    assert stations.focus_object("PLT-CEN-P2") is True
    assert stations.selected_sub_tab() == "Platforms"
    assert stations.focus_object("STOP-C-P2-DEP") is True
    assert stations.selected_sub_tab() == "Stopping Marks"

    # the schematic marks errors with text plus the code, never colour alone
    view = page._editors.schematic.view()
    drawing = schematic_render.render_schematic(
        controller.project.infrastructure[0],
        error_ids=["TR-C-P2"],
        error_codes={"TR-C-P2": code_catalogue.VAL_TOPO_001},
    )
    assert "! ERROR VAL-TOPO-001" in drawing.svg
    assert drawing.error_ids == ("TR-C-P2",)

    view.select_object("STA-ALPHA")
    assert view.selected_id() == "STA-ALPHA"
    assert "STA-ALPHA" in view.drawing().svg

    # opening an object that lives on another page leaves this page's selection alone
    tab_before = page.selected_sub_tab()
    page._editors._handle_open_object("station", "STA-ALPHA")
    assert page.selected_sub_tab() == tab_before
    # opening an object of this page follows it
    page._editors._handle_open_object("speed_restriction", "SPR-08")
    assert page.selected_sub_tab() == "Speed"


# ---------------------------------------------------------------------------
# TEST P3-020
# ---------------------------------------------------------------------------
def test_p3_020_sub_tabs_are_exact_and_selection_survives_a_refresh():
    """TEST P3-020 - the required sub-tabs exist and keep their state in the session."""
    pytest.importorskip("ipywidgets")
    from railway_headway_sim.ui.infrastructure_page import InfrastructurePage
    from railway_headway_sim.ui.stations_page import StationsPage

    controller = _controller_with_grr01()
    page = InfrastructurePage(controller)
    assert page.sub_tab_titles() == ("Line", "Tracks", "Geometry", "Speed", "Schematic")
    stations = StationsPage(controller)
    assert stations.sub_tab_titles() == (
        "Stations", "Platforms", "Stopping Marks", "Observation Points",
    )
    assert page.select_sub_tab("Geometry") is True
    assert page.select_sub_tab("Nope") is False

    # switching sub-tabs must not discard a staged draft
    editor = editing_module.InfrastructureEditor(controller)
    assert editor.stage_field("speed_restrictions", "SPR-08", "speed_kmh", 42.0).ok
    assert controller.draft_pending
    page.select_sub_tab("Tracks")
    stations.select_sub_tab("Platforms")
    controller.report_ui_message("refresh after tab switch")
    assert controller.draft_pending, "switching tabs discarded the draft"
    assert editor.pending_change_count() == 1
    assert page.selected_sub_tab() == "Tracks"
    assert stations.selected_sub_tab() == "Platforms"

    page.select_sub_tab("Schematic")
    controller.report_ui_message("another refresh")
    assert page.selected_sub_tab() == "Schematic"
    controller.discard_draft()


# ---------------------------------------------------------------------------
# TEST P3-021
# ---------------------------------------------------------------------------
def test_p3_021_the_pages_keep_the_phase2_inspection_contract():
    """TEST P3-021 - every Phase-2 page attribute still exists and shows the frozen data."""
    pytest.importorskip("ipywidgets")
    from railway_headway_sim.ui import AppShell, InfrastructurePage, NAVIGATION_TITLES, StationsPage

    controller = _controller_with_grr01()
    shell = AppShell(controller)
    hash_before = controller.current_project_hash

    infrastructure_index = list(NAVIGATION_TITLES).index("Infrastructure")
    stations_index = list(NAVIGATION_TITLES).index("Stations & Platforms")
    assert isinstance(shell._tabs.children[infrastructure_index], type(shell._infrastructure_page.widget))
    assert isinstance(shell._tabs.children[stations_index], type(shell._stations_page.widget))

    page = shell._infrastructure_page
    assert isinstance(page, InfrastructurePage)
    for count in grr_fixtures.GRR01_EXPECTED_COUNTS.values():
        assert str(count) in page._inventory.value
    assert "LYR-MAIN" in page._overview.value
    assert "PHASE-2 PHYSICAL INFRASTRUCTURE" in page._overview.value
    assert "N-ALP-W" in page._nodes.value and "TR-C-P2" in page._edges.value
    assert "SPR-08" in page._speed.value
    assert "Connected components" in page._topology_summary.value and ">1<" in page._topology_summary.value

    page._sequence_input.value = "TR-C-E-X-U1, TR-O-CEN-VAL-ML1"
    page._handle_sequence_check(None)
    assert "continuous" in page._sequence_result.value.lower()
    page._sequence_input.value = "TR-C-P1, TR-O-CEN-VAL-ML1"
    page._handle_sequence_check(None)
    assert "break" in page._sequence_result.value.lower()

    stations = shell._stations_page
    assert isinstance(stations, StationsPage)
    assert "STA-ALPHA" in stations._stations.value and "STA-DELTA" in stations._stations.value
    assert "PLT-CEN-P2" in stations._platforms.value
    assert "STOP-C-P2-DEP" in stations._marks.value
    assert "STOP-C-P2-DEP" in stations._footprints.value
    assert "infringement" in stations._footprints.value
    assert "OBS-XC24" in stations._observations.value

    assert controller.current_project_hash == hash_before
    assert shell._controller.project is controller.project


# ---------------------------------------------------------------------------
# TEST P3-022
# ---------------------------------------------------------------------------
def test_p3_022_validation_surface_uses_only_existing_codes():
    """TEST P3-022 - row badges, category counts and focus actions; no new codes."""
    pytest.importorskip("ipywidgets")
    from railway_headway_sim.ui.infrastructure_page import InfrastructurePage

    controller = _controller_with_grr01()
    page = InfrastructurePage(controller)
    summary = page._validation
    editor = page.editor

    clean = editor.diagnostics_by_category()
    assert set(clean) == {"schema", "geometry", "topology", "operations"}
    assert all(values["errors"] == 0 for values in clean.values())

    bad = editor.stage_field("speed_restrictions", "SPR-08", "speed_kmh", -5.0)
    assert bad.ok is False
    counts = editor.diagnostics_by_category()
    assert counts["geometry"]["errors"] >= 1
    summary.refresh()
    assert "Geometry" in summary._counts.value
    assert code_catalogue.VAL_GEOM_007 in summary._detail.value
    assert any(value == "SPR-08" for _label, value in summary._targets.options)
    assert editor.error_badge("SPR-08").startswith("ERROR VAL-")
    assert page.editor_tables()["speed_restrictions"].badge_of("SPR-08").startswith("ERROR VAL-")
    assert "APP-EDIT-002" in page._draft_bar.status_text() or page._draft_bar.status_text() == "REJECTED"

    # click-to-focus from the validation summary reaches the owning editor row
    page._validation._targets.value = "SPR-08"
    page._validation._handle_focus(None)
    assert page.selected_sub_tab() == "Speed"
    assert page.editor_tables()["speed_restrictions"].focused_id() == "SPR-08"

    # no new validation code exists: the UI only names codes of the Phase-1/2 catalogue
    import re

    pattern = re.compile(r"\b(?:VAL|APP)-[A-Z]+-\d{3}\b")
    found: dict[str, list[str]] = {}
    for path in sorted(UI_ROOT.glob("*.py")):
        for code in pattern.findall(path.read_text(encoding="utf-8")):
            found.setdefault(code, []).append(path.name)
    assert found, "the UI should reference the reused application codes"
    unknown = {code: files for code, files in found.items() if code not in code_catalogue.ALL_DIAGNOSTIC_CODES}
    assert unknown == {}, f"the UI references codes that are not in the catalogue: {unknown}"
    assert all(code in code_catalogue.ALL_DIAGNOSTIC_CODES for code in bad.codes())
    controller.discard_draft()


# ---------------------------------------------------------------------------
# TEST P3-023
# ---------------------------------------------------------------------------
def test_p3_023_json_import_export_stays_authoritative(tmp_path):
    """TEST P3-023 - export/import remain available and keep the canonical hash."""
    pytest.importorskip("ipywidgets")
    from railway_headway_sim.ui.infrastructure_page import InfrastructurePage
    from railway_headway_sim.ui.project_page import ProjectPage

    controller = _controller_with_grr01()
    assert controller.current_project_hash.startswith(GRR01_CANONICAL_HASH_PREFIX)

    page = InfrastructurePage(controller)
    assert hasattr(page._json_panel, "_import_button") and hasattr(page._json_panel, "_export_button")
    project_page = ProjectPage(controller)
    assert hasattr(project_page, "_export_button") and hasattr(project_page, "_import_button")

    outcome = controller.export_json(download=False, directory=str(tmp_path))
    assert outcome is not None
    exported = pathlib.Path(outcome.written_path)
    document = json.loads(exported.read_text(encoding="utf-8"))
    assert document_hash(document).startswith(GRR01_CANONICAL_HASH_PREFIX)

    reimported = ProjectController()
    result = reimported.import_json_data(document, source_name="roundtrip.json")
    assert result.has_errors() is False
    assert reimported.current_project_hash == controller.current_project_hash

    # an INVALID draft disables the export button of the JSON panel
    editor = page.editor
    editor.stage_field("speed_restrictions", "SPR-08", "speed_kmh", -1.0)
    page._json_panel.refresh()
    assert page._json_panel._export_button.disabled is True
    assert "blocked" in page._json_panel._message.value
    controller.discard_draft()
    page._json_panel.refresh()
    assert page._json_panel._export_button.disabled is False


# ---------------------------------------------------------------------------
# TEST P3-024
# ---------------------------------------------------------------------------
def test_p3_024_no_engineering_calculation_in_the_ui():
    """TEST P3-024 - the UI renders stored/package values; it computes no engineering value."""
    forbidden_names = (
        "headway", "blocking_time", "occupation_time", "residual_occupancy",
        "speed_envelope", "traction", "davis", "roeckl", "braking_curve",
        "monte_carlo", "uic406",
    )
    offenders: list[str] = []
    for path in sorted(UI_ROOT.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                lowered = node.name.lower()
                if any(name in lowered for name in forbidden_names):
                    offenders.append(f"{path.name}:{node.name}")
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split(".")[0] in {"math", "numpy", "scipy", "statistics", "random"}:
                        offenders.append(f"{path.name}: imports {alias.name}")
            if isinstance(node, ast.ImportFrom) and (node.module or "").split(".")[0] in {
                "math", "numpy", "scipy", "statistics", "random",
            }:
                offenders.append(f"{path.name}: from {node.module} import ...")
    assert offenders == [], f"the UI must not carry engineering computation: {offenders}"

    # the only controller method the editing layer uses to change data is stage_draft
    mutating = {"stage_draft", "commit_draft", "discard_draft"}
    used: set[str] = set()
    tree = ast.parse((UI_ROOT / "editing.py").read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Attribute)
            and isinstance(node.value.value, ast.Name)
            and node.value.value.id == "self"
            and node.value.attr == "_controller"
        ):
            used.add(node.attr)
    assert mutating <= used, f"the editing layer must stage through the draft mechanism: {used}"
    assert used - {
        "project", "stage_draft", "draft_result", "draft_pending", "draft_blocks_export",
        "state", "validation", "subscribe", "commit_draft", "discard_draft",
        "compiled_infrastructure", "current_project_hash", "report_ui_message",
        "_draft_document",
    } == set(), f"unexpected controller surface in the editing layer: {used}"

    # the derived series stay in the package layer and are rendered unchanged
    pytest.importorskip("ipywidgets")
    from railway_headway_sim.ui.preview_panel import GeometryPreview, SpeedPreview

    controller = _controller_with_grr01()
    geometry = GeometryPreview(controller)
    assert geometry.gradient_segments() == preview_series.gradient_segments(
        controller.project.infrastructure[0]["vertical_profiles"][0]["points"],
        direction=controller.direction,
    )
    assert geometry.curvature_segments() == preview_series.curvature_segments(
        controller.project.infrastructure[0]["horizontal_geometry"]
    )
    assert geometry.elevation_points() == preview_series.elevation_series(
        controller.project.infrastructure[0]["vertical_profiles"][0]["points"]
    )
    speed = SpeedPreview(controller)
    assert speed.segments() == preview_series.effective_speed_segments(
        controller.project.infrastructure[0]["speed_restrictions"], direction=controller.direction
    )
    assert geometry.elevation_points()[0] == (
        controller.project.infrastructure[0]["vertical_profiles"][0]["points"][0]["chainage_km"],
        controller.project.infrastructure[0]["vertical_profiles"][0]["points"][0]["elevation_m"],
    )

    # the preview widgets do not change any state when refreshed or when the mode changes
    before = copy.deepcopy(to_normalized_dict(controller.project))
    geometry.refresh()
    speed.refresh()
    from railway_headway_sim.models.enums import Direction

    controller.set_direction(Direction.REVERSE)
    geometry.refresh()
    speed.refresh()
    controller.set_direction(Direction.FORWARD)
    assert to_normalized_dict(controller.project) == before
    assert controller.project.infrastructure[0] == before["infrastructure"][0]


# ---------------------------------------------------------------------------
# TEST P3-025
# ---------------------------------------------------------------------------
def test_p3_025_package_uses_only_the_public_ipywidgets_api():
    """TEST P3-025 - no module imports a private name from ipywidgets."""
    findings: list[str] = []
    for path in sorted(PACKAGE_ROOT.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        relative = path.relative_to(PACKAGE_ROOT).as_posix()
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        ipywidgets_names: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "ipywidgets" or alias.name.startswith("ipywidgets."):
                        ipywidgets_names.add(alias.asname or alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if module != "ipywidgets" and not module.startswith("ipywidgets."):
                    continue
                for alias in node.names:
                    if alias.name == "*":
                        findings.append(f"{relative}:{node.lineno}: from {module} import *")
                    elif alias.name.startswith("_"):
                        findings.append(
                            f"{relative}:{node.lineno}: from {module} import {alias.name}"
                        )
                    else:
                        ipywidgets_names.add(alias.asname or alias.name)
        # Attribute access on a name that came from ipywidgets, e.g. ``widgets.widgets._x``.
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr.startswith("_"):
                root = node
                while isinstance(root, ast.Attribute):
                    root = root.value
                if isinstance(root, ast.Name) and root.id in ipywidgets_names:
                    findings.append(f"{relative}:{node.lineno}: {root.id}.{node.attr}")
    assert findings == [], (
        "the package must use only the public ipywidgets API; private ipywidgets names found: "
        + "; ".join(findings)
    )


# ---------------------------------------------------------------------------
# TEST P3-026
# ---------------------------------------------------------------------------
def test_p3_026_close_widget_tree_closes_a_real_tree_through_close(monkeypatch):
    """TEST P3-026 - close_widget_tree releases a real widget tree through Widget.close()."""
    pytest.importorskip("ipywidgets")
    import ipywidgets as widgets

    from railway_headway_sim.ui.table_editor import close_widget_tree

    root = widgets.VBox([widgets.Label(value="a"), widgets.VBox([widgets.Label(value="b")])])
    inner = root.children[1]
    members = [root, root.children[0], inner, inner.children[0]]

    closed: list[object] = []
    original_close = widgets.Widget.close

    def counting_close(self):  # noqa: ANN001 - local test double for the public method
        closed.append(self)
        return original_close(self)

    monkeypatch.setattr(widgets.Widget, "close", counting_close)

    close_widget_tree(root)  # must not raise
    for widget in members:
        assert closed.count(widget) == 1, (
            f"{type(widget).__name__} was closed {closed.count(widget)} times; "
            "every widget of the tree must be closed exactly once (nested containers included)"
        )

    closed.clear()
    close_widget_tree(root)  # a repeated call must not raise either
    for widget in members:
        assert closed.count(widget) == 1, (
            "a repeated call must close every widget exactly once and never raise"
        )

    leaf = widgets.Label(value="leaf")
    close_widget_tree(leaf)  # a leaf with no children is safe too
    assert closed.count(leaf) == 1
