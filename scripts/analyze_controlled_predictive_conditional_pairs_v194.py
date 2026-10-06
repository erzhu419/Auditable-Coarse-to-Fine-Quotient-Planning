"""Independent rank-bin features and nonnegative same-root pair transfer."""
import argparse
from collections import Counter
from copy import deepcopy
from itertools import combinations
import json
import math
from pathlib import Path
import random
import sys
from time import perf_counter

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT)); sys.path.insert(0, str(PROJECT/'src'))
from scripts import analyze_controlled_predictive_merge_relations_v190 as relation
from scripts import analyze_controlled_predictive_nonlinear_relations_v192 as nonlinear
from acfqp.science import controlled_predictive_exact_h3_v177 as native_exact

SCHEMA = 'acfqp.conditional_pairs.v194'
OUTPUT = PROJECT/'reports/controlled_predictive_conditional_pairs_v194'
ACTIONS, EPS = relation.ACTIONS, relation.EPS
MODES, K_VALUES, TEMPERATURES = ('PAIR98', 'CONDITIONAL'), (1, 8, 32), (.01, .1, 1.)
BINS = ('le7', 'rank8', 'rank9', 'rank10', 'ge11')
FEATURE_NAMES = (*relation.FEATURE_NAMES[:6], *(f'{rank_bin}:{kind}:{name}' for rank_bin in BINS
    for kind, names in (('node', relation.NODE_MOMENT_NAMES), ('pair', relation.PAIR_MOMENT_NAMES)) for name in names),
    *relation.VACANCY_MOMENT_NAMES)
MODEL_NAMES = ('CONDITIONAL', 'PAIR98', 'NONLINEAR', 'RELATION', 'LINEAR', 'INTERACT', 'RIDGE', 'LAYOUT', 'SHARED', 'OLD_SHARED', 'ONE')
COMPARATORS = (*MODEL_NAMES[1:], 'FALLBACK')


def utility(vector):
    return vector[0]-vector[1]+vector[2]


def close(actual, expected):
    if isinstance(expected, dict):
        return isinstance(actual, dict) and set(actual) == set(expected) and all(close(actual[key], value) for key, value in expected.items())
    if isinstance(expected, list):
        return isinstance(actual, list) and len(actual) == len(expected) and all(close(a, b) for a, b in zip(actual, expected, strict=True))
    if isinstance(expected, float):
        return isinstance(actual, (int, float)) and abs(actual-expected) <= 1e-8*(1.+abs(expected))
    return actual == expected


def conditional_features(root, counts=None):
    work, result = Counter(), {}
    if 'conditional_features' in root:
        result = {a: list(root['conditional_features'][a]) for a in ACTIONS if a in root['legal_actions']}
        work.update(conditional_feature_cache_hits=1, conditional_cached_feature_reads=224*len(result))
    else:
        for action in ACTIONS:
            if action not in root['legal_actions']:
                continue
            contract = relation.build_contract(root['layout_features'][action], work)
            node, pair = [[0.]*9 for _ in BINS], [[0.]*33 for _ in BINS]
            for key, target, columns in (('nodes', node, 9), ('equal_pairs', pair, 33)):
                for record in contract[key]:
                    rank = record['rank']; index = 0 if rank <= 7 else rank-7 if rank <= 10 else 4
                    for column, value in enumerate(record['moments']):
                        target[index][column] += value
                    work['conditional_rank_bin_assignments'] += 1
                    work['conditional_node_moment_accumulations' if key == 'nodes' else 'conditional_pair_moment_accumulations'] += columns
            vector = list(map(float, contract['aggregate']))
            for node_values, pair_values in zip(node, pair, strict=True):
                vector.extend(value/4. for value in node_values); vector.extend(value/math.sqrt(120.) for value in pair_values)
            vector.extend(contract['vacancy_moments']); result[action] = vector
            work.update(conditional_node_normalizations=45, conditional_pair_normalizations=165,
                conditional_vacancy_values_copied=8, conditional_feature_vectors_computed=1)
        work['conditional_feature_maps_derived'] += 1
    if counts is not None:
        counts.update(work)
    return result


def cache_roots(roots):
    work = Counter()
    for root in roots:
        root['conditional_features'] = conditional_features(root, work)
    return dict(work)


def features(root, mode, counts):
    key, columns = ('relation_features', 98) if mode == 'PAIR98' else ('conditional_features', 224)
    values = {a: list(map(float, root[key][a])) for a in ACTIONS if a in root['legal_actions']}
    counts.update(pair_feature_cache_reads=1, pair_feature_value_reads=columns*len(values))
    return values


def distance(first, second):
    return sum((a-b)**2 for a, b in zip(first, second, strict=True))


def median(values):
    ordered = sorted(values); n = len(values)
    return ordered[n//2] if n % 2 else (ordered[n//2-1]+ordered[n//2])/2.


def prepare_design(examples, mode, life=0, costs=None):
    counts = costs if costs is not None else Counter(); before = Counter(counts)
    counts['pair_design_attempts'] += 1; roots = []
    for original in examples:
        counts['pair_examples_examined'] += 1
        if original['life'] != life:
            counts['pair_other_life_examples_excluded'] += 1; continue
        root = deepcopy(original); legal = [a for a in ACTIONS if a in root['legal_actions']]
        root['legal_actions'] = legal; root['immediate_rewards'] = {a: float(root['immediate_rewards'][a]) for a in legal}
        root['action_components'] = {a: list(map(float, root['action_components'][a])) for a in legal}; roots.append(root)
        counts.update(pair_examples_fitted=1, pair_legal_action_reads=len(legal), pair_immediate_reward_reads=len(legal),
            pair_label_component_reads=3*len(legal), pair_tail_reward_subtractions=len(legal))
    roots.sort(key=lambda row: row['root_id']); centers, prototypes = [], []
    for root in roots:
        values, ids = features(root, mode, counts), {}
        for action in root['legal_actions']:
            ids[action] = len(centers); centers.append(dict(root_id=root['root_id'], source_id=root['source_id'], action=action, features=values[action]))
        legal = root['legal_actions']; n = len(legal)*(len(legal)-1)
        tails = {a: [root['action_components'][a][0]-root['immediate_rewards'][a], *root['action_components'][a][1:]] for a in legal}
        for a in legal:
            for b in legal:
                if a != b:
                    prototypes.append(dict(root_id=root['root_id'], source_id=root['source_id'], actions=[a, b],
                        center_indices=[ids[a], ids[b]], root_mass=1./n, tail_difference=[tails[a][k]-tails[b][k] for k in range(3)]))
                    counts.update(pair_prototypes_built=1, pair_prototype_component_subtractions=3)
    columns = 98 if mode == 'PAIR98' else 224; pairs = len(centers)*(len(centers)-1)//2
    positive = [value for a, b in combinations(range(len(centers)), 2)
        if (value := distance(centers[a]['features'], centers[b]['features'])) > 0.]
    counts.update(pair_centers_built=len(centers), pair_train_center_distance_pairs=pairs,
        pair_train_distance_component_subtractions=columns*pairs, pair_train_distance_component_squares=columns*pairs,
        pair_train_distance_component_addends=columns*pairs, pair_train_nonzero_distance_tests=pairs,
        pair_median_attempts=1, pair_median_distance_values=len(positive), pair_median_computations=1, pair_design_preparations=1)
    source_counts = dict(Counter(root['source_id'] for root in roots))
    return dict(schema=SCHEMA+'.design', mode=mode, life=life, feature_names=list(relation.FEATURE_NAMES if mode == 'PAIR98' else FEATURE_NAMES),
        columns=columns, centers=centers, prototypes=prototypes, median_squared_distance=median(positive),
        root_ids=[root['root_id'] for root in roots], source_ids=sorted(source_counts), source_root_counts=source_counts,
        design_counts=dict(Counter(counts)-before))


def model_from_design(design, k, temperature, folds=None):
    return dict(schema=SCHEMA+'.model', mode=design['mode'], life=design['life'], query='risk1',
        native_teacher_query=native_exact.QUERY, horizon=native_exact.HORIZON, label_kind='exact_enumerated_vector',
        k=k, temperature=temperature, median_squared_distance=design['median_squared_distance'],
        constants=dict(columns=design['columns'], epsilon=EPS, goal_rank=11, k=k, temperature=temperature,
            projection='COMPLETE_GRAPH_ZERO_MEAN', weights='NONNEGATIVE_ROOT_MASS_LOCAL'),
        **{key: design[key] for key in ('centers', 'prototypes', 'feature_names', 'root_ids', 'source_ids', 'source_root_counts',
            'design_counts')}, source_folds=deepcopy(folds or []))


def observable(root):
    result = {key: root[key] for key in ('root_id', 'source_id', 'life', 'canonical_board', 'legal_actions',
        'immediate_rewards', 'fallback_action', 'action_map')}
    for key in ('relation_features', 'conditional_features'):
        if key in root:
            result[key] = root[key]
    return result


def geometry(model, root, counts):
    values = features(root, model['mode'], counts); legal = [a for a in ACTIONS if a in root['legal_actions']]
    distances = {a: [distance(values[a], center['features']) for center in model['centers']] for a in legal}
    orders = {f'{a}|{b}': sorted(((distances[a][row['center_indices'][0]]+distances[b][row['center_indices'][1]])/
        (2.*model['median_squared_distance']), i) for i, row in enumerate(model['prototypes'])) for a, b in combinations(legal, 2)}
    q, p, columns = len(legal)*len(model['centers']), len(legal)*(len(legal)-1)//2*len(model['prototypes']), model['constants']['columns']
    counts.update(pair_geometry_preparations=1, pair_query_center_distance_pairs=q, pair_query_distance_component_subtractions=columns*q,
        pair_query_distance_component_squares=columns*q, pair_query_distance_component_addends=columns*q,
        pair_query_prototype_distance_checks=p, pair_query_prototype_distance_additions=p, pair_query_prototype_distance_normalizations=p,
        pair_query_prototype_sorts=len(orders), pair_query_prototype_sort_items=p)
    return dict(legal_actions=legal, sorted_pairs=orders)


def decision_from_geometry(model, root, geometry, counts):
    legal = geometry['legal_actions']; n = len(legal); theta = {a: [0., 0., 0.] for a in legal}; estimated = {}
    for a, b in combinations(legal, 2):
        key = f'{a}|{b}'; nearest = geometry['sorted_pairs'][key][:model['k']]; minimum = nearest[0][0]
        neighbors = [dict(prototype_index=i, distance=d, raw_weight=math.exp(-(d-minimum)/model['temperature'])*
            model['prototypes'][i]['root_mass']) for d, i in nearest]
        total = sum(row['raw_weight'] for row in neighbors)
        for row in neighbors:
            row['weight'] = row['raw_weight']/total
        delta = [sum(row['weight']*model['prototypes'][row['prototype_index']]['tail_difference'][k] for row in neighbors) for k in range(3)]
        for k in range(3):
            theta[a][k] += delta[k]/n; theta[b][k] -= delta[k]/n
        estimated[key] = dict(actions=[a, b], estimated_tail_delta=delta, neighbors=neighbors)
        counts.update(pair_neighbor_exponentials=len(neighbors), pair_neighbor_root_mass_products=len(neighbors),
            pair_neighbor_weight_addends=len(neighbors), pair_neighbor_normalizations=len(neighbors), pair_tail_prediction_products=3*len(neighbors),
            pair_projection_divisions=6, pair_projection_accumulations=6, pair_estimates=1)
    predicted = {a: [root['immediate_rewards'][a]+theta[a][0], *theta[a][1:]] for a in legal}; pairs, residuals = {}, []
    for a, b in combinations(legal, 2):
        key = f'{a}|{b}'; projected = [theta[a][k]-theta[b][k] for k in range(3)]
        residual = [estimated[key]['estimated_tail_delta'][k]-projected[k] for k in range(3)]
        estimated[key].update(projected_tail_delta=projected, projection_residual=residual)
        pairs[key] = [predicted[a][k]-predicted[b][k] for k in range(3)]; residuals.extend(residual)
        counts.update(pair_projected_component_subtractions=3, pair_projection_residual_subtractions=3, pair_predicted_component_subtractions=3)
    chosen, best = legal[0], None
    for action in legal:
        value = utility(predicted[action])
        if best is None or value > best+EPS:
            chosen, best = action, value
    counts.update(pair_decisions=1, pair_reward_additions=n, pair_utility_evaluations=n, pair_projection_residual_squares=len(residuals))
    return dict(canonical_action=chosen, actual_action=root['action_map'][chosen], fallback=False, leaf=0,
        reason='single_legal_action' if n == 1 else 'local_pair_projection', predicted_components=predicted, predicted_pairs=pairs,
        estimated_pairs=estimated, tail_offsets=theta, projection_residual_sse=sum(value*value for value in residuals),
        projection_residual_max=max(map(abs, residuals), default=0.))


def choose_action(model, root, counts=None):
    work = Counter(); view = geometry(model, root, work); result = decision_from_geometry(model, root, view, work)
    result.update(work=dict(work), feature_work={})
    if counts is not None:
        counts.update(work)
    return result


def weights_valid(decision):
    return all(all(row['weight'] >= 0. and row['raw_weight'] >= 0. for row in pair['neighbors']) and
        abs(sum(row['weight'] for row in pair['neighbors'])-1.) <= 1e-8 for pair in decision['estimated_pairs'].values())


def heldout(model, roots, views, counts):
    groups, choices = {}, []
    for root in sorted(roots, key=lambda row: row['root_id']):
        selected = decision_from_geometry(model, observable(root), views[root['root_id']], counts)['canonical_action']
        vector = list(map(float, root['action_components'][selected])); value = utility(vector)
        groups.setdefault(root['source_id'], []).append(vector)
        choices.append(dict(root_id=root['root_id'], source_id=root['source_id'], canonical_action=selected, components=vector, utility=value))
        counts.update(pair_heldout_action_vector_reads=1, pair_heldout_component_reads=3, pair_heldout_utility_evaluations=1)
    records = []
    for source, vectors in sorted(groups.items()):
        mean = [sum(vector[k] for vector in vectors)/len(vectors) for k in range(3)]
        records.append(dict(source_id=source, roots=len(vectors), components=mean, utility=utility(mean)))
        counts.update(pair_heldout_group_component_means=3, pair_heldout_group_utility_evaluations=1)
    return records, choices


def rebuild_model(examples, mode, life=0):
    costs = Counter(new_linear_solves=0, new_eigen_decompositions=0, new_svd_decompositions=0,
        new_environment_samples=0, new_source_games=0, new_native_weight_updates=0)
    rows = [deepcopy(root) for root in examples if root['life'] == life]; sources = sorted({root['source_id'] for root in rows})
    folds = [sources[::2], sources[1::2]]; designs, heldouts, views, fold_records = [], [], [], []
    costs.update(pair_source_fold_assignments=len(sources), pair_selection_candidates=9)
    for fold, source_ids in enumerate(folds):
        training = [row for row in rows if row['source_id'] not in source_ids]
        withheld = sorted([row for row in rows if row['source_id'] in source_ids], key=lambda row: row['root_id'])
        design = prepare_design(training, mode, life, costs); model = model_from_design(design, K_VALUES[0], TEMPERATURES[0], folds)
        view = {row['root_id']: geometry(model, observable(row), costs) for row in withheld}
        designs.append(design); heldouts.append(withheld); views.append(view)
        fold_records.append(dict(fold=fold, train_sources=design['source_ids'], heldout_sources=source_ids, design=design))
    candidates, selected_k, selected_temperature, best = [], K_VALUES[0], TEMPERATURES[0], None
    for k in K_VALUES:
        for temperature in TEMPERATURES:
            results, groups = [], []
            for fold in range(2):
                before = Counter(costs); costs.update(pair_predictor_configurations=1, new_predictors_fitted=1)
                model = model_from_design(designs[fold], k, temperature, folds)
                records, choices = heldout(model, heldouts[fold], views[fold], costs); groups.extend(records)
                results.append(dict(fold=fold, group_records=records, choices=choices, prediction_counts=dict(Counter(costs)-before)))
            groups.sort(key=lambda row: row['source_id']); value = sum(row['utility'] for row in groups)/len(sources)
            candidates.append(dict(k=k, temperature=temperature, utility=value, group_records=groups, fold_results=results))
            costs.update(pair_selection_group_mean_reads=len(sources), pair_selection_score_comparisons=1)
            if best is None or value > best+EPS:
                selected_k, selected_temperature, best = k, temperature, value
    design = prepare_design(rows, mode, life, costs); costs.update(pair_predictor_configurations=1, new_predictors_fitted=1)
    model = model_from_design(design, selected_k, selected_temperature, folds)
    selection = dict(schema=SCHEMA+'.selection', mode=mode, life=life, k_values=list(K_VALUES), temperatures=list(TEMPERATURES),
        source_folds=folds, folds=fold_records, candidates=candidates, selected_k=selected_k, selected_temperature=selected_temperature,
        selected_utility=best, costs=dict(costs))
    return dict(model=model, selection=selection, costs=dict(costs))


def projection_metrics(rows):
    pairs = [pair for row in rows for pair in row['decision']['estimated_pairs'].values()]; n = len(pairs)
    return dict(roots=len(rows), pairs=n,
        max_abs_components=[max((abs(pair['projection_residual'][k]) for pair in pairs), default=0.) for k in range(3)],
        mean_abs_components=[math.fsum(abs(pair['projection_residual'][k]) for pair in pairs)/n if n else 0. for k in range(3)],
        utility_sign_flips=sum(abs(utility(pair['estimated_tail_delta'])) > EPS and abs(utility(pair['projected_tail_delta'])) > EPS and
            utility(pair['estimated_tail_delta'])*utility(pair['projected_tail_delta']) < 0. for pair in pairs))


def source_diagnostics(roots, model):
    records, work = [], Counter()
    for root in sorted(roots, key=lambda row: row['root_id']):
        decision = choose_action(model, observable(root), work)
        if not weights_valid(decision):
            raise ValueError('SOURCE pair weights must be nonnegative and normalized')
        for pair in decision['estimated_pairs'].values():
            del pair['neighbors']
        legal = [a for a in ACTIONS if a in root['legal_actions']]; vectors = root['action_components']
        values = {a: utility(vectors[a]) for a in legal}; best = max(values.values())
        oracle = next(a for a in legal if values[a] >= best-EPS); action = decision['canonical_action']; regret = best-values[action]
        records.append(dict(root_id=root['root_id'], source_id=root['source_id'], decision=decision, action=action,
            components=list(vectors[action]), utility=values[action], oracle_action=oracle, oracle_components=list(vectors[oracle]),
            oracle_utility=best, regret=regret, positive_regret=regret > EPS))
        work.update(source_observable_root_preparations=1, source_complete_component_reads=3*len(legal), source_action_utility_evaluations=len(legal),
            source_selected_component_reads=3, source_oracle_component_reads=3, source_regret_subtractions=1,
            source_oracle_action_comparisons=legal.index(oracle)+1, source_diagnostic_root_records=1)
    n = len(records)
    metrics = dict(roots=n, components=[math.fsum(row['components'][k] for row in records)/n for k in range(3)],
        utility=math.fsum(row['utility'] for row in records)/n,
        oracle_components=[math.fsum(row['oracle_components'][k] for row in records)/n for k in range(3)],
        oracle_utility=math.fsum(row['oracle_utility'] for row in records)/n, regret_mean=math.fsum(row['regret'] for row in records)/n,
        positive_regret_roots=sum(row['positive_regret'] for row in records), fallback_roots=sum(row['decision']['fallback'] for row in records))
    work.update(source_summary_component_reads=6*n, source_summary_scalar_reads=3*n, source_summary_flag_reads=2*n)
    return dict(root_records=records, metrics=metrics, projection_residuals=projection_metrics(records), work=dict(work))


def cohort_cases():
    edges = [(4*r+c, 4*r+c+1) for r in range(4) for c in range(3)]+[(4*r+c, 4*(r+1)+c) for r in range(3) for c in range(4)]
    cases = []
    for replica in range(4):
        for index, (a, b) in enumerate(edges):
            seed = 1940200+24*replica+index; rng = random.Random(seed)
            board = [rng.randint(1, 10) for _ in range(16)]; board[a] = board[b] = 1+index%10
            for position in rng.sample([p for p in range(16) if p not in (a, b)], index%3):
                board[position] = 0
            cases.append(dict(split='TARGET', replica=replica, stratum=index, horizon=3, seed=seed,
                name=f'v194_target_r{replica:02d}_{index:02d}', board=board, vacancies=index%3))
    return cases


def freeze_choices(roots, models):
    choices, work = {name: [] for name in (*MODEL_NAMES, 'FALLBACK')}, Counter()
    for root in roots:
        seen = relation.observable(root); seen['conditional_features'] = root['conditional_features']
        for name in MODEL_NAMES:
            chooser = choose_action if name in MODES else nonlinear.choose_action if name == 'NONLINEAR' else relation.choose_action if name == 'RELATION' else (
                relation.dense.choose_action if name in ('LINEAR', 'INTERACT') else relation.shared.choose_action if name in ('SHARED', 'OLD_SHARED')
                else relation.exact.choose_action if name == 'ONE' else relation.layout.choose_action)
            decision = chooser(models[name], seen); work.update(decision['work']); work.update(decision.get('feature_work', {})); work['frozen_model_choices'] += 1
            choices[name].append(dict(root_id=root['root_id'], mode=name, canonical_action=decision['canonical_action'],
                actual_action=decision['actual_action'], fallback=decision['fallback'], decision=decision))
        action = root['fallback_action']; work['frozen_fallback_choices'] += 1
        choices['FALLBACK'].append(dict(root_id=root['root_id'], mode='FALLBACK', canonical_action=action, actual_action=root['action_map'][action],
            fallback=False, decision=dict(reason='observable_immediate_reward', work={'frozen_fallback_choices': 1})))
    return choices, dict(work)


def verify_decision(saved, expected):
    return close(saved, expected) and saved['canonical_action'] == expected['canonical_action'] and weights_valid(saved)


def summarize(roots, labels, choices, selections, models, source):
    label_by_id = {row['root_id']: row['action_components'] for row in labels}
    chosen = {name: {row['root_id']: row for row in rows} for name, rows in choices.items()}; names = (*MODEL_NAMES, 'FALLBACK', 'ORACLE'); records = []
    for root in roots['TARGET']:
        vectors = label_by_id[root['root_id']]; oracle = root['legal_actions'][0]
        for action in root['legal_actions'][1:]:
            if utility(vectors[action]) > utility(vectors[oracle])+EPS:
                oracle = action
        outcomes = {}
        for name in names:
            choice = None if name == 'ORACLE' else chosen[name][root['root_id']]
            action = oracle if choice is None else choice['canonical_action']; vector = list(vectors[action])
            outcomes[name] = dict(action=action, components=vector, utility=utility(vector), regret=utility(vectors[oracle])-utility(vector),
                fallback=False if choice is None else choice['fallback'])
        records.append(dict(root_id=root['root_id'], replica=root['replica'], stratum=root['stratum'], models=outcomes))
    def means(rows):
        result = {}
        for name in names:
            vector = [math.fsum(row['models'][name]['components'][k] for row in rows)/len(rows) for k in range(3)]
            result[name] = dict(components=vector, utility=utility(vector), positive_regret_roots=sum(row['models'][name]['regret'] > EPS for row in rows),
                fallback_roots=sum(row['models'][name]['fallback'] for row in rows))
        return result
    def contrasts(rows):
        selected = [dict(root_id=row['root_id'], models={'CONDITIONAL': row['models']['CONDITIONAL']}) for row in rows]
        return {'CONDITIONAL_MINUS_'+name: relation.coverage.coverage_effect(selected,
            [dict(root_id=row['root_id'], models={'CONDITIONAL': row['models'][name]}) for row in rows], 'CONDITIONAL') for name in COMPARATORS}
    metrics, effects = means(records), contrasts(records)
    replicas = [dict(replica=replica, roots=len(rows), models=means(rows), comparisons=contrasts(rows)) for replica in sorted({row['replica'] for row in records})
        for rows in [[row for row in records if row['replica'] == replica]]]
    source_modes = {mode: dict(selected_k=selections[mode]['selected_k'], selected_temperature=selections[mode]['selected_temperature'],
        source_heldout_utility=selections[mode]['selected_utility'], feature_columns=models[mode]['constants']['columns'],
        median_squared_distance=models[mode]['median_squared_distance'], actual=source[mode]['metrics'],
        source_selection=[dict(k=row['k'], temperature=row['temperature'], utility=row['utility']) for row in selections[mode]['candidates']]) for mode in ('CONDITIONAL', 'PAIR98')}
    headroom = metrics['ORACLE']['utility']-metrics['ONE']['utility']
    return dict(schema=SCHEMA+'.summary', complete=True, roots=len(records),
        SOURCE=dict(roots=len(roots['SOURCE']), design_groups=len({root['source_id'] for root in roots['SOURCE']}), modes=source_modes),
        models=metrics, comparisons=effects, replicas=replicas, root_records=records,
        projection_residuals=dict(SOURCE={mode: projection_metrics(source[mode]['root_records']) for mode in MODES},
            TARGET={mode: projection_metrics(choices[mode]) for mode in MODES}),
        oracle_minus_one=headroom, oracle_minus_conditional=metrics['ORACLE']['utility']-metrics['CONDITIONAL']['utility'],
        headroom_closed_fraction=effects['CONDITIONAL_MINUS_ONE']['utility']/headroom if headroom > EPS else None,
        whole_cohort_positive_vs_primary=all(effects['CONDITIONAL_MINUS_'+name]['utility'] > EPS for name in ('PAIR98', 'LINEAR', 'NONLINEAR', 'OLD_SHARED')),
        all_replicas_positive_vs_primary=all(row['comparisons']['CONDITIONAL_MINUS_'+name]['utility'] > EPS for row in replicas for name in ('PAIR98', 'LINEAR', 'NONLINEAR', 'OLD_SHARED')),
        new_environment_samples=0, new_source_games=0, new_native_weight_updates=0, new_predictors_fitted=38, new_prototype_configurations=38, new_parameter_solves=0)


def analyze(directory):
    begun = perf_counter(); directory = Path(directory); checks, io, bindings = [], Counter(), Counter()
    def read(relative):
        raw = (directory/relative).read_bytes(); io.update(json_read_operations=1, input_bytes_read=len(raw)); return json.loads(raw)
    def check(name, condition):
        checks.append(dict(name=name, passed=bool(condition)))
    run, inputs = read('run.json'), read('input_manifest.json')
    names = ('v193_stage_checks.json', 'v193_run.json', 'v193_roots.json', 'nonlinear_model.json',
        'relation_model.json', 'expanded_models.json', 'baseline_models.json', 'learned_rule.json', 'dense_models.json')
    check('nine_frozen_SOURCE_and_control_inputs', [(row['saved_ref'], row['phase']) for row in inputs] ==
        [(f'inputs/inherited/{name}', 'protocol_frozen') for name in names])
    for row in inputs:
        saved, original = (directory/row['saved_ref']).read_bytes(), Path(row['path']).read_bytes()
        io.update(input_byte_comparisons=1, input_comparison_bytes_read=len(saved)+len(original))
        check('retained_input:'+row['saved_ref'], saved == original and len(saved) == row['bytes'])
    stage, inherited = read('inputs/inherited/v193_stage_checks.json'), read('inputs/inherited/v193_run.json')
    check('settled_V193_complete', stage['valid'] and inherited['status'] == 'complete')
    source = deepcopy(read('inputs/inherited/v193_roots.json')['SOURCE'])
    check('unchanged_SOURCE143_36_groups_98_features_and_complete_labels', len(source) == 143 and
        len({row['source_id'] for row in source}) == 36 and all(len(root['relation_features'][a]) == 98 and
        len(root['action_components'][a]) == 3 for root in source for a in root['legal_actions']))
    source_features = cache_roots(source)
    check('once_SOURCE_rank_bin_projection_paid', run['costs']['source_features']['counts'] == source_features and
        source_features.get('conditional_feature_maps_derived') == 143)
    saved_models, saved_selections, saved_source = read('models.json'), read('selection.json'), read('source_diagnostics.json')
    check('exact_two_new_model_rosters', set(saved_models) == set(saved_selections) == set(saved_source) == set(MODES))
    models, selections, diagnostics, learning = {}, {}, {}, {}
    for mode in MODES:
        fitted = rebuild_model(source, mode); models[mode], selections[mode], learning[mode] = fitted['model'], fitted['selection'], fitted['costs']
        check(mode+'_independent_train_only_prototypes_median_and_actual_group_selection', close(saved_selections[mode], selections[mode]))
        check(mode+'_retained_full_model_and_native_teacher_metadata', close(saved_models[mode], models[mode]))
        paid = learning[mode]
        check(mode+'_three_designs_19_configurations_and_geometry_reuse_paid', paid['pair_design_preparations'] == 3 and
            paid['pair_predictor_configurations'] == paid['new_predictors_fitted'] == 19 and paid['pair_geometry_preparations'] == 143 and
            all(paid[key] == 0 for key in ('new_linear_solves', 'new_eigen_decompositions', 'new_svd_decompositions')) and
            run['costs']['learning_'+mode]['counts'] == paid)
        diagnostics[mode] = source_diagnostics(source, models[mode])
        check(mode+'_actual_SOURCE_RFS_choices_and_compact_projection_diagnostics', close(saved_source[mode], diagnostics[mode]))
        check(mode+'_paid_actual_SOURCE_evaluation', run['costs']['source_evaluation_'+mode]['counts'] == diagnostics[mode]['work'])
    cases = cohort_cases(); target, observation_work = relation.observe_roots(cases)
    feature_work = relation.coverage.cache_roots(target); relation_work = relation.cache_roots(target); conditional_work = cache_roots(target)
    roots = dict(SOURCE=source, TARGET=target)
    check('96_fresh_seeded_H3_cases', read('target_cases.json') == cases)
    check('unchanged_SOURCE_and_FRESH_observations_all_cached_features', close(read('roots.json'), roots))
    observed = run['costs']['observations']
    check('once_fresh_observation_geometry_relation_conditional_costs', observed['counts'] == observation_work and
        observed['feature_counts'] == feature_work and observed['relation_counts'] == relation_work and observed['conditional_counts'] == conditional_work)
    expanded, old, dense = read('inputs/inherited/expanded_models.json'), read('inputs/inherited/baseline_models.json'), read('inputs/inherited/dense_models.json')
    all_models = dict(expanded, **dense, **models, NONLINEAR=read('inputs/inherited/nonlinear_model.json'),
        RELATION=read('inputs/inherited/relation_model.json'), OLD_SHARED=old['SHARED'], ONE=old['ONE'])
    choices, choice_work = freeze_choices(target, all_models); saved_choices = read('choices.json')
    check('all_SOURCE_selected_and_fixed_control_choices_before_labels', close(saved_choices, choices))
    for mode in MODES:
        check(mode+'_actual_EPS_actions_and_nonnegative_normalized_neighbor_weights',
            all(verify_decision(saved['decision'], expected['decision']) for saved, expected in zip(saved_choices[mode], choices[mode], strict=True)))
    check('paid_frozen_RFS_decisions', run['costs']['choices']['counts'] == choice_work)
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
        accounting = accounting and costs['label_evaluation']['root_labels_emitted'] == 1
        accounting = accounting and export == dict(teacher_encoding_records_read=construction['concrete_states'], teacher_policy_records=n,
            teacher_policy_action_reads=n, teacher_policy_tile_reads=16*n)
        check('settled_acquisition_caps_and_export_costs:'+root['root_id'], accounting)
        for kind in ('construction', 'planning', 'label_evaluation', 'teacher_export', 'compilation'):
            label_work.update({kind+'.'+key: value for key, value in costs[kind].items() if type(value) is int})
    check('all_new_canonical_RFS_vectors_and_fraction_metadata', close(read('labels.json'), labels))
    summary = summarize(roots, labels, choices, selections, models, diagnostics)
    check('13_arm_actual_RFS_11_contrasts_replicas_and_projection_components', close(read('summary.json'), summary))
    phases = ('protocol_frozen', 'source_selection', 'models_frozen', 'target_roots', 'target_choices_frozen', 'target_labels', 'complete')
    check('SOURCE_selection_and_all_choices_frozen_before_target_labels', [(row['phase'], row['input_reads']) for row in run['phase_history']] ==
        [(phase, 0 if index == 0 else 9) for index, phase in enumerate(phases)])
    check('all_paid_input_and_label_counts', run['costs']['input_counts'] == dict(json_read_operations=9,
        input_bytes_read=sum(row['bytes'] for row in inputs), input_bytes_retained=sum(row['bytes'] for row in inputs)) and
        run['costs']['labels']['counts'] == dict(label_work))
    accounting = all(run[key] == 96 for key in ('new_boards_generated', 'new_reference_kernel_attempts', 'new_reference_kernels',
        'new_teacher_plans', 'new_exact_label_roots', 'completed_roots'))
    accounting = accounting and run['new_learning_attempts'] == 2 and run['new_predictors_fitted'] == run['new_prototype_configurations'] == 38
    accounting = accounting and run['resource_cap_per_board'] == 200000 and all(run[key] == 0 for key in
        ('new_parameter_solves', 'new_environment_samples', 'new_source_games', 'new_native_weight_updates'))
    check('two_SOURCE_selections_38_configurations_96_labels_no_parameter_solves', accounting)
    valid = all(row['passed'] for row in checks); complete = valid and run['status'] == 'complete' and summary['complete']
    return dict(schema=SCHEMA+'.analysis', valid=valid, complete=complete, primary_complete=complete, checks=checks,
        passed_checks=sum(row['passed'] for row in checks), total_checks=len(checks), summary=summary,
        costs=dict(independent_parameter_solves=0, independent_eigen_solves=0, independent_svd_solves=0,
            new_environment_samples=0, physical_branches_replayed=0, new_kernels_reintegrated=0, old_models_refitted=0,
            independent_input_counts=dict(io), independent_SOURCE_feature_counts=source_features, reconstructed_learning_counts=learning,
            independent_source_evaluation_counts={mode: diagnostics[mode]['work'] for mode in MODES},
            independent_observation_counts=observation_work, independent_feature_counts=feature_work,
            independent_relation_counts=relation_work, independent_conditional_counts=conditional_work, independent_choice_counts=choice_work,
            independent_new_label_binding_counts=dict(bindings), reconstructed_acquisition_counts=dict(label_work),
            original_run_costs=run['costs'], inherited_cost_refs=run['inherited_cost_refs'], test_refs=run['test_refs'], seconds=perf_counter()-begun))


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--directory', type=Path, default=OUTPUT)
    args = parser.parse_args(); result = analyze(args.directory)
    (args.directory/'analysis.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps(dict(valid=result['valid'], complete=result['complete'], passed=result['passed_checks'], total=result['total_checks'])))


if __name__ == '__main__':
    main()
