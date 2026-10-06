"""Finite four-branch continuation checks with scripted, non-native policies."""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import random

import pytest

from acfqp.domains import standard_2048 as ground
from acfqp.science.controlled_predictive_module_diagnosis_v153 import MODES, QUERIES, run_branch

TEMP = Path(__file__).resolve().parents[1]/'reports/v153_runtime_tmp'
ROWS, STUB_WORK, ORACLE = [], Counter(), Counter()
SPARSE = [1, 1]+[0]*14
LOSS_ROOT = [1, 1, 3, 4, 5, 6, 7, 8, 9, 10, 9, 10, 8, 7, 6, 5]


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    TEMP.mkdir(parents=True, exist_ok=True); before = request.session.testsfailed
    yield
    path = TEMP/'core_checks.json'; payload = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    environment = sum((Counter(r['result']['environment_counts']) for r in ROWS), Counter())
    payload['attempts'].append(dict(tests=sum(i.module.__name__ == __name__ for i in request.session.items),
        failures=request.session.testsfailed-before, environment_counts=dict(environment),
        newly_sampled_environment_transitions=environment['sampled_transitions'], newly_sampled_model_transitions=0,
        real_training_updates=0, native_planner_calls=0, policy_stub_work=dict(STUB_WORK),
        deterministic_oracle_work=dict(ORACLE), scope='Fixed boards and finite branches; no native planner or fitting.'))
    path.write_text(json.dumps(payload, indent=2)+'\n')


class LegalPlanner:
    """Use a declared direction cycle; explicitly charge finite legality probes."""
    def __init__(self, cycle=('LEFT', 'DOWN', 'RIGHT', 'UP')):
        self.cycle, self.calls = cycle, []
        self.counts = Counter(choose_calls=11, value_predictions=13)
    def choose(self, board, query):
        index = len(self.calls) % 4; order = self.cycle[index:]+self.cycle[:index]
        self.calls.append((tuple(board), deepcopy(query)))
        for action in order:
            after, score, changed = ground.swipe_board_v1(board, ground.Swipe2048Action(action))
            STUB_WORK['legality_swipes'] += 1
            if changed: break
        assert changed
        self.counts.update(choose_calls=1, value_predictions=4)
        STUB_WORK.update(choose_calls=1, value_predictions=4)
        return dict(action=action, afterstate=list(after), score=score, value=1., tail_value=.5,
                    status='ACTIVE', action_values={action: dict(value=1., afterstate=list(after), score=score)})


class Predictor:
    def __init__(self, values=([1., 0., 0.],)):
        self.values, self.calls = deepcopy(values), []
        self.frozen, self.counts, self.updates = True, Counter(), 17
    def predict(self, board):
        index = len(self.calls); self.calls.append(tuple(board))
        self.counts['root_predictions'] += 1; STUB_WORK['root_predictions'] += 1
        return self.values[min(index, len(self.values)-1)]


def branch(*args, **kwargs):
    row = run_branch(*args, **kwargs); ROWS.append(row); return row


def replay_and_account(row):
    board, rng = tuple(row['root_board']), random.Random(row['seed']); boards = [board]
    prefix, continuation, teacher = Counter(), Counter(), {q: Counter() for q in QUERIES}
    for step, (action, cell, rank, score, choice) in enumerate(zip(row['actions'], row['spawned_cells'],
            row['spawned_ranks'], row['scores'], row['choices'], strict=True)):
        after, actual_score, changed = ground.swipe_board_v1(board, ground.Swipe2048Action(action))
        ORACLE['replay_swipes'] += 1
        assert changed and actual_score == score and choice['afterstate'] == list(after)
        assert choice['action'] == action and choice['score'] == score and choice['step'] == step
        empty = [i for i, r in enumerate(after) if not r]
        assert cell == empty[int(rng.random()*len(empty))] and rank == (1 if rng.random() < 1.-row['p_four'] else 2)
        ORACLE['uniform_draws'] += 2
        board = list(after); board[cell] = rank; board = tuple(board); boards.append(board)
        (prefix if choice['phase'] == 'prefix' else continuation).update(choice['work'])
        policy = choice['policy_key']; teacher[policy].update(choose_calls=1, value_predictions=4)
        assert choice['action_values'][action]['afterstate'] == list(after)
    result = row['result']; count = len(row['actions']); env = result['environment_counts']
    assert result['steps'] == count and row['final_board'] == list(board)
    assert result['score'] == sum(row['scores']) and result['components'][0] == sum(row['scores'])/2048.
    assert env['sampled_transitions'] == env['ground_explicit_swipe_calls'] == count
    assert env['environment_random_draws'] == 2*count and env['ground_state_status_calls'] == count+1
    assert env.get('initial_spawns', 0) == 0 and result['learning_counts'] == {}
    assert Counter(result['prefix_counts']) == prefix and Counter(result['continuation_counts']) == continuation
    assert Counter(result['policy_counts']) == prefix+continuation
    assert result['policy_counts_by_query'] == {q: dict(c) for q, c in teacher.items()}
    return boards


@pytest.mark.parametrize('mode,limit,prefix_size,expected_keys,gate_steps', [
    ('H_H2', 3, 1, ['risk1']*3, []),
    ('M_H2', 10, 8, ['risk8']*8+['risk1']*2, []),
    ('H_GATE', 10, 1, ['risk1']+['risk8']*8+['risk1'], list(range(1, 10))),
    ('M_GATE', 10, 8, ['risk8']*10, [8, 9]),
])
def test_four_modes_have_fixed_prefix_and_correct_continuation(mode, limit, prefix_size, expected_keys, gate_steps):
    bank = {q: LegalPlanner() for q in QUERIES}; predictor = Predictor([[1., 0., 0.], [-1., 0., 0.]])
    row = branch(SPARSE, bank, 'risk1', mode, predictor, 123, max_steps=limit)
    boards = replay_and_account(row)
    assert row['result']['status'] == 'CUTOFF' and row['result']['utility'] is None
    assert [c['policy_key'] for c in row['choices']] == expected_keys
    assert [c['phase'] for c in row['choices']] == ['prefix']*prefix_size+['continuation']*(limit-prefix_size)
    assert [c['step'] for c in row['choices'] if c['module_decision'] is not None] == gate_steps
    for c in row['choices']:
        if c['module_decision'] is None:
            assert c['work']['forced_decisions'] == 1 and 'choose_calls' not in c['work']
        else:
            assert c['module_decision']['step'] == c['step'] and c['work']['choose_calls'] == 1
            assert 'forced_decisions' not in c['work']
    assert all(q == QUERIES[key] for key, planner in bank.items() for _, q in planner.calls)
    assert predictor.frozen and predictor.updates == 17
    if gate_steps:
        first = row['choices'][gate_steps[0]]['module_decision']
        assert first['boundary'] and first['remaining_before'] == 8 and first['remaining_after'] == 7
        assert predictor.calls[0] == boards[gate_steps[0]]
    else:
        assert predictor.calls == []
    if mode == 'H_GATE':
        assert [row['choices'][i]['module_decision']['boundary'] for i in gate_steps] == [True]+[False]*7+[True]
        assert row['choices'][9]['module_decision']['estimated_advantage'] == -1.
        assert len(predictor.calls) == 2


def test_each_branch_starts_a_fresh_gate_with_absolute_step_and_frozen_model():
    predictor = Predictor(); bank = {q: LegalPlanner() for q in QUERIES}
    rows = [branch(SPARSE, bank, 'risk1', 'M_GATE', predictor, 123, max_steps=9) for _ in range(2)]
    for row in rows:
        replay_and_account(row); decision = row['choices'][8]['module_decision']
        assert decision['step'] == 8 and decision['boundary']
        assert decision['remaining_before'] == 8 and decision['remaining_after'] == 7
        assert row['result']['policy_counts']['learner_root_predictions'] == 1
        assert row['result']['policy_counts']['module_accepts'] == 1
    assert len(predictor.calls) == 2 and predictor.updates == 17 and predictor.frozen


def test_same_first_action_keeps_the_distinct_multistep_intervention():
    def bank(): return dict(risk1=LegalPlanner(), risk8=LegalPlanner(('LEFT', 'RIGHT', 'UP', 'DOWN')))
    h = branch(SPARSE, bank(), 'risk1', 'H_H2', None, 123, max_steps=2)
    m = branch(SPARSE, bank(), 'risk1', 'M_H2', None, 123, max_steps=2)
    hb, mb = replay_and_account(h), replay_and_account(m)
    assert h['actions'][0] == m['actions'][0] == 'LEFT' and hb[1] == mb[1]
    assert h['actions'][1] != m['actions'][1] and h['final_board'] != m['final_board']


@pytest.mark.parametrize('mode', MODES)
def test_terminal_prefix_spawns_once_without_entering_the_gate(mode):
    bank = {q: LegalPlanner() for q in QUERIES}; predictor = Predictor()
    row = branch([10, 10]+[0]*14, bank, 'risk8', mode, predictor, 4)
    replay_and_account(row)
    assert row['result']['status'] == 'WON' and row['result']['steps'] == 1
    assert row['result']['components'] == [1., 0., 1.] and row['result']['utility'] == 9.
    assert row['final_board'].count(0) == row['choices'][0]['afterstate'].count(0)-1
    assert row['result']['continuation_counts'] == {} and predictor.calls == []
    assert row['choices'][0]['module_decision'] is None


def test_terminal_loss_uses_target_query_and_never_becomes_cutoff():
    predictor = Predictor(); bank = {q: LegalPlanner() for q in QUERIES}
    row = branch(LOSS_ROOT, bank, 'risk8', 'H_GATE', predictor, 4)
    replay_and_account(row)
    assert row['result']['status'] == 'LOST' and row['result']['steps'] == 1
    assert row['result']['components'] == [4/2048., 1., 0.] and row['result']['utility'] == 4/2048.-8.
    assert predictor.calls == [] and row['result']['continuation_counts'] == {}
