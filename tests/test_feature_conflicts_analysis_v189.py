"""Three pure alias/coverage/certificate cases; no data reads or LP solves."""
from copy import deepcopy
from fractions import Fraction

import pytest

from scripts import analyze_controlled_predictive_feature_conflicts_v189 as audit


def root(identity, values, rewards=None, source_id='FRESH_REPLICA:00', cohort='FRESH'):
    return dict(root_id=identity, source_id=source_id, cohort=cohort, life=0,
        canonical_board=[0]*16, legal_actions=list(reversed(list(values))),
        action_features={action: [0., float(value), 0., 0., 0., 0.] for action, value in values.items()},
        immediate_rewards=rewards or {action: 0. for action in values})


def saved_summary(rows, actions):
    # Only the saved choice is input; vectors and regrets are reconstructed from labels.
    return dict(root_records=[dict(root_id=row['root_id'], models=dict(LINEAR=dict(
        action=action, components=[999., 0., 0.], utility=999., regret=999.)))
        for row, action in zip(rows, actions)])


def capacity_fixture(problem, potentials, support, upper, status):
    """Build a small analytic certificate in the retained V181 wire format."""
    verifier = audit.capacity_audit
    constraints = verifier.constraints_for(problem, [])
    evaluation = verifier.evaluate_potentials(problem, potentials)
    disposition = {'strict_feasible': 'strict_witness', 'no_positive_margin': 'pruned_zero',
                   'weak_infeasible': 'pruned_negative'}[status]
    node = dict(node_id=0, parent_id=None, assigned=[], constraints=constraints,
        native_lp=dict(success=True, status=0, iterations=0, message='analytic fixture',
                       potentials=potentials, delta=float(Fraction(upper))),
        primal=dict(potentials=evaluation['potentials'], evaluation=evaluation),
        dual=dict(support=[dict(constraint_index=index, weight=weight) for index, weight in support], upper_bound=upper),
        disposition=disposition, branch_root_id=None, branch_actions=[], children=[], unexplored_actions=[])
    weak = dict(node_id=0, potentials=evaluation['potentials'], evaluation=evaluation) if evaluation['all_weak'] else None
    minimum = Fraction(1) if evaluation['minimum_gap'] is None else Fraction(evaluation['minimum_gap'])
    witness = dict(node_id=0, potentials=evaluation['potentials'], margin=str(min(Fraction(1), minimum)),
                   evaluation=evaluation) if status == 'strict_feasible' else None
    selected = [constraints[index] for index, _ in support]
    costs = dict(lp_solves=1, lp_constraint_rows=len(constraints), lp_variables=len(problem['vertices'])+1,
        lp_incidence_entries=sum(3 if row['kind'] == 'ranking' else 1 for row in constraints), lp_seconds=0.,
        symbolic_balance_solves=1, symbolic_balance_seconds=0., dual_support_rows=len(support),
        dual_vertex_flow_accumulations=2*sum(row['kind'] == 'ranking' for row in selected),
        dual_balance_vertices_checked=len(problem['vertices']), dual_margin_weight_accumulations=len(support),
        potential_evaluations=1, potential_root_records=len(problem['roots']),
        potential_rational_conversions=len(problem['vertices']))
    return dict(status=status, witness=witness, weak_witness=weak, upper_bound=upper, nodes=[node], costs=costs)


def test_alias_floor_uses_reward_representatives_full_vectors_and_optimal_value_regret():
    from acfqp.science import controlled_predictive_feature_conflicts_v189 as core

    source = [root('source', dict(DOWN=0, LEFT=1), source_id='DESIGN_SOURCE:00', cohort='SOURCE')]
    target = [
        root('target:a', dict(DOWN=0, LEFT=0, RIGHT=1), dict(DOWN=.5, LEFT=.5+audit.EPS/2, RIGHT=.125)),
        root('target:b', dict(DOWN=0, LEFT=0), dict(DOWN=.25, LEFT=.5)),
        root('target:c', dict(DOWN=0, LEFT=1), dict(DOWN=.5, LEFT=1.)),
    ]
    labels = [
        dict(root_id='target:a', action_components=dict(DOWN=[1., .5, 0.], LEFT=[.8, 0., .2], RIGHT=[.5, .5, .25])),
        dict(root_id='target:b', action_components=dict(DOWN=[.5, .25, .5], LEFT=[.5, .5, .75])),
        dict(root_id='target:c', action_components=dict(DOWN=[2., .5, .5], LEFT=[1.5, .5, .5])),
    ]
    roots, summary = dict(SOURCE=source, TARGET=target), saved_summary(target, ['RIGHT', 'LEFT', 'LEFT'])
    before = deepcopy((roots, labels, summary))
    diagnostics = audit.build_diagnostics(roots, labels, summary)
    production = core.build_diagnostics(roots, labels, summary)
    assert audit.same(diagnostics, production) and audit.same(production, diagnostics)
    assert diagnostics['costs'] == production['costs'] and (roots, labels, summary) == before
    first, tied, distinct = diagnostics['alias']['root_records']
    assert first['oracle']['actions'] == ['LEFT'] and first['oracle']['utility'] == pytest.approx(1.)
    assert first['alias']['actions'] == ['DOWN'] and first['alias']['utility'] == pytest.approx(.5)
    assert first['alias']['components_by_action'] == {'DOWN': [1., .5, 0.]}
    assert first['linear']['action'] == 'RIGHT' and first['linear']['components'] == [.5, .5, .25]
    assert first['linear']['regret'] == pytest.approx(.75)
    assert first['within_root_regret'] == pytest.approx(.5) and first['remaining_regret'] == pytest.approx(.25)
    assert first['linear_error'] is True and first['alias_loss'] is True
    classes = diagnostics['problem']['roots'][0]['classes']
    assert classes[0]['actions'] == ['DOWN', 'LEFT'] and classes[0]['representative'] == 'DOWN'
    assert tied['oracle']['actions'] == ['DOWN', 'LEFT'] and tied['oracle']['reference_action'] == 'DOWN'
    assert tied['alias']['actions'] == ['LEFT'] and tied['linear']['action'] == 'LEFT'
    assert tied['linear']['regret'] == tied['within_root_regret'] == tied['remaining_regret'] == 0.
    assert tied['linear_error'] is False and tied['alias_loss'] is False
    assert distinct['within_root_regret'] == 0. and distinct['remaining_regret'] == pytest.approx(.5)
    assert all(row['linear_is_class_representative'] for row in diagnostics['alias']['root_records'])
    assert all(row['cohort'] == 'FRESH' for row in diagnostics['problem']['roots'])
    assert diagnostics['costs']['alias_action_utility_evaluations'] == 12
    assert diagnostics['costs']['alias_original_terminal_component_reads'] == 21
    assert diagnostics['costs']['alias_linear_component_reads'] == 9
    assert diagnostics['costs']['coverage_source_ordered_pairs'] == 2
    assert diagnostics['costs']['coverage_target_ordered_pairs'] == 10
    capacity = capacity_fixture(diagnostics['problem'], [2., 0.], [(2, '1')], '1', 'strict_feasible')
    result = audit.summarize(diagnostics, capacity)
    assert audit.same(result, core.summarize(production, capacity))
    assert result['alias']['linear_error_roots'] == 2 and result['alias']['within_root_loss_roots'] == 1
    assert result['alias']['linear_errors_affected_by_alias'] == 1
    assert result['alias']['within_root_regret_mean'] == pytest.approx(1/6)
    assert result['alias']['linear_regret_mean'] == pytest.approx(5/12)
    assert result['alias']['remaining_regret_mean'] == pytest.approx(1/4)
    assert result['alias']['within_root_regret_mean']/result['alias']['linear_regret_mean'] == pytest.approx(.4)
    assert result['alias']['oracle']['reference_components'] == pytest.approx([1.1, .25, .4])
    assert result['alias']['alias']['reference_components'] == pytest.approx([7/6, .5, 5/12])
    assert result['alias']['linear']['reference_components'] == pytest.approx([5/6, .5, .5])
    assert result['work'] == dict(summary_alias_root_records=3, summary_reference_component_reads=27,
                                 summary_regret_scalar_reads=9, summary_coverage_flags_read=15)


def test_source143_target96_distinguish_tuple_occurrences_support_direction_and_reward_gap():
    from acfqp.science import controlled_predictive_feature_conflicts_v189 as core

    source = [root(f'source:{index:03d}', dict(DOWN=0, LEFT=1),
                   source_id=f'DESIGN_SOURCE:{index % 36:02d}', cohort='SOURCE') for index in range(143)]
    # Two occurrences of phi0 and of phi0->phi0 at this root still give support 1.
    source[0]['legal_actions'].append('RIGHT')
    source[0]['action_features']['RIGHT'] = [0.]*6
    source[0]['immediate_rewards']['RIGHT'] = 0.
    target, labels = [], []
    for index in range(96):
        values = (dict(DOWN=0, LEFT=0) if index == 0 else dict(DOWN=1, LEFT=1) if index < 24
                  else dict(DOWN=1, LEFT=0) if index < 48 else dict(DOWN=0, LEFT=1) if index < 84
                  else dict(DOWN=0, LEFT=2))
        rewards = dict(DOWN=.25 if 48 <= index < 72 else 0., LEFT=0.)
        target.append(root(f'target:{index:03d}', values, rewards, source_id=f'FRESH_REPLICA:{index//24:02d}'))
        labels.append(dict(root_id=target[-1]['root_id'], action_components=dict(DOWN=[1., 0., 0.], LEFT=[0., 0., 0.])))
    roots, summary = dict(SOURCE=source, TARGET=target), saved_summary(target, ['DOWN']*96)
    diagnostics, production = audit.build_diagnostics(roots, labels, summary), core.build_diagnostics(roots, labels, summary)
    assert audit.same(diagnostics, production) and audit.same(production, diagnostics)
    assert diagnostics['costs'] == production['costs']
    coverage = diagnostics['coverage']; rows = coverage['root_records']
    assert coverage['source_roots'] == 143 and coverage['source_groups'] == 36
    assert coverage['distinct_tuples'] == 2
    assert coverage['distinct_contrast_structures'] == coverage['distinct_reward_thresholds'] == 3
    assert coverage['pair_definition'] == 'ALL_ORDERED_DISTINCT_LEGAL_ACTIONS'
    assert coverage['threshold_definition'] == 'EXACT_FIRST_REWARD_DIFFERENCE'
    occurrences = [entry for row in rows for entry in row['tuples']]
    assert len(rows) == 96 and len(occurrences) == 192
    assert sum(len({tuple(entry['features']) for entry in row['tuples']}) for row in rows) == 168
    assert len({tuple(entry['features']) for entry in occurrences}) == 3
    assert sum(entry['seen'] for entry in occurrences) == 180
    assert sum(row['all_tuples_seen'] for row in rows) == 84
    assert sum(row['all_contrast_structures_seen'] for row in rows) == 61
    assert sum(row['all_reward_thresholds_seen'] for row in rows) == 37
    duplicate = rows[0]['ordered_contrasts']
    assert len(duplicate) == 2 and all(entry['source_root_count'] == entry['source_group_count'] == 1 for entry in duplicate)
    assert all(entry['reward_threshold_source_root_count'] == entry['reward_threshold_source_group_count'] == 1 for entry in duplicate)
    assert rows[1]['all_tuples_seen'] is True and rows[1]['all_contrast_structures_seen'] is False
    reversed_pair = next(entry for entry in rows[24]['ordered_contrasts'] if entry['first_action'] == 'DOWN')
    assert reversed_pair['first_features'] == [0., 1., 0., 0., 0., 0.]
    assert reversed_pair['second_features'] == [0.]*6
    assert reversed_pair['structure_seen'] is True and reversed_pair['reward_threshold_seen'] is True
    assert reversed_pair['source_root_count'] == 143 and reversed_pair['source_group_count'] == 36
    assert reversed_pair['reward_difference_fraction'] == '0'
    gap = rows[48]['ordered_contrasts']
    assert [entry['reward_difference_fraction'] for entry in gap] == ['1/4', '-1/4']
    assert all(entry['structure_seen'] and not entry['reward_threshold_seen'] for entry in gap)
    assert all(entry['source_root_count'] == 143 and entry['source_group_count'] == 36 for entry in gap)
    assert all(entry['reward_threshold_source_root_count'] == entry['reward_threshold_source_group_count'] == 0 for entry in gap)
    novel = next(entry for entry in rows[84]['tuples'] if entry['action'] == 'LEFT')
    assert novel['seen'] is False and novel['source_root_count'] == novel['source_group_count'] == 0
    for row in rows:
        assert row['alias_optimal_vs_linear'] == [dict(first_action='DOWN', second_action='DOWN',
            same_action=True, requires_change=False, structure_seen=None, reward_threshold_seen=None)]
    assert diagnostics['costs']['coverage_source_legal_actions'] == 287
    assert diagnostics['costs']['coverage_source_feature_values_read'] == 1722
    assert diagnostics['costs']['coverage_source_ordered_pairs'] == 290
    assert diagnostics['costs']['coverage_target_legal_actions'] == diagnostics['costs']['coverage_target_tuple_lookups'] == 192
    assert diagnostics['costs']['coverage_target_ordered_pairs'] == 192
    assert diagnostics['costs']['coverage_alias_optimal_linear_records'] == 96
    assert len(diagnostics['problem']['roots']) == 96
    assert not any(row['root_id'].startswith('source:') for row in diagnostics['problem']['roots'])


def test_target_only_exact_certificates_keep_strict_zero_and_negative_claims_separate():
    from acfqp.science import controlled_predictive_feature_conflicts_v189 as core

    source = [root('source', dict(DOWN=0, LEFT=1), source_id='DESIGN_SOURCE:00', cohort='SOURCE')]
    fixtures = [
        ('strict_feasible', [dict(DOWN=1, LEFT=0), dict(DOWN=1, LEFT=2)],
         [dict(DOWN=[1., 0., 0.], LEFT=[0., 0., 0.])]*2, dict(DOWN=0., LEFT=0.),
         [0., 2., 0.], [(2, '1')], '1', ['LEFT', 'LEFT'], True),
        ('no_positive_margin', [dict(DOWN=0, LEFT=1), dict(DOWN=1, LEFT=0)],
         [dict(DOWN=[1., 0., 0.], LEFT=[0., 0., 0.])]*2, dict(DOWN=0., LEFT=0.),
         [0., 0.], [(0, '1/2'), (1, '1/2')], '0', ['DOWN', 'DOWN'], True),
        ('no_positive_margin', [dict(DOWN=0, LEFT=1), dict(DOWN=0, LEFT=1)],
         [dict(DOWN=[1., 0., 0.], LEFT=[0., 0., 0.]), dict(DOWN=[0., 0., 0.], LEFT=[1., 0., 0.])],
         dict(DOWN=0., LEFT=0.), [0., 0.], [(0, '1/2'), (1, '1/2')], '0', ['DOWN', 'DOWN'], False),
        ('weak_infeasible', [dict(DOWN=0, LEFT=1), dict(DOWN=1, LEFT=0)],
         [dict(DOWN=[2., 0., 0.], LEFT=[1., 1., 0.])]*2, dict(DOWN=0., LEFT=1.),
         [0., 0.], [(0, '1/2'), (1, '1/2')], '-1', ['LEFT', 'LEFT'], None),
    ]
    for status, features, components, rewards, potentials, support, upper, choices, weak_optimal in fixtures:
        target = [root(f'target:{index}', values, dict(rewards)) for index, values in enumerate(features)]
        labels = [dict(root_id=row['root_id'], action_components=vector) for row, vector in zip(target, components)]
        diagnostics = audit.build_diagnostics(dict(SOURCE=source, TARGET=target), labels, saved_summary(target, choices))
        capacity = capacity_fixture(diagnostics['problem'], potentials, support, upper, status)
        checks, verify_work = audit.capacity_audit.verify_capacity(diagnostics['problem'], capacity)
        assert all(check['passed'] for check in checks)
        assert verify_work['nodes_verified'] == 1 and verify_work['potential_root_records'] == 2
        result = audit.summarize(diagnostics, capacity)
        assert audit.same(result, core.summarize(diagnostics, capacity))
        assert result['complete'] is True and result['roots'] == 2
        assert result['capacity']['status'] == status and result['capacity']['upper_bound'] == upper
        assert result['capacity']['solver_nodes'] == result['capacity']['lp_solves'] == 1
        assert result['capacity']['weak_witness_all_optimal'] is weak_optimal
        assert result['alias']['within_root_regret_mean'] == 0.
        assert result['new_environment_samples'] == result['new_fits'] == result['new_labels'] == 0
        if status == 'strict_feasible':
            assert result['capacity']['interpretation'] == 'strict_alias_optimal_witness_on_retained_TARGET'
            assert result['dual_explanations'] == []
        elif status == 'no_positive_margin':
            interpretation = ('no_positive_margin_actual_tie_policy_attained' if weak_optimal
                              else 'no_positive_margin_actual_tie_policy_not_settled')
            assert result['capacity']['interpretation'] == interpretation
            expected = 'attained_by_retained_weak_witness' if weak_optimal else 'unknown'
            assert result['capacity']['actual_tie_policy_attainability'] == expected
            explanation = result['dual_explanations'][0]
            assert explanation['upper_bound'] == explanation['weighted_reward_difference_sum'] == '0'
            assert explanation['balanced_vertex_flow'] is True
        else:
            assert result['capacity']['interpretation'] == 'incompatible_alias_rankings_on_retained_TARGET'
            assert result['capacity']['actual_tie_policy_attainability'] == 'unknown'
            assert result['alias']['linear_regret_mean'] == pytest.approx(2.)
            explanation = result['dual_explanations'][0]
            assert explanation['upper_bound'] == explanation['weighted_reward_difference_sum'] == '-1'
            assert explanation['margin_weight_sum'] == '1' and explanation['balanced_vertex_flow'] is True
            assert len(explanation['edges']) == 2
            assert all(edge['reward_difference_fraction'] == '-1' for edge in explanation['edges'])
            assert all(row['net_flow'] == '0' for row in explanation['vertex_flows'])
            tampered = deepcopy(capacity); tampered['nodes'][0]['dual']['upper_bound'] = '0'
            rejected, _ = audit.capacity_audit.verify_capacity(diagnostics['problem'], tampered)
            assert not all(check['passed'] for check in rejected)
