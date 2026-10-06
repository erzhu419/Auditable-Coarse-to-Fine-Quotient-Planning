"""Same-sample horizon treatment and policy-bound fitting, with zero ground calls."""
from collections import Counter
import json
from pathlib import Path

import numpy as np
import pytest

from acfqp.science import controlled_predictive_target_horizon_v80 as module


ROOT = Path(__file__).resolve().parents[1]
LEDGER = Counter()
LOW = [1] + [0] * 15
HIGH = [8] + [0] * 15


@pytest.fixture(scope="module", autouse=True)
def retain_work(request):
    yield
    path = ROOT / "reports/controlled_predictive_target_horizon_v80.core_checks.json"
    payload = json.loads(path.read_text()) if path.exists() else {"attempts": []}
    payload["attempts"].append(dict(test_module=__file__, session_failures=request.session.testsfailed,
        scope="Synthetic retained trajectories and paired multi-output fits only.",
        ground_calls=0, main_campaign_calls=0, **LEDGER))
    path.write_text(json.dumps(payload, indent=2) + "\n")


def game(length=33, status="LOST"):
    return dict(status=status, steps=[dict(
        afterstate=LOW if index % 2 == 0 else HIGH, score=4 * (index + 1),
        status=status if index == length - 1 and status in ("WON", "LOST") else "ACTIVE",
    ) for index in range(length)])


def test_shared_anchor_rows_exclude_anchor_reward_and_include_terminal_once():
    source = game()
    rows, log = module.paired_targets(source, "GREEDY", 7)
    assert [row["anchor_step"] for row in rows] == list(range(0, 33, 4))
    assert len(rows) == log["paired_records"] == log["terminal_records"] == 9
    assert log["short_terminal_records"] == 8
    assert rows[0] == dict(board=LOW, episode=7, anchor_step=0, policy="GREEDY",
        short_target=[sum(step["score"] for step in source["steps"][1:31]) / 2048, 0, 0],
        terminal_target=[sum(step["score"] for step in source["steps"][1:]) / 2048, 1, 0])
    assert rows[-1]["short_target"] == rows[-1]["terminal_target"] == [0, 1, 0]
    assert all(set(row) == {"board", "episode", "anchor_step", "policy",
                           "short_target", "terminal_target"} for row in rows)


def test_branch_anchor_only_and_early_success_close_both_windows():
    source = game(length=3, status="WON")
    rows, log = module.paired_targets(source, "SPACE", 8, anchor_only=True)
    assert len(rows) == log["candidate_anchors"] == 1
    assert rows[0]["short_target"] == rows[0]["terminal_target"] == [20 / 2048, 0, 1]
    assert log["short_success_records"] == log["terminal_success_records"] == 1
    all_rows, _ = module.paired_targets(source, "SPACE", 8)
    assert [row["anchor_step"] for row in all_rows] == [0, 2]


def test_incomplete_terminal_observation_discards_both_targets_together():
    # Its first short window is fully observed, but the paired terminal target is not.
    rows, log = module.paired_targets(game(status="CUTOFF"), "SNAKE", 9)
    assert rows == []
    assert log["discarded_game"] is True
    assert log["discard_reason"] == "no_observed_terminal"
    assert log["discarded_records"] == log["candidate_anchors"] == 9
    assert log["paired_records"] == 0


@pytest.fixture(scope="module")
def fitted():
    rows = []
    for episode in range(6):
        for policy_index, policy in enumerate(module.POLICIES):
            for sample in range(32):
                high = sample >= 16
                offset = 1000 if episode >= 4 else 0
                rows.append(dict(board=HIGH if high else LOW, episode=episode,
                    anchor_step=sample, policy=policy,
                    short_target=[policy_index + float(high) + offset, 0, 0],
                    terminal_target=[policy_index + 3 + float(high) + offset, 1, 0]))
    seen = []
    original_fit = module._fit

    def record_fit(x, y, counts):
        seen.append((x.copy(), y.copy()))
        return original_fit(x, y, counts)

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(module, "_fit", record_fit)
        models, logs = {}, {}
        for scope in module.TARGET_SCOPES:
            models[scope], logs[scope] = module.fit_model(rows, 5, scope)
            LEDGER.update(logs[scope]["counts"])
    return models, logs, seen


def test_same_order_features_and_chronological_holdout_isolation(fitted):
    models, logs, seen = fitted
    for scope in module.TARGET_SCOPES:
        log = logs[scope]
        assert log["input_records"] == 576
        assert log["prefix_records"] == 480
        assert log["future_records_excluded"] == log["heldout_records"] == 96
        assert log["training_records"] == log["counts"]["fit_rows"] == 384
        assert log["counts"]["tree_fits"] == 3
        assert models[scope].checkpoint == 5
        for policy in module.POLICIES:
            assert log["policies"][policy]["training_rows"] == 128
            assert log["policies"][policy]["heldout_rows"] == 32
            assert log["policies"][policy]["heldout_mse_components"][0] == 1000000
    for policy_index in range(3):
        short_x, short_y = seen[policy_index]
        terminal_x, terminal_y = seen[policy_index + 3]
        np.testing.assert_array_equal(short_x, terminal_x)
        assert short_x.shape == (128, 37)
        np.testing.assert_array_equal(short_x[:, -1], 30 / 32)
        np.testing.assert_array_equal(terminal_y[:, 0] - short_y[:, 0], 3)
        assert np.max(terminal_y[:, 0]) < 1000


def test_payload_and_predictions_preserve_scope_and_policy_vector_binding(fitted):
    models, _, _ = fitted
    for scope, model in models.items():
        payload = json.loads(json.dumps(model.to_payload()))
        restored = module.ConsequenceModel.from_payload(payload)
        assert payload["target_scope"] == restored.target_scope == scope
        assert payload["target_semantics"] == module.TARGET_SEMANTICS[scope]
        assert payload["feature_context_horizon"] == 30
        expected = np.asarray([[[policy + rank + (3 if scope == "TERMINAL" else 0),
                                 int(scope == "TERMINAL"), 0]
                                for policy in range(3)] for rank in (0, 1)])
        np.testing.assert_array_equal(model.predict_many([LOW, HIGH], 30), expected)
        np.testing.assert_array_equal(restored.predict_many([LOW, HIGH], 30), expected)
        assert restored.predict_many([], 30).shape == (0, 3, 3)
        with pytest.raises(ValueError, match="feature context horizon=30"):
            restored.predict_many([LOW], 31)
