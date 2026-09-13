"""Teacher parity and hand-computed label/ranking checks; account all sampling."""
from collections import Counter
import json
from pathlib import Path
from unittest.mock import patch

import networkx as nx
import numpy as np
import pytest

from acfqp.science.lmta_aim_v43 import AIMEnvironment
from acfqp.science.lmta_heuristics_v44 import AverageScoreAgent
from acfqp.science.lmta_supervised_v49 import (
    collect_episode, features_from_state, ranking_metrics, score_targets)


@pytest.fixture(scope="module", autouse=True)
def development_accounting(request):
    counters = {}
    original = AIMEnvironment._count

    def measured(env, phase, **increments):
        counters.setdefault(phase, Counter()).update(increments)
        return original(env, phase, **increments)

    before_failures = request.session.testsfailed
    with patch.object(AIMEnvironment, "_count", measured):
        yield
    path = Path(__file__).resolve().parents[1] / "reports/lmta_supervised_v49.development_checks.json"
    existing = json.loads(path.read_text()) if path.exists() else {"attempts": []}
    existing["attempts"].append({
        "test_module": "tests/test_lmta_supervised_v49.py",
        "new_failures": request.session.testsfailed - before_failures,
        "environment_counters": {phase: dict(values) for phase, values in counters.items()},
        "scope": "Every physical select and finish_day in collector, reference, and feature checks; no optimizer."})
    path.write_text(json.dumps(existing, indent=2) + "\n")


def small_graph():
    graph = nx.DiGraph()
    graph.add_nodes_from(range(7))
    graph.add_edges_from([(0, 3), (0, 4), (0, 5), (1, 0), (1, 6), (2, 6), (2, 4)])
    return graph


def test_collector_matches_teacher_states_actions_rewards_and_physical_counts():
    graph = small_graph()
    samples, event = collect_episode(graph, 49001, 49002, budget=5, horizon=3)
    teacher = AverageScoreAgent(graph, budget=5, horizon=3, seed=0)
    env = AIMEnvironment(graph, budget=5, horizon=3, seed=49002)
    reference_samples = []
    original = teacher.choose

    def record(reference_env):
        reference_samples.append({"statuses": reference_env.statuses.copy(),
            "day": reference_env.day, "remaining_budget": reference_env.remaining_budget})
        return original(reference_env)

    with patch.object(teacher, "choose", record):
        reference = teacher.run_episode(env, training=False)
    assert event["graph_id"] == 49001 and event["environment_seed"] == 49002
    assert event["raw_return"] == reference["raw_return"]
    assert event["counters"] == env.counters["evaluation"]
    assert event["day_history"] == reference["day_history"]
    assert event["selected_nodes"] == [day["selected"] for day in reference["actions"]]
    assert event["selected_nodes"][0] == [0, 2]
    assert event["state_count"] == len(samples) == len(reference_samples)
    assert event["label_calls"] == len(samples)
    assert event["label_node_evaluations"] == len(samples) * len(graph)
    assert event["wall_seconds"] >= 0
    for sample, expected in zip(samples, reference_samples):
        np.testing.assert_array_equal(sample["statuses"], expected["statuses"])
        assert sample["day"] == expected["day"]
        assert sample["remaining_budget"] == expected["remaining_budget"]
        assert sample["statuses"].dtype == np.int8
        assert sample["targets"].dtype == np.float64
    assert samples[0]["statuses"][0] == 0 and samples[1]["statuses"][0] == 1


def test_targets_change_with_inactive_successors_and_keep_full_indegrees():
    graph = small_graph()
    statuses = np.zeros(len(graph), dtype=np.int8)
    np.testing.assert_array_equal(score_targets(graph, statuses), [2.5, 1.5, 1., 0., 0., 0., 0.])
    statuses[0] = 1
    np.testing.assert_array_equal(score_targets(graph, statuses), [2.5, .5, 1., 0., 0., 0., 0.])
    statuses[4] = 2
    np.testing.assert_array_equal(score_targets(graph, statuses), [2., .5, .5, 0., 0., 0., 0.])


def test_features_match_environment_after_selection_and_day_transition():
    env = AIMEnvironment(small_graph(), budget=5, horizon=3, seed=49003)
    for step in range(3):
        actual = features_from_state(env.statuses, env.remaining_days,
            env.remaining_budget, budget=5, horizon=3)
        np.testing.assert_array_equal(actual, env.features())
        assert actual.dtype == np.float32
        if step == 0:
            env.select(0, phase="feature_check")
        elif step == 1:
            env.finish_day(phase="feature_check")


def test_masked_ranking_rejects_illegal_high_prediction():
    result = ranking_metrics([999., 0., 4.], [999., 3., 1.], [False, True, True])
    assert result["predicted_node"] == 2 and result["teacher_node"] == 1
    assert result["score_regret"] == 2. and result["relative_regret"] == 2. / 3.
    assert result["optimal"] is False
    assert result["pairwise_correct"] == 0 and result["pairwise_pairs"] == 1


def test_all_pairs_exclude_teacher_ties_and_give_prediction_ties_half_credit():
    result = ranking_metrics([4., 4., 1., 0.], [3., 1., 1., 0.], [True] * 4)
    assert result["predicted_node"] == result["teacher_node"] == 0
    assert result["pairwise_correct"] == 4.5 and result["pairwise_pairs"] == 5
    assert result["optimal"] is True and result["score_regret"] == 0.


@pytest.mark.parametrize("targets", [[0., 0., 0.], [2., 2., 2.]])
def test_teacher_ties_and_zero_scores_have_zero_regret(targets):
    result = ranking_metrics([0., 1., 2.], targets, [True] * 3)
    assert result["predicted_node"] == 2 and result["teacher_node"] == 0
    assert result["score_regret"] == result["relative_regret"] == 0.
    assert result["optimal"] is True
    assert result["pairwise_pairs"] == result["pairwise_correct"] == 0
