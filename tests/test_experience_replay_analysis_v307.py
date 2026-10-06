"""Replay utility is distinct from A1 preservation and SOURCE benefit."""
from copy import deepcopy
import random
from statistics import mean

import pytest

from acfqp.science.experience_replay_analysis_v307 import ARMS, summarize


def cohort(new_only=1., mixed=2., frozen=1.5):
    gains = dict(SOURCE=0., A1_FROZEN=frozen, NEW_ONLY=new_only, MIXED_REPLAY=mixed)
    return [dict(lifecycle=life, parent=life % 4,
        arms={arm:dict(evaluation=dict(game_summaries=[
            dict(seed=307900000000+life*1000000+episode,
                 utility=life+gain, status='LOST', steps=episode+1)
            for episode in range(32)])) for arm, gain in gains.items()}) for life in range(64)]


def games(row, arm='MIXED_REPLAY'):
    return row['arms'][arm]['evaluation']['game_summaries']


def test_primary_replay_advantage_and_a1_retention_use_new_a_seeds():
    result = summarize(cohort(), draws=20)
    assert result['primary_contrast']=='MIXED_REPLAY_minus_NEW_ONLY'
    assert result['primary_replay_gain_supported']
    assert result['paired_contrasts']['MIXED_REPLAY_minus_NEW_ONLY']['ci95']==[1., 1.]
    assert result['paired_contrasts']['MIXED_REPLAY_minus_A1_FROZEN']['ci95']==[.5, .5]
    assert result['replay_retention_status']=='SUPPORTED_NONDECREASE'
    assert result['replay_no_degradation_supported']
    assert result['source_reference_gain_supported']==dict(A1_FROZEN=True, NEW_ONLY=True, MIXED_REPLAY=True)
    assert result['arms']['MIXED_REPLAY']['games']==64*32
    assert result['arms']['MIXED_REPLAY']['mean_game_utility']==33.5
    assert 'RETAINED_A1_AND_V306_CURRENT_DATA_HISTORIES' in result['primary_replay_gain_status']
    assert 'No new training cohort is acquired' in result['evidence_scope']


def test_replay_advantage_and_gain_over_source_can_coexist_with_a1_loss():
    result = summarize(cohort(new_only=1., mixed=2., frozen=3.), draws=20)
    assert result['primary_replay_gain_supported']
    assert result['source_reference_gain_supported']['MIXED_REPLAY']
    assert result['replay_retention_status']=='SUPPORTED_LOSS'
    assert not result['replay_no_degradation_supported']


def test_retention_does_not_substitute_for_failed_replay_advantage():
    result = summarize(cohort(new_only=3., mixed=2., frozen=1.), draws=20)
    assert not result['primary_replay_gain_supported']
    assert result['replay_no_degradation_supported']
    assert result['paired_contrasts']['MIXED_REPLAY_minus_NEW_ONLY']['ci95']==[-1., -1.]


def test_exact_zero_retention_is_supported_but_exact_zero_primary_is_not():
    result = summarize(cohort(new_only=2., mixed=2., frozen=2.), draws=20)
    assert not result['primary_replay_gain_supported']
    assert result['paired_contrasts']['MIXED_REPLAY_minus_A1_FROZEN']['ci95']==[0., 0.]
    assert result['replay_retention_status']=='SUPPORTED_NONDECREASE'
    assert result['replay_no_degradation_supported']


def test_crossing_zero_retention_remains_unresolved_despite_replay_advantage():
    rows = cohort(new_only=-5., mixed=1.5, frozen=1.5)
    for life, row in enumerate(rows):
        for game in games(row):
            game['utility'] += 2. if (life // 4) % 2 else -2.
    result = summarize(rows, draws=40)
    lower, upper = result['paired_contrasts']['MIXED_REPLAY_minus_A1_FROZEN']['ci95']
    assert lower<0.<upper
    assert result['primary_replay_gain_supported']
    assert result['replay_retention_status']=='UNRESOLVED'
    assert not result['replay_no_degradation_supported']


def test_parent_bootstrap_uses_v307_seed_and_retains_signed_lifecycle_results():
    rows = cohort()
    values = [(life % 9)-4. for life in range(64)]
    for row, value in zip(rows, values):
        for mixed, new_only in zip(games(row), games(row, 'NEW_ONLY')):
            mixed['utility'] = new_only['utility']+value
    result = summarize(rows, draws=40)
    contrast = result['paired_contrasts']['MIXED_REPLAY_minus_NEW_ONLY']
    groups = [values[parent::4] for parent in range(4)]
    rng = random.Random(30700001)
    samples = sorted(mean(mean(rng.choices(group, k=16)) for group in groups) for _ in range(40))
    assert contrast['ci95']==pytest.approx([samples[0]+(samples[1]-samples[0])*.975,
                                          samples[38]+(samples[39]-samples[38])*.025])
    assert contrast['parent_mean_deltas']=={str(parent):mean(group) for parent, group in enumerate(groups)}
    assert contrast['adverse_lifecycles']==[life for life, value in enumerate(values) if value<0.]
    assert contrast['lifecycle_deltas']=={str(life):value for life, value in enumerate(values)}
    assert result['bootstrap_seed']==30700001


@pytest.mark.parametrize('arm', ARMS)
def test_cutoff_in_any_arm_is_retained_and_blocks_supported_claims(arm):
    rows = cohort()
    games(rows[0], arm)[0].update(status='CUTOFF', utility=-30.)
    result = summarize(rows, draws=2)
    assert not result['complete_game_endpoints'] and not result['primary_replay_gain_supported']
    assert not result['replay_no_degradation_supported']
    assert result['replay_retention_status']=='INCOMPLETE_GAME_ENDPOINTS'
    assert result['by_lifecycle'][0]['arms'][arm]['cutoff_episodes']==[0]
    assert not any(result['source_reference_gain_supported'].values())
    assert result['arms'][arm]['games']==2048


@pytest.mark.parametrize('arm', ARMS)
def test_old_evaluation_seeds_cannot_enter_new_v307_pairs(arm):
    rows = cohort()
    games(rows[0], arm)[0]['seed'] = 306900000000
    with pytest.raises(ValueError, match='new paired A evaluation seeds'):
        summarize(rows, draws=2)


@pytest.mark.parametrize('error', ['missing_life', 'wrong_parent', 'missing_game', 'unknown_status'])
def test_incomplete_inventory_and_unknown_status_are_rejected(error):
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


def test_old_outcomes_training_metrics_and_input_order_do_not_change_primary():
    rows = cohort()
    before = deepcopy(rows)
    result = summarize(rows, draws=2)
    assert rows==before and result==summarize(list(reversed(rows)), draws=2)
    for row in rows:
        row['old_v306_primary'] = -1e9
        row['fit'] = dict(training_utility=1e9, retained_old_fact_accuracy=1.)
    assert result==summarize(rows, draws=2)
