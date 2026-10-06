"""Own-FIRST growth and a target-only comparison under one fixed factual policy."""
from math import floor
import random
from statistics import mean

import pytest

from acfqp.science.local_target_analysis_v314 import BOOTSTRAP_SEED, PRIMARY_CONTRAST, TASKS, summarize


def evaluated(life, task, value, p, version=None):
    return dict(estimated_p_four=p, head_version=version, game_summaries=[dict(
        seed=314900000000+(100000 if task=='B' else 0)+life*1000000+episode,
        utility=life+(100. if task=='B' else 0.)+value, status='LOST', steps=episode+1)
        for episode in range(32)])


def dataset():
    return dict(games=[dict(episode=0, status='LOST', split='FIT')])


def cohort():
    rows = []
    for life in range(16):
        initial, rounds = {}, {'1':{}, '2':{}}
        for task in TASKS:
            p = .23 if task=='A' else .73
            first_version = dict(version=f'{life}_{task}_FIRST_0', updates=10)
            initial[task] = dict(planning_belief=dict(estimated_p_four=p), acquisition={}, dataset=dataset(),
                first_fits={}, head_versions=dict(FIRST_LOCAL=first_version), evaluations={
                    'SOURCE':dict(H2=evaluated(life, task, 0., p)),
                    'FIRST_LOCAL':dict(H2=evaluated(life, task, 2., p, first_version))})
            previous = dict(MC_LOCAL=first_version, TD_LOCAL=first_version)
            for number in (1, 2):
                arms = {}
                for arm,value in dict(MC_LOCAL=2.5 if number==1 else 3., TD_LOCAL=3. if number==1 else 4.).items():
                    version = dict(version=f'{life}_{task}_{arm}_{number}', updates=10+3*number)
                    fit = dict(trained_afterstates=3, alpha=.0025,
                        normalization_counts=dict(reward_parameter_writes=12, risk_parameter_writes=12))
                    if arm=='TD_LOCAL':
                        fit.update(frozen_game_start_predictions=True,
                                   bootstrap_version=previous[arm], frozen_batch_start_bootstrap=True,
                                   bootstrap_mode='BATCH_START_FROZEN_OWN_HEAD',
                                   target_artifact=dict(file=f'{life}_{task}_{number}.npz', saved_bytes=100))
                    else:
                        fit['frozen_game_start_targets'] = True
                    arms[arm] = dict(fit=fit, updates_before=10+3*(number-1), updates_after=10+3*number,
                        head_version=version, evaluations=dict(H2=evaluated(life, task, value, p, version)))
                    previous[arm] = version
                rounds[str(number)][task] = dict(quota=3, collectors=dict(FIXED_FIRST=dict(
                    actor_version=first_version, acquisition={}, dataset=dataset(), selection=dict(
                        eligible_samples=3, selected_samples=3, selection_rule='ALL_NONWINNING_COMPLETE_FIT_STATES'))), arms=arms)
        rows.append(dict(lifecycle=life, parent=life%4, initial_context_precondition_met=True,
                         initial=initial, rounds=rounds))
    return rows


def shift(evaluation, amount):
    for game in evaluation['game_summaries']:
        game['utility'] += amount


def final(row, task, arm='TD_LOCAL'):
    return row['rounds']['2'][task]['arms'][arm]['evaluations']['H2']


def test_six_contrasts_separate_own_first_target_intervention_and_source_with_no_direct_games():
    result = summarize(cohort(), draws=20)
    expected = dict(TD_LOCAL_minus_FIRST_LOCAL=2., TD_LOCAL_minus_MC_LOCAL=1., TD_LOCAL_minus_SOURCE=4.,
        MC_LOCAL_minus_FIRST_LOCAL=1., MC_LOCAL_minus_SOURCE=3., FIRST_LOCAL_minus_SOURCE=2.)
    assert {key:value['mean'] for key,value in result['final_ab_contrasts'].items()}==expected
    assert result['primary_contrast']==PRIMARY_CONTRAST=='TD_LOCAL_minus_FIRST_LOCAL_FINAL_AB'
    assert result['primary_self_improvement_supported'] and result['target_intervention_supported']
    assert result['retained_improvement_supported'] and result['target_mechanism_supported']
    assert result['task_retention_status']==dict(A='SUPPORTED_NONDECREASE', B='SUPPORTED_NONDECREASE')
    assert result['round_ab_contrasts']['1']['TD_LOCAL_minus_FIRST_LOCAL']['mean']==1.
    assert result['checkpoint_contrasts']['ROUND2_B']['MC_LOCAL']['mean']==1.
    assert result['mc_self_improvement_supported']
    assert {arm:value['games'] for arm,value in result['arms'].items()}==dict(
        SOURCE=1024, FIRST_LOCAL=1024, MC_LOCAL=2048, TD_LOCAL=2048)
    assert sum(value['games'] for value in result['arms'].values())==6144
    assert result['by_lifecycle'][0]['cells']['ROUND2_B']['estimated_p_four']==.73
    assert result['cells']['FIRST_A']['paired_contrasts']['FIRST_LOCAL_minus_SOURCE']['mean']==2.
    assert 'four frozen fresh V312 SOURCE parents' in result['evidence_scope']
    assert 'deterministic dynamics are reused' in result['evidence_scope']
    assert 'unconditional' in result['evidence_scope'] and 'development' in result['evidence_scope']
    assert 'does not equate either target with the H2 optimal counterfactual operator' in result['contribution_scope']


@pytest.mark.parametrize('case', ['source_without_growth', 'negative_source', 'intervention_zero', 'b_loss', 'negative_primary'])
def test_growth_intervention_source_and_both_raw_task_retention_have_distinct_rules(case):
    rows = cohort()
    for row in rows:
        for task in TASKS:
            if case=='source_without_growth':
                shift(final(row, task), -2.)
            elif case=='negative_source':
                shift(row['initial'][task]['evaluations']['FIRST_LOCAL']['H2'], -7.)
                for arm in ('MC_LOCAL', 'TD_LOCAL'):
                    shift(final(row, task, arm), -7.)
            elif case=='intervention_zero':
                shift(final(row, task, 'MC_LOCAL'), 1.)
            elif case=='b_loss':
                shift(final(row, task), 2. if task=='A' else -3.)
            else:
                shift(final(row, task), -3.)
    result = summarize(rows, draws=20)
    if case=='source_without_growth':
        assert result['final_net_gain_supported'] and result['task_retention_supported']
        assert result['primary_self_improvement_status']=='UNRESOLVED'
        assert not result['retained_improvement_supported']
    elif case=='negative_source':
        assert result['retained_improvement_supported'] and result['target_mechanism_supported']
        assert result['final_net_gain_status']=='SUPPORTED_LOSS' and not result['final_net_gain_supported']
    elif case=='intervention_zero':
        assert result['retained_improvement_supported']
        assert result['target_intervention_status']=='UNRESOLVED' and not result['target_mechanism_supported']
    elif case=='b_loss':
        assert result['primary_self_improvement_supported'] and result['target_intervention_supported']
        assert result['task_retention_status']['B']=='SUPPORTED_LOSS'
        assert result['final_task_improvement_supported']==dict(A=True, B=False)
        assert not result['retained_improvement_supported'] and not result['target_mechanism_supported']
    else:
        assert result['final_ab_contrasts']['TD_LOCAL_minus_FIRST_LOCAL']['ci95']==[-1., -1.]
        assert result['primary_self_improvement_status']=='SUPPORTED_LOSS'
        assert not result['retained_improvement_supported']


def test_first_round_losses_remain_literal_without_changing_final_retention_rule():
    rows = cohort()
    for row in rows:
        shift(row['rounds']['1']['B']['arms']['TD_LOCAL']['evaluations']['H2'], -2.)
        shift(row['rounds']['1']['A']['arms']['MC_LOCAL']['evaluations']['H2'], -3.)
    result = summarize(rows, draws=20)
    assert result['checkpoint_contrasts']['ROUND1_B']['TD_LOCAL']['ci95']==[-1., -1.]
    assert result['checkpoint_status']['ROUND1_A']['MC_LOCAL']=='SUPPORTED_LOSS'
    assert result['retained_improvement_supported']


def test_v314_bootstrap_uses_new_seed_and_within_each_fixed_parent_sampling():
    rows = cohort()
    for row in rows:
        for task in TASKS:
            shift(final(row, task), row['lifecycle']/8.)
    result = summarize(rows, draws=40)
    assert result['bootstrap_seed']==BOOTSTRAP_SEED==31400001
    rng = random.Random(31400001)
    groups = [[2.+life/8. for life in range(parent, 16, 4)] for parent in range(4)]
    samples = sorted(mean(mean(rng.choices(group, k=4)) for group in groups) for _ in range(40))
    expected = []
    for q in (.025, .975):
        position = 39*q; index = floor(position)
        expected.append(samples[index]+(samples[index+1]-samples[index])*(position-index))
    contrast = result['final_ab_contrasts']['TD_LOCAL_minus_FIRST_LOCAL']
    assert contrast['ci95']==expected
    assert contrast['parent_mean_deltas']=={str(parent):mean(group) for parent,group in enumerate(groups)}
    assert contrast['interval_scope']=='CONDITIONAL_ON_FOUR_FROZEN_PARENTS'


@pytest.mark.parametrize('case', ['updated_actor', 'wrong_snapshot', 'unfrozen_snapshot', 'unfrozen_predictions',
    'old_prediction_alias', 'missing_artifact', 'unequal_writes', 'partial_quota', 'reset_updates'])
def test_target_only_comparison_requires_fixed_actor_own_snapshot_and_equal_actual_work(case):
    rows = cohort(); batch = rows[0]['rounds']['2']['A']; item = batch['arms']['TD_LOCAL']
    message = 'batch-start bootstrap'
    if case=='updated_actor':
        batch['collectors']['FIXED_FIRST']['actor_version'] = rows[0]['rounds']['1']['A']['arms']['TD_LOCAL']['head_version']
        message = 'immutable FIRST_LOCAL v0'
    elif case=='wrong_snapshot':
        item['fit']['bootstrap_version'] = rows[0]['rounds']['1']['A']['arms']['MC_LOCAL']['head_version']
    elif case=='unfrozen_snapshot':
        item['fit']['frozen_batch_start_bootstrap'] = False
    elif case=='unfrozen_predictions':
        item['fit']['frozen_game_start_predictions'] = False; message = 'game-start residual rule'
    elif case=='old_prediction_alias':
        del item['fit']['frozen_game_start_predictions']
        item['fit']['frozen_game_start_targets'] = True; message = 'target metadata'
    elif case=='missing_artifact':
        del item['fit']['target_artifact']; message = 'target metadata'
    elif case=='unequal_writes':
        item['fit']['normalization_counts']['risk_parameter_writes'] += 1; message = 'equal actual writes'
    elif case=='partial_quota':
        batch['collectors']['FIXED_FIRST']['selection']['eligible_samples'] += 1; message = 'all eligible'
    else:
        item.update(updates_before=10, updates_after=13); message = 'continues its own'
    with pytest.raises(ValueError, match=message):
        summarize(rows, draws=2)


@pytest.mark.parametrize('case', ['missing_belief', 'wrong_p', 'old_seed', 'wrong_head'])
def test_actual_bank_p_new_eval_seed_and_actual_head_cannot_be_replaced_by_label_or_receipt_counter(case):
    rows = cohort(); row = rows[0]; item = row['rounds']['2']['B']['arms']['TD_LOCAL']
    message = 'immutable first-FIT bank'
    if case=='missing_belief':
        row['evaluation_beliefs'] = dict(B=dict(estimated_p_four=.73))
        del row['initial']['B']['planning_belief']; message = 'initial bank planning belief'
    elif case=='wrong_p':
        item['evaluations']['H2']['estimated_p_four'] = .5
    elif case=='old_seed':
        item['evaluations']['H2']['game_summaries'][0]['seed'] = 313900000000; message = 'fresh paired task seeds'
    else:
        item['evaluations']['H2']['head_version'] = row['rounds']['1']['B']['arms']['TD_LOCAL']['head_version']
        message = 'advanced actual private learner head'
    with pytest.raises(ValueError, match=message):
        summarize(rows, draws=2)


@pytest.mark.parametrize('where', ['initial', 'training', 'intermediate_eval', 'precondition'])
def test_incomplete_or_failed_bank_cohort_is_retained_and_all_support_held(where):
    rows = cohort(); row = rows[3]
    expected = 'INCOMPLETE_GAME_ENDPOINTS'
    if where=='initial':
        row['initial']['A']['dataset']['games'][0]['status'] = 'CUTOFF'
    elif where=='training':
        row['rounds']['2']['B']['collectors']['FIXED_FIRST']['dataset']['games'][0]['status'] = 'CUTOFF'
    elif where=='intermediate_eval':
        row['rounds']['1']['A']['arms']['MC_LOCAL']['evaluations']['H2']['game_summaries'][0]['status'] = 'CUTOFF'
    else:
        row['initial_context_precondition_met'] = False; expected = 'INITIAL_BANK_PRECONDITION_NOT_MET'
    result = summarize(rows, draws=2)
    assert len(result['by_lifecycle'])==16
    assert result['primary_self_improvement_status']==result['target_intervention_status']==expected
    assert not result['retained_improvement_supported'] and not result['target_mechanism_supported']
    if where=='precondition':
        assert result['initial_precondition_failed_lifecycles']==[3]
    elif where in ('initial', 'training'):
        assert result['training_cutoffs'][0]['lifecycle']==3
    else:
        assert result['by_lifecycle'][3]['cells']['ROUND1_A']['arms']['MC_LOCAL']['cutoff_episodes']==[0]
