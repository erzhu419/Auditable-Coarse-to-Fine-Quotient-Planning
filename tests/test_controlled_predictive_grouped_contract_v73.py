"""Bounded block-geometry and grouping checks before V73 target execution."""
from collections import Counter
from dataclasses import replace
from fractions import Fraction
import json
from pathlib import Path

import pytest

from acfqp.domains.standard_2048 import Swipe2048Action, swipe_board_v1
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics
from acfqp.science.controlled_predictive_local_contract_v72 import LocalCompiler
from acfqp.science.controlled_predictive_grouped_contract_v73 import GroupedCompiler


ROOT = Path(__file__).resolve().parents[1]
CHECKER = (0, 2, 1, 2, 2, 1, 2, 1, 1, 2, 1, 2, 2, 1, 2, 1)
BASES = (CHECKER, (3, 3, 3, 0) * 4, (11,) + CHECKER[1:15] + (0,))
LEDGER = dict(fixture_checks=[], ground_swipes=0, grouped_work=Counter(), each_work=Counter())


@pytest.fixture(scope="module", autouse=True)
def retain_work(request):
    yield
    path = ROOT / "reports/controlled_predictive_grouped_contract_v73.core_checks.json"
    payload = json.loads(path.read_text()) if path.exists() else {"attempts": []}
    payload["attempts"].append(dict(test_module=__file__, session_failures=request.session.testsfailed,
        scope="Three fixed spawn bases plus changed spawn probabilities; no target roots.", **LEDGER))
    path.write_text(json.dumps(payload, indent=2) + "\n")


@pytest.fixture(scope="module")
def rule():
    return LearnedDynamics.from_payload(json.loads((ROOT /
        "reports/controlled_predictive_composition_v69/learned_rule.json").read_text()))


def test_factorized_patch_geometry_and_actions_match_complete_board_reference(rule):
    compiler = GroupedCompiler(rule)
    for base in BASES:
        context = compiler.prepare(base)
        for cell in context.empty_cells:
            for rank, _ in rule.spawn_distribution:
                board = base[:cell] + (rank,) + base[cell + 1:]
                patched = compiler.patched_context(context, cell, rank)
                assert patched.rows == tuple(board[row:row + 4] for row in range(0, 16, 4))
                status, moves = rule.classify(board)
                assert compiler.status(patched) == status
                actual = tuple((action, score, after.rows) for action, score, after in compiler.actions(patched))
                expected = tuple((action, score, tuple(moved[row:row + 4] for row in range(0, 16, 4)))
                                 for action, moved, score in moves)
                assert actual == expected
                if base == CHECKER and rank == 2:
                    for action, moved, score in moves:
                        LEDGER["ground_swipes"] += 1
                        assert swipe_board_v1(board, Swipe2048Action(action)) == (moved, score, True)
                LEDGER["fixture_checks"].append(dict(kind="patch_geometry", base=list(base), cell=cell, rank=rank))
    assert compiler.work["full_board_materializations"] == 0
    assert not hasattr(compiler, "context_cache")
    LEDGER["grouped_work"].update(compiler.work)


def test_grouping_preserves_candidate_mass_and_order_without_h1_geometry_retention(rule):
    grouped, each, reference = GroupedCompiler(rule), GroupedCompiler(rule), LocalCompiler(rule)
    for base in BASES:
        expected, collapsed = [], {}
        ref_context = reference.prepare(base)
        for cell in ref_context.empty_cells:
            for rank, probability in rule.spawn_distribution:
                status = reference.patch_status(ref_context, cell, rank)
                contract = reference.contract(ref_context, cell, rank) if status == "ACTIVE" else None
                p = probability / len(ref_context.empty_cells)
                expected.append((p, status, contract, (cell, rank), 1))
                key = status, contract
                if key not in collapsed:
                    collapsed[key] = [Fraction(), (cell, rank), 0]
                collapsed[key][0] += p
                collapsed[key][2] += 1
        grouped_context = grouped.prepare(base)
        contexts_before = grouped.work["factorized_contexts"]
        actual = grouped.spawn_groups(grouped_context)
        assert grouped.work["factorized_contexts"] == contexts_before
        assert actual == tuple((p, status, contract, descriptor, count)
            for (status, contract), (p, descriptor, count) in collapsed.items())
        assert each.spawn_groups(each.prepare(base), grouping=False) == tuple(expected)
        assert sum(p for p, _, _, _, _ in actual) == 1
        assert sum(count for _, _, _, _, count in actual) == len(expected)
        LEDGER["fixture_checks"].append(dict(kind="candidate_grouping", base=list(base), candidates=len(expected)))
    assert not each.contract_cache
    assert grouped.work["candidate_predicate_evaluations"] == each.work["candidate_predicate_evaluations"]
    assert grouped.work["contract_materializations"] < each.work["contract_materializations"]
    assert grouped.work["terminal_probability_combinations"] < each.work["terminal_probability_combinations"]
    assert grouped.work["vacancy_family_shortcuts"] > 0
    assert grouped.work["full_board_materializations"] == each.work["full_board_materializations"] == 0
    LEDGER["grouped_work"].update(grouped.work)
    LEDGER["each_work"].update(each.work)


def test_grouped_probability_contract_reads_rule_and_routes_existing_observations(rule):
    changed = replace(rule, spawn_distribution=((1, Fraction(3, 4)), (2, Fraction(1, 4))))
    compiler, reference = GroupedCompiler(changed), LocalCompiler(changed)
    for board in ((2,) + CHECKER[1:], (11,) + CHECKER[1:]):
        assert compiler.observation_contract(board) == reference.observation_contract(board)
    first = compiler.spawn_groups(compiler.prepare(CHECKER))
    assert tuple(row[0] for row in first) == (Fraction(3, 4), Fraction(1, 4))
    assert tuple(row[1] for row in first) == ("LOST", "ACTIVE")
    LEDGER["fixture_checks"].append(dict(kind="changed_probabilities", base=list(CHECKER)))
    LEDGER["grouped_work"].update(compiler.work)
