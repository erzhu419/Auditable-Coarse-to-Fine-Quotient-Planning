"""Finite module tests: exact vacancy objective, exits, and teacher bindings."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path
import random

import pytest

from acfqp.domains import standard_2048 as ground
from acfqp.science.controlled_predictive_module_mobility_v160 import (
    ACTIONS, MODES, QUERIES, mobility_choice, run_branch)
from acfqp.science.controlled_predictive_relational_dynamics_v69 import (
    LearnedDynamics, RewriteProgram)

TEMP = Path(__file__).resolve().parents[1]/'reports/v160_runtime_tmp'
ROWS, STUB_WORK, ORACLE, RULE_WORK = [], Counter(), Counter(), Counter()
SPARSE = [1, 1]+[0]*14
LOSS_ROOT = [1, 1, 3, 4, 5, 6, 7, 8, 9, 10, 9, 10, 8, 7, 6, 5]
RULE = LearnedDynamics(RewriteProgram(True, 'equal', 1, 'once', 'output_value'),
                       ((1, Fraction(9, 10)), (2, Fraction(1, 10))), 'uniform')


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    TEMP.mkdir(parents=True, exist_ok=True); before = request.session.testsfailed
    yield
    path = TEMP/'core_checks.json'
    payload = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    environment = sum((Counter(r['result']['environment_counts']) for r in ROWS), Counter())
    policy = sum((Counter(r['result']['policy_counts']) for r in ROWS), Counter())
    payload['attempts'].append(dict(tests=sum(i.module.__name__ == __name__ for i in request.session.items),
        failures=request.session.testsfailed-before, environment_counts=dict(environment),
        newly_sampled_environment_transitions=environment['sampled_transitions'], newly_sampled_model_transitions=0,
        real_training_updates=0, native_planner_calls=0, policy_stub_work=dict(STUB_WORK),
        deterministic_oracle_work=dict(ORACLE), rule_work=dict(RULE_WORK), policy_counts=dict(policy),
        scope='Finite branches and exact model support; no native planner or fitting.'))
    path.write_text(json.dumps(payload, indent=2)+'\n')


class LegalPlanner:
    def __init__(self, cycle=('LEFT', 'DOWN', 'RIGHT', 'UP')):
        self.cycle, self.calls = cycle, []
        self.counts = Counter(choose_calls=11, value_predictions=13)

    def choose(self, board, query):
        index = len(self.calls) % 4; order = self.cycle[index:]+self.cycle[:index]
        self.calls.append((tuple(board), deepcopy(query)))
        for action in order:
            after, score, changed = ground.swipe_board_v1(board, ground.Swipe2048Action(action))
            STUB_WORK['legality_swipes'] += 1
            if changed:
                break
        assert changed
        self.counts.update(choose_calls=1, value_predictions=4)
        STUB_WORK.update(choose_calls=1, value_predictions=4)
        return dict(action=action, afterstate=list(after), score=score, value=1., tail_value=.5,
                    status='ACTIVE', action_values={action: dict(value=1., afterstate=list(after), score=score)})


def branch(board, query, mode, seed=123, max_steps=10):
    bank = {q: LegalPlanner() for q in QUERIES}
    row = run_branch(board, bank, RULE, query, mode, seed, max_steps=max_steps)
    ROWS.append(row)
    assert all(given == QUERIES[key] for key, planner in bank.items() for _, given in planner.calls)
    return row


def replay_and_account(row):
    board, rng = tuple(row['root_board']), random.Random(row['seed'])
    prefix, continuation, teacher = Counter(), Counter(), {q: Counter() for q in QUERIES}
    for step, (action, cell, rank, score, choice) in enumerate(zip(row['actions'], row['spawned_cells'],
            row['spawned_ranks'], row['scores'], row['choices'], strict=True)):
        after, actual_score, changed = ground.swipe_board_v1(board, ground.Swipe2048Action(action))
        ORACLE['replay_swipes'] += 1
        assert changed and actual_score == score and choice['afterstate'] == list(after)
        assert choice['action'] == action and choice['score'] == score and choice['step'] == step
        empty = [i for i, r in enumerate(after) if not r]
        assert cell == empty[int(rng.random()*len(empty))]
        assert rank == (1 if rng.random() < 1.-row['p_four'] else 2)
        ORACLE['uniform_draws'] += 2
        board = list(after); board[cell] = rank; board = tuple(board)
        (prefix if choice['phase'] == 'prefix' else continuation).update(choice['work'])
        policy = choice['policy_key']
        if policy in QUERIES:
            teacher[policy].update(choose_calls=1, value_predictions=4)
        else:
            assert policy == 'MOBILITY' and choice['expected_postspawn_empty'] == board.count(0)
            assert all(key.startswith('mobility_') for key in choice['work'])
        assert choice['module_decision'] is None
    result = row['result']; count = len(row['actions']); env = result['environment_counts']
    assert result['steps'] == count and row['final_board'] == list(board)
    assert result['score'] == sum(row['scores']) and result['components'][0] == sum(row['scores'])/2048.
    assert env['sampled_transitions'] == env['ground_explicit_swipe_calls'] == count
    assert env['environment_random_draws'] == 2*count and env['ground_state_status_calls'] == count+1
    assert env.get('initial_spawns', 0) == 0 and result['learning_counts'] == {}
    assert Counter(result['prefix_counts']) == prefix and Counter(result['continuation_counts']) == continuation
    assert Counter(result['policy_counts']) == prefix+continuation
    assert result['policy_counts_by_query'] == {q: dict(c) for q, c in teacher.items()}


def test_analytic_empty_objective_matches_exact_nonzero_spawn_support():
    choice = mobility_choice(SPARSE, RULE); RULE_WORK.update(choice['counts'])
    for action, value in choice['action_values'].items():
        outcomes = RULE.successors_from_afterstate(tuple(value['afterstate']), value['score'], RULE_WORK)
        assert sum(p*board.count(0) for p, board, _ in outcomes) == value['expected_postspawn_empty']
    assert choice['counts']['mobility_action_evaluations'] == 4
    assert choice['counts']['mobility_learned_swipe_calls'] == 4
    assert choice['counts']['mobility_learned_line_rewrites'] == 16
    assert 'mobility_learned_spawn_outcomes' not in choice['counts']


def test_ties_use_first_legal_lexical_action_and_exclude_unchanged_swipes():
    board = [1]+[0]*15
    choice = mobility_choice(board, RULE); RULE_WORK.update(choice['counts'])
    assert ACTIONS == ('DOWN', 'LEFT', 'RIGHT', 'UP')
    assert list(choice['action_values']) == ['DOWN', 'RIGHT']
    assert choice['action'] == 'DOWN' and choice['expected_postspawn_empty'] == 14
    assert choice['counts']['mobility_legal_actions'] == 2


@pytest.mark.parametrize('query', tuple(QUERIES))
def test_target_exit_is_postspawn_and_irreversible(query):
    row = branch([1]*16, query, 'MOBILITY')
    replay_and_account(row)
    assert row['module'] == dict(initial_empty=0, target_empty=2, prefix_steps=1,
                                exit_reason='target', exit_empty=7, completion=True)
    assert row['choices'][0]['expected_postspawn_empty'] == 7
    assert [c['policy_key'] for c in row['choices']] == ['MOBILITY']+[query]*9
    assert [c['phase'] for c in row['choices']] == ['prefix']+['continuation']*9


@pytest.mark.parametrize('query', tuple(QUERIES))
def test_budget_exit_then_every_continuation_uses_own_query(query):
    mobility = branch(SPARSE, query, 'MOBILITY')
    other = branch(SPARSE, query, 'OTHER8')
    for row in (mobility, other):
        replay_and_account(row)
        assert row['module']['prefix_steps'] == 8 and row['module']['exit_reason'] == 'budget'
        assert not row['module']['completion']
        assert [c['phase'] for c in row['choices']] == ['prefix']*8+['continuation']*2
        assert [c['policy_key'] for c in row['choices'][-2:]] == [query]*2
    opposite = 'risk8' if query == 'risk1' else 'risk1'
    assert [c['policy_key'] for c in other['choices'][:8]] == [opposite]*8
    assert [c['policy_key'] for c in mobility['choices'][:8]] == ['MOBILITY']*8


def test_h2_has_no_prefix_and_cutoff_prefix_remains_uncompleted():
    baseline = branch(SPARSE, 'risk8', 'H2', max_steps=3)
    truncated = branch(SPARSE, 'risk8', 'MOBILITY', max_steps=3)
    for row in (baseline, truncated):
        replay_and_account(row)
        assert row['result']['status'] == 'CUTOFF' and row['result']['utility'] is None
    assert baseline['module'] == dict(initial_empty=14, target_empty=16, prefix_steps=0,
                                     exit_reason='baseline', exit_empty=14, completion=False)
    assert baseline['result']['prefix_counts'] == {}
    assert [c['policy_key'] for c in baseline['choices']] == ['risk8']*3
    assert truncated['module']['prefix_steps'] == 3 and truncated['module']['exit_reason'] == 'cutoff'
    assert not truncated['module']['completion'] and truncated['result']['continuation_counts'] == {}


@pytest.mark.parametrize('mode', MODES)
def test_terminal_win_is_not_cutoff_and_spawns_once(mode):
    row = branch([10, 10]+[0]*14, 'risk8', mode, seed=4)
    replay_and_account(row)
    assert row['result']['status'] == 'WON' and row['result']['steps'] == 1
    assert row['result']['components'] == [1., 0., 1.] and row['result']['utility'] == 9.
    assert row['final_board'].count(0) == row['choices'][0]['afterstate'].count(0)-1
    if mode != 'H2':
        assert row['module']['exit_reason'] == 'terminal' and row['module']['prefix_steps'] == 1
        assert row['result']['continuation_counts'] == {}


def test_terminal_loss_keeps_target_utility_and_ends_prefix():
    row = branch(LOSS_ROOT, 'risk8', 'MOBILITY', seed=4)
    replay_and_account(row)
    assert row['result']['status'] == 'LOST' and row['result']['steps'] == 1
    assert row['result']['components'] == [4/2048., 1., 0.] and row['result']['utility'] == 4/2048.-8.
    assert row['module']['exit_reason'] == 'terminal' and not row['module']['completion']
    assert row['result']['continuation_counts'] == {}
