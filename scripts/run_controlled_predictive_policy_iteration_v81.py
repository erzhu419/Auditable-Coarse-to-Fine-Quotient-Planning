"""Collect terminal action advantages under H2, then under its learned successor."""
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
from acfqp.science.controlled_predictive_policy_advantage_v81 import Policy, QUERIES, improve
from acfqp.science.controlled_predictive_advantage_experience_v81 import sample_root
from acfqp.science.controlled_predictive_target_horizon_v80 import ConsequenceModel
from acfqp.science import controlled_predictive_lifelong_experience_v77 as experience
from acfqp.science import controlled_predictive_lifelong_planner_v77 as planner
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics

PRIOR = ROOT / 'reports/controlled_predictive_target_horizon_v80'
DYNAMICS = ROOT / 'reports/controlled_predictive_decision_v78/supplied_dynamics.json'
METHODS = ('H2_ONLY', 'CURRENT', 'FROZEN_1', 'SHORT_REF', 'TERMINAL_REF')
ITERATIONS = (1, 2)


def save(path, value):
    path.write_text(json.dumps(value, allow_nan=False, separators=(',', ':')) + '\n')


def write_row(handle, value):
    handle.write(json.dumps(value, allow_nan=False, separators=(',', ':')) + '\n')


def select_roots(game, query, episode):
    steps = game['steps']
    return [dict(board=steps[index]['board'], reference_action=steps[index]['action'],
                 query=query, episode=episode, step=index)
            for index in sorted({len(steps)//3, 2*len(steps)//3}) if index < len(steps)]


def collect_behavior(parent, rule, lifecycle, iteration, folder, seen):
    started = perf_counter()
    roots, states = {query: [] for query in QUERIES}, set()
    work, planning_counts, outcomes = Counter(), Counter(), Counter()
    with gzip.open(folder / 'behavior_games.jsonl.gz', 'wt') as output:
        for query in QUERIES:
            for episode in range(12):
                seed = 8100000 + lifecycle*10000 + iteration*1000 + episode
                rng = random.Random(seed + 1000000)
                game_work = Counter()
                def act(board, step):
                    return parent.choose(board, query, rule, rng, work=game_work)['action']
                game = experience.run_episode(seed, act)
                write_row(output, dict(query=query, episode=episode, policy_iteration=parent.iteration,
                                       model_seed=seed+1000000, game=game, planning_counts=dict(game_work)))
                roots[query].extend(select_roots(game, query, episode))
                states.update(tuple(step['board']) for step in game['steps'])
                work.update(game['work'])
                planning_counts.update(game_work)
                outcomes[game['status']] += 1
    coverage = dict(unique_observations=len(states), new_vs_prior=len(states-seen),
                    root_observations=len({tuple(root['board']) for rs in roots.values() for root in rs}))
    seen.update(states)
    return roots, dict(policy_iteration=parent.iteration, games=24, outcomes=dict(outcomes),
        work=dict(work), planning_counts=dict(planning_counts), state_coverage=coverage,
        seconds=perf_counter()-started)


def collect_branches(roots, parent, rule, lifecycle, iteration, folder):
    started = perf_counter()
    rows, logs = [], []
    work, continuation, known, outcomes = Counter(), Counter(), Counter(), Counter()
    with gzip.open(folder / 'branch_games.jsonl.gz', 'wt') as output:
        for query, query_roots in roots.items():
            for index, root in enumerate(query_roots):
                labels, raw, log = sample_root(root, parent, rule, lifecycle, iteration, index)
                for trajectory in raw:
                    write_row(output, dict(root=root, **trajectory))
                rows.extend(labels)
                logs.append(dict(root=root, root_index=index, **log))
                work.update(log['ground_work'])
                continuation.update(log['continuation_work'])
                known.update(log['known_model_counts'])
                outcomes.update(log['outcomes'])
                if (index+1) % 6 == 0:
                    print(json.dumps(dict(phase='branches', lifecycle=lifecycle, iteration=iteration,
                        query=query, completed_query_roots=index+1,
                        transitions=work['sampled_transitions'], outcomes=dict(outcomes))), flush=True)
    save(folder / 'root_logs.json', logs)
    with gzip.open(folder / 'advantage_rows.jsonl.gz', 'wt') as output:
        for row in rows:
            write_row(output, row)
    return rows, logs, dict(continuation_iteration=parent.iteration, roots=len(logs),
        trajectories=sum(log['trajectories'] for log in logs),
        censored_roots=sum(log['censored_root'] for log in logs), outcomes=dict(outcomes),
        work=dict(work), continuation_work=dict(continuation), known_model_counts=dict(known),
        seconds=perf_counter()-started)


def dataset_summary(rows, logs, seen_roots):
    pairs = [deltas for log in logs for deltas in log['pair_deltas'].values()]
    root_boards = {tuple(log['root']['board']) for log in logs}
    coverage = dict(unique=len(root_boards), new_vs_prior=len(root_boards-seen_roots))
    seen_roots.update(root_boards)
    return dict(records=len(rows), training_records=sum(row['episode'] % 5 != 4 for row in rows),
        heldout_records=sum(row['episode'] % 5 == 4 for row in rows),
        queries={query: dict(training_records=sum(row['query'] == query and row['episode'] % 5 != 4 for row in rows),
            heldout_records=sum(row['query'] == query and row['episode'] % 5 == 4 for row in rows),
            nonzero_failure_deltas=sum(row['query'] == query and row['target'][1] != 0 for row in rows),
            nonzero_success_deltas=sum(row['query'] == query and row['target'][2] != 0 for row in rows))
            for query in QUERIES}, root_state_coverage=coverage,
        replica_noise=dict(pairs=len(pairs), reward_sign_reversals=sum(pair[0][0]*pair[1][0] < 0 for pair in pairs),
            mean_abs_component_difference=[sum(abs(pair[0][i]-pair[1][i]) for pair in pairs)/len(pairs)
                for i in range(3)] if pairs else None))


def evaluate_game(method, model, rule, lifecycle, replica, query_name, max_steps=2000):
    seed = 8190000 + lifecycle*100 + replica
    rng, work, decisions = random.Random(seed+1000000), Counter(), []
    query = QUERIES[query_name]
    before = dict(model.counts) if isinstance(model, ConsequenceModel) else {}
    def act(board, step):
        if isinstance(model, Policy):
            choice = model.choose(board, query_name, rule, rng, work=work)
            decision = {key: choice[key] for key in ('action', 'reference_action', 'advantage', 'value', 'iteration')}
        else:
            choice = planner.choose(board, query, model, rule, rng, depth=2, work=work)
            decision = {key: choice[key] for key in ('action', 'policy', 'metrics', 'value')}
        decisions.append(decision)
        return choice['action']
    game = experience.run_episode(seed, act, max_steps=max_steps)
    utility = (query['reward_weight']*game['return_score']/2048
        - query['failure_penalty']*(game['status'] == 'LOST')
        + query['goal_bonus']*(game['status'] == 'WON'))
    row = dict(seed=seed, replica=replica, query=query_name, score=game['return_score'],
        status=game['status'], steps=game['steps_count'], max_rank=max(game['final_board']),
        utility=utility, seconds=game['seconds'], environment_counts=game['work'], planning_counts=dict(work),
        prediction_counts={key: value-before.get(key, 0) for key, value in model.counts.items()
            if value != before.get(key, 0)} if isinstance(model, ConsequenceModel) else {},
        decisions=len(decisions), top_layer_overrides=sum(d['action'] != d['reference_action']
            for d in decisions if 'reference_action' in d))
    return row, dict(method=method, query=query_name, episode=game, decisions=decisions)


def lifecycle_run(lifecycle, directory, rule, prior_run, progress):
    folder = directory / f'life_{lifecycle}'
    folder.mkdir()
    parent, frozen = Policy.base(), None
    cumulative, eval_seconds, seen, seen_roots = Counter(), Counter(), set(), set()
    frozen_cost = {}
    prior_life = next(row for row in prior_run['lifecycles'] if row['id'] == lifecycle)
    prior_costs = {scope+'_REF': {key: value for key, value in prior_life['stages'][-1]['methods'][scope+'_PLAN']['costs'].items()
        if key not in ('evaluation_seconds', 'total_seconds')} for scope in ('SHORT', 'TERMINAL')}
    prior_models = {}
    for scope in ('SHORT', 'TERMINAL'):
        path = PRIOR / f'life_{lifecycle}/checkpoint_75/{scope}.json'
        payload = json.loads(path.read_text())
        save(folder / f'{scope}_REF.json', payload)
        prior_models[scope+'_REF'] = ConsequenceModel.from_payload(payload)
    result = dict(id=lifecycle, rounds=[])
    for iteration in ITERATIONS:
        started = perf_counter()
        cpdir = folder / f'iteration_{iteration}'
        cpdir.mkdir()
        export_tick = perf_counter()
        save(cpdir / 'behavior_policy.json', parent.to_payload())
        cumulative['export_seconds'] += perf_counter()-export_tick
        roots, behavior = collect_behavior(parent, rule, lifecycle, iteration, cpdir, seen)
        print(json.dumps(dict(phase='behavior', lifecycle=lifecycle, iteration=iteration,
            outcomes=behavior['outcomes'], transitions=behavior['work']['sampled_transitions'])), flush=True)
        rows, logs, branches = collect_branches(roots, parent, rule, lifecycle, iteration, cpdir)
        dataset = dataset_summary(rows, logs, seen_roots)
        current, update = improve(parent, rows, iteration, rule)
        cumulative.update(behavior_acquisition_seconds=behavior['seconds'],
            branch_acquisition_seconds=branches['seconds'], fitting_seconds=update['seconds'])
        export_tick = perf_counter()
        save(cpdir / 'current_policy.json', current.to_payload())
        cumulative['export_seconds'] += perf_counter()-export_tick
        if iteration == 1:
            frozen = Policy.from_payload(current.to_payload())
            frozen_cost = dict(cumulative)
        stage = dict(iteration=iteration, behavior=behavior, branches=branches, dataset=dataset,
            update=update, methods={method: dict(games=[]) for method in METHODS})
        save(cpdir / 'learning.json', stage)
        print(json.dumps(dict(phase='learned', lifecycle=lifecycle, iteration=iteration,
            records=len(rows), training=update['training_records'], heldout=update['heldout_records'])), flush=True)
        deployed = dict(H2_ONLY=Policy.base(), CURRENT=Policy.from_payload(current.to_payload()),
            FROZEN_1=Policy.from_payload(frozen.to_payload()), **{name: ConsequenceModel.from_payload(model.to_payload())
                for name, model in prior_models.items()})
        histories = {}
        with gzip.open(cpdir / 'evaluation_games.jsonl.gz', 'wt') as output:
            for replica in range(2):
                for qi, query in enumerate(QUERIES):
                    offset = (lifecycle+iteration+replica+qi) % len(METHODS)
                    for method in METHODS[offset:] + METHODS[:offset]:
                        tick = perf_counter()
                        game, raw = evaluate_game(method, deployed[method], rule, lifecycle, replica, query)
                        write_row(output, raw)
                        output.flush()
                        eval_seconds[method] += perf_counter()-tick
                        stage['methods'][method]['games'].append(game)
                        histories[method, replica, query] = [(s['board'], s['action'], s['next_board']) for s in raw['episode']['steps']]
                        print(json.dumps(dict(phase='game', lifecycle=lifecycle, iteration=iteration,
                            method=method, query=query, replica=replica, score=game['score'], status=game['status'])), flush=True)
        stage['query_response'] = {method: dict(pairs=2, identical_trajectory_pairs=sum(
            histories[method, replica, 'reward'] == histories[method, replica, 'risk_goal'] for replica in range(2)))
            for method in METHODS}
        for method, record in stage['methods'].items():
            costs = dict(evaluation_seconds=eval_seconds[method])
            if method == 'CURRENT':
                costs.update(cumulative)
            elif method == 'FROZEN_1':
                costs.update(frozen_cost)
            elif method.endswith('_REF'):
                costs.update({'prior_'+key: value for key, value in prior_costs[method].items()})
            costs['total_seconds'] = sum(costs.values())
            record['costs'] = costs
        stage['phase_seconds'] = perf_counter()-started
        result['rounds'].append(stage)
        save(cpdir / 'round.json', stage)
        progress(result)
        parent = current
    return result


def snapshot(directory):
    paths = ['scripts/run_controlled_predictive_policy_iteration_v81.py',
        'scripts/analyze_controlled_predictive_policy_iteration_v81.py',
        'specs/ON_POLICY_ACTION_ADVANTAGES_V81.md',
        'src/acfqp/science/controlled_predictive_policy_advantage_v81.py',
        'src/acfqp/science/controlled_predictive_advantage_experience_v81.py',
        'src/acfqp/science/controlled_predictive_target_horizon_v80.py',
        'src/acfqp/science/controlled_predictive_decision_experience_v78.py']
    paths += [f'src/acfqp/science/controlled_predictive_lifelong{suffix}_v77.py'
              for suffix in ('', '_experience', '_planner')]
    paths += [f'src/acfqp/science/controlled_predictive_{name}_v{version}.py'
        for name, version in (('relational_dynamics', 69), ('effect_contract', 74),
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
    prior_run = json.loads((PRIOR / 'run.json').read_text())
    payload = json.loads(DYNAMICS.read_text())
    save(directory / 'supplied_dynamics.json', payload)
    rule = LearnedDynamics.from_payload(payload)
    report = dict(schema='acfqp.on_policy_action_advantages.v81', status='running',
        platform=platform.platform(), executable=sys.executable, python=sys.version,
        inherited_sources=dict(reference_construction=str(PRIOR), dynamics=str(DYNAMICS)),
        settings=dict(lifecycles=[0, 1, 2], iterations=list(ITERATIONS), methods=list(METHODS), queries=QUERIES,
            evaluation_replicas=2, behavior_games_per_query_per_round=12, branch_replicas=2,
            max_episode_steps=2000, branch_transition_ceiling=4608000), lifecycles=[])
    save(directory / 'run.json', report)
    for lifecycle in (0, 1, 2):
        def progress(partial):
            report['lifecycles'] = [life for life in report['lifecycles'] if life['id'] != lifecycle] + [partial]
            report['actual_wall_seconds'] = perf_counter()-started
            save(directory / 'run.json', report)
        progress(lifecycle_run(lifecycle, directory, rule, prior_run, progress))
    report.update(status='complete', actual_wall_seconds=perf_counter()-started)
    save(directory / 'run.json', report)
    print(json.dumps(dict(phase='complete', seconds=report['actual_wall_seconds'])), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    run(parser.parse_args().output)
