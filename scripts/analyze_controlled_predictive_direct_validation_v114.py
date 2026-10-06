"""Retrospectively test validation of the actual three-source deployment models."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'src'))
from acfqp.science.controlled_predictive_fragments_v83 import OPTIONS
from scripts.analyze_controlled_predictive_crossed_ranking_v106 import event_metrics, matrix_summary, mean, BLOCKS, FIELDS
from scripts.analyze_controlled_predictive_natural_reference_v104 import reference_values
from scripts.analyze_controlled_predictive_fresh_targets_v113 import METHODS as OLD_METHODS, BASE_METHODS, WIDTHS

NEW_METHODS = tuple(f'DIRECT_H{hidden}' for hidden in WIDTHS)
METHODS = OLD_METHODS + NEW_METHODS
CONTRASTS = tuple((f'DIRECT_H{hidden}', right) for hidden in WIDTHS for right in (
    f'SELECTED_H{hidden}', f'POOLED_H{hidden}_HALF', f'POOLED_H{hidden}_FULL', 'H2_ONLY'))


def analyze_source_selection(run):
    settings, roots = run['settings'], run['source_cohort']['roots']
    bundles, queries = settings['source_bundles'], settings['queries']
    count, replicas = settings['validation_roots_per_query'], settings['reference_replicas']
    root_by_id = {root['root_id']: root for root in roots}
    expected_roots = {(life, query, episode) for life in bundles for query in queries for episode in range(count)}
    expected_decisions = {(bundle, root['root_id'], method) for bundle in bundles for root in roots
        if root['life'] != bundle for method in BASE_METHODS}
    decisions = {(row['bundle_id'], row['root_id'], row['method']): row['event'] for row in run['source_decisions']}
    choices = {(row['heldout_life'], row['hidden'], row['query']): row for row in run['direct_selections']}
    expected_choices = {(bundle, hidden, query) for bundle in bundles for hidden in WIDTHS for query in queries}
    source_log, selection_log = run['source_scoring_log'], run['direct_selection_log']
    overlap = run['source_overlap_check']
    checks = dict(complete_source_validation_roots=len(root_by_id) == len(roots) == len(expected_roots)
        and {(root['life'], root['query'], root['episode']) for root in roots} == expected_roots,
        source_validation_samples_disjoint_from_training=overlap['source_seed_overlap_count'] == overlap['board_overlap_count'] == 0
            and overlap['validation_roots'] == len(roots) and bool(overlap['checks']) and all(overlap['checks'].values()),
        complete_actual_model_validation_decisions=len(run['source_decisions']) == len(decisions) == len(expected_decisions)
            and set(decisions) == expected_decisions,
        validation_uses_own_three_source_models=source_log['validation_source_models'] == selection_log['validation_source_models']
            == 'three_source_deployment',
        source_reference_rosters_complete=True, direct_selection_roster=len(choices) == len(run['direct_selections']) == len(expected_choices)
            and set(choices) == expected_choices,
        direct_source_selection_recomputed=True, strict_positive_mean_selects_full=True,
        new_source_scoring_work_accounted=True, new_source_selection_work_accounted=True)
    model_index = {(row['bundle_id'], row['method']): row['metadata'] for row in run['models']}
    bindings = {(row['bundle_id'], row['method']): row for row in source_log['model_bindings']}
    checks['validation_uses_own_three_source_models'] &= (len(bindings) == len(source_log['model_bindings']) == len(model_index)
        and set(bindings) == set(model_index) and all(binding['source_lives'] == model_index[key]['source_lives']
            and binding['retained_model_path'] == model_index[key]['path'] for key, binding in bindings.items()))
    for row in run['source_decisions']:
        root = root_by_id.get(row['root_id'])
        checks['validation_uses_own_three_source_models'] &= (root is not None
            and row['validation_life'] == root['life'] and root['life'] != row['bundle_id'])
    utilities = {}
    for root in roots:
        log = root['reference_log']
        valid = (root['reference_complete'] and not log['censored_root'] and bool(root['reference_audit'])
            and all(root['reference_audit'].values()) and set(log['outcomes']) <= {'WON', 'LOST'}
            and log['trajectories'] == sum(log['outcomes'].values()) == replicas * len(OPTIONS)
            and set(log['pair_deltas']) == set(OPTIONS[1:]) and all(len(log['pair_deltas'][option]) == replicas
                and all(len(row) == 3 for row in log['pair_deltas'][option]) for option in OPTIONS[1:]))
        checks['source_reference_rosters_complete'] &= valid
        if valid:
            utilities[root['root_id']] = reference_values(log, root['query'], replicas)['pooled']
    frequency = {str(hidden): {query: dict(HALF=0, FULL=0) for query in queries} for hidden in WIDTHS}
    old = {(row['heldout_life'], row['hidden'], row['query']): row for row in run['frozen_selections']}
    changes = []
    for bundle, hidden, query in sorted(expected_choices):
        choice = choices.get((bundle, hidden, query))
        if choice is None:
            checks['direct_source_selection_recomputed'] = False
            continue
        sources = [life for life in bundles if life != bundle]
        folds = []
        for validation in sources:
            group = sorted((root for root in roots if root['life'] == validation and root['query'] == query),
                key=lambda root: root['episode'])
            deltas = []
            for root in group:
                values = utilities.get(root['root_id'])
                half = decisions.get((bundle, root['root_id'], f'POOLED_H{hidden}_HALF'))
                full = decisions.get((bundle, root['root_id'], f'POOLED_H{hidden}_FULL'))
                deltas.append(values[full['option']] - values[half['option']]
                    if values is not None and half is not None and full is not None else None)
            folds.append(dict(validation_life=validation, source_lives=sources,
                root_ids=[root['root_id'] for root in group], mean_utility_delta=mean(deltas) if len(group) == count else None))
        average = mean(fold['mean_utility_delta'] for fold in folds)
        checks['direct_source_selection_recomputed'] &= (choice['source_lives'] == sources and choice['validation_folds'] == folds
            and average is not None and choice['mean_utility_delta'] == average)
        stage = 'FULL' if average is not None and average > 0 else 'HALF'
        checks['strict_positive_mean_selects_full'] &= average is not None and choice['chosen_stage'] == stage and choice['chosen_method'] == f'POOLED_H{hidden}_{stage}'
        if choice['chosen_stage'] in ('HALF', 'FULL'):
            frequency[str(hidden)][query][choice['chosen_stage']] += 1
        previous = old.get((bundle, hidden, query))
        changes.append(dict(bundle_id=bundle, hidden=hidden, query=query, direct_stage=choice['chosen_stage'],
            previous_stage=previous['chosen_stage'] if previous else None,
            changed=previous is not None and previous['chosen_stage'] != choice['chosen_stage'],
            direct_source_validation_delta=average,
            previous_proxy_validation_delta=previous.get('mean_utility_delta') if previous else None))
    counts = source_log['counts']
    checks['new_source_scoring_work_accounted'] = (bool(source_log['checks']) and all(source_log['checks'].values())
        and counts['model_payloads_loaded'] == len(run['models'])
        and counts['model_root_scores'] == len(run['source_decisions'])
        and counts['neural_candidate_predictions'] == len(run['source_decisions']) * len(OPTIONS)
        and counts['neural_hidden_activations'] == len(OPTIONS) * sum(row['metadata']['hidden']
            * sum(root['life'] in row['metadata']['source_lives'] for root in roots) for row in run['models'])
        and all(counts[key] == 0 for key in ('new_environment_transitions', 'new_synthetic_transitions',
            'neural_model_fits', 'optimizer_steps', 'model_prefix_trajectories')))
    counts = selection_log['counts']
    comparisons = len(expected_choices) * (len(bundles) - 1) * count
    checks['new_source_selection_work_accounted'] = (bool(selection_log['checks']) and all(selection_log['checks'].values())
        and counts['selections'] == len(expected_choices) and counts['validation_folds'] == 3 * len(expected_choices)
        and counts['root_comparisons'] == comparisons and counts['cached_decision_lookups'] == 2 * comparisons
        and all(counts[key] == 0 for key in ('neural_candidate_predictions', 'neural_model_fits', 'optimizer_steps',
            'new_environment_transitions', 'new_synthetic_transitions')))
    return dict(checks=checks, choice_counts=frequency, changes_from_proxy=changes,
        changed_selections=sum(row['changed'] for row in changes), selections=run['direct_selections'])


def analyze_run(run):
    settings, roots = run['settings'], run['cohort']['roots']
    bundles, targets, queries = settings['source_bundles'], settings['lifecycles'], settings['queries']
    count, replicas = settings['validation_roots_per_query'], settings['reference_replicas']
    root_ids = {root['root_id'] for root in roots}
    expected_roots = {(life, query, episode) for life in targets for query in queries for episode in range(count)}
    expected_models = {(bundle, method) for bundle in bundles for method in BASE_METHODS}
    models = {(row['bundle_id'], row['method']): row['metadata'] for row in run['models']}
    inherited_models = {(row['heldout_life'], row['method']): row['metadata'] for row in run['source_models']}
    decisions = {(row['root_id'], row['bundle_id'], row['method']): row['event'] for row in run['decisions']}
    expected_decisions = {(root['root_id'], bundle, method) for root in roots for bundle in bundles for method in METHODS[1:]}
    choices = {(row['heldout_life'], row['hidden'], row['query']): row for row in run['direct_selections']}
    checks = dict(run_terminal=run['status'] == 'complete',
        frozen_recipe_and_inherited_records=bool(run['runner_checks']) and all(run['runner_checks'].values())
            and bool(run['inherited_runner_checks']) and all(run['inherited_runner_checks'].values())
            and run['inherited_target_analysis']['complete'] and settings['methods'] == list(METHODS)
            and settings['contrasts'] == [list(pair) for pair in CONTRASTS]
            and bundles == [11, 12, 13, 14] and targets == [15, 16, 17, 18] and settings['widths'] == list(WIDTHS),
        complete_target_model_and_decision_rosters=len(root_ids) == len(roots) == len(expected_roots)
            and {(root['life'], root['query'], root['episode']) for root in roots} == expected_roots
            and len(run['models']) == len(models) == len(expected_models) and set(models) == expected_models and models == inherited_models
            and len(run['decisions']) == len(decisions) == len(expected_decisions) and set(decisions) == expected_decisions,
        inherited_target_decisions_exact=[row for row in run['decisions'] if row['method'] in OLD_METHODS[1:]]
            == run['inherited_target_decisions'],
        fixed_pooled_reference_blocks=replicas == 32 and settings['reference_block_size'] == 16,
        selected_direct_target_events_exact=True, new_derivation_work_without_target_scoring=True,
        inherited_target_reference_audits=True, all_target_references_terminal=True)
    source = analyze_source_selection(run)
    checks.update(source['checks'])
    metrics, missing = {}, []
    root_by_id = {root['root_id']: root for root in roots}
    for root in roots:
        log = root['reference_log']
        audit = bool(root['reference_audit']) and all(root['reference_audit'].values())
        terminal = root['reference_complete'] and not log['censored_root'] and set(log['outcomes']) <= {'WON', 'LOST'}
        complete_deltas = set(log['pair_deltas']) == set(OPTIONS[1:]) and all(len(log['pair_deltas'][option]) == replicas
            and all(len(vector) == 3 for vector in log['pair_deltas'][option]) for option in OPTIONS[1:])
        checks['inherited_target_reference_audits'] &= audit
        checks['all_target_references_terminal'] &= terminal
        if not (audit and terminal and complete_deltas):
            missing.append(root['root_id'])
            continue
        for block, utilities in reference_values(log, root['query'], replicas).items():
            for bundle in bundles:
                for method in METHODS:
                    event = None if method == 'H2_ONLY' else decisions.get((root['root_id'], bundle, method))
                    if method != 'H2_ONLY' and event is None:
                        continue
                    metrics[root['root_id'], bundle, method, block] = event_metrics(event, utilities)
    derived = [row for row in run['decisions'] if row['method'] in NEW_METHODS]
    for row in derived:
        root = root_by_id[row['root_id']]
        hidden = int(row['method'].split('H')[-1])
        choice = choices.get((row['bundle_id'], hidden, root['query']))
        chosen = models.get((row['bundle_id'], choice['chosen_method'])) if choice else None
        event = decisions.get((row['root_id'], row['bundle_id'], choice['chosen_method'])) if choice else None
        checks['selected_direct_target_events_exact'] &= (choice is not None and chosen is not None and event is not None
            and row['event'] == event and row['chosen_method'] == choice['chosen_method']
            and row['chosen_model_path'] == chosen['path'] and row['target_life'] == root['life'])
    log = run['derived_log']
    checks['new_derivation_work_without_target_scoring'] = (bool(log['checks']) and all(log['checks'].values())
        and len(derived) == len(roots) * len(bundles) * len(WIDTHS)
        and log['counts']['derived_decisions'] == log['counts']['cached_decision_lookups'] == len(derived)
        and log['counts']['new_neural_candidate_predictions'] == 0)

    def summarize(method, query, block, field, right=None):
        cells = []
        for bundle in bundles:
            row = []
            for target in targets:
                group = [root for root in roots if root['life'] == target and root['query'] == query]
                values = []
                for root in group:
                    value = metrics.get((root['root_id'], bundle, method, block), {}).get(field)
                    if right is not None:
                        other = metrics.get((root['root_id'], bundle, right, block), {}).get(field)
                        value = value - other if value is not None and other is not None else None
                    values.append(value)
                row.append(mean(values) if len(group) == count else None)
            cells.append(row)
        return matrix_summary(cells, bundles, targets)

    methods = {method: {query: {block: {field: summarize(method, query, block, field) for field in FIELDS}
        for block in BLOCKS} for query in queries} for method in METHODS}
    comparisons = {left + '_minus_' + right: {query: {block: dict(
        selected_utility_delta=summarize(left, query, block, 'selected_reference_utility', right),
        pairwise_weighted_error_delta=summarize(left, query, block, 'pairwise_weighted_error', right))
        for block in BLOCKS} for query in queries} for left, right in CONTRASTS}
    score_counts, selection_counts, derived_counts = run['source_scoring_log']['counts'], run['direct_selection_log']['counts'], log['counts']
    complete = all(value for name, value in checks.items() if name != 'all_target_references_terminal')
    return dict(schema='acfqp.direct_validation_analysis.v114', complete=complete,
        primary_complete=complete and checks['all_target_references_terminal'] and not missing, checks=checks,
        cohort=dict(source_validation_roots=len(run['source_cohort']['roots']), reused_target_roots=len(roots),
            source_bundles=bundles, target_histories=targets, missing_or_censored_target_roots=missing),
        methods=methods, comparisons=comparisons, source_selection=source,
        actual_executed_work=dict(newly_sampled_environment_transitions=score_counts['new_environment_transitions']
                + selection_counts['new_environment_transitions'],
            new_model_prefix_transitions=score_counts['new_synthetic_transitions'] + selection_counts['new_synthetic_transitions'],
            new_neural_model_fits=score_counts['neural_model_fits'] + selection_counts['neural_model_fits'],
            new_optimizer_steps=score_counts['optimizer_steps'] + selection_counts['optimizer_steps'], new_selection_decisions=selection_counts['selections'],
            new_neural_candidate_predictions=score_counts['neural_candidate_predictions'],
            new_source_model_root_decisions=score_counts['model_root_scores'],
            derived_target_decisions=len(derived), new_target_neural_candidate_predictions=derived_counts['new_neural_candidate_predictions'],
            source_scoring_counts=score_counts, selection_counts=selection_counts, derived_counts=derived_counts,
            source_scoring_seconds=run['source_scoring_log']['seconds'], selection_seconds=run['direct_selection_log']['seconds'],
            derived_seconds=log['seconds'], actual_wall_seconds=run['actual_wall_seconds']),
        inherited_total_work=run['inherited_work'],
        inherited_target_evaluation_work=run['inherited_target_analysis']['actual_executed_work'],
        inherited_selection_acquisition_accounting=run['inherited_selection_acquisition_accounting'],
        evidence_scope='Only the model pair used for source validation changes: the actual three-source deployment '
            'HALF/FULL pair replaces the two-source proxy. Validation roots are from the same source histories but have '
            'distinct source seeds and boards from fitting samples. The rule remains an equal-history pooled32 mean '
            'strictly greater than zero for FULL, otherwise HALF. No target reference enters selection. DIRECT target '
            'events are copied from the existing V113 HALF/FULL cache; old SELECTED events remain inherited. Target '
            'matrices retain all four source bundles and all four target histories with equal weights on both axes. '
            'Source reference acquisition remains a learning/validation cost; all V113 sampling is inherited, not new. '
            'This mechanism comparison was designed after observing V113, so its target results are retrospective and '
            'require fresh confirmation. It neither identifies the unique cause of generalization failure nor creates '
            'a new scientific Gate.')


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
