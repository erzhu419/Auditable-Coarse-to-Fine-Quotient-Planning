"""Cross frozen source learners and update choices on independent fresh targets."""
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
    event_metrics, matrix_summary, mean, BLOCKS, FIELDS)
from scripts.analyze_controlled_predictive_natural_reference_v104 import reference_values
from scripts.analyze_controlled_predictive_nested_selection_v112 import (
    METHODS, CONTRASTS, INNER_METHODS as BASE_METHODS, NEW_METHODS, WIDTHS)


def summarize_metrics(metrics, roots, settings):
    bundles, targets = settings['source_bundles'], settings['lifecycles']
    count, queries = settings['validation_roots_per_query'], settings['queries']

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
    return methods, comparisons


def analyze_run(run):
    settings, roots = run['settings'], run['cohort']['roots']
    bundles, targets, queries = settings['source_bundles'], settings['lifecycles'], settings['queries']
    count, replicas = settings['validation_roots_per_query'], settings['reference_replicas']
    root_ids = {root['root_id'] for root in roots}
    expected_roots = {(life, query, episode) for life in targets for query in queries for episode in range(count)}
    decisions = {(row['root_id'], row['bundle_id'], row['method']): row['event'] for row in run['decisions']}
    expected_decisions = {(root['root_id'], bundle, method) for root in roots for bundle in bundles for method in METHODS[1:]}
    expected_models = {(bundle, method) for bundle in bundles for method in BASE_METHODS}
    metadata = {(row['bundle_id'], row['method']): row['metadata'] for row in run['models']}
    inherited = {(row['heldout_life'], row['method']): row['metadata'] for row in run['source_models']}
    choices = {(row['heldout_life'], row['hidden'], row['query']): row for row in run['frozen_selections']}
    expected_choices = {(bundle, hidden, query) for bundle in bundles for hidden in WIDTHS for query in queries}
    checks = dict(run_terminal=run['status'] == 'complete',
        frozen_execution_recipe=bool(run['runner_checks']) and all(run['runner_checks'].values())
            and settings['methods'] == list(METHODS) and settings['contrasts'] == [list(pair) for pair in CONTRASTS]
            and bundles == [11, 12, 13, 14] and targets == [15, 16, 17, 18]
            and settings['widths'] == list(WIDTHS),
        complete_fresh_root_roster=len(root_ids) == len(roots) == len(expected_roots) == run['cohort']['expected_roots']
            and {(root['life'], root['query'], root['episode']) for root in roots} == expected_roots
            and not run['cohort']['missing_roots'],
        complete_crossed_model_and_decision_rosters=len(run['models']) == len(metadata) == len(expected_models)
            and set(metadata) == expected_models and metadata == inherited
            and len(run['decisions']) == len(decisions) == len(expected_decisions) and set(decisions) == expected_decisions,
        frozen_source_choices_and_target_exclusion=len(choices) == len(run['frozen_selections']) == len(expected_choices)
            and set(choices) == expected_choices and set(targets).isdisjoint(bundles),
        fresh_root_streams_and_features_bound=True, source_and_prefix_work_accounted=True,
        source_history_execution_checks=True, complete_reference_roster=run['cohort']['completed_references'] == len(roots),
        fixed_reference_blocks=replicas == 32 and settings['reference_block_size'] == 16 and settings['prefix_replicas'] == 32,
        reference_audits_pass=True, reference_rosters_and_costs=True, all_references_terminal=True,
        frozen_choice_binding_and_derived_events=True, new_scoring_and_no_learning_work_accounted=True)
    source = dict(games=0, roots=0, ground_work=Counter(), planning_counts=Counter(), outcomes=Counter(), seconds=0.)
    prefix = dict(trajectories=0, model_work=Counter(), planning_counts=Counter(), feature_counts=Counter(), outcomes=Counter(), seconds=0.)
    checks['source_history_execution_checks'] &= (len(run['histories']) == len(targets)
        and {history['life'] for history in run['histories']} == set(targets))
    acquired_ids = []
    for history in run['histories']:
        source_log, prefix_log = history['source_log'], history['prefix_log']
        acquired_ids.extend(root['root_id'] for root in history['roots'])
        checks['source_history_execution_checks'] &= bool(history['checks']) and all(history['checks'].values())
        checks['source_and_prefix_work_accounted'] &= (source_log['games'] == count * len(queries)
            and source_log['roots'] == len(history['roots']) and source_log['games'] == len(history['roots']) + len(history['missing_roots'])
            and sum(source_log['outcomes'].values()) == source_log['games']
            and source_log['ground_work'].get('environment_random_draws', 0) ==
                2 * source_log['ground_work'].get('sampled_transitions', 0) + 4 * source_log['games']
            and prefix_log['trajectories'] == len(history['roots']) * len(OPTIONS) * settings['prefix_replicas']
            and sum(prefix_log['outcomes'].values()) == prefix_log['trajectories']
            and 0 <= prefix_log['model_work'].get('synthetic_transitions', 0) <= prefix_log['trajectories'] * settings['horizon']
            and prefix_log['model_work'].get('spawn_uniform_draws', 0) == 2 * prefix_log['model_work'].get('synthetic_transitions', 0)
            and prefix_log['planning_counts'].get('model_uniform_draws', 0) == 4 * prefix_log['model_work'].get('synthetic_transitions', 0)
            and bool(prefix_log['wiring']) and all(prefix_log['wiring'].values()))
        for name in ('games', 'roots', 'seconds'):
            source[name] += source_log[name]
        for name in ('ground_work', 'planning_counts', 'outcomes'):
            source[name].update(source_log[name])
        for name in ('trajectories', 'seconds'):
            prefix[name] += prefix_log[name]
        for name in ('model_work', 'planning_counts', 'feature_counts', 'outcomes'):
            prefix[name].update(prefix_log[name])
    checks['source_history_execution_checks'] &= len(acquired_ids) == len(root_ids) and set(acquired_ids) == root_ids
    root_by_id = {root['root_id']: root for root in roots}
    references = dict(ground_work=Counter(), planning_counts=Counter(), outcomes=Counter(), trajectories=0, seconds=0.)
    metrics, missing = {}, []
    for root in roots:
        root_id, log = root['root_id'], root['reference_log']
        expected_source = 8300000 + (settings['source_life_base'] + root['life']) * 10000 + root['episode']
        expected_prefix = (settings['prefix_seed_base'] + root['life'] * 10000000
            + list(queries).index(root['query']) * 1000000 + root['episode'] * 1000)
        checks['fresh_root_streams_and_features_bound'] &= (settings['source_life_base'] == settings['reference_life_base'] == 113000
            and settings['prefix_seed_base'] == 253000000000 and root['source_seed'] == expected_source
            and root['prefix_seed'] == expected_prefix and len(root['features']) == len(OPTIONS)
            and all(len(vector) == settings['feature_dim'] for vector in root['features']))
        for name in ('ground_work', 'planning_counts', 'outcomes'):
            references[name].update(log[name])
        references['trajectories'] += log['trajectories']
        references['seconds'] += log['seconds']
        valid_audit = bool(root['reference_audit']) and all(root['reference_audit'].values())
        checks['reference_audits_pass'] &= valid_audit
        terminal = not log['censored_root'] and set(log['outcomes']) <= {'WON', 'LOST'}
        delta_complete = set(log['pair_deltas']) == set(OPTIONS[1:]) and all(
            len(log['pair_deltas'][option]) == replicas and all(len(vector) == 3 for vector in log['pair_deltas'][option])
            for option in OPTIONS[1:])
        checks['all_references_terminal'] &= terminal and root['reference_complete']
        checks['reference_rosters_and_costs'] &= (log['trajectories'] == replicas * len(OPTIONS)
            and sum(log['outcomes'].values()) == log['trajectories']
            and log['planning_counts'].get('model_uniform_draws', 0) == 4 * log['ground_work'].get('sampled_transitions', 0)
            and log['ground_work'].get('environment_random_draws', 0) == 2 * log['ground_work'].get('sampled_transitions', 0)
            and (delta_complete if terminal else not log['pair_deltas']))
        if not (terminal and delta_complete and valid_audit and root['reference_complete']):
            missing.append(root_id)
            continue
        for block, utilities in reference_values(log, root['query'], replicas).items():
            for bundle in bundles:
                for method in METHODS:
                    event = None if method == 'H2_ONLY' else decisions.get((root_id, bundle, method))
                    if method != 'H2_ONLY' and event is None:
                        continue
                    metrics[root_id, bundle, method, block] = event_metrics(event, utilities)
    scoring = run['scoring_log']
    bindings = {(row['bundle_id'], row['hidden'], row['query']): row for row in scoring['choices_binding']}
    checks['frozen_choice_binding_and_derived_events'] &= len(bindings) == len(scoring['choices_binding']) == len(expected_choices) and set(bindings) == expected_choices
    choice_counts = {str(hidden): {query: dict(HALF=0, FULL=0) for query in queries} for hidden in WIDTHS}
    for key, choice in choices.items():
        bundle, hidden, query = key
        sources = [life for life in bundles if life != bundle]
        selected_method = f"POOLED_H{hidden}_{choice['chosen_stage']}"
        chosen_metadata = inherited.get((bundle, selected_method))
        checks['frozen_source_choices_and_target_exclusion'] &= (choice['source_lives'] == sources
            and choice['chosen_method'] == selected_method and choice['chosen_stage'] in ('HALF', 'FULL')
            and chosen_metadata is not None and chosen_metadata['source_lives'] == sources
            and set(chosen_metadata['source_lives']).isdisjoint(targets))
        expected_binding = dict(bundle_id=bundle, hidden=hidden, query=query, source_lives=sources,
            chosen_stage=choice['chosen_stage'], chosen_method=choice['chosen_method'],
            chosen_model_path=chosen_metadata['path'] if chosen_metadata else None)
        checks['frozen_choice_binding_and_derived_events'] &= bindings.get(key) == expected_binding
        if choice['chosen_stage'] in ('HALF', 'FULL'):
            choice_counts[str(hidden)][query][choice['chosen_stage']] += 1
    learned = [row for row in run['decisions'] if row['method'] in BASE_METHODS]
    derived = [row for row in run['decisions'] if row['method'] in NEW_METHODS]
    for row in derived:
        root = root_by_id.get(row['root_id'])
        hidden = int(row['method'].split('H')[-1])
        choice = choices.get((row['bundle_id'], hidden, root['query'])) if root else None
        expected = decisions.get((row['root_id'], row['bundle_id'], choice['chosen_method'])) if choice else None
        chosen_metadata = inherited.get((row['bundle_id'], choice['chosen_method'])) if choice else None
        checks['frozen_choice_binding_and_derived_events'] &= (choice is not None and row['event'] == expected
            and row['chosen_method'] == choice['chosen_method'] and chosen_metadata is not None
            and row['chosen_model_path'] == chosen_metadata['path'] and row['target_life'] == root['life'])
    counts = scoring['counts']
    checks['new_scoring_and_no_learning_work_accounted'] = (bool(scoring['checks']) and all(scoring['checks'].values())
        and counts['model_payloads_loaded'] == len(run['models'])
        and counts['model_root_scores'] == len(learned) == len(run['models']) * len(roots)
        and counts['neural_candidate_predictions'] == len(learned) * len(OPTIONS)
        and counts['neural_hidden_activations'] == len(roots) * len(OPTIONS) * sum(row['metadata']['hidden'] for row in run['models'])
        and counts['derived_decisions'] == counts['cached_decision_lookups'] == len(derived) == len(roots) * len(bundles) * len(WIDTHS)
        and all(row['target_life'] == root_by_id[row['root_id']]['life'] for row in run['decisions'])
        and all(counts[key] == 0 for key in ('new_environment_transitions', 'new_synthetic_transitions',
            'neural_model_fits', 'optimizer_steps', 'model_prefix_trajectories'))
        and settings['new_neural_model_fits'] == settings['new_optimizer_steps'] == 0)
    methods, comparisons = summarize_metrics(metrics, roots, settings)
    for group, names in ((source, ('ground_work', 'planning_counts', 'outcomes')),
            (prefix, ('model_work', 'planning_counts', 'feature_counts', 'outcomes')),
            (references, ('ground_work', 'planning_counts', 'outcomes'))):
        for name in names:
            group[name] = dict(group[name])
    complete = all(value for name, value in checks.items() if name != 'all_references_terminal')
    return dict(schema='acfqp.fresh_targets_analysis.v113', complete=complete,
        primary_complete=complete and checks['all_references_terminal'] and not missing, checks=checks,
        cohort=dict(fresh_target_histories=targets, frozen_source_bundles=bundles,
            unique_reference_roots=len(roots), fresh_reference_trajectories=references['trajectories'],
            new_model_root_decisions=len(learned), derived_decisions=len(derived),
            missing_trigger_roots=run['cohort']['missing_roots'], missing_or_censored_reference_roots=missing),
        methods=methods, comparisons=comparisons, frozen_choice_counts=choice_counts,
        actual_executed_work=dict(newly_sampled_environment_transitions=source['ground_work'].get('sampled_transitions', 0)
                + references['ground_work'].get('sampled_transitions', 0),
            new_h2_source_transitions=source['ground_work'].get('sampled_transitions', 0),
            new_reference_transitions=references['ground_work'].get('sampled_transitions', 0),
            new_model_prefix_transitions=prefix['model_work'].get('synthetic_transitions', 0),
            new_model_prefix_trajectories=prefix['trajectories'], new_source_games=source['games'],
            source_games_with_cutoff=source['outcomes'].get('CUTOFF', 0),
            new_neural_model_fits=counts['neural_model_fits'], new_optimizer_steps=counts['optimizer_steps'],
            new_selection_decisions=0, new_neural_candidate_predictions=counts['neural_candidate_predictions'],
            new_model_root_decisions=counts['model_root_scores'], derived_decisions=counts['derived_decisions'],
            scoring_counts=counts, new_source_work=source, new_prefix_work=prefix, new_reference_work=references,
            source_seconds=source['seconds'], prefix_seconds=prefix['seconds'], reference_worker_seconds=references['seconds'],
            scoring_seconds=scoring['seconds'], actual_wall_seconds=run['actual_wall_seconds']),
        inherited_total_work=run['inherited_work'],
        inherited_selection_acquisition_accounting=run['inherited_selection_acquisition_accounting'],
        inherited_cohort_extraction_work=run['inherited_cohort_extraction_work'],
        evidence_scope='The V112 source models and sixteen query choices remain fixed before fresh target references are '
            'sampled. Four frozen three-source bundles cross the same four new target histories; each cell equally weights '
            'its eight query roots and both matrix axes have equal weights. New targets and suffix streams provide fresh '
            'evaluation evidence, not new independently trained learners. The source bundles share histories and all bundles '
            'share target references, so cells are not independent replicates. H2 source games are fully charged; a source '
            'CUTOFF after a valid trigger does not invalidate its root. A censored terminal reference preserves costs and '
            'blocks every affected matrix mean. Prefix model work is separate from real environment transitions. Source '
            'training and selection-validation costs remain inherited; no fitting, selection or threshold adjustment uses '
            'new target results. A/B16 partition the fixed pool32. This evaluates retained first-trigger choices, not full '
            'closed-loop return under repeated learned choices and not a new scientific Gate.')


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
