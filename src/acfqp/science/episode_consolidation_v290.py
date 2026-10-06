"""Same factual data, address-normalized sequential and episodic MC learning."""
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
import json
from pathlib import Path
import resource
from time import perf_counter, process_time

from .controlled_predictive_online_query_td_v131 import QueryTD
from .controlled_predictive_regime_memory_v115 import SpawnMemory
from .natural_model_revision_v281 import load_leaf, QUERY, MAX_STEPS
from .native_retained_critic_v287 import fit_retained, score_retained
from .native_value_stream_v286 import NativeValueStream
from .retained_actor_data_v287 import load_retained_parent
from .retained_critic_v287 import compact_dataset

ARMS=('FROZEN','EPISODIC_MC','NORMALIZED_SEQUENTIAL_MC','EPISODE_MEAN_MC')
EVALUATION_GAMES=16


def evaluation_seed(life,episode):
    return 290500000000+life*1000000+episode


def configuration(source_summary):
    return dict(schema='acfqp.episode_consolidation_freeze.v290',
        protocol=str(Path(__file__).resolve().parents[3]/'specs/EPISODE_CONSOLIDATION_V290.md'),
        source_summary=str(Path(source_summary).resolve()),lifecycles=list(range(16)),parents=4,
        arms=ARMS,phase='A',fit_fraction=.8,alpha=.0025,query=QUERY,
        evaluation_games=EVALUATION_GAMES,seed_evaluation=290500000000,
        max_steps=MAX_STEPS,bootstrap_draws=20000,bootstrap_seed=29000001,
        primary='EPISODE_MEAN_MC_minus_FROZEN_COMPLETE_GAME_UTILITY',
        primary_prediction='EPISODE_MEAN_MC_minus_FROZEN_COMPLETE_HELDOUT_MSE',
        address_counts='ALL_NONWINNING_FEATURE_OCCURRENCES_IN_ONE_COMPLETE_GAME',
        evaluation='STATIC_SAME_FIT_PREFIX_BELIEF_WITHOUT_VALUE_OR_MEMORY_UPDATES',
        finite_test_passes=dict(native=7,analysis=10,driver=3))


def check_original_fit(fit,expected):
    for key in ('learning_counts','target_counts','first_update','last_update'):
        if fit[key]!=expected[key]:
            raise ValueError(f'The original V287 MC {key} differs')


def _run_parent(source,parent_receipt,original_lives,old_lives,output):
    from .native_episode_consolidation_v290 import fit_consolidated
    started,cpu_started=perf_counter(),process_time()
    before_child=resource.getrusage(resource.RUSAGE_CHILDREN)
    runtime=Path(output)/'runtime'/f"parent_{source['parent']}"
    runtime.mkdir(parents=True,exist_ok=True)
    life_ids=parent_receipt['lifecycle_ids']
    datasets=load_retained_parent(parent_receipt['trace_file'],life_ids,original_lives)
    template,setup=load_leaf(source,runtime)
    engine=NativeValueStream(template,evaluation_seed(life_ids[0],0),runtime)
    rows=[]
    for life in life_ids:
        data=datasets.pop(life)
        old=old_lives[life]
        for key in ('games','fit_game_count','fit_step_end','fit_end_raw','fit_memory'):
            if data[key]!=old['dataset'][key]:
                raise ValueError('The original fixed actor dataset differs from V287')
        memory=SpawnMemory.from_payload(data['fit_memory'])
        p=memory.predict()
        if p!=old['evaluation_snapshot']['estimated_p_four']:
            raise ValueError('The frozen fit-prefix belief differs from V287')
        arms={}
        inventory=[]
        for arm in ARMS:
            if arm=='FROZEN':
                leaf=template
                fit=dict(method='NONE',trained_afterstates=0,learning_counts={},target_counts={},
                    consolidation_counts={},seconds=0.,cpu_seconds=0.)
                head_setup=dict(source_weights_shared=True,setup_counts={},setup_seconds=0.,private_weight_bytes=0)
            else:
                leaf=QueryTD(template.parent,'PRIOR',runtime)
                head_setup=dict(source_weights_shared=False,setup_counts=dict(leaf.setup_counts),
                    setup_seconds=leaf.setup_seconds,private_weight_bytes=leaf.weights.nbytes)
                if arm=='EPISODIC_MC':
                    fit=fit_retained(leaf,data,'MC',runtime)
                    check_original_fit(fit,old['arms']['EPISODIC_MC']['fit'])
                    fit['consolidation_counts']={}
                else:
                    fit=fit_consolidated(leaf,data,arm,runtime)
                leaf.freeze()
                inventory.append(fit['trained_afterstates'])
            updates_before=leaf.updates
            heldout=score_retained(leaf,data,runtime)
            if arm in ('FROZEN','EPISODIC_MC'):
                if heldout['game_metrics']!=old['arms'][arm]['heldout']['game_metrics']:
                    raise ValueError('The original complete heldout critic predictions differ')
            before_eval=engine.state()
            evaluated=engine.evaluate_games(leaf,p,.1,
                [evaluation_seed(life,e) for e in range(EVALUATION_GAMES)],depth=2,max_steps=MAX_STEPS)
            if engine.state()!=before_eval or leaf.updates!=updates_before:
                raise ValueError('Static heldout/evaluation altered the critic or actor stream')
            arms[arm]=dict(fit=fit,head_setup=head_setup,heldout=heldout,
                processed_training_samples=fit['trained_afterstates'],sample_counter=leaf.updates,
                game_summaries=evaluated['game_summaries'],evaluation_counts=evaluated['counts'],
                evaluation_seconds=evaluated['seconds'],evaluation_cpu_seconds=evaluated['cpu_seconds'])
            print(json.dumps(dict(event='episode_consolidation_arm_complete',lifecycle=life,arm=arm,
                samples=fit['trained_afterstates'],parameter_writes=fit['learning_counts'].get('table_updates',0),
                heldout=heldout['metrics'],mean_utility=sum(g['utility'] for g in evaluated['game_summaries'])/16)),flush=True)
            if arm!='FROZEN':
                del leaf
        if len(set(inventory))!=1:
            raise ValueError('The three learners must process the same complete MC training samples')
        rows.append(dict(lifecycle=life,parent=source['parent'],dataset=compact_dataset(data),
            evaluation_snapshot=dict(memory=memory.to_payload(),estimated_p_four=p),arms=arms,
            original_frozen_and_mc_heldout_exact=True,original_mc_fit_exact=True))
    engine.close()
    after_child=resource.getrusage(resource.RUSAGE_CHILDREN)
    return dict(parent=source['parent'],lifecycles=rows,source_setup=setup,
        native_evaluation_setup=dict(counts=dict(engine.setup_counts),seconds=engine.setup_seconds),
        cpu_seconds=process_time()-cpu_started,wall_seconds=perf_counter()-started,
        compiler_cpu_seconds=after_child.ru_utime+after_child.ru_stime-before_child.ru_utime-before_child.ru_stime)


def build_accounting(old,lives,parents,cpu,wall):
    def summed(values):
        return dict(sum((Counter(value) for value in values),Counter()))
    def targets(arm,stage):
        return [life['arms'][arm][stage]['target_counts'] for life in lives]
    def total_targets(values):
        return summed({k:v for k,v in value.items() if k!='target_buffer_doubles_peak'} for value in values)
    consolidated={arm:[life['arms'][arm]['fit'].get('consolidation_counts',{}) for life in lives] for arm in ARMS}
    inherited=old['accounting']['inherited_costs_per_arm']['FROZEN']
    return dict(new_training_environment_observations=0,
        economic_training_raw_tiles_per_arm={a:old['accounting']['economic_training_raw_tiles_per_arm']['FROZEN'] for a in ARMS},
        inherited_costs_per_arm={a:inherited for a in ARMS},
        retained_physical_A_raw_tiles=old['accounting']['retained_physical_A_raw_tiles'],
        retained_physical_A_counts=old['accounting']['retained_physical_A_counts'],
        reconstruction_costs_by_lifecycle={str(l['lifecycle']):l['dataset']['costs'] for l in lives},
        processed_training_samples={a:sum(l['arms'][a]['processed_training_samples'] for l in lives) for a in ARMS},
        fit_counts={a:summed(l['arms'][a]['fit']['learning_counts'] for l in lives) for a in ARMS},
        fit_target_counts={a:total_targets(targets(a,'fit')) for a in ARMS},
        fit_target_buffer_doubles_peak={a:max(v.get('target_buffer_doubles_peak',0) for v in targets(a,'fit')) for a in ARMS},
        consolidation_counts={a:summed({k:v for k,v in value.items() if not k.endswith('_peak')}
            for value in consolidated[a]) for a in ARMS},
        consolidation_buffer_peaks={a:{k:max(value.get(k,0) for value in consolidated[a])
            for k in {key for value in consolidated[a] for key in value if key.endswith('_peak')}} for a in ARMS},
        heldout_prediction_counts={a:summed(l['arms'][a]['heldout']['prediction_counts'] for l in lives) for a in ARMS},
        heldout_target_counts={a:total_targets(targets(a,'heldout')) for a in ARMS},
        heldout_target_buffer_doubles_peak={a:max(v.get('target_buffer_doubles_peak',0) for v in targets(a,'heldout')) for a in ARMS},
        evaluation_counts={kind:summed(l['arms'][a]['evaluation_counts'][kind] for l in lives for a in ARMS)
            for kind in ('environment','planning')},
        evaluation_counts_per_arm={a:{kind:summed(l['arms'][a]['evaluation_counts'][kind] for l in lives)
            for kind in ('environment','planning')} for a in ARMS},
        private_head_weight_bytes_created={a:sum(l['arms'][a]['head_setup']['private_weight_bytes'] for l in lives) for a in ARMS},
        worker_cpu_seconds=sum(p['cpu_seconds'] for p in parents),
        compiler_cpu_seconds=sum(p['compiler_cpu_seconds'] for p in parents),
        coordinator_cpu_seconds=cpu,wall_seconds=wall,
        accounting_scope='Equal original source/dynamics/warmup/all-A acquisition per arm; paid physical acquisition once. '
            'Training sample counts are equal for the three learners, actual parameter writes and consolidation work differ. '
            'Fresh complete-game evaluation and all current processing are new costs.')


def run(source_summary,output):
    from .episode_consolidation_analysis_v290 import summarize
    output=Path(output)
    output.mkdir(parents=True,exist_ok=True)
    if (output/'configuration.json').exists() or (output/'summary.json').exists():
        raise FileExistsError('V290 formal freeze or results already exist')
    old=json.loads(Path(source_summary).read_text())
    if not json.loads(Path(source_summary).with_name('audit.json').read_text())['independent_valid']:
        raise ValueError('Original factual critic data needs its passing independent audit')
    settings=configuration(source_summary)
    (output/'configuration.json').write_text(json.dumps(settings,indent=2)+'\n')
    started,cpu_started=perf_counter(),process_time()
    original=json.loads(Path(old['settings']['source_summary']).read_text())
    original_lives={l['lifecycle']:l for l in original['by_lifecycle']}
    old_lives={l['lifecycle']:l for l in old['by_lifecycle']}
    parents=[]
    with ProcessPoolExecutor(max_workers=4) as pool:
        jobs=[pool.submit(_run_parent,s,original['parent_receipts'][s['parent']],original_lives,old_lives,output)
            for s in old['source_provenance']['parents']]
        for job in as_completed(jobs):
            parents.append(job.result())
    parents.sort(key=lambda p:p['parent'])
    lives=sorted([l for p in parents for l in p['lifecycles']],key=lambda l:l['lifecycle'])
    analysis=summarize(lives)
    result=dict(schema='acfqp.episode_consolidation.v290',status='EXPERIMENT_COMPLETE',
        scientific_gate='NOT_A_FORMAL_GATE',settings=settings,source_provenance=old['source_provenance'],
        by_lifecycle=lives,parent_receipts=[dict({k:v for k,v in p.items() if k!='lifecycles'},
            lifecycle_ids=[l['lifecycle'] for l in p['lifecycles']]) for p in parents],
        summary=analysis,accounting=build_accounting(old,lives,parents,process_time()-cpu_started,perf_counter()-started))
    (output/'summary.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps(dict(event='episode_consolidation_complete',status=result['status'],
        utility_primary=analysis['paired_contrasts'][analysis['primary_contrast']],
        mse_primary=analysis['heldout_contrasts'][analysis['primary_contrast']]['mse'])),flush=True)
    return result
