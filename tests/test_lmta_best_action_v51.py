"""Best-set semantics, masked gradients and one tiny original-NodeQ update."""
from collections import Counter
import json
import math
from pathlib import Path
from time import perf_counter
from unittest.mock import patch

import numpy as np
import pytest
import torch

from acfqp.science import lmta_best_action_v51 as objective
from acfqp.science import lmta_models_v43 as models


@pytest.fixture(scope="module", autouse=True)
def development_accounting(request):
    started = perf_counter()
    old_threads = torch.get_num_threads()
    torch.set_num_threads(1)
    counts = Counter()
    original_forward = models.NodeQ.forward
    original_loss = objective.best_action_loss
    original_step = models.optimizer_step
    before_failures = request.session.testsfailed

    def forward(model, x, *args, **kwargs):
        states = x.shape[0] if x.ndim == 3 else 1
        counts["model_forward_state_presentations"] += states
        counts["gradient_enabled_model_states" if torch.is_grad_enabled()
               else "no_grad_model_states"] += states
        return original_forward(model, x, *args, **kwargs)

    def loss(logits, *args, **kwargs):
        counts["loss_state_presentations"] += logits.shape[0] if logits.ndim == 2 else 1
        return original_loss(logits, *args, **kwargs)

    def step(*args, **kwargs):
        result = original_step(*args, **kwargs)
        counts["optimizer_gradient_steps"] += 1
        counts["backward_calls"] += 1
        return result

    with patch.object(models.NodeQ, "forward", forward), \
         patch.object(objective, "best_action_loss", loss), \
         patch.object(models, "optimizer_step", step):
        yield counts
    torch.set_num_threads(old_threads)
    path = Path(__file__).resolve().parents[1] / "reports/lmta_best_action_v51.development_checks.json"
    result = json.loads(path.read_text()) if path.exists() else {"attempts": []}
    result["attempts"].append({"test_module": "tests/test_lmta_best_action_v51.py",
        "new_failures": request.session.testsfailed - before_failures,
        "environment_counters": {}, "computation_counters": dict(counts),
        "wall_seconds": perf_counter() - started,
        "scope": "CPU best-set objective/gradient checks and one two-state original-NodeQ optimizer update; no environments."})
    path.write_text(json.dumps(result, indent=2) + "\n")


def test_probability_mass_of_all_best_actions_and_state_mean():
    logits = torch.log(torch.tensor([[2., 3., 5.], [4., 1., 1.]], dtype=torch.float64))
    legal = torch.ones_like(logits, dtype=torch.bool)
    best = torch.tensor([[True, True, False], [True, False, False]])
    actual = objective.best_action_loss(logits, best, legal)
    assert actual.item() == pytest.approx((math.log(2.) + math.log(1.5)) / 2.)
    first = objective.objective_metrics(logits[0].numpy(), best[0].numpy(), legal[0].numpy())
    assert first == pytest.approx({"best_set_nll": math.log(2.), "best_set_probability": .5,
                                 "best_set_size": 2})
    uniform_best_cross_entropy = -(math.log(.2) + math.log(.3)) / 2.
    assert first["best_set_nll"] != pytest.approx(uniform_best_cross_entropy)


def test_illegal_highest_logit_has_no_loss_effect_or_gradient(development_accounting):
    logits = torch.tensor([999., math.log(2.), math.log(3.)],
                          dtype=torch.float64, requires_grad=True)
    legal = torch.tensor([False, True, True])
    best = torch.tensor([False, True, False])
    loss = objective.best_action_loss(logits, best, legal)
    assert loss.item() == pytest.approx(-math.log(.4))
    loss.backward()
    development_accounting["backward_calls"] += 1
    torch.testing.assert_close(logits.grad, torch.tensor([0., -.6, .6], dtype=torch.float64))
    diagnostic = objective.objective_metrics(logits.detach().numpy(), best.numpy(), legal.numpy())
    assert diagnostic["best_set_probability"] == pytest.approx(.4)


def test_entire_legal_set_optimal_has_zero_loss_and_gradient(development_accounting):
    logits = torch.tensor([[999., -3., 2.], [1., -4., 999.]], requires_grad=True)
    legal = torch.tensor([[False, True, True], [True, True, False]])
    loss = objective.best_action_loss(logits, legal, legal)
    assert loss.item() == 0.
    loss.backward()
    development_accounting["backward_calls"] += 1
    assert torch.count_nonzero(logits.grad) == 0
    for row, mask in zip(logits.detach().numpy(), legal.numpy()):
        assert objective.objective_metrics(row, mask, mask) == {
            "best_set_nll": 0., "best_set_probability": 1., "best_set_size": 2}


def test_best_mask_uses_float64_near_tie_threshold_in_one_or_two_dimensions():
    targets = np.asarray([[1., 1. - .5e-9, 1. - 2e-9, 99.],
                          [3., 2., 3., 99.]], dtype=np.float64)
    legal = np.asarray([[True, True, True, False], [True, True, True, False]])
    assert np.unique(targets[0, :3].astype(np.float32)).size == 1
    actual = objective.teacher_best_mask(targets, legal)
    assert actual.dtype == bool and actual.shape == targets.shape
    np.testing.assert_array_equal(actual, [[True, True, False, False],
                                           [True, False, True, False]])
    np.testing.assert_array_equal(objective.teacher_best_mask(targets[0], legal[0]), actual[0])


def test_extreme_logits_stay_finite_and_one_real_nodeq_update(development_accounting):
    extreme = torch.tensor([[10000., -10000., 99999.],
                            [-10000., 10000., 99999.]], requires_grad=True)
    legal = torch.tensor([[True, True, False], [True, True, False]])
    best = torch.tensor([[False, True, False], [False, True, False]])
    loss = objective.best_action_loss(extreme, best, legal)
    assert torch.isfinite(loss) and loss.item() == 10000.
    loss.backward()
    development_accounting["backward_calls"] += 1
    assert torch.isfinite(extreme.grad).all()
    for row, mask, available, expected in zip(extreme.detach().numpy(), best.numpy(),
                                            legal.numpy(), [20000., 0.]):
        measured = objective.objective_metrics(row, mask, available)
        assert measured["best_set_nll"] == expected
        assert math.isfinite(measured["best_set_probability"])

    torch.manual_seed(51041)
    model = models.NodeQ()
    x = torch.tensor([[[1., 0., 0., 1., 1.], [0., 1., 0., 1., 1.], [1., 0., 0., 1., 1.]],
                      [[0., 1., 0., .5, .5], [1., 0., 0., .5, .5], [1., 0., 0., .5, .5]]])
    a = torch.tensor([[[1., .5, 0.], [0., 1., 1.], [0., 0., 1.]],
                      [[1., 0., 1.], [0., 1., 0.], [0., .5, 1.]]])
    legal = torch.tensor([[True, False, True], [False, True, True]])
    best = torch.tensor([[True, False, False], [False, False, True]])
    before = {name: value.detach().clone() for name, value in model.state_dict().items()}
    optimizer = torch.optim.Adam(model.parameters(), lr=.001, weight_decay=.00001)
    loss = objective.best_action_loss(model(x, a), best, legal)
    development_accounting["supervised_training_state_presentations"] += 2
    models.optimizer_step(optimizer, loss, model.parameters())
    assert torch.isfinite(loss)
    assert any(not torch.equal(before[name], value) for name, value in model.state_dict().items())
