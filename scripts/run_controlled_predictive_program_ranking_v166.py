"""Decompose same-program rankings from paid V164 compact interventions."""
import argparse
import importlib
import json
from pathlib import Path
import shutil
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from acfqp.science.controlled_predictive_program_ranking_v166 import build_roster, evaluate

SOURCE = ROOT / 'reports/controlled_predictive_supported_program_v164'
PRIOR = ROOT / 'reports/controlled_predictive_program_headroom_v165'
OUTPUT = ROOT / 'reports/controlled_predictive_program_ranking_v166'


def read(path):
    return json.loads(path.read_text())


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def snapshot_code(directory):
    importlib.import_module('acfqp.science.controlled_predictive_program_ranking_analysis_v166')
    files = {Path(__file__).resolve(), ROOT / 'specs/PROGRAM_RANKING_V166.md',
             ROOT / 'reports/v166_runtime_tmp/run_stage.py'}
    files.update((ROOT / 'tests').glob('*program_ranking*v166.py'))
    for module in list(sys.modules.values()):
        name = getattr(module, '__file__', None)
        if name:
            path = Path(name).resolve()
            if path.is_relative_to(ROOT / 'src') or path.is_relative_to(ROOT / 'scripts'):
                files.add(path)
    for path in sorted(files):
        target = directory / 'source' / path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
    return len(files)


def run(directory=OUTPUT):
    started = perf_counter()
    directory = directory.resolve()
    directory.mkdir(parents=True, exist_ok=False)
    source_run, source_analysis = read(SOURCE / 'run.json'), read(SOURCE / 'analysis.json')
    prior_run, prior_analysis = read(PRIOR / 'run.json'), read(PRIOR / 'analysis.json')
    if not (source_run['status'] == 'complete' and source_analysis['complete']
            and source_analysis['primary_complete'] and prior_run['status'] == 'complete'
            and prior_analysis['valid']):
        raise ValueError('Audited V164/V165 completion required')
    metadata = read(PRIOR / 'frozen_metadata.json')
    screen = metadata['screening_inputs.json']
    if screen['roots'] != metadata['train_roots.json'] or screen['candidates'] != metadata['generated_candidates.json']:
        raise ValueError('Frozen screening roots/candidates differ')
    roster = build_roster(metadata['generated_candidates.json'], metadata['frozen_programs.json'],
                          metadata['train_roots.json'], screen['branch_roster'])
    save(directory / 'frozen_metadata.json', metadata)
    save(directory / 'retained_roster.json', roster)
    prior_capsule = read(PRIOR / 'source_capsule.json')
    capsule = dict(schema='acfqp.program_ranking.v166.source', source=str(SOURCE),
        audited_v164_analysis_ref=str(SOURCE / 'analysis.json'),
        audited_v165_analysis_ref=str(PRIOR / 'analysis.json'),
        inherited_v164_environment_samples=source_analysis['costs']['new_environment_samples'],
        inherited_cost_refs=prior_capsule['additional_cost_refs'] + prior_capsule['inherited_prior_cost_refs']
            + [dict(path=str(PRIOR / 'result.json'), fields=['costs'])],
        prior_runtime_ref=str(ROOT / 'reports/v165_runtime_tmp/stage_checks.json'),
        test_refs=[str(ROOT / f'reports/v166_runtime_tmp/{name}_checks.json') for name in ('core', 'analyzer')],
        previously_inspected_subset='V165 selected candidates, 32 semantic roots and 128 triplets; retrospective routing, not independent confirmation',
        inherited_physical_replay='V164 physical audit settled; not repeated')
    save(directory / 'source_capsule.json', capsule)
    data = dict(schema='acfqp.program_ranking.v166.run', status='roster_frozen',
        phase_order=['ROSTER_FROZEN'], protocol=str(ROOT / 'specs/PROGRAM_RANKING_V166.md'),
        source=str(SOURCE), expected_strata=3, expected_semantic_roots=48,
        expected_physical_roots=32, expected_triplets=192, expected_unique_rows=512,
        groups=dict(half01=[0, 1], half23=[2, 3], full03=[0, 1, 2, 3]),
        new_environment_samples=0, new_parameter_updates=0,
        frozen_source_files=snapshot_code(directory))
    save(directory / 'run.json', data)
    if not roster['complete']:
        data.update(status='incomplete_metadata', seconds=perf_counter() - started)
        save(directory / 'run.json', data)
        return
    wanted = {branch['branch_id'] for stratum in roster['strata']
              for history in stratum['histories'] for root in history['roots']
              for branch in root['branches']}
    retained, all_rows, input_bytes = [], 0, 0
    for life in range(4):
        path = SOURCE / f'screening/life_{life}/outcomes.json'
        rows = read(path)
        all_rows += len(rows)
        input_bytes += path.stat().st_size
        retained.extend(row for row in rows if row['branch_id'] in wanted)
    save(directory / 'retained_interventions.json', retained)
    result = evaluate(roster, retained)
    result['costs'] = dict(new_environment_samples=0, new_parameter_updates=0,
        new_symbolic_rule_fits=0, physical_games=0, physical_branches=0,
        checkpoint_loads=0, native_compilations=0, compact_source_files_read=4,
        compact_source_bytes_read=input_bytes, compact_source_rows_read=all_rows,
        unique_retained_rows=len(retained), logical_work=result['logical_work'],
        inherited_v164_environment_samples=capsule['inherited_v164_environment_samples'],
        inherited_cost_refs=capsule['inherited_cost_refs'], test_refs=capsule['test_refs'])
    save(directory / 'result.json', result)
    data.update(status='complete' if result['complete'] else 'incomplete_outcomes',
        phase_order=['ROSTER_FROZEN', 'RETAINED_LABELS_LOADED', 'RANKS_DECOMPOSED'],
        seconds=perf_counter() - started, unique_retained_rows=len(retained))
    save(directory / 'run.json', data)
    print(json.dumps(dict(status=data['status'], seconds=data['seconds'],
                          new_environment_samples=0, unique_retained_rows=len(retained))), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    run(parser.parse_args().output)
