"""Same-suffix reward/WIN learning with two fit and two held-out members."""
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
import json
from pathlib import Path
from time import perf_counter, process_time

import numpy as np

from .b_mechanism_v299 import sum_counts
from .closed_loop_run_v313 import _child_cpu, _new_head
from .closed_loop_versions_v313 import snapshot_weights, save_version
from .native_query_supervision_v319 import fit_supervision
from .native_win_learning_v324 import fit_win_supervision
from .native_split_risk_v301 import evaluate_split
from .native_value_stream_v286 import NativeValueStream
from .natural_model_revision_v281 import load_leaf
from .query_supervision_run_v319 import _restore_first, _artifact, _compact, _save
from .joint_terminal_prediction_v327 import predict_components_batch
from .joint_terminal_analysis_v327 import summarize, prediction_metrics

TASKS, ARMS = ('A','B'), ('WIN_ONLY','JOINT_RETURN')
PROBABILITIES = {'A':.1,'B':.5}
GROUPS, MEMBERS, EPOCHS, EPISODES = 1024, 4, 16, 64
FIT_MEMBERS, VALIDATION_MEMBERS = (0,1), (2,3)
PREDICTION_FIELDS = ('rewards','probabilities','logits','utilities')


def evaluation_seed(life, task, episode):
    return 3279000000000+life*1000000+TASKS.index(task)*100000+episode


def configuration(source):
    return dict(schema='acfqp.joint_terminal_freeze.v327', source_summary=str(Path(source).resolve()),
        protocol=str(Path(__file__).resolve().parents[3]/'specs/JOINT_TERMINAL_V327.md'),
        lifecycles=list(range(16)),parents=4,workers=4,tasks=list(TASKS),
        arms=['SOURCE','FIRST_LOCAL',*ARMS],updating_arms=list(ARMS),rounds=[1,2],
        groups=GROUPS,retained_members=MEMBERS,fit_members=list(FIT_MEMBERS),
        validation_members=list(VALIDATION_MEMBERS),fit_replicates=2,epochs=EPOCHS,alpha=.0025,
        rootgroup_updates_per_arm_task_round=GROUPS*EPOCHS,
        initial='ACTUAL_V326_FIRST_V0_RESTORE_NO_OLD_UPDATED_HEADS',
        targets='PAIRED_SAME_V326_FULL_SUFFIX_REWARD_RETURN_AND_WIN',
        target_policy='SAVED_DIRECT_THEN_IMMUTABLE_FIRST_H2_TRUE_WORLD',
        reward_contract='WIN_ONLY_COMPLETE_FIRST_REWARD_FROZEN_JOINT_RETURN_REWARD_LEARNED',
        win_contract='COMPLETE_WIN_TABLES_BIT_EXACT_EQUAL_BOTH_ARMS_AFTER_EVERY_STAGE',
        update='SIXTEEN_FIXED_ORDER_PASSES_TWO_REAL_MEMBERS_NO_DUPLICATION',
        validation='MEMBERS_TWO_THREE_UNUSED_BY_THESE_RETRAINED_MODELS_SAME_OBSERVED_ROOTS',
        prediction='ACTUAL_NATIVE_COMPONENTS_FIRST_BEFORE_AFTER_UNIQUE_SNAPSHOTS',
        planning_belief='ACTUAL_IMMUTABLE_V326_FIRST_BANK_BELIEF',true_probabilities=PROBABILITIES,
        new_training_raw_tiles=0,new_source_fits=0,new_FIRST_fits=0,
        expected_fit_member_uses_per_arm=16*2*2*GROUPS*2,
        expected_rootgroup_updates_per_arm=16*2*2*GROUPS*EPOCHS,
        max_steps=8192,evaluation_games_per_cell=EPISODES,seed_evaluation=3279000000000,
        expected_new_evaluation_games=12288,reused_evaluation_games=0,
        bootstrap_draws=20000,bootstrap_seed=32700001,
        primary='JOINT_RETURN_minus_FIRST_LOCAL_FINAL_AB',
        target_combination_contribution='JOINT_RETURN_minus_WIN_ONLY_FINAL_AB',
        retention='FINAL_JOINT_MINUS_OWN_FIRST_PER_TASK_CI_LOWER_NONNEGATIVE',
        route_if_retained_gain='ADVANCE_TO_NEW_COHORT_CONFIRMATION',
        route_otherwise='STOP_FIXED_FIRST_TERMINAL_REGRESSION',
        stop_rule='ANY_NATURAL_GAME_OR_RETAINED_SUFFIX_CUTOFF_GLOBAL_HOLD_NO_TUNING_OR_REPLACEMENT',
        evidence_scope='RETRAINED_V326_COHORT_MECHANISM_INTERVENTION_NEW_NATURAL_GAMES_NOT_NEW_LEARNING_CONFIRMATION')


def _read_stage(old):
    cpu, wall = process_time(),perf_counter()
    group=old['shared_supervision']['group_artifact'];outcome=old['continuation']['outcome_artifact']
    with np.load(group['file'],allow_pickle=False) as saved:
        roots=saved['roots'];saved_win=saved['terminal_win']
    with np.load(outcome['file'],allow_pickle=False) as saved:
        reward,win,status=saved['reward_return'],saved['win'],saved['status']
    if roots.shape!=(GROUPS,16) or reward.shape!=(GROUPS,MEMBERS) or not np.array_equal(win,saved_win):
        raise ValueError('V327 retained roots and paired suffix targets differ from the audited V326 groups')
    if np.any(status==0) or not np.all(np.isfinite(reward)) or not np.all(np.isfinite(win)):
        raise ValueError('V327 requires complete retained terminal labels without imputation')
    receipt=dict(counts=dict(group_files_read=1,outcome_files_read=1,
        rootgroups_read=GROUPS,retained_suffix_members_read=GROUPS*MEMBERS,
        selected_array_bytes=roots.nbytes+saved_win.nbytes+reward.nbytes+win.nbytes+status.nbytes),
        compressed_bytes_referenced=group['saved_bytes']+outcome['saved_bytes'],
        cpu_seconds=process_time()-cpu,wall_seconds=perf_counter()-wall)
    statuses={name:int(np.count_nonzero(status==code)) for name,code in (('WON',1),('LOST',-1),('CUTOFF',0))}
    return roots,reward,win,statuses,receipt


def _fit(leaf, roots, reward, win, runtime, arm):
    started,cpu=perf_counter(),process_time()
    epochs=[]
    for _ in range(EPOCHS):
        fit=(fit_win_supervision(leaf,roots,win,runtime,alpha=.0025) if arm=='WIN_ONLY'
            else fit_supervision(leaf,roots,reward,win,runtime,alpha=.0025))
        epochs.append(fit)
    return dict(method='REPLAY_GROUPED_'+arm,alpha=.0025,distinct_rootgroups=len(roots),
        epochs=EPOCHS,fitted_rootgroups=len(roots)*EPOCHS,replicates=2,epoch_receipts=epochs,
        **{field:sum_counts(e[field] for e in epochs) for field in
            ('learning_counts','normalization_counts','target_counts','representation_counts','setup_counts')},
        cpu_seconds=process_time()-cpu,seconds=perf_counter()-started)


def _evaluate(leaf, life, task, belief, runtime, engine, version=None):
    seeds=[evaluation_seed(life,task,i) for i in range(EPISODES)];before=leaf.updates
    result=(engine.evaluate_games(leaf,belief['estimated_p_four'],PROBABILITIES[task],seeds,depth=2,max_steps=8192)
        if version is None else evaluate_split(leaf,belief['estimated_p_four'],PROBABILITIES[task],seeds,runtime,max_steps=8192))
    if leaf.updates!=before:raise ValueError('V327 natural evaluation changed its frozen head')
    return dict(result,estimated_p_four=belief['estimated_p_four'],head_version=deepcopy(version),
        planner='H2',static_evaluation_valid=True)


def _metrics(prediction, reward, win):
    return {name:prediction_metrics(prediction['rewards'],prediction['probabilities'],reward,win,members)
        for name,members in (('train',FIT_MEMBERS),('validation',VALIDATION_MEMBERS))}


def _run_life(template, source, old, runtime, out, engine):
    life=old['lifecycle'];initial,heads,versions,setups={},{},{},{}
    for task in TASKS:
        original=old['initial'][task];version=original['head_version'];belief=original['planning_belief']
        first,setup=_restore_first(template,version,runtime)
        heads[task]={'FIRST_LOCAL':first};versions[task]={a:version for a in ARMS};setups[task]={'FIRST_LOCAL':setup}
        for arm in ARMS:
            leaf,setup=_new_head(template,'LOCAL_RISK',runtime,first);leaf.freeze()
            heads[task][arm]=leaf;setups[task][arm]=setup
        initial[task]=dict(context_id=original['context_id'],head_version=deepcopy(version),
            planning_belief=deepcopy(belief),evaluations={
                'SOURCE':_evaluate(template,life,task,belief,runtime,engine),
                'FIRST_LOCAL':_evaluate(first,life,task,belief,runtime,engine,version)})
    rounds={}
    for number in (1,2):
        rounds[str(number)]={}
        for task in TASKS:
            oldstage=old['rounds'][str(number)][task]
            roots,reward,win,statuses,read=_read_stage(oldstage)
            first=heads[task]['FIRST_LOCAL'];first_version=initial[task]['head_version']
            belief=initial[task]['planning_belief'];directory=out/'models'/f'life_{life}'/f"bank_{initial[task]['context_id']}"
            stage=dict(groups=GROUPS,replicas=MEMBERS,fit_members=list(FIT_MEMBERS),
                validation_members=list(VALIDATION_MEMBERS),epochs=EPOCHS,teacher_version=deepcopy(first_version),
                source_group_artifact=deepcopy(oldstage['shared_supervision']['group_artifact']),
                source_outcome_artifact=deepcopy(oldstage['continuation']['outcome_artifact']),
                source_read=read,terminal_status_counts=statuses,arms={})
            rounds[str(number)][task]=stage
            predictions={'FIRST':predict_components_batch(first,roots)}
            prediction_versions={'FIRST':deepcopy(first_version)}
            stage['first_prediction_metrics']=_metrics(predictions['FIRST'],reward,win)
            for arm in ARMS:
                leaf=heads[task][arm];previous_version=deepcopy(versions[task][arm]);before=leaf.updates
                before_key='FIRST' if number==1 else arm+'_BEFORE'
                if number!=1:
                    predictions[before_key]=predict_components_batch(leaf,roots)
                    prediction_versions[before_key]=previous_version
                previous=snapshot_weights(leaf);leaf.risk_weights.flags.writeable=True
                if arm=='JOINT_RETURN':leaf.reward_weights.flags.writeable=True
                fit=_fit(leaf,roots,np.ascontiguousarray(reward[:,FIT_MEMBERS]),
                    np.ascontiguousarray(win[:,FIT_MEMBERS]),runtime,arm);leaf.freeze()
                if leaf.updates-before!=GROUPS*EPOCHS:raise ValueError('V327 changed the fixed update quota')
                reward_unchanged=np.array_equal(leaf.reward_weights,first.reward_weights)
                if arm=='WIN_ONLY' and not reward_unchanged:raise ValueError('V327 WIN-only reward changed')
                version=save_version(leaf,source,life,initial[task]['context_id'],arm,number,
                    directory/f'{arm}_v{number}.npz',base=previous_version,previous=previous)
                del previous
                versions[task][arm]=version
                after_key=arm+'_AFTER';predictions[after_key]=predict_components_batch(leaf,roots)
                prediction_versions[after_key]=deepcopy(version)
                stage['arms'][arm]=dict(fit=fit,head_version=version,updates_before=before,
                    updates_after=leaf.updates,reward_unchanged=reward_unchanged,
                    prediction_keys=dict(before=before_key,after=after_key),prediction_metrics={
                        'before':_metrics(predictions[before_key],reward,win),
                        'after':_metrics(predictions[after_key],reward,win)},
                    evaluations=_evaluate(leaf,life,task,belief,runtime,engine,version))
            stage['win_weights_identical']=np.array_equal(heads[task]['WIN_ONLY'].risk_weights,heads[task]['JOINT_RETURN'].risk_weights)
            stage['win_table_parameters_compared']=int(first.risk_weights.size)
            stage['first_unchanged']=first.updates==first_version['updates'] and not first.reward_weights.flags.writeable and not first.risk_weights.flags.writeable
            if not stage['win_weights_identical'] or not stage['first_unchanged']:
                raise ValueError('V327 joint reward updates changed the matched WIN trajectory or immutable FIRST')
            labels=list(predictions)
            metadata=dict(schema='acfqp.joint_terminal_predictions.v327',lifecycle=life,parent=source['parent'],
                task=task,round=number,roots=GROUPS,snapshot_labels=labels,head_versions=prediction_versions,
                source_group_file=stage['source_group_artifact']['file'],source_outcome_file=stage['source_outcome_artifact']['file'],
                fit_members=list(FIT_MEMBERS),validation_members=list(VALIDATION_MEMBERS))
            stage['prediction_artifact']=_artifact(directory/f'R{number}_predictions.npz',metadata,
                **{field:np.vstack([predictions[label][field] for label in labels]) for field in PREDICTION_FIELDS})
            stage['unique_prediction_receipts']={key:_compact(value) for key,value in predictions.items()}
            print(json.dumps(dict(event='joint_terminal_stage_complete',lifecycle=life,task=task,round=number)),flush=True)
    row=dict(lifecycle=life,parent=source['parent'],initial=initial,rounds=rounds,
        head_setups=setups,final_head_versions=versions)
    _save(out/'lifecycle_receipts'/f'life_{life}.json',row)
    return row


def _run_parent(source, previous, out):
    cpu,wall,compiler=process_time(),perf_counter(),_child_cpu()
    runtime=out/'runtime'/f"parent_{source['parent']}";runtime.mkdir(parents=True,exist_ok=True)
    template,setup=load_leaf(source,runtime);engine=NativeValueStream(template,3278000000000+source['parent'],runtime)
    try:rows=[_run_life(template,source,old,runtime,out,engine) for old in previous['by_lifecycle'] if old['parent']==source['parent']]
    finally:engine.close()
    return dict(parent=source['parent'],lifecycles=rows,source_setup=setup,
        cpu_seconds=process_time()-cpu,compiler_cpu_seconds=_child_cpu()-compiler,wall_seconds=perf_counter()-wall)


def accounting(lives, parents, cpu, wall, inherited):
    stages=[row['rounds'][r][t] for row in lives for r in ('1','2') for t in TASKS]
    arms=[s['arms'][a] for s in stages for a in ARMS]
    evaluations=[v for row in lives for t in TASKS for v in row['initial'][t]['evaluations'].values()]+[a['evaluations'] for a in arms]
    predictions=[p for s in stages for p in s['unique_prediction_receipts'].values()]
    worker=sum(p['cpu_seconds'] for p in parents);compiler=sum(p['compiler_cpu_seconds'] for p in parents)
    component=worker+compiler+cpu
    return dict(new_training_raw_tiles=0,new_source_fits=0,new_FIRST_fits=0,
        source_training_repeated=False,first_adaptation_repeated=False,old_full_physics_audit_repeated=False,
        reused_target_cohort=True,new_target_learning_histories=False,equal_total_raw_efficiency_test=False,
        retained_member_reads=sum(s['source_read']['counts']['retained_suffix_members_read'] for s in stages),
        reused_fit_members_per_arm=len(stages)*GROUPS*2,reused_validation_members=len(stages)*GROUPS*2,
        new_fit_rootgroup_updates=sum(a['fit']['fitted_rootgroups'] for a in arms),
        per_arm={arm:dict(rootgroup_updates=sum(s['arms'][arm]['fit']['fitted_rootgroups'] for s in stages),
            fit_cpu_seconds=sum(s['arms'][arm]['fit']['cpu_seconds'] for s in stages),
            **{field:sum_counts(s['arms'][arm]['fit'][field] for s in stages) for field in
                ('learning_counts','normalization_counts','target_counts','representation_counts')}) for arm in ARMS},
        retained_target_read_counts=sum_counts(s['source_read']['counts'] for s in stages),
        retained_target_read_cpu_seconds=sum(s['source_read']['cpu_seconds'] for s in stages),
        new_prediction_roots=sum(p['roots'] for p in predictions),
        new_prediction_counts=sum_counts(p['counts'] for p in predictions),
        new_prediction_representation_counts=sum_counts(p['representation_counts'] for p in predictions),
        new_prediction_cpu_seconds=sum(p['cpu_seconds'] for p in predictions),
        win_table_parameters_compared=sum(s['win_table_parameters_compared'] for s in stages),
        new_evaluation_games=sum(len(e['game_summaries']) for e in evaluations),reused_evaluation_games=0,
        new_evaluation_environment_counts=sum_counts(e['counts']['environment'] for e in evaluations),
        new_evaluation_planning_counts=sum_counts(e['counts']['planning'] for e in evaluations),
        split_evaluation_representation_counts=sum_counts(e.get('representation_counts',{}) for e in evaluations),
        new_evaluation_cpu_seconds=sum(e['cpu_seconds'] for e in evaluations),
        new_head_files=len(arms),new_head_saved_bytes=sum(a['head_version']['saved_bytes'] for a in arms),
        prediction_files=len(stages),prediction_saved_bytes=sum(s['prediction_artifact']['saved_bytes'] for s in stages),
        worker_cpu_seconds=worker,compiler_cpu_seconds=compiler,coordinator_cpu_seconds=cpu,
        new_experiment_component_cpu_seconds=component,wall_seconds=wall,
        inherited_source_v326_actual_full_cpu_seconds=inherited,
        economic_source_v326_and_experiment_component_cpu_seconds=inherited+component,
        cost_scope='All retained reads/restores/fits/predictions/saves/new games/compiler/coordinator once; full execution '
            'adds final serialization/shutdown. Actual SOURCE/V326 execution inherited once including its failed scientific '
            'intervention; no old fitting/physics audits or game receipts reused. Audit separate; historical dynamics/failed-attempt CPU unknown.')


def run(source_summary, output):
    cpu,wall=process_time(),perf_counter();out=Path(output).resolve();out.mkdir(parents=True,exist_ok=True)
    if (out/'configuration.json').exists():raise FileExistsError('V327 is already frozen')
    source_path=Path(source_summary).resolve();previous=json.loads(source_path.read_text())
    prior_audit=json.loads((source_path.parent/'audit.json').read_text());execution=json.loads((source_path.parent/'execution.json').read_text())
    if previous['status']!='EXPERIMENT_COMPLETE' or not prior_audit['independent_valid'] or execution['exit_code']!=0:
        raise ValueError('V327 requires the audited complete V326 learning cohort and suffixes')
    inherited=json.loads((source_path.parent/'audit_costs.json').read_text())['full_economic_source_and_experiment_cpu_seconds']
    settings=configuration(source_path);_save(out/'configuration.json',settings);parents=[]
    with ProcessPoolExecutor(max_workers=4) as pool:
        for job in as_completed([pool.submit(_run_parent,s,previous,out) for s in previous['source_provenance']['parents']]):
            result=job.result();parents.append(result)
            _save(out/f"parent_{result['parent']}_receipt.json",{k:v for k,v in result.items() if k!='lifecycles'})
    parents.sort(key=lambda p:p['parent']);lives=sorted((r for p in parents for r in p['lifecycles']),key=lambda r:r['lifecycle'])
    analysis=summarize(lives)
    result=dict(schema='acfqp.joint_terminal.v327',status='EXPERIMENT_COMPLETE' if analysis['complete_game_endpoints'] else 'HOLD_CUTOFF',
        scientific_gate='FIXED_FIRST_TERMINAL_REGRESSION_LAST_MECHANISM_TEST_NOT_U006',settings=settings,
        source_summary=str(source_path),source_provenance=previous['source_provenance'],by_lifecycle=lives,
        parent_receipts=[{k:v for k,v in p.items() if k!='lifecycles'} for p in parents],summary=analysis,
        accounting=accounting(lives,parents,process_time()-cpu,perf_counter()-wall,inherited))
    _save(out/'summary.json',result)
    print(json.dumps(dict(event='joint_terminal_complete',status=result['status'],primary=analysis['primary_status'],
        retained=analysis['retained_improvement_supported'],route=analysis['next_route'])),flush=True)
    return result
