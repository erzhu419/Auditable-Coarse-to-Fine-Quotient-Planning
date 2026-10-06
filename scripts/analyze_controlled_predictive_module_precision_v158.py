"""Independent audit of fresh nested training labels and common evaluation suffixes."""
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor,as_completed
import json
import math
from pathlib import Path
import sys
from time import perf_counter

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'src'))
from scripts import analyze_controlled_predictive_module_diagnosis_v153 as diagnosis
from scripts import analyze_controlled_predictive_module_split_half_v157 as arithmetic

prior=diagnosis.prior
LIVES,QUERIES,SOURCES=prior.LIVES,prior.QUERIES,diagnosis.SOURCES
SPLITS=('TRAIN','EVAL');MODES=('H_GATE','M_GATE');BUDGETS=(8,16,32)
BASE,MAX_STEPS,WORKERS=158*100000000,2000,4
GAINS=('vs_old','vs_reject','vs_accept')
DIAGNOSTICS=('accept_rate','old_accept_rate','decision_change_rate','train_eval_sign_agreement','train_advantage','eval_advantage','apparent_gain_vs_old','selection_optimism')
read,mean,add_checks,equivalent=prior.read,prior.mean,prior.add_checks,arithmetic.equivalent


def branch_seed(root,split,suffix):
    return BASE+20000000+SPLITS.index(split)*10000000+root['life']*1000000+list(QUERIES).index(root['query'])*100000+SOURCES.index(root['source_method'])*10000+root['slot']*100+suffix


def branch_roster(roots):
    return [dict(branch_id=f'{r["root_id"]}:{split}:{suffix}:{mode}',root_id=r['root_id'],split=split,suffix=suffix,mode=mode,seed=branch_seed(r,split,suffix))
        for split in SPLITS for r in roots for suffix in range(32) for mode in MODES]


def metadata(root):
    return {k:root[k] for k in ('root_id','life','query','source_method','slot')}


def paired_outcomes(roots,outcomes,split):
    index={(r['root_id'],r['suffix'],r['mode']):r for r in outcomes if r['split']==split};pairs=[]
    for root in sorted(roots,key=lambda r:(r['life'],r['query'],r['source_method'],r['slot'],r['root_id'])):
        for suffix in range(32):
            left,right=(index[root['root_id'],suffix,m] for m in MODES);complete=left['status']!='CUTOFF' and right['status']!='CUTOFF'
            components=[b-a for a,b in zip(left['components'],right['components'])] if complete else None
            pairs.append(dict(**metadata(root),split=split,suffix=suffix,complete=complete,components=components,
                advantage=prior.utility(components,root['query']) if complete else None))
    return pairs


def component_mean(pairs):
    return [mean(r['components'][c] for r in pairs) for c in range(3)] if all(r['complete'] for r in pairs) else None


def selectors(roots,pairs):
    index={(r['root_id'],r['suffix']):r for r in pairs};result=[]
    for root in sorted(roots,key=lambda r:(r['life'],r['query'],r['source_method'],r['slot'],r['root_id'])):
        for budget in BUDGETS:
            components=component_mean([index[root['root_id'],s] for s in range(budget)])
            value=prior.utility(components,root['query']) if components is not None else None
            result.append(dict(**metadata(root),budget=budget,train_components=components,train_advantage=value,
                accept=None if value is None else value>0,old_accept=root['prediction']['advantage']>0,complete=components is not None))
    return result


def moments(values):
    average=mean(values);complete=average is not None
    variance=sum((v-average)**2 for v in values)/(len(values)-1) if complete and len(values)>1 else (0. if complete else None)
    return dict(samples=values,complete=complete,mean=average,sample_variance=variance,mean_variance=variance/len(values) if complete else None)


def interval(average,variance,complete):
    se=math.sqrt(variance) if complete else None
    return dict(complete=complete,mean=average,conditional_suffix_se=se,conditional_suffix_ci95=[average-1.96*se,average+1.96*se] if complete else None)


def root_pool(stats):
    complete=bool(stats) and all(r['complete'] for r in stats)
    variance=sum(r['mean_variance'] for r in stats)/len(stats)**2 if complete else None
    return interval(mean(r['mean'] for r in stats),variance,complete)


def history_pool(stats):
    complete=len(stats)==4 and all(r['complete'] for r in stats)
    variance=sum(r['conditional_suffix_se']**2 for r in stats)/16 if complete else None
    return interval(mean(r['mean'] for r in stats),variance,complete)


def evaluate(selected,pairs):
    index={(r['root_id'],r['suffix']):r for r in pairs};rows=[]
    for selector in selected:
        values=[index[selector['root_id'],s] for s in range(32)];components=component_mean(values)
        value=prior.utility(components,selector['query']) if components is not None else None
        accepted=selector['accept'];old=selector['old_accept'];gains={}
        for gain,baseline in (('vs_old',int(old)),('vs_reject',0),('vs_accept',1)):
            samples=[None if accepted is None or not row['complete'] else (int(accepted)-baseline)*row['advantage'] for row in values]
            gains[gain]=moments(samples)
        apparent=None if accepted is None else (int(accepted)-int(old))*selector['train_advantage']
        rows.append(dict(selector,complete=selector['complete'] and components is not None,eval_components=components,eval_advantage=value,
            train_eval_sign_agreement=None if accepted is None or value is None else int(accepted==(value>0)),
            decision_change=None if accepted is None else int(accepted!=old),apparent_gain_vs_old=apparent,
            selection_optimism=None if apparent is None or gains['vs_old']['mean'] is None else apparent-gains['vs_old']['mean'],gains=gains))
    summaries=[]
    for query in QUERIES:
        for budget in BUDGETS:
            for source in ('ALL',*SOURCES):
                group=[r for r in rows if r['query']==query and r['budget']==budget and (source=='ALL' or r['source_method']==source)];histories=[]
                for life in LIVES:
                    local=[r for r in group if r['life']==life];diagnostics=[]
                    for row in local:
                        diagnostics.append(dict(accept_rate=None if row['accept'] is None else int(row['accept']),old_accept_rate=int(row['old_accept']),
                            decision_change_rate=row['decision_change'],**{k:row[k] for k in DIAGNOSTICS[3:]}))
                    histories.append(dict(life=life,roots=len(local),complete=bool(local) and all(r['complete'] for r in local),
                        means={k:mean(d[k] for d in diagnostics) for k in DIAGNOSTICS},gains={k:root_pool([r['gains'][k] for r in local]) for k in GAINS}))
                summaries.append(dict(query=query,budget=budget,source_method=source,roots=len(group),complete=all(h['complete'] for h in histories),
                    means={k:mean(h['means'][k] for h in histories) for k in DIAGNOSTICS},gains={k:history_pool([h['gains'][k] for h in histories]) for k in GAINS},per_history=histories))
    lookup={(r['root_id'],r['budget']):r for r in selected};differences=[]
    for high in [r for r in selected if r['budget']==32]:
        low=lookup[high['root_id'],8];coefficient=int(high['accept'])-int(low['accept']) if high['complete'] and low['complete'] else None
        values=[index[high['root_id'],s] for s in range(32)]
        differences.append(dict(**metadata(high),gain=moments([None if coefficient is None or not r['complete'] else coefficient*r['advantage'] for r in values])))
    comparisons=[]
    for query in QUERIES:
        for source in ('ALL',*SOURCES):
            group=[r for r in differences if r['query']==query and (source=='ALL' or r['source_method']==source)]
            histories=[dict(life=life,roots=sum(r['life']==life for r in group),gain=root_pool([r['gain'] for r in group if r['life']==life])) for life in LIVES]
            gain=history_pool([h['gain'] for h in histories])
            comparisons.append(dict(query=query,source_method=source,contrast='32-8',roots=len(group),complete=gain['complete'],gain=gain,per_history=histories))
    return rows,summaries,comparisons


def expected_settings():
    return dict(lifecycles=list(LIVES),queries=QUERIES,source_methods=list(SOURCES),roots=64,modes=list(MODES),splits=list(SPLITS),suffixes_per_split=32,
        budgets=list(BUDGETS),primary_budget=32,primary_precision_contrast='32-8',physical_branches=8192,max_steps=MAX_STEPS,maximum_environment_transitions=16384000,
        p_four=.1,workers=WORKERS,version_base=BASE,
        seeds='BASE+20000000+split_index*10000000+life*1000000+query_index*100000+source_index*10000+slot*100+suffix; modes paired',
        roots_source='all64 unchanged audited V157/V153 roots and frozen OLD cp4 LEARN8',
        intervention='unchanged V153 H_GATE own1 then OLD gate; M_GATE other8 then OLD gate',
        selection='strict positive mean M_GATE-H_GATE utility over TRAIN suffixes 0..n-1; zero rejects',
        freeze='all TRAIN sampling complete and selectors written before any EVAL sampling',
        evaluation='all budgets and OLD/reject/accept use common EVAL suffixes 0..31; no train/eval swap',
        weighting='equal roots within each history then equal four histories; unchanged roots retained',
        primary='n32 GATE utility gain versus OLD/reject/accept; paired n32-minus-n8 precision gain',
        secondary='n8/n16 curve, source and history strata, training diagnostics; no best-budget selection',
        intervals='pointwise normal 95% conditional suffix intervals from per-root paired EVAL32 variances; fixed training decisions, roots and histories',
        incomplete='retain all cutoffs and costs; affected means and intervals incomplete; no replacements',
        acquisition='all32 TRAIN plus all32 EVAL per root; nested views do not multiply physical acquisition',
        new_training_updates=0,stopping='fixed8192 branches; no evaluation-driven extra samples, refit or threshold changes')


def source_models(capsule,directory):
    run=read(capsule['source_run_ref']);analysis=read(capsule['source_analysis_ref']);latest=read(capsule['source_capsule_ref'])
    branch_run=read(capsule['branch_source_run_ref']);original=read(capsule['branch_source_capsule_ref']);frozen=read(capsule['branch_frozen_ref'])
    origin=Path(capsule['branch_source_run_ref']).parent;references={(r['life'],r['query']):r for r in original['models']};models={}
    checks=dict(source_complete=run['status']=='complete' and analysis['complete'] and analysis['primary_complete'] and branch_run['status']=='complete',
        source_binding=capsule['roots']==latest['roots']==frozen['roots'] and capsule['snapshots']==original['snapshots'] and
            capsule['retained_training_cost']==latest['retained_training_cost'],model_roster=True,model_copies=True,frozen_old_gate=True)
    roots=capsule['roots'];checks['source_binding'] &= len(roots)==64 and {r['root_id'] for r in roots}=={f'{l}:{q}:{s}:{slot}' for l in LIVES for q in QUERIES for s in SOURCES for slot in range(4)}
    checks['frozen_old_gate'] &= all(r['prediction']['accept']==(r['prediction']['advantage']>0) for r in roots)
    for meta in capsule['models']:
        key=meta['life'],meta['query'];reference=references[key];path=directory/meta['model_ref'];payload=read(path);source=read(meta['source_model_ref'])
        checks['model_roster'] &= key not in models and meta['checkpoint']==4 and meta['duration']==8
        checks['model_copies'] &= Path(meta['source_model_ref'])==origin/reference['model_ref'] and payload==source and payload['frozen'] and meta['model_bytes']==path.stat().st_size
        checks['model_copies'] &= meta['frozen_state']==reference['frozen_state']==prior.local.prior.state(payload)
        models[key]=dict(metadata=meta,weights={int(r[0]):tuple(r[1:]) for r in payload['weights']})
    checks['model_roster'] &= len(capsule['models'])==len(models)==8 and set(models)=={(l,q) for l in LIVES for q in QUERIES}
    return models,checks


def new_cost():
    return dict(physical_branches=0,environment_counts=Counter(),policy_counts=Counter(),statuses=Counter(),decision_seconds=0.)


def add_branch_cost(cost,result):
    cost['physical_branches']+=1;cost['statuses'][result['status']]+=1;cost['decision_seconds']+=result['decision_seconds']
    for name in ('environment_counts','policy_counts'):cost[name].update(result[name])


def combine_costs(target,source):
    for name in ('physical_branches','decision_seconds'):target[name]+=source[name]
    for name in ('environment_counts','policy_counts','statuses'):target[name].update(source[name])


def audit_lifecycle(lifecycle,source,models,roots,split,directory):
    directory=Path(directory);life=lifecycle['life'];root_map={r['root_id']:r for r in roots};seen=[];outcomes=[]
    teacher_counts={q:Counter() for q in QUERIES};model_counts={q:Counter() for q in QUERIES}
    checks=dict(branch_identity=lifecycle['split']==split,branch_roster=True,compact_outcomes=True,physical_accounting=True,
        teacher_bank=True,teacher_totals=True,models_frozen=True,model_counts=True,model_roster=True)
    costs=new_cost();costs.update(analysis_replay_swipes=0,physical_cells={},model_accounting=[],teacher_accounting=[],training_views={str(n):new_cost() for n in BUDGETS})
    for row in prior.old.read_rows(directory/lifecycle['branch_trace']):
        root=root_map[row['root_id']];query=root['query'];mode=row['mode'];suffix=row['suffix'];seen.append(row['branch_id'])
        checks['branch_identity'] &= all(row[k]==v for k,v in dict(branch_id=f'{root["root_id"]}:{split}:{suffix}:{mode}',life=life,split=split,
            query=query,source_method=root['source_method'],slot=root['slot'],root_board=root['board'],seed=branch_seed(root,split,suffix)).items())
        local_checks,swipes=diagnosis.replay_branch(row,models[query]['weights']);add_checks(checks,local_checks);costs['analysis_replay_swipes']+=swipes
        result=row['result'];outcomes.append(dict(**{k:row[k] for k in ('branch_id','root_id','life','query','source_method','slot','split','suffix','mode','seed')},
            **{k:result[k] for k in ('score','steps','status','components')}))
        add_branch_cost(costs,result)
        for q in QUERIES:teacher_counts[q].update(result['policy_counts_by_query'][q])
        model_counts[query].update({k[len('learner_'):]:v for k,v in result['policy_counts'].items() if k.startswith('learner_')})
        cell=costs['physical_cells'].setdefault(f'{query}:{root["source_method"]}:{mode}',dict(query=query,source_method=root['source_method'],mode=mode,**new_cost()))
        add_branch_cost(cell,result)
        if split=='TRAIN':
            for n in BUDGETS:
                if suffix<n:add_branch_cost(costs['training_views'][str(n)],result)
    checks['branch_roster'] &= seen==[f'{r["root_id"]}:{split}:{s}:{m}' for r in roots for s in range(32) for m in MODES] and len(seen)==1024
    checks['compact_outcomes'] &= read(directory/lifecycle['outcomes_ref'])==outcomes
    checks['physical_accounting'] &= lifecycle['physical_branches']==costs['physical_branches'] and all(Counter(lifecycle[k])==costs[k] for k in ('environment_counts','policy_counts','statuses'))
    loaded=[]
    for meta in lifecycle['models']:
        query=meta['query'];loaded.append(query);model=models[query]
        checks['models_frozen'] &= meta['model_ref']==model['metadata']['model_ref'] and meta['before']==meta['after']==model['metadata']['frozen_state']
        checks['model_counts'] &= Counter(meta['counts'])==model_counts[query] and Counter(meta['setup_counts'])==diagnosis.model_setup(len(model['weights']))
        costs['model_accounting'].append(dict(split=split,life=life,**meta))
    checks['model_roster'] &= len(loaded)==len(set(loaded))==2 and set(loaded)==set(QUERIES)
    for query in QUERIES:
        teacher=lifecycle['teacher_bank'][query]
        checks['teacher_bank'] &= prior.h1.teacher_analysis.teacher_loads_valid(teacher['loads'],source,'SINGLE',query)
        checks['teacher_bank'] &= teacher['parent_before']==teacher['parent_after']==prior.planning.previous.model_state(source,query,'PARENT',0)
        checks['teacher_bank'] &= teacher['leaf_before']==teacher['leaf_after']==prior.planning.expected_model_state(source,query,'SINGLE')
        checks['teacher_totals'] &= Counter(teacher['total_counts'])==teacher_counts[query]
        costs['teacher_accounting'].append(dict(split=split,life=life,query=query,**teacher))
    print(json.dumps(dict(event='audited_lifecycle',split=split,life=life,physical_branches=costs['physical_branches'],replayed_swipes=costs['analysis_replay_swipes'])),flush=True)
    return dict(split=split,life=life,checks=checks,outcomes=outcomes,costs=costs)


def analyze(directory):
    started=perf_counter();directory=Path(directory).resolve();run,capsule,frozen=(read(directory/n) for n in ('run.json','source_capsule.json','frozen_inputs.json'))
    checks=dict(settings=run['settings']==expected_settings(),frozen_inputs=frozen['status']=='frozen' and not frozen['phases'] and
        all(frozen[k]==run[k] for k in ('settings','inherited_cost_refs')),inherited_costs=run['inherited_cost_refs']==capsule['cost_refs'],
        frozen_roots=frozen['roots']==capsule['roots'],frozen_branch_roster=frozen['branch_roster']==branch_roster(capsule['roots']),
        phase_roster=set(run['phases'])==set(SPLITS) and all(run['phases'][s]['split']==s and len(run['phases'][s]['lifecycles'])==4 and
            {l['life'] for l in run['phases'][s]['lifecycles']}==set(LIVES) for s in SPLITS))
    models,local_checks=source_models(capsule,directory);add_checks(checks,local_checks);sources={s['life']:s for s in capsule['snapshots']};results=[]
    with ProcessPoolExecutor(max_workers=WORKERS) as pool:
        tasks=[pool.submit(audit_lifecycle,lifecycle,sources[lifecycle['life']],{q:models[lifecycle['life'],q] for q in QUERIES},
            [r for r in capsule['roots'] if r['life']==lifecycle['life']],split,directory) for split in SPLITS for lifecycle in run['phases'][split]['lifecycles']]
        for task in as_completed(tasks):results.append(task.result())
    results.sort(key=lambda r:(SPLITS.index(r['split']),r['life']));outcomes={s:[] for s in SPLITS}
    costs=dict(stages={s:new_cost() for s in SPLITS},training_views={str(n):new_cost() for n in BUDGETS},analysis_replay_swipes=0,
        physical_cells={},model_accounting=[],teacher_accounting=[],new_training_updates=0,
        inherited_retained_training_cost=capsule['retained_training_cost'],analysis_source_metadata_files_read=6,analysis_model_files_read=16,
        source_model_reads=8,source_model_copies=8,runtime_old_model_loads=16,runtime_teacher_parent_loads=16,runtime_teacher_leaf_loads=16,
        frozen_model_copies=dict(files=8,bytes=sum(m['model_bytes'] for m in capsule['models'])),old_raw_branch_reads=0)
    for result in results:
        add_checks(checks,result['checks']);outcomes[result['split']].extend(result['outcomes']);work=result['costs'];combine_costs(costs['stages'][result['split']],work)
        costs['analysis_replay_swipes']+=work['analysis_replay_swipes']
        for n in BUDGETS:combine_costs(costs['training_views'][str(n)],work['training_views'][str(n)])
        for name in ('model_accounting','teacher_accounting'):costs[name].extend(work[name])
        for key,cell in work['physical_cells'].items():
            name=f'{result["split"]}:{key}';target=costs['physical_cells'].setdefault(name,dict(split=result['split'],query=cell['query'],source_method=cell['source_method'],mode=cell['mode'],**new_cost()))
            combine_costs(target,cell)
    train=paired_outcomes(capsule['roots'],outcomes['TRAIN'],'TRAIN');evaluation=paired_outcomes(capsule['roots'],outcomes['EVAL'],'EVAL')
    selected=selectors(capsule['roots'],train);rows,summary,comparisons=evaluate(selected,evaluation)
    checks['paired_values']=equivalent(read(directory/'train_pairs.json'),train) and equivalent(read(directory/'eval_pairs.json'),evaluation)
    checks['frozen_selectors']=run['selectors_ref']=='frozen_selectors.json' and run['selectors']==len(selected)==192 and equivalent(read(directory/run['selectors_ref']),selected)
    checks['evaluation_arithmetic']=equivalent(read(directory/'evaluation_rows.json'),rows) and equivalent(read(directory/'summary.json'),summary) and equivalent(read(directory/'comparisons.json'),comparisons)
    costs['physical_branches']=sum(s['physical_branches'] for s in costs['stages'].values());costs['new_environment_samples']=sum(s['environment_counts'].get('sampled_transitions',0) for s in costs['stages'].values())
    checks['all_physical_branches']=costs['physical_branches']==8192 and all(len(outcomes[s])==4096 for s in SPLITS)
    costs['nested_budget_views']={str(n):dict(training=costs['training_views'][str(n)],evaluation=costs['stages']['EVAL'],
        sampled_transitions=costs['training_views'][str(n)]['environment_counts'].get('sampled_transitions',0)+costs['stages']['EVAL']['environment_counts'].get('sampled_transitions',0)) for n in BUDGETS}
    complete=run['status']=='complete' and all(checks.values());primary=all(s['complete'] for s in summary if s['budget']==32) and all(c['complete'] for c in comparisons)
    return dict(schema='acfqp.module_precision.v158.analysis',complete=complete,primary_complete=complete and primary,checks=checks,summary=summary,comparisons=comparisons,
        costs=costs,inherited_cost_refs=run['inherited_cost_refs'],seconds=perf_counter()-started,
        uncertainty='Pointwise suffix intervals condition on fixed TRAIN decisions, roots and four histories; they do not cover training-sample or history-population uncertainty.',
        scope='Fresh paired interventions at retained roots. Physical sampling is counted once; budget views reuse common EVAL32. Cutoffs retain all costs and invalidate affected means and intervals.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--directory','--input',dest='directory',type=Path,default=ROOT/'reports/controlled_predictive_module_precision_v158')
    args=parser.parse_args();result=analyze(args.directory);(args.directory/'analysis.json').write_text(json.dumps(result,separators=(',',':'))+'\n')
    print(json.dumps(dict(complete=result['complete'],primary_complete=result['primary_complete'],checks=len(result['checks']),failed=[k for k,v in result['checks'].items() if not v],seconds=result['seconds'])),flush=True)
    raise SystemExit(0 if result['complete'] else 1)
