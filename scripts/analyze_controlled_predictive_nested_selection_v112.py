"""Evaluate source-history validation choices on their excluded outer histories."""
from collections import Counter
from itertools import combinations
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
    WIDTHS, METHODS as OLD_METHODS, LEARNED as INNER_METHODS, ZERO_DATA, fold_summary)

NEW_METHODS = tuple(f'SELECTED_H{hidden}' for hidden in WIDTHS)
METHODS = OLD_METHODS + NEW_METHODS
LEARNED = METHODS[1:]
CONTRASTS = tuple(pair for hidden in WIDTHS for pair in (
    (f'SELECTED_H{hidden}', f'POOLED_H{hidden}_HALF'),
    (f'SELECTED_H{hidden}', f'POOLED_H{hidden}_FULL'),
    (f'SELECTED_H{hidden}', 'H2_ONLY'),
    (f'POOLED_H{hidden}_FULL', f'POOLED_H{hidden}_HALF')))


def analyze_training(run):
    settings, bank = run['settings'], run['bank_log']
    lives, steps = settings['lifecycles'], settings['optimizer_steps']
    histories = {row['life']: row for row in bank['histories']}
    expected_pairs = {'_'.join(map(str, pair)): list(pair) for pair in combinations(lives, 2)}
    checks = dict(source_bank_roster_and_work_bound=len(histories) == len(bank['histories']) == len(lives)
        and set(histories) == set(lives) and bool(bank['checks']) and all(bank['checks'].values()),
        complete_inner_pair_roster=len(run['pairs']) == len(expected_pairs)
            and {row['pair_id']: row['source_lives'] for row in run['pairs']} == expected_pairs,
        inner_validation_histories_excluded=True, actual_source_half_full_rosters_bound=True,
        fixed_pair_learning_rule_bound=True, frozen_half_statistics_and_reset_adam=True,
        new_fit_budget_and_diagnostics_accounted=True, inner_model_metadata_bound=True)
    bank_counts = Counter()
    for log in bank['histories']:
        bank_counts.update(log['counts'])
        checks['source_bank_roster_and_work_bound'] &= (bool(log['checks']) and all(log['checks'].values())
            and all(log['counts'][key] == 0 for key in ZERO_DATA))
    checks['source_bank_roster_and_work_bound'] &= all(bank['counts'].get(key) == value for key, value in bank_counts.items())
    data_counts, fit_counts = Counter(), Counter()
    fit_seconds, data_seconds, fits = 0., 0., []
    metadata_index = {(row['pair_id'], row['method']): row['metadata'] for row in run['inner_models']}
    for pair in run['pairs']:
        pair_id, sources, data = pair['pair_id'], pair['source_lives'], pair['data_log']
        validation = [life for life in lives if life not in sources]
        checks['inner_validation_histories_excluded'] &= (data['pair_id'] == pair_id
            and pair_id == '_'.join(map(str, sources)) and data['source_lives'] == sources
            and data['validation_lives'] == validation and len(sources) == len(validation) == 2)
        checks['fixed_pair_learning_rule_bound'] &= (bool(data['checks']) and all(data['checks'].values())
            and set(pair['fit_logs']) == set(pair['model_metadata']) == set(INNER_METHODS))
        data_counts.update(pooled_record_references=data['half']['records'] + data['full']['records'])
        data_seconds += data['seconds']
        half = data['half']
        for stage in ('half', 'full'):
            summary = data[stage]
            train, heldout = summary['training_roster'], summary['heldout_roster']
            expected_train = [row for life in sources for row in bank['rosters'][str(life)][stage]['training_roster']]
            expected_heldout = [row for life in sources for row in bank['rosters'][str(life)][stage]['heldout_roster']]
            checks['actual_source_half_full_rosters_bound'] &= (train == expected_train and heldout == expected_heldout
                and len(train) == summary['training_roots'] and len(heldout) == summary['heldout_roots']
                and len(train) + len(heldout) == summary['records'])
            checks['inner_validation_histories_excluded'] &= all(row[0] in sources for row in train + heldout)
        for hidden in WIDTHS:
            half_fit = pair['fit_logs'][f'POOLED_H{hidden}_HALF']
            for stage, budget in zip(('HALF', 'FULL'), settings['budgets']):
                method = f'POOLED_H{hidden}_{stage}'
                fit, summary = pair['fit_logs'][method], data[stage.lower()]
                model = fit['models']['UNIFORM_SHRINK']
                statistics = fit['statistics_roster']
                checks['inner_validation_histories_excluded'] &= (fit['source_lives'] == sources
                    and all(row[0] in sources for row in fit['training_roster'] + fit['heldout_roster'] + statistics))
                checks['frozen_half_statistics_and_reset_adam'] &= (statistics == half['training_roster']
                    and fit['normalization_training_roots'] == fit['conflict_mass_training_roots'] == half['training_roots']
                    and fit['uniform_gamma'] == half_fit['uniform_gamma']
                    and fit['initialization'] == ('original_initialization' if stage == 'HALF' else 'half_parameters')
                    and fit['optimizer_state'] == 'reset_zero_moments' and fit['new_optimizer_steps'] == steps
                    and fit['inherited_parameter_steps'] == (0 if stage == 'HALF' else steps)
                    and fit['parameter_lineage_steps'] == (steps if stage == 'HALF' else 2 * steps))
                checks['fixed_pair_learning_rule_bound'] &= (bool(fit['checks']) and all(fit['checks'].values())
                    and fit['stage'] == stage and fit['checkpoint'] == budget
                    and fit['training_roster'] == summary['training_roster'] and fit['heldout_roster'] == summary['heldout_roster']
                    and fit['training_roots'] == summary['training_roots'] and fit['heldout_roots'] == summary['heldout_roots']
                    and fit['training_replica_rows'] == 4 * summary['training_roots']
                    and fit['total_training_pairs'] == 10 * summary['training_roots']
                    and fit['l2_coefficient'] == settings['l2_coefficient']
                    and fit['l2_reference_parameters'] == settings['l2_reference_parameters'])
                expected_counts = dict(neural_model_fits=1, optimizer_steps=steps,
                    optimizer_root_passes=steps * summary['training_roots'], optimizer_pair_passes=10 * steps * summary['training_roots'],
                    optimizer_parameter_updates=steps * 123 * hidden, diagnostic_candidate_predictions=5 * summary['records'])
                checks['new_fit_budget_and_diagnostics_accounted'] &= (fit['family'] == 'UNIFORM_SHRINK'
                    and fit['hidden'] == hidden and fit['parameter_count'] == model['parameter_count'] == 123 * hidden
                    and all(fit['counts'][key] == model['counts'][key] == value for key, value in expected_counts.items()))
                metadata = pair['model_metadata'][method]
                checks['inner_model_metadata_bound'] &= (metadata_index.get((pair_id, method)) == metadata
                    and metadata['hidden'] == hidden and metadata['family'] == fit['family']
                    and metadata['stage'] == stage and metadata['source_lives'] == sources
                    and metadata['validation_lives'] == validation
                    and metadata['checkpoint'] == metadata['budget'] == budget
                    and metadata['parameter_count'] == fit['parameter_count'])
                fit_counts.update(fit['counts'])
                fit_seconds += fit['seconds']
                fits.append(dict(pair_id=pair_id, method=method, **fit))
    return dict(checks=checks, bank_counts=dict(bank_counts), pair_data_counts=dict(data_counts),
        fit_counts=dict(fit_counts), fits=fits, fit_seconds=fit_seconds, data_seconds=data_seconds + bank['seconds'])


def analyze_selection(run, reference_utilities):
    settings, roots = run['settings'], run['cohort']['roots']
    lives, queries = settings['lifecycles'], settings['queries']
    count = settings['validation_roots_per_query']
    index = {(row['pair_id'], row['root_id'], row['method']): row['event'] for row in run['inner_decisions']}
    selected = {(row['heldout_life'], row['hidden'], row['query']): row for row in run['selections']}
    expected = {(life, hidden, query) for life in lives for hidden in WIDTHS for query in queries}
    log = run['selection_log']
    checks = dict(selection_roster_complete=len(selected) == len(run['selections']) == len(expected) and set(selected) == expected,
        source_only_selection_recomputed=True, strict_positive_source_mean_selects_full=True,
        cached_selection_work_accounted=bool(log['checks']) and all(log['checks'].values()))
    decisions = {(row['root_id'], row['heldout_life'], row['method']): row['event'] for row in run['decisions']}
    checks['selected_events_match_chosen_outer_model'] = True
    frequency = {str(hidden): {query: dict(HALF=0, FULL=0) for query in queries} for hidden in WIDTHS}
    for outer, hidden, query in sorted(expected):
        row = selected.get((outer, hidden, query))
        if row is None:
            checks['source_only_selection_recomputed'] = False
            continue
        sources = [life for life in lives if life != outer]
        folds = []
        for validation in sources:
            training = [life for life in sources if life != validation]
            pair_id = '_'.join(map(str, training))
            group = sorted((root for root in roots if root['life'] == validation and root['query'] == query),
                key=lambda root: root['episode'])
            values = []
            for root in group:
                utility = reference_utilities.get(root['root_id'], {}).get('pooled')
                half = index.get((pair_id, root['root_id'], f'POOLED_H{hidden}_HALF'))
                full = index.get((pair_id, root['root_id'], f'POOLED_H{hidden}_FULL'))
                values.append(utility[full['option']] - utility[half['option']]
                    if utility is not None and half is not None and full is not None else None)
            folds.append(dict(validation_life=validation, pair_id=pair_id, source_lives=training,
                root_ids=[root['root_id'] for root in group], mean_utility_delta=mean(values) if len(group) == count else None))
        average = mean(fold['mean_utility_delta'] for fold in folds)
        checks['source_only_selection_recomputed'] &= (row['source_lives'] == sources
            and row['validation_folds'] == folds and average is not None and row['mean_utility_delta'] == average)
        chosen = 'FULL' if average is not None and average > 0 else 'HALF'
        chosen_method = f'POOLED_H{hidden}_{chosen}'
        checks['strict_positive_source_mean_selects_full'] &= (average is not None
            and row['chosen_stage'] == chosen and row['chosen_method'] == chosen_method)
        if row['chosen_stage'] in ('HALF', 'FULL'):
            frequency[str(hidden)][query][row['chosen_stage']] += 1
        for root in roots:
            if root['life'] != outer or root['query'] != query:
                continue
            chosen_event = decisions.get((root['root_id'], outer, row['chosen_method']))
            derived = decisions.get((root['root_id'], outer, f'SELECTED_H{hidden}'))
            checks['selected_events_match_chosen_outer_model'] &= chosen_event is not None and derived == chosen_event
    counts = log['counts']
    comparisons = len(expected) * (len(lives) - 1) * count
    checks['cached_selection_work_accounted'] &= (counts['selections'] == len(expected)
        and counts['validation_folds'] == len(expected) * (len(lives) - 1)
        and counts['root_comparisons'] == comparisons and counts['cached_decision_lookups'] == 2 * comparisons
        and all(counts[key] == 0 for key in ('neural_candidate_predictions', 'neural_model_fits',
            'new_environment_transitions', 'new_synthetic_transitions')))
    return dict(checks=checks, choice_counts=frequency, selections=run['selections'], counts=counts)


def reference_work(roots):
    counters = {name: Counter() for name in ('ground_work', 'planning_counts', 'outcomes')}
    for root in roots:
        for name in counters:
            counters[name].update(root['reference_log'][name])
    return dict(roots=len(roots), trajectories=sum(root['reference_log']['trajectories'] for root in roots),
        sampled_transitions=counters['ground_work']['sampled_transitions'],
        **{name: dict(values) for name, values in counters.items()})


def selection_cost_bound(run):
    roots, lives = run['cohort']['roots'], run['settings']['lifecycles']
    cost, acquisition = run['selection_acquisition_accounting'], run['acquisition_accounting']
    histories = {row['life']: row for row in cost['per_history']}
    original = {row['life']: row for row in acquisition['per_history']}
    folds = {row['heldout_life']: row for row in cost['per_fold']}
    valid = (bool(cost['checks']) and all(cost['checks'].values()) and cost['newly_sampled_environment_transitions'] == 0
        and len(histories) == len(cost['per_history']) == len(lives) and set(histories) == set(lives)
        and len(folds) == len(cost['per_fold']) == len(lives) and set(folds) == set(lives))
    for life in lives:
        row = histories[life]
        valid &= (row['reference_work'] == reference_work([root for root in roots if root['life'] == life])
            and row['half_transitions'] == original[life]['half_transitions']
            and row['full_transitions'] == original[life]['full_transitions'])
        fold = folds[life]
        sources = [source for source in lives if source != life]
        source_work = reference_work([root for root in roots if root['life'] in sources])
        outer_work = row['reference_work']
        training = sum(original[source]['full_transitions'] for source in sources)
        valid &= (fold['source_lives'] == sources and fold['selection_validation_work'] == source_work
            and fold['outer_evaluation_work'] == outer_work
            and fold['source_training_transitions'] == fold['full_baseline_training_transitions'] == training
            and fold['half_baseline_training_transitions'] == sum(original[source]['half_transitions'] for source in sources)
            and fold['learning_validation_environment_transitions'] == training + source_work['sampled_transitions']
            and fold['outer_evaluation_environment_transitions'] == outer_work['sampled_transitions'])
    unique = cost['unique_physical']
    physical = reference_work(roots)
    training = sum(original[life]['full_transitions'] for life in lives)
    return bool(valid and unique['source_lives'] == lives and unique['reference_work'] == physical
        and unique['training_environment_transitions'] == training
        and unique['training_plus_reference_environment_transitions'] == training + physical['sampled_transitions'])


def analyze_run(run):
    settings, roots = run['settings'], run['cohort']['roots']
    lives, queries = settings['lifecycles'], settings['queries']
    count, replicas = settings['validation_roots_per_query'], settings['reference_replicas']
    expected_roots = {(life, query, episode) for life in lives for query in queries for episode in range(count)}
    root_ids = {root['root_id'] for root in roots}
    root_lives = {root['root_id']: root['life'] for root in roots}
    decisions = {(row['root_id'], row['heldout_life'], row['method']): row['event'] for row in run['decisions']}
    expected_decisions = {(root['root_id'], root['life'], method) for root in roots for method in LEARNED}
    expected_models = {(life, method) for life in lives for method in INNER_METHODS}
    pairs = {'_'.join(map(str, pair)): list(pair) for pair in combinations(lives, 2)}
    inner = {(row['pair_id'], row['root_id'], row['method']): row['event'] for row in run['inner_decisions']}
    expected_inner = {(pair_id, root['root_id'], method) for pair_id, sources in pairs.items()
        for root in roots if root['life'] not in sources for method in INNER_METHODS}
    expected_inner_models = {(pair_id, method) for pair_id in pairs for method in INNER_METHODS}
    checks = dict(run_terminal=run['status'] == 'complete',
        cached_outer_models_decisions_and_cohort_exact=bool(run['runner_checks']) and all(run['runner_checks'].values())
            and bool(run['cohort']['log']['checks']) and all(run['cohort']['log']['checks'].values()),
        frozen_recipe_rosters=settings['methods'] == list(METHODS) and settings['contrasts'] == [list(pair) for pair in CONTRASTS]
            and settings['widths'] == list(WIDTHS) and len(lives) == len(set(lives)) == 4,
        full_outer_root_model_and_decision_rosters=len(root_ids) == len(roots) == len(expected_roots)
            and {(root['life'], root['query'], root['episode']) for root in roots} == expected_roots
            and len(run['models']) == run['inherited_model_count'] == len(expected_models)
            and {(row['heldout_life'], row['method']) for row in run['models']} == expected_models
            and len(run['decisions']) == len(decisions) == len(expected_decisions) and set(decisions) == expected_decisions
            and run['inherited_decisions'] == len(roots) * len(INNER_METHODS),
        complete_inner_model_decision_rosters=len(run['inner_models']) == len(expected_inner_models)
            and {(row['pair_id'], row['method']) for row in run['inner_models']} == expected_inner_models
            and len(run['inner_decisions']) == len(inner) == len(expected_inner) and set(inner) == expected_inner,
        only_excluded_inner_histories_scored=all((row['pair_id'], row['root_id'], row['method']) in expected_inner
            and row['validation_life'] == root_lives.get(row['root_id']) for row in run['inner_decisions']),
        new_inner_scoring_work_accounted=True, derived_outer_decisions_without_scoring=True,
        source_reference_validation_charged_as_learning=selection_cost_bound(run),
        fixed_reference_blocks=replicas == 32 and settings['reference_block_size'] == 16,
        inherited_reference_audits_pass=True, inherited_reference_rosters_and_costs=True, all_references_terminal=True)
    training = analyze_training(run)
    checks.update(training['checks'])
    metrics, reference_utilities, missing = {}, {}, []
    for root in roots:
        root_id, log = root['root_id'], root['reference_log']
        valid_audit = bool(root['reference_audit']) and all(root['reference_audit'].values())
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
        reference_utilities[root_id] = reference_values(log, root['query'], replicas)
        for block, utilities in reference_utilities[root_id].items():
            for method in METHODS:
                event = None if method == 'H2_ONLY' else decisions.get((root_id, root['life'], method))
                if method != 'H2_ONLY' and event is None:
                    continue
                metrics[root_id, method, block] = event_metrics(event, utilities)
    selection = analyze_selection(run, reference_utilities)
    checks.update(selection['checks'])

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
    transfer = {}
    choices = {(row['heldout_life'], row['hidden'], row['query']): row for row in run['selections']}
    for hidden in WIDTHS:
        transfer[str(hidden)] = {}
        for query in queries:
            transfer[str(hidden)][query] = {}
            for block in BLOCKS:
                actual = comparisons[f'POOLED_H{hidden}_FULL_minus_POOLED_H{hidden}_HALF'][query][block]['selected_utility_delta']['fold_means']
                rows = []
                for life, outer_delta in zip(lives, actual):
                    choice = choices.get((life, hidden, query))
                    source_delta = choice['mean_utility_delta'] if choice else None
                    same = ((source_delta > 0) - (source_delta < 0) == (outer_delta > 0) - (outer_delta < 0)
                        if source_delta is not None and outer_delta is not None else None)
                    rows.append(dict(heldout_life=life, source_validation_delta=source_delta,
                        outer_update_delta=outer_delta, same_direction=same))
                transfer[str(hidden)][query][block] = dict(folds=rows,
                    same_direction=sum(row['same_direction'] is True for row in rows),
                    opposite_or_zero_direction=sum(row['same_direction'] is False for row in rows),
                    missing=sum(row['same_direction'] is None for row in rows))
    scoring, counts = run['scoring_log'], run['scoring_log']['counts']
    checks['new_inner_scoring_work_accounted'] = (bool(scoring['checks']) and all(scoring['checks'].values())
        and counts['model_payloads_loaded'] == len(run['inner_models'])
        and counts['model_root_scores'] == len(run['inner_decisions'])
        and counts['neural_candidate_predictions'] == len(run['inner_decisions']) * len(OPTIONS)
        and counts['neural_hidden_activations'] == len(OPTIONS) * sum(row['metadata']['hidden']
            * sum(root['life'] in row['metadata']['validation_lives'] for root in roots) for row in run['inner_models'])
        and all(counts[key] == 0 for key in ('neural_model_fits', 'optimizer_steps', 'new_environment_transitions',
            'new_synthetic_transitions', 'model_prefix_trajectories')))
    derived = [row for row in run['decisions'] if row['method'] in NEW_METHODS]
    log = run['derived_log']
    checks['derived_outer_decisions_without_scoring'] = (bool(log['checks']) and all(log['checks'].values())
        and len(derived) == log['counts']['derived_outer_decisions'] == log['counts']['cached_outer_decision_lookups']
        and len(derived) == len(roots) * len(WIDTHS) and log['counts']['new_neural_candidate_predictions'] == 0)
    complete = all(value for name, value in checks.items() if name != 'all_references_terminal')
    bank, fitting = training['bank_counts'], training['fit_counts']
    return dict(schema='acfqp.nested_selection_analysis.v112', complete=complete,
        primary_complete=complete and checks['all_references_terminal'] and not missing, checks=checks,
        cohort=dict(unique_reference_roots=len(roots), inherited_reference_trajectories=reference_work(roots)['trajectories'],
            inherited_model_root_decisions=run['inherited_decisions'], new_inner_model_root_decisions=len(run['inner_decisions']),
            derived_outer_decisions=len(derived), missing_or_censored_reference_roots=missing),
        methods=methods, comparisons=comparisons, training=training, selection=selection, selection_transfer=transfer,
        actual_executed_work=dict(newly_sampled_environment_transitions=bank['new_environment_transitions'] + counts['new_environment_transitions'],
            new_model_prefix_transitions=bank['new_synthetic_transitions'] + counts['new_synthetic_transitions'],
            new_neural_model_fits=fitting['neural_model_fits'] + bank['neural_model_fits'] + counts['neural_model_fits'],
            new_optimizer_steps=fitting['optimizer_steps'] + counts['optimizer_steps'],
            new_optimizer_root_passes=fitting['optimizer_root_passes'], new_optimizer_pair_passes=fitting['optimizer_pair_passes'],
            new_optimizer_parameter_updates=fitting['optimizer_parameter_updates'],
            new_neural_candidate_predictions=counts['neural_candidate_predictions'],
            new_training_diagnostic_candidate_predictions=fitting['diagnostic_candidate_predictions'],
            new_inner_model_root_decisions=counts['model_root_scores'], derived_outer_decisions=len(derived),
            new_outer_neural_candidate_predictions=log['counts']['new_neural_candidate_predictions'],
            scoring_counts=counts, selection_counts=selection['counts'], derived_counts=log['counts'],
            bank_counts=bank, pair_data_counts=training['pair_data_counts'], fitting_seconds=training['fit_seconds'],
            data_seconds=training['data_seconds'], scoring_seconds=scoring['seconds'],
            selection_seconds=run['selection_log']['seconds'], derived_seconds=log['seconds'],
            actual_wall_seconds=run['actual_wall_seconds']), inherited_reference_work=reference_work(roots),
        inherited_cohort_extraction_work=run['cohort']['log'], inherited_total_work=run['inherited_work'],
        inherited_acquisition_accounting=run['acquisition_accounting'],
        selection_acquisition_accounting=run['selection_acquisition_accounting'],
        evidence_scope='For each excluded outer history, the other three histories supply inner two-train one-validation '
            'comparisons. FULL is deployed only when the equal-history pooled32 validation advantage is positive; '
            'otherwise HALF is retained. Source validation references are part of learning cost. The outer history '
            'does not enter its own selection. Outer model decisions are copied from the retained V110 cache with no '
            'new neural score. All 24 inner fits and 768 inner decisions are newly charged; acquisition/reference work '
            'is inherited and counted once physically despite overlapping folds. HALF selection still incurs full source '
            'data and validation acquisition. The four folds overlap and reuse a previously explored reference bank; '
            'they are not independent confirmation. A/B16 partition the outer evaluation only. Missing roots or decisions '
            'do not shrink the primary cohort. No new scientific Gate.')


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
