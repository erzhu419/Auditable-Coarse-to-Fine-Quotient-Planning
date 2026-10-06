"""Actual-environment action branches with a fixed frozen continuation policy."""
from collections import Counter
import random
from time import perf_counter

from acfqp.domains import standard_2048 as ground
from .controlled_predictive_lifelong_experience_v77 import _status
from .controlled_predictive_regime_experience_v115 import _spawn


def run_branch(root_board, first_action, planner, query_dict, seed,
               max_steps=2000, p_four=.1):
    """Force one candidate action, then run H2 with the same suffix RNG seed.

    There are no initial spawns. Each executed action uses the next position
    and rank uniforms, including an action that creates the goal tile. The
    compact action/spawn arrays reconstruct every board without planner replay.
    """
    if not 0.0 <= p_four <= 1.0:
        raise ValueError('p_four must be between zero and one')
    if max_steps <= 0:
        raise ValueError('max_steps must be positive')
    started = perf_counter()
    board = tuple(root_board)
    action = ground.Swipe2048Action(first_action)
    rng, work = random.Random(seed), Counter()
    if _status(board, work) != 'ACTIVE':
        raise ValueError('the counterfactual root must be ACTIVE')
    before = dict(planner.counts)
    actions, cells, ranks, scores = [], [], [], []
    decision_seconds = 0.
    for index in range(max_steps):
        if index:
            decision_started = perf_counter()
            choice = planner.choose(board, query_dict)
            decision_seconds += perf_counter()-decision_started
            action = ground.Swipe2048Action(choice['action'])
            work['continuation_actions'] += 1
        else:
            work['forced_actions'] += 1
        work['ground_explicit_swipe_calls'] += 1
        work['ground_swipe_calls'] += 1
        afterstate, score, changed = ground.swipe_board_v1(board, action)
        if not changed:
            raise ValueError(f'illegal action {action.value} at step {index}')
        board, cell, rank = _spawn(afterstate, rng, work, p_four)
        work['sampled_transitions'] += 1
        status = _status(board, work)
        if not index:
            first_afterstate, first_exit = list(afterstate), list(board)
        actions.append(action.value)
        cells.append(cell)
        ranks.append(rank)
        scores.append(score)
        if status != 'ACTIVE':
            break
    if status == 'ACTIVE':
        status = 'CUTOFF'
    return_score = sum(scores)
    components = [return_score/2048., float(status == 'LOST'), float(status == 'WON')]
    utility = None if status == 'CUTOFF' else (
        components[0]-query_dict['failure_penalty']*components[1]
        +query_dict['goal_bonus']*components[2])
    policy_counts = {key: value-before.get(key, 0) for key, value in planner.counts.items()
                     if value != before.get(key, 0)}
    result = dict(score=return_score, steps=len(actions), status=status,
        components=components, utility=utility, environment_counts=dict(work),
        policy_counts=policy_counts, learning_counts={}, forced_action_count=1,
        continuation_decisions=len(actions)-1, decision_seconds=decision_seconds,
        seconds=perf_counter()-started)
    return dict(seed=seed, root_board=list(root_board), first_action=actions[0],
        first_afterstate=first_afterstate, first_exit=first_exit,
        actions=actions, spawned_cells=cells, spawned_ranks=ranks, scores=scores,
        final_board=list(board), result=result)
