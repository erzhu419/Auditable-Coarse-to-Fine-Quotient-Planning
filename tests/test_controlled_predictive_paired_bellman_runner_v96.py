"""Mock-only incremental learning, frozen deployment and reference handoff."""
from collections import Counter
from copy import deepcopy
import gzip
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("paired_bellman_runner_v96",
    ROOT / "scripts/run_controlled_predictive_paired_bellman_v96.py")
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)
MOCK_WORK = Counter()


@pytest.fixture(scope="module", autouse=True)
def retain_work(request):
    before = request.session.testsfailed
    MOCK_WORK.clear()
    yield
    path = ROOT / "reports/controlled_predictive_paired_bellman_runner_v96.checks.json"
    payload = json.loads(path.read_text()) if path.exists() else {"attempts": []}
    payload["attempts"].append(dict(test_module=__file__, test_failures=request.session.testsfailed - before,
        scope="Runner integration with mocked extraction, models and games; no actual learning or simulation.",
        mock_calls=dict(MOCK_WORK), ground_calls=0, tree_fits=0, main_campaign_calls=0))
    path.write_text(json.dumps(payload, indent=2) + "\n")


def test_incremental_batches_once_and_frozen_models_survive_later_learning(monkeypatch, tmp_path):
    class Pair:
        def __init__(self, family, checkpoint, episodes):
            self.family, self.checkpoint, self.episodes = family, checkpoint, list(episodes)

        def to_payload(self):
            return dict(family=self.family, checkpoint=self.checkpoint, episodes=list(self.episodes))

    source, branches, output = (tmp_path / name for name in ("source", "branches", "output"))
    output.mkdir()
    prior = []
    for checkpoint, increment in ((6, 10), (12, 20)):
        directory = source / "life_3" / f"checkpoint_{checkpoint}"
        directory.mkdir(parents=True)
        for family in ("MC_TAIL", "FQE"):
            M.save(directory / f"{family.lower()}_full.json", dict(checkpoint=checkpoint,
                excluded_fold=None, training_method=family, training_episodes={}, trees={}, iterations=128))
        prior.append(dict(episodes=checkpoint,
            updates={"value": {"counts": {"tree_fits": 100}}, "heads": {"counts": {"tree_fits": 4}}},
            inherited_acquisition={"source": {"sampled_transitions": increment},
                "branches": {"sampled_transitions": increment * 10}},
            method_acquisition={family: {"total_training_transitions": checkpoint * 100}
                for family in ("MC_TAIL", "FQE")}))
    M.save(source / "life_3/run.json", {"checkpoints": prior})
    loaded, fitted, evaluated = [], [], []
    deployed_at_evaluation = {}

    def load(folder):
        MOCK_WORK["batch_loads"] += 1
        loaded.append(folder)
        checkpoint = int(folder.name.split("_")[-1])
        episodes = [0, 4] if checkpoint == 6 else [6, 9]
        return [dict(episode=episode) for episode in episodes], [dict(episode=episode) for episode in episodes], {}

    def fit(rows, checkpoint, iterations):
        MOCK_WORK["fit_model_calls"] += 1
        episodes = [row["episode"] for row in rows]
        fitted.append((checkpoint, episodes, iterations))
        return {family: Pair(family, checkpoint, episodes) for family in ("PAIR_MC", "PAIR_FQE")}, {
            "counts": {"tree_fits": 2}}

    def evaluate(life, checkpoint, folder, deployed, rule):
        assert fitted == [(6, [0, 4], 128), (12, [0, 4, 6, 9], 128)]
        evaluated.append(checkpoint)
        deployed_at_evaluation.update(deployed)
        return {"methods": {}}, [{"evaluation_only": True}], []

    monkeypatch.setattr(M, "SOURCE", source)
    monkeypatch.setattr(M, "BRANCH_SOURCE", branches)
    monkeypatch.setattr(M, "LearnedDynamics", SimpleNamespace(from_payload=lambda payload: None))
    monkeypatch.setattr(M, "load_batch", load)
    monkeypatch.setattr(M, "fit_models", fit)
    monkeypatch.setattr(M, "evaluate_checkpoint", evaluate)
    monkeypatch.setattr(M, "validate_roots", lambda roots, *args: {"roots": roots})
    result = M.lifecycle_run(3, output, {})
    assert loaded == [branches / "life_3" / f"checkpoint_{checkpoint}" for checkpoint in (6, 12)]
    assert evaluated == [12] and len(fitted) == 2
    assert set(deployed_at_evaluation) == set(M.METHODS[12])
    for name, model in deployed_at_evaluation.items():
        if model is None:
            continue
        age = 6 if name.endswith("_FROZEN_6") else 12
        assert model.checkpoint == age
        path = output / "life_3" / f"checkpoint_{age}" / f"{name.lower()}_model.json"
        assert json.loads(path.read_text())["checkpoint"] == age
    current = deployed_at_evaluation["PAIR_FQE_DIRECT"]
    frozen = deployed_at_evaluation["PAIR_FQE_DIRECT_FROZEN_6"]
    current.episodes.append(99)
    assert frozen.episodes == [0, 4]
    frozen_path = output / "life_3/checkpoint_6/pair_fqe_direct_frozen_6_model.json"
    assert json.loads(frozen_path.read_text())["episodes"] == [0, 4]
    stage = result["checkpoints"][0]
    assert stage["new_tree_fits"] == 4  # Mock accounting values; actual tree fits are zero.
    assert stage["historical_v94_tree_fits"] == 208
    assert stage["inherited_training"] == {
        "source": {"sampled_transitions": 30}, "branches": {"sampled_transitions": 300}}
    assert stage["new_training_environment_transitions"] == 0
    assert stage["validation"]["roots"] == [{"evaluation_only": True}]


def test_pair_unary_factory_and_model_ages_share_prefix_but_not_actor_rng(monkeypatch):
    factories, natural, controllers = [], [], []

    class Unary:
        kind = "unary"

        def __init__(self, value, rule, seed, replicas):
            factories.append((self.kind, value.checkpoint, seed, replicas))
            self.checkpoint = value.checkpoint
            self.last_log, self.last_prefixes = None, []

    class Pair(Unary):
        kind = "pair"

    class Controller:
        def __init__(self, selector, query, rule, rng, mode):
            self.work, self.events = {}, []
            self.fragment_actions = 0
            self.selected_option = self.initiation_step = None
            self.rng = rng
            controllers.append(self)

    def episode(seed, act, max_steps):
        MOCK_WORK["natural_games"] += 1
        natural.append((seed, controllers[-1].rng.random()))
        return dict(return_score=0, status="CUTOFF", steps_count=0, final_board=[1] * 16,
                    seconds=0, work={}, steps=[])

    monkeypatch.setattr(M, "DirectSelector", Unary)
    monkeypatch.setattr(M, "PairedDirectSelector", Pair)
    monkeypatch.setattr(M, "FragmentController", Controller)
    monkeypatch.setattr(M.experience, "run_episode", episode)
    for query_index, query in enumerate(M.QUERIES):
        for method in M.METHODS[12]:
            age = 6 if method.endswith("_FROZEN_6") else 12
            model = None if method == "H2_ONLY" else SimpleNamespace(checkpoint=age)
            game, raw = M.evaluate_game(method, model, None, 3, 12, 0, query)
            assert game["selector_checkpoint"] == (age if model else None)
            assert raw["model_prefixes"] == []
            if model is not None:
                assert factories[-1] == ("pair" if method.startswith("PAIR_") else "unary",
                    age, 196030000000 + query_index * 1000000, 32)
    assert len(factories) == 16 and len(natural) == 18
    assert all(row == natural[0] for row in natural)
    assert natural[0][0] == 9810300
    assert all(row[2] != natural[0][0] for row in factories)


def test_reference_uses_original_natural_events_and_preserves_censored_costs(monkeypatch, tmp_path):
    expected, selections = {}, []
    board = [1] * 10 + [0] * 6

    def evaluate(method, selector, rule, life, checkpoint, replica, query, max_steps):
        MOCK_WORK["evaluation_game_calls"] += 1
        selections.append((method, query))
        learned = method != "H2_ONLY"
        event = dict(step=0, board=board, option="H2", value=0.,
            selection_serial=len(selections), predictions={"H2": {"target": [0., 0., 0.], "value": 0.}})
        if learned:
            expected[query, method] = deepcopy(event)
        game = dict(seed=9810300, score=4, query=query, replica=replica, steps=1,
            committed_length_matches=True, controller_events=int(learned),
            planning_counts={"model_uniform_draws": 4}, initiation_step=0 if learned else None,
            selected_option="H2" if learned else None, candidate_evaluation={"wiring": {"matched": True}})
        steps = [dict(board=board, action="LEFT", next_board=board)]
        prefixes = [dict(option="H2", replica=0, spawn_seed=M.prefix_seed(life, query, replica),
            planning_seed=M.prefix_seed(life, query, replica) + 10 ** 12,
            steps=steps, status="ACTIVE")] if learned else []
        return game, dict(method=method, query=query, episode={"steps": steps},
            controller_events=[event] if learned else [], model_prefixes=prefixes)

    monkeypatch.setattr(M, "evaluate_game", evaluate)
    _, roots, missing = M.evaluate_checkpoint(3, 12, tmp_path,
        {name: None for name in M.METHODS[12]}, None, replicas=1)
    assert len(roots) == 2 and missing == [] and len(selections) == 18
    for root in roots:
        assert root["predictions"] == {method: expected[root["query"], method] for method in M.METHODS[12][1:]}

    def forbid(*args, **kwargs):
        raise AssertionError("reference must not invoke a selector or another natural game")

    def sample(root, rule, life, replicas):
        MOCK_WORK["reference_roots"] += 1
        assert life == 96003 and replicas == 16
        assert "predictions" not in root
        retained = json.loads((tmp_path / "validation_cohort.json").read_text())["roots"]
        assert retained == roots  # The natural decisions are on disk before outcomes are requested.
        censored = root["query"] == "risk_goal"
        raw = [dict(option=option, replica=replica, game={"status": "LOST"})
            for replica in range(replicas) for option in M.OPTIONS]
        if censored:
            raw[-1]["game"]["status"] = "CUTOFF"
        return [], raw, dict(censored_root=censored, ground_work={"sampled_transitions": 80},
            pair_deltas={} if censored else {option: [[0., 0., 0.]] * replicas for option in M.OPTIONS[1:]})

    monkeypatch.setattr(M, "DirectSelector", forbid)
    monkeypatch.setattr(M, "PairedDirectSelector", forbid)
    monkeypatch.setattr(M, "evaluate_game", forbid)
    monkeypatch.setattr(M, "sample_root", sample)
    validation = M.validate_roots(roots, missing, tmp_path, None)
    assert validation["new_selector_calls"] == validation["new_model_transitions"] == 0
    for row in validation["roots"]:
        query = row["root"]["query"]
        assert row["predictions"] == {method: expected[query, method] for method in M.METHODS[12][1:]}
        assert row["reference_complete"] == (query == "reward")
        assert row["terminal_log"]["ground_work"]["sampled_transitions"] == 80
        if query == "risk_goal":
            assert row["paired_reference"] == {}
    with gzip.open(tmp_path / "validation_games.jsonl.gz", "rt") as handle:
        assert len(list(handle)) == 160
