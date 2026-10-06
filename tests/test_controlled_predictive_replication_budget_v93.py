"""Exact interaction caps, fixed root order, and replica-weighted extra MC labels."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path

import pytest

from acfqp.science import controlled_predictive_replication_budget_v93 as module
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics, RewriteProgram


ROOT = Path(__file__).resolve().parents[1]
BOARD = [1] * 10 + [0] * 6
LEDGER = Counter()


@pytest.fixture(scope="module", autouse=True)
def retain_work(request):
    yield
    path = ROOT / "reports/controlled_predictive_replication_budget_v93.core_checks.json"
    payload = json.loads(path.read_text()) if path.exists() else {"attempts": []}
    payload["attempts"].append(dict(test_module=__file__, session_failures=request.session.testsfailed,
        scope="Mock allocation and weighted means plus seven real terminal transitions; no campaign calls.",
        main_campaign_calls=0, tree_fits=0, **LEDGER))
    path.write_text(json.dumps(payload, indent=2) + "\n")


def root(query="reward", episode=0, board=None):
    board = BOARD if board is None else board
    return dict(board=list(board), query=query, episode=episode, censored=False,
        mc_rows=[dict(board=list(board), query=query, episode=episode, option=option,
                      target=[2., .25, -.25]) for option in module.OPTIONS[1:]])


@pytest.fixture
def fake_sample(monkeypatch):
    calls = []
    lengths = [1, 2, 3, 1, 2]
    def sample(root, rule, env_seed_base, remaining, replicas):
        assert replicas == 1
        raw, consumed, outcomes = [], 0, Counter()
        for option, length in zip(module.OPTIONS, lengths):
            if consumed == remaining:
                break
            executed = min(length, remaining - consumed)
            status = "LOST" if executed == length else "CUTOFF"
            consumed += executed
            outcomes[status] += 1
            raw.append(dict(option=option, replica=0, env_seed=env_seed_base,
                model_seed=env_seed_base + 1_000_000_000_000,
                game=dict(status=status, work={"sampled_transitions": executed})))
        complete = len(raw) == 5 and "CUTOFF" not in outcomes
        rows = [dict(row, target=[root["episode"] + 1., 0., 0.]) for row in root["mc_rows"]] if complete else []
        calls.append(dict(query=root["query"], episode=root["episode"], seed=env_seed_base,
                          remaining=remaining, complete=complete))
        return rows, raw, dict(complete_block=complete, ground_work={"sampled_transitions": consumed},
            planning_counts={"model_uniform_draws": 4 * consumed}, outcomes=dict(outcomes),
            trajectories=len(raw), budget_exhausted=consumed == remaining, seconds=0)
    monkeypatch.setattr(module, "sample_root", sample)
    return calls


def test_fixed_round_robin_roster_uses_actual_remaining_and_keeps_partial_cost(fake_sample):
    roots = [root("risk_goal", 0), root("reward", 1), root("reward", 4), root("reward", 0),
             dict(root("reward", 2), censored=True), root("reward", 8)]
    before = deepcopy(roots)
    raw = []
    blocks, log = module.acquire_extra(roots, None, 2, 6, 32, raw.append)
    assert roots == before
    assert [(call["query"], call["episode"]) for call in fake_sample] == [
        ("reward", 1), ("reward", 0), ("risk_goal", 0), ("reward", 1)]
    assert log["roster_rotation"] == 2
    assert [call["remaining"] for call in fake_sample] == [32, 23, 14, 5]
    assert [call["seed"] for call in fake_sample] == [293_026_000_000 + i * 1000 for i in range(4)]
    assert len(blocks) == log["complete_blocks"] == 3
    assert log["used_transitions"] == 32 and log["unused_budget"] == 0
    assert log["incorporated_ground_work"]["sampled_transitions"] == 27
    assert log["unincorporated_ground_work"]["sampled_transitions"] == 5
    assert log["incomplete_blocks"] == log["budget_truncated_blocks"] == 1
    assert log["budget_cutoff_trajectories"] == 1 and log["max_step_cutoff_trajectories"] == 0
    assert len(raw) == log["trajectories"] == 18
    assert all(row["checkpoint"] == 6 and row["life"] == 2 for row in raw)
    assert [row["complete_extra_replicas"] for row in log["root_statistics"]] == [1, 1, 1]


def test_zero_budget_or_empty_eligible_roster_never_calls_sampler(fake_sample):
    blocks, log = module.acquire_extra([root()], None, 0, 6, 0, lambda row: None)
    assert blocks == fake_sample == []
    assert log["used_transitions"] == 0 and log["attempted_blocks"] == 0
    unavailable = [dict(root(), censored=True), root(episode=4)]
    blocks, log = module.acquire_extra(unavailable, None, 0, 6, 50, lambda row: None)
    assert blocks == fake_sample == log["roster"] == []
    assert log["used_transitions"] == 0 and log["unused_budget"] == 50


def test_real_terminal_block_and_partial_last_block_use_exactly_seven_transitions():
    rule = LearnedDynamics(RewriteProgram(True, "equal", 1, "once", "output_value"),
        ((1, Fraction(9, 10)), (2, Fraction(1, 10))), "uniform")
    raw = []
    blocks, log = module.acquire_extra([root(board=[10] * 16)], rule, 99, 6, 7, raw.append)
    LEDGER.update({"ground_" + key: value for key, value in log["ground_work"].items()})
    LEDGER.update({"planning_" + key: value for key, value in log["planning_counts"].items()})
    assert log["used_transitions"] == len(raw) == 7
    assert log["outcomes"] == {"WON": 7}
    assert log["complete_blocks"] == log["incomplete_blocks"] == log["budget_truncated_blocks"] == 1
    assert log["unincorporated_ground_work"]["sampled_transitions"] == 2
    assert log["budget_cutoff_trajectories"] == log["max_step_cutoff_trajectories"] == 0
    assert all(row["target"] == [0, 0, 0] for row in blocks[0]["rows"])
    assert [row["option"] for row in raw[-2:]] == ["H2", "SPACE_1"]


def block(root, checkpoint, target):
    return dict(checkpoint=checkpoint, root=module._metadata(root),
                rows=[dict(row, target=target) for row in root["mc_rows"]])


def test_original_means_and_cumulative_extra_pairs_use_replica_counts():
    first, untouched, heldout = root(), root(episode=1), root(episode=4)
    roots = [first, untouched, heldout]
    blocks = [block(first, 6, [10, -.5, .5]), block(first, 12, [6, .5, -.5]),
              block(untouched, 12, [11, 1, -1])]
    before = deepcopy((roots, blocks))
    early, early_log = module.merge_rows(roots, blocks, 6)
    late, late_log = module.merge_rows(roots, blocks, 12)
    assert (roots, blocks) == before
    assert early_log["complete_extra_blocks"] == 1 and late_log["complete_extra_blocks"] == 3
    for row in early:
        assert row["target"] == pytest.approx([26 / 9, 1.5 / 9, -1.5 / 9] if row["episode"] == 0 else [2, .25, -.25])
    for row in late:
        expected = ([3.2, .2, -.2] if row["episode"] == 0 else
                    [3, 1 / 3, -1 / 3] if row["episode"] == 1 else [2, .25, -.25])
        assert row["target"] == pytest.approx(expected)
    assert [item["total_replicas"] for item in late_log["root_statistics"]] == [10, 9, 8]
    assert late_log["heldout_roots"] == 1 and late_log["training_roots"] == 2


def test_incomplete_block_or_heldout_extra_cannot_enter_combined_labels():
    sample = root()
    incomplete = block(sample, 6, [1, 0, 0])
    incomplete["rows"].pop()
    with pytest.raises(ValueError, match="all four"):
        module.merge_rows([sample], [incomplete], 6)
    heldout = root(episode=4)
    with pytest.raises(ValueError, match="training roster"):
        module.merge_rows([heldout], [block(heldout, 6, [1, 0, 0])], 6)
