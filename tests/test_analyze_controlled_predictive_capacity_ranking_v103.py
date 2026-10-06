"""Width changes retain objective/root bindings and distinguish new from copied fits."""
from copy import deepcopy
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


A = load('capacity_ranking_analysis_v103', ROOT / 'scripts/analyze_controlled_predictive_capacity_ranking_v103.py')
BASE = load('replica_ranking_fixture_v103', ROOT / 'tests/test_analyze_controlled_predictive_replica_ranking_v102.py')


def fixture():
    run = BASE.fixture()
    mapping = {'H2_ONLY': 'H2_ONLY', 'PREFIX_ONLY_DIRECT': 'PREFIX_ONLY_DIRECT'}
    for suffix in ('', '_FROZEN_HALF'):
        for r in (8, 4):
            for hidden in (4, 16):
                for family in A.FAMILIES:
                    prior = 'MEAN_SIGN' if hidden == 4 and family == 'REPLICA' else family
                    mapping[f'R{r}_H{hidden}_{family}_DIRECT{suffix}'] = f'R{r}_{prior}_DIRECT{suffix}'
    run['settings'].update(methods=list(mapping), contrasts=[list(pair) for pair in A.CONTRASTS],
        hidden=4, widths=[4, 16], frozen_hidden=16, l2_coefficient=.001 / 1968, l2_reference_parameters=1968)
    run['allocations'] = []
    for life in run['lifecycles']:
        evaluation = life['evaluation']
        evaluation['methods'] = {name: deepcopy(evaluation['methods'][prior]) for name, prior in mapping.items()}
        for name, data in evaluation['methods'].items():
            if name in ('H2_ONLY', 'PREFIX_ONLY_DIRECT'):
                continue
            hidden = int(name.split('_')[1][1:])
            for game in data['games']:
                game['candidate_evaluation']['value_counts']['neural_hidden_activations'] = 5 * hidden
                game['planning_counts']['candidate_neural_hidden_activations'] = 5 * hidden
        for record in evaluation['validation']['roots']:
            record['predictions'] = {name: deepcopy(record['predictions'][prior])
                for name, prior in mapping.items() if name != 'H2_ONLY'}
        evaluation['model_metadata'] = {}
        for allocation in life['allocations']:
            r = allocation['replicas']
            metadata = allocation['model_metadata']
            allocation['model_metadata'] = {}
            for method, prior in mapping.items():
                if not method.startswith(f'R{r}_'):
                    continue
                row = deepcopy(metadata[prior])
                hidden = int(method.split('_')[1][1:])
                family = next(f for f in A.FAMILIES if method.startswith(f'R{r}_H{hidden}_{f}_DIRECT'))
                row.update(hidden=hidden, parameter_count=hidden * 123, family=family)
                allocation['model_metadata'][method] = row
            evaluation['model_metadata'].update(allocation['model_metadata'])
            for stage in allocation['construction']:
                data, fit = stage['data'], stage['fit_log']
                for model in fit['models'].values():
                    model['training'].update(pairwise_weighted_error=0., selected_empirical_regret=0.)
                    model['heldout'].update(pairwise_weighted_error=.6, selected_empirical_regret=.9)
                stage['frozen_fit_log'] = deepcopy(fit)
                fit.update(hidden=4, parameter_count=492, l2_coefficient=.001 / 1968, l2_reference_parameters=1968)
                for model in fit['models'].values():
                    model.update(hidden=4, parameter_count=492, l2_coefficient=.001 / 1968)
                    model['training'].update(pairwise_weighted_error=.1, selected_empirical_regret=.05)
                    model['heldout'].update(pairwise_weighted_error=.3, selected_empirical_regret=.4)
                stage.update(baseline_equivalence=dict.fromkeys(A.FAMILIES, True), frozen_baseline_count=3,
                    baseline_sources={family: f'frozen_{family}.json' for family in A.FAMILIES})
                data['inherited_v102_data_counts'] = deepcopy(data['counts'])
                data['counts'] = dict(roots_read=data['counts']['complete_roots'],
                    training_roots=data['counts']['training_roots'], heldout_roots=data['counts']['heldout_roots'],
                    mean_roots_verified=data['counts']['mean_roots_verified'], new_environment_transitions=0,
                    new_synthetic_transitions=0, neural_model_fits=0, neural_candidate_predictions=0,
                    model_prefix_trajectories=0)
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


def test_narrow_fits_and_loaded_wide_models_do_not_double_charge_training_work():
    result = A.analyze_run(fixture())
    assert result['complete'] and result['primary_complete'], result['checks']
    cost = result['actual_executed_work']
    assert cost['new_neural_model_fits'] == 24 and cost['new_optimizer_steps'] == 24000
    assert cost['frozen_baseline_models'] == 24
    assert cost['inherited_v102_fit_counts'] == dict(neural_model_fits=24, optimizer_steps=24000)
    assert cost['new_training_environment_transitions'] == cost['training_simulated_transitions'] == 0
    assert cost['new_simulated_transitions'] == 4000 and cost['simulated_selector_calls'] == 100
    assert cost['simulated_value_counts']['neural_hidden_activations'] == 4800
    assert cost['newly_sampled_environment_transitions'] == 7440
    assert cost['inherited_training_prefixes']['model_work']['synthetic_transitions'] == 320


def test_training_and_heldout_capacity_comparisons_use_matched_saved_diagnostics():
    result = A.analyze_training(fixture())
    rows = result['capacity_fit_comparisons']
    assert len(rows) == 24
    assert all(row['hidden4_parameter_count'] == 492 and row['hidden16_parameter_count'] == 1968 for row in rows)
    assert all(row['training']['pairwise_weighted_error']['delta'] == .1 for row in rows)
    assert all(row['heldout']['pairwise_weighted_error']['delta'] == -.3 for row in rows)
    run = fixture()
    stage = run['lifecycles'][0]['allocations'][0]['construction'][0]
    stage['frozen_fit_log']['uniform_gamma'] += 1
    assert not A.analyze_training(run)['checks']['capacity_parameter_penalty_matched']
    run = fixture()
    run['lifecycles'][0]['allocations'][0]['construction'][0]['fit_log']['l2_coefficient'] *= 4
    assert not A.analyze_training(run)['checks']['capacity_parameter_penalty_matched']


def test_actual_hidden_work_and_saved_model_width_must_match_the_method():
    run = fixture()
    method = 'R4_H4_REPLICA_DIRECT'
    life = run['lifecycles'][0]
    game = life['evaluation']['methods'][method]['games'][0]
    game['candidate_evaluation']['value_counts']['neural_hidden_activations'] = 80
    assert not A.analyze_training(run)['checks']['deployed_width_work_accounted']
    run = fixture()
    life = run['lifecycles'][0]
    life['evaluation']['model_metadata'][method]['hidden'] = 16
    assert not A.analyze_training(run)['checks']['deployed_model_family_and_age_match']
    run = fixture()
    stage = run['lifecycles'][0]['allocations'][0]['construction'][0]
    stage['baseline_equivalence']['REPLICA'] = False
    stage['frozen_baseline_count'] = 2
    result = A.analyze_training(run)
    assert not result['checks']['wide_models_match_frozen_v102']
    assert not result['checks']['frozen_baseline_work_accounted']


def test_all_twenty_six_methods_and_forty_contrasts_are_evaluated_without_extra_pairs():
    run = fixture()
    assert len(run['settings']['methods']) == 26 and len(A.CONTRASTS) == len(set(A.CONTRASTS)) == 40
    natural = A.analyze_natural(run)
    assert len(natural['methods']) == 26 and len(natural['comparisons']) == 40
    assert 'R4_H4_REPLICA_DIRECT_minus_R4_H16_REPLICA_DIRECT' in natural['comparisons']
    run['settings']['contrasts'].pop()
    assert not A.analyze_training(run)['checks']['primary_contrast_roster_matches']


def test_reference_blocks_preserve_ordinal_semantics_and_censored_cost():
    run = fixture()
    before = A.analyze_validation(run)
    assert set(before['calibrated_utility_errors']) == {'PREFIX_ONLY_DIRECT'}
    method = 'R4_H16_REPLICA_DIRECT'
    field = 'selected_reference_utility'
    for life in run['lifecycles']:
        for record in life['evaluation']['validation']['roots']:
            for vectors in record['paired_reference'].values():
                for index in range(16, 32):
                    vectors[index] = [vectors[index][0] + 10., *vectors[index][1:]]
    after = A.analyze_validation(run)
    original = before['methods'][method]['reward']['primary'][field]
    assert after['methods'][method]['reward']['primary'][field] == original + 5
    assert after['independent_blocks']['A']['methods'][method]['reward']['primary'][field] == original
    assert after['independent_blocks']['B']['methods'][method]['reward']['primary'][field] == original + 10
    record = run['lifecycles'][0]['evaluation']['validation']['roots'][0]
    record.update(reference_complete=False, paired_reference={})
    record['terminal_log'].update(censored_root=True, outcomes={'LOST': 159, 'CUTOFF': 1})
    result = A.analyze_run(run)
    assert result['complete'] and not result['primary_complete']
    assert result['actual_executed_work']['newly_sampled_environment_transitions'] == 7440
    assert result['validation']['methods'][method]['reward']['primary'] is None


def test_no_new_prefix_generation_or_training_heldout_leak_is_accepted():
    run = fixture()
    stage = run['lifecycles'][0]['allocations'][0]['construction'][0]
    stage['data']['counts']['new_synthetic_transitions'] = 1
    stage['fit_log']['training_episodes']['reward'].append(4)
    stage['fit_log']['conflict_mass_training_roots'] += 1
    result = A.analyze_training(run)
    assert not result['checks']['retained_features_reused_without_simulation']
    assert not result['checks']['whole_episode_isolation']
    assert not result['checks']['conflict_mass_from_training_roots']
