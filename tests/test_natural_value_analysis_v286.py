"""Finite complete-game evidence fixtures; no environment calls."""
from copy import deepcopy

import pytest

from acfqp.science import natural_value_analysis_v286 as core


def cohort():
    rows = []
    for life in range(16):
        arms = {}
        for arm in core.ARMS:
            phases = {}
            for phase_index, phase in enumerate(core.PHASES):
                base = (1. if arm == 'FROZEN' else 2. if arm == 'ORDINARY_TD'
                        else 2.+dict(A=-2., B=4., A_prime=-8.)[phase])
                games = [dict(seed=28600000+100*life+16*phase_index+i,
                    utility=base+i-7.5, status='WON' if i == 0 else 'LOST', steps=i+1)
                    for i in range(16)]
                phases[phase] = dict(game_summaries=games, training_return=1e9)
            arms[arm] = dict(phases=phases, training_utility=-1e12)
        direct = deepcopy(arms['PERSISTENT_TD']['phases']['A_prime'])
        for game in direct['game_summaries']:
            game['utility'] -= 3.
        rows.append(dict(lifecycle=life, parent=life % 4, arms=arms,
            direct_final=direct, training_return=1e14))
    return rows


def test_three_phase_means_use_complete_games_and_keep_all_adverse_lives():
    inputs = cohort()
    original = deepcopy(inputs)
    summary = core.summarize(inputs, draws=3)
    assert inputs == original
    assert summary['primary_contrast'] == 'PERSISTENT_TD_minus_ORDINARY_TD'
    primary = summary['paired_contrasts'][summary['primary_contrast']]
    assert primary['mean'] == -2. and primary['ci95'] == [-2., -2.]
    assert primary['phases']['A']['mean'] == -2.
    assert primary['phases']['B']['mean'] == 4.
    assert primary['phases']['A_prime']['mean'] == -8.
    assert primary['improved_equal_worse'] == [0, 0, 16]
    assert primary['adverse_lifecycles'] == list(range(16))
    assert primary['lifecycle_deltas'] == {str(life): -2. for life in range(16)}
    assert summary['arms']['PERSISTENT_TD']['mean_lifecycle_utility'] == 0.
    assert summary['paired_contrasts']['PERSISTENT_TD_minus_FROZEN']['mean'] == -1.
    assert summary['paired_contrasts']['ORDINARY_TD_minus_FROZEN']['mean'] == 1.
    assert summary['complete_game_endpoints']


def test_long_game_or_long_phase_does_not_receive_extra_outcome_weight():
    rows = cohort()
    for life in rows:
        for game in life['arms']['PERSISTENT_TD']['phases']['B']['game_summaries']:
            game['steps'] *= 100000
        life['arms']['PERSISTENT_TD']['phases']['A']['game_summaries'][0]['steps'] = 1_000_000
    summary = core.summarize(rows, draws=2)
    assert summary['paired_contrasts']['PERSISTENT_TD_minus_ORDINARY_TD']['mean'] == -2.
    assert summary['arms']['PERSISTENT_TD']['phases']['B']['mean_game_utility'] == 6.
    assert summary['arms']['PERSISTENT_TD']['phases']['B']['steps'] == 16*136*100000


def test_final_same_snapshot_planner_comparison_and_outcome_counts():
    summary = core.summarize(cohort(), draws=2)
    planner = summary['planner_contribution']
    assert planner['contrast'] == 'PERSISTENT_TD_H2_minus_DIRECT' and planner['phase'] == 'A_prime'
    assert planner['mean'] == 3. and planner['ci95'] == [3., 3.]
    for arm in summary['arms'].values():
        assert arm['games'] == 768 and arm['wins'] == 48 and arm['losses'] == 720
        assert arm['cutoffs'] == 0 and arm['steps'] == 16*3*136
    assert summary['direct_final']['games'] == 256
    assert summary['direct_final']['wins'] == 16
    assert summary['direct_final']['losses'] == 240
    rows = cohort()
    rows[0]['direct_final']['game_summaries'][0]['status'] = 'CUTOFF'
    cutoff = core.summarize(rows, draws=2)
    assert cutoff['direct_final']['cutoffs'] == 1
    assert not cutoff['complete_game_endpoints']
    assert cutoff['direct_final']['games'] == 256


def test_whole_lifecycle_bootstrap_keeps_four_fixed_parents(monkeypatch):
    calls = []
    class WithinParentRng:
        def __init__(self, seed):
            assert seed == 28600001
        def choices(self, values, k):
            assert k == 4 and len({int(value) % 4 for value in values}) == 1
            calls.append(list(values))
            return [values[0]]*k
    monkeypatch.setattr(core.random, 'Random', WithinParentRng)
    records = [dict(lifecycle=life, parent=life % 4) for life in range(16)]
    result = core._bootstrap(records, list(map(float, range(16))), 3)
    assert len(calls) == 12
    assert result['mean'] == 7.5 and result['ci95'] == [1.5, 1.5]
    assert result['parent_mean_deltas'] == {'0': 6., '1': 7., '2': 8., '3': 9.}
    assert result['interval_scope'] == 'CONDITIONAL_ON_FOUR_FROZEN_PARENTS'


def test_unmatched_or_missing_game_cannot_be_called_a_paired_complete_checkpoint():
    rows = cohort()
    rows[0]['arms']['ORDINARY_TD']['phases']['A']['game_summaries'][0]['seed'] += 1_000_000
    with pytest.raises(ValueError, match='same sixteen distinct seeds'):
        core.summarize(rows, draws=2)
    rows = cohort()
    rows[0]['direct_final']['game_summaries'][0]['seed'] += 1_000_000
    with pytest.raises(ValueError, match='final DIRECT must pair'):
        core.summarize(rows, draws=2)
    rows = cohort()
    rows[0]['arms']['PERSISTENT_TD']['phases']['B']['game_summaries'].pop()
    with pytest.raises(ValueError, match='sixteen evaluation games'):
        core.summarize(rows, draws=2)
