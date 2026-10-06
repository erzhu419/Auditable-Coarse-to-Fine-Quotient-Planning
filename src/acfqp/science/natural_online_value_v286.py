"""Equal raw-observation budgets for frozen, ordinary and persistent value TD."""
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
import gzip
import json
from pathlib import Path
import resource
from time import perf_counter, process_time

from .controlled_predictive_online_query_td_v131 import QueryTD
from .controlled_predictive_regime_experience_v115 import run_episode
from .controlled_predictive_regime_memory_v115 import SpawnMemory, WARMUP, BLOCK
from .natural_model_revision_v281 import load_leaf, PHASES, QUERY, MAX_STEPS, delta, utility
from .natural_value_analysis_v286 import summarize, ARMS

RAW_TILES_PER_PHASE = 131072
EVALUATION_GAMES = 16


def training_seed(life):
    return 286200000000 + life*10000000


def evaluation_seed(life, phase, episode):
    return 286500000000 + life*1000000 + phase*100000 + episode


def memory_state(memory):
    payload = memory.to_payload()
    return {key: payload[key] for key in ('observations_seen', 'active_module_id', 'modules', 'pending')}


def warmup(leaf, life, emit):
    """Common physical DIRECT games; all raw ranks precede training."""
    memory, games = SpawnMemory('LIBRARY'), []
    started, cpu_started = perf_counter(), process_time()
    env_counts, events = Counter(), []
    before_leaf = dict(leaf.counts)
    while memory.observations_seen < WARMUP:
        seed = 286100000000 + life*1000000 + len(games)
        game = run_episode(seed, lambda board, step: leaf.choose(board, QUERY)['action'], .1, MAX_STEPS)
        spawns = [dict(s, kind='INITIAL') for s in game['initial_spawns']]
        spawns.extend(dict(rank=s['spawned_rank'], cell=s['spawned_cell'], kind='POST_ACTION')
            for s in game['steps'])
        for spawn in spawns:
            event = memory.observe(spawn['rank'])
            if event is not None:
                events.append(event)
        summary = dict(seed=seed, score=game['return_score'], status=game['status'],
            steps=game['steps_count'], utility=utility(game))
        games.append(summary)
        env_counts.update(game['work'])
        emit(dict(kind='WARMUP', lifecycle=life, summary=summary, raw_spawns=spawns,
            actions=[s['action'] for s in game['steps']],
            scores=[s['score'] for s in game['steps']], final_board=game['final_board']))
    return memory, dict(game_summaries=games, raw_tiles=memory.observations_seen,
        environment_counts=dict(env_counts), direct_counts=delta(leaf.counts, before_leaf),
        memory_counts=dict(memory.counts), memory_events=events,
        final_memory=memory_state(memory), cpu_seconds=process_time()-cpu_started,
        wall_seconds=perf_counter()-started)


def compact_training(receipt):
    """Keep reconstructible feedback and decisions rather than repeated boards."""
    result = {key: receipt[key] for key in ('start', 'end', 'raw_spawns', 'actions',
        'scores', 'completed_games', 'counts')}
    updates = receipt['updates']
    result['bank_update_counts'] = dict(Counter(str(u['bank_id']) for u in updates))
    result['td_examples'] = [] if not updates else [updates[0], updates[-1]]
    return result


def run_arm(template, warmed, life, arm, emit, runtime):
    from .native_value_stream_v286 import NativeValueStream
    memory = SpawnMemory.from_payload(warmed.to_payload())
    banks, bank_setups = {}, []
    started, cpu_started = perf_counter(), process_time()
    children_before = resource.getrusage(resource.RUSAGE_CHILDREN)

    def get_bank():
        bank_id = memory.module_id if arm == 'PERSISTENT_TD' else 0
        if bank_id not in banks:
            if arm == 'FROZEN':
                banks[bank_id] = template
                bank_setups.append(dict(bank_id=bank_id, source_weights_shared=True,
                    setup_counts={}, setup_seconds=0., weight_bytes=template.weights.nbytes))
            else:
                bank = QueryTD(template.parent, 'PRIOR', runtime)
                banks[bank_id] = bank
                bank_setups.append(dict(bank_id=bank_id, source_weights_shared=False,
                    setup_counts=dict(bank.setup_counts), setup_seconds=bank.setup_seconds,
                    weight_bytes=bank.weights.nbytes))
        return bank_id, banks[bank_id]

    engine = NativeValueStream(template, training_seed(life), runtime, max_steps=MAX_STEPS)
    phases, eval_counts = {}, {kind: Counter() for kind in ('environment', 'planning')}
    eval_seconds = eval_cpu_seconds = 0.
    for phase_index, (phase, env_p) in enumerate(PHASES):
        before_engine = {key: dict(value) for key, value in engine.counts.items()}
        before_memory, before_state = dict(memory.counts), engine.state()
        goal_tiles = (phase_index+1)*RAW_TILES_PER_PHASE
        memory_events, chunks = [], 0
        while engine.state()['raw_tiles'] < goal_tiles:
            bank_id, active = get_bank()
            state = engine.state()
            old_bank_id = state['pending_bank_id']
            pending = banks.get(old_bank_id) if old_bank_id is not None and old_bank_id >= 0 else None
            remaining = min(goal_tiles-state['raw_tiles'], BLOCK-memory.pending_n)
            p_used = memory.predict()
            module_before = memory.module_id
            receipt = engine.advance(active, bank_id, pending, p_used, env_p,
                tile_budget=remaining, max_postaction=BLOCK)
            events = []
            for spawn in receipt['raw_spawns']:
                event = memory.observe(spawn['rank'])
                if event is not None:
                    events.append(event)
                    memory_events.append(event)
            row = compact_training(receipt)
            emit(dict(kind='TRAIN', lifecycle=life, arm=arm, phase=phase,
                active_bank_id=bank_id, module_id_before=module_before,
                model_p_four=p_used, memory_events=events, **row))
            chunks += 1
        bank_id, active = get_bank()
        p_used = memory.predict()
        snapshot = dict(active_bank_id=bank_id, estimated_p_four=p_used,
            memory=memory_state(memory), stream=engine.state(),
            banks={str(i): dict(updates=b.updates, weight_bytes=b.weights.nbytes)
                   for i, b in banks.items()})
        seeds = [evaluation_seed(life, phase_index, episode) for episode in range(EVALUATION_GAMES)]
        before_eval = engine.state()
        evaluated = engine.evaluate_games(active, p_used, env_p, seeds, depth=2)
        if engine.state() != before_eval:
            raise ValueError('Checkpoint evaluation changed the training stream')
        for kind in eval_counts:
            eval_counts[kind].update(evaluated['counts'][kind])
        eval_seconds += evaluated['seconds']
        eval_cpu_seconds += evaluated['cpu_seconds']
        emit(dict(kind='EVALUATION', lifecycle=life, arm=arm, phase=phase,
            snapshot=snapshot, **evaluated))
        phases[phase] = dict(game_summaries=evaluated['game_summaries'], snapshot=snapshot,
            training=dict(raw_tiles=RAW_TILES_PER_PHASE, chunks=chunks,
                before_stream=before_state, after_stream=engine.state(),
                memory_events=memory_events, memory_counts=delta(memory.counts, before_memory),
                counts={key: delta(value, before_engine.get(key, {}))
                        for key, value in engine.counts.items()}),
            evaluation_counts=evaluated['counts'], evaluation_seconds=evaluated['seconds'])
        print(json.dumps(dict(event='value_phase_complete', lifecycle=life, arm=arm, phase=phase,
            raw_tiles=engine.state()['raw_tiles'], banks=len(banks),
            mean_eval_utility=sum(g['utility'] for g in evaluated['game_summaries'])/EVALUATION_GAMES)), flush=True)
    direct = None
    if arm == 'PERSISTENT_TD':
        direct = engine.evaluate_games(active, p_used, PHASES[-1][1], seeds, depth=1)
        emit(dict(kind='DIRECT_FINAL', lifecycle=life, snapshot=snapshot, **direct))
        for kind in eval_counts:
            eval_counts[kind].update(direct['counts'][kind])
        eval_seconds += direct['seconds']
        eval_cpu_seconds += direct['cpu_seconds']
    children_after = resource.getrusage(resource.RUSAGE_CHILDREN)
    result = dict(phases=phases, final_memory=memory_state(memory),
        final_stream=engine.state(), training_counts={key: dict(value) for key, value in engine.counts.items()},
        native_setup_counts=dict(engine.setup_counts), native_setup_seconds=engine.setup_seconds,
        bank_setups=bank_setups, bank_counts={str(i): dict(b.counts) if arm != 'FROZEN' else {}
            for i, b in banks.items()}, new_value_updates=sum(b.updates for b in banks.values()),
        private_weight_bytes=sum(b.weights.nbytes for b in banks.values()) if arm != 'FROZEN' else 0,
        evaluation_counts={key: dict(value) for key, value in eval_counts.items()},
        evaluation_seconds=eval_seconds, evaluation_cpu_seconds=eval_cpu_seconds,
        cpu_seconds=process_time()-cpu_started, wall_seconds=perf_counter()-started,
        compiler_cpu_seconds=children_after.ru_utime+children_after.ru_stime
            - children_before.ru_utime-children_before.ru_stime)
    engine.close()
    return result, direct


def _run_parent(source, output):
    output = Path(output)
    runtime = output/'runtime'/f"parent_{source['parent']}"
    runtime.mkdir(parents=True, exist_ok=True)
    started, cpu_started = perf_counter(), process_time()
    children_before = resource.getrusage(resource.RUSAGE_CHILDREN)
    leaf, setup = load_leaf(source, runtime)
    rows = []
    trace = output/f"parent_{source['parent']}_records.jsonl.gz"
    with gzip.open(trace, 'xt', encoding='utf-8') as stream:
        def emit(row):
            stream.write(json.dumps(row, separators=(',', ':'), allow_nan=False)+'\n')
        for life in range(source['parent'], 16, 4):
            warmed, warm_costs = warmup(leaf, life, emit)
            arms, direct = {}, None
            for arm in ARMS:
                arms[arm], final = run_arm(leaf, warmed, life, arm, emit, runtime)
                if final is not None:
                    direct = final
            for phase, _ in PHASES:
                memories = [arms[a]['phases'][phase]['snapshot']['memory'] for a in ARMS]
                if any(m != memories[0] for m in memories[1:]):
                    raise ValueError('Same raw observations produced different arm memories')
            rows.append(dict(lifecycle=life, parent=source['parent'], warmup=warm_costs,
                arms=arms, direct_final=direct))
            stream.flush()
    children_after = resource.getrusage(resource.RUSAGE_CHILDREN)
    return dict(parent=source['parent'], lifecycles=rows, setup=setup,
        trace_file=str(trace.resolve()), trace_bytes=trace.stat().st_size,
        cpu_seconds=process_time()-cpu_started, wall_seconds=perf_counter()-started,
        compiler_cpu_seconds=children_after.ru_utime+children_after.ru_stime
            - children_before.ru_utime-children_before.ru_stime)


def compact_summary(result):
    """Route events remain in gz receipts; keep one lifecycle copy in JSON."""
    for life in result['by_lifecycle']:
        for arm in ARMS:
            for phase, _ in PHASES:
                training = life['arms'][arm]['phases'][phase]['training']
                training['memory_event_count'] = len(training.pop('memory_events'))
    result['parent_receipts'] = [dict(
        {key: value for key, value in parent.items() if key != 'lifecycles'},
        lifecycle_ids=[life['lifecycle'] for life in parent['lifecycles']])
        for parent in result['parent_receipts']]
    return result


def run(source_summary, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    if (output/'summary.json').exists() or list(output.glob('parent_*_records.jsonl.gz')):
        raise FileExistsError('V286 receipts already exist')
    original = json.loads(Path(source_summary).read_text())
    started, cpu_started = perf_counter(), process_time()
    parents = []
    with ProcessPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(_run_parent, source, output)
            for source in original['source_provenance']['parents']]
        for future in as_completed(futures):
            parents.append(future.result())
    parents.sort(key=lambda row: row['parent'])
    lives = sorted([life for parent in parents for life in parent['lifecycles']],
        key=lambda row: row['lifecycle'])
    analysis = summarize(lives)
    train, evaluate = {}, {}
    for key in ('environment', 'planning', 'learning'):
        train[key] = dict(sum((Counter(life['arms'][arm]['training_counts'][key])
            for life in lives for arm in ARMS), Counter()))
    for key in ('environment', 'planning'):
        evaluate[key] = dict(sum((Counter(life['arms'][arm]['evaluation_counts'][key])
            for life in lives for arm in ARMS), Counter()))
    source_costs = original['source_provenance']
    source_environment = dict(sum((Counter(s['inherited_training_costs']['environment_counts'])
        for s in source_costs['parents']), Counter()))
    warmed_environment = dict(sum((Counter(life['warmup']['environment_counts'])
        for life in lives), Counter()))
    inherited = dict(source_training_environment_counts=source_environment,
        source_training_raw_tiles=source_environment['sampled_transitions']+source_environment['initial_spawns'],
        source_training_games=sum(s['inherited_training_costs']['training_games'] for s in source_costs['parents']),
        source_training_seconds=sum(s['inherited_training_costs']['training_seconds'] for s in source_costs['parents']),
        dynamics_costs=source_costs['inherited_dynamics_costs'],
        dynamics_raw_tiles=source_costs['inherited_dynamics_costs']['source_environment']['sampled_transitions']
            +source_costs['inherited_dynamics_costs']['source_environment']['initial_spawns'],
        warmup_raw_tiles=sum(life['warmup']['raw_tiles'] for life in lives),
        warmup_environment_counts=warmed_environment,
        warmup_direct_counts=dict(sum((Counter(life['warmup']['direct_counts']) for life in lives), Counter())),
        warmup_memory_counts=dict(sum((Counter(life['warmup']['memory_counts']) for life in lives), Counter())),
        warmup_cpu_seconds=sum(life['warmup']['cpu_seconds'] for life in lives),
        warmup_wall_seconds=sum(life['warmup']['wall_seconds'] for life in lives))
    result = dict(schema='acfqp.natural_online_value.v286', status='EXPERIMENT_COMPLETE',
        scientific_gate='NOT_A_FORMAL_GATE', source_summary=str(Path(source_summary).resolve()),
        settings=dict(arms=ARMS, phases=PHASES, lifecycles=list(range(16)), parents=4,
            raw_tiles_per_phase=RAW_TILES_PER_PHASE, evaluation_games=EVALUATION_GAMES,
            query=QUERY, alpha=.0025, max_steps=MAX_STEPS,
            memory_input='ALL_RAW_SPAWN_RANKS_INCLUDING_INITIAL_TILES',
            training='SAMPLED_AFTERSTATE_SARSA_WITH_FIXED_BEFORE_UPDATE_NEXT_ACTION',
            evaluation='FIXED_VALUE_AND_BELIEF_WITHOUT_FEEDBACK',
            seed_training=286200000000, seed_warmup=286100000000, seed_evaluation=286500000000),
        source_provenance=original['source_provenance'], summary=analysis,
        by_lifecycle=lives, parent_receipts=parents,
        accounting=dict(training_raw_tiles=16*len(ARMS)*len(PHASES)*RAW_TILES_PER_PHASE,
            training_counts=train, evaluation_counts=evaluate,
            training_raw_tiles_per_arm=16*len(PHASES)*RAW_TILES_PER_PHASE,
            inherited_costs_per_arm={arm: inherited for arm in ARMS},
            economic_training_raw_tiles_per_arm={arm: inherited['source_training_raw_tiles']
                +inherited['dynamics_raw_tiles']+inherited['warmup_raw_tiles']
                +16*len(PHASES)*RAW_TILES_PER_PHASE for arm in ARMS},
            new_value_updates={arm: sum(life['arms'][arm]['new_value_updates'] for life in lives) for arm in ARMS},
            physical_warmup_raw_tiles=sum(life['warmup']['raw_tiles'] for life in lives),
            physical_warmup_games=sum(len(life['warmup']['game_summaries']) for life in lives),
            physical_warmup_environment_counts=warmed_environment,
            inherited_source_training_transitions=sum(s['inherited_training_costs']['environment_counts']['sampled_transitions']
                for s in original['source_provenance']['parents']),
            inherited_dynamics_costs=original['source_provenance']['inherited_dynamics_costs'],
            observation_scope='Economic source and shared warmup inherited equally by every arm; physical costs counted once.',
            worker_cpu_seconds=sum(p['cpu_seconds'] for p in parents),
            compiler_cpu_seconds=sum(p['compiler_cpu_seconds'] for p in parents),
            coordinator_cpu_seconds=process_time()-cpu_started,
            wall_seconds=perf_counter()-started, trace_bytes=sum(p['trace_bytes'] for p in parents)))
    compact_summary(result)
    (output/'summary.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps(dict(event='online_value_complete', status=result['status'],
        primary=analysis['paired_contrasts']['PERSISTENT_TD_minus_ORDINARY_TD'],
        accounting=result['accounting'])), flush=True)
    return result
