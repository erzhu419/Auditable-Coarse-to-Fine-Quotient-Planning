"""Audit independent paired labels for fixed TRAIN roots and frozen predictions."""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys
from time import perf_counter

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'src'))
from scripts import analyze_controlled_predictive_shared_local_advantage_v147 as prior

previous,h1,planning,old=prior.previous,prior.h1,prior.planning,prior.old
LIVES,QUERIES,METHODS=prior.LIVES,prior.QUERIES,('ZERO','UPDATED','SHARED')
BASE,SUFFIXES,MAX_STEPS=148*100000000,32,2000
mean,close,add_checks=prior.mean,prior.close,prior.add_checks
read=lambda path:json.loads(Path(path).read_text())


def expected_settings():
    return dict(lifecycles=list(LIVES),queries=QUERIES,methods=list(METHODS),
        train_replicas=[0,1,2,3],origins=['OLD','NEW'],total_train_roots=256,
        disagreement_roots=173,same_action_roots=83,suffixes_per_root=32,
        paired_records=5536,physical_branches=11072,workers=4,
        continuation='H2',representation='SINGLE',p_four=.1,max_steps=2000,
        version_base=BASE,new_training_updates=0,full_policy_games=0,
        root_selection='all retained TRAIN action disagreements; same actions retained as exact zeros',
        budget='32 independent fresh suffixes per disagreement; four fixed blocks of eight; no early stopping',
        primary='equal history means over all 16 roots per origin/query/history; disagreement-only secondary',
        cutoff_rule='retain all branches and costs; any cutoff blocks complete-cohort scientific claims',
        diagnostic_policy='fixed models and predictions before acquisition; no refit, model selection or gate change')


def suffix_seeds(root):
    return [BASE+root['life']*1000000+list(QUERIES).index(root['query'])*100000+
        ('OLD','NEW').index(root['origin'])*50000+root['replica']*10000+root['slot']*100+s for s in range(SUFFIXES)]


def utility(components,query):
    q=QUERIES[query]
    return q['reward_weight']*components[0]-q['failure_penalty']*components[1]+q['goal_bonus']*components[2]


def moments(values,deterministic=False):
    values=list(values);complete=all(v is not None for v in values) and (bool(values) or deterministic)
    average=(mean(values) if values else 0.) if complete else None
    variance=(sum((v-average)**2 for v in values)/(len(values)-1) if len(values)>1 else 0.) if complete else None
    return dict(n=len(values),complete=complete,mean=average,sample_variance=variance,
        mean_variance=variance/len(values) if complete and values else (0. if complete else None))


def root_diagnostics(root,fresh_values):
    same=root['example']['candidate_action']==root['example']['baseline_action']
    old_stat=dict(n=8,complete=True,mean=utility(root['example']['target_total'],root['query']))
    fresh_stat=moments(fresh_values,deterministic=same)
    blocks=[moments(fresh_values[k:k+8],deterministic=same) for k in range(0,32,8)]
    sign=lambda v:None if v is None else int(v>0)-int(v<0)
    models={};predictions=root['predictions'];zero=predictions['ZERO']
    for method,prediction in predictions.items():
        p=prediction['estimated_advantage'];z=zero['estimated_advantage']
        selected=int(prediction['selected_h1']);zero_selected=int(zero['selected_h1'])
        cells={}
        for label,stat in (('old',old_stat),('fresh',fresh_stat)):
            y=stat['mean'];error=None if y is None else (p-y)**2
            cells[label]=dict(mse=error,mse_gain_over_zero=None if y is None else (z-y)**2-error,
                gate_advantage_vs_h2=None if y is None else selected*y,
                gate_advantage_vs_zero=None if y is None else (selected-zero_selected)*y)
            if label=='fresh':cells[label]['corrected_mse']=None if error is None else error-stat['mean_variance']
        models[method]=dict(prediction=p,selected_h1=bool(selected),**cells)
    return dict(root_id=root['root_id'],origin=root['origin'],life=root['life'],query=root['query'],
        replica=root['replica'],slot=root['slot'],same_action=same,old=old_stat,fresh=fresh_stat,
        old_sign=sign(old_stat['mean']),fresh_sign=sign(fresh_stat['mean']),
        sign_reproduced=None if fresh_stat['mean'] is None else sign(old_stat['mean'])==sign(fresh_stat['mean']),
        old_fresh_squared_difference=None if fresh_stat['mean'] is None else (old_stat['mean']-fresh_stat['mean'])**2,
        blocks=blocks,models=models)


def summarize_roots(rows):
    complete=all(r['fresh']['complete'] for r in rows) and bool(rows)
    models={}
    for method in METHODS:
        cells={}
        for label in ('old','fresh'):
            metrics=('mse','mse_gain_over_zero','gate_advantage_vs_h2','gate_advantage_vs_zero')+(
                ('corrected_mse',) if label=='fresh' else ())
            cells[label]={metric:mean(r['models'][method][label][metric] for r in rows) for metric in metrics}
        models[method]=dict(selected_h1=sum(r['models'][method]['selected_h1'] for r in rows),**cells)
    informative=[r for r in rows if not r['same_action']]
    transitions=Counter(f"{r['old_sign']}->{r['fresh_sign']}" for r in informative if r['fresh']['complete'])
    return dict(roots=len(rows),disagreements=len(informative),same_action=sum(r['same_action'] for r in rows),
        complete=complete,models=models,old_mean=mean(r['old']['mean'] for r in rows),
        fresh_mean=mean(r['fresh']['mean'] for r in rows),
        old_fresh_mse=mean(r['old_fresh_squared_difference'] for r in rows),
        fresh_mean_variance=mean(r['fresh']['mean_variance'] for r in rows),
        sign_transitions=dict(transitions),sign_reproduced=sum(r['sign_reproduced'] is True for r in informative),
        blocks=[dict(mean=mean(r['blocks'][block]['mean'] for r in rows),models={m:dict(
            mse_gain_over_zero=mean(None if r['blocks'][block]['mean'] is None else
                (r['models']['ZERO']['prediction']-r['blocks'][block]['mean'])**2-
                (r['models'][m]['prediction']-r['blocks'][block]['mean'])**2 for r in rows),
            gate_advantage_vs_h2=mean(None if r['blocks'][block]['mean'] is None else
                int(r['models'][m]['selected_h1'])*r['blocks'][block]['mean'] for r in rows),
            gate_advantage_vs_zero=mean(None if r['blocks'][block]['mean'] is None else
                (int(r['models'][m]['selected_h1'])-int(r['models']['ZERO']['selected_h1']))*
                r['blocks'][block]['mean'] for r in rows)) for m in METHODS}) for block in range(4)])


def aggregate(rows,disagreement_only=False):
    output={}
    for origin in ('OLD','NEW'):
        output[origin]={}
        for query in QUERIES:
            cells=[dict(life=life,**summarize_roots([r for r in rows if r['origin']==origin and
                r['query']==query and r['life']==life and (not disagreement_only or not r['same_action'])])) for life in LIVES]
            models={m:{label:{key:mean(c['models'][m][label][key] for c in cells)
                for key in cells[0]['models'][m][label]} for label in ('old','fresh')} for m in METHODS}
            output[origin][query]=dict(lifecycles=cells,complete=all(c['complete'] for c in cells),models=models,
                roots=sum(c['roots'] for c in cells),disagreements=sum(c['disagreements'] for c in cells),
                **{key:mean(c[key] for c in cells) for key in ('old_mean','fresh_mean','old_fresh_mse','fresh_mean_variance')},
                sign_transitions=dict(sum((Counter(c['sign_transitions']) for c in cells),Counter())),
                sign_reproduced=sum(c['sign_reproduced'] for c in cells),
                blocks=[dict(mean=mean(c['blocks'][b]['mean'] for c in cells),models={m:{k:
                    mean(c['blocks'][b]['models'][m][k] for c in cells) for k in cells[0]['blocks'][b]['models'][m]}
                    for m in METHODS}) for b in range(4)])
    return output


def source_inputs(capsule):
    examples={};cohorts={}
    for origin,key in (('OLD','old_examples_ref'),('NEW','new_examples_ref')):
        path=Path(capsule[key]);examples[origin]=[e for e in read(path)['examples'] if e['split']=='TRAIN']
        original=read(path.parent/'source_capsule.json')
        cohort_path=original['cohort_ref'] if origin=='OLD' else path.parent/'cohort.json'
        cohorts[origin]={r['root_id']:r for r in read(cohort_path)['roots']}
    return examples,cohorts


def cohort_checks(cohort,examples,originals,models):
    checks=dict(full_train_roster=True,disagreement_roster=True,same_action_roster=True,source_root_identity=True,
        frozen_predictions=True,independent_suffix_seeds=True,whole_game_split=True)
    expected={(o,e['root_id']):e for o,rows in examples.items() for e in rows}
    rows=cohort['roots']+cohort['same_action_roots'];keys=[(r['origin'],r['root_id']) for r in rows]
    checks['full_train_roster']=len(keys)==len(set(keys))==256 and set(keys)==set(expected)
    checks['whole_game_split']=Counter((o,e['life'],e['query'],e['replica']) for (o,_),e in expected.items())==Counter(
        {(o,l,q,r):4 for o in ('OLD','NEW') for l in LIVES for q in QUERIES for r in range(4)})
    expected_same=[];expected_fresh=[];all_seeds=[];old_seeds=set()
    for root in rows:
        key=root['origin'],root['root_id'];example=expected[key];original=originals[root['origin']][root['root_id']]
        same=example['candidate_action']==example['baseline_action'];(expected_same if same else expected_fresh).append(root['root_id'])
        checks['source_root_identity'] &= root['example']==example and root['original_suffix_seeds']==original['suffix_seeds'] and all(root.get(k)==v for k,v in original.items() if k not in ('actions','suffix_seeds'))
        checks['source_root_identity'] &= root['actions']==sorted(set((example['candidate_action'],example['baseline_action'])))
        seeds=[] if same else suffix_seeds(root);all_seeds.extend(seeds);old_seeds.update(original['suffix_seeds'])
        checks['independent_suffix_seeds'] &= root['suffix_seeds']==seeds
        checks['frozen_predictions'] &= set(root['predictions'])==set(METHODS)
        for method in METHODS:
            prediction=(dict(root_id=root['root_id'],predicted_tail=[0.,0.,0.],estimated_advantage=0.,selected_h1=False)
                if same else prior.expected_prediction(example,models[root['life'],root['query'],method],method))
            checks['frozen_predictions'] &= prior.prior.prior.prediction_matches(root['predictions'][method],prediction)
    checks['disagreement_roster'] &= len(cohort['roots'])==len(expected_fresh)==173 and {r['root_id'] for r in cohort['roots']}==set(expected_fresh)
    checks['same_action_roster'] &= len(cohort['same_action_roots'])==len(expected_same)==83 and set(cohort['excluded_same_action_roots'])==set(expected_same)
    checks['independent_suffix_seeds'] &= len(all_seeds)==len(set(all_seeds))==173*32 and not(set(all_seeds)&old_seeds)
    return checks


def analyze(directory):
    started=perf_counter();directory=Path(directory).resolve()
    run,capsule,frozen,cohort=(read(directory/name) for name in ('run.json','source_capsule.json','frozen_inputs.json','cohort.json'))
    checks=dict(source_roster=len(capsule['snapshots'])==4 and {s['life'] for s in capsule['snapshots']}==set(LIVES),
        source_complete=True,source_model_bindings=True,models_frozen=True,cost_references=True,
        frozen_before_acquisition=frozen['status']=='frozen' and not frozen['lifecycles'],
        paired_record_roster=True,shared_suffix_seeds=True,distinct_action_branches=True,branch_roots=True,
        frozen_continuation=True,query_roster=True,model_loads=True,frozen_leaves=True,planner_spawn_law=True,
                acquisition_accounting=True,prediction_accounting=True,prediction_setup=True)
    checks['frozen_settings']=run['settings']==expected_settings()
    checks['frozen_before_acquisition'] &= all(frozen[k]==run[k] for k in ('settings','inherited_cost_refs'))
    sources={s['life']:s for s in capsule['snapshots']};models={}
    origin=Path(capsule['source_run_ref']).parent;source_run=read(origin/'run.json');source_analysis=read(origin/'analysis.json')
    checks['source_complete'] &= source_run['status']=='complete' and source_analysis['complete'] and source_analysis['primary_complete']
    fitted={r['life']:r for r in source_run['lifecycles']}
    for life,source in sources.items():
        for query in QUERIES:
            for method in METHODS:
                path=Path(source['advantage_models'][query][method]);payload=read(path)
                reference=fitted[life]['queries'][query]['models'][method]
                checks['source_model_bindings'] &= path==origin/reference['model_ref'] and prior.prior.state(payload)==reference['frozen_state']
                checks['models_frozen'] &= payload['frozen']
                models[life,query,method]={row[0]:tuple(row[1:]) for row in payload['weights']}
    checks['cost_references'] &= run['inherited_cost_refs']==capsule['cost_refs'] and all(
        all(field in read(r['path']) for field in r['fields']) for r in capsule['cost_refs'])
    examples,originals=source_inputs(capsule);add_checks(checks,cohort_checks(cohort,examples,originals,models))
    roots={r['root_id']:r for r in cohort['roots']+cohort['same_action_roots']}
    prediction_counts=Counter();analysis_prediction_counts=Counter();work_keys=[]
    for item in cohort['prediction_work']:
        key=item['life'],item['query'],item['method'];work_keys.append(key);life,query,method=key
        expected=Counter()
        for root in roots.values():
            if root['life']==life and root['query']==query and len(root['actions'])==2:
                e=root['example'];expected.update(prior.prediction_work(e['candidate_after'],e['baseline_after'],method))
        checks['prediction_accounting'] &= Counter(item['counts'])==expected and item['state_unchanged']
        checks['prediction_setup'] &= (Path(item['model_ref'])==Path(sources[life]['advantage_models'][query][method]) and
            Counter(item['setup_counts'])==prior.setup_counts(method,len(models[key]),True))
        prediction_counts.update(item['counts']);analysis_prediction_counts.update(expected)
    checks['prediction_accounting'] &= len(work_keys)==len(set(work_keys))==24 and set(work_keys)=={
        (l,q,m) for l in LIVES for q in QUERIES for m in METHODS}
    costs=dict(new_acquisition=previous.new_cost(),acquisition_by_query={q:previous.new_cost() for q in QUERIES},
        acquisition_seconds=sum(r['seconds'] for r in run['lifecycles']),retained_train_examples=256,
        prediction_work=cohort['prediction_work'],prediction_counts=dict(prediction_counts),
        analysis_prediction_oracle_equivalent_counts=dict(analysis_prediction_counts),analysis_replay_swipes=0,
        analysis_frozen_prediction_records=len(roots)*3,model_accounting=[])
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
    checks['paired_record_roster'] &= len(seen)==len(set(seen))==5536 and set(seen)=={(r,s) for r in records for s in range(32)}
    checks['distinct_action_branches'] &= costs['new_acquisition']['physical_branches']==11072
    diagnostics=[root_diagnostics(root,[records[key].get(s) for s in range(32)] if key in records else []) for key,root in roots.items()]
    full,disagreements=aggregate(diagnostics),aggregate(diagnostics,True)
    costs['new_environment_samples']=costs['new_acquisition']['environment_counts'].get('sampled_transitions',0)
    complete=run['status']=='complete' and all(checks.values())
    return dict(schema='acfqp.independent_labels.v148.analysis',complete=complete,
        primary_complete=complete and all(c['complete'] for group in full.values() for c in group.values()),checks=checks,
        full_train=full,disagreement_only=disagreements,root_diagnostics=diagnostics,costs=costs,
        inherited_cost_refs=run['inherited_cost_refs'],seconds=perf_counter()-started,
        estimand='Fixed TRAIN roots; equal roots within each history, equal four histories; same-action roots retained with exact zero.',
        interpretation='Independent H2-continuation labels diagnose in-sample fit reliability; no refit, policy rollout, or adoption test.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input','--directory',dest='input',type=Path,default=ROOT/'reports/controlled_predictive_independent_labels_v148')
    args=parser.parse_args();result=analyze(args.input)
    (args.input/'analysis.json').write_text(json.dumps(result,separators=(',',':'))+'\n')
    print(json.dumps(dict(complete=result['complete'],primary_complete=result['primary_complete'],checks=len(result['checks']),
        failed=[k for k,v in result['checks'].items() if not v],seconds=result['seconds'])),flush=True)
    raise SystemExit(0 if result['complete'] else 1)
