"""Fixed-cohort labels, finite reference splits, and unique physical acquisition."""
from copy import deepcopy
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('heldout_order_analysis_v101',
    ROOT / 'scripts/analyze_controlled_predictive_heldout_order_v101.py')
A = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(A)


def fixture():
    roots, references = [], []
    for life in (9, 10):
        root = dict(id=f'life_{life}_reward_4', life=life, query='reward', episode=4, board=[0] * 16,
            prefix_utilities=[0., 1., 2., 3., 4.], allocations=[])
        for replicas in (8, 4):
            predictions = {}
            for family in A.FAMILIES:
                scores = [0., 1., 2., 3., 4.] if family == 'UTILITY_MSE' else [0., -1., -2., -3., -4.]
                predictions[family] = dict(scores=scores, option=A.OPTIONS[max(range(5), key=scores.__getitem__)],
                    score_semantics='rank_score' if family == 'PAIRWISE_RANK' else 'utility_estimate')
            root['allocations'].append(dict(replicas=replicas, old_utilities=[0., 1., 2., 3., 4.], predictions=predictions))
        roots.append(root)
        references.append(dict(root_id=root['id'], checks=dict.fromkeys(A.EXECUTION_CHECKS, True), seconds=.1,
            log=dict(trajectories=160, censored_root=False, ground_work={'sampled_transitions': 1600},
                planning_counts={'model_uniform_draws': 6400}, outcomes={'LOST': 160},
                pair_deltas={option: [[float(index), 0., 0.]] * 32 for index, option in enumerate(A.OPTIONS) if index})))
    return dict(status='complete', settings=dict(lifecycles=[9, 10], allocations=[8, 4], queries=['reward'],
        replicas=32, block_size=16), cohort=dict(roots=roots, log=dict(counts=dict.fromkeys(A.ZERO_NEW_WORK, 0))), references=references, actual_wall_seconds=1.)


def test_ten_pairs_ties_weighting_and_reference_stability_preserve_all_pairs():
    values = [0., 1., 2., 3., 4.]
    metric = A.pair_metrics([0.] * 5, values)
    assert metric['counts']['pairs'] == 10 and metric['pairwise_weighted_error'] == .5
    assert A.pair_metrics(values, [0.] * 5)['pairwise_weighted_error'] is None
    root = fixture()['cohort']['roots'][0]
    references = dict(A=values, B=[0., -1., 2., 3., 3.], pooled=[0., 0., 2., 3., 3.5])
    row, pairs = A.analyze_root(root, root['allocations'][0], references)
    assert len(pairs) == 10
    assert row['stability_counts'] == dict(all=10, stable=8, opposed=1, tied=1)
    assert pairs[0]['stability'] == 'opposed'
    assert pairs[-1]['stability'] == 'tied'


def test_reference_stable_original_and_model_errors_are_cross_classified():
    run = fixture()
    root = run['cohort']['roots'][0]
    root['allocations'][0]['old_utilities'] = [0., 1., 1., 3., -4.]
    row, pairs = A.analyze_root(root, root['allocations'][0], dict.fromkeys(A.REFERENCES, [0., 1., 2., 3., 4.]))
    rank = row['stable_cross']['PAIRWISE_RANK']
    assert rank == {'old_correct_model_opposite': 5, 'old_tie_model_opposite': 1, 'old_opposite_model_opposite': 4}
    assert len(pairs) == sum(rank.values()) == 10
    assert row['stable_cross_mass']['UTILITY_MSE']['old_opposite_model_correct'] == 10


def test_frozen_ordinal_scores_scale_without_mse_or_choice_changes():
    run = fixture()
    before = A.analyze_run(run)
    for root in run['cohort']['roots']:
        for allocation in root['allocations']:
            prediction = allocation['predictions']['PAIRWISE_RANK']
            prediction['scores'] = [17 * value for value in prediction['scores']]
    after = A.analyze_run(run)
    assert before['primary_complete'] and after['primary_complete']
    for reference in A.REFERENCES:
        left = before['across_lifecycles'][0]['primary']['metrics'][reference]
        right = after['across_lifecycles'][0]['primary']['metrics'][reference]
        assert left['PAIRWISE_RANK'] == right['PAIRWISE_RANK']
        assert 'mean_utility_mse' not in right['PAIRWISE_RANK']
        assert right['UTILITY_MSE']['mean_utility_mse'] == 0


def test_cross_history_means_do_not_weight_longer_history_by_root_count():
    run = fixture()
    first = run['cohort']['roots'][0]
    second = run['cohort']['roots'][1]
    for allocation in second['allocations']:
        allocation['predictions']['UTILITY_MSE'] = deepcopy(allocation['predictions']['PAIRWISE_RANK'])
        allocation['predictions']['UTILITY_MSE']['score_semantics'] = 'utility_estimate'
    extra = deepcopy(first)
    extra.update(id='life_9_reward_9', episode=9)
    run['cohort']['roots'].append(extra)
    extra_reference = deepcopy(run['references'][0])
    extra_reference['root_id'] = extra['id']
    run['references'].append(extra_reference)
    result = A.analyze_run(run)
    summary = result['across_lifecycles'][0]['primary']['metrics']['pooled']['UTILITY_MSE']
    assert summary['mean_root_weighted_error'] == .5
    assert summary['mean_selected_reference_utility'] == 2
    per_life = [group['primary']['metrics']['pooled']['UTILITY_MSE']['mean_root_weighted_error']
        for group in result['groups'] if group['replicas'] == 8]
    assert per_life == [0., 1.]


def test_missing_duplicate_and_censored_references_do_not_shrink_primary_cohort():
    run = fixture()
    missing = deepcopy(run)
    missing['references'].pop()
    assert not A.analyze_run(missing)['complete']
    duplicate = deepcopy(run)
    duplicate['references'].append(deepcopy(duplicate['references'][0]))
    assert not A.analyze_run(duplicate)['complete']
    censored = deepcopy(run)
    log = censored['references'][0]['log']
    log.update(censored_root=True, pair_deltas={}, outcomes={'LOST': 159, 'CUTOFF': 1})
    result = A.analyze_run(censored)
    assert result['complete'] and not result['primary_complete']
    assert result['cohort']['unique_roots'] == 2 and result['cohort']['allocated_root_records'] == 4
    assert result['actual_executed_work']['newly_sampled_environment_transitions'] == 3200
    assert result['across_lifecycles'][0]['primary'] is None
    assert result['cohort']['analyzed_allocated_pairs'] == 20
    split = deepcopy(run)
    split['references'][0]['log']['pair_deltas'][A.OPTIONS[1]].pop()
    result = A.analyze_run(split)
    assert not result['complete'] and not result['primary_complete']


def test_shared_allocation_roots_reuse_reference_cost_only_once():
    result = A.analyze_run(fixture())
    assert result['primary_complete']
    assert result['cohort'] == dict(unique_roots=2, allocated_root_records=4, shared_roots=2,
        complete_reference_roots=2, expected_allocated_pairs=40, analyzed_allocated_pairs=40,
        missing_or_censored_root_ids=[])
    cost = result['actual_executed_work']
    assert cost['reference_trajectories'] == 320 and cost['newly_sampled_environment_transitions'] == 3200
    assert cost['new_training_environment_transitions'] == cost['new_model_transitions'] == cost['new_model_fits'] == 0
