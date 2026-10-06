"""Frozen causal-context consequence experiment across A/B/A-return games."""
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
from acfqp.science.controlled_predictive_context_consequences_v116 import ConsequenceKnowledge, MODES, POLICIES
from acfqp.science.controlled_predictive_context_experience_v116 import policy_game, causal_records
from acfqp.science.controlled_predictive_lifelong_experience_v77 import targets
from acfqp.science.controlled_predictive_regime_memory_v115 import SpawnMemory
from acfqp.science.controlled_predictive_regime_experience_v115 import run_episode
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics
from acfqp.science import controlled_predictive_lifelong_planner_v77 as planner

PHASES = (('A', .1), ('B', .3), ('A_RETURN', .1))
METHODS = ('H2_ONLY', 'MIXED_PLAN', 'CONTEXT_PLAN')
QUERIES = dict(reward=dict(reward_weight=1., failure_penalty=0., goal_bonus=0.),
    risk_goal=dict(reward_weight=1., failure_penalty=4., goal_bonus=4.))
LIFECYCLES = (0, 1, 2, 3)
SOURCE_GAMES, PREDICTION_REPLICAS, CONTROL_REPLICAS, MAX_STEPS, WORKERS = 18, 2, 2, 2000, 4
DYNAMICS_SOURCE = ROOT / 'reports/controlled_predictive_fresh_ranking_v105/supplied_dynamics.json'


def save(path, value):
    path.write_text(json.dumps(value, allow_nan=False, separators=(',', ':')) + '\n')


def append(stream, value):
    stream.write(json.dumps(value, allow_nan=False, separators=(',', ':')) + '\n')


def snapshot(directory):
    importlib.import_module('scripts.analyze_controlled_predictive_context_consequences_v116')
    files = {Path(__file__).resolve(), ROOT / 'specs/CONTEXT_CONSEQUENCES_V116.md'}
    for module in list(sys.modules.values()):
        filename = getattr(module, '__file__', None)
        if filename:
            path = Path(filename).resolve()
            if path.is_relative_to(ROOT / 'src') or path.is_relative_to(ROOT / 'scripts'):
                files.add(path)
    files.update((ROOT / 'src/acfqp/science').glob('controlled_predictive_*contract_v7[234].py'))
    for path in files:
        target = directory / 'source' / path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)


def prediction_games(life, phase_index, template, router_p4, versions, stream):
    models = {version: {mode: ConsequenceKnowledge.from_payload(payload)
        for mode, payload in payloads.items()} for version, payloads in versions.items()}
    rows = []
    for policy_index, policy in enumerate(POLICIES):
        for replica in range(PREDICTION_REPLICAS):
            seed = 116800000 + life * 100000 + phase_index * 10000 + policy_index * 100 + replica
            game, work = policy_game(seed, policy, template, PHASES[phase_index][1], MAX_STEPS)
            records = targets(game, policy, policy_index * PREDICTION_REPLICAS + replica,
                stride=4, horizons=(30, 31))
            predictions = {version: {mode: model.predict_records(records, router_p4).tolist()
                for mode, model in group.items()} for version, group in models.items()}
            evaluated = [dict(record, predictions={version: {mode: values[i] for mode, values in group.items()}
                for version, group in predictions.items()}) for i, record in enumerate(records)]
            row = dict(policy=policy, replica=replica, seed=seed, status=game['status'],
                steps=game['steps_count'], environment_counts=game['work'], planning_counts=work,
                seconds=game['seconds'], records=evaluated)
            rows.append(row)
            append(stream, dict(policy=policy, replica=replica, episode=game))
    counts = {version: {mode: dict(model.counts) for mode, model in group.items()}
        for version, group in models.items()}
    return rows, counts


def control_game(method, query, replica, life, phase_index, rule, payload):
    knowledge = None if method == 'H2_ONLY' else ConsequenceKnowledge.from_payload(payload)
    seed = 117900000 + life * 100000 + phase_index * 10000 + replica
    rng, work, decisions = random.Random(seed + 1000000), Counter(), []
    def act(board, step):
        chosen = planner.choose(board, QUERIES[query], knowledge, rule, rng, depth=2, work=work)
        decisions.append({key: chosen[key] for key in ('action', 'value', 'metrics', 'policy', 'branches')})
        return chosen['action']
    game = run_episode(seed, act, PHASES[phase_index][1], MAX_STEPS)
    q = QUERIES[query]
    result = dict(score=game['return_score'], status=game['status'], steps=game['steps_count'],
        utility=q['reward_weight'] * game['return_score'] / 2048
            - q['failure_penalty'] * (game['status'] == 'LOST') + q['goal_bonus'] * (game['status'] == 'WON'),
        environment_counts=game['work'], planning_counts=dict(work),
        prediction_counts={} if knowledge is None else dict(knowledge.counts), seconds=game['seconds'])
    row = dict(method=method, query=query, replica=replica, seed=seed, result=result)
    return row, dict(**row, episode=game, decisions=decisions)


def lifecycle_run(life, directory, dynamics_payload):
    started = perf_counter()
    folder = directory / f'life_{life}'; folder.mkdir()
    template = LearnedDynamics.from_payload(dynamics_payload)
    router, training, archives = SpawnMemory('LIBRARY'), [], {}
    result = dict(life=life, phases=[], checks={})
    for phase_index, (name, p_true) in enumerate(PHASES):
        phase_dir = folder / name; phase_dir.mkdir()
        phase = dict(name=name, p4=p_true, source_games=[])
        result['phases'].append(phase)
        with gzip.open(phase_dir / 'source_games.jsonl.gz', 'wt') as raw_file, \
                gzip.open(phase_dir / 'training_records.jsonl.gz', 'wt') as records_file:
            for local_episode in range(SOURCE_GAMES):
                episode = phase_index * SOURCE_GAMES + local_episode
                policy = POLICIES[local_episode % len(POLICIES)]
                seed = 116000000 + life * 10000 + phase_index * 100 + local_episode
                game, work = policy_game(seed, policy, template, p_true, MAX_STEPS)
                records, labels = causal_records(game, policy, episode, router)
                training.extend(records)
                for record in records:
                    append(records_file, record)
                append(raw_file, dict(policy=policy, episode_id=episode, game=game, label_log=labels))
                phase['source_games'].append(dict(episode=episode, policy=policy, seed=seed,
                    status=game['status'], steps=game['steps_count'], environment_counts=game['work'],
                    planning_counts=work, seconds=game['seconds'], label_log=labels['counts']))
        rule = router.to_rule(template)
        context = float(dict(rule.spawn_distribution)[2])
        cp = dict(phase=name, router_p4=context, router_payload=router.to_payload(), models={}, fit_logs={}, checks={})
        phase['checkpoint'] = cp
        for mode in MODES:
            model, log = ConsequenceKnowledge.fit(training, mode, context)
            cp['models'][mode], cp['fit_logs'][mode] = model.to_payload(), log
        versions = dict(CURRENT=cp['models'])
        if name == 'A_RETURN':
            versions.update(archives)
        before = deepcopy(router.to_payload())
        model_before = deepcopy(cp['models'])
        archives_before = deepcopy(archives)
        with gzip.open(phase_dir / 'predictive_games.jsonl.gz', 'wt') as stream:
            cp['predictive_tests'], cp['prediction_counts'] = prediction_games(
                life, phase_index, template, context, versions, stream)
        cp['control_evaluations'] = []
        with gzip.open(phase_dir / 'control_games.jsonl.gz', 'wt') as stream:
            for method in METHODS:
                payload = None if method == 'H2_ONLY' else cp['models'][method.removesuffix('_PLAN')]
                for query in QUERIES:
                    for replica in range(CONTROL_REPLICAS):
                        row, raw = control_game(method, query, replica, life, phase_index, rule, payload)
                        cp['control_evaluations'].append(row); append(stream, raw)
        cp['checks'] = dict(evaluation_never_updates_router=before == router.to_payload(),
            evaluation_never_changes_parameters=model_before == cp['models'] and archives_before == archives,
            identical_training_rosters=cp['fit_logs']['MIXED']['training_roster'] == cp['fit_logs']['CONTEXT']['training_roster'],
            deterministic_program_preserved=rule.program == template.program)
        if name in ('A', 'B'):
            archives[name + '_END'] = deepcopy(cp['models'])
        save(folder / 'lifecycle.json', result)
        print(json.dumps(dict(event='phase_complete', life=life, phase=name,
            training_records=len(training), router_p4=context)), flush=True)
    result['final_router'] = router.to_payload()
    result['checks'] = dict(source_observation_count=router.observations_seen == sum(
        game['steps'] for phase in result['phases'] for game in phase['source_games']),
        source_games_complete_roster=all(len(phase['source_games']) == SOURCE_GAMES for phase in result['phases']))
    result['actual_wall_seconds'] = perf_counter() - started
    save(folder / 'lifecycle.json', result)
    return result


def run(directory):
    started = perf_counter(); directory.mkdir(parents=True, exist_ok=False)
    payload = json.loads(DYNAMICS_SOURCE.read_text())
    snapshot(directory); save(directory / 'supplied_dynamics.json', payload)
    settings = dict(lifecycles=list(LIFECYCLES), phases=[dict(name=name, p4=p) for name,p in PHASES],
        source_games_per_phase=SOURCE_GAMES, policies=list(POLICIES), modes=list(MODES),
        methods=list(METHODS), queries=QUERIES, horizons=[30,31], stride=4,
        prediction_replicas=PREDICTION_REPLICAS, control_replicas=CONTROL_REPLICAS, max_steps=MAX_STEPS, workers=WORKERS)
    report = dict(schema='acfqp.context_consequences.v116.run', status='running', settings=settings,
        supplied_dynamics_source=str(DYNAMICS_SOURCE), supplied_dynamics=payload,
        platform=platform.platform(), executable=sys.executable, python=sys.version, lifecycles=[],
        runner_checks=dict(no_phase_or_true_parameter_in_learner_api=True, fixed_learning_recipe=True,
            source_prediction_control_seed_namespaces_disjoint=True),
        source_prior_scope='V69 swipe/reward program, goal and location rule are supplied; spawn p4 is estimated from source only.')
    save(directory / 'run.json', report)
    with ProcessPoolExecutor(max_workers=WORKERS) as pool:
        tasks = {pool.submit(lifecycle_run, life, directory, payload): life for life in LIFECYCLES}
        for future in as_completed(tasks):
            life = future.result()
            if life['life'] != tasks[future]:
                raise ValueError('lifecycle identity differs from submitted worker')
            report['lifecycles'].append(life); report['lifecycles'].sort(key=lambda row: row['life'])
            report['actual_wall_seconds'] = perf_counter() - started
            save(directory / 'run.json', report)
    report['status'] = 'complete'; report['actual_wall_seconds'] = perf_counter() - started
    save(directory / 'run.json', report)
    print(json.dumps(dict(status='complete', lifecycles=len(report['lifecycles']), seconds=report['actual_wall_seconds'])), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    run(parser.parse_args().output)
