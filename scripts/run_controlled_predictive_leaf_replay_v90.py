"""Replay fixed enabled decisions and same-leaf training controls on fresh suffixes."""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
import gzip
import json
from pathlib import Path
import platform
import shutil
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from acfqp.science.controlled_predictive_leaf_cohort_v90 import build_cohort
from acfqp.science.controlled_predictive_leaf_replay_v90 import sample_pair_root
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics

SOURCE = ROOT / 'reports/controlled_predictive_evidence_resampling_v89'
REPLICAS = 64
MAX_STEPS = 2000
WORKERS = 3


def save(path, value):
    path.write_text(json.dumps(value, allow_nan=False, separators=(',', ':')) + '\n')


def sampling_order(cohort):
    roots = {row['id']: row for kind in ('targets', 'controls') for row in cohort[kind]}
    ordered = []
    for group in cohort['groups']:
        targets, training = group['target_ids'], group['training_ids']
        for index in range(max(len(targets), len(training))):
            for ids in (targets, training):
                if index < len(ids):
                    ordered.append(deepcopy(roots[ids[index]]))
    for index, root in enumerate(ordered):
        root.update(sample_index=index, seed_base=110_000_000_000 + index * 10000)
    return ordered


def sample_and_save(root, folder, payload, replicas, max_steps):
    started = perf_counter()
    directory = folder / root['id']
    directory.mkdir()
    tick = perf_counter()
    rule = LearnedDynamics.from_payload(payload)
    load_seconds = perf_counter() - tick
    raw, record = sample_pair_root(root, rule, root['seed_base'], replicas=replicas, max_steps=max_steps)
    export_tick = perf_counter()
    with gzip.open(directory / 'trajectories.jsonl.gz', 'wt') as handle:
        for row in raw:
            handle.write(json.dumps(row, allow_nan=False, separators=(',', ':')) + '\n')
    record.update(root=root, seed_base=root['seed_base'], dynamics_load_seconds=load_seconds,
        export_seconds=perf_counter() - export_tick, actual_wall_seconds=perf_counter() - started)
    save(directory / 'root.json', record)
    print(json.dumps(dict(phase='root_complete', root_id=root['id'], kind=root['kind'], life=root['life'],
        complete_pairs=record['complete_pairs'], requested_replicas=replicas,
        transitions=record['ground_work'].get('sampled_transitions', 0))), flush=True)
    return record


def snapshot(directory):
    paths = ['scripts/run_controlled_predictive_leaf_replay_v90.py',
        'scripts/analyze_controlled_predictive_leaf_replay_v90.py',
        'specs/LEAF_REPLAY_FRAGMENTS_V90.md']
    paths += [f'src/acfqp/science/controlled_predictive_{name}_v{version}.py' for name, version in (
        ('leaf_cohort', 90), ('leaf_replay', 90), ('evidence_fragments', 88), ('joint_fragments', 84),
        ('fragments', 83), ('fragment_experience', 83), ('policy_advantage', 81),
        ('decision_experience', 78), ('lifelong', 77), ('lifelong_experience', 77),
        ('lifelong_planner', 77), ('relational_dynamics', 69), ('effect_contract', 74),
        ('grouped_contract', 73), ('local_contract', 72))]
    paths += ['src/acfqp/domains/standard_2048.py', 'src/acfqp/domains/g2048.py']
    for relative in paths:
        target = directory / 'source' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)


def run(directory):
    started = perf_counter()
    directory.mkdir(parents=True, exist_ok=False)
    snapshot(directory)
    cohort = build_cohort(SOURCE)
    ordered = sampling_order(cohort)
    cohort['sampling_roots'] = ordered
    save(directory / 'cohort.json', cohort)
    for life in sorted({root['life'] for root in ordered}):
        for variant in ('evidence', 'balanced'):
            shutil.copyfile(SOURCE / f'life_{life}' / f'{variant}_selector.json',
                            directory / f'life_{life}_{variant}_selector.json')
    payload = json.loads((SOURCE / 'supplied_dynamics.json').read_text())
    save(directory / 'supplied_dynamics.json', payload)
    previous = json.loads((SOURCE / 'analysis.json').read_text())
    report = dict(schema='acfqp.leaf_replay.v90', status='running', platform=platform.platform(),
        python=sys.version, executable=sys.executable, source=str(SOURCE),
        settings=dict(replicas=REPLICAS, max_steps=MAX_STEPS, workers=WORKERS, new_tree_fits=0,
            new_source_games=0, new_natural_games=0, planned_roots=len(ordered),
            planned_pairs=len(ordered) * REPLICAS, planned_trajectories=len(ordered) * REPLICAS * 2),
        cohort_preparation_seconds=cohort['seconds'],
        inherited=dict(v89_work=previous['actual_executed_work'], acquisition=previous['inherited']), roots=[])
    save(directory / 'run.json', report)
    folder = directory / 'roots'
    folder.mkdir()
    with ProcessPoolExecutor(max_workers=WORKERS) as pool:
        futures = [pool.submit(sample_and_save, root, folder, payload, REPLICAS, MAX_STEPS) for root in ordered]
        for future in as_completed(futures):
            report['roots'].append(future.result())
            report['roots'].sort(key=lambda row: row['root']['sample_index'])
            report['actual_wall_seconds'] = perf_counter() - started
            save(directory / 'run.json', report)
    report.update(status='complete', actual_wall_seconds=perf_counter() - started)
    save(directory / 'run.json', report)
    print(json.dumps(dict(phase='complete', roots=len(report['roots']), seconds=report['actual_wall_seconds'])), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    run(parser.parse_args().output)
