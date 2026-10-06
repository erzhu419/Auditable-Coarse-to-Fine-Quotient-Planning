"""Warm starts, synchronous targets, episode isolation, and cached board features."""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path

import pytest

from acfqp.science import controlled_predictive_bellman_value_v94 as module


ROOT = Path(__file__).resolve().parents[1]
BOARD = [1, 1, 2, 3, 4, 1, 2, 3, 4, 5, 0, 0, 0, 0, 0, 0]
LEDGER = Counter()


@pytest.fixture(scope="module", autouse=True)
def retain_work(request):
    yield
    path = ROOT / "reports/controlled_predictive_bellman_value_v94.core_checks.json"
    payload = json.loads(path.read_text()) if path.exists() else {"attempts": []}
    payload["attempts"].append(dict(test_module=__file__, session_failures=request.session.testsfailed,
        scope="Synthetic two-round Bellman models and heads; no source extraction or environment sampling.",
        sampled_transitions=0, main_campaign_calls=0, **LEDGER))
    path.write_text(json.dumps(payload, indent=2) + "\n")


def data():
    return [dict(query=query, episode=episode, board=list(BOARD),
        next_board=list(BOARD) if active else [10] * 16, next_active=active,
        n_target=[1, 0, 0] if active else [2, 1, 0],
        target=[10 * (episode + 1), .25, .75], weight=1.0)
        for query in module.QUERIES for episode in (0, 1, 2, 3, 4, 6)
        for active in (True, False) for _ in range(16)]


@pytest.fixture(scope="module")
def fitted():
    rows = data()
    before = deepcopy(rows)
    models, log = module.fit_models(rows, checkpoint=6, iterations=2)
    assert rows == before
    changed = deepcopy(rows)
    for row in changed:
        if row["episode"] not in (1, 3):
            row.update(target=[100000, 0, 1], n_target=[90000, 0, 1], next_active=False)
    other, other_log = module.fit_models(changed, checkpoint=6, iterations=2)
    LEDGER.update(log["counts"])
    LEDGER.update(other_log["counts"])
    return models, log, other


def test_warm_start_is_preserved_and_synchronous_rounds_use_previous_values(fitted):
    models, log, _ = fitted
    for query in module.QUERIES:
        assert models["MC_TAIL"]["full"].predict(BOARD, query) == [25, .25, .75]
        assert models["FQE"]["full"].predict(BOARD, query) == [8.5, .8125, .1875]
        # R_{t+1}=0.5*(1+R_t)+0.5*2; terminal anchors never add a predicted tail.
        iterations = log["folds"]["full"]["FQE"]["iterations"]
        assert iterations[0]["queries"][query]["mean_prediction_rfs"] == [14, .625, .375]
        assert iterations[1]["queries"][query]["mean_prediction_rfs"] == [8.5, .8125, .1875]
        assert all(row["queries"][query]["mean_failure_plus_success"] == 1 for row in iterations)
    assert models["MC_TAIL"]["full"].iterations == 0
    assert models["FQE"]["full"].iterations == 2


def test_excluded_episode_cannot_leak_through_warm_start_or_bootstrap(fitted):
    models, log, other = fitted
    for family in module.FAMILIES:
        assert models[family]["fold_0"].to_payload() == other[family]["fold_0"].to_payload()
        assert models[family]["fold_0"].training_episodes == {query: [1, 3] for query in module.QUERIES}
    assert models["FQE"]["fold_0"].predict(BOARD, "reward") == [9.75, .8125, .1875]
    assert models["FQE"]["fold_1"].predict(BOARD, "reward") == [7.25, .8125, .1875]
    for fold in log["folds"].values():
        assert all(4 not in episodes and 6 not in episodes for episodes in fold["training_episodes"].values())


def test_feature_caches_are_built_once_and_all_real_fit_work_is_counted(fitted):
    _, log, _ = fitted
    counts = log["counts"]
    assert counts["tree_fits"] == 18
    assert counts["mc_tail_tree_fits"] == 6 and counts["fqe_tree_fits"] == 12
    assert counts["feature_cache_builds"] == 6
    assert counts["cached_training_rows"] == 512
    assert counts["cached_bootstrap_rows"] == 256
    assert counts["board_feature_rows"] == 768
    assert counts["bootstrap_prediction_rows"] == 512
    for fold in log["folds"].values():
        assert fold["MC_TAIL"]["counts"]["tree_fits"] == 2
        assert fold["FQE"]["counts"]["tree_fits"] == 4
        assert fold["FQE"]["initialization"] == "MC_TAIL"


def test_json_roundtrip_preserves_training_method_and_both_saved_models(fitted):
    models = fitted[0]
    for family in module.FAMILIES:
        payload = json.loads(json.dumps(models[family]["full"].to_payload(), allow_nan=False))
        restored = module.BellmanValue.from_payload(payload)
        assert restored.to_payload() == payload
        assert restored.predict(BOARD, "reward") == models[family]["full"].predict(BOARD, "reward")
        assert restored.training_method == family
    assert len(module.FEATURE_NAMES) == 36


def roots():
    output = []
    for query in module.QUERIES:
        for episode in range(7):
            prefixes = {option: [] for option in module.OPTIONS}
            for option in module.OPTIONS:
                for replica in range(8):
                    status = "WON" if option == "SNAKE_1" else "ACTIVE"
                    direct = [10, 0, 1] if status == "WON" else [1, 0, 0]
                    prefixes[option].append(dict(replica=replica, option=option, status=status,
                        direct=direct, boundary_board=list(BOARD), full_target=[999, 0, 1]))
            output.append(dict(board=list(BOARD), query=query, episode=episode, prefixes=prefixes,
                               censored=episode == 5))
    return output


def test_heads_use_corresponding_oof_models_and_terminal_values_once(fitted):
    models = fitted[0]
    source = roots()
    before = deepcopy(source)
    selectors, labels, log = module.fit_heads(source, models, checkpoint=6)
    LEDGER.update(log["counts"])
    assert source == before and log["oof_episode_isolation"]
    assert log["counts"]["tree_fits"] == 4
    assert log["censored_roots_excluded"] == log["future_roots_excluded"] == 2
    for family in module.FAMILIES:
        assert len(labels[family]) == 40
        assert log["head_fits"][family]["training_roots"] == 8
        assert log["head_fits"][family]["heldout_roots"] == 2
        assert selectors[family].checkpoint == 6
        for row in labels[family]:
            name = "full" if row["episode"] == 4 else f"fold_{row['episode'] % 2}"
            assert row["continuation_model"] == name
            tail = models[family][name].predict(BOARD, row["query"])
            expected = [9 - tail[0], -tail[1], 1 - tail[2]] if row["option"] == "SNAKE_1" else [0, 0, 0]
            assert row["target"] == pytest.approx(expected)
            assert len(row["paired_targets"]) == 8
