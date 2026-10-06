"""Policy-data gain, A1 retention, and original SOURCE gain are distinct."""
from copy import deepcopy
import random
from statistics import mean

import pytest

from acfqp.science.policy_data_analysis_v306 import ARMS, DATASETS, summarize


def cohort(source_data=1., current_data=2., frozen=1.5):
    gains = dict(SOURCE=0., A1_FROZEN=frozen, SOURCE_DATA=source_data, CURRENT_DATA=current_data)
    return [dict(lifecycle=life, parent=life % 4,
        arms={arm:dict(evaluation=dict(game_summaries=[
            dict(seed=306900000000+life*1000000+episode,
                 utility=life+gain, status='LOST', steps=episode+1)
            for episode in range(32)])) for arm, gain in gains.items()}) for life in range(64)]


def games(row, arm='CURRENT_DATA'):
    return row['arms'][arm]['evaluation']['game_summaries']


def test_primary_actor_data_gain_and_retention_are_separate_with_new_a_seeds():
    result = summarize(cohort(), draws=20)
    assert result['primary_contrast']=='CURRENT_DATA_minus_SOURCE_DATA'
    assert result['primary_policy_data_gain_supported']
    assert result['paired_contrasts']['CURRENT_DATA_minus_SOURCE_DATA']['ci95']==[1., 1.]
    assert result['paired_contrasts']['CURRENT_DATA_minus_A1_FROZEN']['ci95']==[.5, .5]
    assert result['current_policy_retention_status']=='SUPPORTED_NONDECREASE'
    assert result['current_policy_no_degradation_supported']
    assert result['source_reference_gain_supported']==dict(A1_FROZEN=True, SOURCE_DATA=True, CURRENT_DATA=True)
    assert result['arms']['CURRENT_DATA']['games']==64*32
    assert result['arms']['CURRENT_DATA']['mean_game_utility']==33.5
    assert result['heldout_by_dataset']=={}
    assert 'RETAINED_V303_A1_HISTORIES' in result['primary_policy_data_gain_status']
    assert 'B retention and dual-task continual learning are not evaluated' in result['evidence_scope']


def test_current_policy_advantage_can_coexist_with_loss_of_a1_capability():
    result = summarize(cohort(source_data=1., current_data=2., frozen=3.), draws=20)
    assert result['primary_policy_data_gain_supported']
    assert result['source_reference_gain_supported']['CURRENT_DATA']
    assert result['current_policy_retention_status']=='SUPPORTED_LOSS'
    assert not result['current_policy_no_degradation_supported']


def test_retention_can_hold_without_actor_data_advantage():
    result = summarize(cohort(source_data=3., current_data=2., frozen=1.), draws=20)
    assert not result['primary_policy_data_gain_supported']
    assert result['current_policy_no_degradation_supported']
    assert result['paired_contrasts']['CURRENT_DATA_minus_SOURCE_DATA']['ci95']==[-1., -1.]


def test_exact_zero_retention_is_supported_but_exact_zero_primary_is_not():
    result = summarize(cohort(source_data=2., current_data=2., frozen=2.), draws=20)
    assert not result['primary_policy_data_gain_supported']
    assert result['paired_contrasts']['CURRENT_DATA_minus_A1_FROZEN']['ci95']==[0., 0.]
    assert result['current_policy_retention_status']=='SUPPORTED_NONDECREASE'
    assert result['current_policy_no_degradation_supported']


def test_crossing_zero_retention_is_unresolved_even_when_actor_data_gain_is_supported():
    rows = cohort(source_data=-5., current_data=1.5, frozen=1.5)
    for life, row in enumerate(rows):
        for game in games(row):
            game['utility'] += 2. if (life // 4) % 2 else -2.
    result = summarize(rows, draws=40)
    lower, upper = result['paired_contrasts']['CURRENT_DATA_minus_A1_FROZEN']['ci95']
    assert lower<0.<upper
    assert result['primary_policy_data_gain_supported']
    assert result['current_policy_retention_status']=='UNRESOLVED'
    assert not result['current_policy_no_degradation_supported']


def test_conditional_parent_bootstrap_uses_frozen_v306_seed_and_signed_life_results():
    rows = cohort()
    values = [(life % 9)-4. for life in range(64)]
    for row, value in zip(rows, values):
        for current, source_data in zip(games(row), games(row, 'SOURCE_DATA')):
            current['utility'] = source_data['utility']+value
    result = summarize(rows, draws=40)
    contrast = result['paired_contrasts']['CURRENT_DATA_minus_SOURCE_DATA']
    groups = [values[parent::4] for parent in range(4)]
    rng = random.Random(30600001)
    samples = sorted(mean(mean(rng.choices(group, k=16)) for group in groups) for _ in range(40))
    assert contrast['ci95']==pytest.approx([samples[0]+(samples[1]-samples[0])*.975,
                                          samples[38]+(samples[39]-samples[38])*.025])
    assert contrast['parent_mean_deltas']=={str(parent):mean(group) for parent, group in enumerate(groups)}
    assert contrast['adverse_lifecycles']==[life for life, value in enumerate(values) if value<0.]
    assert contrast['lifecycle_deltas']=={str(life):value for life, value in enumerate(values)}
    assert result['bootstrap_seed']==30600001


@pytest.mark.parametrize('arm', ARMS)
def test_any_arm_cutoff_is_retained_and_blocks_supported_claims(arm):
    rows = cohort()
    games(rows[0], arm)[0].update(status='CUTOFF', utility=-30.)
    result = summarize(rows, draws=2)
    assert not result['complete_game_endpoints']
    assert not result['primary_policy_data_gain_supported']
    assert not result['current_policy_no_degradation_supported']
    assert result['current_policy_retention_status']=='INCOMPLETE_GAME_ENDPOINTS'
    assert result['by_lifecycle'][0]['arms'][arm]['cutoff_episodes']==[0]
    assert not any(result['source_reference_gain_supported'].values())
    assert result['arms'][arm]['games']==2048


@pytest.mark.parametrize('arm', ARMS)
def test_old_v303_evaluation_seeds_cannot_enter_new_a_evaluation(arm):
    rows = cohort()
    games(rows[0], arm)[0]['seed'] = 303900000000
    with pytest.raises(ValueError, match='new paired A evaluation seeds'):
        summarize(rows, draws=2)


@pytest.mark.parametrize('error', ['missing_life', 'wrong_parent', 'missing_game', 'unknown_status'])
def test_missing_matched_inventory_or_unknown_terminal_status_is_rejected(error):
    rows = cohort()
    if error=='missing_life':
        rows.pop()
    elif error=='wrong_parent':
        rows[0]['parent'] = 1
    elif error=='missing_game':
        games(rows[0]).pop()
    else:
        games(rows[0])[0]['status'] = 'COMPLETE'
    with pytest.raises(ValueError):
        summarize(rows, draws=2)


def test_old_aggregate_results_training_metrics_and_row_order_cannot_change_primary():
    rows = cohort()
    before = deepcopy(rows)
    result = summarize(rows, draws=2)
    assert rows==before and result==summarize(list(reversed(rows)), draws=2)
    for row in rows:
        row['old_v305_primary'] = -1e9
        row['datasets'] = {dataset:dict(training_utility=1e9) for dataset in DATASETS}
    assert result==summarize(rows, draws=2)


def test_heldout_diagnostics_allow_different_actor_inventories_but_match_arms_within_dataset():
    rows = cohort()
    for row in rows:
        for arm in ARMS:
            row['arms'][arm]['heldout_by_dataset'] = {}
            for dataset in DATASETS:
                metrics = [dict(episode=0, start=0, end=1, count=1, bias=-1., mse=1., mae=1.)]
                if row['lifecycle']==0 and dataset=='SOURCE_DATA':
                    metrics.append(dict(episode=1, start=1, end=1001, count=1000, bias=0., mse=9., mae=3.))
                row['arms'][arm]['heldout_by_dataset'][dataset] = dict(game_metrics=metrics)
    result = summarize(rows, draws=2)
    heldout = result['heldout_by_dataset']['SOURCE_DATA']['CURRENT_DATA']
    assert heldout['games']==65 and heldout['samples']==1064
    assert heldout['mse']==1.0625 and heldout['mae']==1.015625
    assert result['heldout_by_dataset']['CURRENT_DATA']['CURRENT_DATA']['games']==64
    assert result['primary_policy_data_gain_supported']
    rows[0]['arms']['SOURCE_DATA']['heldout_by_dataset']['SOURCE_DATA']['game_metrics'][0]['count'] += 1
    with pytest.raises(ValueError, match='same complete heldout inventory within a dataset'):
        summarize(rows, draws=2)


def test_partial_cross_actor_heldout_diagnostics_are_not_silently_aggregated():
    rows = cohort()
    rows[0]['arms']['CURRENT_DATA']['heldout_by_dataset'] = dict(SOURCE_DATA=dict(game_metrics=[]))
    with pytest.raises(ValueError, match='all arms and lifecycles of a dataset'):
        summarize(rows, draws=2)
