"""Compact normative outer contract for one deterministic CEGAR step."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
from typing import Hashable, Iterable

from acfqp.abstraction.partition import Partition

from .predicates import canonical_fraction
from .split import (
    RankedSplitCandidate,
    RefinementTracker,
    SplitResult,
    attempt_split,
    rank_split_candidates,
)


class CEGARStatus(str, Enum):
    """The eight externally visible V0 refinement outcomes."""

    CERTIFIED = "CERTIFIED"
    SPLIT_ACCEPTED = "SPLIT_ACCEPTED"
    NO_SEPARATING_PREDICATE = "NO_SEPARATING_PREDICATE"
    ALL_SPLITS_REJECTED = "ALL_SPLITS_REJECTED"
    REFINEMENT_BUDGET_EXHAUSTED = "REFINEMENT_BUDGET_EXHAUSTED"
    RATE_BUDGET_EXHAUSTED = "RATE_BUDGET_EXHAUSTED"
    GROUND_FALLBACK = "GROUND_FALLBACK"
    INFEASIBLE_QUERY = "INFEASIBLE_QUERY"


@dataclass(frozen=True)
class RefinementBudget:
    max_leaves: int
    max_accepted_splits: int
    rate_budget_bits: Fraction
    max_candidate_evaluations: int
    max_fallback_invocations: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "rate_budget_bits", canonical_fraction(self.rate_budget_bits))
        if self.max_leaves < 1:
            raise ValueError("maximum leaves must be positive")
        if min(
            self.max_accepted_splits,
            self.max_candidate_evaluations,
            self.max_fallback_invocations,
        ) < 0:
            raise ValueError("refinement budgets must be non-negative")
        if self.rate_budget_bits < 0:
            raise ValueError("rate budget must be non-negative")

    @classmethod
    def full_v0(cls) -> "RefinementBudget":
        return cls(64, 63, Fraction(256), 2_048, 32)

    @classmethod
    def phase05(cls) -> "RefinementBudget":
        return cls(8, 7, Fraction(256), 128, 4)


@dataclass(frozen=True)
class RefinementCounters:
    leaves: int = 1
    accepted_splits: int = 0
    rate_bits: Fraction = Fraction(0)
    candidate_evaluations: int = 0
    fallback_invocations: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "rate_bits", canonical_fraction(self.rate_bits))
        if min(
            self.leaves,
            self.accepted_splits,
            self.candidate_evaluations,
            self.fallback_invocations,
        ) < 0:
            raise ValueError("refinement counters must be non-negative")


@dataclass(frozen=True)
class CEGARResult:
    status: CEGARStatus
    partition: Partition
    counters: RefinementCounters
    split: SplitResult | None = None
    considered_predicates: tuple[str, ...] = ()
    detail: str = ""


def _result(
    status: CEGARStatus,
    partition: Partition,
    counters: RefinementCounters,
    *,
    split: SplitResult | None = None,
    considered: Iterable[str] = (),
    detail: str = "",
) -> CEGARResult:
    return CEGARResult(status, partition, counters, split, tuple(considered), detail)


def refine_once(
    partition: Partition,
    cell: Hashable,
    candidates: Iterable[RankedSplitCandidate],
    tracker: RefinementTracker,
    budget: RefinementBudget,
    counters: RefinementCounters,
    *,
    current_audit_width: Fraction,
    witness: tuple[Hashable, Hashable] | None = None,
    already_certified: bool = False,
    query_feasible: bool = True,
) -> CEGARResult:
    """Rank, budget-check, and attempt one accepted local refinement.

    Candidate metrics are produced by the exact audit layer.  A structurally
    valid split is accepted only if it reduces current maximum audit width by
    at least 20 percent or certifies at least one previously uncertified
    reachable ``(cell, horizon)`` pair.
    """

    if not query_feasible:
        return _result(CEGARStatus.INFEASIBLE_QUERY, partition, counters)
    if already_certified:
        return _result(CEGARStatus.CERTIFIED, partition, counters)
    if counters.leaves >= budget.max_leaves or counters.accepted_splits >= budget.max_accepted_splits:
        return _result(
            CEGARStatus.REFINEMENT_BUDGET_EXHAUSTED,
            partition,
            counters,
            detail="leaf or accepted-split budget exhausted",
        )

    width = canonical_fraction(current_audit_width)
    if width < 0:
        raise ValueError("current audit width must be non-negative")
    ranked = rank_split_candidates(tuple(candidates))
    if witness is not None:
        left, right = witness
        separating = tuple(
            candidate
            for candidate in ranked
            if candidate.predicate(left) != candidate.predicate(right)
        )
    else:
        separating = ranked
    if not separating:
        return _result(
            CEGARStatus.NO_SEPARATING_PREDICATE,
            partition,
            counters,
            detail="finite grammar contains no predicate separating the witness",
        )

    considered: list[str] = []
    evaluations = counters.candidate_evaluations
    saw_rate_block = False
    saw_non_rate_rejection = False
    for candidate in separating:
        if evaluations >= budget.max_candidate_evaluations:
            updated = RefinementCounters(
                counters.leaves,
                counters.accepted_splits,
                counters.rate_bits,
                evaluations,
                counters.fallback_invocations,
            )
            return _result(
                CEGARStatus.REFINEMENT_BUDGET_EXHAUSTED,
                partition,
                updated,
                considered=considered,
                detail="candidate-evaluation budget exhausted",
            )
        evaluations += 1
        considered.append(candidate.predicate.canonical_id)

        quality_passes = candidate.newly_certified_pairs > 0 or (
            width > 0
            and candidate.audit_width_reduction * 5 >= width
        )
        if not quality_passes:
            saw_non_rate_rejection = True
            continue
        if counters.rate_bits + candidate.rate_cost > budget.rate_budget_bits:
            saw_rate_block = True
            continue

        split = attempt_split(partition, cell, candidate.predicate, tracker)
        if not split.accepted:
            saw_non_rate_rejection = True
            continue
        updated = RefinementCounters(
            leaves=counters.leaves + 1,
            accepted_splits=counters.accepted_splits + 1,
            rate_bits=counters.rate_bits + candidate.rate_cost,
            candidate_evaluations=evaluations,
            fallback_invocations=counters.fallback_invocations,
        )
        return _result(
            CEGARStatus.SPLIT_ACCEPTED,
            split.partition,
            updated,
            split=split,
            considered=considered,
        )

    updated = RefinementCounters(
        counters.leaves,
        counters.accepted_splits,
        counters.rate_bits,
        evaluations,
        counters.fallback_invocations,
    )
    if saw_rate_block and not saw_non_rate_rejection:
        return _result(
            CEGARStatus.RATE_BUDGET_EXHAUSTED,
            partition,
            updated,
            considered=considered,
        )
    return _result(
        CEGARStatus.ALL_SPLITS_REJECTED,
        partition,
        updated,
        considered=considered,
    )


def record_ground_fallback(
    partition: Partition,
    budget: RefinementBudget,
    counters: RefinementCounters,
) -> CEGARResult:
    """Charge a ground fallback without hiding exhaustion."""

    if counters.fallback_invocations >= budget.max_fallback_invocations:
        return _result(
            CEGARStatus.REFINEMENT_BUDGET_EXHAUSTED,
            partition,
            counters,
            detail="ground fallback/oracle budget exhausted",
        )
    updated = RefinementCounters(
        counters.leaves,
        counters.accepted_splits,
        counters.rate_bits,
        counters.candidate_evaluations,
        counters.fallback_invocations + 1,
    )
    return _result(CEGARStatus.GROUND_FALLBACK, partition, updated)
