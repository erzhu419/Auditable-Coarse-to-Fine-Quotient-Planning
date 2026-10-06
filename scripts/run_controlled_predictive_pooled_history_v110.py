"""Pool three source histories and evaluate only the excluded fourth history."""
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
from acfqp.science.controlled_predictive_pooled_data_v110 import load_bank, pool_fold
from acfqp.science.controlled_predictive_pooled_history_v110 import fit_stage, STEPS
from acfqp.science.controlled_predictive_capacity_ranking_v103 import CandidateModel
from acfqp.science.controlled_predictive_crossed_scoring_v106 import _event

TRAIN_SOURCE = ROOT / 'reports/controlled_predictive_fresh_ranking_v105'
SOURCE = ROOT / 'reports/controlled_predictive_frozen_head_v109'
LIVES, WIDTHS, STAGES = (11, 12, 13, 14), (4, 16), ('HALF', 'FULL')
METHODS = ('H2_ONLY',) + tuple(f'POOLED_H{h}_{stage}' for h in WIDTHS for stage in STAGES)
CONTRASTS = tuple(pair for h in WIDTHS for pair in (
    (f'POOLED_H{h}_FULL', f'POOLED_H{h}_HALF'),
    (f'POOLED_H{h}_FULL', 'H2_ONLY'), (f'POOLED_H{h}_HALF', 'H2_ONLY')))


def save(path, value):
    path.write_text(json.dumps(value, allow_nan=False, separators=(',', ':')) + '\n')


def snapshot(directory):
    importlib.import_module('scripts.analyze_controlled_predictive_pooled_history_v110')
    paths = {Path(__file__).resolve(), ROOT / 'specs/POOLED_HISTORY_V110.md'}
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


def acquisition_accounting(allocations):
    histories = []
    for row in sorted(allocations, key=lambda item: item['life']):
        stages, partitions = [], {}
        cumulative = 0
        for stage in row['construction']:
            acquisition = stage['acquisition']
            cumulative += acquisition['used_transitions']
            for role, amounts in acquisition['cost_partition'].items():
                part = partitions.setdefault(role, Counter())
                part.update(amounts)
            stages.append(dict(budget=stage['budget'], used_transitions=acquisition['used_transitions'],
                cumulative_transitions=cumulative, cost_partition=acquisition['cost_partition']))
        histories.append(dict(life=row['life'], half_transitions=stages[0]['cumulative_transitions'],
            full_transitions=cumulative, stages=stages, cost_partition={k: dict(v) for k, v in partitions.items()}))
    folds = [dict(heldout_life=target, source_lives=[row['life'] for row in histories if row['life'] != target],
        half_transitions=sum(row['half_transitions'] for row in histories if row['life'] != target),
        full_transitions=sum(row['full_transitions'] for row in histories if row['life'] != target)) for target in LIVES]
    return dict(unique_source_histories=[row['life'] for row in histories],
        unique_inherited_training_transitions=sum(row['full_transitions'] for row in histories),
        per_history=histories, per_fold=folds,
        scope='Reused acquisition subset of V105 total work, including diagnostic and unincorporated costs; '
            'overlapping source folds do not incur new draws or multiply physical acquisition.')


def score_models(models, roots):
    started = perf_counter()
    decisions = []
    counts = Counter(model_payloads_loaded=0, model_root_scores=0, neural_candidate_predictions=0,
        neural_hidden_activations=0, new_environment_transitions=0, new_synthetic_transitions=0,
        neural_model_fits=0, optimizer_steps=0, model_prefix_trajectories=0)
    checks = dict(model_metadata_match=True, only_excluded_history_scored=True, scoring_roster_complete=True)
    for row in models:
        metadata = row['metadata']
        payload = json.loads(Path(metadata['path']).read_text())
        model = CandidateModel.from_payload(payload)
        update = payload['update']
        counts['model_payloads_loaded'] += 1
        checks['model_metadata_match'] &= (model.hidden == metadata['hidden']
            and model.checkpoint == metadata['checkpoint'] and model.family == metadata['family']
            and update['heldout_life'] == row['heldout_life'] == metadata['heldout_life']
            and update['source_lives'] == metadata['source_lives'] and update['stage'] == metadata['stage']
            and row['heldout_life'] not in update['source_lives'])
        if not checks['model_metadata_match']:
            break
        for root in roots:
            if root['life'] != row['heldout_life']:
                continue
            checks['only_excluded_history_scored'] &= root['life'] not in update['source_lives']
            event = _event(model.score_candidates(root['features'], counts))
            decisions.append(dict(root_id=root['root_id'], heldout_life=row['heldout_life'], method=row['method'], event=event))
            counts['model_root_scores'] += 1
    expected = sum(sum(root['life'] == row['heldout_life'] for root in roots) for row in models)
    checks['scoring_roster_complete'] = len(decisions) == expected
    return decisions, dict(counts=dict(counts), checks=checks, seconds=perf_counter() - started)


def run(directory):
    started = perf_counter()
    directory.mkdir(parents=True, exist_ok=False)
    snapshot(directory)
    previous = json.loads((SOURCE / 'run.json').read_text())
    prior_analysis = json.loads((SOURCE / 'analysis.json').read_text())
    source = json.loads((TRAIN_SOURCE / 'run.json').read_text())
    if previous['status'] != 'complete' or source['status'] != 'complete' or not prior_analysis['primary_complete']:
        raise ValueError('pooled history comparison requires complete retained training and V109 results')
    settings = dict(previous['settings'], lifecycles=list(LIVES), widths=list(WIDTHS), methods=list(METHODS),
        contrasts=CONTRASTS, optimizer_steps=STEPS, update_modes=list(STAGES),
        new_neural_model_fits=16, expected_new_model_root_decisions=256, evaluation_scope='excluded_history_only')
    settings.pop('crossed_model_count', None)
    settings.pop('training_lifecycles', None)
    inherited = {f'V{v}': previous[f'inherited_v{v}_work'] for v in range(105, 109)}
    inherited['V109'] = prior_analysis['actual_executed_work']
    report = dict(schema='acfqp.pooled_history.v110', status='running', platform=platform.platform(),
        executable=sys.executable, python=sys.version, source=str(SOURCE), training_source=str(TRAIN_SOURCE),
        settings=settings, inherited_work=inherited, cohort=deepcopy(previous['cohort']),
        acquisition_accounting=acquisition_accounting(source['allocations']), bank_log=None, folds=[],
        models=[], decisions=[], scoring_log=None, runner_checks=dict(source_history_roster=True,
            source_target_exclusion=True, full_statistics_frozen=True, full_start_matches_half=True,
            model_fit_metadata_match=True, cached_cohort_exact=True))
    save(directory / 'run.json', report)
    bank, bank_log = load_bank(TRAIN_SOURCE, source['allocations'])
    report['bank_log'] = bank_log
    report['runner_checks']['source_history_roster'] = sorted(bank) == list(LIVES)
    save(directory / 'run.json', report)
    if not report['runner_checks']['source_history_roster'] or not all(bank_log['checks'].values()):
        raise ValueError('original source bank is incomplete')
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
            raise ValueError('excluded history entered a source pool')
        for width in WIDTHS:
            half = None
            for stage in STAGES:
                method = f'POOLED_H{width}_{stage}'
                model, log = fit_stage(records, width, stage, sources, half_payload=half)
                payload = model.to_payload()
                payload['update'] = dict(stage=stage, source_lives=sources, heldout_life=target,
                    statistics_roster=log['statistics_roster'], training_roster=log['training_roster'],
                    optimizer_state=log['optimizer_state'], new_optimizer_steps=log['new_optimizer_steps'],
                    inherited_parameter_steps=log['inherited_parameter_steps'], parameter_lineage_steps=log['parameter_lineage_steps'])
                path = folder / f'{method.lower()}_model.json'
                save(path, payload)
                metadata = dict(hidden=width, stage=stage, family='UNIFORM_SHRINK', budget=model.checkpoint,
                    checkpoint=model.checkpoint, episode_cutoff=model.checkpoint, source_lives=sources, heldout_life=target, path=str(path),
                    parameter_count=model.parameter_count)
                fold['fit_logs'][method] = log
                fold['model_metadata'][method] = metadata
                report['models'].append(dict(heldout_life=target, method=method, metadata=metadata))
                report['runner_checks']['model_fit_metadata_match'] &= (payload['hidden'] == width
                    and payload['checkpoint'] == (256000 if stage == 'HALF' else 512000)
                    and payload['family'] == 'UNIFORM_SHRINK' and payload['optimizer_steps'] == STEPS
                    and log['source_lives'] == sources and log['stage'] == stage)
                if stage == 'FULL':
                    report['runner_checks']['full_statistics_frozen'] &= all(payload[key] == half[key]
                        for key in ('mean', 'scale', 'uniform_gamma'))
                    report['runner_checks']['full_start_matches_half'] &= (log['initialization'] == 'half_parameters'
                        and log['inherited_parameter_steps'] == half['optimizer_steps'])
                else:
                    half = payload
                save(folder / 'construction.json', fold)
                save(directory / 'run.json', report)
                if not all(log['checks'].values()) or not all(report['runner_checks'].values()):
                    raise ValueError('pooled model differs from its frozen data or update semantics')
        print(json.dumps(dict(phase='fold_complete', heldout_life=target, source_lives=sources,
            half_training_roots=data['half']['training_roots'], full_training_roots=data['full']['training_roots'])), flush=True)
    decisions, scoring = score_models(report['models'], report['cohort']['roots'])
    report['decisions'], report['scoring_log'] = decisions, scoring
    report['runner_checks']['cached_cohort_exact'] = report['cohort'] == previous['cohort']
    report['actual_wall_seconds'] = perf_counter() - started
    save(directory / 'run.json', report)
    if not all(report['runner_checks'].values()) or not all(scoring['checks'].values()):
        raise ValueError('pooled excluded-history scoring is incomplete')
    report.update(status='complete', actual_wall_seconds=perf_counter() - started)
    save(directory / 'run.json', report)
    print(json.dumps(dict(phase='complete', models=len(report['models']), decisions=len(decisions),
        counts=scoring['counts'], seconds=report['actual_wall_seconds'])), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    run(parser.parse_args().output)
