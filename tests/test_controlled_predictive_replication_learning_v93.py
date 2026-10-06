"""Shared fresh cohorts and integration of the unchanged V91/V92 algorithms."""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path

import pytest

from acfqp.science import controlled_predictive_replication_learning_v93 as module
from acfqp.science.controlled_predictive_continuation_data_v91 import _key
from acfqp.science.controlled_predictive_fragments_v83 import OPTIONS, QUERIES


ROOT = Path(__file__).resolve().parents[1]
BOARD = [1, 1, 2, 3, 4, 1, 2, 3, 4, 5, 0, 0, 0, 0, 0, 0]
OTHER = [2, 1, 2, 3, 4, 1, 2, 3, 4, 5, 0, 0, 0, 0, 0, 0]
LEDGER = Counter()


@pytest.fixture(scope="module", autouse=True)
def retain_work(request):
    yield
    path = ROOT / "reports/controlled_predictive_replication_learning_v93.learning_checks.json"
    payload = json.loads(path.read_text()) if path.exists() else {"attempts": []}
    payload["attempts"].append(dict(test_module=__file__, session_failures=request.session.testsfailed,
        scope="Synthetic integrated V91/V92 learning; no fresh campaign data or environment calls.",
        sampled_transitions=0, main_campaign_calls=0, **LEDGER))
    path.write_text(json.dumps(payload, indent=2) + "\n")


def dataset():
    roots, unary, paired, pools = [], [], [], {}
    for query in QUERIES:
        for episode in range(7):
            prefixes = {option: [] for option in OPTIONS}
            for index, option in enumerate(OPTIONS):
                for replica in range(2):
                    prefixes[option].append(dict(replica=replica, option=option,
                        direct=[index / 10, 0., 0.], boundary_board=list(BOARD if option == "H2" else OTHER),
                        status="ACTIVE", full_target=[2 + index / 2 + replica / 10, 1., 0.]))
            root = dict(board=list(BOARD), query=query, episode=episode, prefixes=prefixes,
                        mc_rows=[], censored=episode == 5)
            roots.append(root)
            pools[_key(root)] = deepcopy(prefixes)
            if episode == 5:
                continue
            for step in range(16):
                unary.append(dict(board=list(BOARD), query=query, episode=episode,
                    target=[1 + episode, .75, .25], weight=1 / 16, step=step))
                paired.append(dict(candidate_board=list(OTHER), reference_board=list(BOARD),
                    candidate_active=True, reference_active=True, query=query, episode=episode,
                    target=[episode / 10, 0., 0.], weight=1 / 32, step=step))
    return roots, unary, paired, pools


@pytest.fixture(scope="module")
def learned():
    data = dataset()
    before = deepcopy(data)
    result = module.learn(*data, checkpoint=6)
    assert data == before
    LEDGER.update(result[-1]["counts"])
    return result


def test_unchanged_learners_return_all_models_and_exactly_twenty_new_trees(learned):
    selectors, paired_models, unary_models, labels, log = learned
    assert set(selectors) == set(labels) == {"MC", "PAIR_ONLY", "CORRECTED", "V91_DECOMPOSED"}
    assert set(paired_models) == set(unary_models) == {"full", "fold_0", "fold_1"}
    assert log["counts"]["tree_fits"] == 20
    assert log["paired_models"]["counts"]["tree_fits"] == 6
    assert log["paired_selectors"]["counts"]["tree_fits"] == 6
    assert log["v91_decomposed"]["counts"]["tree_fits"] == 8
    assert log["new_environment_transitions"] == 0
    assert all(selector.checkpoint == 6 for selector in selectors.values())
    assert all(len(rows) == 40 and {row["episode"] for row in rows} == {0, 1, 2, 3, 4}
               for rows in labels.values())
    for models in (paired_models, unary_models):
        for name, model in models.items():
            expected = {"full": [0, 1, 2, 3], "fold_0": [1, 3], "fold_1": [0, 2]}[name]
            assert all(roster == expected for roster in model.training_episodes.values())
    for fit in log["paired_selectors"]["head_fits"].values():
        assert fit["training_roots"] == 8 and fit["heldout_roots"] == 2
    assert log["v91_decomposed"]["head_fit"]["training_roots"] == 8


def test_integration_keeps_v91_and_v92_weights_and_hyperparameters_separate(learned):
    _, paired_models, unary_models, _, log = learned
    p = paired_models["full"].to_payload()
    u = unary_models["full"].to_payload()
    assert p["tree_parameters"] == dict(max_depth=8, min_samples_leaf=16, random_state=9201)
    assert u["tree_parameters"] == dict(max_depth=8, min_samples_leaf=16, random_state=9101)
    assert len(p["feature_names"]) == 74 and len(u["feature_names"]) == 36
    for query in QUERIES:
        assert log["paired_models"]["fits"]["full"]["queries"][query]["weight_sum"] == 2
        assert log["v91_decomposed"]["tail_fits"]["full"]["queries"][query]["weight_sum"] == 4
    # All returned selectors/models and logs are ready for retained JSON export.
    json.dumps(dict(paired={key: model.to_payload() for key, model in paired_models.items()},
                    unary={key: model.to_payload() for key, model in unary_models.items()}, log=log), allow_nan=False)


def test_already_loaded_cohorts_compare_every_prefix_and_label_without_reading_files():
    roots = dataset()[0]
    same = deepcopy(roots)
    assert module.assert_shared_roots(roots, same) == dict(root_cohorts_identical=True, roots=14, mc_rows=0)
    same[0]["prefixes"]["SNAKE_4"][0]["full_target"][0] += 1
    with pytest.raises(ValueError, match="different roots"):
        module.assert_shared_roots(roots, same)
