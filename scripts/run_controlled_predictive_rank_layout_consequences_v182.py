"""Learn one rank/layout-conditioned complete-vector model from SOURCE only."""
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
from acfqp.science import controlled_predictive_rank_layout_consequences_v182 as core
from scripts import run_controlled_predictive_exact_h3_v177 as statistics
from scripts.run_controlled_predictive_shared_consequences_v179 import paired_contrast

SOURCE = ROOT/'reports/controlled_predictive_shared_consequences_v179'
RUNTIME = ROOT/'reports/v182_runtime_tmp'
OUTPUT = ROOT/'reports/controlled_predictive_rank_layout_consequences_v182'


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')


def layout_choices(roots, model, inherited):
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


def feature_coverage(choices):
    cohorts = {}
    for cohort in ('SOURCE', 'TARGET'):
        records = []
        for row in choices[cohort]:
            if row['mode'] != 'TREE':
                continue
            actions = deepcopy(row['decision']['coverage'])
            records.append(dict(root_id=row['root_id'], actions=actions,
                all_tokens_seen=all(item['unknown_tokens'] == 0 for item in actions.values())))
        action_records = [item for row in records for item in row['actions'].values()]
        cohorts[cohort] = dict(roots=len(records), actions=len(action_records),
            total_tokens=sum(item['total_tokens'] for item in action_records),
            known_tokens=sum(item['known_tokens'] for item in action_records),
            unknown_tokens=sum(item['unknown_tokens'] for item in action_records),
            roots_all_tokens_seen=sum(row['all_tokens_seen'] for row in records), root_records=records)
    return cohorts


def summarize(roots, labels, choices):
    summaries = {}
    for name in ('LAYOUT', 'SHARED', 'RAW', 'STRUCTURE'):
        summary = statistics.summarize(roots, labels, choices[name],
            {'TREE': dict(nodes=[], candidate_records=[])})
        summary.pop('learned_splits'); summary.pop('candidate_reasons')
        summary['model_kind'] = name; summaries[name] = summary
    return dict(schema='acfqp.rank_layout_consequences.v182.summary', complete=True,
        LAYOUT=summaries['LAYOUT'],
        layout_minus_shared=paired_contrast(roots, summaries['LAYOUT'], summaries['SHARED']),
        layout_minus_raw=paired_contrast(roots, summaries['LAYOUT'], summaries['RAW']),
        layout_minus_structure=paired_contrast(roots, summaries['LAYOUT'], summaries['STRUCTURE']),
        feature_coverage=feature_coverage(choices['LAYOUT']),
        new_environment_samples=0, new_source_games=0, new_native_weight_updates=0,
        new_predictors_fitted=1)


def capture_code(output):
    importlib.import_module('scripts.analyze_controlled_predictive_rank_layout_consequences_v182')
    paths = {Path(module.__file__).resolve() for module in list(sys.modules.values())
        if getattr(module, '__file__', None) and Path(module.__file__).suffix == '.py'
        and any(str(Path(module.__file__).resolve()).startswith(str(ROOT/folder)+'/')
            for folder in ('src', 'scripts'))}
    paths.update(ROOT/relative for relative in (
        'scripts/run_controlled_predictive_rank_layout_consequences_v182.py',
        'scripts/analyze_controlled_predictive_rank_layout_consequences_v182.py',
        'specs/RANK_LAYOUT_CONSEQUENCES_V182.md',
        'tests/test_rank_layout_consequences_core_v182.py',
        'tests/test_rank_layout_consequences_runner_v182.py',
        'tests/test_rank_layout_consequences_analysis_v182.py',
        'reports/v182_runtime_tmp/run_checks.py', 'reports/v182_runtime_tmp/run_stage.py'))
    for path in sorted(paths):
        target = output/'source_code'/path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(path, target)
    save(output/'source_manifest.json', dict(files=[str(path.relative_to(ROOT)) for path in sorted(paths)]))


def run(output=OUTPUT):
    begun = perf_counter(); output.mkdir(parents=True, exist_ok=False)
    record = dict(schema='acfqp.rank_layout_consequences.v182.run', status='preparing', phase_history=[],
        runtime=dict(python=sys.version.split()[0], executable=sys.executable), costs={},
        new_environment_samples=0, new_source_games=0, new_native_weight_updates=0,
        new_fit_attempts=0, new_predictors_fitted=0,
        inherited_cost_refs=[
            dict(path=str(SOURCE/'run.json'), fields=['costs', 'inherited_cost_refs']),
            dict(path=str(SOURCE/'analysis.json'), fields=['costs']),
            dict(path=str(ROOT/'reports/v179_runtime_tmp/stage_checks.json'), fields=['attempts']),
            dict(path=str(ROOT/'reports/controlled_predictive_shared_feature_capacity_v181/run.json'), fields=['costs']),
            dict(path=str(ROOT/'reports/controlled_predictive_shared_feature_capacity_v181/analysis.json'), fields=['costs']),
            dict(path=str(ROOT/'reports/v181_runtime_tmp/stage_checks.json'), fields=['attempts'])],
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
        capacity_stage = read(ROOT/'reports/v181_runtime_tmp/stage_checks.json', 'v181_stage_checks.json')
        stage = read(ROOT/'reports/v179_runtime_tmp/stage_checks.json', 'stage_checks.json')
        if not capacity_stage['valid'] or not stage['valid']:
            raise ValueError('required settled V181/V179 stage is not valid')
        inherited_run = read(SOURCE/'run.json', 'run.json')
        if inherited_run['status'] != 'complete':
            raise ValueError('inherited complete-vector experiment is incomplete')
        roots = read(SOURCE/'roots.json', 'roots.json')
        old_models = read(SOURCE/'models.json', 'models.json')
        old_choices = read(SOURCE/'choices.json', 'choices.json')
        source_labels = read(SOURCE/'inputs/inherited/source_labels.json', 'source_labels.json')
        feature_work = Counter(); tick = perf_counter()
        for cohort in ('SOURCE', 'TARGET'):
            for root in roots[cohort]:
                root['layout_features'] = core.action_features_from_root(root, feature_work)
        record['costs']['feature_construction'] = dict(counts=dict(feature_work), seconds=perf_counter()-tick)
        save(output/'roots.json', roots)
        features = {root['root_id']: root['layout_features'] for root in roots['SOURCE']}
        examples = [dict(deepcopy(row), layout_features=deepcopy(features[row['root_id']]))
            for row in source_labels]
        phase('source_fit'); tick = perf_counter(); record['new_fit_attempts'] = 1
        model = core.fit_model(examples, 0); record['new_predictors_fitted'] = 1
        record['costs']['learning'] = dict(seconds=perf_counter()-tick, fit_counts=model['fit_counts'],
            feature_counts=model['feature_counts'], encoder_counts=model['encoder_counts'])
        models = dict(deepcopy(old_models), LAYOUT=model)
        save(output/'models.json', models); phase('models_frozen')
        tick = perf_counter(); new_choices, choice_work = layout_choices(roots, model, old_choices['RAW'])
        record['costs']['choice_counts'] = choice_work
        record['costs']['choice_seconds'] = perf_counter()-tick
        choices = dict(deepcopy(old_choices), LAYOUT=new_choices)
        save(output/'choices.json', choices); phase('target_choices_frozen'); phase('target_labels')
        labels = read(SOURCE/'labels.json', 'labels.json')
        if labels['SOURCE'] != source_labels:
            raise ValueError('SOURCE labels differ from retained standalone copy')
        save(output/'labels.json', labels); summary = summarize(roots, labels, choices)
        save(output/'summary.json', summary); record['costs']['input_counts'] = dict(work)
        record['seconds'] = perf_counter()-begun; phase('complete'); save(output/'run.json', record)
        print(json.dumps(summary['LAYOUT']['cohorts']['TARGET']['aggregates']['ROOT_MEAN']), flush=True)
        return record
    except Exception as error:
        record.update(status='failed', seconds=perf_counter()-begun,
            failure=dict(type=type(error).__name__, message=str(error)))
        record['costs']['input_counts'] = dict(work); save(output/'run.json', record); raise


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--output', type=Path, default=OUTPUT)
    args = parser.parse_args(); run(args.output)


if __name__ == '__main__':
    main()
