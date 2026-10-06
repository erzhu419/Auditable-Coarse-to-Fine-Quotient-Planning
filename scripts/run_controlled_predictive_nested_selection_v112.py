"""Choose HALF or FULL from source-history validation, then evaluate the excluded history."""
import argparse
from copy import deepcopy
import importlib
from itertools import combinations
import json
from pathlib import Path
import platform
import shutil
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'src'))
from acfqp.science.controlled_predictive_pooled_data_v110 import load_bank
from acfqp.science.controlled_predictive_pooled_history_v110 import fit_stage, STEPS
from acfqp.science.controlled_predictive_nested_data_v112 import pool_pair, score_inner_models
from acfqp.science.controlled_predictive_nested_selection_v112 import (
    select_updates, selection_acquisition_accounting)
from scripts.run_controlled_predictive_pooled_history_v110 import METHODS as OLD_METHODS

TRAIN_SOURCE = ROOT / 'reports/controlled_predictive_fresh_ranking_v105'
SOURCE = ROOT / 'reports/controlled_predictive_pooled_history_v110'
PREVIOUS = ROOT / 'reports/controlled_predictive_half_continuation_v111'
LIVES, WIDTHS, STAGES = (11, 12, 13, 14), (4, 16), ('HALF', 'FULL')
QUERIES = ('reward', 'risk_goal')
METHODS = OLD_METHODS + tuple(f'SELECTED_H{hidden}' for hidden in WIDTHS)
CONTRASTS = tuple(pair for hidden in WIDTHS for pair in (
    (f'SELECTED_H{hidden}', f'POOLED_H{hidden}_HALF'),
    (f'SELECTED_H{hidden}', f'POOLED_H{hidden}_FULL'),
    (f'SELECTED_H{hidden}', 'H2_ONLY'),
    (f'POOLED_H{hidden}_FULL', f'POOLED_H{hidden}_HALF')))


def save(path, value):
    path.write_text(json.dumps(value, allow_nan=False, separators=(',', ':')) + '\n')


def snapshot(directory):
    importlib.import_module('scripts.analyze_controlled_predictive_nested_selection_v112')
    paths = {Path(__file__).resolve(), ROOT / 'specs/NESTED_SELECTION_V112.md'}
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


def derive_outer_decisions(selections, models, decisions, roots):
    """Dispatch query-specific choices by copying the already scored outer model."""
    started = perf_counter()
    wanted = {(life, width, query) for life in LIVES for width in WIDTHS for query in QUERIES}
    actual = {(s['heldout_life'], s['hidden'], s['query']) for s in selections}
    if actual != wanted or len(selections) != len(wanted):
        raise ValueError('each excluded history, width and query requires one selection')
    cached = {(d['root_id'], d['heldout_life'], d['method']): d['event'] for d in decisions}
    metadata = {(m['heldout_life'], m['method']): m['metadata'] for m in models}
    output = []
    for choice in selections:
        target, width, query = choice['heldout_life'], choice['hidden'], choice['query']
        method = choice['chosen_method']
        if choice['chosen_stage'] not in STAGES or method != f'POOLED_H{width}_{choice["chosen_stage"]}':
            raise ValueError('selection must dispatch the matching width and chosen stage')
        model = metadata[target, method]
        sources = [life for life in LIVES if life != target]
        if (model['source_lives'] != sources or choice['source_lives'] != sources
                or model['heldout_life'] != target or model['hidden'] != width
                or model['stage'] != choice['chosen_stage']):
            raise ValueError('chosen outer model differs from its excluded-history selection')
        group = [root for root in roots if root['life'] == target and root['query'] == query]
        if len(group) != 8 or {root['episode'] for root in group} != set(range(8)):
            raise ValueError('derived decisions require all eight frozen query roots')
        for root in group:
            output.append(dict(root_id=root['root_id'], heldout_life=target, method=f'SELECTED_H{width}',
                chosen_method=method, chosen_model_path=model['path'],
                event=deepcopy(cached[root['root_id'], target, method])))
    expected = {(r['root_id'], r['life'], f'SELECTED_H{width}') for r in roots for width in WIDTHS}
    checks = dict(selection_roster_complete=True, chosen_outer_model_bound=True,
        selected_event_exact=all(row['event'] == cached[row['root_id'], row['heldout_life'], row['chosen_method']]
            for row in output),
        derived_roster_complete=len(output) == len(expected)
            and {(row['root_id'], row['heldout_life'], row['method']) for row in output} == expected)
    return output, dict(checks=checks, counts=dict(derived_outer_decisions=len(output),
        cached_outer_decision_lookups=len(output), new_neural_candidate_predictions=0),
        seconds=perf_counter() - started)


def run(directory):
    started = perf_counter()
    directory.mkdir(parents=True, exist_ok=False)
    snapshot(directory)
    outer = json.loads((SOURCE / 'run.json').read_text())
    outer_analysis = json.loads((SOURCE / 'analysis.json').read_text())
    previous = json.loads((PREVIOUS / 'run.json').read_text())
    previous_analysis = json.loads((PREVIOUS / 'analysis.json').read_text())
    training = json.loads((TRAIN_SOURCE / 'run.json').read_text())
    if (any(row['status'] != 'complete' for row in (outer, previous, training))
            or not outer_analysis['primary_complete'] or not previous_analysis['primary_complete']):
        raise ValueError('nested selection requires complete V105/V110/V111 sources')
    settings = dict(outer['settings'], methods=list(METHODS), contrasts=CONTRASTS,
        optimizer_steps=STEPS, new_neural_model_fits=24, expected_new_model_root_decisions=768,
        expected_derived_outer_decisions=128, evaluation_scope='nested_source_history_selection',
        selection_rule='query_mean_source_validation_delta_gt_zero_else_half')
    report = dict(schema='acfqp.nested_selection.v112', status='running', platform=platform.platform(),
        executable=sys.executable, python=sys.version, source=str(SOURCE), previous=str(PREVIOUS),
        training_source=str(TRAIN_SOURCE), settings=settings,
        inherited_work=dict(previous['inherited_work'], V111=previous_analysis['actual_executed_work']),
        cohort=deepcopy(outer['cohort']), models=deepcopy(outer['models']), decisions=deepcopy(outer['decisions']),
        inherited_model_count=len(outer['models']), inherited_decisions=len(outer['decisions']),
        inherited_folds=deepcopy(outer['folds']), acquisition_accounting=deepcopy(outer['acquisition_accounting']),
        selection_acquisition_accounting=None, bank_log=None, pairs=[], inner_models=[], inner_decisions=[],
        scoring_log=None, selections=[], selection_log=None, derived_log=None,
        runner_checks=dict(source_history_roster=True, pair_exclusions=True, paired_full_initialization=True,
            model_fit_metadata_match=True, cached_outer_models_and_cohort_exact=True, inherited_outer_decisions_exact=True))
    save(directory / 'run.json', report)
    report['selection_acquisition_accounting'] = selection_acquisition_accounting(
        report['cohort']['roots'], report['acquisition_accounting'], LIVES)
    bank, bank_log = load_bank(TRAIN_SOURCE, training['allocations'])
    report['bank_log'] = bank_log
    report['runner_checks']['source_history_roster'] = sorted(bank) == list(LIVES)
    save(directory / 'run.json', report)
    if not report['runner_checks']['source_history_roster'] or not all(bank_log['checks'].values()):
        raise ValueError('original source bank is incomplete')
    for sources in combinations(LIVES, 2):
        records, data = pool_pair(bank, sources)
        pair_id, validation = data['pair_id'], data['validation_lives']
        pair = dict(pair_id=pair_id, source_lives=list(sources), validation_lives=validation,
            data_log=data, fit_logs={}, model_metadata={})
        report['pairs'].append(pair)
        folder = directory / f'pair_{pair_id}'
        folder.mkdir()
        report['runner_checks']['pair_exclusions'] &= (data['source_lives'] == list(sources)
            and validation == [life for life in LIVES if life not in sources]
            and all(row['source_life'] in sources for row in records) and all(data['checks'].values()))
        if not report['runner_checks']['pair_exclusions']:
            save(directory / 'run.json', report)
            raise ValueError('inner model includes a validation or target history')
        for width in WIDTHS:
            half = None
            for stage in STAGES:
                method = f'POOLED_H{width}_{stage}'
                model, log = fit_stage(records, width, stage, list(sources), half)
                payload = model.to_payload()
                payload['update'] = dict(pair_id=pair_id, source_lives=list(sources), validation_lives=validation,
                    stage=stage, statistics_roster=log['statistics_roster'], training_roster=log['training_roster'],
                    optimizer_state=log['optimizer_state'], new_optimizer_steps=log['new_optimizer_steps'],
                    inherited_parameter_steps=log['inherited_parameter_steps'], parameter_lineage_steps=log['parameter_lineage_steps'])
                path = folder / f'{method.lower()}_model.json'
                save(path, payload)
                metadata = dict(source_lives=list(sources), validation_lives=validation, hidden=width,
                    stage=stage, family=model.family, checkpoint=model.checkpoint, budget=model.checkpoint,
                    path=str(path), parameter_count=model.parameter_count)
                pair['fit_logs'][method], pair['model_metadata'][method] = log, metadata
                report['inner_models'].append(dict(pair_id=pair_id, method=method, metadata=metadata))
                report['runner_checks']['paired_full_initialization'] &= (
                    log['initialization'] == ('original_initialization' if stage == 'HALF' else 'half_parameters')
                    and log['optimizer_state'] == 'reset_zero_moments' and log['new_optimizer_steps'] == STEPS
                    and log['inherited_parameter_steps'] == (0 if stage == 'HALF' else STEPS)
                    and log['statistics_roster'] == data['half']['training_roster'])
                if stage == 'FULL':
                    report['runner_checks']['paired_full_initialization'] &= all(payload[key] == half[key]
                        for key in ('mean', 'scale', 'uniform_gamma'))
                report['runner_checks']['model_fit_metadata_match'] &= (payload['hidden'] == width
                    and payload['checkpoint'] == (256000 if stage == 'HALF' else 512000)
                    and payload['family'] == 'UNIFORM_SHRINK' and log['source_lives'] == list(sources)
                    and log['training_roster'] == data[stage.lower()]['training_roster'])
                save(folder / 'construction.json', pair)
                save(directory / 'run.json', report)
                if not all(log['checks'].values()) or not all(report['runner_checks'].values()):
                    raise ValueError('inner fitting differs from frozen paired stages')
                if stage == 'HALF':
                    half = payload
        print(json.dumps(dict(phase='pair_complete', pair_id=pair_id, models=len(pair['fit_logs']))), flush=True)
    report['inner_decisions'], report['scoring_log'] = score_inner_models(report['inner_models'], report['cohort']['roots'])
    save(directory / 'run.json', report)
    if not all(report['scoring_log']['checks'].values()):
        raise ValueError('inner scoring did not preserve the complete validation roster')
    report['selections'], report['selection_log'] = select_updates(report['inner_decisions'],
        report['cohort']['roots'], LIVES, WIDTHS, roots_per_query=settings['validation_roots_per_query'])
    save(directory / 'run.json', report)
    if not all(report['selection_log']['checks'].values()):
        raise ValueError('selection differs from frozen source-history rule')
    selected, report['derived_log'] = derive_outer_decisions(report['selections'], report['models'],
        outer['decisions'], report['cohort']['roots'])
    report['decisions'].extend(selected)
    report['runner_checks']['cached_outer_models_and_cohort_exact'] = (report['models'] == outer['models']
        and report['cohort'] == outer['cohort'] and report['inherited_folds'] == outer['folds'])
    report['runner_checks']['inherited_outer_decisions_exact'] = report['decisions'][:len(outer['decisions'])] == outer['decisions']
    report['actual_wall_seconds'] = perf_counter() - started
    save(directory / 'run.json', report)
    if not all(report['runner_checks'].values()) or not all(report['derived_log']['checks'].values()):
        raise ValueError('selected outer deployment or inherited comparisons are incomplete')
    report.update(status='complete', actual_wall_seconds=perf_counter() - started)
    save(directory / 'run.json', report)
    print(json.dumps(dict(phase='complete', inner_models=len(report['inner_models']),
        new_inner_decisions=len(report['inner_decisions']), derived_outer_decisions=len(selected),
        seconds=report['actual_wall_seconds'])), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    run(parser.parse_args().output)
