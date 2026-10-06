"""Three ordinal objectives, retained feature costs, and independent suffix blocks."""
from copy import deepcopy
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


A = load('replica_ranking_analysis_v102', ROOT / 'scripts/analyze_controlled_predictive_replica_ranking_v102.py')
BASE = load('query_ranking_fixture_v102', ROOT / 'tests/test_analyze_controlled_predictive_query_ranking_v100.py')


def fixture():
    run = BASE.fixture()
    mapping = {'H2_ONLY': 'H2_ONLY', 'PREFIX_ONLY_DIRECT': 'PREFIX_ONLY_DIRECT'}
    for suffix in ('', '_FROZEN_HALF'):
        for r in (8, 4):
            for family in A.FAMILIES:
                prior = 'PAIRWISE_RANK' if family == 'MEAN_SIGN' else 'UTILITY_MSE'
                mapping[f'R{r}_{family}_DIRECT{suffix}'] = f'R{r}_{prior}_DIRECT{suffix}'
    run['settings'].update(methods=list(mapping), contrasts=[list(pair) for pair in A.CONTRASTS], reference_replicas=32)
    run['allocations'] = []
    for life in run['lifecycles']:
        evaluation = life['evaluation']
        evaluation['methods'] = {name: deepcopy(evaluation['methods'][prior]) for name, prior in mapping.items()}
        for record in evaluation['validation']['roots']:
            record['predictions'] = {name: deepcopy(record['predictions'][prior])
                for name, prior in mapping.items() if name != 'H2_ONLY'}
            for name, event in record['predictions'].items():
                event['score_semantics'] = 'prefix_utility' if name == 'PREFIX_ONLY_DIRECT' else 'rank_score'
            record['paired_reference'] = {option: vectors * 16 for option, vectors in record['paired_reference'].items()}
            log = record['terminal_log']
            log['trajectories'] *= 16
            for field in ('ground_work', 'planning_counts', 'outcomes'):
                log[field] = {key: value * 16 for key, value in log[field].items()}
        evaluation['model_metadata'] = {}
        for allocation in life['allocations']:
            r = allocation['replicas']
            allocation['new_neural_model_fits'] = 6
            metadata = allocation['model_metadata']
            allocation['model_metadata'] = {}
            for method, prior in mapping.items():
                if not method.startswith(f'R{r}_'):
                    continue
                row = deepcopy(metadata[prior])
                row['family'] = next(family for family in A.FAMILIES if method.startswith(f'R{r}_{family}_DIRECT'))
                allocation['model_metadata'][method] = row
            evaluation['model_metadata'].update(allocation['model_metadata'])
            for stage in allocation['construction']:
                stage['baseline_equivalence'] = True
                data, fit = stage['data'], stage['fit_log']
                data.update(replicas=r, max_mean_utility_difference=0.)
                data['counts'].update(paired_replica_rows=r * data['counts']['complete_roots'],
                    mean_roots_verified=data['counts']['complete_roots'], new_synthetic_transitions=0,
                    neural_model_fits=0, neural_candidate_predictions=0, model_prefix_trajectories=0)
                data['inherited_feature_prefixes'] = dict(model_work=data.pop('new_model_work'),
                    planning_counts=data.pop('new_planning_counts'), feature_counts=data.pop('new_feature_counts'),
                    outcomes=data.pop('new_prefix_outcomes'), trajectories=data.pop('model_prefix_trajectories'),
                    roots=data.pop('model_prefix_roots'))
                fit['models'] = {family: deepcopy(fit['models']['PAIRWISE_RANK']) for family in A.FAMILIES}
                fit['counts'] = dict(neural_model_fits=3, optimizer_steps=3000)
                fit.update(uniform_gamma=1., conflict_mass_training_roots=fit['training_roots'], conflict_pairs=3,
                    total_training_pairs=10 * fit['training_roots'], training_replica_rows=r * fit['training_roots'])
            run['allocations'].append(dict(life=life['id'], **deepcopy(allocation)))
        evaluation['gate_changes'] = {}
        for left, right in A.CONTRASTS:
            rows = []
            for new, old in zip(evaluation['methods'][left]['games'], evaluation['methods'][right]['games']):
                before, after = old['selected_option'] or 'H2', new['selected_option'] or 'H2'
                category = ('both_h2' if before == after == 'H2' else 'enabled' if before == 'H2' else
                    'disabled' if after == 'H2' else 'same_fragment' if before == after else 'changed_fragment')
                rows.append(dict(seed=new['seed'], query=new['query'], replica=new['replica'], category=category,
                    old_option=before, new_option=after))
            evaluation['gate_changes'][left + '_minus_' + right] = rows
    return run


def test_new_fits_and_deployment_work_are_separate_from_retained_training_prefixes():
    result = A.analyze_run(fixture())
    assert result['complete'] and result['primary_complete'], result['checks']
    costs = result['actual_executed_work']
    assert costs['new_neural_model_fits'] == 24 and costs['new_optimizer_steps'] == 24000
    assert costs['training_simulated_transitions'] == costs['new_training_environment_transitions'] == 0
    assert costs['new_simulated_transitions'] == 2080 and costs['simulated_selector_calls'] == 52
    assert costs['inherited_training_prefixes']['model_work']['synthetic_transitions'] == 320
    assert costs['newly_sampled_environment_transitions'] == 6960
    assert costs['new_reference_transitions'] == 6400


def test_all_learned_scores_are_ordinal_and_a_b_blocks_use_independent_halves():
    run = fixture()
    before = A.analyze_validation(run)
    assert set(before['calibrated_utility_errors']) == {'PREFIX_ONLY_DIRECT'}
    for life in run['lifecycles']:
        for record in life['evaluation']['validation']['roots']:
            for vectors in record['paired_reference'].values():
                for index in range(16, 32):
                    vectors[index] = [vectors[index][0] + 10., *vectors[index][1:]]
    after = A.analyze_validation(run)
    method = 'R4_REPLICA_DIRECT'
    field = 'selected_reference_utility'
    original = before['methods'][method]['reward']['primary'][field]
    assert after['methods'][method]['reward']['primary'][field] == original + 5
    assert after['independent_blocks']['A']['methods'][method]['reward']['primary'][field] == original
    assert after['independent_blocks']['B']['methods'][method]['reward']['primary'][field] == original + 10
    event = run['lifecycles'][0]['evaluation']['validation']['roots'][0]['predictions'][method]
    event['score_semantics'] = 'utility_estimate'
    assert not A.analyze_validation(run)['checks']['rank_scores_not_utility_estimates']


def test_incomplete_reference_retains_cost_and_does_not_reduce_fixed_primary_roster():
    run = fixture()
    record = run['lifecycles'][0]['evaluation']['validation']['roots'][0]
    record.update(reference_complete=False, paired_reference={})
    record['terminal_log'].update(censored_root=True, outcomes={'LOST': 159, 'CUTOFF': 1})
    result = A.analyze_run(run)
    assert result['complete'] and not result['primary_complete']
    assert result['actual_executed_work']['newly_sampled_environment_transitions'] == 6960
    assert result['validation']['methods']['R4_REPLICA_DIRECT']['reward']['primary'] is None
    assert result['validation']['independent_blocks']['A']['methods']['R4_REPLICA_DIRECT']['reward']['primary'] is None


def test_uniform_coefficient_rosters_and_frozen_mean_sign_binding_are_checked():
    run = fixture()
    stage = run['lifecycles'][0]['allocations'][0]['construction'][0]
    stage['fit_log']['conflict_mass_training_roots'] += 1
    stage['baseline_equivalence'] = False
    result = A.analyze_training(run)
    assert not result['checks']['conflict_mass_from_training_roots']
    assert not result['checks']['mean_sign_matches_frozen_v100']
    stage['data']['counts']['new_synthetic_transitions'] = 1
    stage['data']['max_mean_utility_difference'] = .1
    result = A.analyze_training(run)
    assert not result['checks']['retained_features_reused_without_simulation']
    assert not result['checks']['replica_means_match_retained_labels']


def test_model_age_and_objective_rosters_match_the_frozen_twenty_four_contrasts():
    run = fixture()
    assert len(A.CONTRASTS) == len(set(A.CONTRASTS)) == 24
    assert len(A.analyze_natural(run)['comparisons']) == 24
    run['settings']['contrasts'].pop()
    life = run['lifecycles'][0]
    life['evaluation']['methods']['R4_UNIFORM_SHRINK_DIRECT']['games'][0]['selector_checkpoint'] += 1
    result = A.analyze_training(run)
    assert not result['checks']['primary_contrast_roster_matches']
    assert not result['checks']['deployed_model_family_and_age_match']


def test_heldout_and_future_episodes_cannot_be_declared_as_training_roots():
    run = fixture()
    stage = run['lifecycles'][0]['allocations'][0]['construction'][0]
    stage['fit_log']['training_episodes']['reward'].append(4)
    stage['fit_log']['normalization_training_roots'] += 1
    result = A.analyze_training(run)
    assert not result['checks']['whole_episode_isolation']
