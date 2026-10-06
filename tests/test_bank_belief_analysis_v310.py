"""Selected-bank probabilities, paired SOURCE identity and literal V310 retention."""
import random
from statistics import mean

import pytest

from acfqp.science.bank_belief_analysis_v310 import (
    ARMS, BOOTSTRAP_SEED, CELLS, CHECKPOINTS, FINAL_CELLS, STAGES, summarize,
)


def cohort(local=None, mc=None):
    local = local if local is not None else {
        cell:1. if task=='A' else 2. for cell, _, task in CELLS}
    mc = mc if mc is not None else {cell:.5 for cell, _, _ in CELLS}
    rows = []
    for life in range(64):
        stages = {stage:dict(planning_beliefs={},
            arms={arm:dict(evaluations={}) for arm in ARMS}) for stage in STAGES}
        for cell, stage, task in CELLS:
            p = .1 if task=='A' else .5
            stages[stage]['planning_beliefs'][task] = dict(estimated_p_four=p)
            for arm in ARMS:
                gain = local[cell] if arm=='CONTEXT_LOCAL' else mc[cell] if arm=='CONTEXT_MC' else 0.
                stages[stage]['arms'][arm]['evaluations'][task] = dict(estimated_p_four=p,
                    game_summaries=[dict(
                        seed=310900000000+(100000 if task=='B' else 0)+life*1000000+episode,
                        utility=life+(100. if task=='B' else 0.)+gain,
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


def test_final_supported_endpoints_keep_equal_task_weights_and_seven_zero_margin_retentions():
    result = summarize(cohort(), draws=20)
    assert result['final_ab_contrasts']['CONTEXT_LOCAL_minus_CONTEXT_MC']['ci95']==[1., 1.]
    assert result['final_ab_contrasts']['CONTEXT_LOCAL_minus_SOURCE']['ci95']==[1.5, 1.5]
    assert result['current_task_sequence_contrasts']['CONTEXT_LOCAL_minus_CONTEXT_MC']['mean']==pytest.approx(.9)
    assert result['retention_status']=={key:'SUPPORTED_NONDECREASE' for key in CHECKPOINTS}
    assert len(result['retention_status'])==7
    assert result['primary_local_over_mc_supported'] and result['final_net_gain_supported']
    assert result['final_dual_task_gain_supported'] and result['retained_gain_supported']
    assert all(result['arms'][arm]['games']==64*32*9 for arm in ARMS)
    assert result['by_lifecycle'][0]['cells']['A3_A']['estimated_p_four']==.1
    assert 'conditional on the four source parents' in result['evidence_scope']
    assert 'causal improvement over V309' in result['evidence_scope']
    assert 'Unsegmented full online discovery' in result['contribution_scope']


@pytest.mark.parametrize('local,mc,primary,net', [
    (-1., -2., True, False), (1., 3., False, True), (1., 1., False, True)])
def test_primary_and_source_net_gain_are_separate_strict_positive_conditions(local, mc, primary, net):
    result = summarize(cohort({cell:local for cell, _, _ in CELLS},
                              {cell:mc for cell, _, _ in CELLS}), draws=20)
    assert result['primary_local_over_mc_supported']==primary
    assert result['final_net_gain_supported']==net
    assert result['retention_supported']
    assert not result['retained_gain_supported']


def test_positive_equal_weight_final_gain_keeps_negative_a_gain_separate():
    result = summarize(cohort({cell:-1. if task=='A' else 3. for cell, _, task in CELLS}), draws=20)
    assert result['final_ab_contrasts']['CONTEXT_LOCAL_minus_SOURCE']['ci95']==[1., 1.]
    assert result['retained_gain_supported']
    assert result['final_task_gain_supported']==dict(A=False, B=True)
    assert not result['final_dual_task_gain_supported']


def test_changed_actual_bank_belief_allows_source_drift_but_keeps_literal_deployment_loss():
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
    assert checkpoint['CONTEXT_LOCAL']['ci95']==[-5., -5.]
    assert checkpoint['SOURCE']['ci95']==[-5., -5.]
    assert checkpoint['CONTEXT_LOCAL']['mean']-checkpoint['SOURCE']['mean']==0.
    assert result['retention_status']['A_final_vs_A1']=='SUPPORTED_LOSS'
    assert result['primary_local_over_mc_supported'] and result['final_net_gain_supported']
    assert not result['retention_supported'] and not result['retained_gain_supported']
    assert result['by_lifecycle'][0]['cells']['A3_A']['estimated_p_four']==.4
    assert 'not necessarily source-adjusted gain changes' in result['checkpoint_sign']


def test_source_same_probability_repeats_exactly_even_after_an_intervening_other_bank():
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


@pytest.mark.parametrize('error', ['arm_mismatch', 'missing_stage_belief', 'missing_arm_probability'])
def test_missing_or_inconsistent_selected_probability_is_rejected(error):
    rows = cohort()
    if error=='arm_mismatch':
        evaluation(rows[0], 'A3_A', 'SOURCE')['estimated_p_four'] = .5
    elif error=='missing_stage_belief':
        del rows[0]['stages']['A3']['planning_beliefs']['A']
    else:
        del evaluation(rows[0], 'A3_A')['estimated_p_four']
    with pytest.raises(ValueError, match='planning belief|planning probability'):
        summarize(rows, draws=2)


@pytest.mark.parametrize('arm', ['CONTEXT_LOCAL', 'SOURCE'])
def test_cutoff_is_retained_and_blocks_support_even_when_changed_source_belief_is_legal(arm):
    rows = cohort()
    change_belief(rows[0], 'A3_A', .4)
    games(rows[0], 'A3_A', arm)[0].update(status='CUTOFF', utility=-30.)
    result = summarize(rows, draws=2)
    assert not result['complete_game_endpoints']
    assert not result['primary_local_over_mc_supported'] and not result['final_net_gain_supported']
    assert result['final_task_gain_supported']==dict(A=False, B=False)
    assert result['retention_status']=={key:'INCOMPLETE_GAME_ENDPOINTS' for key in CHECKPOINTS}
    assert not result['retention_supported'] and not result['retained_gain_supported']
    assert result['by_lifecycle'][0]['cells']['A3_A']['arms'][arm]['cutoff_episodes']==[0]
    assert result['arms'][arm]['cutoffs']==1


def test_negative_retention_mean_with_interval_crossing_zero_remains_unresolved():
    rows = cohort()
    for life, row in enumerate(rows):
        for game in games(row, 'B2_A'):
            game['utility']+=1. if (life // 4) % 2 else -1.25
    result = summarize(rows, draws=40)
    contrast = result['checkpoint_contrasts']['A_after_B2']['CONTEXT_LOCAL']
    lower, upper = contrast['ci95']
    assert contrast['mean']<0. and lower<0.<upper
    assert result['retention_status']['A_after_B2']=='UNRESOLVED'
    assert not result['retained_gain_supported']


def test_paired_parent_bootstrap_uses_fresh_v310_seed_and_signed_lifecycle_deltas():
    rows = cohort(); values = [(life % 9)-4. for life in range(64)]
    for row, value in zip(rows, values):
        for cell in FINAL_CELLS:
            for local, mc in zip(games(row, cell), games(row, cell, 'CONTEXT_MC')):
                local['utility']=mc['utility']+value
    result = summarize(rows, draws=40)
    contrast = result['final_ab_contrasts']['CONTEXT_LOCAL_minus_CONTEXT_MC']
    groups = [values[parent::4] for parent in range(4)]
    rng = random.Random(31000001)
    samples = sorted(mean(mean(rng.choices(group, k=16)) for group in groups) for _ in range(40))
    assert contrast['ci95']==pytest.approx([samples[0]+(samples[1]-samples[0])*.975,
                                          samples[38]+(samples[39]-samples[38])*.025])
    assert contrast['parent_mean_deltas']=={str(parent):mean(group) for parent, group in enumerate(groups)}
    assert contrast['lifecycle_deltas']=={str(life):value for life, value in enumerate(values)}
    assert result['bootstrap_seed']==BOOTSTRAP_SEED==31000001


@pytest.mark.parametrize('error', ['old_seed', 'missing_game', 'running_game', 'missing_cell', 'wrong_parent'])
def test_incomplete_or_old_paired_endpoint_inventory_is_rejected(error):
    rows = cohort()
    if error=='old_seed': games(rows[0], 'A3_B')[0]['seed']=309900000000
    elif error=='missing_game': games(rows[0], 'A3_B').pop()
    elif error=='running_game': games(rows[0], 'A3_B')[0]['status']='RUNNING'
    elif error=='missing_cell': del rows[0]['stages']['A3']['arms']['CONTEXT_LOCAL']['evaluations']['B']
    else: rows[0]['parent']=1
    with pytest.raises(ValueError):
        summarize(rows, draws=2)
