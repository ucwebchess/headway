"""Phase-6A rolling-stock validation: physical validity, reported, never repaired.

Every rule below is a *data* rule about one rolling-stock object. The checks use
the project's existing diagnostic model (:class:`~railway_headway_sim.models.diagnostics.Diagnostic`
and :class:`~railway_headway_sim.models.diagnostics.ValidationResult`, the same
severity enum and the same category mechanism) — there is no parallel result
type — and every finding is an ``ERROR``, so a catalogue that fails any rule is
``INVALID``.

Implemented rules (Stage 6A):

* ``static_mass_t``, ``length_m``, ``max_speed_kmh``,
  ``max_operational_acceleration_mps2``, ``rated_power_kw``,
  ``max_tractive_effort_kn``, ``service_braking.reference_deceleration_mps2`` and
  ``etcs_supervision.reference_deceleration_mps2`` — finite and strictly positive;
* ``rotating_mass_factor`` — finite and at least ``1.0``;
* the three running-resistance coefficients — finite and non-negative;
* ``coefficient_speed_unit`` and ``output_force_unit`` — recognised values;
* ``traction.model`` and ``running_resistance.model`` — recognised values;
* the optional tractive-effort characteristic — at least two points, strictly
  increasing speed, finite non-positive-free effort (a valid strictly increasing
  characteristic is accepted unchanged);
* **any** NaN or ``+/-`` infinity in a numeric field is reported as an ``ERROR``
  naming that field (``VAL-RS-001``).

Nothing is clamped, defaulted, dropped or "fixed": the invalid object is
reported and refused, exactly as the rest of the project treats data problems.
No motion quantity is computed here — the module reads stored numbers only.
"""

from __future__ import annotations

from typing import Any, Optional, Sequence

from ..models.diagnostics import Diagnostic, ValidationResult
from ..models.enums import DiagnosticCategory, Severity
from ..models.rolling_stock import (
    RECOGNISED_COEFFICIENT_SPEED_UNITS,
    RECOGNISED_OUTPUT_FORCE_UNITS,
    RollingStock,
    RollingStockCatalogue,
    RunningResistanceModel,
    TractiveEffortModel,
)
from . import codes
from .infrastructure_support import is_finite_number

#: Lowest accepted rotating-mass allowance (the stored factor is dimensionless).
MIN_ROTATING_MASS_FACTOR = 1.0

#: Fewest points an optional effort characteristic must carry when it is present.
MIN_EFFORT_CHARACTERISTIC_POINTS = 2

_SUGGESTED_ACTION = (
    "Correct the stored value in the rolling-stock catalogue and load it again; "
    "the definition is refused, never repaired."
)


def _diagnostic(
    code: str,
    *,
    object_id: str,
    field: str,
    message: str,
    context: Optional[dict[str, Any]] = None,
) -> Diagnostic:
    """Build one ERROR diagnostic of the rolling-stock category."""
    details: dict[str, Any] = {"field": field}
    if context:
        details.update(context)
    return Diagnostic(
        code=code,
        severity=Severity.ERROR,
        category=DiagnosticCategory.ROLLING_STOCK,
        message=message,
        object_id=object_id,
        context=details,
        suggested_action=_SUGGESTED_ACTION,
    )


def _finite(
    value: Any, *, stock_id: str, field: str, diagnostics: list[Diagnostic]
) -> bool:
    """Report a non-finite (NaN or +/- infinity) number; return ``True`` when finite."""
    if is_finite_number(value):
        return True
    diagnostics.append(
        _diagnostic(
            codes.VAL_RS_001,
            object_id=stock_id,
            field=field,
            message=f"The value of '{field}' must be a finite number; found {value!r}.",
            context={"value": repr(value)},
        )
    )
    return False


def _positive(
    value: Any, *, stock_id: str, field: str, diagnostics: list[Diagnostic]
) -> None:
    """Report a value that is not finite and strictly positive."""
    if not _finite(value, stock_id=stock_id, field=field, diagnostics=diagnostics):
        return
    if value <= 0:
        diagnostics.append(
            _diagnostic(
                codes.VAL_RS_002,
                object_id=stock_id,
                field=field,
                message=f"The value of '{field}' must be greater than 0.0; found {value!r}.",
                context={"value": repr(value), "minimum_exclusive": 0.0},
            )
        )


def _at_least(
    value: Any,
    *,
    stock_id: str,
    field: str,
    minimum: float,
    diagnostics: list[Diagnostic],
) -> None:
    """Report a value that is not finite and at least *minimum*."""
    if not _finite(value, stock_id=stock_id, field=field, diagnostics=diagnostics):
        return
    if value < minimum:
        diagnostics.append(
            _diagnostic(
                codes.VAL_RS_003,
                object_id=stock_id,
                field=field,
                message=(
                    f"The value of '{field}' must be at least {minimum!r}; found {value!r}."
                ),
                context={"value": repr(value), "minimum_inclusive": minimum},
            )
        )


def _non_negative(
    value: Any, *, stock_id: str, field: str, diagnostics: list[Diagnostic]
) -> None:
    """Report a value that is not finite and non-negative."""
    if not _finite(value, stock_id=stock_id, field=field, diagnostics=diagnostics):
        return
    if value < 0:
        diagnostics.append(
            _diagnostic(
                codes.VAL_RS_004,
                object_id=stock_id,
                field=field,
                message=f"The value of '{field}' must not be negative; found {value!r}.",
                context={"value": repr(value), "minimum_inclusive": 0.0},
            )
        )


def _recognised(
    value: Any,
    *,
    stock_id: str,
    field: str,
    recognised: Sequence[str],
    diagnostics: list[Diagnostic],
) -> None:
    """Report a value that is not one of the recognised values of its enumeration."""
    allowed = tuple(str(item) for item in recognised)
    text = value.value if hasattr(value, "value") else value
    if isinstance(text, str) and text in allowed:
        return
    diagnostics.append(
        _diagnostic(
            codes.VAL_RS_005,
            object_id=stock_id,
            field=field,
            message=(
                f"The value of '{field}' must be one of {', '.join(repr(a) for a in allowed)}; "
                f"found {text!r}."
            ),
            context={"value": repr(text), "recognised": list(allowed)},
        )
    )


def _check_effort_characteristic(stock: RollingStock, prefix: str, diagnostics: list[Diagnostic]) -> None:
    """Validate the optional stored effort/speed characteristic of *stock*."""
    curve = stock.traction.traction_curve
    field = f"{prefix}.traction.traction_curve"
    if curve is None:
        return  # the simplified model is declared; no characteristic to check
    points = list(curve)
    if len(points) < MIN_EFFORT_CHARACTERISTIC_POINTS:
        diagnostics.append(
            _diagnostic(
                codes.VAL_RS_006,
                object_id=stock.id,
                field=field,
                message=(
                    f"The value of '{field}' must carry at least "
                    f"{MIN_EFFORT_CHARACTERISTIC_POINTS} points when it is present; "
                    f"found {len(points)}."
                ),
                context={"points": len(points)},
            )
        )
    previous_speed: Optional[Any] = None
    for index, point in enumerate(points):
        point_field = f"{field}[{index}]"
        speed_field = f"{point_field}.speed_kmh"
        effort_field = f"{point_field}.tractive_effort_kn"
        speed_finite = _finite(
            point.speed_kmh, stock_id=stock.id, field=speed_field, diagnostics=diagnostics
        )
        effort_finite = _finite(
            point.tractive_effort_kn,
            stock_id=stock.id,
            field=effort_field,
            diagnostics=diagnostics,
        )
        if speed_finite and previous_speed is not None and point.speed_kmh <= previous_speed:
            diagnostics.append(
                _diagnostic(
                    codes.VAL_RS_006,
                    object_id=stock.id,
                    field=speed_field,
                    message=(
                        f"The value of '{speed_field}' must be strictly greater than the "
                        f"previous stored speed; {point.speed_kmh!r} does not exceed "
                        f"{previous_speed!r}."
                    ),
                    context={"previous_speed_kmh": repr(previous_speed), "value": repr(point.speed_kmh)},
                )
            )
        if effort_finite and point.tractive_effort_kn <= 0:
            diagnostics.append(
                _diagnostic(
                    codes.VAL_RS_006,
                    object_id=stock.id,
                    field=effort_field,
                    message=(
                        f"The value of '{effort_field}' must be greater than 0.0 kN; "
                        f"found {point.tractive_effort_kn!r}."
                    ),
                    context={"value": repr(point.tractive_effort_kn), "minimum_exclusive": 0.0},
                )
            )
        if speed_finite:
            previous_speed = point.speed_kmh


def _validate_stock(stock: RollingStock, prefix: str) -> list[Diagnostic]:
    """Return every physical-validity diagnostic of one rolling-stock object."""
    diagnostics: list[Diagnostic] = []
    object_id = str(getattr(stock, "id", "") or "<unnamed>")

    _positive(
        stock.mass.static_mass_t,
        stock_id=object_id,
        field=f"{prefix}.mass.static_mass_t",
        diagnostics=diagnostics,
    )
    _at_least(
        stock.mass.rotating_mass_factor,
        stock_id=object_id,
        field=f"{prefix}.mass.rotating_mass_factor",
        minimum=MIN_ROTATING_MASS_FACTOR,
        diagnostics=diagnostics,
    )
    _positive(
        stock.geometry.length_m,
        stock_id=object_id,
        field=f"{prefix}.geometry.length_m",
        diagnostics=diagnostics,
    )
    _positive(
        stock.performance_limits.max_speed_kmh,
        stock_id=object_id,
        field=f"{prefix}.performance_limits.max_speed_kmh",
        diagnostics=diagnostics,
    )
    _positive(
        stock.performance_limits.max_operational_acceleration_mps2,
        stock_id=object_id,
        field=f"{prefix}.performance_limits.max_operational_acceleration_mps2",
        diagnostics=diagnostics,
    )
    _positive(
        stock.traction.rated_power_kw,
        stock_id=object_id,
        field=f"{prefix}.traction.rated_power_kw",
        diagnostics=diagnostics,
    )
    _positive(
        stock.traction.max_tractive_effort_kn,
        stock_id=object_id,
        field=f"{prefix}.traction.max_tractive_effort_kn",
        diagnostics=diagnostics,
    )
    coefficients = stock.running_resistance.coefficients
    for name, value in (("A", coefficients.A), ("B", coefficients.B), ("C", coefficients.C)):
        _non_negative(
            value,
            stock_id=object_id,
            field=f"{prefix}.running_resistance.coefficients.{name}",
            diagnostics=diagnostics,
        )
    _recognised(
        stock.running_resistance.coefficient_speed_unit,
        stock_id=object_id,
        field=f"{prefix}.running_resistance.coefficient_speed_unit",
        recognised=RECOGNISED_COEFFICIENT_SPEED_UNITS,
        diagnostics=diagnostics,
    )
    _recognised(
        stock.running_resistance.output_force_unit,
        stock_id=object_id,
        field=f"{prefix}.running_resistance.output_force_unit",
        recognised=RECOGNISED_OUTPUT_FORCE_UNITS,
        diagnostics=diagnostics,
    )
    _recognised(
        stock.traction.model,
        stock_id=object_id,
        field=f"{prefix}.traction.model",
        recognised=tuple(model.value for model in TractiveEffortModel),
        diagnostics=diagnostics,
    )
    _recognised(
        stock.running_resistance.model,
        stock_id=object_id,
        field=f"{prefix}.running_resistance.model",
        recognised=tuple(model.value for model in RunningResistanceModel),
        diagnostics=diagnostics,
    )
    _positive(
        stock.service_braking.reference_deceleration_mps2,
        stock_id=object_id,
        field=f"{prefix}.service_braking.reference_deceleration_mps2",
        diagnostics=diagnostics,
    )
    _positive(
        stock.etcs_supervision.reference_deceleration_mps2,
        stock_id=object_id,
        field=f"{prefix}.etcs_supervision.reference_deceleration_mps2",
        diagnostics=diagnostics,
    )
    _check_effort_characteristic(stock, prefix, diagnostics)
    return diagnostics


def validate_rolling_stock(stock: RollingStock) -> list[Diagnostic]:
    """Return the physical-validity diagnostics of a single rolling-stock object.

    Field paths are relative to the object (``mass.static_mass_t``,
    ``traction.traction_curve[1].speed_kmh``, …); every diagnostic is an ERROR of
    the ``ROLLING_STOCK`` category and names the offending field. The list is
    returned in the same deterministic order the catalogue form uses (most severe
    first, then by code, object and message).
    """
    return sorted(_validate_stock(stock, "rolling_stock"), key=Diagnostic.sort_key)


def validate_rolling_stock_catalogue(catalogue: RollingStockCatalogue) -> ValidationResult:
    """Validate a whole catalogue and return the project's :class:`ValidationResult`.

    One diagnostic per physical-validity defect, with the object id of the
    offending stock type and the field path ``rolling_stock[i].<block>.<field>``.
    A catalogue with no finding is ``VALID``; any finding makes it ``INVALID``.
    """
    diagnostics: list[Diagnostic] = []
    for index, stock in enumerate(catalogue.rolling_stock):
        diagnostics.extend(_validate_stock(stock, f"rolling_stock[{index}]"))
    return ValidationResult.from_diagnostics(diagnostics)
