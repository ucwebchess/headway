"""Application/project controller.

The controller owns the application state: current project, direction selection,
validation results, export/import outcomes and the modification/hash bookkeeping.
UI widgets only *call* the controller and *render* its state - no engineering or
project state is stored inside widget values.

Direction selection is intentionally part of the controller state, not of the
project model: changing it never modifies project data (see
:meth:`ProjectController.set_direction`).
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Callable, Optional, Union

from pydantic import ValidationError

from ..infrastructure.compiler import CompiledInfrastructure, compile_infrastructure
from ..infrastructure.static_geometry import compute_static_footprint, traversal_for_direction
from ..io.project_io import (
    ExportOutcome,
    FileSource,
    ImportOutcome,
    export_project,
    import_project_from_bytes,
    import_project_from_data,
    import_project_from_file,
    import_project_from_text,
    import_project_from_uploaded,
    project_hash,
    short_hash,
    to_normalized_dict,
)
from ..models.common import utc_now_iso
from ..models.diagnostics import Diagnostic, ValidationResult
from ..models.enums import (
    DataStatus,
    DiagnosticCategory,
    Direction,
    EngineeringStatus,
    Severity,
    SELECTABLE_DIRECTIONS,
    ValidationScope,
)
from ..models.project import Project
from ..validation import codes, validate_document, ValidationOutcome
from ..version import APP_VERSION, DEFAULT_PROJECT_SCHEMA_VERSION

#: Project metadata/reference fields the UI may edit through the controller.
EDITABLE_METADATA_FIELDS: tuple[tuple[str, str], ...] = (
    ("id", "project"),
    ("name", "project"),
    ("description", "project"),
    ("chainage_origin_name", "reference_system"),
    ("chainage_end_name", "reference_system"),
    ("chainage_start_km", "reference_system"),
    ("chainage_end_km", "reference_system"),
)

#: Metadata fields that are number-typed (accept int/float, or a numeric string).
_NUMBER_FIELDS: tuple[str, ...] = ("chainage_start_km", "chainage_end_km")

#: Metadata fields that are enumeration-typed.
_ENUM_FIELDS: dict[str, type] = {"data_status": DataStatus, "engineering_status": EngineeringStatus}


@dataclass(frozen=True)
class ControllerState:
    """Immutable snapshot of the controller state (safe to render in the UI)."""

    has_project: bool = False
    direction: Direction = Direction.FORWARD
    direction_changed_utc: Optional[str] = None
    validation_status: Optional[str] = None
    assurance_scope: Optional[str] = None
    current_project_hash: Optional[str] = None
    last_validated_hash: Optional[str] = None
    modified_since_validation: bool = False
    schema_version: Optional[str] = None
    app_version: str = APP_VERSION
    project_revision: int = 0
    defaults_applied: tuple[str, ...] = ()
    last_action: str = ""
    last_message: str = ""
    last_message_severity: Severity = Severity.INFO
    last_source_name: Optional[str] = None
    last_export_filename: Optional[str] = None
    last_export_path: Optional[str] = None
    last_export_used_browser: bool = False
    import_schema_version_seen: Optional[str] = None
    # -- Phase-2 draft mechanism (APP-EDIT-002) ----------------------------
    draft_pending: bool = False
    draft_description: str = ""
    draft_status: Optional[str] = None
    draft_blocks_export: bool = False

    # -- derived helpers (single source for UI text) -----------------------
    @property
    def freshness_text(self) -> str:
        """Return 'VALIDATED CURRENT' or 'PROJECT MODIFIED SINCE VALIDATION'."""
        if self.validation_status is None:
            return "NOT YET VALIDATED"
        return "PROJECT MODIFIED SINCE VALIDATION" if self.modified_since_validation else "VALIDATED CURRENT"

    @property
    def direction_label(self) -> str:
        """Return the stable machine value of the selected direction."""
        return self.direction.value

    @property
    def display_direction(self) -> str:
        """Return the selected direction, constrained to the Phase-1 selector."""
        return self.direction.value if self.direction in SELECTABLE_DIRECTIONS else Direction.FORWARD.value

    def short_current_hash(self) -> str:
        """Return the abbreviated current project hash for compact display."""
        return short_hash(self.current_project_hash)

    def short_validated_hash(self) -> str:
        """Return the abbreviated last-validated hash for compact display."""
        return short_hash(self.last_validated_hash)

    def __post_init__(self) -> None:
        if self.direction not in SELECTABLE_DIRECTIONS:
            raise ValueError(
                f"Phase-1 direction selection must be one of "
                f"{[d.value for d in SELECTABLE_DIRECTIONS]}, got {self.direction!r}."
            )


class ProjectController:
    """Owns the current project, its validation state and the run selection."""

    def __init__(
        self,
        project: Optional[Project] = None,
        *,
        direction: Direction = Direction.FORWARD,
        export_directory: Optional[Union[str, Path]] = None,
        download_on_export: bool = True,
    ) -> None:
        self._project: Optional[Project] = project
        self._validation: Optional[ValidationResult] = None
        self._last_validated_hash: Optional[str] = None
        self._last_import: Optional[ImportOutcome] = None
        self._listeners: list[Callable[[], None]] = []
        self._export_directory = Path(export_directory) if export_directory is not None else Path.cwd()
        self._download_on_export = download_on_export
        self._draft_document: Optional[dict[str, Any]] = None
        self._draft_outcome: Optional[ValidationOutcome] = None
        self._draft_description: str = ""
        self._compiled_cache: Optional[tuple[int, CompiledInfrastructure]] = None
        self._assurance_scope: Optional[ValidationScope] = None
        self._state = ControllerState(
            has_project=project is not None,
            direction=direction,
            schema_version=_schema_version_of(project) if project is not None else None,
            last_message="Controller initialised." if project is None else "Controller initialised with a project.",
        )
        if project is not None:
            self._set_hash_and_revision(project)
        self._recompute_modification_flag()

    # ------------------------------------------------------------------
    # construction helpers
    # ------------------------------------------------------------------
    @classmethod
    def new_project(
        cls, *, direction: Direction = Direction.FORWARD, **project_kwargs: Any
    ) -> "ProjectController":
        """Create a controller that already holds a valid new project template.

        ``project_kwargs`` are passed to :meth:`Project.new` (project_id, name,
        description, chainage_start_km, chainage_end_km, origin_name, end_name...).
        """
        controller = cls(direction=direction)
        controller.create_new_project(**project_kwargs)
        return controller

    # ------------------------------------------------------------------
    # state access
    # ------------------------------------------------------------------
    @property
    def state(self) -> ControllerState:
        """Return the current immutable state snapshot."""
        return self._state

    @property
    def project(self) -> Optional[Project]:
        """Return the current project, or ``None`` when no project is loaded."""
        return self._project

    @property
    def has_project(self) -> bool:
        """Return whether a project is loaded."""
        return self._project is not None

    @property
    def direction(self) -> Direction:
        """Return the currently selected application direction."""
        return self._state.direction

    @property
    def validation(self) -> Optional[ValidationResult]:
        """Return the most recent validation result (may be stale)."""
        return self._validation

    @property
    def diagnostics(self) -> list[Diagnostic]:
        """Return the diagnostics of the most recent validation (empty if none)."""
        return list(self._validation.diagnostics) if self._validation else []

    @property
    def current_project_hash(self) -> Optional[str]:
        """Return the canonical hash of the current project content."""
        return self._state.current_project_hash

    @property
    def last_validated_hash(self) -> Optional[str]:
        """Return the project hash captured at the last successful validation."""
        return self._last_validated_hash

    @property
    def modified_since_validation(self) -> bool:
        """Return ``True`` when project content changed after the last validation."""
        return self._state.modified_since_validation

    @property
    def assurance_scope(self) -> Optional[ValidationScope]:
        """Return the assurance scope recorded by the last validation run."""
        return self._assurance_scope

    @property
    def draft_pending(self) -> bool:
        """Return ``True`` while an uncommitted draft document is staged."""
        return self._draft_document is not None

    @property
    def draft_result(self) -> Optional[ValidationResult]:
        """Return the validation result of the staged draft (``None`` if none)."""
        return self._draft_outcome.result if self._draft_outcome is not None else None

    @property
    def draft_blocks_export(self) -> bool:
        """Return ``True`` when a staged, INVALID draft blocks export."""
        result = self.draft_result
        return result is not None and result.has_errors()

    @property
    def compiled_infrastructure(self) -> Optional[CompiledInfrastructure]:
        """Return the compiled typed infrastructure of the current project.

        The result is cached per project revision: compiling is a pure read of
        the canonical model, and all engineering interpretation stays in
        :mod:`railway_headway_sim.infrastructure`.
        """
        project = self._project
        if project is None:
            return None
        revision = self._state.project_revision
        if self._compiled_cache is None or self._compiled_cache[0] != revision:
            infrastructure = getattr(project, "infrastructure", None) or ()
            self._compiled_cache = (revision, compile_infrastructure(infrastructure))
        return self._compiled_cache[1]

    @property
    def is_physical_project(self) -> bool:
        """Return ``True`` when the current project declares physical infrastructure."""
        compiled = self.compiled_infrastructure
        return bool(compiled is not None and compiled.physical)

    @property
    def last_import(self) -> Optional[ImportOutcome]:
        """Return the outcome of the most recent import attempt."""
        return self._last_import

    # ------------------------------------------------------------------
    # observer plumbing (UI subscribes; the controller never imports widgets)
    # ------------------------------------------------------------------
    def subscribe(self, listener: Callable[[], None]) -> Callable[[], None]:
        """Register *listener* for state changes; returns an unsubscribe callable."""
        self._listeners.append(listener)

        def unsubscribe() -> None:
            if listener in self._listeners:
                self._listeners.remove(listener)

        return unsubscribe

    def _notify(self) -> None:
        for listener in list(self._listeners):
            listener()

    def _publish(self, **changes: Any) -> None:
        """Publish a new state snapshot and notify observers."""
        self._state = replace(self._state, **changes)
        self._notify()

    # ------------------------------------------------------------------
    # project lifecycle
    # ------------------------------------------------------------------
    def create_new_project(self, **project_kwargs: Any) -> Project:
        """Create, store and validate a minimal schema-1.0 project template."""
        project = Project.new(**project_kwargs)
        self._replace_project(
            project,
            last_action="new_project",
            last_message="New project created from the Phase-1 template.",
            last_message_severity=Severity.INFO,
            last_source_name="<new project template>",
            defaults_applied=(),
            import_schema_version_seen=None,
        )
        result = self.validate_project()
        self._publish(
            last_message=(
                f"New project '{project.project.name}' created and validated: {result.summary_text()}"
            ),
            last_message_severity=Severity.INFO if not result.has_errors() else Severity.ERROR,
        )
        return project

    def replace_project(self, project: Project, *, message: str = "Project replaced.", action: str = "load") -> None:
        """Replace the current project (used by APIs/tests; the UI imports instead)."""
        self._replace_project(
            project,
            last_action=action,
            last_message=message,
            last_message_severity=Severity.INFO,
        )

    def _replace_project(
        self,
        project: Project,
        *,
        last_action: str,
        last_message: str,
        last_message_severity: Severity,
        last_source_name: Optional[str] = None,
        defaults_applied: tuple[str, ...] = (),
        import_schema_version_seen: Optional[str] = None,
        validation: Optional[ValidationResult] = None,
    ) -> None:
        """Store *project*, recompute the hash/revision and publish the new state."""
        self._project = project
        new_hash = project_hash(project)
        revision = self._state.project_revision + 1
        self._publish(
            has_project=True,
            project_revision=revision,
            current_project_hash=new_hash,
            schema_version=_schema_version_of(project),
            last_action=last_action,
            last_message=last_message,
            last_message_severity=last_message_severity,
            last_source_name=last_source_name,
            defaults_applied=defaults_applied,
            import_schema_version_seen=import_schema_version_seen,
            last_export_filename=None,
            last_export_path=None,
            last_export_used_browser=False,
        )
        if validation is not None:
            self._validation = validation
        self._recompute_modification_flag()

    def _set_hash_and_revision(self, project: Project) -> None:
        """Recompute hash-dependent state after an in-place modification."""
        new_hash = project_hash(project)
        self._publish(
            has_project=True,
            current_project_hash=new_hash,
            project_revision=self._state.project_revision + 1,
            schema_version=_schema_version_of(project),
        )
        self._recompute_modification_flag()

    def _recompute_modification_flag(self) -> None:
        current = self._state.current_project_hash
        if self._last_validated_hash is None:
            modified = self._validation is not None and current != self._last_validated_hash
        else:
            modified = current != self._last_validated_hash
        if modified != self._state.modified_since_validation:
            self._publish(modified_since_validation=modified)

    # ------------------------------------------------------------------
    # validation
    # ------------------------------------------------------------------
    def validate_project(self) -> ValidationResult:
        """Validate the current project and record the validated hash.

        The in-memory project is validated through its own canonical
        serialization, so the audit result describes exactly what will be
        exported (and not a more forgiving in-memory view).
        """
        if self._project is None:
            result = ValidationResult.from_diagnostics(
                [_no_project_diagnostic("validate")]
            )
            self._validation = result
            self._last_validated_hash = None
            self._assurance_scope = None
            self._publish(
                validation_status=result.status.value,
                assurance_scope=None,
                last_action="validate",
                last_message=result.summary_text(),
                last_message_severity=Severity.ERROR,
            )
            return result

        document = to_normalized_dict(self._project)
        outcome: ValidationOutcome = validate_document(document, source_name="<in-memory project>")
        result = outcome.result
        self._validation = result
        self._assurance_scope = result.scope
        self._last_validated_hash = self._state.current_project_hash
        self._publish(
            validation_status=result.status.value,
            assurance_scope=result.scope.value if result.scope is not None else None,
            last_validated_hash=self._last_validated_hash,
            defaults_applied=outcome.defaults_applied,
            last_action="validate",
            last_message=f"Validation complete: {result.summary_with_scope()}",
            last_message_severity=_severity_for_status(result),
        )
        self._recompute_modification_flag()
        return result

    # ------------------------------------------------------------------
    # import
    # ------------------------------------------------------------------
    def import_json_text(self, text: str, *, source_name: str = "<text>") -> ValidationResult:
        """Import a project from JSON text."""
        return self._apply_import(import_project_from_text(text, source_name=source_name))

    def import_json_bytes(self, raw: bytes, *, source_name: str = "<bytes>") -> ValidationResult:
        """Import a project from UTF-8 encoded JSON bytes."""
        return self._apply_import(import_project_from_bytes(raw, source_name=source_name))

    def import_json_data(self, data: Any, *, source_name: str = "<data>") -> ValidationResult:
        """Import a project from already-parsed JSON data."""
        return self._apply_import(import_project_from_data(data, source_name=source_name))

    def import_json_file(self, source: FileSource, *, source_name: Optional[str] = None) -> ValidationResult:
        """Import a project from a path or file-like object."""
        return self._apply_import(import_project_from_file(source, source_name=source_name))

    def import_json_upload(self, uploaded: Any, *, source_name: Optional[str] = None) -> ValidationResult:
        """Import a project from an ``ipywidgets.FileUpload.value`` mapping."""
        return self._apply_import(import_project_from_uploaded(uploaded, source_name=source_name))

    def _apply_import(self, outcome: ImportOutcome) -> ValidationResult:
        """Store a successful import; keep the current project when it fails."""
        self._last_import = outcome
        result = outcome.validation

        if outcome.project is None:
            # Unusable document: the current project is deliberately preserved.
            self._validation = result
            self._assurance_scope = result.scope
            self._publish(
                validation_status=result.status.value,
                assurance_scope=result.scope.value if result.scope is not None else None,
                last_action="import_failed",
                last_message=(
                    f"Import of {outcome.source_name} failed: {result.summary_text()}. "
                    "The current project was kept unchanged."
                ),
                last_message_severity=Severity.ERROR,
                last_source_name=outcome.source_name,
                import_schema_version_seen=outcome.schema_version_seen,
            )
            return result

        project = outcome.project
        validation = result
        severity = _severity_for_status(validation)
        name = project.project.name
        if validation.has_errors():
            message = (
                f"Imported data for '{name}' from {outcome.source_name}, but the project is "
                f"INVALID: {validation.summary_text()}. Valid content was preserved; see the "
                "Validation & Audit page."
            )
        else:
            message = (
                f"Imported '{name}' from {outcome.source_name}: {validation.summary_text()}."
            )
        self._replace_project(
            project,
            last_action="import",
            last_message=message,
            last_message_severity=severity,
            last_source_name=outcome.source_name,
            defaults_applied=outcome.defaults_applied,
            import_schema_version_seen=outcome.schema_version_seen,
            validation=validation,
        )
        # An import is validated against exactly the imported content.
        self._last_validated_hash = self._state.current_project_hash
        self._assurance_scope = validation.scope
        self._publish(
            last_validated_hash=self._last_validated_hash,
            validation_status=validation.status.value,
            assurance_scope=validation.scope.value if validation.scope is not None else None,
        )
        self._recompute_modification_flag()
        return validation

    # ------------------------------------------------------------------
    # editing
    # ------------------------------------------------------------------
    def update_metadata(self, **changes: Any) -> str:
        """Apply editable metadata/reference changes; returns a status message.

        Only the fields in :data:`EDITABLE_METADATA_FIELDS` (plus the two status
        enumerations) are accepted. Nothing is written when the value is
        unchanged, so a no-op save does not invalidate the current validation.
        """
        if self._project is None:
            message = "No project is loaded - create or import a project first."
            self._publish(
                last_action="edit_rejected", last_message=message, last_message_severity=Severity.WARNING
            )
            return message

        unknown = [key for key in changes if key not in _editable_field_names()]
        if unknown:
            message = f"Ignored unknown/uneditable field(s): {', '.join(sorted(unknown))}."
            self._publish(
                last_action="edit_rejected", last_message=message, last_message_severity=Severity.WARNING
            )
            return message

        applied: list[str] = []
        problems: list[str] = []
        project = self._project

        for field_name, value in changes.items():
            target = _field_owner(field_name)
            section = project.project if target == "project" else project.reference_system
            prepared, problem = _prepare_value(field_name, value)
            if problem is not None:
                problems.append(problem)
                continue
            if _same_value(getattr(section, field_name), prepared):
                continue
            try:
                setattr(section, field_name, prepared)
            except ValidationError as exc:
                problems.append(f"{field_name}: {exc.errors()[0].get('msg', 'invalid value')}")
                continue
            applied.append(field_name)

        if applied:
            project.project.modified_utc = utc_now_iso()
            self._set_hash_and_revision(project)

        message = self._compose_edit_message(applied, problems)
        severity = Severity.INFO if not problems else Severity.WARNING
        self._publish(last_action="edit", last_message=message, last_message_severity=severity)
        return message

    def _compose_edit_message(self, applied: list[str], problems: list[str]) -> str:
        """Build the user-facing status text for an edit attempt."""
        parts: list[str] = []
        if applied:
            parts.append("Updated " + ", ".join(applied) + ".")
            if self.modified_since_validation:
                parts.append("Project content changed - validate again before relying on results.")
        else:
            parts.append("No project fields changed.")
        if problems:
            parts.append("Not applied: " + "; ".join(problems) + ".")
        return " ".join(parts)

    def reset_metadata_to_template(self) -> str:
        """Reset editable metadata fields to the template defaults."""
        if self._project is None:
            return "No project is loaded."
        defaults = {
            "id": self._project.project.id,
            "name": self._project.project.name,
            "description": "",
            "chainage_origin_name": "Origin",
            "chainage_end_name": "Terminus",
            "chainage_start_km": 0.0,
            "chainage_end_km": 100.0,
        }
        return self.update_metadata(**defaults)

    # ------------------------------------------------------------------
    # direction selection (application state only)
    # ------------------------------------------------------------------
    def report_ui_message(
        self, message: str, *, severity: Severity = Severity.INFO
    ) -> None:
        """Publish a UI message in the status line (Phase 3).

        Widgets report what they did here instead of printing or logging.  The
        message is application state only: no project value, validation result or
        hash is touched.
        """
        self._publish(
            last_action="ui_message",
            last_message=str(message),
            last_message_severity=severity,
        )

    def set_direction(self, direction: Union[Direction, str]) -> ControllerState:
        """Select FORWARD or REVERSE for the application/run.

        This changes *application state only*: the stored project document -
        including all infrastructure containers - is not read or modified, so
        the canonical project hash is unaffected.
        """
        try:
            candidate = direction if isinstance(direction, Direction) else Direction(str(direction).strip().upper())
        except ValueError:
            message = (
                f"Direction {direction!r} is not selectable in Phase 1; "
                f"choose {[d.value for d in SELECTABLE_DIRECTIONS]}."
            )
            self._publish(
                last_action="direction_rejected",
                last_message=message,
                last_message_severity=Severity.WARNING,
            )
            return self._state

        if candidate not in SELECTABLE_DIRECTIONS:
            message = (
                f"Direction {candidate.value} exists in the schema but is not selectable in "
                f"Phase 1 (reserved for a later phase)."
            )
            self._publish(
                last_action="direction_rejected",
                last_message=message,
                last_message_severity=Severity.WARNING,
            )
            return self._state

        if candidate is self._state.direction:
            self._publish(
                last_action="direction",
                last_message=f"Direction already set to {candidate.value} - project data unchanged.",
                last_message_severity=Severity.INFO,
            )
            return self._state

        self._publish(
            direction=candidate,
            direction_changed_utc=utc_now_iso(),
            last_action="direction",
            last_message=(
                f"Direction set to {candidate.value}. Application selection only - stored "
                "project data and the project hash are unchanged."
            ),
            last_message_severity=Severity.INFO,
        )
        return self._state

    def toggle_direction(self) -> ControllerState:
        """Switch between FORWARD and REVERSE."""
        target = Direction.REVERSE if self._state.direction is Direction.FORWARD else Direction.FORWARD
        return self.set_direction(target)

    # ------------------------------------------------------------------
    # export
    # ------------------------------------------------------------------
    def export_json(
        self,
        *,
        download: Optional[bool] = None,
        directory: Optional[Union[str, Path]] = None,
        embed_export_metadata: bool = False,
    ) -> Optional[ExportOutcome]:
        """Export the current project; returns ``None`` when no project is loaded.

        An uncommitted draft that failed validation blocks the export
        (``APP-EDIT-002``): the exported document must never be an unreviewed
        mixture of committed and staged data.
        """
        if self._project is None:
            self._publish(
                last_action="export_rejected",
                last_message="No project is loaded - nothing to export.",
                last_message_severity=Severity.WARNING,
            )
            return None
        if self.draft_blocks_export:
            self._publish(
                last_action="export_rejected",
                last_message=(
                    "Export blocked: the staged draft is INVALID and must be corrected or "
                    "discarded before the project can be exported (APP-EDIT-002)."
                ),
                last_message_severity=Severity.ERROR,
            )
            return None

        outcome = export_project(
            self._project,
            download=self._download_on_export if download is None else download,
            directory=self._export_directory if directory is None else directory,
            embed_export_metadata=embed_export_metadata,
        )
        delivery = (
            "browser download started" if outcome.browser_download_used else "written to the file system"
        )
        path_note = f" ({outcome.written_path})" if outcome.written_path else ""
        self._publish(
            last_action="export",
            last_message=(
                f"Exported '{outcome.filename}' ({outcome.size_bytes} bytes) - {delivery}{path_note}."
            ),
            last_message_severity=Severity.INFO,
            last_export_filename=outcome.filename,
            last_export_path=outcome.written_path,
            last_export_used_browser=outcome.browser_download_used,
        )
        return outcome

    # ------------------------------------------------------------------
    # draft mechanism (APP-EDIT-002)
    # ------------------------------------------------------------------
    def stage_draft(self, document: Any, *, description: str = "") -> ValidationResult:
        """Validate a *candidate* document without touching the current project.

        A draft is a proposed future state of the project (an edited document).
        It is validated as data and reported; it is **not** applied to the
        project until :meth:`commit_draft` succeeds. Widget values are never
        project data - the document is the only input, and it is parsed with
        ``json``-safe data semantics like any import.
        """
        outcome = validate_document(document, source_name=description or "<draft>")
        self._draft_document = document if isinstance(document, dict) else None
        self._draft_outcome = outcome
        self._draft_description = description
        result = outcome.result
        self._publish(
            draft_pending=self._draft_document is not None,
            draft_description=description,
            draft_status=result.status.value,
            draft_blocks_export=result.has_errors(),
            last_action="stage_draft",
            last_message=(
                f"Draft '{description or 'untitled'}' validated: {result.summary_with_scope()} - "
                + (
                    "the draft has errors and blocks export until it is corrected or discarded."
                    if result.has_errors()
                    else "the draft is valid and can be committed."
                )
            ),
            last_message_severity=Severity.ERROR if result.has_errors() else Severity.INFO,
        )
        return result

    def commit_draft(self) -> ValidationResult:
        """Apply the staged draft to the project when it validated without errors.

        An invalid (or missing) draft is rejected with ``APP-EDIT-002``; the
        current project, its hash and its validated revision stay untouched.
        """
        if self._draft_outcome is None:
            return self._reject_draft(
                "No draft is staged - stage a draft document before committing."
            )
        if self._draft_outcome.result.has_errors() or self._draft_outcome.project is None:
            codes_of_interest = ", ".join(
                diagnostic.code for diagnostic in self._draft_outcome.result.diagnostics[:5]
            )
            return self._reject_draft(
                "The staged draft is rejected by validation and was not applied "
                f"(first diagnostics: {codes_of_interest or 'none'}).",
                diagnostic_codes=codes_of_interest,
            )
        project = self._draft_outcome.project
        result = self._draft_outcome.result
        self._clear_draft(publish=False)
        self._replace_project(
            project,
            last_action="commit_draft",
            last_message=(
                f"Draft '{self._draft_description or 'untitled'}' committed: {result.summary_with_scope()}."
            ),
            last_message_severity=Severity.INFO,
            validation=result,
            last_source_name=self._draft_description or None,
        )
        self._last_validated_hash = self._state.current_project_hash
        self._assurance_scope = result.scope
        self._publish(
            assurance_scope=result.scope.value if result.scope is not None else None,
            validation_status=result.status.value,
        )
        self._recompute_modification_flag()
        return result

    def discard_draft(self) -> None:
        """Discard the staged draft (the project is never modified by a draft)."""
        had_draft = self._draft_document is not None
        self._clear_draft(publish=False)
        self._publish(
            last_action="discard_draft",
            last_message=(
                "Staged draft discarded; the loaded project is unchanged."
                if had_draft
                else "No draft was staged."
            ),
            last_message_severity=Severity.INFO,
        )

    def _clear_draft(self, *, publish: bool = True) -> None:
        """Drop the staged draft from memory."""
        self._draft_document = None
        self._draft_outcome = None
        self._draft_description = ""
        if publish:
            self._publish(
                draft_pending=False, draft_description="", draft_status=None, draft_blocks_export=False
            )

    def _reject_draft(self, message: str, *, diagnostic_codes: str = "") -> ValidationResult:
        """Publish an APP-EDIT-002 rejection and return it as a result."""
        diagnostic = Diagnostic(
            code=codes.APP_EDIT_002,
            severity=Severity.ERROR,
            category=DiagnosticCategory.PROJECT,
            message=message,
            context={
                "draft_description": self._draft_description,
                "draft_status": self._state.draft_status,
                "diagnostic_codes": [item for item in diagnostic_codes.split(", ") if item],
            },
            suggested_action=(
                "Correct the draft and re-stage it, or discard the draft to continue with the "
                "currently loaded project."
            ),
        )
        result = ValidationResult.from_diagnostics(
            [diagnostic], scope=self._assurance_scope
        )
        self._publish(
            last_action="commit_draft_rejected",
            last_message=message,
            last_message_severity=Severity.ERROR,
        )
        return result

    # ------------------------------------------------------------------
    # Phase-2 reporting helpers for the UI (read-only)
    # ------------------------------------------------------------------
    def infrastructure_rows(self) -> list[tuple[str, str]]:
        """Return layer-level rows for the Infrastructure page."""
        compiled = self.compiled_infrastructure
        if compiled is None:
            return []
        rows: list[tuple[str, str]] = [
            ("Infrastructure layers", str(len(compiled.layers))),
            (
                "Assurance scope",
                compiled.scope.value,
            ),
            ("Registered engineering objects", str(compiled.registry.size())),
            ("Preserved Phase-1 opaque records", str(compiled.legacy_record_count())),
            (
                "Typed catalogues present",
                ", ".join(compiled.present_catalogue_keys()) or "(none)",
            ),
        ]
        for layer in compiled.layers:
            rows.append(
                (
                    f"Layer {layer.layer_id}",
                    f"{layer.name or '(unnamed)'} - physical_mode "
                    f"{'PHYSICAL' if layer.declared_physical else 'LEGACY'}, "
                    f"{layer.typed_entry_count()} typed object(s)",
                )
            )
        return rows

    def typed_inventory_rows(self) -> list[tuple[str, int]]:
        """Return ``(catalogue label, typed object count)`` rows (Phase 2)."""
        compiled = self.compiled_infrastructure
        if compiled is None or not compiled.physical:
            return []
        return compiled.inventory_rows()

    def registry_rows(self) -> list[tuple[str, str]]:
        """Return registry summary rows (object type -> count)."""
        compiled = self.compiled_infrastructure
        if compiled is None:
            return []
        return sorted((key, str(value)) for key, value in compiled.registry.type_counts().items())

    def station_rows(self) -> list[tuple[str, str, str, str, str]]:
        """Return station rows: id, name, type, reference chainage, platforms."""
        compiled = self.compiled_infrastructure
        if compiled is None or not compiled.physical:
            return []
        rows: list[tuple[str, str, str, str, str]] = []
        for station in compiled.catalogue("stations"):
            rows.append(
                (
                    station.id,
                    station.name or "",
                    station.type.value,
                    f"{station.reference_chainage_km:g} km",
                    str(len(station.platform_ids)),
                )
            )
        return rows

    def platform_rows(self) -> list[tuple[str, str, str, str, str, str]]:
        """Return platform rows: id, station, track, usable start, end, length."""
        compiled = self.compiled_infrastructure
        if compiled is None or not compiled.physical:
            return []
        rows: list[tuple[str, str, str, str, str, str]] = []
        for platform in compiled.catalogue("platforms"):
            rows.append(
                (
                    platform.id,
                    platform.station_id,
                    platform.track_id,
                    f"{platform.usable_start_m:g} m",
                    f"{platform.usable_end_m:g} m",
                    f"{platform.usable_length_m:g} m",
                )
            )
        return rows

    def stopping_mark_rows(self) -> list[tuple[str, str, str, str, str]]:
        """Return stopping-mark rows: id, platform, track, position, direction."""
        compiled = self.compiled_infrastructure
        if compiled is None or not compiled.physical:
            return []
        rows: list[tuple[str, str, str, str, str]] = []
        for mark in compiled.catalogue("stopping_marks"):
            rows.append(
                (
                    mark.id,
                    mark.platform_id,
                    mark.track_id,
                    f"{mark.position_m:g} m",
                    mark.direction.value if hasattr(mark.direction, "value") else str(mark.direction),
                )
            )
        return rows

    def node_rows(self) -> list[tuple[str, str, str, str, str]]:
        """Return topology-node rows: id, type, chainage, station, degree."""
        compiled = self.compiled_infrastructure
        if compiled is None or not compiled.physical:
            return []
        topology = compiled.topology()
        rows: list[tuple[str, str, str, str, str]] = []
        for node in compiled.catalogue("nodes"):
            node_id = node.id
            degree = len(topology.incident_edges(node_id))
            rows.append(
                (
                    node_id,
                    node.type.value,
                    f"{node.chainage_km:g} km",
                    node.station_id or "-",
                    str(degree),
                )
            )
        return rows

    def edge_rows(self) -> list[tuple[str, str, str, str, str, str]]:
        """Return track-edge rows: id, from, to, length, group, chainage map."""
        compiled = self.compiled_infrastructure
        if compiled is None or not compiled.physical:
            return []
        rows: list[tuple[str, str, str, str, str, str]] = []
        for track in compiled.catalogue("tracks"):
            chainage_map = track.chainage_map
            rows.append(
                (
                    track.id,
                    track.from_node,
                    track.to_node,
                    f"{track.length_m:g} m",
                    track.track_group_id or "-",
                    f"{chainage_map.mode.value} {chainage_map.start_km:g}-{chainage_map.end_km:g} km",
                )
            )
        return rows

    def topology_summary_rows(self) -> list[tuple[str, str]]:
        """Return the topology inspector summary (components, isolated nodes...)."""
        compiled = self.compiled_infrastructure
        if compiled is None or not compiled.physical:
            return []
        topology = compiled.topology()
        report = topology.connectivity()
        isolated = report.isolated_nodes
        components = report.components
        return [
            ("Nodes", str(len(compiled.catalogue("nodes")))),
            ("Track edges", str(len(compiled.catalogue("tracks")))),
            ("Connected components", str(len(components))),
            (
                "Largest component",
                str(max((len(component) for component in components), default=0)),
            ),
            ("Isolated nodes", ", ".join(isolated) if isolated else "(none)"),
            ("Track groups", str(len(compiled.catalogue("track_groups")))),
        ]

    def static_footprint_rows(self, train_length_m: float) -> list[tuple[str, str, str, str]]:
        """Return a static footprint evaluation for every stopping marker.

        Static geometry only: no time, speed, acceleration, braking or occupation
        is computed anywhere. ``train_length_m`` is an evaluation input supplied
        by the caller - it is never stored in the project document.
        """
        compiled = self.compiled_infrastructure
        if compiled is None or not compiled.physical:
            return []
        tracks = {track.id: track for track in compiled.catalogue("tracks")}
        platforms = {platform.id: platform for platform in compiled.catalogue("platforms")}
        rows: list[tuple[str, str, str, str]] = []
        for mark in compiled.catalogue("stopping_marks"):
            track = tracks.get(mark.track_id)
            if track is None:
                continue
            platform = platforms.get(mark.platform_id)
            traversal = traversal_for_direction(mark.direction)
            footprint = compute_static_footprint(
                track, mark, float(train_length_m), traversal, platform=platform
            )
            rows.append(
                (
                    mark.id,
                    f"{footprint.front_position_m:g} / {footprint.rear_position_m:g} m",
                    f"{footprint.critical_boundary_m:g} m" if footprint.critical_boundary_m is not None else "-",
                    (
                        f"fits ({footprint.rear_clearance_m:g} m rear clearance)"
                        if footprint.fit_in_usable_platform
                        else f"rear infringement {footprint.rear_infringement_m:g} m"
                    ),
                )
            )
        return rows

    # ------------------------------------------------------------------
    # reporting helpers for the UI
    # ------------------------------------------------------------------
    def summary_rows(self) -> list[tuple[str, str]]:
        """Return the compact project summary shown on the Project page."""
        if self._project is None:
            return []
        reference = self._project.reference_system
        meta = self._project.project
        return [
            ("Project ID", meta.id or "(not set)"),
            ("Project name", meta.name or "(not set)"),
            ("Project type", meta.project_type or "(not set)"),
            ("Data status", _enum_text(meta.data_status)),
            ("Engineering status", _enum_text(meta.engineering_status)),
            ("Alignment ID", reference.alignment_id or "(not set)"),
            (
                "Chainage range",
                f"{reference.chainage_start_km} - {reference.chainage_end_km} "
                f"{self._project.display_units.chainage or 'km'}",
            ),
            ("Created (UTC)", meta.created_utc or "(not set)"),
            ("Modified (UTC)", meta.modified_utc or "(not set)"),
            ("Schema version", self._state.schema_version or DEFAULT_PROJECT_SCHEMA_VERSION),
            ("Application version", APP_VERSION),
        ]

    def object_count_rows(self) -> list[tuple[str, int]]:
        """Return the object counts of the canonical containers."""
        return list(self._project.summary_counts().items()) if self._project else []

    def state_rows(self) -> list[tuple[str, str]]:
        """Return the audit rows shared by the header/footer and audit page."""
        state = self._state
        return [
            ("Application version", state.app_version),
            ("Project schema version", state.schema_version or f"(none - supported: {DEFAULT_PROJECT_SCHEMA_VERSION})"),
            ("Validation status", state.validation_status or "(not validated yet)"),
            ("Validation freshness", state.freshness_text),
            ("Current project hash", state.current_project_hash or "(no project)"),
            ("Last validated hash", state.last_validated_hash or "(not validated yet)"),
            ("Direction (application selection)", state.direction.value),
            ("Direction changed (UTC)", state.direction_changed_utc or "(not changed this session)"),
            ("Project revision", str(state.project_revision)),
            ("Last action", state.last_action or "(none)"),
            ("Last source", state.last_source_name or "(none)"),
            ("Sections defaulted on import", ", ".join(state.defaults_applied) or "(none)"),
        ]


# ---------------------------------------------------------------------------
# module-level helpers
# ---------------------------------------------------------------------------
def _editable_field_names() -> set[str]:
    """Return the set of field names :meth:`ProjectController.update_metadata` accepts."""
    return {name for name, _ in EDITABLE_METADATA_FIELDS} | set(_ENUM_FIELDS)


def _field_owner(field_name: str) -> str:
    """Return the section ('project' or 'reference_system') owning *field_name*."""
    for name, owner in EDITABLE_METADATA_FIELDS:
        if name == field_name:
            return owner
    if field_name in _ENUM_FIELDS:
        return "project"
    raise KeyError(field_name)


def _prepare_value(field_name: str, value: Any) -> tuple[Any, Optional[str]]:
    """Coerce a UI-supplied value; returns ``(value, problem_message)``."""
    if field_name in _NUMBER_FIELDS:
        if value is None or (isinstance(value, str) and not value.strip()):
            return None, f"{field_name} cannot be empty - enter a number"
        if isinstance(value, bool):
            return None, f"{field_name} must be a number"
        if isinstance(value, (int, float)):
            return value, None
        if isinstance(value, str):
            try:
                number = float(value.strip().replace(",", "."))
            except ValueError:
                return None, f"{field_name} must be a number (got {value!r})"
            return (int(number) if number.is_integer() else number), None
        return None, f"{field_name} must be a number (got {type(value).__name__})"

    if field_name in _ENUM_FIELDS:
        enum_type = _ENUM_FIELDS[field_name]
        if value is None or value == "":
            return None, None
        try:
            return enum_type(str(value).strip().upper()), None
        except ValueError:
            allowed = [member.value for member in enum_type]
            return None, f"{field_name} must be one of {allowed}"

    if value is None:
        return None, None
    text = str(value).strip()
    return (text if text else None), None


def _same_value(current: Any, prepared: Any) -> bool:
    """Return ``True`` when writing *prepared* would not change the stored value.

    Numbers are compared type-sensitively: writing ``0`` where ``0.0`` is stored
    is a real edit (the exported document keeps the JSON-native type the user
    supplied), while re-saving an identical value stays a no-op so that a
    validation is not invalidated by pressing "Save metadata" twice.
    """
    if isinstance(current, bool) or isinstance(prepared, bool):
        return type(current) is type(prepared) and current == prepared
    if isinstance(current, (int, float)) and isinstance(prepared, (int, float)):
        return type(current) is type(prepared) and current == prepared
    return current == prepared


def _enum_text(value: Any) -> str:
    """Render an optional enum value for display."""
    if value is None:
        return "(not set)"
    return getattr(value, "value", str(value))


def _schema_version_of(project: Optional[Project]) -> Optional[str]:
    """Return the schema version of *project* (defaults to the supported one)."""
    if project is None:
        return None
    return project.schema_version or DEFAULT_PROJECT_SCHEMA_VERSION


def _severity_for_status(result: ValidationResult) -> Severity:
    """Map a validation status onto the severity used for status messages."""
    if result.has_errors():
        return Severity.ERROR
    if result.has_warnings():
        return Severity.WARNING
    return Severity.INFO


def _no_project_diagnostic(action: str) -> Diagnostic:
    """Build the diagnostic used when an action requires a loaded project."""
    from ..models.enums import DiagnosticCategory

    return Diagnostic(
        code="APP-CTRL-001",
        severity=Severity.ERROR,
        category=DiagnosticCategory.PROJECT,
        message=f"No project is loaded - cannot {action}.",
        suggested_action="Create a new project or import a project JSON file.",
    )
