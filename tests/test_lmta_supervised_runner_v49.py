"""Three bounded checks of the V49 supervised objective and model execution."""
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


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("run_lmta_supervised_v49", ROOT / "scripts/run_lmta_supervised_v49.py")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


@pytest.fixture(scope="module", autouse=True)
def development_accounting(request):
    old_threads = torch.get_num_threads()
    torch.set_num_threads(1)
    started = perf_counter()
    counts = Counter()
    original_forward = runner.NodeQ.forward
    original_step = runner.optimizer_step
    before_failures = request.session.testsfailed

    def forward(model, x, *args, **kwargs):
        states = x.shape[0] if x.ndim == 3 else 1
        counts["model_forward_state_presentations"] += states
        counts["gradient_enabled_model_states" if torch.is_grad_enabled()
               else "no_grad_model_states"] += states
        return original_forward(model, x, *args, **kwargs)

    def step(*args, **kwargs):
        result = original_step(*args, **kwargs)
        counts["optimizer_gradient_steps"] += 1
        counts["backward_calls"] += 1
        return result

    with patch.object(runner.NodeQ, "forward", forward), patch.object(runner, "optimizer_step", step):
        yield counts
    torch.set_num_threads(old_threads)
    path = ROOT / "reports/lmta_supervised_v49.development_checks.json"
    result = json.loads(path.read_text()) if path.exists() else {"attempts": []}
    result["attempts"].append({"test_module": "tests/test_lmta_supervised_runner_v49.py",
        "new_failures": request.session.testsfailed - before_failures,
        "environment_counters": {}, "computation_counters": dict(counts),
        "wall_seconds": perf_counter() - started,
        "scope": "CPU objective, batch/individual forward parity, one tiny optimizer update; no environment calls."})
    path.write_text(json.dumps(result, indent=2) + "\n")


def small_batch():
    graphs = [nx.DiGraph(), nx.DiGraph()]
    for graph in graphs:
        graph.add_nodes_from(range(4))
    graphs[0].add_edges_from([(0, 1), (0, 2), (3, 2)])
    graphs[1].add_edges_from([(0, 3), (1, 3), (2, 0)])
    x = torch.as_tensor(np.stack([
        runner.features_from_state(np.asarray([0, 1, 0, 2]), 7, 53),
        runner.features_from_state(np.asarray([1, 0, 2, 0]), 3, 12)]))
    adjacency = torch.stack([runner.weighted_adjacency(graph, "cpu", torch.float32)
                             for graph in graphs])
    return x, adjacency


def test_loss_averages_legal_nodes_within_each_state_and_masks_gradients(development_accounting):
    predictions = torch.tensor([[1., 3., 99.], [2., 99., 99.]], dtype=torch.float64, requires_grad=True)
    targets = torch.zeros_like(predictions)
    legal = torch.tensor([[True, True, False], [True, False, False]])
    loss = runner.supervised_loss(predictions, targets, legal)
    development_accounting["supervised_loss_state_presentations"] += 2
    assert loss.item() == 4.5  # ((1 + 9) / 2 + 4 / 1) / 2
    loss.backward()
    development_accounting["backward_calls"] += 1
    torch.testing.assert_close(predictions.grad,
        torch.tensor([[.5, 1.5, 0.], [2., 0., 0.]], dtype=torch.float64), rtol=0, atol=0)


def test_batch_with_different_graph_operators_matches_individual_forwards():
    torch.manual_seed(49041)
    model = runner.NodeQ().eval()
    x, adjacency = small_batch()
    assert not torch.equal(adjacency[0], adjacency[1])
    with torch.no_grad():
        batch = model(x, adjacency)
        individual = torch.stack([model(x[i], adjacency[i]) for i in range(2)])
    torch.testing.assert_close(batch, individual, rtol=1e-6, atol=1e-7)


def test_one_update_changes_nodeq_and_no_grad_evaluation_preserves_parameters(development_accounting):
    torch.manual_seed(49042)
    model = runner.NodeQ()
    x, adjacency = small_batch()
    targets = torch.tensor([[1., 0., 2., 0.], [0., 2., 0., 1.]])
    legal = torch.tensor([[True, False, True, False], [False, True, False, True]])
    optimizer = torch.optim.Adam(model.parameters(), lr=.001, weight_decay=.00001)
    before = {name: value.clone() for name, value in model.state_dict().items()}
    loss = runner.supervised_loss(model(x, adjacency), targets, legal)
    development_accounting["supervised_loss_state_presentations"] += 2
    runner.optimizer_step(optimizer, loss, model.parameters())
    after = {name: value.clone() for name, value in model.state_dict().items()}
    assert any(not torch.equal(before[name], value) for name, value in after.items())
    model.eval()
    with torch.no_grad():
        predictions = model(x, adjacency)
    assert not predictions.requires_grad and torch.isfinite(predictions).all()
    for name, value in model.state_dict().items():
        torch.testing.assert_close(after[name], value, rtol=0, atol=0)
