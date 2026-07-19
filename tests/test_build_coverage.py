from fractions import Fraction

import pytest

from acfqp.artifacts import canonical_sha256, object_id
from acfqp.build_coverage import (
    BuildCoverage,
    QueryOutsideBuildCoverageError,
    SuiteBuildCoverage,
    validate_query_coverage,
)
from acfqp.core import Outcome, QuerySpec


class _BranchKernel:
    """Tiny kernel whose closure requires following both actions."""

    horizon = 3
    registered_reward_features: tuple[str, ...] = ()
    registered_goals = ("default",)

    def reward_upper_bound(self, horizon, raw_weights, goal):
        return Fraction(1)

    def initial_distribution(self):
        return ((Fraction(1), "a"),)

    def actions(self, state):
        return {
            "a": ("left", "right"),
            "b": ("right",),
            "m": ("finish",),
            "n": ("finish",),
            "t": (),
        }[state]

    def step(self, state, action):
        successor = {
            ("a", "left"): "m",
            ("a", "right"): "n",
            ("b", "right"): "n",
            ("m", "finish"): "t",
            ("n", "finish"): "t",
        }[(state, action)]
        return (Outcome(Fraction(1), successor, terminal=successor == "t"),)

    def is_terminal(self, state):
        return state == "t"


def _query(*weighted_states: tuple[Fraction, str]) -> QuerySpec[str]:
    return QuerySpec(
        tuple(weighted_states),
        horizon=2,
        reward_weights=(),
        goal="default",
        delta=Fraction(1, 20),
    )


def test_suite_coverage_digest_is_a_canonical_support_set_identity() -> None:
    kernel = _BranchKernel()
    first = _query((Fraction(1, 4), "a"), (Fraction(3, 4), "b"))
    reordered_and_reweighted = _query(
        (Fraction(2, 5), "b"), (Fraction(3, 5), "a")
    )
    extra = _query((Fraction(1), "m"))

    coverage = SuiteBuildCoverage.from_queries(
        kernel, (first, extra), state_cap=5
    )
    equivalent = SuiteBuildCoverage.from_queries(
        kernel, (extra, reordered_and_reweighted), state_cap=5
    )

    assert coverage.declared_support_states == ("a", "b", "m")
    assert coverage.declared_support_set_sha256 == canonical_sha256(("a", "b", "m"))
    assert coverage.declared_support_set_sha256 == (
        equivalent.declared_support_set_sha256
    )
    assert coverage.descriptor() == equivalent.descriptor()
    assert object_id(coverage.descriptor(), "build") == object_id(
        equivalent.descriptor(), "build"
    )


def test_suite_coverage_closes_union_under_every_action_and_binds_descriptor() -> None:
    kernel = _BranchKernel()
    coverage = SuiteBuildCoverage.from_queries(
        kernel,
        (
            _query((Fraction(1), "a")),
            _query((Fraction(1), "b")),
        ),
        state_cap=5,
    )

    # Both a-actions are required to discover m and n; their continuations add t.
    assert coverage.covered_states == ("a", "b", "m", "n", "t")
    assert coverage.declared_support_state_count == 2
    assert coverage.covered_state_count == 5
    assert coverage.descriptor() == {
        "mode": "suite_support_union_transition_closure",
        "declared_support_set_sha256": coverage.declared_support_set_sha256,
        "declared_support_state_count": 2,
        "covered_state_count": 5,
        "exact_state_cap": 5,
        "admissible_query_support_rule": (
            "positive_support_subset_of_covered_states"
        ),
        "reuse_outside_coverage_forbidden": True,
    }

    # Admissibility is closure containment, not membership in the declared roots.
    validate_query_coverage(coverage, _query((Fraction(1), "n")))
    with pytest.raises(QueryOutsideBuildCoverageError, match="rebuild required"):
        validate_query_coverage(coverage, _query((Fraction(1), "outside")))


def test_suite_coverage_enforces_and_records_the_exact_state_cap() -> None:
    kernel = _BranchKernel()
    suite = (_query((Fraction(1), "a")), _query((Fraction(1), "b")))

    exact = SuiteBuildCoverage.from_queries(kernel, suite, state_cap=5)
    assert exact.exact_state_cap == 5

    with pytest.raises(RuntimeError, match="exceeded the exact state cap"):
        SuiteBuildCoverage.from_queries(kernel, suite, state_cap=4)
    with pytest.raises(RuntimeError, match="exceeded the exact state cap"):
        SuiteBuildCoverage.from_queries(
            kernel,
            (_query((Fraction(1, 2), "a"), (Fraction(1, 2), "b")),),
            state_cap=1,
        )
    with pytest.raises(ValueError, match="at least one query"):
        SuiteBuildCoverage.from_queries(kernel, (), state_cap=5)


def test_phase05_build_coverage_keeps_mass_sensitive_identity_and_descriptor() -> None:
    kernel = _BranchKernel()
    first = _query((Fraction(1, 4), "a"), (Fraction(3, 4), "b"))
    changed = _query((Fraction(1, 2), "a"), (Fraction(1, 2), "b"))

    first_coverage = BuildCoverage.from_query(kernel, first, state_cap=5)
    changed_coverage = BuildCoverage.from_query(kernel, changed, state_cap=5)

    assert first_coverage.covered_states == changed_coverage.covered_states
    assert first_coverage.initial_support_sha256 != (
        changed_coverage.initial_support_sha256
    )
    assert first_coverage.descriptor() == {
        "mode": "query_support_transition_closure",
        "initial_support_sha256": first_coverage.initial_support_sha256,
        "covered_state_count": 5,
        "reuse_outside_coverage_forbidden": True,
    }
