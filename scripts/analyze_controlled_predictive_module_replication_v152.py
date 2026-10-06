"""Audit frozen module checkpoints on common fresh seeds with physical reuse."""
import argparse
from collections import Counter
import json
import math
from pathlib import Path
import sys
from time import perf_counter

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'src'))
from scripts import analyze_controlled_predictive_policy_modules_v151 as prior

LIVES,QUERIES,METHODS=prior.LIVES,prior.QUERIES,prior.METHODS
BASE,REPLICAS,CHECKPOINTS,MAX_STEPS,WORKERS=152*100000000,16,tuple(range(5)),2000,4
DURATIONS=prior.DURATIONS
CONTRASTS={'LEARN1-H2':('LEARN1','H2'),'LEARN8-H2':('LEARN8','H2'),'LEARN8-LEARN1':('LEARN8','LEARN1'),
    'ALT-H2':('ALT','H2'),'LEARN1-ALT':('LEARN1','ALT'),'LEARN8-ALT':('LEARN8','ALT')}
INCREMENTS=((0,1),(1,2),(2,3),(3,4),(0,4))
mean,close,add_checks,read=prior.mean,prior.close,prior.add_checks,prior.read


def expected_settings():
    return dict(lifecycles=list(LIVES),queries=QUERIES,durations=[1,8],methods=list(METHODS),
        checkpoints=list(CHECKPOINTS),evaluation_replicas=REPLICAS,physical_evaluation_games=1152,
        logical_evaluation_games=2560,physical_baseline_games=128,physical_learned_games=1024,
        frozen_models=80,loaded_learned_models=64,new_training_transitions=0,new_training_updates=0,
        representation='SINGLE',p_four=.1,max_steps=MAX_STEPS,workers=WORKERS,version_base=BASE,
        seed_rule='BASE+90000000+life*1000000+replica; identical across queries, methods and checkpoints',
        learner='unchanged frozen V151 RootConsequences; no fitting or new labels',
        gate='strict positive learned total advantage; commit full duration; otherwise own H2 one step',
        baseline_reuse='one physical H2 per life/query/replica; ALT references other policy and rescores target utility',
        checkpoint_zero_reuse='alias own H2 only after verifying frozen empty weights and zero updates',
        accounting='charge physical traces once; aliases carry no extra environment or policy work; no claimed runtime for skipped zero-model predictions',
        primary='all five checkpoints; equal 16 replicas within each of four frozen histories then equal histories',
        contrasts=['LEARN1-H2','LEARN8-H2','LEARN8-LEARN1','ALT-H2','LEARN1-ALT','LEARN8-ALT'],
        increments=['0->1','1->2','2->3','3->4','0->4'],
        blocks=[[0,3],[4,7],[8,11],[12,15]],
        conditional_seed_ci95='paired mean +/-1.96*sqrt(sum_l(sample_variance(delta_l)/16)/16); conditional on four frozen histories',
        incomplete='retain every cutoff and its cost; affected comparisons and intervals incomplete, no replacement',
        frozen_policy='no evaluation-dependent refit, hyperparameter choice, checkpoint choice or early stopping')


def evaluation_seed(life,replica):
    return BASE+90000000+life*1000000+replica


def physical_key(life,query,checkpoint,method,replica):
    if method=='H2' or (checkpoint==0 and method in DURATIONS):return life,query,-1,'H2',replica
    if method=='ALT':return life,('risk8' if query=='risk1' else 'risk1'),-1,'H2',replica
    return life,query,checkpoint,method,replica


def zero_checkpoint_valid(payload):
    return payload['frozen'] and payload['updates']==0 and payload['weights']==[]


def logical_result(result,query):
    """Recompose utility for the logical target query; never copy ALT utility."""
    return dict(score=result['score'],steps=result['steps'],status=result['status'],components=list(result['components']),
        utility=None if result['status']=='CUTOFF' else prior.utility(result['components'],query))


def paired_contrast(indexed,valid,pairs):
    cells=[]
    for life in LIVES:
        deltas=[]
        for replica in range(REPLICAS):
            left,right=pairs(life,replica)
            complete=all(key in indexed and valid.get(key,False) and indexed[key]['result']['status'] in ('WON','LOST') for key in (left,right))
            deltas.append(indexed[left]['result']['utility']-indexed[right]['result']['utility'] if complete else None)
        blocks=[dict(replica_start=start,replica_end=start+3,complete=all(x is not None for x in deltas[start:start+4]),
            mean=mean(deltas[start:start+4])) for start in range(0,16,4)]
        cells.append(dict(life=life,complete=all(x is not None for x in deltas),replica_deltas=deltas,mean=mean(deltas),blocks=blocks))
    complete=all(c['complete'] for c in cells);average=mean(c['mean'] for c in cells)
    variances=[sum((x-c['mean'])**2 for x in c['replica_deltas'])/(REPLICAS-1) for c in cells] if complete else []
    se=math.sqrt(sum(variances)/REPLICAS/len(LIVES)**2) if complete else None
    interval=[average-1.96*se,average+1.96*se] if complete else None
    return dict(lifecycles=cells,complete=complete,mean=average,conditional_seed_se=se,conditional_seed_ci95=interval,
        positive=sum(c['mean'] is not None and c['mean']>0 for c in cells),negative=sum(c['mean'] is not None and c['mean']<0 for c in cells),
        zero=sum(c['mean']==0 for c in cells),blocks=[dict(replica_start=b*4,replica_end=b*4+3,
            complete=all(c['blocks'][b]['complete'] for c in cells),mean=mean(c['blocks'][b]['mean'] for c in cells),
            positive_histories=sum(c['blocks'][b]['mean'] is not None and c['blocks'][b]['mean']>0 for c in cells)) for b in range(4)])


def aggregate(indexed,valid):
    curves={}
    for checkpoint in CHECKPOINTS:
        methods={};comparisons={}
        for method in METHODS:
            methods[method]={}
            for query in QUERIES:
                cells=[]
                for life in LIVES:
                    keys=[(life,query,checkpoint,method,r) for r in range(REPLICAS)];rows=[indexed[k]['result'] for k in keys if k in indexed]
                    complete=all(k in indexed and valid.get(k,False) and indexed[k]['result']['status'] in ('WON','LOST') for k in keys)
                    cells.append(dict(life=life,complete=complete,games=len(rows),statuses=dict(Counter(r['status'] for r in rows)),
                        wins=sum(r['status']=='WON' for r in rows),means={name:mean(r[name] for r in rows) if complete else None for name in ('utility','score','steps')}))
                methods[method][query]=dict(lifecycles=cells,complete=all(c['complete'] for c in cells),
                    wins=sum(c['wins'] for c in cells),games=sum(c['games'] for c in cells),
                    means={name:mean(c['means'][name] for c in cells) for name in ('utility','score','steps')})
        for name,(left,right) in CONTRASTS.items():
            comparisons[name]={q:paired_contrast(indexed,valid,lambda life,replica,q=q:
                ((life,q,checkpoint,left,replica),(life,q,checkpoint,right,replica))) for q in QUERIES}
        curves[str(checkpoint)]=dict(methods=methods,comparisons=comparisons)
    increments={f'{before}->{after}':{m:{q:paired_contrast(indexed,valid,lambda life,replica,q=q,m=m:
        ((life,q,after,m,replica),(life,q,before,m,replica))) for q in QUERIES} for m in METHODS} for before,after in INCREMENTS}
    return dict(learning_curves=curves,checkpoint_increments=increments,
        primary_complete=all(c['complete'] for cp in curves.values() for m in cp['methods'].values() for c in m.values()))


def expected_rosters():
    physical={};logical=[]
    for life in LIVES:
        for query in QUERIES:
            for checkpoint in CHECKPOINTS:
                for method in METHODS:
                    for replica in range(REPLICAS):
                        key=physical_key(life,query,checkpoint,method,replica)
                        l,q,c,m,r=key;identifier=f'{l}:{q}:{c}:{m}:{r}'
                        physical[identifier]=dict(physical_id=identifier,life=l,query=q,checkpoint=c,method=m,
                            duration=DURATIONS.get(m,0),replica=r,seed=evaluation_seed(l,r))
                        logical.append(dict(life=life,query=query,checkpoint=checkpoint,method=method,
                            duration=DURATIONS.get(method,1 if method=='ALT' else 0),replica=replica,
                            seed=evaluation_seed(life,replica),physical_id=identifier))
    return physical,logical


def logical_roster_checks(physical_roster,logical_roster):
    expected_physical,expected_logical=expected_rosters()
    physical={r['physical_id']:r for r in physical_roster}
    key=lambda r:(r['life'],r['query'],r['checkpoint'],r['method'],r['replica'])
    logical={key(r):r for r in logical_roster}
    return dict(physical_roster=len(physical_roster)==len(physical)==1152 and physical==expected_physical,
        logical_roster=len(logical_roster)==len(logical)==2560 and logical=={key(r):r for r in expected_logical},
        physical_reuse=Counter(r['physical_id'] for r in logical_roster)==Counter(r['physical_id'] for r in expected_logical))


def source_models(capsule,directory):
    origin=Path(capsule['source_run_ref']).parent;source_run=read(capsule['source_run_ref'])
    source_analysis=read(origin/'analysis.json');source_capsule=read(origin/'source_capsule.json')
    records={r['life']:r for r in source_run['lifecycles']};models={};read_bytes=0
    checks=dict(source_complete=source_run['status']=='complete' and source_analysis['complete'] and source_analysis['primary_complete'],
        source_teacher_bindings=capsule['snapshots']==source_capsule['snapshots'],source_model_roster=True,
        source_model_bindings=True,frozen_model_copies=True,zero_checkpoint_models=True)
    for item in capsule['models']:
        life,query,checkpoint,duration=(item[k] for k in ('life','query','checkpoint','duration'))
        key=life,query,checkpoint,duration;reference=records[life]['checkpoints'][checkpoint]['models'][query][str(duration)]
        path=directory/item['model_ref'];payload=read(path);original=read(item['source_model_ref']);read_bytes+=path.stat().st_size+Path(item['source_model_ref']).stat().st_size
        checks['source_model_roster'] &= key not in models
        checks['source_model_bindings'] &= Path(item['source_model_ref'])==origin/reference['model_ref'] and item['frozen_state']==reference['frozen_state']==prior.local.prior.state(original)
        checks['frozen_model_copies'] &= payload==original and payload['frozen'] and item['model_bytes']==path.stat().st_size
        if checkpoint==0:checks['zero_checkpoint_models'] &= zero_checkpoint_valid(payload)
        models[key]=dict(metadata=item,payload=payload,weights={int(row[0]):tuple(row[1:]) for row in payload['weights']})
    checks['source_model_roster'] &= len(capsule['models'])==len(models)==80 and set(models)=={
        (l,q,c,d) for l in LIVES for q in QUERIES for c in CHECKPOINTS for d in (1,8)}
    return models,checks,dict(source_model_files_read=len(capsule['models']),frozen_model_files_read=len(capsule['models']),model_bytes_read=read_bytes)


def analyze(directory):
    started=perf_counter();directory=Path(directory).resolve()
    run,capsule,frozen=(read(directory/name) for name in ('run.json','source_capsule.json','frozen_inputs.json'))
    checks=dict(frozen_settings=run['settings']==expected_settings(),frozen_inputs=frozen['status']=='frozen' and not frozen['lifecycles'] and
        frozen['settings']==run['settings'] and frozen['inherited_cost_refs']==run['inherited_cost_refs'],
        inherited_cost_refs=run['inherited_cost_refs']==capsule['cost_refs'],
        lifecycle_roster=len(run['lifecycles'])==4 and {r['life'] for r in run['lifecycles']}==set(LIVES),
        physical_records=True,physical_accounting=True,teacher_bank=True,teacher_totals=True,
        loaded_model_roster=True,loaded_models_frozen=True,model_prediction_counts=True,model_setup=True)
    add_checks(checks,logical_roster_checks(frozen['physical_roster'],frozen['logical_roster']))
    physical_roster={r['physical_id']:r for r in frozen['physical_roster']}
    models,source_checks,source_reads=source_models(capsule,directory);add_checks(checks,source_checks)
    inherited={path:read(path) for path in {ref['path'] for ref in capsule['cost_refs']}}
    checks['inherited_fields']=all(all(field in inherited[ref['path']] for field in ref['fields']) for ref in capsule['cost_refs'])
    sources={s['life']:s for s in capsule['snapshots']};physical={};physical_valid={};seen=[]
    costs=dict(physical_games=0,logical_games=len(frozen['logical_roster']),alias_references=len(frozen['logical_roster'])-len(physical_roster),
        new_training_environment_samples=0,new_training_updates=0,environment_counts=Counter(),policy_counts=Counter(),statuses=Counter(),
        seconds=sum(l['seconds'] for l in run['lifecycles']),decision_seconds=0.,analysis_replay_swipes=0,
        analysis_source_reads=source_reads,analysis_inherited_files_read=len(inherited),physical_cells={},frozen_model_copies=dict(files=len(models),bytes=sum(m['metadata']['model_bytes'] for m in models.values())),
        model_accounting=[],teacher_accounting=[])
    for lifecycle in run['lifecycles']:
        life=lifecycle['life'];source=sources[life];teacher_counts={q:Counter() for q in QUERIES}
        model_counts={(q,c,d):Counter() for q in QUERIES for c in range(1,5) for d in (1,8)}
        environment,policies,statuses=Counter(),Counter(),Counter();local_seen=[]
        for row in prior.old.read_rows(directory/lifecycle['control_trace']):
            identifier=row['physical_id'];seen.append(identifier);local_seen.append(identifier);reference=physical_roster[identifier]
            checks['physical_records'] &= all(row[k]==v for k,v in reference.items()) and row['life']==life and row['max_steps']==MAX_STEPS
            model_key=(life,row['query'],row['checkpoint'],row['duration'])
            weights=models[model_key]['weights'] if row['method'] in DURATIONS else {}
            local_checks,swipes,_=prior.replay_game(row,weights);add_checks(checks,local_checks)
            costs['analysis_replay_swipes']+=swipes;physical_valid[identifier]=all(local_checks.values())
            result=row['result'];physical[identifier]=dict(metadata=reference,result={k:result[k] for k in ('score','steps','status','components','utility')})
            costs['physical_games']+=1;costs['decision_seconds']+=result['decision_seconds']
            for target in (environment,costs['environment_counts']):target.update(result['environment_counts'])
            for target in (policies,costs['policy_counts']):target.update(result['policy_counts'])
            statuses[result['status']]+=1;costs['statuses'][result['status']]+=1
            cell_id=f"{row['query']}:{row['checkpoint']}:{row['method']}"
            cell=costs['physical_cells'].setdefault(cell_id,dict(query=row['query'],checkpoint=row['checkpoint'],method=row['method'],
                games=0,statuses=Counter(),environment_counts=Counter(),policy_counts=Counter(),decision_seconds=0.,game_seconds=0.))
            cell['games']+=1;cell['statuses'][result['status']]+=1;cell['decision_seconds']+=result['decision_seconds'];cell['game_seconds']+=result['seconds']
            for name in ('environment_counts','policy_counts'):cell[name].update(result[name])
            prior.add_policy_work(teacher_counts,result['policy_counts'])
            if row['method'] in DURATIONS:
                model_counts[row['query'],row['checkpoint'],row['duration']].update({k[len('learner_'):]:v for k,v in result['policy_counts'].items() if k.startswith('learner_')})
        checks['physical_records'] &= len(local_seen)==len(set(local_seen))==288 and set(local_seen)=={key for key,value in physical_roster.items() if value['life']==life}
        checks['physical_accounting'] &= lifecycle['physical_games']==len(local_seen) and Counter(lifecycle['environment_counts'])==environment and Counter(lifecycle['policy_counts'])==policies and Counter(lifecycle['statuses'])==statuses
        loaded=[]
        for meta in lifecycle['models']:
            query,checkpoint,duration=(meta[k] for k in ('query','checkpoint','duration'));key=query,checkpoint,duration;loaded.append(key)
            model=models[(life,*key)];state=model['metadata']['frozen_state'];n=len(model['weights'])
            checks['loaded_models_frozen'] &= meta['model_ref']==model['metadata']['model_ref'] and meta['before']==meta['after']==state
            checks['model_prediction_counts'] &= Counter(meta['counts'])==model_counts[key]
            checks['model_setup'] &= Counter(meta['setup_counts'])==Counter(topology_integer_cells=64,bias_integer_cells=1,
                loaded_weight_addresses=n,loaded_weight_parameters=3*n,loaded_numeric_weight_bytes=24*n)
            costs['model_accounting'].append(dict(life=life,**meta))
        checks['loaded_model_roster'] &= len(loaded)==len(set(loaded))==16 and set(loaded)==set(model_counts)
        for query in QUERIES:
            teacher=lifecycle['teacher_bank'][query]
            checks['teacher_bank'] &= prior.h1.teacher_analysis.teacher_loads_valid(teacher['loads'],source,'SINGLE',query)
            checks['teacher_bank'] &= teacher['parent_before']==teacher['parent_after']==prior.planning.previous.model_state(source,query,'PARENT',0)
            checks['teacher_bank'] &= teacher['leaf_before']==teacher['leaf_after']==prior.planning.expected_model_state(source,query,'SINGLE')
            checks['teacher_totals'] &= Counter(teacher['total_counts'])==teacher_counts[query]
            costs['teacher_accounting'].append(dict(life=life,query=query,**teacher))
        print(json.dumps(dict(event='audited_lifecycle',life=life,physical_games=len(local_seen),replayed_swipes=costs['analysis_replay_swipes'])),flush=True)
    checks['physical_records'] &= len(seen)==len(set(seen))==1152 and set(seen)==set(physical_roster)
    logical={};logical_valid={}
    for row in frozen['logical_roster']:
        key=tuple(row[k] for k in ('life','query','checkpoint','method','replica'));reference=physical[row['physical_id']]
        logical[key]=dict(result=logical_result(reference['result'],row['query']),physical_id=row['physical_id'])
        logical_valid[key]=physical_valid[row['physical_id']]
    results=aggregate(logical,logical_valid);scientific_complete=results.pop('primary_complete')
    complete=run['status']=='complete' and all(checks.values())
    costs['new_environment_samples']=costs['environment_counts'].get('sampled_transitions',0)
    return dict(schema='acfqp.module_replication.v152.analysis',complete=complete,primary_complete=complete and scientific_complete,
        checks=checks,**results,costs=costs,inherited_cost_refs=run['inherited_cost_refs'],seconds=perf_counter()-started,
        estimand='Common fresh seeds across all frozen checkpoints and policies, equal replicas within each history and equal four histories.',
        uncertainty='conditional_seed_ci95 is a normal approximation over new seed variation conditional on four fixed learned histories; it does not estimate training-history population uncertainty.',
        accounting='Each physical trajectory is replayed and charged once; logical references reuse trajectories and recompose target-query utility without duplicated physical work.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input','--directory',dest='input',type=Path,default=ROOT/'reports/controlled_predictive_module_replication_v152')
    args=parser.parse_args();result=analyze(args.input)
    (args.input/'analysis.json').write_text(json.dumps(result,separators=(',',':'))+'\n')
    print(json.dumps(dict(complete=result['complete'],primary_complete=result['primary_complete'],checks=len(result['checks']),
        failed=[k for k,v in result['checks'].items() if not v],seconds=result['seconds'])),flush=True)
    raise SystemExit(0 if result['complete'] else 1)
