"""Fixed-board component arithmetic and semantics; no new environment draws."""
from fractions import Fraction

import numpy as np
import pytest

from acfqp.science import natural_action_components_v283 as core
from acfqp.science.controlled_predictive_frozen_leaf_planning_v135 import FrozenLeafPlanner
from acfqp.science.controlled_predictive_ntuple_td_v120 import ACTIONS, NtupleValue
from acfqp.science.controlled_predictive_online_query_td_v131 import QueryTD
from acfqp.science.controlled_predictive_paired_ntuple_v130 import QueryParent
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics, RewriteProgram

BUILD = core.Path(__file__).resolve().parents[1] / 'reports/natural_action_components_v283/runtime/tests'
QUERY = dict(reward_weight=1., failure_penalty=4., goal_bonus=4.)
SPARSE = [1, 1] + [0] * 14
NEAR_LOSS = [1, 2, 1, 2, 2, 1, 2, 1, 1, 2, 1, 2, 2, 1, 2, 0]
LOST = [1, 2, 1, 2, 2, 1, 2, 1] * 2
GOAL = [3, 3] + [0] * 14
LOSS_BRANCH = [2, 1, 2, 1, 1, 2, 1, 2, 2, 1, 2, 1, 2, 1, 1, 1]


@pytest.fixture(scope='module')
def leaf():
    rule = LearnedDynamics(RewriteProgram(True, 'equal', 1, 'once', 'output_value'),
        ((1, Fraction(9, 10)), (2, Fraction(1, 10))), 'uniform', 4)
    source = NtupleValue(rule, BUILD)
    source.weights[:] = np.arange(source.weights.size).reshape(source.weights.shape) % 11 * .001
    parent = QueryParent(source, QUERY, QUERY, .5)
    model = QueryTD(parent, 'PRIOR', BUILD)
    model.freeze()
    return model


def without_counts(choice):
    return {key: value for key, value in choice.items() if key != 'counts'}


@pytest.mark.parametrize('probability', [0., .1, .37, .5, 1.])
def test_full_original_h2_scores_and_action_are_bitwise_identical(leaf, probability):
    components = core.ActionComponents(leaf, BUILD)
    original = FrozenLeafPlanner(leaf, depth=2, build_dir=BUILD)
    original.spawn_probabilities = 1. - probability, probability
    for board in (SPARSE, NEAR_LOSS, LOSS_BRANCH, LOST, GOAL, [4] + [0] * 15):
        extracted = components.components(board)
        actual = components.compose(extracted, probability)
        expected = original.choose(board)
        assert without_counts(actual) == without_counts(expected)


def test_rank_tails_and_short_values_match_independent_finite_rewrites(leaf):
    model = core.ActionComponents(leaf, BUILD)
    for board in (SPARSE, NEAR_LOSS, LOSS_BRANCH, GOAL):
        payload = model.components(board)
        for action, item in payload['action_components'].items():
            root_after, root_score, changed = leaf.rule.swipe(board, action)
            assert changed and root_score == item['score'] and list(root_after) == item['afterstate']
            if max(root_after) >= leaf.radix:
                assert item['spawn_leaf_values'] == []
                assert item['short_rank1_tail'] == item['short_rank2_tail'] == QUERY['goal_bonus']
                continue
            assert [s['cell'] for s in item['spawn_leaf_values']] == [i for i, rank in enumerate(root_after) if rank == 0]
            for spawn in item['spawn_leaf_values']:
                for rank in (1, 2):
                    child = list(root_after)
                    child[spawn['cell']] = rank
                    full = leaf.choose(child)['value']
                    legal = []
                    for second in ACTIONS:
                        after, score, changed = leaf.rule.swipe(child, second)
                        if changed:
                            legal.append(score / 2048. + (QUERY['goal_bonus'] if max(after) >= leaf.radix else 0.))
                    short = max(legal) if legal else -QUERY['failure_penalty']
                    assert spawn['full'][rank - 1] == full
                    assert spawn['short'][rank - 1] == short
            for rank in (1, 2):
                assert item[f'rank{rank}_tail'] == sum((1. / len(item['spawn_leaf_values'])) * s['full'][rank - 1]
                                                      for s in item['spawn_leaf_values'])


def test_full_and_short_preserve_terminal_goal_and_loss(leaf):
    model = core.ActionComponents(leaf, BUILD)
    for board in (LOST, [4] + [0] * 15):
        payload = model.components(board)
        assert without_counts(model.compose(payload, .5, 'short')) == without_counts(model.compose(payload, .5, 'full'))
    goal = model.components(GOAL)
    for item in goal['action_components'].values():
        if not item['spawn_leaf_values']:
            assert item['short_rank1_tail'] == item['rank1_tail'] == 4.
    near_loss = model.components(LOSS_BRANCH)
    losses = [spawn for item in near_loss['action_components'].values() for spawn in item['spawn_leaf_values']
              if -4. in spawn['short']]
    assert losses and all(spawn['full'][i] == -4. for spawn in losses
                          for i, value in enumerate(spawn['short']) if value == -4.)


def test_components_computed_once_and_reweighting_never_queries_leaf_or_mutates_weights(leaf):
    model = core.ActionComponents(leaf, BUILD)
    before_weights, before_updates = leaf.weights.copy(), leaf.updates
    payload = model.components(SPARSE)
    before_counts = model.counts.copy()
    for probability in (.1, .3, .5):
        for tail in ('full', 'short'):
            model.compose(payload, probability, tail)
    assert model.counts['leaf_choose_calls'] == before_counts['leaf_choose_calls']
    assert model.counts['generated_spawn_outcomes'] == before_counts['generated_spawn_outcomes']
    assert model.counts['value_predictions'] == before_counts['value_predictions']
    assert model.counts['compose_calls'] == 6
    assert model.counts['short_leaf_action_comparisons'] == model.counts['full_leaf_action_comparisons'] > 0
    np.testing.assert_array_equal(leaf.weights, before_weights)
    assert leaf.updates == before_updates and not leaf.weights.flags.writeable


def test_composition_retains_cell_rank_order_when_affine_regrouping_rounds_differently():
    rows = [dict(cell=i, full=[first, second], short=[first, second])
            for i, (first, second) in enumerate(((.1, .2), (.3, .4), (.5, .6)))]
    payload = dict(board=SPARSE, status='ACTIVE', goal_bonus=4., failure_penalty=4.,
        action_components={'LEFT': dict(afterstate=SPARSE, score=0, spawn_leaf_values=rows)})
    probability = .37
    expected = 0.
    for row in rows:
        expected += ((1. - probability) / 3) * row['full'][0]
        expected += (probability / 3) * row['full'][1]
    actual = core.compose(payload, probability)['value']
    assert actual == expected
    # Means are useful for interpretation, but are not the exact-score contract.
    rank1 = sum((1. / 3) * row['full'][0] for row in rows)
    rank2 = sum((1. / 3) * row['full'][1] for row in rows)
    assert actual != (1. - probability) * rank1 + probability * rank2
