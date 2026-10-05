"""Phase-1 project controller tests.

Acceptance tests covered here: TEST P1-009 and TEST P1-010.
"""

from __future__ import annotations

import json

import pytest

from railway_headway_sim import (
    Direction,
    ProjectController,
    Severity,
    ValidationStatus,
    project_hash,
    to_json_text,
    to_normalized_dict,
)
from railway_headway_sim.models.project import Project
from railway_headway_sim.validation import codes
from railway_headway_sim.version import APP_VERSION

from .support import codes_of, example_document, controller_with_example


# ---------------------------------------------------------------------------
# TEST P1-009 - modification-since-validation state
# ---------------------------------------------------------------------------
def test_p1_009_modify_after_validation_is_detected():
    """TEST P1-009 - Editing after validation marks the project as modified."""
    controller = ProjectController.new_project()
    controller.validate_project()

    assert controller.modified_since_validation is False
    assert controller.state.freshness_text == "VALIDATED CURRENT"
    validated_hash = controller.current_project_hash

    message = controller.update_metadata(name="Renamed after validation")
    assert "Updated name" in message

    assert controller.modified_since_validation is True
    assert controller.state.freshness_text == "PROJECT MODIFIED SINCE VALIDATION"
    assert controller.current_project_hash != validated_hash
    assert controller.last_validated_hash == validated_hash

    controller.validate_project()
    assert controller.modified_since_validation is False
    assert controller.state.freshness_text == "VALIDATED CURRENT"
    assert controller.current_project_hash == controller.last_validated_hash


def test_no_op_edit_does_not_invalidate_the_validation():
    """Regression - saving unchanged values keeps the project validated."""
    controller = ProjectController.new_project()
    controller.validate_project()
    before_hash = controller.current_project_hash
    before_modified = controller.project.project.modified_utc

    message = controller.update_metadata(name=controller.project.project.name)

    assert "No project fields changed" in message
    assert controller.modified_since_validation is False
    assert controller.current_project_hash == before_hash
    assert controller.project.project.modified_utc == before_modified


def test_import_marks_project_as_validated_for_imported_content():
    """Regression - a successful import leaves the project in a validated state."""
    controller = ProjectController()
    controller.import_json_data(example_document(), source_name="example")

    assert controller.modified_since_validation is False
    assert controller.current_project_hash == controller.last_validated_hash
    assert controller.state.validation_status == ValidationStatus.VALID.value


def test_invalid_edit_is_rejected_with_a_message():
    """Regression - malformed metadata edits are rejected and reported."""
    controller = ProjectController.new_project()
    controller.validate_project()

    message = controller.update_metadata(chainage_start_km="not a number", name="Kept name")

    assert "Not applied" in message
    assert controller.project.reference_system.chainage_start_km == 0.0
    assert controller.state.last_message_severity is Severity.WARNING


def test_unknown_field_edit_is_rejected():
    """Regression - only editable fields may be written through the controller."""
    controller = ProjectController.new_project()
    message = controller.update_metadata(project_type="TRACK_AND_STATION_CAPACITY")

    assert "unknown/uneditable" in message.lower()
    assert controller.project.project.project_type == "TRAIN_RUN_ANALYSIS"


# ---------------------------------------------------------------------------
# TEST P1-010 - direction selection does not mutate the project
# ---------------------------------------------------------------------------
def test_p1_010_direction_change_does_not_mutate_project_data():
    """TEST P1-010 - Switching FORWARD/REVERSE leaves all stored data unchanged."""
    controller = ProjectController()
    controller.import_json_data(example_document(), source_name="example")

    document_before = to_normalized_dict(controller.project)
    json_before = to_json_text(controller.project)
    hash_before = controller.current_project_hash
    infrastructure_before = json.dumps(
        controller.project.infrastructure, sort_keys=True
    )

    state = controller.set_direction(Direction.REVERSE)

    assert state.direction is Direction.REVERSE
    assert controller.state.direction is Direction.REVERSE
    assert controller.state.direction_changed_utc is not None

    assert to_normalized_dict(controller.project) == document_before
    assert to_json_text(controller.project) == json_before
    assert controller.current_project_hash == hash_before
    assert json.dumps(controller.project.infrastructure, sort_keys=True) == infrastructure_before
    assert "direction" not in to_normalized_dict(controller.project)

    # Direction is not part of the canonical project content: the hash of the
    # exported document is identical in both directions.
    hash_forward = project_hash(controller.project)
    controller.toggle_direction()
    assert controller.state.direction is Direction.FORWARD
    assert project_hash(controller.project) == hash_forward


def test_direction_selection_rejects_reserved_values():
    """Regression - BOTH/TRACK exist in the schema but are not selectable in Phase 1."""
    controller = ProjectController.new_project()

    controller.set_direction(Direction.BOTH)

    assert controller.state.direction is Direction.FORWARD
    assert "not selectable in Phase 1" in controller.state.last_message
    assert controller.state.last_message_severity is Severity.WARNING

    controller.set_direction("REVERSE")
    assert controller.state.direction is Direction.REVERSE


def test_direction_state_guard_rejects_other_values():
    """Regression - ControllerState refuses non-selectable directions."""
    from railway_headway_sim.app.project_controller import ControllerState

    with pytest.raises(ValueError):
        ControllerState(direction=Direction.BOTH)


# ---------------------------------------------------------------------------
# lifecycle / state helpers
# ---------------------------------------------------------------------------
def test_new_project_provides_template_defaults():
    """Regression - the template is complete and immediately usable."""
    controller = ProjectController.new_project(name="Template Check")
    project = controller.project

    assert isinstance(project, Project)
    assert project.project.project_type == "TRAIN_RUN_ANALYSIS"
    assert project.project.data_status.value == "TEMPLATE"
    assert project.reference_system.chainage_start_km == 0.0
    assert project.reference_system.chainage_end_km == 100.0
    assert project.reference_system.forward_direction.value == "INCREASING_CHAINAGE"
    assert project.display_units.chainage == "km"
    assert project.services == [] and project.scenarios == [] and project.infrastructure == []
    assert controller.state.schema_version == "1.0"
    # The app version is read from the single authoritative source (version.py);
    # Phase 2 bumped it 0.1.0 -> 0.2.0, Phase 3 bumped it 0.2.0 -> 0.3.0, the Phase-3
    # bugfix bumped it 0.3.0 -> 0.3.1, Phase 4A bumped it 0.3.1 -> 0.4.0, the Phase-4A
    # label correction bumped it 0.4.0 -> 0.4.1, the Phase-4A corridor correction bumped
    # it 0.4.1 -> 0.4.2, Phase 4B bumped it 0.4.2 -> 0.5.0, Phase 5A bumped it
    # 0.5.0 -> 0.6.0, Phase 5B bumped it 0.6.0 -> 0.7.0 and Phase 6A bumped it
    # 0.7.0 -> 0.8.0 (Phase 6A, rolling-stock model) -> 0.9.0 (Phase 6B, rolling-stock UI)
    # (declared version-literal adaptation, docs/PHASE1_REGRESSION_MAP.md §3); the schema
    # version stays 1.0 and the expectation itself is unchanged.
    assert controller.state.app_version == APP_VERSION
    assert controller.state.app_version == "0.9.0"


def test_import_failure_preserves_the_current_project():
    """Regression - a rejected import keeps the current project unchanged."""
    controller = controller_with_example()
    hash_before = controller.current_project_hash

    result = controller.import_json_data({"schema_version": "9.9"}, source_name="future.json")

    assert result.status is ValidationStatus.INVALID
    assert controller.current_project_hash == hash_before
    assert controller.state.last_action == "import_failed"
    assert "kept unchanged" in controller.state.last_message


def test_import_of_invalid_but_usable_document_preserves_content():
    """Regression - INVALID documents still import their valid content."""
    document = example_document()
    document["project"]["id"] = ""
    controller = ProjectController()

    result = controller.import_json_data(document, source_name="bad-id.json")

    assert result.status is ValidationStatus.INVALID
    assert controller.project is not None
    assert controller.project.project.name == "Demo Intercity Line"
    assert controller.project.summary_counts()["Stations"] == 3
    assert controller.state.validation_status == ValidationStatus.INVALID.value
    assert codes.VAL_PROJECT_001 in codes_of(result)


def test_no_file_selected_import_reports_precondition_error():
    """Regression - importing without a selection reports APP-CTRL-002."""
    controller = ProjectController.new_project()
    result = controller.import_json_upload(())
    assert codes.APP_CTRL_002 in codes_of(result)


def test_export_without_project_is_rejected_cleanly():
    """Regression - exporting without a project warns instead of raising."""
    controller = ProjectController()
    assert controller.export_json(download=False) is None
    assert controller.state.last_action == "export_rejected"
    assert controller.state.last_message_severity is Severity.WARNING


def test_validate_without_project_is_reported_as_error():
    """Regression - validating without a project yields APP-CTRL-001."""
    controller = ProjectController()
    result = controller.validate_project()

    assert result.status is ValidationStatus.INVALID
    assert codes.APP_CTRL_001 in codes_of(result)
    assert "No project is loaded" in result.diagnostics[0].message


def test_subscribers_are_notified_and_can_unsubscribe():
    """Regression - the UI can subscribe to controller state changes."""
    controller = ProjectController.new_project()
    calls: list[int] = []
    unsubscribe = controller.subscribe(lambda: calls.append(1))

    controller.set_direction(Direction.REVERSE)
    assert calls, "listener must be notified on state changes"

    unsubscribe()
    count_after_unsubscribe = len(calls)
    controller.set_direction(Direction.FORWARD)
    assert len(calls) == count_after_unsubscribe


def test_export_uses_controller_directory_and_reports_outcome(tmp_path):
    """Regression - exports land in the configured directory and report the path."""
    controller = ProjectController(download_on_export=False, export_directory=tmp_path)
    controller.create_new_project(name="Export Target")

    outcome = controller.export_json()

    assert outcome is not None
    assert outcome.written_path is not None
    assert outcome.browser_download_used is False
    assert controller.state.last_export_filename == outcome.filename
    assert controller.state.last_export_path == outcome.written_path


def test_summary_and_state_rows_are_available_for_the_ui():
    """Regression - the UI-facing summary/audit rows are complete."""
    controller = ProjectController.new_project(name="Summary Check")
    summary_keys = [key for key, _value in controller.summary_rows()]
    state_keys = [key for key, _value in controller.state_rows()]

    for expected in ("Project ID", "Project name", "Chainage range", "Schema version"):
        assert expected in summary_keys
    for expected in (
        "Application version",
        "Project schema version",
        "Validation status",
        "Validation freshness",
        "Current project hash",
        "Last validated hash",
        "Direction (application selection)",
    ):
        assert expected in state_keys
    assert controller.object_count_rows()  # template counts are available
