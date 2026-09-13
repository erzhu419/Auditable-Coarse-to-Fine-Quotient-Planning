"""Measure local H1 construction and procedural routing with matched controls."""
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
    ROOT, PREVIOUS, contract, dynamics, module, read, save, same_plans,
)
from query_controlled_predictive_local_v72 import make_router

terminal = module('controlled_predictive_symbolic_successors_v71.py', 'acfqp_v72_terminal')
baseline = module('controlled_predictive_symbolic_contract_v71.py', 'acfqp_v72_baseline')
local = module('controlled_predictive_local_builder_v72.py', 'acfqp_v72_builder')
auditor = module('controlled_predictive_local_audit_v72.py', 'acfqp_v72_auditor')
ARMS = ('FULL_BASE', 'COMPOSED_BASE', 'FULL_LOCAL', 'COMPOSED_LOCAL')


def deploy(name, package, directory):
    started = perf_counter()
    encoded = json.dumps(package, separators=(',', ':'), allow_nan=False)+'\n'
    path = directory/f'{name}.package.json'
    path.write_text(encoded)
    package_bytes = len(encoded.encode())
    serialization = perf_counter()-started
    tick = perf_counter()
    with (directory/f'{name}.stdout.log').open('x') as out, (directory/f'{name}.stderr.log').open('x') as err:
        proc = subprocess.run([sys.executable, str(ROOT/'scripts/query_controlled_predictive_local_v72.py'),
            '--package', str(path), '--inputs', str(directory/'inputs.json'),
            '--output', str(directory/f'{name}.worker.json')], stdout=out, stderr=err)
    command_seconds = perf_counter()-tick
    tick = perf_counter()
    del encoded
    gc.collect()
    cleanup = perf_counter()-tick
    total = perf_counter()-started
    process = dict(exit_code=proc.returncode, command_seconds=command_seconds,
        stderr_bytes=(directory/f'{name}.stderr.log').stat().st_size, passed=False)
    if proc.returncode:
        save(directory/f'{name}.failure.json', dict(process=process, paid_seconds=total))
        raise RuntimeError(f'{name} portable exit {proc.returncode}')
    worker = read(directory/f'{name}.worker.json')
    cost = dict(package_bytes=package_bytes,
        router_bytes=len(json.dumps(package['router'], separators=(',', ':')).encode()),
        routing_counts=worker['routing_counts'], planning_counts=worker['planning_counts'],
        index_counts=worker['index_counts'],
        times=dict(serialize=serialization, worker_command=command_seconds, release_gc=cleanup,
            total=total, load=worker['load_seconds'], index=worker['index_seconds'],
            routing=worker['routing_seconds'], planning=worker['planning_seconds']))
    return worker, cost, process


def arm(case, name, rule, terminal_rule, directory):
    started = perf_counter()
    variant, engine = name.split('_')
    build = (baseline if engine == 'BASE' else local).build_model(
        tuple(case['board']), case['horizon'], rule, terminal_rule, variant, max_states=200000)
    construction = perf_counter()-started
    tick = perf_counter()
    payload = contract.model_payload(build)
    labels = [[h, list(board), state] for (h, board), state in build.encoding.items()
              if build.model.terminal[state] == 'ACTIVE']
    package = dict(schema='acfqp.observation_package.v72', kernel=payload,
        router=dict(kind='LOCAL_H1' if name=='COMPOSED_LOCAL' else 'MAP', labels=labels))
    payload_time = perf_counter()-tick
    counts = build.counts
    tick = perf_counter()
    del build
    gc.collect()
    cleanup = perf_counter()-tick
    upstream = perf_counter()-started
    worker, deployment, process = deploy(name, package, directory)
    times = dict(construction=construction, payload_labels=payload_time, build_release_gc=cleanup,
        upstream_total=upstream, deployment_total=deployment['times']['total'],
        total=upstream+deployment['times']['total'])
    return package, worker, dict(counts=counts, times=times, deployment=deployment, portable=process)


def fixed_inputs(case):
    data = read(PREVIOUS/case['name']/'portable_inputs.json')
    full = read(PREVIOUS/case['name']/'FULL.model.json')
    first = next((row for row in full['literal_boards'] if row[0] == 1), None)
    if first is not None:
        h, board, full_id = first
        labels = read(ROOT/'reports/controlled_predictive_observation_v70'/case['name']/
                      'COMPOSED_MAP.package.json')['router']['labels']
        expected = next(state for h2, b, state in labels if h2 == h and b == board)
        data['observations'].append(dict(board=board, horizon=h, expected_full=full_id, expected=expected))
    return data


def snapshot(output):
    scripts = ('run_controlled_predictive_local_v72', 'query_controlled_predictive_local_v72',
        'check_controlled_predictive_local_generalization_v72', 'analyze_controlled_predictive_local_v72',
        'run_controlled_predictive_observation_v70')
    modules = ('controlled_predictive_local_contract_v72', 'controlled_predictive_local_builder_v72',
        'controlled_predictive_local_audit_v72', 'controlled_predictive_symbolic_successors_v71',
        'controlled_predictive_symbolic_contract_v71', 'controlled_predictive_observation_audit_v70',
        'controlled_predictive_observation_dag_v70', 'controlled_predictive_compositional_contract_v69',
        'controlled_predictive_relational_dynamics_v69', 'controlled_predictive_quotient_v1')
    files = ['scripts/'+name+'.py' for name in scripts]+['src/acfqp/science/'+name+'.py' for name in modules]
    files += ['specs/CONTROLLED_PREDICTIVE_LOCAL_CONTRACT_V72.md', 'src/acfqp/domains/standard_2048.py']
    for relative in files:
        destination = output/'source'/relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT/relative, destination)


def run(output):
    started = perf_counter()
    output.mkdir(parents=True, exist_ok=False)
    snapshot(output)
    cases = read(PREVIOUS/'roster.json')['target']
    save(output/'roster.json', cases)
    inputs = {c['name']:fixed_inputs(c) for c in cases}
    for case in cases:
        directory = output/case['name']
        directory.mkdir()
        save(directory/'inputs.json', inputs[case['name']])
    rule_payload = read(PREVIOUS/'learned_rule.json')
    save(output/'learned_rule.json', rule_payload)
    rule = dynamics.LearnedDynamics.from_payload(rule_payload)
    manifest = dict(schema='acfqp.local_contract.v72', status='running', target_roots=len(cases),
        completed_targets=0, original_observations=60, added_h1_observations=27,
        matched_observations=sum(len(x['observations']) for x in inputs.values()),
        source_learning_reused=True, source_fit_calls=0, target_ground_calls=0,
        source_path=str(PREVIOUS), max_concrete_states=200000,
        runtime=dict(python=platform.python_version(), executable=sys.executable))
    save(output/'manifest.json', manifest)
    try:
        tick = perf_counter()
        compiled_rule = terminal.compile_rule(rule)
        manifest['rule_compile'] = dict(seconds=perf_counter()-tick, counts=compiled_rule.compile_counts)
        save(output/'manifest.json', manifest)
        with (output/'targets.jsonl').open('x') as handle:
            for i, case in enumerate(cases):
                case_started = perf_counter()
                directory = output/case['name']
                order = ARMS[i % 4:]+ARMS[:i % 4]
                packages, workers, costs = {}, {}, {}
                for name in order:
                    packages[name], workers[name], costs[name] = arm(case,name,rule,compiled_rule,directory)
                tick = perf_counter()
                full = read(PREVIOUS/case['name']/'FULL.model.json')
                composed = read(PREVIOUS/case['name']/'COMPOSED.model.json')
                old_kernels = dict(FULL={k:v for k,v in full.items() if k!='literal_boards'}, COMPOSED=composed)
                old_labels = dict(FULL=full['literal_boards'], COMPOSED=read(
                    ROOT/'reports/controlled_predictive_observation_v70'/case['name']/
                    'COMPOSED_MAP.package.json')['router']['labels'])
                old_plans = {v:read(PREVIOUS/case['name']/f'{v}.plans.json') for v in ('FULL','COMPOSED')}
                for name in ARMS:
                    variant = name.split('_')[0]
                    entry = costs[name]
                    entry['kernel_equal'] = packages[name]['kernel'] == old_kernels[variant]
                    expected_labels = old_labels[variant]
                    if name == 'COMPOSED_LOCAL':
                        expected_labels = [r for r in expected_labels if r[0]>1]
                    entry['labels_equal'] = packages[name]['router']['labels'] == expected_labels
                    entry['plans_equal'] = same_plans(workers[name],old_plans[variant])
                    key = 'expected_full' if variant=='FULL' else 'expected'
                    entry['routes_equal'] = workers[name]['routes'] == [r[key] for r in inputs[case['name']]['observations']]
                    entry['portable']['passed'] = (entry['plans_equal'] and entry['routes_equal']
                        and not workers[name]['ground_imports'] and entry['portable']['stderr_bytes']==0)
                compiled, loaded_rule = contract.load_model(packages['COMPOSED_LOCAL']['kernel'])
                router, _ = make_router(packages['COMPOSED_LOCAL'],compiled,loaded_rule)
                checked = auditor.audit(full,composed,packages['COMPOSED_LOCAL']['kernel'],
                    packages['COMPOSED_LOCAL']['router']['labels'],
                    lambda board:router(board,1,Counter()), inputs[case['name']]['observations'])
                correct = checked['valid'] and all(all(c[k] for k in
                    ('kernel_equal','labels_equal','plans_equal','routes_equal')) and c['portable']['passed']
                    for c in costs.values())
                record = dict(case=case,status='complete',order=order,arms=costs,audit=checked,
                              verification_seconds=perf_counter()-tick)
                tick = perf_counter()
                del packages,workers,full,composed,old_kernels,old_labels,old_plans,compiled,loaded_rule,router
                gc.collect()
                record['case_cleanup_seconds']=perf_counter()-tick
                record['case_seconds']=perf_counter()-case_started
                handle.write(json.dumps(record,allow_nan=False)+'\n');handle.flush()
                manifest['completed_targets']+=1;save(output/'manifest.json',manifest)
                print(json.dumps(dict(case=case['name'],completed=manifest['completed_targets'],correct=correct)),flush=True)
        manifest['status']='complete'
    except Exception as error:
        manifest.update(status='failed',error=f'{type(error).__name__}: {error}',partial_counts=getattr(error,'counts',{}))
        raise
    finally:
        manifest.update(wall_seconds=perf_counter()-started,
                        peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
        save(output/'manifest.json',manifest)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    run(parser.parse_args().output)
