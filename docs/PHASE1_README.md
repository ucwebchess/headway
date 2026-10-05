# Railway Track Headway Simulator — Phase 1

**Application version 0.1.0 · Project schema version 1.0 · Google Colab**

Phase-1 deliverable: the modular application foundation for a future microscopic
railway train-performance / blocking-time / headway / capacity simulator
(OpenTrack-like engineering analysis philosophy).

> Phase 1 contains **no** train simulation, railway physics, signalling, headway or
> capacity calculation — and no placeholder result values anywhere. Pages for those
> functions are explicitly marked `PLANNED FOR LATER DEVELOPMENT PHASE`.

## Contents

| Path | What it is |
|---|---|
| `Railway_Track_Headway_Simulator_Phase1.ipynb` | **Main deliverable.** Colab notebook: installs dependencies, writes the package, runs the tests, self-checks the roundtrip, launches the app. |
| `railway_headway_sim/` | The Python package (31 modules), identical to what the notebook writes. |
| `example_project.json` | Minimal-but-complete example project JSON (schema 1.0). |
| `build_colab_notebook.py` | Regenerates the notebook from the package (`python3 build_colab_notebook.py`), so code and notebook cannot drift. |

## Run in Google Colab

1. Open `Railway_Track_Headway_Simulator_Phase1.ipynb` in Colab.
2. `Runtime → Run all` (cells 1–2 install dependencies and create the package; the
   `%%writefile` cells write the modules; the final cells verify, test and launch).
3. Use the application rendered by cell 7 — no manual file editing is required.

## Run locally

```bash
pip install "pydantic>=2.5" "ipywidgets>=8.0" pytest
python3 -m railway_headway_sim.tests.run_tests   # 66 tests, 18/18 acceptance instances
python3 -c "from railway_headway_sim.ui import launch_app; launch_app()"   # in Jupyter/Colab
```

## Layer contract

```
UI  ->  ProjectController  ->  Project model  ->  Validation / Serialization
```

* `models/` – canonical project container (schema 1.0) and structured diagnostics.
  Never imports widgets.
* `validation/` – stage 1 raw JSON/schema/type checks, stage 2 structural + basic
  semantic checks. Never imports widgets.
* `io/` – safe JSON import (`json.loads` only), deterministic export, canonical SHA-256 hash.
* `app/` – `ProjectController`: project, direction selection, validation, modification state,
  hashes, export/import outcomes, UI subscriptions.
* `ui/` – Colab shell: header, FORWARD/REVERSE selector, navigation tabs, Project page,
  Validation & Audit page, placeholder pages for later phases.
* `tests/` – TEST P1-001 … P1-012 plus regression tests (PASS/FAIL table via
  `pytest_terminal_summary`).

## Key invariants

* The canonical JSON/project model is the source of truth; widget values are never
  engineering state.
* `project.id` is the stable machine key; `project.name` is display-only.
* Changing the direction selector never rewrites stored project data and never changes
  the project hash.
* `Project → export → import → export` is byte-stable (import never rewrites timestamps;
  export metadata is opt-in).
* Unknown/future JSON fields are preserved through import/export (schema 1.x additive).
* Uploaded JSON is treated strictly as data — no `eval`, `exec`, `pickle` or dynamic import.
