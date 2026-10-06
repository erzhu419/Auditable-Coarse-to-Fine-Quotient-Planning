from copy import deepcopy

import pytest

from acfqp.science.episode_consolidation_analysis_v290 import ARMS, PAIRS, summarize


def cohort():
    rows = []
    for life in range(16):
        arms = {}
        for arm, shift, error in zip(ARMS, (0., -3., 2., -1.), (1., 4., .5, .25)):
            metrics = [dict(episode=0, start=0, end=1, count=1,
                            bias=-1., mse=error, mae=error)]
            if life == 0:
                metrics.append(dict(episode=1, start=1, end=1001, count=1000,
                                    bias=0., mse=9.*error, mae=3.*error))
            arms[arm] = dict(game_summaries=[dict(seed=290500000000+life*1000000+i,
                utility=life+shift, status='LOST', steps=10+i) for i in range(16)],
                heldout=dict(game_metrics=metrics, metrics=dict(mse=99999.),
                             prediction_counts={}, target_counts={}),
                training_returns=[999999.], new_value_updates=10000000 if life == 0 else 1,
                anchor_metrics=dict(mse=-999999.))
        rows.append(dict(lifecycle=life, parent=life%4, arms=arms))
    return rows


def test_full_holdout_weights_games_then_lives_not_samples_updates_or_anchors():
    result = summarize(cohort(), draws=40)
    frozen = result['arms']['FROZEN']['heldout']
    assert result['by_lifecycle'][0]['arms']['FROZEN']['heldout']['mse'] == 5.
    assert frozen['mse'] == 1.25 and frozen['mae'] == 1.0625
    assert frozen['bias'] == -.96875
    assert frozen['games'] == 17 and frozen['samples'] == 1016
    assert result['heldout_contrasts']['EPISODE_MEAN_MC_minus_FROZEN']['mse']['mean'] == -.9375


def test_prediction_improvement_cannot_replace_primary_new_game_learning():
    result = summarize(cohort(), draws=40)
    name = 'EPISODE_MEAN_MC_minus_FROZEN'
    primary = result['paired_contrasts'][name]
    assert result['primary_contrast'] == result['primary_prediction_contrast'] == name
    assert result['primary_prediction_metric'] == 'mse'
    assert primary['mean'] == -1. and primary['ci95'] == [-1., -1.]
    assert primary['improved_equal_worse'] == [0, 0, 16]
    assert primary['adverse_lifecycles'] == list(range(16))
    assert result['heldout_contrasts'][name]['mse']['improved_equal_worse'] == [16, 0, 0]
    assert 'improved_equal_worse' not in result['heldout_contrasts'][name]['bias']


def test_all_five_signed_contrasts_keep_normalization_and_aggregation_separate():
    result = summarize(cohort(), draws=40)
    pairs = result['paired_contrasts']
    assert set(pairs) == {left+'_minus_'+right for left, right in PAIRS}
    assert pairs['NORMALIZED_SEQUENTIAL_MC_minus_FROZEN']['mean'] == 2.
    assert pairs['EPISODIC_MC_minus_FROZEN']['mean'] == -3.
    assert pairs['EPISODE_MEAN_MC_minus_NORMALIZED_SEQUENTIAL_MC']['mean'] == -3.
    assert pairs['EPISODE_MEAN_MC_minus_EPISODIC_MC']['mean'] == 2.
    assert pairs['EPISODE_MEAN_MC_minus_NORMALIZED_SEQUENTIAL_MC']['adverse_lifecycles'] == list(range(16))


def test_bootstrap_resamples_whole_lives_within_fixed_parents():
    rows = cohort()
    for row in rows:
        for game, frozen in zip(row['arms']['EPISODE_MEAN_MC']['game_summaries'],
                                row['arms']['FROZEN']['game_summaries']):
            game['utility'] = frozen['utility']-(row['parent']+1.)
    result = summarize(rows, draws=80)
    primary = result['paired_contrasts'][result['primary_contrast']]
    assert primary['mean'] == -2.5 and primary['ci95'] == [-2.5, -2.5]
    assert primary['parent_mean_deltas'] == {str(parent): -(parent+1.) for parent in range(4)}
    assert primary['interval_scope'] == 'CONDITIONAL_ON_FOUR_FROZEN_PARENTS'
    assert result['bootstrap_seed'] == 29000001


@pytest.mark.parametrize('error', ['seed', 'heldout', 'parent', 'missing'])
def test_actual_game_pairing_or_complete_heldout_inventory_errors_are_rejected(error):
    rows = cohort()
    if error == 'seed':
        rows[0]['arms']['EPISODE_MEAN_MC']['game_summaries'][0]['seed'] += 1
    elif error == 'heldout':
        rows[0]['arms']['EPISODE_MEAN_MC']['heldout']['game_metrics'][0]['count'] += 1
    elif error == 'parent':
        rows[1]['parent'] = 0
    else:
        rows.pop()
    with pytest.raises(ValueError):
        summarize(rows, draws=40)


def test_cutoff_and_negative_utility_are_retained_in_primary():
    rows = cohort()
    rows[0]['arms']['EPISODE_MEAN_MC']['game_summaries'][0].update(status='CUTOFF', utility=-49.)
    result = summarize(rows, draws=40)
    assert not result['complete_game_endpoints']
    assert result['arms']['EPISODE_MEAN_MC']['cutoffs'] == 1
    assert result['by_lifecycle'][0]['arms']['EPISODE_MEAN_MC']['mean_game_utility'] == -4.
    assert result['paired_contrasts'][result['primary_contrast']]['mean'] == -1.1875


def test_analysis_is_read_only_and_reproducible():
    rows = cohort()
    before = deepcopy(rows)
    first = summarize(rows, draws=40)
    assert rows == before and first == summarize(rows, draws=40)
