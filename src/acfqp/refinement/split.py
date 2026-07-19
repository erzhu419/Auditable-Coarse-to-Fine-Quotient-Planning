"""Deterministic, duplicate-safe hard-partition splitting."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from fractions import Fraction
from typing import Hashable, Iterable

from acfqp.abstraction.partition import Partition

from .predicates import Predicate, canonical_fraction


class SplitStatus(str, Enum):
    SPLIT_ACCEPTED = "SPLIT_ACCEPTED"
    DUPLICATE_PREDICATE = "DUPLICATE_PREDICATE"
    DUPLICATE_PARTITION = "DUPLICATE_PARTITION"
    NO_OP_SPLIT = "NO_OP_SPLIT"


@dataclass
class RefinementTracker:
    """Mutable build-local memory preventing repeated split work."""

    path_predicates: dict[Hashable, tuple[str, ...]] = field(default_factory=dict)
    evaluated_child_signatures: dict[Hashable, set[tuple[tuple[str, ...], ...]]] = field(
        default_factory=dict
    )

    def predicate_path(self, cell: Hashable) -> tuple[str, ...]:
        return self.path_predicates.get(cell, ())


@dataclass(frozen=True)
class SplitResult:
    status: SplitStatus
    partition: Partition
    predicate_id: str
    parent_cell: Hashable
    false_cell: Hashable | None = None
    true_cell: Hashable | None = None
    detail: str = ""

    @property
    def accepted(self) -> bool:
        return self.status is SplitStatus.SPLIT_ACCEPTED


@dataclass(frozen=True)
class RankedSplitCandidate:
    predicate: Predicate
    audit_width_reduction: Fraction
    newly_certified_pairs: int = 0
    failure_width_reduction: Fraction = Fraction(0)
    rate_cost: Fraction = Fraction(1)

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "audit_width_reduction", canonical_fraction(self.audit_width_reduction)
        )
        object.__setattr__(
            self, "failure_width_reduction", canonical_fraction(self.failure_width_reduction)
        )
        object.__setattr__(self, "rate_cost", canonical_fraction(self.rate_cost))
        if self.rate_cost <= 0:
            raise ValueError("split rate cost must be positive")

    @property
    def score(self) -> Fraction:
        return self.audit_width_reduction / self.rate_cost


def rank_split_candidates(
    candidates: Iterable[RankedSplitCandidate],
) -> tuple[RankedSplitCandidate, ...]:
    """Apply the frozen deterministic split order and tie breakers."""

    return tuple(
        sorted(
            candidates,
            key=lambda candidate: (
                -candidate.score,
                -candidate.newly_certified_pairs,
                -candidate.failure_width_reduction,
                candidate.rate_cost,
                candidate.predicate.canonical_id,
            ),
        )
    )


def _child_signature(
    false_states: Iterable[Hashable],
    true_states: Iterable[Hashable],
) -> tuple[tuple[str, ...], ...]:
    false_block = tuple(sorted(repr(state) for state in false_states))
    true_block = tuple(sorted(repr(state) for state in true_states))
    return tuple(sorted((false_block, true_block)))


def attempt_split(
    partition: Partition,
    cell: Hashable,
    predicate: Predicate,
    tracker: RefinementTracker,
) -> SplitResult:
    """Apply one canonical predicate, rejecting duplicate and no-op work."""

    predicate_id = predicate.canonical_id
    if predicate_id in tracker.predicate_path(cell):
        return SplitResult(
            SplitStatus.DUPLICATE_PREDICATE,
            partition,
            predicate_id,
            cell,
            detail="predicate already occurs on the root-to-cell path",
        )
    members = partition.members(cell)
    true_states = tuple(state for state in members if predicate(state))
    false_states = tuple(state for state in members if not predicate(state))
    if not true_states or not false_states:
        return SplitResult(
            SplitStatus.NO_OP_SPLIT,
            partition,
            predicate_id,
            cell,
            detail="predicate creates an empty child",
        )
    signature = _child_signature(false_states, true_states)
    evaluated = tracker.evaluated_child_signatures.setdefault(cell, set())
    if signature in evaluated:
        return SplitResult(
            SplitStatus.DUPLICATE_PARTITION,
            partition,
            predicate_id,
            cell,
            detail="equivalent child partition was already evaluated",
        )
    evaluated.add(signature)

    false_cell = f"{cell!r}|{predicate_id}|false"
    true_cell = f"{cell!r}|{predicate_id}|true"
    refined = partition.replace_cell(
        cell,
        false_states,
        true_states,
        false_cell,
        true_cell,
    )
    inherited_path = tracker.predicate_path(cell) + (predicate_id,)
    tracker.path_predicates[false_cell] = inherited_path
    tracker.path_predicates[true_cell] = inherited_path
    return SplitResult(
        SplitStatus.SPLIT_ACCEPTED,
        refined,
        predicate_id,
        cell,
        false_cell=false_cell,
        true_cell=true_cell,
    )
