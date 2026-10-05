"""Phase-5A acceptance tests: pure Davis and Roeckl resistance utilities.

TEST P5-001 ... TEST P5-024.

Scope of this module (master specification, Stage 5A):

* :mod:`railway_headway_sim.physics.resistance` exposes four pure functions -
  ``davis_resistance_n``, ``gradient_force_n``, ``roeckl_curve_resistance_n`` and
  ``total_resistance_n`` - plus the two helpers ``is_roeckl_radius_usable`` and
  ``roeckl_equivalent_gradient_permille``;
* every function takes plain numbers and returns a plain number in newtons (the helpers
  return a ``bool`` and a ``permille`` value); there is no project, no route, no compiled
  network, no route geometry, no rolling-stock object, no time and no integration;
* the frozen sign convention holds: Davis and Roeckl are returned as non-negative
  magnitudes, the gradient force is the one signed quantity, and the total is their
  literal sum;
* the Roeckl applicability condition ``R > 55 m`` is enforced, ``radius_m = None``
  (straight) returns exactly ``0.0``, and a radius in ``(0.0, 55.0]`` is a reported error;
* the Section-D scan is updated so the five Phase-5A tokens are *allowed* in the physics
  module while every other forbidden token is still rejected by the same surfaces.

Every expected value is recomputed inside the test from the frozen inputs (never
hand-typed as a constant the data must match), and no test writes to any protected
artefact.
"""

from __future__ import annotations

import ast
import hashlib
import importlib
import inspect
import json
import re
import sys
from pathlib import Path

import pytest

from railway_headway_sim.io.project_io import (
    document_hash,
    import_project_from_data,
    to_normalized_dict,
)
from railway_headway_sim.physics import (
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

_REPO_ROOT = Path(__file__).resolve().parents[2]
_PACKAGE_DIR = _REPO_ROOT / "railway_headway_sim"
_PHYSICS_DIR = _PACKAGE_DIR / "physics"
_MODULE_PATH = _PHYSICS_DIR / "resistance.py"
_PACKAGE_INIT = _PHYSICS_DIR / "__init__.py"
_PROTECTED_GRR01 = _REPO_ROOT / "examples" / "GRR-01.json"
_SECTION_D_PATTERNS = _REPO_ROOT / "docs" / "SECTION_D_PATTERNS.md"
_CONFTEST = _PACKAGE_DIR / "tests" / "conftest.py"
_INVENTORY_BUILDER = _REPO_ROOT / "build_test_inventory.py"
_INVENTORY = _REPO_ROOT / "docs" / "TEST_INVENTORY.md"

#: sha256 of the protected reference project file (must not change; checked here).
PROTECTED_GRR01_SHA256 = "ad0a26265d4e072aeedcc69161bef90f200c20b4efb12a4d56a5276c4a4f7a56"

#: Canonical document hash of the reference project (must not change).
CANONICAL_GRR01_HASH = "5189aaa2340c17022666ef44772c7d34f99b2fea9ee9609bb7b7513238ef4dbe"

#: The frozen HSR dataset of the specification: mass [kg] and Davis coefficients
#: A [kN], B [kN / (km/h)], C [kN / (km/h)**2].
HSR_MASS_KG = 485000.0
HSR_DAVIS_A = 2.506
HSR_DAVIS_B = 0.04065
HSR_DAVIS_C = 0.00043

#: The five tokens the Section-D scan now allows, in the physics module only.
ALLOWED_PHASE5A_TOKENS = ("Davis", "Roeckl", "rolling resistance", "curve resistance", "gradient force")

#: The frozen public signatures of the Phase-5A API (arguments in declaration order).
EXPECTED_SIGNATURES = {
    "davis_resistance_n": ("speed_kmh", "davis_a", "davis_b", "davis_c"),
    "gradient_force_n": ("mass_kg", "gradient_permille"),
    "roeckl_curve_resistance_n": ("mass_kg", "radius_m"),
    "total_resistance_n": (
        "mass_kg",
        "speed_kmh",
        "davis_a",
        "davis_b",
        "davis_c",
        "gradient_permille",
        "radius_m",
    ),
    "is_roeckl_radius_usable": ("radius_m",),
    "roeckl_equivalent_gradient_permille": ("radius_m",),
}

#: Arguments whose *name* carries their unit (the frozen Davis coefficient names keep the
#: unit in the docstring instead, because the specification freezes them as davis_a/b/c).
UNIT_IN_ARGUMENT_NAME = {
    "speed_kmh": "kmh",
    "mass_kg": "kg",
    "gradient_permille": "permille",
    "radius_m": "m",
}

#: The unit token each argument name must be documented with in the function docstring.
UNIT_TOKEN_IN_DOCSTRING = {
    "speed_kmh": "km/h",
    "mass_kg": "kg",
    "gradient_permille": "permille",
    "radius_m": "m",
    "davis_a": "kN",
    "davis_b": "kN",
    "davis_c": "kN",
}


def _module():
    """Return the imported Phase-5A module."""
    return importlib.import_module("railway_headway_sim.physics.resistance")


def _section_tokens(heading: str) -> tuple[str, ...]:
    """Return the token list of one ``docs/SECTION_D_PATTERNS.md`` section."""
    text = _SECTION_D_PATTERNS.read_text(encoding="utf-8")
    start = text.index(heading)
    end = text.index("\n## ", start + 1)
    body = text[start:end].split("\n", 1)[1]
    paragraph = body.strip().split("\n\n", 1)[0]
    return tuple(re.findall(r"`([^`]+)`", paragraph))


def _declared_names(path: Path) -> list[str]:
    """Return every declared function / async function / class name of one module file."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return [
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    ]


def _canonical_hash() -> str:
    """Return the canonical hash of the loaded reference project."""
    document = json.loads(_PROTECTED_GRR01.read_text(encoding="utf-8"))
    project = import_project_from_data(document).project
    return document_hash(to_normalized_dict(project))


# ---------------------------------------------------------------------------
# P5-001 ... P5-005 - the module surface and the Davis running resistance
# ---------------------------------------------------------------------------
def test_p5_001_module_exposes_the_documented_api():
    """TEST P5-001 - the module exists, imports cleanly and exposes the documented API."""
    assert _MODULE_PATH.is_file(), "railway_headway_sim/physics/resistance.py must exist"
    assert _PACKAGE_INIT.is_file(), "the physics package needs its __init__.py"
    module = _module()
    package = importlib.import_module("railway_headway_sim.physics")
    for name in EXPECTED_SIGNATURES:
        assert callable(getattr(module, name)), name
        assert getattr(package, name) is getattr(module, name), f"physics.{name} is not re-exported"

    assert GRAVITY_MPS2 == 9.80665
    assert module.GRAVITY_MPS2 == GRAVITY_MPS2 == 9.80665
    assert (FORCE_UNIT, DAVIS_FORCE_UNIT, DAVIS_SPEED_UNIT, GRADIENT_UNIT, RADIUS_UNIT) == (
        "N",
        "kN",
        "km/h",
        "permille",
        "m",
    )
    assert isinstance(module.__doc__, str) and "Phase-5A" in module.__doc__
    for name, parameters in EXPECTED_SIGNATURES.items():
        assert tuple(inspect.signature(getattr(module, name)).parameters) == parameters, name


def test_p5_002_davis_resistance_is_the_declared_formula_in_newtons():
    """TEST P5-002 - Davis resistance is A + B*V + C*V**2 [kN] returned in newtons."""
    combinations = (
        (0.0, 0.0, 0.0, 0.0),
        (0.0, HSR_DAVIS_A, HSR_DAVIS_B, HSR_DAVIS_C),
        (1.0, HSR_DAVIS_A, HSR_DAVIS_B, HSR_DAVIS_C),
        (80.0, HSR_DAVIS_A, HSR_DAVIS_B, HSR_DAVIS_C),
        (123.456, 1.5, 0.02, 0.0005),
        (200.0, HSR_DAVIS_A, HSR_DAVIS_B, HSR_DAVIS_C),
        (320.0, HSR_DAVIS_A, HSR_DAVIS_B, HSR_DAVIS_C),
        (400.0, HSR_DAVIS_A, HSR_DAVIS_B, HSR_DAVIS_C),
        (400.0, 7.0, 0.0, 0.0),
    )
    for speed_kmh, davis_a, davis_b, davis_c in combinations:
        expected = (davis_a + davis_b * speed_kmh + davis_c * speed_kmh**2) * 1000.0
        observed = davis_resistance_n(speed_kmh, davis_a, davis_b, davis_c)
        assert isinstance(observed, float)
        assert observed == expected, (speed_kmh, davis_a, davis_b, davis_c, observed, expected)
        assert observed >= 0.0

    # the frozen HSR dataset at 320 km/h, recomputed here
    assert davis_resistance_n(
        320.0, HSR_DAVIS_A, HSR_DAVIS_B, HSR_DAVIS_C
    ) == pytest.approx(
        (HSR_DAVIS_A + HSR_DAVIS_B * 320.0 + HSR_DAVIS_C * 320.0**2) * 1000.0,
        rel=1e-12,
    )


def test_p5_003_davis_resistance_at_zero_speed_is_the_constant_term():
    """TEST P5-003 - at V = 0 the Davis resistance is A * 1000.0, bit-for-bit."""
    for davis_a in (0.0, 2.506, 1.0 / 3.0, 12.75):
        expected = davis_a * 1000.0
        observed = davis_resistance_n(0.0, davis_a, HSR_DAVIS_B, HSR_DAVIS_C)
        assert observed == expected
        assert repr(observed) == repr(expected)


def test_p5_004_davis_resistance_is_non_decreasing_in_speed():
    """TEST P5-004 - the Davis resistance never decreases with speed on [0, 400] km/h."""
    for davis_a, davis_b, davis_c in (
        (HSR_DAVIS_A, HSR_DAVIS_B, HSR_DAVIS_C),
        (0.0, 0.0, 0.0),
        (1.0, 0.0, 0.001),
        (0.0, 0.05, 0.0),
        (3.5, 0.01, 0.0002),
    ):
        previous = davis_resistance_n(0.0, davis_a, davis_b, davis_c)
        step = 0
        while step <= 4000:
            speed_kmh = step * 0.1
            value = davis_resistance_n(speed_kmh, davis_a, davis_b, davis_c)
            assert value >= previous, (speed_kmh, davis_a, davis_b, davis_c, value, previous)
            previous = value
            step += 1


def test_p5_005_davis_resistance_rejects_impossible_inputs():
    """TEST P5-005 - negative/non-finite speed and negative coefficients are reported."""
    with pytest.raises(ValueError, match="speed_kmh"):
        davis_resistance_n(-0.001, HSR_DAVIS_A, HSR_DAVIS_B, HSR_DAVIS_C)
    with pytest.raises(ValueError, match="speed_kmh"):
        davis_resistance_n(float("nan"), HSR_DAVIS_A, HSR_DAVIS_B, HSR_DAVIS_C)
    with pytest.raises(ValueError, match="speed_kmh"):
        davis_resistance_n(float("inf"), HSR_DAVIS_A, HSR_DAVIS_B, HSR_DAVIS_C)
    with pytest.raises(ValueError, match="davis_a"):
        davis_resistance_n(120.0, -1.0, HSR_DAVIS_B, HSR_DAVIS_C)
    with pytest.raises(ValueError, match="davis_b"):
        davis_resistance_n(120.0, HSR_DAVIS_A, -0.001, HSR_DAVIS_C)
    with pytest.raises(ValueError, match="davis_c"):
        davis_resistance_n(120.0, HSR_DAVIS_A, HSR_DAVIS_B, -0.000001)
    with pytest.raises(ValueError, match="davis_c"):
        davis_resistance_n(120.0, HSR_DAVIS_A, HSR_DAVIS_B, float("-inf"))
    # a negative coefficient is never repaired into 0.0 or abs(): the call must raise
    with pytest.raises(ValueError):
        davis_resistance_n(0.0, -2.506, HSR_DAVIS_B, HSR_DAVIS_C)


# ---------------------------------------------------------------------------
# P5-006 ... P5-010 - the signed gradient force
# ---------------------------------------------------------------------------
def test_p5_006_gradient_force_of_the_frozen_hsr_mass_uphill():
    """TEST P5-006 - +10 per mille on 485 000 kg is m * g * 0.01 newtons."""
    expected = 485000.0 * 9.80665 * 0.01
    observed = gradient_force_n(HSR_MASS_KG, 10.0)
    assert isinstance(observed, float)
    assert observed == pytest.approx(expected, rel=1e-9)
    assert observed == HSR_MASS_KG * GRAVITY_MPS2 * (10.0 / 1000.0)
    assert observed > 0.0


def test_p5_007_gradient_force_downhill_is_the_exact_negative():
    """TEST P5-007 - -10 per mille is the exact negation of the +10 per mille force."""
    uphill = gradient_force_n(HSR_MASS_KG, 10.0)
    downhill = gradient_force_n(HSR_MASS_KG, -10.0)
    assert downhill == -uphill
    assert repr(downhill) == "-" + repr(uphill)
    assert downhill < 0.0 < uphill
    for gradient_permille in (0.5, 2.0, 12.5, 33.0, 40.0):
        assert gradient_force_n(HSR_MASS_KG, -gradient_permille) == -gradient_force_n(
            HSR_MASS_KG, gradient_permille
        )


def test_p5_008_gradient_force_on_level_track_is_zero():
    """TEST P5-008 - 0.0 per mille returns exactly 0.0 (and not a signed zero)."""
    for mass_kg in (1.0, HSR_MASS_KG, 12345678.0):
        observed = gradient_force_n(mass_kg, 0.0)
        assert observed == 0.0
        assert repr(observed) == "0.0"


def test_p5_009_gradient_force_uses_the_module_gravity_constant():
    """TEST P5-009 - GRAVITY_MPS2 is 9.80665 and the force is linear in mass."""
    module = _module()
    assert module.GRAVITY_MPS2 == 9.80665
    assert GRAVITY_MPS2 == 9.80665
    for gradient_permille in (-25.0, 0.0, 5.5, 10.0):
        base = gradient_force_n(HSR_MASS_KG, gradient_permille)
        assert base == HSR_MASS_KG * module.GRAVITY_MPS2 * (gradient_permille / 1000.0)
        for factor in (2.0, 0.5, 10.0):
            assert gradient_force_n(HSR_MASS_KG * factor, gradient_permille) == pytest.approx(
                base * factor, rel=1e-12
            )
            assert gradient_force_n(HSR_MASS_KG * factor, gradient_permille) == base * factor


def test_p5_010_gradient_force_rejects_impossible_inputs():
    """TEST P5-010 - a non-positive mass and a non-finite grade are reported."""
    with pytest.raises(ValueError, match="mass_kg"):
        gradient_force_n(0.0, 10.0)
    with pytest.raises(ValueError, match="mass_kg"):
        gradient_force_n(-1.0, 10.0)
    with pytest.raises(ValueError, match="mass_kg"):
        gradient_force_n(float("nan"), 10.0)
    with pytest.raises(ValueError, match="gradient_permille"):
        gradient_force_n(HSR_MASS_KG, float("inf"))
    with pytest.raises(ValueError, match="gradient_permille"):
        gradient_force_n(HSR_MASS_KG, float("-inf"))
    with pytest.raises(ValueError, match="gradient_permille"):
        gradient_force_n(HSR_MASS_KG, float("nan"))


# ---------------------------------------------------------------------------
# P5-011 ... P5-016 - the Roeckl curve resistance and its helpers
# ---------------------------------------------------------------------------
def test_p5_011_roeckl_curve_resistance_of_the_frozen_hsr_mass():
    """TEST P5-011 - R = 1800 m on 485 000 kg is m * g * (650 / (R - 55)) / 1000 newtons."""
    expected = 485000.0 * 9.80665 * (650.0 / (1800.0 - 55.0)) / 1000.0
    observed = roeckl_curve_resistance_n(HSR_MASS_KG, 1800.0)
    assert observed == expected, (observed, expected)
    assert observed == pytest.approx(expected, rel=1e-9)
    assert observed > 0.0
    # the same value is reached through the documented helper
    assert observed == HSR_MASS_KG * GRAVITY_MPS2 * roeckl_equivalent_gradient_permille(1800.0) / 1000.0


def test_p5_012_roeckl_curve_resistance_on_a_straight_is_zero():
    """TEST P5-012 - radius_m = None returns exactly 0.0 and does not raise."""
    for mass_kg in (1.0, HSR_MASS_KG):
        observed = roeckl_curve_resistance_n(mass_kg, None)
        assert observed == 0.0
        assert repr(observed) == "0.0"
    assert roeckl_curve_resistance_n(HSR_MASS_KG, None) != float("inf")


def test_p5_013_roeckl_curve_resistance_rejects_radii_at_or_below_55_m():
    """TEST P5-013 - a radius in (0.0, 55.0] is a reported error, never a clamp."""
    for radius_m in (0.5, 1.0, 27.5, 54.999999, 55.0):
        with pytest.raises(ValueError) as excinfo:
            roeckl_curve_resistance_n(HSR_MASS_KG, radius_m)
        message = str(excinfo.value)
        assert "R > 55" in message, message
        assert "radius_m" in message
    # the same condition is enforced by the helper that computes the permille value
    with pytest.raises(ValueError, match="R > 55"):
        roeckl_equivalent_gradient_permille(55.0)


def test_p5_014_roeckl_curve_resistance_rejects_zero_negative_and_non_finite_radii():
    """TEST P5-014 - radius 0.0, a negative radius, NaN and infinity are all reported."""
    for radius_m in (0.0, -1.0, -1800.0, float("nan"), float("inf"), float("-inf")):
        with pytest.raises(ValueError) as excinfo:
            roeckl_curve_resistance_n(HSR_MASS_KG, radius_m)
        assert "radius_m" in str(excinfo.value)
    for radius_m in (0.0, -1.0, float("nan"), float("inf")):
        with pytest.raises(ValueError):
            roeckl_equivalent_gradient_permille(radius_m)


def test_p5_015_roeckl_equivalent_gradient_is_the_permille_used_by_the_force():
    """TEST P5-015 - W_c = 650 / (R - 55) permille is the value the force uses."""
    for radius_m in (55.000001, 55.5, 100.0, 300.0, 800.0, 1200.0, 1800.0, 2000.0, 5000.0, 1.0e6):
        expected = 650.0 / (radius_m - 55.0)
        observed = roeckl_equivalent_gradient_permille(radius_m)
        assert observed == expected, (radius_m, observed, expected)
        assert observed > 0.0
        # the force is exactly m * g * W_c / 1000 with that same permille value
        assert roeckl_curve_resistance_n(HSR_MASS_KG, radius_m) == (
            HSR_MASS_KG * GRAVITY_MPS2 * observed / 1000.0
        )
    # the equivalent gradient decreases as the radius grows (a milder curve)
    values = [roeckl_equivalent_gradient_permille(r) for r in (100.0, 800.0, 1800.0, 5000.0)]
    assert values == sorted(values, reverse=True)


def test_p5_016_is_roeckl_radius_usable_is_the_applicability_predicate():
    """TEST P5-016 - True for R > 55 m; False for R <= 55, NaN and infinity."""
    for radius_m in (55.000001, 56.0, 300.0, 1800.0, 1.0e7):
        assert is_roeckl_radius_usable(radius_m) is True, radius_m
    for radius_m in (55.0, 54.999999, 1.0, 0.0, -1800.0, float("nan"), float("inf"), float("-inf")):
        assert is_roeckl_radius_usable(radius_m) is False, radius_m


# ---------------------------------------------------------------------------
# P5-017 ... P5-019 - the signed sum
# ---------------------------------------------------------------------------
def test_p5_017_total_resistance_is_the_literal_sum_of_the_three_functions():
    """TEST P5-017 - the total is Davis + gradient + Roeckl, recomputed here."""
    combinations = (
        (HSR_MASS_KG, 0.0, HSR_DAVIS_A, HSR_DAVIS_B, HSR_DAVIS_C, 0.0, None),
        (HSR_MASS_KG, 320.0, HSR_DAVIS_A, HSR_DAVIS_B, HSR_DAVIS_C, 10.0, 1800.0),
        (HSR_MASS_KG, 200.0, HSR_DAVIS_A, HSR_DAVIS_B, HSR_DAVIS_C, -12.5, 1200.0),
        (250000.0, 80.0, 1.5, 0.02, 0.0005, 5.0, 600.0),
        (1.0, 0.0, 0.0, 0.0, 0.0, -40.0, None),
    )
    for (
        mass_kg,
        speed_kmh,
        davis_a,
        davis_b,
        davis_c,
        gradient_permille,
        radius_m,
    ) in combinations:
        expected = (
            davis_resistance_n(speed_kmh, davis_a, davis_b, davis_c)
            + gradient_force_n(mass_kg, gradient_permille)
            + roeckl_curve_resistance_n(mass_kg, radius_m)
        )
        observed = total_resistance_n(
            mass_kg, speed_kmh, davis_a, davis_b, davis_c, gradient_permille, radius_m
        )
        assert observed == expected, (mass_kg, speed_kmh, gradient_permille, radius_m)
    # the same validation surface as the three functions
    with pytest.raises(ValueError, match="speed_kmh"):
        total_resistance_n(HSR_MASS_KG, -1.0, HSR_DAVIS_A, HSR_DAVIS_B, HSR_DAVIS_C, 0.0, None)
    with pytest.raises(ValueError, match="mass_kg"):
        total_resistance_n(0.0, 100.0, HSR_DAVIS_A, HSR_DAVIS_B, HSR_DAVIS_C, 0.0, None)
    with pytest.raises(ValueError, match="R > 55"):
        total_resistance_n(HSR_MASS_KG, 100.0, HSR_DAVIS_A, HSR_DAVIS_B, HSR_DAVIS_C, 0.0, 10.0)


def test_p5_018_total_resistance_on_level_straight_track_is_davis_alone():
    """TEST P5-018 - gradient 0.0 and radius None leave the Davis resistance alone."""
    for speed_kmh in (0.0, 120.0, 320.0):
        davis_only = davis_resistance_n(speed_kmh, HSR_DAVIS_A, HSR_DAVIS_B, HSR_DAVIS_C)
        total = total_resistance_n(
            HSR_MASS_KG, speed_kmh, HSR_DAVIS_A, HSR_DAVIS_B, HSR_DAVIS_C, 0.0, None
        )
        assert total == davis_only
        assert total == pytest.approx(davis_only, rel=1e-12)


def test_p5_019_total_resistance_can_be_negative_on_a_steep_downhill():
    """TEST P5-019 - a steep enough downhill outweighs both resistance magnitudes."""
    gradient_permille = -25.0
    speed_kmh = 320.0
    davis = davis_resistance_n(speed_kmh, HSR_DAVIS_A, HSR_DAVIS_B, HSR_DAVIS_C)
    gradient = gradient_force_n(HSR_MASS_KG, gradient_permille)
    curve = roeckl_curve_resistance_n(HSR_MASS_KG, 1800.0)
    assert davis > 0.0 and curve > 0.0 and gradient < 0.0
    assert davis + curve < abs(gradient), "the constructed case must be dominated by the grade"
    total = total_resistance_n(
        HSR_MASS_KG, speed_kmh, HSR_DAVIS_A, HSR_DAVIS_B, HSR_DAVIS_C, gradient_permille, 1800.0
    )
    assert total == davis + gradient + curve
    assert total < 0.0


# ---------------------------------------------------------------------------
# P5-020 ... P5-023 - dependencies, unit discipline, purity and the scan update
# ---------------------------------------------------------------------------
def test_p5_020_physics_package_uses_the_standard_library_only():
    """TEST P5-020 - no numeric library, nothing outside the standard library, no cycle."""
    forbidden = {"math", "numpy", "scipy", "statistics", "random"}
    scanned = sorted(_PHYSICS_DIR.glob("*.py"))
    assert scanned, "the physics package must contain at least one module"
    for path in scanned:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                roots = [alias.name.split(".")[0] for alias in node.names]
                assert roots and all(root in sys.stdlib_module_names for root in roots), (
                    path.name,
                    roots,
                )
                assert not (set(roots) & forbidden), (path.name, roots)
            elif isinstance(node, ast.ImportFrom):
                if node.level:  # a relative import inside the physics package
                    continue
                root = (node.module or "").split(".")[0]
                assert root in sys.stdlib_module_names, (path.name, node.module)
                assert root not in forbidden, (path.name, node.module)
                assert root != "railway_headway_sim", (path.name, node.module)

    # no cycle is possible: (a) the physics modules import nothing but the standard library
    # and their own submodule (checked above), and (b) the physics package is imported only
    # by its single declared consumer - so a cycle back into it from a would-be dependency
    # is impossible.
    # Declared adaptation A8 (Phase 6B): Stage 6B delivers the Rolling Stock page, which
    # plots the two series the physics package samples, so *one* module outside the package
    # now imports it on purpose and the previous "leaf" claim ("no importer at all") cannot
    # hold. The claim is restated as an **exact allow-list of one file**: any other importer
    # - a model, a validator, the infrastructure, the controller or another page - still
    # fails this test, so the direction of the dependency graph is still asserted, not
    # merely hoped for. Stage 6B's own TEST P6-046 re-asserts the same import direction.
    importers: list[str] = []
    for path in sorted(_PACKAGE_DIR.rglob("*.py")):
        if _PHYSICS_DIR in path.parents or "tests" in path.parts:
            # the physics package itself and the test modules (which import it on purpose)
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith("railway_headway_sim.physics"):
                        importers.append(f"{path.relative_to(_PACKAGE_DIR)}:{alias.name}")
            elif isinstance(node, ast.ImportFrom):
                modules = [node.module or ""]
                if node.level:
                    modules = ["." * node.level + (node.module or "")]
                if any("physics" in module for module in modules):
                    importers.append(f"{path.relative_to(_PACKAGE_DIR)}:{node.module}")
    allowed_importers = {"ui/rolling_stock_page.py"}
    assert {importer.split(":", 1)[0] for importer in importers} == allowed_importers, (
        f"the physics package must be imported only by {sorted(allowed_importers)}: {importers}"
    )

    # the import machinery reaches the two modules consistently (no partially initialised
    # module remains behind a cycle)
    package = importlib.import_module("railway_headway_sim.physics")
    resistance = importlib.import_module("railway_headway_sim.physics.resistance")
    assert package.resistance is resistance
    assert sys.modules["railway_headway_sim.physics.resistance"] is resistance
    expected_exports = sorted(
        [*EXPECTED_SIGNATURES]
        + [
            "DAVIS_FORCE_UNIT",
            "DAVIS_SPEED_UNIT",
            "FORCE_UNIT",
            "GRADIENT_UNIT",
            "GRAVITY_MPS2",
            "RADIUS_UNIT",
        ]
    )
    # Declared adaptation A3 (Phase 5B): Stage 5B adds its four along-route functions to the
    # same package, so the Phase-5A exports cannot be pinned as the package's *entire*
    # __all__. The check is now an exact containment, which is strictly what the row means -
    # every Phase-5A export must still be there, and a missing one still fails.
    missing_exports = sorted(set(expected_exports) - set(package.__all__))
    assert missing_exports == [], f"Phase-5A exports missing from the package: {missing_exports}"


def test_p5_021_unit_discipline_of_names_and_docstrings():
    """TEST P5-021 - unit suffixes in names, units documented in every docstring."""
    module = _module()
    for name in ("davis_resistance_n", "gradient_force_n", "roeckl_curve_resistance_n", "total_resistance_n"):
        assert name.endswith("_n"), f"{name} must carry the force unit in its name"
        assert inspect.signature(getattr(module, name)).return_annotation in (float, "float")
    assert "roeckl_equivalent_gradient_permille".endswith("_permille")
    assert inspect.signature(module.is_roeckl_radius_usable).return_annotation in (bool, "bool")

    for name, parameters in EXPECTED_SIGNATURES.items():
        function = getattr(module, name)
        signature = inspect.signature(function)
        assert tuple(signature.parameters) == parameters, name
        docstring = inspect.getdoc(function) or ""
        assert docstring, f"{name} must carry a docstring"
        assert docstring.startswith("Return"), name
        for parameter in parameters:
            assert parameter in docstring, f"{name}: {parameter} is not documented"
            unit = UNIT_IN_ARGUMENT_NAME.get(parameter) or UNIT_TOKEN_IN_DOCSTRING[parameter]
            if parameter in UNIT_IN_ARGUMENT_NAME:
                assert UNIT_IN_ARGUMENT_NAME[parameter] in parameter, (name, parameter)
            assert unit in docstring, f"{name}: the unit of {parameter} is not documented"
    for name in ("davis_resistance_n", "gradient_force_n", "roeckl_curve_resistance_n", "total_resistance_n"):
        assert "[N]" in (inspect.getdoc(getattr(module, name)) or ""), name


def test_p5_022_functions_are_pure_deterministic_and_touch_no_project():
    """TEST P5-022 - bit-identical repeat calls; the loaded project never changes."""
    module = _module()
    mutable_globals = [
        name
        for name, value in vars(module).items()
        if not name.startswith("__") and isinstance(value, (list, dict, set, bytearray))
    ]
    assert mutable_globals == [], f"the module must hold no global mutable state: {mutable_globals}"

    calls = (
        lambda: davis_resistance_n(320.0, HSR_DAVIS_A, HSR_DAVIS_B, HSR_DAVIS_C),
        lambda: gradient_force_n(HSR_MASS_KG, -10.0),
        lambda: roeckl_curve_resistance_n(HSR_MASS_KG, 1800.0),
        lambda: roeckl_curve_resistance_n(HSR_MASS_KG, None),
        lambda: roeckl_equivalent_gradient_permille(1800.0),
        lambda: is_roeckl_radius_usable(1800.0),
        lambda: total_resistance_n(
            HSR_MASS_KG, 320.0, HSR_DAVIS_A, HSR_DAVIS_B, HSR_DAVIS_C, -10.0, 1800.0
        ),
    )
    before = hashlib.sha256(_PROTECTED_GRR01.read_bytes()).hexdigest()
    assert before == PROTECTED_GRR01_SHA256
    canonical_before = _canonical_hash()
    assert canonical_before == CANONICAL_GRR01_HASH

    for call in calls:
        first, second = call(), call()
        assert first == second
        assert repr(first) == repr(second)
        assert type(first) is type(second)
    assert hashlib.sha256(_PROTECTED_GRR01.read_bytes()).hexdigest() == before
    assert _canonical_hash() == canonical_before == CANONICAL_GRR01_HASH


def test_p5_023_section_d_scan_after_the_allowed_list_update():
    """TEST P5-023 - the five tokens are allowed; every other forbidden token still fails."""
    text = _SECTION_D_PATTERNS.read_text(encoding="utf-8")
    s1_tokens = _section_tokens("## 2. S1")
    s2_tokens = _section_tokens("## 3. S2")
    allowed = _section_tokens("## 2.1")

    assert allowed == ALLOWED_PHASE5A_TOKENS, allowed
    assert len(allowed) == 5
    forbidden_lower = {token.lower() for token in s1_tokens + s2_tokens}
    assert not (set(token.lower() for token in allowed) & forbidden_lower), (
        "the five allowed tokens must have left the forbidden lists"
    )
    assert len(s1_tokens) == 9, s1_tokens
    for token in (
        "headway",
        "blocking_time",
        "occupation_time",
        "residual_occupancy",
        "speed_envelope",
        "traction",
        "braking_curve",
        "monte_carlo",
        "uic406",
    ):
        assert token in s1_tokens, token
    assert "capacity" in s2_tokens
    assert "timetable" in s2_tokens
    for heading in ("## 2. S1", "## 2.1", "## 3. S2", "## 4. S3"):
        assert heading in text, heading

    # (a) the S1 matcher still rejects a reintroduced forbidden name
    probe_tree = ast.parse("def traction_force_n(mass_kg):\n    return mass_kg\n")
    probe_names = [
        node.name
        for node in ast.walk(probe_tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    ]
    assert [name for name in probe_names if any(t in name.lower() for t in s1_tokens)] == [
        "traction_force_n"
    ]
    for token in ("headway", "traction", "braking_curve", "speed_envelope", "uic406", "monte_carlo"):
        probe_name = f"probe_{token}_helper".lower()
        assert [candidate for candidate in s1_tokens if candidate in probe_name] == [token], token

    # (b) the S2 result-key surface still rejects a capacity result key on a probe document
    from railway_headway_sim.infrastructure import grr_audit

    assert "capacity" in grr_audit.FORBIDDEN_RESULT_KEYS
    assert "headway" in grr_audit.FORBIDDEN_RESULT_KEYS
    probe_finding = grr_audit._check_out_of_scope({"results": {"capacity": 0, "headway": 0}})
    assert probe_finding.severity != "OK", probe_finding
    assert grr_audit._check_out_of_scope({"results": {"static": 0}}).severity == "OK"

    # (c) the five allowed tokens may name something only inside the physics package;
    # declared adaptation A2 (Phase 5B): Stage 5B added physics/along_route.py to that same
    # package, so the surface is the package (nothing outside it is excused).
    allowed_lower = tuple(token.lower() for token in allowed)
    offenders: list[str] = []
    for path in sorted(_PACKAGE_DIR.rglob("*.py")):
        if "tests" in path.parts:
            continue
        for name in _declared_names(path):
            if (
                any(token in name.lower() for token in allowed_lower)
                and _PHYSICS_DIR not in path.parents
            ):
                offenders.append(f"{path.relative_to(_PACKAGE_DIR)}:{name}")
    assert offenders == [], f"Phase-5A tokens outside the physics package: {offenders}"
    phase5a_names = sorted(
        name for name in _declared_names(_MODULE_PATH) if any(t in name.lower() for t in allowed_lower)
    )
    assert phase5a_names == [
        "davis_resistance_n",
        "is_roeckl_radius_usable",
        "roeckl_curve_resistance_n",
        "roeckl_equivalent_gradient_permille",
    ], phase5a_names

    # (d) "signalling" is not token-matched by the Section-D pattern lists (a documented
    # boundary of the scan, §5 of the document). It is guarded instead on the delivered
    # surfaces: no *function* anywhere in the package carries the word, the only declared
    # name that does is the Phase-1 data container of the (empty) signalling catalogue,
    # which stores fields and computes nothing, and the Signalling page of the UI is still
    # an explicit placeholder.
    assert "signalling" not in {token.lower() for token in s1_tokens + s2_tokens}
    signalling_functions: list[str] = []
    signalling_classes: list[str] = []
    for path in sorted(_PACKAGE_DIR.rglob("*.py")):
        if "tests" in path.parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and "signalling" in node.name.lower():
                signalling_functions.append(f"{path.relative_to(_PACKAGE_DIR)}:{node.name}")
            if isinstance(node, ast.ClassDef) and "signalling" in node.name.lower():
                signalling_classes.append(f"{path.relative_to(_PACKAGE_DIR)}:{node.name}")
    assert signalling_functions == [], signalling_functions
    assert signalling_classes == ["models/project.py:SignallingContainer"], signalling_classes

    from railway_headway_sim.models.project import SignallingContainer

    assert hasattr(SignallingContainer, "model_fields"), (
        "the signalling container must stay a data container, not a behaviour"
    )
    assert sorted(SignallingContainer.model_fields) == [
        "rule_set_template",
        "signals",
        "simulation_time_step_s",
    ]
    from railway_headway_sim.ui.formatting import placeholder_html
    from railway_headway_sim.ui.placeholder_pages import PLANNED_PAGES

    assert "Signalling" in PLANNED_PAGES
    placeholder = placeholder_html(
        "Signalling", PLANNED_PAGES["Signalling"], phase_note="Not part of Phase 5A."
    )
    assert "PLANNED FOR LATER DEVELOPMENT PHASE" in placeholder
    assert "performs no calculations" in placeholder


# ---------------------------------------------------------------------------
# P5-024 - the suite registration and the collected total
# ---------------------------------------------------------------------------
def test_p5_024_phase5a_suite_is_registered_and_counted():
    """TEST P5-024 - the Phase-5A table is registered; the earlier six are unchanged."""
    source = Path(__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    acceptance_ids: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_p5_"):
            assert isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant), node.name
            text = str(node.body[0].value.value)
            match = re.search(r"\bP5-\d{3}\b", text)
            assert match, node.name
            acceptance_ids.append(match.group(0))
    assert sorted(acceptance_ids) == [f"P5-{number:03d}" for number in range(1, 25)]
    assert len(acceptance_ids) == 24

    conftest_text = _CONFTEST.read_text(encoding="utf-8")
    assert "PHASE-5A TESTS (TEST P5-001 ... TEST P5-024)" in conftest_text
    for earlier in (
        "PHASE-1 ACCEPTANCE TESTS (TEST P1-001 ... TEST P1-012)",
        "PHASE-2 TESTS (TEST P2-001 ... TEST P2-028)",
        "GRR-01 REGISTRY REGRESSIONS (TEST P2-REG-G001 ... TEST P2-REG-G005)",
        "PHASE-3 TESTS (TEST P3-001 ... TEST P3-026)",
        "PHASE-4A TESTS (TEST P4-001 ... TEST P4-030)",
        "PHASE-4B TESTS (TEST P4-031 ... TEST P4-048)",
    ):
        assert earlier in conftest_text, earlier
    assert "test_phase5a_resistance" not in conftest_text.split("PHASE-5A")[0], (
        "the earlier tables must not list the Phase-5A module"
    )

    builder_text = _INVENTORY_BUILDER.read_text(encoding="utf-8")
    assert '"phase5a"' in builder_text
    assert "test_phase5a_resistance.py" in builder_text
    assert "Phase-5A suite (TEST P5-001 … TEST P5-024)" in builder_text
    assert 'totals["phase5a"]' in builder_text

    # Declared adaptation A4 (Phase 5B): the two literal pins of the Phase-5A inventory text
    # ("... = `199` collected items", "Total (all seven suites) | `199`") cannot survive a later
    # stage, because docs/TEST_INVENTORY.md is a generated file whose totals and suite count
    # follow the collected suite. They are replaced by an exact structural check of the same
    # two facts: the canonical decomposition must sum to its own stated total, the totals row
    # must state that same number and count its suites, and the Phase-5A suite must still be
    # listed with its own range and rows.
    inventory = _INVENTORY.read_text(encoding="utf-8")
    decomposition = re.search(r"`(\d+(?: \+ \d+)+) = (\d+)` collected items", inventory)
    assert decomposition, "the canonical decomposition string is missing"
    parts = [int(part) for part in decomposition.group(1).split(" + ")]
    total = int(decomposition.group(2))
    assert sum(parts) == total, (parts, total)
    totals_row = re.search(
        r"\| \*\*Total \(all (\w+) suites\)\*\* \| \*\*(\d+)\*\* \|", inventory
    )
    assert totals_row, "the totals row is missing"
    # Declared adaptation A9 (Phase 6B): the totals row of the generated inventory now
    # counts ten suites; the map gained the matching word and nothing else changed.
    number_words = {"five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}
    assert number_words[totals_row.group(1)] == len(parts), totals_row.group(0)
    assert int(totals_row.group(2)) == total, totals_row.group(0)
    assert "Phase-5A suite (TEST P5-001 … TEST P5-024)" in inventory
    assert "| `P5-024` |" in inventory
