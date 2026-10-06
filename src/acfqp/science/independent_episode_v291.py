"""Frozen V290 methods on fresh acquisition and complete paired games."""
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
import gzip
import json
from pathlib import Path
import resource
from time import perf_counter, process_time

from .controlled_predictive_online_query_td_v131 import QueryTD
from .controlled_predictive_regime_memory_v115 import SpawnMemory
from .independent_actor_data_v291 import acquire_dataset, RAW_BUDGET
from .independent_episode_analysis_v291 import summarize, ARMS, BOOTSTRAP_SEED
from .natural_model_revision_v281 import load_leaf, QUERY, MAX_STEPS
from .native_episode_consolidation_v290 import fit_consolidated
from .native_retained_critic_v287 import score_retained
from .native_value_stream_v286 import NativeValueStream
from .retained_critic_v287 import compact_dataset

EVALUATION_GAMES = 32


def evaluation_seed(life, episode):
    return 291900000000+life*1000000+episode


def configuration(source_summary):
    return dict(schema='acfqp.independent_episode_freeze.v291',
        protocol=str(Path(__file__).resolve().parents[3]/'specs/INDEPENDENT_EPISODE_V291.md'),
        source_summary=str(Path(source_summary).resolve()), lifecycles=list(range(64)), parents=4,
        arms=ARMS, phase='A', raw_budget=RAW_BUDGET, fit_fraction=.8, alpha=.0025, query=QUERY,
        seed_warmup=291100000000, seed_training=291200000000, seed_evaluation=291900000000,
        evaluation_games=EVALUATION_GAMES, max_steps=MAX_STEPS,
        bootstrap_draws=20000, bootstrap_seed=BOOTSTRAP_SEED,
        primary='EPISODE_MEAN_MC_minus_FROZEN_COMPLETE_GAME_UTILITY',
        primary_prediction='EPISODE_MEAN_MC_minus_FROZEN_COMPLETE_HELDOUT_MSE',
        evaluation='STATIC_SAME_FIT_PREFIX_BELIEF_WITHOUT_VALUE_OR_MEMORY_UPDATES',
        finite_test_passes=dict(acquisition=6, analysis=14, driver=3))


def _run_lifecycle(template, data, acquisition, life, parent, runtime, engine):
    memory = SpawnMemory.from_payload(data['fit_memory'])
    p = memory.predict()
    arms, inventory = {}, []
    for arm in ARMS:
        if arm == 'FROZEN':
            leaf = template
            fit = dict(method='NONE', trained_afterstates=0, learning_counts={}, target_counts={},
                consolidation_counts={}, seconds=0., cpu_seconds=0.)
            head_setup = dict(source_weights_shared=True, setup_counts={}, setup_seconds=0., private_weight_bytes=0)
        else:
            leaf = QueryTD(template.parent, 'PRIOR', runtime)
            head_setup = dict(source_weights_shared=False, setup_counts=dict(leaf.setup_counts),
                setup_seconds=leaf.setup_seconds, private_weight_bytes=leaf.weights.nbytes)
            fit = fit_consolidated(leaf, data, arm, runtime)
            leaf.freeze()
            inventory.append(fit['trained_afterstates'])
        updates_before = leaf.updates
        heldout = score_retained(leaf, data, runtime)
        before_eval = engine.state()
        evaluated = engine.evaluate_games(leaf, p, .1,
            [evaluation_seed(life, e) for e in range(EVALUATION_GAMES)], depth=2, max_steps=MAX_STEPS)
        if engine.state() != before_eval or leaf.updates != updates_before:
            raise ValueError('Static evaluation altered the critic or acquisition stream')
        arms[arm] = dict(fit=fit, head_setup=head_setup, heldout=heldout,
            processed_training_samples=fit['trained_afterstates'], sample_counter=leaf.updates,
            game_summaries=evaluated['game_summaries'], evaluation_counts=evaluated['counts'],
            evaluation_seconds=evaluated['seconds'], evaluation_cpu_seconds=evaluated['cpu_seconds'])
        print(json.dumps(dict(event='independent_episode_arm_complete', lifecycle=life, arm=arm,
            samples=fit['trained_afterstates'], parameter_writes=fit['learning_counts'].get('table_updates', 0),
            heldout=heldout['metrics'],
            mean_utility=sum(g['utility'] for g in evaluated['game_summaries'])/EVALUATION_GAMES)), flush=True)
        if arm != 'FROZEN':
            del leaf
    if len(set(inventory)) != 1 or template.updates != 0:
        raise ValueError('Learner inventories differ or the acquisition source was trained')
    return dict(lifecycle=life, parent=parent, dataset=compact_dataset(data), acquisition=acquisition,
        evaluation_snapshot=dict(memory=memory.to_payload(), estimated_p_four=p), arms=arms)


def _run_parent(source, output):
    started, cpu_started = perf_counter(), process_time()
    child_before = resource.getrusage(resource.RUSAGE_CHILDREN)
    parent = source['parent']
    runtime = Path(output)/'runtime'/f'parent_{parent}'
    runtime.mkdir(parents=True, exist_ok=True)
    template, setup = load_leaf(source, runtime)
    engine = NativeValueStream(template, evaluation_seed(parent, 0), runtime)
    trace = Path(output)/f'parent_{parent}_records.jsonl.gz'
    rows = []
    try:
        with gzip.open(trace, 'xt') as stream:
            def emit(row):
                stream.write(json.dumps(row, separators=(',', ':'), allow_nan=False)+'\n')
            for life in range(parent, 64, 4):
                acquired = acquire_dataset(template, life, parent, emit, runtime)
                rows.append(_run_lifecycle(template, acquired['dataset'], acquired['acquisition'],
                    life, parent, runtime, engine))
                stream.flush()
                del acquired
    finally:
        engine.close()
    child_after = resource.getrusage(resource.RUSAGE_CHILDREN)
    return dict(parent=parent, lifecycles=rows, source_setup=setup,
        trace_file=str(trace.resolve()), trace_bytes=trace.stat().st_size,
        native_evaluation_setup=dict(counts=dict(engine.setup_counts), seconds=engine.setup_seconds),
        cpu_seconds=process_time()-cpu_started, wall_seconds=perf_counter()-started,
        compiler_cpu_seconds=child_after.ru_utime+child_after.ru_stime-child_before.ru_utime-child_before.ru_stime)


def build_accounting(old, lives, parents, cpu, wall):
    """Old sources are inherited; old pilot target histories are not new inputs."""
    def summed(values):
        return dict(sum((Counter(value) for value in values), Counter()))
    def stage_targets(arm, stage):
        return [life['arms'][arm][stage]['target_counts'] for life in lives]
    def total_targets(values):
        return summed({k:v for k,v in value.items() if k!='target_buffer_doubles_peak'} for value in values)
    inherited_old = old['accounting']['inherited_costs_per_arm']['FROZEN']
    inherited = {key:inherited_old[key] for key in ('source_training_raw_tiles', 'source_training_games',
        'source_training_environment_counts', 'source_training_seconds', 'dynamics_raw_tiles', 'dynamics_costs')}
    warm_raw = sum(l['acquisition']['warmup']['raw_tiles'] for l in lives)
    actor_raw = sum(l['acquisition']['training']['raw_tiles'] for l in lives)
    economic = inherited['source_training_raw_tiles']+inherited['dynamics_raw_tiles']+warm_raw+actor_raw
    training_counts = {kind:summed(l['acquisition']['training']['counts'][kind] for l in lives)
        for kind in ('environment', 'planning', 'learning')}
    warm_environment = summed(l['acquisition']['warmup']['environment_counts'] for l in lives)
    environment = summed([training_counts['environment'], warm_environment])
    environment['raw_tile_productions'] = actor_raw+warm_raw
    consolidated = {a:[l['arms'][a]['fit']['consolidation_counts'] for l in lives] for a in ARMS}
    return dict(new_training_environment_observations=actor_raw+warm_raw,
        physical_acquisitions=len(lives), new_warmup_raw_tiles=warm_raw, new_actor_A_raw_tiles=actor_raw,
        economic_training_raw_tiles_per_arm=dict.fromkeys(ARMS, economic),
        inherited_costs_per_arm={a:inherited for a in ARMS},
        new_training_environment_counts=environment, new_actor_A_counts=training_counts,
        new_warmup_environment_counts=warm_environment,
        new_warmup_direct_counts=summed(l['acquisition']['warmup']['direct_counts'] for l in lives),
        new_warmup_memory_counts=summed(l['acquisition']['warmup']['memory_counts'] for l in lives),
        new_actor_memory_counts=summed(l['acquisition']['training']['memory_counts'] for l in lives),
        reconstruction_counts=summed(l['acquisition']['reconstruction']['counts'] for l in lives),
        reconstruction_memory_counts=summed(l['acquisition']['reconstruction']['memory_counts'] for l in lives),
        reconstruction_cpu_seconds=sum(l['acquisition']['reconstruction']['cpu_seconds'] for l in lives),
        excluded_tail_raw_tiles=sum(l['dataset']['costs']['excluded_tail_raw_tiles'] for l in lives),
        processed_training_samples={a:sum(l['arms'][a]['processed_training_samples'] for l in lives) for a in ARMS},
        fit_counts={a:summed(l['arms'][a]['fit']['learning_counts'] for l in lives) for a in ARMS},
        fit_target_counts={a:total_targets(stage_targets(a, 'fit')) for a in ARMS},
        fit_target_buffer_doubles_peak={a:max(v.get('target_buffer_doubles_peak', 0)
            for v in stage_targets(a, 'fit')) for a in ARMS},
        consolidation_counts={a:summed({k:v for k,v in value.items() if not k.endswith('_peak')}
            for value in consolidated[a]) for a in ARMS},
        consolidation_buffer_peaks={a:{k:max(value.get(k, 0) for value in consolidated[a])
            for k in {key for value in consolidated[a] for key in value if key.endswith('_peak')}} for a in ARMS},
        heldout_prediction_counts={a:summed(l['arms'][a]['heldout']['prediction_counts'] for l in lives) for a in ARMS},
        heldout_target_counts={a:total_targets(stage_targets(a, 'heldout')) for a in ARMS},
        heldout_target_buffer_doubles_peak={a:max(v.get('target_buffer_doubles_peak', 0)
            for v in stage_targets(a, 'heldout')) for a in ARMS},
        evaluation_counts={kind:summed(l['arms'][a]['evaluation_counts'][kind] for l in lives for a in ARMS)
            for kind in ('environment', 'planning')},
        evaluation_counts_per_arm={a:{kind:summed(l['arms'][a]['evaluation_counts'][kind] for l in lives)
            for kind in ('environment', 'planning')} for a in ARMS},
        private_head_weight_bytes_created={a:sum(l['arms'][a]['head_setup']['private_weight_bytes'] for l in lives) for a in ARMS},
        processing_seconds_per_arm={a:{stage:sum(l['arms'][a][stage]['seconds'] for l in lives)
            for stage in ('fit', 'heldout')} for a in ARMS},
        processing_cpu_seconds_per_arm={a:{stage:sum(l['arms'][a][stage]['cpu_seconds'] for l in lives)
            for stage in ('fit', 'heldout')} for a in ARMS},
        evaluation_cpu_seconds_per_arm={a:sum(l['arms'][a]['evaluation_cpu_seconds'] for l in lives) for a in ARMS},
        canonical_trace_bytes=sum(p['trace_bytes'] for p in parents),
        worker_cpu_seconds=sum(p['cpu_seconds'] for p in parents),
        compiler_cpu_seconds=sum(p['compiler_cpu_seconds'] for p in parents), coordinator_cpu_seconds=cpu, wall_seconds=wall,
        development_reference=dict(previous_pilot='V290',
            previous_target_acquisition_raw_tiles=inherited_old['warmup_raw_tiles']+inherited_old['retained_actor_A_raw_tiles'],
            previous_evaluation_counts=old['accounting']['evaluation_counts'],
            scope='Previous target acquisition/evaluation are development costs, not inputs to the new fit; '
                'the source training and dynamics are shared with this confirmation, paid once.'),
        accounting_scope='Each arm pays source value/dynamics plus all fresh warmup and A raw, including initial '
            'and excluded tail. Physical source acquisition and each fresh carrier are shared once. '
            'Actual training samples, parameter writes, consolidation and complete-game evaluation are separate. '
            'Reconstruction CPU is a component of acquisition/worker CPU, not an additional total.')


def run(source_summary, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    if (output/'configuration.json').exists() or (output/'summary.json').exists():
        raise FileExistsError('V291 formal freeze or results already exist')
    old = json.loads(Path(source_summary).read_text())
    if not json.loads(Path(source_summary).with_name('audit.json').read_text())['independent_valid']:
        raise ValueError('V290 methods require their passing independent audit')
    settings = configuration(source_summary)
    (output/'configuration.json').write_text(json.dumps(settings, indent=2)+'\n')
    started, cpu_started = perf_counter(), process_time()
    parents = []
    with ProcessPoolExecutor(max_workers=4) as pool:
        jobs = [pool.submit(_run_parent, source, output) for source in old['source_provenance']['parents']]
        for job in as_completed(jobs):
            parents.append(job.result())
    parents.sort(key=lambda p:p['parent'])
    lives = sorted([l for p in parents for l in p['lifecycles']], key=lambda l:l['lifecycle'])
    analysis = summarize(lives)
    result = dict(schema='acfqp.independent_episode.v291', status='EXPERIMENT_COMPLETE',
        scientific_gate='NOT_A_FORMAL_GATE', settings=settings, source_provenance=old['source_provenance'],
        by_lifecycle=lives, parent_receipts=[dict({k:v for k,v in p.items() if k!='lifecycles'},
            lifecycle_ids=[l['lifecycle'] for l in p['lifecycles']]) for p in parents],
        summary=analysis, accounting=build_accounting(old, lives, parents, process_time()-cpu_started, perf_counter()-started))
    (output/'summary.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps(dict(event='independent_episode_complete', status=result['status'],
        independent_learning_confirmed=analysis['independent_learning_confirmed'],
        utility_primary=analysis['paired_contrasts'][analysis['primary_contrast']],
        mse_primary=analysis['heldout_contrasts'][analysis['primary_contrast']]['mse'])), flush=True)
    return result
