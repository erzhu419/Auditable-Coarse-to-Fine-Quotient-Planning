"""Observed-context persistence on the unchanged retained A/B/A factual sequence."""
from concurrent.futures import ProcessPoolExecutor, as_completed
import gzip
import json
from pathlib import Path
import resource
from time import perf_counter, process_time

from .b_mechanism_v299 import sum_counts
from .context_analysis_v305 import ARMS, BOOTSTRAP_SEED, summarize
from .continual_v303 import _evaluate, evaluation_seed, STAGES, TASKS, EVALUATION_GAMES
from .history_control_v304 import scientific_identity
from .native_split_risk_v301 import SplitLeaf, fit_split, score_split
from .native_value_stream_v286 import NativeValueStream
from .natural_model_revision_v281 import load_leaf, QUERY, MAX_STEPS
from .observed_context_v305 import ObservedContexts
from .retained_actor_data_v287 import _Replay
from .retained_critic_v287 import compact_dataset


def configuration(source_summary,history_summary):
    return dict(schema='acfqp.context_continual_freeze.v305',
        protocol=str(Path(__file__).resolve().parents[3]/'specs/CONTEXT_CONTINUAL_V305.md'),
        source_summary=str(Path(source_summary).resolve()),history_summary=str(Path(history_summary).resolve()),
        lifecycles=list(range(64)),parents=4,arms=ARMS,stages=STAGES,fit_fraction=.8,alpha=.0025,query=QUERY,
        representation='UNCHANGED_V301_LOCAL_PERSISTENT_OBSERVED_CONTEXT_BANKS',
        router='BETA_1_1_SAME_VERSUS_DISJOINT_LOG_BAYES_FACTOR',log_bayes_factor_threshold=0.,
        context_statistics='ALL_OBSERVED_FIT_PREFIX_SPAWNS_FROM_MODULES_AND_PENDING',
        context_update='COMMIT_FIT_PREFIX_ONCE_WITHOUT_TASK_OR_STAGE_LABELS',
        context_initialization='ORIGINAL_SOURCE_REWARD_AND_ZERO_RISK',
        evaluation_routing='MAX_EXISTING_BAYES_FACTOR_WITHOUT_PROTOTYPE_UPDATES',
        planning_probability='UNCHANGED_V303_FIRST_OBSERVED_TASK_BELIEF',
        observations='ALL_RETAINED_V303_A1_B_A2_WITHOUT_NEW_TRAINING_ACQUISITION',
        evaluation_cells=['A1_A','B_A','B_B','A2_A','A2_B'],seed_evaluation=303900000000,
        evaluation_task_offset=100000,evaluation_games_per_cell=EVALUATION_GAMES,max_steps=MAX_STEPS,
        primary='CONTEXT_LOCAL_minus_SHARED_LOCAL_FINAL_AB',bootstrap_draws=20000,bootstrap_seed=BOOTSTRAP_SEED,
        interval_scope='CONDITIONAL_ON_FOUR_FROZEN_PARENTS_AND_RETAINED_V303_HISTORIES',
        new_training_acquisitions=0,new_evaluation_games=10240,reused_evaluation_games=20480,
        stop_rule='NO_ROUTING_TARGET_ALPHA_OR_SEED_TUNING_ON_THIS_RETAINED_SEQUENCE')


def retained_stages(receipt,old_lives,reconstruction):
    """Reconstruct and release one factual stage at a time in original order."""
    current=None; replay=None; completed=[]
    with gzip.open(receipt['trace_file'],'rt') as stream:
        for line in stream:
            row=json.loads(line); reconstruction['canonical_rows_read']+=1
            life,stage=row['lifecycle'],row['phase']
            if current is None:
                old=old_lives[life]['stages'][stage]; acquired=old['acquisition']
                expected=dict(lifecycle=life,parent=receipt['parent'],warmup=acquired['warmup'],
                    arms={'FROZEN':{'phases':{stage:dict(training=acquired['training'],snapshot=acquired['snapshot'])}}})
                replay=_Replay(expected,stage); current=(life,stage)
            if current!=(life,stage) or row['parent']!=receipt['parent']:
                raise ValueError('Retained sequence stage order or parent changed')
            started=process_time()
            if row['kind']=='WARMUP': replay.warmup(row)
            elif row['kind']=='TRAIN': replay.train(row)
            elif row['kind']=='ACQUISITION_SNAPSHOT': replay.checkpoint(row)
            else: raise ValueError('Unexpected retained acquisition record')
            reconstruction['cpu_seconds']+=process_time()-started
            if row['kind']=='ACQUISITION_SNAPSHOT':
                started=process_time(); data=replay.finish()
                reconstruction['cpu_seconds']+=process_time()-started
                reconstruction['counts']=sum_counts((reconstruction['counts'],replay.processing))
                reconstruction['reconstructed_stages']+=1
                data['costs']['processing_cpu_seconds']=old_lives[life]['stages'][stage]['dataset']['costs']['processing_cpu_seconds']
                if compact_dataset(data)!=old_lives[life]['stages'][stage]['dataset']:
                    raise ValueError('Retained complete-game dataset did not reproduce V303')
                completed.append((life,stage)); current=None; replay=None
                yield life,stage,data
    if current is not None or completed!=[(l,s) for l in receipt['lifecycle_ids'] for s in STAGES]:
        raise ValueError('Retained parent is missing an original sequence stage')


def _run_lifecycle(template,old,fresh,stages,runtime,engine):
    life,parent=old['lifecycle'],old['parent']; router=ObservedContexts(); heads={}; setups={}; arrays={}
    seen_beliefs={}; results={}; prior_evaluations={}
    for stage in STAGES:
        replay_life,replay_stage,data=next(stages)
        if (replay_life,replay_stage)!=(life,stage): raise ValueError('Replay stream changed lifecycle stage order')
        original=old['stages'][stage]; route=router.observe(data['fit_memory']); context=route['context_id']
        if route['created']:
            started=process_time(); leaf=SplitLeaf(template,'LOCAL_RISK',runtime); heads[context]=leaf
            arrays[context]=(leaf.weights,leaf.risk_weights)
            setups[context]=dict(source_weights_shared=False,setup_counts=dict(leaf.setup_counts),
                setup_seconds=leaf.setup_seconds,setup_cpu_seconds=process_time()-started,
                private_weight_bytes=leaf.weights.nbytes+leaf.risk_weights.nbytes)
        leaf=heads[context]; current=(leaf.weights,leaf.risk_weights)
        if any(a is not b for a,b in zip(current,arrays[context])): raise ValueError('Context replaced persistent arrays')
        before={str(k):h.updates for k,h in heads.items()}
        for array in current: array.flags.writeable=True
        fit=fit_split(leaf,data,runtime,alpha=.0025); leaf.freeze()
        after={str(k):h.updates for k,h in heads.items()}
        if leaf.updates-before[str(context)]!=fit['trained_afterstates'] or any(
            after[k]!=n for k,n in before.items() if k!=str(context)):
            raise ValueError('Context learning wrote an unrelated parameter history')
        heldout=score_split(leaf,data,runtime)
        task=TASKS[stage]
        if task not in seen_beliefs: seen_beliefs[task]=old['evaluation_beliefs'][task]
        evaluated={}; eval_routes={}
        for task,belief in seen_beliefs.items():
            bank_before=[dict(b) for b in router.banks]; selected=router.select(belief['memory'])
            if router.banks!=bank_before: raise ValueError('Static context selection committed evaluation observations')
            eval_context=selected['context_id']; eval_leaf=heads[eval_context]
            result=_evaluate(eval_leaf,'LOCAL_RISK',life,task,belief,runtime,engine)
            key=(task,eval_context,eval_leaf.updates)
            if key in prior_evaluations and scientific_identity(result)!=scientific_identity(prior_evaluations[key]):
                raise ValueError('An unchanged context changed its paired task outcomes')
            prior_evaluations[key]=result; evaluated[task]=result; eval_routes[task]=selected
        if stage=='A1':
            reference=original['arms']['LOCAL_RISK']
        elif stage=='B' and route['created']:
            reference=dict(fit=fresh['arms']['LOCAL_FRESH_B']['fit_by_stage']['B'],
                heldout=fresh['arms']['LOCAL_FRESH_B']['heldout'],
                evaluations={'B':fresh['arms']['LOCAL_FRESH_B']['evaluation']})
        else: reference=None
        if reference is not None:
            if scientific_identity(fit)!=scientific_identity(reference['fit']) or scientific_identity(heldout)!=scientific_identity(reference['heldout']):
                raise ValueError('Original A1 or fresh B numerical fit/heldout control changed')
            if any(scientific_identity(evaluated[t])!=scientific_identity(r) for t,r in reference['evaluations'].items()):
                raise ValueError('Original A1 or fresh B complete-game control changed')
        arms={a:dict(original['arms']['SOURCE' if a=='SOURCE' else 'LOCAL_RISK'],
            evaluation_is_new=False,heldout_is_new=False) for a in ('SOURCE','SHARED_LOCAL')}
        arms['CONTEXT_LOCAL']=dict(fit=fit,head_updates_before=before[str(context)],head_updates_after=after[str(context)],
            processed_training_samples=fit['trained_afterstates'],parameters_retained=True,
            heldout=heldout,evaluations=evaluated,evaluation_is_new=True,heldout_is_new=True)
        results[stage]=dict(dataset=compact_dataset(data),fit_snapshot=original['fit_snapshot'],
            context_route=route,evaluation_routes=eval_routes,context_updates_before=before,context_updates_after=after,arms=arms)
        print(json.dumps(dict(event='context_stage_complete',lifecycle=life,stage=stage,context=context,
            created=route['created'],contexts=len(heads),utilities={t:sum(g['utility'] for g in e['game_summaries'])/32
                for t,e in evaluated.items()})),flush=True)
        del data
    if template.updates!=0: raise ValueError('Original SOURCE changed')
    banks=[dict(b,head_updates=heads[b['context_id']].updates,head_setup=setups[b['context_id']]) for b in router.banks]
    private=sum(s['private_weight_bytes'] for s in setups.values())
    return dict(lifecycle=life,parent=parent,evaluation_beliefs=old['evaluation_beliefs'],stages=results,
        context_bank=dict(banks=banks,counts=dict(router.counts),route_cpu_seconds=router.cpu_seconds,
            private_weight_bytes=private,peak_private_weight_bytes=private))


def _run_parent(source,receipt,old_lives,fresh_lives,output):
    started,cpu_started=perf_counter(),process_time(); child_before=resource.getrusage(resource.RUSAGE_CHILDREN)
    parent=source['parent']; runtime=Path(output)/'runtime'/f'parent_{parent}'; runtime.mkdir(parents=True,exist_ok=True)
    template,setup=load_leaf(source,runtime); engine=NativeValueStream(template,evaluation_seed(parent,'A',0),runtime)
    reconstruction=dict(canonical_rows_read=0,reconstructed_stages=0,counts={},cpu_seconds=0.); rows=[]
    stages=retained_stages(receipt,old_lives,reconstruction)
    try:
        for life in receipt['lifecycle_ids']:
            row=_run_lifecycle(template,old_lives[life],fresh_lives[life],stages,runtime,engine); rows.append(row)
            (Path(output)/'lifecycle_receipts'/f'life_{life:02d}.json').write_text(json.dumps(row,allow_nan=False)+'\n')
        if next(stages,None) is not None: raise ValueError('Unconsumed factual sequence')
    finally: stages.close(); engine.close()
    child_after=resource.getrusage(resource.RUSAGE_CHILDREN)
    return dict(parent=parent,lifecycles=rows,source_setup=setup,reconstruction=reconstruction,
        native_evaluation_setup=dict(counts=dict(engine.setup_counts),seconds=engine.setup_seconds),
        cpu_seconds=process_time()-cpu_started,wall_seconds=perf_counter()-started,
        compiler_cpu_seconds=child_after.ru_utime+child_after.ru_stime-child_before.ru_utime-child_before.ru_stime)


def build_accounting(old,lives,parents,cpu,wall):
    raw={s:sum(l['stages'][s]['acquisition']['warmup']['raw_tiles']+l['stages'][s]['acquisition']['training']['raw_tiles']
        for l in old['by_lifecycle']) for s in STAGES}
    base=old['accounting']['inherited_costs_per_arm']['SOURCE']; economic=base['source_training_raw_tiles']+base['dynamics_raw_tiles']+sum(raw.values())
    rows=[l['stages'][s] for l in lives for s in STAGES]; new=[r['arms']['CONTEXT_LOCAL'] for r in rows]
    evaluations=[e for a in new for e in a['evaluations'].values()]; banks=[b for l in lives for b in l['context_bank']['banks']]
    result=dict(new_training_environment_observations=0,physical_acquisitions=0,inherited_raw_tiles_by_stage=raw,
        economic_training_raw_tiles_per_arm=dict.fromkeys(ARMS,economic),inherited_costs_per_arm={a:base for a in ARMS},
        historical_sequence_physical_training_raw_tiles_lower_bound=old['recovery']['training_raw_tiles_physical_lower_bound'],
        historical_total_compute_closed=False,new_evaluation_games=sum(len(e['game_summaries']) for e in evaluations),
        reused_evaluation_games=sum(len(e['game_summaries']) for r in rows for a in ('SOURCE','SHARED_LOCAL') for e in r['arms'][a]['evaluations'].values()),
        new_processed_training_samples=dict(SOURCE=0,SHARED_LOCAL=0,CONTEXT_LOCAL=sum(a['processed_training_samples'] for a in new)),
        total_contexts_created=len(banks),contexts_per_lifecycle={str(l['lifecycle']):len(l['context_bank']['banks']) for l in lives},
        context_private_weight_bytes_created=sum(b['head_setup']['private_weight_bytes'] for b in banks),
        peak_context_private_weight_bytes_per_lifecycle=max(l['context_bank']['peak_private_weight_bytes'] for l in lives),
        inherited_shared_private_weight_bytes_per_lifecycle=max(l['head_setup']['LOCAL_RISK']['private_weight_bytes'] for l in old['by_lifecycle']),
        context_head_setup_counts=sum_counts(b['head_setup']['setup_counts'] for b in banks),
        context_router_counts=sum_counts(l['context_bank']['counts'] for l in lives),context_router_cpu_seconds=sum(l['context_bank']['route_cpu_seconds'] for l in lives),
        processing_cpu_seconds=dict(fit=sum(a['fit']['cpu_seconds'] for a in new),heldout=sum(a['heldout']['cpu_seconds'] for a in new),
            head_setup=sum(b['head_setup']['setup_cpu_seconds'] for b in banks)),
        new_evaluation_counts={k:sum_counts(e['counts'][k] for e in evaluations) for k in ('environment','planning')},
        new_evaluation_cpu_seconds=sum(e['cpu_seconds'] for e in evaluations),
        retained_canonical_trace_bytes=old['accounting']['canonical_trace_bytes'],canonical_rows_read=sum(p['reconstruction']['canonical_rows_read'] for p in parents),
        reconstructed_stages=sum(p['reconstruction']['reconstructed_stages'] for p in parents),
        reconstruction_counts=sum_counts(p['reconstruction']['counts'] for p in parents),reconstruction_cpu_seconds=sum(p['reconstruction']['cpu_seconds'] for p in parents),
        worker_cpu_seconds=sum(p['cpu_seconds'] for p in parents),compiler_cpu_seconds=sum(p['compiler_cpu_seconds'] for p in parents),
        coordinator_cpu_seconds=cpu,wall_seconds=wall,
        accounting_scope='All retained source/dynamics and A1/B/A2 observations paid economically per arm. '
            'SOURCE and shared controls are reused, not new physical fits or evaluations. Context copies, routing, '
            'reconstruction, fits and evaluations are actual new work; their CPU is contained in worker CPU. '
            'Context capacity differs from the shared baseline. Historical total CPU remains unavailable.')
    for field,section,key in [('fit_counts','fit','learning_counts'),('fit_target_counts','fit','target_counts'),
        ('fit_normalization_counts','fit','normalization_counts'),('fit_representation_counts','fit','representation_counts'),
        ('fit_setup_counts','fit','setup_counts'),('heldout_prediction_counts','heldout','prediction_counts'),
        ('heldout_target_counts','heldout','target_counts'),('heldout_representation_counts','heldout','representation_counts'),
        ('heldout_setup_counts','heldout','setup_counts')]:
        work=[a[section].get(key,{}) for a in new]
        result[field]=sum_counts({k:v for k,v in r.items() if not k.endswith('_peak')} for r in work)
        result[field+'_buffer_peaks']={k:max(r.get(k,0) for r in work) for k in {k for r in work for k in r if k.endswith('_peak')}}
    result['new_evaluation_representation_counts']=sum_counts(e['representation_counts'] for e in evaluations)
    result['new_evaluation_setup_counts']=sum_counts(e['setup_counts'] for e in evaluations)
    return result


def run(source_summary,history_summary,output):
    output=Path(output); output.mkdir(parents=True,exist_ok=True)
    if (output/'configuration.json').exists() or (output/'summary.json').exists(): raise FileExistsError('V305 already frozen or completed')
    paths=[Path(source_summary).resolve(),Path(history_summary).resolve()]; old,fresh=[json.loads(p.read_text()) for p in paths]
    if not all(json.loads(p.with_name('audit.json').read_text())['independent_valid'] for p in paths):
        raise ValueError('V303 and V304 passing independent audits are required')
    settings=configuration(*paths); (output/'configuration.json').write_text(json.dumps(settings,indent=2)+'\n'); (output/'lifecycle_receipts').mkdir()
    started,cpu_started=perf_counter(),process_time(); parents=[]
    old_lives={l['lifecycle']:l for l in old['by_lifecycle']}; fresh_lives={l['lifecycle']:l for l in fresh['by_lifecycle']}; receipts={p['parent']:p for p in old['parent_receipts']}
    with ProcessPoolExecutor(max_workers=4) as pool:
        jobs=[pool.submit(_run_parent,s,receipts[s['parent']],old_lives,fresh_lives,output) for s in old['source_provenance']['parents']]
        for job in as_completed(jobs):
            p=job.result(); parents.append(p); (output/f"parent_{p['parent']}_receipt.json").write_text(json.dumps({k:v for k,v in p.items() if k!='lifecycles'},indent=2)+'\n')
    parents.sort(key=lambda p:p['parent']); lives=sorted([l for p in parents for l in p['lifecycles']],key=lambda l:l['lifecycle']); analysis=summarize(lives)
    result=dict(schema='acfqp.context_continual.v305',status='EXPERIMENT_COMPLETE',scientific_gate='NOT_A_FORMAL_GATE',settings=settings,
        source_provenance=old['source_provenance'],by_lifecycle=lives,
        parent_receipts=[dict({k:v for k,v in p.items() if k!='lifecycles'},lifecycle_ids=[l['lifecycle'] for l in p['lifecycles']]) for p in parents],
        summary=analysis,accounting=build_accounting(old,lives,parents,process_time()-cpu_started,perf_counter()-started))
    (output/'summary.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps(dict(event='context_continual_complete',primary_repair_supported=analysis['primary_repair_supported'],
        primary=analysis['final_ab_contrasts']['CONTEXT_LOCAL_minus_SHARED_LOCAL'])),flush=True)
    return result
