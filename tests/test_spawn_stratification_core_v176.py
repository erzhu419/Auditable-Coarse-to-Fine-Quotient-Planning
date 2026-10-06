"""Pure support, allocation and conditional-block variance counterexamples."""
from collections import defaultdict
from copy import deepcopy
from fractions import Fraction
from math import sqrt

import pytest

from acfqp.science import controlled_predictive_spawn_stratification_v176 as core


def batches(kind='reduction'):
    values = [-7., -5., -3., -1., 1., 3., 5., 7.]
    result = []
    for method in core.METHODS:
        for cohort in core.COHORTS:
            for life in core.LIVES:
                for block, value in enumerate(values):
                    if kind == 'equal' or method == 'IID':
                        vector = [value, 0., 0.]
                    elif kind == 'full_vector':
                        value /= 10
                        vector = [value, value/2, -value/2]
                    else:
                        vector = [0., 0., 0.]
                    result.append(dict(method=method, block=block, root_id=f'{cohort}:{life}:root', cohort=cohort,
                        life=life, components=vector, physical_branches=16,
                        environment_samples=100 if method == 'STRAT' else 120))
    return result


def test_joint_uniform_cell_support_preserves_both_native_spawn_marginals_and_shared_rank():
    tree, one = [1, 13], [0, 7, 15]
    support = core.joint_support(tree, one)
    assert len(support) == 8  # Four union intervals, each with two shared ranks.
    assert [row['stratum'] for row in support] == list(range(8))
    assert sum(row['probability'] for row in support) == pytest.approx(1.)
    marginals = defaultdict(float)
    for row in support:
        assert row['upper'] > row['lower'] and row['probability'] > 0
        marginals['TREE', row['tree_cell'], row['rank']] += row['probability']
        marginals['ONE', row['one_cell'], row['rank']] += row['probability']
    for mode, cells in (('TREE', tree), ('ONE', one)):
        for cell in cells:
            assert marginals[mode, cell, 1] == pytest.approx(.9/len(cells))
            assert marginals[mode, cell, 2] == pytest.approx(.1/len(cells))
    assert {(row['tree_cell'], row['one_cell']) for row in support} == {(1, 0), (1, 7), (13, 7), (13, 15)}


def test_equal_fraction_endpoints_merge_and_equal_size_lists_are_index_coupled():
    support = core.joint_support([0, 1, 2], [5, 6, 7, 8, 9, 10])
    assert len(support) == 12
    for index, row in enumerate(support[::2]):
        assert [row['lower'], row['upper']] == pytest.approx([index/6, (index+1)/6])
    equal = core.joint_support([1, 9], [5, 15])
    assert len(equal) == 4
    assert {(row['tree_cell'], row['one_cell']) for row in equal} == {(1, 5), (9, 15)}
    with pytest.raises(ValueError, match='nonterminal actions'):
        core.joint_support([], [1])


def test_probability_only_allocation_matches_budget_minimum_and_does_not_fit_outcomes():
    support = core.joint_support([0], [15])
    counts = core.allocation(support)
    assert counts == {0: 6, 1: 2}
    assert sum(counts.values()) == 4*len(support) and min(counts.values()) >= 2
    assert counts[0] > counts[1]
    noisy = deepcopy(support)
    for row in noisy:
        row['observed_variance'] = 100000. if row['rank'] == 2 else 0.
    assert core.allocation(noisy) == counts


def test_greedy_integer_allocation_has_no_improving_one_pair_transfer_and_true_probability_ties():
    support = core.joint_support([0, 15], [1, 2, 3, 4, 5, 6, 7])
    allocated = core.allocation(support)
    assert len(support) == 16 and sum(allocated.values()) == 64
    assert [allocated[row['stratum']] for row in support if row['rank'] == 2] == [2]*8
    assert [allocated[row['stratum']] for row in support if row['rank'] == 1] == [7, 7, 7, 3, 3, 7, 7, 7]
    probabilities = {row['stratum']: Fraction(row['probability']).limit_denominator(2560) for row in support}
    objective = sum(probabilities[index]**2/allocated[index] for index in allocated)
    for donor in allocated:
        if allocated[donor] <= 2:
            continue
        for recipient in allocated:
            if recipient == donor:
                continue
            changed = dict(allocated); changed[donor] -= 1; changed[recipient] += 1
            assert sum(probabilities[index]**2/changed[index] for index in changed) >= objective


def test_primary_variance_uses_eight_board_means_within_each_independent_block():
    summary = core.analyze_batches(batches())
    assert summary['complete'] and summary['roots'] == summary['blocks'] == 8
    strat, iid = (summary['methods'][method] for method in core.METHODS)
    assert iid['metrics']['utility']['mean'] == strat['metrics']['utility']['mean'] == 0.
    assert iid['metrics']['utility']['block_estimate_variance'] == 24.
    assert iid['metrics']['utility']['mean_estimate_variance'] == 3.
    assert strat['metrics']['utility']['block_estimate_variance'] == 0.
    comparison = summary['comparison']['metrics']['utility']
    assert comparison['variance_ratio'] == 0.
    assert comparison['block_variance_difference'] == -24.
    # Paired leave-one-block-out variance differences have SE 16/sqrt(3).
    assert comparison['variance_difference_jackknife_se'] == pytest.approx(16/sqrt(3))
    assert comparison['variance_difference_jackknife_ci95'] == pytest.approx([-24-1.96*16/sqrt(3), -24+1.96*16/sqrt(3)])
    assert comparison['variance_difference_jackknife_ci95'][1] < 0.
    assert len(strat['per_root']) == 8 and len(strat['per_history']) == 4
    assert summary['work']['batch_rows_indexed'] == 128


def test_jackknife_preserves_pairing_instead_of_adding_two_variance_uncertainties():
    summary = core.analyze_batches(batches('equal'))
    assert summary['complete']
    stat = summary['comparison']['metrics']['utility']
    assert stat['variance_ratio'] == 1.
    assert stat['block_variance_difference'] == stat['variance_difference_jackknife_se'] == 0.
    assert stat['variance_difference_jackknife_ci95'] == [0., 0.]
    assert summary['methods']['IID']['metrics']['utility']['block_estimate_variance'] > 0.


def test_utility_variance_comes_from_whole_vectors_including_component_covariance():
    summary = core.analyze_batches(batches('full_vector'))
    assert summary['complete']
    stat = summary['methods']['STRAT']['metrics']
    assert stat['utility']['block_estimate_variance'] == 0.
    assert all(stat[metric]['block_estimate_variance'] > 0. for metric in ('reward', 'failure', 'success'))
    assert sum(stat[metric]['block_estimate_variance'] for metric in ('reward', 'failure', 'success')) > 0.


def test_matched_physical_branches_retain_different_actual_transition_costs_and_secondary_product():
    summary = core.analyze_batches(batches())
    strat, iid = (summary['methods'][method] for method in core.METHODS)
    assert strat['mean_per_block_physical_branches'] == iid['mean_per_block_physical_branches'] == 128
    assert strat['mean_per_block_environment_samples'] == 800
    assert iid['mean_per_block_environment_samples'] == 960
    assert strat['total_physical_branches'] == iid['total_physical_branches'] == 1024
    assert iid['total_environment_samples'] == 7680
    assert iid['metrics']['utility']['block_variance_environment_cost_product'] == 24*960
    assert all(row['physical_branches'] == 128 and row['environment_samples'] == 960 for row in iid['per_block'])


@pytest.mark.parametrize('fault', ['missing', 'duplicate', 'foreign_block', 'history_mismatch', 'partial_vector', 'budget_mismatch', 'missing_cost'])
def test_partial_or_unbound_batches_stop_instead_of_reporting_sampler_variance(fault):
    rows = batches()
    if fault == 'missing':
        rows.pop()
    elif fault == 'duplicate':
        rows.append(deepcopy(rows[0]))
    elif fault == 'foreign_block':
        rows[0]['block'] = 8
    elif fault == 'history_mismatch':
        rows[0]['life'] = 1
    elif fault == 'partial_vector':
        rows[0]['components'].pop()
    elif fault == 'budget_mismatch':
        rows[0]['physical_branches'] += 2
    else:
        rows[0]['environment_samples'] = 0
    summary = core.analyze_batches(rows)
    assert not summary['complete'] and summary['issues']
    assert summary['methods'] == summary['comparison'] == {}


def test_zero_iid_variance_is_reported_as_undefined_ratio_not_infinity():
    rows = batches()
    for row in rows:
        if row['method'] == 'IID':
            row['components'] = [0., 0., 0.]
    summary = core.analyze_batches(rows)
    assert summary['complete']
    assert summary['comparison']['metrics']['utility']['variance_ratio'] is None
    assert summary['comparison']['metrics']['utility']['variance_difference_jackknife_ci95'] == [0., 0.]
