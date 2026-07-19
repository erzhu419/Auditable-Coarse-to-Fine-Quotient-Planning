from __future__ import annotations

from fractions import Fraction

import pytest

from acfqp.abstraction import Partition, build_quotient_models
from acfqp.core import Outcome, QuerySpec
from acfqp.planning import (
    FiniteHorizonPolicy,
    audit_abstract_policy,
    solve_ground_pareto,
    solve_nominal_pareto,
)
from acfqp.refinement import (
    CEGARStatus,
    Predicate,
    RankedSplitCandidate,
    RefinementBudget,
    RefinementCounters,
    RefinementTracker,
    SplitStatus,
    attempt_split,
    record_ground_fallback,
    refine_once,
)


class RewardRiskKernel:
    horizon = 1

    def initial_distribution(self):
        return ((Fraction(1), "start"),)

    def actions(self, state):
        return ("safe", "risky") if state == "start" else ()

    def step(self, state, action):
        assert state == "start"
        if action == "safe":
            return (
                Outcome(
                    Fraction(1),
                    "done",
                    (("score", Fraction(1)),),
                    terminal=True,
                ),
            )
        return (
            Outcome(
                Fraction(9, 10),
                "done",
                (("score", Fraction(2)),),
                terminal=True,
            ),
            Outcome(
                Fraction(1, 10),
                "failure",
                (("score", Fraction(2)),),
                failure=True,
                terminal=True,
            ),
        )

    def is_terminal(self, state):
        return state in {"done", "failure"}


class AliasingKernel:
    horizon = 1

    def initial_distribution(self):
        return ((Fraction(1), "low"),)

    def actions(self, state):
        return ("act",) if state in {"low", "high"} else ()

    def step(self, state, action):
        assert action == "act"
        if state == "low":
            return (
                Outcome(
                    Fraction(1),
                    "done",
                    (("score", Fraction(1)),),
                    terminal=True,
                ),
            )
        assert state == "high"
        return (
            Outcome(Fraction(9, 10), "done", terminal=True),
            Outcome(
                Fraction(1, 10),
                "failure",
                failure=True,
                terminal=True,
            ),
        )

    def is_terminal(self, state):
        return state in {"done", "failure"}


class MergingPolicyKernel:
    """Two weighted branches later share ``e`` but not ``f``.

    A state-local Pareto recursion drops the locally dominated
    ``e=safe, f=risky`` subpolicy at ``c``.  It is nevertheless the unique
    reward-positive feasible root policy because the much heavier ``d`` branch
    also reaches ``e``.  The exact oracle must therefore choose actions jointly
    over the stage occupancy distribution.
    """

    horizon = 3

    def initial_distribution(self):
        return ((Fraction(1, 10), "s1"), (Fraction(9, 10), "s2"))

    def actions(self, state):
        return {
            "s1": ("go",),
            "s2": ("go",),
            "c": ("mix",),
            "d": ("to_e",),
            "e": ("safe", "risky"),
            "f": ("safe", "risky"),
        }.get(state, ())

    def step(self, state, action):
        if state == "s1" and action == "go":
            return (Outcome(Fraction(1), "c"),)
        if state == "s2" and action == "go":
            return (Outcome(Fraction(1), "d"),)
        if state == "c" and action == "mix":
            return (Outcome(Fraction(1, 2), "e"), Outcome(Fraction(1, 2), "f"))
        if state == "d" and action == "to_e":
            return (Outcome(Fraction(1), "e"),)
        if state in {"e", "f"} and action == "safe":
            return (Outcome(Fraction(1), "done", terminal=True),)
        if state == "e" and action == "risky":
            return (
                Outcome(Fraction(9, 10), "done", (("score", Fraction(10)),), terminal=True),
                Outcome(
                    Fraction(1, 10),
                    "failure",
                    (("score", Fraction(10)),),
                    failure=True,
                    terminal=True,
                ),
            )
        if state == "f" and action == "risky":
            return (
                Outcome(Fraction(4, 5), "done", (("score", Fraction(9)),), terminal=True),
                Outcome(
                    Fraction(1, 5),
                    "failure",
                    (("score", Fraction(9)),),
                    failure=True,
                    terminal=True,
                ),
            )
        raise AssertionError((state, action))

    def is_terminal(self, state):
        return state in {"done", "failure"}


def test_exact_ground_pareto_frontier_and_constraint_selection():
    kernel = RewardRiskKernel()
    query = QuerySpec.from_state(
        "start",
        horizon=1,
        reward_weights=(("score", Fraction(1)),),
        delta=Fraction(0),
    )

    result = solve_ground_pareto(kernel, query)

    assert {(point.expected_reward, point.failure_probability) for point in result.frontier} == {
        (Fraction(1), Fraction(0)),
        (Fraction(2), Fraction(1, 10)),
    }
    assert result.selected is not None
    assert result.selected.policy.action("start", 1) == "safe"
    assert result.selected.expected_reward == 1
    assert result.composed_candidate_count > 0

    normalized = solve_ground_pareto(
        kernel,
        QuerySpec.from_state(
            "start",
            horizon=1,
            reward_weights=(("score", Fraction(1)),),
            delta=Fraction(0),
            normalizer=Fraction(2),
        ),
    )
    assert normalized.selected is not None
    assert normalized.selected.expected_reward == Fraction(1, 2)


def test_ground_oracle_preserves_global_policy_consistency_after_path_merging():
    kernel = MergingPolicyKernel()
    query = QuerySpec(
        kernel.initial_distribution(),
        horizon=3,
        reward_weights=(("score", Fraction(1)),),
        goal="default",
        delta=Fraction(1, 20),
    )

    result = solve_ground_pareto(kernel, query)

    assert {
        (point.expected_reward, point.failure_probability)
        for point in result.frontier
    } == {
        (Fraction(0), Fraction(0)),
        (Fraction(9, 20), Fraction(1, 100)),
        (Fraction(19, 2), Fraction(19, 200)),
        (Fraction(199, 20), Fraction(21, 200)),
    }
    assert result.selected is not None
    assert result.selected.expected_reward == Fraction(9, 20)
    assert result.selected.failure_probability == Fraction(1, 100)
    assert result.selected.policy.action("e", 1) == "safe"
    assert result.selected.policy.action("f", 1) == "risky"

    states = ("s1", "s2", "c", "d", "e", "f", "done", "failure")
    identity = Partition.from_mapping({state: state for state in states})
    nominal_model = build_quotient_models(kernel, states, identity).nominal
    nominal = solve_nominal_pareto(nominal_model, query)
    assert nominal.selected is not None
    assert nominal.selected.expected_reward == Fraction(9, 20)
    assert nominal.selected.failure_probability == Fraction(1, 100)
    assert nominal.selected.policy.action("e", 1) == "safe"
    assert nominal.selected.policy.action("f", 1) == "risky"


def test_nominal_model_is_separate_from_exact_envelope_and_split_certifies():
    kernel = AliasingKernel()
    states = ("low", "high", "done", "failure")
    coarse = Partition.from_cells(
        {
            "ambiguous": ("low", "high"),
            "done": ("done",),
            "failure": ("failure",),
        }
    )
    query = QuerySpec.from_state(
        "low",
        horizon=1,
        reward_weights=(("score", Fraction(1)),),
        delta=Fraction(1, 20),
    )

    models = build_quotient_models(kernel, states, coarse)
    nominal = models.nominal.transition("ambiguous", "act")
    exact = models.envelope.realizations("ambiguous", "act")

    assert nominal.reward_features == (("score", Fraction(1, 2)),)
    assert nominal.failure_probability == Fraction(1, 20)
    assert {realization.failure_probability for realization in exact} == {
        Fraction(0),
        Fraction(1, 10),
    }

    proposal = solve_nominal_pareto(models.nominal, query)
    assert proposal.selected is not None
    coarse_audit = audit_abstract_policy(
        kernel,
        query,
        models.envelope,
        proposal.selected.policy,
    )
    assert coarse_audit.lifted_reward_lower == 0
    assert coarse_audit.lifted_failure_upper == Fraction(1, 10)
    assert not coarse_audit.certified

    risk = {"low": 0, "high": 1, "done": 0, "failure": 1}
    predicate = Predicate("risk", "<=", Fraction(1, 2), lambda state: risk[state])
    tracker = RefinementTracker()
    split = attempt_split(coarse, "ambiguous", predicate, tracker)
    assert split.status is SplitStatus.SPLIT_ACCEPTED
    assert split.false_cell is not None and split.true_cell is not None

    # The identical predicate on a child is rejected via the inherited path.
    duplicate = attempt_split(split.partition, split.true_cell, predicate, tracker)
    assert duplicate.status is SplitStatus.DUPLICATE_PREDICATE

    refined_models = build_quotient_models(kernel, states, split.partition)
    refined_policy = FiniteHorizonPolicy.from_mapping({(1, split.true_cell): "act"})
    # ``risk <= 1/2`` sends low to the true child.
    assert split.partition.cell_of("low") == split.true_cell
    refined_audit = audit_abstract_policy(
        kernel,
        query,
        refined_models.envelope,
        refined_policy,
    )
    assert refined_audit.unrestricted_reward_upper == 1
    assert refined_audit.lifted_reward_lower == 1
    assert refined_audit.lifted_failure_upper == 0
    assert refined_audit.regret_upper == 0
    assert refined_audit.certified


def test_failure_target_cannot_alias_an_ordinary_state():
    kernel = RewardRiskKernel()
    invalid = Partition.from_cells(
        {
            "start": ("start",),
            "terminal": ("done", "failure"),
        }
    )

    with pytest.raises(ValueError, match="failure state must be isolated"):
        build_quotient_models(kernel, ("start", "done", "failure"), invalid)


def test_noop_split_is_rejected():
    partition = Partition.single_cell(("a", "b"))
    predicate = Predicate("constant", "<=", 10, lambda _state: 0)
    result = attempt_split(partition, "root", predicate, RefinementTracker())
    assert result.status is SplitStatus.NO_OP_SPLIT
    assert result.partition == partition


def test_outer_cegar_statuses_and_budget_boundaries_are_normative():
    assert {status.value for status in CEGARStatus} == {
        "CERTIFIED",
        "SPLIT_ACCEPTED",
        "NO_SEPARATING_PREDICATE",
        "ALL_SPLITS_REJECTED",
        "REFINEMENT_BUDGET_EXHAUSTED",
        "RATE_BUDGET_EXHAUSTED",
        "GROUND_FALLBACK",
        "INFEASIBLE_QUERY",
    }
    partition = Partition.single_cell(("a", "b"))
    value = {"a": 0, "b": 1}
    predicate = Predicate("value", "<=", Fraction(1, 2), lambda state: value[state])
    boundary_candidate = RankedSplitCandidate(
        predicate,
        audit_width_reduction=Fraction(1, 5),  # exactly the 20% boundary
        rate_cost=2,
    )
    budget = RefinementBudget(2, 1, Fraction(2), 1, 1)

    infeasible = refine_once(
        partition,
        "root",
        (boundary_candidate,),
        RefinementTracker(),
        budget,
        RefinementCounters(),
        current_audit_width=1,
        witness=("a", "b"),
        query_feasible=False,
    )
    assert infeasible.status is CEGARStatus.INFEASIBLE_QUERY

    certified = refine_once(
        partition,
        "root",
        (boundary_candidate,),
        RefinementTracker(),
        budget,
        RefinementCounters(),
        current_audit_width=1,
        witness=("a", "b"),
        already_certified=True,
    )
    assert certified.status is CEGARStatus.CERTIFIED

    accepted = refine_once(
        partition,
        "root",
        (boundary_candidate,),
        RefinementTracker(),
        budget,
        RefinementCounters(),
        current_audit_width=1,
        witness=("a", "b"),
    )
    assert accepted.status is CEGARStatus.SPLIT_ACCEPTED
    assert accepted.counters == RefinementCounters(2, 1, Fraction(2), 1, 0)

    exhausted = refine_once(
        accepted.partition,
        accepted.split.true_cell,
        (boundary_candidate,),
        RefinementTracker(),
        budget,
        accepted.counters,
        current_audit_width=1,
        witness=("a", "b"),
    )
    assert exhausted.status is CEGARStatus.REFINEMENT_BUDGET_EXHAUSTED

    rate_blocked = refine_once(
        partition,
        "root",
        (RankedSplitCandidate(predicate, Fraction(1), rate_cost=3),),
        RefinementTracker(),
        RefinementBudget(2, 1, 2, 2, 1),
        RefinementCounters(),
        current_audit_width=1,
        witness=("a", "b"),
    )
    assert rate_blocked.status is CEGARStatus.RATE_BUDGET_EXHAUSTED

    rejected = refine_once(
        partition,
        "root",
        (RankedSplitCandidate(predicate, Fraction(19, 100), rate_cost=1),),
        RefinementTracker(),
        RefinementBudget(2, 1, 2, 2, 1),
        RefinementCounters(),
        current_audit_width=1,
        witness=("a", "b"),
    )
    assert rejected.status is CEGARStatus.ALL_SPLITS_REJECTED

    no_separator = refine_once(
        partition,
        "root",
        (),
        RefinementTracker(),
        RefinementBudget.phase05(),
        RefinementCounters(),
        current_audit_width=1,
        witness=("a", "b"),
    )
    assert no_separator.status is CEGARStatus.NO_SEPARATING_PREDICATE

    fallback = record_ground_fallback(
        partition,
        RefinementBudget(2, 1, 2, 2, 1),
        RefinementCounters(),
    )
    assert fallback.status is CEGARStatus.GROUND_FALLBACK
    fallback_exhausted = record_ground_fallback(
        partition,
        RefinementBudget(2, 1, 2, 2, 1),
        fallback.counters,
    )
    assert fallback_exhausted.status is CEGARStatus.REFINEMENT_BUDGET_EXHAUSTED
