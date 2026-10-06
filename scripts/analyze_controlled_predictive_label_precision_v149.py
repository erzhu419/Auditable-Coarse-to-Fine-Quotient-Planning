"""Audit nested label budgets with fixed representation and independent evaluation."""
import argparse
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import sys
from time import perf_counter

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'src'))
from scripts import analyze_controlled_predictive_independent_labels_v148 as prior

previous,h1,planning,old=prior.previous,prior.h1,prior.planning,prior.old
model_audit=prior.prior
LIVES,QUERIES,METHODS=prior.LIVES,prior.QUERIES,('ZERO','UPDATED','TRAIN8','TRAIN32')
BASE,SUFFIXES,MAX_STEPS,WORKERS,EPOCHS,ALPHA=149*100000000,32,2000,4,32,.1
TRAIN_METHODS=('TRAIN8','TRAIN32')
mean,close,add_checks,read=prior.mean,prior.close,prior.add_checks,prior.read
COMPARISONS={'TRAIN32-TRAIN8':('TRAIN32','TRAIN8'),'TRAIN8-ZERO':('TRAIN8','ZERO'),
    'TRAIN32-ZERO':('TRAIN32','ZERO'),'UPDATED-ZERO':('UPDATED','ZERO')}


def expected_settings():
    return dict(lifecycles=list(LIVES),queries=QUERIES,methods=list(METHODS),train_methods=list(TRAIN_METHODS),
        train_replicas=[0,1,2,3],origins=['OLD','NEW'],total_train_roots=256,disagreement_roots=173,same_action_roots=83,
        training_suffixes=dict(TRAIN8=list(range(8)),TRAIN32=list(range(32))),epochs=EPOCHS,alpha=ALPHA,
        training_order='OLD16 then NEW16 per pass; zero initialization for each new learner',
        learner_representation='V144 six-cell signed n-tuple differences; unchanged UPDATED representation',
        update='three-component normalized LMS; denominator=sum(x*x)',
        target='paired H1_CONT minus H2 terminal components; exact immediate reward difference removed once',
        suffixes_per_root=SUFFIXES,paired_records=5536,physical_branches=11072,workers=WORKERS,
        continuation='H2',representation='SINGLE',p_four=.1,max_steps=MAX_STEPS,version_base=BASE,
        new_training_environment_samples=0,training_update_attempts=16384,full_policy_games=0,
        gate='strict positive recomposed advantage; ties H2',
        primary='equal history means; OLD16 and NEW16 separately and combined32; same-action exact zeros retained',
        comparison='TRAIN32 versus TRAIN8 MSE reduction and fixed-gate value; each versus ZERO and H2',
        cutoff_rule='retain all branches and costs; any cutoff blocks complete-cohort scientific claims',
        diagnostic_policy='freeze all fits and predictions before fresh labels; no refit, selection or early stopping')


def suffix_seeds(root):
    return [BASE+root['life']*1000000+list(QUERIES).index(root['query'])*100000+
        ('OLD','NEW').index(root['origin'])*50000+root['replica']*10000+root['slot']*100+s for s in range(SUFFIXES)]


def training_examples(capsule):
    """Reconstruct labels from retained branch components without runner helpers."""
    cohort=read(capsule['training_cohort_ref']);roots=cohort['roots']+cohort['same_action_roots']
    indexed={r['root_id']:r for r in roots};differences={key:{} for key in indexed};seen=[]
    views={m:previous.new_cost() for m in ('TRAIN8','TRAIN32')};checks=dict(training_branch_roster=True,
        training_branch_identity=True,training_labels_terminal=True)
    origin=Path(capsule['source_run_ref']).parent;source_run=read(capsule['source_run_ref'])
    for lifecycle in source_run['lifecycles']:
        for row in old.read_rows(origin/lifecycle['consequences_trace']):
            root=indexed[row['root_id']];e=root['example'];suffix=row['suffix'];seen.append((root['root_id'],suffix))
            checks['training_branch_identity'] &= (root['life']==lifecycle['life'] and row['seed']==root['suffix_seeds'][suffix]
                and row['continuation']=='H2' and set(row['branches'])==set(root['actions']))
            for action,branch in row['branches'].items():
                checks['training_labels_terminal'] &= branch['result']['status'] in ('WON','LOST')
                checks['training_branch_identity'] &= branch['root_board']==root['board'] and branch['first_action']==action and branch['seed']==row['seed']
                for method,budget in (('TRAIN8',8),('TRAIN32',32)):
                    if suffix<budget:previous.add_cost(views[method],branch)
            a,b=(row['branches'][e[k]]['result']['components'] for k in ('candidate_action','baseline_action'))
            differences[root['root_id']][suffix]=[a[k]-b[k] for k in range(3)]
    checks['training_branch_roster'] &= (len(seen)==len(set(seen))==5536 and
        set(seen)=={(r['root_id'],s) for r in cohort['roots'] for s in range(32)})
    examples={m:[] for m in ('TRAIN8','TRAIN32')}
    for root in sorted(roots,key=lambda r:(r['life'],list(QUERIES).index(r['query']),('OLD','NEW').index(r['origin']),r['replica'],r['slot'])):
        for method,budget in (('TRAIN8',8),('TRAIN32',32)):
            values=differences[root['root_id']];total=[mean(values[s][k] for s in range(budget)) for k in range(3)] if values else [0.,0.,0.]
            example=deepcopy(root['example']);example.update(origin=root['origin'],suffixes=budget if values else 0,training_method=method,
                target_total=total,target_tail=[total[0]-example['immediate_difference'],*total[1:]])
            examples[method].append(example)
    compact_views={m:dict(paired_records=v['physical_branches']//2,physical_branches=v['physical_branches'],
        sampled_transitions=v['environment_counts'].get('sampled_transitions',0)) for m,v in views.items()}
    return examples,compact_views,dict(trace_files=len(source_run['lifecycles']),paired_records=len(seen),
        branch_results=2*len(seen)),checks


def root_diagnostics(root,fresh_values,targets):
    same=root['example']['candidate_action']==root['example']['baseline_action']
    fresh=prior.moments(fresh_values,deterministic=same)
    blocks=[prior.moments(fresh_values[k:k+8],deterministic=same) for k in range(0,32,8)]
    labels={m.lower():prior.utility(targets[m]['target_total'],root['query']) for m in ('TRAIN8','TRAIN32')}
    labels['fresh']=fresh['mean'];models={}
    for method,prediction in root['predictions'].items():
        p=prediction['estimated_advantage'];selected=int(prediction['selected_h1']);zero=root['predictions']['ZERO']
        cells={}
        for name,y in labels.items():
            error=None if y is None else (p-y)**2
            cells[name]=dict(mse=error,mse_gain_over_zero=None if y is None else (zero['estimated_advantage']-y)**2-error,
                gate_advantage_vs_h2=None if y is None else selected*y,
                gate_advantage_vs_zero=None if y is None else (selected-int(zero['selected_h1']))*y)
            if name=='fresh':cells[name]['corrected_mse']=None if y is None else error-fresh['mean_variance']
        models[method]=dict(prediction=p,selected_h1=bool(selected),**cells)
    return dict(root_id=root['root_id'],origin=root['origin'],life=root['life'],query=root['query'],
        replica=root['replica'],slot=root['slot'],same_action=same,labels=labels,fresh=fresh,blocks=blocks,models=models)


def summarize_roots(rows):
    models={m:{label:{key:mean(r['models'][m][label][key] for r in rows)
        for key in ('mse','mse_gain_over_zero','gate_advantage_vs_h2','gate_advantage_vs_zero')+
        (('corrected_mse',) if label=='fresh' else ())} for label in ('train8','train32','fresh')} for m in METHODS}
    comparisons={name:{label:dict(mse_reduction=mean(None if r['models'][a][label]['mse'] is None else
        r['models'][b][label]['mse']-r['models'][a][label]['mse'] for r in rows),
        gate_advantage=mean(None if r['models'][a][label]['gate_advantage_vs_h2'] is None else
        r['models'][a][label]['gate_advantage_vs_h2']-r['models'][b][label]['gate_advantage_vs_h2'] for r in rows))
        for label in ('train8','train32','fresh')} for name,(a,b) in COMPARISONS.items()}
    blocks=[]
    for block in range(4):
        cells={m:dict(mse=mean(None if r['blocks'][block]['mean'] is None else
            (r['models'][m]['prediction']-r['blocks'][block]['mean'])**2 for r in rows),
            gate_advantage_vs_h2=mean(None if r['blocks'][block]['mean'] is None else
            int(r['models'][m]['selected_h1'])*r['blocks'][block]['mean'] for r in rows)) for m in METHODS}
        blocks.append(dict(models=cells,comparisons={name:dict(
            mse_reduction=None if cells[a]['mse'] is None else cells[b]['mse']-cells[a]['mse'],
            gate_advantage=None if cells[a]['gate_advantage_vs_h2'] is None else
            cells[a]['gate_advantage_vs_h2']-cells[b]['gate_advantage_vs_h2']) for name,(a,b) in COMPARISONS.items()}))
    return dict(roots=len(rows),disagreements=sum(not r['same_action'] for r in rows),
        complete=bool(rows) and all(r['fresh']['complete'] for r in rows),models=models,comparisons=comparisons,blocks=blocks,
        selected_h1={m:sum(r['models'][m]['selected_h1'] for r in rows) for m in METHODS},
        fresh_mean=mean(r['fresh']['mean'] for r in rows),fresh_mean_variance=mean(r['fresh']['mean_variance'] for r in rows))


def aggregate(rows,disagreement_only=False):
    output={}
    for origin in ('OLD','NEW','COMBINED'):
        output[origin]={}
        for query in QUERIES:
            cells=[dict(life=life,**summarize_roots([r for r in rows if (origin=='COMBINED' or r['origin']==origin) and
                r['query']==query and r['life']==life and (not disagreement_only or not r['same_action'])])) for life in LIVES]
            result=dict(lifecycles=cells,complete=all(c['complete'] for c in cells),roots=sum(c['roots'] for c in cells),
                disagreements=sum(c['disagreements'] for c in cells),
                selected_h1={m:sum(c['selected_h1'][m] for c in cells) for m in METHODS},
                fresh_mean=mean(c['fresh_mean'] for c in cells),fresh_mean_variance=mean(c['fresh_mean_variance'] for c in cells))
            for kind in ('models','comparisons'):
                result[kind]={m:{label:{key:mean(c[kind][m][label][key] for c in cells)
                    for key in cells[0][kind][m][label]} for label in ('train8','train32','fresh')}
                    for m in cells[0][kind]}
            result['blocks']=[{kind:{m:{key:mean(c['blocks'][b][kind][m][key] for c in cells)
                for key in cells[0]['blocks'][b][kind][m]} for m in cells[0]['blocks'][b][kind]}
                for kind in ('models','comparisons')} for b in range(4)]
            output[origin][query]=result
    return output


def cohort_checks(cohort,training,models):
    checks=dict(full_train_roster=True,source_root_identity=True,frozen_predictions=True,independent_suffix_seeds=True)
    expected={r['root_id']:r for r in training['roots']+training['same_action_roots']}
    rows=cohort['roots']+cohort['same_action_roots'];keys=[r['root_id'] for r in rows]
    checks['full_train_roster'] &= len(keys)==len(set(keys))==256 and set(keys)==set(expected)
    checks['full_train_roster'] &= len(cohort['roots'])==173 and len(cohort['same_action_roots'])==83
    checks['full_train_roster'] &= set(cohort['excluded_same_action_roots'])=={r['root_id'] for r in training['same_action_roots']}
    fresh_seeds=[];used_seeds=set()
    for root in rows:
        old_root=expected[root['root_id']];same=len(old_root['actions'])==1
        checks['source_root_identity'] &= all(root[k]==v for k,v in old_root.items() if k not in ('predictions','suffix_seeds'))
        checks['source_root_identity'] &= root['training_suffix_seeds']==old_root['suffix_seeds']
        seeds=[] if same else suffix_seeds(root);fresh_seeds.extend(seeds)
        used_seeds.update(old_root['suffix_seeds']);used_seeds.update(old_root['original_suffix_seeds'])
        checks['independent_suffix_seeds'] &= root['suffix_seeds']==seeds
        checks['frozen_predictions'] &= set(root['predictions'])==set(METHODS)
        for method in METHODS:
            prediction=(dict(root_id=root['root_id'],predicted_tail=[0.,0.,0.],estimated_advantage=0.,selected_h1=False)
                if same else model_audit.expected_prediction(root['example'],models[root['life'],root['query'],method],
                    'ZERO' if method=='ZERO' else 'UPDATED'))
            checks['frozen_predictions'] &= model_audit.prior.prior.prediction_matches(root['predictions'][method],prediction)
    checks['independent_suffix_seeds'] &= len(fresh_seeds)==len(set(fresh_seeds))==5536 and not(set(fresh_seeds)&used_seeds)
    return checks


def analyze(directory):
    started=perf_counter();directory=Path(directory).resolve()
    run,capsule,frozen,trained_frozen,cohort,retained=(read(directory/name) for name in
        ('run.json','source_capsule.json','frozen_inputs.json','frozen_training.json','cohort.json','examples.json'))
    checks=dict(source_roster=len(capsule['snapshots'])==4 and {s['life'] for s in capsule['snapshots']}==set(LIVES),
        source_complete=True,source_model_bindings=True,training_trace_bindings=True,models_frozen=True,cost_references=True,
        frozen_before_fit=frozen['status']=='frozen' and not frozen['lifecycles'] and not frozen['training_lifecycles'],
        frozen_before_acquisition=trained_frozen['status']=='trained_frozen' and not trained_frozen['lifecycles'],
        normalized_lms=True,training_order=True,model_storage=True,model_setup=True,model_schema=True,
        training_accounting=True,model_bindings=True,reference_models_unchanged=True,paired_record_roster=True,
        shared_suffix_seeds=True,distinct_action_branches=True,branch_roots=True,frozen_continuation=True,
        query_roster=True,model_loads=True,frozen_leaves=True,planner_spawn_law=True,acquisition_accounting=True,
        prediction_accounting=True,prediction_setup=True)
    checks['frozen_settings']=run['settings']==expected_settings()
    checks['frozen_before_fit'] &= all(frozen[k]==run[k] for k in ('settings','inherited_cost_refs'))
    checks['frozen_before_acquisition'] &= all(trained_frozen[k]==run[k] for k in ('settings','inherited_cost_refs','training_lifecycles'))
    sources={s['life']:s for s in capsule['snapshots']};models={};trained={r['life']:r for r in run['training_lifecycles']}
    checks['training_lifecycle_roster']=len(trained)==len(run['training_lifecycles'])==4 and set(trained)==set(LIVES)
    origin=Path(capsule['source_run_ref']).parent;source_run=read(capsule['source_run_ref']);source_analysis=read(origin/'analysis.json')
    checks['source_complete'] &= source_run['status']=='complete' and source_analysis['complete'] and source_analysis['primary_complete']
    original_capsule=read(origin/'source_capsule.json');reference_run=read(capsule['reference_run_ref'])
    reference_trained={r['life']:r for r in reference_run['lifecycles']};reference_origin=Path(capsule['reference_run_ref']).parent
    checks['source_model_bindings'] &= capsule['reference_run_ref']==original_capsule['source_run_ref']
    for source in capsule['snapshots']:
        life=source['life'];record=next(r for r in source_run['lifecycles'] if r['life']==life)
        checks['training_trace_bindings'] &= Path(source['training_trace_ref'])==origin/record['consequences_trace']
        for query in QUERIES:
            for method in ('ZERO','UPDATED'):
                ref=reference_trained[life]['queries'][query]['models'][method]
                path=Path(source['reference_models'][query][method]);payload=read(path)
                checks['source_model_bindings'] &= path==reference_origin/ref['model_ref'] and model_audit.prior.state(payload)==ref['frozen_state']
    checks['cost_references'] &= run['inherited_cost_refs']==capsule['cost_refs'] and all(
        all(field in read(r['path']) for field in r['fields']) for r in capsule['cost_refs'])
    examples,budget_views,source_reads,training_checks=training_examples(capsule);add_checks(checks,training_checks)
    checks['retained_training_labels']=retained['methods']==examples
    checks['retained_training_accounting']=retained['training_budget_views']==budget_views and retained['source_rows_read']==source_reads
    costs=dict(new_acquisition=previous.new_cost(),acquisition_by_query={q:previous.new_cost() for q in QUERIES},
        acquisition_seconds=sum(r['seconds'] for r in run['lifecycles']),retained_train_examples=256,
        training_seconds=sum(r['seconds'] for r in run['training_lifecycles']),training_counts=Counter(),
        training_budget_views=budget_views,training_source_rows_read=source_reads,new_training_environment_samples=0,
        analysis_training_source_rows_read=source_reads,analysis_lms_attempts=0,analysis_replay_swipes=0,
        analysis_frozen_prediction_records=1024,model_accounting=[])
    for life in LIVES:
        source=sources[life];lifecycle=trained[life]
        checks['query_roster'] &= set(lifecycle['queries'])==set(QUERIES)
        for query in QUERIES:
            qdata=lifecycle['queries'][query]
            sequences={m:[e for e in rows if e['life']==life and e['query']==query] for m,rows in examples.items()}
            checks['training_order'] &= qdata['train_roots']==[e['root_id'] for e in sequences['TRAIN8']]
            checks['model_bindings'] &= qdata['binding']==dict(life=life,query=query,continuation='H2',leaf_ref=source['leaves'][query]['SINGLE']['model_ref'])
            checks['query_roster'] &= set(qdata['models'])==set(METHODS)
            for method in METHODS:
                mdata=qdata['models'][method];path=directory/mdata['model_ref'];payload=read(path);state=model_audit.prior.state(payload)
                if method in TRAIN_METHODS:
                    expected=model_audit.fit_oracle(sequences[method],method='UPDATED');costs['analysis_lms_attempts']+=expected['attempts']
                    weights=expected['weights'];fit=expected['work']
                    checks['normalized_lms'] &= model_audit.model_matches(payload,expected) and expected['attempts']==1024
                    checks['models_frozen'] &= mdata['before']==dict(radix=11,updates=0,frozen=False,weights=[])
                else:
                    original=read(source['reference_models'][query][method]);weights={int(r[0]):tuple(r[1:]) for r in original['weights']};fit=Counter()
                    checks['reference_models_unchanged'] &= state==model_audit.prior.state(original)==mdata['before']
                    if method=='ZERO':checks['reference_models_unchanged'] &= not weights and state['updates']==0
                models[life,query,method]=weights;n=len(weights);feature_method='ZERO' if method=='ZERO' else 'UPDATED'
                checks['model_schema'] &= payload['schema']==('acfqp.shared_local_advantage.v147' if method=='ZERO' else 'acfqp.paired_advantage.v144')
                checks['training_order'] &= mdata['training_roots']==([e['root_id'] for e in sequences[method]] if method in TRAIN_METHODS else [])
                checks['models_frozen'] &= mdata['frozen_state']==state and state['frozen']
                checks['model_storage'] &= mdata['model_bytes']==path.stat().st_size and payload['storage']==dict(
                    weight_addresses=n,weight_parameters=3*n,numeric_weight_bytes=24*n,numeric_address_bytes=8*n)
                checks['model_setup'] &= Counter(mdata['setup_counts'])==Counter(payload['setup_counts'])==model_audit.setup_counts(feature_method,n,method not in TRAIN_METHODS)
                checks['training_accounting'] &= Counter(mdata['fit_counts'])==fit and Counter(mdata['total_counts'])==Counter(payload['counts'])==fit+Counter(
                    checkpoint_saves=1,checkpoint_saved_addresses=n,checkpoint_saved_parameters=3*n)
                costs['training_counts'].update(fit)
                costs['model_accounting'].append(dict(stage='training',life=life,query=query,method=method,
                    model_bytes=mdata['model_bytes'],storage=payload['storage'],setup_counts=mdata['setup_counts'],fit_counts=mdata['fit_counts'],total_counts=mdata['total_counts']))
    checks['training_accounting'] &= costs['training_counts']['update_calls']==16384
    training_cohort=read(capsule['training_cohort_ref']);add_checks(checks,cohort_checks(cohort,training_cohort,models))
    roots={r['root_id']:r for r in cohort['roots']+cohort['same_action_roots']};prediction_counts=Counter();work_keys=[]
    for item in cohort['prediction_work']:
        key=item['life'],item['query'],item['method'];work_keys.append(key);life,query,method=key
        feature_method='ZERO' if method=='ZERO' else 'UPDATED';expected=Counter()
        for root in roots.values():
            if root['life']==life and root['query']==query and len(root['actions'])==2:
                e=root['example'];expected.update(model_audit.prediction_work(e['candidate_after'],e['baseline_after'],feature_method))
        checks['prediction_accounting'] &= Counter(item['counts'])==expected and item['state_unchanged']
        checks['prediction_setup'] &= (Path(item['model_ref'])==directory/trained[life]['queries'][query]['models'][method]['model_ref'] and
            Counter(item['setup_counts'])==model_audit.setup_counts(feature_method,len(models[key]),True))
        prediction_counts.update(item['counts'])
    checks['prediction_accounting'] &= len(work_keys)==len(set(work_keys))==32 and set(work_keys)=={(l,q,m) for l in LIVES for q in QUERIES for m in METHODS}
    costs.update(prediction_counts=dict(prediction_counts),prediction_work=cohort['prediction_work'],
        analysis_prediction_oracle_equivalent_counts=dict(prediction_counts))
    records={r['root_id']:{} for r in cohort['roots']};seen=[]
    checks['lifecycle_roster']=len(run['lifecycles'])==4 and {r['life'] for r in run['lifecycles']}==set(LIVES)
    for lifecycle in run['lifecycles']:
        life=lifecycle['life'];source=sources[life];local={q:previous.new_cost() for q in QUERIES};pairs=Counter()
        for row in old.read_rows(directory/lifecycle['consequences_trace']):
            key=row['root_id'];root=roots[key];suffix=row['suffix'];seen.append((key,suffix));query=root['query'];pairs[query]+=1
            checks['paired_record_roster'] &= key in records and root['life']==life and 0<=suffix<SUFFIXES
            checks['shared_suffix_seeds'] &= row['seed']==root['suffix_seeds'][suffix]
            checks['frozen_continuation'] &= row['continuation']=='H2'
            checks['distinct_action_branches'] &= set(row['branches'])==set(root['actions'])
            valid=True
            for action,branch in row['branches'].items():
                checks['branch_roots'] &= branch['root_board']==root['board'] and branch['first_action']==action and branch['seed']==row['seed']
                branch_checks,swipes=previous.replay_branch(branch,query,max_steps=MAX_STEPS);add_checks(checks,branch_checks)
                costs['analysis_replay_swipes']+=swipes
                valid &= all(branch_checks.values()) and branch['result']['status'] in ('WON','LOST')
                for cell in (costs['new_acquisition'],costs['acquisition_by_query'][query],local[query]):previous.add_cost(cell,branch)
            a,b=(row['branches'][root['example'][k]]['result'] for k in ('candidate_action','baseline_action'))
            records[key][suffix]=a['utility']-b['utility'] if valid else None
        checks['query_roster'] &= set(lifecycle['queries'])==set(QUERIES)
        for query,qdata in lifecycle['queries'].items():
            cell=local[query];count=sum(r['life']==life and r['query']==query for r in cohort['roots'])
            checks['acquisition_accounting'] &= (qdata['roots']==count and qdata['paired_records']==pairs[query]==count*32 and
                qdata['physical_branches']==cell['physical_branches']==count*64 and all(Counter(qdata[k])==cell[k]
                for k in ('statuses','environment_counts','policy_counts')))
            checks['model_loads'] &= h1.teacher_analysis.teacher_loads_valid(qdata['loads'],source,'SINGLE',query)
            checks['frozen_leaves'] &= qdata['parent_before']==qdata['parent_after']==planning.previous.model_state(source,query,'PARENT',0)
            checks['frozen_leaves'] &= qdata['leaf_before']==qdata['leaf_after']==planning.expected_model_state(source,query,'SINGLE')
            checks['planner_spawn_law'] &= qdata['spawn_probabilities']==planning.expected_spawn_probabilities(source)
            costs['model_accounting'].append(dict(life=life,query=query,loads=qdata['loads']))
        print(json.dumps(dict(event='audited_acquisition',life=life,replayed_swipes=costs['analysis_replay_swipes'])),flush=True)
    checks['paired_record_roster'] &= len(seen)==len(set(seen))==5536 and set(seen)=={(r,s) for r in records for s in range(32)}
    checks['distinct_action_branches'] &= costs['new_acquisition']['physical_branches']==11072
    targets={m:{e['root_id']:e for e in rows} for m,rows in examples.items()}
    diagnostics=[root_diagnostics(root,[records[key].get(s) for s in range(32)] if key in records else [],
        {m:values[key] for m,values in targets.items()}) for key,root in roots.items()]
    full,disagreements=aggregate(diagnostics),aggregate(diagnostics,True)
    costs['new_environment_samples']=costs['new_acquisition']['environment_counts'].get('sampled_transitions',0)
    complete=run['status']=='complete' and all(checks.values())
    return dict(schema='acfqp.label_precision.v149.analysis',complete=complete,
        primary_complete=complete and all(c['complete'] for group in full.values() for c in group.values()),checks=checks,
        full_train=full,disagreement_only=disagreements,root_diagnostics=diagnostics,costs=costs,
        inherited_cost_refs=run['inherited_cost_refs'],seconds=perf_counter()-started,
        estimand='Fixed TRAIN roots; equal roots within history, equal four histories; same-action exact zeros retained.',
        interpretation='Training labels overlap between nested budgets; only fresh V149 suffixes independently evaluate fixed predictions. No new full-policy games or adoption test.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input','--directory',dest='input',type=Path,default=ROOT/'reports/controlled_predictive_label_precision_v149')
    args=parser.parse_args();result=analyze(args.input)
    (args.input/'analysis.json').write_text(json.dumps(result,separators=(',',':'))+'\n')
    print(json.dumps(dict(complete=result['complete'],primary_complete=result['primary_complete'],checks=len(result['checks']),
        failed=[k for k,v in result['checks'].items() if not v],seconds=result['seconds'])),flush=True)
    raise SystemExit(0 if result['complete'] else 1)
