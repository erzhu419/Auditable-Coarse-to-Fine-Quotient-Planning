"""Five synthetic transfer witnesses; no real JSON, model fit or physics."""
from collections import Counter
from copy import deepcopy
import math

import pytest

from scripts import analyze_controlled_predictive_kernel_transfer_v193 as audit


def vector(aggregate, node=0.):
    values = [0.]*98; values[0], values[6] = float(aggregate), float(node); return values


def sources(positions):
    roots, centers, groups = [], [], {}
    for index, pair in enumerate(positions):
        root_id, source_id = f's{index}', f'group{index}'
        features = {action: vector(*values) for action, values in zip(('DOWN', 'LEFT'), pair, strict=True)}
        root = dict(root_id=root_id, source_id=source_id, legal_actions=['DOWN', 'LEFT'], relation_features=features,
            immediate_rewards=dict(DOWN=0., LEFT=0.), action_components=dict(DOWN=[0., 0., 1.], LEFT=[0., 0., 0.]))
        roots.append(root); groups[root_id] = []
        for action in ('DOWN', 'LEFT'):
            groups[root_id].append(len(centers)); centers.append(dict(root_id=root_id, source_id=source_id, action=action, features=features[action]))
    return roots, centers, groups


def fixture():
    source, centers, _ = sources([[(0., 0.), (10., 0.)], [(1., 0.), (11., 0.)]])
    model = dict(centers=centers, coefficients=[[0., .2, .4], [0., 0., 0.], [0., 0., 0.], [0., 0., 0.]],
        gamma=1., median_squared_distance=1., constants=dict(lambda_value=.001, columns=98))
    targets, choices, labels, previous = [], [], [], []
    specifications = [('error', dict(DOWN=0., LEFT=10.), dict(DOWN=.125, LEFT=0.),
            dict(DOWN=[.125, 0., 0.], LEFT=[0., 0., 1.]), 'LEFT', 'LEFT'),
        ('good', dict(DOWN=0., LEFT=0.), dict(DOWN=0., LEFT=audit.EPS/2),
            dict(DOWN=[0., 0., 1.], LEFT=[audit.EPS/2, 0., 0.]), 'DOWN', 'LEFT'),
        ('forced', dict(DOWN=5.), dict(DOWN=0.), dict(DOWN=[0., 0., .5]), 'DOWN', 'DOWN')]
    for index, (name, positions, rewards, truth, oracle, linear) in enumerate(specifications):
        root = dict(root_id=name, source_id='target', replica=0, stratum=index, legal_actions=list(positions),
            relation_features={a: vector(value) for a, value in positions.items()}, immediate_rewards=rewards, fallback_action='DOWN')
        predictions = {a: [rewards[a], .2*math.exp(-value**2), .4*math.exp(-value**2)] for a, value in positions.items()}
        targets.append(root); choices.append(dict(root_id=name, canonical_action='DOWN', fallback=False,
            decision=dict(predicted_components=predictions)))
        labels.append(dict(root_id=name, action_components=truth))
        previous.append(dict(root_id=name, models=dict(NONLINEAR=dict(action='DOWN'), ORACLE=dict(action=oracle), LINEAR=dict(action=linear))))
    source_diagnostics = dict(root_records=[dict(root_id=root['root_id'], action='DOWN', decision=dict(canonical_action='DOWN'),
        components=root['action_components']['DOWN'], utility=1.) for root in source])
    summary = dict(root_records=previous, comparisons={'NONLINEAR_MINUS_'+name: dict(utility=0.) for name in ('LINEAR', 'RELATION', 'OLD_SHARED')})
    return model, dict(SOURCE=source, TARGET=targets), dict(NONLINEAR=choices), labels, summary, source_diagnostics


def test_same_source_group_is_excluded_and_joint_pair_cannot_mix_source_roots():
    roots, centers, groups = sources([[(0., 0.), (10., 0.)], [(1., 0.), (11., 0.)]])
    counts = Counter(); cache = audit.distance_cache(roots[0], centers, 'source', counts)
    coverage = audit.pair_coverage(cache, ['DOWN', 'LEFT'], centers, groups, 1., 'group0', counts)
    assert coverage['joint_distance'] == 1.
    assert all(row['source_id'] == 'group1' for row in coverage['independent_nearest_centers'])
    _, centers, groups = sources([[(0., 0.), (100., 0.)], [(100., 0.), (10., 0.)]])
    cache = audit.distance_cache(roots[0], centers, 'target', counts)
    coverage = audit.pair_coverage(cache, ['DOWN', 'LEFT'], centers, groups, 1., None, counts)
    assert coverage['independent_distance'] == 0. and coverage['joint_distance'] == 4050.
    assert len({row['root_id'] for row in coverage['nearest_source_pair']}) == 1


def test_block_minima_separate_composition_and_nearest_rank_flags():
    scale = math.sqrt(2.)
    _, centers, groups = sources([[(0., scale), (2., 2.+scale)], [(scale, 0.), (2.+scale, 2.)]])
    query = dict(legal_actions=['DOWN', 'LEFT'], relation_features=dict(DOWN=vector(0., 0.), LEFT=vector(2., 2.)))
    counts = Counter(); cache = audit.distance_cache(query, centers, 'target', counts)
    coverage = audit.pair_coverage(cache, ['DOWN', 'LEFT'], centers, groups, 1., None, counts)
    assert coverage['joint_distance'] == pytest.approx(2.) and sum(coverage['block_min_distances'].values()) == 0.
    assert sum(coverage['joint_block_distances'].values()) == pytest.approx(coverage['joint_distance'])
    values = dict(independent_distance=1., max_individual_distance=2., joint_distance=1., coupling_excess=0., block_coupling_excess=1.)
    reference = dict(records=[dict(**values, block_min_distances={name: 0. for name, _, _ in audit.BLOCKS})],
        metrics={name: audit.quantiles([value]) for name, value in values.items()},
        block_metrics={name: audit.quantiles([0.]) for name, _, _ in audit.BLOCKS})
    audit.add_reference(coverage, reference, counts)
    assert coverage['pair_outlier'] and coverage['composition_outlier'] and coverage['block_composition_outlier']
    assert not coverage['endpoint_outlier'] and audit.quantiles([0., 1., 2., 3.])['q50'] == 1.


def test_full_cohort_forced_roots_reward_risk_sign_EPS_and_label_conflict():
    result = audit.reconstruct(*fixture()); error, good, forced = result['root_records']
    assert error['prediction_vectors']['DOWN'][0] == .125
    assert error['predicted_gap']['utility'] == pytest.approx(-.325)
    assert error['contributions']['negative_utility_mass'] == pytest.approx(-.2)
    assert error['label_direction_reversed'] and error['exact_pair_label_conflict']
    assert good['replayed_action'] == 'DOWN' and good['prediction_vectors']['LEFT'][0] == audit.EPS/2
    assert forced['pair_kind'] == 'forced' and forced['coverage'] is None and forced['true_gap'] is None
    assert result['summary']['groups']['ALL']['n'] == 3 and result['summary']['groups']['ALL']['pair_roots'] == 2
    assert result['summary']['new_error_ids'] == ['error'] and result['summary']['resolved_error_ids'] == ['good']
    assert result['costs']['source_model_predictions'] == 0
    assert all(row['passed'] for row in audit.verify_reconstruction(result, result))


def test_saved_contribution_or_classification_tampering_is_rejected():
    expected = audit.reconstruct(*fixture()); changed = deepcopy(expected)
    changed['root_records'][0]['contributions']['groups'][0]['components'][2] += .1
    assert not all(row['passed'] for row in audit.verify_reconstruction(changed, expected))
    changed = deepcopy(expected); changed['root_records'][0]['coverage']['pair_outlier'] = True
    assert not all(row['passed'] for row in audit.verify_reconstruction(changed, expected))


def test_wrong_saved_choice_cannot_pass_by_matching_a_common_false_replay():
    arguments = list(fixture()); arguments[2]['NONLINEAR'][0]['canonical_action'] = 'LEFT'
    result = audit.reconstruct(*arguments)
    assert not result['root_records'][0]['replay_matches']
    checks = audit.verify_reconstruction(result, result)
    assert any(row['name'] == 'actual_retained_action_prediction_and_contribution_bindings' and not row['passed'] for row in checks)
