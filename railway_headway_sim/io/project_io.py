"""Project JSON import/export and canonical hashing.

Security posture (Phase 1 and later): uploaded JSON is treated strictly as
*data*. Only :func:`json.loads` is used. There is no ``eval``, ``exec``,
``pickle``, ``yaml.load`` or dynamic import anywhere in the import path, and no
code is ever derived from project content.

Roundtrip contract
------------------
``Project -> export -> import -> export`` produces the same normalized document
(and therefore the same bytes and the same canonical hash). Import does **not**
touch ``created_utc``/``modified_utc``; the application layer only writes those
when the user actually edits metadata.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Union

from ..constants import (
    EXPORT_METADATA_KEY,
    FALLBACK_EXPORT_STEM,
    SAFE_FILENAME_CHARS,
    SCHEMA_VERSION_FIELD,
    TOP_LEVEL_SECTIONS,
)
from ..models.diagnostics import Diagnostic, ValidationResult
from ..models.enums import DiagnosticCategory, Severity
from ..models.project import Project
from ..validation import ValidationOutcome, codes, validate_document, validate_json_text
from ..version import APP_NAME, APP_VERSION, DEFAULT_PROJECT_SCHEMA_VERSION

#: Number of decimal places kept when normalizing floats for hashing. This is a
#: hash-normalization tolerance only; exported JSON keeps full precision.
HASH_FLOAT_DECIMALS = 9

#: Characters used when building an export file name from a project name/id.
_FILENAME_ALLOWED = set(SAFE_FILENAME_CHARS)
_MAX_FILENAME_STEM = 60

FileSource = Union[str, Path, bytes, bytearray, memoryview]


@dataclass(frozen=True)
class ImportOutcome:
    """Everything the controller needs to know about one import attempt."""

    project: Optional[Project]
    validation: ValidationResult
    defaults_applied: tuple[str, ...] = ()
    schema_version_seen: Optional[str] = None
    source_name: str = ""

    @property
    def ok(self) -> bool:
        """Return ``True`` when a project model was built (even if INVALID)."""
        return self.project is not None

    @property
    def status_text(self) -> str:
        """Return a one-line human status for the import attempt."""
        if self.project is None:
            return f"Import failed: {self.validation.summary_text()}"
        return f"Imported '{self.project.project.name}' from {self.source_name}: {self.validation.summary_text()}"


@dataclass(frozen=True)
class ExportOutcome:
    """Result of an export request (file bytes + delivery information)."""

    filename: str
    text: str
    data: bytes
    written_path: Optional[str] = None
    browser_download_used: bool = False

    @property
    def size_bytes(self) -> int:
        """Return the byte size of the exported document."""
        return len(self.data)


# ---------------------------------------------------------------------------
# import
# ---------------------------------------------------------------------------
def import_project_from_text(text: str, *, source_name: str = "<text>") -> ImportOutcome:
    """Validate JSON text and build a project (never executes the content)."""
    return _to_import_outcome(validate_json_text(text, source_name=source_name))


def import_project_from_data(data: Any, *, source_name: str = "<data>") -> ImportOutcome:
    """Validate already-parsed JSON data (e.g. from ``json.loads``)."""
    return _to_import_outcome(validate_document(data, source_name=source_name))


def import_project_from_bytes(raw: bytes, *, source_name: str = "<bytes>") -> ImportOutcome:
    """Decode UTF-8 (with optional BOM) and import the resulting JSON text."""
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        return ImportOutcome(
            project=None,
            validation=_single_error(
                codes.VAL_SCHEMA_005,
                f"The uploaded data could not be decoded as UTF-8 text: {exc.reason} at byte {exc.start}.",
                context={"source": source_name, "byte_offset": exc.start},
                suggested_action="Save the project file as UTF-8 encoded JSON and upload it again.",
            ),
            source_name=source_name,
        )
    return import_project_from_text(text, source_name=source_name)


def import_project_from_file(source: FileSource, *, source_name: Optional[str] = None) -> ImportOutcome:
    """Import a project from a file path or a file-like/binary object."""
    if isinstance(source, (str, Path)):
        path = Path(source)
        name = source_name or path.name
        try:
            raw = path.read_bytes()
        except OSError as exc:
            return _unreadable_source_outcome(name, str(exc))
        return import_project_from_bytes(raw, source_name=name)

    if isinstance(source, (bytes, bytearray, memoryview)):
        return import_project_from_bytes(bytes(source), source_name=source_name or "<bytes>")

    read = getattr(source, "read", None)
    if callable(read):
        payload = read()
        name = source_name or str(getattr(source, "name", "<file>"))
        if isinstance(payload, str):
            return import_project_from_text(payload, source_name=name)
        if isinstance(payload, (bytes, bytearray, memoryview)):
            return import_project_from_bytes(bytes(payload), source_name=name)
        return _unreadable_source_outcome(name, f"unsupported payload type {type(payload).__name__}")

    return _unreadable_source_outcome(str(source), "unsupported source type")


def normalise_upload_payload(uploaded: Any) -> tuple[str, Any]:
    """Normalize any ``ipywidgets.FileUpload.value`` variant to ``(filename, content)``.

    Supported shapes:

    * ipywidgets >= 8: ``( {'name': ..., 'content': memoryview, ...}, ... )``
    * legacy mapping: ``{'filename.json': {'content': bytes, ...}, ...}``
    * a single entry mapping with a ``content`` key

    Raises
    ------
    ValueError
        When *uploaded* is empty or has no usable content. This is a caller
        precondition (the UI checks for an empty selection first and reports it
        as ``APP-CTRL-002``); it is not a data-validation problem.
    """
    entry: Optional[dict[str, Any]] = None
    filename = "<uploaded>"

    if isinstance(uploaded, (list, tuple)):
        entries = [item for item in uploaded if isinstance(item, dict)]
        if not entries:
            raise ValueError("The FileUpload value contains no file entries.")
        entry = entries[0]
        filename = str(entry.get("name") or filename)
    elif isinstance(uploaded, dict):
        if "content" in uploaded:
            entry = uploaded
            filename = str(uploaded.get("name") or filename)
        else:
            for key, payload in uploaded.items():
                if isinstance(payload, dict) and "content" in payload:
                    filename = str(key)
                    entry = payload
                    break
            if entry is None:
                raise ValueError("The FileUpload value contains no entry with a 'content' key.")
    else:
        raise ValueError(
            "Unsupported FileUpload value type "
            f"{type(uploaded).__name__}; expected a tuple of entries or a mapping."
        )

    if entry is None or "content" not in entry:
        raise ValueError("The uploaded entry has no 'content' key.")
    return filename, entry["content"]


def import_project_from_uploaded(
    uploaded: Any, *, source_name: Optional[str] = None
) -> ImportOutcome:
    """Import from an ``ipywidgets.FileUpload.value`` payload (any supported shape)."""
    if uploaded is None or (isinstance(uploaded, (list, tuple, dict)) and len(uploaded) == 0):
        return ImportOutcome(
            project=None,
            validation=_single_error(
                codes.APP_CTRL_002,
                "No JSON file was selected in the import widget.",
                suggested_action="Choose a .json project file, then press Import JSON.",
            ),
            source_name="<no file selected>",
        )
    filename, content = normalise_upload_payload(uploaded)
    name = source_name or filename
    if isinstance(content, str):
        return import_project_from_text(content, source_name=name)
    return import_project_from_bytes(bytes(content), source_name=name)


def _to_import_outcome(outcome: ValidationOutcome) -> ImportOutcome:
    """Convert a validation outcome into an import outcome."""
    return ImportOutcome(
        project=outcome.project,
        validation=outcome.result,
        defaults_applied=outcome.defaults_applied,
        schema_version_seen=outcome.schema_version_seen,
        source_name=outcome.source_name,
    )


def _single_error(
    code: str,
    message: str,
    *,
    context: Optional[dict[str, Any]] = None,
    suggested_action: Optional[str] = None,
    category: DiagnosticCategory = DiagnosticCategory.SCHEMA,
) -> ValidationResult:
    """Build a one-diagnostic ERROR validation result."""
    return ValidationResult.from_diagnostics(
        [
            Diagnostic(
                code=code,
                severity=Severity.ERROR,
                category=category,
                message=message,
                context=context,
                suggested_action=suggested_action,
            )
        ]
    )


def _unreadable_source_outcome(source_name: str, reason: str) -> ImportOutcome:
    """Build the import outcome used when the source cannot be read at all."""
    return ImportOutcome(
        project=None,
        validation=_single_error(
            codes.VAL_SCHEMA_001,
            f"The project source '{source_name}' could not be read: {reason}.",
            context={"source": source_name},
            suggested_action="Check that the file is a readable .json file and try again.",
        ),
        source_name=source_name,
    )


# ---------------------------------------------------------------------------
# export
# ---------------------------------------------------------------------------
def to_normalized_dict(project: Project) -> dict[str, Any]:
    """Return the canonical document of *project* in schema field order.

    * Section order follows the schema.
    * All sections are always present.
    * ``schema_version`` is always written.
    * Unknown (forward-compatible) keys are preserved, in their original order,
      after the known sections.
    * Numbers are exported exactly as stored - no presentation rounding.
    """
    dumped = project.model_dump(mode="json")
    ordered: dict[str, Any] = {}
    ordered[SCHEMA_VERSION_FIELD] = dumped.get(SCHEMA_VERSION_FIELD, DEFAULT_PROJECT_SCHEMA_VERSION)
    for section in TOP_LEVEL_SECTIONS:
        if section == SCHEMA_VERSION_FIELD:
            continue
        if section in dumped:
            ordered[section] = dumped.pop(section)
    for key, value in dumped.items():
        ordered[key] = value
    return ordered


def export_metadata_block(exported_utc: Optional[str] = None, *, app_version: Optional[str] = None) -> dict[str, Any]:
    """Return the optional, non-canonical export metadata block.

    It is *not* written unless explicitly requested, so that import -> export
    roundtrips stay byte-stable and the canonical hash is unaffected.
    """
    from ..models.common import utc_now_iso

    return {
        "exported_utc": exported_utc or utc_now_iso(),
        "application": APP_NAME,
        "application_version": app_version or APP_VERSION,
        "schema_version": DEFAULT_PROJECT_SCHEMA_VERSION,
        "note": "Volatile export metadata - not part of the canonical project content.",
    }


def to_json_text(
    project: Project,
    *,
    indent: Optional[int] = 2,
    embed_export_metadata: bool = False,
    exported_utc: Optional[str] = None,
) -> str:
    """Serialize *project* to readable, deterministic JSON text."""
    document = to_normalized_dict(project)
    if embed_export_metadata:
        document = {EXPORT_METADATA_KEY: export_metadata_block(exported_utc), **document}
    return json.dumps(document, indent=indent, ensure_ascii=False, allow_nan=False)


def to_json_bytes(
    project: Project,
    *,
    indent: Optional[int] = 2,
    embed_export_metadata: bool = False,
    exported_utc: Optional[str] = None,
) -> bytes:
    """Serialize *project* to UTF-8 encoded JSON bytes."""
    return to_json_text(
        project,
        indent=indent,
        embed_export_metadata=embed_export_metadata,
        exported_utc=exported_utc,
    ).encode("utf-8")


def export_filename(project: Project, *, extension: str = ".json") -> str:
    """Build a useful export file name from the project name and ID.

    Example: ``demo-intercity-line_prj-4f9c1a7b2d3e.json``.
    """
    name_slug = _slugify(project.project.name or "")
    id_slug = _slugify(project.project.id or "")
    if name_slug and id_slug:
        stem = f"{name_slug}_{id_slug}"
    else:
        stem = name_slug or id_slug or FALLBACK_EXPORT_STEM
    return f"{stem[:_MAX_FILENAME_STEM]}{extension}"


def write_project_file(project: Project, path: Union[str, Path], **json_options: Any) -> Path:
    """Write the project JSON to *path* (UTF-8) and return the written path."""
    target = Path(path)
    if target.parent and not target.parent.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(to_json_bytes(project, **json_options))
    return target


def export_project(
    project: Project,
    *,
    directory: Optional[Union[str, Path]] = None,
    write_file: bool = True,
    embed_export_metadata: bool = False,
    download: bool = True,
    indent: Optional[int] = 2,
) -> ExportOutcome:
    """Export a project: build the JSON and deliver it (Colab download + file).

    The browser download uses the Colab-compatible ``google.colab.files.download``
    when running inside Colab. Outside Colab the file is still written to
    *directory* (default: the current working directory) and the outcome reports
    ``browser_download_used=False``.
    """
    text = to_json_text(project, indent=indent, embed_export_metadata=embed_export_metadata)
    data = text.encode("utf-8")
    filename = export_filename(project)
    written_path: Optional[str] = None
    if write_file:
        target_dir = Path(directory) if directory is not None else Path.cwd()
        written_path = str(write_project_file(project, target_dir / filename, indent=indent,
                                              embed_export_metadata=embed_export_metadata))
    browser_download_used = False
    if download:
        browser_download_used = download_in_colab(data, filename)
    return ExportOutcome(
        filename=filename,
        text=text,
        data=data,
        written_path=written_path,
        browser_download_used=browser_download_used,
    )


def download_in_colab(data: bytes, filename: str) -> bool:
    """Trigger a browser download inside Google Colab. Returns ``True`` on success.

    Uses ``google.colab.files`` only when available; outside Colab (or if the
    Colab API rejects the call) this returns ``False`` so the caller can report
    the on-disk location instead.
    """
    try:
        from google.colab import files as colab_files  # type: ignore[import-not-found]
    except ImportError:
        return False
    try:
        colab_files.download(data, filename)
    except Exception:  # pragma: no cover - environment dependent, reported to the user
        return False
    return True


# ---------------------------------------------------------------------------
# hashing
# ---------------------------------------------------------------------------
def _normalize_numbers(value: Any) -> Any:
    """Normalize numbers for hashing (10 and 10.0 hash identically)."""
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("Non-finite numbers cannot be part of a canonical project document.")
        if value.is_integer():
            return int(value)
        return round(value, HASH_FLOAT_DECIMALS)
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return {str(key): _normalize_numbers(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_normalize_numbers(item) for item in value]
    raise TypeError(f"Cannot hash non-JSON value of type {type(value).__name__}.")


class _NormalizingEncoder(json.JSONEncoder):
    """JSON encoder that normalizes numbers before encoding (deterministic)."""

    def iterencode(self, o: Any, _one_shot: bool = False):  # type: ignore[override]
        return super().iterencode(_normalize_numbers(o), _one_shot)


def canonical_json_text(data: Any) -> str:
    """Return the canonical form of a JSON document (sorted keys, no spaces)."""
    return json.dumps(
        data,
        sort_keys=True,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        cls=_NormalizingEncoder,
    )


def document_hash(document: Any) -> str:
    """Return the SHA-256 of the canonical form of a JSON document."""
    return hashlib.sha256(canonical_json_text(document).encode("utf-8")).hexdigest()


def project_hash(project: Project) -> str:
    """Return the deterministic SHA-256 hash of the canonical project content.

    Only canonical project data is hashed. Volatile UI-only state (selected
    direction, scroll position, last action messages) is never part of the
    project model, so it cannot change this hash.
    """
    return document_hash(to_normalized_dict(project))


def short_hash(value: Optional[str], *, length: int = 16) -> str:
    """Return a display-friendly prefix of a hash (``""`` when absent)."""
    if not value:
        return ""
    return value[:length]


def _slugify(text: str) -> str:
    """Return a file-name-safe slug of *text* (lowercase, ``-`` separated)."""
    lowered = text.strip().lower()
    slug_chars: list[str] = []
    previous_dash = False
    for char in lowered:
        if char in _FILENAME_ALLOWED and char != "-":
            slug_chars.append(char)
            previous_dash = False
        elif char in "-_" or char.isspace():
            if not previous_dash and slug_chars:
                slug_chars.append("-")
                previous_dash = True
        else:
            if not previous_dash and slug_chars:
                slug_chars.append("-")
                previous_dash = True
    return "".join(slug_chars).strip("-_")
