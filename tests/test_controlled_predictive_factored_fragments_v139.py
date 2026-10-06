"""Finite recombination of separately observed line programs without fallback."""
from collections import Counter
from fractions import Fraction
import json
from pathlib import Path

import pytest

from acfqp.science import controlled_predictive_factored_fragments_v139 as core
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics, RewriteProgram

ROOT = Path(__file__).resolve().parents[1]
RULE = LearnedDynamics(RewriteProgram(True, 'equal', 1, 'once', 'output_value'),
    ((1, Fraction(9, 10)), (2, Fraction(1, 10))), 'uniform', 11)
ACTIONS = ('LEFT', 'RIGHT')
FIRST = ([1, 1, 2, 0]+[0]*12, ACTIONS, [dict(cell=2, rank=1), dict(cell=0, rank=2)])
SECOND = ([0, 1, 2, 3]+[0]*12, ACTIONS, [dict(cell=4, rank=1), dict(cell=0, rank=1)])
COMBINED = ([2, 0, 0, 0, 2, 1, 0, 0, 3, 2, 0, 0, 0, 3, 0, 0],
    ('UP', 'DOWN'), [dict(cell=8, rank=1), dict(cell=1, rank=2)])
CACHES, ORACLE_WORK = [], Counter()


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    before = request.session.testsfailed
    yield
    path = ROOT/'reports/controlled_predictive_factored_fragments_v139.core_checks.json'
    payload = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    payload['attempts'].append(dict(
        tests=sum(item.module.__name__ == __name__ for item in request.session.items),
        failures=request.session.testsfailed-before,
        cache_work=dict(sum((cache.work for cache in CACHES), Counter())), oracle_work=dict(ORACLE_WORK),
        newly_sampled_environment_transitions=0, newly_sampled_model_transitions=0,
        scope='Finite recorded fragment recombination, with no natural-game or model sampling.'))
    path.write_text(json.dumps(payload, indent=2)+'\n')


def cache():
    result = core.FactoredFragmentCache(RULE); CACHES.append(result); return result


def truth(fragment):
    board, actions, spawns = fragment
    board, scores = tuple(board), []
    for step, (action, spawn) in enumerate(zip(actions, spawns)):
        board, score, changed = RULE.swipe(board, action, ORACLE_WORK)
        assert changed and board[spawn['cell']] == 0
        assert step or max(board) < RULE.goal_rank
        board = list(board); board[spawn['cell']] = spawn['rank']; board = tuple(board)
        scores.append(score)
    status, _ = RULE.classify(board, ORACLE_WORK)
    return dict(exit_board=list(board), scores=scores, cumulative_score=sum(scores), status=status, duration=2)


def observe(instance, fragment):
    expected = truth(fragment)
    result = instance.observe(*fragment, expected['exit_board'], expected['scores'], expected['status'])
    assert result == expected
    return result


def test_parts_learned_from_separate_fragments_compose_unseen_actions_positions_and_spawn_locations():
    left, right = cache(), cache()
    observe(left, FIRST); first_ids = {p.program_id for p in left.programs}
    observe(right, SECOND)
    assert left.lookup(*COMBINED) is None and right.lookup(*COMBINED) is None
    observe(left, SECOND)
    before = left.work.copy(); result = left.lookup(*COMBINED)
    assert result == truth(COMBINED) and result['scores'] == [8, 16]
    ids = left.last_components
    assert len(ids) == 8 and any(i in first_ids for i in ids) and any(i not in first_ids for i in ids)
    assert left.work['compiled_programs'] == before['compiled_programs']
    assert left.work['observations'] == before['observations']
    assert left.work['composition_line_gathers']-before['composition_line_gathers'] == 8
    assert left.work['composition_board_writes']-before['composition_board_writes'] == 34
    assert left.work['composition_spawn_patches']-before['composition_spawn_patches'] == 2
    assert left.work['new_numeric_line_hits'] > before['new_numeric_line_hits']


def test_missing_component_returns_partial_ids_without_compile_or_primitive_transition_fallback(monkeypatch):
    instance = cache(); observe(instance, FIRST)
    before = instance.work.copy()
    def forbidden(*args, **kwargs):
        raise AssertionError('a missing component must not call the full primitive or terminal classifier')
    monkeypatch.setattr(LearnedDynamics, 'swipe', forbidden)
    monkeypatch.setattr(LearnedDynamics, 'classify', forbidden)
    assert instance.lookup(*COMBINED) is None
    assert 0 < len(instance.last_components) < 8
    assert instance.work['compiled_programs'] == before['compiled_programs']
    assert instance.work['compile_local_line_rewrites'] == before['compile_local_line_rewrites']
    assert instance.work['component_misses'] == before['component_misses']+1


def test_changed_local_equality_requires_observation_then_creates_alternative_only_for_that_line():
    instance = cache(); observe(instance, FIRST)
    changed = ([1, 1, 3, 0]+[0]*12, ACTIONS, FIRST[2])
    before = instance.work.copy(); assert instance.lookup(*changed) is None
    assert instance.work['compiled_programs'] == before['compiled_programs']
    observe(instance, changed)
    assert instance.work['guard_refinements'] > before['guard_refinements']
    assert instance.lookup(*changed) == truth(changed)
    assert instance.lookup(*FIRST) == truth(FIRST)
    assert all(len(program.anchor_binding) == 4 and len(program.output_expressions) == 4
        for program in instance.programs)
    assert all(kind == 'EQ' for program in instance.programs for kind, *_ in program.guards)


def test_dynamic_spawn_rank_changes_are_runtime_inputs_and_unseen_binding_can_reuse():
    instance = cache(); observe(instance, FIRST)
    changed = (FIRST[0], FIRST[1], [FIRST[2][0], dict(cell=1, rank=1)])
    before = instance.summary()
    result = instance.lookup(*changed)
    assert result == truth(changed)
    assert result['exit_board'][0] == 0 and result['exit_board'][1] == 1
    assert instance.summary() == before


def test_second_action_goal_keeps_winning_reward_and_final_spawn():
    instance = cache(); observe(instance, FIRST)
    winning = ([9, 9, 10, 0]+[0]*12, ACTIONS, FIRST[2])
    before = instance.work.copy()
    result = instance.lookup(*winning)
    assert result == truth(winning) and result['status'] == 'WON'
    assert result['scores'] == [1024, 2048] and result['cumulative_score'] == 3072
    assert result['exit_board'][0] == 2 and result['exit_board'][2] == 11
    assert instance.work['exit_status_learned_swipe_calls'] == before['exit_status_learned_swipe_calls']
    assert instance.work['exit_status_learned_terminal_checks'] == before['exit_status_learned_terminal_checks']+1


@pytest.mark.parametrize('fragment,match', [
    (([10, 10, 10, 0]+[0]*12, ACTIONS, FIRST[2]), 'first action reaches the goal'),
    ((FIRST[0], ('UP', 'RIGHT'), FIRST[2]), 'action 0 is illegal'),
    ((FIRST[0], ACTIONS, [dict(cell=0, rank=1), FIRST[2][1]]), 'spawn 0 has no vacancy')])
def test_inapplicable_observation_cannot_partially_fit_and_lookup_rejects(fragment, match):
    instance = cache(); observe(instance, FIRST)
    before = instance.summary()
    assert instance.lookup(*fragment) is None
    with pytest.raises(ValueError, match=match):
        instance.observe(*fragment, [0]*16, [0, 0], 'ACTIVE')
    assert instance.summary() == before


def test_wrong_full_observation_is_rejected_before_learning_any_component():
    instance = cache(); expected = truth(FIRST)
    with pytest.raises(ValueError, match='observation disagrees'):
        instance.observe(*FIRST, expected['exit_board'], [4, 9], 'ACTIVE')
    assert instance.summary()['num_programs'] == 0
    assert not instance.work['line_observations'] and not instance.work['compiled_programs']
    assert instance.work['observation_validation_learned_swipe_calls'] == 6


def test_serialized_prefix_retains_stable_component_ids_and_freezes_program_set():
    instance = cache(); observe(instance, FIRST)
    payload = json.loads(json.dumps(instance.to_dict()))
    frozen = core.FactoredFragmentCache.from_dict(payload, RULE); CACHES.append(frozen)
    assert frozen.summary() == instance.summary()
    assert [p.program_id for p in frozen.programs] == list(range(len(frozen.programs)))
    assert frozen.lookup(*FIRST) == instance.lookup(*FIRST)
    assert frozen.last_components == instance.last_components
    ids = frozen.last_components.copy()
    observe(instance, SECOND)
    assert instance.lookup(*COMBINED) == truth(COMBINED) and frozen.lookup(*COMBINED) is None
    assert frozen.lookup(*FIRST) == truth(FIRST) and frozen.last_components == ids
    assert not frozen.work['observations'] and not frozen.work['compiled_programs']
    assert frozen.work['composition_descriptions'] == 1
    assert frozen.work['copied_anchor_ranks'] == 4*len(frozen.programs)


def test_program_footprint_counts_local_storage_and_one_shared_composition_description():
    instance = cache(); observe(instance, FIRST); observe(instance, SECOND)
    summary = instance.summary(); n = len(instance.programs)
    assert summary['total_exit_cell_slots'] == summary['total_anchor_rank_copies'] == 4*n
    assert summary['total_guards'] == sum(len(p.guards) for p in instance.programs)
    assert summary['total_reward_expressions'] == sum(len(p.reward_expressions) for p in instance.programs)
    assert summary['shared_composition_instructions'] == sum(n for _, n in core.COMPOSITION_FOOTPRINT)
    assert summary['total_instructions'] == summary['local_program_instructions']+summary['shared_composition_instructions']
    assert instance.work['line_observations'] == 16
    assert instance.work['observation_validation_recorded_spawn_patches'] == 4
    assert not instance.work['sampled_transitions']
