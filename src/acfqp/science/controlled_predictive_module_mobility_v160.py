"""A bounded mobility-restoration prefix followed by the target H2 policy."""
from collections import Counter
from copy import deepcopy
import random
from time import perf_counter

from acfqp.domains import standard_2048 as ground
from .controlled_predictive_lifelong_experience_v77 import _status
from .controlled_predictive_regime_experience_v115 import _spawn
from .controlled_predictive_policy_modules_v151 import QUERIES, counter_delta, utility

MODES = ('H2', 'OTHER8', 'MOBILITY')
ACTIONS = tuple(sorted(action.value for action in ground.Swipe2048Action))
PREFIX_BUDGET = 8
EMPTY_GAIN = 2
CHOICE_KEYS = ('action', 'afterstate', 'score', 'value', 'tail_value', 'status',
               'action_values', 'expected_postspawn_empty')


def mobility_choice(board, rule):
    """Maximize vacancies after the next spawn using the frozen learned rule.

    Each supported spawn occupies exactly one empty cell, so its expectation
    equals the deterministic afterstate vacancy count minus one. Ties use the
    first legal action in lexical order.
    """
    counts = Counter(mobility_choose_calls=1)
    action_values = {}
    for action in ACTIONS:
        work = Counter()
        after, score, changed = rule.swipe(board, action, work)
        counts['mobility_action_evaluations'] += 1
        counts.update({f'mobility_{key}': value for key, value in work.items()})
        if changed:
            counts['mobility_legal_actions'] += 1
            counts['mobility_empty_cell_inspections'] += len(after)
            action_values[action] = dict(afterstate=list(after), score=score,
                                         expected_postspawn_empty=after.count(0)-1)
    if not action_values:
        raise ValueError('mobility_choice requires an active board')
    action = max(action_values, key=lambda key: action_values[key]['expected_postspawn_empty'])
    return dict(action=action, **action_values[action], action_values=action_values,
                counts=dict(counts))


def run_branch(root_board, bank, rule, target_query, mode, seed,
               max_steps=2000, p_four=.1):
    """Apply one fixed intervention, then use the target teacher permanently."""
    if mode not in MODES or target_query not in QUERIES:
        raise ValueError('unknown branch mode or target query')
    if not 0 < max_steps <= 2000:
        raise ValueError('max_steps must be between 1 and 2000')
    if not 0. <= p_four <= 1.:
        raise ValueError('p_four must be between zero and one')
    started = perf_counter()
    other = 'risk8' if target_query == 'risk1' else 'risk1'
    board, rng, environment = tuple(root_board), random.Random(seed), Counter()
    status = _status(board, environment)
    if status != 'ACTIVE':
        raise ValueError('the mobility root must be ACTIVE')
    initial_empty = board.count(0)
    module = dict(initial_empty=initial_empty, target_empty=initial_empty+EMPTY_GAIN,
                  prefix_steps=0, exit_reason='baseline' if mode == 'H2' else None,
                  exit_empty=initial_empty if mode == 'H2' else None, completion=False)
    prefix_active = mode != 'H2'
    teacher_before = {q: dict(bank[q].counts) for q in QUERIES}
    actions, cells, ranks, scores, choices = [], [], [], [], []
    prefix_counts, continuation_counts = Counter(), Counter()
    decision_seconds = 0.
    for step in range(max_steps):
        phase = 'prefix' if prefix_active else 'continuation'
        decision_started = perf_counter()
        if phase == 'prefix' and mode == 'MOBILITY':
            policy = 'MOBILITY'
            choice = mobility_choice(board, rule)
            work = choice['counts']
        else:
            policy = other if phase == 'prefix' else target_query
            before = dict(bank[policy].counts)
            choice = bank[policy].choose(board, QUERIES[policy])
            work = dict(forced_decisions=1, **{
                f'policy_{policy}_{key}': value
                for key, value in counter_delta(bank[policy].counts, before).items()})
        decision_seconds += perf_counter()-decision_started
        (prefix_counts if phase == 'prefix' else continuation_counts).update(work)
        compact = {key: deepcopy(choice[key]) for key in CHOICE_KEYS if key in choice}
        compact.update(step=step, phase=phase, policy_key=policy,
                       module_decision=None, work=work)
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
        if phase == 'prefix':
            module['prefix_steps'] += 1
            reason = ('terminal' if status != 'ACTIVE' else
                      'target' if mode == 'MOBILITY' and board.count(0) >= module['target_empty'] else
                      'budget' if module['prefix_steps'] == PREFIX_BUDGET else None)
            if reason is not None:
                module.update(exit_reason=reason, exit_empty=board.count(0),
                              completion=mode == 'MOBILITY' and board.count(0) >= module['target_empty'])
                prefix_active = False
        if status != 'ACTIVE':
            break
    if status == 'ACTIVE':
        status = 'CUTOFF'
    if prefix_active:
        module.update(exit_reason='cutoff', exit_empty=board.count(0))
    components = [sum(scores)/2048., float(status == 'LOST'), float(status == 'WON')]
    result = dict(score=sum(scores), steps=len(actions), status=status, components=components,
        utility=None if status == 'CUTOFF' else utility(components, target_query),
        environment_counts=dict(environment), policy_counts=dict(prefix_counts+continuation_counts),
        prefix_counts=dict(prefix_counts), continuation_counts=dict(continuation_counts),
        policy_counts_by_query={q: counter_delta(bank[q].counts, teacher_before[q]) for q in QUERIES},
        learning_counts={}, decision_seconds=decision_seconds, seconds=perf_counter()-started)
    return dict(root_board=list(root_board), query=target_query, mode=mode, seed=seed,
        max_steps=max_steps, p_four=p_four, actions=actions, spawned_cells=cells,
        spawned_ranks=ranks, scores=scores, choices=choices, final_board=list(board),
        module=module, result=result)
