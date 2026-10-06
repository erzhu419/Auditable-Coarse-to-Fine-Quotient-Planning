from copy import deepcopy
from math import ceil

import numpy as np
import pytest

from acfqp.science.cumulative_critic_analysis_v289 import (
    CHECKPOINT_FRACTIONS, select_anchor_indices, summarize,
)


def cohort(delta_path=(0., -2., 1., 2., 3.)):
    rows = []
    n = len(delta_path)-1
    for life in range(16):
        snapshots = [dict(completed_fit_games=k,
            cumulative_updates=k*(1000 if life == 0 else 1), cumulative_fit_steps=k*(1001 if life == 0 else 2),
            metrics=dict(mse=10.+delta, mae=3.+delta/2., bias=-3.+delta/10.))
            for k, delta in enumerate(delta_path)]
        probes = [dict(completed_fit_games=k,
            metrics=dict(action_disagreement=.5*k/n, validation_utility_delta=.2*k/n,
                frozen_reference_regret=.3, mc_reference_regret=.3-.2*k/n,
                predicted_frozen_action_margin=.1))
            for k in sorted({ceil(f*n) for f in CHECKPOINT_FRACTIONS})]
        rows.append(dict(lifecycle=life, parent=life%4, fit_game_count=n,
                         snapshots=snapshots, h2_probes=probes))
    return rows


def test_anchor_selection_uses_only_heldout_nonwinning_chronology_and_covers_ends():
    boards = np.zeros((20, 16), dtype=np.int32)
    boards[[8, 13, 17, 19], 0] = 11
    dataset = dict(afterstates=boards, ends=np.array([4, 14, 20]), fit_game_count=1)
    anchors = select_anchor_indices(dataset)
    assert anchors.dtype == np.int64
    assert anchors.tolist() == [4, 6, 9, 12, 14, 15, 16, 18]
    # Arbitrary changes to labels cannot choose anchors or borrow fitting states.
    dataset.update(rewards=np.linspace(100., -100., 20), terminal_codes=np.array([-1, 1, -1]))
    assert np.array_equal(anchors, select_anchor_indices(dataset))
    dataset['rewards'] *= -1
    dataset['terminal_codes'] *= -1
    assert np.array_equal(anchors, select_anchor_indices(dataset))


def test_short_heldout_games_have_unique_anchors_including_the_only_position():
    dataset = dict(afterstates=np.zeros((10, 16), dtype=np.int32),
                   ends=np.array([4, 5, 7, 10]), fit_game_count=1)
    assert select_anchor_indices(dataset).tolist() == [4, 5, 6, 7, 8, 9]


def test_final_primary_does_not_select_the_best_prefix_or_weight_by_update_counts():
    rows = cohort()
    rows[0]['snapshots'][-1]['metrics']['mse'] = 42.
    result = summarize(rows, draws=50)
    primary = result['primary_final_anchor_mse_delta']
    assert result['primary_endpoint'] == 'FINAL_ANCHOR_MC_MINUS_FROZEN_MSE'
    assert primary == result['final_anchor_contrasts']['mse']
    assert primary['mean'] == (32.+15*3.)/16
    assert primary['improved_equal_worse'] == [0, 0, 16]
    assert primary['adverse_lifecycles'] == list(range(16))
    assert primary['lifecycle_values']['0'] == 32.
    assert result['anchor_checkpoints'][1]['delta_from_frozen']['mse'] == -2.
    assert len(result['by_lifecycle'][0]['anchor_trajectory']) == 5


def test_crossings_are_strict_and_final_positive_run_is_not_monotonic_worsening():
    rows = cohort((0., 2., -1., 4., 3.))
    # A zero at the final prefix ends the positive run.
    rows[1] = cohort((0., 2., -1., 4., 0.))[1]
    rows[2] = cohort((0., -1., 0., -2., -1.))[2]
    result = summarize(rows, draws=30)
    lives = result['by_lifecycle']
    assert lives[0]['first_above_baseline_game'] == 1
    assert lives[0]['final_above_baseline_run_start_game'] == 3
    assert lives[1]['first_above_baseline_game'] == 1
    assert lives[1]['final_above_baseline_run_start_game'] is None
    assert lives[2]['first_above_baseline_game'] is None
    assert lives[2]['final_above_baseline_run_start_game'] is None


def test_preset_prefixes_use_ceil_per_life_and_keep_signed_h2_quality():
    rows = cohort()
    rows[0] = cohort((0., 1., 2., 3., 4., 5.))[0]
    rows[0]['h2_probes'][-1]['metrics']['validation_utility_delta'] = -2.
    result = summarize(rows, draws=50)
    assert [point['fraction'] for point in result['anchor_checkpoints']] == list(CHECKPOINT_FRACTIONS)
    assert result['anchor_checkpoints'][1]['lifecycle_fit_games']['0'] == 2
    assert result['anchor_checkpoints'][1]['lifecycle_fit_games']['1'] == 1
    utility = result['final_h2_diagnostics']['validation_utility_delta']
    assert utility['mean'] == pytest.approx((-2.+15*.2)/16)
    assert utility['improved_equal_worse'] == [15, 0, 1]
    assert utility['adverse_lifecycles'] == [0]
    assert 'improved_equal_worse' not in result['final_h2_diagnostics']['action_disagreement']
    assert 'improved_equal_worse' not in result['final_anchor_contrasts']['bias']
    assert result['h2_checkpoints'][-1]['metrics']['frozen_reference_regret'] == .3


def test_wholelife_bootstrap_keeps_four_parent_means_and_all_negative_deltas():
    rows = cohort((0., -1., -2., -3., -4.))
    for row in rows:
        row['snapshots'][-1]['metrics']['mse'] = 10.-(row['parent']+1.)
    result = summarize(rows, draws=80)
    primary = result['primary_final_anchor_mse_delta']
    assert primary['mean'] == -2.5
    # Within each parent all four lives agree, so stratified resampling is exact.
    assert primary['ci95'] == [-2.5, -2.5]
    assert primary['parent_means'] == {str(p): -(p+1.) for p in range(4)}
    assert primary['improved_equal_worse'] == [16, 0, 0]
    assert primary['interval_scope'] == 'CONDITIONAL_ON_FOUR_FROZEN_PARENTS'
    assert result['bootstrap_seed'] == 28900001


@pytest.mark.parametrize('error', ['missing_prefix', 'wrong_h2_prefix', 'parent'])
def test_missing_real_prefix_or_frozen_roster_cannot_produce_crossing_statistics(error):
    rows = cohort()
    if error == 'missing_prefix':
        rows[0]['snapshots'].pop(2)
    elif error == 'wrong_h2_prefix':
        rows[0]['h2_probes'][1]['completed_fit_games'] = 0
    else:
        rows[0]['parent'] = 1
    with pytest.raises(ValueError):
        summarize(rows, draws=30)


def test_analysis_is_read_only_and_reproducible():
    rows = cohort()
    before = deepcopy(rows)
    first = summarize(rows, draws=50)
    assert rows == before
    assert first == summarize(rows, draws=50)
