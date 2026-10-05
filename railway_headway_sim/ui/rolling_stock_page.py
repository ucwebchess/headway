"""Rolling Stock page (Phase 6B) — the read-only view of the loaded stock catalogue.

Stage 6A delivered the typed rolling-stock catalogue and its validity rules; Stage 6B
turns the placeholder navigation entry into a functional, **read-only** page that shows
what the catalogue says. The page holds four sub-tabs:

* **Overview** — one table per stock type with its identity, geometry, mass (including
  the derived effective mass the model's own property reports) and performance limits;
* **Traction** — the stored effort parameters, the transition speed of the frozen
  piecewise model and the effort curve drawn from
  :func:`railway_headway_sim.physics.rolling_stock_series.tractive_effort_series_n`;
* **Resistance** — the stored running-resistance parameters, the curve-resistance model
  source and the resistance curve drawn from
  :func:`railway_headway_sim.physics.rolling_stock_series.running_resistance_series_n`;
* **Braking** — the stored service-braking and supervision reference decelerations.

Contract of this page:

* **read-only** — it declares no editable widget, stages no draft, commits nothing and
  writes no file. The draft mechanism (``APP-EDIT-002``) is deliberately *not* wired
  here: rolling stock lives in its companion file, not in the project document, so the
  project draft mechanism does not apply;
* **no calculation** — every number shown comes either from a stored field of the
  loaded catalogue, from a read-only property of the model, or from a physics series
  function. The page computes no curve, no transition speed and no derived mass of its
  own: the plot points are the series the physics package returned;
* **no motion** — this is a display of stored data and of two sampled series at chosen
  speeds. There is no trajectory, no speed envelope, no acceleration, no integration,
  no time step and no simulation anywhere here;
* **never blocks the shell** — an absent or unparsable companion file is reported as a
  message on the page; the page never raises while the application shell is built.

The catalogue is read through :func:`railway_headway_sim.models.rolling_stock.load_rolling_stock_catalogue`
on the delivered companion file ``examples/GRR-01-rolling-stock.json`` (overridable for
tests and for a caller that already holds a catalogue).
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Union

import ipywidgets as widgets

from ..models.enums import Severity
from ..models.rolling_stock import RollingStock, RollingStockCatalogue, load_rolling_stock_catalogue
from ..physics.rolling_stock_series import (
    DEFAULT_STEP_KMH,
    running_resistance_series_n,
    tractive_effort_series_n,
)
from ..physics.tractive_effort import transition_speed_kmh
from ..version import APP_PHASE
from . import formatting as fmt
from . import svg_render
from .page_editors import SubTabHost
from .project_page import panel_box

#: Sub-tab titles of the page, in display order.
SUB_TAB_TITLES: tuple[str, ...] = ("Overview", "Traction", "Resistance", "Braking")

#: Path of the delivered rolling-stock companion file, relative to the repository root.
REFERENCE_STOCK_PATH: Path = (
    Path(__file__).resolve().parents[2] / "examples" / "GRR-01-rolling-stock.json"
)

#: Sample step [km/h] used for the two curves of the delivered page.
PAGE_STEP_KMH: float = DEFAULT_STEP_KMH


def _text(value: object) -> str:
    """Return the display text of a stored value (pure presentation, no rounding of data)."""
    if isinstance(value, float):
        return repr(value)
    return str(value)


class RollingStockPage:
    """Read-only Rolling Stock page: Overview | Traction | Resistance | Braking."""

    def __init__(
        self,
        catalogue_source: Optional[Union[str, Path, RollingStockCatalogue]] = None,
        *,
        step_kmh: float = PAGE_STEP_KMH,
    ) -> None:
        self._source = REFERENCE_STOCK_PATH if catalogue_source is None else catalogue_source
        self._step_kmh = float(step_kmh)
        self._catalogue: Optional[RollingStockCatalogue] = None
        self._load_error: str = ""
        self._load_catalogue()
        self._build()

    # -- catalogue access --------------------------------------------------
    def _load_catalogue(self) -> None:
        """Load the catalogue once, reporting (never raising) an unusable source."""
        if isinstance(self._source, RollingStockCatalogue):
            self._catalogue = self._source
            return
        try:
            self._catalogue = load_rolling_stock_catalogue(self._source)
        except Exception as error:  # reported on the page, never repaired, never fatal
            self._catalogue = None
            self._load_error = f"{type(error).__name__}: {error}"

    @property
    def catalogue(self) -> Optional[RollingStockCatalogue]:
        """Return the loaded catalogue, or ``None`` when the source could not be read."""
        return self._catalogue

    def stocks(self) -> tuple[RollingStock, ...]:
        """Return the loaded stock types in catalogue order (empty when nothing is loaded)."""
        if self._catalogue is None:
            return ()
        return tuple(self._catalogue.rolling_stock)

    def stock(self, stock_id: str) -> Optional[RollingStock]:
        """Return the stock type with *stock_id*, or ``None``."""
        for candidate in self.stocks():
            if candidate.id == stock_id:
                return candidate
        return None

    # -- series access (thin delegation to the physics package) ------------
    def tractive_effort_series_n(
        self, stock_id: str, step_kmh: Optional[float] = None
    ) -> tuple[tuple[float, float], ...]:
        """Return the effort series of *stock_id* produced by the physics package."""
        stock = self.stock(stock_id)
        if stock is None:
            return ()
        return tractive_effort_series_n(stock, self._step_kmh if step_kmh is None else step_kmh)

    def running_resistance_series_n(
        self, stock_id: str, step_kmh: Optional[float] = None
    ) -> tuple[tuple[float, float], ...]:
        """Return the resistance series of *stock_id* produced by the physics package."""
        stock = self.stock(stock_id)
        if stock is None:
            return ()
        return running_resistance_series_n(stock, self._step_kmh if step_kmh is None else step_kmh)

    # -- construction ------------------------------------------------------
    def _build(self) -> None:
        self._notice = widgets.HTML(value="")
        self._overview = widgets.HTML(value="")
        self._traction = widgets.HTML(value="")
        self._traction_plot = widgets.HTML(value="")
        self._traction_points = widgets.HTML(value="")
        self._resistance = widgets.HTML(value="")
        self._resistance_plot = widgets.HTML(value="")
        self._resistance_points = widgets.HTML(value="")
        self._braking = widgets.HTML(value="")
        self._effort_plot_svg: dict[str, str] = {}
        self._resistance_plot_svg: dict[str, str] = {}

        self._host = SubTabHost(
            "Rolling Stock — read-only view of the loaded catalogue",
            (
                (
                    "Overview",
                    widgets.VBox(
                        [
                            panel_box(
                                "Stock types in the loaded catalogue",
                                [self._overview],
                                subtitle="identity, geometry, mass and performance limits — stored values",
                            ),
                        ]
                    ),
                ),
                (
                    "Traction",
                    widgets.VBox(
                        [
                            panel_box(
                                "Stored tractive-effort parameters (read-only)",
                                [self._traction],
                                subtitle="what the catalogue says about this stock type",
                            ),
                            panel_box(
                                "Effort curve",
                                [self._traction_plot, self._traction_points],
                                subtitle="sampled by the physics package, drawn read-only",
                            ),
                        ]
                    ),
                ),
                (
                    "Resistance",
                    widgets.VBox(
                        [
                            panel_box(
                                "Stored running-resistance parameters (read-only)",
                                [self._resistance],
                                subtitle="coefficients, their units and the curve-resistance source",
                            ),
                            panel_box(
                                "Running-resistance curve",
                                [self._resistance_plot, self._resistance_points],
                                subtitle="sampled by the physics package, drawn read-only",
                            ),
                        ]
                    ),
                ),
                (
                    "Braking",
                    widgets.VBox(
                        [
                            panel_box(
                                "Stored braking references (read-only)",
                                [self._braking],
                                subtitle="service braking and supervision reference decelerations",
                            ),
                        ]
                    ),
                ),
            ),
        )

        self._widget = widgets.VBox(
            [self._notice, self._host.widget],
            layout=widgets.Layout(margin="8px 0px 0px 0px"),
        )
        self.refresh()

    # -- rendering ---------------------------------------------------------
    def refresh(self) -> None:
        """Re-render every sub-tab from the loaded catalogue (read-only, no recalculation)."""
        if self._catalogue is None:
            self._notice.value = fmt.message_html(
                f"The rolling-stock catalogue could not be read: {self._load_error}", severity=Severity.WARNING
            )
            for holder in (self._overview, self._traction, self._traction_plot,
                           self._traction_points, self._resistance, self._resistance_plot,
                           self._resistance_points, self._braking):
                holder.value = fmt.section_note_html("No rolling-stock catalogue is loaded.")
            return

        self._notice.value = fmt.message_html(
            "Read-only view of the loaded rolling-stock catalogue "
            f"({len(self.stocks())} stock type(s) from "
            f"{Path(self._source).name if not isinstance(self._source, RollingStockCatalogue) else 'the given catalogue'}). "
            "Editing rolling stock is a later, deliberate stage: this page stages no draft and "
            f"writes nothing. Not part of {APP_PHASE}.",
            severity=Severity.INFO,
        )
        self._overview.value = self._overview_html()
        self._traction.value = self._effort_parameters_html()
        self._resistance.value = self._resistance_parameters_html()
        self._braking.value = self._braking_html()
        self._render_effort_plots()
        self._render_resistance_plots()

    def _overview_html(self) -> str:
        """Render one read-only parameter table per stock type."""
        blocks: list[str] = []
        for stock in self.stocks():
            rows = (
                ("id", stock.id),
                ("name", stock.name),
                ("category", stock.category.value),
                ("data_status", stock.data_status),
                ("manufacturer_data", _text(stock.manufacturer_data)),
                ("length_m", _text(stock.length_m)),
                ("static_mass_t", _text(stock.mass.static_mass_t)),
                ("rotating_mass_factor", _text(stock.mass.rotating_mass_factor)),
                ("effective_mass_kg", _text(stock.effective_mass_kg)),
                ("max_speed_kmh", _text(stock.max_speed_kmh)),
                (
                    "max_operational_acceleration_mps2",
                    _text(stock.performance_limits.max_operational_acceleration_mps2),
                ),
            )
            blocks.append(
                fmt.panel(
                    f"{stock.id} — {stock.name} ({stock.category.value}, {stock.data_status})",
                    fmt.kv_table_html(rows),
                    tone="steel",
                )
            )
        if not blocks:
            return fmt.section_note_html("The loaded catalogue declares no stock type.")
        return "".join(blocks)

    def _effort_parameters_html(self) -> str:
        """Render the stored effort parameters and the transition speed the physics package reports."""
        blocks: list[str] = []
        for stock in self.stocks():
            rows = (
                ("traction.model", stock.traction.model.value),
                ("rated_power_kw", _text(stock.traction.rated_power_kw)),
                ("max_tractive_effort_kn", _text(stock.traction.max_tractive_effort_kn)),
                (
                    "transition speed [km/h]",
                    _text(
                        transition_speed_kmh(
                            float(stock.traction.max_tractive_effort_kn),
                            float(stock.traction.rated_power_kw),
                        )
                    ),
                ),
                (
                    "stored effort points (traction_curve)",
                    "none declared"
                    if not stock.traction.traction_curve
                    else f"{len(stock.traction.traction_curve)} stored point(s)",
                ),
            )
            blocks.append(fmt.panel(f"{stock.id}", fmt.kv_table_html(rows), tone="steel"))
        if not blocks:
            return fmt.section_note_html("The loaded catalogue declares no stock type.")
        return "".join(blocks)

    def _resistance_parameters_html(self) -> str:
        """Render the stored running-resistance parameters and the curve-resistance source."""
        blocks: list[str] = []
        for stock in self.stocks():
            rows = (
                ("running_resistance.model", stock.running_resistance.model.value),
                ("running_resistance.formula", stock.running_resistance.formula),
                ("coefficients.A [kN]", _text(stock.running_resistance.coefficients.A)),
                ("coefficients.B", _text(stock.running_resistance.coefficients.B)),
                ("coefficients.C", _text(stock.running_resistance.coefficients.C)),
                ("coefficient_speed_unit", stock.running_resistance.coefficient_speed_unit),
                ("output_force_unit", stock.running_resistance.output_force_unit),
                ("curve_resistance.model_source", stock.curve_resistance.model_source),
            )
            blocks.append(fmt.panel(f"{stock.id}", fmt.kv_table_html(rows), tone="steel"))
        if not blocks:
            return fmt.section_note_html("The loaded catalogue declares no stock type.")
        return "".join(blocks)

    def _braking_html(self) -> str:
        """Render the stored service-braking and supervision reference decelerations."""
        blocks: list[str] = []
        for stock in self.stocks():
            rows = (
                (
                    "service_braking.model",
                    stock.service_braking.model.value,
                ),
                (
                    "service_braking.reference_deceleration_mps2",
                    _text(stock.service_braking.reference_deceleration_mps2),
                ),
                (
                    "etcs_supervision.reference_deceleration_mps2",
                    _text(stock.etcs_supervision.reference_deceleration_mps2),
                ),
                ("etcs_supervision.model_role", stock.etcs_supervision.model_role),
            )
            blocks.append(fmt.panel(f"{stock.id}", fmt.kv_table_html(rows), tone="steel"))
        if not blocks:
            return fmt.section_note_html("The loaded catalogue declares no stock type.")
        return "".join(blocks)

    def _series_plot_html(
        self, series: tuple[tuple[float, float], ...], *, title: str, unit: str, colour: str
    ) -> str:
        """Return the SVG of one sampled series (presentation only — the points are given)."""
        if len(series) < 2:
            return svg_render.message_svg(f"No curve for {title}: fewer than two samples.")
        low_speed = series[0][0]
        high_speed = series[-1][0]
        values = [value for _speed, value in series]
        low_value = min(values)
        high_value = max(values)
        if high_value == low_value:  # a flat curve still needs a non-degenerate axis
            high_value = low_value + 1.0
        return svg_render.svg_open(1020, 300, title=title) + svg_render.line_chart(
            series,
            low_chainage=low_speed,
            high_chainage=high_speed,
            low_value=low_value,
            high_value=high_value,
            title=title,
            unit=unit,
            colour=colour,
            subtitle=f"speed [km/h] from {low_speed:g} to {high_speed:g}, {len(series)} sample(s)",
        )

    def _series_table_html(
        self, series: tuple[tuple[float, float], ...], *, unit: str
    ) -> str:
        """Return the read-only sample table of one series."""
        rows = [(f"{speed:.1f}", f"{value:.3f}") for speed, value in series]
        return fmt.data_table_html(("speed [km/h]", unit), rows, empty_text="No samples.")

    def _render_effort_plots(self) -> None:
        """Draw the effort curve of every stock type from the physics series."""
        plots: list[str] = []
        tables: list[str] = []
        svgs: dict[str, str] = {}
        for stock in self.stocks():
            series = tractive_effort_series_n(stock, self._step_kmh)
            svg = self._series_plot_html(
                series,
                title=f"{stock.id} — available tractive effort",
                unit="effort [N]",
                colour=svg_render.PALETTE["elevation"],
            )
            svgs[stock.id] = svg
            plots.append(svg)
            tables.append(
                fmt.panel(f"{stock.id}", self._series_table_html(series, unit="effort [N]"), tone="steel")
            )
        self._effort_plot_svg = svgs
        self._traction_plot.value = "".join(plots) or fmt.section_note_html("No stock type loaded.")
        self._traction_points.value = "".join(tables)

    def _render_resistance_plots(self) -> None:
        """Draw the running-resistance curve of every stock type from the physics series."""
        plots: list[str] = []
        tables: list[str] = []
        svgs: dict[str, str] = {}
        for stock in self.stocks():
            series = running_resistance_series_n(stock, self._step_kmh)
            svg = self._series_plot_html(
                series,
                title=f"{stock.id} — running resistance",
                unit="resistance [N]",
                colour=svg_render.PALETTE["curve"],
            )
            svgs[stock.id] = svg
            plots.append(svg)
            tables.append(
                fmt.panel(
                    f"{stock.id}",
                    self._series_table_html(series, unit="resistance [N]"),
                    tone="steel",
                )
            )
        self._resistance_plot_svg = svgs
        self._resistance_plot.value = "".join(plots) or fmt.section_note_html("No stock type loaded.")
        self._resistance_points.value = "".join(tables)

    # -- accessors ---------------------------------------------------------
    @property
    def widget(self) -> widgets.Widget:
        """Return the root widget of this page."""
        return self._widget

    def select_sub_tab(self, title: str) -> bool:
        """Select a sub-tab by title (used by the shell and tests)."""
        return self._host.select(title)

    def sub_tab_titles(self) -> tuple[str, ...]:
        """Return the sub-tab titles in display order."""
        return self._host.titles()

    def selected_sub_tab(self) -> str:
        """Return the visible sub-tab title."""
        return self._host.selected_title()

    def series_step_kmh(self) -> float:
        """Return the sampling step [km/h] the two curves use."""
        return self._step_kmh

    def effort_plot_svg(self, stock_id: str) -> str:
        """Return the rendered effort-curve SVG of one stock type (empty when absent)."""
        return getattr(self, "_effort_plot_svg", {}).get(stock_id, "")

    def resistance_plot_svg(self, stock_id: str) -> str:
        """Return the rendered resistance-curve SVG of one stock type (empty when absent)."""
        return getattr(self, "_resistance_plot_svg", {}).get(stock_id, "")

    def rendered_text(self) -> str:
        """Return the rendered text of every read-only panel (used by tests and reports)."""
        return " | ".join(
            holder.value
            for holder in (
                self._notice,
                self._overview,
                self._traction,
                self._traction_plot,
                self._traction_points,
                self._resistance,
                self._resistance_plot,
                self._resistance_points,
                self._braking,
            )
        )

    def help_text(self) -> str:
        """Return a textual description of the page for the quick guide."""
        return (
            "Sub-tabs: "
            + ", ".join(self.sub_tab_titles())
            + ". The page is read-only: it shows the stored stock types and the effort and "
            "running-resistance curves the physics package samples. No draft, no editing and "
            "no train motion."
        )
