"""Allocation causality, pooled evidence, exact budgets and independent confirmation."""
from collections import Counter
from copy import deepcopy
import gzip
import json
from pathlib import Path

import numpy as np
import pytest

from acfqp.science import controlled_predictive_evidence_resampling_v89 as module


ROOT = Path(__file__).resolve().parents[1]
BOARD = [1, 1, 2, 3, 4, 1, 2, 3, 4, 5, 0, 0, 0, 0, 0, 0]
LEDGER = Counter()


@pytest.fixture(scope="module", autouse=True)
def retain_work(request):
    yield
    path = ROOT / "reports/controlled_predictive_evidence_resampling_v89.core_checks.json"
    payload = json.loads(path.read_text()) if path.exists() else {"attempts": []}
    payload["attempts"].append(dict(test_module=__file__, session_failures=request.session.testsfailed,
        scope="Synthetic sample collector; no environment transitions or tree fits.",
        ground_calls=0, main_campaign_calls=0, **LEDGER))
    path.write_text(json.dumps(payload, indent=2) + "\n")


def root(episode, samples=None, query="reward"):
    samples = [[-4, 0, 0], [5, 0, 0]] * 4 if samples is None else samples
    return module.refresh_root(dict(query=query, episode=episode, board=list(BOARD),
        pair_deltas={option: deepcopy(samples) for option in module.OPTIONS[1:]}))


def roster():
    return [root(episode, query=query) for query in module.QUERIES for episode in (0, 1, 4)]


def fake_collector(calls, sample_for=None):
    def collect(root, rule, env_seed_base, remaining, replicas=8, max_steps=2000):
        calls.append(dict(key=module._key(root), seed=env_seed_base, remaining=remaining, replicas=replicas))
        LEDGER["synthetic_collector_calls"] += 1
        used = min(remaining, replicas * len(module.OPTIONS))
        complete = used == replicas * len(module.OPTIONS)
        samples = [[2, 0, 0]] * replicas if sample_for is None else sample_for(len(calls), root, env_seed_base)
        raw = [dict(option=module.OPTIONS[index % len(module.OPTIONS)], replica=index // len(module.OPTIONS),
                    env_seed=env_seed_base + index // len(module.OPTIONS), game=dict(status="LOST", work={"sampled_transitions": 1}))
               for index in range(used)]
        pair_deltas = {option: deepcopy(samples) for option in module.OPTIONS[1:]} if complete else {}
        return [], raw, dict(complete_block=complete, ground_work={"sampled_transitions": used},
            planning_counts={"synthetic_draws": used}, outcomes={"LOST": used},
            trajectories=used, pair_deltas=pair_deltas, seconds=0,
            unused_budget=remaining - used, budget_exhausted=used == remaining)
    return collect


def test_evidence_priority_uses_unresolved_bounds_only_then_balanced_fallback():
    resolved = root(0, [[100, 0, 0]] * 8)
    weaker = root(1, [[-1, 0, 0], [2, 0, 0]] * 4)
    stronger = root(2)
    selected, priority = module.choose_root([resolved, weaker, stronger], "EVIDENCE")
    assert selected is stronger and priority["rule"] == "unresolved_upper"
    assert "SPACE_1" in priority["unresolved_upper_bounds"]
    # A resolved candidate cannot increase its root's scheduling priority.
    weaker["evidence"]["SPACE_1"].update(upper=10000, label=1)
    assert module.choose_root([weaker, stronger], "EVIDENCE")[0] is stronger
    longer = root(3, [[-4, 0, 0], [5, 0, 0]] * 8)
    for option in module.OPTIONS[1:]:
        longer["evidence"][option]["upper"] = stronger["evidence"][option]["upper"]
    assert module.choose_root([longer, stronger], "EVIDENCE")[0] is stronger
    equal = deepcopy(stronger)
    assert module.choose_root([equal, stronger], "EVIDENCE")[0] is equal
    resolved_more = root(1, [[100, 0, 0]] * 16)
    selected, priority = module.choose_root([resolved_more, resolved], "EVIDENCE")
    assert selected is resolved and priority["balanced_fallback"]


def test_refresh_pools_raw_replicas_for_means_and_standard_errors():
    item = root(0, [[0, 0, 0], [2, 0, 0]] * 4)
    extra = [[4, 0, 0], [8, 0, 0]] * 4
    for option in module.OPTIONS[1:]:
        item["pair_deltas"][option].extend(deepcopy(extra))
    module.refresh_root(item)
    values = np.asarray([0, 2] * 4 + [4, 8] * 4)
    assert item["n_replicas"] == 16
    assert item["target"] == [3.5, 0, 0] * 4
    evidence = item["evidence"]["SPACE_1"]
    assert evidence["n"] == 16 and evidence["mean_utility"] == 3.5
    assert evidence["standard_error"] == pytest.approx(values.std(ddof=1) / 4)


def test_exact_budget_retains_partial_trace_without_labels_and_preserves_heldout(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(module, "sample_root", fake_collector(calls))
    before = roster()
    unchanged = deepcopy(before)
    updated, record = module.acquire_allocation(0, "BALANCED", before, None, tmp_path / "allocation", budget=43)
    assert before == unchanged
    assert all(call["key"][1] != 4 for call in calls)
    for query, log in record["queries"].items():
        assert log["used_transitions"] == log["branch_work"]["sampled_transitions"] == 43
        assert log["completed_blocks"] == log["incomplete_blocks"] == 1
        assert log["branch_trajectories"] == 43
        assert sorted(log["training_replica_counts"].values()) == [8, 16]
    assert record["dataset"] == dict(roots=6, training_roots=4, heldout_roots=2, records=24)
    logs = json.loads((tmp_path / "allocation/root_logs.json").read_text())
    assert len(logs) == 4
    for log in logs:
        assert log["resulting_replicas"] == log["original_replicas"] + (8 if log["complete_block"] else 0)
        if not log["complete_block"]:
            assert log["pair_deltas"] == {} and log["ground_work"]["sampled_transitions"] == 3
    assert [r for r in updated if r["episode"] == 4] == [r for r in unchanged if r["episode"] == 4]
    with gzip.open(tmp_path / "allocation/branch_games.jsonl.gz", "rt") as handle:
        raw = [json.loads(line) for line in handle]
    assert len(raw) == 86
    assert sum(item["game"]["work"]["sampled_transitions"] for item in raw) == 86


def test_root_keyed_streams_match_across_arms_and_rotation_breaks_ties(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(module, "sample_root", fake_collector(calls))
    base = roster()
    module.acquire_allocation(1, "BALANCED", base, None, tmp_path / "balanced", budget=85)
    balanced_calls = deepcopy(calls)
    calls.clear()
    module.acquire_allocation(1, "EVIDENCE", base, None, tmp_path / "evidence", budget=85)
    evidence_calls = deepcopy(calls)
    assert balanced_calls[0]["key"][1] == 1  # life + reward index rotates episode 1 first.
    common = {}
    for arm, history in (("BALANCED", balanced_calls), ("EVIDENCE", evidence_calls)):
        attempts = Counter()
        for call in history:
            key = call["key"]
            attempt = attempts[key]
            qi = list(module.QUERIES).index(key[0])
            expected = 89_000_000_000 + 1_000_000_000 + qi * 100_000_000 + key[1] * 100_000 + attempt * 100
            assert call["seed"] == expected
            common.setdefault((key, attempt), {})[arm] = call["seed"]
            attempts[key] += 1
    overlapping = [item for item in common.values() if len(item) == 2]
    assert overlapping and all(item["BALANCED"] == item["EVIDENCE"] for item in overlapping)


def test_schedule_only_changes_after_changed_observed_block(tmp_path, monkeypatch):
    base = roster()
    first_calls, second_calls = [], []
    def values_one(call, root, seed):
        return [[100, 0, 0]] * 8
    def values_two(call, root, seed):
        return [[100, 0, 0]] * 8 if call == 1 else [[-100, 0, 0], [101, 0, 0]] * 4
    monkeypatch.setattr(module, "sample_root", fake_collector(first_calls, values_one))
    module.acquire_allocation(0, "EVIDENCE", base, None, tmp_path / "one", budget=120)
    monkeypatch.setattr(module, "sample_root", fake_collector(second_calls, values_two))
    module.acquire_allocation(0, "EVIDENCE", base, None, tmp_path / "two", budget=120)
    # The second block is selected before its differing observations are available.
    assert first_calls[:2] == second_calls[:2]
    assert first_calls[2]["key"] != second_calls[2]["key"]


def test_confirmation_uses_fixed_training_roster_and_new_streams(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(module, "sample_root", fake_collector(calls))
    before = roster()
    changed = deepcopy(before)
    for item in changed:
        item["n_replicas"] = 999
        item["evidence"] = {option: {"label": 1, "upper": 1e9} for option in module.OPTIONS[1:]}
    unchanged = deepcopy(changed)
    first = module.collect_confirmation(2, before, None, tmp_path / "one")
    initial_calls = deepcopy(calls)
    calls.clear()
    second = module.collect_confirmation(2, changed, None, tmp_path / "two")
    assert calls == initial_calls and changed == unchanged
    assert first["roots"] == second["complete_roots"] == 4
    assert first["incomplete_roots"] == 0 and first["branch_trajectories"] == 160
    assert first["branch_work"]["sampled_transitions"] == 160
    assert all(call["key"][1] != 4 and call["replicas"] == 8 and call["remaining"] == 80000 for call in calls)
    for call in calls:
        query, episode, _ = call["key"]
        qi = list(module.QUERIES).index(query)
        assert call["seed"] == 99_000_000_000 + 2_000_000_000 + qi * 100_000_000 + episode * 100_000
