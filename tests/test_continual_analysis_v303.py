"""Final two-task gain, exact repeated controls, and signed forgetting endpoints."""
from copy import deepcopy
import random
from statistics import mean

import pytest

from acfqp.science.continual_analysis_v303 import ARMS, CELLS, STAGE_TASKS, summarize


def cohort(local_gains=None):
    local_gains = local_gains or dict(A1_A=1., B_A=1., B_B=2., A2_A=1., A2_B=2.)
    rows = []
    for life in range(64):
        stages = {stage:dict(arms={arm:dict(evaluations={}) for arm in ARMS}) for stage in STAGE_TASKS}
        for cell, stage, task in CELLS:
            for arm in ARMS:
                gain = local_gains[cell] if arm=='LOCAL_RISK' else -1. if arm=='MC' else 0.
                stages[stage]['arms'][arm]['evaluations'][task] = dict(game_summaries=[
                    dict(seed=303900000000+(0 if task=='A' else 100000)+life*1000000+episode,
                         utility=life+(100. if task=='B' else 0.)+gain, status='LOST', steps=episode+1)
                    for episode in range(32)])
        rows.append(dict(lifecycle=life, parent=life % 4, stages=stages))
    return rows


def games(row, cell, arm='LOCAL_RISK'):
    stage, task = cell.split('_')
    return row['stages'][stage]['arms'][arm]['evaluations'][task]['game_summaries']


def test_primary_is_final_equal_ab_not_current_task_sequence_or_calibration():
    result = summarize(cohort(), draws=20)
    assert result['primary_contrast']=='LOCAL_RISK_minus_SOURCE_FINAL_AB'
    assert result['primary_sequence_gain_supported']
    assert result['final_ab_contrasts']['LOCAL_RISK_minus_SOURCE']['ci95']==[1.5, 1.5]
    assert result['current_task_sequence_contrasts']['LOCAL_RISK_minus_SOURCE']['mean']==pytest.approx(4./3.)
    assert result['arms']['LOCAL_RISK']['games']==64*32*5
    assert result['arms']['LOCAL_RISK']['mean_final_ab_game_utility']==83.
    assert result['final_dual_task_gain_supported']
    assert result['retained_gain_supported']
    assert not result['a_restoration_supported']
    assert result['primary_sequence_gain_status']=='SUPPORTED_CONDITIONAL_ON_FOUR_FROZEN_PARENTS'
    assert 'four reused frozen source parents' in result['evidence_scope']
    assert 'equal data does not imply equal computation' in result['contribution_scope']


def test_positive_current_task_sequence_cannot_replace_failed_final_ab_endpoint():
    result = summarize(cohort(dict(A1_A=10., B_A=0., B_B=10., A2_A=-1., A2_B=-1.)), draws=20)
    assert result['current_task_sequence_contrasts']['LOCAL_RISK_minus_SOURCE']['ci95'][0]>0.
    assert result['final_ab_contrasts']['LOCAL_RISK_minus_SOURCE']['ci95']==[-1., -1.]
    assert result['final_ab_contrasts']['LOCAL_RISK_minus_MC']['mean']==0.
    assert not result['primary_sequence_gain_supported']


def test_final_average_gain_does_not_assert_each_task_gain_or_retention():
    result = summarize(cohort(dict(A1_A=1., B_A=-1., B_B=4., A2_A=-1., A2_B=3.)), draws=20)
    assert result['primary_sequence_gain_supported']
    assert result['final_task_gain_supported']==dict(A=False, B=True)
    assert not result['final_dual_task_gain_supported']
    assert result['retention_status']==dict(A_after_B='SUPPORTED_LOSS',
        B_after_A2='SUPPORTED_LOSS', A_final_vs_A1='SUPPORTED_LOSS')
    assert not result['retained_gain_supported']


def test_recovery_and_b_forgetting_are_reported_separately_from_final_gain():
    result = summarize(cohort(dict(A1_A=1., B_A=-1., B_B=2., A2_A=1., A2_B=1.)), draws=20)
    assert result['primary_sequence_gain_supported'] and result['a_restoration_supported']
    assert result['checkpoint_contrasts']['A_after_B']['LOCAL_RISK']['mean']==-2.
    assert result['checkpoint_contrasts']['A_restore_after_A2']['LOCAL_RISK']['mean']==2.
    assert result['checkpoint_contrasts']['B_after_A2']['LOCAL_RISK']['mean']==-1.
    assert result['retention_status']['A_final_vs_A1']=='SUPPORTED_NONDECREASE'
    assert not result['retained_gain_supported']
    for contrasts in result['checkpoint_contrasts'].values():
        assert contrasts['SOURCE']['ci95']==[0., 0.]


def test_crossing_zero_retention_interval_is_unresolved():
    rows = cohort()
    for life, row in enumerate(rows):
        for game in games(row, 'B_A'):
            game['utility'] += 2. if (life // 4) % 2 else -2.
    result = summarize(rows, draws=40)
    lower, upper = result['checkpoint_contrasts']['A_after_B']['LOCAL_RISK']['ci95']
    assert lower<0.<upper
    assert result['retention_status']['A_after_B']=='UNRESOLVED'
    assert not result['retained_gain_supported']


def test_fixed_parent_bootstrap_retains_signed_lifecycle_results():
    rows = cohort()
    values = [(life % 9)-4. for life in range(64)]
    for row, value in zip(rows, values):
        for cell in ('A2_A', 'A2_B'):
            for local, source in zip(games(row, cell), games(row, cell, 'SOURCE')):
                local['utility'] = source['utility']+value
    result = summarize(rows, draws=40)
    contrast = result['final_ab_contrasts']['LOCAL_RISK_minus_SOURCE']
    groups = [values[parent::4] for parent in range(4)]
    rng = random.Random(30300001)
    samples = sorted(mean(mean(rng.choices(group, k=16)) for group in groups) for _ in range(40))
    assert contrast['ci95']==pytest.approx([samples[0]+(samples[1]-samples[0])*.975,
                                          samples[38]+(samples[39]-samples[38])*.025])
    assert contrast['parent_mean_deltas']=={str(parent):mean(group) for parent, group in enumerate(groups)}
    assert contrast['adverse_lifecycles']==[life for life, value in enumerate(values) if value<0.]
    assert contrast['lifecycle_deltas']=={str(life):value for life, value in enumerate(values)}
    assert result['bootstrap_seed']==30300001


@pytest.mark.parametrize('cell', [cell for cell, _, _ in CELLS])
def test_checkpoint_or_old_confirmation_seed_cannot_enter_task_pair(cell):
    rows = cohort()
    games(rows[0], cell)[0]['seed'] = 302900000000
    with pytest.raises(ValueError, match='task seeds reused'):
        summarize(rows, draws=2)


def test_source_must_repeat_exactly_for_each_task():
    rows = cohort()
    games(rows[0], 'B_A', 'SOURCE')[0]['utility'] += 1.
    with pytest.raises(ValueError, match='SOURCE must repeat exactly'):
        summarize(rows, draws=2)


@pytest.mark.parametrize('arm', ARMS)
def test_cutoff_in_retention_only_cell_is_retained_and_blocks_confirmation(arm):
    rows = cohort()
    games(rows[0], 'B_A', arm)[0].update(status='CUTOFF', utility=-30.)
    if arm=='SOURCE':
        for cell in ('A1_A', 'A2_A'):
            games(rows[0], cell, arm)[0].update(status='CUTOFF', utility=-30.)
    result = summarize(rows, draws=2)
    assert not result['complete_game_endpoints'] and not result['primary_sequence_gain_supported']
    assert result['by_lifecycle'][0]['cells']['B_A']['arms'][arm]['cutoff_episodes']==[0]
    assert result['retention_status']['A_after_B']=='INCOMPLETE_GAME_ENDPOINTS'
    assert result['arms'][arm]['games']==10240


@pytest.mark.parametrize('error', ['missing_life', 'wrong_parent', 'missing_game'])
def test_missing_frozen_inventory_is_rejected(error):
    rows = cohort()
    if error=='missing_life':
        rows.pop()
    elif error=='wrong_parent':
        rows[0]['parent'] = 1
    else:
        games(rows[0], 'A2_B').pop()
    with pytest.raises(ValueError):
        summarize(rows, draws=2)


def test_old_outcomes_training_metrics_and_order_cannot_change_primary():
    rows = cohort()
    before = deepcopy(rows)
    result = summarize(rows, draws=2)
    assert rows==before and result==summarize(list(reversed(rows)), draws=2)
    for row in rows:
        row['old_v302_primary'] = -1e9
        for stage in row['stages'].values():
            for arm in stage['arms'].values():
                arm['training_utility'] = 1e9
    assert result==summarize(rows, draws=2)


def test_optional_heldout_diagnostics_weight_games_then_lifecycles_not_samples():
    rows = cohort()
    for row in rows:
        for arm in ARMS:
            metrics = [dict(episode=0, start=0, end=1, count=1, bias=-1., mse=1., mae=1.)]
            if row['lifecycle']==0:
                metrics.append(dict(episode=1, start=1, end=1001, count=1000, bias=0., mse=9., mae=3.))
            row['stages']['A1']['arms'][arm]['heldout'] = dict(game_metrics=metrics)
    result = summarize(rows, draws=2)
    heldout = result['heldout_by_stage']['A1']['SOURCE']
    assert heldout['games']==65 and heldout['samples']==1064
    assert heldout['mse']==1.0625 and heldout['mae']==1.015625
    assert result['primary_sequence_gain_supported']
    rows[0]['stages']['A1']['arms']['MC']['heldout']['game_metrics'][0]['count'] += 1
    with pytest.raises(ValueError, match='same complete heldout inventory'):
        summarize(rows, draws=2)
