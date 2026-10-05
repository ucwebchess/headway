"""Single authoritative source of version information.

Two different concepts live here on purpose:

* :data:`APP_VERSION` – the application (software) version. Bumped when the
  Python code changes.
* :data:`SUPPORTED_PROJECT_SCHEMA_VERSIONS` / :data:`DEFAULT_PROJECT_SCHEMA_VERSION`
  – versions of the *project JSON document* format. Bumped only when the
  serialized project format changes.

No other module may hard-code a version string.
"""

from __future__ import annotations

APP_NAME: str = "Railway Track Headway Simulator"
APP_PHASE: str = "Phase 6B — Rolling-Stock UI"
APP_VERSION: str = "0.9.0"

#: Project JSON document schema versions this build can read and write.
#:
#: Phase 3 deliberately keeps schema version ``1.0``: the Phase-3 editors change
#: *values* inside the existing typed catalogues and never add, rename or remove a
#: stored key, so every Phase-1 and Phase-2 document validates and round-trips
#: unchanged. The editors additionally reuse the Phase-2 draft mechanism, so an
#: uncommitted edit cannot reach a document at all.
SUPPORTED_PROJECT_SCHEMA_VERSIONS: tuple[str, ...] = ("1.0",)

#: Schema version stamped onto new projects and written by the exporter.
DEFAULT_PROJECT_SCHEMA_VERSION: str = "1.0"

#: Key used for optional, non-canonical export metadata on exported documents.
EXPORT_METADATA_KEY: str = "export_metadata"


def get_app_version() -> str:
    """Return the application version string (e.g. ``"0.9.0"``)."""
    return APP_VERSION


def get_supported_schema_versions() -> tuple[str, ...]:
    """Return all project schema versions understood by this application."""
    return SUPPORTED_PROJECT_SCHEMA_VERSIONS


def get_default_schema_version() -> str:
    """Return the project schema version written for new/exported projects."""
    return DEFAULT_PROJECT_SCHEMA_VERSION


def is_supported_schema_version(version: object) -> bool:
    """Return ``True`` when *version* is a schema version this build supports."""
    return isinstance(version, str) and version in SUPPORTED_PROJECT_SCHEMA_VERSIONS
