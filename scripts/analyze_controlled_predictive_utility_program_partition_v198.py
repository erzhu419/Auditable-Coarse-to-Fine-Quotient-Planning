"""Independent decision-utility induction over the frozen program representation."""
import argparse
from collections import Counter
from copy import deepcopy
import json
import math
from pathlib import Path
import random
import sys
from time import perf_counter

import numpy as np

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT)); sys.path.insert(0, str(PROJECT/'src'))
from scripts import analyze_controlled_predictive_relational_programs_v196 as previous
from scripts import analyze_controlled_predictive_frozen_program_replication_v197 as replication

SCHEMA = 'acfqp.utility_program_partition.v198'
OUTPUT = PROJECT/'reports/controlled_predictive_utility_program_partition_v198'
ACTIONS, EPS, utility, close = previous.ACTIONS, previous.EPS, previous.utility, previous.close
MODEL_NAMES = ('UTILITY', *previous.MODEL_NAMES)
COMPARATORS = (*previous.MODEL_NAMES, 'FALLBACK')
PRIMARY = ('PROGRAM', 'PROGRAM_NEIGHBOR', 'TERMINAL', 'TREE32', 'LINEAR', 'NONLINEAR', 'OLD_SHARED')
PAIR_MODES = ('UTILITY', *replication.PAIR_MODES)
INPUT_NAMES = ('v197_stage_checks.json', 'v197_run.json', 'v197_summary.json', 'v196_roots.json',
    'program_models.json', 'program_libraries.json', 'region_models.json', 'region_libraries.json', 'conditional_models.json',
    'nonlinear_model.json', 'relation_model.json', 'expanded_models.json', 'baseline_models.json', 'learned_rule.json',
    'dense_models.json', 'v196_selection.json')
PHASES = ('protocol_frozen', 'source_selection', 'models_frozen', 'target_roots', 'target_choices_frozen', 'target_labels', 'complete')


def prepare_training_view(examples, library, counts=None):
    work = counts if counts is not None else Counter(); work['training_view_attempts'] += 1
    lookup = {row['root_id']: row for row in examples}; rows = [lookup[name] for name in library['root_ids']]
    indices = {row['root_id']: i for i, row in enumerate(rows)}; sources = Counter(row['source_id'] for row in rows); n = len(rows)
    legal, rewards, truth = np.zeros((n, 4), dtype=bool), np.zeros((n, 4)), np.zeros((n, 4, 3))
    weights, sizes = np.zeros(n), np.zeros(n, dtype=int)
    for i, row in enumerate(rows):
        actions = [a for a in ACTIONS if a in row['legal_actions']]; sizes[i] = len(actions)
        weights[i] = 1./(len(sources)*sources[row['source_id']])
        for action in actions:
            a = ACTIONS.index(action); legal[i, a] = True; rewards[i, a] = row['immediate_rewards'][action]
            truth[i, a] = row['action_components'][action]
        work.update(training_view_roots=1, training_view_forced_roots=int(len(actions) == 1),
            training_view_reward_reads=len(actions), training_view_truth_component_reads=3*len(actions))
    prototypes = library['prototypes']; prototype_roots = np.asarray([indices[row['root_id']] for row in prototypes], dtype=int)
    work.update(training_view_preparations=1, training_view_prototypes=len(prototypes), training_view_feature_reads=162*len(prototypes),
        training_view_incidence_divisions=len(prototypes), training_view_source_weights=n,
        training_matrix_preparations=1, training_matrix_cells=162*len(prototypes))
    return dict(root_ids=[row['root_id'] for row in rows], source_ids=sorted(sources), legal=legal, rewards=rewards, truth=truth,
        root_weights=weights, action_counts=sizes, prototype_roots=prototype_roots,
        first_actions=np.asarray([ACTIONS.index(row['actions'][0]) for row in prototypes], dtype=int),
        second_actions=np.asarray([ACTIONS.index(row['actions'][1]) for row in prototypes], dtype=int),
        incidence_scale=1./(2.*sizes[prototype_roots]), features=np.asarray([row['features162'] for row in prototypes], dtype=float))


def weighted_moments(prototypes, indices, counts):
    mass, sums = 0., [0.]*3
    for i in indices:
        sample = prototypes[i]; mass += sample['root_mass']
        for k in range(3):
            sums[k] += sample['root_mass']*sample['tail_difference'][k]
    counts.update(tree_moment_sample_reads=len(indices), tree_moment_weight_additions=len(indices),
        tree_moment_WY_products=3*len(indices), tree_moment_component_additions=3*len(indices))
    return mass, sums


def incidence(view, indices, counts):
    result = np.zeros_like(view['rewards'])
    for i in indices:
        row, scale = view['prototype_roots'][i], view['incidence_scale'][i]
        result[row, view['first_actions'][i]] += scale; result[row, view['second_actions'][i]] -= scale
    counts.update(training_incidence_preparations=1, training_incidence_zero_cells=result.size,
        training_incidence_sample_reads=len(indices), training_incidence_additions=2*len(indices))
    return result


def training_actions(theta, view):
    scores = (view['rewards']+theta[:, :, 0])-theta[:, :, 1]+theta[:, :, 2]
    selected = []
    for i in range(len(view['root_ids'])):
        chosen, best = -1, -math.inf
        for a in range(4):
            value = float(scores[i, a]); better = value > best+EPS
            if view['legal'][i, a] and (chosen < 0 or better):
                chosen, best = a, value
        selected.append(chosen)
    return np.asarray(selected, dtype=int)


def training_utility(theta, view, counts):
    selected = training_actions(theta, view); n = len(selected)
    actual = view['truth'][np.arange(n), selected]; values = actual[:, 0]-actual[:, 1]+actual[:, 2]
    value = float(np.sum(view['root_weights']*values))
    counts.update(training_utility_passes=1, training_root_decisions=n, training_action_utility_evaluations=4*n,
        training_decoder_epsilon_checks=4*n, training_reward_additions=4*n, training_actual_component_reads=3*n,
        training_actual_utility_evaluations=n, training_root_weight_products=n, training_objective_addends=n)
    return value


def build_tree(library, view, max_depth, min_leaf_roots, counts=None):
    work = counts if counts is not None else Counter(); work['tree_fit_attempts'] += 1
    samples = library['prototypes']; indices = list(range(len(samples))); n = len(view['root_ids'])
    moments = weighted_moments(samples, indices, work); mean = np.asarray([v/moments[0] for v in moments[1]])
    total_incidence = incidence(view, indices, work)
    state = dict(theta=np.zeros((n, 4, 3)), predictions=np.tile(mean, (len(samples), 1)))
    work.update(training_initial_prediction_component_copies=3*len(samples), training_initial_theta_zero_cells=state['theta'].size)
    state['utility'] = training_utility(state['theta'], view, work)
    def leaf(indices, depth, node_id, moments, mean):
        work.update(tree_nodes_built=1, tree_node_mean_components=3)
        return dict(kind='leaf', node_id=node_id, depth=depth, prototype_count=len(indices),
            root_count=len({samples[i]['root_id'] for i in indices}), source_count=len({samples[i]['source_id'] for i in indices}),
            weight_sum=moments[0], mean=mean.tolist(), prototype_indices=list(indices))
    def grow(current, indices, moments, mean, node_incidence):
        best = None; mass, sums = moments
        if current['depth'] < max_depth and current['root_count'] >= min_leaf_roots and current['source_count'] >= 2:
            for feature in range(162):
                order = sorted(indices, key=lambda i: (view['features'][i, feature], i))
                work.update(tree_feature_sorts=1, tree_feature_sort_items=len(indices))
                if view['features'][order[0], feature] == view['features'][order[-1], feature]:
                    work['tree_constant_features'] += 1; continue
                left_roots, left_sources = set(), set()
                right_roots, right_sources = Counter(samples[i]['root_id'] for i in indices), Counter(samples[i]['source_id'] for i in indices)
                weight, vector, left_incidence = 0., [0.]*3, np.zeros_like(node_incidence)
                work.update(tree_prefix_incidence_preparations=1, tree_prefix_incidence_zero_cells=node_incidence.size)
                for at, i in enumerate(order[:-1]):
                    sample = samples[i]; w = sample['root_mass']; weight += w
                    for k in range(3):
                        vector[k] += w*sample['tail_difference'][k]
                    row, scale = view['prototype_roots'][i], view['incidence_scale'][i]
                    left_incidence[row, view['first_actions'][i]] += scale; left_incidence[row, view['second_actions'][i]] -= scale
                    for key, seen, remaining in (('root_id', left_roots, right_roots), ('source_id', left_sources, right_sources)):
                        name = sample[key]; seen.add(name); remaining[name] -= 1
                        if remaining[name] == 0:
                            del remaining[name]
                    work.update(tree_prefix_sample_updates=1, tree_prefix_WY_products=3, tree_prefix_component_additions=3,
                        tree_prefix_incidence_additions=2, tree_prefix_support_updates=4)
                    threshold = float(view['features'][i, feature])
                    if threshold == view['features'][order[at+1], feature]:
                        continue
                    work['tree_observed_thresholds'] += 1
                    if min(len(left_roots), len(right_roots)) < min_leaf_roots or min(len(left_sources), len(right_sources)) < 2:
                        work['tree_unsupported_thresholds'] += 1; continue
                    right_moments = (mass-weight, [sums[k]-vector[k] for k in range(3)])
                    mean_left = np.asarray([v/weight for v in vector]); mean_right = np.asarray([v/right_moments[0] for v in right_moments[1]])
                    right_incidence = node_incidence-left_incidence
                    proposed = state['theta']+left_incidence[:, :, None]*(mean_left-mean)+right_incidence[:, :, None]*(mean_right-mean)
                    work.update(tree_supported_split_candidates=1, tree_candidate_mean_divisions=6, tree_candidate_incidence_subtractions=4*n,
                        tree_candidate_mean_subtractions=6, tree_candidate_theta_products=24*n, tree_candidate_theta_additions=24*n,
                        tree_candidate_root_decisions=n)
                    after = training_utility(proposed, view, work); gain = after-state['utility']; work['tree_gain_comparisons'] += 1
                    if gain > EPS and (best is None or gain > best['improvement']+EPS):
                        best = dict(feature=feature, threshold=threshold, improvement=gain, training_utility_before=state['utility'],
                            training_utility_after=after, left_moments=(weight, list(vector)), right_moments=right_moments,
                            left_mean=mean_left, right_mean=mean_right, left_incidence=left_incidence.copy(), right_incidence=right_incidence, theta=proposed)
                        work.update(tree_best_candidate_updates=1, tree_best_candidate_array_copies=4*n)
        if best is None:
            work['tree_leaves_built'] += 1; return
        feature, threshold = best['feature'], best['threshold']
        left = [i for i in indices if view['features'][i, feature] <= threshold]
        right = [i for i in indices if view['features'][i, feature] > threshold]
        work.update(tree_split_partition_tests=2*len(indices), tree_splits_built=1,
            training_accepted_prediction_component_assignments=3*len(indices), training_accepted_theta_bindings=1)
        state['predictions'][left] = best['left_mean']; state['predictions'][right] = best['right_mean']
        state['theta'], state['utility'] = best['theta'], best['training_utility_after']
        current.pop('prototype_indices')
        left_node = leaf(left, current['depth']+1, 2*current['node_id']+1, best['left_moments'], best['left_mean'])
        right_node = leaf(right, current['depth']+1, 2*current['node_id']+2, best['right_moments'], best['right_mean'])
        current.update(kind='split', feature=feature, threshold=threshold, improvement=best['improvement'],
            training_utility_before=best['training_utility_before'], training_utility_after=best['training_utility_after'], left=left_node, right=right_node)
        grow(left_node, left, best['left_moments'], best['left_mean'], best['left_incidence'])
        grow(right_node, right, best['right_moments'], best['right_mean'], best['right_incidence'])
    tree = leaf(indices, 0, 0, moments, mean); grow(tree, indices, moments, mean, total_incidence)
    work.update(tree_predictors_fitted=1, new_predictors_fitted=1)
    return tree


def model_from_tree(library, view, depth, support, counts):
    counts['UTILITY_tree_fit_attempts'] += 1
    model = dict(schema=SCHEMA+'.model', mode='UTILITY', library_id=library['library_id'], life=library['life'], query='risk1',
        native_teacher_query=previous.old.native_exact.QUERY, horizon=previous.old.native_exact.HORIZON, label_kind='exact_enumerated_vector',
        input_columns=list(range(162)), feature_names=list(previous.FEATURE_NAMES),
        constants=dict(columns=162, epsilon=EPS, goal_rank=11, projection='COMPLETE_GRAPH_ZERO_MEAN', antisymmetrization='FORWARD_MINUS_REVERSE_OVER_TWO'),
        max_depth=depth, min_leaf_roots=support, tree=build_tree(library, view, depth, support, counts))
    counts['UTILITY_tree_predictors_fitted'] += 1
    return model


def fit_models(examples, libraries, life=0):
    counts = Counter(shared_library_preparations=0, new_linear_solves=0, new_eigen_decompositions=0, new_svd_decompositions=0,
        new_environment_samples=0, new_source_games=0, new_native_weight_updates=0, neighbor_predictor_configurations=0)
    roots = sorted((row for row in examples if row['life'] == life), key=lambda row: row['root_id'])
    sources = sorted({row['source_id'] for row in roots}); folds = [sources[::2], sources[1::2]]
    counts['source_fold_assignments'] += len(sources)
    views = {name: prepare_training_view(roots, libraries[name], counts) for name in ('FOLD_0', 'FOLD_1', 'FULL')}
    heldouts, queries = [], []
    for withheld in folds:
        rows = [row for row in roots if row['source_id'] in withheld]
        heldouts.append(rows); queries.append({row['root_id']: previous.query_inputs(previous.observable(row), counts) for row in rows})
    candidates, best, selected = [], None, (1, 4)
    for depth in previous.DEPTHS:
        for support in previous.MIN_ROOTS:
            results, groups = [], []
            for fold in range(2):
                name = f'FOLD_{fold}'; before = Counter(counts); model = model_from_tree(libraries[name], views[name], depth, support, counts)
                records, choices = previous.heldout(model, libraries[name], heldouts[fold], queries[fold], counts); groups.extend(records)
                results.append(dict(fold=fold, library_id=name, tree=model['tree'], group_records=records, choices=choices, work=dict(Counter(counts)-before)))
            groups.sort(key=lambda row: row['source_id']); score = sum(row['utility'] for row in groups)/len(sources)
            candidates.append(dict(max_depth=depth, min_leaf_roots=support, utility=score, group_records=groups, fold_results=results))
            counts.update(selection_group_mean_reads=len(sources), selection_score_comparisons=1)
            if best is None or score > best+EPS:
                best, selected = score, (depth, support)
    selection = dict(schema=SCHEMA+'.selection', mode='UTILITY', source_folds=folds,
        folds=[dict(fold=fold, library_id=f'FOLD_{fold}', train_sources=libraries[f'FOLD_{fold}']['source_ids'], heldout_sources=folds[fold]) for fold in range(2)],
        candidates=candidates, selected_depth=selected[0], selected_min_leaf_roots=selected[1], selected_utility=best)
    model = model_from_tree(libraries['FULL'], views['FULL'], *selected, counts)
    return dict(models={'UTILITY': model}, selection={'UTILITY': selection}, costs=dict(counts))


def cohort_cases():
    edges = [(4*r+c, 4*r+c+1) for r in range(4) for c in range(3)]+[(4*r+c, 4*(r+1)+c) for r in range(3) for c in range(4)]
    cases = []
    for replica in range(4):
        for index, (a, b) in enumerate(edges):
            seed = 1980200+24*replica+index; rng = random.Random(seed)
            board = [rng.randint(1, 10) for _ in range(16)]; board[a] = board[b] = 1+index%10
            for position in rng.sample([p for p in range(16) if p not in (a, b)], index%3):
                board[position] = 0
            cases.append(dict(split='TARGET', replica=replica, stratum=index, horizon=3, seed=seed,
                name=f'v198_target_r{replica:02d}_{index:02d}', board=board, vacancies=index%3))
    return cases


def freeze_choices(target, models, libraries, region_libraries):
    old, counts = previous.freeze_choices(target, {name: models[name] for name in previous.MODEL_NAMES}, libraries, region_libraries)
    choices, work = dict(UTILITY=[], **old), Counter(counts)
    for root in target:
        decision = previous.choose_action(models['UTILITY'], previous.observable(root), libraries['FULL'])
        choices['UTILITY'].append(dict(root_id=root['root_id'], mode='UTILITY', canonical_action=decision['canonical_action'],
            actual_action=decision['actual_action'], fallback=decision['fallback'], decision=decision))
        work.update(decision['work']); work.update(decision.get('feature_work', {})); work['frozen_model_choices'] += 1
    return choices, dict(work)


def success_diagnostics(records, chosen):
    result = {}
    for mode in PAIR_MODES:
        eligible, missed, wrong = 0, [], []
        for row in records:
            selected, oracle = row['models'][mode], row['models']['ORACLE']
            truth = selected['components'][2]-oracle['components'][2]
            if selected['regret'] <= EPS or abs(truth) <= EPS:
                continue
            eligible += 1; first, second = sorted((selected['action'], oracle['action']), key=ACTIONS.index)
            pair = chosen[mode][row['root_id']]['decision']['estimated_pairs'][first+'|'+second]
            estimate = pair['estimated_tail_delta'][2]*(1. if pair['actions'][0] == selected['action'] else -1.)
            if abs(estimate) <= EPS:
                missed.append(row['root_id'])
            elif truth*estimate < 0.:
                wrong.append(row['root_id'])
        result[mode] = dict(eligible_roots=eligible, missed=len(missed), wrong_direction=len(wrong),
            missed_root_ids=missed, wrong_direction_root_ids=wrong)
    return result


def summarize(roots, labels, choices, selection, model, diagnostics, retained, retained_selection):
    labeled = {row['root_id']: row['action_components'] for row in labels}
    chosen = {name: {row['root_id']: row for row in rows} for name, rows in choices.items()}
    names, records = (*MODEL_NAMES, 'FALLBACK', 'ORACLE'), []
    for root in roots['TARGET']:
        vectors = labeled[root['root_id']]; oracle = root['legal_actions'][0]
        for action in root['legal_actions'][1:]:
            if utility(vectors[action]) > utility(vectors[oracle])+EPS:
                oracle = action
        outcomes = {}
        for name in names:
            decision = None if name == 'ORACLE' else chosen[name][root['root_id']]
            action = oracle if decision is None else decision['canonical_action']; vector = list(vectors[action])
            outcomes[name] = dict(action=action, components=vector, utility=utility(vector),
                regret=utility(vectors[oracle])-utility(vector), fallback=False if decision is None else decision['fallback'])
        records.append(dict(root_id=root['root_id'], replica=root['replica'], stratum=root['stratum'], models=outcomes))
    def aggregate(rows):
        result = {}
        for name in names:
            vector = [math.fsum(row['models'][name]['components'][k] for row in rows)/len(rows) for k in range(3)]
            result[name] = dict(components=vector, utility=utility(vector), positive_regret_roots=sum(row['models'][name]['regret'] > EPS for row in rows),
                fallback_roots=sum(row['models'][name]['fallback'] for row in rows))
        return result
    def contrasts(rows):
        first = [dict(root_id=row['root_id'], models={'UTILITY': row['models']['UTILITY']}) for row in rows]
        return {'UTILITY_MINUS_'+name: previous.relation.coverage.coverage_effect(first,
            [dict(root_id=row['root_id'], models={'UTILITY': row['models'][name]}) for row in rows], 'UTILITY') for name in COMPARATORS}
    metrics, effects = aggregate(records), contrasts(records)
    replicas = [dict(replica=replica, roots=len(rows), models=aggregate(rows), comparisons=contrasts(rows))
        for replica in sorted({row['replica'] for row in records})
        for rows in [[row for row in records if row['replica'] == replica]]]
    source_modes = deepcopy(retained['SOURCE']['modes'])
    source_modes['UTILITY'] = dict(selected_depth=selection['selected_depth'], selected_min_leaf_roots=selection['selected_min_leaf_roots'],
        source_heldout_utility=selection['selected_utility'], feature_columns=model['constants']['columns'], actual=deepcopy(diagnostics['metrics']))
    headroom = metrics['ORACLE']['utility']-metrics['ONE']['utility']
    return dict(schema=SCHEMA+'.summary', complete=True, roots=len(records),
        SOURCE=dict(roots=len(roots['SOURCE']), design_groups=len({row['source_id'] for row in roots['SOURCE']}), modes=source_modes,
            heldout_comparison=dict(UTILITY_utility=selection['selected_utility'], PROGRAM_utility=retained_selection['PROGRAM']['selected_utility'],
                UTILITY_MINUS_PROGRAM=selection['selected_utility']-retained_selection['PROGRAM']['selected_utility'])),
        SOURCE_reuse=dict(retained_modes=list(previous.MODES), summary_ref='inputs/inherited/v197_summary.json',
            selection_ref='inputs/inherited/v196_selection.json', fields=['SOURCE.modes', 'projection_residuals.SOURCE']),
        models=metrics, comparisons=effects, replicas=replicas, root_records=records,
        projection_residuals=dict(SOURCE=dict(deepcopy(retained['projection_residuals']['SOURCE']), UTILITY=previous.old.projection_metrics(diagnostics['root_records'])),
            TARGET={mode: previous.old.projection_metrics(choices[mode]) for mode in PAIR_MODES}),
        success_diagnostics=success_diagnostics(records, chosen), oracle_minus_one=headroom,
        oracle_minus_utility=metrics['ORACLE']['utility']-metrics['UTILITY']['utility'],
        headroom_closed_fraction=effects['UTILITY_MINUS_ONE']['utility']/headroom if headroom > EPS else None,
        whole_cohort_positive_vs_primary=all(effects['UTILITY_MINUS_'+name]['utility'] > EPS for name in PRIMARY),
        all_replicas_positive_vs_primary=all(row['comparisons']['UTILITY_MINUS_'+name]['utility'] > EPS for row in replicas for name in PRIMARY),
        new_environment_samples=0, new_source_games=0, new_native_weight_updates=0, new_predictors_fitted=17,
        new_tree_fits=17, new_neighbor_configurations=0, new_parameter_solves=0, shared_library_preparations=0,
        new_learning_attempts=1, new_source_selection_roots=len(roots['SOURCE']), new_source_evaluation_roots=len(roots['SOURCE']), new_source_cache_roots=0)


def source_reuse_binding(summary, retained):
    return all(summary['SOURCE']['modes'][mode] == retained['SOURCE']['modes'][mode] and
        summary['projection_residuals']['SOURCE'][mode] == retained['projection_residuals']['SOURCE'][mode] for mode in previous.MODES) and (
        summary['SOURCE_reuse'] == dict(retained_modes=list(previous.MODES), summary_ref='inputs/inherited/v197_summary.json',
            selection_ref='inputs/inherited/v196_selection.json', fields=['SOURCE.modes', 'projection_residuals.SOURCE']))


def analyze(directory):
    begun = perf_counter(); directory = Path(directory); checks, io, bindings = [], Counter(), Counter()
    def read(relative):
        raw = (directory/relative).read_bytes(); io.update(json_read_operations=1, input_bytes_read=len(raw)); return json.loads(raw)
    def check(name, condition):
        checks.append(dict(name=name, passed=bool(condition)))
    run, inputs = read('run.json'), read('input_manifest.json')
    check('sixteen_frozen_SOURCE_model_library_and_evidence_inputs', [(row['saved_ref'], row['phase']) for row in inputs] ==
        [(f'inputs/inherited/{name}', 'protocol_frozen') for name in INPUT_NAMES])
    for row in inputs:
        saved, original = (directory/row['saved_ref']).read_bytes(), Path(row['path']).read_bytes()
        io.update(input_byte_comparisons=1, input_comparison_bytes_read=len(saved)+len(original))
        check('retained_input:'+row['saved_ref'], saved == original and len(saved) == row['bytes'])
    inherited = {name: read('inputs/inherited/'+name) for name in INPUT_NAMES}
    check('settled_V197_complete', inherited['v197_stage_checks.json']['valid'] and inherited['v197_run.json']['status'] == 'complete' and
        inherited['v197_summary.json']['complete'])
    source, libraries, region_libraries = inherited['v196_roots.json']['SOURCE'], inherited['program_libraries.json'], inherited['region_libraries.json']
    check('retained_SOURCE143_36_cached_program_contexts', len(source) == 143 and len({row['source_id'] for row in source}) == 36 and all(
        len(row['program_contracts'][a]['values']) == 81 and len(row['action_components'][a]) == 3 for row in source for a in row['legal_actions']))
    fitted = fit_models(source, libraries); models, selection, learning = fitted['models'], fitted['selection'], fitted['costs']
    all_models = dict(replication.merge_models(inherited), **models); saved_models = read('models.json'); saved_selection = read('selection.json')
    check('sixteen_exact_frozen_models_and_one_new_full_RFS_UTILITY_model', set(saved_models) == set(MODEL_NAMES) and
        all(saved_models[name] == all_models[name] for name in previous.MODEL_NAMES) and close(saved_models['UTILITY'], models['UTILITY']) and
        run['library_refs'] == dict(program='inputs/inherited/program_libraries.json', region='inputs/inherited/region_libraries.json'))
    check('SOURCE_only_actual_group_utility_selection', close(saved_selection, selection))
    exact_trees = previous.tree_identity(saved_models['UTILITY']['tree'], models['UTILITY']['tree']) and all(
        previous.tree_identity(saved_fold['tree'], expected_fold['tree'])
        for saved_candidate, expected_candidate in zip(saved_selection['UTILITY']['candidates'], selection['UTILITY']['candidates'], strict=True)
        for saved_fold, expected_fold in zip(saved_candidate['fold_results'], expected_candidate['fold_results'], strict=True))
    check('17_exact_UTILITY_tree_split_and_leaf_partition_identities', exact_trees)
    check('17_new_utility_trees_three_training_views_cached_queries_and_no_library_preparation', learning['tree_predictors_fitted'] == 17 and
        learning['new_predictors_fitted'] == 17 and learning['training_view_preparations'] == 3 and learning['query_input_roots'] == 143 and
        all(learning[key] == 0 for key in ('new_linear_solves', 'new_eigen_decompositions', 'new_svd_decompositions', 'shared_library_preparations')) and
        run['costs']['learning']['counts'] == learning)
    diagnostics = previous.source_diagnostics(source, models['UTILITY'], libraries['FULL'])
    saved_source = read('source_diagnostics.json')
    check('only_new_UTILITY_SOURCE_evaluation_and_full_RFS_actions', set(saved_source) == {'UTILITY'} and close(saved_source['UTILITY'], diagnostics) and
        run['costs']['source_evaluation_UTILITY']['counts'] == diagnostics['work'] and 'source_features' not in run['costs'] and not any(
            key.startswith('source_evaluation_') and key != 'source_evaluation_UTILITY' for key in run['costs']))
    relation = previous.relation; cases = cohort_cases(); target, observation_work = relation.observe_roots(cases)
    feature_work = relation.coverage.cache_roots(target); relation_work = relation.cache_roots(target)
    conditional_work = previous.old.cache_roots(target); raw_work = previous.regions.cache_roots(target)
    program_work = previous.cache_roots(target, inherited['learned_rule.json']); roots = dict(SOURCE=source, TARGET=target)
    check('96_fresh_fixed_H3_target_cases', read('target_cases.json') == cases)
    saved_roots = read('roots.json')
    check('SOURCE_unchanged_and_TARGET_exact_independent_tile_lineage', set(saved_roots) == {'SOURCE', 'TARGET'} and saved_roots['SOURCE'] == source and
        close(saved_roots['TARGET'], target) and all(saved['program_contracts'] == expected['program_contracts'] for saved, expected in zip(saved_roots['TARGET'], target, strict=True)))
    observed = run['costs']['observations']
    check('once_fresh_observation_and_all_five_cache_costs', observed['counts'] == observation_work and observed['feature_counts'] == feature_work and
        observed['relation_counts'] == relation_work and observed['conditional_counts'] == conditional_work and observed['raw_counts'] == raw_work and observed['program_counts'] == program_work)
    choices, choice_work = freeze_choices(target, all_models, libraries, region_libraries); saved_choices = read('choices.json')
    check('all_frozen_model_and_SOURCE_selected_UTILITY_choices_before_labels', close(saved_choices, choices))
    for mode in ('UTILITY', *previous.MODES):
        check(mode+'_actual_EPS_actions_and_nonnegative_normalized_weights', all(previous.verify_decision(saved['decision'], expected['decision'])
            for saved, expected in zip(saved_choices[mode], choices[mode], strict=True)))
    check('paid_all_TARGET_decisions', run['costs']['choices']['counts'] == choice_work)
    native, cost_rows = read('native_labels.json'), read('label_costs.json'); ids = [root['root_id'] for root in target]
    check('complete_native_label_and_cost_rosters', [row['root_id'] for row in native] == [row['root_id'] for row in cost_rows] == ids)
    labels, label_work = [], Counter()
    for root, raw, row in zip(target, native, cost_rows, strict=True):
        teacher = read(f"teacher_policy/{root['root_id']}.json")
        check('settled_native_fraction_teacher_binding:'+root['root_id'], relation.coverage.native_binding(root, raw, teacher))
        bindings.update(new_label_roots_bound=1, teacher_root_records_inspected=len(teacher), exact_component_coordinates_bound=3*len(root['legal_actions']))
        labels.append(relation.exact.canonical_labels(root, raw, dict(kind='new_exact_V69_FULL', teacher_query='goal_1_risk_1',
            teacher_policy_ref='teacher_policy/'+root['root_id']+'.json')))
        costs = row['costs']; construction, compilation, export, n = costs['construction'], costs['compilation'], costs['teacher_export'], len(teacher)
        accounting = construction['concrete_states'] <= 200000 and construction['concrete_active_states'] == construction['active_states'] == n
        accounting = accounting and compilation['model_payload_calls'] == compilation['model_reload_calls'] == 1
        accounting = accounting and compilation['payload_cells'] == construction['registered_states'] == costs['label_evaluation']['kernel_cells_read']
        accounting = accounting and compilation['payload_rows'] == costs['label_evaluation']['kernel_rows_read'] and compilation['payload_outcomes'] == costs['label_evaluation']['kernel_outcomes_read']
        accounting = accounting and costs['label_evaluation']['root_labels_emitted'] == 1 and export == dict(
            teacher_encoding_records_read=construction['concrete_states'], teacher_policy_records=n, teacher_policy_action_reads=n, teacher_policy_tile_reads=16*n)
        check('settled_acquisition_caps_and_export_costs:'+root['root_id'], accounting)
        for kind in ('construction', 'planning', 'label_evaluation', 'teacher_export', 'compilation'):
            label_work.update({kind+'.'+key: value for key, value in costs[kind].items() if type(value) is int})
    check('all_new_canonical_RFS_vectors_and_fraction_metadata', close(read('labels.json'), labels))
    summary = summarize(roots, labels, choices, selection['UTILITY'], models['UTILITY'], diagnostics, inherited['v197_summary.json'], inherited['v196_selection.json'])
    saved_summary = read('summary.json')
    check('19_arm_RFS_17_contrasts_replicas_and_eight_pair_diagnostics', close(saved_summary, summary))
    check('previous_SOURCE_modes_and_projection_retained_exactly', source_reuse_binding(saved_summary, inherited['v197_summary.json']))
    check('SOURCE_selection_and_all_TARGET_choices_precede_labels', [(row['phase'], row['input_reads']) for row in run['phase_history']] ==
        [(phase, 0 if index == 0 else 16) for index, phase in enumerate(PHASES)])
    check('all_paid_input_and_label_counts', run['costs']['input_counts'] == dict(json_read_operations=16,
        input_bytes_read=sum(row['bytes'] for row in inputs), input_bytes_retained=sum(row['bytes'] for row in inputs)) and run['costs']['labels']['counts'] == dict(label_work))
    accounting = all(run[key] == 96 for key in ('new_boards_generated', 'new_reference_kernel_attempts', 'new_reference_kernels',
        'new_teacher_plans', 'new_exact_label_roots', 'completed_roots'))
    accounting = accounting and run['new_predictors_fitted'] == run['new_tree_fits'] == 17 and run['new_learning_attempts'] == 1 and (
        run['new_source_selection_roots'] == run['new_source_evaluation_roots'] == 143) and run['resource_cap_per_board'] == 200000
    accounting = accounting and all(run[key] == 0 for key in ('new_environment_samples', 'new_source_games', 'new_native_weight_updates',
        'new_neighbor_configurations', 'new_parameter_solves', 'shared_library_preparations', 'new_source_cache_roots'))
    check('17_new_tree_fits_96_new_labels_no_SOURCE_cache_or_library_rebuild', accounting)
    valid = all(row['passed'] for row in checks); complete = valid and run['status'] == 'complete' and summary['complete']
    return dict(schema=SCHEMA+'.analysis', valid=valid, complete=complete, primary_complete=complete, checks=checks,
        passed_checks=sum(row['passed'] for row in checks), total_checks=len(checks), summary=summary,
        costs=dict(independent_parameter_solves=0, independent_eigen_solves=0, independent_svd_solves=0,
            independent_tree_fits=learning['tree_predictors_fitted'], independent_neighbor_configurations=0, independent_shared_library_preparations=0,
            independent_SOURCE_feature_counts={}, reconstructed_learning_counts=learning, independent_source_evaluation_counts={'UTILITY': diagnostics['work']},
            new_environment_samples=0, physical_branches_replayed=0, new_kernels_reintegrated=0, old_models_refitted=0,
            independent_input_counts=dict(io), independent_observation_counts=observation_work, independent_feature_counts=feature_work,
            independent_relation_counts=relation_work, independent_conditional_counts=conditional_work, independent_raw_counts=raw_work,
            independent_program_counts=program_work, independent_choice_counts=choice_work, independent_new_label_binding_counts=dict(bindings),
            reconstructed_acquisition_counts=dict(label_work), original_run_costs=run['costs'], inherited_cost_refs=run['inherited_cost_refs'], test_refs=run['test_refs'], seconds=perf_counter()-begun))


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--directory', type=Path, default=OUTPUT)
    args = parser.parse_args(); result = analyze(args.directory)
    (args.directory/'analysis.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps(dict(valid=result['valid'], complete=result['complete'], passed=result['passed_checks'], total=result['total_checks'])))


if __name__ == '__main__':
    main()
