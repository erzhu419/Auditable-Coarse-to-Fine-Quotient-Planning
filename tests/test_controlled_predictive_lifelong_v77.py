"""Synthetic update semantics, without simulator or future target observations."""
from collections import Counter
import json
from pathlib import Path

import numpy as np
import pytest

from acfqp.science.controlled_predictive_lifelong_v77 import Knowledge, POLICIES


ROOT = Path(__file__).resolve().parents[1]
LEDGER = Counter()
LOW = [1] + [0] * 15
HIGH = [8] + [0] * 15


def records(stop):
    result = []
    for episode in range(stop):
        for policy in POLICIES:
            for sample in range(32):
                high = episode >= 5 and sample >= 16
                result.append(dict(board=HIGH if high else LOW, horizon=30 + sample % 2,
                    policy=policy, target=[float(high), float(high), float(not high)], episode=episode))
    return result


@pytest.fixture(scope="module", autouse=True)
def retain_work(request):
    yield
    path = ROOT / "reports/controlled_predictive_lifelong_v77.core_checks.json"
    payload = json.loads(path.read_text()) if path.exists() else {"attempts": []}
    payload["attempts"].append(dict(test_module=__file__, session_failures=request.session.testsfailed,
        scope="Two synthetic afterstates with 32 samples per policy per synthetic episode.",
        ground_calls=0, main_campaign_calls=0, **LEDGER))
    path.write_text(json.dumps(payload, indent=2) + "\n")


@pytest.fixture(scope="module")
def initialized():
    modes, log = Knowledge.initialize(records(5))
    LEDGER.update(log["counts"])
    return {name: model.to_payload() for name, model in modes.items()}


@pytest.fixture(scope="module")
def accepted(initialized):
    model = Knowledge.from_payload(initialized["REVISED"])
    log = model.update(records(10), 5)
    LEDGER.update(log["counts"])
    return model.to_payload(), log


def test_frozen_and_fixed_statistics_are_isolated_and_holdout_never_trains(initialized):
    frozen = Knowledge.from_payload(initialized["FROZEN"])
    fixed = Knowledge.from_payload(initialized["FIXED"])
    old_trees = fixed.to_payload()["trees"]
    observations = records(10)
    for row in observations:
        if row["episode"] % 5 == 4:
            row["target"] = [100.0, 1.0, 0.0]
    frozen_log = frozen.update(observations, 5)
    fixed_log = fixed.update(observations, 5)
    LEDGER.update(frozen_log["counts"])
    LEDGER.update(fixed_log["counts"])
    assert frozen.trees == old_trees
    assert not frozen_log["counts"].get("training_rows_read", 0)
    np.testing.assert_array_equal(frozen.predict_many([LOW, HIGH], 30),
                                  np.broadcast_to([0, 0, 1], (2, 3, 3)))
    # Four old training episodes, then four half-low/half-high episodes.
    np.testing.assert_allclose(fixed.predict_many([LOW, HIGH], 30),
                               np.broadcast_to([0.25, 0.25, 0.75], (2, 3, 3)))
    for policy in POLICIES:
        for key in ("left", "right", "feature", "threshold"):
            assert fixed.trees[policy][key] == old_trees[policy][key]
        assert fixed.trees[policy]["samples"] == [256]


def test_revision_accepts_improvement_and_rejects_equal_new_holdout_error(accepted):
    payload, accepted_log = accepted
    assert all(log["accepted"] and log["structure_changed"]
               for log in accepted_log["policies"].values())
    assert all(log["validation_mse"]["new"]["candidate"] == 0
               for log in accepted_log["policies"].values())
    model = Knowledge.from_payload(payload)
    log = model.update(records(15), 10)
    LEDGER.update(log["counts"])
    assert all(not item["accepted"] for item in log["policies"].values())
    assert log["counts"]["proposals_rejected"] == 3
    assert all(item["validation_mse"]["new"]["candidate"] ==
               item["validation_mse"]["new"]["incumbent"] == 0
               for item in log["policies"].values())


def test_json_reload_preserves_policy_paired_components_and_checkpoint(accepted):
    payload, _ = accepted
    model = Knowledge.from_payload(payload)
    restored = Knowledge.from_payload(json.loads(json.dumps(model.to_payload())))
    values = model.predict_many([LOW, HIGH], 31)
    np.testing.assert_array_equal(values, restored.predict_many([LOW, HIGH], 31))
    np.testing.assert_array_equal(values[:, 0], [[0, 0, 1], [1, 1, 0]])
    assert np.all(values[:, :, 1] + values[:, :, 2] <= 1)
    assert restored.predict_many([], 30).shape == (0, 3, 3)
    assert restored.checkpoint == 10
    with pytest.raises(ValueError, match="previous_checkpoint"):
        restored.update(records(15), 5)
