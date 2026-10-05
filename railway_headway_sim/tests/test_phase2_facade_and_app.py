"""Phase-2 tests: validation facade, controller draft mechanism, UI pages and scope guards.

Acceptance tests covered here: TEST P2-025 ... TEST P2-028.
"""

from __future__ import annotations

import json

import pytest

import railway_headway_sim
from railway_headway_sim import ProjectController
from railway_headway_sim.infrastructure import grr_fixtures
from railway_headway_sim.models.diagnostics import ValidationResult
from railway_headway_sim.models.enums import Direction, Severity, ValidationScope
from railway_headway_sim.models.project import Project
from railway_headway_sim.validation import codes, validate_document

from .phase2_support import (
    codes_of,
    diagnostics_with_code,
    entry,
    grr_document,
    has_code,
    load_project,
    roundtrip_text,
    validate,
)
from .support import example_document


# ---------------------------------------------------------------------------
# TEST P2-025
# ---------------------------------------------------------------------------
def test_p2_025_validation_facade_scope_and_single_result_model():
    """TEST P2-025 - physical projects get Phase-2 scope; legacy projects keep Phase-1 behaviour."""
    physical = validate(grr_document()).result
    assert physical.status.value == "VALID"
    assert physical.error_count == 0
    assert physical.scope is ValidationScope.PHASE2_PHYSICAL_INFRASTRUCTURE
    assert physical.is_phase2_physical()
    assert "PHASE-2 PHYSICAL INFRASTRUCTURE" in physical.summary_with_scope()
    assert isinstance(physical, ValidationResult)

    legacy = validate(example_document()).result
    assert legacy.scope is ValidationScope.BASIC_PROJECT
    assert not legacy.is_phase2_physical()
    phase2_codes = tuple(
        code for code in codes_of(legacy) if code.startswith(("VAL-INFR-", "VAL-REGISTRY-", "VAL-GEOM-"))
    )
    assert phase2_codes == (), "legacy projects must not receive Phase-2 diagnostics"
    # ... and the Phase-1 "not yet validated" INFO for infrastructure stays for legacy projects
    assert has_code(legacy, codes.VAL_FUTURE_002)

    # the same result model is used everywhere (no duplicate result classes)
    in_memory = railway_headway_sim.validate_in_memory_project(load_project(grr_document()))
    assert isinstance(in_memory, ValidationResult)
    assert in_memory.scope is ValidationScope.PHASE2_PHYSICAL_INFRASTRUCTURE

    # a document that cannot even be parsed has no assurance scope at all
    broken = validate_document("this is not a JSON object").result
    assert broken.scope is None
    assert broken.scope_text() == "(scope not determined)"
    assert broken.status.value == "INVALID"


# ---------------------------------------------------------------------------
# TEST P2-026
# ---------------------------------------------------------------------------
def test_p2_026_controller_draft_mechanism_blocks_export():
    """TEST P2-026 - an invalid uncommitted draft is rejected (APP-EDIT-002) and blocks export."""
    controller = ProjectController()
    controller.replace_project(load_project(grr_document()), message="GRR-01 loaded")
    controller.validate_project()
    hash_before = controller.current_project_hash

    # a valid draft can be staged, inspected and committed
    good = grr_document()
    good["project"]["description"] = "Edited description (draft)"
    staged = controller.stage_draft(good, description="metadata edit")
    assert staged.status.value == "VALID"
    assert controller.draft_pending is True
    assert controller.draft_blocks_export is False
    assert controller.current_project_hash == hash_before, "staging must not touch the project"

    committed = controller.commit_draft()
    assert committed.status.value == "VALID"
    assert controller.draft_pending is False
    assert controller.project.project.description == "Edited description (draft)"

    # an invalid draft is rejected on commit and leaves the project untouched
    hash_before = controller.current_project_hash
    bad = grr_document()
    entry(bad, "tracks", "TR-C-P2")["from_node"] = "N-NOT-THERE"
    staged = controller.stage_draft(bad, description="broken topology")
    assert staged.status.value == "INVALID"
    assert controller.draft_blocks_export is True

    rejected = controller.commit_draft()
    assert has_code(rejected, codes.APP_EDIT_002)
    assert rejected.diagnostics[0].severity is Severity.ERROR
    assert controller.current_project_hash == hash_before
    assert controller.draft_pending is True, "a rejected draft stays staged until discarded"

    # export is blocked while the invalid draft is staged
    outcome = controller.export_json(download=False, directory="/tmp")
    assert outcome is None
    assert controller.state.last_action == "export_rejected"
    assert "block" in controller.state.last_message.lower()

    # discarding clears the block; export works again
    controller.discard_draft()
    assert controller.draft_pending is False
    assert controller.draft_blocks_export is False
    outcome = controller.export_json(download=False, directory="/tmp")
    assert outcome is not None and outcome.filename.endswith(".json")

    # committing without a draft is rejected as well
    assert has_code(controller.commit_draft(), codes.APP_EDIT_002)


# ---------------------------------------------------------------------------
# TEST P2-027
# ---------------------------------------------------------------------------
def test_p2_027_ui_pages_are_functional_and_read_only(monkeypatch):
    """TEST P2-027 - Infrastructure + Stations pages render typed data and never edit it."""
    pytest.importorskip("ipywidgets")
    from railway_headway_sim.ui import AppShell, InfrastructurePage, NAVIGATION_TITLES, StationsPage

    controller = ProjectController()
    controller.replace_project(load_project(grr_document()), message="GRR-01 loaded")
    controller.validate_project()
    shell = AppShell(controller)
    hash_before = controller.current_project_hash

    assert "Infrastructure" in NAVIGATION_TITLES and "Stations & Platforms" in NAVIGATION_TITLES
    infrastructure_index = list(NAVIGATION_TITLES).index("Infrastructure")
    stations_index = list(NAVIGATION_TITLES).index("Stations & Platforms")
    assert isinstance(shell._tabs.children[infrastructure_index], type(shell._infrastructure_page.widget))
    assert isinstance(shell._tabs.children[stations_index], type(shell._stations_page.widget))
    assert isinstance(shell._infrastructure_page, InfrastructurePage)
    assert isinstance(shell._stations_page, StationsPage)

    page = shell._infrastructure_page
    inventory_html = page._inventory.value
    for count in grr_fixtures.GRR01_EXPECTED_COUNTS.values():
        assert str(count) in inventory_html  # every frozen count is on the page
    assert "LYR-MAIN" in page._overview.value
    assert "PHASE-2 PHYSICAL INFRASTRUCTURE" in page._overview.value
    assert "N-ALP-W" in page._nodes.value and "TR-C-P2" in page._edges.value
    assert "SPR-08" in page._speed.value  # the single REVERSE restriction
    topology_summary = page._topology_summary.value
    assert "Connected components" in topology_summary and ">1<" in topology_summary

    stations = shell._stations_page
    assert "STA-ALPHA" in stations._stations.value and "STA-DELTA" in stations._stations.value
    assert "PLT-CEN-P2" in stations._platforms.value
    assert "STOP-C-P2-DEP" in stations._marks.value
    footprints_html = stations._footprints.value
    assert "STOP-C-P2-DEP" in footprints_html
    assert "infringement" in footprints_html  # the 12 m rear infringement is reported, not hidden
    assert "OBS-XC24" in stations._observations.value

    # the edge-sequence inspector runs through the package topology utility
    page._sequence_input.value = "TR-C-E-X-U1, TR-O-CEN-VAL-ML1"
    page._handle_sequence_check(None)
    assert "continuous" in page._sequence_result.value.lower()
    page._sequence_input.value = "TR-C-P1, TR-O-CEN-VAL-ML1"
    page._handle_sequence_check(None)
    assert "break" in page._sequence_result.value.lower()

    # no page interaction changed the project
    assert controller.current_project_hash == hash_before
    assert shell._controller.project is controller.project


# ---------------------------------------------------------------------------
# TEST P2-028
# ---------------------------------------------------------------------------
def test_p2_028_no_out_of_scope_capability_or_result():
    """TEST P2-028 - Section D: no train dynamics, signalling, headway or capacity anywhere."""
    import ast
    import pathlib
    import re

    package_root = pathlib.Path(railway_headway_sim.__file__).parent
    # Phase-5A moved "davis" and "roeckl" out of this list: they are now allowed physics
    # utilities, but only inside the physics package (see the allowed-surface assertion
    # below, which replaces "no longer forbidden" by "forbidden everywhere except there").
    # Declared adaptation A1 (Phase 5B): Stage 5B added a second module to that package
    # (physics/along_route.py), so the allowed surface is the physics *package*; every other
    # module of the project is still scanned exactly as before.
    forbidden_names = (
        "headway",
        "blocking_time",
        "occupation_time",
        "residual_occupancy",
        "speed_envelope",
        "traction",
        "braking_curve",
        "monte_carlo",
        "uic406",
    )
    section_d = (package_root.parent / "docs" / "SECTION_D_PATTERNS.md").read_text(encoding="utf-8")
    allowed_start = section_d.index("## 2.1")
    allowed_end = section_d.index("\n## ", allowed_start + 1)
    allowed_paragraph = (
        section_d[allowed_start:allowed_end].split("\n", 1)[1].strip().split("\n\n", 1)[0]
    )
    allowed_names = tuple(re.findall(r"`([^`]+)`", allowed_paragraph))
    assert allowed_names == (
        "Davis",
        "Roeckl",
        "rolling resistance",
        "curve resistance",
        "gradient force",
    ), f"the Phase-5A allowed list changed: {allowed_names}"

    offenders: list[str] = []
    allowed_offenders: list[str] = []
    allowed_package = package_root / "physics"
    for path in sorted(package_root.rglob("*.py")):
        if "tests" in path.parts or path.name in {"codes.py", "grr_audit.py"}:
            # the code catalogue and the audit module may *name* the out-of-scope
            # concepts in order to forbid them; they must not implement them.
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                lowered = node.name.lower()
                if any(name in lowered for name in forbidden_names):
                    offenders.append(f"{path.name}:{node.name}")
                if (
                    any(token.lower() in lowered for token in allowed_names)
                    and allowed_package not in path.parents
                ):
                    allowed_offenders.append(f"{path.name}:{node.name}")
    assert offenders == [], f"out-of-scope implementation found: {offenders}"
    assert allowed_offenders == [], (
        f"a Phase-5A allowed token appears outside the physics package: {allowed_offenders}"
    )

    # the reference project contains static physical data only (key-based, Section BA-12)
    from railway_headway_sim.infrastructure import grr_audit

    findings = {finding.check_id: finding for finding in grr_audit.scan_contradictions()}
    assert findings["BA-12"].severity == "OK"
    assert grr_audit.scan_summary()["contradictions"] == []
    text = roundtrip_text(grr_document())
    for result_key in grr_audit.FORBIDDEN_RESULT_KEYS:
        assert f'"{result_key}"' not in text

    # the UI's planned pages still declare their work as not implemented
    from railway_headway_sim.ui import FUNCTIONAL_PAGES
    from railway_headway_sim.ui.placeholder_pages import PLANNED_PAGES

    # Declared adaptation A7 (Phase 6B): Stage 6B turns "Rolling Stock" into a functional
    # read-only page, so the two hard-coded sets of Stage 2 cannot survive. The same claims
    # are now stated structurally, and stay true for every later stage: both sets are drawn
    # from the navigation order, they are disjoint, together they cover every navigation
    # entry, the Phase-6B page is functional (and no longer planned), and every planned
    # entry still declares its intended content. Nothing is loosened - a page that is
    # neither functional nor planned, or that is both, still fails.
    from railway_headway_sim.ui.app_shell import NAVIGATION_TITLES

    assert set(FUNCTIONAL_PAGES) <= set(NAVIGATION_TITLES)
    assert set(PLANNED_PAGES) <= set(NAVIGATION_TITLES)
    assert set(FUNCTIONAL_PAGES) & set(PLANNED_PAGES) == set()
    assert set(FUNCTIONAL_PAGES) | set(PLANNED_PAGES) == set(NAVIGATION_TITLES)
    assert "Rolling Stock" in FUNCTIONAL_PAGES and "Rolling Stock" not in PLANNED_PAGES
    for items in PLANNED_PAGES.values():
        assert items and all(isinstance(item, str) for item in items)

    # the GRR-01 document carries no simulated arrival/departure time fields
    document = grr_document()
    serialized = json.dumps(document)
    assert "arrival_time" not in serialized and "departure_time" not in serialized
    assert document["project"]["data_status"] == "SYNTHETIC"
    assert document["project"]["engineering_status"] == "REFERENCE_ASSUMPTIONS"
    assert document["project"]["project_type"] == "REFERENCE_TEST_PROJECT"
    assert Project.model_validate(document).project.id == grr_fixtures.GRR01_PROJECT_ID
    assert Direction.FORWARD.value == "FORWARD"
    assert not diagnostics_with_code(validate(document).result, codes.APP_EDIT_002)
