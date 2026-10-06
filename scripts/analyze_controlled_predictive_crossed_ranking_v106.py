"""Cross frozen training histories with a common bank of retained decision roots."""
from collections import Counter
import argparse
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'src'))
from acfqp.science.controlled_predictive_fragments_v83 import OPTIONS
from scripts.analyze_controlled_predictive_query_ranking_v100 import ranking_error
from scripts.analyze_controlled_predictive_natural_reference_v104 import reference_values
from scripts.analyze_controlled_predictive_fresh_ranking_v105 import METHODS, CONTRASTS

LEARNED = METHODS[2:]
BLOCKS = ('pooled', 'A', 'B')
FIELDS = ('selected_reference_utility', 'selected_reference_regret', 'pairwise_weighted_error')
ZERO_DATA = ('new_environment_transitions', 'new_synthetic_transitions', 'neural_model_fits',
             'neural_candidate_predictions', 'new_selector_calls')


def mean(values):
    values = list(values)
    return math.fsum(values) / len(values) if values and all(value is not None for value in values) else None


def directions(values):
    values = [value for value in values if value is not None]
    return dict(positive=sum(value > 0 for value in values), negative=sum(value < 0 for value in values),
                zero=sum(value == 0 for value in values))


def matrix_summary(cells, training_lives, cohort_lives):
    """Equal-cell descriptive decomposition; missing cells never shrink the primary matrix."""
    if len(cells) != len(training_lives) or any(len(row) != len(cohort_lives) for row in cells):
        raise ValueError('Matrix dimensions must match the frozen history rosters')
    rows = [mean(row) for row in cells]
    columns = [mean(row[j] for row in cells) for j in range(len(cohort_lives))]
    grand = mean(rows)
    diagonal = [dict(life=life, value=cells[i][cohort_lives.index(life)])
        for i, life in enumerate(training_lives) if life in cohort_lives]
    result = dict(primary_estimable=grand is not None, training_lifecycles=training_lives,
        cohort_lifecycles=cohort_lives, cells=cells, row_means=rows, column_means=columns, grand_mean=grand,
        row_directions=directions(rows), column_directions=directions(columns),
        diagonal=dict(cells=diagonal, mean=mean(row['value'] for row in diagonal),
            directions=directions(row['value'] for row in diagonal)), decomposition=None)
    if grand is None:
        return result
    model = [value - grand for value in rows]
    cohort = [value - grand for value in columns]
    interaction = [[value - grand - model[i] - cohort[j] for j, value in enumerate(row)]
        for i, row in enumerate(cells)]
    sums = dict(total=math.fsum((value - grand) ** 2 for row in cells for value in row),
        model=len(cohort_lives) * math.fsum(value ** 2 for value in model),
        cohort=len(training_lives) * math.fsum(value ** 2 for value in cohort),
        interaction=math.fsum(value ** 2 for row in interaction for value in row))
    result['decomposition'] = dict(model_effects=model, cohort_effects=cohort, interaction=interaction,
        sum_of_squares=sums, shares={key: sums[key] / sums['total'] if sums['total'] else None
            for key in ('model', 'cohort', 'interaction')},
        identity_residual=sums['total'] - sums['model'] - sums['cohort'] - sums['interaction'])
    return result


def event_metrics(event, utilities):
    if event is None:
        return dict(selected_reference_utility=0., selected_reference_regret=max(utilities.values()),
                    pairwise_weighted_error=None)
    return ranking_error({option: event['predictions'][option]['value'] for option in OPTIONS},
                         utilities, event['option'])


def event_matches(left, right):
    return all(left[field] == right[field] for field in ('option', 'value', 'score_semantics')) and all(
        left['predictions'][option]['value'] == right['predictions'][option]['value'] for option in OPTIONS)


def analyze_run(run):
    settings, roots = run['settings'], run['cohort']['roots']
    data_log, scoring = run['cohort']['log'], run['scoring_log']
    training, cohorts = settings['training_lifecycles'], settings['lifecycles']
    count = settings['validation_roots_per_query']
    replicas = settings['reference_replicas']
    expected_roots = {(life, query, episode) for life in cohorts for query in settings['queries']
        for episode in range(count)}
    root_ids = {root['root_id'] for root in roots}
    root_lives = {root['root_id']: root['life'] for root in roots}
    decisions = {(row['root_id'], row['training_life'], row['method']): row['event'] for row in run['decisions']}
    expected_decisions = {(root_id, life, method) for root_id in root_ids for life in training for method in LEARNED}
    expected_models = {(life, method) for life in training for method in LEARNED}
    checks = dict(run_terminal=run['status'] == 'complete',
        source_extraction_checks=bool(data_log['checks']) and all(value is True for value in data_log['checks'].values()),
        frozen_recipe_rosters=settings['methods'] == list(METHODS) and settings['contrasts'] == [list(pair) for pair in CONTRASTS]
            and len(set(training)) == len(training) == len(cohorts) and set(training) == set(cohorts),
        full_crossed_root_roster=len(root_ids) == len(roots) == len(expected_roots) and
            {(root['life'], root['query'], root['episode']) for root in roots} == expected_roots,
        full_frozen_model_roster=len(run['models']) == len(expected_models) and
            {(row['training_life'], row['method']) for row in run['models']} == expected_models,
        full_decision_roster=len(run['decisions']) == len(decisions) == len(expected_decisions)
            and set(decisions) == expected_decisions,
        scoring_checks=bool(scoring['checks']) and all(value is True for value in scoring['checks'].values()),
        fixed_reference_blocks=replicas == 32 and settings['reference_block_size'] == 16,
        no_new_data_sampling_or_fitting=all(data_log['counts'][key] == 0 for key in ZERO_DATA),
        original_prediction_rosters=True, frozen_diagonal_matches=True, reference_audits_pass=True,
        reference_rosters_and_costs=True, all_references_terminal=True)
    work = dict(ground_work=Counter(), planning_counts=Counter(), outcomes=Counter(), trajectories=0, seconds=0.)
    metric_rows, original_rows, missing = {}, {}, []
    root_counts = [[sum(root['life'] == cohort and root['query'] == query for root in roots)
        for cohort in cohorts] for query in settings['queries']]
    for root in roots:
        root_id, log = root['root_id'], root['reference_log']
        for name in ('ground_work', 'planning_counts', 'outcomes'):
            work[name].update(log[name])
        work['trajectories'] += log['trajectories']
        work['seconds'] += log['seconds']
        original = root['original_predictions']
        checks['original_prediction_rosters'] &= set(original) == set(METHODS[1:])
        audit = root['reference_audit']
        valid_audit = bool(audit) and all(value is True for value in audit.values())
        checks['reference_audits_pass'] &= valid_audit
        delta_complete = set(log['pair_deltas']) == set(OPTIONS[1:]) and all(
            len(log['pair_deltas'][option]) == replicas and all(len(vector) == 3 for vector in log['pair_deltas'][option])
            for option in OPTIONS[1:])
        terminal = not log['censored_root'] and set(log['outcomes']) <= {'WON', 'LOST'}
        checks['all_references_terminal'] &= terminal and root['reference_complete']
        checks['reference_rosters_and_costs'] &= (log['trajectories'] == replicas * len(OPTIONS)
            and sum(log['outcomes'].values()) == log['trajectories']
            and log['planning_counts'].get('model_uniform_draws', 0) == 4 * log['ground_work'].get('sampled_transitions', 0)
            and (delta_complete if terminal else not log['pair_deltas']))
        for method in LEARNED:
            event = decisions.get((root_id, root['life'], method))
            checks['frozen_diagonal_matches'] &= event is not None and event_matches(event, original[method])
        if not (terminal and delta_complete and valid_audit and root['reference_complete']):
            missing.append(root_id)
            continue
        values = reference_values(log, root['query'], replicas)
        for block, utility in values.items():
            for method in METHODS:
                original_rows[root_id, method, block] = event_metrics(None if method == 'H2_ONLY' else original[method], utility)
                for life in training:
                    if method == 'H2_ONLY':
                        event = None
                    elif method == 'PREFIX_ONLY_DIRECT':
                        event = original[method]
                    else:
                        event = decisions.get((root_id, life, method))
                        if event is None:
                            continue
                    metric_rows[root_id, life, method, block] = event_metrics(event, utility)
    for name in ('ground_work', 'planning_counts', 'outcomes'):
        work[name] = dict(work[name])

    def summarize(method, query, block, field, right=None, original=False):
        cells = []
        for train_life in training:
            row = []
            for cohort in cohorts:
                group = [root for root in roots if root['life'] == cohort and root['query'] == query]
                values = []
                for root in group:
                    key = ((root['root_id'], method, block) if original else (root['root_id'], train_life, method, block))
                    source = original_rows if original else metric_rows
                    value = source.get(key, {}).get(field)
                    if right is not None:
                        other_key = ((root['root_id'], right, block) if original else (root['root_id'], train_life, right, block))
                        other = source.get(other_key, {}).get(field)
                        value = value - other if value is not None and other is not None else None
                    values.append(value)
                row.append(mean(values) if len(group) == count else None)
            cells.append(row)
        return matrix_summary(cells, training, cohorts)

    methods = {method: {query: {block: {field: summarize(method, query, block, field) for field in FIELDS}
        for block in BLOCKS} for query in settings['queries']} for method in METHODS}
    comparisons = {}
    for left, right in settings['contrasts']:
        comparisons[left + '_minus_' + right] = {query: {block: {
            'selected_utility_delta': summarize(left, query, block, 'selected_reference_utility', right),
            'pairwise_weighted_error_delta': summarize(left, query, block, 'pairwise_weighted_error', right),
            'original_v105_diagonal': summarize(left, query, block, 'selected_reference_utility', right,
                original=True)['diagonal']} for block in BLOCKS} for query in settings['queries']}
    checks['diagonal_reference_values_match'] = all(
        row['selected_utility_delta']['diagonal'] == row['original_v105_diagonal']
        for by_query in comparisons.values() for by_block in by_query.values() for row in by_block.values())
    complete = all(value for key, value in checks.items() if key != 'all_references_terminal')
    costs = scoring['counts']
    checks['no_new_scoring_sampling_or_fitting'] = all(costs[key] == 0 for key in
        ('new_environment_transitions', 'new_synthetic_transitions', 'neural_model_fits', 'optimizer_steps', 'model_prefix_trajectories'))
    checks['new_scoring_work_accounted'] = (costs['model_payloads_loaded'] == len(run['models'])
        and costs['model_root_scores'] == len(run['decisions'])
        and costs['diagonal_model_root_scores'] == sum(row['training_life'] == root_lives.get(row['root_id'])
            for row in run['decisions'])
        and costs['neural_candidate_predictions'] == len(run['decisions']) * len(OPTIONS)
        and costs['neural_hidden_activations'] == len(roots) * len(OPTIONS)
            * sum(row['metadata']['hidden'] for row in run['models']))
    complete &= checks['no_new_scoring_sampling_or_fitting'] and checks['new_scoring_work_accounted']
    return dict(schema='acfqp.crossed_ranking_analysis.v106', complete=complete,
        primary_complete=complete and checks['all_references_terminal'] and not missing, checks=checks,
        cohort=dict(unique_reference_roots=len(roots), inherited_reference_trajectories=work['trajectories'],
            newly_scored_model_root_decisions=len(run['decisions']), root_counts_by_query_and_cohort=root_counts,
            queries=settings['queries'], cohort_lifecycles=cohorts, missing_or_censored_reference_roots=missing),
        methods=methods, comparisons=comparisons,
        actual_executed_work=dict(newly_sampled_environment_transitions=data_log['counts']['new_environment_transitions']
                + costs['new_environment_transitions'],
            new_model_prefix_transitions=data_log['counts']['new_synthetic_transitions'] + costs['new_synthetic_transitions'],
            new_neural_model_fits=data_log['counts']['neural_model_fits'] + costs['neural_model_fits'],
            new_optimizer_steps=costs['optimizer_steps'], new_neural_candidate_predictions=costs['neural_candidate_predictions'],
            new_model_root_decisions=costs['model_root_scores'],
            scoring_counts=costs, cohort_extraction_counts=data_log['counts'],
            cohort_extraction_seconds=data_log['seconds'], scoring_seconds=scoring['seconds'],
            actual_wall_seconds=run['actual_wall_seconds']),
        inherited_reference_work=work, inherited_v105_total_work=run['inherited_v105_work'],
        evidence_scope='Each method and contrast uses equal root weights within each model-history by root-cohort cell, '
            'then equal histories on both axes. Pool32 is primary; A/B16 remain descriptive. Row effects, column effects '
            'and interaction are a balanced decomposition of the retained cell means, without inferential p-values '
            'or causal identification. The 64 reference roots and their 10240 trajectories are reused once as old '
            'evidence; 1024 rescored model-root decisions are not 1024 independent reference samples. Inherited '
            'reference work is a subset of the V105 total, not an additional charge. No crossed natural trajectories '
            'are observed or inferred. Missing/censored roots preserve the frozen roster and costs while making '
            'affected full-matrix estimates unavailable. No refitting, checkpoint selection or new scientific Gate.')


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
