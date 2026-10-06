"""Pure incidence certificates; no LP, fits, cached-data reads or environment."""
from copy import deepcopy
from fractions import Fraction

from scripts import analyze_controlled_predictive_shared_feature_capacity_v181 as audit


def root(name, features, rewards, values, cohort='SOURCE'):
    row = dict(root_id=name, cohort=cohort, life=0, source_id='DESIGN_SOURCE:00', legal_actions=list(features),
               action_features={action: [0, value, 0, 0, 0, 0] for action, value in features.items()}, immediate_rewards=rewards)
    label = dict(root_id=name, action_components={action: [value, 0., 0.] for action, value in values.items()})
    return row, label


def lift(rows):
    return audit.lift_problem(audit.previous.build_problem([row for row, _ in rows], [label for _, label in rows]))


def node(problem, index, parent, assigned, values, support, upper, disposition):
    evaluation = audit.evaluate_potentials(problem, values)
    return dict(node_id=index, parent_id=parent, assigned=assigned, constraints=audit.constraints_for(problem, assigned),
                native_lp=dict(success=True, status=0, iterations=0, message='fixture', potentials=values, delta=float(Fraction(upper))),
                primal=dict(potentials=evaluation['potentials'], evaluation=evaluation),
                dual=dict(support=[dict(constraint_index=i, weight=weight) for i, weight in support], upper_bound=upper),
                disposition=disposition, branch_root_id=None, branch_actions=[], children=[], unexplored_actions=[])


def costs(problem, nodes):
    rows = [row for item in nodes for row in item['constraints']]; support = [item['constraints'][atom['constraint_index']] for item in nodes for atom in item['dual']['support']]
    return dict(lp_solves=len(nodes), lp_constraint_rows=len(rows), lp_variables=len(nodes)*(len(problem['vertices'])+1),
                lp_incidence_entries=sum(3 if row['kind'] == 'ranking' else 1 for row in rows), lp_seconds=0.,
                symbolic_balance_solves=len(nodes), symbolic_balance_seconds=0., dual_support_rows=len(support),
                dual_vertex_flow_accumulations=2*sum(row['kind'] == 'ranking' for row in support),
                dual_balance_vertices_checked=len(nodes)*len(problem['vertices']), dual_margin_weight_accumulations=len(support),
                potential_evaluations=len(nodes), potential_root_records=len(nodes)*len(problem['roots']),
                potential_rational_conversions=len(nodes)*len(problem['vertices']))


def test_lift_shares_exact_feature_vertices_across_cohorts():
    data = [root('source', {'DOWN': 0, 'LEFT': 1}, {'DOWN': 0., 'LEFT': 0.}, {'DOWN': 1., 'LEFT': 0.}),
            root('target', {'DOWN': 1, 'LEFT': 2}, {'DOWN': 0., 'LEFT': 0.}, {'DOWN': 1., 'LEFT': 0.}, 'TARGET')]
    old = audit.previous.build_problem([row for row, _ in data], [label for _, label in data]); original = deepcopy(old)
    problem = audit.lift_problem(old)
    assert old == original and [row['features'][1] for row in problem['vertices']] == [0, 1, 2]
    assert problem['roots'][0]['classes'][1]['vertex_id'] == problem['roots'][1]['classes'][0]['vertex_id']
    assert problem['inherited_problem_work'] == old['work']
    assert problem['work'] == dict(lift_class_records=4, lift_feature_values_read=24, lift_terminal_components_copied=12,
                                   lift_vertex_assignments=4, lift_roots_copied=2, lift_distinct_vertices=3)


def test_vertex_dual_rejects_balance_that_only_holds_for_linear_features():
    problem = lift([root('r0', {'DOWN': 0, 'LEFT': 1}, {'DOWN': 0., 'LEFT': 0.}, {'DOWN': 1., 'LEFT': 0.}),
                    root('r2', {'DOWN': 2, 'LEFT': 1}, {'DOWN': 0., 'LEFT': 0.}, {'DOWN': 1., 'LEFT': 0.})])
    constraints = audit.constraints_for(problem, [])
    certificate = dict(support=[dict(constraint_index=0, weight='1/2'), dict(constraint_index=1, weight='1/2')], upper_bound='0')
    assert (1-0)/2+(1-2)/2 == 0  # cancellation of numeric feature coordinate is insufficient
    assert not audit.verify_dual(problem, constraints, certificate)
    balanced = deepcopy(constraints); balanced[1]['best_vertex'], balanced[1]['bad_vertex'] = 1, 0
    assert audit.verify_dual(problem, balanced, certificate)
    wrong = deepcopy(certificate); wrong['upper_bound'] = '-1'
    assert not audit.verify_dual(problem, balanced, wrong)


def test_nonlinear_potential_witness_and_cap_are_verified_without_a_solver():
    problem = lift([root('left', {'DOWN': 1, 'LEFT': 0}, {'DOWN': 0., 'LEFT': 0.}, {'DOWN': 1., 'LEFT': 0.}),
                    root('right', {'DOWN': 1, 'LEFT': 2}, {'DOWN': 0., 'LEFT': 0.}, {'DOWN': 1., 'LEFT': 0.})])
    item = node(problem, 0, None, [], [0., 2., 0.], [(2, '1')], '1', 'strict_witness')
    witness = dict(node_id=0, potentials=item['primal']['potentials'], margin='1', evaluation=item['primal']['evaluation'])
    weak = {key: witness[key] for key in ('node_id', 'potentials', 'evaluation')}
    capacity = dict(status='strict_feasible', witness=witness, weak_witness=weak, upper_bound='1', nodes=[item], costs=costs(problem, [item]))
    checks, _ = audit.verify_capacity(problem, capacity)
    assert all(row['passed'] for row in checks)
    assert item['primal']['evaluation']['minimum_gap'] == '2'
    tampered = deepcopy(capacity); tampered['witness']['margin'] = '2'
    checks, _ = audit.verify_capacity(problem, tampered)
    assert not all(row['passed'] for row in checks)


def test_negative_incidence_cycles_require_complete_disjunction_coverage():
    data = [root('multi', {'DOWN': 0, 'LEFT': 2, 'RIGHT': 1}, {'DOWN': 0., 'LEFT': 0., 'RIGHT': 2.}, {'DOWN': 2., 'LEFT': 2., 'RIGHT': 1.}),
            root('unique1', {'DOWN': 0, 'LEFT': 1}, {'DOWN': 0., 'LEFT': 0.}, {'DOWN': 1., 'LEFT': 0.}),
            root('unique2', {'DOWN': 1, 'LEFT': 0}, {'DOWN': 1., 'LEFT': 0.}, {'DOWN': 1., 'LEFT': 0.}),
            root('unique3', {'DOWN': 1, 'LEFT': 2}, {'DOWN': 1., 'LEFT': 0.}, {'DOWN': 1., 'LEFT': 0.})]
    data[0][1]['action_components']['RIGHT'] = [2., 1., 0.]
    problem = lift(data)
    nodes = [node(problem, 0, None, [], [0., -.5, 0.], [(0, '1/2'), (1, '1/2')], '1/2', 'branch'),
             node(problem, 1, 0, [dict(root_id='multi', best_action='DOWN')], [0., -1.5, 0.], [(0, '1/2'), (2, '1/2')], '-1/2', 'pruned_negative'),
             node(problem, 2, 0, [dict(root_id='multi', best_action='LEFT')], [0., 0., 1.5], [(0, '1/2'), (3, '1/2')], '-1/2', 'pruned_negative')]
    nodes[0].update(branch_root_id='multi', branch_actions=['DOWN', 'LEFT'], children=[1, 2])
    capacity = dict(status='weak_infeasible', witness=None, weak_witness=None, upper_bound='-1/2', nodes=nodes, costs=costs(problem, nodes))
    checks, _ = audit.verify_capacity(problem, capacity)
    assert all(row['passed'] for row in checks)
    missing = deepcopy(capacity); missing['nodes'][0].update(children=[1], unexplored_actions=['LEFT'])
    checks, _ = audit.verify_capacity(problem, missing)
    assert not all(row['passed'] for row in checks)
