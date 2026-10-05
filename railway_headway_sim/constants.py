"""Central enums/constants for the Phase-1 canonical project container.

Everything here is *data description only*: no railway engineering value is
computed, derived or defaulted beyond documented schema defaults.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Top-level document layout (schema 1.0)
# ---------------------------------------------------------------------------
SCHEMA_VERSION_FIELD: str = "schema_version"

#: Name of the physical infrastructure section (an array of layer objects).
INFRASTRUCTURE_SECTION: str = "infrastructure"

#: Ordered list of the top-level sections of a schema-1.0 project document.
TOP_LEVEL_SECTIONS: tuple[str, ...] = (
    "schema_version",
    "project",
    "display_units",
    "reference_system",
    "provenance",
    "infrastructure",
    "signalling",
    "rolling_stock",
    "train_paths",
    "services",
    "simulation",
    "analysis",
    "scenarios",
    "reporting",
)

#: Sections that are *array containers*: JSON arrays of objects.
#: Documented schema default for every array container is ``[]``.
CONTAINER_SECTIONS: tuple[str, ...] = (
    "infrastructure",
    "services",
    "scenarios",
)

#: Sections that must be JSON objects. Documented schema default is the empty
#: object of that section: the typed section models apply their own field
#: defaults (``signalling``/``rolling_stock``/``train_paths`` keep their nested
#: arrays empty, ``{}`` for the remaining sections).
OBJECT_SECTIONS: tuple[str, ...] = (
    "project",
    "display_units",
    "reference_system",
    "provenance",
    "signalling",
    "rolling_stock",
    "train_paths",
    "simulation",
    "analysis",
    "reporting",
)

#: Sections summarised with a plain object count on the Project page.
SUMMARY_SECTIONS: tuple[str, ...] = (
    "infrastructure",
    "signalling",
    "rolling_stock",
    "train_paths",
    "services",
    "scenarios",
)

#: Sections that Phase 1 preserves (and counts) but does not validate in depth.
#: Importing such data produces an INFO diagnostic, never a false ERROR.
CONTAINERS_NOT_SEMANTICALLY_VALIDATED: tuple[str, ...] = (
    "infrastructure",
    "signalling",
    "rolling_stock",
    "train_paths",
    "services",
    "scenarios",
)

# ---------------------------------------------------------------------------
# Container element structure (used by duplicate-ID and type diagnostics)
# ---------------------------------------------------------------------------
#: For every container section: the object type of its elements and the nested
#: lists of identified objects it may hold. Example: a ``services`` container is
#: an array of service-group objects, each with ``folder_id`` and a nested
#: ``timetable`` array of service objects.
CONTAINER_ELEMENT_SPEC: dict[str, dict[str, object]] = {
    "infrastructure": {
        "element_type": "infrastructure_layer",
        "nested_lists": {
            "chainages": "chainage",
            "stations": "station",
            "speed_profiles": "speed_profile",
            "gradients": "gradient",
            "curves": "curve",
            "tunnels": "tunnel",
            "bridges": "bridge",
        },
    },
    "signalling": {
        "element_type": "signalling_layer",
        "nested_lists": {"signals": "signal"},
    },
    "rolling_stock": {
        "element_type": "rolling_stock_layer",
        "nested_lists": {"vehicles": "rolling_stock_vehicle"},
    },
    "train_paths": {
        "element_type": "train_paths_layer",
        "nested_lists": {"stop_patterns": "stop_pattern", "paths": "train_path"},
    },
    "services": {
        "element_type": "service_group",
        "nested_lists": {"service_groups": "service_group_item", "timetable": "service"},
    },
    "scenarios": {
        "element_type": "scenario",
        "nested_lists": {},
    },
}

#: Sections whose (nested) objects are checked for identifiers and structure:
#: the array containers plus the object sections that hold identified objects.
IDENTITY_SCAN_SECTIONS: tuple[str, ...] = tuple(CONTAINER_ELEMENT_SPEC)

#: Fields that carry an identifier which must be unique (per field, per type).
IDENTITY_FIELDS: tuple[str, ...] = ("id", "folder_id", "code")

#: Identifier prefixes for objects this application generates itself.
ID_PREFIXES: dict[str, str] = {
    "project": "PRJ",
    "station": "STN",
    "track": "TRK",
    "rolling_stock": "RS",
    "service": "SVC",
}
PROJECT_ID_PREFIX: str = ID_PREFIXES["project"]
DEFAULT_PROJECT_NAME: str = "New Railway Project"

#: Project-type values recognised by schema 1.0 (stored data only; the project
#: type does not change Phase-1 behaviour in any way).
PROJECT_TYPES: tuple[str, ...] = ("TRAIN_RUN_ANALYSIS", "TRAIN_RUN", "TRACK_AND_STATION_CAPACITY")
DEPRECATED_PROJECT_TYPES: dict[str, str] = {
    "TRAIN_RUN": "Use TRAIN_RUN_ANALYSIS (the current schema-1.0 project type value).",
}

# ---------------------------------------------------------------------------
# Display units (presentation preferences only - NOT internal physics units)
# ---------------------------------------------------------------------------
#: Allowed display-unit spellings per unit field. The first entry is the
#: schema default written into new projects.
UNIT_CHOICES: dict[str, tuple[str, ...]] = {
    "chainage": ("km", "m"),
    "track_distance": ("km", "m"),
    "elevation": ("m", "km"),
    "speed": ("km/h", "m/s", "mph"),
    "mass": ("t", "kg"),
    "force": ("kN", "N", "tf"),
    "power": ("kW", "MW", "hp"),
    "time": ("s", "min", "h"),
    "acceleration": ("m/s^2", "m/s2", "km/h/s"),
    "gradient": ("%", "permille"),
    "curve_radius": ("m", "km"),
}

DEFAULT_DISPLAY_UNITS: dict[str, str] = {field: choices[0] for field, choices in UNIT_CHOICES.items()}

#: Default timestep stored in a new project's ``simulation`` container.
#: (Stored data only - no simulation and no time-stepping is performed.)
DEFAULT_SIMULATION_TIME_STEP_S: float = 1.0

# ---------------------------------------------------------------------------
# Serialization / export
# ---------------------------------------------------------------------------
#: Optional, non-canonical metadata block added on top of exported documents.
EXPORT_METADATA_KEY: str = "export_metadata"
FALLBACK_EXPORT_STEM: str = "railway_project"
SAFE_FILENAME_CHARS: str = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
