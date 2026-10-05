# PHASE 1 → PHASE 2 REGRESSION MAP

**Phase-1 baseline (frozen):** `Acceptance tests: 18/18 passed`
→ 66 tests, `PASS - all tests passed`, acceptance 18/18 (recorded in
`docs/PHASE1_VERIFICATION.md`, node IDs in section 4 below).

**Phase-2 requirement:** every accepted Phase-1 test must still pass **except the two
declared supersessions** listed in §2. Phase 2 additionally adds 28 numbered tests
(`P2-001` … `P2-028`) and 5 GRR-01 registry regressions (`P2-REG-G001` … `G005`).

## 1. Preserved Phase-1 behaviour (no change)

All other Phase-1 tests are preserved unchanged and still pass. In particular:

* package layering (UI → controller → model → validation/IO) and the module boundaries;
* `json.loads`-only import, no `eval`/`exec`/`pickle`, no class names from untrusted JSON;
* deterministic export, canonical SHA-256 (9-decimal float normalisation, signed zero),
  byte-stable `import → export → import → export`, timestamps never rewritten by a load;
* the structured diagnostics model (`Diagnostic` / `ValidationResult`) — Phase 2 adds a
  `scope` field and Phase-2 diagnostics to the *same* model, no duplicate result classes;
* `ProjectController` behaviour (project lifecycle, direction selection, hashes,
  modification tracking, export/import outcomes, listeners);
* the Colab shell (`launch_app(embed=...)`, FORWARD/REVERSE selector, static HTML
  fallback) and `project.id` as the stable machine key;
* schema defaults expand once (`VAL-FUTURE-001`), unknown fields survive round-trips.

### P1-013 … P1-018 — the six extra Phase-1 acceptance rows (Phase-2R, F5)

The Phase-1 acceptance table prints **18 rows** from the **12 mandatory IDs** `P1-001 …
P1-012`: a mandatory statement whose test is parametrised prints one row per asserted
instance. The six additional rows are labelled `P1-013 … P1-018` for reference. These labels
**name printed rows**; no test was added, removed or renamed in Phase-2R, and the labels do
not appear in the code.

| Row label | Printed row (collected item) | One-line reason |
|---|---|---|
| `P1-013` | `test_p1_002_export_import_roundtrip_preserves_data[example]` | The same mandatory roundtrip statement is asserted for the documented example project as well as for the new-project template. |
| `P1-014` | `test_p1_006_project_identity_is_required[blank-id]` | Blank-string `project.id` is a distinct rejection case from the empty string. |
| `P1-015` | `test_p1_006_project_identity_is_required[missing-id]` | Absent `project.id` key must be reported, not defaulted. |
| `P1-016` | `test_p1_006_project_identity_is_required[missing-name]` | Identity requires `project.name` too; the missing-name case is asserted separately. |
| `P1-017` | `test_p1_007_chainage_end_not_greater_than_start_is_invalid[10.0-5.0-reversed]` | A reversed range with a non-zero start is a distinct case from the 100→0 case. |
| `P1-018` | `test_p1_007_chainage_end_not_greater_than_start_is_invalid[0.0-0.0-equal]` | A zero-length range (`end == start`) must be rejected as well as a reversed one. |

Counts for this table are quoted from `docs/TEST_INVENTORY.md` (Phase-1 suite: 66 collected
items, 12 distinct acceptance IDs, 18 printed rows).

## 2. Declared supersessions (the only expectation changes)

| ID | Phase-1 test | Superseded expectation |
|---|---|---|
| VAL-REG-011 | tests/test_validation.py::test_duplicate_identifiers_are_reported_per_object_type | First assertion replaced: two typed engineering objects of *different* types may not share the same registered ID — the project is INVALID (`VAL-REGISTRY-001`, project-wide scope). The second assertion is unchanged: arbitrary nested extension data carrying an `id` is not a registered object and is not reported. The Phase-1 per-object-type duplicate check is kept for legacy (non-physical) projects only. |
| UI-REG-009 | tests/test_ui_shell.py::test_placeholder_pages_do_not_implement_engineering_calculations | **Phase 3:** Infrastructure and Stations & Platforms became functional pages (typed catalogues, registry, topology inspector, static footprint evaluation) and the remaining seven navigation entries stayed explicit `PLANNED FOR LATER DEVELOPMENT PHASE` placeholders with no calculations and no placeholder results. **Phase 6B (declared extension of this same supersession):** Rolling Stock is now a functional **read-only** page, so the hard-coded seven-entry list was replaced by a `PLANNED_PAGES`-driven check (six entries) plus a two-way disjointness check against `FUNCTIONAL_PAGES` (`FUNCTIONAL_PAGES` must be exactly the navigation titles minus the planned pages). The exact placeholder string, the no-calculation assertion and the "colour is never the only indicator" wording are byte-identical, and the test is not renamed — its collected node id is unchanged. Recorded in `VERIFICATION.md` §19.5. |

Both supersessions are visible in the code:

* `railway_headway_sim/validation/codes.py::PHASE1_TEST_ID_ALIASES` maps the prompt IDs to
  the real pytest names (`VAL-REG-011`, `UI-REG-009`);
* `railway_headway_sim/validation/__init__.py::phase2_identity_supersessions()` returns the
  Phase-1 nested object type (`station`) whose identity uniqueness the Phase-2 registry
  now owns for physical projects;
* `railway_headway_sim/ui/__init__.py::FUNCTIONAL_PAGES` lists the functional pages (five after
  Phase 6B), and `placeholder_pages.PLANNED_PAGES` lists exactly the six remaining placeholders.

## 3. Version-mandated adaptations (not supersessions, not weakenings)

| Phase-1 test | Why it had to change | How it changed |
|---|---|---|
| tests/test_controller.py (state/version assertion) | Phase 2 mandates app version 0.2.0 while schema_version stays 1.0. | The literal `"0.1.0"` assertion now reads the value from the single authoritative source (`railway_headway_sim.version.APP_VERSION`) *and* asserts `"0.2.0"` explicitly. The test's intent (the state reports the authoritative app version) is unchanged; no expectation was weakened. |
| tests/test_ui_shell.py::test_header_shows_versions_and_status_text | Same version bump. | `"APP v0.1.0"` now becomes `f"APP v{{APP_VERSION}}"` plus an explicit `"APP v0.2.0"` assertion; the header must still show the app version next to `SCHEMA v1.0`. |

Both edits keep the original intent (the UI/state must expose the *authoritative* version)
and additionally pin the new value, so the bump is asserted rather than accommodated.

**Phase 3 (same two tests, the same declaration).** Phase 3 bumps the application version
0.2.0 → 0.3.0 in `railway_headway_sim/version.py` only (the single authority) and leaves
`SUPPORTED_PROJECT_SCHEMA_VERSIONS` at `("1.0",)`. The two literal assertions declared above
therefore had to be re-pointed from `0.2.0` to `0.3.0`:

| Phase-1 test | Why it had to change | How it changed |
|---|---|---|
| tests/test_controller.py (state/version assertion) | The literal pinned in Phase 2 names the *current* application version, which Phase 3 bumps to 0.3.0. | The literal `"0.2.0"` became `"0.3.0"`; the assertion still reads the single authoritative source (`railway_headway_sim.version.APP_VERSION`) *and* pins the current value. No expectation was weakened, added or removed. |
| tests/test_ui_shell.py::test_header_shows_versions_and_status_text | Same version bump (the header must show the authoritative application version). | The literal `"APP v0.2.0"` became `"APP v0.3.0"`; `"SCHEMA v1.0"` and the status assertions are unchanged. |

Only these two literals were touched in Phase 3; no Phase-1 (or Phase-2) test was removed,
renamed, weakened or skipped, and Phase 3 added its own 24 tests (`TEST P3-001 … P3-024`) with
the same PASS/FAIL discipline. A related Phase-3 comment-only correction is recorded in
`docs/PHASE1_CHAIN_OF_CUSTODY.md` §7: the two comments that attributed the version bump to the
GRR-01 data amendment `GRR-AMD-003` now point at this section instead, because `GRR-AMD-003`
is the Delta line-end attachment in the GRR-01 change-control record and must stay a data
amendment.

## 4. Phase-1 test node IDs (baseline, 66)

```text
railway_headway_sim/tests/test_controller.py::test_p1_009_modify_after_validation_is_detected
railway_headway_sim/tests/test_controller.py::test_no_op_edit_does_not_invalidate_the_validation
railway_headway_sim/tests/test_controller.py::test_import_marks_project_as_validated_for_imported_content
railway_headway_sim/tests/test_controller.py::test_invalid_edit_is_rejected_with_a_message
railway_headway_sim/tests/test_controller.py::test_unknown_field_edit_is_rejected
railway_headway_sim/tests/test_controller.py::test_p1_010_direction_change_does_not_mutate_project_data
railway_headway_sim/tests/test_controller.py::test_direction_selection_rejects_reserved_values
railway_headway_sim/tests/test_controller.py::test_direction_state_guard_rejects_other_values
railway_headway_sim/tests/test_controller.py::test_new_project_provides_template_defaults
railway_headway_sim/tests/test_controller.py::test_import_failure_preserves_the_current_project
railway_headway_sim/tests/test_controller.py::test_import_of_invalid_but_usable_document_preserves_content
railway_headway_sim/tests/test_controller.py::test_no_file_selected_import_reports_precondition_error
railway_headway_sim/tests/test_controller.py::test_export_without_project_is_rejected_cleanly
railway_headway_sim/tests/test_controller.py::test_validate_without_project_is_reported_as_error
railway_headway_sim/tests/test_controller.py::test_subscribers_are_notified_and_can_unsubscribe
railway_headway_sim/tests/test_controller.py::test_export_uses_controller_directory_and_reports_outcome
railway_headway_sim/tests/test_controller.py::test_summary_and_state_rows_are_available_for_the_ui
railway_headway_sim/tests/test_project_io.py::test_p1_002_export_import_roundtrip_preserves_data[template]
railway_headway_sim/tests/test_project_io.py::test_p1_002_export_import_roundtrip_preserves_data[example]
railway_headway_sim/tests/test_project_io.py::test_roundtrip_through_files_and_helpers
railway_headway_sim/tests/test_project_io.py::test_p1_003_equivalent_project_produces_same_canonical_hash_after_roundtrip
railway_headway_sim/tests/test_project_io.py::test_export_metadata_is_opt_in_and_does_not_break_roundtrip
railway_headway_sim/tests/test_project_io.py::test_hash_is_order_independent_and_normalises_numbers
railway_headway_sim/tests/test_project_io.py::test_export_preserves_stored_numeric_values_and_types
railway_headway_sim/tests/test_project_io.py::test_export_document_shape_uses_canonical_section_order
railway_headway_sim/tests/test_project_io.py::test_export_filename_reflects_project_name_and_id
railway_headway_sim/tests/test_project_io.py::test_p1_011_imported_json_content_is_never_executed
railway_headway_sim/tests/test_project_io.py::test_import_helpers_do_not_use_unsafe_deserialization
railway_headway_sim/tests/test_project_io.py::test_upload_payload_shapes_are_supported
railway_headway_sim/tests/test_project_io.py::test_empty_upload_is_reported_as_application_error
railway_headway_sim/tests/test_ui_shell.py::test_shell_builds_all_navigation_pages
railway_headway_sim/tests/test_ui_shell.py::test_header_shows_versions_and_status_text
railway_headway_sim/tests/test_ui_shell.py::test_direction_buttons_drive_the_controller_and_labels
railway_headway_sim/tests/test_ui_shell.py::test_project_page_edits_are_written_through_the_controller
railway_headway_sim/tests/test_ui_shell.py::test_project_page_reimport_updates_every_widget
railway_headway_sim/tests/test_ui_shell.py::test_audit_page_renders_and_filters_diagnostics
railway_headway_sim/tests/test_ui_shell.py::test_placeholder_pages_do_not_implement_engineering_calculations
railway_headway_sim/tests/test_ui_shell.py::test_launch_app_builds_and_can_write_a_static_snapshot
railway_headway_sim/tests/test_ui_shell.py::test_controller_listeners_refresh_the_shell_without_manual_calls
railway_headway_sim/tests/test_validation.py::test_p1_001_new_project_is_valid
railway_headway_sim/tests/test_validation.py::test_documented_example_project_is_valid
railway_headway_sim/tests/test_validation.py::test_p1_004_missing_schema_version_is_invalid
railway_headway_sim/tests/test_validation.py::test_p1_005_unsupported_schema_version_is_invalid
railway_headway_sim/tests/test_validation.py::test_schema_version_of_wrong_type_is_invalid
railway_headway_sim/tests/test_validation.py::test_p1_006_project_identity_is_required[empty-id]
railway_headway_sim/tests/test_validation.py::test_p1_006_project_identity_is_required[blank-id]
railway_headway_sim/tests/test_validation.py::test_p1_006_project_identity_is_required[missing-id]
railway_headway_sim/tests/test_validation.py::test_p1_006_project_identity_is_required[missing-name]
railway_headway_sim/tests/test_validation.py::test_p1_007_chainage_end_not_greater_than_start_is_invalid[100.0-0.0-reversed]
railway_headway_sim/tests/test_validation.py::test_p1_007_chainage_end_not_greater_than_start_is_invalid[10.0-5.0-reversed]
railway_headway_sim/tests/test_validation.py::test_p1_007_chainage_end_not_greater_than_start_is_invalid[0.0-0.0-equal]
railway_headway_sim/tests/test_validation.py::test_chainage_bounds_are_accepted_when_increasing
railway_headway_sim/tests/test_validation.py::test_p1_008_invalid_direction_enumeration_is_invalid
railway_headway_sim/tests/test_validation.py::test_missing_direction_is_invalid
railway_headway_sim/tests/test_validation.py::test_identical_forward_and_reverse_direction_warns
railway_headway_sim/tests/test_validation.py::test_p1_012_diagnostics_have_stable_structure
railway_headway_sim/tests/test_validation.py::test_malformed_field_type_is_reported_once_and_not_repaired_silently
railway_headway_sim/tests/test_validation.py::test_missing_container_is_created_with_default_and_info
railway_headway_sim/tests/test_validation.py::test_malformed_container_is_reported_and_defaulted
railway_headway_sim/tests/test_validation.py::test_duplicate_identifiers_are_reported_per_object_type
railway_headway_sim/tests/test_validation.py::test_non_object_root_is_reported
railway_headway_sim/tests/test_validation.py::test_unparseable_json_text_is_reported
railway_headway_sim/tests/test_validation.py::test_undecodable_upload_bytes_are_reported
railway_headway_sim/tests/test_validation.py::test_display_unit_warning_is_not_an_error
railway_headway_sim/tests/test_validation.py::test_preserved_containers_get_info_only
railway_headway_sim/tests/test_validation.py::test_extra_unknown_fields_are_preserved
```

**Bugfix 0.3.1 (same declaration, and the Phase-3 suite pins the same literal).** The
`ipywidgets` public-API bugfix bumps the application version 0.3.0 → 0.3.1 in
`railway_headway_sim/version.py` only (the single authority) and leaves
`SUPPORTED_PROJECT_SCHEMA_VERSIONS` at `("1.0",)`. The two literals declared above were
re-pointed from `0.3.0` to `0.3.1`:

| Phase-1 test | Why it had to change | How it changed |
|---|---|---|
| tests/test_controller.py (state/version assertion) | The literal names the *current* application version, which the bugfix bumps to 0.3.1. | The literal `"0.3.0"` became `"0.3.1"`; the assertion still reads the single authoritative source *and* pins the current value. No expectation was weakened, added or removed. |
| tests/test_ui_shell.py::test_header_shows_versions_and_status_text | Same version bump (the header must show the authoritative application version). | The literal `"APP v0.3.0"` became `"APP v0.3.1"`; `"SCHEMA v1.0"` and the status assertions are unchanged. |

The Phase-3 suite pins the same current value in
`railway_headway_sim/tests/test_phase3_editors.py::TEST P3-001` (`APP_VERSION`,
`get_app_version()`, the controller state, and the scan that proves the literal appears nowhere
else in the package). It was re-pointed `0.3.0` → `0.3.1` in exactly the same way. The test
function keeps its original name: renaming it would change the collected node id, and this
project does not rename delivered tests. No test was removed, renamed, weakened or skipped; the
bugfix *added* `TEST P3-025` and `TEST P3-026`, so the Phase-3 suite is 26 collected items and
the four suites total `66 + 30 + 5 + 26 = 127`.

**Phase 4A (same declaration; a new engineering phase, not a bugfix).** Phase 4A adds the
compiled network and the route-coordinate system and bumps the application version
`0.3.1` → `0.4.0` in `railway_headway_sim/version.py` only (the single authority);
`SUPPORTED_PROJECT_SCHEMA_VERSIONS` and `DEFAULT_PROJECT_SCHEMA_VERSION` stay `("1.0",)`. The
same three sites were re-pointed `0.3.1` → `0.4.0`, with no change of expectation:

| Site | Why it had to change | How it changed |
|---|---|---|
| `tests/test_controller.py` (state/version assertion) | The literal names the *current* application version, which Phase 4A bumps to 0.4.0. | The literal `"0.3.1"` became `"0.4.0"`; the assertion still reads the single authoritative source *and* pins the current value. The historical comment above it now records both bumps. No expectation was weakened, added or removed. |
| `tests/test_ui_shell.py::test_header_shows_versions_and_status_text` | Same version bump (the header must show the authoritative application version). | The literal `"APP v0.3.1"` became `"APP v0.4.0"`; `"SCHEMA v1.0"` and the status assertions are unchanged. |
| `tests/test_phase3_editors.py::TEST P3-001` | The Phase-3 suite pins the same current value (`APP_VERSION`, `get_app_version()`, the controller state, and the scan proving the literal appears nowhere else in the package). | Re-pointed `0.3.1` → `0.4.0` in exactly the same way, **without renaming the function** (a rename would change the collected node id, which this project does not do to delivered tests). |

Two further, equally mechanical adaptations were required by the *checkers* rather than by the
version bump, and are declared here for the same reason as the literals above:

| Adaptation | Why it had to change | How it changed |
|---|---|---|
| `tests/conftest.py` — acceptance-id matcher and the fifth PASS/FAIL table | The runner prints one table per suite; without the `P4-\d{3}` alternative the new suite would print no table at all. | The regex alternative `\bP4-\d{3}\b` and the table title `PHASE-4A TESTS (TEST P4-001 ... TEST P4-022)` were added. No existing alternative, table or row was altered. |
| `build_test_inventory.py` — the Phase-4A suite entry; `docs/TEST_INVENTORY.md` regenerated | The inventory is the single source of truth for every quoted test total and must know the new suite. | A `phase4a` suite (title `Phase-4A suite (TEST P4-001 … TEST P4-022)`, module `test_phase4a_route_coordinate.py`) was added to `SUITES`, to the allowed-count set and to the decomposition line; the inventory was regenerated. The four existing suites and their tables are unchanged, and the totals become `66 + 30 + 5 + 26 + 22 = 149`. |

**Correction 0.4.1 (same declaration, patch release).** The Phase-4A correction adds the
declared-paths companion file `examples/GRR-01-paths.json` (the frozen project still declares
`train_paths.paths == []`), renames the Phase-4A **test-internal** paths to
`TEST-CORRIDOR-A-D` / `TEST-CORRIDOR-D-A` (the names `PATH-H1-F` / `PATH-H1-R` are reserved for
the companion file) and corrects the user-visible `APP_PHASE` label, which bumps the
application version `0.4.0` → `0.4.1` in `railway_headway_sim/version.py` only (the single
authority). The three sites that pin the *current* version were re-pointed in exactly the same
way, with no change of expectation and **no test renamed**:

| Site | Why it had to change | How it changed |
|---|---|---|
| `tests/test_controller.py` (state/version assertion) | The literal names the *current* application version, which this release bumps to 0.4.1. | The literal `"0.4.0"` became `"0.4.1"`; the assertion still reads the single authoritative source *and* pins the current value, and the historical comment above it now records all three bumps. |
| `tests/test_ui_shell.py::test_header_shows_versions_and_status_text` | Same version bump (the header must show the authoritative application version). | The literal `"APP v0.4.0"` became `"APP v0.4.1"`; `"SCHEMA v1.0"` and the status assertions are unchanged. |
| `tests/test_phase3_editors.py::TEST P3-001` | The Phase-3 suite pins the same current value. | Re-pointed `0.4.0` → `0.4.1` in the same way, without renaming the function (a rename would change the collected node id). |

Two further mechanical adaptations belong to this correction and are declared for the same
reason:

| Adaptation | Why it had to change | How it changed |
|---|---|---|
| `infrastructure/compiled_network.py` — the declared-paths reader gained stdlib `json` and `pathlib`; the import-surface assertion in `TEST P4-022` was extended to those two names | The companion file must be readable as a mapping, as JSON text or as a file path (C1.5), which needs those stdlib modules; the guard test asserts the module's exact import surface, so it had to list them. | Additive: no numeric library, no dependency and no validation-facade import was added, and the guard's remaining clauses are unchanged. |
| `tests/conftest.py`, `build_test_inventory.py`, `build_colab_notebook.py` — the Phase-4A range `P4-001 … P4-022` → `P4-001 … P4-026`; the notebook gained a declared-paths companion write cell | Four acceptance tests were added (`TEST P4-023 … TEST P4-026`) and the notebook must write the companion file into the runtime. | Additive only: no existing table, row, range or cell wording changed beyond the range end, and the inventory regenerates to `66 + 30 + 5 + 26 + 26 = 153`. |

**Correction 0.4.2 (same declaration, patch release).** The Phase-4A corridor correction
rewrites the declared-paths companion file `examples/GRR-01-paths.json` so that `PATH-H1-F` and
`PATH-H1-R` are the two running orders of one physical corridor (the same 14 edge entries, in
reverse order, with the complementary traversal, the same 47 400.0 m and the same terminal pair,
swapped), which bumps the application version `0.4.1` -> `0.4.2` in
`railway_headway_sim/version.py` only (the single authority). The three sites that pin the
*current* version were re-pointed in exactly the same way, with no change of expectation and
**no test renamed**:

| Site | Why it had to change | How it changed |
|---|---|---|
| `tests/test_controller.py` (state/version assertion) | The literal names the *current* application version, which this release bumps to 0.4.2. | The literal `"0.4.1"` became `"0.4.2"`; the assertion still reads the single authoritative source *and* pins the current value, and the historical comment above it now records all four bumps. |
| `tests/test_ui_shell.py::test_header_shows_versions_and_status_text` | Same version bump (the header must show the authoritative application version). | The literal `"APP v0.4.1"` became `"APP v0.4.2"`; `"SCHEMA v1.0"` and the status assertions are unchanged. |
| `tests/test_phase3_editors.py::TEST P3-001` | The Phase-3 suite pins the same current value. | Re-pointed `0.4.1` -> `0.4.2` in the same way, without renaming the function (a rename would change the collected node id). |

Three further mechanical adaptations belong to this correction and are declared for the same
reason:

| Adaptation | Why it had to change | How it changed |
|---|---|---|
| `railway_headway_sim/tests/test_phase4a_route_coordinate.py` — `TEST P4-024` assertion strings | Three of its expectations pinned the superseded 0.4.1 corridor: the reverse terminus on the Alpha **P1** platform edge, the clause that each path "must run through Central P2", and the equality of the reverse walk with the test corridor's 49 000.0 m. | Re-pointed to the corrected data: the reverse terminus is the Alpha **P2** platform edge (the forward origin edge), both paths must pass a Central station platform edge (read from the project's own platform set), and the two paths must share one route length distinct from the test corridor's. The function name, the row and the remaining assertions are unchanged, and the test cross-checks the compiled values against the companion record. |
| `railway_headway_sim/tests/test_phase4a_route_coordinate.py` — `TEST P4-026` and the Phase-4A range label | `TEST P4-026` pins the current application version; four new acceptance tests (`TEST P4-027 … TEST P4-030`) extend the suite. | The two version literals became `0.4.2`; the range label became `TEST P4-001 … TEST P4-030` in `tests/conftest.py`, `build_test_inventory.py` and `build_colab_notebook.py`. Additive only; `TEST P4-001 … TEST P4-023` and `TEST P4-025` are untouched. |
| `examples/GRR-01-paths.json`, `build_colab_notebook.py` (embedded companion text and header version) and `docs/TEST_INVENTORY.md` | The companion file is rewritten, so the notebook must embed and write the corrected text; the inventory follows the collected items. | The file is regenerated by the deterministic rule stated in its own `notes`; the notebook is rebuilt and re-executed; the inventory regenerates to `66 + 30 + 5 + 26 + 30 = 157`. |

**Phase 4B 0.4.2 -> 0.5.0 (minor release, same declaration).** Phase 4B delivers the geometry
along a compiled route as a new module and bumps the application version `0.4.2` -> `0.5.0` in
`railway_headway_sim/version.py` only (the single authority), where `APP_PHASE` now names
`Phase 4B — Geometry Along Route`. A minor bump (not a patch) is correct here: a new
engineering surface is added. The three sites that pin the *current* version were re-pointed in
exactly the same way, with no change of expectation and **no test renamed**:

| Site | Why it had to change | How it changed |
|---|---|---|
| `tests/test_controller.py` (state/version assertion) | The literal names the *current* application version, which this release bumps to 0.5.0. | The literal `"0.4.2"` became `"0.5.0"`; the assertion still reads the single authoritative source *and* pins the current value, and the historical comment above it now records all five bumps. |
| `tests/test_ui_shell.py::test_header_shows_versions_and_status_text` | Same version bump (the header must show the authoritative application version). | The literal `"APP v0.4.2"` became `"APP v0.5.0"`; `"SCHEMA v1.0"` and the status assertions are unchanged. |
| `tests/test_phase3_editors.py::TEST P3-001` | The Phase-3 suite pins the same current value. | Re-pointed `0.4.2` -> `0.5.0` in the same way, without renaming the function (a rename would change the collected node id). |

Two further mechanical adaptations belong to this stage and are declared for the same reason:

| Adaptation | Why it had to change | How it changed |
|---|---|---|
| `tests/test_phase4a_route_coordinate.py` — `TEST P4-026`'s version and phase literals | The test asserts that `APP_PHASE` names the *current* phase and matches `APP_VERSION`, so it had to follow the bump. | `0.4.2` -> `0.5.0`, `"APP v0.4.2"` -> `"APP v0.5.0"`; the phase expectation `"Phase 4A" in label` became `"Phase 4B" in label`, `"Phase 3" not in label` became `"Phase 4A" not in label` (the previous phase) and the guard `"4B" not in label` became `"Phase 5" not in label` (a phase the project has not reached). The function name, its row and its remaining assertions are unchanged. |
| `railway_headway_sim/tests/conftest.py`, `build_test_inventory.py`, `build_colab_notebook.py` | The Phase-4B suite must be registered and counted. | A sixth PASS/FAIL table `PHASE-4B TESTS (TEST P4-031 ... TEST P4-048)` beside the five existing ones (whose titles and rows are unchanged), a `phase4b` suite entry with its own module and the canonical decomposition `66 + 30 + 5 + 26 + 30 + 18 = 175`, and the notebook's embedded header/module lists. Additive only. |

**Phase 5A 0.5.0 -> 0.6.0 (minor release, same declaration).** Stage 5A delivers the resistance
and force utilities that precede any train motion and bumps the application version `0.5.0` ->
`0.6.0` in `railway_headway_sim/version.py` only (the single authority), where `APP_PHASE` now
names `Phase 5A — Resistance and Force Utilities`. A minor bump (not a patch) is correct: a new
engineering surface is added. The three sites that pin the *current* version were re-pointed in
exactly the same way, with no change of expectation and **no test renamed**:

| Site | Why it had to change | How it changed |
|---|---|---|
| `tests/test_controller.py` (state/version assertion) | The literal names the *current* application version, which this release bumps to 0.6.0. | The literal `"0.5.0"` became `"0.6.0"`; the assertion still reads the single authoritative source *and* pins the current value, and the historical comment above it now records the full chain of bumps since 0.1.0. |
| `tests/test_ui_shell.py::test_header_shows_versions_and_status_text` | Same version bump (the header must show the authoritative application version). | The literal `"APP v0.5.0"` became `"APP v0.6.0"`; `"SCHEMA v1.0"` and the status assertions are unchanged. |
| `tests/test_phase3_editors.py::TEST P3-001` | The Phase-3 suite pins the same current value. | Re-pointed `0.5.0` -> `0.6.0` in the same way (including its "no other module carries the app version literal" scan), without renaming the function (a rename would change the collected node id). |

Four further mechanical adaptations belong to this stage and are declared for the same reason:

| Adaptation | Why it had to change | How it changed |
|---|---|---|
| `tests/test_phase4a_route_coordinate.py` — `TEST P4-026`'s version and phase literals | The test asserts that `APP_PHASE` names the *current* phase and matches `APP_VERSION`, so it had to follow the bump. | `0.5.0` -> `0.6.0`, `"APP v0.5.0"` -> `"APP v0.6.0"`; the phase expectation `"Phase 4B" in label` became `"Phase 5A" in label`, `"Phase 4A" not in label` became `"Phase 4B" not in label` (the previous phase) and the guard `"Phase 5" not in label` became `"Phase 5B" not in label` (a sub-phase the project has not reached). The function name, its row and its remaining assertions are unchanged. |
| `docs/SECTION_D_PATTERNS.md` §2 / §2.1 (the Section-D forbidden list) | Stage 5A's scope includes the Davis resistance, the Roeckl curve resistance and the gradient force, so the five tokens `Davis`, `Roeckl`, `rolling resistance`, `curve resistance` and `gradient force` moved from the forbidden lists to a new allowed list (one rationale per token, §2.1), and the S1 list went from 11 to 9 tokens. | §2's before text `` `headway`, `blocking_time`, `occupation_time`, `residual_occupancy`, `speed_envelope`, `traction`, `davis`, `roeckl`, `braking_curve`, `monte_carlo`, `uic406` `` became the nine-token list without `davis`/`roeckl`, followed by the new §2.1 `` `Davis`, `Roeckl`, `rolling resistance`, `curve resistance`, `gradient force` ``. The §1 S1 row, the two §5 concept rows and the §6 guarantee paragraph were extended to point at §2.1. No other token was moved, removed or weakened and no scan surface was removed. |
| `tests/test_phase2_facade_and_app.py` (TEST P2-028), `tests/test_phase4a_route_coordinate.py` (TEST P4-021), `tests/test_phase4b_geometry_along_route.py` (TEST P4-047) — the scan surfaces that read the list | The list itself changed, and §F8 requires that the update assert the allowed list explicitly instead of merely no longer failing. | P2-028's forbidden list went 11 -> 9 tokens and gained an allowed-surface assertion (any declared name carrying one of the five tokens must live in `railway_headway_sim/physics/resistance.py`); P4-021 and P4-047 moved their S1 length expectation 11 -> 9 and read §2.1, asserting the five tokens are on the allowed list and absent from the forbidden one. P3-024 (the UI surface) is unchanged: the UI must still carry no engineering computation at all. |
| `railway_headway_sim/tests/conftest.py`, `build_test_inventory.py`, `build_colab_notebook.py` | The Phase-5A suite must be registered, counted and inlined. | A seventh PASS/FAIL table `PHASE-5A TESTS (TEST P5-001 ... TEST P5-024)` beside the six existing ones (whose titles and rows are unchanged), a `phase5a` suite entry with its own module and the canonical decomposition `66 + 30 + 5 + 26 + 30 + 18 + 24 = 199`, a `physics` section in the notebook (plus the folder in the setup cell) and the Phase-5A header/module/range text. Additive only. |

**Four declared re-points inside `VERIFICATION.md` §1/§2 (checker-forced).** The quoted-total
checker (`python3 build_test_inventory.py --check`) rejects any pass total in README,
VERIFICATION and the notebook that is not a current inventory total, and §1/§2 quote the
*historical* four-suite run of the Phase-3/0.3.1 record. The four affected lines were re-pointed
by the house convention already used for the canonical decomposition string (a historical total
is written between backticks, so it is recorded without being re-asserted): the two quoted run
summaries, the quoted four-suite decomposition string, and the policy sentence that called the
historical total "current". No number was changed, no table row was added, and no other text in
§1–§13 was touched.

**Phase 5B 0.6.0 -> 0.7.0 (minor release, same declaration).** Stage 5B delivers the resistance
utilities *along a compiled route* — one new module (`railway_headway_sim/physics/along_route.py`)
plus one additive, purely geometric method on `RouteGeometry`
(`curve_radius_segments_in`) — and bumps the application version `0.6.0` -> `0.7.0` in
`railway_headway_sim/version.py` only (the single authority), where `APP_PHASE` now names
`Phase 5B — Along-Route Resistance`. A minor bump (not a patch) is correct: a new engineering
surface is added, and no stored key, validation rule or existing public interface changes. The
three sites that pin the *current* version were re-pointed in exactly the same way, with no
change of expectation and **no test renamed**:

| Site | Why it had to change | How it changed |
|---|---|---|
| `tests/test_controller.py` (state/version assertion) | The literal names the *current* application version, which this release bumps to 0.7.0. | The literal `"0.6.0"` became `"0.7.0"`; the assertion still reads the single authoritative source *and* pins the current value, and the historical comment above it now records the full chain of bumps since 0.1.0. |
| `tests/test_ui_shell.py::test_header_shows_versions_and_status_text` | Same version bump (the header must show the authoritative application version). | The literal `"APP v0.6.0"` became `"APP v0.7.0"`; `"SCHEMA v1.0"` and the status assertions are unchanged. |
| `tests/test_phase3_editors.py::TEST P3-001` | The Phase-3 suite pins the same current value. | Re-pointed `0.6.0` -> `0.7.0` in the same way (including its "no other module carries the app version literal" scan), without renaming the function (a rename would change the collected node id). |

Four further mechanical adaptations belong to this stage and are declared for the same reason:

| Adaptation | Why it had to change | How it changed |
|---|---|---|
| `tests/test_phase4a_route_coordinate.py` — `TEST P4-026`'s version and phase literals | The test asserts that `APP_PHASE` names the *current* phase and matches `APP_VERSION`, so it had to follow the bump. | `0.6.0` -> `0.7.0`, `"APP v0.6.0"` -> `"APP v0.7.0"`; the phase expectation `"Phase 5A" in label` became `"Phase 5B" in label`, `"Phase 4B" not in label` became `"Phase 5A" not in label` (the previous phase) and the guard `"Phase 5B" not in label` became `"Phase 6" not in label` (a phase the project has not reached). The function name, its row and its remaining assertions are unchanged. |
| `railway_headway_sim/tests/conftest.py`, `build_test_inventory.py`, `build_colab_notebook.py` | The Phase-5B suite must be registered, counted and inlined. | An eighth PASS/FAIL table `PHASE-5B TESTS (TEST P5-025 ... TEST P5-042)` beside the seven existing ones (whose titles and rows are unchanged), a `phase5b` suite entry with its own module, the canonical decomposition `66 + 30 + 5 + 26 + 30 + 18 + 24 + 18 = 217`, the totals row "all eight suites", the new module in the `physics` section of the notebook (plus `tests/test_phase5b_along_route.py`) and the Phase-5B header/module/range text. Additive only. |
| `railway_headway_sim/tests/test_phase5a_resistance.py` (TEST P5-020, TEST P5-023, TEST P5-024) and `tests/test_phase2_facade_and_app.py` (TEST P2-028); `docs/SECTION_D_PATTERNS.md` §2/§2.1 | Stage 5B adds a second module to the `physics` package, so the *surface* on which the five Stage-5A tokens may appear, the package's whole-`__all__` pin and two literal pins of the generated inventory text could not survive a later stage. | The five authorised adaptations A1–A5: the allowed surface is the `railway_headway_sim/physics/` package instead of the single module (A1, A2, A5), the package-export pin became an exact containment of the Phase-5A exports (A3), and the two inventory literals became the same two facts checked structurally (A4). No token moved, no forbidden list changed (S1 9, S2 14, S3 7, allowed 5), no tolerance was loosened and no other assertion of those tests changed. Every one is recorded with its before/after text in `VERIFICATION.md` §17 and with the file hashes in `docs/PHASE1_CHAIN_OF_CUSTODY.md` §7.5. |
| `VERIFICATION.md` §16 (two run rows) | The quoted-total checker accepts only the totals the generated inventory records, and §16’s run rows quote the Phase-5A pass total. | The two rows were re-laid out so the number is recorded without being re-asserted (`**199 passed**` -> `` `199` passed ``); the values and every other word are unchanged (checker-forced, declared in `VERIFICATION.md` §17). |

**Phase 6A 0.7.0 -> 0.8.0 (minor release, same declaration).** Stage 6A delivers the typed
rolling-stock *catalogue* — one new model module
(`railway_headway_sim/models/rolling_stock.py`), one new validation module
(`railway_headway_sim/validation/rolling_stock_validation.py`), the reference companion file
`examples/GRR-01-rolling-stock.json` and the Phase-6A suite — and bumps the application version
`0.7.0` -> `0.8.0` in `railway_headway_sim/version.py` only (the single authority), where
`APP_PHASE` now names `Phase 6A — Rolling-Stock Model`. A minor bump (not a patch) is correct: a
new engineering surface is added, and no stored key, validation rule or existing public
interface changes. The project schema stays `("1.0",)` and the frozen project is untouched (the
rolling stock is a companion document of its own `document_kind`, not a project key). Three
sites that pin the *current* version were re-pointed in exactly the same way, with no change of
expectation and **no test renamed**:

| Site | Why it had to change | How it changed |
|---|---|---|
| `tests/test_controller.py` (state/version assertion) | The literal names the *current* application version, which this release bumps to 0.8.0. | The literal `"0.7.0"` became `"0.8.0"`; the assertion still reads the single authoritative source *and* pins the current value, and the historical comment above it now records the full chain of bumps since 0.1.0. |
| `tests/test_ui_shell.py::test_header_shows_versions_and_status_text` | Same version bump (the header must show the authoritative application version). | The literal `"APP v0.7.0"` became `"APP v0.8.0"`; `"SCHEMA v1.0"` and the status assertions are unchanged. |
| `tests/test_phase3_editors.py::TEST P3-001` | The Phase-3 suite pins the same current value. | Re-pointed `0.7.0` -> `0.8.0` in the same way (including its "no other module carries the app version literal" scan), without renaming the function (a rename would change the collected node id). |

Four further mechanical adaptations belong to this stage and are declared for the same reason:

| Adaptation | Why it had to change | How it changed |
|---|---|---|
| `tests/test_phase4a_route_coordinate.py` — `TEST P4-026`'s version and phase literals | The test asserts that `APP_PHASE` names the *current* phase and matches `APP_VERSION`, so it had to follow the bump. | `0.7.0` -> `0.8.0`, `"APP v0.7.0"` -> `"APP v0.8.0"`; the phase expectation `"Phase 5B" in label` became `"Phase 6A" in label`, `"Phase 5A" not in label` became `"Phase 5B" not in label` (the previous phase) and the guard `"Phase 6" not in label` became `"Phase 6B" not in label` (the *next* stage, not started — the bare `"Phase 6"` guard could not survive a Stage-6A label). The function name, its row and its remaining assertions are unchanged. |
| `railway_headway_sim/tests/conftest.py`, `build_test_inventory.py`, `build_colab_notebook.py` | The Phase-6A suite must be registered, counted and inlined. | A ninth PASS/FAIL table `PHASE-6A TESTS (TEST P6-001 ... TEST P6-024)` beside the eight existing ones (whose titles and rows are unchanged), a `phase6a` suite entry with its own module, the canonical decomposition `66 + 30 + 5 + 26 + 30 + 18 + 24 + 18 + 24 = 241`, the totals row "all nine suites", the new model/validation modules and the rolling-stock companion in the notebook's section cells (plus `tests/test_phase6a_rolling_stock_model.py`) and the Phase-6A header/module/range/scope text. Additive only. |
| `VERIFICATION.md` §17 J1 row | The quoted-total checker accepts only the totals the generated inventory records, and §17's J1 row quotes the Phase-5B pass total. | The row was re-laid out so the number is recorded without being re-asserted (the digits moved into their own code span, the word "passed" no longer directly after them); the value and every other word are unchanged (checker-forced, declared in `VERIFICATION.md` §18.1). |
| `railway_headway_sim/models/rolling_stock.py` and `railway_headway_sim/validation/rolling_stock_validation.py` — declared names | The Section-D scan forbids the tokens `Davis` and `traction` in any *declared* name outside `railway_headway_sim/physics/`, and the stage brief's own class and property names carry them. | Plain-language declared names were used from the start (`RollingStockTractiveEffort`, `TractiveEffortModel`, `RollingStockTractiveEffortPoint`, `RollingStockRunningResistanceCoefficients`, `resistance_a_kn` / `resistance_b_kn_per_kmh` / `resistance_c_kn_per_kmh2`), while the **data** keeps the natural names (`traction`, `traction_curve`, `running_resistance`, `curve_resistance`, `"DAVIS"`, `"FORCE_THEN_POWER_LIMITED"`). No token moved, no forbidden list changed (S1 9, S2 14, S3 7, allowed 5) and no scan surface was widened or narrowed; recorded as the stage's §F5 adaptation in `VERIFICATION.md` §18.6 and with the file hashes in `docs/PHASE1_CHAIN_OF_CUSTODY.md` §7.6. |

**Declared adaptation A6 (`TEST P5-042`) — one more file than the Stage-6A brief's §H list.**
`docs/TEST_INVENTORY.md` is a *generated* file, and `TEST P5-042` pinned two of its literal lines:
the canonical decomposition `66 + 30 + 5 + 26 + 30 + 18 + 24 + 18 = 217` and the totals row
`| **Total (all eight suites)** | **217** |`. Registering the ninth acceptance table makes both
lines false, so the pins could not survive Stage 6A — the identical situation to the Stage-5B
adaptation A4 in `TEST P5-024`. A6 applies A4's exact treatment and nothing else: the
decomposition is read from the inventory and must **sum to its own stated total**, and the totals
row must state **that same total** with a suite count **equal to the number of terms** (the
word-number map already carries `nine`). Both replacements are strictly stronger than the
literals they replace; the three still-valid Phase-5B pins (the suite row, the suite heading and
the `P5-042` row) were kept, and every other assertion of `TEST P5-042` — the S1/S3 token counts,
the allowed-token list, the declared-name scan, the prose scan and the physics-package scan — is
byte-identical. No test was renamed, removed, weakened or skipped, and the file's before/after
hash is in `docs/PHASE1_CHAIN_OF_CUSTODY.md` §7.6.

**Additive registration, not a supersession.** The Phase-6A table, the ninth suite entry and the
new module cells change no existing expectation: every row of the eight earlier tables and every
verdict they print is unchanged, and the Phase-6A additions are declared here only because they
touch files that also carry pinned counts.

**Phase 6B 0.8.0 -> 0.9.0 (minor release, same declaration).** Stage 6B delivers the
**read-only Rolling Stock page** and the two small physics utilities its curves need — three new
modules (`railway_headway_sim/physics/tractive_effort.py`, the frozen simplified
`FORCE_THEN_POWER_LIMITED` effort; `railway_headway_sim/physics/rolling_stock_series.py`, the two
sampled series; `railway_headway_sim/ui/rolling_stock_page.py`, the page itself) plus the
Phase-6B suite — and bumps the application version `0.8.0` -> `0.9.0` in
`railway_headway_sim/version.py` only (the single authority), where `APP_PHASE` now names
`Phase 6B — Rolling-Stock UI`. A minor bump (not a patch) is correct: a new engineering surface
is added (the effort characteristic and the two series) together with a new functional page, and
no stored key, validation rule or existing public interface changes. The project schema stays
`("1.0",)`, no protected artefact and neither companion file changed, and the canonical project
hash is unchanged. Four sites that pin the *current* version were re-pointed in exactly the same
way, with no change of expectation and **no test renamed**:

| Site | Why it had to change | How it changed |
|---|---|---|
| `tests/test_controller.py` (state/version assertion) | The literal names the *current* application version, which this release bumps to 0.9.0. | The literal `"0.8.0"` became `"0.9.0"`; the assertion still reads `railway_headway_sim.version.APP_VERSION` and pins the current value. The comment that records the version chain keeps the historical 0.7.0 -> 0.8.0 text. |
| `tests/test_ui_shell.py::test_header_shows_versions_and_status_text` | Same version bump (the header must show the authoritative application version). | The literal `"APP v0.8.0"` became `"APP v0.9.0"`; `"SCHEMA v1.0"` and the status assertions are unchanged. |
| `tests/test_phase3_editors.py::TEST P3-001` | The Phase-3 suite pins the same current value. | Re-pointed `0.8.0` -> `0.9.0` (including its "no other module carries the app version literal" scan). The function name is kept — a rename would change a collected node id. |
| `tests/test_phase4a_route_coordinate.py` — `TEST P4-026`'s version and phase literals | The test asserts that `APP_PHASE` names the *current* phase and matches `APP_VERSION`, so it had to follow the bump. | `0.8.0` -> `0.9.0`, `"APP v0.8.0"` -> `"APP v0.9.0"`; the phase expectation `"Phase 6A" in label` became `"Phase 6B" in label`, `"Phase 5B" not in label` became `"Phase 6A" not in label` (the previous phase) and the guard `"Phase 6B" not in label` became `"Phase 7" not in label` (the next phase, not started — the bare `"Phase 6"` guard of Stage 5B could not survive a Stage-6B label). The function name, its row and its remaining assertions are unchanged. |

Five further adaptations belong to this stage and are declared for the same reason:

| Adaptation | Why it had to change | How it changed |
|---|---|---|
| `tests/test_phase2_facade_and_app.py` — **A7** in `TEST P2-028` | The test compared the shell's structural sets against a hard-coded page list that could not know the new functional page. | The two structural sets are compared against `NAVIGATION_TITLES` itself, so a page that is rendered without being declared — or declared without being rendered — still fails. No set was dropped and nothing was loosened. |
| `tests/test_phase5a_resistance.py` — **A8** in `TEST P5-020` | The test asserted that the physics package stays a leaf (no importer outside it), which the page cannot satisfy. | The assertion became an **allow-list of exactly `ui/rolling_stock_page.py`**: any other importer outside `railway_headway_sim/physics/` still fails, and the direction rule (no physics module imports infrastructure, IO, app or UI) is asserted separately by `TEST P6-044`. A lazy/`importlib` import to dodge the rule was considered and rejected as a workaround. |
| `tests/test_phase5a_resistance.py` — **A9** in `TEST P5-024`; `tests/test_phase5b_along_route.py` — **A10** in `TEST P5-042` | Both decompose the generated inventory's canonical totals line and totals row through a word map that ended at `"nine"`; the tenth suite makes the word `"ten"`, and a missing key raises rather than passing silently. | Both maps gained `"ten": 10` — the only edit in either file besides A8. The checks themselves (the decomposition must sum to its own stated total; the totals row must state that total and count its suites) are unchanged and remain strictly stronger than the literals they replaced in Stages 5B/6A. |
| `tests/test_ui_shell.py` — **`UI-REG-009`** (the one declared supersession of this stage) | The hard-coded seven-entry placeholder list could not survive a fifth functional page. | Recorded in §2 above; the placeholder string, the no-calculation assertion and the colour-independence wording are byte-identical, and the test is not renamed. |
| `docs/SECTION_D_PATTERNS.md` — **D1** (declared document adaptation, authorised in advance) | Two counts had gone stale and the S4 row's mechanism sentence described the pre-6B check. | §1's S4 row now reads *six* remaining pages (every entry of `PLANNED_PAGES`) and *five* implemented pages with the two-way disjointness against `NAVIGATION_TITLES`; §6's closing sentence reads *six* unimplemented pages and names the enumeration of the five functional ones. No token list of §2, §2.1, §3 or §4 changed. `084d82c43d6a…` -> `936cabddd75e…`. |

Three more mechanical edits complete the stage, none of them an expectation change: the
registration (`tests/conftest.py` tenth table, `build_test_inventory.py` tenth suite, the
canonical decomposition `… + 24 = 265` and the totals row "all ten suites",
`build_colab_notebook.py` version/phase text and the new module cells); the **three
checker-forced re-layouts of `VERIFICATION.md` §18** (the retired Phase-6A pass total now sits in
its own code span in §18.1/§18.5/§18.8, exactly as §17's J1 row and §16's two rows were treated
in earlier stages — no number, row or other word changed); and the naming consequence of the S1
scan (`traction` may not appear in a *declared name* anywhere, so the page names its
Traction-tab helpers `_effort_parameters_html`, `_render_effort_plots` and `effort_plot_svg`
while the stored data keeps `traction`, `traction_curve`, the enumeration value
`"FORCE_THEN_POWER_LIMITED"` and the sub-tab title `"Traction"`).

**Additive registration, not a supersession.** The Phase-6B table, the tenth suite entry and the
new module cells change no existing expectation beyond the declared items above: every row of the
nine earlier tables and every verdict they print is unchanged, and the Phase-6B additions are
declared here only because they touch files that also carry pinned counts. The full file-by-file
before -> after ledger is `docs/PHASE1_CHAIN_OF_CUSTODY.md` §7.7.

