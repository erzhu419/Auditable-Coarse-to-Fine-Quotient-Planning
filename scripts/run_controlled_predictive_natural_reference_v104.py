"""Complete V103 natural-root references without changing models or choices."""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import gzip
import json
from pathlib import Path
import platform
import shutil
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'src'))
from acfqp.science.controlled_predictive_natural_cohort_v104 import load_cohort
from acfqp.science.controlled_predictive_reference_suffix_v104 import audit_reference
from acfqp.science.controlled_predictive_fragment_experience_v83 import sample_root
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics

SOURCE = ROOT / 'reports/controlled_predictive_capacity_ranking_v103'
REPLICAS, BLOCK_SIZE, LIFE_BASE, MAX_STEPS, WORKERS = 32, 16, 103000, 2000, 4


def save(path, value):
    path.write_text(json.dumps(value, allow_nan=False, separators=(',', ':')) + '\n')


def pending_roots(roots):
    return [root for root in roots if root['reference_origin'] == 'new']


def reference_job(retained, directory, payload):
    if retained['reference_origin'] != 'new' or retained['inherited_reference'] is not None:
        raise ValueError('only roots without retained references may be sampled')
    started = perf_counter()
    folder = directory / 'references' / retained['id']
    folder.mkdir(parents=True, exist_ok=False)
    root = {field: retained[field] for field in ('life', 'query', 'episode', 'board', 'step', 'source_seed')}
    rule = LearnedDynamics.from_payload(payload)
    _, raw, log = sample_root(root, rule, LIFE_BASE + root['life'], replicas=REPLICAS, max_steps=MAX_STEPS)
    checks = audit_reference(root, raw, log, replicas=REPLICAS, life_base=LIFE_BASE)
    with gzip.open(folder / 'games.jsonl.gz', 'wt') as handle:
        for row in raw:
            handle.write(json.dumps(dict(root_id=retained['id'], block='A' if row['replica'] < BLOCK_SIZE else 'B',
                **row), allow_nan=False, separators=(',', ':')) + '\n')
    record = dict(root_id=retained['id'], log=log, checks=checks, seconds=perf_counter() - started)
    save(folder / 'reference.json', record)
    if not all(checks.values()):
        raise ValueError(f"reference execution mismatch at {retained['id']}: {checks}")
    return record


def snapshot(directory):
    # Preserve the inherited source exactly as it was retained by V103.
    for source in (SOURCE / 'source').rglob('*'):
        if source.is_file():
            target = directory / 'source' / source.relative_to(SOURCE / 'source')
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
    paths = ('scripts/run_controlled_predictive_natural_reference_v104.py',
        'scripts/analyze_controlled_predictive_natural_reference_v104.py',
        'src/acfqp/science/controlled_predictive_natural_cohort_v104.py',
        'src/acfqp/science/controlled_predictive_reference_suffix_v104.py',
        'specs/NATURAL_REFERENCE_V104.md')
    for relative in paths:
        target = directory / 'source' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)


def run(directory):
    started = perf_counter()
    directory.mkdir(parents=True, exist_ok=False)
    snapshot(directory)
    source = json.loads((SOURCE / 'run.json').read_text())
    payload = json.loads((SOURCE / 'supplied_dynamics.json').read_text())
    save(directory / 'supplied_dynamics.json', payload)
    roots, log = load_cohort(SOURCE, directory)
    cohort = dict(roots=roots, log=log)
    settings = dict(source['settings'], source=str(SOURCE), reference_replicas=REPLICAS,
        reference_block_size=BLOCK_SIZE, reference_life_base=LIFE_BASE, validation_roots_per_query=8,
        max_steps=MAX_STEPS, workers=WORKERS)
    report = dict(schema='acfqp.natural_reference.v104', status='running',
        platform=platform.platform(), executable=sys.executable, python=sys.version,
        settings=settings, cohort=cohort, references=[], actual_wall_seconds=perf_counter() - started)
    save(directory / 'run.json', report)
    pending = pending_roots(roots)
    print(json.dumps(dict(phase='cohort_frozen', roots=len(roots), new_roots=len(pending),
        inherited_roots=len(roots)-len(pending), recovered_prediction_events=log['counts']['retained_prediction_events'])), flush=True)
    with ProcessPoolExecutor(max_workers=WORKERS) as pool:
        futures = [pool.submit(reference_job, root, directory, payload) for root in pending]
        for future in as_completed(futures):
            record = future.result()
            report['references'].append(record)
            report['references'].sort(key=lambda r: r['root_id'])
            report['actual_wall_seconds'] = perf_counter() - started
            save(directory / 'run.json', report)
            print(json.dumps(dict(phase='reference', root=record['root_id'], completed=len(report['references']),
                censored=record['log']['censored_root'], trajectories=record['log']['trajectories'],
                transitions=record['log']['ground_work']['sampled_transitions'])), flush=True)
    report.update(status='complete', actual_wall_seconds=perf_counter() - started)
    save(directory / 'run.json', report)
    print(json.dumps(dict(phase='complete', seconds=report['actual_wall_seconds'])), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    run(parser.parse_args().output)
