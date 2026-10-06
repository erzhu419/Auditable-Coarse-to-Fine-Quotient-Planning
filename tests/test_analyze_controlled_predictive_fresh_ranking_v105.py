"""Fresh acquisition accounting and six matched frozen-recipe comparisons."""
from copy import deepcopy
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


A = load('fresh_ranking_analysis_v105', ROOT / 'scripts/analyze_controlled_predictive_fresh_ranking_v105.py')
BASE = load('capacity_fixture_v105', ROOT / 'tests/test_analyze_controlled_predictive_capacity_ranking_v103.py')


def fixture():
    old = BASE.fixture()
    settings = dict(old['settings'], methods=list(A.METHODS), contrasts=[list(pair) for pair in A.CONTRASTS],
        lifecycles=[11, 12, 13, 14], allocations=[4], reference_block_size=16)
    run = dict(status='complete', settings=settings, lifecycles=[], actual_wall_seconds=1.)
    for index, life_id in enumerate(settings['lifecycles']):
        life = deepcopy(old['lifecycles'][index % 2])
        life['id'] = life_id
        life['allocations'] = [row for row in life['allocations'] if row['replicas'] == 4]
        allocation = life['allocations'][0]
        allocation['new_neural_model_fits'] = 4
        allocation['new_training_environment_transitions'] = allocation['inherited_training_environment_transitions']
        allocation['inherited_training_environment_transitions'] = 0
        allocation['model_metadata'] = {name: value for name, value in allocation['model_metadata'].items() if name in A.METHODS}
        for stage in allocation['construction']:
            data = stage['data']
            stage['acquisition'] = deepcopy(data['inherited_acquisition'])
            stage['acquisition'].update(life=life_id, seconds=.01, counts={})
            data['counts'] = deepcopy(data['inherited_v102_data_counts'])
            prefixes = data['inherited_feature_prefixes']
            data.update(new_model_work=prefixes['model_work'], new_planning_counts=prefixes['planning_counts'],
                new_feature_counts=prefixes['feature_counts'], new_prefix_outcomes=prefixes['outcomes'],
                model_prefix_trajectories=prefixes['trajectories'], model_prefix_roots=prefixes['roots'])
            stage['fit_logs'] = {}
            for hidden in (4, 16):
                fit = deepcopy(stage['fit_log'] if hidden == 4 else stage['frozen_fit_log'])
                fit.update(family=A.FAMILY, hidden=hidden, parameter_count=123 * hidden,
                    l2_coefficient=.001 / 1968, l2_reference_parameters=1968)
                fit['counts'] = dict(neural_model_fits=1, optimizer_steps=1000)
                fit['models'] = {A.FAMILY: fit['models'][A.FAMILY]}
                stage['fit_logs'][str(hidden)] = fit
        evaluation = life['evaluation']
        evaluation['methods'] = {name: value for name, value in evaluation['methods'].items() if name in A.METHODS}
        evaluation['model_metadata'] = allocation['model_metadata']
        for data in evaluation['methods'].values():
            for game in data['games']:
                game['seed'] += life_id * 10000
        validation = evaluation['validation']
        for record in validation['roots']:
            record['root'].update(life=life_id, source_seed=record['root']['source_seed'] + life_id * 10000)
            record['predictions'] = {name: value for name, value in record['predictions'].items() if name in A.METHODS}
            record.update(audit={'paired_fresh_streams': True}, seconds=.01)
        run['lifecycles'].append(life)
    return run


def test_fresh_source_branch_prefix_and_both_width_fits_are_charged_exactly_once():
    result = A.analyze_run(fixture())
    assert result['complete'] and result['primary_complete'], result['checks']
    cost = result['actual_executed_work']
    assert cost['new_training_environment_transitions'] == 16000
    assert cost['new_natural_transitions'] == 480 and cost['new_reference_transitions'] == 12800
    assert cost['newly_sampled_environment_transitions'] == 29280
    assert cost['new_neural_model_fits'] == 16 and cost['new_optimizer_steps'] == 16000
    assert cost['new_training_model_prefix_transitions'] == 320
    assert cost['new_deployment_model_prefix_transitions'] == 1600
    assert cost['new_model_prefix_transitions'] == 1920 and cost['new_selector_calls'] == 40
    assert sum(row['total_transitions'] for row in cost['training_cost_partition'].values()) == 16000


def test_loader_acquisition_alias_is_not_a_second_charge_or_historical_training():
    run = fixture()
    data = run['lifecycles'][0]['allocations'][0]['construction'][0]['data']
    data['inherited_acquisition']['source']['ground_work']['sampled_transitions'] = 999999
    result = A.analyze_run(run)
    assert result['complete']
    assert result['actual_executed_work']['new_training_environment_transitions'] == 16000
    assert result['actual_executed_work']['new_neural_model_fits'] == 16


def test_same_root_reference_and_natural_directions_are_reported_for_all_four_histories():
    run = fixture()
    narrow, wide = A.CURRENT
    for life in run['lifecycles']:
        evaluation = life['evaluation']
        for left, right in zip(evaluation['methods'][narrow]['games'], evaluation['methods'][wide]['games']):
            left.update(selected_option='SNAKE_4', score=right['score'] + 2048, utility=right['utility'] + 1.)
            right['selected_option'] = 'H2'
        for record in evaluation['validation']['roots']:
            for method, option in ((narrow, 'SNAKE_4'), (wide, 'H2')):
                event = record['predictions'][method]
                event['option'] = option
                event['predictions'] = {name: {'value': float(name == option and option != 'H2')} for name in A.OPTIONS}
    result = A.analyze_run(run)
    comparison = result['reference']['matched']['comparisons'][narrow + '_minus_' + wide]['reward']
    assert comparison['primary_estimable'] and len(comparison['lifecycles']) == 4
    assert comparison['direction_counts']['natural'] == dict(positive=4, negative=0, zero=0)
    assert comparison['direction_counts']['references']['pooled'] == dict(positive=4, negative=0, zero=0)
    assert comparison['primary']['natural_mean_utility_delta'] == 1.
    assert len(result['reference']['matched']['comparisons']) == 6


def test_censored_reference_keeps_fresh_training_and_evaluation_costs_without_primary_shrinkage():
    run = fixture()
    record = run['lifecycles'][0]['evaluation']['validation']['roots'][0]
    record.update(reference_complete=False, paired_reference={})
    record['terminal_log'].update(censored_root=True, outcomes={'LOST': 159, 'CUTOFF': 1})
    result = A.analyze_run(run)
    assert result['complete'] and not result['primary_complete']
    assert result['actual_executed_work']['newly_sampled_environment_transitions'] == 29280
    assert result['reference']['matched']['root_records'] == 8
    comparison = result['reference']['matched']['comparisons'][A.CURRENT[0] + '_minus_' + A.CURRENT[1]]['reward']
    assert comparison['primary'] is None and comparison['lifecycles'][0]['roots'] == 2
    assert comparison['lifecycles'][0]['paired_reference_roots'] == 1


def test_new_width_fits_keep_identical_data_gamma_and_penalty_without_hidden_work_mixups():
    run = fixture()
    stage = run['lifecycles'][0]['allocations'][0]['construction'][0]
    stage['fit_logs']['16']['uniform_gamma'] += 1
    stage['fit_logs']['4']['normalization_training_roots'] += 1
    game = run['lifecycles'][0]['evaluation']['methods'][A.CURRENT[0]]['games'][0]
    game['candidate_evaluation']['value_counts']['neural_hidden_activations'] = 80
    result = A.analyze_training(run)
    assert not result['checks']['both_widths_share_data_and_penalty']
    assert not result['checks']['whole_episode_isolation']
    assert not result['checks']['deployed_models_and_hidden_work_match']


def test_changed_reference_events_or_failed_audits_do_not_pass_as_frozen_choices():
    run = fixture()
    record = run['lifecycles'][0]['evaluation']['validation']['roots'][0]
    record['predictions'][A.CURRENT[0]]['step'] += 1
    record['audit']['paired_fresh_streams'] = False
    result = A.analyze_references(run)
    assert not result['checks']['deployed_reference_predictions_match']
    assert not result['checks']['reference_audits_pass']
