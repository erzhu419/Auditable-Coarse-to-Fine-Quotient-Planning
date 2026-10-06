"""New alias, coverage and evidence-reporting logic; no LP is executed."""
from copy import deepcopy

import pytest

from acfqp.science import controlled_predictive_feature_conflicts_v189 as core


A, B, C = [0, 0, 0, 0, 0, 0], [0, 1, 0, 0, 0, 0], [0, 2, 0, 0, 0, 0]


def root(name, features, rewards=None, source='FRESH_REPLICA:00', cohort='TARGET'):
    actions = [a for a in core.ACTIONS if a in features]
    return dict(root_id=name, source_id=source, cohort=cohort, life=0, legal_actions=actions,
        action_features=deepcopy(features), immediate_rewards=rewards or {a: 0. for a in actions})


def build(target, components, chosen, source=()):
    labels = [dict(root_id=row['root_id'], action_components=components[row['root_id']]) for row in target]
    summary = dict(root_records=[dict(root_id=row['root_id'], models={'LINEAR': dict(action=chosen[row['root_id']])})
                                 for row in target])
    return core.build_diagnostics(dict(SOURCE=list(source), TARGET=target), labels, summary)


def capacity(status='no_positive_margin', weak=None, nodes=None, upper='0'):
    return dict(status=status, upper_bound=upper, weak_witness=weak, witness=None,
                nodes=[] if nodes is None else nodes, costs={})


def test_within_root_alias_loss_is_separate_from_remaining_linear_regret():
    observed = root('alias', dict(DOWN=A, LEFT=A, UP=B), dict(DOWN=1/256., LEFT=0., UP=0.))
    vectors = dict(DOWN=[.01, 1., 0.], LEFT=[2., 0., 1.], UP=[1., 0., 0.])
    diagnostics = build([observed], {'alias': vectors}, {'alias': 'DOWN'})
    row = diagnostics['alias']['root_records'][0]
    assert row['oracle']['actions'] == ['LEFT'] and row['oracle']['components_by_action']['LEFT'] == [2., 0., 1.]
    assert row['alias']['actions'] == ['UP'] and row['alias']['components_by_action']['UP'] == [1., 0., 0.]
    assert row['within_root_regret'] == 2.
    assert row['remaining_regret'] == pytest.approx(1.99)
    assert row['linear']['regret'] == pytest.approx(row['within_root_regret']+row['remaining_regret'])
    assert row['alias_loss'] and row['linear_error'] and row['linear_is_class_representative']
    assert diagnostics['problem']['roots'][0]['optimal_actions'] == ['UP']  # Capacity never targets discarded LEFT.
    report = core.summarize(diagnostics, capacity('strict_feasible', upper='1'))
    assert report['alias']['within_root_regret_mean'] == 2.
    assert report['capacity']['interpretation'] == 'strict_alias_optimal_witness_on_retained_TARGET'
    assert report['alias']['oracle']['reference_components'] == [2., 0., 1.]
    assert report['alias']['alias']['reference_components'] == [1., 0., 0.]
    assert report['alias']['linear_errors_affected_by_alias'] == 1
    tied = root('tied-alias', dict(DOWN=A, LEFT=A))
    tied_diagnostics = build([tied], {'tied-alias': dict(DOWN=[0., 1., 0.], LEFT=[2., 0., 1.])}, {'tied-alias': 'DOWN'})
    tied_row = tied_diagnostics['alias']['root_records'][0]
    assert tied_row['alias']['actions'] == ['DOWN'] and tied_row['within_root_regret'] == 4.
    assert tied_row['remaining_regret'] == 0.
    self_comparison = tied_diagnostics['coverage']['root_records'][0]['alias_optimal_vs_linear'][0]
    assert self_comparison['same_action'] and not self_comparison['requires_change']
    assert self_comparison['structure_seen'] is None


def test_every_optimal_action_and_its_complete_vector_are_retained():
    observed = root('full-ties', dict(DOWN=A, LEFT=B, RIGHT=C))
    vectors = dict(DOWN=[1., 0., 0.], LEFT=[0., 0., 1.], RIGHT=[0., 1., 0.])
    diagnostics = build([observed], {'full-ties': vectors}, {'full-ties': 'RIGHT'})
    row = diagnostics['alias']['root_records'][0]
    for optimum in ('oracle', 'alias'):
        assert row[optimum]['actions'] == ['DOWN', 'LEFT']
        assert row[optimum]['components_by_action'] == dict(DOWN=[1., 0., 0.], LEFT=[0., 0., 1.])
    assert row['within_root_regret'] == 0. and row['remaining_regret'] == 2.
    assert diagnostics['problem']['roots'][0]['optimal_actions'] == ['DOWN', 'LEFT']
    comparisons = diagnostics['coverage']['root_records'][0]['alias_optimal_vs_linear']
    assert [(row['first_action'], row['second_action']) for row in comparisons] == [('DOWN', 'RIGHT'), ('LEFT', 'RIGHT')]
    report = core.summarize(diagnostics, capacity())
    assert report['alias']['oracle']['reference_components'] == [1., 0., 0.]  # One complete reference, not component maxima.
    assert report['alias']['alias']['utility'] == 1.


def test_source_coverage_is_directed_reward_exact_and_never_reads_source_labels():
    class NoSourceLabels(dict):
        def __getitem__(self, key):
            raise AssertionError('coverage used a SOURCE terminal label')
    source = [root('source:0', dict(DOWN=A, LEFT=B, UP=A), dict(DOWN=1/256., LEFT=0., UP=0.), 'DESIGN_SOURCE:00', 'SOURCE'),
              root('source:1', dict(DOWN=A, LEFT=B), dict(DOWN=1/128., LEFT=0.), 'DESIGN_SOURCE:01', 'SOURCE')]
    for row in source:
        row['action_components'] = NoSourceLabels()
    target = [root('seen', dict(DOWN=A, LEFT=B), dict(DOWN=1/256., LEFT=0.)),
              root('new-threshold', dict(DOWN=A, LEFT=B), dict(DOWN=1/512., LEFT=0.)),
              root('reverse-threshold', dict(DOWN=B, LEFT=A), dict(DOWN=1/256., LEFT=0.))]
    vectors = {row['root_id']: dict(DOWN=[1., 0., 0.], LEFT=[0., 0., 0.]) for row in target}
    diagnostics = build(target, vectors, {row['root_id']: 'LEFT' for row in target}, source)
    records = {row['root_id']: row for row in diagnostics['coverage']['root_records']}
    assert diagnostics['coverage']['source_roots'] == diagnostics['coverage']['source_groups'] == 2
    assert diagnostics['coverage']['distinct_tuples'] == 2
    assert diagnostics['costs']['coverage_source_ordered_pairs'] == 8
    assert diagnostics['costs']['coverage_source_reward_fraction_conversions'] == 5
    assert all(row['all_tuples_seen'] and row['all_contrast_structures_seen'] for row in records.values())
    assert records['seen']['all_reward_thresholds_seen']
    assert not records['new-threshold']['all_reward_thresholds_seen']
    assert not records['reverse-threshold']['all_reward_thresholds_seen']
    pair = records['seen']['ordered_contrasts'][0]
    assert pair['reward_difference_fraction'] == '1/256'
    assert pair['source_root_count'] == pair['source_group_count'] == 2
    assert pair['reward_threshold_source_root_count'] == 1
    assert records['reverse-threshold']['ordered_contrasts'][0]['first_features'] == B
    assert records['reverse-threshold']['ordered_contrasts'][0]['structure_seen']
    assert not records['reverse-threshold']['ordered_contrasts'][0]['reward_threshold_seen']
    report = core.summarize(diagnostics, capacity())
    assert report['coverage']['linear_errors'] == dict(roots=3, all_tuples_seen=3,
        all_contrast_structures_seen=3, all_reward_thresholds_seen=1)


def test_negative_dual_explanation_preserves_exact_cycle_full_vectors_and_subtree_context():
    target = [root('cycle:a', dict(DOWN=B, LEFT=A), dict(DOWN=.25, LEFT=0.)),
              root('cycle:b', dict(DOWN=A, LEFT=B), dict(DOWN=.5, LEFT=0.))]
    vectors = {'cycle:a': dict(DOWN=[.25, 1., 0.], LEFT=[2., 0., 1.]),
               'cycle:b': dict(DOWN=[.5, 1., 0.], LEFT=[2., 0., 1.])}
    diagnostics = build(target, vectors, {'cycle:a': 'DOWN', 'cycle:b': 'DOWN'})
    constraints = core.capacity_backend._constraints(diagnostics['problem'], [])
    assert [row['b'] for row in constraints] == ['-1/4', '-1/2', '1']
    node = dict(node_id=0, assigned=[], disposition='pruned_negative', constraints=constraints,
        dual=dict(upper_bound='-3/8', support=[dict(constraint_index=0, weight='1/2'),
                                              dict(constraint_index=1, weight='1/2')]))
    frozen = capacity('weak_infeasible', nodes=[node], upper='-3/8')
    frozen['costs']['lp_solves'] = 1  # Retained input metadata, no solver call by this test.
    report = core.summarize(diagnostics, frozen)
    explanation = report['dual_explanations'][0]
    assert explanation['upper_bound'] == explanation['weighted_reward_difference_sum'] == '-3/8'
    assert explanation['margin_weight_sum'] == '1' and explanation['balanced_vertex_flow']
    assert [row['net_flow'] for row in explanation['vertex_flows']] == ['0', '0']
    assert [row['root_id'] for row in explanation['edges']] == ['cycle:a', 'cycle:b']
    assert explanation['edges'][0]['best']['action'] == 'LEFT'
    assert explanation['edges'][0]['best']['features'] == A
    assert explanation['edges'][0]['bad']['features'] == B
    assert explanation['edges'][0]['best']['components'] == [2., 0., 1.]
    assert explanation['edges'][0]['bad']['components'] == [.25, 1., 0.]
    assert explanation['edges'][0]['bad']['immediate_reward_fraction'] == '1/4'
    assert report['work']['explanation_vertex_flow_accumulations'] == 4
    assert report['capacity']['interpretation'] == 'incompatible_alias_rankings_on_retained_TARGET'
    assert report['alias']['within_root_loss_roots'] == 0  # A global conflict never labels each support root irreparable.
    node['assigned'] = [dict(root_id='previous-disjunction', best_action='LEFT')]
    scoped = core.summarize(diagnostics, frozen)['dual_explanations'][0]
    assert scoped['assigned'] == node['assigned']


def test_zero_margin_does_not_invent_tie_policy_impossibility():
    observed = root('zero-margin', dict(DOWN=A, LEFT=B))
    diagnostics = build([observed], {'zero-margin': dict(DOWN=[0., 1., 0.], LEFT=[1., 0., 0.])}, {'zero-margin': 'DOWN'})
    weak = dict(evaluation=dict(all_optimal=False, all_weak=True))
    report = core.summarize(diagnostics, capacity(weak=weak))
    assert report['capacity']['status'] == 'no_positive_margin'
    assert report['capacity']['actual_tie_policy_attainability'] == 'unknown'
    assert report['capacity']['weak_witness_all_optimal'] is False
    weak['evaluation']['all_optimal'] = True
    attainable = core.summarize(diagnostics, capacity(weak=weak))
    assert attainable['capacity']['actual_tie_policy_attainability'] == 'attained_by_retained_weak_witness'
    assert attainable['capacity']['interpretation'] == 'no_positive_margin_actual_tie_policy_attained'
    assert attainable['new_fits'] == attainable['new_labels'] == attainable['new_environment_samples'] == 0


def test_diagnostic_only_reuses_problem_and_lift_once_and_rejects_unbound_frozen_rows(monkeypatch):
    assert core.solve_capacity is core.capacity_backend.solve_capacity
    assert core.evaluate_potentials is core.capacity_backend.evaluate_potentials
    calls = dict(problem=0, lift=0)
    problem, lift = core.ranking.build_problem, core.capacity_backend.lift_problem
    def counted_problem(*args, **kwargs):
        calls['problem'] += 1
        return problem(*args, **kwargs)
    def counted_lift(*args, **kwargs):
        calls['lift'] += 1
        return lift(*args, **kwargs)
    def forbidden(*args, **kwargs):
        raise AssertionError('diagnostic assembly executed an LP or evaluated a new policy')
    monkeypatch.setattr(core.ranking, 'build_problem', counted_problem)
    monkeypatch.setattr(core.capacity_backend, 'lift_problem', counted_lift)
    monkeypatch.setattr(core, 'solve_capacity', forbidden)
    monkeypatch.setattr(core, 'evaluate_potentials', forbidden)
    observed = root('binding', dict(DOWN=A, LEFT=B))
    labels = [dict(root_id='binding', action_components=dict(DOWN=[1., 0., 0.], LEFT=[0., 0., 0.]))]
    summary = dict(root_records=[dict(root_id='binding', models={'LINEAR': dict(action='LEFT')})])
    roots = dict(SOURCE=[], TARGET=[observed])
    diagnostics = core.build_diagnostics(roots, labels, summary)
    assert calls == dict(problem=1, lift=1)
    assert diagnostics['costs']['problem_root_records'] == diagnostics['costs']['lift_roots_copied'] == 1
    assert diagnostics['costs']['diagnostic_label_root_bindings'] == 1
    assert 'lp_solves' not in diagnostics['costs']
    with pytest.raises(ValueError, match='bind once each'):
        core.build_diagnostics(roots, labels+labels, summary)
    with pytest.raises(ValueError, match='bind once each'):
        core.build_diagnostics(roots, labels, dict(root_records=[]))
    assert calls == dict(problem=1, lift=1)
