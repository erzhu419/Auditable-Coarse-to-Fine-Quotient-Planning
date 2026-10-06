"""Bind the existing full-vector fit and known absorbing-goal semantics."""
import pytest
from scripts import run_controlled_predictive_ranking_capacity_v180 as runner


def test_scalar_capacity_class_uses_all_three_existing_components():
    coefficients = [[1., 2., 3.], [.5, .25, .125], [-2., 0., 4.], [0., 1., 0.], [1., 0., 0.], [0., 0., 1.]]
    assert runner.fitted_beta({'SHARED': {'coefficients': coefficients}}) == pytest.approx([2., .375, 2., -1., 1., 1.])


def test_terminal_identity_detects_a_reward_or_event_label_misalignment():
    roots = {name: [dict(root_id=name, legal_actions=['DOWN', 'LEFT'],
        action_features={'DOWN': [1, 3, 0, 0, 0, 0], 'LEFT': [0, 3, 0, 0, 0, 0]},
        immediate_rewards={'DOWN': 1., 'LEFT': .25})] for name in ('SOURCE', 'TARGET')}
    labels = {name: [dict(root_id=name, action_components={'DOWN': [1., 0., 1.], 'LEFT': [.5, 0., .5]})]
        for name in ('SOURCE', 'TARGET')}
    result = runner.terminal_identities(roots, labels)
    assert result['consistent'] and result['actions'] == 2
    assert result['work'] == dict(cached_goal_feature_reads=4, goal_component_reads=6, goal_identity_comparisons=6)
    labels['TARGET'][0]['action_components']['DOWN'] = [1.25, 0., 1.]
    failed = runner.terminal_identities(roots, labels)
    assert not failed['consistent']
    assert [row['root_id'] for row in failed['records'] if not row['consistent']] == ['TARGET']
    labels['TARGET'][0]['action_components']['DOWN'] = [1., .1, .9]
    assert not runner.terminal_identities(roots, labels)['consistent']


def test_certificate_flow_distinguishes_missing_information_from_linear_restriction():
    # Opposite edges on identical feature vertices cancel any shared function.
    classes = [dict(representative=action, features=[feature, 0, 0, 0, 0, 0])
        for action, feature in [('DOWN', 0), ('LEFT', 1), ('RIGHT', 2)]]
    problem = dict(roots=[dict(root_id='a', classes=classes), dict(root_id='b', classes=classes)])
    constraints = [dict(kind='ranking', root_id='a', best_action='DOWN', bad_action='LEFT'),
        dict(kind='ranking', root_id='b', best_action='LEFT', bad_action='DOWN')]
    capacity = dict(status='no_positive_margin', nodes=[dict(node_id=0, disposition='pruned_zero',
        constraints=constraints, dual=dict(support=[dict(constraint_index=i, weight='1/2') for i in range(2)]))])
    first = runner.interpret_certificates({'SOURCE': problem}, {'SOURCE': capacity})
    assert first['scopes']['SOURCE']['all_terminal_bounds_apply_to_any_shared_function']
    assert first['scopes']['SOURCE']['nodes'][0]['feature_flow'] == []
    # Equal and opposite coordinate differences alone do not cancel arbitrary functions.
    constraints[1].update(best_action='RIGHT', bad_action='LEFT')
    second = runner.interpret_certificates({'SOURCE': problem}, {'SOURCE': capacity})
    assert not second['scopes']['SOURCE']['all_terminal_bounds_apply_to_any_shared_function']
    assert [row['weight'] for row in second['scopes']['SOURCE']['nodes'][0]['feature_flow']] == ['-1/2', '1', '-1/2']
