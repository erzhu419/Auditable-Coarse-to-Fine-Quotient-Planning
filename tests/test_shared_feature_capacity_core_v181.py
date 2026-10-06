"""Pure vertex-potential witnesses and whole-function contradictions."""
from copy import deepcopy
from fractions import Fraction
from types import SimpleNamespace

import pytest

from acfqp.science import controlled_predictive_ranking_capacity_v180 as prior
from acfqp.science import controlled_predictive_shared_feature_capacity_v181 as core


def phi(vacancies):
    return [0, vacancies, 1, 0, 0, 0]


def case(name, features, utilities, rewards=None):
    legal = [action for action in prior.ACTIONS if action in features]
    root = dict(root_id=name, cohort='SOURCE', life=0, source_id='DESIGN_SOURCE:00',
        legal_actions=legal, action_features=features,
        immediate_rewards={action: (rewards or {}).get(action, 0.) for action in legal})
    label = dict(root_id=name, action_components={action: [utilities[action], 0., 0.] for action in legal})
    return root, label


def problem(*cases):
    old = prior.build_problem([row[0] for row in cases], [row[1] for row in cases])
    return core.lift_problem(old)


def assert_vertex_dual(problem, node):
    flow, delta, upper = [Fraction(0)]*len(problem['vertices']), Fraction(0), Fraction(0)
    for support in node['dual']['support']:
        weight = Fraction(support['weight']); assert weight >= 0
        row = node['constraints'][support['constraint_index']]
        delta += weight; upper += weight*Fraction(row['b'])
        if row['kind'] == 'ranking':
            flow[row['bad_vertex']] += weight; flow[row['best_vertex']] -= weight
    assert flow == [0]*len(flow) and delta == 1
    assert upper == Fraction(node['dual']['upper_bound'])


def test_lift_preserves_audited_aliases_and_optimal_sets_without_mutating_or_recomputing():
    rows = [case('z', dict(DOWN=phi(2), LEFT=phi(2), RIGHT=phi(1)), dict(DOWN=9., LEFT=1., RIGHT=1.), dict(LEFT=.5)),
            case('a', dict(DOWN=phi(3), LEFT=phi(1)), dict(DOWN=2., LEFT=0.))]
    old = prior.build_problem([row[0] for row in rows], [row[1] for row in rows])
    original = deepcopy(old)
    lifted = core.lift_problem(old)
    assert old == original
    assert [vertex['features'] for vertex in lifted['vertices']] == [phi(1), phi(2), phi(3)]
    assert lifted['inherited_problem_work'] == old['work'] and lifted['work']['lift_distinct_vertices'] == 3
    for before, after in zip(old['roots'], lifted['roots']):
        assert before['optimal_actions'] == after['optimal_actions']
        assert before['suboptimal_actions'] == after['suboptimal_actions']
        for first, second in zip(before['classes'], after['classes']):
            assert {key: value for key, value in second.items() if key != 'vertex_id'} == first
            assert lifted['vertices'][second['vertex_id']]['features'] == first['features']


def test_arbitrary_shared_function_resolves_opposite_linear_slopes_without_per_root_values():
    data = problem(
        case('a', dict(DOWN=phi(2), LEFT=phi(1)), dict(DOWN=.25, LEFT=2.), dict(DOWN=.25)),
        case('b', dict(DOWN=phi(2), LEFT=phi(3)), dict(DOWN=125/256, LEFT=2.), dict(DOWN=125/256)))
    result = core.solve_capacity(data)
    assert result['status'] == 'strict_feasible' and result['costs']['lp_solves'] == 1
    evaluation = result['witness']['evaluation']
    assert [row['chosen'] for row in evaluation['root_records']] == ['LEFT', 'LEFT']
    values = list(map(Fraction, result['witness']['potentials']))
    assert values[0]-values[1] >= Fraction(5, 4)
    assert values[2]-values[1] >= Fraction(381, 256)
    assert len(values) == 3 and evaluation['all_optimal']
    assert_vertex_dual(data, result['nodes'][0])


def test_negative_feature_vertex_cycle_excludes_any_shared_function_with_exact_two_edge_certificate():
    data = problem(
        case('a', dict(DOWN=phi(2), LEFT=phi(1)), dict(DOWN=1., LEFT=2.), dict(DOWN=1.)),
        case('b', dict(DOWN=phi(1), LEFT=phi(2)), dict(DOWN=1., LEFT=2.), dict(DOWN=1.)))
    result = core.solve_capacity(data)
    assert result['status'] == 'weak_infeasible' and result['upper_bound'] == '-1'
    assert result['witness'] is None and result['weak_witness'] is None
    assert len(result['nodes'][0]['dual']['support']) == 2
    assert_vertex_dual(data, result['nodes'][0])
    assert result['costs']['lp_incidence_entries'] == 7


def test_multi_optimal_search_rejects_one_choice_but_finds_the_other_without_canonical_false_failure():
    data = problem(
        case('a', dict(DOWN=phi(2), LEFT=phi(1)), dict(DOWN=1., LEFT=2.), dict(DOWN=1.)),
        case('b', dict(DOWN=phi(2), LEFT=phi(3), RIGHT=phi(1)), dict(DOWN=2., LEFT=2., RIGHT=1.)))
    result = core.solve_capacity(data)
    assert result['status'] == 'strict_feasible' and result['costs']['lp_solves'] == 3
    root, first, second = result['nodes']
    assert root['branch_actions'] == ['DOWN', 'LEFT'] and root['children'] == [1, 2]
    assert first['assigned'] == [dict(root_id='b', best_action='DOWN')]
    assert first['disposition'] == 'pruned_negative'
    assert second['assigned'] == [dict(root_id='b', best_action='LEFT')]
    assert second['disposition'] == 'strict_witness'
    assert result['witness']['evaluation']['root_records'][1]['chosen'] == 'LEFT'
    for node in result['nodes']:
        assert_vertex_dual(data, node)


def test_negative_disjunctive_conclusion_covers_every_optimal_branch():
    data = problem(
        case('a', dict(DOWN=phi(0), LEFT=phi(2)), dict(DOWN=1., LEFT=2.), dict(DOWN=1.)),
        case('b', dict(DOWN=phi(1), LEFT=phi(2)), dict(DOWN=1., LEFT=2.), dict(DOWN=1.)),
        case('z', dict(DOWN=phi(0), LEFT=phi(1), RIGHT=phi(2)), dict(DOWN=2., LEFT=2., RIGHT=0.)))
    result = core.solve_capacity(data)
    assert result['status'] == 'weak_infeasible' and result['upper_bound'] == '-1/2'
    assert result['nodes'][0]['children'] == [1, 2] and not result['nodes'][0]['unexplored_actions']
    assert [node['assigned'][-1]['best_action'] for node in result['nodes'][1:]] == ['DOWN', 'LEFT']
    assert all(node['disposition'] == 'pruned_negative' for node in result['nodes'][1:])
    for node in result['nodes']:
        assert_vertex_dual(data, node)


def test_zero_margin_bound_keeps_lexical_boundary_distinct_from_strict_capacity():
    data = problem(
        case('a', dict(DOWN=phi(1), LEFT=phi(2)), dict(DOWN=1., LEFT=0.)),
        case('b', dict(DOWN=phi(2), LEFT=phi(1)), dict(DOWN=1., LEFT=0.)))
    result = core.solve_capacity(data)
    assert result['status'] == 'no_positive_margin' and result['upper_bound'] == '0'
    assert result['weak_witness']['evaluation']['all_weak']
    assert result['weak_witness']['evaluation']['all_optimal']
    incompatible = problem(
        case('a', dict(DOWN=phi(1), LEFT=phi(2)), dict(DOWN=0., LEFT=1.)),
        case('b', dict(DOWN=phi(2), LEFT=phi(1)), dict(DOWN=0., LEFT=1.)))
    other = core.solve_capacity(incompatible)
    assert other['status'] == 'no_positive_margin'
    assert other['weak_witness']['evaluation']['all_weak']
    assert not other['weak_witness']['evaluation']['all_optimal']


def test_potential_gauge_shift_preserves_action_gap_and_complete_vector_evaluation():
    root, label = case('vector', dict(DOWN=phi(1), LEFT=phi(2)), dict(DOWN=1., LEFT=0.))
    label['action_components'] = dict(DOWN=[.5, .25, .75], LEFT=[.5, .5, .5])
    data = problem((root, label))
    first = core.evaluate_potentials(data, ['1/2048', '0'])
    shifted = core.evaluate_potentials(data, ['18433/2048', '9'])
    for evaluation in (first, shifted):
        row = evaluation['root_records'][0]
        assert row['chosen'] == 'DOWN' and row['optimal_vs_bad_gap'] == '1/2048'
        assert row['chosen_components'] == [.5, .25, .75] and row['chosen_utility'] == 1.
        assert evaluation['all_optimal']


def test_all_optimal_scope_requires_only_cap_lp_not_a_gauge_or_artificial_potential_bound():
    data = problem(case('tie', dict(DOWN=phi(1), LEFT=phi(2)), dict(DOWN=1., LEFT=1.)))
    result = core.solve_capacity(data)
    assert result['status'] == 'strict_feasible' and result['witness']['margin'] == '1'
    assert result['costs']['lp_solves'] == 1 and len(result['nodes'][0]['constraints']) == 1
    assert result['nodes'][0]['constraints'][0]['kind'] == 'margin_cap'
    assert_vertex_dual(data, result['nodes'][0])


def test_native_failure_retains_paid_scope_as_execution_error_not_scientific_impossibility(monkeypatch):
    data = problem(case('scope', dict(DOWN=phi(1), LEFT=phi(2)), dict(DOWN=1., LEFT=0.)))
    monkeypatch.setattr(core, 'linprog', lambda *args, **kwargs:
        SimpleNamespace(success=False, status=2, message='synthetic native failure', nit=0))
    with pytest.raises(core.CapacityExecutionError) as caught:
        core.solve_capacity(data)
    record = caught.value.record
    assert record['status'] == 'execution_error' and record['costs']['lp_solves'] == 1
    assert record['witness'] is None and record['upper_bound'] is None
