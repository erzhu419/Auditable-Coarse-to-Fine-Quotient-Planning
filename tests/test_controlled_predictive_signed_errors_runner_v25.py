"""Pure retained-number input, exact RAW reproduction, and distinct CF validity."""

import builtins
from copy import deepcopy
import gzip
import importlib.util
import json
from pathlib import Path

from test_controlled_predictive_signed_errors_v25 import _refresh_target, _target


def _setup(monkeypatch, tmp_path, *, anomaly=None):
    target = _target({"LEFT": (1., -2., 1.5, 2), "RIGHT": (.9, 0., 0., 2)})
    arms = ["CACHED", "VARIANCE", "FRONTIER"]
    contexts = [{"context_index": index, "case_name": "numeric", "sample_seed": 832101,
        "query_name": target["query_name"], "group": "regression", "source_v20_changed": True,
        "source_old_witness": True, "source_old_group": "regression", "v20_value_difference": -.1,
        "case": {}, "query": {}, "target_key": target["target_key"], "panel": [target["target_key"]],
        "requested_batch_count": 2, "initial_batches": 2, "request_index": 0} for index in range(2)]
    replicates = [{"replicate_index": i, "base_seed": 922001+i} for i in range(2)]
    frontier_plan = {"contexts": contexts, "replicates": replicates, "arms": arms,
        "context_count": 2, "replicate_count": 2, "queries": {"q": {}}, "source_query_order": ["q"]}
    source_reps = []
    for repetition in replicates:
        rows = []
        for fixed in contexts:
            current = {"identity": {key: value for key, value in fixed.items() if key not in
                ("case", "query", "target_key", "panel", "requested_batch_count", "initial_batches", "request_index")},
                **{key: fixed[key] for key in ("target_key", "panel", "requested_batch_count", "initial_batches", "request_index")},
                "initial_snapshot_validation": {"passed": True}, "paired_complete": True, "arms": {}}
            for arm in arms:
                value = deepcopy(target)
                current["arms"][arm] = {"local": {"requested_batch_count": 2, "initial_batches": 2,
                    "completed_batches": 2, "completed_fixed_budget": True, "final_batches": 4, "actual_draws": 512,
                    "initial_batches_matches_common": True, "final_action": value["selected_action"],
                    "lower": value["lower"], "upper": value["upper"]},
                    "endpoint_restoration": {"passed": True}, "first_request_validation": {"passed": True},
                    "source_reference_validation": {"passed": True},
                    "evaluation": {"target": value, "panel": {"large_panel_placeholder": [1, 2, 3]}}}
            rows.append(current)
        source_reps.append({**repetition, "complete": True, "contexts": rows})
    if anomaly == "identity":
        source_reps[0]["contexts"][0]["identity"]["context_index"] = 999
    elif anomaly == "unknown":
        source_arm = source_reps[0]["contexts"][0]["arms"]["FRONTIER"]
        unknown = source_arm["evaluation"]["target"]["actions"]["RIGHT"]
        unknown.update(observed=False, q_hat=None, q_hat_exact_continuation=None, A_transition_error=None,
            D_continuation_error=None, total_error=None, identity_residual=None, batch_count=0, lower=.8, upper=2.)
        value = _refresh_target(source_arm["evaluation"]["target"]["actions"])
        source_arm["evaluation"]["target"] = value
        source_arm["local"].update(final_action=value["selected_action"], lower=value["lower"], upper=value["upper"])
    source_account = {"local_physical_batches": 24, "local_physical_draws": 6144, "local_allocation_wall_seconds": 3.}
    costs = {arm: {"actual_arm_count": 4, "provider_counts": {"physical_draws": 2048}, "whole_run_seconds": 1.} for arm in arms}
    source = {"plan": frontier_plan, "repetitions": source_reps, "complete_repetition_count": 2,
        "accounting": source_account, "elapsed_seconds_before_report_serialization": 4.}
    reference = {"accounting": source_account, "complete_stream_count": 2, "all_actual_arm_costs": costs,
        "analysis_seconds": .2, "analysis_result_read_seconds": .1}
    source_path, reference_path, source_plan_path = tmp_path / "source.json", tmp_path / "reference.json", tmp_path / "frontier_plan.json"
    for path, payload in ((source_path, source), (reference_path, reference), (source_plan_path, frontier_plan)):
        path.write_text(json.dumps(payload))
    plan = {**frontier_plan, "source_result": str(source_path), "source_analysis": str(reference_path),
        "source_frontier_plan": str(source_plan_path), "historical_physical_batches": 24,
        "historical_physical_draws": 6144, "modes": ["RAW", "REMOVE_A", "REMOVE_D"]}
    plan_path, output = tmp_path / "plan.json", tmp_path / "diagnosis.json"
    plan_path.write_text(json.dumps(plan))
    reads = []
    original_read_text = Path.read_text
    def read_text(path, *args, **kwargs):
        reads.append(path)
        return original_read_text(path, *args, **kwargs)
    monkeypatch.setattr(Path, "read_text", read_text)
    def forbidden(*args, **kwargs):
        raise AssertionError("Numeric diagnosis must not read retained models")
    monkeypatch.setattr(gzip, "open", forbidden)
    original_import = builtins.__import__
    def numeric_import(name, *args, **kwargs):
        assert not any(value in name for value in ("controlled_predictive_restore", "controlled_predictive_sampling",
            "controlled_predictive_local_v21", "controlled_predictive_decomposition", "controlled_predictive_2048")), name
        return original_import(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", numeric_import)
    script = Path(__file__).resolve().parents[1] / "scripts/run_controlled_predictive_signed_errors_v25.py"
    spec = importlib.util.spec_from_file_location("v25_runner_test", script)
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    return cli, plan_path, output, source_path, reads, source, reference


def test_retained_numbers_read_once_reproduce_raw_without_any_model_calls(monkeypatch, tmp_path):
    cli, plan, output, source_path, reads, source, reference = _setup(monkeypatch, tmp_path)
    result, _ = cli.run_signed_errors(plan, output)
    assert reads.count(source_path) == 1 and len(reads) == 4
    assert result["raw_complete_repetition_count"] == result["complete_repetition_count"] == 2
    assert result["source_accounting"] == source["accounting"]
    assert result["source_actual_arm_costs"] == reference["all_actual_arm_costs"]
    accounting = result["accounting"]
    assert accounting["targets_diagnosed"] == 12
    assert accounting["diagnostic_work_counts"] == {"action_records_processed": 24, "pair_records_processed": 12}
    assert all(accounting[key] == 0 for key in ("new_provider_calls", "new_oracle_calls", "new_physical_draws", "model_restore_calls", "source_endpoint_reads"))
    for rep in result["repetitions"]:
        for context in rep["contexts"]:
            assert context["raw_valid"] and context["paired_complete"]
            assert "panel" not in context
            for row in context["arms"].values():
                assert row["raw_reproduction_validation"]["passed"]
                raw = row["diagnostic"]["modes"]["RAW"]
                assert raw["selected_action"] == row["source_target"]["selected_action"] == "RIGHT"
                assert raw["wrong"] and raw["regret"] == row["source_target"]["local_regret"]
                assert set(row["diagnostic"]["modes"]) == {"RAW", "REMOVE_A", "REMOVE_D"}
                assert row["diagnostic"]["modes"]["REMOVE_A"]["raw_wrong_repaired"]


def test_source_identity_mismatch_keeps_numeric_diagnosis_but_invalidates_stream(monkeypatch, tmp_path):
    cli, plan, output, _, _, source, reference = _setup(monkeypatch, tmp_path, anomaly="identity")
    result, _ = cli.run_signed_errors(plan, output)
    first, second = result["repetitions"]
    assert not first["raw_complete"] and not first["complete"] and second["complete"]
    assert [context["identity"]["context_index"] for context in first["contexts"]] == [0, 1]
    bad = first["contexts"][0]
    assert bad["source_validation"]["actual_source_identity"]["context_index"] == 999
    assert not bad["raw_valid"] and not bad["paired_complete"]
    assert all(row["diagnostic_validation"]["passed"] and not row["raw_valid"] for row in bad["arms"].values())
    assert result["source_accounting"] == source["accounting"] and result["source_actual_arm_costs"] == reference["all_actual_arm_costs"]


def test_one_unknown_action_preserves_raw_but_disables_both_whole_target_corrections(monkeypatch, tmp_path):
    cli, plan, output, _, _, source, reference = _setup(monkeypatch, tmp_path, anomaly="unknown")
    result, _ = cli.run_signed_errors(plan, output)
    assert result["raw_complete_repetition_count"] == 2 and result["complete_repetition_count"] == 1
    first = result["repetitions"][0]
    target = first["contexts"][0]["arms"]["FRONTIER"]
    assert first["raw_complete"] and not first["complete"] and target["raw_valid"]
    assert target["diagnostic"]["modes"]["RAW"]["selected_action"] == "RIGHT"
    assert len(target["diagnostic"]["actions"]) == 2
    for mode in ("REMOVE_A", "REMOVE_D"):
        corrected = target["diagnostic"]["modes"][mode]
        assert not corrected["available"] and corrected["selected_action"] is None and corrected["regret"] is None
    assert result["source_accounting"] == source["accounting"] and result["source_actual_arm_costs"] == reference["all_actual_arm_costs"]
