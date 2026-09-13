"""Tiny exact fixtures catch changed joint laws and incomplete emitted labels."""
from copy import deepcopy

from acfqp.science.controlled_predictive_symbolic_audit_v71 import audit


def fixture():
    boards = [(1, 2) * 8, (2, 1) * 8]
    full = dict(cells=[[0, 0, 'CUTOFF'], [1, 0, 'LOST'],
                       [2, 1, 'ACTIVE'], [3, 1, 'ACTIVE']],
                rows=[[s, 'go', [[1, 2, 0, 0, 1], [1, 2, 1, 1, 2]]] for s in (2, 3)],
                roots=[2], literal_boards=[[1, list(board), s] for board, s in zip(boards, (2, 3))])
    composed = dict(cells=full['cells'][:3], rows=full['rows'][:1], roots=[2])
    labels = [[1, list(board), 2] for board in boards]
    observations = [dict(board=list(boards[0]), horizon=1, expected=2, expected_full=2)]
    return full, composed, labels, observations


def test_complete_active_mapping_needs_no_terminal_board_labels():
    full, composed, labels, observations = fixture()
    result = audit(full, composed, deepcopy(composed), labels, observations)
    assert result['valid'] and result['frozen_core_exact']
    assert result['active_observations'] == result['active_routes_matched'] == 2
    assert result['portable_routes_matched'] == 1
    assert result['kernel_correspondence']['counts']['joint_rows_verified'] == 2


def test_joint_reward_successor_swap_fails_despite_preserved_marginals():
    full, composed, labels, observations = fixture()
    changed = deepcopy(composed)
    changed['rows'][0][2][0][3:] = [1, 2]
    changed['rows'][0][2][1][3:] = [0, 1]
    result = audit(full, composed, changed, labels, observations)
    assert not result['valid'] and not result['frozen_core_exact']
    assert result['differing_core_fields'] == ['rows']
    assert result['kernel_correspondence']['errors']['unmatched_full_contract'] == 2


def test_support_omission_extra_duplicate_and_wrong_cell_are_visible():
    full, composed, labels, observations = fixture()
    bad_labels = [labels[0], [1, labels[0][1], 0], [1, [3] * 16, 2]]
    result = audit(full, composed, deepcopy(composed), bad_labels, observations)
    assert result['kernel_correspondence']['valid'] and not result['valid']
    assert result['missing_observations'] == result['extra_observations'] == 1
    assert result['errors']['duplicate_candidate_observation'] == 1
    assert result['errors']['candidate_layer_or_status_difference'] == 1
    assert result['errors']['active_route_difference'] == 2
