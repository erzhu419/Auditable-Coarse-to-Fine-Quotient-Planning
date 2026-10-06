"""Runner roster/reuse tests with mocked traces and no environment acquisition."""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import run_controlled_predictive_forced_actions_v128 as runner

ROOT = Path(__file__).resolve().parents[1]
BOARD = [1, 1] + [0] * 14


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    before = request.session.testsfailed
    yield
    path = ROOT / 'reports/controlled_predictive_forced_actions_v128.runner_checks.json'
    payload = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    payload['attempts'].append(dict(tests=sum(item.module.__name__ == __name__ for item in request.session.items),
        failures=request.session.testsfailed - before,
        newly_sampled_environment_transitions=0, environment_random_draws=0,
        scope='Mocked corpus, divergence helper and forced-game result; no native model or environment run.'))
    path.write_text(json.dumps(payload, indent=2) + '\n')


def retained(life, query, replica, method, age=1024):
    action = {'risk1': {'LEARNED': 'LEFT', 'CONSTANT': 'UP'},
              'risk8': {'LEARNED': 'RIGHT', 'CONSTANT': 'LEFT'}}[query][method.split('_', 1)[0]]
    return dict(life=life, query=query, replica=replica, checkpoint=age, method=method,
        eval_id=f'{life}/{method}/{query}/{age}/{replica}',
        actions=[action], chosen_anchor_values=[1.], chosen_success_probabilities=[.25],
        chosen_values=[2.])


def install_corpus(monkeypatch):
    corpus = {life: [retained(life, query, replica, method)
        for query in runner.QUERIES for replica in range(runner.RETAINED_REPLICAS)
        for method in ('LEARNED_risk_goal', 'CONSTANT_risk_goal')] for life in runner.LIVES}
    # Non-final and other-method records must not become cases.
    for life in corpus:
        corpus[life].extend([retained(life, 'risk1', 0, 'LEARNED_risk_goal', age=256),
                            retained(life, 'risk1', 0, 'LEARNED_GPI')])
    monkeypatch.setattr(runner, 'read_rows', lambda path: iter(corpus[int(path.name)]))
    monkeypatch.setattr(runner.LearnedDynamics, 'from_payload', lambda payload: None)
    calls = []
    def divergence(left, right, rule):
        calls.append((left['life'], left['query'], left['replica']))
        changed = left['replica'] in (0, 1)
        return dict(diverged=changed, index=0 if changed else None, board=BOARD if changed else None,
            left_action=left['actions'][0] if changed else None,
            right_action=right['actions'][0] if changed else None,
            shared_prefix_steps=0, counts={'fixture_prefixes': 1}, seconds=0.)
    monkeypatch.setattr(runner, 'board_at_first_divergence', divergence)
    source = dict(snapshots=[dict(life=life, rule={}, control_trace=str(life)) for life in reversed(runner.LIVES)])
    return source, corpus, calls


def test_roster_keeps_all_cases_and_nochanges_but_deduplicates_shared_boards(monkeypatch):
    source, _, calls = install_corpus(monkeypatch)
    roster = runner.build_roster(source)
    assert len(calls) == len(roster['cases']) == 64
    assert sum(c['diverged'] for c in roster['cases']) == 16
    assert len([c for c in roster['cases'] if not c['diverged'] and c['root_id'] is None]) == 48
    assert len(roster['roots']) == 4
    assert [root['life'] for root in roster['roots']] == [0, 1, 2, 3]
    assert all(root['actions'] == ['LEFT', 'RIGHT', 'UP'] for root in roster['roots'])
    assert roster['physical_attempts'] == 4 * 3 * 2 * 16
    assert roster['logical_attempts'] == 16 * 2 * 2 * 16
    assert roster['preparation']['prefix_counts'] == {'fixture_prefixes': 64}
    for case in roster['cases']:
        if case['diverged']:
            assert case['root_id'] == case['life']
            assert case['retained_choices']['LEARNED']['action'] == case['left_action']


def test_roster_and_suffix_pairing_are_stable_across_source_snapshot_order(monkeypatch):
    source, _, _ = install_corpus(monkeypatch)
    first = runner.build_roster(source)
    source['snapshots'].reverse()
    second = runner.build_roster(source)
    assert first['cases'] == second['cases'] and first['roots'] == second['roots']
    seeds = [runner.suffix_seed(root['root_id'], replica) for root in first['roots']
             for replica in range(runner.REPLICAS)]
    assert len(set(seeds)) == len(seeds)
    assert runner.suffix_seed(2, 3) == 128 * 100000000 + 90000000 + 2000 + 3


def test_duplicate_or_missing_retained_case_cannot_silently_shrink_roster(monkeypatch):
    source, corpus, _ = install_corpus(monkeypatch)
    corpus[0].append(deepcopy(corpus[0][0]))
    with pytest.raises(ValueError, match='duplicate'): runner.build_roster(source)
    corpus[0].pop(); corpus[0].pop(0)
    with pytest.raises(KeyError): runner.build_roster(source)


def test_extract_source_uses_final_count_snapshots_and_preserves_inherited_costs(monkeypatch):
    monkeypatch.setattr(runner, 'SOURCE', Path('/retained/v127'))
    source = dict(inherited_costs=dict(v120_training={'sampled': 7}, v126_training={'sampled': 9}),
        snapshots=[dict(life=0, rule={'fixed': True}, models={p: {'path': p, 'updates': 19} for p in runner.POLICIES},
                        unrelated='exclude')])
    checkpoints = [dict(age=age, updates=age + 1, successes=3, constant=.25, model_bytes=100,
                        model_ref=f'life_0/{policy}/checkpoint_{age}.npz')
                   for policy in runner.POLICIES for age in (256, 1024)]
    previous_run = dict(status='complete', lifecycles=[dict(life=0, control_trace='life_0/control.jsonl.gz',
        policies={p: {'checkpoints': [c for c in checkpoints if f'/{p}/' in c['model_ref']]} for p in runner.POLICIES})])
    analysis = dict(complete=True, costs=dict(replay={'retained': 11}, outer={'sampled': 13}))
    result = runner.extract_source(source, previous_run, analysis)
    snapshot = result['snapshots'][0]
    assert snapshot['control_trace'] == '/retained/v127/life_0/control.jsonl.gz'
    assert all(c['updates'] == 1025 and c['path'].endswith('checkpoint_1024.npz') for c in snapshot['counts'].values())
    assert result['inherited_costs'] == dict(source['inherited_costs'], v127_processing=analysis['costs'])
    result['inherited_costs']['v120_training']['sampled'] = 999
    assert source['inherited_costs']['v120_training']['sampled'] == 7
    with pytest.raises(ValueError, match='completed'):
        runner.extract_source(source, previous_run, dict(analysis, complete=False))


def test_forced_row_preserves_paired_seed_fixed_policy_budget_and_observed_game(monkeypatch):
    captured = {}
    game = dict(seed=0, initial_board=BOARD, initial_spawns=[], final_board=[2] + [0] * 14 + [1],
        steps=[dict(action='LEFT', spawned_cell=15, spawned_rank=1, score=4)],
        return_score=4, status='LOST', steps_count=1, seconds=.001,
        work=dict(sampled_transitions=1, environment_random_draws=2, forced_actions=1),
        policy_counts=dict(choose_calls=0), source_updates_before=31, source_updates_after=31)
    def forced(board, action, actor, query, seed, max_steps):
        captured.update(board=board, action=action, actor=actor, query=query, seed=seed, max_steps=max_steps)
        return dict(game, seed=seed)
    monkeypatch.setattr(runner, 'run_forced_continuation', forced)
    actor = SimpleNamespace()
    root = dict(root_id=3, life=2, board=BOARD, forced_action='LEFT')
    row = runner.forced_row(root, 'risk_goal', 4, actor)
    assert captured == dict(board=BOARD, action='LEFT', actor=actor, query=runner.POLICIES['risk_goal'],
        seed=runner.suffix_seed(3, 4), max_steps=2000)
    assert (row['root_id'], row['life'], row['policy'], row['replica'], row['forced_action']) == (3, 2, 'risk_goal', 4, 'LEFT')
    assert row['initial_spawns'] == [] and row['actions'] == ['LEFT']
    assert row['result']['components'] == [4/2048, 1., 0.]
    assert row['result']['source_updates_before'] == row['result']['source_updates_after'] == 31
    assert row['result']['environment_counts'] == game['work']
