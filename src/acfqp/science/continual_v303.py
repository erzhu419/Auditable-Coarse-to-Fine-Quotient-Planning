"""Frozen A/B/A sequence with unchanged kernels and persistent critic arrays."""
from concurrent.futures import ProcessPoolExecutor, as_completed
import gzip
import json
from pathlib import Path
import resource
from time import perf_counter, process_time

from .b_mechanism_v299 import sum_counts
from .controlled_predictive_online_query_td_v131 import QueryTD
from .controlled_predictive_regime_memory_v115 import SpawnMemory
from .independent_actor_data_v291 import acquire_dataset, RAW_BUDGET
from .continual_analysis_v303 import ARMS, BOOTSTRAP_SEED, summarize
from .native_episode_consolidation_v290 import fit_consolidated
from .native_retained_critic_v287 import score_retained
from .native_split_risk_v301 import SplitLeaf, fit_split, score_split, evaluate_split
from .native_value_stream_v286 import NativeValueStream
from .natural_model_revision_v281 import load_leaf, QUERY, MAX_STEPS
from .retained_critic_v287 import compact_dataset

STAGES=('A1','B','A2')
TASKS={'A1':'A','B':'B','A2':'A'}
PROBABILITIES={'A':.1,'B':.5}
EVALUATION_GAMES=32


def warmup_seed_base(stage):
    return 303100000000+STAGES.index(stage)*100000


def training_seed_base(stage):
    return 303200000000+STAGES.index(stage)*100000


def evaluation_seed(life,task,episode):
    return 303900000000+(100000 if task=='B' else 0)+life*1000000+episode


def configuration(source_summary):
    return dict(schema='acfqp.continual_freeze.v303',
        protocol=str(Path(__file__).resolve().parents[3]/'specs/CONTINUAL_V303.md'),
        source_summary=str(Path(source_summary).resolve()),lifecycles=list(range(64)),parents=4,
        arms=ARMS,stages=STAGES,tasks=TASKS,true_probabilities=PROBABILITIES,
        canonical_acquisition_arm='FROZEN',source_initialization='ORIGINAL_SOURCE_WITHOUT_A_STAGE_UPDATES',
        observations='THREE_NEW_SOURCE_CARRIER_COHORTS_WITH_RETAINED_LEARNER_PARAMETERS',
        raw_budget_per_stage=RAW_BUDGET,fit_fraction=.8,alpha=.0025,query=QUERY,
        representation='UNCHANGED_V301_LOCAL_REWARD_AND_SIGMOID_TERMINAL_NTUPLES',
        reward_initialization='ORIGINAL_SOURCE_UTILITY_TABLE_ONCE',risk_initialization='ZERO_LOGITS_ONCE',
        combination='REWARD_PLUS_8_TIMES_PROBABILITY_MINUS_HALF',
        reward_target='FACTUAL_FUTURE_REWARD_EXCLUDING_CURRENT_REWARD_AND_TERMINAL_BONUS',
        risk_target='COMPLETE_FIT_GAME_WON_LABEL',
        consolidation='GAME_START_PREDICTIONS_THEN_PER_FEATURE_MASS_NORMALIZED_MEAN',
        model_probability='FIRST_ENCOUNTER_OBSERVED_FIT_PREFIX_FIXED_BY_TASK',
        seed_warmup={stage:warmup_seed_base(stage) for stage in STAGES},
        seed_training={stage:training_seed_base(stage) for stage in STAGES},
        seed_evaluation=303900000000,evaluation_task_offset=100000,
        evaluation_games_per_cell=EVALUATION_GAMES,evaluation_cells=('A1_A','B_A','B_B','A2_A','A2_B'),
        max_steps=MAX_STEPS,bootstrap_draws=20000,bootstrap_seed=BOOTSTRAP_SEED,
        primary='LOCAL_RISK_minus_SOURCE_FINAL_AB_COMPLETE_GAME_UTILITY',
        interval_scope='CONDITIONAL_ON_FOUR_FROZEN_PARENTS',
        evaluation='STATIC_TASK_BELIEF_AND_PAIRED_TASK_SEEDS_ACROSS_CHECKPOINTS',
        stop_rule='RETAIN_ALL_NEGATIVE_RETENTION_RESULTS_WITHOUT_SEQUENCE_TUNING')


def initialize_heads(template,runtime):
    heads={'SOURCE':template}; setups={}
    for arm in ARMS:
        started=process_time()
        if arm=='SOURCE':
            setups[arm]=dict(source_weights_shared=True,setup_counts={},setup_seconds=0.,
                setup_cpu_seconds=0.,private_weight_bytes=0)
            continue
        leaf=(QueryTD(template.parent,'PRIOR',runtime) if arm=='MC'
            else SplitLeaf(template,'LOCAL_RISK',runtime))
        heads[arm]=leaf
        setups[arm]=dict(source_weights_shared=False,setup_counts=dict(leaf.setup_counts),
            setup_seconds=leaf.setup_seconds,setup_cpu_seconds=process_time()-started,
            private_weight_bytes=leaf.weights.nbytes+(leaf.risk_weights.nbytes if arm=='LOCAL_RISK' else 0))
    return heads,setups


def _evaluate(leaf,arm,life,task,belief,runtime,engine):
    before,updates=engine.state(),leaf.updates
    p=belief['estimated_p_four']; seeds=[evaluation_seed(life,task,e) for e in range(EVALUATION_GAMES)]
    result=(evaluate_split(leaf,p,PROBABILITIES[task],seeds,runtime,max_steps=MAX_STEPS) if arm=='LOCAL_RISK'
        else engine.evaluate_games(leaf,p,PROBABILITIES[task],seeds,depth=2,max_steps=MAX_STEPS))
    if engine.state()!=before or leaf.updates!=updates:
        raise ValueError('Static checkpoint evaluation changed acquisition or learning state')
    return dict(game_summaries=result['game_summaries'],counts=result['counts'],
        representation_counts=result.get('representation_counts',{}),setup_counts=result.get('setup_counts',{}),
        seconds=result['seconds'],cpu_seconds=result['cpu_seconds'],estimated_p_four=p,static_evaluation_valid=True)


def _run_lifecycle(template,life,parent,runtime,engine,emit):
    heads,setups=initialize_heads(template,runtime)
    buffers={arm:(leaf.weights,leaf.risk_weights) if arm=='LOCAL_RISK' else (leaf.weights,)
        for arm,leaf in heads.items()}
    beliefs,stages={},{}
    for stage in STAGES:
        task=TASKS[stage]
        acquired=acquire_dataset(template,life,parent,emit,runtime,phase=stage,p_four=PROBABILITIES[task],
            warmup_seed_base=warmup_seed_base(stage),training_seed_base=training_seed_base(stage))
        data=acquired['dataset']; memory=SpawnMemory.from_payload(data['fit_memory'])
        fit_p=memory.predict(); fit_belief=dict(memory=memory.to_payload(),estimated_p_four=fit_p)
        if task not in beliefs: beliefs[task]=fit_belief
        arms={}
        for arm,leaf in heads.items():
            current=(leaf.weights,leaf.risk_weights) if arm=='LOCAL_RISK' else (leaf.weights,)
            if any(new is not old for new,old in zip(current,buffers[arm])):
                raise ValueError('A continuous learner replaced its parameter arrays')
            before=leaf.updates
            if arm=='SOURCE':
                fit=dict(method='NONE',trained_afterstates=0,learning_counts={},target_counts={},
                    consolidation_counts={},seconds=0.,cpu_seconds=0.)
            else:
                for array in current: array.flags.writeable=True
                fit=(fit_split(leaf,data,runtime,alpha=.0025) if arm=='LOCAL_RISK'
                    else fit_consolidated(leaf,data,'EPISODE_MEAN_MC',runtime,alpha=.0025))
                leaf.freeze()
            after=leaf.updates
            if after-before!=fit['trained_afterstates'] or (arm=='SOURCE' and after!=0):
                raise ValueError('Stage samples do not match persistent head update history')
            heldout=score_split(leaf,data,runtime) if arm=='LOCAL_RISK' else score_retained(leaf,data,runtime)
            evaluated={t:_evaluate(leaf,arm,life,t,belief,runtime,engine) for t,belief in beliefs.items()}
            arms[arm]=dict(fit=fit,head_updates_before=before,head_updates_after=after,
                processed_training_samples=fit['trained_afterstates'],parameters_retained=True,
                heldout=heldout,evaluations=evaluated)
            print(json.dumps(dict(event='continual_arm_complete',lifecycle=life,stage=stage,arm=arm,
                updates_before=before,updates_after=after,utilities={t:sum(g['utility'] for g in row['game_summaries'])/32
                    for t,row in evaluated.items()})),flush=True)
        if arms['MC']['processed_training_samples']!=arms['LOCAL_RISK']['processed_training_samples']:
            raise ValueError('Continuous learners processed different factual samples')
        stages[stage]=dict(task=task,dataset=compact_dataset(data),acquisition=acquired['acquisition'],
            fit_snapshot=fit_belief,arms=arms)
        del data,acquired
    return dict(lifecycle=life,parent=parent,head_setup=setups,evaluation_beliefs=beliefs,stages=stages)


def _run_parent(source,output):
    started,cpu_started=perf_counter(),process_time(); child_before=resource.getrusage(resource.RUSAGE_CHILDREN)
    parent=source['parent']; runtime=Path(output)/'runtime'/f'parent_{parent}'
    runtime.mkdir(parents=True,exist_ok=True)
    template,setup=load_leaf(source,runtime)
    engine=NativeValueStream(template,evaluation_seed(parent,'A',0),runtime)
    trace=Path(output)/f'parent_{parent}_records.jsonl.gz'; rows=[]
    try:
        with gzip.open(trace,'xt') as stream:
            def emit(row): stream.write(json.dumps(row,separators=(',',':'),allow_nan=False)+'\n')
            for life in range(parent,64,4):
                rows.append(_run_lifecycle(template,life,parent,runtime,engine,emit)); stream.flush()
    finally: engine.close()
    child_after=resource.getrusage(resource.RUSAGE_CHILDREN)
    return dict(parent=parent,lifecycles=rows,source_setup=setup,trace_file=str(trace.resolve()),trace_bytes=trace.stat().st_size,
        native_evaluation_setup=dict(counts=dict(engine.setup_counts),seconds=engine.setup_seconds),
        cpu_seconds=process_time()-cpu_started,wall_seconds=perf_counter()-started,
        compiler_cpu_seconds=child_after.ru_utime+child_after.ru_stime-child_before.ru_utime-child_before.ru_stime)


def build_accounting(old,lives,parents,cpu,wall):
    inherited_old=old['accounting']['inherited_costs_per_arm']['SOURCE']
    inherited={key:inherited_old[key] for key in ('source_training_raw_tiles','source_training_games',
        'source_training_environment_counts','source_training_seconds','dynamics_raw_tiles','dynamics_costs')}
    rows=[life['stages'][stage] for life in lives for stage in STAGES]
    warm=sum(row['acquisition']['warmup']['raw_tiles'] for row in rows)
    actor=sum(row['acquisition']['training']['raw_tiles'] for row in rows)
    economy=inherited['source_training_raw_tiles']+inherited['dynamics_raw_tiles']+warm+actor
    training={kind:sum_counts(row['acquisition']['training']['counts'][kind] for row in rows)
        for kind in ('environment','planning','learning')}
    warm_env=sum_counts(row['acquisition']['warmup']['environment_counts'] for row in rows)
    env=sum_counts((training['environment'],warm_env)); env['raw_tile_productions']=warm+actor
    evaluations={arm:[e for row in rows for e in row['arms'][arm]['evaluations'].values()] for arm in ARMS}
    result=dict(new_training_environment_observations=warm+actor,physical_acquisitions=len(rows),
        new_warmup_raw_tiles=warm,new_actor_raw_tiles=actor,
        new_raw_tiles_by_stage={stage:sum(life['stages'][stage]['acquisition']['warmup']['raw_tiles']+
            life['stages'][stage]['acquisition']['training']['raw_tiles'] for life in lives) for stage in STAGES},
        economic_training_raw_tiles_per_arm=dict.fromkeys(ARMS,economy),inherited_costs_per_arm={a:inherited for a in ARMS},
        new_training_environment_counts=env,new_actor_counts=training,new_warmup_environment_counts=warm_env,
        new_warmup_direct_counts=sum_counts(row['acquisition']['warmup']['direct_counts'] for row in rows),
        new_warmup_memory_counts=sum_counts(row['acquisition']['warmup']['memory_counts'] for row in rows),
        new_actor_memory_counts=sum_counts(row['acquisition']['training']['memory_counts'] for row in rows),
        reconstruction_counts=sum_counts(row['acquisition']['reconstruction']['counts'] for row in rows),
        reconstruction_memory_counts=sum_counts(row['acquisition']['reconstruction']['memory_counts'] for row in rows),
        reconstruction_cpu_seconds=sum(row['acquisition']['reconstruction']['cpu_seconds'] for row in rows),
        acquisition_cpu_seconds=sum(row['acquisition']['cpu_seconds'] for row in rows),
        acquisition_native_setup_counts=sum_counts(row['acquisition']['native_setup_counts'] for row in rows),
        acquisition_native_setup_seconds=sum(row['acquisition']['native_setup_seconds'] for row in rows),
        excluded_tail_raw_tiles=sum(row['dataset']['costs']['excluded_tail_raw_tiles'] for row in rows),
        processed_training_samples={a:sum(row['arms'][a]['processed_training_samples'] for row in rows) for a in ARMS},
        final_cumulative_updates={a:sum(life['stages']['A2']['arms'][a]['head_updates_after'] for life in lives) for a in ARMS},
        private_head_weight_bytes_created={a:sum(life['head_setup'][a]['private_weight_bytes'] for life in lives) for a in ARMS},
        head_setup_counts={a:sum_counts(life['head_setup'][a]['setup_counts'] for life in lives) for a in ARMS},
        processing_seconds_per_arm={a:dict(**{s:sum(row['arms'][a][s]['seconds'] for row in rows) for s in ('fit','heldout')},
            head_setup=sum(life['head_setup'][a]['setup_seconds'] for life in lives)) for a in ARMS},
        processing_cpu_seconds_per_arm={a:dict(**{s:sum(row['arms'][a][s]['cpu_seconds'] for row in rows) for s in ('fit','heldout')},
            head_setup=sum(life['head_setup'][a]['setup_cpu_seconds'] for life in lives)) for a in ARMS},
        evaluation_counts_per_arm={a:{kind:sum_counts(e['counts'][kind] for e in values)
            for kind in ('environment','planning')} for a,values in evaluations.items()},
        evaluation_counts={kind:sum_counts(e['counts'][kind] for values in evaluations.values() for e in values)
            for kind in ('environment','planning')},
        evaluation_representation_counts={a:sum_counts(e['representation_counts'] for e in values) for a,values in evaluations.items()},
        evaluation_setup_counts={a:sum_counts(e['setup_counts'] for e in values) for a,values in evaluations.items()},
        evaluation_seconds_per_arm={a:sum(e['seconds'] for e in values) for a,values in evaluations.items()},
        evaluation_cpu_seconds_per_arm={a:sum(e['cpu_seconds'] for e in values) for a,values in evaluations.items()},
        canonical_trace_bytes=sum(p['trace_bytes'] for p in parents),worker_cpu_seconds=sum(p['cpu_seconds'] for p in parents),
        compiler_cpu_seconds=sum(p['compiler_cpu_seconds'] for p in parents),coordinator_cpu_seconds=cpu,wall_seconds=wall,
        development_reference=dict(previous_experiment='V302',previous_target_raw_tiles=old['accounting']['new_training_environment_observations'],
            previous_evaluation_counts=old['accounting']['evaluation_counts'],scope='Not inputs to this sequence or its intervals.'),
        accounting_scope='Original source/dynamics paid once per sequence; all three fresh carriers, warmups and tails paid. '
            'Physical acquisition shared once, heads allocated once per lifecycle, actual continued fits and five-cell '
            'checkpoint evaluation counted. Component CPU contained in worker CPU, not added twice.')
    for field,stage,key in (
        ('fit_counts','fit','learning_counts'),('fit_target_counts','fit','target_counts'),
        ('fit_normalization_counts','fit','normalization_counts'),('fit_consolidation_counts','fit','consolidation_counts'),
        ('fit_setup_counts','fit','setup_counts'),('fit_representation_counts','fit','representation_counts'),
        ('heldout_prediction_counts','heldout','prediction_counts'),('heldout_target_counts','heldout','target_counts'),
        ('heldout_representation_counts','heldout','representation_counts'),('heldout_setup_counts','heldout','setup_counts')):
        values={arm:[row['arms'][arm][stage].get(key,{}) for row in rows] for arm in ARMS}
        result[field]={arm:sum_counts({k:v for k,v in row.items() if not k.endswith('_peak')} for row in records)
            for arm,records in values.items()}
        result[field+'_buffer_peaks']={arm:{k:max(row.get(k,0) for row in records)
            for k in {k for row in records for k in row if k.endswith('_peak')}} for arm,records in values.items()}
    return result


def run(source_summary,output):
    output=Path(output); output.mkdir(parents=True,exist_ok=True)
    if (output/'configuration.json').exists() or (output/'summary.json').exists():
        raise FileExistsError('V303 sequence already frozen or completed')
    source_summary=Path(source_summary).resolve(); old=json.loads(source_summary.read_text())
    if not json.loads(source_summary.with_name('audit.json').read_text())['independent_valid']:
        raise ValueError('V302 must have its passing independent audit')
    settings=configuration(source_summary); (output/'configuration.json').write_text(json.dumps(settings,indent=2)+'\n')
    started,cpu_started=perf_counter(),process_time(); parents=[]
    with ProcessPoolExecutor(max_workers=4) as pool:
        jobs=[pool.submit(_run_parent,source,output) for source in old['source_provenance']['parents']]
        for job in as_completed(jobs): parents.append(job.result())
    parents.sort(key=lambda row:row['parent'])
    lives=sorted([life for parent in parents for life in parent['lifecycles']],key=lambda row:row['lifecycle'])
    analysis=summarize(lives)
    result=dict(schema='acfqp.continual.v303',status='EXPERIMENT_COMPLETE',scientific_gate='NOT_A_FORMAL_GATE',
        settings=settings,source_provenance=old['source_provenance'],by_lifecycle=lives,
        parent_receipts=[dict({k:v for k,v in p.items() if k!='lifecycles'},lifecycle_ids=[l['lifecycle'] for l in p['lifecycles']]) for p in parents],
        summary=analysis,accounting=build_accounting(old,lives,parents,process_time()-cpu_started,perf_counter()-started))
    (output/'summary.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps(dict(event='continual_complete',primary_sequence_gain_supported=analysis['primary_sequence_gain_supported'],
        primary=analysis['final_ab_contrasts']['LOCAL_RISK_minus_SOURCE'])),flush=True)
    return result
