"""Update only the output head of the retained half-stage ranking representation."""
from collections import Counter
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'src'))
from acfqp.science.controlled_predictive_fragments_v83 import OPTIONS
from scripts.analyze_controlled_predictive_crossed_ranking_v106 import (
    matrix_summary, event_metrics, event_matches, mean, BLOCKS, FIELDS)
from scripts.analyze_controlled_predictive_natural_reference_v104 import reference_values
from scripts.analyze_controlled_predictive_fresh_ranking_v105 import METHODS as ORIGINAL_METHODS, CURRENT
from scripts.analyze_controlled_predictive_query_update_v108 import METHODS as OLD_METHODS

MODE = 'HEAD_ONLY'
NEW_METHODS = tuple(base + '_FROZEN_STATS_WARM_HEAD_ONLY' for base in CURRENT)
METHODS = OLD_METHODS + NEW_METHODS
CONTRASTS = tuple((base + '_FROZEN_STATS_WARM_HEAD_ONLY', right) for base in CURRENT
    for right in (base + '_FROZEN_STATS_WARM', base + '_FROZEN_HALF', 'H2_ONLY'))
ZERO_DATA = ('new_environment_transitions', 'new_synthetic_transitions', 'neural_model_fits',
             'neural_candidate_predictions', 'new_feature_vectors', 'model_prefix_trajectories')


def analyze_training(run):
    settings = run['settings']
    training = run['training']
    checks = dict(training_history_roster=len(training) == len(settings['training_lifecycles'])
        and {row['life'] for row in training} == set(settings['training_lifecycles']),
        full_data_and_half_statistics_bound=True, active_query_and_full_denominator_bound=True,
        paired_initializations_and_reset_adam=True, hidden_parameters_frozen_and_head_only_updated=True,
        new_fit_budget_and_diagnostics_accounted=True, deployed_update_metadata_bound=True)
    data_counts, fit_counts = Counter(), Counter()
    diagnostics, fit_seconds, data_seconds, fits = 0, 0., 0., []
    models = {(row['training_life'], row['method']): row['metadata'] for row in run['models']}
    for row in training:
        data, life = row['data_log'], row['life']
        data_counts.update(data['counts'])
        data_seconds += data['seconds']
        checks['full_data_and_half_statistics_bound'] &= (bool(data['checks']) and all(data['checks'].values())
            and all(data['counts'][key] == 0 for key in ZERO_DATA)
            and set(row['fit_logs']) == set(row['model_metadata']) == set(NEW_METHODS))
        for base in CURRENT:
            hidden = int(base.split('_')[1][1:])
            method = base + '_FROZEN_STATS_WARM_HEAD_ONLY'
            fit = row['fit_logs'][method]
            full, half = data['full'], data['half']
            checks['full_data_and_half_statistics_bound'] &= (
                bool(fit['checks']) and all(fit['checks'].values())
                and fit['checkpoint'] == data['full_cutoff'] and fit['training_episodes'] == full['training_episodes']
                and fit['training_roots'] == full['training_roots'] and fit['heldout_roots'] == full['heldout_roots']
                and fit['statistics_source_checkpoint'] == data['half_cutoff']
                and fit['statistics_training_episodes'] == half['training_episodes']
                and fit['normalization_training_roots'] == fit['conflict_mass_training_roots'] == half['training_roots']
                and fit['training_replica_rows'] == 4 * full['training_roots']
                and fit['total_training_pairs'] == 10 * full['training_roots'])
            steps = settings['optimizer_steps']
            active_roots = full['training_roots']
            queries = ['reward', 'risk_goal']
            checks['active_query_and_full_denominator_bound'] &= (
                fit['optimized_queries'] == queries and fit['active_training_episodes'] == full['training_episodes']
                and fit['active_training_roots'] == fit['full_loss_denominator_roots'] == active_roots
                and fit['data_loss_weight'] == 1.)
            checks['paired_initializations_and_reset_adam'] &= (fit['mode'] == MODE
                and fit['initialization'] == 'half_parameters'
                and fit['optimizer_state'] == 'reset_zero_moments' and fit['new_optimizer_steps'] == steps
                and fit['inherited_parameter_steps'] == steps and fit['parameter_lineage_steps'] == 2 * steps)
            model = fit['models']['UNIFORM_SHRINK']
            checks['hidden_parameters_frozen_and_head_only_updated'] &= (fit['checks']['frozen_hidden_parameters'] is True
                and all(value['updated_parameter_indices'] == [2] and value['trainable_parameter_count'] == hidden
                    and value['frozen_parameter_count'] == 122 * hidden for value in (fit, model))
                and model['gradient_norm_semantics'] == 'updated_parameters_only')
            checks['new_fit_budget_and_diagnostics_accounted'] &= (fit['family'] == 'UNIFORM_SHRINK'
                and fit['hidden'] == hidden and fit['parameter_count'] == model['parameter_count'] == 123 * hidden
                and fit['counts']['neural_model_fits'] == model['counts']['neural_model_fits'] == 1
                and fit['counts']['optimizer_steps'] == model['counts']['optimizer_steps'] == steps
                and fit['counts']['optimizer_root_passes'] == model['counts']['optimizer_root_passes'] == steps * active_roots
                and fit['counts']['optimizer_pair_passes'] == model['counts']['optimizer_pair_passes'] == 10 * steps * active_roots
                and fit['counts']['optimizer_parameter_updates'] == model['counts']['optimizer_parameter_updates'] == steps * hidden
                and model['counts']['diagnostic_candidate_predictions'] == 5 * full['records']
                and fit['l2_coefficient'] == settings['l2_coefficient']
                and fit['l2_reference_parameters'] == settings['l2_reference_parameters'])
            metadata = row['model_metadata'][method]
            checks['deployed_update_metadata_bound'] &= (models.get((life, method)) == metadata
                and metadata['hidden'] == hidden and metadata['mode'] == MODE and metadata['optimized_queries'] == queries
                and all(metadata[key] == fit[key] for key in ('parameter_count', 'trainable_parameter_count',
                    'frozen_parameter_count', 'updated_parameter_indices'))
                and metadata['budget'] == settings['budgets'][-1]
                and metadata['episode_cutoff'] == fit['checkpoint'] and metadata['family'] == fit['family'])
            fit_counts.update(fit['counts'])
            diagnostics += model['counts']['diagnostic_candidate_predictions']
            fit_seconds += fit['seconds']
            fits.append(dict(life=life, method=method, **fit))
    return dict(checks=checks, data_counts=dict(data_counts), fit_counts=dict(fit_counts),
        diagnostic_candidate_predictions=diagnostics, fits=fits, fit_seconds=fit_seconds, data_seconds=data_seconds)


def analyze_run(run):
    settings, roots = run['settings'], run['cohort']['roots']
    training, cohorts = settings['training_lifecycles'], settings['lifecycles']
    count, replicas = settings['validation_roots_per_query'], settings['reference_replicas']
    expected_roots = {(life, query, episode) for life in cohorts for query in settings['queries'] for episode in range(count)}
    root_ids = {root['root_id'] for root in roots}
    learned = METHODS[2:]
    decisions = {(row['root_id'], row['training_life'], row['method']): row['event'] for row in run['decisions']}
    expected_decisions = {(root_id, life, method) for root_id in root_ids for life in training for method in learned}
    expected_models = {(life, method) for life in training for method in learned}
    scores = run['scoring_log']
    checks = dict(run_terminal=run['status'] == 'complete',
        cached_baselines_and_cohort_exact=bool(run['runner_checks']) and all(run['runner_checks'].values())
            and bool(run['cohort']['log']['checks']) and all(run['cohort']['log']['checks'].values()),
        frozen_recipe_rosters=settings['methods'] == list(METHODS) and settings['contrasts'] == [list(pair) for pair in CONTRASTS]
            and run['inherited_model_methods'] == list(OLD_METHODS[2:])
            and len(set(training)) == len(training) == len(cohorts) and set(training) == set(cohorts),
        full_root_model_and_decision_rosters=len(root_ids) == len(roots) == len(expected_roots)
            and {(root['life'], root['query'], root['episode']) for root in roots} == expected_roots
            and len(run['models']) == len(expected_models)
            and {(row['training_life'], row['method']) for row in run['models']} == expected_models
            and len(run['decisions']) == len(decisions) == len(expected_decisions) and set(decisions) == expected_decisions,
        new_scoring_roster_and_work_accounted=True, frozen_original_diagonal_matches=True,
        fixed_reference_blocks=replicas == 32 and settings['reference_block_size'] == 16,
        inherited_reference_audits_pass=True, inherited_reference_rosters_and_costs=True, all_references_terminal=True)
    fit = analyze_training(run)
    checks.update(fit['checks'])
    work = dict(ground_work=Counter(), planning_counts=Counter(), outcomes=Counter(), trajectories=0, seconds=0.)
    metrics, missing = {}, []
    for root in roots:
        root_id, log = root['root_id'], root['reference_log']
        for name in ('ground_work', 'planning_counts', 'outcomes'):
            work[name].update(log[name])
        work['trajectories'] += log['trajectories']
        work['seconds'] += log['seconds']
        audit = root['reference_audit']
        valid_audit = bool(audit) and all(audit.values())
        checks['inherited_reference_audits_pass'] &= valid_audit
        terminal = not log['censored_root'] and set(log['outcomes']) <= {'WON', 'LOST'}
        delta_complete = set(log['pair_deltas']) == set(OPTIONS[1:]) and all(
            len(log['pair_deltas'][option]) == replicas and all(len(vector) == 3 for vector in log['pair_deltas'][option])
            for option in OPTIONS[1:])
        checks['all_references_terminal'] &= terminal and root['reference_complete']
        checks['inherited_reference_rosters_and_costs'] &= (log['trajectories'] == replicas * len(OPTIONS)
            and sum(log['outcomes'].values()) == log['trajectories']
            and log['planning_counts'].get('model_uniform_draws', 0) == 4 * log['ground_work'].get('sampled_transitions', 0)
            and (delta_complete if terminal else not log['pair_deltas']))
        for method in ORIGINAL_METHODS[2:]:
            event = decisions.get((root_id, root['life'], method))
            checks['frozen_original_diagonal_matches'] &= event is not None and event_matches(event, root['original_predictions'][method])
        if not (terminal and delta_complete and valid_audit and root['reference_complete']):
            missing.append(root_id)
            continue
        for block, utility in reference_values(log, root['query'], replicas).items():
            for method in METHODS:
                for life in training:
                    if method == 'H2_ONLY':
                        event = None
                    elif method == 'PREFIX_ONLY_DIRECT':
                        event = root['original_predictions'][method]
                    else:
                        event = decisions.get((root_id, life, method))
                        if event is None:
                            continue
                    metrics[root_id, life, method, block] = event_metrics(event, utility)
    for name in ('ground_work', 'planning_counts', 'outcomes'):
        work[name] = dict(work[name])

    def summarize(method, query, block, field, right=None):
        cells = []
        for train_life in training:
            row = []
            for cohort in cohorts:
                group = [root for root in roots if root['life'] == cohort and root['query'] == query]
                values = []
                for root in group:
                    value = metrics.get((root['root_id'], train_life, method, block), {}).get(field)
                    if right is not None:
                        other = metrics.get((root['root_id'], train_life, right, block), {}).get(field)
                        value = value - other if value is not None and other is not None else None
                    values.append(value)
                row.append(mean(values) if len(group) == count else None)
            cells.append(row)
        return matrix_summary(cells, training, cohorts)

    methods = {method: {query: {block: {field: summarize(method, query, block, field) for field in FIELDS}
        for block in BLOCKS} for query in settings['queries']} for method in METHODS}
    comparisons = {left + '_minus_' + right: {query: {block: dict(
        selected_utility_delta=summarize(left, query, block, 'selected_reference_utility', right),
        pairwise_weighted_error_delta=summarize(left, query, block, 'pairwise_weighted_error', right))
        for block in BLOCKS} for query in settings['queries']} for left, right in CONTRASTS}
    counts = scores['counts']
    new_models = [row for row in run['models'] if row['method'] in NEW_METHODS]
    new_decisions = [row for row in run['decisions'] if row['method'] in NEW_METHODS]
    checks['new_scoring_roster_and_work_accounted'] = (bool(scores['checks']) and all(scores['checks'].values())
        and run['inherited_decisions'] == len(roots) * len(training) * len(OLD_METHODS[2:])
        and len(new_decisions) + run['inherited_decisions'] == len(run['decisions'])
        and counts['model_root_scores'] == len(new_decisions) == len(new_models) * len(roots)
        and counts['neural_candidate_predictions'] == len(new_decisions) * len(OPTIONS)
        and counts['neural_hidden_activations'] == len(roots) * len(OPTIONS) * sum(row['metadata']['hidden'] for row in new_models)
        and all(counts[key] == 0 for key in ('neural_model_fits', 'optimizer_steps', 'new_environment_transitions',
            'new_synthetic_transitions', 'model_prefix_trajectories')))
    complete = all(value for name, value in checks.items() if name != 'all_references_terminal')
    data, fitting = fit['data_counts'], fit['fit_counts']
    return dict(schema='acfqp.frozen_head_analysis.v109', complete=complete,
        primary_complete=complete and checks['all_references_terminal'] and not missing, checks=checks,
        cohort=dict(unique_reference_roots=len(roots), inherited_reference_trajectories=work['trajectories'],
            inherited_model_root_decisions=run['inherited_decisions'], new_model_root_decisions=len(new_decisions),
            missing_or_censored_reference_roots=missing), methods=methods, comparisons=comparisons, training=fit,
        actual_executed_work=dict(newly_sampled_environment_transitions=data['new_environment_transitions'] + counts['new_environment_transitions'],
            new_model_prefix_transitions=data['new_synthetic_transitions'] + counts['new_synthetic_transitions'],
            new_neural_model_fits=fitting['neural_model_fits'] + data['neural_model_fits'] + counts['neural_model_fits'],
            new_optimizer_steps=fitting['optimizer_steps'] + counts['optimizer_steps'],
            new_optimizer_root_passes=fitting['optimizer_root_passes'],
            new_optimizer_pair_passes=fitting['optimizer_pair_passes'],
            new_optimizer_parameter_updates=fitting['optimizer_parameter_updates'],
            new_neural_candidate_predictions=counts['neural_candidate_predictions'],
            new_training_diagnostic_candidate_predictions=fit['diagnostic_candidate_predictions'],
            new_model_root_decisions=counts['model_root_scores'], scoring_counts=counts, data_counts=data,
            fitting_seconds=fit['fit_seconds'], data_seconds=fit['data_seconds'], scoring_seconds=scores['seconds'],
            actual_wall_seconds=run['actual_wall_seconds']), inherited_reference_work=work,
        inherited_cohort_extraction_work=run['cohort']['log'], inherited_v105_total_work=run['inherited_v105_work'],
        inherited_v106_total_work=run['inherited_v106_work'],
        inherited_v107_total_work=run['inherited_v107_work'],
        inherited_v108_total_work=run['inherited_v108_work'], joint_source=run['joint_source'],
        evidence_scope='Head-only updating holds the half-stage hidden weights and hidden biases exactly fixed, changing '
            'only the output vector. Total network capacity remains 492/1968 parameters; trainable parameters are 4/16. '
            'It retains both query contributions, the full-root denominator, full L2 including the constant frozen part, '
            'and half-stage normalization/gamma. Half parameters initialize the update, with reset Adam moments and '
            '1000 new steps. The final_gradient_norm describes the active head; final_full_gradient_norm also includes '
            'frozen parameters and is not a convergence failure criterion. Restricting updates also regularizes learning; '
            'this comparison alone cannot uniquely identify representation drift as a causal mechanism. '
            'Actual root/pair passes and head-parameter updates are charged. Half-parameter training is inherited work. '
            'Half statistics use actual first-batch membership, not a cutoff filter on the merged records. '
            'All six prespecified contrasts evaluate both queries against cached joint/full, half and H2 baselines. '
            'Each matrix cell equally averages its eight retained roots, with equal history weights on both axes. '
            'Pool32 is primary and A/B16 descriptive. The 64 retained reference roots are reused evidence, not new independent '
            'samples. Original cohort extraction and reference work are subsets of the separately inherited totals and are not '
            'charged again. New fitting, diagnostics and model scoring are separate costs; no new natural trajectories '
            'are inferred. Missing/censored roots retain costs and invalidate affected full matrices. No new scientific Gate.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    args = parser.parse_args()
    result = analyze_run(json.loads((args.directory / 'run.json').read_text()))
    (args.directory / 'analysis.json').write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps(dict(complete=result['complete'], primary_complete=result['primary_complete'],
        checks=result['checks'], actual_executed_work=result['actual_executed_work']), allow_nan=False))


if __name__ == '__main__':
    main()
