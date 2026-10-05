"""Phase-2 infrastructure validation facade: structure, registry, geometry.

Validation is layered (Section AH):

* ``LEGACY`` containers   -> Phase-1 structural checks only (basic assurance);
* ``PHYSICAL`` containers -> the checks in this module plus the topology and
  station/platform validators, in addition to Phase 1.

Responsibility split:

* this module          - layer structure, global registry, alignment reference,
  horizontal/vertical geometry, speed restrictions, declaration policy;
* ``topology_validation`` - nodes, edges, chainage maps, connectivity;
* ``station_validation``  - stations, platforms, stopping marks, observations.

Every check returns structured diagnostics; nothing is silently repaired, and no
railway dynamics, signalling, headway or capacity semantics are evaluated here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

from ..infrastructure.compiler import CompiledInfrastructure
from ..infrastructure.mapping import CHAINAGE_TOLERANCE_KM
from ..models.diagnostics import Diagnostic
from ..models.enums import DiagnosticCategory, Severity
from ..models.infrastructure import PHYSICAL_MODE_FIELD
from . import codes
from .infrastructure_support import (
    catalogue_items,
    is_finite_number,
    object_label,
    object_type_of,
    pairs_of,
    reference_alignment,
    unresolved_reference,
)
from .station_validation import validate_stations_and_platforms
from .topology_validation import validate_topology

#: Phase-2 geometry coverage policy of this build (documented default). When a
#: physical project declares an alignment, its horizontal geometry must cover the
#: alignment completely and without overlap (Section J).
REQUIRE_CONTINUOUS_HORIZONTAL_COVERAGE = True


@dataclass
class InfrastructureValidationContext:
    """Inputs of one Phase-2 infrastructure validation run."""

    compiled: CompiledInfrastructure
    reference_alignment_id: Optional[str] = None


def validate_infrastructure(
    compiled: CompiledInfrastructure,
    *,
    reference_alignment_id: Optional[str] = None,
) -> list[Diagnostic]:
    """Run every Phase-2 physical infrastructure check on a compiled project."""
    diagnostics: list[Diagnostic] = []
    diagnostics.extend(_check_layer_structure(compiled))
    diagnostics.extend(_check_registry(compiled))
    diagnostics.extend(_check_alignment_reference(compiled, reference_alignment_id))
    diagnostics.extend(_check_horizontal_geometry(compiled))
    diagnostics.extend(_check_vertical_profiles(compiled))
    diagnostics.extend(_check_speed_restrictions(compiled))
    diagnostics.extend(validate_topology(compiled))
    diagnostics.extend(validate_stations_and_platforms(compiled))
    diagnostics.extend(_check_declaration_consistency(compiled))
    return diagnostics


def validation_scope_for(compiled: CompiledInfrastructure) -> str:
    """Return the assurance-scope label of a compiled infrastructure (Section AH)."""
    return compiled.scope.value


def iter_registered_ids(compiled: CompiledInfrastructure) -> Iterable[str]:
    """Return every registered engineering object ID."""
    return compiled.registry.ids()


# ---------------------------------------------------------------------------
# layer structure / registry
# ---------------------------------------------------------------------------
def _check_layer_structure(compiled: CompiledInfrastructure) -> list[Diagnostic]:
    """Report layer-id problems and physical projects without a usable layer."""
    diagnostics: list[Diagnostic] = []
    seen: dict[str, int] = {}
    for layer in compiled.layers:
        if not layer.layer_id:
            diagnostics.append(
                Diagnostic(
                    code=codes.VAL_INFR_001,
                    severity=Severity.ERROR,
                    category=DiagnosticCategory.INFRASTRUCTURE,
                    message=f"Infrastructure layer '{layer.path}' has no non-empty 'id'.",
                    context={"field": f"{layer.path}.id"},
                    suggested_action="Give each infrastructure layer a stable id (e.g. LYR-MAIN).",
                )
            )
            continue
        seen[layer.layer_id] = seen.get(layer.layer_id, 0) + 1
    for layer_id, count in sorted(seen.items()):
        if count > 1:
            diagnostics.append(
                Diagnostic(
                    code=codes.VAL_INFR_001,
                    severity=Severity.ERROR,
                    category=DiagnosticCategory.INFRASTRUCTURE,
                    message=(
                        f"Infrastructure layer id '{layer_id}' is used by {count} layer objects; "
                        "layer ids must be unique."
                    ),
                    object_id=layer_id,
                    context={"layer_id": layer_id, "occurrences": count},
                    suggested_action="Rename the duplicate layer id.",
                )
            )
    if compiled.physical and not compiled.layers:
        diagnostics.append(
            Diagnostic(
                code=codes.VAL_INFR_003,
                severity=Severity.ERROR,
                category=DiagnosticCategory.INFRASTRUCTURE,
                message=(
                    "The project declares Phase-2 physical infrastructure but the "
                    "infrastructure array contains no usable layer object."
                ),
                context={"physical": True},
                suggested_action=(
                    "Add the infrastructure layer (with its typed catalogues) or set "
                    f"'{PHYSICAL_MODE_FIELD}' to 'LEGACY'."
                ),
            )
        )
    return diagnostics


def _check_registry(compiled: CompiledInfrastructure) -> list[Diagnostic]:
    """Global uniqueness and well-formedness of registered engineering object IDs."""
    diagnostics: list[Diagnostic] = []

    for duplicate in compiled.registry.duplicates():
        types = duplicate.object_types
        cross_type = len(types) > 1
        locations = ", ".join(
            f"{registration.json_path} ({object_label(registration.object_type)})"
            for registration in duplicate.registrations
        )
        diagnostics.append(
            Diagnostic(
                code=codes.VAL_REGISTRY_001,
                severity=Severity.ERROR,
                category=DiagnosticCategory.REGISTRY,
                message=(
                    f"Duplicate engineering object id '{duplicate.object_id}' "
                    f"({len(duplicate.registrations)} registrations"
                    + (f", across object types {', '.join(types)}" if cross_type else "")
                    + f"): {locations}."
                ),
                object_id=duplicate.object_id,
                context={
                    "object_id": duplicate.object_id,
                    "object_types": list(types),
                    "cross_type": cross_type,
                    "registrations": [
                        {
                            "object_type": r.object_type,
                            "json_path": r.json_path,
                            "layer_id": r.layer_id,
                        }
                        for r in duplicate.registrations
                    ],
                },
                suggested_action=(
                    "All registered engineering object ids must be globally unique across the "
                    "project (frozen Phase-2 rule). Rename the duplicate id."
                ),
            )
        )

    for layer in compiled.layers:
        for key, _model in catalogue_items():
            for index, obj in enumerate(layer.catalogue(key)):
                object_id = getattr(obj, "id", None)
                if not isinstance(object_id, str) or not object_id.strip():
                    diagnostics.append(
                        Diagnostic(
                            code=codes.VAL_REGISTRY_002,
                            severity=Severity.ERROR,
                            category=DiagnosticCategory.REGISTRY,
                            message=(
                                f"{object_label(object_type_of(key))} at "
                                f"'{layer.entry_path(key, index)}' has no valid id."
                            ),
                            context={"field": layer.entry_path(key, index)},
                            suggested_action="Give the object a stable non-empty id.",
                        )
                    )
    return diagnostics


# ---------------------------------------------------------------------------
# alignment reference
# ---------------------------------------------------------------------------
def _check_alignment_reference(
    compiled: CompiledInfrastructure, reference_alignment_id: Optional[str]
) -> list[Diagnostic]:
    """``reference_system.alignment_id`` must resolve to an alignment object."""
    diagnostics: list[Diagnostic] = []
    if not compiled.physical:
        return diagnostics
    if not compiled.catalogue("alignments"):
        diagnostics.append(
            Diagnostic(
                code=codes.VAL_REGISTRY_003,
                severity=Severity.ERROR,
                category=DiagnosticCategory.REGISTRY,
                message=(
                    "The project declares physical infrastructure but contains no alignment "
                    "object for reference_system.alignment_id to resolve to."
                ),
                context={"expected_object_type": "alignment", "reference": reference_alignment_id},
                suggested_action="Add the alignment object to the layer's 'alignments' catalogue.",
            )
        )
        return diagnostics
    if reference_alignment_id and not compiled.registry.has_type_of(
        reference_alignment_id, "alignment"
    ):
        diagnostics.append(
            unresolved_reference(
                reference_alignment_id,
                "alignment",
                "reference_system.alignment_id",
                label="Reference system alignment",
            )
        )
    return diagnostics


# ---------------------------------------------------------------------------
# horizontal geometry
# ---------------------------------------------------------------------------
def _check_horizontal_geometry(compiled: CompiledInfrastructure) -> list[Diagnostic]:
    """Per-section rules plus overlap/coverage checks per alignment."""
    diagnostics: list[Diagnostic] = []
    sections_by_alignment: dict[str, list[tuple[str, object]]] = {}

    for section, path in pairs_of(compiled, "horizontal_geometry"):
        alignment_id = section.alignment_id
        if not compiled.registry.has_type_of(alignment_id, "alignment"):
            diagnostics.append(
                unresolved_reference(
                    alignment_id,
                    "alignment",
                    f"{path}.alignment_id",
                    label=f"Horizontal geometry section '{section.id}'",
                )
            )
            continue

        alignment = compiled.registry.value_of(alignment_id)
        start = float(section.start_chainage_km)
        end = float(section.end_chainage_km)
        if start >= end:
            diagnostics.append(
                Diagnostic(
                    code=codes.VAL_GEOM_002,
                    severity=Severity.ERROR,
                    category=DiagnosticCategory.GEOMETRY,
                    message=(
                        f"Horizontal geometry section '{section.id}' has start_chainage_km "
                        f"{section.start_chainage_km} >= end_chainage_km {section.end_chainage_km}."
                    ),
                    object_id=section.id,
                    context={"field": f"{path}.end_chainage_km"},
                    suggested_action="Set start_chainage_km < end_chainage_km.",
                )
            )
        elif (
            start < float(alignment.start_chainage_km) - CHAINAGE_TOLERANCE_KM
            or end > float(alignment.end_chainage_km) + CHAINAGE_TOLERANCE_KM
        ):
            diagnostics.append(
                Diagnostic(
                    code=codes.VAL_GEOM_002,
                    severity=Severity.ERROR,
                    category=DiagnosticCategory.GEOMETRY,
                    message=(
                        f"Horizontal geometry section '{section.id}' "
                        f"[{section.start_chainage_km}, {section.end_chainage_km}] km lies "
                        f"outside alignment '{alignment.id}' "
                        f"[{alignment.start_chainage_km}, {alignment.end_chainage_km}] km."
                    ),
                    object_id=section.id,
                    context={
                        "field": path,
                        "section_range_km": [start, end],
                        "alignment_range_km": [
                            float(alignment.start_chainage_km),
                            float(alignment.end_chainage_km),
                        ],
                    },
                    suggested_action="Clip the section to the alignment or correct its chainages.",
                )
            )

        section_type = getattr(section.type, "value", section.type)
        if section_type == "CURVE":
            radius = section.radius_m
            if radius is None:
                diagnostics.append(
                    Diagnostic(
                        code=codes.VAL_GEOM_001,
                        severity=Severity.ERROR,
                        category=DiagnosticCategory.GEOMETRY,
                        message=f"CURVE section '{section.id}' has no radius_m.",
                        object_id=section.id,
                        context={"field": f"{path}.radius_m"},
                        suggested_action="Provide radius_m > 0 for a curve section.",
                    )
                )
            elif not is_finite_number(radius) or float(radius) <= 0:
                diagnostics.append(
                    Diagnostic(
                        code=codes.VAL_GEOM_001,
                        severity=Severity.ERROR,
                        category=DiagnosticCategory.GEOMETRY,
                        message=(
                            f"CURVE section '{section.id}' has radius_m = {radius!r} (must be > 0)."
                        ),
                        object_id=section.id,
                        context={"field": f"{path}.radius_m", "found": radius},
                        suggested_action="Provide radius_m > 0 for a curve section.",
                    )
                )
            handedness = getattr(section.handedness, "value", section.handedness)
            if handedness not in ("LEFT", "RIGHT"):
                diagnostics.append(
                    Diagnostic(
                        code=codes.VAL_GEOM_001,
                        severity=Severity.ERROR,
                        category=DiagnosticCategory.GEOMETRY,
                        message=(
                            f"CURVE section '{section.id}' has handedness {handedness!r}; "
                            "LEFT or RIGHT is required."
                        ),
                        object_id=section.id,
                        context={"field": f"{path}.handedness", "found": handedness},
                        suggested_action="Set handedness to LEFT or RIGHT.",
                    )
                )
        sections_by_alignment.setdefault(alignment_id, []).append((path, section))

    for alignment_id, entries in sorted(sections_by_alignment.items()):
        ordered = sorted(entries, key=lambda item: (float(item[1].start_chainage_km), item[0]))
        for previous, current in zip(ordered, ordered[1:]):
            previous_section = previous[1]
            current_section = current[1]
            if float(current_section.start_chainage_km) < float(
                previous_section.end_chainage_km
            ) - CHAINAGE_TOLERANCE_KM:
                diagnostics.append(
                    Diagnostic(
                        code=codes.VAL_GEOM_003,
                        severity=Severity.ERROR,
                        category=DiagnosticCategory.GEOMETRY,
                        message=(
                            f"Horizontal geometry sections '{previous_section.id}' and "
                            f"'{current_section.id}' overlap on alignment '{alignment_id}' "
                            f"({current_section.start_chainage_km} < "
                            f"{previous_section.end_chainage_km})."
                        ),
                        object_id=current_section.id,
                        context={
                            "alignment_id": alignment_id,
                            "previous_section": previous_section.id,
                            "previous_end_km": float(previous_section.end_chainage_km),
                            "current_start_km": float(current_section.start_chainage_km),
                        },
                        suggested_action="Make geometry sections contiguous and non-overlapping.",
                    )
                )
        if REQUIRE_CONTINUOUS_HORIZONTAL_COVERAGE:
            diagnostics.extend(_check_coverage_gaps(reference_alignment(compiled), alignment_id, ordered))
    return diagnostics


def _check_coverage_gaps(
    alignment: object, alignment_id: str, ordered: list[tuple[str, object]]
) -> list[Diagnostic]:
    """Report chainage ranges of the alignment that no geometry section covers."""
    diagnostics: list[Diagnostic] = []
    if alignment is None or not ordered:
        return diagnostics
    expected_start = float(alignment.start_chainage_km)
    expected_end = float(alignment.end_chainage_km)
    cursor = expected_start
    gaps: list[tuple[float, float]] = []
    for _path, section in ordered:
        start = float(section.start_chainage_km)
        end = float(section.end_chainage_km)
        if start > cursor + CHAINAGE_TOLERANCE_KM:
            gaps.append((cursor, start))
        cursor = max(cursor, end)
    if cursor < expected_end - CHAINAGE_TOLERANCE_KM:
        gaps.append((cursor, expected_end))
    for gap_start, gap_end in gaps:
        diagnostics.append(
            Diagnostic(
                code=codes.VAL_GEOM_004,
                severity=Severity.ERROR,
                category=DiagnosticCategory.GEOMETRY,
                message=(
                    f"Horizontal geometry of alignment '{alignment_id}' is not continuous: "
                    f"no section covers [{gap_start:g}, {gap_end:g}] km."
                ),
                object_id=alignment_id,
                context={
                    "alignment_id": alignment_id,
                    "gap_start_km": gap_start,
                    "gap_end_km": gap_end,
                    "coverage_expected_km": [expected_start, expected_end],
                },
                suggested_action=(
                    "Add the missing geometry section(s) so the alignment is covered "
                    "completely and without overlap."
                ),
            )
        )
    return diagnostics


# ---------------------------------------------------------------------------
# vertical profiles
# ---------------------------------------------------------------------------
def _check_vertical_profiles(compiled: CompiledInfrastructure) -> list[Diagnostic]:
    """Vertical profile ordering, duplicates, containment and source mode."""
    diagnostics: list[Diagnostic] = []
    for profile, path in pairs_of(compiled, "vertical_profiles"):
        alignment_id = profile.alignment_id
        alignment = None
        if not compiled.registry.has_type_of(alignment_id, "alignment"):
            diagnostics.append(
                unresolved_reference(
                    alignment_id,
                    "alignment",
                    f"{path}.alignment_id",
                    label=f"Vertical profile '{profile.id}'",
                )
            )
        else:
            alignment = compiled.registry.value_of(alignment_id)

        mode = getattr(profile.source_mode, "value", profile.source_mode)
        if mode != "ELEVATION_POINTS":
            diagnostics.append(
                Diagnostic(
                    code=codes.VAL_GEOM_006,
                    severity=Severity.ERROR,
                    category=DiagnosticCategory.GEOMETRY,
                    message=(
                        f"Vertical profile '{profile.id}' uses unsupported source_mode {mode!r}; "
                        "Phase 2 supports ELEVATION_POINTS."
                    ),
                    object_id=profile.id,
                    context={"field": f"{path}.source_mode", "found": mode},
                    suggested_action="Set source_mode to ELEVATION_POINTS.",
                )
            )

        points = compiled.profile_point_pairs(str(profile.id))
        if len(points) < 2:
            diagnostics.append(
                Diagnostic(
                    code=codes.VAL_GEOM_006,
                    severity=Severity.ERROR,
                    category=DiagnosticCategory.GEOMETRY,
                    message=(
                        f"Vertical profile '{profile.id}' has {len(points)} usable elevation "
                        "point(s); at least two are required."
                    ),
                    object_id=profile.id,
                    context={"field": f"{path}.points", "point_count": len(points)},
                    suggested_action="Provide at least two elevation points.",
                )
            )

        previous_chainage: Optional[float] = None
        seen_chainages: dict[float, str] = {}
        for point, point_path in points:
            chainage = float(point.chainage_km)
            elevation = float(point.elevation_m)
            if not is_finite_number(elevation):
                diagnostics.append(
                    Diagnostic(
                        code=codes.VAL_GEOM_005,
                        severity=Severity.ERROR,
                        category=DiagnosticCategory.GEOMETRY,
                        message=f"Vertical profile point '{point.id}' has a non-finite elevation_m.",
                        object_id=point.id,
                        context={"field": f"{point_path}.elevation_m", "found": point.elevation_m},
                        suggested_action="Provide a finite elevation in metres.",
                    )
                )
            if alignment is not None and (
                chainage < float(alignment.start_chainage_km) - CHAINAGE_TOLERANCE_KM
                or chainage > float(alignment.end_chainage_km) + CHAINAGE_TOLERANCE_KM
            ):
                diagnostics.append(
                    Diagnostic(
                        code=codes.VAL_GEOM_002,
                        severity=Severity.ERROR,
                        category=DiagnosticCategory.GEOMETRY,
                        message=(
                            f"Vertical profile point '{point.id}' at {point.chainage_km} km lies "
                            f"outside alignment '{alignment.id}' "
                            f"[{alignment.start_chainage_km}, {alignment.end_chainage_km}] km."
                        ),
                        object_id=point.id,
                        context={"field": point_path},
                        suggested_action="Move the point inside the alignment range.",
                    )
                )
            if previous_chainage is not None and chainage <= previous_chainage + CHAINAGE_TOLERANCE_KM:
                diagnostics.append(
                    Diagnostic(
                        code=codes.VAL_GEOM_005,
                        severity=Severity.ERROR,
                        category=DiagnosticCategory.GEOMETRY,
                        message=(
                            f"Vertical profile '{profile.id}' point chainages are not strictly "
                            f"increasing at '{point.id}' ({previous_chainage} -> {chainage} km)."
                        ),
                        object_id=point.id,
                        context={
                            "field": point_path,
                            "previous_chainage_km": previous_chainage,
                            "chainage_km": chainage,
                        },
                        suggested_action="Order the elevation points by strictly increasing chainage.",
                    )
                )
            previous_chainage = chainage
            if chainage in seen_chainages:
                diagnostics.append(
                    Diagnostic(
                        code=codes.VAL_GEOM_005,
                        severity=Severity.ERROR,
                        category=DiagnosticCategory.GEOMETRY,
                        message=(
                            f"Vertical profile '{profile.id}' has duplicate chainage {chainage} km "
                            f"at '{point.id}' and '{seen_chainages[chainage]}'."
                        ),
                        object_id=point.id,
                        context={"field": point_path, "chainage_km": chainage},
                        suggested_action="Give each profile point a unique chainage.",
                    )
                )
            else:
                seen_chainages[chainage] = str(point.id)
    return diagnostics


# ---------------------------------------------------------------------------
# speed restrictions
# ---------------------------------------------------------------------------
def _check_speed_restrictions(compiled: CompiledInfrastructure) -> list[Diagnostic]:
    """Speed restriction ranges, speeds and alignment containment."""
    diagnostics: list[Diagnostic] = []
    for restriction, path in pairs_of(compiled, "speed_restrictions"):
        alignment_id = restriction.alignment_id
        if not compiled.registry.has_type_of(alignment_id, "alignment"):
            diagnostics.append(
                unresolved_reference(
                    alignment_id,
                    "alignment",
                    f"{path}.alignment_id",
                    label=f"Speed restriction '{restriction.id}'",
                )
            )
            continue
        alignment = compiled.registry.value_of(alignment_id)
        start = float(restriction.start_chainage_km)
        end = float(restriction.end_chainage_km)
        if start >= end:
            diagnostics.append(
                Diagnostic(
                    code=codes.VAL_GEOM_007,
                    severity=Severity.ERROR,
                    category=DiagnosticCategory.GEOMETRY,
                    message=(
                        f"Speed restriction '{restriction.id}' has start_chainage_km "
                        f"{restriction.start_chainage_km} >= end_chainage_km "
                        f"{restriction.end_chainage_km}."
                    ),
                    object_id=restriction.id,
                    context={"field": f"{path}.end_chainage_km"},
                    suggested_action="Set start_chainage_km < end_chainage_km.",
                )
            )
        elif (
            start < float(alignment.start_chainage_km) - CHAINAGE_TOLERANCE_KM
            or end > float(alignment.end_chainage_km) + CHAINAGE_TOLERANCE_KM
        ):
            diagnostics.append(
                Diagnostic(
                    code=codes.VAL_GEOM_007,
                    severity=Severity.ERROR,
                    category=DiagnosticCategory.GEOMETRY,
                    message=(
                        f"Speed restriction '{restriction.id}' "
                        f"[{restriction.start_chainage_km}, {restriction.end_chainage_km}] km lies "
                        f"outside alignment '{alignment.id}' "
                        f"[{alignment.start_chainage_km}, {alignment.end_chainage_km}] km."
                    ),
                    object_id=restriction.id,
                    context={
                        "field": path,
                        "restriction_range_km": [start, end],
                        "alignment_range_km": [
                            float(alignment.start_chainage_km),
                            float(alignment.end_chainage_km),
                        ],
                    },
                    suggested_action="Clip the restriction to the alignment or correct its chainages.",
                )
            )
        speed = restriction.speed_kmh
        if not is_finite_number(speed) or float(speed) <= 0:
            diagnostics.append(
                Diagnostic(
                    code=codes.VAL_GEOM_007,
                    severity=Severity.ERROR,
                    category=DiagnosticCategory.GEOMETRY,
                    message=(
                        f"Speed restriction '{restriction.id}' has speed_kmh = {speed!r} "
                        "(must be > 0)."
                    ),
                    object_id=restriction.id,
                    context={"field": f"{path}.speed_kmh", "found": speed},
                    suggested_action="Provide a positive speed in km/h.",
                )
            )
    return diagnostics


# ---------------------------------------------------------------------------
# declaration policy
# ---------------------------------------------------------------------------
def _check_declaration_consistency(compiled: CompiledInfrastructure) -> list[Diagnostic]:
    """Opaque records must not be mixed into a physical project (Section AH)."""
    diagnostics: list[Diagnostic] = []
    if not compiled.physical:
        return diagnostics
    for catalogue, layer_path, path, record in compiled.legacy_records:
        if not isinstance(record, dict) or "id" not in record:
            continue
        diagnostics.append(
            Diagnostic(
                code=codes.VAL_PHASE_002,
                severity=Severity.ERROR,
                category=DiagnosticCategory.PHASE2,
                message=(
                    f"Legacy opaque record '{path}' (catalogue '{catalogue}' of layer "
                    f"'{layer_path}') is mixed into a project that declares Phase-2 physical "
                    "infrastructure. Incomplete opaque records must not be mixed into a "
                    "physical project."
                ),
                object_id=str(record.get("id")),
                context={"field": path, "catalogue": catalogue, "layer": layer_path},
                suggested_action=(
                    "Migrate the record to the corresponding typed Phase-2 catalogue, or remove it."
                ),
            )
        )
    return diagnostics
