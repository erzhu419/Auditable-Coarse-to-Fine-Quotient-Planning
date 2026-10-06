"""Separate historical causal quotients with complete-vector replanning."""
from collections import Counter, defaultdict
from copy import deepcopy
import random
from time import perf_counter

from acfqp.domains import standard_2048 as ground
from acfqp.domains.g2048 import D4Transform
from .controlled_predictive_lifelong_experience_v77 import _status
from .controlled_predictive_regime_experience_v115 import _spawn
from .controlled_predictive_policy_modules_v151 import QUERIES, counter_delta, utility
from .controlled_predictive_program_consolidation_v161 import CHOICE_KEYS, INVERSE, canonical_frame

ACTIONS = ('DOWN', 'LEFT', 'RIGHT', 'UP')
ACTIVE_STATES = tuple(f'A:{rank}:{empty}:{merge}' for rank in range(3) for empty in range(3) for merge in range(2))
STATES = ACTIVE_STATES+('WON', 'LOST')
MODES = ('H2', 'SAME_D1', 'SAME_D3', 'XFER_D1', 'XFER_D3')
MIN_ROW_COUNT = 8


def state_key(board, counts=None):
    """Retain high-tile regime, spawn capacity and immediate merge availability."""
    work = counts if counts is not None else Counter()
    work.update(quotient_state_encodings=1, quotient_state_tile_reads=16)
    maximum, empties = 0, 0
    for rank in board:
        maximum = max(maximum, rank)
        empties += rank == 0
    if maximum >= 11:
        return 'WON'
    merge = False
    for axis in (0, 1):
        for index in range(4):
            line = [board[4*index+offset] if axis == 0 else board[4*offset+index] for offset in range(4)]
            compressed = [rank for rank in line if rank]
            work.update(quotient_state_tile_reads=4, quotient_merge_line_checks=1,
                        quotient_merge_comparisons=max(0, len(compressed)-1))
            for a, b in zip(compressed, compressed[1:]):
                merge |= a == b
    if empties == 0 and not merge:
        return 'LOST'
    rank_class = 0 if maximum <= 8 else maximum-8
    return f'A:{rank_class}:{min(empties, 2)}:{int(merge)}'


def fit_model(source_rows, train_rows, life):
    """Use all actual transitions but only genuine same-teacher continuation tails."""
    transitions, tails, counts = defaultdict(Counter), {}, Counter()
    for phase, rows in (('source', source_rows), ('train', train_rows)):
        for row in rows:
            counts[f'{phase}_rows_examined'] += 1
            if row['life'] != life or row['query'] != 'risk1':
                continue
            status = row['result']['status']
            if status not in ('WON', 'LOST'):
                raise ValueError('complete H2 continuations required for teacher-boundary labels')
            counts[f'fitted_{phase}_games'] += 1
            remaining = [0.]*(len(row['scores'])+1)
            for step in range(len(row['scores'])-1, -1, -1):
                remaining[step] = remaining[step+1]+row['scores'][step]/2048.
                counts['tail_score_reads'] += 1
            board = tuple(row['initial_board'] if phase == 'source' else row['root_board'])
            for step, (action, choice, cell, rank, score) in enumerate(zip(
                    row['actions'], row['choices'], row['spawned_cells'], row['spawned_ranks'], row['scores'], strict=True)):
                canonical, frame = canonical_frame(board)
                state = state_key(canonical, counts)
                label = ground.transform_action_v1(ground.Swipe2048Action(action), D4Transform(frame)).value
                next_board = list(choice['afterstate']); next_board[cell] = rank
                successor = state_key(next_board, counts)
                event = successor if successor in ('WON', 'LOST') else 'ACTIVE'
                transitions[state, label][successor, event] += 1
                # Reward is aggregated on the state edge, never used as its identity.
                transitions[state, label][successor, event, 'reward_sum'] += score/2048.
                counts.update(board_transforms=8, action_transports=1, transition_labels=1,
                              transition_component_reads=3, source_state_reconstructions=1)
                counts[f'{phase}_transitions'] += 1
                if phase == 'source' or step >= 1:
                    vector = [remaining[step], float(status == 'LOST'), float(status == 'WON')]
                    tail = tails.setdefault(state, dict(count=0, component_sum=[0., 0., 0.]))
                    tail['count'] += 1
                    for component in range(3): tail['component_sum'][component] += vector[component]
                    counts.update(teacher_tail_labels=1, teacher_tail_component_reads=3)
                board = tuple(next_board)
    rows = []
    for (state, action), table in sorted(transitions.items()):
        outcomes = []
        for key, count in sorted(((key, count) for key, count in table.items() if len(key) == 2)):
            successor, status = key
            reward = table[successor, status, 'reward_sum']
            outcomes.append(dict(next_state=successor, status=status, count=count, reward_sum=reward,
                                 reward_mean=reward/count, failure=float(status == 'LOST'), success=float(status == 'WON')))
        rows.append(dict(state=state, action=action, count=sum(outcome['count'] for outcome in outcomes), outcomes=outcomes))
    tail_rows = [dict(state=state, **tail, component_mean=[value/tail['count'] for value in tail['component_sum']])
                 for state, tail in sorted(tails.items())]
    return dict(schema='acfqp.causal_quotient.v171.model', life=life, rows=rows, tails=tail_rows, counts=dict(counts))


class CompiledModel:
    """Read-only lookup of frozen depth tables, with no repeated Bellman work."""
    def __init__(self, payload, tables, counts=None):
        self.payload, self.tables = deepcopy(payload), deepcopy(tables)
        self.life, self.counts = payload['life'], dict(counts or {})
        self._rows = {(row['state'], row['action']): row for row in self.payload['rows']}
        self._q = {(int(depth), row['state'], row['action']): row['components'] if row['complete'] else None
                   for depth, table in self.tables['depths'].items() for row in table['actions']}

    def q(self, state, canonical_action, depth):
        return deepcopy(self._q.get((depth, state, canonical_action)))

    def row_count(self, state, action):
        return self._rows.get((state, action), {}).get('count', 0)


def compile_model(payload):
    rows = {(row['state'], row['action']): row for row in payload['rows']}
    tails = {row['state']: row['component_mean'] for row in payload['tails']}
    counts = Counter(action_rows_evaluated=0, supported_action_rows=0,
                     successor_vector_reads=0, component_accumulations=0, value_states_resolved=0)
    tables, previous = dict(min_row_count=MIN_ROW_COUNT, depths={}), {}
    for depth in range(4):
        actions, values = [], []
        for state in STATES:
            terminal = state in ('WON', 'LOST')
            candidates = []
            if depth and not terminal:
                for action in ACTIONS:
                    counts['action_rows_evaluated'] += 1
                    row, issues = rows.get((state, action)), []
                    if row is None or row['count'] < MIN_ROW_COUNT:
                        issues.append('insufficient_row_support')
                    vector = [0., 0., 0.]
                    if not issues:
                        counts['supported_action_rows'] += 1
                        for outcome in row['outcomes']:
                            successor = outcome['next_state']
                            continuation = [0., 0., 0.] if successor in ('WON', 'LOST') else previous.get(successor)
                            if successor not in ('WON', 'LOST') and successor not in tails:
                                continuation = None
                            if continuation is None:
                                if 'missing_teacher_tail' not in issues: issues.append('missing_teacher_tail')
                                continue
                            counts['successor_vector_reads'] += 1
                            immediate = [outcome['reward_mean'], outcome['failure'], outcome['success']]
                            weight = outcome['count']/row['count']
                            for component in range(3):
                                vector[component] += weight*(immediate[component]+continuation[component])
                                counts['component_accumulations'] += 1
                    complete = not issues
                    actions.append(dict(state=state, action=action, count=0 if row is None else row['count'],
                                        complete=complete, components=vector if complete else None, issues=issues))
                    if complete: candidates.append((utility(vector, 'risk1'), action, vector))
            counts['value_states_resolved'] += 1
            if terminal:
                vector, selected, boundary = [0., 0., 0.], None, 'terminal'
            elif depth and candidates:
                _, selected, vector = min(candidates, key=lambda item: (-item[0], item[1]))
                boundary = 'model'
            else:
                vector, selected = deepcopy(tails.get(state)), None
                boundary = 'missing_tail' if vector is None else 'teacher_tail'
            values.append(dict(state=state, components=vector, chosen_action=selected, boundary=boundary))
        tables['depths'][str(depth)] = dict(values=values, actions=actions)
        previous = {row['state']: row['components'] for row in values}
    return CompiledModel(payload, tables, counts)


def load_compiled(payload, tables):
    return CompiledModel(payload, tables)


def run_episode(bank, models, life, mode, seed, max_steps=8192, p_four=.1):
    """Replan on the current canonical quotient while preserving source tails."""
    if mode not in MODES or not 0 < max_steps <= 8192 or not 0 <= p_four <= 1:
        raise ValueError('invalid causal quotient episode settings')
    started, rng, environment, policy = perf_counter(), random.Random(seed), Counter(), Counter()
    board, initial_spawns = (0,)*16, []
    for _ in range(2):
        board, cell, rank = _spawn(board, rng, environment, p_four)
        initial_spawns.append(dict(cell=cell, rank=rank)); environment['initial_spawns'] += 1
    initial_board, status = board, _status(board, environment)
    depth = 0 if mode == 'H2' else int(mode[-1])
    module = dict(mode=mode, life=life, depth=depth, decisions=0, model_decisions=0,
                  h2_calls=0, unsupported_fallbacks=0, source_counts=[0]*4, ground_legality_checks=0)
    bank_before = {query: dict(bank[query].counts) for query in QUERIES}
    actions, cells, ranks, scores, choices, decision_seconds = [], [], [], [], [], 0.
    for step in range(max_steps):
        begun, work, decision, choice = perf_counter(), Counter(), None, None
        phase, policy_key = 'teacher', 'risk1'
        if mode != 'H2':
            canonical, frame = canonical_frame(board)
            state = state_key(canonical, work)
            inverse = INVERSE[D4Transform(frame)]
            legal = {}
            for action in ACTIONS:
                actual = ground.transform_action_v1(ground.Swipe2048Action(action), inverse).value
                after, score, changed = ground.swipe_board_v1(board, ground.Swipe2048Action(actual))
                if changed: legal[action] = (actual, after, score)
            work.update(quotient_decisions=1, quotient_board_transforms=8,
                        quotient_action_transports=4, quotient_ground_legality_swipe_calls=4)
            module['decisions'] += 1; module['ground_legality_checks'] += 4
            eligible = [life] if mode.startswith('SAME') else [source for source in range(4) if source != life]
            candidates = []
            for source in eligible:
                for action in ACTIONS:
                    if action not in legal: continue
                    work['quotient_model_lookups'] += 1
                    vector = models[source].q(state, action, depth)
                    if vector is None: continue
                    work['quotient_component_reads'] += 3
                    candidates.append(dict(source_life=source, canonical_action=action,
                        actual_action=legal[action][0], components=vector, utility=utility(vector, 'risk1'),
                        row_count=models[source].row_count(state, action)))
            selected = min(candidates, key=lambda row: (-row['utility'], row['source_life'], row['canonical_action'])) if candidates else None
            decision = dict(state=state, canonical_board=list(canonical), transform=frame,
                            eligible_models=eligible, depth=depth, candidates=deepcopy(candidates),
                            selected_source_life=None if selected is None else selected['source_life'],
                            selected_canonical_action=None if selected is None else selected['canonical_action'],
                            selected_actual_action=None if selected is None else selected['actual_action'], fallback=selected is None)
            if selected is None:
                module['unsupported_fallbacks'] += 1
            else:
                actual, after, score = legal[selected['canonical_action']]
                choice = dict(action=actual, afterstate=list(after), score=score, value=selected['utility'])
                phase, policy_key = 'quotient', 'MODEL'
                module['model_decisions'] += 1; module['source_counts'][selected['source_life']] += 1
        if choice is None:
            before = dict(bank['risk1'].counts)
            choice = bank['risk1'].choose(board, QUERIES['risk1'])
            work['forced_decisions'] += 1
            work.update({f'policy_risk1_{key}': value for key, value in counter_delta(bank['risk1'].counts, before).items()})
            module['h2_calls'] += 1
        decision_seconds += perf_counter()-begun
        policy.update(work)
        compact = {key: deepcopy(choice[key]) for key in CHOICE_KEYS if key in choice}
        compact.update(step=step, phase=phase, policy_key=policy_key, model_decision=decision, work=dict(work))
        actual = ground.Swipe2048Action(choice['action'])
        environment.update(ground_explicit_swipe_calls=1, ground_swipe_calls=1)
        after, score, changed = ground.swipe_board_v1(board, actual)
        if not changed: raise ValueError('quotient executor selected an illegal physical action')
        board, cell, rank = _spawn(after, rng, environment, p_four)
        environment['sampled_transitions'] += 1
        status = _status(board, environment)
        actions.append(actual.value); cells.append(cell); ranks.append(rank); scores.append(score); choices.append(compact)
        if status != 'ACTIVE': break
    if status == 'ACTIVE': status = 'CUTOFF'
    components = [sum(scores)/2048., float(status == 'LOST'), float(status == 'WON')]
    result = dict(score=sum(scores), steps=len(actions), status=status, components=components,
        utility=None if status == 'CUTOFF' else utility(components, 'risk1'), environment_counts=dict(environment),
        policy_counts=dict(policy), policy_counts_by_query={query: counter_delta(bank[query].counts, bank_before[query]) for query in QUERIES},
        program_setup_counts={}, learning_counts={}, decision_seconds=decision_seconds, seconds=perf_counter()-started)
    return dict(seed=seed, query='risk1', mode=mode, max_steps=max_steps, p_four=p_four,
        initial_board=list(initial_board), initial_spawns=initial_spawns, actions=actions,
        spawned_cells=cells, spawned_ranks=ranks, scores=scores, choices=choices, final_board=list(board),
        module=module, result=result)
