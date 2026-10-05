"""Canonical project model (schema 1.0).

The model is the *source of truth*. The UI is only an editor/consumer of this
data; no engineering state may live exclusively inside widget values.

Design notes
------------
* Every section is a typed Pydantic model so that malformed JSON is reported by
  the validation layer instead of being silently accepted.
* All sections allow extra keys (``extra="allow"``) and are therefore
  forward-compatible: unknown fields written by a future minor schema revision
  survive import -> export unchanged.
* Container sections are JSON **arrays of objects**. Empty container = ``[]``.
* Engineering payloads (station attributes, signal attributes, ...) are kept as
  ``Any`` in Phase 1 on purpose: Phase 1 establishes and preserves the
  container, it does not model railway semantics yet.
* Fields that cannot be parsed cleanly (e.g. a non-string project name) are left
  as ``None`` by the validation layer, which reports a diagnostic instead of
  inventing a value.
"""

from __future__ import annotations

from typing import Any, Iterator, Optional

from pydantic import Field, field_serializer

from ..constants import (
    CONTAINER_ELEMENT_SPEC,
    CONTAINER_SECTIONS,
    DEFAULT_DISPLAY_UNITS,
    DEFAULT_PROJECT_NAME,
    DEFAULT_SIMULATION_TIME_STEP_S,
    IDENTITY_FIELDS,
    IDENTITY_SCAN_SECTIONS,
    PROJECT_ID_PREFIX,
)
from ..version import DEFAULT_PROJECT_SCHEMA_VERSION
from .common import ContainerBase, Number, new_stable_id, utc_now_iso
from .enums import (
    ChainageDirection,
    CurveRadiusConvention,
    DataStatus,
    Direction,
    EngineeringStatus,
    ProjectionType,
    RuleSetTemplate,
)


class ProjectMeta(ContainerBase):
    """``project`` section: identity and lifecycle metadata."""

    id: Optional[str] = None
    name: Optional[str] = None
    project_type: Optional[str] = None
    data_status: Optional[DataStatus] = None
    description: Optional[str] = None
    engineering_status: Optional[EngineeringStatus] = None
    created_utc: Optional[str] = None
    modified_utc: Optional[str] = None


class DisplayUnits(ContainerBase):
    """``display_units`` section: UI/report preferences only.

    These strings never define internal physics units and no conversion is
    performed in Phase 1.
    """

    chainage: Optional[str] = None
    track_distance: Optional[str] = None
    elevation: Optional[str] = None
    speed: Optional[str] = None
    mass: Optional[str] = None
    force: Optional[str] = None
    power: Optional[str] = None
    time: Optional[str] = None
    acceleration: Optional[str] = None
    gradient: Optional[str] = None
    curve_radius: Optional[str] = None


class ReferenceSystem(ContainerBase):
    """``reference_system`` section: chainage/alignment reference of the project."""

    alignment_id: Optional[str] = None
    chainage_start_km: Optional[Number] = None
    chainage_end_km: Optional[Number] = None
    chainage_origin_name: Optional[str] = None
    chainage_end_name: Optional[str] = None
    projection: Optional[ProjectionType] = None
    coordinate_system: Optional[str] = None
    datum: Optional[str] = None
    forward_direction: Optional[ChainageDirection] = None
    reverse_direction: Optional[ChainageDirection] = None
    curve_radius_convention: Optional[CurveRadiusConvention] = None


class ProvenanceContainer(ContainerBase):
    """``provenance`` section: where the project data came from."""

    created_by: Optional[str] = None
    tool_name: Optional[str] = None
    tool_version: Optional[str] = None
    source: Optional[str] = None
    notes: Optional[str] = None


class InfrastructureContainer(ContainerBase):
    """``infrastructure`` section.

    ``infrastructure`` is a JSON array of infrastructure-layer objects; each
    layer may carry the nested arrays listed in
    :data:`~railway_headway_sim.constants.CONTAINER_ELEMENT_SPEC`
    (``chainages``, ``stations``, ``speed_profiles``, ``gradients``, ``curves``,
    ``tunnels``, ``bridges``). Phase 1 stores and counts those objects.
    """


class SignallingContainer(ContainerBase):
    """``signalling`` section (stored and counted; no rules are implemented)."""

    simulation_time_step_s: Optional[Number] = None
    rule_set_template: Optional[RuleSetTemplate] = None
    signals: Optional[list[Any]] = None


class RollingStockContainer(ContainerBase):
    """``rolling_stock`` section (stored and counted; no physics implemented)."""

    trainset_defaults: Optional[dict[str, Any]] = None
    vehicles: Optional[list[Any]] = None


class TrainPathsContainer(ContainerBase):
    """``train_paths`` section: stop patterns and train paths."""

    stop_patterns: Optional[list[Any]] = None
    paths: Optional[list[Any]] = None


class SimulationContainer(ContainerBase):
    """``simulation`` section: run configuration placeholders (no run yet)."""

    time_step_s: Optional[Number] = None
    random_seed: Optional[int] = None
    start_time_s: Optional[Number] = None
    horizon_s: Optional[Number] = None
    notes: Optional[str] = None


class AnalysisContainer(ContainerBase):
    """``analysis`` section: analysis configuration placeholders."""

    notes: Optional[str] = None
    parameters: Optional[dict[str, Any]] = None


class ReportingContainer(ContainerBase):
    """``reporting`` section: report metadata only (no report is generated)."""

    report_title: Optional[str] = None
    author: Optional[str] = None
    organisation: Optional[str] = None
    notes: Optional[str] = None


class Project(ContainerBase):
    """The canonical project document."""

    schema_version: Optional[str] = None

    project: ProjectMeta = Field(default_factory=ProjectMeta)
    display_units: DisplayUnits = Field(default_factory=DisplayUnits)
    reference_system: ReferenceSystem = Field(default_factory=ReferenceSystem)
    provenance: ProvenanceContainer = Field(default_factory=ProvenanceContainer)

    infrastructure: list[Any] = Field(default_factory=list)
    signalling: SignallingContainer = Field(default_factory=SignallingContainer)
    rolling_stock: RollingStockContainer = Field(default_factory=RollingStockContainer)
    train_paths: TrainPathsContainer = Field(default_factory=TrainPathsContainer)
    services: list[Any] = Field(default_factory=list)
    simulation: SimulationContainer = Field(default_factory=SimulationContainer)
    analysis: AnalysisContainer = Field(default_factory=AnalysisContainer)
    scenarios: list[Any] = Field(default_factory=list)
    reporting: ReportingContainer = Field(default_factory=ReportingContainer)

    # -- serialization -----------------------------------------------------
    @field_serializer("schema_version")
    def _serialize_schema_version(self, value: Optional[str]) -> str:
        """Always write a schema version.

        A project can only be built once a supported ``schema_version`` string
        has been seen, so ``None`` is unreachable in practice; the default keeps
        the serializer type-safe.
        """
        return value if value is not None else DEFAULT_PROJECT_SCHEMA_VERSION

    # -- convenience accessors --------------------------------------------
    @property
    def meta(self) -> ProjectMeta:
        """Alias for the ``project`` metadata section."""
        return self.project

    @property
    def units(self) -> DisplayUnits:
        """Alias for the ``display_units`` section."""
        return self.display_units

    @property
    def reference(self) -> ReferenceSystem:
        """Alias for the ``reference_system`` section."""
        return self.reference_system

    # -- factory -----------------------------------------------------------
    @classmethod
    def new(
        cls,
        *,
        project_id: Optional[str] = None,
        name: Optional[str] = None,
        description: str = "",
        chainage_start_km: Number = 0.0,
        chainage_end_km: Number = 100.0,
        origin_name: str = "Origin",
        end_name: str = "Terminus",
        project_type: str = "TRAIN_RUN_ANALYSIS",
        data_status: DataStatus = DataStatus.TEMPLATE,
        engineering_status: EngineeringStatus = EngineeringStatus.PLANNING,
        alignment_id: Optional[str] = None,
    ) -> "Project":
        """Create a minimal, valid schema-1.0 project template."""
        timestamp = utc_now_iso()
        meta = ProjectMeta(
            id=project_id if project_id else new_stable_id(PROJECT_ID_PREFIX),
            name=name if name else DEFAULT_PROJECT_NAME,
            project_type=project_type,
            data_status=data_status,
            description=description,
            engineering_status=engineering_status,
            created_utc=timestamp,
            modified_utc=timestamp,
        )
        reference = ReferenceSystem(
            alignment_id=alignment_id if alignment_id else new_stable_id("ALN"),
            chainage_start_km=chainage_start_km,
            chainage_end_km=chainage_end_km,
            chainage_origin_name=origin_name,
            chainage_end_name=end_name,
            projection=ProjectionType.X_Y,
            coordinate_system="LOCAL",
            datum="LOCAL",
            forward_direction=ChainageDirection.INCREASING_CHAINAGE,
            reverse_direction=ChainageDirection.DECREASING_CHAINAGE,
            curve_radius_convention=CurveRadiusConvention.SIGNED_LEFT_POSITIVE,
        )
        provenance = ProvenanceContainer(
            created_by="Railway Track Headway Simulator",
            tool_name="railway_headway_sim",
            tool_version=None,  # filled by the application layer, never by the model
            source="new_project_template",
            notes="Created from the Phase-1 project template.",
        )
        simulation = SimulationContainer(
            time_step_s=DEFAULT_SIMULATION_TIME_STEP_S,
            random_seed=None,
            start_time_s=0.0,
            horizon_s=None,
            notes="Run configuration placeholder - no run is performed in Phase 1.",
        )
        analysis = AnalysisContainer(
            notes="Analysis configuration placeholder - no analysis is performed in Phase 1.",
            parameters={},
        )
        reporting = ReportingContainer(
            report_title=meta.name,
            author="",
            organisation="",
            notes="Report metadata only - no report is generated in Phase 1.",
        )
        signalling = SignallingContainer(
            simulation_time_step_s=DEFAULT_SIMULATION_TIME_STEP_S,
            rule_set_template=None,
            signals=[],
        )
        return cls(
            schema_version=DEFAULT_PROJECT_SCHEMA_VERSION,
            project=meta,
            display_units=DisplayUnits(**DEFAULT_DISPLAY_UNITS),
            reference_system=reference,
            provenance=provenance,
            infrastructure=[],
            signalling=signalling,
            rolling_stock=RollingStockContainer(trainset_defaults={}, vehicles=[]),
            train_paths=TrainPathsContainer(stop_patterns=[], paths=[]),
            services=[],
            simulation=simulation,
            analysis=analysis,
            scenarios=[],
            reporting=reporting,
        )

    # -- introspection -----------------------------------------------------
    def container(self, section: str) -> list[Any]:
        """Return the raw list of an *array* container section.

        Returns ``[]`` for object sections (``signalling``, ``rolling_stock``,
        ``train_paths``, ...) and for unusable/absent values.
        """
        value = getattr(self, section, None)
        return value if isinstance(value, list) else []

    def section_element_dicts(self, section: str) -> list[tuple[str, dict[str, Any]]]:
        """Return ``(json_path, element)`` pairs for the elements of a section.

        Array containers yield ``section[i]`` per element; object sections yield
        a single pair ``section`` describing the section object itself (its
        nested arrays are reached through ``nested_key`` lookups).
        """
        if section in CONTAINER_SECTIONS:
            return [
                (f"{section}[{index}]", element)
                for index, element in enumerate(self.container(section))
                if isinstance(element, dict)
            ]
        value = getattr(self, section, None)
        if isinstance(value, ContainerBase):
            return [(section, value.model_dump(mode="python"))]
        return []

    def count_nested(self, container: str, nested_key: str) -> int:
        """Count the objects under ``<container>[*].<nested_key>``."""
        total = 0
        for _path, element in self.section_element_dicts(container):
            nested = element.get(nested_key)
            if isinstance(nested, list):
                total += len(nested)
        return total

    def object_count(self, section: str) -> int:
        """Return the number of objects a section holds (documented, no derivation).

        Array containers count their elements; object sections count the objects
        of their known nested arrays (e.g. ``signalling`` -> number of signals).
        """
        if section in CONTAINER_SECTIONS:
            return len(self.container(section))
        spec = CONTAINER_ELEMENT_SPEC.get(section, {})
        nested_lists = dict(spec.get("nested_lists") or {})
        return sum(self.count_nested(section, key) for key in nested_lists)

    def summary_counts(self) -> dict[str, int]:
        """Return the object counts shown on the Project page.

        These are *plain list sizes* of the canonical containers - no derived,
        simulated or calculated quantity appears here.
        """
        counts: dict[str, int] = {}
        counts["Infrastructure layers"] = len(self.container("infrastructure"))
        counts["Chainage points"] = self.count_nested("infrastructure", "chainages")
        counts["Stations"] = self.count_nested("infrastructure", "stations")
        counts["Speed profiles"] = self.count_nested("infrastructure", "speed_profiles")
        counts["Gradients"] = self.count_nested("infrastructure", "gradients")
        counts["Curves"] = self.count_nested("infrastructure", "curves")
        counts["Tunnels"] = self.count_nested("infrastructure", "tunnels")
        counts["Bridges"] = self.count_nested("infrastructure", "bridges")
        counts["Signals"] = self.count_nested("signalling", "signals")
        counts["Rolling stock vehicles"] = self.count_nested("rolling_stock", "vehicles")
        counts["Stop patterns"] = self.count_nested("train_paths", "stop_patterns")
        counts["Train paths"] = self.count_nested("train_paths", "paths")
        counts["Service groups"] = len(self.container("services"))
        counts["Services"] = self.count_nested("services", "timetable")
        counts["Scenarios"] = len(self.container("scenarios"))
        return counts

    def total_object_count(self) -> int:
        """Return the number of identified objects the containers hold."""
        return sum(1 for _ in self.iter_identity_fields())

    def iter_identity_fields(self) -> Iterator[tuple[str, str, str, Any]]:
        """Yield ``(object_type, json_path, field_name, value)`` for identifier fields.

        Only ``id``/``folder_id``/``code`` fields of dictionaries inside the
        sections listed in
        :data:`~railway_headway_sim.constants.IDENTITY_SCAN_SECTIONS` are
        inspected - the same set the duplicate-ID validator reports on. None of
        these values are used as reference keys in Phase 1.
        """
        for section in IDENTITY_SCAN_SECTIONS:
            spec = CONTAINER_ELEMENT_SPEC.get(section, {})
            element_type = str(spec.get("element_type") or section)
            nested_lists = dict(spec.get("nested_lists") or {})
            for path, element in self.section_element_dicts(section):
                yield from self._identity_fields_of(element, element_type, path)
                for nested_key, nested_type in nested_lists.items():
                    nested_items = element.get(nested_key)
                    if not isinstance(nested_items, list):
                        continue
                    for nested_index, nested_item in enumerate(nested_items):
                        if not isinstance(nested_item, dict):
                            continue
                        nested_path = f"{path}.{nested_key}[{nested_index}]"
                        yield from self._identity_fields_of(nested_item, str(nested_type), nested_path)

    @staticmethod
    def _identity_fields_of(obj: dict[str, Any], object_type: str, path: str) -> Iterator[tuple[str, str, str, Any]]:
        for field_name in IDENTITY_FIELDS:
            if field_name in obj:
                yield (object_type, path, field_name, obj[field_name])


def new_project(**kwargs: Any) -> Project:
    """Convenience wrapper around :meth:`Project.new`."""
    return Project.new(**kwargs)


#: Direction values that a project's reference system describes, in UI order.
PROJECT_DIRECTIONS: tuple[Direction, ...] = (Direction.FORWARD, Direction.REVERSE)
