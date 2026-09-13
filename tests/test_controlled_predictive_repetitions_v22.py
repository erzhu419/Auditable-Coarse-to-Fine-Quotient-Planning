"""Fresh-stream reset, streaming evidence order and incomplete-run retention."""

from copy import deepcopy
from dataclasses import asdict
import gzip
import importlib.util
import json
from pathlib import Path

from test_controlled_predictive_snapshot_v21 import _fixture
from acfqp.science.controlled_predictive_snapshot_v21 import reconstruct_common_snapshots, common_record
from acfqp.science.controlled_predictive_variance_v20 import VarianceGapPlannerState


def _setup(monkeypatch, tmp_path, *, contexts=2, repetitions=2):
    fixture = _fixture(monkeypatch)
    snapshots, _, _, _ = reconstruct_common_snapshots(fixture.payload, fixture.roster)
    base = snapshots[0]
    records = []
    source_contexts = []
    plan_contexts = []
    for index in range(contexts):
        record = common_record(base)
        record["identity"] = dict(record["identity"], context_index=index)
        records.append(record)
        source_context = dict(fixture.roster["contexts"][0], context_index=index)
        source_contexts.append(source_context)
        plan_contexts.append({**source_context, "query": asdict(base.state.queries["risk"]),
            "target_key": record["target_key"], "panel": record["panel"],
            "requested_batch_count": record["requested_batch_count"], "request_index": record["request_index"],
            "initial_batches": record["state"]["spent_batches"]})
    source_path = tmp_path / "common.json.gz"
    common = {"schema": "acfqp.controlled_predictive_common_snapshots.v21",
        "cohort_roster": {**fixture.roster, "contexts": source_contexts}, "snapshots": records,
        "identity_statuses": [{"identity": record["identity"], "status": "READY"} for record in records]}
    with gzip.open(source_path, "wt") as handle:
        json.dump(common, handle)
    plan = {"source_common_snapshots": str(source_path), "source_query_order": ["risk"],
        "queries": fixture.roster["queries"], "contexts": plan_contexts,
        "context_count": contexts, "replicate_count": repetitions,
        "replicates": [{"replicate_index": i, "base_seed": 922001+i} for i in range(repetitions)]}
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(plan))
    script = Path(__file__).resolve().parents[1] / "scripts/run_controlled_predictive_repetitions_v22.py"
    spec = importlib.util.spec_from_file_location("v22_cli_test", script)
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    providers, events, inputs = [], [], []
    original_provider = fixture.provider
    class FreshProvider(original_provider):
        def __init__(self, seed):
            assert "truth" not in events
            super().__init__(seed)
            self.seed, self.calls = seed, []
            providers.append(self)
        def sample_batch(self, key, action, index):
            assert "truth" not in events
            row = super().sample_batch(key, action, index)
            if len(row) == 2:
                probability = .25 if self.seed % 2 else .75
                row = ((probability, row[0][1], row[0][2]), (1-probability, row[1][1], row[1][2]))
            self.calls.append((key, action, index, row))
            return row
    monkeypatch.setattr(cli, "BatchRowSampleProvider", FreshProvider)
    endpoints, output = tmp_path / "endpoints.jsonl.gz", tmp_path / "report.json"
    def closure(**kwargs):
        with gzip.open(endpoints, "rt") as handle:
            lines = [json.loads(line) for line in handle]
        assert len(lines) == contexts * repetitions
        assert len(providers) == 2 * contexts * repetitions
        events.append("truth")
        return fixture.closure
    monkeypatch.setattr(cli, "build_development_closure", closure)
    original_local = cli.run_local_allocation
    def local(snapshot, arm, provider, *args, **kwargs):
        inputs.append((provider.seed, arm, tuple(sorted(snapshot.batch_counts.items())), snapshot.spent_batches))
        events.append("local")
        return original_local(snapshot, arm, provider, *args, **kwargs)
    monkeypatch.setattr(cli, "run_local_allocation", local)
    return cli, plan_path, endpoints, output, providers, events, inputs, base


def test_fresh_repetitions_reset_share_streams_and_close_all_endpoints_before_truth(monkeypatch, tmp_path):
    cli, plan, endpoints, output, providers, events, inputs, base = _setup(monkeypatch, tmp_path)
    report, _ = cli.run_repetitions(plan, endpoints, output)
    assert report["complete_repetition_count"] == 2
    expected_counts = tuple(sorted(base.state.batch_counts.items()))
    assert all(counts == expected_counts and batches == base.state.spent_batches for _, _, counts, batches in inputs)
    assert [provider.seed for provider in providers] == [922001]*4 + [922002]*4
    assert len({id(provider) for provider in providers}) == 8
    # Same row/batch streams recur across contexts but each provider call is paid.
    assert providers[0].calls == providers[3].calls
    assert providers[1].calls == providers[2].calls
    assert providers[4].calls == providers[7].calls
    assert providers[5].calls == providers[6].calls
    assert providers[0].calls[0][:3] == providers[5].calls[0][:3]
    assert providers[0].calls[0][3] != providers[5].calls[0][3]
    assert [row["run_order"] for rep in report["repetitions"] for row in rep["contexts"]] == [
        ["CACHED", "VARIANCE"], ["VARIANCE", "CACHED"], ["VARIANCE", "CACHED"], ["CACHED", "VARIANCE"]]
    assert events[-1] == "truth" and events.count("local") == 8
    assert report["all_sampling_endpoints_closed_before_oracle"] and not report["endpoint_reload_uses_provider"]
    assert report["accounting"]["warm_physical_draws"] == report["accounting"]["warm_provider_calls"] == 0
    assert report["accounting"]["local_physical_draws"] == sum(provider.work_counts["physical_draws"] for provider in providers)
    assert report["accounting"]["reset_from_original_common_snapshot_count"] == 8
    assert report["accounting"]["endpoint_states_restored"] == 8
    assert len(report["initial_evaluations"]) == 2
    assert all("children" not in action for rep in report["repetitions"] for context in rep["contexts"]
               for arm in context["arms"].values() for action in arm["evaluation"]["target"]["actions"].values())


def test_partial_arm_keeps_its_cost_and_excludes_the_whole_repetition(monkeypatch, tmp_path):
    cli, plan, endpoints, output, providers, _, _, _ = _setup(monkeypatch, tmp_path, contexts=1, repetitions=1)
    original_local = cli.run_local_allocation
    original_select = VarianceGapPlannerState.select_resample
    def local(snapshot, arm, *args, **kwargs):
        if arm == "CACHED":
            return original_local(snapshot, arm, *args, **kwargs)
        calls = 0
        def select(current, *selection_args, **selection_kwargs):
            nonlocal calls
            calls += 1
            return original_select(current, *selection_args, **selection_kwargs) if calls == 1 else None
        with monkeypatch.context() as patch:
            patch.setattr(VarianceGapPlannerState, "select_resample", select)
            return original_local(snapshot, arm, *args, **kwargs)
    monkeypatch.setattr(cli, "run_local_allocation", local)
    report, _ = cli.run_repetitions(plan, endpoints, output)
    repetition = report["repetitions"][0]
    context = repetition["contexts"][0]
    assert not repetition["complete"] and report["complete_repetition_count"] == 0
    assert context["status"] == "FIXED_BUDGET_INCOMPLETE" and not context["paired_complete"]
    assert context["arms"]["VARIANCE"]["local"]["completed_batches"] == 1
    assert context["arms"]["VARIANCE"]["local"]["stop_reason"] == "NO_ELIGIBLE_CANDIDATE"
    assert context["arms"]["VARIANCE"]["first_request_validation"]["passed"]
    assert report["accounting"]["local_physical_draws"] == sum(provider.work_counts["physical_draws"] for provider in providers)
    assert "evaluation" in context["arms"]["VARIANCE"]
