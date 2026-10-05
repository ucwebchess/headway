# GRR-01 INVENTORY — canonical counts

> **Canonical source for GRR-01 object counts.** Every count quoted in `README.md`,
> `VERIFICATION.md`, `docs/GRR-01 CHANGE CONTROL.md` and any run log (`result.txt`) is
> quoted from this file. Numbers here are read back from `examples/GRR-01.json` through
> the delivered application (`typed_inventory_rows()` / `registry_rows()`), not restated
> from memory. Reviewer check:
> `python3 -c "from railway_headway_sim import ProjectController; from railway_headway_sim.infrastructure.grr_fixtures import build_grr01_document as b; c=ProjectController(); c.import_json_data(b()); c.validate_project(); print(c.typed_inventory_rows())"`.

## 1. The canonical count string

```text
1/2/7/1/13/8/50/59/4/9/14/9 = 177
```

Expanded, in catalogue order:

| # | Catalogue | Count |
|---|---|---|
| 1 | `alignments` | 1 |
| 2 | `track_groups` | 2 |
| 3 | `horizontal_geometry` | 7 |
| 4 | `vertical_profiles` | 1 |
| 5 | `vertical_profiles[*].points` (vertical profile points) | 13 |
| 6 | `speed_restrictions` | 8 |
| 7 | `nodes` | 50 |
| 8 | `tracks` | 59 |
| 9 | `stations` | 4 |
| 10 | `platforms` | 9 |
| 11 | `stopping_marks` | 14 |
| 12 | `observation_points` | 9 |

Arithmetic: 1 + 2 + 7 + 1 + 13 + 8 + 50 + 59 + 4 + 9 + 14 + 9 = **177** registered
engineering objects. (A shorter grouping is sometimes quoted as
`1 alignment + 2 track groups + 7 geometry sections + 1 vertical profile + 13 profile
points + 8 speed restrictions + 50 nodes + 59 tracks + 4 stations + 9 platforms +
14 stopping marks + 9 observation points = 177`.)

⚠️ The string `1/2/7/13/8/50/59/4/9/14/9` (vertical profile omitted) sums to **176** and is
**wrong**; it must not be quoted. Likewise any string whose terms do not sum to its stated
total is wrong by construction.

## 2. Typed catalogues — canonical count is 12

**12 typed catalogues.** The canonical phrasing is:

> GRR-01 registers **177 objects across 12 typed catalogues**: the **11 catalogue keys** of
> the infrastructure layer object (`alignments`, `track_groups`, `horizontal_geometry`,
> `vertical_profiles`, `speed_restrictions`, `nodes`, `tracks`, `stations`, `platforms`,
> `stopping_marks`, `observation_points`) **plus the vertical profile points nested inside
> `vertical_profiles`** (registry object type `vertical_profile_point`).

"11" alone is ambiguous (it is the number of *layer catalogue keys*, and the JSON Schema
records exactly that list as `x-phase2-typed-catalogues` with 11 entries); "12" is the
number of *typed catalogues* and the number of *registry object types*. Use 12 wherever
object counts or registry size are discussed, and say "11 catalogue keys" only when talking
about the layer object's keys or the schema list.

Registered object types (12, `registry_rows()` order): `alignment`, `track_group`,
`horizontal_geometry_section`, `vertical_profile`, `vertical_profile_point`,
`speed_restriction`, `node`, `track`, `station`, `platform`, `stopping_mark`,
`observation_point`.

Opaque Phase-1 catalogues (6, preserved verbatim, all empty in GRR-01): `chainages`,
`speed_profiles`, `gradients`, `curves`, `tunnels`, `bridges`.

## 3. Regional inventory

| Region | Nodes | Tracks/edges |
|---|---|---|
| Open line | 0 (see GRR-AMD-002) | 8 |
| Alpha | 6 | 4 |
| Central | 18 | 23 |
| XC-24 | 8 | 8 |
| Valley | 12 | 12 |
| Delta | 6 | 4 |
| **Total** | **50** | **59** |

Regional membership is declared explicitly in
`railway_headway_sim/infrastructure/grr_fixtures.py` (`REGION_NODE_IDS`,
`REGION_TRACK_IDS`) — never inferred from ID prefixes.

## 4. Project identity and recorded amendments

| Item | Value |
|---|---|
| Project id | `PRJ-GRR-01` |
| Project type / data status / engineering status | `REFERENCE_TEST_PROJECT` / `SYNTHETIC` / `REFERENCE_ASSUMPTIONS` |
| Layer | `LYR-MAIN` (single layer, `physical_mode = PHYSICAL`) |
| Alignment | `ALN-MAIN`, 0.000 → 50.000 km |
| Stations | `STA-ALPHA`, `STA-CEN`, `STA-VAL`, `STA-DELTA` |
| Amendments recorded in `provenance.approved_amendments` | `GRR-AMD-001`, `GRR-AMD-003`, `GRR-AMD-004` |
| Amendment documented but **not** in the JSON | `GRR-AMD-002` (table-only correction; explanation in `docs/GRR-01 CHANGE CONTROL.md` §3) |

## 5. Canonical replacement block for any run log (`result.txt`)

The reviewer's `result.txt` is **not part of the delivered tree** (see finding F14 in
`docs/PHASE-2R RECONCILIATION REPORT.md`), so it could not be edited here. Wherever a run
log prints an inventory count line, replace it with these canonical lines verbatim:

```text
inventory : 1/2/7/1/13/8/50/59/4/9/14/9 = 177 registered engineering objects
catalogues: 12 typed (11 layer catalogue keys + vertical profile points), 6 opaque Phase-1
```

If the log also quotes test totals, they must equal `docs/TEST_INVENTORY.md`
(canonical decomposition there: `66 + 30 + 5 = 101` collected items).
