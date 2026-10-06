"""Finite roster, structure and budget checks without natural game sampling."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from scripts import analyze_controlled_predictive_program_planning_v140 as analysis
from acfqp.science.controlled_predictive_policy_programs_v140 import fit_programs, randomize_programs

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    before = request.session.testsfailed
    yield
    path = ROOT/'reports/controlled_predictive_program_planning_v140.analysis_checks.json'
    record = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    record['attempts'].append(dict(failures=request.session.testsfailed-before,
        tests_run=sum(Path(str(item.path)).resolve() == Path(__file__).resolve() for item in request.session.items),
        environment_samples=0, model_samples=0,
        scope='finite full roster, paired history means, censored returns, tree structure and explicit budget accounting'))
    path.write_text(json.dumps(record, indent=2)+'\n')


def rows():
    result = {}
    for life in analysis.LIVES:
        for query in analysis.QUERIES:
            for method in analysis.METHODS:
                for replica in range(analysis.REPLICAS):
                    benefit = life+1 if method.startswith('LEARNED') else 0
                    result[(life, query, method, replica)] = dict(result=dict(
                        status='LOST', utility=10*life+replica+benefit, score=4, steps=1))
    return result


def test_all_queries_methods_and_histories_pair_inside_each_lifecycle():
    indexed = rows(); output = analysis.full_game_comparison(indexed, {key: True for key in indexed})
    assert len(indexed) == 512 and output['complete']
    assert set(output['methods']) == set(analysis.METHODS)
    for comparison in output['comparisons'].values():
        for cell in comparison.values():
            assert cell['mean'] == 2.5 and cell['positive'] == 4
            assert cell['lifecycles'][2]['replica_deltas'] == [3]*8


def test_missing_game_and_cutoff_keep_roster_and_suppress_affected_returns():
    indexed = rows(); valid = {key: True for key in indexed}
    indexed[(0, 'risk1', 'LEARNED64', 0)]['result']['status'] = 'CUTOFF'
    del indexed[(3, 'risk8', 'RANDOM8', 7)]
    output = analysis.full_game_comparison(indexed, valid)
    assert not output['complete']
    assert output['methods']['LEARNED64']['risk1']['lifecycles'][0]['games'] == 8
    assert output['methods']['LEARNED64']['risk1']['lifecycles'][0]['statuses']['CUTOFF'] == 1
    assert output['comparisons']['LEARNED64-H2']['risk1']['mean'] is None
    assert output['comparisons']['LEARNED8-RANDOM8']['risk8']['mean'] is None
    assert output['comparisons']['LEARNED64-H2']['risk8']['mean'] == 2.5


def test_invalid_complete_game_is_not_dropped_or_used_as_a_return():
    indexed = rows(); valid = {key: True for key in indexed}; valid[(2, 'risk8', 'H2', 0)] = False
    output = analysis.full_game_comparison(indexed, valid)
    assert output['methods']['H2']['risk8']['lifecycles'][2]['games'] == 8
    assert output['comparisons']['LEARNED64-H2']['risk8']['mean'] is None


def test_environment_and_simulation_seeds_have_separate_reproducible_rosters():
    outer = {analysis.outer_seed(life, replica) for life in analysis.LIVES for replica in range(analysis.REPLICAS)}
    model = {analysis.model_seed(life, replica, step) for life in analysis.LIVES for replica in range(analysis.REPLICAS) for step in range(2000)}
    assert len(outer) == 32 and len(model) == 64000 and not outer & model


def examples():
    return [dict(board=([1, 2]+[0]*14 if i%2 else [3, 2, 1, 1]*4),
        previous_action='DOWN', action='UP' if i%2 else 'RIGHT') for i in range(64)]


def test_fitted_histograms_and_randomized_predicates_are_independently_reconciled():
    sample = examples(); learned = fit_programs(sample); random = randomize_programs(learned, 100)
    assert all(analysis.tree_checks(learned, random, sample, 100).values())
    random['trees'][0][0][0] = -1
    assert not analysis.tree_checks(learned, random, sample, 100)['random_preserves_structure']


def test_changed_label_metadata_and_missing_fit_work_are_detected():
    sample = examples(); learned = fit_programs(sample); random = randomize_programs(learned, 100)
    learned['metadata']['node_action_counts'][0][0][0] += 1
    assert not analysis.tree_checks(learned, random, sample, 100)['fitted_node_histograms']
    learned = fit_programs(sample); random = randomize_programs(learned, 100)
    learned['work']['split_predicate_reads'] -= 1
    assert not analysis.tree_checks(learned, random, sample, 100)['tree_training_accounting']


def budget_fixture(direct=False):
    options = dict(DOWN=dict(afterstate=[0, 0]+[1, 2]*7,
        budget=0 if direct else 16, used=0 if direct else 7, rollouts=0 if direct else 1))
    program_swipes, trees = (4, 1) if direct else (7, 3)
    counts = dict(choose_calls=1, root_swipe_calls=4, root_legal_actions=1,
        program_swipe_calls=program_swipes, bootstrap_swipe_calls=0 if direct else 4,
        model_swipe_budget=4 if direct else 20, model_swipes_used=4 if direct else 11,
        learned_swipe_calls=4 if direct else 11, legal_swipes=1 if direct else 7,
        learned_terminal_checks=2 if direct else 9, value_predictions=0 if direct else 3,
        line_table_lookups=0 if direct else 16, table_lookups=0 if direct else 96,
        line_lookup_calls=4*program_swipes, line_hits=4*program_swipes,
        composition_line_gathers=4*program_swipes, composition_line_scatters=4*program_swipes,
        line_bound_output_cells=16*program_swipes, line_zero_mask_rank_reads=16*program_swipes,
        tree_calls=trees, tree_order_reads=4*trees, feature_board_reads=16*trees,
        feature_neighbor_comparisons=24*trees, feature_predicate_values=14*trees,
        tree_predicate_checks=trees, direct_choose_calls=int(direct))
    if not direct:
        counts.update(rollouts_started=1, rollout_actions=3, model_sampled_transitions=4,
            simulation_uniform_draws=8, simulation_rng_initializations=1, spawn_empty_cell_reads=64,
            spawn_board_writes=4, rollout_reward_additions=3, rollout_mean_additions=1,
            leaf_choose_calls=1, root_empty_cell_reads=16)
    return counts, options


@pytest.mark.parametrize('direct', [True, False])
def test_actual_work_can_be_below_cap_and_direct_has_no_bootstrap(direct):
    counts, options = budget_fixture(direct)
    assert all(analysis.program_counts_valid(counts, options, direct).values())


def test_budget_overrun_and_unreported_model_draws_are_detected():
    counts, options = budget_fixture()
    options['DOWN']['used'] = 17
    assert not analysis.program_counts_valid(counts, options, False)['model_budget']
    counts, options = budget_fixture(); counts['simulation_uniform_draws'] -= 1
    assert not analysis.program_counts_valid(counts, options, False)['simulation_costs']


def test_missing_local_programs_and_eval_fitting_are_failures():
    counts, options = budget_fixture(); counts['line_misses'] = 1
    assert not analysis.program_counts_valid(counts, options, False)['program_costs']
    counts, options = budget_fixture(); counts['compiled_programs'] = 1
    assert not analysis.program_counts_valid(counts, options, False)['no_evaluation_fitting']


def test_training_board_comes_from_actual_first_action_and_spawn():
    window = dict(root=[1, 1]+[0]*14, actions=['LEFT', 'DOWN'], spawns=[dict(cell=1, rank=1)], expected=dict(scores=[4, 0]))
    board, action = analysis.training_example(window)
    assert board == [2, 1]+[0]*14 and action == 'DOWN'
    window['spawns'][0]['cell'] = 0
    with pytest.raises(ValueError): analysis.training_example(window)
