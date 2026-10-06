"""Audit grouped retained-label holdout fits without new environment execution."""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys
from time import perf_counter

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'src'))
from scripts import analyze_controlled_predictive_policy_modules_v151 as prior
from scripts import analyze_controlled_predictive_module_diagnosis_v153 as diagnosis

LIVES,QUERIES=prior.LIVES,prior.QUERIES
ARMS=('REPAIR_H2','REPAIR_GATE');SOURCES=('H2','LEARN8');REPLICAS=(0,4,8,12)
mean,close,add_checks,read=prior.mean,prior.close,prior.add_checks,prior.read


def metrics(row):
    old=row['old_prediction']['advantage'];new=row['prediction']['advantage'];old_accept=int(old>0);new_accept=int(new>0)
    targets={arm:prior.utility(value,row['query']) for arm,value in row['targets'].items()};values={}
    for label,arm in (('h2','REPAIR_H2'),('gate','REPAIR_GATE'),('own',row['arm'])):
        target=targets[arm];a=(old-target)**2;b=(new-target)**2
        values.update({f'old_mse_{label}':a,f'new_mse_{label}':b,f'mse_change_{label}':b-a})
        if label!='own':values[f'policy_gain_change_{label}']=(new_accept-old_accept)*target
    values.update(old_accept_rate=old_accept,new_accept_rate=new_accept,changed_rate=int(old_accept!=new_accept))
    return values


def decision_counts(rows):
    return dict(old_accepts=sum(r["old_prediction"]["advantage"]>0 for r in rows),
        new_accepts=sum(r["prediction"]["advantage"]>0 for r in rows),
        gate_changes=sum((r["old_prediction"]["advantage"]>0)!=(r["prediction"]["advantage"]>0) for r in rows))


def summarize(rows,split,source):
    names=tuple(f'{prefix}_mse_{label}' if prefix!='change' else f'mse_change_{label}'
        for label in ('h2','gate','own') for prefix in ('old','new','change'))+('policy_gain_change_h2','policy_gain_change_gate','old_accept_rate','new_accept_rate','changed_rate')
    cells=[];expected=(8 if split=='heldout' else 24)//(1 if source=='ALL' else 2)
    for life in LIVES:
        selected=[r for r in rows if r['life']==life];values=[metrics(r) for r in selected];folds=[]
        for replica in REPLICAS:
            folded=[r for r in selected if r['replica']==replica];fm=[metrics(r) for r in folded]
            folds.append(dict(fold_id=folded[0]['fold_id'] if folded else None,replica=replica,records=len(folded),
                means={name:mean(v[name] for v in fm) for name in names},counts=decision_counts(folded)))
        cells.append(dict(life=life,records=len(selected),complete=len(selected)==expected,
            means={name:mean(v[name] for v in values) for name in names},folds=folds,counts=decision_counts(selected)))
    return dict(records=len(rows),unique_roots=len({r['root_id'] for r in rows}),complete=all(c['complete'] for c in cells),
        means={name:mean(c['means'][name] for c in cells) for name in names},lifecycles=cells,counts=decision_counts(rows))


def aggregate(rows):
    groups={}
    for split in ('heldout','train'):
        groups[split]={}
        for query in QUERIES:
            groups[split][query]={}
            for source in ('ALL',*SOURCES):
                groups[split][query][source]={arm:summarize([r for r in rows if r['query']==query and r['arm']==arm and
                    r['split']==split and (source=='ALL' or r['source_method']==source)],split,source) for arm in ARMS}
    return dict(groups=groups,primary_complete=all(cell['complete'] for queries in groups.values() for sources in queries.values()
        for arms in sources.values() for cell in arms.values()))


def expected_settings():
    return dict(lifecycles=list(LIVES),queries=QUERIES,repairs=list(ARMS),replicas=list(REPLICAS),
        source='audited V154 compact means of all64 V153 roots and unchanged OLD cp4 models',
        grouping='same history/query/replica: hold out both H2 and LEARN8 source roots together',
        folds=32,training_roots_per_fold=6,heldout_roots_per_fold=2,epochs=32,alpha=.1,
        initialization='each fold/arm independently loads the same OLD checkpoint; no old V151 label replay',
        training_order='V153 frozen root order with the two heldout roots removed',
        new_fits=64,new_updates=12288,updates_per_fit=192,frozen_models=72,
        targets={'REPAIR_H2':'mean components(M_H2-H_H2)','REPAIR_GATE':'mean components(M_GATE-H_GATE)'},
        gate='strict positive predicted utility; fixed OLD continuation for local decision evaluation',
        predictions=dict(old=64,repair=512,total=576),
        primary='heldout own-target MSE change and (new_accept-old_accept)*GATE target utility',
        secondary='common GATE target MSE; H2 target local gain; train diagnostics; all roots and both source strata',
        weighting='equal roots within each history, then equal four histories; include zero-disagreement roots',
        uncertainty='descriptive only; overlapping fold training sets are not independent repetitions',
        freeze='protocol and all32 folds before fitting; all64 repairs frozen before any evaluation predictions',
        new_environment_samples=0,native_planner_calls=0,
        accounting='reuse audited compact means; both arms charge the full retained2017530-transition pool, physical acquisition once')


def expected_folds(roots):
    folds=[]
    for life in LIVES:
        for query in QUERIES:
            selected=[r for r in roots if r['life']==life and r['query']==query]
            for replica in REPLICAS:
                held=[r for r in selected if r['replica']==replica]
                folds.append(dict(fold_id=f'{life}:{query}:{replica}',life=life,query=query,replica=replica,
                    source_seed=held[0]['source_seed'],train_ids=[r['root_id'] for r in selected if r['replica']!=replica],
                    heldout_ids=[r['root_id'] for r in held]))
    return folds


def source_models(capsule,directory):
    run=read(capsule['source_run_ref']);analysis=read(capsule['source_analysis_ref']);source=read(capsule['source_capsule_ref'])
    examples=read(capsule['source_examples_ref']);origin=Path(capsule['source_run_ref']).parent
    checks=dict(source_complete=run['status']=='complete' and analysis['complete'] and analysis['primary_complete'],
        source_bindings=Path(capsule['source_analysis_ref'])==origin/'analysis.json' and Path(capsule['source_capsule_ref'])==origin/'source_capsule.json' and
        Path(capsule['source_examples_ref'])==origin/run['training']['examples_ref'],source_labels=capsule['examples']==examples and capsule['roots']==source['roots'],
        retained_cost=capsule['retained_training_cost']==run['training']['read_work'],source_model_roster=True,source_model_copies=True)
    roots=capsule['roots'];expected=[(l,q,s,slot) for l in LIVES for q in QUERIES for s in SOURCES for slot in range(4)]
    checks['source_labels'] &= len(examples)==len(roots)==64 and [(r['life'],r['query'],r['source_method'],r['slot']) for r in roots]==expected
    checks['source_labels'] &= [e['root_id'] for e in examples]==[r['root_id'] for r in roots] and all(
        all(e[k]==r[k] for k in ('life','query','source_method','slot','board')) and e['suffixes']==16 for e,r in zip(examples,roots))
    checks['source_groups']=all(r['replica']==4*r['slot'] for r in roots) and all(
        len({r['source_seed'] for r in roots if (r['life'],r['query'],r['replica'])==(l,q,replica)})==1
        for l in LIVES for q in QUERIES for replica in REPLICAS)
    references={(m['life'],m['query']):m for m in source['models']};models={}
    for meta in capsule['models']:
        key=meta['life'],meta['query'];reference=references[key];path=directory/meta['model_ref'];payload=read(path);original=read(meta['source_model_ref'])
        checks['source_model_roster'] &= key not in models and meta['arm']=='OLD'
        checks['source_model_copies'] &= Path(meta['source_model_ref'])==origin/reference['model_ref'] and payload==original and payload['frozen']
        checks['source_model_copies'] &= meta['frozen_state']==reference['frozen_state']==prior.local.prior.state(payload) and meta['model_bytes']==path.stat().st_size
        models[key]=dict(metadata=meta,payload=payload,weights={int(r[0]):tuple(r[1:]) for r in payload['weights']})
    checks['source_model_roster'] &= len(capsule['models'])==len(models)==8 and set(models)=={(l,q) for l in LIVES for q in QUERIES}
    return models,checks


def audit_fits(examples,folds,metadata,models,directory):
    indexed={e['root_id']:e for e in examples};by_fold={f['fold_id']:f for f in folds};seen=[];new_models={}
    checks=dict(fit_model_roster=True,fit_initialization=True,fit_root_groups=True,fit_weights=True,fit_counts=True,fit_storage=True)
    for meta in metadata:
        life,query,arm=meta['life'],meta['query'],meta['arm'];fold=by_fold[meta['fold_id']];key=meta['fold_id'],arm;seen.append(key)
        original=models[life,query];before=original['metadata']['frozen_state'];selected=[indexed[r] for r in fold['train_ids']]
        expected=prior.fit_oracle([dict(board=e['board'],target=e['targets'][arm]) for e in selected],original['weights'],passes=32,alpha=.1)
        updates=before['updates']+expected['updates'];path=directory/meta['model_ref'];payload=read(path);n=len(expected['weights'])
        save_counts=Counter(checkpoint_saves=1,checkpoint_saved_addresses=n,checkpoint_saved_parameters=3*n)
        checks['fit_initialization'] &= meta['source_model_ref']==original['metadata']['model_ref'] and meta['before']==before
        checks['fit_root_groups'] &= all(meta[k]==fold[k] for k in ('life','query','replica')) and len(selected)==6 and len(fold['heldout_ids'])==2
        checks['fit_root_groups'] &= not(set(fold['train_ids'])&set(fold['heldout_ids'])) and meta['root_ids']==fold['train_ids'] and meta['new_updates']==expected['updates']==192
        checks['fit_weights'] &= prior.state_matches(meta['frozen_state'],expected['weights'],updates) and prior.local.model_matches(payload,dict(weights=expected['weights'],updates=updates))
        checks['fit_counts'] &= Counter(meta['fit_counts'])==expected['counts'] and Counter(meta['total_counts'])==expected['counts']+save_counts
        checks['fit_counts'] &= Counter(payload['counts'])==Counter(meta['total_counts']) and Counter(meta['setup_counts'])==diagnosis.model_setup(len(original['weights']))
        checks['fit_counts'] &= payload['setup_counts']==meta['setup_counts'] and close(payload['setup_seconds'],meta['setup_seconds'])
        checks['fit_storage'] &= meta['model_bytes']==path.stat().st_size and payload['storage']==dict(weight_addresses=n,weight_parameters=3*n,numeric_weight_bytes=24*n,numeric_address_bytes=8*n)
        new_models[key]=dict(metadata=meta,payload=payload,weights={int(r[0]):tuple(r[1:]) for r in payload['weights']})
    checks['fit_model_roster'] &= len(seen)==len(set(seen))==64 and set(seen)=={(f['fold_id'],a) for f in folds for a in ARMS}
    return new_models,checks


def prediction(board,query,weights):
    components=list(prior.predict(board,weights));advantage=prior.utility(components,query)
    return dict(components=components,advantage=advantage,accept=advantage>0)


def prediction_matches(actual,expected):
    return len(actual['components'])==3 and all(close(a,b) for a,b in zip(actual['components'],expected['components'])) and \
        close(actual['advantage'],expected['advantage']) and actual['accept']==expected['accept']


def audit_predictions(capsule,folds,rows,evaluation,old_models,new_models):
    examples={e['root_id']:e for e in capsule['examples']};roots={r['root_id']:r for r in capsule['roots']};by_fold={f['fold_id']:f for f in folds}
    olds={};work={};all_models={m['metadata']['model_ref']:m for m in list(old_models.values())+list(new_models.values())}
    for ref in all_models:work[ref]=Counter()
    for root in capsule['roots']:
        model=old_models[root['life'],root['query']];olds[root['root_id']]=prediction(root['board'],root['query'],model['weights'])
        work[model['metadata']['model_ref']].update(prior.prediction_work(root['board']))
    checks=dict(prediction_roster=True,prediction_identity=True,prediction_values=True,prediction_models=True,prediction_counts=True,prediction_setup=True)
    seen=[]
    for row in rows:
        key=row['fold_id'],row['arm'],row['root_id'];seen.append(key);root=roots[row['root_id']];fold=by_fold[row['fold_id']]
        model=new_models[row['fold_id'],row['arm']];expected=prediction(root['board'],root['query'],model['weights'])
        checks['prediction_identity'] &= all(row[k]==fold[k] for k in ('life','query','replica')) and (root['life'],root['query'])==(fold['life'],fold['query'])
        checks['prediction_identity'] &= row['source_method']==root['source_method'] and row['targets']==examples[row['root_id']]['targets']
        checks['prediction_identity'] &= row['split']==('heldout' if row['root_id'] in fold['heldout_ids'] else 'train')
        checks['prediction_values'] &= prediction_matches(row['prediction'],expected) and prediction_matches(row['old_prediction'],olds[row['root_id']])
        work[model['metadata']['model_ref']].update(prior.prediction_work(root['board']))
    expected_keys={(f['fold_id'],arm,r['root_id']) for f in folds for arm in ARMS for r in capsule['roots'] if (r['life'],r['query'])==(f['life'],f['query'])}
    checks['prediction_roster'] &= len(seen)==len(set(seen))==512 and set(seen)==expected_keys
    loaded=[]
    for meta in evaluation['models']:
        ref=meta['model_ref'];loaded.append(ref);model=all_models[ref];state=model['metadata']['frozen_state']
        checks['prediction_models'] &= meta['before']==meta['after']==state
        checks['prediction_counts'] &= Counter(meta['counts'])==work[ref]
        checks['prediction_setup'] &= Counter(meta['setup_counts'])==diagnosis.model_setup(len(model['weights']))
    checks['prediction_models'] &= len(loaded)==len(set(loaded))==72 and set(loaded)==set(all_models)
    checks['prediction_counts'] &= evaluation['root_predictions']==sum(c['root_predictions'] for c in work.values())==576
    checks['prediction_counts'] &= evaluation['new_environment_samples']==evaluation['native_planner_calls']==0
    return checks,dict(oracle_root_predictions=len(olds)+len(rows),expected_prediction_counts=dict(sum(work.values(),Counter())))


def analyze(directory):
    started=perf_counter();directory=Path(directory).resolve()
    run,capsule,frozen,training=(read(directory/name) for name in ('run.json','source_capsule.json','frozen_inputs.json','frozen_training.json'))
    checks=dict(settings=run['settings']==expected_settings(),frozen_inputs=frozen['status']=='frozen' and frozen['training']==[] and frozen['evaluation'] is None and
        all(frozen[k]==run[k] for k in ('settings','folds','inherited_cost_refs')),frozen_training=training==run['training'],
        inherited_costs=run['inherited_cost_refs']==capsule['cost_refs'])
    old_models,local_checks=source_models(capsule,directory);add_checks(checks,local_checks)
    folds=expected_folds(capsule['roots']);checks['fold_roster']=run['folds']==folds
    new_models,local_checks=audit_fits(capsule['examples'],folds,training,old_models,directory);add_checks(checks,local_checks)
    rows=read(directory/run['evaluation']['rows_ref'])
    local_checks,prediction_work=audit_predictions(capsule,folds,rows,run['evaluation'],old_models,new_models);add_checks(checks,local_checks)
    outcome=aggregate(rows);primary_complete=outcome.pop('primary_complete');complete=run['status']=='complete' and all(checks.values())
    costs=dict(new_environment_samples=0,native_planner_calls=0,new_fits=len(training),new_updates=sum(m['new_updates'] for m in training),
        physical_retained_acquisition=capsule['retained_training_cost']['retained_environment_transitions'],retained_budget_views=capsule['retained_training_cost']['matched_budget_views'],
        compact_label_rows=64,old_raw_branch_reads=0,runtime_model_loads=64+72,runtime_model_file_reads=8+32+72,source_model_copies=8,
        runtime_root_predictions=run['evaluation']['root_predictions'],runtime_fit_counts=dict(sum((Counter(m['fit_counts']) for m in training),Counter())),
        runtime_fit_total_counts=dict(sum((Counter(m['total_counts']) for m in training),Counter())),runtime_evaluation=run['evaluation'],
        frozen_models=dict(files=72,bytes=sum(m['model_bytes'] for m in capsule['models']+training)),
        analysis_model_files_read=80,analysis_compact_label_rows_read=64,analysis_fit_oracle_updates=32*6*len(training),
        analysis_inherited_files_read=0,analysis_source_metadata_files_read=4,analysis_prediction_work=prediction_work)
    return dict(schema='acfqp.module_holdout.v155.analysis',complete=complete,primary_complete=complete and primary_complete,
        checks=checks,**outcome,costs=costs,inherited_cost_refs=run['inherited_cost_refs'],seconds=perf_counter()-started,
        estimand='Paired heldout root diagnostics of independently warm-fitted repairs; MSE change is new minus OLD, local gain change is (new_accept-old_accept)*retained target utility.',
        limitations='Descriptive means only: fold training sets overlap. Retained labels have sampling noise, and GATE targets use the fixed OLD continuation. Local gains do not establish fresh full-game improvement; acquisition is inherited once and fully charged to both arm budget views.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input','--directory',dest='input',type=Path,default=ROOT/'reports/controlled_predictive_module_holdout_v155')
    args=parser.parse_args();result=analyze(args.input)
    (args.input/'analysis.json').write_text(json.dumps(result,separators=(',',':'))+'\n')
    print(json.dumps(dict(complete=result['complete'],primary_complete=result['primary_complete'],checks=len(result['checks']),
        failed=[k for k,v in result['checks'].items() if not v],seconds=result['seconds'])),flush=True)
    raise SystemExit(0 if result['complete'] else 1)
