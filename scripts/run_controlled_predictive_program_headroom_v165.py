"""Score frozen local suffix selectors using only paid V164 interventions."""
import argparse
import importlib
import json
from pathlib import Path
import shutil
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from acfqp.science.controlled_predictive_program_headroom_v165 import build_roster, evaluate

SOURCE = ROOT / 'reports/controlled_predictive_supported_program_v164'
OUTPUT = ROOT / 'reports/controlled_predictive_program_headroom_v165'
METADATA = ('generated_candidates.json', 'frozen_programs.json',
            'train_roots.json', 'screening_inputs.json')


def read(path):
    return json.loads(path.read_text())


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def snapshot_code(directory):
    importlib.import_module('acfqp.science.controlled_predictive_program_headroom_analysis_v165')
    files = {Path(__file__).resolve(), ROOT / 'specs/PROGRAM_HEADROOM_V165.md',
             ROOT / 'reports/v165_runtime_tmp/run_stage.py'}
    files.update((ROOT / 'tests').glob('*headroom*v165.py'))
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
    source_run = read(SOURCE / 'run.json')
    source_analysis = read(SOURCE / 'analysis.json')
    if not (source_run['status'] == 'complete' and source_analysis['complete']
            and source_analysis['primary_complete']):
        raise ValueError('V164 audited completion required')
    metadata = {name: read(SOURCE / name) for name in METADATA}
    screen = metadata['screening_inputs.json']
    if screen['roots'] != metadata['train_roots.json'] or screen['candidates'] != metadata['generated_candidates.json']:
        raise ValueError('V164 screening metadata differs from frozen roots/candidates')
    roster = build_roster(metadata['generated_candidates.json'], metadata['frozen_programs.json'],
                          metadata['train_roots.json'], screen['branch_roster'])
    save(directory / 'frozen_metadata.json', metadata)
    save(directory / 'retained_roster.json', roster)
    prior_capsule = read(SOURCE / 'source_capsule.json')
    capsule = dict(schema='acfqp.program_headroom.v165.source', source=str(SOURCE),
        audited_run_ref=str(SOURCE / 'run.json'), audited_analysis_ref=str(SOURCE / 'analysis.json'),
        inherited_v164_environment_samples=source_analysis['costs']['new_environment_samples'],
        inherited_prior_cost_refs=prior_capsule['cost_refs'],
        additional_cost_refs=[dict(path=str(SOURCE / 'analysis.json'), fields=['costs']),
            *[dict(path=str(ROOT / f'reports/v164_runtime_tmp/{name}_checks.json'), fields=['attempts'])
              for name in ('core', 'runner', 'analyzer')]],
        this_stage_test_refs=[str(ROOT / f'reports/v165_runtime_tmp/{name}_checks.json')
                              for name in ('core', 'analyzer')],
        inherited_physical_replay='V164 settled audit; not repeated',
        metadata_inspection='Schema inspection exposed source frozen program scores; predicate coverage inspection loaded compact records. Neither terminal fitting/scoring nor donor selection used terminal returns before this freeze.')
    save(directory / 'source_capsule.json', capsule)
    data = dict(schema='acfqp.program_headroom.v165.run', status='roster_frozen',
        protocol=str(ROOT / 'specs/PROGRAM_HEADROOM_V165.md'), source=str(SOURCE),
        phase_order=['ROSTER_FROZEN'], expected_cells=8, expected_roots=32,
        expected_triplets=128, selection_suffixes=[0, 1], scoring_suffixes=[2, 3],
        primary='ROOT-BIT_REFIT', sensitivity='reverse split fixed before labels',
        new_environment_samples=0, physical_games=0, physical_branches=0,
        new_parameter_updates=0, frozen_source_files=snapshot_code(directory))
    save(directory / 'run.json', data)
    if not roster['complete']:
        data.update(status='incomplete_metadata', seconds=perf_counter() - started)
        save(directory / 'run.json', data)
        return
    # This execution opens raw labels after the protocol, roster and snapshot exist.
    wanted = {branch['branch_id'] for cell in roster['cells']
              for root in cell['roots'] for branch in root['branches']}
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
        physical_games=0, physical_branches=0, checkpoint_loads=0, native_compilations=0,
        compact_source_files_read=4, compact_source_bytes_read=input_bytes,
        compact_source_rows_read=all_rows, retained_rows=len(retained),
        logical_work=result['logical_work'],
        inherited_v164_environment_samples=capsule['inherited_v164_environment_samples'],
        inherited_cost_refs=capsule['additional_cost_refs'] + capsule['inherited_prior_cost_refs'],
        test_refs=capsule['this_stage_test_refs'])
    save(directory / 'result.json', result)
    data.update(status='complete' if result['complete'] else 'incomplete_outcomes',
                phase_order=['ROSTER_FROZEN', 'RETAINED_LABELS_LOADED', 'SPLITS_SCORED'],
                seconds=perf_counter() - started, retained_rows=len(retained))
    save(directory / 'run.json', data)
    print(json.dumps(dict(status=data['status'], seconds=data['seconds'],
                          new_environment_samples=0, retained_rows=len(retained))), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    run(parser.parse_args().output)
