"""Independent lineage, full-vector calibration and frozen transfer certificates."""
from collections import Counter
from copy import deepcopy

import pytest

from scripts import analyze_controlled_predictive_relational_programs_v196 as audit


PAYLOAD = dict(program=dict(pack=True, merge_relation='equal', rank_increment=1,
    consumption='once', reward_rule='output_value'), goal_rank=11,
    spawn_distribution=[[1, 9, 10], [2, 1, 10]], spawn_location='uniform')


def contract(value, goal=0.):
    return dict(goal_now=bool(goal), values=[float(goal), 0., float(value)]+[0.]*78)


def root(name='query', source=0, first=0, second=1):
    return dict(root_id=name, source_id=f'DESIGN_SOURCE:{source:02d}', life=0, canonical_board=[0]*16,
        legal_actions=['DOWN', 'LEFT'], immediate_rewards=dict(DOWN=0., LEFT=0.), fallback_action='LEFT',
        action_map=dict(DOWN='UP', LEFT='RIGHT', RIGHT='LEFT', UP='DOWN'),
        raw_afterstates=dict(DOWN=[9, 9, 10, 0]+[0]*12, LEFT=[10, 9, 0, 0]+[0]*12),
        program_contracts=dict(DOWN=contract(first), LEFT=contract(second)),
        action_components=dict(DOWN=[1., .2, .3], LEFT=[0., .5, .5]))


def word_prefix(trace, *actions):
    word = next(row for row in trace['words'] if row['actions'] == list(actions))
    return trace['prefixes'][word['prefix_id']]


def library(rows):
    return audit.prepare_library(rows, 'FULL')


def test_two_parent_lineage_once_consumption_and_second_step_goal_dependency():
    counts = Counter(); trace = audit.trace_afterstate([9, 9, 10, 0]+[0]*12, PAYLOAD, counts)
    first, second = word_prefix(trace, 'LEFT'), word_prefix(trace, 'LEFT', 'LEFT')
    assert first['events'] == [dict(id=16, left=0, right=1, left_rank=9, right_rank=9,
        rank=10, reward=1024, origins=[0, 1], step=1, line=0, cell=0)]
    assert first['valid'] and not first['goal'] and first['score'] == .5
    assert second['events'] == [dict(id=17, left=16, right=2, left_rank=10, right_rank=10,
        rank=11, reward=2048, origins=[0, 1, 2], step=2, line=0, cell=0)]
    assert second['goal'] and second['linked_goal'] and second['score'] == 1.5 and second['goal_ids'] == [17]
    right = word_prefix(trace, 'RIGHT', 'RIGHT')
    assert right['events'][0]['left'] == 2 and right['events'][0]['right'] == 16
    assert right['events'][0]['origins'] == [0, 1, 2] and right['linked_goal']
    assert len(trace['values']) == 81 and len(trace['words']) == 20 and len(trace['prefixes']) == 21
    assert counts['program_swipe_calls']+counts['program_stopped_prefix_reuses'] == 20
    assert counts['program_dependency_edges'] == 2*counts['program_merges']
    assert counts['program_line_rewrites'] == 4*counts['program_swipe_calls']
    assert counts['program_feature_values_written'] == 81


def test_absorbing_goal_illegal_words_and_partial_reward_do_not_invent_linkage():
    work = Counter(); won = audit.trace_afterstate([11]+[0]*15, PAYLOAD, work)
    assert all(row['valid'] and row['goal'] and not row['linked_goal'] and row['score'] == 0. for row in won['words'])
    assert work.get('program_swipe_calls', 0) == 0 and work['program_stopped_prefix_reuses'] == 20
    partial = audit.trace_afterstate([9, 9, 0, 0]+[0]*12, PAYLOAD)
    stopped = word_prefix(partial, 'LEFT', 'LEFT')
    assert stopped['executed'] and not stopped['valid'] and stopped['score'] == .5 and not stopped['goal']
    illegal = audit.trace_afterstate([10, 9, 0, 0]+[0]*12, PAYLOAD)
    first, inherited = word_prefix(illegal, 'LEFT'), word_prefix(illegal, 'LEFT', 'DOWN')
    assert first['executed'] and not first['valid'] and not inherited['executed'] and not inherited['valid']
    direct = audit.trace_afterstate([10, 10, 0, 0]+[0]*12, PAYLOAD)
    assert word_prefix(direct, 'LEFT')['goal'] and not word_prefix(direct, 'LEFT')['linked_goal']
    inherited = word_prefix(direct, 'LEFT', 'RIGHT')
    assert not inherited['executed'] and inherited['goal'] and not inherited['linked_goal'] and inherited['score'] == 1.


def test_cache_is_prefix_shared_and_ignores_future_spawns_and_teacher_labels():
    rows = [root('source'), root('target', 1)]
    for row in rows:
        del row['program_contracts']
        row['action_components'] = {'forbidden': 'trace may not read labels'}
        row['future_spawn'] = {'forbidden': 'trace may not read future observations'}
    counts = audit.cache_roots(rows, PAYLOAD)
    assert counts['program_cache_roots_built'] == 2 and counts['program_contracts_built'] == 4
    assert counts['program_initial_cell_reads'] == 64 and counts['program_prefix_records'] == 84
    assert counts['program_word_records'] == 80 and counts['program_feature_values_written'] == 324
    assert counts['program_swipe_calls'] <= 80 and not any('spawn' in name for name in counts)
    assert audit.cache_roots(rows, PAYLOAD) == dict(program_cache_hits=2)
    changed_spawn = deepcopy(PAYLOAD); changed_spawn.update(spawn_distribution='unreadable future', spawn_location='unreadable future')
    assert audit.trace_afterstate(rows[0]['raw_afterstates']['DOWN'], changed_spawn) == rows[0]['program_contracts']['DOWN']


def test_source_equal_mass_full_rfs_and_learned_continuation_terminal_ablation():
    mass_rows = [root('a', 0), root('b', 0), root('c', 1), root('d', 1)]
    mass_rows[-1]['legal_actions'] = ['DOWN']; mass_rows[-1]['action_components'] = {'DOWN': [1., .2, .3]}
    mass_rows[0]['immediate_rewards'] = dict(DOWN=.5, LEFT=.2)
    mass_rows[0]['action_components'] = dict(DOWN=[1.5, .2, .3], LEFT=[.2, .5, .5])
    prepared = library(mass_rows)
    assert prepared['source_root_counts'] == {'DESIGN_SOURCE:00': 2, 'DESIGN_SOURCE:01': 2}
    assert len(prepared['prototypes']) == 6 and all(row['root_mass'] == .25 for row in prepared['prototypes'])
    assert prepared['prototypes'][0]['tail_difference'] == pytest.approx([1., -.3, -.2])
    assert prepared['prototypes'][0]['features162'] == contract(0)['values']+contract(1)['values']
    assert sum(row['root_mass'] for row in prepared['prototypes'] if row['source_id'].endswith(':01')) == .5
    rows = [root(f'partition:{i}', i//2) for i in range(4)]; prepared = library(rows)
    program = audit.model_from_library(prepared, 'PROGRAM', min_leaf_roots=4)
    terminal = audit.model_from_library(prepared, 'TERMINAL', min_leaf_roots=4)
    assert program['tree']['kind'] == 'split' and program['tree']['feature'] == 2 and program['tree']['threshold'] == 0.
    assert program['tree']['left']['root_count'] == program['tree']['right']['root_count'] == 4
    assert program['tree']['left']['mean'] == pytest.approx([1., -.3, -.2])
    assert terminal['tree']['kind'] == 'leaf' and terminal['input_columns'] == [0, 81]
    assert terminal['constants']['columns'] == 2 and program['constants']['columns'] == 162
    assert program['feature_names'][2] == 'first:DOWN:goal' and len(program['feature_names']) == 162
    assert program['native_teacher_query'] == 'goal_1_risk_1' and program['horizon'] == 3
    query = root(); query['immediate_rewards']['LEFT'] = .5; query['action_components'] = {'forbidden': 'no query labels'}
    assert audit.choose_action(program, audit.observable(query), prepared)['canonical_action'] == 'DOWN'
    assert audit.choose_action(terminal, audit.observable(query), prepared)['canonical_action'] == 'LEFT'
    # Logical feature1 in the ablation must address full column81, not word column1.
    terminal['tree'] = dict(kind='split', feature=1, threshold=.5,
        left=dict(kind='leaf', node_id=1, mean=[1., 0., 0.]), right=dict(kind='leaf', node_id=2, mean=[-1., 0., 0.]))
    query['program_contracts']['LEFT']['values'][0] = 1.
    assert audit.choose_action(terminal, audit.observable(query), prepared)['estimated_pairs']['DOWN|LEFT']['estimated_tail_delta'] == [-1., 0., 0.]


def test_two_direction_full_rfs_reward_once_dyadic_neighbors_and_eps_forced():
    prepared = library([root('source')]); model = audit.model_from_library(prepared, 'PROGRAM')
    model['tree'] = dict(kind='split', feature=2, threshold=1,
        left=dict(kind='leaf', node_id=1, mean=[1., 2., 3.]), right=dict(kind='leaf', node_id=2, mean=[.2, 4., -1.]))
    query = root(first=0, second=2); query['immediate_rewards'] = dict(DOWN=.7, LEFT=.2)
    decision = audit.choose_action(model, audit.observable(query), prepared); pair = decision['estimated_pairs']['DOWN|LEFT']
    assert pair['estimated_tail_delta'] == pytest.approx([.4, -1., 2.])
    assert pair['projected_tail_delta'] == pytest.approx([.4, -1., 2.])
    assert decision['predicted_pairs']['DOWN|LEFT'] == pytest.approx([.9, -1., 2.])
    assert decision['projection_residual_sse'] == 0. and decision['work']['pair_reward_additions'] == 2
    for row in prepared['prototypes']:
        for column in range(4, 162, 4):
            row['features162'][column] = column/2048.
    work = Counter(); geometry = audit.query_inputs(audit.observable(query), work)
    audit.neighbor_geometry(geometry, prepared, work, audit.prototype_matrix(prepared, work))
    for direction in ('forward', 'reverse'):
        inputs = geometry['pairs']['DOWN|LEFT'][direction]
        expected = sorted((sum((inputs[c]-row['features162'][c])**2 for c in range(162)), i) for i, row in enumerate(prepared['prototypes']))
        assert geometry['pairs']['DOWN|LEFT'][direction+'_neighbors'] == expected
    model = audit.model_from_library(prepared, 'PROGRAM_NEIGHBOR', k=1)
    query = root(first=0, second=0); query['legal_actions'] = ['LEFT', 'DOWN']
    query['immediate_rewards'] = dict(DOWN=0., LEFT=audit.EPS/2)
    query['action_components'] = {'forbidden': 'inference must not read labels'}
    tied = audit.choose_action(model, audit.observable(query), prepared)
    assert audit.weights_valid(tied) and tied['canonical_action'] == 'DOWN'
    query['immediate_rewards']['LEFT'] = 2*audit.EPS
    assert audit.choose_action(model, audit.observable(query), prepared)['canonical_action'] == 'LEFT'
    query['legal_actions'] = ['DOWN']; query['immediate_rewards']['DOWN'] = .9
    forced = audit.choose_action(model, audit.observable(query), prepared)
    assert forced['predicted_components']['DOWN'] == [.9, 0., 0.] and forced['estimated_pairs'] == {}
    assert forced['work'].get('neighbor_direction_predictions', 0) == 0


def test_actual_group_cv_shared_libraries_34_trees_41_configs_and_compact_source(monkeypatch):
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
    fitted = audit.fit_models(rows); selections, counts = fitted['selection'], fitted['costs']
    expected = (3*.875+1.)/4
    assert selections['PROGRAM_NEIGHBOR']['selected_k'] == 1 and selections['PROGRAM_NEIGHBOR']['selected_utility'] == pytest.approx(expected)
    assert selections['PROGRAM']['selected_depth'] == 1 and selections['PROGRAM']['selected_min_leaf_roots'] == 8
    assert selections['PROGRAM']['selected_utility'] == pytest.approx(.8)
    assert selections['TERMINAL']['selected_depth'] == 1 and selections['TERMINAL']['selected_min_leaf_roots'] == 4
    assert selections['TERMINAL']['selected_utility'] == pytest.approx(expected)
    assert set(fitted['libraries']) == {'FOLD_0', 'FOLD_1', 'FULL'} and counts['shared_library_preparations'] == 3
    assert counts['tree_predictors_fitted'] == 34 and counts['PROGRAM_tree_predictors_fitted'] == counts['TERMINAL_tree_predictors_fitted'] == 17
    assert counts['neighbor_predictor_configurations'] == 7 and counts['new_predictors_fitted'] == 41
    assert counts['query_input_roots'] == 15 and counts['neighbor_sorts'] == 30 and counts['neighbor_matrix_preparations'] == 2
    assert calls['decisions'] == 19*15 and counts['new_linear_solves'] == counts['new_eigen_decompositions'] == counts['new_svd_decompositions'] == 0
    for mode in audit.MODES:
        assert all(set(fold['train_sources']).isdisjoint(fold['heldout_sources']) for fold in selections[mode]['folds'])
    actual = audit.source_diagnostics(rows, fitted['models']['PROGRAM_NEIGHBOR'], fitted['libraries']['FULL'])
    assert actual['metrics']['roots'] == 15 and actual['projection_residuals']['pairs'] == 15
    assert all('neighbors' not in pair[direction] for row in actual['root_records']
        for pair in row['decision']['estimated_pairs'].values() for direction in ('forward', 'reverse'))
    assert actual['work']['neighbor_direction_predictions'] == 30 and actual['work']['neighbor_matrix_preparations'] == 15


def test_tampered_parent_feature_split_action_and_negative_weight_rejected():
    trace = audit.trace_afterstate([9, 9, 10, 0]+[0]*12, PAYLOAD)
    altered = deepcopy(trace); word_prefix(altered, 'LEFT', 'LEFT')['events'][0]['right'] = 3
    assert not audit.close(altered, trace)
    altered = deepcopy(trace); altered['values'][2] = 1.
    assert altered != trace
    prepared = library([root('a', 0), root('b', 1)])
    expected = audit.build_tree(prepared, 1, 2, list(range(162))); assert expected['kind'] == 'split'
    altered = deepcopy(expected); altered['threshold'] += .001
    assert not audit.close(altered, expected) and not audit.tree_identity(altered, expected)
    altered = deepcopy(expected); altered['left']['prototype_indices'].reverse()
    assert not audit.tree_identity(altered, expected)
    model = audit.model_from_library(prepared, 'PROGRAM_NEIGHBOR'); decision = audit.choose_action(model, audit.observable(root()), prepared)
    assert audit.verify_decision(deepcopy(decision), decision)
    altered = deepcopy(decision); altered['canonical_action'] = 'LEFT'
    assert not audit.verify_decision(altered, decision)
    expected = dict(canonical_action='DOWN', estimated_pairs={'DOWN|LEFT': dict(forward=dict(neighbors=[dict(weight=1.), dict(weight=0.)]), reverse=dict(neighbors=[dict(weight=1.)]))})
    altered = deepcopy(expected); altered['estimated_pairs']['DOWN|LEFT']['forward']['neighbors'][1]['weight'] = -1e-12
    assert audit.close(altered, expected) and not audit.verify_decision(altered, expected)


def test_eighteen_arm_summary_seven_pair_goal_errors_and_twelve_input_roster():
    target = root('heldout'); target.update(replica=0, stratum=0)
    labels = [dict(root_id='heldout', action_components=dict(DOWN=[0., 0., 0.], LEFT=[0., 0., 1.]))]
    prepared = library([root('source')]); models = {mode: audit.model_from_library(prepared, mode) for mode in audit.MODES}
    decision = audit.choose_action(models['PROGRAM_NEIGHBOR'], audit.observable(target), prepared)
    selections = {mode: dict(selected_depth=1, selected_min_leaf_roots=4, selected_utility=.5) for mode in ('PROGRAM', 'TERMINAL')}
    selections['PROGRAM_NEIGHBOR'] = dict(selected_k=1, selected_utility=.5)
    choices = {}
    for name in (*audit.MODEL_NAMES, 'FALLBACK'):
        saved = deepcopy(decision); saved['canonical_action'] = 'DOWN'; saved['estimated_pairs']['DOWN|LEFT']['estimated_tail_delta'][2] = 0.
        if name == 'CONDITIONAL':
            saved['estimated_pairs']['DOWN|LEFT']['estimated_tail_delta'][2] = 1.
        choices[name] = [dict(root_id='heldout', canonical_action='DOWN', fallback=False, decision=saved)]
    source = {mode: dict(metrics={'utility': .5}, root_records=[dict(decision=decision)]) for mode in audit.MODES}
    result = audit.summarize(dict(SOURCE=[root('source')], TARGET=[target]), labels, choices, selections, models, source)
    assert result['schema'] == 'acfqp.relational_programs.v196.summary'
    assert len(result['models']) == 18 and len(result['comparisons']) == 16
    assert result['models']['ORACLE']['utility'] == 1. and result['models']['PROGRAM']['positive_regret_roots'] == 1
    assert not result['whole_cohort_positive_vs_primary'] and not result['all_replicas_positive_vs_primary']
    assert result['success_diagnostics']['PROGRAM'] == dict(eligible_roots=1, missed=1, wrong_direction=0, missed_root_ids=['heldout'], wrong_direction_root_ids=[])
    assert result['success_diagnostics']['CONDITIONAL']['wrong_direction_root_ids'] == ['heldout']
    assert set(result['projection_residuals']['TARGET']) == {'PROGRAM', 'TERMINAL', 'PROGRAM_NEIGHBOR', 'TREE32', 'RAW32', 'CONDITIONAL', 'PAIR98'}
    assert set(result['projection_residuals']['SOURCE']) == set(audit.MODES)
    assert result['new_tree_fits'] == 34 and result['new_neighbor_configurations'] == 7 and result['new_predictors_fitted'] == 41
    assert audit.INPUT_NAMES == ('v195_stage_checks.json', 'v195_run.json', 'v195_roots.json', 'region_models.json', 'region_libraries.json',
        'conditional_models.json', 'nonlinear_model.json', 'relation_model.json', 'expanded_models.json', 'baseline_models.json', 'learned_rule.json', 'dense_models.json')
    cases = audit.cohort_cases()
    assert len(cases) == 96 and cases[0]['name'] == 'v196_target_r00_00' and cases[-1]['seed'] == 1960295
