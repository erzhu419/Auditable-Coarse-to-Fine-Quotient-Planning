"""Finish V78 training branches under their original continuation policy."""
from collections import Counter
from time import perf_counter

from acfqp.science.controlled_predictive_lifelong_planner_v77 import policy_action
from acfqp.science.controlled_predictive_terminal_continuation_v79 import extend_episode


def complete_training_branch(raw, rule, max_total_steps=2000):
    """Return a complete game, separate cost log, and newly sampled suffix.

    V78 already forced ``raw['action']`` at its root. Every new action follows
    ``raw['policy']`` while reusing the original environment random stream.
    No planning RNG or validation trajectory is needed for this continuation.
    The returned game's work includes inherited transitions; the log separates
    them from work newly performed here for experimental cost accounting.
    """
    started = perf_counter()
    prefix = raw['game']
    policy_work = Counter()

    def act(board, _absolute_step):
        return policy_action(board, raw['policy'], rule, policy_work)

    extension = extend_episode(prefix, act, max_total_steps=max_total_steps)
    suffix = extension['suffix']
    work = Counter(prefix['work'])
    work.update(suffix['work'])
    complete_game = dict(prefix)
    complete_game.update(
        final_board=suffix['final_board'], status=extension['status'],
        return_score=extension['total_score'], steps_count=extension['total_steps'],
        steps=prefix['steps'] + suffix['steps'], work=dict(work),
    )
    seconds = perf_counter() - started
    complete_game['seconds'] = prefix['seconds'] + seconds
    log = dict(
        prefix_work=dict(prefix['work']), new_work=dict(suffix['work']),
        policy_work=dict(policy_work),
        restoration_random_draws=extension['restoration_random_draws'],
        resumed=extension['resumed'], seconds=seconds,
        prefix_steps=prefix['steps_count'], new_steps=suffix['steps_count'],
        total_steps=extension['total_steps'], status=extension['status'],
    )
    return complete_game, log, suffix
