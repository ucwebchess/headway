"""Build (or rebuild) the GRR-01 reference project files and the Phase-1 manifest.

Run from the repository root::

    python3 build_reference_projects.py

Outputs
-------
``examples/GRR-01.json``
    GRR-01 Part A reference project (typed physical infrastructure, schema 1.0),
    exported through the real import -> model -> export path so that the file is
    exactly the canonical serialization of the fixture.
``docs/GRR-01_FROZEN_PHYSICAL_v1.0.json``
    Pre-amendment frozen evidence file: identical except that
    ``STOP-V-P1-R.position_m`` keeps its frozen value 220.0 m and
    ``provenance.approved_amendments`` is absent.
``docs/PHASE1_SOURCE_MANIFEST.json``
    SHA-256 inventory of the accepted Phase-1 source tree (only written when the
    accepted snapshot is available at ``/tmp/phase1_snapshot``; the file records
    the tree as delivered for Phase 1).

The script is deterministic: no timestamps are generated, nothing is rewritten
in the fixture, and re-running it produces byte-identical files.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from railway_headway_sim.infrastructure import grr_audit, grr_fixtures
from railway_headway_sim.io import import_project_from_data, project_hash, to_json_text
from railway_headway_sim.validation import validate_document

ROOT = Path(__file__).resolve().parent
EXAMPLES_DIR = ROOT / "examples"
DOCS_DIR = ROOT / "docs"
PHASE1_SNAPSHOT = Path("/tmp/phase1_snapshot")


def _canonical_text(document: dict, *, label: str) -> str:
    """Import *document* and return the canonical exported JSON text."""
    outcome = import_project_from_data(document, source_name=label)
    if not outcome.ok or outcome.project is None:
        print(f"FAIL - {label} did not import:", file=sys.stderr)
        for diagnostic in outcome.result.diagnostics:
            print("   ", diagnostic.format_line(), file=sys.stderr)
        raise SystemExit(1)
    text = to_json_text(outcome.project)
    # import -> export -> import -> export must be byte-stable.
    again = import_project_from_data(json.loads(text), source_name=label + " (roundtrip)")
    if not again.ok or again.project is None or to_json_text(again.project) != text:
        print(f"FAIL - {label} is not byte-stable across a roundtrip.", file=sys.stderr)
        raise SystemExit(1)
    if (
        again.project.project.created_utc != outcome.project.project.created_utc
        or again.project.project.modified_utc != outcome.project.project.modified_utc
    ):
        print(f"FAIL - {label} roundtrip modified created_utc/modified_utc.", file=sys.stderr)
        raise SystemExit(1)
    print(
        f"  {label}: {len(text):,} bytes, hash {project_hash(outcome.project)[:16]}, "
        "roundtrip byte-stable, timestamps preserved"
    )
    return text


def build_examples() -> None:
    """Write the two GRR-01 JSON documents."""
    print("GRR-01 reference project files")
    EXAMPLES_DIR.mkdir(exist_ok=True)
    DOCS_DIR.mkdir(exist_ok=True)

    amended = _canonical_text(grr_fixtures.build_grr01_document(), label="GRR-01 (amended)")
    frozen = _canonical_text(grr_fixtures.frozen_document(), label="GRR-01 (frozen v1.0)")

    (EXAMPLES_DIR / "GRR-01.json").write_text(amended + "\n", encoding="utf-8")
    (DOCS_DIR / "GRR-01_FROZEN_PHYSICAL_v1.0.json").write_text(frozen + "\n", encoding="utf-8")
    print(f"  wrote {EXAMPLES_DIR / 'GRR-01.json'}")
    print(f"  wrote {DOCS_DIR / 'GRR-01_FROZEN_PHYSICAL_v1.0.json'}")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_phase1_manifest() -> None:
    """Record the accepted Phase-1 source tree as delivered (if available)."""
    print("Phase-1 source manifest")
    if not PHASE1_SNAPSHOT.is_dir():
        print(f"  skipped - accepted snapshot not found at {PHASE1_SNAPSHOT}")
        return
    entries = []
    for path in sorted(PHASE1_SNAPSHOT.rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts:
            continue
        relative = path.relative_to(PHASE1_SNAPSHOT).as_posix()
        entries.append(
            {
                "path": relative,
                "bytes": path.stat().st_size,
                "sha256": _sha256(path),
            }
        )
    manifest = {
        "description": (
            "SHA-256 inventory of the ACCEPTED Phase-1 source tree as delivered "
            "(before any Phase-2 edit). Phase 2 extends this tree in place; the "
            "superseded/adapted tests are listed in PHASE1_REGRESSION_MAP.md."
        ),
        "phase": "Phase 1 - Application Foundation",
        "app_version": "0.1.0",
        "schema_version": "1.0",
        "test_summary": "66 passed - PASS - all tests passed (18/18 acceptance)",
        "file_count": len(entries),
        "files": entries,
    }
    out = DOCS_DIR / "PHASE1_SOURCE_MANIFEST.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"  {manifest['file_count']} files recorded in {out}")


def report_grr01_status() -> None:
    """Validate GRR-01 and print the Section-BA contradiction scan."""
    print("GRR-01 validation")
    outcome = validate_document(grr_fixtures.build_grr01_document(), source_name="GRR-01")
    print(f"  status: {outcome.result.status.value} - {outcome.result.summary_with_scope()}")
    print("GRR-01 Part A contradiction scan")
    for finding in grr_audit.scan_contradictions():
        print("  " + finding.format_line())


def main() -> int:
    build_examples()
    build_phase1_manifest()
    report_grr01_status()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
