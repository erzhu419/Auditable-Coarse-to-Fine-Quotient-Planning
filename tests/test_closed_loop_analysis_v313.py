"""Own-first growth, actual collector versions, active control and paired planners."""
import random
from statistics import mean

import pytest

from acfqp.science.closed_loop_analysis_v313 import (
    ARMS, BOOTSTRAP_SEED, DIRECT_ARMS, PAIRS, PRIMARY_CONTRAST, TASKS, summarize,
)


def evaluated(life, task, value, p):
    return dict(estimated_p_four=p, game_summaries=[dict(
        seed=313900000000+(100000 if task=='B' else 0)+life*1000000+episode,
        utility=life+(100. if task=='B' else 0.)+value,
        status='LOST', steps=episode+1) for episode in range(32)])


def dataset():
    return dict(games=[dict(episode=0, status='LOST', split='FIT')])


def cohort():
    rows = []
    for life in range(16):
        initial, rounds, direct = {}, {'1':{}, '2':{}}, {}
        for task in TASKS:
            p = .23 if task=='A' else .73
            versions = {arm:dict(version=f'{life}_{task}_{arm}_0', updates=10)
                        for arm in ('FIRST_LOCAL', 'FIRST_LINEAR')}
            first = dict(SOURCE=0., FIRST_LOCAL=2., FIRST_LINEAR=1.)
            initial[task] = dict(planning_belief=dict(estimated_p_four=p), dataset=dataset(),
                acquisition={}, first_fits={}, head_versions=versions,
                evaluations={arm:dict(H2=evaluated(life, task, value, p)) for arm,value in first.items()})
            previous = {arm:versions['FIRST_LINEAR' if arm=='CLOSED_LINEAR' else 'FIRST_LOCAL']
                        for arm in ('FIXED_LOCAL', 'CLOSED_LOCAL', 'CLOSED_LINEAR')}
            for number in (1, 2):
                if number==1:
                    actors = dict(SHARED_LOCAL=versions['FIRST_LOCAL'], CLOSED_LINEAR=versions['FIRST_LINEAR'])
                    values = dict(FIXED_LOCAL=3., CLOSED_LOCAL=3., CLOSED_LINEAR=1.5)
                else:
                    actors = dict(CLOSED_LOCAL=previous['CLOSED_LOCAL'], FIXED_LOCAL=versions['FIRST_LOCAL'],
                                  CLOSED_LINEAR=previous['CLOSED_LINEAR'])
                    values = dict(FIXED_LOCAL=3., CLOSED_LOCAL=4., CLOSED_LINEAR=2.)
                arms = {}
                for arm,value in values.items():
                    version = dict(version=f'{life}_{task}_{arm}_{number}', updates=10+3*number, changed_parameters=5)
                    arms[arm] = dict(fit=dict(trained_afterstates=3, alpha=.0025),
                        updates_before=10+3*(number-1), updates_after=10+3*number, head_version=version,
                        evaluations=dict(H2=evaluated(life, task, value, p)))
                    previous[arm] = version
                rounds[str(number)][task] = dict(quota=3, collectors={arm:dict(
                    actor_version=version, acquisition={}, dataset=dataset()) for arm,version in actors.items()}, arms=arms)
            direct[task] = {arm:evaluated(life, task, value, p) for arm,value in
                           dict(FIRST_LOCAL=1., FIRST_LINEAR=.5, CLOSED_LOCAL=3., CLOSED_LINEAR=1.5).items()}
        rows.append(dict(lifecycle=life, parent=life%4, initial_context_precondition_met=True,
                         initial=initial, rounds=rounds, final_direct=direct))
    return rows


def shift(evaluation, amount):
    for game in evaluation['game_summaries']:
        game['utility'] += amount


def final(row, task, arm='CLOSED_LOCAL'):
    return row['rounds']['2'][task]['arms'][arm]['evaluations']['H2']


def test_six_final_contrasts_use_own_first_primary_and_keep_feedback_and_planning_separate():
    result = summarize(cohort(), draws=20)
    expected = dict(CLOSED_LOCAL_minus_FIRST_LOCAL=2., CLOSED_LOCAL_minus_FIXED_LOCAL=1.,
        CLOSED_LOCAL_minus_CLOSED_LINEAR=2., CLOSED_LOCAL_minus_SOURCE=4.,
        CLOSED_LINEAR_minus_FIRST_LINEAR=1., CLOSED_LINEAR_minus_SOURCE=2.)
    assert {key:value['mean'] for key,value in result['final_ab_contrasts'].items()}==expected
    assert len(PAIRS)==6 and result['primary_contrast']==PRIMARY_CONTRAST
    assert result['primary_self_improvement_supported'] and result['feedback_supported']
    assert result['retained_improvement_supported'] and result['closed_loop_mechanism_supported']
    assert result['actor_change_premise_met'] and result['actor_change_premise_status']=='MET'
    assert result['round_ab_contrasts']['1']['CLOSED_LOCAL_minus_FIXED_LOCAL']['ci95']==[0., 0.]
    assert result['final_task_improvement_supported']==dict(A=True, B=True)
    assert result['task_retention_status']==dict(A='SUPPORTED_NONDECREASE', B='SUPPORTED_NONDECREASE')
    contributions = result['planning_contributions']
    assert {arm:contributions[arm]['final_ab']['mean'] for arm in DIRECT_ARMS}==dict(
        FIRST_LOCAL=1., FIRST_LINEAR=.5, CLOSED_LOCAL=1., CLOSED_LINEAR=.5)
    # Frozen references are evaluated once in H2, rather than counted again each round.
    assert result['arms']['SOURCE']['games']==16*2*32
    assert result['arms']['CLOSED_LOCAL']['games']==16*2*3*32
    assert set(result['arms'])==set(ARMS)
    assert result['by_lifecycle'][0]['cells']['ROUND2_B']['estimated_p_four']==.73
    scope = result['evidence_scope']
    assert 'development' in scope and 'four frozen fresh V312 SOURCE parents' in scope
    assert 'no old target outcomes are pooled' in scope and 'deterministic dynamics are reused' in scope
    assert 'coverage and collector outcomes' in result['contribution_scope']


@pytest.mark.parametrize('case', ['source_positive_without_self_gain', 'negative_net_source', 'feedback_zero', 'b_loss'])
def test_primary_feedback_net_source_and_task_retention_cannot_replace_each_other(case):
    rows = cohort()
    for row in rows:
        for task in TASKS:
            if case=='source_positive_without_self_gain':
                shift(final(row, task), -2.)
            elif case=='negative_net_source':
                shift(row['initial'][task]['evaluations']['FIRST_LOCAL']['H2'], -7.)
                shift(final(row, task), -7.)
            elif case=='feedback_zero':
                shift(final(row, task, 'FIXED_LOCAL'), 1.)
            else:
                shift(final(row, task), 2. if task=='A' else -3.)
    result = summarize(rows, draws=20)
    if case=='source_positive_without_self_gain':
        assert result['final_net_gain_supported']
        assert not result['primary_self_improvement_supported']
        assert result['primary_self_improvement_status']=='UNRESOLVED'
    elif case=='negative_net_source':
        assert result['primary_self_improvement_supported'] and result['retained_improvement_supported']
        assert not result['final_net_gain_supported'] and result['final_net_gain_status']=='SUPPORTED_LOSS'
    elif case=='feedback_zero':
        assert result['retained_improvement_supported'] and not result['closed_loop_mechanism_supported']
        assert result['feedback_status']=='UNRESOLVED'
    else:
        assert result['primary_self_improvement_supported'] and result['feedback_supported']
        assert result['task_retention_status']['B']=='SUPPORTED_LOSS'
        assert result['final_task_improvement_supported']==dict(A=True, B=False)
        assert not result['retained_improvement_supported'] and not result['closed_loop_mechanism_supported']


def test_intermediate_raw_losses_and_negative_direct_contributions_remain_visible():
    rows = cohort()
    for row in rows:
        shift(row['rounds']['1']['A']['arms']['CLOSED_LINEAR']['evaluations']['H2'], -2.)
        shift(row['final_direct']['B']['CLOSED_LOCAL'], 3.)
    result = summarize(rows, draws=20)
    assert result['checkpoint_contrasts']['ROUND1_A']['CLOSED_LINEAR']['ci95']==[-1.5, -1.5]
    assert result['checkpoint_status']['ROUND1_A']['CLOSED_LINEAR']=='SUPPORTED_LOSS'
    assert result['planning_contributions']['CLOSED_LOCAL']['by_task']['B']['ci95']==[-2., -2.]
    assert result['primary_self_improvement_supported']


@pytest.mark.parametrize('arm', ['CLOSED_LOCAL', 'CLOSED_LINEAR'])
def test_version_counter_without_actual_weight_changes_holds_mechanism_and_retains_contrasts(arm):
    rows = cohort()
    # This same receipt is the actual round-two actor reference.
    rows[0]['rounds']['1']['B']['arms'][arm]['head_version']['changed_parameters'] = 0
    result = summarize(rows, draws=2)
    assert result['primary_self_improvement_supported'] and result['feedback_supported']
    assert result['retained_improvement_supported'] and not result['closed_loop_mechanism_supported']
    assert not result['actor_change_premise_met']
    assert result['actor_change_premise_status']=='HOLD_NO_ACTOR_CHANGE'
    assert result['unchanged_round_two_actors']==[dict(lifecycle=0, task='B', arm=arm, version=1, changed_parameters=0)]
    assert result['final_ab_contrasts']['CLOSED_LOCAL_minus_FIRST_LOCAL']['ci95']==[2., 2.]


@pytest.mark.parametrize('collector', ['CLOSED_LOCAL', 'FIXED_LOCAL', 'CLOSED_LINEAR'])
def test_round_two_actor_metadata_must_link_to_updated_own_head_or_frozen_fixed_v0(collector):
    rows = cohort(); row = rows[0]
    wrong = (row['rounds']['1']['A']['arms']['FIXED_LOCAL']['head_version'] if collector=='FIXED_LOCAL'
             else row['initial']['A']['head_versions']['FIRST_LINEAR' if collector=='CLOSED_LINEAR' else 'FIRST_LOCAL'])
    row['rounds']['2']['A']['collectors'][collector]['actor_version'] = wrong
    with pytest.raises(ValueError, match='previous actual head version'):
        summarize(rows, draws=2)


@pytest.mark.parametrize('case', ['state_quota', 'update_delta', 'reset_history', 'unchanged_version'])
def test_actual_fits_have_equal_state_quotas_and_continuous_private_head_versions(case):
    rows = cohort(); item = rows[0]['rounds']['2']['B']['arms']['CLOSED_LINEAR']
    message = 'selected-state quota'
    if case=='state_quota':
        item['fit']['trained_afterstates'] += 1
    elif case=='update_delta':
        item['updates_after'] += 1
    elif case=='reset_history':
        item.update(updates_before=10, updates_after=13); message = 'continues its own'
    else:
        item['head_version'] = rows[0]['rounds']['1']['B']['arms']['CLOSED_LINEAR']['head_version']
        message = 'advance the actual'
    with pytest.raises(ValueError, match=message):
        summarize(rows, draws=2)


def test_task_label_map_cannot_replace_missing_initial_selected_bank_belief():
    rows = cohort(); row = rows[0]
    row['evaluation_beliefs'] = dict(A=dict(estimated_p_four=.23))
    del row['initial']['A']['planning_belief']
    with pytest.raises(ValueError, match='initial bank planning belief'):
        summarize(rows, draws=2)


def test_failed_initial_bank_precondition_keeps_the_life_and_holds_the_entire_cohort():
    rows = cohort(); rows[3]['initial_context_precondition_met'] = False
    result = summarize(rows, draws=2)
    assert result['complete_game_endpoints'] and not result['initial_context_precondition_met']
    assert result['initial_precondition_failed_lifecycles']==[3]
    assert len(result['by_lifecycle'])==16
    assert result['primary_self_improvement_status']=='INITIAL_BANK_PRECONDITION_NOT_MET'
    assert not result['primary_self_improvement_supported'] and not result['closed_loop_mechanism_supported']
    del rows[3]['initial_context_precondition_met']
    with pytest.raises(ValueError, match='observed initial distinct-bank precondition'):
        summarize(rows, draws=2)


@pytest.mark.parametrize('where', ['initial', 'round', 'direct'])
def test_all_actual_h2_and_direct_cells_use_the_same_immutable_bank_probability_and_new_seeds(where):
    rows = cohort(); row = rows[0]
    cell = (row['initial']['A']['evaluations']['FIRST_LINEAR']['H2'] if where=='initial'
            else final(row, 'A', 'CLOSED_LINEAR') if where=='round'
            else row['final_direct']['A']['CLOSED_LINEAR'])
    cell['estimated_p_four'] = .1
    with pytest.raises(ValueError, match='immutable first-FIT bank'):
        summarize(rows, draws=2)
    cell['estimated_p_four'] = .23; cell['game_summaries'][0]['seed'] = 312900000000
    with pytest.raises(ValueError, match='fresh paired task seeds'):
        summarize(rows, draws=2)


@pytest.mark.parametrize('where', ['intermediate_h2', 'first_direct', 'training'])
def test_cutoffs_block_support_and_keep_the_affected_checkpoint_or_factual_game(where):
    rows = cohort(); row = rows[0]
    if where=='training':
        row['rounds']['1']['A']['collectors']['SHARED_LOCAL']['dataset']['games'][0]['status'] = 'CUTOFF'
    else:
        cell = (row['rounds']['1']['A']['arms']['CLOSED_LINEAR']['evaluations']['H2']
                if where=='intermediate_h2' else row['final_direct']['A']['FIRST_LINEAR'])
        cell['game_summaries'][0]['status'] = 'CUTOFF'
    result = summarize(rows, draws=2)
    assert not result['complete_game_endpoints']
    assert result['primary_self_improvement_status']==result['feedback_status']=='INCOMPLETE_GAME_ENDPOINTS'
    assert not result['retained_improvement_supported'] and not result['closed_loop_mechanism_supported']
    if where=='training':
        assert result['training_cutoffs']==[dict(lifecycle=0, task='A', round='1', collector='SHARED_LOCAL', episode=0)]
    else:
        stored = (result['by_lifecycle'][0]['cells']['ROUND1_A']['arms']['CLOSED_LINEAR']
                  if where=='intermediate_h2' else result['by_lifecycle'][0]['direct']['A']['FIRST_LINEAR'])
        assert stored['cutoff_episodes']==[0]


def test_bootstrap_resamples_four_lives_within_each_frozen_parent_using_v313_seed():
    rows = cohort(); values = [(life%7)-3. for life in range(16)]
    for row,value in zip(rows, values):
        for task in TASKS:
            initial = row['initial'][task]['evaluations']['FIRST_LOCAL']['H2']['game_summaries']
            for before,after in zip(initial, final(row, task)['game_summaries']):
                after['utility'] = before['utility']+value
    result = summarize(rows, draws=40)
    contrast = result['final_ab_contrasts']['CLOSED_LOCAL_minus_FIRST_LOCAL']
    groups = [values[parent::4] for parent in range(4)]
    rng = random.Random(31300001)
    samples = sorted(mean(mean(rng.choices(group,k=4)) for group in groups) for _ in range(40))
    assert contrast['ci95']==pytest.approx([samples[0]+(samples[1]-samples[0])*.975,
                                          samples[38]+(samples[39]-samples[38])*.025])
    assert contrast['parent_mean_deltas']=={str(parent):mean(group) for parent,group in enumerate(groups)}
    assert result['bootstrap_seed']==BOOTSTRAP_SEED==31300001
    assert contrast['interval_scope']=='CONDITIONAL_ON_FOUR_FROZEN_PARENTS'
