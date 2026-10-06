"""Causal whole-game value consolidation over uninterrupted natural episodes."""
from collections import Counter
import resource
from time import perf_counter, process_time

import numpy as np

from acfqp.domains import standard_2048 as ground
from .controlled_predictive_online_query_td_v131 import QueryTD
from .controlled_predictive_regime_memory_v115 import SpawnMemory, BLOCK
from .natural_model_revision_v281 import MAX_STEPS, delta
from .natural_online_value_v286 import compact_training, memory_state
from .native_episode_consolidation_v290 import fit_consolidated
from .native_value_stream_v286 import NativeValueStream

PHASES = (('A', .1), ('B', .5), ('A_prime', .1))
ARMS = ('FROZEN_H2', 'NSEQ_H2', 'MEAN_H2', 'FROZEN_DIRECT', 'MEAN_DIRECT')
RAW_TILES_PER_PHASE = 131072
EVALUATION_GAMES = 32


def training_seed(life):
    return 292200000000+life*10000000


def evaluation_seed(life, phase, episode):
    return 292900000000+life*1000000+phase*100000+episode


def _accumulate(total, current):
    for key, value in current.items():
        total[key] = max(total.get(key, 0), value) if key.endswith('_peak') else total.get(key, 0)+value


class _GameBuffer:
    """Reconstruct one actual game across raw-budget and phase boundaries."""
    def __init__(self, state, goal_rank, retain_afterstates):
        self.state = dict(state)
        self.goal_rank, self.retain = goal_rank, retain_afterstates
        self.afterstates, self.rewards = [], []
        self.counts = Counter()
        self.cpu_seconds = 0.
        self.completed = self.cutoffs = self.peak_steps = 0

    def _status(self, board):
        self.counts['ground_state_status_calls'] += 1
        if max(board) >= self.goal_rank:
            return 'WON'
        for action in ground.ACTION_ORDER:
            self.counts.update(ground_swipe_calls=1, ground_status_internal_swipe_calls=1)
            if ground.swipe_board_v1(board, action)[2]:
                return 'ACTIVE'
        return 'LOST'

    def ingest(self, receipt):
        started = process_time()
        if self.state != receipt['start'] or len(receipt['completed_games']) > 1:
            raise ValueError('Online stream must continue its prefix and pause at the first game end')
        state, board, action_index = self.state, tuple(self.state['board']), 0
        completed = receipt['completed_games']
        terminal = None
        for spawn in receipt['raw_spawns']:
            if spawn['kind'] == 'INITIAL':
                if state['status'] != 'INITIALIZING':
                    if state['status'] not in ('NOT_STARTED', 'WON', 'LOST', 'CUTOFF'):
                        raise ValueError('New game initialization overwrote an unfinished game')
                    state.update(episode=state['episode']+1, step=0, return_score=0,
                        status='INITIALIZING', initial_count=0, game_start_raw=state['raw_tiles'],
                        pending_afterstate=None, pending_bank_id=None)
                    board, self.afterstates, self.rewards = (0,)*16, [], []
                state['initial_count'] += 1
                if state['initial_count'] > 2:
                    raise ValueError('Actual episode requires two initial tiles')
            elif spawn['kind'] == 'POST_ACTION':
                if state['status'] != 'ACTIVE' or action_index >= len(receipt['actions']):
                    raise ValueError('Actual action lacks its active board or recorded choice')
                action = ground.Swipe2048Action(receipt['actions'][action_index])
                after, score, changed = ground.swipe_board_v1(board, action)
                self.counts.update(ground_explicit_swipe_calls=1, ground_swipe_calls=1)
                if not changed or score != receipt['scores'][action_index]:
                    raise ValueError('Actual action score or legality differs from its receipt')
                if self.retain:
                    self.afterstates.append(after)
                    self.rewards.append(score/2048.)
                    self.peak_steps = max(self.peak_steps, len(self.afterstates))
                board = after
                action_index += 1
                state['step'] += 1
                state['return_score'] += score
                state['post_action_spawns'] += 1
                winning = max(after) >= self.goal_rank
                state['pending_afterstate'] = None if winning else list(after)
                state['pending_bank_id'] = None if winning else 0
            else:
                raise ValueError('Unknown actual spawn kind')
            if board[spawn['cell']] or spawn['rank'] not in (1, 2):
                raise ValueError('Actual spawn must occupy an empty cell with rank one or two')
            board = list(board)
            board[spawn['cell']] = spawn['rank']
            board = tuple(board)
            if spawn['kind'] == 'INITIAL' and state['initial_count'] == 2:
                state['status'] = self._status(board)
            if spawn['episode'] != state['episode']:
                raise ValueError('Actual spawn belongs to a different episode')
            state['raw_tiles'] += 1
            state['random_draw_position'] += 2
            candidate = completed[0] if completed else None
            if candidate is not None and candidate['episode'] == state['episode'] and candidate['steps'] == state['step']:
                status = self._status(board)
                if candidate['status'] == 'CUTOFF':
                    if status != 'ACTIVE' or state['step'] != MAX_STEPS:
                        raise ValueError('Cutoff must censor an active game at its actual step limit')
                    status = 'CUTOFF'
                elif status != candidate['status'] or status not in ('WON', 'LOST'):
                    raise ValueError('Completed game is not its recorded actual terminal')
                state['status'] = status
                state['pending_afterstate'] = state['pending_bank_id'] = None
                actual = dict(episode=state['episode'], stream_seed=state['stream_seed'],
                    start_raw=state['game_start_raw'], end_raw=state['raw_tiles'],
                    steps=state['step'], score=state['return_score'], status=status)
                if actual != candidate or terminal is not None:
                    raise ValueError('Full game score, steps or raw range differs from its receipt')
                data = None
                if self.retain and status in ('WON', 'LOST'):
                    n = len(self.afterstates)
                    data = dict(afterstates=np.asarray(self.afterstates, dtype=np.int32).reshape(-1, 16),
                        rewards=np.asarray(self.rewards, dtype=np.float64), ends=np.asarray([n], dtype=np.int64),
                        terminal_codes=np.asarray([1 if status == 'WON' else -1], dtype=np.int32),
                        fit_game_count=1, fit_step_end=n)
                terminal = (actual, data)
                self.completed += 1
                self.cutoffs += int(status == 'CUTOFF')
                self.afterstates, self.rewards = [], []
                if spawn is not receipt['raw_spawns'][-1]:
                    raise ValueError('Native execution continued beyond terminal before consolidation')
        state['board'] = list(board)
        if state['status'] == 'ACTIVE' and self._status(board) != 'ACTIVE':
            raise ValueError('Actual terminal game was omitted from its receipt')
        if (action_index != len(receipt['actions']) or action_index != len(receipt['scores'])
                or bool(terminal) != bool(completed) or state != receipt['end']):
            raise ValueError('Actual chunk board, score or game boundary differs')
        self.cpu_seconds += process_time()-started
        return terminal

    def unfinished(self):
        state = self.state
        active = state['status'] in ('ACTIVE', 'INITIALIZING')
        return dict(episode=state['episode'] if active else None,
            raw_tiles=state['raw_tiles']-state['game_start_raw'] if active else 0,
            steps=state['step'] if active else 0, score=state['return_score'] if active else 0,
            status=state['status'], retained_afterstates=len(self.afterstates))


def _fit_sample(sample, game):
    if sample is None:
        return None
    return dict(sample, global_episode=game['episode'],
                global_raw_before_action=game['start_raw']+2+sample['step'])


def _evaluate(engine, leaf, p, env_p, seeds, depth):
    state, updates = engine.state(), leaf.updates
    evaluated = engine.evaluate_games(leaf, p, env_p, seeds, depth=depth, max_steps=MAX_STEPS)
    if engine.state() != state or leaf.updates != updates or leaf.weights.flags.writeable:
        raise ValueError('Static evaluation modified the raw stream or value head')
    return dict(evaluated, model_p_four=p, environment_p_four=env_p, depth=depth)


def run_arm(template, warmed, life, arm, emit, runtime):
    """Keep actor, memory and incomplete game alive through all three phases."""
    if arm not in ARMS or template.weights.flags.writeable:
        raise ValueError('V292 requires its frozen source and one of the five fixed arms')
    method = ('NORMALIZED_SEQUENTIAL_MC' if arm == 'NSEQ_H2' else
              'EPISODE_MEAN_MC' if arm.startswith('MEAN') else None)
    depth = 1 if arm.endswith('DIRECT') else 2
    started, cpu_started = perf_counter(), process_time()
    child_before = resource.getrusage(resource.RUSAGE_CHILDREN)
    if method is None:
        leaf = template
        head_setup = dict(source_weights_shared=True, setup_counts={}, setup_seconds=0., private_weight_bytes=0)
    else:
        leaf = QueryTD(template.parent, 'PRIOR', runtime)
        head_setup = dict(source_weights_shared=False, setup_counts=dict(leaf.setup_counts),
                         setup_seconds=leaf.setup_seconds, private_weight_bytes=leaf.weights.nbytes)
        leaf.freeze()
    memory = SpawnMemory.from_payload(warmed.to_payload())
    engine = NativeValueStream(template, training_seed(life), runtime, max_steps=MAX_STEPS)
    buffer = _GameBuffer(engine.state(), leaf.radix, method is not None)
    totals = dict(fitted_games=0, fitted_steps=0, trained_afterstates=0,
        learning_counts={}, target_counts={}, consolidation_counts={}, setup_counts={},
        seconds=0., cpu_seconds=0.)
    phases = {}
    evaluations = {kind: Counter() for kind in ('environment', 'planning')}
    retention_counts = {kind: Counter() for kind in evaluations}
    a_head_counts = {kind: Counter() for kind in evaluations}
    retained_A, retained_A_setup, saved_A_p = None, None, None
    try:
        for phase_index, (phase, env_p) in enumerate(PHASES):
            before_engine = {kind: dict(counts) for kind, counts in engine.counts.items()}
            before_fit = dict(totals['learning_counts'])
            before_memory, before_state = dict(memory.counts), engine.state()
            before_games, before_cutoffs, before_fitted = buffer.completed, buffer.cutoffs, totals['fitted_games']
            chunks = memory_event_count = 0
            quota = (phase_index+1)*RAW_TILES_PER_PHASE
            while engine.state()['raw_tiles'] < quota:
                state = engine.state()
                remaining = min(quota-state['raw_tiles'], BLOCK-memory.pending_n)
                p, module, updates_before = memory.predict(), memory.module_id, leaf.updates
                receipt = engine.advance(leaf, 0, leaf if state['pending_bank_id'] is not None else None,
                    p, env_p, tile_budget=remaining, max_postaction=BLOCK,
                    depth=depth, stop_on_game_end=True)
                events = []
                for spawn in receipt['raw_spawns']:
                    event = memory.observe(spawn['rank'])
                    if event is not None:
                        events.append(event)
                memory_event_count += len(events)
                row = dict(kind='TRAIN', lifecycle=life, arm=arm, phase=phase, depth=depth,
                    active_bank_id=0, module_id_before=module, model_p_four=p, memory_events=events,
                    leaf_updates_before=updates_before, leaf_updates_after=leaf.updates,
                    actor_weights_readonly=not leaf.weights.flags.writeable,
                    seconds=receipt['seconds'], cpu_seconds=receipt['cpu_seconds'], **compact_training(receipt))
                emit(row)
                if receipt['updates'] or leaf.updates != updates_before or leaf.weights.flags.writeable:
                    raise ValueError('Whole-game actor received a transition TD update')
                terminal = buffer.ingest(receipt)
                chunks += 1
                if terminal is not None:
                    game, dataset = terminal
                    old_updates = leaf.updates
                    if dataset is not None:
                        leaf.weights.flags.writeable = True
                        try:
                            fit = fit_consolidated(leaf, dataset, method, runtime, alpha=.0025)
                        finally:
                            leaf.freeze()
                        for key in ('fitted_games', 'fitted_steps', 'trained_afterstates', 'seconds', 'cpu_seconds'):
                            totals[key] += fit[key]
                        for key in ('learning_counts', 'target_counts', 'consolidation_counts', 'setup_counts'):
                            _accumulate(totals[key], fit[key])
                        fit = dict(fit, first_sample=_fit_sample(fit['first_sample'], game),
                                   last_sample=_fit_sample(fit['last_sample'], game))
                    else:
                        fit = dict(method='SKIPPED_CUTOFF' if game['status'] == 'CUTOFF' else 'NONE',
                            trained_afterstates=0, learning_counts={}, target_counts={}, consolidation_counts={},
                            first_sample=None, last_sample=None, seconds=0., cpu_seconds=0.)
                    emit(dict(kind='GAME_FIT', lifecycle=life, arm=arm, phase=phase, completion=game,
                        fitted=dataset is not None, old_value_updates=old_updates,
                        new_value_updates=leaf.updates, fit=fit))
            p = memory.predict()
            snapshot = dict(estimated_p_four=p, memory=memory_state(memory), stream=engine.state(),
                            value_updates=leaf.updates, unfinished_game=buffer.unfinished())
            seeds = [evaluation_seed(life, phase_index, e) for e in range(EVALUATION_GAMES)]
            evaluated = _evaluate(engine, leaf, p, env_p, seeds, depth)
            for kind, counts in evaluated['counts'].items():
                evaluations[kind].update(counts)
            a_seeds = [evaluation_seed(life, 0, e) for e in range(EVALUATION_GAMES)]
            if phase_index == 0:
                saved_A_p = p
                retention = dict(evaluated, shared_with_current=True,
                    counts={kind: {} for kind in evaluations}, seconds=0., cpu_seconds=0.)
                if arm == 'MEAN_H2':
                    copy_started, copy_cpu = perf_counter(), process_time()
                    retained_A = QueryTD(template.parent, 'PRIOR', runtime)
                    np.copyto(retained_A.weights, leaf.weights)
                    retained_A.freeze()
                    retained_A_setup = dict(setup_counts=dict(retained_A.setup_counts,
                        retained_A_parameters_copied=retained_A.weights.size,
                        retained_A_weight_bytes_copied=retained_A.weights.nbytes),
                        setup_seconds=retained_A.setup_seconds, seconds=perf_counter()-copy_started,
                        cpu_seconds=process_time()-copy_cpu, private_weight_bytes=retained_A.weights.nbytes,
                        copied_from_value_updates=leaf.updates)
            else:
                retention = dict(_evaluate(engine, leaf, saved_A_p, .1, a_seeds, depth), shared_with_current=False)
                for kind, counts in retention['counts'].items():
                    retention_counts[kind].update(counts)
            training = dict(raw_tiles=RAW_TILES_PER_PHASE, chunks=chunks,
                before_stream=before_state, after_stream=engine.state(),
                memory_counts=delta(memory.counts, before_memory), memory_event_count=memory_event_count,
                completed_games=buffer.completed-before_games, cutoff_games=buffer.cutoffs-before_cutoffs,
                fitted_games=totals['fitted_games']-before_fitted,
                counts={kind: delta(counts, before_engine[kind]) for kind, counts in engine.counts.items()})
            training['counts']['learning'] = dict(Counter(training['counts']['learning'])
                +Counter(delta(totals['learning_counts'], before_fit)))
            result = dict(game_summaries=evaluated['game_summaries'], snapshot=snapshot, training=training,
                evaluation_counts=evaluated['counts'], evaluation_seconds=evaluated['seconds'],
                evaluation_cpu_seconds=evaluated['cpu_seconds'], retention_probe=retention)
            if phase_index == 1 and retained_A is not None:
                result['a_head_on_B'] = _evaluate(engine, retained_A, p, env_p, seeds, depth)
                for kind, counts in result['a_head_on_B']['counts'].items():
                    a_head_counts[kind].update(counts)
                retained_A = None
            phases[phase] = result
            emit(dict(kind='CHECKPOINT', lifecycle=life, arm=arm, phase=phase, **result))
        child_after = resource.getrusage(resource.RUSAGE_CHILDREN)
        training_counts = {kind: dict(counts) for kind, counts in engine.counts.items()}
        training_counts['learning'] = dict(Counter(training_counts['learning'])+Counter(totals['learning_counts']))
        return dict(phases=phases, training_counts=training_counts, final_memory=memory.to_payload(),
            final_stream=engine.state(), final_unfitted_game=buffer.unfinished(), fit_totals=totals,
            head_setup=head_setup, retained_A_head_setup=retained_A_setup,
            native_setup_counts=dict(engine.setup_counts), native_setup_seconds=engine.setup_seconds,
            evaluation_counts={kind: dict(counts) for kind, counts in evaluations.items()},
            retention_evaluation_counts={kind: dict(counts) for kind, counts in retention_counts.items()},
            a_head_on_B_evaluation_counts={kind: dict(counts) for kind, counts in a_head_counts.items()},
            completed_games=buffer.completed, cutoff_games=buffer.cutoffs,
            costs=dict(cpu_seconds=process_time()-cpu_started, wall_seconds=perf_counter()-started,
                compiler_cpu_seconds=child_after.ru_utime+child_after.ru_stime-child_before.ru_utime-child_before.ru_stime,
                reconstruction_counts=dict(buffer.counts), reconstruction_cpu_seconds=buffer.cpu_seconds,
                retained_afterstate_steps_peak=buffer.peak_steps))
    finally:
        engine.close()
