"""Objective comparisons preserve root groups, scalar semantics, and actual work."""
from copy import deepcopy
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


A = load('query_ranking_analysis_v100', ROOT / 'scripts/analyze_controlled_predictive_query_ranking_v100.py')
BASE = load('coverage_fixture_v100', ROOT / 'tests/test_analyze_controlled_predictive_root_coverage_v98.py')


def fixture():
    base = BASE.fixture()
    methods = ['H2_ONLY', 'PREFIX_ONLY_DIRECT'] + [f'R{r}_{f}_DIRECT{s}'
        for s in ('', '_FROZEN_HALF') for r in (8, 4) for f in A.FAMILIES]
    settings = dict(base['settings'], methods=methods, optimizer_steps=1000, hidden=16, feature_dim=121,
        contrasts=[list(pair) for pair in A.CONTRASTS])
    run = dict(status='complete', settings=settings, lifecycles=[], allocations=[], actual_wall_seconds=2.)
    for original in base['lifecycles']:
        old = original['evaluation']
        evaluation = dict(methods={'H2_ONLY': deepcopy(old['methods']['H2_ONLY'])},
            wiring=deepcopy(old['wiring']), validation=deepcopy(old['validation']), model_metadata={})
        for record in evaluation['validation']['roots']:
            record['predictions'] = {}
        for method in methods[1:]:
            prefix = method == 'PREFIX_ONLY_DIRECT'
            template = 'R4_BOUNDARY_FQE_DIRECT' if prefix else 'R4_PAIR_FQE_DIRECT' if 'RANK' in method else 'R8_PAIR_FQE_DIRECT'
            evaluation['methods'][method] = deepcopy(old['methods'][template])
            for game in evaluation['methods'][method]['games']:
                if prefix:
                    game['selector_checkpoint'] = None
                log = game['candidate_evaluation']
                log['feature_counts'] = {'candidate_features': 5}
                log['value_counts'] = {'prefix_only_decisions': 1} if prefix else {'neural_candidate_predictions': 5}
                game['planning_counts'].pop('candidate_paired_continuation_predictions')
                game['planning_counts'].update({'candidate_' + k: v for k, v in log['value_counts'].items()})
                game['planning_counts']['candidate_candidate_features'] = 5
            for before, record in zip(old['validation']['roots'], evaluation['validation']['roots']):
                event = deepcopy(before['predictions'][template])
                event['predictions'] = {option: {'value': A._utility(row['target'], A.QUERIES['reward'])}
                    for option, row in event['predictions'].items()}
                event['score_semantics'] = 'prefix_utility' if prefix else 'rank_score' if 'RANK' in method else 'utility_estimate'
                record['predictions'][method] = event
        allocations = []
        for prior in original['allocations']:
            replicas = prior['replicas']
            allocation = dict(replicas=replicas, construction=[], model_metadata={}, new_neural_model_fits=4,
                new_training_environment_transitions=0, inherited_training_environment_transitions=4000)
            for index, stage in enumerate(prior['construction']):
                acquisition, cutoff, budget = stage['acquisition'], stage['episode_cutoff'], stage['budget']
                data = dict(episode_cutoff=cutoff, start_cursor=acquisition['start_cursor'], next_cursor=acquisition['next_cursor'],
                    counts=dict(complete_roots=1, training_roots=1, heldout_roots=0, new_environment_transitions=0, tree_fits=0),
                    inherited_acquisition=deepcopy(acquisition), new_model_work={'synthetic_transitions': 40, 'spawn_uniform_draws': 80},
                    new_planning_counts={'model_uniform_draws': 160}, new_feature_counts={'candidate_features': 5},
                    new_prefix_outcomes={'ACTIVE': 10}, model_prefix_trajectories=10, model_prefix_roots=1, seconds=.01)
                fit = dict(checkpoint=cutoff, training_episodes={'reward': list(range(0, 2 * index + 1, 2))},
                    training_roots=index + 1, heldout_roots=0, normalization_training_roots=index + 1,
                    counts={'neural_model_fits': 2, 'optimizer_steps': 2000}, seconds=.02, models={})
                for family in A.FAMILIES:
                    fit['models'][family] = dict(counts={'neural_model_fits': 1, 'optimizer_steps': 1000,
                        'diagnostic_candidate_predictions': 5 * (index + 1)}, parameter_count=1968,
                        initial_loss=2., final_loss=1., final_gradient_norm=.01,
                        training={'roots': index + 1}, heldout={'roots': 0}, seconds=.01)
                    method = f'R{replicas}_{family}_DIRECT' + ('' if index else '_FROZEN_HALF')
                    allocation['model_metadata'][method] = dict(replicas=replicas, budget=budget,
                        episode_cutoff=cutoff, family=family, path='saved.json')
                    for game in evaluation['methods'][method]['games']:
                        game['selector_checkpoint'] = cutoff
                allocation['construction'].append(dict(budget=budget, episode_cutoff=cutoff, data=data,
                    fit_log=fit, cumulative_roots=stage['cumulative_roots'], cumulative_root_count=index + 1))
            allocations.append(allocation)
            evaluation['model_metadata'].update(allocation['model_metadata'])
            run['allocations'].append(dict(life=original['id'], **deepcopy(allocation)))
        evaluation['gate_changes'] = {}
        for left, right in A.CONTRASTS:
            records = []
            for new, old_game in zip(evaluation['methods'][left]['games'], evaluation['methods'][right]['games']):
                before, after = old_game['selected_option'] or 'H2', new['selected_option'] or 'H2'
                category = ('both_h2' if before == after == 'H2' else 'enabled' if before == 'H2' else
                    'disabled' if after == 'H2' else 'same_fragment' if before == after else 'changed_fragment')
                records.append(dict(seed=new['seed'], query='reward', replica=new['replica'],
                    category=category, old_option=before, new_option=after))
            evaluation['gate_changes'][left + '_minus_' + right] = records
        run['lifecycles'].append(dict(id=original['id'], allocations=allocations, evaluation=evaluation))
    return run


def test_shared_training_prefixes_new_fits_and_actor_duplicate_counters_are_counted_once():
    result = A.analyze_run(fixture())
    assert result['complete'] and result['primary_complete'], result['checks']
    cost = result['actual_executed_work']
    assert cost['new_neural_model_fits'] == 16 and cost['new_optimizer_steps'] == 16000
    assert cost['new_tree_fits'] == cost['new_training_environment_transitions'] == 0
    assert cost['newly_sampled_environment_transitions'] == 800
    assert cost['training_simulated_transitions'] == 320
    assert cost['deployed_simulated_transitions'] == 1440
    assert cost['new_simulated_transitions'] == 1760
    assert cost['simulated_selector_calls'] == 36
    assert cost['simulated_value_counts'] == {'prefix_only_decisions': 4, 'neural_candidate_predictions': 160}
    assert sum(row['ground_work']['sampled_transitions'] for row in result['training']['inherited_work'].values()) == 16000


def test_rank_error_is_scale_invariant_and_ties_are_not_false_certainty():
    reference = dict(zip(A.OPTIONS, (0., 1., 2., 3., 4.)))
    scores = {name: 10 * value + 20 for name, value in reference.items()}
    best = A.OPTIONS[-1]
    assert A.ranking_error(scores, reference, best)['pairwise_weighted_error'] == 0
    reverse = A.ranking_error({name: -value for name, value in scores.items()}, reference, A.OPTIONS[0])
    assert reverse['pairwise_weighted_error'] == 1 and reverse['selected_reference_regret'] == 4
    assert A.ranking_error(dict.fromkeys(A.OPTIONS, 0.), reference, best)['pairwise_weighted_error'] == .5
    assert A.ranking_error(scores, dict.fromkeys(A.OPTIONS, 0.), best)['pairwise_weighted_error'] == 0


def test_rank_has_no_calibrated_mse_and_reference_means_do_not_use_training_labels():
    result = A.analyze_validation(fixture())
    assert 'R4_PAIRWISE_RANK_DIRECT' not in result['calibrated_utility_errors']
    assert result['calibrated_utility_errors']['R4_UTILITY_MSE_DIRECT']['reward']['primary']['mean_utility_mse'] == 7.75
    assert result['methods']['R4_PAIRWISE_RANK_DIRECT']['reward']['primary']['selected_reference_utility'] == 4
    assert result['methods']['PREFIX_ONLY_DIRECT']['reward']['primary']['selected_reference_utility'] == 0


def test_reference_cutoff_retains_cost_and_fixed_cohort_is_not_silently_shrunk():
    run = fixture()
    record = run['lifecycles'][0]['evaluation']['validation']['roots'][0]
    record.update(reference_complete=False, paired_reference={})
    record['terminal_log'].update(censored_root=True, outcomes={'LOST': 9, 'CUTOFF': 1})
    result = A.analyze_run(run)
    assert result['complete'] and not result['primary_complete']
    assert result['actual_executed_work']['newly_sampled_environment_transitions'] == 800
    assert result['actual_executed_work']['new_neural_model_fits'] == 16
    assert result['validation']['methods']['R4_PAIRWISE_RANK_DIRECT']['reward']['primary'] is None


def test_whole_root_normalization_and_deployed_budget_age_are_checked():
    run = fixture()
    life = run['lifecycles'][0]
    life['allocations'][0]['construction'][0]['fit_log']['normalization_training_roots'] += 1
    life['evaluation']['methods']['R8_PAIRWISE_RANK_DIRECT']['games'][0]['selector_checkpoint'] = 4000
    result = A.analyze_training(run)
    assert not result['checks']['whole_episode_isolation']
    assert not result['checks']['deployed_model_family_and_age_match']


def test_objective_contrasts_preserve_history_pairing_and_actual_prefix_contribution():
    run = fixture()
    result = A.analyze_natural(run)
    assert len(result['comparisons']) == len(result['gate_decomposition']) == 16
    label = 'R4_PAIRWISE_RANK_DIRECT_minus_PREFIX_ONLY_DIRECT'
    comparison = result['comparisons'][label]['reward']
    assert comparison['mean_score_delta'] == 10
    assert len(comparison['available_common_terminal']['lifecycles']) == 2
    assert 'descriptive_lifecycle_uncertainty' not in comparison
    attribution = result['gate_decomposition'][label]['reward']['primary_attribution']['score']
    assert attribution['new_or_changed_choice_comparator_contribution'] == 10
    assert attribution['cancelled_intervention_recovery_contribution'] == 0
    run['lifecycles'][0]['evaluation']['methods']['R4_PAIRWISE_RANK_DIRECT']['games'][0]['seed'] += 1
    assert not A.analyze_natural(run)['checks']['natural_streams_paired']
