"""Certificate-only capacity of the frozen six-feature affine action ranking.

No policy is learned or deployed. A strict witness proves existence on retained
roots; a zero margin bound does not prove impossibility of a tied policy.
"""
from collections import Counter
from fractions import Fraction
from time import perf_counter

import numpy as np
from scipy.optimize import linprog
import sympy as sp

from .controlled_predictive_consequence_partition_v172 import ACTIONS, EPSILON

SCHEMA = 'acfqp.ranking_capacity.v180'
EPS = Fraction(EPSILON)


class CapacityExecutionError(RuntimeError):
    def __init__(self, message, record):
        super().__init__(message)
        self.record = record


def _fraction(value):
    return Fraction(value)


def _utility(vector):
    return vector[0]-vector[1]+vector[2]


def build_problem(roots_list, labels_list):
    """Freeze action aliases and ALL equally optimal representative choices."""
    labels = {row['root_id']: row for row in labels_list}
    rows, work = [], Counter()
    for root in sorted(roots_list, key=lambda row: row['root_id']):
        components = labels[root['root_id']]['action_components']
        groups = {}
        for action in ACTIONS:
            if action in root['legal_actions']:
                features = tuple(root['action_features'][action])
                groups.setdefault(features, []).append(action)
                work.update(problem_feature_values_read=6, problem_action_alias_classifications=1)
        classes = []
        for features, actions in groups.items():
            representative = actions[0]
            for action in actions[1:]:
                if root['immediate_rewards'][action] > root['immediate_rewards'][representative]+EPSILON:
                    representative = action
                work.update(problem_alias_reward_comparisons=1, problem_immediate_rewards_read=2)
            vector = list(components[representative])
            reward = root['immediate_rewards'][representative]
            classes.append(dict(class_id=len(classes), features=list(features), actions=actions,
                representative=representative, immediate_reward=reward,
                immediate_reward_fraction=str(_fraction(reward)),
                components=vector, utility=_utility(vector)))
            work.update(problem_terminal_components_read=3, problem_immediate_rewards_read=1)
        best = max(row['utility'] for row in classes)
        optimal = [action for action in ACTIONS if any(row['representative'] == action and
                   row['utility'] >= best-EPSILON for row in classes)]
        suboptimal = [action for action in ACTIONS if any(row['representative'] == action and
                      action not in optimal for row in classes)]
        rows.append(dict(root_id=root['root_id'], cohort=root['cohort'], life=root['life'],
            source_id=root['source_id'], classes=classes, optimal_actions=optimal,
            suboptimal_actions=suboptimal, best_utility=best))
        work.update(problem_root_records=1, problem_representative_utility_evaluations=len(classes))
    if not rows or len({row['root_id'] for row in rows}) != len(rows):
        raise ValueError('distinct retained roots required for a capacity scope')
    return dict(schema=SCHEMA+'.problem', roots=rows, epsilon=EPSILON, work=dict(work))


def evaluate_beta(problem, beta):
    """Evaluate rational scores and the actual ACTIONS/EPS representative choice."""
    beta = [_fraction(value) for value in beta]
    records, gaps = [], []
    for root in problem['roots']:
        classes = {row['representative']: row for row in root['classes']}
        scores = {action: _fraction(row['immediate_reward_fraction'])+
                  sum(_fraction(value)*weight for value, weight in zip(row['features'], beta))
                  for action, row in classes.items()}
        chosen, best = None, None
        for action in ACTIONS:
            if action in scores and (best is None or scores[action] > best+EPS):
                chosen, best = action, scores[action]
        optimum_score = max(scores[action] for action in root['optimal_actions'])
        bad_score = max((scores[action] for action in root['suboptimal_actions']), default=None)
        gap = None if bad_score is None else optimum_score-bad_score
        if gap is not None:
            gaps.append(gap)
        row = classes[chosen]
        records.append(dict(root_id=root['root_id'], chosen=chosen, chosen_optimal=chosen in root['optimal_actions'],
            action_scores={action: str(value) for action, value in scores.items()},
            optimal_score=str(optimum_score), suboptimal_score=None if bad_score is None else str(bad_score),
            optimal_vs_bad_gap=None if gap is None else str(gap), chosen_components=list(row['components']),
            chosen_utility=row['utility'], regret=root['best_utility']-row['utility']))
    return dict(beta=[str(value) for value in beta], root_records=records,
        minimum_gap=None if not gaps else str(min(gaps)),
        all_optimal=all(row['chosen_optimal'] for row in records), all_weak=all(gap >= 0 for gap in gaps))


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
            a = [_fraction(b)-_fraction(g) for b, g in zip(bad['features'], best['features'])]+[Fraction(1)]
            b = _fraction(best['immediate_reward_fraction'])-_fraction(bad['immediate_reward_fraction'])
            rows.append(dict(kind='ranking', root_id=root['root_id'], best_action=action, bad_action=bad_action,
                             a=[str(value) for value in a], b=str(b)))
    rows.append(dict(kind='margin_cap', root_id=None, best_action=None, bad_action=None,
                     a=['0']*6+['1'], b='1'))
    return rows


def _dual_certificate(constraints, native_weights, costs):
    support = [index for index, weight in enumerate(native_weights) if weight > 0.]
    if not support:
        raise ValueError('bounded margin LP lacks a native dual support')
    tick = perf_counter()
    costs['symbolic_balance_solves'] += 1
    matrix = sp.Matrix([[sp.Rational(constraints[index]['a'][column]) for index in support] for column in range(7)])
    target, variables = sp.Matrix([0]*6+[1]), sp.symbols(f'w0:{len(support)}')
    try:
        solutions = sp.linsolve((matrix, target), variables)
        if solutions == sp.EmptySet:
            raise ValueError('native dual support cannot balance exactly')
        solution = next(iter(solutions))
        substitutions = {variable: sp.Rational(str(_fraction(float(native_weights[support[index]]))))
                         for index, variable in enumerate(variables)}
        weights = [Fraction(str(value.subs(substitutions))) for value in solution]
        if any(weight < 0 for weight in weights):
            raise ValueError('exact balanced dual has a negative weight')
        for column in range(7):
            if sum(weight*_fraction(constraints[index]['a'][column]) for index, weight in zip(support, weights)) != int(column == 6):
                raise ValueError('exact dual balance verification failed')
        upper = sum(weight*_fraction(constraints[index]['b']) for index, weight in zip(support, weights))
        costs.update(dual_support_rows=len(support), dual_balance_scalar_products=7*len(support))
        return dict(support=[dict(constraint_index=index, weight=str(weight))
            for index, weight in zip(support, weights) if weight], upper_bound=str(upper))
    finally:
        costs['symbolic_balance_seconds'] += perf_counter()-tick


def solve_capacity(problem):
    """DFS disjunctive best-action witnesses with exact dual subtree pruning."""
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
        costs.update(lp_solves=1, lp_constraint_rows=len(constraints), lp_matrix_cells=matrix.size)
        tick = perf_counter()
        try:
            result = linprog([0.]*6+[-1.], A_ub=matrix, b_ub=rhs,
                             bounds=[(None, None)]*7, method='highs')
        finally:
            costs['lp_seconds'] += perf_counter()-tick
        node['native_lp'] = dict(success=bool(result.success), status=int(result.status), message=result.message,
                                iterations=int(getattr(result, 'nit', 0)))
        if not result.success:
            raise ValueError('native margin LP failed; the explicit-cap free-variable LP is feasible')
        node['native_lp'].update(beta=list(map(float, result.x[:6])), delta=float(result.x[6]))
        certificate = _dual_certificate(constraints, -np.asarray(result.ineqlin.marginals), costs)
        node['dual'] = certificate
        upper = _fraction(certificate['upper_bound'])
        beta = [str(_fraction(float(value))) for value in result.x[:6]]
        evaluation = evaluate_beta(problem, beta)
        costs.update(beta_evaluations=1, beta_root_records=len(problem['roots']), beta_rational_conversions=6)
        node['primal'] = dict(beta=beta, evaluation=evaluation)
        if evaluation['all_weak'] and record['weak_witness'] is None:
            record['weak_witness'] = dict(node_id=node_id, beta=beta, evaluation=evaluation)
        if upper <= 0:
            node['disposition'] = 'pruned_negative' if upper < 0 else 'pruned_zero'
            terminal_bounds.append(upper)
            return False
        minimum = Fraction(1) if evaluation['minimum_gap'] is None else _fraction(evaluation['minimum_gap'])
        if minimum > EPS:
            if not evaluation['all_optimal']:
                raise ValueError('strict scores do not reproduce the declared best representative')
            node['disposition'] = 'strict_witness'
            record['witness'] = dict(node_id=node_id, beta=beta, margin=str(min(Fraction(1), minimum)), evaluation=evaluation)
            return True
        chosen_roots = {row['root_id'] for row in assigned}
        roots = {root['root_id']: root for root in problem['roots']}
        violated = [roots[row['root_id']] for row in evaluation['root_records']
                    if row['optimal_vs_bad_gap'] is not None and _fraction(row['optimal_vs_bad_gap']) <= EPS]
        branch = next((root for root in violated if len(root['optimal_actions']) > 1 and root['root_id'] not in chosen_roots), None)
        if branch is None:
            raise ValueError('positive dual bound lacks a verified strict primal or an unassigned disjunction')
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
