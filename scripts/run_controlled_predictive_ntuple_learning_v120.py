"""Persistent spatial afterstate TD from natural, on-policy 2048 games."""
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
from acfqp.science.controlled_predictive_regime_experience_v115 import run_episode
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics
from acfqp.science import controlled_predictive_lifelong_planner_v77 as planner

SOURCE = ROOT / 'reports/controlled_predictive_rollout_consequences_v119'
QUERIES = dict(reward=dict(reward_weight=1., failure_penalty=0., goal_bonus=0.),
    risk_goal=dict(reward_weight=1., failure_penalty=4., goal_bonus=4.))
LIVES, TRAIN_EPISODES, REPLICAS, MAX_STEPS, WORKERS = (0, 1, 2, 3), 4096, 8, 2000, 4
CHECKPOINTS, BLOCK_SIZE, ALPHA = (0, 256, 1024, 4096), 256, .0025
BASE, PLANNER_OFFSET, ROLLOUT_OFFSET = 120 * 100_000_000, 50_000_000, 60_000_000


def save(path, value):
    path.write_text(json.dumps(value, allow_nan=False, separators=(',', ':')) + '\n')


def append(stream, value):
    stream.write(json.dumps(value, allow_nan=False, separators=(',', ':')) + '\n')


def train_seed(life, query, episode):
    return BASE + 1_000_000 + life * 100000 + list(QUERIES).index(query) * 10000 + episode


def evaluation_seed(life, replica):
    return BASE + 2_000_000 + life * 100000 + replica


def extract_source(previous):
    """Retain mechanism and router acquisition only, never old value models."""
    snapshots = [dict(life=row['life'], rule=deepcopy(row['rule']))
        for row in previous['snapshots']]
    if sorted(row['life'] for row in snapshots) != list(LIVES):
        raise ValueError('V120 requires the four frozen V119 dynamics snapshots')
    cost_keys = ('supplied_dynamics_fit_counts', 'source_environment',
        'source_planning', 'source_seconds', 'source_router')
    costs = {key: deepcopy(previous['inherited_costs'][key]) for key in cost_keys}
    costs['scope'] = ('All actors inherit the deterministic dynamics program; only H2/MC4 '
        'references use the frozen source spawn router. Source acquisition/router costs '
        'are retained separately; old trees, selectors and outer games are not used.')
    return dict(schema='acfqp.ntuple_source.v120', snapshots=snapshots, inherited_costs=costs)


def snapshot(directory):
    importlib.import_module('acfqp.science.controlled_predictive_ntuple_td_v120')
    importlib.import_module('acfqp.science.controlled_predictive_rollout_consequences_v119')
    importlib.import_module('scripts.analyze_controlled_predictive_ntuple_learning_v120')
    files = {Path(__file__).resolve(), ROOT / 'specs/NTUPLE_LEARNING_V120.md'}
    for module in list(sys.modules.values()):
        filename = getattr(module, '__file__', None)
        if filename:
            path = Path(filename).resolve()
            if path.is_relative_to(ROOT / 'src') or path.is_relative_to(ROOT / 'scripts'):
                files.add(path)
    files.update((ROOT / 'src/acfqp/science').glob('controlled_predictive_*contract_v7[234].py'))
    files.update((ROOT / 'src/acfqp/science').glob('controlled_predictive_*v120.cpp'))
    files.add(ROOT / 'src/acfqp/science/controlled_predictive_rollout_kernel_v119.cpp')
    for path in files:
        target = directory / 'source' / path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)


def counter_delta(after, before):
    return {key: value - before.get(key, 0) for key, value in after.items()
        if value != before.get(key, 0)}


def compact_trace(game):
    """Replayable actual transitions without duplicating every full board."""
    return dict(initial_board=game['initial_board'], initial_spawns=game['initial_spawns'],
        final_board=game['final_board'], actions=[step['action'] for step in game['steps']],
        spawned_cells=[step['spawned_cell'] for step in game['steps']],
        spawned_ranks=[step['spawned_rank'] for step in game['steps']],
        scores=[step['score'] for step in game['steps']])


def game_result(game, query, learning_counts=None, planning_counts=None):
    q = QUERIES[query]
    return dict(score=game['return_score'], status=game['status'], steps=game['steps_count'],
        utility=q['reward_weight'] * game['return_score'] / 2048
            - q['failure_penalty'] * (game['status'] == 'LOST')
            + q['goal_bonus'] * (game['status'] == 'WON'),
        environment_counts=game['work'], planning_counts=planning_counts or {},
        learning_counts=learning_counts or {}, setup_counts={}, setup_seconds=0.,
        seconds=game['seconds'])


def td_game(model, life, query, *, episode=None, checkpoint=None, replica=None):
    """Choose the next action before the previous afterstate's TD update."""
    training = episode is not None
    seed = train_seed(life, query, episode) if training else evaluation_seed(life, replica)
    q, before = QUERIES[query], dict(model.counts)
    updates_before, pending = model.updates, None
    def act(board, step):
        nonlocal pending
        chosen = model.choose(board, q)
        if training and pending is not None:
            model.update(pending, chosen['value'], ALPHA)
        # A winning afterstate has an analytic continuation and never needs a TD fit.
        pending = None if max(chosen['afterstate']) >= model.rule.goal_rank else chosen['afterstate']
        return chosen['action']
    game = run_episode(seed, act, .1, MAX_STEPS)
    terminal_update = training and game['status'] == 'LOST' and pending is not None
    if terminal_update:
        started = perf_counter()
        model.update(pending, -q['failure_penalty'], ALPHA)
        game['seconds'] += perf_counter() - started
    updates_after = model.updates
    expected = game['steps_count'] - (game['status'] in ('WON', 'CUTOFF')) if training else 0
    if updates_after - updates_before != expected:
        raise AssertionError('TD update count does not match terminal/censoring semantics')
    result = game_result(game, query, counter_delta(model.counts, before))
    result.update(updates_before=updates_before, updates_after=updates_after)
    row = dict(life=life, query=query, method='TRAIN' if training else 'TD',
        checkpoint=checkpoint, replica=replica, seed=seed, result=result)
    if training:
        row.update(episode_index=episode, terminal_update=terminal_update,
            censored_last_update=game['status'] == 'CUTOFF',
            analytic_terminal=game['status'] == 'WON')
    return row, dict(**row, **compact_trace(game))


def reference_game(source, method, query, replica, build_dir):
    from acfqp.science.controlled_predictive_rollout_consequences_v119 import RolloutKnowledge
    seed = evaluation_seed(source['life'], replica)
    rule = LearnedDynamics.from_payload(source['rule'])
    model = None if method == 'H2_ONLY' else RolloutKnowledge(rule, 4, seed + ROLLOUT_OFFSET, build_dir)
    rng, work = random.Random(seed + PLANNER_OFFSET), Counter()
    def act(board, step):
        return planner.choose(board, QUERIES[query], model, rule, rng, depth=2, work=work)['action']
    game = run_episode(seed, act, .1, MAX_STEPS)
    result = game_result(game, query, planning_counts=dict(work))
    result.update(consequence_counts={} if model is None else dict(model.counts),
        setup_counts=dict(getattr(model, 'setup_counts', {})),
        setup_seconds=getattr(model, 'setup_seconds', 0.))
    row = dict(life=source['life'], query=query, method=method, checkpoint=None,
        replica=replica, seed=seed, planner_seed=seed + PLANNER_OFFSET,
        rollout_seed=seed + ROLLOUT_OFFSET if model is not None else None, result=result)
    return row, dict(**row, **compact_trace(game))


def checkpoint_evaluate(model, life, query, episodes, folder, directory, control_stream):
    path = folder / f'checkpoint_{episodes}.npz'
    started = perf_counter()
    before = dict(model.counts)
    metadata = model.save(path)
    result = dict(episodes=episodes, model_file=str(path.relative_to(directory)),
        model_bytes=path.stat().st_size, updates=model.updates,
        save_seconds=perf_counter() - started, save_counts=counter_delta(model.counts, before),
        evaluations=[])
    if isinstance(metadata, dict):
        result['model_metadata'] = metadata
    for replica in range(REPLICAS):
        row, raw = td_game(model, life, query, checkpoint=episodes, replica=replica)
        result['evaluations'].append(row); append(control_stream, raw)
    control_stream.flush()
    return result


def empty_block(start):
    return dict(start=start, end=start, games=0, environment_counts=Counter(),
        learning_counts=Counter(), statuses=Counter(), total_score=0, seconds=0.)


def add_training(block, row):
    result = row['result']
    block['end'] = row['episode_index'] + 1
    block['games'] += 1
    block['environment_counts'].update(result['environment_counts'])
    block['learning_counts'].update(result['learning_counts'])
    block['statuses'][result['status']] += 1
    block['total_score'] += result['score']
    block['seconds'] += result['seconds']


def lifecycle_run(source, directory):
    from acfqp.science.controlled_predictive_ntuple_td_v120 import NtupleValue
    started = perf_counter()
    folder = directory / f"life_{source['life']}"; folder.mkdir()
    build_dir = folder / 'build'; build_dir.mkdir()
    lifecycle = dict(life=source['life'], queries={})
    for query in QUERIES:
        query_folder = folder / query; query_folder.mkdir()
        model = NtupleValue(LearnedDynamics.from_payload(source['rule']), build_dir)
        result = dict(training_blocks=[], checkpoints=[], references=[],
            setup_counts=dict(model.setup_counts), setup_seconds=model.setup_seconds,
            training_trace=str((query_folder / 'training.jsonl.gz').relative_to(directory)),
            control_trace=str((query_folder / 'control.jsonl.gz').relative_to(directory)))
        lifecycle['queries'][query] = result
        with gzip.open(directory / result['training_trace'], 'wt') as train_stream, \
                gzip.open(directory / result['control_trace'], 'wt') as control_stream:
            result['checkpoints'].append(checkpoint_evaluate(model, source['life'], query,
                0, query_folder, directory, control_stream))
            save(folder / 'lifecycle.json', lifecycle)
            block = empty_block(0)
            for episode in range(TRAIN_EPISODES):
                row, raw = td_game(model, source['life'], query, episode=episode)
                append(train_stream, raw); add_training(block, row)
                done = episode + 1
                if done % BLOCK_SIZE == 0:
                    train_stream.flush()
                    result['training_blocks'].append(block)
                    if done in CHECKPOINTS:
                        result['checkpoints'].append(checkpoint_evaluate(model, source['life'],
                            query, done, query_folder, directory, control_stream))
                    save(folder / 'lifecycle.json', lifecycle)
                    print(json.dumps(dict(event='training_block_complete', life=source['life'],
                        query=query, episodes=done, updates=model.updates,
                        statuses=dict(block['statuses']), seconds=block['seconds'])), flush=True)
                    block = empty_block(done)
            # References are evaluated once, after the fixed training budget completes.
            for method in ('H2_ONLY', 'MC4'):
                for replica in range(REPLICAS):
                    row, raw = reference_game(source, method, query, replica, build_dir)
                    result['references'].append(row); append(control_stream, raw)
                control_stream.flush(); save(folder / 'lifecycle.json', lifecycle)
                print(json.dumps(dict(event='reference_complete', life=source['life'],
                    query=query, method=method)), flush=True)
        result.update(final_updates=model.updates)
        del model
        save(folder / 'lifecycle.json', lifecycle)
    lifecycle['seconds'] = perf_counter() - started
    save(folder / 'lifecycle.json', lifecycle)
    return lifecycle


def run(directory):
    started = perf_counter(); directory.mkdir(parents=True, exist_ok=False)
    capsule = extract_source(json.loads((SOURCE / 'source_capsule.json').read_text()))
    save(directory / 'source_capsule.json', capsule); snapshot(directory)
    result = dict(schema='acfqp.ntuple_learning.v120.run', status='running',
        settings=dict(lifecycles=list(LIVES), queries=QUERIES, train_episodes=TRAIN_EPISODES,
            checkpoints=list(CHECKPOINTS), replicas=REPLICAS, max_steps=MAX_STEPS,
            workers=WORKERS, alpha=ALPHA, block_size=BLOCK_SIZE, p_four=.1,
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
