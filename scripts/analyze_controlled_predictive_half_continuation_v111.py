"""Separate additional records from additional optimization using retained half pools."""
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
    event_metrics, mean, BLOCKS, FIELDS)
from scripts.analyze_controlled_predictive_natural_reference_v104 import reference_values

from scripts.analyze_controlled_predictive_pooled_history_v110 import (
    WIDTHS, METHODS as OLD_METHODS, LEARNED as OLD_LEARNED, ZERO_DATA, fold_summary)

NEW_METHODS = tuple(f'POOLED_H{hidden}_HALF_CONTINUED' for hidden in WIDTHS)
METHODS = OLD_METHODS + NEW_METHODS
LEARNED = METHODS[1:]
CONTRASTS = tuple(pair for hidden in WIDTHS for pair in (
    (f'POOLED_H{hidden}_FULL', f'POOLED_H{hidden}_HALF_CONTINUED'),
    (f'POOLED_H{hidden}_HALF_CONTINUED', f'POOLED_H{hidden}_HALF'),
    (f'POOLED_H{hidden}_HALF_CONTINUED', 'H2_ONLY'),
    (f'POOLED_H{hidden}_FULL', f'POOLED_H{hidden}_HALF')))


def analyze_training(run):
    settings, bank = run['settings'], run['bank_log']
    lives, steps = settings['lifecycles'], settings['optimizer_steps']
    histories = {row['life']: row for row in bank['histories']}
    inherited = {fold['heldout_life']: fold for fold in run['inherited_folds']}
    checks = dict(source_bank_roster_and_work_bound=len(histories) == len(bank['histories']) == len(lives)
        and set(histories) == set(lives) and bool(bank['checks']) and all(bank['checks'].values()),
        excluded_history_fold_roster=len(run['folds']) == len(lives)
            and {fold['heldout_life'] for fold in run['folds']} == set(lives)
            and len(inherited) == len(run['inherited_folds']) == len(lives) and set(inherited) == set(lives),
        source_history_training_and_statistics_exclusion=True, actual_half_membership_and_statistics_bound=True,
        matched_start_and_new_steps_with_full=True, half_data_learning_rule_bound=True,
        new_fit_budget_and_diagnostics_accounted=True, deployed_model_metadata_bound=True,
        pooled_half_payload_reads_accounted=run['input_counts']['pooled_half_payload_files_read'] == len(lives) * len(WIDTHS))
    bank_counts = Counter()
    for log in bank['histories']:
        bank_counts.update(log['counts'])
        checks['source_bank_roster_and_work_bound'] &= (bool(log['checks']) and all(log['checks'].values())
            and all(log['counts'][key] == 0 for key in ZERO_DATA))
    checks['source_bank_roster_and_work_bound'] &= all(bank['counts'].get(key) == value for key, value in bank_counts.items())
    data_counts, fit_counts = Counter(), Counter()
    fit_seconds, data_seconds, fits = 0., 0., []
    metadata_index = {(row['heldout_life'], row['method']): row['metadata'] for row in run['models']}
    for fold in run['folds']:
        excluded, sources, data = fold['heldout_life'], fold['source_lives'], fold['data_log']
        original = inherited[excluded]
        wanted_sources = [life for life in lives if life != excluded]
        checks['source_history_training_and_statistics_exclusion'] &= (sources == wanted_sources
            and data['heldout_life'] == excluded and data['source_lives'] == original['source_lives'] == sources)
        checks['half_data_learning_rule_bound'] &= (bool(data['checks']) and all(data['checks'].values())
            and set(fold['fit_logs']) == set(fold['model_metadata']) == set(NEW_METHODS))
        data_counts.update(pooled_record_references=data['half']['records'] + data['full']['records'])
        data_seconds += data['seconds']
        half = data['half']
        for stage in ('half', 'full'):
            summary = data[stage]
            train, validation = summary['training_roster'], summary['heldout_roster']
            expected_train = [row for life in sources for row in bank['rosters'][str(life)][stage]['training_roster']]
            expected_validation = [row for life in sources for row in bank['rosters'][str(life)][stage]['heldout_roster']]
            checks['actual_half_membership_and_statistics_bound'] &= (summary == original['data_log'][stage]
                and train == expected_train and validation == expected_validation)
            checks['source_history_training_and_statistics_exclusion'] &= all(
                row[0] in sources and row[0] != excluded for row in train + validation)
        for hidden in WIDTHS:
            method = f'POOLED_H{hidden}_HALF_CONTINUED'
            fit = fold['fit_logs'][method]
            half_fit = original['fit_logs'][f'POOLED_H{hidden}_HALF']
            full_fit = original['fit_logs'][f'POOLED_H{hidden}_FULL']
            model = fit['models']['UNIFORM_SHRINK']
            statistics = fit['statistics_roster']
            checks['source_history_training_and_statistics_exclusion'] &= (
                fit['source_lives'] == sources and all(row[0] in sources and row[0] != excluded
                    for row in fit['training_roster'] + fit['heldout_roster'] + statistics))
            checks['actual_half_membership_and_statistics_bound'] &= (
                statistics == half_fit['statistics_roster'] == full_fit['statistics_roster'] == half['training_roster']
                and fit['normalization_training_roots'] == fit['conflict_mass_training_roots'] == half['training_roots']
                and fit['uniform_gamma'] == half_fit['uniform_gamma'] == full_fit['uniform_gamma'])
            checks['half_data_learning_rule_bound'] &= (bool(fit['checks']) and all(fit['checks'].values())
                and fit['stage'] == 'HALF_CONTINUED' and fit['checkpoint'] == settings['budgets'][0]
                and fit['training_roster'] == half_fit['training_roster'] == half['training_roster']
                and fit['heldout_roster'] == half_fit['heldout_roster'] == half['heldout_roster']
                and fit['training_roots'] == half['training_roots'] and fit['heldout_roots'] == half['heldout_roots']
                and fit['training_replica_rows'] == 4 * half['training_roots']
                and fit['total_training_pairs'] == 10 * half['training_roots']
                and fit['l2_coefficient'] == full_fit['l2_coefficient'] == settings['l2_coefficient']
                and fit['l2_reference_parameters'] == full_fit['l2_reference_parameters'] == settings['l2_reference_parameters'])
            checks['matched_start_and_new_steps_with_full'] &= (
                fit['initialization'] == full_fit['initialization'] == 'half_parameters'
                and fit['optimizer_state'] == full_fit['optimizer_state'] == 'reset_zero_moments'
                and fit['new_optimizer_steps'] == full_fit['new_optimizer_steps'] == steps
                and fit['inherited_parameter_steps'] == full_fit['inherited_parameter_steps'] == steps
                and fit['parameter_lineage_steps'] == full_fit['parameter_lineage_steps'] == 2 * steps)
            expected_counts = dict(neural_model_fits=1, optimizer_steps=steps,
                optimizer_root_passes=steps * half['training_roots'], optimizer_pair_passes=10 * steps * half['training_roots'],
                optimizer_parameter_updates=steps * 123 * hidden, diagnostic_candidate_predictions=5 * half['records'])
            checks['new_fit_budget_and_diagnostics_accounted'] &= (fit['family'] == 'UNIFORM_SHRINK'
                and fit['hidden'] == hidden and fit['parameter_count'] == model['parameter_count'] == 123 * hidden
                and all(fit['counts'][key] == model['counts'][key] == value for key, value in expected_counts.items()))
            metadata = fold['model_metadata'][method]
            half_metadata = original['model_metadata'][f'POOLED_H{hidden}_HALF']
            checks['deployed_model_metadata_bound'] &= (metadata_index.get((excluded, method)) == metadata
                and metadata['hidden'] == hidden and metadata['family'] == fit['family']
                and metadata['stage'] == 'HALF_CONTINUED' and metadata['heldout_life'] == excluded
                and metadata['source_lives'] == sources and metadata['half_source_path'] == half_metadata['path']
                and metadata['checkpoint'] == metadata['budget'] == settings['budgets'][0]
                and metadata['parameter_count'] == fit['parameter_count'])
            fit_counts.update(fit['counts'])
            fit_seconds += fit['seconds']
            fits.append(dict(heldout_life=excluded, method=method, **fit))
    return dict(checks=checks, bank_counts=dict(bank_counts), fold_data_counts=dict(data_counts),
        fit_counts=dict(fit_counts), fits=fits, fit_seconds=fit_seconds, data_seconds=data_seconds + bank['seconds'])


def analyze_run(run):
    settings, roots = run['settings'], run['cohort']['roots']
    lives, queries = settings['lifecycles'], settings['queries']
    count, replicas = settings['validation_roots_per_query'], settings['reference_replicas']
    expected_roots = {(life, query, episode) for life in lives for query in queries for episode in range(count)}
    root_ids = {root['root_id'] for root in roots}
    decisions = {(row['root_id'], row['heldout_life'], row['method']): row['event'] for row in run['decisions']}
    expected_decisions = {(root['root_id'], root['life'], method) for root in roots for method in LEARNED}
    expected_models = {(life, method) for life in lives for method in LEARNED}
    checks = dict(run_terminal=run['status'] == 'complete',
        cached_cohort_and_runner_checks=bool(run['runner_checks']) and all(run['runner_checks'].values())
            and bool(run['cohort']['log']['checks']) and all(run['cohort']['log']['checks'].values()),
        inherited_model_and_decision_counts_bound=run['inherited_model_count'] == len(lives) * len(OLD_LEARNED)
            and run['inherited_decisions'] == len(roots) * len(OLD_LEARNED),
        frozen_recipe_rosters=settings['methods'] == list(METHODS) and settings['contrasts'] == [list(pair) for pair in CONTRASTS]
            and settings['widths'] == list(WIDTHS) and len(lives) == len(set(lives)) == 4,
        full_root_model_and_decision_rosters=len(root_ids) == len(roots) == len(expected_roots)
            and {(root['life'], root['query'], root['episode']) for root in roots} == expected_roots
            and len(run['models']) == len(expected_models)
            and {(row['heldout_life'], row['method']) for row in run['models']} == expected_models
            and len(run['decisions']) == len(decisions) == len(expected_decisions) and set(decisions) == expected_decisions,
        excluded_history_scoring_only=all((row['root_id'], row['heldout_life'], row['method']) in expected_decisions
            for row in run['decisions']),
        new_scoring_roster_and_work_accounted=True,
        reused_acquisition_budgets_bound=True,
        fixed_reference_blocks=replicas == 32 and settings['reference_block_size'] == 16,
        inherited_reference_audits_pass=True, inherited_reference_rosters_and_costs=True, all_references_terminal=True)
    acquisition = run['acquisition_accounting']
    history_work = {row['life']: row for row in acquisition['per_history']}
    fold_work = {row['heldout_life']: row for row in acquisition['per_fold']}
    checks['reused_acquisition_budgets_bound'] = (acquisition['unique_source_histories'] == lives
        and len(history_work) == len(acquisition['per_history']) == len(lives) and set(history_work) == set(lives)
        and len(fold_work) == len(acquisition['per_fold']) == len(lives) and set(fold_work) == set(lives)
        and acquisition['unique_inherited_training_transitions'] == sum(row['full_transitions'] for row in history_work.values())
        and all(row['half_transitions'] == settings['budgets'][0] and row['full_transitions'] == settings['budgets'][-1]
            for row in history_work.values())
        and all(row['source_lives'] == [life for life in lives if life != excluded]
            and row['half_transitions'] == sum(history_work[life]['half_transitions'] for life in row['source_lives'])
            and row['full_transitions'] == sum(history_work[life]['full_transitions'] for life in row['source_lives'])
            for excluded, row in fold_work.items()))
    training = analyze_training(run)
    checks.update(training['checks'])
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
        if not (terminal and delta_complete and valid_audit and root['reference_complete']):
            missing.append(root_id)
            continue
        for block, utilities in reference_values(log, root['query'], replicas).items():
            for method in METHODS:
                event = None if method == 'H2_ONLY' else decisions.get((root_id, root['life'], method))
                if method != 'H2_ONLY' and event is None:
                    continue
                metrics[root_id, method, block] = event_metrics(event, utilities)
    for name in ('ground_work', 'planning_counts', 'outcomes'):
        work[name] = dict(work[name])

    def summarize(method, query, block, field, right=None):
        means = []
        for life in lives:
            group = [root for root in roots if root['life'] == life and root['query'] == query]
            values = []
            for root in group:
                value = metrics.get((root['root_id'], method, block), {}).get(field)
                if right is not None:
                    other = metrics.get((root['root_id'], right, block), {}).get(field)
                    value = value - other if value is not None and other is not None else None
                values.append(value)
            means.append(mean(values) if len(group) == count else None)
        return fold_summary(means, lives)

    methods = {method: {query: {block: {field: summarize(method, query, block, field) for field in FIELDS}
        for block in BLOCKS} for query in queries} for method in METHODS}
    comparisons = {left + '_minus_' + right: {query: {block: dict(
        selected_utility_delta=summarize(left, query, block, 'selected_reference_utility', right),
        pairwise_weighted_error_delta=summarize(left, query, block, 'pairwise_weighted_error', right))
        for block in BLOCKS} for query in queries} for left, right in CONTRASTS}
    decomposition = {}
    for hidden in WIDTHS:
        full, continued, half = f'POOLED_H{hidden}_FULL', f'POOLED_H{hidden}_HALF_CONTINUED', f'POOLED_H{hidden}_HALF'
        decomposition[str(hidden)] = {}
        for query in queries:
            decomposition[str(hidden)][query] = {}
            for block in BLOCKS:
                components = [comparisons[left + '_minus_' + right][query][block]['selected_utility_delta']['fold_means']
                    for left, right in ((full, half), (full, continued), (continued, half))]
                residuals = [total - data - extra if all(value is not None for value in (total, data, extra)) else None
                    for total, data, extra in zip(*components)]
                decomposition[str(hidden)][query][block] = fold_summary(residuals, lives)
    checks['additional_data_and_optimization_decomposition'] = all(abs(value) <= 1e-12
        for queries_ in decomposition.values() for blocks_ in queries_.values() for summary in blocks_.values()
        for value in summary['fold_means'] if value is not None)
    new_models = [row for row in run['models'] if row['method'] in NEW_METHODS]
    new_decisions = [row for row in run['decisions'] if row['method'] in NEW_METHODS]
    scoring, counts = run['scoring_log'], run['scoring_log']['counts']
    checks['new_scoring_roster_and_work_accounted'] = (bool(scoring['checks']) and all(scoring['checks'].values())
        and counts['model_payloads_loaded'] == len(new_models)
        and len(new_models) + run['inherited_model_count'] == len(run['models'])
        and len(new_decisions) + run['inherited_decisions'] == len(run['decisions'])
        and counts['model_root_scores'] == len(new_decisions)
        and counts['neural_candidate_predictions'] == len(new_decisions) * len(OPTIONS)
        and counts['neural_hidden_activations'] == len(OPTIONS) * sum(row['metadata']['hidden']
            * sum(root['life'] == row['heldout_life'] for root in roots) for row in new_models)
        and all(counts[key] == 0 for key in ('neural_model_fits', 'optimizer_steps', 'new_environment_transitions',
            'new_synthetic_transitions', 'model_prefix_trajectories')))
    complete = all(value for name, value in checks.items() if name != 'all_references_terminal')
    bank, data, fitting = training['bank_counts'], training['fold_data_counts'], training['fit_counts']
    return dict(schema='acfqp.half_continuation_analysis.v111', complete=complete,
        primary_complete=complete and checks['all_references_terminal'] and not missing, checks=checks,
        cohort=dict(unique_reference_roots=len(roots), inherited_reference_trajectories=work['trajectories'],
            inherited_model_root_decisions=run['inherited_decisions'],
            new_model_root_decisions=len(new_decisions), missing_or_censored_reference_roots=missing),
        methods=methods, comparisons=comparisons, effect_decomposition_residuals=decomposition, training=training,
        actual_executed_work=dict(newly_sampled_environment_transitions=bank['new_environment_transitions']
                + data.get('new_environment_transitions', 0) + counts['new_environment_transitions'],
            new_model_prefix_transitions=bank['new_synthetic_transitions']
                + data.get('new_synthetic_transitions', 0) + counts['new_synthetic_transitions'],
            new_neural_model_fits=fitting['neural_model_fits'] + bank['neural_model_fits']
                + data.get('neural_model_fits', 0) + counts['neural_model_fits'],
            new_optimizer_steps=fitting['optimizer_steps'] + counts['optimizer_steps'],
            new_optimizer_root_passes=fitting['optimizer_root_passes'],
            new_optimizer_pair_passes=fitting['optimizer_pair_passes'],
            new_optimizer_parameter_updates=fitting['optimizer_parameter_updates'],
            new_neural_candidate_predictions=counts['neural_candidate_predictions'],
            new_training_diagnostic_candidate_predictions=fitting['diagnostic_candidate_predictions'],
            new_model_root_decisions=counts['model_root_scores'], scoring_counts=counts,
            bank_counts=bank, input_counts=run['input_counts'], fold_data_counts=data, fitting_seconds=training['fit_seconds'],
            data_seconds=training['data_seconds'], scoring_seconds=scoring['seconds'],
            actual_wall_seconds=run['actual_wall_seconds']), inherited_reference_work=work,
        inherited_cohort_extraction_work=run['cohort']['log'], inherited_total_work=run['inherited_work'],
        inherited_acquisition_accounting=acquisition,
        evidence_scope='The continuation control uses only the actual pooled first batches, with the same initial half '
            'parameters, frozen half normalization/gamma, reset Adam moments and 1000 new steps as the inherited full-data '
            'update. FULL-minus-HALF_CONTINUED changes the inclusion of second-batch records at matched new optimizer '
            'steps; HALF_CONTINUED-minus-HALF measures additional optimization on unchanged records. Root/pair passes '
            'differ with pool size and are charged as executed. The two contrasts add to inherited FULL-minus-HALF. '
            'No inherited model is refit or rescored. Each new model scores only its excluded history. Fold means equally '
            'weight their retained roots and the grand mean equally weights all four folds, whose overlapping training '
            'histories do not constitute independent replicates. The 64 roots and 10240 references are reused evidence; '
            'A/B16 are descriptive partitions of pool32. Source-bank reads and eight pooled half payload reads are new '
            'work, whereas inherited acquisition/reference budgets are not multiplied by folds. Missing decisions or '
            'references never shrink the primary cohort. This does not identify label noise or representation drift '
            'as a unique cause, and creates no scientific Gate.')


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
