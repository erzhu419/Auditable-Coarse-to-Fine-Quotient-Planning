"""Analytical small-graph tests: no environment transitions or training."""
import networkx as nx
import numpy as np
import pytest
import torch

from acfqp.science.lmta_structure_v45 import (
    exact_one_step_score, initial_features, mean_adjacency,
    one_step_readout, spread_summary, weighted_adjacency,
)


def asymmetric_graph():
    graph = nx.DiGraph()
    graph.add_nodes_from(range(5))
    graph.add_edges_from([(0, 1), (0, 2), (3, 2), (2, 3)])
    return graph


def test_weighted_edges_use_outgoing_orientation_and_target_indegree():
    graph = asymmetric_graph()
    matrix = weighted_adjacency(graph)
    assert matrix.dtype == torch.float64
    expected = torch.eye(5, dtype=torch.float64)
    expected[0, 1] = 1.
    expected[0, 2] = .5
    expected[3, 2] = .5
    expected[2, 3] = 1.
    torch.testing.assert_close(matrix, expected, rtol=0, atol=0)
    # The two children of node 0 have different indegrees; source normalization
    # or reversing the edge direction cannot produce this analytical score.
    np.testing.assert_array_equal(exact_one_step_score(graph), [1.5, 0., 1., .5, 0.])


def test_constant_baseline_and_candidate_score_recovery_include_isolated_node():
    graph = asymmetric_graph()
    features = initial_features(5)
    assert features.dtype == torch.float64 and features.shape == (5, 5)
    baseline = mean_adjacency(graph)
    candidate = weighted_adjacency(graph)
    torch.testing.assert_close(baseline @ features, features, rtol=0, atol=1e-15)
    messages = candidate @ features
    np.testing.assert_allclose(one_step_readout(messages).numpy(),
                               exact_one_step_score(graph), rtol=0, atol=1e-15)
    # A sink and an isolated node retain their own feature without spurious spread.
    torch.testing.assert_close(messages[1], features[1], rtol=0, atol=0)
    torch.testing.assert_close(messages[4], features[4], rtol=0, atol=0)
    assert spread_summary(baseline @ features)['max_coordinate_row_range'] < 1e-15
    assert spread_summary(messages)['max_coordinate_row_range'] == 1.5


def test_node_relabeling_permutes_messages_and_scores_without_changing_rule():
    graph = asymmetric_graph()
    permutation = np.array([3, 0, 4, 1, 2])
    relabeled = nx.relabel_nodes(graph, dict(enumerate(permutation)))
    old_matrix, new_matrix = weighted_adjacency(graph), weighted_adjacency(relabeled)
    torch.testing.assert_close(new_matrix[permutation[:, None], permutation], old_matrix,
                               rtol=0, atol=0)
    np.testing.assert_array_equal(exact_one_step_score(relabeled)[permutation],
                                  exact_one_step_score(graph))
    old_message = old_matrix @ initial_features(5)
    new_message = new_matrix @ initial_features(5)
    torch.testing.assert_close(new_message[permutation], old_message, rtol=0, atol=0)


def test_spread_summary_uses_unit_floor_and_reports_q_range():
    assert spread_summary(torch.tensor([.1, .3], dtype=torch.float64)) == pytest.approx(
        dict(max_coordinate_row_range=.2, max_abs=.3, scaled_row_range=.2, q_range=.2))
    summary = spread_summary(torch.tensor([[1., -4.], [3., -2.]], dtype=torch.float64))
    assert summary == dict(max_coordinate_row_range=2., max_abs=4., scaled_row_range=.5)
