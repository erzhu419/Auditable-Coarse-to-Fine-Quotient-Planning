"""V301 whole-game primary, retained-data scope, complete inventory and diagnostics."""
from copy import deepcopy
import random
from statistics import mean

import pytest

from acfqp.science.split_risk_analysis_v301 import ARMS, PAIRS, summarize


def cohort(global_shift=2., local_shift=1., mc_shift=-1., global_error=.25):
    rows = []
    for life in range(64):
        arms = {}
        for arm, shift, error in zip(ARMS, (0., mc_shift, local_shift, global_shift),
                                     (1., .5, .75, global_error)):
            metrics = [dict(episode=0, start=0, end=1, count=1, bias=-1., mse=error, mae=error)]
            if life == 0:
                metrics.append(dict(episode=1, start=1, end=1001, count=1000,
                                    bias=0., mse=9.*error, mae=3.*error))
            heldout = dict(game_metrics=metrics, metrics=dict(mse=-999999.))
            if arm in ('LOCAL_RISK', 'GLOBAL_RISK'):
                heldout['component_game_metrics'] = [dict(
                    episode=game['episode'], start=game['start'], end=game['end'], count=game['count'],
                    reward_bias=-.2, reward_mse=2.+8.*game['episode'], reward_mae=1.+2.*game['episode'],
                    risk_brier=.3+.2*game['episode'], risk_log_loss=.8+.2*game['episode'],
                    risk_bias=.1, mean_risk_probability=.5, win_label=float(game['episode']))
                    for game in metrics]
            arms[arm] = dict(game_summaries=[dict(seed=301900000000+life*1000000+episode,
                utility=life+shift, status='LOST', steps=10+episode) for episode in range(32)],
                heldout=heldout, training_utility=999999., old_v298_gain=999999.)
        rows.append(dict(lifecycle=life, parent=life % 4, arms=arms))
    return rows


def test_split_support_requires_primary_fresh_game_gain_not_prediction_or_risk():
    rows = cohort(global_error=4.)
    for row in rows:
        for game in row['arms']['GLOBAL_RISK']['heldout']['component_game_metrics']:
            game.update(risk_brier=.9, reward_mse=99.)
    result = summarize(rows, draws=20)
    assert result['split_risk_gain_supported']
    assert result['primary_contrast'] == 'GLOBAL_RISK_minus_SOURCE'
    assert result['paired_contrasts'][result['primary_contrast']]['ci95'] == [2., 2.]
    assert result['heldout_contrasts'][result['primary_contrast']]['mse']['mean'] > 0.
    assert result['arms']['GLOBAL_RISK']['heldout']['components']['risk_brier'] == .9
    assert result['arms']['SOURCE']['games'] == 64*32
    assert len(result['paired_contrasts']) == 5
    assert 'retained V298 B training data' in result['evidence_scope']
    assert 'Not an independent new learning cohort' in result['evidence_scope']
    assert 'feature basis and dimension' in result['contribution_scope']
    assert 'not an equal-compute contrast' in result['contribution_scope']
    assert 'independent_learning_confirmed' not in result


@pytest.mark.parametrize('local_shift,mc_shift', [(2., -2.), (-2., 2.)])
def test_secondary_or_calibration_cannot_replace_negative_global_source(local_shift, mc_shift):
    result = summarize(cohort(global_shift=-1., local_shift=local_shift, mc_shift=mc_shift), draws=20)
    primary = result['paired_contrasts'][result['primary_contrast']]
    assert primary['mean'] == -1. and primary['ci95'] == [-1., -1.]
    assert primary['improved_equal_worse'] == [0, 0, 64]
    assert primary['adverse_lifecycles'] == list(range(64))
    assert result['heldout_contrasts'][result['primary_contrast']]['mse']['ci95'][1] < 0.
    assert result['paired_contrasts']['GLOBAL_RISK_minus_MC' if mc_shift<0.
                                      else 'GLOBAL_RISK_minus_LOCAL_RISK']['mean'] == 1.
    assert not result['split_risk_gain_supported']


def test_old_training_outcomes_and_aggregate_scores_do_not_select_lifecycles():
    rows = cohort()
    original = summarize(rows, draws=20)
    for row in rows:
        for value in row['arms'].values():
            value.update(training_utility=-1e9, old_v298_gain=-1e9, target_fit_mse=1e9)
            value['heldout']['metrics'] = dict(mse=1e9, mae=1e9, bias=1e9)
    assert summarize(rows, draws=20) == original


def test_heldout_and_components_equal_weight_complete_games_then_lifecycles():
    result = summarize(cohort(), draws=20)
    heldout = result['arms']['SOURCE']['heldout']
    assert result['by_lifecycle'][0]['arms']['SOURCE']['heldout']['mse'] == 5.
    assert heldout['mse'] == 1.0625 and heldout['mae'] == 1.015625
    assert heldout['games'] == 65 and heldout['samples'] == 1064
    component = result['arms']['GLOBAL_RISK']['heldout']['components']
    assert component['games'] == 65 and component['samples'] == 1064
    assert component['reward_mse'] == 2.0625 and component['risk_brier'] == pytest.approx(.3015625)
    assert component['win_label'] == .0078125
    assert 'components' not in result['arms']['SOURCE']['heldout']


def test_seed_and_parent_bootstrap_preserve_all_signed_lifecycle_results():
    rows = cohort()
    values = [(life % 9)-4. for life in range(64)]
    for row, value in zip(rows, values):
        for game, source in zip(row['arms']['GLOBAL_RISK']['game_summaries'],
                                row['arms']['SOURCE']['game_summaries']):
            game['utility'] = source['utility']+value
    result = summarize(rows, draws=40)
    primary = result['paired_contrasts'][result['primary_contrast']]
    groups = [values[parent::4] for parent in range(4)]
    rng = random.Random(30100001)
    draws = sorted(mean(mean(rng.choices(group, k=16)) for group in groups) for _ in range(40))
    assert result['bootstrap_seed'] == 30100001
    assert primary['ci95'] == pytest.approx([draws[0]+(draws[1]-draws[0])*.975,
                                           draws[38]+(draws[39]-draws[38])*.025])
    assert primary['adverse_lifecycles'] == [life for life, value in enumerate(values) if value < 0.]
    assert primary['lifecycle_deltas'] == {str(life):value for life,value in enumerate(values)}


@pytest.mark.parametrize('arm', ARMS)
def test_each_arm_must_use_all_new_shared_evaluation_seeds(arm):
    rows = cohort()
    rows[0]['arms'][arm]['game_summaries'][0]['seed'] = 300900000000
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
        rows[0]['arms']['GLOBAL_RISK']['heldout']['component_game_metrics'][0]['count'] += 1
    elif error == 'missing_component_lifecycle':
        del rows[0]['arms']['GLOBAL_RISK']['heldout']['component_game_metrics']
    else:
        rows[0]['arms']['LOCAL_RISK']['heldout']['component_game_metrics'][0]['win_label'] = .5
    with pytest.raises(ValueError):
        summarize(rows, draws=20)


def test_cutoff_is_kept_and_blocks_support_in_every_arm():
    for arm in ARMS:
        rows = cohort()
        rows[0]['arms'][arm]['game_summaries'][0].update(status='CUTOFF', utility=-62.)
        result = summarize(rows, draws=20)
        assert not result['complete_game_endpoints'] and not result['split_risk_gain_supported']
        assert result['by_lifecycle'][0]['arms'][arm]['cutoff_episodes'] == [0]
        assert result['arms'][arm]['games'] == 2048 and result['arms'][arm]['cutoffs'] == 1


def test_zero_bound_and_good_calibration_cannot_support_gain():
    result = summarize(cohort(global_shift=0.), draws=20)
    assert result['paired_contrasts'][result['primary_contrast']]['ci95'] == [0., 0.]
    assert not result['split_risk_gain_supported']


def test_summary_keeps_receipts_unchanged_and_optional_diagnostics_do_not_change_utility():
    rows = cohort()
    before = deepcopy(rows)
    result = summarize(rows, draws=20)
    assert rows == before and result == summarize(list(reversed(rows)), draws=20)
    for row in rows:
        for arm in ('LOCAL_RISK', 'GLOBAL_RISK'):
            del row['arms'][arm]['heldout']['component_game_metrics']
    without_components = summarize(rows, draws=20)
    assert result['paired_contrasts'] == without_components['paired_contrasts']
    assert result['split_risk_gain_supported'] == without_components['split_risk_gain_supported']
    assert set(result['paired_contrasts']) == {left+'_minus_'+right for left,right in PAIRS}
