"""Program orientation, history exclusion, permanent exits, and sampled costs."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path
import random

import pytest

from acfqp.domains import standard_2048 as ground
from acfqp.domains.g2048 import D4_ELEMENTS
from acfqp.science.controlled_predictive_program_consolidation_v161 import (
    QUERIES, canonical_frame, canonical_word, generate_candidates, run_branch, transport_word)
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics, RewriteProgram

TEMP = Path(__file__).resolve().parents[1]/'reports/v161_runtime_tmp'
ROWS, ORACLE, STUB_WORK = [], Counter(), Counter()
SPARSE = [1, 1]+[0]*14
ASYMMETRIC = (0, 1, 2, 3, 4, 0, 5, 6, 7, 8, 0, 9, 10, 2, 4, 6)
RULE = LearnedDynamics(RewriteProgram(True, 'equal', 1, 'once', 'output_value'),
                       ((1, Fraction(9, 10)), (2, Fraction(1, 10))), 'uniform')


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    TEMP.mkdir(parents=True, exist_ok=True); before = request.session.testsfailed
    yield
    path = TEMP/'core_checks.json'
    payload = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    environment = sum((Counter(r['result']['environment_counts']) for r in ROWS), Counter())
    policy = sum((Counter(r['result']['policy_counts']) for r in ROWS), Counter())
    setup = sum((Counter(r['result']['program_setup_counts']) for r in ROWS), Counter())
    payload['attempts'].append(dict(tests=sum(i.module.__name__ == __name__ for i in request.session.items),
        failures=request.session.testsfailed-before, environment_counts=dict(environment),
        newly_sampled_environment_transitions=environment['sampled_transitions'],
        newly_sampled_model_transitions=0, real_training_updates=0, native_planner_calls=0,
        policy_stub_work=dict(STUB_WORK), deterministic_oracle_work=dict(ORACLE),
        policy_counts=dict(policy), program_setup_counts=dict(setup),
        scope='Finite stub-teacher branches, D4 and fragment fixtures; no native planner or fitting.'))
    path.write_text(json.dumps(payload, indent=2)+'\n')


class LegalPlanner:
    def __init__(self, cycle=('LEFT', 'DOWN', 'RIGHT', 'UP')):
        self.cycle, self.calls = cycle, []
        self.counts = Counter(choose_calls=11, value_predictions=13)

    def choose(self, board, query):
        index = len(self.calls) % 4; order = self.cycle[index:]+self.cycle[:index]
        self.calls.append((tuple(board), deepcopy(query)))
        for action in order:
            after, score, changed = ground.swipe_board_v1(board, ground.Swipe2048Action(action))
            STUB_WORK['legality_swipes'] += 1
            if changed:
                break
        assert changed
        self.counts.update(choose_calls=1, value_predictions=4)
        STUB_WORK.update(choose_calls=1, value_predictions=4)
        return dict(action=action, afterstate=list(after), score=score, value=1., tail_value=.5,
                    status='ACTIVE', action_values={action: dict(value=1., afterstate=list(after), score=score)})


def branch(board, query='risk8', actual_word=None, seed=123, max_steps=7, cycle=None):
    bank = {q: LegalPlanner(cycle or ('LEFT', 'DOWN', 'RIGHT', 'UP')) for q in QUERIES}
    word = None if actual_word is None else canonical_word(board, actual_word)
    row = run_branch(board, bank, RULE, query, word, seed, max_steps=max_steps)
    ROWS.append(row)
    assert all(given == QUERIES[q] for q, planner in bank.items() for _, given in planner.calls)
    return row


def replay_and_account(row):
    board, rng = tuple(row['root_board']), random.Random(row['seed'])
    prefix, continuation = Counter(), Counter()
    teachers = {q: Counter() for q in QUERIES}
    for step, (action, cell, rank, score, choice) in enumerate(zip(row['actions'], row['spawned_cells'],
            row['spawned_ranks'], row['scores'], row['choices'], strict=True)):
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
            assert choice['policy_key'] == row['query']
            teachers[row['query']].update(choose_calls=1, value_predictions=4)
        else:
            assert choice['policy_key'] == 'PROGRAM'
            assert choice['work'] == dict(program_action_checks=1,
                program_learned_swipe_calls=1, program_learned_line_rewrites=4)
    result = row['result']; n = len(row['actions']); env = result['environment_counts']
    assert row['final_board'] == list(board) and result['steps'] == n
    assert result['score'] == sum(row['scores'])
    assert env['sampled_transitions'] == env['ground_explicit_swipe_calls'] == n
    assert env['environment_random_draws'] == 2*n and env['ground_state_status_calls'] == n+1
    assert env.get('initial_spawns', 0) == 0 and result['learning_counts'] == {}
    assert Counter(result['prefix_counts']) == prefix
    assert Counter(result['continuation_counts']) == continuation
    assert Counter(result['policy_counts']) == prefix+continuation
    assert result['policy_counts_by_query'] == {q: dict(c) for q, c in teachers.items()}


def test_d4_action_transport_commutes_with_swipes_and_normalizes_asymmetric_words():
    word = ('LEFT', 'DOWN', 'RIGHT', 'UP')
    frame, _ = canonical_frame(ASYMMETRIC)
    expected = canonical_word(ASYMMETRIC, word)
    for transform in D4_ELEMENTS:
        changed_board = ground.transform_board_v1(ASYMMETRIC, transform)
        changed_word = tuple(ground.transform_action_v1(ground.Swipe2048Action(a), transform).value for a in word)
        ORACLE.update(board_transforms=1, action_transports=4)
        assert canonical_frame(changed_board)[0] == frame
        assert canonical_word(changed_board, changed_word) == expected
        assert transport_word(changed_board, expected) == changed_word
        for action in ground.Swipe2048Action:
            after, score, changed = ground.swipe_board_v1(ASYMMETRIC, action)
            moved = ground.transform_action_v1(action, transform)
            alternate, alternate_score, alternate_changed = ground.swipe_board_v1(changed_board, moved)
            transformed_after = ground.transform_board_v1(after, transform)
            ORACLE.update(commutation_swipes=2, board_transforms=1, action_transports=1)
            assert (alternate, alternate_score, alternate_changed) == (transformed_after, score, changed)


def test_symmetric_frame_uses_first_transform_and_word_roundtrip():
    assert canonical_frame((1,)*16) == ((1,)*16, 'identity')
    word = ('UP', 'UP', 'LEFT', 'DOWN')
    assert canonical_word((1,)*16, word) == word
    assert transport_word((1,)*16, word) == word


def test_generation_excludes_holdout_before_processing_and_keeps_all_observed_windows():
    source = []
    for life in range(3):
        row = branch(SPARSE, actual_word=None, seed=10+life, max_steps=6)
        row.update(initial_board=row['root_board'], life=life, replica=0)
        source.append(row)
    source += [dict(life=3, query='risk8'), dict(life=0, query='risk1')]
    generated = generate_candidates(source, 3, 'risk8')
    expected = Counter()
    for row in source[:3]:
        board = tuple(row['initial_board'])
        boards = []
        for choice, cell, rank in zip(row['choices'], row['spawned_cells'], row['spawned_ranks'], strict=True):
            boards.append(board); board = list(choice['afterstate']); board[cell] = rank; board = tuple(board)
        for start in range(3):
            transformed = [(ground.transform_board_v1(boards[start], t), i, t) for i, t in enumerate(D4_ELEMENTS)]
            _, _, transform = min(transformed)
            word = tuple(ground.transform_action_v1(ground.Swipe2048Action(a), transform).value
                         for a in row['actions'][start:start+4])
            expected[word] += 1; ORACLE.update(board_transforms=8, action_transports=4)
    selected = sorted(expected, key=lambda word: (-expected[word], word))[:4]
    assert generated['candidates'] == [dict(candidate_id=f'P{i}', word=list(word), occurrences=expected[word])
                                        for i, word in enumerate(selected)]
    assert generated['training_lives'] == [0, 1, 2]
    assert len(generated['source_games']) == 3 and all(g['status'] == 'CUTOFF' for g in generated['source_games'])
    assert generated['counts'] == dict(source_rows_examined=5, source_games=3,
        source_state_reconstructions=18, fragment_windows=9, board_transforms=72,
        action_transports=36, unique_words=len(expected))


@pytest.mark.parametrize('query', tuple(QUERIES))
def test_legal_word_finishes_four_steps_then_only_own_h2(query):
    row = branch([1]*16, query, ('LEFT', 'DOWN', 'RIGHT', 'UP'))
    replay_and_account(row)
    assert row['module']['actual_word'] == ['LEFT', 'DOWN', 'RIGHT', 'UP']
    assert row['module']['prefix_steps'] == row['module']['attempts'] == 4
    assert row['module']['exit_reason'] == 'budget' and row['module']['exit_step'] == 4
    assert [c['policy_key'] for c in row['choices']] == ['PROGRAM']*4+[query]*3
    assert row['result']['program_setup_counts'] == dict(program_board_transforms=8, program_action_transports=4)


@pytest.mark.parametrize('query', tuple(QUERIES))
def test_illegal_word_exits_without_sampling_attempt_and_never_reenters(query):
    row = branch([1]+[0]*15, query, ('UP', 'DOWN', 'RIGHT', 'LEFT'))
    replay_and_account(row)
    module = row['module']
    assert module['prefix_steps'] == 0 and module['attempts'] == 1
    assert module['exit_reason'] == 'illegal' and module['exit_step'] == 0
    assert [c['policy_key'] for c in row['choices']] == [query]*7
    attempt = row['choices'][0]['program_action_attempt']
    assert attempt == dict(index=0, action='UP', legal=False, afterstate=[1]+[0]*15, score=0)
    assert all(c['program_action_attempt'] is None for c in row['choices'][1:])
    assert row['result']['prefix_counts'] == {}
    assert row['result']['continuation_counts']['program_action_checks'] == 1
    assert row['result']['environment_counts']['sampled_transitions'] == 7


def test_baseline_has_no_program_cost_and_cutoff_keeps_incomplete_prefix():
    baseline = branch(SPARSE, max_steps=2)
    truncated = branch([1]*16, actual_word=('LEFT', 'DOWN', 'RIGHT', 'UP'), max_steps=2)
    for row in (baseline, truncated):
        replay_and_account(row)
        assert row['result']['status'] == 'CUTOFF' and row['result']['utility'] is None
    assert baseline['module'] == dict(program=None, canonical_board=None, transform=None,
        actual_word=[], prefix_steps=0, attempts=0, exit_reason='baseline', exit_step=0)
    assert baseline['result']['program_setup_counts'] == {} and baseline['result']['prefix_counts'] == {}
    assert truncated['module']['prefix_steps'] == truncated['module']['attempts'] == 2
    assert truncated['module']['exit_reason'] == 'cutoff' and truncated['module']['exit_step'] == 2


def test_illegal_second_action_is_charged_and_falls_back_on_same_step():
    row = branch(SPARSE, actual_word=('LEFT',)*4)
    replay_and_account(row)
    assert row['module']['prefix_steps'] == 1 and row['module']['attempts'] == 2
    assert row['module']['exit_reason'] == 'illegal' and row['module']['exit_step'] == 1
    assert [c['policy_key'] for c in row['choices']] == ['PROGRAM']+['risk8']*6
    assert row['choices'][1]['program_action_attempt']['legal'] is False
    assert row['choices'][1]['phase'] == 'continuation'
    assert row['result']['prefix_counts']['program_action_checks'] == 1
    assert row['result']['continuation_counts']['program_action_checks'] == 1
    assert row['result']['environment_counts']['sampled_transitions'] == 7


def test_winning_swipe_still_spawns_and_exits_terminal_before_budget():
    row = branch([10, 10]+[0]*14, actual_word=('LEFT', 'DOWN', 'RIGHT', 'UP'), seed=4)
    replay_and_account(row)
    assert row['result']['status'] == 'WON' and row['result']['steps'] == 1
    assert row['result']['components'] == [1., 0., 1.] and row['result']['utility'] == 9.
    assert row['module']['exit_reason'] == 'terminal' and row['module']['exit_step'] == 1
    assert row['module']['prefix_steps'] == row['module']['attempts'] == 1
    assert row['result']['environment_counts']['environment_random_draws'] == 2
