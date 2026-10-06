"""Synthetic geometry only: no swipes, spawns, fits or real cohorts."""
from collections import Counter
from copy import deepcopy
from math import sqrt

import pytest

from acfqp.science import controlled_predictive_merge_relations_v190 as core
from acfqp.science import controlled_predictive_shared_consequences_v179 as legacy


def record(board, aggregate=None):
    return dict(aggregate=[0., board.count(0), 0., 0., 0., 0.] if aggregate is None else aggregate,
        tokens=[['cell', i, rank] for i, rank in enumerate(board)]
        + [['horizontal', 4*r+c, board[4*r+c], board[4*r+c+1]] for r in range(4) for c in range(3)]
        + [['vertical', 4*r+c, board[4*r+c], board[4*(r+1)+c]] for r in range(3) for c in range(4)])


def vector(board, aggregate=None):
    return core.action_features_from_root(dict(layout_features={'DOWN': record(board, aggregate)}))['DOWN']


def pair(contract, first, second):
    return next(row for row in contract['equal_pairs'] if (row['first'], row['second']) == (first, second))


def test_column_order_physical_normalizers_and_outside_neighbors():
    board = [0]*16; board[5] = 11
    aggregate = [1., 15., 0., 0., 0., 0.]
    values = vector(board, aggregate)
    node = [1., 1/3., 2/3., 1/3., 2/3., 1., 1., 1., 1.]
    assert len(core.FEATURE_NAMES) == len(set(core.FEATURE_NAMES)) == len(values) == 98
    assert values[:6] == aggregate
    assert values[6:15] == pytest.approx([value/4. for value in node])
    assert values[15:48] == [0.]*33
    assert values[48:57] == pytest.approx([value/4. for value in node])
    assert values[57:90] == [0.]*33 and values[90:] == [0.]*8
    metadata = core.basis_metadata()
    assert metadata['node_normalizer'] == 4. and metadata['pair_normalizer'] == sqrt(120.)
    assert metadata['directions'] == ['LEFT', 'RIGHT', 'UP', 'DOWN']
    assert len(metadata['node_moments']) == 9 and len(metadata['pair_moments']) == 33
    assert core.FEATURE_NAMES[15] == 'rank_over_goal:pair:same_row'
    assert core.FEATURE_NAMES[36] == 'rank_over_goal:pair:packing_left_blocker_first'
    assert core.FEATURE_NAMES[44] == 'rank_over_goal:pair:once_pair_left'
    boundary = core.build_contract(record([5]+[0]*15))['nodes'][0]
    assert boundary['adjacent_zero'] == dict(LEFT=0, RIGHT=1, UP=0, DOWN=1)


def test_blocker_first_last_order_changes_the_used_projection_not_just_contract():
    first, second = [7, 3, 4, 7]+[0]*12, [7, 4, 3, 7]+[0]*12
    a, b = core.build_contract(record(first)), core.build_contract(record(second))
    pa, pb = pair(a, 0, 3), pair(b, 0, 3)
    assert pa['moments'][:21] == pb['moments'][:21]
    assert pa['projections']['UP']['blocker_ranks'] == [3, 4]
    assert pb['projections']['UP']['blocker_ranks'] == [4, 3]
    assert pa['projections']['DOWN']['blocker_ranks'] == [3, 4]  # Always perpendicular coordinates increasing.
    assert pa['moments'][25:27] == pytest.approx([3/11., 4/11.])
    assert pb['moments'][25:27] == pytest.approx([4/11., 3/11.])
    va, vb = vector(first), vector(second)
    index = core.FEATURE_NAMES.index('rank_over_goal:pair:packing_up_blocker_first')
    assert va[index] == pytest.approx((7/11.)*(3/11.)/sqrt(120.))
    assert vb[index] == pytest.approx((7/11.)*(4/11.)/sqrt(120.))
    assert va != vb


def test_cross_line_packing_retains_alignment_and_projected_blockers():
    board = [0]*16; board[1] = board[4] = 5
    contract = core.build_contract(record(board))
    relation = pair(contract, 1, 4)
    assert relation['moments'][:2] == [0., 0.] and relation['raw_blockers'] == []
    assert relation['moments'][13:17] == [1., 1., 1., 1.]
    for direction in core.DIRECTIONS:
        assert relation['projections'][direction]['aligned']
        assert relation['projections'][direction]['blocker_ranks'] == []
    blocked = [0]*16; blocked[2] = blocked[8] = 5; blocked[5] = 2
    blocked_relation = pair(core.build_contract(record(blocked)), 2, 8)
    assert blocked_relation['raw_blockers'] == []
    assert blocked_relation['moments'][13:17] == [0.]*4
    assert blocked_relation['moments'][17:21] == pytest.approx([2/22.]*4)
    for direction in core.DIRECTIONS:
        assert blocked_relation['projections'][direction]['blocker_ranks'] == [2]
    assert blocked_relation['projections']['LEFT']['first_position'] == 0
    assert blocked_relation['projections']['LEFT']['second_position'] == 8


def test_three_and_four_runs_pair_once_from_moving_end_without_merge_outputs():
    triple = core.build_contract(record([3, 3, 3, 0]+[0]*12))
    assert triple['once_pairs']['LEFT'] == [[0, 1]]
    assert triple['once_pairs']['RIGHT'] == [[1, 2]]
    assert triple['once_pairs']['UP'] == triple['once_pairs']['DOWN'] == []
    assert pair(triple, 0, 1)['moments'][29:33] == [1., 0., 0., 0.]
    assert pair(triple, 1, 2)['moments'][29:33] == [0., 1., 0., 0.]
    assert pair(triple, 0, 2)['moments'][29:33] == [0.]*4
    quadruple = core.build_contract(record([3, 3, 3, 3]+[0]*12))
    assert quadruple['once_pairs']['LEFT'] == [[0, 1], [2, 3]]
    assert {tuple(row) for row in quadruple['once_pairs']['RIGHT']} == {(0, 1), (2, 3)}
    assert pair(quadruple, 1, 2)['moments'][29:33] == [0.]*4
    assert len(quadruple['nodes']) == 4 and {node['rank'] for node in quadruple['nodes']} == {3}
    assert all(sorted(p for p in row['occupants'] if p is not None) == [0, 1, 2, 3]
               for row in quadruple['packing'].values())
    values = vector([3, 3, 3, 3]+[0]*12)
    index = core.FEATURE_NAMES.index('rank_over_goal:pair:once_pair_left')
    assert values[index] == pytest.approx(2*(3/11.)/sqrt(120.))


def test_low_rank_vacancy_neighbors_keep_direction_rank_and_boundary():
    board = [0]*16; board[5], board[6] = 1, 2
    expected = [0., .25, .25, 0., .25, .25, .25, .25]
    contract = core.build_contract(record(board))
    assert contract['vacancy_moments'] == expected and vector(board)[90:] == expected
    board[5], board[6] = 3, 4
    assert vector(board)[90:] == [0.]*8
    boundary = [1]+[0]*15
    assert vector(boundary)[90:] == [.25, 0., 0., 0., .25, 0., 0., 0.]


def test_two_numeric_rank_bases_share_relations_without_vocab_or_position_weights():
    low, high = [2, 2]+[0]*14, [3, 3]+[0]*14
    a, b = vector(low), vector(high)
    assert a[6] == pytest.approx(1/11.) and a[48] == 1/1024.
    assert b[6]/a[6] == pytest.approx(3/2.) and b[48]/a[48] == 2.
    assert a[15] == pytest.approx((2/11.)/sqrt(120.))
    assert b[57]/a[57] == 2.
    assert core.basis_metadata()['rank_bases'] == ['rank/11', '2^(rank-11)']
    assert 'vocabulary' not in core.basis_metadata()
    # Identical original six counts still have distinct shared relation columns.
    aggregate = [0., 14., 1., 0., 0., 0.]
    va, vb = vector(low, aggregate), vector(high, aggregate)
    assert va[:6] == vb[:6] and va[6:90] != vb[6:90]


def test_cache_is_label_free_and_does_not_repeat_contracts_or_ground_swipes(monkeypatch):
    class ForbiddenLabels(dict):
        def __getitem__(self, key):
            raise AssertionError('encoder consumed a consequence label')
    observed = dict(layout_features={'DOWN': record([3, 3, 0, 0]+[0]*12),
                                     'LEFT': record([7, 3, 4, 7]+[0]*12)},
                    action_components=ForbiddenLabels())
    original = deepcopy(observed['layout_features'])
    def forbidden(*args, **kwargs):
        raise AssertionError('relation encoding performed an unpaid swipe or rebuilt a cached contract')
    monkeypatch.setattr(legacy.ground, 'swipe_board_v1', forbidden)
    work = core.cache_roots([observed])
    assert observed['layout_features'] == original
    assert work['relation_contracts_built'] == 2 and work['relation_token_kind_reads'] == 80
    assert work['relation_cell_token_records_read'] == 32 and work['relation_feature_maps_derived'] == 1
    assert all(len(values) == 98 for values in observed['relation_features'].values())
    assert 'shared_ground_swipe_calls' not in work and 'layout_ground_swipe_calls' not in work
    monkeypatch.setattr(core, 'build_contract', forbidden)
    counts = Counter()
    cached = core.action_features_from_root(observed, counts)
    assert counts == dict(relation_feature_cache_hits=1, relation_cached_feature_reads=196)
    assert cached == observed['relation_features']
    cached['DOWN'][0] = -999.
    assert observed['relation_features']['DOWN'][0] != -999.
