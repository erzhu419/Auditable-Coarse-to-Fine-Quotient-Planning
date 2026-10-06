"""Terminal-anchor accounting and the contribution beyond prefix-only decisions."""
from copy import deepcopy
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


A = load('terminal_anchor_analysis_v99', ROOT / 'scripts/analyze_controlled_predictive_terminal_anchor_v99.py')
BASE = load('coverage_fixture_v98', ROOT / 'tests/test_analyze_controlled_predictive_root_coverage_v98.py')


def gates(evaluation):
    records = {}
    for left, right in A.CONTRASTS:
        rows = []
        for new, old in zip(evaluation['methods'][left]['games'], evaluation['methods'][right]['games']):
            before, after = old['selected_option'] or 'H2', new['selected_option'] or 'H2'
            category = ('both_h2' if before == after == 'H2' else 'enabled' if before == 'H2' else
                'disabled' if after == 'H2' else 'same_fragment' if before == after else 'changed_fragment')
            rows.append(dict(seed=new['seed'], query='reward', replica=new['replica'],
                category=category, old_option=before, new_option=after))
        records[left + '_minus_' + right] = rows
    return records


def fixture():
    base = BASE.fixture()
    methods = ['H2_ONLY', 'PREFIX_ONLY_DIRECT'] + [f'R{r}_{w}_{f}_DIRECT{s}'
        for s in ('', '_FROZEN_HALF') for r in (8, 4) for w in ('PAIR', 'BOUNDARY')
        for f in ('MC', 'FQE', 'ANCHORED_FQE')]
    settings = dict(base['settings'], methods=methods, anchor_weight=.5,
        contrasts=[list(pair) for pair in A.CONTRASTS])
    run = dict(status='complete', settings=settings, lifecycles=[], allocations=[], actual_wall_seconds=2.)
    for prior in base['lifecycles']:
        old = prior['evaluation']
        evaluation = dict(methods={'H2_ONLY': deepcopy(old['methods']['H2_ONLY'])},
            wiring=deepcopy(old['wiring']), validation=deepcopy(old['validation']), model_metadata={})
        prefix = deepcopy(old['methods']['R4_BOUNDARY_FQE_DIRECT'])
        for game in prefix['games']:
            game['selector_checkpoint'] = None
            game['candidate_evaluation']['value_counts'] = {'prefix_only_zero_predictions': 8}
            game['planning_counts'].pop('candidate_paired_continuation_predictions')
            game['planning_counts']['candidate_prefix_only_zero_predictions'] = 8
        evaluation['methods']['PREFIX_ONLY_DIRECT'] = prefix
        for original, record in zip(old['validation']['roots'], evaluation['validation']['roots']):
            record['predictions'] = {'PREFIX_ONLY_DIRECT': deepcopy(original['predictions']['R4_BOUNDARY_FQE_DIRECT'])}
        allocations = []
        for original in prior['allocations']:
            allocation = dict(replicas=original['replicas'], construction=[], model_metadata={},
                new_tree_fits=original['new_tree_fits'], new_training_environment_transitions=0,
                inherited_training_environment_transitions=original['new_training_environment_transitions'],
                historical_v98_tree_fits=original['new_tree_fits'])
            r = original['replicas']
            for stage in original['construction']:
                acq, cutoff, budget = stage['acquisition'], stage['episode_cutoff'], stage['budget']
                data = dict(life=prior['id'], replicas=r, budget=acq['budget'], start_cursor=acq['start_cursor'],
                    next_cursor=acq['next_cursor'], episode_cutoff=cutoff, row_weight=1/32,
                    inherited_physical_transitions=acq['used_transitions'], inherited_source_work=acq['source']['ground_work'],
                    inherited_branch_work=acq['branches']['ground_work'], inherited_cost_partition=acq['cost_partition'],
                    root_rosters={'reward': {'training': acq['completed_roots'], 'heldout': []}},
                    counts=dict(acq['counts'], new_environment_transitions=0, tree_fits=0), seconds=.01)
                record = dict(budget=budget, episode_cutoff=cutoff, data=data, weighting=deepcopy(stage['weighting']),
                    inherited_acquisition=deepcopy(acq), cumulative_roots=stage['cumulative_roots'],
                    cumulative_rows=stage['cumulative_rows'], fit_logs={})
                suffix = '' if budget == settings['budgets'][-1] else '_FROZEN_HALF'
                for weight, old_family in (('PAIR', 'PAIR_FQE'), ('BOUNDARY', 'BOUNDARY_FQE')):
                    log = deepcopy(stage['fit_logs'][old_family])
                    log['ANCHORED_FQE'] = log.pop('PAIR_FQE')
                    log['ANCHORED_FQE']['anchor_weight'] = log['anchor_weight'] = .5
                    log['counts']['anchored_fqe_tree_fits'] = log['counts']['pair_fqe_tree_fits']
                    record['fit_logs'][weight] = log
                    for family in ('MC', 'FQE', 'ANCHORED_FQE'):
                        name = f'R{r}_{weight}_{family}_DIRECT{suffix}'
                        template = f'R{r}_{old_family}_DIRECT{suffix}' if family == 'FQE' else (
                            'R8_PAIR_FQE_DIRECT' if family == 'MC' else 'R4_PAIR_FQE_DIRECT')
                        evaluation['methods'][name] = deepcopy(old['methods'][template])
                        for game in evaluation['methods'][name]['games']:
                            game['selector_checkpoint'] = cutoff
                        for original_ref, reference in zip(old['validation']['roots'], evaluation['validation']['roots']):
                            reference['predictions'][name] = deepcopy(original_ref['predictions'][template])
                        allocation['model_metadata'][name] = dict(replicas=r, budget=budget, episode_cutoff=cutoff,
                            weighting='uniform' if weight == 'PAIR' else 'boundary_0.5',
                            family={'MC': 'PAIR_MC', 'FQE': 'PAIR_FQE', 'ANCHORED_FQE': 'ANCHORED_FQE'}[family],
                            source='v98' if family == 'FQE' else 'v99', path='saved.json')
                allocation['construction'].append(record)
            allocations.append(allocation)
            evaluation['model_metadata'].update(allocation['model_metadata'])
            run['allocations'].append(dict(life=prior['id'], **deepcopy(allocation)))
        evaluation['gate_changes'] = gates(evaluation)
        run['lifecycles'].append(dict(id=prior['id'], allocations=allocations, evaluation=evaluation))
    return run


def test_new_fits_and_prefix_work_do_not_duplicate_old_acquisition_or_fit_classes():
    result = A.analyze_run(fixture())
    assert result['complete'] and result['primary_complete']
    assert all(result['checks'].values())
    cost = result['actual_executed_work']
    assert cost['new_tree_fits'] == 48
    assert cost['new_mc_initialization_fits'] == 16 and cost['new_anchored_fqe_fits'] == 32
    assert cost['new_training_environment_transitions'] == 0
    assert cost['newly_sampled_environment_transitions'] == 1440
    assert cost['new_simulated_transitions'] == 4000
    assert cost['simulated_selector_calls'] == 100
    assert cost['simulated_value_counts']['prefix_only_zero_predictions'] == 32
    assert cost['simulated_value_counts']['paired_continuation_predictions'] == 768
    inherited = result['training']['inherited_work']
    assert sum(row['ground_work']['sampled_transitions'] for row in inherited.values()) == 16000
    assert result['training']['historical_v98_tree_fits'] == 48


def test_fixed_contrasts_and_actual_contribution_relative_to_prefix():
    result = A.analyze_natural(fixture())
    label = 'R4_PAIR_ANCHORED_FQE_DIRECT_minus_PREFIX_ONLY_DIRECT'
    assert len(result['comparisons']) == len(result['gate_decomposition']) == 36
    effect = result['comparisons'][label]['reward']
    assert effect['mean_score_delta'] == 10
    assert 'descriptive_lifecycle_uncertainty' not in effect
    attribution = result['gate_decomposition'][label]['reward']['primary_attribution']['score']
    assert attribution['new_or_changed_choice_comparator_contribution'] == 10
    assert attribution['cancelled_intervention_recovery_contribution'] == 0


def test_fixed_anchor_and_old_model_provenance_are_checked():
    run = fixture()
    life = run['lifecycles'][0]
    life['allocations'][0]['construction'][0]['fit_logs']['PAIR']['anchor_weight'] = .2
    life['evaluation']['model_metadata']['R8_PAIR_FQE_DIRECT']['source'] = 'v99'
    result = A.analyze_training(run)
    assert not result['checks']['fixed_terminal_anchor']
    assert not result['checks']['deployed_model_family_and_age_match']


def test_prefix_zero_work_is_not_a_learned_tail_prediction():
    run = fixture()
    game = run['lifecycles'][0]['evaluation']['methods']['PREFIX_ONLY_DIRECT']['games'][0]
    game['candidate_evaluation']['value_counts']['paired_continuation_predictions'] = 8
    result = A.analyze_simulation(run)
    assert not result['checks']['simulated_work_accounted']


def test_reference_cutoff_keeps_all_new_and_inherited_costs():
    run = fixture()
    record = run['lifecycles'][0]['evaluation']['validation']['roots'][0]
    record.update(reference_complete=False, paired_reference={})
    record['terminal_log'].update(censored_root=True, outcomes={'LOST': 9, 'CUTOFF': 1})
    result = A.analyze_run(run)
    assert result['complete'] and not result['primary_complete']
    assert result['actual_executed_work']['newly_sampled_environment_transitions'] == 1440
    assert result['actual_executed_work']['new_tree_fits'] == 48
    assert result['validation']['methods']['R4_PAIR_ANCHORED_FQE_DIRECT']['reward']['primary'] is None


def test_independent_reference_evaluates_mc_anchor_and_prefix_original_choices():
    result = A.analyze_validation(fixture())
    assert result['methods']['R4_PAIR_MC_DIRECT']['reward']['primary']['mean_utility_mse'] == 7.75
    assert result['methods']['R4_PAIR_ANCHORED_FQE_DIRECT']['reward']['primary']['mean_utility_mse'] == 1
    assert result['methods']['R4_PAIR_ANCHORED_FQE_DIRECT']['reward']['primary']['selected_reference_utility'] == 4
    assert result['methods']['PREFIX_ONLY_DIRECT']['reward']['primary']['selected_reference_utility'] == 0
