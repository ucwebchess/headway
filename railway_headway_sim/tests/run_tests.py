"""Test runner for the Phase-1 suite.

Usage (from a notebook or a shell)::

    python -m railway_headway_sim.tests.run_tests
    # or
    from railway_headway_sim.tests.run_tests import run_tests
    run_tests()               # verbose output, returns a pytest exit code

The runner prints a per-test PASS/FAIL line and a summary table for the numbered
acceptance tests (TEST P1-001 ... TEST P1-012).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional, Sequence

TESTS_DIR = Path(__file__).resolve().parent
PACKAGE_PARENT = TESTS_DIR.parent.parent


def run_tests(extra_args: Optional[Sequence[str]] = None, *, verbose: bool = True) -> int:
    """Run the Phase-1 + Phase-2 test suite and return the pytest exit code (0 = all passed)."""
    try:
        import pytest
    except ImportError:  # pragma: no cover - environment dependent
        print(
            "pytest is not installed. Install it with 'pip install pytest' "
            "(handled automatically by the Colab notebook setup cell)."
        )
        return 2

    if str(PACKAGE_PARENT) not in sys.path:
        sys.path.insert(0, str(PACKAGE_PARENT))

    args = [str(TESTS_DIR), "-p", "no:cacheprovider", "--tb=short"]
    args += ["-v"] if verbose else ["-q"]
    if extra_args:
        args.extend(extra_args)

    print("Running the Phase-1 + Phase-2 test suite:")
    print(" ".join(["pytest", *args]))
    exit_code = int(pytest.main(args))
    print("")
    print("Test suite result:", "PASS - all tests passed" if exit_code == 0 else f"FAIL - pytest exit code {exit_code}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(run_tests(sys.argv[1:]))
