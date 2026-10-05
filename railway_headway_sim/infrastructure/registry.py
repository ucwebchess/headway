"""Global engineering object registry (Phase 2, frozen rule).

**Frozen rule:** every registered engineering object ID must be globally unique
across the project. The registry spans the union of the typed catalogues of all
``infrastructure[*]`` layers.

What is registered: the typed Phase-2 engineering objects (alignments, track
groups, horizontal geometry sections, vertical profile points, speed
restrictions, nodes, tracks, stations, platforms, stopping marks, observation
points).

What is **not** registered:

* arbitrary nested extension dictionaries that merely contain an ``"id"`` field
  (they are preserved data, not engineering objects);
* Phase-1 opaque signalling / rolling-stock / services / legacy catalogue
  records (later phases extend the registry to those).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Iterator, Optional

#: Registry object type -> human label (stable, single source for UI/diagnostics).
OBJECT_TYPE_LABELS: dict[str, str] = {
    "alignment": "Alignment",
    "track_group": "Track group",
    "horizontal_geometry_section": "Horizontal geometry section",
    "vertical_profile": "Vertical profile",
    "vertical_profile_point": "Vertical profile point",
    "speed_restriction": "Speed restriction",
    "node": "Topology node",
    "track": "Track edge",
    "station": "Station",
    "platform": "Platform",
    "stopping_mark": "Stopping mark",
    "observation_point": "Observation point",
}


@dataclass(frozen=True)
class RegisteredObject:
    """One registered engineering object and where it came from."""

    object_id: str
    object_type: str
    json_path: str
    layer_id: Optional[str]
    value: Any


@dataclass(frozen=True)
class DuplicateRegistration:
    """A globally duplicated engineering ID."""

    object_id: str
    registrations: tuple[RegisteredObject, ...]

    @property
    def object_types(self) -> tuple[str, ...]:
        """Return the distinct object types sharing this ID, in registration order."""
        seen: list[str] = []
        for registration in self.registrations:
            if registration.object_type not in seen:
                seen.append(registration.object_type)
        return tuple(seen)

    def describe(self) -> str:
        """Return a human-readable description of the collision."""
        parts = [
            f"{OBJECT_TYPE_LABELS.get(r.object_type, r.object_type)} at {r.json_path}"
            for r in self.registrations
        ]
        return f"ID '{self.object_id}' is registered {len(parts)} times: " + "; ".join(parts)


@dataclass
class EngineeringRegistry:
    """Index of every typed engineering object of a project by globally unique ID."""

    _by_id: dict[str, list[RegisteredObject]] = field(default_factory=dict)
    _order: list[str] = field(default_factory=list)

    # -- construction ------------------------------------------------------
    def register(
        self,
        object_id: str,
        object_type: str,
        value: Any,
        *,
        json_path: str = "",
        layer_id: Optional[str] = None,
    ) -> None:
        """Register one engineering object (duplicates are kept, then reported)."""
        registration = RegisteredObject(
            object_id=object_id,
            object_type=object_type,
            json_path=json_path,
            layer_id=layer_id,
            value=value,
        )
        if object_id not in self._by_id:
            self._by_id[object_id] = []
            self._order.append(object_id)
        self._by_id[object_id].append(registration)

    def extend(self, registrations: Iterable[RegisteredObject]) -> None:
        """Register many objects at once."""
        for registration in registrations:
            self.register(
                registration.object_id,
                registration.object_type,
                registration.value,
                json_path=registration.json_path,
                layer_id=registration.layer_id,
            )

    # -- queries -----------------------------------------------------------
    def get(self, object_id: str) -> Optional[RegisteredObject]:
        """Return the first registration of *object_id*, or ``None``."""
        registrations = self._by_id.get(object_id)
        return registrations[0] if registrations else None

    def get_all(self, object_id: str) -> tuple[RegisteredObject, ...]:
        """Return every registration of *object_id* (empty tuple when unknown)."""
        return tuple(self._by_id.get(object_id, ()))

    def exists(self, object_id: str) -> bool:
        """Return ``True`` when *object_id* is registered at least once."""
        return bool(self._by_id.get(object_id))

    def type_of(self, object_id: str) -> Optional[str]:
        """Return the registry object type of *object_id*, or ``None``."""
        registration = self.get(object_id)
        return registration.object_type if registration else None

    def label_of(self, object_id: str) -> Optional[str]:
        """Return the human label of the registered type of *object_id*."""
        object_type = self.type_of(object_id)
        return None if object_type is None else OBJECT_TYPE_LABELS.get(object_type, object_type)

    def value_of(self, object_id: str) -> Any:
        """Return the registered object value of *object_id* (``None`` when unknown)."""
        registration = self.get(object_id)
        return registration.value if registration else None

    def ids(self) -> tuple[str, ...]:
        """Return all registered IDs in registration order."""
        return tuple(self._order)

    def object_ids_by_type(self, object_type: str) -> tuple[str, ...]:
        """Return the IDs of all objects of *object_type*, in registration order."""
        return tuple(
            object_id
            for object_id in self._order
            if self._by_id[object_id][0].object_type == object_type
        )

    def objects_by_type(self, object_type: str) -> tuple[RegisteredObject, ...]:
        """Return all registered objects of *object_type*, in registration order."""
        return tuple(
            registration
            for object_id in self._order
            for registration in (self._by_id[object_id][0],)
            if registration.object_type == object_type
        )

    def iter_registrations(self) -> Iterator[RegisteredObject]:
        """Iterate over the primary registration of every ID, in order."""
        for object_id in self._order:
            yield self._by_id[object_id][0]

    def type_counts(self) -> dict[str, int]:
        """Return the number of registered objects per object type (stable order)."""
        counts: dict[str, int] = {}
        for registration in self.iter_registrations():
            counts[registration.object_type] = counts.get(registration.object_type, 0) + 1
        return counts

    def duplicates(self) -> tuple[DuplicateRegistration, ...]:
        """Return every globally duplicated ID with all of its registrations."""
        duplicates: list[DuplicateRegistration] = []
        for object_id in self._order:
            registrations = self._by_id[object_id]
            if len(registrations) > 1:
                duplicates.append(
                    DuplicateRegistration(object_id=object_id, registrations=tuple(registrations))
                )
        return tuple(duplicates)

    def has_type_of(self, object_id: str, expected_type: str) -> bool:
        """Return ``True`` when *object_id* is registered with *expected_type*."""
        return self.type_of(object_id) == expected_type

    def size(self) -> int:
        """Return the number of distinct registered IDs."""
        return len(self._order)

    def __len__(self) -> int:
        """Return the number of distinct registered IDs."""
        return len(self._order)

    def __contains__(self, object_id: object) -> bool:
        """Return whether *object_id* is registered."""
        return isinstance(object_id, str) and self.exists(object_id)

    def __iter__(self) -> Iterator[RegisteredObject]:
        """Iterate over the primary registration of every ID."""
        return self.iter_registrations()


def build_registry(
    typed_objects: Iterable[tuple[str, str, Any, str, Optional[str]]],
) -> EngineeringRegistry:
    """Build a registry from ``(object_id, object_type, value, json_path, layer_id)`` tuples."""
    registry = EngineeringRegistry()
    for object_id, object_type, value, json_path, layer_id in typed_objects:
        registry.register(
            object_id, object_type, value, json_path=json_path, layer_id=layer_id
        )
    return registry
