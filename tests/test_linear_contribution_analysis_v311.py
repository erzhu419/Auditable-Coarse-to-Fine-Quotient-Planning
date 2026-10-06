"""Four-arm V311 contribution endpoints without asserting bitwise linear/MC equality."""
import random
from statistics import mean

import pytest

from acfqp.science.linear_contribution_analysis_v311 import (
    ARMS, BOOTSTRAP_SEED, CELLS, CHECKPOINTS, FINAL_CELLS, STAGES, summarize,
)


def cohort(local=None, linear=.75, mc=.5):
    local = local if local is not None else {
        cell:1. if task=='A' else 2. for cell, _, task in CELLS}
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
                        seed=311900000000+(100000 if task=='B' else 0)+life*1000000+episode,
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


def test_primary_is_equal_final_ab_local_over_linear_and_all_six_contrasts_remain():
    result = summarize(cohort(), draws=20)
    contrasts = result['final_ab_contrasts']
    expected = dict(CONTEXT_LOCAL_minus_CONTEXT_LINEAR_WIN=.75,
        CONTEXT_LOCAL_minus_CONTEXT_MC=1., CONTEXT_LINEAR_WIN_minus_CONTEXT_MC=.25,
        CONTEXT_LOCAL_minus_SOURCE=1.5, CONTEXT_LINEAR_WIN_minus_SOURCE=.75,
        CONTEXT_MC_minus_SOURCE=.5)
    assert {key:value['mean'] for key,value in contrasts.items()}==expected
    assert all(contrasts[key]['ci95']==[value,value] for key,value in expected.items())
    assert result['primary_contrast']=='CONTEXT_LOCAL_minus_CONTEXT_LINEAR_WIN_FINAL_AB'
    assert result['primary_local_over_linear_supported'] and result['primary_local_over_mc_supported']
    assert result['retained_gain_supported'] and result['complete_game_endpoints']
    assert result['retention_status']=={key:'SUPPORTED_NONDECREASE' for key in CHECKPOINTS}
    assert len(result['retention_status'])==7
    assert all(result['arms'][arm]['games']==64*32*9 for arm in ARMS)
    assert all(set(value)==set(ARMS) for value in result['checkpoint_contrasts'].values())
    assert result['current_task_sequence_contrasts']['CONTEXT_LOCAL_minus_CONTEXT_LINEAR_WIN']['mean']==pytest.approx(.65)
    assert 'conditional on the four source parents' in result['evidence_scope']
    assert 'V310 target cases and outcomes are not reused or pooled' in result['evidence_scope']
    assert 'floating point and action ties can differ' in result['contribution_scope']


@pytest.mark.parametrize('linear', [1., 2.])
def test_positive_local_mc_and_source_gains_do_not_replace_failed_new_primary(linear):
    result = summarize(cohort({cell:1. for cell, _, _ in CELLS}, linear=linear), draws=20)
    assert result['primary_local_over_mc_supported'] and result['final_net_gain_supported']
    assert result['retention_supported']
    assert result['final_ab_contrasts']['CONTEXT_LOCAL_minus_CONTEXT_LINEAR_WIN']['mean']==1.-linear
    assert not result['primary_local_over_linear_supported'] and not result['retained_gain_supported']


def test_descriptive_local_mc_advantage_is_not_an_additional_primary_gate():
    result = summarize(cohort({cell:1. for cell, _, _ in CELLS}, linear=.5, mc=2.), draws=20)
    assert result['primary_local_over_linear_supported'] and result['final_net_gain_supported']
    assert not result['primary_local_over_mc_supported']
    assert result['retained_gain_supported']


def test_primary_below_source_does_not_establish_retained_net_gain():
    result = summarize(cohort({cell:-1. for cell, _, _ in CELLS}, linear=-2., mc=-3.), draws=20)
    assert result['primary_local_over_linear_supported'] and result['retention_supported']
    assert not result['final_net_gain_supported'] and not result['retained_gain_supported']
    assert result['final_task_gain_supported']==dict(A=False, B=False)


def test_positive_average_and_retention_keep_b_gain_separate():
    result = summarize(cohort({cell:3. if task=='A' else -1. for cell, _, task in CELLS}), draws=20)
    assert result['final_ab_contrasts']['CONTEXT_LOCAL_minus_SOURCE']['ci95']==[1.,1.]
    assert result['retained_gain_supported']
    assert result['final_task_gain_supported']==dict(A=True, B=False)
    assert not result['final_dual_task_gain_supported']


def test_changed_selected_probability_keeps_raw_local_loss_despite_source_cancellation():
    rows = cohort({cell:2. for cell, _, _ in CELLS})
    for row in rows:
        change_belief(row, 'A3_A', .4)
        row['stages']['A3']['context_route'] = dict(context_id=2, created=True, wrong_return=True)
        row['stages']['A3']['readonly_original_task_probe_utility'] = 1e9
        for arm in ARMS:
            for game in games(row, 'A3_A', arm):
                game['utility']-=5.
    result = summarize(rows, draws=20)
    checkpoint = result['checkpoint_contrasts']['A_final_vs_A1']
    assert all(value['ci95']==[-5.,-5.] for value in checkpoint.values())
    assert checkpoint['CONTEXT_LOCAL']['mean']-checkpoint['SOURCE']['mean']==0.
    assert result['primary_local_over_linear_supported'] and result['final_net_gain_supported']
    assert result['retention_status']['A_final_vs_A1']=='SUPPORTED_LOSS'
    assert not result['retention_supported'] and not result['retained_gain_supported']
    assert result['by_lifecycle'][0]['cells']['A3_A']['estimated_p_four']==.4


def test_source_repeat_key_includes_task_and_probability_and_uses_full_episode_inventory():
    rows = cohort()
    for row in rows:
        change_belief(row, 'B1_A', .4)
        for game in games(row, 'B1_A', 'SOURCE'):
            game['utility']-=5.
    assert summarize(rows, draws=2)['complete_game_endpoints']
    source = games(rows[0], 'A3_A', 'SOURCE')
    source[0]['utility']+=1.; source[1]['utility']-=1.
    with pytest.raises(ValueError, match='same task and actual planning probability'):
        summarize(rows, draws=2)


@pytest.mark.parametrize('error', ['linear_mismatch', 'missing_stage_belief', 'missing_linear_probability'])
def test_all_four_arms_require_shared_actual_selected_probability(error):
    rows = cohort()
    if error=='linear_mismatch':
        evaluation(rows[0], 'A3_A', 'CONTEXT_LINEAR_WIN')['estimated_p_four'] = .5
    elif error=='missing_stage_belief':
        del rows[0]['stages']['A3']['planning_beliefs']['A']
    else:
        del evaluation(rows[0], 'A3_A', 'CONTEXT_LINEAR_WIN')['estimated_p_four']
    with pytest.raises(ValueError, match='planning belief|planning probability'):
        summarize(rows, draws=2)


def test_linear_cutoff_is_retained_and_blocks_all_support():
    rows = cohort()
    games(rows[0], 'A2_B', 'CONTEXT_LINEAR_WIN')[0].update(status='CUTOFF', utility=-30.)
    result = summarize(rows, draws=2)
    assert not result['complete_game_endpoints']
    assert not result['primary_local_over_linear_supported']
    assert not result['primary_local_over_mc_supported'] and not result['final_net_gain_supported']
    assert result['final_task_gain_supported']==dict(A=False,B=False)
    assert result['retention_status']=={key:'INCOMPLETE_GAME_ENDPOINTS' for key in CHECKPOINTS}
    assert not result['retained_gain_supported']
    assert result['by_lifecycle'][0]['cells']['A2_B']['arms']['CONTEXT_LINEAR_WIN']['cutoff_episodes']==[0]


def test_v311_parent_bootstrap_preserves_signed_new_primary_deltas():
    rows = cohort(); values = [(life % 9)-4. for life in range(64)]
    for row,value in zip(rows,values):
        for cell in FINAL_CELLS:
            for local,linear in zip(games(row,cell),games(row,cell,'CONTEXT_LINEAR_WIN')):
                local['utility']=linear['utility']+value
    result = summarize(rows,draws=40)
    contrast = result['final_ab_contrasts']['CONTEXT_LOCAL_minus_CONTEXT_LINEAR_WIN']
    groups = [values[parent::4] for parent in range(4)]
    rng = random.Random(31100001)
    samples = sorted(mean(mean(rng.choices(group,k=16)) for group in groups) for _ in range(40))
    assert contrast['ci95']==pytest.approx([samples[0]+(samples[1]-samples[0])*.975,
                                          samples[38]+(samples[39]-samples[38])*.025])
    assert contrast['parent_mean_deltas']=={str(parent):mean(group) for parent,group in enumerate(groups)}
    assert contrast['lifecycle_deltas']=={str(life):value for life,value in enumerate(values)}
    assert result['bootstrap_seed']==BOOTSTRAP_SEED==31100001


@pytest.mark.parametrize('error', ['old_seed', 'missing_linear_cell'])
def test_fourth_arm_requires_fresh_paired_evaluations_in_all_nine_cells(error):
    rows = cohort()
    if error=='old_seed':
        games(rows[0],'A3_B','CONTEXT_LINEAR_WIN')[0]['seed']=310900000000
    else:
        del rows[0]['stages']['A3']['arms']['CONTEXT_LINEAR_WIN']['evaluations']['B']
    with pytest.raises(ValueError):
        summarize(rows,draws=2)
