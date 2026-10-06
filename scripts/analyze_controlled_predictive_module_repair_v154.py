"""Independently audit fixed-label module repairs and fresh paired full games."""
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
import json
from pathlib import Path
import sys
from time import perf_counter

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'src'))
from scripts import analyze_controlled_predictive_policy_modules_v151 as prior
from scripts import analyze_controlled_predictive_module_replication_v152 as replication
from scripts import analyze_controlled_predictive_module_diagnosis_v153 as diagnosis

LIVES,QUERIES=prior.LIVES,prior.QUERIES
ARMS=('H2','ALT','OLD','REPAIR_H2','REPAIR_GATE')
LEARNED=ARMS[2:];REPAIRS=ARMS[3:]
BASE,REPLICAS,MAX_STEPS,WORKERS=154*100000000,16,2000,4
CONTRASTS={'REPAIR_H2-OLD':('REPAIR_H2','OLD'),'REPAIR_GATE-OLD':('REPAIR_GATE','OLD'),
    'REPAIR_GATE-REPAIR_H2':('REPAIR_GATE','REPAIR_H2'),
    **{f'{arm}-{baseline}':(arm,baseline) for arm in LEARNED for baseline in ('H2','ALT')},'ALT-H2':('ALT','H2')}
mean,close,add_checks,read=prior.mean,prior.close,prior.add_checks,prior.read
logical_result=replication.logical_result


def evaluation_seed(life,replica):
    return BASE+90000000+life*1000000+replica


def expected_rosters():
    physical={};logical=[]
    for life in LIVES:
        for query in QUERIES:
            for arm in ARMS:
                for replica in range(REPLICAS):
                    q=('risk8' if query=='risk1' else 'risk1') if arm=='ALT' else query
                    actual='H2' if arm=='ALT' else arm;identifier=f'{life}:{q}:{actual}:{replica}'
                    physical[identifier]=dict(physical_id=identifier,life=life,query=q,arm=actual,replica=replica,
                        method='H2' if actual=='H2' else 'LEARN8',duration=0 if actual=='H2' else 8,seed=evaluation_seed(life,replica))
                    logical.append(dict(life=life,query=query,arm=arm,replica=replica,seed=evaluation_seed(life,replica),physical_id=identifier))
    return physical,logical


def roster_checks(physical,logical):
    ep,el=expected_rosters();key=lambda r:(r['life'],r['query'],r['arm'],r['replica'])
    return dict(physical_roster=len(physical)==512 and {r['physical_id']:r for r in physical}==ep,
        logical_roster=len(logical)==640 and {key(r):r for r in logical}=={key(r):r for r in el},
        alias_reuse=Counter(r['physical_id'] for r in logical)==Counter(r['physical_id'] for r in el))


def aggregate(indexed,valid):
    arms={};comparisons={}
    for arm in ARMS:
        arms[arm]={}
        for query in QUERIES:
            cells=[]
            for life in LIVES:
                keys=[(life,query,arm,r) for r in range(REPLICAS)];rows=[indexed[k]['result'] for k in keys if k in indexed]
                complete=all(k in indexed and valid.get(k,False) and indexed[k]['result']['status'] in ('WON','LOST') for k in keys)
                cells.append(dict(life=life,complete=complete,games=len(rows),statuses=dict(Counter(r['status'] for r in rows)),
                    wins=sum(r['status']=='WON' for r in rows),means={name:mean(r[name] for r in rows) if complete else None for name in ('utility','score','steps')}))
            arms[arm][query]=dict(lifecycles=cells,complete=all(c['complete'] for c in cells),wins=sum(c['wins'] for c in cells),
                games=sum(c['games'] for c in cells),means={name:mean(c['means'][name] for c in cells) for name in ('utility','score','steps')})
    for name,(left,right) in CONTRASTS.items():
        comparisons[name]={q:replication.paired_contrast(indexed,valid,lambda life,replica,q=q,left=left,right=right:
            ((life,q,left,replica),(life,q,right,replica))) for q in QUERIES}
    return dict(arms=arms,comparisons=comparisons,primary_complete=all(c['complete'] for arm in arms.values() for c in arm.values()))


def training_examples(capsule):
    """Read retained result components once; no old transition replay or fitting."""
    roots={r['root_id']:r for r in capsule['roots']};outcomes={key:{} for key in roots};seen=[];work=Counter()
    checks=dict(training_branch_roster=True,training_branch_identity=True,training_terminal_labels=True)
    for trace in capsule['source_traces']:
        work['trace_files_read']+=1
        for row in prior.old.read_rows(trace['path']):
            work['branch_records_read']+=1;work['retained_environment_transitions']+=row['result']['steps'];root=roots[row['root_id']];suffix=row['suffix'];mode=row['mode'];seen.append(row['branch_id'])
            checks['training_branch_identity'] &= all(row[k]==v for k,v in dict(life=trace['life'],query=root['query'],
                source_method=root['source_method'],slot=root['slot'],root_board=root['board'],seed=diagnosis.branch_seed(root,suffix),
                branch_id=f'{root["root_id"]}:{suffix}:{mode}').items())
            result=row['result'];checks['training_terminal_labels'] &= result['status'] in ('WON','LOST') and result['utility'] is not None
            checks['training_terminal_labels'] &= len(result['components'])==3 and close(result['components'][0],result['score']/2048) and result['components'][1:]==[int(result['status']=='LOST'),int(result['status']=='WON')]
            outcomes[root['root_id']].setdefault(suffix,{})[mode]=result['components']
    expected=[f'{r["root_id"]}:{suffix}:{mode}' for r in capsule['roots'] for suffix in range(16) for mode in diagnosis.MODES]
    checks['training_branch_roster'] &= len(seen)==len(set(seen))==4096 and set(seen)==set(expected)
    examples=[]
    for root in capsule['roots']:
        targets={}
        for arm,high,low in (('REPAIR_H2','M_H2','H_H2'),('REPAIR_GATE','M_GATE','H_GATE')):
            targets[arm]=[mean(outcomes[root['root_id']][s][high][j]-outcomes[root['root_id']][s][low][j] for s in range(16)) for j in range(3)]
        examples.append(dict(**{k:root[k] for k in ('root_id','life','query','source_method','slot','board')},suffixes=16,targets=targets))
    transitions=work['retained_environment_transitions']
    return examples,dict(retained_rows_read=work['branch_records_read'],retained_environment_transitions=transitions,
        new_training_environment_samples=0,matched_budget_views={arm:transitions for arm in REPAIRS}),checks


def expected_settings():
    return dict(lifecycles=list(LIVES),queries=QUERIES,arms=list(ARMS),repairs=list(REPAIRS),
        reference='V151 final LEARN8; unchanged through V153 label generation and this single update',
        training_roots=64,roots_per_history_query=8,suffixes_per_root=16,retained_training_branches=4096,
        root_order='V153 frozen order: history, query, H2 then LEARN8 source, slot0..3; all accepted and declined roots',
        targets={'REPAIR_H2':'mean components(M_H2-H_H2)','REPAIR_GATE':'mean components(M_GATE-H_GATE)'},
        initialization='each repair independently loads the same OLD cp4 weights and historical update count',
        learner='unchanged V151 RootConsequences with root unary/pair features plus bias',
        epochs=32,alpha=.1,update='warm normalized LMS over all eight root means per history/query; no old V151 labels',
        new_training_updates=4096,new_training_environment_samples=0,
        accounting='both repair views charge the entire retained V153 physical pool; do not double count physical acquisition',
        evaluation_replicas=REPLICAS,physical_evaluation_games=512,logical_evaluation_games=640,
        frozen_old_models=8,frozen_repair_models=16,
        seed_rule='BASE+90000000+life*1000000+replica; common across queries and arms',
        baseline_reuse='ALT uses opposite-query H2 physical trajectory; utility recomputed under target query',
        gate='unchanged strict positive advantage; other policy for eight committed steps, otherwise own H2 for one step',
        representation='SINGLE',p_four=.1,max_steps=MAX_STEPS,workers=WORKERS,version_base=BASE,
        primary='fresh full-game utility; equal16 replicas within history then equal four histories',
        contrasts=list(CONTRASTS),blocks=[[0,3],[4,7],[8,11],[12,15]],
        conditional_seed_ci95='paired mean +/-1.96*sqrt(sum_l(sample_variance(delta_l)/16)/16); conditional on four frozen histories',
        incomplete='retain all cutoff games and costs; affected comparisons incomplete, no replacement',
        frozen_policy='protocol and rosters before fitting; all24 models frozen before evaluation; no tuning or optional stopping')


def source_models(capsule,directory):
    origin=Path(capsule['source_run_ref']).parent
    source_run=read(capsule['source_run_ref']);source_capsule=read(origin/'source_capsule.json')
    source_analysis=read(origin/'analysis.json');source_frozen=read(capsule['source_frozen_ref'])
    references={(m['life'],m['query']):m for m in source_capsule['models']};models={}
    checks=dict(source_complete=source_run['status']=='complete' and source_analysis['complete'] and source_analysis['primary_complete'],
        source_bindings=capsule['snapshots']==source_capsule['snapshots'] and capsule['roots']==source_frozen['roots'] and
        Path(capsule['source_frozen_ref'])==origin/'frozen_inputs.json',source_model_roster=True,source_model_copies=True)
    checks['source_bindings'] &= capsule['source_traces']==[dict(life=l['life'],path=str(origin/l['branch_trace'])) for l in source_run['lifecycles']]
    checks['source_bindings'] &= len(capsule['roots'])==64 and [(r['life'],r['query'],r['source_method'],r['slot']) for r in capsule['roots']]==[
        (l,q,s,slot) for l in LIVES for q in QUERIES for s in diagnosis.SOURCES for slot in range(4)]
    for meta in capsule['models']:
        life,query=meta['life'],meta['query'];reference=references[life,query];path=directory/meta['model_ref']
        payload=read(path);original=read(meta['source_model_ref']);key=life,query,'OLD'
        checks['source_model_roster'] &= key not in models and meta['arm']=='OLD'
        checks['source_model_copies'] &= Path(meta['source_model_ref'])==origin/reference['model_ref'] and payload==original and payload['frozen']
        checks['source_model_copies'] &= meta['frozen_state']==reference['frozen_state']==prior.local.prior.state(payload) and meta['model_bytes']==path.stat().st_size
        models[key]=dict(metadata=meta,payload=payload,weights={int(r[0]):tuple(r[1:]) for r in payload['weights']})
    checks['source_model_roster'] &= len(capsule['models'])==len(models)==8 and set(models)=={(l,q,'OLD') for l in LIVES for q in QUERIES}
    return models,checks


def audit_fits(examples,metadata,models,directory):
    checks=dict(fit_model_roster=True,fit_initialization=True,fit_roots=True,fit_weights=True,fit_counts=True,fit_storage=True)
    seen=[];new_models={};diagnostics=[]
    for meta in metadata:
        life,query,arm=meta['life'],meta['query'],meta['arm'];key=life,query,arm;seen.append(key)
        original=models[life,query,'OLD'];before=original['metadata']['frozen_state'];selected=[e for e in examples if e['life']==life and e['query']==query]
        targets=[dict(board=e['board'],target=e['targets'][arm]) for e in selected]
        expected=prior.fit_oracle(targets,original['weights'],passes=32,alpha=.1);updates=before['updates']+expected['updates']
        path=directory/meta['model_ref'];payload=read(path);n=len(expected['weights']);save_counts=Counter(checkpoint_saves=1,checkpoint_saved_addresses=n,checkpoint_saved_parameters=3*n)
        checks['fit_initialization'] &= meta['source_model_ref']==original['metadata']['model_ref'] and meta['before']==before
        checks['fit_roots'] &= len(selected)==8 and meta['root_ids']==[e['root_id'] for e in selected] and meta['new_updates']==expected['updates']==256
        checks['fit_weights'] &= prior.state_matches(meta['frozen_state'],expected['weights'],updates) and prior.local.model_matches(payload,dict(weights=expected['weights'],updates=updates))
        checks['fit_counts'] &= Counter(meta['fit_counts'])==expected['counts'] and Counter(meta['total_counts'])==expected['counts']+save_counts
        checks['fit_counts'] &= Counter(payload['counts'])==Counter(meta['total_counts']) and Counter(meta['setup_counts'])==diagnosis.model_setup(len(original['weights']))
        checks['fit_counts'] &= payload['setup_counts']==meta['setup_counts'] and close(payload['setup_seconds'],meta['setup_seconds'])
        checks['fit_storage'] &= meta['model_bytes']==path.stat().st_size and payload['storage']==dict(weight_addresses=n,weight_parameters=3*n,numeric_weight_bytes=24*n,numeric_address_bytes=8*n)
        new_models[key]=dict(metadata=meta,payload=payload,weights={int(r[0]):tuple(r[1:]) for r in payload['weights']})
        targets_by_arm={target_arm:[prior.utility(e['targets'][target_arm],query) for e in selected] for target_arm in REPAIRS}
        predictions={name:[prior.utility(prior.predict(e['board'],weights),query) for e in selected] for name,weights in (
            ('before',original['weights']),('after',expected['weights']))}
        diagnostics.append(dict(life=life,query=query,arm=arm,roots=8,new_updates=expected['updates'],
            in_sample_mse={target_arm:{name:mean((p-y)**2 for p,y in zip(values,labels)) for name,values in predictions.items()} for target_arm,labels in targets_by_arm.items()}))
    checks['fit_model_roster'] &= len(seen)==len(set(seen))==16 and set(seen)=={(l,q,a) for l in LIVES for q in QUERIES for a in REPAIRS}
    return new_models,checks,diagnostics


def audit_lifecycle(lifecycle,source,models,physical_roster,directory):
    life=lifecycle['life'];directory=Path(directory);seen=[];physical={};valid={};teacher_counts={q:Counter() for q in QUERIES}
    model_counts={(q,a):Counter() for q in QUERIES for a in LEARNED}
    checks=dict(physical_records=True,physical_accounting=True,teacher_bank=True,teacher_totals=True,
        loaded_model_roster=True,loaded_models_frozen=True,model_prediction_counts=True,model_setup=True)
    costs=dict(physical_games=0,environment_counts=Counter(),policy_counts=Counter(),statuses=Counter(),decision_seconds=0.,
        analysis_replay_swipes=0,physical_cells={},model_accounting=[],teacher_accounting=[])
    for row in prior.old.read_rows(directory/lifecycle['control_trace']):
        identifier=row['physical_id'];seen.append(identifier);reference=physical_roster[identifier]
        checks['physical_records'] &= all(row[k]==v for k,v in reference.items()) and row['life']==life and row['max_steps']==MAX_STEPS
        query,arm=row['query'],row['arm'];weights=models[query,arm]['weights'] if arm in LEARNED else {}
        local_checks,swipes,_=prior.replay_game(row,weights);add_checks(checks,local_checks);costs['analysis_replay_swipes']+=swipes
        result=row['result'];valid[identifier]=all(local_checks.values());physical[identifier]=dict(result={k:result[k] for k in ('score','steps','status','components','utility')})
        costs['physical_games']+=1;costs['decision_seconds']+=result['decision_seconds'];costs['statuses'][result['status']]+=1
        for name in ('environment_counts','policy_counts'):costs[name].update(result[name])
        prior.add_policy_work(teacher_counts,result['policy_counts'])
        if arm in LEARNED:model_counts[query,arm].update({k[len('learner_'):]:v for k,v in result['policy_counts'].items() if k.startswith('learner_')})
        cell=costs['physical_cells'].setdefault(f'{query}:{arm}',dict(query=query,arm=arm,games=0,statuses=Counter(),environment_counts=Counter(),policy_counts=Counter(),decision_seconds=0.))
        cell['games']+=1;cell['statuses'][result['status']]+=1;cell['decision_seconds']+=result['decision_seconds']
        for name in ('environment_counts','policy_counts'):cell[name].update(result[name])
    checks['physical_records'] &= len(seen)==len(set(seen))==128 and set(seen)==set(physical_roster)
    checks['physical_accounting'] &= lifecycle['physical_games']==len(seen) and all(Counter(lifecycle[name])==costs[name] for name in ('environment_counts','policy_counts','statuses'))
    loaded=[]
    for meta in lifecycle['models']:
        key=meta['query'],meta['arm'];loaded.append(key);model=models[key]
        checks['loaded_models_frozen'] &= meta['model_ref']==model['metadata']['model_ref'] and meta['before']==meta['after']==model['metadata']['frozen_state']
        checks['model_prediction_counts'] &= Counter(meta['counts'])==model_counts[key]
        checks['model_setup'] &= Counter(meta['setup_counts'])==diagnosis.model_setup(len(model['weights']))
        costs['model_accounting'].append(dict(life=life,**meta))
    checks['loaded_model_roster'] &= len(loaded)==len(set(loaded))==6 and set(loaded)==set(model_counts)
    for query in QUERIES:
        teacher=lifecycle['teacher_bank'][query]
        checks['teacher_bank'] &= prior.h1.teacher_analysis.teacher_loads_valid(teacher['loads'],source,'SINGLE',query)
        checks['teacher_bank'] &= teacher['parent_before']==teacher['parent_after']==prior.planning.previous.model_state(source,query,'PARENT',0)
        checks['teacher_bank'] &= teacher['leaf_before']==teacher['leaf_after']==prior.planning.expected_model_state(source,query,'SINGLE')
        checks['teacher_totals'] &= Counter(teacher['total_counts'])==teacher_counts[query]
        costs['teacher_accounting'].append(dict(life=life,query=query,**teacher))
    print(json.dumps(dict(event='audited_lifecycle',life=life,physical_games=len(seen),replayed_swipes=costs['analysis_replay_swipes'])),flush=True)
    return dict(life=life,checks=checks,physical=physical,valid=valid,costs=costs)


def analyze(directory):
    started=perf_counter();directory=Path(directory).resolve()
    run,capsule,frozen,training=(read(directory/name) for name in ('run.json','source_capsule.json','frozen_inputs.json','frozen_training.json'))
    checks=dict(settings=run['settings']==expected_settings(),frozen_inputs=frozen['status']=='frozen' and not frozen['lifecycles'] and
        all(frozen[k]==run[k] for k in ('settings','inherited_cost_refs')),frozen_training=run['training']==training,
        inherited_costs=run['inherited_cost_refs']==capsule['cost_refs'],lifecycle_roster=len(run['lifecycles'])==4 and {r['life'] for r in run['lifecycles']}==set(LIVES),
        training_root_roster=frozen['training_root_ids']==[r['root_id'] for r in capsule['roots']])
    add_checks(checks,roster_checks(frozen['physical_roster'],frozen['logical_roster']))
    models,local_checks=source_models(capsule,directory);add_checks(checks,local_checks)
    examples,read_work,local_checks=training_examples(capsule);add_checks(checks,local_checks)
    checks['training_labels']=read(directory/training['examples_ref'])==examples
    checks['training_read_work']=all(training['read_work'][k]==v for k,v in read_work.items())
    fitted,local_checks,fit_diagnostics=audit_fits(examples,training['models'],models,directory);add_checks(checks,local_checks);models.update(fitted)
    inherited={path:read(path) for path in {ref['path'] for ref in capsule['cost_refs']}}
    checks['inherited_fields']=all(all(field in inherited[ref['path']] for field in ref['fields']) for ref in capsule['cost_refs'])
    sources={s['life']:s for s in capsule['snapshots']};results=[];physical={};valid={}
    with ProcessPoolExecutor(max_workers=WORKERS) as pool:
        tasks=[pool.submit(audit_lifecycle,lifecycle,sources[lifecycle['life']],
            {(q,a):models[lifecycle['life'],q,a] for q in QUERIES for a in LEARNED},
            {r['physical_id']:r for r in frozen['physical_roster'] if r['life']==lifecycle['life']},directory) for lifecycle in run['lifecycles']]
        for task in as_completed(tasks):results.append(task.result())
    results.sort(key=lambda r:r['life'])
    costs=dict(physical_games=0,logical_games=640,alias_references=128,environment_counts=Counter(),policy_counts=Counter(),statuses=Counter(),
        decision_seconds=0.,analysis_replay_swipes=0,physical_cells={},model_accounting=[],teacher_accounting=[],
        training=training,analysis_training_reads=read_work,analysis_fit_oracle_updates=sum(d['new_updates'] for d in fit_diagnostics),
        analysis_training_diagnostic_predictions=sum(2*d['roots'] for d in fit_diagnostics),
        analysis_model_files_read=32,analysis_inherited_files_read=len(inherited),
        source_preparation_model_reads=8,source_model_copies=8,runtime_model_loads=16+sum(len(l['models']) for l in run['lifecycles']),
        frozen_models=dict(files=len(models),bytes=sum(m['metadata']['model_bytes'] for m in models.values())),
        new_training_updates=sum(m['new_updates'] for m in training['models']),new_training_environment_samples=0)
    for result in results:
        add_checks(checks,result['checks']);physical.update(result['physical']);valid.update(result['valid']);local_costs=result['costs']
        for name in ('physical_games','decision_seconds','analysis_replay_swipes'):costs[name]+=local_costs[name]
        for name in ('environment_counts','policy_counts','statuses'):costs[name].update(local_costs[name])
        for name in ('model_accounting','teacher_accounting'):costs[name].extend(local_costs[name])
        for key,cell in local_costs['physical_cells'].items():
            target=costs['physical_cells'].setdefault(key,dict(query=cell['query'],arm=cell['arm'],games=0,statuses=Counter(),
                environment_counts=Counter(),policy_counts=Counter(),decision_seconds=0.))
            for name in ('games','decision_seconds'):target[name]+=cell[name]
            for name in ('statuses','environment_counts','policy_counts'):target[name].update(cell[name])
    checks['full_physical_roster']=costs['physical_games']==len(physical)==512 and set(physical)=={r['physical_id'] for r in frozen['physical_roster']}
    logical={};logical_valid={}
    for row in frozen['logical_roster']:
        key=tuple(row[k] for k in ('life','query','arm','replica'));identifier=row['physical_id']
        logical[key]=dict(result=logical_result(physical[identifier]['result'],row['query']),physical_id=identifier);logical_valid[key]=valid[identifier]
    outcome=aggregate(logical,logical_valid);primary_complete=outcome.pop('primary_complete');complete=run['status']=='complete' and all(checks.values())
    costs['new_environment_samples']=costs['environment_counts'].get('sampled_transitions',0)
    return dict(schema='acfqp.module_repair.v154.analysis',complete=complete,primary_complete=complete and primary_complete,
        checks=checks,**outcome,training_diagnostics=fit_diagnostics,costs=costs,inherited_cost_refs=run['inherited_cost_refs'],seconds=perf_counter()-started,
        estimand='Fresh full-game utility after one fixed-label repair, paired with the unchanged OLD gate and both policy baselines.',
        uncertainty='Pointwise conditional_seed_ci95 describes new seed variation conditional on four fixed learned histories; it does not estimate training-history population uncertainty.',
        limitations='Training MSE is in-sample and uses uncertain retained suffix means. REPAIR_GATE labels use the frozen OLD continuation, not the repaired policy continuation. All physical acquisition is charged once; both repair budget views include the full retained pool.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input','--directory',dest='input',type=Path,default=ROOT/'reports/controlled_predictive_module_repair_v154')
    args=parser.parse_args();result=analyze(args.input)
    (args.input/'analysis.json').write_text(json.dumps(result,separators=(',',':'))+'\n')
    print(json.dumps(dict(complete=result['complete'],primary_complete=result['primary_complete'],checks=len(result['checks']),
        failed=[k for k,v in result['checks'].items() if not v],seconds=result['seconds'])),flush=True)
    raise SystemExit(0 if result['complete'] else 1)
