"""Independent synthetic learned-region, weighting and action certificates."""
from collections import Counter
from copy import deepcopy

import pytest

from scripts import analyze_controlled_predictive_pair_regions_v195 as audit


def cells(value):
    return [value]+[0]*15


def root(name='query', source=0, first=1, second=0):
    raw = dict(DOWN=cells(first), LEFT=cells(second))
    return dict(root_id=name, source_id=f'DESIGN_SOURCE:{source:02d}', life=0, canonical_board=[0]*16,
        legal_actions=['DOWN', 'LEFT'], immediate_rewards=dict(DOWN=0., LEFT=0.), fallback_action='LEFT',
        action_map=dict(DOWN='UP', LEFT='RIGHT', RIGHT='LEFT', UP='DOWN'), raw_afterstates=raw,
        layout_features={action: dict(tokens=[['cell', i, rank] for i, rank in enumerate(values)]) for action, values in raw.items()},
        action_components=dict(DOWN=[1., .2, .3], LEFT=[0., .5, .5]))


def library(rows):
    return audit.prepare_library(rows, 'FULL')


def test_raw_cache_source_equal_mass_and_forced_root_denominator():
    first, second, third, forced = root('a', 0), root('b', 0), root('c', 1), root('d', 1)
    first['immediate_rewards'] = dict(DOWN=.5, LEFT=.2)
    first['action_components'] = dict(DOWN=[1.5, .2, .3], LEFT=[.2, .5, .5])
    forced['legal_actions'] = ['DOWN']; forced['action_components'] = {'DOWN': [1., .2, .3]}
    rows = [first, second, third, forced]
    for row in rows:
        del row['raw_afterstates']
    paid = audit.cache_roots(rows)
    assert paid['raw_afterstate_roots_cached'] == 4 and paid['raw_afterstates_extracted'] == 7
    assert paid['raw_afterstate_cell_tokens'] == 112
    assert audit.cache_roots(rows) == dict(raw_afterstate_cache_hits=4, raw_afterstate_cached_cell_reads=112)
    prepared = library(rows); assert prepared['source_root_counts'] == {'DESIGN_SOURCE:00': 2, 'DESIGN_SOURCE:01': 2}
    masses = {source: sum(pair['root_mass'] for pair in prepared['prototypes'] if pair['source_id'] == source) for source in prepared['source_ids']}
    assert masses == {'DESIGN_SOURCE:00': 1., 'DESIGN_SOURCE:01': .5}
    assert len(prepared['prototypes']) == 6 and all(pair['root_mass'] == .25 for pair in prepared['prototypes'])
    assert prepared['prototypes'][0]['features32'] == cells(1)+cells(0)
    assert prepared['prototypes'][0]['tail_difference'] == pytest.approx([1., -.3, -.2])
    assert prepared['prototypes'][1]['tail_difference'] == pytest.approx([-1., .3, .2])
    assert not any(pair['root_id'] == 'd' for pair in prepared['prototypes'])
    model = audit.model_from_library(prepared, 'RAW32')
    assert model['native_teacher_query'] == 'goal_1_risk_1' and model['horizon'] == 3 and model['constants']['columns'] == 32
    assert model['library_id'] == 'FULL' and 'prototypes' not in model


def test_learned_success_partition_and_overlapping_child_root_support():
    rows = [root(f'goal:{source}:{index}', source, first=9+index) for source in range(4) for index in range(2)]
    for row in rows:
        success = float(row['raw_afterstates']['DOWN'][0] == 10)
        row['action_components'] = dict(DOWN=[0., 0., success], LEFT=[0., 0., 0.])
    prepared = library(rows); tree = audit.build_tree(prepared, 2, 4)
    assert tree['feature'] == 0 and tree['threshold'] == 9
    assert tree['weighted_sse'] == pytest.approx(2.) and tree['improvement'] == pytest.approx(4./3)
    assert tree['right']['mean'] == [0., 0., 1.]
    assert tree['left']['feature'] == 16 and tree['left']['threshold'] == 9
    assert tree['left']['left']['mean'] == [0., 0., 0.] and tree['left']['right']['mean'] == [0., 0., -1.]
    # The same eight roots support both orientations; 2*min_roots pruning would incorrectly reject this split.
    overlap = audit.build_tree(prepared, 1, 8)
    assert overlap['kind'] == 'split' and overlap['feature'] == 0 and overlap['threshold'] == 0
    assert overlap['root_count'] == overlap['left']['root_count'] == overlap['right']['root_count'] == 8
    model = audit.model_from_library(prepared, 'TREE32', max_depth=2, min_leaf_roots=4)
    query = root(first=10); query['action_components'] = {'forbidden': 'query labels must not be read'}
    decision = audit.choose_action(model, audit.observable(query), prepared)
    assert decision['estimated_pairs']['DOWN|LEFT']['estimated_tail_delta'] == [0., 0., 1.]
    assert decision['canonical_action'] == 'DOWN'


def test_two_direction_full_vector_antisymmetry_projection_and_reward_once():
    prepared = library([root('a')]); model = audit.model_from_library(prepared, 'TREE32')
    model['tree'] = dict(kind='split', feature=0, threshold=1,
        left=dict(kind='leaf', node_id=1, mean=[1., 2., 3.]), right=dict(kind='leaf', node_id=2, mean=[.2, 4., -1.]))
    query = root(first=0, second=2); query['immediate_rewards'] = dict(DOWN=.7, LEFT=.2)
    decision = audit.choose_action(model, audit.observable(query), prepared); pair = decision['estimated_pairs']['DOWN|LEFT']
    assert pair['forward'] == dict(components=[1., 2., 3.], leaf_id=1)
    assert pair['reverse'] == dict(components=[.2, 4., -1.], leaf_id=2)
    assert pair['estimated_tail_delta'] == pytest.approx([.4, -1., 2.])
    assert pair['projected_tail_delta'] == pytest.approx([.4, -1., 2.])
    assert decision['predicted_pairs']['DOWN|LEFT'] == pytest.approx([.9, -1., 2.])
    assert decision['projection_residual_sse'] == 0. and decision['canonical_action'] == 'DOWN'
    assert decision['work']['tree_direction_predictions'] == 2 and decision['work']['pair_reward_additions'] == 2
    for k in range(3):
        assert sum(vector[k] for vector in decision['tail_offsets'].values()) == pytest.approx(0.)


def test_RAW_direction_ties_nonnegative_weights_forced_and_epsilon_actions():
    prepared = library([root('a')]); model = audit.model_from_library(prepared, 'RAW32', k=1)
    query = root(first=0, second=0); query['legal_actions'] = ['LEFT', 'DOWN']
    query['immediate_rewards'] = dict(DOWN=0., LEFT=audit.EPS/2)
    query['action_components'] = {'forbidden': 'no labels at inference'}
    decision = audit.choose_action(model, audit.observable(query), prepared); pair = decision['estimated_pairs']['DOWN|LEFT']
    assert pair['forward']['neighbors'][0]['prototype_index'] == pair['reverse']['neighbors'][0]['prototype_index'] == 0
    assert pair['forward']['components'] == pair['reverse']['components']
    assert pair['estimated_tail_delta'] == [0., 0., 0.] and audit.weights_valid(decision)
    assert decision['canonical_action'] == 'DOWN'
    query['immediate_rewards']['LEFT'] = 2*audit.EPS
    assert audit.choose_action(model, audit.observable(query), prepared)['canonical_action'] == 'LEFT'
    query['legal_actions'] = ['DOWN']; query['immediate_rewards']['DOWN'] = .9
    forced = audit.choose_action(model, audit.observable(query), prepared)
    assert forced['canonical_action'] == 'DOWN' and forced['actual_action'] == 'UP'
    assert forced['predicted_components']['DOWN'] == [.9, 0., 0.] and forced['estimated_pairs'] == {}
    assert forced['work'].get('raw_direction_predictions', 0) == 0


def test_source_actual_group_selection_shared_libraries_and_compaction(monkeypatch):
    rows = [root(f'fixture:{source:02d}:{index}', source) for source in range(4) for index in range(3 if source == 3 else 4)]
    for row in rows:
        last = 2 if row['source_id'].endswith(':03') else 3; good = row['root_id'].endswith(':'+str(last))
        row['immediate_rewards'] = dict(DOWN=0., LEFT=0. if good else .5)
        row['action_components'] = dict(DOWN=[2. if good else .2, 0., 0.], LEFT=[row['immediate_rewards']['LEFT'], 0., 0.])
        row.update(teacher_action_native='UP', oracle_action='UP')
    deciding, calls = audit.decision_from_query, Counter()
    def label_free(model, observed, prepared, query, counts):
        assert not {'action_components', 'teacher_action_native', 'oracle_action'} & set(observed)
        calls['decisions'] += 1
        return deciding(model, observed, prepared, query, counts)
    monkeypatch.setattr(audit, 'decision_from_query', label_free)
    result = audit.fit_models(rows); selections, counts = result['selection'], result['costs']
    assert selections['RAW32']['selected_k'] == 1 and selections['RAW32']['selected_utility'] == pytest.approx((3*.875+1.)/4)
    assert selections['TREE32']['selected_depth'] == 1 and selections['TREE32']['selected_min_leaf_roots'] == 8
    assert selections['TREE32']['selected_utility'] == pytest.approx(.8)
    assert counts['shared_library_preparations'] == 3 and set(result['libraries']) == {'FOLD_0', 'FOLD_1', 'FULL'}
    assert counts['tree_predictors_fitted'] == 17 and counts['raw_predictor_configurations'] == 7 and counts['new_predictors_fitted'] == 24
    assert counts['query_input_roots'] == 15 and counts['raw_neighbor_sorts'] == 30 and calls['decisions'] == 11*15
    assert counts['new_linear_solves'] == counts['new_eigen_decompositions'] == counts['new_svd_decompositions'] == 0
    for fold in selections['TREE32']['folds']:
        assert set(fold['train_sources']).isdisjoint(fold['heldout_sources'])
    actual = audit.source_diagnostics(rows, result['models']['RAW32'], result['libraries']['FULL'])
    assert actual['metrics']['roots'] == 15 and actual['projection_residuals']['pairs'] == 15
    assert all('neighbors' not in pair[direction] for row in actual['root_records']
        for pair in row['decision']['estimated_pairs'].values() for direction in ('forward', 'reverse'))
    assert actual['work']['raw_direction_predictions'] == 30


def test_wrong_split_leaf_action_and_small_negative_weight_certificates():
    prepared = library([root('a', 0), root('b', 1)])
    expected = audit.build_tree(prepared, 1, 2); assert expected['kind'] == 'split'
    actual = deepcopy(expected); actual['threshold'] += 1e-12
    assert not audit.close(actual, expected) and not audit.tree_identity(actual, expected)
    actual = deepcopy(expected); actual['left']['prototype_indices'].reverse()
    assert not audit.tree_identity(actual, expected)
    actual = deepcopy(expected); actual['right']['mean'][2] += .001
    assert not audit.close(actual, expected)
    model = audit.model_from_library(prepared, 'RAW32', k=1); decision = audit.choose_action(model, audit.observable(root()), prepared)
    assert audit.verify_decision(deepcopy(decision), decision)
    actual = deepcopy(decision); actual['canonical_action'] = 'LEFT'
    assert not audit.verify_decision(actual, decision)
    expected = dict(canonical_action='DOWN', estimated_pairs={'DOWN|LEFT': dict(forward=dict(neighbors=[dict(weight=1.), dict(weight=0.)]), reverse=dict(neighbors=[dict(weight=1.)]))})
    actual = deepcopy(expected); actual['estimated_pairs']['DOWN|LEFT']['forward']['neighbors'][1]['weight'] = -1e-12
    assert audit.close(actual, expected) and not audit.verify_decision(actual, expected)


def test_goal_error_diagnostics_and_full_fifteen_arm_summary():
    target = root('heldout'); target.update(replica=0, stratum=0)
    labels = [dict(root_id='heldout', action_components=dict(DOWN=[0., 0., 0.], LEFT=[0., 0., 1.]))]
    prepared = library([root('source')]); models = {mode: audit.model_from_library(prepared, mode) for mode in audit.MODES}
    decision = audit.choose_action(models['RAW32'], audit.observable(target), prepared)
    selections = dict(TREE32=dict(selected_depth=1, selected_min_leaf_roots=4, selected_utility=.5), RAW32=dict(selected_k=1, selected_utility=.5))
    choices = {}
    for name in (*audit.MODEL_NAMES, 'FALLBACK'):
        saved = deepcopy(decision); saved['canonical_action'] = 'DOWN'; saved['estimated_pairs']['DOWN|LEFT']['estimated_tail_delta'][2] = 0.
        if name == 'CONDITIONAL':
            saved['estimated_pairs']['DOWN|LEFT']['estimated_tail_delta'][2] = 1.
        choices[name] = [dict(root_id='heldout', canonical_action='DOWN', fallback=False, decision=saved)]
    source = {mode: dict(metrics={'utility': .5}, root_records=[dict(decision=decision)]) for mode in audit.MODES}
    result = audit.summarize(dict(SOURCE=[root('source')], TARGET=[target]), labels, choices, selections, models, source)
    assert len(result['models']) == 15 and len(result['comparisons']) == 13
    assert result['models']['ORACLE']['utility'] == 1. and result['models']['TREE32']['positive_regret_roots'] == 1
    assert not result['whole_cohort_positive_vs_primary'] and not result['all_replicas_positive_vs_primary']
    assert result['success_diagnostics']['TREE32'] == dict(eligible_roots=1, missed=1, wrong_direction=0, missed_root_ids=['heldout'], wrong_direction_root_ids=[])
    assert result['success_diagnostics']['CONDITIONAL']['wrong_direction_root_ids'] == ['heldout']
    assert set(result['projection_residuals']['TARGET']) == {'TREE32', 'RAW32', 'CONDITIONAL', 'PAIR98'}
    assert result['new_tree_fits'] == 17 and result['new_raw_configurations'] == 7 and result['new_parameter_solves'] == 0
