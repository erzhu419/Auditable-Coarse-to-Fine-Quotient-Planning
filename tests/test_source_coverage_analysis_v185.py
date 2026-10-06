"""Pure expanded SOURCE fits and paired effects; no campaign boards or labels."""
from collections import Counter
from copy import deepcopy
import numpy as np
import pytest

from acfqp.science import controlled_predictive_source_coverage_v185 as core
from scripts import analyze_controlled_predictive_source_coverage_v185 as audit


def feature(rank, active):
    board = [rank]+[0]*15
    return dict(aggregate=[float(active), 0., 0., 0., 0., 0.],
        tokens=[['cell', i, value] for i, value in enumerate(board)]
        + [['horizontal', i, board[i], board[i+1]] for i in range(16) if i % 4 < 3]
        + [['vertical', i, board[i], board[i+4]] for i in range(12)])


def examples():
    rows = []
    for source in range(36):
        rows.append(dict(root_id=f'synthetic:{source:02d}', source_id=f'DESIGN_SOURCE:{source:02d}', life=0,
            canonical_board=[0]*16, legal_actions=['DOWN', 'LEFT'], immediate_rewards=dict(DOWN=0., LEFT=.25),
            fallback_action='LEFT', action_map=dict(DOWN='UP', LEFT='RIGHT'),
            layout_features=dict(DOWN=feature(1+source % 10, True), LEFT=feature(1+source % 10, False)),
            action_components=dict(DOWN=[1., .3, .7], LEFT=[.25, .5, .5]),
            teacher_action_native='UP', action_component_fractions={'unused': [[99, 1]]}))
    return rows


def test_36_source_fold_vocabulary_actual_utility_and_all_new_fit_counts(monkeypatch):
    rows = examples(); reference = core.fit_expanded(rows)
    choose, observations = audit.layout.choose_action, []
    def observable_only(model, root, counts=None):
        observations.append(set(root))
        assert not {'action_components', 'action_component_fractions', 'teacher_action_native'} & set(root)
        return choose(model, root, counts)
    monkeypatch.setattr(audit.layout, 'choose_action', observable_only)
    actual, work = audit.fit_expanded(rows)
    assert audit.same(reference, actual)
    assert reference['costs'] == actual['costs']
    assert len(observations) == 6*36 and actual['selection']['selected_lambda'] == 0.
    assert [len(fold) for fold in actual['selection']['source_folds']] == [18, 18]
    for fold in actual['selection']['folds']:
        assert set(fold['train_sources']).isdisjoint(fold['heldout_sources'])
        assert set(fold['design']['source_ids']) == set(fold['train_sources'])
    vocabulary = actual['selection']['folds'][0]['design']['vocabulary']
    assert ['cell', 0, 1] not in vocabulary and ['cell', 0, 2] in vocabulary
    assert any(choice['decision']['coverage']['LEFT']['unknown_tokens'] > 0
        for result in actual['selection']['candidates'][0]['fold_results'] for choice in result['choices'])
    assert actual['costs']['ridge_svd_decompositions'] == 3
    assert actual['costs']['ridge_coefficient_filters'] == 14
    assert actual['costs']['shared_lstsq_solves'] == 1 and actual['costs']['new_predictors_fitted'] == 15
    assert work['zero_minimum_norm_lstsq_solves']+work['positive_row_gram_solves'] == 14
    assert work['shared_six_column_lstsq_solves'] == 1


def test_shared_uses_same_complete_pair_labels_and_unit_weight_per_root():
    rows = examples(); tail = np.asarray([1., -.2, .2])
    for source, row in enumerate(rows):
        if source % 2:
            row['legal_actions'].append('UP'); row['immediate_rewards']['UP'] = .25
            row['layout_features']['UP'] = deepcopy(row['layout_features']['LEFT'])
            row['action_components']['UP'] = list(row['action_components']['LEFT']); row['action_map']['UP'] = 'LEFT'
    design = audit.ridge.prepare_design(rows); work = Counter()
    shared = audit.fit_shared(design, [design['source_ids'][::2], design['source_ids'][1::2]], work)
    assert np.asarray(shared['coefficients'])[0] == pytest.approx(tail)
    assert shared['rank'] == 1 and shared['loss'] < 1e-24
    assert len(shared['fit_residuals']) == 72
    assert all(sum(pair['weight'] for pair in label['pairs']) == pytest.approx(1.) for label in shared['fit_labels'])
    assert all(all(column < 6 for column, _ in row['design']) for row in shared['fit_residuals'])
    fitted, _, _ = audit.ridge.fit_design(design, 1., Counter())
    assert np.asarray(fitted['coefficients'])[0] == pytest.approx(tail*5/11)
    assert shared['fit_counts']['shared_lstsq_solves'] == work['shared_six_column_lstsq_solves'] == 1


def test_new_minus_old_paired_vectors_replica_losses_and_concentration():
    roots = dict(SOURCE=[dict(source_id=f'DESIGN_SOURCE:{i % 36:02d}') for i in range(143)], TARGET=[]); labels = []
    choices = {name: [] for name in (*audit.MODEL_NAMES, 'FALLBACK')}
    for index, (replica, gain) in enumerate(((0, 4.), (0, -1.), (1, -1.))):
        identity = f'synthetic:{index}'
        roots['TARGET'].append(dict(root_id=identity, replica=replica, stratum=index, legal_actions=['DOWN', 'LEFT']))
        labels.append(dict(root_id=identity, action_components=dict(DOWN=[1., 1., 0.], LEFT=[gain-.5, 0., .5])))
        for name, records in choices.items():
            records.append(dict(root_id=identity, canonical_action='LEFT' if name in ('RIDGE', 'SHARED') else 'DOWN', fallback=False,
                decision=dict(coverage={'LEFT': dict(total_tokens=40, known_tokens=39, unknown_tokens=1)})))
    summary = audit.summarize(roots, labels, choices, dict(selected_lambda=.1, candidates=[dict(lambda_value=.1, utility=.5)]))
    effect = summary['coverage_effects']['RIDGE_MINUS_OLD_RIDGE']
    assert effect['components'] == pytest.approx([-5/6, -1., .5]) and effect['utility'] == pytest.approx(2/3)
    assert (effect['improved_roots'], effect['worsened_roots'], effect['new_error_roots'], effect['resolved_error_roots']) == (1, 2, 2, 1)
    assert effect['positive_gain_sum'] == 4. and effect['negative_gain_sum'] == -2.
    assert effect['largest_gain_share_of_positive'] == 1.
    assert [row['effects']['RIDGE_MINUS_OLD_RIDGE']['utility'] for row in summary['replica_coverage_effects']] == [1.5, -1.]
    assert summary['coverage_effects']['LAYOUT_MINUS_OLD_LAYOUT']['equal_value_roots'] == 3
    assert summary['expanded']['comparisons']['RIDGE_MINUS_SHARED']['utility'] == 0.
