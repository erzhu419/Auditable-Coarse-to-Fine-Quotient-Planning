"""Fixed-data shadow learning with independently validated policy deployment."""
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
from .shadow_deployment_core_v293 import (run_lifecycle, ARMS, PHASES,
    CARRIER_RAW_PER_PHASE, ONLINE_RAW_PER_PHASE, EVALUATION_GAMES, VALIDATION_PAIRS)
from .shadow_deployment_analysis_v293 import analyze


def warmup_seed(life, game):
    return 293100010000+life*1000000+game


def configuration(source_summary, finite_test_passes):
    return dict(schema='acfqp.shadow_deployment_freeze.v293',
        protocol=str(Path(__file__).resolve().parents[3]/'specs/SHADOW_DEPLOYMENT_V293.md'),
        source_summary=str(Path(source_summary).resolve()), lifecycles=list(range(16)), parents=4,
        arms=ARMS, phases=PHASES, carrier_raw_tiles_per_phase=CARRIER_RAW_PER_PHASE,
        online_raw_tiles_per_arm_phase=ONLINE_RAW_PER_PHASE, validation_pairs=VALIDATION_PAIRS,
        evaluation_games=EVALUATION_GAMES, max_steps=MAX_STEPS, alpha=.0025, query=QUERY,
        seed_warmup=293100010000, seed_carrier=293200010000, seed_deployment=293400010000,
        seed_validation=293600010000, seed_evaluation=293900010000,
        bootstrap_seed=29300001, bootstrap_draws=20000,
        primary='VALIDATED_H2_minus_FROZEN_H2_THREE_PHASE_COMPLETE_GAME_UTILITY',
        mechanism='VALIDATED_H2_minus_UNCONDITIONAL_H2',
        submission='EIGHT_PAIRED_T_95_LOWER_STRICTLY_POSITIVE_AND_NO_CUTOFF',
        student_t_critical_df7=2.364624251,
        acquisition='FROZEN_SOURCE_H2_CARRIER_WITH_PERSISTENT_SHARED_EPISODE_MEAN_SHADOW',
        memory_input='CARRIER_RAW_ONLY_INCLUDING_INITIAL',
        online_budget='SHARED_CARRIER_PLUS_ACTUAL_COMPLETE_VALIDATION_PLUS_REMAINING_DEPLOYMENT_RAW',
        retention='SAVED_A_BELIEF_AND_A_SEEDS_ACROSS_ALL_CHECKPOINTS',
        correction='CURRENT_B_HEAD_MINUS_OWN_SAVED_A_HEAD_WITH_SAME_B_BELIEF_AND_SEEDS',
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
            raise ValueError('Natural warmup cutoff retained; the campaign cannot start')
    return memory, dict(game_summaries=games, raw_tiles=memory.observations_seen,
        environment_counts=dict(environment), direct_counts=delta(template.counts, before),
        memory_counts=dict(memory.counts), memory_events=events, final_memory=memory_state(memory),
        cpu_seconds=process_time()-cpu_started, wall_seconds=perf_counter()-started)


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
                print(json.dumps(dict(event='shadow_deployment_phase_complete', lifecycle=row['lifecycle'],
                    arm=row['arm'], phase=row['phase'],
                    mean_utility=sum(g['utility'] for g in row['game_summaries'])/EVALUATION_GAMES)), flush=True)
        for life in range(parent, 16, 4):
            warmed, costs = warmup(template, life, parent, emit)
            result = run_lifecycle(template, warmed, life, emit, runtime)
            rows.append(dict(result, lifecycle=life, parent=parent, warmup=costs)); stream.flush()
    after_child = resource.getrusage(resource.RUSAGE_CHILDREN)
    return dict(parent=parent, lifecycles=rows, source_setup=setup,
        trace_file=str(trace.resolve()), trace_bytes=trace.stat().st_size,
        cpu_seconds=process_time()-cpu_started, wall_seconds=perf_counter()-started,
        compiler_cpu_seconds=after_child.ru_utime+after_child.ru_stime-before_child.ru_utime-before_child.ru_stime)


def build_accounting(old, lives, parents, cpu, wall):
    def summed(values):
        return dict(sum((Counter(value) for value in values), Counter()))
    kinds = ('environment', 'planning', 'learning')
    inherited = old['accounting']['inherited_costs_per_arm']['FROZEN_H2']
    warm_raw = sum(l['warmup']['raw_tiles'] for l in lives)
    carrier = {kind:summed(l['carrier']['training_counts'][kind] for l in lives) for kind in kinds}
    validation = {a:{kind:summed(l['arms'][a]['phases'][p]['validation']['counts'][kind]
        for l in lives for p,_ in PHASES) for kind in kinds} for a in ARMS}
    deployment = {a:{kind:summed(l['arms'][a]['deployment_counts'][kind] for l in lives)
        for kind in kinds} for a in ARMS}
    online = {a:{kind:summed((carrier[kind], validation[a][kind], deployment[a][kind]))
        for kind in kinds} for a in ARMS}
    physical = {kind:summed([carrier[kind]]+[validation[a][kind] for a in ARMS]+
        [deployment[a][kind] for a in ARMS]) for kind in kinds}
    raw_per_arm = {a:online[a]['environment']['raw_tile_productions'] for a in ARMS}
    economic = {a:inherited['source_training_raw_tiles']+inherited['dynamics_raw_tiles']+warm_raw+raw_per_arm[a]
        for a in ARMS}
    evaluation_components = {a:{part:{kind:summed(l['arms'][a][part][kind] for l in lives)
        for kind in ('environment', 'planning')} for part in ('evaluation_counts',
        'retention_evaluation_counts', 'a_head_on_B_evaluation_counts')} for a in ARMS}
    evaluations = {a:{kind:summed(component[kind] for component in evaluation_components[a].values())
        for kind in ('environment', 'planning')} for a in ARMS}
    fits = [l['shadow']['fit_totals'] for l in lives]
    fit_counts = {part:summed({k:v for k,v in fit[part].items() if not k.endswith('_peak')}
        for fit in fits) for part in ('learning_counts', 'target_counts', 'consolidation_counts', 'setup_counts')}
    peaks = {k:max(fit[part].get(k, 0) for fit in fits)
        for part in ('target_counts', 'consolidation_counts')
        for k in {name for fit in fits for name in fit[part] if name.endswith('_peak')}}
    samples = sum(fit['trained_afterstates'] for fit in fits)
    copies = [copy for l in lives for copy in l['head_copies']]
    shadow_setups = [l['shadow']['head_setup'] for l in lives]
    return dict(physical_online_raw_tiles=physical['environment']['raw_tile_productions'],
        physical_carrier_raw_tiles=carrier['environment']['raw_tile_productions'],
        physical_validation_raw_tiles={a:validation[a]['environment']['raw_tile_productions'] for a in ARMS},
        physical_deployment_raw_tiles={a:deployment[a]['environment']['raw_tile_productions'] for a in ARMS},
        online_raw_tiles_per_arm=raw_per_arm, economic_online_raw_tiles_per_arm=economic,
        inherited_costs_per_arm={a:inherited for a in ARMS},
        physical_warmup_raw_tiles=warm_raw, physical_warmup_games=sum(len(l['warmup']['game_summaries']) for l in lives),
        warmup_environment_counts=summed(l['warmup']['environment_counts'] for l in lives),
        warmup_direct_counts=summed(l['warmup']['direct_counts'] for l in lives),
        warmup_memory_counts=summed(l['warmup']['memory_counts'] for l in lives),
        carrier_counts=carrier, validation_counts_per_arm=validation, deployment_counts_per_arm=deployment,
        physical_online_counts=physical, online_counts_per_arm=online,
        physical_carrier_memory_counts=summed(l['carrier']['phases'][p]['training']['memory_counts']
            for l in lives for p,_ in PHASES),
        physical_validation_games=sum(len(l['arms'][a]['phases'][p]['validation']['game_summaries'])
            for l in lives for a in ARMS for p,_ in PHASES),
        physical_evaluation_games=sum(len(l['arms'][a]['phases'][p]['game_summaries'])+
            (0 if l['arms'][a]['phases'][p]['retention_probe']['shared_with_current'] else
            len(l['arms'][a]['phases'][p]['retention_probe']['game_summaries']))+
            len(l['arms'][a]['phases'][p].get('a_head_on_B', {}).get('game_summaries', []))
            for l in lives for a in ARMS for p,_ in PHASES),
        evaluation_components_per_arm=evaluation_components, evaluation_counts_per_arm=evaluations,
        evaluation_counts={kind:summed(value[kind] for value in evaluations.values())
            for kind in ('environment', 'planning')},
        physical_processed_training_samples=samples,
        economic_processed_training_samples_per_arm={a:0 if a=='FROZEN_H2' else samples for a in ARMS},
        shared_fit_counts=fit_counts, fit_buffer_peaks=peaks,
        carrier_retained_afterstate_steps_peak=max(l['carrier']['retained_afterstate_steps_peak'] for l in lives),
        final_unfitted_carrier_raw_tiles=sum(l['carrier']['final_unfitted_game']['raw_tiles'] for l in lives),
        final_unfitted_deployment_raw_tiles_per_arm={a:sum(l['arms'][a]['final_unfitted_game']['raw_tiles']
            for l in lives) for a in ARMS},
        physical_head_copies=len(copies), head_copy_setup_counts=summed(copy['setup_counts'] for copy in copies),
        shadow_head_setup_counts=summed(setup['setup_counts'] for setup in shadow_setups),
        physical_private_head_weight_bytes_created=sum(copy['private_weight_bytes'] for copy in copies)+
            sum(setup['private_weight_bytes'] for setup in shadow_setups),
        head_copy_cpu_seconds=sum(copy['cpu_seconds'] for copy in copies),
        physical_fit_cpu_seconds=sum(fit['cpu_seconds'] for fit in fits),
        validation_cpu_seconds_per_arm={a:sum(l['arms'][a]['phases'][p]['validation']['cpu_seconds']
            for l in lives for p,_ in PHASES) for a in ARMS},
        deployment_cpu_seconds_per_arm={a:sum(l['arms'][a]['phases'][p]['deployment']['cpu_seconds']
            for l in lives for p,_ in PHASES) for a in ARMS},
        reconstruction_counts=summed(l['carrier']['reconstruction_counts'] for l in lives),
        reconstruction_cpu_seconds=sum(l['carrier']['reconstruction_cpu_seconds'] for l in lives),
        worker_cpu_seconds=sum(p['cpu_seconds'] for p in parents), compiler_cpu_seconds=sum(p['compiler_cpu_seconds'] for p in parents),
        coordinator_cpu_seconds=cpu, wall_seconds=wall, canonical_trace_bytes=sum(p['trace_bytes'] for p in parents),
        development_reference=dict(previous='V292', previous_target_online_raw_tiles=old['accounting']['physical_training_raw_tiles'],
            previous_evaluation_counts=old['accounting']['evaluation_counts'],
            scope='Old target feedback is development evidence, not a training input; old sources reused once.'),
        accounting_scope='Shared carrier and shadow fit physically once. Each learning arm economically pays '
            'shared learning; all arms pay source, warmup, carrier, actual validation and remaining deployment raw. '
            'Frozen is the same sampling schedule control. Only carrier trains memory/values. Scientific probes '
            'are charged separately; shared A-end probe counted once. Buffer peaks are maxima, not sums.')


def run(source_summary, output, finite_test_passes):
    output = Path(output); output.mkdir(parents=True, exist_ok=True)
    if (output/'configuration.json').exists() or (output/'summary.json').exists():
        raise FileExistsError('V293 frozen acquisition or results already exist')
    old = json.loads(Path(source_summary).read_text())
    if not json.loads(Path(source_summary).with_name('audit.json').read_text())['independent_valid']:
        raise ValueError('V293 requires the valid V292 retained evidence')
    settings = configuration(source_summary, finite_test_passes)
    (output/'configuration.json').write_text(json.dumps(settings, indent=2)+'\n')
    started, cpu_started = perf_counter(), process_time(); parents = []
    with ProcessPoolExecutor(max_workers=4) as pool:
        jobs = [pool.submit(_run_parent, source, output) for source in old['source_provenance']['parents']]
        for job in as_completed(jobs):
            parents.append(job.result())
    parents.sort(key=lambda p:p['parent'])
    lives = sorted([l for p in parents for l in p['lifecycles']], key=lambda l:l['lifecycle'])
    analysis = analyze(lives)
    result = dict(schema='acfqp.shadow_deployment.v293', status='EXPERIMENT_COMPLETE', scientific_gate='NOT_A_FORMAL_GATE',
        settings=settings, source_provenance=old['source_provenance'], by_lifecycle=lives,
        parent_receipts=[dict({k:v for k,v in p.items() if k!='lifecycles'}, lifecycle_ids=[l['lifecycle'] for l in p['lifecycles']]) for p in parents],
        summary=analysis, accounting=build_accounting(old, lives, parents, process_time()-cpu_started, perf_counter()-started))
    (output/'summary.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps(dict(event='shadow_deployment_complete', status=result['status'],
        primary=analysis['paired_contrasts']['VALIDATED_H2_minus_FROZEN_H2'])), flush=True)
    return result
