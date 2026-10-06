"""Synthetic rank conditioning, convex pair transfer and SOURCE selection."""
from collections import Counter
from copy import deepcopy
from math import sqrt

import pytest

from acfqp.science import controlled_predictive_conditional_pairs_v194 as core


def feature(value, columns=98):
    return [float(value)]+[0.]*(columns-1)


def root(root_id='fixture', source=0, first=1., second=0.):
    return dict(root_id=root_id, source_id=f'DESIGN_SOURCE:{source:02d}', life=0,
        canonical_board=[0]*16, legal_actions=['DOWN', 'LEFT'],
        immediate_rewards=dict(DOWN=0., LEFT=0.), fallback_action='LEFT',
        action_map=dict(DOWN='UP', LEFT='RIGHT', RIGHT='LEFT', UP='DOWN'),
        relation_features=dict(DOWN=feature(first), LEFT=feature(second)),
        conditional_features=dict(DOWN=feature(first, 224), LEFT=feature(second, 224)),
        action_components=dict(DOWN=[1., .2, .3], LEFT=[0., .5, .5]))


def library(rows, mode='PAIR98', k=1, temperature=.01):
    design = core.prepare_design(rows, mode)
    return design, core._model(design, k, temperature)


def examples():
    return [root(f'fixture:{source:02d}:{index}', source)
            for source in range(36) for index in range(3 if source == 3 else 4)]


def test_conditional_projection_separates_five_rank_bins_and_caches_once():
    board = [1, 7, 7, 8, 8, 9, 9, 10, 10, 11, 11, 0, 0, 0, 0, 0]
    record = dict(aggregate=[1., 2., 3., 4., 5., 6.], tokens=[['cell', index, rank] for index, rank in enumerate(board)])
    observed = dict(legal_actions=['DOWN'], layout_features={'DOWN': record})
    counts = core.cache_roots([observed])
    vector = observed['conditional_features']['DOWN']
    assert len(vector) == len(core.FEATURE_NAMES) == 224
    assert vector[:6] == record['aggregate']
    assert [vector[6+42*index] for index in range(5)] == [.75, .5, .5, .5, .5]
    assert vector[6+9] == pytest.approx(1./sqrt(120.))
    assert counts['conditional_feature_vectors_computed'] == 1
    assert counts['conditional_node_moment_accumulations'] == 11*9
    assert counts['conditional_rank_bin_assignments'] == 16
    before = deepcopy(vector)
    cached = core.cache_roots([observed])
    assert observed['conditional_features']['DOWN'] == before
    assert cached['conditional_feature_cache_hits'] == 1
    assert cached.get('conditional_feature_vectors_computed', 0) == 0


def test_complete_same_root_ordered_tails_root_mass_and_forced_centers():
    first, second, forced = root('a'), root('b', 1), root('c', 2, first=10.)
    first['legal_actions'].append('UP')
    first['relation_features']['UP'] = feature(0.)
    first['conditional_features']['UP'] = feature(0., 224)
    first['immediate_rewards'] = dict(DOWN=.5, LEFT=.2, UP=.3)
    first['action_components'] = dict(DOWN=[1.5, .2, .3], LEFT=[.2, .5, .5], UP=[.3, .5, .5])
    forced['legal_actions'] = ['DOWN']; forced['action_components'] = {'DOWN': [1., .2, .3]}
    forced['fallback_action'] = 'DOWN'
    before = deepcopy([first, second, forced])
    design = core.prepare_design([first, second, forced, dict(life=1)], 'PAIR98')
    assert [first, second, forced] == before
    assert len(design['centers']) == 6 and len(design['prototypes']) == 8
    assert design['root_ids'] == ['a', 'b', 'c']
    for root_id in ('a', 'b'):
        records = [row for row in design['prototypes'] if row['root_id'] == root_id]
        assert sum(row['root_mass'] for row in records) == pytest.approx(1.)
        for record in records:
            a, b = record['center_indices']
            assert design['centers'][a]['root_id'] == design['centers'][b]['root_id'] == root_id
            reverse = next(row for row in records if row['actions'] == record['actions'][::-1])
            assert reverse['tail_difference'] == pytest.approx([-value for value in record['tail_difference']])
    forward = next(row for row in design['prototypes'] if row['root_id'] == 'a' and row['actions'] == ['DOWN', 'LEFT'])
    assert forward['tail_difference'] == pytest.approx([1., -.3, -.2])
    assert not any(row['root_id'] == 'c' for row in design['prototypes'])
    distances = sorted(sum((a-b)**2 for a, b in zip(first['features'], second['features'], strict=True))
        for index, first in enumerate(design['centers']) for second in design['centers'][index+1:]
        if first['features'] != second['features'])
    n = len(distances)
    expected = distances[n//2] if n % 2 else (distances[n//2-1]+distances[n//2])/2
    assert design['median_squared_distance'] == expected


def test_nonnegative_weights_include_root_mass_and_reward_once():
    first, second = root('a'), root('b', 1)
    second['legal_actions'].append('UP')
    second['relation_features']['UP'] = feature(0.)
    second['immediate_rewards']['UP'] = 0.
    second['action_components']['DOWN'] = [3., .8, .9]
    second['action_components']['UP'] = second['action_components']['LEFT'].copy()
    design, model = library([first, second], k=8)
    observed = root('query', 2)
    observed['immediate_rewards'] = dict(DOWN=.7, LEFT=.2)
    observed['action_components'] = {'forbidden': 'query labels must never be read'}
    decision = core.choose_action(model, core._observable(observed))
    pair = decision['estimated_pairs']['DOWN|LEFT']
    neighbors = pair['neighbors']
    assert all(row['raw_weight'] >= 0. and row['weight'] >= 0. for row in neighbors)
    assert sum(row['weight'] for row in neighbors) == pytest.approx(1.)
    tied = [row for row in neighbors if row['distance'] == 0.]
    assert len(tied) == 3 and tied[0]['weight']/tied[1]['weight'] == pytest.approx(3.)
    expected = [sum(row['weight']*design['prototypes'][row['prototype_index']]['tail_difference'][i]
                    for row in neighbors) for i in range(3)]
    assert pair['estimated_tail_delta'] == pytest.approx(expected)
    for i in range(3):
        values = [design['prototypes'][row['prototype_index']]['tail_difference'][i] for row in neighbors]
        assert min(values)-1e-12 <= expected[i] <= max(values)+1e-12
    assert decision['predicted_pairs']['DOWN|LEFT'][0] == pytest.approx(.5+expected[0])
    assert decision['predicted_pairs']['DOWN|LEFT'][1:] == pytest.approx(expected[1:])
    assert decision['projection_residual_sse'] == pytest.approx(0.)
    assert decision['work']['pair_reward_additions'] == 2


def test_complete_graph_projection_removes_cycle_and_records_residual():
    a, b, c = root('a', 0, 0., 1.), root('b', 1, 1., 2.), root('c', 2, 0., 2.)
    a['action_components'] = b['action_components'] = dict(DOWN=[1., 0., 0.], LEFT=[0., 0., 0.])
    c['action_components'] = dict(DOWN=[0., 0., 0.], LEFT=[1., 0., 0.])
    _, model = library([a, b, c])
    observed = root('query', 3, 0., 1.)
    observed['legal_actions'].append('UP'); observed['relation_features']['UP'] = feature(2.)
    observed['immediate_rewards']['UP'] = 0.
    decision = core.choose_action(model, core._observable(observed))
    pairs = decision['estimated_pairs']
    assert pairs['DOWN|LEFT']['estimated_tail_delta'] == [1., 0., 0.]
    assert pairs['DOWN|UP']['estimated_tail_delta'] == [-1., 0., 0.]
    assert pairs['LEFT|UP']['estimated_tail_delta'] == [1., 0., 0.]
    assert all(vector == [0., 0., 0.] for vector in decision['tail_offsets'].values())
    assert all(row['projected_tail_delta'] == [0., 0., 0.] for row in pairs.values())
    assert decision['projection_residual_sse'] == 3. and decision['projection_residual_max'] == 1.
    assert decision['canonical_action'] == 'DOWN' and not decision['fallback']


def test_forced_actions_and_epsilon_ties_use_canonical_order():
    _, model = library([root('a')], k=8)
    observed = root('query', first=0., second=0.)
    observed['legal_actions'] = ['LEFT', 'DOWN']
    observed['immediate_rewards'] = dict(DOWN=0., LEFT=core.EPSILON/2)
    decision = core.choose_action(model, core._observable(observed))
    assert decision['canonical_action'] == 'DOWN'
    observed['immediate_rewards']['LEFT'] = 2*core.EPSILON
    assert core.choose_action(model, core._observable(observed))['canonical_action'] == 'LEFT'
    observed['legal_actions'] = ['DOWN']; observed['fallback_action'] = 'DOWN'
    observed['immediate_rewards']['DOWN'] = .9
    forced = core.choose_action(model, core._observable(observed))
    assert forced['canonical_action'] == 'DOWN' and forced['actual_action'] == 'UP'
    assert forced['predicted_components']['DOWN'] == [.9, 0., 0.]
    assert forced['estimated_pairs'] == forced['predicted_pairs'] == {}
    assert forced['projection_residual_sse'] == forced['projection_residual_max'] == 0.


def test_conditional_library_uses_224_cache_and_no_rank_projection_at_choice():
    observed = root('a')
    design, model = library([observed], mode='CONDITIONAL')
    counts = Counter()
    decision = core.choose_action(model, core._observable(root('query')), counts)
    assert model['constants']['columns'] == len(model['feature_names']) == 224
    assert all(len(row['features']) == 224 for row in design['centers'])
    assert counts['pair_query_distance_component_squares'] == 224*4
    assert counts.get('conditional_feature_vectors_computed', 0) == 0
    assert decision['estimated_pairs']['DOWN|LEFT']['estimated_tail_delta'] == pytest.approx([1., -.3, -.2])


def test_source_actual_equal_group_selection_reuses_geometry_and_strips_labels(monkeypatch):
    rows = examples()
    for observed in rows:
        last = 2 if observed['source_id'].endswith(':03') else 3
        good = observed['root_id'].endswith(':'+str(last))
        observed['immediate_rewards'] = dict(DOWN=0., LEFT=0. if good else .5)
        observed['action_components'] = dict(DOWN=[2. if good else .2, 0., 0.],
            LEFT=[observed['immediate_rewards']['LEFT'], 0., 0.])
        observed.update(oracle_action='UP', teacher_action_native='UP')
    before, calls = deepcopy(rows), Counter()
    deciding = core._decision
    def label_free(model, observed, geometry, counts):
        assert not {'action_components', 'oracle_action', 'teacher_action_native'} & set(observed)
        calls['decisions'] += 1
        return deciding(model, observed, geometry, counts)
    monkeypatch.setattr(core, '_decision', label_free)
    result = core.fit_model(rows+[dict(life=1)], 'PAIR98')
    assert rows == before and calls['decisions'] == 9*143
    selection, model, costs = result['selection'], result['model'], result['costs']
    assert selection['selected_k'] == 1 and selection['selected_temperature'] == .01
    assert selection['selected_utility'] == pytest.approx((35*.875+1.)/36)
    assert selection['candidates'][3]['utility'] == pytest.approx((35*.65+.8)/36)
    assert len(selection['source_folds'][0]) == len(selection['source_folds'][1]) == 18
    assert costs['pair_geometry_preparations'] == 143
    assert costs['pair_design_preparations'] == 3
    assert costs['new_predictors_fitted'] == costs['pair_predictor_configurations'] == 19
    assert costs['pair_heldout_action_vector_reads'] == 9*143
    assert costs['new_linear_solves'] == costs['new_eigen_decompositions'] == costs['new_svd_decompositions'] == 0
    assert model['source_root_counts']['DESIGN_SOURCE:03'] == 3
    for fold in selection['folds']:
        assert set(fold['train_sources']).isdisjoint(fold['heldout_sources'])
        assert fold['design']['source_ids'] == fold['train_sources']
    for candidate in selection['candidates']:
        for fold in candidate['fold_results']:
            assert 'model' not in fold and 'design' not in fold
            assert all(set(choice) == {'root_id', 'source_id', 'canonical_action', 'components', 'utility'} for choice in fold['choices'])


def test_final_library_failure_retains_eighteen_paid_configurations(monkeypatch):
    median, attempts = core._median, []
    def fail_full(values):
        attempts.append(1)
        if len(attempts) == 3:
            raise ArithmeticError('synthetic selected-full-library median failure')
        return median(values)
    def cheap_heldout(model, rows, geometries, counts):
        return [dict(source_id=source, roots=sum(row['source_id'] == source for row in rows),
                     components=[1., 0., 0.], utility=1.) for source in sorted({row['source_id'] for row in rows})], []
    monkeypatch.setattr(core, '_median', fail_full)
    monkeypatch.setattr(core, '_heldout', cheap_heldout)
    with pytest.raises(core.PairExecutionError) as raised:
        core.fit_model(examples(), 'PAIR98')
    record = raised.value.record
    assert record['operation'] == 'PAIR98:source_selection'
    assert record['costs']['pair_design_attempts'] == record['costs']['pair_median_attempts'] == 3
    assert record['costs']['pair_design_preparations'] == record['costs']['pair_median_computations'] == 2
    assert record['costs']['pair_predictor_configurations'] == record['costs']['new_predictors_fitted'] == 18
    assert record['costs']['pair_train_center_distance_pairs'] > 286*285//2
    assert record['costs']['new_linear_solves'] == 0
