"""Counterexample-driven deterministic refinement primitives."""

from .predicates import Predicate, canonical_fraction
from .split import (
    RankedSplitCandidate,
    RefinementTracker,
    SplitResult,
    SplitStatus,
    attempt_split,
    rank_split_candidates,
)
from .cegar import (
    CEGARResult,
    CEGARStatus,
    RefinementBudget,
    RefinementCounters,
    record_ground_fallback,
    refine_once,
)

__all__ = [
    "Predicate",
    "CEGARResult",
    "CEGARStatus",
    "RankedSplitCandidate",
    "RefinementTracker",
    "RefinementBudget",
    "RefinementCounters",
    "SplitResult",
    "SplitStatus",
    "attempt_split",
    "canonical_fraction",
    "rank_split_candidates",
    "record_ground_fallback",
    "refine_once",
]
