"""Four fixed module/continuation interventions with frozen V151 gates."""
from collections import Counter
from copy import deepcopy
import random
from time import perf_counter

from acfqp.domains import standard_2048 as ground
from .controlled_predictive_lifelong_experience_v77 import _status
from .controlled_predictive_regime_experience_v115 import _spawn
from .controlled_predictive_policy_modules_v151 import (
    ModuleGate, QUERIES, counter_delta, utility)

MODES = ('H_H2', 'M_H2', 'H_GATE', 'M_GATE')
CHOICE_KEYS = ('action', 'afterstate', 'score', 'value', 'tail_value', 'status', 'action_values')


def run_branch(root_board, bank, target_query, mode, model, seed,
               max_steps=2000, p_four=.1):
    """Force one H2 step or eight other-policy steps, then the named continuation.

    Gates start fresh after the prefix and receive the absolute branch step.
    Every planner is bound to its own query, including the other-policy prefix.
    """
    if mode not in MODES or target_query not in QUERIES:
        raise ValueError('unknown branch mode or target query')
    if not 0 < max_steps <= 2000:
        raise ValueError('max_steps must be between 1 and 2000')
    if not 0. <= p_four <= 1.:
        raise ValueError('p_four must be between zero and one')
    started = perf_counter()
    other = 'risk8' if target_query == 'risk1' else 'risk1'
    prefix_steps = 8 if mode.startswith('M_') else 1
    prefix_policy = other if mode.startswith('M_') else target_query
    gate = (ModuleGate(bank, target_query, 8, model, mode='LEARNED')
            if mode.endswith('_GATE') else None)
    board, rng, environment = tuple(root_board), random.Random(seed), Counter()
    if _status(board, environment) != 'ACTIVE':
        raise ValueError('the diagnostic root must be ACTIVE')
    teacher_before = {q: dict(bank[q].counts) for q in QUERIES}
    actions, cells, ranks, scores, choices = [], [], [], [], []
    prefix_counts, continuation_counts = Counter(), Counter()
    decision_seconds = 0.
    for step in range(max_steps):
        phase = 'prefix' if step < prefix_steps else 'continuation'
        decision_started = perf_counter()
        if phase == 'continuation' and gate is not None:
            before = dict(gate.counts)
            choice = gate.choose(board, step)
            work = counter_delta(gate.counts, before)
            module_decision = deepcopy(choice['module_decision'])
            policy = module_decision['policy_key']
        else:
            policy = prefix_policy if phase == 'prefix' else target_query
            before = dict(bank[policy].counts)
            choice = bank[policy].choose(board, QUERIES[policy])
            work = dict(forced_decisions=1, **{
                f'policy_{policy}_{key}': value
                for key, value in counter_delta(bank[policy].counts, before).items()})
            module_decision = None
        decision_seconds += perf_counter()-decision_started
        (prefix_counts if phase == 'prefix' else continuation_counts).update(work)
        compact = {key: deepcopy(choice[key]) for key in CHOICE_KEYS if key in choice}
        compact.update(step=step, phase=phase, policy_key=policy,
                       module_decision=module_decision, work=work)
        action = ground.Swipe2048Action(choice['action'])
        environment.update(ground_explicit_swipe_calls=1, ground_swipe_calls=1)
        after, score, changed = ground.swipe_board_v1(board, action)
        if not changed:
            raise ValueError(f'illegal action {action.value} at step {step}')
        board, cell, rank = _spawn(after, rng, environment, p_four)
        environment['sampled_transitions'] += 1
        status = _status(board, environment)
        choices.append(compact); actions.append(action.value); cells.append(cell)
        ranks.append(rank); scores.append(score)
        if status != 'ACTIVE':
            break
    if status == 'ACTIVE':
        status = 'CUTOFF'
    components = [sum(scores)/2048., float(status == 'LOST'), float(status == 'WON')]
    result = dict(score=sum(scores), steps=len(actions), status=status, components=components,
        utility=None if status == 'CUTOFF' else utility(components, target_query),
        environment_counts=dict(environment), policy_counts=dict(prefix_counts+continuation_counts),
        prefix_counts=dict(prefix_counts), continuation_counts=dict(continuation_counts),
        policy_counts_by_query={q: counter_delta(bank[q].counts, teacher_before[q]) for q in QUERIES},
        learning_counts={}, decision_seconds=decision_seconds, seconds=perf_counter()-started)
    return dict(root_board=list(root_board), query=target_query, mode=mode, seed=seed,
        max_steps=max_steps, p_four=p_four, actions=actions, spawned_cells=cells,
        spawned_ranks=ranks, scores=scores, choices=choices, final_board=list(board), result=result)
