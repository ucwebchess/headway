"""Single source of every editor tooltip (Phase-3 §G12).

All help text lives here - no tooltip string is defined in a callback, a page or a
renderer.  Keys are ``(catalogue_key, field_name)``; a lookup falls back to the
field name alone and finally to a generic sentence naming the stored unit.
"""

from __future__ import annotations

from typing import Optional

#: One-line tooltips for every editor field, keyed by ``(catalogue, field)``.
FIELD_HELP: dict[tuple[str, str], str] = {
    # ---------------------------------------------------------------- alignments
    ("alignments", "id"): "Alignment identifier - globally unique engineering object ID.",
    ("alignments", "name"): "Display name of the alignment (not used as a reference key).",
    ("alignments", "start_chainage_km"): "Chainage of the alignment start, in km.",
    ("alignments", "end_chainage_km"): "Chainage of the alignment end, in km; must be greater than the start.",
    # -------------------------------------------------------------- track groups
    ("track_groups", "id"): "Track group identifier - globally unique engineering object ID.",
    ("track_groups", "name"): "Display name of the track group.",
    ("track_groups", "directionality"): "Which travel directions the group carries: FORWARD_ONLY, REVERSE_ONLY or BOTH.",
    ("track_groups", "normal_direction"): "Normal (preferred) running direction of the group: FORWARD or REVERSE.",
    # --------------------------------------------------------------- nodes
    ("nodes", "id"): "Topology node identifier - globally unique engineering object ID.",
    ("nodes", "type"): "Node kind: BUFFER_STOP, SWITCH, CONNECTION, TRACK_CONNECTION or STATION_BOUNDARY.",
    ("nodes", "chainage_km"): "Chainage of the node on the alignment, in km.",
    ("nodes", "station_id"): "Station this node belongs to (optional; must resolve to a station ID).",
    ("nodes", "name"): "Display name of the node.",
    # --------------------------------------------------------------- tracks
    ("tracks", "id"): "Physical track edge identifier - globally unique engineering object ID.",
    ("tracks", "from_node"): "Node at the stored edge start; must resolve to a node ID.",
    ("tracks", "to_node"): "Node at the stored edge end; must resolve to a node ID and differ from from_node.",
    ("tracks", "length_m"): "Physical length of the edge, in m (need not equal the chainage projection).",
    ("tracks", "directionality"): "Travel directions allowed on the edge: FORWARD_ONLY, REVERSE_ONLY or BOTH.",
    ("tracks", "track_group_id"): "Track group the edge belongs to (optional; must resolve to a group ID).",
    ("tracks", "geometry_source"): "Where the edge geometry comes from: ALIGNMENT, LOCAL_STRAIGHT or LOCAL_SYNTHETIC.",
    ("tracks", "elevation_source"): "Where the edge elevation comes from: ALIGNMENT_MAPPING.",
    ("tracks", "chainage_map"): "Chainage mapping of the edge: start_km, end_km (km) and mode (LINEAR).",
    ("tracks", "chainage_map.start_km"): "Alignment chainage at the stored edge start, in km.",
    ("tracks", "chainage_map.end_km"): "Alignment chainage at the stored edge end, in km.",
    ("tracks", "chainage_map.mode"): "Mapping mode of the chainage map; Phase 2/3 stores LINEAR.",
    # ------------------------------------------------- horizontal geometry
    ("horizontal_geometry", "id"): "Geometry section identifier - globally unique engineering object ID.",
    ("horizontal_geometry", "alignment_id"): "Alignment the section lies on; must resolve to an alignment ID.",
    ("horizontal_geometry", "start_chainage_km"): "Chainage where the section starts, in km.",
    ("horizontal_geometry", "end_chainage_km"): "Chainage where the section ends, in km.",
    ("horizontal_geometry", "type"): "Section type: STRAIGHT or CURVE.",
    ("horizontal_geometry", "radius_m"): "Curve radius, in m. Required and > 0 for a CURVE.",
    ("horizontal_geometry", "handedness"): "Curve handedness: LEFT or RIGHT. Required for a CURVE.",
    # ------------------------------------------------- vertical profiles
    ("vertical_profiles", "id"): "Vertical profile identifier - globally unique engineering object ID.",
    ("vertical_profiles", "alignment_id"): "Alignment the profile belongs to; must resolve to an alignment ID.",
    ("vertical_profiles", "source_mode"): "How the profile is defined; Phase 2/3 stores ELEVATION_POINTS.",
    ("vertical_profiles", "points"): "Profile elevation points: a strictly increasing chainage list with unique chainages.",
    ("vertical_profile_points", "id"): "Profile point identifier - globally unique engineering object ID.",
    ("vertical_profile_points", "chainage_km"): "Chainage of the elevation point, in km.",
    ("vertical_profile_points", "elevation_m"): "Terrain elevation at the point, in m.",
    # ------------------------------------------------- speed restrictions
    ("speed_restrictions", "id"): "Speed restriction identifier - globally unique engineering object ID.",
    ("speed_restrictions", "name"): "Display name of the restriction (e.g. a reason code).",
    ("speed_restrictions", "alignment_id"): "Alignment the restriction lies on; must resolve to an alignment ID.",
    ("speed_restrictions", "start_chainage_km"): "Chainage where the restriction starts, in km.",
    ("speed_restrictions", "end_chainage_km"): "Chainage where the restriction ends, in km.",
    ("speed_restrictions", "speed_kmh"): "Permissible speed of the restriction, in km/h; must be greater than 0.",
    ("speed_restrictions", "direction"): "Travel direction the restriction applies to: FORWARD, REVERSE or BOTH.",
    ("speed_restrictions", "type"): "Restriction type: PERMANENT, PERMANENT_DIRECTIONAL or TEMPORARY.",
    # ------------------------------------------------- stations
    ("stations", "id"): "Station identifier - globally unique engineering object ID.",
    ("stations", "name"): "Display name of the station.",
    ("stations", "type"): "Station kind: TERMINAL or INTERMEDIATE.",
    ("stations", "reference_chainage_km"): "Reference chainage of the station on the alignment, in km.",
    ("stations", "platform_ids"): "Platforms of this station, as a comma separated list of platform IDs.",
    # ------------------------------------------------- platforms
    ("platforms", "id"): "Platform identifier - globally unique engineering object ID.",
    ("platforms", "station_id"): "Station the platform belongs to; must resolve to a station ID.",
    ("platforms", "track_id"): "Physical track edge the platform sits on; must resolve to a track ID.",
    ("platforms", "usable_start_m"): "Start of the usable platform length, in m from the track start.",
    ("platforms", "usable_end_m"): "End of the usable platform length, in m from the track start.",
    ("platforms", "usable_length_m"): "Usable platform length, in m; must reconcile with end minus start.",
    ("platforms", "directionality"): "Travel directions served by the platform: FORWARD_ONLY, REVERSE_ONLY or BOTH.",
    ("platforms", "platform_track_speed_kmh"): "Platform track speed, in km/h (optional static value).",
    ("platforms", "resource_id"): "Optional resource reference. Phase 3 stores it; the ID is deliberately not resolved.",
    ("platforms", "stopping_mark_ids"): "Stopping marks of this platform, as a comma separated list of mark IDs.",
    # ------------------------------------------------- stopping marks
    ("stopping_marks", "id"): "Stopping mark identifier - globally unique engineering object ID.",
    ("stopping_marks", "platform_id"): "Platform the mark belongs to; must resolve to a platform ID.",
    ("stopping_marks", "track_id"): "Track the mark sits on; must match the platform track.",
    ("stopping_marks", "direction"): "Travel direction of the stop: FORWARD or REVERSE.",
    ("stopping_marks", "position_m"): "Authoritative mark position on the track, in m from the track start.",
    ("stopping_marks", "marker_type"): "Marker definition kind; Phase 2/3 stores EXPLICIT.",
    # ------------------------------------------------- observation points
    ("observation_points", "id"): "Observation point identifier - globally unique engineering object ID.",
    ("observation_points", "name"): "Display name of the observation point.",
    ("observation_points", "type"): "Observation kind: SERVICE_EVENT, CROSS_SECTION or TRACK_CROSS_SECTION.",
    ("observation_points", "station_id"): "Station of a SERVICE_EVENT observation (must resolve).",
    ("observation_points", "event"): "Service event kind: ARRIVAL or DEPARTURE.",
    ("observation_points", "platform_id"): "Platform of a SERVICE_EVENT observation (optional, must resolve).",
    ("observation_points", "track_id"): "Track of a SERVICE_EVENT observation (optional, must resolve).",
    ("observation_points", "position_m"): "Position on the referenced track, in m from the track start.",
    ("observation_points", "node_ids"): "Cross-section node members, as a comma separated list of node IDs.",
    ("observation_points", "members"): "Track cross-section members: track ID plus position in m per member.",
    # ------------------------------------------------- reference system
    ("reference_system", "alignment_id"): "Alignment the project reference system points at; must resolve.",
    ("reference_system", "chainage_start_km"): "Project chainage origin, in km.",
    ("reference_system", "chainage_end_km"): "Project chainage end, in km.",
    ("reference_system", "chainage_origin_name"): "Terminal name at the chainage origin (FORWARD label).",
    ("reference_system", "chainage_end_name"): "Terminal name at the chainage end (REVERSE label).",
    ("reference_system", "forward_direction"): "Schema-fixed meaning of FORWARD (INCREASING_CHAINAGE) - not editable.",
    ("reference_system", "reverse_direction"): "Schema-fixed meaning of REVERSE (DECREASING_CHAINAGE) - not editable.",
}

#: Field-name fallbacks used when a catalogue has no specific entry.
_FIELD_FALLBACK: dict[str, str] = {
    "id": "Identifier - must be globally unique across the project.",
    "name": "Display name (never used as a reference key).",
    "position_m": "Track-local position, in m from the track start.",
    "length_m": "Physical length, in m.",
    "chainage_km": "Chainage on the alignment, in km.",
    "speed_kmh": "Permitted speed, in km/h.",
}


def field_tooltip(catalogue: str, field: str) -> str:
    """Return the one-line tooltip of an editor field (never empty)."""
    if (catalogue, field) in FIELD_HELP:
        return FIELD_HELP[(catalogue, field)]
    if field in _FIELD_HELP_BY_NAME.get(catalogue, {}):
        return _FIELD_HELP_BY_NAME[catalogue][field]
    if field in _FIELD_FALLBACK:
        return _FIELD_FALLBACK[field]
    return f"{field} as stored in the {catalogue} catalogue."


def reference_system_tooltip(field: str) -> str:
    """Return the tooltip of a reference-system editor field."""
    return field_tooltip("reference_system", field)


def _index_by_name() -> dict[str, dict[str, str]]:
    """Index :data:`FIELD_HELP` by unqualified field name per catalogue."""
    index: dict[str, dict[str, str]] = {}
    for (catalogue, field), text in FIELD_HELP.items():
        if "." in field:
            continue
        index.setdefault(catalogue, {})[field] = text
    return index


_FIELD_HELP_BY_NAME: dict[str, dict[str, str]] = _index_by_name()


def tooltip_for(catalogue: str, field: str) -> str:
    """Alias of :func:`field_tooltip` for readability at call sites."""
    return field_tooltip(catalogue, field)


def has_tooltip(catalogue: str, field: str) -> bool:
    """Return whether an explicit (curated) tooltip exists for the field."""
    return (catalogue, field) in FIELD_HELP


def missing_tooltips(fields: "list[tuple[str, str]]") -> list[tuple[str, str]]:
    """Return the fields without an explicit curated tooltip (used by tests)."""
    return [item for item in fields if not has_tooltip(*item)]


def describe_source(catalogue: str, field: str) -> Optional[str]:
    """Return the stored unit hint of a field, when the tooltip names one."""
    text = field_tooltip(catalogue, field)
    for unit in ("km/h", "km", "m", "‰", "t", "kN", "kW", "s", "m/s²"):
        if f"in {unit}" in text:
            return unit
    return None
