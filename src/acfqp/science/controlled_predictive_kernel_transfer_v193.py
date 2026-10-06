"""Retained V192 geometry, decision replay and shared-center contributions.

``diagnose`` returns parameters, SOURCE ordered-pair reference records/quantiles,
all TARGET root_records, five summary groups, and flat paid costs. Coverage uses
five scalar metrics and six fixed blocks; contributions retain group totals and
only the five largest absolute-utility centers. No SOURCE model is scored.
"""
from collections import Counter
from math import ceil, exp, fsum

from .controlled_predictive_consequence_partition_v172 import ACTIONS, EPSILON

SCHEMA = 'acfqp.kernel_transfer.v193'
COLUMNS = 98
BLOCKS = dict(aggregate=(0, 6), rank_nodes=(6, 15), rank_pairs=(15, 48),
              value_nodes=(48, 57), value_pairs=(57, 90), vacancy=(90, 98))
METRICS = ('independent_distance', 'max_individual_distance', 'joint_distance',
           'coupling_excess', 'block_coupling_excess')
GROUPS = ('ALL', 'ERROR', 'CORRECT', 'NEW_ERROR_VS_LINEAR', 'RESOLVED_ERROR_VS_LINEAR')
PRIMARY = ('LINEAR', 'RELATION', 'OLD_SHARED')
ZERO_WORK = ('new_predictors_fitted', 'new_learning_attempts', 'new_linear_solves',
             'new_eigen_decompositions', 'new_svd_decompositions', 'new_feature_derivations',
             'new_source_games', 'new_boards_generated', 'new_reference_kernels',
             'new_exact_label_roots', 'new_environment_samples', 'new_native_weight_updates',
             'source_model_predictions')


def utility(vector):
    return vector[0]-vector[1]+vector[2]


def gap(first, second):
    vector = [first[index]-second[index] for index in range(3)]
    return dict(components=vector, utility=utility(vector))


def _close(first, second):
    return all(abs(a-b) <= 1e-8*(1.+abs(b)) for a, b in zip(first, second, strict=True))


def _legal(root):
    return [action for action in ACTIONS if action in root['legal_actions']]


def _center_metadata(center, index):
    return dict(index=index, root_id=center['root_id'], source_id=center['source_id'], action=center['action'])


def _bind(model, source, target, choices, labels, previous_summary, source_diagnostics, costs):
    source_by_id = {root['root_id']: root for root in source}
    expected = [(root['root_id'], action) for root in sorted(source, key=lambda row: row['root_id'])
                for action in _legal(root)]
    if [(center['root_id'], center['action']) for center in model['centers']] != expected:
        raise ValueError('frozen SOURCE center order must match roots and canonical actions')
    for center in model['centers']:
        root = source_by_id[center['root_id']]
        if center['source_id'] != root['source_id'] or center['features'] != root['relation_features'][center['action']]:
            raise ValueError('frozen center must equal its SOURCE relation cache')
    costs.update(center_bindings=len(expected), center_binding_feature_reads=2*COLUMNS*len(expected))
    retained_source = {row['root_id']: row for row in source_diagnostics['root_records']}
    if set(retained_source) != set(source_by_id):
        raise ValueError('complete retained SOURCE diagnostics required')
    for root in source:
        row = retained_source[root['root_id']]
        action = row['action']
        if action not in root['legal_actions'] or row['decision']['canonical_action'] != action:
            raise ValueError('retained SOURCE decision must bind to a legal action')
        vector = root['action_components'][action]
        if not _close(row['components'], vector) or abs(row['utility']-utility(vector)) > 1e-8*(1.+abs(utility(vector))):
            raise ValueError('retained SOURCE outcome must bind to its exact vector')
    costs.update(source_diagnostic_bindings=len(source), source_binding_component_reads=6*len(source))
    target_ids = [root['root_id'] for root in target]
    choice_by_id = {row['root_id']: row for row in choices['NONLINEAR']}
    label_by_id = {row['root_id']: row for row in labels}
    previous_by_id = {row['root_id']: row for row in previous_summary['root_records']}
    if any(set(index) != set(target_ids) for index in (choice_by_id, label_by_id, previous_by_id)):
        raise ValueError('complete retained TARGET decisions, labels and summary required')
    return source_by_id, choice_by_id, label_by_id, previous_by_id


def _distances(root, centers, cohort, costs):
    full, blocks = {}, {}
    for action in _legal(root):
        values = root['relation_features'][action]
        if len(values) != COLUMNS:
            raise ValueError('fixed 98-column relation cache required')
        full[action], blocks[action] = [], []
        for center in centers:
            squares = [(values[index]-center['features'][index])**2 for index in range(COLUMNS)]
            full[action].append(sum(squares))
            blocks[action].append({name: sum(squares[first:last]) for name, (first, last) in BLOCKS.items()})
    pairs = len(_legal(root))*len(centers)
    costs.update({cohort+'_distance_pairs': pairs})
    costs.update(distance_coordinate_subtractions=COLUMNS*pairs, distance_coordinate_squares=COLUMNS*pairs,
        distance_component_addends=COLUMNS*pairs, block_distance_addends=COLUMNS*pairs,
        block_distance_sums=len(BLOCKS)*pairs)
    return full, blocks


def _candidates(centers, excluded_source=None):
    eligible, roots = [], {}
    for index, center in enumerate(centers):
        if center['source_id'] != excluded_source:
            eligible.append(index)
            roots.setdefault(center['root_id'], []).append(index)
    pairs = sorted((first, second) for ids in roots.values() for first in ids for second in ids if first != second)
    if not eligible or not pairs:
        raise ValueError('reference requires a different SOURCE group with two legal actions')
    return eligible, pairs


def _coverage(actions, distances, block_distances, centers, median, eligible, candidates, costs):
    first, second = actions
    # Explicit index tie-breaks retain the original SOURCE center order.
    a = min(eligible, key=lambda index: (distances[first][index], index))
    b = min(eligible, key=lambda index: (distances[second][index], index))
    joint = min(candidates, key=lambda pair: (distances[first][pair[0]]+distances[second][pair[1]], pair))
    best = {name: min(block_distances[first][i][name]+block_distances[second][j][name]
                     for i, j in candidates)/(2.*median) for name in BLOCKS}
    joint_blocks = {name: (block_distances[first][joint[0]][name]+block_distances[second][joint[1]][name])
                          /(2.*median) for name in BLOCKS}
    individual = (distances[first][a]+distances[second][b])/(2.*median)
    joint_distance = (distances[first][joint[0]]+distances[second][joint[1]])/(2.*median)
    costs.update(independent_center_checks=2*len(eligible), candidate_pair_checks=len(candidates),
                 candidate_block_checks=len(BLOCKS)*len(candidates))
    return dict(independent_distance=individual,
        max_individual_distance=max(distances[first][a], distances[second][b])/median,
        joint_distance=joint_distance, coupling_excess=joint_distance-individual,
        block_coupling_excess=joint_distance-sum(best.values()),
        block_min_distances=best, joint_block_distances=joint_blocks,
        independent_nearest_centers=[_center_metadata(centers[a], a), _center_metadata(centers[b], b)],
        nearest_source_pair=[_center_metadata(centers[joint[0]], joint[0]), _center_metadata(centers[joint[1]], joint[1])])


def _quantiles(values):
    ordered, n = sorted(values), len(values)
    return dict(n=n, q50=ordered[ceil(.5*n)-1], q95=ordered[ceil(.95*n)-1], max=ordered[-1])


def _reference(source, centers, median, costs):
    records = []
    for root in source:
        distances, blocks = _distances(root, centers, 'source', costs)
        eligible, candidates = _candidates(centers, root['source_id'])
        legal = _legal(root)
        for first in legal:
            for second in legal:
                if first == second:
                    continue
                coverage = _coverage([first, second], distances, blocks, centers, median, eligible, candidates, costs)
                records.append(dict(root_id=root['root_id'], source_id=root['source_id'], actions=[first, second],
                    **{metric: coverage[metric] for metric in METRICS}, block_min_distances=coverage['block_min_distances']))
                costs['source_reference_pairs'] += 1
    if not records:
        raise ValueError('SOURCE reference needs an ordered legal-action pair')
    costs['reference_quantile_values'] += (len(METRICS)+len(BLOCKS))*len(records)
    return dict(records=records,
        metrics={metric: _quantiles([row[metric] for row in records]) for metric in METRICS},
        block_metrics={name: _quantiles([row['block_min_distances'][name] for row in records]) for name in BLOCKS})


def _classify(coverage, reference, costs):
    n = len(reference['records'])
    coverage['percentiles'] = {metric: sum(row[metric] <= coverage[metric]+EPSILON
                                          for row in reference['records'])/n for metric in METRICS}
    coverage['block_percentiles'] = {name: sum(row['block_min_distances'][name] <= coverage['block_min_distances'][name]+EPSILON
                                               for row in reference['records'])/n for name in BLOCKS}
    endpoint = coverage['max_individual_distance'] > reference['metrics']['max_individual_distance']['q95']+EPSILON
    paired = coverage['joint_distance'] > reference['metrics']['joint_distance']['q95']+EPSILON
    block_covered = all(coverage['block_min_distances'][name] <= reference['block_metrics'][name]['q95']+EPSILON
                        for name in BLOCKS)
    coverage.update(endpoint_outlier=endpoint, pair_outlier=paired, composition_outlier=paired and not endpoint,
                    block_composition_outlier=paired and block_covered)
    costs['target_percentile_comparisons'] += (len(METRICS)+len(BLOCKS))*n


def _predictions(model, root, distances, choice, costs):
    kernels, predictions = {}, {}
    for action in _legal(root):
        kernels[action] = [exp(-model['gamma']*distance/model['median_squared_distance']) for distance in distances[action]]
        vector = [sum(kernels[action][index]*model['coefficients'][index][component]
                      for index in range(len(model['centers']))) for component in range(3)]
        vector[0] += root['immediate_rewards'][action]
        predictions[action] = vector
    if choice['fallback']:
        selected = root['fallback_action']
    else:
        selected, best = None, None
        for action in _legal(root):
            value = utility(predictions[action])
            if best is None or value > best+EPSILON:
                selected, best = action, value
    pairs = len(_legal(root))*len(model['centers'])
    costs.update(target_kernel_exponentials=pairs, target_prediction_component_products=3*pairs,
                 target_reward_additions=len(predictions), target_replayed_roots=1)
    saved = choice['decision']['predicted_components']
    matches = set(saved) == set(predictions) and all(_close(predictions[action], saved[action]) for action in predictions)
    return kernels, predictions, selected, matches


def _contributions(model, actions, kernels, immediate_gap, predicted_gap, costs):
    first, second = actions
    centers, coefficients = model['centers'], model['coefficients']
    rows, groups = [], {source: [0., 0., 0.] for source in sorted({center['source_id'] for center in centers})}
    for index, center in enumerate(centers):
        factor = kernels[first][index]-kernels[second][index]
        vector = [factor*coefficients[index][component] for component in range(3)]
        rows.append(dict(**_center_metadata(center, index), components=vector, utility=utility(vector)))
        for component in range(3):
            groups[center['source_id']][component] += vector[component]
    summed = [sum(row['components'][component] for row in rows) for component in range(3)]
    reconstructed = [summed[0]+immediate_gap, *summed[1:]]
    costs.update(target_contribution_component_products=3*len(centers),
                 target_group_component_additions=3*len(centers), target_center_utility_evaluations=len(centers))
    return dict(summed_center_components=summed, reconstructed_prediction_gap=reconstructed,
        groups=[dict(source_id=source, components=vector, utility=utility(vector)) for source, vector in groups.items()],
        top_centers=sorted(rows, key=lambda row: (-abs(row['utility']), row['index']))[:5],
        positive_utility_mass=sum(row['utility'] for row in rows if row['utility'] > 0.),
        negative_utility_mass=sum(row['utility'] for row in rows if row['utility'] < 0.),
        matches_prediction_gap=_close(reconstructed, predicted_gap['components']))


def _tail_gap(root, actions, vectors):
    first, second = actions
    first_tail = [vectors[first][0]-root['immediate_rewards'][first], *vectors[first][1:]]
    second_tail = [vectors[second][0]-root['immediate_rewards'][second], *vectors[second][1:]]
    return gap(first_tail, second_tail)


def _target_records(model, target, source_by_id, choice_by_id, label_by_id, previous_by_id, reference, costs):
    centers, median = model['centers'], model['median_squared_distance']
    eligible, candidates = _candidates(centers)
    records = []
    for root in target:
        root_id = root['root_id']
        choice, vectors, previous = choice_by_id[root_id], label_by_id[root_id]['action_components'], previous_by_id[root_id]['models']
        selected, oracle, linear = choice['canonical_action'], previous['ORACLE']['action'], previous['LINEAR']['action']
        legal = _legal(root)
        if selected not in legal or oracle not in legal or linear not in legal or set(vectors) != set(legal):
            raise ValueError('retained TARGET actions and complete vectors must bind to legal actions')
        distances, blocks = _distances(root, centers, 'target', costs)
        kernels, predictions, replayed, predictions_match = _predictions(model, root, distances, choice, costs)
        values = {action: utility(vectors[action]) for action in legal}
        actual_utility, oracle_utility, linear_utility = values[selected], values[oracle], values[linear]
        regret, linear_regret = oracle_utility-actual_utility, oracle_utility-linear_utility
        error, linear_error = regret > EPSILON, linear_regret > EPSILON
        record = dict(root_id=root_id, source_id=root['source_id'], replica=root['replica'], stratum=root['stratum'],
            selected=selected, oracle=oracle, challenger=None, pair_kind='forced' if len(legal) == 1 else None,
            actual_vectors={action: list(vectors[action]) for action in legal}, utility=actual_utility,
            oracle_utility=oracle_utility, regret=regret, error=error, LINEAR_action=linear,
            LINEAR_utility=linear_utility, LINEAR_regret=linear_regret,
            LINEAR_utility_delta=actual_utility-linear_utility,
            new_error_vs_LINEAR=error and not linear_error, resolved_error_vs_LINEAR=linear_error and not error,
            prediction_vectors=predictions, replayed_action=replayed,
            replay_matches=replayed == selected == previous['NONLINEAR']['action'], predictions_match=predictions_match,
            true_gap=None, predicted_gap=None, immediate_gap=None, coverage=None, nearest_source_tail_gap=None,
            true_tail_gap=None, label_direction_reversed=False, exact_pair_label_conflict=False, contributions=None)
        costs.update(target_label_component_reads=3*len(legal), target_true_utility_evaluations=len(legal))
        if len(legal) > 1:
            if selected != oracle:
                challenger, kind = selected, 'oracle_vs_selected'
            else:
                others = [action for action in legal if action != oracle]
                challenger, best = others[0], values[others[0]]
                for action in others[1:]:
                    value = values[action]
                    if value > best+EPSILON:
                        challenger, best = action, value
                kind = 'oracle_vs_best_other'
            actions = [oracle, challenger]
            coverage = _coverage(actions, distances, blocks, centers, median, eligible, candidates, costs)
            _classify(coverage, reference, costs)
            true_gap = gap(vectors[oracle], vectors[challenger])
            predicted_gap = gap(predictions[oracle], predictions[challenger])
            immediate = root['immediate_rewards'][oracle]-root['immediate_rewards'][challenger]
            true_tail = _tail_gap(root, actions, vectors)
            nearest = coverage['nearest_source_pair']
            nearest_root = source_by_id[nearest[0]['root_id']]
            nearest_actions = [row['action'] for row in nearest]
            nearest_gap = dict(root_id=nearest_root['root_id'], source_id=nearest_root['source_id'], actions=nearest_actions,
                               **_tail_gap(nearest_root, nearest_actions, nearest_root['action_components']))
            reversed_direction = abs(true_tail['utility']) > EPSILON and abs(nearest_gap['utility']) > EPSILON and true_tail['utility']*nearest_gap['utility'] < 0.
            conflict = coverage['joint_distance'] == 0. and any(abs(a-b) > EPSILON
                for a, b in zip(true_tail['components'], nearest_gap['components'], strict=True))
            record.update(challenger=challenger, pair_kind=kind, true_gap=true_gap, predicted_gap=predicted_gap,
                immediate_gap=immediate, coverage=coverage, nearest_source_tail_gap=nearest_gap,
                true_tail_gap=true_tail, label_direction_reversed=reversed_direction, exact_pair_label_conflict=conflict,
                contributions=_contributions(model, actions, kernels, immediate, predicted_gap, costs))
            costs['target_diagnostic_pairs'] += 1
        records.append(record)
    return records


def _summaries(records, previous_summary):
    subsets = dict(ALL=records, ERROR=[row for row in records if row['error']],
        CORRECT=[row for row in records if not row['error']],
        NEW_ERROR_VS_LINEAR=[row for row in records if row['new_error_vs_LINEAR']],
        RESOLVED_ERROR_VS_LINEAR=[row for row in records if row['resolved_error_vs_LINEAR']])
    def aggregate(rows):
        paired, n = [row for row in rows if row['coverage'] is not None], len(rows)
        return dict(n=n, pair_roots=len(paired),
            mean_regret=fsum(row['regret'] for row in rows)/n if n else None,
            mean_LINEAR_utility_delta=fsum(row['LINEAR_utility_delta'] for row in rows)/n if n else None,
            coverage_means={metric: fsum(row['coverage'][metric] for row in paired)/len(paired) if paired else None for metric in METRICS},
            block_min_distance_means={name: fsum(row['coverage']['block_min_distances'][name] for row in paired)/len(paired) if paired else None for name in BLOCKS},
            **{flag: sum(row['coverage'][flag] for row in paired) for flag in
                ('endpoint_outlier', 'pair_outlier', 'composition_outlier', 'block_composition_outlier')},
            covered_pair_errors=sum(row['error'] and not row['coverage']['pair_outlier'] for row in paired),
            covered_pair_label_reversals=sum(row['label_direction_reversed'] and not row['coverage']['pair_outlier'] for row in paired),
            label_direction_reversed=sum(row['label_direction_reversed'] for row in paired),
            exact_pair_label_conflict=sum(row['exact_pair_label_conflict'] for row in paired))
    return dict(groups={name: aggregate(subsets[name]) for name in GROUPS},
        primary_utility_deltas={'NONLINEAR_MINUS_'+name: previous_summary['comparisons']['NONLINEAR_MINUS_'+name]['utility'] for name in PRIMARY},
        new_error_ids=[row['root_id'] for row in subsets['NEW_ERROR_VS_LINEAR']],
        resolved_error_ids=[row['root_id'] for row in subsets['RESOLVED_ERROR_VS_LINEAR']],
        largest_loss_id=min(records, key=lambda row: row['LINEAR_utility_delta'])['root_id'],
        largest_gain_id=max(records, key=lambda row: row['LINEAR_utility_delta'])['root_id'],
        replay_matches_all=all(row['replay_matches'] for row in records),
        predictions_match_all=all(row['predictions_match'] for row in records),
        contributions_match_all=all(row['contributions'] is None or row['contributions']['matches_prediction_gap'] for row in records))


def diagnose(model, roots, choices, labels, previous_summary, source_diagnostics):
    """Describe frozen SOURCE coverage and every retained TARGET decision."""
    costs = Counter({key: 0 for key in ZERO_WORK})
    source, target = roots['SOURCE'], roots['TARGET']
    source_by_id, choice_by_id, label_by_id, previous_by_id = _bind(model, source, target, choices, labels, previous_summary, source_diagnostics, costs)
    reference = _reference(source, model['centers'], model['median_squared_distance'], costs)
    records = _target_records(model, target, source_by_id, choice_by_id, label_by_id, previous_by_id, reference, costs)
    return dict(schema=SCHEMA, complete=True,
        parameters=dict(gamma=model['gamma'], lambda_value=model['constants']['lambda_value'],
            median_squared_distance=model['median_squared_distance'], feature_columns=COLUMNS,
            centers=len(model['centers']), source_roots=len(source), source_groups=len({root['source_id'] for root in source}),
            target_roots=len(target), blocks={name: list(bounds) for name, bounds in BLOCKS.items()}, epsilon=EPSILON),
        reference=reference, root_records=records, summary=_summaries(records, previous_summary), costs=dict(costs))
