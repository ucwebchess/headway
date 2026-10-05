"""Generate ``docs/TEST_INVENTORY.md`` — the single source of truth for test totals.

Run from the repository root::

    python3 build_test_inventory.py            # regenerate docs/TEST_INVENTORY.md
    python3 build_test_inventory.py --check     # verify quoted totals in the documents

Why this file exists
--------------------
The delivered documents (``README.md``, ``VERIFICATION.md``) and the Colab notebook
quote test totals. Those totals are facts about the test suite, so they are
**collected here, once**, and the documents quote this file instead of re-asserting
numbers. ``--check`` scans the documents for any "N tests / N collected items /
N passed / a/b passed" claim and fails if it is not one of the totals recorded in
``docs/TEST_INVENTORY.md``.

The generator is deterministic: no timestamps, sorted node ids, stable formatting.
It never writes anywhere except ``docs/TEST_INVENTORY.md``; the source tree
(``railway_headway_sim/``) is read-only for this script.

Exit codes: 0 = written / check passed, 1 = check failed or pytest could not run.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TESTS_DIR = ROOT / "railway_headway_sim" / "tests"
DOCS_DIR = ROOT / "docs"
INVENTORY_PATH = DOCS_DIR / "TEST_INVENTORY.md"

#: Acceptance-id matcher (identical to ``tests/conftest.py``).
ACCEPTANCE_ID = re.compile(
    r"\bP1-\d{3}\b|\bP2-REG-G\d{3}\b|\bP2-\d{3}\b|\bP3-\d{3}\b|\bP4-\d{3}\b"
    r"|\bP5-\d{3}\b|\bP6-\d{3}\b"
)

#: Test modules grouped into the ten reported suites, in delivery order.
SUITES: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    (
        "phase1",
        "Phase-1 suite (TEST P1-001 … TEST P1-012)",
        ("test_validation.py", "test_project_io.py", "test_controller.py", "test_ui_shell.py"),
    ),
    (
        "phase2",
        "Phase-2 suite (TEST P2-001 … TEST P2-028)",
        (
            "test_phase2_models.py",
            "test_phase2_topology.py",
            "test_phase2_stations.py",
            "test_phase2_static_geometry.py",
            "test_phase2_facade_and_app.py",
        ),
    ),
    (
        "grr",
        "GRR-01 registry regressions (TEST P2-REG-G001 … TEST P2-REG-G005)",
        ("test_phase2_grr_regressions.py",),
    ),
    (
        "phase3",
        "Phase-3 suite (TEST P3-001 … TEST P3-026)",
        ("test_phase3_editors.py",),
    ),
    (
        "phase4a",
        "Phase-4A suite (TEST P4-001 … TEST P4-030)",
        ("test_phase4a_route_coordinate.py",),
    ),
    (
        "phase4b",
        "Phase-4B suite (TEST P4-031 … TEST P4-048)",
        ("test_phase4b_geometry_along_route.py",),
    ),
    (
        "phase5a",
        "Phase-5A suite (TEST P5-001 … TEST P5-024)",
        ("test_phase5a_resistance.py",),
    ),
    (
        "phase5b",
        "Phase-5B suite (TEST P5-025 … TEST P5-042)",
        ("test_phase5b_along_route.py",),
    ),
    (
        "phase6a",
        "Phase-6A suite (TEST P6-001 … TEST P6-024)",
        ("test_phase6a_rolling_stock_model.py",),
    ),
    (
        "phase6b",
        "Phase-6B suite (TEST P6-025 … TEST P6-048)",
        ("test_phase6b_rolling_stock_ui.py",),
    ),
)

#: Documents that must quote this inventory, not re-assert totals.
CHECKED_DOCUMENTS: tuple[str, ...] = ("README.md", "VERIFICATION.md", "Railway_Track_Headway_Simulator_Phase1.ipynb")

#: "N tests" / "N collected items" / "N passed" style claims.
COUNT_CLAIM = re.compile(
    r"(?<![\w/.-])(\d{1,4})\s*(?:numbered\s+)?(?:test functions|tests?|collected items|passed)\b"
)
#: "a/b passed" style claims.
RATIO_CLAIM = re.compile(r"(?<![\w/.-])(\d{1,4})\s*/\s*(\d{1,4})\s+passed\b")


class _Recorder:
    """Minimal pytest plugin: records collected items, ids, titles and outcomes."""

    def __init__(self) -> None:
        self.items: list[str] = []
        self.outcomes: dict[str, str] = {}

    def pytest_collection_modifyitems(self, session, config, items) -> None:  # noqa: ARG002
        for item in items:
            doc = (getattr(item, "function", None).__doc__ or "") if getattr(item, "function", None) else ""
            match = ACCEPTANCE_ID.search(doc.strip())
            name = item.nodeid.rsplit("::", 1)[0].split("/")[-1]
            self.items.append(f"{name}::{item.name}")
            if match:
                self.acceptance_ids[f"{name}::{item.name}"] = match.group(0)
                self.acceptance_titles[f"{name}::{item.name}"] = (
                    doc.strip().split(" - ", 1)[-1].splitlines()[0].strip()
                )
            else:
                self.unnumbered.append(f"{name}::{item.name}")

    acceptance_ids: dict[str, str]
    acceptance_titles: dict[str, str]
    unnumbered: list[str]

    def pytest_runtest_logreport(self, report) -> None:
        if report.when != "call" and not (report.when == "setup" and report.outcome == "failed"):
            return
        key = report.nodeid.rsplit("::", 1)[0].split("/")[-1] + "::" + report.nodeid.split("::")[-1]
        if report.outcome == "passed":
            self.outcomes[key] = "PASS"
        elif report.outcome == "skipped":
            self.outcomes[key] = "SKIP"
        else:
            self.outcomes[key] = "FAIL"


def _collect() -> tuple[_Recorder, int]:
    """Run the suite once and return the recorder and the pytest exit code."""
    try:
        import pytest
    except ImportError:  # pragma: no cover - environment dependent
        print("pytest is not installed: pip install pytest", file=sys.stderr)
        raise SystemExit(2)
    recorder = _Recorder()
    recorder.acceptance_ids = {}
    recorder.acceptance_titles = {}
    recorder.unnumbered = []
    code = pytest.main(
        [str(TESTS_DIR), "-q", "-p", "no:cacheprovider", "--tb=no"],
        plugins=[recorder],
    )
    return recorder, int(code)


def _suite_of(module: str) -> str:
    for key, _title, files in SUITES:
        if module in files:
            return key
    return "other"


def build() -> tuple[str, dict[str, object]]:
    """Return the markdown text and the machine-readable totals block."""
    import platform

    recorder, exit_code = _collect()
    items = sorted(recorder.items)
    by_suite: dict[str, list[str]] = {key: [] for key, _t, _f in SUITES}
    by_suite["other"] = []
    for key in items:
        by_suite[_suite_of(key.split("::", 1)[0])].append(key)

    tables: dict[str, list[tuple[str, str, int]]] = {}
    totals: dict[str, int] = {}
    for key, _title, _files in SUITES:
        grouped: dict[str, list[str]] = {}
        for node in by_suite[key]:
            acceptance_id = recorder.acceptance_ids.get(node)
            if acceptance_id:
                grouped.setdefault(acceptance_id, []).append(node)
        rows = [
            (acceptance_id, recorder.acceptance_titles.get(nodes[0], ""), len(nodes))
            for acceptance_id, nodes in sorted(grouped.items())
        ]
        tables[key] = rows
        totals[key] = len(by_suite[key])

    total_items = len(items)
    unnumbered = sorted(recorder.unnumbered)
    passed = sum(1 for key in items if recorder.outcomes.get(key) == "PASS")
    failed = [key for key in items if recorder.outcomes.get(key) == "FAIL"]

    out: list[str] = []
    out.append("# TEST INVENTORY")
    out.append("")
    out.append("> **Generated file — do not edit by hand.** Produced by `python3 build_test_inventory.py`.")
    out.append("> This file is the single source of truth for every quoted test total in `README.md`,")
    out.append("> `VERIFICATION.md` and the Colab notebook self-check. Verify with")
    out.append("> `python3 build_test_inventory.py --check`.")
    out.append("")
    out.append("## 1. Totals (canonical)")
    out.append("")
    out.append("| Suite | Collected items | Distinct acceptance IDs | Acceptance table rows |")
    out.append("|---|---|---|---|")
    for key, title, _files in SUITES:
        rows = tables[key]
        out.append(f"| {title} | {totals[key]} | {len(rows)} | {sum(r[2] for r in rows)} |")
    out.append(f"| **Total (all ten suites)** | **{total_items}** | "
               f"{sum(len(tables[k]) for k, _t, _f in SUITES)} | "
               f"{sum(sum(r[2] for r in tables[k]) for k, _t, _f in SUITES)} |")
    out.append("")
    out.append("**Canonical decomposition string** (quoted verbatim by the documents):")
    out.append("")
    out.append(
        f"> `{totals['phase1']} + {totals['phase2']} + {totals['grr']} + {totals['phase3']} "
        f"+ {totals['phase4a']} + {totals['phase4b']} + {totals['phase5a']} "
        f"+ {totals['phase5b']} + {totals['phase6a']} + {totals['phase6b']} = {total_items}` "
        f"collected items "
        f"({totals['phase1']} Phase-1 + {totals['phase2']} Phase-2 + {totals['grr']} GRR-01 "
        f"registry regressions + {totals['phase3']} Phase-3 + {totals['phase4a']} Phase-4A "
        f"+ {totals['phase4b']} Phase-4B + {totals['phase5a']} Phase-5A "
        f"+ {totals['phase5b']} Phase-5B + {totals['phase6a']} Phase-6A "
        f"+ {totals['phase6b']} Phase-6B)."
    )
    out.append("")
    out.append(f"**Run outcome in the recorded environment:** {passed}/{total_items} `PASS`, "
               f"{len(failed)} `FAIL`, exit code {exit_code}.")
    out.append("")
    out.append("The acceptance tables print one row per **asserted instance**, so a numbered test")
    out.append("that is parametrised (or asserts the same acceptance ID in several functions) appears")
    out.append("more than once: this is why the Phase-1 table has more rows than distinct IDs.")
    out.append("")
    out.append("## 2. Acceptance tables (as printed by the runner)")
    for key, title, _files in SUITES:
        rows = tables[key]
        out.append("")
        out.append(f"### {title} — {sum(r[2] for r in rows)}/{sum(r[2] for r in rows)} rows")
        out.append("")
        out.append("| Acceptance ID | Table rows | Title |")
        out.append("|---|---|---|")
        for acceptance_id, row_title, count in rows:
            out.append(f"| `{acceptance_id}` | {count} | {row_title} |")
    out.append("")
    out.append("## 3. Unnumbered tests (collected, no acceptance ID)")
    out.append("")
    out.append("These tests are collected and executed but carry no numbered acceptance ID;")
    out.append("they are structural/guard regressions, not acceptance instances:")
    out.append("")
    for node in unnumbered:
        out.append(f"- `{node}`")
    out.append("")
    out.append("## 4. Collected items per test module")
    out.append("")
    out.append("| Module | Collected items | Suite |")
    out.append("|---|---|---|")
    modules: dict[str, int] = {}
    for key in items:
        modules[key.split("::", 1)[0]] = modules.get(key.split("::", 1)[0], 0) + 1
    for module in sorted(modules):
        out.append(f"| `{module}` | {modules[module]} | {_suite_of(module)} |")
    out.append("")
    out.append("## 5. Record environment")
    out.append("")
    out.append(f"* Python {platform.python_version()} (`{platform.platform()}`)")
    try:
        import pytest as _pytest

        out.append(f"* pytest {_pytest.__version__}")
    except ImportError:  # pragma: no cover
        out.append("* pytest: not installed")
    out.append("* Command: `pytest railway_headway_sim/tests -q -p no:cacheprovider --tb=no`")
    out.append("")
    out.append("## 6. Full collected node id list")
    out.append("")
    out.append("```text")
    out.extend(items)
    out.append("```")
    out.append("")

    totals_block = {
        "phase1": totals["phase1"],
        "phase2": totals["phase2"],
        "grr": totals["grr"],
        "phase3": totals["phase3"],
        "phase4a": totals["phase4a"],
        "phase4b": totals["phase4b"],
        "phase5a": totals["phase5a"],
        "phase5b": totals["phase5b"],
        "phase6a": totals["phase6a"],
        "phase6b": totals["phase6b"],
        "total": total_items,
        "tables": {
            key: sum(r[2] for r in tables[key]) for key, _t, _f in SUITES
        },
        "unnumbered": len(unnumbered),
        "failed": failed,
        "exit_code": exit_code,
    }
    return "\n".join(out), totals_block


def _read_document(path: Path) -> str:
    """Return the searchable text of a document (notebooks: markdown + code cells)."""
    if path.suffix != ".ipynb":
        return path.read_text(encoding="utf-8")
    notebook = json.loads(path.read_text(encoding="utf-8"))
    chunks: list[str] = []
    for cell in notebook.get("cells", []):
        chunks.append("".join(cell.get("source", [])))
    return "\n".join(chunks)


def check(totals: dict[str, object]) -> int:
    """Verify every quoted test total in the documents matches this inventory."""
    allowed_counts = {
        int(totals["total"]),
        int(totals["phase1"]),
        int(totals["phase2"]),
        int(totals["grr"]),
        int(totals["phase3"]),
        int(totals["phase4a"]),
        int(totals["phase4b"]),
        int(totals["phase5a"]),
        int(totals["phase5b"]),
        int(totals["phase6a"]),
        int(totals["phase6b"]),
    }
    allowed_ratios = {f"{n}/{n}" for n in (totals["tables"] or {}).values()}  # type: ignore[union-attr]
    allowed_ratios.add(f"{totals['total']}/{totals['total']}")
    problems: list[str] = []
    if totals["failed"]:
        problems.append(f"the recorded run has failing tests: {totals['failed']}")
    for name in CHECKED_DOCUMENTS:
        path = ROOT / name
        if not path.exists():
            problems.append(f"{name}: missing")
            continue
        text = _read_document(path)
        for match in COUNT_CLAIM.finditer(text):
            value = int(match.group(1))
            if value not in allowed_counts:
                problems.append(f"{name}: unsupported test total {match.group(0)!r}")
        for match in RATIO_CLAIM.finditer(text):
            ratio = f"{match.group(1)}/{match.group(2)}"
            if ratio not in allowed_ratios:
                problems.append(f"{name}: unsupported acceptance ratio {match.group(0)!r}")
    if problems:
        print("CHECK FAILED - documents quote totals that are not in docs/TEST_INVENTORY.md:")
        for problem in problems:
            print("  -", problem)
        return 1
    print("CHECK PASSED - every quoted test total matches docs/TEST_INVENTORY.md")
    print(f"  allowed counts: {sorted(allowed_counts)}; allowed ratios: {sorted(allowed_ratios)}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="verify quoted totals instead of writing")
    args = parser.parse_args()

    text, totals = build()
    DOCS_DIR.mkdir(exist_ok=True)
    if not args.check:
        previous = INVENTORY_PATH.read_text(encoding="utf-8") if INVENTORY_PATH.exists() else None
        INVENTORY_PATH.write_text(text, encoding="utf-8")
        state = "unchanged" if previous == text else "written"
        print(f"{state}: {INVENTORY_PATH} ({len(text):,} bytes)")
    else:
        if not INVENTORY_PATH.exists():
            print("docs/TEST_INVENTORY.md is missing - run without --check first.", file=sys.stderr)
            return 1
        recorded = INVENTORY_PATH.read_text(encoding="utf-8")
        if recorded != text:
            print("CHECK FAILED - docs/TEST_INVENTORY.md is stale; regenerate it.", file=sys.stderr)
            return 1

    print(
        "collected items: "
        f"{totals['phase1']} (Phase-1) + {totals['phase2']} (Phase-2) + {totals['grr']} (GRR-01) "
        f"+ {totals['phase3']} (Phase-3) + {totals['phase4a']} (Phase-4A) "
        f"+ {totals['phase4b']} (Phase-4B) + {totals['phase5a']} (Phase-5A) "
        f"+ {totals['phase5b']} (Phase-5B) + {totals['phase6a']} (Phase-6A) = {totals['total']} total; "
        f"acceptance table rows: {totals['tables']}; "
        f"unnumbered: {totals['unnumbered']}; exit code {totals['exit_code']}"
    )
    return check(totals) if args.check else 0


if __name__ == "__main__":
    raise SystemExit(main())
