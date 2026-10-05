"""Typed physical infrastructure models (Phase 2, schema 1.0 catalogues).

Typed objects are built by parsing **each entry individually** (see
:mod:`railway_headway_sim.infrastructure.compiler`): a malformed entry yields a
diagnostic while the remaining entries still compile, and ``InfrastructureLayer``
below is the fully-typed view used for documentation / JSON Schema generation.

These models are *derived views* over the canonical JSON document. The
canonical document stays the source of truth and is never regenerated from
these objects, which is what preserves the Phase-1 guarantees:

* unknown/future fields survive import -> export (``extra="allow"``);
* export is byte-stable and the canonical hash is unchanged by parsing;
* absent/invalid engineering data never raises - it produces diagnostics.

Unit policy (Section G): engineering numeric fields carry explicit unit
suffixes (``*_km``, ``*_m``, ``*_kmh``). ``display_units`` remains a UI/report
preference object and is never used for engineering conversion here.
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import Field

from .base import ContainerBase, Number
from .enums import (
    ChainageMapMode,
    Directionality,
    Direction,
    ElevationSource,
    GeometrySectionType,
    GeometrySource,
    Handedness,
    NodeType,
    ObservationPointType,
    PhysicalMode,
    ServiceEventType,
    SpeedRestrictionType,
    StationType,
    StoppingMarkerType,
    VerticalProfileSourceMode,
)


class ChainageMap(ContainerBase):
    """Track-local position to physical chainage mapping (Phase 2: LINEAR only).

    ``position_m`` 0 maps to ``start_km``; ``position_m == track.length_m`` maps
    to ``end_km``. Straight-line interpolation between the two.
    """

    mode: ChainageMapMode = ChainageMapMode.LINEAR
    start_km: Number
    end_km: Number


class Alignment(ContainerBase):
    """Horizontal alignment reference object."""

    id: str
    name: Optional[str] = None
    start_chainage_km: Number
    end_chainage_km: Number


class TrackGroup(ContainerBase):
    """Group of tracks sharing operational characteristics.

    ``normal_direction`` is an operational/display preference only; it never
    redefines physical directionality (which is ``directionality``).
    """

    id: str
    name: Optional[str] = None
    directionality: Directionality
    normal_direction: Optional[Direction] = None


class HorizontalGeometrySection(ContainerBase):
    """Horizontal geometry section (STRAIGHT or CURVE) on an alignment."""

    id: str
    alignment_id: str
    start_chainage_km: Number
    end_chainage_km: Number
    type: GeometrySectionType
    radius_m: Optional[Number] = None
    handedness: Optional[Handedness] = None


class VerticalProfilePoint(ContainerBase):
    """Single elevation point of a vertical profile."""

    id: str
    chainage_km: Number
    elevation_m: Number


class VerticalProfile(ContainerBase):
    """Vertical profile of an alignment, defined by elevation points."""

    id: str
    alignment_id: str
    source_mode: VerticalProfileSourceMode = VerticalProfileSourceMode.ELEVATION_POINTS
    points: list[VerticalProfilePoint] = Field(default_factory=list)


class SpeedRestriction(ContainerBase):
    """Speed restriction over a chainage range."""

    id: str
    name: Optional[str] = None
    alignment_id: str
    start_chainage_km: Number
    end_chainage_km: Number
    speed_kmh: Number
    direction: Direction
    type: SpeedRestrictionType


class TopologyNode(ContainerBase):
    """Topology node: the only thing that establishes graph connectivity."""

    id: str
    type: NodeType
    chainage_km: Number
    station_id: Optional[str] = None
    name: Optional[str] = None


class Track(ContainerBase):
    """Directed physical track edge between two topology nodes."""

    id: str
    from_node: str
    to_node: str
    length_m: Number
    directionality: Directionality
    track_group_id: Optional[str] = None
    geometry_source: GeometrySource = GeometrySource.ALIGNMENT
    elevation_source: ElevationSource = ElevationSource.ALIGNMENT_MAPPING
    chainage_map: ChainageMap


class Station(ContainerBase):
    """Passenger station (typed in place inside the infrastructure layer)."""

    id: str
    name: Optional[str] = None
    type: StationType
    reference_chainage_km: Number
    platform_ids: list[str] = Field(default_factory=list)


class Platform(ContainerBase):
    """Platform usable range along a physical track.

    ``resource_id`` is preserved as a future reference (signalling/platform
    occupation resources are not implemented in Phase 2 and are deliberately
    NOT resolved).
    """

    id: str
    station_id: str
    track_id: str
    usable_start_m: Number
    usable_end_m: Number
    usable_length_m: Number
    directionality: Directionality
    platform_track_speed_kmh: Optional[Number] = None
    resource_id: Optional[str] = None
    stopping_mark_ids: list[str] = Field(default_factory=list)


class StoppingMark(ContainerBase):
    """Explicit stopping position on a platform track.

    The authoritative location is ``track_id`` + ``position_m``. A mapped
    chainage is derived from the track map and is never authoritative input.
    """

    id: str
    platform_id: str
    track_id: str
    direction: Direction
    position_m: Number
    marker_type: StoppingMarkerType = StoppingMarkerType.EXPLICIT


class ObservationMember(ContainerBase):
    """Track cross-section member: a point on a track."""

    track_id: str
    position_m: Number


class ObservationPoint(ContainerBase):
    """Observation point (service event, node cross-section or track cross-section)."""

    id: str
    name: Optional[str] = None
    type: ObservationPointType
    # SERVICE_EVENT
    station_id: Optional[str] = None
    event: Optional[ServiceEventType] = None
    platform_id: Optional[str] = None
    track_id: Optional[str] = None
    position_m: Optional[Number] = None
    # CROSS_SECTION
    node_ids: list[str] = Field(default_factory=list)
    # TRACK_CROSS_SECTION
    members: list[ObservationMember] = Field(default_factory=list)


#: Catalogue key -> (human label, typed model, registry object type).
#: This is the single controlled mapping used by the compiler, the registry and
#: the UI (never a class name taken from untrusted JSON).
CATALOGUE_SPEC: dict[str, tuple[str, type[ContainerBase], str]] = {
    "alignments": ("Alignments", Alignment, "alignment"),
    "track_groups": ("Track groups", TrackGroup, "track_group"),
    "horizontal_geometry": (
        "Horizontal geometry sections",
        HorizontalGeometrySection,
        "horizontal_geometry_section",
    ),
    "vertical_profiles": ("Vertical profiles", VerticalProfile, "vertical_profile"),
    "speed_restrictions": ("Speed restrictions", SpeedRestriction, "speed_restriction"),
    "nodes": ("Topology nodes", TopologyNode, "node"),
    "tracks": ("Track edges", Track, "track"),
    "stations": ("Stations", Station, "station"),
    "platforms": ("Platforms", Platform, "platform"),
    "stopping_marks": ("Stopping marks", StoppingMark, "stopping_mark"),
    "observation_points": ("Observation points", ObservationPoint, "observation_point"),
}

#: Catalogue key of the nested point list inside vertical profiles.
VERTICAL_PROFILE_POINT_KEY = "points"
VERTICAL_PROFILE_POINT_OBJECT_TYPE = "vertical_profile_point"

#: Phase-2 catalogue keys of an infrastructure layer.
PHASE2_CATALOGUE_KEYS: tuple[str, ...] = tuple(CATALOGUE_SPEC)

#: Phase-1 legacy (opaque) catalogue keys preserved on every layer.
LEGACY_CATALOGUE_KEYS: tuple[str, ...] = (
    "chainages",
    "speed_profiles",
    "gradients",
    "curves",
    "tunnels",
    "bridges",
)

#: Field on an infrastructure layer that declares its physical-validation mode.
PHYSICAL_MODE_FIELD = "physical_mode"


class InfrastructureLayer(ContainerBase):
    """Typed view of one ``infrastructure[*]`` layer object.

    The Phase-2 catalogues live inside the existing layer object next to the
    preserved Phase-1 catalogues (Section F). ``stations`` is typed in place.
    """

    id: str
    name: Optional[str] = None
    physical_mode: PhysicalMode = PhysicalMode.LEGACY

    # -- Phase-2 typed catalogues --
    alignments: list[Alignment] = Field(default_factory=list)
    track_groups: list[TrackGroup] = Field(default_factory=list)
    horizontal_geometry: list[HorizontalGeometrySection] = Field(default_factory=list)
    vertical_profiles: list[VerticalProfile] = Field(default_factory=list)
    speed_restrictions: list[SpeedRestriction] = Field(default_factory=list)
    nodes: list[TopologyNode] = Field(default_factory=list)
    tracks: list[Track] = Field(default_factory=list)
    stations: list[Station] = Field(default_factory=list)
    platforms: list[Platform] = Field(default_factory=list)
    stopping_marks: list[StoppingMark] = Field(default_factory=list)
    observation_points: list[ObservationPoint] = Field(default_factory=list)

    # -- preserved Phase-1 (opaque) catalogues --
    chainages: list[Any] = Field(default_factory=list)
    speed_profiles: list[Any] = Field(default_factory=list)
    gradients: list[Any] = Field(default_factory=list)
    curves: list[Any] = Field(default_factory=list)
    tunnels: list[Any] = Field(default_factory=list)
    bridges: list[Any] = Field(default_factory=list)


def catalogue_label(key: str) -> str:
    """Return the human label of a catalogue key (falls back to the key)."""
    return CATALOGUE_SPEC.get(key, (key, None, None))[0]


def catalogue_object_type(key: str) -> str:
    """Return the registry object type of a catalogue key."""
    return CATALOGUE_SPEC.get(key, (key, None, key))[2]
