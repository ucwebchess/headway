"""Phase-5B - resistance and force along a compiled route (read-only evaluation).

Stage 5B wires the Stage-5A pure utilities onto a compiled route: given the read-only
Phase-4B route geometry of a Phase-4A route-coordinate system, every function here answers
*what force acts at route distance ``s`` for a given speed* - and nothing else.  The
per-term arithmetic is **not** re-implemented: this module delegates to the Stage-5A module
:mod:`railway_headway_sim.physics.resistance` for every term it reports.

What this module is:

* a **read-only** evaluation layer: it receives a geometry object and only calls its query
  methods; it never writes to the geometry, the route, the project or any file, and it
  holds no mutable state of its own;
* a **force** layer: every function name ends in ``_n`` and every value it returns is in
  newtons, with the unit of every argument named in the argument (``_kg``, ``_m``,
  ``_kmh``);
* built from the standard library and this package's own modules only: it imports no
  numeric library and no infrastructure module, and it passes the geometry object through
  unchanged (duck-typed and queried, never touched).

What this module is **not**:

* no integration, no time step, no speed profile and no acceleration: the speed is a plain
  argument chosen by the caller, and no state is advanced anywhere;
* no rolling-stock object and no train catalogue: the mass, the train length and the three
  coefficients are plain numbers (a later phase will supply them from a rolling-stock
  model);
* no traction, no braking, no adhesion, no rotating-mass factor, no jerk, no energy and no
  signalling, movement-authority, route-locking, occupancy, blocking-time, capacity,
  timetable, scenario, report or chart logic.

Footprint convention (frozen with Phase 4B): a train whose **front** is at route distance
``s_m`` occupies ``[s_m - train_length_m, s_m]``, and route distance increases in the
direction of travel.  An out-of-range footprint is reported by the geometry, never clamped.

Sign convention (frozen with Stage 5A and unchanged here): the running-resistance term and
the curvature term are **non-negative magnitudes**, the grade term is the one **signed**
quantity - positive when ascending in the direction of travel - and the total is their
literal sum.  At the same physical location the grade term is opposite-signed between the
two directions of travel, while the other two are equal in both, because a radius and a
footprint are magnitudes that do not flip.

The prose above deliberately uses plain language instead of the five names Stage 5A put on
the Section-D allowed list: only the Stage-5A module carries those tokens in its prose
(declared adaptation of Stage 5B, recorded in ``VERIFICATION.md`` §17 and
``docs/PHASE1_CHAIN_OF_CUSTODY.md`` §7.5).
"""

from __future__ import annotations

from typing import Any

from . import resistance as _resistance


def davis_resistance_at_n(
    speed_kmh: float,
    davis_a: float,
    davis_b: float,
    davis_c: float,
) -> float:
    """Return the running resistance [N] at *speed_kmh*; independent of position.

    The value is the Stage-5A running-resistance function of the same arguments, returned
    unchanged: this function forwards, it does not re-derive the polynomial.

    :param speed_kmh: running speed ``V`` [km/h]; a finite number >= 0.0.
    :param davis_a: coefficient ``A`` [kN]; a finite number >= 0.0.
    :param davis_b: coefficient ``B`` [kN / (km/h)]; a finite number >= 0.0.
    :param davis_c: coefficient ``C`` [kN / (km/h)**2]; a finite number >= 0.0.
    :returns: the running resistance force [N], a non-negative magnitude.
    :raises ValueError: as reported by the Stage-5A function - this function validates
        nothing itself and repairs nothing.
    """
    return _resistance.davis_resistance_n(speed_kmh, davis_a, davis_b, davis_c)


def gradient_force_at_n(
    geometry: Any,
    mass_kg: float,
    s_m: float,
    train_length_m: float,
) -> float:
    """Return the signed grade force [N] over the footprint ``[s_m - train_length_m, s_m]``.

    The footprint-averaged grade [permille] is read from the geometry and handed to the
    Stage-5A signed-grade function; the sign convention is Stage 5A's, unchanged: positive
    when ascending in the direction of travel, negative when descending, exactly ``0.0`` on
    level track.  The value therefore flips sign between the two directions of travel at the
    same physical location.

    :param geometry: the read-only Phase-4B route geometry (duck-typed: any object exposing
        ``footprint_gradient(s_m, train_length_m)``); it is only queried, never modified.
    :param mass_kg: train mass [kg]; a finite number > 0.0.
    :param s_m: route distance of the **front** of the train [m]; inside ``[0, L]``.
    :param train_length_m: train length [m]; a positive number no longer than *s_m*.
    :returns: the signed grade force [N].
    :raises: the geometry's own route-coordinate error when any part of the footprint lies
        outside ``[0, route_length_m]`` (the footprint is never clamped), and `ValueError`
        for a non-positive train length or a non-positive mass - reported, never repaired.
    """
    return _resistance.gradient_force_n(
        mass_kg, geometry.footprint_gradient(s_m, train_length_m)
    )


def curve_resistance_at_n(
    geometry: Any,
    mass_kg: float,
    s_m: float,
    train_length_m: float,
) -> float:
    """Return the curvature resistance [N] over the footprint ``[s_m - train_length_m, s_m]``.

    The footprint is partitioned by the geometry's own ``curve_radius_segments_in`` into
    sub-intervals of constant stored radius.  Each sub-interval carrying a radius
    contributes its length times the Stage-5A equivalent gradient of that radius [permille];
    a straight sub-interval contributes ``0.0``.  The length-weighted mean ``W_bar``
    [permille] of the footprint is ``sum(length_i * W_i) / train_length_m`` and the returned
    force is ``mass_kg * GRAVITY_MPS2 * W_bar / 1000`` [N].

    The value is always a **non-negative magnitude** - a radius is a magnitude, so the
    footprint and its weighting do not flip with the direction of travel and the result is
    the same in both directions at the same physical location.  It is exactly ``0.0`` when
    the whole footprint lies on straight sections.

    :param geometry: the read-only Phase-4B route geometry (duck-typed: any object exposing
        ``curve_radius_segments_in(s_start_m, s_end_m)``); queried only, never modified.
    :param mass_kg: train mass [kg]; a finite number > 0.0.
    :param s_m: route distance of the **front** of the train [m]; inside ``[0, L]``.
    :param train_length_m: train length [m]; a positive number no longer than *s_m*.
    :returns: the curvature resistance force [N], non-negative.
    :raises: `ValueError` for a non-positive mass, for a non-positive or reversed footprint
        and for a stored radius outside the Stage-5A applicability condition ``R > 55`` m,
        and the geometry's own route-coordinate error for an out-of-range footprint.
        Nothing is clamped, treated as straight or replaced by a fallback value.
    """
    # The mass is validated by the Stage-5A curvature function at its straight case (radius
    # None), which returns exactly 0.0 and has no other effect: the pure utilities' own
    # ValueError is reported unchanged, and the arithmetic below is not re-implemented.
    _resistance.roeckl_curve_resistance_n(mass_kg, None)
    weighted_permille_m = 0.0
    for sub_length_m, radius_m in geometry.curve_radius_segments_in(
        s_m - train_length_m, s_m
    ):
        if radius_m is None:
            continue
        weighted_permille_m += (
            sub_length_m * _resistance.roeckl_equivalent_gradient_permille(radius_m)
        )
    mean_permille = weighted_permille_m / train_length_m
    return mass_kg * _resistance.GRAVITY_MPS2 * mean_permille / 1000.0


def total_resistance_at_n(
    geometry: Any,
    mass_kg: float,
    train_length_m: float,
    s_m: float,
    speed_kmh: float,
    davis_a: float,
    davis_b: float,
    davis_c: float,
) -> float:
    """Return the signed total resistance force [N] at *s_m* and *speed_kmh*.

    The value is the literal sum of the three functions above, in that order - running
    resistance + signed grade + curvature - and their algebra is not re-implemented here.
    It is the only value of this module that may be negative, and only when a downhill grade
    outweighs the two non-negative magnitudes.

    :param geometry: the read-only Phase-4B route geometry; queried only, never modified.
    :param mass_kg: train mass [kg]; a finite number > 0.0.
    :param train_length_m: train length [m]; a positive number no longer than *s_m*.
    :param s_m: route distance of the **front** of the train [m]; inside ``[0, L]``.
    :param speed_kmh: running speed ``V`` [km/h]; a finite number >= 0.0.
    :param davis_a: coefficient ``A`` [kN]; a finite number >= 0.0.
    :param davis_b: coefficient ``B`` [kN / (km/h)]; a finite number >= 0.0.
    :param davis_c: coefficient ``C`` [kN / (km/h)**2]; a finite number >= 0.0.
    :returns: the signed total resistance force [N].
    :raises: as reported by the three functions above - this function validates nothing
        itself and repairs nothing.
    """
    return (
        davis_resistance_at_n(speed_kmh, davis_a, davis_b, davis_c)
        + gradient_force_at_n(geometry, mass_kg, s_m, train_length_m)
        + curve_resistance_at_n(geometry, mass_kg, s_m, train_length_m)
    )
