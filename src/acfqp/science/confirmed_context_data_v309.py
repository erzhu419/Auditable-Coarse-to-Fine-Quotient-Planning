"""Pay complete SOURCE games until observed novelty resolves or reaches its cap."""
from collections import Counter
import resource
from time import perf_counter, process_time

from .controlled_predictive_regime_experience_v115 import run_episode
from .controlled_predictive_regime_memory_v115 import BLOCK, WARMUP, SpawnMemory
from .confirmed_context_v309 import MAX_DETECTION_RAW
from .independent_actor_data_v291 import RAW_BUDGET, _reconstruct
from .natural_model_revision_v281 import MAX_STEPS, QUERY, delta, utility
from .natural_online_value_v286 import compact_training, memory_state
from .native_value_stream_v286 import NativeValueStream
from .retained_actor_data_v287 import _Replay


def _detect(template, life, parent, emit, replay, stage, p_four, seed_base, router):
    """Initial warmup and every extra game share one factual detector memory."""
    started, cpu_started = perf_counter(), process_time()
    memory, games, environment, events = SpawnMemory('LIBRARY'), [], Counter(), []
    before = dict(template.counts)
    initial_raw = initial_games = looks = 0
    while True:
        kind = 'WARMUP' if not looks else 'CONFIRMATION'
        seed = seed_base+life*1000000+len(games)
        game_before = dict(template.counts)
        game = run_episode(seed, lambda board, step: template.choose(board, QUERY)['action'], p_four, MAX_STEPS)
        spawns = [dict(spawn, kind='INITIAL') for spawn in game['initial_spawns']]
        spawns.extend(dict(rank=step['spawned_rank'], cell=step['spawned_cell'], kind='POST_ACTION')
                      for step in game['steps'])
        game_events = []
        for spawn in spawns:
            event = memory.observe(spawn['rank'])
            if event is not None:
                game_events.append(event)
        events.extend(game_events)
        summary = dict(seed=seed, score=game['return_score'], status=game['status'],
            steps=game['steps_count'], utility=utility(game))
        games.append(summary)
        environment.update(game['work'])
        row = dict(kind=kind, lifecycle=life, parent=parent, phase=stage, true_p_four=p_four,
            summary=summary, raw_spawns=spawns, actions=[step['action'] for step in game['steps']],
            scores=[step['score'] for step in game['steps']], final_board=game['final_board'],
            memory_events=game_events,
            counts=dict(environment=game['work'], direct=delta(template.counts, game_before)))
        emit(row)
        if game['status'] == 'CUTOFF':
            raise ValueError('V309 requires natural terminal games; detector cutoff retained')
        _reconstruct(replay, replay.warmup, row)
        if memory.observations_seen < WARMUP:
            continue
        if not looks:
            initial_raw, initial_games = memory.observations_seen, len(games)
        decision = router.probe(memory.to_payload())
        at_cap = memory.observations_seen >= MAX_DETECTION_RAW
        emit(dict(kind='DETECTOR_LOOK', lifecycle=life, parent=parent, phase=stage,
            look_index=looks, detector_raw_tiles=memory.observations_seen, at_cap=at_cap, **decision))
        looks += 1
        if decision['decision'] != 'PENDING_CONFIRMATION':
            break
        if at_cap:
            decision = dict(decision, decision='CAP_REUSE_UNRESOLVED', created=False)
            break
    warmup = dict(game_summaries=games, raw_tiles=memory.observations_seen,
        environment_counts=dict(environment), direct_counts=delta(template.counts, before),
        memory_counts=dict(memory.counts), memory_events=events, final_memory=memory_state(memory),
        initial_raw_tiles=initial_raw, confirmation_raw_tiles=memory.observations_seen-initial_raw,
        initial_game_count=initial_games, confirmation_games=len(games)-initial_games, detector_looks=looks,
        cpu_seconds=process_time()-cpu_started, wall_seconds=perf_counter()-started)
    return memory, warmup, decision


def acquire_stage(template, life, parent, stage, router, emit, runtime, *, p_four,
                  warmup_seed_base, training_seed_base, raw_budget=RAW_BUDGET):
    if life not in range(64) or parent != life%4:
        raise ValueError('V309 lifecycle must belong to its frozen source parent')
    if template.weights.flags.writeable:
        raise ValueError('V309 SOURCE acquisition actor must be frozen')
    started, cpu_started = perf_counter(), process_time()
    child_before = resource.getrusage(resource.RUSAGE_CHILDREN)
    expected = dict(lifecycle=life, parent=parent, warmup={},
        arms={'FROZEN':{'phases':{stage:dict(training={}, snapshot={})}}})
    replay = _Replay(expected, stage)
    before_updates = template.updates
    memory, warmup, decision = _detect(template, life, parent, emit, replay,
        stage, p_four, warmup_seed_base, router)
    expected['warmup'] = warmup
    detector_p = memory.predict()
    replay.memory.predict()
    warmup['memory_counts'] = dict(memory.counts)
    detector_belief = dict(memory=memory.to_payload(), estimated_p_four=detector_p)
    route = router.commit(detector_belief['memory'], decision)
    emit(dict(kind='DETECTION_SNAPSHOT', lifecycle=life, parent=parent, phase=stage,
        true_p_four=p_four, detector_belief=detector_belief, route=route))
    if not route['created']:
        if template.updates != before_updates:
            raise ValueError('SOURCE was updated during detector warmup')
        child_after = resource.getrusage(resource.RUSAGE_CHILDREN)
        acquisition = dict(warmup=warmup, training=None, snapshot=None,
            native_setup_counts={}, native_setup_seconds=0.,
            reconstruction=dict(counts=dict(replay.processing), memory_counts=dict(replay.memory.counts),
                chunks=0, cpu_seconds=replay.cpu_seconds),
            cpu_seconds=process_time()-cpu_started, wall_seconds=perf_counter()-started,
            compiler_cpu_seconds=child_after.ru_utime+child_after.ru_stime-child_before.ru_utime-child_before.ru_stime,
            new_value_updates=0, physical_acquisitions=0, new_evaluation_games=0)
        return dict(route=route, detector_belief=detector_belief, dataset=None, acquisition=acquisition)
    phase_receipt = expected['arms']['FROZEN']['phases'][stage]
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
            row = dict(kind='TRAIN', lifecycle=life, parent=parent, arm='FROZEN', phase=stage,
                true_p_four=p_four, active_bank_id=0, module_id_before=module_before, model_p_four=p_used,
                memory_events=events, seconds=receipt['seconds'], cpu_seconds=receipt['cpu_seconds'],
                **compact_training(receipt))
            emit(row)
            if any(game['status']=='CUTOFF' for game in receipt['completed_games']):
                raise ValueError('V309 requires natural terminal games; training cutoff retained')
            _reconstruct(replay, replay.train, row)
            chunks += 1
        if template.updates != before_updates:
            raise ValueError('Frozen SOURCE acquisition actor received a value update')
        p_used = memory.predict()
        snapshot = dict(active_bank_id=0, estimated_p_four=p_used, memory=memory_state(memory),
            stream=engine.state(), new_value_updates=0)
        training = dict(raw_tiles=raw_budget, chunks=chunks, before_stream=before_state,
            after_stream=engine.state(), memory_counts=delta(memory.counts, before_memory),
            memory_event_count=memory_events, counts={kind:dict(counts) for kind,counts in engine.counts.items()},
            cpu_seconds=process_time()-train_cpu, wall_seconds=perf_counter()-train_started)
        phase_receipt.update(training=training, snapshot=snapshot)
        emit(dict(kind='ACQUISITION_SNAPSHOT', lifecycle=life, parent=parent,
            arm='FROZEN', phase=stage, true_p_four=p_four, snapshot=snapshot, training=training))
        _reconstruct(replay, replay.checkpoint, dict(snapshot=snapshot))
        finish_started = process_time(); dataset = replay.finish()
        replay.cpu_seconds += process_time()-finish_started
        dataset['costs']['processing_cpu_seconds'] = replay.cpu_seconds
        child_after = resource.getrusage(resource.RUSAGE_CHILDREN)
        acquisition = dict(warmup=warmup, training=training, snapshot=snapshot,
            native_setup_counts=dict(engine.setup_counts), native_setup_seconds=engine.setup_seconds,
            reconstruction=dict(counts=dict(replay.processing), memory_counts=dict(replay.memory.counts),
                chunks=replay.chunks, cpu_seconds=replay.cpu_seconds),
            cpu_seconds=process_time()-cpu_started, wall_seconds=perf_counter()-started,
            compiler_cpu_seconds=child_after.ru_utime+child_after.ru_stime-child_before.ru_utime-child_before.ru_stime,
            new_value_updates=0, physical_acquisitions=1, new_evaluation_games=0)
        return dict(route=route, detector_belief=detector_belief, dataset=dataset, acquisition=acquisition)
    finally:
        engine.close()
