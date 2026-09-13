"""Build symbolic dynamics before independent full-state development audits."""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict
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
from acfqp.science.controlled_predictive_cohort_v7 import cases_v7
from acfqp.science.controlled_predictive_comparison_v2 import COMPARISON_QUERIES
from acfqp.science.controlled_predictive_comparison_v3 import PROBE_QUERIES
from acfqp.science.controlled_predictive_2048_v1 import build_development_closure
from acfqp.science.controlled_predictive_quotient_v1 import Query, compile_full_state, build_quotient, plan
from acfqp.science.controlled_predictive_action_contract_v67 import build_model
from acfqp.science.controlled_predictive_contract_io_v67 import model_payload
from acfqp.science.controlled_predictive_causal_audit_v67 import compute_reference, audit_build

VARIANTS = ['BASELINE', 'CONTRACT', 'UNSAFE']
QUERIES = {**COMPARISON_QUERIES, **PROBE_QUERIES,
    'new_low_risk_goal': Query(1., .004, .3),
    'new_risk_goal': Query(1., .02, .3),
    'new_scaled_reward': Query(.4, .4, 1.2),
    'new_combined_query': Query(1., .3, .2)}
SOURCES = ['scripts/run_controlled_predictive_contract_v67.py',
    'scripts/analyze_controlled_predictive_contract_v67.py',
    'scripts/query_controlled_predictive_contract_v67.py',
    'specs/CONTROLLED_PREDICTIVE_ACTION_CONTRACT_V67.md',
    'src/acfqp/science/controlled_predictive_action_contract_v67.py',
    'src/acfqp/science/controlled_predictive_causal_forgetting_v66.py',
    'src/acfqp/science/controlled_predictive_contract_io_v67.py',
    'src/acfqp/science/controlled_predictive_causal_audit_v67.py',
    'src/acfqp/science/controlled_predictive_quotient_v1.py',
    'src/acfqp/science/controlled_predictive_2048_v1.py',
    'src/acfqp/science/controlled_predictive_cohort_v7.py',
    'src/acfqp/science/controlled_predictive_comparison_v2.py',
    'src/acfqp/science/controlled_predictive_comparison_v3.py',
    'src/acfqp/domains/standard_2048.py']


def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')


def run_arm(case, variant, directory):
    tick = perf_counter(); gc.collect(); preparation = perf_counter()-tick
    started = perf_counter()
    try:
        build = build_model(case.board, case.horizon, variant, max_states=30000)
    except Exception as error:
        save(directory/f'{variant}.failure.json', dict(error=f'{type(error).__name__}: {error}',
            paid_wall_seconds=preparation+perf_counter()-started,
            partial_construction_counts=getattr(error,'counts',None)))
        raise
    tick = perf_counter(); compiled = compile_full_state(build.model); compilation = perf_counter()-tick
    solutions, planning_counts = {}, Counter()
    tick = perf_counter()
    for name, query in QUERIES.items():
        solutions[name] = plan(compiled, query)
        planning_counts.update(solutions[name].counts)
    planning_seconds = perf_counter()-tick
    tick = perf_counter()
    payload = model_payload(build, compiled)
    encoded = json.dumps(payload, separators=(',', ':'), allow_nan=False)+'\n'
    (directory/f'{variant}.model.json').write_text(encoded)
    serialization = perf_counter()-tick
    execution_seconds = perf_counter()-started
    tick = perf_counter(); gc.collect(); cleanup = perf_counter()-tick
    result = dict(variant=variant, rule=asdict(build.rule), construction_counts=build.counts,
        planning_counts=dict(planning_counts), queries=len(solutions), model_bytes=len(encoded.encode()),
        times=dict(prepare_gc_seconds=preparation, construction_seconds=build.elapsed_seconds,
            compilation_seconds=compilation, planning_seconds=planning_seconds,
            serialization_seconds=serialization, execution_seconds=execution_seconds,
            cleanup_gc_seconds=cleanup, total_seconds=preparation+execution_seconds+cleanup))
    save(directory/f'{variant}.costs.json', result)
    return build, compiled, solutions, result


def portable_check(directory, queries_path, expected, expected_index):
    started = perf_counter()
    command = [sys.executable, str(ROOT/'scripts/query_controlled_predictive_contract_v67.py'),
        '--model', str(directory/'CONTRACT.model.json'), '--queries', str(queries_path),
        '--output', str(directory/'portable_queries.json')]
    with (directory/'portable.stdout.log').open('x') as out, (directory/'portable.stderr.log').open('x') as err:
        process = subprocess.run(command, stdout=out, stderr=err)
    command_seconds = perf_counter()-started
    if process.returncode:
        return dict(passed=False, exit_code=process.returncode, command_wall_seconds=command_seconds)
    result = json.loads((directory/'portable_queries.json').read_text())
    routing_matches=result['routing_index']==json.loads(json.dumps(
        [[key,cell] for key,cell in sorted(expected_index.items(),key=lambda item:item[1])]))
    mismatches = []
    planning, prediction = Counter(), Counter()
    for name, solution in expected.items():
        row = result['results'][name]
        if ({int(k):v for k,v in row['policy'].items()} != solution.policy
                or {int(k):v for k,v in row['values'].items()} != solution.values
                or row['planning_counts'] != solution.counts):
            mismatches.append(name)
        planning.update(row['planning_counts']); prediction.update(row['prediction']['counts'])
    return dict(passed=not mismatches and result['ground_domain_imports']==[] and routing_matches,
        routing_index_verified=routing_matches, routing_index_cells=result['routing_index_cells'],
        exit_code=process.returncode, mismatched_queries=mismatches,
        ground_domain_imports=result['ground_domain_imports'], command_wall_seconds=command_seconds,
        worker_wall_seconds_before_serialization=result['wall_seconds_before_serialization'],
        planning_counts=dict(planning), prediction_counts=dict(prediction),
        stderr_bytes=(directory/'portable.stderr.log').stat().st_size)


def run(output):
    started = perf_counter()
    output.mkdir(parents=True, exist_ok=False)
    cases = cases_v7()
    save(output/'queries.json', {name:asdict(query) for name,query in QUERIES.items()})
    manifest = dict(schema='acfqp.controlled_predictive_contract.v67', status='running',
        cases=[asdict(case) for case in cases], variants=VARIANTS, queries=len(QUERIES),
        max_states=30000, completed_cases=0, new_random_samples=0, learned_updates=0,
        runtime=dict(python=platform.python_version(), executable=sys.executable, gc_enabled=gc.isenabled()))
    for relative in SOURCES:
        target=output/'source'/relative; target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(ROOT/relative,target)
    results=[]
    save(output/'manifest.json',manifest)
    try:
        with (output/'cases.jsonl').open('x') as handle:
            for index,case in enumerate(cases):
                case_started=perf_counter()
                directory=output/case.name; directory.mkdir()
                order=VARIANTS[index%3:]+VARIANTS[:index%3]
                built={variant:run_arm(case,variant,directory) for variant in order}
                # All three symbolic models and every policy are now frozen.
                closure=build_development_closure(horizon=case.horizon,max_nodes=30000,boards={case.name:case.board})
                reference=compute_reference(closure,QUERIES)
                tick=perf_counter(); quotient=build_quotient(closure.model); quotient_seconds=perf_counter()-tick
                oracle=dict(active_cells=sum(c.terminal=='ACTIVE' for c in quotient.cells.values()),
                    action_rows=len(quotient.rows), successor_entries=sum(len(row) for row in quotient.rows.values()),
                    construction_seconds=quotient_seconds)
                arms={}
                for variant in VARIANTS:
                    build,compiled,solutions,result=built[variant]
                    result['audit']=audit_build(build,closure,QUERIES,solutions,reference,compiled)
                    arms[variant]=result
                portable=portable_check(directory,output/'queries.json',built['CONTRACT'][2],
                    {key:built['CONTRACT'][1].state_to_cell[state]
                     for key,state in built['CONTRACT'][0].state_index.items()})
                record=dict(case=asdict(case),order=order,arms=arms,portable=portable,
                    independent_ground=dict(construction_counts=closure.counts,
                        construction_seconds=closure.elapsed_seconds,reference_counts=reference.counts,
                        reference_seconds=reference.elapsed_seconds,reference_quotient=oracle),
                    case_wall_seconds_before_serialization=perf_counter()-case_started)
                results.append(record)
                handle.write(json.dumps(record,allow_nan=False)+'\n'); handle.flush()
                manifest['completed_cases']=len(results)
                manifest['whole_runner_seconds']=perf_counter()-started
                save(output/'manifest.json',manifest)
                print(json.dumps(dict(case=case.name,completed_cases=len(results),
                    active_states={v:arms[v]['construction_counts']['active_states'] for v in VARIANTS},
                    contract_states=arms['CONTRACT']['construction_counts'].get('contract_states',0),portable=portable['passed'])),flush=True)
                del built,closure,reference,quotient,build,compiled,solutions
        manifest['status']='complete'
    except Exception as error:
        manifest.update(status='failed',error=f'{type(error).__name__}: {error}')
        raise
    finally:
        manifest.update(whole_runner_seconds=perf_counter()-started,
            process_peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
        save(output/'manifest.json',manifest)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'reports/controlled_predictive_contract_v67')
    run(parser.parse_args().output)
