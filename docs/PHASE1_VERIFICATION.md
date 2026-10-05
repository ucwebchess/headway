# PHASE 1 — VERIFICATION RECORD (frozen evidence)

This file records the **accepted Phase-1 verification state** that Phase 2 extended in
place. It is written from the recorded evidence of the delivered Phase-1 run; nothing in
it is re-derived from Phase-2 code.

> **Note for reviewers:** the accepted Phase-1 tree as delivered contained **no**
> `VERIFICATION.md` and **no** `docs/` directory; the Phase-2 task description assumed
> those artefacts existed. This file therefore *reconstructs* the Phase-1 verification
> record from the evidence that was captured while validating the Phase-1 deliverable
> (test run log, source manifest and notebook execution log). The Phase-1 source itself
> is untouched — see `docs/PHASE1_SOURCE_MANIFEST.json`.

## 1. Accepted Phase-1 artefact set

33 files, SHA-256 recorded per file in `docs/PHASE1_SOURCE_MANIFEST.json`
(app version 0.1.0, schema version 1.0).

```
railway_headway_sim/__init__.py
railway_headway_sim/version.py
railway_headway_sim/constants.py
railway_headway_sim/example_project.py
railway_headway_sim/app/         (project_controller.py)
railway_headway_sim/io/          (project_io.py)
railway_headway_sim/models/      (common.py, diagnostics.py, enums.py, project.py)
railway_headway_sim/tests/       (conftest.py, run_tests.py, support.py, test_*.py)
railway_headway_sim/ui/          (app_shell.py, formatting.py, placeholder_pages.py,
                                  project_page.py, validation_page.py)
README.md, example_project.json, Railway_Track_Headway_Simulator_Phase1.ipynb,
build_colab_notebook.py
```

## 2. Test evidence

```text
$ python3 -m railway_headway_sim.tests.run_tests
------------------------------------------------------------------------------
  Acceptance tests: 18/18 passed
==============================================================================
============================== 66 passed in 0.96s ==============================

Test suite result: PASS - all tests passed
```

* **66 tests passed** (57 + 1 skipped when `ipywidgets` is unavailable — the canonical
  number with the documented dependencies installed is 66).
* **18/18** numbered Phase-1 acceptance instances (`P1-001` … `P1-012`; several
  acceptance IDs are asserted by more than one test function).
* `pyflakes railway_headway_sim/` — clean.

The 66 collected test node IDs of the accepted suite are recorded in the
Phase-1 regression mapping (`docs/PHASE1_REGRESSION_MAP.md`).

## 3. Notebook evidence

`Railway_Track_Headway_Simulator_Phase1.ipynb` executed end-to-end in a fresh runtime
with `nbconvert --execute`:

* exit code 0, **0 error cells**, 52 cells / 31 `%%writefile` cells / ≈297.7 KB;
* the in-notebook suite printed **66 passed**, acceptance 18/18;
* the self-check cell printed:
  `Import == export data: True`, `Roundtrip hash equal: True`,
  `Re-export byte-stable: True`, `Hash unchanged: True`;
* example self-check hash
  `2a3007d9105e42f6fd543afab2a90b2db2608b0f8567a696d66a6aca7fc58a6f`;
* every inlined package file byte-matches the on-disk file, and
  `example_project.json` equals `EXAMPLE_PROJECT_JSON` (VALID, 6 INFO).

## 4. Phase-1 acceptance statements (as delivered)

* Schema 1.0 documents import as **data only** (`json.loads`; no `eval`/`exec`/`pickle`,
  no class names taken from the JSON).
* Export is deterministic; `import → export → import → export` is byte-stable; timestamps
  are never rewritten by a load.
* The canonical hash is SHA-256 over sorted keys with floats rounded to 9 decimals for
  hashing only (`10` ≡ `10.0`, `-0.0` ≡ `0.0`).
* Changing the FORWARD/REVERSE selector never modifies stored project data or the hash.
* Unknown/future fields (including nested ones) survive import → export.
* Diagnostics are structured (`code`, `severity`, `category`, `message`, `object_id`,
  `context`, `suggested_action`) and deterministic; no placeholder engineering results.
* `launch_app(embed=True)` displays the shell; `launch_app(embed=False)` writes a static
  HTML snapshot.
