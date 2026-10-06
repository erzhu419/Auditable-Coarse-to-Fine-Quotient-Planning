"""Diagnose arbitrary shared feature potentials on retained V180 problems."""
import argparse
from collections import Counter
from copy import deepcopy
import importlib
import json
from pathlib import Path
import shutil
import sys
from time import perf_counter

import numpy as np
import scipy
import sympy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT/'src'))
from acfqp.science import controlled_predictive_shared_feature_capacity_v181 as core

SOURCE = ROOT/'reports/controlled_predictive_ranking_capacity_v180'
RUNTIME = ROOT/'reports/v181_runtime_tmp'
OUTPUT = ROOT/'reports/controlled_predictive_shared_feature_capacity_v181'


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')


def feature_coverage(problems):
    source = {tuple(row['features']) for row in problems['SOURCE']['vertices']}
    target = {tuple(row['features']) for row in problems['TARGET']['vertices']}
    records, work = [], Counter()
    work['vertex_feature_value_reads'] = 6*(len(source)+len(target))
    for root in problems['TARGET']['roots']:
        features = sorted({tuple(row['features']) for row in root['classes']})
        unseen = [list(feature) for feature in features if feature not in source]
        work.update(target_class_feature_value_reads=6*len(features), source_membership_tests=len(features))
        records.append(dict(root_id=root['root_id'], distinct_tuples=len(features),
            unseen_tuples=unseen, all_tuples_seen=not unseen))
    return dict(source_vertices=len(source), target_vertices=len(target), common_vertices=len(source & target),
        target_only_tuples=[list(feature) for feature in sorted(target-source)],
        target_roots_all_tuples_seen=sum(row['all_tuples_seen'] for row in records),
        target_root_records=records, work=dict(work))


def summarize(problems, capacities, coverage, inherited):
    return dict(schema='acfqp.shared_feature_capacity.v181.summary', complete=True,
        scopes={name: dict(roots=len(problems[name]['roots']), vertices=len(problems[name]['vertices']),
            capacity_status=capacities[name]['status'], upper_bound=capacities[name]['upper_bound'],
            witness=capacities[name]['witness'], weak_witness=capacities[name]['weak_witness'],
            costs=capacities[name]['costs']) for name in ('SOURCE', 'TARGET', 'JOINT')},
        feature_coverage=coverage, inherited_V180=deepcopy(inherited),
        new_environment_samples=0, new_source_games=0, new_native_weight_updates=0, new_predictors_fitted=0)


def capture_code(output):
    importlib.import_module('scripts.analyze_controlled_predictive_shared_feature_capacity_v181')
    paths = {Path(module.__file__).resolve() for module in list(sys.modules.values())
        if getattr(module, '__file__', None) and Path(module.__file__).suffix == '.py'
        and any(str(Path(module.__file__).resolve()).startswith(str(ROOT/folder)+'/')
            for folder in ('src', 'scripts'))}
    paths.update(ROOT/relative for relative in (
        'scripts/run_controlled_predictive_shared_feature_capacity_v181.py',
        'scripts/analyze_controlled_predictive_shared_feature_capacity_v181.py',
        'specs/SHARED_FEATURE_CAPACITY_V181.md',
        'tests/test_shared_feature_capacity_core_v181.py', 'tests/test_shared_feature_capacity_runner_v181.py',
        'tests/test_shared_feature_capacity_analysis_v181.py',
        'reports/v181_runtime_tmp/run_checks.py', 'reports/v181_runtime_tmp/run_stage.py'))
    for path in sorted(paths):
        destination = output/'source_code'/path.relative_to(ROOT)
        destination.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(path, destination)
    save(output/'source_manifest.json', dict(files=[str(path.relative_to(ROOT)) for path in sorted(paths)]))


def run(output=OUTPUT):
    begun = perf_counter(); output.mkdir(parents=True, exist_ok=False)
    record = dict(schema='acfqp.shared_feature_capacity.v181.run', status='preparing', phase_history=[], costs={},
        runtime=dict(python=sys.version.split()[0], executable=sys.executable,
            numpy=np.__version__, scipy=scipy.__version__, sympy=sympy.__version__),
        new_environment_samples=0, new_source_games=0, new_native_weight_updates=0, new_predictors_fitted=0,
        inherited_cost_refs=[dict(path=str(SOURCE/'run.json'), fields=['costs', 'inherited_cost_refs']),
            dict(path=str(SOURCE/'analysis.json'), fields=['costs']),
            dict(path=str(ROOT/'reports/v180_runtime_tmp/stage_checks.json'), fields=['attempts']),
            *[dict(path=str(ROOT/f'reports/v180_runtime_tmp/{kind}_checks.json'), fields=['attempts'])
                for kind in ('core', 'runner', 'analyzer')]],
        test_refs=[str(RUNTIME/f'{kind}_checks.json') for kind in ('core', 'runner', 'analyzer')])
    inputs, work = [], Counter()
    def read(path, name):
        raw = path.read_bytes(); target = output/'inputs'/'inherited'/name
        target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(raw)
        work.update(json_read_operations=1, input_bytes_read=len(raw))
        inputs.append(dict(path=str(path), saved_ref=str(target.relative_to(output)), bytes=len(raw), phase=record['status']))
        save(output/'input_manifest.json', inputs); return json.loads(raw)
    def phase(name):
        record['status'] = name
        record['phase_history'].append(dict(phase=name, seconds_since_start=perf_counter()-begun,
            input_reads=work['json_read_operations']))
        save(output/'run.json', record); print(json.dumps(dict(event=name, seconds=perf_counter()-begun)), flush=True)
    try:
        capture_code(output)
        stage = read(ROOT/'reports/v180_runtime_tmp/stage_checks.json', 'stage_checks.json')
        inherited_run = read(SOURCE/'run.json', 'run.json')
        if not stage['valid'] or inherited_run['status'] != 'complete':
            raise ValueError('required inherited V180 stage is not complete and valid')
        old_problems = read(SOURCE/'problems.json', 'problems.json')
        inherited = read(SOURCE/'summary.json', 'summary.json')
        problems = {name: core.lift_problem(old_problems[name]) for name in ('SOURCE', 'TARGET', 'JOINT')}
        save(output/'problems.json', problems)
        record['costs']['lift_work'] = {name: problem['work'] for name, problem in problems.items()}
        coverage = feature_coverage(problems); save(output/'feature_coverage.json', coverage)
        record['costs']['coverage_work'] = coverage['work']; phase('problems_frozen')
        capacities = {}
        for name in ('SOURCE', 'TARGET', 'JOINT'):
            phase(name.lower()+'_capacity'); tick = perf_counter()
            capacities[name] = core.solve_capacity(problems[name])
            record['costs'][name] = dict(counts=capacities[name]['costs'], seconds=perf_counter()-tick)
            save(output/'capacities.json', capacities); save(output/'run.json', record)
        save(output/'summary.json', summarize(problems, capacities, coverage, inherited))
        record['costs']['input_counts'] = dict(work); record['seconds'] = perf_counter()-begun
        phase('complete'); save(output/'run.json', record)
        print(json.dumps({name: value['status'] for name, value in capacities.items()}), flush=True)
        return record
    except Exception as error:
        failure = dict(type=type(error).__name__, message=str(error))
        if hasattr(error, 'record'):
            save(output/'failed_capacity.json', error.record); failure['paid_record_ref'] = 'failed_capacity.json'
        record.update(status='failed', seconds=perf_counter()-begun, failure=failure)
        record['costs']['input_counts'] = dict(work); save(output/'run.json', record); raise


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--output', type=Path, default=OUTPUT)
    args = parser.parse_args(); run(args.output)


if __name__ == '__main__':
    main()
