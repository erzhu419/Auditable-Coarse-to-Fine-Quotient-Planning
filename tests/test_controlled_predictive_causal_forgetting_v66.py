"""Hand-board checks of the causal rule and independent ground commutation."""
from collections import Counter, defaultdict
from dataclasses import asdict
import json
import math
from pathlib import Path

import pytest

from acfqp.domains.standard_2048 import (
    Swipe2048Action, legal_actions_v1, state_from_board_v1, step_v1,
)
from acfqp.science.controlled_predictive_causal_forgetting_v66 import (
    ANONYMOUS, ForgettingRule, build_model, encode_key, swipe, synthesize_rule,
    terminal_status,
)
from acfqp.science.controlled_predictive_quotient_v1 import Query, compile_full_state, plan


LEDGER = {"hand_board_builds": [], "standalone_rule_calls": [], "direct_work": Counter(),
          "planner_calls": 0, "planner_work": Counter(), "ground_transition_rows": 0,
          "ground_transition_outcomes": 0}
LOST = (1, 2, 1, 2, 2, 1, 2, 1, 1, 2, 1, 2, 2, 1, 2, 1)
HAND = (10, 9, 1, 1) + (0,) * 12


@pytest.fixture(scope="module", autouse=True)
def retain_development_work(request):
    yield
    target = Path(__file__).resolve().parents[1] / "reports/controlled_predictive_causal_forgetting_v66.core_checks.json"
    payload = json.loads(target.read_text()) if target.exists() else {"attempts": []}
    payload["attempts"].append({
        "test_module": __file__, "session_failures": request.session.testsfailed,
        "scope": "hand boards only; no registered V66 experiment roots",
        **LEDGER,
    })
    target.write_text(json.dumps(payload, indent=2) + "\n")


def rule(board, horizon):
    result = synthesize_rule(board, horizon)
    LEDGER["standalone_rule_calls"].append({"board": board, "rule": asdict(result)})
    return result


def build(board, horizon, variant):
    result = build_model(board, horizon, variant)
    LEDGER["hand_board_builds"].append({
        "board": board, "horizon": horizon, "variant": variant,
        "counts": result.counts, "elapsed_seconds": result.elapsed_seconds,
    })
    return result


def solve(model, query):
    result = plan(compile_full_state(model), query)
    LEDGER["planner_calls"] += 1
    LEDGER["planner_work"].update(result.counts)
    return result


def test_anonymous_tiles_slide_but_never_merge_with_one_another():
    source = (ANONYMOUS, ANONYMOUS, 1, 1) + (0,) * 12
    moved, score, changed = swipe(source, "LEFT", LEDGER["direct_work"])
    assert moved[:4] == (ANONYMOUS, ANONYMOUS, 2, 0)
    assert score == 4 and changed
    moved_again, second_score, changed_again = swipe(moved, "LEFT", LEDGER["direct_work"])
    assert moved_again == moved and second_score == 0 and not changed_again


def test_rule_removes_self_partner_retains_duplicate_and_spawn_ranks_and_terminal_roots():
    synthesized = rule(HAND, 2)
    assert synthesized.forgotten_ranks == (9, 10)
    assert synthesized.partner_upper_bounds[9] == synthesized.partner_upper_bounds[10] == 0
    assert 1 not in rule((1,) + (0,) * 15, 1).forgotten_ranks
    assert 10 not in rule((10, 10) + (0,) * 14, 1).forgotten_ranks
    assert rule((11,) + (0,) * 15, 2).forgotten_ranks == ()
    assert rule(LOST, 2).forgotten_ranks == ()


def test_conservative_extra_step_and_final_loss_goal_checks_are_retained():
    # Two simultaneous rank-3 products can supply rank 4 on the extra step.
    synthesized = rule((4, 2, 2, 2, 2) + (0,) * 11, 1)
    assert synthesized.partner_upper_bounds[4] > 0
    assert 4 not in synthesized.forgotten_ranks
    identity = ForgettingRule(1, (), {}, {})
    assert encode_key(LOST, 0, identity) == (0, "LOST")
    assert encode_key((11,) + (0,) * 15, 0, identity) == (0, "WON")
    final_escape = (1, 1) + LOST[2:]
    assert terminal_status(final_escape, LEDGER["direct_work"]) == "ACTIVE"
    assert encode_key(final_escape, 0, identity) == (0, "CUTOFF")


def test_independent_ground_kernel_commutes_for_all_hand_board_two_step_rows():
    baseline = build(HAND, 2, "BASELINE")
    causal = build(HAND, 2, "CAUSAL")
    for source, board in baseline.boards.items():
        remaining = baseline.model.layers[source]
        ground = state_from_board_v1(board)
        assert ground.status.value == "ACTIVE"
        actions = {action.value for action in legal_actions_v1(board)}
        candidate_source = causal.state_index[encode_key(board, remaining, causal.rule)]
        assert actions == {action for state, action in causal.model.rows if state == candidate_source}
        assert actions == {action for state, action in baseline.model.rows if state == source}
        for action in sorted(actions):
            support = step_v1(ground, Swipe2048Action(action))
            LEDGER["ground_transition_rows"] += 1
            LEDGER["ground_transition_outcomes"] += len(support)
            for generated, mapped_source in ((baseline, source), (causal, candidate_source)):
                expected = defaultdict(list)
                for outcome in support:
                    child = outcome.next_state
                    key = encode_key(child.board, remaining - 1, generated.rule)
                    exact_status = child.status.value
                    if exact_status == "ACTIVE" and remaining == 1:
                        exact_status = "CUTOFF"
                    target = generated.state_index[key]
                    assert generated.model.terminal[target] == exact_status
                    expected[target, outcome.merge_score / 2048.0].append(float(outcome.probability))
                expected_mass = {key: math.fsum(parts) for key, parts in expected.items()}
                actual_mass = {(outcome.next_state, outcome.reward): outcome.probability
                               for outcome in generated.model.rows[mapped_source, action]}
                assert actual_mass == pytest.approx(expected_mass, abs=1e-12)
    for query in (Query(), Query(1, 5, 1), Query(.7, .13, 2.1)):
        old = solve(baseline.model, query)
        new = solve(causal.model, query)
        for source, board in baseline.boards.items():
            target = causal.state_index[encode_key(board, baseline.model.layers[source], causal.rule)]
            assert old.values[source] == pytest.approx(new.values[target], abs=1e-12)
            assert old.policy[source] == new.policy[target]


def test_unsafe_singleton_forgetting_destroys_a_real_spawn_merge_opportunity():
    hand = (1,) + (0,) * 15
    baseline = build(hand, 2, "BASELINE")
    unsafe = build(hand, 2, "UNSAFE")
    assert unsafe.rule.forgotten_ranks == (1,) and not unsafe.rule.certified
    old = solve(baseline.model, Query())
    broken = solve(unsafe.model, Query())
    assert old.values[baseline.model.roots[0]] > broken.values[unsafe.model.roots[0]]
    assert broken.values[unsafe.model.roots[0]] == 0
    assert any(ANONYMOUS in board for board in unsafe.boards.values())
