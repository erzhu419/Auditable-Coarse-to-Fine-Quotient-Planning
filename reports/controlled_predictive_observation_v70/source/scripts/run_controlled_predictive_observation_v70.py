"""Rebuild frozen V69 models and measure complete direct-encoding packages."""
from collections import Counter
import argparse
import gc
import importlib.util
import json
from pathlib import Path
import platform
import resource
import shutil
import subprocess
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
PREVIOUS = ROOT / 'reports/controlled_predictive_composition_v69'
ARMS = ('FULL_MAP', 'COMPOSED_MAP', 'COMPOSED_DAG')


def module(filename, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'src/acfqp/science' / filename)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


contract = module('controlled_predictive_compositional_contract_v69.py', 'acfqp_v70_contract')
dynamics = module('controlled_predictive_relational_dynamics_v69.py', 'acfqp_v70_dynamics')
dag = module('controlled_predictive_observation_dag_v70.py', 'acfqp_v70_dag')
auditor = module('controlled_predictive_observation_audit_v70.py', 'acfqp_v70_audit')


def read(path):
    return json.loads(path.read_text())


def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def rebuild(case, variant, rule):
    started = perf_counter()
    built = contract.build_model(tuple(case['board']), case['horizon'], rule, variant,
                                 max_states=200000)
    construction = perf_counter() - started
    tick = perf_counter()
    payload = contract.model_payload(built)
    labels = [[h, list(board), state] for (h, board), state in built.encoding.items()
              if built.model.terminal[state] == 'ACTIVE']
    payload_seconds = perf_counter() - tick
    counts = dict(built.counts)
    tick = perf_counter()
    del built
    gc.collect()
    cleanup = perf_counter() - tick
    return payload, labels, dict(counts=counts, times=dict(construction=construction,
        payload_labels=payload_seconds, cleanup_gc=cleanup, total=perf_counter()-started))


def use_package(name, kernel, labels, directory):
    started = perf_counter()
    tick = perf_counter()
    if name.endswith('_DAG'):
        encoder = dag.compile_encoder(labels)
        router = dict(kind='DAG', data=encoder.to_payload())
        compile_counts = encoder.counts
        del encoder
    else:
        router = dict(kind='MAP', labels=labels)
        compile_counts = dict(input_labels=len(labels), retained_rank_slots=16*len(labels))
    compilation = perf_counter() - tick
    tick = perf_counter()
    package = dict(schema='acfqp.observation_package.v70', kernel=kernel, router=router)
    encoded = json.dumps(package, separators=(',', ':'), allow_nan=False) + '\n'
    path = directory / f'{name}.package.json'
    path.write_text(encoded)
    package_bytes = len(encoded.encode())
    serialization = perf_counter() - tick
    tick = perf_counter()
    with (directory/f'{name}.stdout.log').open('x') as out, (directory/f'{name}.stderr.log').open('x') as err:
        process = subprocess.run([sys.executable, str(ROOT/'scripts/query_controlled_predictive_observation_v70.py'),
            '--package', str(path), '--inputs', str(directory/'portable_inputs.json'),
            '--output', str(directory/f'{name}.worker.json')], stdout=out, stderr=err)
    command_seconds = perf_counter() - tick
    tick = perf_counter()
    del encoded, package
    gc.collect()
    release = perf_counter() - tick
    elapsed = perf_counter() - started
    # Result reading and diagnostics below are verification, outside method time.
    router_bytes = len(json.dumps(router, separators=(',', ':')).encode())
    process_info = dict(exit_code=process.returncode, command_seconds=command_seconds,
        stderr_bytes=(directory/f'{name}.stderr.log').stat().st_size, passed=False)
    if process.returncode:
        save(directory/f'{name}.failure.json', dict(process=process_info, paid_seconds=elapsed))
        raise RuntimeError(f'{name} worker exit {process.returncode}')
    worker = read(directory/f'{name}.worker.json')
    times = dict(router_compile=compilation, serialize=serialization, worker_command=command_seconds,
        load=worker['load_seconds'], index=worker['index_seconds'], planning=worker['planning_seconds'],
        routing=worker['routing_seconds'], release_gc=release, total=elapsed)
    times['worker_overhead'] = command_seconds - sum(times[k] for k in ('load','index','planning','routing'))
    cost = dict(times=times, package_bytes=package_bytes, router_bytes=router_bytes,
        compile_counts=compile_counts, routing_counts=worker['routing_counts'],
        planning_counts=worker['planning_counts'])
    return router, cost, worker, process_info


def verification_router(payload):
    if payload['kind'] == 'DAG':
        return dag.Encoder.from_payload(payload['data']).encode
    index = {(h, tuple(board)): state for h, board, state in payload['labels']}
    return lambda board, h: index.get((h, tuple(board)))


def same_plans(worker, old):
    actual = {name: {key: row[key] for key in ('policy','values','counts')}
              for name, row in worker['queries'].items()}
    return actual == old


def snapshot(output):
    files = ['scripts/run_controlled_predictive_observation_v70.py',
        'scripts/query_controlled_predictive_observation_v70.py',
        'scripts/analyze_controlled_predictive_observation_v70.py',
        'specs/CONTROLLED_PREDICTIVE_OBSERVATION_COMPILATION_V70.md']
    files += ['src/acfqp/science/'+f+'.py' for f in (
        'controlled_predictive_compositional_contract_v69', 'controlled_predictive_relational_dynamics_v69',
        'controlled_predictive_quotient_v1', 'controlled_predictive_observation_dag_v70',
        'controlled_predictive_observation_audit_v70')]
    for relative in files:
        target = output/'source'/relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT/relative, target)


def run(output):
    started = perf_counter()
    output.mkdir(parents=True, exist_ok=False)
    snapshot(output)
    roster = read(PREVIOUS/'roster.json')['target']
    save(output/'roster.json', roster)
    rule_payload = read(PREVIOUS/'learned_rule.json')
    save(output/'learned_rule.json', rule_payload)
    rule = dynamics.LearnedDynamics.from_payload(rule_payload)
    manifest = dict(schema='acfqp.observation_compilation.v70', status='running',
        completed_targets=0, target_roots=len(roster), source_learning_reused=True,
        source_path=str(PREVIOUS), source_fit_calls=0, target_ground_calls=0,
        shared_composed_builds=True, runtime=dict(python=platform.python_version(), executable=sys.executable))
    save(output/'manifest.json', manifest)
    try:
        with (output/'targets.jsonl').open('x') as handle:
            for i, case in enumerate(roster):
                case_started = perf_counter()
                directory = output/case['name']
                directory.mkdir()
                inputs = read(PREVIOUS/case['name']/'portable_inputs.json')
                save(directory/'portable_inputs.json', inputs)
                order = ('FULL','COMPOSED') if i % 2 == 0 else ('COMPOSED','FULL')
                kernels, labels, upstream = {}, {}, {}
                for variant in order:
                    kernels[variant], labels[variant], upstream[variant] = rebuild(case, variant, rule)
                use_order = ARMS[i % 3:] + ARMS[:i % 3]
                routers, arms, workers, portable = {}, {}, {}, {}
                for name in use_order:
                    variant = name.split('_')[0]
                    routers[name], arms[name], workers[name], portable[name] = use_package(
                        name, kernels[variant], labels[variant], directory)
                # All artifacts are fixed before independent correspondence checks.
                tick = perf_counter()
                old_full = read(PREVIOUS/case['name']/'FULL.model.json')
                old_composed = read(PREVIOUS/case['name']/'COMPOSED.model.json')
                old_kernels = dict(FULL={k:v for k,v in old_full.items() if k!='literal_boards'},
                                   COMPOSED=old_composed)
                old_plans = {v:read(PREVIOUS/case['name']/f'{v}.plans.json') for v in order}
                for name in ARMS:
                    variant = name.split('_')[0]
                    arms[name]['kernel_equal'] = kernels[variant] == old_kernels[variant]
                    arms[name]['plans_equal'] = same_plans(workers[name], old_plans[variant])
                    expected_key = 'expected_full' if variant == 'FULL' else 'expected'
                    arms[name]['routes_equal'] = workers[name]['routes'] == [r[expected_key] for r in inputs['observations']]
                    portable[name]['passed'] = (arms[name]['plans_equal'] and arms[name]['routes_equal']
                        and not workers[name]['ground_imports'] and portable[name]['stderr_bytes'] == 0)
                checked = auditor.audit(old_full, old_composed,
                    {n:verification_router(routers[n]) for n in ARMS}, inputs['observations'])
                verification_seconds = perf_counter() - tick
                record = dict(case=case, status='complete', build_order=order, use_order=use_order,
                    upstream=upstream, arms=arms, audit=checked, portable=portable,
                    verification_seconds=verification_seconds)
                tick = perf_counter()
                del kernels, labels, routers, workers, old_full, old_composed, old_kernels, old_plans
                gc.collect()
                record['case_cleanup_seconds'] = perf_counter() - tick
                record['case_seconds'] = perf_counter() - case_started
                handle.write(json.dumps(record, allow_nan=False)+'\n')
                handle.flush()
                manifest['completed_targets'] += 1
                save(output/'manifest.json', manifest)
                print(json.dumps(dict(case=case['name'], completed=manifest['completed_targets'],
                    correct=checked['valid'] and all(a['kernel_equal'] and a['plans_equal'] and a['routes_equal']
                        for a in arms.values()))), flush=True)
        manifest['status'] = 'complete'
    except Exception as error:
        manifest.update(status='failed', error=f'{type(error).__name__}: {error}', partial_counts=getattr(error,'counts',{}))
        raise
    finally:
        manifest.update(wall_seconds=perf_counter()-started,
                        peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
        save(output/'manifest.json', manifest)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    run(parser.parse_args().output)
