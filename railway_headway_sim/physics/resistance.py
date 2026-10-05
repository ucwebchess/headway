"""Phase-5A - pure Davis and Roeckl resistance utilities.

Every function in this module is a **pure numeric utility**: it takes plain numbers and
returns a plain number in newtons (the two helpers return a ``bool`` and a ``permille``
value). Unit discipline is part of the contract, not a hidden assumption:

* speed in ``km/h`` (:param:`speed_kmh`),
* mass in kilograms (:param:`mass_kg`),
* gradient in per mille (:param:`gradient_permille`),
* curve radius in metres (:param:`radius_m`),
* Davis coefficients on the kN basis declared by :func:`davis_resistance_n`,
* every returned force in newtons (``..._n``).

What this module is **not**:

* it is **not** a route, a project, a compiled network, a route-coordinate system or a
  route-geometry reader - it imports nothing from :mod:`railway_headway_sim.infrastructure`
  and it never reads or writes a file, a project or a route;
* it is **not** a rolling-stock model - the caller supplies ``mass_kg`` and the Davis
  coefficients as plain numbers;
* it is **not** a train-motion model: there is no traction, no braking, no adhesion, no
  rotating-mass factor, no speed envelope, no trajectory, no acceleration, no integration,
  no time and no distance here, and no dynamics state is kept anywhere;
* it is **not** signalling, movement-authority, route-locking, headway, blocking-time,
  capacity, timetable, dispatching, scenario, report or chart code.

Sign convention (frozen by the Phase-5A specification): :func:`davis_resistance_n` returns a
**non-negative magnitude**, :func:`roeckl_curve_resistance_n` returns a **non-negative
magnitude** (the caller subtracts both from traction; this module does not encode that
subtraction), and :func:`gradient_force_n` is the **signed** quantity - positive when
ascending in the direction of travel (it opposes forward motion), negative when descending
(it assists forward motion).

The module imports the standard library only (``typing`` for the optional radius), defines no
global mutable state, depends on no environment variable, no random value and no clock, and
performs no floating-point smoothing: the same inputs always produce the same output.
"""

from __future__ import annotations

from typing import Optional

#: Standard gravity [m/s^2], used by the gradient force and the Roeckl curve resistance.
GRAVITY_MPS2: float = 9.80665

#: Unit of every force this module returns.
FORCE_UNIT: str = "N"
#: Unit of the Davis resistance basis: ``A`` in kN, ``B`` in kN / (km/h), ``C`` in
#: kN / (km/h)**2.
DAVIS_FORCE_UNIT: str = "kN"
#: Speed unit of the Davis formula (``V`` in km/h).
DAVIS_SPEED_UNIT: str = "km/h"
#: Gradient unit of the gradient force and of the Roeckl equivalent gradient.
GRADIENT_UNIT: str = "permille"
#: Curve-radius unit of the Roeckl curve resistance.
RADIUS_UNIT: str = "m"

#: Roeckl numerator of ``W_c = 650 / (R - 55)`` [permille * m].
_ROECKL_NUMERATOR_PERMILLE_M: float = 650.0
#: Roeckl radius offset of ``W_c = 650 / (R - 55)`` [m]: the formula is defined for R > 55 m.
_ROECKL_RADIUS_OFFSET_M: float = 55.0

_NEGATIVE_INFINITY: float = float("-inf")
_POSITIVE_INFINITY: float = float("inf")


def _finite_float(argument: str, value: object) -> float:
    """Return *value* as a finite ``float``, or raise ``ValueError`` naming *argument*.

    A non-numeric value, a NaN and either infinity are reported errors - never repaired
    (the Phase-2 "no silent repair" rule applies to this module unchanged).
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{argument} must be a finite number, got {value!r}")
    number = float(value)
    if not (_NEGATIVE_INFINITY < number < _POSITIVE_INFINITY):
        raise ValueError(f"{argument} must be a finite number, got {value!r}")
    return number


def davis_resistance_n(
    speed_kmh: float,
    davis_a: float,
    davis_b: float,
    davis_c: float,
) -> float:
    """Return the Davis running resistance force [N].

    ``R(V) = A + B * V + C * V**2`` [kN], with ``V`` in km/h; the result is that value
    converted to newtons by the factor ``1000``. The returned value is a **non-negative
    magnitude**: the caller subtracts it from traction.

    :param speed_kmh: running speed ``V`` [km/h]; a finite number >= 0.0.
    :param davis_a: Davis coefficient ``A`` [kN]; a finite number >= 0.0.
    :param davis_b: Davis coefficient ``B`` [kN / (km/h)]; a finite number >= 0.0.
    :param davis_c: Davis coefficient ``C`` [kN / (km/h)**2]; a finite number >= 0.0.
    :returns: the Davis running resistance force [N].
    :raises ValueError: for a non-finite value, for ``speed_kmh < 0.0`` or for a negative
        coefficient ``B``/``C``/``A`` - reported, never clamped or repaired.
    """
    speed = _finite_float("speed_kmh", speed_kmh)
    coefficient_a = _finite_float("davis_a", davis_a)
    coefficient_b = _finite_float("davis_b", davis_b)
    coefficient_c = _finite_float("davis_c", davis_c)
    if speed < 0.0:
        raise ValueError(f"speed_kmh must be >= 0.0 km/h, got {speed_kmh!r}")
    for name, value in (
        ("davis_a", coefficient_a),
        ("davis_b", coefficient_b),
        ("davis_c", coefficient_c),
    ):
        if value < 0.0:
            raise ValueError(
                f"{name} must be >= 0.0 (a negative coefficient is a data error, not a "
                f"case to be repaired), got {value!r}"
            )
    return (coefficient_a + coefficient_b * speed + coefficient_c * speed**2) * 1000.0


def gradient_force_n(
    mass_kg: float,
    gradient_permille: float,
) -> float:
    """Return the signed gradient force [N].

    ``F = mass_kg * GRAVITY_MPS2 * (gradient_permille / 1000)``, the frozen normal-railway
    approximation ``sin(theta) ~ tan(theta) ~ gradient_permille / 1000``: no angle is
    computed, no trigonometric function is used and the sinus is not evaluated.

    Positive = ascending in the direction of travel (it opposes forward motion);
    negative = descending (it assists forward motion). This is the one **signed** quantity
    of the module.

    :param mass_kg: train mass [kg]; a finite number > 0.0.
    :param gradient_permille: gradient of the grade of travel [permille]; a finite number
        (positive uphill, negative downhill, 0.0 on level track).
    :returns: the gradient force [N], signed by the grade.
    :raises ValueError: for a non-finite value or for ``mass_kg <= 0.0`` - reported, never
        clamped or repaired.
    """
    mass = _finite_float("mass_kg", mass_kg)
    gradient = _finite_float("gradient_permille", gradient_permille)
    if mass <= 0.0:
        raise ValueError(f"mass_kg must be > 0.0 kg, got {mass_kg!r}")
    return mass * GRAVITY_MPS2 * (gradient / 1000.0)


def is_roeckl_radius_usable(radius_m: float) -> bool:
    """Return ``True`` iff *radius_m* [m] is a radius the Roeckl model accepts.

    The Roeckl denominator ``R - 55`` is safely positive exactly when ``R > 55.0`` [m]. A
    non-numeric value, a NaN and either infinity are **not** usable and return ``False``.
    """
    try:
        radius = _finite_float("radius_m", radius_m)
    except ValueError:
        return False
    return radius > _ROECKL_RADIUS_OFFSET_M


def roeckl_equivalent_gradient_permille(radius_m: float) -> float:
    """Return the Roeckl curve resistance ``W_c = 650 / (R - 55)`` [permille].

    :param radius_m: curve radius ``R`` [m]; a finite number > 55.0.
    :returns: the equivalent gradient the curve adds [permille].
    :raises ValueError: when :func:`is_roeckl_radius_usable` is ``False`` for *radius_m* -
        that is, for ``radius_m <= 55.0`` (including 0.0 and negative radii), for a NaN and
        for either infinity. The denominator would not be safely positive, so the condition
        ``R > 55`` [m] is reported as an error and never replaced by a clamp or by an
        "infinite radius" fallback.
    """
    radius = _finite_float("radius_m", radius_m)
    if not is_roeckl_radius_usable(radius):
        raise ValueError(
            f"radius_m = {radius!r} is outside the Roeckl model's applicability condition "
            f"R > 55 m (W_c = 650 / (R - 55) permille); a radius in (0.0, 55.0] is a "
            f"reported error, not a silently repaired value"
        )
    return _ROECKL_NUMERATOR_PERMILLE_M / (radius - _ROECKL_RADIUS_OFFSET_M)


def roeckl_curve_resistance_n(
    mass_kg: float,
    radius_m: Optional[float],
) -> float:
    """Return the Roeckl curve resistance force [N].

    ``W_c = 650 / (R - 55)`` [permille] with ``R`` in metres, and
    ``F_c = mass_kg * GRAVITY_MPS2 * W_c / 1000``. The returned value is always
    **non-negative**: curve resistance opposes motion.

    :param mass_kg: train mass [kg]; a finite number > 0.0.
    :param radius_m: curve radius ``R`` [m], or ``None``. ``None`` means a straight section
        and returns exactly ``0.0``. A radius in ``(0.0, 55.0]`` is outside the model's
        applicability condition ``R > 55`` m and is reported, never treated as a straight
        and never turned into an infinite radius.
    :returns: the Roeckl curve resistance force [N], non-negative.
    :raises ValueError: for a non-finite mass, for ``mass_kg <= 0.0`` and for every
        rejected radius - reported, never repaired.
    """
    mass = _finite_float("mass_kg", mass_kg)
    if mass <= 0.0:
        raise ValueError(f"mass_kg must be > 0.0 kg, got {mass_kg!r}")
    if radius_m is None:
        return 0.0
    equivalent_gradient = roeckl_equivalent_gradient_permille(radius_m)
    return mass * GRAVITY_MPS2 * equivalent_gradient / 1000.0


def total_resistance_n(
    mass_kg: float,
    speed_kmh: float,
    davis_a: float,
    davis_b: float,
    davis_c: float,
    gradient_permille: float,
    radius_m: Optional[float],
) -> float:
    """Return the signed sum of the three resistance contributions [N].

    The value is the literal sum of the three functions above, in the order Davis +
    gradient + Roeckl; their algebra is not re-implemented here:

    * :func:`davis_resistance_n` [N], a non-negative magnitude,
    * :func:`gradient_force_n` [N], signed by the grade,
    * :func:`roeckl_curve_resistance_n` [N], a non-negative magnitude (``0.0`` on a
      straight).

    :param mass_kg: train mass [kg]; a finite number > 0.0.
    :param speed_kmh: running speed ``V`` [km/h]; a finite number >= 0.0.
    :param davis_a: Davis coefficient ``A`` [kN]; a finite number >= 0.0.
    :param davis_b: Davis coefficient ``B`` [kN / (km/h)]; a finite number >= 0.0.
    :param davis_c: Davis coefficient ``C`` [kN / (km/h)**2]; a finite number >= 0.0.
    :param gradient_permille: gradient [permille], signed by the grade.
    :param radius_m: curve radius ``R`` [m], or ``None`` for a straight.
    :returns: ``davis + gradient + Roeckl`` [N] - the only value of this module that may be
        negative, and only when the (negative) gradient force outweighs the two resistance
        magnitudes.
    :raises ValueError: as reported by the three functions above - this function validates
        nothing itself and repairs nothing.
    """
    davis_force = davis_resistance_n(speed_kmh, davis_a, davis_b, davis_c)
    gradient_force = gradient_force_n(mass_kg, gradient_permille)
    curve_force = roeckl_curve_resistance_n(mass_kg, radius_m)
    return davis_force + gradient_force + curve_force
