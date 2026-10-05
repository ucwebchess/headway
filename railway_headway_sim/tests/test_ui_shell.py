"""Application shell tests (Project page, direction control, audit page, placeholders).

These tests need ``ipywidgets``; they are skipped automatically when it is not
installed, so the model/validation/IO test suite stays dependency-light.
"""

from __future__ import annotations

import datetime
import json

import pytest

pytest.importorskip("ipywidgets")

import ipywidgets as widgets  # noqa: E402

from railway_headway_sim import Direction, ProjectController, launch_app  # noqa: E402
from railway_headway_sim.example_project import EXAMPLE_PROJECT_JSON  # noqa: E402
from railway_headway_sim.ui import NAVIGATION_TITLES, AppShell  # noqa: E402
from railway_headway_sim.ui.placeholder_pages import PLANNED_PAGES  # noqa: E402
from railway_headway_sim.ui.project_page import FIELD_ORDER  # noqa: E402
from railway_headway_sim.version import APP_VERSION  # noqa: E402


def _upload_value(filename: str, text: str) -> tuple[dict[str, object], ...]:
    """Build an ipywidgets-8 style FileUpload payload."""
    raw = text.encode("utf-8")
    return (
        {
            "name": filename,
            "type": "application/json",
            "size": len(raw),
            "content": memoryview(raw),
            "last_modified": datetime.datetime.now(datetime.timezone.utc),
        },
    )


def test_shell_builds_all_navigation_pages():
    """Regression - the shell exposes the required navigation entries."""
    shell = AppShell(ProjectController.new_project())

    assert isinstance(shell.widget, widgets.Widget)
    assert len(shell._tabs.children) == len(NAVIGATION_TITLES)
    titles = [shell._tabs.get_title(index) for index in range(len(NAVIGATION_TITLES))]
    assert titles == list(NAVIGATION_TITLES)
    for required in (
        "Project",
        "Infrastructure",
        "Stations & Platforms",
        "Signalling",
        "Rolling Stock",
        "Services & Timetable",
        "Simulation",
        "Results",
        "Scenarios",
        "Report",
        "Validation & Audit",
    ):
        assert required in titles

    shell.select_tab("Validation & Audit")
    assert shell._tabs.get_title(shell._tabs.selected_index) == "Validation & Audit"
    with pytest.raises(KeyError):
        shell.select_tab("Nonexistent page")


def test_header_shows_versions_and_status_text():
    """Regression - app version, schema version and status are visible as text."""
    controller = ProjectController.new_project(name="Header Check")
    shell = AppShell(controller)
    header = shell._header.value

    assert "Railway Track Headway Simulator" in header
    assert "Header Check" in header
    # Version text is derived from the authoritative version module (Phase 6B: 0.9.0;
    # declared version-literal adaptation, docs/PHASE1_REGRESSION_MAP.md §3).
    assert f"APP v{APP_VERSION}" in header
    assert "APP v0.9.0" in header
    assert "SCHEMA v1.0" in header
    assert "VALIDATION: VALID" in header
    assert "VALIDATED CURRENT" in header


def test_direction_buttons_drive_the_controller_and_labels():
    """Regression - the direction selector works and uses terminal names."""
    controller = ProjectController()
    controller.import_json_data(json.loads(EXAMPLE_PROJECT_JSON), source_name="example")
    shell = AppShell(controller)

    assert shell._forward_button.description.endswith("FORWARD · Alpha → Delta")
    assert shell._reverse_button.description.endswith("REVERSE · Delta → Alpha")

    json_before = controller.project.model_dump_json()
    hash_before = controller.current_project_hash

    shell._reverse_button.click()

    assert controller.direction is Direction.REVERSE
    assert controller.current_project_hash == hash_before
    assert controller.project.model_dump_json() == json_before
    assert shell._forward_button.description.startswith("▷")
    assert shell._reverse_button.description.startswith("▶")
    assert "Active direction:" in shell._direction_status.value
    assert "REVERSE · Delta → Alpha" in shell._direction_status.value


def test_project_page_edits_are_written_through_the_controller():
    """Regression - the Project page edits the canonical model, not widget state."""
    controller = ProjectController.new_project(name="Before Edit")
    shell = AppShell(controller)
    page = shell._project_page

    assert [name for name, _label, _placeholder in FIELD_ORDER] == list(page._fields)
    page._fields["project_name"].value = "After Edit"
    page._fields["origin_name"].value = "Alpha"
    page._fields["chainage_end"].value = "88.25"
    assert page._dirty is True

    page._save_button.click()

    assert controller.project.project.name == "After Edit"
    assert controller.project.reference_system.chainage_origin_name == "Alpha"
    assert controller.project.reference_system.chainage_end_km == 88.25
    assert controller.modified_since_validation is True
    assert page._dirty is False

    page._validate_button.click()
    assert controller.validation.status.value == "VALID"


def test_project_page_reimport_updates_every_widget():
    """Regression - importing refreshes the form and the summary from the model."""
    controller = ProjectController.new_project()
    shell = AppShell(controller)
    page = shell._project_page

    page._upload.value = _upload_value("example.json", EXAMPLE_PROJECT_JSON)
    page._import_button.click()

    assert controller.project.project.name == "Demo Intercity Line"
    assert page._fields["project_name"].value == "Demo Intercity Line"
    assert page._fields["origin_name"].value == "Alpha"
    assert page._fields["end_name"].value == "Delta"
    assert page._fields["chainage_end"].value == "250.4"
    kinds = [kind for _, kind in controller.object_count_rows()]
    assert sum(kinds) > 0
    assert "Demo Intercity Line" in page._summary.value


def test_audit_page_renders_and_filters_diagnostics():
    """Regression - the audit page shows counts, diagnostics and hashes."""
    controller = ProjectController()
    controller.import_json_data(json.loads(EXAMPLE_PROJECT_JSON), source_name="example")
    shell = AppShell(controller)
    audit = shell._audit_page

    for code in ("VAL-FUTURE-002",):
        assert code in audit._table_html.value
    assert "VALIDATED CURRENT" in audit._status_html.value
    assert controller.current_project_hash[:16] in audit._hashes_html.value
    assert "Application version" in audit._widget.children[3].children[2].value

    audit._severity_filter.value = "ERROR"
    assert "No diagnostics" in audit._table_html.value or "VAL-FUTURE" not in audit._table_html.value
    assert "Showing 0 of" in audit._filter_note.value

    audit._severity_filter.value = "All"
    audit._search.value = "not-in-any-diagnostic"
    assert "Showing 0 of" in audit._filter_note.value


def test_placeholder_pages_do_not_implement_engineering_calculations():
    """Regression - UI-REG-009 SUPERSEDED: Infrastructure, Stations and Rolling Stock are functional.

    Declared supersessions (see ``docs/PHASE1_REGRESSION_MAP.md`` §2): the
    Infrastructure page and the Stations & Platforms page became functional pages in
    Phase 2 (they render typed physical infrastructure data), and the Rolling Stock
    page became a functional **read-only** page in Phase 6B (it renders the loaded
    rolling-stock catalogue). The declared Phase-6B supersession replaces the
    hard-coded seven-entry placeholder list with a two-way set check against
    ``FUNCTIONAL_PAGES``; the exact placeholder string, the no-calculation assertion
    and the page-by-page rendering check are unchanged. Every page that is still
    planned stays an explicit "PLANNED FOR LATER DEVELOPMENT PHASE" placeholder with
    no calculations and no placeholder result values.
    """
    from railway_headway_sim.ui import FUNCTIONAL_PAGES, InfrastructurePage, RollingStockPage, StationsPage

    shell = AppShell(ProjectController.new_project())
    # Two-way set check (Phase-6B supersession): the functional set and the planned set are
    # disjoint and together they are exactly the navigation order - no hard-coded page list.
    assert set(FUNCTIONAL_PAGES) == set(NAVIGATION_TITLES) - set(PLANNED_PAGES)
    assert [title for title in FUNCTIONAL_PAGES if title in PLANNED_PAGES] == []
    assert [title for title in PLANNED_PAGES if title in FUNCTIONAL_PAGES] == []

    shell = AppShell(ProjectController.new_project())
    assert isinstance(shell._infrastructure_page, InfrastructurePage)
    assert isinstance(shell._stations_page, StationsPage)
    assert isinstance(shell._rolling_stock_page, RollingStockPage)
    for title in FUNCTIONAL_PAGES:
        index = list(NAVIGATION_TITLES).index(title)
        page = shell._tabs.children[index]
        assert not isinstance(page, widgets.HTML), f"{title} must be a functional page"
        rendered = json.dumps(page.get_state(), default=str)
        assert "PLANNED FOR LATER DEVELOPMENT PHASE" not in rendered

    remaining = list(PLANNED_PAGES)
    for title in remaining:
        index = list(NAVIGATION_TITLES).index(title)
        page = shell._tabs.children[index]
        assert isinstance(page, widgets.HTML)
        assert "PLANNED FOR LATER DEVELOPMENT PHASE" in page.value
        assert "performs no calculations" in page.value


def test_launch_app_builds_and_can_write_a_static_snapshot(tmp_path, monkeypatch):
    """Regression - launch_app() returns a shell and can snapshot for documentation."""
    displayed: list[object] = []
    monkeypatch.setattr("IPython.display.display", lambda *args, **kwargs: displayed.append(args))

    shell = launch_app(ProjectController.new_project(name="Launched"))
    assert isinstance(shell, AppShell)
    assert displayed, "launch_app must display the shell when embed=True"

    snapshot = tmp_path / "snapshot.html"
    shell = launch_app(embed=False, snapshot_path=snapshot)
    assert snapshot.exists()
    assert "Railway Track Headway Simulator" in snapshot.read_text(encoding="utf-8")


def test_controller_listeners_refresh_the_shell_without_manual_calls():
    """Regression - programmatic controller changes refresh the UI automatically."""
    controller = ProjectController.new_project(name="Listener Check")
    shell = AppShell(controller)

    controller.update_metadata(name="Renamed Programmatically")

    assert "Renamed Programmatically" in shell._header.value
    assert shell._project_page._fields["project_name"].value == "Renamed Programmatically"
