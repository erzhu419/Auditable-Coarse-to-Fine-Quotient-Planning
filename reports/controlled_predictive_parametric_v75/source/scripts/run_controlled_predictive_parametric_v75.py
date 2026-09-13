"""Measure guarded parametric H2 construction on the frozen V69 cohort."""
from collections import Counter
import argparse
import gc
import json
from pathlib import Path
import platform
import resource
import shutil
import subprocess
import sys
from time import perf_counter

from run_controlled_predictive_observation_v70 import (
    ROOT,PREVIOUS,contract,dynamics,module,read,save,same_plans,
)

terminal=module('controlled_predictive_symbolic_successors_v71.py','acfqp_v75_terminal')
baseline=module('controlled_predictive_effect_builder_v74.py','acfqp_v75_baseline')
parametric=module('controlled_predictive_parametric_builder_v75.py','acfqp_v75_builder')
ARMS=('BASE','TRACE','PARAM')
OLD=ROOT/'reports/controlled_predictive_effect_v74'


def deploy(name,package,directory):
    started=perf_counter()
    encoded=json.dumps(package,separators=(',',':'),allow_nan=False)+'\n'
    path=directory/f'{name}.package.json';path.write_text(encoded)
    size=len(encoded.encode());serialization=perf_counter()-started
    tick=perf_counter()
    with (directory/f'{name}.stdout.log').open('x') as out,(directory/f'{name}.stderr.log').open('x') as err:
        proc=subprocess.run([sys.executable,str(ROOT/'scripts/query_controlled_predictive_effect_v74.py'),
            '--package',str(path),'--inputs',str(directory/'inputs.json'),
            '--output',str(directory/f'{name}.worker.json')],stdout=out,stderr=err)
    command_seconds=perf_counter()-tick
    tick=perf_counter();del encoded;gc.collect();cleanup=perf_counter()-tick
    total=perf_counter()-started
    process=dict(exit_code=proc.returncode,command_seconds=command_seconds,
                 stderr_bytes=(directory/f'{name}.stderr.log').stat().st_size,passed=False)
    if proc.returncode:
        save(directory/f'{name}.failure.json',dict(process=process,paid_seconds=total))
        raise RuntimeError(f'{name} portable exit {proc.returncode}')
    worker=read(directory/f'{name}.worker.json')
    cost=dict(package_bytes=size,router_bytes=len(json.dumps(package['router'],separators=(',',':')).encode()),
        routing_counts=worker['routing_counts'],planning_counts=worker['planning_counts'],
        index_counts=worker['index_counts'],times=dict(serialize=serialization,worker_command=command_seconds,
        release_gc=cleanup,total=total,load=worker['load_seconds'],index=worker['index_seconds'],
        routing=worker['routing_seconds'],planning=worker['planning_seconds']))
    return worker,cost,process


def arm(case,name,rule,terminal_rule,directory):
    started=perf_counter()
    if name=='BASE':
        built=baseline.build_model(tuple(case['board']),case['horizon'],rule,terminal_rule,
                                   share_successors=True,max_states=200000)
    else:
        built=parametric.build_model(tuple(case['board']),case['horizon'],rule,terminal_rule,
                                     reuse=name=='PARAM',max_states=200000)
    construction=perf_counter()-started;tick=perf_counter()
    labels=[[h,list(board),state] for (h,board),state in built.encoding.items()
            if built.model.terminal[state]=='ACTIVE']
    router=dict(kind='SHARED_EFFECT_H2',labels=labels,grouping=True)
    package=dict(schema='acfqp.observation_package.v74',kernel=contract.model_payload(built),router=router)
    payload_time=perf_counter()-tick;counts=built.counts
    tick=perf_counter();del built;gc.collect();cleanup=perf_counter()-tick
    upstream=perf_counter()-started
    worker,deployment,process=deploy(name,package,directory)
    times=dict(construction=construction,payload_labels=payload_time,build_release_gc=cleanup,
        upstream_total=upstream,deployment_total=deployment['times']['total'],
        total=upstream+deployment['times']['total'])
    return package,worker,dict(counts=counts,times=times,deployment=deployment,portable=process)


def inputs_for(case):
    return read(OLD/case['name']/'inputs.json')


def snapshot(output):
    scripts=('run_controlled_predictive_parametric_v75','analyze_controlled_predictive_parametric_v75',
        'check_controlled_predictive_parametric_binding_v75','query_controlled_predictive_effect_v74',
        'query_controlled_predictive_grouped_v73','query_controlled_predictive_local_v72',
        'run_controlled_predictive_observation_v70','check_controlled_predictive_grouped_generalization_v73')
    modules=('controlled_predictive_parametric_contract_v75','controlled_predictive_parametric_line_v75',
        'controlled_predictive_parametric_builder_v75','controlled_predictive_effect_contract_v74',
        'controlled_predictive_effect_builder_v74','controlled_predictive_grouped_contract_v73',
        'controlled_predictive_local_contract_v72','controlled_predictive_symbolic_successors_v71',
        'controlled_predictive_observation_audit_v70','controlled_predictive_observation_dag_v70',
        'controlled_predictive_compositional_contract_v69','controlled_predictive_relational_dynamics_v69',
        'controlled_predictive_quotient_v1')
    files=['scripts/'+n+'.py' for n in scripts]+['src/acfqp/science/'+n+'.py' for n in modules]
    files+=['specs/CONTROLLED_PREDICTIVE_PARAMETRIC_H2_V75.md',
            'tests/test_controlled_predictive_parametric_line_v75.py',
            'tests/test_controlled_predictive_parametric_contract_v75.py',
            'tests/test_controlled_predictive_parametric_integration_v75.py',
            'src/acfqp/domains/standard_2048.py']
    for relative in files:
        destination=output/'source'/relative;destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(ROOT/relative,destination)


def run(output):
    started=perf_counter();output.mkdir(parents=True,exist_ok=False);snapshot(output)
    cases=read(PREVIOUS/'roster.json')['target'];save(output/'roster.json',cases)
    inputs={c['name']:inputs_for(c) for c in cases}
    for case in cases:
        directory=output/case['name'];directory.mkdir();save(directory/'inputs.json',inputs[case['name']])
    rule_payload=read(PREVIOUS/'learned_rule.json');save(output/'learned_rule.json',rule_payload)
    rule=dynamics.LearnedDynamics.from_payload(rule_payload)
    manifest=dict(schema='acfqp.parametric_h2.v75',status='running',target_roots=len(cases),completed_targets=0,
        original_observations=87,added_h2_observations=8,
        inherited_v74_audit=True,new_full_route_audits=0,
        matched_observations=sum(len(v['observations']) for v in inputs.values()),
        source_learning_reused=True,source_fit_calls=0,target_ground_calls=0,max_geometries=200000,
        source_path=str(PREVIOUS),runtime=dict(python=platform.python_version(),executable=sys.executable))
    save(output/'manifest.json',manifest)
    try:
        tick=perf_counter();terminal_rule=terminal.compile_rule(rule)
        manifest['rule_compile']=dict(seconds=perf_counter()-tick,counts=terminal_rule.compile_counts)
        save(output/'manifest.json',manifest)
        with (output/'targets.jsonl').open('x') as handle:
            for i,case in enumerate(cases):
                case_started=perf_counter();directory=output/case['name'];order=ARMS[i%3:]+ARMS[:i%3]
                packages,workers,costs={},{},{}
                for name in order:packages[name],workers[name],costs[name]=arm(case,name,rule,terminal_rule,directory)
                tick=perf_counter()
                old_package=read(OLD/case['name']/'SHARED.package.json')
                old=old_package['kernel'];old_labels=old_package['router']['labels']
                plans=read(PREVIOUS/case['name']/'COMPOSED.plans.json')
                for name in ARMS:
                    entry=costs[name]
                    entry['kernel_equal']=packages[name]['kernel']==old
                    entry['labels_equal']=packages[name]['router']['labels']==old_labels
                    entry['package_exact_v74']=packages[name]==old_package
                    entry['plans_equal']=same_plans(workers[name],plans)
                    entry['routes_equal']=workers[name]['routes']==[o['expected'] for o in inputs[case['name']]['observations']]
                    entry['portable']['passed']=(entry['plans_equal'] and entry['routes_equal'] and
                        not workers[name]['ground_imports'] and entry['portable']['stderr_bytes']==0)
                correct=all(all(c[k] for k in ('kernel_equal','labels_equal','plans_equal',
                    'routes_equal','package_exact_v74')) and c['portable']['passed'] for c in costs.values())
                record=dict(case=case,status='complete',order=order,arms=costs,
                    inherited_v74_audit=True,verification_seconds=perf_counter()-tick)
                tick=perf_counter();del packages,workers,old_package,old,old_labels,plans;gc.collect()
                record['case_cleanup_seconds']=perf_counter()-tick;record['case_seconds']=perf_counter()-case_started
                handle.write(json.dumps(record,allow_nan=False)+'\n');handle.flush()
                manifest['completed_targets']+=1;save(output/'manifest.json',manifest)
                print(json.dumps(dict(case=case['name'],completed=manifest['completed_targets'],correct=correct)),flush=True)
        manifest['status']='complete'
    except Exception as error:
        manifest.update(status='failed',error=f'{type(error).__name__}: {error}',partial_counts=getattr(error,'counts',{}));raise
    finally:
        manifest.update(wall_seconds=perf_counter()-started,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
        save(output/'manifest.json',manifest)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    run(parser.parse_args().output)
