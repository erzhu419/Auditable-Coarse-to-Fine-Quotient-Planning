"""Synthetic roster, frozen information flow, support limits and joint replay."""
from collections import Counter
from fractions import Fraction
import json
import pytest
from scripts import run_controlled_predictive_deep_transfer_v200 as runner


def model(mode):
    return dict(mode=mode, fit_counts={'synthetic_fits': 1},
        trees={str(h): [{'mask': ['DOWN'], 'tree': {'cell': h+2, 'members': [0]}}] for h in range(1, 5)},
        cells=[[0, 0, 'WON'], [1, 0, 'LOST'], [2, 0, 'CUTOFF']]+[[h+2, h, 'ACTIVE'] for h in range(1, 5)],
        rows=[[h+2, 'DOWN', [[1, 1, 0, 0, 1]]] for h in range(1, 5)])


def test_full_roster_source_and_both_models_plans_frozen_before_target(tmp_path, monkeypatch):
    events = []
    cases = {'SOURCE': [{'root_id': 'source', 'board': [1]*16, 'seed': 1}],
             'TARGET': [{'root_id': f'target:{i}', 'board': [1]*15+[i+1], 'seed': 2+i} for i in range(2)]}
    monkeypatch.setattr(runner, 'capture_code', lambda output: events.append('capture'))
    monkeypatch.setattr(runner, 'roster', lambda: events.append('roster') or cases)
    def acquire(rows, law):
        assert rows == cases['SOURCE'] and json.loads((tmp_path/'out/cases.json').read_text()) == cases
        events.append('source'); law.counts.update(support_rows=2, support_outcomes=4)
        return {'SOURCE_only': True}
    monkeypatch.setattr(runner, 'acquire_source', acquire)
    def fit(source, mode):
        assert source == {'SOURCE_only': True}; events.append('fit_'+mode); return model(mode)
    monkeypatch.setattr(runner.core, 'fit_model', fit)
    def plan(payload, queries, counts):
        events.append('plan_'+payload['mode']); counts.update(planning_calls=1)
        return {query: dict(values={cell: [Fraction(0)]*3 for cell, _, _ in payload['cells']},
                            policy={h+2: 'DOWN' for h in range(1, 5)}) for query in queries}
    monkeypatch.setattr(runner.core, 'plan_model', plan)
    def evaluate(case, law, models, plans):
        assert set(models) == set(plans) == {'COARSE', 'LEARNED'}
        assert (tmp_path/'out/plans.json').exists()
        frozen = json.loads((tmp_path/'out/run.json').read_text())
        assert frozen['status'] == 'models_frozen'
        events.append('target_'+case['root_id']); law.counts.update(support_rows=1, support_outcomes=2)
        keys = {str(h): dict(states={(h, tuple(case['board']))}, rows={(h, tuple(case['board']), 'DOWN')},
            D4_states={(h, tuple(case['board']))}, D4_rows={(h, tuple(case['board']), 'DOWN')}) for h in (3, 4)}
        return dict(**case, evaluations=[], native_deep={}, native_status_counts={'ACTIVE': 1, 'WON': 0, 'LOST': 0},
                    costs={'native': dict(law.counts)}), keys
    monkeypatch.setattr(runner, 'evaluate_case', evaluate)
    monkeypatch.setattr(runner, 'summarize', lambda rows, models, benchmark: {'complete': True})
    record = runner.run(tmp_path/'out')
    assert events == ['capture', 'roster', 'source', 'fit_COARSE', 'plan_COARSE', 'fit_LEARNED', 'plan_LEARNED',
                      'target_target:0', 'target_target:1']
    assert [row['phase'] for row in record['phase_history']] == ['protocol_frozen', 'source_acquired', 'models_frozen', 'target_complete', 'complete']
    assert all(row['target_support_rows'] == row['target_support_outcomes'] == 0 for row in record['phase_history'][:3])
    assert record['target_support_rows'] == 2 and record['target_support_outcomes'] == 4
    assert record['completed_targets'] == 2 and record['new_random_samples'] == record['new_teacher_loads'] == 0
    assert len(json.loads((tmp_path/'out/target_results.json').read_text())['records']) == 2


def test_mask_closure_order_and_source_limit_keeps_paid_work(tmp_path, monkeypatch):
    class SyntheticLaw:
        def __init__(self):
            self.states, self.index, self.rows, self.counts = [], {}, {}, Counter()
        def observe(self, board):
            node = board[0]
            if node not in self.index:
                self.index[node] = len(self.states)
                self.states.append(dict(board=[node]*16, status='WON' if node == 4 else 'ACTIVE',
                    legal=[] if node == 4 else ['DOWN' if node < 2 else 'LEFT' if node == 2 else 'RIGHT']))
            return self.index[node]
        def row(self, sid, action):
            if (sid, action) not in self.rows:
                nxt = self.observe([self.states[sid]['board'][0]+1]*16)
                self.rows[sid, action] = [[1, 1, nxt, 0, 1]]
            return self.rows[sid, action]
        export = runner.NativeLaw.export
    law = SyntheticLaw(); source = runner.acquire_source([{'board': [0]*16}], law)
    assert source['controlled'] == [0, 1, 2, 3] and source['mask_augmentations'] == 2
    assert [row[:2] for row in source['rows']] == [[0, 'DOWN'], [1, 'DOWN'], [2, 'LEFT'], [3, 'RIGHT']]
    monkeypatch.setattr(runner, 'capture_code', lambda output: None)
    monkeypatch.setattr(runner, 'roster', lambda: {'SOURCE': [{'board': [1]*16}], 'TARGET': [{'board': [2]*16}]})
    monkeypatch.setattr(runner, 'SOURCE_BOUNDS', {'rows': 0, 'outcomes': 10, 'boards': 10})
    monkeypatch.setattr(runner.ground, 'swipe_board_v1', lambda board, action: ((0,)+tuple(board[1:]), 0, True))
    with pytest.raises(RuntimeError, match='support-row bound'):
        runner.run(tmp_path/'out')
    record = json.loads((tmp_path/'out/run.json').read_text())
    paid = record['costs']['failed_source_acquisition']['counts']
    assert paid['native_swipe_calls'] == 4 and paid['support_row_attempts'] == 1
    assert record['completed_targets'] == record['target_support_rows'] == 0
    assert [row['phase'] for row in record['phase_history']] == ['protocol_frozen']
    assert len(json.loads((tmp_path/'out/partial_source.json').read_text())['states']) == 1


def test_joint_replay_terminal_cutoff_receding_depth_and_fallback(monkeypatch):
    class SyntheticLaw:
        states = [dict(board=[0]*16, status='ACTIVE', legal=['DOWN', 'LEFT']),
            dict(board=[1]*16, status='ACTIVE', legal=['DOWN']),
            dict(board=[2]*16, status='WON', legal=[]), dict(board=[3]*16, status='LOST', legal=[])]
        def row(self, sid, action):
            return {(0, 'DOWN'): [[1, 1, 1, 0, 1]], (0, 'LEFT'): [[1, 1, 2, 1, 1]],
                    (1, 'DOWN'): [[1, 1, 3, 2, 1]]}[sid, action]
    encoded_depths = []
    def encode(model, board, h, status, legal, counts):
        encoded_depths.append(h); return None
    monkeypatch.setattr(runner.core, 'encode', encode)
    evaluator = runner.Evaluator(SyntheticLaw(), {'LEARNED': {}}, {})
    assert evaluator.terminal(2, 0) == [0, 0, 1] and evaluator.terminal(3, 0) == [0, 1, 0]
    assert evaluator.terminal(0, 0) == [0, 0, 0]
    reward, reward_action = evaluator.oracle(0, 3, 'reward')
    goal, goal_action = evaluator.oracle(0, 3, 'goal')
    assert reward_action == 'DOWN' and reward == [2, 1, 0]
    assert goal_action == 'LEFT' and goal == [1, 0, 1]
    actual, visits, probability = evaluator.replay(0, 3, 'LEARNED_D1', 'reward')
    assert actual == [2, 1, 0] and visits == 2 and probability == 1
    assert encoded_depths == [1, 1]
    actual, visits, probability = evaluator.replay(0, 3, 'NATIVE_H2', 'goal')
    assert actual == [1, 0, 1] and visits == probability == 0


def test_fixed_rosters_force_only_predefined_pairs_without_outcome_filter(monkeypatch):
    seeds = []
    class SyntheticRng:
        def __init__(self, seed): seeds.append(seed)
        def randint(self, *args):
            assert args == (1, 4)
            return 3
        def choice(self, values): return values[0]
    monkeypatch.setattr(runner.random, 'Random', SyntheticRng)
    cases = runner.roster()
    assert seeds == list(range(200100, 200132))+list(range(200200, 200224))
    assert len(cases['SOURCE']) == 32 and len(cases['TARGET']) == 24
    for split, rows in cases.items():
        for index, row in enumerate(rows):
            first, second = runner.PAIRS[index%12]
            assert row['board'][first] == row['board'][second] == 5
            assert row['board'].count(5) == 2 and row['board'].count(0) == index%2
            assert row['root_id'] == f'v200_{split.lower()}_{index:02d}'
