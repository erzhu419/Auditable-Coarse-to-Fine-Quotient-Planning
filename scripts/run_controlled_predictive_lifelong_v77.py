"""Run fixed-algorithm multi-episode consequence learning and natural games."""
from collections import Counter
import argparse
import gzip
import json
from pathlib import Path
import platform
import random
import shutil
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from acfqp.science.controlled_predictive_lifelong_v77 import Knowledge, MODES, POLICIES
from acfqp.science import controlled_predictive_lifelong_experience_v77 as experience
from acfqp.science import controlled_predictive_lifelong_planner_v77 as planner
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics

METHODS = ('H2_ONLY', 'FROZEN_PLAN', 'FIXED_PLAN', 'REVISED_PLAN', 'REVISED_DIRECT')
CHECKPOINTS = (15, 39, 75)
LIFECYCLES = (0, 1, 2)
QUERIES = dict(reward=dict(reward_weight=1.0, failure_penalty=0.0, goal_bonus=0.0),
               risk_goal=dict(reward_weight=1.0, failure_penalty=4.0, goal_bonus=4.0))


def save(path, value):
    path.write_text(json.dumps(value, allow_nan=False, separators=(',', ':')) + '\n')


def count_delta(after, before):
    return {key: value-before.get(key, 0) for key, value in after.items()
            if value != before.get(key, 0)}


def snapshot(directory):
    paths = [f'src/acfqp/science/controlled_predictive_lifelong{suffix}_v77.py'
             for suffix in ('', '_planner', '_experience')]
    paths += [f'scripts/{verb}_controlled_predictive_lifelong_v77.py' for verb in ('run', 'analyze')]
    paths += ['specs/MULTI_EPISODE_CONSEQUENCE_LEARNING_V77.md',
              'src/acfqp/science/controlled_predictive_relational_dynamics_v69.py',
              'src/acfqp/science/controlled_predictive_effect_contract_v74.py',
              'src/acfqp/science/controlled_predictive_grouped_contract_v73.py',
              'src/acfqp/science/controlled_predictive_local_contract_v72.py',
              'src/acfqp/domains/standard_2048.py', 'src/acfqp/domains/g2048.py']
    for relative in paths:
        destination = directory / 'source' / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, destination)


def evaluate_game(method, knowledge, rule, lifecycle, replica, query_name, max_steps=2000):
    seed = 7790000 + lifecycle * 100 + replica
    # Common per-step model uniforms, independent of the environment generator.
    model_rng = random.Random(seed + 1000000)
    counts, decisions = Counter(), []
    before = dict(knowledge.counts) if knowledge is not None else {}
    depth = 1 if method == 'REVISED_DIRECT' else 2

    def act(board, step):
        decision = planner.choose(board, QUERIES[query_name], knowledge, rule, model_rng,
                                  depth=depth, work=counts)
        decisions.append(dict(action=decision['action'], policy=decision['policy'],
                              metrics=decision['metrics'], value=decision['value']))
        return decision['action']

    game = experience.run_episode(seed, act, max_steps=max_steps)
    query = QUERIES[query_name]
    utility = (query['reward_weight'] * game['return_score'] / 2048
               - query['failure_penalty'] * (game['status'] == 'LOST')
               + query['goal_bonus'] * (game['status'] == 'WON'))
    result = dict(seed=seed, replica=replica, query=query_name, status=game['status'],
        score=game['return_score'], steps=game['steps_count'], max_rank=max(game['final_board']),
        utility=utility, seconds=game['seconds'], environment_counts=game['work'],
        planning_counts=dict(counts), prediction_counts=count_delta(knowledge.counts, before)
        if knowledge is not None else {})
    raw = dict(method=method, query=query_name, episode=game, decisions=decisions)
    return result, raw


def lifecycle_run(lifecycle, directory, rule, progress):
    folder = directory / f'life_{lifecycle}'
    folder.mkdir()
    result = dict(id=lifecycle, checkpoints=[])
    records, source_work, behavior_work = [], Counter(), Counter()
    source_outcomes, source_by_policy = Counter(), {policy: Counter() for policy in POLICIES}
    source_seconds = warmup_seconds = 0.0
    update_seconds = Counter()
    serialization_seconds = Counter()
    evaluation_seconds = Counter()
    models = initial = None
    previous = 0
    with gzip.open(folder / 'training_episodes.jsonl.gz', 'wt', encoding='utf-8') as source_file:
        for checkpoint_index, checkpoint in enumerate(CHECKPOINTS):
            phase_tick = perf_counter()
            cpdir = folder / f'checkpoint_{checkpoint}'
            cpdir.mkdir()
            tick = perf_counter()
            for episode_index in range(previous, checkpoint):
                policy = POLICIES[episode_index % len(POLICIES)]
                seed = 7700000 + lifecycle * 10000 + episode_index
                game = experience.run_episode(seed, lambda board, step:
                    planner.policy_action(board, policy, rule, behavior_work))
                new_records = experience.targets(game, policy, episode_index)
                records.extend(new_records)
                source_work.update(game['work'])
                source_outcomes[game['status']] += 1
                source_by_policy[policy].update(episodes=1, transitions=game['steps_count'],
                    records=len(new_records), won=int(game['status'] == 'WON'),
                    lost=int(game['status'] == 'LOST'), cutoff=int(game['status'] == 'CUTOFF'))
                source_file.write(json.dumps(dict(episode_index=episode_index, policy=policy,
                    game=game), allow_nan=False, separators=(',', ':')) + '\n')
            source_file.flush()
            source_seconds += perf_counter() - tick
            updates = {}
            if models is None:
                models, initial = Knowledge.initialize(records)
                warmup_seconds = source_seconds
            else:
                for mode in MODES:
                    updates[mode] = models[mode].update(records, previous)
                    update_seconds[mode] += updates[mode]['seconds']
            if any(model.checkpoint != checkpoint for model in models.values()):
                raise ValueError('knowledge checkpoint does not match the observed experience prefix')
            source_summary = dict(episodes=checkpoint, records=len(records),
                work=dict(source_work), policy_work=dict(behavior_work), seconds=source_seconds,
                warmup_seconds=warmup_seconds, outcomes=dict(source_outcomes),
                by_policy={policy: dict(counts) for policy, counts in source_by_policy.items()},
                training_records=sum(row['episode'] % 5 != 4 for row in records),
                validation_records=sum(row['episode'] % 5 == 4 for row in records),
                failure_labels=sum(row['target'][1] for row in records),
                success_labels=sum(row['target'][2] for row in records),
                exact_teacher_calls=0, latest_available_episode=checkpoint-1)
            checkpoint_row = dict(episodes=checkpoint, source_summary=source_summary,
                initialization=initial, updates=updates, models={}, methods={})
            payloads = {}
            for mode, model in models.items():
                tick = perf_counter()
                payload = model.to_payload()
                model_path = cpdir / f'{mode}.json'
                save(model_path, payload)
                payloads[mode] = payload
                serialization_seconds[mode] += perf_counter() - tick
                checkpoint_row['models'][mode] = dict(
                    nodes=sum(len(tree['left']) for tree in model.trees.values()),
                    leaves=sum(sum(index < 0 for index in tree['left']) for tree in model.trees.values()),
                    bytes=model_path.stat().st_size, counts=dict(model.counts))
            save(cpdir / 'training_update.json', checkpoint_row)
            print(json.dumps(dict(phase='learned', lifecycle=lifecycle, episodes=checkpoint,
                transitions=source_work['sampled_transitions'], records=len(records),
                revised_accepts=models['REVISED'].counts['proposals_accepted'],
                source_outcomes=dict(source_outcomes))), flush=True)

            deployed = {}
            for method in METHODS:
                if method == 'H2_ONLY':
                    deployed[method] = None
                else:
                    mode = method.split('_')[0]
                    tick = perf_counter()
                    deployed[method] = Knowledge.from_payload(payloads[mode])
                    evaluation_seconds[method] += perf_counter() - tick
                checkpoint_row['methods'][method] = dict(games=[])
            with gzip.open(cpdir / 'evaluation_episodes.jsonl.gz', 'wt', encoding='utf-8') as eval_file:
                for replica in range(2):
                    for query_index, query_name in enumerate(QUERIES):
                        offset = (lifecycle + checkpoint_index + replica + query_index) % len(METHODS)
                        order = METHODS[offset:] + METHODS[:offset]
                        for method in order:
                            tick = perf_counter()
                            game, raw = evaluate_game(method, deployed[method], rule, lifecycle,
                                                      replica, query_name)
                            eval_file.write(json.dumps(raw, allow_nan=False,
                                                       separators=(',', ':')) + '\n')
                            eval_file.flush()
                            evaluation_seconds[method] += perf_counter() - tick
                            checkpoint_row['methods'][method]['games'].append(game)
                            print(json.dumps(dict(phase='game', lifecycle=lifecycle,
                                episodes=checkpoint, method=method, query=query_name,
                                replica=replica, score=game['score'], status=game['status'],
                                steps=game['steps'], seconds=round(game['seconds'], 3))), flush=True)
            for method, row in checkpoint_row['methods'].items():
                mode = method.split('_')[0]
                costs = dict(source_seconds=0.0, initial_fit_seconds=0.0,
                    update_seconds=0.0, serialization_seconds=0.0,
                    evaluation_seconds=evaluation_seconds[method])
                if method != 'H2_ONLY':
                    costs.update(source_seconds=warmup_seconds if mode == 'FROZEN' else source_seconds,
                        initial_fit_seconds=initial['seconds'], update_seconds=update_seconds[mode],
                        serialization_seconds=serialization_seconds[mode])
                costs['total_seconds'] = sum(costs.values())
                row['costs'] = costs
            checkpoint_row['phase_seconds'] = perf_counter() - phase_tick
            save(cpdir / 'checkpoint.json', checkpoint_row)
            result['checkpoints'].append(checkpoint_row)
            progress(result)
            previous = checkpoint
    return result


def run(directory):
    started = perf_counter()
    directory.mkdir(parents=True, exist_ok=False)
    snapshot(directory)
    rule_payload = json.loads((ROOT / 'reports/controlled_predictive_composition_v69/learned_rule.json').read_text())
    save(directory / 'supplied_dynamics.json', rule_payload)
    rule = LearnedDynamics.from_payload(rule_payload)
    report = dict(schema='acfqp.multi_episode_lifecycle.v77', status='running',
        platform=platform.platform(), python=sys.version, executable=sys.executable,
        settings=dict(lifecycles=list(LIFECYCLES), checkpoints=list(CHECKPOINTS), queries=QUERIES,
            methods=list(METHODS), evaluation_replicas=2, max_episode_steps=2000,
            continuation_policies=list(POLICIES), prediction_window_actions=32,
            teacher_scope='V69 dynamics supplied equally; all new training targets use sampled actual transitions.',
            learning_scope='Shared chronological offline experience; evaluation games never update knowledge.'),
        lifecycles=[])
    save(directory / 'run.json', report)
    for lifecycle in LIFECYCLES:
        def progress(partial):
            report['lifecycles'] = [row for row in report['lifecycles'] if row['id'] != lifecycle] + [partial]
            report['actual_wall_seconds'] = perf_counter() - started
            save(directory / 'run.json', report)
        result = lifecycle_run(lifecycle, directory, rule, progress)
        progress(result)
    report.update(status='complete', actual_wall_seconds=perf_counter()-started)
    save(directory / 'run.json', report)
    print(json.dumps(dict(phase='complete', lifecycles=len(report['lifecycles']),
                         seconds=report['actual_wall_seconds'])), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    run(parser.parse_args().output)
