"""Retained-prefix joining, single evaluation, and unchanged endpoint evidence."""

from collections import Counter
import gzip
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from test_controlled_predictive_new_starts_runner_v28 import _setup
from test_controlled_predictive_new_starts_v28 import A
from acfqp.science.controlled_predictive_decomposition_v19 import ExactOracle
from acfqp.science.controlled_predictive_score_cache_v18 import CachedGapPlannerState
from acfqp.science import controlled_predictive_restore_v22 as restoration
from acfqp.science import controlled_predictive_sampling_v15 as sampling


def _retained_fixture(monkeypatch, tmp_path, mutation=None):
    cli28, source_plan, prefixes, endpoints, result, _, _, _, _ = _setup(monkeypatch, tmp_path)
    source, _ = cli28.run_new_starts(source_plan, prefixes, endpoints, result)
    source = json.loads(json.dumps(source))
    oracle28 = cli28.ExactOracle.from_closure(None)
    oracle = ExactOracle(oracle28.statuses, oracle28.rows)
    with gzip.open(prefixes, "rt") as reader:
        retained = json.load(reader)
    if mutation:
        mutation(retained)
        with gzip.open(prefixes, "wt") as writer:
            json.dump(retained, writer)
    reference = {"all_analysis_checks_passed": True, "accounting": source["accounting"],
        "source_valid_stream_count": source["source_valid_repetition_count"],
        "quality_complete_stream_count": source["complete_repetition_count"],
        "all_actual_arm_costs": {"retained_actual_provider_counts": source["accounting"]["provider_counts_by_arm"]},
        "analysis_seconds": .25, "analysis_result_read_seconds": .125}
    analysis = tmp_path / "analysis28.json"
    analysis.write_text(json.dumps(reference))
    plan = {**source["plan"], "source_plan": str(source_plan), "source_prefixes": str(prefixes),
        "source_endpoints_result": str(result), "source_analysis": str(analysis),
        "historical_physical_batches": source["accounting"]["total_physical_batches"],
        "historical_physical_draws": source["accounting"]["total_physical_draws"],
        "expected_prefix_evaluations": 2, "baseline": "PREFIX"}
    plan_path, output = tmp_path / "plan29.json", tmp_path / "result29.json.gz"
    plan_path.write_text(json.dumps(plan))
    script = Path(__file__).resolve().parents[1] / "scripts/run_controlled_predictive_prefix_baseline_v29.py"
    spec = importlib.util.spec_from_file_location("v29_runner_test", script)
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    events, reads, evaluations = [], Counter(), []
    old_gzip, old_text = gzip.open, Path.read_text
    def tracked_gzip(path, mode="rb", *args, **kwargs):
        assert Path(path) != endpoints, "V29 must not read retained large endpoints"
        if mode == "rt":
            reads[Path(path)] += 1
        return old_gzip(path, mode, *args, **kwargs)
    def tracked_text(path, *args, **kwargs):
        reads[path] += 1
        return old_text(path, *args, **kwargs)
    monkeypatch.setattr(gzip, "open", tracked_gzip)
    monkeypatch.setattr(Path, "read_text", tracked_text)
    old_validation = cli._prefix_validation
    def validate(*args):
        assert "oracle" not in events
        events.append("bind")
        return old_validation(*args)
    monkeypatch.setattr(cli, "_prefix_validation", validate)
    def closure(**kwargs):
        assert events == ["bind", "bind"]
        assert reads == Counter({plan_path: 1, source_plan: 1, prefixes: 1, result: 1, analysis: 1})
        events.append("oracle")
        return SimpleNamespace(counts={"toy_rows": len(oracle.rows)})
    monkeypatch.setattr(cli, "build_development_closure", closure)
    monkeypatch.setattr(cli.ExactOracle, "from_closure", staticmethod(lambda closure: oracle))
    old_evaluate = cli.evaluate_frozen_policy
    def evaluate(state, *args):
        assert events[-1] == "oracle" and state["spent_batches"] == 32
        evaluations.append(state)
        return old_evaluate(state, *args)
    monkeypatch.setattr(cli, "evaluate_frozen_policy", evaluate)
    def forbidden(*args, **kwargs):
        raise AssertionError("V29 must not sample, restore, prepare or solve a planner")
    monkeypatch.setattr(sampling.BatchRowSampleProvider, "__init__", forbidden)
    monkeypatch.setattr(sampling.BatchRowSampleProvider, "sample_batch", forbidden)
    monkeypatch.setattr(restoration, "restore_state", forbidden)
    monkeypatch.setattr(CachedGapPlannerState, "__init__", forbidden)
    monkeypatch.setattr(CachedGapPlannerState, "solve", forbidden)
    return cli, plan_path, output, source, reference, reads, evaluations, events


def _assert_source_unchanged(report, source, reference):
    assert report["source_accounting"] == source["accounting"] == reference["accounting"]
    assert report["source_actual_costs"] == reference["all_actual_arm_costs"]
    for actual, old in zip(report["repetitions"], source["repetitions"]):
        assert {key: value for key, value in actual.items() if key not in ("contexts", "comparison_source_valid", "comparison_complete")} == {
            key: value for key, value in old.items() if key != "contexts"}
        for context, original in zip(actual["contexts"], old["contexts"]):
            assert {key: context[key] for key in original} == original
            assert context["prefix_context_index"] == original["identity"]["context_index"]


def test_prefix_evaluated_once_without_execution_and_original_endpoints_reused(monkeypatch, tmp_path):
    cli, plan, output, source, reference, reads, evaluations, events = _retained_fixture(monkeypatch, tmp_path)
    report, serialization = cli.run_prefix_baseline(plan, output)
    assert report["plan_binding_validation"]["passed"]
    assert report["comparison_source_valid_repetition_count"] == report["comparison_complete_repetition_count"] == 2
    assert len(evaluations) == len(report["prefix_baselines"]) == 2 and events == ["bind", "bind", "oracle"]
    assert all(count == 1 for count in reads.values()) and serialization["report_bytes"] > 0
    account = report["accounting"]
    assert account["prefix_policy_evaluation_calls"] == 2
    assert all(account[field] == 0 for field in ("new_sampling_calls", "new_physical_draws", "new_physical_batches",
        "new_planner_solves", "new_model_restores", "endpoint_evaluation_calls"))
    assert account["historical_physical_draws"] == source["accounting"]["total_physical_draws"]
    assert report["all_prefix_policies_bound_before_oracle"] and report["endpoint_evaluations_reused_without_recalculation"]
    for baseline in report["prefix_baselines"]:
        index = baseline["context_index"]
        assert baseline["source_valid"] and baseline["first_action_validation"]["passed"] and baseline["evaluation_validation"]["passed"]
        assert baseline["costs"]["independent_query_seconds"] == source["prefixes"][0]["accounting"]["whole_seconds"] + source["query_preparations"][index]["accounting"]["whole_seconds"]
    _assert_source_unchanged(report, source, reference)


def test_missing_prefix_continuation_keeps_costs_and_original_quality_masks(monkeypatch, tmp_path):
    def remove_continuation(retained):
        key = [A[0], list(A[1])]
        rows = retained["query_starts"][0]["state"]["policy_and_intervals"]
        rows[:] = [row for row in rows if row["key"] != key]
    cli, plan, output, source, reference, _, evaluations, _ = _retained_fixture(monkeypatch, tmp_path, remove_continuation)
    report, _ = cli.run_prefix_baseline(plan, output)
    baseline = report["prefix_baselines"][0]
    assert baseline["source_valid"] and baseline["first_action_validation"]["passed"] and baseline["evaluation_validation"]["passed"]
    assert not baseline["policy_evaluable"] and baseline["evaluation"]["missing_probability"] == .5
    assert baseline["evaluation"]["v_pi"] is baseline["evaluation"]["total_regret"] is baseline["evaluation"]["continuation_regret"] is None
    assert report["comparison_source_valid_repetition_count"] == 2 and report["comparison_complete_repetition_count"] == 0
    assert all(rep["complete"] for rep in report["repetitions"]) and len(evaluations) == 2
    _assert_source_unchanged(report, source, reference)


@pytest.mark.parametrize("failure", ["identity", "evaluator"])
def test_binding_or_evaluator_failure_retains_expected_identity_and_all_source_costs(monkeypatch, tmp_path, failure):
    def wrong_identity(retained):
        retained["query_starts"][0]["identity"]["context_index"] = 99
    cli, plan, output, source, reference, _, _, _ = _retained_fixture(monkeypatch, tmp_path, wrong_identity if failure == "identity" else None)
    if failure == "evaluator":
        original = cli.evaluate_frozen_policy
        def fail_first(state, target, query, oracle):
            if query.failure_penalty == 0:
                raise ValueError("inconsistent stored policy")
            return original(state, target, query, oracle)
        monkeypatch.setattr(cli, "evaluate_frozen_policy", fail_first)
    report, _ = cli.run_prefix_baseline(plan, output)
    baseline = report["prefix_baselines"][0]
    assert baseline["context_index"] == baseline["identity"]["context_index"] == 0
    assert baseline["source_valid"] == (failure == "evaluator")
    assert baseline["evaluation_validation"]["passed"] == (failure == "identity")
    assert baseline["costs"]["independent_query_seconds"] > 0
    assert report["comparison_complete_repetition_count"] == 0
    assert report["comparison_source_valid_repetition_count"] == (2 if failure == "evaluator" else 0)
    _assert_source_unchanged(report, source, reference)
