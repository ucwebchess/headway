"""Diagnostic code catalogue (stable, systematic codes).

Code layout: ``VAL-<CATEGORY>-<NNN>``

==================  ========  ==================================================
Code                Severity  Meaning
==================  ========  ==================================================
VAL-SCHEMA-001      ERROR     Document is not parseable JSON text.
VAL-SCHEMA-002      ERROR     JSON structure is malformed (root/field has the
                              wrong JSON type).
VAL-SCHEMA-003      ERROR     ``schema_version`` is missing.
VAL-SCHEMA-004      ERROR     ``schema_version`` is not supported by this build.
VAL-SCHEMA-005      ERROR     Uploaded data could not be decoded as UTF-8 text.
VAL-PROJECT-001     ERROR     ``project.id``/``project.name`` missing or empty.
VAL-PROJECT-002     ERROR     A field with a defined type has a malformed type.
VAL-PROJECT-003     INFO      Standard metadata fields are not supplied.
VAL-PROJECT-004     INFO      Deprecated project-type value in use.
VAL-REF-001         ERROR     ``chainage_end_km`` is not greater than
                              ``chainage_start_km`` (reversed or zero length).
VAL-REF-002         ERROR     Required reference-system information is missing.
VAL-DIR-001         ERROR     Direction value missing or not a supported
                              enumeration value.
VAL-DIR-002         WARNING   Forward and reverse chainage directions are identical.
VAL-ID-001          ERROR     Duplicate identifier of the same object type.
VAL-ID-002          ERROR     Malformed identifier (not a string, or empty).
VAL-ENUM-001        ERROR     Invalid enumeration value.
VAL-UNIT-001        WARNING   Unrecognised display unit string.
VAL-FUTURE-001      INFO      Section was absent and was created with the
                              documented schema default (empty container).
VAL-FUTURE-002      INFO      Section is preserved but not semantically
                              validated in Phase 1.
VAL-INFR-001        ERROR     Infrastructure layer id missing or not unique.
VAL-INFR-002        ERROR     Typed Phase-2 engineering object could not be parsed.
VAL-INFR-003        ERROR     No infrastructure layer present in a physical project.
VAL-INFR-020        WARNING   Legacy opaque record carries an 'id' inside a
                              physical project (preserved, not registered).
VAL-REGISTRY-001    ERROR     Duplicate registered engineering object ID.
VAL-REGISTRY-002    ERROR     Malformed / empty engineering object id.
VAL-REGISTRY-003    ERROR     Reference does not resolve to a registered object.
VAL-GEOM-001..007   ERROR     Horizontal/vertical geometry and speed-range rules.
VAL-TOPO-001..008   ERROR     Node/track/track-group/chainage-map topology rules.
VAL-STATION-001..3  ERROR     Station/platform-reference rules.
VAL-PLATFORM-001..5 ERROR     Platform usable-range and reconciliation rules.
VAL-STOP-001..005   ERROR     Stopping-mark platform/track/position rules.
VAL-OBS-001..003    ERROR     Observation point reference/position rules.
VAL-GRR-001..004    ERROR     GRR-01 reference project inventory rules.
VAL-PHASE-002       ERROR     Incomplete opaque records mixed into a physical
                              project.
VAL-RS-001..006     ERROR     Rolling-stock catalogue physical-validity rules
                              (Phase 6A): non-finite number, non-positive
                              quantity, rotating-mass allowance below 1.0,
                              negative resistance coefficient, unrecognised
                              unit/model value, invalid effort characteristic.
APP-EDIT-002        ERROR     An uncommitted draft is rejected by validation and
                              blocks export until reverted or corrected.
APP-CTRL-001        ERROR     Application precondition failed: no project is
                              loaded.
APP-CTRL-002        ERROR     Application precondition failed: no file selected
                              for import.
==================  ========  ==================================================

The catalogue is documentation plus the single place where codes are defined as
constants, so that later phases can extend it without hunting for literals.
"""

from __future__ import annotations

# -- schema -----------------------------------------------------------------
VAL_SCHEMA_001 = "VAL-SCHEMA-001"
VAL_SCHEMA_002 = "VAL-SCHEMA-002"
VAL_SCHEMA_003 = "VAL-SCHEMA-003"
VAL_SCHEMA_004 = "VAL-SCHEMA-004"
VAL_SCHEMA_005 = "VAL-SCHEMA-005"

# -- project ----------------------------------------------------------------
VAL_PROJECT_001 = "VAL-PROJECT-001"
VAL_PROJECT_002 = "VAL-PROJECT-002"
VAL_PROJECT_003 = "VAL-PROJECT-003"
VAL_PROJECT_004 = "VAL-PROJECT-004"

# -- reference system -------------------------------------------------------
VAL_REF_001 = "VAL-REF-001"
VAL_REF_002 = "VAL-REF-002"

# -- direction --------------------------------------------------------------
VAL_DIR_001 = "VAL-DIR-001"
VAL_DIR_002 = "VAL-DIR-002"

# -- identifiers ------------------------------------------------------------
VAL_ID_001 = "VAL-ID-001"
VAL_ID_002 = "VAL-ID-002"

# -- enumerations / units ---------------------------------------------------
VAL_ENUM_001 = "VAL-ENUM-001"
VAL_UNIT_001 = "VAL-UNIT-001"

# -- forward-compatibility / later phases -----------------------------------
VAL_FUTURE_001 = "VAL-FUTURE-001"
VAL_FUTURE_002 = "VAL-FUTURE-002"

# ---------------------------------------------------------------------------
# Phase 2 - infrastructure / geometry / topology / station / platform / stop
# All Phase-2 codes are new subseries; no accepted Phase-1 code is renumbered.
# ---------------------------------------------------------------------------
# infrastructure container
VAL_INFR_001 = "VAL-INFR-001"  # infrastructure layer id missing / not unique
VAL_INFR_002 = "VAL-INFR-002"  # typed engineering object could not be parsed
VAL_INFR_003 = "VAL-INFR-003"  # no infrastructure layer present (physical project)
VAL_INFR_020 = "VAL-INFR-020"  # legacy opaque record carries an 'id' in a physical project

# global engineering registry
VAL_REGISTRY_001 = "VAL-REGISTRY-001"  # globally duplicated engineering object ID
VAL_REGISTRY_002 = "VAL-REGISTRY-002"  # malformed / empty engineering object ID
VAL_REGISTRY_003 = "VAL-REGISTRY-003"  # reference does not resolve to a registered object

# horizontal / vertical geometry
VAL_GEOM_001 = "VAL-GEOM-001"  # curve without a usable radius_m
VAL_GEOM_002 = "VAL-GEOM-002"  # geometry section outside its alignment / invalid range
VAL_GEOM_003 = "VAL-GEOM-003"  # overlapping geometry sections on one alignment
VAL_GEOM_004 = "VAL-GEOM-004"  # incomplete / gapped geometry coverage
VAL_GEOM_005 = "VAL-GEOM-005"  # vertical profile point ordering / duplicate chainage
VAL_GEOM_006 = "VAL-GEOM-006"  # vertical profile too short / unusable source mode
VAL_GEOM_007 = "VAL-GEOM-007"  # speed restriction out of range / invalid speed

# topology
VAL_TOPO_001 = "VAL-TOPO-001"  # edge references an unknown node
VAL_TOPO_002 = "VAL-TOPO-002"  # degenerate edge (same node at both ends)
VAL_TOPO_003 = "VAL-TOPO-003"  # non-positive edge length
VAL_TOPO_004 = "VAL-TOPO-004"  # invalid chainage mapping (mode / range / alignment)
VAL_TOPO_005 = "VAL-TOPO-005"  # edge references an unknown track group
VAL_TOPO_006 = "VAL-TOPO-006"  # node references an unknown station
VAL_TOPO_007 = "VAL-TOPO-007"  # disconnected infrastructure / edge sequence break
VAL_TOPO_008 = "VAL-TOPO-008"  # Phase-1 chainages[] inconsistent with Track.chainage_map

# stations
VAL_STATION_001 = "VAL-STATION-001"  # station reference chainage outside the alignment
VAL_STATION_002 = "VAL-STATION-002"  # station references an unknown / foreign platform
VAL_STATION_003 = "VAL-STATION-003"  # duplicate platform reference inside one station

# platforms
VAL_PLATFORM_001 = "VAL-PLATFORM-001"  # platform references an unknown station
VAL_PLATFORM_002 = "VAL-PLATFORM-002"  # platform references an unknown track
VAL_PLATFORM_003 = "VAL-PLATFORM-003"  # usable range invalid or outside the track
VAL_PLATFORM_004 = "VAL-PLATFORM-004"  # usable_length_m does not reconcile with the range
VAL_PLATFORM_005 = "VAL-PLATFORM-005"  # platform references an unknown stopping mark

# stopping marks
VAL_STOP_001 = "VAL-STOP-001"  # marker references an unknown platform
VAL_STOP_002 = "VAL-STOP-002"  # marker track does not match the platform track
VAL_STOP_003 = "VAL-STOP-003"  # marker position outside the physical track
VAL_STOP_004 = "VAL-STOP-004"  # marker position outside the usable platform range
VAL_STOP_005 = "VAL-STOP-005"  # marker references an unknown track

# observation points
VAL_OBS_001 = "VAL-OBS-001"  # observation references an unknown / mismatched object
VAL_OBS_002 = "VAL-OBS-002"  # observation track position outside the track
VAL_OBS_003 = "VAL-OBS-003"  # observation point definition incomplete for its type

# GRR-01 reference project
VAL_GRR_001 = "VAL-GRR-001"  # GRR object count mismatch
VAL_GRR_002 = "VAL-GRR-002"  # GRR regional count mismatch
VAL_GRR_003 = "VAL-GRR-003"  # approved amendment not recorded
VAL_GRR_004 = "VAL-GRR-004"  # GRR infrastructure layer structure mismatch

# Phase-2 policy
VAL_PHASE_002 = "VAL-PHASE-002"  # opaque records mixed into a physical project

# ---------------------------------------------------------------------------
# Phase-6A codes (rolling-stock catalogue, physical-validity rules)
#
# One code per *kind* of defect; the offending field is named in the diagnostic
# message and in its ``context["field"]``. Nothing is auto-corrected: every rule
# reports, and the catalogue is INVALID while any ERROR is present.
# ---------------------------------------------------------------------------
#: A numeric field is not a finite number (NaN or +/- infinity).
VAL_RS_001 = "VAL-RS-001"
#: A numeric field is not strictly greater than zero (mass, length, speeds, power,
#: maximum effort, accelerations and reference decelerations).
VAL_RS_002 = "VAL-RS-002"
#: A numeric field is below its documented lower bound (rotating-mass factor < 1.0).
VAL_RS_003 = "VAL-RS-003"
#: A numeric field must not be negative (the running-resistance coefficients).
VAL_RS_004 = "VAL-RS-004"
#: A field does not carry one of the recognised values of its enumeration (unit or
#: model value).
VAL_RS_005 = "VAL-RS-005"
#: The optional tractive-effort characteristic is not a valid strictly increasing
#: curve (fewer than two points, non-increasing speed, non-positive effort).
VAL_RS_006 = "VAL-RS-006"

#: Phase-6A diagnostic codes (rolling-stock catalogue), in code order.
PHASE6A_DIAGNOSTIC_CODES: tuple[str, ...] = (
    VAL_RS_001,
    VAL_RS_002,
    VAL_RS_003,
    VAL_RS_004,
    VAL_RS_005,
    VAL_RS_006,
)

# ---------------------------------------------------------------------------
# application-level codes (controller/UI pre-conditions, never schema findings)
# ---------------------------------------------------------------------------
APP_EDIT_002 = "APP-EDIT-002"  # uncommitted draft rejected by validation blocks export
#: No project is loaded, so the requested action cannot run.
APP_CTRL_001 = "APP-CTRL-001"
#: No file was selected in the import widget.
APP_CTRL_002 = "APP-CTRL-002"

APPLICATION_CODES: tuple[str, ...] = (APP_CTRL_001, APP_CTRL_002, APP_EDIT_002)

#: Phase-2 code families (used by documentation and tests).
PHASE2_CODE_FAMILIES: tuple[str, ...] = (
    "VAL-INFR-",
    "VAL-REGISTRY-",
    "VAL-GEOM-",
    "VAL-TOPO-",
    "VAL-STATION-",
    "VAL-PLATFORM-",
    "VAL-STOP-",
    "VAL-OBS-",
    "VAL-GRR-",
    "VAL-PHASE-",
    "APP-EDIT-",
)

#: Phase-2 diagnostic codes, in family order.
PHASE2_DIAGNOSTIC_CODES: tuple[str, ...] = (
    VAL_INFR_001,
    VAL_INFR_002,
    VAL_INFR_003,
    VAL_INFR_020,
    VAL_REGISTRY_001,
    VAL_REGISTRY_002,
    VAL_REGISTRY_003,
    VAL_GEOM_001,
    VAL_GEOM_002,
    VAL_GEOM_003,
    VAL_GEOM_004,
    VAL_GEOM_005,
    VAL_GEOM_006,
    VAL_GEOM_007,
    VAL_TOPO_001,
    VAL_TOPO_002,
    VAL_TOPO_003,
    VAL_TOPO_004,
    VAL_TOPO_005,
    VAL_TOPO_006,
    VAL_TOPO_007,
    VAL_TOPO_008,
    VAL_STATION_001,
    VAL_STATION_002,
    VAL_STATION_003,
    VAL_PLATFORM_001,
    VAL_PLATFORM_002,
    VAL_PLATFORM_003,
    VAL_PLATFORM_004,
    VAL_PLATFORM_005,
    VAL_STOP_001,
    VAL_STOP_002,
    VAL_STOP_003,
    VAL_STOP_004,
    VAL_STOP_005,
    VAL_OBS_001,
    VAL_OBS_002,
    VAL_OBS_003,
    VAL_GRR_001,
    VAL_GRR_002,
    VAL_GRR_003,
    VAL_GRR_004,
    VAL_PHASE_002,
)

# ---------------------------------------------------------------------------
# Regression-ID map (Section AR)
#
# The accepted Phase-1 suite uses descriptive pytest function names, not
# ``VAL-REG-*``/``IO-REG-*`` style identifiers. The first entries below map the
# regression identifiers named by the Phase-2 brief onto the accepted test node
# IDs, so the mapping is explicit and auditable. The alias entries are the
# frozen Phase-2 regression aliases for the superseded Phase-1 assertion split.
# ---------------------------------------------------------------------------
#: All codes defined by this build (used by tests to prove codes are stable).
ALL_DIAGNOSTIC_CODES: tuple[str, ...] = (
    VAL_SCHEMA_001,
    VAL_SCHEMA_002,
    VAL_SCHEMA_003,
    VAL_SCHEMA_004,
    VAL_SCHEMA_005,
    VAL_PROJECT_001,
    VAL_PROJECT_002,
    VAL_PROJECT_003,
    VAL_PROJECT_004,
    VAL_REF_001,
    VAL_REF_002,
    VAL_DIR_001,
    VAL_DIR_002,
    VAL_ID_001,
    VAL_ID_002,
    VAL_ENUM_001,
    VAL_UNIT_001,
    VAL_FUTURE_001,
    VAL_FUTURE_002,
    *PHASE2_DIAGNOSTIC_CODES,
    APP_EDIT_002,
    *PHASE6A_DIAGNOSTIC_CODES,
)

#: Code prefix used by every validation diagnostic.
VALIDATION_CODE_PREFIX = "VAL-"

PHASE1_TEST_ID_ALIASES: dict[str, str] = {
    "VAL-REG-011": "railway_headway_sim/tests/test_validation.py::test_duplicate_identifiers_are_reported_per_object_type (2nd half)",
    "UI-REG-009": "railway_headway_sim/tests/test_ui_shell.py::test_placeholder_pages_do_not_implement_engineering_calculations",
}

#: Alias codes recorded for the two deliberate supersessions of Phase 1.
VAL_REG_011 = "VAL-REG-011"
UI_REG_009 = "UI-REG-009"
