"""Shared typing helpers - compatibility re-export of :mod:`models.base`.

Phase 1 defined these helpers here; Phase 2 moved the implementation into
:mod:`railway_headway_sim.models.base` to avoid circular imports between the
project container and the typed infrastructure models. Every Phase-1 import
path (``from ..models.common import Number``) keeps working unchanged.
"""

from __future__ import annotations

from .base import (
    ISO8601_UTC_PATTERN,
    ContainerBase,
    Number,
    is_valid_iso8601_utc,
    new_stable_id,
    safe_str,
    utc_now_iso,
)

__all__ = [
    "ISO8601_UTC_PATTERN",
    "ContainerBase",
    "Number",
    "is_valid_iso8601_utc",
    "new_stable_id",
    "safe_str",
    "utc_now_iso",
]
