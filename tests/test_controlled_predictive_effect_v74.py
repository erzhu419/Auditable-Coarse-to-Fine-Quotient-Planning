"""Exact action-effect reuse checks against the frozen V73 compiler."""
from collections import Counter
import json
from pathlib import Path

import pytest

from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics
from acfqp.science.controlled_predictive_grouped_contract_v73 import GroupedCompiler
from acfqp.science.controlled_predictive_effect_contract_v74 import EffectCompiler, SharedEffectCompiler


ROOT = Path(__file__).resolve().parents[1]
LEDGER = dict(fixtures=[], baseline_work=Counter(), candidate_work=Counter())


@pytest.fixture(scope="module", autouse=True)
def retain_work(request):
    yield
    path = ROOT / "reports/controlled_predictive_effect_v74.core_checks.json"
    payload = json.loads(path.read_text()) if path.exists() else {"attempts": []}
    payload["attempts"].append(dict(test_module=__file__, session_failures=request.session.testsfailed,
    scope="Fixed legality, risk, goal, vacancy-family and convergent-parent fixtures; no target roots.",
        ground_calls=0, fit_calls=0, **LEDGER))
    path.write_text(json.dumps(payload, indent=2) + "\n")


@pytest.fixture(scope="module")
def rule():
    return LearnedDynamics.from_payload(json.loads((ROOT /
        "reports/controlled_predictive_composition_v69/learned_rule.json").read_text()))


def record(baseline, candidate):
    LEDGER["baseline_work"].update(baseline.work)
    LEDGER["candidate_work"].update(candidate.work)


def test_same_afterstate_does_not_reuse_action_legality(rule):
    moved_input = (0, 1, 0, 0) + (0,) * 12
    fixed_input = (1, 0, 0, 0) + (0,) * 12
    baseline, candidate = GroupedCompiler(rule), EffectCompiler(rule)
    assert rule.swipe(moved_input, "LEFT") == (fixed_input, 0, True)
    assert rule.swipe(fixed_input, "LEFT") == (fixed_input, 0, False)
    first = candidate.observation_contract(moved_input)
    second = candidate.observation_contract(fixed_input)
    assert first == baseline.observation_contract(moved_input)
    assert second == baseline.observation_contract(fixed_input)
    assert "LEFT" in {action for action, _, _ in first}
    assert "LEFT" not in {action for action, _, _ in second}
    assert candidate.work["effect_cache_hits"] > 0
    LEDGER["fixtures"].append(dict(kind="same_effect_different_legality",
                                  boards=[list(moved_input), list(fixed_input)]))
    record(baseline, candidate)


def test_shared_successors_skip_scans_when_distinct_parents_have_same_afterstate(rule):
    parents = ((0, 1, 0, 0) + (0,) * 12, (0, 0, 1, 0) + (0,) * 12)
    baseline, shared = EffectCompiler(rule), SharedEffectCompiler(rule)
    contexts = [next(after for action, _, after in shared.actions(shared.prepare(board))
                     if action == "LEFT") for board in parents]
    assert contexts[0].rows == contexts[1].rows
    expected = baseline.spawn_groups(baseline.prepare((1, 0, 0, 0) + (0,) * 12))
    first = shared.spawn_groups(contexts[0])
    before = Counter(shared.work)
    second = shared.spawn_groups(contexts[1])
    assert first == second == expected
    assert first is second
    for field in ("spawn_candidates", "candidate_predicate_evaluations",
                  "terminal_predicate_evaluations", "contract_materializations"):
        assert shared.work[field] == before[field]
    assert shared.work["spawn_group_requests"] == 2
    assert shared.work["successor_group_cache_lookups"] == 2
    assert shared.work["successor_group_cache_hits"] == 1
    assert shared.work["successor_group_materializations"] == 1
    assert shared.work["successor_group_cached_groups"] == len(first)
    LEDGER["fixtures"].append(dict(kind="distinct_parents_shared_afterstate",
                                  boards=[list(board) for board in parents]))
    record(baseline, shared)


def test_exact_effect_reuse_preserves_goal_and_last_vacancy_risk(rule):
    boards = ((2, 2, 1, 2, 2, 1, 2, 1, 1, 2, 1, 2, 2, 1, 2, 1),
              (10, 10, 2, 1, 2, 3, 4, 5, 3, 4, 5, 6, 4, 5, 6, 7))
    baseline, candidate = GroupedCompiler(rule), EffectCompiler(rule)
    observed_statuses = set()
    for board in boards:
        expected = baseline.observation_contract(board)
        assert candidate.observation_contract(board) == expected
        before = candidate.work["terminal_predicate_evaluations"]
        assert candidate.observation_contract(board) == expected
        assert candidate.work["terminal_predicate_evaluations"] == before
        observed_statuses.update(status for _, _, terms in expected for status, _ in terms)
        LEDGER["fixtures"].append(dict(kind="goal_or_last_vacancy", board=list(board)))
    assert {"WON", "LOST", "CUTOFF"} <= observed_statuses
    assert candidate.work["effect_exact_output_keys"] > 0
    record(baseline, candidate)


def test_vacancy_family_shares_effects_before_terminal_predicates(rule):
    base = (3, 3, 3, 0) * 4
    baseline, candidate = GroupedCompiler(rule), EffectCompiler(rule)
    expected = baseline.spawn_groups(baseline.prepare(base))
    actual = candidate.spawn_groups(candidate.prepare(base))
    assert actual == expected
    assert candidate.work["candidate_predicate_evaluations"] == baseline.work["candidate_predicate_evaluations"]
    assert candidate.work["candidate_action_predicate_evaluations"] < baseline.work["candidate_action_predicate_evaluations"]
    assert candidate.work["terminal_predicate_evaluations"] < baseline.work["terminal_predicate_evaluations"]
    assert candidate.work["effect_cache_hits"] > 0
    assert candidate.work["effect_vacancy_keys"] > 0
    assert candidate.work["effect_output_line_references"] == 0
    assert candidate.work["full_board_materializations"] == 0
    assert not hasattr(candidate, "context_cache")
    assert candidate.work["effect_cache_entries"] == len(candidate.effect_cache)
    LEDGER["fixtures"].append(dict(kind="shared_four_vacancy_family", base=list(base)))
    record(baseline, candidate)
