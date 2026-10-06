"""Fresh SOURCE conditioning, new paired seeds and frozen V312 joint endpoints."""
import random
from statistics import mean

import pytest

from acfqp.science.fresh_confirmation_analysis_v312 import (
    ARMS, BOOTSTRAP_SEED, CELLS, CHECKPOINTS, FINAL_CELLS, STAGES, summarize,
)


def cohort(local=None, linear=1., mc=.5):
    local = local if local is not None else {cell:2. for cell, _, _ in CELLS}
    rows = []
    for life in range(64):
        stages = {stage:dict(planning_beliefs={},
            arms={arm:dict(evaluations={}) for arm in ARMS}) for stage in STAGES}
        for cell, stage, task in CELLS:
            p = .1 if task=='A' else .5
            stages[stage]['planning_beliefs'][task] = dict(estimated_p_four=p)
            gains = dict(SOURCE=0., CONTEXT_MC=mc, CONTEXT_LINEAR_WIN=linear,
                         CONTEXT_LOCAL=local[cell])
            for arm in ARMS:
                stages[stage]['arms'][arm]['evaluations'][task] = dict(estimated_p_four=p,
                    game_summaries=[dict(
                        seed=312900000000+(100000 if task=='B' else 0)+life*1000000+episode,
                        utility=life+(100. if task=='B' else 0.)+gains[arm],
                        status='LOST', steps=episode+1) for episode in range(32)])
        rows.append(dict(lifecycle=life, parent=life % 4, stages=stages))
    return rows


def evaluation(row, cell, arm='CONTEXT_LOCAL'):
    stage, task = cell.split('_')
    return row['stages'][stage]['arms'][arm]['evaluations'][task]


def games(row, cell, arm='CONTEXT_LOCAL'):
    return evaluation(row, cell, arm)['game_summaries']


def change_belief(row, cell, p):
    stage, task = cell.split('_')
    row['stages'][stage]['planning_beliefs'][task]['estimated_p_four'] = p
    for arm in ARMS:
        evaluation(row, cell, arm)['estimated_p_four'] = p


def test_confirmed_primary_keeps_six_contrasts_and_conditions_on_four_new_source_parents():
    result = summarize(cohort(mc=3.), draws=20)
    expected = dict(CONTEXT_LOCAL_minus_CONTEXT_LINEAR_WIN=1.,
        CONTEXT_LOCAL_minus_CONTEXT_MC=-1., CONTEXT_LINEAR_WIN_minus_CONTEXT_MC=-2.,
        CONTEXT_LOCAL_minus_SOURCE=2., CONTEXT_LINEAR_WIN_minus_SOURCE=1.,
        CONTEXT_MC_minus_SOURCE=3.)
    assert {key:value['mean'] for key,value in result['final_ab_contrasts'].items()}==expected
    assert result['primary_contrast']=='CONTEXT_LOCAL_minus_CONTEXT_LINEAR_WIN_FINAL_AB'
    assert result['primary_local_over_linear_supported'] and result['retained_gain_supported']
    assert not result['primary_local_over_mc_supported']
    assert result['retention_status']=={key:'SUPPORTED_NONDECREASE' for key in CHECKPOINTS}
    assert len(result['retention_status'])==7
    assert result['final_task_gain_supported']==dict(A=True,B=True)
    assert all(result['arms'][arm]['games']==64*32*9 for arm in ARMS)
    scope = result['evidence_scope']
    assert 'zero initialization and fresh seeds' in scope
    assert 'conditional on the four new frozen source parents' in scope
    assert 'previously learned deterministic dynamics program is shared' in scope
    assert 'do not include unconditional source-population uncertainty' in scope
    assert 'not reused or pooled' in scope


@pytest.mark.parametrize('failure', ['zero_primary', 'negative_net_source', 'raw_loss_with_source_drift'])
def test_joint_retained_gain_requires_new_primary_net_source_and_literal_retention(failure):
    rows = cohort()
    for row in rows:
        if failure=='zero_primary':
            for cell, _, _ in CELLS:
                for linear,local in zip(games(row,cell,'CONTEXT_LINEAR_WIN'),games(row,cell)):
                    linear['utility']=local['utility']
        elif failure=='negative_net_source':
            for cell, _, _ in CELLS:
                for arm,shift in (('CONTEXT_LOCAL',-3.),('CONTEXT_LINEAR_WIN',-3.)):
                    for game in games(row,cell,arm):
                        game['utility']+=shift
        else:
            change_belief(row,'A3_A',.4)
            for arm in ARMS:
                for game in games(row,'A3_A',arm):
                    game['utility']-=5.
    result = summarize(rows,draws=20)
    assert not result['retained_gain_supported']
    if failure=='zero_primary':
        assert not result['primary_local_over_linear_supported']
        assert result['final_net_gain_supported'] and result['retention_supported']
    elif failure=='negative_net_source':
        assert result['primary_local_over_linear_supported'] and result['retention_supported']
        assert not result['final_net_gain_supported']
    else:
        delta = result['checkpoint_contrasts']['A_final_vs_A1']
        assert delta['CONTEXT_LOCAL']['ci95']==delta['SOURCE']['ci95']==[-5.,-5.]
        assert result['primary_local_over_linear_supported'] and result['final_net_gain_supported']
        assert result['retention_status']['A_final_vs_A1']=='SUPPORTED_LOSS'


def test_average_confirmation_does_not_assert_individual_b_net_gain():
    result = summarize(cohort({cell:3. if task=='A' else -1. for cell, _, task in CELLS},
                              linear=.5),draws=20)
    assert result['final_ab_contrasts']['CONTEXT_LOCAL_minus_SOURCE']['ci95']==[1.,1.]
    assert result['retained_gain_supported']
    assert result['final_task_gain_supported']==dict(A=True,B=False)
    assert not result['final_dual_task_gain_supported']


def test_source_exact_identity_includes_actual_probability_across_intervening_banks():
    rows = cohort()
    for row in rows:
        change_belief(row,'B1_A',.4)
        for game in games(row,'B1_A','SOURCE'):
            game['utility']-=5.
    assert summarize(rows,draws=2)['complete_game_endpoints']
    source = games(rows[0],'A3_A','SOURCE')
    source[0]['utility']+=1.; source[1]['utility']-=1.
    with pytest.raises(ValueError,match='same task and actual planning probability'):
        summarize(rows,draws=2)


def test_legacy_task_label_belief_cannot_replace_missing_actual_selected_bank_belief():
    rows = cohort()
    rows[0]['evaluation_beliefs'] = dict(A=dict(estimated_p_four=.1), B=dict(estimated_p_four=.5))
    del rows[0]['stages']['A3']['planning_beliefs']['A']
    with pytest.raises(ValueError,match='selected bank planning belief'):
        summarize(rows,draws=2)


def test_fourth_arm_must_use_the_actual_common_cell_probability():
    rows = cohort()
    evaluation(rows[0],'A3_A','CONTEXT_LINEAR_WIN')['estimated_p_four'] = .5
    with pytest.raises(ValueError,match='All four V312 arms'):
        summarize(rows,draws=2)


@pytest.mark.parametrize('arm',['SOURCE','CONTEXT_LINEAR_WIN'])
def test_old_v311_evaluation_seed_is_not_fresh_confirmation(arm):
    rows = cohort()
    games(rows[0],'A1_A',arm)[0]['seed']=311900000000
    with pytest.raises(ValueError,match='fresh paired task seeds'):
        summarize(rows,draws=2)


def test_fresh_parent_bootstrap_uses_v312_seed_without_resampling_source_parents():
    rows = cohort(); values = [(life % 9)-4. for life in range(64)]
    for row,value in zip(rows,values):
        for cell in FINAL_CELLS:
            for local,linear in zip(games(row,cell),games(row,cell,'CONTEXT_LINEAR_WIN')):
                local['utility']=linear['utility']+value
    result = summarize(rows,draws=40)
    contrast = result['final_ab_contrasts']['CONTEXT_LOCAL_minus_CONTEXT_LINEAR_WIN']
    groups = [values[parent::4] for parent in range(4)]
    rng = random.Random(31200001)
    samples = sorted(mean(mean(rng.choices(group,k=16)) for group in groups) for _ in range(40))
    assert contrast['ci95']==pytest.approx([samples[0]+(samples[1]-samples[0])*.975,
                                          samples[38]+(samples[39]-samples[38])*.025])
    assert contrast['parent_mean_deltas']=={str(parent):mean(group) for parent,group in enumerate(groups)}
    assert contrast['lifecycle_deltas']=={str(life):value for life,value in enumerate(values)}
    assert contrast['interval_scope']=='CONDITIONAL_ON_FOUR_FROZEN_PARENTS'
    assert result['bootstrap_seed']==BOOTSTRAP_SEED==31200001


def test_cutoff_in_linear_confirmation_blocks_the_joint_claim_and_keeps_episode():
    rows = cohort()
    games(rows[0],'A2_B','CONTEXT_LINEAR_WIN')[0].update(status='CUTOFF',utility=-30.)
    result = summarize(rows,draws=2)
    assert not result['complete_game_endpoints'] and not result['retained_gain_supported']
    assert not result['primary_local_over_linear_supported'] and not result['final_net_gain_supported']
    assert result['retention_status']=={key:'INCOMPLETE_GAME_ENDPOINTS' for key in CHECKPOINTS}
    assert result['by_lifecycle'][0]['cells']['A2_B']['arms']['CONTEXT_LINEAR_WIN']['cutoff_episodes']==[0]
