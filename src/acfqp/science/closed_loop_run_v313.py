"""Two actual policy-evaluation/improvement rounds after fresh first adaptation."""
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
import gzip
import json
from pathlib import Path
import resource
from time import perf_counter, process_time

import numpy as np

from .b_mechanism_v299 import sum_counts
from .closed_loop_analysis_v313 import ARMS, DIRECT_ARMS, UPDATING_ARMS, summarize
from .closed_loop_data_v313 import acquire_policy_data
from .closed_loop_versions_v313 import (terminal_weights, snapshot_weights,
    save_version, eligible_samples, select_prefix)
from .confirmed_context_data_v309 import acquire_stage
from .confirmed_context_v309 import ConfirmedContexts
from .controlled_predictive_regime_memory_v115 import SpawnMemory
from .native_linear_win_v311 import LinearWinLeaf, fit_linear, evaluate_linear
from .native_masked_linear_v313 import fit_masked_linear
from .native_policy_stream_v313 import evaluate_direct
from .native_replay_fit_v307 import fit_masked_split
from .native_split_risk_v301 import SplitLeaf, fit_split, evaluate_split
from .native_value_stream_v286 import NativeValueStream
from .natural_model_revision_v281 import load_leaf, MAX_STEPS, QUERY
from .retained_critic_v287 import compact_dataset

TASKS, PROBABILITIES = ('A', 'B'), {'A':.1, 'B':.5}
INITIAL_RAW, ROUND_RAW, LIVES = 131072, 65536, 16


def _save(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')


def evaluation_seed(life, task, episode):
    return 313900000000+life*1000000+(100000 if task=='B' else 0)+episode


def collection_seed(life, task, round_index):
    return 313500000000+life*10000000+TASKS.index(task)*1000000+round_index*100000


def configuration(source_summary):
    return dict(schema='acfqp.closed_loop_freeze.v313',
        protocol=str(Path(__file__).resolve().parents[3]/'specs/CLOSED_LOOP_V313.md'),
        source_summary=str(Path(source_summary).resolve()), lifecycles=list(range(LIVES)),
        parents=4, workers=4, arms=ARMS, tasks=TASKS, true_probabilities=PROBABILITIES,
        rounds=(1,2), initial_raw_per_task=INITIAL_RAW, round_raw_per_collector=ROUND_RAW,
        fit_fraction=.8, alpha=.0025, query=QUERY, max_steps=MAX_STEPS,
        initial_contexts='V309_CONFIRMED_NEW_BANKS_DISTINCT_PRECONDITION',
        initial_heads='NEW_TARGET_FACTS_FIRST_LOCAL_AND_FIRST_LINEAR_FROM_V312_SOURCE',
        context_updates='SUPPLIED_KNOWN_TASK_BANK_FROM_ITS_INITIAL_OBSERVED_ROUTE',
        planning_probability='IMMUTABLE_ACTUAL_BANK_FIRST_FIT_BELIEF',
        collectors=dict(FIXED_LOCAL='FIRST_LOCAL_VERSION_0',
            CLOSED_LOCAL='PREVIOUS_OWN_LOCAL_VERSION', CLOSED_LINEAR='PREVIOUS_OWN_LINEAR_VERSION'),
        shared_cohort='ROUND_1_LOCAL_IDENTICAL_FIRST_ACTOR_SHARED_PHYSICALLY_CHARGED_PER_ARM',
        quota='MINIMUM_ELIGIBLE_NONWINNING_80_PERCENT_FIT_STATES_PER_TASK_ROUND',
        selection='CHRONOLOGICAL_ELIGIBLE_PREFIX_MASK_FULL_FACTUAL_SUFFIXES_NO_OLD_LABEL_REPLAY',
        head_history='SOURCE_RELATIVE_SPARSE_V0_AND_ACTUAL_CHANGED_ADDRESS_V1_V2',
        action_probes='FIRST_EIGHT_AND_LAST_EIGHT_ACTIONS_EACH_NEW_BATCH',
        seed_initial_warmup=313100000000, seed_initial_training=313200000000,
        seed_collection=313500000000, collection_life_stride=10000000,
        collection_task_stride=1000000, collection_round_stride=100000,
        seed_evaluation=313900000000, evaluation_games_per_cell=32,
        bootstrap_draws=20000, bootstrap_seed=31300001,
        primary='CLOSED_LOCAL_minus_FIRST_LOCAL_FINAL_AB',
        feedback='CLOSED_LOCAL_minus_FIXED_LOCAL_FINAL_AB',
        retention='FINAL_LOCAL_MINUS_OWN_FIRST_PER_TASK_CI_LOWER_NONNEGATIVE',
        planning_control='SAME_FIRST_AND_FINAL_LOCAL_LINEAR_HEAD_DIRECT_VS_H2',
        expected_post_raw_physical=LIVES*2*5*ROUND_RAW,
        expected_evaluation_games=LIVES*2*32*13,
        evidence_scope='DEVELOPMENT_16_NEW_TARGET_LIVES_CONDITIONAL_ON_FOUR_FROZEN_V312_VALUE_PARENTS_SHARED_DYNAMICS',
        stop_rule='NO_SEED_ALPHA_QUOTA_OR_CHECKPOINT_TUNING_RETAIN_CUTOFFS_AND_LOSS')


def _new_head(template, kind, runtime, initial=None):
    cpu, started = process_time(), perf_counter()
    leaf = SplitLeaf(template, 'LOCAL_RISK', runtime) if kind=='LOCAL_RISK' else LinearWinLeaf(template, runtime)
    setup = dict(setup_counts=dict(leaf.setup_counts), private_weight_bytes=int(
        leaf.reward_weights.nbytes+terminal_weights(leaf).nbytes))
    if initial is not None:
        np.copyto(leaf.reward_weights, initial.reward_weights)
        np.copyto(terminal_weights(leaf), terminal_weights(initial))
        leaf.updates = initial.updates
        setup['setup_counts'].update(first_parameters_copied=int(leaf.reward_weights.size+terminal_weights(leaf).size),
            first_weight_bytes_copied=setup['private_weight_bytes'])
    setup.update(cpu_seconds=process_time()-cpu, wall_seconds=perf_counter()-started)
    return leaf, setup


def _evaluate(leaf, life, task, belief, runtime, engine, version=None, direct=False):
    updates = leaf.updates
    seeds = [evaluation_seed(life, task, episode) for episode in range(32)]
    p = belief['estimated_p_four']
    if direct:
        result = evaluate_direct(leaf,p,PROBABILITIES[task],seeds,runtime,max_steps=MAX_STEPS)
    elif version is None:
        result = engine.evaluate_games(leaf,p,PROBABILITIES[task],seeds,depth=2,max_steps=MAX_STEPS)
    elif leaf.kind=='LOCAL_RISK':
        result = evaluate_split(leaf,p,PROBABILITIES[task],seeds,runtime,max_steps=MAX_STEPS)
    else:
        result = evaluate_linear(leaf,p,PROBABILITIES[task],seeds,runtime,max_steps=MAX_STEPS)
    if leaf.updates != updates:
        raise ValueError('Evaluation changed head updates')
    return dict(result, estimated_p_four=p, head_version=deepcopy(version),
        planner='DIRECT' if direct else 'H2', static_evaluation_valid=True)


def _run_lifecycle(template, source, life, runtime, output, engine, emit):
    router, initial, heads, versions, contexts, setups = ConfirmedContexts(), {}, {}, {}, {}, {}
    for task in TASKS:
        idx = TASKS.index(task)
        acquired = acquire_stage(template, life,source['parent'],task+'0',router,emit,runtime,
            p_four=PROBABILITIES[task],warmup_seed_base=313100000000+idx*100000,
            training_seed_base=313200000000+idx*100000,raw_budget=INITIAL_RAW)
        route, dataset = acquired['route'], acquired['dataset']
        if not route['created'] or dataset is None:
            emit(dict(kind='CONTEXT_PRECONDITION_FAILED',lifecycle=life,parent=source['parent'],task=task,route=route))
            raise ValueError('Fresh known-task consolidation requires distinct confirmed initial banks')
        contexts[task] = route['context_id']
        memory = SpawnMemory.from_payload(dataset['fit_memory'])
        belief = dict(memory=memory.to_payload(), estimated_p_four=memory.predict())
        heads[task], versions[task], setups[task], fits = {}, {}, {}, {}
        for arm,kind in (('FIRST_LOCAL','LOCAL_RISK'),('FIRST_LINEAR','LINEAR_WIN2')):
            leaf, setups[task][arm] = _new_head(template,kind,runtime)
            fit = fit_split(leaf,dataset,runtime,alpha=.0025) if kind=='LOCAL_RISK' else fit_linear(leaf,dataset,runtime,alpha=.0025)
            leaf.freeze(); heads[task][arm] = leaf; fits[arm] = fit
            versions[task][arm] = save_version(leaf,source,life,contexts[task],arm,0,
                output/'models'/f'life_{life}'/f'bank_{contexts[task]}'/f'{arm}_v0.npz')
        for arm in UPDATING_ARMS:
            first = 'FIRST_LINEAR' if arm=='CLOSED_LINEAR' else 'FIRST_LOCAL'
            leaf,setups[task][arm] = _new_head(template,heads[task][first].kind,runtime,heads[task][first])
            leaf.freeze(); heads[task][arm] = leaf; versions[task][arm] = versions[task][first]
        evaluations = {'SOURCE':{'H2':_evaluate(template,life,task,belief,runtime,engine)}}
        for arm in ('FIRST_LOCAL','FIRST_LINEAR'):
            evaluations[arm] = {'H2':_evaluate(heads[task][arm],life,task,belief,runtime,engine,versions[task][arm])}
        initial[task] = dict(context_route=route,context_id=contexts[task],planning_belief=belief,
            acquisition=acquired['acquisition'],dataset=compact_dataset(dataset),first_fits=fits,
            head_versions={arm:versions[task][arm] for arm in ('FIRST_LOCAL','FIRST_LINEAR')},evaluations=evaluations)
        emit(dict(kind='INITIAL_HEADS',lifecycle=life,parent=source['parent'],task=task,
            head_versions=initial[task]['head_versions']))
        print(json.dumps(dict(event='closed_loop_initial_complete',lifecycle=life,task=task,context=contexts[task])),flush=True)
        del acquired,dataset
    rounds = {}
    for round_index in (1,2):
        rounds[str(round_index)] = {}
        for task in TASKS:
            other = 'B' if task=='A' else 'A'
            inactive_before = {arm:versions[other][arm] for arm in UPDATING_ARMS}
            data, collectors = {}, {}
            actors = ('SHARED_LOCAL','CLOSED_LINEAR') if round_index==1 else UPDATING_ARMS
            for arm in actors:
                actual = 'FIRST_LOCAL' if arm in ('SHARED_LOCAL','FIXED_LOCAL') else arm
                acquired = acquire_policy_data(heads[task][actual],life,source['parent'],arm,
                    initial[task]['planning_belief']['estimated_p_four'],PROBABILITIES[task],
                    collection_seed(life,task,round_index),f'{task}_R{round_index}',emit,runtime,
                    raw_budget=ROUND_RAW,actor_version=versions[task][actual],task=task)
                data[arm] = acquired['dataset']
                collectors[arm] = dict(acquisition=acquired['acquisition'],dataset=compact_dataset(acquired['dataset']),
                    actor_version=deepcopy(versions[task][actual]))
            quota = min(eligible_samples(dataset) for dataset in data.values())
            masks, selections = {}, {}
            for arm,dataset in data.items():
                masks[arm],selections[arm] = select_prefix(dataset,quota)
                collectors[arm]['selection'] = selections[arm]
            arms = {}
            for arm in UPDATING_ARMS:
                key = 'SHARED_LOCAL' if round_index==1 and arm!='CLOSED_LINEAR' else arm
                leaf = heads[task][arm]; before = leaf.updates; old = snapshot_weights(leaf)
                leaf.reward_weights.flags.writeable = True; terminal_weights(leaf).flags.writeable = True
                selected = masks[key][:int(data[key]['fit_step_end'])]
                fit = fit_masked_linear(leaf,data[key],selected,runtime,alpha=.0025) if arm=='CLOSED_LINEAR' else fit_masked_split(leaf,data[key],selected,runtime,alpha=.0025)
                leaf.freeze()
                if leaf.updates-before != quota or fit['trained_afterstates'] != quota:
                    raise ValueError('All collectors must receive the same factual-state quota')
                version = save_version(leaf,source,life,contexts[task],arm,round_index,
                    output/'models'/f'life_{life}'/f'bank_{contexts[task]}'/f'{arm}_v{round_index}.npz',
                    base=versions[task][arm],previous=old)
                del old
                versions[task][arm] = version
                arms[arm] = dict(fit=fit,updates_before=before,updates_after=leaf.updates,head_version=version,
                    evaluations={'H2':_evaluate(leaf,life,task,initial[task]['planning_belief'],runtime,engine,version)})
                emit(dict(kind='CONSOLIDATED_HEAD',lifecycle=life,parent=source['parent'],task=task,
                    round_index=round_index,arm=arm,quota=quota,selection=selections[key],head_version=version,fit=fit))
            inactive_after = {arm:versions[other][arm] for arm in UPDATING_ARMS}
            if inactive_before != inactive_after:
                raise ValueError('Updating one bank replaced inactive-bank history')
            rounds[str(round_index)][task] = dict(quota=quota,collectors=collectors,arms=arms,
                inactive_head_versions_before=inactive_before,inactive_head_versions_after=inactive_after)
            print(json.dumps(dict(event='closed_loop_round_complete',lifecycle=life,task=task,
                round_index=round_index,quota=quota)),flush=True)
            del data,masks,acquired
    final_direct = {task:{arm:_evaluate(heads[task][arm],life,task,initial[task]['planning_belief'],runtime,
        engine,versions[task][arm],direct=True) for arm in DIRECT_ARMS} for task in TASKS}
    private = sum(setup['private_weight_bytes'] for by_arm in setups.values() for setup in by_arm.values())
    return dict(lifecycle=life,parent=source['parent'],initial_context_precondition_met=len(set(contexts.values()))==2,
        initial=initial,rounds=rounds,final_direct=final_direct,head_setups=setups,
        private_head_weight_bytes=private,final_head_versions=versions)


def _child_cpu():
    r=resource.getrusage(resource.RUSAGE_CHILDREN)
    return r.ru_utime+r.ru_stime


def _run_parent(source, output):
    cpu,started,compiler = process_time(),perf_counter(),_child_cpu()
    runtime = output/'runtime'/f"parent_{source['parent']}"; runtime.mkdir(parents=True,exist_ok=True)
    template,setup = load_leaf(source,runtime)
    engine = NativeValueStream(template,313800000000+source['parent'],runtime)
    trace=output/f"parent_{source['parent']}_trace.jsonl.gz"; rows=[]; count=0
    paid_raw=0; failure=None; precondition_failed=cutoff_seen=False
    try:
        with gzip.open(trace,'xt') as stream:
            def emit(row):
                nonlocal count,paid_raw,precondition_failed,cutoff_seen
                stream.write(json.dumps(row,separators=(',',':'),allow_nan=False)+'\n'); count+=1
                paid_raw+=len(row.get('raw_spawns',()))
                precondition_failed |= row['kind']=='CONTEXT_PRECONDITION_FAILED'
                cutoff_seen |= row.get('summary',{}).get('status')=='CUTOFF' or any(
                    g['status']=='CUTOFF' for g in row.get('completed_games',()))
            for life in range(source['parent'],LIVES,4):
                try:
                    row=_run_lifecycle(template,source,life,runtime,output,engine,emit)
                except ValueError as error:
                    if not (precondition_failed or cutoff_seen):
                        raise
                    failure=dict(lifecycle=life,reason='INITIAL_BANK_PRECONDITION_NOT_MET'
                        if precondition_failed else 'CUTOFF_NATURAL_LABEL_UNAVAILABLE',error=str(error))
                    emit(dict(kind='COHORT_HOLD',parent=source['parent'],**failure));break
                rows.append(row);stream.flush()
                _save(output/'lifecycle_receipts'/f'life_{life}.json',row)
    finally:
        engine.close()
    return dict(parent=source['parent'],status='COHORT_HOLD' if failure else 'COMPLETE',
        failure=failure,paid_raw_tiles=paid_raw,lifecycles=rows,source_setup=setup,canonical_rows=count,
        trace_file=str(trace.resolve()),trace_bytes=trace.stat().st_size,
        cpu_seconds=process_time()-cpu,compiler_cpu_seconds=_child_cpu()-compiler,wall_seconds=perf_counter()-started)


def build_accounting(source_costs, lives, parents, cpu, wall):
    initial=[value for life in lives for value in life['initial'].values()]
    batches=[collector for life in lives for tasks in life['rounds'].values() for row in tasks.values() for collector in row['collectors'].values()]
    updates={arm:[row['arms'][arm] for life in lives for tasks in life['rounds'].values() for row in tasks.values()] for arm in UPDATING_ARMS}
    evaluations=[result['H2'] for row in initial for result in row['evaluations'].values()]
    evaluations += [value['evaluations']['H2'] for values in updates.values() for value in values]
    evaluations += [result for life in lives for task in life['final_direct'].values() for result in task.values()]
    initial_raw=sum(row['acquisition']['warmup']['raw_tiles']+row['acquisition']['training']['raw_tiles'] for row in initial)
    post_raw=sum(row['acquisition']['training']['raw_tiles'] for row in batches)
    old_source_raw=source_costs['source_training_raw_tiles']+source_costs['dynamics_raw_tiles']
    economic={arm:old_source_raw+initial_raw+(LIVES*2*2*ROUND_RAW if arm in UPDATING_ARMS else 0) for arm in ARMS}
    all_versions=[v for row in initial for v in row['head_versions'].values()]
    all_versions += [value['head_version'] for values in updates.values() for value in values]
    worker=sum(p['cpu_seconds'] for p in parents); compiler=sum(p['compiler_cpu_seconds'] for p in parents)
    return dict(inherited_source_costs=deepcopy(source_costs),source_physical_training_repeated=False,
        initial_acquisitions=len(initial),post_physical_acquisitions=len(batches),initial_raw_tiles=initial_raw,
        post_raw_tiles=post_raw,new_training_raw_tiles=initial_raw+post_raw,
        economic_training_raw_tiles_per_arm=economic,
        excluded_tail_raw_tiles=sum(row['dataset']['costs']['excluded_tail_raw_tiles'] for row in initial+batches),
        fit_states_per_updating_arm={arm:sum(v['fit']['trained_afterstates'] for v in values) for arm,values in updates.items()},
        fit_counts_per_updating_arm={arm:sum_counts(v['fit']['learning_counts'] for v in values) for arm,values in updates.items()},
        fit_cpu_seconds_per_updating_arm={arm:sum(v['fit']['cpu_seconds'] for v in values) for arm,values in updates.items()},
        initial_fit_cpu_seconds=sum(fit['cpu_seconds'] for row in initial for fit in row['first_fits'].values()),
        post_acquisition_cpu_seconds=sum(row['acquisition']['cpu_seconds'] for row in batches),
        new_evaluation_games=sum(len(e['game_summaries']) for e in evaluations),
        evaluation_cpu_seconds=sum(e['cpu_seconds'] for e in evaluations),
        evaluation_environment_counts=sum_counts(e['counts']['environment'] for e in evaluations),
        version_files=len(all_versions),version_saved_bytes=sum(v['saved_bytes'] for v in all_versions),
        version_scanned_parameters=sum(v['scan_parameters'] for v in all_versions),
        version_copy_parameters=sum(v['copy_parameters'] for v in all_versions),
        version_save_cpu_seconds=sum(v['save_cpu_seconds'] for v in all_versions),
        version_copy_cpu_seconds=sum(v['copy_cpu_seconds'] for v in all_versions),
        private_head_weight_bytes_peak=max(life['private_head_weight_bytes'] for life in lives),
        canonical_trace_bytes=sum(p['trace_bytes'] for p in parents),worker_cpu_seconds=worker,
        compiler_cpu_seconds=compiler,coordinator_cpu_seconds=cpu,wall_seconds=wall,
        new_target_cpu_seconds=worker+compiler+cpu,
        economic_source_and_target_cpu_seconds=source_costs['fresh_source_compute']['full_source_cpu_seconds']+worker+compiler+cpu,
        new_compute_closed=True,
        scope='New target work includes actual source loading, first fits, private branch copies, policy collection, '
            'quota masks, version scans/copies/saves, fits and all H2/DIRECT games. Contained component timings '
            'are not added again. Identical first LOCAL cohorts are acquired once physically and charged per '
            'updating arm. V312 SOURCE is reused physically, with its training acquisition and CPU charged '
            'economically once; original dynamics CPU remains unknown. Same state count does not equalize address writes or CPU.')


def run(source_summary, output):
    cpu,started=process_time(),perf_counter(); output=Path(output).resolve(); output.mkdir(parents=True,exist_ok=True)
    if (output/'configuration.json').exists():
        raise FileExistsError('V313 is already frozen')
    source_path=Path(source_summary).resolve(); source=json.loads(source_path.read_text())
    audit=json.loads((source_path.parent/'audit.json').read_text())
    if source['schema']!='acfqp.fresh_source.v312' or source['status']!='SOURCE_COMPLETE' or not audit['independent_valid']:
        raise ValueError('V313 requires audited frozen V312 SOURCE values')
    settings=configuration(source_path); _save(output/'configuration.json',settings)
    (output/'lifecycle_receipts').mkdir(); parents=[]
    with ProcessPoolExecutor(max_workers=4) as pool:
        jobs=[pool.submit(_run_parent,parent,output) for parent in source['source_provenance']['parents']]
        for job in as_completed(jobs):
            result=job.result();parents.append(result)
            _save(output/f"parent_{result['parent']}_receipt.json",{k:v for k,v in result.items() if k!='lifecycles'})
    parents.sort(key=lambda p:p['parent'])
    lives=sorted((life for parent in parents for life in parent['lifecycles']),key=lambda life:life['lifecycle'])
    failures=[parent['failure'] for parent in parents if parent['failure'] is not None]
    if failures:
        worker=sum(parent['cpu_seconds'] for parent in parents)
        compiler=sum(parent['compiler_cpu_seconds'] for parent in parents)
        coordinator=process_time()-cpu
        result=dict(schema='acfqp.closed_loop.v313',status='COHORT_HOLD',scientific_gate='NOT_A_FORMAL_GATE',
            settings=settings,source_provenance=source['source_provenance'],by_lifecycle=lives,
            completed_lifecycles=[life['lifecycle'] for life in lives],cohort_failures=failures,
            parent_receipts=[{k:v for k,v in p.items() if k!='lifecycles'} for p in parents],
            summary=dict(complete_game_endpoints=False,primary_self_improvement_supported=False,
                closed_loop_mechanism_supported=False,cohort_status='HOLD_INCOMPLETE_COHORT'),
            accounting=dict(inherited_source_costs=source['accounting']['inherited_costs_per_arm']['SOURCE'],
                paid_partial_raw_tiles=sum(p['paid_raw_tiles'] for p in parents),
                worker_cpu_seconds=worker,compiler_cpu_seconds=compiler,coordinator_cpu_seconds=coordinator,
                new_target_cpu_seconds=worker+compiler+coordinator,wall_seconds=perf_counter()-started,
                scope='Every retained partial raw tile and completed worker CPU is paid; incomplete lifecycle '
                    'endpoints block the entire planned cohort. No incomplete sample is omitted or replaced.'))
        _save(output/'summary.json',result)
        print(json.dumps(dict(event='closed_loop_cohort_hold',failures=failures)),flush=True)
        return result
    analysis=summarize(lives)
    result=dict(schema='acfqp.closed_loop.v313',status='EXPERIMENT_COMPLETE',scientific_gate='NOT_A_FORMAL_GATE',
        settings=settings,source_provenance=source['source_provenance'],by_lifecycle=lives,
        parent_receipts=[{k:v for k,v in parent.items() if k!='lifecycles'} for parent in parents],summary=analysis,
        accounting=build_accounting(source['accounting']['inherited_costs_per_arm']['SOURCE'],lives,parents,
            process_time()-cpu,perf_counter()-started))
    _save(output/'summary.json',result)
    print(json.dumps(dict(event='closed_loop_complete',primary=analysis['final_ab_contrasts'][
        'CLOSED_LOCAL_minus_FIRST_LOCAL'])),flush=True)
    return result
