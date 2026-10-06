"""A fixed learner adapts spawn-parameter modules without observing phase identities."""
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
from dataclasses import replace
from fractions import Fraction
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
from acfqp.science.controlled_predictive_regime_memory_v115 import SpawnMemory
from acfqp.science.controlled_predictive_regime_experience_v115 import run_episode, observed_rank
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics
from acfqp.science import controlled_predictive_lifelong_planner_v77 as planner

METHODS = ('FROZEN', 'POOLED', 'RECENT', 'LIBRARY')
EVAL_METHODS = METHODS + ('KNOWN_PARAMETER',)
PHASES = (('A', .1), ('B', .3), ('A_RETURN', .1))
QUERIES = dict(reward=dict(reward_weight=1., failure_penalty=0., goal_bonus=0.),
    risk_goal=dict(reward_weight=1., failure_penalty=4., goal_bonus=4.))
LIFECYCLES = (0, 1, 2, 3)
SOURCE_GAMES, REPLICAS, MAX_STEPS, WORKERS = 6, 2, 2000, 4
CHECKPOINTS = {'A': (6,), 'B': (1, 3, 6), 'A_RETURN': (1, 3, 6)}
DYNAMICS_SOURCE = ROOT / 'reports/controlled_predictive_fresh_ranking_v105/supplied_dynamics.json'


def save(path, value):
    path.write_text(json.dumps(value, allow_nan=False, separators=(',', ':')) + '\n')


def snapshot(directory):
    importlib.import_module('scripts.analyze_controlled_predictive_regime_memory_v115')
    files = {Path(__file__).resolve(), ROOT / 'specs/REGIME_MEMORY_V115.md'}
    for module in list(sys.modules.values()):
        filename = getattr(module, '__file__', None)
        if filename:
            path = Path(filename).resolve()
            if path.is_relative_to(ROOT / 'src') or path.is_relative_to(ROOT / 'scripts'):
                files.add(path)
    # V77 loads these compilers on the first planning call, after the snapshot.
    files.update((ROOT / 'src/acfqp/science').glob('controlled_predictive_*contract_v7[234].py'))
    for path in files:
        target = directory / 'source' / path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)


def evaluation_game(method, payload, template, life, phase_index, after_game, replica, query):
    p_true = PHASES[phase_index][1]
    if method == 'KNOWN_PARAMETER':
        p = Fraction(str(p_true))
        rule = replace(template, spawn_distribution=((1, 1-p), (2, p)))
    else:
        rule = SpawnMemory.from_payload(payload).to_rule(template)
    p_used = float(dict(rule.spawn_distribution)[2])
    seed = 115900000 + life * 100000 + phase_index * 10000 + after_game * 100 + replica
    rng, work, decisions = random.Random(seed + 1000000), Counter(), []
    def act(board, step):
        result = planner.choose(board, QUERIES[query], None, rule, rng, depth=2, work=work)
        decisions.append(dict(action=result['action'], value=result['value'], metrics=result['metrics']))
        return result['action']
    game = run_episode(seed, act, p_true, MAX_STEPS)
    q = QUERIES[query]
    result = dict(score=game['return_score'], status=game['status'], steps=game['steps_count'],
        utility=q['reward_weight'] * game['return_score'] / 2048
            - q['failure_penalty'] * (game['status'] == 'LOST') + q['goal_bonus'] * (game['status'] == 'WON'),
        environment_counts=game['work'], planning_counts=dict(work), seconds=game['seconds'], p4_used=p_used)
    row = dict(method=method, query=query, replica=replica, seed=seed, result=result)
    return row, dict(**row, episode=game, decisions=decisions)


def lifecycle_run(life, directory, dynamics_payload):
    started = perf_counter()
    folder = directory / f'life_{life}'; folder.mkdir()
    template = LearnedDynamics.from_payload(dynamics_payload)
    memories = {method: SpawnMemory(method) for method in METHODS}
    result = dict(life=life, phases=[], final_models={}, checks=dict(
        predictions_precede_observations=True, observed_rank_matches_environment=True,
        shared_source_observations=True, warmup_completed_in_A=False,
        deterministic_program_preserved=True, evaluation_never_updates_memory=True,
        source_games_complete_roster=True, evaluation_complete_roster=True))
    observation_index = 0
    for phase_index, (phase_name, p_true) in enumerate(PHASES):
        phase_dir = folder / phase_name; phase_dir.mkdir()
        phase = dict(name=phase_name, p4=p_true, source_games=[], predictions=[], module_events=[], checkpoints=[])
        result['phases'].append(phase)
        phase_observations = 0
        with gzip.open(phase_dir / 'source_games.jsonl.gz', 'wt') as source_file:
            for episode in range(SOURCE_GAMES):
                policy_work = Counter()
                def act(board, step):
                    return planner.policy_action(board, 'GREEDY', template, work=policy_work)
                seed = 115000000 + life * 10000 + phase_index * 100 + episode
                game = run_episode(seed, act, p_true, MAX_STEPS)
                source_file.write(json.dumps(game, separators=(',', ':')) + '\n'); source_file.flush()
                phase['source_games'].append(dict(episode=episode, source_seed=seed, outcome=game['status'],
                    ground_work=game['work'], planning_counts=dict(policy_work), steps=game['steps_count'], seconds=game['seconds']))
                for step in game['steps']:
                    predictions = {method: dict(p4=memory.predict(), module_id=memory.module_id)
                        for method, memory in memories.items()}
                    rank = observed_rank(step)
                    observation_index += 1; phase_observations += 1
                    phase['predictions'].append(dict(phase_observation_index=phase_observations,
                        observation_index=observation_index, is_four=int(rank == 2), methods=predictions))
                    result['checks']['observed_rank_matches_environment'] &= rank == step['spawned_rank']
                    for method, memory in memories.items():
                        event = memory.observe(rank)
                        if method == 'LIBRARY' and event is not None:
                            record = deepcopy(event)
                            record['observation_index'] = record.pop('obs_index')
                            phase['module_events'].append(record)
                after_game = episode + 1
                if phase_name == 'A':
                    result['checks']['warmup_completed_in_A'] = observation_index >= 256
                if after_game in CHECKPOINTS[phase_name]:
                    saved = {method: memory.to_payload() for method, memory in memories.items()}
                    cp = dict(phase=phase_name, after_game=after_game, models=saved, model_predictions={
                        method: float(dict(memory.to_rule(template).spawn_distribution)[2])
                        for method, memory in memories.items()}, evaluations=[])
                    before = deepcopy(saved)
                    with gzip.open(phase_dir / f'evaluation_after_{after_game}.jsonl.gz', 'wt') as eval_file:
                        for method in EVAL_METHODS:
                            for query in QUERIES:
                                for replica in range(REPLICAS):
                                    row, raw = evaluation_game(method, saved.get(method), template,
                                        life, phase_index, after_game, replica, query)
                                    cp['evaluations'].append(row)
                                    eval_file.write(json.dumps(raw, separators=(',', ':')) + '\n')
                    phase['checkpoints'].append(cp)
                    result['checks']['evaluation_never_updates_memory'] &= before == {
                        method: memory.to_payload() for method, memory in memories.items()}
                    result['checks']['deterministic_program_preserved'] &= all(
                        memory.to_rule(template).program == template.program for memory in memories.values())
                save(folder / 'lifecycle.json', result)
                print(json.dumps(dict(phase='source_game_complete', life=life, environment_phase=phase_name,
                    episode=after_game, observed=observation_index, evaluations=sum(len(cp['evaluations'])
                        for ph in result['phases'] for cp in ph['checkpoints']))), flush=True)
    result['final_models'] = {method: memory.to_payload() for method, memory in memories.items()}
    result['checks']['shared_source_observations'] = all(
        memory.observations_seen == observation_index for memory in memories.values())
    result['checks']['source_games_complete_roster'] = all(len(phase['source_games']) == SOURCE_GAMES for phase in result['phases'])
    result['checks']['evaluation_complete_roster'] = all(
        len(cp['evaluations']) == len(EVAL_METHODS) * len(QUERIES) * REPLICAS
        for phase in result['phases'] for cp in phase['checkpoints'])
    result['actual_wall_seconds'] = perf_counter() - started
    save(folder / 'lifecycle.json', result)
    return result


def run(directory):
    started = perf_counter(); directory.mkdir(parents=True, exist_ok=False)
    payload = json.loads(DYNAMICS_SOURCE.read_text())
    snapshot(directory); save(directory / 'supplied_dynamics.json', payload)
    settings = dict(lifecycles=list(LIFECYCLES), phases=[dict(name=name, p4=p) for name,p in PHASES],
        methods=list(METHODS), eval_methods=list(EVAL_METHODS), queries=QUERIES,
        warmup_spawns=256, route_block=64, recent_window=256, source_games_per_phase=SOURCE_GAMES,
        eval_checkpoints=[dict(phase=phase, after_game=g) for phase, _ in PHASES for g in CHECKPOINTS[phase]],
        eval_replicas=REPLICAS, max_steps=MAX_STEPS, workers=WORKERS)
    report = dict(schema='acfqp.regime_memory.v115', status='running', settings=settings,
        supplied_dynamics_source=str(DYNAMICS_SOURCE), supplied_dynamics=payload,
        platform=platform.platform(), executable=sys.executable, python=sys.version,
        lifecycles=[], runner_checks=dict(source_seed_namespace=True, evaluation_seed_namespace=True,
            no_phase_or_true_parameter_in_learner_api=True, fixed_learning_rule=True),
        source_prior_scope='V69 deterministic swipe/reward program, location rule and goal are supplied. '
            'Its rank probability is withheld from all four learners; KNOWN_PARAMETER is an evaluation-only reference.')
    save(directory / 'run.json', report)
    with ProcessPoolExecutor(max_workers=WORKERS) as pool:
        tasks = {pool.submit(lifecycle_run, life, directory, payload): life for life in LIFECYCLES}
        for future in as_completed(tasks):
            result = future.result()
            if result['life'] != tasks[future]:
                raise ValueError('lifecycle differs from its submitted seed identity')
            report['lifecycles'].append(result); report['lifecycles'].sort(key=lambda row: row['life'])
            report['actual_wall_seconds'] = perf_counter() - started
            save(directory / 'run.json', report)
    report['status'] = 'complete'; report['actual_wall_seconds'] = perf_counter() - started
    save(directory / 'run.json', report)
    print(json.dumps(dict(status='complete', lifecycles=len(report['lifecycles']), seconds=report['actual_wall_seconds'])), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    run(parser.parse_args().output)
