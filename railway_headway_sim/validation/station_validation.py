"""Phase-2 station, platform, stopping-mark and observation validation.

All checks are static geometry/reference checks (Sections Q/R/S/T). No signalling
resources, no occupation logic and no train dynamics are evaluated.
"""

from __future__ import annotations

from ..infrastructure.compiler import CompiledInfrastructure
from ..infrastructure.mapping import CHAINAGE_TOLERANCE_KM, POSITION_TOLERANCE_M
from ..models.diagnostics import Diagnostic
from ..models.enums import DiagnosticCategory, Severity
from . import codes
from .infrastructure_support import (
    USABLE_LENGTH_TOLERANCE_M,
    incomplete_observation,
    is_finite_number,
    pairs_of,
    reference_alignment,
)


# ---------------------------------------------------------------------------
# stations / platforms / stopping marks / observations
# ---------------------------------------------------------------------------
def _check_stations(compiled: CompiledInfrastructure) -> list[Diagnostic]:
    """Station chainage bounds, platform references and duplicates."""
    diagnostics: list[Diagnostic] = []
    bound_alignment = reference_alignment(compiled)
    for station, path in pairs_of(compiled, "stations"):
        if bound_alignment is not None:
            chainage = float(station.reference_chainage_km)
            if (
                chainage < float(bound_alignment.start_chainage_km) - CHAINAGE_TOLERANCE_KM
                or chainage > float(bound_alignment.end_chainage_km) + CHAINAGE_TOLERANCE_KM
            ):
                diagnostics.append(
                    Diagnostic(
                        code=codes.VAL_STATION_001,
                        severity=Severity.ERROR,
                        category=DiagnosticCategory.STATION,
                        message=(
                            f"Station '{station.id}' reference chainage {station.reference_chainage_km} km "
                            f"lies outside the reference alignment '{bound_alignment.id}'."
                        ),
                        object_id=station.id,
                        context={"field": f"{path}.reference_chainage_km"},
                        suggested_action="Correct the station reference chainage.",
                    )
                )
        seen: dict[str, int] = {}
        for platform_id in station.platform_ids:
            seen[platform_id] = seen.get(platform_id, 0) + 1
        for platform_id, count in sorted(seen.items()):
            if count > 1:
                diagnostics.append(
                    Diagnostic(
                        code=codes.VAL_STATION_003,
                        severity=Severity.ERROR,
                        category=DiagnosticCategory.STATION,
                        message=(
                            f"Station '{station.id}' lists platform '{platform_id}' {count} times."
                        ),
                        object_id=station.id,
                        context={"field": f"{path}.platform_ids", "platform_id": platform_id},
                        suggested_action="Remove the duplicate platform reference.",
                    )
                )
        for platform_id in dict.fromkeys(seen):
            registration = compiled.registry.get(platform_id)
            if registration is None or registration.object_type != "platform":
                diagnostics.append(
                    Diagnostic(
                        code=codes.VAL_STATION_002,
                        severity=Severity.ERROR,
                        category=DiagnosticCategory.STATION,
                        message=(
                            f"Station '{station.id}' references platform '{platform_id}' which is not "
                            "a registered platform."
                        ),
                        object_id=station.id,
                        context={"field": f"{path}.platform_ids", "reference": platform_id},
                        suggested_action="Create the platform or remove the reference.",
                    )
                )
                continue
            if getattr(registration.value, "station_id", None) != station.id:
                diagnostics.append(
                    Diagnostic(
                        code=codes.VAL_STATION_002,
                        severity=Severity.ERROR,
                        category=DiagnosticCategory.STATION,
                        message=(
                            f"Station '{station.id}' references platform '{platform_id}', but that "
                            f"platform declares station_id "
                            f"'{getattr(registration.value, 'station_id', None)}'."
                        ),
                        object_id=station.id,
                        context={
                            "field": f"{path}.platform_ids",
                            "reference": platform_id,
                            "platform_station_id": getattr(registration.value, "station_id", None),
                        },
                        suggested_action="Point the platform and the station at each other consistently.",
                    )
                )
    return diagnostics


def _check_platforms(compiled: CompiledInfrastructure) -> list[Diagnostic]:
    """Platform references, usable ranges and usable-length reconciliation."""
    diagnostics: list[Diagnostic] = []
    for platform, path in pairs_of(compiled, "platforms"):
        if not compiled.registry.has_type_of(platform.station_id, "station"):
            diagnostics.append(
                Diagnostic(
                    code=codes.VAL_PLATFORM_001,
                    severity=Severity.ERROR,
                    category=DiagnosticCategory.PLATFORM,
                    message=(
                        f"Platform '{platform.id}' references station '{platform.station_id}' which is "
                        "not a registered station."
                    ),
                    object_id=platform.id,
                    context={"field": f"{path}.station_id", "reference": platform.station_id},
                    suggested_action="Create the station or correct platform.station_id.",
                )
            )
        track = None
        if not compiled.registry.has_type_of(platform.track_id, "track"):
            diagnostics.append(
                Diagnostic(
                    code=codes.VAL_PLATFORM_002,
                    severity=Severity.ERROR,
                    category=DiagnosticCategory.PLATFORM,
                    message=(
                        f"Platform '{platform.id}' references track '{platform.track_id}' which is not "
                        "a registered track edge."
                    ),
                    object_id=platform.id,
                    context={"field": f"{path}.track_id", "reference": platform.track_id},
                    suggested_action="Create the track or correct platform.track_id.",
                )
            )
        else:
            track = compiled.registry.value_of(platform.track_id)

        start = platform.usable_start_m
        end = platform.usable_end_m
        length = platform.usable_length_m
        for field_name, value in (
            ("usable_start_m", start),
            ("usable_end_m", end),
            ("usable_length_m", length),
        ):
            if not is_finite_number(value):
                diagnostics.append(
                    Diagnostic(
                        code=codes.VAL_PLATFORM_003,
                        severity=Severity.ERROR,
                        category=DiagnosticCategory.PLATFORM,
                        message=(
                            f"Platform '{platform.id}' {field_name} = {value!r} is not a finite number."
                        ),
                        object_id=platform.id,
                        context={"field": f"{path}.{field_name}", "found": value},
                        suggested_action="Provide finite metre values for the usable range.",
                    )
                )
                return diagnostics
        start_value = float(start)
        end_value = float(end)
        length_value = float(length)
        if start_value < -POSITION_TOLERANCE_M:
            diagnostics.append(
                Diagnostic(
                    code=codes.VAL_PLATFORM_003,
                    severity=Severity.ERROR,
                    category=DiagnosticCategory.PLATFORM,
                    message=f"Platform '{platform.id}' usable_start_m = {start} (must be >= 0).",
                    object_id=platform.id,
                    context={"field": f"{path}.usable_start_m", "found": start},
                    suggested_action="Set usable_start_m >= 0.",
                )
            )
        if start_value >= end_value:
            diagnostics.append(
                Diagnostic(
                    code=codes.VAL_PLATFORM_003,
                    severity=Severity.ERROR,
                    category=DiagnosticCategory.PLATFORM,
                    message=(
                        f"Platform '{platform.id}' usable_start_m {start} >= usable_end_m {end}."
                    ),
                    object_id=platform.id,
                    context={"field": f"{path}.usable_end_m"},
                    suggested_action="Set usable_start_m < usable_end_m.",
                )
            )
        if track is not None and end_value > float(track.length_m) + POSITION_TOLERANCE_M:
            diagnostics.append(
                Diagnostic(
                    code=codes.VAL_PLATFORM_003,
                    severity=Severity.ERROR,
                    category=DiagnosticCategory.PLATFORM,
                    message=(
                        f"Platform '{platform.id}' usable_end_m {end} exceeds track "
                        f"'{track.id}' length {track.length_m} m."
                    ),
                    object_id=platform.id,
                    context={
                        "field": f"{path}.usable_end_m",
                        "track_length_m": float(track.length_m),
                    },
                    suggested_action="Keep the usable range inside the physical track.",
                )
            )
        expected_length = end_value - start_value
        if abs(length_value - expected_length) > USABLE_LENGTH_TOLERANCE_M:
            diagnostics.append(
                Diagnostic(
                    code=codes.VAL_PLATFORM_004,
                    severity=Severity.ERROR,
                    category=DiagnosticCategory.PLATFORM,
                    message=(
                        f"Platform '{platform.id}' usable_length_m {length} does not reconcile with "
                        f"usable_end_m - usable_start_m = {expected_length:g} m "
                        f"(tolerance {USABLE_LENGTH_TOLERANCE_M:g} m)."
                    ),
                    object_id=platform.id,
                    context={
                        "field": f"{path}.usable_length_m",
                        "declared_length_m": length_value,
                        "range_length_m": expected_length,
                        "tolerance_m": USABLE_LENGTH_TOLERANCE_M,
                    },
                    suggested_action="Correct usable_length_m or the usable range.",
                )
            )
        seen_marks: dict[str, int] = {}
        for mark_id in platform.stopping_mark_ids:
            seen_marks[mark_id] = seen_marks.get(mark_id, 0) + 1
        for mark_id in dict.fromkeys(seen_marks):
            registration = compiled.registry.get(mark_id)
            if registration is None or registration.object_type != "stopping_mark":
                diagnostics.append(
                    Diagnostic(
                        code=codes.VAL_PLATFORM_005,
                        severity=Severity.ERROR,
                        category=DiagnosticCategory.PLATFORM,
                        message=(
                            f"Platform '{platform.id}' references stopping mark '{mark_id}' which is "
                            "not a registered stopping mark."
                        ),
                        object_id=platform.id,
                        context={"field": f"{path}.stopping_mark_ids", "reference": mark_id},
                        suggested_action="Create the stopping mark or remove the reference.",
                    )
                )
    return diagnostics


def _check_stopping_marks(compiled: CompiledInfrastructure) -> list[Diagnostic]:
    """Marker platform/track consistency and position bounds."""
    diagnostics: list[Diagnostic] = []
    for marker, path in pairs_of(compiled, "stopping_marks"):
        platform = None
        if not compiled.registry.has_type_of(marker.platform_id, "platform"):
            diagnostics.append(
                Diagnostic(
                    code=codes.VAL_STOP_001,
                    severity=Severity.ERROR,
                    category=DiagnosticCategory.STOP,
                    message=(
                        f"Stopping mark '{marker.id}' references platform '{marker.platform_id}' which "
                        "is not a registered platform."
                    ),
                    object_id=marker.id,
                    context={"field": f"{path}.platform_id", "reference": marker.platform_id},
                    suggested_action="Create the platform or correct stopping_mark.platform_id.",
                )
            )
        else:
            platform = compiled.registry.value_of(marker.platform_id)
            if platform.track_id != marker.track_id:
                diagnostics.append(
                    Diagnostic(
                        code=codes.VAL_STOP_002,
                        severity=Severity.ERROR,
                        category=DiagnosticCategory.STOP,
                        message=(
                            f"Stopping mark '{marker.id}' is on track '{marker.track_id}', but platform "
                            f"'{platform.id}' is on track '{platform.track_id}'."
                        ),
                        object_id=marker.id,
                        context={
                            "field": f"{path}.track_id",
                            "marker_track_id": marker.track_id,
                            "platform_track_id": platform.track_id,
                        },
                        suggested_action="Point the marker at the platform track.",
                    )
                )

        track = None
        if not compiled.registry.has_type_of(marker.track_id, "track"):
            diagnostics.append(
                Diagnostic(
                    code=codes.VAL_STOP_005,
                    severity=Severity.ERROR,
                    category=DiagnosticCategory.STOP,
                    message=(
                        f"Stopping mark '{marker.id}' references track '{marker.track_id}' which is not "
                        "a registered track edge."
                    ),
                    object_id=marker.id,
                    context={"field": f"{path}.track_id", "reference": marker.track_id},
                    suggested_action="Create the track or correct stopping_mark.track_id.",
                )
            )
        else:
            track = compiled.registry.value_of(marker.track_id)

        position = marker.position_m
        if not is_finite_number(position):
            diagnostics.append(
                Diagnostic(
                    code=codes.VAL_STOP_003,
                    severity=Severity.ERROR,
                    category=DiagnosticCategory.STOP,
                    message=f"Stopping mark '{marker.id}' position_m = {position!r} is not finite.",
                    object_id=marker.id,
                    context={"field": f"{path}.position_m"},
                    suggested_action="Provide a finite position in metres.",
                )
            )
            continue
        if track is not None:
            position_value = float(position)
            if position_value < -POSITION_TOLERANCE_M or position_value > float(
                track.length_m
            ) + POSITION_TOLERANCE_M:
                diagnostics.append(
                    Diagnostic(
                        code=codes.VAL_STOP_003,
                        severity=Severity.ERROR,
                        category=DiagnosticCategory.STOP,
                        message=(
                            f"Stopping mark '{marker.id}' position_m {position} is outside track "
                            f"'{track.id}' bounds [0, {track.length_m}] m."
                        ),
                        object_id=marker.id,
                        context={"field": f"{path}.position_m", "track_length_m": float(track.length_m)},
                        suggested_action="Place the marker inside the track bounds.",
                    )
                )
        if platform is not None and is_finite_number(position):
            position_value = float(position)
            if (
                position_value < float(platform.usable_start_m) - POSITION_TOLERANCE_M
                or position_value > float(platform.usable_end_m) + POSITION_TOLERANCE_M
            ):
                diagnostics.append(
                    Diagnostic(
                        code=codes.VAL_STOP_004,
                        severity=Severity.ERROR,
                        category=DiagnosticCategory.STOP,
                        message=(
                            f"Stopping mark '{marker.id}' position_m {position} lies outside the usable "
                            f"range of platform '{platform.id}' "
                            f"[{platform.usable_start_m}, {platform.usable_end_m}] m."
                        ),
                        object_id=marker.id,
                        context={
                            "field": f"{path}.position_m",
                            "usable_start_m": float(platform.usable_start_m),
                            "usable_end_m": float(platform.usable_end_m),
                        },
                        suggested_action="Place the marker inside the usable platform range.",
                    )
                )
    return diagnostics


def _check_observation_points(compiled: CompiledInfrastructure) -> list[Diagnostic]:
    """Observation references, member positions and type completeness."""
    diagnostics: list[Diagnostic] = []
    for observation, path in pairs_of(compiled, "observation_points"):
        observation_type = getattr(observation.type, "value", observation.type)
        for index, node_id in enumerate(observation.node_ids):
            if not compiled.registry.has_type_of(node_id, "node"):
                diagnostics.append(
                    Diagnostic(
                        code=codes.VAL_OBS_001,
                        severity=Severity.ERROR,
                        category=DiagnosticCategory.OBS,
                        message=(
                            f"Observation point '{observation.id}' references node '{node_id}' which is "
                            "not a registered topology node."
                        ),
                        object_id=observation.id,
                        context={"field": f"{path}.node_ids[{index}]", "reference": node_id},
                        suggested_action="Create the node or correct the reference.",
                    )
                )
        for index, member in enumerate(observation.members):
            member_path = f"{path}.members[{index}]"
            track = None
            if not compiled.registry.has_type_of(member.track_id, "track"):
                diagnostics.append(
                    Diagnostic(
                        code=codes.VAL_OBS_001,
                        severity=Severity.ERROR,
                        category=DiagnosticCategory.OBS,
                        message=(
                            f"Observation point '{observation.id}' member references track "
                            f"'{member.track_id}' which is not a registered track edge."
                        ),
                        object_id=observation.id,
                        context={"field": f"{member_path}.track_id", "reference": member.track_id},
                        suggested_action="Create the track or correct the member reference.",
                    )
                )
            else:
                track = compiled.registry.value_of(member.track_id)
            if track is not None and is_finite_number(member.position_m):
                position = float(member.position_m)
                if position < -POSITION_TOLERANCE_M or position > float(track.length_m) + POSITION_TOLERANCE_M:
                    diagnostics.append(
                        Diagnostic(
                            code=codes.VAL_OBS_002,
                            severity=Severity.ERROR,
                            category=DiagnosticCategory.OBS,
                            message=(
                                f"Observation point '{observation.id}' member position_m {member.position_m} "
                                f"is outside track '{track.id}' bounds [0, {track.length_m}] m."
                            ),
                            object_id=observation.id,
                            context={
                                "field": f"{member_path}.position_m",
                                "track_length_m": float(track.length_m),
                            },
                            suggested_action="Place the observation member inside the track bounds.",
                        )
                    )
        if observation_type == "TRACK_CROSS_SECTION" and not observation.members:
            diagnostics.append(
                incomplete_observation(observation, path, "TRACK_CROSS_SECTION", "members[]")
            )
        if observation_type == "CROSS_SECTION" and not observation.node_ids:
            diagnostics.append(
                incomplete_observation(observation, path, "CROSS_SECTION", "node_ids[]")
            )
        if observation_type == "SERVICE_EVENT":
            if observation.station_id is None:
                diagnostics.append(
                    incomplete_observation(observation, path, "SERVICE_EVENT", "station_id")
                )
            elif not compiled.registry.has_type_of(observation.station_id, "station"):
                diagnostics.append(
                    Diagnostic(
                        code=codes.VAL_OBS_001,
                        severity=Severity.ERROR,
                        category=DiagnosticCategory.OBS,
                        message=(
                            f"Observation point '{observation.id}' references station "
                            f"'{observation.station_id}' which is not a registered station."
                        ),
                        object_id=observation.id,
                        context={"field": f"{path}.station_id", "reference": observation.station_id},
                        suggested_action="Create the station or correct the reference.",
                    )
                )
            if observation.event is None:
                diagnostics.append(
                    incomplete_observation(observation, path, "SERVICE_EVENT", "event")
                )
    return diagnostics


def validate_stations_and_platforms(compiled: CompiledInfrastructure) -> list[Diagnostic]:
    """Run every station/platform/stopping-mark/observation check."""
    diagnostics: list[Diagnostic] = []
    diagnostics.extend(_check_stations(compiled))
    diagnostics.extend(_check_platforms(compiled))
    diagnostics.extend(_check_stopping_marks(compiled))
    diagnostics.extend(_check_observation_points(compiled))
    return diagnostics
