"""Stage-1 validation: raw JSON structure, schema version and field types.

This stage works on plain Python data (the result of ``json.loads``) *before*
the canonical model is built. Its job is to guarantee that stage 2
(:mod:`railway_headway_sim.validation.project_validation`) never has to guess:
malformed values of fields that have a defined type are reported here and
removed from the working copy so that the model can be built from the remaining
valid content.

Nothing is "repaired" silently: every removal is reported as an ERROR
diagnostic, and the resulting project state is marked INVALID.
"""

from __future__ import annotations

import copy
from typing import Any, Optional

from ..constants import (
    CONTAINER_SECTIONS,
    DEPRECATED_PROJECT_TYPES,
    OBJECT_SECTIONS,
    SCHEMA_VERSION_FIELD,
)
from ..models.diagnostics import Diagnostic
from ..models.enums import (
    ChainageDirection,
    DataStatus,
    DiagnosticCategory,
    EngineeringStatus,
    Severity,
)
from ..version import SUPPORTED_PROJECT_SCHEMA_VERSIONS, is_supported_schema_version
from . import codes

#: Paths whose value must be a JSON number (int or float, never bool/string).
NUMERIC_FIELD_PATHS: tuple[tuple[str, ...], ...] = (
    ("reference_system", "chainage_start_km"),
    ("reference_system", "chainage_end_km"),
)

#: Paths whose value must be a JSON string.
STRING_FIELD_PATHS: tuple[tuple[str, ...], ...] = (
    ("project", "id"),
    ("project", "name"),
    ("project", "description"),
    ("project", "project_type"),
    ("project", "created_utc"),
    ("project", "modified_utc"),
    ("reference_system", "alignment_id"),
    ("reference_system", "chainage_origin_name"),
    ("reference_system", "chainage_end_name"),
)

#: Paths whose value must be a supported chainage-direction enumeration value.
DIRECTION_FIELD_PATHS: tuple[tuple[str, ...], ...] = (
    ("reference_system", "forward_direction"),
    ("reference_system", "reverse_direction"),
)

#: Paths whose value must be one of a fixed set of string values.
ENUM_FIELD_PATHS: dict[tuple[str, ...], tuple[str, ...]] = {
    ("project", "data_status"): tuple(status.value for status in DataStatus),
    ("project", "engineering_status"): tuple(status.value for status in EngineeringStatus),
}


def _json_type_name(value: Any) -> str:
    """Return the JSON type name of a Python value (for diagnostics/messages)."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return "array"
    return type(value).__name__


def _path_text(path: tuple[str, ...]) -> str:
    """Render a JSON path tuple as dotted text."""
    return ".".join(path)


def _is_json_number(value: Any) -> bool:
    """Return ``True`` for JSON numbers only (booleans are not numbers)."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def validate_schema_and_sanitize(
    data: Any,
) -> tuple[Optional[dict[str, Any]], list[Diagnostic], tuple[str, ...]]:
    """Validate the raw structure of a parsed JSON document.

    Returns ``(sanitized_document, diagnostics, removed_paths)``.

    * ``sanitized_document`` is ``None`` when the document cannot be used at all
      (not an object, missing or unsupported ``schema_version``).
    * ``removed_paths`` lists the dotted field paths that were removed because
      they carried a malformed value; the semantic stage uses it to avoid
      reporting the same problem twice.
    """
    diagnostics: list[Diagnostic] = []
    removed_paths: list[str] = []

    if not isinstance(data, dict):
        diagnostics.append(
            Diagnostic(
                code=codes.VAL_SCHEMA_002,
                severity=Severity.ERROR,
                category=DiagnosticCategory.SCHEMA,
                message=(
                    "A project document must be a JSON object, "
                    f"but the root element is a JSON {_json_type_name(data)}."
                ),
                context={"found_type": _json_type_name(data)},
                suggested_action=(
                    "Export a valid project from the application or check the file contents."
                ),
            )
        )
        return None, diagnostics, ()

    document: dict[str, Any] = copy.deepcopy(data)

    # ---- schema version --------------------------------------------------
    if SCHEMA_VERSION_FIELD not in document:
        diagnostics.append(
            Diagnostic(
                code=codes.VAL_SCHEMA_003,
                severity=Severity.ERROR,
                category=DiagnosticCategory.SCHEMA,
                message=f"Required field '{SCHEMA_VERSION_FIELD}' is missing.",
                context={"supported_versions": list(SUPPORTED_PROJECT_SCHEMA_VERSIONS)},
                suggested_action=(
                    f"Add \"{SCHEMA_VERSION_FIELD}\": \"{SUPPORTED_PROJECT_SCHEMA_VERSIONS[0]}\" "
                    "or import a project exported by this application."
                ),
            )
        )
        return None, diagnostics, ()

    version_value = document[SCHEMA_VERSION_FIELD]
    if not isinstance(version_value, str):
        diagnostics.append(
            Diagnostic(
                code=codes.VAL_SCHEMA_002,
                severity=Severity.ERROR,
                category=DiagnosticCategory.SCHEMA,
                message=(
                    f"'{SCHEMA_VERSION_FIELD}' must be a JSON string, "
                    f"but it is a JSON {_json_type_name(version_value)}."
                ),
                context={"field": SCHEMA_VERSION_FIELD, "found_type": _json_type_name(version_value)},
                suggested_action="Write the schema version as a string, e.g. \"1.0\".",
            )
        )
        return None, diagnostics, ()

    if not is_supported_schema_version(version_value):
        diagnostics.append(
            Diagnostic(
                code=codes.VAL_SCHEMA_004,
                severity=Severity.ERROR,
                category=DiagnosticCategory.SCHEMA,
                message=(
                    f"Project schema version '{version_value}' is not supported by "
                    f"application version {_app_version()}."
                ),
                context={
                    "found": version_value,
                    "supported_versions": list(SUPPORTED_PROJECT_SCHEMA_VERSIONS),
                },
                suggested_action=(
                    "Import a document with a supported schema_version, or update the application."
                ),
            )
        )
        return None, diagnostics, ()

    # ---- section structure ----------------------------------------------
    for section in CONTAINER_SECTIONS:
        if section in document and not isinstance(document[section], list):
            diagnostics.append(
                Diagnostic(
                    code=codes.VAL_SCHEMA_002,
                    severity=Severity.ERROR,
                    category=DiagnosticCategory.SCHEMA,
                    message=(
                        f"Section '{section}' must be a JSON array of objects, "
                        f"but it is a JSON {_json_type_name(document[section])}."
                    ),
                    context={"field": section, "found_type": _json_type_name(document[section])},
                    suggested_action=(
                        f"Replace '{section}' with an array (use [] for an empty container) "
                        "and re-import."
                    ),
                )
            )
            del document[section]
            removed_paths.append(section)

    for section in OBJECT_SECTIONS:
        if section in document and not isinstance(document[section], dict):
            diagnostics.append(
                Diagnostic(
                    code=codes.VAL_SCHEMA_002,
                    severity=Severity.ERROR,
                    category=DiagnosticCategory.SCHEMA,
                    message=(
                        f"Section '{section}' must be a JSON object, "
                        f"but it is a JSON {_json_type_name(document[section])}."
                    ),
                    context={"field": section, "found_type": _json_type_name(document[section])},
                    suggested_action=f"Replace '{section}' with an object (use {{}} if empty).",
                )
            )
            del document[section]
            removed_paths.append(section)

    # ---- typed scalar fields --------------------------------------------
    for path in STRING_FIELD_PATHS:
        value = _lookup(document, path)
        if value is not None and not isinstance(value, str):
            diagnostics.append(
                _malformed_field_diagnostic(document, path, value, expected="a JSON string")
            )
            _remove(document, path)
            removed_paths.append(_path_text(path))

    for path in NUMERIC_FIELD_PATHS:
        value = _lookup(document, path)
        if value is not None and not _is_json_number(value):
            diagnostics.append(
                _malformed_field_diagnostic(document, path, value, expected="a JSON number")
            )
            _remove(document, path)
            removed_paths.append(_path_text(path))

    for path, allowed in ENUM_FIELD_PATHS.items():
        value = _lookup(document, path)
        if value is None:
            continue
        if not isinstance(value, str) or value not in allowed:
            diagnostics.append(
                Diagnostic(
                    code=codes.VAL_ENUM_001,
                    severity=Severity.ERROR,
                    category=DiagnosticCategory.ENUM,
                    message=(
                        f"'{_path_text(path)}' has unsupported value {value!r}; "
                        f"supported values are {list(allowed)}."
                    ),
                    context={"field": _path_text(path), "found": value, "allowed": list(allowed)},
                    suggested_action="Use one of the supported values and re-import.",
                )
            )
            _remove(document, path)
            removed_paths.append(_path_text(path))

    # ---- chainage direction enumerations --------------------------------
    allowed_directions = tuple(direction.value for direction in ChainageDirection)
    for path in DIRECTION_FIELD_PATHS:
        value = _lookup(document, path)
        if value is None:
            continue
        if not isinstance(value, str) or value not in allowed_directions:
            diagnostics.append(
                Diagnostic(
                    code=codes.VAL_DIR_001,
                    severity=Severity.ERROR,
                    category=DiagnosticCategory.DIR,
                    message=(
                        f"'{_path_text(path)}' has unsupported direction value {value!r}; "
                        f"supported values are {list(allowed_directions)}."
                    ),
                    context={
                        "field": _path_text(path),
                        "found": value,
                        "allowed": list(allowed_directions),
                    },
                    suggested_action="Use one of the supported chainage direction values.",
                )
            )
            _remove(document, path)
            removed_paths.append(_path_text(path))

    return document, diagnostics, tuple(removed_paths)


def _malformed_field_diagnostic(
    document: dict[str, Any], path: tuple[str, ...], value: Any, *, expected: str
) -> Diagnostic:
    """Build the standard VAL-PROJECT-002 diagnostic for a malformed field."""
    return Diagnostic(
        code=codes.VAL_PROJECT_002,
        severity=Severity.ERROR,
        category=DiagnosticCategory.PROJECT,
        message=(
            f"Field '{_path_text(path)}' must be {expected}, "
            f"but it is a JSON {_json_type_name(value)}."
        ),
        context={"field": _path_text(path), "found_type": _json_type_name(value), "expected": expected},
        suggested_action="Correct the field value and re-import the project.",
    )


def _app_version() -> str:
    """Local import helper so this module never runs at import time side effects."""
    from ..version import APP_VERSION

    return APP_VERSION


def _lookup(document: dict[str, Any], path: tuple[str, ...]) -> Any:
    """Return the value at *path*, or ``None`` when any segment is absent."""
    node: Any = document
    for key in path:
        if not isinstance(node, dict) or key not in node:
            return None
        node = node[key]
    return node


def _remove(document: dict[str, Any], path: tuple[str, ...]) -> None:
    """Remove the key at *path* when its parent object exists."""
    parent: Any = document
    for key in path[:-1]:
        if not isinstance(parent, dict) or not isinstance(parent.get(key), dict):
            return
        parent = parent[key]
    if isinstance(parent, dict):
        parent.pop(path[-1], None)


def deprecated_project_type_note(project_type: Optional[str]) -> Optional[str]:
    """Return a suggested action when *project_type* is a deprecated value."""
    if project_type and project_type in DEPRECATED_PROJECT_TYPES:
        return DEPRECATED_PROJECT_TYPES[project_type]
    return None
