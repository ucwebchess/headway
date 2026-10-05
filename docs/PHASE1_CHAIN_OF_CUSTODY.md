# PHASE-1 CHAIN OF CUSTODY

**Purpose.** Phase 2 extended the accepted Phase-1 tree *in place*. This file classifies
every Phase-1 artefact as **original** or **reconstructed**, names the source of each
reconstruction, and records exactly what Phase 2 changed.

> **Statement of record: no Phase-1 source file was modified by Phase-2R.** Phase-2R is
> documentation-only. During Phase 2 itself, 21 Phase-1 files were edited
> deliberately; §3 lists each one with its recorded reason, and the two declared test
> supersessions are itemised in `docs/PHASE1_REGRESSION_MAP.md`.

## 1. What "accepted Phase-1 tree" means here

| Artefact | Class | Source | Content / verification |
|---|---|---|---|
| `docs/PHASE1_SOURCE_MANIFEST.json` | **Reconstructed** | Phase-2 build script `build_reference_projects.py` | 33 files with SHA-256 each; phase 'Phase 1 - Application Foundation', app version 0.1.0, schema 1.0 |
| `docs/PHASE1_README.md` | **Reconstructed** | the accepted Phase-1 `README.md` bytes as they stood when Phase 2 started | the Phase-1 scope record, kept verbatim (65 lines) |
| `docs/PHASE1_VERIFICATION.md` | **Reconstructed** | the Phase-1 acceptance evidence captured while Phase 1 was validated (test log, notebook execution log, example hash) | Phase-1 test totals, notebook execution evidence, freeze statements |
| `docs/PHASE1_REGRESSION_MAP.md` | **Reconstructed** | the Phase-1 collected test-node list captured at Phase-1 acceptance, plus the Phase-2 supersession decisions | preserved / superseded / version-adapted map |
| `/tmp/phase1_snapshot/` (session-local, not delivered) | **Reconstructed, not delivered** | byte copy of the 33 Phase-1 files taken immediately before the first Phase-2 edit | no longer present; the manifest above is the surviving record |

The accepted Phase-1 deliverable **did not contain** `VERIFICATION.md` or a `docs/`
directory (reported as discrepancy 1 in `VERIFICATION.md` §9). The four Phase-1 records
above therefore *reconstruct* what the Phase-1 delivery was, from evidence captured while it
was accepted. They are labelled "reconstructed" here and in their own file headers.

## 2. Phase-1 artefacts unchanged in Phase 2 (12)

Every file below still hashes to the value recorded in `docs/PHASE1_SOURCE_MANIFEST.json`
(the Phase-1 acceptance hash) — its bytes are the accepted Phase-1 bytes:

| Phase-1 artefact | Size | SHA-256 (recorded = current) |
|---|---|---|
| `example_project.json` | 8,866 B | `a36492095e34…` |
| `railway_headway_sim/__init__.py` | 3,986 B | `1dc7a48425b0…` |
| `railway_headway_sim/app/__init__.py` | 308 B | `8e776b6c3a8d…` |
| `railway_headway_sim/example_project.py` | 8,591 B | `266c3fcfd9a0…` |
| `railway_headway_sim/io/__init__.py` | 1,141 B | `020e1ca3d126…` |
| `railway_headway_sim/io/project_io.py` | 18,687 B | `45b061d28040…` |
| `railway_headway_sim/models/__init__.py` | 1,589 B | `03e68cf86619…` |
| `railway_headway_sim/models/project.py` | 17,152 B | `f883cbddfd78…` |
| `railway_headway_sim/tests/__init__.py` | 73 B | `46168ac7b4fd…` |
| `railway_headway_sim/tests/support.py` | 1,780 B | `0125f2e49bbc…` |
| `railway_headway_sim/tests/test_project_io.py` | 12,654 B | `9bf978da8c02…` |
| `railway_headway_sim/validation/schema_validation.py` | 13,542 B | `5b51d49bf363…` |

## 3. Phase-1 artefacts modified in Phase 2 (21) — declared, not silent

Each file below exists from Phase 1 and was edited during Phase 2 for the stated reason.
The `before` hash is the Phase-1 acceptance hash from the manifest; the `after` hash is the
delivered Phase-2 hash. No other file of the accepted tree was touched, and 0 files are
missing.

| Phase-1 artefact | SHA-256 (before -> after) | Reason recorded in Phase 2 |
|---|---|---|
| `README.md` | `2deb6bc7480e…` -> `50b624a3910c…` | Phase-2 README (contents table, Colab section, run-locally, GRR-01 entry) |
| `railway_headway_sim/app/project_controller.py` | `94467667f068…` -> `54b8c222d4fb…` | Phase-2 draft mechanism, typed reporting helpers, assurance scope |
| `railway_headway_sim/constants.py` | `9450367206f1…` -> `b15b8432a048…` | Phase-2 section/catalogue constants |
| `railway_headway_sim/models/common.py` | `17d8328dd95b…` -> `5bd8d460e4ae…` | Phase-2 base-model refactor (`models/base.py` split out) |
| `railway_headway_sim/models/diagnostics.py` | `1a2ae97dec06…` -> `e8283992e23f…` | Phase-2 validation scope added to the existing diagnostics model |
| `railway_headway_sim/models/enums.py` | `f14ff5444fd8…` -> `d71f16f89692…` | Phase-2 enums (object types, traversals, validation scopes) |
| `railway_headway_sim/tests/conftest.py` | `5854aafa8126…` -> `218a7d1b2776…` | Phase-2 PASS/FAIL tables added (P2-xxx, P2-REG-Gxxx) |
| `railway_headway_sim/tests/run_tests.py` | `bf39e3e9e78a…` -> `0275622ed38f…` | Phase-2 wording only (no behaviour change) |
| `railway_headway_sim/tests/test_controller.py` | `f4cd8c1a5203…` -> `9079777abc95…` | declared version-literal adaptation to 0.2.0 (PHASE1_REGRESSION_MAP §3) |
| `railway_headway_sim/tests/test_ui_shell.py` | `b8f046da2378…` -> `5de7e41eb4a6…` | declared UI-REG-009 supersession + version-literal adaptation |
| `railway_headway_sim/tests/test_validation.py` | `eba1c2db6f18…` -> `099f5432ae9f…` | declared VAL-REG-011 supersession |
| `railway_headway_sim/ui/__init__.py` | `ae089122c0cd…` -> `76068ff77fa2…` | FUNCTIONAL_PAGES plus the two new page exports |
| `railway_headway_sim/ui/app_shell.py` | `634414313ba2…` -> `13cd986e0278…` | wiring for the two functional Phase-2 pages |
| `railway_headway_sim/ui/formatting.py` | `5489fdd046b2…` -> `fb3d32e688d2…` | Phase-2 formatting helpers |
| `railway_headway_sim/ui/placeholder_pages.py` | `17efd278210c…` -> `49ef773fbfc5…` | PLANNED_PAGES reduced to the 7 remaining placeholders |
| `railway_headway_sim/ui/project_page.py` | `c95eda64f97d…` -> `732c205c7ed2…` | typed-inventory panel |
| `railway_headway_sim/ui/validation_page.py` | `2dda8413e15d…` -> `5631a4acfe8e…` | assurance-scope row |
| `railway_headway_sim/validation/__init__.py` | `ab4869a8fed2…` -> `40e590f1ea12…` | Phase-2 facade and scope dispatch |
| `railway_headway_sim/validation/codes.py` | `68979c6668d9…` -> `7171d6ed4bc0…` | 43 Phase-2 diagnostic codes (63 total) |
| `railway_headway_sim/validation/project_validation.py` | `9e126742c4ea…` -> `e2315533a630…` | Phase-2 stage added on the existing result model |
| `railway_headway_sim/version.py` | `753b79bb9afa…` -> `28c48f448ec9…` | app version 0.1.0 -> 0.2.0 (schema version stays 1.0) |

Four of these edits are the **declared test changes** (`test_validation.py` -> VAL-REG-011,
`test_ui_shell.py` -> UI-REG-009 supersession plus the version literal, `test_controller.py`
-> version literal, `conftest.py` -> Phase-2 tables); their intent is itemised in
`docs/PHASE1_REGRESSION_MAP.md` §2-§3. In Phase-2R none of them was touched.

## 4. Phase-1 artefacts delivered but not hash-recorded (gap, reported as F17)

`Railway_Track_Headway_Simulator_Phase1.ipynb` and `build_colab_notebook.py` were both part
of the accepted Phase-1 delivery, but the Phase-1 custody snapshot contained **only** the 33
files listed above (`README.md`, `example_project.json` and the package). Their Phase-1 bytes
were therefore never hashed and cannot be verified post hoc. Both were regenerated/edited in
Phase 2 (notebook: Phase-2 content; builder: Phase-2 sections and cells).

Classification: **original Phase-1 artefact, Phase-2-modified, baseline unverifiable.**
Reported as finding F17 in `docs/PHASE-2R RECONCILIATION REPORT.md`. No repair was attempted:
any "repair" would require inventing a Phase-1 baseline that does not exist.

## 5. Phase-2 additions (new files; no Phase-1 counterpart)

Package: `models/base.py`, `models/infrastructure.py`, `infrastructure/` (8 modules),
`validation/infrastructure_support.py`, `validation/topology_validation.py`,
`validation/station_validation.py`, `validation/infrastructure_validation.py`,
`ui/infrastructure_page.py`, `ui/stations_page.py`, `tests/phase2_support.py` and the six
`tests/test_phase2_*.py` modules.

Deliverable and record files: `VERIFICATION.md`, `docs/GRR-01 CHANGE CONTROL.md`,
`docs/GRR-01_FROZEN_PHYSICAL_v1.0.json`, `docs/TEST_INVENTORY.md`, `docs/GRR-01 INVENTORY.md`,
`docs/PHASE1_CHAIN_OF_CUSTODY.md` (this file), `docs/SECTION_D_PATTERNS.md`,
`docs/PHASE-2R RECONCILIATION REPORT.md`, `examples/GRR-01.json`,
`schema/project_schema_v1.0.json`, `build_reference_projects.py`, `build_json_schema.py`,
`build_test_inventory.py`.

`example_project.json` is a Phase-1 artefact and is **unchanged** (byte-identical; see §2).

## 6. Reproduction

```python
import hashlib, json, pathlib
manifest = json.loads(pathlib.Path('docs/PHASE1_SOURCE_MANIFEST.json').read_text())
for entry in manifest['files']:
    current = hashlib.sha256(pathlib.Path(entry['path']).read_bytes()).hexdigest()
    print('UNCHANGED' if current == entry['sha256'] else 'MODIFIED ', entry['path'])
```

## 7. Phase-3 declared adaptations (recorded 2026-10-03)

Phase 3 (the infrastructure UI) touches the accepted tree again. Every change is declared
here with the delivery hash of each file; the `before` column is the Phase-2 delivery hash
from §3.

| File | SHA-256 (Phase-2 -> Phase-3) | Reason recorded in Phase 3 |
|---|---|---|
| `railway_headway_sim/version.py` | `28c48f448ec9…` -> `50b4ba998926…` | application version 0.2.0 -> 0.3.0 (single authority; schema version stays 1.0) |
| `railway_headway_sim/app/project_controller.py` | `54b8c222d4fb…` -> `9011e466ca8d…` | one **added** method `report_ui_message` (no existing signature changed) |
| `railway_headway_sim/ui/app_shell.py` | `13cd986e0278…` -> `b9738a904e0d…` | the shared STANDARD/ADVANCED editor-mode panel and the Phase-3 navigation/quick-guide text |
| `railway_headway_sim/ui/infrastructure_page.py` | (Phase-2 file) -> `e39a59ad0e8d…` | Line/Tracks/Geometry/Speed/Schematic sub-tabs with editors; every Phase-2 attribute kept |
| `railway_headway_sim/ui/stations_page.py` | (Phase-2 file) -> `1ec293e99520…` | Stations/Platforms/Stopping Marks/Observation Points sub-tabs with editors; every Phase-2 attribute kept |
| `railway_headway_sim/tests/conftest.py` | `218a7d1b2776…` -> `33d6c80fcd2c…` | Phase-3 PASS/FAIL table (`P3-xxx`), added alongside the Phase-1/Phase-2 tables |
| `railway_headway_sim/tests/test_controller.py` | `9079777abc95…` -> `718d31eaa811…` | declared version-literal adaptation to 0.3.0 (PHASE1_REGRESSION_MAP §3) |
| `railway_headway_sim/tests/test_ui_shell.py` | `5de7e41eb4a6…` -> `dab3b7ed4570…` | declared version-literal adaptation to 0.3.0 (PHASE1_REGRESSION_MAP §3) |
| `README.md` | `50b624a3910c…` -> `1a3caac58d07…` | Phase-3 README (scope section, contents table, totals) |
| `VERIFICATION.md` | (Phase-2 file) -> `b2c86030a72f…` | Phase-3 acceptance statement (§1, §13) alongside the preserved Phase-2 record |
| `build_test_inventory.py` | (Phase-2 file) -> `0bbf494cb9a1…` | Phase-3 suite entry and four-suite totals |
| `build_colab_notebook.py` | (Phase-2 file) -> `238001204163…` | Phase-3 sections, self-check and scope text |

Unchanged from the Phase-2 delivery (recorded so the absence of a change is checkable):
`railway_headway_sim/ui/__init__.py` (`76068ff77fa2…` — `FUNCTIONAL_PAGES` already names
exactly the four functional pages, and Phase 3 adds no fifth) and
`railway_headway_sim/tests/run_tests.py` (`0275622ed38f…` — it runs the whole `tests`
directory, so the Phase-3 module needed no change).

**Comment-only correction (declared, no expectation touched).** The two version-literal
comments introduced with the Phase-2 adaptation attributed the bump to the GRR-01 data
amendment `GRR-AMD-003`. `GRR-AMD-003` is the Delta line-end attachment in the GRR-01
change-control record (`docs/GRR-01 CHANGE CONTROL.md` §3) and is asserted by
`TEST P2-REG-G005`; a version bump is a *programme* adaptation, not a project-data
amendment, so the two comments now point at `docs/PHASE1_REGRESSION_MAP.md` §3. No
assertion, expectation or value in either test changed — the correction is inside the
comments only, and it is recorded here because the two files are covered by the
version-literal declaration above.

**Protected artefacts, re-verified in Phase 3** (byte-identical; the Phase-3 code never
writes them):

| Artefact | SHA-256 | Status |
|---|---|---|
| `examples/GRR-01.json` | `ad0a26265d4e…` | unchanged |
| `docs/GRR-01_FROZEN_PHYSICAL_v1.0.json` | `9348158d7b28…` | unchanged |
| `schema/project_schema_v1.0.json` | `1a52b73b5587…` | unchanged (its `$comment` records the *schema* decision, not the application version) |
| `example_project.json` | `a36492095e34…` | unchanged |
| canonical hash of the loaded `GRR-01` | `5189aaa2340c1702…` | unchanged |

New Phase-3 files are listed in `docs/PHASE-3 UI SCOPE.md` §9; they have no Phase-1
counterpart to compare against, exactly like the Phase-2 additions in §5.

**Phase-3 bugfix 0.3.1 — declared adaptations (recorded 2026-10-03, after the Phase-3
closure step).** A real defect was observed by the project owner running the notebook in
Google Colab: `railway_headway_sim/ui/table_editor.py` imported `_instances`, a **private**
attribute of `ipywidgets`, so sections "5 · Self-check" and "7 · Launch the application"
stopped with `ImportError: cannot import name '_instances' from 'ipywidgets.widgets.widget'`.
The fix replaces the private registry access with the documented public API: the widget tree
is walked through `children` / `layout` / `style` / `value` and every widget is released
through its own `Widget.close()`. The `before` column is the state immediately before this
bugfix step; where an intermediate step is already recorded, the full chain is given. Every
value is the SHA-256 of the file bytes on disk, re-hashed **after** the notebook was
regenerated and re-executed, so the table records the delivered bytes.

| File | SHA-256 (before -> 0.3.1) | Reason recorded for the bugfix |
|---|---|---|
| `railway_headway_sim/ui/table_editor.py` | `9d91db106167…` -> `d8ed65492282…` | **the fix** — private `_instances` import/use replaced by the public `Widget.close()`; resource management only, no project data involved |
| `railway_headway_sim/version.py` | `50b4ba998926…` -> `ec22da39c233…` | application version 0.3.0 -> 0.3.1 (single authority; `SUPPORTED_PROJECT_SCHEMA_VERSIONS` stays `("1.0",)`) |
| `railway_headway_sim/tests/test_phase3_editors.py` | `2f38eb479d8e…` -> `bdb35b5f24c2…` | added `TEST P3-025`/`TEST P3-026`; `TEST P3-001` version literal re-pointed (function name kept — renaming would change a collected node id) |
| `railway_headway_sim/tests/test_controller.py` | `718d31eaa811…` -> `0e7196ae24d8…` | declared version-literal adaptation 0.3.0 -> 0.3.1 (`docs/PHASE1_REGRESSION_MAP.md` §3) |
| `railway_headway_sim/tests/test_ui_shell.py` | `dab3b7ed4570…` -> `cce43af4098b…` | same declared adaptation (`"APP v0.3.0"` -> `"APP v0.3.1"`; `"SCHEMA v1.0"` unchanged) |
| `railway_headway_sim/tests/conftest.py` | `33d6c80fcd2c…` -> `83d5254b1edc…` | printed Phase-3 table range `P3-024` -> `P3-026` (header + module docstring) |
| `build_test_inventory.py` | `0bbf494cb9a1…` -> `55989083312a…` | Phase-3 suite title range `P3-024` -> `P3-026` |
| `build_colab_notebook.py` | `238001204163…` -> (`6762770ccc81…`, closure-step print-escape fix) -> `e7ba12009b00…` | embedded version and range re-points for the regenerated notebook |
| `README.md` | `1a3caac58d07…` -> `041706d3e155…` | version-history line for 0.3.1, current version, totals and Phase-3 range |
| `VERIFICATION.md` | `b2c86030a72f…` -> (`6087fa89f8fa…`, closure-step §2 rewrite) -> `7e42a6174a35…` | §13.8 added; §1/§2/§7/§8/§13.1 version and totals re-pointed; §2 carries the bugfix run |
| `docs/TEST_INVENTORY.md` | `31d5cd49b161…` -> `559794223bb5…` | regenerated: `66 + 30 + 5 + 26 = 127` collected items |
| `docs/PHASE1_REGRESSION_MAP.md` | `f0e4e1a3c4e4…` -> `e1e49a4f5c18…` | §3 bugfix declaration (the two Phase-1 literals and `TEST P3-001`) |
| `docs/PHASE-3 UI SCOPE.md` | not previously hash-recorded -> `7c17400278e5…` | header version 0.3.1, file-list range and §10 map (`P3-025`/`P3-026` rows added) |
| `docs/GRR-01 CHANGE CONTROL.md` | not previously hash-recorded -> `7eb9b8dc7d6f…` | §6 row recording **no GRR-01 data change** for 0.3.1 |
| `Railway_Track_Headway_Simulator_Phase1.ipynb` | 101,353,331 -> 101,360,594 bytes (regenerated from the builder, then executed in place) | bugfix cell payloads; the execution record was re-created (exit 0, 0 error cells) |

Unchanged by the bugfix (re-verified byte-identical after it): the four protected artefacts —
`examples/GRR-01.json` (`ad0a2626…`), `docs/GRR-01_FROZEN_PHYSICAL_v1.0.json` (`9348158d…`),
`schema/project_schema_v1.0.json` (`1a52b73b…`), `example_project.json` (`a3649209…`) — and the
canonical project hash of the loaded GRR-01 (`5189aaa2340c1702…`). `railway_headway_sim/ui/__init__.py`
(`76068ff77fa2…`) and `railway_headway_sim/tests/run_tests.py` (`0275622ed38f…`) also remain
byte-identical to their Phase-2 delivery, so the close-out in §7 above still holds for them.

Two files are deliberately **not** self-recorded here: this file is not hashed by itself, and
`app_snapshot.html` is a launch-cell runtime artefact that every notebook execution rewrites.
`preview/` contains workspace viewing helpers only (`preview/app_preview.ipynb` re-pointed to
0.3.1, `1f47e20dc712…`); it is not part of the delivered package and carries no delivery hash.

**Phase-4A — declared adaptations (recorded 2026-10-03).** Phase 4A adds the compiled network
and the route-coordinate system (`railway_headway_sim/infrastructure/compiled_network.py`),
`TEST P4-001 … TEST P4-022`, and bumps the application version `0.3.1` → **0.4.0** (single
authority; `SUPPORTED_PROJECT_SCHEMA_VERSIONS` stays `("1.0",)`). The `before` column is the
state delivered by the Phase-3 bugfix (re-hashed from the pre-Phase-4A baseline archive, and
for `infrastructure/__init__.py` additionally verified by reversing the Phase-4A edit); the
`after` column is the SHA-256 of the file bytes on disk after the notebook was regenerated and
re-executed, so the table records the delivered bytes. The four protected artefacts are not in
this table because they are not touched.

| File | SHA-256 (before -> 0.4.0) | Reason recorded for Phase 4A |
|---|---|---|
| `railway_headway_sim/infrastructure/compiled_network.py` | not previously present -> `019885aac9c6…` | **the new module**: `CompiledNetwork`, `RouteCoordinateSystem`, `RoutePosition`, `RouteSegment`, `PathEdgeRef`, `compile_network` and the declared-path diagnostics (`VAL-REGISTRY-003`, `VAL-ID-001`, `VAL-ID-002`, `VAL-ENUM-001`, `VAL-TOPO-007`, `VAL-DIR-001`) |
| `railway_headway_sim/infrastructure/__init__.py` | `36eb13e29bc3…` -> `15a0d78155b3…` | package facade exports the Phase-4A names (additive) |
| `railway_headway_sim/tests/test_phase4a_route_coordinate.py` | not previously present -> `ab68af2e69fa…` | **the new acceptance suite** (`TEST P4-001 … TEST P4-022`, incl. the D6 synthetic fixture) |
| `railway_headway_sim/tests/conftest.py` | `83d5254b1edc…` -> `ae7c84660ec2…` | fifth acceptance table (`PHASE-4A TESTS (TEST P4-001 ... TEST P4-022)`) + `P4-\d{3}` matcher alternative (additive) |
| `railway_headway_sim/version.py` | `ec22da39c233…` -> `25dbe5e941b1…` | application version 0.3.1 -> 0.4.0 (single authority) |
| `railway_headway_sim/tests/test_controller.py` | `0e7196ae24d8…` -> `ee1021f40be4…` | declared version-literal adaptation 0.3.1 -> 0.4.0 (`docs/PHASE1_REGRESSION_MAP.md` §3) |
| `railway_headway_sim/tests/test_ui_shell.py` | `cce43af4098b…` -> `a0575ed0ef30…` | same adaptation (`"APP v0.3.1"` -> `"APP v0.4.0"`; `"SCHEMA v1.0"` unchanged) |
| `railway_headway_sim/tests/test_phase3_editors.py` | `bdb35b5f24c2…` -> `712979000d79…` | `TEST P3-001` literal re-pointed (function name kept — a rename would change a collected node id) |
| `build_test_inventory.py` | `55989083312a…` -> `a38211f33790…` | Phase-4A suite entry + allowed-count set + decomposition line |
| `docs/TEST_INVENTORY.md` | `559794223bb5…` -> `20eb64cd2223…` | regenerated: `66 + 30 + 5 + 26 + 22 = 149` collected items |
| `build_colab_notebook.py` | `e7ba12009b00…` -> `4ce0304d9a6f…` | embedded version string, Phase-4A header/scope text, the two new module cells, success message |
| `README.md` | `041706d3e155…` -> `079176e8a671…` | Phase-4A section, version and totals |
| `VERIFICATION.md` | `7e42a6174a35…` -> `a5f5de1dd814…` | §14 added; four checker-forced historical-total re-points inside §1/§2 (no number changed) |
| `docs/PHASE1_REGRESSION_MAP.md` | `e1e49a4f5c18…` -> `d2ec764b0696…` | §3 Phase-4A declaration (three literals + two checker-driven adaptations) |
| `docs/GRR-01 CHANGE CONTROL.md` | `7eb9b8dc7d6f…` -> `9d2d6d1c426c…` | §6 row recording **no GRR-01 data change** for Phase 4A |
| `Railway_Track_Headway_Simulator_Phase1.ipynb` | 101,360,594 -> 101,466,587 bytes (`46b6b32629a3…` -> `e45e9305f798…`) | regenerated from the builder (89 cells: 75 code, 67 payloads) and executed in place: exit 0, 0 error cells, observed `149 passed` |

Unchanged by Phase 4A (re-verified byte-identical): the four protected artefacts —
`examples/GRR-01.json` (`ad0a2626…`), `docs/GRR-01_FROZEN_PHYSICAL_v1.0.json` (`9348158d…`),
`schema/project_schema_v1.0.json` (`1a52b73b…`), `example_project.json` (`a3649209…`) — and the
canonical project hash of the loaded GRR-01 (`5189aaa2340c1702…`). `railway_headway_sim/ui/__init__.py`
(`76068ff77fa2…`), `railway_headway_sim/tests/run_tests.py` (`0275622ed38f…`) and every other
package module remain byte-identical to their Phase-3 delivery — the Phase-2 close-out in §7
therefore still holds, and the Phase-4A change to `railway_headway_sim/infrastructure/__init__.py`
is an additive export only (a superset of the Phase-3 public surface).

The Phase-4A declared-path data (`H1-F` / `H1-R`) is **not** a file: it is supplied by the tests
in the Phase-4A interchange form because the frozen reference project declares
`train_paths.paths == []`. Nothing was written into any GRR-01 file (`docs/GRR-01 CHANGE
CONTROL.md` §6, Phase-4A row). `preview/` remains workspace viewing helpers only
(`preview/app_preview.ipynb`, `1f47e20dc712…`, unchanged and not part of the delivered package);
`app_snapshot.html` and the `self-check-line_prj-*.json` exports are launch/self-check runtime
artefacts that every notebook execution rewrites.

### 7.1 Phase-4A correction (0.4.1) declared adaptations (recorded 2026-10-03)

(Sub-section of §7 — the declared-adaptation record of the accepted tree; §7 itself is left as written.)

The correction step that precedes Stage 4B touches the accepted tree again, and every change is
declared here in the same form as §3 and §7: the `before` column is the Phase-4A delivery hash
(the state accepted with 0.4.0), the `after` column is the hash of the delivered correction.

| File | SHA-256 (Phase-4A -> correction) | Reason |
|---|---|---|
| `examples/GRR-01-paths.json` | (new file, 5,353 bytes) -> `d9099b79c10a…` | the reference railway's declared paths `PATH-H1-F` / `PATH-H1-R` in the Phase-4A interchange form; generated deterministically from the frozen project's own track endpoints, never hand-edited and never merged into GRR-01 |
| `railway_headway_sim/infrastructure/compiled_network.py` | `019885aac9c6…` -> `a3a26b2fa81f…` | declared-paths reader (`read_declared_paths`, `PATH_CONTAINER_FIELD`, `compile_network(..., paths_source=...)`); additive, stdlib `json`/`pathlib` only, no new diagnostic code |
| `railway_headway_sim/tests/test_phase4a_route_coordinate.py` | `ab68af2e69fa…` -> `1f4baa4879ac…` | test-internal path ids renamed to `TEST-CORRIDOR-A-D` / `TEST-CORRIDOR-D-A` (no collected node id changed) and `TEST P4-023 … TEST P4-026` added |
| `railway_headway_sim/version.py` | `25dbe5e941b1…` -> `d0bf46988526…` | application version 0.4.0 -> 0.4.1 and the corrected `APP_PHASE` label (single authority) |
| `railway_headway_sim/tests/test_controller.py` | `ee1021f40be4…` -> `13c9ea999c53…` | declared version-literal adaptation 0.4.0 -> 0.4.1 (`docs/PHASE1_REGRESSION_MAP.md` §3); function name kept |
| `railway_headway_sim/tests/test_ui_shell.py` | `a0575ed0ef30…` -> `d4bb4bbc4c7a…` | same adaptation (`"APP v0.4.0"` -> `"APP v0.4.1"`; `"SCHEMA v1.0"` unchanged); no test renamed |
| `railway_headway_sim/tests/test_phase3_editors.py` | `712979000d79…` -> `c78c2a251515…` | `TEST P3-001` literal re-pointed (function name kept — a rename would change a collected node id) |
| `railway_headway_sim/tests/conftest.py` | `ae7c84660ec2…` -> `d48d2b3420b9…` | Phase-4A table label `TEST P4-001 … TEST P4-022` -> `… TEST P4-026` (additive range end only) |
| `build_colab_notebook.py` | `4ce0304d9a6f…` -> `708e5df03b05…` | embedded version string, Phase-4A range text and the new declared-paths companion write cell (the notebook must write `examples/GRR-01-paths.json` into the runtime) |
| `build_test_inventory.py` | `a38211f33790…` -> `5744909499e4…` | Phase-4A suite range ends at `TEST P4-026`; the allowed-count table follows the builder |
| `docs/TEST_INVENTORY.md` | `20eb64cd2223…` -> `bf079f16f218…` | regenerated: `66 + 30 + 5 + 26 + 26 = 153` collected items |
| `README.md` | `079176e8a671…` -> `ae315e0c5837…` | declared-paths companion line, version 0.4.0 -> 0.4.1 and totals |
| `VERIFICATION.md` | `a5f5de1dd814…` -> `2db47aa955a6…` | §1 retitled (historical Phase-3/0.3.1 run; current totals in §14) and §14.8 recording the correction; §1 body, §2–§13 and the four §1 historical-total re-points are unchanged |
| `docs/PHASE1_REGRESSION_MAP.md` | `d2ec764b0696…` -> `e013e7a1debc…` | §3 declaration of the 0.4.1 bump, the three re-pointed literals and the two mechanical adaptations |
| `docs/GRR-01 CHANGE CONTROL.md` | `9d2d6d1c426c…` -> `e46dedd90728…` | §6 row recording **no GRR-01 data change** for the correction |
| `Railway_Track_Headway_Simulator_Phase1.ipynb` | 101,466,587 -> 101,499,676 bytes (`e45e9305f798…` -> `2350d7b0ae9c…`) | regenerated from the builder (90 cells: 76 code, 67 payloads) and executed: exit 0, 0 error cells, observed `153 passed`, header shows 0.4.1 |

Supersession: the paragraph above (§7) records that the Phase-4A declared-path data `H1-F` /
`H1-R` "is **not** a file". That was true of the 0.4.0 delivery and is left as the historical
record; from 0.4.1 the reference railway's declared paths live in the companion file
`examples/GRR-01-paths.json` listed above, while the frozen project itself still declares
`train_paths.paths == []`.

Unchanged by the correction (re-verified byte-identical): the four protected artefacts —
`examples/GRR-01.json` (`ad0a2626…`, 57,039 bytes and still `train_paths.paths == []`),
`docs/GRR-01_FROZEN_PHYSICAL_v1.0.json` (`9348158d…`), `schema/project_schema_v1.0.json`
(`1a52b73b…`), `example_project.json` (`a3649209…`) — the canonical hash of the loaded GRR-01
(`5189aaa2340c1702…`), and `railway_headway_sim/infrastructure/__init__.py` (`15a0d78155b3…` —
the reader is reached through the `compiled_network` module, so no export line changed),
`railway_headway_sim/tests/run_tests.py` (`0275622ed38f…`), `railway_headway_sim/ui/table_editor.py`
(`d8ed65492282…`) and `railway_headway_sim/ui/schematic_page.py` (`d949089d49e8…`). No test was
removed, renamed, weakened or skipped; no dependency was added; this document
(`docs/PHASE1_CHAIN_OF_CUSTODY.md`, `507460f987b2…` before this block) is itself the record of
the correction, so its post-write hash is quoted in the delivery note instead of a table row.

### 7.2 Phase-4A correction #2 (0.4.2) declared adaptations (recorded 2026-10-03)

The correction that makes the companion file's two declared paths the two running orders of one
physical corridor touches the accepted tree again; the `before` column is the state delivered
with the 0.4.1 correction (§7.1), the `after` column is the delivered correction.

| File | SHA-256 (§7.1 -> 0.4.2) | Reason |
|---|---|---|
| `examples/GRR-01-paths.json` | `d9099b79c10a…` -> `c62c3ee6d910…` | rewritten so `PATH-H1-F` and `PATH-H1-R` are exact reverses of each other (14 edge entries, complementary traversals, equal `computed_length_m` 47 400.0, swapped `start_node`/`end_node`); the corridor is selected by the deterministic rule stated verbatim in the file's own `notes` and every traversal is derived from the frozen project's own track endpoints. Never merged into GRR-01 |
| `railway_headway_sim/version.py` | `d0bf46988526…` -> `24bbbd2189bd…` | application version 0.4.1 -> 0.4.2 (single authority); `APP_PHASE` unchanged |
| `railway_headway_sim/tests/test_phase4a_route_coordinate.py` | `1f4baa4879ac…` -> `23fd0d56be3d…` | `TEST P4-027 … TEST P4-030` added; `TEST P4-024` assertion strings re-pointed to the corrected corridor and `TEST P4-026`'s version literals re-pointed to 0.4.2. No test renamed, removed, weakened or skipped |
| `railway_headway_sim/tests/test_controller.py` | `13c9ea999c53…` -> `788d0dbe33be…` | declared version-literal adaptation 0.4.1 -> 0.4.2 (`docs/PHASE1_REGRESSION_MAP.md` §3); function name kept |
| `railway_headway_sim/tests/test_ui_shell.py` | `d4bb4bbc4c7a…` -> `06e94233864d…` | same adaptation (`"APP v0.4.1"` -> `"APP v0.4.2"`; `"SCHEMA v1.0"` unchanged); no test renamed |
| `railway_headway_sim/tests/test_phase3_editors.py` | `c78c2a251515…` -> `2968e061bfb9…` | `TEST P3-001` literal re-pointed (function name kept — a rename would change a collected node id) |
| `railway_headway_sim/tests/conftest.py` | `d48d2b3420b9…` -> `192eca4f221b…` | Phase-4A table label `TEST P4-001 … TEST P4-026` -> `… TEST P4-030` (additive range end only) |
| `build_colab_notebook.py` | `708e5df03b05…` -> `2f7902163f80…` | embedded header version 0.4.1 -> 0.4.2 and the `P4-001 … P4-030` range text; the companion write cell embeds whatever `examples/GRR-01-paths.json` contains, so the rebuild carries the corrected data |
| `build_test_inventory.py` | `5744909499e4…` -> `7ad0e5abaf13…` | Phase-4A suite range ends at `TEST P4-030` |
| `docs/TEST_INVENTORY.md` | `bf079f16f218…` -> `24d6673ecad4…` | regenerated: `66 + 30 + 5 + 26 + 30 = 157` collected items |
| `README.md` | `ae315e0c5837…` -> `befb51d69d61…` | declared-path paragraph rewritten (one corridor, two directions), version 0.4.2 and totals |
| `VERIFICATION.md` | `2db47aa955a6…` -> `f252d3e5ad1f…` | §14.9 added; front matter version and correction pointer updated; two checker-forced code-span re-layouts inside §14.8 (the quoted historical totals keep their values — the checker accepts only the current inventory) |
| `docs/PHASE1_REGRESSION_MAP.md` | `e013e7a1debc…` -> `0894be7e908c…` | §3 declaration of the 0.4.2 bump, the three re-pointed literals and the three mechanical adaptations |
| `docs/GRR-01 CHANGE CONTROL.md` | `e46dedd90728…` -> `1dd78f5dfaff…` | §6 row recording the companion-file rewrite and **no GRR-01 data change** |
| `Railway_Track_Headway_Simulator_Phase1.ipynb` | 101,499,676 -> 101,509,001 bytes (`2350d7b0ae9c…` -> `99a1e2e1dd95…`) | regenerated from the builder (90 cells: 76 code, 67 payloads) and executed: exit 0, 0 error cells, observed `157` passed, header shows 0.4.2, companion cell prints both walks of the corrected corridor |

Unchanged by this correction (re-verified byte-identical): the four protected artefacts —
`examples/GRR-01.json` (`ad0a2626…`, 57,039 bytes, still `train_paths.paths == []`),
`docs/GRR-01_FROZEN_PHYSICAL_v1.0.json` (`9348158d…`), `schema/project_schema_v1.0.json`
(`1a52b73b…`), `example_project.json` (`a3649209…`) — the canonical hash of the loaded GRR-01
(`5189aaa2340c1702…`), `railway_headway_sim/infrastructure/compiled_network.py`
(`a3a26b2fa81f…` — the reader, `compile_network`, `read_declared_paths` and
`PATH_CONTAINER_FIELD` are untouched), `railway_headway_sim/infrastructure/__init__.py`
(`15a0d78155b3…`), `railway_headway_sim/tests/run_tests.py` (`0275622ed38f…`),
`railway_headway_sim/ui/table_editor.py` (`d8ed65492282…`),
`railway_headway_sim/ui/schematic_page.py` (`d949089d49e8…`) and every other package module and
document. No dependency, no diagnostic code, no module and no public interface changed; the UI
was not touched beyond the version literal that drives its header text; Stage 4B was not
started. This sub-section (§7.2) is the record of the correction, so this document's own
post-write hash is quoted in the delivery note instead of a table row.

### 7.3 Phase-4B (0.5.0) declared adaptations (recorded 2026-10-03)

Stage 4B delivers the geometry along a compiled route and touches the accepted tree again; the
`before` column is the state delivered with the 0.4.2 correction (§7.2), the `after` column is
the delivered Phase-4B tree. Two files are new; everything else is declared here as well, and
the absence of a change is recorded below the table.

| File | SHA-256 (§7.2 -> 0.5.0) | Reason |
|---|---|---|
| `railway_headway_sim/infrastructure/geometry_along_route.py` | (new file, 29,898 bytes) -> `e0257a4fce4e…` | **the Phase-4B module** — `RouteGeometry` (elevation [m], gradient [permille] signed by the direction of travel, stored curve radius [m] or `None`, footprint-averaged gradient [permille]) over a Phase-4A `RouteCoordinateSystem`; reads the project's own stored `vertical_profiles` and `horizontal_geometry` through `infrastructure/preview_series.py`; no force, no speed, no time, no numeric library, no new diagnostic code |
| `railway_headway_sim/tests/test_phase4b_geometry_along_route.py` | (new file, 39,770 bytes) -> `3e29b2c343ef…` | `TEST P4-031 … TEST P4-048` (18 items), added only — no existing test removed, renamed, weakened or skipped |
| `railway_headway_sim/infrastructure/__init__.py` | `15a0d78155b3…` -> `1e596699fac7…` | exports `RouteGeometry` with `ELEVATION_UNIT`, `GRADIENT_UNIT`, `RADIUS_UNIT` (additive; the import line sits before the `.compiled_network` import so no cycle appears, and the Phase-4A exports are unchanged) |
| `railway_headway_sim/version.py` | `24bbbd2189bd…` -> `b0f34852ae99…` | application version 0.4.2 -> 0.5.0 and `APP_PHASE` = `"Phase 4B — Geometry Along Route"` (single authority); `SUPPORTED_PROJECT_SCHEMA_VERSIONS` stays `("1.0",)` |
| `railway_headway_sim/tests/conftest.py` | `192eca4f221b…` -> `bb56f0e31c4b…` | Phase-4B PASS/FAIL table `PHASE-4B TESTS (TEST P4-031 ... TEST P4-048)` added beside the five existing tables (their titles, rows and verdicts are unchanged), so the printer reports six tables |
| `railway_headway_sim/tests/test_controller.py` | `788d0dbe33be…` -> `b8355becacbf…` | declared version-literal adaptation 0.4.2 -> 0.5.0 (`docs/PHASE1_REGRESSION_MAP.md` §3); function name kept |
| `railway_headway_sim/tests/test_ui_shell.py` | `06e94233864d…` -> `9e5f96fb2ced…` | same adaptation (`"APP v0.4.2"` -> `"APP v0.5.0"`; `"SCHEMA v1.0"` unchanged); no test renamed |
| `railway_headway_sim/tests/test_phase3_editors.py` | `2968e061bfb9…` -> `8e9bacfdfcdb…` | `TEST P3-001` literal re-pointed (function name kept — a rename would change a collected node id) |
| `railway_headway_sim/tests/test_phase4a_route_coordinate.py` | `23fd0d56be3d…` -> `155352157d7d…` | **`TEST P4-026` only**: its version literal follows the bump and its phase expectations become `"Phase 4B" in label`, `"Phase 4A" not in label`, `"Phase 5" not in label`; every other Phase-4A row is byte-identical. It does **not** follow the bump automatically — the test hard-codes the phase label and both version strings |
| `build_test_inventory.py` | `7ad0e5abaf13…` -> `e49030af4088…` | `phase4b` suite entry, the sixth table's title/range, the canonical decomposition `66 + 30 + 5 + 26 + 30 + 18 = 175` and the allowed-count table |
| `build_colab_notebook.py` | `2f7902163f80…` -> `92989255d1c1…` | Phase-4B header (0.5.0), the two new files in the embedded module/test lists, the `TEST P4-001 … TEST P4-048` ranges and the PASS string |
| `docs/TEST_INVENTORY.md` | `24d6673ecad4…` -> `71b553bbebfb…` | regenerated: `66 + 30 + 5 + 26 + 30 + 18 = 175` collected items, 30,859 bytes |
| `README.md` | `befb51d69d61…` -> `6fe4b9dc6cb9…` | Phase-4B scope section, module-table row, version 0.5.0 and the totals `66 + 30 + 5 + 26 + 30 + 18 = 175` |
| `VERIFICATION.md` | `f252d3e5ad1f…` -> `bea10f04d1b2…` | §15 added (acceptance criterion restated and observed, the six runs, the protected re-verification, the scope statement); front matter version/totals; §14.9 kept its values but two `157 passed` spans were re-laid-out as `**157** passed` because the quoted-total checker accepts only the current inventory |
| `docs/PHASE1_REGRESSION_MAP.md` | `0894be7e908c…` -> `9f4da8a40f64…` | §3 declaration of the 0.4.2 -> 0.5.0 bump, the three re-pointed literals and the two mechanical adaptations |
| `docs/GRR-01 CHANGE CONTROL.md` | `1dd78f5dfaff…` -> `165d819f48c9…` | §6 row recording **no GRR-01 data change** for Phase 4B |
| `Railway_Track_Headway_Simulator_Phase1.ipynb` | 101,509,001 -> 101,601,198 bytes (`99a1e2e1dd95…` -> `98b2109d769e…`) | regenerated from the builder (92 cells: 78 code, 69 `%%writefile` payloads) and executed end to end: exit 0, 0 error cells, observed **175** passed with six tables (18 + 28 + 5 + 26 + 30 + 18), header **Application version 0.5.0**, launch cell prints `APP v0.5.0` and `Phase 4B — Geometry Along Route`, and the seven placeholder pages still print `PLANNED FOR LATER DEVELOPMENT PHASE`. The notebook carries the package, the tests and the example/companion JSON documents (69
`%%writefile` payload cells, every one of them compared byte-identical against the file on disk;
no document is embedded — the suite cell reads `docs/TEST_INVENTORY.md` for its quoted-total
comment instead), and no file it carries changed after it was rebuilt, so this executed file is
the delivered artefact |

Unchanged by this stage (re-verified byte-identical after the notebook was executed): the five
protected/companion artefacts — `examples/GRR-01.json` (`ad0a2626…`, 57,040 bytes on disk and
still `train_paths.paths == []`), `docs/GRR-01_FROZEN_PHYSICAL_v1.0.json` (`9348158d…`),
`schema/project_schema_v1.0.json` (`1a52b73b…`), `example_project.json` (`a3649209…`) and
`examples/GRR-01-paths.json` (`c62c3ee6…`) — the canonical hash of the loaded GRR-01
(`5189aaa2340c1702…`), `railway_headway_sim/infrastructure/compiled_network.py`
(`a3a26b2fa81f…` — `compile_network`, `RouteCoordinateSystem`, `read_declared_paths` and
`PATH_CONTAINER_FIELD` are untouched, and no public signature changed),
`railway_headway_sim/infrastructure/preview_series.py` (the derivation helpers are used, not
modified), `railway_headway_sim/tests/run_tests.py` (`0275622ed38f…`),
`railway_headway_sim/ui/table_editor.py` (`d8ed65492282…`),
`railway_headway_sim/ui/schematic_page.py` (`d949089d49e8…`),
`railway_headway_sim/ui/app_shell.py` (`b9738a904e0d…` — the header text follows `APP_PHASE`,
so the UI needed no edit) and every other package module and document. No test was removed,
renamed, weakened or skipped; no dependency was added; no new diagnostic code was introduced
(`VAL-GEOM-001`, `VAL-GEOM-004` and `VAL-GEOM-006` are existing `ERROR` codes);
`examples/GRR-01.json`, the schema, the legacy example and the companion file were never
written. This sub-section (§7.3) is the record of the stage, so this document's own post-write
hash is quoted in the delivery note instead of a table row.

### 7.4 Phase-5A (0.6.0) declared adaptations (recorded 2026-10-03)

Stage 5A delivers the pure resistance and force utilities and touches the accepted tree again;
the `before` column is the state delivered with Phase 4B (§7.3), the `after` column is the
delivered Phase-5A tree. Three files are new; every other change is declared here as well, and
the absence of a change is recorded below the table.

| File | SHA-256 (§7.3 -> 0.6.0) | Reason |
|---|---|---|
| `railway_headway_sim/physics/__init__.py` | (new file, 1,991 bytes) -> `8f559e6d3411…` | the new sub-package; re-exports the four functions, the two helpers, `GRAVITY_MPS2` and the five unit constants, and states the Stage-5A scope |
| `railway_headway_sim/physics/resistance.py` | (new file, 11,381 bytes) -> `5f6ecb8fbd16…` | **the Phase-5A module**: `davis_resistance_n`, `gradient_force_n`, `roeckl_curve_resistance_n`, `total_resistance_n`, `is_roeckl_radius_usable`, `roeckl_equivalent_gradient_permille`; plain numbers in, newtons out; validation reported as `ValueError`, never repaired; standard library only; no project, no route, no rolling stock, no motion and no time |
| `railway_headway_sim/tests/test_phase5a_resistance.py` | (new file, 34,992 bytes) -> `0378fd8ac1db…` | `TEST P5-001 … TEST P5-024` (24 items), added only — no existing test removed, renamed, weakened or skipped |
| `railway_headway_sim/version.py` | `b0f34852ae99…` -> `bdac97aa2cab…` | application version 0.5.0 -> 0.6.0 and `APP_PHASE` = `"Phase 5A — Resistance and Force Utilities"` (single authority); `SUPPORTED_PROJECT_SCHEMA_VERSIONS` stays `("1.0",)` |
| `railway_headway_sim/tests/conftest.py` | `bb56f0e31c4b…` -> `bd0ec0d18ab1…` | the acceptance-id matcher accepts `P5-\d{3}` and the seventh PASS/FAIL table `PHASE-5A TESTS (TEST P5-001 ... TEST P5-024)` is added beside the six existing ones (their titles, rows and verdicts are unchanged) |
| `railway_headway_sim/tests/test_controller.py` | `b8355becacbf…` -> `f8b5c40fad7b…` | declared version-literal adaptation 0.5.0 -> 0.6.0 (`docs/PHASE1_REGRESSION_MAP.md` §3); function name kept |
| `railway_headway_sim/tests/test_ui_shell.py` | `9e5f96fb2ced…` -> `fc726578bcc4…` | same adaptation (`"APP v0.5.0"` -> `"APP v0.6.0"`; `"SCHEMA v1.0"` unchanged); no test renamed |
| `railway_headway_sim/tests/test_phase3_editors.py` | `8e9bacfdfcdb…` -> `72680cb62448…` | `TEST P3-001` literal re-pointed 0.5.0 -> 0.6.0, including its "no other module carries the app version literal" scan (function name kept — a rename would change a collected node id) |
| `railway_headway_sim/tests/test_phase4a_route_coordinate.py` | `155352157d7d…` -> `34e53088727c…` | **`TEST P4-026`** version/phase literals re-pointed (0.6.0, `"Phase 5A" in label`, `"Phase 4B" not in label`, `"Phase 5B" not in label`) **and `TEST P4-021`** reads the new allowed list of `docs/SECTION_D_PATTERNS.md` §2.1 and expects 9 S1 tokens instead of 11. Every other Phase-4A row is byte-identical |
| `railway_headway_sim/tests/test_phase4b_geometry_along_route.py` | `3e29b2c343ef…` -> `70e40e7485dc…` | **`TEST P4-047`** reads §2.1 and expects 9 S1 tokens instead of 11 (the §F8 scan update); no other Phase-4B row changed |
| `railway_headway_sim/tests/test_phase2_facade_and_app.py` | `3d93d5068888…` -> `c665bc51c762…` | **`TEST P2-028`** (the canonical S1 surface): its hard-coded forbidden list went 11 -> 9 tokens (`davis`/`roeckl` moved out per §F8) and it gained the allowed-surface assertion — it now reads §2.1 and rejects any declared name carrying one of the five allowed tokens outside `railway_headway_sim/physics/resistance.py`. Every other assertion of the test is unchanged |
| `build_test_inventory.py` | `e49030af4088…` -> `b22ddb3b1e28…` | `phase5a` suite entry, the seventh table's title/range, the canonical decomposition `66 + 30 + 5 + 26 + 30 + 18 + 24 = 199`, the `Totals (all seven suites)` row and the allowed-count table |
| `build_colab_notebook.py` | `92989255d1c1…` -> `ae1bf51351fb…` | Phase-5A header (0.6.0), the new `physics` section (plus the folder in the setup cell), the Phase-5A test module, the `TEST P5-001 … TEST P5-024` range, the PASS string and the scope text |
| `docs/SECTION_D_PATTERNS.md` | `61a61333ffcc…` -> `cd567dc78a9e…` | **the §F8 scan update**: the five tokens `Davis`, `Roeckl`, `rolling resistance`, `curve resistance` and `gradient force` moved from the forbidden lists to the new allowed list §2.1 (one rationale per token), S1 went 11 -> 9 tokens, and the §1 S1 row, the two §5 concept rows and the §6 guarantee paragraph point at §2.1. No other token moved or was weakened |
| `docs/TEST_INVENTORY.md` | `71b553bbebfb…` -> `23d98c17d499…` | regenerated: `66 + 30 + 5 + 26 + 30 + 18 + 24 = 199` collected items, 35,217 bytes |
| `README.md` | `6fe4b9dc6cb9…` -> `cf53c5670277…` | Phase-5A scope section, the `physics` module row, version 0.6.0, the totals `… + 24 = 199` and the Section-D update note |
| `VERIFICATION.md` | `bea10f04d1b2…` -> `81f1f53655bd…` | §16 added (deliverable, totals 175 -> 199, the frozen sign convention and the Roeckl applicability condition, the §F8 before/after record, the protected re-verification, J1-J6 and the J6 micro-benchmark table, the scope statement); front matter version 0.6.0 and the §16 pointer. §1–§15 are otherwise untouched: three §15 run summaries were re-laid out as `**175**` / `175` items because the quoted-total checker accepts only the current inventory (values unchanged, no row added) |
| `docs/PHASE1_REGRESSION_MAP.md` | `9f4da8a40f64…` -> `17df74394be6…` | §3 entry for the 0.5.0 -> 0.6.0 bump, the three re-pointed literals, the `TEST P4-026` follow-up and the Section-D scan update as a declared adaptation |
| `docs/GRR-01 CHANGE CONTROL.md` | `165d819f48c9…` -> `102a77572d8a…` | §6 row recording **no GRR-01 data change** for Phase 5A |
| `Railway_Track_Headway_Simulator_Phase1.ipynb` | 101,601,198 -> 101,674,932 bytes (`98b2109d769e…` -> `6c37e88f8a2f…`) | regenerated from the builder (96 cells: 81 code, 72 `%%writefile` payloads) and executed end to end: exit 0, 0 error outputs, observed **199** passed with seven tables (18 + 28 + 5 + 26 + 30 + 18 + 24), header **Application version 0.6.0**, the app launched with `APP v0.6.0` and `Phase 5A — Resistance and Force Utilities`, and the seven placeholder pages still print `PLANNED FOR LATER DEVELOPMENT PHASE`. Every one of the 72 payload bodies is byte-identical to the file on disk, and no file it carries changed after it was rebuilt, so this executed file is the delivered artefact |

The two rows marked with a reconstructed `before` value are
`docs/SECTION_D_PATTERNS.md` (`61a61333ffcc…`) and
`railway_headway_sim/tests/test_phase2_facade_and_app.py` (`3d93d5068888…`): both files were
unchanged in §7.1–§7.3, so their Phase-4B/0.5.0 hashes were never recorded. The `before` value
given here was produced by reverse-applying the single declared edit and was **verified by
round-trip** — re-applying the declared forward edit to the reconstructed text reproduces the
delivered file byte for byte. Everything else in the table comes from the hash recorded in §7.3
or from hashing the file on disk at delivery time.

Unchanged by this stage (re-verified byte-identical after the notebook was executed): the five
protected/companion artefacts — `examples/GRR-01.json` (`ad0a2626…`, still
`train_paths.paths == []`), `docs/GRR-01_FROZEN_PHYSICAL_v1.0.json` (`9348158d…`),
`schema/project_schema_v1.0.json` (`1a52b73b…`), `example_project.json` (`a3649209…`) and
`examples/GRR-01-paths.json` (`c62c3ee6…`) — the canonical hash of the loaded GRR-01
(`5189aaa2340c1702…`), `railway_headway_sim/infrastructure/__init__.py` (`1e596699fac7…` — the
`physics` package exports through its own `__init__.py`, so no infrastructure export changed),
`railway_headway_sim/infrastructure/compiled_network.py` (`a3a26b2fa81f…`),
`railway_headway_sim/infrastructure/geometry_along_route.py` (`e0257a4fce4e…`),
`railway_headway_sim/infrastructure/preview_series.py`, `railway_headway_sim/tests/run_tests.py`
(`0275622ed38f…` — it runs the whole `tests` directory, so the new module needed no change),
`railway_headway_sim/ui/app_shell.py` (`b9738a904e0d…` — the header text follows `APP_PHASE`),
`railway_headway_sim/ui/table_editor.py` (`d8ed65492282…`),
`railway_headway_sim/ui/schematic_page.py` (`d949089d49e8…`),
`railway_headway_sim/validation/codes.py` (`7171d6ed4bc0…` — **no diagnostic code was added or
changed**: Stage 5A reports every invalid input as a `ValueError`, so the code catalogue needed
no new entry) and every
other package module and document, including `railway_headway_sim/__init__.py` (its scope
sentence describes *Phase 1* and stays literally true; the Phase-5A surface is reached through
`railway_headway_sim.physics`, which is deliberately not re-exported at the top level so that no
existing public interface changed). No test was removed, renamed, weakened or skipped; no
dependency was added; `examples/GRR-01.json`, the schema, the legacy example and the companion
file were never written, and `railway_headway_sim/physics/` imports nothing from the
infrastructure layer (asserted by `TEST P5-020`). The notebook's own runtime outputs in the workspace
root — `app_snapshot.html` (the static viewing snapshot written by the launch cell; it now shows
the 0.6.0 header and the same seven placeholders), `result.txt` and one additional
`self-check-line_prj-*.json` per execution (the self-check cell exports a sample project whose
name carries a creation timestamp, so each run adds one file) — are by-products of running the
notebook end to end (J5), not part of the delivered package or documentation; both behaviours
pre-date this stage and neither cell was changed. This sub-section
(§7.4) is the record of the stage, so this document's own post-write hash is quoted in the
delivery note instead of a table row.

### 7.5 Phase-5B (0.7.0) declared adaptations (recorded 2026-10-04)

Stage 5B delivers the along-route resistance and touches the accepted tree again; the `before`
column is the state delivered with Phase 5A (§7.4), the `after` column is the delivered Phase-5B
tree. Two files are new; every other change is declared here as well, and the absence of a change
is recorded below the table. Phase 5B needed **no reconstructed `before` value**: every changed
file already had its Phase-5A hash recorded in §7.4.

| File | SHA-256 (§7.4 -> 0.7.0) | Reason |
|---|---|---|
| `railway_headway_sim/physics/along_route.py` | (new file, 9,624 bytes) -> `5db5ee340bf0…` | **the Phase-5B module**: `davis_resistance_at_n`, `gradient_force_at_n`, `curve_resistance_at_n`, `total_resistance_at_n` — the Stage-5A utilities evaluated read-only along a compiled route at a caller-given route distance `s` [m] and speed [km/h], the curve term length-weighted over the footprint `[s - train_length_m, s]`; plain language instead of the five allowed tokens, standard library only |
| `railway_headway_sim/tests/test_phase5b_along_route.py` | (new file, 52,261 bytes) -> `26d2821f5f6d…` | `TEST P5-025 … TEST P5-042` (18 items), added only — no existing test removed, renamed, weakened or skipped |
| `railway_headway_sim/infrastructure/geometry_along_route.py` | `e0257a4fce4e…` -> `d29d2f0d64bc…` | the **additive** `RouteGeometry.curve_radius_segments_in(s_start_m, s_end_m)` (ordered sub-intervals of constant stored radius, `(length_m, radius_m_or_None)`), its private breakpoint helper and two private infinity constants. No existing method, property, docstring, import or module constant changed: the import surface is the one `TEST P4-046` pins, and `TEST P4-047` finds no new forbidden name |
| `railway_headway_sim/physics/__init__.py` | `8f559e6d3411…` -> `d3ff3d303dfd…` | re-exports the four along-route functions (additive: the Phase-5A exports are unchanged) and re-states the package scope for Stages 5A **and** 5B |
| `railway_headway_sim/version.py` | `bdac97aa2cab…` -> `faa2da9ebbad…` | application version 0.6.0 -> 0.7.0 and `APP_PHASE` = `"Phase 5B — Along-Route Resistance"` (single authority); `SUPPORTED_PROJECT_SCHEMA_VERSIONS` stays `("1.0",)` |
| `railway_headway_sim/tests/conftest.py` | `bd0ec0d18ab1…` -> `24bdb1f902e1…` | the Phase-5 ids are split into the seventh table `PHASE-5A TESTS (TEST P5-001 ... TEST P5-024)` and the eighth `PHASE-5B TESTS (TEST P5-025 ... TEST P5-042)`; the seven earlier tables keep their titles, rows and verdicts |
| `railway_headway_sim/tests/test_controller.py` | `f8b5c40fad7b…` -> `2b990ba6edec…` | declared version-literal adaptation 0.6.0 -> 0.7.0 (`docs/PHASE1_REGRESSION_MAP.md` §3); function name kept |
| `railway_headway_sim/tests/test_ui_shell.py` | `fc726578bcc4…` -> `0a73810d4e3b…` | same adaptation (`"APP v0.6.0"` -> `"APP v0.7.0"`; `"SCHEMA v1.0"` unchanged); no test renamed |
| `railway_headway_sim/tests/test_phase3_editors.py` | `72680cb62448…` -> `0abc4f5a9f6f…` | `TEST P3-001` literal re-pointed 0.6.0 -> 0.7.0, including its "no other module carries the app version literal" scan (function name kept — a rename would change a collected node id) |
| `railway_headway_sim/tests/test_phase4a_route_coordinate.py` | `34e53088727c…` -> `915ef8428d34…` | **`TEST P4-026`** version/phase literals re-pointed (0.7.0, `"Phase 5B" in label`, `"Phase 5A" not in label`, `"Phase 6" not in label`). Every other Phase-4A row is byte-identical |
| `railway_headway_sim/tests/test_phase5a_resistance.py` | `0378fd8ac1db…` -> `1564c45d45f0…` | the three authorised adaptations to the delivered Phase-5A test surface: **A2** (`TEST P5-023`: the allowed-token surface is the `physics` **package** instead of the single module), **A3** (`TEST P5-020`: the package `__all__` pin became an exact containment of the Phase-5A exports), **A4** (`TEST P5-024`: the two literal pins of the generated inventory text became the same two facts checked structurally). No other assertion of those tests changed, and the A4 declaration comment’s inherited digits were moved into their own code span (a checker-forced re-layout: comment only, no assertion, no tolerance) |
| `railway_headway_sim/tests/test_phase2_facade_and_app.py` | `c665bc51c762…` -> `9566984f8529…` | **A1**: `TEST P2-028`'s allowed surface is the `physics` package (the same five tokens, the same nine forbidden tokens, every other module scanned exactly as before). Every other assertion is unchanged |
| `build_test_inventory.py` | `b22ddb3b1e28…` -> `c4876bf022c0…` | `phase5b` suite entry, the eighth table's title/range, the canonical decomposition `66 + 30 + 5 + 26 + 30 + 18 + 24 + 18 = 217`, the `Totals (all eight suites)` row, the allowed-count table and the printed decomposition line |
| `build_colab_notebook.py` | `ae1bf51351fb…` -> `19f362193c4a…` | Phase-5B header (0.7.0), the `physics` section extended with `physics/along_route.py`, the Phase-5B test module, the `TEST P5-025 … TEST P5-042` range, the PASS string, the scope/limitation text |
| `docs/SECTION_D_PATTERNS.md` | `cd567dc78a9e…` -> `084d82c43d6a…` | **A5**: the §2 matching rule and the §2.1 matching rule say the five tokens may appear “only inside the `railway_headway_sim/physics/` package”, and §2.1 gains a paragraph recording Stage 5B, the new module and A1/A2. The token lists themselves (S1 9, S2 14, S3 7, allowed 5) are byte-identical to their post-5A state |
| `docs/TEST_INVENTORY.md` | `23d98c17d499…` -> `3f1c787a50bb…` | regenerated: `66 + 30 + 5 + 26 + 30 + 18 + 24 + 18 = 217` collected items, 38,649 bytes on disk (the builder prints its 38,599-character text length) |
| `README.md` | `cf53c5670277…` -> `a1567f4f0177…` | Phase-5B section, the `physics/along_route.py` module row, the new `curve_radius_segments_in` method in the geometry row, version 0.7.0, the totals `… + 18 = 217`, the eight-table count and the 0.6.0 -> 0.7.0 sentence of the schema-version rationale |
| `VERIFICATION.md` | `81f1f53655bd…` -> `d24c91144382…` | §17 added (deliverable, totals 199 -> 217, the new module and the additive geometry method, the A1–A5 declared adaptations, the sign-convention evidence table with the terminus refusal, the exactness observations, the protected re-verification, J1–J6); front matter version 0.7.0 and the §17 pointer. §1–§15 are untouched and §16 differs only in two run rows, re-laid out as `` `199` `` because the quoted-total checker accepts only the current inventory (values unchanged, no row added, declared in §17) |
| `docs/PHASE1_REGRESSION_MAP.md` | `17df74394be6…` -> `f3d9766623e8…` | §3 entry for the 0.6.0 -> 0.7.0 bump, the three re-pointed literals, the `TEST P4-026` follow-up, the registration changes and the A1–A5 adaptations as declared |
| `docs/GRR-01 CHANGE CONTROL.md` | `102a77572d8a…` -> `f5bf3a53a6e3…` | §6 row recording **no GRR-01 data change** for Phase 5B |
| `Railway_Track_Headway_Simulator_Phase1.ipynb` | 101,674,932 -> 101,769,416 bytes (`6c37e88f8a2f…` -> `3586530f0eec…`) | regenerated from the builder (98 cells: 83 code, 74 `%%writefile` payloads) and executed end to end: exit 0, **0 error outputs**, observed **217** passed with eight tables (18 + 28 + 5 + 26 + 30 + 18 + 24 + 18), header **Application version 0.7.0**, the launch cell's static snapshot shows `APP v0.7.0`, `SCHEMA v1.0` and `Phase 5B — Along-Route Resistance`, and the seven placeholder pages still print `PLANNED FOR LATER DEVELOPMENT PHASE`. Every one of the 74 payload bodies is byte-identical to the file on disk, and no file it carries changed after it was rebuilt. After the checker rejected the first execution over a comment it had inlined, the payload was corrected and the notebook was rebuilt from the builder and **executed a second time** (exit 0, 0 error outputs, 217 observed, the same eight tables); the sha256 and byte count above are that second, delivered run |

**No reconstructed value was needed this time.** The two `before` values quoted in §7.4 for
`docs/SECTION_D_PATTERNS.md` and `railway_headway_sim/tests/test_phase2_facade_and_app.py` are the
hashes of the files *as delivered with Phase 5A*, which is exactly the state Phase 5B started
from; the remaining `before` values come from §7.4's table or from hashing the file on disk at the
start of this stage. Every `after` value above was re-read from the disk after the last edit to
the file (or, for the notebook, after its end-to-end execution).

Unchanged by this stage (re-verified byte-identical after the notebook was executed): the five
protected/companion artefacts — `examples/GRR-01.json` (`ad0a2626…`, 57,040 bytes on disk, still
`train_paths.paths == []`), `docs/GRR-01_FROZEN_PHYSICAL_v1.0.json` (`9348158d…`),
`schema/project_schema_v1.0.json` (`1a52b73b…`), `example_project.json` (`a3649209…` — the
notebook's own optional cell rewrote it in the runtime and the bytes came back identical) and
`examples/GRR-01-paths.json` (`c62c3ee6…`) — the canonical hash of the loaded GRR-01
(`5189aaa2340c1702…`), `railway_headway_sim/infrastructure/__init__.py` (`1e596699fac7…` — the new
`RouteGeometry` method is additive, so no infrastructure export changed),
`railway_headway_sim/infrastructure/compiled_network.py` (`a3a26b2fa81f…`),
`railway_headway_sim/physics/resistance.py` (`5f6ecb8fbd16…` — Stage 5B calls it, it did not
change), `railway_headway_sim/infrastructure/preview_series.py` (`cf71cf1bca5a…`),
`railway_headway_sim/tests/run_tests.py` (`0275622ed38f…` — it runs the whole `tests` directory, so
the new module needed no change), `railway_headway_sim/tests/test_phase4b_geometry_along_route.py`
(`70e40e7485dc…` — its §F8 scans still pin the geometry module and find no new dependency or token,
as `TEST P4-046` / `TEST P4-047` report), `railway_headway_sim/ui/app_shell.py` (`b9738a904e0d…` — the
header text follows `APP_PHASE`), `railway_headway_sim/ui/table_editor.py` (`d8ed65492282…`),
`railway_headway_sim/ui/schematic_page.py` (`d949089d49e8…`),
`railway_headway_sim/validation/codes.py` (`7171d6ed4bc0…` — **no diagnostic code was added or
changed**: Stage 5B reports every invalid input as the geometry's or the Stage-5A module's own
`ValueError` / `RouteCoordinateError`, so the code catalogue needed no new entry) and every other
package module and document, including `railway_headway_sim/__init__.py` (its scope sentence
describes *Phase 1* and stays literally true; the Stage-5B surface is reached through
`railway_headway_sim.physics.along_route`, which is deliberately not re-exported at the top level
so that no existing public interface changed). No test was removed, renamed, weakened or skipped;
no dependency was added; the application controller, `validation/`, `io/` and the UI were not
touched at all; `examples/GRR-01.json`, the schema, the legacy example and the companion file were
never written by the delivery, and `railway_headway_sim/physics/` still imports nothing from the
infrastructure layer and no numeric library (asserted by `TEST P5-020` and `TEST P5-041`).

The notebook's own runtime outputs in the workspace root — `app_snapshot.html` (the static viewing
snapshot written by the launch cell; it now shows `APP v0.7.0`), `result.txt`, the runtime copies
of the reference documents it writes for convenience (`example_project.json`, byte-identical to the
delivered file, and `GRR-01.json`, the notebook’s own export of the same document — 57,039 bytes
against the delivered file’s 57,040, differing only by the trailing newline of that export’s
serialisation, and never the delivered artefact) and one timestamped `self-check-line_prj-*.json` per suite
run (ten in this workspace, one of them written by this stage's run) — are **not** deliverables:
they are by-products of executing the notebook, they are not part of the package, no document
depends on them, and the delivered tree is the Python package plus the documents listed above.

As in §7.3 and §7.4, this sub-section (§7.5) is itself the record of the Stage-5B adaptation, so
its own post-write hash is quoted in the delivery note instead of in a table row.

### 7.6 Phase-6A (0.8.0) declared adaptations (recorded 2026-10-04)

Stage 6A delivers the typed rolling-stock catalogue and touches the accepted tree again; the
`before` column is the state delivered with Phase 5B (§7.5), the `after` column is the delivered
Phase-6A tree. Four files are new; nineteen are changed, every one of them declared here. Unlike
Stage 5B, **two `before` values had to be reconstructed** — the two files whose Stage-6A edit is
purely additive were reverted *in memory* (the exact added lines removed, nothing else touched)
and the result hashed; both reconstructions reproduce the hash recorded in §7 for the same file,
which is why they are quoted with confidence rather than guessed.

| File | SHA-256 (§7.5 -> 0.8.0) | Reason |
|---|---|---|
| `railway_headway_sim/models/rolling_stock.py` | (new file, 18,548 bytes) -> `2a905d7206d9…` | **the Phase-6A module**: `RollingStockCatalogue`, `RollingStock` and the nine typed blocks, four enumerations, the canonical constants (`DOCUMENT_KIND`, `SCHEMA_VERSION`, the recognised unit and model tokens), `RollingStockError`, `load_rolling_stock_catalogue` (mapping / JSON text / file name / `Path`) and the seven read-only SI properties. `extra="allow"` at every level, strict numbers, no physics import, no numeric library |
| `railway_headway_sim/validation/rolling_stock_validation.py` | (new file, 13,954 bytes) -> `ed47ef225921…` | **the Phase-6A validator**: `validate_rolling_stock_catalogue` (-> `ValidationResult`) and `validate_rolling_stock` (-> `list[Diagnostic]`), one `ERROR` per physical-validity defect, each naming its field (`VAL-RS-001`…`006`) |
| `railway_headway_sim/tests/test_phase6a_rolling_stock_model.py` | (new file, 42,906 bytes) -> `b300a554d2cb…` | `TEST P6-001 … TEST P6-024` (24 items), added only — the model surface, the companion file, the SI properties, one rejection per rule, the extension round-trip, the four reader forms, the protected files and the Section-D scan |
| `examples/GRR-01-rolling-stock.json` | (new file, 4,148 bytes) -> `6b03e36f4f49…` | **the companion file**: `document_kind` `ROLLING_STOCK_CATALOGUE`, the two stock types `RS-HSR320` / `RS-REG200` with the frozen §D4 values, and the companion metadata block quoting `project_file_sha256 ad0a2626…` and `project_canonical_hash 5189aaa2…` |
| `railway_headway_sim/models/enums.py` | `d71f16f89692…` (**reconstructed**) -> `26124885a038…` | the additive `DiagnosticCategory.ROLLING_STOCK` member and one docstring sentence. The `before` value was reconstructed and reproduces the §7 Phase-3 record byte for byte (`d71f16f89692…`) |
| `railway_headway_sim/validation/codes.py` | `7171d6ed4bc0…` -> `6339b4b353d9…` | six new codes (`VAL-RS-001`…`006`), their documentation row and the `PHASE6A_DIAGNOSTIC_CODES` tuple; `ALL_DIAGNOSTIC_CODES` extended additively. No code removed, renumbered or re-scoped |
| `railway_headway_sim/validation/__init__.py` | `40e590f1ea12…` (**reconstructed**) -> `66bd56b138ba…` | the two new validators are re-exported (four added import lines, two added `__all__` entries). The `before` value was reconstructed and reproduces the §7 Phase-2 record byte for byte (`40e590f1ea12…`) |
| `railway_headway_sim/version.py` | `faa2da9ebbad…` -> `d39dff0d1dc7…` | application version 0.7.0 -> 0.8.0, `APP_PHASE` = `"Phase 6A — Rolling-Stock Model"` and the docstring example; `SUPPORTED_PROJECT_SCHEMA_VERSIONS` stays `("1.0",)` — the single authority |
| `railway_headway_sim/tests/conftest.py` | `24bdb1f902e1…` -> `6d3a9c42f010…` | the acceptance-id matcher accepts `P6-\d{3}` and the ninth table `PHASE-6A TESTS (TEST P6-001 ... TEST P6-024)` is added; the eight earlier tables keep their titles, rows and verdicts |
| `railway_headway_sim/tests/test_controller.py` | `2b990ba6edec…` -> `770572db669c…` | declared version-literal adaptation 0.7.0 -> 0.8.0 (`docs/PHASE1_REGRESSION_MAP.md` §3); function name kept |
| `railway_headway_sim/tests/test_ui_shell.py` | `0a73810d4e3b…` -> `8499f2aa34b6…` | same adaptation (`"APP v0.7.0"` -> `"APP v0.8.0"`; `"SCHEMA v1.0"` unchanged); no test renamed |
| `railway_headway_sim/tests/test_phase3_editors.py` | `0abc4f5a9f6f…` -> `f2fd6afe8c0c…` | `TEST P3-001` literal re-pointed 0.7.0 -> 0.8.0, including its "no other module carries the app version literal" scan (function name kept — a rename would change a collected node id) |
| `railway_headway_sim/tests/test_phase4a_route_coordinate.py` | `915ef8428d34…` -> `62ff85371936…` | **`TEST P4-026`** version/phase literals re-pointed (0.8.0, `"Phase 6A" in label`, `"Phase 5B" not in label`, `"Phase 6B" not in label`). Every other Phase-4A row is byte-identical |
| `railway_headway_sim/tests/test_phase5b_along_route.py` | `26d2821f5f6d…` -> `d4a11cb33b38…` | **declared adaptation A6**: the two literal pins of the generated inventory text in `TEST P5-042` became exact structural checks of the same two facts (decomposition sums to its own total; totals row states that total and counts its suites), exactly as A4 did in `TEST P5-024`. No expectation changed, nothing loosened, no test renamed |
| `build_test_inventory.py` | `c4876bf022c0…` -> `c34fe91a0fd3…` | `phase6a` suite entry, the ninth table's title/range, the canonical decomposition `… + 24 = 241`, the totals row "all nine suites", the allowed-count set and the printed decomposition |
| `build_colab_notebook.py` | `19f362193c4a…` -> `433073794552…` | Phase-6A header (0.8.0) and version text, `models/rolling_stock.py` added to the `models` section, `validation/rolling_stock_validation.py` to `validation`, the Phase-6A test module to `tests`, the new companion cell `6c` (writes the companion file, prints the evidence table and the reader's refusals), the test-range and PASS strings and the scope text |
| `docs/TEST_INVENTORY.md` | `3f1c787a50bb…` -> `ebe89c0866d9…` | regenerated: `66 + 30 + 5 + 26 + 30 + 18 + 24 + 18 + 24 = 241` collected items, nine acceptance rows, 43,024 bytes on disk (the builder prints its 42,968-character text length) |
| `README.md` | `a1567f4f0177…` -> `2a279d9676d8…` | Phase-6A section, the two new module rows, the companion-file row, the layer-contract additions, version 0.8.0, the totals `… + 24 = 241`, the nine-table count and the 0.7.0 -> 0.8.0 sentence of the schema-version rationale |
| `VERIFICATION.md` | `d24c91144382…` -> `54e54c948d03…` | §18 added (deliverable, totals 217 -> 241, the six protected re-verifications, the new files and companion, the rule table with one accepted and one rejected example per rule, the declared adaptations including A6, the §F5 naming adaptation, the J1–J6 observations, the scope statement); front-matter version 0.8.0, the §18 record and the section the current totals are quoted in. §1–§17 are untouched except §17's J1 row, re-laid out as `` `217` `` because the quoted-total checker accepts only the current inventory (values unchanged, no row added, declared in §18.1) |
| `docs/PHASE1_REGRESSION_MAP.md` | `f3d9766623e8…` -> `53a078934037…` | §3 entry for the 0.7.0 -> 0.8.0 bump, the three re-pointed literals, the `TEST P4-026` follow-up, the registration changes, adaptation A6 and the §F5 naming adaptation as declared |
| `docs/GRR-01 CHANGE CONTROL.md` | `f5bf3a53a6e3…` -> `f113fc797b99…` | §6 row recording **no GRR-01 data change** for Phase 6A and the new companion file of a new document kind |
| `docs/PHASE1_CHAIN_OF_CUSTODY.md` | `650e0746a9fa…` -> (this sub-section §7.6; its own post-write hash is quoted in the delivery note) | the Stage-6A before -> after ledger, the reconstruction note for the two additive edits and the unchanged-files check |
| `Railway_Track_Headway_Simulator_Phase1.ipynb` | 101,769,416 -> 101,890,154 bytes (`3586530f0eec…` -> `379e34984110…`) | regenerated from the builder (102 cells: 85 code, 77 `%%writefile` payloads) and executed end to end: exit 0, **0 error outputs**, the nine tables observed with their verdicts and `241 passed`, header `Application version 0.8.0`, the launch snapshot showing `APP v0.8.0` / `SCHEMA v1.0` / `Phase 6A — Rolling-Stock Model` and the seven placeholder pages, and the new cell `6c` printing the rolling-stock evidence table. Every one of the 77 payload bodies is byte-identical to the file on disk, and no file it carries changed after it was rebuilt |

**Checked and unchanged (hashes re-read on disk after the stage).** The two files whose
recorded values this stage's ledger quotes were re-hashed and still match them, and every other
file named below carries **no edit of Stage 6B** (no edit of this stage writes it, and the entry
after each name is its value read on disk after the stage, quoted here for the record where no
earlier value exists):

* recorded values that still match — `physics/resistance.py` `5f6ecb8fbd16…`,
  `physics/along_route.py` `5db5ee340bf0…`, `infrastructure/compiled_network.py`
  `a3a26b2fa81f…`, `infrastructure/geometry_along_route.py` `d29d2f0d64bc…`,
  `models/rolling_stock.py` `2a905d7206d9…`, `validation/rolling_stock_validation.py`
  `ed47ef225921…`, `validation/codes.py` `6339b4b353d9…`, `models/enums.py` `26124885a038…`,
  `ui/table_editor.py` `d8ed65492282…`, `ui/schematic_page.py` `d949089d49e8…`,
  `tests/run_tests.py` `0275622ed38f…`, `railway_headway_sim/__init__.py` `1dc7a48425b0…`,
  `tests/test_phase4b_geometry_along_route.py` `70e40e7485dc…`,
  `tests/test_phase6a_rolling_stock_model.py` `b300a554d2cb…`;
* read on disk after the stage, no earlier recorded value (unchanged by construction — no edit of
  Stage 6B names them) — `ui/page_editors.py` `86bb917cb4ad…`, `ui/stations_page.py`
  `1ec293e99520…`, `ui/infrastructure_page.py` `e39a59ad0e8d…`, `ui/svg_render.py`
  `e3a287614f95…`, `ui/formatting.py` `fb3d32e688d2…`, `ui/project_page.py` `732c205c7ed2…`,
  `ui/editing.py` `918f16036736…`, `ui/preview_panel.py` `e8e5868d54d4…`,
  `ui/validation_page.py` `5631a4acfe8e…`, and the other test modules of Phases 1–5B.

The five protected artefacts and both companion files are unchanged as well:
`examples/GRR-01.json` `ad0a26265d4e…` (57,040 bytes, still `train_paths.paths == []` and
`rolling_stock.vehicles == []`), `docs/GRR-01_FROZEN_PHYSICAL_v1.0.json` `9348158d7b28…`,
`schema/project_schema_v1.0.json` `1a52b73b5587…` (still schema 1.0),
`example_project.json` `a36492095e34…`, `examples/GRR-01-paths.json` `c62c3ee6d910…` and
`examples/GRR-01-rolling-stock.json` `6b03e36f4f49…`; the canonical project hash is still
`5189aaa2340c17022666ef44772c7d34f99b2fea9ee9609bb7b7513238ef4dbe`.

**The notebook's own runtime outputs** in the workspace root — `app_snapshot.html` (written by the
launch cell; it now shows `APP v0.8.0`, `SCHEMA v1.0`, `Phase 6A — Rolling-Stock Model` and the
seven placeholder pages; `2463f556db12…`, 12,805,230 bytes), `result.txt`, the two runtime copies
of the reference documents the notebook writes for convenience (`example_project.json`,
byte-identical to the delivered file, and `GRR-01.json`, 57,039 bytes against the delivered file's
57,040, differing only by the trailing newline of that export's serialisation — and never the
delivered artefact) and one timestamped `self-check-line_prj-*.json` per suite run — remain
**by-products**, not deliverables: they are not part of the package, no document depends on them,
and the delivered tree is the Python package plus the documents listed above.

As in §7.3, §7.4 and §7.5, this sub-section (§7.6) is itself the record of the Stage-6A
adaptations, so its own post-write hash is quoted in the delivery note instead of in a table row;
`VERIFICATION.md` carries its own before/after values in §18.5 row 14 with the same convention.

### 7.7 Phase-6B (0.9.0) declared adaptations (recorded 2026-10-04)

Stage 6B delivers the read-only Rolling Stock page and the two small physics utilities it plots; the
`before` column is the state delivered with Phase 6A (§7.6), the `after` column is the delivered
Phase-6B tree. **Four files are new; twenty-two are changed; one is regenerated** (the notebook),
and every one of them is declared here. Unlike Stage 6A, **no `before` value had to be
reconstructed**: each one is quoted from §7.6 (or, for the two files Stage 6A did not touch, from
§7.5), and each was re-verified by hashing the value recorded there.

| File | SHA-256 (0.8.0 -> 0.9.0) | Reason |
|---|---|---|
| `railway_headway_sim/physics/tractive_effort.py` | (new file, 7,107 bytes) -> `e17ad1078274…` | **the Phase-6B effort primitive**: `tractive_effort_n` (the frozen simplified `FORCE_THEN_POWER_LIMITED` characteristic — `F_max * 1000` N at or below the transition speed `v_t = P * 1000 / (F_max * 1000)`, `P * 1000 / v` N above it), `transition_speed_kmh`, the three unit constants and the two private argument guards. Every unusable argument raises `ValueError` naming it; the standard library only (`{"__future__"}` is its whole import surface) |
| `railway_headway_sim/physics/rolling_stock_series.py` | (new file, 6,444 bytes) -> `7a33800d4d90…` | **the two Phase-6B series**: `tractive_effort_series_n(stock, step_kmh=10.0)` and `running_resistance_series_n(stock, step_kmh=10.0)` — `(speed_kmh, force_n)` tuples from 0.0 to the stock's own `max_speed_kmh` **inclusive**, the resistance series over the Stage-5A Davis primitive, bit-identical across calls; imports `..models.rolling_stock`, `.resistance` and `.tractive_effort` only |
| `railway_headway_sim/ui/rolling_stock_page.py` | (new file, 22,079 bytes) -> `a3bc013f1071…` | **the Phase-6B page**: four sub-tabs (Overview · Traction · Resistance · Braking), the stock selector, `rendered_text()`, `tractive_effort_series_n` / `running_resistance_series_n` and the two plot accessors. Read-only: no draft call, no editable `ipywidgets` class, no engineering computation of its own — stored fields and delivered series render through the existing `ui/svg_render.py` / `ui/formatting.py` |
| `railway_headway_sim/tests/test_phase6b_rolling_stock_ui.py` | (new file, 45,470 bytes) -> `f45166127447…` | `TEST P6-025 … TEST P6-048` (24 items), added only — the two primitives, their argument rules, the frozen pair's 117.6 km/h, the two series, the page and its two plots, read-only-ness, the Section-D scan, the hashes and the registration |
| `railway_headway_sim/physics/__init__.py` | `d3ff3d303dfd…` -> `c5ef15d98f9f…` | additive re-exports for the two Stage-6B modules and their constants plus one docstring paragraph; the Phase-5A/5B exports are byte-identical |
| `railway_headway_sim/ui/__init__.py` | `76068ff77fa2…` -> `a0ba5c0719b8…` | `Rolling Stock` added to `FUNCTIONAL_PAGES` (now five) and `RollingStockPage` exported |
| `railway_headway_sim/ui/placeholder_pages.py` | `49ef773fbfc5…` -> `033a91dbea17…` | the `Rolling Stock` entry removed from the planned catalogue (six entries remain); the placeholder text itself is unchanged |
| `railway_headway_sim/ui/app_shell.py` | `b9738a904e0d…` -> `3ecf0be1a27e…` | the page imported, constructed and added to the tab order, and the quick-guide bullet added; the header, direction buttons and other pages are untouched |
| `railway_headway_sim/version.py` | `d39dff0d1dc7…` -> `e21575cd0b69…` | 0.8.0 -> 0.9.0, `APP_PHASE` = `"Phase 6B — Rolling-Stock UI"`, docstring example; `SUPPORTED_PROJECT_SCHEMA_VERSIONS` stays `("1.0",)` — the single authority |
| `railway_headway_sim/tests/conftest.py` | `6d3a9c42f010…` -> `3690a0ee8375…` | the tenth table `PHASE-6B TESTS (TEST P6-025 ... TEST P6-048)` added and the Phase-6A table split at P6-024/025 (no row, title or verdict of the nine earlier tables changed) |
| `railway_headway_sim/tests/test_controller.py` | `770572db669c…` -> `01a6aa20bbf6…` | declared version-literal adaptation 0.8.0 -> 0.9.0; function name kept |
| `railway_headway_sim/tests/test_ui_shell.py` | `8499f2aa34b6…` -> `fe32dc86db1f…` | the same version re-point (`"APP v0.8.0"` -> `"APP v0.9.0"`) and the one declared supersession of this stage (`UI-REG-009`, exported to `VERIFICATION.md` §19.5) |
| `railway_headway_sim/tests/test_phase3_editors.py` | `f2fd6afe8c0c…` -> `6e8c486e8f37…` | `TEST P3-001` literal re-pointed 0.8.0 -> 0.9.0, including its "no other module carries the app version literal" scan; function name kept |
| `railway_headway_sim/tests/test_phase4a_route_coordinate.py` | `62ff85371936…` -> `2801eb0fbede…` | **`TEST P4-026`** version/phase literals re-pointed (`"Phase 6B" in label`, `"Phase 6A" not in label`, `"Phase 7" not in label`); every other Phase-4A row is byte-identical |
| `railway_headway_sim/tests/test_phase2_facade_and_app.py` | `9566984f8529…` -> `26824042c3b9…` | **declared adaptation A7** in `TEST P2-028`: the structural sets are compared against `NAVIGATION_TITLES` itself |
| `railway_headway_sim/tests/test_phase5a_resistance.py` | `1564c45d45f0…` -> `efc81bb6a7c4…` | **declared adaptations A8 + A9**: the physics-leaf assertion in `TEST P5-020` became the allow-list `{"ui/rolling_stock_page.py"}` (any other importer outside physics still fails), and `TEST P5-024`'s word map gained `"ten": 10` |
| `railway_headway_sim/tests/test_phase5b_along_route.py` | `d4a11cb33b38…` -> `fa2ac51e9dcb…` | **declared adaptation A10**: `TEST P5-042`'s word map gained `"ten": 10`; its structural decomposition checks are unchanged |
| `build_test_inventory.py` | `c34fe91a0fd3…` -> `380e066424e0…` | `phase6b` suite entry, the tenth suite's title/range, the canonical decomposition `… + 24 = 265`, the totals row "all ten suites", the allowed-count set and the printed decomposition |
| `build_colab_notebook.py` | `433073794552…` -> `29d990175b11…` | Phase-6B header (0.9.0) and phase text, the two physics modules and the page added to their sections, the Phase-6B test module to `tests`, the test-range and PASS strings, and the scope/usage sentences that had named the Rolling Stock page as a placeholder |
| `docs/SECTION_D_PATTERNS.md` | `084d82c43d6a…` -> `936cabddd75e…` | **declared adaptation D1**: §1's S4 row and §6's closing sentence now read six placeholder pages / five functional pages, with the S4 mechanism clause describing the two-way `PLANNED_PAGES` / `FUNCTIONAL_PAGES` check; no token list changed |
| `docs/TEST_INVENTORY.md` | `ebe89c0866d9…` -> `52f03633f52a…` | regenerated: ten suites, `66 + 30 + 5 + 26 + 30 + 18 + 24 + 18 + 24 + 24 = 265` collected items, ten acceptance rows; byte-identical on two consecutive runs |
| `README.md` | `2a279d9676d8…` -> `fc9b47411344…` | the Phase-6B section, the three new module rows, the layer-contract placeholder count and test ranges, version 0.9.0, the totals `… + 24 = 265`, the ten-table count and the navigation text |
| `VERIFICATION.md` | `54e54c948d03…` -> `6fef6007d360…` | §19 added (totals 241 -> 265, the protected and companion re-verifications, the new files, the frozen effort model, the declared adaptations A7-A10 + D1 + the `UI-REG-009` supersession + the §H re-points, the Section-D record, the J1-J6 observations, the scope statement) and three declared checker-forced re-layouts of the retired Phase-6A pass total inside §18; final value `6fef6007d360…`, 172,028 bytes |
| `docs/PHASE1_REGRESSION_MAP.md` | `53a078934037…` -> `af1cd475c428…` | the `UI-REG-009` row of §2 (both supersessions recorded) and the Phase-6B block of §3 with the four re-pointed version sites and the five further adaptations |
| `docs/GRR-01 CHANGE CONTROL.md` | `f113fc797b99…` -> `c1ea3e137fd9…` | §6 row recording **no GRR-01 data change** for Phase 6B, the byte-identical companion file and the unchanged canonical hash; no amendment entry added |
| `Railway_Track_Headway_Simulator_Phase1.ipynb` | 101,890,154 -> 102,286,700 bytes (`379e34984110…` -> `38335abeaf6e…`) | regenerated from the builder (106 cells: 91 code, 81 `%%writefile` payloads) and executed end to end: exit 0, **0 error outputs**, the ten acceptance tables with their verdicts and `265 passed`, header markdown `Application version 0.9.0`, the launch snapshot showing `APP v0.9.0` / `SCHEMA v1.0` and exactly the six remaining placeholder pages (Rolling Stock is functional and carries no badge), and all 81 payload bodies byte-identical to the files on disk |
| `docs/PHASE1_CHAIN_OF_CUSTODY.md` | `1fe66f92cc2f…` -> *(this sub-section §7.7; its own post-write hash is quoted in the run report, as §7.6's was)* | the Stage-6B before -> after ledger and the unchanged-files check |

**Checked and unchanged (hashes re-read on disk after the stage).** The already delivered physics
and infrastructure modules — `physics/resistance.py` `5f6ecb8fbd16…`, `physics/along_route.py`
`5db5ee340bf0…`, `infrastructure/compiled_network.py` `a3a26b2fa81f…`,
`infrastructure/geometry_along_route.py` `d29d2f0d64bc…` — the Phase-6A modules
(`models/rolling_stock.py` `2a905d7206d9…`, `validation/rolling_stock_validation.py`
`ed47ef225921…`, `validation/codes.py` `6339b4b353d9…`, `models/enums.py` `26124885a038…`), the
layout and viewer modules (`ui/table_editor.py` `d8ed65492282…`, `ui/schematic_page.py`
`d949089d49e8…`, `ui/page_editors.py`, `ui/stations_page.py`, `ui/infrastructure_page.py`,
`ui/svg_render.py`, `ui/formatting.py`), the runner (`tests/run_tests.py` `0275622ed38f…`), the
Phase-4B and Phase-5A/5B/6A test modules other than the three edited above, and
`railway_headway_sim/__init__.py` `1dc7a48425b0…` are all byte-identical to their Stage-6A values.
The five protected artefacts and both companion files are unchanged as well:
`examples/GRR-01.json` `ad0a26265d4e…` (57,040 bytes, still `train_paths.paths == []` and
`rolling_stock.vehicles == []`), `docs/GRR-01_FROZEN_PHYSICAL_v1.0.json` `9348158d7b28…`,
`schema/project_schema_v1.0.json` `1a52b73b5587…` (still schema 1.0),
`example_project.json` `a36492095e34…`, `examples/GRR-01-paths.json` `c62c3ee6d910…` and
`examples/GRR-01-rolling-stock.json` `6b03e36f4f49…`; the canonical project hash is still
`5189aaa2340c17022666ef44772c7d34f99b2fea9ee9609bb7b7513238ef4dbe`.

**The notebook's own runtime outputs** in the workspace root — `app_snapshot.html` (written by the
launch cell; it now shows `APP v0.9.0`, `SCHEMA v1.0`, `Phase 6B — Rolling-Stock UI` in the header
text and exactly six placeholder pages; `e870389364df…`,
12,972,882 bytes), `result.txt`, the two runtime copies of the reference documents
the notebook writes for convenience (`example_project.json`, byte-identical to the delivered file,
and `GRR-01.json`, 57,039 bytes against the delivered file's 57,040, differing only by the trailing
newline of that export's serialisation — and never the delivered artefact) and one timestamped
`self-check-line_prj-*.json` per suite run — remain **by-products**, not deliverables: they are not
part of the package, no document depends on them, and the delivered tree is the Python package plus
the documents listed above.

As in §7.3, §7.4, §7.5 and §7.6, this sub-section (§7.7) is itself the record of the Stage-6B
adaptations, so its own post-write hash is quoted in the run report instead of in a table row;
`VERIFICATION.md` carries the other files' before/after values in §19.5 with the same convention
for its own row (§19.9).
