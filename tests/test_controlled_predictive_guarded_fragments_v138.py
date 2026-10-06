"""Finite symbolic two-action reuse and recorded-spawn binding checks."""
from collections import Counter
from dataclasses import FrozenInstanceError
from fractions import Fraction
import json
from pathlib import Path

import pytest

from acfqp.science import controlled_predictive_guarded_fragments_v138 as core
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics, RewriteProgram

ROOT = Path(__file__).resolve().parents[1]
RULE = LearnedDynamics(RewriteProgram(True, 'equal', 1, 'once', 'output_value'),
    ((1, Fraction(9, 10)), (2, Fraction(1, 10))), 'uniform', 11)
ACTIONS = ('LEFT', 'RIGHT')
SPAWNS = [dict(cell=2, rank=1), dict(cell=0, rank=2)]
CACHES, ORACLE_WORK = [], Counter()


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    before = request.session.testsfailed
    yield
    path = ROOT/'reports/controlled_predictive_guarded_fragments_v138.core_checks.json'
    payload = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    payload['attempts'].append(dict(
        tests=sum(item.module.__name__ == __name__ for item in request.session.items),
        failures=request.session.testsfailed-before,
        cache_work=dict(sum((cache.work for cache in CACHES), Counter())), oracle_work=dict(ORACLE_WORK),
        newly_sampled_environment_transitions=0, newly_sampled_model_transitions=0,
        scope='Finite symbolic and concrete recorded fragments; no natural-game sampling.'))
    path.write_text(json.dumps(payload, indent=2)+'\n')


def cache(concrete=False):
    result = (core.ExactConcreteFragmentCache if concrete else core.GuardedFragmentCache)(RULE)
    CACHES.append(result)
    return result


def board(a=1, c=2):
    return [a, a, c, 0]+[0]*12


def truth(root, actions=ACTIONS, spawns=SPAWNS):
    current, scores = tuple(root), []
    for step, (action, spawn) in enumerate(zip(actions, spawns)):
        current, score, changed = RULE.swipe(current, action, ORACLE_WORK)
        assert changed and current[spawn['cell']] == 0
        if step == 0:
            assert max(current) < RULE.goal_rank
        spawned = list(current); spawned[spawn['cell']] = spawn['rank']; current = tuple(spawned)
        scores.append(score)
    status, _ = RULE.classify(current, ORACLE_WORK)
    return dict(exit_board=list(current), scores=scores, cumulative_score=sum(scores), status=status, duration=2)


def observe(instance, root, actions=ACTIONS, spawns=SPAWNS):
    result = truth(root, actions, spawns)
    assert instance.observe(root, actions, spawns, result['exit_board'], result['scores'], result['status']) == result
    return result


def test_cross_action_guards_share_program_across_numerical_roots_and_keep_rewards_parametric():
    instance = cache()
    initial = observe(instance, board())
    assert initial['scores'] == [4, 8] and initial['exit_board'] == [2, 0, 3, 1]+[0]*12
    program = next(iter(instance.buckets.values()))[0]
    with pytest.raises(FrozenInstanceError):
        program.zero_mask = 0
    assert any(kind == 'EQ' and (left[1] == 1 or right[1] == 1)
        for kind, left, right, _ in program.guards if kind == 'EQ')
    before = instance.work['compile_symbolic_swipes']
    result = instance.lookup(board(2, 3), ACTIONS, SPAWNS)
    assert result == truth(board(2, 3)) and result['scores'] == [8, 16]
    assert instance.work['new_numeric_board_hits'] == 1
    assert instance.work['compile_symbolic_swipes'] == before == 2
    assert instance.summary()['num_programs'] == 1


def test_spawn_rank_variables_are_bound_and_changed_intermediate_merge_path_requires_new_guard():
    instance = cache(); observe(instance, board())
    final_changed = [SPAWNS[0], dict(cell=0, rank=1)]
    assert instance.lookup(board(), ACTIONS, final_changed) == truth(board(), spawns=final_changed)
    middle_changed = [dict(cell=2, rank=2), SPAWNS[1]]
    assert instance.lookup(board(), ACTIONS, middle_changed) is None
    observe(instance, board(), spawns=middle_changed)
    assert instance.summary()['num_programs'] == 2
    assert instance.work['guard_refinements'] == 1
    assert instance.lookup(board(), ACTIONS, middle_changed) == truth(board(), spawns=middle_changed)
    assert any(expression == (17, 0) for fragment in next(iter(instance.buckets.values()))
        for expression in fragment.exit_expressions)


def test_rejected_cross_action_equality_is_refined_only_after_observation():
    instance = cache(); observe(instance, board())
    altered = board(1, 3)
    work = instance.work.copy()
    assert instance.lookup(altered, ACTIONS, SPAWNS) is None
    assert instance.work['compiled_programs'] == work['compiled_programs'] == 1
    observe(instance, altered)
    assert instance.summary()['num_programs'] == 2 and instance.work['guard_refinements'] == 1
    assert instance.lookup(altered, ACTIONS, SPAWNS) == truth(altered)
    assert instance.lookup(board(), ACTIONS, SPAWNS) == truth(board())


def test_goal_on_second_action_is_allowed_and_first_goal_prevents_reuse():
    instance = cache(); observe(instance, board())
    final_goal = instance.lookup(board(9, 10), ACTIONS, SPAWNS)
    assert final_goal == truth(board(9, 10))
    assert final_goal['status'] == 'WON' and final_goal['scores'] == [1024, 2048]
    assert final_goal['exit_board'][0] == 2
    assert instance.lookup(board(10, 10), ACTIONS, SPAWNS) is None
    with pytest.raises(ValueError, match='first action reaches the goal'):
        instance.observe(board(10, 10), ACTIONS, SPAWNS, [0]*16, [0, 0], 'WON')
    assert instance.summary()['num_programs'] == 1


@pytest.mark.parametrize('actions,spawns,error', [
    (('UP', 'RIGHT'), SPAWNS, 'action 0 is illegal'),
    (('LEFT', 'LEFT'), [dict(cell=3, rank=1), dict(cell=0, rank=1)], 'action 1 is illegal'),
    (ACTIONS, [dict(cell=0, rank=1), SPAWNS[1]], 'spawn 0 has no vacancy')])
def test_inapplicable_observations_do_not_create_programs(actions, spawns, error):
    instance = cache()
    # For the second illegal swipe use a no-merge first result, fully packed left.
    root = [1, 2, 3, 0]+[0]*12 if actions == ('LEFT', 'LEFT') else board()
    if actions == ('LEFT', 'LEFT'):
        root = [0, 1, 2, 3]+[0]*12
    with pytest.raises(ValueError, match=error):
        instance.observe(root, actions, spawns, [0]*16, [0, 0], 'ACTIVE')
    assert instance.summary()['num_programs'] == 0


def test_guard_hit_and_new_compile_must_match_observed_full_consequences():
    instance = cache(); expected = truth(board())
    with pytest.raises(ValueError, match='compiled fragment disagrees'):
        instance.observe(board(), ACTIONS, SPAWNS, expected['exit_board'], [4, 9], 'ACTIVE')
    assert instance.summary()['num_programs'] == 0
    observe(instance, board())
    corrupted = expected['exit_board'].copy(); corrupted[0] = 1
    with pytest.raises(ValueError, match='guarded fragment disagrees'):
        instance.observe(board(), ACTIONS, SPAWNS, corrupted, expected['scores'], 'ACTIVE')
    assert instance.summary()['num_programs'] == 1


@pytest.mark.parametrize('concrete', [False, True])
def test_serialized_prefix_is_independent_and_no_compilation_occurs_on_lookup(concrete):
    instance = cache(concrete); observe(instance, board())
    payload = json.loads(json.dumps(instance.to_dict()))
    frozen = type(instance).from_dict(payload, RULE); CACHES.append(frozen)
    assert frozen.work == Counter(copied_programs=1)
    assert frozen.summary() == instance.summary()
    observe(instance, board(1, 3))
    assert instance.summary()['num_programs'] == 2 and frozen.summary()['num_programs'] == 1
    assert frozen.lookup(board(), ACTIONS, SPAWNS) == truth(board())
    assert frozen.lookup(board(1, 3), ACTIONS, SPAWNS) is None
    assert not frozen.work['compile_symbolic_swipes'] and not frozen.work['compiled_programs']


def test_concrete_cache_requires_full_numeric_binding_and_copies_observed_values():
    instance = cache(True); expected = observe(instance, board())
    expected['exit_board'][0] = 99
    assert instance.lookup(board(), ACTIONS, SPAWNS) == truth(board())
    assert instance.lookup(board(2, 3), ACTIONS, SPAWNS) is None
    changed = [SPAWNS[0], dict(cell=0, rank=1)]
    assert instance.lookup(board(), ACTIONS, changed) is None
    assert instance.summary()['total_stored_output_values'] == 18
    assert instance.work['stored_input_rank_copies'] == 18
    assert not instance.work['compile_symbolic_swipes']


def test_unsupported_rule_and_terminal_root_are_rejected_without_sampling():
    changed = LearnedDynamics(RewriteProgram(True, 'equal', 1, 'once', 'count'),
        RULE.spawn_distribution, 'uniform', 11)
    with pytest.raises(ValueError, match='frozen equal-merge'):
        core.GuardedFragmentCache(changed)
    instance = cache()
    assert instance.lookup([11]+[0]*15, ACTIONS, SPAWNS) is None
    assert instance.lookup(board(), ACTIONS, [dict(cell=2, rank=3), SPAWNS[1]]) is None
    assert not instance.work['compile_symbolic_swipes']
    assert not instance.work['sampled_transitions']
