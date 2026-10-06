"""Fit one action-structure partition on retained V177 exact labels."""
import argparse
from collections import Counter, defaultdict
from copy import deepcopy
import importlib
import json
from pathlib import Path
import shutil
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT/'src'))
from acfqp.science import controlled_predictive_afterstate_structure_v178 as core
from scripts import run_controlled_predictive_exact_h3_v177 as prior

SOURCE = ROOT/'reports/controlled_predictive_exact_h3_v177'
RUNTIME = ROOT/'reports/v178_runtime_tmp'
OUTPUT = ROOT/'reports/controlled_predictive_afterstate_structure_v178'
EPSILON = 1e-12


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')


def structure_choices(roots, model, inherited):
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


def summarize(roots, labels, choices, models):
    summaries = {name: prior.summarize(roots, labels, choices[name], {'TREE': models[name]})
        for name in ('STRUCTURE', 'RAW')}
    contrasts = {}
    for cohort in ('SOURCE', 'TARGET'):
        by_model = {name: {row['root_id']: row for row in summaries[name]['cohorts'][cohort]['root_records']}
            for name in summaries}
        records, groups = [], defaultdict(list)
        for root in roots[cohort]:
            a, b = [by_model[name][root['root_id']]['modes']['TREE'] for name in ('STRUCTURE', 'RAW')]
            vector = [a['components'][k]-b['components'][k] for k in range(3)]
            row = dict(root_id=root['root_id'], source_id=root['source_id'], components=vector,
                utility=prior.utility(vector), structure_action=a['action'], raw_action=b['action'],
                structure_regret=a['regret'], raw_regret=b['regret'])
            records.append(row); groups[root['source_id']].append(vector)
        group_rows = [dict(source_id=group, roots=len(vectors), components=prior.mean_vectors(vectors),
            utility=prior.utility(prior.mean_vectors(vectors))) for group, vectors in sorted(groups.items())]
        aggregates = {}
        for weighting in ('ROOT_MEAN', 'DESIGN_GROUP_MEAN'):
            rows = records if weighting == 'ROOT_MEAN' else group_rows
            vector = prior.mean_vectors([row['components'] for row in rows])
            aggregates[weighting] = dict(components=vector, utility=prior.utility(vector))
        contrasts[cohort] = dict(roots=len(records), primary_weighting=(
            'DESIGN_GROUP_MEAN' if cohort == 'SOURCE' else 'ROOT_MEAN'), aggregates=aggregates,
            diagnostics=dict(improved_roots=sum(row['utility'] > EPSILON for row in records),
                worsened_roots=sum(row['utility'] < -EPSILON for row in records),
                equal_value_roots=sum(abs(row['utility']) <= EPSILON for row in records),
                action_changes=sum(row['structure_action'] != row['raw_action'] for row in records),
                new_positive_regret_roots=sum(row['raw_regret'] <= EPSILON < row['structure_regret'] for row in records),
                resolved_positive_regret_roots=sum(row['structure_regret'] <= EPSILON < row['raw_regret'] for row in records)),
            groups=group_rows, root_records=records)
    return dict(schema='acfqp.afterstate_structure.v178.summary', complete=True, **summaries,
        structure_minus_raw=contrasts, new_environment_samples=0, new_source_games=0, new_native_weight_updates=0)


def capture_code(output):
    importlib.import_module('scripts.analyze_controlled_predictive_afterstate_structure_v178')
    paths = {Path(module.__file__).resolve() for module in list(sys.modules.values())
        if getattr(module, '__file__', None) and Path(module.__file__).suffix == '.py'
        and any(str(Path(module.__file__).resolve()).startswith(str(ROOT/folder)+'/')
            for folder in ('src', 'scripts'))}
    paths.update(ROOT/relative for relative in (
        'scripts/run_controlled_predictive_afterstate_structure_v178.py',
        'scripts/analyze_controlled_predictive_afterstate_structure_v178.py',
        'specs/AFTERSTATE_STRUCTURE_V178.md',
        'tests/test_afterstate_structure_core_v178.py', 'tests/test_afterstate_structure_runner_v178.py',
        'tests/test_afterstate_structure_analysis_v178.py',
        'reports/v178_runtime_tmp/run_checks.py', 'reports/v178_runtime_tmp/run_stage.py'))
    for path in sorted(paths):
        destination = output/'source_code'/path.relative_to(ROOT)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, destination)
    save(output/'source_manifest.json', dict(files=[str(path.relative_to(ROOT)) for path in sorted(paths)]))


def run(output=OUTPUT):
    begun = perf_counter(); output.mkdir(parents=True, exist_ok=False)
    record = dict(schema='acfqp.afterstate_structure.v178.run', status='preparing', phase_history=[],
        runtime=dict(python=sys.version.split()[0], executable=sys.executable),
        costs={}, new_environment_samples=0, new_source_games=0, new_native_weight_updates=0,
        inherited_cost_refs=[dict(path=str(SOURCE/'run.json'), fields=['costs', 'inherited_cost_refs']),
            dict(path=str(SOURCE/'analysis.json'), fields=['costs']),
            dict(path=str(ROOT/'reports/v177_runtime_tmp/stage_checks.json'), fields=['attempts']),
            *[dict(path=str(ROOT/f'reports/v177_runtime_tmp/{kind}_checks.json'), fields=['attempts'])
                for kind in ('core', 'runner', 'analyzer')]],
        test_refs=[str(RUNTIME/f'{kind}_checks.json') for kind in ('core', 'runner', 'analyzer')])
    inputs, work = [], Counter()
    def read(path, name):
        raw = path.read_bytes(); target = output/'inputs'/'inherited'/name
        target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(raw)
        work.update(json_read_operations=1, input_bytes_read=len(raw))
        inputs.append(dict(path=str(path), saved_ref=str(target.relative_to(output)),
            bytes=len(raw), phase=record['status']))
        save(output/'input_manifest.json', inputs)
        return json.loads(raw)
    def phase(name):
        record['status'] = name
        record['phase_history'].append(dict(phase=name, seconds_since_start=perf_counter()-begun,
            input_reads=work['json_read_operations']))
        save(output/'run.json', record)
        print(json.dumps(dict(event=name, seconds=perf_counter()-begun)), flush=True)
    try:
        capture_code(output)
        stage = read(ROOT/'reports/v177_runtime_tmp/stage_checks.json', 'stage_checks.json')
        if not stage['valid']:
            raise ValueError('required inherited V177 stage is not valid')
        inherited_run = read(SOURCE/'run.json', 'run.json')
        if inherited_run['status'] != 'complete':
            raise ValueError('inherited exact H3 run is incomplete')
        roots = read(SOURCE/'roots.json', 'roots.json')
        source_labels = read(SOURCE/'source_labels.json', 'source_labels.json')
        old_models = read(SOURCE/'models.json', 'models.json')
        old_choices = read(SOURCE/'choices.json', 'choices.json')
        feature_work = Counter(); tick = perf_counter()
        for cohort in ('SOURCE', 'TARGET'):
            for root in roots[cohort]:
                root['structural_features'] = core.feature_from_root(root, feature_work)
        record['costs']['feature_construction'] = dict(counts=dict(feature_work), seconds=perf_counter()-tick)
        save(output/'roots.json', roots)
        features = {root['root_id']: root['structural_features'] for cohort in ('SOURCE', 'TARGET') for root in roots[cohort]}
        examples = [dict(deepcopy(row), structural_features=features[row['root_id']]) for row in source_labels]
        phase('source_fit')
        tick = perf_counter(); structure = core.fit_partition(examples, 0)
        record['costs']['learning'] = dict(seconds=perf_counter()-tick, fit_counts=structure['fit_counts'],
            search_counts=structure['utility_search_counts'], node_fit_counts=structure['node_fit_counts'],
            feature_counts=structure['feature_counts'])
        models = dict(STRUCTURE=structure, RAW=old_models['TREE'], ONE=old_models['ONE'])
        save(output/'models.json', models)
        phase('models_frozen')
        structure_rows, decision_work = structure_choices(roots, structure, old_choices)
        record['costs']['choice_counts'] = decision_work
        choices = dict(STRUCTURE=structure_rows, RAW=old_choices)
        save(output/'choices.json', choices)
        phase('target_choices_frozen')
        phase('target_labels')
        labels = read(SOURCE/'labels.json', 'labels.json')
        if labels['SOURCE'] != source_labels:
            raise ValueError('source labels differ from their inherited standalone copy')
        save(output/'labels.json', labels)
        summary = summarize(roots, labels, choices, models)
        save(output/'summary.json', summary)
        record['costs']['input_counts'] = dict(work)
        record['seconds'] = perf_counter()-begun
        phase('complete')
        save(output/'run.json', record)
        print(json.dumps(summary['STRUCTURE']['cohorts']['TARGET']['aggregates']['ROOT_MEAN']), flush=True)
        return record
    except Exception as error:
        record.update(status='failed', seconds=perf_counter()-begun,
            failure=dict(type=type(error).__name__, message=str(error)))
        record['costs']['input_counts'] = dict(work); save(output/'run.json', record)
        raise


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--output', type=Path, default=OUTPUT)
    args = parser.parse_args(); run(args.output)


if __name__ == '__main__':
    main()
