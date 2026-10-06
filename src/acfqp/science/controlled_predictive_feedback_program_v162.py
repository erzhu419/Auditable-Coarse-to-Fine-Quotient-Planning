"""Consolidate a source-observed conditional suffix and execute it once."""
from collections import Counter, defaultdict
from copy import deepcopy
import random
from time import perf_counter

from acfqp.domains import standard_2048 as ground
from acfqp.domains.g2048 import D4Transform
from .controlled_predictive_lifelong_experience_v77 import _status
from .controlled_predictive_regime_experience_v115 import _spawn
from .controlled_predictive_policy_modules_v151 import QUERIES, counter_delta, utility
from .controlled_predictive_program_consolidation_v161 import (
    CHOICE_KEYS, INVERSE, WORD_LENGTH, canonical_frame)


def _modal_suffix(frequencies):
    return min(frequencies, key=lambda suffix: (-frequencies[suffix], suffix))


def generate_candidates(source_rows, rules_by_life, heldout_life, query, limit=2):
    """Use observed postspawn feedback; exclude the held-out life before access."""
    groups, counts, games = defaultdict(list), Counter(), []
    for row in source_rows:
        counts['source_rows_examined'] += 1
        if row['life'] == heldout_life or row['query'] != query:
            continue
        rule = rules_by_life[row['life']]
        counts['source_games'] += 1
        board, boards, postspawn = tuple(row['initial_board']), [], []
        for choice, cell, rank in zip(row['choices'], row['spawned_cells'],
                                     row['spawned_ranks'], strict=True):
            boards.append(board)
            board = list(choice['afterstate']); board[cell] = rank; board = tuple(board)
            postspawn.append(board)
            counts['source_state_reconstructions'] += 1
        actions = row['actions']
        for start in range(len(actions)-WORD_LENGTH+1):
            _, transform = canonical_frame(boards[start])
            transform = D4Transform(transform)
            word = tuple(ground.transform_action_v1(ground.Swipe2048Action(action), transform).value
                         for action in actions[start:start+WORD_LENGTH])
            groups[word[0]].append((word[1:], postspawn[start], transform, rule))
            counts.update(fragment_windows=1, board_transforms=8, action_transports=WORD_LENGTH)
        games.append(dict(life=row['life'], query=row['query'], replica=row['replica'],
                          seed=row['seed'], steps=len(actions), status=row['result']['status']))
    eligible = []
    for first_action, windows in groups.items():
        fixed_suffix = _modal_suffix(Counter(window[0] for window in windows))
        probe = fixed_suffix[0]
        conditional = {True: Counter(), False: Counter()}
        for suffix, board, transform, rule in windows:
            observed = ground.transform_board_v1(board, transform)
            counts.update(postspawn_board_transforms=1, probe_checks=1)
            native = Counter()
            _, score, changed = rule.swipe(observed, probe, native)
            counts.update(native)
            conditional[bool(changed and score > 0)][suffix] += 1
        if not conditional[True] or not conditional[False]:
            continue
        true_suffix, false_suffix = (_modal_suffix(conditional[value]) for value in (True, False))
        if true_suffix == false_suffix:
            continue
        eligible.append(dict(first_action=first_action, probe_action=probe,
            fixed_suffix=list(fixed_suffix), true_suffix=list(true_suffix),
            false_suffix=list(false_suffix), occurrences=len(windows),
            condition_counts=dict(true=sum(conditional[True].values()),
                                  false=sum(conditional[False].values()))))
    counts.update(first_action_groups=len(groups), eligible_groups=len(eligible))
    selected = sorted(eligible, key=lambda candidate: (-candidate['occurrences'], candidate['first_action']))[:limit]
    candidates = [dict(candidate_id=f'P{i}', **candidate) for i, candidate in enumerate(selected)]
    return dict(heldout_life=heldout_life, query=query,
                training_lives=sorted({row['life'] for row in games}), candidates=candidates,
                counts=dict(counts), source_games=games)


def run_branch(root_board, bank, rule, target_query, program, arm, seed,
               max_steps=2000, p_four=.1):
    """Transport once, observe one spawned board, and exit permanently to own H2."""
    if target_query not in QUERIES:
        raise ValueError('unknown target query')
    if arm not in ('H2', 'FIXED', 'FEEDBACK') or (arm == 'H2') != (program is None):
        raise ValueError('H2 has no program; FIXED and FEEDBACK require a candidate')
    if not 0 < max_steps <= 2000:
        raise ValueError('max_steps must be between 1 and 2000')
    started = perf_counter()
    board, rng, environment = tuple(root_board), random.Random(seed), Counter()
    status = _status(board, environment)
    if status != 'ACTIVE':
        raise ValueError('the program root must be ACTIVE')
    setup = Counter()
    canonical, transform, actual_word, actual_probe = None, None, (), None
    true_suffix, false_suffix = (), ()
    if program is not None:
        canonical, transform = canonical_frame(board)
        inverse = INVERSE[D4Transform(transform)]
        def transport(actions):
            return tuple(ground.transform_action_v1(ground.Swipe2048Action(action), inverse).value
                         for action in actions)
        if arm == 'FIXED':
            actual_word = transport([program['first_action']]+program['fixed_suffix'])
            setup.update(program_board_transforms=8, program_action_transports=WORD_LENGTH)
        else:
            actual_word = transport([program['first_action']])
            actual_probe, = transport([program['probe_action']])
            true_suffix, false_suffix = transport(program['true_suffix']), transport(program['false_suffix'])
            setup.update(program_board_transforms=8, program_action_transports=8)
    module = dict(program=deepcopy(program), arm=arm,
        canonical_board=None if canonical is None else list(canonical), transform=transform,
        actual_word=list(actual_word), actual_probe=actual_probe,
        actual_true_suffix=list(true_suffix), actual_false_suffix=list(false_suffix),
        prefix_steps=0, attempts=0, predicate=None,
        exit_reason='baseline' if program is None else None,
        exit_step=0 if program is None else None)
    prefix_active = program is not None
    teacher_before = {q: dict(bank[q].counts) for q in QUERIES}
    actions, cells, ranks, scores, choices = [], [], [], [], []
    prefix_counts, continuation_counts = Counter(), Counter()
    decision_seconds = 0.
    for step in range(max_steps):
        decision_started, work, attempt, feedback = perf_counter(), Counter(), None, None
        if prefix_active:
            index = module['prefix_steps']
            if arm == 'FEEDBACK' and index == 1:
                native = Counter()
                probe_after, probe_score, probe_legal = rule.swipe(board, actual_probe, native)
                predicate = bool(probe_legal and probe_score > 0)
                selected = true_suffix if predicate else false_suffix
                actual_word = actual_word[:1]+selected
                module.update(predicate=predicate, actual_word=list(actual_word))
                feedback = dict(probe_action=actual_probe, afterstate=list(probe_after),
                    score=probe_score, legal=bool(probe_legal), predicate=predicate,
                    selected_suffix=list(selected))
                work.update(feedback_probe_checks=1)
                work.update({f'feedback_{key}': value for key, value in native.items()})
            action = actual_word[index]
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
                       program_action_attempt=attempt, feedback_event=feedback,
                       module_decision=None, work=dict(work))
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
    return dict(root_board=list(root_board), query=target_query, arm=arm, seed=seed,
        max_steps=max_steps, p_four=p_four, actions=actions, spawned_cells=cells,
        spawned_ranks=ranks, scores=scores, choices=choices, final_board=list(board),
        module=module, result=result)
