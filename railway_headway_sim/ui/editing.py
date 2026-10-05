"""Editing engine of the Phase-3 editors (no widgets, no engineering calculation).

Every editor in the UI calls this module; this module is the only place that builds
an edited project document, and it always hands the document to the **existing**
Phase-2 draft mechanism (``ProjectController.stage_draft`` / ``commit_draft`` /
``discard_draft``).  There is no second edit path, and no widget value ever reaches
the project model directly.

Guarantees

* ``document()`` returns the *working* document: the staged draft when one is
  staged, otherwise the committed canonical document.  A second edit therefore
  continues from the first one instead of discarding it.
* ``stage_*`` never mutates the committed project, its hash or its validation
  result; it only stages (and reports) a candidate document.
* Deleting an object that is still referenced is **refused** with the diagnostic
  the deletion would produce, naming the referencing objects - the draft is not
  staged and no reference is silently orphaned.
* Unknown/extension fields are preserved: edits are applied to a deep copy of the
  canonical document, so every untouched key survives.
"""

from __future__ import annotations

from dataclasses import dataclass, field as dataclass_field
from enum import Enum
from typing import Any, Optional

from ..app.project_controller import ProjectController
from ..io.project_io import to_normalized_dict
from ..models.diagnostics import Diagnostic
from ..models.enums import Severity
from ..validation import ValidationOutcome, ValidationResult, validate_document
from .editor_specs import EDITOR_FIELDS, nested_field_split

#: Sections of the canonical document that belong to one infrastructure layer.
LAYER_SECTION = "infrastructure"


class Provenance(str, Enum):
    """Provenance label of an editor value.

    Only ``INPUT`` and ``DERIVED`` are emitted in Phase 3: the Phase-2 model tracks
    no default/inheritance metadata for typed catalogue fields, and the Phase-3
    scope forbids inventing a new provenance mechanism.  ``DEFAULT`` and
    ``INHERITED`` exist so that a later phase can adopt them without a rename, and
    are never produced by this module.
    """

    INPUT = "INPUT"
    DEFAULT = "DEFAULT"
    DERIVED = "DERIVED"
    INHERITED = "INHERITED"


@dataclass(frozen=True)
class Reference:
    """One object that references a target object."""

    source_catalogue: str
    source_id: str
    field: str
    kind: str

    def describe(self) -> str:
        """Return a one-line description naming the referencing object."""
        return f"{self.source_catalogue[:-1] if self.source_catalogue.endswith('s') else self.source_catalogue} '{self.source_id}' ({self.field})"


@dataclass(frozen=True)
class CatalogueEdit:
    """Outcome of one editor operation."""

    ok: bool
    staged: bool
    message: str
    diagnostics: tuple[Diagnostic, ...] = ()
    code: str = ""
    object_id: str = ""

    @property
    def blocked_reason(self) -> str:
        """Return a short machine-readable reason (``''`` when the edit is fine)."""
        if self.ok and self.staged:
            return ""
        if self.code:
            return self.code
        return "EDIT-REFUSED" if not self.ok else "NOT-STAGED"

    def codes(self) -> tuple[str, ...]:
        """Return the diagnostic codes carried by this outcome."""
        return tuple(diagnostic.code for diagnostic in self.diagnostics)


#: Reference map: target catalogue -> (source catalogue, field path, kind).
REFERENCE_MAP: dict[str, tuple[tuple[str, str, str], ...]] = {
    "alignments": (
        ("horizontal_geometry", "alignment_id", "scalar"),
        ("vertical_profiles", "alignment_id", "scalar"),
        ("speed_restrictions", "alignment_id", "scalar"),
        ("<reference_system>", "alignment_id", "scalar"),
    ),
    "track_groups": (("tracks", "track_group_id", "scalar"),),
    "nodes": (
        ("tracks", "from_node", "scalar"),
        ("tracks", "to_node", "scalar"),
        ("observation_points", "node_ids", "list"),
    ),
    "tracks": (
        ("platforms", "track_id", "scalar"),
        ("stopping_marks", "track_id", "scalar"),
        ("observation_points", "track_id", "scalar"),
        ("observation_points", "members", "member"),
    ),
    "stations": (
        ("nodes", "station_id", "scalar"),
        ("platforms", "station_id", "scalar"),
        ("observation_points", "station_id", "scalar"),
    ),
    "platforms": (
        ("stopping_marks", "platform_id", "scalar"),
        ("stations", "platform_ids", "list"),
        ("observation_points", "platform_id", "scalar"),
    ),
    "stopping_marks": (("platforms", "stopping_mark_ids", "list"),),
    "horizontal_geometry": (),
    "vertical_profiles": (),
    "vertical_profile_points": (),
    "speed_restrictions": (),
    "observation_points": (),
}

#: Fields that are DERIVED in the editors (computed by the package layer, never stored).
DERIVED_FIELDS: dict[str, tuple[str, ...]] = {
    "stopping_marks": ("chainage_km",),
    "platforms": ("usable_range_text",),
    "tracks": ("chainage_projection_km",),
}


class InfrastructureEditor:
    """Build edited documents and stage them through the Phase-2 draft mechanism."""

    def __init__(self, controller: ProjectController, *, layer_index: int = 0) -> None:
        self._controller = controller
        self._layer_index = layer_index
        self._last_report = ""

    # -- document access ---------------------------------------------------
    @property
    def layer_index(self) -> int:
        """Return the edited infrastructure layer index."""
        return self._layer_index

    def committed_document(self) -> dict[str, Any]:
        """Return a deep copy of the committed project as a canonical document."""
        project = self._controller.project
        if project is None:
            return {}
        return to_normalized_dict(project)

    def document(self) -> dict[str, Any]:
        """Return the working document (staged draft when one is staged)."""
        staged = getattr(self._controller, "_draft_document", None)
        if isinstance(staged, dict):
            return staged
        return self.committed_document()

    def layer(self, document: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        """Return the edited infrastructure layer of a document."""
        doc = document if document is not None else self.document()
        layers = doc.get(LAYER_SECTION) or []
        if not layers:
            return {}
        index = min(self._layer_index, len(layers) - 1)
        layer = layers[index]
        return layer if isinstance(layer, dict) else {}

    def entries(self, catalogue: str, document: Optional[dict[str, Any]] = None) -> list[dict[str, Any]]:
        """Return the raw entries of one typed catalogue."""
        raw = self.layer(document).get(catalogue) or []
        return [entry for entry in raw if isinstance(entry, dict)]

    def container(
        self, catalogue: str, document: Optional[dict[str, Any]] = None
    ) -> list[Any]:
        """Return the **live** list that stores a catalogue inside a document.

        ``entries()`` returns a filtered view for reading; adding or deleting an
        object must act on the list the document actually holds, so those two
        operations use this accessor instead.  No value is invented and nothing is
        repaired: the list is only extended or shortened when the user asks for it.
        """
        layer = self.layer(document)
        raw = layer.get(catalogue)
        if not isinstance(raw, list):
            raw = []
            layer[catalogue] = raw
        return raw

    def entry(
        self, catalogue: str, object_id: str, document: Optional[dict[str, Any]] = None
    ) -> Optional[dict[str, Any]]:
        """Return one raw catalogue entry by id."""
        for record in self.entries(catalogue, document):
            if record.get("id") == object_id:
                return record
        return None

    def ids(self, catalogue: str, document: Optional[dict[str, Any]] = None) -> tuple[str, ...]:
        """Return the ids of a catalogue, in document order."""
        return tuple(str(record.get("id")) for record in self.entries(catalogue, document))

    # -- staging -----------------------------------------------------------
    def stage(self, document: dict[str, Any], *, description: str) -> ValidationResult:
        """Stage *document* through the existing draft mechanism and return its result.

        The draft mechanism is the Phase-2 one (``ProjectController.stage_draft``
        plus the ``APP-EDIT-002`` commit gate); nothing here replaces or bypasses it.
        """
        self._controller.stage_draft(document, description=description)
        result = self._controller.draft_result
        if result is None:  # pragma: no cover - defensive: stage_draft always sets it
            raise RuntimeError("stage_draft did not produce a validation result")
        return result

    def stage_field(
        self,
        catalogue: str,
        object_id: str,
        field_name: str,
        value: Any,
        *,
        description: str = "",
    ) -> CatalogueEdit:
        """Write one field of one entry into a staged draft."""
        record = self.entry(catalogue, object_id)
        if record is None:
            return CatalogueEdit(
                ok=False,
                staged=False,
                message=f"{catalogue} '{object_id}' is not in the current document.",
                object_id=object_id,
            )
        document = self.document()
        target = self.entry(catalogue, object_id, document)
        if target is None:  # pragma: no cover - defensive
            return CatalogueEdit(ok=False, staged=False, message="Entry disappeared.", object_id=object_id)
        parent, leaf = nested_field_split(field_name)
        container = target
        if parent and parent != field_name:
            nested = container.get(parent)
            if not isinstance(nested, dict):
                nested = {}
                container[parent] = nested
            container = nested
            key = leaf
        else:
            key = field_name
        container[key] = value
        label = f"{catalogue}.{field_name}"
        result = self.stage(
            document,
            description=description or f"edit {label} of {object_id}",
        )
        return self._result_to_edit(result, object_id=object_id)

    def stage_entry(
        self,
        catalogue: str,
        values: dict[str, Any],
        *,
        object_id: Optional[str] = None,
        description: str = "",
    ) -> CatalogueEdit:
        """Add a new entry, or update the entry named by *object_id*."""
        if catalogue not in EDITOR_FIELDS:
            raise KeyError(f"{catalogue!r} is not an editable catalogue")
        document = self.document()
        container = self.container(catalogue, document)
        target_id = object_id or str(values.get("id") or "")
        if not target_id:
            return CatalogueEdit(
                ok=False,
                staged=False,
                message="An object ID is required.",
            )
        existing = self.entry(catalogue, target_id, document)
        nested: dict[str, Any] = {}
        flat: dict[str, Any] = {}
        for name, value in values.items():
            parent, leaf = nested_field_split(name)
            if parent and parent != name:
                nested.setdefault(parent, {})[leaf] = value
            else:
                flat[name] = value
        if existing is None:
            record: dict[str, Any] = {"id": target_id}
            record.update(flat)
            record.update(nested)
            container.append(record)
            action = "add"
        else:
            if "id" in flat and flat["id"] != existing.get("id"):
                return CatalogueEdit(
                    ok=False,
                    staged=False,
                    message=(
                        "Renaming an ID is not supported by the editors; delete the object and "
                        "add it with the new ID."
                    ),
                    object_id=target_id,
                )
            existing.update(flat)
            existing.update(nested)
            action = "edit"
        result = self.stage(document, description=description or f"{action} {catalogue} {target_id}")
        return self._result_to_edit(result, object_id=target_id)

    def delete_entry(
        self, catalogue: str, object_id: str, *, description: str = ""
    ) -> CatalogueEdit:
        """Delete an entry - refused (and never staged) while other objects reference it."""
        references = self.references_to(catalogue, object_id)
        if references:
            document = self.document()
            entry = self.entry(catalogue, object_id, document)
            if entry is None:
                return CatalogueEdit(
                    ok=False,
                    staged=False,
                    message=f"{catalogue} '{object_id}' is not in the current document.",
                    object_id=object_id,
                )
            self.container(catalogue, document).remove(entry)
            preview = self._validate_document(document)
            # The object is *not* deleted: the draft is left exactly as it was.
            names = ", ".join(reference.describe() for reference in references)
            diagnostics = tuple(preview.result.diagnostics) if preview is not None else ()
            return CatalogueEdit(
                ok=False,
                staged=False,
                message=(
                    f"Delete of {catalogue} '{object_id}' refused: {len(references)} object(s) still "
                    f"reference it ({names}). Remove or re-point those references first."
                ),
                diagnostics=diagnostics,
                code=diagnostics[0].code if diagnostics else "",
                object_id=object_id,
            )
        document = self.document()
        entry = self.entry(catalogue, object_id, document)
        if entry is None:
            return CatalogueEdit(
                ok=False,
                staged=False,
                message=f"{catalogue} '{object_id}' is not in the current document.",
                object_id=object_id,
            )
        self.container(catalogue, document).remove(entry)
        result = self.stage(document, description=description or f"delete {catalogue} {object_id}")
        return self._result_to_edit(result, object_id=object_id)

    def _result_to_edit(self, result: ValidationResult, *, object_id: str) -> CatalogueEdit:
        """Translate a validation result into a :class:`CatalogueEdit`."""
        first_error = next(
            (diagnostic for diagnostic in result.diagnostics if diagnostic.severity is Severity.ERROR),
            None,
        )
        if first_error is not None:
            return CatalogueEdit(
                ok=False,
                staged=True,
                message=(
                    f"Staged with errors: {first_error.code} - {first_error.message} "
                    "(the draft blocks commit and export until it is corrected or discarded)."
                ),
                diagnostics=tuple(result.diagnostics),
                code=first_error.code,
                object_id=object_id,
            )
        return CatalogueEdit(
            ok=True,
            staged=True,
            message=f"Staged: {result.summary_with_scope()}",
            diagnostics=tuple(result.diagnostics),
            object_id=object_id,
        )

    def _validate_document(self, document: dict[str, Any]) -> Optional[ValidationOutcome]:
        """Validate a candidate document without staging it."""
        try:
            return validate_document(document, source_name="<editor preview>")
        except Exception:  # pragma: no cover - validation never raises on dict input
            return None

    # -- references --------------------------------------------------------
    def references_to(self, catalogue: str, object_id: str) -> tuple[Reference, ...]:
        """Return every object that references ``(catalogue, object_id)``."""
        document = self.document()
        references: list[Reference] = []
        for source_catalogue, field_path, kind in REFERENCE_MAP.get(catalogue, ()):
            if source_catalogue == "<reference_system>":
                value = (document.get("reference_system") or {}).get(field_path)
                if value == object_id:
                    references.append(
                        Reference("<reference_system>", "reference_system", field_path, "scalar")
                    )
                continue
            for record in self.entries(source_catalogue, document):
                source_id = str(record.get("id") or "")
                if kind == "scalar":
                    if record.get(field_path) == object_id:
                        references.append(Reference(source_catalogue, source_id, field_path, kind))
                elif kind == "list":
                    if object_id in (record.get(field_path) or []):
                        references.append(Reference(source_catalogue, source_id, field_path, kind))
                elif kind == "member":
                    for member in record.get(field_path) or []:
                        if isinstance(member, dict) and member.get("track_id") == object_id:
                            references.append(
                                Reference(source_catalogue, source_id, field_path, kind)
                            )
        return tuple(references)

    # -- commit / discard (used by the draft status bar) -------------------
    def commit_and_report(self) -> CatalogueEdit:
        """Commit the staged draft through the Phase-2 gate and report the outcome."""
        result = self._controller.commit_draft()
        self._last_report = result.summary_with_scope()
        return self._result_to_edit(result, object_id="")

    def discard_and_report(self) -> str:
        """Discard the staged draft and return the message shown on the page."""
        self._controller.discard_draft()
        self._last_report = self._controller.state.last_message or "Draft discarded."
        return self._last_report

    def last_report(self) -> str:
        """Return the message of the last commit/discard action (``''`` when none)."""
        return self._last_report

    # -- reference system (Line sub-tab) -----------------------------------
    def reference_system(self, document: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        """Return the ``reference_system`` section of the working document."""
        doc = document if document is not None else self.document()
        section = doc.get("reference_system")
        return section if isinstance(section, dict) else {}

    def reference_value(self, field_name: str, document: Optional[dict[str, Any]] = None) -> Any:
        """Return one value of the reference system (``None`` when absent)."""
        return self.reference_system(document).get(field_name)

    def stage_reference_field(
        self, field_name: str, value: Any, *, description: str = ""
    ) -> CatalogueEdit:
        """Stage one reference-system field through the existing draft mechanism.

        Only the fields listed in :data:`REFERENCE_SYSTEM_EDITABLE` may be staged;
        the schema-fixed direction fields stay read-only.
        """
        if field_name not in REFERENCE_SYSTEM_EDITABLE:
            return CatalogueEdit(
                ok=False,
                staged=False,
                message=(
                    f"reference_system.{field_name} is not editable "
                    "(schema-fixed or unknown field)."
                ),
            )
        document = self.document()
        section = document.get("reference_system")
        if not isinstance(section, dict):
            section = {}
            document["reference_system"] = section
        section[field_name] = value
        result = self.stage(
            document,
            description=description or f"edit reference_system.{field_name}",
        )
        return self._result_to_edit(result, object_id=f"reference_system.{field_name}")

    # -- draft insight -----------------------------------------------------
    def pending_change_count(self) -> int:
        """Return the number of staged changes (0 when nothing is staged)."""
        staged = getattr(self._controller, "_draft_document", None)
        if not isinstance(staged, dict):
            return 0
        return _count_changes(self.committed_document(), staged)

    def draft_status_text(self) -> str:
        """Return the STAGED / COMMITTED / REJECTED status line for the editors."""
        state = self._controller.state
        if not state.draft_pending:
            return "CLEAN - no staged draft (the committed project is shown)"
        status = (state.draft_status or "UNKNOWN").upper()
        if status == "INVALID":
            return "REJECTED - staged draft is INVALID and blocks commit/export (APP-EDIT-002)"
        return f"STAGED - {self.pending_change_count()} pending change(s), draft status {status}"

    # -- provenance --------------------------------------------------------
    def provenance(self, catalogue: str, field_name: str) -> Provenance:
        """Return the provenance label of an editor field (INPUT or DERIVED)."""
        if field_name in DERIVED_FIELDS.get(catalogue, ()):
            return Provenance.DERIVED
        return Provenance.INPUT

    def diagnostics_for(self, object_id: str) -> tuple[Diagnostic, ...]:
        """Return the staged/committed diagnostics that belong to *object_id*."""
        result = self._controller.draft_result if self._controller.draft_pending else self._controller.validation
        if result is None:
            return ()
        return tuple(
            diagnostic
            for diagnostic in result.diagnostics
            if getattr(diagnostic, "object_id", None) == object_id
            or object_id in str(getattr(diagnostic, "context", {}))
        )

    def error_badge(self, object_id: str) -> str:
        """Return an error/warning badge text for a row (``''`` when clean)."""
        diagnostics = self.diagnostics_for(object_id)
        first_error = next(
            (item for item in diagnostics if item.severity is Severity.ERROR), None
        )
        if first_error is not None:
            return f"ERROR {first_error.code}"
        first_warning = next(
            (item for item in diagnostics if item.severity is Severity.WARNING), None
        )
        if first_warning is not None:
            return f"WARN {first_warning.code}"
        return ""

    def diagnostics_by_category(self) -> dict[str, dict[str, int]]:
        """Return error/warning/info counts grouped by reporting category (§G9)."""
        result = self._controller.draft_result if self._controller.draft_pending else self._controller.validation
        counts = {"schema": [0, 0, 0], "geometry": [0, 0, 0], "topology": [0, 0, 0], "operations": [0, 0, 0]}
        if result is None:
            return {name: {"errors": 0, "warnings": 0, "info": 0} for name in counts}
        for diagnostic in result.diagnostics:
            bucket = _category_bucket(str(getattr(diagnostic.category, "value", diagnostic.category)))
            slot = {Severity.ERROR: 0, Severity.WARNING: 1, Severity.INFO: 2}[diagnostic.severity]
            counts[bucket][slot] += 1
        return {
            name: {"errors": values[0], "warnings": values[1], "info": values[2]}
            for name, values in counts.items()
        }


#: Diagnostic categories mapped onto the four reporting buckets of §G9.
_CATEGORY_BUCKETS: dict[str, str] = {
    "SCHEMA": "schema",
    "PROJECT": "schema",
    "REF": "topology",
    "DIR": "schema",
    "ID": "schema",
    "ENUM": "schema",
    "UNIT": "schema",
    "FUTURE": "schema",
    "INFRASTRUCTURE": "geometry",
    "GEOMETRY": "geometry",
    "TOPOLOGY": "topology",
    "REGISTRY": "topology",
    "GRR": "topology",
    "PHASE2": "topology",
    "STATION": "operations",
    "PLATFORM": "operations",
    "STOP": "operations",
    "OBS": "operations",
}


def _category_bucket(category: str) -> str:
    """Map a diagnostic category onto one of the four reporting buckets."""
    return _CATEGORY_BUCKETS.get(category.upper(), "operations")


def _count_changes(committed: dict[str, Any], staged: dict[str, Any]) -> int:
    """Count differing entries between two canonical documents."""
    changes = 0
    committed_layers = committed.get(LAYER_SECTION) or []
    staged_layers = staged.get(LAYER_SECTION) or []
    for index, staged_layer in enumerate(staged_layers):
        committed_layer = committed_layers[index] if index < len(committed_layers) else {}
        if not isinstance(staged_layer, dict) or not isinstance(committed_layer, dict):
            changes += 1
            continue
        for catalogue, staged_entries in staged_layer.items():
            if not isinstance(staged_entries, list):
                if staged_entries != committed_layer.get(catalogue):
                    changes += 1
                continue
            committed_entries = committed_layer.get(catalogue) or []
            committed_by_id = {
                str(entry.get("id")): entry for entry in committed_entries if isinstance(entry, dict)
            }
            staged_ids: set[str] = set()
            for entry in staged_entries:
                if not isinstance(entry, dict):
                    changes += 1
                    continue
                object_id = str(entry.get("id"))
                staged_ids.add(object_id)
                if committed_by_id.get(object_id) != entry:
                    changes += 1
            changes += len(set(committed_by_id) - staged_ids)
    for section, value in staged.items():
        if section == LAYER_SECTION:
            continue
        if committed.get(section) != value:
            changes += 1
    return changes


def editable_catalogues() -> tuple[str, ...]:
    """Return the catalogue keys the Phase-3 editors can edit."""
    return tuple(EDITOR_FIELDS)


def catalogues_with_entries(document: dict[str, Any], layer_index: int = 0) -> tuple[str, ...]:
    """Return the catalogues that carry at least one entry in *document*."""
    layers = document.get(LAYER_SECTION) or []
    if not layers:
        return ()
    layer = layers[min(layer_index, len(layers) - 1)]
    if not isinstance(layer, dict):
        return ()
    return tuple(
        key for key in EDITOR_FIELDS if isinstance(layer.get(key), list) and layer.get(key)
    )


@dataclass
class EditorRowState:
    """Rendered state of one editor row (used by the widget layer)."""

    object_id: str
    badge: str = ""
    values: dict[str, Any] = dataclass_field(default_factory=dict)
    errors: tuple[Diagnostic, ...] = ()

    @property
    def has_error(self) -> bool:
        """Return whether the row carries an ERROR diagnostic."""
        return any(item.severity is Severity.ERROR for item in self.errors)


# ---------------------------------------------------------------------------
# Nested catalogues (a catalogue stored *inside* another catalogue)
# ---------------------------------------------------------------------------
#: Catalogues that live inside an owning catalogue: ``nested -> (owner, path)``.
NESTED_CATALOGUES: dict[str, tuple[str, str]] = {
    "vertical_profile_points": ("vertical_profiles", "points"),
}

#: Field that defines the stored order of a nested catalogue (used for insertion).
NESTED_CATALOGUE_ORDER: dict[str, str] = {
    "vertical_profile_points": "chainage_km",
}

#: Reference-system fields of the ``project`` section that the Line editor may change.
REFERENCE_SYSTEM_EDITABLE: tuple[str, ...] = (
    "alignment_id",
    "chainage_start_km",
    "chainage_end_km",
    "chainage_origin_name",
    "chainage_end_name",
    "projection",
    "coordinate_system",
    "datum",
    "curve_radius_convention",
)

#: Reference-system fields fixed by the frozen schema (displayed, never edited).
REFERENCE_SYSTEM_FIXED: tuple[str, ...] = ("forward_direction", "reverse_direction")


class ScopedEditor(InfrastructureEditor):
    """An editor view scoped to the nested entries of one owning object.

    ``vertical_profile_points`` is stored inside its profile
    (``vertical_profiles[i].points``) rather than as a top-level catalogue.  This
    subclass only changes **where** the entries are read from and written to; the
    staging path, validation and draft mechanism are inherited unchanged, so a
    nested edit behaves exactly like a top-level edit (including APP-EDIT-002).
    """

    def __init__(
        self,
        controller: ProjectController,
        *,
        catalogue: str,
        owner_id: str,
        layer_index: int = 0,
    ) -> None:
        super().__init__(controller, layer_index=layer_index)
        if catalogue not in NESTED_CATALOGUES:
            raise KeyError(f"{catalogue!r} is not a nested catalogue")
        self._nested_catalogue = catalogue
        self._owner_id = owner_id

    # -- accessors ---------------------------------------------------------
    @property
    def catalogue(self) -> str:
        """Return the nested catalogue key edited by this view."""
        return self._nested_catalogue

    @property
    def owner_id(self) -> str:
        """Return the id of the owning object."""
        return self._owner_id

    @property
    def owner_catalogue(self) -> str:
        """Return the catalogue key of the owning object."""
        return NESTED_CATALOGUES[self._nested_catalogue][0]

    @property
    def container_field(self) -> str:
        """Return the field of the owner that holds the nested entries."""
        return NESTED_CATALOGUES[self._nested_catalogue][1]

    # -- scoped reads ------------------------------------------------------
    def entries(
        self, catalogue: str, document: Optional[dict[str, Any]] = None
    ) -> list[dict[str, Any]]:
        """Return the *live* nested list of the owner (so adds/deletes stage in place)."""
        doc = document if document is not None else self.document()
        owner = None
        for record in InfrastructureEditor.entries(self, self.owner_catalogue, doc):
            if record.get("id") == self._owner_id:
                owner = record
                break
        if owner is None:
            return []
        raw = owner.get(self.container_field)
        if not isinstance(raw, list):
            raw = []
            owner[self.container_field] = raw
        return raw  # type: ignore[return-value]

    def container(
        self, catalogue: str, document: Optional[dict[str, Any]] = None
    ) -> list[Any]:
        """Return the live nested list of the owner (the container the document holds)."""
        return self.entries(catalogue, document)

    def stage_entry(
        self,
        catalogue: str,
        values: dict[str, Any],
        *,
        object_id: Optional[str] = None,
        description: str = "",
    ) -> CatalogueEdit:
        """Add or update a nested entry, placing *new* entries by their chainage.

        A new vertical profile point is inserted at the position implied by its own
        ``chainage_km`` value so that the stored "strictly increasing" order is
        preserved by construction.  No value is invented, altered or repaired: the
        entry keeps exactly the values it was given, and validation still decides
        whether the draft may be committed.
        """
        document = self.document()
        target_id = object_id or str(values.get("id") or "")
        if target_id and self.entry(catalogue, target_id, document) is None:
            entries = self.entries(catalogue, document)
            record: dict[str, Any] = {"id": target_id}
            position = self._insert_position(entries, values.get(self.order_field))
            entries.insert(position, record)
        return super().stage_entry(
            catalogue, values, object_id=target_id, description=description
        )

    @property
    def order_field(self) -> str:
        """Return the field that defines the stored order of a nested catalogue."""
        return NESTED_CATALOGUE_ORDER.get(self._nested_catalogue, "")

    @staticmethod
    def _insert_position(entries: list[dict[str, Any]], chainage: Any) -> int:
        """Return the index a new entry with *chainage* should be inserted at."""
        if not isinstance(chainage, (int, float)) or isinstance(chainage, bool):
            return len(entries)
        for index, record in enumerate(entries):
            value = record.get("chainage_km")
            if isinstance(value, (int, float)) and not isinstance(value, bool) and value > chainage:
                return index
        return len(entries)

    def owner_ids(self, document: Optional[dict[str, Any]] = None) -> tuple[str, ...]:
        """Return the ids of the possible owners (profiles that can hold points)."""
        doc = document if document is not None else self.document()
        return tuple(
            str(record.get("id"))
            for record in InfrastructureEditor.entries(self, self.owner_catalogue, doc)
        )


# ---------------------------------------------------------------------------
# Reference system (project section, edited from the Line sub-tab)
# ---------------------------------------------------------------------------
def reference_system_fields() -> tuple[str, ...]:
    """Return every reference-system field in display order."""
    return REFERENCE_SYSTEM_EDITABLE + REFERENCE_SYSTEM_FIXED
