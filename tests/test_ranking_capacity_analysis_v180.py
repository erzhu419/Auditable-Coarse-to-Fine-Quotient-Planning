"""Pure certificate failures; no solver, old data, fitting or environment calls."""
from copy import deepcopy
from fractions import Fraction

from scripts import analyze_controlled_predictive_ranking_capacity_v180 as audit


def root(name, features, rewards, values):
    row = dict(root_id=name, cohort='SOURCE', life=0, source_id='DESIGN_SOURCE:00',
               legal_actions=list(features), action_features={action: [0, value, 0, 0, 0, 0] for action, value in features.items()},
               immediate_rewards=rewards)
    labels = dict(root_id=name, action_components={action: [value, 0., 0.] for action, value in values.items()})
    return row, labels


def negative_tree():
    data = [root('multi', {'DOWN': 0, 'LEFT': 2, 'RIGHT': 1}, {'DOWN': 0., 'LEFT': 0., 'RIGHT': 2.}, {'DOWN': 2., 'LEFT': 2., 'RIGHT': 1.}),
            root('unique1', {'DOWN': 0, 'LEFT': 1}, {'DOWN': 0., 'LEFT': 0.}, {'DOWN': 1., 'LEFT': 0.}),
            root('unique2', {'DOWN': 1, 'LEFT': 0}, {'DOWN': 1., 'LEFT': 0.}, {'DOWN': 1., 'LEFT': 0.})]
    problem = audit.build_problem([row for row, _ in data], [label for _, label in data])
    nodes = []
    for index, action, beta, support, bound in [(0, None, -.5, [0, 1], '1/2'),
                                              (1, 'DOWN', -1.5, [0, 2], '-1/2'),
                                              (2, 'LEFT', -1., [0, 1], '-1')]:
        assigned = [] if action is None else [dict(root_id='multi', best_action=action)]
        vector = [0., beta, 0., 0., 0., 0.]; evaluation = audit.evaluate_beta(problem, vector)
        nodes.append(dict(node_id=index, parent_id=None if index == 0 else 0, assigned=assigned,
            constraints=audit.constraints_for(problem, assigned),
            native_lp=dict(success=True, status=0, message='fixture', iterations=0, beta=vector, delta=float(Fraction(bound))),
            primal=dict(beta=evaluation['beta'], evaluation=evaluation),
            dual=dict(support=[dict(constraint_index=i, weight='1/2') for i in support], upper_bound=bound),
            disposition='branch' if index == 0 else 'pruned_negative',
            branch_root_id='multi' if index == 0 else None, branch_actions=['DOWN', 'LEFT'] if index == 0 else [],
            children=[1, 2] if index == 0 else [], unexplored_actions=[]))
    rows = sum(len(node['constraints']) for node in nodes)
    costs = dict(lp_solves=3, lp_constraint_rows=rows, lp_matrix_cells=7*rows, lp_seconds=0.,
                 symbolic_balance_solves=3, symbolic_balance_seconds=0., dual_support_rows=6,
                 dual_balance_scalar_products=42, beta_evaluations=3, beta_root_records=9, beta_rational_conversions=18)
    return problem, dict(schema='acfqp.ranking_capacity.v180.capacity', status='weak_infeasible', witness=None,
                         weak_witness=None, upper_bound='-1/2', nodes=nodes, costs=costs)


def test_optimal_tie_is_a_disjunction_and_alias_uses_known_reward():
    row, label = root('r', {'DOWN': 0, 'LEFT': 2, 'RIGHT': 1, 'UP': 0},
                      {'DOWN': 0., 'LEFT': 0., 'RIGHT': 2., 'UP': 1.},
                      {'DOWN': 1., 'LEFT': 3., 'RIGHT': 1., 'UP': 3.})
    problem = audit.build_problem([row], [label]); record = problem['roots'][0]
    assert record['optimal_actions'] == ['LEFT', 'UP']
    assert record['classes'][0]['representative'] == 'UP'
    assert len(audit.constraints_for(problem, [])) == 1  # no arbitrary tied witness
    evaluation = audit.evaluate_beta(problem, [0, 3, 0, 0, 0, 0])
    assert evaluation['all_optimal'] and evaluation['root_records'][0]['chosen'] == 'LEFT'
    assert Fraction(evaluation['minimum_gap']) > Fraction(audit.EPS)


def test_exact_dual_rejects_tiny_stationarity_error_and_wrong_bound():
    constraints = [dict(a=['0']*6+['1'], b='1')]
    certificate = dict(support=[dict(constraint_index=0, weight='1')], upper_bound='1')
    assert audit.verify_dual(constraints, certificate)
    perturbed = deepcopy(constraints); perturbed[0]['a'][0] = '1/1000000000000000000000000'
    assert not audit.verify_dual(perturbed, certificate)
    changed = deepcopy(certificate); changed['upper_bound'] = '0'
    assert not audit.verify_dual(constraints, changed)
    changed = deepcopy(certificate); changed['support'][0]['weight'] = '-1'
    assert not audit.verify_dual(constraints, changed)


def test_negative_certificate_requires_every_optimal_alternative():
    problem, capacity = negative_tree(); checks, _ = audit.verify_capacity(problem, capacity)
    assert all(row['passed'] for row in checks)
    missing = deepcopy(capacity); missing['nodes'][0]['children'] = [1]
    missing['nodes'][0]['unexplored_actions'] = ['LEFT']
    checks, _ = audit.verify_capacity(problem, missing)
    assert not all(row['passed'] for row in checks)
    assert any(not row['passed'] and 'alternatives' in row['name'] for row in checks)
    falsely_weak = deepcopy(capacity); falsely_weak['weak_witness'] = falsely_weak['nodes'][1]['primal']
    checks, _ = audit.verify_capacity(problem, falsely_weak)
    assert not all(row['passed'] for row in checks)


def test_absorbing_goal_requires_complete_first_reward_success_vector():
    roots = {cohort: [dict(root_id=cohort, legal_actions=['DOWN'], action_features={'DOWN': [1, 4, 0, 0, 0, 0]},
                         immediate_rewards={'DOWN': .5})] for cohort in ('SOURCE', 'TARGET')}
    labels = {cohort: [dict(root_id=cohort, action_components={'DOWN': [.5, 0., 1.]})] for cohort in roots}
    assert audit.terminal_identities(roots, labels)['consistent']
    labels['TARGET'][0]['action_components']['DOWN'] = [.5, 0., 0.]
    report = audit.terminal_identities(roots, labels)
    assert not report['consistent'] and report['actions'] == 2
    assert report['work']['goal_identity_comparisons'] == 6
