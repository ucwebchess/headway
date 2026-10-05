"""Shared helpers for the Phase-2 test suite (no pytest dependency)."""

from __future__ import annotations

import copy
import json
from typing import Any, Optional

from railway_headway_sim.infrastructure import grr_fixtures
from railway_headway_sim.infrastructure.compiler import CompiledInfrastructure, compile_infrastructure
from railway_headway_sim.io.project_io import import_project_from_data
from railway_headway_sim.validation import ValidationOutcome, validate_document


def grr_document() -> dict[str, Any]:
    """Return a mutable deep copy of the GRR-01 Part-A reference document."""
    return copy.deepcopy(grr_fixtures.build_grr01_document())


def frozen_document() -> dict[str, Any]:
    """Return a mutable deep copy of the frozen (pre-amendment) GRR-01 document."""
    return copy.deepcopy(grr_fixtures.frozen_document())


def layer_of(document: dict[str, Any]) -> dict[str, Any]:
    """Return the single infrastructure layer of *document*."""
    layers = document["infrastructure"]
    assert isinstance(layers, list) and len(layers) == 1, "GRR-01 has exactly one layer"
    return layers[0]


def catalogue(document: dict[str, Any], key: str) -> list[dict[str, Any]]:
    """Return one typed catalogue of the GRR-01 layer."""
    entries = layer_of(document)[key]
    assert isinstance(entries, list)
    return entries


def entry(document: dict[str, Any], key: str, object_id: str) -> dict[str, Any]:
    """Return one catalogue entry by id (fails loudly when it does not exist)."""
    for record in catalogue(document, key):
        if record["id"] == object_id:
            return record
    raise AssertionError(f"{object_id} not found in catalogue {key}")


def validate(document: Optional[dict[str, Any]] = None) -> ValidationOutcome:
    """Validate a document (GRR-01 by default) through the real validation facade."""
    return validate_document(document if document is not None else grr_document(),
                             source_name="<phase2 test>")


def compile_document(document: Optional[dict[str, Any]] = None) -> CompiledInfrastructure:
    """Compile the infrastructure of a document (GRR-01 by default)."""
    return compile_infrastructure(layer_container(document))


def layer_container(document: Optional[dict[str, Any]] = None) -> list[Any]:
    """Return the infrastructure array of a document (GRR-01 by default)."""
    return (document if document is not None else grr_document())["infrastructure"]


def load_project(document: Optional[dict[str, Any]] = None):
    """Import a document through the real import path and return the project."""
    outcome = import_project_from_data(document if document is not None else grr_document())
    assert outcome.ok and outcome.project is not None, "the fixture must import"
    return outcome.project


def codes_of(result: Any) -> tuple[str, ...]:
    """Return the diagnostic codes of a validation result, in display order."""
    return tuple(diagnostic.code for diagnostic in result.diagnostics)


def diagnostics_with_code(result: Any, code: str) -> list[Any]:
    """Return the diagnostics carrying *code*."""
    return [diagnostic for diagnostic in result.diagnostics if diagnostic.code == code]


def has_code(result: Any, code: str) -> bool:
    """Return whether *code* appears among the diagnostics."""
    return code in codes_of(result)


def roundtrip_text(document: dict[str, Any]) -> str:
    """Import and re-export a document; returns the canonical JSON text."""
    from railway_headway_sim.io.project_io import to_json_text

    return to_json_text(load_project(document))


def json_text(document: dict[str, Any]) -> str:
    """Return a document as JSON text (used to prove data-only handling)."""
    return json.dumps(document, indent=2)
