"""Phase-6B — the two effort/resistance series a plot consumes, from a stored stock type.

The Rolling Stock page draws two curves per stock type: the tractive-effort curve and
the running-resistance curve, both as functions of speed. This module produces exactly
those two point series from a :class:`~railway_headway_sim.models.rolling_stock.RollingStock`
instance, so the user interface renders numbers the physics package produced instead of
computing anything of its own.

Both functions are pure: they hold no state, read no file, write nothing, depend on no
clock, no environment and no randomness, and each call returns a fresh tuple. Neither
advances a train — the speed is a sampled argument, not an evolved quantity, and no
trajectory, acceleration, integration step or time exists here.

The series are *sampled* for display:

* ``0.0``, ``step_kmh``, ``2 * step_kmh``, … while the sampled speed stays below the
  stock's maximum speed, and then the stock's maximum speed itself — so the last point
  is exactly ``stock.max_speed_kmh`` even when the step does not divide it, and the
  series always carries at least the two endpoints;
* the effort series delegates to :func:`railway_headway_sim.physics.tractive_effort.tractive_effort_n`
  and the resistance series to
  :func:`railway_headway_sim.physics.resistance.davis_resistance_n` over the stock's own
  three coefficients — every sample equals a direct call of the primitive at the same
  speed bit-for-bit, because nothing is rounded, interpolated or smoothed here.

Stored data is never repaired: a stock type whose stored maximum speed or coefficients
are unusable is a reported error (``ValueError`` naming the field), not a substituted
default.

Section-D discipline. ``traction`` is an S1 forbidden token and appears in no declared
name here; the plain-language ``tractive_effort`` form is used instead, while the
**stored** names (``traction``, ``traction_curve``, ``"DAVIS"``) stay data and are read
through the model's own attributes. The five tokens allowed since Stage 5A remain
confined to this package, and this module declares no name carrying one.
"""

from __future__ import annotations

from ..models.rolling_stock import RollingStock
from .resistance import davis_resistance_n
from .tractive_effort import tractive_effort_n

#: Default distance between two sampled speeds [km/h].
DEFAULT_STEP_KMH: float = 10.0

_NEGATIVE_INFINITY: float = float("-inf")
_POSITIVE_INFINITY: float = float("inf")


def _finite_float(argument: str, value: object) -> float:
    """Return *value* as a finite ``float``, or raise ``ValueError`` naming *argument*."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{argument} must be a finite number, got {value!r}")
    number = float(value)
    if not (_NEGATIVE_INFINITY < number < _POSITIVE_INFINITY):
        raise ValueError(f"{argument} must be a finite number, got {value!r}")
    return number


def _sampled_speeds(max_speed_kmh: float, step_kmh: float) -> tuple[float, ...]:
    """Return the ordered sample speeds [km/h] from ``0.0`` to *max_speed_kmh* inclusive."""
    step = _finite_float("step_kmh", step_kmh)
    if step <= 0.0:
        raise ValueError(f"step_kmh must be > 0.0 km/h, got {step_kmh!r}")
    maximum = _finite_float("stock.max_speed_kmh", max_speed_kmh)
    if maximum <= 0.0:
        raise ValueError(
            f"stock.max_speed_kmh must be > 0.0 km/h, got {max_speed_kmh!r}"
        )
    speeds: list[float] = [0.0]
    index = 1
    while True:
        value = step * index
        if not value < maximum:
            break
        speeds.append(value)
        index += 1
    speeds.append(maximum)
    return tuple(speeds)


def tractive_effort_series_n(
    stock: RollingStock,
    step_kmh: float = DEFAULT_STEP_KMH,
) -> tuple[tuple[float, float], ...]:
    """Return ``(speed_kmh, effort_n)`` pairs of *stock* from ``0.0`` to its maximum speed.

    Each pair is ``(v, tractive_effort_n(v, stock.traction.max_tractive_effort_kn,
    stock.traction.rated_power_kw))`` — the primitive is called once per sample, and no
    value is adjusted afterwards.

    :param stock: the stored stock type to sample; read only, never mutated.
    :param step_kmh: distance between two sampled speeds [km/h]; a finite number > 0.0.
        The last point is exactly ``stock.max_speed_kmh`` when the step does not divide
        it evenly.
    :returns: an ordered tuple of ``(speed_kmh, effort_n)`` pairs, at least two of them.
    :raises ValueError: for a non-finite or non-positive step, or for a stored maximum
        speed that is not a finite number > 0.0 — naming the offending field.
    """
    speeds = _sampled_speeds(float(stock.max_speed_kmh), step_kmh)
    return tuple(
        (
            speed,
            tractive_effort_n(
                speed,
                float(stock.traction.max_tractive_effort_kn),
                float(stock.traction.rated_power_kw),
            ),
        )
        for speed in speeds
    )


def running_resistance_series_n(
    stock: RollingStock,
    step_kmh: float = DEFAULT_STEP_KMH,
) -> tuple[tuple[float, float], ...]:
    """Return ``(speed_kmh, resistance_n)`` pairs of *stock* from ``0.0`` to its maximum speed.

    Each pair is ``(v, davis_resistance_n(v, stock.resistance_a_kn,
    stock.resistance_b_kn_per_kmh, stock.resistance_c_kn_per_kmh2))`` — the stock's own
    stored coefficients, read through the model's read-only properties.

    :param stock: the stored stock type to sample; read only, never mutated.
    :param step_kmh: distance between two sampled speeds [km/h]; a finite number > 0.0.
        The last point is exactly ``stock.max_speed_kmh`` when the step does not divide
        it evenly.
    :returns: an ordered tuple of ``(speed_kmh, resistance_n)`` pairs, at least two of them.
    :raises ValueError: for a non-finite or non-positive step, or for a stored maximum
        speed that is not a finite number > 0.0 — naming the offending field.
    """
    speeds = _sampled_speeds(float(stock.max_speed_kmh), step_kmh)
    return tuple(
        (
            speed,
            davis_resistance_n(
                speed,
                float(stock.resistance_a_kn),
                float(stock.resistance_b_kn_per_kmh),
                float(stock.resistance_c_kn_per_kmh2),
            ),
        )
        for speed in speeds
    )
