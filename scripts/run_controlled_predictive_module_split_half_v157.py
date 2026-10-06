"""Freeze and evaluate root-local selectors on opposite retained suffix halves."""
import argparse
from copy import deepcopy
import gzip
import json
from pathlib import Path
import shutil
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from acfqp.science.controlled_predictive_module_split_half_v157 import (
    build_pairs, build_selection_rows, summarize)

SOURCE = ROOT / 'reports/controlled_predictive_module_semantics_v156'
BRANCH_SOURCE = ROOT / 'reports/controlled_predictive_module_diagnosis_v153'
HALVES = {'A': list(range(8)), 'B': list(range(8, 16))}
OUTPUT_REFS = dict(outcomes='retained_outcomes.json', pairs='paired_outcomes.json',
                   selections='selection_rows.json', summary='summary.json')


def read(path):
    return json.loads(Path(path).read_text())


def save(path, data):
    Path(path).write_text(json.dumps(data, indent=2, allow_nan=False) + '\n')


def settings():
    return dict(lifecycles=[0, 1, 2, 3], queries=['risk1', 'risk8'],
        source_methods=['H2', 'LEARN8'], slots=[0, 1, 2, 3], roots=64,
        suffixes_per_root=16, modes=['H_H2', 'M_H2', 'H_GATE', 'M_GATE'],
        halves=deepcopy(HALVES), directions=['A_to_B', 'B_to_A'],
        selection_targets=['H2', 'GATE'], evaluation_targets=['H2', 'GATE'],
        primary='GATE-selected heldout GATE utility gain versus OLD; both directions and equal average',
        secondary='H2 target, cross-target outcomes, source/history strata, always reject/accept and apparent gains',
        selector='strict positive train-half paired utility mean; zero rejects',
        weighting='equal roots within history, then equal histories; average both directions per root; all roots retained',
        uncertainty='descriptive only; opposite-half evaluation, reused halves and previously inspected outcomes; no independent-fold CI',
        new_environment_samples=0, native_planner_calls=0, model_fits=0,
        accounting='physical retained acquisition 2017530 transitions counted once; all selectors use full retained pool',
        decision='stable opposite-half gain supports more independent roots; unstable sign or gains prioritize label precision')


def extract_source():
    source = read(SOURCE / 'source_capsule.json')
    latest_run, latest_analysis = read(SOURCE / 'run.json'), read(SOURCE / 'analysis.json')
    branch_run, branch_analysis = read(BRANCH_SOURCE / 'run.json'), read(BRANCH_SOURCE / 'analysis.json')
    if not all((latest_run['status'] == 'complete', latest_analysis['complete'],
                latest_analysis['primary_complete'], branch_run['status'] == 'complete',
                branch_analysis['complete'], branch_analysis['primary_complete'])):
        raise ValueError('audited V153 and V156 completion is required')
    frozen = read(BRANCH_SOURCE / 'frozen_inputs.json')
    roots = frozen['roots']
    expected = {f'{life}:{query}:{method}:{slot}' for life in range(4)
                for query in ('risk1', 'risk8') for method in ('H2', 'LEARN8') for slot in range(4)}
    if len(roots) != 64 or {r['root_id'] for r in roots} != expected or roots != source['roots']:
        raise ValueError('V153/V156 root roster differs')
    return dict(schema='acfqp.module_split_half.v157.source',
        source_run_ref=str(SOURCE / 'run.json'), source_analysis_ref=str(SOURCE / 'analysis.json'),
        source_capsule_ref=str(SOURCE / 'source_capsule.json'),
        branch_run_ref=str(BRANCH_SOURCE / 'run.json'), branch_analysis_ref=str(BRANCH_SOURCE / 'analysis.json'),
        branch_frozen_ref=str(BRANCH_SOURCE / 'frozen_inputs.json'),
        roots=deepcopy(roots), branch_roster=deepcopy(frozen['branch_roster']),
        examples=deepcopy(source['examples']),
        source_traces=[dict(life=x['life'], path=str(BRANCH_SOURCE / x['branch_trace']))
                       for x in branch_run['lifecycles']],
        retained_training_cost=deepcopy(source['retained_training_cost']),
        cost_refs=deepcopy(source['cost_refs']) + [dict(path=str(SOURCE / 'analysis.json'), fields=['costs'])] +
            [dict(path=str(ROOT / f'reports/v156_runtime_tmp/{name}_checks.json'), fields=['attempts'])
             for name in ('core', 'runner', 'metrics', 'analyzer')])


def extract_outcomes(capsule):
    started = perf_counter()
    outcomes, transitions = [], 0
    for trace in capsule['source_traces']:
        with gzip.open(trace['path'], 'rt') as stream:
            for line in stream:
                row = json.loads(line)
                if row['life'] != trace['life']:
                    raise ValueError('branch stored under wrong history')
                result = row['result']
                outcomes.append(dict(**{k: row[k] for k in ('branch_id', 'root_id', 'life', 'query',
                    'source_method', 'slot', 'suffix', 'mode', 'seed', 'root_board')},
                    **{k: result[k] for k in ('score', 'steps', 'status', 'components')}))
                transitions += result['steps']
    return outcomes, dict(rows=len(outcomes), retained_environment_transitions=transitions,
        raw_trace_files_read=len(capsule['source_traces']), new_environment_samples=0,
        native_planner_calls=0, model_fits=0, seconds=perf_counter() - started)


def snapshot_code(directory):
    files = [Path(__file__).resolve(),
        ROOT / 'src/acfqp/science/controlled_predictive_module_split_half_v157.py',
        ROOT / 'scripts/analyze_controlled_predictive_module_split_half_v157.py',
        ROOT / 'specs/MODULE_SPLIT_HALF_V157.md', ROOT / 'reports/v157_runtime_tmp/run_stage.py']
    files += sorted((ROOT / 'tests').glob('*module_split_half*v157.py'))
    for path in files:
        target = directory / 'source' / path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)


def run(directory):
    started = perf_counter()
    directory = directory.resolve()
    directory.mkdir(parents=True, exist_ok=False)
    capsule = extract_source()
    save(directory / 'source_capsule.json', capsule)
    snapshot_code(directory)
    data = dict(schema='acfqp.module_split_half.v157.run', status='frozen', settings=settings(),
        halves=deepcopy(HALVES), root_ids=[r['root_id'] for r in capsule['roots']],
        output_refs=deepcopy(OUTPUT_REFS), inherited_cost_refs=capsule['cost_refs'])
    save(directory / 'frozen_inputs.json', data)
    save(directory / 'run.json', data)
    outcomes, data['extraction'] = extract_outcomes(capsule)
    save(directory / OUTPUT_REFS['outcomes'], outcomes)
    arithmetic_started = perf_counter()
    pairs = build_pairs(capsule['roots'], outcomes)
    selections = build_selection_rows(capsule['roots'], pairs)
    summary = summarize(selections)
    for key, value in (('pairs', pairs), ('selections', selections), ('summary', summary)):
        save(directory / OUTPUT_REFS[key], value)
    data.update(status='complete', arithmetic_seconds=perf_counter() - arithmetic_started,
        pairs=len(pairs), selection_rows=len(selections), summary_groups=len(summary),
        seconds=perf_counter() - started)
    save(directory / 'run.json', data)
    print(dict(status=data['status'], pairs=len(pairs), selection_rows=len(selections), seconds=data['seconds']), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'reports/controlled_predictive_module_split_half_v157')
    run(parser.parse_args().output)
