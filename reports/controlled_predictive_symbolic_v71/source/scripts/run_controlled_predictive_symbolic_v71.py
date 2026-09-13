"""Factor terminal integration and state abstraction under the frozen V69 rule."""
import argparse
import gc
import json
from pathlib import Path
import platform
import resource
import shutil
import sys
from time import perf_counter

from run_controlled_predictive_observation_v70 import (
    ROOT, PREVIOUS, contract, dynamics, module, read, save, use_package, same_plans,
)

symbolic = module('controlled_predictive_symbolic_successors_v71.py', 'acfqp_v71_successors')
builder = module('controlled_predictive_symbolic_contract_v71.py', 'acfqp_v71_builder')
auditor = module('controlled_predictive_symbolic_audit_v71.py', 'acfqp_v71_audit')
ARMS = ('FULL_ENUM', 'COMPOSED_ENUM', 'FULL_SYMBOLIC', 'COMPOSED_SYMBOLIC')


def arm(case, name, rule, compiled_rule, directory):
    started = perf_counter()
    variant, engine = name.split('_')
    if engine == 'ENUM':
        built = contract.build_model(tuple(case['board']), case['horizon'], rule,
                                     variant, max_states=200000)
    else:
        built = builder.build_model(tuple(case['board']), case['horizon'], rule,
                                    compiled_rule, variant, max_states=200000)
    construction = perf_counter()-started
    tick = perf_counter()
    payload = contract.model_payload(built)
    labels = [[h, list(board), state] for (h, board), state in built.encoding.items()
              if built.model.terminal[state] == 'ACTIVE']
    payload_time = perf_counter()-tick
    counts = built.counts
    tick = perf_counter()
    del built
    gc.collect()
    cleanup = perf_counter()-tick
    upstream = perf_counter()-started
    _, deployment, worker, portable = use_package(name, payload, labels, directory)
    times = dict(construction=construction, payload_labels=payload_time,
        build_release_gc=cleanup, upstream_total=upstream,
        deployment_total=deployment['times']['total'],
        total=upstream+deployment['times']['total'])
    return payload, labels, worker, dict(counts=counts, times=times,
                                       deployment=deployment, portable=portable)


def snapshot(output):
    files = ['scripts/run_controlled_predictive_symbolic_v71.py',
        'scripts/analyze_controlled_predictive_symbolic_v71.py',
        'scripts/run_controlled_predictive_observation_v70.py',
        'scripts/query_controlled_predictive_observation_v70.py',
        'specs/CONTROLLED_PREDICTIVE_SYMBOLIC_SUCCESSORS_V71.md']
    files += ['src/acfqp/science/'+name+'.py' for name in (
        'controlled_predictive_symbolic_successors_v71',
        'controlled_predictive_symbolic_contract_v71', 'controlled_predictive_symbolic_audit_v71',
        'controlled_predictive_observation_audit_v70', 'controlled_predictive_observation_dag_v70',
        'controlled_predictive_compositional_contract_v69',
        'controlled_predictive_relational_dynamics_v69', 'controlled_predictive_quotient_v1')]
    for relative in files:
        destination = output/'source'/relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT/relative, destination)


def run(output):
    started = perf_counter()
    output.mkdir(parents=True, exist_ok=False)
    snapshot(output)
    cases = read(PREVIOUS/'roster.json')['target']
    rule_payload = read(PREVIOUS/'learned_rule.json')
    save(output/'roster.json', cases)
    save(output/'learned_rule.json', rule_payload)
    rule = dynamics.LearnedDynamics.from_payload(rule_payload)
    manifest = dict(schema='acfqp.symbolic_successors.v71', status='running',
        target_roots=len(cases), completed_targets=0, source_learning_reused=True,
        source_fit_calls=0, target_ground_calls=0, arms=ARMS,
        source_path=str(PREVIOUS), max_concrete_states=200000,
        runtime=dict(python=platform.python_version(), executable=sys.executable))
    save(output/'manifest.json', manifest)
    try:
        tick = perf_counter()
        compiled_rule = symbolic.compile_rule(rule)
        manifest['rule_compile'] = dict(seconds=perf_counter()-tick, counts=compiled_rule.compile_counts)
        save(output/'manifest.json', manifest)
        with (output/'targets.jsonl').open('x') as handle:
            for i, case in enumerate(cases):
                case_started = perf_counter()
                directory = output/case['name']
                directory.mkdir()
                inputs = read(PREVIOUS/case['name']/'portable_inputs.json')
                save(directory/'portable_inputs.json', inputs)
                order = ARMS[i % 4:] + ARMS[:i % 4]
                payloads, labels, workers, costs = {}, {}, {}, {}
                for name in order:
                    payloads[name], labels[name], workers[name], costs[name] = arm(
                        case, name, rule, compiled_rule, directory)
                # All four complete deployments are retained before expected data is read.
                tick = perf_counter()
                full = read(PREVIOUS/case['name']/'FULL.model.json')
                composed = read(PREVIOUS/case['name']/'COMPOSED.model.json')
                old_kernels = dict(FULL={k:v for k,v in full.items() if k!='literal_boards'},
                                   COMPOSED=composed)
                old_labels = dict(FULL=full['literal_boards'], COMPOSED=read(
                    ROOT/'reports/controlled_predictive_observation_v70'/case['name']/
                    'COMPOSED_MAP.package.json')['router']['labels'])
                old_plans = {v:read(PREVIOUS/case['name']/f'{v}.plans.json') for v in ('FULL','COMPOSED')}
                for name in ARMS:
                    variant = name.split('_')[0]
                    entry = costs[name]
                    entry['kernel_equal'] = payloads[name] == old_kernels[variant]
                    entry['labels_equal'] = labels[name] == old_labels[variant]
                    entry['plans_equal'] = same_plans(workers[name], old_plans[variant])
                    expected = 'expected_full' if variant == 'FULL' else 'expected'
                    entry['routes_equal'] = workers[name]['routes'] == [o[expected] for o in inputs['observations']]
                    entry['portable']['passed'] = (entry['plans_equal'] and entry['routes_equal']
                        and not workers[name]['ground_imports'] and entry['portable']['stderr_bytes'] == 0)
                checked = auditor.audit(full, composed, payloads['COMPOSED_SYMBOLIC'],
                                        labels['COMPOSED_SYMBOLIC'], inputs['observations'])
                verification = perf_counter()-tick
                correct = checked['valid'] and all(all(c[k] for k in (
                    'kernel_equal','labels_equal','plans_equal','routes_equal')) and c['portable']['passed']
                    for c in costs.values())
                record = dict(case=case, status='complete', order=order, arms=costs,
                              audit=checked, verification_seconds=verification)
                tick = perf_counter()
                del payloads, labels, workers, full, composed, old_kernels, old_labels, old_plans
                gc.collect()
                record['case_cleanup_seconds'] = perf_counter()-tick
                record['case_seconds'] = perf_counter()-case_started
                handle.write(json.dumps(record, allow_nan=False)+'\n')
                handle.flush()
                manifest['completed_targets'] += 1
                save(output/'manifest.json', manifest)
                print(json.dumps(dict(case=case['name'], completed=manifest['completed_targets'], correct=correct)), flush=True)
        manifest['status'] = 'complete'
    except Exception as error:
        manifest.update(status='failed', error=f'{type(error).__name__}: {error}',
                        partial_counts=getattr(error, 'counts', {}))
        raise
    finally:
        manifest.update(wall_seconds=perf_counter()-started,
                        peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
        save(output/'manifest.json', manifest)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    run(parser.parse_args().output)
