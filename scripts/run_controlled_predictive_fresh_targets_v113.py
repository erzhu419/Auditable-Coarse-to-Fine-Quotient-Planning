"""Evaluate frozen source-validated updates on fresh common target histories."""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
import importlib
import json
from pathlib import Path
import platform
import shutil
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'src'))
from acfqp.science.controlled_predictive_fragments_v83 import QUERIES
from acfqp.science.controlled_predictive_fresh_targets_v113 import build_target_history, reference_job
from acfqp.science.controlled_predictive_frozen_cross_scoring_v113 import score_frozen_models
from scripts.run_controlled_predictive_nested_selection_v112 import METHODS, CONTRASTS

SOURCE = ROOT / 'reports/controlled_predictive_nested_selection_v112'
DYNAMICS_SOURCE = ROOT / 'reports/controlled_predictive_fresh_ranking_v105/supplied_dynamics.json'
SOURCE_BUNDLES, TARGETS, WIDTHS = (11, 12, 13, 14), (15, 16, 17, 18), (4, 16)
WORKERS, MAX_STEPS, ROOTS_PER_QUERY, REPLICAS = 4, 2000, 8, 32


def save(path, value):
    path.write_text(json.dumps(value, allow_nan=False, separators=(',', ':')) + '\n')


def snapshot(directory):
    importlib.import_module('scripts.analyze_controlled_predictive_fresh_targets_v113')
    paths = {Path(__file__).resolve(), ROOT / 'specs/FRESH_TARGETS_V113.md'}
    for module in list(sys.modules.values()):
        filename = getattr(module, '__file__', None)
        if filename:
            path = Path(filename).resolve()
            if path.is_relative_to(ROOT / 'src') or path.is_relative_to(ROOT / 'scripts'):
                paths.add(path)
    for source in paths:
        target = directory / 'source' / source.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)


def merge_reference(cohort, record):
    matches = [root for root in cohort['roots'] if root['root_id'] == record['root_id']]
    if len(matches) != 1:
        raise ValueError('reference must bind to exactly one frozen new target root')
    root = matches[0]
    if (any(root[key] != record[key] for key in ('life', 'query', 'episode'))
            or 'reference_log' in root):
        raise ValueError('reference is duplicated or differs from its frozen new target')
    for key in ('reference_log', 'reference_audit', 'reference_complete'):
        root[key] = deepcopy(record[key])
    root['reference_seconds'] = record['seconds']
    cohort['completed_references'] += 1


def run(directory):
    started = perf_counter()
    directory.mkdir(parents=True, exist_ok=False)
    snapshot(directory)
    source = json.loads((SOURCE / 'run.json').read_text())
    analysis = json.loads((SOURCE / 'analysis.json').read_text())
    payload = json.loads(DYNAMICS_SOURCE.read_text())
    if source['status'] != 'complete' or not analysis['primary_complete']:
        raise ValueError('fresh-target evaluation requires complete frozen V112 models and selections')
    if source['settings']['lifecycles'] != list(SOURCE_BUNDLES):
        raise ValueError('source bundle roster differs from V112')
    save(directory / 'supplied_dynamics.json', payload)
    report = dict(schema='acfqp.fresh_targets.v113', status='running', platform=platform.platform(),
        executable=sys.executable, python=sys.version, source=str(SOURCE), dynamics_source=str(DYNAMICS_SOURCE),
        settings=dict(source_bundles=list(SOURCE_BUNDLES), lifecycles=list(TARGETS), widths=list(WIDTHS),
            methods=list(METHODS), contrasts=CONTRASTS, queries=QUERIES,
            validation_roots_per_query=ROOTS_PER_QUERY, prefix_replicas=REPLICAS, reference_replicas=REPLICAS,
            reference_block_size=16, horizon=4, feature_dim=121, max_steps=MAX_STEPS, workers=WORKERS,
            source_life_base=113000, prefix_seed_base=253000000000, reference_life_base=113000,
            new_neural_model_fits=0, new_optimizer_steps=0, new_training_environment_transitions=0),
        source_models=deepcopy(source['models']), source_folds=deepcopy(source['inherited_folds']),
        frozen_selections=deepcopy(source['selections']), source_settings=deepcopy(source['settings']),
        inherited_work=dict(source['inherited_work'], V112=analysis['actual_executed_work']),
        inherited_selection_acquisition_accounting=deepcopy(source['selection_acquisition_accounting']),
        inherited_cohort_extraction_work=deepcopy(analysis['inherited_cohort_extraction_work']),
        histories=[], cohort=dict(roots=[], missing_roots=[], expected_roots=64, completed_references=0),
        models=[], decisions=[], scoring_log=None,
        runner_checks=dict(source_complete=True, fresh_history_namespace=not set(TARGETS).intersection(SOURCE_BUNDLES),
            frozen_source_selections_exact=True, predictions_before_references=False,
            reference_root_binding=True, all_history_execution_checks=True, all_reference_execution_checks=True))
    save(directory / 'run.json', report)
    with ProcessPoolExecutor(max_workers=WORKERS) as pool:
        tasks = {pool.submit(build_target_history, life, directory, payload): life for life in TARGETS}
        for future in as_completed(tasks):
            history = future.result()
            if history['life'] != tasks[future]:
                raise ValueError('new source-game history differs from its submitted identity')
            report['histories'].append(history)
            report['histories'].sort(key=lambda row: row['life'])
            report['runner_checks']['all_history_execution_checks'] &= bool(history['checks']) and all(history['checks'].values())
            report['actual_wall_seconds'] = perf_counter() - started
            save(directory / 'run.json', report)
            print(json.dumps(dict(phase='target_history', life=history['life'], roots=len(history['roots']),
                missing=len(history['missing_roots']), transitions=history['source_log']['ground_work'].get('sampled_transitions', 0))), flush=True)
        report['cohort']['roots'] = deepcopy([root for history in report['histories'] for root in history['roots']])
        report['cohort']['roots'].sort(key=lambda row: (row['life'], tuple(QUERIES).index(row['query']), row['episode']))
        report['cohort']['missing_roots'] = deepcopy([row for history in report['histories'] for row in history['missing_roots']])
        save(directory / 'run.json', report)
        if not report['runner_checks']['all_history_execution_checks']:
            raise ValueError('new source games or prefixes differ from their frozen execution semantics')
        report['models'], report['decisions'], report['scoring_log'] = score_frozen_models(source, report['cohort']['roots'])
        save(directory / 'run.json', report)
        if not all(report['scoring_log']['checks'].values()):
            raise ValueError('fresh target scoring differs from the complete frozen crossed roster')
        save(directory / 'pre_reference_cohort.json', dict(roots=report['cohort']['roots'],
            models=report['models'], decisions=report['decisions'], frozen_selections=report['frozen_selections']))
        report['runner_checks']['predictions_before_references'] = all('reference_log' not in root
            for root in report['cohort']['roots']) and report['cohort']['completed_references'] == 0
        save(directory / 'run.json', report)
        print(json.dumps(dict(phase='frozen_crossed_predictions', models=len(report['models']),
            decisions=len(report['decisions']), counts=report['scoring_log']['counts'])), flush=True)
        tasks = {pool.submit(reference_job, root, directory, payload): root['root_id'] for root in report['cohort']['roots']}
        for future in as_completed(tasks):
            record = future.result()
            if record['root_id'] != tasks[future]:
                report['runner_checks']['reference_root_binding'] = False
                save(directory / 'run.json', report)
                raise ValueError('returned reference differs from its submitted root')
            merge_reference(report['cohort'], record)
            report['runner_checks']['all_reference_execution_checks'] &= bool(record['reference_audit']) and all(record['reference_audit'].values())
            report['actual_wall_seconds'] = perf_counter() - started
            save(directory / 'run.json', report)
            print(json.dumps(dict(phase='fresh_reference', root_id=record['root_id'],
                completed=report['cohort']['completed_references'], expected=report['cohort']['expected_roots'],
                reference_complete=record['reference_complete'],
                transitions=record['reference_log']['ground_work']['sampled_transitions'],
                seconds=report['actual_wall_seconds'])), flush=True)
    report['runner_checks']['frozen_source_selections_exact'] = (report['frozen_selections'] == source['selections']
        and report['source_models'] == source['models'] and report['source_folds'] == source['inherited_folds'])
    save(directory / 'run.json', report)
    if not all(report['runner_checks'].values()):
        raise ValueError('fresh target execution or frozen choices are incomplete')
    report.update(status='complete', actual_wall_seconds=perf_counter() - started)
    save(directory / 'run.json', report)
    print(json.dumps(dict(phase='complete', references=report['cohort']['completed_references'],
        seconds=report['actual_wall_seconds'])), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    run(parser.parse_args().output)
