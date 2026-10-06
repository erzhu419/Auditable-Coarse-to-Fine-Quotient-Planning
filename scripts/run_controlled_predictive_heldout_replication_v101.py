"""Independent terminal suffixes on fixed V100 heldout roots and frozen models."""
import argparse
from collections import Counter
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
from acfqp.science.controlled_predictive_heldout_cohort_v101 import load_cohort
from acfqp.science.controlled_predictive_fragment_experience_v83 import sample_root
from acfqp.science.controlled_predictive_fragments_v83 import OPTIONS, QUERIES
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics

SOURCE = ROOT / 'reports/controlled_predictive_query_ranking_v100'
REPLICAS, BLOCK_SIZE, LIFE_BASE, MAX_STEPS, WORKERS = 32, 16, 101000, 2000, 4


def save(path, value):
    path.write_text(json.dumps(value, allow_nan=False, separators=(',', ':')) + '\n')


def audit_reference(root, raw, log, replicas):
    roster = {(row['option'], row['replica']) for row in raw}
    checks = dict(trajectory_roster_complete=len(raw) == len(roster) == replicas * len(OPTIONS)
        and roster == {(option, replica) for option in OPTIONS for replica in range(replicas)},
        root_boards_match=True, paired_fresh_streams=True, committed_fragments_match=True,
        executed_costs_match=True)
    ground, planning, outcomes = Counter(), Counter(), Counter()
    for row in raw:
        game, controller = row['game'], row['controller']
        steps, option = game['steps_count'], row['option']
        seed = (8310000000 + (LIFE_BASE + root['life']) * 10000000
                + tuple(QUERIES).index(root['query']) * 100000 + root['episode'] * 100 + row['replica'])
        checks['root_boards_match'] &= game['initial_board'] == root['board']
        checks['paired_fresh_streams'] &= (row['env_seed'] == game['seed'] == seed
            and row['model_seed'] == seed + 1000000000000
            and game['work'].get('environment_random_draws', 0) == 2 * steps
            and row['planning_counts'].get('model_uniform_draws', 0) == 4 * steps)
        duration = 0 if option == 'H2' else int(option.split('_')[1])
        checks['committed_fragments_match'] &= (controller['initiation_step'] == 0
            and controller['selected_option'] == option and len(controller['events']) == 1
            and controller['fragment_actions'] == min(duration, steps))
        ground.update(game['work']); planning.update(row['planning_counts']); outcomes[game['status']] += 1
    checks['executed_costs_match'] &= (ground == Counter(log['ground_work'])
        and planning == Counter(log['planning_counts']) and outcomes == Counter(log['outcomes'])
        and log['trajectories'] == len(raw))
    return checks


def reference_job(root, directory, payload):
    started = perf_counter()
    folder = directory / 'references' / root['id']
    folder.mkdir(parents=True)
    rule = LearnedDynamics.from_payload(payload)
    _, raw, log = sample_root(root, rule, LIFE_BASE + root['life'], replicas=REPLICAS, max_steps=MAX_STEPS)
    checks = audit_reference(root, raw, log, REPLICAS)
    with gzip.open(folder / 'games.jsonl.gz', 'wt') as handle:
        for row in raw:
            handle.write(json.dumps(dict(root_id=root['id'], block='A' if row['replica'] < BLOCK_SIZE else 'B',
                **row), allow_nan=False, separators=(',', ':')) + '\n')
    record = dict(root_id=root['id'], log=log, checks=checks, seconds=perf_counter() - started)
    save(folder / 'reference.json', record)
    if not all(checks.values()):
        raise ValueError(f"reference execution mismatch at {root['id']}: {checks}")
    return record


def snapshot(directory):
    paths = {str(p.relative_to(SOURCE / 'source')) for p in (SOURCE / 'source').rglob('*') if p.is_file()}
    paths.update(('scripts/run_controlled_predictive_heldout_replication_v101.py',
        'scripts/analyze_controlled_predictive_heldout_order_v101.py',
        'src/acfqp/science/controlled_predictive_heldout_cohort_v101.py',
        'specs/HELDOUT_ORDER_REPLICATION_V101.md'))
    for relative in sorted(paths):
        target = directory / 'source' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)


def run(directory):
    started = perf_counter()
    directory.mkdir(parents=True, exist_ok=False)
    snapshot(directory)
    payload = json.loads((SOURCE / 'supplied_dynamics.json').read_text())
    save(directory / 'supplied_dynamics.json', payload)
    roots, log = load_cohort(SOURCE, directory)
    cohort = dict(roots=roots, log=log)
    save(directory / 'cohort.json', cohort)
    report = dict(schema='acfqp.heldout_replication.v101', status='running',
        platform=platform.platform(), executable=sys.executable, python=sys.version,
        settings=dict(lifecycles=[9,10], allocations=[8,4], queries=QUERIES, options=OPTIONS,
            replicas=REPLICAS, block_size=BLOCK_SIZE, reference_life_base=LIFE_BASE,
            max_steps=MAX_STEPS, workers=WORKERS, source=str(SOURCE)),
        cohort=cohort, references=[], actual_wall_seconds=perf_counter() - started)
    save(directory / 'run.json', report)
    print(json.dumps(dict(phase='cohort_frozen', roots=len(roots), log=log)), flush=True)
    with ProcessPoolExecutor(max_workers=WORKERS) as pool:
        futures = [pool.submit(reference_job, root, directory, payload) for root in roots]
        for future in as_completed(futures):
            record = future.result()
            report['references'].append(record)
            report['references'].sort(key=lambda r: r['root_id'])
            report['actual_wall_seconds'] = perf_counter() - started
            save(directory / 'run.json', report)
            print(json.dumps(dict(phase='reference', root=record['root_id'],
                completed=len(report['references']), censored=record['log']['censored_root'],
                transitions=record['log']['ground_work']['sampled_transitions'])), flush=True)
    report.update(status='complete', actual_wall_seconds=perf_counter() - started)
    save(directory / 'run.json', report)
    print(json.dumps(dict(phase='complete', seconds=report['actual_wall_seconds'])), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    run(parser.parse_args().output)
