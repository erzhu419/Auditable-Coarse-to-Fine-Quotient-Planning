"""Independent concrete-kernel checks before the controlled V71 campaign."""
from collections import Counter
from dataclasses import replace
from fractions import Fraction
import json
from pathlib import Path

import pytest

from acfqp.domains.standard_2048 import (
    Swipe2048Action, state_from_board_v1, step_v1, swipe_board_v1,
)
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics
from acfqp.science.controlled_predictive_symbolic_successors_v71 import compile_rule


ROOT = Path(__file__).resolve().parents[1]
LEDGER = dict(ground_classifications=0, ground_step_rows=0,
              ground_step_outcomes=0, fixture_checks=[], prediction_work=Counter())


@pytest.fixture(scope="module", autouse=True)
def retain_work(request):
    yield
    path = ROOT / "reports/controlled_predictive_symbolic_successors_v71.core_checks.json"
    payload = json.loads(path.read_text()) if path.exists() else {"attempts": []}
    payload["attempts"].append(dict(test_module=__file__,
        session_failures=request.session.testsfailed,
        scope="four fixed afterstates, one winning swipe, and changed spawn probabilities; no target roots",
        **LEDGER))
    path.write_text(json.dumps(payload, indent=2) + "\n")


@pytest.fixture(scope="module")
def rule():
    return LearnedDynamics.from_payload(json.loads((ROOT /
        "reports/controlled_predictive_composition_v69/learned_rule.json").read_text()))


def collapse_oracle(rows, remaining_h):
    mass = {}
    for probability, board, reward in rows:
        LEDGER["ground_classifications"] += 1
        status = state_from_board_v1(board).status.value
        if status == "ACTIVE" and remaining_h == 0:
            status = "CUTOFF"
        key = (status, board if status == "ACTIVE" else None, reward)
        mass[key] = mass.get(key, Fraction()) + probability
    return tuple((p, status, board, reward) for (status, board, reward), p in mass.items())


def concrete_spawn(moved, score, distribution):
    empty = [cell for cell, rank in enumerate(moved) if not rank]
    for cell in empty:
        for rank, probability in distribution:
            board = list(moved)
            board[cell] = rank
            yield probability / len(empty), tuple(board), Fraction(score, 2048)


def test_symbolic_status_mass_board_and_order_match_independent_kernel(rule):
    checker = (0, 2, 1, 2, 2, 1, 2, 1, 1, 2, 1, 2, 2, 1, 2, 1)
    pair = (0, 2, 2, 2) + checker[4:]
    multiple = checker[:15] + (0,)
    goal = (11,) + checker[1:15] + (0,)
    compiled = compile_rule(rule)
    for name, moved in (("last_hole_mixed", checker), ("existing_pair", pair),
                        ("multiple_holes", multiple), ("goal_priority", goal)):
        for horizon in (0, 2):
            expected = collapse_oracle(concrete_spawn(moved, 12, rule.spawn_distribution), horizon)
            work = Counter()
            actual = compiled.successors(moved, 12, horizon, work)
            LEDGER["prediction_work"].update(work)
            LEDGER["fixture_checks"].append(dict(name=name, remaining_h=horizon,
                                                 board=list(moved), score=12))
            assert actual == expected
            assert sum(row[0] for row in actual) == 1
            assert work["symbolic_board_materializations"] == sum(row[1] == "ACTIVE" for row in actual)
            if horizon == 0:
                assert work["symbolic_board_materializations"] == 0
    mixed = compiled.successors(checker, 0, 2)
    assert [row[1] for row in mixed] == ["LOST", "ACTIVE"]


def test_winning_legal_swipe_preserves_true_step_probability_and_reward(rule):
    board = (10, 10, 2, 1, 2, 3, 4, 5, 3, 4, 5, 6, 4, 5, 6, 7)
    action = Swipe2048Action.LEFT
    moved, score, changed = swipe_board_v1(board, action)
    assert changed and score == 2048
    ground = step_v1(state_from_board_v1(board), action)
    LEDGER["ground_step_rows"] += 1
    LEDGER["ground_step_outcomes"] += len(ground)
    LEDGER["fixture_checks"].append(dict(name="winning_legal_swipe", board=list(board), action="LEFT"))
    expected = collapse_oracle(((o.probability, o.next_state.board, Fraction(o.merge_score, 2048))
                                for o in ground), 0)
    work = Counter()
    assert compile_rule(rule).successors(moved, score, 0, work) == expected == (
        (Fraction(1), "WON", None, Fraction(1)),)
    LEDGER["prediction_work"].update(work)
    assert work["symbolic_board_materializations"] == 0


def test_compilation_reads_frozen_spawn_probabilities_without_refitting(rule):
    changed = replace(rule, spawn_distribution=((1, Fraction(3, 4)), (2, Fraction(1, 4))))
    moved = (0, 2, 1, 2, 2, 1, 2, 1, 1, 2, 1, 2, 2, 1, 2, 1)
    expected = collapse_oracle(concrete_spawn(moved, 4, changed.spawn_distribution), 0)
    work = Counter()
    actual = compile_rule(changed).successors(moved, 4, 0, work)
    LEDGER["prediction_work"].update(work)
    LEDGER["fixture_checks"].append(dict(name="changed_spawn_probability", board=list(moved)))
    assert actual == expected == ((Fraction(3, 4), "LOST", None, Fraction(1, 512)),
                                  (Fraction(1, 4), "CUTOFF", None, Fraction(1, 512)))
