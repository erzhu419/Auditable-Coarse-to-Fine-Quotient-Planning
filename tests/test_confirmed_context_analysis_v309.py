"""Frozen V309 final advantage, repeated actual routes and strict first-reference retention."""
from copy import deepcopy
import random
from statistics import mean

import pytest

from acfqp.science.confirmed_context_analysis_v309 import (
    ARMS, BOOTSTRAP_SEED, CELLS, CHECKPOINTS, CURRENT_TASK_CELLS, FINAL_CELLS,
    STAGES, STAGE_TASKS, summarize,
)


def cohort(local=None, mc=None):
    local = local if local is not None else {
        cell:1. if task=='A' else 2. for cell, _, task in CELLS}
    mc = mc if mc is not None else {cell:.5 for cell, _, _ in CELLS}
    rows = []
    for life in range(64):
        stages = {stage:dict(arms={arm:dict(evaluations={}) for arm in ARMS}) for stage in STAGES}
        for cell, stage, task in CELLS:
            for arm in ARMS:
                gain = local[cell] if arm=='CONTEXT_LOCAL' else mc[cell] if arm=='CONTEXT_MC' else 0.
                stages[stage]['arms'][arm]['evaluations'][task] = dict(game_summaries=[
                    dict(seed=309900000000+(100000 if task=='B' else 0)+life*1000000+episode,
                         utility=life+(100. if task=='B' else 0.)+gain, status='LOST', steps=episode+1)
                    for episode in range(32)])
        rows.append(dict(lifecycle=life, parent=life % 4, stages=stages))
    return rows


def games(row, cell, arm='CONTEXT_LOCAL'):
    stage, task = cell.split('_')
    return row['stages'][stage]['arms'][arm]['evaluations'][task]['game_summaries']


def test_final_primary_and_whole_current_sequence_have_distinct_frozen_estimands():
    result = summarize(cohort(), draws=20)
    assert STAGES==('A1', 'B1', 'A2', 'B2', 'A3')
    assert STAGE_TASKS=={'A1':('A',), 'B1':('A', 'B'), 'A2':('A', 'B'),
                        'B2':('A', 'B'), 'A3':('A', 'B')}
    assert CURRENT_TASK_CELLS==('A1_A', 'B1_B', 'A2_A', 'B2_B', 'A3_A')
    assert FINAL_CELLS==('A3_A', 'A3_B')
    assert list(result['cells'])==['A1_A', 'B1_A', 'B1_B', 'A2_A', 'A2_B',
                                  'B2_A', 'B2_B', 'A3_A', 'A3_B']
    assert result['primary_contrast']=='CONTEXT_LOCAL_minus_CONTEXT_MC_FINAL_AB'
    assert result['final_ab_contrasts']['CONTEXT_LOCAL_minus_CONTEXT_MC']['ci95']==[1., 1.]
    assert result['final_ab_contrasts']['CONTEXT_LOCAL_minus_SOURCE']['ci95']==[1.5, 1.5]
    assert result['current_task_sequence_contrasts']['CONTEXT_LOCAL_minus_CONTEXT_MC']['mean']==pytest.approx(.9)
    assert result['arms']['CONTEXT_LOCAL']['mean_final_ab_game_utility']==83.
    assert result['arms']['CONTEXT_LOCAL']['mean_current_task_sequence_game_utility']==pytest.approx(72.9)
    assert all(result['arms'][arm]['games']==64*32*9 for arm in ARMS)
    assert result['primary_local_over_mc_supported'] and result['final_net_gain_supported']
    assert result['final_dual_task_gain_supported'] and result['retention_supported']
    assert result['retained_gain_supported'] and result['complete_game_endpoints']
    assert result['primary_local_over_mc_status']=='SUPPORTED_CONDITIONAL_ON_FOUR_FROZEN_PARENTS'
    assert 'conditional on the four source parents' in result['evidence_scope']
    assert 'V308 target cases and outcomes are not reused or pooled' in result['evidence_scope']
    assert 'unequal capacity and computation' in result['contribution_scope']


def test_primary_below_source_cannot_establish_retained_net_gain():
    result = summarize(cohort({cell:-1. for cell, _, _ in CELLS},
                              {cell:-2. for cell, _, _ in CELLS}), draws=20)
    assert result['primary_local_over_mc_supported'] and result['retention_supported']
    assert not result['final_net_gain_supported'] and not result['retained_gain_supported']
    assert result['final_task_gain_supported']==dict(A=False, B=False)


def test_positive_source_gain_and_retention_cannot_replace_mc_advantage():
    result = summarize(cohort(mc={cell:3. for cell, _, _ in CELLS}), draws=20)
    assert result['final_net_gain_supported'] and result['retention_supported']
    assert not result['primary_local_over_mc_supported'] and not result['retained_gain_supported']


def test_exact_zero_primary_is_not_supported_and_all_seven_zero_retention_intervals_are():
    local = {cell:1. for cell, _, _ in CELLS}
    result = summarize(cohort(local, dict(local)), draws=20)
    assert result['final_ab_contrasts']['CONTEXT_LOCAL_minus_CONTEXT_MC']['ci95']==[0., 0.]
    assert not result['primary_local_over_mc_supported']
    assert result['retention_status']=={key:'SUPPORTED_NONDECREASE' for key in CHECKPOINTS}
    assert len(result['retention_status'])==7
    assert result['retention_supported'] and not result['retained_gain_supported']


def test_equal_weight_final_gain_does_not_assert_individual_a_gain():
    result = summarize(cohort({cell:-1. if task=='A' else 3. for cell, _, task in CELLS}), draws=20)
    assert result['final_ab_contrasts']['CONTEXT_LOCAL_minus_SOURCE']['ci95']==[1., 1.]
    assert result['primary_local_over_mc_supported'] and result['final_net_gain_supported']
    assert result['retained_gain_supported']
    assert result['final_task_gain_supported']==dict(A=False, B=True)
    assert not result['final_dual_task_gain_supported']


@pytest.mark.parametrize('name,after,before',[
    ('A_after_B1', 'B1_A', 'A1_A'),
    ('A_return_A2', 'A2_A', 'A1_A'),
    ('A_after_B2', 'B2_A', 'A1_A'),
    ('A_final_vs_A1', 'A3_A', 'A1_A'),
    ('B_after_A2', 'A2_B', 'B1_B'),
    ('B_return_B2', 'B2_B', 'B1_B'),
    ('B_final_vs_B1', 'A3_B', 'B1_B'),
])
def test_each_first_reference_endpoint_loss_blocks_retention_even_with_final_gain(name, after, before):
    local = {cell:3. for cell, _, _ in CELLS}; local[after]=2.
    result = summarize(cohort(local), draws=20)
    assert CHECKPOINTS[name]==(after, before)
    assert result['checkpoint_contrasts'][name]['CONTEXT_LOCAL']['ci95']==[-1., -1.]
    assert result['retention_status'][name]=='SUPPORTED_LOSS'
    assert all(value=='SUPPORTED_NONDECREASE' for key, value in result['retention_status'].items() if key!=name)
    assert result['primary_local_over_mc_supported'] and result['final_net_gain_supported']
    assert result['final_dual_task_gain_supported']
    assert not result['retention_supported'] and not result['retained_gain_supported']
    assert all(contrast['SOURCE']['ci95']==[0., 0.] for contrast in result['checkpoint_contrasts'].values())


def test_current_sequence_gain_cannot_replace_failed_a3_primary_or_use_a2_as_final():
    local = {cell:10. for cell, _, _ in CELLS}; local.update(A3_A=-1., A3_B=-1.)
    result = summarize(cohort(local), draws=20)
    assert result['current_task_sequence_contrasts']['CONTEXT_LOCAL_minus_CONTEXT_MC']['ci95'][0]>0.
    assert result['cells']['A2_A']['paired_contrasts']['CONTEXT_LOCAL_minus_CONTEXT_MC']['ci95'][0]>0.
    assert result['final_ab_contrasts']['CONTEXT_LOCAL_minus_CONTEXT_MC']['ci95']==[-1.5, -1.5]
    assert not result['primary_local_over_mc_supported'] and not result['retained_gain_supported']


@pytest.mark.parametrize('cell,retention',[
    ('A2_A', 'A_return_A2'), ('B2_B', 'B_return_B2'), ('A3_A', 'A_final_vs_A1')])
def test_actual_return_route_losses_enter_endpoints_despite_optimistic_readonly_probe(cell, retention):
    rows = cohort(); stage, task = cell.split('_')
    for row in rows:
        row['stages'][stage]['context_route'] = dict(created=True, wrong_return=True)
        row['stages'][stage]['readonly_original_task_probe_utility'] = 1e9
        for game in games(row, cell):
            game['utility']-=5.
    result = summarize(rows, draws=20)
    assert result['cells'][cell]['paired_contrasts']['CONTEXT_LOCAL_minus_SOURCE']['mean']==(-4. if task=='A' else -3.)
    assert result['current_task_sequence_contrasts']['CONTEXT_LOCAL_minus_CONTEXT_MC']['mean']==pytest.approx(-.1)
    assert result['retention_status'][retention]=='SUPPORTED_LOSS'
    assert not result['retained_gain_supported']
    assert result['primary_local_over_mc_supported']==(cell!='A3_A')


def test_route_error_metadata_does_not_replace_observed_utility_evidence():
    rows = cohort(); before = summarize(rows, draws=2)
    for row in rows:
        for stage in row['stages'].values():
            stage['context_route'] = dict(created=True, classification_error=True)
    assert summarize(rows, draws=2)==before


def test_negative_mean_with_retention_interval_crossing_zero_remains_unresolved():
    rows = cohort()
    for life, row in enumerate(rows):
        for game in games(row, 'B2_A'):
            game['utility']+=1. if (life // 4) % 2 else -1.25
    result = summarize(rows, draws=40)
    contrast = result['checkpoint_contrasts']['A_after_B2']['CONTEXT_LOCAL']
    lower, upper = contrast['ci95']
    assert contrast['mean']<0. and lower<0.<upper
    assert result['retention_status']['A_after_B2']=='UNRESOLVED'
    assert not result['retention_supported'] and not result['retained_gain_supported']


def test_parent_group_bootstrap_uses_v309_seed_and_signed_new_lifecycle_results():
    rows = cohort(); values = [(life % 9)-4. for life in range(64)]
    for row, value in zip(rows, values):
        for cell in FINAL_CELLS:
            for local, mc in zip(games(row, cell), games(row, cell, 'CONTEXT_MC')):
                local['utility']=mc['utility']+value
    result = summarize(rows, draws=40)
    contrast = result['final_ab_contrasts']['CONTEXT_LOCAL_minus_CONTEXT_MC']
    groups = [values[parent::4] for parent in range(4)]
    rng = random.Random(30900001)
    samples = sorted(mean(mean(rng.choices(group, k=16)) for group in groups) for _ in range(40))
    assert contrast['ci95']==pytest.approx([samples[0]+(samples[1]-samples[0])*.975,
                                          samples[38]+(samples[39]-samples[38])*.025])
    assert contrast['parent_mean_deltas']=={str(parent):mean(group) for parent, group in enumerate(groups)}
    assert contrast['adverse_lifecycles']==[life for life, value in enumerate(values) if value<0.]
    assert contrast['lifecycle_deltas']=={str(life):value for life, value in enumerate(values)}
    assert contrast['improved_equal_worse']==[sum(value>0 for value in values),
                                            sum(value==0 for value in values), sum(value<0 for value in values)]
    assert result['bootstrap_seed']==BOOTSTRAP_SEED==30900001
    assert result['bootstrap_draws']==40


@pytest.mark.parametrize('cell', [cell for cell, _, _ in CELLS])
@pytest.mark.parametrize('arm', ARMS)
def test_every_arm_and_checkpoint_requires_fresh_v309_paired_task_seeds(cell, arm):
    rows = cohort(); games(rows[0], cell, arm)[0]['seed']=308900000000
    with pytest.raises(ValueError, match='fresh paired task seeds reused'):
        summarize(rows, draws=2)


@pytest.mark.parametrize('cell', ['B1_A', 'A2_A', 'B2_A', 'A3_A', 'A2_B', 'B2_B', 'A3_B'])
def test_source_episode_inventory_repeats_exactly_not_just_its_mean(cell):
    rows = cohort(); source = games(rows[0], cell, 'SOURCE')
    source[0]['utility']+=1.; source[1]['utility']-=1.
    with pytest.raises(ValueError, match='SOURCE must repeat exactly'):
        summarize(rows, draws=2)


@pytest.mark.parametrize('cell', [cell for cell, _, _ in CELLS])
@pytest.mark.parametrize('arm', ARMS)
def test_cutoff_in_any_required_endpoint_is_retained_and_blocks_all_support(cell, arm):
    rows = cohort(); task = cell.split('_')[1]
    changed = [name for name, _, evaluated in CELLS if evaluated==task] if arm=='SOURCE' else [cell]
    for name in changed:
        games(rows[0], name, arm)[0].update(status='CUTOFF', utility=-30.)
    result = summarize(rows, draws=2)
    assert not result['complete_game_endpoints'] and not result['primary_local_over_mc_supported']
    assert not result['final_net_gain_supported'] and not result['retained_gain_supported']
    assert result['final_task_gain_supported']==dict(A=False, B=False)
    assert not result['final_dual_task_gain_supported'] and not result['retention_supported']
    assert result['retention_status']=={name:'INCOMPLETE_GAME_ENDPOINTS' for name in CHECKPOINTS}
    assert result['by_lifecycle'][0]['cells'][cell]['arms'][arm]['cutoff_episodes']==[0]
    assert result['arms'][arm]['games']==18432
    assert result['arms'][arm]['cutoffs']==len(changed)


@pytest.mark.parametrize('stage', ['A2', 'B2', 'A3'])
def test_missing_return_stage_cannot_be_analyzed_as_a_shorter_sequence(stage):
    rows = cohort(); del rows[0]['stages'][stage]
    with pytest.raises(ValueError, match='all nine evaluation cells'):
        summarize(rows, draws=2)


@pytest.mark.parametrize('cell', ['A2_A', 'A2_B', 'B2_A', 'B2_B', 'A3_A', 'A3_B'])
def test_missing_return_task_endpoint_is_rejected(cell):
    rows = cohort(); stage, task = cell.split('_')
    del rows[0]['stages'][stage]['arms']['CONTEXT_LOCAL']['evaluations'][task]
    with pytest.raises(ValueError, match='all nine evaluation cells'):
        summarize(rows, draws=2)


@pytest.mark.parametrize('error', ['missing_life', 'duplicate_life', 'wrong_parent', 'missing_game', 'nonterminal_status'])
def test_incomplete_or_unpaired_new_inventory_is_rejected(error):
    rows = cohort()
    if error=='missing_life': rows.pop()
    elif error=='duplicate_life': rows[-1]['lifecycle']=0
    elif error=='wrong_parent': rows[0]['parent']=1
    elif error=='missing_game': games(rows[0], 'A3_B').pop()
    else: games(rows[0], 'A3_B')[0]['status']='RUNNING'
    with pytest.raises(ValueError):
        summarize(rows, draws=2)


def test_old_cases_training_metrics_and_order_cannot_change_new_endpoints():
    rows = cohort(); before = deepcopy(rows); result = summarize(rows, draws=2)
    assert rows==before and result==summarize(list(reversed(rows)), draws=2)
    for row in rows:
        row['old_v308_primary']=1e9
        row['old_v308_target_case']=dict(utility=1e9)
        for stage in row['stages'].values():
            stage['training_utility']=1e9
    assert result==summarize(rows, draws=2)
