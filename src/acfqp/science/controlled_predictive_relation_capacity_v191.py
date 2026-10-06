"""Retained-root capacity of the fixed V190 98-coordinate action score.

The finite binary feature array is the representation under test. Numerical
LP output is a candidate; positive policies and negative dual bounds are
verified on that array using exact rational arithmetic.
"""
from collections import Counter
from fractions import Fraction
from math import isfinite
from time import perf_counter

import numpy as np
from scipy.optimize import linprog
import sympy as sp

from .controlled_predictive_consequence_partition_v172 import ACTIONS, EPSILON

SCHEMA = 'acfqp.relation_capacity.v191'
EPS = Fraction(EPSILON)
COLUMNS = 98


class CapacityExecutionError(RuntimeError):
    def __init__(self, message, record):
        super().__init__(message)
        self.record = record


def _fraction(value):
    return Fraction(value)


def _utility(vector):
    return vector[0]-vector[1]+vector[2]


def build_problem(roots_list, labels_list):
    """Retain every legal action, including identical-feature actions."""
    labels = {row['root_id']: row for row in labels_list}
    if len(labels) != len(labels_list) or len({r['root_id'] for r in roots_list}) != len(roots_list):
        raise ValueError('distinct retained roots and labels required')
    if not roots_list or set(labels) != {row['root_id'] for row in roots_list}:
        raise ValueError('one retained label for every capacity root required')
    rows, work = [], Counter()
    for root in sorted(roots_list, key=lambda row: row['root_id']):
        legal = [action for action in ACTIONS if action in root['legal_actions']]
        components = labels[root['root_id']]['action_components']
        if not legal or len(legal) != len(root['legal_actions']) or set(components) != set(legal):
            raise ValueError('complete labels for all distinct legal actions required')
        actions = []
        for action in legal:
            features = list(map(float, root['relation_features'][action]))
            if len(features) != COLUMNS:
                raise ValueError('fixed 98-coordinate V190 features required')
            vector = list(map(float, components[action]))
            if len(vector) != 3:
                raise ValueError('complete retained R/F/S vector required')
            reward = float(root['immediate_rewards'][action])
            actions.append(dict(action=action, features=features,
                feature_fractions=[str(Fraction(value)) for value in features],
                immediate_reward=reward, immediate_reward_fraction=str(Fraction(reward)),
                components=vector, utility=_utility(vector)))
            work.update(problem_action_records=1, problem_feature_values_read=COLUMNS,
                problem_feature_fraction_conversions=COLUMNS, problem_terminal_components_read=3,
                problem_immediate_rewards_read=1, problem_reward_fraction_conversions=1,
                problem_action_utility_evaluations=1)
        best = max(row['utility'] for row in actions)
        optimal = [row['action'] for row in actions if row['utility'] >= best-EPSILON]
        rows.append(dict(root_id=root['root_id'], cohort=root['cohort'], life=root['life'],
            source_id=root['source_id'], actions=actions, optimal_actions=optimal,
            suboptimal_actions=[action for action in legal if action not in optimal], best_utility=best))
        work['problem_root_records'] += 1
    return dict(schema=SCHEMA+'.problem', columns=COLUMNS, roots=rows,
                epsilon=EPSILON, work=dict(work))


def _select(scores, epsilon):
    chosen, best = None, None
    for action in ACTIONS:
        if action in scores and (best is None or scores[action] > best+epsilon):
            chosen, best = action, scores[action]
    return chosen


def evaluate_beta(problem, beta):
    """Compare exact gaps and the actual finite-float ACTIONS/EPS choices."""
    columns = problem['columns']
    if len(beta) != columns:
        raise ValueError('one coefficient per frozen feature coordinate required')
    weights = [_fraction(value) for value in beta]
    native_weights = list(map(float, weights))
    records, gaps, work = [], [], Counter(beta_rational_conversions=columns, beta_float_conversions=columns)
    for root in problem['roots']:
        actions = {row['action']: row for row in root['actions']}
        scores = {action: _fraction(row['immediate_reward_fraction'])+
            sum(_fraction(value)*weight for value, weight in zip(row['feature_fractions'], weights, strict=True))
            for action, row in actions.items()}
        actual_scores = {action: row['immediate_reward']+
            sum(value*weight for value, weight in zip(row['features'], native_weights, strict=True))
            for action, row in actions.items()}
        if not all(isfinite(value) for value in actual_scores.values()):
            raise ValueError('candidate coefficients produce nonfinite actual scores')
        chosen = _select(scores, EPS)
        actual_chosen = _select(actual_scores, EPSILON)
        optimum_score = max(scores[action] for action in root['optimal_actions'])
        bad_score = max((scores[action] for action in root['suboptimal_actions']), default=None)
        gap = None if bad_score is None else optimum_score-bad_score
        if gap is not None:
            gaps.append(gap)
        actual_row = actions[actual_chosen]
        records.append(dict(root_id=root['root_id'], chosen=chosen,
            chosen_optimal=chosen in root['optimal_actions'],
            actual_chosen=actual_chosen, actual_chosen_optimal=actual_chosen in root['optimal_actions'],
            action_scores={action: str(value) for action, value in scores.items()},
            actual_action_scores=actual_scores, optimal_score=str(optimum_score),
            suboptimal_score=None if bad_score is None else str(bad_score),
            optimal_vs_bad_gap=None if gap is None else str(gap),
            chosen_components=list(actual_row['components']), chosen_utility=actual_row['utility'],
            regret=root['best_utility']-actual_row['utility']))
        work.update(beta_root_records=1, beta_action_records=len(actions),
            beta_feature_fraction_reads=columns*len(actions),
            beta_rational_scalar_products=columns*len(actions),
            beta_float_feature_reads=columns*len(actions), beta_float_scalar_products=columns*len(actions),
            beta_exact_score_evaluations=len(actions), beta_float_score_evaluations=len(actions),
            beta_exact_choice_comparisons=len(actions), beta_float_choice_comparisons=len(actions),
            beta_gap_subtractions=int(gap is not None))
    return dict(beta=[str(value) for value in weights], root_records=records,
        minimum_gap=None if not gaps else str(min(gaps)),
        all_optimal=all(row['actual_chosen_optimal'] for row in records),
        rational_all_optimal=all(row['chosen_optimal'] for row in records),
        all_weak=all(gap >= 0 for gap in gaps), work=dict(work))


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
        actions = {row['action']: row for row in root['actions']}
        best = actions[action]
        for bad_action in root['suboptimal_actions']:
            bad = actions[bad_action]
            # Subtract the stored binary rationals before rounding the LP array.
            values = [_fraction(b)-_fraction(g) for b, g in
                      zip(bad['feature_fractions'], best['feature_fractions'], strict=True)]
            rhs = _fraction(best['immediate_reward_fraction'])-_fraction(bad['immediate_reward_fraction'])
            rows.append(dict(kind='ranking', root_id=root['root_id'], best_action=action,
                bad_action=bad_action, a=[str(value) for value in values]+['1'], b=str(rhs)))
    rows.append(dict(kind='margin_cap', root_id=None, best_action=None, bad_action=None,
                     a=['0']*problem['columns']+['1'], b='1'))
    return rows


def _verify_dual(constraints, support, weights, columns, costs, method):
    if any(weight < 0 for weight in weights):
        raise ValueError('exact balanced dual has a negative weight')
    for column in range(columns+1):
        balance = sum(weight*_fraction(constraints[index]['a'][column])
                      for index, weight in zip(support, weights, strict=True))
        if balance != int(column == columns):
            raise ValueError('exact dual balance verification failed')
    upper = sum(weight*_fraction(constraints[index]['b'])
                for index, weight in zip(support, weights, strict=True))
    costs.update(dual_support_rows=len(support), dual_balance_scalar_products=(columns+1)*len(support))
    return dict(method=method, support=[dict(constraint_index=index, weight=str(weight))
        for index, weight in zip(support, weights, strict=True) if weight], upper_bound=str(upper))


def _dual_certificate(constraints, native_weights, columns, costs):
    support = [index for index, weight in enumerate(native_weights) if weight > 0.]
    if not support:
        raise ValueError('bounded margin LP lacks a native dual support')
    tick = perf_counter()
    costs['symbolic_balance_solves'] += 1
    costs['symbolic_balance_matrix_cells'] += (columns+1)*len(support)
    try:
        matrix = sp.Matrix([[sp.Rational(constraints[index]['a'][column]) for index in support]
                            for column in range(columns+1)])
        target = sp.Matrix([0]*columns+[1])
        variables = sp.symbols(f'w0:{len(support)}')
        solutions = sp.linsolve((matrix, target), variables)
        if solutions == sp.EmptySet:
            raise ValueError('native dual support cannot balance the binary-rational matrix exactly')
        solution = next(iter(solutions))
        substitutions = {variable: sp.Rational(str(Fraction(float(native_weights[support[index]]))))
                         for index, variable in enumerate(variables)}
        weights = [Fraction(str(value.subs(substitutions))) for value in solution]
        return _verify_dual(constraints, support, weights, columns, costs, 'exact_native_support')
    finally:
        costs['symbolic_balance_seconds'] += perf_counter()-tick


def solve_capacity(problem):
    """Search all tied-optimum disjunctions; retain every paid LP and failure."""
    columns = problem['columns']
    costs, nodes, terminal_bounds = Counter(), [], []
    record = dict(schema=SCHEMA+'.capacity', status='running', nodes=nodes, witness=None,
                  weak_witness=None, upper_bound=None, costs={})

    def visit(assigned, parent_id):
        node_id = len(nodes)
        constraints = _constraints(problem, assigned)
        node = dict(node_id=node_id, parent_id=parent_id, assigned=list(assigned), constraints=constraints,
            native_lp=None, primal=None, dual=None, disposition=None, branch_root_id=None,
            branch_actions=[], children=[], unexplored_actions=[])
        nodes.append(node)
        matrix = np.asarray([[float(_fraction(value)) for value in row['a']] for row in constraints])
        rhs = np.asarray([float(_fraction(row['b'])) for row in constraints])
        costs.update(lp_solves=1, lp_constraint_rows=len(constraints), lp_matrix_cells=matrix.size,
            constraint_exact_feature_subtractions=columns*(len(constraints)-1),
            constraint_exact_reward_subtractions=len(constraints)-1)
        tick = perf_counter()
        try:
            result = linprog([0.]*columns+[-1.], A_ub=matrix, b_ub=rhs,
                             bounds=[(None, None)]*(columns+1), method='highs')
        finally:
            costs['lp_seconds'] += perf_counter()-tick
        node['native_lp'] = dict(success=bool(result.success), status=int(result.status),
                                message=result.message, iterations=int(getattr(result, 'nit', 0)))
        if not result.success:
            raise ValueError('native margin LP failed; the explicit-cap free-variable LP is feasible')
        node['native_lp'].update(beta=list(map(float, result.x[:columns])), delta=float(result.x[columns]))
        beta = [str(Fraction(float(value))) for value in result.x[:columns]]
        costs['beta_evaluations'] += 1
        evaluation = evaluate_beta(problem, beta)
        costs.update(evaluation['work'])
        node['primal'] = dict(beta=beta, evaluation=evaluation)
        if evaluation['all_weak'] and record['weak_witness'] is None:
            record['weak_witness'] = dict(node_id=node_id, beta=beta, evaluation=evaluation)
        minimum = Fraction(1) if evaluation['minimum_gap'] is None else _fraction(evaluation['minimum_gap'])
        if minimum > EPS and evaluation['all_optimal'] and evaluation['rational_all_optimal']:
            # A verified existence witness needs only the explicit cap as upper bound.
            costs['trivial_margin_cap_certificates'] += 1
            node['dual'] = _verify_dual(constraints, [len(constraints)-1], [Fraction(1)],
                columns, costs, 'trivial_margin_cap')
            node['disposition'] = 'strict_witness'
            record['witness'] = dict(node_id=node_id, beta=beta,
                margin=str(min(Fraction(1), minimum)), evaluation=evaluation)
            return True
        certificate = _dual_certificate(constraints, -np.asarray(result.ineqlin.marginals), columns, costs)
        node['dual'] = certificate
        upper = _fraction(certificate['upper_bound'])
        if upper <= 0:
            node['disposition'] = 'pruned_negative' if upper < 0 else 'pruned_zero'
            terminal_bounds.append(upper)
            return False
        chosen_roots = {row['root_id'] for row in assigned}
        roots = {root['root_id']: root for root in problem['roots']}
        violated = [roots[row['root_id']] for row in evaluation['root_records']
                    if row['optimal_vs_bad_gap'] is not None and _fraction(row['optimal_vs_bad_gap']) <= EPS]
        branch = next((root for root in violated if len(root['optimal_actions']) > 1 and
                       root['root_id'] not in chosen_roots), None)
        if branch is None:
            raise ValueError('positive certified bound lacks a strict actual-float witness or an unassigned disjunction')
        node.update(disposition='branch', branch_root_id=branch['root_id'], branch_actions=list(branch['optimal_actions']))
        for ordinal, action in enumerate(branch['optimal_actions']):
            child_id = len(nodes)
            node['children'].append(child_id)
            if visit(assigned+[dict(root_id=branch['root_id'], best_action=action)], node_id):
                node['unexplored_actions'] = branch['optimal_actions'][ordinal+1:]
                return True
        return False

    try:
        strict = visit([], None)
        if strict:
            record.update(status='strict_feasible', upper_bound=nodes[0]['dual']['upper_bound'])
        else:
            upper = max(terminal_bounds)
            record.update(status='weak_infeasible' if upper < 0 else 'no_positive_margin', upper_bound=str(upper))
        record['costs'] = dict(costs)
        return record
    except Exception as error:
        record.update(status='execution_error', failure=dict(type=type(error).__name__, message=str(error)), costs=dict(costs))
        raise CapacityExecutionError(str(error), record) from error
