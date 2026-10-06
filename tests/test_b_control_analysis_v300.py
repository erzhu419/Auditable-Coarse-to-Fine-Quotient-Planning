"""V300 primary utility, old-data scope, complete inventory and signed evidence."""
from copy import deepcopy
import random
from statistics import mean

import pytest

from acfqp.science.b_control_analysis_v300 import ARMS, summarize


def cohort(control_shift=2., mc_shift=1., control_error=.25):
    rows = []
    for life in range(64):
        arms = {}
        for arm, shift, error in zip(ARMS, (0., mc_shift, control_shift), (1., .5, control_error)):
            metrics = [dict(episode=0, start=0, end=1, count=1, bias=-1., mse=error, mae=error)]
            if life == 0:
                metrics.append(dict(episode=1, start=1, end=1001, count=1000,
                                    bias=0., mse=9.*error, mae=3.*error))
            arms[arm] = dict(game_summaries=[dict(seed=300900000000+life*1000000+episode,
                utility=life+shift, status='LOST', steps=10+episode) for episode in range(32)],
                heldout=dict(game_metrics=metrics, metrics=dict(mse=-999999.)),
                training_utility=999999., old_v298_gain=999999.,
                evaluation_counts=dict(raw_tiles=100))
        rows.append(dict(lifecycle=life, parent=life % 4, arms=arms))
    return rows


def test_control_support_requires_primary_fresh_game_gain_not_prediction():
    result = summarize(cohort(control_error=4.), draws=20)
    assert result['control_target_gain_supported']
    assert result['primary_contrast'] == 'EXPECTED_CONTROL_minus_SOURCE'
    assert result['paired_contrasts'][result['primary_contrast']]['ci95'] == [2., 2.]
    assert result['heldout_contrasts'][result['primary_contrast']]['mse']['mean'] > 0.
    assert result['arms']['SOURCE']['games'] == 64*32
    assert 'retained V298 B training data' in result['evidence_scope']
    assert 'Not an independent new learning cohort' in result['evidence_scope']
    assert 'independent_learning_confirmed' not in result


@pytest.mark.parametrize('mc_shift', [1., -2.])
def test_better_prediction_or_either_secondary_cannot_replace_negative_primary(mc_shift):
    result = summarize(cohort(control_shift=-1., mc_shift=mc_shift), draws=20)
    primary = result['paired_contrasts'][result['primary_contrast']]
    assert primary['mean'] == -1. and primary['ci95'] == [-1., -1.]
    assert primary['improved_equal_worse'] == [0, 0, 64]
    assert primary['adverse_lifecycles'] == list(range(64))
    assert result['heldout_contrasts'][result['primary_contrast']]['mse']['ci95'][1] < 0.
    secondary = 'MC_minus_SOURCE' if mc_shift>0. else 'EXPECTED_CONTROL_minus_MC'
    assert result['paired_contrasts'][secondary]['mean'] == 1.
    assert not result['control_target_gain_supported']


def test_old_target_returns_training_scores_and_aggregate_errors_never_select():
    rows = cohort()
    original = summarize(rows, draws=20)
    for row in rows:
        for value in row['arms'].values():
            value.update(training_utility=-1e9, old_v298_gain=-1e9, target_fit_mse=1e9)
            value['heldout']['metrics'] = dict(mse=1e9, mae=1e9, bias=1e9)
    assert summarize(rows, draws=20) == original


def test_complete_heldout_games_then_lives_are_equal_weighted():
    result = summarize(cohort(), draws=20)
    heldout = result['arms']['SOURCE']['heldout']
    assert result['by_lifecycle'][0]['arms']['SOURCE']['heldout']['mse'] == 5.
    assert heldout['mse'] == 1.0625 and heldout['mae'] == 1.015625
    assert heldout['games'] == 65 and heldout['samples'] == 1064


def test_bootstrap_uses_frozen_seed_keeps_all_signed_differences_and_fixed_parents():
    rows = cohort()
    values = [(life % 9)-4. for life in range(64)]
    for row, value in zip(rows, values):
        for game, source in zip(row['arms']['EXPECTED_CONTROL']['game_summaries'],
                                row['arms']['SOURCE']['game_summaries']):
            game['utility'] = source['utility']+value
    result = summarize(rows, draws=40)
    primary = result['paired_contrasts'][result['primary_contrast']]
    groups = [values[parent::4] for parent in range(4)]
    rng = random.Random(30000001)
    draws = sorted(mean(mean(rng.choices(group, k=16)) for group in groups) for _ in range(40))
    assert result['bootstrap_seed'] == 30000001
    assert primary['ci95'] == pytest.approx([draws[0]+(draws[1]-draws[0])*.975,
                                           draws[38]+(draws[39]-draws[38])*.025])
    assert primary['adverse_lifecycles'] == [life for life, value in enumerate(values) if value < 0.]
    assert primary['lifecycle_deltas'] == {str(life):value for life,value in enumerate(values)}


@pytest.mark.parametrize('error', ['old_seed', 'missing_game', 'heldout_identity', 'missing_life', 'wrong_parent'])
def test_reused_evaluation_or_omitted_inventory_is_rejected(error):
    rows = cohort()
    if error == 'old_seed':
        rows[0]['arms']['EXPECTED_CONTROL']['game_summaries'][0]['seed'] = 298900000000
    elif error == 'missing_game':
        rows[0]['arms']['EXPECTED_CONTROL']['game_summaries'].pop()
    elif error == 'heldout_identity':
        rows[0]['arms']['EXPECTED_CONTROL']['heldout']['game_metrics'][0]['count'] += 1
    elif error == 'missing_life':
        rows.pop()
    else:
        rows[0]['parent'] = 1
    with pytest.raises(ValueError):
        summarize(rows, draws=20)


def test_cutoff_stays_in_primary_and_blocks_support():
    rows = cohort()
    rows[0]['arms']['EXPECTED_CONTROL']['game_summaries'][0].update(status='CUTOFF', utility=-62.)
    result = summarize(rows, draws=20)
    assert not result['complete_game_endpoints'] and not result['control_target_gain_supported']
    life = result['by_lifecycle'][0]['arms']['EXPECTED_CONTROL']
    assert life['cutoff_episodes'] == [0] and life['mean_game_utility'] == 0.
    assert result['paired_contrasts'][result['primary_contrast']]['mean'] == 1.96875


def test_zero_bound_and_secondary_cutoff_each_block_support():
    result = summarize(cohort(control_shift=0.), draws=20)
    assert result['paired_contrasts'][result['primary_contrast']]['ci95'] == [0., 0.]
    assert not result['control_target_gain_supported']
    rows = cohort()
    rows[0]['arms']['MC']['game_summaries'][5]['status'] = 'CUTOFF'
    result = summarize(rows, draws=20)
    assert not result['control_target_gain_supported']
    assert result['by_lifecycle'][0]['arms']['MC']['cutoff_episodes'] == [5]


def test_analysis_does_not_update_retained_training_or_new_evaluation_inventory():
    rows = cohort()
    before = deepcopy(rows)
    result = summarize(rows, draws=20)
    assert rows == before and result == summarize(list(reversed(rows)), draws=20)

