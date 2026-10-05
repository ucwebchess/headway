# TEST INVENTORY

> **Generated file — do not edit by hand.** Produced by `python3 build_test_inventory.py`.
> This file is the single source of truth for every quoted test total in `README.md`,
> `VERIFICATION.md` and the Colab notebook self-check. Verify with
> `python3 build_test_inventory.py --check`.

## 1. Totals (canonical)

| Suite | Collected items | Distinct acceptance IDs | Acceptance table rows |
|---|---|---|---|
| Phase-1 suite (TEST P1-001 … TEST P1-012) | 66 | 12 | 18 |
| Phase-2 suite (TEST P2-001 … TEST P2-028) | 30 | 28 | 28 |
| GRR-01 registry regressions (TEST P2-REG-G001 … TEST P2-REG-G005) | 5 | 5 | 5 |
| Phase-3 suite (TEST P3-001 … TEST P3-026) | 26 | 26 | 26 |
| Phase-4A suite (TEST P4-001 … TEST P4-030) | 30 | 30 | 30 |
| Phase-4B suite (TEST P4-031 … TEST P4-048) | 18 | 18 | 18 |
| Phase-5A suite (TEST P5-001 … TEST P5-024) | 24 | 24 | 24 |
| Phase-5B suite (TEST P5-025 … TEST P5-042) | 18 | 18 | 18 |
| Phase-6A suite (TEST P6-001 … TEST P6-024) | 24 | 24 | 24 |
| Phase-6B suite (TEST P6-025 … TEST P6-048) | 24 | 24 | 24 |
| **Total (all ten suites)** | **265** | 209 | 215 |

**Canonical decomposition string** (quoted verbatim by the documents):

> `66 + 30 + 5 + 26 + 30 + 18 + 24 + 18 + 24 + 24 = 265` collected items (66 Phase-1 + 30 Phase-2 + 5 GRR-01 registry regressions + 26 Phase-3 + 30 Phase-4A + 18 Phase-4B + 24 Phase-5A + 18 Phase-5B + 24 Phase-6A + 24 Phase-6B).

**Run outcome in the recorded environment:** 265/265 `PASS`, 0 `FAIL`, exit code 0.

The acceptance tables print one row per **asserted instance**, so a numbered test
that is parametrised (or asserts the same acceptance ID in several functions) appears
more than once: this is why the Phase-1 table has more rows than distinct IDs.

## 2. Acceptance tables (as printed by the runner)

### Phase-1 suite (TEST P1-001 … TEST P1-012) — 18/18 rows

| Acceptance ID | Table rows | Title |
|---|---|---|
| `P1-001` | 1 | A new project template validates as VALID with no diagnostics. |
| `P1-002` | 2 | Export -> import yields equivalent project data. |
| `P1-003` | 1 | Roundtrip and re-export keep the canonical project hash. |
| `P1-004` | 1 | A document without schema_version is INVALID with a schema diagnostic. |
| `P1-005` | 1 | An unsupported schema_version is INVALID and is not parsed. |
| `P1-006` | 4 | Missing/empty project ID (or name) is an ERROR (INVALID). |
| `P1-007` | 3 | chainage_end <= chainage_start is INVALID (VAL-REF-001). |
| `P1-008` | 1 | An unsupported chainage direction value is INVALID (VAL-DIR-001). |
| `P1-009` | 1 | Editing after validation marks the project as modified. |
| `P1-010` | 1 | Switching FORWARD/REVERSE leaves all stored data unchanged. |
| `P1-011` | 1 | Hostile JSON payloads are treated as inert data. |
| `P1-012` | 1 | Every diagnostic exposes code/severity/message and is deterministic. |

### Phase-2 suite (TEST P2-001 … TEST P2-028) — 28/28 rows

| Acceptance ID | Table rows | Title |
|---|---|---|
| `P2-001` | 1 | every typed catalogue parses into strict unit-suffixed models. |
| `P2-002` | 1 | display_units never changes stored values (unit suffixes rule). |
| `P2-003` | 1 | alignment end > start is enforced; a reversed alignment is INVALID. |
| `P2-004` | 1 | reference_system.alignment_id must resolve to an alignment. |
| `P2-005` | 1 | curves need radius_m > 0 plus handedness and must stay in the alignment. |
| `P2-006` | 1 | overlapping sections and coverage gaps are both ERRORs. |
| `P2-007` | 1 | ELEVATION_POINTS: >= 2 points, strictly increasing unique chainage, in-range. |
| `P2-008` | 1 | speed > 0, range inside the alignment, valid direction and type. |
| `P2-009` | 1 | node chainage inside the alignment; optional station_id must resolve. |
| `P2-010` | 1 | endpoints exist and differ, length_m > 0, group resolves, map in-range. |
| `P2-011` | 1 | parallel/overlapping chainage is not a conflict; length != projection is legal. |
| `P2-012` | 1 | legacy chainages[] must match Track.chainage_map within 1e-9 km. |
| `P2-013` | 1 | adjacency/connectivity use node identity only (never chainage equality). |
| `P2-014` | 1 | edge sequences are checked for continuity by node identity. |
| `P2-015` | 1 | an opaque record with an 'id' is an ERROR (VAL-PHASE-002) plus a WARNING. |
| `P2-016` | 1 | unknown extension fields survive import -> export at every level. |
| `P2-017` | 1 | platform ids resolve and belong to the station; no duplicates. |
| `P2-018` | 1 | usable range inside the track, length reconciliation, references. |
| `P2-019` | 1 | mark track, position bounds, usable range, direction; chainage derived. |
| `P2-020` | 1 | SERVICE_EVENT / CROSS_SECTION / TRACK_CROSS_SECTION members. |
| `P2-021` | 1 | WITH_EDGE: rear = front - L; AGAINST_EDGE: rear = front + L. |
| `P2-022` | 1 | the five frozen static benchmarks reproduce exactly. |
| `P2-023` | 1 | front/rear chainages are mapped; unmappable positions are reported. |
| `P2-024` | 1 | FORWARD -> WITH_EDGE, REVERSE -> AGAINST_EDGE; baseline table holds. |
| `P2-025` | 1 | physical projects get Phase-2 scope; legacy projects keep Phase-1 behaviour. |
| `P2-026` | 1 | an invalid uncommitted draft is rejected (APP-EDIT-002) and blocks export. |
| `P2-027` | 1 | Infrastructure + Stations pages render typed data and never edit it. |
| `P2-028` | 1 | Section D: no train dynamics, signalling, headway or capacity anywhere. |

### GRR-01 registry regressions (TEST P2-REG-G001 … TEST P2-REG-G005) — 5/5 rows

| Acceptance ID | Table rows | Title |
|---|---|---|
| `P2-REG-G001` | 1 | GRR-01 loads with exactly the frozen object counts and no errors. |
| `P2-REG-G002` | 1 | regional node/edge counts (6/18/8/12/6 and 8/4/23/8/12/4). |
| `P2-REG-G003` | 1 | globally unique registered IDs; a broken draft cannot be exported. |
| `P2-REG-G004` | 1 | the Section BA contradiction scan reports no contradiction. |
| `P2-REG-G005` | 1 | loading/export is stable; timestamps, hash and amendments hold. |

### Phase-3 suite (TEST P3-001 … TEST P3-026) — 26/26 rows

| Acceptance ID | Table rows | Title |
|---|---|---|
| `P3-001` | 1 | app version 0.9.0 lives in version.py only; schema stays 1.0. |
| `P3-002` | 1 | the editor column headers carry the unit of their field. |
| `P3-003` | 1 | all tooltips come from ui/field_help.py (single source). |
| `P3-004` | 1 | STANDARD/ADVANCED hides only optional columns and is shared. |
| `P3-005` | 1 | a staged edit leaves the committed project and hash untouched. |
| `P3-006` | 1 | commit applies the draft; discard keeps the canonical hash. |
| `P3-007` | 1 | invalid edits reuse Phase-1/2 codes and block commit/export. |
| `P3-008` | 1 | rows can be added and deleted; a referenced row refuses deletion. |
| `P3-009` | 1 | deletion refusal names the referencing objects, incl. the reference system. |
| `P3-010` | 1 | profile points are edited inside their owning profile. |
| `P3-011` | 1 | Line-level reference system editing, with fixed fields refused. |
| `P3-012` | 1 | gradient between adjacent points; FORWARD/REVERSE is display only. |
| `P3-013` | 1 | the curvature series carries stored radius/handedness, nothing derived. |
| `P3-014` | 1 | effective speed per direction; the lowest limit wins. |
| `P3-015` | 1 | FIT / TOO_LONG / MARKER_OUTSIDE_USABLE classification. |
| `P3-016` | 1 | the checker shows the package result; the length is never stored. |
| `P3-017` | 1 | every drawn element exists in the loaded document. |
| `P3-018` | 1 | four layers render; the four others are visibly disabled. |
| `P3-019` | 1 | schematic selection routes to the owning editor row. |
| `P3-020` | 1 | the required sub-tabs exist and keep their state in the session. |
| `P3-021` | 1 | every Phase-2 page attribute still exists and shows the frozen data. |
| `P3-022` | 1 | row badges, category counts and focus actions; no new codes. |
| `P3-023` | 1 | export/import remain available and keep the canonical hash. |
| `P3-024` | 1 | the UI renders stored/package values; it computes no engineering value. |
| `P3-025` | 1 | no module imports a private name from ipywidgets. |
| `P3-026` | 1 | close_widget_tree releases a real widget tree through Widget.close(). |

### Phase-4A suite (TEST P4-001 … TEST P4-030) — 30/30 rows

| Acceptance ID | Table rows | Title |
|---|---|---|
| `P4-001` | 1 | compile the reference network without touching the project. |
| `P4-002` | 1 | the network reads exactly the train paths the project declares. |
| `P4-003` | 1 | FORWARD uses the declared traversal; s runs 0 -> L_F. |
| `P4-004` | 1 | REVERSE: same physical edges, reversed order, complementary traversal. |
| `P4-005` | 1 | both directions resolve the same chainage_map values per edge. |
| `P4-006` | 1 | (edge_id, local_position_m) identifies the position; chainage is mapped. |
| `P4-007` | 1 | s is bounded to [0, route_length]; outside values are refused. |
| `P4-008` | 1 | edge_at() resolves each segment and stays in travel order. |
| `P4-009` | 1 | chainage -> s -> chainage round-trips on the reference path. |
| `P4-010` | 1 | a chainage that is not on the path is refused, never fabricated. |
| `P4-011` | 1 | the fixture runs 0 -> L_F forward and 0 -> L_R reverse. |
| `P4-012` | 1 | route distance and chainage stay separate measures. |
| `P4-013` | 1 | an opposite-oriented chainage_map is honoured, not repaired. |
| `P4-014` | 1 | FORWARD/REVERSE write neither the project, the file nor the hash. |
| `P4-015` | 1 | one compilation per run; the coordinate systems are read-only. |
| `P4-016` | 1 | the direction is a property of the system, s never goes negative. |
| `P4-017` | 1 | an unresolved edge_id is reported (VAL-REGISTRY-003) and refused. |
| `P4-018` | 1 | a sequence break is reported (VAL-TOPO-007) and refused. |
| `P4-019` | 1 | an unusable traversal (VAL-ENUM-001) or direction (VAL-DIR-001) is reported. |
| `P4-020` | 1 | missing/duplicate ids and empty sequences are reported, never repaired. |
| `P4-021` | 1 | the new module carries no Section-D pattern (S1 names, S3 public names). |
| `P4-022` | 1 | no numeric dependency, no validation facade import, no cycle. |
| `P4-023` | 1 | the companion file loads and declares exactly PATH-H1-F/PATH-H1-R. |
| `P4-024` | 1 | PATH-H1-F/PATH-H1-R are the real terminal-to-terminal walks. |
| `P4-025` | 1 | the renamed test-corridor paths keep their 49 000 m walk. |
| `P4-026` | 1 | APP_PHASE names the current phase and matches APP_VERSION. |
| `P4-027` | 1 | PATH-H1-R is the exact reverse of PATH-H1-F, entry by entry. |
| `P4-028` | 1 | equal length (bit for bit), equal edge count, swapped terminals. |
| `P4-029` | 1 | FORWARD of both paths is the same physical edge sequence, reversed. |
| `P4-030` | 1 | no diagnostic is emitted for the corrected companion file. |

### Phase-4B suite (TEST P4-031 … TEST P4-048) — 18/18 rows

| Acceptance ID | Table rows | Title |
|---|---|---|
| `P4-031` | 1 | RouteGeometry builds from the frozen project and an H1 route, cleanly. |
| `P4-032` | 1 | elevation_at is the stored profile's linear interpolation. |
| `P4-033` | 1 | the same physical location returns the same elevation both ways. |
| `P4-034` | 1 | the same physical location returns opposite-signed gradients. |
| `P4-035` | 1 | the gradient uses its stored segment and is not interpolated. |
| `P4-036` | 1 | a flat stored segment yields exactly 0.0 per mille. |
| `P4-037` | 1 | the stored radius is returned wherever a CURVE section covers. |
| `P4-038` | 1 | a STRAIGHT section returns None, never a sentinel float. |
| `P4-039` | 1 | the radius is a magnitude: both directions return the same value. |
| `P4-040` | 1 | a footprint inside one segment returns gradient_at exactly. |
| `P4-041` | 1 | a straddling footprint returns the length-weighted mean. |
| `P4-042` | 1 | a non-positive train length raises ValueError. |
| `P4-043` | 1 | a route distance outside [0, L] raises RouteCoordinateError. |
| `P4-044` | 1 | a project without a catalogue reports and raises, never invents. |
| `P4-045` | 1 | the project and the companion file are unchanged by reading. |
| `P4-046` | 1 | the Phase-4B module imports only the standard library and the package. |
| `P4-047` | 1 | the Phase-4B module carries no Section-D token. |
| `P4-048` | 1 | the Phase-4B table is registered; the earlier tables are unchanged. |

### Phase-5A suite (TEST P5-001 … TEST P5-024) — 24/24 rows

| Acceptance ID | Table rows | Title |
|---|---|---|
| `P5-001` | 1 | the module exists, imports cleanly and exposes the documented API. |
| `P5-002` | 1 | Davis resistance is A + B*V + C*V**2 [kN] returned in newtons. |
| `P5-003` | 1 | at V = 0 the Davis resistance is A * 1000.0, bit-for-bit. |
| `P5-004` | 1 | the Davis resistance never decreases with speed on [0, 400] km/h. |
| `P5-005` | 1 | negative/non-finite speed and negative coefficients are reported. |
| `P5-006` | 1 | +10 per mille on 485 000 kg is m * g * 0.01 newtons. |
| `P5-007` | 1 | -10 per mille is the exact negation of the +10 per mille force. |
| `P5-008` | 1 | 0.0 per mille returns exactly 0.0 (and not a signed zero). |
| `P5-009` | 1 | GRAVITY_MPS2 is 9.80665 and the force is linear in mass. |
| `P5-010` | 1 | a non-positive mass and a non-finite grade are reported. |
| `P5-011` | 1 | R = 1800 m on 485 000 kg is m * g * (650 / (R - 55)) / 1000 newtons. |
| `P5-012` | 1 | radius_m = None returns exactly 0.0 and does not raise. |
| `P5-013` | 1 | a radius in (0.0, 55.0] is a reported error, never a clamp. |
| `P5-014` | 1 | radius 0.0, a negative radius, NaN and infinity are all reported. |
| `P5-015` | 1 | W_c = 650 / (R - 55) permille is the value the force uses. |
| `P5-016` | 1 | True for R > 55 m; False for R <= 55, NaN and infinity. |
| `P5-017` | 1 | the total is Davis + gradient + Roeckl, recomputed here. |
| `P5-018` | 1 | gradient 0.0 and radius None leave the Davis resistance alone. |
| `P5-019` | 1 | a steep enough downhill outweighs both resistance magnitudes. |
| `P5-020` | 1 | no numeric library, nothing outside the standard library, no cycle. |
| `P5-021` | 1 | unit suffixes in names, units documented in every docstring. |
| `P5-022` | 1 | bit-identical repeat calls; the loaded project never changes. |
| `P5-023` | 1 | the five tokens are allowed; every other forbidden token still fails. |
| `P5-024` | 1 | the Phase-5A table is registered; the earlier six are unchanged. |

### Phase-5B suite (TEST P5-025 … TEST P5-042) — 18/18 rows

| Acceptance ID | Table rows | Title |
|---|---|---|
| `P5-025` | 1 | the module exists, exposes the four functions, and the table is registered. |
| `P5-026` | 1 | the running-resistance term is the Stage-5A value, recomputed. |
| `P5-027` | 1 | the sub-intervals are ordered, sum to the span, and report stored radii. |
| `P5-028` | 1 | ValueError for a reversed interval; the footprint range convention. |
| `P5-029` | 1 | on level track on a straight the grade force is exactly 0.0. |
| `P5-030` | 1 | inside one stored gradient segment: m * g * (gradient / 1000), recomputed. |
| `P5-031` | 1 | FORWARD and REVERSE are opposite-signed for the same physical body. |
| `P5-032` | 1 | a footprint wholly on straight sections returns exactly 0.0. |
| `P5-033` | 1 | wholly inside one curve: m * g * W(R) / 1000, recomputed from R. |
| `P5-034` | 1 | a footprint across a straight/curve boundary: weighted mean, recomputed. |
| `P5-035` | 1 | non-negative everywhere, and equal in both directions of travel. |
| `P5-036` | 1 | the total is running + grade + curvature, recomputed by the test. |
| `P5-037` | 1 | level and straight: the total is the position-independent term. |
| `P5-038` | 1 | a steep enough descent outweighs both resistance magnitudes. |
| `P5-039` | 1 | non-positive length, out-of-range footprint and bad mass all report. |
| `P5-040` | 1 | bit-identical repeats; canonical and companion hashes unchanged. |
| `P5-041` | 1 | standard library plus the package's own modules, nothing else. |
| `P5-042` | 1 | no Section-D token outside the allowed ones; the table is counted. |

### Phase-6A suite (TEST P6-001 … TEST P6-024) — 24/24 rows

| Acceptance ID | Table rows | Title |
|---|---|---|
| `P6-001` | 1 | the module exists, imports cleanly, and exposes the documented API. |
| `P6-002` | 1 | the companion file exists, loads, and validates with zero diagnostics. |
| `P6-003` | 1 | the companion file declares exactly RS-HSR320 and RS-REG200. |
| `P6-004` | 1 | the typed RS-HSR320 instance carries the frozen HSR values. |
| `P6-005` | 1 | the typed RS-REG200 instance carries its own frozen values. |
| `P6-006` | 1 | the SI properties equal the stored fields, recomputed here. |
| `P6-007` | 1 | static_mass_t = 0.0 and a negative value are both rejected. |
| `P6-008` | 1 | length_m = 0.0 and a negative value are both rejected. |
| `P6-009` | 1 | a rotating-mass allowance below 1.0 is rejected. |
| `P6-010` | 1 | max_speed_kmh <= 0.0 is rejected. |
| `P6-011` | 1 | rated_power_kw <= 0.0 is rejected. |
| `P6-012` | 1 | max_tractive_effort_kn <= 0.0 is rejected. |
| `P6-013` | 1 | max_operational_acceleration_mps2 <= 0.0 is rejected. |
| `P6-014` | 1 | a negative running-resistance coefficient is rejected. |
| `P6-015` | 1 | a service-braking reference deceleration <= 0.0 is rejected. |
| `P6-016` | 1 | an ETCS reference deceleration <= 0.0 is rejected. |
| `P6-017` | 1 | an unrecognised unit or model value is rejected, naming the field. |
| `P6-018` | 1 | NaN and +inf / -inf are rejected, naming the offending field. |
| `P6-019` | 1 | the optional effort characteristic is validated point by point. |
| `P6-020` | 1 | extension fields at every level survive load -> dump -> load. |
| `P6-021` | 1 | mapping, JSON text, Path and file name yield the same catalogue. |
| `P6-022` | 1 | the frozen project, its hash and the paths companion are untouched. |
| `P6-023` | 1 | the delivered modules add no numeric or forbidden dependency. |
| `P6-024` | 1 | Section-D scan: the new modules carry no forbidden declared name. |

### Phase-6B suite (TEST P6-025 … TEST P6-048) — 24/24 rows

| Acceptance ID | Table rows | Title |
|---|---|---|
| `P6-025` | 1 | the module exists, imports cleanly, and exposes the documented API. |
| `P6-026` | 1 | at zero speed the force-limited branch applies (no P/v singularity). |
| `P6-027` | 1 | at or below the transition speed the effort is exactly F_max * 1000. |
| `P6-028` | 1 | above the transition speed the effort is exactly P / v, recomputed here. |
| `P6-029` | 1 | the curve is capped by F_max at every sampled speed. |
| `P6-030` | 1 | the frozen pair (9800.0 kW, 300.0 kN) implies 117.6 km/h. |
| `P6-031` | 1 | every unusable argument is reported, and the message names it. |
| `P6-032` | 1 | the series module exists, imports cleanly, and exposes both functions. |
| `P6-033` | 1 | the effort series starts at 0.0 and ends exactly at max_speed_kmh. |
| `P6-034` | 1 | every sample equals the primitive at the same speed, recomputed here. |
| `P6-035` | 1 | the resistance series spans 0.0 to max_speed_kmh and is ordered. |
| `P6-036` | 1 | every sample equals the Stage-5A primitive over the stock's coefficients. |
| `P6-037` | 1 | a non-positive step is reported naming the argument; valid steps give >= 2. |
| `P6-038` | 1 | the new page module exists, is functional, and the shell shows it. |
| `P6-039` | 1 | Rolling Stock is no longer planned; the six remaining pages still are. |
| `P6-040` | 1 | the page shows both stock types and every stored parameter of each. |
| `P6-041` | 1 | the Traction plot is built from the effort series and has >= 2 points. |
| `P6-042` | 1 | the Resistance plot is built from the resistance series, >= 2 points. |
| `P6-043` | 1 | the page is read-only: no draft call, no editable widget, only outputs. |
| `P6-044` | 1 | no numeric library, and nothing outside the standard library and the package. |
| `P6-045` | 1 | Section-D scan: forbidden names absent, allowed tokens still confined. |
| `P6-046` | 1 | the page render and both series calls leave every hash unchanged. |
| `P6-047` | 1 | the nine earlier tables are registered unchanged; only §H and §G.5 moved. |
| `P6-048` | 1 | the Phase-6B table is registered, and the suite is now 265 items. |

## 3. Unnumbered tests (collected, no acceptance ID)

These tests are collected and executed but carry no numbered acceptance ID;
they are structural/guard regressions, not acceptance instances:

- `test_controller.py::test_direction_selection_rejects_reserved_values`
- `test_controller.py::test_direction_state_guard_rejects_other_values`
- `test_controller.py::test_export_uses_controller_directory_and_reports_outcome`
- `test_controller.py::test_export_without_project_is_rejected_cleanly`
- `test_controller.py::test_import_failure_preserves_the_current_project`
- `test_controller.py::test_import_marks_project_as_validated_for_imported_content`
- `test_controller.py::test_import_of_invalid_but_usable_document_preserves_content`
- `test_controller.py::test_invalid_edit_is_rejected_with_a_message`
- `test_controller.py::test_new_project_provides_template_defaults`
- `test_controller.py::test_no_file_selected_import_reports_precondition_error`
- `test_controller.py::test_no_op_edit_does_not_invalidate_the_validation`
- `test_controller.py::test_subscribers_are_notified_and_can_unsubscribe`
- `test_controller.py::test_summary_and_state_rows_are_available_for_the_ui`
- `test_controller.py::test_unknown_field_edit_is_rejected`
- `test_controller.py::test_validate_without_project_is_reported_as_error`
- `test_phase2_models.py::test_phase2_models_out_of_scope_guards`
- `test_phase2_static_geometry.py::test_phase2_static_geometry_has_no_dynamics`
- `test_project_io.py::test_empty_upload_is_reported_as_application_error`
- `test_project_io.py::test_export_document_shape_uses_canonical_section_order`
- `test_project_io.py::test_export_filename_reflects_project_name_and_id`
- `test_project_io.py::test_export_metadata_is_opt_in_and_does_not_break_roundtrip`
- `test_project_io.py::test_export_preserves_stored_numeric_values_and_types`
- `test_project_io.py::test_hash_is_order_independent_and_normalises_numbers`
- `test_project_io.py::test_import_helpers_do_not_use_unsafe_deserialization`
- `test_project_io.py::test_roundtrip_through_files_and_helpers`
- `test_project_io.py::test_upload_payload_shapes_are_supported`
- `test_ui_shell.py::test_audit_page_renders_and_filters_diagnostics`
- `test_ui_shell.py::test_controller_listeners_refresh_the_shell_without_manual_calls`
- `test_ui_shell.py::test_direction_buttons_drive_the_controller_and_labels`
- `test_ui_shell.py::test_header_shows_versions_and_status_text`
- `test_ui_shell.py::test_launch_app_builds_and_can_write_a_static_snapshot`
- `test_ui_shell.py::test_placeholder_pages_do_not_implement_engineering_calculations`
- `test_ui_shell.py::test_project_page_edits_are_written_through_the_controller`
- `test_ui_shell.py::test_project_page_reimport_updates_every_widget`
- `test_ui_shell.py::test_shell_builds_all_navigation_pages`
- `test_validation.py::test_chainage_bounds_are_accepted_when_increasing`
- `test_validation.py::test_display_unit_warning_is_not_an_error`
- `test_validation.py::test_documented_example_project_is_valid`
- `test_validation.py::test_duplicate_identifiers_are_reported_per_object_type`
- `test_validation.py::test_extra_unknown_fields_are_preserved`
- `test_validation.py::test_identical_forward_and_reverse_direction_warns`
- `test_validation.py::test_malformed_container_is_reported_and_defaulted`
- `test_validation.py::test_malformed_field_type_is_reported_once_and_not_repaired_silently`
- `test_validation.py::test_missing_container_is_created_with_default_and_info`
- `test_validation.py::test_missing_direction_is_invalid`
- `test_validation.py::test_non_object_root_is_reported`
- `test_validation.py::test_preserved_containers_get_info_only`
- `test_validation.py::test_schema_version_of_wrong_type_is_invalid`
- `test_validation.py::test_undecodable_upload_bytes_are_reported`
- `test_validation.py::test_unparseable_json_text_is_reported`

## 4. Collected items per test module

| Module | Collected items | Suite |
|---|---|---|
| `test_controller.py` | 17 | phase1 |
| `test_phase2_facade_and_app.py` | 4 | phase2 |
| `test_phase2_grr_regressions.py` | 5 | grr |
| `test_phase2_models.py` | 8 | phase2 |
| `test_phase2_static_geometry.py` | 5 | phase2 |
| `test_phase2_stations.py` | 4 | phase2 |
| `test_phase2_topology.py` | 9 | phase2 |
| `test_phase3_editors.py` | 26 | phase3 |
| `test_phase4a_route_coordinate.py` | 30 | phase4a |
| `test_phase4b_geometry_along_route.py` | 18 | phase4b |
| `test_phase5a_resistance.py` | 24 | phase5a |
| `test_phase5b_along_route.py` | 18 | phase5b |
| `test_phase6a_rolling_stock_model.py` | 24 | phase6a |
| `test_phase6b_rolling_stock_ui.py` | 24 | phase6b |
| `test_project_io.py` | 13 | phase1 |
| `test_ui_shell.py` | 9 | phase1 |
| `test_validation.py` | 27 | phase1 |

## 5. Record environment

* Python 3.13.14 (`Linux-6.1.158+-x86_64-with-glibc2.41`)
* pytest 9.0.3
* Command: `pytest railway_headway_sim/tests -q -p no:cacheprovider --tb=no`

## 6. Full collected node id list

```text
test_controller.py::test_direction_selection_rejects_reserved_values
test_controller.py::test_direction_state_guard_rejects_other_values
test_controller.py::test_export_uses_controller_directory_and_reports_outcome
test_controller.py::test_export_without_project_is_rejected_cleanly
test_controller.py::test_import_failure_preserves_the_current_project
test_controller.py::test_import_marks_project_as_validated_for_imported_content
test_controller.py::test_import_of_invalid_but_usable_document_preserves_content
test_controller.py::test_invalid_edit_is_rejected_with_a_message
test_controller.py::test_new_project_provides_template_defaults
test_controller.py::test_no_file_selected_import_reports_precondition_error
test_controller.py::test_no_op_edit_does_not_invalidate_the_validation
test_controller.py::test_p1_009_modify_after_validation_is_detected
test_controller.py::test_p1_010_direction_change_does_not_mutate_project_data
test_controller.py::test_subscribers_are_notified_and_can_unsubscribe
test_controller.py::test_summary_and_state_rows_are_available_for_the_ui
test_controller.py::test_unknown_field_edit_is_rejected
test_controller.py::test_validate_without_project_is_reported_as_error
test_phase2_facade_and_app.py::test_p2_025_validation_facade_scope_and_single_result_model
test_phase2_facade_and_app.py::test_p2_026_controller_draft_mechanism_blocks_export
test_phase2_facade_and_app.py::test_p2_027_ui_pages_are_functional_and_read_only
test_phase2_facade_and_app.py::test_p2_028_no_out_of_scope_capability_or_result
test_phase2_grr_regressions.py::test_p2_reg_g001_grr01_loads_with_the_frozen_inventory
test_phase2_grr_regressions.py::test_p2_reg_g002_regional_inventory
test_phase2_grr_regressions.py::test_p2_reg_g003_global_registry_uniqueness_and_draft_guard
test_phase2_grr_regressions.py::test_p2_reg_g004_section_ba_contradiction_scan_is_clean
test_phase2_grr_regressions.py::test_p2_reg_g005_grr01_load_stability_and_evidence_files
test_phase2_models.py::test_p2_001_all_typed_catalogues_parse_with_unit_suffixed_fields
test_phase2_models.py::test_p2_002_display_units_are_a_preference_only
test_phase2_models.py::test_p2_003_alignment_requires_end_greater_than_start
test_phase2_models.py::test_p2_004_reference_system_alignment_id_must_resolve
test_phase2_models.py::test_p2_005_horizontal_geometry_curve_and_range_rules
test_phase2_models.py::test_p2_006_geometry_overlap_and_coverage_rules
test_phase2_models.py::test_p2_007_vertical_profile_rules
test_phase2_models.py::test_phase2_models_out_of_scope_guards
test_phase2_static_geometry.py::test_p2_021_orientation_rules_and_fit_flags
test_phase2_static_geometry.py::test_p2_022_frozen_static_benchmarks
test_phase2_static_geometry.py::test_p2_023_footprint_chainage_mapping_and_notes
test_phase2_static_geometry.py::test_p2_024_marker_direction_maps_to_traversal_and_baseline_table
test_phase2_static_geometry.py::test_phase2_static_geometry_has_no_dynamics
test_phase2_stations.py::test_p2_017_station_rules
test_phase2_stations.py::test_p2_018_platform_rules
test_phase2_stations.py::test_p2_019_stopping_mark_rules
test_phase2_stations.py::test_p2_020_observation_point_rules
test_phase2_topology.py::test_p2_008_speed_restriction_rules
test_phase2_topology.py::test_p2_009_node_rules
test_phase2_topology.py::test_p2_010_track_rules
test_phase2_topology.py::test_p2_011_parallel_chainage_and_projection_mismatch_are_legal
test_phase2_topology.py::test_p2_012_legacy_chainages_reconciled_with_chainage_map
test_phase2_topology.py::test_p2_013_topology_adjacency_and_connectivity
test_phase2_topology.py::test_p2_014_edge_sequence_continuity_check
test_phase2_topology.py::test_p2_015_opaque_records_in_a_physical_project
test_phase2_topology.py::test_p2_016_unknown_extension_fields_are_preserved_everywhere
test_phase3_editors.py::test_p3_001_app_version_is_0_3_0_from_the_single_authority
test_phase3_editors.py::test_p3_002_every_engineering_column_carries_a_unit_suffix
test_phase3_editors.py::test_p3_003_every_editable_field_has_a_tooltip_from_one_file
test_phase3_editors.py::test_p3_004_standard_and_advanced_modes_share_one_switch
test_phase3_editors.py::test_p3_005_staging_never_touches_the_committed_project
test_phase3_editors.py::test_p3_006_commit_replaces_and_discard_restores_byte_stable_state
test_phase3_editors.py::test_p3_007_invalid_edit_is_rejected_with_a_reused_phase2_code
test_phase3_editors.py::test_p3_008_add_delete_rows_and_reference_refusal
test_phase3_editors.py::test_p3_009_deleting_an_alignment_names_every_referencing_object
test_phase3_editors.py::test_p3_010_nested_vertical_profile_points_are_edited_in_place
test_phase3_editors.py::test_p3_011_reference_system_fields_are_editable_except_schema_fixed_ones
test_phase3_editors.py::test_p3_012_gradient_preview_follows_the_direction_without_mutating_data
test_phase3_editors.py::test_p3_013_curvature_preview_uses_only_the_stored_radius
test_phase3_editors.py::test_p3_014_effective_speed_is_direction_filtered_and_most_restrictive_wins
test_phase3_editors.py::test_p3_015_train_fit_classification_covers_the_three_outcomes
test_phase3_editors.py::test_p3_016_train_fit_checker_widget_is_read_only_and_uses_the_package_utility
test_phase3_editors.py::test_p3_017_schematic_is_generated_from_the_canonical_model
test_phase3_editors.py::test_p3_018_layer_control_reports_inactive_layers_without_drawing_them
test_phase3_editors.py::test_p3_019_click_surface_focuses_objects_and_marks_errors_with_text
test_phase3_editors.py::test_p3_020_sub_tabs_are_exact_and_selection_survives_a_refresh
test_phase3_editors.py::test_p3_021_the_pages_keep_the_phase2_inspection_contract
test_phase3_editors.py::test_p3_022_validation_surface_uses_only_existing_codes
test_phase3_editors.py::test_p3_023_json_import_export_stays_authoritative
test_phase3_editors.py::test_p3_024_no_engineering_calculation_in_the_ui
test_phase3_editors.py::test_p3_025_package_uses_only_the_public_ipywidgets_api
test_phase3_editors.py::test_p3_026_close_widget_tree_closes_a_real_tree_through_close
test_phase4a_route_coordinate.py::test_p4_001_compiled_network_from_reference_project
test_phase4a_route_coordinate.py::test_p4_002_declared_paths_are_read_exactly_as_declared
test_phase4a_route_coordinate.py::test_p4_003_forward_follows_the_declared_traversal
test_phase4a_route_coordinate.py::test_p4_004_reverse_reverses_order_and_complements_traversal
test_phase4a_route_coordinate.py::test_p4_005_both_directions_use_the_declared_chainage_maps
test_phase4a_route_coordinate.py::test_p4_006_track_identity_is_authoritative_and_chainage_is_derived
test_phase4a_route_coordinate.py::test_p4_007_route_distance_is_bounded_and_never_negative
test_phase4a_route_coordinate.py::test_p4_008_edge_at_resolves_every_segment_in_travel_order
test_phase4a_route_coordinate.py::test_p4_009_chainage_to_route_distance_round_trips
test_phase4a_route_coordinate.py::test_p4_010_chainage_off_the_path_is_refused_not_invented
test_phase4a_route_coordinate.py::test_p4_011_fixture_forward_and_reverse_run_zero_to_route_length
test_phase4a_route_coordinate.py::test_p4_012_fixture_edge_longer_than_its_chainage_projection
test_phase4a_route_coordinate.py::test_p4_013_fixture_opposite_oriented_chainage_map_is_honoured
test_phase4a_route_coordinate.py::test_p4_014_compiling_and_routing_never_write
test_phase4a_route_coordinate.py::test_p4_015_compiled_network_and_coordinates_are_read_only
test_phase4a_route_coordinate.py::test_p4_016_route_system_carries_no_direction_flag_or_negative_s
test_phase4a_route_coordinate.py::test_p4_017_unresolved_edge_is_reported_and_the_path_is_refused
test_phase4a_route_coordinate.py::test_p4_018_sequence_break_is_reported_and_the_path_is_refused
test_phase4a_route_coordinate.py::test_p4_019_declared_traversal_and_direction_values_are_validated
test_phase4a_route_coordinate.py::test_p4_020_missing_ids_and_empty_sequences_are_reported
test_phase4a_route_coordinate.py::test_p4_021_network_module_stays_outside_the_out_of_scope_patterns
test_phase4a_route_coordinate.py::test_p4_022_network_module_has_no_new_dependencies_and_no_cycle
test_phase4a_route_coordinate.py::test_p4_023_companion_file_declares_the_reference_paths
test_phase4a_route_coordinate.py::test_p4_024_reference_paths_run_platform_edge_to_platform_edge
test_phase4a_route_coordinate.py::test_p4_025_test_corridor_keeps_the_original_49_km_walk
test_phase4a_route_coordinate.py::test_p4_026_app_phase_names_the_current_phase
test_phase4a_route_coordinate.py::test_p4_027_reference_paths_are_entry_by_entry_reverses
test_phase4a_route_coordinate.py::test_p4_028_reference_paths_share_length_and_swap_terminals
test_phase4a_route_coordinate.py::test_p4_029_compiled_routes_traverse_the_same_edges_in_opposite_order
test_phase4a_route_coordinate.py::test_p4_030_corrected_companion_compiles_without_diagnostics
test_phase4b_geometry_along_route.py::test_p4_031_route_geometry_constructs_from_the_reference_corridor
test_phase4b_geometry_along_route.py::test_p4_032_elevation_is_the_interpolation_of_the_stored_profile
test_phase4b_geometry_along_route.py::test_p4_033_elevation_is_direction_independent
test_phase4b_geometry_along_route.py::test_p4_034_gradient_is_direction_aware
test_phase4b_geometry_along_route.py::test_p4_035_gradient_is_piecewise_constant_between_stored_points
test_phase4b_geometry_along_route.py::test_p4_036_gradient_is_zero_where_two_points_share_an_elevation
test_phase4b_geometry_along_route.py::test_p4_037_curve_radius_returns_the_stored_radius_on_curves
test_phase4b_geometry_along_route.py::test_p4_038_curve_radius_is_none_on_straights_never_a_sentinel
test_phase4b_geometry_along_route.py::test_p4_039_curve_radius_is_direction_independent
test_phase4b_geometry_along_route.py::test_p4_040_footprint_gradient_is_exact_inside_one_segment
test_phase4b_geometry_along_route.py::test_p4_041_footprint_gradient_averages_across_a_transition
test_phase4b_geometry_along_route.py::test_p4_042_footprint_gradient_refuses_a_non_positive_train_length
test_phase4b_geometry_along_route.py::test_p4_043_out_of_range_queries_raise_and_never_clamp
test_phase4b_geometry_along_route.py::test_p4_044_missing_catalogues_are_reported_and_refuse_to_answer
test_phase4b_geometry_along_route.py::test_p4_045_route_geometry_does_not_mutate_the_project
test_phase4b_geometry_along_route.py::test_p4_046_geometry_module_has_no_numeric_dependency
test_phase4b_geometry_along_route.py::test_p4_047_geometry_module_stays_outside_the_out_of_scope_patterns
test_phase4b_geometry_along_route.py::test_p4_048_phase4b_suite_is_registered_and_counted
test_phase5a_resistance.py::test_p5_001_module_exposes_the_documented_api
test_phase5a_resistance.py::test_p5_002_davis_resistance_is_the_declared_formula_in_newtons
test_phase5a_resistance.py::test_p5_003_davis_resistance_at_zero_speed_is_the_constant_term
test_phase5a_resistance.py::test_p5_004_davis_resistance_is_non_decreasing_in_speed
test_phase5a_resistance.py::test_p5_005_davis_resistance_rejects_impossible_inputs
test_phase5a_resistance.py::test_p5_006_gradient_force_of_the_frozen_hsr_mass_uphill
test_phase5a_resistance.py::test_p5_007_gradient_force_downhill_is_the_exact_negative
test_phase5a_resistance.py::test_p5_008_gradient_force_on_level_track_is_zero
test_phase5a_resistance.py::test_p5_009_gradient_force_uses_the_module_gravity_constant
test_phase5a_resistance.py::test_p5_010_gradient_force_rejects_impossible_inputs
test_phase5a_resistance.py::test_p5_011_roeckl_curve_resistance_of_the_frozen_hsr_mass
test_phase5a_resistance.py::test_p5_012_roeckl_curve_resistance_on_a_straight_is_zero
test_phase5a_resistance.py::test_p5_013_roeckl_curve_resistance_rejects_radii_at_or_below_55_m
test_phase5a_resistance.py::test_p5_014_roeckl_curve_resistance_rejects_zero_negative_and_non_finite_radii
test_phase5a_resistance.py::test_p5_015_roeckl_equivalent_gradient_is_the_permille_used_by_the_force
test_phase5a_resistance.py::test_p5_016_is_roeckl_radius_usable_is_the_applicability_predicate
test_phase5a_resistance.py::test_p5_017_total_resistance_is_the_literal_sum_of_the_three_functions
test_phase5a_resistance.py::test_p5_018_total_resistance_on_level_straight_track_is_davis_alone
test_phase5a_resistance.py::test_p5_019_total_resistance_can_be_negative_on_a_steep_downhill
test_phase5a_resistance.py::test_p5_020_physics_package_uses_the_standard_library_only
test_phase5a_resistance.py::test_p5_021_unit_discipline_of_names_and_docstrings
test_phase5a_resistance.py::test_p5_022_functions_are_pure_deterministic_and_touch_no_project
test_phase5a_resistance.py::test_p5_023_section_d_scan_after_the_allowed_list_update
test_phase5a_resistance.py::test_p5_024_phase5a_suite_is_registered_and_counted
test_phase5b_along_route.py::test_p5_025_module_exposes_the_documented_api_and_is_registered
test_phase5b_along_route.py::test_p5_026_running_resistance_forwards_to_the_stage_5a_function
test_phase5b_along_route.py::test_p5_027_radius_segments_partition_the_interval_from_the_stored_catalogue
test_phase5b_along_route.py::test_p5_028_interval_errors_use_the_delivered_conventions
test_phase5b_along_route.py::test_p5_029_level_straight_footprint_returns_exactly_zero
test_phase5b_along_route.py::test_p5_030_grade_force_is_the_footprint_gradient_in_newtons
test_phase5b_along_route.py::test_p5_031_grade_force_is_direction_aware_for_the_same_train_body
test_phase5b_along_route.py::test_p5_032_straight_footprint_costs_no_curvature_force
test_phase5b_along_route.py::test_p5_033_curve_footprint_is_the_stage_5a_single_radius_value
test_phase5b_along_route.py::test_p5_034_straddling_footprint_is_the_length_weighted_mean
test_phase5b_along_route.py::test_p5_035_curvature_is_non_negative_and_direction_independent
test_phase5b_along_route.py::test_p5_036_total_is_the_literal_sum_recomputed
test_phase5b_along_route.py::test_p5_037_total_on_level_straight_track_is_the_running_resistance_alone
test_phase5b_along_route.py::test_p5_038_total_can_be_negative_on_a_steep_synthetic_descent
test_phase5b_along_route.py::test_p5_039_errors_are_propagated_and_nothing_is_substituted
test_phase5b_along_route.py::test_p5_040_calls_are_pure_and_the_loaded_project_is_unchanged
test_phase5b_along_route.py::test_p5_041_new_module_imports_no_numeric_library
test_phase5b_along_route.py::test_p5_042_section_d_scan_and_the_registered_phase5b_table
test_phase6a_rolling_stock_model.py::test_p6_001_model_module_exists_and_exposes_the_documented_surface
test_phase6a_rolling_stock_model.py::test_p6_002_companion_file_loads_and_validates_with_no_diagnostic
test_phase6a_rolling_stock_model.py::test_p6_003_companion_declares_exactly_the_two_reference_stock_types
test_phase6a_rolling_stock_model.py::test_p6_004_hsr_stock_carries_the_frozen_reference_values
test_phase6a_rolling_stock_model.py::test_p6_005_regional_stock_carries_its_own_frozen_reference_values
test_phase6a_rolling_stock_model.py::test_p6_006_derived_si_properties_are_recomputed_from_the_stored_fields
test_phase6a_rolling_stock_model.py::test_p6_007_rejects_non_positive_static_mass
test_phase6a_rolling_stock_model.py::test_p6_008_rejects_non_positive_length
test_phase6a_rolling_stock_model.py::test_p6_009_rejects_rotating_mass_factor_below_one
test_phase6a_rolling_stock_model.py::test_p6_010_rejects_non_positive_max_speed
test_phase6a_rolling_stock_model.py::test_p6_011_rejects_non_positive_rated_power
test_phase6a_rolling_stock_model.py::test_p6_012_rejects_non_positive_max_tractive_effort
test_phase6a_rolling_stock_model.py::test_p6_013_rejects_non_positive_max_operational_acceleration
test_phase6a_rolling_stock_model.py::test_p6_014_rejects_negative_resistance_coefficients
test_phase6a_rolling_stock_model.py::test_p6_015_rejects_non_positive_service_braking_reference
test_phase6a_rolling_stock_model.py::test_p6_016_rejects_non_positive_etcs_reference
test_phase6a_rolling_stock_model.py::test_p6_017_rejects_unrecognised_unit_and_model_values
test_phase6a_rolling_stock_model.py::test_p6_018_rejects_nan_and_infinities_in_numeric_fields
test_phase6a_rolling_stock_model.py::test_p6_019_effort_characteristic_rules
test_phase6a_rolling_stock_model.py::test_p6_020_unknown_extension_fields_survive_every_level
test_phase6a_rolling_stock_model.py::test_p6_021_all_four_reader_forms_are_equal_and_do_not_mutate_the_input
test_phase6a_rolling_stock_model.py::test_p6_022_loading_does_not_change_the_frozen_project_or_companion
test_phase6a_rolling_stock_model.py::test_p6_023_new_modules_import_no_numeric_library_and_no_forbidden_module
test_phase6a_rolling_stock_model.py::test_p6_024_new_modules_carry_no_forbidden_section_d_token
test_phase6b_rolling_stock_ui.py::test_p6_025_effort_module_exists_and_exposes_the_documented_function
test_phase6b_rolling_stock_ui.py::test_p6_026_effort_at_zero_speed_is_the_starting_effort
test_phase6b_rolling_stock_ui.py::test_p6_027_effort_is_flat_at_and_below_the_transition_speed
test_phase6b_rolling_stock_ui.py::test_p6_028_effort_above_the_transition_follows_the_power_branch
test_phase6b_rolling_stock_ui.py::test_p6_029_effort_never_exceeds_the_starting_effort
test_phase6b_rolling_stock_ui.py::test_p6_030_transition_speed_of_the_frozen_pair_and_of_the_hsr_stock
test_phase6b_rolling_stock_ui.py::test_p6_031_effort_rejects_unusable_arguments_naming_them
test_phase6b_rolling_stock_ui.py::test_p6_032_series_module_exists_and_exposes_the_two_functions
test_phase6b_rolling_stock_ui.py::test_p6_033_effort_series_is_ordered_and_ends_at_the_maximum_speed
test_phase6b_rolling_stock_ui.py::test_p6_034_effort_series_samples_equal_the_primitive_called_here
test_phase6b_rolling_stock_ui.py::test_p6_035_resistance_series_is_ordered_and_ends_at_the_maximum_speed
test_phase6b_rolling_stock_ui.py::test_p6_036_resistance_series_samples_equal_the_primitive_called_here
test_phase6b_rolling_stock_ui.py::test_p6_037_series_reject_a_non_positive_step_and_always_have_two_points
test_phase6b_rolling_stock_ui.py::test_p6_038_page_exists_is_functional_and_is_wired_into_the_shell
test_phase6b_rolling_stock_ui.py::test_p6_039_rolling_stock_left_the_placeholder_set_and_six_remain
test_phase6b_rolling_stock_ui.py::test_p6_040_page_renders_every_stored_parameter_of_both_stock_types
test_phase6b_rolling_stock_ui.py::test_p6_041_traction_sub_tab_plot_comes_from_the_effort_series
test_phase6b_rolling_stock_ui.py::test_p6_042_resistance_sub_tab_plot_comes_from_the_resistance_series
test_phase6b_rolling_stock_ui.py::test_p6_043_page_has_no_editable_widget_and_no_draft_call
test_phase6b_rolling_stock_ui.py::test_p6_044_new_modules_import_no_numeric_library
test_phase6b_rolling_stock_ui.py::test_p6_045_new_modules_carry_no_forbidden_section_d_token
test_phase6b_rolling_stock_ui.py::test_p6_046_project_hash_and_both_companions_survive_every_operation
test_phase6b_rolling_stock_ui.py::test_p6_047_the_nine_earlier_tables_keep_their_rows_and_only_the_declared_changes
test_phase6b_rolling_stock_ui.py::test_p6_048_phase6b_suite_is_registered_and_counted
test_project_io.py::test_empty_upload_is_reported_as_application_error
test_project_io.py::test_export_document_shape_uses_canonical_section_order
test_project_io.py::test_export_filename_reflects_project_name_and_id
test_project_io.py::test_export_metadata_is_opt_in_and_does_not_break_roundtrip
test_project_io.py::test_export_preserves_stored_numeric_values_and_types
test_project_io.py::test_hash_is_order_independent_and_normalises_numbers
test_project_io.py::test_import_helpers_do_not_use_unsafe_deserialization
test_project_io.py::test_p1_002_export_import_roundtrip_preserves_data[example]
test_project_io.py::test_p1_002_export_import_roundtrip_preserves_data[template]
test_project_io.py::test_p1_003_equivalent_project_produces_same_canonical_hash_after_roundtrip
test_project_io.py::test_p1_011_imported_json_content_is_never_executed
test_project_io.py::test_roundtrip_through_files_and_helpers
test_project_io.py::test_upload_payload_shapes_are_supported
test_ui_shell.py::test_audit_page_renders_and_filters_diagnostics
test_ui_shell.py::test_controller_listeners_refresh_the_shell_without_manual_calls
test_ui_shell.py::test_direction_buttons_drive_the_controller_and_labels
test_ui_shell.py::test_header_shows_versions_and_status_text
test_ui_shell.py::test_launch_app_builds_and_can_write_a_static_snapshot
test_ui_shell.py::test_placeholder_pages_do_not_implement_engineering_calculations
test_ui_shell.py::test_project_page_edits_are_written_through_the_controller
test_ui_shell.py::test_project_page_reimport_updates_every_widget
test_ui_shell.py::test_shell_builds_all_navigation_pages
test_validation.py::test_chainage_bounds_are_accepted_when_increasing
test_validation.py::test_display_unit_warning_is_not_an_error
test_validation.py::test_documented_example_project_is_valid
test_validation.py::test_duplicate_identifiers_are_reported_per_object_type
test_validation.py::test_extra_unknown_fields_are_preserved
test_validation.py::test_identical_forward_and_reverse_direction_warns
test_validation.py::test_malformed_container_is_reported_and_defaulted
test_validation.py::test_malformed_field_type_is_reported_once_and_not_repaired_silently
test_validation.py::test_missing_container_is_created_with_default_and_info
test_validation.py::test_missing_direction_is_invalid
test_validation.py::test_non_object_root_is_reported
test_validation.py::test_p1_001_new_project_is_valid
test_validation.py::test_p1_004_missing_schema_version_is_invalid
test_validation.py::test_p1_005_unsupported_schema_version_is_invalid
test_validation.py::test_p1_006_project_identity_is_required[blank-id]
test_validation.py::test_p1_006_project_identity_is_required[empty-id]
test_validation.py::test_p1_006_project_identity_is_required[missing-id]
test_validation.py::test_p1_006_project_identity_is_required[missing-name]
test_validation.py::test_p1_007_chainage_end_not_greater_than_start_is_invalid[0.0-0.0-equal]
test_validation.py::test_p1_007_chainage_end_not_greater_than_start_is_invalid[10.0-5.0-reversed]
test_validation.py::test_p1_007_chainage_end_not_greater_than_start_is_invalid[100.0-0.0-reversed]
test_validation.py::test_p1_008_invalid_direction_enumeration_is_invalid
test_validation.py::test_p1_012_diagnostics_have_stable_structure
test_validation.py::test_preserved_containers_get_info_only
test_validation.py::test_schema_version_of_wrong_type_is_invalid
test_validation.py::test_undecodable_upload_bytes_are_reported
test_validation.py::test_unparseable_json_text_is_reported
```
