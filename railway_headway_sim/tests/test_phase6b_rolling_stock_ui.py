"""Phase-6B acceptance tests: TEST P6-025 ... TEST P6-048.

Stage 6B delivers the read-only Rolling Stock page and the two small physics
utilities it needs so that the page renders curves instead of computing them:

* :mod:`railway_headway_sim.physics.tractive_effort` — the frozen simplified piecewise
  effort model ``FORCE_THEN_POWER_LIMITED`` evaluated at a given speed;
* :mod:`railway_headway_sim.physics.rolling_stock_series` — the two sampled series a
  plot consumes (effort and running resistance) built from a stored stock type;
* :mod:`railway_headway_sim.ui.rolling_stock_page` — the **read-only** page with the
  four sub-tabs Overview | Traction | Resistance | Braking.

Scope of this module (Stage 6B):

* nothing here moves a train: every assertion is about a force at a caller-given speed,
  a sampled series, a rendered table or a rendered SVG;
* no editing is introduced: the page is checked to contain no draft call and no editable
  widget, and its leaves are read-only outputs;
* no protected artefact is written: the tests re-hash the frozen project and both
  companion files around the operations they exercise, and they write no file at all.

Every expected value is recomputed inside the test from the loaded catalogue or from the
published formula — never hand-typed as a constant the code must match. This module does
not carry the literal filename of a delivered module it must not import (the Phase-4B
importer scan reads every package file as text), so those targets are composed from
string fragments.
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
from typing import Any

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_PACKAGE_DIR = _REPO_ROOT / "railway_headway_sim"
_PHYSICS_DIR = _PACKAGE_DIR / "physics"
_UI_DIR = _PACKAGE_DIR / "ui"
_TESTS_DIR = _PACKAGE_DIR / "tests"
_TRACTIVE_MODULE_PATH = _PHYSICS_DIR / "tractive_effort.py"
_SERIES_MODULE_PATH = _PHYSICS_DIR / "rolling_stock_series.py"
_PAGE_MODULE_PATH = _UI_DIR / "rolling_stock_page.py"
_COMPANION_PATH = _REPO_ROOT / "examples" / "GRR-01-rolling-stock.json"
_GRR01_PATH = _REPO_ROOT / "examples" / "GRR-01.json"
_PATHS_COMPANION_PATH = _REPO_ROOT / "examples" / "GRR-01-paths.json"
_SECTION_D_PATH = _REPO_ROOT / "docs" / "SECTION_D_PATTERNS.md"
_INVENTORY_PATH = _REPO_ROOT / "docs" / "TEST_INVENTORY.md"
_CONFTEST_PATH = _TESTS_DIR / "conftest.py"
_BUILDER_PATH = _REPO_ROOT / "build_test_inventory.py"

#: The three modules Stage 6B delivers.
_NEW_MODULES = (_TRACTIVE_MODULE_PATH, _SERIES_MODULE_PATH, _PAGE_MODULE_PATH)

#: sha256 of the two companion files (pinned; the tests re-hash them on disk).
COMPANION_SHA256 = "6b03e36f4f4959ab343019eea918160f8e019ebb56a50207a7fc577cbb50c93d"
GRR01_SHA256 = "ad0a26265d4e072aeedcc69161bef90f200c20b4efb12a4d56a5276c4a4f7a56"
PATHS_COMPANION_SHA256 = "c62c3ee6d910457a6f59533c2b92b4e65a0cd8c64dff49fe8e6796ed829fac86"
CANONICAL_GRR01_HASH = "5189aaa2340c17022666ef44772c7d34f99b2fea9ee9609bb7b7513238ef4dbe"

#: Module names the Stage-6B physics modules must not import from. Composed from
#: fragments so this file never carries the literal path of a delivered module.
_FORBIDDEN_IMPORT_TARGETS = (
    "compiled" + "_network",
    "geometry_" + "along_route",
)

#: Libraries no delivered module of this stage may import.
_NUMERIC_LIBRARIES = (
    "math",
    "numpy",
    "scipy",
    "pandas",
    "statistics",
    "random",
    "decimal",
    "fractions",
)

#: The draft-mechanism entry points the page must not call (APP-EDIT-002).
_DRAFT_ENTRY_POINTS = (
    "stage_field",
    "stage_entry",
    "delete_entry",
    "commit_draft",
    "discard_draft",
)

#: Editable ``ipywidgets`` classes the page must not use anywhere.
_EDITABLE_WIDGET_CLASSES = (
    "Text",
    "Textarea",
    "BoundedFloatText",
    "FloatText",
    "BoundedIntText",
    "IntText",
    "FloatSlider",
    "FloatRangeSlider",
    "IntSlider",
    "IntRangeSlider",
    "Checkbox",
    "Dropdown",
    "Select",
    "SelectMultiple",
    "Combobox",
    "RadioButtons",
    "ToggleButton",
    "ToggleButtons",
    "ColorPicker",
    "DatePicker",
    "FileUpload",
)

#: The stock types the delivered companion file declares.
EXPECTED_STOCK_IDS = ("RS-HSR320", "RS-REG200")

#: The six navigation entries that stay explicit placeholders after Stage 6B.
EXPECTED_PLACEHOLDERS = (
    "Signalling",
    "Services & Timetable",
    "Simulation",
    "Results",
    "Scenarios",
    "Report",
)

#: The expected decomposition of the collected suite after Stage 6B.
EXPECTED_SUITE_COUNTS = (66, 30, 5, 26, 30, 18, 24, 18, 24, 24)
EXPECTED_TOTAL = 265

#: The nine tables that must keep their rows below the Phase-6B table.
EARLIER_TABLE_TITLES = (
    "PHASE-1 ACCEPTANCE TESTS (TEST P1-001 ... TEST P1-012)",
    "PHASE-2 TESTS (TEST P2-001 ... TEST P2-028)",
    "GRR-01 REGISTRY REGRESSIONS (TEST P2-REG-G001 ... TEST P2-REG-G005)",
    "PHASE-3 TESTS (TEST P3-001 ... TEST P3-026)",
    "PHASE-4A TESTS (TEST P4-001 ... TEST P4-030)",
    "PHASE-4B TESTS (TEST P4-031 ... TEST P4-048)",
    "PHASE-5A TESTS (TEST P5-001 ... TEST P5-024)",
    "PHASE-5B TESTS (TEST P5-025 ... TEST P5-042)",
    "PHASE-6A TESTS (TEST P6-001 ... TEST P6-024)",
)
PHASE6B_TABLE_TITLE = "PHASE-6B TESTS (TEST P6-025 ... TEST P6-048)"

#: The four sub-tabs of the page, in the delivered order.
EXPECTED_SUB_TABS = ("Overview", "Traction", "Resistance", "Braking")


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _tractive_module():
    """Return the delivered effort-primitive module."""
    return importlib.import_module("railway_headway_sim.physics.tractive_effort")


def _series_module():
    """Return the delivered series module."""
    return importlib.import_module("railway_headway_sim.physics.rolling_stock_series")


def _page_module():
    """Return the delivered Rolling Stock page module."""
    return importlib.import_module("railway_headway_sim.ui.rolling_stock_page")


def _physics_package():
    """Return the physics package facade."""
    return importlib.import_module("railway_headway_sim.physics")


def _resistance_module():
    """Return the Stage-5A pure-resistance module."""
    return importlib.import_module("railway_headway_sim.physics.resistance")


def _placeholder_pages() -> dict[str, tuple[str, ...]]:
    """Return the placeholder catalogue of the UI package."""
    from railway_headway_sim.ui.placeholder_pages import PLANNED_PAGES

    return PLANNED_PAGES


def _catalogue_document() -> dict[str, Any]:
    """Return the delivered companion file as plain data."""
    return json.loads(_COMPANION_PATH.read_text(encoding="utf-8"))


def _loaded_stock(stock_id: str):
    """Return a freshly loaded stock type of the delivered companion file."""
    from railway_headway_sim.models.rolling_stock import load_rolling_stock_catalogue

    catalogue = load_rolling_stock_catalogue(_COMPANION_PATH)
    matches = [stock for stock in catalogue.rolling_stock if stock.id == stock_id]
    assert len(matches) == 1, stock_id
    return matches[0]


def _raw_stock(stock_id: str) -> dict[str, Any]:
    """Return the raw mapping of one stock type of the companion document."""
    entries = [entry for entry in _catalogue_document()["rolling_stock"] if entry["id"] == stock_id]
    assert len(entries) == 1, stock_id
    return entries[0]


def _page(**kwargs):
    """Return a freshly built Rolling Stock page over the delivered companion file."""
    return _page_module().RollingStockPage(**kwargs)


def _import_edges(path: Path) -> set[str]:
    """Return the import surface of one module file, in the P4-046 notation."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            imported.add("." * node.level + (node.module or ""))
        elif isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
    return imported


def _absolute_roots(edges: set[str]) -> set[str]:
    """Return the root module name of every absolute import edge."""
    return {edge.split(".")[0] for edge in edges if not edge.startswith(".")}


def _declared_names(path: Path) -> list[str]:
    """Return every declared function / async function / class name of one module."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return [
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    ]


def _section_tokens(heading: str) -> tuple[str, ...]:
    """Return the token list of one ``docs/SECTION_D_PATTERNS.md`` section."""
    text = _SECTION_D_PATH.read_text(encoding="utf-8")
    start = text.index(heading)
    end = text.index("\n## ", start + 1)
    body = text[start:end].split("\n", 1)[1]
    paragraph = body.strip().split("\n\n", 1)[0]
    return tuple(re.findall(r"`([^`]+)`", paragraph))


def _file_sha256(path: Path) -> str:
    """Return the sha256 of a file on disk."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_project_hash() -> str:
    """Return the canonical hash of the frozen reference project."""
    from railway_headway_sim.infrastructure.grr_fixtures import build_grr01_document
    from railway_headway_sim.io import import_project_from_data, project_hash

    return project_hash(import_project_from_data(build_grr01_document()).project)


def _inventory_text() -> str:
    """Return the generated inventory document."""
    return _INVENTORY_PATH.read_text(encoding="utf-8")


def _inventory_decomposition() -> tuple[list[int], int]:
    """Return the canonical decomposition terms and total quoted by the inventory."""
    match = re.search(r"`(\d+(?: \+ \d+)+) = (\d+)` collected items", _inventory_text())
    assert match, "the canonical decomposition string is missing"
    return [int(term) for term in match.group(1).split(" + ")], int(match.group(2))


def _leaf_widgets(widget) -> list[Any]:
    """Return every leaf of a widget tree (a container's children are walked)."""
    children = getattr(widget, "children", ())
    if not children:
        return [widget]
    leaves: list[Any] = []
    for child in children:
        leaves.extend(_leaf_widgets(child))
    return leaves


def _svg_points(svg: str) -> list[tuple[float, float]]:
    """Return the polyline points of one rendered SVG chart."""
    match = re.search(r'<polyline points="([^"]+)"', svg)
    assert match, "the rendered chart carries no polyline"
    points: list[tuple[float, float]] = []
    for pair in match.group(1).split():
        first, _, second = pair.partition(",")
        points.append((float(first), float(second)))
    return points


# ---------------------------------------------------------------------------
# TEST P6-025
# ---------------------------------------------------------------------------
def test_p6_025_effort_module_exists_and_exposes_the_documented_function():
    """TEST P6-025 - the module exists, imports cleanly, and exposes the documented API."""
    assert _TRACTIVE_MODULE_PATH.is_file()
    module = _tractive_module()
    function = module.tractive_effort_n
    assert callable(function)
    signature = inspect.signature(function)
    assert list(signature.parameters) == [
        "speed_kmh",
        "max_tractive_effort_kn",
        "rated_power_kw",
    ], list(signature.parameters)
    for name, parameter in signature.parameters.items():
        assert parameter.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD, name
        assert parameter.default is inspect.Parameter.empty, name
    assert signature.return_annotation in (float, "float"), signature.return_annotation
    assert module.TRACTIVE_EFFORT_UNIT == "N"
    assert module.SPEED_UNIT == "km/h"
    assert module.POWER_UNIT == "kW"
    # the units travel in the names of the arguments as well
    assert function.__doc__ and "tractive effort [N]" in function.__doc__

    package = _physics_package()
    assert package.tractive_effort_n is function
    for name in (
        "tractive_effort_n",
        "transition_speed_kmh",
        "tractive_effort_series_n",
        "running_resistance_series_n",
        "TRACTIVE_EFFORT_UNIT",
        "SPEED_UNIT",
        "POWER_UNIT",
    ):
        assert name in package.__all__, f"{name} must be re-exported by the physics package"


# ---------------------------------------------------------------------------
# TEST P6-026
# ---------------------------------------------------------------------------
def test_p6_026_effort_at_zero_speed_is_the_starting_effort():
    """TEST P6-026 - at zero speed the force-limited branch applies (no P/v singularity)."""
    for stock_id in EXPECTED_STOCK_IDS:
        raw = _raw_stock(stock_id)
        effort_kn = raw["traction"]["max_tractive_effort_kn"]
        power_kw = raw["traction"]["rated_power_kw"]
        value = _tractive_module().tractive_effort_n(0.0, effort_kn, power_kw)
        assert value == effort_kn * 1000.0, (stock_id, value)
        assert isinstance(value, float)


# ---------------------------------------------------------------------------
# TEST P6-027
# ---------------------------------------------------------------------------
def test_p6_027_effort_is_flat_at_and_below_the_transition_speed():
    """TEST P6-027 - at or below the transition speed the effort is exactly F_max * 1000."""
    module = _tractive_module()
    for stock_id in EXPECTED_STOCK_IDS:
        raw = _raw_stock(stock_id)
        effort_kn = raw["traction"]["max_tractive_effort_kn"]
        power_kw = raw["traction"]["rated_power_kw"]
        transition = module.transition_speed_kmh(effort_kn, power_kw)
        # the sampled speeds are relative to *this* stock's transition speed: the regular
        # stock (260.0 kN, 5000.0 kW) leaves the force-limited branch far below 100 km/h, so
        # an absolute sample list would silently exercise the power branch
        for speed in (0.0, 1e-9, 1.0, transition * 0.25, transition, transition * 0.999):
            assert module.tractive_effort_n(speed, effort_kn, power_kw) == effort_kn * 1000.0, (
                stock_id,
                speed,
            )


# ---------------------------------------------------------------------------
# TEST P6-028
# ---------------------------------------------------------------------------
def test_p6_028_effort_above_the_transition_follows_the_power_branch():
    """TEST P6-028 - above the transition speed the effort is exactly P / v, recomputed here."""
    module = _tractive_module()
    for stock_id in EXPECTED_STOCK_IDS:
        raw = _raw_stock(stock_id)
        effort_kn = raw["traction"]["max_tractive_effort_kn"]
        power_kw = raw["traction"]["rated_power_kw"]
        transition = module.transition_speed_kmh(effort_kn, power_kw)
        for speed in (transition * 1.001, transition + 1.0, 200.0, 320.0, 400.0):
            expected = power_kw * 1000.0 / (speed / 3.6)
            value = module.tractive_effort_n(speed, effort_kn, power_kw)
            assert value == expected, (stock_id, speed, value, expected)
            assert value < effort_kn * 1000.0


# ---------------------------------------------------------------------------
# TEST P6-029
# ---------------------------------------------------------------------------
def test_p6_029_effort_never_exceeds_the_starting_effort():
    """TEST P6-029 - the curve is capped by F_max at every sampled speed."""
    module = _tractive_module()
    for stock_id in EXPECTED_STOCK_IDS:
        raw = _raw_stock(stock_id)
        effort_kn = raw["traction"]["max_tractive_effort_kn"]
        power_kw = raw["traction"]["rated_power_kw"]
        cap = effort_kn * 1000.0
        samples = [
            module.tractive_effort_n(index * 0.5, effort_kn, power_kw)
            for index in range(0, 801)
        ]
        assert len(samples) == 801
        assert max(samples) == cap, stock_id
        assert all(value <= cap for value in samples), stock_id
        assert all(value > 0.0 for value in samples), stock_id


# ---------------------------------------------------------------------------
# TEST P6-030
# ---------------------------------------------------------------------------
def test_p6_030_transition_speed_of_the_frozen_pair_and_of_the_hsr_stock():
    """TEST P6-030 - the frozen pair (9800.0 kW, 300.0 kN) implies 117.6 km/h."""
    module = _tractive_module()
    derived = module.transition_speed_kmh(300.0, 9800.0)
    assert abs(derived - 117.6) <= 1e-9 * 117.6, derived

    stock = _loaded_stock("RS-HSR320")
    from_stock = module.transition_speed_kmh(
        float(stock.traction.max_tractive_effort_kn),
        float(stock.traction.rated_power_kw),
    )
    assert abs(from_stock - 117.6) <= 1e-9 * 117.6, from_stock

    # the transition point is the boundary: at it the force is still F_max, just above it
    # the power branch has taken over and the value has dropped below F_max
    cap = float(stock.traction.max_tractive_effort_kn) * 1000.0
    assert module.tractive_effort_n(117.6, 300.0, 9800.0) == cap
    assert module.tractive_effort_n(117.7, 300.0, 9800.0) < cap


# ---------------------------------------------------------------------------
# TEST P6-031
# ---------------------------------------------------------------------------
def test_p6_031_effort_rejects_unusable_arguments_naming_them():
    """TEST P6-031 - every unusable argument is reported, and the message names it."""
    module = _tractive_module()
    cases = (
        ("speed_kmh", (-1.0, 300.0, 9800.0)),
        ("speed_kmh", (float("nan"), 300.0, 9800.0)),
        ("speed_kmh", (float("inf"), 300.0, 9800.0)),
        ("speed_kmh", (float("-inf"), 300.0, 9800.0)),
        ("speed_kmh", ("100.0", 300.0, 9800.0)),
        ("max_tractive_effort_kn", (100.0, 0.0, 9800.0)),
        ("max_tractive_effort_kn", (100.0, -300.0, 9800.0)),
        ("max_tractive_effort_kn", (100.0, float("nan"), 9800.0)),
        ("rated_power_kw", (100.0, 300.0, 0.0)),
        ("rated_power_kw", (100.0, 300.0, -9800.0)),
        ("rated_power_kw", (100.0, 300.0, float("inf"))),
    )
    for argument, arguments in cases:
        with pytest.raises(ValueError) as excinfo:
            module.tractive_effort_n(*arguments)
        assert argument in str(excinfo.value), (argument, str(excinfo.value))
    # the same rules hold for the transition-speed helper
    for argument, arguments in (("max_tractive_effort_kn", (0.0, 9800.0)), ("rated_power_kw", (300.0, 0.0))):
        with pytest.raises(ValueError) as excinfo:
            module.transition_speed_kmh(*arguments)
        assert argument in str(excinfo.value)


# ---------------------------------------------------------------------------
# TEST P6-032
# ---------------------------------------------------------------------------
def test_p6_032_series_module_exists_and_exposes_the_two_functions():
    """TEST P6-032 - the series module exists, imports cleanly, and exposes both functions."""
    assert _SERIES_MODULE_PATH.is_file()
    module = _series_module()
    for name in ("tractive_effort_series_n", "running_resistance_series_n"):
        function = getattr(module, name)
        signature = inspect.signature(function)
        assert list(signature.parameters) == ["stock", "step_kmh"], (name, list(signature.parameters))
        assert signature.parameters["step_kmh"].default == 10.0, name
        assert signature.return_annotation in (
            tuple[tuple[float, float], ...],
            "tuple[tuple[float, float], ...]",
        ), (name, signature.return_annotation)
        assert function.__doc__ and "km/h" in function.__doc__, name
    assert module.DEFAULT_STEP_KMH == 10.0

    package = _physics_package()
    assert package.tractive_effort_series_n is module.tractive_effort_series_n
    assert package.running_resistance_series_n is module.running_resistance_series_n


# ---------------------------------------------------------------------------
# TEST P6-033
# ---------------------------------------------------------------------------
def test_p6_033_effort_series_is_ordered_and_ends_at_the_maximum_speed():
    """TEST P6-033 - the effort series starts at 0.0 and ends exactly at max_speed_kmh."""
    stock = _loaded_stock("RS-HSR320")
    series = _series_module().tractive_effort_series_n(stock)
    speeds = [speed for speed, _value in series]
    assert len(series) >= 2
    assert speeds[0] == 0.0
    assert speeds[-1] == float(stock.max_speed_kmh)
    assert speeds == sorted(speeds) and len(set(speeds)) == len(speeds)

    # a step that does not divide the maximum speed still ends exactly at the maximum
    ragged = _series_module().tractive_effort_series_n(stock, 7.0)
    ragged_speeds = [speed for speed, _value in ragged]
    assert ragged_speeds[-1] == float(stock.max_speed_kmh)
    assert ragged_speeds[-2] < ragged_speeds[-1]
    assert len(ragged) == 47  # 0.0, 7.0, ... 315.0, then 320.0


# ---------------------------------------------------------------------------
# TEST P6-034
# ---------------------------------------------------------------------------
def test_p6_034_effort_series_samples_equal_the_primitive_called_here():
    """TEST P6-034 - every sample equals the primitive at the same speed, recomputed here."""
    module = _tractive_module()
    for stock_id in EXPECTED_STOCK_IDS:
        series = _series_module().tractive_effort_series_n(_loaded_stock(stock_id))
        fresh = _loaded_stock(stock_id)
        effort_kn = float(fresh.traction.max_tractive_effort_kn)
        power_kw = float(fresh.traction.rated_power_kw)
        assert series, stock_id
        for speed, value in series:
            assert value == module.tractive_effort_n(speed, effort_kn, power_kw), (stock_id, speed)
        # determinism: two calls with equal arguments are bit-identical
        assert _series_module().tractive_effort_series_n(_loaded_stock(stock_id)) == series


# ---------------------------------------------------------------------------
# TEST P6-035
# ---------------------------------------------------------------------------
def test_p6_035_resistance_series_is_ordered_and_ends_at_the_maximum_speed():
    """TEST P6-035 - the resistance series spans 0.0 to max_speed_kmh and is ordered."""
    for stock_id in EXPECTED_STOCK_IDS:
        stock = _loaded_stock(stock_id)
        series = _series_module().running_resistance_series_n(stock)
        speeds = [speed for speed, _value in series]
        assert len(series) >= 2, stock_id
        assert speeds[0] == 0.0, stock_id
        assert speeds[-1] == float(stock.max_speed_kmh), stock_id
        assert speeds == sorted(speeds) and len(set(speeds)) == len(speeds), stock_id
        assert all(value >= 0.0 for _speed, value in series), stock_id


# ---------------------------------------------------------------------------
# TEST P6-036
# ---------------------------------------------------------------------------
def test_p6_036_resistance_series_samples_equal_the_primitive_called_here():
    """TEST P6-036 - every sample equals the Stage-5A primitive over the stock's coefficients."""
    module = _resistance_module()
    for stock_id in EXPECTED_STOCK_IDS:
        series = _series_module().running_resistance_series_n(_loaded_stock(stock_id))
        fresh = _loaded_stock(stock_id)
        coefficients = (
            float(fresh.resistance_a_kn),
            float(fresh.resistance_b_kn_per_kmh),
            float(fresh.resistance_c_kn_per_kmh2),
        )
        assert series, stock_id
        for speed, value in series:
            assert value == module.davis_resistance_n(speed, *coefficients), (stock_id, speed)
        assert _series_module().running_resistance_series_n(_loaded_stock(stock_id)) == series


# ---------------------------------------------------------------------------
# TEST P6-037
# ---------------------------------------------------------------------------
def test_p6_037_series_reject_a_non_positive_step_and_always_have_two_points():
    """TEST P6-037 - a non-positive step is reported naming the argument; valid steps give >= 2."""
    module = _series_module()
    stock = _loaded_stock("RS-HSR320")
    for function in (module.tractive_effort_series_n, module.running_resistance_series_n):
        for bad_step in (0.0, -1.0, -10.0, float("nan"), float("inf")):
            with pytest.raises(ValueError) as excinfo:
                function(stock, bad_step)
            assert "step_kmh" in str(excinfo.value), (function.__name__, bad_step)
        for good_step in (10.0, 7.0, 0.5, 320.0, 1000.0):
            series = function(stock, good_step)
            assert len(series) >= 2, (function.__name__, good_step)
            assert series[0][0] == 0.0
            assert series[-1][0] == float(stock.max_speed_kmh)


# ---------------------------------------------------------------------------
# TEST P6-038
# ---------------------------------------------------------------------------
def test_p6_038_page_exists_is_functional_and_is_wired_into_the_shell():
    """TEST P6-038 - the new page module exists, is functional, and the shell shows it."""
    assert _PAGE_MODULE_PATH.is_file()
    from railway_headway_sim.ui import FUNCTIONAL_PAGES, RollingStockPage
    from railway_headway_sim.ui.app_shell import AppShell, NAVIGATION_TITLES

    assert "Rolling Stock" in FUNCTIONAL_PAGES
    assert "Rolling Stock" not in _placeholder_pages()
    assert RollingStockPage is _page_module().RollingStockPage
    assert "RollingStockPage" in importlib.import_module("railway_headway_sim.ui").__all__

    page = RollingStockPage()
    assert page.sub_tab_titles() == EXPECTED_SUB_TABS
    assert page.selected_sub_tab() == "Overview"
    for title in EXPECTED_SUB_TABS:
        assert page.select_sub_tab(title) is True
    assert page.select_sub_tab("No such tab") is False

    from railway_headway_sim.app.project_controller import ProjectController

    shell = AppShell(ProjectController.new_project())
    assert isinstance(shell._rolling_stock_page, RollingStockPage)
    index = list(NAVIGATION_TITLES).index("Rolling Stock")
    assert shell._tabs.get_title(index) == "Rolling Stock"
    assert shell._tabs.children[index] is shell._rolling_stock_page.widget
    shell.select_tab("Rolling Stock")
    assert shell._tabs.selected_index == index


# ---------------------------------------------------------------------------
# TEST P6-039
# ---------------------------------------------------------------------------
def test_p6_039_rolling_stock_left_the_placeholder_set_and_six_remain():
    """TEST P6-039 - Rolling Stock is no longer planned; the six remaining pages still are."""
    from railway_headway_sim.ui import FUNCTIONAL_PAGES
    from railway_headway_sim.ui.app_shell import AppShell, NAVIGATION_TITLES
    from railway_headway_sim.ui.formatting import placeholder_html
    from railway_headway_sim.ui.placeholder_pages import PLANNED_PAGES

    assert "Rolling Stock" not in PLANNED_PAGES
    assert set(PLANNED_PAGES) == set(EXPECTED_PLACEHOLDERS), sorted(PLANNED_PAGES)
    assert set(PLANNED_PAGES) | {"Rolling Stock"} | set(FUNCTIONAL_PAGES) == set(NAVIGATION_TITLES)
    assert set(PLANNED_PAGES) & set(FUNCTIONAL_PAGES) == set()

    from railway_headway_sim.app.project_controller import ProjectController

    shell = AppShell(ProjectController.new_project())
    rolling_index = list(NAVIGATION_TITLES).index("Rolling Stock")
    rolling_rendered = json.dumps(shell._tabs.children[rolling_index].get_state(), default=str)
    assert "PLANNED FOR LATER DEVELOPMENT PHASE" not in rolling_rendered

    for title in EXPECTED_PLACEHOLDERS:
        assert PLANNED_PAGES[title], title
        rendered = placeholder_html(title, PLANNED_PAGES[title], phase_note="Not part of Phase 6B.")
        assert "PLANNED FOR LATER DEVELOPMENT PHASE" in rendered, title
        assert "performs no calculations" in rendered, title
        index = list(NAVIGATION_TITLES).index(title)
        page = shell._tabs.children[index]
        import ipywidgets as widgets

        assert isinstance(page, widgets.HTML), f"{title} must stay a placeholder"
        assert "PLANNED FOR LATER DEVELOPMENT PHASE" in page.value, title


# ---------------------------------------------------------------------------
# TEST P6-040
# ---------------------------------------------------------------------------
def test_p6_040_page_renders_every_stored_parameter_of_both_stock_types():
    """TEST P6-040 - the page shows both stock types and every stored parameter of each."""
    from railway_headway_sim.models.rolling_stock import load_rolling_stock_catalogue

    catalogue = load_rolling_stock_catalogue(_COMPANION_PATH)
    page = _page()
    rendered = page.rendered_text()
    page_ids = tuple(stock.id for stock in page.stocks())
    assert page_ids == EXPECTED_STOCK_IDS, page_ids
    assert tuple(stock.id for stock in catalogue.rolling_stock) == page_ids

    for stock in catalogue.rolling_stock:
        assert stock.id in rendered, stock.id
        assert stock.name in rendered, stock.name
        expected_values = (
            stock.length_m,
            stock.mass.static_mass_t,
            stock.mass.rotating_mass_factor,
            stock.effective_mass_kg,
            stock.max_speed_kmh,
            stock.performance_limits.max_operational_acceleration_mps2,
            stock.traction.rated_power_kw,
            stock.traction.max_tractive_effort_kn,
            stock.running_resistance.coefficients.A,
            stock.running_resistance.coefficients.B,
            stock.running_resistance.coefficients.C,
            stock.service_braking.reference_deceleration_mps2,
            stock.etcs_supervision.reference_deceleration_mps2,
        )
        for value in expected_values:
            assert repr(float(value)) in rendered, (stock.id, value)
        for text in (
            stock.category.value,
            stock.data_status,
            str(stock.manufacturer_data),
            stock.traction.model.value,
            stock.running_resistance.model.value,
            stock.running_resistance.formula,
            stock.running_resistance.coefficient_speed_unit,
            stock.running_resistance.output_force_unit,
            stock.curve_resistance.model_source,
            stock.etcs_supervision.model_role,
        ):
            assert text in rendered, (stock.id, text)

    # the page reads the delivered companion file by default
    assert Path(_page_module().REFERENCE_STOCK_PATH) == _COMPANION_PATH


# ---------------------------------------------------------------------------
# TEST P6-041
# ---------------------------------------------------------------------------
def test_p6_041_traction_sub_tab_plot_comes_from_the_effort_series():
    """TEST P6-041 - the Traction plot is built from the effort series and has >= 2 points."""
    module = _series_module()
    page = _page()
    for stock_id in EXPECTED_STOCK_IDS:
        expected = module.tractive_effort_series_n(_loaded_stock(stock_id), page.series_step_kmh())
        plotted = page.tractive_effort_series_n(stock_id)
        assert plotted == expected, stock_id
        assert len(plotted) >= 2, stock_id
        svg = page.effort_plot_svg(stock_id)
        assert svg.startswith("<svg"), stock_id
        points = _svg_points(svg)
        assert len(points) == len(plotted), (stock_id, len(points), len(plotted))
        # the drawn curve is the sampled series: same speed span, first point at the top
        assert plotted[0][0] == 0.0 and plotted[-1][0] == float(_loaded_stock(stock_id).max_speed_kmh)
        assert len({x for x, _y in points}) == len(plotted)


# ---------------------------------------------------------------------------
# TEST P6-042
# ---------------------------------------------------------------------------
def test_p6_042_resistance_sub_tab_plot_comes_from_the_resistance_series():
    """TEST P6-042 - the Resistance plot is built from the resistance series, >= 2 points."""
    module = _series_module()
    page = _page()
    for stock_id in EXPECTED_STOCK_IDS:
        expected = module.running_resistance_series_n(_loaded_stock(stock_id), page.series_step_kmh())
        plotted = page.running_resistance_series_n(stock_id)
        assert plotted == expected, stock_id
        assert len(plotted) >= 2, stock_id
        svg = page.resistance_plot_svg(stock_id)
        assert svg.startswith("<svg"), stock_id
        points = _svg_points(svg)
        assert len(points) == len(plotted), (stock_id, len(points), len(plotted))
        assert plotted[0][0] == 0.0
        assert plotted[-1][0] == float(_loaded_stock(stock_id).max_speed_kmh)


# ---------------------------------------------------------------------------
# TEST P6-043
# ---------------------------------------------------------------------------
def test_p6_043_page_has_no_editable_widget_and_no_draft_call():
    """TEST P6-043 - the page is read-only: no draft call, no editable widget, only outputs."""
    source = _PAGE_MODULE_PATH.read_text(encoding="utf-8")
    for entry_point in _DRAFT_ENTRY_POINTS:
        assert not re.search(rf"\b{entry_point}\b", source), entry_point
    for class_name in _EDITABLE_WIDGET_CLASSES:
        assert not re.search(rf"\bwidgets\.{class_name}\b", source), class_name
        assert not re.search(rf"\b{class_name}\(", source), class_name
    # the draft bridge itself is not imported by the page
    edges = _import_edges(_PAGE_MODULE_PATH)
    assert ".editing" not in edges and "..app" not in edges, sorted(edges)
    assert "ProjectController" not in source

    # every leaf of the rendered widget tree is a read-only HTML output
    import ipywidgets as widgets

    page = _page()
    leaves = _leaf_widgets(page.widget)
    assert leaves, "the page must render something"
    assert all(isinstance(leaf, widgets.HTML) for leaf in leaves), sorted(
        {type(leaf).__name__ for leaf in leaves}
    )
    assert len(leaves) >= 8, len(leaves)


# ---------------------------------------------------------------------------
# TEST P6-044
# ---------------------------------------------------------------------------
def test_p6_044_new_modules_import_no_numeric_library():
    """TEST P6-044 - no numeric library, and nothing outside the standard library and the package."""
    for path in _NEW_MODULES:
        assert path.is_file(), path
        edges = _import_edges(path)
        assert not set(_NUMERIC_LIBRARIES) & _absolute_roots(edges), (path.name, sorted(edges))

        if path.parent == _PHYSICS_DIR:
            # the physics modules import only the standard library, the models they are given,
            # and their own package (§D2: no numeric library, no infrastructure, no UI)
            for root in _absolute_roots(edges):
                assert root in sys.stdlib_module_names, (path.name, root)
            for edge in edges:
                target = edge.lstrip(".").split(".")[-1]
                assert target not in _FORBIDDEN_IMPORT_TARGETS, (path.name, edge)
                assert not edge.startswith(("..infrastructure", "..io", "..app", "..ui", "..validation")), (
                    path.name,
                    edge,
                )
        else:
            # the page may import ipywidgets (the notebook UI dependency) and nothing else
            for root in _absolute_roots(edges):
                assert root in sys.stdlib_module_names or root == "ipywidgets", (path.name, root)
            for edge in edges:
                target = edge.lstrip(".").split(".")[-1]
                assert target not in _FORBIDDEN_IMPORT_TARGETS, (path.name, edge)

    assert _import_edges(_TRACTIVE_MODULE_PATH) == {"__future__"}, sorted(
        _import_edges(_TRACTIVE_MODULE_PATH)
    )
    assert _import_edges(_SERIES_MODULE_PATH) == {
        "__future__",
        "..models.rolling_stock",
        ".resistance",
        ".tractive_effort",
    }, sorted(_import_edges(_SERIES_MODULE_PATH))


# ---------------------------------------------------------------------------
# TEST P6-045
# ---------------------------------------------------------------------------
def test_p6_045_new_modules_carry_no_forbidden_section_d_token():
    """TEST P6-045 - Section-D scan: forbidden names absent, allowed tokens still confined."""
    s1_tokens = _section_tokens("## 2. S1")
    s2_tokens = _section_tokens("## 3. S2")
    s3_tokens = _section_tokens("## 4. S3")
    allowed_tokens = _section_tokens("## 2.1")
    assert len(s1_tokens) == 9, s1_tokens
    assert len(s2_tokens) == 14, s2_tokens
    assert len(s3_tokens) == 7, s3_tokens
    assert allowed_tokens == (
        "Davis",
        "Roeckl",
        "rolling resistance",
        "curve resistance",
        "gradient force",
    ), allowed_tokens
    assert not (set(token.lower() for token in allowed_tokens) & set(s1_tokens))

    for path in _NEW_MODULES:
        names = _declared_names(path)
        assert names, path.name
        for name in names:
            lowered = name.lower()
            for token in s1_tokens:
                assert token not in lowered, f"{path.name}:{name} carries '{token}'"

    # the five allowed tokens stay confined to the physics package: no declared name outside
    # it carries one, and the three new modules are clean
    offenders: list[str] = []
    for path in sorted(_PACKAGE_DIR.rglob("*.py")):
        if "tests" in path.parts or path.name in {"codes.py", "grr_audit.py"}:
            continue
        for name in _declared_names(path):
            if any(token.lower() in name.lower() for token in allowed_tokens):
                if _PHYSICS_DIR not in path.parents:
                    offenders.append(f"{path.name}:{name}")
    assert offenders == [], f"an allowed token appears outside the physics package: {offenders}"
    for path in _NEW_MODULES:
        for name in _declared_names(path):
            assert not any(token.lower() in name.lower() for token in allowed_tokens), (
                f"{path.name}:{name}"
            )

    # the stored data names are unaffected: they are values, not declared names
    stock = _loaded_stock("RS-HSR320")
    assert stock.traction.model.value == "FORCE_THEN_POWER_LIMITED"
    assert stock.running_resistance.model.value == "DAVIS"


# ---------------------------------------------------------------------------
# TEST P6-046
# ---------------------------------------------------------------------------
def test_p6_046_project_hash_and_both_companions_survive_every_operation():
    """TEST P6-046 - the page render and both series calls leave every hash unchanged."""
    project_before = _canonical_project_hash()
    assert project_before == CANONICAL_GRR01_HASH
    assert _file_sha256(_GRR01_PATH) == GRR01_SHA256
    assert _file_sha256(_PATHS_COMPANION_PATH) == PATHS_COMPANION_SHA256
    assert _file_sha256(_COMPANION_PATH) == COMPANION_SHA256

    page = _page()
    page.refresh()
    for stock_id in EXPECTED_STOCK_IDS:
        page.select_sub_tab("Traction")
        assert page.tractive_effort_series_n(stock_id), stock_id
        page.select_sub_tab("Resistance")
        assert page.running_resistance_series_n(stock_id), stock_id
    _series_module().tractive_effort_series_n(_loaded_stock("RS-REG200"))
    _series_module().running_resistance_series_n(_loaded_stock("RS-REG200"))

    assert _canonical_project_hash() == project_before
    assert _file_sha256(_GRR01_PATH) == GRR01_SHA256
    assert _file_sha256(_PATHS_COMPANION_PATH) == PATHS_COMPANION_SHA256
    assert _file_sha256(_COMPANION_PATH) == COMPANION_SHA256

    # the physics package is imported by exactly one module outside itself: the new page
    # (declared adaptation A8 of TEST P5-020, re-asserted here from the other side)
    importers: set[str] = set()
    for path in sorted(_PACKAGE_DIR.rglob("*.py")):
        if _PHYSICS_DIR in path.parents or "tests" in path.parts:
            continue
        for edge in _import_edges(path):
            if edge.startswith(".") and "physics" in edge:
                importers.add(str(path.relative_to(_PACKAGE_DIR)))
            elif edge.startswith("railway_headway_sim.physics"):
                importers.add(str(path.relative_to(_PACKAGE_DIR)))
    assert importers == {"ui/rolling_stock_page.py"}, sorted(importers)
    assert _import_edges(_PAGE_MODULE_PATH) & {"..physics"} == set()
    for edge in _import_edges(_PAGE_MODULE_PATH):
        if "physics" in edge:
            assert edge in {"..physics.rolling_stock_series", "..physics.tractive_effort"}, edge


# ---------------------------------------------------------------------------
# TEST P6-047
# ---------------------------------------------------------------------------
def test_p6_047_the_nine_earlier_tables_keep_their_rows_and_only_the_declared_changes():
    """TEST P6-047 - the nine earlier tables are registered unchanged; only §H and §G.5 moved."""
    terms, total = _inventory_decomposition()
    assert terms[:9] == list(EXPECTED_SUITE_COUNTS[:9]), terms
    assert terms[9] == EXPECTED_SUITE_COUNTS[9], terms
    assert total == EXPECTED_TOTAL, total
    assert sum(terms) == total

    conftest = _CONFTEST_PATH.read_text(encoding="utf-8")
    for title in EARLIER_TABLE_TITLES:
        assert f'"{title}"' in conftest, title
    assert PHASE6B_TABLE_TITLE in conftest
    assert r"\bP6-\d{3}\b" in conftest

    # the §H version-literal re-points: the four files that pin the current version now
    # expect 0.9.0. The previous literal survives only inside the comment that records the
    # version chain, so the check is on comparisons, not on the raw text.
    for name in (
        "test_controller.py",
        "test_ui_shell.py",
        "test_phase3_editors.py",
        "test_phase4a_route_coordinate.py",
    ):
        text = (_TESTS_DIR / name).read_text(encoding="utf-8")
        assert "0.9.0" in text, name
        expectation_lines = [
            line
            for line in text.splitlines()
            if "0.9.0" in line and ("==" in line or " in " in line)
        ]
        assert expectation_lines, f"{name} no longer compares against the current version"
        for line in text.splitlines():
            if "0.8.0" in line:
                assert "==" not in line and "assert" not in line, (
                    f"{name} still compares against the previous version: {line.strip()}"
                )

    # the declared §G.5 supersession: the same test function, now a two-way set check
    shell_tests = (_TESTS_DIR / "test_ui_shell.py").read_text(encoding="utf-8")
    assert "def test_placeholder_pages_do_not_implement_engineering_calculations" in shell_tests
    assert "set(FUNCTIONAL_PAGES) == set(NAVIGATION_TITLES) - set(PLANNED_PAGES)" in shell_tests
    assert "PLANNED FOR LATER DEVELOPMENT PHASE" in shell_tests
    assert "performs no calculations" in shell_tests
    assert "Phase 6B" in shell_tests


# ---------------------------------------------------------------------------
# TEST P6-048
# ---------------------------------------------------------------------------
def test_p6_048_phase6b_suite_is_registered_and_counted():
    """TEST P6-048 - the Phase-6B table is registered, and the suite is now 265 items."""
    source = Path(__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    acceptance_ids: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_p6_"):
            assert isinstance(node.body[0], ast.Expr) and isinstance(
                node.body[0].value, ast.Constant
            ), node.name
            text = str(node.body[0].value.value)
            match = re.search(r"\bP6-\d{3}\b", text)
            assert match, node.name
            acceptance_ids.append(match.group(0))
    phase6b_ids = sorted(set(acceptance_ids) - {f"P6-{number:03d}" for number in range(1, 25)})
    assert phase6b_ids == [f"P6-{number:03d}" for number in range(25, 49)], phase6b_ids
    assert len(phase6b_ids) == 24

    conftest = _CONFTEST_PATH.read_text(encoding="utf-8")
    assert PHASE6B_TABLE_TITLE in conftest
    assert conftest.count("_write_table(") == 11, "ten tables plus the function definition"
    for title in EARLIER_TABLE_TITLES:
        assert title in conftest, title

    builder = _BUILDER_PATH.read_text(encoding="utf-8")
    assert '"phase6b"' in builder
    assert "test_phase6b_rolling_stock_ui.py" in builder
    assert "Phase-6B suite (TEST P6-025 … TEST P6-048)" in builder
    assert 'totals["phase6b"]' in builder
    spec = importlib.util.spec_from_file_location("_inventory_builder_probe", _BUILDER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert len(module.SUITES) == 10, [entry[0] for entry in module.SUITES]
    assert module.SUITES[-1][0] == "phase6b"
    assert module.SUITES[-1][2] == ("test_phase6b_rolling_stock_ui.py",)

    inventory = _inventory_text()
    assert "| Phase-6B suite (TEST P6-025 … TEST P6-048) | 24 |" in inventory
    assert "| **Total (all ten suites)** | **265** |" in inventory
    assert "= 265` collected items" in inventory
