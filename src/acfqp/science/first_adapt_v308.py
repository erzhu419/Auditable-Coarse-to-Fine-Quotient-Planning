"""Fresh first-context adaptation and observational parameter reuse in A/B/A."""
from concurrent.futures import ProcessPoolExecutor, as_completed
import gzip
import json
from pathlib import Path
import resource
from time import perf_counter, process_time

from .b_mechanism_v299 import sum_counts
from .controlled_predictive_online_query_td_v131 import QueryTD
from .controlled_predictive_regime_memory_v115 import SpawnMemory
from .first_adapt_analysis_v308 import ARMS, BOOTSTRAP_SEED, INTERVAL_SCOPE, summarize
from .first_adapt_data_v308 import acquire_stage
from .history_control_v304 import scientific_identity
from .native_episode_consolidation_v290 import fit_consolidated
from .native_split_risk_v301 import SplitLeaf, fit_split, evaluate_split
from .native_value_stream_v286 import NativeValueStream
from .natural_model_revision_v281 import load_leaf, QUERY, MAX_STEPS
from .observed_context_v305 import ObservedContexts
from .retained_critic_v287 import compact_dataset

STAGES = ('A1', 'B', 'A2')
TASKS = {'A1':'A', 'B':'B', 'A2':'A'}
PROBABILITIES = {'A':.1, 'B':.5}
LEARNERS = ('CONTEXT_MC', 'CONTEXT_LOCAL')
RAW_BUDGET = 131072


def evaluation_seed(life, task, episode):
    return 308900000000+(100000 if task=='B' else 0)+life*1000000+episode


def configuration(source_summary):
    return dict(schema='acfqp.first_adapt_freeze.v308',
        protocol=str(Path(__file__).resolve().parents[3]/'specs/FIRST_ADAPT_V308.md'),
        source_summary=str(Path(source_summary).resolve()), source_inputs='ORIGINAL_SOURCE_PROVENANCE_AND_COSTS_ONLY_NO_OLD_TARGET_FACTS',
        lifecycles=list(range(64)), parents=4, arms=ARMS, stages=STAGES, tasks=TASKS, true_probabilities=PROBABILITIES,
        observations='NEW_SOURCE_WARMUP_EACH_STAGE_NEW_SOURCE_COHORT_ONLY_IF_OBSERVED_CONTEXT_CREATED',
        router='UNCHANGED_V305_BETA_1_1_SAME_VERSUS_DISJOINT_LOG_BAYES_FACTOR', log_bayes_factor_threshold=0.,
        context_statistics='CURRENT_STAGE_WARMUP_RAW_SPAWNS_ONLY_COMMITTED_ONCE_BEFORE_TRAINING',
        minimum_detection_raw=256, raw_budget_per_created_context=RAW_BUDGET, fit_fraction=.8, alpha=.0025, query=QUERY,
        context_initialization='ORIGINAL_SOURCE_FOR_EVERY_NEW_BANK',
        adaptation='ONE_FIT_ONLY_ON_FIRST_OBSERVED_CONTEXT_CREATION_REUSE_WITHOUT_REFIT',
        context_baseline='MC_USES_IDENTICAL_ROUTING_BANKS_AND_FACTUAL_FIT_SAMPLES',
        representations=dict(CONTEXT_MC='UNCHANGED_V290_EPISODE_MEAN_MC', CONTEXT_LOCAL='UNCHANGED_V301_LOCAL_REWARD_AND_SIGMOID_RISK'),
        seed_warmup={stage:308100000000+index*100000 for index,stage in enumerate(STAGES)},
        seed_training={stage:308200000000+index*100000 for index,stage in enumerate(STAGES)},
        seed_evaluation=308900000000, evaluation_task_offset=100000, evaluation_games_per_cell=32,
        evaluation_cells=('A1_A', 'B_A', 'B_B', 'A2_A', 'A2_B'), max_steps=MAX_STEPS,
        planning_probability='FIRST_ENCOUNTER_OBSERVED_TASK_FIT_BELIEF_OR_DETECTOR_IF_REUSED_FIXED_ACROSS_ARMS_AND_CHECKPOINTS',
        evaluation_routing='ACTUAL_STAGE_ROUTE_FOR_CURRENT_TASK_READ_ONLY_FIRST_DETECTOR_ROUTING_FOR_RETENTION_PROBES',
        primary='CONTEXT_LOCAL_minus_CONTEXT_MC_FINAL_AB', net_gain='CONTEXT_LOCAL_minus_SOURCE_FINAL_AB',
        retention='ZERO_MARGIN_CI_LOWER_NONNEGATIVE_FOR_A_AFTER_B_B_AFTER_A2_AND_FINAL_A_VS_A1',
        bootstrap_draws=20000, bootstrap_seed=BOOTSTRAP_SEED, interval_scope=INTERVAL_SCOPE,
        new_evaluation_games=30720, old_target_training_raw_reused=0,
        stop_rule='RETAIN_MISROUTES_EXTRA_CONTEXTS_CUTOFFS_AND_NEGATIVE_RESULTS_WITHOUT_ROUTER_OR_FIT_TUNING')


def _initialize(template, runtime):
    heads, setups = {}, {}
    for arm in LEARNERS:
        started = process_time()
        leaf = QueryTD(template.parent, 'PRIOR', runtime) if arm=='CONTEXT_MC' else SplitLeaf(template, 'LOCAL_RISK', runtime)
        heads[arm] = leaf
        setups[arm] = dict(source_weights_shared=False, setup_counts=dict(leaf.setup_counts),
            setup_seconds=leaf.setup_seconds, setup_cpu_seconds=process_time()-started,
            private_weight_bytes=leaf.weights.nbytes+(leaf.risk_weights.nbytes if arm=='CONTEXT_LOCAL' else 0))
    return heads, setups


def _evaluate(leaf, arm, life, task, belief, runtime, engine):
    before, updates = engine.state(), leaf.updates
    seeds = [evaluation_seed(life, task, episode) for episode in range(32)]
    result = (evaluate_split(leaf, belief['estimated_p_four'], PROBABILITIES[task], seeds, runtime, max_steps=MAX_STEPS)
        if arm=='CONTEXT_LOCAL' else engine.evaluate_games(leaf, belief['estimated_p_four'], PROBABILITIES[task],
            seeds, depth=2, max_steps=MAX_STEPS))
    if engine.state()!=before or leaf.updates!=updates:
        raise ValueError('Static V308 evaluation changed parameters or acquisition state')
    return dict(game_summaries=result['game_summaries'], counts=result['counts'],
        representation_counts=result.get('representation_counts', {}), setup_counts=result.get('setup_counts', {}),
        seconds=result['seconds'], cpu_seconds=result['cpu_seconds'],
        estimated_p_four=belief['estimated_p_four'], static_evaluation_valid=True)


def _updates(banks):
    return {arm:{str(context):heads[arm].updates for context,heads in banks.items()} for arm in LEARNERS}


def _none_fit():
    return dict(method='NONE', trained_afterstates=0, learning_counts={}, target_counts={}, seconds=0., cpu_seconds=0.)


def _run_lifecycle(template, life, parent, runtime, engine, emit):
    router = ObservedContexts(); banks, setups, arrays = {}, {}, {}
    beliefs, detectors, stages, evaluations = {}, {}, {}, {}
    for index,stage in enumerate(STAGES):
        acquired = acquire_stage(template, life, parent, stage, router, emit, runtime,
            p_four=PROBABILITIES[TASKS[stage]], warmup_seed_base=308100000000+index*100000,
            training_seed_base=308200000000+index*100000, raw_budget=RAW_BUDGET)
        route, data = acquired['route'], acquired['dataset']; context = route['context_id']
        if route['created']:
            banks[context], setups[context] = _initialize(template, runtime)
            arrays[context] = {arm:(leaf.weights, leaf.risk_weights) if arm=='CONTEXT_LOCAL' else (leaf.weights,)
                for arm,leaf in banks[context].items()}
            if data is None:
                raise ValueError('A new observed context requires its newly acquired cohort')
        elif data is not None:
            raise ValueError('An existing observed context must reuse without a training cohort')
        before = _updates(banks); fits = {}
        for arm in LEARNERS:
            leaf = banks[context][arm]
            current = (leaf.weights, leaf.risk_weights) if arm=='CONTEXT_LOCAL' else (leaf.weights,)
            if any(new is not old for new,old in zip(current, arrays[context][arm])):
                raise ValueError('A persistent bank replaced its learned arrays')
            fits[arm] = (fit_split(leaf, data, runtime, alpha=.0025) if arm=='CONTEXT_LOCAL'
                else fit_consolidated(leaf, data, 'EPISODE_MEAN_MC', runtime, alpha=.0025)) if route['created'] else _none_fit()
            leaf.freeze()
            if leaf.updates-before[arm][str(context)]!=fits[arm]['trained_afterstates']:
                raise ValueError('First adaptation samples do not match bank updates')
        if fits['CONTEXT_MC']['trained_afterstates']!=fits['CONTEXT_LOCAL']['trained_afterstates']:
            raise ValueError('Context MC and LOCAL did not fit the same factual sample inventory')
        after = _updates(banks)
        if any(after[arm][key]!=count for arm,values in before.items() for key,count in values.items() if key!=str(context)):
            raise ValueError('First adaptation updated an unrelated bank')
        task = TASKS[stage]; fit_snapshot = None
        if data is not None:
            memory = SpawnMemory.from_payload(data['fit_memory'])
            fit_snapshot = dict(memory=memory.to_payload(), estimated_p_four=memory.predict())
        if task not in beliefs:
            beliefs[task] = fit_snapshot if fit_snapshot is not None else acquired['detector_belief']
            detectors[task] = acquired['detector_belief']
        eval_routes = {}
        for evaluated_task in beliefs:
            if evaluated_task==task:
                eval_routes[evaluated_task] = dict(kind='ACTUAL_STAGE_ROUTE', context_id=context)
            else:
                prototypes = [dict(bank) for bank in router.banks]
                eval_routes[evaluated_task] = dict(kind='READ_ONLY_FIRST_DETECTOR',
                    **router.select(detectors[evaluated_task]['memory']))
                if prototypes!=router.banks:
                    raise ValueError('A retention probe changed observed context prototypes')
        arms = {}
        for arm in ARMS:
            fitted = _none_fit() if arm=='SOURCE' else fits[arm]
            evaluated = {}
            for evaluated_task,belief in beliefs.items():
                selected = eval_routes[evaluated_task]['context_id']
                leaf = template if arm=='SOURCE' else banks[selected][arm]
                result = _evaluate(leaf, arm, life, evaluated_task, belief, runtime, engine)
                key = (arm, evaluated_task, selected if arm!='SOURCE' else -1, leaf.updates)
                if key in evaluations and scientific_identity(result)!=scientific_identity(evaluations[key]):
                    raise ValueError('An unchanged bank changed fixed-belief paired task outcomes')
                evaluations[key] = result; evaluated[evaluated_task] = result
            arms[arm] = dict(fit=fitted, head_updates_before=0 if arm=='SOURCE' else before[arm][str(context)],
                head_updates_after=0 if arm=='SOURCE' else after[arm][str(context)],
                processed_training_samples=fitted['trained_afterstates'], parameters_retained=True, evaluations=evaluated)
        stages[stage] = dict(detector_belief=acquired['detector_belief'], context_route=route,
            dataset=compact_dataset(data) if data is not None else None, acquisition=acquired['acquisition'],
            fit_snapshot=fit_snapshot, context_updates_before=before, context_updates_after=after,
            evaluation_routes=eval_routes, arms=arms)
        print(json.dumps(dict(event='first_adapt_stage_complete', lifecycle=life, stage=stage,
            context=context, created=route['created'], contexts=len(banks),
            raw=acquired['acquisition']['warmup']['raw_tiles']+(acquired['acquisition']['training']['raw_tiles']
                if acquired['acquisition']['training'] is not None else 0))), flush=True)
        del data, acquired
    if template.updates:
        raise ValueError('Original SOURCE changed during V308')
    bank_rows = [dict(bank, head_updates={arm:banks[bank['context_id']][arm].updates for arm in LEARNERS},
        head_setup=setups[bank['context_id']]) for bank in router.banks]
    return dict(lifecycle=life, parent=parent, evaluation_beliefs=beliefs, task_detectors=detectors, stages=stages,
        context_bank=dict(banks=bank_rows, counts=dict(router.counts), route_cpu_seconds=router.cpu_seconds,
            private_weight_bytes_per_arm={arm:sum(setup[arm]['private_weight_bytes'] for setup in setups.values()) for arm in LEARNERS}))


def _run_parent(source, output):
    started, cpu_started = perf_counter(), process_time(); children = resource.getrusage(resource.RUSAGE_CHILDREN)
    parent = source['parent']; runtime = Path(output)/'runtime'/f'parent_{parent}'
    template, setup = load_leaf(source, runtime)
    engine = NativeValueStream(template, evaluation_seed(parent, 'A', 0), runtime)
    rows = []; trace = Path(output)/f'parent_{parent}_records.jsonl.gz'
    try:
        with gzip.open(trace, 'xt') as stream:
            def emit(row):
                stream.write(json.dumps(row, separators=(',', ':'), allow_nan=False)+'\n')
            for life in range(parent, 64, 4):
                row = _run_lifecycle(template, life, parent, runtime, engine, emit); rows.append(row); stream.flush()
                (Path(output)/'lifecycle_receipts'/f'life_{life:02d}.json').write_text(json.dumps(row, allow_nan=False)+'\n')
    finally:
        engine.close()
    after = resource.getrusage(resource.RUSAGE_CHILDREN)
    return dict(parent=parent, lifecycles=rows, source_setup=setup, trace_file=str(trace.resolve()), trace_bytes=trace.stat().st_size,
        native_evaluation_setup=dict(counts=dict(engine.setup_counts), seconds=engine.setup_seconds),
        cpu_seconds=process_time()-cpu_started, wall_seconds=perf_counter()-started,
        compiler_cpu_seconds=after.ru_utime+after.ru_stime-children.ru_utime-children.ru_stime)


def build_accounting(inherited, lives, parents, cpu, wall):
    rows = [life['stages'][stage] for life in lives for stage in STAGES]
    acquisitions = [row['acquisition'] for row in rows]
    trained = [row for row in rows if row['dataset'] is not None]
    warm = sum(acquisition['warmup']['raw_tiles'] for acquisition in acquisitions)
    actor = sum(row['acquisition']['training']['raw_tiles'] for row in trained)
    economic = inherited['source_training_raw_tiles']+inherited['dynamics_raw_tiles']+warm+actor
    evaluations = {arm:[evaluation for row in rows for evaluation in row['arms'][arm]['evaluations'].values()] for arm in ARMS}
    result = dict(new_training_environment_observations=warm+actor, new_warmup_raw_tiles=warm, new_actor_raw_tiles=actor,
        old_target_training_raw_reused=0, physical_acquisitions=len(trained), physical_detection_stages=len(rows),
        new_raw_tiles_by_stage={stage:sum(life['stages'][stage]['acquisition']['warmup']['raw_tiles']+
            (life['stages'][stage]['acquisition']['training']['raw_tiles'] if life['stages'][stage]['acquisition']['training'] is not None else 0)
            for life in lives) for stage in STAGES},
        economic_training_raw_tiles_per_arm=dict.fromkeys(ARMS, economic), inherited_costs_per_arm={arm:inherited for arm in ARMS},
        new_training_environment_counts=sum_counts([acquisition['warmup']['environment_counts'] for acquisition in acquisitions]+
            [row['acquisition']['training']['counts']['environment'] for row in trained]),
        new_actor_counts={kind:sum_counts(row['acquisition']['training']['counts'][kind] for row in trained)
            for kind in ('environment', 'planning', 'learning')},
        new_warmup_environment_counts=sum_counts(acquisition['warmup']['environment_counts'] for acquisition in acquisitions),
        new_warmup_direct_counts=sum_counts(acquisition['warmup']['direct_counts'] for acquisition in acquisitions),
        new_warmup_memory_counts=sum_counts(acquisition['warmup']['memory_counts'] for acquisition in acquisitions),
        acquisition_cpu_seconds=sum(acquisition['cpu_seconds'] for acquisition in acquisitions),
        acquisition_native_setup_counts=sum_counts(acquisition['native_setup_counts'] for acquisition in acquisitions),
        reconstruction_counts=sum_counts(acquisition['reconstruction']['counts'] for acquisition in acquisitions),
        reconstruction_memory_counts=sum_counts(acquisition['reconstruction']['memory_counts'] for acquisition in acquisitions),
        reconstruction_cpu_seconds=sum(acquisition['reconstruction']['cpu_seconds'] for acquisition in acquisitions),
        excluded_tail_raw_tiles=sum(row['dataset']['costs']['excluded_tail_raw_tiles'] for row in trained),
        processed_training_samples={arm:sum(row['arms'][arm]['processed_training_samples'] for row in rows) for arm in ARMS},
        total_contexts_created=sum(len(life['context_bank']['banks']) for life in lives),
        contexts_per_lifecycle={str(life['lifecycle']):len(life['context_bank']['banks']) for life in lives},
        private_head_weight_bytes_created={arm:sum(life['context_bank']['private_weight_bytes_per_arm'][arm] for life in lives) for arm in LEARNERS},
        peak_private_weight_bytes_per_lifecycle={arm:max(life['context_bank']['private_weight_bytes_per_arm'][arm] for life in lives) for arm in LEARNERS},
        context_router_counts=sum_counts(life['context_bank']['counts'] for life in lives),
        context_router_cpu_seconds=sum(life['context_bank']['route_cpu_seconds'] for life in lives),
        head_setup_counts={arm:sum_counts(bank['head_setup'][arm]['setup_counts'] for life in lives for bank in life['context_bank']['banks']) for arm in LEARNERS},
        head_setup_cpu_seconds={arm:sum(bank['head_setup'][arm]['setup_cpu_seconds'] for life in lives for bank in life['context_bank']['banks']) for arm in LEARNERS},
        fit_cpu_seconds={arm:sum(row['arms'][arm]['fit']['cpu_seconds'] for row in rows) for arm in ARMS},
        new_evaluation_games=sum(len(evaluation['game_summaries']) for values in evaluations.values() for evaluation in values),
        evaluation_counts_per_arm={arm:{kind:sum_counts(evaluation['counts'][kind] for evaluation in values)
            for kind in ('environment', 'planning')} for arm,values in evaluations.items()},
        evaluation_representation_counts={arm:sum_counts(evaluation['representation_counts'] for evaluation in values) for arm,values in evaluations.items()},
        evaluation_cpu_seconds_per_arm={arm:sum(evaluation['cpu_seconds'] for evaluation in values) for arm,values in evaluations.items()},
        canonical_trace_bytes=sum(parent['trace_bytes'] for parent in parents),
        worker_cpu_seconds=sum(parent['cpu_seconds'] for parent in parents), compiler_cpu_seconds=sum(parent['compiler_cpu_seconds'] for parent in parents),
        coordinator_cpu_seconds=cpu, wall_seconds=wall, new_sequence_compute_closed=True,
        accounting_scope='Original SOURCE/dynamics are inherited economically; all new stage detections, actually '
            'created-context acquisitions and unfinished tails are paid once physically and per arm economically. '
            'Both learners share the same routing and newly acquired facts. No old A1/B training facts, replay fits '
            'or previous evaluations enter. Bank setup, fits, routing, reconstruction and all checkpoint evaluations '
            'are actual new work; contained component CPU is not added twice. Matched observations and samples do '
            'not imply equal parameter capacity, writes or total compute. Inherited source seconds are retained '
            'historical timing, not a full newly measured source CPU run.')
    for field,key in (('fit_counts', 'learning_counts'), ('fit_target_counts', 'target_counts'),
        ('fit_normalization_counts', 'normalization_counts'), ('fit_consolidation_counts', 'consolidation_counts'),
        ('fit_representation_counts', 'representation_counts'), ('fit_setup_counts', 'setup_counts')):
        result[field] = {arm:sum_counts({name:value for name,value in row['arms'][arm]['fit'].get(key, {}).items()
            if not name.endswith('_peak')} for row in rows) for arm in ARMS}
    return result


def run(source_summary, output):
    started, cpu_started = perf_counter(), process_time()
    output = Path(output); output.mkdir(parents=True, exist_ok=True)
    if (output/'configuration.json').exists() or (output/'summary.json').exists():
        raise FileExistsError('V308 already frozen or completed')
    path = Path(source_summary).resolve(); previous = json.loads(path.read_text())
    sources = previous['source_provenance']
    source_costs = previous['accounting']['inherited_costs_per_arm']['SOURCE']
    inherited = {key:source_costs[key] for key in ('source_training_raw_tiles', 'source_training_games',
        'source_training_environment_counts', 'source_training_seconds', 'dynamics_raw_tiles', 'dynamics_costs')}
    settings = configuration(path)
    (output/'configuration.json').write_text(json.dumps(settings, indent=2)+'\n'); (output/'lifecycle_receipts').mkdir()
    parents = []
    with ProcessPoolExecutor(max_workers=4) as pool:
        jobs = [pool.submit(_run_parent, source, output) for source in sources['parents']]
        for job in as_completed(jobs):
            parent = job.result(); parents.append(parent)
            (output/f"parent_{parent['parent']}_receipt.json").write_text(json.dumps(
                {key:value for key,value in parent.items() if key!='lifecycles'}, indent=2)+'\n')
    parents.sort(key=lambda parent:parent['parent'])
    lives = sorted((row for parent in parents for row in parent['lifecycles']), key=lambda row:row['lifecycle'])
    analysis = summarize(lives)
    result = dict(schema='acfqp.first_adapt.v308', status='EXPERIMENT_COMPLETE', scientific_gate='NOT_A_FORMAL_GATE',
        settings=settings, source_provenance=sources, by_lifecycle=lives,
        parent_receipts=[dict({key:value for key,value in parent.items() if key!='lifecycles'},
            lifecycle_ids=[row['lifecycle'] for row in parent['lifecycles']]) for parent in parents],
        summary=analysis, accounting=build_accounting(inherited, lives, parents, process_time()-cpu_started, perf_counter()-started))
    (output/'summary.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps(dict(event='first_adapt_complete', primary=analysis['final_ab_contrasts']['CONTEXT_LOCAL_minus_CONTEXT_MC'],
        net_gain=analysis['final_net_gain_supported'], retention=analysis['retention_status'])), flush=True)
    return result
