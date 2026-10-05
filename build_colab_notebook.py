"""Build the Colab notebook deliverable from the verified workspace package.

Run:  python3 build_colab_notebook.py
Out:  Railway_Track_Headway_Simulator_Phase1.ipynb  (workspace root)

The notebook inlines every package file verbatim via ``%%writefile`` cells, so
the notebook and the tested package cannot drift apart.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

import nbformat as nbf

WORKSPACE = Path(__file__).resolve().parent
PACKAGE_DIR = WORKSPACE / "railway_headway_sim"
NOTEBOOK_PATH = WORKSPACE / "Railway_Track_Headway_Simulator_Phase1.ipynb"
PACKAGE_NAME = "railway_headway_sim"
#: Declared-paths companion file of the reference railway (Phase-4A correction).
REFERENCE_PATHS_PATH = WORKSPACE / "examples" / "GRR-01-paths.json"
#: Rolling-stock companion file of the reference railway (Phase 6A).
REFERENCE_STOCK_PATH = WORKSPACE / "examples" / "GRR-01-rolling-stock.json"

#: Order of the notebook sections: (markdown title, [relative file paths]).
SECTIONS: list[tuple[str, list[str]]] = [
    (
        "### Package: root modules\n"
        "`__init__.py` (public API), `version.py` (single source of versions), "
        "`constants.py` (schema layout, container spec, units), "
        "`example_project.py` (documented example JSON).",
        ["__init__.py", "version.py", "constants.py", "example_project.py"],
    ),
    (
        "### Package: `models` — canonical project model and diagnostics\n"
        "Layering: `UI → controller → model → validation/serialization`. "
        "The model and validation layers never import UI widgets. Phase 6A adds the typed "
        "rolling-stock catalogue (`models/rolling_stock.py`) with its reader — a document kind "
        "of its own, no physics import and no numeric library.",
        [
            "models/__init__.py",
            "models/base.py",
            "models/common.py",
            "models/diagnostics.py",
            "models/enums.py",
            "models/infrastructure.py",
            "models/project.py",
            "models/rolling_stock.py",
        ],
    ),
    (
        "### Package: `validation` — structured diagnostics\n"
        "Three stages: raw JSON structure/schema version/field types, then "
        "Phase-1 structural + basic semantic checks, then Phase-2 physical "
        "infrastructure checks (only for projects that declare physical infrastructure). "
        "Phase 6A adds the rolling-stock validity rules (`validation/rolling_stock_validation.py`), "
        "reported through the existing result model.",
        [
            "validation/__init__.py",
            "validation/codes.py",
            "validation/schema_validation.py",
            "validation/project_validation.py",
            "validation/infrastructure_support.py",
            "validation/topology_validation.py",
            "validation/station_validation.py",
            "validation/infrastructure_validation.py",
            "validation/rolling_stock_validation.py",
        ],
    ),
    (
        "### Package: `infrastructure` — Phase 2 typed physical infrastructure\n"
        "Engineering registry, position/chainage mapping, static train footprint, "
        "topology, the typed-layer compiler, the compiled network with its route "
        "coordinates, and the frozen GRR-01 Part A fixture "
        "with its Section-BA contradiction scan. Contains **no** train dynamics.",
        [
            "infrastructure/__init__.py",
            "infrastructure/registry.py",
            "infrastructure/mapping.py",
            "infrastructure/static_geometry.py",
            "infrastructure/topology.py",
            "infrastructure/compiler.py",
            "infrastructure/grr_fixtures.py",
            "infrastructure/grr_audit.py",
            "infrastructure/preview_series.py",
            "infrastructure/compiled_network.py",
            "infrastructure/geometry_along_route.py",
        ],
    ),
    (
        "### Package: `physics` — resistance utilities, their along-route evaluation\n"
        "and the Stage-6B effort series (Phase 5A, extended by Phase 5B and Phase 6B)\n"
        "Stage 5A: four pure functions over plain numbers — the Davis running resistance, the\n"
        "signed gradient force, the Roeckl curve resistance and their literal sum, plus the two\n"
        "applicability helpers. Stage 5B: the same four quantities evaluated read-only along a\n"
        "compiled route, at a caller-given route distance and speed, with the curvature term\n"
        "length-weighted over the train footprint. Stage 6B adds the frozen simplified effort\n"
        "primitive (`physics/tractive_effort.py`: force-limited up to the transition speed,\n"
        "power-limited above it) and the two plottable series swept from a stored stock type\n"
        "(`physics/rolling_stock_series.py`). No project, no motion and no time; the standard\n"
        "library only.",
        [
            "physics/__init__.py",
            "physics/resistance.py",
            "physics/along_route.py",
            "physics/tractive_effort.py",
            "physics/rolling_stock_series.py",
        ],
    ),
    (
        "### Package: `io` — JSON import/export and canonical hashing",
        ["io/__init__.py", "io/project_io.py"],
    ),
    (
        "### Package: `app` — project controller (application state)",
        ["app/__init__.py", "app/project_controller.py"],
    ),
    (
        "### Package: `ui` — Colab application shell (requires `ipywidgets`)\n"
        "Phase-2 project/validation pages, the Phase-6B read-only Rolling Stock page\n"
        "(`ui/rolling_stock_page.py`), the six `PLANNED FOR LATER DEVELOPMENT PHASE`\n"
        "placeholders, the shared header/shell, and the Phase-3 editing layer: field help\n"
        "(the single tooltip file), editor specs (catalogue field definitions), the draft\n"
        "bridge (`ui/editing.py`), the table editor, the SVG charts, the preview panels, the\n"
        "schematic renderer/page and the per-sub-tab editor hosts.",
        [
            "ui/__init__.py",
            "ui/formatting.py",
            "ui/field_help.py",
            "ui/editor_specs.py",
            "ui/svg_render.py",
            "ui/project_page.py",
            "ui/editing.py",
            "ui/table_editor.py",
            "ui/preview_panel.py",
            "ui/infrastructure_page.py",
            "ui/stations_page.py",
            "ui/validation_page.py",
            "ui/placeholder_pages.py",
            "ui/page_editors.py",
            "ui/schematic_render.py",
            "ui/schematic_page.py",
            "ui/rolling_stock_page.py",
            "ui/app_shell.py",
        ],
    ),
    (
        "### Package: `tests` — automated tests\n"
        "Covers TEST P1-001 … TEST P1-012, TEST P2-001 … TEST P2-028, "
        "TEST P2-REG-G001 … G005, TEST P3-001 … TEST P3-026, "
        "TEST P4-001 … TEST P4-048, TEST P5-001 … TEST P5-024, TEST P5-025 … TEST P5-042, "
        "TEST P6-001 … TEST P6-024 and TEST P6-025 … TEST P6-048 "
        "plus structural "
        "regression tests.",
        [
            "tests/__init__.py",
            "tests/conftest.py",
            "tests/support.py",
            "tests/phase2_support.py",
            "tests/run_tests.py",
            "tests/test_validation.py",
            "tests/test_project_io.py",
            "tests/test_controller.py",
            "tests/test_ui_shell.py",
            "tests/test_phase2_models.py",
            "tests/test_phase2_topology.py",
            "tests/test_phase2_stations.py",
            "tests/test_phase2_static_geometry.py",
            "tests/test_phase2_facade_and_app.py",
            "tests/test_phase2_grr_regressions.py",
            "tests/test_phase3_editors.py",
            "tests/test_phase4a_route_coordinate.py",
            "tests/test_phase4b_geometry_along_route.py",
            "tests/test_phase5a_resistance.py",
            "tests/test_phase5b_along_route.py",
            "tests/test_phase6a_rolling_stock_model.py",
            "tests/test_phase6b_rolling_stock_ui.py",
        ],
    ),
]

HEADER_MD = """# Railway Track Headway Simulator — Phase 6B
### Rolling-Stock UI (the read-only Rolling Stock page, and the two small physics utilities it plots — data only, no motion)

**Application version 0.9.0 · Project schema version 1.0 · Target environment: Google Colab**

*(The file name is the historical Phase-1 name; this notebook is the Phase-6B build.)*

---

## What this notebook builds

A modular Python application foundation for a future microscopic railway
train-performance / blocking-time / headway / capacity simulator, with an
OpenTrack-like engineering analysis philosophy — Phase 3 adds the **infrastructure
editor UI** on top of the accepted Phase-1/Phase-2 code, so the typed catalogues can
be maintained without hand-editing project JSON, Phase 4A adds the **compiled
network and the route-coordinate system**, Phase 4B adds the **geometry along that
route** (elevation, gradient and curve radius as functions of route distance), Phase 5A
adds the **pure resistance and force utilities** (Davis running resistance, signed gradient
force, Roeckl curve resistance and their sum) and Phase 5B evaluates those utilities **along
the compiled route** (running resistance, signed grade force, length-weighted curve resistance
and their total, as functions of route distance and speed), Phase 6A adds the **typed
rolling-stock catalogue** (what a train *is*: mass, length, performance limits, the traction
description, the resistance coefficients and the reference decelerations, with a reader and a
validation module) and Phase 6B adds the **read-only Rolling Stock page** (Overview ·
Traction · Resistance · Braking over the delivered catalogue, together with the two small
physics utilities the curves need — the frozen simplified effort primitive and the two
sampled series) on top of that:

| Layer | Content |
|---|---|
| `railway_headway_sim.models` | canonical project container (schema 1.0), typed infrastructure objects, structured diagnostics, **typed rolling-stock catalogue + reader (Phase 6A)**: `RollingStockCatalogue` / `RollingStock` with their typed blocks, four enumerations, seven read-only SI properties and `RollingStockError` — data only, no physics import, no numeric library |
| `railway_headway_sim.infrastructure` | engineering registry, position↔chainage mapping, static footprint, topology, layer compiler, **compiled network + route coordinates (Phase 4A)**, **geometry along route (Phase 4B)**, GRR-01 Part A fixture + audit |
| `railway_headway_sim.physics` | **resistance and force (Phase 5A, extended by Phase 5B and Phase 6B)**: `davis_resistance_n`, `gradient_force_n`, `roeckl_curve_resistance_n`, `total_resistance_n` and the two Roeckl applicability helpers over plain numbers, plus the along-route evaluation `davis_resistance_at_n`, `gradient_force_at_n`, `curve_resistance_at_n`, `total_resistance_at_n`, plus the Stage-6B effort primitive `tractive_effort_n` (force-limited up to the transition speed, power-limited above it) and the two swept series `tractive_effort_series_n` / `running_resistance_series_n` — newtons out, read-only, no project, no motion, no time |
| `railway_headway_sim.validation` | three stages: raw JSON structure, Phase-1 semantics, Phase-2 physical-infrastructure checks, plus **rolling-stock physical-validity rules (Phase 6A)**: `validate_rolling_stock_catalogue` / `validate_rolling_stock`, every finding an `ERROR` naming its field (`VAL-RS-001…006`) through the existing result model |
| `railway_headway_sim.io` | safe JSON import, deterministic export, canonical SHA-256 hashing |
| `railway_headway_sim.app` | `ProjectController`: project state, direction selection, validation, modification tracking, draft mechanism |
| `railway_headway_sim.ui` | Colab shell: Project, **Infrastructure** (Line · Tracks · Geometry · Speed · Schematic), **Stations & Platforms** (Stations · Platforms · Stopping Marks · Observation Points), **Rolling Stock (Phase 6B — read-only: Overview · Traction · Resistance · Braking, no editing)** and Validation & Audit — with validated editors, draft status, unit-suffixed columns, tooltips, JSON import/export and a click-through schematic |
| `railway_headway_sim.tests` | TEST P1-001 … P1-012, TEST P2-001 … P2-028, TEST P2-REG-G001 … G005, TEST P3-001 … P3-026, TEST P4-001 … P4-048, TEST P5-001 … P5-024, TEST P5-025 … P5-042, TEST P6-001 … P6-024, TEST P6-025 … P6-048 |

> **Scope.** No train simulation and **no train dynamics** exist here: no acceleration,
> braking, speed profiles, traction, signalling, blocking times, movement authority,
> route locking, technical headway, capacity, timetable, Monte-Carlo or UIC 406 — not
> even placeholder result numbers. The computed engineering values are: **static
> geometry** values (front/rear positions, fit checks, chainage mapping) and the Phase-3
> UI previews read from them (gradient between adjacent elevation points, the stored
> curve radius, the most-restrictive stored speed per direction); the Phase-4A compiled
> **coordinates** (the physical edges of a validated project, one route distance `s` [m]
> per (train path, direction), the chainage mapped from each edge's own `chainage_map`);
> the Phase-4B **geometry along route** (elevation [m], gradient [permille] in the
> direction of travel, stored curve radius [m] or `None`, and the footprint-averaged
> gradient — interpolation and a length-weighted mean, nothing more); and the Phase-5A
> **resistance and force utilities** (`railway_headway_sim.physics.resistance`: the Davis
> running resistance, the signed gradient force, the Roeckl curve resistance and their
> literal sum — four pure functions of plain numbers returning newtons, with no route, no
> rolling-stock object, no speed profile, no integration and no time); and the Phase-5B
> **along-route resistance** (`railway_headway_sim.physics.along_route`: the same three
> quantities and their total as functions of route distance `s` [m] and speed [km/h] for a
> caller-given mass [kg] and train length [m], with the curvature term length-weighted over
> the footprint — a read-only evaluation, no integration and no time). The Phase-6A
> **rolling-stock catalogue** is the last item on the list and is **data and validation
> only**: a typed description of what a train *is* (mass, length, performance limits, the
> traction description, the resistance coefficients and the reference decelerations), read
> and checked, never moved. The Phase-3 UI
> computes no engineering value of its own: every editor is a validated draft around the
> Phase-2 data model, and its results come from the Phase-2 compiler and validator.
> Stage 6A stops at stored data: no module computes a trajectory, a speed, an acceleration or
> a time, and the two Phase-6A modules import no physics module and no numeric library.
> Stage 6B adds the values a **read-only** Rolling Stock page displays: the frozen simplified
> effort primitive `tractive_effort_n` (a force at a caller-given speed, recomputed from the
> stored `max_tractive_effort_kn` and `rated_power_kw`) and the two sampled series built from a
> stored stock type (`tractive_effort_series_n` and `running_resistance_series_n`, the latter
> over the Stage-5A Davis primitive). Nothing is edited on the page: no draft mechanism, no
> editable widget, no engineering computation inside a callback — the sub-tabs render stored
> fields and delivered series only. No trajectory, no speed profile, no acceleration, no
> integration and no time step exists, and the page still holds no motion quantity.
> The six pages outside the implemented scope state clearly that they are planned for a
> later development phase.

---

## How to run

1. **Run all cells** (`Runtime → Run all`), top to bottom, in a fresh runtime.
   Cells 1–2 install dependencies and create the package; the `%%writefile`
   cells write the package modules; the last cells verify, test and launch.
2. If you prefer step by step: run cells **1 → 2**, then all `%%writefile` cells,
   then **3 (verify)**, **4 (tests)**, and **7 (launch)**.
3. Then use the application in the last cell — no manual file editing is required.

**Dependencies:** `pydantic>=2`, `ipywidgets>=8` (both pre-installed in Colab)
and `pytest` for the test suite.
"""

SETUP_CELL = '''#@title 1 · Setup — install dependencies { display-mode: "form" }
# Application version: see railway_headway_sim/version.py (single source of truth).
import os
import subprocess
import sys

IN_COLAB = "google.colab" in sys.modules or os.path.isdir("/content")

# Phase-1 dependencies: typed modelling (pydantic), the notebook UI (ipywidgets)
# and the test runner (pytest). Colab normally provides pydantic/ipywidgets already.
print(f"Python {sys.version.split()[0]}  |  Google Colab detected: {IN_COLAB}")
subprocess.run(
    [sys.executable, "-m", "pip", "install", "-q", "pydantic>=2.5", "ipywidgets>=8.0", "pytest>=7.0"],
    check=True,
)
print("Dependencies ready: pydantic, ipywidgets, pytest")
'''

PREPARE_CELL = '''#@title 2 · Prepare the package folder { display-mode: "form" }
import os
import shutil

# Work in the Colab content directory (or the current directory outside Colab).
PROJECT_ROOT = "/content" if os.path.isdir("/content") else os.getcwd()
os.makedirs(PROJECT_ROOT, exist_ok=True)
os.chdir(PROJECT_ROOT)  # %%writefile cells below use paths relative to this folder

RESET_PACKAGE = True  # set False to keep an existing copy of the package
if RESET_PACKAGE and os.path.isdir("railway_headway_sim"):
    shutil.rmtree("railway_headway_sim")

for sub in ("", "models", "validation", "infrastructure", "physics", "io", "app", "ui", "tests"):
    os.makedirs(os.path.join("railway_headway_sim", sub), exist_ok=True)
# Phase-2 reference-project / schema folders (written by the optional cells).
for folder in ("examples", "docs", "schema"):
    os.makedirs(folder, exist_ok=True)

print("Project root:", PROJECT_ROOT)
print("Package folder:", os.path.join(PROJECT_ROOT, "railway_headway_sim"))
'''

VERIFY_CELL = '''#@title 3 · Verify the installation { display-mode: "form" }
import os

import railway_headway_sim as rhs
from railway_headway_sim import ProjectController

print(f"{rhs.APP_NAME} - application version {rhs.APP_VERSION} ({rhs.APP_PHASE})")
print("Supported project schema versions:", ", ".join(rhs.SUPPORTED_PROJECT_SCHEMA_VERSIONS))
print("Canonical top-level sections:")
for section in rhs.TOP_LEVEL_SECTIONS:
    print("   -", section)

files = sorted(
    os.path.join(dirpath, name).replace(PROJECT_ROOT + os.sep, "")
    for dirpath, _dirs, names in os.walk("railway_headway_sim")
    for name in names
    if name.endswith(".py")
)
print(f"\\n{len(files)} modules written:")
for path in files:
    print("   ", path)

controller = ProjectController.new_project(name="Installation check")
print("\\nTemplate project check:", controller.validation.summary_text())
print("Template project ID:", controller.project.project.id)
'''

TESTS_CELL = '''#@title 4 · Run the automated test suite { display-mode: "form" }
import pathlib
import subprocess
import sys

# Runs in a subprocess so the output below is exactly the test runner's output,
# including the PASS/FAIL tables for TEST P1-001 … P1-012, TEST P2-001 … P2-028,
# TEST P2-REG-G001 … G005, TEST P3-001 … P3-026, TEST P4-001 … P4-048, TEST P5-001 … P5-024,
# TEST P5-025 … TEST P5-042, TEST P6-001 … TEST P6-024 and TEST P6-025 … TEST P6-048.
result = subprocess.run(
    [sys.executable, "-m", "railway_headway_sim.tests.run_tests"],
    cwd=PROJECT_ROOT,
)
print("\\nExit code:", result.returncode)
print(
    "RESULT:",
    "PASS - all Phase-1, Phase-2, Phase-3, Phase-4A, Phase-4B, Phase-5A, Phase-5B, "
    "Phase-6A and Phase-6B tests passed"
    if result.returncode == 0
    else "FAIL - see the failures above",
)

# Test totals are NOT asserted here: they are quoted from the generated inventory
# (docs/TEST_INVENTORY.md), which the delivery record verifies with
# `python3 build_test_inventory.py --check`.
inventory_path = pathlib.Path(PROJECT_ROOT) / "docs" / "TEST_INVENTORY.md"
canonical_line = None
if inventory_path.exists():
    canonical_line = next(
        (
            line
            for line in inventory_path.read_text(encoding="utf-8").splitlines()
            if line.startswith("> `") and "collected items" in line
        ),
        None,
    )
if canonical_line is not None:
    canonical_text = canonical_line.removeprefix("> ").replace("`", "")
    print("Canonical test totals (docs/TEST_INVENTORY.md):", canonical_text)
else:
    print(
        "docs/TEST_INVENTORY.md is not present in this runtime, so no test total is "
        "printed here. Generate it with `python3 build_test_inventory.py` (in the "
        "delivery the canonical decomposition is recorded there and verified by "
        "`build_test_inventory.py --check`)."
    )
'''

SELFCHECK_CELL = '''#@title 5 · Self-check: new project → validate → export → import → hash { display-mode: "form" }
import json

from railway_headway_sim import (
    EXAMPLE_PROJECT_JSON,
    ProjectController,
    project_hash,
    to_normalized_dict,
)

check = ProjectController.new_project(name="Self-check line", chainage_end_km=42.5)
check.update_metadata(origin_name="Alpha", end_name="Delta", description="Phase-1 self-check")
check.validate_project()

exported = check.export_json(download=False, directory=PROJECT_ROOT)
reimported = ProjectController()
reimported.import_json_text(exported.text, source_name=exported.filename)

same_data = to_normalized_dict(reimported.project) == to_normalized_dict(check.project)
same_hash = project_hash(reimported.project) == check.current_project_hash
re_export = reimported.export_json(download=False, directory=PROJECT_ROOT)
byte_stable = re_export.text == exported.text

print("File written          :", exported.written_path)
print("Validation status     :", check.validation.summary_text())
print("Canonical hash        :", check.current_project_hash)
print("Import == export data :", same_data)
print("Roundtrip hash equal  :", same_hash)
print("Re-export byte-stable :", byte_stable)

# Direction selection must not touch stored project data or the hash.
hash_before = check.current_project_hash
check.set_direction("REVERSE")
print("\\nDirection changed to  :", check.direction.value)
print("Hash unchanged        :", check.current_project_hash == hash_before)
print("Freshness state       :", check.state.freshness_text)

# Export of the demo project with engineering-style container content:
demo = ProjectController()
demo.import_json_data(json.loads(EXAMPLE_PROJECT_JSON), source_name="example")
print("\\nExample project       :", demo.validation.summary_text())
print("Example object counts :", demo.object_count_rows()[:6], "...")

# --- Phase 2: GRR-01 Part A reference project, typed infrastructure and static geometry ---
from railway_headway_sim.infrastructure import grr_audit
from railway_headway_sim.infrastructure.grr_fixtures import (
    GRR01_STATIC_BENCHMARKS,
    build_grr01_document,
    evaluate_grr01_benchmark,
)
from railway_headway_sim.infrastructure.compiler import compile_infrastructure
from railway_headway_sim.validation import validate_in_memory_project

grr = ProjectController()
grr.import_json_data(build_grr01_document(), source_name="GRR-01")
print("\\nGRR-01 Part A        :", grr.validation.summary_text(), "|", grr.assurance_scope)
print("GRR-01 inventory     :", grr.typed_inventory_rows())
print("GRR-01 registry      :", len(grr.registry_rows()), "object types,", grr.registry_rows()[:3], "...")

print("\\nFrozen static benchmarks (static geometry only - no train dynamics):")
for entry in GRR01_STATIC_BENCHMARKS:
    footprint, benchmark = evaluate_grr01_benchmark(entry["id"])
    print(
        f"  {entry['id']:31s} front {benchmark['front_position_m']:7.1f} m"
        f" final rear {footprint.rear_position_m:8.1f} m"
        f" critical boundary {benchmark['critical_boundary_m']:8.1f} m"
    )
footprint, benchmark = evaluate_grr01_benchmark("GRR-STATIC-P2-FWD-HSR")
print("\\nExample footprint    :", footprint.describe())

compiled = compile_infrastructure(grr.project.infrastructure)
print("Topology             :", dict(compiled.topology().summary_rows()))
findings = grr_audit.scan_contradictions()
print(
    "\\nSection-BA audit     :",
    f"{len(findings)} checks, "
    f"{len(grr_audit.scan_summary()['contradictions'])} contradictions, "
    + ", ".join(f"{item.check_id}={item.severity}" for item in findings),
)

# --- Phase 3: the editors are validated drafts around the same canonical model ---
from railway_headway_sim.ui import InfrastructurePage, StationsPage
from railway_headway_sim.ui.editing import InfrastructureEditor

infra_page = InfrastructurePage(grr)
stations_page = StationsPage(grr)
print("\\nInfrastructure sub-tabs:", " | ".join(infra_page.sub_tab_titles()))
print("Stations sub-tabs      :", " | ".join(stations_page.sub_tab_titles()))
print("Editable catalogues    :", ", ".join(sorted(infra_page.editor_tables())))
print("Stopping-mark fit check:", stations_page.fit_outcome(), stations_page.field_values())

editor = InfrastructureEditor(grr)
canonical_hash = grr.current_project_hash
staged = editor.stage_field("speed_restrictions", "SPR-08", "speed_kmh", 45.0)
print("\\nStaged draft           :", staged.message)
print("Draft pending          :", grr.draft_pending, "| blocks export:", grr.draft_blocks_export)
print("Hash while staged      :", grr.current_project_hash == canonical_hash,
      "(the committed project is never touched by a draft)")
editor.discard_and_report()
print("After discard          :", grr.draft_pending, "| canonical hash kept:",
      grr.current_project_hash == canonical_hash)
'''

EXAMPLE_CELL = '''#@title 6 · (Optional) write the example project JSON to disk { display-mode: "form" }
import json
import os

from railway_headway_sim import EXAMPLE_PROJECT_JSON

example_path = os.path.join(PROJECT_ROOT, "example_project.json")
example_document = json.loads(EXAMPLE_PROJECT_JSON)
with open(example_path, "w", encoding="utf-8") as handle:
    json.dump(example_document, handle, indent=2, ensure_ascii=False)

print("Example project written to:", example_path)
print("Import it in the app with the file picker on the Project page, or download it")
print("to your machine: from google.colab import files; files.download(example_path)")
print("\\nSections:", ", ".join(example_document.keys()))

# --- Phase 2: write the GRR-01 Part A reference project JSON ---
from railway_headway_sim.infrastructure.grr_fixtures import build_grr01_document
from railway_headway_sim.io import import_project_from_data, to_json_text

grr_path = os.path.join(PROJECT_ROOT, "GRR-01.json")
outcome = import_project_from_data(build_grr01_document())
if not outcome.ok:
    raise RuntimeError("GRR-01 Part A did not import: " + outcome.summary_text())
grr_text = to_json_text(outcome.project)
with open(grr_path, "w", encoding="utf-8") as handle:
    handle.write(grr_text)

reimport = import_project_from_data(json.loads(grr_text))
print("\\nGRR-01 Part A written to:", grr_path)
print("GRR-01 byte-stable roundtrip:", to_json_text(reimport.project) == grr_text)
print("GRR-01 validation status    :", reimport.project is not None and "loaded")
'''

PATHS_CELL = (
    '''#@title 6b · (Optional) write the declared-paths companion file { display-mode: "form" }
# Phase-4A correction: examples/GRR-01.json stays frozen and declares no train path
# of its own (train_paths.paths == []).  Its declared paths PATH-H1-F / PATH-H1-R live
# in this companion file and are read with compile_network(project, paths_source=...).
import json
import os

REFERENCE_PATHS_JSON = '''
    + ascii(REFERENCE_PATHS_PATH.read_text(encoding="utf-8"))
    + '''

paths_dir = os.path.join(PROJECT_ROOT, "examples")
os.makedirs(paths_dir, exist_ok=True)
paths_path = os.path.join(paths_dir, "GRR-01-paths.json")
with open(paths_path, "w", encoding="utf-8") as handle:
    handle.write(REFERENCE_PATHS_JSON)

from railway_headway_sim.infrastructure import compile_network
from railway_headway_sim.infrastructure.grr_fixtures import build_grr01_document
from railway_headway_sim.io import import_project_from_data

project = import_project_from_data(build_grr01_document()).project
companion_text = open(paths_path, encoding="utf-8").read()
network = compile_network(project, paths_source=companion_text)

print("Declared-paths companion written to :", paths_path)
print("Frozen project train_paths.paths   :", project.train_paths.paths)
print("Declared paths read from companion :", ", ".join(network.path_ids))
for path_id in network.path_ids:
    rcs = network.route(path_id)
    origin = rcs.at_route_distance(0.0)
    terminus = rcs.at_route_distance(rcs.route_length_m)
    print(f"  {path_id}: route_length_m={rcs.route_length_m:.1f} | "
          f"s=0 on {origin.edge_id} ({origin.chainage_km:.3f} km) | "
          f"s=L on {terminus.edge_id} ({terminus.chainage_km:.3f} km)")
print("Companion diagnostics               :", [d.code for d in network.diagnostics] or "none")
'''
)

STOCK_CELL = (
    '''#@title 6c · (Optional) write the rolling-stock companion file { display-mode: "form" }
# Phase 6A/6B: the typed rolling-stock catalogue, and the series the read-only page plots.
# The frozen examples/GRR-01.json still
# declares no rolling stock of its own (rolling_stock.vehicles == []); the reference
# railway's two stock types live in this companion file and are read with
# load_rolling_stock_catalogue(...).
import hashlib
import json
import os

REFERENCE_STOCK_JSON = '''
    + ascii(REFERENCE_STOCK_PATH.read_text(encoding="utf-8"))
    + '''

stock_dir = os.path.join(PROJECT_ROOT, "examples")
os.makedirs(stock_dir, exist_ok=True)
stock_path = os.path.join(stock_dir, "GRR-01-rolling-stock.json")
with open(stock_path, "w", encoding="utf-8") as handle:
    handle.write(REFERENCE_STOCK_JSON)

from railway_headway_sim.infrastructure.grr_fixtures import build_grr01_document
from railway_headway_sim.io import import_project_from_data, project_hash
from railway_headway_sim.models.rolling_stock import (
    RollingStockError,
    load_rolling_stock_catalogue,
)
from railway_headway_sim.validation import validate_rolling_stock_catalogue

# The reader never writes: hash the frozen project before and after the load.
grr_path = os.path.join(PROJECT_ROOT, "GRR-01.json")
grr_before = hashlib.sha256(open(grr_path, "rb").read()).hexdigest() if os.path.exists(grr_path) else "(not written yet)"

catalogue = load_rolling_stock_catalogue(stock_path)
verdict = validate_rolling_stock_catalogue(catalogue)

grr_after = hashlib.sha256(open(grr_path, "rb").read()).hexdigest() if os.path.exists(grr_path) else "(not written yet)"
project = import_project_from_data(build_grr01_document()).project

print("Rolling-stock companion written to :", stock_path)
print("Document kind / schema           :", catalogue.document_kind, "/", catalogue.schema_version)
print("Validation status                :", verdict.summary_text())
print("Frozen project train_paths.paths :", project.train_paths.paths)
print("Frozen project rolls its own stock:", project.rolling_stock.vehicles)
print("Frozen project canonical hash    :", project_hash(project))
print("Frozen project file unchanged    :", grr_before == grr_after)

print("\\nRolling-stock evidence table (read through the reader, no physics involved):")
headers = (
    "id", "category", "length_m", "static_mass_t", "rotating_mass_factor",
    "effective_mass_kg", "max_speed_kmh", "rated_power_kw", "max_tractive_effort_kn",
    "resistance_a_kn", "resistance_b_kn_per_kmh", "resistance_c_kn_per_kmh2",
    "service_deceleration_mps2", "etcs_reference_deceleration_mps2",
)
print("  " + " | ".join(headers))
for stock in catalogue.rolling_stock:
    row = (
        stock.id,
        stock.category.value,
        f"{stock.length_m:.1f}",
        f"{stock.mass.static_mass_t:.1f}",
        f"{stock.mass.rotating_mass_factor:.2f}",
        f"{stock.effective_mass_kg:.1f}",
        f"{stock.max_speed_kmh:.1f}",
        f"{stock.traction.rated_power_kw:.1f}",
        f"{stock.traction.max_tractive_effort_kn:.1f}",
        f"{stock.resistance_a_kn:.5f}",
        f"{stock.resistance_b_kn_per_kmh:.5f}",
        f"{stock.resistance_c_kn_per_kmh2:.5f}",
        f"{stock.service_braking.reference_deceleration_mps2:.2f}",
        f"{stock.etcs_supervision.reference_deceleration_mps2:.2f}",
    )
    print("  " + " | ".join(row))

# An invalid definition is reported, never repaired: it parses (the number is a
# number) and the validator names the field.
broken_document = json.loads(REFERENCE_STOCK_JSON)
broken_document["rolling_stock"][0]["mass"]["rotating_mass_factor"] = 0.5
broken_catalogue = load_rolling_stock_catalogue(broken_document)
broken_verdict = validate_rolling_stock_catalogue(broken_catalogue)
print("\\nInvalid definition reported      :", broken_verdict.summary_text())
for diagnostic in broken_verdict.diagnostics[:3]:
    print("   ", diagnostic.code, "-", diagnostic.message)

# A string where a number belongs is refused by the reader, never coerced.
not_a_number = json.loads(REFERENCE_STOCK_JSON)
not_a_number["rolling_stock"][0]["mass"]["static_mass_t"] = "485.0"
try:
    load_rolling_stock_catalogue(not_a_number)
except RollingStockError as exc:
    print("String for a number refused      :", str(exc).splitlines()[0][:120])
print("No motion, no trajectory, no integration and no time step:")
print("  the cell reads stored numbers and checks them. Phase 6B also prints what the")
print("  read-only Rolling Stock page displays: the effort at the transition speed and the")
print("  two sampled series, recomputed here from the stored catalogue.")
'''
)

LAUNCH_CELL = '''#@title 7 · Launch the application { display-mode: "form" }
from railway_headway_sim import ProjectController
from railway_headway_sim.infrastructure.grr_fixtures import build_grr01_document
from railway_headway_sim.ui import FUNCTIONAL_PAGES, launch_app
from railway_headway_sim.ui.app_shell import NAVIGATION_TITLES

# Phase 3 launches with the GRR-01 Part A reference project loaded, so the
# Infrastructure (Line · Tracks · Geometry · Speed · Schematic) and Stations &
# Platforms (Stations · Platforms · Stopping Marks · Observation Points) pages show
# typed physical data and its editors.
# Pass your own controller to open another project, e.g.
#   controller = ProjectController(); controller.import_json_file("my_project.json")
#   shell = launch_app(controller, direction="REVERSE")
controller = ProjectController()
controller.import_json_data(build_grr01_document(), source_name="GRR-01 Part A")
shell = launch_app(controller)

print("Application   :", shell.controller.project.project.name)
print("Direction     :", shell.controller.direction.value)
print("Validation    :", shell.controller.validation.summary_with_scope())
print("Assurance     :", shell.controller.assurance_scope)
print("Tabs          :", ", ".join(NAVIGATION_TITLES))
print("Functional    :", ", ".join(FUNCTIONAL_PAGES), "(all other tabs are explicit placeholders)")
print(
    "Sub-tabs      :",
    " | ".join(shell._infrastructure_page.sub_tab_titles()),
    "//",
    " | ".join(shell._stations_page.sub_tab_titles()),
)

# Static HTML fallback (documentation / offline viewing). It cannot call back into
# the kernel, and the interactive / authoritative state stays in the controller.
launch_app(controller, embed=False, snapshot_path="app_snapshot.html")
'''

UPLOAD_CELL = '''#@title 8 · (Optional) import your own project JSON via the browser { display-mode: "form" }
try:
    from google.colab import files  # Colab only
except ImportError:
    print("This cell needs Google Colab's file uploader (skipped outside Colab).")
else:
    uploaded = files.upload()  # choose a .json project file
    if not uploaded:
        print("No file selected - nothing imported.")
    else:
        filename = next(iter(uploaded))
        result = shell.controller.import_json_upload(uploaded, source_name=filename)
        print(f"Import of {filename}: {result.summary_text()}")
        for diagnostic in shell.controller.diagnostics:
            print("  -", diagnostic.format_line())
'''

USAGE_MD = """---
## Using the application

The shell is displayed by cell 7. Its layout:

* **Header** — application name, project name, application version, project schema version,
  validation status and validation freshness (`VALIDATED CURRENT` /
  `PROJECT MODIFIED SINCE VALIDATION`). Status is always written as text as well as colour.
* **Simulation direction** — two prominent buttons:
  `FORWARD · Alpha → Delta` and `REVERSE · Delta → Alpha` (labels use your terminal names).
  This is an **application/run selection only**: stored project data, including the
  infrastructure containers, is never rewritten, and the project hash does not change.
  `BOTH`/`TRACK` exist in the schema for later phases but are not selectable in Phase 1.
* **Navigation** — *Project*, *Infrastructure*, *Stations & Platforms*,
  *Rolling Stock* (read-only, Phase 6B) and *Validation & Audit* are functional.
  Signalling, Services & Timetable, Simulation, Results, Scenarios and Report remain
  explicit `PLANNED FOR LATER DEVELOPMENT PHASE` placeholders with no calculations.
* **Editor mode** — one STANDARD / ADVANCED switch in the shell header drives every
  table: STANDARD hides the optional columns, ADVANCED shows all of them. Optional
  columns are hidden, never dropped from the model.

### Project page

* **New Project** — creates a minimal valid schema-1.0 template.
* **Import JSON** — choose a `.json` file with the picker, then press *Import JSON*.
  Unsupported schema versions and malformed documents are rejected with structured
  diagnostics, and the current project is kept unchanged.
* **Validate Project** — runs the Phase-1 validation.
* **Export JSON** — writes the canonical JSON, starts a Colab browser download and reports
  the on-disk path (filename is derived from project name + project ID).
* **Editable fields** — Project ID, Project Name, Description, Origin Name, End Name,
  Chainage Start, Chainage End. Values are read from the canonical model and written back
  only when you press **Save metadata**.
* **Summary** — project metadata, chainage range, versions, and plain object counts of the
  canonical containers (no derived or simulated quantities).

### Infrastructure page (Phase 3) — Line | Tracks | Geometry | Speed | Schematic

The typed physical infrastructure of the loaded project, now with **validated editors**:

* the shared layer summary, the **typed inventory**, the **global engineering registry**,
  the **topology summary** and the layer diagnostics stay visible above the sub-tabs;
* **Line** — the alignment table plus the reference system (editable reference-system
  fields; fixed fields such as the alignment id are read-only and labelled as such);
* **Tracks** — track groups, nodes and tracks (including the nested `chainage_map`);
* **Geometry** — horizontal geometry sections and vertical profiles with their nested
  elevation points, plus synchronised previews: elevation, gradient between adjacent
  points (‰) and the stored curvature series. The previews respect FORWARD/REVERSE as a
  display orientation only and never mutate stored data;
* **Speed** — the speed-restriction table and the effective-speed preview per direction
  (the most restrictive stored restriction wins);
* **Schematic** — the auto-generated schematic with the eight required layers. Tracks,
  Stations, Platforms and Speed are drawn from the canonical model; Signals,
  TVPs/Resources, Routes and Simulation Occupancy are **visibly disabled** with the reason
  shown — they are never drawn or faked. Clicking surface: choose a drawn object in the
  *Object* list and press *Open in editor* to jump to its row, or use a focus action in the
  validation strip.

Editing rules that apply to every table on every page:

* a cell edit, an added row or a deleted row is staged as a **draft** (`APP-EDIT-002`);
  the committed project and its hash are untouched until you press **Commit**;
* the status bar reports **STAGED**, **COMMITTED** or **REJECTED** in words (never by
  colour alone), with the diagnostic code, the reason and the project hash before/after;
* an invalid draft cannot be committed and blocks export; **Discard** returns to the
  committed project with the canonical hash unchanged;
* every engineering column carries its unit in the header (`km`, `m`, `km/h`, `‰`), and
  every cell has a tooltip from one single tooltip file;
* values read from the document are marked **INPUT**, values produced by the Phase-2
  compiler/validator are marked **DERIVED** — Phase-2 objects have no invented defaults;
* deleting an object that is still referenced is refused, and the refusal names the
  referencing objects;
* JSON import and export stay available and authoritative on the Project page and on the
  Infrastructure page.

### Stations & Platforms page (Phase 3) — Stations | Platforms | Stopping Marks | Observation Points

* **Stations** — the station table (terminal/intermediate, reference chainage, platform ids);
* **Platforms** — the platform table (usable range and length, directionality, platform
  track speed, resource id);
* **Stopping Marks** — the stopping-mark table plus the static train-footprint checker:
  choose a stopping mark, a reference train length (HSR 202.0 m / REG 160.0 m) and a
  direction; the result comes from the Phase-2 package and is reported as
  **FIT**, **TOO_LONG** or **MARKER_OUTSIDE_USABLE** with the front/rear positions,
  chainages, the critical platform boundary and the rear clearance — or the rear
  infringement in metres. The evaluation length is a session value: it is never stored in
  the project;
* **Observation Points** — the observation-point table (service events, cross sections,
  members, node ids) plus the local station schematic of the selected station.

Nothing on these pages computes an engineering value: the editors stage data and show
what the Phase-2 compiler, validator and static-geometry functions return.

### Validation & Audit page

In Phase 3 the same validation surface is also summarised inside the editors: every
editor row carries a severity badge, the schematic marks error objects with the text `!`
plus the code, and a summary counts errors / warnings / info grouped by schema, geometry,
topology and operations. The objects named by the diagnostics are offered as **focus
actions**: choose one and press *Focus* to switch to the owning sub-tab and select the
offending row. Colour is never the only status indicator.

The page itself shows: overall status, error/warning/info counts, the diagnostics table
(*Severity · Code · Category · Object · Message · Suggested action*) with severity,
category and free-text filters, the current and last-validated project hashes, the schema
version, the application version, the direction selection and the sections that received
schema defaults on import.

### Programmatic use (no widgets)

```python
from railway_headway_sim import ProjectController

controller = ProjectController.new_project()
controller.update_metadata(name="My line", chainage_end_km=180.0)
controller.validate_project()
print(controller.state.freshness_text, controller.current_project_hash)
controller.set_direction("REVERSE")          # application state only
controller.export_json()                      # file + Colab download
controller.import_json_file("my_project.json")
for diagnostic in controller.diagnostics:
    print(diagnostic.format_line())
```
"""

REFERENCE_MD = """---
## Reference: schema 1.0 container, diagnostics and hashing

### Canonical project document (schema 1.0)

```
schema_version   "1.0"                      (required, single source: version.py)
project          id, name, project_type, data_status, description,
                 engineering_status, created_utc, modified_utc
display_units    chainage, track_distance, elevation, speed, mass, force, power,
                 time, acceleration, gradient, curve_radius   (UI/report preferences only)
reference_system alignment_id, chainage_start_km, chainage_end_km,
                 chainage_origin_name, chainage_end_name, projection, coordinate_system,
                 datum, forward_direction, reverse_direction, curve_radius_convention
provenance       created_by, tool_name, tool_version, source, notes
infrastructure   [ layer { id, name, physical_mode,
                           # Phase-1 opaque catalogues, preserved verbatim:
                           chainages[], stations[], speed_profiles[],
                           gradients[], curves[], tunnels[], bridges[],
                           # Phase-2 typed catalogues (typed physical infrastructure):
                           alignments[], track_groups[], horizontal_geometry[],
                           vertical_profiles[], speed_restrictions[], nodes[],
                           tracks[], stations[], platforms[], stopping_marks[],
                           observation_points[] } ]                               -> []
signalling       { simulation_time_step_s, rule_set_template, signals[] }
rolling_stock    { trainset_defaults{}, vehicles[] }
train_paths      { stop_patterns[], paths[] }
services         [ group { folder_id, name, service_groups[], timetable[] } ]    -> []
simulation       { time_step_s, random_seed, start_time_s, horizon_s, notes }
analysis         { notes, parameters{} }
scenarios        [ { id, name, ... } ]                                           -> []
reporting        { report_title, author, organisation, notes }
```

* Array containers (`infrastructure`, `services`, `scenarios`) default to `[]`; every absent
  section receives its documented default and is reported as `VAL-FUTURE-001` (INFO).
* Unknown fields anywhere in the document are preserved through import → export
  (forward-compatible within schema 1.x).
* `project.id` is the stable machine identifier; `project.name` is user-editable display
  information and is never used as a reference key.
* **All registered engineering object IDs are globally unique in a physical project**
  (alignments, track groups, horizontal geometry sections, vertical profiles and their
  points, speed restrictions, nodes, tracks, stations, platforms, stopping marks,
  observation points). A collision **between different types** is INVALID
  (`VAL-REGISTRY-001`), not merely a duplicate inside one catalogue.
* Field names carry their unit as a suffix (`chainage_km`, `length_m`, `speed_kmh`); the
  `display_units` section is a UI/report preference only and never changes stored values.
* An opaque (Phase-1) record that carries an `id` inside a *physical* project is an error
  (`VAL-PHASE-002`) plus a warning (`VAL-INFR-020`); it is reported, never silently
  repaired, reinterpreted or dropped.

### Diagnostic codes

| Code | Severity | Meaning |
|---|---|---|
| `VAL-SCHEMA-001` | ERROR | Not parseable JSON text |
| `VAL-SCHEMA-002` | ERROR | Malformed JSON structure (root/field type) |
| `VAL-SCHEMA-003` | ERROR | `schema_version` missing |
| `VAL-SCHEMA-004` | ERROR | Unsupported `schema_version` |
| `VAL-SCHEMA-005` | ERROR | Uploaded data is not UTF-8 text |
| `VAL-PROJECT-001` | ERROR | `project.id` / `project.name` missing or empty |
| `VAL-PROJECT-002` | ERROR | Field has a malformed JSON type |
| `VAL-PROJECT-003` | INFO | Standard metadata not supplied |
| `VAL-PROJECT-004` | INFO | Deprecated project-type value |
| `VAL-REF-001` | ERROR | `chainage_end_km` ≤ `chainage_start_km` |
| `VAL-REF-002` | ERROR | Required reference-system information missing |
| `VAL-DIR-001` | ERROR | Direction value missing or unsupported |
| `VAL-DIR-002` | WARNING | Forward and reverse chainage direction identical |
| `VAL-ID-001` | ERROR | Duplicate identifier of the same object type |
| `VAL-ID-002` | ERROR | Malformed identifier (not a string / empty) |
| `VAL-ENUM-001` | ERROR | Invalid enumeration value |
| `VAL-UNIT-001` | WARNING | Unrecognised display unit |
| `VAL-FUTURE-001` | INFO | Section created with its documented schema default |
| `VAL-FUTURE-002` | INFO | Section preserved but not semantically validated yet |
| `APP-CTRL-001` | ERROR | Application precondition: no project loaded |
| `APP-CTRL-002` | ERROR | Application precondition: no file selected |

Every diagnostic carries `code`, `severity` (INFO/WARNING/ERROR), `category`, `message`
and optionally `object_id`, `context` and `suggested_action`. Status derivation:
any ERROR → `INVALID`; else any WARNING → `VALID_WITH_WARNINGS`; else `VALID`.

### Phase-2 diagnostic codes (physical infrastructure)

The Phase-2 checks run **only** for a project that declares physical infrastructure
(`infrastructure[*].physical_mode == "PHYSICAL"` or typed catalogues present); a legacy
Phase-1 project keeps exactly the Phase-1 behaviour and result. An added `scope` field on
the validation result states what was actually assured (`PHASE-2 PHYSICAL INFRASTRUCTURE`,
`BASIC PROJECT` or `(scope not determined)`).

| Code group | Meaning |
|---|---|
| `VAL-PHASE-001/002` | Physical layer declared but incomplete / an opaque (Phase-1) record inside a physical project carries an `id` |
| `VAL-INFR-001…020` | Typed object field, unit and structural checks; `VAL-INFR-020` is the warning twin of `VAL-PHASE-002` |
| `VAL-REGISTRY-001…005` | Global engineering registry: duplicate ID, malformed ID, unresolvable reference, wrong type, registry/layer mismatch |
| `VAL-ALIGN-001…004` | Alignment range, duplicate/unknown alignment, reference-system alignment resolution |
| `VAL-GEOM-001…006` | Horizontal geometry (`STRAIGHT`/`CURVE`, radius/handedness, alignment containment, overlap, coverage) and vertical profile points |
| `VAL-SPEED-001…005` | Speed restrictions: positive speed, alignment containment, direction and type vocabulary |
| `VAL-TOPO-001…008` | Nodes, tracks, endpoints, chainage maps, connectivity, isolated nodes, track groups |
| `VAL-STATION-001…004`, `VAL-PLATFORM-001…005` | Stations and platforms (usable range inside the track, `usable_length_m` reconciliation, station/platform ownership) |
| `VAL-STOP-001…005` | Stopping marks (platform/track agreement, position inside the track and the usable platform range, direction) |
| `VAL-OBS-001…003` | Observation points (service event, cross section, incomplete definition) |
| `VAL-GRR-001…004` | GRR-01 frozen inventory contract (counts, registry, amendments, regional inventory) |

Topology connectivity is established by **node identity only** — never by chainage
equality; parallel chainage or overlapping chainage ranges are not conflicts. A track's
physical length need not equal its chainage projection; the difference is reported as INFO,
never as an error.

### Hashing and roundtrip guarantees

* `project_hash(project)` = SHA-256 over the canonical document
  (sorted keys, compact separators, `10` ≡ `10.0`, floats rounded to 9 decimals for hashing only).
* Volatile UI/application state (selected direction, messages, scroll position) is not part of
  the project model, so it can never change the hash.
* `Project → export → import → export` is **byte-stable**: import never rewrites
  `created_utc`/`modified_utc`, and export metadata is only written when explicitly requested
  (`embed_export_metadata=True`).
* The exporter writes engineering numbers exactly as stored — no presentation rounding.
"""

SCOPE_MD = """---
## Scope, limitations and next phases

### Implemented in Phase 1

New Project · JSON Import (safe, data-only) · JSON Export (Colab download + file) ·
schema version handling · structured diagnostics with stable codes · staged validation ·
canonical SHA-256 project hash · modification-since-validation tracking ·
prominent FORWARD/REVERSE selector that never mutates project data ·
Project page · Validation & Audit page · version display · automated tests.

### Implemented in Phase 2

Typed physical infrastructure (alignments, track groups, horizontal geometry, vertical
profiles, speed restrictions, nodes, tracks, stations, platforms, stopping marks,
observation points) · **global engineering registry with globally unique object IDs** ·
position ↔ chainage mapping per track · **static train footprint** (front/rear position and
chainage, fit in track, fit in the usable platform range, critical platform boundary, rear
clearance or infringement, both traversal orientations) · topology adjacency, connectivity
and isolated-node checks without a graph library · cross-reference, geometry-coverage,
station, platform and stopping-marker validation · the GRR-01 Part A reference project
(1 alignment 0–50 km, 50 nodes, 59 tracks, 4 stations, 9 platforms, 14 stopping marks,
9 observation points) · registry/count regressions · the **draft mechanism**
(`APP-EDIT-002`: an invalid draft cannot be committed and blocks export) ·
Infrastructure page · Stations & Platforms page · assurance-scope reporting.

### Implemented in Phase 3

Validated editors for every typed Phase-2 catalogue: alignments and the reference system
(Line) · track groups, nodes and tracks including the nested chainage map (Tracks) ·
horizontal geometry and vertical profiles with their nested elevation points (Geometry) ·
speed restrictions (Speed) · stations, platforms, stopping marks and observation points
(Stations & Platforms sub-tabs) · **draft workflow reused from `APP-EDIT-002`**
(STAGED / COMMITTED / REJECTED, hash before/after, invalid drafts cannot be committed and
block export) · add/delete row controls, with deletion refused while an object is still
referenced (the refusal names the referencing objects) · **unit suffixes in every
engineering column** and one tooltip file for every field · STANDARD/ADVANCED editor mode ·
**INPUT / DERIVED provenance markers** (no invented defaults for Phase-2 objects) ·
previews limited to values the package provides (elevation, gradient between adjacent
points, stored curvature, effective speed per direction, static footprint / fit outcome) ·
**infrastructure schematic** generated from the canonical model with a click-through
selection surface and eight layers, four of which are visibly disabled with their reason ·
validation surface inside the editors (row badges, schematic error marks with the code,
counts by schema/geometry/topology/operations, focus actions) · JSON import/export kept
authoritative on the Project and Infrastructure pages · sub-tab state that survives a
refresh and never discards a draft.

The Phase-3 UI introduces **no** new dependency, **no** new validation code (it reuses the
Phase-1/Phase-2 catalogue; genuinely new editing conditions are INFO diagnostics) and
**no** engineering calculation of its own.

### Deliberately **not** implemented (later phases)

Train motion of any kind: traction, braking, speed envelopes and integration, train
trajectories, station stopping physics, train movement simulation, ETCS movement authority,
signals, TVP blocking / route locking / resource occupation, blocking times (including the
seven-component decomposition), technical headway / H(i,j), capacity / UIC 406, timetable
simulation, Monte-Carlo and sensitivity runs, engineering PDF reports, GRR numerical
simulation, simulated arrival/departure times and any time-based residual-occupancy claim.

The Davis running resistance, the gradient force and the Roeckl curve resistance are **not**
on that list any more: Stage 5A delivers them as pure utilities over plain numbers
(`railway_headway_sim.physics.resistance`) and Stage 5B evaluates them along the compiled route
(`railway_headway_sim.physics.along_route`, application version 0.7.0) — the resistance of a
train of a given mass and length at a given route distance and speed, including the
length-weighted curve term and the signed grade term. What is still absent is every *use* of
them that would need a train to move: a speed that evolves, an acceleration, an integration
step, a trajectory, a time. The mass, the train length and the three coefficients are plain
arguments of the caller — Phase 6 introduces the rolling-stock model that will supply them.

No placeholder result values exist anywhere in this code base (no `headway = 0`,
no `capacity = 0`): the corresponding pages are explicitly marked as not implemented.

### Known limitations (documented, not hidden)

* Phase 2 validates physical infrastructure and computes **static geometry only**; no
  quantity that depends on time, speed or train performance is produced.
* The Phase-3 editors show the gradient between adjacent stored elevation points and the
  stored curve radius; both are read from stored values (the gradient is the only
  arithmetic the UI performs, and it is a display of two stored elevations over the stored
  distance between them). Everything else on every page is the package's own result.
* Click-through of the schematic is delivered as an object list plus an *Open in editor*
  action, not as a mouse-click on the SVG: a plain `ipywidgets` `HTML` widget cannot send a
  click back to the kernel without a JavaScript model, which would be a new dependency.
  Every drawn element carries `data-object-id` so a front-end can bind real clicks later.
* Engineering payloads inside the Phase-1 opaque containers are stored and counted but not
  modelled field-by-field; an opaque record with an `id` inside a physical project is
  flagged (`VAL-PHASE-002` error + `VAL-INFR-020` warning).
* `reference_system.chainage_start_km`/`chainage_end_km` describe the **project range**;
  the physical alignment (`ALN-MAIN`, 0.000–50.000 km) is a separate container and the
  reference system points at it by `reference_system.alignment_id`.
* An imported document that is INVALID for a *content* reason is still loaded (valid content
  is preserved and the status is INVALID); a document with a missing/unsupported
  `schema_version` or a non-object root is rejected and the current project is kept.
* Track connectivity is defined by node identity; a physical length differing from the
  chainage projection is legal and reported as INFO.

### Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `ModuleNotFoundError: railway_headway_sim` | Run cells 1–2 and all `%%writefile` cells (or `Runtime → Run all`). |
| Widgets render as static text / no interactivity | Use the Colab/Jupyter front-end, not an exported notebook preview; re-run cell 7. |
| `Import JSON` reports `APP-CTRL-002` | No file was selected in the picker on the Project page. |
| Test cell reports FAIL | Re-run cells 1–2 to recreate the package, then re-run the test cell. |
| Export did not download | Outside Colab there is no browser download; the file path is reported in the status line. |

### Suggested next phases

1. **Phase 4** — signalling and rolling-stock editors with their own typed objects and
   validators, extending the global registry.
2. **Phase 5** — services & timetable editors.
3. **Phase 6+** — simulation engine, blocking-time decomposition, headway and capacity modules
   with their own validated validators and result hashes (the hashing/validation framework
   is already prepared for them: `current_project_hash`/`last_validated_hash` plus
   reserved room for result hashes).
"""


def iter_package_files() -> Iterable[str]:
    """Yield package-relative file paths in notebook section order."""
    for _title, files in SECTIONS:
        for relative in files:
            yield relative


def build_notebook() -> nbf.NotebookNode:
    """Build the notebook node tree from the workspace package files."""
    notebook = nbf.v4.new_notebook()
    notebook.metadata.update(
        {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.11"},
            "colab": {"provenance": [], "toc_visible": True},
        }
    )
    cells: list[nbf.NotebookNode] = [
        nbf.v4.new_markdown_cell(HEADER_MD),
        nbf.v4.new_code_cell(SETUP_CELL),
        nbf.v4.new_code_cell(PREPARE_CELL),
        nbf.v4.new_markdown_cell(
            "## 2 · Write the canonical package\n"
            "The cells below write `railway_headway_sim/` into the runtime using `%%writefile`. "
            "Each file is the exact module used by the test suite.\n\n"
            "```\n"
            "UI  ->  ProjectController  ->  Project model  ->  Validation / Serialization\n"
            "```"
        ),
    ]

    for title, files in SECTIONS:
        cells.append(nbf.v4.new_markdown_cell(title))
        for relative in files:
            source = (PACKAGE_DIR / relative).read_text(encoding="utf-8").rstrip("\n") + "\n"
            cells.append(nbf.v4.new_code_cell(f"%%writefile {PACKAGE_NAME}/{relative}\n{source}"))

    cells.extend(
        [
            nbf.v4.new_markdown_cell("## 3 · Verify, test, self-check and launch"),
            nbf.v4.new_code_cell(VERIFY_CELL),
            nbf.v4.new_code_cell(TESTS_CELL),
            nbf.v4.new_code_cell(SELFCHECK_CELL),
            nbf.v4.new_code_cell(EXAMPLE_CELL),
            nbf.v4.new_code_cell(PATHS_CELL),
            nbf.v4.new_code_cell(STOCK_CELL),
            nbf.v4.new_code_cell(LAUNCH_CELL),
            nbf.v4.new_code_cell(UPLOAD_CELL),
            nbf.v4.new_markdown_cell(USAGE_MD),
            nbf.v4.new_markdown_cell(REFERENCE_MD),
            nbf.v4.new_markdown_cell(SCOPE_MD),
        ]
    )
    notebook.cells = cells
    return notebook


def main() -> int:
    """Write the notebook and report a short summary."""
    missing = [path for path in iter_package_files() if not (PACKAGE_DIR / path).is_file()]
    if missing:
        raise SystemExit(f"Missing package files: {missing}")

    notebook = build_notebook()
    NOTEBOOK_PATH.write_text(json.dumps(notebook, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    writefile_cells = sum(
        1 for cell in notebook.cells if cell.cell_type == "code" and cell.source.startswith("%%writefile")
    )
    size_kb = NOTEBOOK_PATH.stat().st_size / 1024
    print(f"Notebook written: {NOTEBOOK_PATH.name} ({size_kb:.1f} KB)")
    print(f"Cells: {len(notebook.cells)} ({writefile_cells} package file cells)")
    print("Files inlined:", ", ".join(iter_package_files()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
