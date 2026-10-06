"""Finite fixtures for matched data, terminal targets and paired comparisons."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from scripts import analyze_controlled_predictive_terminal_supervision_v137 as analysis

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    before = request.session.testsfailed
    yield
    path = ROOT/'reports/controlled_predictive_terminal_supervision_v137.analysis_checks.json'
    record = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    record['attempts'].append(dict(failures=request.session.testsfailed-before, tests_run=len(request.session.items),
        environment_samples=0, model_samples=0, model_updates=0,
        scope='synthetic retained targets, source numeric identity, matched counters, paired control and calibration'))
    path.write_text(json.dumps(record,indent=2)+'\n')


def rows():
    result = {}
    for life in analysis.LIVES:
        for rep in analysis.REPRESENTATIONS:
            for teacher in analysis.TEACHERS:
                for method in analysis.METHODS:
                    for replica in range(analysis.REPLICAS):
                        delta = (life+1)*(1 if teacher == 'risk1' else -1)
                        value = replica+life+({'TD':1,'TERMINAL':2}.get(method,0))*delta
                        result[(life,rep,teacher,method,replica)] = dict(result=dict(status='LOST',utility=value,score=4,steps=1))
    return result


def test_paired_comparisons_keep_each_teacher_and_history():
    indexed = rows(); result = analysis.full_game_comparison(indexed,{key:True for key in indexed})
    assert result['complete'] and len(result['cells']) == 4
    for cell in result['cells']:
        expected = 2.5 if cell['teacher_query'] == 'risk1' else -2.5
        assert cell['comparisons']['TD_minus_TEACHER']['mean'] == expected
        assert cell['comparisons']['TERMINAL_minus_TD']['mean'] == expected
        assert cell['comparisons']['TERMINAL_minus_TEACHER']['mean'] == 2*expected


def test_cutoff_suppresses_affected_comparison_without_dropping_the_game():
    indexed = rows(); key = (0,'SINGLE','risk1','TERMINAL',0)
    indexed[key]['result']['status'] = 'CUTOFF'
    result = analysis.full_game_comparison(indexed,{key:True for key in indexed})
    cell = result['cells'][0]
    assert not result['complete']
    assert cell['comparisons']['TERMINAL_minus_TD']['mean'] is None
    assert cell['comparisons']['TD_minus_TEACHER']['mean'] == 2.5
    assert cell['methods']['TERMINAL']['lifecycles'][0]['games'] == 16


def update(reward, success, raw=2., intercept=-.5):
    return dict(pre_raw_reward=raw,pre_reward=raw+intercept,pre_success=.5,
        target_reward=reward,target_success=success,raw_reward_target=reward-intercept,
        reward_error=reward-intercept-raw,success_error=success-.5)


def work(predictions, updates, rep='SINGLE'):
    counts = dict(joint_predictions=predictions,reward_predictions=predictions,success_predictions=predictions,
        sigmoid_evaluations=predictions,table_lookups=64*predictions,feature_address_occurrences=32*predictions,
        bank_0_prediction_occurrences=32*(predictions-updates),bank_0_update_occurrences=32*updates,
        td_updates=updates,reward_td_updates=updates,success_td_updates=updates,
        reward_table_update_occurrences=32*updates,success_table_update_occurrences=32*updates,
        reward_table_updates=8*updates,success_table_updates=8*updates,update_feature_squared_norm=128*updates)
    if rep == 'CAPACITY': counts.update(context_cell_reads=32*predictions,
        context_bank_selections=32*predictions,context_bank_offset_additions=32*predictions)
    return counts


def replay_fixture(method, status='WON', rep='SINGLE'):
    won = status == 'WON'; n = 3; count = n-int(won)
    scores = [1024,512,2048]
    predictions = [[2.,.5],[1.,.75],[0.,1.]] if won else [[2.,.5],[1.,.75],[.5,.25]]
    td_targets = [(scores[i]/2048.+predictions[i][0],predictions[i][1]) for i in range(1,n)]
    if not won: td_targets.append((0.,0.))
    td_updates = [update(*target) for target in td_targets]
    source = dict(episode=0,seed=42,status=status,scores=scores,
        next_components=[dict(reward=r,success=s) for r,s in predictions],
        joint_updates=[None]+td_updates[:2],terminal_update=None if won else td_updates[-1])
    targets = analysis.diagnostic_targets(scores,status)
    row = dict(method=method,episode=0,seed=42,status=status,steps=n,eligible_updates=count,
        updates_before=0,updates_after=count,predictions=predictions if method == 'TD' else [],
        updates=td_updates if method == 'TD' else [update(target['reward'],target['success']) for target in targets],
        td_source_comparison=None if method != 'TD' else dict(prediction_values_compared=6,prediction_values_matched=6,
            update_values_compared=8*count,update_values_matched=8*count,mismatches=0),
        model_counts=dict(work(count*(2 if method == 'TD' else 1),count,rep),value_calls=n if method == 'TD' else 0),
        replay_counts=dict(replay_swipes=n,replayed_transitions=n,replayed_spawn_events=n,
            newly_sampled_environment_transitions=0,newly_sampled_model_transitions=0),
        target_counts=(dict(reward_target_additions=n-1,terminal_boundary_targets=int(not won),eligible_targets=count)
            if method == 'TD' else dict(suffix_score_additions=n,terminal_labels=count,eligible_targets=count)))
    return row,source


@pytest.mark.parametrize('method,status', [('TD','WON'),('TD','LOST'),('TERMINAL','WON'),('TERMINAL','LOST')])
def test_replayed_suffix_and_bellman_targets_share_exact_eligible_updates(method,status):
    row,source = replay_fixture(method,status)
    assert all(analysis.replay_checks(row,source,method,-.5,'SINGLE',0).values())
    broken = deepcopy(row); broken['updates'][0]['target_reward'] += source['scores'][0]/2048.
    assert not analysis.replay_checks(broken,source,method,-.5,'SINGLE',0)['replay_targets']
    broken = deepcopy(row); broken['model_counts']['success_td_updates'] += 1
    assert not analysis.replay_checks(broken,source,method,-.5,'SINGLE',0)['replay_model_counts']


def test_td_source_identity_cannot_be_claimed_by_a_zero_mismatch_counter():
    row,source = replay_fixture('TD',rep='CAPACITY')
    assert all(analysis.replay_checks(row,source,'TD',-.5,'CAPACITY',0).values())
    row['predictions'][0][0] += .01
    checks = analysis.replay_checks(row,source,'TD',-.5,'CAPACITY',0)
    assert checks['replay_targets'] and not checks['exact_td_reproduction']


def test_active_prefix_and_unmatched_updates_are_rejected():
    row,source = replay_fixture('TERMINAL')
    source['status'] = 'ACTIVE'
    assert not analysis.replay_checks(row,source,'TERMINAL',-.5,'SINGLE',0)['replay_roster']
    row,source = replay_fixture('TERMINAL'); row['updates_before'] = 1
    assert not analysis.replay_checks(row,source,'TERMINAL',-.5,'SINGLE',0)['matched_updates']


def test_replaying_recorded_spawns_is_not_counted_as_new_sampling():
    row,source = replay_fixture('TD')
    row['replay_counts']['newly_sampled_environment_transitions'] = 3
    assert not analysis.replay_checks(row,source,'TD',-.5,'SINGLE',0)['replay_accounting']


def test_diagnostics_weight_games_equally_and_keep_three_heads_visible():
    metrics = ('reward_mse','success_brier','source_query_mse','reward_bias','success_bias','source_query_bias')
    games = []
    for rep in analysis.REPRESENTATIONS:
        for teacher in analysis.TEACHERS:
            for life in analysis.LIVES:
                for replica in range(analysis.REPLICAS):
                    row = dict(life=life,representation=rep,teacher_query=teacher,replica=replica)
                    for method,multiple in zip(analysis.PHASES,(1.,2.,.5)):
                        error = 100.*multiple if replica == 0 else 0.
                        row[method] = dict(complete=True,eligible_afterstates=1000 if replica == 0 else 1,
                            **{metric:error for metric in metrics})
                    games.append(row)
    result = analysis.calibration_summary(games)
    assert result['complete']
    assert all(cell['means']['INITIAL_H2']['reward_mse'] == 6.25 for cell in result['cells'])
    assert all(cell['changes']['TERMINAL_minus_TD']['reward_mse'] == -9.375 for cell in result['cells'])
