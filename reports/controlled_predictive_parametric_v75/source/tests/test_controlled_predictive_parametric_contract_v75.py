"""Exact H2 reward binding, guarded fallback, and terminal branch fixtures."""
from collections import Counter
import json
from pathlib import Path

import pytest

from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics
from acfqp.science.controlled_predictive_effect_contract_v74 import SharedEffectCompiler
from acfqp.science.controlled_predictive_parametric_contract_v75 import ParametricCompiler


ROOT = Path(__file__).resolve().parents[1]
BASE = (3, 3, 4, 5, 4, 5, 6, 3, 5, 6, 3, 4, 6, 3, 4, 5)
LEDGER = dict(fixtures=[], reference_work=Counter(), parametric_work=Counter(),
              no_reuse_work=Counter())


@pytest.fixture(scope="module", autouse=True)
def retain_work(request):
    yield
    path = ROOT / "reports/controlled_predictive_parametric_contract_v75.core_checks.json"
    payload = json.loads(path.read_text()) if path.exists() else {"attempts": []}
    payload["attempts"].append(dict(test_module=__file__, session_failures=request.session.testsfailed,
        scope="Three shifted dense bindings, changed merge relation, goal and failure fixtures; no main-cohort roots.",
        ground_calls=0, fit_calls=0, **LEDGER))
    path.write_text(json.dumps(payload, indent=2) + "\n")


@pytest.fixture(scope="module")
def rule():
    return LearnedDynamics.from_payload(json.loads((ROOT /
        "reports/controlled_predictive_composition_v69/learned_rule.json").read_text()))


def reference(rule, board):
    compiler = SharedEffectCompiler(rule)
    context = compiler.prepare(board)
    rows = []
    if compiler.status(context) == "ACTIVE":
        for action, score, after in compiler.actions(context):
            outcomes = tuple((p, status, description)
                for p, status, description, _, _ in compiler.spawn_groups(after, grouping=False))
            rows.append((action, score, outcomes))
    LEDGER["reference_work"].update(compiler.work)
    return tuple(rows)


def test_new_rank_bindings_reuse_symbolic_trace_and_rebind_real_rewards(rule):
    parametric, no_reuse = ParametricCompiler(rule), ParametricCompiler(rule, reuse=False)
    first_root_scores = None
    for shift in (0, 1, 2):
        board = tuple(rank + shift for rank in BASE)
        expected = reference(rule, board)
        before = Counter(parametric.work)
        actual = parametric.contract(board)
        assert actual == expected == no_reuse.contract(board)
        root_scores = tuple(score for _, score, _ in actual)
        if first_root_scores is None:
            first_root_scores = root_scores
            assert any(first_root_scores)
        else:
            assert root_scores == tuple(score * (1 << shift) for score in first_root_scores)
            for field in ("compile_symbolic_swipes", "compile_h1_symbolic_boards",
                          "compile_spawn_candidates", "compile_terminal_mass_calls"):
                assert parametric.work[field] == before[field]
            assert parametric.work["guard_checks"] > before["guard_checks"]
        LEDGER["fixtures"].append(dict(kind="new_binding", shift=shift, board=list(board)))
    assert parametric.work["template_compilations"] == 1
    assert parametric.work["template_hits"] == 2
    assert no_reuse.work["template_compilations"] == 3
    assert no_reuse.work["guard_checks"] == 0
    assert not no_reuse.templates
    LEDGER["parametric_work"].update(parametric.work)
    LEDGER["no_reuse_work"].update(no_reuse.work)


def test_changed_merge_relation_rejects_the_old_template_and_compiles_exact_fallback(rule):
    compiler = ParametricCompiler(rule)
    changed = (4,) + BASE[1:]
    assert compiler.contract(BASE) == reference(rule, BASE)
    before = Counter(compiler.work)
    assert compiler.contract(changed) == reference(rule, changed)
    assert compiler.work["template_guard_rejections"] > before["template_guard_rejections"]
    assert compiler.work["template_compilations"] == 2
    assert compiler.work["compile_spawn_candidates"] > before["compile_spawn_candidates"]
    LEDGER["fixtures"].append(dict(kind="guard_rejection", board=list(changed)))
    LEDGER["parametric_work"].update(compiler.work)


def test_goal_failure_and_unmerged_ordered_spawn_branches_match_reference(rule):
    boards = ((2, 2, 1, 2, 2, 1, 2, 1, 1, 2, 1, 2, 2, 1, 2, 1),
              (10, 10, 2, 1, 2, 3, 4, 5, 3, 4, 5, 6, 4, 5, 6, 7))
    compiler = ParametricCompiler(rule)
    statuses = set()
    for board in boards:
        expected = reference(rule, board)
        actual = compiler.contract(board)
        assert actual == expected
        for _, _, outcomes in actual:
            assert sum(p for p, _, _ in outcomes) == 1
            for _, status, description in outcomes:
                statuses.add(status)
                if description is not None:
                    statuses.update(terminal for _, _, terms in description for terminal, _ in terms)
        assert [len(outcomes) for _, _, outcomes in actual] == [len(outcomes) for _, _, outcomes in expected]
        LEDGER["fixtures"].append(dict(kind="terminal_and_order", board=list(board)))
    assert {"WON", "LOST", "CUTOFF"} <= statuses
    LEDGER["parametric_work"].update(compiler.work)
