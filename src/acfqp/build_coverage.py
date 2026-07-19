"""Immutable coverage contracts for reusable finite-kernel builds.

V0 Phase 0.5 builds a model only over the all-action/all-outcome transition
closure of the query's positive initial support.  Such a build may be reused
only for a query whose positive support is already contained in that closure.
The initial-law digest remains part of the build descriptor so changing
``rho0`` produces a different build identity even when the resulting closure
set happens to be unchanged.

Phase 3 suite builds use a distinct contract.  They close the union of the
declared queries' positive supports once, and bind the build to that canonical
support *set*.  Consequently their support digest is intentionally independent
of query order and probability masses.  Keeping this as a separate value object
prevents those reusable-suite semantics from silently changing the Phase 0.5
per-query :class:`BuildCoverage` identity contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Any, Generic, Hashable, Iterable, TypeVar

from .artifacts import canonical_sha256, object_id
from .core import FiniteKernel, QuerySpec


StateT = TypeVar("StateT", bound=Hashable)


class QueryOutsideBuildCoverageError(ValueError):
    """Raised when a cached model does not cover a candidate query support."""


def _ordered_states(states: Iterable[StateT]) -> tuple[StateT, ...]:
    return tuple(
        sorted(states, key=lambda state: (type(state).__qualname__, repr(state)))
    )


def transition_closure(
    kernel: FiniteKernel[StateT, Any],
    initial_distribution: Iterable[tuple[Fraction, StateT]],
    *,
    state_cap: int = 50_000,
) -> tuple[StateT, ...]:
    """Return the complete all-action/all-positive-outcome state closure.

    This closure is deliberately not horizon truncated: every legal action is
    followed at every nonterminal state until no unseen successor remains.
    Consequently, support-subset validation is sufficient for safe reuse with
    any structurally registered finite-horizon query over the same kernel.
    """

    if state_cap <= 0:
        raise ValueError("transition-closure state cap must be positive")
    initial = tuple(initial_distribution)
    seen = {state for probability, state in initial if Fraction(probability) > 0}
    if not seen:
        raise ValueError(
            "transition closure requires nonempty positive-probability support"
        )
    pending = list(reversed(_ordered_states(seen)))
    while pending:
        state = pending.pop()
        if kernel.is_terminal(state):
            continue
        for action in sorted(kernel.actions(state), key=repr):
            outcomes = kernel.step(state, action)
            mass = sum((outcome.probability for outcome in outcomes), Fraction(0))
            if not outcomes or mass != 1:
                raise ValueError(
                    "coverage closure requires nonempty unit-mass transitions"
                )
            for outcome in outcomes:
                if outcome.probability <= 0:
                    continue
                successor = outcome.next_state
                if successor in seen:
                    continue
                if len(seen) >= state_cap:
                    raise RuntimeError(
                        "RAPM transition closure exceeded the exact state cap"
                    )
                seen.add(successor)
                pending.append(successor)
    return _ordered_states(seen)


@dataclass(frozen=True, slots=True)
class BuildCoverage(Generic[StateT]):
    """A query-support-derived, immutable build-coverage certificate."""

    initial_support_sha256: str
    covered_states: tuple[StateT, ...]
    covered_state_ids: tuple[str, ...]

    mode: str = "query_support_transition_closure"
    reuse_outside_coverage_forbidden: bool = True

    def __post_init__(self) -> None:
        ordered = _ordered_states(self.covered_states)
        if ordered != self.covered_states or len(set(ordered)) != len(ordered):
            raise ValueError("covered states must be unique and canonically ordered")
        expected_ids = tuple(sorted(object_id(state, "state") for state in ordered))
        if self.covered_state_ids != expected_ids:
            raise ValueError("covered state IDs do not match the covered states")
        if len(self.initial_support_sha256) != 64:
            raise ValueError("initial-support digest must be a full SHA-256")
        if self.mode != "query_support_transition_closure":
            raise ValueError("unsupported build-coverage mode")
        if self.reuse_outside_coverage_forbidden is not True:
            raise ValueError("coverage-limited builds must forbid out-of-coverage reuse")

    @classmethod
    def from_query(
        cls,
        kernel: FiniteKernel[StateT, Any],
        query: QuerySpec[StateT],
        *,
        state_cap: int = 50_000,
    ) -> "BuildCoverage[StateT]":
        states = transition_closure(
            kernel,
            query.initial_distribution,
            state_cap=state_cap,
        )
        return cls(
            initial_support_sha256=canonical_sha256(query.initial_distribution),
            covered_states=states,
            covered_state_ids=tuple(
                sorted(object_id(state, "state") for state in states)
            ),
        )

    @property
    def covered_state_count(self) -> int:
        return len(self.covered_state_ids)

    def descriptor(self) -> dict[str, object]:
        """Return the frozen four-field descriptor bound into ``build_id``."""

        return {
            "mode": self.mode,
            "initial_support_sha256": self.initial_support_sha256,
            "covered_state_count": self.covered_state_count,
            "reuse_outside_coverage_forbidden": (
                self.reuse_outside_coverage_forbidden
            ),
        }

    def validate_query_coverage(self, query: QuerySpec[StateT]) -> None:
        """Reject a candidate query with positive support outside this build."""

        covered = set(self.covered_states)
        missing = _ordered_states(
            state
            for probability, state in query.initial_distribution
            if probability > 0 and state not in covered
        )
        if missing:
            missing_ids = tuple(object_id(state, "state") for state in missing)
            raise QueryOutsideBuildCoverageError(
                "candidate query support lies outside cached build coverage; "
                f"rebuild required for state IDs {missing_ids!r}"
            )


@dataclass(frozen=True, slots=True)
class SuiteBuildCoverage(Generic[StateT]):
    """Immutable coverage certificate for a declared reusable query suite.

    ``declared_support_set_sha256`` hashes the canonically ordered set of
    positive-support states.  It does not hash query probability masses or the
    order in which queries were supplied.  ``covered_states`` is then the full
    all-action/all-positive-outcome transition closure of that support union.
    """

    declared_support_set_sha256: str
    declared_support_states: tuple[StateT, ...]
    declared_support_state_ids: tuple[str, ...]
    covered_states: tuple[StateT, ...]
    covered_state_ids: tuple[str, ...]
    exact_state_cap: int

    mode: str = "suite_support_union_transition_closure"
    admissible_query_support_rule: str = (
        "positive_support_subset_of_covered_states"
    )
    reuse_outside_coverage_forbidden: bool = True

    def __post_init__(self) -> None:
        declared = _ordered_states(self.declared_support_states)
        if (
            not declared
            or declared != self.declared_support_states
            or len(set(declared)) != len(declared)
        ):
            raise ValueError(
                "declared support states must be nonempty, unique, and "
                "canonically ordered"
            )
        expected_declared_ids = tuple(
            sorted(object_id(state, "state") for state in declared)
        )
        if self.declared_support_state_ids != expected_declared_ids:
            raise ValueError(
                "declared support state IDs do not match the declared support set"
            )
        expected_support_digest = canonical_sha256(declared)
        if self.declared_support_set_sha256 != expected_support_digest:
            raise ValueError(
                "declared-support-set digest does not match the canonical support set"
            )

        covered = _ordered_states(self.covered_states)
        if covered != self.covered_states or len(set(covered)) != len(covered):
            raise ValueError("covered states must be unique and canonically ordered")
        expected_covered_ids = tuple(
            sorted(object_id(state, "state") for state in covered)
        )
        if self.covered_state_ids != expected_covered_ids:
            raise ValueError("covered state IDs do not match the covered states")
        if not set(declared).issubset(covered):
            raise ValueError("declared support must be contained in build coverage")

        if self.exact_state_cap <= 0:
            raise ValueError("suite build exact state cap must be positive")
        if len(covered) > self.exact_state_cap:
            raise ValueError("covered states exceed the recorded exact state cap")
        if self.mode != "suite_support_union_transition_closure":
            raise ValueError("unsupported suite build-coverage mode")
        if (
            self.admissible_query_support_rule
            != "positive_support_subset_of_covered_states"
        ):
            raise ValueError("unsupported suite query-admissibility rule")
        if self.reuse_outside_coverage_forbidden is not True:
            raise ValueError("suite builds must forbid out-of-coverage reuse")

    @classmethod
    def from_queries(
        cls,
        kernel: FiniteKernel[StateT, Any],
        queries: Iterable[QuerySpec[StateT]],
        *,
        state_cap: int = 50_000,
    ) -> "SuiteBuildCoverage[StateT]":
        """Build exact closure coverage for the union of suite supports."""

        if state_cap <= 0:
            raise ValueError("suite build exact state cap must be positive")
        suite = tuple(queries)
        if not suite:
            raise ValueError("suite build coverage requires at least one query")

        declared_support = _ordered_states(
            {
                state
                for query in suite
                for probability, state in query.initial_distribution
                if Fraction(probability) > 0
            }
        )
        if not declared_support:
            raise ValueError(
                "suite build coverage requires nonempty positive-probability support"
            )
        if len(declared_support) > state_cap:
            raise RuntimeError(
                "RAPM transition closure exceeded the exact state cap"
            )

        states = transition_closure(
            kernel,
            ((Fraction(1), state) for state in declared_support),
            state_cap=state_cap,
        )
        return cls(
            declared_support_set_sha256=canonical_sha256(declared_support),
            declared_support_states=declared_support,
            declared_support_state_ids=tuple(
                sorted(object_id(state, "state") for state in declared_support)
            ),
            covered_states=states,
            covered_state_ids=tuple(
                sorted(object_id(state, "state") for state in states)
            ),
            exact_state_cap=state_cap,
        )

    @property
    def declared_support_state_count(self) -> int:
        return len(self.declared_support_state_ids)

    @property
    def covered_state_count(self) -> int:
        return len(self.covered_state_ids)

    def descriptor(self) -> dict[str, object]:
        """Return every suite-coverage field that must enter ``build_id``."""

        return {
            "mode": self.mode,
            "declared_support_set_sha256": self.declared_support_set_sha256,
            "declared_support_state_count": self.declared_support_state_count,
            "covered_state_count": self.covered_state_count,
            "exact_state_cap": self.exact_state_cap,
            "admissible_query_support_rule": self.admissible_query_support_rule,
            "reuse_outside_coverage_forbidden": (
                self.reuse_outside_coverage_forbidden
            ),
        }

    def validate_query_coverage(self, query: QuerySpec[StateT]) -> None:
        """Reject a query whose positive support is outside suite coverage."""

        covered = set(self.covered_states)
        missing = _ordered_states(
            state
            for probability, state in query.initial_distribution
            if Fraction(probability) > 0 and state not in covered
        )
        if missing:
            missing_ids = tuple(object_id(state, "state") for state in missing)
            raise QueryOutsideBuildCoverageError(
                "candidate query support lies outside cached suite build coverage; "
                f"rebuild required for state IDs {missing_ids!r}"
            )


def validate_query_coverage(
    coverage: BuildCoverage[StateT] | SuiteBuildCoverage[StateT],
    query: QuerySpec[StateT],
) -> None:
    """Validate a query against either immutable coverage contract."""

    coverage.validate_query_coverage(query)


__all__ = [
    "BuildCoverage",
    "QueryOutsideBuildCoverageError",
    "SuiteBuildCoverage",
    "transition_closure",
    "validate_query_coverage",
]
