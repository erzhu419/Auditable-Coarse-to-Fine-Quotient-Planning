"""V129 source/namespace/roster/control integration without sampled games."""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import run_controlled_predictive_policy_calibration_v129 as runner
from acfqp.science import controlled_predictive_policy_calibration_v129 as core

ROOT = Path(__file__).resolve().parents[1]
BOARD = [1, 1] + [0] * 14


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    before = request.session.testsfailed
    yield
    path = ROOT / 'reports/controlled_predictive_policy_calibration_v129.runner_checks.json'
    payload = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    payload['attempts'].append(dict(tests=sum(item.module.__name__ == __name__ for item in request.session.items),
        failures=request.session.testsfailed - before, newly_sampled_environment_transitions=0,
        environment_random_draws=0, optimizer_steps=0,
        scope='Mocked model choices, source capsules and short episode result; no native or environment execution.'))
    path.write_text(json.dumps(payload, indent=2) + '\n')


def test_source_uses_only_retained_training_and_model_references_with_old_costs():
    previous = dict(snapshots=[dict(life=0, rule={'fixed': True}, models={'reward': {'path': 'scalar'}},
        counts={'reward': {'path': 'counts'}}, control_trace='old_outer_must_not_enter', predictions={'old': True})],
        inherited_costs=dict(v120={'sampled': 7}, v126={'sampled': 9}))
    analysis = dict(complete=True, costs={'new_environment_transitions': 11})
    source = runner.extract_source(previous, analysis)
    item = source['snapshots'][0]
    assert set(item) == {'life', 'rule', 'models', 'counts', 'training_trace'}
    assert item['training_trace'] == str(runner.ROOT / 'reports/controlled_predictive_policy_consequences_v126/life_0/training.jsonl.gz')
    assert source['inherited_costs'] == dict(previous['inherited_costs'], v128_diagnosis=analysis['costs'])
    source['inherited_costs']['v120']['sampled'] = 999
    assert previous['inherited_costs']['v120']['sampled'] == 7
    with pytest.raises(ValueError, match='complete'):
        runner.extract_source(previous, dict(analysis, complete=False))


def test_root_suffix_and_outer_seed_namespaces_are_paired_and_disjoint():
    roots = {runner.source_seed(life, rep, root=True) for life in runner.LIVES for rep in range(runner.ROOT_REPLICAS)}
    outer = {runner.source_seed(life, rep) for life in runner.LIVES for rep in range(runner.REPLICAS)}
    suffix = {runner.suffix_seed(root, rep) for root in range(32) for rep in range(runner.SUFFIX_REPLICAS)}
    assert len(roots) == 8 and len(outer) == 32 and len(suffix) == 256
    assert not roots & outer and not roots & suffix and not outer & suffix
    assert runner.source_seed(2, 1, root=True) == runner.BASE + 10000000 + 200000 + 1
    assert runner.source_seed(2, 1) == runner.BASE + 90000000 + 200000 + 1
    assert runner.suffix_seed(3, 1) == runner.BASE + 50000000 + 3000 + 1


def prepared():
    items = []
    for life in reversed(runner.LIVES):
        cases = []
        for policy in runner.POLICIES:
            for replica in range(runner.ROOT_REPLICAS):
                for index in runner.ROOT_INDICES:
                    available = index == 128
                    cases.append(dict(life=life, policy=policy, replica=replica, index=index,
                        source_eval_id=f'{life}/ROOT_{policy}/{replica}', available=available,
                        board=BOARD if available else None, local_root_id=0 if available else None))
        items.append(dict(life=life, cases=cases, roots=[dict(board=BOARD,
            actions=['DOWN', 'LEFT', 'UP'], predictions={'fixed': True}, candidates={'fixed': True})]))
    return items


def test_roster_preserves_all_32_slots_and_missing_roots_with_stable_deduplication():
    source = prepared(); roster = runner.assemble_roster(source)
    assert len(roster['cases']) == 32 and len(roster['roots']) == 4
    assert sum(c['available'] for c in roster['cases']) == 16
    assert all(c['root_id'] is None and c['board'] is None for c in roster['cases'] if not c['available'])
    assert all(c['root_id'] == c['life'] for c in roster['cases'] if c['available'])
    assert [r['life'] for r in roster['roots']] == [0, 1, 2, 3]
    assert roster['physical_attempts'] == 4 * 3 * 2 * 8
    assert roster['logical_attempts'] == 16 * 3 * 2 * 8
    source.reverse()
    assert roster == runner.assemble_roster(source)
    roster['roots'][0]['actions'].append('RIGHT')
    assert source[0]['roots'][0]['actions'] == ['DOWN', 'LEFT', 'UP']


def test_root_predictions_union_all_modes_queries_and_source_policy_candidates(monkeypatch):
    calls = []
    schedules = {(1., 'LEARNED'): ['LEFT', 'UP'], (1., 'CONSTANT'): ['DOWN', 'UP'],
                 (8., 'LEARNED'): ['RIGHT', 'LEFT'], (8., 'CONSTANT'): ['DOWN', 'RIGHT']}
    def choice(models, offsets, board, query, mode):
        calls.append((query['failure_penalty'], mode, offsets))
        actions = schedules[query['failure_penalty'], mode]
        candidates = [dict(action=a, value=float(i), comparison_value=float(i),
            score=0, afterstate=BOARD, anchor_value=float(i) + 10., success_probability=.25)
            for i, a in enumerate(actions)]
        all_actions = [{a: dict(anchor_value=float(i) + 10., success_probability=.25,
            score=0, afterstate=BOARD) for a in ('DOWN', 'LEFT', 'RIGHT', 'UP')} for i in range(2)]
        return dict(per_policy_candidates=candidates, per_policy_action_values=all_actions)
    monkeypatch.setattr(core, 'calibrated_choice', choice)
    result = runner.root_predictions([object(), object()], BOARD)
    assert len(calls) == 4 and all(offsets == [0., 0.] for _, _, offsets in calls)
    assert result['actions'] == ['DOWN', 'LEFT', 'RIGHT', 'UP']
    assert set(result['candidates']) == set(runner.QUERIES)
    assert all(set(modes) == {'LEARNED', 'CONSTANT'} for modes in result['candidates'].values())
    assert set(result['predictions']) == set(runner.POLICIES)
    assert result['predictions']['risk_goal']['LEFT']['value'] == 11.


def test_control_game_records_original_and_comparison_values_without_state_changes(monkeypatch):
    models = [SimpleNamespace(counts=Counter(), source=SimpleNamespace(updates=21 + i),
        updates=100 + i, successes=20 + i) for i in range(2)]
    calls = []
    def choice(actual_models, offsets, board, query, mode):
        calls.append((list(offsets), mode, query))
        actual_models[0].counts['source_choose_calls'] += 1
        actual_models[1].counts['source_choose_calls'] += 1
        rows = [dict(action='LEFT', value=1., comparison_value=1. + offsets[0], afterstate=BOARD),
                dict(action='UP', value=2., comparison_value=2. + offsets[1], afterstate=BOARD)]
        return dict(action='UP', policy_index=1, per_policy_candidates=rows)
    def episode(seed, act, p_four, max_steps):
        assert p_four == .1 and max_steps == 2000
        action = act(BOARD, 0)
        return dict(seed=seed, initial_board=BOARD, initial_spawns=[{}, {}], final_board=[2] + [0] * 15,
            steps=[dict(action=action, score=4, spawned_cell=15, spawned_rank=1)],
            status='LOST', return_score=4, steps_count=1, seconds=.001,
            work=dict(sampled_transitions=1, environment_random_draws=6))
    monkeypatch.setattr(core, 'calibrated_choice', choice)
    monkeypatch.setattr(runner, 'run_episode', episode)
    row = runner.control_game(models, [.5, -.25], 2, 'risk8', 'CAL_LEARNED', 3)
    assert calls == [([.5, -.25], 'LEARNED', runner.QUERIES['risk8'])]
    assert row['candidate_actions'] == [['LEFT', 'UP']]
    assert row['candidate_values'] == [[1., 2.]] and row['comparison_values'] == [[1.5, 1.75]]
    assert row['policy_indices'] == [1] and row['actions'] == ['UP']
    assert row['result']['model_state_before'] == row['result']['model_state_after']
    assert row['result']['controller_counts'] == dict(candidate_evaluations=2,
        policy_comparisons=1, offset_additions=2)
    assert row['seed'] == runner.source_seed(2, 3)
    runner.control_game(models, [.5, -.25], 2, 'risk8', 'UNCAL_CONSTANT', 3)
    assert calls[-1] == ([0., 0.], 'CONSTANT', runner.QUERIES['risk8'])
