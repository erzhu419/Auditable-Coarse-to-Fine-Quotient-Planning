"""Deterministic contract validation; no environment observations are drawn."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction as F
from itertools import combinations
import json
from pathlib import Path
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT)); sys.path.insert(0,str(ROOT/'src'))
from acfqp.science import scoped_repair_v228 as core
from acfqp.science import scoped_route_task_v228 as task
from scripts.run_conditioned_mechanisms_v205 import save

OUTPUT=ROOT/'reports/scoped_repair_v228'
SOURCE_FILES=(
    'src/acfqp/science/scoped_union_v228.py',
    'src/acfqp/science/scoped_queries_v228.py',
    'src/acfqp/science/scoped_route_task_v228.py',
    'src/acfqp/science/scoped_repair_v228.py',
    'tests/test_scoped_union_v228.py',
    'tests/test_scoped_route_v228.py',
    'tests/test_scoped_repair_v228.py',
    'scripts/probe_scoped_repair_v228.py',
    'specs/SCOPED_REPAIR_V228.md',
    'specs/SCOPED_REPAIR_V228_PROOF.md',
    'reports/v228_runtime_tmp/run_stage.py',
)


def fixture(law,n):
    return {op:{cat:int(n*p) for cat,p in row.items()} for op,row in law.items()}


def pure_values(case,law):
    # Direct mechanics, independent of the learner's value/certificate helper.
    sc,dc=core.mechanics.robust.learning.COST_PRIOR[case['operating']]
    s,d,r=(law[op] for op in core.OPERATORS); rc=F(case['retry_cost'])
    return dict(WAIT=[F(0)]*3,SHORT=[-sc,s['LOST'],s['DELIVERY']],
        DETOUR_RETURN=[-dc,d['LOST'],d['DELIVERY']],
        DETOUR_RETRY=[-dc-d['RECOVERY']*rc,
            d['LOST']+d['RECOVERY']*r['LOST'],d['DELIVERY']+d['RECOVERY']*r['DELIVERY']])


def oracle_goal(pure):
    delta=F(1,20); utility=lambda value:value[0]+4*value[2]
    options=[utility(value) for value in pure.values() if value[1]<=delta]
    for a,b in combinations(pure.values(),2):
        if min(a[1],b[1])<delta<max(a[1],b[1]):
            w=(delta-b[1])/(a[1]-b[1])
            options.append(w*utility(a)+(1-w)*utility(b))
    return max(options)


def covered(box,law):
    return all(lo<=law[op][cat]<=hi for op,row in box.items()
               for cat,(lo,hi) in row['bounds'].items())


def run():
    OUTPUT.mkdir(parents=True,exist_ok=False)
    for name in SOURCE_FILES:
        dest=OUTPUT/'source_code'/name; dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(ROOT/name,dest)
    save(OUTPUT/'source_manifest.json',list(SOURCE_FILES))
    qualification=[]; totals=Counter()
    for life in range(12):
        cases,laws,_,metadata=task.world(life)
        for stage,(start,end) in metadata['stage_ranges'].items():
            values=[oracle_goal(pure_values(cases[i],laws[i])) for i in range(start,end)]
            failed=sum(value<2 for value in values)
            qualification.append(dict(life=life,stage=stage,targets=len(values),
                oracle_goal_below_2=failed,min_oracle_utility=min(values)))
            totals[stage+'_below_2']+=failed; totals[stage+'_targets']+=len(values)
    checks=Counter(); rows=[]; work={a:Counter() for a in core.ARMS}
    # Synthetic exact-frequency fixtures test scope, not statistical performance.
    for life in range(3):
        cases,laws,identities,metadata=task.world(life)
        states={a:core.prepare([fixture(laws[i],10000) for i in (0,1,2)],a,work[a]) for a in core.ARMS}
        for index,case in enumerate(cases):
            if case['stage'] in ('SOURCE','B_SOURCE'):
                continue
            if index==30:
                for arm,state in states.items():
                    core.begin_b(state,[fixture(laws[i],10000) for i in (27,28,29)],work[arm])
            for arm,state in states.items():
                member=fixture(laws[index],100); before_a=deepcopy(state['a'])
                before_b=deepcopy(state['b'])
                plan=core.make_plan(member,case,state,work[arm])
                pure=pure_values(case,laws[index]); optimum=oracle_goal(pure)
                if case['context']=='A':
                    key='A/'+str(identities[index])
                elif arm=='REBUILD_CS':
                    key='rebuild/'+str(identities[index])
                else:
                    true=metadata['changed_operator']+':'+''.join(map(str,metadata['b_to_a']))
                    key=true+'/'+str(identities[index])
                checks['true_candidate']+=key in plan['candidate_envelopes']
                checks['true_candidate_coverage']+=key in plan['candidate_envelopes'] and covered(plan['candidate_envelopes'][key],laws[index])
                actual=[sum(w*pure[name][j] for name,w in plan['mix']) for j in range(3)]
                goal=actual[0]+4*actual[2]
                checks['execution_bounds']+=plan['utility_lower']<=goal and actual[1]<=plan['risk_upper']<=F(1,20)
                checks['optimistic_goal_upper']+=optimum<=plan['goal_upper']
                checks['infeasible_sound']+=not plan['goal_impossible'] or optimum<2
                regrets={}
                for query,weights in core.query_bounds.WEIGHTS.items():
                    value=lambda vector:weights[0]*vector[0]-weights[1]*vector[1]+weights[2]*vector[2]
                    selected=plan['queries'][query]['policy']
                    regret=max(map(value,pure.values()))-value(pure[selected])
                    regrets[query]=regret
                    checks['query_regret_bounds']+=F(0)<=regret<=plan['query_certificates'][query]['regret_upper']
                terminal=core.finish(plan)
                checks['separate_eligibility']+=terminal['execution_certified']==(plan['utility_lower']>=2)
                event=core.advance(state,member,case,plan,work[arm])
                checks['context_isolation']+=state['a']==before_a if case['context']=='B' else state['b']==before_b
                rows.append(dict(life=life,index=index,arm=arm,stage=case['stage'],
                    fixture_samples_per_operator=100,goal_impossible=plan['goal_impossible'],
                    execution_certified=terminal['execution_certified'],query_certified=terminal['query_certified'],
                    goal_lower=plan['utility_lower'],goal_upper=plan['goal_upper'],oracle_goal=optimum,
                    actual_regret=regrets,query_bounds=plan['query_certificates'],advance=event))
        print(json.dumps(dict(life=life,validated_records=len(rows))),flush=True)
    expected={name:len(rows)*(3 if name=='query_regret_bounds' else 1) for name in checks}
    valid=len(rows)==648 and all(checks[name]==count for name,count in expected.items())
    save(OUTPUT/'qualification.json',qualification); save(OUTPUT/'probe_records.json',rows)
    summary=dict(valid=valid,complete=True,kind='deterministic_contract_validation',
        scientific_performance_gate=None,stage_environment_samples=0,records=len(rows),
        checks=checks,expected=expected,task_qualification=totals,work=work,
        decision='SCOPED_REPAIR_CONTRACT_VALIDATED' if valid else 'SCOPED_REPAIR_CONTRACT_NOT_VALIDATED')
    save(OUTPUT/'summary.json',summary)
    print(json.dumps({k:v for k,v in summary.items() if k!='work'}),flush=True)
    return valid


if __name__=='__main__':
    raise SystemExit(0 if run() else 1)
