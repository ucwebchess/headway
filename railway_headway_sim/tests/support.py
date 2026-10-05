"""Shared helpers for the Phase-1 tests (no pytest dependency)."""

from __future__ import annotations

import copy
import json
from typing import Any, Iterable

from railway_headway_sim.app.project_controller import ProjectController
from railway_headway_sim.example_project import example_project_dict
from railway_headway_sim.io.project_io import to_normalized_dict
from railway_headway_sim.models.project import Project


def template_document(**project_kwargs: Any) -> dict[str, Any]:
    """Return the canonical document of a freshly created project template."""
    return to_normalized_dict(Project.new(**project_kwargs))


def example_document() -> dict[str, Any]:
    """Return a mutable deep copy of the documented example project."""
    return copy.deepcopy(example_project_dict())


def example_json_text() -> str:
    """Return the example project as JSON text."""
    return json.dumps(example_document(), indent=2)


def controller_with_example() -> ProjectController:
    """Return a controller holding the example project (imported data path)."""
    controller = ProjectController()
    controller.import_json_data(example_document(), source_name="example")
    return controller


def codes_of(result: Iterable[Any]) -> tuple[str, ...]:
    """Return the diagnostic codes of a validation result, in display order."""
    return tuple(diagnostic.code for diagnostic in result.diagnostics)


def diagnostics_with_code(result: Iterable[Any], code: str) -> list[Any]:
    """Return the diagnostics carrying *code*."""
    return [diagnostic for diagnostic in result.diagnostics if diagnostic.code == code]


def has_code(result: Iterable[Any], code: str) -> bool:
    """Return whether *code* appears among the diagnostics."""
    return code in codes_of(result)
