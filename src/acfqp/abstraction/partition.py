"""Immutable hard partitions of finite ground-state sets."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Hashable, Iterable, Mapping


@dataclass(frozen=True)
class Partition:
    """A total, hard assignment from each registered state to one cell."""

    assignments: tuple[tuple[Hashable, Hashable], ...]

    def __post_init__(self) -> None:
        state_to_cell: dict[Hashable, Hashable] = {}
        for state, cell in self.assignments:
            if state in state_to_cell:
                raise ValueError(f"state {state!r} appears more than once in partition")
            state_to_cell[state] = cell
        if not state_to_cell:
            raise ValueError("partition must contain at least one state")
        populated = {cell for cell in state_to_cell.values()}
        if any(cell is None for cell in populated):
            raise ValueError("partition cell identifiers must not be None")

    @classmethod
    def from_mapping(cls, mapping: Mapping[Hashable, Hashable]) -> "Partition":
        return cls(tuple(sorted(mapping.items(), key=lambda item: repr(item[0]))))

    @classmethod
    def from_cells(
        cls,
        cells: Mapping[Hashable, Iterable[Hashable]],
    ) -> "Partition":
        assignments: dict[Hashable, Hashable] = {}
        for cell, states in cells.items():
            members = tuple(states)
            if not members:
                raise ValueError(f"cell {cell!r} is empty")
            for state in members:
                if state in assignments:
                    raise ValueError(f"state {state!r} appears in multiple cells")
                assignments[state] = cell
        return cls.from_mapping(assignments)

    @classmethod
    def single_cell(
        cls,
        states: Iterable[Hashable],
        cell: Hashable = "root",
    ) -> "Partition":
        return cls.from_cells({cell: tuple(states)})

    @property
    def cell_ids(self) -> tuple[Hashable, ...]:
        return tuple(sorted({cell for _, cell in self.assignments}, key=repr))

    @property
    def states(self) -> tuple[Hashable, ...]:
        return tuple(state for state, _ in self.assignments)

    def cell_of(self, state: Hashable) -> Hashable:
        for registered, cell in self.assignments:
            if registered == state:
                return cell
        raise KeyError(f"state {state!r} is not registered in partition")

    def members(self, cell: Hashable) -> tuple[Hashable, ...]:
        states = tuple(state for state, assigned in self.assignments if assigned == cell)
        if not states:
            raise KeyError(f"unknown or empty cell {cell!r}")
        return states

    def signature(self) -> tuple[tuple[str, ...], ...]:
        """A label-independent canonical signature of the represented blocks."""

        blocks = [tuple(sorted((repr(state) for state in self.members(cell)))) for cell in self.cell_ids]
        return tuple(sorted(blocks))

    def replace_cell(
        self,
        cell: Hashable,
        false_states: Iterable[Hashable],
        true_states: Iterable[Hashable],
        false_cell: Hashable,
        true_cell: Hashable,
    ) -> "Partition":
        expected = set(self.members(cell))
        false_members = set(false_states)
        true_members = set(true_states)
        if not false_members or not true_members:
            raise ValueError("a hard split must create two non-empty children")
        if false_members & true_members:
            raise ValueError("split children overlap")
        if false_members | true_members != expected:
            raise ValueError("split children do not exactly cover the parent cell")
        if false_cell == true_cell:
            raise ValueError("split children require distinct identifiers")
        unaffected_cells = set(self.cell_ids) - {cell}
        if false_cell in unaffected_cells or true_cell in unaffected_cells:
            raise ValueError("split child identifier collides with an existing cell")
        mapping = dict(self.assignments)
        for state in false_members:
            mapping[state] = false_cell
        for state in true_members:
            mapping[state] = true_cell
        return Partition.from_mapping(mapping)
