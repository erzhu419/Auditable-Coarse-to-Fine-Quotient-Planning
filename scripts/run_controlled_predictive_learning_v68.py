"""Source-only learned world model; target kernels are opened after policy freeze."""
from collections import Counter
from dataclasses import asdict
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

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
import torch
from acfqp.science.controlled_predictive_action_contract_v67 import build_model
from acfqp.science.controlled_predictive_learning_cohort_v68 import roster
from acfqp.science.controlled_predictive_learned_model_v68 import assemble_sources, train_model, save_model
from acfqp.science.controlled_predictive_learned_audit_v68 import (
    recursive_support, support_coverage, audit_frozen,
)
from acfqp.science.controlled_predictive_causal_audit_v67 import compute_reference
from acfqp.science.controlled_predictive_2048_v1 import build_development_closure
from acfqp.science.controlled_predictive_quotient_v1 import plan
from run_controlled_predictive_contract_v67 import QUERIES

VARIANTS = ('QUOTIENT', 'RAW')
SOURCES = ['scripts/run_controlled_predictive_learning_v68.py',
    'scripts/query_controlled_predictive_learning_v68.py',
    'scripts/analyze_controlled_predictive_learning_v68.py',
    'src/acfqp/science/controlled_predictive_learning_cohort_v68.py',
    'src/acfqp/science/controlled_predictive_learned_model_v68.py',
    'src/acfqp/science/controlled_predictive_learned_audit_v68.py',
    'src/acfqp/science/controlled_predictive_action_contract_v67.py',
    'src/acfqp/science/controlled_predictive_causal_forgetting_v66.py',
    'src/acfqp/science/controlled_predictive_quotient_v1.py',
    'src/acfqp/science/controlled_predictive_causal_audit_v67.py',
    'src/acfqp/science/controlled_predictive_2048_v1.py',
    'src/acfqp/science/controlled_predictive_cohort_v7.py',
    'src/acfqp/science/controlled_predictive_comparison_v2.py',
    'src/acfqp/science/controlled_predictive_comparison_v3.py',
    'src/acfqp/domains/standard_2048.py',
    'scripts/run_controlled_predictive_contract_v67.py',
    'specs/CONTROLLED_PREDICTIVE_LEARNED_WORLD_MODEL_V68.md']


def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')


def portable(directory, inputs_path, expected_codes, solutions):
    tick = perf_counter()
    with (directory/'portable.stdout.log').open('x') as out, (directory/'portable.stderr.log').open('x') as err:
        process = subprocess.run([sys.executable,
            str(ROOT/'scripts/query_controlled_predictive_learning_v68.py'),
            '--model', str(directory), '--inputs', str(inputs_path),
            '--output', str(directory/'portable.json')], stdout=out, stderr=err)
    result = dict(exit_code=process.returncode, command_seconds=perf_counter()-tick,
                  stderr_bytes=(directory/'portable.stderr.log').stat().st_size, passed=False)
    if process.returncode:
        return result
    worker = json.loads((directory/'portable.json').read_text())
    mismatch = []
    for name, solution in solutions.items():
        row = worker['queries'][name]
        if ({int(k):v for k,v in row['policy'].items()} != solution.policy or
                {int(k):v for k,v in row['values'].items()} != solution.values or row['counts'] != solution.counts):
            mismatch.append(name)
    result.update(passed=not mismatch and worker['encoded']==expected_codes and not worker['ground_imports'],
                  codes_equal=worker['encoded']==expected_codes, query_mismatches=mismatch,
                  worker_seconds=worker['wall_seconds_before_write'], inference_counts=worker['inference_counts'])
    return result


def run(output):
    started = perf_counter()
    output.mkdir(parents=True, exist_ok=False)
    torch.set_num_threads(1)
    inputs = roster()
    save(output/'roster.json', inputs)
    save(output/'queries.json', {n:asdict(q) for n,q in QUERIES.items()})
    save(output/'portable_inputs.json', dict(cases=inputs['target'], queries={n:asdict(q) for n,q in QUERIES.items()}))
    for relative in SOURCES:
        destination = output/'source'/relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT/relative, destination)
    manifest = dict(schema='acfqp.learned_world_model.v68', status='source_construction',
        source_cases=len(inputs['source']), target_cases=len(inputs['target']),
        completed_targets=0, runtime=dict(python=platform.python_version(), torch=torch.__version__,
            executable=sys.executable, device='cpu', threads=torch.get_num_threads()),
        training_protocol=dict(steps=1500, batch_size=128, seed=6801, lr=.001),
        target_transition_rows_used_for_training_or_kernel_fill=0, new_random_environment_samples=0)
    save(output/'manifest.json', manifest)
    try:
        builds, source_costs = [], []
        with (output/'source_cases.jsonl').open('x') as log:
            for case in inputs['source']:
                built = build_model(tuple(case['board']), case['horizon'], 'BASELINE', max_states=30000)
                builds.append(built)
                cost = dict(case=case, counts=built.counts, seconds=built.elapsed_seconds)
                source_costs.append(cost)
                log.write(json.dumps(cost)+'\n'); log.flush()
        source = assemble_sources(builds)
        manifest['source'] = dict(counts=source.counts, assembly_seconds=source.elapsed_seconds,
            teacher_seconds=sum(c['seconds'] for c in source_costs),
            teacher_counts=dict(sum((Counter(c['counts']) for c in source_costs), Counter())))
        del builds
        models, policies, model_costs = {}, {}, {}
        for variant in VARIANTS:
            directory = output/variant
            tick = perf_counter(); gc.collect(); prepare = perf_counter()-tick
            tick = perf_counter()
            model = train_model(source, variant=variant, steps=1500, batch_size=128, seed=6801)
            learning = perf_counter()-tick
            tick = perf_counter(); solutions = {n:plan(model.compiled, q) for n,q in QUERIES.items()}
            planning = perf_counter()-tick
            tick = perf_counter(); save_model(model, directory)
            save(directory/'plans.json', {n:dict(policy=p.policy, values=p.values, counts=p.counts) for n,p in solutions.items()})
            serialization = perf_counter()-tick
            payload_bytes = sum(p.stat().st_size for p in directory.iterdir() if p.is_file() and p.name != 'plans.json')
            tick = perf_counter(); gc.collect(); cleanup = perf_counter()-tick
            models[variant], policies[variant] = model, solutions
            costs = dict(training=model.training_report, learning_and_compile_seconds=learning,
                planning_seconds=planning, serialization_seconds=serialization, prepare_gc_seconds=prepare,
                cleanup_gc_seconds=cleanup, model_bytes=payload_bytes,
                total_seconds=prepare+learning+planning+serialization+cleanup,
                active_cells=sum(c.terminal=='ACTIVE' for c in model.compiled.cells.values()),
                cells_by_horizon=dict(Counter(str(c.layer) for c in model.compiled.cells.values() if c.terminal=='ACTIVE')),
                planning_counts=dict(sum((Counter(p.counts) for p in solutions.values()), Counter())))
            save(directory/'costs.json', costs); model_costs[variant] = costs
            print(json.dumps(dict(variant=variant, phase='trained', active_cells=costs['active_cells'], seconds=learning)), flush=True)
        manifest.update(status='models_and_policies_frozen', models=model_costs,
                        freeze_seconds_since_start=perf_counter()-started)
        save(output/'manifest.json', manifest)
        for variant, model in models.items():
            codes = model.batch_encode([tuple(c['board']) for c in inputs['target']], [c['horizon'] for c in inputs['target']])
            model_costs[variant]['portable'] = portable(output/variant, output/'portable_inputs.json', codes, policies[variant])
        # Source support and all target outcomes are now audit-only information.
        tick = perf_counter(); support = recursive_support(source.model)
        manifest['source_support_seconds'] = perf_counter()-tick
        manifest['source_support_counts'] = support.counts
        source_keys = {(source.model.layers[s], b) for s,b in source.boards.items()}
        with (output/'targets.jsonl').open('x') as log:
            for case in inputs['target']:
                case_tick = perf_counter()
                closure = build_development_closure(horizon=case['horizon'], max_nodes=200000,
                    boards={case['name']:tuple(case['board'])})
                reference = compute_reference(closure, QUERIES)
                tick = perf_counter(); target_support = support_coverage(closure.model, support)
                support_seconds = perf_counter()-tick
                active = [s for s in closure.model.layers if closure.model.terminal[s]=='ACTIVE']
                arms = {}
                for variant, model in models.items():
                    before = Counter(model.inference_counts)
                    tick = perf_counter()
                    codes = model.batch_encode([closure.boards[s] for s in active], [closure.model.layers[s] for s in active])
                    encoding_seconds = perf_counter()-tick
                    mapping = dict(zip(active, codes))
                    audit = audit_frozen(closure, QUERIES, model.compiled, policies[variant], mapping, reference, support,
                        encoding_counts=Counter(model.inference_counts)-before,
                        encoding_seconds=encoding_seconds, target_support=target_support)
                    arms[variant] = dict(audit=audit, encoding_seconds=encoding_seconds,
                        encoded_states=len(active), distinct_codes=len(set(codes)),
                        codes_by_horizon={str(h):len({mapping[s] for s in active if closure.model.layers[s]==h}) for h in range(1,4)})
                record = dict(case=case, arms=arms,
                    source_active_overlap=sum((closure.model.layers[s], closure.boards[s]) in source_keys for s in active),
                    ground=dict(counts=closure.counts, seconds=closure.elapsed_seconds, support_seconds=support_seconds,
                        reference_counts=reference.counts, reference_seconds=reference.elapsed_seconds),
                    case_seconds=perf_counter()-case_tick)
                log.write(json.dumps(record, allow_nan=False)+'\n'); log.flush()
                manifest['completed_targets'] += 1
                save(output/'manifest.json', manifest)
                print(json.dumps(dict(case=case['name'], phase='audited', active=len(active),
                    completed_targets=manifest['completed_targets'])), flush=True)
        manifest['status'] = 'complete'
    except Exception as error:
        manifest.update(status='failed', error=f'{type(error).__name__}: {error}', partial_counts=getattr(error, 'counts', None))
        raise
    finally:
        manifest.update(wall_seconds=perf_counter()-started,
            process_peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
        save(output/'manifest.json', manifest)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    run(parser.parse_args().output)
