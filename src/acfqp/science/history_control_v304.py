"""Matched retained-B history intervention with unchanged V303 learners."""
from concurrent.futures import ProcessPoolExecutor, as_completed
import gzip
import json
from pathlib import Path
import resource
from time import perf_counter, process_time

from .b_mechanism_v299 import sum_counts
from .continual_v303 import _evaluate, evaluation_seed, EVALUATION_GAMES
from .controlled_predictive_online_query_td_v131 import QueryTD
from .controlled_predictive_regime_memory_v115 import SpawnMemory
from .history_analysis_v304 import ARMS, BOOTSTRAP_SEED, summarize
from .native_episode_consolidation_v290 import fit_consolidated
from .native_retained_critic_v287 import score_retained
from .native_split_risk_v301 import SplitLeaf, fit_split, score_split
from .native_value_stream_v286 import NativeValueStream
from .natural_model_revision_v281 import load_leaf, QUERY, MAX_STEPS
from .retained_actor_data_v287 import _Replay
from .retained_critic_v287 import compact_dataset


def configuration(source_summary):
    return dict(schema='acfqp.history_control_freeze.v304',
        protocol=str(Path(__file__).resolve().parents[3]/'specs/HISTORY_CONTROL_V304.md'),
        source_summary=str(Path(source_summary).resolve()),lifecycles=list(range(64)),parents=4,
        arms=ARMS,retained_stages=['A1','B'],true_p_four=.5,fit_fraction=.8,alpha=.0025,query=QUERY,
        initialization='ORIGINAL_SOURCE_FOR_ALL_HEADS_WITH_A1_ONLY_IN_HISTORY_ARMS',
        representation='UNCHANGED_V301_LOCAL_AND_V290_MC',
        observations='RETAINED_V303_B_MATCHED_WITH_ADDITIONAL_A1_ONLY_FOR_HISTORY_ARMS',
        model_probability='UNCHANGED_V303_OBSERVED_B_FIT_PREFIX',
        seed_evaluation=303900100000,evaluation_games=EVALUATION_GAMES,max_steps=MAX_STEPS,
        bootstrap_draws=20000,bootstrap_seed=BOOTSTRAP_SEED,
        primary='LOCAL_FRESH_B_minus_LOCAL_AFTER_A1_B',
        interval_scope='CONDITIONAL_ON_FOUR_FROZEN_PARENTS_AND_RETAINED_V303_HISTORIES',
        new_training_acquisitions=0,new_evaluation_games=8192,reused_source_games=2048,
        stop_rule='NO_HISTORY_OR_BUDGET_TUNING_ON_THIS_FIXED_COHORT')


def scientific_identity(value):
    return {k:v for k,v in value.items() if k not in ('seconds','cpu_seconds','setup_counts')}


def retained_lifecycles(receipt, old_lives, reconstruction):
    """Stream one A1/B pair at a time, skipping the unused A2 reconstruction."""
    data, replay, current = {}, None, None
    completed=[]
    with gzip.open(receipt['trace_file'],'rt') as stream:
        for line in stream:
            row=json.loads(line); reconstruction['canonical_rows_read']+=1
            life,stage=row['lifecycle'],row['phase']
            if stage=='A2':
                reconstruction['skipped_A2_rows']+=1
                continue
            if current is None:
                old=old_lives[life]; acquired=old['stages'][stage]['acquisition']
                expected=dict(lifecycle=life,parent=old['parent'],warmup=acquired['warmup'],
                    arms={'FROZEN':{'phases':{stage:dict(training=acquired['training'],snapshot=acquired['snapshot'])}}})
                replay=_Replay(expected,stage); current=(life,stage)
            if current!=(life,stage) or stage not in ('A1','B'):
                raise ValueError('Retained A1/B stage order changed')
            if row['parent']!=receipt['parent'] or row['true_p_four']!=(.1 if stage=='A1' else .5):
                raise ValueError('Retained stage parent or task changed')
            started=process_time()
            if row['kind']=='WARMUP': replay.warmup(row)
            elif row['kind']=='TRAIN': replay.train(row)
            elif row['kind']=='ACQUISITION_SNAPSHOT': replay.checkpoint(row)
            else: raise ValueError('Unexpected retained acquisition record')
            reconstruction['cpu_seconds']+=process_time()-started
            if row['kind']=='ACQUISITION_SNAPSHOT':
                started=process_time(); result=replay.finish()
                reconstruction['cpu_seconds']+=process_time()-started
                reconstruction['reconstruction_counts']=sum_counts((reconstruction['reconstruction_counts'],replay.processing))
                reconstruction['reconstructed_stages']+=1
                # Preserve the paid historical input receipt; today's CPU is separate.
                result['costs']['processing_cpu_seconds']=old_lives[life]['stages'][stage]['dataset']['costs']['processing_cpu_seconds']
                if compact_dataset(result)!=old_lives[life]['stages'][stage]['dataset']:
                    raise ValueError('Retained factual dataset did not reproduce V303')
                data[stage]=result; current=None; replay=None
                if stage=='B':
                    if set(data)!= {'A1','B'}: raise ValueError('B replay has no paired A1 history')
                    completed.append(life); pair=data; data={}
                    yield life,pair
    if current is not None or data or completed!=receipt['lifecycle_ids']:
        raise ValueError('Retained parent did not complete exactly its A1/B lifecycles')


def _run_lifecycle(template, datasets, old, runtime, engine):
    life,parent=old['lifecycle'],old['parent']; belief=old['evaluation_beliefs']['B']
    memory=SpawnMemory.from_payload(datasets['B']['fit_memory']); p=memory.predict()
    if dict(memory=memory.to_payload(),estimated_p_four=p)!=belief:
        raise ValueError('Retained B evaluation belief changed')
    arms={}
    for arm in ARMS:
        local=arm.startswith('LOCAL'); inherited='AFTER_A1' in arm
        if arm=='SOURCE':
            prior=old['stages']['B']['arms']['SOURCE']
            arms[arm]=dict(fit_by_stage={},head_updates_by_stage={},head_updates=0,
                head_setup=dict(source_weights_shared=True,setup_counts={},setup_seconds=0.,setup_cpu_seconds=0.,private_weight_bytes=0),
                heldout=prior['heldout'],evaluation=prior['evaluations']['B'],
                evaluation_is_new=False,heldout_is_new=False)
            continue
        started=process_time()
        leaf=SplitLeaf(template,'LOCAL_RISK',runtime) if local else QueryTD(template.parent,'PRIOR',runtime)
        arrays=(leaf.weights,leaf.risk_weights) if local else (leaf.weights,)
        setup=dict(source_weights_shared=False,setup_counts=dict(leaf.setup_counts),setup_seconds=leaf.setup_seconds,
            setup_cpu_seconds=process_time()-started,private_weight_bytes=sum(a.nbytes for a in arrays))
        fits,histories={},{}
        for stage in (('A1','B') if inherited else ('B',)):
            for array in arrays: array.flags.writeable=True
            before=leaf.updates
            fit=(fit_split(leaf,datasets[stage],runtime,alpha=.0025) if local
                else fit_consolidated(leaf,datasets[stage],'EPISODE_MEAN_MC',runtime,alpha=.0025))
            if leaf.updates-before!=fit['trained_afterstates']:
                raise ValueError('Fitted history does not match parameter updates')
            if inherited:
                prior=old['stages'][stage]['arms']['LOCAL_RISK' if local else 'MC']['fit']
                if scientific_identity(fit)!=scientific_identity(prior):
                    raise ValueError('Inherited fit did not reproduce V303')
            fits[stage]=fit; histories[stage]=dict(before=before,after=leaf.updates)
            leaf.freeze()
        heldout=score_split(leaf,datasets['B'],runtime) if local else score_retained(leaf,datasets['B'],runtime)
        evaluated=_evaluate(leaf,'LOCAL_RISK' if local else 'MC',life,'B',belief,runtime,engine)
        if inherited:
            prior=old['stages']['B']['arms']['LOCAL_RISK' if local else 'MC']
            if scientific_identity(heldout)!=scientific_identity(prior['heldout']):
                raise ValueError('Inherited heldout predictions did not reproduce V303')
            if scientific_identity(evaluated)!=scientific_identity(prior['evaluations']['B']):
                raise ValueError('Inherited complete-game outcomes did not reproduce V303')
        arms[arm]=dict(fit_by_stage=fits,head_updates_by_stage=histories,head_updates=leaf.updates,
            head_setup=setup,heldout=heldout,evaluation=evaluated,evaluation_is_new=True,heldout_is_new=True)
        print(json.dumps(dict(event='history_control_arm_complete',lifecycle=life,arm=arm,
            updates=leaf.updates,utility=sum(g['utility'] for g in evaluated['game_summaries'])/32)),flush=True)
        del leaf,arrays
    if template.updates!=0: raise ValueError('Original SOURCE baseline changed')
    for prefix in ('MC','LOCAL'):
        fresh,history=arms[prefix+'_FRESH_B']['fit_by_stage']['B'],arms[prefix+'_AFTER_A1_B']['fit_by_stage']['B']
        keys=('trained_afterstates','target_counts','normalization_counts' if prefix=='LOCAL' else 'consolidation_counts')
        if any(fresh[k]!=history[k] for k in keys): raise ValueError('B factual targets or address work are not matched')
    return dict(lifecycle=life,parent=parent,datasets={s:compact_dataset(d) for s,d in datasets.items()},
        evaluation_belief=belief,arms=arms)


def _run_parent(source, receipt, old_lives, output):
    started,cpu_started=perf_counter(),process_time(); child_before=resource.getrusage(resource.RUSAGE_CHILDREN)
    parent=source['parent']; runtime=Path(output)/'runtime'/f'parent_{parent}'; runtime.mkdir(parents=True,exist_ok=True)
    template,setup=load_leaf(source,runtime); engine=NativeValueStream(template,evaluation_seed(parent,'B',0),runtime)
    reconstruction=dict(canonical_rows_read=0,skipped_A2_rows=0,reconstructed_stages=0,reconstruction_counts={},cpu_seconds=0.)
    rows=[]
    try:
        for life,data in retained_lifecycles(receipt,old_lives,reconstruction):
            row=_run_lifecycle(template,data,old_lives[life],runtime,engine); rows.append(row)
            (Path(output)/'lifecycle_receipts'/f'life_{life:02d}.json').write_text(json.dumps(row,allow_nan=False)+'\n')
            del data
    finally: engine.close()
    child_after=resource.getrusage(resource.RUSAGE_CHILDREN)
    return dict(parent=parent,lifecycles=rows,source_setup=setup,reconstruction=reconstruction,
        native_evaluation_setup=dict(counts=dict(engine.setup_counts),seconds=engine.setup_seconds),
        cpu_seconds=process_time()-cpu_started,wall_seconds=perf_counter()-started,
        compiler_cpu_seconds=child_after.ru_utime+child_after.ru_stime-child_before.ru_utime-child_before.ru_stime)


def build_accounting(old,lives,parents,cpu,wall):
    stages=('A1','B'); raw={s:sum(l['stages'][s]['acquisition']['warmup']['raw_tiles']+
        l['stages'][s]['acquisition']['training']['raw_tiles'] for l in old['by_lifecycle']) for s in stages}
    base=old['accounting']['inherited_costs_per_arm']['SOURCE']; original=base['source_training_raw_tiles']+base['dynamics_raw_tiles']
    fits={a:[f for l in lives for f in l['arms'][a]['fit_by_stage'].values()] for a in ARMS}
    evals={a:[l['arms'][a]['evaluation'] for l in lives if l['arms'][a]['evaluation_is_new']] for a in ARMS}
    held={a:[l['arms'][a]['heldout'] for l in lives if l['arms'][a]['heldout_is_new']] for a in ARMS}
    result=dict(new_training_environment_observations=0,physical_acquisitions=0,
        inherited_raw_tiles_by_stage=raw,inherited_costs_per_arm={a:base for a in ARMS},
        economic_training_raw_tiles_per_arm={a:original+raw['B']+
            (raw['A1'] if 'AFTER_A1' in a else 0) for a in ARMS},
        historical_sequence_physical_training_raw_tiles_lower_bound=old['recovery']['training_raw_tiles_physical_lower_bound'],
        historical_total_compute_closed=False,
        processed_training_samples={a:sum(f['trained_afterstates'] for f in values) for a,values in fits.items()},
        final_cumulative_updates={a:sum(l['arms'][a]['head_updates'] for l in lives) for a in ARMS},
        private_head_weight_bytes_created={a:sum(l['arms'][a]['head_setup']['private_weight_bytes'] for l in lives) for a in ARMS},
        head_setup_counts={a:sum_counts(l['arms'][a]['head_setup']['setup_counts'] for l in lives) for a in ARMS},
        processing_cpu_seconds_per_arm={a:dict(fit=sum(f['cpu_seconds'] for f in fits[a]),
            heldout=sum(h['cpu_seconds'] for h in held[a]),head_setup=sum(l['arms'][a]['head_setup']['setup_cpu_seconds'] for l in lives)) for a in ARMS},
        new_evaluation_games=sum(len(e['game_summaries']) for values in evals.values() for e in values),
        reused_evaluation_games=sum(len(l['arms']['SOURCE']['evaluation']['game_summaries']) for l in lives),
        evaluation_counts_per_arm={a:{k:sum_counts(e['counts'][k] for e in values) for k in ('environment','planning')} for a,values in evals.items()},
        evaluation_cpu_seconds_per_arm={a:sum(e['cpu_seconds'] for e in values) for a,values in evals.items()},
        retained_canonical_trace_bytes=old['accounting']['canonical_trace_bytes'],
        canonical_rows_read=sum(p['reconstruction']['canonical_rows_read'] for p in parents),
        reconstructed_stages=sum(p['reconstruction']['reconstructed_stages'] for p in parents),
        reconstruction_cpu_seconds=sum(p['reconstruction']['cpu_seconds'] for p in parents),
        reconstruction_counts=sum_counts(p['reconstruction']['reconstruction_counts'] for p in parents),
        worker_cpu_seconds=sum(p['cpu_seconds'] for p in parents),compiler_cpu_seconds=sum(p['compiler_cpu_seconds'] for p in parents),
        coordinator_cpu_seconds=cpu,wall_seconds=wall,
        accounting_scope='Same retained B observations; inherited arms additionally pay A1 history. No new training raw. '
            'SOURCE outcomes reused; all four learned evaluations are new physical work. New component CPU is contained '
            'in worker CPU. Historical interrupted sequence CPU remains unavailable.')
    result['evaluation_counts']={k:sum_counts(row[k] for row in result['evaluation_counts_per_arm'].values()) for k in ('environment','planning')}
    for field,values,key in [('fit_counts',fits,'learning_counts'),('fit_target_counts',fits,'target_counts'),
        ('fit_normalization_counts',fits,'normalization_counts'),('fit_consolidation_counts',fits,'consolidation_counts'),
        ('fit_representation_counts',fits,'representation_counts'),('heldout_prediction_counts',held,'prediction_counts'),
        ('heldout_target_counts',held,'target_counts'),('heldout_representation_counts',held,'representation_counts'),
        ('evaluation_representation_counts',evals,'representation_counts'),('evaluation_setup_counts',evals,'setup_counts')]:
        records={a:[v.get(key,{}) for v in items] for a,items in values.items()}
        result[field]={a:sum_counts({k:v for k,v in row.items() if not k.endswith('_peak')} for row in items) for a,items in records.items()}
        result[field+'_buffer_peaks']={a:{k:max(row.get(k,0) for row in items) for k in
            {k for row in items for k in row if k.endswith('_peak')}} for a,items in records.items()}
    return result


def run(source_summary, output):
    output=Path(output); output.mkdir(parents=True,exist_ok=True)
    if (output/'configuration.json').exists() or (output/'summary.json').exists(): raise FileExistsError('V304 already frozen or completed')
    source_summary=Path(source_summary).resolve(); old=json.loads(source_summary.read_text())
    if not json.loads(source_summary.with_name('audit.json').read_text())['independent_valid']:
        raise ValueError('V303 retained evidence requires its passing independent audit')
    settings=configuration(source_summary); (output/'configuration.json').write_text(json.dumps(settings,indent=2)+'\n')
    (output/'lifecycle_receipts').mkdir()
    started,cpu_started=perf_counter(),process_time(); parents=[]
    old_lives={l['lifecycle']:l for l in old['by_lifecycle']}; receipts={p['parent']:p for p in old['parent_receipts']}
    with ProcessPoolExecutor(max_workers=4) as pool:
        jobs=[pool.submit(_run_parent,s,receipts[s['parent']],old_lives,output) for s in old['source_provenance']['parents']]
        for job in as_completed(jobs):
            p=job.result(); parents.append(p)
            (output/f"parent_{p['parent']}_receipt.json").write_text(json.dumps({k:v for k,v in p.items() if k!='lifecycles'},indent=2)+'\n')
    parents.sort(key=lambda p:p['parent']); lives=sorted([l for p in parents for l in p['lifecycles']],key=lambda l:l['lifecycle'])
    analysis=summarize(lives)
    result=dict(schema='acfqp.history_control.v304',status='EXPERIMENT_COMPLETE',scientific_gate='NOT_A_FORMAL_GATE',
        settings=settings,source_provenance=old['source_provenance'],by_lifecycle=lives,
        parent_receipts=[dict({k:v for k,v in p.items() if k!='lifecycles'},lifecycle_ids=[l['lifecycle'] for l in p['lifecycles']]) for p in parents],
        summary=analysis,accounting=build_accounting(old,lives,parents,process_time()-cpu_started,perf_counter()-started))
    (output/'summary.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps(dict(event='history_control_complete',history_diagnosis=analysis['history_diagnosis'],
        primary=analysis['paired_contrasts']['LOCAL_FRESH_B_minus_LOCAL_AFTER_A1_B'])),flush=True)
    return result
