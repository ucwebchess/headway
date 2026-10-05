# PHASE 3 — INFRASTRUCTURE UI SCOPE RECORD

**Application version 0.3.1 · Project schema version 1.0 (unchanged) · Google Colab**

This file is the Phase-3 scope record: it states what the infrastructure UI **is**, how an
edit becomes data, which values the UI is allowed to show, and what the UI explicitly does
**not** claim. It is written to be checkable against the delivered tree — every statement
names the module or the test that holds it.

---

## 1. Purpose

Phase 2 delivered typed physical-infrastructure catalogues, their validators and their
compiler. Maintaining that data therefore required hand-editing project JSON. Phase 3 adds
**validated, friendly editors** for those catalogues so ordinary work no longer needs a JSON
editor, while JSON import/export stays available and remains the authoritative interchange
format.

Two rules bound the whole phase:

1. **The document stays canonical.** An editor never writes to the loaded project: it stages a
   *draft* through the Phase-2 mechanism (`APP-EDIT-002`). Only `Commit` replaces the project,
   and only if the draft validates.
2. **The UI computes nothing.** Every engineering number shown in the UI is a stored value or
   a value the package produced (Phase-2 compiler / validator / static geometry, or
   `infrastructure/preview_series.py`). The single arithmetic expression the UI itself
   evaluates is the gradient between two adjacent stored elevation points.

---

## 2. Pages and sub-tabs

| Page | Sub-tabs | Contents |
|---|---|---|
| **Infrastructure** | **Line** | alignment catalogue; reference system (editable fields + schema-fixed fields shown read-only) |
| | **Tracks** | track groups, nodes, tracks (including the nested `chainage_map`); topology summary and the Phase-2 adjacency/sequence inspector |
| | **Geometry** | horizontal geometry sections; vertical profiles with their nested elevation points; synchronised elevation / gradient (‰) / stored-curvature previews |
| | **Speed** | speed-restriction table; effective-speed-per-direction preview |
| | **Schematic** | the auto-generated schematic, the layer control, the click surface and the validation strip |
| **Stations & Platforms** | **Stations** | station table |
| | **Platforms** | platform table |
| | **Stopping Marks** | stopping-mark table; static train-fit / rear-clearance checker |
| | **Observation Points** | observation-point table; local station schematic |

*Sub-tab titles are asserted by `TEST P3-020`; the state of the selected sub-tab is kept for
the session and survives a re-render. Switching sub-tabs never discards a staged draft
(`TEST P3-020`).*

The page roots keep the Phase-2 inspection contract: every attribute the Phase-2 acceptance
test reads (`_inventory`, `_overview`, `_nodes`, `_edges`, `_speed`, `_topology_summary`,
`_sequence_input`, `_sequence_result`, `_stations`, `_platforms`, `_marks`, `_footprints`,
`_observations`, …) still exists and still shows the frozen GRR-01 data (`TEST P3-021`).

---

## 3. How an edit becomes data

```
widget → TableEditor / ScopedEditor / ReferenceSystemEditor
       → InfrastructureEditor.stage_field / stage_entry / delete_entry
       → ProjectController.stage_draft(document, description)      (APP-EDIT-002)
       → validation of the draft document
       → STAGED result in the draft bar (code + reason + hash before/after)
       → Commit (only when VALID) → project replaced, draft cleared
       → Discard → draft dropped, canonical hash unchanged
```

* **Mutation goes through the live container.** `InfrastructureEditor.container()` returns the
  list the document actually stores, and nested edits are placed by chainage order. Editing a
  filtered *view* list would stage nothing — that defect was found and fixed with
  `TEST P3-010`.
* **Status is worded, never colour-only.** The draft bar prints `STAGED`, `COMMITTED` or
  `REJECTED`, the diagnostic code and the reason (`TEST P3-007`, `TEST P3-022`).
* **Hash discipline.** A staged draft never changes `current_project_hash`; `Discard` returns
  the canonical `5189aaa2340c1702…` hash of the delivered `examples/GRR-01.json`
  (`TEST P3-005`, `TEST P3-006`).
* **Invalid drafts block export.** `commit_draft()` rejects with `APP-EDIT-002` and
  `export_json()` returns `None` with `export_rejected` while an INVALID draft is staged
  (`TEST P3-007`, `TEST P3-023`).
* **Deletion is guarded.** Deleting an object that other objects reference is refused, and the
  refusal names the referencing objects — including the reference system when an alignment is
  referenced by `reference_system.alignment_id` (`TEST P3-008`, `TEST P3-009`).
* **Round-trip stays byte-stable.** Loaded-then-exported GRR-01 keeps the canonical hash, and
  an add-then-delete round trip returns to it exactly (`TEST P3-006`, `TEST P3-023`).

---

## 4. What the UI is allowed to show

| Category | Source | Marking |
|---|---|---|
| Stored field values | the document | **INPUT** |
| Reference-system values | the document | **INPUT** |
| Gradient between adjacent elevation points | `preview_series.gradient_segments()` (the UI's own arithmetic is limited to reviewing it) | **DERIVED** |
| Curvature series | stored horizontal-geometry radius/handedness via `preview_series.curvature_segments()` | **INPUT** |
| Effective speed per direction | `preview_series.effective_speed_segments()` over stored restrictions (most restrictive wins, filtered by direction) | **DERIVED** |
| Train fit / rear clearance | `infrastructure.static_geometry` through the controller (`static_footprint_rows`, `compute_static_footprint`) | **DERIVED** |
| Row badges, counts, focus targets | the validation result | **DERIVED** |

* Phase-2 objects are never given invented defaults: a field that is absent in the document is
  shown as absent, not as `0` (`TEST P3-005`, `TEST P3-021`).
* **Units** are part of every engineering column header (`km`, `m`, `km/h`, `‰`) and every
  field spec carries its unit (`TEST P3-002`).
* **Tooltips** come from one file only, `ui/field_help.py`; `missing_tooltips()` must be empty
  for the complete field list (`TEST P3-003`).
* **STANDARD / ADVANCED** is one shared mode object for every editor; ADVANCED only reveals
  optional columns and never adds, hides or changes data (`TEST P3-004`).
* **Direction** (`FORWARD` / `REVERSE`, with the terminal names as labels) is an application
  selection: it changes previews and drawing labels only. It never mutates stored data and
  never changes the hash (`TEST P3-012`).
* **No engineering calculation in the UI.** No UI module imports `math`, `numpy` or any
  numeric library; the pages and editors only call package functions
  (`TEST P3-024`). No function or class under `ui/` carries a dynamics name (the Phase-2
  Section-D token list) (`TEST P3-024`).

---

## 5. Schematic layer contract

| Layer | State | What is shown |
|---|---|---|
| Tracks | **ACTIVE** | track lanes with chainage span, node markers, endpoint labels |
| Stations | **ACTIVE** | station extents at their reference chainage |
| Platforms | **ACTIVE** | platform usable ranges over their track |
| Speed | **ACTIVE** | restriction bands with the stored speed |
| Signals | DISABLED | *no Phase-3 renderer* — the layer is listed, disabled and explained |
| TVPs/Resources | DISABLED | `resource_id` values are stored but not resolved |
| Routes | DISABLED | no Phase-3 renderer for `train_paths` |
| Simulation Occupancy | DISABLED | no simulation engine exists (out of scope) |

* The drawing is generated **from the canonical model**; every drawn element carries
  `data-object-id` and is registered as a hit target whose ids exist in the document
  (`TEST P3-017`).
* Disabled layers are visibly disabled and are **never drawn or faked** — forcing them on
  adds nothing to the drawing (`TEST P3-018`).
* Objects whose chainage cannot be resolved are drawn at the drawing origin with the explicit
  text *no resolvable chainage* rather than being silently dropped.
* ERROR objects are marked with the text `!` plus the diagnostic code, so colour is never the
  only status indicator (`TEST P3-019`).
* **Click-through**: the drawing is an `ipywidgets` `HTML` widget, which cannot send a click
  back to the kernel without a JavaScript model — a new dependency this phase does not take.
  The click surface is therefore an object list plus *Open in editor*, which switches to the
  owning sub-tab and focuses the row; the same routing is used by the validation strip and by
  the summary focus actions (`TEST P3-019`, `TEST P3-022`).

---

## 6. Validation surface inside the editors

* every editor row carries a severity badge (`VAL-…` code in words);
* the schematic marks error objects with `! <code>`;
* a summary counts errors / warnings / info grouped by **schema**, **geometry**, **topology**
  and **operations**, and offers the named objects as focus actions (`TEST P3-022`);
* **no new validation code exists**: every code the UI names is a Phase-1/Phase-2 code from
  `validation/codes.py`; genuinely new *editing* conditions are reported as INFO diagnostics
  with reused codes (`TEST P3-022`).

---

## 7. JSON import / export

Unchanged and authoritative: `import_json_upload` / `import_json_data` / `export_json` stay
on the **Project** page and on the **Infrastructure** page. An INVALID staged draft blocks
export (`APP-EDIT-002`); a loaded-then-exported `examples/GRR-01.json` preserves the canonical
hash (`TEST P3-023`).

---

## 8. Explicitly not claimed

* no train simulation, no train dynamics, no signalling, no blocking time, no headway, no
  capacity, no timetable — and no placeholder numbers for any of them;
* no rendered Signals / TVPs-Resources / Routes / Simulation-Occupancy layer;
* no resolved platform `resource_id`;
* no speed-resolution service: the effective-speed preview is a direction-filtered,
  most-restrictive-wins read of the stored restrictions;
* no mouse-click on the SVG (see §5);
* no new dependency: `pydantic>=2.5`, `ipywidgets>=8.0`, `pytest`
  (`nbformat`/`nbconvert`/`ipykernel` are used only to execute the notebook);
* no change to the Phase-2 field names, catalogue shapes, validator behaviour or the
  `PHASE-2 PHYSICAL INFRASTRUCTURE` / `BASIC PROJECT` / `(scope not determined)` scope values;
* no change to the protected artefacts: `examples/GRR-01.json` (`ad0a2626…`),
  `docs/GRR-01_FROZEN_PHYSICAL_v1.0.json` (`9348158d…`),
  `schema/project_schema_v1.0.json` (`1a52b73b…`) and `example_project.json` (`a3649209…`)
  are byte-identical to the Phase-2 delivery, and the canonical hash of the loaded GRR-01
  stays `5189aaa2340c1702…`;
* no Phase-4 work: the seven remaining pages still show exactly
  `PLANNED FOR LATER DEVELOPMENT PHASE`.

---

## 9. Files added by Phase 3

| File | Role |
|---|---|
| `railway_headway_sim/infrastructure/preview_series.py` | the only preview-series module (gradient, stored curvature, effective speed); pure reads of stored values |
| `railway_headway_sim/ui/field_help.py` | the single tooltip file |
| `railway_headway_sim/ui/editor_specs.py` | catalogue field definitions, identifiers, reference targets, mode columns |
| `railway_headway_sim/ui/editing.py` | the draft bridge: field/entry/delete staging, nested catalogues, reference system, refusal reporting |
| `railway_headway_sim/ui/svg_render.py` | embedded-SVG primitives (charts, legend) |
| `railway_headway_sim/ui/table_editor.py` | the table editor (unit headers, tooltips, badges, add/delete, provenance) |
| `railway_headway_sim/ui/preview_panel.py` | the preview panels built from `preview_series` |
| `railway_headway_sim/ui/schematic_render.py` | the schematic renderer and its hit targets |
| `railway_headway_sim/ui/schematic_page.py` | the schematic sub-tab (layer control, click surface) |
| `railway_headway_sim/ui/page_editors.py` | the per-sub-tab editor hosts, draft bar and validation summary |
| `railway_headway_sim/tests/test_phase3_editors.py` | `TEST P3-001 … TEST P3-026` |

Phase-3 changes to existing files are limited to: `version.py` (0.2.0 → 0.3.0, the single
authority; re-pointed 0.3.0 → 0.3.1 by the Phase-3 bugfix, `VERIFICATION.md` §13.8), `ui/infrastructure_page.py` and `ui/stations_page.py` (sub-tabs + editors, keeping
every Phase-2 attribute), `ui/app_shell.py` (the shared STANDARD/ADVANCED switch),
`app/project_controller.py` (one **added** method, `report_ui_message`; no signature changed),
`tests/conftest.py` (Phase-3 pass/fail table), `build_test_inventory.py` (Phase-3 suite), the
notebook builder and the documents.

---

## 10. Test map

| Test | Requirement covered |
|---|---|
| P3-001 | application version 0.3.1 lives in `version.py` only; the schema version stays 1.0 |
| P3-002 | every engineering column header carries the unit of its field |
| P3-003 | all tooltips come from `ui/field_help.py` (single source) |
| P3-004 | STANDARD/ADVANCED hides only optional columns and is shared by all editors |
| P3-005 | a staged edit leaves the committed project and the hash untouched |
| P3-006 | commit applies the draft; discard keeps the canonical hash |
| P3-007 | invalid edits reuse Phase-1/2 codes and block commit and export |
| P3-008 | rows can be added and deleted; a referenced row refuses deletion |
| P3-009 | the deletion refusal names the referencing objects, incl. the reference system |
| P3-010 | profile points are edited inside their owning profile, in chainage order |
| P3-011 | Line-level reference-system editing, with schema-fixed fields refused |
| P3-012 | gradient between adjacent points; FORWARD/REVERSE is display only |
| P3-013 | the curvature series carries the stored radius/handedness, nothing derived |
| P3-014 | effective speed per direction; the lowest limit wins |
| P3-015 | FIT / TOO_LONG / MARKER_OUTSIDE_USABLE classification |
| P3-016 | the checker shows the package result; the length is never stored |
| P3-017 | every drawn element exists in the loaded document |
| P3-018 | four layers render; the four others are visibly disabled |
| P3-019 | schematic selection routes to the owning editor row; errors carry text |
| P3-020 | the required sub-tabs exist and keep their state in the session |
| P3-021 | every Phase-2 page attribute still exists and shows the frozen data |
| P3-022 | row badges, category counts and focus actions; no new codes |
| P3-023 | export/import remain available and keep the canonical hash |
| P3-024 | the UI renders stored/package values; it computes no engineering value |
| P3-025 | no module imports a private name from `ipywidgets` (bugfix 0.3.1) |
| P3-026 | `close_widget_tree` releases a real widget tree through the public `Widget.close()` only (bugfix 0.3.1) |

Totals, decomposition and environment of record: `docs/TEST_INVENTORY.md` (generated by
`python3 build_test_inventory.py`), quoted verbatim by `README.md`, `VERIFICATION.md` and the
Colab notebook. `python3 build_test_inventory.py --check` fails if any document quotes a total
the inventory does not record.
