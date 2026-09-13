"""Initialization parity and one tiny supervised update; no environments."""
from collections import Counter
import importlib.util
import json
from pathlib import Path
from time import perf_counter
from unittest.mock import patch

import networkx as nx
import numpy as np
import pytest
import torch

from acfqp.science.lmta_models_v43 import NodeQ
from acfqp.science.lmta_readout_v50 import FirstMessageNodeQ
from acfqp.science.lmta_structure_v45 import weighted_adjacency
from acfqp.science.lmta_supervised_v49 import features_from_state, score_targets


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("readout_v50_objective",
    ROOT / "scripts/run_lmta_supervised_v49.py")
objective = importlib.util.module_from_spec(spec)
spec.loader.exec_module(objective)


@pytest.fixture(scope="module", autouse=True)
def development_accounting(request):
    started = perf_counter()
    old_threads = torch.get_num_threads()
    torch.set_num_threads(1)
    counts = Counter()
    original_base_forward = NodeQ.forward
    original_candidate_forward = FirstMessageNodeQ.forward
    original_step = objective.optimizer_step
    before_failures = request.session.testsfailed

    def measured_forward(original, model, x, a):
        states = x.shape[0] if x.ndim == 3 else 1
        counts["model_forward_state_presentations"] += states
        counts["gradient_enabled_model_states" if torch.is_grad_enabled()
               else "no_grad_model_states"] += states
        return original(model, x, a)

    def step(*args, **kwargs):
        result = original_step(*args, **kwargs)
        counts["optimizer_gradient_steps"] += 1
        counts["backward_calls"] += 1
        return result

    with patch.object(NodeQ, "forward", lambda model, x, a:
                      measured_forward(original_base_forward, model, x, a)), \
         patch.object(FirstMessageNodeQ, "forward", lambda model, x, a:
                      measured_forward(original_candidate_forward, model, x, a)), \
         patch.object(objective, "optimizer_step", step):
        yield counts
    torch.set_num_threads(old_threads)
    path = ROOT / "reports/lmta_readout_v50.development_checks.json"
    result = json.loads(path.read_text()) if path.exists() else {"attempts": []}
    result["attempts"].append({"test_module": "tests/test_lmta_readout_v50.py",
        "new_failures": request.session.testsfailed - before_failures,
        "environment_counters": {}, "computation_counters": dict(counts),
        "wall_seconds": perf_counter() - started,
        "scope": "CPU initial-parameter/Q parity, one two-state gradient update, and analytic first-message checks; no environment calls."})
    path.write_text(json.dumps(result, indent=2) + "\n")


def small_graph():
    graph = nx.DiGraph()
    graph.add_nodes_from(range(4))
    graph.add_edges_from([(0, 1), (0, 2), (3, 2), (2, 3)])
    return graph


def small_batch():
    graph = small_graph()
    statuses = np.asarray([[0, 1, 0, 2], [1, 0, 2, 0]], dtype=np.int8)
    x = torch.as_tensor(np.stack([features_from_state(s, 7, 53) for s in statuses]))
    a = weighted_adjacency(graph, "cpu", torch.float32).expand(2, -1, -1)
    targets = torch.as_tensor(np.stack([score_targets(graph, s) for s in statuses]),
                              dtype=torch.float32)
    return x, a, targets, torch.as_tensor(statuses == 0)


def test_zero_branch_preserves_old_parameters_rng_and_initial_batch_q():
    torch.manual_seed(50041)
    baseline = NodeQ().eval()
    baseline_rng = torch.random.get_rng_state().clone()
    torch.manual_seed(50041)
    candidate = FirstMessageNodeQ().eval()
    assert torch.equal(torch.random.get_rng_state(), baseline_rng)
    old = baseline.state_dict()
    new = candidate.state_dict()
    assert set(new) - set(old) == {"message_weight", "message_bias"}
    for name, value in old.items():
        assert torch.equal(value, new[name])
    assert candidate.message_weight.shape == (5,)
    assert candidate.message_bias.shape == ()
    assert not torch.count_nonzero(candidate.message_weight)
    assert not torch.count_nonzero(candidate.message_bias)
    assert sum(p.numel() for p in candidate.parameters()) == sum(p.numel() for p in baseline.parameters()) + 6
    x, a, _, _ = small_batch()
    with torch.no_grad():
        assert torch.equal(candidate(x, a), baseline(x, a))


def test_existing_legal_node_loss_updates_new_branch(development_accounting):
    torch.manual_seed(50042)
    model = FirstMessageNodeQ()
    x, a, targets, legal = small_batch()
    optimizer = torch.optim.Adam(model.parameters(), lr=.001, weight_decay=.00001)
    predictions = model(x, a)
    predictions.retain_grad()
    loss = objective.supervised_loss(predictions, targets, legal)
    development_accounting["supervised_loss_state_presentations"] += 2
    expected = torch.stack([(predictions[i, legal[i]] - targets[i, legal[i]]).square().mean()
                            for i in range(2)]).mean()
    torch.testing.assert_close(loss, expected, rtol=0, atol=0)
    before_weight = model.message_weight.detach().clone()
    before_bias = model.message_bias.detach().clone()
    objective.optimizer_step(optimizer, loss, model.parameters())
    assert torch.count_nonzero(predictions.grad[~legal]) == 0
    assert torch.isfinite(model.message_weight.grad).all()
    assert torch.isfinite(model.message_bias.grad)
    assert not torch.equal(before_weight, model.message_weight)
    assert not torch.equal(before_bias, model.message_bias)


@pytest.mark.parametrize("statuses", [[0, 0, 0, 0], [0, 1, 0, 2]])
def test_first_message_contains_current_score_on_legal_nodes(statuses):
    graph = small_graph()
    statuses = np.asarray(statuses, dtype=np.int8)
    x = torch.as_tensor(features_from_state(statuses, 7, 53), dtype=torch.float64)
    first = weighted_adjacency(graph, "cpu", torch.float64) @ x
    legal = statuses == 0
    actual = first[:, 0].numpy()[legal] - 1.
    np.testing.assert_allclose(actual, score_targets(graph, statuses)[legal],
                               rtol=0, atol=1e-12)
