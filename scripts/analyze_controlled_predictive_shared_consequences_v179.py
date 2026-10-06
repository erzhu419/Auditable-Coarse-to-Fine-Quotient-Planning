"""Independent action-oriented features and shared weighted-vector regression."""
from collections import Counter
from copy import deepcopy
from itertools import combinations
import argparse
import json
import math
from pathlib import Path
import sys
from time import perf_counter
import numpy as np

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT)); sys.path.insert(0, str(PROJECT/'src'))
from scripts import analyze_controlled_predictive_exact_h3_v177 as exact
from scripts import analyze_controlled_predictive_afterstate_structure_v178 as previous
from acfqp.science.controlled_predictive_causal_forgetting_v66 import swipe

ACTIONS, EPS = exact.ACTIONS, exact.EPS
FEATURE_NAMES = ['goal_reached', 'vacancies', 'row_positive_equal', 'col_positive_equal', 'row_goal_pair', 'col_goal_pair']


def rotate_to_down(board, action):
    turns = {'DOWN': 0, 'RIGHT': 1, 'UP': 2, 'LEFT': 3}[action]
    output = [0]*16
    for source, rank in enumerate(board):
        row, col = divmod(source, 4)
        for _ in range(turns):
            row, col = col, 3-row
        output[4*row+col] = rank
    return tuple(output)


def action_features_from_root(root, counts=None):
    work = Counter(); features = {}
    if 'action_features' in root:
        features = {action: list(root['action_features'][action]) for action in ACTIONS if action in root['action_features']}
        if counts is not None:
            counts.update(shared_feature_cache_hits=1, shared_cached_feature_reads=6*len(features))
        return features
    for action in ACTIONS:
        after, _, legal = swipe(tuple(root['canonical_board']), action)
        work['shared_ground_swipe_calls'] += 1
        if not legal:
            continue
        work['shared_direction_transport_tests'] += {'DOWN': 1, 'LEFT': 4, 'RIGHT': 2, 'UP': 3}[action]
        oriented = rotate_to_down(after, action); totals = []
        work.update(shared_afterstate_rotations=1, shared_rotated_tile_moves=16, shared_goal_tile_reads=16, shared_vacancy_tile_reads=16)
        for lines in ([oriented[4*r:4*r+4] for r in range(4)], [tuple(oriented[4*r+c] for r in range(4)) for c in range(4)]):
            equal, goal = 0, 0
            for line in lines:
                packed = [rank for rank in line if rank > 0]
                work.update(shared_compressed_lines=1, shared_line_tile_reads=4, shared_adjacent_slots_inspected=3)
                for a, b in zip(packed, packed[1:]):
                    equal += int(a == b); goal += int(a == b == 10)
                    work.update(shared_positive_equal_tests=1, shared_goal_pair_tests=1)
            totals.append((equal, goal))
        features[action] = [int(max(oriented) >= 11), sum(rank == 0 for rank in oriented), totals[0][0], totals[1][0], totals[0][1], totals[1][1]]
    work['shared_feature_maps_computed'] += 1
    if counts is not None:
        counts.update(work)
    return features


def svd_coefficients(matrix, targets):
    matrix, targets = np.asarray(matrix, dtype=float).reshape(-1, 6), np.asarray(targets, dtype=float).reshape(-1, 3)
    left, singular, right = np.linalg.svd(matrix, full_matrices=False)
    threshold = np.finfo(float).eps*max(matrix.shape)*(singular[0] if len(singular) else 0.)
    keep = singular > threshold
    coefficients = right[keep].T@((left[:, keep].T@targets)/singular[keep, None])
    return coefficients, int(sum(keep)), singular


def connected_components(pair_roots):
    adjacency = {action: set() for action in ACTIONS}
    for pair, roots in pair_roots.items():
        if roots:
            a, b = pair.split('|'); adjacency[a].add(b); adjacency[b].add(a)
    remaining, groups = set(ACTIONS), []
    while remaining:
        group = {min(remaining)}; frontier = list(group)
        while frontier:
            node = frontier.pop()
            for neighbor in adjacency[node]-group:
                group.add(neighbor); frontier.append(neighbor)
        remaining -= group; groups.append(sorted(group))
    return groups


def fit_model(examples, life=0):
    counts, feature_counts = Counter(), Counter()
    examples, folds, labels = exact.prepare_exact(examples, life, counts)
    action_roots = {action: set() for action in ACTIONS}; pair_roots = {f'{a}|{b}': set() for a, b in combinations(ACTIONS, 2)}
    matrix, targets, records, fitted_labels, training = [], [], [], [], []
    for example, label in zip(examples, labels):
        features = action_features_from_root(example, feature_counts)
        for action in example['legal_actions']:
            action_roots[action].add(example['root_id'])
        pairs = []
        for pair in label['pairs']:
            a, b = pair['actions']; row = [x-y for x, y in zip(features[a], features[b])]; weight = pair['weight']; scale = math.sqrt(weight)
            matrix.append([scale*x for x in row]); targets.append([scale*x for x in pair['components']]); pair_roots[f'{a}|{b}'].add(example['root_id'])
            record = dict(actions=[a, b], weight=weight, design=row, components=list(pair['components']))
            pairs.append(deepcopy(record)); records.append(dict(root_id=example['root_id'], source_id=example['source_id'], **record))
            counts.update(shared_pair_rows=1, shared_feature_value_reads=12, shared_feature_difference_subtractions=6,
                          shared_weight_square_roots=1, shared_weighted_design_scalings=6, shared_weighted_target_scalings=3)
        fitted_labels.append(dict(root_id=example['root_id'], source_id=example['source_id'], legal_actions=example['legal_actions'], label_kind='exact_enumerated_vector', pairs=pairs))
        training.append({key: deepcopy(example[key]) for key in ('root_id', 'source_id', 'life', 'fold', 'canonical_board', 'legal_actions', 'immediate_rewards', 'action_components')} |
                        dict(provenance=deepcopy(example.get('provenance', {})), action_features=deepcopy(features)))
    coefficients, rank, singular = svd_coefficients(matrix, targets)
    counts.update(shared_lstsq_solves=1, shared_design_matrix_cells=6*len(matrix), shared_target_matrix_cells=3*len(matrix), shared_coefficient_cells=18)
    component_losses = [0., 0., 0.]
    for record in records:
        prediction = np.asarray(record['design'], dtype=float)@coefficients
        residual = prediction-np.asarray(record['components']); losses = [record['weight']*float(value)**2 for value in residual]
        for k in range(3):
            component_losses[k] += losses[k]
        record.update(predicted_components=prediction.tolist(), residual_components=residual.tolist(), weighted_component_losses=losses, weighted_loss=sum(losses))
        counts.update(shared_fit_prediction_component_evaluations=3, shared_residual_component_subtractions=3, shared_weighted_component_losses=3)
    sources = dict(Counter(example['source_id'] for example in examples)); pair_ids = {pair: sorted(roots) for pair, roots in pair_roots.items()}
    return dict(schema='acfqp.shared_consequences.v179', mode='SHARED', life=life, query='risk1', native_teacher_query='goal_1_risk_1', horizon=3,
                label_kind='exact_enumerated_vector', feature_names=list(FEATURE_NAMES), coefficients=coefficients.tolist(), rank=rank, singular_values=singular.tolist(),
                component_losses=component_losses, loss=sum(component_losses), action_root_ids={action: sorted(roots) for action, roots in action_roots.items()},
                pair_root_ids=pair_ids, connected_components=connected_components(pair_ids),
                constants=dict(min_action_roots=4, epsilon=EPS, goal_rank=11, features=6, intercept=False, ridge=False, rcond=None),
                root_ids=[example['root_id'] for example in examples], source_ids=sorted(sources), source_folds=folds, source_root_counts=sources,
                fit_labels=fitted_labels, fit_residuals=records, training_outcomes=training, fit_counts=dict(counts), feature_counts=dict(feature_counts))


def choose_action(payload, root, counts=None):
    legal = [action for action in ACTIONS if action in root['legal_actions']]
    feature_work = Counter(); features = action_features_from_root(root, feature_work)
    work = Counter(shared_decisions=1, shared_legal_action_reads=len(legal))
    action_counts = {action: len(payload['action_root_ids'][action]) for action in legal}
    pair_counts = {f'{a}|{b}': len(payload['pair_root_ids'][f'{a}|{b}']) for a, b in combinations(legal, 2)}
    connected = payload['connected_components']; component = {action: i for i, group in enumerate(connected) for action in group}
    work.update(shared_action_support_lookups=len(legal), shared_pair_support_lookups=len(pair_counts), shared_component_membership_lookups=len(legal))
    fallback, reason = False, 'selected'
    if len(legal) == 1:
        selected, reason = legal[0], 'single_legal_action'
    elif any(value < 4 for value in action_counts.values()):
        selected, fallback, reason = root['fallback_action'], True, 'insufficient_action_support'
    elif len({component[action] for action in legal}) != 1:
        selected, fallback, reason = root['fallback_action'], True, 'disconnected_required_actions'
    else:
        selected = None
    predicted = {}
    for action in legal:
        vector = [sum(features[action][i]*payload['coefficients'][i][k] for i in range(6)) for k in range(3)]
        vector[0] += root['immediate_rewards'][action]; predicted[action] = vector
        work.update(shared_prediction_feature_reads=18, shared_prediction_coefficient_reads=18, shared_prediction_component_evaluations=3,
                    shared_immediate_reward_reads=1, shared_reward_additions=1)
    pairs = {}
    for a, b in combinations(legal, 2):
        if component[a] == component[b]:
            pairs[f'{a}|{b}'] = [x-y for x, y in zip(predicted[a], predicted[b])]; work['shared_predicted_pair_component_subtractions'] += 3
    if selected is None:
        best = None
        for action in legal:
            value = exact.utility(predicted[action]); work['shared_utility_evaluations'] += 1
            if best is None or value > best+EPS:
                selected, best = action, value
    if counts is not None:
        counts.update(work); counts.update(feature_work)
    result = dict(canonical_action=selected, fallback=fallback, leaf=0, reason=reason, predicted_components=predicted, predicted_pairs=pairs,
                  support=dict(action_root_counts=action_counts, pair_root_counts=pair_counts, connected_components=deepcopy(connected), required_actions=legal, complete=not fallback),
                  work=dict(work), feature_work=dict(feature_work))
    if 'action_map' in root:
        result['actual_action'] = root['action_map'][selected]
    return result


def shared_choices(roots, model, inherited):
    choices, work = {}, Counter()
    for cohort in ('SOURCE', 'TARGET'):
        rows = []
        for root in roots[cohort]:
            decision = choose_action(model, root); work.update(decision['work']); work.update(decision['feature_work'])
            rows.append(dict(root_id=root['root_id'], mode='TREE', canonical_action=decision['canonical_action'], actual_action=decision['actual_action'],
                             fallback=decision['fallback'], decision=decision))
        rows.extend(deepcopy(row) for row in inherited[cohort] if row['mode'] in ('ONE', 'FALLBACK'))
        choices[cohort] = rows
    return choices, dict(work)


def paired_contrast(roots, shared, baseline):
    contrasts = {}
    for cohort in ('SOURCE', 'TARGET'):
        indices = [{row['root_id']: row for row in summary['cohorts'][cohort]['root_records']} for summary in (shared, baseline)]
        records, groups = [], {}
        for root in roots[cohort]:
            a, b = [index[root['root_id']]['modes']['TREE'] for index in indices]; vector = [x-y for x, y in zip(a['components'], b['components'])]
            records.append(dict(root_id=root['root_id'], source_id=root['source_id'], components=vector, utility=exact.utility(vector),
                                shared_action=a['action'], baseline_action=b['action'], shared_regret=a['regret'], baseline_regret=b['regret']))
            groups.setdefault(root['source_id'], []).append(vector)
        group_rows = [dict(source_id=source, roots=len(vectors), components=exact.mean_vectors(vectors), utility=exact.utility(exact.mean_vectors(vectors))) for source, vectors in sorted(groups.items())]
        aggregates = {}
        for weighting in ('ROOT_MEAN', 'DESIGN_GROUP_MEAN'):
            rows = records if weighting == 'ROOT_MEAN' else group_rows; vector = exact.mean_vectors([row['components'] for row in rows])
            aggregates[weighting] = dict(components=vector, utility=exact.utility(vector))
        contrasts[cohort] = dict(roots=len(records), primary_weighting='DESIGN_GROUP_MEAN' if cohort == 'SOURCE' else 'ROOT_MEAN', aggregates=aggregates,
            diagnostics=dict(improved_roots=sum(row['utility'] > EPS for row in records), worsened_roots=sum(row['utility'] < -EPS for row in records),
                             equal_value_roots=sum(abs(row['utility']) <= EPS for row in records), action_changes=sum(row['shared_action'] != row['baseline_action'] for row in records),
                             new_positive_regret_roots=sum(row['baseline_regret'] <= EPS < row['shared_regret'] for row in records),
                             resolved_positive_regret_roots=sum(row['shared_regret'] <= EPS < row['baseline_regret'] for row in records)), groups=group_rows, root_records=records)
    return contrasts


def alias_bound(roots, labels, shared):
    cohorts = {}
    for cohort in ('SOURCE', 'TARGET'):
        labels_by_root = {row['root_id']: row for row in labels[cohort]}
        outcomes = {row['root_id']: row for row in shared['cohorts'][cohort]['root_records']}; records, grouped = [], {}
        for root in roots[cohort]:
            vectors = labels_by_root[root['root_id']]['action_components']; classes = {}
            for action in ACTIONS:
                if action in root['legal_actions']:
                    classes.setdefault(tuple(root['action_features'][action]), []).append(action)
            groups, pairs = [], []
            for features, actions in classes.items():
                selected = actions[0]
                for action in actions[1:]:
                    if root['immediate_rewards'][action] > root['immediate_rewards'][selected]+EPS:
                        selected = action
                groups.append(dict(features=list(features), actions=actions, representative=selected))
                for a, b in combinations(actions, 2):
                    delta = [x-y for x, y in zip(vectors[a], vectors[b])]; immediate = root['immediate_rewards'][a]-root['immediate_rewards'][b]
                    tail = [delta[0]-immediate, *delta[1:]]
                    pairs.append(dict(actions=[a, b], features=list(features), true_components=delta, immediate_reward_difference=immediate,
                                      continuation_components=tail, continuation_utility=exact.utility(tail)))
            representatives = sorted((group['representative'] for group in groups), key=ACTIONS.index); restricted = representatives[0]
            for action in representatives[1:]:
                if exact.utility(vectors[action]) > exact.utility(vectors[restricted])+EPS:
                    restricted = action
            modes = outcomes[root['root_id']]['modes']; difference = [x-y for x, y in zip(vectors[restricted], modes['ONE']['components'])]
            row = dict(root_id=root['root_id'], source_id=root['source_id'], feature_groups=groups, restricted_action=restricted,
                       one_action=modes['ONE']['action'], oracle_action=modes['ORACLE']['action'], restricted_components=vectors[restricted],
                       restricted_minus_one_components=difference, restricted_minus_one_utility=exact.utility(difference),
                       oracle_minus_restricted=modes['ORACLE']['utility']-exact.utility(vectors[restricted]), same_feature_pairs=pairs)
            records.append(row); grouped.setdefault(root['source_id'], []).append(row)
        def aggregate(rows):
            vector = exact.mean_vectors([row['restricted_components'] for row in rows]); difference = exact.mean_vectors([row['restricted_minus_one_components'] for row in rows])
            return dict(restricted_components=vector, restricted_utility=exact.utility(vector), restricted_minus_one_components=difference,
                        restricted_minus_one_utility=exact.utility(difference), oracle_minus_restricted=math.fsum(row['oracle_minus_restricted'] for row in rows)/len(rows))
        group_rows = [dict(source_id=source, roots=len(rows), **aggregate(rows)) for source, rows in sorted(grouped.items())]
        cohorts[cohort] = dict(roots=len(records), primary_weighting='DESIGN_GROUP_MEAN' if cohort == 'SOURCE' else 'ROOT_MEAN',
            aggregates=dict(ROOT_MEAN=aggregate(records), DESIGN_GROUP_MEAN=aggregate(group_rows)),
            diagnostics=dict(identical_feature_pairs=sum(len(row['same_feature_pairs']) for row in records), roots_with_alias=sum(bool(row['same_feature_pairs']) for row in records),
                             conflicting_continuation_pairs=sum(any(abs(value) > EPS for value in pair['continuation_components']) for row in records for pair in row['same_feature_pairs']),
                             lost_headroom_roots=sum(row['oracle_minus_restricted'] > EPS for row in records)), groups=group_rows, root_records=records)
    return cohorts


def summarize(roots, labels, choices, models):
    summaries = {name: exact.summarize(roots, labels, choices[name], {'TREE': dict(nodes=[], candidate_records=[]) if name == 'SHARED' else models[name]}) for name in ('SHARED', 'STRUCTURE', 'RAW')}
    del summaries['SHARED']['learned_splits'], summaries['SHARED']['candidate_reasons']; summaries['SHARED']['model_kind'] = 'SHARED'
    return dict(schema='acfqp.shared_consequences.v179.summary', complete=True, **summaries,
                shared_minus_raw=paired_contrast(roots, summaries['SHARED'], summaries['RAW']),
                shared_minus_structure=paired_contrast(roots, summaries['SHARED'], summaries['STRUCTURE']),
                feature_alias=alias_bound(roots, labels, summaries['SHARED']), new_environment_samples=0, new_source_games=0, new_native_weight_updates=0)


def analyze(directory):
    begun = perf_counter(); directory = Path(directory); checks, work = [], Counter()
    def read(relative):
        raw = (directory/relative).read_bytes(); work.update(json_read_operations=1, input_bytes_read=len(raw)); return json.loads(raw)
    def check(name, condition):
        checks.append(dict(name=name, passed=bool(condition)))
    run, inputs = read('run.json'), read('input_manifest.json')
    names = ['stage_checks.json', 'run.json', 'roots.json', 'models.json', 'choices.json', 'source_labels.json', 'labels.json']
    check('fixed_input_order_and_label_freeze', [(row['saved_ref'], row['phase']) for row in inputs] ==
          [(f'inputs/inherited/{name}', 'preparing' if i < 6 else 'target_labels') for i, name in enumerate(names)])
    for row in inputs:
        raw, original = (directory/row['saved_ref']).read_bytes(), Path(row['path']).read_bytes(); work.update(input_byte_comparisons=1, input_comparison_bytes_read=len(raw)+len(original))
        check('retained_input_bytes:'+row['saved_ref'], raw == original and len(raw) == row['bytes'])
    check('input_costs', run['costs']['input_counts'] == dict(json_read_operations=7, input_bytes_read=sum(row['bytes'] for row in inputs)))
    stage, inherited_run = read('inputs/inherited/stage_checks.json'), read('inputs/inherited/run.json')
    check('inherited_V178_settled_complete', stage['valid'] and inherited_run['status'] == 'complete')
    roots = read('inputs/inherited/roots.json'); labels = read('inputs/inherited/labels.json'); source_labels = read('inputs/inherited/source_labels.json')
    old_models, old_choices = read('inputs/inherited/models.json'), read('inputs/inherited/choices.json')
    check('fixed47_SOURCE24_TARGET', len(roots['SOURCE']) == 47 and len(roots['TARGET']) == 24)
    check('unchanged_SOURCE_and_TARGET_labels', read('labels.json') == labels and labels['SOURCE'] == source_labels)
    feature_work = Counter()
    for cohort in ('SOURCE', 'TARGET'):
        for root in roots[cohort]:
            root['action_features'] = action_features_from_root(root, feature_work)
    check('independent_local_swipe_manual_rotation_cache', read('roots.json') == roots)
    check('one_feature_computation_per_root', run['costs']['feature_construction']['counts'] == dict(feature_work) and feature_work['shared_ground_swipe_calls'] == 284)
    features = {root['root_id']: root['action_features'] for cohort in ('SOURCE', 'TARGET') for root in roots[cohort]}
    examples = [dict(deepcopy(row), action_features=features[row['root_id']]) for row in source_labels]; model = fit_model(examples)
    models = dict(SHARED=model, STRUCTURE=old_models['STRUCTURE'], RAW=old_models['RAW'], ONE=old_models['ONE']); saved_models = read('models.json')
    check('all_old_models_fixed_without_refit', all(saved_models[name] == models[name] for name in ('STRUCTURE', 'RAW', 'ONE')))
    check('independent_weighted_SVD_rank_coefficients_and_residuals', exact._equal(saved_models['SHARED'], model) and exact._equal(model, saved_models['SHARED']))
    check('fit_and_feature_costs', run['costs']['learning']['fit_counts'] == model['fit_counts'] and run['costs']['learning']['feature_counts'] == model['feature_counts'])
    shared, choice_work = shared_choices(roots, model, old_choices['RAW']); choices = dict(SHARED=shared, STRUCTURE=old_choices['STRUCTURE'], RAW=old_choices['RAW']); saved_choices = read('choices.json')
    check('old_choices_fixed', all(saved_choices[name] == old_choices[name] for name in ('STRUCTURE', 'RAW')))
    check('new_choices_before_target_labels', exact._equal(saved_choices['SHARED'], shared) and exact._equal(shared, saved_choices['SHARED']))
    check('new_choice_support_and_cache_costs', run['costs']['choice_counts'] == choice_work)
    summary = summarize(roots, labels, choices, models); saved_summary = read('summary.json')
    check('independent_full_vector_regret_and_alias_bound', exact._equal(saved_summary, summary) and exact._equal(summary, saved_summary))
    check('target_choice_freeze_before_label_reads', [row['phase'] for row in run['phase_history']] == ['source_fit', 'models_frozen', 'target_choices_frozen', 'target_labels', 'complete'] and [row['input_reads'] for row in run['phase_history']] == [6, 6, 6, 6, 7])
    check('no_new_physical_samples_or_native_updates', all(run[key] == 0 for key in ('new_environment_samples', 'new_source_games', 'new_native_weight_updates')))
    valid = all(row['passed'] for row in checks); complete = valid and run['status'] == 'complete' and summary['complete']
    return dict(schema='acfqp.shared_consequences.v179.analysis', valid=valid, complete=complete, primary_complete=complete, checks=checks,
                passed_checks=sum(row['passed'] for row in checks), total_checks=len(checks), summary=summary,
                costs=dict(new_environment_samples=0, physical_branches_replayed=0, old_kernels_reevaluated=0, old_models_refitted=0,
                           inherited_cost_refs=run['inherited_cost_refs'], test_refs=run['test_refs'], original_run_costs=run['costs'], independent_input_counts=dict(work),
                           reconstructed_production_feature_counts=dict(feature_work), reconstructed_production_fit_counts=model['fit_counts'], independent_fit_feature_counts=model['feature_counts'],
                           independent_svd_solves=1, independent_svd_design_matrix_cells=model['fit_counts']['shared_design_matrix_cells'],
                           independent_svd_target_matrix_cells=model['fit_counts']['shared_target_matrix_cells'], independent_choice_counts=choice_work, seconds=perf_counter()-begun))


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--directory', type=Path, default=PROJECT/'reports/controlled_predictive_shared_consequences_v179')
    args = parser.parse_args(); result = analyze(args.directory); (args.directory/'analysis.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps(dict(valid=result['valid'], complete=result['complete'], passed=result['passed_checks'], total=result['total_checks'], new_environment_samples=0)))


if __name__ == '__main__':
    main()
