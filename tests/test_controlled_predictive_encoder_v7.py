"""Tests catch lookup leakage, incorrect learned targets and row pooling errors."""
import inspect
import json
from unittest.mock import patch

import pytest

from acfqp.science.controlled_predictive_encoder_v7 import (
    ACTIONS, FEATURE_NAMES, RuleEncoder, TrainingModel, board_features,
    compile_encoded, fit_encoder,
)
from acfqp.science.controlled_predictive_quotient_v1 import FiniteModel, Outcome, Query, plan


def _board(rank, position=5):
    board = [0] * 16
    board[position] = rank
    return tuple(board)


LOST = (1, 2, 1, 2, 2, 1, 2, 1, 1, 2, 1, 2, 2, 1, 2, 1)
WON = (11,) + (0,) * 15


def _training():
    # Four active records in one mandatory group. Rank predicts empirical
    # successor status, while every immediate reward is exactly zero.
    boards = {0: _board(1), 1: _board(1), 2: _board(2), 3: _board(2),
              4: _board(1), 5: LOST}
    model = FiniteModel(
        {0: 1, 1: 1, 2: 1, 3: 1, 4: 0, 5: 0},
        {0: "ACTIVE", 1: "ACTIVE", 2: "ACTIVE", 3: "ACTIVE", 4: "CUTOFF", 5: "LOST"},
        {(state, action): (Outcome(1, 4 if state < 2 else 5, 0),)
         for state in range(4) for action in ACTIONS}, (0, 2))
    return TrainingModel("synthetic_empirical", model, boards)


def test_learns_empirical_future_and_shares_codes_across_state_ids():
    data = _training()
    fit = fit_encoder([data])
    build = compile_encoded(data.empirical, data.boards, fit.encoder)
    codes = build.compiled.state_to_cell
    assert codes[0] == codes[1]
    assert codes[2] == codes[3]
    assert codes[0] != codes[2]
    assert fit.diagnostics["active_leaf_count"] == 2
    assert fit.diagnostics["training_target_squared_error"] == pytest.approx(0)
    query = plan(build.compiled, Query(failure_penalty=1))
    assert query.values[codes[0]] == 0
    assert query.values[codes[2]] == -1
    assert fit.diagnostics["work_counts"]["training_action_rows_read"] == 16


def test_serialized_rules_encode_novel_board_without_board_or_state_lookup():
    fit = fit_encoder([_training()])
    payload = json.loads(json.dumps(fit.encoder.to_payload()))
    restored = RuleEncoder.from_payload(payload)
    novel = _board(1, position=6)
    assert novel not in _training().boards.values()
    # Repositioning keeps these board features, so learned rule executes on a
    # novel board and shares its code without adding a training lookup entry.
    assert restored.encode(novel, 1) == fit.encoder.encode(_board(1), 1)
    assert set(payload) == {"schema", "feature_names", "trees", "unseen_active_group_leaf"}
    assert all(set(group) == {"horizon", "status", "legal", "tree"} for group in payload["trees"])
    assert len(FEATURE_NAMES) == 31
    assert len(board_features(novel)) == 31


def test_mandatory_groups_separate_horizon_terminal_and_legal_actions():
    encoder = fit_encoder([_training()]).encoder
    assert encoder.encode(_board(1), 0)[1] == "CUTOFF"
    assert encoder.encode(LOST, 0)[1] == "LOST"
    assert encoder.encode(WON, 0)[1] == "WON"
    assert encoder.encode(_board(1), 1)[1:3] == ("ACTIVE", ACTIONS)
    unseen = encoder.encode(_board(1), 2)
    assert unseen[0] == 2 and unseen[-1] == -1
    corner = encoder.encode(_board(1, 0), 1)
    assert corner[2] == ("DOWN", "RIGHT") and corner[-1] == -1


def test_compile_uses_uniform_member_mean_and_planner_needs_only_compiled_rows():
    data = _training()
    encoder = fit_encoder([data], max_depth=0).encoder
    changed_rows = dict(data.empirical.rows)
    for state in range(4):
        changed_rows[state, "UP"] = (Outcome(1, 4, float(state)),)
    empirical = FiniteModel(data.empirical.layers, data.empirical.terminal, changed_rows, data.empirical.roots)
    build = compile_encoded(empirical, data.boards, encoder)
    cell = build.compiled.state_to_cell[0]
    row = build.compiled.rows[cell, "UP"]
    assert len(row) == 1
    assert row[0].reward == pytest.approx(1.5)
    other = build.compiled.rows[cell, "DOWN"]
    assert sorted(outcome.probability for outcome in other) == [0.5, 0.5]
    empirical.rows.clear()
    result = plan(build.compiled, Query(failure_penalty=1))
    assert result.policy[cell] == "UP"
    assert result.values[cell] == pytest.approx(1.5)


def test_encoder_never_calls_stochastic_step_or_accepts_query_or_future_inputs():
    data = _training()
    with patch("acfqp.domains.standard_2048.step_v1", side_effect=AssertionError("oracle step used")):
        fit = fit_encoder([data])
        fit.encoder.encode(_board(1, 6), 1)
        compile_encoded(data.empirical, data.boards, fit.encoder)
    assert tuple(inspect.signature(RuleEncoder.encode).parameters) == ("self", "board", "remaining_horizon")
    assert tuple(inspect.signature(fit_encoder).parameters) == ("training", "max_depth", "min_leaf")


def test_bottom_up_successor_codes_preserve_delayed_predictive_distinction():
    data = _training()
    boards = dict(data.boards) | {10: _board(1), 11: _board(1), 12: _board(2), 13: _board(2)}
    layers = dict(data.empirical.layers) | {state: 2 for state in range(10, 14)}
    terminal = dict(data.empirical.terminal) | {state: "ACTIVE" for state in range(10, 14)}
    rows = dict(data.empirical.rows) | {(state, action): (Outcome(1, state - 10, 0),)
                                    for state in range(10, 14) for action in ACTIONS}
    model = FiniteModel(layers, terminal, rows, (10, 12))
    fit = fit_encoder([TrainingModel("delayed", model, boards)])
    compiled = compile_encoded(model, boards, fit.encoder).compiled
    assert compiled.state_to_cell[10] != compiled.state_to_cell[12]
    result = plan(compiled, Query(failure_penalty=1))
    assert result.values[compiled.state_to_cell[10]] == 0
    assert result.values[compiled.state_to_cell[12]] == -1
    assert fit.diagnostics["active_leaf_count"] == 4
