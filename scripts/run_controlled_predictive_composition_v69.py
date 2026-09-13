"""Identify source rules, generate fresh multilevel models, then audit ground."""
from collections import Counter
from dataclasses import asdict
import argparse
import gc
import json
from pathlib import Path
import platform
import random
import resource
import shutil
import subprocess
import sys
from time import perf_counter

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from acfqp.domains.standard_2048 import Swipe2048Action,swipe_board_v1,state_from_board_v1,step_v1
from acfqp.science.controlled_predictive_relational_dynamics_v69 import fit_rules
from acfqp.science.controlled_predictive_compositional_contract_v69 import build_model,model_payload,load_model
from acfqp.science.controlled_predictive_compositional_audit_v69 import audit
from acfqp.science.controlled_predictive_causal_audit_v67 import compute_reference
from acfqp.science.controlled_predictive_learned_audit_v68 import recursive_support
from acfqp.science.controlled_predictive_quotient_v1 import FiniteModel,Outcome,plan
from acfqp.science.controlled_predictive_2048_v1 import build_development_closure
from run_controlled_predictive_contract_v67 import QUERIES

VARIANTS=('FULL','COMPOSED')
SOURCES=['scripts/run_controlled_predictive_composition_v69.py','scripts/query_controlled_predictive_composition_v69.py',
    'scripts/analyze_controlled_predictive_composition_v69.py','src/acfqp/science/controlled_predictive_relational_dynamics_v69.py',
    'src/acfqp/science/controlled_predictive_compositional_contract_v69.py','src/acfqp/science/controlled_predictive_compositional_audit_v69.py',
    'src/acfqp/science/controlled_predictive_learned_audit_v68.py','src/acfqp/science/controlled_predictive_causal_audit_v67.py',
    'src/acfqp/science/controlled_predictive_quotient_v1.py','src/acfqp/science/controlled_predictive_2048_v1.py',
    'src/acfqp/domains/standard_2048.py','scripts/run_controlled_predictive_contract_v67.py',
    'src/acfqp/science/controlled_predictive_comparison_v2.py','src/acfqp/science/controlled_predictive_comparison_v3.py',
    'specs/CONTROLLED_PREDICTIVE_COMPOSITIONAL_DYNAMICS_V69.md']


def save(path,value):path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')


def targets():
    edges=[(4*r+c,4*r+c+1) for r in range(4) for c in range(3)]
    edges += [(4*r+c,4*(r+1)+c) for r in range(3) for c in range(4)]
    result=[]
    for horizon,count,seed_start,vmod in ((3,24,690200,3),(4,8,690300,2)):
        for index in range(count):
            seed=seed_start+index;rng=random.Random(seed)
            board=[rng.randint(1,10) for _ in range(16)];left,right=edges[index%len(edges)]
            board[left]=board[right]=1+index%10
            for cell in rng.sample([i for i in range(16) if i not in (left,right)],index%vmod):board[cell]=0
            result.append(dict(name=f'v69_h{horizon}_{index:02d}',horizon=horizon,seed=seed,board=board,vacancies=index%vmod))
    return result


def acquire(sources):
    started=perf_counter(); records=[];work=Counter()
    for case in sources:
        board=tuple(case['board']);state=state_from_board_v1(board);work['source_status_calls']+=1
        for action in Swipe2048Action:
            moved,score,changed=swipe_board_v1(board,action);work['afterstate_labels']+=1
            outcomes=[]
            if changed:
                exact=step_v1(state,action);work['full_support_rows']+=1;work['full_support_outcomes']+=len(exact)
                outcomes=[dict(board=list(o.next_state.board),score=o.merge_score,
                    probability=[o.probability.numerator,o.probability.denominator],
                    spawned_cell=o.spawned_cell,spawned_rank=o.spawned_rank) for o in exact]
            records.append(dict(source=case['name'],board=list(board),action=action.value,afterstate=list(moved),
                                score=score,changed=changed,outcomes=outcomes))
    return records,dict(counts=dict(work),seconds=perf_counter()-started)


def source_semantics():
    started=perf_counter()
    path=ROOT/'reports/controlled_predictive_learning_v68/QUOTIENT/kernel.json'
    old=json.loads(path.read_text());restored=0;largest=0.;rows={}
    for state,action,outcomes in old['rows']:
        converted=[]
        for p,next_state,reward in outcomes:
            exact_reward=round(reward*2048)/2048;error=abs(reward-exact_reward)
            if error>1e-12:raise ValueError('source reference reward is not an integer merge score')
            restored+=int(error>0);largest=max(largest,error)
            converted.append(Outcome(p,next_state,exact_reward))
        rows[state,action]=tuple(converted)
    model=FiniteModel({s:h for s,h,t in old['cells']},{s:t for s,h,t in old['cells']},rows,tuple(old['roots']))
    support=recursive_support(model)
    return support,dict(source_path=str(path),seconds=perf_counter()-started,counts=support.counts,
        source_reward_grid_restored_atoms=restored,maximum_reward_restoration=largest)


def arm(case,variant,rule,directory):
    tick=perf_counter();gc.collect();preparation=perf_counter()-tick
    started=perf_counter()
    try:built=build_model(tuple(case['board']),case['horizon'],rule,variant,max_states=200000)
    except ValueError as error:
        save(directory/f'{variant}.failure.json',dict(error=str(error),counts=getattr(error,'counts',{}),
            paid_seconds=preparation+perf_counter()-started));raise
    tick=perf_counter();payload=model_payload(built)
    if variant=='FULL':
        payload['literal_boards']=[[h,list(board),state] for (h,board),state in built.encoding.items()
            if built.model.terminal[state]=='ACTIVE']
    compiled,_=load_model(payload);compilation=perf_counter()-tick
    tick=perf_counter();solutions={name:plan(compiled,q) for name,q in QUERIES.items()};planning=perf_counter()-tick
    tick=perf_counter();encoded=json.dumps(payload,separators=(',',':'),allow_nan=False)+'\n'
    (directory/f'{variant}.model.json').write_text(encoded)
    save(directory/f'{variant}.plans.json',{n:dict(policy=s.policy,values=s.values,counts=s.counts) for n,s in solutions.items()})
    serialization=perf_counter()-tick
    elapsed=perf_counter()-started;tick=perf_counter();gc.collect();cleanup=perf_counter()-tick
    costs=dict(construction=built.counts,planning_counts=dict(sum((Counter(s.counts) for s in solutions.values()),Counter())),
        model_bytes=len(encoded.encode()),times=dict(prepare_gc=preparation,construction=built.elapsed_seconds,
            compilation=compilation,planning=planning,serialization=serialization,cleanup_gc=cleanup,
            total=preparation+elapsed+cleanup))
    save(directory/f'{variant}.costs.json',costs)
    return built,compiled,solutions,costs


def portable(directory,built,solutions,full_build):
    observations=[dict(board=list(board),horizon=h,expected=state) for (h,board),state in built.encoding.items()
                  if state==built.model.roots[0]]
    child=next((dict(board=list(board),horizon=h,expected=state) for (h,board),state in built.encoding.items()
        if h==built.model.layers[built.model.roots[0]]-1 and h>1 and built.model.terminal[state]=='ACTIVE'),None)
    if child:observations.append(child)
    for row in observations:row['expected_full']=full_build.encoding[row['horizon'],tuple(row['board'])]
    save(directory/'portable_inputs.json',dict(observations=observations,queries={n:asdict(q) for n,q in QUERIES.items()}))
    tick=perf_counter()
    with (directory/'portable.stdout.log').open('x') as out,(directory/'portable.stderr.log').open('x') as err:
        process=subprocess.run([sys.executable,str(ROOT/'scripts/query_controlled_predictive_composition_v69.py'),
            '--model',str(directory/'COMPOSED.model.json'),'--inputs',str(directory/'portable_inputs.json'),
            '--output',str(directory/'portable.json')],stdout=out,stderr=err)
    result=dict(exit_code=process.returncode,command_seconds=perf_counter()-tick,
                stderr_bytes=(directory/'portable.stderr.log').stat().st_size,passed=False)
    if process.returncode:return result
    worker=json.loads((directory/'portable.json').read_text());bad=[]
    for name,solution in solutions.items():
        actual=worker['queries'][name]
        if ({int(k):v for k,v in actual['policy'].items()}!=solution.policy or
            {int(k):v for k,v in actual['values'].items()}!=solution.values or actual['counts']!=solution.counts):bad.append(name)
    correct_routes=(worker['routed']==[row['expected'] for row in observations] and
        worker['full_routed']==[row['expected_full'] for row in observations])
    result.update(passed=not bad and correct_routes and not worker['ground_imports'],routes_match=correct_routes,
        observations=len(observations),query_mismatches=bad,routing_counts=worker['routing_counts'],
        routing_seconds=worker['routing_seconds'],full_routing_seconds=worker['full_routing_seconds'],
        full_routing_counts=worker['full_routing_counts'],worker_seconds=worker['worker_seconds_before_write'])
    return result


def run(output):
    started=perf_counter();output.mkdir(parents=True,exist_ok=False)
    sources=json.loads((ROOT/'reports/controlled_predictive_learning_v68/roster.json').read_text())['source']
    sources += [dict(name=f'v69_source_probe_{i}',board=list(line)+(12*[0])) for i,line in enumerate(
        ((1,1,2,0),(1,0,1,0),(1,1,1,1),(10,10,9,0)))]
    cases=targets();save(output/'roster.json',dict(source=sources,target=cases))
    for relative in SOURCES:
        path=output/'source'/relative;path.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/relative,path)
    manifest=dict(schema='acfqp.compositional_dynamics.v69',status='source_learning',source_roots=len(sources),
        target_roots=len(cases),completed_targets=0,limited_targets=0,max_concrete_states=200000,
        target_labels_used_for_fit_or_construction=0,random_environment_samples=0,
        runtime=dict(python=platform.python_version(),executable=sys.executable))
    save(output/'manifest.json',manifest)
    try:
        observations,acquisition=acquire(sources);save(output/'source_observations.json',observations)
        rule=fit_rules(observations);save(output/'learned_rule.json',rule.to_payload())
        manifest.update(status='source_rule_frozen',acquisition=acquisition,rule=rule.to_payload(),
            rule_freeze_seconds_since_start=perf_counter()-started);save(output/'manifest.json',manifest)
        support,support_info=source_semantics();manifest['source_semantics_reference']=support_info
        with (output/'targets.jsonl').open('x') as handle:
            for i,case in enumerate(cases):
                case_started=perf_counter();directory=output/case['name'];directory.mkdir();built={}
                order=VARIANTS if i%2==0 else VARIANTS[::-1]
                try:
                    for variant in order:built[variant]=arm(case,variant,rule,directory)
                    # Both learned models and all policies are frozen before ground.
                    frozen_at=perf_counter()-case_started
                    closure=build_development_closure(horizon=case['horizon'],max_nodes=200000,boards={case['name']:tuple(case['board'])})
                    reference=compute_reference(closure,QUERIES)
                    arms={}
                    for variant in VARIANTS:
                        build,compiled,solutions,costs=built[variant]
                        arms[variant]=dict(costs=costs,audit=audit(build,compiled,closure,QUERIES,solutions,reference,support))
                    exported=portable(directory,built['COMPOSED'][0],built['COMPOSED'][2],built['FULL'][0])
                    record=dict(case=case,status='complete',order=order,arms=arms,portable=exported,
                        policies_frozen_seconds_since_case_start=frozen_at,
                        ground=dict(counts=closure.counts,seconds=closure.elapsed_seconds,
                                    reference_counts=reference.counts,reference_seconds=reference.elapsed_seconds))
                    manifest['completed_targets']+=1
                    del closure,reference,build,compiled,solutions
                except ValueError as error:
                    if 'exceeds max_' not in str(error):raise
                    manifest['limited_targets']+=1
                    record=dict(case=case,status='limited',order=order,error=str(error),partial_counts=getattr(error,'counts',{}),
                        completed_arm_costs={v:x[3] for v,x in built.items()})
                tick=perf_counter();del built;gc.collect();record['case_cleanup_seconds']=perf_counter()-tick
                record['case_seconds']=perf_counter()-case_started
                handle.write(json.dumps(record,allow_nan=False)+'\n');handle.flush();save(output/'manifest.json',manifest)
                print(json.dumps(dict(case=case['name'],status=record['status'],completed=manifest['completed_targets'],
                    limited=manifest['limited_targets'])),flush=True)
        manifest['status']='complete' if not manifest['limited_targets'] else 'complete_with_limits'
    except Exception as error:
        manifest.update(status='failed',error=f'{type(error).__name__}: {error}',partial_counts=getattr(error,'counts',{}));raise
    finally:
        manifest.update(wall_seconds=perf_counter()-started,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
        save(output/'manifest.json',manifest)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    run(parser.parse_args().output)
