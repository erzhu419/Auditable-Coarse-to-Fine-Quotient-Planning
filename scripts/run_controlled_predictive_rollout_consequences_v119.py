"""Replace fitted leaf consequences while preserving V118's planning interface."""
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
import argparse
import gzip
import importlib
import json
from pathlib import Path
import platform
import random
import shutil
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / 'src'))
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics
from acfqp.science.controlled_predictive_regime_memory_v115 import SpawnMemory
from acfqp.science.controlled_predictive_regime_experience_v115 import run_episode
from acfqp.science import controlled_predictive_lifelong_planner_v77 as planner
from scripts.run_controlled_predictive_consolidation_v117 import bound_model, save, append, QUERIES

SOURCE = ROOT / 'reports/controlled_predictive_utility_consolidation_v118'
METHODS = ('H2_ONLY', 'TREE', 'MC4', 'MC16')
LIVES, REPLICAS, MAX_STEPS, WORKERS = (0, 1, 2, 3), 2, 2000, 4
BASE, PLANNER_OFFSET, ROLLOUT_OFFSET = 119 * 100_000_000, 50_000_000, 60_000_000


def extract_source(previous, inherited):
    """Whitelist knowledge and source work; never copy outer evidence."""
    if previous['status'] != 'complete':
        raise ValueError('V119 requires completed V118 selection')
    template = LearnedDynamics.from_payload(inherited['supplied_dynamics'])
    old = {life['life']: life for life in inherited['lifecycles']}
    source_counts, fit_counts, validation_counts = Counter(), Counter(), Counter()
    source_planning, utility_planning, utility_predictions, old_selection = (Counter() for _ in range(4))
    router_counts = Counter()
    source_seconds = utility_seconds = 0.
    snapshots = []
    for life in previous['lifecycles']:
        history = old[life['life']]
        phase = life['phases'][-1]
        cp, original = phase['checkpoint'], history['phases'][-1]['checkpoint']
        if phase['name'] != 'A_RETURN' or history['phases'][-1]['name'] != 'A_RETURN':
            raise ValueError('V119 requires A_RETURN checkpoints')
        router = SpawnMemory.from_payload(original['router_payload'])
        snapshots.append(dict(life=life['life'], phase='A_RETURN',
            module_id=router.module_id, rule=router.to_rule(template).to_payload(),
            model=deepcopy(cp['models']['UTILITY_SELECTED']),
            selected_origin=deepcopy(cp['utility_selected_origin']),
            source_choices=[p['checkpoint']['selection']['selected_candidate'] for p in life['phases']]))
        for p in history['phases']:
            for game in p['source_games']:
                source_counts.update(game['environment_counts'])
                source_planning.update(game.get('planning_counts', {}))
                source_seconds += game.get('seconds', 0.)
            for log in p['checkpoint']['fit_logs'].values():
                fit_counts.update(log['counts'])
            for counts in p['checkpoint'].get('source_validation_prediction_counts', {}).values():
                old_selection.update(counts)
        router_counts.update(history.get('final_router', {}).get('counts', {}))
        for p in life['phases']:
            for game in p['checkpoint']['source_validation_games']:
                validation_counts.update(game['result']['environment_counts'])
                utility_planning.update(game['result'].get('planning_counts', {}))
                utility_predictions.update(game['result'].get('prediction_counts', {}))
                utility_seconds += game['result'].get('seconds', 0.)
    if sorted(row['life'] for row in snapshots) != list(LIVES):
        raise ValueError('V119 requires all four source histories')
    return dict(schema='acfqp.rollout_source.v119', snapshots=snapshots,
        inherited_costs=dict(source_environment=dict(source_counts), tree_fitting=dict(fit_counts),
            utility_validation_environment=dict(validation_counts),
            source_planning=dict(source_planning), source_seconds=source_seconds,
            source_router=dict(router_counts), mse_selection_prediction=dict(old_selection),
            utility_validation_planning=dict(utility_planning),
            utility_validation_prediction=dict(utility_predictions), utility_validation_seconds=utility_seconds,
            supplied_dynamics_fit_counts=deepcopy(template.fit_counts),
            scope='V117 source/fit plus V118 selection; old outer evaluation excluded'))


def snapshot(directory):
    importlib.import_module('acfqp.science.controlled_predictive_rollout_consequences_v119')
    importlib.import_module('scripts.analyze_controlled_predictive_rollout_consequences_v119')
    files = {Path(__file__).resolve(), ROOT / 'specs/ROLLOUT_CONSEQUENCES_V119.md',
        ROOT / 'src/acfqp/science/controlled_predictive_rollout_kernel_v119.cpp'}
    for module in list(sys.modules.values()):
        name = getattr(module, '__file__', None)
        if name:
            path = Path(name).resolve()
            if path.is_relative_to(ROOT / 'src') or path.is_relative_to(ROOT / 'scripts'):
                files.add(path)
    files.update((ROOT / 'src/acfqp/science').glob('controlled_predictive_*contract_v7[234].py'))
    for path in files:
        target = directory / 'source' / path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)


def control_game(source, method, query, replica, build_dir):
    from acfqp.science.controlled_predictive_rollout_consequences_v119 import RolloutKnowledge
    seed = BASE + 3_000_000 + source['life'] * 100000 + replica
    rule = LearnedDynamics.from_payload(source['rule'])
    if method == 'H2_ONLY':
        model = None
    elif method == 'TREE':
        model = bound_model(source['model'], source['module_id'])
        if not model.can_route(source['module_id']):
            raise ValueError('frozen selected consequence model has no current module')
    else:
        model = RolloutKnowledge(rule, int(method[2:]), seed + ROLLOUT_OFFSET, build_dir)
    before = deepcopy(source)
    rng, work, decisions = random.Random(seed + PLANNER_OFFSET), Counter(), []
    def act(board, step):
        chosen = planner.choose(board, QUERIES[query], model, rule, rng, depth=2, work=work)
        decisions.append({key: chosen[key] for key in
            ('action', 'value', 'metrics', 'policy', 'branches', 'action_values')})
        return chosen['action']
    game = run_episode(seed, act, .1, MAX_STEPS)
    q = QUERIES[query]
    result = dict(score=game['return_score'], status=game['status'], steps=game['steps_count'],
        utility=q['reward_weight'] * game['return_score'] / 2048
            - q['failure_penalty'] * (game['status'] == 'LOST')
            + q['goal_bonus'] * (game['status'] == 'WON'),
        environment_counts=game['work'], planning_counts=dict(work),
        consequence_counts={} if model is None else dict(model.counts),
        setup_counts=dict(getattr(model, 'setup_counts', {})),
        setup_seconds=getattr(model, 'setup_seconds', 0.),
        seconds=game['seconds'], source_unchanged=before == source)
    row = dict(life=source['life'], method=method, query=query, replica=replica, seed=seed,
        planner_seed=seed + PLANNER_OFFSET,
        rollout_seed=seed + ROLLOUT_OFFSET if method.startswith('MC') else None, result=result)
    return row, dict(**row, episode=game, decisions=decisions)


def lifecycle_run(source, directory):
    started = perf_counter()
    folder = directory / f"life_{source['life']}"; folder.mkdir()
    build_dir = folder / 'build'; build_dir.mkdir()
    result = dict(life=source['life'], games=[])
    with gzip.open(folder / 'control_games.jsonl.gz', 'wt') as stream:
        for method in METHODS:
            for query in QUERIES:
                for replica in range(REPLICAS):
                    row, raw = control_game(source, method, query, replica, build_dir)
                    result['games'].append(row); append(stream, raw)
                    save(folder / 'lifecycle.json', result)
            print(json.dumps(dict(event='method_complete', life=source['life'], method=method)), flush=True)
    result['seconds'] = perf_counter() - started
    save(folder / 'lifecycle.json', result)
    return result


def run(directory):
    started = perf_counter(); directory.mkdir(parents=True, exist_ok=False)
    capsule = extract_source(json.loads((SOURCE / 'run.json').read_text()),
        json.loads((SOURCE / 'source_capsule.json').read_text()))
    save(directory / 'source_capsule.json', capsule); snapshot(directory)
    result = dict(schema='acfqp.rollout_consequences.v119.run', status='running',
        settings=dict(lifecycles=list(LIVES), phase='A_RETURN', methods=list(METHODS),
            queries=QUERIES, replicas=REPLICAS, max_steps=MAX_STEPS, workers=WORKERS,
            version_base=BASE, planner_offset=PLANNER_OFFSET, rollout_offset=ROLLOUT_OFFSET),
        inherited_costs=capsule['inherited_costs'], lifecycles=[],
        executable=sys.executable, platform=platform.platform())
    save(directory / 'run.json', result)
    with ProcessPoolExecutor(max_workers=WORKERS) as pool:
        tasks = [pool.submit(lifecycle_run, source, directory) for source in capsule['snapshots']]
        for future in as_completed(tasks):
            result['lifecycles'].append(future.result())
            result['lifecycles'].sort(key=lambda row: row['life'])
            save(directory / 'run.json', result)
    result.update(status='complete', seconds=perf_counter() - started)
    save(directory / 'run.json', result)
    print(json.dumps(dict(status='complete', seconds=result['seconds'])), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    run(parser.parse_args().output)
