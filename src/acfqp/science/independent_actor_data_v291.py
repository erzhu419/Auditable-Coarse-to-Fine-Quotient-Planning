"""One physical acquisition of fresh frozen-actor data in a stable task.

All raw ranks, including initialization, enter the observed-prefix library.
Only naturally complete games supply fitting or heldout labels; the paid
unfinished tail remains in the acquisition ledger and canonical receipts.
"""
from collections import Counter
import resource
from time import perf_counter, process_time

from .controlled_predictive_regime_experience_v115 import run_episode
from .controlled_predictive_regime_memory_v115 import SpawnMemory, WARMUP, BLOCK
from .natural_model_revision_v281 import MAX_STEPS, QUERY, delta, utility
from .natural_online_value_v286 import compact_training, memory_state
from .native_value_stream_v286 import NativeValueStream
from .retained_actor_data_v287 import _Replay

RAW_BUDGET = 131072


def warmup_seed(life, game):
    return 291100000000+life*1000000+game


def training_seed(life):
    return 291200000000+life*10000000


def _reconstruct(replay, method, row):
    started = process_time()
    method(row)
    replay.cpu_seconds += process_time()-started


def _warmup(template, life, parent, emit, replay, phase, p_four, seed_base):
    memory, games, environment, events = SpawnMemory('LIBRARY'), [], Counter(), []
    started, cpu_started = perf_counter(), process_time()
    before = dict(template.counts)
    while memory.observations_seen < WARMUP:
        seed = seed_base+life*1000000+len(games)
        game_before = dict(template.counts)
        game = run_episode(seed, lambda board, step: template.choose(board, QUERY)['action'], p_four, MAX_STEPS)
        spawns = [dict(spawn, kind='INITIAL') for spawn in game['initial_spawns']]
        spawns.extend(dict(rank=step['spawned_rank'], cell=step['spawned_cell'], kind='POST_ACTION')
                      for step in game['steps'])
        for spawn in spawns:
            event = memory.observe(spawn['rank'])
            if event is not None:
                events.append(event)
        summary = dict(seed=seed, score=game['return_score'], status=game['status'],
                       steps=game['steps_count'], utility=utility(game))
        games.append(summary)
        environment.update(game['work'])
        row = dict(kind='WARMUP', lifecycle=life, parent=parent, phase=phase,
            true_p_four=p_four, summary=summary,
            raw_spawns=spawns, actions=[step['action'] for step in game['steps']],
            scores=[step['score'] for step in game['steps']], final_board=game['final_board'],
            counts=dict(environment=game['work'], direct=delta(template.counts, game_before)))
        emit(row)
        if game['status'] == 'CUTOFF':
            raise ValueError('V291 acquisition requires natural terminal games; warmup cutoff retained')
        _reconstruct(replay, replay.warmup, row)
    return memory, dict(game_summaries=games, raw_tiles=memory.observations_seen,
        environment_counts=dict(environment), direct_counts=delta(template.counts, before),
        memory_counts=dict(memory.counts), memory_events=events, final_memory=memory_state(memory),
        cpu_seconds=process_time()-cpu_started, wall_seconds=perf_counter()-started)


def acquire_dataset(template, life, parent, emit, runtime, raw_budget=RAW_BUDGET, *,
                    phase='A', p_four=.1, warmup_seed_base=291100000000,
                    training_seed_base=291200000000):
    """Return dataset plus acquisition; emit each actual receipt exactly once.

    The caller's source weights and update history stay frozen. Operational
    prediction counts accrue on that source and are charged in this receipt.
    ACQUISITION_SNAPSHOT marks a raw-budget boundary, without evaluation games.
    """
    if life not in range(64) or parent != life % 4:
        raise ValueError('V291 life must belong to its frozen source parent')
    if template.weights.flags.writeable:
        raise ValueError('V291 acquisition actor weights must already be frozen')
    started, cpu_started = perf_counter(), process_time()
    children_before = resource.getrusage(resource.RUSAGE_CHILDREN)
    expected = dict(lifecycle=life, parent=parent, warmup={},
        arms=dict(FROZEN=dict(phases={phase:dict(training={}, snapshot={})})))
    replay = _Replay(expected, phase)
    memory, warmup = _warmup(template, life, parent, emit, replay,
        phase, p_four, warmup_seed_base)
    expected['warmup'] = warmup
    phase_receipt = expected['arms']['FROZEN']['phases'][phase]
    before_updates = template.updates
    train_started, train_cpu = perf_counter(), process_time()
    engine = NativeValueStream(template, training_seed_base+life*10000000, runtime, max_steps=MAX_STEPS)
    try:
        before_state, before_memory = engine.state(), dict(memory.counts)
        phase_receipt['training']['before_stream'] = before_state
        chunks = memory_events = 0
        while engine.state()['raw_tiles'] < raw_budget:
            state = engine.state()
            remaining = min(raw_budget-state['raw_tiles'], BLOCK-memory.pending_n)
            p_used, module_before = memory.predict(), memory.module_id
            pending = template if state['pending_bank_id'] is not None else None
            receipt = engine.advance(template, 0, pending, p_used, p_four,
                                     tile_budget=remaining, max_postaction=BLOCK)
            events = []
            for spawn in receipt['raw_spawns']:
                event = memory.observe(spawn['rank'])
                if event is not None:
                    events.append(event)
            memory_events += len(events)
            row = dict(kind='TRAIN', lifecycle=life, parent=parent, arm='FROZEN', phase=phase,
                true_p_four=p_four,
                active_bank_id=0, module_id_before=module_before, model_p_four=p_used,
                memory_events=events, seconds=receipt['seconds'], cpu_seconds=receipt['cpu_seconds'],
                **compact_training(receipt))
            emit(row)
            if any(game['status'] == 'CUTOFF' for game in receipt['completed_games']):
                raise ValueError('V291 acquisition requires natural terminal games; training cutoff retained')
            _reconstruct(replay, replay.train, row)
            chunks += 1
        if template.updates != before_updates:
            raise ValueError('Frozen acquisition actor received a value update')
        p_used = memory.predict()
        snapshot = dict(active_bank_id=0, estimated_p_four=p_used, memory=memory_state(memory),
                        stream=engine.state(), new_value_updates=0)
        training = dict(raw_tiles=raw_budget, chunks=chunks, before_stream=before_state,
            after_stream=engine.state(), memory_counts=delta(memory.counts, before_memory),
            memory_event_count=memory_events,
            counts={kind: dict(counts) for kind, counts in engine.counts.items()},
            cpu_seconds=process_time()-train_cpu, wall_seconds=perf_counter()-train_started)
        phase_receipt.update(training=training, snapshot=snapshot)
        boundary = dict(kind='ACQUISITION_SNAPSHOT', lifecycle=life, parent=parent,
                        arm='FROZEN', phase=phase, true_p_four=p_four,
                        snapshot=snapshot, training=training)
        emit(boundary)
        _reconstruct(replay, replay.checkpoint, boundary)
        finish_started = process_time()
        dataset = replay.finish()
        replay.cpu_seconds += process_time()-finish_started
        dataset['costs']['processing_cpu_seconds'] = replay.cpu_seconds
        children_after = resource.getrusage(resource.RUSAGE_CHILDREN)
        acquisition = dict(warmup=warmup, training=training, snapshot=snapshot,
            native_setup_counts=dict(engine.setup_counts), native_setup_seconds=engine.setup_seconds,
            reconstruction=dict(counts=dict(replay.processing), memory_counts=dict(replay.memory.counts),
                chunks=replay.chunks, cpu_seconds=replay.cpu_seconds),
            cpu_seconds=process_time()-cpu_started, wall_seconds=perf_counter()-started,
            compiler_cpu_seconds=children_after.ru_utime+children_after.ru_stime
                -children_before.ru_utime-children_before.ru_stime,
            new_value_updates=0, physical_acquisitions=1, new_evaluation_games=0)
        return dict(dataset=dataset, acquisition=acquisition)
    finally:
        engine.close()
