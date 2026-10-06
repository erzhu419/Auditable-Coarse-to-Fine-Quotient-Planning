"""Paired first-divergence diagnosis with fixed-policy forced continuations."""
from collections import Counter
import json
from pathlib import Path
import random
from time import perf_counter

import numpy as np

from acfqp.domains import standard_2048 as ground
from .controlled_predictive_anchored_success_v127 import AnchoredSuccess, SCHEMA
from .controlled_predictive_lifelong_experience_v77 import _status
from .controlled_predictive_ntuple_td_v120 import PATTERNS
from .controlled_predictive_regime_experience_v115 import _spawn


def board_at_first_divergence(left, right, rule):
    """Reconstruct only the shared recorded prefix before two choices differ."""
    started = perf_counter(); work = Counter()
    if left['seed'] != right['seed'] or left['initial_board'] != right['initial_board']:
        raise ValueError('first-divergence histories must share seed and initial board')
    board = tuple(left['initial_board'])
    for row in (left, right):
        if any(len(row[key]) != len(row['actions']) for key in ('scores', 'spawned_cells', 'spawned_ranks')):
            raise ValueError('retained transition arrays must align')
    for index, (left_action, right_action) in enumerate(zip(left['actions'], right['actions'])):
        if left_action != right_action:
            return dict(diverged=True, index=index, board=list(board), left_action=left_action,
                right_action=right_action, shared_prefix_steps=index, counts=dict(work),
                seconds=perf_counter() - started)
        if any(left[key][index] != right[key][index] for key in ('scores', 'spawned_cells', 'spawned_ranks')):
            raise ValueError('recorded common-action prefix has different score or spawn')
        afterstate, score, changed = rule.swipe(board, left_action, work)
        cell, rank = left['spawned_cells'][index], left['spawned_ranks'][index]
        if not changed or score != left['scores'][index]:
            raise ValueError('recorded common prefix disagrees with identified swipe program')
        if cell not in range(16) or afterstate[cell] != 0 or rank not in (1, 2):
            raise ValueError('recorded common prefix has an invalid spawn')
        successor = list(afterstate); successor[cell] = rank; board = tuple(successor)
        work['recorded_spawns_replayed'] += 1
    if len(left['actions']) != len(right['actions']):
        raise ValueError('identical action prefix cannot have different recorded stopping lengths')
    if list(board) != left['final_board'] or list(board) != right['final_board']:
        raise ValueError('identical histories have inconsistent final boards')
    return dict(diverged=False, index=None, board=None, left_action=None, right_action=None,
        shared_prefix_steps=len(left['actions']), counts=dict(work), seconds=perf_counter() - started)


def run_forced_continuation(board, first_action, frozen_source_model, source_query,
                            seed, max_steps=2000):
    """Real environment from a retained board, forced once then fixed policy.

    No initial tiles are generated. A spawn follows every executed swipe,
    including a winning swipe, exactly as in the V115 episode interface.
    """
    if max_steps <= 0:
        raise ValueError('forced continuation needs a positive action budget')
    started = perf_counter(); rng = random.Random(seed); work = Counter()
    initial = board = tuple(board)
    status = _status(board, work)
    if status != 'ACTIVE':
        raise ValueError('forced continuation must start from an active decision board')
    source_before, updates = dict(frozen_source_model.counts), frozen_source_model.updates
    steps, return_score = [], 0
    for index in range(max_steps):
        if index == 0:
            action_name = first_action; work['forced_actions'] += 1
        else:
            action_name = frozen_source_model.choose(board, source_query)['action']
        action = ground.Swipe2048Action(action_name)
        work['ground_explicit_swipe_calls'] += 1
        work['ground_swipe_calls'] += 1
        afterstate, score, changed = ground.swipe_board_v1(board, action)
        if not changed:
            raise ValueError(f'illegal forced-continuation action {action_name} at step {index}')
        successor, cell, rank = _spawn(afterstate, rng, work, .1)
        work['sampled_transitions'] += 1
        status = _status(successor, work)
        steps.append(dict(board=list(board), action=action_name, afterstate=list(afterstate),
            next_board=list(successor), score=score, status=status, spawned_cell=cell, spawned_rank=rank))
        return_score += score; board = successor
        if status != 'ACTIVE': break
    if status == 'ACTIVE': status = 'CUTOFF'
    if frozen_source_model.updates != updates:
        raise AssertionError('forced continuation changed its frozen source model')
    return dict(seed=seed, initial_board=list(initial), initial_spawns=[], final_board=list(board),
        status=status, return_score=return_score, steps_count=len(steps), steps=steps,
        work=dict(work), policy_counts={key: value - source_before.get(key, 0)
            for key, value in frozen_source_model.counts.items() if value != source_before.get(key, 0)},
        source_updates_before=updates, source_updates_after=frozen_source_model.updates,
        forced_action=first_action, seconds=perf_counter() - started)


def load_anchored_success(path, source_model, source_query, build_dir):
    """Load count state without inheriting historical work into new counters."""
    started = perf_counter(); path = Path(path)
    with np.load(path, allow_pickle=False) as data:
        metadata = json.loads(str(data['metadata']))
        if (metadata['schema'] != SCHEMA or metadata['radix'] != source_model.radix
                or metadata['patterns'] != [list(row) for row in PATTERNS]
                or metadata['source_query'] != source_query
                or metadata['source_updates'] != source_model.updates):
            raise ValueError('success checkpoint does not match its frozen scalar source')
        result = AnchoredSuccess(source_model, source_query, build_dir)
        result.visits.reshape(-1)[data['indices']] = data['visits']
        result.wins.reshape(-1)[data['indices']] = data['wins']
        result.updates, result.successes = metadata['updates'], metadata['successes']
        result.load_counts = dict(checkpoint_loads=1, checkpoint_loaded_addresses=len(data['indices']),
            checkpoint_loaded_count_entries=2 * len(data['indices']))
        result.counts.update(result.load_counts)
    result.source.weights.flags.writeable = False
    result.visits.flags.writeable = False; result.wins.flags.writeable = False
    result.loaded_metadata = metadata
    result.last_load_seconds = perf_counter() - started
    return result
