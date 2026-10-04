"""Read-only bilateral genealogy queries over the existing person registry."""

from __future__ import annotations

from collections import defaultdict, deque

from .family_models import FamilyPerson


class BilateralGenealogy:
    def __init__(self, people: dict[int, FamilyPerson]):
        self.people = people
        self._children: dict[int, set[int]] = defaultdict(set)
        for child in people.values():
            for parent_id in (child.mother_id, child.father_id):
                if parent_id is not None:
                    self._children[parent_id].add(child.id)

    def _ancestors_from(self, parent_id: int | None, side: str,
                        max_generations: int | None) -> dict[int, dict[str, object]]:
        found: dict[int, dict[str, object]] = {}
        if parent_id is None:
            return found
        queue = deque([(parent_id, 1)])
        while queue:
            person_id, distance = queue.popleft()
            if max_generations is not None and distance > max_generations:
                continue
            if person_id not in self.people:
                continue
            existing = found.get(person_id)
            if existing is not None and existing["distance"] <= distance:
                continue
            found[person_id] = {"person_id": person_id, "distance": distance, "side": side}
            person = self.people[person_id]
            queue.extend((ancestor_id, distance + 1) for ancestor_id in
                         (person.mother_id, person.father_id) if ancestor_id is not None)
        return found

    def query(self, person_id: int, *, max_generations: int | None = None) -> dict[str, object]:
        if person_id not in self.people:
            raise KeyError(f"unknown person: {person_id}")
        if max_generations is not None and (type(max_generations) is not int or max_generations < 1):
            raise ValueError("max_generations must be a positive integer or None")
        root = self.people[person_id]
        maternal = self._ancestors_from(root.mother_id, "maternal", max_generations)
        paternal = self._ancestors_from(root.father_id, "paternal", max_generations)
        combined = {}
        for ancestor_id in sorted(set(maternal) | set(paternal)):
            sides = [side for side, rows in (("maternal", maternal), ("paternal", paternal))
                     if ancestor_id in rows]
            distances = [rows[ancestor_id]["distance"] for rows in (maternal, paternal)
                         if ancestor_id in rows]
            combined[ancestor_id] = {
                "person_id": ancestor_id,
                "distance": min(distances),
                "sides": sides,
            }

        descendants: dict[int, int] = {}
        queue = deque((child_id, 1) for child_id in sorted(self._children.get(person_id, ())))
        while queue:
            child_id, distance = queue.popleft()
            if max_generations is not None and distance > max_generations:
                continue
            if child_id not in self.people:
                continue
            prior = descendants.get(child_id)
            if prior is not None and prior <= distance:
                continue
            descendants[child_id] = distance
            queue.extend((next_id, distance + 1)
                         for next_id in sorted(self._children.get(child_id, ())))
        return {
            "person_id": person_id,
            "max_generations": max_generations,
            "maternal_ancestors": [maternal[key] for key in sorted(maternal)],
            "paternal_ancestors": [paternal[key] for key in sorted(paternal)],
            "ancestors": [combined[key] for key in sorted(combined)],
            "descendants": [
                {"person_id": key, "distance": descendants[key]}
                for key in sorted(descendants)
            ],
        }
