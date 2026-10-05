"""Phase-6B — the frozen simplified tractive-effort model (effort at a given speed).

This module answers one question: *how much tractive effort does this stock type
offer at this speed?* It is the primitive the Rolling Stock page plots and the
primitive Stage 7 will call when dynamics are introduced. Nothing here moves: the
speed is an **argument**, never an evolved quantity, and the function holds no
state, reads no file and depends on no clock, no environment and no randomness.

The frozen model — the simplified description the catalogue stores as
``"FORCE_THEN_POWER_LIMITED"`` — is piecewise:

.. code-block:: text

    F_max [N]        = max_tractive_effort_kn * 1000.0
    v_transition_mps = rated_power_kw * 1000.0 / F_max

    F(v):
        speed_mps = speed_kmh / 3.6
        if speed_mps <= v_transition_mps:   F = F_max          # force-limited
        else:                               F = P / speed_mps   # power-limited

    and F is capped by F_max at every speed

so the curve starts at the starting tractive effort, is exactly flat up to the
transition speed, and falls as ``P / v`` beyond it — never above ``F_max``. At zero
speed the force-limited branch applies, so the ``P / v`` singularity is never
evaluated.

Scope (Stage 6B, identical to the rest of the physics package):

* no motion, no trajectory, no speed envelope, no acceleration, no integration, no
  time step and no dynamics state: the function evaluates a force at the speed the
  caller names and returns it;
* no project, no route, no compiled network and no rolling-stock *catalogue*: the
  two parameters are plain numbers — the :mod:`models.rolling_stock` model supplies
  them at the call site, and this module does not import it;
* no braking, no adhesion, no jerk, no energy and no signalling;
* the **stored** operational acceleration limit of the catalogue is deliberately not
  part of this function: it bounds a commanded acceleration in the future dynamics
  engine, not the effort curve drawn for the user;
* no numeric library: the standard library only.

Section-D discipline. The token ``traction`` is an S1 forbidden token and is *not*
on the allowed list, so it may not appear in a declared name anywhere — not even
inside the physics package. The declared names here therefore use the plain-language
form ``tractive_effort`` (``TRACTIVE_EFFORT_UNIT``, :func:`tractive_effort_n`); the
natural name survives in the *data* — the stored field ``traction`` and the stored
model value ``"FORCE_THEN_POWER_LIMITED"`` — which the scan does not read.
"""

from __future__ import annotations

#: Unit of the force returned by :func:`tractive_effort_n`.
TRACTIVE_EFFORT_UNIT: str = "N"
#: Unit of the speed accepted by this module's functions.
SPEED_UNIT: str = "km/h"
#: Unit of the rated-power argument of :func:`tractive_effort_n`.
POWER_UNIT: str = "kW"

_KMH_PER_MPS: float = 3.6
_NEWTON_PER_KILONEWTON: float = 1000.0
_NEGATIVE_INFINITY: float = float("-inf")
_POSITIVE_INFINITY: float = float("inf")


def _finite_float(argument: str, value: object) -> float:
    """Return *value* as a finite ``float``, or raise ``ValueError`` naming *argument*.

    A non-numeric value, a boolean, a NaN and either infinity are reported errors —
    never repaired (the project-wide "no silent repair" rule).
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{argument} must be a finite number, got {value!r}")
    number = float(value)
    if not (_NEGATIVE_INFINITY < number < _POSITIVE_INFINITY):
        raise ValueError(f"{argument} must be a finite number, got {value!r}")
    return number


def _positive_parameters(max_tractive_effort_kn: float, rated_power_kw: float) -> tuple[float, float]:
    """Return ``(starting_effort_n, rated_power_w)`` or raise, naming the offending argument."""
    effort_kn = _finite_float("max_tractive_effort_kn", max_tractive_effort_kn)
    power_kw = _finite_float("rated_power_kw", rated_power_kw)
    if effort_kn <= 0.0:
        raise ValueError(f"max_tractive_effort_kn must be > 0.0 kN, got {max_tractive_effort_kn!r}")
    if power_kw <= 0.0:
        raise ValueError(f"rated_power_kw must be > 0.0 kW, got {rated_power_kw!r}")
    return effort_kn * _NEWTON_PER_KILONEWTON, power_kw * _NEWTON_PER_KILONEWTON


def transition_speed_kmh(max_tractive_effort_kn: float, rated_power_kw: float) -> float:
    """Return the transition speed [km/h] of the frozen piecewise model.

    ``v_transition_mps = P / F_max`` in SI units, converted to km/h for display; the
    curve is force-limited at or below this speed and power-limited above it.

    :param max_tractive_effort_kn: starting tractive effort ``F_max`` [kN]; a finite
        number > 0.0.
    :param rated_power_kw: rated traction power ``P`` [kW]; a finite number > 0.0.
    :returns: the transition speed [km/h].
    :raises ValueError: for a non-finite value or a non-positive parameter — reported
        with the offending argument named, never clamped or repaired.
    """
    effort_n, power_w = _positive_parameters(max_tractive_effort_kn, rated_power_kw)
    return (power_w / effort_n) * _KMH_PER_MPS


def tractive_effort_n(
    speed_kmh: float,
    max_tractive_effort_kn: float,
    rated_power_kw: float,
) -> float:
    """Return the maximum tractive effort [N] available at *speed_kmh*.

    The frozen piecewise model: the force-limited branch (the starting effort) up to
    and including the transition speed, then ``P / v`` in SI units, capped by the
    starting effort at every speed. The result is exact — the force-limited branch
    returns ``max_tractive_effort_kn * 1000.0`` bit-for-bit, and the power-limited
    branch returns ``rated_power_kw * 1000.0 / (speed_kmh / 3.6)`` bit-for-bit.

    :param speed_kmh: speed ``v`` [km/h]; a finite number >= 0.0. At ``0.0`` the
        force-limited branch applies, so no ``P / v`` singularity is evaluated.
    :param max_tractive_effort_kn: starting tractive effort ``F_max`` [kN]; a finite
        number > 0.0.
    :param rated_power_kw: rated traction power ``P`` [kW]; a finite number > 0.0.
    :returns: the available tractive effort [N], never above
        ``max_tractive_effort_kn * 1000.0``.
    :raises ValueError: for a non-finite value, for ``speed_kmh < 0.0`` or for a
        non-positive parameter — reported with the offending argument named, never
        clamped, defaulted or repaired.
    """
    speed = _finite_float("speed_kmh", speed_kmh)
    if speed < 0.0:
        raise ValueError(f"speed_kmh must be >= 0.0 km/h, got {speed_kmh!r}")
    starting_effort_n, rated_power_w = _positive_parameters(
        max_tractive_effort_kn, rated_power_kw
    )
    speed_mps = speed / _KMH_PER_MPS
    transition_mps = rated_power_w / starting_effort_n
    if speed_mps <= transition_mps:
        force_n = starting_effort_n
    else:
        force_n = rated_power_w / speed_mps
    # The cap is unconditional in the frozen model: the curve never exceeds F_max.
    return starting_effort_n if force_n > starting_effort_n else force_n
