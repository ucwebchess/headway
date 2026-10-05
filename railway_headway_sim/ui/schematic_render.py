"""Infrastructure schematic generation from the canonical model (Phase-3 §G7).

The drawing is derived from the loaded catalogue data - there is no separate
drawing definition anywhere.  Elements drawn:

* tracks (rails) - one horizontal line per track edge, placed in the lane of its
  track group, spanning the chainage range of its ``chainage_map``;
* nodes - one marker per topology node, in a compact lane row, at its chainage;
* stations - a box spanning the chainage range of their platforms;
* platforms - a bar over the usable range, on the lane of the platform track;
* stopping marks - a tick at the mark position;
* speed restrictions - a bar in the speed band, labelled with the stored speed;
* cross-section observation points - a tick in the observation band.

Every element carries ``data-object-id`` so that a click surface can map a
hotspot onto the object, and objects with validation errors are marked with the
text ``!`` plus the diagnostic code (never colour alone).

The module is presentation only: it reads plain values, maps them onto pixels and
emits SVG.  It cannot create, delete or modify infrastructure.
"""

from __future__ import annotations

from dataclasses import dataclass, field as dataclass_field
from typing import Any, Iterable, Mapping, Optional

from . import svg_render

#: Layer names of the schematic control (order = control order).
SCHEMATIC_LAYERS: tuple[str, ...] = (
    "Tracks",
    "Stations",
    "Platforms",
    "Signals",
    "TVPs/Resources",
    "Speed",
    "Routes",
    "Simulation Occupancy",
)

#: Layers with a Phase-3 renderer.
ACTIVE_LAYERS: tuple[str, ...] = ("Tracks", "Stations", "Platforms", "Speed")

#: Reason shown for every layer that has data but no Phase-3 renderer yet.
INACTIVE_LAYER_REASONS: dict[str, str] = {
    "Signals": "inactive in Phase 3 - the signalling catalogue exists but has no Phase-3 renderer",
    "TVPs/Resources": "inactive in Phase 3 - platform resource_id values are stored but not resolved",
    "Routes": "inactive in Phase 3 - train_paths holds no Phase-3 renderer",
    "Simulation Occupancy": "inactive in Phase 3 - no simulation engine exists (out of scope)",
}

#: Object kinds the schematic can select, and the editor catalogue of each.
KIND_TO_CATALOGUE: dict[str, str] = {
    "alignment": "alignments",
    "track_group": "track_groups",
    "node": "nodes",
    "track": "tracks",
    "station": "stations",
    "platform": "platforms",
    "stopping_mark": "stopping_marks",
    "speed_restriction": "speed_restrictions",
    "observation_point": "observation_points",
}


@dataclass(frozen=True)
class HitTarget:
    """One clickable element of the schematic."""

    object_id: str
    kind: str
    x: float
    y: float
    width: float = 16.0
    height: float = 16.0
    label: str = ""

    @property
    def catalogue(self) -> str:
        """Return the editor catalogue that owns this object."""
        return KIND_TO_CATALOGUE.get(self.kind, "")


@dataclass
class SchematicDrawing:
    """Result of rendering the schematic."""

    svg: str
    hit_targets: tuple[HitTarget, ...] = ()
    layer_states: Mapping[str, str] = dataclass_field(default_factory=dict)
    error_ids: tuple[str, ...] = ()
    chainage_range: tuple[float, float] = (0.0, 1.0)
    counts: Mapping[str, int] = dataclass_field(default_factory=dict)

    def target_for(self, object_id: str) -> Optional[HitTarget]:
        """Return the hit target of an object (``None`` when it is not drawn)."""
        for target in self.hit_targets:
            if target.object_id == object_id:
                return target
        return None

    def drawn_ids(self, kind: Optional[str] = None) -> tuple[str, ...]:
        """Return the ids drawn on the schematic (optionally filtered by kind)."""
        return tuple(
            target.object_id for target in self.hit_targets if kind is None or target.kind == kind
        )


def _num(value: Any, default: float = 0.0) -> float:
    """Return *value* as a float when possible."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return default
    return float(value)


def _value(item: Any, field: str, default: Any = None) -> Any:
    """Read a field from a dict or a typed object."""
    if isinstance(item, dict):
        return item.get(field, default)
    return getattr(item, field, default)


def _chainage_range(layer: Mapping[str, Any]) -> tuple[float, float]:
    """Return the chainage range drawn by the schematic."""
    lows: list[float] = []
    highs: list[float] = []
    for alignment in layer.get("alignments") or []:
        start = _value(alignment, "start_chainage_km")
        end = _value(alignment, "end_chainage_km")
        if isinstance(start, (int, float)):
            lows.append(float(start))
        if isinstance(end, (int, float)):
            highs.append(float(end))
    for track in layer.get("tracks") or []:
        chainage_map = _value(track, "chainage_map") or {}
        start = _value(chainage_map, "start_km")
        end = _value(chainage_map, "end_km")
        if isinstance(start, (int, float)):
            lows.append(float(start))
        if isinstance(end, (int, float)):
            highs.append(float(end))
    if not lows or not highs:
        return 0.0, 1.0
    low = min(lows)
    high = max(highs)
    if high <= low:
        high = low + 1.0
    return low, high


def _chainage_of_track(track: Any) -> tuple[float, float]:
    """Return the ``(start_km, end_km)`` chainage span of a track edge."""
    chainage_map = _value(track, "chainage_map") or {}
    start = _num(_value(chainage_map, "start_km"))
    end = _num(_value(chainage_map, "end_km"), start)
    return (start, end) if start <= end else (end, start)


def render_schematic(
    layer: Mapping[str, Any],
    *,
    layers: Optional[Mapping[str, bool]] = None,
    error_ids: Iterable[str] = (),
    error_codes: Optional[Mapping[str, str]] = None,
    selected_id: str = "",
    direction: str = "FORWARD",
    width: int = 980,
    row_height: int = 18,
) -> SchematicDrawing:
    """Render the schematic of one infrastructure layer.

    Parameters
    ----------
    layer
        The raw infrastructure layer (typed catalogues, as stored).
    layers
        Layer visibility flags keyed by :data:`SCHEMATIC_LAYERS`; a layer that is
        False is not drawn.  Inactive layers are never drawn even when True.
    error_ids
        Object ids that carry an ERROR diagnostic (marked on the drawing).
    error_codes
        Optional ``object_id -> code`` mapping shown next to the error marker.
    selected_id
        Object highlighted as selected.
    direction
        Application direction; only affects the text of the drawing, never the data.
    """
    flags = dict(layers or {})
    for name in SCHEMATIC_LAYERS:
        flags.setdefault(name, name in ACTIVE_LAYERS)
    errors = set(error_ids)
    codes = dict(error_codes or {})

    low_chainage, high_chainage = _chainage_range(layer)
    left = 96
    right = 24
    plot_width = width - left - right

    def x_of(chainage_km: float) -> float:
        """Map a chainage to a pixel column (drawing only)."""
        if high_chainage <= low_chainage:
            return left
        ratio = (chainage_km - low_chainage) / (high_chainage - low_chainage)
        return left + max(0.0, min(1.0, ratio)) * plot_width

    parts: list[str] = []
    targets: list[HitTarget] = []
    counts: dict[str, int] = {}
    y_cursor = 30

    def label(x_px: float, y_px: float, text: str, *, colour: str = svg_render.PALETTE["ink"], size: int = 9) -> str:
        """Return a small text element."""
        return (
            f'<text x="{x_px:.1f}" y="{y_px:.1f}" font-size="{size}" fill="{colour}" '
            f'font-family="Helvetica,Arial,sans-serif">{svg_render.esc(text)}</text>'
        )

    def lane_label(text: str, y_px: float) -> str:
        """Return the left-hand lane label."""
        return (
            f'<text x="6" y="{y_px:.1f}" font-size="10" fill="{svg_render.PALETTE["muted"]}" '
            f'font-family="Helvetica,Arial,sans-serif">{svg_render.esc(text)}</text>'
        )

    # -- chainage axis ----------------------------------------------------
    parts.append(
        f'<line x1="{left}" y1="{y_cursor}" x2="{left + plot_width}" y2="{y_cursor}" '
        f'stroke="{svg_render.PALETTE["axis"]}" stroke-width="1"/>'
    )
    for step in range(6):
        ratio = step / 5
        x_px = left + ratio * plot_width
        value = low_chainage + ratio * (high_chainage - low_chainage)
        parts.append(
            f'<line x1="{x_px:.1f}" y1="{y_cursor - 4}" x2="{x_px:.1f}" y2="{y_cursor + 4}" '
            f'stroke="{svg_render.PALETTE["axis"]}" stroke-width="1"/>'
        )
        parts.append(label(x_px, y_cursor - 7, f"{value:g} km", colour=svg_render.PALETTE["muted"]))
    y_cursor += 12

    # -- tracks (rails) per track group -----------------------------------
    if flags.get("Tracks", True):
        tracks = list(layer.get("tracks") or [])
        groups = [str(_value(group, "id")) for group in (layer.get("track_groups") or [])]
        lanes: dict[str, int] = {name: index for index, name in enumerate(groups)}
        lanes["(no group)"] = len(lanes)
        extra = 0
        for track in tracks:
            group_id = _value(track, "track_group_id")
            group_name = str(group_id) if group_id else "(no group)"
            if group_name not in lanes:
                lanes[group_name] = len(lanes) + extra
                extra += 1
        lane_base = y_cursor
        drawn_by_lane: dict[int, list[Any]] = {}
        for track in tracks:
            group_id = _value(track, "track_group_id")
            lane_index = lanes[str(group_id) if group_id else "(no group)"]
            drawn_by_lane.setdefault(lane_index, []).append(track)
        for lane_index in sorted(drawn_by_lane):
            y_px = lane_base + lane_index * row_height
            group_name = [name for name, index in lanes.items() if index == lane_index]
            parts.append(lane_label(group_name[0] if group_name else "", y_px + 4))
            for track in drawn_by_lane[lane_index]:
                object_id = str(_value(track, "id"))
                start_km, end_km = _chainage_of_track(track)
                x1 = x_of(start_km)
                x2 = x_of(end_km)
                is_selected = object_id == selected_id
                colour = svg_render.PALETTE["selection"] if is_selected else svg_render.PALETTE["track"]
                parts.append(
                    f'<line data-object-id="{svg_render.esc(object_id)}" class="schematic-track" '
                    f'x1="{x1:.1f}" y1="{y_px:.1f}" x2="{x2:.1f}" y2="{y_px:.1f}" '
                    f'stroke="{colour}" stroke-width="{4 if is_selected else 2.5}" '
                    f'stroke-linecap="round"><title>{svg_render.esc(object_id)}</title></line>'
                )
                targets.append(HitTarget(object_id, "track", x1, y_px, max(x2 - x1, 6.0), 12.0))
                counts["tracks"] = counts.get("tracks", 0) + 1
                if len(drawn_by_lane[lane_index]) <= 12:
                    parts.append(label((x1 + x2) / 2, y_px - 3, object_id, colour=svg_render.PALETTE["muted"]))
                if object_id in errors:
                    parts.append(
                        f'<text x="{(x1 + x2) / 2:.1f}" y="{y_px + 12:.1f}" font-size="10" '
                        f'font-weight="700" fill="{svg_render.PALETTE["error"]}" '
                        f'font-family="Helvetica,Arial,sans-serif">! ERROR {svg_render.esc(codes.get(object_id, ""))}</text>'
                    )
        y_cursor = lane_base + (max(drawn_by_lane) + 1) * row_height + 8 if drawn_by_lane else y_cursor

    # -- stations and platforms -------------------------------------------
    station_rows: list[tuple[str, str, float, float]] = []
    if flags.get("Stations", True):
        platforms_by_station: dict[str, list[Any]] = {}
        for platform in layer.get("platforms") or []:
            platforms_by_station.setdefault(str(_value(platform, "station_id")), []).append(platform)
        tracks_by_id = {str(_value(track, "id")): track for track in (layer.get("tracks") or [])}
        for station in layer.get("stations") or []:
            object_id = str(_value(station, "id"))
            spans: list[tuple[float, float]] = []
            for platform in platforms_by_station.get(object_id, []):
                track = tracks_by_id.get(str(_value(platform, "track_id")))
                if track is None:
                    continue
                start_km, end_km = _chainage_of_track(track)
                spans.append((start_km, end_km))
            if spans:
                start_km = min(span[0] for span in spans)
                end_km = max(span[1] for span in spans)
            else:
                reference = _num(_value(station, "reference_chainage_km"))
                start_km = end_km = reference
            station_rows.append((object_id, str(_value(station, "name") or object_id), start_km, end_km))
        for object_id, station_name, start_km, end_km in station_rows:
            y_px = y_cursor + 6
            x1 = x_of(start_km)
            x2 = max(x_of(end_km), x1 + 12)
            is_selected = object_id == selected_id
            colour = svg_render.PALETTE["selection"] if is_selected else svg_render.PALETTE["station"]
            parts.append(lane_label(object_id, y_px + 4))
            parts.append(
                f'<rect data-object-id="{svg_render.esc(object_id)}" class="schematic-station" '
                f'x="{x1:.1f}" y="{y_px - 7:.1f}" width="{x2 - x1:.1f}" height="16" rx="3" '
                f'fill="{colour}" fill-opacity="0.18" stroke="{colour}" stroke-width="{2 if is_selected else 1}">'
                f"<title>{svg_render.esc(object_id)}</title></rect>"
            )
            parts.append(
                label(x1 + 3, y_px - 9, f"station {station_name}",
                      colour=svg_render.PALETTE["muted"])
            )
            targets.append(HitTarget(object_id, "station", x1, y_px - 7, max(x2 - x1, 12.0), 16.0))
            counts["stations"] = counts.get("stations", 0) + 1
            if object_id in errors:
                parts.append(
                    f'<text x="{x2 + 3:.1f}" y="{y_px + 4:.1f}" font-size="10" font-weight="700" '
                    f'fill="{svg_render.PALETTE["error"]}" font-family="Helvetica,Arial,sans-serif">'
                    f"! ERROR {svg_render.esc(codes.get(object_id, ''))}</text>"
                )
            y_cursor += 22

    platform_rows: list[tuple[str, float, float]] = []
    if flags.get("Platforms", True):
        y_cursor += 4
        parts.append(lane_label("Platforms", y_cursor + 4))
        for index, platform in enumerate(layer.get("platforms") or []):
            object_id = str(_value(platform, "id"))
            track_id = str(_value(platform, "track_id"))
            track = next(
                (item for item in (layer.get("tracks") or []) if str(_value(item, "id")) == track_id),
                None,
            )
            y_px = y_cursor + 8 + index * row_height
            if track is None:
                parts.append(
                    label(x_of(low_chainage) + 4, y_px + 4, f"{object_id} (track {track_id} unresolved)",
                          colour=svg_render.PALETTE["error"])
                )
                continue
            start_km, end_km = _chainage_of_track(track)
            total_m = max(_num(_value(track, "length_m")), 1e-9)
            usable_start = _num(_value(platform, "usable_start_m"))
            usable_end = _num(_value(platform, "usable_end_m"), total_m)
            fraction_start = max(0.0, min(1.0, usable_start / total_m))
            fraction_end = max(0.0, min(1.0, usable_end / total_m))
            span_km = end_km - start_km
            x1 = x_of(start_km + span_km * fraction_start)
            x2 = x_of(start_km + span_km * fraction_end)
            is_selected = object_id == selected_id
            colour = svg_render.PALETTE["selection"] if is_selected else svg_render.PALETTE["platform"]
            parts.append(
                f'<rect data-object-id="{svg_render.esc(object_id)}" class="schematic-platform" '
                f'x="{x1:.1f}" y="{y_px - 5:.1f}" width="{max(x2 - x1, 4.0):.1f}" height="10" rx="2" '
                f'fill="{colour}" fill-opacity="0.45" stroke="{colour}" '
                f'stroke-width="{2 if is_selected else 1}"><title>{svg_render.esc(object_id)}</title></rect>'
            )
            parts.append(label(x1, y_px - 7, object_id, colour=svg_render.PALETTE["muted"]))
            targets.append(HitTarget(object_id, "platform", x1, y_px - 5, max(x2 - x1, 10.0), 10.0))
            platform_rows.append((object_id, start_km, end_km))
            counts["platforms"] = counts.get("platforms", 0) + 1
            if object_id in errors:
                parts.append(
                    f'<text x="{x2 + 3:.1f}" y="{y_px + 4:.1f}" font-size="10" font-weight="700" '
                    f'fill="{svg_render.PALETTE["error"]}" font-family="Helvetica,Arial,sans-serif">'
                    f"! {svg_render.esc(codes.get(object_id, ''))}</text>"
                )
        if platform_rows:
            y_cursor = y_cursor + 8 + len(platform_rows) * row_height

    # -- stopping marks ----------------------------------------------------
    marks = list(layer.get("stopping_marks") or [])
    if marks:
        y_cursor += 6
        parts.append(lane_label("Stopping marks", y_cursor + 4))
        tracks_by_id = {str(_value(track, "id")): track for track in (layer.get("tracks") or [])}
        for mark in marks:
            object_id = str(_value(mark, "id"))
            track = tracks_by_id.get(str(_value(mark, "track_id")))
            if track is None:
                continue
            start_km, end_km = _chainage_of_track(track)
            total_m = max(_num(_value(track, "length_m")), 1e-9)
            fraction = max(0.0, min(1.0, _num(_value(mark, "position_m")) / total_m))
            x_px = x_of(start_km + (end_km - start_km) * fraction)
            is_selected = object_id == selected_id
            colour = svg_render.PALETTE["selection"] if is_selected else svg_render.PALETTE["node"]
            parts.append(
                f'<line data-object-id="{svg_render.esc(object_id)}" class="schematic-mark" '
                f'x1="{x_px:.1f}" y1="{y_cursor:.1f}" x2="{x_px:.1f}" y2="{y_cursor + 12:.1f}" '
                f'stroke="{colour}" stroke-width="{3 if is_selected else 2}">'
                f"<title>{svg_render.esc(object_id)}</title></line>"
            )
            targets.append(HitTarget(object_id, "stopping_mark", x_px - 6, y_cursor, 12.0, 12.0))
            counts["stopping_marks"] = counts.get("stopping_marks", 0) + 1
            if object_id in errors:
                parts.append(
                    f'<text x="{x_px + 2:.1f}" y="{y_cursor + 10:.1f}" font-size="10" font-weight="700" '
                    f'fill="{svg_render.PALETTE["error"]}" font-family="Helvetica,Arial,sans-serif">'
                    f"! {svg_render.esc(codes.get(object_id, ''))}</text>"
                )
        y_cursor += 22

    # -- nodes -------------------------------------------------------------
    if flags.get("Tracks", True):
        nodes = list(layer.get("nodes") or [])
        if nodes:
            parts.append(lane_label(f"Nodes ({len(nodes)})", y_cursor + 4))
            per_lane = 26
            for index, node in enumerate(nodes):
                object_id = str(_value(node, "id"))
                chainage_km = _num(_value(node, "chainage_km"))
                x_px = x_of(chainage_km)
                lane = index // per_lane
                y_px = y_cursor + 4 + lane * 12
                is_selected = object_id == selected_id
                colour = svg_render.PALETTE["selection"] if is_selected else svg_render.PALETTE["node"]
                parts.append(
                    f'<circle data-object-id="{svg_render.esc(object_id)}" class="schematic-node" '
                    f'cx="{x_px:.1f}" cy="{y_px:.1f}" r="{4 if is_selected else 2.8}" fill="{colour}">'
                    f"<title>{svg_render.esc(object_id)} {svg_render.esc(_value(node, 'type') or '')}</title></circle>"
                )
                targets.append(HitTarget(object_id, "node", x_px - 5, y_px - 5, 10.0, 10.0))
                counts["nodes"] = counts.get("nodes", 0) + 1
                if object_id in errors:
                    code = codes.get(object_id, "")
                    parts.append(
                        f'<text x="{x_px + 2:.1f}" y="{y_px - 4:.1f}" font-size="10" font-weight="700" '
                        f'fill="{svg_render.PALETTE["error"]}" font-family="Helvetica,Arial,sans-serif">'
                        f"! {svg_render.esc(code)}</text>"
                    )
            y_cursor += 12 * (1 + (len(nodes) - 1) // per_lane) + 10

    # -- speed restrictions ------------------------------------------------
    if flags.get("Speed", True):
        restrictions = list(layer.get("speed_restrictions") or [])
        if restrictions:
            parts.append(lane_label("Speed", y_cursor + 4))
            for restriction in restrictions:
                object_id = str(_value(restriction, "id"))
                x1 = x_of(_num(_value(restriction, "start_chainage_km")))
                x2 = x_of(_num(_value(restriction, "end_chainage_km"), _num(_value(restriction, "start_chainage_km"))))
                is_selected = object_id == selected_id
                colour = svg_render.PALETTE["selection"] if is_selected else svg_render.PALETTE["speed"]
                parts.append(
                    f'<rect data-object-id="{svg_render.esc(object_id)}" class="schematic-speed" '
                    f'x="{x1:.1f}" y="{y_cursor - 2:.1f}" width="{max(x2 - x1, 3.0):.1f}" height="10" '
                    f'fill="{colour}" fill-opacity="0.5" stroke="{colour}">'
                    f"<title>{svg_render.esc(object_id)}</title></rect>"
                )
                parts.append(
                    label(x1 + 2, y_cursor - 4,
                          f"{_value(restriction, 'speed_kmh')} km/h {_value(restriction, 'direction')}",
                          colour=svg_render.PALETTE["ink"])
                )
                targets.append(HitTarget(object_id, "speed_restriction", x1, y_cursor - 2, max(x2 - x1, 10.0), 10.0))
                counts["speed_restrictions"] = counts.get("speed_restrictions", 0) + 1
                if object_id in errors:
                    parts.append(
                        f'<text x="{x2 + 2:.1f}" y="{y_cursor + 6:.1f}" font-size="10" font-weight="700" '
                        f'fill="{svg_render.PALETTE["error"]}" font-family="Helvetica,Arial,sans-serif">'
                        f"! {svg_render.esc(codes.get(object_id, ''))}</text>"
                    )
            y_cursor += 20

    # -- observation points (cross sections) -------------------------------
    observations = [item for item in (layer.get("observation_points") or [])]
    if observations:
        parts.append(lane_label("Observations", y_cursor + 4))
        tracks_by_id = {str(_value(track, "id")): track for track in (layer.get("tracks") or [])}
        nodes_by_id = {str(_value(node, "id")): node for node in (layer.get("nodes") or [])}
        for observation in observations:
            object_id = str(_value(observation, "id"))
            chainages: list[float] = []
            for node_id in _value(observation, "node_ids") or []:
                node = nodes_by_id.get(str(node_id))
                if node is not None:
                    chainages.append(_num(_value(node, "chainage_km")))
            for member in _value(observation, "members") or []:
                track = tracks_by_id.get(str(_value(member, "track_id")))
                if track is None:
                    continue
                start_km, end_km = _chainage_of_track(track)
                total_m = max(_num(_value(track, "length_m")), 1e-9)
                fraction = max(0.0, min(1.0, _num(_value(member, "position_m")) / total_m))
                chainages.append(start_km + (end_km - start_km) * fraction)
            if not chainages:
                # Nothing to place it on: draw it at the origin of the drawing with an
                # explicit note instead of silently dropping it from the schematic.
                parts.append(
                    label(
                        x_px + 2,
                        y_cursor + 22,
                        f"{object_id}: no resolvable chainage (node_ids/members empty or unmapped)",
                        colour=svg_render.PALETTE["error"],
                    )
                )
            x_px = x_of(sum(chainages) / len(chainages)) if chainages else left
            is_selected = object_id == selected_id
            colour = svg_render.PALETTE["selection"] if is_selected else svg_render.PALETTE["station"]
            parts.append(
                f'<polygon data-object-id="{svg_render.esc(object_id)}" class="schematic-observation" '
                f'points="{x_px:.1f},{y_cursor + 12:.1f} {x_px - 5:.1f},{y_cursor + 2:.1f} '
                f'{x_px + 5:.1f},{y_cursor + 2:.1f}" fill="{colour}">'
                f"<title>{svg_render.esc(object_id)}</title></polygon>"
            )
            targets.append(HitTarget(object_id, "observation_point", x_px - 6, y_cursor, 12.0, 12.0))
            counts["observation_points"] = counts.get("observation_points", 0) + 1
        y_cursor += 20

    # -- inactive layer notice --------------------------------------------
    inactive = [name for name in SCHEMATIC_LAYERS if name not in ACTIVE_LAYERS]
    parts.append(
        label(left, y_cursor + 12,
              "Disabled layers (no Phase-3 renderer): "
              + ", ".join(f"{name} ({INACTIVE_LAYER_REASONS[name]})" for name in inactive),
              colour=svg_render.PALETTE["error"])
    )
    y_cursor += 24
    parts.append(
        label(6, y_cursor, f"direction {direction} - drawn from the canonical model", colour=svg_render.PALETTE["muted"])
    )
    height = y_cursor + 12
    svg = (
        svg_render.svg_open(width, height, title="Infrastructure schematic")
        + f'<rect x="0" y="0" width="{width}" height="{height}" fill="#FFFFFF"/>'
        + "\n".join(parts)
        + "</svg>"
    )
    return SchematicDrawing(
        svg=svg,
        hit_targets=tuple(targets),
        layer_states={
            name: ("ACTIVE" if name in ACTIVE_LAYERS else "INACTIVE")
            for name in SCHEMATIC_LAYERS
        },
        error_ids=tuple(sorted(errors)),
        chainage_range=(low_chainage, high_chainage),
        counts=counts,
    )
