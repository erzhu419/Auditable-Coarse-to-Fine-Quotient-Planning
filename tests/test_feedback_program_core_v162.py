"""Observed feedback, exclusion, original orientation, permanent exits and costs."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path
import random

import pytest

from acfqp.domains import standard_2048 as ground
from acfqp.domains.g2048 import D4_ELEMENTS, D4Transform
from acfqp.science.controlled_predictive_feedback_program_v162 import (
    INVERSE, QUERIES, canonical_frame, generate_candidates as _generate_candidates, run_branch)
from acfqp.science.controlled_predictive_program_consolidation_v161 import canonical_word
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics, RewriteProgram

TEMP = Path(__file__).resolve().parents[1]/'reports/v162_runtime_tmp'
ROWS, ORACLE, STUB_WORK, GENERATION_WORK = [], Counter(), Counter(), Counter()
SPARSE = (1,)+(0,)*15
RULE = LearnedDynamics(RewriteProgram(True, 'equal', 1, 'once', 'output_value'),
                       ((1, Fraction(9, 10)), (2, Fraction(1, 10))), 'uniform')


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    TEMP.mkdir(parents=True, exist_ok=True); before = request.session.testsfailed
    yield
    path = TEMP/'core_checks.json'
    payload = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    environment = sum((Counter(row['result']['environment_counts']) for row in ROWS), Counter())
    policy = sum((Counter(row['result']['policy_counts']) for row in ROWS), Counter())
    setup = sum((Counter(row['result']['program_setup_counts']) for row in ROWS), Counter())
    payload['attempts'].append(dict(tests=sum(item.module.__name__ == __name__ for item in request.session.items),
        failures=request.session.testsfailed-before, environment_counts=dict(environment),
        newly_sampled_environment_transitions=environment['sampled_transitions'],
        newly_sampled_model_transitions=0, real_training_updates=0, native_planner_calls=0,
        policy_stub_work=dict(STUB_WORK), deterministic_oracle_work=dict(ORACLE),
        policy_counts=dict(policy), program_setup_counts=dict(setup), generation_counts=dict(GENERATION_WORK),
        scope='Finite stub-teacher trajectories and observed-source fragments; no native planning or fitting.'))
    path.write_text(json.dumps(payload, indent=2)+'\n')


def generate_candidates(*args, **kwargs):
    result = _generate_candidates(*args, **kwargs)
    GENERATION_WORK.update(result['counts'])
    return result


class LegalPlanner:
    def __init__(self):
        self.calls = []
        self.counts = Counter(choose_calls=11, value_predictions=13)

    def choose(self, board, query):
        self.calls.append((tuple(board), deepcopy(query)))
        cycle = ('LEFT', 'DOWN', 'RIGHT', 'UP'); index = (len(self.calls)-1) % 4
        for action in cycle[index:]+cycle[:index]:
            after, score, changed = ground.swipe_board_v1(board, ground.Swipe2048Action(action))
            STUB_WORK['legality_swipes'] += 1
            if changed:
                break
        assert changed
        self.counts.update(choose_calls=1, value_predictions=4)
        STUB_WORK.update(choose_calls=1, value_predictions=4)
        return dict(action=action, afterstate=list(after), score=score, value=1., tail_value=.5,
                    status='ACTIVE', action_values={action: dict(value=1., afterstate=list(after), score=score)})


def candidate(board=SPARSE, first='DOWN', true=('DOWN', 'RIGHT', 'UP'),
              false=('RIGHT', 'UP', 'LEFT')):
    true_word, false_word = canonical_word(board, (first,)+true), canonical_word(board, (first,)+false)
    return dict(candidate_id='P0', first_action=true_word[0], probe_action=true_word[1],
                fixed_suffix=list(true_word[1:]), true_suffix=list(true_word[1:]),
                false_suffix=list(false_word[1:]), occurrences=3, condition_counts=dict(true=2, false=1))


def branch(board=SPARSE, query='risk8', program=None, arm='H2', seed=7, max_steps=7):
    bank = {q: LegalPlanner() for q in QUERIES}
    row = run_branch(board, bank, RULE, query, program, arm, seed, max_steps=max_steps)
    ROWS.append(row)
    assert all(given == QUERIES[q] for q, planner in bank.items() for _, given in planner.calls)
    return row


def source(seed, word, life=0, query='risk8'):
    generated = candidate(first=word[0], true=word[1:], false=word[1:])
    row = branch(query=query, program=generated, arm='FIXED', seed=seed, max_steps=4)
    assert row['actions'] == list(word) and row['module']['prefix_steps'] == 4
    row.update(initial_board=row['root_board'], life=life, replica=seed)
    return row


def replay_and_account(row):
    board, rng = tuple(row['root_board']), random.Random(row['seed'])
    prefix, continuation = Counter(), Counter()
    teachers = {q: Counter() for q in QUERIES}
    for step, (action, cell, rank, score, choice) in enumerate(zip(row['actions'], row['spawned_cells'],
            row['spawned_ranks'], row['scores'], row['choices'], strict=True)):
        expected_work = Counter()
        feedback = choice['feedback_event']
        if feedback is not None:
            probe_after, probe_score, legal = ground.swipe_board_v1(board,
                ground.Swipe2048Action(feedback['probe_action']))
            ORACLE['feedback_probe_swipes'] += 1
            predicate = bool(legal and probe_score > 0)
            assert step == 1 and row['arm'] == 'FEEDBACK'
            assert feedback['afterstate'] == list(probe_after) and feedback['score'] == probe_score
            assert feedback['legal'] == legal and feedback['predicate'] == predicate
            assert feedback['selected_suffix'] == row['module'][
                'actual_true_suffix' if predicate else 'actual_false_suffix']
            expected_work.update(feedback_probe_checks=1, feedback_learned_swipe_calls=1,
                                 feedback_learned_line_rewrites=4)
        attempt = choice['program_action_attempt']
        if attempt is not None:
            attempted, attempted_score, legal = ground.swipe_board_v1(board,
                ground.Swipe2048Action(attempt['action']))
            ORACLE['attempt_swipes'] += 1
            assert attempt['afterstate'] == list(attempted) and attempt['score'] == attempted_score
            assert attempt['legal'] == legal
            expected_work.update(program_action_checks=1, program_learned_swipe_calls=1,
                                 program_learned_line_rewrites=4)
        after, actual_score, changed = ground.swipe_board_v1(board, ground.Swipe2048Action(action))
        ORACLE['replay_swipes'] += 1
        assert changed and actual_score == score and choice['afterstate'] == list(after)
        assert choice['action'] == action and choice['score'] == score and choice['step'] == step
        empty = [i for i, value in enumerate(after) if not value]
        assert cell == empty[int(rng.random()*len(empty))]
        assert rank == (1 if rng.random() < 1.-row['p_four'] else 2)
        ORACLE['uniform_draws'] += 2
        board = list(after); board[cell] = rank; board = tuple(board)
        (prefix if choice['phase'] == 'prefix' else continuation).update(choice['work'])
        if choice['policy_key'] in QUERIES:
            assert choice['policy_key'] == row['query'] and choice['phase'] == 'continuation'
            teachers[row['query']].update(choose_calls=1, value_predictions=4)
            expected_work.update(forced_decisions=1)
            expected_work.update({f'policy_{row["query"]}_choose_calls': 1,
                                  f'policy_{row["query"]}_value_predictions': 4})
        else:
            assert choice['policy_key'] == 'PROGRAM' and choice['phase'] == 'prefix' and attempt['legal']
        assert Counter(choice['work']) == expected_work
    result = row['result']; n = len(row['actions']); env = result['environment_counts']
    assert row['final_board'] == list(board) and result['steps'] == n
    assert result['score'] == sum(row['scores'])
    assert env['sampled_transitions'] == env['ground_explicit_swipe_calls'] == n
    assert env['environment_random_draws'] == 2*n and env['ground_state_status_calls'] == n+1
    assert env.get('initial_spawns', 0) == 0 and result['learning_counts'] == {}
    assert Counter(result['prefix_counts']) == prefix
    assert Counter(result['continuation_counts']) == continuation
    assert Counter(result['policy_counts']) == prefix+continuation
    assert result['policy_counts_by_query'] == {q: dict(counts) for q, counts in teachers.items()}


def test_generation_uses_observed_predicates_and_excludes_holdout_before_rule_or_fields():
    rows = [source(7, ('DOWN', 'DOWN', 'RIGHT', 'UP'), life=0),
            source(10, ('DOWN', 'DOWN', 'RIGHT', 'UP'), life=1),
            source(1, ('DOWN', 'RIGHT', 'UP', 'LEFT'), life=2),
            dict(life=3, query='risk8'), dict(life=0, query='risk1')]
    generated = generate_candidates(rows, {life: RULE for life in range(3)}, 3, 'risk8')
    assert generated['candidates'] == [candidate()]
    assert generated['training_lives'] == [0, 1, 2] and len(generated['source_games']) == 3
    assert all(row['status'] == 'CUTOFF' for row in generated['source_games'])
    assert generated['counts'] == dict(source_rows_examined=5, source_games=3,
        source_state_reconstructions=12, fragment_windows=3, board_transforms=24,
        action_transports=12, postspawn_board_transforms=3, probe_checks=3,
        learned_swipe_calls=3, learned_line_rewrites=12, first_action_groups=1, eligible_groups=1)


def test_generation_preserves_original_window_frame_for_postspawn_probe():
    rows = [source(7, ('DOWN', 'DOWN', 'RIGHT', 'UP')),
            source(10, ('DOWN', 'DOWN', 'RIGHT', 'UP')),
            source(1, ('DOWN', 'RIGHT', 'UP', 'LEFT'))]
    class RecordingRule:
        def __init__(self): self.calls = []
        def swipe(self, board, action, work):
            self.calls.append((board, action)); return RULE.swipe(board, action, work)
    rule = RecordingRule()
    generate_candidates(rows, {0: rule}, 3, 'risk8')
    different = False
    for row, (recorded, action) in zip(rows, rule.calls, strict=True):
        postspawn = list(row['choices'][0]['afterstate']); postspawn[row['spawned_cells'][0]] = row['spawned_ranks'][0]
        _, frame = canonical_frame(row['initial_board'])
        expected = ground.transform_board_v1(tuple(postspawn), D4Transform(frame))
        ORACLE['board_transforms'] += 1
        assert recorded == expected and action == 'UP'
        different |= expected != canonical_frame(postspawn)[0]
    assert different


def test_generation_modal_ties_are_lexical_and_single_condition_is_valid_empty():
    true_a = source(7, ('DOWN', 'DOWN', 'RIGHT', 'UP'))
    true_b = source(10, ('DOWN', 'DOWN', 'UP', 'RIGHT'))
    false = source(1, ('DOWN', 'DOWN', 'RIGHT', 'UP'))
    generated = generate_candidates([true_a, true_b, false], {0: RULE}, 3, 'risk8')
    expected = candidate()
    expected['true_suffix'] = ['UP', 'DOWN', 'LEFT']
    expected['false_suffix'] = ['UP', 'LEFT', 'DOWN']
    assert generated['candidates'] == [expected]
    empty = generate_candidates([true_a, true_a], {0: RULE}, 3, 'risk8')
    assert empty['candidates'] == [] and empty['counts']['eligible_groups'] == 0
    assert empty['counts']['probe_checks'] == 2


@pytest.mark.parametrize('query', tuple(QUERIES))
def test_feedback_observes_new_spawn_changes_suffix_and_uses_only_own_h2(query):
    program = candidate()
    positive = branch(query=query, program=program, arm='FEEDBACK', seed=7)
    negative = branch(query=query, program=program, arm='FEEDBACK', seed=1)
    fixed = branch(query=query, program=program, arm='FIXED', seed=1)
    for row in (positive, negative, fixed):
        replay_and_account(row)
        assert row['module']['prefix_steps'] == row['module']['attempts'] == 4
        assert row['module']['exit_reason'] == 'budget' and row['module']['exit_step'] == 4
        assert [choice['policy_key'] for choice in row['choices']] == ['PROGRAM']*4+[query]*3
    assert positive['module']['predicate'] is True and negative['module']['predicate'] is False
    assert positive['actions'][:4] == ['DOWN', 'DOWN', 'RIGHT', 'UP']
    assert negative['actions'][:4] == ['DOWN', 'RIGHT', 'UP', 'LEFT']
    assert negative['actions'][0] == fixed['actions'][0]
    assert negative['spawned_cells'][0] == fixed['spawned_cells'][0]
    assert negative['spawned_ranks'][0] == fixed['spawned_ranks'][0]
    assert negative['actions'][1] != fixed['actions'][1]
    assert positive['result']['program_setup_counts'] == dict(program_board_transforms=8, program_action_transports=8)
    assert fixed['result']['program_setup_counts'] == dict(program_board_transforms=8, program_action_transports=4)


def test_feedback_transport_uses_initial_d4_frame_through_all_orientations():
    root = (0, 1, 2, 3, 4, 0, 5, 6, 7, 8, 0, 9, 10, 2, 4, 6)
    program = candidate(root, first='LEFT')
    for transform in D4_ELEMENTS:
        board = ground.transform_board_v1(root, transform)
        row = branch(board, program=program, arm='FEEDBACK', seed=7, max_steps=2)
        replay_and_account(row)
        _, original = canonical_frame(board)
        inverse = INVERSE[D4Transform(original)]
        expected = lambda actions: [ground.transform_action_v1(ground.Swipe2048Action(a), inverse).value for a in actions]
        ORACLE.update(board_transforms=1, action_transports=8)
        assert row['module']['actual_probe'] == expected([program['probe_action']])[0]
        assert row['module']['actual_true_suffix'] == expected(program['true_suffix'])
        assert row['module']['actual_false_suffix'] == expected(program['false_suffix'])


def test_illegal_first_action_exits_without_probe_without_sampling_attempt_or_reentry():
    program = candidate(first='UP')
    row = branch(program=program, arm='FEEDBACK')
    replay_and_account(row)
    assert row['module']['prefix_steps'] == 0 and row['module']['attempts'] == 1
    assert row['module']['predicate'] is None
    assert row['module']['exit_reason'] == 'illegal' and row['module']['exit_step'] == 0
    assert all(choice['feedback_event'] is None for choice in row['choices'])
    assert all(choice['policy_key'] == 'risk8' for choice in row['choices'])
    assert all(choice['program_action_attempt'] is None for choice in row['choices'][1:])
    assert row['result']['prefix_counts'] == {}
    assert row['result']['continuation_counts']['program_action_checks'] == 1


def test_illegal_feedback_suffix_exits_same_step_and_charges_probe_once():
    program = candidate(true=('UP', 'UP', 'UP'), false=('DOWN', 'DOWN', 'DOWN'))
    program['probe_action'] = canonical_word(SPARSE, ('DOWN',))[0]
    row = branch(program=program, arm='FEEDBACK', seed=0)
    replay_and_account(row)
    assert row['module']['predicate'] is False and row['module']['prefix_steps'] == 1
    assert row['module']['attempts'] == 2 and row['module']['exit_reason'] == 'illegal'
    assert row['module']['exit_step'] == 1
    assert row['choices'][1]['phase'] == 'continuation'
    assert sum(choice['feedback_event'] is not None for choice in row['choices']) == 1
    assert row['result']['continuation_counts']['feedback_probe_checks'] == 1
    assert row['result']['environment_counts']['sampled_transitions'] == 7
    assert all(choice['program_action_attempt'] is None for choice in row['choices'][2:])


def test_baseline_and_cutoff_keep_no_program_and_incomplete_prefix_costs():
    baseline = branch(max_steps=2)
    cutoff = branch(program=candidate(), arm='FEEDBACK', seed=7, max_steps=1)
    for row in (baseline, cutoff):
        replay_and_account(row)
        assert row['result']['status'] == 'CUTOFF' and row['result']['utility'] is None
    assert baseline['module'] == dict(program=None, arm='H2', canonical_board=None,
        transform=None, actual_word=[], actual_probe=None, actual_true_suffix=[],
        actual_false_suffix=[], prefix_steps=0, attempts=0, predicate=None,
        exit_reason='baseline', exit_step=0)
    assert baseline['result']['program_setup_counts'] == {} and baseline['result']['prefix_counts'] == {}
    assert cutoff['module']['exit_reason'] == 'cutoff' and cutoff['module']['exit_step'] == 1
    assert cutoff['module']['predicate'] is None and cutoff['module']['prefix_steps'] == 1


def test_winning_first_swipe_still_spawns_and_exits_without_feedback():
    board = (10, 10)+(0,)*14
    row = branch(board, program=candidate(board, first='LEFT'), arm='FEEDBACK', seed=4)
    replay_and_account(row)
    assert row['result']['status'] == 'WON' and row['result']['steps'] == 1
    assert row['result']['components'] == [1., 0., 1.] and row['result']['utility'] == 9.
    assert row['module']['exit_reason'] == 'terminal' and row['module']['exit_step'] == 1
    assert row['module']['predicate'] is None and row['choices'][0]['feedback_event'] is None
    assert row['result']['environment_counts']['environment_random_draws'] == 2
