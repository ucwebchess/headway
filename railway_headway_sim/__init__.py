"""Railway Track Headway Simulator - Phase-1 application foundation.

Layering (dependencies point downwards only)::

    UI  ->  Application/Project controller  ->  Project model  ->  Validation/Serialization

Phase 1 provides the canonical project container, JSON import/export, structured
validation diagnostics, project hashing and the Colab application shell. It
contains **no** train simulation, railway physics, signalling, headway or
capacity calculation.

Typical programmatic use::

    from railway_headway_sim import ProjectController, launch_app

    controller = ProjectController.new_project()
    controller.update_metadata(name="My line", chainage_end_km=180.0)
    controller.validate_project()
    controller.export_json()

The interactive application lives in :mod:`railway_headway_sim.ui` (it requires
``ipywidgets``, which Google Colab provides).
"""

from __future__ import annotations

from .app.project_controller import ControllerState, ProjectController
from .constants import CONTAINER_SECTIONS, IDENTITY_FIELDS, TOP_LEVEL_SECTIONS
from .example_project import EXAMPLE_PROJECT_JSON, example_project_dict, example_project_text
from .io.project_io import (
    ExportOutcome,
    ImportOutcome,
    document_hash,
    export_filename,
    export_project,
    import_project_from_bytes,
    import_project_from_data,
    import_project_from_file,
    import_project_from_text,
    import_project_from_uploaded,
    project_hash,
    to_json_bytes,
    to_json_text,
    to_normalized_dict,
)
from .models.diagnostics import Diagnostic, ValidationResult
from .models.enums import (
    DataStatus,
    Direction,
    EngineeringStatus,
    SELECTABLE_DIRECTIONS,
    Severity,
    ValidationStatus,
)
from .models.project import Project, new_project
from .validation import (
    ValidationOutcome,
    validate_document,
    validate_in_memory_project,
    validate_json_text,
)
from .version import (
    APP_NAME,
    APP_PHASE,
    APP_VERSION,
    DEFAULT_PROJECT_SCHEMA_VERSION,
    SUPPORTED_PROJECT_SCHEMA_VERSIONS,
    get_app_version,
    get_default_schema_version,
    get_supported_schema_versions,
    is_supported_schema_version,
)

__version__ = APP_VERSION


def __getattr__(name: str):
    """Lazily expose the UI entry point (it requires ``ipywidgets``).

    ``railway_headway_sim.launch_app`` and ``railway_headway_sim.ui`` are
    resolved on first access so that the model, validation and I/O layers can be
    imported and tested in environments without widget support.
    """
    if name in {"launch_app", "ui"}:
        import importlib

        module = importlib.import_module(".ui", __name__)
        return module.launch_app if name == "launch_app" else module
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "APP_NAME",
    "APP_PHASE",
    "APP_VERSION",
    "CONTAINER_SECTIONS",
    "ControllerState",
    "DEFAULT_PROJECT_SCHEMA_VERSION",
    "DataStatus",
    "Diagnostic",
    "Direction",
    "EXAMPLE_PROJECT_JSON",
    "EngineeringStatus",
    "ExportOutcome",
    "IDENTITY_FIELDS",
    "ImportOutcome",
    "Project",
    "ProjectController",
    "SELECTABLE_DIRECTIONS",
    "SUPPORTED_PROJECT_SCHEMA_VERSIONS",
    "Severity",
    "TOP_LEVEL_SECTIONS",
    "ValidationOutcome",
    "ValidationResult",
    "ValidationStatus",
    "__version__",
    "document_hash",
    "example_project_dict",
    "example_project_text",
    "export_filename",
    "export_project",
    "get_app_version",
    "get_default_schema_version",
    "get_supported_schema_versions",
    "import_project_from_bytes",
    "import_project_from_data",
    "import_project_from_file",
    "import_project_from_text",
    "import_project_from_uploaded",
    "is_supported_schema_version",
    "launch_app",
    "new_project",
    "project_hash",
    "to_json_bytes",
    "to_json_text",
    "to_normalized_dict",
    "validate_document",
    "validate_in_memory_project",
    "validate_json_text",
]
