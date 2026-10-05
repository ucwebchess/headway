"""Validation framework: structured diagnostics for project documents.

Three stages, deliberately separated:

* :mod:`~railway_headway_sim.validation.schema_validation` - raw JSON structure,
  schema version, field types (works on plain parsed data).
* :mod:`~railway_headway_sim.validation.project_validation` - structural/basic
  semantic checks on the canonical model (Phase 1).
* :mod:`~railway_headway_sim.validation.infrastructure_validation` - the typed
  physical infrastructure, topology, station/platform/stopping-mark and registry
  checks (Phase 2), run **only** for projects that declare physical
  infrastructure.  Legacy (opaque) projects keep the exact Phase-1 behaviour.

The facade :func:`validate_document` runs the applicable stages and returns
everything the application layer needs: the (possibly ``None``) project, the
diagnostics (one single diagnostic model, no duplicate result classes), the list
of container sections that received documented defaults, and the assurance scope
of the run (Section AH).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Optional

from pydantic import ValidationError

from ..constants import INFRASTRUCTURE_SECTION, SCHEMA_VERSION_FIELD, TOP_LEVEL_SECTIONS
from ..infrastructure.compiler import compile_infrastructure
from ..models.diagnostics import Diagnostic, ValidationResult
from ..models.enums import DiagnosticCategory, Severity, ValidationScope
from ..models.project import Project
from . import codes
from .infrastructure_validation import (
    iter_registered_ids,
    validate_infrastructure,
    validation_scope_for,
)
from .rolling_stock_validation import (
    validate_rolling_stock,
    validate_rolling_stock_catalogue,
)
from .project_validation import (
    apply_container_defaults,
    chainage_bounds,
    iter_container_objects,
    validate_project,
)
from .schema_validation import validate_schema_and_sanitize

__all__ = [
    "ValidationOutcome",
    "apply_container_defaults",
    "chainage_bounds",
    "codes",
    "compile_infrastructure",
    "iter_container_objects",
    "iter_registered_ids",
    "phase2_identity_supersessions",
    "validate_document",
    "validate_infrastructure",
    "validate_json_text",
    "validate_in_memory_project",
    "validate_project",
    "validate_rolling_stock",
    "validate_rolling_stock_catalogue",
    "validate_schema_and_sanitize",
    "validation_scope_for",
]


@dataclass(frozen=True)
class ValidationOutcome:
    """Result of validating one document: model (if buildable) + diagnostics."""

    project: Optional[Project]
    result: ValidationResult
    defaults_applied: tuple[str, ...] = ()
    schema_version_seen: Optional[str] = None
    source_name: str = ""

    @property
    def ok(self) -> bool:
        """Return ``True`` when a project model could be built from the document."""
        return self.project is not None


def _error_result(code: str, message: str, *, severity: Severity = Severity.ERROR,
                  category: DiagnosticCategory = DiagnosticCategory.SCHEMA,
                  context: Optional[dict[str, Any]] = None,
                  suggested_action: Optional[str] = None) -> ValidationResult:
    """Build a single-diagnostic result (used for early, unrecoverable failures)."""
    return ValidationResult.from_diagnostics(
        [
            Diagnostic(
                code=code,
                severity=severity,
                category=category,
                message=message,
                context=context,
                suggested_action=suggested_action,
            )
        ]
    )


def validate_document(data: Any, *, source_name: str = "") -> ValidationOutcome:
    """Validate parsed JSON data end-to-end and build the canonical model.

    Never raises for *data* problems: schema problems, malformed fields and
    model-construction failures are all returned as structured diagnostics.
    Unexpected programming errors are **not** swallowed here.
    """
    seen_version = data.get(SCHEMA_VERSION_FIELD) if isinstance(data, dict) else None
    seen_version_text = seen_version if isinstance(seen_version, str) else None

    document, schema_diagnostics, removed_paths = validate_schema_and_sanitize(data)
    if document is None:
        return ValidationOutcome(
            project=None,
            result=ValidationResult.from_diagnostics(schema_diagnostics),
            defaults_applied=(),
            schema_version_seen=seen_version_text,
            source_name=source_name,
        )

    # Sections that were absent from the incoming document receive their
    # documented schema default (empty container / empty section object). This
    # is reported per section as VAL-FUTURE-001 so nothing changes silently.
    removed = set(removed_paths)
    defaults_applied = tuple(
        section
        for section in TOP_LEVEL_SECTIONS
        if section != SCHEMA_VERSION_FIELD and section not in document and section not in removed
    )
    schema_version_seen = document.get("schema_version")

    try:
        project = Project.model_validate(document)
    except ValidationError as exc:
        # The sanitizer is designed to make this unreachable for known fields;
        # any remaining failure is reported with exact field locations.
        diagnostics = list(schema_diagnostics)
        for error in exc.errors():
            location = ".".join(str(part) for part in error.get("loc", ())) or "<document>"
            diagnostics.append(
                Diagnostic(
                    code=codes.VAL_SCHEMA_002,
                    severity=Severity.ERROR,
                    category=DiagnosticCategory.SCHEMA,
                    message=f"Field '{location}' is invalid: {error.get('msg', 'unknown error')}.",
                    context={"field": location, "error_type": str(error.get("type"))},
                    suggested_action="Correct the field value and re-import the project.",
                )
            )
        return ValidationOutcome(
            project=None,
            result=ValidationResult.from_diagnostics(diagnostics),
            defaults_applied=(),
            schema_version_seen=schema_version_seen if isinstance(schema_version_seen, str) else None,
            source_name=source_name,
        )

    apply_container_defaults(project)  # guarantee arrays exist for the model
    compiled = _compiled_infrastructure(project)
    diagnostics = list(schema_diagnostics)
    diagnostics.extend(
        validate_project(
            project,
            defaults_applied=defaults_applied,
            suppressed_field_paths=removed_paths,
            source_name=source_name,
            phase2_validated_sections=(
                (INFRASTRUCTURE_SECTION,) if compiled.physical else ()
            ),
            skip_identity_object_types=(
                phase2_identity_supersessions() if compiled.physical else ()
            ),
        )
    )
    diagnostics.extend(_infrastructure_diagnostics(project, compiled=compiled))
    return ValidationOutcome(
        project=project,
        result=ValidationResult.from_diagnostics(
            diagnostics, scope=_assurance_scope(project, compiled=compiled)
        ),
        defaults_applied=defaults_applied,
        schema_version_seen=schema_version_seen if isinstance(schema_version_seen, str) else None,
        source_name=source_name,
    )


def _compiled_infrastructure(project: Project):
    """Compile the project's infrastructure array into typed views (Phase 2)."""
    infrastructure = getattr(project, "infrastructure", None) or ()
    return compile_infrastructure(infrastructure)


def phase2_identity_supersessions() -> tuple[str, ...]:
    """Return the Phase-1 nested object types now owned by the Phase-2 registry.

    Phase-2 typed catalogues live *inside* a layer object; where such a catalogue
    reuses a Phase-1 nested list name (``stations``), identifier uniqueness moves
    from the per-object-type Phase-1 check to the project-wide engineering
    registry (declared supersession for ``VAL-REG-011``).
    """
    from ..constants import CONTAINER_ELEMENT_SPEC
    from ..models.infrastructure import CATALOGUE_SPEC

    nested = CONTAINER_ELEMENT_SPEC.get(INFRASTRUCTURE_SECTION, {}).get("nested_lists") or {}
    return tuple(sorted({nested[key] for key in CATALOGUE_SPEC if key in nested}))


def _infrastructure_diagnostics(project: Project, *, compiled: Any = None) -> list[Diagnostic]:
    """Return the Phase-2 diagnostics of *project* (empty for legacy projects).

    Phase-2 checks run only when the project declares physical infrastructure, so
    Phase-1 documents are validated exactly as before (declared supersessions
    aside).  The compiled infrastructure is reused by the UI through
    :func:`compile_infrastructure`.
    """
    if compiled is None:
        compiled = _compiled_infrastructure(project)
    if not compiled.physical:
        return []
    reference = getattr(project, "reference_system", None)
    source = getattr(reference, "alignment_id", None) if reference is not None else None
    diagnostics = list(compiled.diagnostics)
    diagnostics.extend(
        validate_infrastructure(compiled, reference_alignment_id=source)
    )
    return diagnostics


def _assurance_scope(project: Project, *, compiled: Any = None) -> ValidationScope:
    """Return the assurance scope of a successful validation run (Section AH)."""
    if compiled is None:
        compiled = _compiled_infrastructure(project)
    if compiled.physical:
        return compiled.scope
    return ValidationScope.BASIC_PROJECT


def validate_json_text(text: str, *, source_name: str = "<text>") -> ValidationOutcome:
    """Parse JSON text and validate it (safely - parsed as data only).

    JSON parse failures are reported as ``VAL-SCHEMA-001``; the text is never
    evaluated, imported or deserialized with anything other than :func:`json.loads`.
    """
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, ValueError) as exc:
        message = (
            f"The document is not valid JSON text: {exc.msg} (line {exc.lineno}, column {exc.colno})."
            if isinstance(exc, json.JSONDecodeError)
            else f"The document is not valid JSON text: {exc}."
        )
        return ValidationOutcome(
            project=None,
            result=_error_result(
                codes.VAL_SCHEMA_001,
                message,
                suggested_action=(
                    "Check for trailing commas, comments or unquoted keys - JSON does not "
                    "allow them - and re-import the file."
                ),
                context={"source": source_name},
            ),
            source_name=source_name,
        )
    return validate_document(data, source_name=source_name)


def validate_in_memory_project(project: Project) -> ValidationResult:
    """Re-validate an existing project object (no defaults are applied here).

    The project is validated through its canonical serialization, so the audit
    result describes exactly what would be exported.
    """
    from ..io.project_io import to_normalized_dict

    return validate_document(to_normalized_dict(project), source_name="<in-memory project>").result
