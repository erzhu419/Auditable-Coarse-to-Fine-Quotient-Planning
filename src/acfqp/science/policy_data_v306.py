"""New matched actor cohorts after identical retained A1 reward/risk parameters."""
from concurrent.futures import ProcessPoolExecutor, as_completed
import gzip
import json
from pathlib import Path
import resource
from time import perf_counter, process_time
import numpy as np

from .b_mechanism_v299 import sum_counts
from .history_control_v304 import scientific_identity
from .native_split_risk_v301 import SplitLeaf, fit_split, evaluate_split
from .natural_model_revision_v281 import load_leaf, QUERY, MAX_STEPS
from .policy_actor_data_v306 import acquire_policy_data, RAW_BUDGET, CHUNK_RAW
from .policy_data_analysis_v306 import ARMS, DATASETS, BOOTSTRAP_SEED, INTERVAL_SCOPE, summarize
from .retained_actor_data_v287 import _Replay
from .retained_critic_v287 import compact_dataset


def evaluation_seed(life,episode): return 306900000000+life*1000000+episode


def configuration(source_summary):
    return dict(schema='acfqp.policy_data_freeze.v306',protocol=str(Path(__file__).resolve().parents[3]/'specs/POLICY_DATA_V306.md'),
        source_summary=str(Path(source_summary).resolve()),lifecycles=list(range(64)),parents=4,arms=ARMS,
        actors=DATASETS,retained_stage='A1',true_p_four=.1,raw_budget_per_actor=RAW_BUDGET,chunk_raw=CHUNK_RAW,
        fit_fraction=.8,alpha=.0025,query=QUERY,representation='UNCHANGED_V301_LOCAL_REWARD_AND_SIGMOID_RISK',
        actor_policy='FULL_SPLIT_H2_WITH_FROZEN_REWARD_AND_RISK',actor_initializations=dict(SOURCE_DATA='ORIGINAL_SOURCE_ZERO_RISK',CURRENT_DATA='FROZEN_RETAINED_A1'),
        learner_initialization='IDENTICAL_RETAINED_A1_REWARD_AND_RISK_COPIES',
        planning_probability='FIXED_ORIGINAL_A1_OBSERVED_BELIEF_FOR_BOTH_ACTORS_AND_ALL_EVALUATIONS',
        observations='TWO_NEW_A_COHORTS_FROM_PAIRED_CONTINUOUS_RAW_RNG_STREAMS',
        seed_training=306200000000,seed_evaluation=306900000000,evaluation_games=32,max_steps=MAX_STEPS,
        bootstrap_draws=20000,bootstrap_seed=BOOTSTRAP_SEED,primary='CURRENT_DATA_minus_SOURCE_DATA',
        retention='CURRENT_DATA_minus_A1_FROZEN_CI_LOWER_NONNEGATIVE',
        interval_scope=INTERVAL_SCOPE,
        new_training_raw_tiles=64*2*RAW_BUDGET,new_evaluation_games=64*4*32,
        stop_rule='NO_ACTOR_INITIALIZATION_ALPHA_OR_SEED_TUNING_ON_THESE_NEW_COHORTS')


def retained_a1(receipt,old_lives,reconstruction):
    current=None; replay=None; completed=[]
    with gzip.open(receipt['trace_file'],'rt') as stream:
        for line in stream:
            row=json.loads(line);reconstruction['canonical_rows_read']+=1
            if row['phase']!='A1':
                reconstruction['skipped_rows']+=1;continue
            life=row['lifecycle']
            if current is None:
                acquired=old_lives[life]['stages']['A1']['acquisition']
                expected=dict(lifecycle=life,parent=receipt['parent'],warmup=acquired['warmup'],
                    arms={'FROZEN':{'phases':{'A1':dict(training=acquired['training'],snapshot=acquired['snapshot'])}}})
                replay=_Replay(expected,'A1');current=life
            if current!=life or row['parent']!=receipt['parent']: raise ValueError('Retained A1 lifecycle order changed')
            started=process_time()
            if row['kind']=='WARMUP': replay.warmup(row)
            elif row['kind']=='TRAIN': replay.train(row)
            elif row['kind']=='ACQUISITION_SNAPSHOT': replay.checkpoint(row)
            else: raise ValueError('Unexpected retained A1 acquisition record')
            reconstruction['cpu_seconds']+=process_time()-started
            if row['kind']=='ACQUISITION_SNAPSHOT':
                started=process_time();data=replay.finish();reconstruction['cpu_seconds']+=process_time()-started
                data['costs']['processing_cpu_seconds']=old_lives[life]['stages']['A1']['dataset']['costs']['processing_cpu_seconds']
                if compact_dataset(data)!=old_lives[life]['stages']['A1']['dataset']: raise ValueError('Retained A1 factual dataset changed')
                reconstruction['counts']=sum_counts((reconstruction['counts'],replay.processing));reconstruction['stages']+=1
                completed.append(life);current=None;replay=None;yield life,data
    if current is not None or completed!=receipt['lifecycle_ids']: raise ValueError('Missing retained A1 lifecycle')


def new_head(template,runtime,initial=None):
    started=process_time();leaf=SplitLeaf(template,'LOCAL_RISK',runtime)
    setup=dict(source_weights_shared=False,setup_counts=dict(leaf.setup_counts),setup_seconds=leaf.setup_seconds,
        private_weight_bytes=leaf.reward_weights.nbytes+leaf.risk_weights.nbytes)
    if initial is not None:
        copy_started=perf_counter();np.copyto(leaf.reward_weights,initial.reward_weights);np.copyto(leaf.risk_weights,initial.risk_weights)
        setup['setup_counts'].update(a1_parameters_copied=initial.reward_weights.size+initial.risk_weights.size,
            a1_weight_bytes_copied=initial.reward_weights.nbytes+initial.risk_weights.nbytes)
        setup['setup_seconds']+=perf_counter()-copy_started;leaf.updates=initial.updates
    setup['setup_cpu_seconds']=process_time()-started
    return leaf,setup


def _evaluate(leaf,life,belief,runtime):
    updates=leaf.updates
    result=evaluate_split(leaf,belief['estimated_p_four'],.1,[evaluation_seed(life,e) for e in range(32)],runtime,max_steps=MAX_STEPS)
    if leaf.updates!=updates: raise ValueError('Static evaluation changed learned parameters')
    return dict(result,estimated_p_four=belief['estimated_p_four'],static_evaluation_valid=True)


def _run_lifecycle(template,old,a1_data,runtime,emit):
    life,parent=old['lifecycle'],old['parent'];belief=old['evaluation_beliefs']['A']
    source,source_setup=new_head(template,runtime);source.freeze()
    initial,initial_setup=new_head(template,runtime);initial_fit=fit_split(initial,a1_data,runtime,alpha=.0025);initial.freeze()
    if scientific_identity(initial_fit)!=scientific_identity(old['stages']['A1']['arms']['LOCAL_RISK']['fit']):
        raise ValueError('Initial A1 reward/risk fit did not reproduce V303')
    initial_updates=initial.updates;datasets={};acquisitions={}
    for actor in DATASETS:
        actor_leaf=source if actor=='SOURCE_DATA' else initial
        acquired=acquire_policy_data(actor_leaf,life,parent,actor,belief['estimated_p_four'],emit,runtime)
        datasets[actor]=acquired['dataset'];acquisitions[actor]=acquired['acquisition']
        if actor_leaf.updates!=(0 if actor=='SOURCE_DATA' else initial_updates): raise ValueError('Actor parameters were trained during new acquisition')
        print(json.dumps(dict(event='policy_data_acquisition_complete',lifecycle=life,actor=actor,
            raw=acquisitions[actor]['training']['raw_tiles'],complete_games=len(datasets[actor]['games']))),flush=True)
    streams=[acquisitions[a]['training']['after_stream'] for a in DATASETS]
    if any(s['raw_tiles']!=RAW_BUDGET or s['random_draw_position']!=2*RAW_BUDGET for s in streams) or streams[0]['stream_seed']!=streams[1]['stream_seed']:
        raise ValueError('Actor datasets do not share the same actual raw/RNG budget')
    arms={}
    for arm in ARMS:
        if arm in ('SOURCE','A1_FROZEN'):
            leaf=source if arm=='SOURCE' else initial;setup=source_setup if arm=='SOURCE' else initial_setup
            before=leaf.updates;fit=dict(method='NONE',trained_afterstates=0,learning_counts={},target_counts={},seconds=0.,cpu_seconds=0.)
        else:
            leaf,setup=new_head(template,runtime,initial);before=leaf.updates
            fit=fit_split(leaf,datasets[arm],runtime,alpha=.0025);leaf.freeze()
        if leaf.updates-before!=fit['trained_afterstates']: raise ValueError('New policy-data fit sample/update mismatch')
        evaluated=_evaluate(leaf,life,belief,runtime)
        arms[arm]=dict(fit=fit,head_setup=setup,head_updates_before=before,head_updates_after=leaf.updates,evaluation=evaluated)
        print(json.dumps(dict(event='policy_data_arm_complete',lifecycle=life,arm=arm,
            updates=leaf.updates,utility=sum(g['utility'] for g in evaluated['game_summaries'])/32)),flush=True)
        if arm in DATASETS: del leaf
    if initial.updates!=initial_updates or source.updates!=0 or template.updates!=0: raise ValueError('Frozen initialization/source changed')
    return dict(lifecycle=life,parent=parent,evaluation_belief=belief,initial_fit=initial_fit,
        initial_head_setup=initial_setup,datasets={a:compact_dataset(d) for a,d in datasets.items()},acquisitions=acquisitions,arms=arms)


def _run_parent(source,receipt,old_lives,output):
    started,cpu_started=perf_counter(),process_time();child_before=resource.getrusage(resource.RUSAGE_CHILDREN)
    parent=source['parent'];runtime=Path(output)/'runtime'/f'parent_{parent}';runtime.mkdir(parents=True,exist_ok=True)
    template,setup=load_leaf(source,runtime);reconstruction=dict(canonical_rows_read=0,skipped_rows=0,stages=0,counts={},cpu_seconds=0.)
    trace=Path(output)/f'parent_{parent}_records.jsonl.gz';rows=[]
    with gzip.open(trace,'xt') as stream:
        def emit(row): stream.write(json.dumps(row,separators=(',',':'),allow_nan=False)+'\n')
        for life,data in retained_a1(receipt,old_lives,reconstruction):
            row=_run_lifecycle(template,old_lives[life],data,runtime,emit);rows.append(row);stream.flush()
            (Path(output)/'lifecycle_receipts'/f'life_{life:02d}.json').write_text(json.dumps(row,allow_nan=False)+'\n')
            del data
    child_after=resource.getrusage(resource.RUSAGE_CHILDREN)
    return dict(parent=parent,lifecycles=rows,source_setup=setup,initial_reconstruction=reconstruction,
        trace_file=str(trace.resolve()),trace_bytes=trace.stat().st_size,cpu_seconds=process_time()-cpu_started,
        wall_seconds=perf_counter()-started,compiler_cpu_seconds=child_after.ru_utime+child_after.ru_stime-child_before.ru_utime-child_before.ru_stime)


def build_accounting(old,lives,parents,cpu,wall):
    inherited=old['accounting']['inherited_costs_per_arm']['SOURCE']
    raw=sum(l['stages']['A1']['acquisition']['warmup']['raw_tiles']+l['stages']['A1']['acquisition']['training']['raw_tiles'] for l in old['by_lifecycle'])
    base=inherited['source_training_raw_tiles']+inherited['dynamics_raw_tiles']+raw
    new_raw={a:sum(l['acquisitions'][a]['training']['raw_tiles'] for l in lives) for a in DATASETS}
    acquisitions=[l['acquisitions'][a] for l in lives for a in DATASETS];initial=[l['initial_fit'] for l in lives]
    fits={a:[l['arms'][a]['fit'] for l in lives] for a in ARMS};evals={a:[l['arms'][a]['evaluation'] for l in lives] for a in ARMS}
    result=dict(inherited_a1_raw_tiles=raw,inherited_costs_per_arm={a:inherited for a in ARMS},
        economic_training_raw_tiles_per_arm={a:base+new_raw.get(a,0) for a in ARMS},
        new_training_raw_tiles_by_actor=new_raw,new_training_environment_observations=sum(new_raw.values()),physical_acquisitions=len(acquisitions),
        new_training_environment_counts=sum_counts(a['training']['counts']['environment'] for a in acquisitions),
        new_acquisition_planning_counts=sum_counts(a['training']['counts']['planning'] for a in acquisitions),
        new_acquisition_representation_counts=sum_counts(a['training']['representation_counts'] for a in acquisitions),
        new_acquisition_setup_counts=sum_counts(a['native_setup_counts'] for a in acquisitions),
        new_acquisition_cpu_seconds=sum(a['cpu_seconds'] for a in acquisitions),
        new_reconstruction_counts=sum_counts(a['reconstruction']['counts'] for a in acquisitions),
        new_reconstruction_memory_counts=sum_counts(a['reconstruction']['memory_counts'] for a in acquisitions),
        new_reconstruction_cpu_seconds=sum(a['reconstruction']['cpu_seconds'] for a in acquisitions),
        excluded_tail_raw_tiles_by_actor={a:sum(l['datasets'][a]['costs']['excluded_tail_raw_tiles'] for l in lives) for a in DATASETS},
        initial_replayed_training_samples=sum(f['trained_afterstates'] for f in initial),
        initial_refit_counts=sum_counts(f['learning_counts'] for f in initial),initial_refit_cpu_seconds=sum(f['cpu_seconds'] for f in initial),
        new_processed_training_samples={a:sum(f['trained_afterstates'] for f in fs) for a,fs in fits.items()},
        final_cumulative_updates={a:sum(l['arms'][a]['head_updates_after'] for l in lives) for a in ARMS},
        private_head_weight_bytes_created={a:sum(l['arms'][a]['head_setup']['private_weight_bytes'] for l in lives) for a in ARMS},
        head_setup_counts={a:sum_counts(l['arms'][a]['head_setup']['setup_counts'] for l in lives) for a in ARMS},
        head_setup_cpu_seconds={a:sum(l['arms'][a]['head_setup']['setup_cpu_seconds'] for l in lives) for a in ARMS},
        fit_cpu_seconds={a:sum(f['cpu_seconds'] for f in fs) for a,fs in fits.items()},
        new_evaluation_games=sum(len(e['game_summaries']) for es in evals.values() for e in es),
        evaluation_counts_per_arm={a:{k:sum_counts(e['counts'][k] for e in es) for k in ('environment','planning')} for a,es in evals.items()},
        evaluation_representation_counts={a:sum_counts(e['representation_counts'] for e in es) for a,es in evals.items()},
        evaluation_cpu_seconds_per_arm={a:sum(e['cpu_seconds'] for e in es) for a,es in evals.items()},
        canonical_trace_bytes=sum(p['trace_bytes'] for p in parents),
        initial_reconstruction_cpu_seconds=sum(p['initial_reconstruction']['cpu_seconds'] for p in parents),
        initial_reconstruction_counts=sum_counts(p['initial_reconstruction']['counts'] for p in parents),
        worker_cpu_seconds=sum(p['cpu_seconds'] for p in parents),compiler_cpu_seconds=sum(p['compiler_cpu_seconds'] for p in parents),
        coordinator_cpu_seconds=cpu,wall_seconds=wall,historical_total_compute_closed=False,
        accounting_scope='Retained SOURCE/dynamics and A1 paid once economically per arm; each updating arm pays '
            'its own new cohort. Two physical raw streams per life, frozen actors including full risk calculation, '
            'A1 reconstruction/refit and copies, new reconstruction/fits and all evaluations are actual new work. '
            'A1 head setup is shared with its carrier/reference and counted once. Component CPU is contained '
            'in worker or acquisition CPU, not added twice. Historical V303 total CPU remains unavailable.')
    result['evaluation_counts']={k:sum_counts(v[k] for v in result['evaluation_counts_per_arm'].values()) for k in ('environment','planning')}
    for field,key in [('fit_counts','learning_counts'),('fit_target_counts','target_counts'),('fit_normalization_counts','normalization_counts'),
        ('fit_representation_counts','representation_counts'),('fit_setup_counts','setup_counts')]:
        records={a:[f.get(key,{}) for f in fs] for a,fs in fits.items()}
        result[field]={a:sum_counts({k:v for k,v in row.items() if not k.endswith('_peak')} for row in rs) for a,rs in records.items()}
        result[field+'_buffer_peaks']={a:{k:max(r.get(k,0) for r in rs) for k in {k for r in rs for k in r if k.endswith('_peak')}} for a,rs in records.items()}
    return result


def run(source_summary,output):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    if (output/'configuration.json').exists() or (output/'summary.json').exists(): raise FileExistsError('V306 already frozen or completed')
    path=Path(source_summary).resolve();old=json.loads(path.read_text())
    if not json.loads(path.with_name('audit.json').read_text())['independent_valid']: raise ValueError('Retained V303 A1 requires its passing audit')
    settings=configuration(path);(output/'configuration.json').write_text(json.dumps(settings,indent=2)+'\n');(output/'lifecycle_receipts').mkdir()
    old_lives={l['lifecycle']:l for l in old['by_lifecycle']};receipts={p['parent']:p for p in old['parent_receipts']}
    started,cpu_started=perf_counter(),process_time();parents=[]
    with ProcessPoolExecutor(max_workers=4) as pool:
        jobs=[pool.submit(_run_parent,s,receipts[s['parent']],old_lives,output) for s in old['source_provenance']['parents']]
        for job in as_completed(jobs):
            p=job.result();parents.append(p);(output/f"parent_{p['parent']}_receipt.json").write_text(json.dumps({k:v for k,v in p.items() if k!='lifecycles'},indent=2)+'\n')
    parents.sort(key=lambda p:p['parent']);lives=sorted([l for p in parents for l in p['lifecycles']],key=lambda l:l['lifecycle']);analysis=summarize(lives)
    result=dict(schema='acfqp.policy_data.v306',status='EXPERIMENT_COMPLETE',scientific_gate='NOT_A_FORMAL_GATE',settings=settings,
        source_provenance=old['source_provenance'],by_lifecycle=lives,
        parent_receipts=[dict({k:v for k,v in p.items() if k!='lifecycles'},lifecycle_ids=[l['lifecycle'] for l in p['lifecycles']]) for p in parents],
        summary=analysis,accounting=build_accounting(old,lives,parents,process_time()-cpu_started,perf_counter()-started))
    (output/'summary.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps(dict(event='policy_data_complete',primary=analysis['paired_contrasts']['CURRENT_DATA_minus_SOURCE_DATA'],
        retention=analysis['current_policy_retention_status'])),flush=True)
    return result
