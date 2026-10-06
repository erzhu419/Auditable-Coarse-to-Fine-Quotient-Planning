"""Fit matched fixed-statistics update arms and reuse the V106 reference bank."""
import argparse
from collections import Counter
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
from acfqp.science.controlled_predictive_incremental_ranking_v107 import fit_update, MODES, STEPS
from acfqp.science.controlled_predictive_capacity_ranking_v103 import CandidateModel
from acfqp.science.controlled_predictive_crossed_scoring_v106 import _event

TRAIN_SOURCE = ROOT / 'reports/controlled_predictive_fresh_ranking_v105'
CROSS_SOURCE = ROOT / 'reports/controlled_predictive_crossed_ranking_v106'
WIDTHS = (4, 16)
BASE = {width: f'R4_H{width}_UNIFORM_SHRINK_DIRECT' for width in WIDTHS}
NEW_METHODS = tuple(BASE[width] + '_' + mode for width in WIDTHS for mode in MODES)
CONTRASTS = []
for width in WIDTHS:
    base = BASE[width]
    scratch, warm = (base + '_' + mode for mode in MODES)
    CONTRASTS.extend(((scratch, base), (warm, scratch), (warm, base),
                      (warm, base + '_FROZEN_HALF'), (warm, 'H2_ONLY')))


def save(path, value):
    path.write_text(json.dumps(value, allow_nan=False, separators=(',', ':')) + '\n')


def snapshot(directory):
    importlib.import_module('scripts.analyze_controlled_predictive_incremental_ranking_v107')
    paths = {Path(__file__).resolve(), ROOT / 'specs/INCREMENTAL_RANKING_V107.md'}
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


def score_new(models, roots):
    started = perf_counter()
    decisions = []
    counts = Counter(model_payloads_loaded=0, model_root_scores=0, neural_candidate_predictions=0,
        neural_hidden_activations=0, new_environment_transitions=0, new_synthetic_transitions=0,
        neural_model_fits=0, optimizer_steps=0, model_prefix_trajectories=0)
    checks = dict(new_model_metadata_match=True, scoring_roster_complete=True)
    for row in models:
        metadata = row['metadata']
        payload = json.loads(Path(metadata['path']).read_text())
        model = CandidateModel.from_payload(payload)
        counts['model_payloads_loaded'] += 1
        checks['new_model_metadata_match'] &= (model.checkpoint == metadata['episode_cutoff']
            and model.hidden == metadata['hidden'] and model.family == metadata['family']
            and payload['update']['mode'] == metadata['mode'])
        if not checks['new_model_metadata_match']:
            break
        for root in roots:
            event = _event(model.score_candidates(root['features'], counts))
            counts['model_root_scores'] += 1
            decisions.append(dict(root_id=root['root_id'], training_life=row['training_life'],
                method=row['method'], event=event))
    checks['scoring_roster_complete'] = len(decisions) == len(models) * len(roots)
    return decisions, dict(counts=dict(counts), checks=checks, seconds=perf_counter() - started)


def run(directory):
    started = perf_counter()
    directory.mkdir(parents=True, exist_ok=False)
    snapshot(directory)
    cross = json.loads((CROSS_SOURCE / 'run.json').read_text())
    analysis = json.loads((CROSS_SOURCE / 'analysis.json').read_text())
    source = json.loads((TRAIN_SOURCE / 'run.json').read_text())
    if cross['status'] != 'complete' or source['status'] != 'complete' or not analysis['primary_complete']:
        raise ValueError('incremental comparison requires completed V105 data and V106 common-root references')
    settings = dict(cross['settings'], methods=cross['settings']['methods'] + list(NEW_METHODS),
        contrasts=CONTRASTS, update_modes=list(MODES), optimizer_steps=STEPS,
        new_neural_model_fits=16, expected_new_model_root_decisions=1024,
        crossed_model_count=32, new_environment_transitions=0, new_model_prefix_transitions=0)
    report = dict(schema='acfqp.incremental_ranking.v107', status='running',
        platform=platform.platform(), executable=sys.executable, python=sys.version,
        source=str(CROSS_SOURCE), training_source=str(TRAIN_SOURCE), settings=settings,
        inherited_model_methods=cross['settings']['methods'][2:], inherited_decisions=len(cross['decisions']),
        inherited_v105_work=cross['inherited_v105_work'], inherited_v106_work=analysis['actual_executed_work'],
        cohort=deepcopy(cross['cohort']), models=deepcopy(cross['models']), decisions=deepcopy(cross['decisions']),
        training=[], scoring_log=None, runner_checks=dict(cached_baselines_exact=True,
            new_model_statistics_match=True, new_model_fit_metadata_match=True))
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
            for mode in MODES:
                name = BASE[width] + '_' + mode
                model, log = fit_update(records, cutoff, half, mode)
                payload = model.to_payload()
                half_path = allocation['model_metadata'][BASE[width] + '_FROZEN_HALF']['path']
                payload['update'] = dict(mode=mode, optimizer_state=log['optimizer_state'],
                    new_optimizer_steps=log['new_optimizer_steps'],
                    inherited_parameter_steps=log['inherited_parameter_steps'],
                    parameter_lineage_steps=log['parameter_lineage_steps'], half_source_path=half_path)
                path = folder / f'{name.lower()}_model.json'
                save(path, payload)
                metadata = dict(hidden=width, budget=settings['budgets'][-1], episode_cutoff=cutoff,
                    family='UNIFORM_SHRINK', mode=mode, path=str(path), half_source_path=half_path,
                    parameter_count=model.parameter_count)
                stage['fit_logs'][name] = log
                stage['model_metadata'][name] = metadata
                new_models.append(dict(training_life=life, method=name, metadata=metadata))
                report['runner_checks']['new_model_statistics_match'] &= all(
                    payload[field] == half[field] for field in ('mean', 'scale', 'uniform_gamma'))
                report['runner_checks']['new_model_fit_metadata_match'] &= (payload['hidden'] == width
                    and payload['checkpoint'] == cutoff and payload['family'] == 'UNIFORM_SHRINK'
                    and payload['optimizer_steps'] == STEPS)
                save(folder / 'construction.json', stage)
                save(directory / 'run.json', report)
                if not all(report['runner_checks'].values()) or not all(log['checks'].values()):
                    raise ValueError('new update model does not match frozen statistics or fit semantics')
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
        raise ValueError('new scoring or retained V106 baseline differs from frozen inputs')
    report.update(status='complete', actual_wall_seconds=perf_counter() - started)
    save(directory / 'run.json', report)
    print(json.dumps(dict(phase='complete', new_models=len(new_models), new_decisions=len(decisions),
        counts=scoring['counts'], seconds=report['actual_wall_seconds'])), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    run(parser.parse_args().output)
