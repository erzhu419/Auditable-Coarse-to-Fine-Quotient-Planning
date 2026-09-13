"""Single-pass retained-policy evaluation, source binding and missing coverage."""

from copy import deepcopy
import gzip
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from test_controlled_predictive_frozen_policy_v27 import A, numeric_fixture


def _setup(monkeypatch, tmp_path, *, anomaly=None):
    record, oracle = numeric_fixture()
    record["row_order"] = [row["row_key"] for row in record["rows"]]
    record["spent_batches"] = sum(row["batch_count"] for row in record["rows"])
    arms = ["CACHED", "VARIANCE", "FRONTIER", "FRONTIER_VARIANCE"]
    K, initial = 2, record["spent_batches"] - 2
    contexts = [{"context_index": i, "case_name": "toy", "sample_seed": 832101, "query_name": "q",
        "case": {"name": "toy", "horizon": 2, "board": [1]}, "query": record["query"],
        "group": "regression", "target_key": record["root"], "panel": [record["root"]],
        "requested_batch_count": K, "initial_batches": initial, "request_index": 0} for i in range(2)]
    replicates = [{"replicate_index": i, "base_seed": 922001+i} for i in range(2)]
    factorial_plan = {"contexts": contexts, "context_count": 2, "replicates": replicates,
        "replicate_count": 2, "queries": {"q": record["query"]}, "source_query_order": ["q"], "arms": arms}
    endpoints = []
    for repetition in replicates:
        for context in contexts:
            offset = (repetition["replicate_index"] + context["context_index"]) % 4
            identity = {key: value for key, value in context.items() if key not in
                ("case", "query", "target_key", "panel", "requested_batch_count", "initial_batches", "request_index")}
            row = {**repetition, "identity": identity, **{key: context[key] for key in
                ("target_key", "panel", "requested_batch_count", "initial_batches", "request_index")},
                "run_order": arms[offset:] + arms[:offset], "initial_snapshot_validation": {"passed": True},
                "paired_complete": True, "arms": {}}
            for arm in arms:
                row["arms"][arm] = {"state": deepcopy(record), "first_request_validation": {"passed": True},
                    "local": {"arm": arm, "query_name": "q", "target_key": record["root"],
                        "requested_batch_count": K, "completed_batches": K, "completed_fixed_budget": True,
                        "initial_batches": initial, "initial_batches_matches_common": True,
                        "final_batches": initial+K, "actual_draws": K*256, "final_action": "LEFT",
                        "lower": -123., "upper": 456., "unresolved": True, "selected_action_observed": True,
                        "stop_reason": "FIXED_BATCH_BUDGET_COMPLETE",
                        "provider_counts": {"physical_draws": 256*K, "row_requests": K}}}
            endpoints.append(row)
    if anomaly == "identity":
        endpoints[0]["identity"]["context_index"] = 999
    elif anomaly == "local_action":
        endpoints[0]["arms"]["FRONTIER_VARIANCE"]["local"]["final_action"] = "RIGHT"
    elif anomaly == "missing":
        policy = endpoints[0]["arms"]["FRONTIER_VARIANCE"]["state"]["policy_and_intervals"]
        policy[:] = [row for row in policy if row["key"] != [A[0], list(A[1])]]
    endpoint_path, analysis_path, factorial_plan_path = tmp_path / "endpoints.jsonl.gz", tmp_path / "analysis.json", tmp_path / "factorial_plan.json"
    with gzip.open(endpoint_path, "wt") as writer:
        for row in endpoints:
            writer.write(json.dumps(row) + "\n")
    history = {"local_physical_batches": 32, "local_physical_draws": 8192, "local_allocation_wall_seconds": 2.}
    costs = {arm: {"provider_counts": {"physical_draws": 2048}, "whole_run_seconds": .5} for arm in arms}
    analysis = {"stream_statuses": [{**rep, "complete": True, "status": "REPETITION_COMPLETE"} for rep in replicates],
        "complete_stream_count": 2, "all_analysis_checks_passed": anomaly != "global_analysis",
        "accounting": history, "all_actual_arm_costs": costs, "elapsed_seconds_before_report_serialization": 3.,
        "analysis_seconds": .2, "analysis_result_read_seconds": .1}
    factorial_plan_path.write_text(json.dumps(factorial_plan))
    analysis_path.write_text(json.dumps(analysis))
    plan = {**factorial_plan, "source_endpoints": str(endpoint_path), "source_analysis": str(analysis_path),
        "source_factorial_plan": str(factorial_plan_path), "historical_physical_batches": 32,
        "historical_physical_draws": 8192, "expected_quadruplet_count": 4}
    plan_path, output = tmp_path / "plan.json", tmp_path / "policies.json"
    plan_path.write_text(json.dumps(plan))
    script = Path(__file__).resolve().parents[1] / "scripts/run_controlled_predictive_frozen_policy_v27.py"
    spec = importlib.util.spec_from_file_location("v27_runner_test", script)
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    calls, source_reads, small_reads = [], [], []
    def closure(**kwargs):
        calls.append("closure")
        return SimpleNamespace(counts={"toy_truth_rows": len(oracle.rows)})
    def make_oracle(value):
        assert value.counts["toy_truth_rows"] == len(oracle.rows)
        calls.append("oracle")
        return oracle
    monkeypatch.setattr(cli, "build_development_closure", closure)
    monkeypatch.setattr(cli.ExactOracle, "from_closure", staticmethod(make_oracle))
    old_open, old_read_text = gzip.open, Path.read_text
    def tracked_open(path, mode="rb", *args, **kwargs):
        assert Path(path) == endpoint_path and mode == "rt"
        source_reads.append(path)
        return old_open(path, mode, *args, **kwargs)
    def tracked_read(path, *args, **kwargs):
        assert path in (plan_path, factorial_plan_path, analysis_path)
        small_reads.append(path)
        return old_read_text(path, *args, **kwargs)
    monkeypatch.setattr(gzip, "open", tracked_open)
    monkeypatch.setattr(Path, "read_text", tracked_read)
    # These are the actual model/provider entrypoints; none belongs to evaluation.
    from acfqp.science.controlled_predictive_restore_v22 import CachedGapPlannerState
    import acfqp.science.controlled_predictive_restore_v22 as restoration
    from acfqp.science.controlled_predictive_sampling_v15 import BatchRowSampleProvider
    def forbidden(*args, **kwargs):
        raise AssertionError("Frozen policy evaluation cannot restore, solve or sample")
    monkeypatch.setattr(restoration, "restore_state", forbidden)
    monkeypatch.setattr(CachedGapPlannerState, "solve", forbidden)
    monkeypatch.setattr(BatchRowSampleProvider, "__init__", forbidden)
    monkeypatch.setattr(BatchRowSampleProvider, "sample_batch", forbidden)
    return cli, plan_path, output, calls, source_reads, small_reads, analysis


def test_stream_once_keeps_frozen_actions_and_separates_exact_evaluation_from_historical_cost(monkeypatch, tmp_path):
    cli, plan, output, calls, source_reads, small_reads, source = _setup(monkeypatch, tmp_path)
    result, _ = cli.run_frozen_policy(plan, output)
    assert calls == ["closure", "oracle"] and len(source_reads) == 1 and len(small_reads) == 3
    assert result["complete_repetition_count"] == result["source_valid_repetition_count"] == 2
    assert result["source_actual_arm_costs"] == source["all_actual_arm_costs"]
    assert result["source_accounting"] == source["accounting"]
    accounting = result["accounting"]
    assert accounting["source_endpoint_reads"] == 1 and accounting["source_endpoint_records_read"] == 4
    assert accounting["frozen_policy_evaluation_calls"] == 16 and accounting["oracle_instance_count"] == 1
    assert accounting["evaluation_work_counts"]["true_policy_rows_read"] == 48
    assert all(accounting[key] == 0 for key in ("new_sampling_calls", "new_provider_calls", "new_physical_draws",
        "new_physical_batches", "new_replanning_calls", "model_restore_calls"))
    for repetition in result["repetitions"]:
        for context in repetition["contexts"]:
            assert context["source_valid"] and context["policy_evaluable"] and context["paired_complete"]
            for row in context["arms"].values():
                assert row["first_action_validation"]["passed"]
                value = row["evaluation"]
                assert value["initial_action"] == "LEFT" and value["first_action_wrong"]
                assert value["first_action_regret"] == 3.5
                assert value["v_pi"] == 1.5 and value["continuation_regret"] == 1. and value["total_regret"] == 4.5
                assert value["identities_pass"] and value["reach_probability_pass"]


def test_missing_true_reachable_policy_retains_source_first_action_and_all_costs(monkeypatch, tmp_path):
    cli, plan, output, _, _, _, source = _setup(monkeypatch, tmp_path, anomaly="missing")
    result, _ = cli.run_frozen_policy(plan, output)
    assert result["source_valid_repetition_count"] == 2 and result["complete_repetition_count"] == 1
    context = result["repetitions"][0]["contexts"][0]
    row = context["arms"]["FRONTIER_VARIANCE"]
    assert context["source_valid"] and not context["policy_evaluable"] and not context["paired_complete"]
    assert row["first_action_validation"]["passed"] and row["evaluation"]["first_action_regret"] == 3.5
    assert row["evaluation"]["missing_probability"] == .25
    assert row["evaluation"]["v_pi"] is row["evaluation"]["total_regret"] is row["evaluation"]["continuation_regret"] is None
    assert result["source_actual_arm_costs"] == source["all_actual_arm_costs"] and result["source_accounting"] == source["accounting"]


@pytest.mark.parametrize("anomaly", ["identity", "global_analysis", "local_action"])
def test_invalid_source_or_retained_action_never_enters_statistics(monkeypatch, tmp_path, anomaly):
    cli, plan, output, _, _, _, source = _setup(monkeypatch, tmp_path, anomaly=anomaly)
    result, _ = cli.run_frozen_policy(plan, output)
    assert result["source_valid_repetition_count"] == result["complete_repetition_count"] == (0 if anomaly == "global_analysis" else 1)
    first = result["repetitions"][0]
    assert [context["identity"]["context_index"] for context in first["contexts"]] == [0, 1]
    assert not first["contexts"][0]["source_valid"] and not first["complete"]
    if anomaly == "local_action":
        assert not first["contexts"][0]["arms"]["FRONTIER_VARIANCE"]["first_action_validation"]["checks"]["initial_action"]
    elif anomaly == "identity":
        assert first["contexts"][0]["source_validation"]["actual_source_identity"]["identity"]["context_index"] == 999
    else:
        assert not result["plan_binding_validation"]["checks"]["source_analysis_passed"]
    assert result["accounting"]["frozen_policy_evaluation_calls"] == 16
    assert result["source_actual_arm_costs"] == source["all_actual_arm_costs"] and result["source_accounting"] == source["accounting"]
