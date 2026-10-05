# Railway Track Headway Simulator — Phase 4A

**Application version 0.8.0 · Project schema version 1.0 · Google Colab**

> **Filename/alias note.** This file is the delivered `README.md`. The Phase-2R task text
> refers to it as `README (4).md` (a browser-download suffix); no such file exists in the
> tree, and none was created — see finding F13 in
> `docs/PHASE-2R RECONCILIATION REPORT.md`.

Phase-3 deliverable: **the infrastructure UI** — validated, unit-aware, tooltip-annotated
editors for the typed Phase-2 catalogues, so ordinary work no longer requires hand-editing
project JSON, with JSON import/export kept available and authoritative. Phase 3 extends the
accepted Phase-1/Phase-2 source in place — it does not regenerate it.

Phase-4A deliverable: **the compiled network and the route-coordinate system** — one
read-only compilation of the validated project (`CompiledNetwork`) and, per
`(train_path, direction)`, one `RouteCoordinateSystem` carrying a route distance `s` [m] that
always increases in the direction of travel and the physical chainage [km] mapped from each
edge's own `chainage_map`. Stage 4B (gradients and curves along the route) is **not** started;
Phase 4A computes coordinates only.

> Phase 3 still contains **no** train simulation and no train dynamics: no acceleration,
> braking, speed profiles, traction/resistance, gradients forces, signalling, blocking
> time, integration, ETCS movement authority, route locking, technical headway, H(i,j),
> capacity, timetable, Monte-Carlo or UIC 406 analysis. The only engineering values that
> are computed anywhere are **static geometry** values (positions, fit checks, chainage
> mapping), and the Phase-3 UI only *displays* what the package provides (plus the gradient
> between adjacent stored elevation points and the stored curve radius). The editors do not
> compute anything: they stage validated drafts around the Phase-2 model. Pages outside the
> implemented scope are explicitly marked `PLANNED FOR LATER DEVELOPMENT PHASE` and contain
> no placeholder results.

## Contents

| Path | What it is |
|---|---|
| `Railway_Track_Headway_Simulator_Phase1.ipynb` | **Main deliverable.** Colab notebook: installs dependencies, writes the package, runs the full Phase-1 + Phase-2 + Phase-3 test suite, self-checks the roundtrip and the editor draft workflow, launches the app. *The filename retains `Phase1` for continuity with the accepted Phase-1 deliverable path. Its contents are the Phase-3 deliverable. The name is historical, not a scope statement.* |
| `railway_headway_sim/` | The Python package (identical to what the notebook writes), extended in place from Phase 1. |
| `railway_headway_sim/infrastructure/compiled_network.py` | **Phase-4A module.** `CompiledNetwork`, `RouteCoordinateSystem`, `RoutePosition`, `RouteSegment`, `PathEdgeRef`, `compile_network` (with the `paths_source` declared-paths reader) and the diagnostic model for declared train paths. Read-only after compilation; imports no numeric library. |
| `examples/GRR-01-paths.json` | **Declared-paths companion file** (Phase-4A correction). Carries the reference railway's declared paths `PATH-H1-F` / `PATH-H1-R`; the frozen `examples/GRR-01.json` still declares `train_paths.paths == []` itself. |
| `railway_headway_sim/infrastructure/geometry_along_route.py` | **Phase-4B module.** `RouteGeometry`: `elevation_at`, `gradient_at`, `curve_radius_at`, `footprint_gradient` and (added by Phase 5B) `curve_radius_segments_in` — the ordered sub-intervals of a route-distance span on which the stored radius is constant, each as `(length_m, radius_m_or_None)` — over a Phase-4A `RouteCoordinateSystem`, read from the stored vertical profile and horizontal geometry. Read-only; no force, no speed, no time; imports no numeric library. |
| `railway_headway_sim/physics/__init__.py`, `railway_headway_sim/physics/resistance.py` | **Phase-5A package.** Pure numeric utilities: `davis_resistance_n`, `gradient_force_n`, `roeckl_curve_resistance_n`, `total_resistance_n` and the helpers `is_roeckl_radius_usable` / `roeckl_equivalent_gradient_permille`, with `GRAVITY_MPS2` and the five unit constants. Plain numbers in, newtons out; no project, no route, no rolling stock, no motion, no time; standard library only. |
| `railway_headway_sim/physics/along_route.py` | **Phase-5B module.** `davis_resistance_at_n`, `gradient_force_at_n`, `curve_resistance_at_n` and `total_resistance_at_n`: the Phase-5A utilities evaluated read-only along a compiled route at a caller-given route distance `s` [m] and speed [km/h], the curve term length-weighted over the train footprint `[s - train_length_m, s]`. No rolling stock, no motion, no time; standard library only. |
| `railway_headway_sim/models/rolling_stock.py`, `railway_headway_sim/validation/rolling_stock_validation.py` | **Phase-6A modules.** The typed rolling-stock catalogue: `RollingStockCatalogue` / `RollingStock` with their typed blocks and enumerations, `RollingStockError`, `load_rolling_stock_catalogue` (the four accepted source forms), the read-only SI properties, and `validate_rolling_stock_catalogue` / `validate_rolling_stock` — every physical-validity rule reported as an `ERROR` (`VAL-RS-001…006`) through the existing `ValidationResult` / `Diagnostic` model. Data only: no force, no motion, no time; no numeric library and no physics import. |
| `railway_headway_sim/physics/tractive_effort.py`, `railway_headway_sim/physics/rolling_stock_series.py` | **Phase-6B modules.** `tractive_effort_n` (the frozen simplified `FORCE_THEN_POWER_LIMITED` effort: force-limited up to the transition speed, power-limited above it, capped by the starting effort), `transition_speed_kmh` and the two sampled series `tractive_effort_series_n` / `running_resistance_series_n` — `(speed_kmh, force_n)` tuples from 0.0 to the stock's own `max_speed_kmh` inclusive. Plain numbers and stored stock data in, newtons out; no motion, no time step, no numeric library. |
| `railway_headway_sim/ui/rolling_stock_page.py` | **Phase-6B module.** The read-only Rolling Stock page: four sub-tabs (Overview · Traction · Resistance · Braking) over the Phase-6A catalogue plus the two delivered series. No draft mechanism, no editable widget, no engineering computation in a callback. |
| `examples/GRR-01-rolling-stock.json` | **Rolling-stock companion file** (Phase 6A). The reference railway's two stock types `RS-HSR320` (HIGH_SPEED_PASSENGER) and `RS-REG200` (REGIONAL_PASSENGER) with their frozen values; `document_kind` `ROLLING_STOCK_CATALOGUE`. The frozen `examples/GRR-01.json` still declares no rolling stock of its own (`rolling_stock.vehicles == []`). |
| `examples/GRR-01.json` | **GRR-01 Part A reference project** (schema 1.0), single layer `LYR-MAIN`. Canonical counts — quoted from `docs/GRR-01 INVENTORY.md`: `1/2/7/1/13/8/50/59/4/9/14/9 = 177` registered engineering objects across **12 typed catalogues** (1 alignment, 2 track groups, 7 horizontal geometry sections, 1 vertical profile, 13 vertical profile points, 8 speed restrictions, 50 nodes, 59 tracks, 4 stations, 9 platforms, 14 stopping marks, 9 observation points), alignment 0.000–50.000 km. |
| `example_project.json` | Minimal-but-complete *legacy* example project (schema 1.0) — **unchanged** from Phase 1 (byte-identical; see `docs/PHASE1_CHAIN_OF_CUSTODY.md`). |
| `schema/project_schema_v1.0.json` | Generated JSON Schema of the document, including the typed Phase-2 catalogues. |
| `docs/TEST_INVENTORY.md` | **Generated single source of truth for test totals** (`python3 build_test_inventory.py`). Canonical decomposition: `66 + 30 + 5 + 26 + 30 + 18 + 24 + 18 + 24 + 24 = 265` collected items. |
| `docs/PHASE-3 UI SCOPE.md` | Phase-3 UI scope record: the sub-tab layout, the editing workflow (draft states, refusals, provenance, units, tooltips, modes), the schematic layer contract and the explicit list of what the UI does **not** claim to do. |
| `docs/GRR-01 INVENTORY.md` | **Canonical GRR-01 counts** (`1/2/7/1/13/8/50/59/4/9/14/9 = 177`, 12 typed catalogues) and the replacement block for any run log. |
| `docs/GRR-01 CHANGE CONTROL.md` | Amendment record (GRR-AMD-001/002/003/004) and the Section-BA scan output. |
| `docs/GRR-01_FROZEN_PHYSICAL_v1.0.json` | Pre-amendment frozen evidence file. |
| `docs/PHASE1_CHAIN_OF_CUSTODY.md` | Every Phase-1 artefact classified **original** or **reconstructed**, with the source of each reconstruction. |
| `docs/SECTION_D_PATTERNS.md` | The exact pattern list behind the out-of-scope scan and the boundary of that claim. |
| `docs/PHASE1_SOURCE_MANIFEST.json`, `docs/PHASE1_README.md`, `docs/PHASE1_VERIFICATION.md`, `docs/PHASE1_REGRESSION_MAP.md` | Reconstructed Phase-1 records (see the chain-of-custody file). |
| `docs/PHASE-2R RECONCILIATION REPORT.md` | Phase-2R finding-by-finding closure record. |
| `VERIFICATION.md` | Verification report (§1–§12 are the Phase-2 record, §13–§17 the Phase-3 … Phase-5B records, §18 the Phase-6A record and §19 the Phase-6B record): what was run, what was observed, what is *not* claimed. |
| `build_colab_notebook.py` | Regenerates the notebook from the package — code and notebook cannot drift. |
| `build_reference_projects.py` | Regenerates `examples/GRR-01.json`, the frozen evidence file and the Phase-1 manifest (byte-stable). |
| `build_json_schema.py` | Regenerates `schema/project_schema_v1.0.json` (byte-stable). |
| `build_test_inventory.py` | Collects the real pytest inventory and writes `docs/TEST_INVENTORY.md`; `--check` verifies every quoted test total against it. |

## Run in Google Colab

1. Open `Railway_Track_Headway_Simulator_Phase1.ipynb` in Colab.
2. `Runtime → Run all` (cells 1–2 install dependencies and create the package; the
   `%%writefile` cells write the modules; the final cells verify, test and launch).
3. Use the application rendered by the launch cell — no manual file editing is required.

**Environment wording (F7).** *Designed for Google Colab; executed in the record
environment via `nbconvert --execute` (`Google Colab detected: False`). A Colab-hosted
execution record is a declared residual.* See `VERIFICATION.md` §9 item 7.

The notebook is designed for Google Colab: no separate web server, no desktop GUI, no
mandatory manual module execution order, and `launch_app(embed=False)` still writes the
static HTML snapshot. `Railway_Track_Headway_Simulator_Phase1.ipynb` keeps its Phase-1
filename for path continuity — *the name is historical, not a scope statement*.

## Run locally

```bash
pip install "pydantic>=2.5" "ipywidgets>=8.0" pytest
python3 build_test_inventory.py                   # regenerate docs/TEST_INVENTORY.md
python3 -m railway_headway_sim.tests.run_tests    # quotes: 66 + 30 + 5 + 26 + 30 + 18 + 24 + 18 + 24 + 24 = 265 collected items
python3 build_test_inventory.py --check           # verify every quoted test total
python3 -c "from railway_headway_sim.ui import launch_app; launch_app()"   # in Jupyter/Colab
python3 build_json_schema.py                      # regenerate the JSON Schema
python3 build_reference_projects.py               # regenerate GRR-01 + evidence files
```

Test totals are quoted from `docs/TEST_INVENTORY.md` (generated by `build_test_inventory.py`),
not re-asserted here: **66 + 30 + 5 + 26 + 30 + 18 + 24 + 18 + 24 + 24 = 265 collected items** (66 Phase-1
items + 30 Phase-2 items + 5 GRR-01 registry regressions + 26 Phase-3 UI items + 30 Phase-4A
compiled-network / route-coordinate items + 18 Phase-4B geometry-along-route items + 24 Phase-5A
resistance-utility items + 18 Phase-5B along-route resistance items + 24 Phase-6A rolling-stock
model items + 24 Phase-6B rolling-stock UI items, the Phase-4A group being 22
delivered with Phase 4A plus 4 added by the 0.4.1 correction and 4 added by the 0.4.2
correction). The ten acceptance tables print 18 + 28 + 5 + 26 + 30 + 18 + 24 + 18 + 24 + 24 rows.

**Declared constraint (packaging).** *Declared constraint. No packaging manifest exists (no
`pyproject.toml`, `setup.py`, or `requirements.txt`). The package is importable only from the
repository root on `sys.path`. Dependencies are unchanged from Phase 1: `pydantic>=2.5`,
`ipywidgets>=8.0`, `pytest`.* (`nbformat`/`nbconvert`/`ipykernel` are used only to execute the
notebook.) This is a property of the accepted Phase-1 tree, carried forward deliberately and
declared here rather than silently "fixed"; Phase-2R added no manifest. No plotting or graph
library is used — stdlib plus embedded HTML/SVG only.

## Layer contract

```
UI  ->  ProjectController  ->  Project model  ->  Validation / Serialization
                                    ^
                        infrastructure/ (registry, mapping, static geometry, topology, compiler)
```

* `models/` – canonical project container (schema 1.0), typed infrastructure objects
  (unit-suffixed field names: `*_km`, `*_m`, `*_kmh`) and structured diagnostics.
  Never imports widgets. **Phase 6A adds `rolling_stock.py`:** the typed rolling-stock
  catalogue and its reader — still schema 1.0, a document kind of its own, no physics
  import and no numeric library.
* `infrastructure/` – **Phase 2:** `registry.py` (global ID registry), `mapping.py`
  (edge-position ↔ chainage), `static_geometry.py` (static footprint),
  `topology.py` (adjacency/connectivity, no graph library needed for 50 nodes / 59 edges),
  `compiler.py` (typed views of the layers), `grr_fixtures.py` (frozen GRR-01 Part A),
  `grr_audit.py` (Section-BA contradiction scan and GRR inventory diagnostics).
* `validation/` – stage 1 raw JSON/schema/type checks, stage 2 Phase-1 structural
  semantics, stage 3 **Phase-2 physical-infrastructure checks** (run only for projects
  that declare physical infrastructure; legacy projects keep the exact Phase-1 behaviour).
  **Phase 6A adds `rolling_stock_validation.py`:** the physical-validity rules of a
  rolling-stock catalogue (`VAL-RS-001…006`), reported through the same
  `ValidationResult` / `Diagnostic` model — additive, the project document's behaviour is
  untouched.
* `io/` – safe JSON import (`json.loads` only), deterministic export, canonical SHA-256 hash.
* `app/` – `ProjectController`: project, direction selection, validation, hashes,
  import/export, listeners and the **draft mechanism** (`APP-EDIT-002`: an invalid staged
  draft cannot be committed and blocks export).
* `ui/` – Colab shell. Functional pages: **Project**, **Infrastructure** (Line · Tracks ·
  Geometry · Speed · Schematic), **Stations & Platforms** (Stations · Platforms · Stopping
  Marks · Observation Points), **Validation & Audit**. **Phase 3 adds the editing layer:**
  `field_help.py` (the single tooltip file), `editor_specs.py` (catalogue field
  definitions), `editing.py` (the draft bridge and reference/structure guards),
  `table_editor.py`, `svg_render.py`, `preview_panel.py`, `schematic_render.py`,
  `schematic_page.py`, `page_editors.py`. **Phase 6B adds `rolling_stock_page.py`:** the
  **read-only** Rolling Stock page (Overview · Traction · Resistance · Braking) over the
  Phase-6A catalogue — no draft mechanism, no editable widget, no engineering computation in a
  callback; the six remaining navigation entries are explicit placeholders.
* `infrastructure/preview_series.py` – **Phase 3:** the only preview-series module (gradient
  between adjacent elevation points, stored curvature series, effective speed per
  direction). It is a pure read of stored values; no UI callback calculates.
* `tests/` – `TEST P1-001 … P1-012`, `TEST P2-001 … P2-028`,
  `TEST P2-REG-G001 … G005`, `TEST P3-001 … P3-026`, `TEST P4-001 … P4-048`,
  `TEST P5-001 … P5-042`, `TEST P6-001 … P6-024` and `TEST P6-025 … P6-048` with
  explicit PASS/FAIL tables.

### Container rule

`infrastructure` remains an **array of layer objects**. A layer object keeps the Phase-1
opaque catalogues (`chainages`, `speed_profiles`, `gradients`, `curves`, `tunnels`,
`bridges` — preserved verbatim, never interpreted) and may carry the typed Phase-2
catalogues: `alignments`, `track_groups`, `horizontal_geometry`, `vertical_profiles`,
`speed_restrictions`, `nodes`, `tracks`, `stations`, `platforms`, `stopping_marks`,
`observation_points`. An opaque record that carries an `id` inside a *physical* project is
an error (`VAL-PHASE-002`) and a warning (`VAL-INFR-020`) — it is reported, never silently
repaired or dropped.

## Key invariants

* The canonical JSON/project model is the source of truth; widget values are never
  engineering data.
* **All registered engineering object IDs are globally unique across the project**
  (alignments, track groups, horizontal geometry sections, vertical profiles and their
  points, speed restrictions, nodes, tracks, stations, platforms, stopping marks,
  observation points). Cross-type collisions are INVALID (`VAL-REGISTRY-001`).
* Topology connectivity is established by **node identity only** — never by chainage
  equality. Parallel or overlapping chainage is not a conflict; a track's physical length
  need not equal its chainage projection.
* `project.id` is the stable machine key; `project.name` is display-only.
* Changing the FORWARD/REVERSE selector never rewrites stored project data and never
  changes the project hash.
* `Project → export → import → export` is byte-stable (import never rewrites
  `created_utc`/`modified_utc`; export metadata is opt-in).
* Unknown/future JSON fields are preserved through import/export at every level (schema
  1.x additive).
* Uploaded JSON is treated strictly as data — no `eval`, `exec`, `pickle` or dynamic
  import; no class names are taken from untrusted JSON.
* Static footprint rules (formerly Section Y/Z/AM): `WITH_EDGE` → rear = front − length;
  `AGAINST_EDGE` → rear = front + length. No time, speed or occupation is involved.

## GRR-01 amendments and the deliberate numbering gap

*GRR-AMD-002 corrects a table row in the change-control record (open-line node row = 0). It
changes no project data. It is intentionally absent from `provenance.approved_amendments` in
`examples/GRR-01.json` and from the frozen evidence file. The numbering gap is deliberate, not
an omission.*

The delivered file records exactly three amendments — GRR-AMD-001 (`STOP-V-P1-R` 220.0 →
250.0 m), GRR-AMD-003 (Delta line-end attachment) and GRR-AMD-004 (`PLT-VAL-P2` usable range
100.0 – 500.0 m). Object counts are unchanged by all of them; the canonical counts are in
`docs/GRR-01 INVENTORY.md`.

## Why the schema version stays 1.0

Phase 2 adds *typed catalogues nested inside the existing infrastructure layer object*.
Every Phase-1 document therefore still validates and round-trips unchanged, and a Phase-1
build reading a Phase-2 document preserves the new catalogues as unknown-but-preserved
extension fields. No migration is required in either direction, so
`SUPPORTED_PROJECT_SCHEMA_VERSIONS` stays `("1.0",)` and only the **application** version
was bumped (0.1.0 → 0.2.0 in Phase 2, 0.2.0 → 0.3.0 in Phase 3, 0.3.0 → 0.3.1 as the
Phase-3 bugfix release for `ipywidgets` public-API compatibility, 0.3.1 → 0.4.0 for Phase 4A:
the compiled network and the route-coordinate system add a new module and a read-only per-run
compilation, **0.4.0 → 0.4.1** as the Phase-4A correction release that adds the declared-paths
companion file `examples/GRR-01-paths.json`, renames the test-internal paths to
`TEST-CORRIDOR-A-D` / `TEST-CORRIDOR-D-A` and corrects `APP_PHASE` to
`Phase 4A — Compiled Network and Route Coordinates`, **0.4.1 → 0.4.2** as the Phase-4A
corridor correction that rewrites the companion file so that `PATH-H1-F` and `PATH-H1-R` are
the two running orders of one physical corridor, and **0.4.2 → 0.5.0** for Phase 4B: the
geometry along route adds a new module and a read-only per-query derivation from the stored
catalogues, and it changes no stored key, no validation rule and no existing public
interface, **0.5.0 → 0.6.0** for Phase 5A: the resistance and force utilities add a new
`physics` sub-package with four pure functions and two helpers, and **0.6.0 → 0.7.0** for
Phase 5B: the along-route resistance adds one module (`physics/along_route.py`) and one
additive, purely geometric method on `RouteGeometry` (`curve_radius_segments_in`), and it
changes no stored key, no validation rule and no existing public interface, and **0.7.0 → 0.8.0**
for Phase 6A: the rolling-stock model adds one typed catalogue module
(`models/rolling_stock.py`), one validation module (`validation/rolling_stock_validation.py`)
and the reference companion file `examples/GRR-01-rolling-stock.json` — data of a new document
kind — while the project schema, every stored key and every existing public interface stay
exactly as they are). The same rationale is recorded in `railway_headway_sim/version.py`, in `VERIFICATION.md` (§7 and §13) and in the
generated JSON Schema (`$comment` records the schema decision, not the application
version).

## Phase 3 — the infrastructure UI

Phase 3 turns the typed catalogues into something a user can maintain without editing JSON by
hand. The JSON remains the authoritative interchange format: import/export are unchanged and
stay available on the **Project** page and on the **Infrastructure** page.

**Sub-tabs.** *Infrastructure* = **Line** (alignment + reference system) | **Tracks** (track
groups, nodes, tracks incl. the nested `chainage_map`) | **Geometry** (horizontal geometry,
vertical profiles and their nested points, with synchronised elevation / gradient [‰] /
stored-curvature previews) | **Speed** (restrictions + effective-speed preview per direction) |
**Schematic**. *Stations & Platforms* = **Stations** | **Platforms** | **Stopping Marks**
(including the static train-fit / rear-clearance checker returning `FIT`, `TOO_LONG` or
`MARKER_OUTSIDE_USABLE`) | **Observation Points**. Sub-tab state survives a refresh, and
switching tabs never discards a staged draft.

**Editing workflow (reuses the Phase-2 draft mechanism, `APP-EDIT-002`).** A cell edit, an
added row or a deleted row is staged, never applied directly. The status bar reports
`STAGED`, `COMMITTED` or `REJECTED` **in words** (colour is never the only indicator) with the
diagnostic code, the reason and the project hash before/after. An invalid draft cannot be
committed and blocks export; `Discard` returns to the committed project with the canonical
hash unchanged. Deleting an object that is still referenced is refused and the refusal names
the referencing objects. Round-trip stays byte-stable when nothing is committed, and a
loaded-then-exported `GRR-01` keeps its canonical hash.

**Presentation contract.** Every engineering column carries its unit (`km`, `m`, `km/h`, `‰`);
every field has a tooltip from the single file `ui/field_help.py`; each value is marked
**INPUT** (read from the document) or **DERIVED** (produced by the Phase-2 compiler/validator)
— Phase-2 objects have no invented defaults. A single STANDARD/ADVANCED switch (shared by all
editors) hides optional columns only, never model data. Changing FORWARD/REVERSE is a display
selection: it never mutates stored data and never changes the hash.

**Schematic.** Generated from the canonical model, with the eight required layers. *Tracks*,
*Stations*, *Platforms* and *Speed* are active; *Signals*, *TVPs/Resources*, *Routes* and
*Simulation Occupancy* are **visibly disabled with the reason shown** — never drawn and never
faked. Every drawn element carries `data-object-id` and is registered in an *Object* list; the
*Open in editor* action switches to the owning sub-tab and focuses the row, as do the focus
actions of the validation surface (row badges, entries marked `! <code>`, and error / warning /
info counts grouped by schema, geometry, topology and operations).

**No new code, no new dependency, no new calculation.** The UI references only existing
Phase-1/Phase-2 diagnostic codes (genuinely new editing conditions are INFO diagnostics), adds
no dependency beyond `pydantic`, `ipywidgets` and `pytest`, and performs no engineering
calculation: the only arithmetic in the UI layer is the gradient between two adjacent stored
elevation points, and every other preview is the package's own output.

## Phase 4A — compiled network and route coordinates

Phase 4A compiles **coordinates only**. It turns one validated project into
`CompiledNetwork` (the physical edges plus the train paths the project declares, with every
diagnostic raised while reading them) and, per `(train_path, direction)`, into a read-only
`RouteCoordinateSystem`:

* `FORWARD` uses every declared path entry as written; `REVERSE` walks the **same physical
  edges** in the reversed order with the **complementary traversal**. Neither direction writes
  the project, the document, the protected files or any cached dictionary, and neither changes
  the canonical hash.
* Route distance `s` [m] starts at 0 at the operational origin of the path and **always
  increases in the direction of travel**; there is no negative `s` and no direction flag inside
  the constructed system — the direction is a property of the system itself.
* A railway position is authoritative as `(edge_id, local_position_m)`. The physical chainage
  [km] is a *derived reporting coordinate*, mapped through each edge's own `chainage_map`
  (LINEAR). `chainage_to_route_distance(chainage_km)` refuses a chainage that is not on the
  path (`RouteCoordinateError`) instead of inventing a value.
* Track identity, not chainage, is authoritative: where a declared `length_m` exceeds the
  chainage projection of the same edge, route distance and chainage simply disagree by that
  difference and neither is "corrected".
* Every defect a declared path can carry — unresolved `edge_id`, missing `edge_id`, unusable
  `traversal`, an edge-sequence break, an empty edge list, a duplicate path id, an unusable
  direction — is reported through an **existing** diagnostic code (`VAL-REGISTRY-003`,
  `VAL-ID-001`, `VAL-ID-002`, `VAL-ENUM-001`, `VAL-TOPO-007`, `VAL-DIR-001`) and the path is
  refused. Nothing is silently repaired, dropped or reordered.
* Continuity is checked **in train order** (previous entry's exit node is the next entry's
  entry node). A legal reversal move — entering a node on one edge and leaving along another
  edge stored the other way round — therefore compiles, although the stored-orientation
  sequence check would call it a break (evidence: `TEST P4-018`).

**Declared-path data.** The frozen reference project declares `train_paths.paths == []`: it
contains **no** train path of its own. Its declared paths live in the companion file
`examples/GRR-01-paths.json` and are read with `compile_network(project, paths_source=...)`.
The two paths are **one physical corridor run in opposite directions**: `PATH-H1-F` runs the
selected 14-edge walk in its travel order and `PATH-H1-R` is exactly its reverse — the same
edge entries in reverse order with the complementary traversal, the same 47 400.0 m and the
same terminal pair, swapped (Alpha P2 platform edge ⇄ Delta P1 platform edge). The corridor is
selected by a deterministic rule stated verbatim in the file's own `notes` (minimum total
length, then minimum edge count, then the lexicographically smallest edge-id list, among all
walks that begin and end on a station platform edge of the two stations), and every traversal
is derived from the reference project's own track endpoints. Nothing is written into
`examples/GRR-01.json`, into the frozen evidence file or into `example_project.json`; their
hashes are re-verified unchanged in `VERIFICATION.md` §14, and the tests keep their own
test-corridor paths under the unambiguous ids `TEST-CORRIDOR-A-D` / `TEST-CORRIDOR-D-A`.

**Acceptance criterion C (observed).** For the same physical reference project the test
corridor FORWARD runs 0 → 49 000.000 m from `TR-A-W-U1` (chainage 0.000 km) to `TR-D-P1`
(chainage 49.000 km) and its REVERSE runs 0 → 49 000.000 m in the opposite travel direction
from chainage 49.000 km back to 0.000 km, over the same 15 physical edges with the same
`chainage_map` values; both companion-file reference walks run 0 → 47 400.0 m between the two
platform edges (`PATH-H1-F` from `TR-A-E1-E` to `TR-D-P1`, `PATH-H1-R` over the same edges
starting on `TR-D-P1`), because they are the two running orders of one physical corridor. In
every case the loaded project's canonical hash is unchanged.

**Out of scope for Phase 4A (and what Phase 4B then added).** Phase 4A itself added no
gradient, elevation or curvature along the route — that was Stage 4B, delivered as **Phase 4B**
in the next section. No Davis/Roeckl resistance, traction, braking or integration; no
signalling, ETCS/TVP, route locking or movement authority; no headway, blocking time or
capacity; no timetable, dispatching or scenario work; no UI, editor or schematic change; no
reporting, PDF or chart. No new dependency, no rename, no refactor and no change to a protected
artefact.

## Phase 4B — geometry along route

Phase 4B reads the stored geometry of the physical railway along a compiled route. It adds
exactly one module, `railway_headway_sim/infrastructure/geometry_along_route.py`, exporting
`RouteGeometry(project, route_system)` — one class that works with whichever Phase-4A
`RouteCoordinateSystem` it is given (one `FORWARD` or one `REVERSE` instance, never both at
once), and that answers four questions for any route distance `s` in `[0, route_length_m]`:

| Method | Returns | Unit |
|---|---|---|
| `elevation_at(s_m)` | physical elevation, linearly interpolated between the stored elevation points of the vertical profile | `[m]` |
| `gradient_at(s_m)` | effective gradient, signed by the direction of travel; piecewise constant between two stored elevation points | `[permille]` |
| `curve_radius_at(s_m)` | the stored `radius_m` of the `CURVE` section that contains the position, else `None` on a straight (never `0.0`, never a sentinel); handedness is not part of the API | `[m]` or `None` |
| `footprint_gradient(s_m, train_length_m)` | the length-weighted mean of the gradient over the footprint `[s_m - train_length_m, s_m]` (a train whose front is at `s_m`), `ValueError` for a non-positive length | `[permille]` |

The direction rules follow the railway, not the travel direction: elevation and curve radius are
**the same** for `FORWARD` and `REVERSE` at the same physical location, and the gradient is
**opposite-signed** there, because the vertical profile is stored against increasing physical
chainage. Everything is read from the project's own `vertical_profiles` and
`horizontal_geometry` catalogues; nothing is derived from another catalogue and nothing is
invented. A route distance outside `[0, route_length_m]`, or a position the stored data does not
cover, raises the Phase-4A `RouteCoordinateError` — no value is clamped and no placeholder is
returned; a missing or too-short vertical profile is reported as `VAL-GEOM-006` and a missing or
gapped horizontal geometry as `VAL-GEOM-004` (existing codes, `ERROR`, category `GEOMETRY`),
never silently repaired.

**Acceptance criterion (observed).** For the same physical location on the H1 corridor of the
frozen reference project: `elevation_FORWARD == elevation_REVERSE`, `gradient_FORWARD ==
-gradient_REVERSE` and `curve_radius_FORWARD == curve_radius_REVERSE`; the evidence table and
the six runs (suite, pyflakes, inventory check, protected hashes, notebook, direction evidence)
are recorded in `VERIFICATION.md` §15. The loaded project was not modified: its canonical hash
is still `5189aaa2340c1702…` and `examples/GRR-01-paths.json` is still `c62c3ee6…`.

**Still no dynamics.** Phase 4B contains no force, no resistance (no Davis, no Roeckl),
no traction, no braking, no adhesion, no speed, no acceleration, no trajectory, no integration
and no time; no signalling, ETCS/TVP, movement authority or route locking; no headway, blocking
time, occupancy or capacity; no timetable, dispatching, scenario runner, report, PDF or chart.
It performs no engineering calculation beyond the interpolation of the stored elevation, the
stored-data gradient, the stored radius and the length-weighted mean of the footprint gradient,
and it imports no numeric library. Phase 5A is next (delivered — see the next section).

## Phase 5A — resistance and force utilities (pure)

Phase 5A delivers the resistance and force utilities that precede any train motion, as **pure
functions over plain numbers**. It adds exactly one sub-package,
`railway_headway_sim/physics/` (`__init__.py` plus `resistance.py`), which exposes the module
constant `GRAVITY_MPS2 = 9.80665` [m/s²], the unit constants `FORCE_UNIT = "N"`,
`DAVIS_FORCE_UNIT = "kN"`, `DAVIS_SPEED_UNIT = "km/h"`, `GRADIENT_UNIT = "permille"`,
`RADIUS_UNIT = "m"`, and six functions:

| Function | Returns | Unit |
|---|---|---|
| `davis_resistance_n(speed_kmh, davis_a, davis_b, davis_c)` | the Davis running resistance `R(V) = A + B·V + C·V²` with `V` in km/h, the coefficients on the kN basis declared in the docstring | `[N]`, non-negative magnitude |
| `gradient_force_n(mass_kg, gradient_permille)` | the signed gradient force `F = m · g · (i / 1000)` — the frozen normal-railway approximation `sin θ ≈ tan θ ≈ i/1000`, no angle and no trigonometry | `[N]`, positive uphill, negative downhill, exactly `0.0` on level track |
| `roeckl_curve_resistance_n(mass_kg, radius_m)` | the Roeckl curve resistance `W_c = 650 / (R − 55)` permille, i.e. `F_c = m · g · W_c / 1000`; `None` (straight) returns exactly `0.0` | `[N]`, non-negative magnitude |
| `total_resistance_n(mass_kg, speed_kmh, davis_a, davis_b, davis_c, gradient_permille, radius_m)` | the literal sum of the three values above, in that order — the algebra is not re-implemented | `[N]`, signed; negative only when a downhill grade outweighs both magnitudes |
| `is_roeckl_radius_usable(radius_m)` | `True` iff the radius is `> 55.0` m, i.e. the Roeckl denominator is safely positive | `bool` |
| `roeckl_equivalent_gradient_permille(radius_m)` | `W_c = 650 / (R − 55)` | `[permille]` |

**Sign convention, frozen.** Davis and Roeckl are returned as **non-negative magnitudes** (the
caller subtracts them from traction; Stage 5A does not encode that subtraction); the gradient
force is the one **signed** quantity.

**Validation, reported rather than repaired.** Every function validates its inputs before it
computes anything: `speed_kmh` must be a finite `>= 0.0`, `mass_kg` a finite `> 0.0`,
`gradient_permille` finite, the three Davis coefficients finite and `>= 0.0` (a negative
coefficient is a data error, not a case to repair), and `radius_m` either `None` or a finite
`> 55.0`. A NaN or an infinity anywhere raises `ValueError` naming the offending argument. A
radius in `(0.0, 55.0]` is outside the Roeckl model's applicability condition and raises — it is
never clamped, never treated as a straight and never turned into an "infinite radius".

**Purity.** Same inputs, same output, bit for bit. The module holds no mutable global state,
reads no file, project or route, imports nothing but the standard library (`typing` for the
optional radius — no `math`, no `numpy`, no `scipy`, no `statistics`, no `random`), and depends
on no environment variable, no random value and no clock.

**Section-D scan update (declared adaptation).** The five tokens `Davis`, `Roeckl`, `rolling
resistance`, `curve resistance` and `gradient force` were out of scope for Phases 2–4B and were
listed as forbidden. Phase 5A's scope includes them, so they moved to a new allowed list in
`docs/SECTION_D_PATTERNS.md` §2.1 (one rationale per token), allowed **only** inside
`railway_headway_sim/physics/resistance.py`; every other forbidden token stays forbidden, the S1
list went from 11 to 9 tokens, and the scan (P2-028, P4-021, P4-047, P5-023) now asserts the
allowed surface explicitly instead of merely no longer failing.

**Still no dynamics.** Stage 5A is the resistance algebra and nothing else: there is no route, no
project, no compiled network, no rolling-stock model, no train catalogue, no mass, traction,
brake, speed envelope, trajectory, acceleration or integration, no adhesion, rotating-mass
factor, jerk, regenerative braking or energy, no distance and no position, **no time**; no
signalling, ETCS, movement authority, route locking, occupancy, headway, blocking time, capacity,
timetable, dispatching, scenarios, reports or charts; no new dependency, no new diagnostic code
and no UI change (its header follows `APP_PHASE` from the single authority). The observed runs
(suite, pyflakes, inventory check, protected hashes, notebook, micro-benchmarks) are recorded in
`VERIFICATION.md` §16. Stage 5B is next: wiring these functions onto the compiled network and the
Phase-4B geometry so resistance becomes available as a function of route distance.

## Phase 5B — along-route resistance (read-only, still no dynamics)

Phase 5B wires the Phase-5A utilities onto the compiled route, so resistance is available as a
function of route distance `s` [m] and speed [km/h] — and nothing else moves. It adds exactly
one module and one additive method:

| Item | What it is |
|---|---|
| `railway_headway_sim/physics/along_route.py` (new) | `davis_resistance_at_n(speed_kmh, davis_a, davis_b, davis_c)` — position-independent running resistance [N], forwarded to the Phase-5A function; `gradient_force_at_n(geometry, mass_kg, s_m, train_length_m)` — the signed grade force [N] over the footprint `[s_m - train_length_m, s_m]`; `curve_resistance_at_n(geometry, mass_kg, s_m, train_length_m)` — the curvature resistance [N] over the same footprint, length-weighted sub-interval by sub-interval; `total_resistance_at_n(...)` — their literal sum, in that order. |
| `RouteGeometry.curve_radius_segments_in(s_start_m, s_end_m)` (additive) | The ordered sub-intervals of `[s_start_m, s_end_m]` on which the stored radius is constant, each as `(length_m, radius_m_or_None)`; purely geometric (no resistance model applied), lengths summing to the span, `None` on a straight, `ValueError` for a reversed/empty interval and `RouteCoordinateError` for any part outside `[0, route_length_m]` — the convention `footprint_gradient` already uses. No existing `RouteGeometry` method changed. |

**The curvature term, exactly.** The footprint is partitioned by
`curve_radius_segments_in`; a sub-interval carrying a radius `R` contributes
`length · W(R)` with `W(R) = 650 / (R − 55)` [permille] from Phase 5A, a straight sub-interval
contributes `0.0`, and the length-weighted mean `W̄ = Σ(length_i · W_i) / train_length_m` gives
`F_c = m · g · W̄ / 1000` [N]. A footprint inside one curve therefore returns exactly the
Phase-5A single-radius value.

**Sign convention, unchanged and frozen.** The running resistance and the curvature resistance
are **non-negative magnitudes**; the grade force is the one **signed** quantity (positive
uphill in the direction of travel); the total is their literal sum and can be negative only on
a descent steep enough to outweigh both magnitudes (a synthetic `−90 ‰` case is asserted by
`TEST P5-038`). At the same physical train body the grade force is exactly opposite-signed
between FORWARD and REVERSE while the curvature force is equal, because a radius and a
footprint are magnitudes that do not flip.

**Read-only and pure.** Every function takes the geometry object as a read-only argument and
only queries it; nothing writes to the project, the route, the geometry or any file, the loaded
project’s canonical hash is unchanged by any call, and identical inputs return bit-identical
output. Errors are propagated, never repaired: a non-positive train length and an out-of-range
footprint raise the geometry’s own `ValueError` / `RouteCoordinateError`, a stored radius
outside the Phase-5A applicability condition `R > 55` m raises, and no placeholder value is
substituted.

**Section-D and the allowed surface.** The five tokens `Davis`, `Roeckl`, `rolling resistance`,
`curve resistance` and `gradient force` stay on the allowed list of
`docs/SECTION_D_PATTERNS.md` §2.1 and every other forbidden token stays forbidden; because
Phase 5B adds a second module to the same package, the allowed **surface** is now the
`railway_headway_sim/physics/` package rather than the single Phase-5A module (declared
adaptations A1/A2/A5, recorded in `VERIFICATION.md` §17 and
`docs/PHASE1_CHAIN_OF_CUSTODY.md` §7.5). The new module carries no forbidden token
(`TEST P5-042`) and its prose deliberately uses plain language instead of the five names.

**Still contains no dynamics.** Stage 5B is a read-only evaluation of a force at a pair
`(s, speed)`: there is no integration, no time step, no trajectory, no speed envelope, no
acceleration, no motion of any kind; **no rolling-stock object, model or catalogue** (the mass,
the train length and the three coefficients are plain arguments — Phase 6 introduces the model
that supplies them); no traction, brake, adhesion, rotating-mass factor, jerk, regenerative
braking or energy; no signalling, ETCS/TVP, movement authority, route locking, occupancy,
headway, blocking time, capacity, timetable, dispatching, scenario, report or chart; no UI
change of any kind (the header follows `APP_PHASE`); no new dependency; and no change to any
protected artefact. The observed runs (suite, pyflakes, inventory check, protected hashes,
notebook, the along-route evidence table) are recorded in `VERIFICATION.md` §17. **Phase 6 is
next.**

## Phase 6A — rolling-stock model (data and validation, still no dynamics)

Phase 6A declares **what a train *is***: the typed rolling-stock catalogue that later stages
consume. It introduces no motion of any kind and is deliberately limited to the model, the
reader, the reference data and the physical-validity rules.

| Item | What it is |
|---|---|
| `railway_headway_sim/models/rolling_stock.py` (new) | `RollingStockCatalogue` (companion metadata + `rolling_stock` list) and `RollingStock` with its typed blocks — `geometry` (`length_m`), `mass` (`static_mass_t`, `rotating_mass_factor`), `performance_limits` (`max_speed_kmh`, `max_operational_acceleration_mps2`), `traction` (`model`, `rated_power_kw`, `max_tractive_effort_kn`, optional `traction_curve` of `RollingStockTractiveEffortPoint`s), `running_resistance` (`model`, `formula`, `coefficients` A/B/C, `coefficient_speed_unit`, `output_force_unit`), `curve_resistance` (`model_source`), `service_braking` (`model`, `reference_deceleration_mps2`) and `etcs_supervision` (`reference_deceleration_mps2`, `model_role`) — plus the four enumerations (`RollingStockCategory`, `TractiveEffortModel`, `RunningResistanceModel`, `BrakingModel`), the seven read-only SI properties (`mass_kg`, `length_m`, `effective_mass_kg`, `max_speed_kmh`, `resistance_a_kn`, `resistance_b_kn_per_kmh`, `resistance_c_kn_per_kmh2`), `RollingStockError` and the reader `load_rolling_stock_catalogue(source)` for the four accepted forms (mapping, JSON text, file name, `pathlib.Path`). Unknown extension fields survive at every level. |
| `railway_headway_sim/validation/rolling_stock_validation.py` (new) | `validate_rolling_stock_catalogue(catalogue) -> ValidationResult` and `validate_rolling_stock(stock) -> list[Diagnostic]`: one `ERROR` diagnostic per physical-validity defect, each naming its field — non-finite number (`VAL-RS-001`), non-positive quantity (`VAL-RS-002`), rotating-mass allowance below 1.0 (`VAL-RS-003`), negative resistance coefficient (`VAL-RS-004`), unrecognised unit or model value (`VAL-RS-005`), invalid effort characteristic (`VAL-RS-006`). Nothing is clamped, defaulted or dropped. |
| `examples/GRR-01-rolling-stock.json` (new) | The reference railway's two stock types — `RS-HSR320` (202.0 m, 485.0 t, 1.04, 320 km/h, 0.65 m/s², 9800 kW, 300 kN, coefficients 2.506 / 0.04065 / 0.00043, service 0.63 m/s², ETCS 0.50 m/s², `REFERENCE_ASSUMPTION`) and `RS-REG200` (160.0 m, 300.0 t, 1.06, 200 km/h, 0.80 m/s², 5000 kW, 260 kN, coefficients 3.0 / 0.030 / 0.0005, service 0.80 m/s², ETCS 0.55 m/s², `SYNTHETIC_REFERENCE`). Neither declares an effort characteristic: the simplified `FORCE_THEN_POWER_LIMITED` description is the delivered one. |

**The project is not touched.** The catalogue is a companion document of its own
`document_kind`; `examples/GRR-01.json`, the JSON Schema, the frozen evidence file, the legacy
example and the declared-paths companion are byte-identical to Phase 5B, and the canonical
GRR-01 hash is unchanged (`TEST P6-022`). No `rolling_stock` key was added to the project or the
schema: the rolling stock is modelled entirely in Python and stored in its own file.

**Strict, preserving and read-only.** Numbers are JSON-native and strict — a string such as
`"485.0"`, a boolean or `None` for a numeric field is refused, never coerced; unknown extension
fields survive at every level, so the canonical dump round-trips; and loading never mutates the
source mapping. Physical validity is a separate, reported step: an invalid definition is
refused with a named field and an `ERROR`, never repaired.

**Plain-language naming (Section-D, declared).** The Section-D scan surface is unchanged (S1 9
tokens, S3 7, the same five allowed tokens confined to `railway_headway_sim/physics/`). Because
the tokens `Davis` and `traction` may not appear in a *declared name* outside the physics
package, the delivered classes and properties use plain language
(`RollingStockRunningResistanceCoefficients`, `RollingStockTractiveEffort`,
`TractiveEffortModel`, `resistance_a_kn`, …) while the **data** keeps the natural names — the
stored fields `traction`, `traction_curve`, `running_resistance`, `curve_resistance` and the
enumeration values `"DAVIS"`, `"FORCE_THEN_POWER_LIMITED"`. This is recorded as a declared
adaptation in `VERIFICATION.md` §18.6 and `docs/PHASE1_CHAIN_OF_CUSTODY.md` §7.6; no token was
moved, added or removed from any Section-D list.

**Still contains no dynamics.** Stage 6A stores and validates numbers: there is no motion, no
trajectory, no speed envelope, no acceleration, no integration, no time step and no dynamics
state; **no use of the physics package** (the two new modules import no physics and no numeric
library, `TEST P6-023`); no signalling, ETCS/TVP behaviour, movement authority, route locking,
occupancy, headway, blocking time, capacity, timetable, dispatching, scenario, report or chart;
**no UI work** — the Rolling Stock page is still the `PLANNED FOR LATER DEVELOPMENT PHASE`
placeholder and `railway_headway_sim/ui/` was not touched; no new dependency; and no change to
any protected artefact. The observed runs (suite, pyflakes, inventory check, protected hashes,
notebook, the computed rolling-stock evidence table) are recorded in `VERIFICATION.md` §18.
**Stage 6B (the read-only Rolling Stock page) is delivered in the section immediately below.**

## Phase 6B — rolling-stock UI page (read-only, still no dynamics)

Phase 6B displays what Phase 6A modelled. It adds **no motion and no editing**: the page is a
read-only view of the delivered catalogue, and the only new computation is the pair of sampled
series the two curves need.

| Item | What it is |
|---|---|
| `railway_headway_sim/physics/tractive_effort.py` (new) | The frozen simplified effort characteristic. `tractive_effort_n(speed_kmh, max_tractive_effort_kn, rated_power_kw) -> float` [N] applies `FORCE_THEN_POWER_LIMITED`: with `v_t = P * 1000 / (F_max * 1000)` m/s, a speed at or below `v_t` gives exactly `F_max * 1000` N and a speed above it gives exactly `P * 1000 / v` N, so the curve is capped by the starting effort. `transition_speed_kmh(max_tractive_effort_kn, rated_power_kw)` returns `v_t * 3.6` km/h — 117.6 km/h for the frozen pair (300.0 kN, 9800.0 kW). Every unusable argument raises `ValueError` naming that argument: the speed must be finite and `>= 0.0`, the two stock parameters finite and `> 0.0`. Constants `TRACTIVE_EFFORT_UNIT` `"N"`, `SPEED_UNIT` `"km/h"`, `POWER_UNIT` `"kW"`. Pure, standard library only; no acceleration and no motion quantity is computed. |
| `railway_headway_sim/physics/rolling_stock_series.py` (new) | The two plottable series. `tractive_effort_series_n(stock, step_kmh=10.0)` and `running_resistance_series_n(stock, step_kmh=10.0)` return `(speed_kmh, force_n)` tuples sampled from 0.0 to the stock's own `max_speed_kmh` **inclusive** (the last point is exactly that speed, even when the step does not divide it), the resistance series being the Stage-5A Davis primitive over the stock's own A/B/C. A non-positive or non-finite step raises `ValueError` naming `step_kmh`; the result never has fewer than two points and two calls with equal arguments are bit-identical. Pure and read-only. |
| `railway_headway_sim/ui/rolling_stock_page.py` (new) | The **read-only** page. Four sub-tabs: **Overview** (identity, category, data status, geometry, mass and the `effective_mass_kg` property, speed limit, operational acceleration limit), **Traction** (model, rated power, maximum effort, the derived transition speed and the effort curve), **Resistance** (model, formula, the three coefficients with their speed unit and output unit, the curve-resistance model source and the resistance curve) and **Braking** (service and ETCS reference decelerations and the supervision model role). It reads `examples/GRR-01-rolling-stock.json` through `load_rolling_stock_catalogue` and draws through the existing `ui/svg_render.py` / `ui/formatting.py`; there is no draft mechanism, no editable widget and no engineering computation in a callback. |

**Navigation.** `Rolling Stock` moved from the placeholder set to `FUNCTIONAL_PAGES` (now
**five**), and the six remaining pages (Signalling, Services & Timetable, Simulation, Results,
Scenarios, Report) still render the exact `PLANNED FOR LATER DEVELOPMENT PHASE` text and perform
no calculations. The one declared supersession of the stage is the Phase-1 regression
`UI-REG-009`: its hard-coded seven-entry list became a `PLANNED_PAGES`-driven check plus a
two-way disjointness check against `FUNCTIONAL_PAGES` — the placeholder string, the
no-calculation assertion and the "colour is never the only indicator" wording are byte-identical
(`VERIFICATION.md` §19.5, `docs/PHASE1_REGRESSION_MAP.md` §2).

**Still contains no dynamics.** No trajectory, no speed profile, no acceleration, no integration,
no time step and no dynamics state exists; nothing in the page or the two utilities moves a
train, and no module of the stage imports `math` or any other numeric library. No protected
artefact and neither companion file changed, and the canonical GRR-01 hash is unchanged
(`TEST P6-046`). **Stage 7 (signalling) is not started.**

## Out of scope for Phase 3

Davis/Roeckl resistance, gradient forces, traction, braking, speed envelopes and
integration, ETCS movement authority, TVP blocking / route locking / resource occupation,
the 7-component decomposition, technical headway, H(i,j), capacity, timetable simulation,
Monte Carlo, UIC 406, the engineering PDF report and simulated arrival/departure times.

*No forbidden pattern was detected by the Section-D scan (`P2-028`, `BA-12`). The scan covers
the patterns listed in `docs/SECTION_D_PATTERNS.md`; it is a detection guarantee over that
list, not a proof of absence.* That file states each token, the exact matching rule, the
concepts that are not token-matched, and what a pass does and does not guarantee.
No placeholder engineering result value is produced anywhere: the unimplemented pages declare
themselves as planned work instead.

Phase 3 adds nothing to that list. It also does **not** claim: a mouse-click on an SVG (the
click-through is an object list plus *Open in editor*, because a plain `ipywidgets` `HTML`
widget cannot call back into the kernel without a JavaScript model — a new dependency this
phase does not take); a rendered Signals, TVPs/Resources, Routes or Simulation-Occupancy
layer; a resolved platform `resource_id`; a speed-resolution service (the effective-speed
preview is a direction-filtered, most-restrictive-wins read of the stored restrictions); or
any train-dynamics, signalling, headway or capacity result. The Phase-3 scope record with the
full layer contract is `docs/PHASE-3 UI SCOPE.md`.
