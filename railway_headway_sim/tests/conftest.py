"""Shared pytest configuration for the Phase-1 + Phase-2 test suite.

Two jobs:

1. Make the package importable when pytest is invoked from the project root or
   from a Colab ``/content`` directory.
2. Print explicit ``PASS/FAIL`` tables for the numbered tests, taken from each
   test's docstring: Phase-1 acceptance tests (TEST P1-001 ... TEST P1-012),
   Phase-2 tests (TEST P2-001 ... TEST P2-028), the GRR-01 registry regressions
   (TEST P2-REG-G001 ... TEST P2-REG-G005), the Phase-3 tests
   (TEST P3-001 ... TEST P3-026), the Phase-4A tests
   (TEST P4-001 ... TEST P4-030), the Phase-4B tests (TEST P4-031 ... TEST P4-048), the
   Phase-5A tests (TEST P5-001 ... TEST P5-024), the Phase-5B tests
   (TEST P5-025 ... TEST P5-042), the Phase-6A tests
   (TEST P6-001 ... TEST P6-024) and the Phase-6B tests
   (TEST P6-025 ... TEST P6-048).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

_PACKAGE_PARENT = Path(__file__).resolve().parents[2]
if str(_PACKAGE_PARENT) not in sys.path:
    sys.path.insert(0, str(_PACKAGE_PARENT))

_ACCEPTANCE_ID = re.compile(
    r"\bP1-\d{3}\b|\bP2-REG-G\d{3}\b|\bP2-\d{3}\b|\bP3-\d{3}\b|\bP4-\d{3}\b"
    r"|\bP5-\d{3}\b|\bP6-\d{3}\b"
)
_ACCEPTANCE_IDS: dict[str, str] = {}
_ACCEPTANCE_TITLES: dict[str, str] = {}
_RESULTS: dict[str, str] = {}


def pytest_collection_modifyitems(session, config, items) -> None:  # noqa: ARG001
    """Remember the acceptance-test id/title declared in each docstring."""
    for item in items:
        function = getattr(item, "function", None)
        doc = (function.__doc__ or "").strip() if function is not None else ""
        match = _ACCEPTANCE_ID.search(doc)
        if not match:
            continue
        _ACCEPTANCE_IDS[item.nodeid] = match.group(0)
        _ACCEPTANCE_TITLES[item.nodeid] = doc.split(" - ", 1)[-1].splitlines()[0].strip()


def pytest_runtest_logreport(report) -> None:
    """Record the outcome of setup/call phases for acceptance tests."""
    if report.nodeid not in _ACCEPTANCE_IDS:
        return
    if report.when == "call" or (report.when == "setup" and report.outcome == "failed"):
        if report.outcome == "passed":
            _RESULTS[report.nodeid] = "PASS"
        elif report.outcome == "skipped":
            _RESULTS[report.nodeid] = "SKIP"
        else:
            _RESULTS[report.nodeid] = "FAIL"


def _write_table(terminalreporter, title: str, items: list[tuple[str, str]]) -> tuple[int, int]:
    """Print one PASS/FAIL table and return ``(passed, total)``."""
    terminalreporter.write_line("")
    terminalreporter.write_line("=" * 78)
    terminalreporter.write_line(title)
    terminalreporter.write_line("=" * 78)
    failures = 0
    for nodeid, acceptance_id in items:
        status = _RESULTS.get(nodeid, "NOT RUN")
        if status != "PASS":
            failures += 1
        terminalreporter.write_line(
            f"  {status:8s} {acceptance_id}  {_ACCEPTANCE_TITLES.get(nodeid, '')}"
        )
    total = len(items)
    terminalreporter.write_line("-" * 78)
    terminalreporter.write_line(f"  {title.split(' (')[0].title()}: {total - failures}/{total} passed")
    terminalreporter.write_line("=" * 78)
    return total - failures, total


def pytest_terminal_summary(terminalreporter, exitstatus, config) -> None:  # noqa: ARG001
    """Print the Phase-1 ... Phase-6B tables (one per delivered stage)."""
    if not _ACCEPTANCE_IDS:
        return
    ordered = sorted(_ACCEPTANCE_IDS.items(), key=lambda kv: kv[1])
    phase1 = [(nodeid, test_id) for nodeid, test_id in ordered if test_id.startswith("P1-")]
    phase2 = [
        (nodeid, test_id)
        for nodeid, test_id in ordered
        if test_id.startswith("P2-") and not test_id.startswith("P2-REG-")
    ]
    grr = [(nodeid, test_id) for nodeid, test_id in ordered if test_id.startswith("P2-REG-")]
    phase3 = [(nodeid, test_id) for nodeid, test_id in ordered if test_id.startswith("P3-")]
    phase4 = [(nodeid, test_id) for nodeid, test_id in ordered if test_id.startswith("P4-")]
    phase4a = [
        (nodeid, test_id)
        for nodeid, test_id in phase4
        if int(test_id.split("-", 1)[1]) <= 30
    ]
    phase4b = [
        (nodeid, test_id)
        for nodeid, test_id in phase4
        if int(test_id.split("-", 1)[1]) > 30
    ]
    if phase1:
        _write_table(terminalreporter, "PHASE-1 ACCEPTANCE TESTS (TEST P1-001 ... TEST P1-012)", phase1)
    if phase2:
        _write_table(terminalreporter, "PHASE-2 TESTS (TEST P2-001 ... TEST P2-028)", phase2)
    if grr:
        _write_table(
            terminalreporter,
            "GRR-01 REGISTRY REGRESSIONS (TEST P2-REG-G001 ... TEST P2-REG-G005)",
            grr,
        )
    if phase3:
        _write_table(
            terminalreporter,
            "PHASE-3 TESTS (TEST P3-001 ... TEST P3-026)",
            phase3,
        )
    if phase4a:
        _write_table(
            terminalreporter,
            "PHASE-4A TESTS (TEST P4-001 ... TEST P4-030)",
            phase4a,
        )
    if phase4b:
        _write_table(
            terminalreporter,
            "PHASE-4B TESTS (TEST P4-031 ... TEST P4-048)",
            phase4b,
        )
    phase5 = [(nodeid, test_id) for nodeid, test_id in ordered if test_id.startswith("P5-")]
    phase5a = [
        (nodeid, test_id)
        for nodeid, test_id in phase5
        if int(test_id.split("-", 1)[1]) <= 24
    ]
    phase5b = [
        (nodeid, test_id)
        for nodeid, test_id in phase5
        if int(test_id.split("-", 1)[1]) > 24
    ]
    if phase5a:
        _write_table(
            terminalreporter,
            "PHASE-5A TESTS (TEST P5-001 ... TEST P5-024)",
            phase5a,
        )
    if phase5b:
        _write_table(
            terminalreporter,
            "PHASE-5B TESTS (TEST P5-025 ... TEST P5-042)",
            phase5b,
        )
    phase6 = [(nodeid, test_id) for nodeid, test_id in ordered if test_id.startswith("P6-")]
    phase6a = [
        (nodeid, test_id)
        for nodeid, test_id in phase6
        if int(test_id.split("-", 1)[1]) <= 24
    ]
    phase6b = [
        (nodeid, test_id)
        for nodeid, test_id in phase6
        if int(test_id.split("-", 1)[1]) > 24
    ]
    if phase6a:
        _write_table(
            terminalreporter,
            "PHASE-6A TESTS (TEST P6-001 ... TEST P6-024)",
            phase6a,
        )
    if phase6b:
        _write_table(
            terminalreporter,
            "PHASE-6B TESTS (TEST P6-025 ... TEST P6-048)",
            phase6b,
        )
