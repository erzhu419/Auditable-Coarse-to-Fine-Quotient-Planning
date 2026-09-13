"""Small local-contract comparisons before the frozen V72 target campaign."""
from collections import Counter
from dataclasses import replace
from fractions import Fraction
import json
from pathlib import Path

import pytest

from acfqp.domains.standard_2048 import (
    legal_actions_v1, state_from_board_v1, step_v1,
)
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics
from acfqp.science.controlled_predictive_symbolic_successors_v71 import compile_rule
from acfqp.science.controlled_predictive_local_contract_v72 import LocalCompiler


ROOT = Path(__file__).resolve().parents[1]
LEDGER = dict(fixture_checks=[], ground_states=0, ground_step_rows=0,
              ground_outcomes=0, compiler_work=Counter())


@pytest.fixture(scope="module", autouse=True)
def retain_work(request):
    yield
    path = ROOT / "reports/controlled_predictive_local_contract_v72.core_checks.json"
    payload = json.loads(path.read_text()) if path.exists() else {"attempts": []}
    payload["attempts"].append(dict(test_module=__file__,
        session_failures=request.session.testsfailed,
        scope="four fixed spawn bases, two independent ground boards, one changed-probability case; no target roots",
        **LEDGER))
    path.write_text(json.dumps(payload, indent=2) + "\n")


@pytest.fixture(scope="module")
def rule():
    return LearnedDynamics.from_payload(json.loads((ROOT /
        "reports/controlled_predictive_composition_v69/learned_rule.json").read_text()))


def reference_contract(rule, board):
    status, moves = rule.classify(board)
    terminal = compile_rule(rule)
    return status, tuple((action, score, tuple((status, p) for p, status, _, _ in
        terminal.successors(moved, score, 0))) for action, moved, score in moves)


def test_single_cell_patch_contract_matches_complete_board_calculation(rule):
    checker = (0, 2, 1, 2, 2, 1, 2, 1, 1, 2, 1, 2, 2, 1, 2, 1)
    bases = (checker, (0, 2, 2, 2) + checker[4:],
             checker[:15] + (0,), (11,) + checker[1:15] + (0,))
    compiler = LocalCompiler(rule)
    for base in bases:
        context = compiler.prepare(base)
        for cell in context.empty_cells:
            for rank, _ in rule.spawn_distribution:
                # Materialization is confined to the test's independent full-board reference.
                board = base[:cell] + (rank,) + base[cell + 1:]
                status, expected = reference_contract(rule, board)
                assert compiler.patch_status(context, cell, rank) == status
                assert compiler.contract(context, cell, rank) == expected
                assert compiler.observation_contract(board) == expected
                LEDGER["fixture_checks"].append(dict(base=list(base), cell=cell, rank=rank))
    assert compiler.work["full_board_materializations"] == 0
    assert compiler.work["line_cache_hits"] > 0
    assert compiler.work["unaffected_line_summaries_reused"] == 3 * compiler.work["patched_line_inputs"]
    LEDGER["compiler_work"].update(compiler.work)


def test_whole_and_patch_contracts_match_independent_true_kernel(rule):
    boards = ((2, 2, 1, 2, 2, 1, 2, 1, 1, 2, 1, 2, 2, 1, 2, 1),
              (10, 10, 2, 1, 2, 3, 4, 5, 3, 4, 5, 6, 4, 5, 6, 7))
    compiler = LocalCompiler(rule)
    for board in boards:
        state = state_from_board_v1(board)
        LEDGER["ground_states"] += 1
        expected = []
        for action in legal_actions_v1(board):
            outcomes = step_v1(state, action)
            LEDGER["ground_step_rows"] += 1
            LEDGER["ground_outcomes"] += len(outcomes)
            mass = {}
            for outcome in outcomes:
                status = outcome.next_state.status.value
                if status == "ACTIVE":
                    status = "CUTOFF"
                mass[status] = mass.get(status, Fraction()) + outcome.probability
            expected.append((action.value, outcomes[0].merge_score, tuple(mass.items())))
        expected = tuple(expected)
        cell = next(cell for cell, rank in enumerate(board) if rank in (1, 2))
        base = board[:cell] + (0,) + board[cell + 1:]
        context = compiler.prepare(base)
        assert compiler.patch_status(context, cell, board[cell]) == state.status.value
        assert compiler.contract(context, cell, board[cell]) == expected
        assert compiler.observation_contract(board) == expected
        LEDGER["fixture_checks"].append(dict(ground_board=list(board), cell=cell))
    assert compiler.work["full_board_materializations"] == 0
    LEDGER["compiler_work"].update(compiler.work)


def test_local_contract_uses_supplied_spawn_law(rule):
    changed = replace(rule, spawn_distribution=((1, Fraction(3, 4)), (2, Fraction(1, 4))))
    board = (2, 2, 1, 2, 2, 1, 2, 1, 1, 2, 1, 2, 2, 1, 2, 1)
    compiler = LocalCompiler(changed)
    _, expected = reference_contract(changed, board)
    assert compiler.observation_contract(board) == expected
    assert any(len(mass) > 1 for _, _, mass in expected)
    assert any(probability in (Fraction(3, 4), Fraction(1, 4))
               for _, _, mass in expected for _, probability in mass)
    LEDGER["compiler_work"].update(compiler.work)
    LEDGER["fixture_checks"].append(dict(changed_probability_board=list(board)))
