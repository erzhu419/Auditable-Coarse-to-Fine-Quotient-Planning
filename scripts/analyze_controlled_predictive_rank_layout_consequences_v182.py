"""Independent rank/layout observations and one weighted full-vector SVD fit."""
import argparse
from collections import Counter
from copy import deepcopy
from itertools import combinations
import json
import math
from pathlib import Path
import sys
from time import perf_counter
import numpy as np

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT)); sys.path.insert(0, str(PROJECT/'src'))
from scripts import analyze_controlled_predictive_shared_consequences_v179 as previous
from acfqp.science.controlled_predictive_causal_forgetting_v66 import swipe

ACTIONS, EPS, exact = previous.ACTIONS, previous.EPS, previous.exact
OUTPUT = PROJECT/'reports/controlled_predictive_rank_layout_consequences_v182'


def rotate_down(board, action):
    turns = {'DOWN': 0, 'RIGHT': 1, 'UP': 2, 'LEFT': 3}[action]
    output = [0]*16
    for index, rank in enumerate(board):
        row, col = divmod(index, 4)
        for _ in range(turns):
            row, col = col, 3-row
        output[4*row+col] = rank
    return tuple(output)


def token_weight(token):
    return .25 if token[0] == 'cell' else 1/math.sqrt(12)


def action_features_from_root(root, counts=None):
    work, features = Counter(), {}
    if 'layout_features' in root:
        features = deepcopy(root['layout_features'])
        work.update(layout_feature_cache_hits=1, layout_cached_aggregate_reads=6*len(features),
                    layout_cached_token_records=40*len(features), layout_cached_token_values_read=144*len(features))
    else:
        for action in ACTIONS:
            after, _, legal = swipe(tuple(root['canonical_board']), action); work['layout_ground_swipe_calls'] += 1
            if not legal:
                continue
            work['layout_direction_transport_tests'] += {'DOWN': 1, 'RIGHT': 2, 'UP': 3, 'LEFT': 4}[action]
            board = rotate_down(after, action)
            aggregate = [int(max(board) >= 11), sum(value == 0 for value in board), 0, 0, 0, 0]
            work.update(layout_afterstate_rotations=1, layout_rotated_tile_moves=16,
                        layout_aggregate_goal_tile_reads=16, layout_aggregate_vacancy_tile_reads=16)
            for axis, lines in enumerate(([board[4*r:4*r+4] for r in range(4)], [board[c::4] for c in range(4)])):
                for line in lines:
                    packed = [value for value in line if value > 0]
                    work.update(layout_compressed_lines=1, layout_compressed_line_tile_reads=4, layout_adjacent_slots_inspected=3)
                    for first, second in zip(packed, packed[1:]):
                        aggregate[2+axis] += int(first == second); aggregate[4+axis] += int(first == second == 10)
                        work.update(layout_positive_equal_tests=1, layout_goal_pair_tests=1)
            tokens = [['cell', index, rank] for index, rank in enumerate(board)]
            tokens.extend(['horizontal', index, board[index], board[index+1]] for index in range(16) if index % 4 < 3)
            tokens.extend(['vertical', index, board[index], board[index+4]] for index in range(12))
            features[action] = dict(aggregate=aggregate, tokens=tokens)
            work.update(layout_cell_token_tile_reads=16, layout_horizontal_token_tile_reads=24, layout_vertical_token_tile_reads=24, layout_tokens_formed=40)
        work['layout_feature_maps_computed'] += 1
    if counts is not None:
        counts.update(work)
    return features


def vocabulary_index(vocabulary, work):
    work['vocabulary_entries_indexed'] += len(vocabulary)
    return {tuple(token): index+6 for index, token in enumerate(vocabulary)}


def encode_action(record, indexed, work):
    values = {index: float(value) for index, value in enumerate(record['aggregate'])}; known, unknown = 0, 0
    for token in record['tokens']:
        work['token_lookups'] += 1
        column = indexed.get(tuple(token))
        if column is None:
            unknown += 1; work['unknown_token_entries'] += 1
        else:
            values[column] = token_weight(token); known += 1
            work.update(known_token_entries=1, token_weight_loads=1)
    work.update(encoded_actions=1, aggregate_values_read=6)
    return values, dict(known_tokens=known, unknown_tokens=unknown, total_tokens=len(record['tokens']))


def svd_coefficients(matrix, targets, columns):
    matrix = np.asarray(matrix, dtype=float).reshape(-1, columns)
    targets = np.asarray(targets, dtype=float).reshape(-1, 3)
    left, singular, right = np.linalg.svd(matrix, full_matrices=False)
    cutoff = np.finfo(float).eps*max(matrix.shape)*(singular[0] if len(singular) else 0.)
    keep = singular > cutoff
    coefficients = right[keep].T@((left[:, keep].T@targets)/singular[keep, None])
    return coefficients, int(sum(keep)), singular


def fit_model(examples, life=0):
    examples = list(examples); counts, feature_counts, encoder_counts = Counter(), Counter(), Counter()
    features = {row['root_id']: action_features_from_root(row, feature_counts) for row in examples if row['life'] == life}
    vocabulary = [list(token) for token in sorted({tuple(token) for actions in features.values() for row in actions.values() for token in row['tokens']})]
    counts.update(vocabulary_token_records_read=sum(len(row['tokens']) for actions in features.values() for row in actions.values()), source_vocabulary_tokens=len(vocabulary))
    indexed = vocabulary_index(vocabulary, encoder_counts); prepared, folds, original_labels = exact.prepare_exact(examples, life, counts)
    action_roots = {action: set() for action in ACTIONS}; pair_roots = {f'{a}|{b}': set() for a, b in combinations(ACTIONS, 2)}
    labels, records, training = [], [], []
    for row, label in zip(prepared, original_labels):
        encoded = {action: encode_action(features[row['root_id']][action], indexed, encoder_counts)[0] for action in row['legal_actions']}
        for action in row['legal_actions']:
            action_roots[action].add(row['root_id'])
        pairs = []
        for pair in label['pairs']:
            a, b = pair['actions']; columns = sorted(set(encoded[a]) | set(encoded[b]))
            design = [[column, encoded[a].get(column, 0.)-encoded[b].get(column, 0.)] for column in columns]
            sparse = [[column, value] for column, value in design if value != 0.]
            record = dict(deepcopy(pair), design=sparse); pairs.append(deepcopy(record))
            records.append(dict(root_id=row['root_id'], source_id=row['source_id'], **record)); pair_roots[f'{a}|{b}'].add(row['root_id'])
            counts.update(layout_pair_rows=1, layout_design_value_lookups=2*len(columns), layout_design_subtractions=len(columns), layout_nonzero_design_entries=len(sparse))
        labels.append(dict(root_id=row['root_id'], source_id=row['source_id'], legal_actions=row['legal_actions'], label_kind='exact_enumerated_vector', pairs=pairs))
        training.append({key: deepcopy(row[key]) for key in ('root_id', 'source_id', 'life', 'fold', 'canonical_board', 'legal_actions', 'immediate_rewards', 'action_components')} |
                        dict(provenance=deepcopy(row.get('provenance', {})), layout_features=deepcopy(features[row['root_id']])))
    dimensions = 6+len(vocabulary); matrix, targets = np.zeros((len(records), dimensions)), np.zeros((len(records), 3))
    for index, record in enumerate(records):
        scale = math.sqrt(record['weight'])
        for column, value in record['design']:
            matrix[index, column] = scale*value
        targets[index] = [scale*value for value in record['components']]
        counts.update(layout_weight_square_roots=1, layout_weighted_design_scalings=len(record['design']), layout_weighted_target_scalings=3)
    coefficients, rank, singular = svd_coefficients(matrix, targets, dimensions)
    counts.update(layout_lstsq_solves=1, layout_design_matrix_cells=matrix.size, layout_target_matrix_cells=targets.size, layout_coefficient_cells=3*dimensions)
    losses = [0., 0., 0.]
    for record in records:
        prediction = [sum(value*coefficients[column, k] for column, value in record['design']) for k in range(3)]
        residual = [prediction[k]-record['components'][k] for k in range(3)]
        component_losses = [record['weight']*value*value for value in residual]
        losses = [losses[k]+component_losses[k] for k in range(3)]
        record.update(predicted_components=prediction, residual_components=residual, weighted_component_losses=component_losses, weighted_loss=sum(component_losses))
        counts.update(layout_fit_prediction_coefficient_reads=3*len(record['design']), layout_fit_residual_component_subtractions=3, layout_fit_weighted_component_losses=3)
    source_counts = dict(Counter(row['source_id'] for row in prepared)); pair_ids = {pair: sorted(ids) for pair, ids in pair_roots.items()}
    return dict(schema='acfqp.rank_layout_consequences.v182', mode='LAYOUT', life=life, query='risk1', native_teacher_query='goal_1_risk_1', horizon=3,
        label_kind='exact_enumerated_vector', feature_names=list(previous.FEATURE_NAMES), vocabulary=vocabulary, design_format='sparse_columns',
        coefficients=coefficients.tolist(), rank=rank, singular_values=singular.tolist(), component_losses=losses, loss=sum(losses),
        action_root_ids={action: sorted(ids) for action, ids in action_roots.items()}, pair_root_ids=pair_ids, connected_components=previous.connected_components(pair_ids),
        constants=dict(min_action_roots=4, epsilon=EPS, goal_rank=11, aggregate_columns=6, columns=dimensions,
                       token_weights=dict(cell=.25, horizontal=1/math.sqrt(12), vertical=1/math.sqrt(12)), intercept=False, ridge=False, rcond=None),
        root_ids=[row['root_id'] for row in prepared], source_ids=sorted(source_counts), source_folds=folds, source_root_counts=source_counts,
        fit_labels=labels, fit_residuals=records, training_outcomes=training, fit_counts=dict(counts), feature_counts=dict(feature_counts), encoder_counts=dict(encoder_counts))


def choose_action(payload, root, counts=None):
    legal = [action for action in ACTIONS if action in root['legal_actions']]
    feature_work = Counter(); features = action_features_from_root(root, feature_work)
    work = Counter(layout_decisions=1, layout_legal_action_reads=len(legal)); indexed = vocabulary_index(payload['vocabulary'], work)
    action_counts = {action: len(payload['action_root_ids'][action]) for action in legal}
    pair_counts = {f'{a}|{b}': len(payload['pair_root_ids'][f'{a}|{b}']) for a, b in combinations(legal, 2)}
    connected = payload['connected_components']; component = {action: index for index, group in enumerate(connected) for action in group}
    work.update(layout_action_support_lookups=len(legal), layout_pair_support_lookups=len(pair_counts), layout_component_membership_lookups=len(legal))
    fallback, reason = False, 'selected'
    if len(legal) == 1:
        selected, reason = legal[0], 'single_legal_action'
    elif any(value < 4 for value in action_counts.values()):
        selected, fallback, reason = root['fallback_action'], True, 'insufficient_action_support'
    elif len({component[action] for action in legal}) != 1:
        selected, fallback, reason = root['fallback_action'], True, 'disconnected_required_actions'
    else:
        selected = None
    predicted, coverage = {}, {}
    for action in legal:
        entries, coverage[action] = encode_action(features[action], indexed, work)
        vector = [sum(value*payload['coefficients'][column][k] for column, value in entries.items()) for k in range(3)]
        vector[0] += root['immediate_rewards'][action]; predicted[action] = vector
        work.update(layout_prediction_coefficient_reads=3*len(entries), layout_prediction_value_reads=3*len(entries),
                    layout_prediction_component_evaluations=3, layout_immediate_reward_reads=1, layout_reward_additions=1)
    pairs = {}
    for a, b in combinations(legal, 2):
        if component[a] == component[b]:
            pairs[f'{a}|{b}'] = [x-y for x, y in zip(predicted[a], predicted[b])]; work['layout_predicted_pair_component_subtractions'] += 3
    if selected is None:
        best = None
        for action in legal:
            value = exact.utility(predicted[action]); work['layout_utility_evaluations'] += 1
            if best is None or value > best+EPS:
                selected, best = action, value
    if counts is not None:
        counts.update(work); counts.update(feature_work)
    result = dict(canonical_action=selected, fallback=fallback, leaf=0, reason=reason, predicted_components=predicted, predicted_pairs=pairs,
        support=dict(action_root_counts=action_counts, pair_root_counts=pair_counts, connected_components=deepcopy(connected), required_actions=legal, complete=not fallback),
        coverage=coverage, work=dict(work), feature_work=dict(feature_work))
    if 'action_map' in root:
        result['actual_action'] = root['action_map'][selected]
    return result


def layout_choices(roots, model, inherited):
    choices, work = {}, Counter()
    for cohort in ('SOURCE', 'TARGET'):
        rows = []
        for root in roots[cohort]:
            decision = choose_action(model, root); work.update(decision['work']); work.update(decision['feature_work'])
            rows.append(dict(root_id=root['root_id'], mode='TREE', canonical_action=decision['canonical_action'],
                             actual_action=decision['actual_action'], fallback=decision['fallback'], decision=decision))
        rows.extend(deepcopy(row) for row in inherited[cohort] if row['mode'] in ('ONE', 'FALLBACK'))
        choices[cohort] = rows
    return choices, dict(work)


def feature_coverage(choices):
    result = {}
    for cohort in ('SOURCE', 'TARGET'):
        records = [dict(root_id=row['root_id'], actions=deepcopy(row['decision']['coverage']),
                        all_tokens_seen=all(item['unknown_tokens'] == 0 for item in row['decision']['coverage'].values()))
                   for row in choices[cohort] if row['mode'] == 'TREE']
        actions = [action for row in records for action in row['actions'].values()]
        result[cohort] = dict(roots=len(records), actions=len(actions), total_tokens=sum(row['total_tokens'] for row in actions),
            known_tokens=sum(row['known_tokens'] for row in actions), unknown_tokens=sum(row['unknown_tokens'] for row in actions),
            roots_all_tokens_seen=sum(row['all_tokens_seen'] for row in records), root_records=records)
    return result


def summarize(roots, labels, choices):
    summaries = {}
    for name in ('LAYOUT', 'SHARED', 'RAW', 'STRUCTURE'):
        summary = exact.summarize(roots, labels, choices[name], {'TREE': dict(nodes=[], candidate_records=[])})
        del summary['learned_splits'], summary['candidate_reasons']; summary['model_kind'] = name; summaries[name] = summary
    return dict(schema='acfqp.rank_layout_consequences.v182.summary', complete=True, LAYOUT=summaries['LAYOUT'],
        layout_minus_shared=previous.paired_contrast(roots, summaries['LAYOUT'], summaries['SHARED']),
        layout_minus_raw=previous.paired_contrast(roots, summaries['LAYOUT'], summaries['RAW']),
        layout_minus_structure=previous.paired_contrast(roots, summaries['LAYOUT'], summaries['STRUCTURE']),
        feature_coverage=feature_coverage(choices['LAYOUT']), new_environment_samples=0, new_source_games=0, new_native_weight_updates=0, new_predictors_fitted=1)


def analyze(directory):
    begun = perf_counter(); directory = Path(directory); checks, work = [], Counter()
    def read(relative):
        raw = (directory/relative).read_bytes(); work.update(json_read_operations=1, input_bytes_read=len(raw)); return json.loads(raw)
    def check(name, condition):
        checks.append(dict(name=name, passed=bool(condition)))
    run, inputs = read('run.json'), read('input_manifest.json')
    names = ['v181_stage_checks.json', 'stage_checks.json', 'run.json', 'roots.json', 'models.json', 'choices.json', 'source_labels.json', 'labels.json']
    check('fixed_input_order_and_label_freeze', [(row['saved_ref'], row['phase']) for row in inputs] ==
          [(f'inputs/inherited/{name}', 'preparing' if i < 7 else 'target_labels') for i, name in enumerate(names)])
    for row in inputs:
        saved, original = (directory/row['saved_ref']).read_bytes(), Path(row['path']).read_bytes()
        work.update(input_byte_comparisons=1, input_comparison_bytes_read=len(saved)+len(original))
        check('retained_input_bytes:'+row['saved_ref'], saved == original and len(saved) == row['bytes'])
    check('input_costs', run['costs']['input_counts'] == dict(json_read_operations=8, input_bytes_read=sum(row['bytes'] for row in inputs)))
    stages = [read('inputs/inherited/'+name) for name in names[:2]]; inherited_run = read('inputs/inherited/run.json')
    check('inherited_V181_V179_settled_complete', all(stage['valid'] for stage in stages) and inherited_run['status'] == 'complete')
    roots = read('inputs/inherited/roots.json'); old_models, old_choices = read('inputs/inherited/models.json'), read('inputs/inherited/choices.json')
    source_labels = read('inputs/inherited/source_labels.json'); feature_work = Counter()
    for cohort in ('SOURCE', 'TARGET'):
        for root in roots[cohort]:
            root['layout_features'] = action_features_from_root(root, feature_work)
    check('independent_local_swipe_manual_rotation_rank_layout', read('roots.json') == roots)
    check('unchanged_six_aggregates', all(row['aggregate'] == root['action_features'][action]
          for cohort in ('SOURCE', 'TARGET') for root in roots[cohort] for action, row in root['layout_features'].items()))
    check('one_feature_computation_per_root', run['costs']['feature_construction']['counts'] == dict(feature_work) and feature_work['layout_ground_swipe_calls'] == 284)
    features = {root['root_id']: root['layout_features'] for root in roots['SOURCE']}
    model = fit_model([dict(deepcopy(row), layout_features=deepcopy(features[row['root_id']])) for row in source_labels])
    saved_models = read('models.json')
    check('all_old_models_fixed_without_refit', all(saved_models[name] == old_models[name] for name in ('SHARED', 'STRUCTURE', 'RAW', 'ONE')))
    check('independent_SOURCE_only_vocabulary_SVD_and_full_vector_residuals', exact._equal(saved_models['LAYOUT'], model) and exact._equal(model, saved_models['LAYOUT']))
    check('new_fit_geometry_and_encoder_costs', all(run['costs']['learning'][key] == model[key] for key in ('fit_counts', 'feature_counts', 'encoder_counts')))
    layout, choice_work = layout_choices(roots, model, old_choices['RAW']); choices = dict(deepcopy(old_choices), LAYOUT=layout); saved_choices = read('choices.json')
    check('old_choices_fixed', all(saved_choices[name] == old_choices[name] for name in ('SHARED', 'STRUCTURE', 'RAW')))
    check('new_choice_support_unknown_zero_and_full_vectors', exact._equal(saved_choices['LAYOUT'], layout) and exact._equal(layout, saved_choices['LAYOUT']))
    check('new_choice_and_encoder_costs', run['costs']['choice_counts'] == choice_work)
    labels = read('inputs/inherited/labels.json')
    check('unchanged_SOURCE_and_TARGET_labels', read('labels.json') == labels and labels['SOURCE'] == source_labels)
    summary = summarize(roots, labels, choices); saved_summary = read('summary.json')
    check('independent_full_vector_regret_and_coverage', exact._equal(saved_summary, summary) and exact._equal(summary, saved_summary))
    check('target_choice_freeze_before_label_reads', [row['phase'] for row in run['phase_history']] ==
          ['source_fit', 'models_frozen', 'target_choices_frozen', 'target_labels', 'complete'] and [row['input_reads'] for row in run['phase_history']] == [7, 7, 7, 7, 8])
    check('one_new_fit_and_no_new_physical_samples_or_native_updates', run['new_fit_attempts'] == run['new_predictors_fitted'] == 1 and
          all(run[key] == 0 for key in ('new_environment_samples', 'new_source_games', 'new_native_weight_updates')))
    valid = all(row['passed'] for row in checks); complete = valid and run['status'] == 'complete' and summary['complete']
    return dict(schema='acfqp.rank_layout_consequences.v182.analysis', valid=valid, complete=complete, primary_complete=complete, checks=checks,
        passed_checks=sum(row['passed'] for row in checks), total_checks=len(checks), summary=summary,
        costs=dict(new_environment_samples=0, physical_branches_replayed=0, old_kernels_reevaluated=0, old_models_refitted=0,
            inherited_cost_refs=run['inherited_cost_refs'], test_refs=run['test_refs'], original_run_costs=run['costs'], independent_input_counts=dict(work),
            reconstructed_production_feature_counts=dict(feature_work), reconstructed_production_fit_counts=model['fit_counts'],
            independent_fit_feature_counts=model['feature_counts'], independent_encoder_counts=model['encoder_counts'],
            independent_svd_solves=1, independent_svd_design_matrix_cells=model['fit_counts']['layout_design_matrix_cells'],
            independent_svd_target_matrix_cells=model['fit_counts']['layout_target_matrix_cells'], independent_choice_counts=choice_work, seconds=perf_counter()-begun))


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--directory', type=Path, default=OUTPUT)
    args = parser.parse_args(); result = analyze(args.directory)
    (args.directory/'analysis.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps(dict(valid=result['valid'], complete=result['complete'], passed=result['passed_checks'], total=result['total_checks'], new_environment_samples=0)))


if __name__ == '__main__':
    main()
