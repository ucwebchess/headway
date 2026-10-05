"""Base model configuration and shared typing helpers.

Extracted from :mod:`railway_headway_sim.models.common` in Phase 2 so that the
typed infrastructure models can build on it without importing the project
container (avoids circular imports).

The strict/frozen/extra-preservation configuration is preserved exactly as
accepted in Phase 1:

* ``extra="allow"``  - unknown/future JSON fields survive import -> export;
* ``validate_assignment=True`` - assignment goes through validation;
* JSON-native numbers only (``Number``), no silent string/boolean coercion.
"""

from __future__ import annotations

import datetime as _dt
import re
import uuid
from typing import Union

from pydantic import BaseModel, ConfigDict, StrictFloat, StrictInt

#: JSON-native number: an ``int`` (e.g. ``632``) or a ``float`` (e.g. ``632.4``).
#: Strings such as ``"632.4"`` and booleans are explicitly *rejected* so that no
#: silent type coercion can corrupt engineering values. Values keep their JSON
#: int/float nature, which makes export -> import -> export byte-stable.
Number = Union[StrictInt, StrictFloat]

#: ISO-8601 UTC timestamp pattern used for ``created_utc``/``modified_utc``.
ISO8601_UTC_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,6})?Z$")


class ContainerBase(BaseModel):
    """Base class for typed sections and typed engineering objects.

    ``extra="allow"`` is deliberate: a schema-1.0 document may carry additional
    fields (including forward-compatible ones authored by hand or by a later
    minor schema revision). They are *preserved* through import/export instead
    of being silently dropped.
    """

    model_config = ConfigDict(extra="allow", validate_assignment=True)


def utc_now_iso() -> str:
    """Return the current UTC time as an ISO-8601 string with a ``Z`` suffix."""
    return (
        _dt.datetime.now(_dt.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def is_valid_iso8601_utc(value: object) -> bool:
    """Return ``True`` when *value* looks like an ISO-8601 UTC timestamp."""
    return isinstance(value, str) and bool(ISO8601_UTC_PATTERN.match(value))


def new_stable_id(prefix: str) -> str:
    """Return a new machine identifier such as ``STN-4f9c1a7b2d3e``.

    Identifiers are random-but-opaque: they are stable once created and are
    never derived from user-editable display names.
    """
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def safe_str(value: object) -> str:
    """Return *value* as a stripped string, or ``""`` for missing values."""
    if value is None:
        return ""
    return str(value).strip()
