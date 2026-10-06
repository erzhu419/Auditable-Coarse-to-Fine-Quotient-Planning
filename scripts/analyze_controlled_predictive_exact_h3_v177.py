"""Independent fixed-teacher H3 vectors and exact-label partition reconstruction."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction
from itertools import combinations
import argparse
import json
import math
from pathlib import Path
import sys
from time import perf_counter

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))
from scripts import analyze_controlled_predictive_utility_partition_v174 as previous
from scripts.analyze_controlled_predictive_fixed_program_v167 import _equal

ACTIONS = ('DOWN', 'LEFT', 'RIGHT', 'UP')
EPS = 1e-12
frames = previous.previous.previous.previous.frames
ground = previous.previous.previous.previous.prior.ground


def utility(vector):
    return vector[0]-vector[1]+vector[2]


def root_from_case(case, ordinal, cohort, counts=None):
    counts = Counter() if counts is None else counts
    board = list(case['board'])
    canonical, transform = frames.frame(board)
    local = Counter(root_records_read=1, root_tile_reads=16, root_board_transforms=8)
    legal, action_map, immediate = [], {}, {}
    for action in ACTIONS:
        actual = frames.transport(transform, [action])[0]
        local.update(root_action_transports=1, root_ground_swipe_calls=1)
        _, score, valid = ground.swipe_board_v1(tuple(board), ground.Swipe2048Action(actual))
        if valid:
            legal.append(action); action_map[action] = actual; immediate[action] = score/2048.
    if not legal:
        raise ValueError('An ACTIVE source/target root must have a legal action')
    best, value = legal[0], None
    for action in legal:
        local['fallback_immediate_reward_comparisons'] += 1
        if value is None or immediate[action] > value+EPS:
            best, value = action, immediate[action]
    counts.update(local)
    return dict(root_id=case['name'], life=0, source_id=f'DESIGN_SOURCE:{ordinal//4:02d}',
                cohort=cohort, ordinal=ordinal, horizon=case['horizon'], board=board,
                canonical_board=list(canonical), frame=transform.value, legal_actions=legal,
                action_map=action_map, immediate_rewards=immediate, fallback_action=best, teacher_action=best,
                fallback_origin='largest_exact_immediate_reward', work=dict(local))


def evaluate_payload(payload, plan, root_indices=None):
    """Evaluate a saved policy, never replace its continuation by an oracle."""
    counts = Counter()
    cells = {row[0]: (row[1], row[2]) for row in payload['cells']}
    if len(cells) != len(payload['cells']):
        raise ValueError('Duplicate kernel cells')
    rows = {}
    for state, action, atoms in payload['rows']:
        if (state, action) in rows or state not in cells or cells[state][1] != 'ACTIVE':
            raise ValueError('Duplicate/non-ACTIVE action row')
        counts['kernel_rows_read'] += 1; restored = []
        for atom in atoms:
            counts.update(kernel_outcomes_read=1, horizon_edge_checks=1)
            if len(atom) == 5:
                pn, pd, successor, rn, rd = atom
                probability, reward = Fraction(pn, pd), Fraction(rn, rd)
                counts['kernel_rational_outcomes_loaded'] += 1
            elif len(atom) == 3:
                p, successor, r = atom
                probability = Fraction(p).limit_denominator(2560)
                reward = Fraction(round(r*2048), 2048)
                pe, re = float(abs(probability-Fraction(p))), float(abs(reward-Fraction(r)))
                if pe > EPS or re > EPS:
                    raise ValueError('Kernel float lies outside the frozen rational recovery grid')
                counts.update(kernel_probability_recoveries=1, kernel_reward_recoveries=1)
                counts['probability_grid_changed_atoms'] += int(pe > 0.)
                counts['reward_grid_changed_atoms'] += int(re > 0.)
                counts['probability_grid_max_error'] = max(counts['probability_grid_max_error'], pe)
                counts['reward_grid_max_error'] = max(counts['reward_grid_max_error'], re)
            else:
                raise ValueError('Unsupported kernel atom')
            if probability < 0 or successor not in cells or cells[successor][0] != cells[state][0]-1:
                raise ValueError('Kernel probability/successor horizon binding')
            restored.append((probability, successor, reward))
        if sum(atom[0] for atom in restored) != 1:
            raise ValueError('An exact kernel row must have probability mass one')
        rows[state, action] = restored
        counts['probability_mass_checks'] += 1
    counts['kernel_cells_read'] = len(cells)
    values = {}
    def action_value(state, action, prefix):
        key = state, action
        if key not in rows:
            raise ValueError('Frozen continuation selects an absent legal action')
        vector = [Fraction(0), Fraction(0), Fraction(0)]
        counts[prefix+'_action_rows_evaluated'] += 1
        for probability, successor, reward in rows[key]:
            tail = values[successor]
            vector[0] += probability*(reward+tail[0])
            vector[1] += probability*tail[1]
            vector[2] += probability*tail[2]
            counts[prefix+'_outcomes_evaluated'] += 1
            counts[prefix+'_component_accumulations'] += 3
        return vector
    for state, (horizon, status) in sorted(cells.items(), key=lambda item: (item[1][0], item[0])):
        if status != 'ACTIVE':
            if status not in ('WON', 'LOST', 'CUTOFF') or status == 'CUTOFF' and horizon != 0:
                raise ValueError('Unknown terminal or nonzero-horizon cutoff')
            values[state] = [Fraction(0), Fraction(status == 'LOST'), Fraction(status == 'WON')]
            counts['terminal_vector_initializations'] += 1
        else:
            if horizon <= 0:
                raise ValueError('An ACTIVE cell requires a positive horizon')
            action = plan['policy'].get(str(state))
            values[state] = action_value(state, action, 'teacher')
            counts.update(teacher_policy_reads=1, teacher_states_evaluated=1)
        if 'values' in plan and str(state) in plan['values'] and not math.isclose(
                float(utility(values[state])), plan['values'][str(state)], rel_tol=1e-10, abs_tol=1e-10):
            raise ValueError('Saved scalar teacher value disagrees with its complete-vector continuation')
    labels = []
    for index in list(range(len(payload['roots']))) if root_indices is None else root_indices:
        state = payload['roots'][index]; horizon, status = cells[state]
        legal = [action for action in ACTIONS if (state, action) in rows]
        vectors, immediate, fractions, exact_vectors = {}, {}, {}, {}
        for action in legal:
            result = action_value(state, action, 'root')
            exact_vectors[action] = result
            vectors[action] = [float(x) for x in result]
            fractions[action] = [[x.numerator, x.denominator] for x in result]
            row_rewards = {reward for _, _, reward in rows[state, action]}
            if len(row_rewards) != 1:
                raise ValueError('A concrete first swipe must have deterministic reward')
            immediate[action] = float(next(iter(row_rewards)))
            counts['oracle_utility_evaluations'] += 1
        oracle = None
        for action in legal:
            if oracle is None or utility(exact_vectors[action]) > utility(exact_vectors[oracle])+Fraction(1, 10**12):
                oracle = action
        labels.append(dict(root_index=index, root_cell=state, horizon=horizon, status=status,
                           legal_actions=legal, immediate_rewards=immediate, action_components=vectors, action_component_fractions=fractions,
                           continuation_components=[float(x) for x in values[state]], oracle_action=oracle,
                           oracle_components=[float(x) for x in values[state]] if oracle is None else vectors[oracle],
                           teacher_action=plan['policy'].get(str(state))))
        counts['root_labels_emitted'] += 1
    return dict(labels=labels, counts=dict(counts))


def exact_pair_samples(example):
    pairs = list(combinations(example['legal_actions'], 2))
    samples = []
    for a, b in pairs:
        va, vb = example['action_components'][a], example['action_components'][b]
        vector = [va[k]-vb[k] for k in range(3)]
        vector[0] = (va[0]-example['immediate_rewards'][a])-(vb[0]-example['immediate_rewards'][b])
        samples.append((ACTIONS.index(a), ACTIONS.index(b), 1./len(pairs), vector))
    return samples


def exact_leaf_fit(examples, counts):
    """One exact pair label per action pair; no suffix or pseudo-replication."""
    counts.update(leaf_fits=1, leaf_fit_root_visits=len(examples))
    matrix = [[0.]*4 for _ in ACTIONS]; rhs = [[0.]*4 for _ in range(3)]
    adjacency = [set() for _ in ACTIONS]; support = {action: [] for action in ACTIONS}
    samples = []; pair_roots = {f'{a}|{b}': set() for a, b in combinations(ACTIONS, 2)}; total_weight = 0.
    for example in examples:
        for action in example['legal_actions']:
            support[action].append(example['root_id'])
        for a, b, weight, delta in exact_pair_samples(example):
            matrix[a][a] += weight; matrix[b][b] += weight; matrix[a][b] -= weight; matrix[b][a] -= weight
            adjacency[a].add(b); adjacency[b].add(a)
            for k in range(3):
                rhs[k][a] += weight*delta[k]; rhs[k][b] -= weight*delta[k]
            samples.append((a, b, weight, delta)); pair_roots[f'{ACTIONS[a]}|{ACTIONS[b]}'].add(example['root_id']); total_weight += weight
            counts.update(leaf_pair_observations=1, laplacian_scalar_accumulations=4, rhs_component_accumulations=6)
    components, unseen = [], set(range(4))
    while unseen:
        connected = {min(unseen)}; frontier = list(connected)
        while frontier:
            node = frontier.pop()
            for neighbor in adjacency[node]-connected:
                connected.add(neighbor); frontier.append(neighbor)
        unseen -= connected; components.append(sorted(connected))
    potentials = [[0.]*3 for _ in ACTIONS]
    if samples:
        counts.update(laplacian_solves=1, laplacian_matrix_cells=16, laplacian_rhs_cells=12,
                      zero_sum_constraint_rows=len(components), zero_sum_constraint_cells=4*len(components),
                      centered_solver_matrix_cells=4*(4+len(components)), centered_solver_rhs_cells=3*(4+len(components)))
    solver = previous.previous.previous.solve_centered
    for connected in components:
        for k in range(3):
            for action, value in zip(connected, solver(matrix, rhs[k], connected)):
                potentials[action][k] = value
    loss = math.fsum(weight*math.fsum((potentials[a][k]-potentials[b][k]-delta[k])**2 for k in range(3)) for a, b, weight, delta in samples)
    if samples:
        counts['loss_component_residuals'] += len(samples)*3
    return dict(root_ids=sorted(row['root_id'] for row in examples), source_ids=sorted({row['source_id'] for row in examples}),
                action_root_ids={action: sorted(ids) for action, ids in support.items()}, pair_root_ids={key: sorted(ids) for key, ids in pair_roots.items()},
                coefficients={action: potentials[i] for i, action in enumerate(ACTIONS)}, connected_components=[[ACTIONS[i] for i in row] for row in components],
                loss=loss, pair_observations=len(samples), total_pair_weight=total_weight)


def prepare_exact(examples, life, counts):
    examples = list(examples)
    sources = sorted({row['source_id'] for row in examples if row['life'] == life})
    if len(sources) != 12:
        raise ValueError('Twelve frozen design source groups required')
    folds = [sources[::2], sources[1::2]]
    source_fold = {source: fold for fold, group in enumerate(folds) for source in group}
    kept, labels = [], []
    for example in examples:
        counts['examples_examined'] += 1
        if example['life'] != life:
            counts['other_life_examples_excluded'] += 1; continue
        legal = [action for action in ACTIONS if action in example['legal_actions']]
        if not legal or len(legal) != len(example['legal_actions']) or len(example['canonical_board']) != 16:
            raise ValueError('Complete canonical legal root required')
        if 'suffix_trials' in example or 'seed' in example or set(example['action_components']) != set(legal):
            raise ValueError('One exact full vector per legal action required')
        if any(len(vector) != 3 or not all(math.isfinite(x) for x in vector) for vector in example['action_components'].values()):
            raise ValueError('Finite complete exact vectors required')
        counts.update(examples_fitted=1, root_feature_tile_reads=16, legal_action_reads=len(legal), immediate_reward_reads=len(legal),
                      exact_action_vector_reads=len(legal), label_component_reads=3*len(legal), tail_reward_subtractions=len(legal))
        pairs = []
        for a, b, weight, vector in exact_pair_samples(dict(example, legal_actions=legal)):
            pairs.append(dict(actions=[ACTIONS[a], ACTIONS[b]], weight=weight, components=vector))
            counts.update(paired_vector_labels=1, paired_component_subtractions=3)
        labels.append(dict(root_id=example['root_id'], source_id=example['source_id'], legal_actions=legal, label_kind='exact_enumerated_vector', pairs=pairs))
        kept.append(dict(example, legal_actions=legal, fold=source_fold[example['source_id']], observed_means=deepcopy(example['action_components'])))
        counts.update(utility_immediate_reward_loads=len(legal), observed_terminal_action_averages=len(legal))
    kept.sort(key=lambda row: row['root_id']); labels.sort(key=lambda row: row['root_id'])
    if not kept or len({row['root_id'] for row in kept}) != len(kept):
        raise ValueError('Distinct exact design roots required')
    counts['source_fold_assignments'] += len(sources)
    return kept, folds, labels


def exact_candidate(examples, indices, node_id, cell, threshold, folds, source_counts, work):
    work.update(utility_candidates_evaluated=1, utility_split_feature_threshold_tests=len(indices))
    sides = {i: 'left' if examples[i]['canonical_board'][cell] <= threshold else 'right' for i in indices}
    partitions = [{side: [i for i in indices if examples[i]['fold'] == fold and sides[i] == side] for side in ('left', 'right')} for fold in range(2)]
    record = dict(candidate_id=f'{node_id}:{cell}:{threshold}', node_id=node_id, cell=cell, threshold=threshold,
                  comparable=False, score=None, selected=False, reason=None, directions=[])
    for fold in range(2):
        stats = {side: dict(roots=len(partitions[fold][side]), sources=sorted({examples[i]['source_id'] for i in partitions[fold][side]})) for side in ('left', 'right')}
        record['directions'].append(dict(fit_fold=fold, heldout_fold=1-fold, fit_children=stats, root_decisions=[], source_effects=[], mean_components=None, score=None))
    if any(stats['roots'] < 8 for direction in record['directions'] for stats in direction['fit_children'].values()):
        record['reason'] = 'insufficient_fit_child_roots'; return record
    if any(len(stats['sources']) < 2 for direction in record['directions'] for stats in direction['fit_children'].values()):
        record['reason'] = 'insufficient_fit_child_sources'; return record
    work['utility_structurally_eligible_candidates'] += 1; complete = True
    for fold, direction in enumerate(record['directions']):
        parent = exact_leaf_fit([examples[i] for i in sorted(partitions[fold]['left']+partitions[fold]['right'])], work)
        children = {side: exact_leaf_fit([examples[i] for i in partitions[fold][side]], work) for side in ('left', 'right')}
        work.update(crossfit_parent_leaf_fits=1, crossfit_child_leaf_fits=2)
        direction['parent_coefficients'] = deepcopy(parent['coefficients'])
        direction['child_coefficients'] = {side: deepcopy(fit['coefficients']) for side, fit in children.items()}
        for i in indices:
            example = examples[i]
            if example['fold'] == fold:
                continue
            side = sides[i]
            parent_decision = previous.supported_action(parent, example, work)
            child_decision = previous.supported_action(children[side], example, work)
            supported = parent_decision['support']['complete'] and child_decision['support']['complete']; complete &= supported
            direction['root_decisions'].append(dict(root_id=example['root_id'], source_id=example['source_id'], side=side,
                                                    parent=parent_decision, child=child_decision, complete=supported))
    if not complete:
        record['reason'] = 'unsupported_heldout_policy'; return record
    work['utility_comparable_candidates'] += 1
    by_root = {examples[i]['root_id']: examples[i] for i in indices}
    for direction in record['directions']:
        sums = {source: [0., 0., 0.] for source in folds[direction['heldout_fold']]}; in_region = Counter()
        for row in direction['root_decisions']:
            example = by_root[row['root_id']]
            a = example['action_components'][row['parent']['canonical_action']]
            b = example['action_components'][row['child']['canonical_action']]
            vector = [x-y for x, y in zip(b, a)]
            row.update(observed_parent_components=list(a), observed_child_components=list(b), actual_difference_components=vector)
            for k in range(3):
                sums[example['source_id']][k] += vector[k]
            in_region[example['source_id']] += 1
            work.update(crossfit_observed_terminal_component_reads=6, crossfit_actual_component_subtractions=3, crossfit_source_component_accumulations=3)
        for source in sorted(sums):
            vector = [value/source_counts[source] for value in sums[source]]
            direction['source_effects'].append(dict(source_id=source, roots=source_counts[source], in_region_roots=in_region[source], components=vector, utility=utility(vector)))
            work.update(crossfit_source_component_normalizations=3, crossfit_source_utility_evaluations=1)
        vector = [math.fsum(row['components'][k] for row in direction['source_effects'])/len(direction['source_effects']) for k in range(3)]
        direction.update(mean_components=vector, score=utility(vector)); work['crossfit_direction_scores'] += 1
    score = math.fsum(row['score'] for row in record['directions'])/2
    record.update(comparable=True, score=score, reason='positive_utility' if score > EPS else 'utility_not_positive')
    return record


def fit_exact_partition(examples, life=0):
    fit_work, search_work, node_work = Counter(), Counter(), Counter()
    examples, folds, labels = prepare_exact(examples, life, fit_work)
    source_counts = dict(Counter(row['source_id'] for row in examples))
    nodes = [dict(node_id=0, kind='leaf', leaf_id=0)]; active = {0: list(range(len(examples)))}; node_indices = {0: list(active[0])}; records = []
    def search(node, indices):
        search_work['utility_search_nodes_evaluated'] += 1
        if any(sum(examples[i]['fold'] == fold for i in indices) < 16 for fold in range(2)):
            search_work['utility_nodes_without_two_fit_children'] += 1; return None
        best = None
        for cell in range(16):
            for threshold in range(10):
                candidate = exact_candidate(examples, indices, node, cell, threshold, folds, source_counts, search_work); records.append(candidate)
                if candidate['score'] is None or candidate['score'] <= EPS:
                    continue
                search_work['utility_positive_candidate_comparisons'] += 1
                if best is None or candidate['score'] > best['score']+EPS:
                    best = candidate
        return best
    candidates = {0: search(0, active[0])}
    while len(active) < 16:
        best = None
        for node in sorted(candidates):
            candidate = candidates[node]
            if candidate is None:
                continue
            search_work['utility_global_candidate_comparisons'] += 1
            if best is None or candidate['score'] > best['score']+EPS:
                best = candidate
        if best is None:
            break
        node, first, second = best['node_id'], len(nodes), len(nodes)+1; best['selected'] = True
        left = [i for i in active[node] if examples[i]['canonical_board'][best['cell']] <= best['threshold']]
        right = [i for i in active[node] if examples[i]['canonical_board'][best['cell']] > best['threshold']]
        nodes[node] = dict(node_id=node, kind='split', cell=best['cell'], threshold=best['threshold'], left=first, right=second, utility_gain=best['score'])
        del active[node], candidates[node]
        for child, indices in ((first, left), (second, right)):
            nodes.append(dict(node_id=child, kind='leaf', leaf_id=child)); active[child] = indices; node_indices[child] = indices
        search_work['utility_splits_applied'] += 1
        if len(active) < 16:
            for child in (first, second):
                candidates[child] = search(child, active[child])
    fits = {}
    for node in nodes:
        index = node['node_id']; fits[str(index)] = dict(leaf_id=index, **exact_leaf_fit([examples[i] for i in node_indices[index]], node_work))
        node_work['full_discovery_node_fits'] += 1
    training = [{key: deepcopy(row[key]) for key in ('root_id', 'source_id', 'life', 'fold', 'canonical_board', 'legal_actions', 'immediate_rewards', 'action_components')} | dict(provenance=deepcopy(row.get('provenance', {}))) for row in examples]
    return dict(schema='acfqp.exact_h3_learning.v177', life=life, query='risk1', native_teacher_query='goal_1_risk_1', horizon=3, mode='PART_UNPRUNED', label_kind='exact_enumerated_vector',
                constants=dict(min_child_roots=8, min_child_sources=2, min_action_roots=4, max_leaves=16, epsilon=EPS, discovery_design_groups=12),
                root_ids=[row['root_id'] for row in examples], source_ids=sorted(source_counts), source_folds=folds, source_root_counts=source_counts,
                nodes=nodes, groups={}, leaves=[deepcopy(fits[str(node)]) for node in sorted(active)], node_fits=fits,
                fit_labels=labels, training_outcomes=training, candidate_records=records, fit_counts=dict(fit_work),
                utility_search_counts=dict(search_work), node_fit_counts=dict(node_work))


def fit_exact_one(examples, life=0):
    counts, node_counts = Counter(), Counter(); examples, folds, labels = prepare_exact(examples, life, counts)
    leaf = dict(leaf_id=0, **exact_leaf_fit(examples, node_counts)); node_counts['full_discovery_node_fits'] += 1
    training = [{key: deepcopy(row[key]) for key in ('root_id', 'source_id', 'life', 'fold', 'canonical_board', 'legal_actions', 'immediate_rewards', 'action_components')} | dict(provenance=deepcopy(row.get('provenance', {}))) for row in examples]
    return dict(schema='acfqp.exact_h3_learning.v177', life=life, query='risk1', native_teacher_query='goal_1_risk_1', horizon=3, mode='ONE_LATE', label_kind='exact_enumerated_vector',
                constants=dict(min_child_roots=8, max_leaves=16, min_child_sources=2, min_action_roots=4, epsilon=EPS, discovery_design_groups=12),
                root_ids=[row['root_id'] for row in examples], source_ids=sorted({row['source_id'] for row in examples}),
                source_folds=folds, source_root_counts=dict(Counter(row['source_id'] for row in examples)),
                nodes=[], groups={'ALL': 0}, leaves=[leaf], node_fits={'0': deepcopy(leaf)}, fit_labels=labels,
                training_outcomes=training, candidate_records=[], fit_counts=dict(counts), utility_search_counts={}, node_fit_counts=dict(node_counts))


def choose_action(payload, root, counts=None):
    legal = [action for action in ACTIONS if action in root['legal_actions']]
    work = Counter(partition_decisions=1, partition_legal_action_reads=len(legal))
    fit, leaf = previous.previous.previous.leaf_for(payload, root['canonical_board'], work)
    action_counts = {action: len(fit['action_root_ids'][action]) if fit else 0 for action in legal}
    pair_counts = {f'{a}|{b}': len(fit['pair_root_ids'][f'{a}|{b}']) if fit else 0 for a, b in combinations(legal, 2)}
    connected = fit['connected_components'] if fit else [[action] for action in ACTIONS]
    component = {action: i for i, group in enumerate(connected) for action in group}
    work.update(partition_action_support_lookups=len(legal), partition_pair_support_lookups=len(pair_counts))
    supported = len(legal) == 1 or fit is not None and all(value >= 4 for value in action_counts.values()) and len({component[action] for action in legal}) == 1
    reason = 'single_legal_action' if len(legal) == 1 else 'selected' if supported else 'missing_partition_leaf' if fit is None else 'insufficient_action_support' if any(value < 4 for value in action_counts.values()) else 'disconnected_required_actions'
    predicted, pairs = {}, {}
    for action in legal:
        if fit and action_counts[action]:
            vector = list(fit['coefficients'][action]); vector[0] += root['immediate_rewards'][action]; predicted[action] = vector
            work.update(partition_coefficient_component_reads=3, partition_immediate_reward_reads=1, partition_reward_additions=1)
    for a, b in combinations(legal, 2):
        if a in predicted and b in predicted and component[a] == component[b]:
            pairs[f'{a}|{b}'] = [x-y for x, y in zip(predicted[a], predicted[b])]
            work['partition_predicted_pair_component_subtractions'] += 3
    selected = legal[0] if len(legal) == 1 else root['fallback_action']
    if supported and len(legal) > 1:
        best = None
        for action in legal:
            value = utility(predicted[action]); work['partition_utility_evaluations'] += 1
            if best is None or value > best+EPS:
                best, selected = value, action
    if counts is not None:
        counts.update(work)
    return dict(canonical_action=selected, actual_action=root['action_map'][selected], fallback=not supported, leaf=leaf, reason=reason, predicted_components=predicted, predicted_pairs=pairs,
                support=dict(action_root_counts=action_counts, pair_root_counts=pair_counts, connected_components=connected, required_actions=legal, complete=supported), work=dict(work))


def canonical_labels(root, native, provenance):
    if native['status'] != 'ACTIVE' or native['horizon'] != 3:
        raise ValueError('Required exact root must be ACTIVE H3')
    if set(native['legal_actions']) != set(root['action_map'].values()):
        raise ValueError('Kernel and observed root actions differ')
    for action, actual in root['action_map'].items():
        if abs(root['immediate_rewards'][action]-native['immediate_rewards'][actual]) > EPS:
            raise ValueError('Kernel first reward differs from the observed board')
    return dict(deepcopy(root), action_components={action: native['action_components'][actual] for action, actual in root['action_map'].items()},
                action_component_fractions={action: native['action_component_fractions'][actual] for action, actual in root['action_map'].items()},
                kernel_root=native['root_cell'], kernel_root_index=native['root_index'], provenance=provenance,
                teacher_action_native=native['teacher_action'])


def freeze_choices(roots, models):
    rows, work = [], Counter()
    for root in roots:
        for mode in ('TREE', 'ONE'):
            decision = choose_action(models[mode], root)
            work.update(decision['work'])
            rows.append(dict(root_id=root['root_id'], mode=mode, canonical_action=decision['canonical_action'], actual_action=decision['actual_action'],
                             fallback=decision['fallback'], decision=decision))
        action = root['fallback_action']
        rows.append(dict(root_id=root['root_id'], mode='FALLBACK', canonical_action=action,
                         actual_action=root['action_map'][action], fallback=False, decision=dict(reason='observable_immediate_reward')))
    return rows, dict(work)


def mean_vectors(vectors):
    return [math.fsum(vector[k] for vector in vectors)/len(vectors) for k in range(3)]


def summarize(roots, labels, choices, models):
    cohorts = {}; modes = ('TREE', 'ONE', 'FALLBACK', 'ORACLE')
    for cohort in ('SOURCE', 'TARGET'):
        label_index = {row['root_id']: row for row in labels[cohort]}
        choice_index = {(row['root_id'], row['mode']): row for row in choices[cohort]}
        if len(label_index) != len(labels[cohort]) or set(label_index) != {root['root_id'] for root in roots[cohort]}:
            raise ValueError('Complete distinct exact root labels required')
        expected = {(root['root_id'], mode) for root in roots[cohort] for mode in modes[:3]}
        if len(choice_index) != len(choices[cohort]) or set(choice_index) != expected:
            raise ValueError('Complete frozen choices required')
        records, groups = [], {}
        for root in roots[cohort]:
            vectors = label_index[root['root_id']]['action_components']; oracle = root['legal_actions'][0]
            for action in root['legal_actions'][1:]:
                if utility(vectors[action]) > utility(vectors[oracle])+EPS:
                    oracle = action
            selected = {}
            for mode in modes:
                action = oracle if mode == 'ORACLE' else choice_index[root['root_id'], mode]['canonical_action']
                vector = vectors[action]
                selected[mode] = dict(action=action, components=vector, utility=utility(vector),
                                      regret=utility(vectors[oracle])-utility(vector),
                                      fallback=False if mode in ('ORACLE', 'FALLBACK') else choice_index[root['root_id'], mode]['fallback'])
            record = dict(root_id=root['root_id'], source_id=root['source_id'], modes=selected,
                          headroom=selected['ORACLE']['utility']-selected['ONE']['utility'],
                          tree_minus_one=selected['TREE']['utility']-selected['ONE']['utility'])
            records.append(record); groups.setdefault(root['source_id'], []).append(record)
        group_rows = [dict(source_id=source, roots=len(rows), metrics={mode: dict(components=mean_vectors([row['modes'][mode]['components'] for row in rows])) for mode in modes}) for source, rows in sorted(groups.items())]
        aggregates = {}
        for weighting in ('ROOT_MEAN', 'DESIGN_GROUP_MEAN'):
            metrics = {}
            for mode in modes:
                vectors = [row['modes'][mode]['components'] for row in records] if weighting == 'ROOT_MEAN' else [row['metrics'][mode]['components'] for row in group_rows]
                vector = mean_vectors(vectors); metrics[mode] = dict(components=vector, utility=utility(vector))
            headroom = metrics['ORACLE']['utility']-metrics['ONE']['utility']; change = metrics['TREE']['utility']-metrics['ONE']['utility']
            aggregates[weighting] = dict(metrics=metrics, headroom=headroom, tree_minus_one=change,
                                        oracle_minus_tree=metrics['ORACLE']['utility']-metrics['TREE']['utility'],
                                        informative=headroom > EPS, headroom_closed_fraction=change/headroom if headroom > EPS else None)
        diagnostics = dict(headroom_roots=sum(row['headroom'] > EPS for row in records),
                           tree_improved_roots=sum(row['tree_minus_one'] > EPS for row in records),
                           tree_worsened_roots=sum(row['tree_minus_one'] < -EPS for row in records),
                           tree_same_value_roots=sum(abs(row['tree_minus_one']) <= EPS for row in records),
                           tree_one_action_changes=sum(row['modes']['TREE']['action'] != row['modes']['ONE']['action'] for row in records),
                           fallback_counts={mode: sum(row['modes'][mode]['fallback'] for row in records) for mode in ('TREE', 'ONE')},
                           oracle_action_disagreements={mode: sum(row['modes'][mode]['action'] != row['modes']['ORACLE']['action'] for row in records) for mode in ('TREE', 'ONE')},
                           positive_regret_roots={mode: sum(row['modes'][mode]['regret'] > EPS for row in records) for mode in ('TREE', 'ONE')})
        cohorts[cohort] = dict(roots=len(records), design_groups=len(groups), primary_weighting='DESIGN_GROUP_MEAN' if cohort == 'SOURCE' else 'ROOT_MEAN',
                               aggregates=aggregates, diagnostics=diagnostics, groups=group_rows, root_records=records)
    return dict(schema='acfqp.exact_h3.v177.summary', complete=True, cohorts=cohorts,
                learned_splits=sum(node['kind'] == 'split' for node in models['TREE']['nodes']),
                candidate_reasons=dict(Counter(row['reason'] for row in models['TREE']['candidate_records'])),
                new_environment_samples=0, new_source_games=0, new_native_weight_updates=0)


def analyze(directory):
    started = perf_counter(); directory = Path(directory); checks, work = [], Counter()
    def read(relative):
        raw = (directory/relative).read_bytes(); work.update(json_read_operations=1, input_bytes_read=len(raw))
        return json.loads(raw)
    def check(name, condition):
        checks.append(dict(name=name, passed=bool(condition)))
    run = read('run.json'); saved_roots = read('roots.json'); saved_labels = read('labels.json')
    saved_models = read('models.json'); saved_choices = read('choices.json'); saved_summary = read('summary.json')
    inputs = read('input_manifest.json')
    source_roster = read('inputs/source/roster.json'); target_roster = read('inputs/target/roster.json')
    query = read('inputs/source/queries.json')['goal_1_risk_1']
    check('one_native_complete_vector_query', query == dict(reward_weight=1., failure_penalty=1., goal_bonus=1.))
    roots = {'SOURCE': [], 'TARGET': [], 'excluded': []}; preparation = Counter()
    for ordinal, case in enumerate(source_roster['source']):
        if case['horizon'] == 3:
            roots['SOURCE'].append(root_from_case(case, ordinal, 'SOURCE', preparation))
        else:
            roots['excluded'].append(dict(cohort='SOURCE', ordinal=ordinal, case=case, reason='horizon_not_three'))
    for ordinal, case in enumerate(target_roster['target']):
        if case['horizon'] == 3:
            roots['TARGET'].append(root_from_case(case, ordinal, 'TARGET', preparation))
    check('fixed47H3_source24H3_target_one_excludedH2', len(roots['SOURCE']) == 47 and len(roots['TARGET']) == 24 and len(roots['excluded']) == 1 and roots['excluded'][0]['case']['horizon'] == 2)
    check('distinct71_root_identities', len({row['root_id'] for cohort in ('SOURCE', 'TARGET') for row in roots[cohort]}) == 71)
    check('observed_roots_D4_immediate_rewards', _equal(saved_roots, roots))
    check('source_group_binding', len({root['source_id'] for root in roots['SOURCE']}) == 12 and sorted(Counter(root['source_id'] for root in roots['SOURCE']).values()) == [3]+[4]*11)
    expected_inputs = [('inputs/source/roster.json', 'preparing'), ('inputs/target/roster.json', 'preparing'), ('inputs/source/queries.json', 'preparing'),
                       ('inputs/source/RAW.kernel.json', 'source_labels'), ('inputs/source/RAW.plans.json', 'source_labels')]
    for root in roots['TARGET']:
        expected_inputs.extend([(f"inputs/target/{root['root_id']}/FULL.model.json", 'target_labels'), (f"inputs/target/{root['root_id']}/FULL.plans.json", 'target_labels')])
    check('all_inputs_first_read_in_frozen_order', [(row['saved_ref'], row['phase']) for row in inputs] == expected_inputs)
    for row in inputs:
        raw = (directory/row['saved_ref']).read_bytes(); original = Path(row['path']).read_bytes()
        work.update(input_byte_comparisons=1, input_comparison_bytes_read=len(raw)+len(original))
        check('retained_input_bytes:'+row['saved_ref'], raw == original and len(raw) == row['bytes'])
    preparation.update(json_read_operations=len(inputs), input_bytes_read=sum(row['bytes'] for row in inputs))
    kernel = read('inputs/source/RAW.kernel.json'); plans = read('inputs/source/RAW.plans.json')
    cells = {row[0]: row[1:] for row in kernel['cells']}
    check('source_RAW_ground_kernel', kernel['variant'] == 'RAW' and len(kernel['roots']) == len(source_roster['source']))
    check('original_source_root_horizons', all(cells[kernel['roots'][i]][0] == case['horizon'] for i, case in enumerate(source_roster['source'])))
    result = evaluate_payload(kernel, plans['goal_1_risk_1'], [root['ordinal'] for root in roots['SOURCE']])
    native = {row['root_index']: row for row in result['labels']}
    labels = {'SOURCE': [canonical_labels(root, native[root['ordinal']], dict(kernel_ref='inputs/source/RAW.kernel.json', plans_ref='inputs/source/RAW.plans.json', query='goal_1_risk_1')) for root in roots['SOURCE']], 'TARGET': []}
    check('source_exact_full_vectors_and_fraction_labels', _equal(saved_labels['SOURCE'], labels['SOURCE']))
    check('standalone_source_labels', _equal(read('source_labels.json'), labels['SOURCE']))
    check('source_DP_costs', _equal(run['costs']['source_evaluation']['counts'], result['counts']) and _equal(result['counts'], run['costs']['source_evaluation']['counts']))
    models = {'ONE': fit_exact_one(labels['SOURCE']), 'TREE': fit_exact_partition(labels['SOURCE'])}
    for mode in ('ONE', 'TREE'):
        check('independent_exact_candidate_and_node_fit:'+mode, _equal(saved_models[mode], models[mode]) and _equal(models[mode], saved_models[mode]))
    learning = run['costs']['learning']
    for key, expected in (('one_fit_counts', models['ONE']['fit_counts']), ('one_node_fit_counts', models['ONE']['node_fit_counts']),
                          ('tree_fit_counts', models['TREE']['fit_counts']), ('tree_search_counts', models['TREE']['utility_search_counts']), ('tree_node_fit_counts', models['TREE']['node_fit_counts'])):
        check('learning_costs:'+key, learning.get(key) == expected)
    choices, choice_work = {}, {}
    for cohort in ('SOURCE', 'TARGET'):
        choices[cohort], choice_work[cohort] = freeze_choices(roots[cohort], models)
        check('label_free_frozen_choices:'+cohort, _equal(saved_choices[cohort], choices[cohort]) and _equal(choices[cohort], saved_choices[cohort]))
    check('decision_costs', run['costs']['decision_counts'] == choice_work)
    target_results = []; restoration = dict(maximum_probability_restoration=result['counts'].get('probability_grid_max_error', 0.),
                                           maximum_reward_restoration=result['counts'].get('reward_grid_max_error', 0.))
    for root in roots['TARGET']:
        name = root['root_id']; kernel_ref = f'inputs/target/{name}/FULL.model.json'; plan_ref = f'inputs/target/{name}/FULL.plans.json'
        kernel = read(kernel_ref); plan = read(plan_ref)
        literals = {(h, tuple(board)): state for h, board, state in kernel['literal_boards']}
        check('target_FULL_literal_identity:'+name, kernel['variant'] == 'FULL' and kernel['rule']['goal_rank'] == 11 and len(kernel['roots']) == 1 and literals.get((3, tuple(root['board']))) == kernel['roots'][0])
        check('target_native_spawn_rule:'+name, kernel['rule']['spawn_distribution'] == [[1, 9, 10], [2, 1, 10]] and kernel['rule']['spawn_location'] == 'uniform')
        evaluation = evaluate_payload(kernel, plan['goal_1_risk_1'], [0])
        labels['TARGET'].append(canonical_labels(root, evaluation['labels'][0], dict(kernel_ref=kernel_ref, plans_ref=plan_ref, query='goal_1_risk_1')))
        target_results.append(dict(root_id=name, counts=evaluation['counts']))
    check('target_exact_full_vectors_and_fraction_labels', _equal(saved_labels['TARGET'], labels['TARGET']))
    check('target_DP_costs', _equal(run['costs']['target_evaluations'], target_results))
    expected_phases = ['source_labels', 'models_frozen', 'target_choices_frozen', 'target_labels', 'complete']
    check('target_choices_frozen_before_target_label_reads', [row['phase'] for row in run['phase_history']] == expected_phases and [row['input_reads'] for row in run['phase_history']] == [3, 5, 5, 5, 53])
    check('complete_execution_without_new_samples', run['status'] == 'complete' and all(run[key] == 0 for key in ('new_environment_samples', 'new_source_games', 'new_native_weight_updates')))
    check('preparation_input_costs', run['costs']['preparation_and_input_counts'] == dict(preparation))
    summary = summarize(roots, labels, choices, models)
    check('independent_exact_headroom_regret_and_weighting', _equal(saved_summary, summary) and _equal(summary, saved_summary))
    valid = all(row['passed'] for row in checks); complete = valid and run['status'] == 'complete' and summary['complete']
    counts = Counter(result['counts'])
    for item in target_results:
        counts.update(item['counts'])
    fit_counts = Counter()
    for model in models.values():
        for key in ('fit_counts', 'utility_search_counts', 'node_fit_counts'):
            fit_counts.update(model[key])
    return dict(schema='acfqp.exact_h3.v177.analysis', valid=valid, complete=complete, primary_complete=complete,
                passed_checks=sum(row['passed'] for row in checks), total_checks=len(checks), checks=checks,
                summary=summary, rational_restoration=restoration,
                costs=dict(new_environment_samples=0, physical_branches_replayed=0, new_source_games=0, new_native_weight_updates=0,
                           inherited_cost_refs=run['inherited_cost_refs'], test_refs=run['test_refs'], original_run_costs=run['costs'],
                           independent_input_counts=dict(work), independent_root_counts=dict(preparation), independent_exact_DP_counts=dict(counts),
                           independent_fit_counts=dict(fit_counts), independent_choice_counts=choice_work, seconds=perf_counter()-started))


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--directory', type=Path, default=PROJECT/'reports/controlled_predictive_exact_h3_v177')
    args = parser.parse_args(); result = analyze(args.directory)
    (args.directory/'analysis.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps(dict(valid=result['valid'], complete=result['complete'], passed=result['passed_checks'], total=result['total_checks'], new_environment_samples=0)))


if __name__ == '__main__':
    main()
