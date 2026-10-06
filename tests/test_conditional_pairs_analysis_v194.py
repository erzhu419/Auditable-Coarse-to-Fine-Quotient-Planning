"""Independent synthetic certificates for conditional action-pair transfer."""
from collections import Counter
from copy import deepcopy
from math import sqrt

import pytest

from scripts import analyze_controlled_predictive_conditional_pairs_v194 as audit


def feature(value, columns=98):
    return [float(value)]+[0.]*(columns-1)


def root(root_id='query', source=0, first=1., second=0.):
    return dict(root_id=root_id, source_id=f'DESIGN_SOURCE:{source:02d}', life=0,
        canonical_board=[0]*16, legal_actions=['DOWN', 'LEFT'], immediate_rewards=dict(DOWN=0., LEFT=0.),
        fallback_action='LEFT', action_map=dict(DOWN='UP', LEFT='RIGHT', RIGHT='LEFT', UP='DOWN'),
        relation_features=dict(DOWN=feature(first), LEFT=feature(second)),
        conditional_features=dict(DOWN=feature(first, 224), LEFT=feature(second, 224)),
        action_components=dict(DOWN=[1., .2, .3], LEFT=[0., .5, .5]))


def library(rows, mode='PAIR98', k=1, temperature=.01):
    design = audit.prepare_design(rows, mode)
    return design, audit.model_from_design(design, k, temperature)


def test_independent_conditional_bins_boundaries_and_once_cached_projection():
    board = [7, 7, 8, 8, 9, 9, 10, 10, 11, 11, 0, 0, 0, 0, 0, 0]
    layout = dict(aggregate=[1., 2., 3., 4., 5., 6.], tokens=[['cell', i, value] for i, value in enumerate(board)])
    observed = dict(legal_actions=['DOWN'], layout_features={'DOWN': layout})
    paid = audit.cache_roots([observed]); vector = observed['conditional_features']['DOWN']
    assert len(vector) == len(audit.FEATURE_NAMES) == 224
    assert vector[:6] == layout['aggregate']
    assert [vector[6+42*i] for i in range(5)] == [.5]*5
    assert vector[6+9] == pytest.approx(1./sqrt(120.))
    assert paid['conditional_node_moment_accumulations'] == 10*9
    assert paid['conditional_rank_bin_assignments'] == 15
    again = audit.cache_roots([observed])
    assert observed['conditional_features']['DOWN'] == vector
    assert again == dict(conditional_feature_cache_hits=1, conditional_cached_feature_reads=224)


def test_independent_ordered_prototypes_training_median_and_native_metadata():
    first, second, forced = root('a'), root('b', 1), root('c', 2, first=10.)
    first['legal_actions'].append('UP'); first['relation_features']['UP'] = feature(2.)
    first['immediate_rewards'] = dict(DOWN=.5, LEFT=.2, UP=.3)
    first['action_components'] = dict(DOWN=[1.5, .2, .3], LEFT=[.2, .5, .5], UP=[.3, .5, .5])
    forced['legal_actions'] = ['DOWN']; forced['fallback_action'] = 'DOWN'
    design, model = library([first, second, forced])
    assert len(design['centers']) == 6 and len(design['prototypes']) == 8
    assert design['root_ids'] == ['a', 'b', 'c']
    assert 'training_outcomes' not in design and 'training_outcomes' not in model
    assert model['native_teacher_query'] == 'goal_1_risk_1' and model['horizon'] == 3
    for name in ('a', 'b'):
        pairs = [pair for pair in design['prototypes'] if pair['root_id'] == name]
        assert sum(pair['root_mass'] for pair in pairs) == pytest.approx(1.)
        for pair in pairs:
            a, b = pair['center_indices']
            assert design['centers'][a]['root_id'] == design['centers'][b]['root_id'] == name
            reverse = next(other for other in pairs if other['actions'] == pair['actions'][::-1])
            assert reverse['tail_difference'] == pytest.approx([-x for x in pair['tail_difference']])
    forward = next(pair for pair in design['prototypes'] if pair['root_id'] == 'a' and pair['actions'] == ['DOWN', 'LEFT'])
    assert forward['tail_difference'] == pytest.approx([1., -.3, -.2])
    assert not any(pair['root_id'] == 'c' for pair in design['prototypes'])
    values = sorted((a['features'][0]-b['features'][0])**2 for index, a in enumerate(design['centers'])
        for b in design['centers'][index+1:] if a['features'][0] != b['features'][0])
    n = len(values); expected = values[n//2] if n % 2 else (values[n//2-1]+values[n//2])/2
    assert design['median_squared_distance'] == expected
    observed = root(first=1000., second=-1000.)
    audit.choose_action(model, audit.observable(observed))
    assert model['median_squared_distance'] == expected


def test_query_labels_excluded_nonnegative_root_mass_and_reward_once():
    first, second = root('a'), root('b', 1)
    second['legal_actions'].append('UP'); second['relation_features']['UP'] = feature(0.)
    second['immediate_rewards']['UP'] = 0.; second['action_components']['UP'] = second['action_components']['LEFT'].copy()
    second['action_components']['DOWN'] = [3., .8, .9]
    design, model = library([first, second], k=8)
    observed = root(); observed['immediate_rewards'] = dict(DOWN=.7, LEFT=.2)
    observed['action_components'] = {'forbidden': 'query labels cannot be read'}
    seen = audit.observable(observed)
    assert 'action_components' not in seen
    decision = audit.choose_action(model, seen); pair = decision['estimated_pairs']['DOWN|LEFT']
    assert audit.weights_valid(decision)
    neighbors = pair['neighbors']; tied = [row for row in neighbors if row['distance'] == 0.]
    assert len(tied) == 3 and tied[0]['weight']/tied[1]['weight'] == pytest.approx(3.)
    expected = [sum(row['weight']*design['prototypes'][row['prototype_index']]['tail_difference'][k] for row in neighbors) for k in range(3)]
    assert pair['estimated_tail_delta'] == pytest.approx(expected)
    for k in range(3):
        raw = [design['prototypes'][row['prototype_index']]['tail_difference'][k] for row in neighbors]
        assert min(raw)-1e-12 <= expected[k] <= max(raw)+1e-12
    assert decision['predicted_pairs']['DOWN|LEFT'] == pytest.approx([.5+expected[0], *expected[1:]])
    assert decision['projection_residual_sse'] == pytest.approx(0.)
    assert decision['work']['pair_reward_additions'] == 2


def test_closed_form_three_component_projection_and_sign_flip_summary():
    observed = root(); observed['legal_actions'] = ['DOWN', 'LEFT', 'UP']; observed['immediate_rewards']['UP'] = 0.
    model = dict(k=1, temperature=.01, prototypes=[dict(root_mass=.5, tail_difference=[value, .2*value, .1*value]) for value in (1., -3., 3.)])
    view = dict(legal_actions=observed['legal_actions'], sorted_pairs={'DOWN|LEFT': [(0., 0)], 'DOWN|UP': [(0., 1)], 'LEFT|UP': [(0., 2)]})
    counts = Counter(); decision = audit.decision_from_geometry(model, audit.observable(observed), view, counts)
    assert decision['canonical_action'] == 'LEFT'
    assert decision['tail_offsets']['DOWN'] == pytest.approx([-2./3, -.4/3, -.2/3])
    assert decision['tail_offsets']['LEFT'] == pytest.approx([2./3, .4/3, .2/3])
    for k in range(3):
        assert sum(row[k] for row in decision['tail_offsets'].values()) == pytest.approx(0.)
    residual = decision['estimated_pairs']['DOWN|LEFT']['projection_residual']
    assert residual == pytest.approx([7./3, 1.4/3, .7/3])
    assert decision['projection_residual_sse'] == pytest.approx((49./3)*(1.+.04+.01))
    metrics = audit.projection_metrics([dict(decision=decision)])
    assert set(metrics) == {'roots', 'pairs', 'max_abs_components', 'mean_abs_components', 'utility_sign_flips'}
    assert metrics['roots'] == 1 and metrics['pairs'] == 3 and metrics['utility_sign_flips'] == 1
    assert metrics['max_abs_components'] == pytest.approx(residual)
    assert metrics['mean_abs_components'] == pytest.approx(residual)
    assert counts['pair_projection_divisions'] == 18 and counts['pair_projection_residual_squares'] == 9


def test_forced_action_epsilon_order_and_conditional_cache_only():
    _, model = library([root('a')], mode='CONDITIONAL', k=8)
    observed = root(first=0., second=0.); observed['legal_actions'] = ['LEFT', 'DOWN']
    observed['immediate_rewards'] = dict(DOWN=0., LEFT=audit.EPS/2)
    decision = audit.choose_action(model, audit.observable(observed))
    assert decision['canonical_action'] == 'DOWN'
    observed['immediate_rewards']['LEFT'] = 2*audit.EPS
    assert audit.choose_action(model, audit.observable(observed))['canonical_action'] == 'LEFT'
    observed['legal_actions'] = ['DOWN']; observed['immediate_rewards']['DOWN'] = .9
    forced = audit.choose_action(model, audit.observable(observed))
    assert forced['canonical_action'] == 'DOWN' and forced['actual_action'] == 'UP'
    assert forced['predicted_components']['DOWN'] == [.9, 0., 0.] and forced['tail_offsets']['DOWN'] == [0., 0., 0.]
    assert forced['estimated_pairs'] == forced['predicted_pairs'] == {} and not forced['fallback']
    assert forced['work']['pair_feature_value_reads'] == 224
    assert forced['work'].get('conditional_feature_vectors_computed', 0) == 0


def test_actual_group_selection_reuses_geometry_and_SOURCE_compaction(monkeypatch):
    rows = [root(f'fixture:{source:02d}:{index}', source) for source in range(4) for index in range(3 if source == 3 else 4)]
    for observed in rows:
        last = 2 if observed['source_id'].endswith(':03') else 3
        good = observed['root_id'].endswith(':'+str(last))
        observed['immediate_rewards'] = dict(DOWN=0., LEFT=0. if good else .5)
        observed['action_components'] = dict(DOWN=[2. if good else .2, 0., 0.], LEFT=[observed['immediate_rewards']['LEFT'], 0., 0.])
        observed.update(oracle_action='UP', teacher_action_native='UP')
    deciding, calls = audit.decision_from_geometry, Counter()
    def label_free(model, observed, view, counts):
        assert not {'action_components', 'oracle_action', 'teacher_action_native'} & set(observed)
        calls['choices'] += 1
        return deciding(model, observed, view, counts)
    monkeypatch.setattr(audit, 'decision_from_geometry', label_free)
    result = audit.rebuild_model(rows, 'PAIR98'); selection, counts = result['selection'], result['costs']
    assert selection['selected_k'] == 1 and selection['selected_temperature'] == .01
    assert selection['selected_utility'] == pytest.approx((3*.875+1.)/4)
    assert selection['candidates'][3]['utility'] == pytest.approx((3*.65+.8)/4)
    assert calls['choices'] == 9*15 and counts['pair_geometry_preparations'] == 15
    assert counts['pair_design_preparations'] == 3 and counts['new_predictors_fitted'] == counts['pair_predictor_configurations'] == 19
    assert counts['new_linear_solves'] == counts['new_eigen_decompositions'] == counts['new_svd_decompositions'] == 0
    for fold in selection['folds']:
        assert set(fold['train_sources']).isdisjoint(fold['heldout_sources'])
    actual = audit.source_diagnostics(rows, result['model'])
    assert actual['metrics']['roots'] == 15
    assert all('neighbors' not in pair for row in actual['root_records'] for pair in row['decision']['estimated_pairs'].values())
    assert actual['projection_residuals']['pairs'] == 15
    assert actual['work']['pair_neighbor_exponentials'] == 15


def test_certificate_rejects_tiny_negative_weights_and_wrong_action():
    _, model = library([root('a')], k=8); decision = audit.choose_action(model, audit.observable(root()))
    assert audit.verify_decision(deepcopy(decision), decision)
    tampered = deepcopy(decision); tampered['estimated_pairs']['DOWN|LEFT']['neighbors'][1]['weight'] = -1e-12
    assert audit.close(tampered, decision)
    assert not audit.verify_decision(tampered, decision)
    # A tiny negative raw weight also fails despite being inside the float tolerance.
    tampered = deepcopy(decision); tampered['estimated_pairs']['DOWN|LEFT']['neighbors'][1]['raw_weight'] = -1e-12
    assert audit.close(tampered, decision)
    assert not audit.verify_decision(tampered, decision)
    tampered = deepcopy(decision); tampered['canonical_action'] = 'LEFT'
    assert not audit.verify_decision(tampered, decision)
    tampered = deepcopy(decision); tampered['estimated_pairs']['DOWN|LEFT']['projection_residual'][1] += .01
    assert not audit.verify_decision(tampered, decision)
