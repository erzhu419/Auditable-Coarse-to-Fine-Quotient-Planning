"""Independent retained-prefix spawn-control and RAW-evaluation audit."""
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor,as_completed
import gzip
from itertools import zip_longest
import json
import math
from pathlib import Path
import sys
from time import perf_counter

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'src'))
from scripts import analyze_controlled_predictive_module_precision_v158 as precision
from scripts import analyze_controlled_predictive_module_semantics_v156 as semantics
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics

prior=precision.prior
LIVES,QUERIES,SOURCES,SPLITS,BUDGETS=precision.LIVES,precision.QUERIES,precision.SOURCES,precision.SPLITS,precision.BUDGETS
read,mean,close,add_checks=prior.read,prior.mean,prior.close,prior.add_checks
equivalent=precision.equivalent
PREFIX,WORKERS=8,4


class DirectOracle:
    """Frozen SINGLE QueryTD readout using Python rewrites and indexed weights."""
    def __init__(self,rule,weights,metadata):
        self.rule,self.weights,self.metadata=rule,weights,metadata
        self.patterns=np.asarray(semantics.tuple_patterns(),dtype=np.int64)
        self.offsets=(np.arange(32)//8)*(rule.goal_rank**6)
        self.powers=np.asarray([rule.goal_rank**i for i in range(5,-1,-1)],dtype=np.int64)
        self.counts=Counter();self.native_counts=Counter()

    def __call__(self,board):
        rule=self.rule;metadata=self.metadata;query=metadata['target_query'];self.counts['critic_queries']+=1
        self.native_counts.update(choose_calls=1,inner_choose_calls=1,inner_learned_terminal_checks=1)
        if max(board)>=rule.goal_rank:
            self.native_counts['inner_terminal_goal_bypasses']+=1;return float(query['goal_bonus'])
        values=[];convert=metadata['kind']=='PRIOR' and any(metadata['source_query'].get(k,d)!=query.get(k,d)
            for k,d in (('reward_weight',1.),('failure_penalty',0.),('goal_bonus',0.)))
        for action in semantics.ACTIONS:
            after,score,changed=rule.swipe(board,action,self.counts)
            self.native_counts.update(inner_learned_swipe_calls=1,inner_line_table_lookups=4)
            if not changed:continue
            self.native_counts.update(inner_legal_swipes=1,inner_learned_terminal_checks=1)
            if max(after)>=rule.goal_rank:
                value=score/2048.+query['goal_bonus'];self.native_counts['inner_terminal_goal_bypasses']+=1
            else:
                indices=np.asarray(after)[self.patterns]@self.powers
                tail=sum(float(v) for v in self.weights[indices+self.offsets]);self.counts.update(weight_lookups=32,value_predictions=1)
                self.native_counts.update(inner_value_predictions=1,inner_table_lookups=32)
                value=score/2048.+tail
                if convert:value=value+metadata['failure_shift']+metadata['success_shift']
            values.append(value)
        return max(values) if values else -float(query['failure_penalty'])


def prefix_checks(original,correction,critic):
    """Bind only the recorded first eight afterstates/spawns, then center f."""
    names=('branch_id','root_id','life','query','source_method','slot','split','suffix','mode')
    checks=dict(prefix_identity=all(correction[k]==original[k] for k in names),prefix_steps=True,spawn_enumeration=True,
        critic_values=True,conditional_centering=True,branch_correction=True,correction_counts=True)
    steps=correction['steps'];n=min(PREFIX,len(original['actions']));counts=Counter(branch_records_processed=1,corrected_spawn_steps=n);terms=[]
    checks['prefix_steps'] &= len(steps)==n
    for number,step in enumerate(steps):
        after=original['choices'][number]['afterstate'];cell=original['spawned_cells'][number];rank=original['spawned_ranks'][number]
        checks['prefix_steps'] &= step['step']==number and step['afterstate']==after and step['spawned_cell']==cell and step['spawned_rank']==rank
        empty=[i for i,value in enumerate(after) if value==0];expected=[]
        for candidate_cell in empty:
            for candidate_rank,probability in ((1,.9),(2,.1)):
                board=list(after);board[candidate_cell]=candidate_rank
                expected.append(dict(cell=candidate_cell,rank=candidate_rank,probability=probability/len(empty),value=float(critic(board))))
        candidates=step['candidates'];checks['spawn_enumeration'] &= len(candidates)==len(expected) and all(
            (a['cell'],a['rank'])==(b['cell'],b['rank']) and close(a['probability'],b['probability']) for a,b in zip(candidates,expected))
        checks['critic_values'] &= len(candidates)==len(expected) and all(close(a['value'],b['value']) for a,b in zip(candidates,expected))
        expectation=sum(c['probability']*c['value'] for c in expected)
        observed=next(c['value'] for c in expected if (c['cell'],c['rank'])==(cell,rank));term=observed-expectation;terms.append(term)
        checks['conditional_centering'] &= close(sum(c['probability'] for c in expected),1.) and close(sum(c['probability']*(c['value']-expectation) for c in expected),0.)
        checks['branch_correction'] &= all(close(step[k],v) for k,v in dict(observed_value=observed,expected_value=expectation,correction=term).items())
        step_counts=Counter(spawn_outcomes_enumerated=len(expected),critic_calls=len(expected));counts.update(step_counts)
        checks['correction_counts'] &= Counter(step['counts'])==step_counts
    checks['branch_correction'] &= close(correction['correction'],sum(terms))
    checks['correction_counts'] &= Counter(correction['counts'])==counts
    return checks,dict(counts)


def adjusted_pairs(raw_pairs,corrections):
    lookup={(r['root_id'],r['split'],r['suffix'],r['mode']):r['correction'] for r in corrections};result=[]
    for row in raw_pairs:
        root,split,suffix=row['root_id'],row['split'],row['suffix'];difference=lookup[root,split,suffix,'M_GATE']-lookup[root,split,suffix,'H_GATE']
        result.append(dict(**precision.metadata(row),split=split,suffix=suffix,complete=row['complete'],raw_components=row['components'],components=None,scalar_control=True,
            raw_advantage=row['advantage'],control_difference=difference,advantage=None if not row['complete'] else row['advantage']-difference))
    return result


def cv_selectors(roots,pairs):
    lookup={(r['root_id'],r['suffix']):r for r in pairs};result=[]
    for root in sorted(roots,key=lambda r:(r['life'],r['query'],r['source_method'],r['slot'],r['root_id'])):
        for budget in BUDGETS:
            value=mean(lookup[root['root_id'],s]['advantage'] for s in range(budget))
            result.append(dict(**precision.metadata(root),budget=budget,train_components=None,scalar_control=True,train_advantage=value,
                accept=None if value is None else value>0,old_accept=bool(root['prediction']['accept']),complete=value is not None))
    return result


def evaluate_control(raw_selectors,controlled_selectors,raw_eval_pairs):
    result={}
    for name,selected in (('raw',raw_selectors),('cv',controlled_selectors)):
        rows,summary,comparisons=precision.evaluate(selected,raw_eval_pairs);result[name]=dict(rows=rows,summary=summary,comparisons=comparisons)
    indexed={(r['root_id'],r['suffix']):r for r in raw_eval_pairs};raw={(r['root_id'],r['budget']):r for r in raw_selectors};differences=[]
    for selected in controlled_selectors:
        reference=raw[selected['root_id'],selected['budget']];coefficient=int(selected['accept'])-int(reference['accept']) if selected['complete'] and reference['complete'] else None
        values=[indexed[selected['root_id'],s] for s in range(32)]
        differences.append(dict(**precision.metadata(selected),budget=selected['budget'],gain=precision.moments([
            None if coefficient is None or not r['complete'] else coefficient*r['advantage'] for r in values])))
    contrasts=[]
    for query in QUERIES:
        for budget in BUDGETS:
            for source in ('ALL',*SOURCES):
                group=[r for r in differences if r['query']==query and r['budget']==budget and (source=='ALL' or r['source_method']==source)]
                histories=[dict(life=life,roots=sum(r['life']==life for r in group),gain=precision.root_pool([r['gain'] for r in group if r['life']==life])) for life in LIVES]
                gain=precision.history_pool([h['gain'] for h in histories])
                contrasts.append(dict(query=query,budget=budget,source_method=source,contrast='CV-RAW',roots=len(group),complete=gain['complete'],gain=gain,per_history=histories))
    result['contrasts']=contrasts
    return result


VARIANCE_FIELDS=('raw_mean','cv_mean','control_mean','raw_variance','cv_variance','covariance_raw_control')


def variance_stats(pairs):
    if not all(p['complete'] for p in pairs):return dict.fromkeys(VARIANCE_FIELDS)
    raw=[p['raw_advantage'] for p in pairs];controlled=[p['advantage'] for p in pairs];control=[p['control_difference'] for p in pairs]
    r,v,c=mean(raw),mean(controlled),mean(control)
    return dict(raw_mean=r,cv_mean=v,control_mean=c,raw_variance=sum((x-r)**2 for x in raw)/(len(raw)-1),
        cv_variance=sum((x-v)**2 for x in controlled)/(len(controlled)-1),covariance_raw_control=sum((x-r)*(y-c) for x,y in zip(raw,control))/(len(raw)-1))


def variance_ratio(stats):
    return stats['cv_variance']/stats['raw_variance'] if stats['raw_variance'] is not None and stats['raw_variance']>0 and stats['cv_variance'] is not None else None


def variance_report(pairs):
    groups=[]
    for split in SPLITS:
        selected=[p for p in pairs if p['split']==split];root_rows=[]
        for root_id in dict.fromkeys(p['root_id'] for p in selected):
            values=sorted((p for p in selected if p['root_id']==root_id),key=lambda p:p['suffix'])
            root_rows.append(dict(**precision.metadata(values[0]),samples=32,complete=all(p['complete'] for p in values),stats=variance_stats(values)))
        for query in QUERIES:
            for source in ('ALL',*SOURCES):
                roots=[r for r in root_rows if r['query']==query and (source=='ALL' or r['source_method']==source)];histories=[]
                for life in LIVES:
                    local=[r for r in roots if r['life']==life];means={k:mean(r['stats'][k] for r in local) for k in VARIANCE_FIELDS}
                    histories.append(dict(life=life,roots=len(local),complete=bool(local) and all(r['complete'] for r in local),means=means,
                        variance_ratio=variance_ratio(means),per_root=[{k:r[k] for k in ('root_id','samples','complete','stats')} for r in local]))
                means={k:mean(h['means'][k] for h in histories) for k in VARIANCE_FIELDS}
                groups.append(dict(split=split,query=query,source_method=source,roots=len(roots),complete=all(h['complete'] for h in histories),
                    means=means,variance_ratio=variance_ratio(means),per_history=histories))
    return groups


def expected_settings():
    return dict(lifecycles=list(LIVES),queries=QUERIES,roots=64,splits=list(SPLITS),suffixes_per_split=32,modes=['H_GATE','M_GATE'],retained_branches=8192,
        window=8,beta=1.,p_four=.1,budgets=list(BUDGETS),primary_budget=32,workers=WORKERS,
        critic='frozen target-query SINGLE QueryTD DIRECT choose(state).value; analytic terminals; no H2 expansion',
        correction='sum first min(8,steps) of f(actual postspawn)-exact uniform-cell/.9/.1 expectation after chosen action',
        paired_label='CV=RAW-(C_M-C_H); scalar correction only; terminal objective unchanged',
        selection='strict positive TRAIN-prefix paired label mean; zero rejects; all budgets retained',
        evaluation='both selectors scored only on original V158 EVAL32 terminal utilities',
        primary='n32 CV-minus-RAW paired action utility and CV versus OLD/reject/accept; both queries',
        secondary='n8/n16 controls; TRAIN/EVAL within-root label variance, source/history strata and fixed coefficient covariance',
        uncertainty='exploratory inspected V158 paths; conditional suffix intervals fixed roots/training; no fresh confirmation',
        accounting='retain V158 acquisition4026405 and earlier refs; zero new samples/updates; all critic/enumeration/load work separate',
        freeze='configuration/code/source roots before correction; CV selectors use TRAIN only and freeze before EVAL corrections',
        incomplete='retain cutoffs and all costs; affected comparisons incomplete without replacements',
        forbidden_adaptation='no coefficient/window/critic/budget choice after outcomes; no automatic extra samples')


def source_checks(capsule):
    run,analysis,source,frozen=(read(capsule[k]) for k in ('source_run_ref','source_analysis_ref','source_capsule_ref','source_frozen_ref'))
    origin=Path(capsule['source_run_ref']).parent
    checks=dict(source_complete=run['status']=='complete' and analysis['complete'] and analysis['primary_complete'],
        source_identity=Path(capsule['source_analysis_ref'])==origin/'analysis.json' and Path(capsule['source_capsule_ref'])==origin/'source_capsule.json' and
            Path(capsule['source_frozen_ref'])==origin/'frozen_inputs.json' and capsule['roots']==source['roots']==frozen['roots'] and capsule['snapshots']==source['snapshots'],
        source_traces=capsule['source_traces']==[dict(life=l['life'],split=s,path=str(origin/l['branch_trace']),outcomes_ref=str(origin/l['outcomes_ref']))
            for s in SPLITS for l in run['phases'][s]['lifecycles']],
        retained_acquisition=capsule['inherited_new_environment_samples']==analysis['costs']['new_environment_samples'],raw_label_refs=True)
    for key,name in (('raw_train_pairs_ref','train_pairs.json'),('raw_eval_pairs_ref','eval_pairs.json'),('raw_selectors_ref','frozen_selectors.json'),('raw_summary_ref','summary.json')):
        checks['raw_label_refs'] &= Path(capsule[key])==origin/name
    return checks


def read_rows(path):
    with gzip.open(path,'rt') as stream:
        for line in stream:yield json.loads(line)


def load_oracles(source):
    models={};counts=Counter();checks=dict(critic_source=True)
    for query in QUERIES:
        reference=source['leaves'][query]['SINGLE'];path=Path(reference['model_ref']);metadata=read(str(path)+'.query.json')
        rule=LearnedDynamics.from_payload(source['rule'])
        with np.load(path,allow_pickle=False) as data:
            checkpoint=json.loads(str(data['metadata']));weights=np.zeros(4*rule.goal_rank**6,dtype=np.float64);weights[data['indices']]=data['values']
            nonzero=len(data['indices'])
        weights.flags.writeable=False
        checks['critic_source'] &= metadata['kind']=='PRIOR' and metadata['target_query']==QUERIES[query] and metadata['updates']==reference['updates']==checkpoint['updates']
        checks['critic_source'] &= checkpoint['radix']==rule.goal_rank and metadata['offset']==prior.planning.previous.expected_offset(source,query,'SINGLE')
        models[query]=DirectOracle(rule,weights,metadata)
        counts.update(leaf_checkpoint_files_read=1,leaf_sidecars_read=1,leaf_nonzero_parameters_read=nonzero,leaf_numeric_bytes_allocated=weights.nbytes)
    return models,checks,counts


def audit_life(source,lifecycles,traces,directory):
    directory=Path(directory);life=source['life'];oracles,checks,loads=load_oracles(source);phases=[]
    for split in SPLITS:
        lifecycle=lifecycles[split];trace=traces[split];seen=[];corrections=[];outcomes=[];counts=Counter()
        for model in oracles.values():model.counts.clear();model.native_counts.clear()
        local_checks=dict(prefix_source_roster=True,compact_source_outcomes=True,compact_corrections=True,critic_bindings=True,critic_counts=True,phase_accounting=True)
        for original,correction in zip_longest(read_rows(trace['path']),read_rows(directory/lifecycle['correction_trace'])):
            if original is None or correction is None:
                local_checks['prefix_source_roster']=False;continue
            seen.append(original['branch_id']);local_checks['prefix_source_roster'] &= original['life']==life and original['split']==split and original['p_four']==.1
            actual,work=prefix_checks(original,correction,oracles[original['query']]);add_checks(local_checks,actual);counts.update(work)
            names=('branch_id','root_id','life','query','source_method','slot','split','suffix','mode')
            corrections.append(dict(**{k:correction[k] for k in names},correction=correction['correction']))
            result=original['result'];outcomes.append(dict(**{k:original[k] for k in (*names,'seed')},**{k:result[k] for k in ('score','steps','status','components')}))
        expected_outcomes=read(trace['outcomes_ref']);local_checks['compact_source_outcomes'] &= outcomes==expected_outcomes
        local_checks['prefix_source_roster'] &= len(seen)==len(set(seen))==1024
        local_checks['compact_corrections'] &= read(directory/lifecycle['corrections_ref'])==corrections
        local_checks['phase_accounting'] &= lifecycle['life']==life and lifecycle['split']==split and lifecycle['source_rows_read']==len(seen) and Counter(lifecycle['counts'])==counts
        local_checks['phase_accounting'] &= lifecycle['new_environment_samples']==lifecycle['new_training_updates']==0
        for query in QUERIES:
            meta=lifecycle['critics'][query];model=oracles[query];reference=source['leaves'][query]['SINGLE']
            local_checks['critic_bindings'] &= meta['reference']==reference and meta['query']==query
            local_checks['critic_bindings'] &= meta['parent_before']==meta['parent_after']==prior.planning.previous.model_state(source,query,'PARENT',0)
            local_checks['critic_bindings'] &= meta['leaf_before']==meta['leaf_after']==prior.planning.expected_model_state(source,query,'SINGLE')
            local_checks['critic_bindings'] &= meta['parent_load']['load_counts'].get('checkpoint_loads')==1 and meta['leaf_load']['load_counts'].get('checkpoint_loads')==1
            local_checks['critic_bindings'] &= meta['leaf_load']['setup_counts'].get('allocated_weight_parameters')==prior.planning.previous.parameter_count('SINGLE')
            local_checks['critic_counts'] &= Counter(meta['counts'])==model.native_counts
        local_checks['critic_counts'] &= sum(m.native_counts['choose_calls'] for m in oracles.values())==counts['critic_calls']
        work=dict(source_rows_read=len(seen),correction_rows_read=len(corrections),counts=dict(counts),critic_seconds=lifecycle['critic_seconds'],
            runtime_critics=lifecycle['critics'],analysis_critic_counts=dict(sum((m.counts for m in oracles.values()),Counter())),
            reconstructed_native_counts=dict(sum((m.native_counts for m in oracles.values()),Counter())))
        add_checks(checks,local_checks);phases.append(dict(split=split,life=life,corrections=corrections,outcomes=outcomes,work=work))
        print(json.dumps(dict(event='audited_corrections',split=split,life=life,source_rows=len(seen),critic_queries=counts['critic_calls'])),flush=True)
    return dict(life=life,checks=checks,model_reads=dict(loads),phases=phases)


def analyze(directory):
    started=perf_counter();directory=Path(directory).resolve();run,capsule,frozen=(read(directory/n) for n in ('run.json','source_capsule.json','frozen_inputs.json'))
    checks=dict(settings=run['settings']==expected_settings(),frozen_inputs=frozen['status']=='frozen' and not frozen['phases'] and
        all(frozen[k]==run[k] for k in ('settings','root_ids','inherited_cost_refs')),root_roster=run['root_ids']==[r['root_id'] for r in capsule['roots']] and
        len(run['root_ids'])==len(set(run['root_ids']))==64,inherited_cost_refs=run['inherited_cost_refs']==capsule['cost_refs'],
        phase_roster=set(run['phases'])==set(SPLITS) and all(run['phases'][s]['split']==s and len(run['phases'][s]['lifecycles'])==4 and
            {l['life'] for l in run['phases'][s]['lifecycles']}==set(LIVES) for s in SPLITS),zero_new_samples_updates=run['new_environment_samples']==run['new_training_updates']==0)
    add_checks(checks,source_checks(capsule));sources={s['life']:s for s in capsule['snapshots']};results=[]
    with ProcessPoolExecutor(max_workers=WORKERS) as pool:
        tasks=[pool.submit(audit_life,sources[l],{s:next(r for r in run['phases'][s]['lifecycles'] if r['life']==l) for s in SPLITS},
            {s:next(t for t in capsule['source_traces'] if t['life']==l and t['split']==s) for s in SPLITS},directory) for l in LIVES]
        for task in as_completed(tasks):results.append(task.result())
    results.sort(key=lambda r:r['life']);corrections={s:[] for s in SPLITS};outcomes={s:[] for s in SPLITS};costs=dict(stages={s:dict(source_rows_read=0,correction_rows_read=0,
        counts=Counter(),critic_seconds=0.,analysis_critic_counts=Counter(),reconstructed_native_counts=Counter(),runtime_critics=[]) for s in SPLITS},analysis_model_reads=Counter())
    for result in results:
        add_checks(checks,result['checks']);costs['analysis_model_reads'].update(result['model_reads'])
        for phase in result['phases']:
            split=phase['split'];corrections[split].extend(phase['corrections']);outcomes[split].extend(phase['outcomes']);stage=costs['stages'][split];work=phase['work']
            for name in ('source_rows_read','correction_rows_read','critic_seconds'):stage[name]+=work[name]
            for name in ('counts','analysis_critic_counts','reconstructed_native_counts'):stage[name].update(work[name])
            stage['runtime_critics'].append(dict(life=result['life'],critics=work['runtime_critics']))
    raw_train,raw_eval,raw_selected=(read(capsule[k]) for k in ('raw_train_pairs_ref','raw_eval_pairs_ref','raw_selectors_ref'))
    checks['raw_pair_binding']=equivalent(raw_train,precision.paired_outcomes(capsule['roots'],outcomes['TRAIN'],'TRAIN')) and equivalent(raw_eval,precision.paired_outcomes(capsule['roots'],outcomes['EVAL'],'EVAL'))
    checks['raw_selector_binding']=equivalent(raw_selected,precision.selectors(capsule['roots'],raw_train))
    train=adjusted_pairs(raw_train,corrections['TRAIN']);evaluation=adjusted_pairs(raw_eval,corrections['EVAL']);selected=cv_selectors(capsule['roots'],train)
    results=evaluate_control(raw_selected,selected,raw_eval);variance=variance_report(train+evaluation)
    checks['adjusted_pairs']=equivalent(read(directory/'adjusted_train_pairs.json'),train) and equivalent(read(directory/'adjusted_eval_pairs.json'),evaluation)
    checks['frozen_cv_selectors']=run['selectors']==len(selected)==192 and equivalent(read(directory/'frozen_cv_selectors.json'),selected)
    checks['raw_evaluation_anchor']=equivalent(results['raw']['summary'],read(capsule['raw_summary_ref']))
    checks['raw_only_evaluation']=equivalent(read(directory/'evaluation.json'),results)
    checks['variance_diagnostics']=equivalent(read(directory/'variance.json'),variance)
    costs.update(new_environment_samples=0,new_training_updates=0,retained_branches=sum(s['source_rows_read'] for s in costs['stages'].values()),
        inherited_new_environment_samples=capsule['inherited_new_environment_samples'],runtime_parent_loads=16,runtime_leaf_loads=16,
        analysis_source_metadata_files_read=4,analysis_raw_compact_pair_rows_read=len(raw_train)+len(raw_eval),analysis_raw_selector_rows_read=len(raw_selected),
        full_environment_replays=0,inherited_cost_refs=run['inherited_cost_refs'])
    checks['retained_branches']=costs['retained_branches']==8192
    complete=run['status']=='complete' and all(checks.values());primary=all(s['complete'] for name in ('raw','cv') for s in results[name]['summary'] if s['budget']==32) and all(c['complete'] for c in results['contrasts'] if c['budget']==32)
    return dict(schema='acfqp.module_control_variate.v159.analysis',complete=complete,primary_complete=complete and primary,checks=checks,evaluation=results,variance=variance,
        costs=costs,seconds=perf_counter()-started,
        scope='Conditional-zero-mean spawn corrections use the actual fixed spawn law and frozen DIRECT critic. Both selectors are scored only against retained RAW EVAL terminal utilities.',
        limitations='Exploratory previously inspected paths. Conditional suffix intervals fix training decisions, roots and four histories; reduced label variance alone does not establish policy gain or fresh confirmation.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--directory','--input',dest='directory',type=Path,default=ROOT/'reports/controlled_predictive_module_control_variate_v159')
    args=parser.parse_args();result=analyze(args.directory);(args.directory/'analysis.json').write_text(json.dumps(result,separators=(',',':'))+'\n')
    print(json.dumps(dict(complete=result['complete'],primary_complete=result['primary_complete'],checks=len(result['checks']),failed=[k for k,v in result['checks'].items() if not v],seconds=result['seconds'])),flush=True)
    raise SystemExit(0 if result['complete'] else 1)
