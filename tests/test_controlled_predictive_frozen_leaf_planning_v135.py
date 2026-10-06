"""Finite learned-rule enumeration checks; no sampled games or search tuning."""
from collections import Counter
from fractions import Fraction
import json
from pathlib import Path

import numpy as np
import pytest

from acfqp.science import controlled_predictive_frozen_leaf_planning_v135 as core
from acfqp.science.controlled_predictive_contextual_ntuple_v134 import ConditionalQueryTD
from acfqp.science.controlled_predictive_ntuple_td_v120 import ACTIONS, NtupleValue
from acfqp.science.controlled_predictive_online_query_td_v131 import QueryTD
from acfqp.science.controlled_predictive_paired_ntuple_v130 import QueryParent
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics, RewriteProgram

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT/'reports/controlled_predictive_frozen_leaf_planning_v135_build'
SOURCE = dict(reward_weight=1., failure_penalty=4., goal_bonus=4.)
RISK8 = dict(reward_weight=1., failure_penalty=8., goal_bonus=8.)
RISK1 = dict(reward_weight=1., failure_penalty=1., goal_bonus=1.)
SPARSE = [1, 1]+[0]*14
NEAR_LOSS = [1, 2, 1, 2, 2, 1, 2, 1, 1, 2, 1, 2, 2, 1, 2, 0]
LOST = [1, 2, 1, 2, 2, 1, 2, 1]*2
GOAL = [3, 3]+[0]*14
LOSS_BRANCH = [2, 1, 2, 1, 1, 2, 1, 2, 2, 1, 2, 1, 2, 1, 1, 1]
SOURCES, MODELS, PLANNERS = [], [], []
ORACLE_WORK = Counter()


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    before = request.session.testsfailed
    yield
    path = ROOT/'reports/controlled_predictive_frozen_leaf_planning_v135.core_checks.json'
    payload = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    payload['attempts'].append(dict(
        tests=sum(item.module.__name__ == __name__ for item in request.session.items),
        failures=request.session.testsfailed-before,
        planner_work=dict(sum((planner.counts for planner in PLANNERS), Counter())),
        model_work=dict(sum((model.counts for model in MODELS), Counter())),
        source_work=dict(sum((model.counts for model in SOURCES), Counter())),
        oracle_work=dict(ORACLE_WORK),
        setup_counts=dict(sum((model.setup_counts for model in MODELS+SOURCES+PLANNERS), Counter())),
        newly_sampled_environment_transitions=0, newly_sampled_model_transitions=0,
        scope='Static synthetic boards and exact finite learned-rule enumeration only.'))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2)+'\n')


def leaf(representation='SINGLE', target=RISK8, constant_weights=False, freeze=True, constant=.4,
         spawn_distribution=((1, Fraction(9, 10)), (2, Fraction(1, 10)))):
    rule = LearnedDynamics(RewriteProgram(True, 'equal', 1, 'once', 'output_value'),
        spawn_distribution, 'uniform', 4)
    source = NtupleValue(rule, BUILD)
    source.weights[:] = (.01/32 if constant_weights else
        np.arange(source.weights.size).reshape(source.weights.shape)%11*.001)
    source.weights.flags.writeable = False
    source.updates = 42
    SOURCES.append(source)
    parent = QueryParent(source, SOURCE, target, constant)
    result = QueryTD(parent, 'PRIOR', BUILD) if representation == 'SINGLE' else (
        ConditionalQueryTD(parent, representation, BUILD))
    # Distinct context banks must be tested beyond their identical initialization.
    if representation == 'CAPACITY' and not constant_weights:
        result.update(SPARSE, .7)
        result.update(NEAR_LOSS, -4.)
    if freeze:
        result.freeze()
    MODELS.append(result)
    return result


def planner(model, depth=2):
    result = core.FrozenLeafPlanner(model, depth, BUILD)
    PLANNERS.append(result)
    return result


def oracle(model, board, collapsed_offset=False):
    """Python rewrite program plus the original model's public leaf choose."""
    if max(board) >= model.radix:
        return dict(action=None, value=model.target_query['goal_bonus'], status='WON', action_values={})
    values = {}
    for action in ACTIONS:
        after, score, changed = model.rule.swipe(board, action, ORACLE_WORK)
        if not changed:
            continue
        if max(after) >= model.radix:
            tail = model.target_query['goal_bonus']
        else:
            empty = [cell for cell, rank in enumerate(after) if rank == 0]
            tail = 0.
            for cell in empty:
                for rank, exact_rank_probability in model.rule.spawn_distribution:
                    rank_probability = float(exact_rank_probability)
                    successor = list(after)
                    successor[cell] = rank
                    chosen = model.choose(successor)
                    value = chosen['value']
                    if collapsed_offset and chosen['action_values']:
                        value = max(row['value'] if max(row['afterstate']) >= model.radix else
                            row['raw_value']+model.offset for row in chosen['action_values'].values())
                    tail += (rank_probability/len(empty))*value
                    ORACLE_WORK.update(enumerated_spawn_outcomes=1, leaf_queries=1)
        values[action] = dict(afterstate=list(after), score=score, tail_value=tail, value=score/2048.+tail)
    if not values:
        return dict(action=None, value=-model.target_query['failure_penalty'], status='LOST', action_values={})
    chosen = min(values, key=lambda action: (-values[action]['value'], action))
    return dict(action=chosen, **values[chosen], status='ACTIVE', action_values=values)


def assert_result(actual, expected):
    for field in ('action', 'value', 'status'):
        assert actual[field] == expected[field]
    assert actual['action_values'] == expected['action_values']


@pytest.mark.parametrize('representation', ['SINGLE', 'CAPACITY'])
def test_direct_is_the_original_choose_with_exact_values_and_schema(representation):
    model = leaf(representation)
    direct = planner(model, depth=1)
    for board in (SPARSE, NEAR_LOSS, GOAL, LOST, [4]+[0]*15):
        expected = model.choose(board, RISK8)
        actual = direct.choose(board, RISK8)
        assert actual == expected
    assert direct.counts['generated_spawn_outcomes'] == 0
    assert direct.counts['leaf_choose_calls'] == 0
    assert direct.setup_counts['cpp_compilations'] == 0
    assert direct.counts['learned_swipe_calls'] == direct.counts['root_swipe_calls']


@pytest.mark.parametrize('representation', ['SINGLE', 'CAPACITY'])
def test_h2_every_root_value_matches_independent_python_enumeration(representation):
    model = leaf(representation)
    search = planner(model)
    weights, updates = model.weights.copy(), model.updates
    for board in (SPARSE, NEAR_LOSS, GOAL, [1]+[0]*15, LOST, [4]+[0]*15):
        expected = oracle(model, board)
        model_counts = model.counts.copy()
        actual = search.choose(board, RISK8)
        assert_result(actual, expected)
        assert model.counts == model_counts
    np.testing.assert_array_equal(model.weights, weights)
    assert model.updates == search.updates == updates
    assert not search.weights.flags.writeable


@pytest.mark.parametrize('representation', ['SINGLE', 'CAPACITY'])
def test_h2_retains_two_offset_additions_instead_of_collapsing_the_offset(representation):
    model = leaf(representation, RISK1, constant_weights=True, constant=.5)
    search = planner(model)
    expected = oracle(model, SPARSE)
    incorrect = oracle(model, SPARSE, collapsed_offset=True)
    assert any(expected['action_values'][action]['value'] != incorrect['action_values'][action]['value']
        for action in expected['action_values'])
    assert_result(search.choose(SPARSE), expected)


def test_root_wins_do_not_expand_spawn_and_root_terminal_states_do_no_swipes():
    search = planner(leaf())
    result = search.choose(GOAL)
    winning = [row for row in result['action_values'].values() if max(row['afterstate']) >= 4]
    assert winning and result['counts']['root_goal_actions'] == len(winning)
    for row in winning:
        assert row['tail_value'] == 8. and row['value'] == row['score']/2048.+8.
    expected_branches = sum(2*row['afterstate'].count(0) for row in result['action_values'].values()
        if max(row['afterstate']) < 4)
    assert result['counts']['generated_spawn_outcomes'] == expected_branches
    terminal = search.choose([4]+[0]*15)
    assert terminal['status'] == 'WON'
    assert terminal['counts'].get('root_swipe_calls', 0) == 0
    assert terminal['counts'].get('generated_spawn_outcomes', 0) == 0


def test_leaf_loss_is_analytic_and_enumeration_counts_describe_actual_generated_work():
    search = planner(leaf('CAPACITY'))
    result = search.choose(LOSS_BRANCH)
    counts = result['counts']
    assert counts['leaf_terminal_loss_states'] > 0
    assert counts['generated_spawn_outcomes'] == sum(
        2*row['afterstate'].count(0) for row in result['action_values'].values())
    for key in ('leaf_choose_calls', 'expanded_postspawn_states',
                'expectimax_probability_products', 'expectimax_probability_sums'):
        assert counts[key] == counts['generated_spawn_outcomes']
    assert counts['spawn_rank1_outcomes'] == counts['spawn_rank2_outcomes']
    assert counts['generated_spawn_outcomes'] == 2*counts['spawn_rank1_outcomes']
    assert counts['root_swipe_calls'] == 4
    assert counts['second_ply_swipe_calls'] == 4*counts['leaf_choose_calls']
    assert counts['learned_swipe_calls'] == counts['root_swipe_calls']+counts['second_ply_swipe_calls']
    assert counts['table_lookups'] == 32*counts['value_predictions']
    assert counts['context_cell_reads'] == 32*counts['value_predictions']
    assert counts['bank_0_prediction_occurrences']+counts['bank_1_prediction_occurrences'] == counts['table_lookups']
    assert counts.get('table_update_occurrences', 0) == 0


def test_illegal_root_swipes_are_absent_and_depth1_returns_the_original_object(monkeypatch):
    model = leaf()
    result = planner(model).choose([1]+[0]*15)
    assert set(result['action_values']) == {'DOWN', 'RIGHT'}
    direct = planner(model, depth=1)
    original = model.choose(SPARSE)
    calls = []

    def choose(board, query=None):
        calls.append((board, query))
        return original

    monkeypatch.setattr(model, 'choose', choose)
    assert direct.choose(SPARSE, RISK8) is original
    assert calls == [(SPARSE, RISK8)]


def test_planner_requires_frozen_leaf_and_the_declared_target_query():
    model = leaf(freeze=False)
    with pytest.raises(ValueError, match='already be frozen'):
        planner(model)
    model.freeze()
    search = planner(model)
    with pytest.raises(ValueError, match='target query is fixed'):
        search.choose(SPARSE, RISK1)
    assert not search.counts


def test_actual_source_estimated_spawn_probabilities_are_used_without_true_law_injection():
    distribution = ((1, Fraction(8075, 9026)), (2, Fraction(951, 9026)))
    model = leaf(spawn_distribution=distribution)
    search = planner(model)
    assert search.spawn_probabilities == (8075/9026, 951/9026)
    assert search.spawn_probabilities != (.9, .1)
    assert_result(search.choose(LOSS_BRANCH), oracle(model, LOSS_BRANCH))
