"""Three paid arms, retained old traces, frozen evidence order and partial costs."""

from copy import deepcopy
import gzip
import importlib.util
import json
from pathlib import Path

from test_controlled_predictive_repetitions_v22 import _setup
from acfqp.science.controlled_predictive_frontier_v24 import FrontierGapPlannerState


def _frontier_setup(monkeypatch, tmp_path):
    cli22, source_plan, source_endpoints, source_output, providers, events, inputs, base = _setup(monkeypatch, tmp_path)
    cli22.run_repetitions(source_plan, source_endpoints, source_output)
    exact_closure = cli22.build_development_closure()
    providers.clear()
    events.clear()
    inputs.clear()
    source_plan_data = json.loads(source_plan.read_text())
    plan = {**source_plan_data, "source_repetition_plan": str(source_plan),
        "source_control_endpoints": str(source_endpoints), "arms": ["CACHED", "VARIANCE", "FRONTIER"]}
    plan_path, endpoints, output = tmp_path / "frontier_plan.json", tmp_path / "frontier_endpoints.jsonl.gz", tmp_path / "frontier.json"
    plan_path.write_text(json.dumps(plan))
    scripts = Path(__file__).resolve().parents[1] / "scripts"
    monkeypatch.syspath_prepend(str(scripts))
    spec = importlib.util.spec_from_file_location("v24_runner_test", scripts / "run_controlled_predictive_frontier_v24.py")
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    monkeypatch.setattr(cli, "BatchRowSampleProvider", cli22.BatchRowSampleProvider)
    monkeypatch.setattr(cli, "run_local_allocation", cli22.run_local_allocation)
    opened_writers, source_reads = [], []
    original_open = gzip.open
    def tracked_open(path, mode="rb", *args, **kwargs):
        handle = original_open(path, mode, *args, **kwargs)
        if Path(path) == endpoints and mode == "xt":
            opened_writers.append(handle)
        if Path(path) == source_endpoints and mode == "rt":
            source_reads.append(handle)
        return handle
    monkeypatch.setattr(gzip, "open", tracked_open)
    def closure(**kwargs):
        assert len(opened_writers) == 1 and opened_writers[0].closed
        with gzip.open(endpoints, "rt") as reader:
            rows = [json.loads(line) for line in reader]
        assert len(rows) == 4 and all(set(row["arms"]) == set(cli.ARMS) for row in rows)
        assert len(providers) == 12 and not source_reads
        assert all("state" in arm for row in rows for arm in row["arms"].values())
        events.append("truth")
        return exact_closure
    monkeypatch.setattr(cli, "build_development_closure", closure)
    return cli, plan_path, endpoints, output, providers, events, inputs, base, source_reads, source_endpoints


def test_three_arms_reset_rotate_and_physically_replay_old_controls_before_evaluation(monkeypatch, tmp_path):
    cli, plan, endpoints, output, providers, events, inputs, base, source_reads, _ = _frontier_setup(monkeypatch, tmp_path)
    report, _ = cli.run_frontier(plan, endpoints, output)
    assert report["complete_repetition_count"] == 2 and report["source_reference_validation"]["all_passed"]
    assert events[-1] == "truth" and events.count("local") == 12 and len(source_reads) == 1
    assert all(counts == tuple(sorted(base.state.batch_counts.items())) and batches == base.state.spent_batches
               for _, _, counts, batches in inputs)
    assert [provider.seed for provider in providers] == [922001]*6 + [922002]*6
    assert len({id(provider) for provider in providers}) == 12
    contexts = [context for repetition in report["repetitions"] for context in repetition["contexts"]]
    assert [context["run_order"] for context in contexts] == [
        ["CACHED", "VARIANCE", "FRONTIER"], ["VARIANCE", "FRONTIER", "CACHED"],
        ["VARIANCE", "FRONTIER", "CACHED"], ["FRONTIER", "CACHED", "VARIANCE"]]
    account = report["accounting"]
    assert account["local_arm_run_count"] == account["reset_from_original_common_snapshot_count"] == account["endpoint_states_restored"] == 12
    assert account["endpoint_triplet_records_written"] == account["endpoint_triplet_records_reloaded"] == 4
    assert account["local_physical_draws"] == sum(p.work_counts["physical_draws"] for p in providers)
    assert account["warm_physical_draws"] == account["warm_provider_calls"] == 0
    for context in contexts:
        for arm in cli.ARMS:
            row = context["arms"][arm]
            assert row["endpoint_restoration"]["passed"] and row["source_reference_validation"]["passed"]
            assert row["first_request_validation"]["applicable"] == (arm in cli.REFERENCE_ARMS)
            assert row["local"]["completed_batches"] == context["requested_batch_count"]
            assert row["local"]["repeat_batches_on_rows_absent_from_common"] == 0
            assert not any(field in row["local"] for field in cli.TRACE_FIELDS)
            assert all("children" not in action for action in row["evaluation"]["target"]["actions"].values())
    # Same base-seed/row/batch stream remains identical across independent providers.
    assert providers[0].calls == providers[5].calls
    assert report["all_sampling_endpoints_closed_before_oracle"] and not report["endpoint_reload_uses_provider"]
    with gzip.open(endpoints, "rt") as reader:
        endpoint = json.loads(next(reader))
    for field in cli.TRACE_FIELDS + ("final_action", "lower", "upper"):
        changed = deepcopy(endpoint)
        if field == "requested_batches":
            changed["arms"]["CACHED"]["local"][field][0]["batch_index"] += 1
        elif field == "observed_batches":
            changed["arms"]["CACHED"]["local"][field][0]["outcomes"][0][0] += .1
        elif field == "gap_assessments":
            changed["arms"]["CACHED"]["local"][field][0]["separated"] = not changed["arms"]["CACHED"]["local"][field][0]["separated"]
        else:
            changed["arms"]["CACHED"]["local"][field] = "DIFFERENT"
        assert not cli._reference_checks(endpoint, changed, "CACHED")["passed"], field


def test_old_control_trace_mismatch_is_retained_and_invalidates_the_stream(monkeypatch, tmp_path):
    cli, plan, endpoints, output, providers, _, _, _, source_reads, source_path = _frontier_setup(monkeypatch, tmp_path)
    with gzip.open(source_path, "rt") as reader:
        rows = [json.loads(line) for line in reader]
    rows[0]["arms"]["CACHED"]["local"]["requested_batches"][0]["batch_index"] += 1
    with gzip.open(source_path, "wt") as writer:
        for row in rows:
            writer.write(json.dumps(row) + "\n")
    source_reads.clear()
    report, _ = cli.run_frontier(plan, endpoints, output)
    first, second = report["repetitions"]
    assert not first["complete"] and second["complete"] and report["complete_repetition_count"] == 1
    context = first["contexts"][0]
    assert context["status"] == "SOURCE_REFERENCE_MISMATCH" and not context["paired_complete"]
    assert context["identity"]["context_index"] == 0 and len(first["contexts"]) == 2
    assert not context["arms"]["CACHED"]["source_reference_validation"]["checks"]["local.requested_batches"]
    assert all("evaluation" in row and row["local"]["completed_fixed_budget"] for row in context["arms"].values())
    assert report["accounting"]["local_physical_draws"] == sum(p.work_counts["physical_draws"] for p in providers)
    assert not report["source_reference_validation"]["all_passed"] and len(source_reads) == 1


def test_frontier_partial_run_keeps_all_costs_and_excludes_its_repetition(monkeypatch, tmp_path):
    cli, plan, endpoints, output, providers, _, _, _, _, _ = _frontier_setup(monkeypatch, tmp_path)
    original_local = cli.run_local_allocation
    original_resample = FrontierGapPlannerState.select_resample
    def local(snapshot, arm, *args, **kwargs):
        if arm != "FRONTIER":
            return original_local(snapshot, arm, *args, **kwargs)
        calls = 0
        def resample(state, *selection_args, **selection_kwargs):
            nonlocal calls
            calls += 1
            return original_resample(state, *selection_args, **selection_kwargs) if calls == 1 else None
        with monkeypatch.context() as patch:
            patch.setattr(FrontierGapPlannerState, "select_row", lambda *args, **kwargs: None)
            patch.setattr(FrontierGapPlannerState, "select_resample", resample)
            return original_local(snapshot, arm, *args, **kwargs)
    monkeypatch.setattr(cli, "run_local_allocation", local)
    report, _ = cli.run_frontier(plan, endpoints, output)
    assert report["complete_repetition_count"] == 0 and report["source_reference_validation"]["all_passed"]
    for repetition in report["repetitions"]:
        for context in repetition["contexts"]:
            local = context["arms"]["FRONTIER"]["local"]
            assert context["status"] == "FIXED_BUDGET_INCOMPLETE" and not context["paired_complete"]
            assert local["completed_batches"] == 1 and local["stop_reason"] == "NO_ELIGIBLE_CANDIDATE"
            assert "evaluation" in context["arms"]["FRONTIER"]
    assert report["accounting"]["local_physical_draws"] == sum(p.work_counts["physical_draws"] for p in providers)
    assert report["accounting"]["provider_counts_by_arm"]["FRONTIER"]["physical_draws"] == 4*256
