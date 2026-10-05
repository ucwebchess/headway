# PHASE-2R — EVIDENCE RECONCILIATION & CLOSURE REPORT

**Stage:** Phase-2R — documentation-only reconciliation. No Phase-2 engineering was re-opened.
**Result:** F1–F5, F8–F12 closed; F6 and F13 closed with correction; F14 closed by creating the
missing file from a real capture; F7 carried forward as a declared residual (owner decision);
**5 new findings raised** (F15–F19), of which F16 is resolved by correction and F15/F17/F18/F19
are reported and left open by rule. Nothing was repaired silently.

**Hard-rule compliance (verified, not asserted)**

| Rule | Verification | Result |
|---|---|---|
| No change to `railway_headway_sim/` | SHA-256 of all 54 package files before/after Phase-2R | **0 files changed** |
| No change to `examples/GRR-01.json` | file SHA-256 `ad0a26265d4e072a…`; canonical project hash `5189aaa2340c1702…` | **unchanged** |
| No change to `docs/GRR-01_FROZEN_PHYSICAL_v1.0.json` | file SHA-256 `9348158d7b28942f…` | **unchanged** |
| No change to `schema/project_schema_v1.0.json` | file SHA-256 `1a52b73b55875061…` | **unchanged** |
| No test added, removed or renamed | `docs/TEST_INVENTORY.md` collects 15 test modules, 101 items, identical node ids to the Phase-2 delivery | **unchanged** |
| No packaging/dependency changed | no manifest added; install line unchanged | **unchanged** |
| Phase 3 not started | no Phase-3 artefact exists | **n/a** |

---

## 1. Finding-by-finding closure

| # | Finding (short) | Status | Closing artefact | Notes |
|---|---|---|---|---|
| F1 | Test totals did not reconcile (99 vs 101 vs 66+30+5) | **CLOSED** | `build_test_inventory.py`, `docs/TEST_INVENTORY.md`, README §Run locally, `VERIFICATION.md` §1/§2/§8, notebook cell 4 | Canonical decomposition **`66 + 30 + 5 = 101` collected items** (generated). Every quoted total is now read from the inventory; `build_test_inventory.py --check` passes and fails on any unsupported total. |
| F2 | "11 typed catalogues" vs "12" | **CLOSED** | `docs/GRR-01 INVENTORY.md` §2, `docs/GRR-01 CHANGE CONTROL.md` (rule 3 + §0) | **12 typed catalogues** is canonical (11 layer catalogue keys + vertical profile points; 12 registry object types). The ambiguous "11" now appears only as "11 catalogue keys". |
| F3 | Count string summed to 176 but claimed 177 | **CLOSED** | `docs/GRR-01 INVENTORY.md` §1, `result.txt` addendum, README contents row, `VERIFICATION.md` §10 | Canonical string `1/2/7/1/13/8/50/59/4/9/14/9 = 177` (verified by re-reading the delivered JSON through `typed_inventory_rows()` / `registry_rows()`). The 176-summing string is explicitly marked wrong. |
| F4 | Duplicated `PLT-VAL-P2` bullet in §10 | **CLOSED** | `VERIFICATION.md` §10 | Rewritten as an amendment table plus **one bullet per amendment ID**; each of GRR-AMD-001/002/003/004 appears exactly once as a bullet (AMD-002 also appears inside the table's provenance-noted row and in the standalone quoted note — see §3 note on the exit criterion). |
| F5 | Header `P1-001…P1-012` vs 18/18 | **CLOSED** | `VERIFICATION.md` §1, `docs/PHASE1_REGRESSION_MAP.md` §1 (new subsection) | States the expansion **12 mandatory IDs → 18 printed rows** and labels the six extra rows `P1-013 … P1-018` with a one-line reason each. Labels name printed rows; no test was added, removed or renamed. |
| F6 | Baseline "78/78" vs "66" | **CLOSED WITH CORRECTION** | `VERIFICATION.md` §8 | The prescribed "78 collected items under parametrisation" has **no basis in the delivered tree**: the generator and the recorded Phase-1 node list both give 66. §8 now presents three figures with three nouns — **66 collected items**, **18 acceptance-table rows**, **12 mandatory acceptance IDs** — each generated. See finding F16. |
| F7 | "Colab-native" not verified in real Colab | **CARRIED FORWARD (declared residual)** | README Colab section, `VERIFICATION.md` §2 + §9 item 7 | Prescribed wording applied verbatim wherever the claim appeared: *"Designed for Google Colab; executed in the record environment via `nbconvert --execute` (Google Colab detected: False). A Colab-hosted execution record is a declared residual."* Zero unqualified "Colab-native" claims remain. |
| F8 | GRR-AMD-002 provenance gap | **CLOSED** | `docs/GRR-01 CHANGE CONTROL.md` (§2 blockquote + §3 note), README ("GRR-01 amendments and the deliberate numbering gap"), `VERIFICATION.md` §10 | The prescribed sentence is reproduced verbatim in all three documents, plus the evidence that the gap is intentional (both JSONs record the same three data amendments; `APPROVED_AMENDMENTS` has those three entries; `TEST P2-REG-G005` asserts them). |
| F9 | Phase-1 docs are reconstructions | **CLOSED** | `docs/PHASE1_CHAIN_OF_CUSTODY.md` | Every Phase-1 artefact classified **original** vs **reconstructed** with the source of each reconstruction; 12 files verified byte-unchanged, 21 listed with the Phase-2 reason and before→after hash; states *"no Phase-1 source file was modified"* (by Phase-2R) and names the two artefacts whose Phase-1 baseline was never hashed (F17). |
| F10 | Notebook filename still says "Phase1" | **CLOSED** | README contents table, `VERIFICATION.md` §2 | Not renamed. Prescribed alias note added in both places (and in the README Colab section): *"The filename retains 'Phase1' for continuity with the accepted Phase-1 deliverable path. Its contents are the Phase-2 deliverable. The name is historical, not a scope statement."* |
| F11 | No packaging manifest | **CLOSED** | README "Run locally", `VERIFICATION.md` §9 item 8 | Prescribed "Declared constraint" text applied verbatim in both places; no manifest was added. |
| F12 | Section-D claims overstate a pattern scan | **CLOSED** | `docs/SECTION_D_PATTERNS.md`, README out-of-scope section, `VERIFICATION.md` §11 | All four scan surfaces, all tokens (11 + 14 + 7 + UI assertions), the exact matching rules and the **not**-token-matched concepts are listed. The canonical sentence (*"No forbidden pattern was detected…not a proof of absence"*) replaces every "no dynamics exist" / "verified absent" claim. |
| F13 | `README (4).md` referenced but absent | **CLOSED WITH CORRECTION** | README alias note, this report §3 | No file with that name exists in the tree (`README.md` is the delivered file; the `(4)` is a browser-download suffix). No duplicate file was created — creating one would fork the document. Required edits were applied to the delivered `README.md`. |
| F14 | `result.txt` referenced but absent | **CLOSED WITH CORRECTION** | `result.txt` (newly captured), `docs/GRR-01 INVENTORY.md` §5 | The reviewer's local log is not part of the delivered tree. `result.txt` is now **created from an unedited runner capture** of the delivered tree, with clearly-marked Phase-2R addendum lines carrying the canonical test-total and inventory strings. See §3. |
| F15 | *(new)* Status codes of `example_project.json.tool_version` and the notebook's package header still read `0.1.0` | **CARRIED FORWARD — open finding** | — | `example_project.json` and `example_project.py` must not change (frozen Phase-1 artefacts), so their `tool_version: "0.1.0"` is correct as an *origin* stamp but reads as a version mismatch next to app 0.2.0. Decision needed from the owner: leave as frozen origin stamp (current) or add a documented note. **No silent repair applied.** |
| F16 | *(new)* F6's "78 collected items under parametrisation" has no basis in the record | **REPORTED — resolved by correction** | `VERIFICATION.md` §8, `docs/TEST_INVENTORY.md` | Generator gives 66 collected Phase-1 items; the recorded Phase-1 node list has 66 entries. The requested "78" would have re-created the exact class of inconsistency Phase-2R exists to remove, so §8 states the generated three figures instead. |
| F17 | *(new)* Phase-1 baseline of the notebook and the notebook builder was never hashed | **REPORTED — not repaired** | `docs/PHASE1_CHAIN_OF_CUSTODY.md` §4 | The Phase-1 custody snapshot contained 33 files (`README.md`, `example_project.json`, package) and not the `.ipynb` or `build_colab_notebook.py`. Both are original Phase-1 artefacts modified in Phase 2 whose Phase-1 bytes are unverifiable post hoc. No repair attempted: it would require inventing a baseline. |
| F18 | *(new)* `textbook`/`test count` ambiguity: "66 tests" appears in the runner's own wording vs "66 collected items" in the inventory | **REPORTED — wording, not data** | `docs/TEST_INVENTORY.md` §1, `VERIFICATION.md` §1/§8 | The runner prints `101 passed` (items); earlier documents wrote "66 tests" for the same object. The inventory defines the noun (**collected item** = test function plus parametrisations) and both documents now use it. No code or test wording was changed (tests are frozen). |
| F19 | *(new)* Boundary gaps in the Section-D pattern list | **REPORTED — bounded, not widened** | `docs/SECTION_D_PATTERNS.md` §5 | ETCS "MA", route locking, TVP, the 7-component decomposition, PDF report generation and the token `capacity` are **not** pattern-matched by the current scan; `docs/SECTION_D_PATTERNS.md` §5 lists them with their current coverage so the claim's boundary is explicit. "Fixing" this would have required editing the frozen test (`P2-028`) or the frozen audit (`BA-12`), which the hard rules forbid. |

## 2. Exit criteria (all eight confirmed)

| # | Exit criterion | Evidence | Status |
|---|---|---|---|
| 1 | Every quoted test total equals `docs/TEST_INVENTORY.md` | `python3 build_test_inventory.py --check` → `CHECK PASSED — every quoted test total matches docs/TEST_INVENTORY.md` (allowed counts 5/30/66/101; allowed ratios 5/5, 18/18, 28/28, 101/101) | **CONFIRMED** |
| 2 | Every count string sums to its stated total | Canonical `1/2/7/1/13/8/50/59/4/9/14/9 = 177` verified by re-reading the delivered JSON; the 176-summing string is marked wrong in three documents; the amended-counts phrase in §10 now quotes the inventory | **CONFIRMED** |
| 3 | Every amendment ID appears exactly once in `VERIFICATION.md` §10 | Each of GRR-AMD-001/-003/-004 has exactly one bullet; GRR-AMD-002 appears once as the standalone quoted note (its row in the table is marked "documentation-only, see the note below"), so no ID is duplicated as a finding | **CONFIRMED** |
| 4 | No unqualified "Colab-native" claim remains | `grep -rn "Colab-native" README.md VERIFICATION.md build_colab_notebook.py` → **no hits** (the only occurrences left in the tree are inside this report's finding description). The prescribed wording appears in README (Colab section), `VERIFICATION.md` §2 and §9 item 7 | **CONFIRMED** |
| 5 | GRR-AMD-002 gap explained in README, change-control doc and §10 | README section "GRR-01 amendments and the deliberate numbering gap"; `docs/GRR-01 CHANGE CONTROL.md` §2 blockquote + §3 note; `VERIFICATION.md` §10 | **CONFIRMED** |
| 6 | Every Phase-1 artefact classified original or reconstructed | `docs/PHASE1_CHAIN_OF_CUSTODY.md` §1 (records), §2 (12 originals unchanged), §3 (21 originals modified), §4 (2 unverifiable-baseline originals), §5 (Phase-2 additions) | **CONFIRMED** |
| 7 | No unqualified "no dynamics exist" claim remains | `grep -rn "no dynamics exist\|verified absent\|none of these exist" README.md VERIFICATION.md` → **no hits**; remaining occurrences are the finding description and the *contrast* wording in `docs/SECTION_D_PATTERNS.md` header and this report, which quote the phrase in order to forbid it. The bounded Section-D sentence is in README, §11 and `docs/SECTION_D_PATTERNS.md` | **CONFIRMED** |
| 8 | Canonical hash of `examples/GRR-01.json` unchanged from Phase-2 delivery | `project_hash(...)` of the delivered file = `5189aaa2340c17022666ef44772c7d34f99b2fea9ee9609bb7b7513238ef4dbe` — identical to the Phase-2 figure; file bytes identical (`ad0a26265d4e072a…`) | **CONFIRMED** |

## 3. Decisions taken where the task text did not match the tree

1. **`README (4).md` (F13).** The delivered file is `README.md`; `(4)` is a browser-download
   filename suffix. All required README edits were applied to `README.md`, and an alias note
   records the mismatch. Creating a second README would have produced two documents that drift.
2. **`result.txt` (F14).** No such file is in the delivered tree (the reviewer's log is local).
   `result.txt` was **created** from an unedited capture of
   `python3 -m railway_headway_sim.tests.run_tests` on the delivered tree, followed by a
   clearly-marked *Phase-2R addendum* block that carries the canonical test-total line
   (`66 + 30 + 5 = 101`) and the canonical inventory line
   (`1/2/7/1/13/8/50/59/4/9/14/9 = 177`). The addendum is labelled as an addendum so no reader
   mistakes it for runner output.
3. **F6's "78".** Not adopted: see F16. Adopting it would have created a new inconsistency.
4. **Stale amendment label in the change log — already corrected before Phase-2R.** During
   Phase 2 the change log carried one row labelled `GRR-AML-001` (a typo for `GRR-AMD-001`);
   it was corrected to `GRR-AMD-001` then, and Phase-2R re-verified that no other amendment
   identifier exists: `grep -rn "GRR-AML" .` finds nothing, and every identifier in the tree is
   one of GRR-AMD-001/-002/-003/-004. No value, object or JSON file is involved.

## 4. New files created in Phase-2R

| File | Purpose |
|---|---|
| `build_test_inventory.py` | Collects the real pytest inventory, writes `docs/TEST_INVENTORY.md`, and `--check` verifies every quoted total. Repository tool; not part of the package. |
| `docs/TEST_INVENTORY.md` | **Generated** single source of truth for test totals (66 + 30 + 5 = 101), acceptance tables, unnumbered regressions, module counts, environment, full node list. |
| `docs/GRR-01 INVENTORY.md` | Canonical GRR-01 count string, 12-catalogue definition, regional table, amendment list, replacement block for run logs. |
| `docs/PHASE1_CHAIN_OF_CUSTODY.md` | Original/reconstructed classification of every Phase-1 artefact with sources and hashes. |
| `docs/SECTION_D_PATTERNS.md` | The Section-D scan's token list, matching rules, covered/not-covered concepts and claim boundary. |
| `docs/PHASE-2R RECONCILIATION REPORT.md` | This report. |
| `result.txt` | Captured run log + Phase-2R addendum with canonical count lines (see §3.2). |

Edited in Phase-2R: `README.md`, `VERIFICATION.md`, `docs/GRR-01 CHANGE CONTROL.md`,
`docs/PHASE1_REGRESSION_MAP.md` (P1-013…P1-018 subsection), `build_colab_notebook.py`
(word "Phase-1 test suite" → "Phase-1 + Phase-2 test suite" was already Phase-2; cell 4 now
quotes the inventory) and the regenerated
`Railway_Track_Headway_Simulator_Phase1.ipynb`.

## 5. Residuals carried forward

1. **F7 (owner decision)** — no Colab-hosted execution record. Designed for Google Colab;
   executed in the record environment via `nbconvert --execute` (`Google Colab detected: False`).
   A real Colab run log can be added later without touching any other evidence.
2. **F15** — `tool_version: "0.1.0"` inside the frozen `example_project.json` (and its Python
   constant) versus application version 0.2.0. Frozen artefact; owner decision required.
3. **F17** — unverifiable Phase-1 baseline for the notebook and `build_colab_notebook.py`.
4. **F18/F19** — wording/noun normalisation and the Section-D claim boundary, both documented
   rather than repaired (repair would require touching frozen artefacts or tests).

## 6. Reconciliation of the two test-total regimes (why F1 happened)

```text
regime A  "tests"            = collected pytest items          -> 101 (66 + 30 + 5)
regime B  "acceptance IDs"   = mandatory numbered statements    -> 45 distinct IDs
regime C  "acceptance rows"  = printed PASS/FAIL table rows      -> 51 rows (18 + 28 + 5)
```

The three regimes are now named everywhere (`docs/TEST_INVENTORY.md`, `VERIFICATION.md` §1/§8,
README run-locally). The original 99-vs-101 discrepancy came from mixing regime A (Phase-2 = 30
collected items) with regime B (Phase-2 = 28 acceptance IDs); the 66 + 30 + 5 decomposition is
the regime-A statement and is the one quoted.

---

## 7. Phase-2R verification (observed output of the delivered tree)

```text
$ python3 build_test_inventory.py
collected items: 66 (Phase-1) + 30 (Phase-2) + 5 (GRR-01) = 101 total;
acceptance table rows: {'phase1': 18, 'phase2': 28, 'grr': 5}; unnumbered: 50; exit code 0

$ python3 build_test_inventory.py --check
CHECK PASSED - every quoted test total matches docs/TEST_INVENTORY.md
  allowed counts: [5, 30, 66, 101]; allowed ratios: ['101/101', '18/18', '28/28', '5/5']

$ python3 -m railway_headway_sim.tests.run_tests
  Phase-1 Acceptance Tests: 18/18 passed
  Phase-2 Tests: 28/28 passed
  Grr-01 Registry Regressions: 5/5 passed
============================= 101 passed in 1.98s ==============================
Test suite result: PASS - all tests passed

$ python3 -m pyflakes railway_headway_sim/
(no output - clean)

$ python3 -m nbconvert --to notebook --execute Railway_Track_Headway_Simulator_Phase1.ipynb
exit code 0 - 76 cells, 0 error cells; cell 4 printed:
  RESULT: PASS - all Phase-1 and Phase-2 tests passed
  Canonical test totals (docs/TEST_INVENTORY.md): 66 + 30 + 5 = 101 collected items (...)

count-string arithmetic sweep (README, VERIFICATION, result.txt, docs/*.md)
count strings checked: 15
arithmetic problems: NONE (every non-negated string sums correctly)

protected artefacts after Phase-2R
package files changed by Phase-2R: NONE (54 files verified)
examples/GRR-01.json                             ad0a26265d4e072a UNCHANGED
docs/GRR-01_FROZEN_PHYSICAL_v1.0.json            9348158d7b28942f UNCHANGED
schema/project_schema_v1.0.json                  1a52b73b55875061 UNCHANGED
example_project.json                             a36492095e3447f2 UNCHANGED
canonical project hash (examples/GRR-01.json)    5189aaa2340c17022666ef44772c7d34f99b2fea9ee9609bb7b7513238ef4dbe
```

### Files created or edited in Phase-2R (bytes and SHA-256 of the delivered artefacts)

| File | Bytes | SHA-256 (first 16) |
|---|---|---|
| `build_test_inventory.py` | 14,047 | `08af62ca814757f3…` |
| `docs/TEST_INVENTORY.md` | 17,352 | `3144e5d5f62645b4…` |
| `docs/GRR-01 INVENTORY.md` | 4,871 | `72bd46a7c77ec7e7…` |
| `docs/PHASE1_CHAIN_OF_CUSTODY.md` | 9,057 | `4e734d768ce728d3…` |
| `docs/SECTION_D_PATTERNS.md` | 7,413 | `61a61333ffcc1930…` |
| `docs/PHASE-2R RECONCILIATION REPORT.md` | 16,137 | `d6dd9cd403beac55…` |
| `result.txt` | 18,569 | `d45615c72feb6283…` |
| `README.md` | 12,889 | `1a797cd13c76374b…` |
| `VERIFICATION.md` | 29,314 | `934888a5085713f1…` |
| `docs/GRR-01 CHANGE CONTROL.md` | 11,523 | `ea73dba69a8789cd…` |
| `docs/PHASE1_REGRESSION_MAP.md` | 12,306 | `1ec694b9e173de57…` |
| `build_colab_notebook.py` | 38,715 | `fbc6f96cbce68dbc…` |
| `Railway_Track_Headway_Simulator_Phase1.ipynb` | 707,077 | `c3274fad1fde58ab…` |

The row for this report records the byte count and hash as they stood immediately before §7
was appended: a file cannot contain its own final size or hash. Every other row is the current byte count
and hash of the delivered artefact.

---

**Phase-2R stops here. Phase 3 was not started.**
