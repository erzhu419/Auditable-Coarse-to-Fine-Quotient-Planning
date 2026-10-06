"""Three synthetic witnesses for the independent ranking auditor; no acquisition."""
from copy import deepcopy
from itertools import combinations
import math

import numpy as np
import pytest
from scipy.sparse import csr_matrix

from scripts import analyze_controlled_predictive_action_ranking_v186 as audit


def cached_layout(aggregate=None, rank=0):
    board = [rank]*16
    tokens = [['cell', cell, value] for cell, value in enumerate(board)]
    tokens += [['horizontal', 4*row+column, board[4*row+column], board[4*row+column+1]]
               for row in range(4) for column in range(3)]
    tokens += [['vertical', 4*row+column, board[4*row+column], board[4*(row+1)+column]]
               for row in range(3) for column in range(4)]
    return dict(aggregate=list(aggregate or [0.]*6), tokens=tokens)


def frozen_reference(rows):
    action_ids = {action: sorted(row['root_id'] for row in rows if action in row['legal_actions'])
                  for action in audit.ACTIONS}
    pair_ids = {f'{first}|{second}': sorted(row['root_id'] for row in rows
                if first in row['legal_actions'] and second in row['legal_actions'])
                for first, second in combinations(audit.ACTIONS, 2)}
    return dict(life=0, root_ids=sorted(row['root_id'] for row in rows),
        vocabulary=sorted(cached_layout()['tokens'], key=tuple), action_root_ids=action_ids,
        pair_root_ids=pair_ids, connected_components=[list(audit.ACTIONS)])


def test_preparation_rebuilds_full_vector_offsets_ties_weights_and_frozen_design():
    from acfqp.science import controlled_predictive_action_ranking_v186 as core

    rows = [
        dict(root_id='synthetic:a', source_id='source:0', life=0,
            legal_actions=['UP', 'RIGHT', 'LEFT', 'DOWN'],
            immediate_rewards=dict(DOWN=.5, LEFT=.875, RIGHT=.125, UP=.75),
            action_components=dict(DOWN=[1., .5, .25], LEFT=[1.+audit.EPS/2, .5, .25],
                                   RIGHT=[1.5, 1., 0.], UP=[1., .75, 0.]),
            layout_features=dict(DOWN=cached_layout([1., 2., 3., 4., 5., 6.]),
                LEFT=cached_layout([6., 5., 4., 3., 2., 1.]),
                RIGHT=cached_layout([0., 1., 1., 1., 1., 1.]),
                UP=cached_layout([2., 0., 0., 0., 0., 0.], rank=9))),
        dict(root_id='synthetic:b', source_id='source:0', life=0,
            legal_actions=['LEFT', 'DOWN'], immediate_rewards=dict(DOWN=.375, LEFT=.125),
            action_components=dict(DOWN=[1., 1., 0.], LEFT=[.5, 0., 0.]),
            layout_features=dict(DOWN=cached_layout([0., 1., 0., 0., 0., 0.]),
                                 LEFT=cached_layout([1., 0., 0., 0., 0., 0.]))),
        dict(root_id='synthetic:c', source_id='source:1', life=0,
            legal_actions=['LEFT', 'DOWN'], immediate_rewards=dict(DOWN=0., LEFT=0.),
            action_components=dict(DOWN=[.5, .25, .25], LEFT=[.625, .25, .125]),
            layout_features=dict(DOWN=cached_layout(), LEFT=cached_layout())),
        dict(root_id='synthetic:d', source_id='source:1', life=0,
            legal_actions=['UP'], immediate_rewards=dict(UP=0.),
            action_components=dict(UP=[0., 0., 1.]), layout_features=dict(UP=cached_layout())),
    ]
    reference = frozen_reference(rows)
    before = deepcopy(reference)
    # Misleading scalar labels do not replace complete reward/failure/success vectors.
    for row in rows:
        row['oracle_action'] = row['teacher_action_native'] = 'UP'
    examples = list(reversed(rows))+[dict(life=1, root_id='other-teacher')]
    design = audit.prepare_ranking(examples, reference)
    production = core.prepare_ranking(examples, reference)
    saved = {key: value for key, value in design.items() if key not in ('D', 'targets', 'weights')}
    production_saved = {key: value for key, value in production.items() if key not in ('D', 'targets', 'weights')}
    assert audit.same(saved, production_saved) and audit.same(production_saved, saved)
    assert reference == before
    for key in ('vocabulary', 'root_ids', 'action_root_ids', 'pair_root_ids', 'connected_components'):
        assert design[key] == before[key]
    assert design['root_count'] == 4 and design['shape'] == [3, 46]
    records = design['root_records']
    assert records[0]['legal_actions'] == list(audit.ACTIONS)
    assert records[0]['best_action'] == 'DOWN'
    assert records[0]['tied_actions'] == ['DOWN', 'LEFT']
    assert records[0]['loser_actions'] == ['RIGHT', 'UP'] and records[0]['rows'] == [0, 1]
    assert records[1]['best_action'] == 'LEFT'
    assert records[2]['tied_actions'] == ['DOWN', 'LEFT'] and records[2]['rows'] == []
    assert records[3]['tied_actions'] == ['UP'] and records[3]['rows'] == []
    assert [row['utility_gap'] for row in design['rows']] == pytest.approx([.25, .5, .5])
    assert [row['immediate_reward_gap'] for row in design['rows']] == pytest.approx([.375, -.25, -.25])
    assert design['targets'].tolist() == pytest.approx([-.125, .75, .75])
    assert design['weights'].tolist() == [.5, .5, 1.]
    expected = np.zeros((3, 46))
    expected[0, :6] = [1., 1., 2., 3., 4., 5.]
    expected[1, :6] = [-1., 2., 3., 4., 5., 6.]
    expected[1, 6:] = [.25 if token[0] == 'cell' else 1/math.sqrt(12)
                        for token in before['vocabulary']]
    expected[2, :2] = [1., -1.]
    assert audit.same(design['D'].toarray().tolist(), expected.tolist())
    assert design['D'].indptr.tolist() == [0, 6, 52, 54]
    assert design['D'].indptr.tolist() == production['D'].indptr.tolist()
    assert design['D'].indices.tolist() == production['D'].indices.tolist()
    assert design['D'].data.tolist() == pytest.approx(production['D'].data.tolist())
    assert design['targets'].tolist() == pytest.approx(production['targets'].tolist())
    assert design['weights'].tolist() == production['weights'].tolist()
    # Both K=0 roots still contribute to N=4 in the mean-root loss.
    assert audit.loss_gradient(np.zeros(46), design)[0] == pytest.approx(27/128)
    assert design['work'] == dict(vocabulary_entries_indexed=40, ranking_examples_examined=5,
        ranking_other_life_excluded=1, ranking_root_labels_read=4, ranking_legal_action_reads=9,
        ranking_full_component_reads=27, ranking_immediate_reward_reads=9, token_lookups=360,
        known_token_entries=320, token_weight_loads=320, unknown_token_entries=40,
        encoded_actions=9, aggregate_values_read=54, ranking_loser_pairs=3,
        ranking_design_value_reads=276, ranking_design_subtractions=138,
        ranking_sparse_design_entries=54, ranking_utility_gap_subtractions=3,
        ranking_reward_gap_subtractions=3, ranking_target_subtractions=3,
        ranking_utility_evaluations=9, ranking_best_comparisons=5, ranking_tie_tests=9,
        ranking_loser_tests=9, ranking_roots_prepared=4, ranking_csr_matrices=1,
        ranking_csr_stored_values=54)


def test_dual_certificate_accepts_analytic_active_set_and_rejects_tampered_beta():
    design = dict(D=csr_matrix([[1., 0.], [1., 1.], [-1., 0.]]),
        targets=np.asarray([1., .5, -2.]), weights=np.asarray([1., .5, 1.]),
        root_count=4, rows=[{}, {}, {}], lambda_value=.1)
    beta = [5/7, 0.]
    certificate = audit.dual_certificate(design, beta)
    assert certificate['accepted'] is True
    assert certificate['alpha'] == pytest.approx([1/7, 0., 0.], abs=1e-12)
    assert certificate['beta_dual'] == pytest.approx(beta, abs=1e-12)
    assert certificate['primal_objective'] == pytest.approx(1/14, abs=1e-12)
    assert certificate['dual_lower_bound'] == pytest.approx(1/14, abs=1e-12)
    assert certificate['primal_dual_gap'] == pytest.approx(0., abs=1e-12)
    assert certificate['primal_gradient'] == pytest.approx([0., 0.], abs=1e-12)
    assert certificate['primal_gradient_inf'] <= 1e-12
    assert certificate['kkt_residual'] == pytest.approx([0., 3/14, 9/7], abs=1e-12)
    assert certificate['dual_kkt_inf'] <= 1e-12
    assert certificate['coefficient_l2_difference'] <= 1e-12
    gap_bound = math.sqrt(max(certificate['primal_dual_gap'], 0.)/.1)
    gradient_bound = (np.linalg.norm(certificate['primal_gradient'])
                      +np.linalg.norm(certificate['dual_beta_gradient']))/.2
    assert certificate['gap_coefficient_distance_bound'] == pytest.approx(gap_bound)
    assert certificate['gradient_coefficient_distance_bound'] == pytest.approx(gradient_bound)
    assert certificate['coefficient_l2_bound'] == pytest.approx(max(gap_bound, gradient_bound)+1e-8)
    assert certificate['coefficient_l2_difference'] <= certificate['coefficient_l2_bound']
    assert certificate['costs'] == dict(dual_row_gram_matrices=1, dual_row_gram_cells=9,
        dual_hessian_diagonal_entries=3, dual_cholesky_decompositions=1,
        dual_cholesky_cells=9, dual_triangular_solves=1, dual_rhs_values=3,
        dual_nnls_attempts=1, dual_nnls_returns=1, dual_nnls_matrix_cells=9,
        dual_nnls_target_values=3, independent_loss_gradient_calls=2,
        independent_sparse_value_products=16, independent_hinge_values=6,
        independent_gradient_values=4, dual_nonnegative_multiplier_checks=3,
        dual_kkt_values=3, dual_coefficient_values=2, dual_gradient_norm_values=4,
        dual_coefficient_distance_values=2, dual_gap_evaluations=1)
    damaged = audit.dual_certificate(design, [.9, 0.])
    assert damaged['accepted'] is False
    assert damaged['alpha'] == pytest.approx(certificate['alpha'], abs=1e-12)
    assert damaged['primal_objective'] == pytest.approx(167/2000)
    assert damaged['primal_gradient'] == pytest.approx([.13, 0.], abs=1e-12)
    assert damaged['primal_dual_gap'] == pytest.approx(169/14000)
    assert damaged['coefficient_l2_difference'] == pytest.approx(13/70)

    # A fixed loss of 16 hides an O(1e-16) objective gap in floating subtraction.
    # The coefficient witness remains valid even when that gap rounds to zero.
    cancellation = dict(D=csr_matrix([[1., 0.], [1., 1.], [-1., 0.], [0., 0.]]),
        targets=np.asarray([1., .5, -2., 8.]), weights=np.asarray([1., .5, 1., 1.]),
        root_count=4, rows=[{}, {}, {}, {}], lambda_value=.1)
    near = audit.dual_certificate(cancellation, [5/7+2e-8, 0.])
    assert near['accepted'] is True
    assert near['alpha'] == pytest.approx([1/7, 0., 0., 4.], abs=1e-12)
    assert near['beta_dual'] == pytest.approx(beta, abs=1e-12)
    assert near['primal_objective'] == pytest.approx(16+1/14, abs=1e-12)
    assert near['primal_dual_gap'] == pytest.approx(0., abs=1e-12)
    assert near['primal_gradient'] == pytest.approx([1.4e-8, 0.], abs=1e-12)
    assert near['primal_gradient_inf'] <= 1e-7 and near['dual_kkt_inf'] <= 1e-7
    assert near['coefficient_l2_difference'] == pytest.approx(2e-8, abs=1e-12)
    unsafe_zero_gap_bound = math.sqrt(max(0., 0.)/.1)+1e-8
    assert unsafe_zero_gap_bound < near['coefficient_l2_difference']
    assert near['gradient_coefficient_distance_bound'] >= near['coefficient_l2_difference']
    assert near['coefficient_l2_bound'] >= near['gradient_coefficient_distance_bound']
    assert near['coefficient_l2_difference'] <= near['coefficient_l2_bound']


def test_scalar_decisions_and_summary_use_observable_offsets_and_actual_full_vectors():
    from acfqp.science import controlled_predictive_action_ranking_v186 as core

    model = dict(life=0, vocabulary=sorted(cached_layout()['tokens'], key=tuple),
        coefficients=[1.]+[0.]*45,
        action_root_ids={action: ['support:0', 'support:1', 'support:2', 'support:3']
                         for action in audit.ACTIONS},
        pair_root_ids={f'{first}|{second}': ['support:0', 'support:1', 'support:2', 'support:3']
                       for first, second in combinations(audit.ACTIONS, 2)},
        connected_components=[list(audit.ACTIONS)],
        predicted_components=dict(DOWN=[100., 0., 1.], LEFT=[0., 1., 0.]))
    current = dict(life=0, legal_actions=['LEFT', 'DOWN'],
        immediate_rewards=dict(DOWN=.25, LEFT=1.5), fallback_action='LEFT',
        action_map=dict(DOWN='UP', LEFT='RIGHT'),
        layout_features=dict(DOWN=cached_layout([1., 0., 0., 0., 0., 0.]), LEFT=cached_layout()),
        action_components=dict(DOWN=[100., 0., 1.], LEFT=[0., 1., 0.]))
    decision = audit.choose_action(model, current)
    assert audit.same(decision, core.choose_action(model, current))
    assert decision['canonical_action'] == 'LEFT' and decision['actual_action'] == 'RIGHT'
    assert decision['predicted_utilities'] == pytest.approx(dict(DOWN=1.25, LEFT=1.5))
    assert decision['predicted_pair_utilities'] == pytest.approx({'DOWN|LEFT': -.25})
    assert 'predicted_components' not in decision and 'predicted_pair_components' not in decision
    assert decision['fallback'] is False
    stronger = deepcopy(model); stronger['coefficients'][0] = 2.
    assert audit.choose_action(stronger, current)['canonical_action'] == 'DOWN'
    stronger['action_root_ids']['LEFT'] = ['support:0', 'support:1', 'support:2']
    fallback = audit.choose_action(stronger, current)
    assert fallback['fallback'] is True and fallback['reason'] == 'insufficient_action_support'
    assert fallback['canonical_action'] == 'LEFT' and fallback['actual_action'] == 'RIGHT'
    disconnected = deepcopy(model); disconnected['connected_components'] = [[action] for action in audit.ACTIONS]
    separated = audit.choose_action(disconnected, current)
    assert separated['fallback'] is True and separated['reason'] == 'disconnected_required_actions'
    assert separated['canonical_action'] == 'LEFT' and separated['predicted_pair_utilities'] == {}

    roots = dict(SOURCE=[dict(source_id=f'source:{index//2}') for index in range(4)], TARGET=[])
    labels, choices = [], {name: [] for name in (*audit.MODEL_NAMES, 'FALLBACK')}
    for index, (replica, gain) in enumerate(((0, 4.), (0, -1.), (0, 0.), (1, -1.))):
        identity = f'synthetic-target:{index}'
        roots['TARGET'].append(dict(root_id=identity, replica=replica, stratum=index,
                                    legal_actions=['DOWN', 'LEFT']))
        labels.append(dict(root_id=identity, oracle_action='LEFT',
                           action_components=dict(DOWN=[2., .5, 0.], LEFT=[gain+1., 0., .5])))
        for name, selected in choices.items():
            coverage = dict(DOWN=dict(total_tokens=40, known_tokens=39, unknown_tokens=1),
                            LEFT=dict(total_tokens=40, known_tokens=38, unknown_tokens=2))
            selected.append(dict(root_id=identity, canonical_action='LEFT' if name == 'RANK' else 'DOWN',
                fallback=name == 'RANK' and index == 1,
                decision=dict(coverage=coverage if name == 'RANK' else {},
                              predicted_utilities=dict(DOWN=100., LEFT=-100.))))
    fit = dict(design=dict(rows=[{}, {}, {}]), objective=.125, gradient_inf=2e-9,
               objective_gap_upper_bound=1e-12)
    result = audit.summarize(roots, labels, choices, fit)
    assert result['schema'] == 'acfqp.action_ranking.v186.summary' and result['complete'] is True
    assert result['roots'] == 4
    assert result['SOURCE'] == dict(roots=4, design_groups=2, lambda_value=.1,
        ranking_pairs=3, objective=.125, gradient_inf=2e-9, objective_gap_upper_bound=1e-12)
    assert set(result['models']) == set((*audit.MODEL_NAMES, 'FALLBACK', 'ORACLE'))
    assert result['models']['RANK']['components'] == pytest.approx([1.5, 0., .5])
    assert result['models']['RANK']['utility'] == pytest.approx(2.)
    assert result['models']['RANK']['positive_regret_roots'] == 2
    assert result['models']['RANK']['fallback_roots'] == 1
    assert result['models']['RIDGE']['components'] == pytest.approx([2., .5, 0.])
    assert result['models']['ORACLE']['components'] == pytest.approx([11/4, 3/8, 1/8])
    assert result['root_records'][2]['models']['ORACLE']['action'] == 'DOWN'
    assert result['root_records'][0]['models']['RANK']['components'] == [5., 0., .5]
    assert set(result['comparisons']) == {'RANK_MINUS_'+name for name in ('RIDGE', 'LAYOUT', 'SHARED', 'OLD_SHARED', 'ONE')}
    for effect in result['comparisons'].values():
        assert effect['components'] == pytest.approx([-.5, -.5, .5])
        assert effect['utility'] == pytest.approx(.5)
        assert (effect['improved_roots'], effect['worsened_roots'], effect['equal_value_roots']) == (1, 2, 1)
        assert (effect['action_changes'], effect['new_error_roots'], effect['resolved_error_roots']) == (4, 2, 1)
        assert (effect['positive_gain_sum'], effect['negative_gain_sum']) == pytest.approx((4., -2.))
        assert effect['largest_gain_root'] == 'synthetic-target:0' and effect['largest_gain'] == 4.
        assert effect['largest_gain_share_of_positive'] == 1.
        assert effect['largest_loss_root'] == 'synthetic-target:1' and effect['largest_loss'] == -1.
        assert [row['utility'] for row in effect['root_records']] == pytest.approx([4., -1., 0., -1.])
    assert [(row['replica'], row['roots']) for row in result['replicas']] == [(0, 3), (1, 1)]
    assert [row['comparisons']['RANK_MINUS_RIDGE']['utility'] for row in result['replicas']] == pytest.approx([1., -1.])
    assert result['whole_cohort_positive_vs_ridge_and_old_shared'] is True
    assert result['all_replicas_positive_vs_ridge_and_old_shared'] is False
    assert result['oracle_minus_one'] == pytest.approx(1.)
    assert result['oracle_minus_rank'] == pytest.approx(.5)
    assert result['headroom_closed_fraction'] == pytest.approx(.5)
    assert result['feature_coverage'] == dict(total_tokens=320, known_tokens=308, unknown_tokens=12)
    assert (result['new_environment_samples'], result['new_source_games'],
            result['new_native_weight_updates'], result['new_predictors_fitted']) == (0, 0, 0, 1)
