"""Four paid arms, three retained controls, and complete-group eligibility."""

import gzip
import importlib.util
import json
from pathlib import Path

from test_controlled_predictive_frontier_runner_v24 import _frontier_setup
from acfqp.science.controlled_predictive_frontier_variance_v26 import FrontierVarianceGapPlannerState


def _factorial_setup(monkeypatch, tmp_path):
    cli24, source_plan, source_endpoints, source_output, providers, events, inputs, base, _, _ = _frontier_setup(monkeypatch, tmp_path)
    closure_values = []
    old_closure = cli24.build_development_closure
    def capture_closure(**kwargs):
        closure = old_closure(**kwargs)
        closure_values.append(closure)
        return closure
    monkeypatch.setattr(cli24, "build_development_closure", capture_closure)
    cli24.run_frontier(source_plan, source_endpoints, source_output)
    providers.clear()
    events.clear()
    inputs.clear()
    plan = {**json.loads(source_plan.read_text()), "source_frontier_plan": str(source_plan),
        "source_control_endpoints": str(source_endpoints),
        "arms": ["CACHED", "VARIANCE", "FRONTIER", "FRONTIER_VARIANCE"]}
    plan_path, endpoints, output = tmp_path / "factorial_plan.json", tmp_path / "factorial_endpoints.jsonl.gz", tmp_path / "factorial.json"
    plan_path.write_text(json.dumps(plan))
    script = Path(__file__).resolve().parents[1] / "scripts/run_controlled_predictive_factorial_v26.py"
    spec = importlib.util.spec_from_file_location("v26_runner_test", script)
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    monkeypatch.setattr(cli, "BatchRowSampleProvider", cli24.BatchRowSampleProvider)
    monkeypatch.setattr(cli, "run_local_allocation", cli24.run_local_allocation)
    writers, source_reads = [], []
    old_open = gzip.open
    def tracked_open(path, mode="rb", *args, **kwargs):
        handle = old_open(path, mode, *args, **kwargs)
        if Path(path) == endpoints and mode == "xt":
            writers.append(handle)
        if Path(path) == source_endpoints and mode == "rt":
            source_reads.append(handle)
        return handle
    monkeypatch.setattr(gzip, "open", tracked_open)
    def closure(**kwargs):
        assert len(writers) == 1 and writers[0].closed
        with gzip.open(endpoints, "rt") as reader:
            rows = [json.loads(line) for line in reader]
        assert len(rows) == 4 and all(set(row["arms"]) == set(cli.ARMS) for row in rows)
        assert all("state" in arm for row in rows for arm in row["arms"].values())
        assert len(providers) == 16 and not source_reads
        events.append("truth")
        return closure_values[0]
    monkeypatch.setattr(cli, "build_development_closure", closure)
    return cli, plan_path, endpoints, output, providers, events, inputs, base, source_reads, source_endpoints


def test_four_arms_reset_rotate_and_pay_for_exact_three_control_replays(monkeypatch, tmp_path):
    cli, plan, endpoints, output, providers, events, inputs, base, source_reads, _ = _factorial_setup(monkeypatch, tmp_path)
    report, _ = cli.run_factorial(plan, endpoints, output)
    assert report["complete_repetition_count"] == 2 and report["source_reference_validation"]["all_passed"]
    assert events[-1] == "truth" and events.count("local") == 16 and len(source_reads) == 1
    assert all(counts == tuple(sorted(base.state.batch_counts.items())) and batches == base.state.spent_batches
               for _, _, counts, batches in inputs)
    assert [provider.seed for provider in providers] == [922001]*8 + [922002]*8
    assert len({id(provider) for provider in providers}) == 16
    contexts = [context for rep in report["repetitions"] for context in rep["contexts"]]
    assert [context["run_order"] for context in contexts] == [
        ["CACHED", "VARIANCE", "FRONTIER", "FRONTIER_VARIANCE"],
        ["VARIANCE", "FRONTIER", "FRONTIER_VARIANCE", "CACHED"],
        ["VARIANCE", "FRONTIER", "FRONTIER_VARIANCE", "CACHED"],
        ["FRONTIER", "FRONTIER_VARIANCE", "CACHED", "VARIANCE"]]
    account = report["accounting"]
    assert account["local_arm_run_count"] == account["reset_from_original_common_snapshot_count"] == account["endpoint_states_restored"] == 16
    assert account["endpoint_group_records_written"] == account["endpoint_group_records_reloaded"] == 4
    assert account["local_physical_draws"] == sum(p.work_counts["physical_draws"] for p in providers)
    assert account["warm_provider_calls"] == account["warm_physical_draws"] == 0
    assert providers[0].calls == providers[7].calls
    for arm in cli.REFERENCE_ARMS:
        assert report["source_reference_validation"]["by_arm"][arm] == {"checked": 4, "passed": 4, "failed": 0}
    for context in contexts:
        assert set(context["arms"]) == set(cli.ARMS) and context["paired_complete"]
        for arm, row in context["arms"].items():
            assert row["local"]["completed_batches"] == context["requested_batch_count"]
            assert row["source_reference_validation"]["applicable"] == (arm in cli.REFERENCE_ARMS)
            assert row["first_request_validation"]["applicable"] == (arm in ("CACHED", "VARIANCE"))
            assert row["endpoint_restoration"]["passed"]
            assert all("batch_count" in action and "children" not in action for action in row["evaluation"]["target"]["actions"].values())
    assert report["all_sampling_endpoints_closed_before_oracle"] and not report["endpoint_reload_uses_provider"]


def test_frontier_is_a_full_historical_control_and_mismatch_invalidates_stream(monkeypatch, tmp_path):
    cli, plan, endpoints, output, providers, _, _, _, source_reads, source_path = _factorial_setup(monkeypatch, tmp_path)
    with gzip.open(source_path, "rt") as reader:
        rows = [json.loads(line) for line in reader]
    first = rows[0]["arms"]["FRONTIER"]["local"]["gap_assessments"][0]
    first["separated"] = not first["separated"]
    with gzip.open(source_path, "wt") as writer:
        for row in rows:
            writer.write(json.dumps(row) + "\n")
    source_reads.clear()
    report, _ = cli.run_factorial(plan, endpoints, output)
    first_rep, second_rep = report["repetitions"]
    assert not first_rep["complete"] and second_rep["complete"] and report["complete_repetition_count"] == 1
    context = first_rep["contexts"][0]
    assert context["status"] == "SOURCE_REFERENCE_MISMATCH" and not context["paired_complete"]
    assert not context["arms"]["FRONTIER"]["source_reference_validation"]["checks"]["local.gap_assessments"]
    assert all(context["arms"][arm]["source_reference_validation"]["passed"] for arm in ("CACHED", "VARIANCE"))
    assert all("evaluation" in row and row["local"]["completed_fixed_budget"] for row in context["arms"].values())
    assert report["accounting"]["local_physical_draws"] == sum(p.work_counts["physical_draws"] for p in providers)
    assert len(source_reads) == 1


def test_incomplete_fourth_arm_retains_its_cost_and_all_three_valid_controls(monkeypatch, tmp_path):
    cli, plan, endpoints, output, providers, _, _, _, _, _ = _factorial_setup(monkeypatch, tmp_path)
    original_local, original_resample = cli.run_local_allocation, FrontierVarianceGapPlannerState.select_resample
    def local(snapshot, arm, *args, **kwargs):
        if arm != "FRONTIER_VARIANCE":
            return original_local(snapshot, arm, *args, **kwargs)
        calls = 0
        def resample(state, *selection_args, **selection_kwargs):
            nonlocal calls
            calls += 1
            return original_resample(state, *selection_args, **selection_kwargs) if calls == 1 else None
        with monkeypatch.context() as patch:
            patch.setattr(FrontierVarianceGapPlannerState, "select_row", lambda *args, **kwargs: None)
            patch.setattr(FrontierVarianceGapPlannerState, "select_resample", resample)
            return original_local(snapshot, arm, *args, **kwargs)
    monkeypatch.setattr(cli, "run_local_allocation", local)
    report, _ = cli.run_factorial(plan, endpoints, output)
    assert report["complete_repetition_count"] == 0 and report["source_reference_validation"]["all_passed"]
    for rep in report["repetitions"]:
        for context in rep["contexts"]:
            row = context["arms"]["FRONTIER_VARIANCE"]
            assert context["status"] == "FIXED_BUDGET_INCOMPLETE" and not context["paired_complete"]
            assert row["local"]["completed_batches"] == 1 and row["local"]["stop_reason"] == "NO_ELIGIBLE_CANDIDATE"
            assert "evaluation" in row
    assert report["accounting"]["local_physical_draws"] == sum(p.work_counts["physical_draws"] for p in providers)
    assert report["accounting"]["provider_counts_by_arm"]["FRONTIER_VARIANCE"]["physical_draws"] == 4*256
