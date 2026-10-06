"""Select capacity control on held-out SOURCE groups, then freeze TARGET choices."""
import argparse
from collections import Counter
from copy import deepcopy
import importlib
import json
from pathlib import Path
import shutil
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT/'src'))
from acfqp.science import controlled_predictive_source_regularization_v183 as core
from scripts import run_controlled_predictive_exact_h3_v177 as statistics
from scripts.run_controlled_predictive_shared_consequences_v179 import paired_contrast
from scripts.run_controlled_predictive_rank_layout_consequences_v182 import feature_coverage

SOURCE = ROOT/'reports/controlled_predictive_rank_layout_consequences_v182'
RUNTIME = ROOT/'reports/v183_runtime_tmp'
OUTPUT = ROOT/'reports/controlled_predictive_source_regularization_v183'


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')


def ridge_choices(roots, model, inherited):
    choices, work = {}, Counter()
    for cohort in ('SOURCE', 'TARGET'):
        rows = []
        for root in roots[cohort]:
            decision = core.choose_action(model, root)
            work.update(decision['work']); work.update(decision['feature_work'])
            rows.append(dict(root_id=root['root_id'], mode='TREE',
                canonical_action=decision['canonical_action'], actual_action=decision['actual_action'],
                fallback=decision['fallback'], decision=decision))
        rows.extend(deepcopy(row) for row in inherited[cohort] if row['mode'] in ('ONE', 'FALLBACK'))
        choices[cohort] = rows
    return choices, dict(work)


def summarize(roots, labels, choices, selection):
    summaries = {}
    for name in ('RIDGE', 'LAYOUT', 'SHARED', 'RAW'):
        item = statistics.summarize(roots, labels, choices[name],
            {'TREE': dict(nodes=[], candidate_records=[])})
        item.pop('learned_splits'); item.pop('candidate_reasons')
        item['model_kind'] = name; summaries[name] = item
    return dict(schema='acfqp.source_regularization.v183.summary', complete=True,
        selected_lambda=selection['selected_lambda'],
        source_selection=[dict(lambda_value=row['lambda_value'], utility=row['utility'],
            group_records=deepcopy(row['group_records'])) for row in selection['candidates']],
        RIDGE=summaries['RIDGE'],
        ridge_minus_layout=paired_contrast(roots, summaries['RIDGE'], summaries['LAYOUT']),
        ridge_minus_shared=paired_contrast(roots, summaries['RIDGE'], summaries['SHARED']),
        ridge_minus_raw=paired_contrast(roots, summaries['RIDGE'], summaries['RAW']),
        feature_coverage=feature_coverage(choices['RIDGE']),
        new_environment_samples=0, new_source_games=0, new_native_weight_updates=0,
        new_predictors_fitted=13)


def capture_code(output):
    importlib.import_module('scripts.analyze_controlled_predictive_source_regularization_v183')
    paths = {Path(module.__file__).resolve() for module in list(sys.modules.values())
        if getattr(module, '__file__', None) and Path(module.__file__).suffix == '.py'
        and any(str(Path(module.__file__).resolve()).startswith(str(ROOT/folder)+'/')
            for folder in ('src', 'scripts'))}
    paths.update(ROOT/relative for relative in (
        'scripts/run_controlled_predictive_source_regularization_v183.py',
        'scripts/analyze_controlled_predictive_source_regularization_v183.py',
        'specs/SOURCE_REGULARIZATION_V183.md',
        'tests/test_source_regularization_core_v183.py',
        'tests/test_source_regularization_runner_v183.py',
        'tests/test_source_regularization_analysis_v183.py',
        'reports/v183_runtime_tmp/run_checks.py', 'reports/v183_runtime_tmp/run_stage.py'))
    for path in sorted(paths):
        target = output/'source_code'/path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(path, target)
    save(output/'source_manifest.json', dict(files=[str(path.relative_to(ROOT)) for path in sorted(paths)]))


def run(output=OUTPUT):
    begun = perf_counter(); output.mkdir(parents=True, exist_ok=False)
    record = dict(schema='acfqp.source_regularization.v183.run', status='preparing', phase_history=[],
        runtime=dict(python=sys.version.split()[0], executable=sys.executable), costs={},
        new_environment_samples=0, new_source_games=0, new_native_weight_updates=0,
        new_features_computed=0, new_predictors_fitted=0,
        inherited_cost_refs=[dict(path=str(SOURCE/'run.json'), fields=['costs', 'inherited_cost_refs']),
            dict(path=str(SOURCE/'analysis.json'), fields=['costs']),
            dict(path=str(ROOT/'reports/v182_runtime_tmp/stage_checks.json'), fields=['attempts']),
            *[dict(path=str(ROOT/f'reports/v182_runtime_tmp/{kind}_checks.json'), fields=['attempts'])
                for kind in ('core', 'runner', 'analyzer')]],
        test_refs=[str(RUNTIME/f'{kind}_checks.json') for kind in ('core', 'runner', 'analyzer')])
    inputs, work = [], Counter()
    def read(path, name):
        raw = path.read_bytes(); target = output/'inputs'/'inherited'/name
        target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(raw)
        work.update(json_read_operations=1, input_bytes_read=len(raw))
        inputs.append(dict(path=str(path), saved_ref=str(target.relative_to(output)),
            bytes=len(raw), phase=record['status']))
        save(output/'input_manifest.json', inputs); return json.loads(raw)
    def phase(name):
        record['status'] = name
        record['phase_history'].append(dict(phase=name, seconds_since_start=perf_counter()-begun,
            input_reads=work['json_read_operations']))
        save(output/'run.json', record)
        print(json.dumps(dict(event=name, seconds=perf_counter()-begun)), flush=True)
    try:
        capture_code(output)
        stage = read(ROOT/'reports/v182_runtime_tmp/stage_checks.json', 'stage_checks.json')
        inherited_run = read(SOURCE/'run.json', 'run.json')
        if not stage['valid'] or inherited_run['status'] != 'complete':
            raise ValueError('settled V182 stage is incomplete')
        roots = read(SOURCE/'roots.json', 'roots.json')
        old_choices = read(SOURCE/'choices.json', 'choices.json')
        source_labels = read(SOURCE/'inputs/inherited/source_labels.json', 'source_labels.json')
        features = {root['root_id']: root['layout_features'] for root in roots['SOURCE']}
        examples = [dict(deepcopy(row), layout_features=deepcopy(features[row['root_id']]))
            for row in source_labels]
        phase('source_selection'); tick = perf_counter()
        selection = core.select_regularization(examples, 0)
        model = selection.pop('model')
        record['new_predictors_fitted'] = 13
        record['costs']['selection_and_final_fit'] = dict(seconds=perf_counter()-tick,
            counts=selection['costs'])
        save(output/'selection.json', selection); save(output/'models.json', dict(RIDGE=model))
        phase('models_frozen')
        tick = perf_counter(); new_choices, choice_work = ridge_choices(roots, model, old_choices['RAW'])
        record['costs']['choice_counts'] = choice_work
        record['costs']['choice_seconds'] = perf_counter()-tick
        choices = dict(deepcopy(old_choices), RIDGE=new_choices)
        save(output/'choices.json', choices); phase('target_choices_frozen'); phase('target_labels')
        labels = read(SOURCE/'labels.json', 'labels.json')
        if labels['SOURCE'] != source_labels:
            raise ValueError('SOURCE labels differ from retained standalone copy')
        save(output/'labels.json', labels); summary = summarize(roots, labels, choices, selection)
        save(output/'summary.json', summary); record['costs']['input_counts'] = dict(work)
        record['seconds'] = perf_counter()-begun; phase('complete'); save(output/'run.json', record)
        print(json.dumps(summary['RIDGE']['cohorts']['TARGET']['aggregates']['ROOT_MEAN']), flush=True)
        return record
    except Exception as error:
        record.update(status='failed', seconds=perf_counter()-begun,
            failure=dict(type=type(error).__name__, message=str(error)))
        if hasattr(error, 'record'):
            save(output/'failed_selection.json', error.record)
            record['costs']['failed_selection'] = error.record.get('costs', {})
        record['costs']['input_counts'] = dict(work); save(output/'run.json', record); raise


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--output', type=Path, default=OUTPUT)
    args = parser.parse_args(); run(args.output)


if __name__ == '__main__':
    main()
