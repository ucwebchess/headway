# GRR-01 Part A — CHANGE CONTROL

**Scope** — the frozen GRR-01 Part-A physical inventory (one alignment 0.000–50.000 km,
50 topology nodes, 59 track edges, 4 stations, 9 platforms, 14 stopping marks,
9 observation points) as reconstructed in Phase 2 and delivered as
`examples/GRR-01.json`.

**Rules applied**

1. The frozen GRR-01 specification outranks the Phase-2 prompt. A contradiction is
   **reported**, never silently absorbed.
2. Any change to a frozen value or count requires an entry here *before* it is applied,
   plus a record in `provenance.approved_amendments` of the delivered document.
3. Object counts may only change through an approved amendment; the count-preserving
   amendments below therefore leave all **12 typed catalogues** unchanged (counts quoted
   from `docs/GRR-01 INVENTORY.md`).
4. `docs/GRR-01_FROZEN_PHYSICAL_v1.0.json` keeps the **pre-amendment** values as evidence.
   (GRR-AMD-002 is a table-only correction and is therefore documented here but *not*
   listed in `provenance.approved_amendments`; GRR-AMD-001 / -003 / -004 are data
   amendments and are listed there and asserted by `TEST P2-REG-G005`.)

---

## 0. Canonical object counts

Counts in this file are quoted from `docs/GRR-01 INVENTORY.md`; the canonical string is
**`1/2/7/1/13/8/50/59/4/9/14/9 = 177` registered engineering objects across 12 typed
catalogues**. (A run-log string that omits the vertical profile —
`1/2/7/13/8/50/59/4/9/14/9` — sums to 176 and is wrong.)

## 1. Frozen inventory (delivered object counts)

| Catalogue | Frozen count | Observed |
|---|---|---|
| alignments | 1 | 1 |
| track_groups | 2 | 2 |
| horizontal_geometry | 7 | 7 |
| vertical_profile_points | 13 | 13 |
| speed_restrictions | 8 | 8 |
| nodes | 50 | 50 |
| tracks | 59 | 59 |
| stations | 4 | 4 |
| platforms | 9 | 9 |
| stopping_marks | 14 | 14 |
| observation_points | 9 | 9 |

Registry total: **177 registered engineering objects**
across 12 typed catalogues (the 11 layer catalogue keys plus the vertical profile points nested
in `vertical_profiles`). All registered IDs must be globally unique; see
`tests/test_phase2_grr_regressions.py::test_p2_reg_g003_global_registry_uniqueness_and_draft_guard`.

## 2. Regional inventory (declared vs. observed)

| Region | Declared nodes | Declared edges | Observed nodes | Observed edges |
|---|---|---|---|---|
| Alpha | 6 | 4 | 6 | 4 |
| Central | 18 | 23 | 18 | 23 |
| XC-24 | 8 | 8 | 8 | 8 |
| Valley | 12 | 12 | 12 | 12 |
| Delta | 6 | 4 | 6 | 4 |
| Open line | 0 | 8 | 0 | 8 |

Regional membership is declared explicitly in
`railway_headway_sim/infrastructure/grr_fixtures.py` (`REGION_NODE_IDS`,
`REGION_TRACK_IDS`) — the region is **not** inferred from ID prefixes — and the two
maps must partition the node and track catalogues exactly.

> **GRR-AMD-002 (documentation correction, no data change).** The frozen regional table
> lists nodes for Alpha / Central / XC-24 / Valley / Delta only (6 / 18 / 8 / 12 / 6 =
> 50). The **open line** region therefore holds 0 *counted* nodes while carrying 8 edges;
> all its endpoints are counted inside the regional stations. This is recorded here so the
> tables sum to the frozen totals; no node, edge or count was changed.

## 3. Approved amendments

> **GRR-AMD-002 — no amendment entry by design (Phase-2R, F8).** *GRR-AMD-002 corrects a
> table row in the change-control record (open-line node row = 0). It changes no project
> data. It is intentionally absent from `provenance.approved_amendments` in
> `examples/GRR-01.json` and from the frozen evidence file. The numbering gap is deliberate,
> not an omission.*
>
> Evidence that the gap is intentional rather than lost: the delivered JSON and the frozen
> evidence file both record exactly the same three data amendments — GRR-AMD-001,
> GRR-AMD-003, GRR-AMD-004 — asserted by `TEST P2-REG-G005`, and
> `railway_headway_sim/infrastructure/grr_fixtures.py::APPROVED_AMENDMENTS` contains those
> same three entries. GRR-AMD-002 exists only as the record correction in §2 of this file.

### GRR-AMD-001 — Valley P1 reverse stopping mark 220.0 → 250.0 m

* Object: `STOP-V-P1-R` (`PLT-VAL-P1` on `TR-V-P1`), field `position_m`.
* Frozen value: 220.0 m · Amended value: **250.0 m**.
* Counts before/after: unchanged (stopping marks 14; all other catalogues unchanged).
* Evidence: `docs/GRR-01_FROZEN_PHYSICAL_v1.0.json` keeps 220.0 m and omits
  `provenance.approved_amendments`; `examples/GRR-01.json` records the amendment.
* Affected tests: both values are physically consistent (`GRR-STATIC-VP1-FWD-HSR` uses the
  front-position input 480 m, not the mark); `TEST P2-024` checks the amended mark
  (250.0 m) and `TEST P2-REG-G005` asserts the frozen file's 220.0 m.

### GRR-AMD-003 — Delta region connectivity (6 nodes / 4 edges)

* **Contradiction found:** the frozen Delta table declares 6 nodes and 4 edges. A connected
  6-node region requires at least 5 edges, and internal-only attachment would leave one
  Delta node with no incident edge at all (isolated node ⇒ `VAL-TOPO-007`, and an invented
  edge ⇒ count violation).
* **Exact connectivity problem:** with `N-DEL-W`, `N-DEL-THR`, `N-DEL-J`, `N-DEL-P1-W`,
  `N-DEL-P1-E`, `N-DEL-E2` and 4 Delta-internal edges
  (`TR-D-W-THR`, `TR-D-THR-J`, `TR-D-J-P1W`, `TR-D-P1`), the eastern line end `N-DEL-E2`
  has degree 0.
* **Smallest proposed correction (adopted):** attach `N-DEL-E2` to the *neighbouring
  open-line* edge `TR-O-VAL-DEL-ML2` (`N-VAL-E → N-DEL-E2`). The open-line region keeps
  its 8 declared edges; the Delta region keeps its 6 nodes and 4 internal edges; no node or
  edge is added or removed.
* Counts before/after: **identical** — nodes 50, tracks 59, Delta 6 nodes / 4 edges,
  Open line 8 edges. Affected tests: none (the correction is inside the frozen counts).
* Consequence: the network is one connected component of 50 nodes / 59 edges
  (open-line ML2 reaches the Delta line end; the passenger route ends at the Delta P1
  buffer stop `N-DEL-P1-E`, as required by the frozen corridor list).

### GRR-AMD-004 — Valley P2 platform usable range (100.0 – 500.0 m)

* Object: `PLT-VAL-P2` on `TR-V-P2`, fields `usable_start_m` / `usable_end_m`
  (delivered: 100.0 / 500.0 m, `usable_length_m` 400.0 m).
* **Why:** the frozen Valley P2 benchmark evaluates the reference HSR train length from
  front 200.0 m against the edge and requires the **500.0 m eastern boundary** to be the
  platform boundary itself (rear 402.0 m ⇒ 98.0 m clearance). The usable range is therefore
  recorded so that both the critical boundary and the clearance are computed **from platform
  data**, not from a hard-coded constant (`TEST P2-022` asserts
  `result.critical_boundary_m == 500.0`).
* Counts before/after: unchanged (platforms 9; every other catalogue unchanged).
* Evidence: `TEST P2-REG-G005` asserts the delivered range and asserts that the frozen
  evidence file carries the same platform range (the frozen file differs from the delivery
  file only in `STOP-V-P1-R` and `provenance.approved_amendments`).

## 4. Section BA contradiction scan (machine-run, read-only)

`railway_headway_sim/infrastructure/grr_audit.py` re-reads the frozen fixture and checks it
against every declared GRR-01 statement. Run it with:

```bash
python3 -c "from railway_headway_sim.infrastructure import grr_audit; print(grr_audit.format_findings())"
```

Result of the delivered fixture — **13 checks, 0 unresolved contradictions**:

- `BA-01` **OK** — Frozen object counts: All 11 declared GRR-01 object counts match exactly.
- `BA-02` **OK** — Regional inventory (nodes / edges, sum = 50 / 59): Every region matches its declared node/edge count and the regions partition the catalogues exactly.
- `BA-03` **OK** — Node incidence (no invented or dangling nodes): Every one of the 50 declared nodes is incident to at least one track and every track endpoint resolves.
- `BA-04` **OK** — Physical connectivity (all 50 nodes in one component): The whole GRR-01 network is one connected component and all 15 mandatory corridors are traversable.
- `BA-05` **OK** — Mandated edge/node names (Section AD), station identifiers and track-group directions: Final Central east crossing names are used, no provisional name survives, all four station IDs match and both track groups declare their frozen normal direction (TG-ML1 FORWARD, TG-ML2 REVERSE).
- `BA-06` **OK** — Station / platform / stopping-mark reference integrity: All station, platform, track and stopping-mark references resolve and every range is inside its track.
- `BA-07` **OK** — Geometry coverage (continuous 0-50 km, vertical profile strictly increasing): Horizontal geometry covers 0.000-50.000 km without gaps or overlaps; the vertical profile is strictly increasing and inside the alignment.
- `BA-08` **OK** — Speed-restriction composition (7 permanent BOTH + 1 reverse 42-44 km @ 240 km/h): Speed restrictions match the declared composition exactly.
- `BA-09` **OK** — Every track endpoint is a declared, counted node (no invented nodes on load): The 59 edges reference exactly the 50 declared nodes; the endpoints that the frozen regional tables count implicitly are declared explicitly.
- `BA-10` **OK** — Global registry uniqueness across all typed catalogues: All 177 registered engineering object IDs are globally unique across 12 typed catalogues (profiles and their points included).
- `BA-11` **OK** — Frozen static benchmarks (5) reproduced by the static footprint utility: All five frozen static benchmarks reproduce exactly (12 m / 13 m / 12 m / 78 m / 98 m).
- `BA-12` **OK** — Section D out-of-scope guard (no simulated results in the reference project): The reference project contains static physical data only: no headway, blocking, occupation, timetable or capacity result.
- `BA-13` **OK** — Every track chainage map is LINEAR and increases inside the alignment: All 59 track chainage maps are LINEAR, strictly increasing and inside 0.000-50.000 km.

## 5. Static benchmarks (frozen values, reproduced by the static-footprint utility)

| Benchmark | Track | Front (m) | Length (m) | Traversal | Critical boundary (m) | Rear (m) | Result |
|---|---|---|---|---|---|---|---|
| GRR-STATIC-P2-FWD-HSR | TR-C-P2 | 420.0 | 202.0 | WITH_EDGE | 230.0 | 218.0 | 12 m rear infringement |
| GRR-STATIC-P2-FWD-HSR-PLUS25 | TR-C-P2 | 445.0 | 202.0 | WITH_EDGE | 230.0 | 243.0 | 13 m rear clearance |
| GRR-STATIC-P1-REV-HSR | TR-C-P1 | 170.0 | 202.0 | AGAINST_EDGE | 360.0 | 372.0 | 12 m rear infringement |
| GRR-STATIC-VP1-FWD-HSR | TR-V-P1 | 480.0 | 202.0 | WITH_EDGE | 200.0 | 278.0 | 78 m rear clearance |
| GRR-STATIC-VP2-REV-HSR | TR-V-P2 | 200.0 | 202.0 | AGAINST_EDGE | 500.0 | 402.0 | 98 m rear clearance |

Reference train lengths used by the fixtures/tests: HSR 202 m,
REG 160 m. These are **fixture evaluation lengths**, never project
data and never train dynamics.

## 6. Change log

| Date | Entry | Author | Effect |
|---|---|---|---|
| 2026-10-04 | **no GRR-01 data change** (Phase 6B = rolling-stock UI page) | Phase-6B delivery | Application version 0.8.0 → **0.9.0** (minor: a new engineering surface and a new functional page). Adds `railway_headway_sim/physics/tractive_effort.py` (the frozen simplified `FORCE_THEN_POWER_LIMITED` effort — `tractive_effort_n` with `transition_speed_kmh`, force-limited up to the transition speed and power-limited above it, capped by the starting effort; no numeric library), `railway_headway_sim/physics/rolling_stock_series.py` (the two sampled `(speed_kmh, force_n)` series `tractive_effort_series_n` / `running_resistance_series_n`, swept from 0.0 to the stock's own `max_speed_kmh` inclusive and evaluated on the stock they are given) and the **read-only** `railway_headway_sim/ui/rolling_stock_page.py` (Overview · Traction · Resistance · Braking over the delivered catalogue; no draft mechanism, no editable widget, no engineering computation in a callback). No motion, no trajectory, no acceleration, no integration and no time step exists in any of them. The rolling stock itself stays exactly where Phase 6A put it: the companion file `examples/GRR-01-rolling-stock.json` (`6b03e36f…`, 4,148 bytes) is **byte-identical**, and no rolling-stock key was added to the project. **No GRR-01 data changes**: `examples/GRR-01.json` (`ad0a2626…`, 57,040 bytes on disk, still `train_paths.paths == []` and still `rolling_stock.vehicles == []`), the frozen evidence file (`9348158d…`), `schema/project_schema_v1.0.json` (`1a52b73b…`, still schema 1.0), `example_project.json` (`a3649209…`) and the companion file `examples/GRR-01-paths.json` (`c62c3ee6…`) are byte-identical, and the canonical project hash (`5189aaa2340c1702…`) is unchanged. No amendment entry (GRR-AMD-005 or later) is added. |
| 2026-02-01 | GRR-AMD-001 (`STOP-V-P1-R` 220.0 → 250.0 m) | Phase-2 reconstruction | Delivery value; evidence kept in the frozen file |
| 2026-02-01 | GRR-AMD-002 (open-line node row documented as 0) | Phase-2 reconstruction | Documentation only |
| 2026-02-01 | GRR-AMD-003 (Delta line-end attachment) | Phase-2 reconstruction | Count-preserving connectivity fix |
| 2026-02-01 | GRR-AMD-004 (`PLT-VAL-P2` usable range 100.0 – 500.0 m) | Phase-2 reconstruction | Frozen Valley P2 boundary reproduced from platform data |
| 2026-10-03 | **no GRR-01 data change** (Phase 3 = infrastructure UI) | Phase-3 delivery | Application version 0.2.0 → 0.3.0 only. `examples/GRR-01.json` (`ad0a2626…`), the frozen evidence file (`9348158d…`) and the canonical hash (`5189aaa2340c1702…`) are unchanged; no amendment entry is added. The UI editors write only through the `APP-EDIT-002` draft mechanism and never touch the reference files. |
| 2026-10-04 | **no GRR-01 data change** (Phase 6A = rolling-stock model) | Phase-6A delivery | Application version 0.7.0 → **0.8.0** (minor: a new engineering surface). Adds `railway_headway_sim/models/rolling_stock.py` (the typed rolling-stock catalogue, its four enumerations, the seven read-only SI properties, `RollingStockError` and `load_rolling_stock_catalogue`) and `railway_headway_sim/validation/rolling_stock_validation.py` (`validate_rolling_stock_catalogue` / `validate_rolling_stock`; six additive codes `VAL-RS-001…006`, category `ROLLING_STOCK`), plus the **new companion file** `examples/GRR-01-rolling-stock.json` (`6b03e36f…`, 4,148 bytes, `document_kind` `ROLLING_STOCK_CATALOGUE`): a document of its own kind, holding the reference railway's two stock types `RS-HSR320` / `RS-REG200`. The companion file quotes the frozen project's `project_file_sha256` (`ad0a2626…`) and `project_canonical_hash` (`5189aaa2340c1702…`) as metadata only. **No GRR-01 data changes**: `examples/GRR-01.json` (`ad0a2626…`, 57,040 bytes on disk, still `train_paths.paths == []` and still `rolling_stock.vehicles == []` — no rolling-stock key was added to the project), the frozen evidence file (`9348158d…`), `schema/project_schema_v1.0.json` (`1a52b73b…`, still schema 1.0), `example_project.json` (`a3649209…`) and the companion file `examples/GRR-01-paths.json` (`c62c3ee6…`) are byte-identical, and the canonical project hash (`5189aaa2340c1702…`) is unchanged. No amendment entry (GRR-AMD-005 or later) is added. |
| 2026-10-04 | **no GRR-01 data change** (Phase 5B = along-route resistance) | Phase-5B delivery | Application version 0.6.0 → **0.7.0** (minor: a new engineering surface). Adds `railway_headway_sim/physics/along_route.py` — `davis_resistance_at_n`, `gradient_force_at_n`, `curve_resistance_at_n`, `total_resistance_at_n`: the Phase-5A resistance utilities evaluated read-only along a compiled route at a caller-given route distance `s` [m] and speed [km/h] for a caller-given mass [kg] and train length [m], the curve term length-weighted over the footprint — plus the additive, purely geometric `RouteGeometry.curve_radius_segments_in(s_start_m, s_end_m)`. No stored key, value, count or rule changed; no new diagnostic code. **No GRR-01 data changes**: `examples/GRR-01.json` (`ad0a2626…`, 57,040 bytes on disk, still `train_paths.paths == []`), the frozen evidence file (`9348158d…`), `schema/project_schema_v1.0.json` (`1a52b73b…`), `example_project.json` (`a3649209…`) and the companion file `examples/GRR-01-paths.json` (`c62c3ee6…`) are byte-identical, and the canonical project hash (`5189aaa2340c1702…`) is unchanged. No amendment entry (GRR-AMD-005 or later) is added. |
| 2026-10-03 | **no GRR-01 data change** (Phase 5A = resistance and force utilities) | Phase-5A delivery | Application version 0.5.0 → **0.6.0** (minor: a new engineering surface). Adds `railway_headway_sim/physics/` (`__init__.py` + `resistance.py`): the pure Davis running resistance, the signed gradient force, the Roeckl curve resistance and their literal sum, plus the two Roeckl applicability helpers — plain numbers in, newtons out, no project, no route, no rolling stock, no motion and no time. The Section-D scan was updated as a declared adaptation (the five tokens `Davis`, `Roeckl`, `rolling resistance`, `curve resistance`, `gradient force` moved to an allowed list, physics module only). **No GRR-01 data changes**: `examples/GRR-01.json` (`ad0a2626…`, still `train_paths.paths == []`), the frozen evidence file (`9348158d…`), `schema/project_schema_v1.0.json` (`1a52b73b…`), `example_project.json` (`a3649209…`) and the companion file `examples/GRR-01-paths.json` (`c62c3ee6…`) are byte-identical, and the canonical project hash (`5189aaa2340c1702…`) is unchanged. No amendment entry (GRR-AMD-005 or later) is added. |
| 2026-10-03 | **no GRR-01 data change** (Phase 4B = geometry along route) | Phase-4B delivery | Application version 0.4.2 → **0.5.0** (minor: a new engineering surface). Adds `railway_headway_sim/infrastructure/geometry_along_route.py` (`RouteGeometry`: elevation [m], gradient [permille] signed by the direction of travel, stored curve radius [m] or `None`, footprint-averaged gradient [permille]), read from the frozen project's own `vertical_profiles` (`VP-MAIN`) and `horizontal_geometry` (`HGR-01 … HGR-07`) catalogues. **No GRR-01 data changes**: `examples/GRR-01.json` (`ad0a2626…`, 57,040 bytes on disk, still `train_paths.paths == []`; earlier §§6 rows write 57,039 bytes for the same unchanged file and are left as written), the frozen evidence file (`9348158d…`), `schema/project_schema_v1.0.json` (`1a52b73b…`), `example_project.json` (`a3649209…`) and the companion file `examples/GRR-01-paths.json` (`c62c3ee6…`) are byte-identical, and the canonical project hash (`5189aaa2340c1702…`) is unchanged. No amendment entry (GRR-AMD-005 or later) is added. |
| 2026-10-03 | **no GRR-01 data change** (Phase-4A correction #2 = the companion file's two declared paths become one physical corridor, run in opposite directions) | Phase-4A correction #2 | Application version 0.4.1 → **0.4.2** (patch). Rewrites `examples/GRR-01-paths.json` (`d9099b79…` → `c62c3ee6…`) so `PATH-H1-F` and `PATH-H1-R` are exact reverses of each other (same 14 edge entries, complementary traversals, equal 47 400.0 m, swapped terminals); the corridor is selected by a deterministic rule stated in the file's own `notes`. **No GRR-01 data changes**: `examples/GRR-01.json` (`ad0a2626…`) is byte-identical and still declares `train_paths.paths == []`, as are the frozen evidence file (`9348158d…`), `schema/project_schema_v1.0.json` (`1a52b73b…`) and `example_project.json` (`a3649209…`); the canonical project hash (`5189aaa2340c1702…`) is unchanged. No amendment entry (GRR-AMD-005 or later) is added. |
| 2026-10-03 | **no GRR-01 data change** (Phase-4A correction 0.4.1 = declared-paths companion file) | Phase-4A correction | Application version 0.4.0 → **0.4.1**. Adds the companion file `examples/GRR-01-paths.json`, which carries the reference railway's declared paths `PATH-H1-F` / `PATH-H1-R`; **no GRR-01 data changes** — `examples/GRR-01.json` (`ad0a2626…`) still declares `train_paths.paths == []` and remains byte-identical, as do the frozen evidence file (`9348158d…`), `schema/project_schema_v1.0.json` (`1a52b73b…`) and `example_project.json` (`a3649209…`), and the canonical project hash (`5189aaa2340c1702…`) is unchanged. No amendment entry (GRR-AMD-005 or later) is added. |
| 2026-10-03 | **no GRR-01 data change** (Phase 4A = compiled network and route coordinates) | Phase-4A delivery | Application version 0.3.1 → **0.4.0** only; no project key, value, count or rule changed. `examples/GRR-01.json` (`ad0a2626…`), the frozen evidence file (`9348158d…`), `schema/project_schema_v1.0.json` (`1a52b73b…`) and `example_project.json` (`a3649209…`) were re-verified **unchanged**, and the canonical project hash (`5189aaa2340c1702…`) is unchanged; no amendment entry is added. Phase 4A reads the reference project read-only. Its declared train paths H1-F/H1-R are *test-supplied data* in the Phase-4A interchange form (`{"id", "edges": [{"edge_id", "traversal"}]}`): the frozen project itself still declares `train_paths.paths == []`, and no train path was written into any GRR-01 file, into the frozen evidence file or into `example_project.json`. |
| 2026-10-03 | **no GRR-01 data change** (Phase-3 bugfix 0.3.1 = `ipywidgets` public-API compatibility) | Phase-3 bugfix | Application version 0.3.0 → 0.3.1 only; no project key, value, count or rule changed. `examples/GRR-01.json` (`ad0a2626…`), the frozen evidence file (`9348158d…`) and the canonical hash (`5189aaa2340c1702…`) were re-verified **unchanged** after the fix; no amendment entry is added. The fix touches resource management in `ui/table_editor.py` only and reads/writes no project data. |
