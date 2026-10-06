"""Independent B acquisition and primary confirmation of unchanged V301 LOCAL."""
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
from .local_risk_analysis_v302 import ARMS, BOOTSTRAP_SEED, summarize
from .native_episode_consolidation_v290 import fit_consolidated
from .native_retained_critic_v287 import score_retained
from .native_split_risk_v301 import SplitLeaf, fit_split, score_split, evaluate_split
from .native_value_stream_v286 import NativeValueStream
from .natural_model_revision_v281 import load_leaf, QUERY, MAX_STEPS
from .retained_critic_v287 import compact_dataset

EVALUATION_GAMES = 32
WARMUP_SEED_BASE = 302100000000
TRAINING_SEED_BASE = 302200000000


def evaluation_seed(life, episode):
    return 302900000000+life*1000000+episode


def configuration(source_summary):
    return dict(schema='acfqp.local_risk_freeze.v302',
        protocol=str(Path(__file__).resolve().parents[3]/'specs/LOCAL_RISK_V302.md'),
        source_summary=str(Path(source_summary).resolve()),lifecycles=list(range(64)),parents=4,
        arms=ARMS,phase='B',true_p_four=.5,canonical_acquisition_arm='FROZEN',
        source_initialization='ORIGINAL_SOURCE_WITHOUT_A_STAGE_UPDATES',
        observations='NEW_INDEPENDENT_PURE_B_COHORT_WITHOUT_OLD_TARGET_INPUTS',
        raw_budget=RAW_BUDGET,fit_fraction=.8,alpha=.0025,query=QUERY,
        representation='UNCHANGED_V301_LOCAL_REWARD_AND_SIGMOID_TERMINAL_NTUPLES',
        reward_initialization='ORIGINAL_SOURCE_UTILITY_TABLE',risk_initialization='ZERO_LOGITS',
        combination='REWARD_PLUS_8_TIMES_PROBABILITY_MINUS_HALF',
        reward_target='FACTUAL_FUTURE_REWARD_EXCLUDING_CURRENT_REWARD_AND_TERMINAL_BONUS',
        risk_target='COMPLETE_FIT_GAME_WON_LABEL',
        consolidation='GAME_START_PREDICTIONS_THEN_PER_FEATURE_MASS_NORMALIZED_MEAN',
        model_probability='FIXED_OBSERVED_FIT_PREFIX_BELIEF_SHARED_WITH_EVALUATION',
        seed_warmup=WARMUP_SEED_BASE,seed_training=TRAINING_SEED_BASE,seed_evaluation=302900000000,
        evaluation_games=EVALUATION_GAMES,max_steps=MAX_STEPS,
        bootstrap_draws=20000,bootstrap_seed=BOOTSTRAP_SEED,
        primary='LOCAL_RISK_minus_SOURCE_COMPLETE_GAME_UTILITY',
        interval_scope='CONDITIONAL_ON_FOUR_FROZEN_PARENTS',
        evaluation='STATIC_SAME_FIT_PREFIX_BELIEF_WITHOUT_VALUE_OR_MEMORY_UPDATES',
        stop_rule='NO_TUNING_OR_OLD_COHORT_POOLING; ADVANCE_TO_CONTINUAL_TRANSFER_IF_CONFIRMED')


def _run_lifecycle(template,data,acquisition,life,parent,runtime,engine):
    memory=SpawnMemory.from_payload(data['fit_memory']); p=memory.predict()
    arms={}
    for arm in ARMS:
        setup_cpu=process_time()
        if arm=='SOURCE':
            leaf=template
            fit=dict(method='NONE',trained_afterstates=0,learning_counts={},target_counts={},
                consolidation_counts={},seconds=0.,cpu_seconds=0.)
            setup=dict(source_weights_shared=True,setup_counts={},setup_seconds=0.,setup_cpu_seconds=0.,private_weight_bytes=0)
        elif arm=='MC':
            leaf=QueryTD(template.parent,'PRIOR',runtime)
            setup=dict(source_weights_shared=False,setup_counts=dict(leaf.setup_counts),
                setup_seconds=leaf.setup_seconds,setup_cpu_seconds=process_time()-setup_cpu,
                private_weight_bytes=leaf.weights.nbytes)
            fit=fit_consolidated(leaf,data,'EPISODE_MEAN_MC',runtime)
            leaf.freeze()
        else:
            leaf=SplitLeaf(template,'LOCAL_RISK',runtime)
            setup=dict(source_weights_shared=False,setup_counts=dict(leaf.setup_counts),
                setup_seconds=leaf.setup_seconds,setup_cpu_seconds=process_time()-setup_cpu,
                private_weight_bytes=leaf.reward_weights.nbytes+leaf.risk_weights.nbytes)
            fit=fit_split(leaf,data,runtime,alpha=.0025)
            leaf.freeze()
        updates=leaf.updates
        heldout=score_split(leaf,data,runtime) if arm=='LOCAL_RISK' else score_retained(leaf,data,runtime)
        before=engine.state()
        seeds=[evaluation_seed(life,e) for e in range(EVALUATION_GAMES)]
        evaluated=(evaluate_split(leaf,p,.5,seeds,runtime,max_steps=MAX_STEPS) if arm=='LOCAL_RISK'
            else engine.evaluate_games(leaf,p,.5,seeds,depth=2,max_steps=MAX_STEPS))
        if engine.state()!=before or leaf.updates!=updates:
            raise ValueError('Static evaluation changed value parameters or acquisition stream')
        arms[arm]=dict(fit=fit,head_setup=setup,heldout=heldout,
            processed_training_samples=fit['trained_afterstates'],sample_counter=leaf.updates,
            game_summaries=evaluated['game_summaries'],evaluation_counts=evaluated['counts'],
            evaluation_representation_counts=evaluated.get('representation_counts',{}),
            evaluation_setup_counts=evaluated.get('setup_counts',{}),
            evaluation_seconds=evaluated['seconds'],evaluation_cpu_seconds=evaluated['cpu_seconds'],
            static_evaluation_valid=True)
        print(json.dumps(dict(event='local_risk_arm_complete',lifecycle=life,arm=arm,
            samples=fit['trained_afterstates'],heldout=heldout['metrics'],
            mean_utility=sum(game['utility'] for game in evaluated['game_summaries'])/EVALUATION_GAMES)),flush=True)
        if arm!='SOURCE': del leaf
    if template.updates!=0 or arms['MC']['processed_training_samples']!=arms['LOCAL_RISK']['processed_training_samples']:
        raise ValueError('Original SOURCE changed or learners fitted different sample inventories')
    return dict(lifecycle=life,parent=parent,dataset=compact_dataset(data),acquisition=acquisition,
        evaluation_snapshot=dict(memory=memory.to_payload(),estimated_p_four=p),arms=arms)


def _run_parent(source,output):
    started,cpu_started=perf_counter(),process_time()
    child_before=resource.getrusage(resource.RUSAGE_CHILDREN)
    parent=source['parent']; runtime=Path(output)/'runtime'/f'parent_{parent}'
    runtime.mkdir(parents=True,exist_ok=True)
    template,setup=load_leaf(source,runtime)
    engine=NativeValueStream(template,evaluation_seed(parent,0),runtime)
    trace=Path(output)/f'parent_{parent}_records.jsonl.gz'; rows=[]
    try:
        with gzip.open(trace,'xt') as stream:
            def emit(row):
                stream.write(json.dumps(row,separators=(',',':'),allow_nan=False)+'\n')
            for life in range(parent,64,4):
                acquired=acquire_dataset(template,life,parent,emit,runtime,phase='B',p_four=.5,
                    warmup_seed_base=WARMUP_SEED_BASE,training_seed_base=TRAINING_SEED_BASE)
                rows.append(_run_lifecycle(template,acquired['dataset'],acquired['acquisition'],
                    life,parent,runtime,engine))
                stream.flush(); del acquired
    finally:
        engine.close()
    child_after=resource.getrusage(resource.RUSAGE_CHILDREN)
    return dict(parent=parent,lifecycles=rows,source_setup=setup,
        trace_file=str(trace.resolve()),trace_bytes=trace.stat().st_size,
        native_evaluation_setup=dict(counts=dict(engine.setup_counts),seconds=engine.setup_seconds),
        cpu_seconds=process_time()-cpu_started,wall_seconds=perf_counter()-started,
        compiler_cpu_seconds=child_after.ru_utime+child_after.ru_stime-child_before.ru_utime-child_before.ru_stime)


def build_accounting(old,lives,parents,cpu,wall):
    inherited_old=old['accounting']['inherited_costs_per_arm']['SOURCE']
    inherited={key:inherited_old[key] for key in ('source_training_raw_tiles','source_training_games',
        'source_training_environment_counts','source_training_seconds','dynamics_raw_tiles','dynamics_costs')}
    warm_raw=sum(life['acquisition']['warmup']['raw_tiles'] for life in lives)
    actor_raw=sum(life['acquisition']['training']['raw_tiles'] for life in lives)
    training_counts={kind:sum_counts(life['acquisition']['training']['counts'][kind] for life in lives)
        for kind in ('environment','planning','learning')}
    warm_environment=sum_counts(life['acquisition']['warmup']['environment_counts'] for life in lives)
    environment=sum_counts((training_counts['environment'],warm_environment))
    environment['raw_tile_productions']=actor_raw+warm_raw
    economic=inherited['source_training_raw_tiles']+inherited['dynamics_raw_tiles']+warm_raw+actor_raw
    result=dict(new_training_environment_observations=actor_raw+warm_raw,physical_acquisitions=len(lives),
        new_warmup_raw_tiles=warm_raw,new_actor_B_raw_tiles=actor_raw,
        economic_training_raw_tiles_per_arm=dict.fromkeys(ARMS,economic),
        inherited_costs_per_arm={arm:inherited for arm in ARMS},
        new_training_environment_counts=environment,new_actor_B_counts=training_counts,
        new_warmup_environment_counts=warm_environment,
        new_warmup_direct_counts=sum_counts(life['acquisition']['warmup']['direct_counts'] for life in lives),
        new_warmup_memory_counts=sum_counts(life['acquisition']['warmup']['memory_counts'] for life in lives),
        new_actor_memory_counts=sum_counts(life['acquisition']['training']['memory_counts'] for life in lives),
        reconstruction_counts=sum_counts(life['acquisition']['reconstruction']['counts'] for life in lives),
        reconstruction_memory_counts=sum_counts(life['acquisition']['reconstruction']['memory_counts'] for life in lives),
        reconstruction_cpu_seconds=sum(life['acquisition']['reconstruction']['cpu_seconds'] for life in lives),
        excluded_tail_raw_tiles=sum(life['dataset']['costs']['excluded_tail_raw_tiles'] for life in lives),
        acquisition_cpu_seconds=sum(life['acquisition']['cpu_seconds'] for life in lives),
        acquisition_native_setup_counts=sum_counts(life['acquisition']['native_setup_counts'] for life in lives),
        acquisition_native_setup_seconds=sum(life['acquisition']['native_setup_seconds'] for life in lives),
        processed_training_samples={arm:sum(life['arms'][arm]['processed_training_samples'] for life in lives) for arm in ARMS},
        private_head_weight_bytes_created={arm:sum(life['arms'][arm]['head_setup']['private_weight_bytes'] for life in lives) for arm in ARMS},
        head_setup_counts={arm:sum_counts(life['arms'][arm]['head_setup']['setup_counts'] for life in lives) for arm in ARMS},
        processing_seconds_per_arm={arm:dict(**{stage:sum(life['arms'][arm][stage]['seconds'] for life in lives)
            for stage in ('fit','heldout')},head_setup=sum(life['arms'][arm]['head_setup']['setup_seconds'] for life in lives)) for arm in ARMS},
        processing_cpu_seconds_per_arm={arm:dict(**{stage:sum(life['arms'][arm][stage]['cpu_seconds'] for life in lives)
            for stage in ('fit','heldout')},head_setup=sum(life['arms'][arm]['head_setup']['setup_cpu_seconds'] for life in lives)) for arm in ARMS},
        evaluation_counts_per_arm={arm:{kind:sum_counts(life['arms'][arm]['evaluation_counts'][kind] for life in lives)
            for kind in ('environment','planning')} for arm in ARMS},
        evaluation_counts={kind:sum_counts(life['arms'][arm]['evaluation_counts'][kind] for life in lives for arm in ARMS)
            for kind in ('environment','planning')},
        evaluation_representation_counts={arm:sum_counts(life['arms'][arm]['evaluation_representation_counts'] for life in lives) for arm in ARMS},
        evaluation_setup_counts={arm:sum_counts(life['arms'][arm]['evaluation_setup_counts'] for life in lives) for arm in ARMS},
        evaluation_cpu_seconds_per_arm={arm:sum(life['arms'][arm]['evaluation_cpu_seconds'] for life in lives) for arm in ARMS},
        evaluation_seconds_per_arm={arm:sum(life['arms'][arm]['evaluation_seconds'] for life in lives) for arm in ARMS},
        canonical_trace_bytes=sum(parent['trace_bytes'] for parent in parents),
        worker_cpu_seconds=sum(parent['cpu_seconds'] for parent in parents),
        compiler_cpu_seconds=sum(parent['compiler_cpu_seconds'] for parent in parents),coordinator_cpu_seconds=cpu,wall_seconds=wall,
        development_reference=dict(method_selection='V301_PRESPECIFIED_LOCAL_SECONDARY_RESULT',
            previous_B_acquisition_raw_tiles=old['accounting']['retained_B_acquisition_raw_tiles'],
            previous_evaluation_counts=old['accounting']['evaluation_counts'],
            scope='Old target training and evaluations are development costs, not inputs to the new fits or intervals.'),
        accounting_scope='Each arm pays original SOURCE and dynamics plus all fresh B warmup and actor raw, '
            'including initial and excluded tail. Physical acquisition is shared once. Actual two-head fits, '
            'copies, parameters, scoring, representation and H2 evaluation are counted separately. Component '
            'CPU is contained in worker CPU and is not added twice; equal data is not equal compute.')
    for field,stage,key in (
        ('fit_counts','fit','learning_counts'),('fit_target_counts','fit','target_counts'),
        ('fit_normalization_counts','fit','normalization_counts'),('fit_consolidation_counts','fit','consolidation_counts'),
        ('fit_setup_counts','fit','setup_counts'),('fit_representation_counts','fit','representation_counts'),
        ('heldout_prediction_counts','heldout','prediction_counts'),('heldout_target_counts','heldout','target_counts'),
        ('heldout_representation_counts','heldout','representation_counts'),('heldout_setup_counts','heldout','setup_counts')):
        values={arm:[life['arms'][arm][stage].get(key,{}) for life in lives] for arm in ARMS}
        result[field]={arm:sum_counts({k:v for k,v in row.items() if not k.endswith('_peak')} for row in rows)
            for arm,rows in values.items()}
        result[field+'_buffer_peaks']={arm:{k:max(row.get(k,0) for row in rows)
            for k in {k for row in rows for k in row if k.endswith('_peak')}} for arm,rows in values.items()}
    return result


def run(source_summary,output):
    output=Path(output); output.mkdir(parents=True,exist_ok=True)
    if (output/'configuration.json').exists() or (output/'summary.json').exists():
        raise FileExistsError('V302 frozen experiment already exists')
    source_summary=Path(source_summary).resolve(); old=json.loads(source_summary.read_text())
    if not json.loads(source_summary.with_name('audit.json').read_text())['independent_valid']:
        raise ValueError('V301 method selection must have its passing independent audit')
    settings=configuration(source_summary)
    (output/'configuration.json').write_text(json.dumps(settings,indent=2)+'\n')
    started,cpu_started=perf_counter(),process_time(); parents=[]
    with ProcessPoolExecutor(max_workers=4) as pool:
        jobs=[pool.submit(_run_parent,source,output) for source in old['source_provenance']['parents']]
        for job in as_completed(jobs): parents.append(job.result())
    parents.sort(key=lambda row:row['parent'])
    lives=sorted([life for parent in parents for life in parent['lifecycles']],key=lambda row:row['lifecycle'])
    analysis=summarize(lives)
    result=dict(schema='acfqp.local_risk.v302',status='EXPERIMENT_COMPLETE',scientific_gate='NOT_A_FORMAL_GATE',
        settings=settings,source_provenance=old['source_provenance'],by_lifecycle=lives,
        parent_receipts=[dict({key:v for key,v in parent.items() if key!='lifecycles'},
            lifecycle_ids=[life['lifecycle'] for life in parent['lifecycles']]) for parent in parents],
        summary=analysis,accounting=build_accounting(old,lives,parents,process_time()-cpu_started,perf_counter()-started))
    (output/'summary.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps(dict(event='local_risk_complete',status=result['status'],
        independent_local_learning_confirmed=analysis['independent_local_learning_confirmed'],
        utility_primary=analysis['paired_contrasts'][analysis['primary_contrast']])),flush=True)
    return result
