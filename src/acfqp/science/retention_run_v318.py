"""Frozen bootstrap and exact-state propagation interventions on retained A facts."""
from concurrent.futures import ProcessPoolExecutor,as_completed
from copy import deepcopy
import json
from pathlib import Path
from time import perf_counter,process_time

import numpy as np

from .b_mechanism_v299 import sum_counts
from .closed_loop_run_v313 import _child_cpu,_new_head
from .closed_loop_versions_v313 import save_version
from .native_greedy_targets_v317 import fit_greedy_targets
from .native_split_risk_v301 import evaluate_split
from .natural_model_revision_v281 import load_leaf
from .native_localized_value_v318 import support_from_dataset,choose_localized,evaluate_localized
from .retention_facts_v318 import iter_a_lifecycles,sample_indices
from .retention_analysis_v318 import summarize,NEW_VIEWS


def _save(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')


def configuration(source):
    return dict(schema='acfqp.retention_mechanism_freeze.v318',
        source_summary=str(Path(source).resolve()),protocol=str(Path(__file__).resolve().parents[3]/'specs/RETENTION_MECHANISM_V318.md'),
        lifecycles=list(range(16)),parents=4,workers=4,task='A',rounds=[1,2],alpha=.0025,
        actual_reproduction='EXACT_ALL_PARAMETERS_TARGET_ARRAYS_AND_NATIVE_COUNTS_BEFORE_INTERVENTION',
        counterfactual='FROZEN_FIRST_V0_WITH_ACTUAL_V1_CURRENT_HEAD',
        propagation='COUPLED_HEAD_SWITCH_AT_NONWIN_H2_LEAF_BY_EXACT_CURRENT_ROUND_NONWIN_FIT_BOARD',
        support_encoding='CELL_0_LOW_NIBBLE_UINT64',max_steps=8192,evaluation_games_per_view=32,
        new_views=list(NEW_VIEWS),expected_new_evaluation_games=2048,new_training_raw_tiles=0,
        evaluation_seed=317900000000,bootstrap_seed=31800001,bootstrap_draws=20000,mechanism_family_size=4,
        mechanism_ci_coverage=.9875,sample_nonwin_per_split=64,probe_positions='FIRST_AND_LAST_PER_SPLIT',
        stop_rule='NO_LIFE_SEED_ALPHA_SUPPORT_TARGET_OR_INTERVAL_SELECTION_RETAIN_CUTOFF')


def apply_version(leaf,version):
    leaf.reward_weights.flags.writeable=True;leaf.risk_weights.flags.writeable=True
    with np.load(version['file'],allow_pickle=False) as saved:
        leaf.reward_weights.reshape(-1)[saved['reward_indices']]=saved['reward_values']
        leaf.risk_weights.reshape(-1)[saved['terminal_indices']]=saved['terminal_values']
    leaf.updates=version['updates'];leaf.freeze()


def frozen_arrays(leaf):
    return dict(reward=leaf.reward_weights,terminal=leaf.risk_weights,
        copy_parameters=0,copy_bytes=0,copy_cpu_seconds=0.,copy_wall_seconds=0.)


def save_support(support,dataset,batch,life,round_index,path):
    started=process_time()
    metadata=dict(schema='acfqp.exact_fit_support.v318',lifecycle=life['lifecycle'],parent=life['parent'],task='A',
        round=round_index,goal_rank=11,encoding=support['encoding'],
        fit_step_end=dataset['fit_step_end'],fit_game_count=dataset['fit_game_count'],
        trained_nonwin_steps=int(np.count_nonzero(np.max(dataset['afterstates'][:dataset['fit_step_end']],axis=1)<11)),
        unique_count=int(len(support['keys'])),source_batch=dict(actor_version=batch['actor_version'],
            stream_seed=batch['acquisition']['training']['before_stream']['stream_seed'],
            fit_step_end=dataset['fit_step_end'],fit_game_count=dataset['fit_game_count']))
    path.parent.mkdir(parents=True,exist_ok=True)
    np.savez_compressed(path,keys=support['keys'],metadata_json=json.dumps(metadata,sort_keys=True))
    return dict(file=str(path.resolve()),saved_bytes=path.stat().st_size,save_cpu_seconds=process_time()-started,
        metadata=metadata,unique_count=len(support['keys']),**{k:v for k,v in support.items() if k!='keys'})


def fit_first_counterfactual(leaf,dataset,first,first_version,current_version,runtime,path):
    """Reuse the unchanged kernel; replace the inherited own-head metadata for this real intervention."""
    started,cpu=perf_counter(),process_time()
    fit=fit_greedy_targets(leaf,dataset,frozen_arrays(first),runtime,path,bootstrap_version=first_version,alpha=.0025)
    artifact=fit['target_artifact'];rewrite_cpu=process_time()
    with np.load(path,allow_pickle=False) as saved:
        arrays={key:saved[key].copy() for key in ('targetreward','targetwin','targetkind','selected_action')}
    metadata=dict(artifact['metadata'],schema='acfqp.frozen_first_greedy_targets.v318',
        bootstrap_mode='FROZEN_FIRST_V0_WITH_ACTUAL_V1_CURRENT_HEAD',current_start_version=current_version)
    with Path(path).open('wb') as stream:
        np.savez_compressed(stream,**arrays,metadata_json=json.dumps(metadata,sort_keys=True,allow_nan=False))
    artifact.update(metadata=metadata,saved_bytes=Path(path).stat().st_size,
        save_cpu_seconds=artifact['save_cpu_seconds']+process_time()-rewrite_cpu)
    fit.update(method='FIRST_BOOTSTRAP_LOCAL',bootstrap_mode=metadata['bootstrap_mode'],
        current_start_version=current_version,metadata_rewrite_cpu_seconds=process_time()-rewrite_cpu,
        cpu_seconds=process_time()-cpu,seconds=perf_counter()-started)
    return fit


def reproduce_actual(leaf,dataset,previous,actual,receipt,runtime,path):
    fit=fit_greedy_targets(leaf,dataset,frozen_arrays(previous),runtime,path,
        bootstrap_version=receipt['fit']['bootstrap_version'],alpha=.0025)
    reward_exact=np.array_equal(leaf.reward_weights,actual.reward_weights)
    risk_exact=np.array_equal(leaf.risk_weights,actual.risk_weights)
    with np.load(path,allow_pickle=False) as now,np.load(receipt['fit']['target_artifact']['file'],allow_pickle=False) as old:
        target_exact=all(np.array_equal(now[key],old[key]) for key in ('targetreward','targetwin','targetkind','selected_action'))
    counts_exact=all(fit[key]==receipt['fit'][key] for key in ('learning_counts','normalization_counts','target_counts','bootstrap_counts','bootstrap_planning_counts'))
    if not(reward_exact and risk_exact and target_exact and counts_exact):
        raise ValueError('V318 must exactly reproduce actual v2 parameters, targets and counts before counterfactual inference')
    return dict(head_exact=True,targets_exact=True,matched_counts=True,reward_max_abs_diff=0.,risk_max_abs_diff=0.,fit=fit)


def _run_life(template,source,life,datasets,extraction,runtime,out):
    identity=life['lifecycle'];initial=life['initial']['A'];belief=initial['planning_belief'];p=belief['estimated_p_four']
    original={r:life['rounds'][r]['A']['arms']['GREEDY_LOCAL'] for r in ('1','2')}
    source_versions=dict(FIRST=initial['head_versions']['FIRST_LOCAL'],R1=original['1']['head_version'],R2=original['2']['head_version'])
    setups=[]
    first,setup=_new_head(template,'LOCAL_RISK',runtime);setups.append(setup);apply_version(first,source_versions['FIRST'])
    previous,setup=_new_head(template,'LOCAL_RISK',runtime,first);setups.append(setup);apply_version(previous,source_versions['R1'])
    actual,setup=_new_head(template,'LOCAL_RISK',runtime,previous);setups.append(setup);apply_version(actual,source_versions['R2'])
    directory=out/'models'/f'life_{identity}';directory.mkdir(parents=True,exist_ok=True)
    replica,setup=_new_head(template,'LOCAL_RISK',runtime,previous);setups.append(setup)
    replica.reward_weights.flags.writeable=replica.risk_weights.flags.writeable=True
    reproduction=reproduce_actual(replica,datasets['2'],previous,actual,original['2'],runtime,directory/'reproduced_targets.npz')
    del replica
    frozen,setup=_new_head(template,'LOCAL_RISK',runtime,previous);setups.append(setup)
    frozen.reward_weights.flags.writeable=frozen.risk_weights.flags.writeable=True
    fit=fit_first_counterfactual(frozen,datasets['2'],first,source_versions['FIRST'],source_versions['R1'],runtime,directory/'first_bootstrap_targets.npz')
    frozen.freeze()
    if fit['learning_counts']!=reproduction['fit']['learning_counts']:
        raise ValueError('V318 target intervention must keep actual current-state writes identical')
    version=save_version(frozen,source,identity,initial['context_id'],'FIRST_BOOTSTRAP_LOCAL',2,
        directory/'FIRST_BOOTSTRAP_LOCAL_v2.npz',base=source_versions['R1'],previous=frozen_arrays(previous))
    supports={r:support_from_dataset(datasets[r]) for r in ('1','2')}
    support_receipts={r:save_support(supports[r],datasets[r],life['rounds'][r]['A']['collectors']['FIXED_FIRST'],life,int(r),
        directory/f'support_R{r}.npz') for r in ('1','2')}
    evaluations=dict(FIRST=deepcopy(initial['evaluations']['FIRST_LOCAL']['H2']),
        R1_OWN_FULL=deepcopy(original['1']['evaluations']['H2']),R2_OWN_FULL=deepcopy(original['2']['evaluations']['H2']))
    seeds=[317900000000+identity*1000000+i for i in range(32)]
    localized=dict(R1_OWN_LOCAL=(previous,first,supports['1'],source_versions['R1'],source_versions['FIRST']),
        R2_OWN_LOCAL=(actual,previous,supports['2'],source_versions['R2'],source_versions['R1']),
        R2_FIRST_LOCAL=(frozen,previous,supports['2'],version,source_versions['R1']))
    for view in NEW_VIEWS:
        if view=='R2_FIRST_FULL':
            evaluated=evaluate_split(frozen,p,.1,seeds,runtime,max_steps=8192)
            references=dict(head_version=version,base_head_version=None,support_file=None)
        else:
            head,base,support,head_version,base_version=localized[view]
            evaluated=evaluate_localized(head,base,support,p,.1,seeds,runtime,max_steps=8192)
            references=dict(head_version=head_version,base_head_version=base_version,
                support_file=support_receipts['1' if view.startswith('R1') else '2']['file'])
        evaluations[view]=dict(evaluated,**references,estimated_p_four=p,view=view,planner='H2')
    probe_rows=[];probe_started=process_time()
    for r in ('1','2'):
        views={'R1_OWN_FULL':previous,'R1_OWN_LOCAL':localized['R1_OWN_LOCAL']} if r=='1' else {
            'R2_OWN_FULL':actual,'R2_OWN_LOCAL':localized['R2_OWN_LOCAL'],
            'R2_FIRST_FULL':frozen,'R2_FIRST_LOCAL':localized['R2_FIRST_LOCAL']}
        for split in ('FIT','HELDOUT'):
            indices=sample_indices(datasets[r],split,64)
            for index in dict.fromkeys((indices[0],indices[-1])):
                board=datasets[r]['postspawn_boards'][index];values={}
                for view,head in views.items():
                    values[view]=(choose_localized(head[0],head[1],head[2],board,p,runtime)
                        if isinstance(head,tuple) else head.choose(board,p))
                probe_rows.append(dict(round=int(r),split=split,index=index,postspawn_board=board.tolist(),views=values))
    row=dict(lifecycle=identity,parent=life['parent'],source=source,planning_belief=belief,source_versions=source_versions,
        extraction=extraction,supports=support_receipts,reproduction=reproduction,
        counterfactual=dict(head_version=version,fit=fit),evaluations=evaluations,probe_rows=probe_rows,
        probe_cpu_seconds=process_time()-probe_started,head_setups=setups)
    _save(out/'lifecycle_receipts'/f'life_{identity}.json',row)
    print(json.dumps(dict(event='retention_mechanism_life_complete',lifecycle=identity,reproduction_exact=True)),flush=True)
    return row


def _run_parent(source,document,out):
    cpu,started,compiler=process_time(),perf_counter(),_child_cpu()
    runtime=out/'runtime'/f"parent_{source['parent']}";runtime.mkdir(parents=True,exist_ok=True)
    template,setup=load_leaf(source,runtime);rows=[]
    for life,datasets,extraction in iter_a_lifecycles(document,source['parent']):
        rows.append(_run_life(template,source,life,datasets,extraction,runtime,out))
        del datasets
    return dict(parent=source['parent'],lifecycles=rows,source_setup=setup,cpu_seconds=process_time()-cpu,
        compiler_cpu_seconds=_child_cpu()-compiler,wall_seconds=perf_counter()-started)


def accounting(document,lives,parents,cpu,wall):
    evaluations=[r['evaluations'][v] for r in lives for v in NEW_VIEWS]
    fits=[r[k]['fit'] for r in lives for k in ('reproduction','counterfactual')]
    supports=[s for r in lives for s in r['supports'].values()]
    worker=sum(p['cpu_seconds'] for p in parents);compiler=sum(p['compiler_cpu_seconds'] for p in parents)
    new_cpu=worker+compiler+cpu
    return dict(new_training_raw_tiles=0,retained_raw_tiles_reconstructed=16*2*65536,
        retained_trace_records_parsed=sum(r['extraction']['parsed_records'] for r in lives),
        retained_compressed_trace_bytes_read=sum(r['extraction']['compressed_bytes_read'] for r in lives),
        retained_selected_training_records=sum(r['extraction']['selected_training_records'] for r in lives),
        retained_fact_read_cpu_seconds=sum(r['extraction']['cpu_seconds'] for r in lives),
        new_evaluation_games=sum(len(v['game_summaries']) for v in evaluations),
        new_evaluation_environment_counts=sum_counts(v['counts']['environment'] for v in evaluations),
        localized_support_counts=sum_counts(v.get('support_counts',{}) for v in evaluations),
        fitted_states=sum(f['trained_afterstates'] for f in fits),fit_cpu_seconds=sum(f['cpu_seconds'] for f in fits),
        fit_counts=sum_counts(f['learning_counts'] for f in fits),support_files=len(supports),
        support_saved_bytes=sum(s['saved_bytes'] for s in supports),support_array_bytes=sum(s['bytes'] for s in supports),
        target_files=len(fits),target_saved_bytes=sum(f['target_artifact']['saved_bytes'] for f in fits),
        new_head_files=len(lives),new_head_saved_bytes=sum(r['counterfactual']['head_version']['saved_bytes'] for r in lives),
        worker_cpu_seconds=worker,compiler_cpu_seconds=compiler,coordinator_cpu_seconds=cpu,
        new_diagnostic_cpu_seconds=new_cpu,wall_seconds=wall,
        inherited_successful_source_and_v317_cpu_seconds=document['accounting']['economic_source_and_target_cpu_seconds'],
        economic_source_v317_and_diagnostic_cpu_seconds=document['accounting']['economic_source_and_target_cpu_seconds']+new_cpu,
        scope='New diagnostic work is contained in workers, compiler children and coordinator CPU; '
            'fit, serialization, support and evaluation CPU are not added twice. Old A facts are reconstructed, not acquired. '
            'Four new view evaluations are physical games; reference evaluations and SOURCE/V317 are reused. '
            'Archived V317 failed-attempt CPU and historical dynamics CPU remain unknown.')


def run(source_summary,output):
    cpu,started=process_time(),perf_counter();out=Path(output).resolve();out.mkdir(parents=True,exist_ok=True)
    if (out/'configuration.json').exists():raise FileExistsError('V318 is already frozen')
    source_path=Path(source_summary).resolve();document=json.loads(source_path.read_text())
    audit=json.loads((source_path.parent/'audit.json').read_text())
    if document['status']!='EXPERIMENT_COMPLETE' or not audit['independent_valid']:
        raise ValueError('V318 requires the audited complete frozen V317 run')
    settings=configuration(source_path);_save(out/'configuration.json',settings)
    parents=[]
    with ProcessPoolExecutor(max_workers=4) as pool:
        for job in as_completed([pool.submit(_run_parent,s,document,out) for s in document['source_provenance']['parents']]):
            result=job.result();parents.append(result)
            _save(out/f"parent_{result['parent']}_receipt.json",{k:v for k,v in result.items() if k!='lifecycles'})
    parents.sort(key=lambda p:p['parent']);lives=sorted((r for p in parents for r in p['lifecycles']),key=lambda r:r['lifecycle'])
    analysis=summarize(lives)
    result=dict(schema='acfqp.retention_mechanism.v318',status='DIAGNOSTIC_COMPLETE' if analysis['complete_game_endpoints'] else 'HOLD_CUTOFF',
        scientific_gate='MECHANISM_DIAGNOSTIC_NOT_FORMAL_GATE',settings=settings,source_summary=str(source_path),
        by_lifecycle=lives,parent_receipts=[{k:v for k,v in p.items() if k!='lifecycles'} for p in parents],summary=analysis,
        accounting=accounting(document,lives,parents,process_time()-cpu,perf_counter()-started))
    _save(out/'summary.json',result);print(json.dumps(dict(event='retention_mechanism_complete',status=result['status'])),flush=True)
    return result
