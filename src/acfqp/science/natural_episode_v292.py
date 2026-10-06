"""New continuous A/B/A lifecycles with causal complete-game value learning."""
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
import gzip
import json
from pathlib import Path
import resource
from time import perf_counter, process_time

from .controlled_predictive_regime_experience_v115 import run_episode
from .controlled_predictive_regime_memory_v115 import SpawnMemory, WARMUP
from .natural_model_revision_v281 import load_leaf, QUERY, MAX_STEPS, delta, utility
from .natural_online_value_v286 import memory_state
from .online_episode_stream_v292 import run_arm, ARMS, PHASES, RAW_TILES_PER_PHASE, EVALUATION_GAMES
from .natural_episode_analysis_v292 import summarize


def warmup_seed(life, game):
    return 292100000000+life*1000000+game


def configuration(source_summary, finite_test_passes):
    return dict(schema='acfqp.natural_episode_freeze.v292',
        protocol=str(Path(__file__).resolve().parents[3]/'specs/NATURAL_EPISODE_V292.md'),
        source_summary=str(Path(source_summary).resolve()), lifecycles=list(range(16)), parents=4,
        arms=ARMS, phases=PHASES, raw_tiles_per_phase=RAW_TILES_PER_PHASE,
        evaluation_games=EVALUATION_GAMES, max_steps=MAX_STEPS, alpha=.0025, query=QUERY,
        seed_warmup=292100000000, seed_training=292200000000, seed_evaluation=292900000000,
        bootstrap_seed=29200001, bootstrap_draws=20000,
        primary='MEAN_H2_minus_FROZEN_H2_THREE_PHASE_COMPLETE_GAME_UTILITY',
        training='IMMEDIATE_NATURAL_GAME_CONSOLIDATION_WITHOUT_NATIVE_SARSA',
        memory_input='ALL_RAW_SPAWNS_INCLUDING_INITIAL',
        retention='SAVED_A_BELIEF_AND_A_SEEDS_ACROSS_ALL_CHECKPOINTS',
        correction='CURRENT_B_HEAD_MINUS_SAVED_A_HEAD_WITH_SAME_B_BELIEF_AND_SEEDS',
        finite_test_passes=finite_test_passes)


def warmup(template, life, parent, emit):
    memory, games, environment, events = SpawnMemory('LIBRARY'), [], Counter(), []
    started, cpu_started = perf_counter(), process_time()
    before = dict(template.counts)
    while memory.observations_seen < WARMUP:
        game_before = dict(template.counts)
        game = run_episode(warmup_seed(life, len(games)),
            lambda board, step: template.choose(board, QUERY)['action'], .1, MAX_STEPS)
        spawns = [dict(s, kind='INITIAL') for s in game['initial_spawns']]
        spawns.extend(dict(rank=s['spawned_rank'], cell=s['spawned_cell'], kind='POST_ACTION') for s in game['steps'])
        for spawn in spawns:
            event = memory.observe(spawn['rank'])
            if event is not None:
                events.append(event)
        summary = dict(seed=warmup_seed(life, len(games)), score=game['return_score'],
            status=game['status'], steps=game['steps_count'], utility=utility(game))
        games.append(summary); environment.update(game['work'])
        emit(dict(kind='WARMUP', lifecycle=life, parent=parent, summary=summary,
            raw_spawns=spawns, actions=[s['action'] for s in game['steps']],
            scores=[s['score'] for s in game['steps']], final_board=game['final_board'],
            counts=dict(environment=game['work'], direct=delta(template.counts, game_before))))
        if game['status'] == 'CUTOFF':
            raise ValueError('Natural warmup cutoff retained; confirmation cannot start')
    return memory, dict(game_summaries=games, raw_tiles=memory.observations_seen,
        environment_counts=dict(environment), direct_counts=delta(template.counts, before),
        memory_counts=dict(memory.counts), memory_events=events, final_memory=memory_state(memory),
        cpu_seconds=process_time()-cpu_started, wall_seconds=perf_counter()-started)


def _run_lifecycle(template, life, parent, runtime, emit):
    warmed, costs = warmup(template, life, parent, emit)
    arms = {arm:run_arm(template, warmed, life, arm, emit, runtime) for arm in ARMS}
    for phase, _ in PHASES:
        memories = [arms[a]['phases'][phase]['snapshot']['memory'] for a in ARMS]
        if any(value != memories[0] for value in memories[1:]):
            raise ValueError('Paired raw ranks did not produce the same learned memory')
    if template.updates != 0:
        raise ValueError('The frozen source was updated')
    return dict(lifecycle=life, parent=parent, warmup=costs, arms=arms)


def _run_parent(source, output):
    started, cpu_started = perf_counter(), process_time()
    before_child = resource.getrusage(resource.RUSAGE_CHILDREN)
    parent = source['parent']; runtime = Path(output)/'runtime'/f'parent_{parent}'
    runtime.mkdir(parents=True, exist_ok=True)
    template, setup = load_leaf(source, runtime)
    trace = Path(output)/f'parent_{parent}_records.jsonl.gz'
    rows = []
    with gzip.open(trace, 'xt') as stream:
        def emit(row):
            stream.write(json.dumps(dict(row, parent=parent), separators=(',', ':'), allow_nan=False)+'\n')
            if row['kind'] == 'CHECKPOINT':
                print(json.dumps(dict(event='natural_episode_phase_complete', lifecycle=row['lifecycle'],
                    arm=row['arm'], phase=row['phase'], raw_tiles=row['snapshot']['stream']['raw_tiles'],
                    value_updates=row['snapshot']['value_updates'],
                    mean_utility=sum(g['utility'] for g in row['game_summaries'])/EVALUATION_GAMES)), flush=True)
        for life in range(parent, 16, 4):
            rows.append(_run_lifecycle(template, life, parent, runtime, emit)); stream.flush()
    after_child = resource.getrusage(resource.RUSAGE_CHILDREN)
    return dict(parent=parent, lifecycles=rows, source_setup=setup,
        trace_file=str(trace.resolve()), trace_bytes=trace.stat().st_size,
        cpu_seconds=process_time()-cpu_started, wall_seconds=perf_counter()-started,
        compiler_cpu_seconds=after_child.ru_utime+after_child.ru_stime-before_child.ru_utime-before_child.ru_stime)


def build_accounting(old, lives, parents, cpu, wall):
    def summed(values):
        return dict(sum((Counter(value) for value in values), Counter()))
    inherited = old['accounting']['inherited_costs_per_arm']['FROZEN']
    warm_raw = sum(l['warmup']['raw_tiles'] for l in lives)
    training = {a:{k:summed(l['arms'][a]['training_counts'][k] for l in lives)
        for k in ('environment', 'planning', 'learning')} for a in ARMS}
    raw_per_arm = {a:training[a]['environment']['raw_tile_productions'] for a in ARMS}
    economic = {a:inherited['source_training_raw_tiles']+inherited['dynamics_raw_tiles']+warm_raw+raw_per_arm[a] for a in ARMS}
    fit = {a:[l['arms'][a]['fit_totals'] for l in lives] for a in ARMS}
    evaluation_components = {a:{part:{k:summed(l['arms'][a][part][k] for l in lives)
        for k in ('environment', 'planning')} for part in ('evaluation_counts',
        'retention_evaluation_counts', 'a_head_on_B_evaluation_counts')} for a in ARMS}
    evaluations = {a:{k:summed(value[k] for value in evaluation_components[a].values())
        for k in ('environment', 'planning')} for a in ARMS}
    return dict(physical_training_raw_tiles=sum(raw_per_arm.values()), training_raw_tiles_per_arm=raw_per_arm,
        physical_warmup_raw_tiles=warm_raw, physical_warmup_games=sum(len(l['warmup']['game_summaries']) for l in lives),
        inherited_costs_per_arm={a:inherited for a in ARMS}, economic_training_raw_tiles_per_arm=economic,
        warmup_environment_counts=summed(l['warmup']['environment_counts'] for l in lives),
        warmup_direct_counts=summed(l['warmup']['direct_counts'] for l in lives),
        warmup_memory_counts=summed(l['warmup']['memory_counts'] for l in lives),
        training_counts_per_arm=training, training_counts={k:summed(v[k] for v in training.values())
            for k in ('environment', 'planning', 'learning')},
        evaluation_counts_per_arm=evaluations, evaluation_counts={k:summed(v[k] for v in evaluations.values())
            for k in ('environment', 'planning')},
        evaluation_components_per_arm=evaluation_components,
        processed_training_samples={a:sum(value['trained_afterstates'] for value in fit[a]) for a in ARMS},
        fit_counts={a:summed(value['learning_counts'] for value in fit[a]) for a in ARMS},
        fit_target_counts={a:summed({k:v for k,v in value['target_counts'].items() if not k.endswith('_peak')}
            for value in fit[a]) for a in ARMS},
        consolidation_counts={a:summed({k:v for k,v in value['consolidation_counts'].items() if not k.endswith('_peak')}
            for value in fit[a]) for a in ARMS},
        fit_buffer_peaks={a:{k:max(value[part].get(k, 0) for value in fit[a])
            for part in ('target_counts', 'consolidation_counts')
            for k in {name for value in fit[a] for name in value[part] if name.endswith('_peak')}} for a in ARMS},
        final_unfitted_raw_tiles_per_arm={a:sum(l['arms'][a]['final_unfitted_game']['raw_tiles'] for l in lives) for a in ARMS},
        private_head_weight_bytes_created={a:sum(l['arms'][a]['head_setup']['private_weight_bytes'] for l in lives) for a in ARMS},
        retained_A_head_setups=[l['arms']['MEAN_H2']['retained_A_head_setup'] for l in lives],
        fit_cpu_seconds_per_arm={a:sum(v['cpu_seconds'] for v in fit[a]) for a in ARMS},
        arm_cpu_seconds={a:sum(l['arms'][a]['costs']['cpu_seconds'] for l in lives) for a in ARMS},
        reconstruction_counts=summed(l['arms'][a]['costs']['reconstruction_counts'] for l in lives for a in ARMS),
        reconstruction_cpu_seconds=sum(l['arms'][a]['costs']['reconstruction_cpu_seconds'] for l in lives for a in ARMS),
        memory_counts_per_arm={a:summed(l['arms'][a]['final_memory']['counts'] for l in lives) for a in ARMS},
        worker_cpu_seconds=sum(p['cpu_seconds'] for p in parents), compiler_cpu_seconds=sum(p['compiler_cpu_seconds'] for p in parents),
        coordinator_cpu_seconds=cpu, wall_seconds=wall, canonical_trace_bytes=sum(p['trace_bytes'] for p in parents),
        development_reference=dict(previous_pilot='V291',
            previous_target_acquisition_raw_tiles=old['accounting']['new_training_environment_observations'],
            previous_evaluation_counts=old['accounting']['evaluation_counts'],
            scope='Previous target acquisition/evaluation are development, not online training inputs; sources shared once.'),
        accounting_scope='Equal total training raw, differing real trajectories/samples/writes/CPU. Source and warmup '
            'physical acquisition once; five new training trajectories paid separately. All evaluation cost includes '
            'A probes and saved-A-head-on-B; A-end shared probe charged once. Counter peaks are maxima.')


def run(source_summary, output, finite_test_passes):
    output = Path(output); output.mkdir(parents=True, exist_ok=True)
    if (output/'configuration.json').exists() or (output/'summary.json').exists():
        raise FileExistsError('V292 freeze or results already exist')
    old = json.loads(Path(source_summary).read_text())
    if not json.loads(Path(source_summary).with_name('audit.json').read_text())['independent_valid']:
        raise ValueError('Online experiment requires the confirmed V291 evidence audit')
    settings = configuration(source_summary, finite_test_passes)
    (output/'configuration.json').write_text(json.dumps(settings, indent=2)+'\n')
    started, cpu_started = perf_counter(), process_time(); parents = []
    with ProcessPoolExecutor(max_workers=4) as pool:
        jobs = [pool.submit(_run_parent, source, output) for source in old['source_provenance']['parents']]
        for job in as_completed(jobs):
            parents.append(job.result())
    parents.sort(key=lambda p:p['parent'])
    lives = sorted([l for p in parents for l in p['lifecycles']], key=lambda l:l['lifecycle'])
    analysis = summarize(lives)
    result = dict(schema='acfqp.natural_episode.v292', status='EXPERIMENT_COMPLETE', scientific_gate='NOT_A_FORMAL_GATE',
        settings=settings, source_provenance=old['source_provenance'], by_lifecycle=lives,
        parent_receipts=[dict({k:v for k,v in p.items() if k!='lifecycles'}, lifecycle_ids=[l['lifecycle'] for l in p['lifecycles']]) for p in parents],
        summary=analysis, accounting=build_accounting(old, lives, parents, process_time()-cpu_started, perf_counter()-started))
    (output/'summary.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps(dict(event='natural_episode_complete', status=result['status'],
        primary=analysis['paired_contrasts']['MEAN_H2_minus_FROZEN_H2'])), flush=True)
    return result
