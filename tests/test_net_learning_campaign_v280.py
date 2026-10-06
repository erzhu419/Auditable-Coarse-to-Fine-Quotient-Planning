import copy
from fractions import Fraction as F
import gzip
import importlib.util
import itertools
import json
from pathlib import Path
import sys

import pytest

from acfqp.science import net_learning_campaign_v280 as v280
from acfqp.science import query_relevant_coverage_v278 as v278


@pytest.fixture
def synthetic_lifecycle(monkeypatch):
    fields = {"SHORT_PASS": ("road_profile", "retry_service"),
              "DETOUR_PASS": (), "RECOVERY_RETRY": ("retry_service",)}
    streams = {"SHORT_PASS": ["DELIVERY"] * 64,
               "DETOUR_PASS": ["DELIVERY"] * 40 + ["RECOVERY"] * 8 + ["LOST"] * 16,
               "RECOVERY_RETRY": ["DELIVERY"] * 64}
    seen, sampled, accounted = [], [], []
    original_learner = v278.OnlineLearner

    def learner(*args):
        result = original_learner(*args)
        seen.append(result)
        return result

    def execute(context, phase, seed, episode, trial, policy):
        sampled.append((context, phase, episode, trial, policy))
        if policy == "WAIT":
            return []
        if policy == "SHORT":
            return [{"operator": "SHORT_PASS", "outcome": "DELIVERY", "visit": 0}]
        if policy == "DETOUR_RETURN" or trial % 2 == 0:
            return [{"operator": "DETOUR_PASS", "outcome": "LOST", "visit": 0}]
        return [{"operator": "DETOUR_PASS", "outcome": "RECOVERY", "visit": 0},
                {"operator": "RECOVERY_RETRY", "outcome": "LOST", "visit": 1}]

    posterior = {"SHORT_PASS": {"DELIVERY": F(1, 10), "LOST": F(9, 10)},
                 "DETOUR_PASS": {"DELIVERY": F(4, 5), "LOST": F(1, 20), "RECOVERY": F(3, 20)},
                 "RECOVERY_RETRY": {"DELIVERY": F(7, 10), "LOST": F(3, 10)}}

    def exact(*_):
        assert len(sampled) == len(accounted) + 1
        accounted.append(sampled[-1])
        return v278._consequence_vector_dynamic(v278.CASE, posterior)

    for module in (v278, v280):
        monkeypatch.setattr(module, "PHASES", ("A", "B", "A_prime"))
        monkeypatch.setattr(module, "EPISODES_PER_PHASE", 3)
    monkeypatch.setattr(v278, "_stream", lambda *_: streams)
    monkeypatch.setattr(v278, "select_factor_subsets", lambda *_: {"selected_fields": dict(fields)})
    monkeypatch.setattr(v278, "select_online_fields", lambda _c, _s, history: {
        "selected_fields": dict(fields), "online_events_used": len(history)})
    monkeypatch.setattr(v278, "OnlineLearner", learner)
    monkeypatch.setattr(v278, "execute_policy", execute)
    monkeypatch.setattr(v278, "_exact_vectors", exact)
    monkeypatch.setattr(v278, "SCHEDULE", tuple((v278.TARGETS[t % 4], v278.QUERY_SCHEDULE[e % 3])
        for _phase in range(3) for e in range(3) for t in range(8)))
    clock = itertools.count()
    monkeypatch.setattr(v280, "process_time", lambda: next(clock))
    return {"fields": fields, "streams": streams, "learners": seen,
            "original_learner": original_learner}


def test_actual_relevance_and_natural_histories_match_unchanged_v278(synthetic_lifecycle):
    old = v278.run_lifecycle(-1, -1)
    new = v280.run_lifecycle(-1, -1)
    for arm in ("PASSIVE_REVISED", "RELEVANT_REVISED"):
        old_rows = old["arms"][arm]
        assert [{key: row[key] for key in old_rows[0]} for row in new["arms"][arm]] == old_rows
        assert new["selections"][arm] == old["selections"][arm]
        assert new["totals"][arm]["executed_regret"] == old["totals"][arm]["executed_regret"]


def test_local_ignores_source_and_keeps_history_across_switches(synthetic_lifecycle, monkeypatch):
    first = v280.run_lifecycle(-1, -1)
    local = synthetic_lifecycle["learners"][0]
    assert local.source_contexts == () and local.source_streams == {}
    assert local.selected == {op: ("road_profile", "retry_service") for op in v280.OPERATORS}
    rows = first["arms"]["FULL_CONTEXT_LOCAL"]
    first_b = next(row for row in rows if row["phase"] == "B")
    assert first_b["history_before"] == sum(len(row["events"]) for row in rows if row["phase"] == "A") > 0
    assert first["totals"]["FULL_CONTEXT_LOCAL"]["economic_source_observations"] == 0
    changed = {op: ["LOST"] * 64 for op in v280.OPERATORS}
    monkeypatch.setattr(v278, "_stream", lambda *_: changed)
    second = v280.run_lifecycle(-1, -1)
    assert first["arms"]["FULL_CONTEXT_LOCAL"] == second["arms"]["FULL_CONTEXT_LOCAL"]


def test_frozen_commits_events_without_updating_source_predictions(synthetic_lifecycle):
    result = v280.run_lifecycle(-1, -1)
    frozen = synthetic_lifecycle["learners"][1]
    fresh = synthetic_lifecycle["original_learner"]("FROZEN_FACTOR_ONLINE",
        dict(synthetic_lifecycle["fields"]), frozen.source_contexts, frozen.source_streams)
    assert len(frozen.history) == result["totals"]["FROZEN_FACTOR"]["online_events"] > 0
    assert frozen.model(v280.TARGETS[0]) == fresh.model(v280.TARGETS[0])
    assert result["selections"]["FROZEN_FACTOR"] == result["selections"]["FIXED_FACTOR_UPDATE"] == []
    assert result["totals"]["FIXED_FACTOR_UPDATE"]["final_fields"] == synthetic_lifecycle["fields"]


def test_forced_and_failed_reach_costs_and_cpu_scopes_are_billed(synthetic_lifecycle):
    result = v280.run_lifecycle(-1, -1)
    first = result["arms"]["RELEVANT_REVISED"][0]
    assert first["executed_policy"] == "SHORT" and first["forced_override"]
    assert F(first["executed_regret"]) > F(first["recommendation_regret"])
    failed = next(row for row in result["arms"]["PASSIVE_REVISED"]
                  if row["executed_policy"] == "DETOUR_RETRY" and len(row["events"]) == 1)
    assert failed["history_after"] - failed["history_before"] == 1
    assert failed["events"][0]["operator"] == "DETOUR_PASS"
    for arm, rows in result["arms"].items():
        total = result["totals"][arm]
        assert total["start_opportunities"] == len(rows) == 72
        assert total["online_events"] == sum(len(row["events"]) for row in rows)
        assert F(total["executed_regret"]) == sum(F(row["executed_regret"]) for row in rows)
        assert F(total["sampled_utility"]) == sum(F(row["sampled_utility"]) for row in rows)
        assert total["total_economic_observations"] == total["economic_source_observations"] + total["online_events"]
        assert total["source_fit_cost"] == (0 if arm == "FULL_CONTEXT_LOCAL" else 720)
        assert total["source_reserved_cost"] == (0 if arm == "FULL_CONTEXT_LOCAL" else 240)
        cpu = total["cpu_seconds"]
        assert cpu["prediction"] == cpu["execution"] == cpu["oracle_accounting"] == len(rows)
        assert cpu["selection"] == (9 if arm in ("PASSIVE_REVISED", "RELEVANT_REVISED") else 0)
        assert cpu["coverage"] == (len(rows) if arm == "RELEVANT_REVISED" else 0)
    assert result["source_cpu_seconds"] == {"generation": 1, "fit": 1}


@pytest.mark.parametrize("policy,outcomes,expected", [
    ("WAIT", (), (F(0), F(0), F(0))),
    ("SHORT", ("DELIVERY",), (F(-1, 10), F(0), F(1))),
    ("SHORT", ("LOST",), (F(-1, 10), F(1), F(0))),
    ("DETOUR_RETURN", ("RECOVERY",), (F(-1, 20), F(0), F(0))),
    ("DETOUR_RETRY", ("LOST",), (F(-1, 20), F(1), F(0))),
    ("DETOUR_RETRY", ("RECOVERY", "DELIVERY"), (F(-1), F(0), F(1))),
    ("DETOUR_RETRY", ("RECOVERY", "DELAYED"), (F(-3), F(1), F(0))),
])
def test_realized_consequence_uses_only_reached_events(policy, outcomes, expected):
    assert v280.sampled_vector(policy, [{"outcome": outcome} for outcome in outcomes]) == expected


def test_registered_sources_are_unfiltered_and_disjoint():
    assert v280.SOURCE_SEEDS == tuple(28040100 + 100 * i for i in range(128))
    assert v280.SEEDS == tuple(28090100 + 100 * i for i in range(128))
    draws = {seed + offset for seed in v280.SOURCE_SEEDS for offset in range(5)}
    assert len(draws) == 128 * 5
    assert draws.isdisjoint({seed + offset for seed in v278.SOURCE_SEEDS for offset in range(5)})
    assert draws.isdisjoint(v280.SEEDS)


def synthetic_records(base):
    result = []
    for index, actual in enumerate((6, 10, 12)):
        item = copy.deepcopy(base)
        item["source_seed"], item["seed"] = -index - 1, -index - 1
        for arm, total in item["totals"].items():
            total["executed_regret"] = str(actual if arm == "RELEVANT_REVISED" else 10)
            total["recommendation_regret"] = "0"
        result.append(item)
    return result


def test_summary_keeps_all_source_units_and_adverse_executed_regret(synthetic_lifecycle, monkeypatch):
    monkeypatch.setattr(v280, "BOOTSTRAP_DRAWS", 100)
    records = synthetic_records(v280.run_lifecycle(-1, -1))
    result = v280.summarize(records)
    primary = result["contrasts"]["RELEVANT_REVISED_minus_PASSIVE_REVISED"]
    assert primary["per_seed_regret_delta"] == ["-4", "0", "2"]
    assert primary["improved_equal_worse"] == [1, 1, 1]
    assert primary["mean_regret_delta"] == "-2/3"
    assert primary["ci95"][1] > 0
    assert [r["primary_delta"] for r in result["by_source"]] == ["-4", "0", "2"]
    assert result["net_gain_result"] == "NET_GAIN_NOT_SUPPORTED"
    assert result["accounting"]["physical_source_observations"] == 3 * 960
    assert result["accounting"]["start_opportunities_all_arms"] == 3 * 5 * 72
    assert result["accounting"]["online_events_all_arms"] == sum(
        len(row["events"]) for r in records for rows in r["arms"].values() for row in rows)


@pytest.mark.parametrize("uppers,expected", [((-1, -1), "NET_GAIN_SUPPORTED"),
    ((-1, 0), "NET_GAIN_NOT_SUPPORTED"), ((0, -1), "NET_GAIN_NOT_SUPPORTED")])
def test_both_registered_comparisons_must_pass(synthetic_lifecycle, monkeypatch, uppers, expected):
    monkeypatch.setattr(v280, "BOOTSTRAP_DRAWS", 5)
    intervals = iter((*uppers, -1, -1, -1, -1))
    monkeypatch.setattr(v280, "paired_contrast", lambda values: {
        "ci95": [-2, next(intervals)], "per_seed_regret_delta": list(map(str, values))})
    assert v280.summarize(synthetic_records(v280.run_lifecycle(-1, -1)))["net_gain_result"] == expected


def test_runner_retains_complete_traces_and_small_receipt(tmp_path, monkeypatch):
    script = Path(__file__).parents[1] / "scripts" / "run_net_learning_campaign_v280.py"
    spec = importlib.util.spec_from_file_location("run_v280_fixture", script)
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    retained = {"status": "DEVELOPMENT_COMPLETE", "net_gain_result": "NET_GAIN_NOT_SUPPORTED",
                "records": [{"arms": {"RELEVANT_REVISED": [{"executed_regret": "3/2"}]}}],
                "by_source": [{"source_seed": -1, "primary_delta": "3/2"}]}
    monkeypatch.setattr(runner, "run_replication", lambda: retained)
    monkeypatch.setattr(sys, "argv", [str(script), "--output", str(tmp_path)])
    runner.main()
    with gzip.open(tmp_path / "records.json.gz", "rt", encoding="utf-8") as handle:
        assert json.load(handle) == retained
    assert json.loads((tmp_path / "summary.json").read_text(encoding="utf-8")) == {
        key: value for key, value in retained.items() if key != "records"}
    with pytest.raises(SystemExit):
        runner.main()
