"""Four pure synthetic witnesses for merge geometry and retained diagnostics."""
from collections import Counter
from copy import deepcopy
import math

import numpy as np
import pytest

from scripts import analyze_controlled_predictive_merge_relations_v190 as audit


def layout_record(board, aggregate=None):
    tokens = [['cell', position, rank] for position, rank in enumerate(board)]
    tokens += [['horizontal', 4*row+column, board[4*row+column], board[4*row+column+1]]
               for row in range(4) for column in range(3)]
    tokens += [['vertical', 4*row+column, board[4*row+column], board[4*(row+1)+column]]
               for row in range(3) for column in range(4)]
    return dict(aggregate=list(aggregate or [0.]*6), tokens=tokens)


def vector(value):
    result = [0.]*98
    result[6] = float(value)
    return result


def test_fresh_observer_preserves_v184_cohort_without_source_coverage_split(monkeypatch):
    calls = []
    def observe(case, ordinal, cohort, work):
        calls.append((case, ordinal, cohort)); work['observed_roots'] += 1
        return dict(root_id=case['name'], source_id='overwritten', cohort=cohort, ordinal=ordinal)
    monkeypatch.setattr(audit.exact, 'root_from_case', observe)
    case = dict(name='synthetic-fresh', split='TARGET', replica=2, stratum=5, seed=1900253)
    roots, work = audit.observe_roots([case])
    assert calls == [(case, 0, 'FRESH')]
    assert roots == [dict(root_id='synthetic-fresh', source_id='FRESH_REPLICA:02', cohort='FRESH',
        ordinal=0, replica=2, stratum=5, seed=1900253)]
    assert 'split' not in roots[0] and work == dict(observed_roots=1)


def source_examples():
    rows = []
    for source in range(36):
        for occurrence in range(3 if source == 35 else 4):
            legal = ['LEFT', 'DOWN', 'UP'] if source % 2 else ['LEFT', 'DOWN']
            row = dict(root_id=f'synthetic:{source:02d}:{occurrence}', source_id=f'DESIGN_SOURCE:{source:02d}',
                life=0, canonical_board=[0]*16, legal_actions=legal,
                immediate_rewards=dict(DOWN=0., LEFT=.25), fallback_action='LEFT',
                action_map=dict(DOWN='UP', LEFT='RIGHT'), relation_features=dict(DOWN=vector(1), LEFT=vector(0)),
                action_components=dict(DOWN=[1., .3, .7], LEFT=[.25, .5, .5]),
                oracle_action='UP', teacher_action_native='UP', action_component_fractions={'unused': [[99, 1]]})
            if source % 2:
                row['immediate_rewards']['UP'] = .25
                row['action_map']['UP'] = 'LEFT'
                row['relation_features']['UP'] = vector(0)
                row['action_components']['UP'] = [.25, .5, .5]
            rows.append(row)
    return list(reversed(rows))+[dict(root_id='other-teacher', source_id='ignored', life=1)]


def test_all_98_values_have_frozen_rank_bases_normalizers_order_and_read_only_cache():
    from acfqp.science import controlled_predictive_merge_relations_v190 as core

    board = [11, 11]+[0]*14
    aggregate = [1., 14., 1., 0., 0., 0.]
    record = layout_record(board, aggregate)
    root = dict(layout_features=dict(DOWN=record))
    before, work, production_work = deepcopy(root), Counter(), Counter()
    actual = audit.action_features_from_root(root, work)
    production = core.action_features_from_root(root, production_work)
    assert audit.same(actual, production) and audit.same(production, actual)
    assert work == production_work and root == before
    node = [.5, 0., 1/3, 0., .5, 0., .25, 0., .5]
    pair = [1., 0., 0., 0., 0., 0., 0., 1/3, 0.,
            1/3, 1/3, 0., 0., 0., 0., 1., 1.,
            0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0.,
            1., 1., 0., 0.]
    projected_pair = [value/math.sqrt(120) for value in pair]
    expected = aggregate+node+projected_pair+node+projected_pair+[0.]*8
    assert len(pair) == 33 and len(expected) == len(actual['DOWN']) == 98
    assert actual['DOWN'] == pytest.approx(expected, abs=1e-14)
    assert len(core.FEATURE_NAMES) == len(set(core.FEATURE_NAMES)) == 98
    assert list(core.FEATURE_NAMES[:6]) == list(core.AGGREGATE_NAMES)
    assert core.FEATURE_NAMES[6] == 'rank_over_goal:node:count'
    assert core.FEATURE_NAMES[15] == 'rank_over_goal:pair:same_row'
    assert core.FEATURE_NAMES[48] == 'goal_value_fraction:node:count'
    assert core.FEATURE_NAMES[57] == 'goal_value_fraction:pair:same_row'
    assert list(core.FEATURE_NAMES[90:]) == [f'vacancy_neighbor_{direction}_rank_{rank}'
        for direction in ('left', 'right', 'up', 'down') for rank in (1, 2)]
    assert work['relation_token_kind_reads'] == 40 and work['relation_cell_rank_reads'] == 16
    assert work['relation_node_records'] == 2 and work['relation_equal_pair_records'] == 1
    assert work['relation_rank_basis_evaluations'] == 6
    assert work['relation_node_moment_accumulations'] == 36 and work['relation_pair_moment_accumulations'] == 66
    assert work['relation_node_projection_normalizations'] == 18 and work['relation_pair_projection_normalizations'] == 66
    cached_root = dict(relation_features=dict(DOWN=list(expected)))
    cached_work, production_cached_work = Counter(), Counter()
    cached = audit.action_features_from_root(cached_root, cached_work)
    assert audit.same(cached, core.action_features_from_root(cached_root, production_cached_work))
    assert cached_work == production_cached_work == Counter(relation_feature_cache_hits=1, relation_cached_feature_reads=98)
    cached['DOWN'][6] = 99.
    assert cached_root['relation_features']['DOWN'] == expected
    assert not any(any(word in key for word in ('swipe', 'spawn', 'merge')) for key in work+cached_work)


def test_packing_blocker_order_once_only_pairs_and_rank12_vacancy_information():
    from acfqp.science import controlled_predictive_merge_relations_v190 as core

    triple = layout_record([2, 2, 2]+[0]*13)
    blocked_board = [0]*16
    for position, rank in ((0, 11), (5, 2), (10, 3), (12, 11)):
        blocked_board[position] = rank
    records = [triple, layout_record(blocked_board), layout_record([2, 0, 2]+[0]*13),
               layout_record([1, 0, 2]+[0]*13)]
    contracts = []
    for record in records:
        before, work, production_work = deepcopy(record), Counter(), Counter()
        actual, production = audit.build_contract(record, work), core.build_contract(record, production_work)
        assert audit.same(actual, production) and audit.same(production, actual)
        assert work == production_work and record == before
        contracts.append(actual)
    once, blocked, separated, vacancy = contracts
    assert once['once_pairs'] == dict(LEFT=[[0, 1]], RIGHT=[[1, 2]], UP=[], DOWN=[])
    masks = {(pair['first'], pair['second']): pair['once_masks'] for pair in once['equal_pairs']}
    assert masks[(0, 1)] == dict(LEFT=1., RIGHT=0., UP=0., DOWN=0.)
    assert masks[(1, 2)] == dict(LEFT=0., RIGHT=1., UP=0., DOWN=0.)
    assert masks[(0, 2)] == dict(LEFT=0., RIGHT=0., UP=0., DOWN=0.)
    assert [node['rank'] for node in once['nodes']] == [2, 2, 2]
    pair = next(pair for pair in blocked['equal_pairs'] if (pair['first'], pair['second']) == (0, 12))
    assert pair['raw_blockers'] == []
    assert pair['moments'][:9] == pytest.approx([0., 1., 0., 0., 0., 0., 1., 0., 0.])
    for direction, positions in (('LEFT', (0, 12)), ('RIGHT', (3, 15))):
        projection = pair['projections'][direction]
        assert (projection['first_position'], projection['second_position']) == positions
        assert projection['aligned'] is True and projection['blockers'] == [5, 10]
        assert projection['blocker_ranks'] == [2, 3]
    assert pair['moments'][13:17] == [0.]*4
    assert pair['moments'][17:21] == pytest.approx([5/22, 5/22, 0., 0.])
    assert pair['moments'][21:29] == pytest.approx([2/11, 3/11, 2/11, 3/11, 0., 0., 0., 0.])
    assert pair['once_masks'] == dict(LEFT=0., RIGHT=0., UP=1., DOWN=1.)
    gap = separated['equal_pairs'][0]
    assert gap['moments'][7] == pytest.approx(2/3)
    assert gap['moments'][9:13] == pytest.approx([1/3, 1/3, 0., 0.])
    assert gap['projections']['UP']['aligned'] is True and gap['projections']['UP']['blockers'] == []
    assert gap['moments'][13:17] == [0., 0., 1., 1.]
    assert gap['once_masks'] == dict(LEFT=1., RIGHT=1., UP=0., DOWN=0.)
    assert vacancy['equal_pairs'] == []
    assert vacancy['vacancy_moments'] == pytest.approx([.25, .25, 0., .25, .25, .25, 0., 0.])
    assert once['vacancy_moments'] == pytest.approx([0., .25, 0., 0., 0., .75, 0., 0.])
    # Rank two receives different linear/exponential bases, with no rank-three merge output.
    features = audit.action_features_from_root(dict(layout_features=dict(DOWN=triple)))['DOWN']
    assert features[6] == pytest.approx(3/22) and features[48] == pytest.approx(3/2048)
    assert features[15] == pytest.approx(6/(11*math.sqrt(120)))
    assert features[57] == pytest.approx(3/(512*math.sqrt(120)))
    assert features[90:] == pytest.approx(once['vacancy_moments'])


def test_source36_group_selection_certifies_13_saved_fits_and_scores_actual_full_vectors(monkeypatch):
    from acfqp.science import controlled_predictive_merge_relation_learning_v190 as core

    rows, before = source_examples(), None
    before = deepcopy(rows)
    design, production_design = audit.prepare_design(rows), core.prepare_design(rows)
    actual_metadata = {key: value for key, value in design.items() if key not in ('X', 'Y')}
    production_metadata = {key: value for key, value in production_design.items() if key not in ('X', 'Y')}
    assert audit.same(actual_metadata, production_metadata) and audit.same(production_metadata, actual_metadata)
    assert design['prepare_counts'] == production_design['prepare_counts']
    assert design['feature_counts'] == production_design['feature_counts']
    assert design['X'] == pytest.approx(production_design['X']) and design['Y'] == pytest.approx(production_design['Y'])
    assert design['shape'] == [285, 98]
    assert design['prepare_counts']['examples_examined'] == 144
    assert design['prepare_counts']['other_life_examples_excluded'] == 1
    assert design['prepare_counts']['examples_fitted'] == 143
    assert all(sum(pair['weight'] for pair in label['pairs']) == pytest.approx(1.) for label in design['fit_labels'])
    assert all(len(pair['components']) == 3 for pair in design['pair_records'])
    assert design['pair_records'][0]['components'] == pytest.approx([1., -.2, .2])
    production = core.fit_model(rows)
    observed, original_choose = [], audit.choose_action
    def observable_only(model, root, counts=None):
        observed.append(set(root))
        assert not {'action_components', 'action_component_fractions', 'teacher_action_native', 'oracle_action'} & set(root)
        return original_choose(model, root, counts)
    monkeypatch.setattr(audit, 'choose_action', observable_only)
    actual, solver_work = audit.fit_model(rows, saved_selection=production['selection'], saved_model=production['model'])
    assert audit.same(actual, production) and audit.same(production, actual)
    assert rows == before and actual['costs'] == production['costs']
    assert actual['cache_counts'] == production['cache_counts'] == dict(
        relation_feature_cache_hits=143, relation_cached_feature_reads=34986)
    assert len(observed) == 6*143
    assert all(keys <= {'root_id', 'source_id', 'life', 'canonical_board', 'legal_actions',
        'immediate_rewards', 'fallback_action', 'action_map', 'relation_features', 'layout_features', 'action_features'} for keys in observed)
    selection, model = actual['selection'], actual['model']
    sources = [f'DESIGN_SOURCE:{source:02d}' for source in range(36)]
    assert selection['source_folds'] == [sources[::2], sources[1::2]]
    assert selection['lambdas'] == [0., .0001, .001, .01, .1, 1.]
    assert selection['selected_lambda'] == 0. and selection['selected_utility'] == pytest.approx(33/40)
    assert [candidate['utility'] for candidate in selection['candidates']] == pytest.approx([33/40]*6)
    for index, fold in enumerate(selection['folds']):
        assert len(fold['train_sources']) == len(fold['heldout_sources']) == 18
        assert set(fold['train_sources']).isdisjoint(fold['heldout_sources'])
        assert fold['design']['source_ids'] == fold['train_sources']
        assert fold['design']['shape'] == [213 if index == 0 else 72, 98]
        assert fold['design']['work'] == production['selection']['folds'][index]['design']['work']
    assert len(selection['folds'][0]['design']['action_root_ids']['UP']) == 71
    assert selection['folds'][1]['design']['action_root_ids']['UP'] == []
    assert selection['folds'][1]['design']['pair_root_ids']['DOWN|UP'] == []
    first, second = [result['choices'] for result in selection['candidates'][0]['fold_results']]
    assert len(first) == 72 and len(second) == 71
    assert all(choice['decision']['canonical_action'] == 'DOWN' and not choice['decision']['fallback'] for choice in first)
    assert all(choice['components'] == [1., .3, .7] and choice['utility'] == pytest.approx(1.4) for choice in first)
    assert all(choice['decision']['canonical_action'] == 'LEFT' and choice['decision']['fallback']
        and choice['decision']['reason'] == 'insufficient_action_support' for choice in second)
    assert all(choice['components'] == [.25, .5, .5] for choice in second)
    assert sum(choice['utility'] for choice in first+second)/143 == pytest.approx(118.55/143)
    assert selection['selected_utility'] != pytest.approx(118.55/143)
    coefficients = np.zeros((98, 3)); coefficients[6] = [1., -.2, .2]
    assert np.asarray(model['coefficients']) == pytest.approx(coefficients, abs=1e-12)
    assert model['constants']['columns'] == 98 and model['rank'] == 1
    assert len(model['root_ids']) == 143 and len(model['fit_residuals']) == 285
    assert model['loss'] == pytest.approx(0., abs=1e-24) and model['penalty'] == 0.
    assert model['root_mean_loss'] == pytest.approx(0., abs=1e-24)
    assert model['fit_counts'] == production['model']['fit_counts']
    assert selection['costs']['ridge_design_preparations'] == selection['costs']['ridge_svd_decompositions'] == 3
    assert selection['costs']['ridge_coefficient_filters'] == selection['costs']['ridge_predictors_fitted'] == 13
    assert selection['costs']['relation_feature_cache_hits'] == 1144
    assert selection['costs']['relation_cached_feature_reads'] == 279888
    assert actual['costs']['new_predictors_fitted'] == 13
    assert solver_work['zero_minimum_norm_lstsq_solves'] == 3
    assert solver_work['positive_column_normal_solves'] == 10
    assert solver_work['independent_coefficient_arrays_checked'] == solver_work['independent_coefficient_arrays_passed'] == 13


def test_development_regrouping_splits_old_cycle_vertices_without_fit_or_gate_and_summary_keeps_losses():
    from scripts import run_controlled_predictive_merge_relations_v190 as runner

    roots = [dict(root_id=f'development:{index}', legal_actions=['DOWN', 'LEFT'],
                  immediate_rewards=dict(DOWN=0., LEFT=1.), relation_features={}) for index in range(4)]
    roots[0].update(legal_actions=['RIGHT', 'LEFT', 'DOWN'], immediate_rewards=dict(DOWN=.5, LEFT=.5+audit.EPS/2, RIGHT=.125),
                   relation_features=dict(DOWN=vector(0), LEFT=vector(0), RIGHT=vector(1)))
    roots[1].update(immediate_rewards=dict(DOWN=0., LEFT=0.), relation_features=dict(DOWN=vector(0), LEFT=vector(2)))
    roots[2]['relation_features'] = dict(DOWN=vector(3), LEFT=vector(1))
    roots[3]['relation_features'] = dict(DOWN=vector(1), LEFT=vector(0))
    labels = [dict(root_id=roots[0]['root_id'], action_components=dict(DOWN=[1., .5, 0.], LEFT=[.8, 0., .2], RIGHT=[.5, .5, .25])),
              dict(root_id=roots[1]['root_id'], action_components=dict(DOWN=[1., .5, 0.], LEFT=[.8, 0., .2]))]
    labels += [dict(root_id=root['root_id'], action_components=dict(DOWN=[2., 0., 0.], LEFT=[1., 1., 0.])) for root in roots[2:]]
    previous = dict(alias=dict(root_records=[dict(root_id=root['root_id'], within_root_regret=.5 if index < 2 else 0.)
        for index, root in enumerate(roots)]), problem=dict(roots=[
        dict(root_id=roots[0]['root_id'], classes=[dict(vertex_id=0, representative='DOWN'), dict(vertex_id=1, representative='RIGHT')]),
        dict(root_id=roots[1]['root_id'], classes=[dict(vertex_id=0, representative='DOWN')]),
        dict(root_id=roots[2]['root_id'], classes=[dict(vertex_id=0, representative='DOWN'), dict(vertex_id=1, representative='LEFT')]),
        dict(root_id=roots[3]['root_id'], classes=[dict(vertex_id=1, representative='DOWN'), dict(vertex_id=0, representative='LEFT')])]))
    certificate = dict(status='weak_infeasible', upper_bound='-1', dual_explanations=[dict(edges=[
        dict(root_id=roots[2]['root_id'], best=dict(vertex_id=0, action='DOWN'), bad=dict(vertex_id=1, action='LEFT'), reward_difference='-1'),
        dict(root_id=roots[3]['root_id'], best=dict(vertex_id=1, action='DOWN'), bad=dict(vertex_id=0, action='LEFT'), reward_difference='-1')])])
    before = deepcopy((roots, labels, previous, certificate))
    actual = audit.development_diagnostics(roots, labels, previous, certificate)
    production = runner.development_diagnostics(roots, labels, previous, certificate)
    assert audit.same(actual, production) and audit.same(production, actual)
    assert (roots, labels, previous, certificate) == before and actual['work'] == production['work']
    assert actual['metrics'] == dict(roots=4, old_loss_roots=2, new_loss_roots=1, old_loss_roots_now_accessible=1,
        old_floor_mean=.25, new_floor_mean=.125, old_cycle_vertices=2, old_cycle_vertices_split=1)
    assert actual['root_records'][0]['groups'] == [['DOWN', 'LEFT'], ['RIGHT']]
    assert actual['root_records'][0]['representatives'] == ['DOWN', 'RIGHT']
    assert actual['root_records'][1]['groups'] == [['DOWN'], ['LEFT']]
    assert [row['new_floor'] for row in actual['root_records']] == pytest.approx([.5, 0., 0., 0.])
    assert actual['vertex_records'] == [dict(vertex_id=0, occurrences=4, still_equal=False), dict(vertex_id=1, occurrences=3, still_equal=True)]
    assert [row['still_equal'] for row in actual['certified_vertex_records']] == [False, True]
    assert actual['work'] == dict(development_vector_comparisons=5, development_feature_values_read=2352,
        development_alias_reward_comparisons=1, development_roots=4, development_complete_vector_reads=17,
        development_component_reads=51, development_utility_evaluations=17,
        development_vertex_vector_comparisons=5, development_certificate_vector_comparisons=2)
    assert not any(word in key for key in actual for word in ('gate', 'fit', 'feasible'))

    fresh_roots = dict(SOURCE=[dict(source_id=f'source:{index//2}') for index in range(4)], TARGET=[])
    fresh_labels, choices = [], {name: [] for name in (*runner.MODEL_NAMES, 'FALLBACK')}
    for index, (replica, gain) in enumerate(((0, 4.), (0, -1.), (0, 0.), (1, -1.))):
        identity = f'fresh:{index}'
        fresh_roots['TARGET'].append(dict(root_id=identity, replica=replica, stratum=index, legal_actions=['DOWN', 'LEFT']))
        fresh_labels.append(dict(root_id=identity, action_components=dict(DOWN=[2., .5, 0.], LEFT=[gain+1., 0., .5])))
        for name, selected in choices.items():
            selected.append(dict(root_id=identity, canonical_action='LEFT' if name == 'RELATION' else 'DOWN',
                fallback=name == 'RELATION' and index == 1, decision=dict(predicted_components=dict(LEFT=[999., 0., 0.]))))
    selection = dict(selected_lambda=.01, selected_utility=.8,
        candidates=[dict(lambda_value=value, utility=score, unused='excluded') for value, score in
                    zip((0., .0001, .001, .01, .1, 1.), (.3, .4, .5, .8, .6, .7))])
    model = dict(constants=dict(columns=98), rank=2, root_mean_loss=.125)
    result = audit.summarize(fresh_roots, fresh_labels, choices, selection, model, actual)
    saved = runner.summarize(fresh_roots, fresh_labels, choices, selection, model, actual)
    assert audit.same(result, saved) and audit.same(saved, result)
    assert result['schema'] == 'acfqp.merge_relations.v190.summary' and result['complete'] is True
    assert result['development'] == actual['metrics']
    assert result['SOURCE'] == dict(roots=4, design_groups=2, selected_lambda=.01, source_heldout_utility=.8,
        source_selection=[dict(lambda_value=row['lambda_value'], utility=row['utility']) for row in selection['candidates']],
        columns=98, source_rank=2, source_root_mean_loss=.125)
    assert result['models']['RELATION']['components'] == pytest.approx([1.5, 0., .5])
    assert result['models']['RELATION']['utility'] == pytest.approx(2.)
    assert result['models']['RELATION']['positive_regret_roots'] == 2 and result['models']['RELATION']['fallback_roots'] == 1
    assert result['models']['ORACLE']['components'] == pytest.approx([11/4, 3/8, 1/8])
    assert set(result['comparisons']) == {'RELATION_MINUS_'+name for name in runner.CONTROLS}
    for effect in result['comparisons'].values():
        assert effect['components'] == pytest.approx([-.5, -.5, .5]) and effect['utility'] == pytest.approx(.5)
        assert (effect['improved_roots'], effect['worsened_roots'], effect['equal_value_roots']) == (1, 2, 1)
        assert (effect['positive_gain_sum'], effect['negative_gain_sum']) == pytest.approx((4., -2.))
        assert effect['largest_gain_root'] == 'fresh:0' and effect['largest_gain_share_of_positive'] == 1.
        assert effect['largest_loss_root'] == 'fresh:1' and effect['largest_loss'] == -1.
    assert [row['comparisons']['RELATION_MINUS_LINEAR']['utility'] for row in result['replicas']] == pytest.approx([1., -1.])
    assert result['whole_cohort_positive_vs_linear_ridge_old_shared'] is True
    assert result['all_replicas_positive_vs_linear_ridge_old_shared'] is False
    assert result['oracle_minus_one'] == pytest.approx(1.) and result['oracle_minus_relation'] == pytest.approx(.5)
    assert result['headroom_closed_fraction'] == pytest.approx(.5)
    assert 'feature_coverage' not in result
    assert (result['new_environment_samples'], result['new_source_games'],
            result['new_native_weight_updates'], result['new_predictors_fitted']) == (0, 0, 0, 13)
