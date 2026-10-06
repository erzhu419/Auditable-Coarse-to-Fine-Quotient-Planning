"""Finite pairing, selected-source identities and deterministic branch replay."""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import random

import pytest

from scripts import analyze_controlled_predictive_counterfactual_outcomes_v143 as analysis

ROOT = Path(__file__).resolve().parents[1]
REPLAY_WORK = Counter()


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    before = request.session.testsfailed
    yield
    path = ROOT/'reports/controlled_predictive_counterfactual_outcomes_v143.analysis_checks.json'
    record = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    record['attempts'].append(dict(failures=request.session.testsfailed-before,
        tests_run=sum(item.module.__name__ == __name__ for item in request.session.items),
        environment_samples=0, model_samples=0, deterministic_replay_work=dict(REPLAY_WORK),
        scope='Fixed four-level pairing, same-action zeros, missing/censored returns, quantile source selection and deterministic terminal/spawn/accounting replay'))
    path.write_text(json.dumps(record, indent=2)+'\n')


def paired_rows():
    roots, indexed = {}, {}
    for life in analysis.LIVES:
        for query in analysis.QUERIES:
            for replica in range(analysis.REPLICAS):
                for slot in range(4):
                    key = life, query, replica, slot
                    action = 'RIGHT' if slot else 'LEFT'
                    roots[key] = dict(choices=dict(H2='LEFT', SHALLOW='LEFT', LEARNED64=action, H1_CONT=action))
                    for act in set(roots[key]['choices'].values()):
                        for suffix in range(8):
                            reward = 10*life+replica+(life+1+suffix)*(act == 'RIGHT')
                            indexed[(*key, act, suffix)] = dict(result=dict(status='LOST', utility=reward-1,
                                components=[reward, 1., 0.]))
    return roots, indexed, {key: True for key in indexed}


def test_four_level_means_keep_same_action_zeros_and_all_suffixes():
    result = analysis.paired_comparison(*paired_rows())
    assert result['complete']
    for query in analysis.QUERIES:
        cell = result['comparisons']['H1_CONT-H2'][query]
        assert cell['mean'] == 4.5 and cell['same_action_roots'] == 32
        assert cell['means'] == dict(utility=4.5, reward=4.5, failure=0., success=0.)
        assert cell['positive'] == 4 and cell['negative'] == 0
        assert result['comparisons']['H1_CONT-LEARNED64'][query]['mean'] == 0
        assert result['comparisons']['SHALLOW-H2'][query]['mean'] == 0


@pytest.mark.parametrize('damage', ['cutoff', 'missing', 'invalid'])
def test_affected_roots_never_dropped_from_primary_means(damage):
    roots, indexed, valid = paired_rows(); key = (0, 'risk1', 0, 1, 'RIGHT', 0)
    if damage == 'cutoff': indexed[key]['result'].update(status='CUTOFF', utility=None)
    elif damage == 'missing': del indexed[key]
    else: valid[key] = False
    result = analysis.paired_comparison(roots, indexed, valid)
    assert not result['complete']
    cell = result['comparisons']['H1_CONT-H2']['risk1']
    assert cell['mean'] is None and len(cell['lifecycles'][0]['games'][0]['roots']) == 4
    assert cell['lifecycles'][0]['games'][0]['roots'][1]['means']['utility'] is None
    assert result['comparisons']['SHALLOW-H2']['risk1']['mean'] == 0
    assert result['comparisons']['H1_CONT-H2']['risk8']['mean'] == 4.5


def branch(status):
    board = {'WON': [10, 10]+[0]*14, 'LOST': [1, 1, 3, 4, 5, 6, 7, 8, 9, 10, 9, 10, 8, 7, 6, 5],
        'CUTOFF': [1, 1]+[0]*14}[status]
    after, score, changed = analysis.ground.swipe_board_v1(tuple(board), analysis.ground.Swipe2048Action.LEFT)
    assert changed
    rng = random.Random(4); empty = [i for i, rank in enumerate(after) if not rank]
    cell, rank = empty[int(rng.random()*len(empty))], 1 if rng.random() < .9 else 2
    final = list(after); final[cell] = rank
    internal = 4 if status == 'WON' else 8
    components = [score/2048., float(status == 'LOST'), float(status == 'WON')]
    return dict(seed=4, root_board=board, first_action='LEFT', first_afterstate=list(after), first_exit=final,
        actions=['LEFT'], spawned_cells=[cell], spawned_ranks=[rank], scores=[score], final_board=final,
        result=dict(score=score, steps=1, status=status, components=components,
            utility=None if status == 'CUTOFF' else components[0]-8*components[1]+8*components[2],
            environment_counts=dict(ground_state_status_calls=2, ground_status_internal_swipe_calls=internal,
                ground_swipe_calls=internal+1, ground_explicit_swipe_calls=1, sampled_transitions=1,
                environment_random_draws=2, forced_actions=1), policy_counts={}, learning_counts={},
            forced_action_count=1, continuation_decisions=0, decision_seconds=0., seconds=.1))


def replay(row, cap=2000):
    checks, swipes = analysis.replay_branch(row, 'risk8', cap)
    REPLAY_WORK['swipes'] += swipes
    return checks


@pytest.mark.parametrize('status', ['WON', 'LOST', 'CUTOFF'])
def test_actual_terminal_components_spawn_after_goal_and_cutoff(status):
    row = branch(status); checks = replay(row, 1 if status == 'CUTOFF' else 2000)
    assert all(checks.values()), checks
    assert row['first_exit'].count(0) == row['first_afterstate'].count(0)-1


@pytest.mark.parametrize('damage,check', [
    ('seed', 'branch_spawn_stream'), ('score', 'branch_scores'), ('goal_bonus', 'branch_returns'),
    ('extra_action', 'branch_terminal_chain'), ('environment', 'branch_environment_accounting'),
    ('policy', 'branch_h2_accounting')])
def test_replay_detects_mispairing_reward_and_accounting_changes(damage, check):
    row = branch('WON')
    if damage == 'seed': row['seed'] = 5
    elif damage == 'score': row['scores'][0] += 4
    elif damage == 'goal_bonus': row['result']['utility'] += 8
    elif damage == 'environment': row['result']['environment_counts']['sampled_transitions'] += 1
    elif damage == 'policy': row['result']['policy_counts']['choose_calls'] = 1
    else:
        for key in ('actions', 'spawned_cells', 'spawned_ranks', 'scores'): row[key] *= 2
        row['result']['steps'] = 2
    assert not replay(row)[check]


def test_quantile_roots_and_actions_come_only_from_retained_records(monkeypatch):
    sources, paths = [], {}; index = 0
    for life in analysis.LIVES:
        source = dict(life=life, diagnostic_source_trace=f'old{life}', h1_diagnostic_trace=f'new{life}')
        sources.append(source); old, new = [], []
        for query in analysis.QUERIES:
            for replica in range(8):
                n = 31 if index < 53 else 30; index += 1
                for i in range(n):
                    step = 32*i
                    row = dict(life=life, query=query, replica=replica, step=step,
                        seed=analysis.previous.v140.outer_seed(life, replica), board=[1, 1]+[0]*14,
                        previous_action='DOWN', simulation_seed=analysis.previous.v140.model_seed(life, replica, step))
                    old.append(dict(**row, reference=dict(action='LEFT'), probes=dict(SHALLOW=dict(action='DOWN'), LEARNED64=dict(action='LEFT'))))
                    new.append(dict(**row, probes=dict(H1_CONT=dict(action='RIGHT'))))
        paths[f'old{life}'], paths[f'new{life}'] = old[::-1], new[::-1]
    monkeypatch.setattr(analysis.previous.old, 'read_rows', lambda path: iter(paths[path]))
    roots, reads, checks = analysis.source_cohort(sources)
    assert all(checks.values()) and reads == Counter(v141=1973, v142=1973) and len(roots) == 256
    assert [root['source_ordinal'] for root in roots[:4]] == [3, 11, 19, 27]
    assert roots[0]['choices'] == dict(H2='LEFT', SHALLOW='DOWN', LEARNED64='LEFT', H1_CONT='RIGHT')
    assert roots[0]['actions'] == ['DOWN', 'LEFT', 'RIGHT']
    assert roots[0]['suffix_seeds'] == [143*100000000+s for s in range(8)]
    damaged = next(row for row in paths['new0'] if row['query'] == 'risk1' and row['replica'] == 0 and row['step'] == 96)
    damaged['board'] = [2, 2]+[0]*14
    assert not analysis.source_cohort(sources)[2]['source_root_identity']
