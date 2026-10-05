"""Editor field specifications for the Phase-3 infrastructure editors (§G2, §G12).

One declaration per editable catalogue field drives, at the same time:

* the widget kind (text / number / enum / reference / nested chainage map),
* the **unit suffix** shown in the column header (taken from the field name,
  which is the Phase-2 typed-catalogue field name - never renamed),
* the tooltip (looked up in :mod:`railway_headway_sim.ui.field_help`),
* whether the field is STANDARD or ADVANCED (§G11),
* the provenance label (INPUT / DERIVED - see :mod:`railway_headway_sim.ui.editing`).

The catalogue keys and field names are exactly those of
``railway_headway_sim.models.infrastructure``; this module adds presentation
metadata only.
"""

from __future__ import annotations

from dataclasses import dataclass, field as dataclass_field
from enum import Enum
from typing import Any, Optional

from ..models import enums as model_enums
from . import field_help


class FieldKind(str, Enum):
    """Widget kind of one editable field."""

    TEXT = "TEXT"
    ID = "ID"
    INTEGER = "INTEGER"
    NUMBER = "NUMBER"
    ENUM = "ENUM"
    REFERENCE = "REFERENCE"
    ID_LIST = "ID_LIST"
    MEMBER_LIST = "MEMBER_LIST"


#: Unit suffix per unit-bearing field name prefix (the suffix *is* the unit).
UNIT_SUFFIXES: tuple[str, ...] = ("_km", "_m", "_kmh", "_permille", "_s", "_mps2", "_t", "_kn", "_kw")


def unit_suffix(field_name: str) -> Optional[str]:
    """Return the unit part of a unit-suffixed field name (``length_m`` -> ``m``)."""
    for suffix in UNIT_SUFFIXES:
        if field_name.endswith(suffix):
            return suffix.lstrip("_").replace("mps2", "m/s²")
    if field_name.endswith("chainage_map"):
        return None
    return None


def unit_label(field_name: str) -> str:
    """Return the display unit of a field (``''`` when the field has no unit)."""
    suffix = unit_suffix(field_name)
    if suffix is None:
        return ""
    return {"permille": "‰", "kmh": "km/h"}.get(suffix, suffix)


@dataclass(frozen=True)
class FieldSpec:
    """Presentation metadata of one editable field of a typed catalogue."""

    name: str
    kind: FieldKind
    catalogue: str
    advanced: bool = False
    reference: Optional[str] = None
    enum: Optional[type] = None
    step: Optional[float] = None
    minimum: Optional[float] = None
    optional: bool = False
    derived: bool = False
    note: str = ""

    @property
    def unit(self) -> str:
        """Return the unit suffix shown in the column header."""
        return unit_label(self.name)

    @property
    def header(self) -> str:
        """Return the column header, including the unit when the field carries one."""
        return f"{self.name} [{self.unit}]" if self.unit else self.name

    @property
    def tooltip(self) -> str:
        """Return the one-line tooltip from :mod:`field_help`."""
        return field_help.field_tooltip(self.catalogue, self.name)

    @property
    def enum_values(self) -> tuple[str, ...]:
        """Return the allowed values of an ENUM field."""
        if self.enum is None:
            return ()
        return tuple(str(member.value) for member in self.enum)  # type: ignore[attr-defined]


def _spec(name: str, catalogue: str, kind: FieldKind, **kwargs: Any) -> FieldSpec:
    """Build a :class:`FieldSpec` (small helper to keep the tables readable)."""
    return FieldSpec(name=name, catalogue=catalogue, kind=kind, **kwargs)


# ---------------------------------------------------------------------------
# per-catalogue field specifications (order = editor column order)
# ---------------------------------------------------------------------------
_ALIGNMENT: tuple[FieldSpec, ...] = (
    _spec("id", "alignments", FieldKind.ID),
    _spec("name", "alignments", FieldKind.TEXT, optional=True),
    _spec("start_chainage_km", "alignments", FieldKind.NUMBER, step=0.1),
    _spec("end_chainage_km", "alignments", FieldKind.NUMBER, step=0.1),
)

_TRACK_GROUP: tuple[FieldSpec, ...] = (
    _spec("id", "track_groups", FieldKind.ID),
    _spec("name", "track_groups", FieldKind.TEXT, optional=True),
    _spec("directionality", "track_groups", FieldKind.ENUM, enum=model_enums.Directionality),
    _spec(
        "normal_direction",
        "track_groups",
        FieldKind.ENUM,
        enum=model_enums.Direction,
        optional=True,
        advanced=True,
    ),
)

_NODE: tuple[FieldSpec, ...] = (
    _spec("id", "nodes", FieldKind.ID),
    _spec("type", "nodes", FieldKind.ENUM, enum=model_enums.NodeType),
    _spec("chainage_km", "nodes", FieldKind.NUMBER, step=0.1),
    _spec("station_id", "nodes", FieldKind.REFERENCE, reference="stations", optional=True),
    _spec("name", "nodes", FieldKind.TEXT, optional=True, advanced=True),
)

_TRACK: tuple[FieldSpec, ...] = (
    _spec("id", "tracks", FieldKind.ID),
    _spec("from_node", "tracks", FieldKind.REFERENCE, reference="nodes"),
    _spec("to_node", "tracks", FieldKind.REFERENCE, reference="nodes"),
    _spec("length_m", "tracks", FieldKind.NUMBER, step=10.0, minimum=0.0),
    _spec("directionality", "tracks", FieldKind.ENUM, enum=model_enums.Directionality),
    _spec("track_group_id", "tracks", FieldKind.REFERENCE, reference="track_groups", optional=True),
    _spec(
        "chainage_map.start_km",
        "tracks",
        FieldKind.NUMBER,
        step=0.1,
        advanced=True,
    ),
    _spec(
        "chainage_map.end_km",
        "tracks",
        FieldKind.NUMBER,
        step=0.1,
        advanced=True,
    ),
    _spec(
        "geometry_source",
        "tracks",
        FieldKind.ENUM,
        enum=model_enums.GeometrySource,
        advanced=True,
    ),
    _spec(
        "elevation_source",
        "tracks",
        FieldKind.ENUM,
        enum=model_enums.ElevationSource,
        advanced=True,
    ),
)

_HORIZONTAL_GEOMETRY: tuple[FieldSpec, ...] = (
    _spec("id", "horizontal_geometry", FieldKind.ID),
    _spec("alignment_id", "horizontal_geometry", FieldKind.REFERENCE, reference="alignments"),
    _spec("start_chainage_km", "horizontal_geometry", FieldKind.NUMBER, step=0.1),
    _spec("end_chainage_km", "horizontal_geometry", FieldKind.NUMBER, step=0.1),
    _spec("type", "horizontal_geometry", FieldKind.ENUM, enum=model_enums.GeometrySectionType),
    _spec("radius_m", "horizontal_geometry", FieldKind.NUMBER, step=50.0, optional=True),
    _spec("handedness", "horizontal_geometry", FieldKind.ENUM, enum=model_enums.Handedness, optional=True),
)

_SPEED_RESTRICTION: tuple[FieldSpec, ...] = (
    _spec("id", "speed_restrictions", FieldKind.ID),
    _spec("name", "speed_restrictions", FieldKind.TEXT, optional=True),
    _spec("alignment_id", "speed_restrictions", FieldKind.REFERENCE, reference="alignments"),
    _spec("start_chainage_km", "speed_restrictions", FieldKind.NUMBER, step=0.1),
    _spec("end_chainage_km", "speed_restrictions", FieldKind.NUMBER, step=0.1),
    _spec("speed_kmh", "speed_restrictions", FieldKind.NUMBER, step=10.0, minimum=0.0),
    _spec("direction", "speed_restrictions", FieldKind.ENUM, enum=model_enums.Direction),
    _spec("type", "speed_restrictions", FieldKind.ENUM, enum=model_enums.SpeedRestrictionType),
)

_STATION: tuple[FieldSpec, ...] = (
    _spec("id", "stations", FieldKind.ID),
    _spec("name", "stations", FieldKind.TEXT, optional=True),
    _spec("type", "stations", FieldKind.ENUM, enum=model_enums.StationType),
    _spec("reference_chainage_km", "stations", FieldKind.NUMBER, step=0.1),
    _spec("platform_ids", "stations", FieldKind.ID_LIST, reference="platforms"),
)

_PLATFORM: tuple[FieldSpec, ...] = (
    _spec("id", "platforms", FieldKind.ID),
    _spec("station_id", "platforms", FieldKind.REFERENCE, reference="stations"),
    _spec("track_id", "platforms", FieldKind.REFERENCE, reference="tracks"),
    _spec("usable_start_m", "platforms", FieldKind.NUMBER, step=5.0, minimum=0.0),
    _spec("usable_end_m", "platforms", FieldKind.NUMBER, step=5.0, minimum=0.0),
    _spec("usable_length_m", "platforms", FieldKind.NUMBER, step=5.0, minimum=0.0),
    _spec("directionality", "platforms", FieldKind.ENUM, enum=model_enums.Directionality),
    _spec(
        "platform_track_speed_kmh",
        "platforms",
        FieldKind.NUMBER,
        step=10.0,
        optional=True,
    ),
    _spec("resource_id", "platforms", FieldKind.TEXT, optional=True, advanced=True),
    _spec("stopping_mark_ids", "platforms", FieldKind.ID_LIST, reference="stopping_marks", advanced=True),
)

_STOPPING_MARK: tuple[FieldSpec, ...] = (
    _spec("id", "stopping_marks", FieldKind.ID),
    _spec("platform_id", "stopping_marks", FieldKind.REFERENCE, reference="platforms"),
    _spec("track_id", "stopping_marks", FieldKind.REFERENCE, reference="tracks"),
    _spec("direction", "stopping_marks", FieldKind.ENUM, enum=model_enums.Direction),
    _spec("position_m", "stopping_marks", FieldKind.NUMBER, step=5.0, minimum=0.0),
    _spec(
        "marker_type",
        "stopping_marks",
        FieldKind.ENUM,
        enum=model_enums.StoppingMarkerType,
        advanced=True,
    ),
)

_OBSERVATION_POINT: tuple[FieldSpec, ...] = (
    _spec("id", "observation_points", FieldKind.ID),
    _spec("name", "observation_points", FieldKind.TEXT, optional=True),
    _spec("type", "observation_points", FieldKind.ENUM, enum=model_enums.ObservationPointType),
    _spec("station_id", "observation_points", FieldKind.REFERENCE, reference="stations", optional=True),
    _spec("event", "observation_points", FieldKind.ENUM, enum=model_enums.ServiceEventType, optional=True),
    _spec("platform_id", "observation_points", FieldKind.REFERENCE, reference="platforms", optional=True, advanced=True),
    _spec("track_id", "observation_points", FieldKind.REFERENCE, reference="tracks", optional=True, advanced=True),
    _spec("position_m", "observation_points", FieldKind.NUMBER, step=5.0, optional=True, advanced=True),
    _spec("node_ids", "observation_points", FieldKind.ID_LIST, reference="nodes", advanced=True),
    _spec("members", "observation_points", FieldKind.MEMBER_LIST, advanced=True),
)

#: Vertical profile points are edited inside the profile row (nested catalogue).
VERTICAL_PROFILE_POINT_FIELDS: tuple[FieldSpec, ...] = (
    _spec("id", "vertical_profile_points", FieldKind.ID),
    _spec("chainage_km", "vertical_profile_points", FieldKind.NUMBER, step=0.1),
    _spec("elevation_m", "vertical_profile_points", FieldKind.NUMBER, step=0.1),
)

_VERTICAL_PROFILE: tuple[FieldSpec, ...] = (
    _spec("id", "vertical_profiles", FieldKind.ID),
    _spec("alignment_id", "vertical_profiles", FieldKind.REFERENCE, reference="alignments"),
    _spec("source_mode", "vertical_profiles", FieldKind.ENUM, enum=model_enums.VerticalProfileSourceMode),
)

#: Editable fields per catalogue (editor column order).
EDITOR_FIELDS: dict[str, tuple[FieldSpec, ...]] = {
    "alignments": _ALIGNMENT,
    "track_groups": _TRACK_GROUP,
    "nodes": _NODE,
    "tracks": _TRACK,
    "horizontal_geometry": _HORIZONTAL_GEOMETRY,
    "vertical_profiles": _VERTICAL_PROFILE,
    "vertical_profile_points": VERTICAL_PROFILE_POINT_FIELDS,
    "speed_restrictions": _SPEED_RESTRICTION,
    "stations": _STATION,
    "platforms": _PLATFORM,
    "stopping_marks": _STOPPING_MARK,
    "observation_points": _OBSERVATION_POINT,
}

#: Default values used when adding a row in STANDARD mode.
DEFAULT_VALUES: dict[str, dict[str, Any]] = {
    "alignments": {"start_chainage_km": 0.0, "end_chainage_km": 1.0},
    "track_groups": {"directionality": "BOTH"},
    "nodes": {"type": "SWITCH", "chainage_km": 0.0},
    "tracks": {"length_m": 100.0, "directionality": "BOTH", "chainage_map.start_km": 0.0, "chainage_map.end_km": 0.1},
    "horizontal_geometry": {"start_chainage_km": 0.0, "end_chainage_km": 1.0, "type": "STRAIGHT"},
    "vertical_profiles": {"source_mode": "ELEVATION_POINTS", "points": []},
    "vertical_profile_points": {"chainage_km": 0.0, "elevation_m": 0.0},
    "speed_restrictions": {
        "start_chainage_km": 0.0,
        "end_chainage_km": 1.0,
        "speed_kmh": 100.0,
        "direction": "BOTH",
        "type": "PERMANENT",
    },
    "stations": {"type": "INTERMEDIATE", "reference_chainage_km": 0.0, "platform_ids": []},
    "platforms": {
        "usable_start_m": 0.0,
        "usable_end_m": 100.0,
        "usable_length_m": 100.0,
        "directionality": "BOTH",
        "stopping_mark_ids": [],
    },
    "stopping_marks": {"direction": "FORWARD", "position_m": 0.0, "marker_type": "EXPLICIT"},
    "observation_points": {"type": "CROSS_SECTION", "node_ids": [], "members": []},
}

#: Identifier prefix used when a new row is created from the UI (user editable).
ID_PREFIXES: dict[str, str] = {
    "alignments": "ALN",
    "track_groups": "TG",
    "nodes": "N",
    "tracks": "TR",
    "horizontal_geometry": "HGR",
    "vertical_profiles": "VP",
    "vertical_profile_points": "VPP",
    "speed_restrictions": "SPR",
    "stations": "STA",
    "platforms": "PLT",
    "stopping_marks": "STOP",
    "observation_points": "OBS",
}

#: Fields that are references to another catalogue, and the catalogue they point at.
REFERENCE_TARGETS: dict[str, dict[str, str]] = {
    catalogue: {spec.name: spec.reference for spec in fields if spec.reference is not None}
    for catalogue, fields in EDITOR_FIELDS.items()
}


def fields_of(catalogue: str, *, mode: str = "STANDARD") -> tuple[FieldSpec, ...]:
    """Return the visible fields of a catalogue for the given editor mode."""
    fields = EDITOR_FIELDS[catalogue]
    if mode.upper() == "STANDARD":
        return tuple(spec for spec in fields if not spec.advanced)
    return fields


def headers_of(catalogue: str, *, mode: str = "STANDARD") -> tuple[str, ...]:
    """Return the column headers (with unit suffixes) for the given mode."""
    return tuple(spec.header for spec in fields_of(catalogue, mode=mode))


def spec_of(catalogue: str, field_name: str) -> Optional[FieldSpec]:
    """Return the specification of one field (``None`` when it is not editable)."""
    for spec in EDITOR_FIELDS.get(catalogue, ()):
        if spec.name == field_name:
            return spec
    return None


def all_engineering_fields() -> tuple[tuple[str, str], ...]:
    """Return every ``(catalogue, field)`` pair that carries a unit suffix."""
    pairs: list[tuple[str, str]] = []
    for catalogue, fields in EDITOR_FIELDS.items():
        for spec in fields:
            if spec.unit:
                pairs.append((catalogue, spec.name))
    return tuple(pairs)


def nested_field_split(field_name: str) -> tuple[str, str]:
    """Split a nested field name such as ``chainage_map.start_km``."""
    head, _, tail = field_name.partition(".")
    return head, tail


@dataclass
class EditorColumn:
    """One rendered editor column (header + provenance + tooltip)."""

    spec: FieldSpec
    derived_text: str = dataclass_field(default="")
