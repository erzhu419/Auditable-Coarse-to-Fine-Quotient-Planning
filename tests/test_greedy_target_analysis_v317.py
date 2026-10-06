"""Coupled-operator receipts, fresh cohort identity and own-FIRST/retention wiring."""
from math import floor
import random
from statistics import mean

import pytest

from acfqp.science.greedy_target_analysis_v317 import summarize


def evaluated(life, task, value, p, version=None):
    return dict(estimated_p_four=p, head_version=version, game_summaries=[dict(
        seed=317900000000+life*1000000+(100000 if task=='B' else 0)+episode,
        utility=life+(100. if task=='B' else 0.)+value, status='LOST', steps=episode+1)
        for episode in range(32)])


def cohort():
    rows = []
    for life in range(16):
        initial, rounds = {}, {'1':{}, '2':{}}
        for task in ('A','B'):
            p = .23 if task=='A' else .73
            first = dict(version=f'v317_{life}_{task}_FIRST_0', updates=10)
            initial[task] = dict(planning_belief=dict(estimated_p_four=p),
                dataset=dict(games=[dict(episode=0,status='LOST',split='FIT')]),
                head_versions=dict(FIRST_LOCAL=first), evaluations={
                    'SOURCE':dict(H2=evaluated(life,task,0.,p)),
                    'FIRST_LOCAL':dict(H2=evaluated(life,task,2.,p,first))})
            previous = dict(SARSA_LOCAL=first,GREEDY_LOCAL=first)
            for number in (1,2):
                arms = {}
                for arm,value in dict(SARSA_LOCAL=2.5 if number==1 else 3., GREEDY_LOCAL=3. if number==1 else 4.).items():
                    version = dict(version=f'v317_{life}_{task}_{arm}_{number}',updates=10+3*number)
                    fit = dict(trained_afterstates=3,alpha=.0025,
                        normalization_counts=dict(reward_parameter_writes=12,risk_parameter_writes=12))
                    metadata = dict(schema='acfqp.local_sampled_sarsa_targets.v314',
                                    target_rule='RECORDED_SUCCESSOR_AFTERSTATE_NEXT_REWARD_UNDISCOUNTED')
                    if arm=='GREEDY_LOCAL':
                        metadata = dict(schema='acfqp.local_sampled_greedy_targets.v317',
                            target_rule='OBSERVED_POSTSPAWN_SINGLE_COMBINED_DIRECT_GREEDY_BRANCH')
                    fit.update(frozen_game_start_predictions=True,bootstrap_version=previous[arm],
                        frozen_batch_start_bootstrap=True,bootstrap_mode='BATCH_START_FROZEN_OWN_HEAD',
                        target_artifact=dict(file=f'v317_{life}_{task}_{arm}_{number}.npz',
                                             saved_bytes=100,metadata=metadata))
                    arms[arm] = dict(fit=fit,updates_before=10+3*(number-1),updates_after=10+3*number,
                        head_version=version,evaluations=dict(H2=evaluated(life,task,value,p,version)))
                    previous[arm] = version
                rounds[str(number)][task] = dict(quota=3,collectors=dict(FIXED_FIRST=dict(
                    actor_version=first,dataset=dict(games=[dict(episode=0,status='LOST',split='FIT')]),
                    selection=dict(eligible_samples=3,selected_samples=3,
                                   selection_rule='ALL_NONWINNING_COMPLETE_FIT_STATES'))),arms=arms)
        rows.append(dict(lifecycle=life,parent=life%4,initial_context_precondition_met=True,initial=initial,rounds=rounds))
    return rows


def shift(evaluation, amount):
    for game in evaluation['game_summaries']:
        game['utility'] += amount


def final(row, task, arm='GREEDY_LOCAL'):
    return row['rounds']['2'][task]['arms'][arm]['evaluations']['H2']


def test_new_operator_cohort_preserves_equal_task_fixed_parent_estimator_and_reports_sampled_scope():
    rows = cohort()
    for row in rows:
        for task in ('A','B'):
            shift(final(row,task),row['lifecycle']/8.)
    result = summarize(rows,draws=41)
    assert result['bootstrap_seed']==31700001
    assert result['primary_contrast']=='GREEDY_LOCAL_minus_FIRST_LOCAL_FINAL_AB'
    rng = random.Random(31700001)
    groups = [[2.+life/8. for life in range(parent,16,4)] for parent in range(4)]
    samples = sorted(mean(mean(rng.choices(group,k=4)) for group in groups) for _ in range(41))
    expected = []
    for q in (.025,.975):
        position=40*q; index=floor(position)
        expected.append(samples[index]+(samples[index+1]-samples[index])*(position-index))
    contrast = result['final_ab_contrasts']['GREEDY_LOCAL_minus_FIRST_LOCAL']
    assert contrast['ci95']==expected
    assert contrast['parent_mean_deltas']=={str(parent):mean(group) for parent,group in enumerate(groups)}
    assert contrast['interval_scope']=='CONDITIONAL_ON_FOUR_FROZEN_PARENTS'
    assert len(result['final_ab_contrasts'])==6 and sum(value['games'] for value in result['arms'].values())==6144
    scope = result['evidence_scope']
    assert 'new operator-control lifecycles' in scope
    assert 'no old target facts or evaluation outcomes are pooled' in scope
    assert 'four frozen fresh V312 SOURCE parents' in scope and 'unconditional' in scope
    assert 'deterministic dynamics are reused' in scope
    assert 'same branch' in result['contribution_scope']
    assert 'fixed FIRST state coverage' in result['contribution_scope']
    assert 'sampled observed' in result['contribution_scope'] and 'full expected' in result['contribution_scope']
    assert result['sarsa_self_improvement_supported']
    assert result['final_ab_contrasts']['GREEDY_LOCAL_minus_SARSA_LOCAL']['mean']==1.+15./16.


@pytest.mark.parametrize('old_family',[316900000000,315900000000])
def test_old_confirmation_or_component_evaluation_seeds_cannot_enter_the_new_operator_cohort(old_family):
    rows = cohort()
    final(rows[0],'B')['game_summaries'][0]['seed'] = old_family+100000
    with pytest.raises(ValueError,match='V317 requires 32 fresh paired task seeds'):
        summarize(rows,draws=2)


@pytest.mark.parametrize('case',['target_and_source_without_self','b_loss','negative_source'])
def test_operator_comparator_and_source_cannot_replace_own_first_growth_and_both_task_retention(case):
    rows = cohort()
    for row in rows:
        for task in ('A','B'):
            if case=='target_and_source_without_self':
                shift(final(row,task),-2.)
                shift(final(row,task,'SARSA_LOCAL'),-2.5)
            elif case=='b_loss':
                shift(final(row,task),2. if task=='A' else -3.)
            else:
                shift(row['initial'][task]['evaluations']['SOURCE']['H2'],7.)
    result = summarize(rows,draws=20)
    if case=='target_and_source_without_self':
        assert result['operator_intervention_supported'] and result['final_net_gain_supported']
        assert result['task_retention_supported'] and result['primary_self_improvement_status']=='UNRESOLVED'
        assert not result['retained_improvement_supported'] and not result['operator_mechanism_supported']
    elif case=='b_loss':
        assert result['primary_self_improvement_supported'] and result['operator_intervention_supported']
        assert result['task_retention_status']==dict(A='SUPPORTED_NONDECREASE',B='SUPPORTED_LOSS')
        assert not result['retained_improvement_supported'] and not result['operator_mechanism_supported']
    else:
        assert result['primary_self_improvement_supported'] and result['retained_improvement_supported']
        assert result['operator_mechanism_supported'] and result['final_net_gain_status']=='SUPPORTED_LOSS'


@pytest.mark.parametrize('case',['missing_bank_belief','wrong_parent'])
def test_new_operator_cohort_requires_actual_bank_metadata_and_all_four_frozen_source_groups(case):
    rows = cohort()
    if case=='missing_bank_belief':
        rows[0]['evaluation_beliefs'] = dict(A=dict(estimated_p_four=.23))
        del rows[0]['initial']['A']['planning_belief']; message='initial bank planning belief'
    else:
        rows[3]['parent'] = 0; message='all 16 new lifecycles'
    with pytest.raises(ValueError,match=message):
        summarize(rows,draws=2)


@pytest.mark.parametrize('arm',['SARSA_LOCAL','GREEDY_LOCAL'])
def test_both_operators_require_their_actual_own_previous_bootstrap_snapshot(arm):
    rows = cohort()
    rows[0]['rounds']['2']['A']['arms'][arm]['fit']['bootstrap_version'] = rows[0]['initial']['A']['head_versions']['FIRST_LOCAL']
    with pytest.raises(ValueError,match='both arms require their own batch-start bootstrap'):
        summarize(rows,draws=2)


@pytest.mark.parametrize('case',['sarsa_artifact_in_greedy','missing_artifact'])
def test_greedy_requires_its_native_single_coupled_branch_receipt_not_a_sarsa_target(case):
    rows = cohort(); fit = rows[0]['rounds']['1']['B']['arms']['GREEDY_LOCAL']['fit']
    if case=='sarsa_artifact_in_greedy':
        fit['target_artifact']['metadata'] = rows[0]['rounds']['1']['B']['arms']['SARSA_LOCAL']['fit']['target_artifact']['metadata']
        message='actual single combined-branch native target artifact'
    else:
        del fit['target_artifact']; message='target metadata'
    with pytest.raises(ValueError,match=message):
        summarize(rows,draws=2)
