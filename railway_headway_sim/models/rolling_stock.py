"""Typed rolling-stock catalogue (Phase 6A) — what a train **is**, not what it does.

Stage 6A declares the rolling-stock objects the later stages will consume: the
geometry, masses, performance limits, the tractive-effort characteristic, the
running-resistance model, the curve-resistance source, the service-braking
reference and the ETCS supervision reference of one stock type. It introduces

* **no motion** — no trajectory, no speed envelope, no acceleration, no
  integration, no time step and no dynamics state;
* **no use of the physics utilities** — :mod:`railway_headway_sim.physics` is not
  imported here, and this module computes no force;
* **no UI** — the Rolling Stock page stays a ``PLANNED FOR LATER DEVELOPMENT
  PHASE`` placeholder until Stage 6B.

Conventions (identical to the Phase-2 typed catalogues):

* every numeric field carries its unit in the field name (``_m``, ``_t``,
  ``_kmh``, ``_kw``, ``_kn``, ``_mps2``);
* numbers are JSON-native and strict: strings such as ``"202.0"``, booleans and
  ``None`` are rejected for a numeric field — nothing is coerced;
* unknown extension fields survive everywhere (``extra="allow"`` at every level),
  so a schema-1.x document round-trips without losing forward-compatible keys;
* reading never mutates the source, and nothing is silently repaired: a document
  that cannot be parsed raises :class:`RollingStockError` (a ``ValueError``) with
  a message that names the offending field. Physical validity is a separate,
  reported step (:mod:`railway_headway_sim.validation.rolling_stock_validation`).

Plain-language naming note (Section-D discipline). The five resistance/force
tokens allowed since Stage 5A (``Davis``, ``Roeckl``, ``rolling resistance``,
``curve resistance``, ``gradient force``) may appear in a *declared name* only
inside the ``railway_headway_sim/physics/`` package, and the tokens ``traction``
and ``braking_curve`` are forbidden in a declared name everywhere. The declared
names in this module therefore use plain-language forms
(``RollingStockTractiveEffort``, ``RollingStockRunningResistance``, …); the
natural model names live in the *data* — as the stored field names
(``traction``, ``traction_curve``, ``running_resistance``) and as the
enumeration **values** (``"DAVIS"``, ``"FORCE_THEN_POWER_LIMITED"``) — which the
Section-D scan does not read. No rule was weakened: the scan surface is
unchanged.
"""

from __future__ import annotations

import json
from enum import Enum
from pathlib import Path
from typing import Any, Mapping, Optional

from pydantic import Field, ValidationError

from .base import ContainerBase, Number

__all__ = [
    "BrakingModel",
    "RECOGNISED_COEFFICIENT_SPEED_UNITS",
    "RECOGNISED_OUTPUT_FORCE_UNITS",
    "ROLLING_STOCK_DOCUMENT_KIND",
    "RollingStock",
    "RollingStockCatalogue",
    "RollingStockCategory",
    "RollingStockCurveResistance",
    "RollingStockError",
    "RollingStockEtcsSupervision",
    "RollingStockGeometry",
    "RollingStockMass",
    "RollingStockPerformanceLimits",
    "RollingStockRunningResistance",
    "RollingStockRunningResistanceCoefficients",
    "RollingStockServiceBraking",
    "RollingStockTractiveEffort",
    "RollingStockTractiveEffortPoint",
    "RunningResistanceModel",
    "TractiveEffortModel",
    "load_rolling_stock_catalogue",
]

#: ``document_kind`` of the rolling-stock companion file. The catalogue is data of
#: a document kind of its own: it never touches the frozen project document.
ROLLING_STOCK_DOCUMENT_KIND = "ROLLING_STOCK_CATALOGUE"

#: Speed units recognised for the running-resistance coefficients. The stored
#: coefficients are evaluated with the speed in km/h, which is the convention of
#: the reference catalogue; an unrecognised unit is reported by the validator.
RECOGNISED_COEFFICIENT_SPEED_UNITS: tuple[str, ...] = ("km/h",)

#: Force units recognised for the running-resistance output. kN is the stored
#: unit of the coefficients; an unrecognised unit is reported by the validator.
RECOGNISED_OUTPUT_FORCE_UNITS: tuple[str, ...] = ("kN",)

#: Infinite values are detected without importing a numeric library.
_POSITIVE_INFINITY = float("inf")
_NEGATIVE_INFINITY = float("-inf")


class RollingStockError(ValueError):
    """Raised when a rolling-stock document cannot be parsed into the typed model.

    The message always names the offending field (or the unreadable source). The
    reader never repairs, defaults or drops anything: a document that does not
    parse is refused.
    """


# ---------------------------------------------------------------------------
# enumerations (string-valued, uppercase — the project's stable machine values)
# ---------------------------------------------------------------------------
class RollingStockCategory(str, Enum):
    """Reference category of a stock type (data description only)."""

    HIGH_SPEED_PASSENGER = "HIGH_SPEED_PASSENGER"
    REGIONAL_PASSENGER = "REGIONAL_PASSENGER"


class TractiveEffortModel(str, Enum):
    """How the tractive-effort characteristic is described.

    ``FORCE_THEN_POWER_LIMITED`` is the simplified two-regime description: a
    constant maximum tractive effort up to the speed where the rated power
    limits the effort, and a constant-power regime above it. Stage 6A stores the
    description; it evaluates nothing.
    """

    FORCE_THEN_POWER_LIMITED = "FORCE_THEN_POWER_LIMITED"


class RunningResistanceModel(str, Enum):
    """Model of the speed-dependent running resistance.

    The stored value names the model family of the Stage-5A utility
    (``railway_headway_sim.physics.resistance``); Stage 6A stores the model name,
    the coefficients and the units, and computes no force.
    """

    DAVIS = "DAVIS"


class BrakingModel(str, Enum):
    """Model of the stored service-braking reference."""

    CONSTANT_EQUIVALENT_BRAKE_FORCE = "CONSTANT_EQUIVALENT_BRAKE_FORCE"


# ---------------------------------------------------------------------------
# typed blocks of one rolling-stock object
# ---------------------------------------------------------------------------
class RollingStockGeometry(ContainerBase):
    """Physical envelope of one stock type."""

    length_m: Number = Field(description="Overall train length [m].")


class RollingStockMass(ContainerBase):
    """Static mass and the rotating-mass allowance."""

    static_mass_t: Number = Field(description="Static (standing) mass [t].")
    rotating_mass_factor: Number = Field(
        description=(
            "Rotating-mass allowance: the factor applied to the static mass to "
            "obtain the effective mass for acceleration [1] (>= 1.0)."
        )
    )


class RollingStockPerformanceLimits(ContainerBase):
    """Stored performance limits of one stock type (no envelope is computed)."""

    max_speed_kmh: Number = Field(description="Maximum speed [km/h].")
    max_operational_acceleration_mps2: Number = Field(
        description="Maximum operational acceleration [m/s^2]."
    )


class RollingStockTractiveEffortPoint(ContainerBase):
    """One stored point of an optional tractive-effort characteristic."""

    speed_kmh: Number = Field(description="Speed of the stored point [km/h].")
    tractive_effort_kn: Number = Field(description="Tractive effort of the stored point [kN].")


class RollingStockTractiveEffort(ContainerBase):
    """Tractive-effort description of one stock type.

    ``characteristic`` (stored as ``traction_curve``) is optional: the reference
    catalogue declares no characteristic, so the simplified
    ``FORCE_THEN_POWER_LIMITED`` description is the delivered one.
    """

    model: TractiveEffortModel = Field(description="Stored description of the effort model.")
    rated_power_kw: Number = Field(description="Rated traction power [kW].")
    max_tractive_effort_kn: Number = Field(description="Maximum tractive effort [kN].")
    traction_curve: Optional[list[RollingStockTractiveEffortPoint]] = Field(
        default=None,
        description=("Optional stored effort/speed characteristic [kN, km/h]; None when the "
                     "simplified model is used."),
    )


class RollingStockRunningResistanceCoefficients(ContainerBase):
    """The three stored coefficients of the running-resistance model.

    The coefficients are evaluated with the speed in the unit named by
    ``coefficient_speed_unit`` and return a force in the unit named by
    ``output_force_unit``. Stage 6A stores them; the Stage-5A utility evaluates
    them elsewhere.
    """

    A: Number = Field(description="Speed-independent coefficient [kN].")
    B: Number = Field(description="Linear coefficient [kN per (km/h)].")
    C: Number = Field(description="Quadratic coefficient [kN per (km/h)^2].")


class RollingStockRunningResistance(ContainerBase):
    """Running-resistance description of one stock type."""

    model: RunningResistanceModel = Field(description="Stored resistance model.")
    formula: str = Field(description="Stored formula identifier, e.g. 'A_PLUS_BV_PLUS_CV2'.")
    coefficients: RollingStockRunningResistanceCoefficients = Field(
        description="The three stored coefficients of the model."
    )
    coefficient_speed_unit: str = Field(description="Speed unit of the coefficients, e.g. 'km/h'.")
    output_force_unit: str = Field(description="Force unit of the model output, e.g. 'kN'.")


class RollingStockCurveResistance(ContainerBase):
    """Where the curve-resistance term of this stock type comes from.

    ``PROJECT_DYNAMICS`` means the term is evaluated from the project's stored
    geometry by the delivered physics utility; no curve resistance is stored per
    stock type, and none is computed in Stage 6A.
    """

    model_source: str = Field(description="Source of the curve-resistance term.")


class RollingStockServiceBraking(ContainerBase):
    """Stored service-braking reference of one stock type (no braking is computed)."""

    model: BrakingModel = Field(description="Stored braking description.")
    reference_deceleration_mps2: Number = Field(
        description="Reference service deceleration [m/s^2]."
    )


class RollingStockEtcsSupervision(ContainerBase):
    """Stored ETCS supervision reference of one stock type (no supervision is computed)."""

    reference_deceleration_mps2: Number = Field(
        description="Reference deceleration the supervision is described with [m/s^2]."
    )
    model_role: str = Field(description="Stored role of the reference, e.g. a look-ahead model.")


class RollingStock(ContainerBase):
    """One rolling-stock object of the catalogue (data only — no behaviour).

    The read-only convenience properties below return the SI values the later
    stages consume. They are pure derivations of the stored fields; they call no
    physics function, hold no state and change nothing.
    """

    id: str = Field(description="Stable machine identifier of the stock type.")
    name: str = Field(description="Display name of the stock type.")
    category: RollingStockCategory = Field(description="Stored reference category.")
    data_status: str = Field(description="Provenance/quality marker of the stored values.")
    manufacturer_data: bool = Field(
        default=False, description="True only when the values come from manufacturer data."
    )
    geometry: RollingStockGeometry = Field(description="Physical envelope.")
    mass: RollingStockMass = Field(description="Static mass and rotating-mass allowance.")
    performance_limits: RollingStockPerformanceLimits = Field(description="Stored limits.")
    traction: RollingStockTractiveEffort = Field(description="Stored effort description.")
    running_resistance: RollingStockRunningResistance = Field(
        description="Stored running-resistance description."
    )
    curve_resistance: RollingStockCurveResistance = Field(
        description="Stored source of the curvature term."
    )
    service_braking: RollingStockServiceBraking = Field(
        description="Stored service-braking reference."
    )
    etcs_supervision: RollingStockEtcsSupervision = Field(
        description="Stored supervision reference."
    )

    # -- read-only derived SI values (pure; no physics call, no state) --------
    @property
    def mass_kg(self) -> float:
        """Static mass in kilograms (``static_mass_t * 1000.0``)."""
        return float(self.mass.static_mass_t) * 1000.0

    @property
    def length_m(self) -> float:
        """Overall train length in metres (the stored ``geometry.length_m``)."""
        return float(self.geometry.length_m)

    @property
    def effective_mass_kg(self) -> float:
        """Effective mass for acceleration in kilograms.

        ``static_mass_t * 1000.0 * rotating_mass_factor`` — the static mass in
        kilograms times the stored rotating-mass allowance.
        """
        return float(self.mass.static_mass_t) * 1000.0 * float(self.mass.rotating_mass_factor)

    @property
    def max_speed_kmh(self) -> float:
        """Maximum speed in kilometres per hour (the stored limit)."""
        return float(self.performance_limits.max_speed_kmh)

    @property
    def resistance_a_kn(self) -> float:
        """Speed-independent running-resistance coefficient [kN]."""
        return float(self.running_resistance.coefficients.A)

    @property
    def resistance_b_kn_per_kmh(self) -> float:
        """Linear running-resistance coefficient [kN per (km/h)]."""
        return float(self.running_resistance.coefficients.B)

    @property
    def resistance_c_kn_per_kmh2(self) -> float:
        """Quadratic running-resistance coefficient [kN per (km/h)^2]."""
        return float(self.running_resistance.coefficients.C)


class RollingStockCatalogue(ContainerBase):
    """The rolling-stock companion document: metadata plus the stored stock types."""

    schema_version: str = Field(description="Document schema version, e.g. '1.0'.")
    document_kind: str = Field(description="Document kind, e.g. 'ROLLING_STOCK_CATALOGUE'.")
    project_id: Optional[str] = Field(default=None, description="Owning project identifier.")
    project_file: Optional[str] = Field(default=None, description="Owning project file name.")
    project_file_sha256: Optional[str] = Field(
        default=None, description="SHA-256 of the owning project file as delivered."
    )
    project_canonical_hash: Optional[str] = Field(
        default=None, description="Canonical project hash of the owning project."
    )
    notes: list[str] = Field(default_factory=list, description="Free-text notes (data only).")
    rolling_stock: list[RollingStock] = Field(description="The stored stock types.")


# ---------------------------------------------------------------------------
# reader
# ---------------------------------------------------------------------------
def _format_validation_error(exc: ValidationError) -> str:
    """Return one message per failed field, each naming the field."""
    parts: list[str] = []
    for error in exc.errors():
        location = ".".join(str(part) for part in error.get("loc", ())) or "<document>"
        parts.append(f"{location}: {error.get('msg', 'unknown error')}")
    return "; ".join(parts)


def _loads(text: str, *, source_name: str) -> Any:
    """Parse JSON text into data only (never evaluated, imported or de-serialized)."""
    try:
        return json.loads(text)
    except ValueError as exc:
        raise RollingStockError(
            f"The rolling-stock source '{source_name}' is not valid JSON text: {exc}."
        ) from exc


def _read_file(path: Path) -> Any:
    """Read and parse one JSON file, refusing unreadable or malformed files."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RollingStockError(
            f"The rolling-stock file '{path}' could not be read: {exc}."
        ) from exc
    except UnicodeDecodeError as exc:  # pragma: no cover - decoding failure path
        raise RollingStockError(
            f"The rolling-stock file '{path}' is not UTF-8 text: {exc}."
        ) from exc
    return _loads(text, source_name=str(path))


def _read_source(source: Any) -> Any:
    """Return the parsed document of one of the four accepted source forms."""
    if source is None:
        raise RollingStockError("No rolling-stock source was supplied.")
    if isinstance(source, Mapping):
        return dict(source)
    if isinstance(source, (bytes, bytearray)):
        try:
            text = bytes(source).decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise RollingStockError(
                f"The rolling-stock bytes are not UTF-8 text: {exc}."
            ) from exc
        return _loads(text, source_name="<bytes>")
    if isinstance(source, Path):
        return _read_file(source)
    if isinstance(source, str):
        try:
            return _loads(source, source_name="<text>")
        except RollingStockError:
            candidate = Path(source)
            if "\n" not in source and len(source) < 512 and candidate.is_file():
                return _read_file(candidate)
            raise
    raise RollingStockError(
        f"Unsupported rolling-stock source of type '{type(source).__name__}'; supply a "
        "mapping, JSON text, a file name or a pathlib.Path."
    )


def load_rolling_stock_catalogue(source: Any) -> RollingStockCatalogue:
    """Return the parsed rolling-stock catalogue of *source*.

    ``source`` is one of the four accepted forms:

    * a mapping (already-parsed JSON);
    * a JSON string;
    * a ``str`` naming a file on disk;
    * a :class:`pathlib.Path`.

    Raises :class:`RollingStockError` (a ``ValueError``) on any parse or type
    failure, with a message naming the offending field. The source is never
    mutated, and nothing is repaired or defaulted: physical validity is reported
    separately by
    :func:`railway_headway_sim.validation.rolling_stock_validation.validate_rolling_stock_catalogue`.
    """
    document = _read_source(source)
    if not isinstance(document, Mapping):
        raise RollingStockError(
            "The rolling-stock document must be a JSON object with a 'rolling_stock' list; "
            f"found {type(document).__name__}."
        )
    try:
        return RollingStockCatalogue.model_validate(document)
    except ValidationError as exc:
        raise RollingStockError(
            "The rolling-stock catalogue could not be parsed: " + _format_validation_error(exc)
        ) from exc
