"""Diagnose the retained V192 nonlinear scorer without fitting or acquisition."""
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
from acfqp.science import controlled_predictive_kernel_transfer_v193 as core

PREVIOUS = ROOT/'reports/controlled_predictive_nonlinear_relations_v192'
OUTPUT = ROOT/'reports/controlled_predictive_kernel_transfer_v193'
RUNTIME = ROOT/'reports/v193_runtime_tmp'


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')


def capture_code(output):
    importlib.import_module('scripts.analyze_controlled_predictive_kernel_transfer_v193')
    paths = {Path(module.__file__).resolve() for module in list(sys.modules.values())
        if getattr(module, '__file__', None) and Path(module.__file__).suffix == '.py'
        and any(str(Path(module.__file__).resolve()).startswith(str(ROOT/folder)+'/')
                for folder in ('src', 'scripts'))}
    paths.update(ROOT/relative for relative in ('scripts/run_controlled_predictive_kernel_transfer_v193.py',
        'scripts/analyze_controlled_predictive_kernel_transfer_v193.py', 'specs/KERNEL_TRANSFER_V193.md',
        'tests/test_kernel_transfer_core_v193.py', 'tests/test_kernel_transfer_runner_v193.py',
        'tests/test_kernel_transfer_analysis_v193.py', 'reports/v193_runtime_tmp/run_checks.py',
        'reports/v193_runtime_tmp/run_stage.py'))
    for path in sorted(paths):
        target = output/'source_code'/path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(path, target)
    save(output/'source_manifest.json', dict(files=[str(path.relative_to(ROOT)) for path in sorted(paths)]))


def run(output=OUTPUT):
    begun = perf_counter(); output.mkdir(parents=True, exist_ok=False)
    record = dict(schema='acfqp.kernel_transfer.v193.run', status='preparing', phase_history=[], costs={},
        runtime=dict(python=sys.version.split()[0], executable=sys.executable), diagnostic_attempts=0,
        diagnostic_complete=False, new_predictors_fitted=0, new_solve_attempts=0,
        new_eigen_decompositions=0, new_svd_decompositions=0, new_feature_derivations=0,
        new_source_games=0, new_boards_generated=0, new_reference_kernels=0,
        new_exact_label_roots=0, new_environment_samples=0, new_native_weight_updates=0,
        inherited_cost_refs=[dict(path=str(PREVIOUS/'run.json'), fields=['costs', 'inherited_cost_refs']),
            dict(path=str(PREVIOUS/'analysis.json'), fields=['costs'])],
        test_refs=[str(RUNTIME/f'{kind}_checks.json') for kind in ('core', 'runner', 'analyzer')])
    inputs, input_work, diagnostic_started = [], Counter(), None
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
        stage = read(ROOT/'reports/v192_runtime_tmp/corrected_stage_checks.json', 'v192_stage_checks.json')
        prior = read(PREVIOUS/'run.json', 'run.json')
        if not stage['valid'] or prior['status'] != 'complete':
            raise ValueError('settled corrected V192 stage is incomplete')
        model = read(PREVIOUS/'model.json', 'model.json')
        roots = read(PREVIOUS/'roots.json', 'roots.json')
        choices = read(PREVIOUS/'choices.json', 'choices.json')
        labels = read(PREVIOUS/'labels.json', 'labels.json')
        inherited = read(PREVIOUS/'summary.json', 'summary.json')
        source_diagnostics = read(PREVIOUS/'source_diagnostics.json', 'source_diagnostics.json')
        if (len(roots['SOURCE']) != 143 or len({row['source_id'] for row in roots['SOURCE']}) != 36
                or len(roots['TARGET']) != 96 or len(labels) != 96):
            raise ValueError('fixed SOURCE143/36 and retained TARGET96 differ')
        phase('inputs_retained'); diagnostic_started = perf_counter(); record['diagnostic_attempts'] += 1
        save(output/'run.json', record)
        diagnostics = core.diagnose(model, roots, choices, labels, inherited, source_diagnostics)
        record['costs']['diagnostics'] = dict(seconds=perf_counter()-diagnostic_started, counts=diagnostics['costs'])
        record['diagnostic_complete'] = diagnostics['complete']
        save(output/'diagnostics.json', diagnostics); save(output/'reference.json', diagnostics['reference'])
        save(output/'summary.json', diagnostics['summary'])
        # These are retention milestones after the single call, not internal timer boundaries.
        phase('source_reference'); phase('target_diagnostics')
        record['costs']['input_counts'] = dict(input_work); record['seconds'] = perf_counter()-begun
        phase('complete'); save(output/'run.json', record); return record
    except Exception as error:
        record.update(status='failed', seconds=perf_counter()-begun,
            failure=dict(type=type(error).__name__, message=str(error)))
        if record['diagnostic_attempts'] and 'diagnostics' not in record['costs']:
            failed = getattr(error, 'record', None)
            counts = failed.get('costs', {}) if failed is not None else getattr(error, 'counts', {})
            record['costs']['failed_diagnostics'] = dict(seconds=perf_counter()-diagnostic_started, counts=counts)
            if failed is not None:
                save(output/'failed_diagnostics.json', failed)
        record['costs']['input_counts'] = dict(input_work); save(output/'run.json', record); raise


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--output', type=Path, default=OUTPUT)
    run(parser.parse_args().output)


if __name__ == '__main__':
    main()
