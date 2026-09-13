"""Hand-board action-contract checks, including independent spawn enumeration."""
from collections import Counter, defaultdict
import json
import math
from pathlib import Path

import pytest

from acfqp.domains.standard_2048 import (
    Swipe2048Action, legal_actions_v1, state_from_board_v1, step_v1,
)
from acfqp.science.controlled_predictive_action_contract_v67 import (
    ActionContractRule, action_contract, build_model, encode_key,
)
from acfqp.science.controlled_predictive_quotient_v1 import Query, compile_full_state, plan


HAND = (10, 9, 1, 1) + (0,) * 12
RISK_A = (6, 6, 5, 7, 1, 4, 3, 2, 3, 5, 7, 8, 4, 7, 8, 9)
RISK_B = (6, 6, 5, 7, 2, 4, 3, 1, 3, 5, 7, 8, 4, 7, 8, 9)
LOST = (1, 2, 1, 2, 2, 1, 2, 1, 1, 2, 1, 2, 2, 1, 2, 1)
LEDGER = dict(builds=[], direct_work=Counter(), ground_rows=0, ground_outcomes=0,
              planner_calls=0, planner_work=Counter())


@pytest.fixture(scope='module', autouse=True)
def retain_work(request):
    yield
    path = Path(__file__).resolve().parents[1]/'reports/controlled_predictive_action_contract_v67.core_checks.json'
    payload = json.loads(path.read_text()) if path.exists() else {'attempts': []}
    payload['attempts'].append(dict(test_module=__file__, session_failures=request.session.testsfailed,
        scope='hand boards only; no registered V67 main roots', **LEDGER))
    path.write_text(json.dumps(payload, indent=2)+'\n')


def exact_row(board, action):
    outcomes = step_v1(state_from_board_v1(board), Swipe2048Action(action))
    LEDGER['ground_rows'] += 1
    LEDGER['ground_outcomes'] += len(outcomes)
    return outcomes


def build(board, horizon, variant):
    result = build_model(board, horizon, variant)
    LEDGER['builds'].append(dict(board=board, horizon=horizon, variant=variant,
        counts=result.counts, elapsed_seconds=result.elapsed_seconds))
    return result


def test_analytic_terminal_formula_matches_full_spawn_support_for_reachable_cases():
    created_pair = (1, 1, 2, 3, 4, 5, 6, 7, 5, 6, 7, 8, 6, 7, 8, 9)
    goal_pair = (10, 10, 2, 3, 4, 5, 6, 7, 5, 6, 7, 8, 6, 7, 8, 9)
    for board in (RISK_A, RISK_B, HAND, created_pair, goal_pair):
        contract = action_contract(board, LEDGER['direct_work'])
        assert {a for a, *_ in contract} == {a.value for a in legal_actions_v1(board)}
        for action, reward, won, lost in contract:
            row = exact_row(board, action)
            assert {o.merge_score for o in row} == {reward}
            assert won/10 == pytest.approx(sum(float(o.probability) for o in row if o.next_state.status.value == 'WON'))
            assert lost/10 == pytest.approx(sum(float(o.probability) for o in row if o.next_state.status.value == 'LOST'))
    pair_contract = dict((a, (w, l)) for a, _, w, l in action_contract(created_pair, LEDGER['direct_work']))
    assert pair_contract['LEFT'] == (0, 0)


def test_distinct_geometries_can_share_contract_but_reward_only_aliases_risk():
    first = (3, 4, 5, 6, 4, 5, 6, 7, 5, 6, 7, 8, 6, 7, 1, 1)
    second = tuple(rank+1 if rank >= 3 else rank for rank in first)
    exact = ActionContractRule(1, 'CONTRACT')
    unsafe = ActionContractRule(1, 'UNSAFE')
    assert first != second
    assert encode_key(first, 1, exact) == encode_key(second, 1, exact)
    assert encode_key(RISK_A, 1, unsafe) == encode_key(RISK_B, 1, unsafe)
    assert encode_key(RISK_A, 1, exact) != encode_key(RISK_B, 1, exact)
    left = action_contract(RISK_A, LEDGER['direct_work'])
    right = action_contract(RISK_B, LEDGER['direct_work'])
    assert {a:r for a,r,_,_ in left} == {a:r for a,r,_,_ in right}
    assert {a:l for a,_,_,l in left} != {a:l for a,_,_,l in right}


def test_direct_two_step_contract_model_preserves_independent_joint_rows_and_queries():
    baseline = build(HAND, 2, 'BASELINE')
    candidate = build(HAND, 2, 'CONTRACT')
    assert candidate.counts['active_states'] < baseline.counts['active_states']
    assert candidate.counts['spawn_support_entries'] == baseline.counts['spawn_support_entries']
    assert candidate.counts['h0_boards_generated'] == baseline.counts['h0_boards_generated'] == 0
    assert all(candidate.model.layers[state] > 1 for state in candidate.boards)
    for source, board in baseline.boards.items():
        h = baseline.model.layers[source]
        target = candidate.state_index[encode_key(board, h, candidate.rule)]
        for action in legal_actions_v1(board):
            ground = exact_row(board, action.value)
            for generated, mapped_source in ((baseline, source), (candidate, target)):
                mass = defaultdict(list)
                for o in ground:
                    key = encode_key(o.next_state.board, h-1, generated.rule)
                    child = generated.state_index[key]
                    status = o.next_state.status.value
                    if status == 'ACTIVE' and h == 1: status = 'CUTOFF'
                    assert generated.model.terminal[child] == status
                    mass[child, o.merge_score/2048.].append(float(o.probability))
                expected = {key:math.fsum(parts) for key,parts in mass.items()}
                actual = {(o.next_state,o.reward):o.probability for o in generated.model.rows[mapped_source,action.value]}
                assert actual == pytest.approx(expected, abs=1e-12)
    for query in (Query(), Query(1.,5.,1.), Query(.7,.13,2.1)):
        old, new = [plan(compile_full_state(b.model), query) for b in (baseline,candidate)]
        LEDGER['planner_calls'] += 2
        LEDGER['planner_work'].update(old.counts); LEDGER['planner_work'].update(new.counts)
        for source, board in baseline.boards.items():
            target = candidate.state_index[encode_key(board, baseline.model.layers[source], candidate.rule)]
            assert old.values[source] == pytest.approx(new.values[target], abs=1e-12)
            assert old.policy[source] == new.policy[target]


def test_terminal_roots_and_final_legal_moves_are_not_discarded_by_contracts():
    for board, expected in ((LOST,'LOST'), ((11,)+(0,)*15,'WON')):
        result = build(board, 2, 'CONTRACT')
        assert result.model.terminal[result.model.roots[0]] == expected
        assert result.counts['active_states'] == 0 and not result.model.rows
    contract_rule = ActionContractRule(1, 'CONTRACT')
    assert encode_key(LOST, 0, contract_rule) == (0,'LOST')
    assert encode_key((1,1)+LOST[2:], 0, contract_rule) == (0,'CUTOFF')
