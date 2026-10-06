"""First-context net gain, same-structure MC comparison and real return routes."""
from copy import deepcopy
import random
from statistics import mean

import pytest

from acfqp.science.first_adapt_analysis_v308 import ARMS, CELLS, STAGE_TASKS, summarize


def cohort(local=None, mc=None):
    local = local or dict(A1_A=1.,B_A=1.,B_B=2.,A2_A=1.,A2_B=2.)
    mc = mc or {cell:.5 for cell,_,_ in CELLS}
    rows = []
    for life in range(64):
        stages = {stage:dict(arms={arm:dict(evaluations={}) for arm in ARMS}) for stage in STAGE_TASKS}
        for cell,stage,task in CELLS:
            for arm in ARMS:
                gain = local[cell] if arm=='CONTEXT_LOCAL' else mc[cell] if arm=='CONTEXT_MC' else 0.
                stages[stage]['arms'][arm]['evaluations'][task] = dict(game_summaries=[
                    dict(seed=308900000000+(100000 if task=='B' else 0)+life*1000000+episode,
                         utility=life+(100. if task=='B' else 0.)+gain,status='LOST',steps=episode+1)
                    for episode in range(32)])
        rows.append(dict(lifecycle=life,parent=life % 4,stages=stages))
    return rows


def games(row,cell,arm='CONTEXT_LOCAL'):
    stage,task = cell.split('_')
    return row['stages'][stage]['arms'][arm]['evaluations'][task]['game_summaries']


def test_primary_is_final_local_over_matched_context_mc_and_net_gain_is_separate():
    result = summarize(cohort(),draws=20)
    assert result['primary_contrast']=='CONTEXT_LOCAL_minus_CONTEXT_MC_FINAL_AB'
    assert result['primary_local_over_mc_supported'] and result['final_net_gain_supported']
    assert result['final_ab_contrasts']['CONTEXT_LOCAL_minus_CONTEXT_MC']['ci95']==[1.,1.]
    assert result['final_ab_contrasts']['CONTEXT_LOCAL_minus_SOURCE']['ci95']==[1.5,1.5]
    assert result['current_task_sequence_contrasts']['CONTEXT_LOCAL_minus_CONTEXT_MC']['mean']==pytest.approx(5./6.)
    assert result['arms']['CONTEXT_LOCAL']['games']==64*32*5
    assert result['arms']['CONTEXT_LOCAL']['mean_final_ab_game_utility']==83.
    assert result['final_dual_task_gain_supported'] and result['retention_supported']
    assert result['retained_gain_supported']
    assert result['primary_local_over_mc_status']=='SUPPORTED_CONDITIONAL_ON_FOUR_FROZEN_PARENTS'
    assert 'conditional on the four source parents' in result['evidence_scope']


def test_primary_can_hold_below_source_and_cannot_establish_retained_net_gain():
    result = summarize(cohort({cell:-1. for cell,_,_ in CELLS},
                              {cell:-2. for cell,_,_ in CELLS}),draws=20)
    assert result['primary_local_over_mc_supported'] and result['retention_supported']
    assert not result['final_net_gain_supported'] and not result['retained_gain_supported']
    assert not result['final_dual_task_gain_supported']


def test_positive_source_gain_and_preservation_do_not_substitute_for_primary_mc_advantage():
    result = summarize(cohort(mc={cell:3. for cell,_,_ in CELLS}),draws=20)
    assert result['final_net_gain_supported'] and result['retention_supported']
    assert not result['primary_local_over_mc_supported'] and not result['retained_gain_supported']


def test_exact_zero_mc_advantage_is_not_supported_but_zero_retention_is():
    local = {cell:1. for cell,_,_ in CELLS}
    result = summarize(cohort(local,dict(local)),draws=20)
    assert result['final_ab_contrasts']['CONTEXT_LOCAL_minus_CONTEXT_MC']['ci95']==[0.,0.]
    assert not result['primary_local_over_mc_supported']
    assert result['retention_status']=={key:'SUPPORTED_NONDECREASE'
        for key in ('A_after_B','B_after_A2','A_final_vs_A1')}
    assert not result['retained_gain_supported']


def test_final_average_gain_and_preservation_do_not_assert_each_task_gain():
    result = summarize(cohort(dict(A1_A=-1.,B_A=-1.,B_B=3.,A2_A=-1.,A2_B=3.)),draws=20)
    assert result['primary_local_over_mc_supported'] and result['final_net_gain_supported']
    assert result['retained_gain_supported']
    assert result['final_task_gain_supported']==dict(A=False,B=True)
    assert not result['final_dual_task_gain_supported']


def test_gain_can_hold_while_b_retention_loss_blocks_retained_gain_aggregate():
    result = summarize(cohort(dict(A1_A=1.,B_A=1.,B_B=3.,A2_A=1.,A2_B=2.)),draws=20)
    assert result['primary_local_over_mc_supported'] and result['final_net_gain_supported']
    assert result['final_dual_task_gain_supported']
    assert result['retention_status']['B_after_A2']=='SUPPORTED_LOSS'
    assert not result['retention_supported'] and not result['retained_gain_supported']
    for contrast in result['checkpoint_contrasts'].values():
        assert contrast['SOURCE']['ci95']==[0.,0.]


def test_current_task_sequence_gain_cannot_replace_failed_final_primary():
    result = summarize(cohort(dict(A1_A=10.,B_A=0.,B_B=10.,A2_A=-1.,A2_B=-1.)),draws=20)
    assert result['current_task_sequence_contrasts']['CONTEXT_LOCAL_minus_CONTEXT_MC']['ci95'][0]>0.
    assert not result['primary_local_over_mc_supported'] and not result['retained_gain_supported']


def test_return_routing_loss_enters_primary_instead_of_optimistic_readonly_probe():
    rows = cohort()
    for row in rows:
        row['stages']['A2']['context_route'] = dict(created=False,wrong_return=True)
        row['stages']['A2']['readonly_original_A_probe_utility'] = 1e9
        for game in games(row,'A2_A'):
            game['utility']-=5.
    result = summarize(rows,draws=20)
    assert result['cells']['A2_A']['paired_contrasts']['CONTEXT_LOCAL_minus_SOURCE']['mean']==-4.
    assert result['final_ab_contrasts']['CONTEXT_LOCAL_minus_CONTEXT_MC']['mean']==-1.5
    assert result['retention_status']['A_final_vs_A1']=='SUPPORTED_LOSS'
    assert not result['primary_local_over_mc_supported']


def test_route_error_metadata_alone_cannot_force_or_cancel_utility_support():
    rows = cohort(); before = summarize(rows,draws=2)
    for row in rows:
        for stage in row['stages'].values():
            stage['context_route'] = dict(created=True,classification_error=True)
    assert summarize(rows,draws=2)==before


def test_crossing_zero_retention_is_unresolved():
    rows = cohort()
    for life,row in enumerate(rows):
        for game in games(row,'B_A'):
            game['utility']+=2. if (life // 4) % 2 else -2.
    result = summarize(rows,draws=40)
    lower,upper = result['checkpoint_contrasts']['A_after_B']['CONTEXT_LOCAL']['ci95']
    assert lower<0.<upper and result['retention_status']['A_after_B']=='UNRESOLVED'
    assert not result['retained_gain_supported']


def test_fixed_parent_bootstrap_uses_v308_seed_and_signed_new_lifecycle_results():
    rows = cohort(); values = [(life % 9)-4. for life in range(64)]
    for row,value in zip(rows,values):
        for cell in ('A2_A','A2_B'):
            for local,mc in zip(games(row,cell),games(row,cell,'CONTEXT_MC')):
                local['utility']=mc['utility']+value
    result = summarize(rows,draws=40)
    contrast = result['final_ab_contrasts']['CONTEXT_LOCAL_minus_CONTEXT_MC']
    groups = [values[parent::4] for parent in range(4)]
    rng = random.Random(30800001)
    samples = sorted(mean(mean(rng.choices(group,k=16)) for group in groups) for _ in range(40))
    assert contrast['ci95']==pytest.approx([samples[0]+(samples[1]-samples[0])*.975,
                                          samples[38]+(samples[39]-samples[38])*.025])
    assert contrast['parent_mean_deltas']=={str(parent):mean(group) for parent,group in enumerate(groups)}
    assert contrast['adverse_lifecycles']==[life for life,value in enumerate(values) if value<0.]
    assert contrast['lifecycle_deltas']=={str(life):value for life,value in enumerate(values)}
    assert result['bootstrap_seed']==30800001


@pytest.mark.parametrize('cell',[cell for cell,_,_ in CELLS])
def test_all_checkpoints_require_fresh_v308_task_seeds(cell):
    rows = cohort(); games(rows[0],cell)[0]['seed']=303900000000
    with pytest.raises(ValueError,match='fresh paired task seeds reused'):
        summarize(rows,draws=2)


def test_source_repeats_exactly_under_first_belief_for_each_task():
    rows = cohort(); games(rows[0],'B_A','SOURCE')[0]['utility']+=1.
    with pytest.raises(ValueError,match='SOURCE must repeat exactly'):
        summarize(rows,draws=2)


@pytest.mark.parametrize('arm',ARMS)
def test_cutoff_in_probe_cell_is_retained_and_blocks_supported_claims(arm):
    rows = cohort(); games(rows[0],'B_A',arm)[0].update(status='CUTOFF',utility=-30.)
    if arm=='SOURCE':
        for cell in ('A1_A','A2_A'):
            games(rows[0],cell,arm)[0].update(status='CUTOFF',utility=-30.)
    result = summarize(rows,draws=2)
    assert not result['complete_game_endpoints'] and not result['primary_local_over_mc_supported']
    assert not result['final_net_gain_supported'] and not result['retained_gain_supported']
    assert not result['final_dual_task_gain_supported']
    assert result['by_lifecycle'][0]['cells']['B_A']['arms'][arm]['cutoff_episodes']==[0]
    assert result['retention_status']['A_after_B']=='INCOMPLETE_GAME_ENDPOINTS'
    assert result['arms'][arm]['games']==10240


@pytest.mark.parametrize('error',['missing_life','wrong_parent','missing_game'])
def test_incomplete_new_sequence_inventory_is_rejected(error):
    rows = cohort()
    if error=='missing_life': rows.pop()
    elif error=='wrong_parent': rows[0]['parent']=1
    else: games(rows[0],'A2_B').pop()
    with pytest.raises(ValueError):
        summarize(rows,draws=2)


def test_old_evidence_training_metrics_and_order_cannot_change_new_primary():
    rows = cohort(); before = deepcopy(rows); result = summarize(rows,draws=2)
    assert rows==before and result==summarize(list(reversed(rows)),draws=2)
    for row in rows:
        row['old_v307_primary']=1e9
        for stage in row['stages'].values():
            stage['training_utility']=1e9
    assert result==summarize(rows,draws=2)
