"""Update only the output head and retain the half-model hidden representation."""
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
from acfqp.science.controlled_predictive_incremental_data_v107 import load_training
from acfqp.science.controlled_predictive_frozen_head_v109 import fit_update, MODE, STEPS
from scripts.run_controlled_predictive_incremental_ranking_v107 import score_new

TRAIN_SOURCE = ROOT / 'reports/controlled_predictive_fresh_ranking_v105'
CROSS_SOURCE = ROOT / 'reports/controlled_predictive_query_update_v108'
JOINT_SOURCE = ROOT / 'reports/controlled_predictive_incremental_ranking_v107'
MODES = (MODE,)
WIDTHS = (4, 16)
BASE = {width: f'R4_H{width}_UNIFORM_SHRINK_DIRECT' for width in WIDTHS}
JOINT = {width: BASE[width] + '_FROZEN_STATS_WARM' for width in WIDTHS}
NEW_METHODS = tuple(JOINT[width] + '_' + mode for width in WIDTHS for mode in MODES)
CONTRASTS = []
for width in WIDTHS:
    arms = [JOINT[width] + '_' + mode for mode in MODES]
    for arm in arms:
        CONTRASTS.extend((arm, control) for control in
            (JOINT[width], BASE[width] + '_FROZEN_HALF', 'H2_ONLY'))


def save(path, value):
    path.write_text(json.dumps(value, allow_nan=False, separators=(',', ':')) + '\n')


def snapshot(directory):
    importlib.import_module('scripts.analyze_controlled_predictive_frozen_head_v109')
    paths = {Path(__file__).resolve(), ROOT / 'specs/FROZEN_HEAD_V109.md'}
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
    cross = json.loads((CROSS_SOURCE / 'run.json').read_text())
    analysis = json.loads((CROSS_SOURCE / 'analysis.json').read_text())
    source = json.loads((TRAIN_SOURCE / 'run.json').read_text())
    joint = json.loads((JOINT_SOURCE / 'run.json').read_text())
    if any(row['status'] != 'complete' for row in (cross, source, joint)) or not analysis['primary_complete']:
        raise ValueError('head update requires completed V105 data, V107 joint controls and V108 common-root results')
    settings = dict(cross['settings'], methods=cross['settings']['methods'] + list(NEW_METHODS),
        contrasts=CONTRASTS, update_modes=list(MODES), optimizer_steps=STEPS,
        new_neural_model_fits=8, expected_new_model_root_decisions=512,
        crossed_model_count=56, new_environment_transitions=0, new_model_prefix_transitions=0)
    report = dict(schema='acfqp.frozen_head.v109', status='running',
        platform=platform.platform(), executable=sys.executable, python=sys.version,
        source=str(CROSS_SOURCE), training_source=str(TRAIN_SOURCE), joint_source=str(JOINT_SOURCE), settings=settings,
        inherited_model_methods=cross['settings']['methods'][2:], inherited_decisions=len(cross['decisions']),
        inherited_v105_work=cross['inherited_v105_work'], inherited_v106_work=cross['inherited_v106_work'],
        inherited_v107_work=cross['inherited_v107_work'], inherited_v108_work=analysis['actual_executed_work'],
        cohort=deepcopy(cross['cohort']), models=deepcopy(cross['models']), decisions=deepcopy(cross['decisions']),
        training=[], scoring_log=None, runner_checks=dict(cached_baselines_exact=True,
            new_model_statistics_match=True, new_model_fit_metadata_match=True, joint_start_statistics_match=True, frozen_hidden_parameters=True))
    save(directory / 'run.json', report)
    new_models = []
    allocations = {row['life']: row for row in source['allocations']}
    for life in settings['training_lifecycles']:
        allocation = allocations[life]
        records, halves, data = load_training(TRAIN_SOURCE, life, allocation)
        cutoff = allocation['construction'][-1]['episode_cutoff']
        stage = dict(life=life, data_log=data, fit_logs={}, model_metadata={})
        report['training'].append(stage)
        folder = directory / f'life_{life}'; folder.mkdir()
        save(directory / 'run.json', report)
        if not all(data['checks'].values()):
            raise ValueError('retained training data or half statistics do not match: ' + str(data['checks']))
        for width in WIDTHS:
            half = halves[str(width)]
            joint_log = next(row for row in joint['training'] if row['life'] == life)['fit_logs'][JOINT[width]]
            report['runner_checks']['joint_start_statistics_match'] &= (
                joint_log['statistics_training_episodes'] == data['half']['training_episodes']
                and joint_log['training_episodes'] == data['full']['training_episodes']
                and joint_log['uniform_gamma'] == half['uniform_gamma']
                and joint_log['new_optimizer_steps'] == STEPS
                and joint_log['optimizer_state'] == 'reset_zero_moments')
            if not report['runner_checks']['joint_start_statistics_match']:
                save(directory / 'run.json', report)
                raise ValueError('inherited joint update does not match the head-update starting data')
            for mode in MODES:
                name = JOINT[width] + '_' + mode
                model, log = fit_update(records, cutoff, half, mode)
                payload = model.to_payload()
                half_path = allocation['model_metadata'][BASE[width] + '_FROZEN_HALF']['path']
                payload['update'] = dict(mode=mode, optimized_queries=log['optimized_queries'],
                    trainable_parameter_count=log['trainable_parameter_count'],
                    frozen_parameter_count=log['frozen_parameter_count'],
                    updated_parameter_indices=log['updated_parameter_indices'],
                    data_loss_weight=log['data_loss_weight'], full_loss_denominator_roots=log['full_loss_denominator_roots'],
                    optimizer_state=log['optimizer_state'],
                    new_optimizer_steps=log['new_optimizer_steps'],
                    inherited_parameter_steps=log['inherited_parameter_steps'],
                    parameter_lineage_steps=log['parameter_lineage_steps'], half_source_path=half_path)
                path = folder / f'{name.lower()}_model.json'
                save(path, payload)
                metadata = dict(hidden=width, budget=settings['budgets'][-1], episode_cutoff=cutoff,
                    family='UNIFORM_SHRINK', mode=mode, optimized_queries=log['optimized_queries'], path=str(path), half_source_path=half_path,
                    parameter_count=model.parameter_count, trainable_parameter_count=log['trainable_parameter_count'],
                    frozen_parameter_count=log['frozen_parameter_count'], updated_parameter_indices=log['updated_parameter_indices'])
                stage['fit_logs'][name] = log
                stage['model_metadata'][name] = metadata
                new_models.append(dict(training_life=life, method=name, metadata=metadata))
                report['runner_checks']['new_model_statistics_match'] &= all(
                    payload[field] == half[field] for field in ('mean', 'scale', 'uniform_gamma'))
                report['runner_checks']['frozen_hidden_parameters'] &= payload['parameters'][:2] == half['parameters'][:2]
                report['runner_checks']['new_model_fit_metadata_match'] &= (payload['hidden'] == width
                    and payload['checkpoint'] == cutoff and payload['family'] == 'UNIFORM_SHRINK'
                    and payload['optimizer_steps'] == STEPS)
                save(folder / 'construction.json', stage)
                save(directory / 'run.json', report)
                if not all(report['runner_checks'].values()) or not all(log['checks'].values()):
                    raise ValueError('new update model does not match frozen statistics, hidden parameters or fit semantics')
        print(json.dumps(dict(phase='update_fit', lifecycle=life, records=len(records), fits=len(stage['fit_logs']),
            losses={name: log['models']['UNIFORM_SHRINK']['final_loss'] for name, log in stage['fit_logs'].items()})), flush=True)
    decisions, scoring = score_new(new_models, report['cohort']['roots'])
    report['models'].extend(new_models)
    report['decisions'].extend(decisions)
    report['scoring_log'] = scoring
    report['runner_checks']['cached_baselines_exact'] = (report['models'][:len(cross['models'])] == cross['models']
        and report['decisions'][:len(cross['decisions'])] == cross['decisions'] and report['cohort'] == cross['cohort'])
    report['actual_wall_seconds'] = perf_counter() - started
    save(directory / 'run.json', report)
    if not all(scoring['checks'].values()) or not all(report['runner_checks'].values()):
        raise ValueError('new scoring or retained V108 baseline differs from frozen inputs')
    report.update(status='complete', actual_wall_seconds=perf_counter() - started)
    save(directory / 'run.json', report)
    print(json.dumps(dict(phase='complete', new_models=len(new_models), new_decisions=len(decisions),
        counts=scoring['counts'], seconds=report['actual_wall_seconds'])), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    run(parser.parse_args().output)
