"""Streaming projection order, exact source control, and retained invalid pairs."""

import gzip
import importlib.util
import json
from pathlib import Path

import pytest

from test_controlled_predictive_repetitions_v22 import _setup
from acfqp.science.controlled_predictive_sampling_v15 import BatchRowSampleProvider


def _rewrite(path, change):
    with gzip.open(path, "rt") as reader:
        records = [json.loads(line) for line in reader]
    change(records)
    with gzip.open(path, "wt") as writer:
        for record in records:
            writer.write(json.dumps(record) + "\n")


def _projection_setup(monkeypatch, tmp_path, *, anomaly=None):
    cli22, source_plan_path, source_endpoints, source_output, providers, events, _, _ = _setup(
        monkeypatch, tmp_path, contexts=2, repetitions=1)
    source_report, _ = cli22.run_repetitions(source_plan_path, source_endpoints, source_output)
    source_plan = json.loads(source_plan_path.read_text())
    with gzip.open(source_plan["source_common_snapshots"], "rt") as reader:
        common = json.load(reader)
    contexts = [{**context, "initial_row_keys": record["state"]["row_order"],
        "initial_observed_row_count": len(record["state"]["rows"])}
        for context, record in zip(source_plan["contexts"], common["snapshots"])]
    costs = {arm: {"provider_counts": values, "charged_source": True}
             for arm, values in source_report["accounting"]["provider_counts_by_arm"].items()}
    reference_path = tmp_path / "source_analysis.json"
    reference_path.write_text(json.dumps({"all_actual_arm_costs": costs, "accounting": source_report["accounting"]}))
    plan = {**source_plan, "contexts": contexts, "source_repetition_plan": str(source_plan_path),
        "source_repetition_endpoints": str(source_endpoints), "source_repetition_analysis": str(reference_path),
        "source_physical_batches": source_report["accounting"]["local_physical_batches"],
        "source_physical_draws": source_report["accounting"]["local_physical_draws"]}
    plan_path, endpoints, output = tmp_path / "projection_plan.json", tmp_path / "projected.jsonl.gz", tmp_path / "projection.json"
    plan_path.write_text(json.dumps(plan))
    script = Path(__file__).resolve().parents[1] / "scripts/run_controlled_predictive_projection_v23.py"
    spec = importlib.util.spec_from_file_location("v23_runner_test", script)
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    opened = []
    original_open = gzip.open
    def tracked_open(path, mode="rb", *args, **kwargs):
        handle = original_open(path, mode, *args, **kwargs)
        if Path(path) == endpoints and mode == "xt":
            opened.append(handle)
        return handle
    monkeypatch.setattr(gzip, "open", tracked_open)
    def closure(**kwargs):
        assert len(opened) == 1 and opened[0].closed
        with gzip.open(endpoints, "rt") as reader:
            records = [json.loads(line) for line in reader]
        assert len(records) == 2
        if anomaly != "source_identity":
            assert all("state" in row for pair in records for row in pair["arms"].values())
        assert all("source_local" not in row and "local" not in row for pair in records for row in pair["arms"].values())
        events.append("all_projected_closed")
        if anomaly == "projected_identity":
            _rewrite(endpoints, lambda rows: rows[0]["identity"].update(context_index=999))
        return cli22.build_development_closure(**kwargs)
    monkeypatch.setattr(cli, "build_development_closure", closure)
    def forbidden_provider(*args, **kwargs):
        raise AssertionError("V23 must not construct or call a sampling provider")
    monkeypatch.setattr(BatchRowSampleProvider, "__init__", forbidden_provider)
    monkeypatch.setattr(BatchRowSampleProvider, "sample_batch", forbidden_provider)
    if anomaly == "source_identity":
        _rewrite(source_endpoints, lambda rows: rows[0]["identity"].update(context_index=999))
    elif anomaly == "full_control":
        _rewrite(source_endpoints, lambda rows: rows[0]["arms"]["CACHED"]["local"].update(final_action="CHANGED"))
    return cli, plan_path, endpoints, output, costs, providers, events


def test_projection_closes_all_models_before_truth_preserves_full_control_and_paid_cost(monkeypatch, tmp_path):
    cli, plan, endpoints, output, costs, providers, events = _projection_setup(monkeypatch, tmp_path)
    report, _ = cli.run_projection(plan, endpoints, output)
    assert report["complete_repetition_count"] == 1
    assert events[-2:] == ["all_projected_closed", "truth"] and len(providers) == 4
    assert report["all_projected_endpoints_closed_before_oracle"]
    assert report["new_provider_calls"] == report["new_physical_draws"] == 0
    assert report["source_actual_arm_costs"] == costs
    account = report["accounting"]
    assert account["source_first_read_records"] == account["source_second_read_records"] == account["projected_reload_read_records"] == 2
    assert account["source_states_restored_for_projection"] == account["projected_states_written"] == 4
    assert account["full_evaluation_states_restored"] == account["projected_evaluation_states_restored"] == 4
    assert account["source_physical_draws"] == sum(provider.work_counts["physical_draws"] for provider in providers)
    for context in report["repetitions"][0]["contexts"]:
        assert context["source_alignment_validation"]["passed"] and context["projected_alignment_validation"]["passed"]
        for row in context["arms"].values():
            assert row["projection_validation"]["passed"] and row["full_control_validation"]["passed"]
            assert all(row["evaluation_restoration"][model]["passed"] for model in cli.MODELS)
            assert not any(field in row["source_local"] for field in cli.TRACE_FIELDS)
            assert row["projection"]["original_acquisition_cost_refunded"] is False
            # The toy has already observed all rows; information projection is exact.
            assert row["projection"]["masked_new_row_count"] == 0
            full, projected = row["evaluations"]["FULL"]["target"], row["evaluations"]["PROJECTED"]["target"]
            for field in ("selected_action", "lower", "upper", "local_regret", "actions", "pair_margins"):
                assert full[field] == projected[field]
            assert all("children" not in action for action in full["actions"].values())
    assert json.loads(output.read_text())["complete_repetition_count"] == 1


@pytest.mark.parametrize("anomaly", ["source_identity", "projected_identity", "full_control"])
def test_misaligned_or_changed_control_retains_expected_identity_cost_and_invalid_stream(monkeypatch, tmp_path, anomaly):
    cli, plan, endpoints, output, costs, _, _ = _projection_setup(monkeypatch, tmp_path, anomaly=anomaly)
    report, _ = cli.run_projection(plan, endpoints, output)
    repetition = report["repetitions"][0]
    first, second = repetition["contexts"]
    assert [row["identity"]["context_index"] for row in repetition["contexts"]] == [0, 1]
    assert not first["paired_complete"] and second["paired_complete"]
    assert not repetition["complete"] and report["complete_repetition_count"] == 0
    assert report["source_actual_arm_costs"] == costs
    assert all("source_local" in arm for arm in first["arms"].values())
    if anomaly == "full_control":
        assert first["arms"]["CACHED"]["full_control_validation"]["checks"]["selected_action"] is False
        assert all(model in first["arms"]["CACHED"]["evaluations"] for model in cli.MODELS)
    else:
        field = "source_alignment_validation" if anomaly == "source_identity" else "projected_alignment_validation"
        assert first[field]["passed"] is False
        assert first[field]["actual_source_identity"]["identity"]["context_index"] == 999
        assert all(not row["projection_validation"]["passed"] for row in first["arms"].values())
    assert report["accounting"]["new_provider_calls"] == report["accounting"]["new_physical_draws"] == 0
