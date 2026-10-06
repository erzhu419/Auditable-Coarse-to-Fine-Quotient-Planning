"""Finite prefix and aggregation fixtures; no V283 environment sampling."""

import copy
from collections import Counter

import pytest

from acfqp.science import natural_action_value_v283 as core
from acfqp.science import natural_action_components_v283 as components
from acfqp.science.controlled_predictive_regime_memory_v115 import SpawnMemory


@pytest.mark.parametrize("status,terminal", [("WON", 4.), ("LOST", -4.), ("CUTOFF", 0.)])
def test_future_utility_excludes_current_reward_and_counts_terminal_once(status, terminal):
    game = dict(status=status, steps_count=3, steps=[dict(score=2048), dict(score=4096), dict(score=1024)])
    assert core.future_utilities(game) == [2.5 + terminal, .5 + terminal, terminal]


def test_later_reward_changes_only_earlier_future_targets():
    game = dict(status="LOST", steps_count=3, steps=[dict(score=2048), dict(score=4096), dict(score=1024)])
    changed = copy.deepcopy(game)
    changed["steps"][1]["score"] += 2048
    before, after = core.future_utilities(game), core.future_utilities(changed)
    assert after[0] == before[0] + 1.
    assert after[1:] == before[1:]


def finite_payload(board):
    after = [2 if board[0] == 1 else 3] + [0] * 15
    rows = {}
    for action, full, short in (("LEFT", [2., 1.], [0., 1.]),
                                ("RIGHT", [0., 4.], [0., 0.])):
        rows[action] = dict(afterstate=after, score=0, rank1_tail=full[0], rank2_tail=full[1],
            short_rank1_tail=short[0], short_rank2_tail=short[1],
            spawn_leaf_values=[dict(cell=1, full=full, short=short)])
    return dict(board=list(board), status="ACTIVE", goal_bonus=4., failure_penalty=4.,
                action_components=rows)


class FiniteEngine:
    def __init__(self):
        self.counts = Counter()

    def components(self, board):
        self.counts.update(component_calls=1)
        return finite_payload(board)

    def compose(self, payload, probability, tail="full"):
        result = components.compose(payload, probability, tail)
        self.counts.update(result["counts"])
        return result


class FiniteDirect:
    def choose(self, board, query):
        return components.compose(finite_payload(board), .1)


def retained_game(ranks=(1, 2), status="LOST"):
    # Only the root prefix protocol is mocked; native board semantics have a
    # separate component test. All feedback is one observed empty-cell spawn.
    memory = SpawnMemory("LIBRARY")
    board, steps, saved = [1, 1] + [0] * 14, [], []
    for rank in ranks:
        probability = memory.predict()
        choice = components.compose(finite_payload(board), probability)
        after = choice["afterstate"]
        child = list(after)
        child[1] = rank
        saved.append(dict(p_four=probability, module_id=memory.module_id,
            observations_before=memory.observations_seen,
            action=choice["action"], value=choice["value"]))
        steps.append(dict(board=list(board), action=choice["action"], afterstate=after,
                          next_board=child, score=0))
        memory.observe(rank)
        board = child
    return dict(lifecycle=0, parent=0, phase="A", episode_index=0, environment_p_four=.1,
        episode=dict(status=status, steps_count=len(steps), steps=steps, final_board=board),
        decisions=saved, summary=dict(seed=-1, observations_after=len(ranks)))


def replay_fixture(raw, memories=None):
    memories = memories or {model: SpawnMemory(model) for model in core.MODELS}
    emitted, engine = [], FiniteEngine()
    result = core.replay_game(raw, memories, engine, FiniteDirect(), emitted.append)
    return result, emitted, memories, engine


@pytest.mark.parametrize("status", ["WON", "LOST", "CUTOFF"])
def test_current_rank_is_committed_after_decision_and_last_rank_once(status):
    raw = retained_game(status=status)
    result, emitted, memories, engine = replay_fixture(raw)
    assert result["decisions"] == result["counts"]["restored_decisions"] == 2
    assert result["changed_rows"] == len(emitted) == 1
    first = emitted[0]
    assert first["observations_before"] == 0
    assert first["p"]["LIBRARY"] == .5
    assert first["full_actions"]["LIBRARY"] == raw["decisions"][0]["action"] == "RIGHT"
    assert raw["decisions"][1]["p_four"] == 1 / 3
    assert raw["decisions"][1]["observations_before"] == 1
    assert all(memory.observations_seen == 2 for memory in memories.values())
    assert all(memory.predict() == .5 for memory in memories.values())
    assert engine.counts["component_calls"] == 2


def test_current_or_later_rank_cannot_change_preceding_replayed_actions():
    original, baseline, _, _ = replay_fixture(retained_game((1, 2)))
    changed_current, current_rows, _, _ = replay_fixture(retained_game((2, 2)))
    _, future_rows, _, _ = replay_fixture(retained_game((1, 1)))
    assert baseline[0] == current_rows[0] == future_rows[0]
    assert current_rows[1]["p"]["LIBRARY"] == 2 / 3
    assert current_rows[1]["observations_before"] == 1
    assert changed_current["changed_rows"] == 2 > original["changed_rows"]


def test_truth_and_retained_future_score_only_without_entering_shadow_memory():
    raw = retained_game()
    changed = copy.deepcopy(raw)
    changed["environment_p_four"] = .5
    changed["episode"]["status"] = "WON"
    changed["episode"]["steps"][1]["score"] = 2048
    baseline, _, before, _ = replay_fixture(raw)
    result, _, after, _ = replay_fixture(changed)
    assert {model: memory.to_payload() for model, memory in before.items()} == {
        model: memory.to_payload() for model, memory in after.items()}
    assert baseline["metrics"]["LIBRARY.p_mse"] != result["metrics"]["LIBRARY.p_mse"]
    assert baseline["metrics"]["ORACLE_P.factual_future_bias"] != result["metrics"]["ORACLE_P.factual_future_bias"]


@pytest.mark.parametrize("field,value", [("p_four", .25), ("module_id", 1),
    ("observations_before", 1), ("action", "LEFT"), ("value", -1.)])
def test_retained_prefix_or_action_mismatch_is_reported(field, value):
    raw = retained_game()
    raw["decisions"][0][field] = value
    with pytest.raises(ValueError):
        replay_fixture(raw)


def test_game_phase_lifecycle_averages_do_not_weight_longer_games(monkeypatch):
    monkeypatch.setattr(core, "BOOTSTRAP_DRAWS", 20)
    games = []
    for life in range(16):
        for phase in core.PHASE_NAMES:
            for episode, value, decisions in ((0, 0., 1), (1, 10., 100)):
                metrics = {f"{model}.{name}": value if model == "LIBRARY" else 0.
                           for model in core.MODELS for name in ("p_mse", "reference_score_loss")}
                games.append(dict(lifecycle=life, parent=life % 4, phase=phase,
                    episode_index=episode, decisions=decisions, metrics=metrics,
                    counts=dict(restored_decisions=decisions)))
    result = core.summarize_games(games)
    assert len(result["games"]) == 16 * 3 * 2
    assert len(result["by_lifecycle"]) == 16
    assert result["metrics"]["LIBRARY.reference_score_loss"] == 5.
    assert all(r["metrics"]["LIBRARY.reference_score_loss"] == 5. for r in result["by_lifecycle"])
    assert all(r["phases"][phase]["decisions"] == 101 for r in result["by_lifecycle"]
               for phase in core.PHASE_NAMES)
    assert result["paired_diagnostic_contrasts"]["LIBRARY_minus_POOLED.reference_score_loss"][
        "improved_equal_worse"] == [0, 0, 16]
    assert result["counts"]["restored_decisions"] == 16 * 3 * 101
    assert all(c["restored_decisions"] == 16 * 101 for c in result["phase_counts"].values())


def test_bootstrap_holds_parent_composition_fixed(monkeypatch):
    monkeypatch.setattr(core, "BOOTSTRAP_DRAWS", 50)
    records = [dict(parent=life % 4, metrics={"LIBRARY.p_mse": float(life % 4),
                    "POOLED.p_mse": 0.}) for life in range(16)]
    result = core.bootstrap_contrast(records, "p_mse", "LIBRARY", "POOLED")
    assert result["mean"] == 1.5 and result["ci95"] == [1.5, 1.5]
    assert result["parent_mean_deltas"] == {"0": 0., "1": 1., "2": 2., "3": 3.}


def test_paired_summary_keeps_adverse_lifecycles_and_signs(monkeypatch):
    monkeypatch.setattr(core, "BOOTSTRAP_DRAWS", 100)
    deltas = [-2., 0., 3., 0.] * 4
    records = [dict(parent=life % 4, metrics={"LIBRARY.reference_score_loss": value + 2.,
                    "POOLED.reference_score_loss": 2.}) for life, value in enumerate(deltas)]
    result = core.bootstrap_contrast(records, "reference_score_loss", "LIBRARY", "POOLED")
    assert result["lifecycle_deltas"] == deltas
    assert result["mean"] == .25
    assert result["improved_equal_worse"] == [4, 8, 4]


def test_shadow_only_short_action_change_is_retained():
    class ShortChangeEngine(FiniteEngine):
        def components(self, board):
            payload = super().components(board)
            for action, full, short in (("LEFT", [2., 2.], [1., 0.]),
                                        ("RIGHT", [1., 1.], [0., 2.])):
                item = payload["action_components"][action]
                item.update(rank1_tail=full[0], rank2_tail=full[1],
                    short_rank1_tail=short[0], short_rank2_tail=short[1],
                    spawn_leaf_values=[dict(cell=1, full=full, short=short)])
            return payload

    memories = {model: SpawnMemory(model) for model in core.MODELS}
    common_prefix = [2] * 26 + [1] * 230 + [1, 2] * 32
    for rank in common_prefix:
        for memory in memories.values():
            memory.observe(rank)
    engine = ShortChangeEngine()
    board = [1, 1] + [0] * 14
    choice = engine.compose(engine.components(board), memories["LIBRARY"].predict())
    after, child = choice["afterstate"], list(choice["afterstate"])
    child[1] = 1
    raw = dict(lifecycle=0, parent=0, phase="A", episode_index=0, environment_p_four=.1,
        episode=dict(status="LOST", steps_count=1, steps=[dict(board=board,
            action=choice["action"], afterstate=after, next_board=child, score=0)]),
        decisions=[dict(p_four=memories["LIBRARY"].predict(), module_id=memories["LIBRARY"].module_id,
            observations_before=320, action=choice["action"], value=choice["value"])],
        summary=dict(seed=-1, observations_after=321))
    emitted = []
    result = core.replay_game(raw, memories, engine, FiniteDirect(), emitted.append)
    assert result["changed_rows"] == len(emitted) == 1
    row = emitted[0]
    assert set(row["full_actions"].values()) == {"LEFT"}
    assert row["short_actions"]["ORACLE_P"] == "LEFT"
    assert row["short_actions"]["FROZEN"] == row["short_actions"]["POOLED"] == "LEFT"
    assert row["short_actions"]["LIBRARY"] == "RIGHT"
    assert result["counts"]["LIBRARY.full_short_action_change"] == 1
    assert result["counts"]["ORACLE_P.full_short_action_change"] == 0
