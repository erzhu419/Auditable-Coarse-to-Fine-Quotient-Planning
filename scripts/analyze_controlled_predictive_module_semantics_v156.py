"""Independent feature, residual-fit and grouped holdout audit for V156."""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys
from time import perf_counter

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'src'))
from scripts import analyze_controlled_predictive_module_holdout_v155 as holdout
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics

prior,diagnosis=holdout.prior,holdout.diagnosis
LIVES,QUERIES,ARMS,SOURCES=holdout.LIVES,holdout.QUERIES,holdout.ARMS,holdout.SOURCES
KINDS=('LOCAL','SEMANTIC');ACTIONS=('DOWN','LEFT','RIGHT','UP')
mean,close,add_checks,read=prior.mean,prior.close,prior.add_checks,prior.read


def semantic_features(board,choices,query):
    own=choices[query];other=choices['risk8' if query=='risk1' else 'risk1'];values=own['action_values']
    first,second=values[own['action']],values[other['action']];rank=max(board);q=QUERIES[query]
    scores=sorted((v['value'] for v in values.values()),reverse=True)
    pairs=[(i,i+1) for i in range(16) if i%4!=3]+[(i,i+4) for i in range(12)]
    scale=1+q['failure_penalty']+q['goal_bonus']
    values=[1.,board.count(0)/16,len(values)/4,rank/11,float(any(board[i]==rank for i in (0,3,12,15))),
        sum(board[a]!=0 and board[a]==board[b] for a,b in pairs)/24,float(own['action']!=other['action']),
        (second['value']-first['value'])/scale,(scores[0]-scores[1])/scale if len(scores)>1 else 0.,first['value']/scale,
        (second['afterstate'].count(0)-first['afterstate'].count(0))/16,
        (second['score']-first['score'])/(2048+abs(second['score'])+abs(first['score']))]
    return {i:value for i,value in enumerate(values) if value!=0.}


def tuple_patterns():
    result=[]
    for pattern in ((0,1,2,4,5,6),(4,5,6,8,9,10),(0,1,2,3,4,5),(4,5,6,7,8,9)):
        for reflected in (False,True):
            for rotations in range(4):
                cells=[]
                for cell in pattern:
                    row,col=divmod(cell,4)
                    if reflected:col=3-col
                    for _ in range(rotations):row,col=col,3-row
                    cells.append(4*row+col)
                result.append(cells)
    return result


def h2_oracle(board,rule,weights,metadata,work):
    """Python learned rewrites and n-tuple lookups; no native planner/leaf call."""
    query=metadata['target_query'];radix=rule.goal_rank;patterns=tuple_patterns();stride=radix**6
    convert=metadata['kind']=='PRIOR' and any(metadata['source_query'].get(k,d)!=query.get(k,d)
        for k,d in (('reward_weight',1.),('failure_penalty',0.),('goal_bonus',0.)))
    def leaf_value(state):
        work['leaf_queries']+=1
        if max(state)>=radix:return query['goal_bonus']
        values=[]
        for action in ACTIONS:
            after,score,changed=rule.swipe(state,action,work);work['leaf_swipes']+=1
            if not changed:continue
            if max(after)>=radix:value=score/2048.+query['goal_bonus']
            else:
                tail=0.
                for i,cells in enumerate(patterns):
                    index=0
                    for cell in cells:index=index*radix+after[cell]
                    tail+=float(weights[(i//8)*stride+index]);work['weight_lookups']+=1
                work['leaf_predictions']+=1;value=score/2048.+tail
                if convert:value=value+metadata['failure_shift']+metadata['success_shift']
            values.append(value)
        return max(values) if values else -query['failure_penalty']
    work['h2_queries']+=1
    if max(board)>=radix:return dict(action=None,status='WON',value=query['goal_bonus'],action_values={})
    options={};distribution={rank:float(probability) for rank,probability in rule.spawn_distribution}
    for action in ACTIONS:
        after,score,changed=rule.swipe(board,action,work);work['root_swipes']+=1
        if not changed:continue
        if max(after)>=radix:tail=query['goal_bonus']
        else:
            empty=[i for i,rank in enumerate(after) if rank==0];tail=0.
            for cell in empty:
                for rank in (1,2):
                    successor=list(after);successor[cell]=rank;work['enumerated_spawn_outcomes']+=1
                    tail+=(distribution[rank]/len(empty))*leaf_value(successor)
        options[action]=dict(afterstate=list(after),score=score,tail_value=tail,value=score/2048.+tail)
    if not options:return dict(action=None,status='LOST',value=-query['failure_penalty'],action_values={})
    best=min(options,key=lambda a:(-options[a]['value'],a))
    return dict(action=best,status='ACTIVE',**options[best],action_values=options)


def choice_matches(actual,expected):
    valid=actual['action']==expected['action'] and actual['status']==expected['status'] and close(actual['value'],expected['value'])
    valid &= set(actual['action_values'])==set(expected['action_values'])
    for action,row in expected['action_values'].items():
        other=actual['action_values'][action]
        valid &= row['afterstate']==other['afterstate'] and row['score']==other['score'] and all(close(row[k],other[k]) for k in ('tail_value','value'))
    return valid


def aggregate(rows):
    methods={kind:holdout.aggregate([r for r in rows if r['representation']==kind]) for kind in KINDS}
    comparisons={}
    for split in ('heldout','train'):
        comparisons[split]={}
        for query in QUERIES:
            comparisons[split][query]={}
            for source in ('ALL',*SOURCES):
                comparisons[split][query][source]={}
                for arm in ARMS:
                    left=methods['SEMANTIC']['groups'][split][query][source][arm];right=methods['LOCAL']['groups'][split][query][source][arm]
                    names=('new_mse_own','new_mse_gate','policy_gain_change_gate','policy_gain_change_h2')
                    cells=[dict(life=l['life'],differences={k:l['means'][k]-r['means'][k] if l['means'][k] is not None and r['means'][k] is not None else None for k in names})
                        for l,r in zip(left['lifecycles'],right['lifecycles'])]
                    comparisons[split][query][source][arm]=dict(lifecycles=cells,means={k:mean(c['differences'][k] for c in cells) for k in names})
    return dict(representations=methods,semantic_minus_local=comparisons,primary_complete=all(v['primary_complete'] for v in methods.values()))


def residual_prediction(features,weights):
    result=[0.,0.,0.]
    for address,value in sorted(features.items()):
        weight=weights.get(address,(0.,0.,0.))
        for component in range(3):result[component]+=value*weight[component]
    return result


def residual_prediction_counts(features):
    n=len(features)
    return Counter(predictions=1,feature_entries_read=n,weight_address_reads=n,component_weight_reads=3*n)


def fit_oracle(examples,passes=32,alpha=.1):
    weights={};counts=Counter();updates=0
    for _ in range(passes):
        for example in examples:
            features=example['features'];target=example['target'];before=residual_prediction(features,weights);n=len(features)
            counts.update(residual_prediction_counts(features));norm=sum(v*v for _,v in sorted(features.items()))
            for address,value in sorted(features.items()):
                old=weights.get(address,(0.,0.,0.));new=tuple(old[c]+alpha*(target[c]-before[c])*value/norm for c in range(3))
                if any(new):
                    if address not in weights:counts['allocated_weight_addresses']+=1
                    weights[address]=new
                else:weights.pop(address,None)
            updates+=1;counts.update(feature_entries_read=2*n,weight_address_reads=n,component_weight_reads=3*n,
                update_calls=1,weight_address_updates=n,component_weight_updates=3*n)
    return dict(weights=weights,counts=counts,updates=updates)


def state_matches(state,kind,weights,updates,frozen=True):
    return state['feature_kind']==kind and state['updates']==updates and state['frozen']==frozen and len(state['weights'])==len(weights) and all(
        int(row[0]) in weights and all(close(a,b) for a,b in zip(row[1:],weights[int(row[0])])) for row in state['weights'])


def expected_settings():
    return dict(lifecycles=list(LIVES),queries=QUERIES,repairs=list(ARMS),representations=list(KINDS),
        replicas=[0,4,8,12],folds=32,training_roots_per_fold=6,heldout_roots_per_fold=2,
        source='all64 audited V155 roots and V153 component means; unchanged OLD cp4 and frozen H2 teachers',
        feature_definition='specs/MODULE_SEMANTICS_V156.md; LOCAL V151 sparse41 occurrences; SEMANTIC fixed12 features',
        critic='both selected actions scored by the target-query teacher; other-query scalar values are not subtracted',
        local_target='three-component target minus cached frozen OLD components; zero residual initialization',
        epochs=32,alpha=.1,optimizer='normalized LMS with sum of squared feature values; frozen V153 root order',
        new_fits=128,new_updates=24576,updates_per_fit=192,old_predictions=64,residual_evaluation_predictions=1024,
        planned_root_queries=128,new_environment_samples=0,
        freeze='folds before feature preparation; feature package before fitting; all128 residual models before evaluation',
        primary='heldout SEMANTIC minus LOCAL own-target MSE and fixed-OLD-continuation local GATE gain',
        secondary='both representations against OLD; common GATE/H2 MSE, both source strata, histories, train diagnostics',
        weighting='equal roots within history then equal four histories; unchanged decisions retained',
        uncertainty='descriptive only; overlapping folds and previously inspected retained labels',
        accounting='all four views charge full retained2017530-transition pool; native planning and all residual work separate')


def source_models(capsule,directory):
    run=read(capsule['source_run_ref']);analysis=read(capsule['source_analysis_ref']);source=read(capsule['source_capsule_ref'])
    teachers=read(capsule['teacher_capsule_ref']);origin=Path(capsule['source_run_ref']).parent
    checks=dict(source_complete=run['status']=='complete' and analysis['complete'] and analysis['primary_complete'],
        source_bindings=Path(capsule['source_analysis_ref'])==origin/'analysis.json' and Path(capsule['source_capsule_ref'])==origin/'source_capsule.json' and
        capsule['teacher_capsule_ref']==source['source_capsule_ref'] and capsule['snapshots']==teachers['snapshots'],
        source_labels=capsule['roots']==source['roots'] and capsule['examples']==source['examples'] and len(capsule['examples'])==64,
        retained_cost=capsule['retained_training_cost']==source['retained_training_cost'],source_model_roster=True,source_model_copies=True)
    references={(m['life'],m['query']):m for m in source['models']};models={}
    for meta in capsule['models']:
        key=meta['life'],meta['query'];reference=references[key];path=directory/meta['model_ref'];payload=read(path);original=read(meta['source_model_ref'])
        checks['source_model_roster'] &= key not in models and meta['arm']=='OLD'
        checks['source_model_copies'] &= Path(meta['source_model_ref'])==origin/reference['model_ref'] and payload==original and payload['frozen']
        checks['source_model_copies'] &= meta['frozen_state']==reference['frozen_state']==prior.local.prior.state(payload) and meta['model_bytes']==path.stat().st_size
        models[key]=dict(metadata=meta,weights={int(r[0]):tuple(r[1:]) for r in payload['weights']})
    checks['source_model_roster'] &= len(capsule['models'])==len(models)==8 and set(models)=={(l,q) for l in LIVES for q in QUERIES}
    return models,checks,origin/run['evaluation']['rows_ref']


def audit_features(capsule,package,models):
    roots={r['root_id']:r for r in capsule['roots']};seen=[];old_counts={key:Counter() for key in models};teacher_counts={(l,q):Counter() for l in LIVES for q in QUERIES}
    totals={kind:Counter() for kind in KINDS};work=Counter();checks=dict(feature_roster=True,feature_identity=True,feature_values=True,feature_counts=True,
        old_predictions=True,old_models_frozen=True,old_model_counts=True,teacher_roster=True,teacher_bindings=True,teacher_counts=True,h2_values=True,h2_counts=True,leaf_checkpoints=True)
    rows=package['rows'];by_life={l:[r for r in rows if r['life']==l] for l in LIVES}
    for source in capsule['snapshots']:
        life=source['life'];rule=LearnedDynamics.from_payload(source['rule'])
        for query in QUERIES:
            reference=source['leaves'][query]['SINGLE'];path=Path(reference['model_ref']);metadata=read(str(path)+'.query.json')
            with np.load(path,allow_pickle=False) as data:
                leaf_metadata=json.loads(str(data['metadata']));weights=np.zeros(4*rule.goal_rank**6,dtype=np.float64);weights[data['indices']]=data['values']
                work['leaf_checkpoint_nonzero_parameters_read']+=len(data['indices'])
            work['leaf_checkpoint_files_read']+=1;work['leaf_sidecars_read']+=1;work['leaf_numeric_bytes_allocated']+=weights.nbytes
            checks['leaf_checkpoints'] &= metadata['kind']=='PRIOR' and metadata['target_query']==QUERIES[query] and metadata['updates']==reference['updates']
            checks['leaf_checkpoints'] &= leaf_metadata['radix']==rule.goal_rank and leaf_metadata['updates']==reference['updates']
            for row in by_life[life]:
                choice=row['choices'][query];board=roots[row['root_id']]['board'];expected=h2_oracle(board,rule,weights,metadata,work)
                checks['h2_values'] &= choice_matches(choice,expected)
                checks['h2_counts'] &= prior.planning.planning_counts_valid(choice['counts'],'H2','SINGLE',1,len(choice['action_values']))
                teacher_counts[life,query].update(choice['counts'])
            del weights
    for row in rows:
        key=row['root_id'];seen.append(key);root=roots[key];model_key=root['life'],root['query'];board=root['board']
        checks['feature_identity'] &= row['life']==root['life'] and row['query']==root['query'] and set(row['choices'])==set(QUERIES)
        expected={'LOCAL':dict(prior.features(board)),'SEMANTIC':semantic_features(board,row['choices'],root['query'])}
        expected_work={'LOCAL':dict(feature_board_reads=16,feature_rank_reads=64,feature_occurrences=41,unary_feature_occurrences=16,pair_feature_occurrences=24,bias_feature_occurrences=1),
            'SEMANTIC':dict(feature_board_reads=48,feature_rank_reads=116,feature_occurrences=12,teacher_action_value_reads=len(row['choices'][root['query']]['action_values']),feature_nonzero_addresses=len(expected['SEMANTIC']))}
        for kind in KINDS:
            checks['feature_values'] &= row['features'][kind]==[[k,v] for k,v in sorted(expected[kind].items())]
            checks['feature_counts'] &= row['feature_counts'][kind]==expected_work[kind];totals[kind].update(expected_work[kind])
        checks['old_predictions'] &= holdout.prediction_matches(row['old_prediction'],holdout.prediction(board,root['query'],models[model_key]['weights']))
        old_counts[model_key].update(prior.prediction_work(board))
    checks['feature_roster'] &= seen==[r['root_id'] for r in capsule['roots']] and len(seen)==len(set(seen))==64
    checks['feature_counts'] &= all(Counter(package['feature_counts'][kind])==totals[kind] for kind in KINDS)
    old_seen=[]
    for meta in package['old_models']:
        key=meta['life'],meta['query'];old_seen.append(key);model=models[key]
        checks['old_models_frozen'] &= meta['before']==meta['after']==model['metadata']['frozen_state'] and meta['model_ref']==model['metadata']['model_ref']
        checks['old_model_counts'] &= Counter(meta['counts'])==old_counts[key] and Counter(meta['setup_counts'])==diagnosis.model_setup(len(model['weights']))
    checks['old_models_frozen'] &= len(old_seen)==len(set(old_seen))==8 and set(old_seen)==set(models)
    sources={s['life']:s for s in capsule['snapshots']};teacher_seen=[]
    for teacher in package['teachers']:
        life,query=teacher['life'],teacher['query'];key=life,query;teacher_seen.append(key);source=sources[life]
        checks['teacher_bindings'] &= prior.h1.teacher_analysis.teacher_loads_valid(teacher['loads'],source,'SINGLE',query)
        checks['teacher_bindings'] &= teacher['parent_before']==teacher['parent_after']==prior.planning.previous.model_state(source,query,'PARENT',0)
        checks['teacher_bindings'] &= teacher['leaf_before']==teacher['leaf_after']==prior.planning.expected_model_state(source,query,'SINGLE')
        checks['teacher_counts'] &= Counter(teacher['total_counts'])==teacher_counts[key]
    checks['teacher_roster'] &= len(teacher_seen)==len(set(teacher_seen))==8 and set(teacher_seen)==set(teacher_counts)
    checks['old_model_counts'] &= package['old_predictions']==64
    checks['teacher_counts'] &= package['planned_root_queries']==128 and package['new_environment_samples']==0
    work['old_oracle_predictions']=len(rows)
    return checks,dict(work)


def audit_fits(capsule,folds,package,metadata,directory):
    examples={e['root_id']:e for e in capsule['examples']};features={r['root_id']:r for r in package['rows']};by_fold={f['fold_id']:f for f in folds}
    models={};seen=[];checks=dict(fit_roster=True,fit_initialization=True,fit_roots=True,fit_weights=True,fit_counts=True,fit_storage=True)
    for meta in metadata:
        key=meta['fold_id'],meta['representation'],meta['arm'];seen.append(key);fold=by_fold[key[0]];kind,arm=key[1:];selected=[]
        for root_id in fold['train_ids']:
            row=features[root_id];target=[a-b for a,b in zip(examples[root_id]['targets'][arm],row['old_prediction']['components'])]
            selected.append(dict(features=dict(row['features'][kind]),target=target))
        expected=fit_oracle(selected);path=directory/meta['model_ref'];payload=read(path);n=len(expected['weights'])
        checks['fit_initialization'] &= meta['before']==dict(feature_kind=kind,weights=[],updates=0,frozen=False)
        checks['fit_roots'] &= all(meta[k]==fold[k] for k in ('life','query','replica')) and meta['root_ids']==fold['train_ids'] and len(selected)==6
        checks['fit_roots'] &= not(set(fold['train_ids'])&set(fold['heldout_ids'])) and meta['new_updates']==192
        checks['fit_weights'] &= state_matches(meta['frozen_state'],kind,expected['weights'],192) and state_matches(payload,kind,expected['weights'],192)
        save_counts=Counter(checkpoint_saves=1,checkpoint_saved_addresses=n,checkpoint_saved_parameters=3*n)
        checks['fit_counts'] &= Counter(meta['fit_counts'])==expected['counts'] and Counter(meta['total_counts'])==Counter(payload['counts'])==expected['counts']+save_counts
        checks['fit_storage'] &= meta['model_bytes']==path.stat().st_size and payload['storage']==dict(weight_addresses=n,weight_parameters=3*n,numeric_weight_bytes=24*n,numeric_address_bytes=8*n)
        models[key]=dict(metadata=meta,weights={int(r[0]):tuple(r[1:]) for r in payload['weights']})
    checks['fit_roster'] &= len(seen)==len(set(seen))==128 and set(seen)=={(f['fold_id'],k,a) for f in folds for k in KINDS for a in ARMS}
    return models,checks


def audit_predictions(capsule,folds,package,rows,evaluation,models):
    roots={r['root_id']:r for r in capsule['roots']};examples={r['root_id']:r for r in capsule['examples']};features={r['root_id']:r for r in package['rows']};by_fold={f['fold_id']:f for f in folds}
    checks=dict(prediction_roster=True,prediction_identity=True,prediction_values=True,evaluation_models_frozen=True,evaluation_counts=True)
    seen=[];counts={key:Counter(checkpoint_loads=1,checkpoint_loaded_addresses=len(m['weights']),checkpoint_loaded_parameters=3*len(m['weights'])) for key,m in models.items()}
    for row in rows:
        key=row['fold_id'],row['representation'],row['arm'];seen.append((*key,row['root_id']));fold=by_fold[key[0]];root=roots[row['root_id']];feature=features[row['root_id']]
        vector=dict(feature['features'][key[1]]);residual=residual_prediction(vector,models[key]['weights']);counts[key].update(residual_prediction_counts(vector))
        components=[a+b for a,b in zip(feature['old_prediction']['components'],residual)];value=prior.utility(components,root['query'])
        checks['prediction_identity'] &= all(row[k]==fold[k] for k in ('life','query','replica')) and (root['life'],root['query'])==(fold['life'],fold['query'])
        checks['prediction_identity'] &= row['source_method']==root['source_method'] and row['targets']==examples[row['root_id']]['targets'] and row['old_prediction']==feature['old_prediction']
        checks['prediction_identity'] &= row['split']==('heldout' if row['root_id'] in fold['heldout_ids'] else 'train')
        checks['prediction_values'] &= len(row['residual_components'])==3 and all(close(a,b) for a,b in zip(row['residual_components'],residual))
        checks['prediction_values'] &= holdout.prediction_matches(row['prediction'],dict(components=components,advantage=value,accept=value>0))
    expected={(f['fold_id'],k,a,r['root_id']) for f in folds for k in KINDS for a in ARMS for r in capsule['roots'] if (r['life'],r['query'])==(f['life'],f['query'])}
    checks['prediction_roster'] &= len(seen)==len(set(seen))==1024 and set(seen)==expected and evaluation['rows']==1024
    by_ref={m['metadata']['model_ref']:(key,m) for key,m in models.items()};loaded=[]
    for meta in evaluation['models']:
        ref=meta['model_ref'];loaded.append(ref);key,model=by_ref[ref]
        checks['evaluation_models_frozen'] &= meta['before']==meta['after']==model['metadata']['frozen_state']
        checks['evaluation_counts'] &= Counter(meta['counts'])==counts[key]
    checks['evaluation_models_frozen'] &= len(loaded)==len(set(loaded))==128 and set(loaded)==set(by_ref)
    checks['evaluation_counts'] &= evaluation['new_environment_samples']==0
    return checks,dict(residual_oracle_predictions=len(rows),expected_evaluation_counts=dict(sum(counts.values(),Counter())))


def local_anchor_checks(rows,reference_rows):
    key=lambda row:(row['fold_id'],row['arm'],row['root_id'])
    local=[r for r in rows if r['representation']=='LOCAL'];references={key(r):r for r in reference_rows}
    checks=dict(local_anchor_roster=len(local)==len(reference_rows)==len(references)==512 and {key(r) for r in local}==set(references),
        local_anchor_components=True,local_anchor_gate=True)
    for row in local:
        reference=references[key(row)]['prediction'];prediction=row['prediction']
        checks['local_anchor_components'] &= len(prediction['components'])==3 and all(close(a,b) for a,b in zip(prediction['components'],reference['components']))
        checks['local_anchor_components'] &= close(prediction['advantage'],reference['advantage'])
        checks['local_anchor_gate'] &= prediction['accept']==reference['accept']
    return checks


def analyze(directory):
    started=perf_counter();directory=Path(directory).resolve()
    run,capsule,frozen,training=(read(directory/name) for name in ('run.json','source_capsule.json','frozen_inputs.json','frozen_training.json'))
    checks=dict(settings=run['settings']==expected_settings(),frozen_inputs=frozen['status']=='frozen' and frozen['training']==[] and frozen['evaluation'] is None and
        all(frozen[k]==run[k] for k in ('settings','folds','features_ref','inherited_cost_refs')),frozen_training=training==run['training'],
        inherited_costs=run['inherited_cost_refs']==capsule['cost_refs'])
    old_models,local_checks,anchor_ref=source_models(capsule,directory);add_checks(checks,local_checks)
    folds=holdout.expected_folds(capsule['roots']);checks['fold_roster']=run['folds']==folds
    package=read(directory/run['features_ref']);local_checks,feature_work=audit_features(capsule,package,old_models);add_checks(checks,local_checks)
    models,local_checks=audit_fits(capsule,folds,package,training,directory);add_checks(checks,local_checks)
    rows=read(directory/run['evaluation']['rows_ref']);local_checks,prediction_work=audit_predictions(capsule,folds,package,rows,run['evaluation'],models);add_checks(checks,local_checks)
    anchor_rows=read(anchor_ref);add_checks(checks,local_anchor_checks(rows,anchor_rows))
    outcome=aggregate(rows);primary=outcome.pop('primary_complete');complete=run['status']=='complete' and all(checks.values())
    acquisition=capsule['retained_training_cost']['retained_environment_transitions']
    costs=dict(new_environment_samples=0,old_raw_branch_reads=0,new_fits=len(training),new_updates=sum(m['new_updates'] for m in training),
        physical_retained_acquisition=acquisition,retained_budget_views={f'{k}:{a}':acquisition for k in KINDS for a in ARMS},
        feature_preparation={k:v for k,v in package.items() if k!='rows'},runtime_residual_evaluation=run['evaluation'],
        runtime_fit_counts=dict(sum((Counter(m['fit_counts']) for m in training),Counter())),runtime_fit_total_counts=dict(sum((Counter(m['total_counts']) for m in training),Counter())),
        frozen_model_files=136,frozen_model_bytes=sum(m['model_bytes'] for m in capsule['models']+training),
        source_old_model_reads=8,source_model_copies=8,runtime_old_model_loads=8,runtime_residual_constructions=128,runtime_residual_loads=128,
        runtime_teacher_parent_loads=8,runtime_teacher_leaf_loads=8,runtime_old_predictions=64,runtime_residual_predictions=1024,
        analysis_source_metadata_files_read=4,analysis_inherited_files_read=0,analysis_model_payloads_read=144,
        analysis_local_anchor_rows_read=len(anchor_rows),
        analysis_feature_work=feature_work,analysis_fit_oracle_updates=32*6*len(training),analysis_prediction_work=prediction_work)
    return dict(schema='acfqp.module_semantics.v156.analysis',complete=complete,primary_complete=complete and primary,checks=checks,**outcome,
        costs=costs,inherited_cost_refs=run['inherited_cost_refs'],seconds=perf_counter()-started,
        estimand='Matched grouped holdout residual fits, fixed OLD base and targets. SEMANTIC minus LOCAL MSE is better when negative; local policy gain is better when positive.',
        limitations='Descriptive comparisons only: overlapping folds and previously inspected retained labels. Fixed-OLD-continuation local gain does not establish fresh full-game improvement. Native feature planning and inherited acquisition remain charged.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input','--directory',dest='input',type=Path,default=ROOT/'reports/controlled_predictive_module_semantics_v156')
    args=parser.parse_args();result=analyze(args.input)
    (args.input/'analysis.json').write_text(json.dumps(result,separators=(',',':'))+'\n')
    print(json.dumps(dict(complete=result['complete'],primary_complete=result['primary_complete'],checks=len(result['checks']),
        failed=[k for k,v in result['checks'].items() if not v],seconds=result['seconds'])),flush=True)
    raise SystemExit(0 if result['complete'] else 1)
