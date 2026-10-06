"""Fixed budget accounting, pilot effects, and independent reference contracts."""
from copy import deepcopy
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

A = load('root_coverage_analysis_v98', ROOT / 'scripts/analyze_controlled_predictive_root_coverage_v98.py')
BASE = load('boundary_analysis_fixture_v97', ROOT / 'tests/test_analyze_controlled_predictive_boundary_learning_v97.py')


def fixture():
    base = BASE.fixture()
    rename = dict(PAIR_MC_DIRECT='R8_PAIR_FQE_DIRECT', PAIR_FQE_DIRECT='R8_BOUNDARY_FQE_DIRECT',
        BOUNDARY_MC_DIRECT='R4_PAIR_FQE_DIRECT', BOUNDARY_FQE_DIRECT='R4_BOUNDARY_FQE_DIRECT')
    rename.update({name + '_FROZEN_6': value + '_FROZEN_HALF' for name, value in list(rename.items())})
    settings = dict(base['settings'], methods=['H2_ONLY'] + list(rename.values()),
        allocations=[8, 4], budgets=[2000, 4000], contrasts=[list(pair) for pair in A.CONTRASTS])
    run = dict(status='complete', settings=settings, lifecycles=[], allocations=[], actual_wall_seconds=2.)
    for prior in base['lifecycles']:
        evaluation = deepcopy(prior['checkpoints'][0])
        evaluation['methods'] = {rename.get(name, name): value for name, value in evaluation['methods'].items()}
        for record in evaluation['validation']['roots']:
            record['predictions'] = {rename[name]: value for name, value in record['predictions'].items()}
        evaluation['gate_changes'] = {}
        for left, right in A.CONTRASTS:
            records = []
            for new, old in zip(evaluation['methods'][left]['games'], evaluation['methods'][right]['games']):
                before, after = old['selected_option'] or 'H2', new['selected_option'] or 'H2'
                category = ('both_h2' if before == after == 'H2' else 'enabled' if before == 'H2' else
                    'disabled' if after == 'H2' else 'same_fragment' if before == after else 'changed_fragment')
                records.append(dict(seed=new['seed'], query='reward', replica=new['replica'],
                    category=category, old_option=before, new_option=after))
            evaluation['gate_changes'][left + '_minus_' + right] = records
        allocations = []
        evaluation['model_metadata'] = {}
        for replicas in settings['allocations']:
            stages, metadata = [], {}
            for index, budget in enumerate(settings['budgets']):
                episode, cursor, cutoff = 2 * index, 2 * (index + 1), 2 * (index + 1) + 1
                completed = dict(query='reward', episode=episode, board=[1, 0] * 8,
                    replicas=replicas, heldout=False, paired_rows=4)
                partition = dict(training=dict(source_transitions=100, branch_transitions=1200, total_transitions=1300),
                    heldout=dict(source_transitions=0, branch_transitions=0, total_transitions=0),
                    unincorporated=dict(source_transitions=100, branch_transitions=600, total_transitions=700))
                counts = dict(source_games=2, branch_trajectories=5 * replicas + 1,
                    source_transitions=200, branch_transitions=1800, complete_roots=1, training_roots=1,
                    heldout_roots=0, incomplete_roots=1, paired_rows=4)
                acquisition = dict(budget=2000, used_transitions=2000, unused_budget=0, budget_exhausted=True,
                    start_cursor=2 * index, next_cursor=cursor, episode_cutoff=cutoff,
                    source=dict(ground_work={'sampled_transitions': 200}, planning_counts={'model_uniform_draws': 800}, outcomes={'LOST': 2}),
                    branches=dict(ground_work={'sampled_transitions': 1800}, planning_counts={'model_uniform_draws': 7200},
                        outcomes={'LOST': 5 * replicas, 'CUTOFF': 1}), cost_partition=partition, counts=counts,
                    root_records=[dict(cursor=episode, complete_block=True, paired_rows=4),
                        dict(cursor=episode + 1, complete_block=False, paired_rows=0)],
                    completed_roots=[completed], queries={'reward': dict(counts)}, seconds=.01)
                episodes = list(range(0, episode + 1, 2))
                weighting = BASE.weighting(cutoff)
                weighting['eligible_episodes'] = {'reward': episodes}
                fit_logs = {}
                for family in ('PAIR_FQE', 'BOUNDARY_FQE'):
                    log = BASE.construction(cutoff)['fit_log']
                    log['training_episodes'] = {'reward': episodes}
                    log['heldout'] = dict(counts={}, queries={}, seconds=0.)
                    fit_logs[family] = log
                    method = f'R{replicas}_{family}_DIRECT' + ('' if index else '_FROZEN_HALF')
                    metadata[method] = dict(replicas=replicas, budget=budget, episode_cutoff=cutoff,
                        weighting='uniform' if family == 'PAIR_FQE' else 'boundary_0.5', path='saved.json')
                    for game in evaluation['methods'][method]['games']:
                        game['selector_checkpoint'] = cutoff
                stages.append(dict(budget=budget, episode_cutoff=cutoff, next_cursor=cursor, acquisition=acquisition,
                    weighting=weighting, fit_logs=fit_logs, cumulative_rows=4 * (index + 1),
                    cumulative_roots={'reward': dict(training=episodes, heldout=[])}))
            allocation = dict(replicas=replicas, construction=stages, model_metadata=metadata,
                new_tree_fits=12, new_training_environment_transitions=4000)
            allocations.append(allocation)
            evaluation['model_metadata'].update(metadata)
            run['allocations'].append(dict(life=prior['id'], **deepcopy(allocation)))
        run['lifecycles'].append(dict(id=prior['id'], allocations=allocations, evaluation=evaluation))
    return run


def test_fixed_budget_partial_roots_are_charged_and_duplicate_progress_is_not_counted():
    result = A.analyze_run(fixture())
    assert result['complete'] and result['primary_complete']
    assert all(result['checks'].values())
    cost = result['actual_executed_work']
    assert cost['new_training_environment_transitions'] == 16000
    assert cost['newly_sampled_environment_transitions'] == 16760
    assert cost['new_tree_fits'] == 48
    assert cost['new_mc_warm_start_fits'] == 16 and cost['new_fqe_fits'] == 32
    assert cost['new_simulated_transitions'] == 1280
    assert result['training']['cost_partition']['unincorporated']['total_transitions'] == 5600
    assert result['training']['work']['branches']['outcomes']['CUTOFF'] == 8


def test_pilot_retains_history_effects_without_two_se_efficacy_bands():
    run = fixture()
    for life, score in zip(run['lifecycles'], (100, 80)):
        for game in life['evaluation']['methods']['R8_PAIR_FQE_DIRECT']['games']:
            game.update(score=score, utility=score / 2048)
    result = A.analyze_natural(run)
    effect = result['comparisons']['R4_PAIR_FQE_DIRECT_minus_R8_PAIR_FQE_DIRECT']['reward']
    assert effect['mean_score_delta'] == 20
    assert len(effect['available_common_terminal']['lifecycles']) == 2
    assert 'descriptive_lifecycle_uncertainty' not in effect
    assert len(result['gate_decomposition']) == 16


def test_budget_and_whole_root_label_contract_breaks_are_detected():
    run = fixture()
    stage = run['lifecycles'][0]['allocations'][0]['construction'][0]
    stage['acquisition']['used_transitions'] -= 1
    stage['acquisition']['root_records'][1]['paired_rows'] = 1
    result = A.analyze_training(run)
    assert not result['checks']['acquisition_budgets_match']
    assert not result['checks']['discarded_roots_have_no_labels']


def test_budget_age_is_distinct_from_episode_cutoff_and_items_are_not_resumed():
    run = fixture()
    life = run['lifecycles'][0]
    life['evaluation']['methods']['R8_PAIR_FQE_DIRECT']['games'][0]['selector_checkpoint'] = 4000
    life['allocations'][0]['construction'][1]['acquisition']['start_cursor'] = 1
    result = A.analyze_training(run)
    assert not result['checks']['deployed_budget_and_episode_metadata_match']
    assert not result['checks']['acquisition_cursors_continue']


def test_independent_reference_cutoff_preserves_all_training_and_evaluation_costs():
    run = fixture()
    record = run['lifecycles'][0]['evaluation']['validation']['roots'][0]
    record.update(reference_complete=False, paired_reference={})
    record['terminal_log'].update(censored_root=True, outcomes={'LOST': 9, 'CUTOFF': 1})
    result = A.analyze_run(run)
    assert result['complete'] and not result['primary_complete']
    assert result['actual_executed_work']['newly_sampled_environment_transitions'] == 16760
    assert result['validation']['methods']['R4_BOUNDARY_FQE_DIRECT']['reward']['primary'] is None


def test_independent_prediction_error_and_paired_natural_seed_contract():
    run = fixture()
    reference = A.analyze_validation(run)
    assert reference['methods']['R8_PAIR_FQE_DIRECT']['reward']['primary']['mean_utility_mse'] == 7.75
    assert reference['methods']['R4_PAIR_FQE_DIRECT']['reward']['primary']['mean_utility_mse'] == 1
    assert reference['methods']['R4_BOUNDARY_FQE_DIRECT']['reward']['primary']['selected_reference_utility'] == 0
    run['lifecycles'][0]['evaluation']['methods']['R4_PAIR_FQE_DIRECT']['games'][0]['seed'] += 1
    result = A.analyze_natural(run)
    assert not result['checks']['natural_streams_paired']
