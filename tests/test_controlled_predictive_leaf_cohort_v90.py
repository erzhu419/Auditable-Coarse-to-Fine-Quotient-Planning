"""Cohort selection and raw-history provenance without environment calls or fits."""
from copy import deepcopy
import gzip
import json
from pathlib import Path

import pytest

from acfqp.science import controlled_predictive_leaf_cohort_v90 as module
from acfqp.science.controlled_predictive_evidence_fragments_v88 import EvidenceSelector


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module", autouse=True)
def retain_work(request):
    yield
    path = ROOT / "reports/controlled_predictive_leaf_cohort_v90.cohort_checks.json"
    payload = json.loads(path.read_text()) if path.exists() else {"attempts": []}
    payload["attempts"].append(dict(test_module=__file__, session_failures=request.session.testsfailed,
        scope="Synthetic retained JSON campaign and exact tree interpretation.",
        ground_calls=0, main_campaign_calls=0, tree_fits=0))
    path.write_text(json.dumps(payload, indent=2) + "\n")


def _write(path, value):
    path.write_text(json.dumps(value) + "\n")


def _write_rows(path, rows):
    with gzip.open(path, "wt") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")


def _selector(supported):
    # Rank 0 > 5.5 reaches leaf 4; the other represented leaf has no members.
    target = [0., 0., 0.] * 3 + [0.5, 0., 0.]
    fractions = [[0., 1., 0.]] * 3 + [[0., 0., 1.] if supported else [0., 1., 0.]]
    tree = dict(left=[1, -1, -1, 2, -1], right=[3, -1, -1, 4, -1],
        feature=[0, -2, -2, 0, -2], threshold=[-1., -2., -2., .5, -2.],
        values=[target] * 5, frequencies=[fractions] * 5, samples=[10, 0, 0, 10, 10])
    return EvidenceSelector({"reward": tree}, 12)


@pytest.fixture
def campaign(tmp_path):
    source = tmp_path / "v89"
    source.mkdir()
    counter = 0
    for life in range(3):
        folder = source / f"life_{life}"
        folder.mkdir()
        events, raw = [], []
        evidence, balanced = _selector(True), _selector(False)
        _write(folder / "evidence_selector.json", evidence.to_payload())
        _write(folder / "balanced_selector.json", balanced.to_payload())
        for _, query, replica in sorted(item for item in module.EXPECTED_ROSTER if item[0] == life):
            counter += 1
            seed = 8990000 + life * 100 + replica
            board = [9, life + 1, replica + 1] + [1] * 7 + [0] * 6
            before = [0] * 8 + [1] * 8
            steps = [dict(board=before, action=1, next_board=board),
                     dict(board=board, action=2, next_board=board)]
            events.append(dict(seed=seed, query=query, replica=replica, category="enabled",
                               old_option="H2", new_option="SNAKE_4"))
            for method in module.METHODS:
                selector = evidence if method == "EVIDENCE_SUPPORTED" else balanced
                event = [] if method == "H2_ONLY" else [dict(step=1, board=board, **selector.select(board, query))]
                score = 1000 + (counter * (-1) ** counter * 100 if method == "EVIDENCE_SUPPORTED" else 0)
                raw.append(dict(method=method, query=query, controller_events=event,
                    episode=dict(seed=seed, steps=deepcopy(steps), return_score=score, status="LOST")))
        _write(folder / "run.json", dict(evaluation=dict(gate_changes={module.CONTRAST: events})))
        _write_rows(folder / "evaluation_games.jsonl.gz", raw)
        roots = [dict(query="reward", episode=episode, n_replicas=8,
                      board=[9, life + 1, 30 + episode] + [1] * 7 + [0] * 6)
                 for episode in module.EXPECTED_TRAINING.get(life, [])]
        # One same-leaf heldout and one training member of another leaf.
        roots += [dict(query="reward", episode=4, n_replicas=8, board=[9, life + 1, 99] + [1] * 13),
                  dict(query="reward", episode=7, n_replicas=8, board=[1, life + 1, 99] + [1] * 13)]
        _write_rows(folder / "base_paired_roots.jsonl.gz", roots)
    return source


def test_all_enabled_outcomes_retained_and_controls_reused_once(campaign):
    result = module.build_cohort(campaign)
    assert len(result["targets"]) == 7 and len(result["controls"]) == 5
    assert any(root["v89_score_delta"] > 0 for root in result["targets"])
    assert any(root["v89_score_delta"] < 0 for root in result["targets"])
    for root in result["targets"]:
        assert root["v89_utility_delta"] == root["v89_score_delta"] / 2048
    assert {root["episode"] for root in result["controls"]} == {0, 1, 3, 6, 8}
    assert all(root["episode"] % 5 != 4 for root in result["controls"])
    assert len({root["id"] for root in result["controls"]}) == 5
    groups = result["groups"]
    assert [(group["life"], len(group["target_ids"]), len(group["training_ids"])) for group in groups] == [
        (0, 4, 2), (2, 3, 3)]
    assert all(group["leaf"] == 4 and group["predicted_target"] == [.5, 0., 0.]
               and group["predicted_utility"] == .5 and group["positive_fraction"] == 1 for group in groups)
    assert set(groups[0]["training_ids"]).isdisjoint(groups[1]["training_ids"])
    assert all(result["checks"].values())
    assert result["mapping_work"]["environment_transitions"] == result["mapping_work"]["tree_fits"] == 0


def test_missing_enabled_case_fails_frozen_roster(campaign):
    path = campaign / "life_0/run.json"
    payload = json.loads(path.read_text())
    payload["evaluation"]["gate_changes"][module.CONTRAST].pop()
    _write(path, payload)
    with pytest.raises(ValueError, match="all seven"):
        module.build_cohort(campaign)


@pytest.mark.parametrize("change, expected", [
    ("event_prediction", "deployed selector"),
    ("event_board", "trigger state"),
    ("prefix", "pretrigger histories"),
    ("h2_suffix", "does not execute H2"),
])
def test_retained_events_and_actual_histories_must_agree(campaign, change, expected):
    path = campaign / "life_0/evaluation_games.jsonl.gz"
    rows = module._read_rows(path)
    current = next(row for row in rows if row["method"] == "EVIDENCE_SUPPORTED")
    previous = next(row for row in rows if row["method"] == "BALANCED_SUPPORTED")
    if change == "event_prediction":
        current["controller_events"][0]["value"] += 1
    elif change == "event_board":
        previous["controller_events"][0]["board"][2] += 1
    elif change == "prefix":
        current["episode"]["steps"][0]["action"] += 1
    else:
        previous["episode"]["steps"][1]["action"] += 1
    _write_rows(path, rows)
    with pytest.raises(ValueError, match=expected):
        module.build_cohort(campaign)


def test_same_leaf_training_member_cannot_be_omitted(campaign):
    path = campaign / "life_2/base_paired_roots.jsonl.gz"
    roots = module._read_rows(path)
    roots = [root for root in roots if root["episode"] != 8]
    _write_rows(path, roots)
    with pytest.raises(ValueError, match="training membership"):
        module.build_cohort(campaign)
