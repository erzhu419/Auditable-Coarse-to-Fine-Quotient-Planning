"""Finite native-program, leaf-semantics and strict model-budget checks."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction
from itertools import product
import json
from pathlib import Path

import numpy as np
import pytest

from acfqp.science import controlled_predictive_program_planning_v140 as core
from acfqp.science.controlled_predictive_ntuple_td_v120 import ACTIONS, NtupleValue
from acfqp.science.controlled_predictive_online_query_td_v131 import QueryTD
from acfqp.science.controlled_predictive_paired_ntuple_v130 import QueryParent
from acfqp.science.controlled_predictive_policy_programs_v140 import rank_actions, randomize_programs
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics, RewriteProgram

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT/'reports/controlled_predictive_program_planning_v140_build'
RETAINED = ROOT/'reports/controlled_predictive_factored_fragments_v139'
SOURCE = dict(reward_weight=1., failure_penalty=4., goal_bonus=4.)
TARGET = dict(reward_weight=1., failure_penalty=1., goal_bonus=1.)
SPARSE = [1, 1]+[0]*14
NEAR_LOSS = [1, 2, 1, 2, 2, 1, 2, 1, 1, 2, 1, 2, 2, 1, 2, 0]
LOST = [1, 2, 1, 2, 2, 1, 2, 1]*2
GOAL = [3, 3]+[0]*14
PLANNERS, SOURCES, MODELS, ORACLE_WORK = [], [], [], Counter()


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    before = request.session.testsfailed
    yield
    path = ROOT/'reports/controlled_predictive_program_planning_v140.planner_checks.json'
    payload = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    payload['attempts'].append(dict(
        tests=sum(item.module.__name__ == __name__ for item in request.session.items),
        failures=request.session.testsfailed-before,
        planner_work=dict(sum((planner.counts for planner in PLANNERS), Counter())),
        setup_counts=dict(sum((model.setup_counts for model in PLANNERS+SOURCES+MODELS), Counter())),
        model_work=dict(sum((model.counts for model in MODELS+SOURCES), Counter())),
        oracle_work=dict(ORACLE_WORK), newly_sampled_environment_transitions=0,
        newly_sampled_model_transitions=sum(planner.counts['model_sampled_transitions'] for planner in PLANNERS),
        scope='Static finite boards, all retained local lines over ranks 0..10, and bounded simulated rollouts.'))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2)+'\n')


def policy():
    return dict(schema='acfqp.policy_programs.v140', trees=[
        [[-1, *[(previous+i) % 4 for i in range(4)]] for _ in range(7)] for previous in range(4)])


def factored(life=0):
    return json.loads((RETAINED/f'train_{life}/FACTORED_64.json').read_text())


def leaf(target=TARGET, constant_weights=False, frozen=True,
         distribution=((1, Fraction(9, 10)), (2, Fraction(1, 10)))):
    rule = LearnedDynamics(RewriteProgram(True, 'equal', 1, 'once', 'output_value'), distribution, 'uniform', 4)
    source = NtupleValue(rule, BUILD)
    source.weights[:] = .01/32 if constant_weights else np.arange(source.weights.size).reshape(source.weights.shape)%11*.001
    source.weights.flags.writeable = False
    source.updates = 42; SOURCES.append(source)
    result = QueryTD(QueryParent(source, SOURCE, target, .5), 'PRIOR', BUILD)
    if frozen:
        result.freeze()
    MODELS.append(result)
    return result


def planner(model=None, payload=None, programs=None, mode='ROLLOUT'):
    result = core.ProgramPlanner(leaf() if model is None else model,
        factored() if programs is None else programs, policy() if payload is None else payload,
        mode=mode, build_dir=BUILD)
    PLANNERS.append(result)
    return result


@pytest.mark.parametrize('life', range(4))
def test_every_supported_local_line_in_each_retained_library_matches_frozen_rule(life):
    search = planner(programs=factored(life))
    assert len(search.programs) == 34
    for line in product(range(11), repeat=4):
        ORACLE_WORK['complete_local_line_cases'] += 1
        assert search._line(line) == search.rule.program.line(line)
    assert search.counts['line_misses'] == 0
    assert search.counts['line_hits'] == 11**4
    assert search.counts['line_program_mask_tests'] >= search.counts['line_guard_trials']
    assert search.counts['model_sampled_transitions'] == 0


@pytest.mark.parametrize('mode', ['DIRECT', 'ROLLOUT'])
def test_root_candidates_are_full_exact_local_program_swipes_and_budget_includes_every_attempt(mode):
    search = planner(mode=mode)
    for board in (SPARSE, NEAR_LOSS, GOAL, [1]+[0]*15, LOST, [4]+[0]*15):
        choice = search.choose(board, simulation_seed=140)
        counts = choice['counts']
        if max(board) >= search.radix:
            assert choice['status'] == 'WON' and choice['value'] == TARGET['goal_bonus']
            assert counts.get('learned_swipe_calls', 0) == 0
            continue
        expected = {action: (after, score) for action in ACTIONS
            for after, score, changed in [search.rule.swipe(board, action, ORACLE_WORK)] if changed}
        assert set(choice['action_values']) == set(expected)
        for action, row in choice['action_values'].items():
            assert (tuple(row['afterstate']), row['score']) == expected[action]
            expected_cap = 0 if mode == 'DIRECT' or max(row['afterstate']) >= search.radix else 8*row['afterstate'].count(0)
            assert row['budget'] == expected_cap and 0 <= row['used'] <= row['budget']
            assert row['rollouts'] == (max(1, expected_cap//16) if expected_cap else 0)
        assert counts['root_swipe_calls'] == 4
        assert counts['model_swipe_budget'] == 4+sum(row['budget'] for row in choice['action_values'].values())
        assert counts['model_swipes_used'] == 4+sum(row['used'] for row in choice['action_values'].values())
        assert counts['learned_swipe_calls'] == counts['model_swipes_used']
        assert counts['model_swipes_used'] == counts['program_swipe_calls']+counts.get('bootstrap_swipe_calls', 0)
        assert counts.get('rollouts_started', 0) == sum(row['rollouts'] for row in choice['action_values'].values())
        assert counts.get('simulation_uniform_draws', 0) == 2*counts.get('model_sampled_transitions', 0)
        if not expected:
            assert choice['status'] == 'LOST' and choice['value'] == -TARGET['failure_penalty']


def test_h1_bootstrap_exactly_retains_query_conversion_and_terminal_semantics():
    for target in (SOURCE, TARGET):
        model = leaf(target=target, constant_weights=True)
        search = planner(model=model)
        for board in (SPARSE, NEAR_LOSS, LOST, GOAL, [4]+[0]*15):
            expected = model.choose(board)['value']
            model_counts = model.counts.copy()
            assert search._h1(board) == expected
            assert model.counts == model_counts
        if target == TARGET:
            expected = model.choose(SPARSE)
            collapsed = max(row['raw_value']+model.offset for row in expected['action_values'].values())
            assert expected['value'] != collapsed


def test_every_predicate_branch_and_previous_action_matches_python_program():
    boards = [SPARSE, NEAR_LOSS, LOST, [0]*16,
        [3]+[1]*15, [1]*3+[3]+[1]*12, [1]*12+[3]+[1]*3, [1]*15+[3],
        [1, 3, 2, 1, 2, 1, 3, 2, 1, 2, 1, 3, 2, 1, 2, 1]]
    for predicate in range(14):
        payload = policy()
        for tree in payload['trees']:
            tree[0][0] = predicate
            tree[1][1:] = [0, 1, 2, 3]
            tree[2][1:] = [3, 2, 1, 0]
        search = planner(payload=payload, mode='DIRECT')
        for board in boards:
            for previous in ACTIONS:
                assert search._order(board, previous) == rank_actions(board, previous, payload)
    assert search.counts['model_sampled_transitions'] == 0


def test_direct_uses_only_priority_among_all_legal_actions_without_leaf_or_sampling():
    payload, model = policy(), leaf()
    search = planner(model=model, payload=payload, mode='DIRECT')
    before = model.counts.copy()
    for previous in ACTIONS:
        choice = search.choose(SPARSE, previous_action=previous, simulation_seed=9)
        selected = next(action for action in rank_actions(SPARSE, previous, payload)
            if action in choice['action_values'])
        assert choice['action'] == selected and choice['value_kind'] == 'action_priority'
        assert choice['action'] == min(choice['action_values'], key=lambda action: (-choice['action_values'][action]['value'], action))
        assert choice['counts']['learned_swipe_calls'] == 4
        for key in ('value_predictions', 'leaf_choose_calls', 'bootstrap_swipe_calls',
                    'model_sampled_transitions', 'simulation_uniform_draws'):
            assert choice['counts'].get(key, 0) == 0
    assert model.counts == before


def test_simulation_seed_is_repeatable_and_fixed_source_inputs_remain_readonly():
    model, payload, programs = leaf(), policy(), factored()
    original_payload, original_programs = deepcopy(payload), deepcopy(programs)
    search = planner(model=model, payload=payload, programs=programs)
    weights, updates, model_counts = model.weights.copy(), model.updates, model.counts.copy()
    first = search.choose(SPARSE, simulation_seed=41)
    assert search.choose(SPARSE, simulation_seed=41) == first
    alternatives = [search.choose(SPARSE, simulation_seed=seed) for seed in (42, 43)]
    assert any(result['action_values'] != first['action_values'] for result in alternatives)
    np.testing.assert_array_equal(model.weights, weights)
    assert model.updates == updates and model.counts == model_counts
    assert payload == original_payload and programs == original_programs
    assert not search.weights.flags.writeable and not search.trees.flags.writeable and not search.programs.flags.writeable


def test_small_budget_early_bootstrap_and_large_budget_multiple_rollouts_are_retained():
    search = planner()
    small = search.choose(NEAR_LOSS, simulation_seed=17)
    assert any(row['budget'] == 8 and row['rollouts'] == 1 for row in small['action_values'].values())
    assert small['counts'].get('budget_early_bootstraps', 0) > 0
    large = search.choose(SPARSE, simulation_seed=17)
    assert any(row['rollouts'] > 1 for row in large['action_values'].values())
    assert large['counts']['bootstrap_swipe_calls'] == 4*large['counts']['leaf_choose_calls']


def test_root_goal_values_stop_without_spawns_and_incomplete_programs_fail_without_fallback():
    search = planner()
    result = search.choose(GOAL, simulation_seed=1)
    goals = [row for row in result['action_values'].values() if max(row['afterstate']) >= search.radix]
    assert goals
    for row in goals:
        assert row['value'] == row['score']/2048.+TARGET['goal_bonus']
        assert row['tail_value'] == TARGET['goal_bonus']
        assert row['budget'] == row['used'] == row['rollouts'] == 0
    missing = factored(); missing['programs'] = []
    failed = planner(programs=missing)
    with pytest.raises(ValueError, match='coverage is incomplete'):
        failed.choose(SPARSE)
    assert failed.counts['line_misses'] == 1
    assert failed.counts['bootstrap_swipe_calls'] == failed.counts['model_sampled_transitions'] == 0


def test_random_leaf_program_uses_same_budget_formula_and_native_tree_semantics():
    payload = policy(); payload['metadata'] = {}
    random = randomize_programs(payload, 140)
    learned, control = planner(payload=payload), planner(payload=random)
    left, right = learned.choose(SPARSE, simulation_seed=22), control.choose(SPARSE, simulation_seed=22)
    for action in left['action_values']:
        assert left['action_values'][action]['budget'] == right['action_values'][action]['budget']
        assert left['action_values'][action]['rollouts'] == right['action_values'][action]['rollouts']
    for previous in ACTIONS:
        assert control._order(SPARSE, previous) == rank_actions(SPARSE, previous, random)


def test_requires_frozen_single_leaf_and_actual_frozen_spawn_distribution():
    model = leaf(frozen=False)
    with pytest.raises(ValueError, match='already be frozen'):
        planner(model=model)
    model.freeze()
    search = planner(model=model)
    with pytest.raises(ValueError, match='target query is fixed'):
        search.choose(SPARSE, SOURCE)
    distribution = ((1, Fraction(8075, 9026)), (2, Fraction(951, 9026)))
    estimated = planner(model=leaf(distribution=distribution))
    assert estimated.spawn_probabilities == (8075/9026, 951/9026)
    assert estimated.spawn_probabilities != (.9, .1)
