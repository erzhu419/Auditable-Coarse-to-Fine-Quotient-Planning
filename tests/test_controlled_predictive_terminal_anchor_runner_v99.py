"""V99 batch/model wiring and the explicit zero-continuation baseline."""
from collections import Counter
from copy import deepcopy
import importlib.util
import json
from pathlib import Path

import pytest

from acfqp.science import controlled_predictive_paired_direct_v96 as direct
from acfqp.science import controlled_predictive_paired_bellman_value_v96 as old


ROOT = Path(__file__).resolve().parents[1]
LEDGER = Counter()


@pytest.fixture(scope="module", autouse=True)
def retain_work(request):
    yield
    path = ROOT / "reports/controlled_predictive_terminal_anchor_runner_v99.core_checks.json"
    payload = json.loads(path.read_text()) if path.exists() else {"attempts": []}
    payload["attempts"].append(dict(test_module=__file__, session_failures=request.session.testsfailed,
        scope="Mock batch/fit/evaluation and mock physical prefixes only.",
        tree_fits=0, model_predictions=0, ground_sampled_transitions=0,
        synthetic_transitions=0, main_campaign_calls=0, **LEDGER))
    path.write_text(json.dumps(payload, indent=2) + "\n")


@pytest.fixture
def runner():
    spec = importlib.util.spec_from_file_location("terminal_anchor_runner_v99",
        ROOT / "scripts/run_controlled_predictive_terminal_anchor_v99.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_incremental_rows_fit_each_weighting_once_and_reuse_old_models_at_both_ages(runner, tmp_path, monkeypatch):
    source = tmp_path / "source"
    original = source / "life_9/replicas_4"
    original.mkdir(parents=True)
    monkeypatch.setattr(runner, "SOURCE", source)
    monkeypatch.setattr(runner, "BUDGETS", (20, 40))
    stages, old_payloads = [], {}
    for budget, cutoff, episodes in ((20, 2, [0]), (40, 5, [0, 3])):
        stage = original / f"budget_{budget}"
        stage.mkdir()
        roster = {q: episodes for q in runner.QUERIES}
        stages.append(dict(budget=budget, episode_cutoff=cutoff, cumulative_rows=6 * len(episodes),
            cumulative_roots={q: dict(training=episodes, heldout=[]) for q in runner.QUERIES},
            acquisition=dict(used_transitions=20)))
        suffix = "_FROZEN_HALF" if budget == 20 else ""
        for weight in runner.WEIGHTINGS:
            name = f"R4_{weight}_FQE_DIRECT{suffix}"
            payload = dict(checkpoint=cutoff, family="PAIR_FQE", training_episodes=roster,
                           marker=f"old_{budget}_{weight}")
            old_payloads[name] = payload
            (stage / f"{name.lower()}_model.json").write_text(json.dumps(payload))
    (original / "run.json").write_text(json.dumps(dict(construction=stages,
        new_training_environment_transitions=40, new_tree_fits=1032)))
    loads, fits = [], []

    def load_batch(folder):
        budget = int(folder.name.split("_")[-1])
        loads.append(budget)
        episode, start, end, cutoff = (0, 0, 2, 2) if budget == 20 else (3, 2, 8, 5)
        rows = [dict(query=q, episode=episode, option="SNAKE_4", replica=0,
                     step=step, weight=1 / 32, target=[episode, 0, 0])
                for q in runner.QUERIES for step in (4, 20, 36)]
        return rows, dict(start_cursor=start, next_cursor=end, episode_cutoff=cutoff)

    class Value:
        def __init__(self, payload):
            self.payload = deepcopy(payload)
            self.checkpoint, self.family = payload["checkpoint"], payload["family"]
        def to_payload(self):
            return deepcopy(self.payload)

    def learner(rows, checkpoint, iterations):
        fits.append(dict(rows=deepcopy(rows), checkpoint=checkpoint, iterations=iterations))
        roster = {q: sorted({row["episode"] for row in rows if row["query"] == q}) for q in runner.QUERIES}
        values = {family: Value(dict(checkpoint=checkpoint, family=family,
            training_episodes=roster, marker=f"new_fit_{len(fits)}")) for family in ("PAIR_MC", "ANCHORED_FQE")}
        return values, dict(training_episodes=roster, counts=dict(tree_fits=0))

    monkeypatch.setattr(runner, "load_batch", load_batch)
    monkeypatch.setattr(runner, "fit_models", learner)
    monkeypatch.setattr(old, "fit_models", lambda *args, **kwargs: pytest.fail("old FQE must only be loaded"))
    result = runner.construct_allocation(9, 4, tmp_path / "result", {})
    LEDGER.update(mock_batch_loads=len(loads), mock_fit_calls=len(fits))
    assert loads == [20, 40]
    assert [fit["checkpoint"] for fit in fits] == [2, 2, 5, 5]
    assert all(fit["iterations"] == 128 for fit in fits)
    assert [len(fit["rows"]) for fit in fits] == [6, 6, 12, 12]
    for uniform, boundary in (fits[:2], fits[2:]):
        assert all(row["weight"] == 1 / 32 for row in uniform["rows"])
        assert all(row["weight"] == (3 / 64 if row["step"] == 4 else 3 / 128) for row in boundary["rows"])
        assert [{k: v for k, v in row.items() if k != "weight"} for row in uniform["rows"]] == [
            {k: v for k, v in row.items() if k != "weight"} for row in boundary["rows"]]
    assert result["new_training_environment_transitions"] == 0
    assert result["historical_v98_tree_fits"] == 1032
    metadata = result["model_metadata"]
    assert len(metadata) == 12
    for name, record in metadata.items():
        saved = json.loads(Path(record["path"]).read_text())
        if name in old_payloads:
            assert saved == old_payloads[name] and record["source"] == "v98"
        else:
            index = (1 if name.endswith("_FROZEN_HALF") else 3) + int("BOUNDARY" in name)
            assert saved["marker"] == f"new_fit_{index}" and record["source"] == "v99"
            if "ANCHORED" in name:
                assert saved["anchor_weight"] == .5
    monkeypatch.setattr(runner, "METHODS", ("H2_ONLY", "PREFIX_ONLY_DIRECT") + tuple(metadata))
    monkeypatch.setattr(runner.PairedBellmanValue, "from_payload", Value)
    monkeypatch.setattr(runner.LearnedDynamics, "from_payload", lambda payload: object())
    deployed = {}
    def evaluate(life, budget, folder, values, rule):
        assert budget == 40
        deployed.update(values)
        return {}, [], []
    monkeypatch.setattr(runner, "evaluate_checkpoint", evaluate)
    monkeypatch.setattr(runner, "validate_roots", lambda *args: {})
    runner.lifecycle_evaluation(9, tmp_path / "result", {}, [result])
    LEDGER.update(mock_evaluation_calls=1)
    assert deployed.pop("H2_ONLY") is None
    assert isinstance(deployed.pop("PREFIX_ONLY_DIRECT"), runner.PrefixOnlyContinuation)
    for name, value in deployed.items():
        assert value.checkpoint == metadata[name]["episode_cutoff"]
        assert value.family == metadata[name]["family"]


def test_prefix_only_uses_existing_paired_direct_path_with_zero_learned_work(runner, monkeypatch):
    calls = []
    values = {"H2": 1., "SPACE_1": 3., "SNAKE_1": 3., "SPACE_4": 2., "SNAKE_4": 1.}
    def prefix(board, query, option, replica, seed, rule):
        calls.append((option, replica, seed))
        duration = 0 if option == "H2" else int(option.split("_")[1])
        return dict(option=option, replica=replica, spawn_seed=seed, planning_seed=seed + 10**12,
            initial_board=list(board), final_board=list(board), status="ACTIVE", steps_count=4,
            steps=[dict(status="ACTIVE") for _ in range(4)], direct=[values[option], 0, 0],
            action_paths=["fragment"] * duration + ["H2"] * (4 - duration),
            model_work=dict(spawn_uniform_draws=8, synthetic_transitions=4),
            planning_counts=dict(model_uniform_draws=16),
            controller=dict(events=[dict(option=option)], initiation_step=0,
                selected_option=option, fragment_actions=duration))
    monkeypatch.setattr(direct, "_simulate_prefix", prefix)
    monkeypatch.setattr(old.PairedBellmanValue, "predict_pair",
        lambda *args, **kwargs: pytest.fail("prefix-only must not invoke a learned continuation"))
    selector = runner.PairedDirectSelector(runner.PrefixOnlyContinuation(), object(), 1000, replicas=2)
    work = Counter(model_uniform_draws=37)
    choice = selector.select([1] * 10 + [0] * 6, "reward", work=work)
    LEDGER.update(mock_prefix_calls=len(calls), prefix_only_zero_predictions=8)
    assert calls == [(option, replica, 1000 + replica) for replica in range(2) for option in runner.OPTIONS]
    assert choice["option"] == "SPACE_1" and choice["value"] == 2
    assert choice["predictions"]["H2"]["target"] == [0, 0, 0]
    assert selector.last_log["value_counts"] == dict(prefix_only_zero_predictions=8)
    assert all(selector.last_log["wiring"].values())
    assert work["model_uniform_draws"] == 37 and work["candidate_model_uniform_draws"] == 160
    for row in selector.last_prefixes:
        assert row["paired_tail"] == [0, 0, 0]
        assert row["paired_completed"] == row["paired_direct"]
