"""Independent split-half audit of retained paired module outcomes."""
import argparse
from collections import Counter
import gzip
import json
import math
from pathlib import Path
from time import perf_counter

ROOT=Path(__file__).resolve().parents[1]
LIVES=tuple(range(4));QUERIES=('risk1','risk8');SOURCES=('H2','LEARN8')
MODES=('H_H2','M_H2','H_GATE','M_GATE');TARGETS=('H2','GATE')
HALVES={'A':list(range(8)),'B':list(range(8,16))}
read=lambda path:json.loads(Path(path).read_text())


def mean(values):
    values=list(values)
    return None if not values or any(v is None for v in values) else sum(values)/len(values)


def utility(components,query):
    coefficient=1 if query=='risk1' else 8
    return components[0]-coefficient*components[1]+coefficient*components[2]


def close(a,b):
    return math.isclose(a,b,rel_tol=1e-12,abs_tol=1e-12)


def equivalent(actual,expected):
    if isinstance(expected,dict):return isinstance(actual,dict) and actual.keys()==expected.keys() and all(equivalent(actual[k],v) for k,v in expected.items())
    if isinstance(expected,list):return isinstance(actual,list) and len(actual)==len(expected) and all(equivalent(a,b) for a,b in zip(actual,expected))
    if isinstance(expected,float):return isinstance(actual,(int,float)) and close(actual,expected)
    return actual==expected


def seed(root,suffix):
    return 153*100000000+20000000+root['life']*1000000+QUERIES.index(root['query'])*100000+SOURCES.index(root['source_method'])*10000+root['slot']*100+suffix


def extract(capsule):
    roots={r['root_id']:r for r in capsule['roots']};rows=[];seen=[];counts=Counter()
    checks=dict(raw_roster=True,raw_identity=True,terminal_components=True,retained_budget=True)
    for trace in capsule['source_traces']:
        counts['raw_trace_files_read']+=1
        with gzip.open(trace['path'],'rt') as stream:
            for line in stream:
                row=json.loads(line);result=row['result'];root=roots[row['root_id']];suffix=row['suffix'];mode=row['mode'];seen.append(row['branch_id'])
                counts['raw_rows_read']+=1;counts['retained_environment_transitions']+=result['steps']
                checks['raw_identity'] &= all(row[k]==v for k,v in dict(branch_id=f'{root["root_id"]}:{suffix}:{mode}',life=trace['life'],
                    query=root['query'],source_method=root['source_method'],slot=root['slot'],root_board=root['board'],seed=seed(root,suffix)).items())
                checks['terminal_components'] &= result['status'] in ('WON','LOST') and len(result['components'])==3 and close(result['components'][0],result['score']/2048.)
                checks['terminal_components'] &= result['components'][1:]==[int(result['status']=='LOST'),int(result['status']=='WON')]
                compact={k:row[k] for k in ('branch_id','root_id','life','query','source_method','slot','suffix','mode','seed','root_board')}
                compact.update({k:result[k] for k in ('score','steps','status','components')});rows.append(compact)
    expected={f'{root["root_id"]}:{suffix}:{mode}' for root in capsule['roots'] for suffix in range(16) for mode in MODES}
    checks['raw_roster'] &= len(seen)==len(set(seen))==4096 and set(seen)==expected and len(capsule['source_traces'])==4 and {t['life'] for t in capsule['source_traces']}==set(LIVES)
    checks['retained_budget'] &= counts['retained_environment_transitions']==capsule['retained_training_cost']['retained_environment_transitions']
    return rows,checks,dict(counts)


def paired_outcomes(roots,outcomes):
    lookup={(r['root_id'],r['suffix'],r['mode']):r for r in outcomes};pairs=[]
    for root in sorted(roots,key=lambda r:(r['life'],r['query'],r['source_method'],r['slot'],r['root_id'])):
        for suffix in range(16):
            differences={target:[lookup[root['root_id'],suffix,'M_'+target]['components'][c]-lookup[root['root_id'],suffix,'H_'+target]['components'][c]
                for c in range(3)] for target in TARGETS}
            pairs.append(dict(**{k:root[k] for k in ('root_id','life','query','source_method','slot')},suffix=suffix,
                old_accept=root['prediction']['advantage']>0,components=differences,
                advantages={target:utility(value,root['query']) for target,value in differences.items()}))
    return pairs


def selection_rows(roots,pairs):
    lookup={(r['root_id'],r['suffix']):r for r in pairs};selections=[]
    for root in sorted(roots,key=lambda r:(r['life'],r['query'],r['source_method'],r['slot'],r['root_id'])):
        parts={half:{target:[mean(lookup[root['root_id'],suffix]['components'][target][c] for suffix in suffixes) for c in range(3)]
            for target in TARGETS} for half,suffixes in HALVES.items()}
        for train,evaluate in (('A','B'),('B','A')):
            train_values={target:utility(value,root['query']) for target,value in parts[train].items()}
            eval_values={target:utility(value,root['query']) for target,value in parts[evaluate].items()}
            for target in TARGETS:
                selections.append(dict(**{k:root[k] for k in ('root_id','life','query','source_method','slot')},direction=f'{train}_to_{evaluate}',
                    train_half=train,eval_half=evaluate,target=target,old_accept=root['prediction']['advantage']>0,accept=train_values[target]>0,
                    train_advantage=train_values[target],train_advantages=train_values,eval_advantages=eval_values,
                    train_components=parts[train],eval_components=parts[evaluate]))
    return selections


METRICS=('accept_rate','old_accept_rate','decision_change_rate','train_eval_sign_agreement','train_advantage','eval_advantage',
    'gain_vs_old','gain_vs_reject','gain_vs_accept','apparent_gain_vs_old','selection_optimism')


def row_metrics(row,eval_target):
    decision=int(row['accept']);old=int(row['old_accept']);test=row['eval_advantages'][eval_target];train=row['train_advantages'][eval_target]
    gain=(decision-old)*test;apparent=(decision-old)*train
    return dict(accept_rate=decision,old_accept_rate=old,decision_change_rate=int(decision!=old),
        train_eval_sign_agreement=int(bool(decision)==(test>0)),train_advantage=row['train_advantage'],eval_advantage=test,
        gain_vs_old=gain,gain_vs_reject=decision*test,gain_vs_accept=(decision-1)*test,apparent_gain_vs_old=apparent,selection_optimism=apparent-gain)


def summarize(selections):
    groups=[]
    for query in QUERIES:
        for target in TARGETS:
            for eval_target in TARGETS:
                for source in ('ALL',*SOURCES):
                    for direction in ('ALL','A_to_B','B_to_A'):
                        rows=[r for r in selections if r['query']==query and r['target']==target and (source=='ALL' or r['source_method']==source) and (direction=='ALL' or r['direction']==direction)]
                        histories=[]
                        for life in LIVES:
                            selected=[r for r in rows if r['life']==life];root_ids=sorted({r['root_id'] for r in selected});root_metrics=[]
                            for root_id in root_ids:
                                values=[row_metrics(r,eval_target) for r in selected if r['root_id']==root_id]
                                root_metrics.append({k:mean(v[k] for v in values) for k in METRICS})
                            histories.append(dict(life=life,roots=len(root_ids),row_count=len(selected),**{k:mean(r[k] for r in root_metrics) for k in METRICS}))
                        groups.append(dict(query=query,target=target,eval_target=eval_target,source_method=source,direction=direction,
                            roots=len({r['root_id'] for r in rows}),row_count=len(rows),**{k:mean(h[k] for h in histories) for k in METRICS},per_history=histories))
    return groups


def compact_checks(capsule,outcomes):
    roots={r['root_id']:r for r in capsule['roots']};indexed={(r['root_id'],r['suffix'],r['mode']):r for r in outcomes}
    expected={(r['root_id'],suffix,mode) for r in capsule['roots'] for suffix in range(16) for mode in MODES}
    checks=dict(compact_roster=len(outcomes)==len(indexed)==4096 and set(indexed)==expected,paired_branch_identity=True,
        frozen_old_gate=True,full_mean_labels=True)
    checks['frozen_old_gate'] &= all(r['prediction']['accept']==(r['prediction']['advantage']>0) and close(r['prediction']['advantage'],utility(r['prediction']['components'],r['query'])) for r in roots.values())
    if not checks['compact_roster']:
        checks['paired_branch_identity']=False;checks['full_mean_labels']=False
        return checks,[],[],[]
    for key,row in indexed.items():
        root=roots[key[0]];suffix=key[1]
        checks['paired_branch_identity'] &= row['seed']==seed(root,suffix) and row['root_board']==root['board'] and row['life']==root['life'] and row['query']==root['query']
    pairs=paired_outcomes(capsule['roots'],outcomes);lookup={(r['root_id'],r['suffix']):r for r in pairs};examples={e['root_id']:e for e in capsule['examples']}
    checks['full_mean_labels'] &= len(examples)==len(capsule['examples'])==len(roots)==64 and set(examples)==set(roots)
    for root_id,root in roots.items():
        for target in TARGETS:
            expected_mean=[mean(lookup[root_id,s]['components'][target][c] for s in range(16)) for c in range(3)]
            checks['full_mean_labels'] &= equivalent(examples[root_id]['targets']['REPAIR_'+target],expected_mean)
    selections=selection_rows(capsule['roots'],pairs)
    return checks,pairs,selections,summarize(selections)


def expected_settings():
    return dict(lifecycles=list(LIVES),queries=list(QUERIES),source_methods=list(SOURCES),slots=[0,1,2,3],roots=64,
        suffixes_per_root=16,modes=list(MODES),halves=HALVES,directions=['A_to_B','B_to_A'],selection_targets=list(TARGETS),evaluation_targets=list(TARGETS),
        primary='GATE-selected heldout GATE utility gain versus OLD; both directions and equal average',
        secondary='H2 target, cross-target outcomes, source/history strata, always reject/accept and apparent gains',
        selector='strict positive train-half paired utility mean; zero rejects',
        weighting='equal roots within history, then equal histories; average both directions per root; all roots retained',
        uncertainty='descriptive only; opposite-half evaluation, reused halves and previously inspected outcomes; no independent-fold CI',
        new_environment_samples=0,native_planner_calls=0,model_fits=0,
        accounting='physical retained acquisition 2017530 transitions counted once; all selectors use full retained pool',
        decision='stable opposite-half gain supports more independent roots; unstable sign or gains prioritize label precision')


def source_checks(capsule):
    source_run=read(capsule['source_run_ref']);source_analysis=read(capsule['source_analysis_ref']);source=read(capsule['source_capsule_ref'])
    branch_run=read(capsule['branch_run_ref']);branch_analysis=read(capsule['branch_analysis_ref']);frozen=read(capsule['branch_frozen_ref'])
    branch_origin=Path(capsule['branch_run_ref']).parent;origin=Path(capsule['source_run_ref']).parent
    return dict(source_complete=all((source_run['status']=='complete',source_analysis['complete'],source_analysis['primary_complete'],
            branch_run['status']=='complete',branch_analysis['complete'],branch_analysis['primary_complete'])),
        source_binding=Path(capsule['source_analysis_ref'])==origin/'analysis.json' and Path(capsule['source_capsule_ref'])==origin/'source_capsule.json' and
            Path(capsule['branch_analysis_ref'])==branch_origin/'analysis.json' and Path(capsule['branch_frozen_ref'])==branch_origin/'frozen_inputs.json' and
            capsule['roots']==frozen['roots']==source['roots'] and capsule['branch_roster']==frozen['branch_roster'] and capsule['examples']==source['examples'] and
            capsule['retained_training_cost']==source['retained_training_cost'] and capsule['source_traces']==[
                dict(life=r['life'],path=str(branch_origin/r['branch_trace'])) for r in branch_run['lifecycles']])


def analyze(directory):
    started=perf_counter();directory=Path(directory).resolve()
    run,capsule,frozen=(read(directory/name) for name in ('run.json','source_capsule.json','frozen_inputs.json'))
    refs=dict(outcomes='retained_outcomes.json',pairs='paired_outcomes.json',selections='selection_rows.json',summary='summary.json')
    checks=dict(settings=run['settings']==expected_settings(),frozen_inputs=frozen['status']=='frozen' and all(frozen[k]==run[k] for k in
        ('settings','halves','root_ids','output_refs','inherited_cost_refs')),halves_and_roots=run['halves']==HALVES and run['root_ids']==[r['root_id'] for r in capsule['roots']] and
        len(run['root_ids'])==len(set(run['root_ids']))==64,output_refs=run['output_refs']==refs,inherited_cost_refs=run['inherited_cost_refs']==capsule['cost_refs'])
    checks.update(source_checks(capsule));raw,raw_checks,costs=extract(capsule);checks.update(raw_checks)
    artifacts={key:read(directory/path) for key,path in refs.items()}
    checks['compact_extraction']=artifacts['outcomes']==raw
    compact,pairs,selections,summary=compact_checks(capsule,raw);checks.update(compact)
    checks['paired_outcomes']=equivalent(artifacts['pairs'],pairs)
    checks['opposite_half_selection']=equivalent(artifacts['selections'],selections)
    checks['equal_weight_summary']=equivalent(artifacts['summary'],summary)
    checks['extraction_accounting']=all(run['extraction'][k]==v for k,v in dict(rows=costs['raw_rows_read'],
        retained_environment_transitions=costs['retained_environment_transitions'],raw_trace_files_read=costs['raw_trace_files_read'],
        new_environment_samples=0,native_planner_calls=0,model_fits=0).items())
    checks['output_counts']=run['pairs']==len(pairs)==1024 and run['selection_rows']==len(selections)==256 and run['summary_groups']==len(summary)==72
    complete=run['status']=='complete' and all(checks.values())
    costs.update(new_environment_samples=0,native_planner_calls=0,model_fits=0,model_files_read=0,source_metadata_files_read=6,
        inherited_files_read=0,compact_outcome_rows_read=len(artifacts['outcomes']),paired_rows_recomputed=len(pairs),
        selection_rows_recomputed=len(selections),summary_groups_recomputed=len(summary),
        retained_budget_views={f'{target}:{direction}':costs['retained_environment_transitions'] for target in TARGETS for direction in ('A_to_B','B_to_A')},
        runtime_extraction=run['extraction'])
    return dict(schema='acfqp.module_split_half.v157.analysis',complete=complete,primary_complete=complete,
        checks=[dict(name=name,passed=bool(value)) for name,value in checks.items()],summary=summary,costs=costs,
        inherited_cost_refs=run['inherited_cost_refs'],seconds=perf_counter()-started,
        scope='Opposite retained suffix halves select and evaluate fixed root-local interventions. Directions are averaged within root, then roots within history and four histories equally. Descriptive only; no new game or trajectory replay.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,default=ROOT/'reports/controlled_predictive_module_split_half_v157')
    parser.add_argument('--output',type=Path)
    args=parser.parse_args();result=analyze(args.input);output=args.output or args.input/'analysis.json'
    output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps(dict(complete=result['complete'],primary_complete=result['primary_complete'],checks=len(result['checks']),
        failed=[c['name'] for c in result['checks'] if not c['passed']],seconds=result['seconds'])),flush=True)
    raise SystemExit(0 if result['complete'] else 1)
