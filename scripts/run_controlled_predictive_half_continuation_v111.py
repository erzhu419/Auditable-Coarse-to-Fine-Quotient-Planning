"""Continue pooled half models on half data under the full update's new-step budget."""
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
from acfqp.science.controlled_predictive_pooled_data_v110 import load_bank, pool_fold
from acfqp.science.controlled_predictive_half_continuation_v111 import fit_continuation, STEPS, STAGE
from scripts.run_controlled_predictive_pooled_history_v110 import score_models, METHODS as OLD_METHODS

TRAIN_SOURCE = ROOT / 'reports/controlled_predictive_fresh_ranking_v105'
SOURCE = ROOT / 'reports/controlled_predictive_pooled_history_v110'
LIVES, WIDTHS = (11, 12, 13, 14), (4, 16)
NEW_METHODS = tuple(f'POOLED_H{h}_HALF_CONTINUED' for h in WIDTHS)
METHODS = OLD_METHODS + NEW_METHODS
CONTRASTS = tuple(pair for h in WIDTHS for pair in (
    (f'POOLED_H{h}_FULL', f'POOLED_H{h}_HALF_CONTINUED'),
    (f'POOLED_H{h}_HALF_CONTINUED', f'POOLED_H{h}_HALF'),
    (f'POOLED_H{h}_HALF_CONTINUED', 'H2_ONLY'),
    (f'POOLED_H{h}_FULL', f'POOLED_H{h}_HALF')))


def save(path, value):
    path.write_text(json.dumps(value, allow_nan=False, separators=(',', ':')) + '\n')


def snapshot(directory):
    importlib.import_module('scripts.analyze_controlled_predictive_half_continuation_v111')
    paths = {Path(__file__).resolve(), ROOT / 'specs/HALF_CONTINUATION_V111.md'}
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


def run(directory):
    started = perf_counter()
    directory.mkdir(parents=True, exist_ok=False)
    snapshot(directory)
    previous = json.loads((SOURCE / 'run.json').read_text())
    prior_analysis = json.loads((SOURCE / 'analysis.json').read_text())
    source = json.loads((TRAIN_SOURCE / 'run.json').read_text())
    if previous['status'] != 'complete' or source['status'] != 'complete' or not prior_analysis['primary_complete']:
        raise ValueError('half-data continuation requires complete V110 models and retained source data')
    settings = dict(previous['settings'], methods=list(METHODS), contrasts=CONTRASTS,
        optimizer_steps=STEPS, update_modes=[STAGE], new_neural_model_fits=8,
        expected_new_model_root_decisions=128)
    inherited = dict(previous['inherited_work'], V110=prior_analysis['actual_executed_work'])
    report = dict(schema='acfqp.half_continuation.v111', status='running', platform=platform.platform(),
        executable=sys.executable, python=sys.version, source=str(SOURCE), training_source=str(TRAIN_SOURCE),
        settings=settings, inherited_work=inherited, cohort=deepcopy(previous['cohort']),
        acquisition_accounting=deepcopy(previous['acquisition_accounting']),
        inherited_folds=deepcopy(previous['folds']), inherited_model_count=len(previous['models']),
        inherited_decisions=len(previous['decisions']), bank_log=None, folds=[],
        input_counts=dict(pooled_half_payload_files_read=0), models=deepcopy(previous['models']),
        decisions=deepcopy(previous['decisions']), scoring_log=None,
        runner_checks=dict(source_history_roster=True, source_target_exclusion=True,
            inherited_half_bound=True, matched_full_update=True, half_statistics_frozen=True,
            model_fit_metadata_match=True, cached_baselines_exact=True))
    save(directory / 'run.json', report)
    bank, bank_log = load_bank(TRAIN_SOURCE, source['allocations'])
    report['bank_log'] = bank_log
    report['runner_checks']['source_history_roster'] = sorted(bank) == list(LIVES)
    save(directory / 'run.json', report)
    if not report['runner_checks']['source_history_roster'] or not all(bank_log['checks'].values()):
        raise ValueError('original source bank is incomplete')
    old_folds = {row['heldout_life']: row for row in previous['folds']}
    new_models = []
    for target in LIVES:
        records, data = pool_fold(bank, target)
        sources = data['source_lives']
        fold = dict(heldout_life=target, source_lives=sources, data_log=data, fit_logs={}, model_metadata={})
        report['folds'].append(fold)
        folder = directory / f'heldout_{target}'
        folder.mkdir()
        report['runner_checks']['source_target_exclusion'] &= (target not in sources
            and sources == [life for life in LIVES if life != target]
            and all(row['source_life'] in sources for row in records))
        if not report['runner_checks']['source_target_exclusion']:
            save(directory / 'run.json', report)
            raise ValueError('excluded history entered source data')
        old_fold = old_folds[target]
        for width in WIDTHS:
            half_name, full_name = f'POOLED_H{width}_HALF', f'POOLED_H{width}_FULL'
            half_metadata = old_fold['model_metadata'][half_name]
            half = json.loads(Path(half_metadata['path']).read_text())
            report['input_counts']['pooled_half_payload_files_read'] += 1
            old_half, old_full = (old_fold['fit_logs'][name] for name in (half_name, full_name))
            report['runner_checks']['inherited_half_bound'] &= (old_fold['source_lives'] == sources
                and old_half['training_roster'] == half['update']['training_roster'] == data['half']['training_roster']
                and old_half['heldout_roster'] == data['half']['heldout_roster']
                and half['update']['statistics_roster'] == data['half']['training_roster']
                and half['update']['source_lives'] == sources and half['update']['heldout_life'] == target
                and half['update']['stage'] == 'HALF' and half['hidden'] == width
                and half['checkpoint'] == 256000 and half['optimizer_steps'] == STEPS)
            report['runner_checks']['matched_full_update'] &= (old_full['source_lives'] == sources
                and old_full['statistics_roster'] == data['half']['training_roster']
                and old_full['training_roster'] == data['full']['training_roster']
                and old_full['new_optimizer_steps'] == old_full['inherited_parameter_steps'] == STEPS
                and old_full['initialization'] == 'half_parameters'
                and old_full['optimizer_state'] == 'reset_zero_moments'
                and old_full['uniform_gamma'] == half['uniform_gamma'])
            save(directory / 'run.json', report)
            if not all(report['runner_checks'].values()):
                raise ValueError('inherited pooled half or full update does not match the retained fold')
            method = f'POOLED_H{width}_HALF_CONTINUED'
            model, log = fit_continuation(records, width, sources, half)
            payload = model.to_payload()
            payload['update'] = dict(stage=STAGE, source_lives=sources, heldout_life=target,
                statistics_roster=log['statistics_roster'], training_roster=log['training_roster'],
                optimizer_state=log['optimizer_state'], new_optimizer_steps=log['new_optimizer_steps'],
                inherited_parameter_steps=log['inherited_parameter_steps'], parameter_lineage_steps=log['parameter_lineage_steps'],
                half_source_path=half_metadata['path'])
            path = folder / f'{method.lower()}_model.json'
            save(path, payload)
            metadata = dict(hidden=width, stage=STAGE, family='UNIFORM_SHRINK', budget=model.checkpoint,
                checkpoint=model.checkpoint, source_lives=sources, heldout_life=target,
                path=str(path), parameter_count=model.parameter_count, half_source_path=half_metadata['path'])
            fold['fit_logs'][method], fold['model_metadata'][method] = log, metadata
            new_models.append(dict(heldout_life=target, method=method, metadata=metadata))
            report['runner_checks']['half_statistics_frozen'] &= all(payload[key] == half[key]
                for key in ('mean', 'scale', 'uniform_gamma'))
            report['runner_checks']['model_fit_metadata_match'] &= (payload['hidden'] == width
                and payload['checkpoint'] == 256000 and payload['family'] == 'UNIFORM_SHRINK'
                and payload['optimizer_steps'] == STEPS and log['source_lives'] == sources and log['stage'] == STAGE)
            save(folder / 'construction.json', fold)
            save(directory / 'run.json', report)
            if not all(log['checks'].values()) or not all(report['runner_checks'].values()):
                raise ValueError('new half continuation differs from its frozen data or fit semantics')
        print(json.dumps(dict(phase='fold_complete', heldout_life=target, source_lives=sources,
            training_roots=data['half']['training_roots'], new_models=len(fold['fit_logs']))), flush=True)
    decisions, scoring = score_models(new_models, report['cohort']['roots'])
    report['models'].extend(new_models)
    report['decisions'].extend(decisions)
    report['scoring_log'] = scoring
    report['runner_checks']['cached_baselines_exact'] = (report['cohort'] == previous['cohort']
        and report['models'][:len(previous['models'])] == previous['models']
        and report['decisions'][:len(previous['decisions'])] == previous['decisions']
        and report['inherited_folds'] == previous['folds'])
    report['actual_wall_seconds'] = perf_counter() - started
    save(directory / 'run.json', report)
    if not all(report['runner_checks'].values()) or not all(scoring['checks'].values()):
        raise ValueError('new half continuation scoring or retained baselines are incomplete')
    report.update(status='complete', actual_wall_seconds=perf_counter() - started)
    save(directory / 'run.json', report)
    print(json.dumps(dict(phase='complete', new_models=len(new_models), new_decisions=len(decisions),
        counts=scoring['counts'], seconds=report['actual_wall_seconds'])), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    run(parser.parse_args().output)
