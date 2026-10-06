from collections import Counter
from copy import deepcopy
from random import Random
from types import SimpleNamespace

import pytest

from scripts import run_controlled_predictive_spawn_stratification_v176 as runner


def toy_roots():
    roots = []
    for cohort in ("TRAIN", "FRESH"):
        for life in range(4):
            roots.append({
                "root_id": f"{cohort}:{life}:0",
                "cohort": cohort,
                "life": life,
                "source_id": f"{cohort}_SOURCE:{life}:0",
                "probe_ordinal": len(roots),
                "actions": {
                    "TREE": {"canonical_action": "DOWN", "actual_action": "RIGHT"},
                    "ONE": {"canonical_action": "RIGHT", "actual_action": "DOWN"},
                },
                "support": [
                    {"stratum": 0, "lower": 0.0, "upper": 0.9, "rank": 1,
                     "tree_cell": 2, "one_cell": 9, "probability": 0.9},
                    {"stratum": 1, "lower": 0.9, "upper": 1.0, "rank": 2,
                     "tree_cell": 2, "one_cell": 9, "probability": 0.1},
                ],
                "allocation": {"0": 6, "1": 2},
                "draws_per_block": 8,
            })
    return roots


def test_matched_method_budgets_keep_nonuniform_stratum_allocation():
    settings = runner.settings()
    assert settings["blocks"] == 8
    assert settings["methods"] == ["IID", "STRAT"]
    assert settings["minimum_stratum_replicates"] == 2
    assert settings["draws_per_support_entry"] == 4
    assert settings["max_steps"] == 8192
    for key in ("new_model_fits", "new_parameter_updates", "new_source_games"):
        assert settings[key] == 0
    assert settings["autonomous_evaluation"] is False
    assert settings["strategy_promotion"] is False

    roots = toy_roots()
    plans = runner.branch_roster(roots)
    assert len(plans) == len(roots) * 8 * 8 * 2 * 2
    assert len({plan["branch_id"] for plan in plans}) == len(plans)
    assert Counter(plan["method"] for plan in plans) == {"IID": 1024, "STRAT": 1024}
    for root in roots:
        for block in range(8):
            for method in ("IID", "STRAT"):
                group = [plan for plan in plans if plan["root_id"] == root["root_id"]
                         and plan["block"] == block and plan["method"] == method]
                assert len(group) == 16
                assert Counter(plan["mode"] for plan in group) == {"TREE": 8, "ONE": 8}
                assert Counter(plan["suffix"] for plan in group) == {draw: 2 for draw in range(8)}
                if method == "STRAT":
                    assert Counter(plan["stratum"] for plan in group) == {0: 12, 1: 4}
                    for stratum, count in ((0, 6), (1, 2)):
                        assert {plan["replicate"] for plan in group if plan["stratum"] == stratum} == set(range(count))
                else:
                    assert all(plan["stratum"] is None and plan["replicate"] is None for plan in group)


def test_first_spawn_and_tail_seeds_are_paired_across_methods_and_modes():
    roots = toy_roots()
    plans = runner.branch_roster(roots)
    indexed = {(plan["root_id"], plan["block"], plan["suffix"], plan["method"], plan["mode"]): plan
               for plan in plans}
    tail_seeds, spawn_seeds = set(), set()
    for root in roots:
        for block in range(8):
            for draw in range(8):
                paired = [indexed[(root["root_id"], block, draw, method, mode)]
                          for method in ("IID", "STRAT") for mode in ("TREE", "ONE")]
                offset = root["probe_ordinal"] * 100_000 + block * 1000 + draw
                assert {plan["seed"] for plan in paired} == {17_600_000_000 + 10_000_000 + offset}
                assert {plan["spawn_seed"] for plan in paired} == {17_600_000_000 + 20_000_000 + offset}
                for plan in paired:
                    assert plan["phase"] == "PROBE"
                    assert plan["cohort"] == root["cohort"]
                    assert plan["life"] == root["life"]
                    assert plan["source_id"] == root["source_id"]
                    assert plan["probe_ordinal"] == root["probe_ordinal"]
                    assert plan["canonical_action"] == root["actions"][plan["mode"]]["canonical_action"]
                    assert plan["actual_action"] == root["actions"][plan["mode"]]["actual_action"]
                tail_seeds.add(paired[0]["seed"])
                spawn_seeds.add(paired[0]["spawn_seed"])
    assert len(tail_seeds) == len(spawn_seeds) == len(roots) * 8 * 8
    assert tail_seeds.isdisjoint(spawn_seeds)


def test_compact_outcome_preserves_all_plan_fields_without_replica_or_slot():
    plan = next(plan for plan in runner.branch_roster(toy_roots())
                if plan["method"] == "STRAT" and plan["mode"] == "TREE" and plan["stratum"] == 1)
    assert "replica" not in plan
    assert "slot" not in plan
    result = {"score": 2048, "steps": 11, "status": "LOST",
              "components": [1.0, 1.0, 0.0], "utility": 0.0}
    module = {"mode": "FORCED_H2", "life": plan["life"], "forced_decisions": 1, "h2_calls": 10}
    row = {**deepcopy(plan), "result": result, "module": module}
    compact = runner.compact_outcome(row)
    for key, value in plan.items():
        assert compact[key] == value
    for key, value in result.items():
        assert compact[key] == value
    assert compact["components"] == [1.0, 1.0, 0.0]
    assert compact["module"] == module


def test_conditioned_first_spawn_uses_no_rng_and_tail_stream_stays_independent(monkeypatch):
    root = toy_roots()[0]
    root["board"] = [1, 2] + [0] * 14
    plans = runner.branch_roster([root])
    selected = {method: next(plan for plan in plans if plan["method"] == method
                             and plan["mode"] == "TREE" and plan["block"] == 0
                             and plan["suffix"] == 6)
                for method in ("IID", "STRAT")}
    assert selected["STRAT"]["stratum"] == 1
    assert selected["IID"]["seed"] == selected["STRAT"]["seed"]
    assert selected["IID"]["spawn_seed"] == selected["STRAT"]["spawn_seed"]

    empty_afterstate = tuple([0] * 16)
    monkeypatch.setattr(runner.ground, "swipe_board_v1",
                        lambda *args, **kwargs: (empty_afterstate, 0, True))

    def expected_spawn(seed):
        rng = Random(seed)
        board = [0] * 16
        cell = int(rng.random() * 16)
        board[cell] = 1 if rng.random() < 0.9 else 2
        return tuple(board)

    observed = {}
    for method, plan in selected.items():
        boards = []

        def status(board, environment):
            boards.append(tuple(board))
            return "WON" if len(boards) == 3 else "ACTIVE"

        monkeypatch.setattr(runner.physical, "_status", status)
        bank = {query: SimpleNamespace(counts=Counter()) for query in ("risk1", "risk8")}
        bank["risk1"].choose = lambda *args, **kwargs: {
            "action": "DOWN", "afterstate": empty_afterstate, "score": 0,
        }
        outcome = runner.run_conditional_branch(bank, root, plan, max_steps=8192)
        assert len(boards) == 3
        assert outcome["result"]["steps"] == 2
        assert outcome["result"]["status"] == "WON"
        assert boards[2] == expected_spawn(plan["seed"])
        environment = outcome["result"]["environment_counts"]
        if method == "IID":
            assert boards[1] == expected_spawn(plan["spawn_seed"])
            assert environment["environment_random_draws"] == 4
            assert environment.get("conditioned_first_spawn_assignments", 0) == 0
        else:
            first_board = [0] * 16
            first_board[root["support"][1]["tree_cell"]] = root["support"][1]["rank"]
            assert boards[1] == tuple(first_board)
            assert environment["environment_random_draws"] == 2
            assert environment["conditioned_first_spawn_assignments"] == 1
        observed[method] = boards
    assert observed["IID"][2] == observed["STRAT"][2]


def test_stratified_batch_weights_true_probabilities_not_observed_frequencies():
    roots = toy_roots()
    plans = runner.branch_roster(roots)
    outcomes = []
    for plan in plans:
        reward = 0.0
        if plan["mode"] == "TREE":
            reward = 101.0 if plan["method"] == "STRAT" and plan["stratum"] == 1 else 1.0
        outcomes.append({
            **deepcopy(plan),
            "score": int(reward * 2048), "steps": 1, "status": "LOST",
            "components": [reward, 1.0, 0.0], "utility": reward - 1.0,
            "module": {"mode": "FORCED_H2", "life": plan["life"],
                       "forced_decisions": 1, "h2_calls": 0},
        })
    retained_outcomes = deepcopy(outcomes)
    batches = runner.construct_batches(roots, plans, outcomes)
    assert len(batches) == len(roots) * 8 * 2
    assert {(batch["root_id"], batch["block"], batch["method"]) for batch in batches} == {
        (root["root_id"], block, method)
        for root in roots for block in range(8) for method in ("IID", "STRAT")
    }
    for batch in batches:
        if batch["method"] == "STRAT":
            assert batch["components"] == pytest.approx([11.0, 0.0, 0.0])
            assert batch["components"][0] != 26.0
        else:
            assert batch["components"] == [1.0, 0.0, 0.0]
        assert batch["physical_branches"] == 16
        assert batch["environment_samples"] == 16
    assert outcomes == retained_outcomes
