"""Phase-1 JSON import/export and hashing tests.

Acceptance tests covered here: TEST P1-002, P1-003 and P1-011.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from railway_headway_sim import (
    ProjectController,
    ValidationStatus,
    document_hash,
    export_project,
    import_project_from_bytes,
    import_project_from_file,
    import_project_from_text,
    import_project_from_uploaded,
    project_hash,
    to_json_text,
    to_normalized_dict,
)
from railway_headway_sim.constants import EXPORT_METADATA_KEY
from railway_headway_sim.io.project_io import normalise_upload_payload
from railway_headway_sim.validation import codes

from .support import codes_of, example_document, example_json_text, template_document


def _controller_with_content() -> ProjectController:
    """Return a controller holding the example project with edited metadata."""
    controller = ProjectController.new_project()
    controller.update_metadata(
        name="Roundtrip Line",
        description="Import/export roundtrip test project",
        chainage_origin_name="Alpha",
        chainage_end_name="Delta",
        chainage_start_km=0,
        chainage_end_km=250.4,
    )
    controller.import_json_data(example_document(), source_name="example")
    return controller


# ---------------------------------------------------------------------------
# TEST P1-002 - roundtrip equivalence
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("source", ["template", "example"])
def test_p1_002_export_import_roundtrip_preserves_data(source, tmp_path):
    """TEST P1-002 - Export -> import yields equivalent project data."""
    if source == "template":
        controller = ProjectController.new_project(name="Roundtrip Template Line")
        controller.update_metadata(chainage_end_km=12.5, origin_name="Alpha", end_name="Delta")
    else:
        controller = ProjectController()
        controller.import_json_data(example_document(), source_name="example")

    original = to_normalized_dict(controller.project)
    exported = controller.export_json(download=False, directory=tmp_path)
    assert exported is not None
    assert exported.written_path is not None
    assert Path(exported.written_path).exists()

    reimported_controller = ProjectController()
    result = reimported_controller.import_json_text(exported.text, source_name=exported.filename)

    assert result.status is ValidationStatus.VALID
    assert reimported_controller.project is not None
    assert to_normalized_dict(reimported_controller.project) == original
    assert json.loads(exported.text) == to_normalized_dict(reimported_controller.project)


def test_roundtrip_through_files_and_helpers(tmp_path):
    """Regression - file-based and helper-based roundtrips agree."""
    controller = ProjectController()
    controller.import_json_data(example_document(), source_name="example")
    exported = export_project(controller.project, directory=tmp_path, download=False)
    assert exported.written_path is not None

    from_file = import_project_from_file(exported.written_path)
    from_text = import_project_from_text(exported.text, source_name="<text>")
    from_bytes = import_project_from_bytes(exported.data, source_name="<bytes>")

    for outcome in (from_file, from_text, from_bytes):
        assert outcome.ok
        assert outcome.project is not None
    assert (
        to_normalized_dict(from_file.project)
        == to_normalized_dict(from_text.project)
        == to_normalized_dict(from_bytes.project)
        == to_normalized_dict(controller.project)
    )


# ---------------------------------------------------------------------------
# TEST P1-003 - canonical hash stability
# ---------------------------------------------------------------------------
def test_p1_003_equivalent_project_produces_same_canonical_hash_after_roundtrip(tmp_path):
    """TEST P1-003 - Roundtrip and re-export keep the canonical project hash."""
    controller = _controller_with_content()
    controller.validate_project()
    hash_before = controller.current_project_hash
    assert hash_before == project_hash(controller.project)

    exported = controller.export_json(download=False, directory=tmp_path)
    reimported = ProjectController()
    reimported.import_json_text(exported.text, source_name=exported.filename)

    assert project_hash(reimported.project) == hash_before
    # Export -> import -> export must be byte-identical (no volatile metadata).
    second_export = to_json_text(reimported.project)
    assert second_export == exported.text
    assert EXPORT_METADATA_KEY not in json.loads(exported.text)


def test_export_metadata_is_opt_in_and_does_not_break_roundtrip(tmp_path):
    """Regression - export metadata is only written when explicitly requested."""
    controller = ProjectController()
    controller.import_json_data(example_document(), source_name="example")
    plain = controller.export_json(download=False, directory=tmp_path)
    annotated = controller.export_json(
        download=False, directory=tmp_path, embed_export_metadata=True
    )
    assert EXPORT_METADATA_KEY in json.loads(annotated.text)

    reimported = ProjectController()
    reimported.import_json_text(plain.text, source_name="plain.json")
    with_metadata = ProjectController()
    with_metadata.import_json_text(annotated.text, source_name="annotated.json")

    # Annotated documents keep the additional (volatile) key as ordinary data.
    assert EXPORT_METADATA_KEY in to_normalized_dict(with_metadata.project)
    assert EXPORT_METADATA_KEY not in to_normalized_dict(reimported.project)
    base = to_normalized_dict(reimported.project)
    annotated_doc = to_normalized_dict(with_metadata.project)
    annotated_doc.pop(EXPORT_METADATA_KEY)
    assert annotated_doc == base


def test_hash_is_order_independent_and_normalises_numbers():
    """Regression - hashing ignores key order and int/float representation."""
    left = {"schema_version": "1.0", "a": {"x": 10, "y": 0.30000000000000004}, "b": [1, 2]}
    right = {"b": [1, 2], "a": {"y": 0.3, "x": 10.0}, "schema_version": "1.0"}
    assert document_hash(left) == document_hash(right)
    assert len(document_hash(left)) == 64  # SHA-256


def test_export_preserves_stored_numeric_values_and_types(tmp_path):
    """Regression - export does not round or retype stored numbers."""
    controller = ProjectController.new_project()
    controller.update_metadata(chainage_start_km=0, chainage_end_km=250.40000000000003)
    text = controller.export_json(download=False, directory=tmp_path).text
    document = json.loads(text)

    assert document["reference_system"]["chainage_start_km"] == 0
    assert isinstance(document["reference_system"]["chainage_start_km"], int)
    assert document["reference_system"]["chainage_end_km"] == 250.40000000000003
    assert "250.40000000000003" in text


def test_export_document_shape_uses_canonical_section_order(tmp_path):
    """Regression - exported keys are schema_version first, then the schema order."""
    from railway_headway_sim.constants import TOP_LEVEL_SECTIONS

    controller = ProjectController()
    controller.import_json_data(example_document(), source_name="example")
    document = json.loads(controller.export_json(download=False, directory=tmp_path).text)

    assert list(document.keys())[: len(TOP_LEVEL_SECTIONS)] == [
        key for key in TOP_LEVEL_SECTIONS if key in document
    ]
    assert document["schema_version"] == "1.0"


def test_export_filename_reflects_project_name_and_id(tmp_path):
    """Regression - export file names are based on project name and ID."""
    from railway_headway_sim.io.project_io import export_filename

    controller = ProjectController.new_project(project_id="PRJ-TEST-9", name="Sample Line / North")
    filename = export_filename(controller.project)

    assert filename.endswith(".json")
    assert filename.startswith("sample-line-north_")
    assert "prj-test-9" in filename
    assert "/" not in filename and " " not in filename


# ---------------------------------------------------------------------------
# TEST P1-011 - imported JSON is data only
# ---------------------------------------------------------------------------
def test_p1_011_imported_json_content_is_never_executed(tmp_path):
    """TEST P1-011 - Hostile JSON payloads are treated as inert data."""
    marker = tmp_path / "EXECUTED.txt"
    payload_code = f"__import__('pathlib').Path({str(marker)!r}).write_text('executed')"

    document = template_document(name="Hostile payload test")
    document["project"]["description"] = payload_code
    document["infrastructure"] = [
        {"id": "INF-X", "note": f"import os; os.system('touch {marker}')"},
    ]
    document["__unexpected__"] = {"eval": "1 + 1", "exec": "print('boom')", "pickle": "gASV"}

    controller = ProjectController()
    result = controller.import_json_text(json.dumps(document), source_name="hostile.json")

    assert not marker.exists(), "imported content must never be executed"
    assert result.status is ValidationStatus.VALID
    exported = to_normalized_dict(controller.project)

    assert exported["project"]["description"] == payload_code  # preserved verbatim as data
    assert exported["infrastructure"][0]["note"].startswith("import os;")
    assert exported["__unexpected__"] == {"eval": "1 + 1", "exec": "print('boom')", "pickle": "gASV"}


def test_import_helpers_do_not_use_unsafe_deserialization():
    """Regression - the package contains no eval/exec/pickle/yaml/subprocess calls."""
    import ast

    forbidden_modules = {"pickle", "yaml", "marshal", "subprocess", "ctypes", "shelve"}
    forbidden_calls = {"eval", "exec", "compile", "globals", "locals", "__import__"}
    source_dir = Path(__file__).resolve().parent.parent
    checked = 0

    for path in sorted(source_dir.rglob("*.py")):
        if path.name == Path(__file__).name:
            continue  # this test names the forbidden tokens on purpose
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        checked += 1
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name.split(".")[0] not in forbidden_modules, (
                        f"{path.name} imports {alias.name}"
                    )
            elif isinstance(node, ast.ImportFrom):
                module = (node.module or "").split(".")[0]
                if node.level == 0:
                    assert module not in forbidden_modules, f"{path.name} imports from {module}"
            elif isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name):
                    # bare builtins only: ``re.compile`` is legitimate, ``compile`` is not
                    assert func.id not in forbidden_calls, f"{path.name} calls {func.id}()"
                elif isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
                    assert func.value.id not in forbidden_modules, (
                        f"{path.name} calls {func.value.id}.{func.attr}()"
                    )

    assert checked >= 10, "the scan must cover the whole package"


# ---------------------------------------------------------------------------
# upload handling
# ---------------------------------------------------------------------------
def test_upload_payload_shapes_are_supported():
    """Regression - ipywidgets 8 tuples, legacy mappings and single entries all import."""
    raw = example_json_text().encode("utf-8")

    v8_payload = ({"name": "example.json", "content": memoryview(raw), "size": len(raw)},)
    legacy_payload = {"example.json": {"content": raw}}
    single_payload = {"content": raw, "name": "example.json"}

    assert normalise_upload_payload(v8_payload)[0] == "example.json"
    assert normalise_upload_payload(legacy_payload)[0] == "example.json"
    assert normalise_upload_payload(single_payload)[0] == "example.json"

    for payload in (v8_payload, legacy_payload, single_payload):
        outcome = import_project_from_uploaded(payload)
        assert outcome.ok
        assert outcome.project is not None


def test_empty_upload_is_reported_as_application_error():
    """Regression - importing with no file selected reports APP-CTRL-002."""
    outcome = import_project_from_uploaded(())
    assert outcome.project is None
    assert codes.APP_CTRL_002 in codes_of(outcome.validation)

    with pytest.raises(ValueError):
        normalise_upload_payload(())
