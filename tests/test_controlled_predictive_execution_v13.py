"""History isolation, hard episode budgets, and weighted execution accounting."""

from collections import Counter

import pytest

from acfqp.science.controlled_predictive_2048_v1 import build_development_closure
from acfqp.science.controlled_predictive_execution_v13 import (
    ExactEnvironment, evaluate_execution, evaluate_frozen_policy,
)
from acfqp.science.controlled_predictive_incremental_v13 import PlannerState
from acfqp.science.controlled_predictive_partial_v12 import RowSampleProvider
from acfqp.science.controlled_predictive_quotient_v1 import Query


def board(rank):
    return (0,) * 5 + (rank,) + (0,) * 10


R = (3, board(1))
A, B = (2, board(1)), (2, board(2))
K = (1, board(3))
CUTOFF = (0, board(1))
WON = (0, board(11))
Q = Query(1, 1, 2)


class FixedProvider:
    def __init__(self, rows):
        self.rows = rows
        self.calls = []
        self.work_counts = Counter()
        self.provider_seconds = 0.0

    def sample(self, key, action):
        self.calls.append((key, action))
        self.work_counts.update(row_requests=1, physical_draws=256)
        return self.rows[key, action]


def nodes(trace):
    if "action" in trace:
        yield trace
        for edge in trace["children"]:
            yield from nodes(edge["node"])


def test_history_diamond_keeps_different_models_at_same_board_and_weights_cost(monkeypatch):
    warm = PlannerState(R, {"q": Q})
    warm.observe_row(R, "DOWN", ((.25, A, 0.), (.75, B, 0.)))
    warm.observe_row(A, "LEFT", ((1., K, 0.),))
    warm.observe_row(B, "LEFT", ((1., K, 0.),))
    warm.solve("q")
    original_rows, original_profiles = dict(warm.rows), dict(warm.profiles)

    # Script only the acquisition scheduling, leaving real caches, max-L action
    # selection, branch cloning, budget logic and exact recursion in operation.
    def selected(self, key, query):
        sequence = [(K, "LEFT")] if key == A else [(K, "RIGHT"), (B, "RIGHT")] if key == B else []
        return next((pair for pair in sequence if pair not in self.rows), None)

    monkeypatch.setattr(PlannerState, "select_row", selected)
    sampled = {(K, "LEFT"): ((1., CUTOFF, 0.),),
               (K, "RIGHT"): ((1., WON, 0.),),
               (B, "RIGHT"): ((1., K, 0.),)}
    provider = FixedProvider(sampled)
    environment = ExactEnvironment({R: "ACTIVE", A: "ACTIVE", B: "ACTIVE", K: "ACTIVE",
                                    CUTOFF: "CUTOFF", WON: "WON"}, {**warm.rows, **sampled})
    result = evaluate_execution(warm, provider, "q", environment, total_row_cap=7)
    leaves = [node for node in nodes(result["trace"]) if node["key"][0] == 1]
    assert [node["action"] for node in leaves] == ["LEFT", "RIGHT"]
    assert result["root_metrics"] == {"reward": 0., "failure": 0., "success": .75, "value": 1.5}
    assert result["deployment"]["expected_additional_rows"] == 1.75
    assert result["deployment"]["maximum_additional_rows"] == 2
    assert result["deployment"]["expected_total_rows"] == 4.75
    assert result["deployment"]["maximum_total_rows"] == 5
    assert result["physical_audit"]["provider_counts"]["physical_draws"] == 768
    assert result["deployment"]["expected_suffix_work_counts"]["provider_physical_draws"] == 448
    assert result["deployment"]["expected_suffix_work_counts"]["rows_acquired"] == 1.75
    # Only the necessary initial query clone is a deployment cost.
    assert result["deployment"]["expected_suffix_work_counts"]["branch_clones"] == 1
    assert result["physical_audit"]["history_work_counts"]["counterfactual_branch_clones"] == 4
    assert result["deployment"]["expected_seconds_by_stage"]["query_initialization_clone"] == result["initial_query_clone_seconds"]
    assert warm.rows == original_rows and warm.profiles == original_profiles
    assert provider.calls == [(K, "LEFT"), (K, "RIGHT"), (B, "RIGHT")]
    for node in nodes(result["trace"]):
        assert node["rows_after"] - node["rows_before"] <= node["quota"]
        assert node["quota"] == (7 - node["rows_before"]) // node["key"][0]
        assert len(node["observed_rows"]) == len(node["requested_rows"])


@pytest.mark.parametrize("mode", ["upfront", "online"])
def test_complete_and_incremental_have_identical_observations_actions_bounds_and_metrics(mode):
    root_board = (1, 1, 3, 4, 5, 6, 7, 8, 9, 3, 4, 5, 6, 7, 8, 9)
    root = (2, root_board)
    closure = build_development_closure(horizon=2, boards={"tiny": root_board})
    environment = ExactEnvironment.from_closure(closure)
    results = []
    for update_mode in ("full_recompute", "incremental"):
        warm = PlannerState(root, {"q": Q, "second": Query(1, .2, 0)}, update_mode=update_mode)
        warm.sample_next(RowSampleProvider(73))
        before_rows, before_work = dict(warm.rows), Counter(warm.work_counts)
        result = evaluate_execution(warm, RowSampleProvider(73), "q", environment,
                                    mode=mode, total_row_cap=5)
        assert warm.rows == before_rows and warm.work_counts == before_work
        assert result["deployment"]["maximum_total_rows"] <= 5
        assert result["deployment"]["expected_total_rows"] <= result["deployment"]["maximum_total_rows"]
        assert result["physical_audit"]["provider_counts"].get("row_requests", 0) >= result["deployment"]["expected_additional_rows"]
        if mode == "upfront":
            assert all(not node["requested_rows"] for node in list(nodes(result["trace"]))[1:])
            assert result["physical_audit"]["history_work_counts"].get("counterfactual_branch_clones", 0) == 0
        results.append(result)
    assert results[0]["trace"] == results[1]["trace"]
    assert results[0]["root_metrics"] == results[1]["root_metrics"]
    assert results[0]["deployment"]["expected_total_rows"] == results[1]["deployment"]["expected_total_rows"]


def test_unseen_execution_board_is_profiled_online_and_uses_fixed_fallback_upfront_at_cap():
    root, known, unseen = (2, board(1)), (1, board(2)), (1, board(3))
    warm = PlannerState(root, {"q": Q})
    for action in ("DOWN", "LEFT", "RIGHT", "UP"):
        warm.observe_row(root, action, ((1., known, 0.),))
        warm.observe_row(known, action, ((1., CUTOFF, 0.),))
    # Exact execution reaches a successor absent from every sampled row.
    environment = ExactEnvironment({root: "ACTIVE", unseen: "ACTIVE", CUTOFF: "CUTOFF"},
                                   {(root, "DOWN"): ((1., unseen, 0.),),
                                    (unseen, "DOWN"): ((1., CUTOFF, 0.),)})
    results = {mode: evaluate_execution(warm, FixedProvider({}), "q", environment,
                                       mode=mode, total_row_cap=8) for mode in ("online", "upfront")}
    online_child = results["online"]["trace"]["children"][0]["node"]
    upfront_child = results["upfront"]["trace"]["children"][0]["node"]
    assert online_child["unresolved"] and online_child["unobserved_action"] and not online_child["fallback"]
    assert online_child["lower"] == -1 and online_child["upper"] == 2
    assert upfront_child["fallback"] and upfront_child["unobserved_action"]
    assert upfront_child["lower"] is None
    assert unseen not in warm.profiles
    for result in results.values():
        assert result["deployment"]["expected_total_rows"] == result["deployment"]["maximum_total_rows"] == 8
        assert not result["physical_audit"]["provider_counts"]


def test_frozen_policy_hand_calculation_preserves_reward_risk_and_event_probabilities():
    root, a, b = (2, board(1)), (1, board(1)), (1, board(2))
    lost = (0, board(2))
    environment = ExactEnvironment({root: "ACTIVE", a: "ACTIVE", b: "ACTIVE", WON: "WON", lost: "LOST"},
        {(root, "DOWN"): ((.25, a, 1.), (.75, b, 2.)),
         (a, "LEFT"): ((1., WON, 3.),), (b, "LEFT"): ((1., lost, 4.),)})
    result = evaluate_frozen_policy(root, Query(1, 2, 3), lambda key: "DOWN" if key == root else "LEFT", environment,
                                   known_rows={(root, "DOWN"), (b, "LEFT")}, known_policy_keys={root, b}, initial_rows=6)
    assert result["root_metrics"] == {"reward": 5.5, "failure": .75, "success": .25, "value": 4.75}
    assert result["deployment"]["expected_events"]["fallback_calls"] == .25
    assert result["deployment"]["event_probabilities"]["fallback_calls"] == .25
    assert result["deployment"]["event_probabilities"]["unobserved_action_executions"] == .25
    assert result["deployment"]["expected_total_rows"] == result["deployment"]["maximum_total_rows"] == 6
    assert result["deployment"]["expected_decisions"] == 2


def test_environment_row_is_read_only_after_the_history_action_has_been_selected():
    root = (1, board(1))
    selected = []
    class OrderedEnvironment(ExactEnvironment):
        def row(self, key, action):
            assert selected == [(key, action)]
            return super().row(key, action)
    environment = OrderedEnvironment({root: "ACTIVE", CUTOFF: "CUTOFF"},
                                     {(root, "DOWN"): ((1., CUTOFF, 0.),)})
    def action(key):
        selected.append((key, "DOWN"))
        return "DOWN"
    result = evaluate_frozen_policy(root, Q, action, environment)
    assert result["root_metrics"]["value"] == 0
    assert result["physical_audit"]["history_work_counts"]["selected_true_row_lookups"] == 1
