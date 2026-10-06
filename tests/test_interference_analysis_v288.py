"""Unequal action counts, protected targets and fixed-parent uncertainty."""
import pytest

from acfqp.science import interference_analysis_v288 as core

ACTION_COUNTS = (2, 3, 2, 4)
ACTIONS = ('DOWN', 'LEFT', 'RIGHT', 'UP')


def cohort(value=None, protected=False):
    records = []
    for life in range(16):
        groups = {}
        for group_index, group in enumerate(core.GROUPS):
            queries = [(board, action) for board, count in enumerate(ACTION_COUNTS)
                       for action in range(count)]
            pairs = []
            for donor_board, donor_action in queries:
                for target_board, target_action in queries:
                    delta = (value if value is not None else life+100*group_index
                             +donor_board+target_board+donor_action+target_action)
                    noise, kernel = .5, 1
                    if protected and donor_board == 0 and donor_board != target_board:
                        delta, noise, kernel = 0., 0., 0
                    pairs.append(dict(donor_state_id=f'{group}/{donor_board}',
                        donor_action=ACTIONS[donor_action], target_state_id=f'{group}/{target_board}',
                        target_action=ACTIONS[target_action], kernel=kernel,
                        baseline_validation_mse=10., mean_label_delta_mse=float(delta),
                        single_label_mean_delta_mse=delta+noise, empirical_noise_penalty=noise))
            groups[group] = dict(pairs=pairs)
        records.append(dict(lifecycle=life, parent=life % 4, groups=groups))
    return records


def test_categories_use_query_identity_not_shared_board_alone():
    pairs = cohort()[0]['groups']['uniform']['pairs']
    counts = {category: sum(core.pair_category(pair) == category for pair in pairs)
              for category in core.CATEGORIES}
    assert counts == dict(SELF=11, SAME_BOARD_OTHER_ACTION=22, OTHER_BOARD=88)


def test_actions_boards_then_lifecycles_receive_equal_weight():
    rows = cohort()
    result = core.summarize(rows, draws=2)
    for group_index, group in enumerate(core.GROUPS):
        for category in core.CATEGORIES:
            mean = result['groups'][group]['categories'][category]['metrics']['mean_label_delta_mse']
            # Mean board index = 1.5, mean within-board action index = .875.
            assert mean == pytest.approx(7.5+100*group_index+2*1.5+2*.875)
            for life in result['by_lifecycle']:
                own = life['groups'][group]['categories'][category]['metrics']['mean_label_delta_mse']
                assert own == pytest.approx(life['lifecycle']+100*group_index+4.75)
    other_pairs = [pair for pair in rows[0]['groups']['uniform']['pairs']
                   if core.pair_category(pair) == 'OTHER_BOARD']
    assert sum(pair['mean_label_delta_mse'] for pair in other_pairs)/len(other_pairs) != 4.75
    assert result['primary_endpoint'] == dict(group='uniform', category='OTHER_BOARD',
                                            metric='mean_label_delta_mse')


def test_zero_kernel_pairs_remain_in_primary_with_their_baseline_losses():
    result = core.summarize(cohort(value=4., protected=True), draws=2)
    other = result['groups']['uniform']['categories']['OTHER_BOARD']
    assert other['metrics']['mean_label_delta_mse'] == 3.  # protected donor board has one-quarter weight
    assert other['metrics']['baseline_validation_mse'] == 10.
    assert other['metrics']['mean_label_validation_mse'] == 13.
    assert other['metrics']['zero_kernel_fraction'] == .25
    assert other['zero_kernel_pairs'] == 16*18 and other['pairs'] == 16*88
    assert other['zero_kernel_pairs']/other['pairs'] != .25


def test_signed_improvements_and_noise_identity_survive_all_averages():
    result = core.summarize(cohort(value=-2.), draws=3)
    for group in result['groups'].values():
        for category in group['categories'].values():
            metrics = category['metrics']
            assert metrics['mean_label_delta_mse'] == -2.
            assert metrics['single_label_mean_delta_mse'] == -1.5
            assert metrics['single_label_mean_delta_mse']-metrics['mean_label_delta_mse'] == metrics['empirical_noise_penalty']
            diagnostic = category['paired_diagnostics']['mean_label_delta_mse']
            assert diagnostic['mean'] == -2. and diagnostic['ci95'] == [-2., -2.]
            assert diagnostic['improved_equal_worse'] == [16, 0, 0]
            assert diagnostic['adverse_lifecycles'] == []
            noise = category['paired_diagnostics']['empirical_noise_penalty']
            assert noise['mean'] == .5 and noise['adverse_lifecycles'] == list(range(16))


def test_bootstrap_keeps_whole_lifecycle_and_fixed_parent_composition(monkeypatch):
    calls = []
    class FixedParents:
        def __init__(self, seed):
            assert seed == 28800001
        def choices(self, values, k):
            assert k == 4 and len({int(value) % 4 for value in values}) == 1
            calls.append(list(values))
            return [values[0]]*k
    monkeypatch.setattr(core.random, 'Random', FixedParents)
    rows = [dict(lifecycle=life, parent=life % 4) for life in range(16)]
    diagnostic = core._bootstrap(rows, list(map(float, range(16))), 3)
    assert len(calls) == 12 and diagnostic['mean'] == 7.5
    assert diagnostic['ci95'] == [1.5, 1.5]
    assert diagnostic['parent_mean_deltas'] == {'0': 6., '1': 7., '2': 8., '3': 9.}
    assert diagnostic['improved_equal_worse'] == [0, 1, 15]
    assert diagnostic['adverse_lifecycles'] == list(range(1, 16))
    assert diagnostic['interval_scope'] == 'CONDITIONAL_ON_FOUR_FROZEN_PARENTS'
