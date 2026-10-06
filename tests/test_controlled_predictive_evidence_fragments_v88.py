"""Paired uncertainty, complete-block pooling and matched candidate support."""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path

import numpy as np
import pytest

from acfqp.science import controlled_predictive_evidence_fragments_v88 as module


ROOT = Path(__file__).resolve().parents[1]
BOARD = (1, 1, 2, 3, 4, 1, 2, 3, 4, 5, 0, 0, 0, 0, 0, 0)
LEDGER = Counter()


@pytest.fixture(scope="module", autouse=True)
def retain_work(request):
    yield
    path = ROOT / "reports/controlled_predictive_evidence_fragments_v88.core_checks.json"
    payload = json.loads(path.read_text()) if path.exists() else {"attempts": []}
    payload["attempts"].append(dict(test_module=__file__, session_failures=request.session.testsfailed,
        scope="Synthetic paired samples and tree fits; no campaign fit, RNG or environment calls.",
        ground_calls=0, main_campaign_calls=0, **LEDGER))
    path.write_text(json.dumps(payload, indent=2) + "\n")


def log_block(episode, samples, query="reward", **extra):
    return dict(root=dict(query=query, episode=episode, board=list(BOARD)), censored_root=False,
                pair_deltas={option: deepcopy(samples) for option in module.OPTIONS[1:]}, **extra)


def mean_rows(blocks):
    samples = {}
    for block in blocks:
        if block.get("complete_block", True) and not block["censored_root"]:
            root = block["root"]
            key = root["query"], root["episode"]
            if key not in samples:
                samples[key] = {option: [] for option in module.OPTIONS[1:]}
            for option in module.OPTIONS[1:]:
                samples[key][option].extend(block["pair_deltas"][option])
    return [dict(query=query, episode=episode, board=list(BOARD), option=option,
                 target=np.asarray(values).mean(axis=0).tolist())
            for (query, episode), targets in samples.items() for option, values in targets.items()]


def test_complete_blocks_pool_raw_repeat_samples_and_preserve_coverage_roots():
    base = [log_block(0, [[1, 0, 0], [3, 0, 0]])]
    extra = [log_block(0, [[5, 0, 0], [7, 0, 0]], complete_block=True,
                       original_replicas=2, resulting_replicas=4),
             log_block(1, [[2, 0, 0], [6, 0, 0]], complete_block=True,
                       original_replicas=0, resulting_replicas=2),
             log_block(0, [[1000, 0, 0]] * 2, complete_block=False,
                       original_replicas=4, resulting_replicas=4)]
    before = deepcopy((base, extra))
    roots, log = module.reconstruct_roots(base, extra, mean_rows(base + extra))
    assert (base, extra) == before
    assert [root["n_replicas"] for root in roots] == [4, 2]
    np.testing.assert_array_equal(roots[0]["pair_deltas"]["SPACE_1"], [[1, 0, 0], [3, 0, 0], [5, 0, 0], [7, 0, 0]])
    evidence = roots[0]["evidence"]["SPACE_1"]
    assert evidence["n"] == 4 and evidence["mean_utility"] == 4
    assert evidence["standard_error"] == pytest.approx(np.std([1, 3, 5, 7], ddof=1) / 2)
    assert evidence["label"] == 1
    assert log["counts"]["extra_blocks_excluded"] == 1
    assert log["counts"]["extra_complete_blocks"] == 2
    assert log["retained_means_match"] and log["largest_mean_difference"] == 0
    assert log["paired_root_replicas"] == 6


def test_reconstruction_rejects_wrong_means_root_set_and_repeat_weights():
    base = [log_block(0, [[1, 0, 0], [3, 0, 0]])]
    rows = mean_rows(base)
    wrong = deepcopy(rows)
    wrong[0]["target"][0] += 1
    with pytest.raises(ValueError, match="pooled paired means"):
        module.reconstruct_roots(base, [], wrong)
    with pytest.raises(ValueError, match="roots do not match"):
        module.reconstruct_roots(base, [], [])
    with pytest.raises(ValueError, match="each root once"):
        module.reconstruct_roots(base + base, [], rows)
    extra = [log_block(0, [[5, 0, 0], [7, 0, 0]], complete_block=True,
                       original_replicas=8, resulting_replicas=10)]
    with pytest.raises(ValueError, match="original replica count"):
        module.reconstruct_roots(base, extra, rows)


def test_scalar_paired_uncertainty_preserves_covariance_and_three_labels():
    # R and F vary together, so the risk utility is exactly one in each replica.
    correlated = module.paired_evidence([[1, 0, 0], [5, 1, 0], [-3, -1, 0]], "risk_goal")
    assert correlated["mean_utility"] == 1 and correlated["standard_error"] == 0
    assert correlated["label"] == 1
    for samples, label in (([[0, 0, 0]] * 8, 0), ([[-1, 0, 0]] * 8, -1),
                           ([[-4, 0, 0], [5, 0, 0]] * 4, 0)):
        evidence = module.paired_evidence(samples, "reward")
        assert evidence["label"] == label
    assert module.paired_evidence([[0, 0, 0], [2, 0, 0]], "reward")["standard_error"] == 1


@pytest.fixture(scope="module")
def fitted():
    roots = []
    for query in module.QUERIES:
        for episode, samples in enumerate(([[2, 0, 0]] * 8, [[6, 0, 0]] * 16,
                                           [[-2, 0, 0]] * 8, [[-10, 0, 0], [11, 0, 0]] * 4,
                                           [[999, 0, 0]] * 8)):
            targets = {option: np.asarray(samples).mean(axis=0).tolist() for option in module.OPTIONS[1:]}
            roots.append(dict(query=query, episode=episode, board=list(BOARD),
                pair_deltas={option: deepcopy(samples) for option in module.OPTIONS[1:]},
                target=[value for option in module.OPTIONS[1:] for value in targets[option]],
                targets=targets, n_replicas=len(samples),
                evidence={option: module.paired_evidence(samples, query) for option in module.OPTIONS[1:]}))
    captured = []
    actual_fit = module._fit

    def capture(x, labels, targets, counts):
        captured.append((x.copy(), labels.copy(), targets.copy()))
        return actual_fit(x, labels, targets, counts)

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(module, "_fit", capture)
        selector, log = module.EvidenceSelector.fit(roots)
    LEDGER.update(log["counts"])
    changed = deepcopy(roots)
    for root in changed:
        if root["episode"] == 4:
            root["board"] = [12] * 16
            root["target"] = [-1e6] * 12
            for option in module.OPTIONS[1:]:
                root["evidence"][option]["label"] = -1
                root["evidence"][option]["status"] = "negative"
    other, other_log = module.EvidenceSelector.fit(changed)
    LEDGER.update(other_log["counts"])
    return selector, log, captured, other


def test_whole_root_classifier_excludes_heldout_and_weights_roots_equally(fitted):
    selector, log, captured, other = fitted
    assert selector.to_payload() == other.to_payload()
    assert log["input_roots"] == 10 and log["training_roots"] == 8 and log["heldout_roots"] == 2
    assert log["counts"]["tree_fits"] == 2
    assert log["counts"]["fit_rows"] == log["counts"]["fit_roots"] == 8
    assert log["counts"]["fit_candidate_labels"] == 32
    assert log["counts"]["paired_root_replicas_read"] == 80
    for x, labels, targets in captured:
        assert x.shape == (4, 36) and labels.shape == (4, 4) and targets.shape == (4, 12)
        np.testing.assert_array_equal(labels, [[1] * 4, [1] * 4, [-1] * 4, [0] * 4])
    for tree in selector.trees.values():
        assert tree["samples"] == [4]
        np.testing.assert_array_equal(tree["frequencies"][0], [[0.25, 0.25, 0.5]] * 4)
        np.testing.assert_array_equal(np.asarray(tree["values"][0]).reshape(4, 3), [[1.625, 0, 0]] * 4)
    # Two positive roots out of four is exactly 0.5, regardless of 8 vs 16 replicas.
    assert selector.select(BOARD, "reward")["option"] == "H2"
    assert selector.with_mode("POINT").select(BOARD, "reward")["option"] == "SPACE_1"


def leaf_model(values, fractions):
    tree = dict(left=[-1], right=[-1], feature=[-2], threshold=[-2.0], samples=[4],
                values=[np.asarray(values).reshape(-1).tolist()], frequencies=[fractions])
    return module.EvidenceSelector({query: deepcopy(tree) for query in module.QUERIES}, 12)


def test_supported_can_select_lower_mean_supported_candidate_or_abstain():
    model = leaf_model([[9, 0, 0], [4, 0, 0], [3, 0, 0], [2, 0, 0]],
                       [[0.25, 0.25, 0.5], [0, 0.25, 0.75], [0, 1, 0], [1, 0, 0]])
    counts = Counter()
    point = model.with_mode("POINT").select(BOARD, "reward", tuple(reversed(module.OPTIONS)), counts)
    supported = model.select(BOARD, "reward", work=counts)
    assert point["option"] == "SPACE_1" and supported["option"] == "SNAKE_1"
    assert point["predictions"] == supported["predictions"]
    unresolved = supported["predictions"]["SPACE_4"]["evidence_fractions"]
    assert unresolved == dict(negative=0, unresolved=1, positive=0)
    assert model.select(BOARD, "reward", ("H2", "SPACE_1"), counts)["option"] == "H2"
    assert model.select(BOARD, "reward", ("H2",), counts)["option"] == "H2"
    assert counts["tree_apply_rows"] == 3 and counts["board_feature_rows"] == 3
    LEDGER.update(counts)
    nonpositive = leaf_model([[0, 0, 0], [-1, 0, 0], [-2, 0, 0], [-3, 0, 0]], [[0, 0, 1]] * 4)
    assert nonpositive.select(BOARD, "reward")["option"] == "H2"
    tied = leaf_model([[1, 0, 0]] * 4, [[0, 0, 1]] * 4)
    assert tied.select(BOARD, "reward", tuple(reversed(module.OPTIONS)))["option"] == "SPACE_1"


def test_modes_and_json_roundtrip_are_independent_and_preserve_predictions(fitted):
    original, _, _, _ = fitted
    point = original.with_mode("POINT")
    assert point.trees == original.trees and point.trees is not original.trees
    assert point.mode == "POINT" and original.mode == "SUPPORTED"
    payload = json.loads(json.dumps(point.to_payload()))
    restored = module.EvidenceSelector.from_payload(payload)
    counts = Counter()
    for query in module.QUERIES:
        for allowed in (None, module.ONE_STEP_OPTIONS):
            assert restored.select(BOARD, query, allowed, counts) == point.select(BOARD, query, allowed, counts)
    assert restored.to_payload() == payload
    restored.trees["reward"]["values"][0][0] = -100
    assert restored.trees != point.trees and original.trees == point.trees
    assert "model_uniform_draws" not in counts
    LEDGER.update(counts)
