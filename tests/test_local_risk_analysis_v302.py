"""V302 new-cohort confirmation endpoint, shared inventories and signed results."""
from copy import deepcopy
import random
from statistics import mean

import pytest

from acfqp.science.local_risk_analysis_v302 import ARMS, PAIRS, summarize


def cohort(local_shift=1., mc_shift=-1., local_error=.25):
    rows = []
    for life in range(64):
        arms = {}
        for arm, shift, error in zip(ARMS, (0., mc_shift, local_shift),
                                     (1., .5, local_error)):
            metrics = [dict(episode=0, start=0, end=1, count=1, bias=-1., mse=error, mae=error)]
            if life == 0:
                metrics.append(dict(episode=1, start=1, end=1001, count=1000,
                                    bias=0., mse=9.*error, mae=3.*error))
            heldout = dict(game_metrics=metrics, metrics=dict(mse=-999999.))
            if arm == 'LOCAL_RISK':
                heldout['component_game_metrics'] = [dict(
                    episode=game['episode'], start=game['start'], end=game['end'], count=game['count'],
                    reward_bias=-.2, reward_mse=2.+8.*game['episode'], reward_mae=1.+2.*game['episode'],
                    risk_brier=.3+.2*game['episode'], risk_log_loss=.8+.2*game['episode'],
                    risk_bias=.1, mean_risk_probability=.5, win_label=float(game['episode']))
                    for game in metrics]
            arms[arm] = dict(game_summaries=[dict(seed=302900000000+life*1000000+episode,
                utility=life+shift, status='LOST', steps=10+episode) for episode in range(32)],
                heldout=heldout, training_utility=999999., old_v301_gain=999999.)
        rows.append(dict(lifecycle=life, parent=life % 4, arms=arms))
    return rows


def test_confirmation_uses_local_source_whole_games_not_component_accuracy():
    rows = cohort(local_error=4.)
    for row in rows:
        for game in row['arms']['LOCAL_RISK']['heldout']['component_game_metrics']:
            game.update(risk_brier=.9, reward_mse=99.)
    result = summarize(rows, draws=20)
    assert result['independent_local_learning_confirmed']
    assert result['primary_contrast'] == 'LOCAL_RISK_minus_SOURCE'
    assert result['paired_contrasts'][result['primary_contrast']]['ci95'] == [1., 1.]
    assert result['heldout_contrasts'][result['primary_contrast']]['mse']['mean'] > 0.
    assert result['arms']['LOCAL_RISK']['heldout']['components']['risk_brier'] == .9
    assert result['arms']['SOURCE']['games'] == 64*32
    assert set(result['paired_contrasts']) == {left+'_minus_'+right for left,right in PAIRS}
    assert result['independent_local_learning_status'] == 'CONFIRMED_CONDITIONAL_ON_FOUR_FROZEN_PARENTS'
    assert 'independent new B learning cohort' in result['evidence_scope']
    assert 'source parents are reused' in result['evidence_scope']
    assert 'not fresh-source confirmation' in result['evidence_scope']
    assert 'continual learning or cross-task strategic transfer' in result['evidence_scope']
    assert 'LOCAL_RISK versus MC' in result['contribution_scope']
    assert 'Shared samples do not imply equal compute budgets' in result['contribution_scope']


@pytest.mark.parametrize('local_shift', [-1., 0.])
def test_beating_degraded_mc_and_good_calibration_cannot_replace_source_gain(local_shift):
    result = summarize(cohort(local_shift=local_shift, mc_shift=-2.), draws=20)
    primary = result['paired_contrasts'][result['primary_contrast']]
    assert primary['mean'] == local_shift and primary['ci95'] == [local_shift, local_shift]
    assert result['paired_contrasts']['LOCAL_RISK_minus_MC']['ci95'][0] > 0.
    assert result['heldout_contrasts'][result['primary_contrast']]['mse']['ci95'][1] < 0.
    assert not result['independent_local_learning_confirmed']
    assert result['independent_local_learning_status'] == 'NOT_CONFIRMED_CONDITIONAL_ON_FOUR_FROZEN_PARENTS'
    assert primary['adverse_lifecycles'] == (list(range(64)) if local_shift < 0. else [])


def test_old_development_gains_training_outcomes_and_aggregates_are_not_pooled():
    rows = cohort()
    original = summarize(rows, draws=20)
    for row in rows:
        row['old_v301_primary'] = dict(mean=-1e9, ci95=[-1e9, -1e9])
        for value in row['arms'].values():
            value.update(training_utility=-1e9, old_v301_gain=-1e9, target_fit_mse=1e9)
            value['heldout']['metrics'] = dict(mse=1e9, mae=1e9, bias=1e9)
    assert summarize(rows, draws=20) == original
    assert 'not pooled' in original['evidence_scope']


def test_complete_heldout_games_and_components_weight_games_then_lifecycles():
    result = summarize(cohort(), draws=20)
    heldout = result['arms']['SOURCE']['heldout']
    assert result['by_lifecycle'][0]['arms']['SOURCE']['heldout']['mse'] == 5.
    assert heldout['mse'] == 1.0625 and heldout['mae'] == 1.015625
    assert heldout['games'] == 65 and heldout['samples'] == 1064
    component = result['arms']['LOCAL_RISK']['heldout']['components']
    assert component['games'] == 65 and component['samples'] == 1064
    assert component['reward_mse'] == 2.0625 and component['risk_brier'] == pytest.approx(.3015625)
    assert component['win_label'] == .0078125
    assert 'components' not in result['arms']['SOURCE']['heldout']


def test_new_bootstrap_seed_keeps_all_signed_lifecycle_and_parent_results():
    rows = cohort()
    values = [(life % 9)-4. for life in range(64)]
    for row, value in zip(rows, values):
        for game, source in zip(row['arms']['LOCAL_RISK']['game_summaries'],
                                row['arms']['SOURCE']['game_summaries']):
            game['utility'] = source['utility']+value
    result = summarize(rows, draws=40)
    primary = result['paired_contrasts'][result['primary_contrast']]
    groups = [values[parent::4] for parent in range(4)]
    rng = random.Random(30200001)
    draws = sorted(mean(mean(rng.choices(group, k=16)) for group in groups) for _ in range(40))
    assert result['bootstrap_seed'] == 30200001
    assert primary['ci95'] == pytest.approx([draws[0]+(draws[1]-draws[0])*.975,
                                           draws[38]+(draws[39]-draws[38])*.025])
    assert primary['adverse_lifecycles'] == [life for life, value in enumerate(values) if value < 0.]
    assert primary['lifecycle_deltas'] == {str(life):value for life,value in enumerate(values)}
    assert primary['parent_mean_deltas'] == {str(parent):mean(group) for parent,group in enumerate(groups)}
    assert primary['interval_scope'] == 'CONDITIONAL_ON_FOUR_FROZEN_PARENTS'


@pytest.mark.parametrize('arm', ARMS)
def test_old_evaluation_seed_cannot_enter_new_confirmation(arm):
    rows = cohort()
    rows[0]['arms'][arm]['game_summaries'][0]['seed'] = 301900000000
    with pytest.raises(ValueError, match='fresh paired'):
        summarize(rows, draws=20)


@pytest.mark.parametrize('error', ['missing_game', 'heldout_identity', 'missing_life', 'wrong_parent',
                                  'component_identity', 'missing_component_lifecycle', 'nonterminal_label'])
def test_omitted_inventory_or_mismatched_component_games_are_rejected(error):
    rows = cohort()
    if error == 'missing_game':
        rows[0]['arms']['LOCAL_RISK']['game_summaries'].pop()
    elif error == 'heldout_identity':
        rows[0]['arms']['MC']['heldout']['game_metrics'][0]['count'] += 1
    elif error == 'missing_life':
        rows.pop()
    elif error == 'wrong_parent':
        rows[0]['parent'] = 1
    elif error == 'component_identity':
        rows[0]['arms']['LOCAL_RISK']['heldout']['component_game_metrics'][0]['count'] += 1
    elif error == 'missing_component_lifecycle':
        del rows[0]['arms']['LOCAL_RISK']['heldout']['component_game_metrics']
    else:
        rows[0]['arms']['LOCAL_RISK']['heldout']['component_game_metrics'][0]['win_label'] = .5
    with pytest.raises(ValueError):
        summarize(rows, draws=20)


def test_all_arm_cutoffs_are_retained_and_block_confirmation():
    for arm in ARMS:
        rows = cohort()
        rows[0]['arms'][arm]['game_summaries'][0].update(status='CUTOFF', utility=-62.)
        result = summarize(rows, draws=20)
        assert not result['complete_game_endpoints'] and not result['independent_local_learning_confirmed']
        assert result['by_lifecycle'][0]['arms'][arm]['cutoff_episodes'] == [0]
        assert result['arms'][arm]['games'] == 2048 and result['arms'][arm]['cutoffs'] == 1


def test_receipts_unchanged_and_optional_diagnostics_cannot_change_confirmation():
    rows = cohort()
    before = deepcopy(rows)
    result = summarize(rows, draws=20)
    assert rows == before and result == summarize(list(reversed(rows)), draws=20)
    for row in rows:
        del row['arms']['LOCAL_RISK']['heldout']['component_game_metrics']
    without_components = summarize(rows, draws=20)
    assert result['paired_contrasts'] == without_components['paired_contrasts']
    assert result['independent_local_learning_confirmed'] == without_components['independent_local_learning_confirmed']
