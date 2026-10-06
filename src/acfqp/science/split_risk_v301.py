"""Whole-game stable-B comparison of bounded local and global terminal risk."""
from concurrent.futures import ProcessPoolExecutor, as_completed
import json
from pathlib import Path
import resource
from time import perf_counter, process_time

from .b_control_v300 import _fit_identity
from .b_mechanism_v299 import load_parent, sum_counts
from .controlled_predictive_online_query_td_v131 import QueryTD
from .controlled_predictive_regime_memory_v115 import SpawnMemory
from .native_episode_consolidation_v290 import fit_consolidated
from .native_retained_critic_v287 import score_retained
from .native_split_risk_v301 import SplitLeaf, fit_split, score_split, evaluate_split, GLOBAL_FEATURE_NAMES
from .native_value_stream_v286 import NativeValueStream
from .natural_model_revision_v281 import load_leaf, QUERY, MAX_STEPS
from .retained_critic_v287 import compact_dataset
from .split_risk_analysis_v301 import ARMS, BOOTSTRAP_SEED, summarize

EVALUATION_GAMES = 32
SPLIT_ARMS = ('LOCAL_RISK','GLOBAL_RISK')


def evaluation_seed(life, episode):
    return 301900000000+life*1000000+episode


def configuration(source_summary):
    return dict(schema='acfqp.split_risk_freeze.v301',
        protocol=str(Path(__file__).resolve().parents[3]/'specs/SPLIT_RISK_V301.md'),
        source_summary=str(Path(source_summary).resolve()),lifecycles=list(range(64)),parents=4,
        arms=ARMS,phase='B',true_p_four=.5,
        source_initialization='ORIGINAL_SOURCE_WITHOUT_A_STAGE_UPDATES',
        observations='ALL_RETAINED_V298_B_COMPLETE_GAMES_WITHOUT_NEW_TRAINING_ACQUISITION',
        fit_fraction=.8,alpha=.0025,query=QUERY,
        representation='SOURCE_INITIALIZED_REWARD_NTUPLE_PLUS_ZERO_INITIALIZED_SIGMOID_TERMINAL_HEAD',
        combination='REWARD_PLUS_8_TIMES_PROBABILITY_MINUS_HALF',
        reward_target='FACTUAL_FUTURE_REWARD_EXCLUDING_CURRENT_REWARD_AND_TERMINAL_BONUS',
        risk_target='COMPLETE_FIT_GAME_WON_LABEL',
        global_feature_names=GLOBAL_FEATURE_NAMES,
        consolidation='GAME_START_PREDICTIONS_THEN_PER_FEATURE_MASS_NORMALIZED_MEAN',
        model_probability='FIXED_OBSERVED_FIT_PREFIX_BELIEF_SHARED_WITH_EVALUATION',
        seed_evaluation=301900000000,evaluation_games=EVALUATION_GAMES,max_steps=MAX_STEPS,
        bootstrap_draws=20000,bootstrap_seed=BOOTSTRAP_SEED,
        primary='GLOBAL_RISK_minus_SOURCE_COMPLETE_GAME_UTILITY',
        evaluation='STATIC_SAME_FIT_PREFIX_BELIEF_WITHOUT_VALUE_OR_MEMORY_UPDATES',
        training='RETAINED_PURE_B_REWARD_AND_RISK_REPRESENTATION_COMPARISON',
        finite_test_passes=dict(native=21,analysis=20,independent_audit=21,driver=4),
        stop_rule='NO_FEATURE_LEARNING_RATE_OR_BUDGET_TUNING_ON_THIS_FROZEN_COHORT')


def _run_lifecycle(template,data,old,runtime,engine):
    life,parent=old['lifecycle'],old['parent']
    memory=SpawnMemory.from_payload(data['fit_memory']); p=memory.predict()
    snapshot=dict(memory=memory.to_payload(),estimated_p_four=p)
    if compact_dataset(data)!=old['dataset'] or snapshot!=old['evaluation_snapshot']:
        raise ValueError('Retained B inventory or observed fit-prefix belief changed')
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
                setup_seconds=leaf.setup_seconds,setup_cpu_seconds=process_time()-setup_cpu,private_weight_bytes=leaf.weights.nbytes)
            fit=fit_consolidated(leaf,data,'EPISODE_MEAN_MC',runtime)
            if _fit_identity(fit)!=_fit_identity(old['arms']['EPISODE_MEAN_MC']['fit']):
                raise ValueError('Original MC fit no longer reproduces')
            leaf.freeze()
        else:
            leaf=SplitLeaf(template,arm,runtime)
            setup=dict(source_weights_shared=False,setup_counts=dict(leaf.setup_counts),
                setup_seconds=leaf.setup_seconds,setup_cpu_seconds=process_time()-setup_cpu,
                private_weight_bytes=leaf.reward_weights.nbytes+leaf.risk_weights.nbytes)
            fit=fit_split(leaf,data,runtime)
            leaf.freeze()
        updates=leaf.updates
        heldout=score_split(leaf,data,runtime) if arm in SPLIT_ARMS else score_retained(leaf,data,runtime)
        if arm not in SPLIT_ARMS:
            prior=old['arms']['FROZEN' if arm=='SOURCE' else 'EPISODE_MEAN_MC']['heldout']
            if heldout['game_metrics']!=prior['game_metrics']:
                raise ValueError('Original SOURCE/MC full heldout scores changed')
        before=engine.state()
        seeds=[evaluation_seed(life,e) for e in range(EVALUATION_GAMES)]
        evaluated=(evaluate_split(leaf,p,.5,seeds,runtime,max_steps=MAX_STEPS) if arm in SPLIT_ARMS
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
        print(json.dumps(dict(event='split_risk_arm_complete',lifecycle=life,arm=arm,
            samples=fit['trained_afterstates'],heldout=heldout['metrics'],
            mean_utility=sum(game['utility'] for game in evaluated['game_summaries'])/EVALUATION_GAMES)),flush=True)
        if arm!='SOURCE': del leaf
    if (template.updates!=0 or len({arms[arm]['processed_training_samples'] for arm in ARMS if arm!='SOURCE'})!=1):
        raise ValueError('Original SOURCE changed or new heads fitted different sample inventories')
    for local,global_ in zip(arms['LOCAL_RISK']['heldout']['component_game_metrics'],arms['GLOBAL_RISK']['heldout']['component_game_metrics']):
        if any(local[key]!=global_[key] for key in ('episode','count','reward_bias','reward_mse','reward_mae')):
            raise ValueError('Risk representation changed the shared reward-head fit')
    return dict(lifecycle=life,parent=parent,dataset=compact_dataset(data),evaluation_snapshot=snapshot,arms=arms)


def _run_parent(source,receipt,old_lives,output):
    started,cpu_started=perf_counter(),process_time()
    child_before=resource.getrusage(resource.RUSAGE_CHILDREN)
    parent=source['parent']; runtime=Path(output)/'runtime'/f'parent_{parent}'
    runtime.mkdir(parents=True,exist_ok=True)
    datasets,roots,reconstruction=load_parent(receipt,old_lives); del roots
    template,setup=load_leaf(source,runtime)
    engine=NativeValueStream(template,evaluation_seed(parent,0),runtime)
    rows=[]
    try:
        for life in receipt['lifecycle_ids']:
            data=datasets.pop(life)
            data['costs']['processing_cpu_seconds']=old_lives[life]['dataset']['costs']['processing_cpu_seconds']
            rows.append(_run_lifecycle(template,data,old_lives[life],runtime,engine)); del data
    finally:
        engine.close()
    child_after=resource.getrusage(resource.RUSAGE_CHILDREN)
    return dict(parent=parent,lifecycles=rows,source_setup=setup,reconstruction=reconstruction,
        native_evaluation_setup=dict(counts=dict(engine.setup_counts),seconds=engine.setup_seconds),
        cpu_seconds=process_time()-cpu_started,wall_seconds=perf_counter()-started,
        compiler_cpu_seconds=child_after.ru_utime+child_after.ru_stime-child_before.ru_utime-child_before.ru_stime)


def build_accounting(old,lives,parents,cpu,wall):
    def values(arm,stage,key): return [life['arms'][arm][stage].get(key,{}) for life in lives]
    def total(rows): return sum_counts({key:v for key,v in row.items() if not key.endswith('_peak')} for row in rows)
    def peaks(rows): return {key:max(row.get(key,0) for row in rows) for key in {key for row in rows for key in row if key.endswith('_peak')}}
    inherited=old['accounting']['inherited_costs_per_arm']['FROZEN']
    result=dict(new_training_environment_observations=0,new_training_environment_counts={},physical_acquisitions=0,
        retained_B_acquisition_raw_tiles=old['accounting']['new_training_environment_observations'],
        economic_training_raw_tiles_per_arm=dict.fromkeys(ARMS,old['accounting']['economic_training_raw_tiles_per_arm']['FROZEN']),
        inherited_costs_per_arm={arm:inherited for arm in ARMS},
        inherited_B_acquisition={key:old['accounting'][key] for key in ('new_training_environment_observations',
            'new_actor_B_raw_tiles','new_warmup_raw_tiles','new_training_environment_counts','new_actor_B_counts',
            'new_warmup_direct_counts','excluded_tail_raw_tiles')},
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
        retained_canonical_trace_bytes=old['accounting']['canonical_trace_bytes'],
        canonical_rows_read=sum(parent['reconstruction']['canonical_rows_read'] for parent in parents),
        reconstruction_counts=sum_counts(parent['reconstruction']['reconstruction_counts'] for parent in parents),
        reconstruction_cpu_seconds=sum(parent['reconstruction']['cpu_seconds'] for parent in parents),
        worker_cpu_seconds=sum(parent['cpu_seconds'] for parent in parents),
        compiler_cpu_seconds=sum(parent['compiler_cpu_seconds'] for parent in parents),coordinator_cpu_seconds=cpu,wall_seconds=wall,
        accounting_scope='All old source, dynamics and B input costs inherited economically per arm, physically shared once. '
            'No new training observations. New representation work, two-head fits, copies, scoring, reconstruction and H2 '
            'evaluation are counted as actual computation. Component processing CPU is contained in worker CPU, not added twice. '
            'Equal input samples do not imply equal parameters, writes or compute budgets.')
    for field,stage,key in (
        ('fit_counts','fit','learning_counts'),('fit_target_counts','fit','target_counts'),
        ('fit_normalization_counts','fit','normalization_counts'),('fit_consolidation_counts','fit','consolidation_counts'),
        ('fit_setup_counts','fit','setup_counts'),('fit_representation_counts','fit','representation_counts'),
        ('heldout_prediction_counts','heldout','prediction_counts'),('heldout_target_counts','heldout','target_counts'),
        ('heldout_representation_counts','heldout','representation_counts'),('heldout_setup_counts','heldout','setup_counts')):
        result[field]={arm:total(values(arm,stage,key)) for arm in ARMS}
        result[field+'_buffer_peaks']={arm:peaks(values(arm,stage,key)) for arm in ARMS}
    return result


def run(source_summary,output):
    output=Path(output); output.mkdir(parents=True,exist_ok=True)
    if (output/'configuration.json').exists() or (output/'summary.json').exists():
        raise FileExistsError('V301 frozen experiment already exists')
    source_summary=Path(source_summary).resolve(); old=json.loads(source_summary.read_text())
    if not json.loads(source_summary.with_name('audit.json').read_text())['independent_valid']:
        raise ValueError('Retained V298 data must have its passing independent audit')
    settings=configuration(source_summary)
    (output/'configuration.json').write_text(json.dumps(settings,indent=2)+'\n')
    started,cpu_started=perf_counter(),process_time()
    old_lives={row['lifecycle']:row for row in old['by_lifecycle']}
    receipts={row['parent']:row for row in old['parent_receipts']}; parents=[]
    with ProcessPoolExecutor(max_workers=4) as pool:
        jobs=[pool.submit(_run_parent,source,receipts[source['parent']],old_lives,output) for source in old['source_provenance']['parents']]
        for job in as_completed(jobs): parents.append(job.result())
    parents.sort(key=lambda row:row['parent'])
    lives=sorted([life for parent in parents for life in parent['lifecycles']],key=lambda row:row['lifecycle'])
    analysis=summarize(lives)
    result=dict(schema='acfqp.split_risk.v301',status='EXPERIMENT_COMPLETE',scientific_gate='NOT_A_FORMAL_GATE',
        settings=settings,source_provenance=old['source_provenance'],by_lifecycle=lives,
        parent_receipts=[dict({key:v for key,v in parent.items() if key!='lifecycles'},
            lifecycle_ids=[life['lifecycle'] for life in parent['lifecycles']]) for parent in parents],
        summary=analysis,accounting=build_accounting(old,lives,parents,process_time()-cpu_started,perf_counter()-started))
    (output/'summary.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps(dict(event='split_risk_complete',status=result['status'],
        split_risk_gain_supported=analysis['split_risk_gain_supported'],
        utility_primary=analysis['paired_contrasts'][analysis['primary_contrast']])),flush=True)
    return result
