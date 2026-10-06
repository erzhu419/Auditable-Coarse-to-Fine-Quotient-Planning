"""Exact ranking capacity of ANY shared function of the frozen six features.

Each distinct retained feature tuple has a free potential. This is an existence
diagnostic, not a fitted policy; no features, labels or old LPs are recomputed.
"""
from collections import Counter
from copy import deepcopy
from fractions import Fraction
from time import perf_counter

import numpy as np
from scipy.optimize import linprog
from scipy.sparse import csr_matrix
import sympy as sp

from .controlled_predictive_consequence_partition_v172 import ACTIONS, EPSILON
from .controlled_predictive_ranking_capacity_v180 import CapacityExecutionError

SCHEMA = 'acfqp.shared_feature_capacity.v181'
EPS = Fraction(EPSILON)


def lift_problem(problem):
    """Preserve audited alias/optimal sets and lift tuples into shared vertices."""
    tuples = sorted({tuple(row['features']) for root in problem['roots'] for row in root['classes']})
    lookup = {features: index for index, features in enumerate(tuples)}
    lifted, work = deepcopy(problem), Counter()
    for root in lifted['roots']:
        for row in root['classes']:
            row['vertex_id'] = lookup[tuple(row['features'])]
            work.update(lift_class_records=1, lift_feature_values_read=6,
                        lift_terminal_components_copied=3, lift_vertex_assignments=1)
        work['lift_roots_copied'] += 1
    work['lift_distinct_vertices'] = len(tuples)
    lifted.update(schema=SCHEMA+'.problem', vertices=[dict(vertex_id=index, features=list(features))
        for index, features in enumerate(tuples)], inherited_problem_work=deepcopy(problem['work']), work=dict(work))
    return lifted


def evaluate_potentials(problem, potentials):
    """Evaluate free rational potentials using the fixed ACTIONS/EPS rule."""
    potentials = [Fraction(value) for value in potentials]
    records, gaps = [], []
    for root in problem['roots']:
        classes = {row['representative']: row for row in root['classes']}
        scores = {action: Fraction(row['immediate_reward_fraction'])+potentials[row['vertex_id']]
                  for action, row in classes.items()}
        chosen, best = None, None
        for action in ACTIONS:
            if action in scores and (best is None or scores[action] > best+EPS):
                chosen, best = action, scores[action]
        optimal_score = max(scores[action] for action in root['optimal_actions'])
        bad_score = max((scores[action] for action in root['suboptimal_actions']), default=None)
        gap = None if bad_score is None else optimal_score-bad_score
        if gap is not None:
            gaps.append(gap)
        row = classes[chosen]
        records.append(dict(root_id=root['root_id'], chosen=chosen, chosen_optimal=chosen in root['optimal_actions'],
            action_scores={action: str(value) for action, value in scores.items()}, optimal_score=str(optimal_score),
            suboptimal_score=None if bad_score is None else str(bad_score),
            optimal_vs_bad_gap=None if gap is None else str(gap), chosen_components=list(row['components']),
            chosen_utility=row['utility'], regret=root['best_utility']-row['utility']))
    return dict(potentials=[str(value) for value in potentials], root_records=records,
        minimum_gap=None if not gaps else str(min(gaps)), all_optimal=all(row['chosen_optimal'] for row in records),
        all_weak=all(gap >= 0 for gap in gaps))


def _constraints(problem, assigned):
    chosen = {row['root_id']: row['best_action'] for row in assigned}
    rows = []
    for root in problem['roots']:
        if not root['suboptimal_actions']:
            continue
        action = chosen.get(root['root_id'])
        if action is None and len(root['optimal_actions']) == 1:
            action = root['optimal_actions'][0]
        if action is None:
            continue
        classes = {row['representative']: row for row in root['classes']}
        best = classes[action]
        for bad_action in root['suboptimal_actions']:
            bad = classes[bad_action]
            rhs = Fraction(best['immediate_reward_fraction'])-Fraction(bad['immediate_reward_fraction'])
            rows.append(dict(kind='ranking', root_id=root['root_id'], best_action=action, bad_action=bad_action,
                             best_vertex=best['vertex_id'], bad_vertex=bad['vertex_id'], b=str(rhs)))
    rows.append(dict(kind='margin_cap', root_id=None, best_action=None, bad_action=None,
                     best_vertex=None, bad_vertex=None, b='1'))
    return rows


def _incidence(constraints, vertices):
    data, rows, columns = [], [], []
    for index, row in enumerate(constraints):
        entries = [(vertices, 1.)]
        if row['kind'] == 'ranking':
            entries += [(row['bad_vertex'], 1.), (row['best_vertex'], -1.)]
        for column, value in entries:
            rows.append(index); columns.append(column); data.append(value)
    return csr_matrix((data, (rows, columns)), shape=(len(constraints), vertices+1))


def _dual_certificate(constraints, native_weights, vertices, costs):
    support = [index for index, weight in enumerate(native_weights) if weight > 0.]
    if not support:
        raise ValueError('bounded potential LP lacks a native dual support')
    tick = perf_counter(); costs['symbolic_balance_solves'] += 1
    entries = Counter()
    for column, index in enumerate(support):
        row = constraints[index]
        entries[vertices, column] += 1
        if row['kind'] == 'ranking':
            entries[row['bad_vertex'], column] += 1
            entries[row['best_vertex'], column] -= 1
    matrix = sp.SparseMatrix(vertices+1, len(support), dict(entries))
    variables, target = sp.symbols(f'w0:{len(support)}'), sp.Matrix([0]*vertices+[1])
    try:
        solutions = sp.linsolve((matrix, target), variables)
        if solutions == sp.EmptySet:
            raise ValueError('native support cannot balance all feature vertices exactly')
        solution = next(iter(solutions))
        substitutions = {variable: sp.Rational(str(Fraction(float(native_weights[support[index]]))))
                         for index, variable in enumerate(variables)}
        weights = [Fraction(str(value.subs(substitutions))) for value in solution]
        if any(weight < 0 for weight in weights):
            raise ValueError('exact vertex-balanced dual has a negative weight')
        flow, delta = Counter(), Fraction(0)
        for index, weight in zip(support, weights):
            row = constraints[index]; delta += weight
            if row['kind'] == 'ranking':
                flow[row['bad_vertex']] += weight; flow[row['best_vertex']] -= weight
                costs['dual_vertex_flow_accumulations'] += 2
        if delta != 1 or any(flow[vertex] for vertex in range(vertices)):
            raise ValueError('exact feature-vertex dual verification failed')
        upper = sum(weight*Fraction(constraints[index]['b']) for index, weight in zip(support, weights))
        costs.update(dual_support_rows=len(support), dual_balance_vertices_checked=vertices,
                     dual_margin_weight_accumulations=len(support))
        return dict(support=[dict(constraint_index=index, weight=str(weight))
            for index, weight in zip(support, weights) if weight], upper_bound=str(upper))
    finally:
        costs['symbolic_balance_seconds'] += perf_counter()-tick


def solve_capacity(problem):
    """Free-potential margin LPs with exact vertex duals and disjunctive DFS."""
    vertices, costs, nodes, terminal_bounds = len(problem['vertices']), Counter(), [], []
    record = dict(schema=SCHEMA+'.capacity', status='running', nodes=nodes, witness=None,
                  weak_witness=None, upper_bound=None, costs={})

    def visit(assigned, parent_id):
        node_id, constraints = len(nodes), _constraints(problem, assigned)
        node = dict(node_id=node_id, parent_id=parent_id, assigned=list(assigned), constraints=constraints,
            native_lp=None, primal=None, dual=None, disposition=None, branch_root_id=None,
            branch_actions=[], children=[], unexplored_actions=[])
        nodes.append(node)
        matrix = _incidence(constraints, vertices)
        rhs = np.asarray([float(Fraction(row['b'])) for row in constraints])
        costs.update(lp_solves=1, lp_constraint_rows=len(constraints), lp_variables=vertices+1,
                     lp_incidence_entries=matrix.nnz)
        tick = perf_counter()
        try:
            result = linprog([0.]*vertices+[-1.], A_ub=matrix, b_ub=rhs,
                             bounds=[(None, None)]*(vertices+1), method='highs')
        finally:
            costs['lp_seconds'] += perf_counter()-tick
        node['native_lp'] = dict(success=bool(result.success), status=int(result.status), message=result.message,
                                iterations=int(getattr(result, 'nit', 0)))
        if not result.success:
            raise ValueError('native free-potential LP failed; explicit cap and free delta make it feasible')
        node['native_lp'].update(potentials=list(map(float, result.x[:vertices])), delta=float(result.x[vertices]))
        node['dual'] = _dual_certificate(constraints, -np.asarray(result.ineqlin.marginals), vertices, costs)
        upper = Fraction(node['dual']['upper_bound'])
        potentials = [str(Fraction(float(value))) for value in result.x[:vertices]]
        evaluation = evaluate_potentials(problem, potentials)
        costs.update(potential_evaluations=1, potential_root_records=len(problem['roots']),
                     potential_rational_conversions=vertices)
        node['primal'] = dict(potentials=potentials, evaluation=evaluation)
        if evaluation['all_weak'] and record['weak_witness'] is None:
            record['weak_witness'] = dict(node_id=node_id, potentials=potentials, evaluation=evaluation)
        if upper <= 0:
            node['disposition'] = 'pruned_negative' if upper < 0 else 'pruned_zero'
            terminal_bounds.append(upper); return False
        minimum = Fraction(1) if evaluation['minimum_gap'] is None else Fraction(evaluation['minimum_gap'])
        if minimum > EPS:
            if not evaluation['all_optimal']:
                raise ValueError('strict free-potential scores fail the declared representative choice')
            node['disposition'] = 'strict_witness'
            record['witness'] = dict(node_id=node_id, potentials=potentials,
                                    margin=str(min(Fraction(1), minimum)), evaluation=evaluation)
            return True
        selected_roots = {row['root_id'] for row in assigned}
        roots = {row['root_id']: row for row in problem['roots']}
        violated = [roots[row['root_id']] for row in evaluation['root_records']
                    if row['optimal_vs_bad_gap'] is not None and Fraction(row['optimal_vs_bad_gap']) <= EPS]
        branch = next((root for root in violated if len(root['optimal_actions']) > 1
                       and root['root_id'] not in selected_roots), None)
        if branch is None:
            raise ValueError('positive exact bound lacks a strict primal or an unassigned optimal disjunction')
        node.update(disposition='branch', branch_root_id=branch['root_id'], branch_actions=list(branch['optimal_actions']))
        for ordinal, action in enumerate(branch['optimal_actions']):
            node['children'].append(len(nodes))
            if visit(assigned+[dict(root_id=branch['root_id'], best_action=action)], node_id):
                node['unexplored_actions'] = branch['optimal_actions'][ordinal+1:]
                return True
        return False

    try:
        if visit([], None):
            record.update(status='strict_feasible', upper_bound=nodes[0]['dual']['upper_bound'])
        else:
            upper = max(terminal_bounds)
            record.update(status='weak_infeasible' if upper < 0 else 'no_positive_margin', upper_bound=str(upper))
        record['costs'] = dict(costs); return record
    except Exception as error:
        record.update(status='execution_error', failure=dict(type=type(error).__name__, message=str(error)), costs=dict(costs))
        raise CapacityExecutionError(str(error), record) from error
