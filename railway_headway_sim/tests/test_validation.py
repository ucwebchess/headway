"""Phase-1 validation tests.

Acceptance tests covered here: TEST P1-001, P1-004, P1-005, P1-006, P1-007,
P1-008 and P1-012 (plus additional structural regression tests).
"""

from __future__ import annotations

import pytest

from railway_headway_sim import (
    ProjectController,
    Severity,
    ValidationStatus,
    validate_document,
    validate_json_text,
)
from railway_headway_sim.constants import CONTAINER_SECTIONS, OBJECT_SECTIONS, TOP_LEVEL_SECTIONS
from railway_headway_sim.io.project_io import import_project_from_bytes
from railway_headway_sim.validation import codes

from .support import codes_of, diagnostics_with_code, example_document, template_document


# ---------------------------------------------------------------------------
# TEST P1-001
# ---------------------------------------------------------------------------
def test_p1_001_new_project_is_valid():
    """TEST P1-001 - A new project template validates as VALID with no diagnostics."""
    controller = ProjectController.new_project()
    result = controller.validation

    assert result is not None
    assert result.status is ValidationStatus.VALID
    assert result.error_count == 0
    assert result.warning_count == 0
    assert controller.modified_since_validation is False

    project = controller.project
    assert project is not None
    assert project.schema_version == "1.0"
    for section in TOP_LEVEL_SECTIONS:
        assert hasattr(project, section), f"missing top-level section {section}"
    for section in CONTAINER_SECTIONS:
        assert getattr(project, section) == [], f"{section} must default to an empty array"
    for section in OBJECT_SECTIONS:
        assert isinstance(getattr(project, section), object)

    # The same template validated through the document pipeline is also VALID.
    outcome = validate_document(template_document())
    assert outcome.ok
    assert outcome.result.status is ValidationStatus.VALID


def test_documented_example_project_is_valid():
    """Regression - the shipped example project imports as VALID (INFO only)."""
    outcome = validate_document(example_document(), source_name="example")

    assert outcome.ok
    assert outcome.result.status is ValidationStatus.VALID
    assert outcome.result.error_count == 0
    assert outcome.result.warning_count == 0
    assert all(d.severity is Severity.INFO for d in outcome.result.diagnostics)
    assert outcome.project is not None
    assert outcome.project.summary_counts()["Stations"] == 3
    assert outcome.project.summary_counts()["Signals"] == 2


# ---------------------------------------------------------------------------
# TEST P1-004 / P1-005 - schema version handling
# ---------------------------------------------------------------------------
def test_p1_004_missing_schema_version_is_invalid():
    """TEST P1-004 - A document without schema_version is INVALID with a schema diagnostic."""
    document = template_document()
    document.pop("schema_version")

    outcome = validate_document(document)

    assert outcome.result.status is ValidationStatus.INVALID
    assert outcome.project is None
    assert codes.VAL_SCHEMA_003 in codes_of(outcome.result)
    diagnostic = diagnostics_with_code(outcome.result, codes.VAL_SCHEMA_003)[0]
    assert diagnostic.severity is Severity.ERROR
    assert diagnostic.suggested_action


def test_p1_005_unsupported_schema_version_is_invalid():
    """TEST P1-005 - An unsupported schema_version is INVALID and is not parsed."""
    document = template_document()
    document["schema_version"] = "2.7"

    outcome = validate_document(document)

    assert outcome.result.status is ValidationStatus.INVALID
    assert outcome.project is None
    assert codes.VAL_SCHEMA_004 in codes_of(outcome.result)
    assert outcome.schema_version_seen == "2.7"
    assert diagnostics_with_code(outcome.result, codes.VAL_SCHEMA_004)[0].context["supported_versions"]


def test_schema_version_of_wrong_type_is_invalid():
    """Regression - a non-string schema_version is reported as malformed."""
    document = template_document()
    document["schema_version"] = 1.0

    outcome = validate_document(document)

    assert outcome.result.status is ValidationStatus.INVALID
    assert codes.VAL_SCHEMA_002 in codes_of(outcome.result)


# ---------------------------------------------------------------------------
# TEST P1-006 - project identity
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "mutate",
    [
        pytest.param(lambda doc: doc["project"].__setitem__("id", ""), id="empty-id"),
        pytest.param(lambda doc: doc["project"].__setitem__("id", "   "), id="blank-id"),
        pytest.param(lambda doc: doc["project"].pop("id"), id="missing-id"),
        pytest.param(lambda doc: doc["project"].pop("name"), id="missing-name"),
    ],
)
def test_p1_006_project_identity_is_required(mutate):
    """TEST P1-006 - Missing/empty project ID (or name) is an ERROR (INVALID)."""
    document = template_document()
    mutate(document)

    outcome = validate_document(document)

    assert outcome.result.status is ValidationStatus.INVALID
    assert codes.VAL_PROJECT_001 in codes_of(outcome.result)
    diagnostic = diagnostics_with_code(outcome.result, codes.VAL_PROJECT_001)[0]
    assert diagnostic.severity is Severity.ERROR
    assert diagnostic.context["field"].startswith("project.")


# ---------------------------------------------------------------------------
# TEST P1-007 - chainage reference bounds
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "start,end,relation",
    [
        (100.0, 0.0, "reversed"),
        (10.0, 5.0, "reversed"),
        (0.0, 0.0, "equal"),
    ],
)
def test_p1_007_chainage_end_not_greater_than_start_is_invalid(start, end, relation):
    """TEST P1-007 - chainage_end <= chainage_start is INVALID (VAL-REF-001)."""
    document = template_document()
    document["reference_system"]["chainage_start_km"] = start
    document["reference_system"]["chainage_end_km"] = end

    outcome = validate_document(document)

    assert outcome.result.status is ValidationStatus.INVALID
    assert codes.VAL_REF_001 in codes_of(outcome.result)
    diagnostic = diagnostics_with_code(outcome.result, codes.VAL_REF_001)[0]
    assert diagnostic.severity is Severity.ERROR
    assert diagnostic.context["relation"] == relation


def test_chainage_bounds_are_accepted_when_increasing():
    """Regression - increasing chainage bounds validate as VALID."""
    document = template_document(chainage_start_km=0, chainage_end_km=0.5)
    outcome = validate_document(document)

    assert outcome.result.status is ValidationStatus.VALID
    assert codes.VAL_REF_001 not in codes_of(outcome.result)


# ---------------------------------------------------------------------------
# TEST P1-008 - direction enumerations
# ---------------------------------------------------------------------------
def test_p1_008_invalid_direction_enumeration_is_invalid():
    """TEST P1-008 - An unsupported chainage direction value is INVALID (VAL-DIR-001)."""
    document = template_document()
    document["reference_system"]["forward_direction"] = "UP"

    outcome = validate_document(document)

    assert outcome.result.status is ValidationStatus.INVALID
    assert outcome.project is not None, "valid content must still be preserved"
    matching = diagnostics_with_code(outcome.result, codes.VAL_DIR_001)
    assert len(matching) == 1, "one specific diagnostic per malformed direction field"
    assert matching[0].severity is Severity.ERROR
    assert matching[0].context["found"] == "UP"


def test_missing_direction_is_invalid():
    """Regression - a missing direction value is INVALID (VAL-DIR-001)."""
    document = template_document()
    document["reference_system"].pop("reverse_direction")

    outcome = validate_document(document)

    assert outcome.result.status is ValidationStatus.INVALID
    assert codes.VAL_DIR_001 in codes_of(outcome.result)


def test_identical_forward_and_reverse_direction_warns():
    """Regression - identical forward/reverse direction is a WARNING (VAL-DIR-002)."""
    document = template_document()
    document["reference_system"]["reverse_direction"] = "INCREASING_CHAINAGE"

    outcome = validate_document(document)

    assert outcome.result.status is ValidationStatus.VALID_WITH_WARNINGS
    assert codes.VAL_DIR_002 in codes_of(outcome.result)
    assert diagnostics_with_code(outcome.result, codes.VAL_DIR_002)[0].severity is Severity.WARNING


# ---------------------------------------------------------------------------
# TEST P1-012 - stable diagnostic structure
# ---------------------------------------------------------------------------
def _document_with_many_problems():
    """Return a document that triggers several different diagnostics."""
    document = example_document()
    document["project"]["id"] = ""
    document["reference_system"]["chainage_start_km"] = 300.0
    document["reference_system"]["chainage_end_km"] = 100.0
    document["display_units"]["speed"] = "furlongs per fortnight"
    stations = document["infrastructure"][0]["stations"]
    stations[1]["id"] = stations[0]["id"]  # duplicate station id
    stations[2]["id"] = 42  # malformed identifier
    document["scenarios"][0]["direction"] = "SIDEWAYS"  # invalid enum in a preserved container
    return document


def test_p1_012_diagnostics_have_stable_structure():
    """TEST P1-012 - Every diagnostic exposes code/severity/message and is deterministic."""
    document = _document_with_many_problems()
    result = validate_document(document).result

    assert result.error_count > 0
    assert result.status is ValidationStatus.INVALID
    for diagnostic in result.diagnostics:
        assert isinstance(diagnostic.code, str) and diagnostic.code.startswith("VAL-")
        assert diagnostic.code in codes.ALL_DIAGNOSTIC_CODES
        assert isinstance(diagnostic.severity, Severity)
        assert isinstance(diagnostic.message, str) and diagnostic.message.strip()
        assert diagnostic.category is not None
        assert diagnostic.format_line().startswith(f"[{diagnostic.severity.value}]")

    triggered = set(codes_of(result))
    assert {
        codes.VAL_PROJECT_001,
        codes.VAL_REF_001,
        codes.VAL_UNIT_001,
        codes.VAL_ID_001,
        codes.VAL_ID_002,
        codes.VAL_ENUM_001,
    } <= triggered

    counts = (result.error_count, result.warning_count, result.info_count)
    assert sum(counts) == len(result.diagnostics)

    # Same input -> identical diagnostics, same order (deterministic ordering).
    repeat = validate_document(_document_with_many_problems()).result
    assert [
        (d.code, d.severity.value, d.message) for d in result.diagnostics
    ] == [(d.code, d.severity.value, d.message) for d in repeat.diagnostics]


# ---------------------------------------------------------------------------
# additional structural regression tests
# ---------------------------------------------------------------------------
def test_malformed_field_type_is_reported_once_and_not_repaired_silently():
    """Regression - malformed typed fields produce one specific ERROR each."""
    document = template_document()
    document["project"]["name"] = 12345
    document["reference_system"]["chainage_start_km"] = "0 km"

    outcome = validate_document(document)

    assert outcome.result.status is ValidationStatus.INVALID
    malformed = diagnostics_with_code(outcome.result, codes.VAL_PROJECT_002)
    assert len(malformed) == 2
    fields = {diagnostic.context["field"] for diagnostic in malformed}
    assert fields == {"project.name", "reference_system.chainage_start_km"}
    # The malformed value is gone from the model, and no duplicate "missing" error is added.
    assert outcome.project is not None
    assert outcome.project.project.name is None
    assert codes.VAL_REF_002 not in codes_of(outcome.result)


def test_missing_container_is_created_with_default_and_info():
    """Regression - an absent container gets the documented [] default (INFO)."""
    document = template_document()
    document.pop("services")

    outcome = validate_document(document)

    assert outcome.ok
    assert outcome.project.services == []
    assert outcome.defaults_applied == ("services",)
    assert codes.VAL_FUTURE_001 in codes_of(outcome.result)
    assert outcome.result.status is ValidationStatus.VALID  # INFO only


def test_malformed_container_is_reported_and_defaulted():
    """Regression - a container with the wrong JSON type is an ERROR, not a crash."""
    document = template_document()
    document["scenarios"] = {"not": "an array"}

    outcome = validate_document(document)

    assert outcome.result.status is ValidationStatus.INVALID
    assert codes.VAL_SCHEMA_002 in codes_of(outcome.result)
    assert outcome.project is not None
    assert outcome.project.scenarios == []
    # The malformed section is reported once as a schema ERROR, so it is not
    # also listed as a "defaulted" section.
    assert outcome.defaults_applied == ()


def test_duplicate_identifiers_are_reported_per_object_type():
    """Regression - VAL-REG-011 SUPERSEDED: cross-type duplicate registered ids are INVALID.

    Declared Phase-2 supersession (see ``docs/PHASE1_REGRESSION_MAP.md``):

    * the first assertion of the Phase-1 test is replaced - two *typed engineering
      objects of different types* may no longer share the same registered ID; such a
      project is INVALID (``VAL-REGISTRY-001``);
    * the second assertion is unchanged - arbitrary nested extension data carrying an
      ``id`` is not a registered object and is not reported;
    * Phase-1 (legacy, non-physical) projects keep the per-object-type duplicate
      check for their opaque nested lists.
    """
    from railway_headway_sim.infrastructure import grr_fixtures

    # (1) replaced first assertion: cross-type duplicate of two REGISTERED objects.
    document = grr_fixtures.build_grr01_document()
    document["infrastructure"][0]["nodes"][0]["id"] = "ALN-MAIN"  # node vs alignment
    outcome = validate_document(document)
    assert outcome.result.status is ValidationStatus.INVALID
    duplicates = diagnostics_with_code(outcome.result, codes.VAL_REGISTRY_001)
    assert duplicates, "a cross-type duplicate registered ID must be reported"
    assert duplicates[0].object_id == "ALN-MAIN"
    assert duplicates[0].severity is Severity.ERROR

    # (2) unchanged second assertion: extension data with an id is not registered.
    document = example_document()
    document["infrastructure"][0]["vehicles"] = [{"id": "STN-0001"}]  # same id, not registered
    outcome = validate_document(document)
    assert codes.VAL_ID_001 not in codes_of(outcome.result)
    assert codes.VAL_REGISTRY_001 not in codes_of(outcome.result)

    # (3) Phase-1 behaviour for legacy opaque nested lists is preserved.
    document = example_document()
    document["infrastructure"][0]["stations"][1]["id"] = "STN-0001"
    outcome = validate_document(document)
    duplicate = diagnostics_with_code(outcome.result, codes.VAL_ID_001)
    assert len(duplicate) == 1
    assert duplicate[0].object_id == "STN-0001"
    assert duplicate[0].severity is Severity.ERROR


def test_non_object_root_is_reported():
    """Regression - a JSON array/root scalar is a schema error, not an exception."""
    outcome = validate_document([1, 2, 3])
    assert outcome.project is None
    assert codes.VAL_SCHEMA_002 in codes_of(outcome.result)

    outcome = validate_json_text("[1, 2, 3]")
    assert codes.VAL_SCHEMA_002 in codes_of(outcome.result)


def test_unparseable_json_text_is_reported():
    """Regression - invalid JSON text yields VAL-SCHEMA-001 with a location."""
    outcome = validate_json_text("{ this is not json,,, }", source_name="broken.json")
    assert outcome.project is None
    assert codes.VAL_SCHEMA_001 in codes_of(outcome.result)
    diagnostic = diagnostics_with_code(outcome.result, codes.VAL_SCHEMA_001)[0]
    assert "line" in diagnostic.message


def test_undecodable_upload_bytes_are_reported():
    """Regression - non-UTF-8 bytes yield VAL-SCHEMA-005."""
    outcome = import_project_from_bytes(b"\xff\xfe\x00\x00not utf8", source_name="binary.json")
    assert outcome.project is None
    assert codes.VAL_SCHEMA_005 in codes_of(outcome.validation)


def test_display_unit_warning_is_not_an_error():
    """Regression - unknown display units are WARNINGs (presentation only)."""
    document = template_document()
    document["display_units"]["speed"] = "knots"

    outcome = validate_document(document)

    assert outcome.result.status is ValidationStatus.VALID_WITH_WARNINGS
    assert codes.VAL_UNIT_001 in codes_of(outcome.result)
    assert outcome.project is not None
    assert outcome.project.display_units.speed == "knots", "value is preserved as supplied"


def test_preserved_containers_get_info_only():
    """Regression - imported engineering containers produce INFO, never ERROR."""
    result = validate_document(example_document()).result
    future = diagnostics_with_code(result, codes.VAL_FUTURE_002)
    assert len(future) == 6
    assert all(d.severity is Severity.INFO for d in future)


def test_extra_unknown_fields_are_preserved():
    """Regression - unknown (forward-compatible) fields survive validation."""
    document = template_document()
    document["project"]["cost_centre"] = "CC-42"
    document["infrastructure"] = [{"id": "INF-1", "future_field": {"a": 1}}]
    document["future_section"] = {"anything": [1, 2, 3]}

    outcome = validate_document(document)

    assert outcome.ok
    assert outcome.project.project.model_dump()["cost_centre"] == "CC-42"
    assert outcome.project.infrastructure[0]["future_field"] == {"a": 1}
    assert outcome.project.model_dump()["future_section"] == {"anything": [1, 2, 3]}
