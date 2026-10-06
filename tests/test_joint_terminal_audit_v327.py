"""Actual member separation, current-head work and fresh utility reader checks."""
from copy import deepcopy
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import verify_joint_terminal_v327 as audit
from test_verify_win_learning_v324 import new_evaluation


@pytest.fixture(scope='module')
def epochs():
    roots = np.zeros((2, 16), dtype=np.int32); roots[1, 0] = 1
    rewards = np.asarray([[0., 2.], [2., 4.]])
    wins = np.asarray([[0., 1.], [1., 1.]])
    features = np.sort(audit.feature_addresses(roots), axis=1)
    writes = int(2+np.count_nonzero(features[:, 1:] != features[:, :-1]))
    norm = dict(rootgroups_processed=2, feature_extractions=2, feature_occurrences=64,
        feature_digit_reads=384, feature_address_multiply_adds=384, sort_calls=2, sort_items=64,
        sort_comparisons=100, denominator_occurrence_visits=64, rootgroup_unique_addresses=writes,
        win_gradient_products=writes, normalization_divisions=writes, parameter_update_multiplications=writes,
        rootgroup_parameter_commits=2, win_rootgroup_commits=2, win_parameter_writes=writes, native_workspace_bytes=512)
    fit = dict(method='GROUPED_WIN_ONLY_LOCAL', alpha=.0025, fitted_rootgroups=2, trained_afterstates=2,
        win_trained_afterstates=2, reward_trained_afterstates=0, replicates=2,
        frozen_rootgroup_predictions=True, reward_frozen=True, sampling_unit='ROOTGROUP_MEAN_OF_PROVIDED_REPLICAS',
        learning_counts=dict(rootgroup_updates=2, current_predictions=2, win_predictions=2,
            table_lookups=64, win_table_lookups=64, table_update_occurrences=64, table_updates=writes, win_parameter_updates=writes),
        target_counts=dict(rootgroups_targeted=2,win_replica_reads=8,win_target_mean_additions=4,target_mean_divisions=2,
            replica_noise_residuals=4,replica_noise_squares=4,replica_noise_accumulations=4,
            replica_noise_divisions=1,replica_noise_square_roots=1),
        normalization_counts=norm,representation_counts=dict(risk_sigmoid_evaluations=2,local_risk_table_lookups=64),
        replicate_noise=dict(win_replica_rms=np.sqrt(.125),definition='SQRT_MEAN_OVER_ALL_REPLICAS_OF_WITHIN_ROOTGROUP_CENTERED_SQUARES'),
        first_sample=dict(rootgroup=0,risk_target=.5,risk_probability=.5,risk_error=0.),
        last_sample=dict(rootgroup=1,risk_target=1.,risk_probability=.5,risk_error=.5),cpu_seconds=.001,seconds=.001)
    joint = deepcopy(fit); joint.update(method='GROUPED_LOCAL')
    for field in ('reward_frozen','win_trained_afterstates','reward_trained_afterstates'): joint.pop(field)
    joint['learning_counts'].update(table_lookups=128,table_updates=2*writes,
        reward_predictions=2,reward_table_lookups=64,reward_table_updates=writes)
    joint['target_counts'].update(reward_replica_reads=8,reward_target_mean_additions=4,
        target_mean_divisions=4,replica_noise_residuals=8,replica_noise_squares=8,replica_noise_accumulations=8,
        replica_noise_divisions=2,replica_noise_square_roots=2)
    joint['normalization_counts'].update(reward_gradient_products=writes,
        normalization_divisions=2*writes,parameter_update_multiplications=2*writes,
        reward_rootgroup_commits=2,reward_parameter_writes=writes)
    joint['representation_counts'].update(combined_value_additions=4,combined_value_multiplications=2)
    joint['replicate_noise']['reward_replica_rms'] = 1.
    joint['first_sample'].update(reward_target=1.,reward_prediction=0.,reward_error=1.,combined_prediction=0.)
    joint['last_sample'].update(reward_target=3.,reward_prediction=0.,reward_error=3.,combined_prediction=0.)
    zero = np.zeros(4*11**6); head=SimpleNamespace(reward=zero,terminal=zero)
    return fit,joint,roots,rewards,wins,head,writes


def test_real_two_member_counts_and_literal_previous_head_are_accepted(epochs):
    win,joint,roots,rewards,wins,head,writes=epochs
    arrays=dict(roots=roots,targetwin=wins,mean_win=wins.mean(axis=1))
    assert audit.check_win_epoch(win,arrays,head)==writes
    assert audit.check_joint_epoch(joint,roots,rewards,wins,head)==writes


@pytest.mark.parametrize('case', ['four_replica_claim','heldout_targets','reward_read_in_win','reward_write_in_win','wrong_prior_head'])
def test_wrong_fit_members_or_work_cannot_pass_win_reader(epochs,case):
    original,_,roots,_,wins,head,_=epochs; receipt=deepcopy(original)
    if case=='four_replica_claim': receipt['replicates']=4
    elif case=='heldout_targets': receipt['first_sample'].update(risk_target=1.,risk_error=.5)
    elif case=='reward_read_in_win': receipt['learning_counts']['reward_predictions']=2
    elif case=='reward_write_in_win': receipt['normalization_counts']['reward_parameter_writes']=1
    else: receipt['first_sample'].update(risk_probability=.75,risk_error=-.25)
    with pytest.raises(ValueError):
        audit.check_win_epoch(receipt,dict(roots=roots,targetwin=wins,mean_win=wins.mean(axis=1)),head)


@pytest.mark.parametrize('case', ['reward_label','unpaid_joint_writes','dropped_win_read','wrong_prior_reward'])
def test_joint_target_and_actual_two_head_commit_inventory_are_bound(epochs,case):
    _,original,roots,rewards,wins,head,_=epochs; receipt=deepcopy(original)
    if case=='reward_label': receipt['first_sample'].update(reward_target=9.,reward_error=9.)
    elif case=='unpaid_joint_writes': receipt['normalization_counts']['reward_parameter_writes']-=1
    elif case=='dropped_win_read': receipt['learning_counts']['win_table_lookups']=0
    else: receipt['first_sample'].update(reward_prediction=1.,reward_error=0.,combined_prediction=1.)
    with pytest.raises(ValueError): audit.check_joint_epoch(receipt,roots,rewards,wins,head)


def test_only_members_zero_one_reach_actual_target_arrays(monkeypatch):
    monkeypatch.setattr(audit,'GROUPS',2)
    outcomes=dict(reward_return=np.asarray([[1.,2.,91.,92.],[3.,4.,93.,94.]]),
        win=np.asarray([[0.,1.,1.,1.],[1.,1.,0.,0.]]),status=np.asarray([[-1,1,1,1],[1,1,-1,-1]]))
    rewards,wins=audit.training_labels(outcomes)
    assert np.array_equal(rewards,[[1.,2.],[3.,4.]])
    assert np.array_equal(wins,[[0.,1.],[1.,1.]])
    outcomes['reward_return'][1,3]=np.nan
    with pytest.raises(ValueError,match='naturally completed'): audit.training_labels(outcomes)


def test_validation_metrics_keep_member_noise_and_reward_win_covariance():
    from acfqp.science.joint_terminal_analysis_v327 import prediction_metrics
    rewards=np.asarray([2.,1.]); wins=np.asarray([.5,.5])
    outcomes=dict(reward_return=np.asarray([[2.,3.,4.,6.],[1.,3.,0.,0.]]),
        win=np.asarray([[0.,1.,0.,1.],[0.,1.,0.,1.]]))
    value=prediction_metrics(rewards,wins,outcomes['reward_return'],outcomes['win'],(2,3))
    audit.check_prediction_metrics(value,rewards,wins,outcomes,(2,3))
    bad=deepcopy(value);bad['utility_mse']=value['reward_mse']+64.*value['win_brier']
    with pytest.raises(ValueError): audit.check_prediction_metrics(bad,rewards,wins,outcomes,(2,3))
    with pytest.raises(ValueError): audit.check_prediction_metrics(value,rewards,wins,outcomes,(0,1))


def test_fresh_natural_seeds_cannot_be_replaced_with_v326_evaluation():
    value=new_evaluation()
    for episode,game in enumerate(value['game_summaries']):game['seed']=audit.evaluation_seed(0,'A',episode)
    assert audit.check_evaluation(value,0,'A',value['estimated_p_four'],value['head_version'])==np.mean([g['utility'] for g in value['game_summaries']])
    value['game_summaries'][0]['seed']-=10000000000
    with pytest.raises(ValueError,match='fresh V327'):audit.check_evaluation(value,0,'A',value['estimated_p_four'],value['head_version'])


def test_exact_member_partition_fresh_evaluation_and_prospective_stop_configuration():
    from acfqp.science.joint_terminal_run_v327 import configuration
    source=ROOT/'reports/terminal_win_v326/summary.json'
    assert audit.expected_configuration(source)==configuration(source)
    assert audit.evaluation_seed(15,'B',63)==3279015100063


@pytest.fixture(scope='module')
def complete():
    from test_joint_terminal_analysis_v327 import cohort
    from acfqp.science.joint_terminal_analysis_v327 import summarize
    rows=cohort();vectors=[]
    for row in rows:
        cells={}
        for task in audit.TASKS:
            cells['FIRST_'+task]={arm:float(np.mean([g['utility'] for g in value['game_summaries']]))
                for arm,value in row['initial'][task]['evaluations'].items()}
            for r in ('1','2'):
                cells['ROUND'+r+'_'+task]=dict(cells['FIRST_'+task],**{arm:float(np.mean([g['utility'] for g in item['evaluations']['game_summaries']]))
                    for arm,item in row['rounds'][r][task]['arms'].items()})
        vectors.append(dict(lifecycle=row['lifecycle'],parent=row['parent'],cells=cells))
    return rows,vectors,summarize(rows)


def test_primary_member_validation_and_confirmation_route_match_actual_vectors(complete):
    rows,vectors,result=complete
    audit.check_analysis(result,vectors,rows)


@pytest.mark.parametrize('case',['SOURCE_primary','independent_learning_claim','ignored_task_retention','overwritten_stop_route','erased_adverse_vector','equal_raw_claim'])
def test_prediction_or_source_gains_cannot_replace_own_first_gain_and_route(complete,case):
    rows,vectors,original=complete;result=deepcopy(original)
    if case=='SOURCE_primary':result['primary']=result['final_ab_contrasts']['JOINT_RETURN_minus_SOURCE']
    elif case=='independent_learning_claim':result['independent_learning_confirmation']=True
    elif case=='ignored_task_retention':result['task_retention_status']['B']='UNRESOLVED'
    elif case=='overwritten_stop_route':result['next_route']='STOP_FIXED_FIRST_TERMINAL_REGRESSION'
    elif case=='erased_adverse_vector':result['primary']['lifecycle_values'].pop('15')
    else:result['equal_total_raw_efficiency_evaluated']=True
    with pytest.raises(ValueError):audit.check_analysis(result,vectors,rows)
