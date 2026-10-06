"""A fixed actor and identical facts isolate local recurrence from complete MC."""
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
import gzip
import json
from pathlib import Path
from time import perf_counter, process_time

from .b_mechanism_v299 import sum_counts
from .closed_loop_data_v313 import acquire_policy_data
from .closed_loop_run_v313 import _child_cpu, _new_head
from .closed_loop_versions_v313 import eligible_samples, snapshot_weights, save_version
from .confirmed_context_data_v309 import acquire_stage
from .confirmed_context_v309 import ConfirmedContexts
from .controlled_predictive_regime_memory_v115 import SpawnMemory
from .local_target_analysis_v316 import summarize
from .native_local_targets_v314 import fit_local_targets
from .native_split_risk_v301 import fit_split, evaluate_split
from .native_value_stream_v286 import NativeValueStream
from .natural_model_revision_v281 import load_leaf, MAX_STEPS, QUERY
from .retained_critic_v287 import compact_dataset

TASKS, PROBABILITIES = ('A', 'B'), {'A':.1, 'B':.5}
UPDATING_ARMS = ('MC_LOCAL', 'TD_LOCAL')
ARMS = ('SOURCE', 'FIRST_LOCAL') + UPDATING_ARMS
LIVES, INITIAL_RAW, ROUND_RAW = 16, 131072, 65536


def _save(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')


def evaluation_seed(life, task, episode):
    return 316900000000+life*1000000+(100000 if task=='B' else 0)+episode


def collection_seed(life, task, round_index):
    return 316500000000+life*10000000+TASKS.index(task)*1000000+round_index*100000


def configuration(source_summary):
    return dict(schema='acfqp.local_target_freeze.v316',
        protocol=str(Path(__file__).resolve().parents[3]/'specs/LOCAL_TARGETS_V316.md'),
        method_reference=str(Path(__file__).resolve().parents[3]/'specs/LOCAL_TARGETS_V314.md'),
        source_summary=str(Path(source_summary).resolve()), lifecycles=list(range(LIVES)),
        parents=4, workers=4, arms=ARMS, tasks=TASKS, true_probabilities=PROBABILITIES,
        rounds=(1,2), initial_raw_per_task=INITIAL_RAW, round_raw_per_collector=ROUND_RAW,
        fit_fraction=.8, alpha=.0025, query=QUERY, max_steps=MAX_STEPS,
        initial_contexts='V309_CONFIRMED_NEW_BANKS_DISTINCT_PRECONDITION',
        context_updates='SUPPLIED_KNOWN_TASK_BANK_FROM_INITIAL_OBSERVED_ROUTE',
        planning_probability='IMMUTABLE_ACTUAL_BANK_FIRST_FIT_BELIEF',
        collector='FROZEN_FIRST_LOCAL_VERSION_0_ALL_ROUNDS_SHARED_PHYSICALLY',
        quota='ALL_NONWINNING_COMPLETE_FIT_STATES_SHARED_BETWEEN_ARMS',
        mc_target='COMPLETE_FACTUAL_REWARD_SUFFIX_AND_TERMINAL_WIN_LABEL',
        td_target='ACTUAL_NEXT_ACTION_REWARD_AND_AFTERSTATE_BATCH_START_SARSA',
        bootstrap='BATCH_START_FROZEN_OWN_HEAD_V0_THEN_V1',
        update='UNCHANGED_GAME_START_CURRENT_RESIDUAL_AND_OCCURRENCE_NORMALIZATION',
        target_artifact='ALL_FIT_NATIVE_REWARD_WIN_KIND_TARGETS_WITH_ACTUAL_BOOTSTRAP_VERSION',
        head_history_format='acfqp.head_version.v313',
        action_probes='FIRST_EIGHT_AND_LAST_EIGHT_ACTIONS_EACH_NEW_BATCH',
        seed_initial_warmup=316100000000, seed_initial_training=316200000000,
        seed_collection=316500000000, collection_life_stride=10000000,
        collection_task_stride=1000000, collection_round_stride=100000,
        seed_evaluation=316900000000, evaluation_games_per_cell=32,
        bootstrap_draws=20000, bootstrap_seed=31600001,
        primary='TD_LOCAL_minus_FIRST_LOCAL_FINAL_AB',
        target_intervention='TD_LOCAL_minus_MC_LOCAL_FINAL_AB',
        retention='FINAL_TD_MINUS_OWN_FIRST_PER_TASK_CI_LOWER_NONNEGATIVE',
        expected_post_raw_physical=LIVES*2*2*ROUND_RAW,
        expected_evaluation_games=LIVES*2*32*6,
        evidence_scope='FRESH_TARGET_TRAINING_CONFIRMATION_16_LIVES_CONDITIONAL_ON_FOUR_V312_PARENTS_SHARED_DYNAMICS',
        stop_rule='NO_SEED_ALPHA_TARGET_SNAPSHOT_BUDGET_OR_INTERVAL_TUNING_RETAIN_LOSS')


def _evaluate(leaf, life, task, belief, runtime, engine, version=None):
    updates = leaf.updates
    seeds = [evaluation_seed(life,task,episode) for episode in range(32)]
    p = belief['estimated_p_four']
    result = (engine.evaluate_games(leaf,p,PROBABILITIES[task],seeds,depth=2,max_steps=MAX_STEPS)
        if version is None else evaluate_split(leaf,p,PROBABILITIES[task],seeds,runtime,max_steps=MAX_STEPS))
    if leaf.updates != updates:
        raise ValueError('V316 evaluation changed the actual head')
    return dict(result, estimated_p_four=p, head_version=deepcopy(version),
        planner='H2', static_evaluation_valid=True)


def _run_lifecycle(template, source, life, runtime, output, engine, emit):
    router, initial, heads, versions, contexts, setups = ConfirmedContexts(), {}, {}, {}, {}, {}
    for task in TASKS:
        idx = TASKS.index(task)
        acquired = acquire_stage(template,life,source['parent'],task+'0',router,emit,runtime,
            p_four=PROBABILITIES[task],warmup_seed_base=316100000000+idx*100000,
            training_seed_base=316200000000+idx*100000,raw_budget=INITIAL_RAW)
        route, dataset = acquired['route'], acquired['dataset']
        if not route['created'] or dataset is None:
            emit(dict(kind='CONTEXT_PRECONDITION_FAILED',lifecycle=life,parent=source['parent'],task=task,route=route))
            raise ValueError('V316 requires two confirmed initial banks')
        contexts[task] = route['context_id']
        memory = SpawnMemory.from_payload(dataset['fit_memory'])
        belief = dict(memory=memory.to_payload(),estimated_p_four=memory.predict())
        first, setup = _new_head(template,'LOCAL_RISK',runtime)
        fit = fit_split(first,dataset,runtime,alpha=.0025); first.freeze()
        version = save_version(first,source,life,contexts[task],'FIRST_LOCAL',0,
            output/'models'/f'life_{life}'/f'bank_{contexts[task]}'/'FIRST_LOCAL_v0.npz')
        heads[task], versions[task], setups[task] = {'FIRST_LOCAL':first}, {'FIRST_LOCAL':version}, {'FIRST_LOCAL':setup}
        for arm in UPDATING_ARMS:
            leaf, setup = _new_head(template,'LOCAL_RISK',runtime,first)
            leaf.freeze(); heads[task][arm] = leaf; versions[task][arm] = version; setups[task][arm] = setup
        initial[task] = dict(context_route=route,context_id=contexts[task],planning_belief=belief,
            acquisition=acquired['acquisition'],dataset=compact_dataset(dataset),
            first_fits={'FIRST_LOCAL':fit},head_versions={'FIRST_LOCAL':version},
            evaluations={'SOURCE':{'H2':_evaluate(template,life,task,belief,runtime,engine)},
                'FIRST_LOCAL':{'H2':_evaluate(first,life,task,belief,runtime,engine,version)}})
        emit(dict(kind='INITIAL_HEADS',lifecycle=life,parent=source['parent'],task=task,
            head_versions={'FIRST_LOCAL':version}))
        print(json.dumps(dict(event='local_target_initial_complete',lifecycle=life,task=task,context=contexts[task])),flush=True)
        del acquired, dataset
    rounds = {}
    for round_index in (1,2):
        rounds[str(round_index)] = {}
        for task in TASKS:
            other = 'B' if task=='A' else 'A'
            inactive_before = {arm:versions[other][arm] for arm in UPDATING_ARMS}
            acquired = acquire_policy_data(heads[task]['FIRST_LOCAL'],life,source['parent'],'FIXED_FIRST',
                initial[task]['planning_belief']['estimated_p_four'],PROBABILITIES[task],
                collection_seed(life,task,round_index),f'{task}_R{round_index}',emit,runtime,
                raw_budget=ROUND_RAW,actor_version=versions[task]['FIRST_LOCAL'],task=task)
            dataset = acquired['dataset']; quota = eligible_samples(dataset)
            collector = dict(acquisition=acquired['acquisition'],dataset=compact_dataset(dataset),
                actor_version=deepcopy(versions[task]['FIRST_LOCAL']),selection=dict(
                    eligible_samples=quota,selected_samples=quota,selection_rule='ALL_NONWINNING_COMPLETE_FIT_STATES'))
            arms = {}
            for arm in UPDATING_ARMS:
                leaf = heads[task][arm]; before = leaf.updates; old = snapshot_weights(leaf)
                leaf.reward_weights.flags.writeable = True; leaf.risk_weights.flags.writeable = True
                fit = (fit_split(leaf,dataset,runtime,alpha=.0025) if arm=='MC_LOCAL' else
                    fit_local_targets(leaf,dataset,old,runtime,
                        output/'models'/f'life_{life}'/f'bank_{contexts[task]}'/f'TD_LOCAL_v{round_index}_targets.npz',
                        bootstrap_version=versions[task][arm],alpha=.0025))
                leaf.freeze()
                if leaf.updates-before != quota or fit['trained_afterstates'] != quota:
                    raise ValueError('V316 arms must process the same full nonwinning FIT quota')
                version = save_version(leaf,source,life,contexts[task],arm,round_index,
                    output/'models'/f'life_{life}'/f'bank_{contexts[task]}'/f'{arm}_v{round_index}.npz',
                    base=versions[task][arm],previous=old)
                del old
                versions[task][arm] = version
                arms[arm] = dict(fit=fit,updates_before=before,updates_after=leaf.updates,head_version=version,
                    evaluations={'H2':_evaluate(leaf,life,task,initial[task]['planning_belief'],runtime,engine,version)})
                emit(dict(kind='CONSOLIDATED_HEAD',lifecycle=life,parent=source['parent'],task=task,
                    round_index=round_index,arm=arm,quota=quota,head_version=version,fit=fit))
            for count in ('td_updates','reward_table_updates','risk_parameter_updates','table_updates'):
                if arms['MC_LOCAL']['fit']['learning_counts'][count] != arms['TD_LOCAL']['fit']['learning_counts'][count]:
                    raise ValueError('V316 facts must induce equal state and parameter-write counts')
            inactive_after = {arm:versions[other][arm] for arm in UPDATING_ARMS}
            if inactive_before != inactive_after:
                raise ValueError('V316 changed an inactive bank')
            rounds[str(round_index)][task] = dict(quota=quota,collectors={'FIXED_FIRST':collector},arms=arms,
                inactive_head_versions_before=inactive_before,inactive_head_versions_after=inactive_after)
            print(json.dumps(dict(event='local_target_round_complete',lifecycle=life,task=task,
                round_index=round_index,quota=quota)),flush=True)
            del acquired, dataset
    return dict(lifecycle=life,parent=source['parent'],initial_context_precondition_met=len(set(contexts.values()))==2,
        initial=initial,rounds=rounds,head_setups=setups,private_head_weight_bytes=sum(
            setup['private_weight_bytes'] for values in setups.values() for setup in values.values()),
        final_head_versions=versions)


def _run_parent(source, output):
    cpu, started, compiler = process_time(), perf_counter(), _child_cpu()
    runtime = output/'runtime'/f"parent_{source['parent']}"; runtime.mkdir(parents=True,exist_ok=True)
    template, setup = load_leaf(source,runtime)
    engine = NativeValueStream(template,316800000000+source['parent'],runtime)
    trace = output/f"parent_{source['parent']}_trace.jsonl.gz"; rows=[]; count=paid_raw=0
    failure=None; precondition_failed=cutoff_seen=False
    try:
        with gzip.open(trace,'xt') as stream:
            def emit(row):
                nonlocal count, paid_raw, precondition_failed, cutoff_seen
                stream.write(json.dumps(row,separators=(',',':'),allow_nan=False)+'\n'); count+=1
                paid_raw += len(row.get('raw_spawns',()))
                precondition_failed |= row['kind']=='CONTEXT_PRECONDITION_FAILED'
                cutoff_seen |= row.get('summary',{}).get('status')=='CUTOFF' or any(
                    game['status']=='CUTOFF' for game in row.get('completed_games',()))
            for life in range(source['parent'],LIVES,4):
                try:
                    row = _run_lifecycle(template,source,life,runtime,output,engine,emit)
                except ValueError as error:
                    if not (precondition_failed or cutoff_seen): raise
                    failure=dict(lifecycle=life,reason='INITIAL_BANK_PRECONDITION_NOT_MET' if precondition_failed
                        else 'CUTOFF_NATURAL_LABEL_UNAVAILABLE',error=str(error))
                    emit(dict(kind='COHORT_HOLD',parent=source['parent'],**failure)); break
                rows.append(row); stream.flush()
                _save(output/'lifecycle_receipts'/f'life_{life}.json',row)
    finally:
        engine.close()
    return dict(parent=source['parent'],status='COHORT_HOLD' if failure else 'COMPLETE',failure=failure,
        paid_raw_tiles=paid_raw,lifecycles=rows,source_setup=setup,canonical_rows=count,
        trace_file=str(trace.resolve()),trace_bytes=trace.stat().st_size,cpu_seconds=process_time()-cpu,
        compiler_cpu_seconds=_child_cpu()-compiler,wall_seconds=perf_counter()-started)


def build_accounting(source_costs, lives, parents, cpu, wall):
    initial=[value for life in lives for value in life['initial'].values()]
    batches=[row['collectors']['FIXED_FIRST'] for life in lives for tasks in life['rounds'].values() for row in tasks.values()]
    updates={arm:[row['arms'][arm] for life in lives for tasks in life['rounds'].values() for row in tasks.values()] for arm in UPDATING_ARMS}
    evaluations=[value['H2'] for row in initial for value in row['evaluations'].values()]
    evaluations += [value['evaluations']['H2'] for values in updates.values() for value in values]
    versions=[row['head_versions']['FIRST_LOCAL'] for row in initial]
    versions += [value['head_version'] for values in updates.values() for value in values]
    targets=[value['fit']['target_artifact'] for value in updates['TD_LOCAL']]
    initial_raw=sum(row['acquisition']['warmup']['raw_tiles']+row['acquisition']['training']['raw_tiles'] for row in initial)
    post_raw=sum(row['acquisition']['training']['raw_tiles'] for row in batches)
    inherited=source_costs['source_training_raw_tiles']+source_costs['dynamics_raw_tiles']
    worker=sum(row['cpu_seconds'] for row in parents); compiler=sum(row['compiler_cpu_seconds'] for row in parents)
    return dict(inherited_source_costs=deepcopy(source_costs),source_physical_training_repeated=False,
        initial_acquisitions=len(initial),post_physical_acquisitions=len(batches),initial_raw_tiles=initial_raw,
        post_raw_tiles=post_raw,new_training_raw_tiles=initial_raw+post_raw,
        economic_training_raw_tiles_per_arm={arm:inherited+initial_raw+(post_raw if arm in UPDATING_ARMS else 0) for arm in ARMS},
        excluded_tail_raw_tiles=sum(row['dataset']['costs']['excluded_tail_raw_tiles'] for row in initial+batches),
        fit_states_per_updating_arm={arm:sum(v['fit']['trained_afterstates'] for v in values) for arm,values in updates.items()},
        fit_counts_per_updating_arm={arm:sum_counts(v['fit']['learning_counts'] for v in values) for arm,values in updates.items()},
        fit_cpu_seconds_per_updating_arm={arm:sum(v['fit']['cpu_seconds'] for v in values) for arm,values in updates.items()},
        bootstrap_counts=sum_counts(v['fit']['bootstrap_counts'] for v in updates['TD_LOCAL']),
        initial_fit_cpu_seconds=sum(row['first_fits']['FIRST_LOCAL']['cpu_seconds'] for row in initial),
        post_acquisition_cpu_seconds=sum(row['acquisition']['cpu_seconds'] for row in batches),
        new_evaluation_games=sum(len(value['game_summaries']) for value in evaluations),
        evaluation_cpu_seconds=sum(value['cpu_seconds'] for value in evaluations),
        evaluation_environment_counts=sum_counts(value['counts']['environment'] for value in evaluations),
        version_files=len(versions),version_saved_bytes=sum(v['saved_bytes'] for v in versions),
        version_scanned_parameters=sum(v['scan_parameters'] for v in versions),
        version_copy_parameters=sum(v['copy_parameters'] for v in versions),
        version_save_cpu_seconds=sum(v['save_cpu_seconds'] for v in versions),
        version_copy_cpu_seconds=sum(v['copy_cpu_seconds'] for v in versions),
        target_files=len(targets),target_saved_bytes=sum(v['saved_bytes'] for v in targets),
        target_save_cpu_seconds=sum(v['save_cpu_seconds'] for v in targets),
        private_head_weight_bytes_peak=max(life['private_head_weight_bytes'] for life in lives),
        canonical_trace_bytes=sum(row['trace_bytes'] for row in parents),worker_cpu_seconds=worker,
        compiler_cpu_seconds=compiler,coordinator_cpu_seconds=cpu,wall_seconds=wall,
        new_target_cpu_seconds=worker+compiler+cpu,
        economic_source_and_target_cpu_seconds=source_costs['fresh_source_compute']['full_source_cpu_seconds']+worker+compiler+cpu,
        new_compute_closed=True,
        scope='New fixed-policy facts physically acquired once, economically charged to each arm. '
            'Equal fitted states and writes; extra bootstrap reads and target saving paid. All setup, '
            'fit, bootstrap, copy, scan, save, eval work contained in worker CPU, not added twice. '
            'SOURCE reused physically and charged economically once; historical dynamics CPU unknown.')


def run(source_summary, output):
    cpu, started = process_time(), perf_counter(); output=Path(output).resolve(); output.mkdir(parents=True,exist_ok=True)
    if (output/'configuration.json').exists(): raise FileExistsError('V316 is already frozen')
    source_path=Path(source_summary).resolve(); source=json.loads(source_path.read_text())
    audit=json.loads((source_path.parent/'audit.json').read_text())
    if source['status']!='SOURCE_COMPLETE' or not audit['independent_valid']:
        raise ValueError('V316 requires the audited frozen V312 SOURCE')
    settings=configuration(source_path); _save(output/'configuration.json',settings)
    (output/'lifecycle_receipts').mkdir(); parents=[]
    with ProcessPoolExecutor(max_workers=4) as pool:
        for job in as_completed([pool.submit(_run_parent,p,output) for p in source['source_provenance']['parents']]):
            result=job.result(); parents.append(result)
            _save(output/f"parent_{result['parent']}_receipt.json",{k:v for k,v in result.items() if k!='lifecycles'})
    parents.sort(key=lambda row:row['parent'])
    lives=sorted((life for p in parents for life in p['lifecycles']),key=lambda row:row['lifecycle'])
    failures=[p['failure'] for p in parents if p['failure'] is not None]
    if failures:
        worker=sum(p['cpu_seconds'] for p in parents); compiler=sum(p['compiler_cpu_seconds'] for p in parents)
        coordinator=process_time()-cpu
        result=dict(schema='acfqp.local_targets.v316',status='COHORT_HOLD',scientific_gate='NOT_A_FORMAL_GATE',
            settings=settings,source_provenance=source['source_provenance'],by_lifecycle=lives,cohort_failures=failures,
            parent_receipts=[{k:v for k,v in p.items() if k!='lifecycles'} for p in parents],
            summary=dict(complete_game_endpoints=False,primary_self_improvement_supported=False,target_mechanism_supported=False),
            accounting=dict(inherited_source_costs=source['accounting']['inherited_costs_per_arm']['SOURCE'],
                paid_partial_raw_tiles=sum(p['paid_raw_tiles'] for p in parents),worker_cpu_seconds=worker,
                compiler_cpu_seconds=compiler,coordinator_cpu_seconds=coordinator,
                new_target_cpu_seconds=worker+compiler+coordinator,wall_seconds=perf_counter()-started))
    else:
        analysis=summarize(lives)
        result=dict(schema='acfqp.local_targets.v316',status='EXPERIMENT_COMPLETE',scientific_gate='NOT_A_FORMAL_GATE',
            settings=settings,source_provenance=source['source_provenance'],by_lifecycle=lives,
            parent_receipts=[{k:v for k,v in p.items() if k!='lifecycles'} for p in parents],summary=analysis,
            accounting=build_accounting(source['accounting']['inherited_costs_per_arm']['SOURCE'],lives,parents,
                process_time()-cpu,perf_counter()-started))
    _save(output/'summary.json',result)
    print(json.dumps(dict(event='local_targets_complete',status=result['status'])),flush=True)
    return result
