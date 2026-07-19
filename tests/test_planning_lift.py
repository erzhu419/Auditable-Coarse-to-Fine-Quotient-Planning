from __future__ import annotations

from fractions import Fraction

import pytest

from acfqp.abstraction import Partition
from acfqp.core import Outcome, QuerySpec
from acfqp.planning import (
    FiniteHorizonPolicy,
    SemanticKernelView,
    evaluate_semantic_policy,
    lift_semantic_policy,
    lift_semantic_policy_decisions,
    solve_ground_action_frontier,
    solve_ground_pareto,
)


class MixedActionKernel:
    horizon = 1

    def initial_distribution(self):
        return ((Fraction(1), "start"),)

    def actions(self, state):
        return ("a", "b") if state == "start" else ()

    def step(self, state, action):
        assert state == "start"
        if action == "a":
            return (
                Outcome(Fraction(1, 2), "done", (("score", Fraction(0)),), terminal=True),
                Outcome(Fraction(1, 2), "failure", failure=True, terminal=True),
            )
        if action == "b":
            return (
                Outcome(Fraction(1, 2), "done", (("score", Fraction(0)),), terminal=True),
                Outcome(Fraction(1, 2), "done", (("score", Fraction(2)),), terminal=True),
            )
        raise AssertionError(action)

    def is_terminal(self, state):
        return state in {"done", "failure"}


class MixedAdapter:
    def __init__(self):
        self.concretize_calls = 0

    def labels(self, kernel, state):
        return ("mix",) if state == "start" else ()

    def concretize(self, kernel, state, label):
        assert label == "mix"
        self.concretize_calls += 1
        # Duplicate primitive actions are intentional: the view must first
        # coalesce this to a uniform distribution over a and b.
        return (
            (Fraction(1, 4), "a"),
            (Fraction(1, 4), "a"),
            (Fraction(1, 2), "b"),
        )


class SingletonAdapter:
    def labels(self, kernel, state):
        return ("only-a",) if state == "start" else ()

    def concretize(self, kernel, state, label):
        return ((Fraction(1), "a"),)


def mixed_query(*, delta=Fraction(1, 20)):
    return QuerySpec.from_state(
        "start",
        horizon=1,
        reward_weights=(("score", Fraction(1)),),
        delta=delta,
    )


def mixed_partition():
    return Partition.from_mapping(
        {"start": "root", "done": "done", "failure": "failure"}
    )


def test_semantic_kernel_integrates_fixed_concretizer_and_coalesces_outcomes():
    adapter = MixedAdapter()
    view = SemanticKernelView(MixedActionKernel(), adapter)

    assert view.concretizer_distribution("start", "mix") == (
        (Fraction(1, 2), "a"),
        (Fraction(1, 2), "b"),
    )
    outcomes = view.step("start", "mix")
    assert {
        (
            outcome.next_state,
            outcome.reward_features,
            outcome.failure,
            outcome.terminal,
        ): outcome.probability
        for outcome in outcomes
    } == {
        ("done", (("score", Fraction(0)),), False, True): Fraction(1, 2),
        ("done", (("score", Fraction(2)),), False, True): Fraction(1, 4),
        ("failure", (), True, True): Fraction(1, 4),
    }
    assert view.step("start", "mix") is outcomes
    assert adapter.concretize_calls == 1


def test_stochastic_semantic_policy_is_evaluated_exactly_without_fake_ground_policy():
    kernel = MixedActionKernel()
    adapter = MixedAdapter()
    query = mixed_query()
    partition = mixed_partition()
    abstract_policy = FiniteHorizonPolicy.from_mapping({(1, "root"): "mix"})

    decisions = lift_semantic_policy_decisions(
        kernel, query, partition, abstract_policy, adapter
    )
    assert decisions.action("start", 1) == "mix"

    evaluation = evaluate_semantic_policy(
        kernel, query, partition, abstract_policy, adapter
    )
    assert evaluation.expected_reward == Fraction(1, 2)
    assert evaluation.failure_probability == Fraction(1, 4)

    lift = lift_semantic_policy(kernel, query, partition, abstract_policy, adapter)
    assert lift.evaluation == evaluation
    assert lift.lifted_semantic_policy.action("start", 1) == "mix"
    assert lift.deterministic_ground_policy is None
    assert not lift.has_deterministic_ground_materialization


def test_singleton_concretizer_can_materialize_a_deterministic_ground_policy():
    kernel = MixedActionKernel()
    query = mixed_query()
    abstract_policy = FiniteHorizonPolicy.from_mapping({(1, "root"): "only-a"})

    lift = lift_semantic_policy(
        kernel,
        query,
        mixed_partition(),
        abstract_policy,
        SingletonAdapter(),
    )

    assert lift.deterministic_ground_policy is not None
    assert lift.deterministic_ground_policy.action("start", 1) == "a"
    assert lift.evaluation.expected_reward == 0
    assert lift.evaluation.failure_probability == Fraction(1, 2)


class ChoiceKernel:
    horizon = 1

    def initial_distribution(self):
        return ((Fraction(1), "start"),)

    def actions(self, state):
        return ("safe", "risky") if state == "start" else ()

    def step(self, state, action):
        if state != "start":
            raise AssertionError(state)
        if action == "safe":
            return (
                Outcome(Fraction(1), "done", (("score", Fraction(1)),), terminal=True),
            )
        if action == "risky":
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
        raise AssertionError(action)

    def is_terminal(self, state):
        return state in {"done", "failure"}


def choice_query(delta):
    return QuerySpec.from_state(
        "start",
        horizon=1,
        reward_weights=(("score", Fraction(1)),),
        delta=delta,
    )


def test_ground_oracle_accepts_required_decisions_and_action_frontier_helper():
    kernel = ChoiceKernel()
    strict = choice_query(Fraction(0))
    forced_risky = solve_ground_pareto(
        kernel,
        strict,
        required_decisions={(1, "start"): "risky"},
    )
    assert len(forced_risky.frontier) == 1
    assert forced_risky.frontier[0].expected_reward == 2
    assert forced_risky.frontier[0].failure_probability == Fraction(1, 10)
    assert forced_risky.selected is None

    permissive = choice_query(Fraction(1, 10))
    forced_safe = solve_ground_action_frontier(
        kernel,
        permissive,
        state="start",
        remaining=1,
        action="safe",
    )
    assert len(forced_safe.frontier) == 1
    assert forced_safe.selected is not None
    assert forced_safe.selected.expected_reward == 1
    assert forced_safe.selected.policy.action("start", 1) == "safe"


@pytest.mark.parametrize(
    ("requirements", "message"),
    [
        ({(1, "start"): "missing"}, "unavailable"),
        ({(2, "start"): "safe"}, "outside"),
        ({(1, "done"): "safe"}, "not reachable"),
        ({"malformed": "safe"}, "must be"),
    ],
)
def test_ground_oracle_rejects_invalid_required_decisions(requirements, message):
    with pytest.raises(ValueError, match=message):
        solve_ground_pareto(
            ChoiceKernel(),
            choice_query(Fraction(1, 10)),
            required_decisions=requirements,
        )
