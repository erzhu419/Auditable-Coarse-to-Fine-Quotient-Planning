"""Synthetic checks of V78 model isolation and the decision acceptance rule."""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path

import numpy as np
import pytest

from acfqp.science.controlled_predictive_lifelong_v77 import Knowledge, POLICIES
from acfqp.science.controlled_predictive_decision_update_v78 import (
    decision_acceptance, fit_candidate, mse_decision, refresh_fixed,
)


ROOT = Path(__file__).resolve().parents[1]
LEDGER = Counter()
LOW = [1] + [0] * 15
HIGH = [8] + [0] * 15


def records(stop, contaminate_holdout=False):
    result = []
    for episode in range(stop):
        for policy in POLICIES:
            for sample in range(32):
                high = episode >= 5 and sample >= 16
                target = [float(high), float(high), float(not high)]
                if contaminate_holdout and episode % 5 == 4:
                    target = [100.0, 1.0, 0.0]
                result.append(dict(board=HIGH if high else LOW, horizon=30 + sample % 2,
                    policy=policy, target=target, episode=episode))
    return result


@pytest.fixture(scope="module", autouse=True)
def retain_work(request):
    yield
    path = ROOT / "reports/controlled_predictive_decision_update_v78.checks.json"
    payload = json.loads(path.read_text()) if path.exists() else {"attempts": []}
    payload["attempts"].append(dict(test_module=__file__,
        session_failures=request.session.testsfailed,
        scope="Synthetic low/high afterstates and paired utility rows only.",
        ground_calls=0, main_campaign_calls=0, **LEDGER))
    path.write_text(json.dumps(payload, indent=2) + "\n")


@pytest.fixture(scope="module")
def models():
    old, old_log = fit_candidate(records(5, True), 5)
    candidate, candidate_log = fit_candidate(records(10, True), 10)
    LEDGER.update(old_log["counts"])
    LEDGER.update(candidate_log["counts"])
    return old.to_payload(), candidate.to_payload()


def paired_rows():
    return [dict(stratum=stratum, query=query,
                 incumbent_utility=1.0, candidate_utility=1.0 + (stratum == "new"))
            for stratum in ("old", "new") for query in ("reward", "risk_goal")]


def test_candidate_and_fixed_exclude_holdout_and_do_not_modify_inputs(models):
    old = Knowledge.from_payload(models[0])
    candidate = Knowledge.from_payload(models[1])
    original = deepcopy(old.to_payload())
    observations = records(10, True)
    before_records = deepcopy(observations)
    fixed, log = refresh_fixed(old, observations, 10)
    LEDGER.update(log["counts"])
    assert observations == before_records
    assert old.to_payload() == original
    np.testing.assert_array_equal(candidate.predict_many([LOW, HIGH], 30),
        np.repeat(np.array([[[0, 0, 1]], [[1, 1, 0]]]), 3, axis=1))
    np.testing.assert_allclose(fixed.predict_many([LOW, HIGH], 30),
        np.broadcast_to([0.25, 0.25, 0.75], (2, 3, 3)))
    assert fixed.checkpoint == 10
    assert not any(row["structure_changed"] for row in log["policies"].values())


def test_whole_incumbent_mse_comparison_performs_no_hidden_refresh(models):
    old = Knowledge.from_payload(models[0])
    candidate = Knowledge.from_payload(models[1])
    originals = deepcopy((old.to_payload(), candidate.to_payload()))
    log = mse_decision(old, candidate, records(10), 5)
    LEDGER.update(log["counts"])
    assert (old.to_payload(), candidate.to_payload()) == originals
    assert log["accepted"]
    assert log["validation_mse"]["old"] == dict(incumbent=0.0, candidate=0.0)
    assert log["validation_mse"]["new"] == dict(incumbent=0.5, candidate=0.0)
    assert log["validation_rows"] == dict(old=96, new=96)


def test_prediction_improvement_can_fail_query_decision_rule(models):
    log = mse_decision(Knowledge.from_payload(models[0]),
                       Knowledge.from_payload(models[1]), records(10), 5)
    LEDGER.update(log["counts"])
    pairs = paired_rows()
    pairs[2]["candidate_utility"] = 0.75
    decision = decision_acceptance(pairs)
    assert log["accepted"] and not decision["accepted"]
    assert decision["strata"]["new"]["reward"]["mean_delta"] == -0.25
    assert decision["strata"]["new"]["risk_goal"]["mean_delta"] == 1.0


def test_decision_requires_old_new_evidence_and_strict_new_improvement():
    pairs = paired_rows()
    accepted = decision_acceptance(pairs)
    assert accepted["accepted"] and accepted["pairs"] == 4
    missing = decision_acceptance(pairs[1:])
    assert not missing["accepted"] and not missing["complete_strata"]
    pairs[0]["candidate_utility"] = 0.99
    assert not decision_acceptance(pairs)["accepted"]
    for row in pairs:
        row["candidate_utility"] = row["incumbent_utility"]
    assert not decision_acceptance(pairs)["accepted"]


def test_json_reload_keeps_policy_vectors_and_model_checkpoint(models):
    candidate = Knowledge.from_payload(models[1])
    restored = Knowledge.from_payload(json.loads(json.dumps(candidate.to_payload())))
    predicted = candidate.predict_many([LOW, HIGH], 31)
    np.testing.assert_array_equal(predicted, restored.predict_many([LOW, HIGH], 31))
    assert np.all(predicted[:, :, 1] + predicted[:, :, 2] <= 1)
    assert restored.checkpoint == 10 and restored.mode == "CANDIDATE"
    with pytest.raises(ValueError, match="completed episode prefix"):
        fit_candidate(records(10), 5)
