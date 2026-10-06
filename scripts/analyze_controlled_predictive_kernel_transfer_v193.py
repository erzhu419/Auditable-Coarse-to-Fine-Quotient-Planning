"""Independent retained-model coverage, contribution and cohort reconstruction."""
import argparse
from collections import Counter
import json
import math
from pathlib import Path
from time import perf_counter

PROJECT = Path(__file__).resolve().parents[1]
OUTPUT = PROJECT/'reports/controlled_predictive_kernel_transfer_v193'
SCHEMA = 'acfqp.kernel_transfer.v193'
ACTIONS, EPS, COLUMNS = ('DOWN', 'LEFT', 'RIGHT', 'UP'), 1e-12, 98
BLOCKS = (('aggregate', 0, 6), ('rank_nodes', 6, 15), ('rank_pairs', 15, 48),
    ('value_nodes', 48, 57), ('value_pairs', 57, 90), ('vacancy', 90, 98))
METRICS = ('independent_distance', 'max_individual_distance', 'joint_distance', 'coupling_excess', 'block_coupling_excess')
ZERO_WORK = ('new_predictors_fitted', 'new_learning_attempts', 'new_linear_solves', 'new_eigen_decompositions',
    'new_svd_decompositions', 'new_feature_derivations', 'new_source_games', 'new_boards_generated',
    'new_reference_kernels', 'new_exact_label_roots', 'new_environment_samples', 'new_native_weight_updates', 'source_model_predictions')


def utility(vector):
    return vector[0]-vector[1]+vector[2]


def gap(first, second):
    components = [first[k]-second[k] for k in range(3)]
    return dict(components=components, utility=utility(components))


def tail(root, action, vectors):
    return [vectors[action][0]-root['immediate_rewards'][action], *vectors[action][1:]]


def close(actual, expected):
    if isinstance(expected, dict):
        return isinstance(actual, dict) and set(actual) == set(expected) and all(close(actual[key], value) for key, value in expected.items())
    if isinstance(expected, list):
        return isinstance(actual, list) and len(actual) == len(expected) and all(close(a, b) for a, b in zip(actual, expected, strict=True))
    if isinstance(expected, float):
        return isinstance(actual, (int, float)) and abs(actual-expected) <= 1e-8*(1.+abs(expected))
    return actual == expected


def distance_cache(root, centers, cohort, counts):
    result = {}
    for action in ACTIONS:
        if action not in root['legal_actions']:
            continue
        vector = root['relation_features'][action]; rows = []
        for center in centers:
            squares = [(vector[k]-center['features'][k])**2 for k in range(COLUMNS)]
            rows.append(dict(full=sum(squares), blocks={name: sum(squares[start:end]) for name, start, end in BLOCKS}))
        result[action] = rows
    q = len(result)*len(centers)
    counts.update({cohort+'_distance_pairs': q})
    counts.update(distance_coordinate_subtractions=COLUMNS*q, distance_coordinate_squares=COLUMNS*q,
        distance_component_addends=COLUMNS*q, block_distance_addends=COLUMNS*q, block_distance_sums=6*q)
    return result


def center_metadata(centers, index):
    center = centers[index]
    return dict(index=index, root_id=center['root_id'], source_id=center['source_id'], action=center['action'])


def pair_coverage(cache, actions, centers, grouped_centers, median, exclude_source, counts):
    first, second = actions
    eligible = [index for index, center in enumerate(centers) if center['source_id'] != exclude_source]
    nearest = [min(eligible, key=lambda index: (cache[action][index]['full'], index)) for action in actions]
    d_first, d_second = (cache[action][index]['full'] for action, index in zip(actions, nearest, strict=True))
    candidates = [(i, j) for indices in grouped_centers.values() for i in indices for j in indices
        if i != j and centers[i]['source_id'] != exclude_source]
    best = min(candidates, key=lambda pair: (cache[first][pair[0]]['full']+cache[second][pair[1]]['full'], *pair))
    joint = (cache[first][best[0]]['full']+cache[second][best[1]]['full'])/(2.*median)
    blocks = {name: min(cache[first][i]['blocks'][name]+cache[second][j]['blocks'][name] for i, j in candidates)/(2.*median)
        for name, _, _ in BLOCKS}
    joint_blocks = {name: (cache[first][best[0]]['blocks'][name]+cache[second][best[1]]['blocks'][name])/(2.*median)
        for name, _, _ in BLOCKS}
    independent = (d_first+d_second)/(2.*median)
    counts.update(independent_center_checks=2*len(eligible), candidate_pair_checks=len(candidates), candidate_block_checks=6*len(candidates))
    return dict(independent_distance=independent, max_individual_distance=max(d_first, d_second)/median,
        joint_distance=joint, coupling_excess=joint-independent, block_coupling_excess=joint-sum(blocks.values()),
        block_min_distances=blocks, joint_block_distances=joint_blocks,
        independent_nearest_centers=[center_metadata(centers, index) for index in nearest],
        nearest_source_pair=[center_metadata(centers, index) for index in best])


def quantiles(values):
    ordered = sorted(values); n = len(values)
    return dict(n=n, q50=ordered[math.ceil(.5*n)-1], q95=ordered[math.ceil(.95*n)-1], max=ordered[-1])


def build_reference(source, centers, groups, median, counts):
    records = []
    for root in source:
        cache = distance_cache(root, centers, 'source', counts)
        legal = [action for action in ACTIONS if action in root['legal_actions']]
        for first in legal:
            for second in legal:
                if first == second:
                    continue
                coverage = pair_coverage(cache, [first, second], centers, groups, median, root['source_id'], counts)
                records.append(dict(root_id=root['root_id'], source_id=root['source_id'], actions=[first, second],
                    **{name: coverage[name] for name in METRICS}, block_min_distances=coverage['block_min_distances']))
                counts['source_reference_pairs'] += 1
    counts['reference_quantile_values'] += 11*len(records)
    return dict(records=records, metrics={name: quantiles([row[name] for row in records]) for name in METRICS},
        block_metrics={name: quantiles([row['block_min_distances'][name] for row in records]) for name, _, _ in BLOCKS})


def add_reference(coverage, reference, counts):
    n = len(reference['records'])
    coverage['percentiles'] = {name: sum(row[name] <= coverage[name]+EPS for row in reference['records'])/n for name in METRICS}
    coverage['block_percentiles'] = {name: sum(row['block_min_distances'][name] <= coverage['block_min_distances'][name]+EPS
        for row in reference['records'])/n for name, _, _ in BLOCKS}
    coverage['endpoint_outlier'] = coverage['max_individual_distance'] > reference['metrics']['max_individual_distance']['q95']+EPS
    coverage['pair_outlier'] = coverage['joint_distance'] > reference['metrics']['joint_distance']['q95']+EPS
    coverage['composition_outlier'] = coverage['pair_outlier'] and not coverage['endpoint_outlier']
    coverage['block_composition_outlier'] = coverage['pair_outlier'] and all(coverage['block_min_distances'][name] <=
        reference['block_metrics'][name]['q95']+EPS for name, _, _ in BLOCKS)
    counts['target_percentile_comparisons'] += 11*n
    return coverage


def replay_predictions(model, root, cache, counts):
    predictions, kernels = {}, {}
    for action in ACTIONS:
        if action not in root['legal_actions']:
            continue
        kernels[action] = [math.exp(-model['gamma']*row['full']/model['median_squared_distance']) for row in cache[action]]
        vector = [sum(kernels[action][index]*model['coefficients'][index][k] for index in range(len(model['centers']))) for k in range(3)]
        vector[0] += root['immediate_rewards'][action]; predictions[action] = vector
    q = len(predictions)*len(model['centers'])
    counts.update(target_kernel_exponentials=q, target_prediction_component_products=3*q,
        target_reward_additions=len(predictions), target_replayed_roots=1)
    return predictions, kernels


def contributions(model, root, actions, kernels, predicted_gap, counts):
    a, b = actions; by_source = {}; centers = []; total = [0., 0., 0.]
    for index, center in enumerate(model['centers']):
        difference = kernels[a][index]-kernels[b][index]
        components = [difference*model['coefficients'][index][k] for k in range(3)]
        group = by_source.setdefault(center['source_id'], [0., 0., 0.])
        for k in range(3):
            total[k] += components[k]; group[k] += components[k]
        centers.append(dict(**center_metadata(model['centers'], index), components=components, utility=utility(components)))
    reconstructed = list(total); reconstructed[0] += root['immediate_rewards'][a]-root['immediate_rewards'][b]
    groups = [dict(source_id=source, components=components, utility=utility(components)) for source, components in sorted(by_source.items())]
    counts.update(target_contribution_component_products=3*len(centers), target_group_component_additions=3*len(centers),
        target_center_utility_evaluations=len(centers))
    return dict(summed_center_components=total, reconstructed_prediction_gap=reconstructed, groups=groups,
        top_centers=sorted(centers, key=lambda row: (-abs(row['utility']), row['index']))[:5],
        positive_utility_mass=sum(row['utility'] for row in centers if row['utility'] > 0.),
        negative_utility_mass=sum(row['utility'] for row in centers if row['utility'] < 0.),
        matches_prediction_gap=all(abs(a-b) <= 1e-8*(1.+abs(b)) for a, b in zip(reconstructed, predicted_gap['components'], strict=True)))


def bind_retained(model, roots, choices, labels, previous, source_diagnostics, counts):
    source = {root['root_id']: root for root in roots['SOURCE']}
    expected = [(root['root_id'], action) for root in sorted(roots['SOURCE'], key=lambda row: row['root_id'])
        for action in ACTIONS if action in root['legal_actions']]
    if [(center['root_id'], center['action']) for center in model['centers']] != expected:
        raise ValueError('saved center order differs from SOURCE actions')
    for center in model['centers']:
        root = source[center['root_id']]
        if center['source_id'] != root['source_id'] or center['features'] != root['relation_features'][center['action']]:
            raise ValueError('saved center does not bind to its original 98-coordinate cache')
    counts.update(center_bindings=len(expected), center_binding_feature_reads=196*len(expected))
    source_records = {row['root_id']: row for row in source_diagnostics['root_records']}
    if set(source_records) != set(source):
        raise ValueError('SOURCE diagnostic roster is incomplete')
    for root in roots['SOURCE']:
        saved = source_records[root['root_id']]; action = saved['action']
        if action not in root['legal_actions'] or saved['decision']['canonical_action'] != action or not close(
            saved['components'], root['action_components'][action]) or not close(saved['utility'], utility(root['action_components'][action])):
            raise ValueError('SOURCE retained outcome differs from its saved true vector')
    counts.update(source_diagnostic_bindings=len(source), source_binding_component_reads=6*len(source))
    selected = {row['root_id']: row for row in choices['NONLINEAR']}
    vectors = {row['root_id']: row['action_components'] for row in labels}
    previous_rows = {row['root_id']: row['models'] for row in previous['root_records']}
    target_ids = {root['root_id'] for root in roots['TARGET']}
    if any(set(index) != target_ids for index in (selected, vectors, previous_rows)):
        raise ValueError('TARGET retained decision, label or summary roster is incomplete')
    return source, selected, vectors, previous_rows


def target_records(model, targets, sources, selected, labels, previous, reference, groups, counts):
    centers = model['centers']; records = []
    for root in targets:
        root_id = root['root_id']; choice, vectors, old = selected[root_id], labels[root_id], previous[root_id]
        legal = [a for a in ACTIONS if a in root['legal_actions']]
        action, oracle, linear = choice['canonical_action'], old['ORACLE']['action'], old['LINEAR']['action']
        if action not in legal or oracle not in legal or linear not in legal or set(vectors) != set(legal):
            raise ValueError('TARGET actions and complete vectors must bind to legal actions')
        cache = distance_cache(root, centers, 'target', counts); predictions, kernels = replay_predictions(model, root, cache, counts)
        if choice['fallback']:
            replayed = root['fallback_action']
        else:
            replayed, best = legal[0], None
            for candidate in legal:
                value = utility(predictions[candidate])
                if best is None or value > best+EPS:
                    replayed, best = candidate, value
        actual = utility(vectors[action]); oracle_value = utility(vectors[oracle]); linear_value = utility(vectors[linear])
        regret, linear_regret = oracle_value-actual, oracle_value-linear_value
        error, linear_error = regret > EPS, linear_regret > EPS
        record = dict(root_id=root_id, source_id=root['source_id'], replica=root['replica'], stratum=root['stratum'],
            selected=action, oracle=oracle, challenger=None, pair_kind='forced' if len(legal) == 1 else None,
            actual_vectors={a: list(vectors[a]) for a in legal}, utility=actual, oracle_utility=oracle_value, regret=regret, error=error,
            LINEAR_action=linear, LINEAR_utility=linear_value, LINEAR_regret=linear_regret, LINEAR_utility_delta=actual-linear_value,
            new_error_vs_LINEAR=error and not linear_error, resolved_error_vs_LINEAR=linear_error and not error,
            prediction_vectors=predictions, replayed_action=replayed,
            replay_matches=replayed == action == old['NONLINEAR']['action'],
            predictions_match=close(predictions, choice['decision']['predicted_components']),
            true_gap=None, predicted_gap=None, immediate_gap=None, coverage=None, nearest_source_tail_gap=None,
            true_tail_gap=None, label_direction_reversed=False, exact_pair_label_conflict=False, contributions=None)
        counts.update(target_label_component_reads=3*len(legal), target_true_utility_evaluations=len(legal))
        if len(legal) > 1:
            if action != oracle:
                challenger, kind = action, 'oracle_vs_selected'
            else:
                candidates = [a for a in legal if a != oracle]; challenger = candidates[0]
                for candidate in candidates[1:]:
                    if utility(vectors[candidate]) > utility(vectors[challenger])+EPS:
                        challenger = candidate
                kind = 'oracle_vs_best_other'
            pair = [oracle, challenger]
            coverage = add_reference(pair_coverage(cache, pair, centers, groups, model['median_squared_distance'], None, counts), reference, counts)
            true_gap = gap(vectors[oracle], vectors[challenger]); predicted_gap = gap(predictions[oracle], predictions[challenger])
            true_tail = gap(tail(root, oracle, vectors), tail(root, challenger, vectors))
            nearest = coverage['nearest_source_pair']; nearest_root = sources[nearest[0]['root_id']]
            nearest_actions = [row['action'] for row in nearest]
            near_tail = gap(tail(nearest_root, nearest_actions[0], nearest_root['action_components']),
                tail(nearest_root, nearest_actions[1], nearest_root['action_components']))
            nearest_gap = dict(root_id=nearest_root['root_id'], source_id=nearest_root['source_id'], actions=nearest_actions, **near_tail)
            reversed_direction = abs(true_tail['utility']) > EPS and abs(near_tail['utility']) > EPS and true_tail['utility']*near_tail['utility'] < 0.
            conflict = coverage['joint_distance'] == 0. and any(abs(a-b) > EPS
                for a, b in zip(true_tail['components'], near_tail['components'], strict=True))
            record.update(challenger=challenger, pair_kind=kind, coverage=coverage, true_gap=true_gap, predicted_gap=predicted_gap,
                immediate_gap=root['immediate_rewards'][oracle]-root['immediate_rewards'][challenger], true_tail_gap=true_tail,
                nearest_source_tail_gap=nearest_gap, label_direction_reversed=reversed_direction, exact_pair_label_conflict=conflict,
                contributions=contributions(model, root, pair, kernels, predicted_gap, counts))
            counts['target_diagnostic_pairs'] += 1
        records.append(record)
    return records


def summarize(records, previous):
    subsets = dict(ALL=records, ERROR=[row for row in records if row['error']], CORRECT=[row for row in records if not row['error']],
        NEW_ERROR_VS_LINEAR=[row for row in records if row['new_error_vs_LINEAR']],
        RESOLVED_ERROR_VS_LINEAR=[row for row in records if row['resolved_error_vs_LINEAR']])
    def means(rows):
        pairs = [row for row in rows if row['coverage'] is not None]; n = len(rows)
        result = dict(n=n, pair_roots=len(pairs), mean_regret=math.fsum(row['regret'] for row in rows)/n if n else None,
            mean_LINEAR_utility_delta=math.fsum(row['LINEAR_utility_delta'] for row in rows)/n if n else None,
            coverage_means={name: math.fsum(row['coverage'][name] for row in pairs)/len(pairs) if pairs else None for name in METRICS},
            block_min_distance_means={name: math.fsum(row['coverage']['block_min_distances'][name] for row in pairs)/len(pairs) if pairs else None for name, _, _ in BLOCKS})
        for flag in ('endpoint_outlier', 'pair_outlier', 'composition_outlier', 'block_composition_outlier'):
            result[flag] = sum(row['coverage'][flag] for row in pairs)
        result.update(covered_pair_errors=sum(row['error'] and not row['coverage']['pair_outlier'] for row in pairs),
            covered_pair_label_reversals=sum(row['label_direction_reversed'] and not row['coverage']['pair_outlier'] for row in pairs),
            label_direction_reversed=sum(row['label_direction_reversed'] for row in pairs),
            exact_pair_label_conflict=sum(row['exact_pair_label_conflict'] for row in pairs))
        return result
    return dict(groups={name: means(rows) for name, rows in subsets.items()},
        primary_utility_deltas={'NONLINEAR_MINUS_'+name: previous['comparisons']['NONLINEAR_MINUS_'+name]['utility'] for name in ('LINEAR', 'RELATION', 'OLD_SHARED')},
        new_error_ids=[row['root_id'] for row in subsets['NEW_ERROR_VS_LINEAR']],
        resolved_error_ids=[row['root_id'] for row in subsets['RESOLVED_ERROR_VS_LINEAR']],
        largest_loss_id=min(records, key=lambda row: row['LINEAR_utility_delta'])['root_id'],
        largest_gain_id=max(records, key=lambda row: row['LINEAR_utility_delta'])['root_id'],
        replay_matches_all=all(row['replay_matches'] for row in records), predictions_match_all=all(row['predictions_match'] for row in records),
        contributions_match_all=all(row['contributions'] is None or row['contributions']['matches_prediction_gap'] for row in records))


def reconstruct(model, roots, choices, labels, previous, source_diagnostics):
    counts = Counter({key: 0 for key in ZERO_WORK})
    source, selected, vectors, previous_rows = bind_retained(model, roots, choices, labels, previous, source_diagnostics, counts)
    groups = {}
    for index, center in enumerate(model['centers']):
        groups.setdefault(center['root_id'], []).append(index)
    reference = build_reference(roots['SOURCE'], model['centers'], groups, model['median_squared_distance'], counts)
    records = target_records(model, roots['TARGET'], source, selected, vectors, previous_rows, reference, groups, counts)
    return dict(schema=SCHEMA, complete=True, parameters=dict(gamma=model['gamma'], lambda_value=model['constants']['lambda_value'],
        median_squared_distance=model['median_squared_distance'], feature_columns=COLUMNS, centers=len(model['centers']),
        source_roots=len(roots['SOURCE']), source_groups=len({root['source_id'] for root in roots['SOURCE']}), target_roots=len(roots['TARGET']),
        blocks={name: [start, end] for name, start, end in BLOCKS}, epsilon=EPS),
        reference=reference, root_records=records, summary=summarize(records, previous), costs=dict(counts))


def verify_reconstruction(saved, expected):
    checks = [dict(name=name, passed=close(saved[name], expected[name])) for name in
        ('parameters', 'reference', 'root_records', 'summary', 'costs')]
    checks.append(dict(name='actual_retained_action_prediction_and_contribution_bindings', passed=
        all(expected['summary'][name] for name in ('replay_matches_all', 'predictions_match_all', 'contributions_match_all'))))
    return checks


def analyze(directory):
    begun = perf_counter(); directory = Path(directory); io, checks = Counter(), []
    def read(relative):
        raw = (directory/relative).read_bytes(); io.update(json_read_operations=1, input_bytes_read=len(raw)); return json.loads(raw)
    def check(name, condition):
        checks.append(dict(name=name, passed=bool(condition)))
    run, inputs = read('run.json'), read('input_manifest.json')
    names = ('v192_stage_checks.json', 'run.json', 'model.json', 'roots.json', 'choices.json', 'labels.json',
        'summary.json', 'source_diagnostics.json')
    check('eight_protocol_frozen_retained_inputs', [(row['saved_ref'], row['phase']) for row in inputs] ==
        [(f'inputs/inherited/{name}', 'protocol_frozen') for name in names])
    for row in inputs:
        saved, original = (directory/row['saved_ref']).read_bytes(), Path(row['path']).read_bytes()
        io.update(input_byte_comparisons=1, input_comparison_bytes_read=len(saved)+len(original))
        check('retained_input:'+row['saved_ref'], saved == original and len(saved) == row['bytes'])
    stage, prior, model, roots, choices, labels, previous, source = [read('inputs/inherited/'+name) for name in names]
    check('settled_corrected_V192_complete', stage['valid'] and prior['status'] == 'complete')
    check('fixed_SOURCE143_36groups_TARGET96', len(roots['SOURCE']) == 143 and
        len({root['source_id'] for root in roots['SOURCE']}) == 36 and len(roots['TARGET']) == len(labels) == 96)
    check('frozen_gamma_lambda_and_98_column_model', model['gamma'] == 1. and
        model['constants']['lambda_value'] == .001 and model['constants']['columns'] == COLUMNS)
    expected = reconstruct(model, roots, choices, labels, previous, source); saved = read('diagnostics.json')
    checks.extend(verify_reconstruction(saved, expected))
    check('diagnostic_complete_schema_and_fixed_original_roster', saved['schema'] == expected['schema'] and saved['complete'] and
        [row['root_id'] for row in saved['root_records']] == [root['root_id'] for root in roots['TARGET']])
    check('all_actual_action_replays_match', all(row['replay_matches'] for row in expected['root_records']))
    check('all_actual_full_vector_predictions_match', all(row['predictions_match'] for row in expected['root_records']))
    check('all_center_contributions_match_direct_prediction_gap', all(row['contributions'] is None or
        row['contributions']['matches_prediction_gap'] for row in expected['root_records']))
    check('independent_nearest_rank_reference_retained_once', close(read('reference.json'), expected['reference']))
    check('complete_cohort_groups_flags_and_ID_summary', close(read('summary.json'), expected['summary']))
    check('all_paid_distance_pair_kernel_and_contribution_counts', run['costs']['diagnostics']['counts'] == expected['costs'])
    check('one_diagnostic_attempt_and_no_SOURCE_model_scores', run['diagnostic_attempts'] == 1 and run['diagnostic_complete'] and
        expected['costs']['source_model_predictions'] == 0)
    phases = [('protocol_frozen', 0), ('inputs_retained', 8), ('source_reference', 8), ('target_diagnostics', 8), ('complete', 8)]
    check('frozen_inputs_then_retention_milestones', [(row['phase'], row['input_reads']) for row in run['phase_history']] == phases)
    check('all_paid_input_counts', run['costs']['input_counts'] == dict(json_read_operations=8,
        input_bytes_read=sum(row['bytes'] for row in inputs), input_bytes_retained=sum(row['bytes'] for row in inputs)))
    zero = ('new_predictors_fitted', 'new_solve_attempts', 'new_eigen_decompositions', 'new_svd_decompositions',
        'new_feature_derivations', 'new_source_games', 'new_boards_generated', 'new_reference_kernels',
        'new_exact_label_roots', 'new_environment_samples', 'new_native_weight_updates')
    check('no_new_fit_solve_features_or_physical_observations', all(run[key] == 0 for key in zero) and
        all(expected['costs'][key] == 0 for key in ZERO_WORK))
    valid = all(row['passed'] for row in checks); complete = valid and run['status'] == 'complete' and expected['complete']
    return dict(schema=SCHEMA+'.analysis', valid=valid, complete=complete, primary_complete=complete,
        checks=checks, passed_checks=sum(row['passed'] for row in checks), total_checks=len(checks), summary=expected['summary'],
        costs=dict(independent_input_counts=dict(io), independent_diagnostic_counts=expected['costs'],
            new_environment_samples=0, independent_model_fits=0, independent_linear_solves=0, independent_eigen_solves=0,
            independent_svd_solves=0, independent_feature_derivations=0, independent_reference_kernels=0,
            source_model_predictions=0, original_run_costs=run['costs'], inherited_cost_refs=run['inherited_cost_refs'],
            test_refs=run['test_refs'], seconds=perf_counter()-begun))


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--directory', type=Path, default=OUTPUT)
    args = parser.parse_args(); result = analyze(args.directory)
    (args.directory/'analysis.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps(dict(valid=result['valid'], complete=result['complete'], passed=result['passed_checks'], total=result['total_checks'])))


if __name__ == '__main__':
    main()
