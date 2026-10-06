"""Frozen component effects, five-effect multiplicity and secondary retention."""
from math import floor
import random
from statistics import mean

import pytest

from acfqp.science.component_target_analysis_v315 import ARMS, COMBINATIONS, MECHANISMS, summarize


def evaluated(life, task, value, p):
    return dict(estimated_p_four=p, game_summaries=[dict(
        seed=315900000000+life*1000000+(100000 if task=='B' else 0)+episode,
        utility=life+(100. if task=='B' else 0.)+value,
        status='LOST', steps=episode+1) for episode in range(32)])


def cohort():
    rows = []
    for life in range(16):
        tasks = {}
        for index,task in enumerate(('A','B')):
            p = .23 if task=='A' else .73
            def version(arm, number):
                return dict(lifecycle=life, parent=life%4, context_id=index, arm=arm, version=number)
            mc, td, first = version('MC_LOCAL',2), version('TD_LOCAL',2), version('FIRST_LOCAL',0)
            components = dict(MC_MC=dict(reward_version=mc, win_version=mc),
                TD_MC=dict(reward_version=td, win_version=mc), MC_TD=dict(reward_version=mc, win_version=td),
                TD_TD=dict(reward_version=td, win_version=td), FIRST_LOCAL=dict(reward_version=first, win_version=first))
            values = dict(MC_MC=2., TD_MC=3., MC_TD=4., TD_TD=6., FIRST_LOCAL=2.5)
            tasks[task] = dict(context_id=index, estimated_p_four=p, head_components=components,
                evaluations={arm:evaluated(life,task,value,p) for arm,value in values.items()})
        rows.append(dict(lifecycle=life,parent=life%4,tasks=tasks))
    return rows


def shift(row, task, arm, amount):
    for game in row['tasks'][task]['evaluations'][arm]['game_summaries']:
        game['utility'] += amount


def test_exact_five_component_effects_interaction_and_secondary_combinations_on_fresh_games():
    result = summarize(cohort(),draws=20)
    expected = dict(reward_given_MC_WIN=1., reward_given_TD_WIN=2.,
        WIN_given_MC_reward=2., WIN_given_TD_reward=3., interaction=1.)
    assert {key:value['mean'] for key,value in result['mechanism_contrasts'].items()}==expected
    assert result['primary_family']==list(MECHANISMS)==list(expected)
    assert result['mechanism_family_status']=={key:'SUPPORTED_POSITIVE' for key in expected}
    assert result['mechanism_family_size']==5 and result['family_error_rate']==.05
    assert result['family_interval_level']==.99 and result['family_adjustment']=='BONFERRONI_FIVE_TWO_SIDED_EFFECTS'
    assert {key:value['mean'] for key,value in result['secondary_contrasts'].items()}==dict(
        TD_TD_minus_MC_MC=4., MC_MC_minus_FIRST_LOCAL=-.5, TD_MC_minus_FIRST_LOCAL=.5,
        MC_TD_minus_FIRST_LOCAL=1.5, TD_TD_minus_FIRST_LOCAL=3.5)
    assert list(result['arms'])==list(ARMS)
    assert all(value['games']==1024 for value in result['arms'].values())
    assert sum(value['games'] for value in result['arms'].values())==5120
    assert result['by_lifecycle'][0]['cells']['B']['estimated_p_four']==.73
    assert 'ci99' not in result['cells']['B']['mechanism_contrasts']['interaction']
    assert 'ci99' not in result['secondary_contrasts']['TD_TD_minus_MC_MC']
    assert 'No new training cohort' in result['evidence_scope']
    assert 'old evaluation outcomes are not pooled' in result['evidence_scope']
    assert 'realized component estimators' in result['contribution_scope']


def test_pointwise_positive_effect_cannot_pass_the_five_effect_family_when_99_interval_crosses_zero():
    rows = cohort()
    # Three adverse lives in different fixed groups: the 95% and 99% decisions differ.
    for row in rows[:3]:
        for task in ('A','B'):
            shift(row,task,'TD_MC',-2.5)
    result = summarize(rows,draws=2000)
    effect = result['mechanism_contrasts']['reward_given_MC_WIN']
    assert effect['ci95'][0]>0. and effect['ci99'][0]<0.<effect['ci99'][1]
    assert effect['family_status']==result['mechanism_family_status']['reward_given_MC_WIN']=='UNRESOLVED'
    assert effect['ci99'][0]<=effect['ci95'][0]<=effect['ci95'][1]<=effect['ci99'][1]


@pytest.mark.parametrize('case', ['negative_reward', 'zero_interaction'])
def test_negative_and_zero_mechanistic_effects_are_retained_without_winner_selection(case):
    rows = cohort()
    for row in rows:
        for task in ('A','B'):
            shift(row,task,'TD_MC' if case=='negative_reward' else 'TD_TD',-2. if case=='negative_reward' else -1.)
    result = summarize(rows,draws=20)
    key = 'reward_given_MC_WIN' if case=='negative_reward' else 'interaction'
    expected = -1. if case=='negative_reward' else 0.
    assert result['mechanism_contrasts'][key]['ci99']==[expected,expected]
    assert result['mechanism_family_status'][key]==('SUPPORTED_NEGATIVE' if case=='negative_reward' else 'UNRESOLVED')
    assert len(result['mechanism_contrasts'])==5
    assert 'winner' not in result and 'best_arm' not in result


def test_secondary_frozen_head_gain_and_retention_are_not_new_learning_confirmation_flags():
    result = summarize(cohort(),draws=20)
    assert result['secondary_contrasts']['TD_TD_minus_FIRST_LOCAL']['ci95']==[3.5,3.5]
    assert result['task_retention_supported']['TD_TD']
    assert result['task_retention_status']['MC_MC']==dict(A='SUPPORTED_LOSS',B='SUPPORTED_LOSS')
    assert all(key not in result for key in (
        'primary_self_improvement_supported','retained_improvement_supported','target_mechanism_supported'))
    assert 'do not select a winner or confirm new growth' in result['secondary_rule']
    assert 'new-training-cohort uncertainty' in result['evidence_scope']


def test_equal_ab_secondary_gain_cannot_hide_raw_task_loss():
    rows = cohort()
    for row in rows:
        shift(row,'A','MC_TD',6.)
        shift(row,'B','MC_TD',-2.)
    result = summarize(rows,draws=20)
    assert result['secondary_contrasts']['MC_TD_minus_FIRST_LOCAL']['mean']==3.5
    assert result['cells']['B']['secondary_contrasts']['MC_TD_minus_FIRST_LOCAL']['ci95']==[-.5,-.5]
    assert result['task_retention_status']['MC_TD']==dict(A='SUPPORTED_NONDECREASE',B='SUPPORTED_LOSS')
    assert not result['task_retention_supported']['MC_TD']


def test_new_bootstrap_seed_and_fixed_parent_pairing_generate_both_prespecified_intervals():
    rows = cohort()
    for row in rows:
        for task in ('A','B'):
            shift(row,task,'TD_MC',row['lifecycle']/8.)
    result = summarize(rows,draws=41)
    assert result['bootstrap_seed']==31500001
    rng = random.Random(31500001)
    groups = [[1.+life/8. for life in range(parent,16,4)] for parent in range(4)]
    samples = sorted(mean(mean(rng.choices(group,k=4)) for group in groups) for _ in range(41))
    def quantile(q):
        position=40*q; index=floor(position)
        return samples[index]+(samples[index+1]-samples[index])*(position-index)
    effect = result['mechanism_contrasts']['reward_given_MC_WIN']
    assert effect['ci95']==[quantile(.025),quantile(.975)]
    assert effect['ci99']==[quantile(.005),quantile(.995)]
    assert effect['parent_mean_deltas']=={str(parent):mean(group) for parent,group in enumerate(groups)}
    assert effect['interval_scope']=='CONDITIONAL_ON_FOUR_FROZEN_PARENTS_AND_REALIZED_V314_HEADS'


@pytest.mark.parametrize('case', ['missing_p', 'wrong_p', 'old_seed', 'wrong_component', 'missing_component'])
def test_actual_bank_belief_fresh_pairing_and_frozen_component_references_are_required(case):
    rows = cohort(); item = rows[0]['tasks']['B']
    message = 'selected-bank metadata'
    if case=='missing_p':
        rows[0]['evaluation_beliefs'] = dict(B=dict(estimated_p_four=.73))
        del item['estimated_p_four']
    elif case=='wrong_p':
        item['evaluations']['TD_MC']['estimated_p_four'] = .5; message='immutable V314 bank planning belief'
    elif case=='old_seed':
        item['evaluations']['FIRST_LOCAL']['game_summaries'][0]['seed'] = 314900000000; message='fresh paired seeds'
    elif case=='wrong_component':
        item['head_components']['TD_MC']['win_version'] = item['head_components']['TD_TD']['win_version']
        message='specified reward and WIN version components'
    else:
        del item['head_components']['MC_TD']
    with pytest.raises(ValueError,match=message):
        summarize(rows,draws=2)


@pytest.mark.parametrize('arm', ['FIRST_LOCAL','TD_MC'])
def test_any_cutoff_holds_the_entire_family_and_secondary_retention_without_omitting_lives(arm):
    rows = cohort()
    rows[3]['tasks']['A']['evaluations'][arm]['game_summaries'][0]['status'] = 'CUTOFF'
    result = summarize(rows,draws=20)
    assert not result['complete_game_endpoints'] and len(result['by_lifecycle'])==16
    assert set(result['mechanism_family_status'].values())=={'INCOMPLETE_GAME_ENDPOINTS'}
    assert all(set(status.values())=={'INCOMPLETE_GAME_ENDPOINTS'} for status in result['task_retention_status'].values())
    assert not any(result['task_retention_supported'].values())
    assert result['by_lifecycle'][3]['cells']['A']['arms'][arm]['cutoff_episodes']==[0]


@pytest.mark.parametrize('case', ['missing_life','wrong_parent'])
def test_same_complete_frozen_cohort_is_required_for_component_comparisons(case):
    rows = cohort()
    if case=='missing_life':
        rows.pop()
    else:
        rows[3]['parent'] = 0
    with pytest.raises(ValueError,match='all 16 realized V314 lives'):
        summarize(rows,draws=2)
