"""Canonical enumerations used across the project model, validation and UI.

All enumerations subclass :class:`str` so that they serialize to their stable
machine values and can be compared with plain strings.
"""

from __future__ import annotations

from enum import Enum


class DataStatus(str, Enum):
    """Lifecycle/quality status of the data inside a project container.

    ``SYNTHETIC`` (added in Phase 2) marks reference/synthetic data that is
    deliberately *not* a real engineering record, e.g. the GRR-01 reference
    project. The value is additive: existing documents are unaffected.
    """

    TEMPLATE = "TEMPLATE"
    DRAFT = "DRAFT"
    ENGINEERING = "ENGINEERING"
    SYNTHETIC = "SYNTHETIC"


class EngineeringStatus(str, Enum):
    """Engineering readiness of the project (not a simulation result).

    ``REFERENCE_ASSUMPTIONS`` (added in Phase 2) marks a reference project whose
    physical data follows documented reference assumptions rather than a
    validated design. The value is additive: existing documents are unaffected.
    """

    PLANNING = "PLANNING"
    VALIDATED = "VALIDATED"
    APPROVED = "APPROVED"
    REFERENCE_ASSUMPTIONS = "REFERENCE_ASSUMPTIONS"


class Direction(str, Enum):
    """Stable machine values for the headway/analysis direction.

    ``track`` holds transport-oriented projects that have no single
    origin->destination direction; Phase 1 accepts and preserves it but does
    not offer it as a headway direction choice in the UI.
    """

    FORWARD = "FORWARD"
    REVERSE = "REVERSE"
    BOTH = "BOTH"  # reserved - not selectable in Phase 1
    TRACK = "TRACK"  # reserved - not selectable in Phase 1


#: Direction values a user may select in the Phase-1 application shell.
SELECTABLE_DIRECTIONS: tuple[Direction, ...] = (Direction.FORWARD, Direction.REVERSE)

#: Every direction value the schema understands.
DIRECTION_VALUES: tuple[str, ...] = tuple(d.value for d in Direction)

#: Values that must not be used as a Phase-1 headway direction.
RESERVED_DIRECTION_VALUES: tuple[str, ...] = (Direction.BOTH.value, Direction.TRACK.value)


class ChainageDirection(str, Enum):
    """Direction in which chainage increases along an infrastructure container."""

    INCREASING_CHAINAGE = "INCREASING_CHAINAGE"
    DECREASING_CHAINAGE = "DECREASING_CHAINAGE"


class ProjectionType(str, Enum):
    """Supported coordinate reference systems (data description only)."""

    X_Y = "X_Y"
    LOCAL_METRIC = "LOCAL_METRIC"
    GAUSS_KRUGER = "GAUSS_KRUGER"
    UTM = "UTM"
    WGS84 = "WGS84"


class CurveRadiusConvention(str, Enum):
    """Convention for the sign/meaning of stored curve radii."""

    SIGNED_LEFT_POSITIVE = "SIGNED_LEFT_POSITIVE"
    ABSOLUTE_WITH_DIRECTION = "ABSOLUTE_WITH_DIRECTION"


class RuleSetTemplate(str, Enum):
    """Placeholder signalling rule-set/standard marker (no logic in Phase 1)."""

    ETCS = "ETCS"


class Severity(str, Enum):
    """Diagnostic severity."""

    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class ValidationStatus(str, Enum):
    """Overall validation status of a project document/state."""

    VALID = "VALID"
    VALID_WITH_WARNINGS = "VALID_WITH_WARNINGS"
    INVALID = "INVALID"


class DiagnosticCategory(str, Enum):
    """Stable diagnostic categories (the middle segment of a diagnostic code).

    ``SCHEMA``..``FUTURE`` are the accepted Phase-1 categories; everything from
    ``INFRASTRUCTURE`` up to ``PHASE2`` was added in Phase 2 (Section AH), and
    ``ROLLING_STOCK`` was added in Phase 6A for the rolling-stock catalogue codes
    (``VAL-RS-*``). The addition is additive: no existing member, value or code
    changed.
    """

    # -- Phase 1 --
    SCHEMA = "SCHEMA"
    PROJECT = "PROJECT"
    REF = "REF"  # reference system (project chainage range / alignment reference)
    DIR = "DIR"
    ID = "ID"
    ENUM = "ENUM"
    UNIT = "UNIT"
    FUTURE = "FUTURE"
    # -- Phase 2 --
    INFRASTRUCTURE = "INFRASTRUCTURE"
    GEOMETRY = "GEOMETRY"
    TOPOLOGY = "TOPOLOGY"
    STATION = "STATION"
    PLATFORM = "PLATFORM"
    STOP = "STOP"
    OBS = "OBS"
    REGISTRY = "REGISTRY"
    GRR = "GRR"
    PHASE2 = "PHASE2"
    # -- Phase 6A --
    ROLLING_STOCK = "ROLLING_STOCK"


# ===========================================================================
# Phase-2 enumerations (typed physical infrastructure)
#
# All values are stable machine strings. Enum values are always selected
# through controlled schema parsing (pydantic), never from a class name taken
# out of untrusted JSON (Section AY).
# ===========================================================================


class Directionality(str, Enum):
    """Physical directionality of a track group, track or platform."""

    FORWARD_ONLY = "FORWARD_ONLY"
    REVERSE_ONLY = "REVERSE_ONLY"
    BOTH = "BOTH"


class GeometrySectionType(str, Enum):
    """Horizontal geometry section type."""

    STRAIGHT = "STRAIGHT"
    CURVE = "CURVE"


class Handedness(str, Enum):
    """Curve handedness (direction of curvature), intrinsic to the alignment."""

    LEFT = "LEFT"
    RIGHT = "RIGHT"


class GeometrySource(str, Enum):
    """How a track's horizontal geometry is obtained."""

    ALIGNMENT = "ALIGNMENT"
    LOCAL_STRAIGHT = "LOCAL_STRAIGHT"
    LOCAL_SYNTHETIC = "LOCAL_SYNTHETIC"


class ElevationSource(str, Enum):
    """How a track's elevation is obtained."""

    ALIGNMENT_MAPPING = "ALIGNMENT_MAPPING"


class VerticalProfileSourceMode(str, Enum):
    """How a vertical profile is defined."""

    ELEVATION_POINTS = "ELEVATION_POINTS"


class SpeedRestrictionType(str, Enum):
    """Baseline speed-restriction types (no temporary-speed logic in Phase 2)."""

    PERMANENT = "PERMANENT"
    PERMANENT_DIRECTIONAL = "PERMANENT_DIRECTIONAL"
    TEMPORARY = "TEMPORARY"


class NodeType(str, Enum):
    """Topology node type."""

    BUFFER_STOP = "BUFFER_STOP"
    SWITCH = "SWITCH"
    CONNECTION = "CONNECTION"
    TRACK_CONNECTION = "TRACK_CONNECTION"
    STATION_BOUNDARY = "STATION_BOUNDARY"


class ChainageMapMode(str, Enum):
    """Track-local position -> chainage mapping mode."""

    LINEAR = "LINEAR"


class StationType(str, Enum):
    """Station type."""

    TERMINAL = "TERMINAL"
    INTERMEDIATE = "INTERMEDIATE"


class StoppingMarkerType(str, Enum):
    """Stopping marker type."""

    EXPLICIT = "EXPLICIT"


class ServiceEventType(str, Enum):
    """Service event recorded by a SERVICE_EVENT observation point."""

    ARRIVAL = "ARRIVAL"
    DEPARTURE = "DEPARTURE"


class ObservationPointType(str, Enum):
    """Observation point type."""

    SERVICE_EVENT = "SERVICE_EVENT"
    CROSS_SECTION = "CROSS_SECTION"
    TRACK_CROSS_SECTION = "TRACK_CROSS_SECTION"


class EdgeTraversal(str, Enum):
    """Traversal orientation of a track relative to its stored orientation.

    Deliberately NOT called FORWARD/REVERSE: the railway travel direction and
    the stored edge orientation are separate concepts (Section P).
    """

    WITH_EDGE = "WITH_EDGE"
    AGAINST_EDGE = "AGAINST_EDGE"


class PhysicalMode(str, Enum):
    """Declared physical-validation mode of an infrastructure layer (Section AH).

    ``LEGACY``  - Phase-1/opaque container data: basic project assurance only.
    ``PHYSICAL``- typed Phase-2 physical infrastructure: full physical checks.
    """

    LEGACY = "LEGACY"
    PHYSICAL = "PHYSICAL"


class ValidationScope(str, Enum):
    """Level of assurance a validation run actually provided (Section AH)."""

    BASIC_PROJECT = "BASIC PROJECT"
    LEGACY_OPAQUE_DATA = "LEGACY OPAQUE DATA"
    PHASE2_PHYSICAL_INFRASTRUCTURE = "PHASE-2 PHYSICAL INFRASTRUCTURE"


#: Selectable directionality values (all three are valid everywhere).
DIRECTIONALITY_VALUES: tuple[str, ...] = tuple(d.value for d in Directionality)
