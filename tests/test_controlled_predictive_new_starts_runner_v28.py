"""Shared prefix accounting, independent query preparation, and matched stops."""

from collections import Counter
from dataclasses import asdict
import gzip
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from test_controlled_predictive_new_starts_v28 import ROOT, BOARD, A, B, ACTIONS, PrefixProvider
from acfqp.science import controlled_predictive_new_starts_v28 as core
from acfqp.science.controlled_predictive_decomposition_v19 import ExactOracle
from acfqp.science.controlled_predictive_quotient_v1 import Query
from acfqp.science.controlled_predictive_score_cache_v18 import CachedGapPlannerState
from acfqp.science.controlled_predictive_variance_v20 import VarianceGapPlannerState


def _setup(monkeypatch, tmp_path):
    queries = {"reward": Query(1., 0., 0.), "risk": Query(1., 1., 0.)}
    contexts = [{"context_index": i, "board_index": 0, "case_name": "toy", "query_name": name,
        "target_key": [ROOT[0], list(ROOT[1])], "requested_batch_count": 32, "initial_batches": 32}
        for i, name in enumerate(queries)]
    plan = {"boards": [{"board_index": 0, "name": "toy", "board": list(BOARD), "horizon": 2,
            "generation_seed": 940001, "prefix_seed": 941001, "legal_actions": list(ACTIONS), "novelty": {}}],
        "contexts": contexts, "queries": {name: asdict(query) for name, query in queries.items()},
        "source_query_order": list(queries), "replicates": [{"replicate_index": i, "base_seed": 942001+i} for i in range(2)],
        "board_count": 1, "context_count": 2, "query_count": 2, "replicate_count": 2,
        "arms": ["CACHED", "VARIANCE"], "prefix_batches_per_board": 32, "requested_batches_per_arm": 32,
        "expected_pair_count": 4, "expected_arm_count": 8, "samples_per_batch": 256}
    plan_path, prefixes, endpoints, output = (tmp_path / name for name in ("plan.json", "prefixes.json.gz", "endpoints.jsonl.gz", "result.json.gz"))
    plan_path.write_text(json.dumps(plan))
    script = Path(__file__).resolve().parents[1] / "scripts/run_controlled_predictive_new_starts_v28.py"
    spec = importlib.util.spec_from_file_location("v28_runner_test", script)
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    events, providers, preparations, inputs, open_writers = [], [], [], [], {}
    PrefixProvider.calls = []
    class Prefix(PrefixProvider):
        def __init__(self, seed):
            assert "truth" not in events
            events.append("prefix")
            super().__init__(seed)
    monkeypatch.setattr(core, "BatchRowSampleProvider", Prefix)
    old_prepare = cli.prepare_query
    def prepare(*args):
        before = len(PrefixProvider.calls)
        state, accounting = old_prepare(*args)
        assert len(PrefixProvider.calls) == before == 32
        preparations.append((args[1], state, accounting))
        return state, accounting
    monkeypatch.setattr(cli, "prepare_query", prepare)
    end = 0, BOARD
    class Provider:
        def __init__(self, seed):
            assert "truth" not in events and open_writers[prefixes].closed
            self.seed, self.calls = seed, []
            self.work_counts, self.provider_seconds = Counter(), 0.
            providers.append(self)
        def sample_batch(self, key, action, index):
            assert "truth" not in events
            self.calls.append((key, action, index))
            self.work_counts.update(row_requests=1, physical_draws=256)
            self.work_counts["first_batch_requests" if index == 0 else "repeat_batch_requests"] += 1
            if key == ROOT:
                p = .25 if self.seed % 2 else .75
                return ((p, A, 0.), (1.-p, B, 0.))
            return ((1., end, .5 if action == "RIGHT" else .125),)
    monkeypatch.setattr(cli, "BatchRowSampleProvider", Provider)
    original_local = cli.run_local_allocation
    def local(state, arm, provider, *args, **kwargs):
        assert "truth" not in events and open_writers[prefixes].closed
        assert len(preparations) == 2
        inputs.append((provider.seed, arm, tuple(state.queries), state.spent_batches, dict(state.batch_counts)))
        events.append("local")
        return original_local(state, arm, provider, *args, **kwargs)
    monkeypatch.setattr(cli, "run_local_allocation", local)
    old_open = gzip.open
    def tracked_open(path, mode="rb", *args, **kwargs):
        writer = old_open(path, mode, *args, **kwargs)
        if mode == "xt":
            open_writers[Path(path)] = writer
        return writer
    monkeypatch.setattr(gzip, "open", tracked_open)
    oracle = ExactOracle({ROOT: "ACTIVE", A: "ACTIVE", B: "ACTIVE", end: "CUTOFF"}, {
        **{(ROOT, action): ((.5, A, 0.), (.5, B, 0.)) for action in ACTIONS},
        **{(key, action): ((1., end, .5 if action == "RIGHT" else .125),)
           for key in (A, B) for action in ACTIONS}})
    def closure(**kwargs):
        assert open_writers[endpoints].closed and open_writers[prefixes].closed
        with gzip.open(endpoints, "rt") as reader:
            records = [json.loads(line) for line in reader]
        assert len(records) == 4 and all(set(row["arms"]) == {"CACHED", "VARIANCE"} for row in records)
        assert len(providers) == 8 and events.count("local") == 8 and len(PrefixProvider.calls) == 32
        events.append("truth")
        return SimpleNamespace(counts={"toy_rows": len(oracle.rows)})
    monkeypatch.setattr(cli, "build_development_closure", closure)
    monkeypatch.setattr(cli.ExactOracle, "from_closure", staticmethod(lambda closure: oracle))
    return cli, plan_path, prefixes, endpoints, output, providers, preparations, inputs, events


def test_shared_prefix_and_query_preparation_paid_once_but_fully_attributed_per_query(monkeypatch, tmp_path):
    cli, plan, prefixes, endpoints, output, providers, preparations, inputs, events = _setup(monkeypatch, tmp_path)
    report, _ = cli.run_new_starts(plan, prefixes, endpoints, output)
    assert report["source_valid_repetition_count"] == report["complete_repetition_count"] == 2
    assert events.count("prefix") == events.count("truth") == 1 and events[-1] == "truth"
    assert len(preparations) == 2 and len(providers) == 8 and len({id(provider) for provider in providers}) == 8
    assert [provider.seed for provider in providers] == [942001]*4 + [942002]*4
    assert [entry[1] for entry in inputs] == ["CACHED", "VARIANCE", "VARIANCE", "CACHED", "VARIANCE", "CACHED", "CACHED", "VARIANCE"]
    assert all(len(names) == 1 and batches == 32 and counts == {(ROOT, action): 8 for action in ACTIONS}
               for _, _, names, batches, counts in inputs)
    assert all(state.spent_batches == 32 and state.batch_counts == {(ROOT, action): 8 for action in ACTIONS}
               for _, state, _ in preparations)
    account = report["accounting"]
    assert account["prefix_board_count"] == 1 and account["prepared_query_count"] == 2
    assert account["prefix_physical_batches"] == 32 and account["prefix_physical_draws"] == 8192
    assert account["local_physical_batches"] == 8*32 and account["total_physical_draws"] == 288*256
    assert account["reset_from_prepared_query_count"] == account["local_arm_run_count"] == 8
    assert report["budget_counts"] == {"completed_K_pair": 4, "shared_normal_stop_pair": 0, "unequal_budget_pair": 0}
    for repetition in report["repetitions"]:
        for context in repetition["contexts"]:
            for row in context["arms"].values():
                costs = row["costs"]
                assert costs["prefix_sampling_seconds"] == report["prefixes"][0]["accounting"]["whole_seconds"]
                assert costs["single_query_prepare_seconds"] == report["query_preparations"][context["identity"]["context_index"]]["accounting"]["whole_seconds"]
                assert costs["independent_query_seconds"] == costs["prefix_sampling_seconds"] + costs["single_query_prepare_seconds"] + row["local"]["accounting"]["whole_run_seconds"]
                assert row["evaluation"]["identities_pass"] and row["evaluation"]["reach_probability_pass"]
                assert not any(field in row["local"] for field in cli.TRACE_FIELDS)
    with gzip.open(prefixes, "rt") as reader:
        evidence = json.load(reader)
    assert len(evidence["prefixes"]) == 1 and len(evidence["prefixes"][0]["batches"]) == 32 and len(evidence["query_starts"]) == 2
    assert report["all_prefix_snapshots_closed_before_local"] and report["all_sampling_endpoints_closed_before_oracle"]


@pytest.mark.parametrize("shared", [True, False])
def test_normal_early_stop_costs_remain_valid_and_only_equal_actual_counts_match(monkeypatch, tmp_path, shared):
    cli, plan, prefixes, endpoints, output, providers, _, _, _ = _setup(monkeypatch, tmp_path)
    original_local = cli.run_local_allocation
    def local(snapshot, arm, *args, **kwargs):
        if arm == "CACHED" and not shared:
            return original_local(snapshot, arm, *args, **kwargs)
        current_class = CachedGapPlannerState if arm == "CACHED" else VarianceGapPlannerState
        with monkeypatch.context() as patch:
            patch.setattr(current_class, "select_row", lambda *args, **kwargs: None)
            patch.setattr(current_class, "select_resample", lambda *args, **kwargs: None)
            return original_local(snapshot, arm, *args, **kwargs)
    monkeypatch.setattr(cli, "run_local_allocation", local)
    report, _ = cli.run_new_starts(plan, prefixes, endpoints, output)
    assert report["source_valid_repetition_count"] == 2
    assert report["complete_repetition_count"] == (2 if shared else 0)
    assert report["budget_counts"]["completed_K_pair"] == 0
    assert report["budget_counts"]["shared_normal_stop_pair"] == (4 if shared else 0)
    assert report["budget_counts"]["unequal_budget_pair"] == (0 if shared else 4)
    for repetition in report["repetitions"]:
        for context in repetition["contexts"]:
            assert context["source_valid"] and context["budget_matched"] == shared
            variance = context["arms"]["VARIANCE"]
            assert variance["local"]["completed_batches"] == 0 and variance["local"]["stop_reason"] == "NO_ELIGIBLE_CANDIDATE"
            assert variance["source_valid"] and not variance["completed_requested_budget"]
            assert variance["costs"]["independent_query_seconds"] > 0 and "evaluation" in variance
    expected_local = 0 if shared else 4*32
    assert report["accounting"]["local_physical_batches"] == expected_local
    assert report["accounting"]["total_physical_draws"] == (32+expected_local)*256
    assert sum(provider.work_counts.get("physical_draws", 0) for provider in providers) == expected_local*256
