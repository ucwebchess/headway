"""Stage-2 validation: structural/basic semantic checks on the canonical model.

Phase-1 scope (deliberately limited):

* identifiers, project metadata, chainage reference bounds, direction enumerations,
  container structure, display-unit strings, duplicate IDs.

Explicitly **out of scope** for this validator (later phases): railway topology,
track geometry, signalling rules, train physics, headway/capacity semantics.
"""

from __future__ import annotations

from typing import Any, Iterator, Optional

from ..constants import (
    CONTAINER_ELEMENT_SPEC,
    CONTAINER_SECTIONS,
    CONTAINERS_NOT_SEMANTICALLY_VALIDATED,
    IDENTITY_SCAN_SECTIONS,
    UNIT_CHOICES,
)
from ..models.diagnostics import Diagnostic
from ..models.enums import (
    ChainageDirection,
    DiagnosticCategory,
    Direction,
    Severity,
)
from ..models.project import Project
from . import codes
from .schema_validation import deprecated_project_type_note

#: Values accepted in a preserved container's ``direction`` field (Phase-1
#: vocabulary check only - no routing or topology meaning is attached).
_ACCEPTED_CONTAINER_DIRECTION_VALUES: tuple[str, ...] = tuple(
    value.value for value in (*Direction, *ChainageDirection)
)

#: Metadata keys reported by VAL-PROJECT-003 when absent.
_STANDARD_METADATA_FIELDS: tuple[str, ...] = (
    "project_type",
    "data_status",
    "engineering_status",
    "created_utc",
    "modified_utc",
)


def apply_container_defaults(project: Project) -> list[str]:
    """Ensure every container section is a JSON array, per the documented schema.

    The documented default for every container section is ``[]``. This is only
    applied when a container is absent or unusable (a malformed container is
    already reported as an ERROR by stage-1 validation). Returns the names of
    the sections that received the default.
    """
    applied: list[str] = []
    for section in CONTAINER_SECTIONS:
        if not isinstance(getattr(project, section, None), list):
            setattr(project, section, [])
            applied.append(section)
    return applied


def iter_container_objects(project: Project) -> Iterator[tuple[str, dict[str, Any]]]:
    """Yield ``(json_path, object)`` for every dictionary inside the preserved sections.

    Covers array container elements and the objects of their known nested lists,
    for example ``infrastructure[0].stations[2]`` or ``signalling.signals[0]``.
    """
    for section in IDENTITY_SCAN_SECTIONS:
        spec = CONTAINER_ELEMENT_SPEC.get(section, {})
        nested_lists = dict(spec.get("nested_lists") or {})
        for path, element in project.section_element_dicts(section):
            yield path, element
            for nested_key in nested_lists:
                nested_items = element.get(nested_key)
                if isinstance(nested_items, list):
                    for nested_index, nested_item in enumerate(nested_items):
                        if isinstance(nested_item, dict):
                            yield f"{path}.{nested_key}[{nested_index}]", nested_item


def validate_project(
    project: Project,
    *,
    defaults_applied: tuple[str, ...] = (),
    suppressed_field_paths: tuple[str, ...] = (),
    source_name: Optional[str] = None,
    phase2_validated_sections: tuple[str, ...] = (),
    skip_identity_object_types: tuple[str, ...] = (),
) -> list[Diagnostic]:
    """Run all Phase-1 semantic checks and return structured diagnostics.

    ``suppressed_field_paths`` names fields that stage-1 validation already
    reported as malformed and removed from the working copy. The "missing
    value" checks stay silent for those paths so that each problem is reported
    once, with the most specific diagnostic code.

    ``phase2_validated_sections`` names sections that Phase 2 validates
    semantically for this document (only ever ``infrastructure``, and only for
    projects that declare physical infrastructure); the Phase-1 "not yet
    validated" INFO is suppressed for them.

    ``skip_identity_object_types`` names Phase-1 nested object types whose
    identifier uniqueness is delegated to the Phase-2 engineering registry.
    """
    suppressed = set(suppressed_field_paths)
    diagnostics: list[Diagnostic] = []
    diagnostics.extend(_check_container_structure(project))
    diagnostics.extend(_report_applied_defaults(defaults_applied))
    diagnostics.extend(
        _report_preserved_but_unvalidated(project, validated_sections=phase2_validated_sections)
    )
    diagnostics.extend(_check_project_metadata(project, suppressed))
    diagnostics.extend(_check_reference_system(project, suppressed))
    diagnostics.extend(_check_directions(project, suppressed))
    diagnostics.extend(_check_identifiers(project, skip_object_types=skip_identity_object_types))
    diagnostics.extend(_check_container_enumerations(project))
    diagnostics.extend(_check_display_units(project))
    if source_name:
        for diagnostic in diagnostics:
            context = dict(diagnostic.context or {})
            context.setdefault("source", source_name)
            diagnostic.context = context
    return diagnostics


# ---------------------------------------------------------------------------
# checks
# ---------------------------------------------------------------------------
def _check_container_structure(project: Project) -> list[Diagnostic]:
    """Report malformed container elements and malformed nested lists."""
    diagnostics: list[Diagnostic] = []
    for section in IDENTITY_SCAN_SECTIONS:
        if section in CONTAINER_SECTIONS:
            for index, element in enumerate(project.container(section)):
                if not isinstance(element, dict):
                    diagnostics.append(
                        Diagnostic(
                            code=codes.VAL_SCHEMA_002,
                            severity=Severity.ERROR,
                            category=DiagnosticCategory.SCHEMA,
                            message=(
                                f"'{section}[{index}]' must be a JSON object, "
                                f"but it is a JSON {_type_name(element)}."
                            ),
                            context={"field": f"{section}[{index}]", "found_type": _type_name(element)},
                            suggested_action="Every entry of a container array must be an object.",
                        )
                    )
        spec = CONTAINER_ELEMENT_SPEC.get(section, {})
        nested_lists = dict(spec.get("nested_lists") or {})
        for path, element in project.section_element_dicts(section):
            for nested_key in nested_lists:
                if nested_key not in element:
                    continue
                nested_items = element.get(nested_key)
                nested_path = f"{path}.{nested_key}"
                if not isinstance(nested_items, list):
                    diagnostics.append(
                        Diagnostic(
                            code=codes.VAL_SCHEMA_002,
                            severity=Severity.ERROR,
                            category=DiagnosticCategory.SCHEMA,
                            message=(
                                f"'{nested_path}' must be a JSON array, "
                                f"but it is a JSON {_type_name(nested_items)}."
                            ),
                            context={"field": nested_path, "found_type": _type_name(nested_items)},
                            suggested_action=f"Use an array for '{nested_key}' (empty: []).",
                        )
                    )
                    continue
                for nested_index, nested_item in enumerate(nested_items):
                    if not isinstance(nested_item, dict):
                        diagnostics.append(
                            Diagnostic(
                                code=codes.VAL_SCHEMA_002,
                                severity=Severity.WARNING,
                                category=DiagnosticCategory.SCHEMA,
                                message=(
                                    f"'{nested_path}[{nested_index}]' is not an object "
                                    f"(JSON {_type_name(nested_item)}); it is preserved but "
                                    "cannot be inspected by Phase-1 validation."
                                ),
                                context={"field": f"{nested_path}[{nested_index}]"},
                                suggested_action="Represent container entries as objects.",
                            )
                        )
    return diagnostics


def _report_applied_defaults(applied: tuple[str, ...]) -> list[Diagnostic]:
    """Report sections that were absent and received their documented default."""
    return [
        Diagnostic(
            code=codes.VAL_FUTURE_001,
            severity=Severity.INFO,
            category=DiagnosticCategory.FUTURE,
            message=(
                f"Section '{section}' was absent and was created with its documented schema "
                "default (empty container [] for array sections, empty section object otherwise)."
            ),
            context={"section": section, "default": []},
            suggested_action="No action required; populate the section in a later phase.",
        )
        for section in applied
    ]


def _report_preserved_but_unvalidated(
    project: Project, *, validated_sections: tuple[str, ...] = ()
) -> list[Diagnostic]:
    """Tell the user which non-empty sections this phase preserves but does not check.

    ``validated_sections`` names sections that a later stage validated
    semantically (Phase 2 validates ``infrastructure`` of physical projects), so
    the "planned for a later development phase" note is not shown for them.
    """
    diagnostics: list[Diagnostic] = []
    for section in CONTAINERS_NOT_SEMANTICALLY_VALIDATED:
        if section in validated_sections:
            continue
        count = project.object_count(section)
        if count:
            diagnostics.append(
                Diagnostic(
                    code=codes.VAL_FUTURE_002,
                    severity=Severity.INFO,
                    category=DiagnosticCategory.FUTURE,
                    message=(
                        f"Section '{section}' contains {count} object(s); the data is preserved, "
                        "but semantic validation of this section is planned for a later "
                        "development phase."
                    ),
                    context={"section": section, "object_count": count},
                    suggested_action="No action required in Phase 1.",
                )
            )
    return diagnostics


def _check_project_metadata(project: Project, suppressed: set[str]) -> list[Diagnostic]:
    """Check ``project.id``, ``project.name``, types and metadata completeness."""
    diagnostics: list[Diagnostic] = []
    meta = project.project

    for field_name, label in (("id", "Project ID"), ("name", "Project Name")):
        if field_name == "name" and f"project.{field_name}" in suppressed:
            continue  # already reported as a malformed value by stage 1
        value = getattr(meta, field_name)
        if value is None or not str(value).strip():
            diagnostics.append(
                Diagnostic(
                    code=codes.VAL_PROJECT_001,
                    severity=Severity.ERROR,
                    category=DiagnosticCategory.PROJECT,
                    message=f"{label} (project.{field_name}) is missing or empty.",
                    object_id=None,
                    context={"field": f"project.{field_name}"},
                    suggested_action=(
                        f"Enter a {label} in the Project page (Project ID is the stable "
                        "machine identifier and must not be empty)."
                    ),
                )
            )
    for field_name in ("id", "name", "description", "project_type", "created_utc", "modified_utc"):
        value = getattr(meta, field_name)
        if value is not None and not isinstance(value, str):
            diagnostics.append(
                Diagnostic(
                    code=codes.VAL_PROJECT_002,
                    severity=Severity.ERROR,
                    category=DiagnosticCategory.PROJECT,
                    message=(
                        f"Field 'project.{field_name}' must be a JSON string, "
                        f"but it is a {type(value).__name__}."
                    ),
                    context={"field": f"project.{field_name}", "found_type": type(value).__name__},
                    suggested_action="Correct the field value and re-import the project.",
                )
            )
    for field_name in ("data_status", "engineering_status"):
        value = getattr(meta, field_name)
        if value is not None and not isinstance(value, (str, bytes)) and not hasattr(
            value, "value"
        ):
            diagnostics.append(
                Diagnostic(
                    code=codes.VAL_ENUM_001,
                    severity=Severity.ERROR,
                    category=DiagnosticCategory.ENUM,
                    message=(
                        f"Field 'project.{field_name}' has an unsupported value {value!r}."
                    ),
                    context={"field": f"project.{field_name}", "found": repr(value)},
                    suggested_action="Use one of the documented enumeration values.",
                )
            )

    missing = [
        field
        for field in _STANDARD_METADATA_FIELDS
        if getattr(meta, field, None) in (None, "") and f"project.{field}" not in suppressed
    ]
    if missing:
        diagnostics.append(
            Diagnostic(
                code=codes.VAL_PROJECT_003,
                severity=Severity.INFO,
                category=DiagnosticCategory.PROJECT,
                message=(
                    "Standard project metadata not supplied: " + ", ".join(f"project.{f}" for f in missing)
                ),
                context={"missing_fields": [f"project.{f}" for f in missing]},
                suggested_action=(
                    "Optional: fill these fields for a complete project record. "
                    "created_utc/modified_utc are set automatically for new projects."
                ),
            )
        )

    note = deprecated_project_type_note(meta.project_type)
    if note:
        diagnostics.append(
            Diagnostic(
                code=codes.VAL_PROJECT_004,
                severity=Severity.INFO,
                category=DiagnosticCategory.PROJECT,
                message=f"project.project_type '{meta.project_type}' is deprecated.",
                context={"field": "project.project_type", "found": meta.project_type},
                suggested_action=note,
            )
        )
    return diagnostics


def _check_reference_system(project: Project, suppressed: set[str]) -> list[Diagnostic]:
    """Check chainage bounds and required reference information."""
    diagnostics: list[Diagnostic] = []
    reference = project.reference_system

    missing = [
        field
        for field in ("alignment_id", "chainage_start_km", "chainage_end_km")
        if getattr(reference, field, None) is None
        and f"reference_system.{field}" not in suppressed
    ]
    if missing:
        diagnostics.append(
            Diagnostic(
                code=codes.VAL_REF_002,
                severity=Severity.ERROR,
                category=DiagnosticCategory.REF,
                message=(
                    "Required reference-system information is missing: "
                    + ", ".join(f"reference_system.{f}" for f in missing)
                ),
                context={"missing_fields": [f"reference_system.{f}" for f in missing]},
                suggested_action=(
                    "Provide the alignment id and the chainage start/end values "
                    "(Project page or JSON import)."
                ),
            )
        )

    start = reference.chainage_start_km
    end = reference.chainage_end_km
    both_numeric = (
        isinstance(start, (int, float))
        and not isinstance(start, bool)
        and isinstance(end, (int, float))
        and not isinstance(end, bool)
    )
    if both_numeric and end <= start:
        relation = "equal" if end == start else "reversed"
        if relation == "reversed":
            message = (
                f"Chainage end ({end} km) must be greater than chainage start ({start} km); "
                "the values appear to be swapped."
            )
            action = (
                "Swap or correct the chainage start/end values. Changing the simulation "
                "direction does not change the stored chainage values."
            )
        else:
            message = (
                f"Chainage end equals chainage start ({start} km); the project has zero length "
                "and chainage_end_km must be greater than chainage_start_km."
            )
            action = (
                "Set reference_system.chainage_start_km and chainage_end_km to the analysis "
                "range. (Per-track chainage points belong inside the infrastructure containers; "
                "the reference system describes the project range itself.)"
            )
        diagnostics.append(
            Diagnostic(
                code=codes.VAL_REF_001,
                severity=Severity.ERROR,
                category=DiagnosticCategory.REF,
                message=message,
                object_id=reference.alignment_id,
                context={
                    "chainage_start_km": start,
                    "chainage_end_km": end,
                    "relation": relation,
                    "field": "reference_system.chainage_end_km",
                },
                suggested_action=action,
            )
        )
    return diagnostics


def _check_directions(project: Project, suppressed: set[str]) -> list[Diagnostic]:
    """Check the chainage direction enumerations of the reference system."""
    diagnostics: list[Diagnostic] = []
    reference = project.reference_system
    allowed = tuple(direction.value for direction in ChainageDirection)

    for field_name, label in (
        ("forward_direction", "forward"),
        ("reverse_direction", "reverse"),
    ):
        value = getattr(reference, field_name)
        field_path = f"reference_system.{field_name}"
        if value is None:
            if field_path in suppressed:
                continue  # already reported as an unsupported value by stage 1
            diagnostics.append(
                Diagnostic(
                    code=codes.VAL_DIR_001,
                    severity=Severity.ERROR,
                    category=DiagnosticCategory.DIR,
                    message=f"The {label} chainage direction ('{field_path}') is missing.",
                    context={"field": field_path, "allowed": list(allowed)},
                    suggested_action=(
                        "For a normal linear project set forward_direction="
                        f"{allowed[0]} and reverse_direction={allowed[1]}."
                    ),
                )
            )
            continue
        value_text = getattr(value, "value", value)
        if value_text not in allowed:
            diagnostics.append(
                Diagnostic(
                    code=codes.VAL_DIR_001,
                    severity=Severity.ERROR,
                    category=DiagnosticCategory.DIR,
                    message=(
                        f"'{field_path}' has unsupported direction value {value_text!r}; "
                        f"supported values are {list(allowed)}."
                    ),
                    context={"field": field_path, "found": value_text, "allowed": list(allowed)},
                    suggested_action="Use one of the supported chainage direction values.",
                )
            )

    forward = getattr(reference.forward_direction, "value", reference.forward_direction)
    reverse = getattr(reference.reverse_direction, "value", reference.reverse_direction)
    if forward is not None and reverse is not None and forward == reverse:
        diagnostics.append(
            Diagnostic(
                code=codes.VAL_DIR_002,
                severity=Severity.WARNING,
                category=DiagnosticCategory.DIR,
                message=(
                    f"Forward and reverse chainage direction are both '{forward}'; the two "
                    "travel directions would refer to the same chainage sense."
                ),
                context={"forward_direction": forward, "reverse_direction": reverse},
                suggested_action=(
                    "Use INCREASING_CHAINAGE for forward and DECREASING_CHAINAGE for reverse."
                ),
            )
        )
    return diagnostics


def _check_identifiers(
    project: Project, *, skip_object_types: tuple[str, ...] = ()
) -> list[Diagnostic]:
    """Report malformed and duplicated identifiers among container objects.

    ``skip_object_types`` names Phase-1 nested object types whose identifier
    uniqueness is now owned by the Phase-2 engineering registry (a declared
    supersession: duplicate registered IDs are reported as VAL-REGISTRY-001 with
    project-wide scope instead of per object type).
    """
    diagnostics: list[Diagnostic] = []
    seen: dict[tuple[str, str], list[tuple[str, Any]]] = {}

    for object_type, path, field_name, value in project.iter_identity_fields():
        if object_type in skip_object_types:
            continue
        field_path = f"{path}.{field_name}"
        if not isinstance(value, str) or not value.strip():
            diagnostics.append(
                Diagnostic(
                    code=codes.VAL_ID_002,
                    severity=Severity.ERROR,
                    category=DiagnosticCategory.ID,
                    message=(
                        f"Identifier '{field_path}' must be a non-empty string; "
                        f"found {value!r}."
                    ),
                    context={"field": field_path, "found": value, "object_type": object_type},
                    suggested_action=(
                        "Give the object a stable machine identifier "
                        "(e.g. STN-0001) or remove the identifier field."
                    ),
                )
            )
            continue
        seen.setdefault((object_type, field_name), []).append((path, value))

    for (object_type, field_name), entries in sorted(seen.items()):
        by_value: dict[str, list[str]] = {}
        for path, value in entries:
            by_value.setdefault(value, []).append(path)
        for value, paths in sorted(by_value.items()):
            if len(paths) > 1:
                diagnostics.append(
                    Diagnostic(
                        code=codes.VAL_ID_001,
                        severity=Severity.ERROR,
                        category=DiagnosticCategory.ID,
                        message=(
                            f"Duplicate {object_type} {field_name} '{value}' "
                            f"({len(paths)} occurrences)."
                        ),
                        object_id=value,
                        context={"object_type": object_type, "field": field_name, "paths": paths},
                        suggested_action=(
                            "Identifiers must be unique per object type; rename or remove the "
                            "duplicate. Display names may repeat - identifiers may not."
                        ),
                    )
                )
    return diagnostics


def _check_container_enumerations(project: Project) -> list[Diagnostic]:
    """Report invalid ``direction`` values inside preserved containers."""
    diagnostics: list[Diagnostic] = []
    for path, obj in iter_container_objects(project):
        if "direction" not in obj:
            continue
        value = obj.get("direction")
        if value is None:
            continue
        if not isinstance(value, str) or value not in _ACCEPTED_CONTAINER_DIRECTION_VALUES:
            diagnostics.append(
                Diagnostic(
                    code=codes.VAL_ENUM_001,
                    severity=Severity.ERROR,
                    category=DiagnosticCategory.ENUM,
                    message=(
                        f"'{path}.direction' has unsupported value {value!r}; supported values "
                        f"are {list(_ACCEPTED_CONTAINER_DIRECTION_VALUES)}."
                    ),
                    object_id=str(obj.get("id")) if isinstance(obj.get("id"), str) else None,
                    context={
                        "field": f"{path}.direction",
                        "found": value,
                        "allowed": list(_ACCEPTED_CONTAINER_DIRECTION_VALUES),
                    },
                    suggested_action="Use one of the supported direction values.",
                )
            )
    return diagnostics


def _check_display_units(project: Project) -> list[Diagnostic]:
    """Warn about unrecognised display-unit strings (presentation only)."""
    diagnostics: list[Diagnostic] = []
    units = project.display_units
    for field_name, allowed in UNIT_CHOICES.items():
        value = getattr(units, field_name, None)
        if value is None:
            continue
        if not isinstance(value, str) or value not in allowed:
            diagnostics.append(
                Diagnostic(
                    code=codes.VAL_UNIT_001,
                    severity=Severity.WARNING,
                    category=DiagnosticCategory.UNIT,
                    message=(
                        f"display_units.{field_name} = {value!r} is not a recognised display "
                        f"unit; known options are {list(allowed)}."
                    ),
                    context={"field": f"display_units.{field_name}", "found": value, "known": list(allowed)},
                    suggested_action=(
                        "Display units are presentation preferences only; the value is kept "
                        "as supplied. Adjust it in a later phase's unit editor if needed."
                    ),
                )
            )
    return diagnostics


def _type_name(value: Any) -> str:
    """Return a JSON-ish type name for diagnostic messages."""
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if value is None:
        return "null"
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return "array"
    return type(value).__name__


def chainage_bounds(project: Project) -> tuple[Optional[float], Optional[float]]:
    """Return the stored chainage start/end as numbers (``None`` when unusable)."""
    reference = project.reference_system
    start = reference.chainage_start_km
    end = reference.chainage_end_km
    start_value = float(start) if isinstance(start, (int, float)) and not isinstance(start, bool) else None
    end_value = float(end) if isinstance(end, (int, float)) and not isinstance(end, bool) else None
    return start_value, end_value
