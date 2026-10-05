"""Reusable structured diagnostics and validation results.

This module is intentionally free of UI and I/O dependencies so that it can be
used by validators, the controller, tests and any future simulation module.
"""

from __future__ import annotations

from typing import Any, Iterable, Optional

from pydantic import BaseModel, ConfigDict, Field

from .enums import DiagnosticCategory, Severity, ValidationScope, ValidationStatus

#: Severity ordering used for deterministic sorting (most severe first).
_SEVERITY_RANK: dict[Severity, int] = {
    Severity.ERROR: 0,
    Severity.WARNING: 1,
    Severity.INFO: 2,
}


class Diagnostic(BaseModel):
    """A single structured validation/audit finding.

    Diagnostics never replace exceptions for programming errors: they describe
    problems in *data* in a way the UI can display, count, filter and log.
    """

    model_config = ConfigDict(extra="forbid")

    code: str = Field(description="Stable diagnostic code, e.g. 'VAL-REF-001'.")
    severity: Severity = Field(description="INFO, WARNING or ERROR.")
    category: DiagnosticCategory = Field(description="Grouping category of the code.")
    message: str = Field(description="Human-readable description of the finding.")
    object_id: Optional[str] = Field(
        default=None, description="Identifier of the affected object, when known."
    )
    context: Optional[dict[str, Any]] = Field(
        default=None, description="Machine-readable details (JSON path, values, field names)."
    )
    suggested_action: Optional[str] = Field(
        default=None, description="What the user can do to resolve the finding."
    )

    def sort_key(self) -> tuple[int, str, str, str]:
        """Return the deterministic ordering key for this diagnostic."""
        return (
            _SEVERITY_RANK[self.severity],
            self.code,
            self.object_id or "",
            self.message,
        )

    def format_line(self) -> str:
        """Return a compact one-line text form (used by CLI/tests/logs)."""
        parts = [f"[{self.severity.value}]", self.code, f"({self.category.value})", self.message]
        if self.object_id:
            parts.append(f"object_id={self.object_id}")
        if self.suggested_action:
            parts.append(f"-> {self.suggested_action}")
        return " ".join(parts)


class ValidationResult(BaseModel):
    """Overall validation outcome: a status plus structured diagnostics."""

    model_config = ConfigDict(extra="forbid")

    status: ValidationStatus
    diagnostics: list[Diagnostic] = Field(default_factory=list)
    error_count: int = 0
    warning_count: int = 0
    info_count: int = 0
    scope: Optional[ValidationScope] = Field(
        default=None,
        description=(
            "Level of assurance this run provided (Section AH). None means the scope "
            "was not determined (e.g. the document could not be parsed)."
        ),
    )

    # -- construction ------------------------------------------------------
    @classmethod
    def from_diagnostics(
        cls,
        diagnostics: Iterable[Diagnostic],
        *,
        scope: Optional[ValidationScope] = None,
    ) -> "ValidationResult":
        """Build a result from diagnostics, sorted most-severe-first."""
        ordered = sorted(diagnostics, key=Diagnostic.sort_key)
        errors = sum(1 for d in ordered if d.severity is Severity.ERROR)
        warnings = sum(1 for d in ordered if d.severity is Severity.WARNING)
        infos = sum(1 for d in ordered if d.severity is Severity.INFO)
        if errors:
            status = ValidationStatus.INVALID
        elif warnings:
            status = ValidationStatus.VALID_WITH_WARNINGS
        else:
            status = ValidationStatus.VALID
        return cls(
            status=status,
            diagnostics=ordered,
            error_count=errors,
            warning_count=warnings,
            info_count=infos,
            scope=scope,
        )

    @classmethod
    def empty_valid(cls) -> "ValidationResult":
        """Return a VALID result with no diagnostics."""
        return cls.from_diagnostics([])

    # -- queries -----------------------------------------------------------
    def has_errors(self) -> bool:
        """Return ``True`` when at least one ERROR diagnostic is present."""
        return self.error_count > 0

    def has_warnings(self) -> bool:
        """Return ``True`` when at least one WARNING diagnostic is present."""
        return self.warning_count > 0

    def diagnostics_with_code_prefix(self, prefix: str) -> list[Diagnostic]:
        """Return diagnostics whose code starts with *prefix* (e.g. ``"VAL-REF"``)."""
        return [d for d in self.diagnostics if d.code.startswith(prefix)]

    def codes(self) -> list[str]:
        """Return the codes of all diagnostics, in display order."""
        return [d.code for d in self.diagnostics]

    def summary_text(self) -> str:
        """Return a one-line human summary of this result."""
        return (
            f"{self.status.value} - "
            f"{self.error_count} error(s), {self.warning_count} warning(s), "
            f"{self.info_count} info item(s)"
        )

    def scope_text(self) -> str:
        """Return the assurance scope label (Section AH), or '(not determined)'."""
        return self.scope.value if self.scope is not None else "(scope not determined)"

    def summary_with_scope(self) -> str:
        """Return the status summary followed by the assurance scope."""
        return f"{self.summary_text()} - assurance scope: {self.scope_text()}"

    def is_phase2_physical(self) -> bool:
        """Return ``True`` when this run validated typed physical infrastructure."""
        return self.scope is ValidationScope.PHASE2_PHYSICAL_INFRASTRUCTURE

    def as_text_lines(self) -> list[str]:
        """Return the status summary followed by one line per diagnostic."""
        return [self.summary_text()] + [d.format_line() for d in self.diagnostics]
