"""Validate the actual three-source deployment models on independent source roots."""
import argparse
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
from acfqp.science.controlled_predictive_direct_validation_v114 import score_source_models, select_updates
from scripts.run_controlled_predictive_fresh_targets_v113 import METHODS as OLD_METHODS

SOURCE = ROOT / 'reports/controlled_predictive_nested_selection_v112'
TARGET = ROOT / 'reports/controlled_predictive_fresh_targets_v113'
TRAINING = ROOT / 'reports/controlled_predictive_fresh_ranking_v105'
BUNDLES, WIDTHS, QUERIES = (11, 12, 13, 14), (4, 16), ('reward', 'risk_goal')
METHODS = tuple(OLD_METHODS) + tuple(f'DIRECT_H{width}' for width in WIDTHS)
CONTRASTS = tuple((f'DIRECT_H{width}', right) for width in WIDTHS for right in (
    f'SELECTED_H{width}', f'POOLED_H{width}_HALF', f'POOLED_H{width}_FULL', 'H2_ONLY'))


def save(path, value):
    path.write_text(json.dumps(value, allow_nan=False, separators=(',', ':')) + '\n')


def snapshot(directory):
    importlib.import_module('scripts.analyze_controlled_predictive_direct_validation_v114')
    paths = {Path(__file__).resolve(), ROOT / 'specs/DIRECT_VALIDATION_V114.md'}
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


def source_overlap(training, roots):
    acquired = [dict(root, life=allocation['life']) for allocation in training['allocations']
        for batch in allocation['construction'] for root in batch['acquisition']['completed_roots']]
    train_seeds, validation_seeds = ({root['source_seed'] for root in group} for group in (acquired, roots))
    train_boards, validation_boards = ({tuple(root['board']) for root in group} for group in (acquired, roots))
    seed_overlap, board_overlap = len(train_seeds & validation_seeds), len(train_boards & validation_boards)
    checks = dict(seeds_disjoint=seed_overlap == 0, boards_disjoint=board_overlap == 0,
        training_seed_namespace=all(root['source_seed'] == 98000000 + root['life'] * 100000
            + root['episode'] * 10 + QUERIES.index(root['query']) for root in acquired),
        natural_validation_seed_namespace=all(root['source_seed'] == 10590000 + root['life'] * 100
            + root['episode'] for root in roots))
    return dict(training_roots=len(acquired), validation_roots=len(roots),
        source_seed_overlap_count=seed_overlap, board_overlap_count=board_overlap, checks=checks,
        training_seed_range=[min(train_seeds), max(train_seeds)],
        validation_seed_range=[min(validation_seeds), max(validation_seeds)])


def derive_target_decisions(selections, target):
    started = perf_counter()
    roots, models, decisions = target['cohort']['roots'], target['models'], target['decisions']
    choices = {(s['heldout_life'], s['hidden'], s['query']): s for s in selections}
    expected = {(bundle, width, query) for bundle in BUNDLES for width in WIDTHS for query in QUERIES}
    if set(choices) != expected or len(choices) != len(selections):
        raise ValueError('direct deployment requires all 16 unique source choices')
    cache = {(d['bundle_id'], d['root_id'], d['method']): d['event'] for d in decisions}
    metadata = {(m['bundle_id'], m['method']): m['metadata'] for m in models}
    derived = []
    for bundle, width, query in sorted(expected):
        choice = choices[bundle, width, query]
        method = choice['chosen_method']
        stage = choice['chosen_stage']
        sources = [life for life in BUNDLES if life != bundle]
        if (stage not in ('HALF', 'FULL') or method != f'POOLED_H{width}_{stage}'
                or choice['source_lives'] != sources or metadata[bundle, method]['source_lives'] != sources):
            raise ValueError('direct source choice must bind to its actual deployment model')
        for root in roots:
            if root['query'] != query:
                continue
            if root['life'] in BUNDLES:
                raise ValueError('retrospective target history overlaps the source histories')
            event = cache[bundle, root['root_id'], method]
            derived.append(dict(bundle_id=bundle, root_id=root['root_id'], target_life=root['life'],
                method=f'DIRECT_H{width}', chosen_method=method, chosen_model_path=metadata[bundle, method]['path'],
                event=deepcopy(event)))
    expected_rows = {(bundle, root['root_id'], f'DIRECT_H{width}')
        for bundle in BUNDLES for root in roots for width in WIDTHS}
    checks = dict(complete_direct_roster=len(derived) == len(expected_rows)
        and {(r['bundle_id'], r['root_id'], r['method']) for r in derived} == expected_rows,
        chosen_model_binding=True, selected_event_exact=all(r['event'] == cache[
            r['bundle_id'], r['root_id'], r['chosen_method']] for r in derived))
    return derived, dict(counts=dict(derived_decisions=len(derived), cached_decision_lookups=len(derived),
        new_neural_candidate_predictions=0, neural_model_fits=0, optimizer_steps=0,
        new_environment_transitions=0, new_synthetic_transitions=0), checks=checks, seconds=perf_counter() - started)


def run(directory):
    started = perf_counter()
    directory.mkdir(parents=True, exist_ok=False)
    snapshot(directory)
    source = json.loads((SOURCE / 'run.json').read_text())
    source_analysis = json.loads((SOURCE / 'analysis.json').read_text())
    training = json.loads((TRAINING / 'run.json').read_text())
    if source['status'] != 'complete' or training['status'] != 'complete' or not source_analysis['primary_complete']:
        raise ValueError('direct validation requires complete frozen source models and source evidence')
    overlap = source_overlap(training, source['cohort']['roots'])
    save(directory / 'source_overlap.json', overlap)
    if not all(overlap['checks'].values()):
        raise ValueError('source natural validation overlaps training or uses another seed namespace')
    # Scoring cannot access source outcomes; selection never receives the target run.
    scoring_roots = [{k: v for k, v in root.items() if not k.startswith('reference_')}
        for root in source['cohort']['roots']]
    source_decisions, scoring = score_source_models(source, scoring_roots, ROOT)
    save(directory / 'source_scores.json', dict(decisions=source_decisions, log=scoring))
    if not all(scoring['checks'].values()):
        raise ValueError('source scoring differs from actual deployment models')
    selections, selection_log = select_updates(source_decisions, source['cohort']['roots'])
    save(directory / 'pre_target_selection.json', dict(selections=selections, selection_log=selection_log))
    if not all(selection_log['checks'].values()):
        raise ValueError('source-only direct selection is incomplete')
    target = json.loads((TARGET / 'run.json').read_text())
    target_analysis = json.loads((TARGET / 'analysis.json').read_text())
    report = deepcopy(target)
    report.update(schema='acfqp.direct_validation.v114', status='running', platform=platform.platform(),
        executable=sys.executable, python=sys.version, source=str(SOURCE), target_source=str(TARGET),
        training_source=str(TRAINING), inherited_source=target['source'],
        inherited_runner_checks=deepcopy(target['runner_checks']),
        inherited_target_scoring_log=deepcopy(target['scoring_log']), inherited_target_analysis=target_analysis,
        inherited_target_decisions=deepcopy(target['decisions']),
        inherited_work=dict(target['inherited_work'], V113=target_analysis['actual_executed_work']),
        source_cohort=deepcopy(source['cohort']), source_overlap_check=overlap,
        source_decisions=source_decisions, source_scoring_log=scoring,
        direct_selections=selections, direct_selection_log=selection_log, derived_log=None,
        runner_checks=dict(source_complete=True, source_validation_outside_training=True,
            choices_saved_before_target_load=True, inherited_target_complete=target['status'] == 'complete'
                and target_analysis['primary_complete'], same_deployment_models=target['source_models'] == source['models'],
            old_source_choices_unchanged=target['frozen_selections'] == source['selections'],
            target_cohort_and_decisions_exact=True))
    report['settings'].update(methods=list(METHODS), contrasts=[list(pair) for pair in CONTRASTS],
        evaluation_scope='retrospective_actual_deployment_source_validation',
        selection_rule='query_mean_source_validation_delta_gt_zero_else_half')
    save(directory / 'run.json', report)
    if not all(report['runner_checks'].values()):
        raise ValueError('inherited target evidence differs from frozen source deployment')
    derived, report['derived_log'] = derive_target_decisions(selections, target)
    report['decisions'].extend(derived)
    report['runner_checks']['target_cohort_and_decisions_exact'] = (report['cohort'] == target['cohort']
        and report['models'] == target['models'] and report['decisions'][:len(target['decisions'])] == target['decisions'])
    report['actual_wall_seconds'] = perf_counter() - started
    save(directory / 'run.json', report)
    if not all(report['derived_log']['checks'].values()) or not all(report['runner_checks'].values()):
        raise ValueError('direct target dispatch failed to preserve the cached event')
    report['status'] = 'complete'
    save(directory / 'run.json', report)
    print(json.dumps(dict(status='complete', source_scoring=scoring['counts'], selection=selection_log['counts'],
        derived=report['derived_log']['counts'], seconds=report['actual_wall_seconds'])), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    run(parser.parse_args().output)
