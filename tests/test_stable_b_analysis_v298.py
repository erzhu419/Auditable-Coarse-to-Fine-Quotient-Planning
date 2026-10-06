"""Fresh stable-B cohort pairing, primary endpoint and adverse-case retention."""
from copy import deepcopy
import random
from statistics import mean

import pytest

from acfqp.science.stable_b_analysis_v298 import ARMS, summarize


def cohort(mean_shift=2.):
    rows = []
    for life in range(64):
        arms = {}
        for arm, shift, error in zip(ARMS, (0., 1., mean_shift), (1., .5, .25)):
            metrics = [dict(episode=0, start=0, end=1, count=1, bias=-1., mse=error, mae=error)]
            if life == 0:
                metrics.append(dict(episode=1, start=1, end=1001, count=1000,
                                    bias=0., mse=9.*error, mae=3.*error))
            arms[arm] = dict(game_summaries=[dict(seed=298900000000+life*1000000+episode,
                utility=life+shift, status='LOST', steps=10+episode) for episode in range(32)],
                heldout=dict(game_metrics=metrics, metrics=dict(mse=-999999.)),
                training_utility=999999., old_v291_gain=999999.)
        rows.append(dict(lifecycle=life, parent=life % 4, arms=arms))
    return rows


def test_stable_b_supported_only_by_new_complete_primary_games():
    result = summarize(cohort(), draws=20)
    assert result['stable_b_learning_supported'] == result['independent_learning_confirmed'] is True
    assert result['primary_contrast'] == 'EPISODE_MEAN_MC_minus_FROZEN'
    assert result['paired_contrasts'][result['primary_contrast']]['ci95'] == [2., 2.]
    assert result['arms']['FROZEN']['games'] == 64*32
    assert 'stable-B' in result['evidence_scope'] and 'no intervening A-stage' in result['evidence_scope']


def test_better_prediction_and_secondary_utility_cannot_replace_primary():
    result = summarize(cohort(mean_shift=-1.), draws=20)
    primary = result['paired_contrasts'][result['primary_contrast']]
    assert primary['mean'] == -1. and primary['ci95'] == [-1., -1.]
    assert primary['improved_equal_worse'] == [0, 0, 64]
    assert primary['adverse_lifecycles'] == list(range(64))
    assert result['independent_prediction_supported']
    assert result['paired_contrasts']['NORMALIZED_SEQUENTIAL_MC_minus_FROZEN']['mean'] == 1.
    assert not result['stable_b_learning_supported'] and not result['independent_learning_confirmed']


def test_complete_heldout_games_then_lives_are_equal_weighted():
    result = summarize(cohort(), draws=20)
    heldout = result['arms']['FROZEN']['heldout']
    assert result['by_lifecycle'][0]['arms']['FROZEN']['heldout']['mse'] == 5.
    assert heldout['mse'] == 1.0625 and heldout['mae'] == 1.015625
    assert heldout['games'] == 65 and heldout['samples'] == 1064


def test_bootstrap_uses_frozen_new_seed_and_keeps_all_negative_lives():
    rows = cohort()
    values = [(life % 9)-4. for life in range(64)]
    for row, value in zip(rows, values):
        for game, frozen in zip(row['arms']['EPISODE_MEAN_MC']['game_summaries'],
                                row['arms']['FROZEN']['game_summaries']):
            game['utility'] = frozen['utility']+value
    result = summarize(rows, draws=40)
    primary = result['paired_contrasts'][result['primary_contrast']]
    groups = [values[parent::4] for parent in range(4)]
    rng = random.Random(29800001)
    draws = sorted(mean(mean(rng.choices(group, k=16)) for group in groups) for _ in range(40))
    assert result['bootstrap_seed'] == 29800001
    assert primary['ci95'] == pytest.approx([draws[0]+(draws[1]-draws[0])*.975,
                                           draws[38]+(draws[39]-draws[38])*.025])
    assert primary['adverse_lifecycles'] == [life for life, value in enumerate(values) if value < 0.]
    assert len(primary['lifecycle_deltas']) == 64


@pytest.mark.parametrize('error', ['old_seed', 'heldout_identity', 'missing_life'])
def test_old_seed_or_mismatched_holdout_or_omitted_negative_life_is_rejected(error):
    rows = cohort()
    if error == 'old_seed':
        rows[0]['arms']['EPISODE_MEAN_MC']['game_summaries'][0]['seed'] = 291900000000
    elif error == 'heldout_identity':
        rows[0]['arms']['EPISODE_MEAN_MC']['heldout']['game_metrics'][0]['count'] += 1
    else:
        rows.pop()
    with pytest.raises(ValueError):
        summarize(rows, draws=20)


def test_cutoff_stays_in_primary_and_blocks_stable_b_learning():
    rows = cohort()
    rows[0]['arms']['EPISODE_MEAN_MC']['game_summaries'][0].update(status='CUTOFF', utility=-62.)
    result = summarize(rows, draws=20)
    assert not result['complete_game_endpoints'] and not result['stable_b_learning_supported']
    life = result['by_lifecycle'][0]['arms']['EPISODE_MEAN_MC']
    assert life['cutoff_episodes'] == [0] and life['mean_game_utility'] == 0.
    assert result['paired_contrasts'][result['primary_contrast']]['mean'] == 1.96875


def test_zero_primary_bound_and_secondary_cutoff_each_block_support():
    result = summarize(cohort(mean_shift=0.), draws=20)
    assert result['paired_contrasts'][result['primary_contrast']]['ci95'] == [0., 0.]
    assert not result['stable_b_learning_supported']
    rows = cohort()
    rows[0]['arms']['NORMALIZED_SEQUENTIAL_MC']['game_summaries'][5]['status'] = 'CUTOFF'
    result = summarize(rows, draws=20)
    assert not result['stable_b_learning_supported']
    assert result['by_lifecycle'][0]['arms']['NORMALIZED_SEQUENTIAL_MC']['cutoff_episodes'] == [5]


def test_analysis_leaves_new_b_inventory_readonly():
    rows = cohort()
    before = deepcopy(rows)
    result = summarize(rows, draws=20)
    assert rows == before and result == summarize(list(reversed(rows)), draws=20)
