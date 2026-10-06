"""Exact board support, coupled leaf selection and unchanged native H2/world order."""
from fractions import Fraction
from pathlib import Path

import numpy as np
import pytest

from acfqp.domains import standard_2048 as ground
from acfqp.science.controlled_predictive_ntuple_td_v120 import NtupleValue, ACTIONS
from acfqp.science.controlled_predictive_online_query_td_v131 import QueryTD
from acfqp.science.controlled_predictive_paired_ntuple_v130 import QueryParent
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics, RewriteProgram
from acfqp.science.native_localized_value_v318 import support_from_dataset, choose_localized, evaluate_localized
from acfqp.science.native_split_risk_v301 import SplitLeaf, predict_components, evaluate_split

BUILD = Path(__file__).resolve().parents[1] / 'reports/retention_mechanism_v318/runtime/tests/native'
QUERY = dict(reward_weight=1., failure_penalty=4., goal_bonus=4.)
BOARD = (1, 2, 0, 0, 0, 1, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0)


def heads():
    rule = LearnedDynamics(RewriteProgram(True, 'equal', 1, 'once', 'output_value'),
        ((1, Fraction(9, 10)), (2, Fraction(1, 10))), 'uniform', 4)
    template = QueryTD(QueryParent(NtupleValue(rule, BUILD), QUERY, QUERY, .5), 'PRIOR', BUILD)
    template.freeze()
    base, updated = SplitLeaf(template, 'LOCAL_RISK', BUILD), SplitLeaf(template, 'LOCAL_RISK', BUILD)
    index = np.arange(base.reward_weights.size).reshape(base.reward_weights.shape)
    base.reward_weights[:] = index % 7 * .002
    base.risk_weights[:] = -(index % 5) * .01
    updated.reward_weights[:] = .05 + index % 9 * .001
    updated.risk_weights[:] = .06 + index % 3 * .001
    base.updates, updated.updates = 7, 11
    base.freeze(); updated.freeze()
    return base, updated


def code(board):
    return sum(int(rank) << (4 * cell) for cell,rank in enumerate(board))


def make_support(rows):
    rows = list(rows)
    return support_from_dataset(dict(afterstates=np.asarray(rows + [[10] + [0] * 15], dtype=np.int32),
        ends=np.asarray([len(rows), len(rows) + 1], dtype=np.int64),
        fit_game_count=1, fit_step_end=len(rows)))


def literal_h2(base, updated, query, p, keys):
    values, predicted = {}, []
    if max(query) >= base.radix:
        return None, values, 4., predicted
    for action in ACTIONS:
        after, score, changed = ground.swipe_board_v1(query, ground.Swipe2048Action(action))
        if not changed:
            continue
        if max(after) >= base.radix:
            tail = 4.
        else:
            empty = [cell for cell,rank in enumerate(after) if rank == 0]
            tail = 0.
            for cell in empty:
                for rank in (1, 2):
                    spawned = list(after); spawned[cell] = rank
                    if max(spawned) >= base.radix:
                        leaf_value = 4.
                    else:
                        candidates = []
                        for inner_action in ACTIONS:
                            leaf_after, gained, legal = ground.swipe_board_v1(tuple(spawned), ground.Swipe2048Action(inner_action))
                            if not legal:
                                continue
                            if max(leaf_after) >= base.radix:
                                leaf_tail = 4.
                            else:
                                predicted.append(tuple(leaf_after))
                                selected = updated if code(leaf_after) in keys else base
                                leaf_tail = predict_components(selected, leaf_after)['combined_prediction']
                            candidates.append(gained / 2048. + leaf_tail)
                        leaf_value = max(candidates) if candidates else -4.
                    tail += ((1. - p if rank == 1 else p) / len(empty)) * leaf_value
        values[action] = score / 2048. + tail
    chosen = max(values, key=values.get) if values else None
    return chosen, values, values[chosen] if chosen else -4., predicted


def test_lossless_all_sixteen_cells_unique_keys_and_exact_complete_fit_boundary():
    low, high = [0] * 16, [0] * 16
    low[0], low[14] = 1, 10
    high[15] = 10
    win, heldout = [11] + [0] * 15, [2] + [0] * 15
    dataset = dict(afterstates=np.asarray([low, low, high, win, heldout], dtype=np.int32),
        ends=np.asarray([4, 5], dtype=np.int64), fit_game_count=1, fit_step_end=4)
    support = support_from_dataset(dataset)
    assert support['keys'].tolist() == sorted([code(low), code(high)])
    assert code(high) > 2 ** 63 and code(heldout) not in support['keys']
    assert support['keys'].dtype == np.uint64 and not support['keys'].flags.writeable
    assert support['bytes'] == 16
    assert support['counts'] == dict(fit_boards_examined=4, fit_board_cells_examined=64,
        winning_fit_boards_excluded=1, encoded_fit_boards=3, encoded_fit_board_cells=48,
        support_sort_calls=1, support_sort_input_keys=3, unique_support_keys=2)
    with pytest.raises(ValueError, match='complete-game FIT prefix'):
        support_from_dataset(dict(dataset, fit_step_end=3))


@pytest.mark.parametrize('coverage', ['empty', 'all', 'partial'])
def test_exact_leaf_support_selects_both_components_and_matches_literal_h2_first_max(coverage):
    base, updated = heads()
    _, _, _, predictions = literal_h2(base, updated, BOARD, .375, set())
    unique = sorted(set(predictions))
    rows = [] if coverage == 'empty' else unique if coverage == 'all' else unique[::3]
    support = make_support(rows); keys = set(map(int, support['keys']))
    saved = [weights.copy() for leaf in (base, updated) for weights in (leaf.reward_weights, leaf.risk_weights)]
    expected, values, maximum, predicted = literal_h2(base, updated, BOARD, .375, keys)
    actual = choose_localized(updated, base, support, BOARD, .375, BUILD)
    assert actual['action'] == expected and actual['value'] == maximum
    assert {action:row['value'] for action,row in actual['action_values'].items()} == values
    count = actual['support_counts']
    updated_queries = sum(code(board) in keys for board in predicted)
    assert count['membership_queries'] == len(predicted)
    assert count['encoded_board_cells'] == 16 * len(predicted)
    assert count.get('updated_head_queries', 0) == updated_queries
    assert count.get('base_head_queries', 0) == len(predicted) - updated_queries
    if coverage in ('empty', 'all'):
        global_head = base if coverage == 'empty' else updated
        reference = global_head.choose(BOARD, .375)
        assert actual['action_values'] == reference['action_values']
        assert actual['counts'] == reference['counts']
        assert actual['representation_counts'] == reference['representation_counts']
    else:
        assert 0 < updated_queries < len(predicted)
        assert actual['action_values'] != base.choose(BOARD, .375)['action_values']
        assert actual['action_values'] != updated.choose(BOARD, .375)['action_values']
    for weights, before in zip((array for leaf in (base, updated) for array in (leaf.reward_weights, leaf.risk_weights)), saved):
        np.testing.assert_array_equal(weights, before)
        assert not weights.flags.writeable
    assert (base.updates, updated.updates) == (7, 11)


def test_analytic_win_loss_and_winning_candidates_bypass_membership():
    base, updated = heads(); support = make_support([])
    lost = (1, 2, 1, 2, 2, 1, 2, 1, 1, 2, 1, 2, 2, 1, 2, 1)
    for board, status, value in (((4,) + (0,) * 15, 'WON', 4.), (lost, 'LOST', -4.)):
        chosen = choose_localized(updated, base, support, board, .375, BUILD)
        assert chosen['status'] == status and chosen['value'] == value and chosen['action'] is None
        assert chosen['support_counts'] == chosen['representation_counts'] == {}
    winning = (3, 3, 0, 0) + (0,) * 12
    chosen = choose_localized(updated, base, support, winning, .375, BUILD)
    assert chosen['action_values']['LEFT']['tail_value'] == chosen['action_values']['RIGHT']['tail_value'] == 4.
    updated.risk_weights.flags.writeable = True
    with pytest.raises(ValueError, match='remain frozen'):
        choose_localized(updated, base, support, BOARD, .375, BUILD)


def test_empty_support_native_physical_games_match_base_rng_counts_and_terminal_results():
    base, updated = heads(); support = make_support([])
    seeds = [318000001, 318000002]
    actual = evaluate_localized(updated, base, support, .375, .5, seeds, BUILD, max_steps=32)
    expected = evaluate_split(base, .375, .5, seeds, BUILD, max_steps=32)
    for key in ('game_summaries', 'counts', 'representation_counts'):
        assert actual[key] == expected[key]
    assert actual['support_counts']['base_head_queries'] == actual['support_counts']['membership_queries']
    assert not actual['support_counts'].get('updated_head_queries', 0)
    assert actual['support_counts']['encoded_board_cells'] == 16 * actual['support_counts']['membership_queries']
    assert (base.updates, updated.updates) == (7, 11)
