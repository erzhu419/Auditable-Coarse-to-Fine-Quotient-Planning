"""Paired-gap fixtures test forced rewards, aliases, censoring and prefixes."""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path

import numpy as np
import pytest

from scripts import analyze_controlled_predictive_forced_actions_v128 as analysis

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    before = request.session.testsfailed
    yield
    path = ROOT/'reports/controlled_predictive_forced_actions_v128.analysis_checks.json'
    value = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    value['attempts'].append(dict(failures=request.session.testsfailed-before,
        environment_samples=0, model_samples=0, model_updates=0,
        scope='synthetic paired returns and deterministic recorded-prefix fixtures'))
    path.write_text(json.dumps(value, indent=2)+'\n')


def root():
    predictions = {}
    for policy, offset in (('reward', 0.), ('risk_goal', 2.)):
        predictions[policy] = dict(
            LEFT=dict(value=3.+offset, score=4, afterstate=[2]+[0]*15, success_probability=.4),
            DOWN=dict(value=2.+offset, score=0, afterstate=[0]*12+[1, 1, 0, 0], success_probability=.1))
    return dict(root_id=0, life=0, board=[1, 1]+[0]*14, actions=['DOWN', 'LEFT'], predictions=predictions)


def branch(action='LEFT', policy='risk_goal', replica=0, won=False, score=512):
    r = root(); immediate = r['predictions'][policy][action]['score']
    status = 'WON' if won else 'LOST'
    return dict(root_id=0, life=0, forced_action=action, policy=policy, replica=replica,
        seed=analysis.suffix_seed(0, replica), initial_board=r['board'], initial_spawns=[],
        final_board=[11]+[0]*15 if won else [1]*16, actions=[action, 'UP'],
        spawned_cells=[2, 3], spawned_ranks=[1, 1], scores=[immediate, score-immediate],
        result=dict(score=score, status=status, steps=2, components=analysis.old.components(score, status),
            utility=analysis.old.utility(score, status, policy),
            environment_counts=dict(sampled_transitions=2, environment_random_draws=4,
                ground_explicit_swipe_calls=2, forced_actions=1),
            policy_counts=dict(choose_calls=1), source_updates_before=42, source_updates_after=42, seconds=.1))


def experiment():
    indexed, valid = {}, {}
    for action in root()['actions']:
        for policy in analysis.POLICIES:
            for rep in range(16):
                value = branch(action, policy, rep, won=rep % (4 if action == 'LEFT' else 8) == 0,
                    score=512+(256 if action == 'LEFT' else 0)+rep*4)
                key = analysis.branch_key(value); indexed[key], valid[key] = value, True
    case = dict(case_id=0, life=0, query='risk8', replica=0, root_id=0, diverged=True,
        left_action='LEFT', right_action='DOWN')
    return case, root(), indexed, valid


def test_forced_trace_counts_immediate_reward_once_and_has_no_initial_spawns():
    row = branch()
    assert analysis.branch_valid(row, root(), 42)
    row['scores'][0] = 0
    assert not analysis.branch_valid(row, root(), 42)
    row = branch(); row['result']['environment_counts']['environment_random_draws'] += 4
    assert not analysis.branch_valid(row, root(), 42)
    row = branch(); row['result']['source_updates_after'] += 1
    assert not analysis.branch_valid(row, root(), 42)


def test_decomposition_uses_paired_success_covariance_and_retains_small_margins():
    case, board, indexed, valid = experiment()
    result = analysis.action_gap(case, board, indexed, valid)
    assert result['complete'] and result['decomposition_max_residual'] < 1e-12
    assert result['paired']['new_utility_gap']['mean'] == 2.125
    assert result['paired']['source_utility_gap']['mean'] == 1.125
    errors = result['replica_values']
    assert np.allclose(np.asarray(errors['anchor_gap_error'])+errors['success_correction_error'], errors['total_gap_error'])
    assert result['paired']['total_gap_error']['mc_se'] == pytest.approx(result['paired']['new_utility_gap']['mc_se'])
    # A machine-scale prediction difference remains a measured case.
    board['predictions']['risk_goal']['LEFT']['value'] = 1.+1e-14
    board['predictions']['risk_goal']['DOWN']['value'] = 1.
    board['predictions']['risk_goal']['LEFT']['success_probability'] = .1
    result = analysis.action_gap(case, board, indexed, valid)
    assert result['measured'] and 0 < result['predicted_new_gap'] < 1e-12


def test_one_missing_or_cutoff_suffix_suppresses_whole_paired_comparison():
    case, board, indexed, valid = experiment()
    indexed[(0, 'LEFT', 'risk_goal', 3)]['result']['status'] = 'CUTOFF'
    result = analysis.action_gap(case, board, indexed, valid)
    assert not result['complete'] and 'paired' not in result
    del indexed[(0, 'DOWN', 'reward', 0)]
    assert not analysis.policy_comparisons(board, 'risk8', 'DOWN', indexed, valid)['complete']


def test_repeated_root_aliases_do_not_create_false_precision():
    case, board, indexed, valid = experiment()
    measured = analysis.action_gap(case, board, indexed, valid)
    rows = []
    for life in analysis.LIVES:
        for rep in range(8):
            rows.append(dict(deepcopy(measured), life=life, replica=rep))
            rows.append(dict(case_id=100+rep, life=life, query='risk1', replica=rep,
                complete=True, measured=False))
    result = analysis.aggregate_cases(rows)
    se = result['four_life_means']['risk8']['paired']['new_utility_gap']['mc_se']
    assert se == pytest.approx(measured['paired']['new_utility_gap']['mc_se'])
    assert result['four_life_means']['risk1']['measured_cases'] == 0
    assert 'paired' not in result['four_life_means']['risk1']


def test_same_action_policy_gap_keeps_source_values_and_success_errors_separate():
    case, board, indexed, valid = experiment()
    result = analysis.policy_comparisons(board, 'risk8', 'LEFT', indexed, valid)
    assert result['complete'] and result['mc_policy_gap']['mean'] == 0.
    assert result['predicted_policy_gap'] == pytest.approx(2.8)
    assert result['policy_gap_error']['mean'] == pytest.approx(2.8)


def test_ground_prefix_reconstruction_finds_first_different_action():
    board = [1, 1]+[0]*14
    left = dict(seed=1, initial_board=board, actions=['DOWN', 'LEFT'],
        scores=[0, 4], spawned_cells=[0, 1], spawned_ranks=[1, 1])
    right = deepcopy(left); right['actions'][1] = 'RIGHT'
    counts = Counter(); result = analysis.inspect_prefix(left, right, counts)
    assert all(result['checks'].values()) and result['index'] == 1
    assert result['board'] == [1]+[0]*11+[1, 1, 0, 0]
    assert counts == dict(audit_prefix_swipes=1)
    right['spawned_ranks'][0] = 2
    assert not analysis.inspect_prefix(left, right, Counter())['checks']['shared_prefix']


def test_full_schema_dedup_and_no_divergence_cases_preserve_physical_budget(tmp_path, monkeypatch):
    from scripts import run_controlled_predictive_forced_actions_v128 as runner
    goal = dict(value=1e20, score=2048, afterstate=[11]+[0]*15, success_probability=1.)
    assert analysis.anchored_value(goal, 'risk_goal', 'risk1') == 2.
    folder = tmp_path/'run'; folder.mkdir()
    source = dict(schema='acfqp.forced_actions.v128.source', snapshots=[], inherited_costs=dict(scope='fixture'))
    roster = dict(cases=[], roots=[], physical_attempts=256, logical_attempts=2048,
        preparation=dict(prefix_counts=dict(recorded_spawns_replayed=32), lifecycles=[], seconds=.1))
    run = dict(settings=runner.settings(), inherited_costs=source['inherited_costs'],
        preparation=roster['preparation'], lifecycles=[], status='complete', seconds=1.)
    streams = {}
    for life in analysis.LIVES:
        state = root(); state.update(root_id=life, life=life); roster['roots'].append(state)
        snapshot = dict(life=life, rule={}, models={}, counts={}, control_trace=str(
            ROOT/'reports/controlled_predictive_anchored_success_v127'/f'life_{life}'/'control.jsonl.gz'))
        source['snapshots'].append(snapshot)
        prepared = dict(life=life, models={}, seconds=.1); roster['preparation']['lifecycles'].append(prepared)
        runtime = dict(life=life, trace=f'{life}/continuations', models={}, peak_weight_bytes=2*4*11**6*8)
        run['lifecycles'].append(runtime)
        for policy in analysis.POLICIES:
            snapshot['models'][policy] = dict(path=str(ROOT/'reports/controlled_predictive_ntuple_learning_v120'/f'life_{life}'/policy/'checkpoint_4096.npz'), updates=42, nonzero_weights=7)
            snapshot['counts'][policy] = dict(path=str(ROOT/'reports/controlled_predictive_anchored_success_v127'/f'life_{life}'/policy/'checkpoint_1024.npz'), updates=100, successes=10, constant=.1)
            costs = dict(source_updates_before=42, source_updates_after=42,
                source_load_counts=dict(checkpoint_loads=1, checkpoint_loaded_parameters=7),
                source_load_seconds=.1, source_setup_counts={}, source_setup_seconds=.1)
            runtime['models'][policy] = deepcopy(costs)
            prepared['models'][policy] = dict(costs, count_updates_before=100, count_updates_after=100,
                constant=.1, prediction_counts={}, count_load_counts=dict(checkpoint_loads=1,
                    checkpoint_loaded_addresses=4, checkpoint_loaded_count_entries=8))
        retained = []
        for query in analysis.QUERIES:
            for rep in range(8):
                pair = []
                diverged = query == 'risk1'
                for method in ('LEARNED_risk_goal', 'CONSTANT_risk_goal'):
                    action = 'DOWN' if diverged and method.startswith('LEARNED') else 'LEFT'
                    pred = dict(state['predictions']['risk_goal'][action])
                    if method.startswith('CONSTANT'):
                        pred['success_probability'] = .1
                    value = dict(method=method, query=query, checkpoint=1024, replica=rep,
                        eval_id=f'{life}/{method}/{query}/{rep}', seed=12700000000+life*100+rep,
                        initial_board=state['board'] if diverged else [10, 10]+[0]*14,
                        actions=[action], scores=[pred['score']] if diverged else [2048],
                        spawned_cells=[1], spawned_ranks=[1],
                        final_board=[11, 1]+[0]*14,
                        chosen_anchor_values=[pred['value']], chosen_success_probabilities=[pred['success_probability']],
                        chosen_values=[analysis.anchored_value(pred, 'risk_goal', query)])
                    retained.append(value); pair.append(value)
                roster['cases'].append(dict(case_id=len(roster['cases']), life=life, query=query, replica=rep,
                    left_eval_id=pair[0]['eval_id'], right_eval_id=pair[1]['eval_id'], diverged=diverged,
                    index=0 if diverged else None, board=state['board'] if diverged else None,
                    left_action='DOWN' if diverged else None, right_action='LEFT' if diverged else None,
                    shared_prefix_steps=0 if diverged else 1, root_id=life if diverged else None))
        streams[snapshot['control_trace']] = retained
        rows, totals = [], analysis.old.new_cost()
        for action in state['actions']:
            for policy in analysis.POLICIES:
                for rep in range(16):
                    value = branch(action, policy, rep); value.update(root_id=life, life=life,
                        seed=analysis.suffix_seed(life, rep))
                    rows.append(value); analysis.old.add_cost(totals, value)
        runtime.update(games=totals['games'], continuation_seconds=totals['seconds'],
            environment_counts=totals['environment_counts'], policy_counts=totals['policy_counts'], statuses=totals['statuses'])
        streams[str(folder/runtime['trace'])] = rows
    for name, value in (('source_capsule', source), ('roster', roster), ('run', run)):
        (folder/f'{name}.json').write_text(json.dumps(value))
    monkeypatch.setattr(analysis, 'read_rows', lambda path: iter(streams[str(path)]))
    monkeypatch.chdir(tmp_path)
    result = analysis.analyze(Path('run'))
    assert result['complete'] and result['primary_complete'], result['checks']
    assert result['costs']['physical_attempts'] == 256 and result['costs']['logical_attempts'] == 2048
    assert result['costs']['actual_new_environment_transitions'] == 512
    assert result['costs']['analysis_counts']['audit_prefix_swipes'] == 32
    assert result['panel']['risk1']['first_divergence_index']['max'] == 0
    assert result['panel']['risk8']['divergent_cases'] == 0
    assert result['policy_offset_summary']['four_life_means']['risk1']['complete']
