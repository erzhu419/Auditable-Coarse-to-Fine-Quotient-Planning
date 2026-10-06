"""Consolidate observed four-action fragments, then execute one frozen word."""
from collections import Counter
from copy import deepcopy
import random
from time import perf_counter

from acfqp.domains import standard_2048 as ground
from acfqp.domains.g2048 import D4_ELEMENTS, D4Transform
from .controlled_predictive_lifelong_experience_v77 import _status
from .controlled_predictive_regime_experience_v115 import _spawn
from .controlled_predictive_policy_modules_v151 import QUERIES, counter_delta, utility

WORD_LENGTH = 4
CHOICE_KEYS = ('action', 'afterstate', 'score', 'value', 'tail_value', 'status', 'action_values')
INVERSE = {transform: transform for transform in D4_ELEMENTS}
INVERSE.update({D4Transform.ROTATE_90: D4Transform.ROTATE_270,
                D4Transform.ROTATE_270: D4Transform.ROTATE_90})


def canonical_frame(board):
    """Choose the smallest D4 board, using the fixed transform order for ties."""
    candidates = [(ground.transform_board_v1(tuple(board), transform), i, transform)
                  for i, transform in enumerate(D4_ELEMENTS)]
    canonical, _, transform = min(candidates, key=lambda row: (row[0], row[1]))
    return canonical, transform.value


def canonical_word(board, actions):
    _, transform = canonical_frame(board)
    transform = D4Transform(transform)
    return tuple(ground.transform_action_v1(ground.Swipe2048Action(action), transform).value
                 for action in actions)


def transport_word(board, canonical_actions):
    _, transform = canonical_frame(board)
    inverse = INVERSE[D4Transform(transform)]
    return tuple(ground.transform_action_v1(ground.Swipe2048Action(action), inverse).value
                 for action in canonical_actions)


def generate_candidates(source_rows, heldout_life, query, limit=4):
    """Pool observed words in the other histories without conditioning on outcomes."""
    frequencies, counts, games = Counter(), Counter(), []
    for row in source_rows:
        counts['source_rows_examined'] += 1
        if row['life'] == heldout_life or row['query'] != query:
            continue
        counts['source_games'] += 1
        board = tuple(row['initial_board'])
        boards = []
        for choice, cell, rank in zip(row['choices'], row['spawned_cells'], row['spawned_ranks'], strict=True):
            boards.append(board)
            board = list(choice['afterstate']); board[cell] = rank; board = tuple(board)
            counts['source_state_reconstructions'] += 1
        actions = row['actions']
        for start in range(len(actions)-WORD_LENGTH+1):
            word = canonical_word(boards[start], actions[start:start+WORD_LENGTH])
            frequencies[word] += 1
            counts.update(fragment_windows=1, board_transforms=8, action_transports=WORD_LENGTH)
        games.append(dict(life=row['life'], query=row['query'], replica=row['replica'],
                          seed=row['seed'], steps=len(actions), status=row['result']['status']))
    counts['unique_words'] = len(frequencies)
    selected = sorted(frequencies, key=lambda word: (-frequencies[word], word))[:limit]
    candidates = [dict(candidate_id=f'P{i}', word=list(word), occurrences=frequencies[word])
                  for i, word in enumerate(selected)]
    return dict(heldout_life=heldout_life, query=query,
                training_lives=sorted({row['life'] for row in games}), candidates=candidates,
                counts=dict(counts), source_games=games)


def run_branch(root_board, bank, rule, target_query, program, seed,
               max_steps=2000, p_four=.1):
    """Execute one root-oriented word, exiting permanently to the target H2."""
    if target_query not in QUERIES:
        raise ValueError('unknown target query')
    if program is not None and len(program) != WORD_LENGTH:
        raise ValueError('a consolidated program has exactly four actions')
    if not 0 < max_steps <= 2000:
        raise ValueError('max_steps must be between 1 and 2000')
    started = perf_counter()
    board, rng, environment = tuple(root_board), random.Random(seed), Counter()
    status = _status(board, environment)
    if status != 'ACTIVE':
        raise ValueError('the program root must be ACTIVE')
    setup = Counter()
    if program is None:
        canonical, transform, actual_word = None, None, ()
    else:
        canonical, transform = canonical_frame(board)
        inverse = INVERSE[D4Transform(transform)]
        actual_word = tuple(ground.transform_action_v1(ground.Swipe2048Action(action), inverse).value
                            for action in program)
        setup.update(program_board_transforms=8, program_action_transports=WORD_LENGTH)
    module = dict(program=None if program is None else list(program),
        canonical_board=None if canonical is None else list(canonical), transform=transform,
        actual_word=list(actual_word), prefix_steps=0, attempts=0,
        exit_reason='baseline' if program is None else None,
        exit_step=0 if program is None else None)
    prefix_active = program is not None
    teacher_before = {q: dict(bank[q].counts) for q in QUERIES}
    actions, cells, ranks, scores, choices = [], [], [], [], []
    prefix_counts, continuation_counts = Counter(), Counter()
    decision_seconds = 0.
    for step in range(max_steps):
        decision_started, work, attempt = perf_counter(), Counter(), None
        if prefix_active:
            index = module['prefix_steps']; action = actual_word[index]
            native = Counter(); after, score, legal = rule.swipe(board, action, native)
            work.update(program_action_checks=1)
            work.update({f'program_{key}': value for key, value in native.items()})
            module['attempts'] += 1
            attempt = dict(index=index, action=action, legal=bool(legal), afterstate=list(after), score=score)
            if legal:
                phase, policy = 'prefix', 'PROGRAM'
                choice = dict(action=action, afterstate=list(after), score=score)
            else:
                prefix_active = False
                module.update(exit_reason='illegal', exit_step=step)
        if not prefix_active:
            phase, policy = 'continuation', target_query
            before = dict(bank[policy].counts)
            choice = bank[policy].choose(board, QUERIES[policy])
            work.update(forced_decisions=1)
            work.update({f'policy_{policy}_{key}': value
                         for key, value in counter_delta(bank[policy].counts, before).items()})
        decision_seconds += perf_counter()-decision_started
        (prefix_counts if phase == 'prefix' else continuation_counts).update(work)
        compact = {key: deepcopy(choice[key]) for key in CHOICE_KEYS if key in choice}
        compact.update(step=step, phase=phase, policy_key=policy,
                       program_action_attempt=attempt, module_decision=None, work=dict(work))
        action = ground.Swipe2048Action(choice['action'])
        environment.update(ground_explicit_swipe_calls=1, ground_swipe_calls=1)
        after, score, changed = ground.swipe_board_v1(board, action)
        if not changed:
            raise ValueError(f'illegal executed action {action.value} at step {step}')
        board, cell, rank = _spawn(after, rng, environment, p_four)
        environment['sampled_transitions'] += 1
        status = _status(board, environment)
        choices.append(compact); actions.append(action.value); cells.append(cell)
        ranks.append(rank); scores.append(score)
        if phase == 'prefix':
            module['prefix_steps'] += 1
            reason = ('terminal' if status != 'ACTIVE' else
                      'budget' if module['prefix_steps'] == WORD_LENGTH else None)
            if reason is not None:
                module.update(exit_reason=reason, exit_step=step+1)
                prefix_active = False
        if status != 'ACTIVE':
            break
    if status == 'ACTIVE':
        status = 'CUTOFF'
    if prefix_active:
        module.update(exit_reason='cutoff', exit_step=len(actions))
    components = [sum(scores)/2048., float(status == 'LOST'), float(status == 'WON')]
    result = dict(score=sum(scores), steps=len(actions), status=status, components=components,
        utility=None if status == 'CUTOFF' else utility(components, target_query),
        environment_counts=dict(environment), policy_counts=dict(prefix_counts+continuation_counts),
        prefix_counts=dict(prefix_counts), continuation_counts=dict(continuation_counts),
        policy_counts_by_query={q: counter_delta(bank[q].counts, teacher_before[q]) for q in QUERIES},
        program_setup_counts=dict(setup), learning_counts={},
        decision_seconds=decision_seconds, seconds=perf_counter()-started)
    return dict(root_board=list(root_board), query=target_query, seed=seed,
        max_steps=max_steps, p_four=p_four, actions=actions, spawned_cells=cells,
        spawned_ranks=ranks, scores=scores, choices=choices, final_board=list(board),
        module=module, result=result)
