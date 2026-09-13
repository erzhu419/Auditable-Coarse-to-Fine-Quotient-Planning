"""Interface and portable-tree checks; synthetic labels are not science evidence."""
from collections import Counter
import json
from pathlib import Path
import subprocess
import sys

import pytest

from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics
from acfqp.science.controlled_predictive_decision_rule_v76 import (
    BASE_FEATURE_NAMES, FEATURE_NAMES, choose_action, features, fit,
    predict_probability, query_features, score_actions,
)


ROOT = Path(__file__).resolve().parents[1]
BOARD = (0, 0, 0, 1) + (0,) * 12
LEDGER = dict(feature_work=Counter(), synthetic_fit_calls=0, synthetic_training_rows=0,
              cold_worker_calls=0)


@pytest.fixture(scope="module", autouse=True)
def retain_work(request):
    yield
    path = ROOT / "reports/controlled_predictive_decision_rule_v76.core_checks.json"
    payload = json.loads(path.read_text()) if path.exists() else {"attempts": []}
    payload["attempts"].append(dict(test_module=__file__, session_failures=request.session.testsfailed,
        scope="One fixed legal-action board and 32 synthetic query labels; interface validation only.",
        source_campaign_training_calls=0, target_calls=0, ground_calls=0, **LEDGER))
    path.write_text(json.dumps(payload, indent=2) + "\n")


@pytest.fixture(scope="module")
def toy():
    rule = LearnedDynamics.from_payload(json.loads((ROOT /
        "reports/controlled_predictive_composition_v69/learned_rule.json").read_text()))
    action_features = features(BOARD, rule, LEDGER["feature_work"])
    base = action_features["LEFT"]
    records = [dict(features=query_features(base, {"failure_penalty": risk}), label=label)
               for risk, label in ((0, 1), (5, 0)) for _ in range(16)]
    model = fit(records)
    LEDGER["synthetic_fit_calls"] += 1
    LEDGER["synthetic_training_rows"] += len(records)
    return rule, action_features, model


def test_feature_extraction_excludes_illegal_actions_and_never_spawns(toy):
    _, action_features, model = toy
    assert set(action_features) == {"LEFT", "DOWN"}
    assert all(len(base) == len(BASE_FEATURE_NAMES) == 30 for base in action_features.values())
    assert LEDGER["feature_work"]["learned_swipe_calls"] == 4
    assert LEDGER["feature_work"]["learned_spawn_outcomes"] == 0
    assert choose_action(model, action_features, {"failure_penalty": 0}) == "DOWN"
    assert choose_action(model, {}, {"failure_penalty": 0}) is None


def test_query_features_affect_prediction_and_positive_weight_scaling_is_preserved(toy):
    _, action_features, model = toy
    base = action_features["LEFT"]
    low = query_features(base, {"failure_penalty": 0})
    high = query_features(base, {"failure_penalty": 5})
    assert len(low) == len(FEATURE_NAMES) == 41
    assert low != high
    assert predict_probability(model, low) == 1
    assert predict_probability(model, high) == 0
    first = {"reward_weight": 1, "failure_penalty": 5, "goal_bonus": 1}
    scaled = {"reward_weight": 0.4, "failure_penalty": 2, "goal_bonus": 0.4}
    assert query_features(base, first) == query_features(base, scaled)
    assert score_actions(model, action_features, first) == score_actions(model, action_features, scaled)


def test_json_tree_runs_identically_in_a_cold_standard_library_only_process(toy, tmp_path):
    _, action_features, model = toy
    model_path, input_path = tmp_path / "tree.json", tmp_path / "inputs.json"
    model_path.write_text(json.dumps(model))
    query = dict(reward_weight=1, failure_penalty=0, goal_bonus=0)
    input_path.write_text(json.dumps(dict(action_features=action_features, query=query)))
    code = """import importlib.util,json,sys
from pathlib import Path
spec=importlib.util.spec_from_file_location('portable_v76',sys.argv[1])
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
model=json.loads(Path(sys.argv[2]).read_text())
data=json.loads(Path(sys.argv[3]).read_text())
scores=module.score_actions(model,data['action_features'],data['query'])
choice=module.choose_action(model,data['action_features'],data['query'])
forbidden=[name for name in sys.modules if name.startswith(('sklearn','numpy','acfqp.domains'))]
print(json.dumps(dict(scores=scores,choice=choice,forbidden_imports=forbidden)))
"""
    LEDGER["cold_worker_calls"] += 1
    result = subprocess.run([sys.executable, "-c", code, str(ROOT /
        "src/acfqp/science/controlled_predictive_decision_rule_v76.py"),
        str(model_path), str(input_path)], capture_output=True, text=True, check=True)
    actual = json.loads(result.stdout)
    assert not result.stderr
    assert actual["scores"] == score_actions(model, action_features, query)
    assert actual["choice"] == choose_action(model, action_features, query)
    assert actual["forbidden_imports"] == []
