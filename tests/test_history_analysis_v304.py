"""History effects, retained paired seeds and conditional uncertainty are distinct."""
from copy import deepcopy
import random
from statistics import mean

import pytest

from acfqp.science.history_analysis_v304 import ARMS, PRIMARY_CONTRAST, summarize


def cohort(gains=None):
    gains = gains or dict(SOURCE=0., MC_FRESH_B=.5, MC_AFTER_A1_B=-2.,
                         LOCAL_FRESH_B=1., LOCAL_AFTER_A1_B=-1.)
    return [dict(lifecycle=life, parent=life % 4, arms={arm:dict(evaluation=dict(game_summaries=[
        dict(seed=303900100000+life*1000000+episode, utility=life+gains[arm], status='LOST', steps=episode+1)
        for episode in range(32)])) for arm in ARMS}) for life in range(64)]


def games(row, arm):
    return row['arms'][arm]['evaluation']['game_summaries']


def test_matched_history_effect_does_not_replace_fresh_b_gain_or_confirmation():
    result = summarize(cohort(), draws=20)
    assert result['primary_contrast']==PRIMARY_CONTRAST
    assert result['paired_contrasts'][PRIMARY_CONTRAST]['ci95']==[2., 2.]
    assert result['primary_history_penalty_supported']
    assert result['fresh_b_gain_supported']==dict(LOCAL=True, MC=True)
    assert result['history_negative_transfer_supported']==dict(LOCAL=True, MC=True)
    assert result['history_diagnosis']=='FRESH_B_GAIN_WITH_HISTORY_NEGATIVE_TRANSFER_SUPPORTED'
    assert result['arms']['LOCAL_FRESH_B']['games']==2048
    assert result['arms']['LOCAL_FRESH_B']['mean_game_utility']==32.5
    assert 'not independent confirmation' in result['evidence_scope']
    assert 'Equal B exposure does not imply equal total' in result['contribution_scope']


def test_history_penalty_can_be_supported_when_fresh_b_learning_still_fails():
    result = summarize(cohort(dict(SOURCE=0., MC_FRESH_B=-1., MC_AFTER_A1_B=-2.,
                                  LOCAL_FRESH_B=-1., LOCAL_AFTER_A1_B=-2.)), draws=20)
    assert result['primary_history_penalty_supported']
    assert not result['fresh_b_gain_supported']['LOCAL']
    assert result['history_diagnosis']=='HISTORY_NEGATIVE_TRANSFER_SUPPORTED'


def test_history_can_help_and_both_arms_can_gain_without_negative_transfer():
    result = summarize(cohort(dict(SOURCE=0., MC_FRESH_B=1., MC_AFTER_A1_B=1.,
                                  LOCAL_FRESH_B=1., LOCAL_AFTER_A1_B=2.)), draws=20)
    assert not result['primary_history_penalty_supported']
    assert result['history_effect_status']==dict(LOCAL='SUPPORTED_BENEFIT', MC='UNRESOLVED')
    assert result['history_diagnosis']=='HISTORY_INITIALIZATION_BENEFIT_SUPPORTED'
    assert not any(result['history_negative_transfer_supported'].values())


def test_history_penalty_with_positive_inherited_gain_is_not_negative_transfer():
    result = summarize(cohort(dict(SOURCE=0., MC_FRESH_B=2., MC_AFTER_A1_B=1.,
                                  LOCAL_FRESH_B=2., LOCAL_AFTER_A1_B=1.)), draws=20)
    assert result['primary_history_penalty_supported']
    assert result['history_diagnosis']=='HISTORY_INITIALIZATION_PENALTY_SUPPORTED'
    assert not result['history_negative_transfer_supported']['LOCAL']


def test_stratified_bootstrap_preserves_parent_weight_and_signed_lifecycle_effects():
    rows = cohort()
    values = [(life % 9)-4. for life in range(64)]
    for row, value in zip(rows, values):
        for fresh, inherited in zip(games(row, 'LOCAL_FRESH_B'), games(row, 'LOCAL_AFTER_A1_B')):
            fresh['utility'] = inherited['utility']+value
    result = summarize(rows, draws=40)
    contrast = result['paired_contrasts'][PRIMARY_CONTRAST]
    groups = [values[parent::4] for parent in range(4)]
    rng = random.Random(30400001)
    samples = sorted(mean(mean(rng.choices(group, k=16)) for group in groups) for _ in range(40))
    assert contrast['ci95']==pytest.approx([samples[0]+(samples[1]-samples[0])*.975,
                                          samples[38]+(samples[39]-samples[38])*.025])
    assert contrast['parent_mean_deltas']=={str(parent):mean(group) for parent, group in enumerate(groups)}
    assert contrast['lifecycle_deltas']=={str(life):value for life, value in enumerate(values)}
    assert contrast['adverse_lifecycles']==[life for life, value in enumerate(values) if value<0.]
    assert result['history_effect_status']['LOCAL']=='UNRESOLVED'
    assert not result['primary_history_penalty_supported']


@pytest.mark.parametrize('arm', ARMS)
def test_cutoffs_are_retained_and_block_complete_game_claims(arm):
    rows = cohort()
    games(rows[0], arm)[0].update(status='CUTOFF', utility=-30.)
    result = summarize(rows, draws=2)
    assert not result['complete_game_endpoints']
    assert not result['primary_history_penalty_supported']
    assert not any(result['fresh_b_gain_supported'].values())
    assert result['by_lifecycle'][0]['arms'][arm]['cutoff_episodes']==[0]
    assert result['arms'][arm]['games']==2048


@pytest.mark.parametrize('error', ['missing_life', 'wrong_parent', 'wrong_seed', 'wrong_task_seed', 'missing_game'])
def test_incomplete_inventory_or_unmatched_replay_is_rejected(error):
    rows = cohort()
    if error=='missing_life':
        rows.pop()
    elif error=='wrong_parent':
        rows[0]['parent'] = 1
    elif error=='missing_game':
        games(rows[0], 'LOCAL_FRESH_B').pop()
    else:
        games(rows[0], 'LOCAL_FRESH_B')[0]['seed'] = 302900000000 if error=='wrong_seed' else 303900000000
    with pytest.raises(ValueError):
        summarize(rows, draws=2)


def test_old_cohort_outcomes_training_metrics_and_input_order_cannot_select_primary():
    rows = cohort()
    before = deepcopy(rows)
    result = summarize(rows, draws=2)
    assert rows==before and result==summarize(list(reversed(rows)), draws=2)
    for row in rows:
        row['old_v302_primary'] = -1e9
        for arm in row['arms'].values():
            arm['training_utility'] = 1e9
    assert result==summarize(rows, draws=2)


def test_heldout_errors_are_descriptive_and_game_then_lifecycle_weighted():
    rows = cohort()
    for row in rows:
        for arm in ARMS:
            metrics = [dict(episode=0, start=0, end=1, count=1, bias=-1., mse=1., mae=1.)]
            if row['lifecycle']==0:
                metrics.append(dict(episode=1, start=1, end=1001, count=1000, bias=0., mse=9., mae=3.))
            row['arms'][arm]['heldout'] = dict(game_metrics=metrics)
    result = summarize(rows, draws=2)
    heldout = result['heldout']['SOURCE']
    assert heldout['games']==65 and heldout['samples']==1064
    assert heldout['mse']==1.0625 and heldout['mae']==1.015625
    assert result['primary_history_penalty_supported']
    rows[0]['arms']['MC_FRESH_B']['heldout']['game_metrics'][0]['count'] += 1
    with pytest.raises(ValueError, match='same complete B heldout inventory'):
        summarize(rows, draws=2)


def test_risk_diagnostics_share_complete_game_identity_and_factual_terminal_labels():
    rows = cohort()
    for row in rows:
        for arm in ARMS:
            row['arms'][arm]['heldout'] = dict(game_metrics=[
                dict(episode=0, start=0, end=1, count=1, bias=-1., mse=1., mae=1.)])
        for arm in ('LOCAL_FRESH_B', 'LOCAL_AFTER_A1_B'):
            row['arms'][arm]['heldout']['component_game_metrics'] = [dict(
                episode=0, start=0, end=1, count=1, reward_bias=0., reward_mse=0., reward_mae=0.,
                risk_brier=.04, risk_log_loss=.25, risk_bias=.2, mean_risk_probability=.2, win_label=0.)]
    result = summarize(rows, draws=2)
    assert result['heldout']['LOCAL_FRESH_B']['components']['risk_brier']==.04
    assert 'components' not in result['heldout']['SOURCE']
    rows[0]['arms']['LOCAL_FRESH_B']['heldout']['component_game_metrics'][0]['win_label'] = .2
    with pytest.raises(ValueError, match='factual complete-game outcomes'):
        summarize(rows, draws=2)
