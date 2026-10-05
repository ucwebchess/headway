"""Shared helpers for the Phase-2 validation modules.

Kept separate so that the topology and station validators can share lookup and
diagnostic-construction helpers without importing each other (no cycles).
"""

from __future__ import annotations

from typing import Any, Optional

from ..infrastructure.compiler import CompiledInfrastructure
from ..infrastructure.registry import OBJECT_TYPE_LABELS
from ..models.diagnostics import Diagnostic
from ..models.enums import DiagnosticCategory, Severity
from . import codes

#: Static tolerance for platform usable-length reconciliation (Section R).
USABLE_LENGTH_TOLERANCE_M = 1e-6


def pairs_of(compiled: CompiledInfrastructure, key: str) -> list[tuple[Any, str]]:
    """Return ``(typed_object, json_path)`` pairs of a catalogue across all layers."""
    pairs: list[tuple[Any, str]] = []
    for layer in compiled.layers:
        objects = layer.catalogue(key)
        for index, obj in enumerate(objects):
            pairs.append((obj, layer.entry_path(key, index)))
    return pairs


def catalogue_items() -> list[tuple[str, type]]:
    """Return ``(catalogue_key, typed_model)`` pairs in canonical order."""
    from ..models.infrastructure import CATALOGUE_SPEC

    return [(key, CATALOGUE_SPEC[key][1]) for key in CATALOGUE_SPEC]


def object_type_of(key: str) -> str:
    """Return the registry object type of a catalogue key."""
    from ..models.infrastructure import CATALOGUE_SPEC

    entry = CATALOGUE_SPEC.get(key)
    return entry[2] if entry else key


def object_label(object_type: str) -> str:
    """Return the human label of a registry object type."""
    return OBJECT_TYPE_LABELS.get(object_type, object_type)


def is_finite_number(value: Any) -> bool:
    """Return ``True`` for a finite JSON number (booleans excluded)."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    return value == value and value not in (float("inf"), float("-inf"))


def reference_alignment(compiled: CompiledInfrastructure) -> Optional[Any]:
    """Return the single alignment object of a physical project (``None`` if ambiguous)."""
    alignments = compiled.catalogue("alignments")
    if len(alignments) == 1:
        return alignments[0]
    return None


def unresolved_reference(
    reference: Any,
    expected_type: str,
    json_path: str,
    *,
    label: Optional[str] = None,
    extra_context: Optional[dict[str, Any]] = None,
) -> Diagnostic:
    """Build the standard VAL-REGISTRY-003 unresolved-reference diagnostic."""
    expected_label = object_label(expected_type)
    name = label or expected_label
    return Diagnostic(
        code=codes.VAL_REGISTRY_003,
        severity=Severity.ERROR,
        category=DiagnosticCategory.REGISTRY,
        message=(
            f"{name} reference '{reference}' at '{json_path}' does not resolve to a "
            f"registered {expected_label.lower()}."
        ),
        object_id=str(reference) if reference is not None else None,
        context={
            "field": json_path,
            "reference": reference,
            "expected_object_type": expected_type,
            **(extra_context or {}),
        },
        suggested_action=(
            f"Create the missing {expected_label.lower()} or correct the reference value."
        ),
    )


def incomplete_observation(observation: Any, path: str, observation_type: str, missing: str) -> Diagnostic:
    """Build the VAL-OBS-003 diagnostic for an incomplete observation point."""
    return Diagnostic(
        code=codes.VAL_OBS_003,
        severity=Severity.ERROR,
        category=DiagnosticCategory.OBS,
        message=(
            f"Observation point '{getattr(observation, 'id', '?')}' of type {observation_type} is "
            f"incomplete: '{missing}' is required."
        ),
        object_id=getattr(observation, "id", None),
        context={"field": path, "observation_type": observation_type, "missing": missing},
        suggested_action=f"Provide '{missing}' for this observation point.",
    )
