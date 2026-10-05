"""Generate the JSON Schema of the canonical project document (schema 1.0).

Run from the repository root::

    python3 build_json_schema.py

Output: ``schema/project_schema_v1.0.json``.

The document schema is derived from the canonical pydantic models (one authority
for field names, types and defaults) and extended with the typed Phase-2
infrastructure layer definition, because ``Project.infrastructure`` stays an
array of free-form layer objects at the container level (Phase-1 contract): the
typed catalogues are described by :data:`CATALOGUE_SPEC` inside the layer object.

Deterministic: the file contains no timestamps and re-running the script
reproduces the same bytes.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from railway_headway_sim.constants import TOP_LEVEL_SECTIONS
from railway_headway_sim.models.infrastructure import (
    CATALOGUE_SPEC,
    LEGACY_CATALOGUE_KEYS,
    PHASE2_CATALOGUE_KEYS,
)
from railway_headway_sim.models.project import Project
from railway_headway_sim.version import (
    APP_VERSION,
    DEFAULT_PROJECT_SCHEMA_VERSION,
    SUPPORTED_PROJECT_SCHEMA_VERSIONS,
)

ROOT = Path(__file__).resolve().parent
SCHEMA_DIR = ROOT / "schema"
SCHEMA_FILENAME = f"project_schema_v{DEFAULT_PROJECT_SCHEMA_VERSION}.json"

ADDRESS = "https://example.org/railway-headway-sim/schema/project_schema_v1.0.json"


def _typed_layer_schema() -> dict[str, Any]:
    """Return the JSON Schema fragment of one typed infrastructure layer."""
    properties: dict[str, Any] = {
        "id": {"type": "string", "description": "Layer identifier (unique per project)."},
        "name": {"type": ["string", "null"]},
        "physical_mode": {
            "type": "string",
            "enum": ["PHYSICAL", "LEGACY"],
            "description": "Declares whether the layer is validated as typed physical infrastructure.",
        },
    }
    for key in LEGACY_CATALOGUE_KEYS:
        properties[key] = {
            "type": "array",
            "description": (
                f"Phase-1 opaque catalogue '{key}': preserved verbatim and never interpreted. "
                "Records carrying an 'id' are an error inside a physical project (VAL-PHASE-002)."
            ),
            "items": {"type": "object"},
            "default": [],
        }
    for key in PHASE2_CATALOGUE_KEYS:
        label, model, object_type = CATALOGUE_SPEC[key]
        properties[key] = {
            "type": "array",
            "description": f"Typed Phase-2 catalogue '{key}' ({label}); registry object type '{object_type}'.",
            "items": {"$ref": f"#/$defs/{model.__name__}"},
            "default": [],
        }
    return {
        "type": "object",
        "description": (
            "One infrastructure layer. In a physical project the typed catalogues are validated "
            "semantically and every registered engineering object id must be globally unique."
        ),
        "required": ["id"],
        "properties": properties,
        "unevaluatedProperties": True,
    }


def build_schema() -> dict[str, Any]:
    """Return the complete JSON Schema document."""
    project_schema = Project.model_json_schema(ref_template="#/$defs/{model}", mode="validation")
    defs: dict[str, Any] = dict(project_schema.get("$defs", {}))
    for _key, (_label, model, _object_type) in CATALOGUE_SPEC.items():
        model_schema = model.model_json_schema(ref_template="#/$defs/{model}", mode="validation")
        for name, definition in (model_schema.get("$defs") or {}).items():
            defs.setdefault(name, definition)
        defs[model.__name__] = {
            key: value for key, value in model_schema.items() if key != "$defs"
        }
    defs["TypedInfrastructureLayer"] = _typed_layer_schema()

    properties: dict[str, Any] = dict(project_schema.get("properties", {}))
    properties["infrastructure"] = {
        "type": "array",
        "description": (
            "Array of infrastructure layer objects (Phase-1 container contract). Layers may carry "
            "the typed Phase-2 catalogues described by TypedInfrastructureLayer."
        ),
        "items": {"$ref": "#/$defs/TypedInfrastructureLayer"},
        "default": [],
    }
    ordered_properties = {
        section: properties[section] for section in TOP_LEVEL_SECTIONS if section in properties
    }
    for name, definition in properties.items():
        ordered_properties.setdefault(name, definition)

    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": ADDRESS,
        "$comment": (
            f"Railway Track Headway Simulator project document schema {DEFAULT_PROJECT_SCHEMA_VERSION} "
            f"(application version {APP_VERSION}). Phase 2 keeps schema 1.0: the typed physical "
            "catalogues are additive nested keys inside an infrastructure layer object, so every "
            "Phase-1 document remains valid and round-trips unchanged."
        ),
        "title": "Railway headway simulator project document",
        "type": "object",
        "required": list(project_schema.get("required") or []),
        "properties": ordered_properties,
        "unevaluatedProperties": True,
        "additionalProperties": True,
        "x-schema-version": DEFAULT_PROJECT_SCHEMA_VERSION,
        "x-supported-schema-versions": list(SUPPORTED_PROJECT_SCHEMA_VERSIONS),
        "x-application-version": APP_VERSION,
        "x-phase2-typed-catalogues": list(PHASE2_CATALOGUE_KEYS),
        "x-phase1-opaque-catalogues": list(LEGACY_CATALOGUE_KEYS),
        "$defs": defs,
    }


def main() -> int:
    schema = build_schema()
    SCHEMA_DIR.mkdir(exist_ok=True)
    target = SCHEMA_DIR / SCHEMA_FILENAME
    text = json.dumps(schema, indent=2, ensure_ascii=False) + "\n"
    previous = target.read_text(encoding="utf-8") if target.exists() else None
    target.write_text(text, encoding="utf-8")
    state = "unchanged" if previous == text else "written"
    print(f"{state}: {target} ({len(text):,} bytes)")
    print(f"  typed catalogues: {len(PHASE2_CATALOGUE_KEYS)}, opaque catalogues: {len(LEGACY_CATALOGUE_KEYS)}")
    print(f"  definitions: {len(schema['$defs'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
