"""Mirror weights, episode isolation, exact antisymmetry, and JSON round trips."""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path

import numpy as np
import pytest

from acfqp.science import controlled_predictive_paired_continuation_value_v92 as module


ROOT = Path(__file__).resolve().parents[1]
LEFT = [4, 1, 2, 3, 4, 1, 2, 3, 4, 5, 0, 0, 0, 0, 0, 0]
RIGHT = [1, 1, 2, 3, 4, 1, 2, 3, 4, 5, 0, 0, 0, 0, 0, 0]
LEDGER = Counter()


@pytest.fixture(scope="module", autouse=True)
def retain_work(request):
    yield
    path = ROOT / "reports/controlled_predictive_paired_continuation_value_v92.core_checks.json"
    payload = json.loads(path.read_text()) if path.exists() else {"attempts": []}
    payload["attempts"].append(dict(test_module=__file__, session_failures=request.session.testsfailed,
        scope="Synthetic paired trees and fold models; no environment sampling.",
        sampled_transitions=0, main_campaign_calls=0, **LEDGER))
    path.write_text(json.dumps(payload, indent=2) + "\n")


def records():
    values = {0: [1, .2, -.2], 1: [10, .4, -.4], 2: [3, .6, -.6],
              3: [30, .8, -.8], 4: [999, 999, -999], 6: [-999, -999, 999]}
    return [dict(candidate_board=list(LEFT), reference_board=list(RIGHT),
        candidate_active=True, reference_active=True, query=query, episode=episode,
        target=list(target), weight=1 / 32, step=step, option="SNAKE_4", replica=0)
        for query in module.QUERIES for episode, target in values.items() for step in range(16)]


@pytest.fixture(scope="module")
def models():
    rows = records()
    before = deepcopy(rows)
    models, log = module.fit_models(rows, 6)
    assert rows == before
    LEDGER.update(log["counts"])
    changed = deepcopy(rows)
    for row in changed:
        if row["episode"] not in (1, 3):
            row["target"] = [1e9, -1e9, 1e9]
            row["candidate_board"] = list(RIGHT)
            row["weight"] = 1e9
    unaffected, fit_log = module.PairedContinuation.fit(changed, 6, excluded_fold=0)
    LEDGER.update(fit_log["counts"])
    return models, log, unaffected


def test_mirror_keeps_total_weight_and_preserves_whole_episode_fold_exclusion(models):
    values, log, unchanged = models
    assert log["counts"]["tree_fits"] == 6
    assert values["fold_0"].to_payload() == unchanged.to_payload()
    for query in module.QUERIES:
        assert values["full"].training_episodes[query] == [0, 1, 2, 3]
        assert values["fold_0"].training_episodes[query] == [1, 3]
        assert values["fold_1"].training_episodes[query] == [0, 2]
        fit = log["fits"]["full"]["queries"][query]
        assert fit["training_rows"] == 64 and fit["mirrored_training_rows"] == 128
        assert fit["weight_sum"] == 2
        assert values["full"].predict_pair(LEFT, RIGHT, True, True, query) == pytest.approx([11, .5, -.5])
        assert values["fold_0"].predict_pair(LEFT, RIGHT, True, True, query) == pytest.approx([20, .6, -.6])


def test_pair_features_use_only_current_boards_and_active_flags_and_mirror_exactly():
    rows = records()[:1]
    counts = Counter()
    x = module._pair_array(rows, counts)
    changed = deepcopy(rows)
    changed[0].update(episode=9999, option="SPACE_1", replica=999, step=100000,
                      target=[1e9, 1e9, 1e9], remaining_steps=50, final_status="WON")
    assert len(module.FEATURE_NAMES) == x.shape[1] == 74
    assert np.array_equal(x, module._pair_array(changed, Counter()))
    swapped = deepcopy(rows)
    swapped[0]["candidate_board"], swapped[0]["reference_board"] = swapped[0]["reference_board"], swapped[0]["candidate_board"]
    assert np.array_equal(module._mirror(x), module._pair_array(swapped, Counter()))
    assert counts["board_feature_rows"] == 2 and counts["paired_feature_rows"] == 1


def test_prediction_is_exactly_antisymmetric_and_diagonal_or_two_absorbed_is_zero(models):
    model = models[0]["full"]
    for query in module.QUERIES:
        for ca, ra in ((True, True), (True, False), (False, True)):
            forward = model.predict_pair(LEFT, RIGHT, ca, ra, query)
            reverse = model.predict_pair(RIGHT, LEFT, ra, ca, query)
            assert forward == [-value for value in reverse]
        counts = Counter()
        assert model.predict_pair(LEFT, LEFT, True, True, query, counts) == [0., 0., 0.]
        assert model.predict_pair(LEFT, RIGHT, False, False, query, counts) == [0., 0., 0.]
        assert counts["paired_exact_zero_predictions"] == 2
        assert "tree_apply_rows" not in counts


def test_json_roundtrip_keeps_rosters_queries_and_paired_predictions(models):
    model = models[0]["fold_1"]
    payload = json.loads(json.dumps(model.to_payload(), allow_nan=False))
    restored = module.PairedContinuation.from_payload(payload)
    counts = Counter()
    for query in module.QUERIES:
        assert restored.predict_pair(LEFT, RIGHT, True, True, query, counts) == model.predict_pair(LEFT, RIGHT, True, True, query)
    assert restored.to_payload() == payload
    assert restored.excluded_fold == 1 and restored.checkpoint == 6
    assert counts["paired_continuation_predictions"] == 2 and counts["tree_apply_rows"] == 4
    assert "model_uniform_draws" not in counts
