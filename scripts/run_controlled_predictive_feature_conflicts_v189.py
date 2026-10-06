"""Diagnose retained V188 LINEAR errors without fitting or acquiring labels."""
import argparse
from collections import Counter
import importlib
import json
from pathlib import Path
import shutil
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT/'src'))
from acfqp.science import controlled_predictive_feature_conflicts_v189 as core
from acfqp.science import controlled_predictive_shared_feature_capacity_v181 as capacity_backend

PREVIOUS = ROOT/'reports/controlled_predictive_mechanism_interactions_v188'
OUTPUT = ROOT/'reports/controlled_predictive_feature_conflicts_v189'
RUNTIME = ROOT/'reports/v189_runtime_tmp'


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')


def capture_code(output):
    importlib.import_module('scripts.analyze_controlled_predictive_feature_conflicts_v189')
    paths = {Path(module.__file__).resolve() for module in list(sys.modules.values())
        if getattr(module, '__file__', None) and Path(module.__file__).suffix == '.py'
        and any(str(Path(module.__file__).resolve()).startswith(str(ROOT/folder)+'/')
            for folder in ('src', 'scripts'))}
    paths.update(ROOT/relative for relative in (
        'scripts/run_controlled_predictive_feature_conflicts_v189.py',
        'scripts/analyze_controlled_predictive_feature_conflicts_v189.py',
        'specs/FEATURE_CONFLICTS_V189.md', 'tests/test_feature_conflicts_core_v189.py',
        'tests/test_feature_conflicts_runner_v189.py', 'tests/test_feature_conflicts_analysis_v189.py',
        'reports/v189_runtime_tmp/run_checks.py', 'reports/v189_runtime_tmp/run_stage.py'))
    for path in sorted(paths):
        target = output/'source_code'/path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(path, target)
    save(output/'source_manifest.json', dict(files=[str(path.relative_to(ROOT)) for path in sorted(paths)]))


def run(output=OUTPUT):
    begun = perf_counter(); output.mkdir(parents=True, exist_ok=False)
    record = dict(schema='acfqp.feature_conflicts.v189.run', status='preparing', phase_history=[], costs={},
        runtime=dict(python=sys.version.split()[0], executable=sys.executable),
        new_environment_samples=0, new_source_games=0, new_native_weight_updates=0, new_predictors_fitted=0,
        new_reference_kernels=0, new_exact_label_roots=0,
        new_capacity_attempts=0, new_capacity_scopes=0, new_lp_solves=0,
        inherited_cost_refs=[dict(path=str(PREVIOUS/'run.json'), fields=['costs', 'inherited_cost_refs']),
            dict(path=str(PREVIOUS/'analysis.json'), fields=['costs'])],
        test_refs=[str(RUNTIME/f'{kind}_checks.json') for kind in ('core', 'runner', 'analyzer')])
    inputs, input_work = [], Counter()
    def phase(name):
        record['status'] = name
        record['phase_history'].append(dict(phase=name, seconds_since_start=perf_counter()-begun,
            input_reads=input_work['json_read_operations']))
        save(output/'run.json', record)
        print(json.dumps(dict(event=name, seconds=perf_counter()-begun)), flush=True)
    def read(path, name):
        raw = path.read_bytes(); target = output/'inputs/inherited'/name
        target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(raw)
        input_work.update(json_read_operations=1, input_bytes_read=len(raw), input_bytes_retained=len(raw))
        inputs.append(dict(path=str(path), saved_ref=str(target.relative_to(output)), bytes=len(raw), phase=record['status']))
        save(output/'input_manifest.json', inputs); return json.loads(raw)
    try:
        capture_code(output); phase('protocol_frozen')
        stage = read(ROOT/'reports/v188_runtime_tmp/stage_checks.json', 'stage_checks.json')
        prior = read(PREVIOUS/'run.json', 'run.json')
        if not stage['valid'] or prior['status'] != 'complete':
            raise ValueError('settled V188 stage is incomplete')
        roots = read(PREVIOUS/'roots.json', 'roots.json')
        labels = read(PREVIOUS/'labels.json', 'labels.json')
        inherited = read(PREVIOUS/'summary.json', 'summary.json')
        if len(roots['SOURCE']) != 143 or len(roots['TARGET']) != 96 or len(labels) != 96:
            raise ValueError('fixed SOURCE143/TARGET96 differs')
        phase('retained_inputs'); tick = perf_counter()
        diagnostics = core.build_diagnostics(roots, labels, inherited)
        record['costs']['diagnostics'] = dict(seconds=perf_counter()-tick, counts=diagnostics['costs'])
        save(output/'diagnostics.json', diagnostics); phase('diagnostics_frozen')
        phase('target_capacity'); tick = perf_counter(); record['new_capacity_attempts'] += 1
        capacity = capacity_backend.solve_capacity(diagnostics['problem'])
        record['new_capacity_scopes'] += 1; record['new_lp_solves'] = capacity['costs']['lp_solves']
        record['costs']['target_capacity'] = dict(seconds=perf_counter()-tick, counts=capacity['costs'])
        save(output/'capacity.json', capacity)
        tick = perf_counter(); summary = core.summarize(diagnostics, capacity)
        record['costs']['summary'] = dict(seconds=perf_counter()-tick, counts=summary['work'])
        save(output/'summary.json', summary)
        record['costs']['input_counts'] = dict(input_work); record['seconds'] = perf_counter()-begun
        phase('complete'); save(output/'run.json', record); return record
    except Exception as error:
        record.update(status='failed', seconds=perf_counter()-begun,
            failure=dict(type=type(error).__name__, message=str(error)))
        if hasattr(error, 'record'):
            save(output/'failed_capacity.json', error.record)
            record['costs']['failed_capacity'] = error.record.get('costs', {})
            record['new_lp_solves'] = record['costs']['failed_capacity'].get('lp_solves', 0)
        record['costs']['input_counts'] = dict(input_work); save(output/'run.json', record); raise


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--output', type=Path, default=OUTPUT)
    run(parser.parse_args().output)


if __name__ == '__main__':
    main()
