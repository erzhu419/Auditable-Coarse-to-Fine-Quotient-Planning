"""Fixed heldout order replication; finite references remain descriptive estimates."""
from collections import Counter
import argparse
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from acfqp.science.controlled_predictive_fragments_v83 import OPTIONS, QUERIES, _utility

FAMILIES = ('UTILITY_MSE', 'PAIRWISE_RANK')
METHODS = FAMILIES + ('PREFIX_ONLY', 'OLD_LABEL_ARGMAX', 'H2_ONLY')
REFERENCES = ('A', 'B', 'pooled')
SUBSETS = ('all', 'stable', 'opposed', 'tied')
EXECUTION_CHECKS = ('trajectory_roster_complete', 'root_boards_match', 'paired_fresh_streams',
                    'committed_fragments_match', 'executed_costs_match')
ZERO_NEW_WORK = ('new_neural_model_fits', 'new_tree_fits', 'new_optimizer_steps',
                 'new_environment_transitions', 'new_model_transitions')
PAIRS = tuple((i, j) for i in range(5) for j in range(i + 1, 5))


def mean(values):
    values = [value for value in values if value is not None]
    return math.fsum(values) / len(values) if values else None


def sign(value):
    return int(value > 0) - int(value < 0)


def category(predicted, reference):
    return 'tie' if predicted == 0 else 'correct' if predicted * reference > 0 else 'opposite'


def pair_metrics(predicted, reference, pairs=PAIRS):
    """Reference ties contribute zero mass; predictor ties count half an error."""
    counts, error, mass, unweighted = Counter(), 0., 0., 0.
    for i, j in pairs:
        delta, score = reference[i] - reference[j], predicted[i] - predicted[j]
        counts['pairs'] += 1
        if delta == 0:
            counts['reference_ties'] += 1
            continue
        counts['reference_non_ties'] += 1
        error_value = .5 if score == 0 else float(score * delta < 0)
        counts[category(score, delta)] += 1
        error += abs(delta) * error_value
        mass += abs(delta)
        unweighted += error_value
    return dict(counts=dict(counts), error_mass=error, reference_mass=mass,
        pairwise_weighted_error=error / mass if mass else None,
        pairwise_unweighted_error=unweighted / counts['reference_non_ties']
            if counts['reference_non_ties'] else None)


def reference_means(log, size):
    result = {}
    for name, left, right in (('A', 0, size), ('B', size, 2 * size), ('pooled', 0, 2 * size)):
        result[name] = [0.] + [_utility([mean(row[k] for row in log['pair_deltas'][option][left:right])
            for k in range(3)], QUERIES[log['query']]) for option in OPTIONS[1:]]
    return result


def analyze_root(root, allocation, utilities):
    scores = {family: allocation['predictions'][family]['scores'] for family in FAMILIES}
    scores.update(PREFIX_ONLY=root['prefix_utilities'], OLD_LABEL_ARGMAX=allocation['old_utilities'],
                  H2_ONLY=[0.] * 5)
    choices = {family: OPTIONS.index(allocation['predictions'][family]['option']) for family in FAMILIES}
    choices.update({method: max(range(5), key=values.__getitem__) for method, values in scores.items()
                    if method not in FAMILIES})
    old = allocation['old_utilities']
    metadata = dict(root_id=root['id'], life=root['life'], replicas=allocation['replicas'], query=root['query'])
    by_subset = {name: [] for name in SUBSETS}
    pairs, cross = [], {family: Counter() for family in FAMILIES}
    cross_mass = {family: Counter() for family in FAMILIES}
    for i, j in PAIRS:
        da, db = utilities['A'][i] - utilities['A'][j], utilities['B'][i] - utilities['B'][j]
        kind = 'stable' if sign(da) == sign(db) != 0 else 'opposed' if da * db < 0 else 'tied'
        by_subset['all'].append((i, j))
        by_subset[kind].append((i, j))
        delta = utilities['pooled'][i] - utilities['pooled'][j]
        old_delta = old[i] - old[j]
        predicted = {method: values[i] - values[j] for method, values in scores.items()}
        pair = dict(metadata, options=[OPTIONS[i], OPTIONS[j]], stability=kind,
            old_delta=old_delta, reference_deltas=dict(A=da, B=db, pooled=delta), predicted_deltas=predicted)
        if kind == 'stable':
            pair['stable_cross'] = {}
            for family in FAMILIES:
                cell = f'old_{category(old_delta, delta)}_model_{category(predicted[family], delta)}'
                cross[family][cell] += 1
                cross_mass[family][cell] += abs(delta)
                pair['stable_cross'][family] = cell
        pairs.append(pair)
    metrics, subsets = {}, {}
    for reference, values in utilities.items():
        metrics[reference], subsets[reference] = {}, {}
        for method, predicted in scores.items():
            row = pair_metrics(predicted, values)
            row.update(selected_option=OPTIONS[choices[method]], selected_reference_utility=values[choices[method]],
                selected_finite_reference_best_gap=max(values) - values[choices[method]])
            if method in ('UTILITY_MSE', 'PREFIX_ONLY'):
                row['utility_mse'] = mean((score - value) ** 2 for score, value in zip(predicted, values))
            metrics[reference][method] = row
        for subset, selected in by_subset.items():
            subsets[reference][subset] = {method: pair_metrics(predicted, values, selected)
                for method, predicted in scores.items()}
    return dict(metadata, reference_utilities=utilities, stability_counts={k: len(v) for k, v in by_subset.items()},
        metrics=metrics, subsets=subsets, stable_cross={family: dict(cross[family]) for family in FAMILIES},
        stable_cross_mass={family: dict(cross_mass[family]) for family in FAMILIES}), pairs


def aggregate_metrics(rows):
    counts = Counter()
    for row in rows:
        counts.update(row['counts'])
    error, mass = (math.fsum(row[key] for row in rows) for key in ('error_mass', 'reference_mass'))
    result = dict(root_records=len(rows), counts=dict(counts), error_mass=error, reference_mass=mass,
        mean_root_weighted_error=mean(row['pairwise_weighted_error'] for row in rows),
        roots_with_nonzero_reference_mass=sum(row['reference_mass'] > 0 for row in rows),
        mean_root_unweighted_error=mean(row['pairwise_unweighted_error'] for row in rows),
        pooled_pair_weighted_error=error / mass if mass else None)
    for field in ('selected_reference_utility', 'selected_finite_reference_best_gap', 'utility_mse'):
        if rows and field in rows[0]:
            result['mean_' + field] = mean(row[field] for row in rows)
    return result


def aggregate_roots(rows):
    return dict(roots=len(rows),
        metrics={reference: {method: aggregate_metrics([row['metrics'][reference][method] for row in rows])
            for method in METHODS} for reference in REFERENCES},
        subsets={reference: {subset: {method: aggregate_metrics([row['subsets'][reference][subset][method]
            for row in rows]) for method in METHODS} for subset in SUBSETS} for reference in REFERENCES},
        stability_counts={name: sum(row['stability_counts'][name] for row in rows) for name in SUBSETS},
        stable_cross={family: dict(sum((Counter(row['stable_cross'][family]) for row in rows), Counter()))
            for family in FAMILIES},
        stable_cross_mass={family: dict(sum((Counter(row['stable_cross_mass'][family]) for row in rows), Counter()))
            for family in FAMILIES})


def equal_history_metrics(rows):
    fields = ('mean_root_weighted_error', 'mean_root_unweighted_error', 'mean_selected_reference_utility',
              'mean_selected_finite_reference_best_gap', 'mean_utility_mse')
    return {field: mean(row[field] for row in rows) for field in fields if rows and field in rows[0]}


def equal_histories(groups):
    return dict(histories=len(groups), metrics={reference: {method: equal_history_metrics(
        [group['metrics'][reference][method] for group in groups]) for method in METHODS} for reference in REFERENCES},
        subsets={reference: {subset: {method: equal_history_metrics(
            [group['subsets'][reference][subset][method] for group in groups]) for method in METHODS}
            for subset in SUBSETS} for reference in REFERENCES})


def analyze_run(run):
    settings, roots, references = run['settings'], run['cohort']['roots'], run['references']
    size, replicas = settings['block_size'], settings['replicas']
    cohort_counts = run['cohort']['log']['counts']
    indexed = {row['root_id']: row for row in references}
    ids = [root['id'] for root in roots]
    checks = dict(run_terminal=run['status'] == 'complete', fixed_root_ids_unique=len(set(ids)) == len(ids),
        reference_roster_complete=len(indexed) == len(references) == len(roots) and set(indexed) == set(ids),
        two_equal_reference_blocks=2 * size == replicas, heldout_roots_only=True,
        frozen_prediction_rosters=True, reference_trajectory_rosters=True,
        reference_work_accounted=True, reference_execution_wiring=True, reference_delta_rosters=True,
        frozen_cohort_without_new_learning_or_sampling=all(cohort_counts[key] == 0 for key in ZERO_NEW_WORK))
    work = {name: Counter() for name in ('ground_work', 'planning_counts', 'outcomes')}
    trajectories, complete_roots, total_allocations = 0, 0, 0
    root_rows, pair_rows, missing = [], [], []
    reference_status = []
    for root in roots:
        checks['heldout_roots_only'] &= root['episode'] % 5 == 4
        allocations = root['allocations']
        total_allocations += len(allocations)
        checks['frozen_prediction_rosters'] &= len({a['replicas'] for a in allocations}) == len(allocations)
        for allocation in allocations:
            checks['frozen_prediction_rosters'] &= (allocation['replicas'] in settings['allocations']
                and len(allocation['old_utilities']) == len(root['prefix_utilities']) == 5
                and set(allocation['predictions']) == set(FAMILIES))
            for family, prediction in allocation['predictions'].items():
                scores = prediction['scores']
                checks['frozen_prediction_rosters'] &= (len(scores) == 5 and scores[0] == 0
                    and prediction['option'] == OPTIONS[max(range(5), key=scores.__getitem__)]
                    and prediction['score_semantics'] == ('rank_score' if family == 'PAIRWISE_RANK' else 'utility_estimate'))
        if root['id'] not in indexed:
            missing.append(root['id'])
            continue
        record = indexed[root['id']]
        log = record['log']
        for name in work:
            work[name].update(log[name])
        trajectories += log['trajectories']
        checks['reference_trajectory_rosters'] &= log['trajectories'] == replicas * len(OPTIONS)
        checks['reference_work_accounted'] &= (sum(log['outcomes'].values()) == log['trajectories']
            and log['planning_counts'].get('model_uniform_draws', 0) == 4 * log['ground_work'].get('sampled_transitions', 0))
        checks['reference_execution_wiring'] &= all(record['checks'].get(key) is True for key in EXECUTION_CHECKS)
        terminal = not log['censored_root'] and set(log['outcomes']) <= {'WON', 'LOST'}
        delta_complete = set(log['pair_deltas']) == set(OPTIONS[1:]) and all(
            len(log['pair_deltas'][option]) == replicas and all(len(row) == 3 for row in log['pair_deltas'][option])
            for option in OPTIONS[1:])
        checks['reference_delta_rosters'] &= delta_complete if terminal else not log['pair_deltas']
        complete = terminal and delta_complete
        reference_status.append(dict(root_id=root['id'], complete=complete, outcomes=log['outcomes']))
        if not complete:
            missing.append(root['id'])
            continue
        complete_roots += 1
        utilities = reference_means(dict(log, query=root['query']), size)
        for allocation in allocations:
            row, pairs = analyze_root(root, allocation, utilities)
            root_rows.append(row)
            pair_rows.extend(pairs)
    groups = []
    for life in settings['lifecycles']:
        for allocation in settings['allocations']:
            for query in settings['queries']:
                expected = sum(root['life'] == life and root['query'] == query
                    and any(row['replicas'] == allocation for row in root['allocations']) for root in roots)
                selected = [row for row in root_rows if (row['life'], row['replicas'], row['query']) == (life, allocation, query)]
                available = aggregate_roots(selected)
                groups.append(dict(life=life, replicas=allocation, query=query, expected_roots=expected,
                    available=available, primary=available if len(selected) == expected and expected else None))
    across = []
    for allocation in settings['allocations']:
        for query in settings['queries']:
            selected = [group for group in groups if (group['replicas'], group['query']) == (allocation, query)]
            primary = all(group['primary'] is not None for group in selected)
            across.append(dict(replicas=allocation, query=query, lifecycles=settings['lifecycles'],
                primary=equal_histories([group['primary'] for group in selected]) if primary else None,
                available=equal_histories([group['available'] for group in selected if group['available']['roots']])))
    complete = all(checks.values())
    return dict(schema='acfqp.heldout_order_analysis.v101', complete=complete,
        primary_complete=complete and complete_roots == len(roots), checks=checks,
        cohort=dict(unique_roots=len(roots), allocated_root_records=total_allocations,
            shared_roots=sum(len(root['allocations']) > 1 for root in roots), complete_reference_roots=complete_roots,
            expected_allocated_pairs=total_allocations * len(PAIRS), analyzed_allocated_pairs=len(pair_rows),
            missing_or_censored_root_ids=missing),
        reference_status=reference_status, per_root=root_rows, pairs=pair_rows,
        groups=groups, across_lifecycles=across,
        actual_executed_work=dict(reference_trajectories=trajectories,
            newly_sampled_environment_transitions=work['ground_work'].get('sampled_transitions', 0),
            reference_work={name: dict(value) for name, value in work.items()},
            new_training_environment_transitions=cohort_counts['new_environment_transitions'],
            new_model_transitions=cohort_counts['new_model_transitions'],
            new_model_fits=cohort_counts['new_neural_model_fits'] + cohort_counts['new_tree_fits'],
            new_neural_model_fits=cohort_counts['new_neural_model_fits'],
            new_tree_fits=cohort_counts['new_tree_fits'], new_optimizer_steps=cohort_counts['new_optimizer_steps'],
            frozen_cohort_work=run['cohort']['log'], actual_wall_seconds=run.get('actual_wall_seconds')),
        interpretation='Two histories only. All roots and ten candidate pairs remain retained. Stable means two finite '
            'independent 16-replica mean differences have the same nonzero sign; it is not a truth or confidence claim. '
            'Primary errors average roots within each history, then histories equally. Pooled pair ratios are descriptive. '
            'Overlapping R4/R8 roots share one reference acquisition and are not independent replications. '
            'Cross categories describe errors against finite references and do not causally identify label noise. '
            'No refit, new prefix simulation, efficacy interval, or scientific Gate.')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('directory', type=Path)
    args = parser.parse_args()
    result = analyze_run(json.loads((args.directory / 'run.json').read_text()))
    (args.directory / 'analysis.json').write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps(dict(complete=result['complete'], primary_complete=result['primary_complete'],
                         checks=result['checks'], cohort=result['cohort']), allow_nan=False))


if __name__ == '__main__':
    main()
