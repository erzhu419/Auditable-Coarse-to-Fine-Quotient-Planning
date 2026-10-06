"""Continuation weights, episode separation, and paired four-step completion."""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path

import pytest

from acfqp.science import controlled_predictive_continuation_value_v91 as module


ROOT = Path(__file__).resolve().parents[1]
BOARD = [1, 1, 2, 3, 4, 1, 2, 3, 4, 5, 0, 0, 0, 0, 0, 0]
LEDGER = Counter()


@pytest.fixture(scope="module", autouse=True)
def retain_work(request):
    yield
    path = ROOT / "reports/controlled_predictive_continuation_value_v91.core_checks.json"
    payload = json.loads(path.read_text()) if path.exists() else {"attempts": []}
    payload["attempts"].append(dict(test_module=__file__, session_failures=request.session.testsfailed,
        scope="Synthetic weighted trees, fold isolation and paired labels; no environment sampling.",
        sampled_transitions=0, main_campaign_calls=0, **LEDGER))
    path.write_text(json.dumps(payload, indent=2) + "\n")


def tails():
    values = {0: [1, .2, .8], 1: [10, .4, .6], 2: [3, .6, .4], 3: [30, .8, .2],
              4: [999, 999, 999], 6: [-999, -999, -999]}
    return [dict(board=list(BOARD), query=query, episode=episode, target=target,
                 weight=(3 if episode == 3 else 1) / 16, replica=0, option="H2", step=step)
            for query in module.QUERIES for episode, target in values.items() for step in range(16)]


@pytest.fixture(scope="module")
def continuation_models():
    records = tails()
    full, full_log = module.ContinuationValue.fit(records, 6)
    folded, fold_log = module.ContinuationValue.fit(records, 6, excluded_fold=0)
    changed = deepcopy(records)
    for row in changed:
        if row["episode"] not in (1, 3):
            row["target"] = [1e9, -1e9, 1e9]
    same, same_log = module.ContinuationValue.fit(changed, 6, excluded_fold=0)
    for log in (full_log, fold_log, same_log):
        LEDGER.update(log["counts"])
    return full, full_log, folded, fold_log, same


def test_real_weighted_fit_and_episode_exclusions(continuation_models):
    full, full_log, folded, fold_log, same = continuation_models
    assert len(module.FEATURE_NAMES) == 36
    for query in module.QUERIES:
        assert full_log["queries"][query]["training_episodes"] == [0, 1, 2, 3]
        assert fold_log["queries"][query]["training_episodes"] == [1, 3]
        assert fold_log["queries"][query]["weight_sum"] == 4
        assert folded.predict(BOARD, query) == pytest.approx([25, .7, .3])
        assert full.predict(BOARD, query) == pytest.approx([104 / 6, 3.6 / 6, 2.4 / 6])
    assert folded.to_payload() == same.to_payload()
    assert full_log["counts"]["tree_fits"] == fold_log["counts"]["tree_fits"] == 2


def test_json_roundtrip_retains_queries_fold_roster_and_predictions(continuation_models):
    model = continuation_models[2]
    payload = json.loads(json.dumps(model.to_payload(), allow_nan=False))
    restored = module.ContinuationValue.from_payload(payload)
    counts = Counter()
    for query in module.QUERIES:
        assert restored.predict(BOARD, query, counts) == model.predict(BOARD, query)
    assert restored.to_payload() == payload
    assert counts["continuation_predictions"] == counts["board_feature_rows"] == 2
    assert "model_uniform_draws" not in counts
    LEDGER.update(counts)


def test_composition_adds_tail_once_and_never_uses_terminal_or_cutoff_tail():
    class Tail:
        def predict(self, board, query, work=None):
            assert board == BOARD and query == "reward"
            return [7, .2, .8]
    prefix = dict(direct=[2, 0, 0], boundary_board=list(BOARD), status="ACTIVE", full_target=[999] * 3)
    assert module.compose(prefix, Tail(), "reward") == pytest.approx([9, .2, .8])
    for status, target in (("WON", [2, 0, 1]), ("LOST", [2, 1, 0])):
        terminal = dict(prefix, status=status, direct=target)
        result = module.compose(terminal, None, "reward")
        assert result == target and result is not terminal["direct"]
    with pytest.raises(ValueError, match="cutoff"):
        module.compose(dict(prefix, status="CUTOFF"), None, "reward")


def roots():
    result = []
    for query in module.QUERIES:
        for episode in range(7):
            prefixes = {option: [] for option in module.OPTIONS}
            for replica in range(2):
                for option, direct, status in (("H2", [1, 0, 0], "ACTIVE"),
                        ("SPACE_1", [3, 0, 0], "ACTIVE"),
                        ("SNAKE_1", [10, 0, 1], "WON"),
                        ("SPACE_4", [5, 1, 0], "LOST"),
                        ("SNAKE_4", [4 + replica, 0, 0], "ACTIVE")):
                    prefixes[option].append(dict(replica=replica, option=option, direct=direct,
                        boundary_board=list(BOARD), status=status, full_target=[999] * 3))
            result.append(dict(board=list(BOARD), query=query, episode=episode,
                prefixes=prefixes, mc_rows=[], censored=episode == 5))
    return result


@pytest.fixture(scope="module")
def decomposed():
    records, tail_records = roots(), tails()
    before = deepcopy((records, tail_records))
    result = module.fit_decomposed(records, tail_records, 6)
    assert (records, tail_records) == before
    LEDGER.update(result[-1]["counts"])
    return result


def test_crossfit_uses_opposite_episode_fold_for_both_arms(decomposed):
    selector, models, rows, log = decomposed
    assert log["oof_episode_isolation"]
    assert log["counts"]["tree_fits"] == 8
    assert log["head_fit"]["training_roots"] == 8
    assert log["head_fit"]["heldout_roots"] == 2
    assert log["censored_roots_excluded"] == log["future_roots_excluded"] == 2
    assert len(rows) == 40 and {row["episode"] for row in rows} == set(range(5))
    for row in rows:
        episode = row["episode"]
        expected_name = "full" if episode == 4 else f"fold_{episode % 2}"
        assert row["continuation_model"] == expected_name
        model = models[expected_name]
        if episode != 4:
            assert all(episode not in roster for roster in model.training_episodes.values())
        tail = model.predict(BOARD, row["query"])
        if row["option"] == "SPACE_1":
            assert row["target"] == pytest.approx([2, 0, 0])
        elif row["option"] == "SNAKE_1":
            assert row["target"] == pytest.approx([9 - tail[0], -tail[1], 1 - tail[2]])
        elif row["option"] == "SNAKE_4":
            assert row["paired_targets"] == [[3, 0, 0], [4, 0, 0]]
        assert row["paired_replicas"] == [0, 1]
    assert selector.checkpoint == 6
    assert all(item["paired_utility_sample_variance"] == .5
        for item in log["label_variance"] if item["option"] == "SNAKE_4")
