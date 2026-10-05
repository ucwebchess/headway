"""Typed physical infrastructure: registry, mapping, static geometry, topology, compiler,
compiled network and route coordinates (Phase 4A).

Layer contract (Phase 2): ``Project.infrastructure`` remains an **array of layer
objects**.  Each layer object keeps the Phase-1 opaque catalogues and adds the typed
catalogues (``alignments``, ``track_groups``, ``horizontal_geometry``,
``vertical_profiles``, ``speed_restrictions``, ``nodes``, ``tracks``, ``stations``,
``platforms``, ``stopping_marks``, ``observation_points``).  All engineering logic
lives in this layer, never in UI callbacks.
"""

from __future__ import annotations

from .compiler import (
    PHYSICAL_DECLARATION_FIELDS,
    CompiledInfrastructure,
    CompiledLayer,
    compile_infrastructure,
)
from .geometry_along_route import (
    ELEVATION_UNIT,
    GRADIENT_UNIT,
    RADIUS_UNIT,
    RouteGeometry,
)
from .compiled_network import (
    DECLARED_TRAVERSALS,
    PATH_EDGES_FIELD,
    PATH_EDGE_ID_FIELD,
    PATH_ID_FIELD,
    PATH_TRAVERSAL_FIELD,
    SUPPORTED_DIRECTIONS,
    CompiledNetwork,
    PathEdgeRef,
    RouteCoordinateError,
    RouteCoordinateSystem,
    RoutePosition,
    RouteSegment,
    compile_network,
    complementary_traversal,
    normalize_direction,
)
from .mapping import (
    CHAINAGE_TOLERANCE_KM,
    ChainageMapError,
    POSITION_TOLERANCE_M,
    chainage_to_edge_position,
    edge_position_to_chainage,
    mapped_position_delta_m,
)
from .registry import (
    DuplicateRegistration,
    EngineeringRegistry,
    OBJECT_TYPE_LABELS,
    RegisteredObject,
    build_registry,
)
from .static_geometry import (
    StaticFootprint,
    compute_static_footprint,
    evaluate_static_footprint,
    traversal_for_direction,
)
from .topology import InfrastructureTopology

__all__ = [
    "CHAINAGE_TOLERANCE_KM",
    "ChainageMapError",
    "CompiledInfrastructure",
    "CompiledLayer",
    "CompiledNetwork",
    "DECLARED_TRAVERSALS",
    "DuplicateRegistration",
    "EngineeringRegistry",
    "InfrastructureTopology",
    "OBJECT_TYPE_LABELS",
    "PATH_EDGES_FIELD",
    "PATH_EDGE_ID_FIELD",
    "PATH_ID_FIELD",
    "PATH_TRAVERSAL_FIELD",
    "PathEdgeRef",
    "ELEVATION_UNIT",
    "GRADIENT_UNIT",
    "RADIUS_UNIT",
    "RouteCoordinateError",
    "RouteCoordinateSystem",
    "RouteGeometry",
    "RoutePosition",
    "RouteSegment",
    "SUPPORTED_DIRECTIONS",
    "PHYSICAL_DECLARATION_FIELDS",
    "POSITION_TOLERANCE_M",
    "RegisteredObject",
    "StaticFootprint",
    "build_registry",
    "chainage_to_edge_position",
    "compile_infrastructure",
    "compile_network",
    "complementary_traversal",
    "compute_static_footprint",
    "evaluate_static_footprint",
    "edge_position_to_chainage",
    "mapped_position_delta_m",
    "normalize_direction",
    "traversal_for_direction",
]
