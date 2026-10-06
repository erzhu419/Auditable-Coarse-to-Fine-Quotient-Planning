import gzip
import importlib.util
import json
from fractions import Fraction as F
from pathlib import Path
import sys

import pytest

from acfqp.science import online_factor_confirmation_v277 as v277
from acfqp.science import online_factor_repair_v276 as v276


def test_fresh_source_rng_sets_are_disjoint_and_fixed_before_sampling():
    assert v277.SOURCE_SEEDS == tuple(27740100 + 100 * i for i in range(32))
    assert v277.SEEDS == tuple(27790100 + 100 * i for i in range(32))
    groups = [
        {seed + index for index in range(len(v277.SOURCE_PAIRS))}
        for seed in v277.SOURCE_SEEDS
    ]
    combined = set().union(*groups)
    assert len(combined) == 32 * len(v277.SOURCE_PAIRS)
    development = {
        seed + index
        for seed in v276.SOURCE_SEEDS
        for index in range(len(v277.SOURCE_PAIRS))
    }
    assert combined.isdisjoint(development)
    assert combined.isdisjoint(v277.SEEDS)


def test_new_target_opportunity_keys_do_not_reuse_source_or_development_rng():
    targets = v276._contexts(v276.TARGET_PAIRS, "target")

    def keys(seeds):
        return [
            v276.sampling_key(seed, targets[trial % len(targets)], phase,
                              episode, trial, visit, operator)
            for seed in seeds
            for phase in v276.PHASES
            for episode in range(1, v276.EPISODES_PER_PHASE + 1)
            for trial in range(v276.TRIALS_PER_EPISODE)
            for visit, operator in ((0, "SHORT_PASS"), (0, "DETOUR_PASS"),
                                    (1, "RECOVERY_RETRY"))
        ]

    target_keys = keys(v277.SEEDS)
    source_keys = {
        seed + index
        for seed in v277.SOURCE_SEEDS
        for index in range(len(v277.SOURCE_PAIRS))
    }
    assert len(target_keys) == len(set(target_keys))
    assert set(target_keys).isdisjoint(source_keys)
    assert set(target_keys).isdisjoint(keys(v276.SEEDS))


def test_confirmation_imports_the_exact_development_lifecycle():
    assert v277.run_lifecycle is v276.run_lifecycle
    assert v277.ARMS == v276.ARMS
    assert v277.COVERAGE_QUOTA == v276.COVERAGE_QUOTA == 4


def test_paired_contrast_keeps_improved_equal_and_adverse_lifecycles():
    values = [F(-4), F(0), F(2)]
    result = v277.paired_contrast(values)
    assert result["per_seed_regret_delta"] == ["-4", "0", "2"]
    assert result["mean_regret_delta"] == "-2/3"
    assert result["improved_equal_worse"] == [1, 1, 1]
    assert result["ci95"][0] <= float(F(-2, 3)) <= result["ci95"][1]
    assert result["ci95"][1] > 0
    assert result == v277.paired_contrast(values)


def fixture_records():
    records = []
    for index, repaired in enumerate((6, 10, 12)):
        totals, arms = {}, {}
        for arm in v277.ARMS:
            actual = repaired if arm == "COVERED_REVISED" else 10
            totals[arm] = {
                "executed_regret": str(actual),
                "recommendation_regret": "0",
                "phases": {
                    phase: {"executed_regret": str(F(actual, 3)),
                            "executed_events": index + 1,
                            "coverage_opportunities": index}
                    for phase in v277.PHASES
                },
            }
            # Unequal trace lengths must not turn trials into bootstrap units.
            arms[arm] = [{"events": [{"operator": "SHORT_PASS"}]}
                         for _ in range(3 * (index + 1))]
        records.append({"source_seed": v277.SOURCE_SEEDS[index],
                        "seed": v277.SEEDS[index],
                        "initial_selection": {"selected_fields": {}},
                        "totals": totals, "arms": arms})
    return records


def test_summary_uses_all_source_units_and_actual_execution_regret(monkeypatch):
    calls = []
    paired = v277.paired_contrast

    def retain_units(values):
        calls.append(values)
        return paired(values)

    monkeypatch.setattr(v277, "paired_contrast", retain_units)
    result = v277.summarize(fixture_records())
    assert len(calls) == len(v277.CONTRASTS)
    assert all(len(values) == 3 for values in calls)
    assert calls[0] == [F(-4), F(0), F(2)]
    assert result["summary"]["COVERED_REVISED"]["mean_executed_regret"] == "28/3"
    assert result["summary"]["PASSIVE_FIXED"]["mean_executed_regret"] == "10"
    assert result["summary"]["COVERED_REVISED"]["mean_online_events"] == 6
    assert result["summary"]["COVERED_REVISED"]["mean_coverage_opportunities"] == 3
    assert [source["primary_regret_delta"] for source in result["by_source"]] == ["-4", "0", "2"]
    assert result["confirmation"] == "NOT_CONFIRMED_ON_COHORT"
    assert result["accounting"]["physical_source_observations"] == 3 * 960
    assert result["accounting"]["online_events_all_arms"] == 72
    assert result["accounting"]["start_opportunities_all_arms"] == 3 * 4 * 288


@pytest.mark.parametrize("upper, expected", [(-0.001, "CONFIRMED_ON_COHORT"),
                                           (0.0, "NOT_CONFIRMED_ON_COHORT")])
def test_primary_confirmation_requires_strictly_negative_interval(monkeypatch, upper, expected):
    monkeypatch.setattr(v277, "paired_contrast", lambda values: {
        "per_seed_regret_delta": list(map(str, values)), "ci95": [-1.0, upper],
    })
    assert v277.summarize(fixture_records())["confirmation"] == expected


def test_mocked_runner_preserves_full_traces_and_compact_receipt(tmp_path, monkeypatch):
    script = Path(__file__).parents[1] / "scripts" / "run_online_factor_confirmation_v277.py"
    spec = importlib.util.spec_from_file_location("run_v277_fixture", script)
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    result = {"status": "DEVELOPMENT_COMPLETE", "confirmation": "NOT_CONFIRMED_ON_COHORT",
              "records": [{"seed": 1, "arms": {"COVERED_REVISED": [{"executed_regret": "3/2"}]}}],
              "by_source": [{"seed": 1, "primary_regret_delta": "1/2"}]}
    monkeypatch.setattr(runner, "run_replication", lambda: result)
    monkeypatch.setattr(sys, "argv", [str(script), "--output", str(tmp_path)])
    runner.main()
    with gzip.open(tmp_path / "records.json.gz", "rt", encoding="utf-8") as handle:
        assert json.load(handle) == result
    summary = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    assert summary == {key: value for key, value in result.items() if key != "records"}
