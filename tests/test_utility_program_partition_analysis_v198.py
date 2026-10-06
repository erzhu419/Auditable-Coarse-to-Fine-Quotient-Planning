"""Independent utility-induced partitions, global context and frozen flow."""
from collections import Counter
from copy import deepcopy

import numpy as np
import pytest

from scripts import analyze_controlled_predictive_utility_program_partition_v198 as audit


def contract(value=0., context=0.):
    values = [0.]*81; values[1], values[4] = float(value), float(context)
    return dict(goal_now=False, values=values)


def root(name='query', source=0):
    return dict(root_id=name, source_id=f'DESIGN_SOURCE:{source:02d}', life=0, canonical_board=[0]*16,
        legal_actions=['DOWN', 'LEFT'], immediate_rewards=dict(DOWN=0., LEFT=0.), fallback_action='LEFT',
        action_map=dict(DOWN='UP', LEFT='RIGHT', RIGHT='LEFT', UP='DOWN'), raw_afterstates=dict(DOWN=[0]*16, LEFT=[0]*16),
        program_contracts=dict(DOWN=contract(0), LEFT=contract(1)),
        action_components=dict(DOWN=[0., 1., 0.], LEFT=[.1, 0., 0.]))


def fit(rows, depth=1, support=4):
    library = audit.previous.prepare_library(rows, 'FULL'); view = audit.prepare_training_view(rows, library)
    counts = Counter(); model = audit.model_from_tree(library, view, depth, support, counts)
    return model, library, view, counts


def supplied_libraries(rows):
    sources = sorted({row['source_id'] for row in rows})
    libraries = {f'FOLD_{fold}': audit.previous.prepare_library(
        [row for row in rows if row['source_id'] not in sources[fold::2]], f'FOLD_{fold}') for fold in range(2)}
    libraries['FULL'] = audit.previous.prepare_library(rows, 'FULL')
    return libraries


def test_actual_utility_selects_a_decision_condition_instead_of_sse_orientation():
    rows = [root(f'condition:{i}', i//2) for i in range(8)]
    for i, row in enumerate(rows):
        good = bool(i%2); reward = .7 if i < 4 else .9; value = .6 if good else .1
        row['program_contracts'] = {'DOWN': contract(), 'LEFT': contract()}
        row['program_contracts']['DOWN']['values'][4] = 1. if i < 4 else 2.
        row['program_contracts']['DOWN']['values'][8] = 2. if good else 1.
        row['immediate_rewards'] = dict(DOWN=0., LEFT=.35)
        row['action_components'] = dict(DOWN=[reward, reward-value, 0.], LEFT=[.35, 0., 0.])
    model, library, _, counts = fit(rows)
    sse = audit.previous.build_tree(library, 1, 4, list(range(162)))
    tree = model['tree']
    assert sse['feature'] == 4 and sse['threshold'] == 0.
    assert tree['feature'] == 8 and tree['threshold'] == 1.
    assert tree['training_utility_before'] == pytest.approx(.35)
    assert tree['training_utility_after'] == pytest.approx(.475) and tree['improvement'] == pytest.approx(.125)
    actions = [audit.previous.choose_action(model, audit.previous.observable(row), library)['canonical_action'] for row in rows]
    assert actions == ['LEFT', 'DOWN']*4
    assert counts['tree_best_candidate_array_copies'] == 4*len(rows)*counts['tree_best_candidate_updates']
    assert counts['training_decoder_epsilon_checks'] == 4*counts['training_root_decisions']


def test_strict_no_gain_stops_even_with_component_variation_and_sse_gain():
    rows = [root(f'plateau:{i}', i//2) for i in range(4)]
    for row in rows:
        row['action_components'] = dict(DOWN=[1., 1., 0.], LEFT=[0., 0., 0.])
    model, library, view, counts = fit(rows, depth=6)
    assert audit.previous.build_tree(library, 6, 4, list(range(162)))['kind'] == 'split'
    assert model['tree']['kind'] == 'leaf'
    assert counts['tree_supported_split_candidates'] > 0 and counts.get('tree_splits_built', 0) == 0
    assert audit.training_utility(np.zeros((4, 4, 3)), view, Counter()) == 0.
    assert model['tree']['mean'] == [0., 0., 0.]


def test_preorder_keeps_whole_tree_context_and_installs_both_prefix_means():
    rows = [root(f'context:{i:02d}', i//2) for i in range(8)]
    for i, row in enumerate(rows):
        context = float(i >= 4)
        row['program_contracts'] = dict(DOWN=contract(0, context), LEFT=contract(1, context))
        row['action_components'] = dict(DOWN=[.5, 0., 0.] if context else [0., 1., 0.], LEFT=[0., 0., 0.])
    model, library, _, _ = fit(rows, depth=2)
    tree = model['tree']
    assert tree['feature'] == 1 and tree['training_utility_before'] == pytest.approx(-.25)
    assert tree['training_utility_after'] == pytest.approx(0.)
    assert tree['left']['kind'] == 'split' and tree['left']['feature'] == 4
    assert tree['left']['training_utility_before'] == pytest.approx(0.)
    assert tree['left']['training_utility_after'] == pytest.approx(.25)
    assert tree['right']['kind'] == 'leaf'
    actions = [audit.previous.choose_action(model, audit.previous.observable(row), library)['canonical_action'] for row in rows]
    assert actions == ['LEFT']*4+['DOWN']*4
    assert tree['left']['left']['mean'] == pytest.approx([0., 1., 0.])
    assert tree['left']['right']['mean'] == pytest.approx([.5, 0., 0.])
    assert tree['right']['mean'] == pytest.approx([-.25, -.5, 0.])


def test_ordered_incidence_matches_full_three_and_four_action_decode_with_forced_weights():
    for action_count in (3, 4):
        rows = [root('a', 0), root('b', 1), root('c', 1)]
        legal = list(audit.ACTIONS[:action_count])
        for row in rows[:2]:
            row['legal_actions'] = legal
            row['program_contracts'] = {a: contract(i) for i, a in enumerate(legal)}
            row['immediate_rewards'] = {a: .05*(i+1) for i, a in enumerate(legal)}
            row['action_components'] = {a: [.3*i, .1*i, .2*i] for i, a in enumerate(legal)}
        rows[-1]['legal_actions'] = ['DOWN']; rows[-1]['action_components'] = {'DOWN': [2., 0., 0.]}
        library = audit.previous.prepare_library(rows, 'FULL'); counts = Counter(); view = audit.prepare_training_view(rows, library, counts)
        assert view['root_weights'].tolist() == [.5, .25, .25] and counts['training_view_forced_roots'] == 1
        left = [i for i, row in enumerate(library['prototypes']) if row['features162'][1] <= 0.]
        right = [i for i in range(len(library['prototypes'])) if i not in left]
        mean, first, second = np.asarray([.05, .03, .07]), np.asarray([-.3, .4, -.2]), np.asarray([.5, -.1, .6])
        theta = audit.incidence(view, left, Counter())[:, :, None]*(first-mean)+audit.incidence(view, right, Counter())[:, :, None]*(second-mean)
        model = dict(mode='UTILITY', input_columns=list(range(162)), tree=dict(kind='split', feature=1, threshold=0.,
            left=dict(kind='leaf', node_id=1, mean=first.tolist()), right=dict(kind='leaf', node_id=2, mean=second.tolist())))
        selected = audit.training_actions(theta, view); actual = []
        for i, row in enumerate(rows):
            decision = audit.previous.choose_action(model, audit.previous.observable(row), library)
            assert audit.ACTIONS[selected[i]] == decision['canonical_action']
            for a in row['legal_actions']:
                vector = theta[i, audit.ACTIONS.index(a)].copy(); vector[0] += row['immediate_rewards'][a]
                assert decision['predicted_components'][a] == pytest.approx(vector.tolist(), abs=audit.EPS)
            actual.append(audit.utility(row['action_components'][decision['canonical_action']]))
        assert audit.training_utility(theta, view, Counter()) == pytest.approx(np.sum(view['root_weights']*actual))
        zero = np.zeros_like(theta); view['rewards'][0] = 0.; view['rewards'][0, 1] = audit.EPS/2
        assert audit.training_actions(zero, view)[0] == 0
        view['rewards'][0, 1] = 2*audit.EPS
        assert audit.training_actions(zero, view)[0] == 1


def test_source_cv_only_new_seventeen_fits_without_source_trace_or_library_rebuild(monkeypatch):
    rows = [root(f'cv:{source:02d}:{i}', source) for source in range(36) for i in range(3 if source == 3 else 4)]
    libraries = supplied_libraries(rows); before_rows, before_libraries = deepcopy(rows), deepcopy(libraries)
    def forbidden(*args, **kwargs):
        raise AssertionError('settled SOURCE work must not be repeated')
    for name in ('fit_models', 'prepare_library', 'cache_roots'):
        monkeypatch.setattr(audit.previous, name, forbidden)
    original, calls = audit.previous.decision_from_query, Counter()
    def label_free(model, observed, library, query, counts):
        assert 'action_components' not in observed and 'teacher_action_native' not in observed
        calls['decisions'] += 1
        return original(model, observed, library, query, counts)
    monkeypatch.setattr(audit.previous, 'decision_from_query', label_free)
    fitted = audit.fit_models(rows, libraries); selection, counts = fitted['selection']['UTILITY'], fitted['costs']
    assert rows == before_rows and libraries == before_libraries and set(fitted) == {'models', 'selection', 'costs'}
    assert selection['selected_depth'] == 1 and selection['selected_min_leaf_roots'] == 4
    assert selection['selected_utility'] == pytest.approx(.1) and calls['decisions'] == 8*143
    assert counts['tree_fit_attempts'] == counts['tree_predictors_fitted'] == counts['new_predictors_fitted'] == 17
    assert counts['UTILITY_tree_fit_attempts'] == counts['UTILITY_tree_predictors_fitted'] == 17
    assert counts['training_view_preparations'] == counts['training_matrix_preparations'] == 3 and counts['training_view_roots'] == 286
    assert counts['training_matrix_cells'] == sum(162*len(library['prototypes']) for library in libraries.values())
    assert counts['query_input_roots'] == 143 and counts['shared_library_preparations'] == counts['neighbor_predictor_configurations'] == 0
    assert counts['heldout_action_vector_reads'] == 8*143
    assert all(set(fold['train_sources']).isdisjoint(fold['heldout_sources']) for fold in selection['folds'])
    assert fitted['models']['UTILITY']['native_teacher_query'] == 'goal_1_risk_1' and fitted['models']['UTILITY']['horizon'] == 3


def test_tampered_new_partition_action_and_exact_reused_source_binding_rejected():
    rows = [root(f'tamper:{i}', i//2) for i in range(4)]; model, library, _, _ = fit(rows)
    tree = model['tree']; assert tree['kind'] == 'split'
    changed = deepcopy(tree); changed['threshold'] += 1e-12
    assert audit.close(changed, tree) and not audit.previous.tree_identity(changed, tree)
    changed = deepcopy(tree); changed['left']['prototype_indices'].reverse()
    assert not audit.previous.tree_identity(changed, tree)
    changed = deepcopy(model); changed['tree']['left']['mean'][1] += .01
    assert not audit.close(changed, model)
    query = root(); query['action_components'] = {'forbidden_TARGET_label': [999., 999., 999.]}
    decision = audit.previous.choose_action(model, audit.previous.observable(query), library)
    altered = deepcopy(decision); altered['canonical_action'] = 'DOWN'
    assert decision['canonical_action'] == 'LEFT' and not audit.previous.verify_decision(altered, decision)
    retained = dict(SOURCE={'modes': {mode: {'actual': {'utility': 1.2}} for mode in audit.previous.MODES}},
        projection_residuals={'SOURCE': {mode: {'pairs': 10} for mode in audit.previous.MODES}})
    summary = deepcopy(retained); summary['SOURCE_reuse'] = dict(retained_modes=list(audit.previous.MODES),
        summary_ref='inputs/inherited/v197_summary.json', selection_ref='inputs/inherited/v196_selection.json', fields=['SOURCE.modes', 'projection_residuals.SOURCE'])
    assert audit.source_reuse_binding(summary, retained)
    summary['SOURCE']['modes']['PROGRAM']['actual']['utility'] += 1e-12
    assert audit.close(summary['SOURCE'], retained['SOURCE']) and not audit.source_reuse_binding(summary, retained)

