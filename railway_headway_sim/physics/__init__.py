"""Phase-5A/5B/6B - pure resistance and effort utilities and their along-route evaluation.

This package holds three read-only layers.  Stage 5A
(:mod:`railway_headway_sim.physics.resistance`) is the **pure numeric** layer: the Davis
running resistance, the gradient force, the Roeckl curve resistance and their signed sum -
four functions that take plain numbers and return a plain number in newtons, plus two pure
helpers that document the model's applicability. Stage 5B
(:mod:`railway_headway_sim.physics.along_route`) is the **along-route** layer: the same four
quantities evaluated at a route distance ``s`` [m] and a caller-given speed [km/h] for a
train of a given mass [kg] and length [m], using the read-only Phase-4B route geometry.
Stage 6B adds the **effort** layer: :mod:`railway_headway_sim.physics.tractive_effort` is the
primitive of the frozen simplified effort model (effort as a function of speed for a given
starting effort and rated power) and :mod:`railway_headway_sim.physics.rolling_stock_series`
samples that primitive and the Stage-5A running resistance over a stored stock type so a plot
can render them.

Scope of this package (Stages 5A and 5B):

* no project and no project document - the package reads no project and writes no file;
* no compiled network and no route-coordinate system of its own: the along-route functions
  receive a route-geometry object from the caller, query it read-only, and the package
  imports nothing from :mod:`railway_headway_sim.infrastructure`;
* no rolling-stock object, no rolling-stock *catalogue* and no train catalogue: in Stages
  5A/5B the mass, the train length and the running-resistance coefficients are plain
  arguments; the Stage-6B series functions additionally accept a stock type from
  :mod:`railway_headway_sim.models.rolling_stock` and read its stored values through the
  model's own read-only properties (they never write to it);
* no commanded effort and no motion: the Stage-6B effort primitive answers *what effort is
  available at this speed* for a stored starting effort and rated power, and the series
  sample it (and the running resistance) at the speeds the caller names;
* no braking behaviour, no adhesion, no rotating-mass factor, no jerk, no regenerative
  braking, no energy, no speed envelope, no trajectory, no acceleration, no integration,
  no time and no dynamics state: the speed is an argument, never an evolved quantity;
* no signalling, ETCS, movement authority, route locking, occupancy, headway, blocking
  time, capacity, timetable, dispatching, scenario, report or chart;
* no new dependency: the modules here import the standard library only.

Nothing in this package advances a train, and nothing here computes a speed, an acceleration
or a time: Stage 5A delivers the algebra, Stage 5B evaluates it along the route at the
position and the speed the caller asks about, and Stage 6B answers what effort a stored
stock type offers at the speed the caller asks about.
"""

from __future__ import annotations

from .along_route import (
    curve_resistance_at_n,
    davis_resistance_at_n,
    gradient_force_at_n,
    total_resistance_at_n,
)
from .resistance import (
    DAVIS_FORCE_UNIT,
    DAVIS_SPEED_UNIT,
    FORCE_UNIT,
    GRADIENT_UNIT,
    GRAVITY_MPS2,
    RADIUS_UNIT,
    davis_resistance_n,
    gradient_force_n,
    is_roeckl_radius_usable,
    roeckl_curve_resistance_n,
    roeckl_equivalent_gradient_permille,
    total_resistance_n,
)
from .rolling_stock_series import (
    DEFAULT_STEP_KMH,
    running_resistance_series_n,
    tractive_effort_series_n,
)
from .tractive_effort import (
    POWER_UNIT,
    SPEED_UNIT,
    TRACTIVE_EFFORT_UNIT,
    tractive_effort_n,
    transition_speed_kmh,
)

__all__ = [
    "DAVIS_FORCE_UNIT",
    "DAVIS_SPEED_UNIT",
    "DEFAULT_STEP_KMH",
    "FORCE_UNIT",
    "GRADIENT_UNIT",
    "GRAVITY_MPS2",
    "POWER_UNIT",
    "RADIUS_UNIT",
    "SPEED_UNIT",
    "TRACTIVE_EFFORT_UNIT",
    "curve_resistance_at_n",
    "davis_resistance_at_n",
    "davis_resistance_n",
    "gradient_force_at_n",
    "gradient_force_n",
    "is_roeckl_radius_usable",
    "roeckl_curve_resistance_n",
    "roeckl_equivalent_gradient_permille",
    "running_resistance_series_n",
    "total_resistance_at_n",
    "total_resistance_n",
    "tractive_effort_n",
    "tractive_effort_series_n",
    "transition_speed_kmh",
]
