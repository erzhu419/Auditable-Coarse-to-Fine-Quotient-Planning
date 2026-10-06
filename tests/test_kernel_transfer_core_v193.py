"""Synthetic coverage and contribution witnesses without fitting or labels."""
from copy import deepcopy
from math import exp

import pytest

from acfqp.science import controlled_predictive_kernel_transfer_v193 as core


def feature(first, second=0.):
    vector = [0.]*98
    vector[0], vector[6] = float(first), float(second)
    return vector


def source(root_id, source_id, first, second):
    return dict(root_id=root_id, source_id=source_id, life=0,
        legal_actions=['DOWN', 'LEFT'], immediate_rewards=dict(DOWN=0., LEFT=0.),
        relation_features=dict(DOWN=feature(first), LEFT=feature(second)),
        action_components=dict(DOWN=[1., .2, .3], LEFT=[0., .5, .5]))


def target(root_id='target', first=0., second=1.):
    return dict(root_id=root_id, source_id='FRESH', replica=0, stratum=0, life=0,
        legal_actions=['DOWN', 'LEFT'], immediate_rewards=dict(DOWN=0., LEFT=1.1),
        fallback_action='DOWN', relation_features=dict(DOWN=feature(first), LEFT=feature(second)))


def package(sources=None, targets=None, vectors=None, linear_actions=None, coefficients=None):
    sources = sources or [source('s0', 'SOURCE:A', 0., 1.), source('s1', 'SOURCE:B', 2., 3.)]
    targets = targets or [target()]
    centers = [dict(root_id=row['root_id'], source_id=row['source_id'], action=action,
                    features=row['relation_features'][action])
               for row in sorted(sources, key=lambda row: row['root_id']) for action in core.ACTIONS if action in row['legal_actions']]
    model = dict(gamma=1., median_squared_distance=1., constants=dict(lambda_value=.001),
                 centers=centers, coefficients=coefficients or [[1., .2, .3]]+[[0., 0., 0.] for _ in centers[1:]])
    choices, labels, previous = [], [], []
    for row in targets:
        predictions = {}
        for action in row['legal_actions']:
            kernels = [exp(-sum((row['relation_features'][action][i]-center['features'][i])**2
                                for i in range(98))) for center in centers]
            prediction = [sum(kernels[j]*model['coefficients'][j][i] for j in range(len(centers))) for i in range(3)]
            prediction[0] += row['immediate_rewards'][action]
            predictions[action] = prediction
        selected, best = None, None
        for action in core.ACTIONS:
            if action not in predictions:
                continue
            value = predictions[action][0]-predictions[action][1]+predictions[action][2]
            if best is None or value > best+core.EPSILON:
                selected, best = action, value
        actual = vectors[row['root_id']] if vectors else {a: [2., 0., 0.] if a == 'DOWN' else [0., 0., 0.] for a in row['legal_actions']}
        oracle, best = None, None
        for action in core.ACTIONS:
            if action not in actual:
                continue
            value = actual[action][0]-actual[action][1]+actual[action][2]
            if best is None or value > best+core.EPSILON:
                oracle, best = action, value
        linear = linear_actions[row['root_id']] if linear_actions else oracle
        choices.append(dict(root_id=row['root_id'], canonical_action=selected, fallback=False,
                            decision=dict(predicted_components=predictions)))
        labels.append(dict(root_id=row['root_id'], action_components=actual))
        previous.append(dict(root_id=row['root_id'], models={name: dict(action=action)
            for name, action in (('ORACLE', oracle), ('NONLINEAR', selected), ('LINEAR', linear))}))
    diagnostics = dict(root_records=[dict(root_id=row['root_id'], action='DOWN',
        decision=dict(canonical_action='DOWN'), components=row['action_components']['DOWN'],
        utility=row['action_components']['DOWN'][0]-row['action_components']['DOWN'][1]+row['action_components']['DOWN'][2])
        for row in sources])
    summary = dict(root_records=previous, comparisons={'NONLINEAR_MINUS_'+name: dict(utility=-.1)
                                                       for name in core.PRIMARY})
    return model, dict(SOURCE=sources, TARGET=targets), dict(NONLINEAR=choices), labels, summary, diagnostics


def test_source_reference_excludes_the_entire_source_group():
    sources = [source('s0', 'SOURCE:A', 0., 1.), source('s1', 'SOURCE:A', 0., 1.),
               source('s2', 'SOURCE:B', 10., 11.)]
    result = core.diagnose(*package(sources))
    records = [row for row in result['reference']['records'] if row['source_id'] == 'SOURCE:A']
    assert len(records) == 4 and all(row['joint_distance'] == 100. for row in records)
    assert result['costs']['source_model_predictions'] == 0
    assert result['costs']['source_reference_pairs'] == 6
    assert result['reference']['metrics']['joint_distance'] == dict(n=6, q50=100., q95=100., max=100.)


def test_pair_coverage_cannot_splice_two_different_source_roots():
    sources = [source('s0', 'SOURCE:A', 0., 10.), source('s1', 'SOURCE:B', 10., 1.)]
    result = core.diagnose(*package(sources))
    coverage = result['root_records'][0]['coverage']
    assert coverage['independent_distance'] == 0.
    assert coverage['joint_distance'] == coverage['coupling_excess'] == 40.5
    assert [row['root_id'] for row in coverage['independent_nearest_centers']] == ['s0', 's1']
    assert [row['root_id'] for row in coverage['nearest_source_pair']] == ['s0', 's0']
    assert coverage['pair_outlier'] and coverage['composition_outlier'] and not coverage['endpoint_outlier']
    assert not coverage['block_composition_outlier']
    assert coverage['percentiles']['joint_distance'] == 1.


def test_block_minima_use_different_pairs_but_joint_blocks_share_one_pair():
    sources = [source('s0', 'SOURCE:A', 0., 1.), source('s1', 'SOURCE:B', 10., 11.)]
    sources[0]['relation_features'] = dict(DOWN=feature(0., 10.), LEFT=feature(1., 11.))
    sources[1]['relation_features'] = dict(DOWN=feature(10., 0.), LEFT=feature(11., 1.))
    observed = target()
    observed['relation_features'] = dict(DOWN=feature(0., 0.), LEFT=feature(1., 1.))
    result = core.diagnose(*package(sources, [observed]))
    coverage = result['root_records'][0]['coverage']
    assert coverage['joint_distance'] == 100.
    assert coverage['block_coupling_excess'] == 100.
    assert all(value == 0. for value in coverage['block_min_distances'].values())
    assert coverage['joint_block_distances']['aggregate'] == 0.
    assert coverage['joint_block_distances']['rank_nodes'] == 100.
    assert sum(coverage['joint_block_distances'].values()) == coverage['joint_distance']


def test_contributions_preserve_three_components_risk_sign_and_reward_once():
    observed = target()
    observed['immediate_rewards'] = dict(DOWN=.3, LEFT=.7)
    coefficients = [[1., .8, .1], [-.2, -.1, .4], [.1, .2, -.5], [0., 0., 0.]]
    actual = {'target': dict(DOWN=[1., .9, 0.], LEFT=[.3, 0., .2])}
    inputs = package(targets=[observed], vectors=actual, coefficients=coefficients)
    result = core.diagnose(*inputs)
    record = result['root_records'][0]
    assert record['oracle'] == 'LEFT'
    contributions = record['contributions']
    assert contributions['matches_prediction_gap']
    assert contributions['reconstructed_prediction_gap'] == pytest.approx(record['predicted_gap']['components'])
    assert contributions['reconstructed_prediction_gap'][0] == pytest.approx(contributions['summed_center_components'][0]+record['immediate_gap'])
    assert contributions['reconstructed_prediction_gap'][1:] == pytest.approx(contributions['summed_center_components'][1:])
    assert record['true_gap']['utility'] == pytest.approx(.4)
    for center in contributions['top_centers']:
        vector = center['components']
        assert center['utility'] == pytest.approx(vector[0]-vector[1]+vector[2])
    assert contributions['positive_utility_mass'] >= 0. and contributions['negative_utility_mass'] <= 0.
    assert sum(row['utility'] for row in contributions['groups']) == pytest.approx(core.utility(contributions['summed_center_components']))
    assert result['costs']['target_kernel_exponentials'] == 8
    assert result['costs']['target_contribution_component_products'] == 12


def test_exact_pair_tail_conflict_and_failure_sign_reversal():
    sources = [source('s0', 'SOURCE:A', 0., 1.), source('s1', 'SOURCE:B', 2., 3.)]
    sources[0]['action_components'] = dict(DOWN=[.1, .9, 0.], LEFT=[0., 0., 0.])
    observed = target()
    observed['immediate_rewards'] = dict(DOWN=0., LEFT=0.)
    actual = {'target': dict(DOWN=[0., 0., 1.], LEFT=[0., 0., 0.])}
    result = core.diagnose(*package(sources, [observed], vectors=actual))
    record = result['root_records'][0]
    assert record['true_tail_gap']['utility'] == 1.
    assert record['nearest_source_tail_gap']['utility'] == -.8
    assert record['coverage']['joint_distance'] == 0.
    assert record['label_direction_reversed'] and record['exact_pair_label_conflict']
    observed['relation_features']['DOWN'][0] = 1e-6
    near = core.diagnose(*package(sources, [observed], vectors=actual))['root_records'][0]
    assert near['label_direction_reversed'] and not near['exact_pair_label_conflict']


def test_epsilon_ties_forced_roots_and_complete_target_cohort():
    observed = target('tie')
    observed['immediate_rewards'] = dict(DOWN=0., LEFT=core.EPSILON/2)
    forced = target('forced')
    forced['legal_actions'] = ['DOWN']; forced['relation_features'] = {'DOWN': feature(0.)}
    forced['immediate_rewards'] = dict(DOWN=0.)
    actual = dict(tie=dict(DOWN=[1., 0., 0.], LEFT=[0., 0., 0.]), forced=dict(DOWN=[.5, 0., 0.]))
    result = core.diagnose(*package(targets=[observed, forced], vectors=actual, coefficients=[[0., 0., 0.]]*4))
    assert [row['root_id'] for row in result['root_records']] == ['tie', 'forced']
    assert result['root_records'][0]['replayed_action'] == 'DOWN'
    assert result['root_records'][0]['pair_kind'] == 'oracle_vs_best_other'
    assert result['root_records'][1]['coverage'] is None
    assert result['root_records'][1]['contributions'] is None
    assert result['summary']['groups']['ALL']['n'] == result['summary']['groups']['CORRECT']['n'] == 2
    assert result['summary']['groups']['ALL']['pair_roots'] == 1
    assert result['costs']['target_distance_pairs'] == 12
    assert all(result['costs'][key] == 0 for key in core.ZERO_WORK)
    observed['immediate_rewards']['LEFT'] = 2*core.EPSILON
    changed = core.diagnose(*package(targets=[observed, forced], vectors=actual, coefficients=[[0., 0., 0.]]*4))
    assert changed['root_records'][0]['replayed_action'] == 'LEFT'


def test_wrong_retained_decision_or_prediction_is_reported_by_replay():
    inputs = package()
    result = core.diagnose(*inputs)
    assert result['summary']['replay_matches_all'] and result['summary']['predictions_match_all']
    corrupted = deepcopy(inputs)
    corrupted[2]['NONLINEAR'][0]['canonical_action'] = 'DOWN'
    replay = core.diagnose(*corrupted)
    assert not replay['root_records'][0]['replay_matches']
    assert not replay['summary']['replay_matches_all']
    corrupted = deepcopy(inputs)
    corrupted[2]['NONLINEAR'][0]['decision']['predicted_components']['DOWN'][0] += .01
    predictions = core.diagnose(*corrupted)
    assert not predictions['root_records'][0]['predictions_match']
    assert not predictions['summary']['predictions_match_all']
    assert predictions['summary']['contributions_match_all']
