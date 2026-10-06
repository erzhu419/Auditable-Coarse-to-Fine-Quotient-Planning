"""Retained-context repair cannot substitute averages for dual gains or retention."""
from copy import deepcopy
import random
from statistics import mean

import pytest

from acfqp.science.context_analysis_v305 import (
    ARMS, BOOTSTRAP_SEED, CELLS, STAGE_TASKS, summarize,
)


def cohort(context=None, shared=None):
    context = context or dict(A1_A=1., B_A=1., B_B=2., A2_A=1., A2_B=2.)
    shared = shared or dict(A1_A=1., B_A=-1., B_B=-2., A2_A=0., A2_B=-1.)
    rows = []
    for life in range(64):
        stages = {stage:dict(arms={arm:dict(evaluations={}) for arm in ARMS}) for stage in STAGE_TASKS}
        for cell, stage, task in CELLS:
            for arm in ARMS:
                gain = context[cell] if arm=='CONTEXT_LOCAL' else shared[cell] if arm=='SHARED_LOCAL' else 0.
                stages[stage]['arms'][arm]['evaluations'][task] = dict(game_summaries=[
                    dict(seed=303900000000+(0 if task=='A' else 100000)+life*1000000+episode,
                         utility=life+(100. if task=='B' else 0.)+gain, status='LOST', steps=episode+1)
                    for episode in range(32)])
        rows.append(dict(lifecycle=life, parent=life % 4, stages=stages))
    return rows


def games(row, cell, arm='CONTEXT_LOCAL'):
    stage, task = cell.split('_')
    return row['stages'][stage]['arms'][arm]['evaluations'][task]['game_summaries']


def test_final_equal_ab_structural_repair_and_source_gain_are_distinct():
    result = summarize(cohort(), draws=20)
    assert result['primary_contrast']=='CONTEXT_LOCAL_minus_SHARED_LOCAL_FINAL_AB'
    assert result['primary_repair_supported']
    assert result['final_ab_contrasts']['CONTEXT_LOCAL_minus_SHARED_LOCAL']['ci95']==[2., 2.]
    assert result['final_ab_contrasts']['CONTEXT_LOCAL_minus_SOURCE']['ci95']==[1.5, 1.5]
    assert result['current_task_sequence_contrasts']['CONTEXT_LOCAL_minus_SHARED_LOCAL']['mean']==pytest.approx(5./3.)
    assert result['arms']['CONTEXT_LOCAL']['games']==64*32*5
    assert result['arms']['CONTEXT_LOCAL']['mean_final_ab_game_utility']==83.
    assert result['final_dual_task_gain_supported'] and result['retained_gain_supported']
    assert not result['a_restoration_supported']
    assert 'RETAINED_V303_HISTORIES' in result['primary_repair_status']
    assert 'not independent confirmation' in result['evidence_scope']


def test_positive_current_task_adaptation_cannot_replace_failed_final_repair():
    result = summarize(cohort(dict(A1_A=10., B_A=0., B_B=10., A2_A=-2., A2_B=-2.)), draws=20)
    assert result['current_task_sequence_contrasts']['CONTEXT_LOCAL_minus_SHARED_LOCAL']['ci95'][0]>0.
    assert result['final_ab_contrasts']['CONTEXT_LOCAL_minus_SHARED_LOCAL']['ci95']==[-1.5, -1.5]
    assert not result['primary_repair_supported']


def test_repair_vs_shared_cannot_assert_gain_vs_source_or_dual_task_benefit():
    result = summarize(cohort(dict(A1_A=1., B_A=1., B_B=3., A2_A=-1., A2_B=3.),
        dict(A1_A=1., B_A=-2., B_B=0., A2_A=-2., A2_B=0.)), draws=20)
    assert result['primary_repair_supported']
    assert result['final_ab_contrasts']['CONTEXT_LOCAL_minus_SOURCE']['mean']==1.
    assert result['final_task_gain_supported']==dict(A=False, B=True)
    assert not result['final_dual_task_gain_supported']
    assert result['retention_status']['A_final_vs_A1']=='SUPPORTED_LOSS'
    assert not result['retained_gain_supported']


def test_negative_final_ab_vs_source_can_still_be_repair_only():
    result = summarize(cohort(dict(A1_A=-1., B_A=-1., B_B=-1., A2_A=-1., A2_B=-1.),
        {cell:-2. for cell, _, _ in CELLS}), draws=20)
    assert result['primary_repair_supported']
    assert result['final_ab_contrasts']['CONTEXT_LOCAL_minus_SOURCE']['mean']==-1.
    assert not result['final_dual_task_gain_supported']
    assert result['retained_gain_supported']


def test_exact_zero_retention_supports_nondecrease_and_b_loss_is_separate():
    result = summarize(cohort(dict(A1_A=1., B_A=1., B_B=3., A2_A=1., A2_B=2.)), draws=20)
    assert result['primary_repair_supported'] and result['final_dual_task_gain_supported']
    assert result['checkpoint_contrasts']['A_after_B']['CONTEXT_LOCAL']['ci95']==[0., 0.]
    assert result['retention_status']==dict(A_after_B='SUPPORTED_NONDECREASE',
        B_after_A2='SUPPORTED_LOSS', A_final_vs_A1='SUPPORTED_NONDECREASE')
    assert not result['retained_gain_supported']
    for contrasts in result['checkpoint_contrasts'].values():
        assert contrasts['SOURCE']['ci95']==[0., 0.]


def test_crossing_zero_retention_interval_is_unresolved():
    rows = cohort()
    for life, row in enumerate(rows):
        for game in games(row, 'B_A'):
            game['utility'] += 2. if (life // 4) % 2 else -2.
    result = summarize(rows, draws=40)
    lower, upper = result['checkpoint_contrasts']['A_after_B']['CONTEXT_LOCAL']['ci95']
    assert lower<0.<upper
    assert result['retention_status']['A_after_B']=='UNRESOLVED'


def test_fixed_parent_bootstrap_uses_v305_seed_and_retains_signed_lifecycle_results():
    rows = cohort()
    values = [(life % 9)-4. for life in range(64)]
    for row, value in zip(rows, values):
        for cell in ('A2_A', 'A2_B'):
            for context, shared in zip(games(row, cell), games(row, cell, 'SHARED_LOCAL')):
                context['utility'] = shared['utility']+value
    result = summarize(rows, draws=40)
    contrast = result['final_ab_contrasts']['CONTEXT_LOCAL_minus_SHARED_LOCAL']
    groups = [values[parent::4] for parent in range(4)]
    rng = random.Random(BOOTSTRAP_SEED)
    samples = sorted(mean(mean(rng.choices(group, k=16)) for group in groups) for _ in range(40))
    assert contrast['ci95']==pytest.approx([samples[0]+(samples[1]-samples[0])*.975,
                                          samples[38]+(samples[39]-samples[38])*.025])
    assert contrast['parent_mean_deltas']=={str(parent):mean(group) for parent, group in enumerate(groups)}
    assert contrast['adverse_lifecycles']==[life for life, value in enumerate(values) if value<0.]
    assert contrast['lifecycle_deltas']=={str(life):value for life, value in enumerate(values)}
    assert result['bootstrap_seed']==30500001


@pytest.mark.parametrize('cell', [cell for cell, _, _ in CELLS])
def test_evaluation_requires_exact_retained_v303_task_seeds(cell):
    rows = cohort()
    games(rows[0], cell)[0]['seed'] = 305900000000
    with pytest.raises(ValueError, match='task seeds reused'):
        summarize(rows, draws=2)


def test_source_must_repeat_exactly_for_each_task():
    rows = cohort()
    games(rows[0], 'B_A', 'SOURCE')[0]['utility'] += 1.
    with pytest.raises(ValueError, match='SOURCE must repeat exactly'):
        summarize(rows, draws=2)


@pytest.mark.parametrize('arm', ARMS)
def test_cutoff_in_retention_only_cell_blocks_all_supported_gain_claims(arm):
    rows = cohort()
    games(rows[0], 'B_A', arm)[0].update(status='CUTOFF', utility=-30.)
    if arm=='SOURCE':
        for cell in ('A1_A', 'A2_A'):
            games(rows[0], cell, arm)[0].update(status='CUTOFF', utility=-30.)
    result = summarize(rows, draws=2)
    assert not result['complete_game_endpoints'] and not result['primary_repair_supported']
    assert not result['final_dual_task_gain_supported'] and not result['retained_gain_supported']
    assert result['by_lifecycle'][0]['cells']['B_A']['arms'][arm]['cutoff_episodes']==[0]
    assert result['retention_status']['A_after_B']=='INCOMPLETE_GAME_ENDPOINTS'
    assert result['arms'][arm]['games']==10240


@pytest.mark.parametrize('error', ['missing_life', 'wrong_parent', 'missing_game'])
def test_missing_retained_inventory_is_rejected(error):
    rows = cohort()
    if error=='missing_life':
        rows.pop()
    elif error=='wrong_parent':
        rows[0]['parent'] = 1
    else:
        games(rows[0], 'A2_B').pop()
    with pytest.raises(ValueError):
        summarize(rows, draws=2)


def test_history_diagnosis_metrics_and_row_order_cannot_change_primary():
    rows = cohort()
    before = deepcopy(rows)
    result = summarize(rows, draws=2)
    assert rows==before and result==summarize(list(reversed(rows)), draws=2)
    for row in rows:
        row['old_v304_primary'] = -1e9
        for stage in row['stages'].values():
            for arm in stage['arms'].values():
                arm['training_utility'] = 1e9
    assert result==summarize(rows, draws=2)


def test_heldout_diagnostics_weight_games_then_lifecycles_and_require_same_inventory():
    rows = cohort()
    for row in rows:
        for arm in ARMS:
            metrics = [dict(episode=0, start=0, end=1, count=1, bias=-1., mse=1., mae=1.)]
            if row['lifecycle']==0:
                metrics.append(dict(episode=1, start=1, end=1001, count=1000, bias=0., mse=9., mae=3.))
            row['stages']['A1']['arms'][arm]['heldout'] = dict(game_metrics=metrics)
    result = summarize(rows, draws=2)
    heldout = result['heldout_by_stage']['A1']['CONTEXT_LOCAL']
    assert heldout['games']==65 and heldout['samples']==1064
    assert heldout['mse']==1.0625 and heldout['mae']==1.015625
    assert result['primary_repair_supported']
    rows[0]['stages']['A1']['arms']['SHARED_LOCAL']['heldout']['game_metrics'][0]['count'] += 1
    with pytest.raises(ValueError, match='same complete heldout inventory'):
        summarize(rows, draws=2)
