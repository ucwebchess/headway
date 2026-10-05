"""Compile the canonical ``infrastructure`` array into typed Phase-2 views.

The canonical JSON document remains the source of truth. This compiler produces
a *derived, typed* view of it for validation, the registry, the topology graph
and the UI - and reports every parse problem as a structured diagnostic instead
of raising.

Robustness rule: each catalogue entry is parsed **individually**. One malformed
entry produces one diagnostic; the remaining entries still compile, so a report
can list every problem at once.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterator, Optional

from pydantic import ValidationError

from ..models.base import ContainerBase
from ..models.diagnostics import Diagnostic
from ..models.enums import DiagnosticCategory, PhysicalMode, Severity, ValidationScope
from ..models.infrastructure import (
    CATALOGUE_SPEC,
    LEGACY_CATALOGUE_KEYS,
    PHASE2_CATALOGUE_KEYS,
    PHYSICAL_MODE_FIELD,
    VERTICAL_PROFILE_POINT_KEY,
    VERTICAL_PROFILE_POINT_OBJECT_TYPE,
)
from .registry import EngineeringRegistry, OBJECT_TYPE_LABELS

#: Fields that declare an infrastructure container as Phase-2 physical.
#: Any of these triggers controlled strict parsing (Section AH).
PHYSICAL_DECLARATION_FIELDS: tuple[str, ...] = (
    PHYSICAL_MODE_FIELD,
    "alignments",
    "track_groups",
    "horizontal_geometry",
    "vertical_profiles",
    "speed_restrictions",
    "nodes",
    "tracks",
    "platforms",
    "stopping_marks",
    "observation_points",
)


@dataclass
class CompiledLayer:
    """Typed view of one infrastructure layer.

    ``raw`` is the untouched canonical layer object (extension fields included);
    the typed catalogues are derived views and are never written back.
    """

    raw: dict[str, Any]
    index: int
    path: str
    layer_id: Optional[str]
    name: Optional[str]
    physical_mode: PhysicalMode
    declared_physical: bool
    typed: dict[str, list[Any]] = field(default_factory=dict)
    typed_entry_paths: dict[str, list[str]] = field(default_factory=dict)
    profile_points: list[Any] = field(default_factory=list)
    profile_point_paths: list[str] = field(default_factory=list)
    profile_point_parents: list[str] = field(default_factory=list)
    legacy_records: list[tuple[str, str, Any]] = field(default_factory=list)

    @property
    def is_physical(self) -> bool:
        """Return whether this layer is treated as Phase-2 physical infrastructure."""
        return self.declared_physical or self.physical_mode is PhysicalMode.PHYSICAL

    def catalogue(self, key: str) -> list[Any]:
        """Return the typed objects of one catalogue key."""
        return list(self.typed.get(key, []))

    def entry_paths(self, key: str) -> list[str]:
        """Return the JSON paths of one catalogue's entries (aligned with objects)."""
        return list(self.typed_entry_paths.get(key, []))

    def entry_path(self, key: str, index: int) -> str:
        """Return the JSON path of one catalogue entry."""
        paths = self.typed_entry_paths.get(key, [])
        if 0 <= index < len(paths):
            return paths[index]
        return f"{self.path}.{key}[{index}]"

    def typed_entry_count(self) -> int:
        """Return the number of typed catalogue entries in this layer (no profile points)."""
        return sum(len(objects) for objects in self.typed.values())

    def all_legacy_records(self) -> list[tuple[str, str, Any]]:
        """Return ``(catalogue, json_path, record)`` for every preserved legacy record."""
        return list(self.legacy_records)


@dataclass
class CompiledInfrastructure:
    """Typed infrastructure of a whole project (union of all layers)."""

    raw: list[Any]
    layers: list[CompiledLayer]
    registry: EngineeringRegistry
    diagnostics: list[Diagnostic]
    physical: bool
    legacy_records: list[tuple[str, str, str, Any]]  # (catalogue, layer_path, path, record)
    scope: ValidationScope

    # -- aggregate queries -------------------------------------------------
    def catalogue(self, key: str) -> list[Any]:
        """Return the typed objects of a catalogue key across all layers."""
        return [obj for layer in self.layers for obj in layer.catalogue(key)]

    def catalogue_paths(self, key: str) -> list[str]:
        """Return the JSON paths of a catalogue's entries across all layers."""
        return [path for layer in self.layers for path in layer.entry_paths(key)]

    def entry_path(self, key: str, index: int) -> str:
        """Return the JSON path of the n-th entry of a catalogue across all layers."""
        offset = 0
        for layer in self.layers:
            layer_objects = layer.catalogue(key)
            if index < offset + len(layer_objects):
                return layer.entry_path(key, index - offset)
            offset += len(layer_objects)
        return f"infrastructure.*.{key}[{index}]"

    def count(self, key: str) -> int:
        """Return the number of typed objects of a catalogue key across all layers."""
        return sum(len(layer.catalogue(key)) for layer in self.layers)

    def profile_points(self) -> list[Any]:
        """Return every typed vertical profile point across all layers."""
        return [point for layer in self.layers for point in layer.profile_points]

    def profile_point_paths(self) -> list[str]:
        """Return the JSON paths of every vertical profile point."""
        return [path for layer in self.layers for path in layer.profile_point_paths]

    def profile_point_parents(self) -> list[str]:
        """Return the owning vertical profile id of every vertical profile point."""
        return [parent for layer in self.layers for parent in layer.profile_point_parents]

    def profile_point_pairs(self, profile_id: str) -> list[tuple[Any, str]]:
        """Return ``(point, json_path)`` pairs of one vertical profile, in order."""
        return [
            (point, path)
            for parent, point, path in zip(
                self.profile_point_parents(), self.profile_points(), self.profile_point_paths()
            )
            if parent == profile_id
        ]

    def ids(self, key: str) -> tuple[str, ...]:
        """Return the IDs of a catalogue's typed objects."""
        return tuple(str(getattr(obj, "id", "")) for obj in self.catalogue(key))

    def by_id(self, key: str) -> dict[str, Any]:
        """Return a ``{id: object}`` map of a catalogue's typed objects."""
        return {str(getattr(obj, "id", "")): obj for obj in self.catalogue(key)}

    def typed_object_count(self) -> int:
        """Return the number of typed catalogue entries across all layers."""
        return sum(layer.typed_entry_count() for layer in self.layers)

    def typed_registration_entries(self) -> Iterator[tuple[str, str, Any, str, Optional[str]]]:
        """Yield ``(object_id, object_type, value, json_path, layer_id)`` for the registry."""
        for layer in self.layers:
            for key, model in _catalogue_models():
                objects = layer.catalogue(key)
                paths = layer.entry_paths(key)
                object_type = CATALOGUE_SPEC[key][2]
                for index, obj in enumerate(objects):
                    path = paths[index] if index < len(paths) else f"{layer.path}.{key}[{index}]"
                    object_id = getattr(obj, "id", None)
                    if isinstance(object_id, str) and object_id:
                        yield object_id, object_type, obj, path, layer.layer_id
            for index, point in enumerate(layer.profile_points):
                object_id = getattr(point, "id", None)
                if isinstance(point, str) and point:
                    path = layer.profile_point_paths[index]
                    yield (
                        object_id,
                        VERTICAL_PROFILE_POINT_OBJECT_TYPE,
                        point,
                        path,
                        layer.layer_id,
                    )

    def type_counts(self) -> dict[str, int]:
        """Return the number of typed objects per catalogue key."""
        return {key: self.count(key) for key in PHASE2_CATALOGUE_KEYS}

    def inventory_rows(self) -> list[tuple[str, int]]:
        """Return UI-ready typed inventory rows (Section AO)."""
        rows: list[tuple[str, int]] = []
        for key, (label, _model, _object_type) in CATALOGUE_SPEC.items():
            rows.append((label, self.count(key)))
            if key == "vertical_profiles":
                rows.append(("Vertical profile points", len(self.profile_points())))
        return rows

    def legacy_record_count(self) -> int:
        """Return the number of preserved Phase-1 opaque catalogue records."""
        return len(self.legacy_records)

    def present_catalogue_keys(self) -> tuple[str, ...]:
        """Return the typed catalogue keys that exist in at least one layer."""
        return tuple(key for key in PHASE2_CATALOGUE_KEYS if self.count(key) or self._declared(key))

    def _declared(self, key: str) -> bool:
        """Return whether a layer object declares the catalogue key (even if empty)."""
        return any(key in layer.raw for layer in self.layers)

    def topology(self) -> Any:
        """Return a deterministic adjacency view of the typed nodes and tracks.

        Connectivity is established by node identity only (Section W); the view
        performs no routing and no chainage-equality reasoning.
        """
        from .topology import InfrastructureTopology

        topology = InfrastructureTopology.from_objects(
            self.catalogue("nodes"), self.catalogue("tracks")
        )
        return topology


def _catalogue_models() -> list[tuple[str, str, type[ContainerBase], str]]:
    """Return ``(catalogue_key, label, typed_model, object_type)`` in canonical order."""
    return [
        (key, label, model, object_type)
        for key, (label, model, object_type) in CATALOGUE_SPEC.items()
    ]


def layer_declares_physical(layer: dict[str, Any]) -> bool:
    """Return whether a layer object declares Phase-2 physical infrastructure."""
    if layer.get(PHYSICAL_MODE_FIELD) == PhysicalMode.PHYSICAL.value:
        return True
    return any(field_name in layer for field_name in PHYSICAL_DECLARATION_FIELDS)


def compile_infrastructure(
    infrastructure: Any,
    *,
    layer_diag: bool = True,
) -> CompiledInfrastructure:
    """Compile the canonical ``infrastructure`` array into typed views.

    Parameters
    ----------
    infrastructure
        The raw ``infrastructure`` section of the canonical document.
    layer_diag
        When ``True``, non-object layer entries produce their own schema
        diagnostics. Set to ``False`` when the caller already reported them
        (used by the validation facade to avoid duplicate findings).
    """
    # Imported lazily: ``validation`` imports this module, so a top-level
    # import here would create a cycle.
    from ..validation import codes

    diagnostics: list[Diagnostic] = []
    layers: list[CompiledLayer] = []
    raw_list = infrastructure if isinstance(infrastructure, list) else []
    physical = False

    for index, raw_layer in enumerate(raw_list):
        path = f"infrastructure[{index}]"
        if not isinstance(raw_layer, dict):
            if layer_diag:
                diagnostics.append(
                    Diagnostic(
                        code=codes.VAL_SCHEMA_002,
                        severity=Severity.ERROR,
                        category=DiagnosticCategory.SCHEMA,
                        message=(
                            f"'{path}' must be a JSON object, "
                            f"but it is a JSON {_type_name(raw_layer)}."
                        ),
                        context={"field": path, "found_type": _type_name(raw_layer)},
                        suggested_action="Every entry of the infrastructure array must be an object.",
                    )
                )
            continue

        layer_id = raw_layer.get("id") if isinstance(raw_layer.get("id"), str) else None
        name = raw_layer.get("name") if isinstance(raw_layer.get("name"), str) else None
        declared_physical = layer_declares_physical(raw_layer)
        mode_value = raw_layer.get(PHYSICAL_MODE_FIELD)
        try:
            physical_mode = PhysicalMode(mode_value) if mode_value is not None else PhysicalMode.LEGACY
        except ValueError:
            physical_mode = PhysicalMode.LEGACY
            diagnostics.append(
                Diagnostic(
                    code=codes.VAL_ENUM_001,
                    severity=Severity.ERROR,
                    category=DiagnosticCategory.ENUM,
                    message=(
                        f"'{path}.{PHYSICAL_MODE_FIELD}' has unsupported value {mode_value!r}; "
                        f"supported values are {[m.value for m in PhysicalMode]}."
                    ),
                    context={"field": f"{path}.{PHYSICAL_MODE_FIELD}", "found": mode_value},
                    suggested_action="Use 'LEGACY' or 'PHYSICAL'.",
                )
            )
        physical = physical or declared_physical or physical_mode is PhysicalMode.PHYSICAL

        layer = CompiledLayer(
            raw=raw_layer,
            index=index,
            path=path,
            layer_id=layer_id,
            name=name,
            physical_mode=physical_mode,
            declared_physical=declared_physical,
        )

        # ---- typed catalogues ------------------------------------------
        for key, label, model, object_type in _catalogue_models():
            entries = raw_layer.get(key)
            if entries is None:
                continue
            if not isinstance(entries, list):
                diagnostics.append(
                    Diagnostic(
                        code=codes.VAL_SCHEMA_002,
                        severity=Severity.ERROR,
                        category=DiagnosticCategory.SCHEMA,
                        message=(
                            f"'{path}.{key}' must be a JSON array, but it is a "
                            f"JSON {_type_name(entries)}."
                        ),
                        context={"field": f"{path}.{key}", "found_type": _type_name(entries)},
                        suggested_action=f"Use an array for '{key}' (empty: []).",
                    )
                )
                continue
            for entry_index, entry in enumerate(entries):
                entry_path = f"{path}.{key}[{entry_index}]"
                parsed, problem = _parse_entry(model, entry, entry_path, label, object_type)
                if problem is not None:
                    diagnostics.append(problem)
                    continue
                layer.typed.setdefault(key, []).append(parsed)
                layer.typed_entry_paths.setdefault(key, []).append(entry_path)
                if key == "vertical_profiles":
                    _compile_profile_points(
                        parsed, entry_path, layer, diagnostics, codes
                    )

        # ---- preserved legacy catalogues -------------------------------
        for key in LEGACY_CATALOGUE_KEYS:
            records = raw_layer.get(key)
            if not isinstance(records, list):
                continue
            for record_index, record in enumerate(records):
                record_path = f"{path}.{key}[{record_index}]"
                layer.legacy_records.append((key, record_path, record))
                if layer.is_physical and _is_identified_object(record):
                    diagnostics.append(
                        Diagnostic(
                            code=codes.VAL_INFR_020,
                            severity=Severity.WARNING,
                            category=DiagnosticCategory.INFRASTRUCTURE,
                            message=(
                                f"Legacy opaque catalogue entry '{record_path}' carries an 'id' "
                                "but is not a typed Phase-2 engineering object, so it is not "
                                "registered and is not checked by physical validation."
                            ),
                            object_id=str(record.get("id")),
                            context={
                                "field": record_path,
                                "catalogue": key,
                                "layer": layer.layer_id,
                            },
                            suggested_action=(
                                "Migrate the record to the typed Phase-2 catalogue for this data, "
                                "or remove the 'id' field from the opaque extension record."
                            ),
                        )
                    )
        layers.append(layer)

    registry = EngineeringRegistry()
    for object_id, object_type, value, json_path, layer_id in _iter_registrations(layers):
        registry.register(object_id, object_type, value, json_path=json_path, layer_id=layer_id)

    scope = (
        ValidationScope.PHASE2_PHYSICAL_INFRASTRUCTURE if physical else ValidationScope.LEGACY_OPAQUE_DATA
    )
    return CompiledInfrastructure(
        raw=raw_list,
        layers=layers,
        registry=registry,
        diagnostics=diagnostics,
        physical=physical,
        legacy_records=[
            (catalogue, layer.path, path, record)
            for layer in layers
            for catalogue, path, record in layer.all_legacy_records()
        ],
        scope=scope,
    )


def _iter_registrations(
    layers: list[CompiledLayer],
) -> Iterator[tuple[str, str, Any, str, Optional[str]]]:
    """Yield the registration tuples for every typed engineering object."""
    for layer in layers:
        for key, _label, _model, object_type in _catalogue_models():
            objects = layer.catalogue(key)
            paths = layer.entry_paths(key)
            for index, obj in enumerate(objects):
                object_id = getattr(obj, "id", None)
                if not isinstance(object_id, str) or not object_id:
                    continue
                path = paths[index] if index < len(paths) else f"{layer.path}.{key}[{index}]"
                yield object_id, object_type, obj, path, layer.layer_id
        for index, point in enumerate(layer.profile_points):
            object_id = getattr(point, "id", None)
            if not isinstance(object_id, str) or not object_id:
                continue
            yield (
                object_id,
                VERTICAL_PROFILE_POINT_OBJECT_TYPE,
                point,
                layer.profile_point_paths[index],
                layer.layer_id,
            )


def _compile_profile_points(
    profile: Any,
    profile_path: str,
    layer: CompiledLayer,
    diagnostics: list[Diagnostic],
    codes: Any,
) -> None:
    """Parse the nested elevation points of one vertical profile."""
    points = getattr(profile, VERTICAL_PROFILE_POINT_KEY, None)
    if points is None:
        return
    if not isinstance(points, list):
        diagnostics.append(
            Diagnostic(
                code=codes.VAL_SCHEMA_002,
                severity=Severity.ERROR,
                category=DiagnosticCategory.SCHEMA,
                message=(
                    f"'{profile_path}.{VERTICAL_PROFILE_POINT_KEY}' must be a JSON array, "
                    f"but it is a JSON {_type_name(points)}."
                ),
                context={"field": f"{profile_path}.{VERTICAL_PROFILE_POINT_KEY}"},
                suggested_action="Use an array of elevation points.",
            )
        )
        return
    from ..models.infrastructure import VerticalProfilePoint

    for point_index, point in enumerate(points):
        point_path = f"{profile_path}.{VERTICAL_PROFILE_POINT_KEY}[{point_index}]"
        parsed, problem = _parse_entry(
            VerticalProfilePoint, point, point_path, "Vertical profile point", "vertical_profile_point"
        )
        if problem is not None:
            diagnostics.append(problem)
            continue
        layer.profile_points.append(parsed)
        layer.profile_point_paths.append(point_path)
        layer.profile_point_parents.append(str(getattr(profile, "id", "")))


def _parse_entry(
    model: type[ContainerBase],
    entry: Any,
    entry_path: str,
    label: str,
    object_type: str,
) -> tuple[Optional[ContainerBase], Optional[Diagnostic]]:
    """Parse one catalogue entry; return ``(object, diagnostic)``."""
    from ..validation import codes

    if isinstance(entry, model):
        # Already a typed object: nested lists (e.g. vertical profile points) are
        # typed by their parent model, so no second parse is needed.
        return entry, None
    if not isinstance(entry, dict):
        return None, Diagnostic(
            code=codes.VAL_SCHEMA_002,
            severity=Severity.ERROR,
            category=DiagnosticCategory.SCHEMA,
            message=(
                f"'{entry_path}' must be a JSON object, but it is a JSON {_type_name(entry)}."
            ),
            context={"field": entry_path, "found_type": _type_name(entry), "object_type": object_type},
            suggested_action=f"Represent the {label.lower()} as an object.",
        )
    try:
        return model.model_validate(entry), None
    except ValidationError as exc:
        problems = []
        for error in exc.errors():
            location = ".".join(str(part) for part in error.get("loc", ())) or "<object>"
            problems.append(f"{location}: {error.get('msg', 'invalid value')}")
        detail = "; ".join(problems)
        object_id = entry.get("id") if isinstance(entry.get("id"), str) else None
        return None, Diagnostic(
            code=codes.VAL_INFR_002,
            severity=Severity.ERROR,
            category=DiagnosticCategory.INFRASTRUCTURE,
            message=(
                f"{label} '{entry_path}' could not be parsed as a typed Phase-2 "
                f"engineering object ({detail})."
            ),
            object_id=object_id,
            context={
                "field": entry_path,
                "object_type": object_type,
                "object_label": OBJECT_TYPE_LABELS.get(object_type, object_type),
                "problems": problems,
                "found_fields": sorted(entry.keys()),
            },
            suggested_action=(
                "Correct the typed fields of this object (units are part of the field "
                "names, e.g. length_m, chainage_km) or remove it from the typed catalogue."
            ),
        )


def _is_identified_object(record: Any) -> bool:
    """Return whether a legacy record is a dict that carries an ``id`` field."""
    return isinstance(record, dict) and "id" in record


def _type_name(value: Any) -> str:
    """Return a JSON-ish type name for diagnostic messages."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return "array"
    return type(value).__name__
