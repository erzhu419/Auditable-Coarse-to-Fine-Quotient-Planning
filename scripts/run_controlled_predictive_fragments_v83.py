"""Acquire and learn single terminating fragments on a shared observable trigger."""
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
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
from acfqp.science.controlled_predictive_fragments_v83 import (
    Selector, FragmentController, OPTIONS, QUERIES, TRIGGER_EMPTY_CELLS,
)
from acfqp.science.controlled_predictive_fragment_experience_v83 import collect_source, sample_root
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics
from acfqp.science import controlled_predictive_lifelong_experience_v77 as experience

CHECKPOINTS = (6, 12)
METHODS = ('H2_ONLY', 'ONE_STEP', 'FRAGMENT', 'FROZEN_6', 'FIXED_SPACE4')
DYNAMICS = ROOT / 'reports/controlled_predictive_policy_iteration_v81/supplied_dynamics.json'


def save(path, value):
    path.write_text(json.dumps(value, allow_nan=False, separators=(',', ':'))+'\n')


def write_row(handle, row):
    handle.write(json.dumps(row, allow_nan=False, separators=(',', ':'))+'\n')


def evaluate_game(method, selector, rule, lifecycle, replica, query, max_steps=2000):
    seed = 8390000 + lifecycle*100 + replica
    controller = FragmentController(selector, query, rule, random.Random(seed+1000000),
        mode='FRAGMENT' if method == 'FROZEN_6' else method)
    paths = []
    def act(board, step):
        previous = controller.fragment_actions
        action = controller.choose(board, step)
        paths.append('fragment' if controller.fragment_actions > previous else 'H2')
        return action
    game = experience.run_episode(seed, act, max_steps=max_steps)
    q = QUERIES[query]
    utility = (q['reward_weight']*game['return_score']/2048
        - q['failure_penalty']*(game['status'] == 'LOST') + q['goal_bonus']*(game['status'] == 'WON'))
    option, start = controller.selected_option, controller.initiation_step
    budget = int(option.split('_')[1]) if option not in (None, 'H2') else 0
    expected = min(budget, game['steps_count']-start) if start is not None else 0
    correct_path = paths == ['fragment' if start is not None and start <= index < start+budget else 'H2'
                            for index in range(game['steps_count'])]
    row = dict(seed=seed, replica=replica, query=query, score=game['return_score'], status=game['status'],
        steps=game['steps_count'], max_rank=max(game['final_board']), utility=utility, seconds=game['seconds'],
        environment_counts=game['work'], planning_counts=dict(controller.work), selected_option=option,
        initiation_step=start, fragment_actions=controller.fragment_actions, duration_budget=budget,
        controller_events=len(controller.events), selector_checkpoint=selector.checkpoint if selector else None,
        committed_length_matches=correct_path and controller.fragment_actions == expected)
    raw = dict(method=method, query=query, episode=game, controller_events=controller.events, action_paths=paths)
    return row, raw


def acquire_batch(lifecycle, previous, checkpoint, rule, folder):
    source_tick = perf_counter()
    source_work, source_planning, source_outcomes = Counter(), Counter(), Counter()
    roots = []
    with gzip.open(folder / 'source_games.jsonl.gz', 'wt') as output:
        for query in QUERIES:
            for episode in range(previous, checkpoint):
                root, raw, log = collect_source(lifecycle, episode, query, rule)
                write_row(output, raw)
                source_work.update(log['ground_work'])
                source_planning.update(log['planning_counts'])
                source_outcomes.update(log['outcomes'])
                if root is not None:
                    roots.append(root)
    source = dict(games=(checkpoint-previous)*len(QUERIES), roots=len(roots), outcomes=dict(source_outcomes),
        work=dict(source_work), planning_counts=dict(source_planning), seconds=perf_counter()-source_tick)
    save(folder / 'roots.json', roots)
    branch_tick = perf_counter()
    work, planning, outcomes = Counter(), Counter(), Counter()
    rows, logs, trajectories, censored = [], [], 0, 0
    with gzip.open(folder / 'branch_games.jsonl.gz', 'wt') as output:
        for index, root in enumerate(roots):
            labels, raw, log = sample_root(root, rule, lifecycle)
            for trajectory in raw:
                write_row(output, dict(root=root, **trajectory))
            rows.extend(labels)
            logs.append(dict(root=root, **log))
            work.update(log['ground_work'])
            planning.update(log['planning_counts'])
            outcomes.update(log['outcomes'])
            trajectories += log['trajectories']
            censored += int(log['censored_root'])
            print(json.dumps(dict(phase='root', lifecycle=lifecycle, checkpoint=checkpoint,
                completed_roots=index+1, roots=len(roots), transitions=work['sampled_transitions'],
                outcomes=dict(outcomes))), flush=True)
    save(folder / 'root_logs.json', logs)
    with gzip.open(folder / 'new_rows.jsonl.gz', 'wt') as output:
        for row in rows:
            write_row(output, row)
    return rows, source, dict(roots=len(roots), trajectories=trajectories, censored_roots=censored,
        outcomes=dict(outcomes), work=dict(work), planning_counts=dict(planning), seconds=perf_counter()-branch_tick)


def lifecycle_run(lifecycle, directory, payload):
    started = perf_counter()
    folder = directory / f'life_{lifecycle}'
    folder.mkdir()
    rule = LearnedDynamics.from_payload(payload)
    rows, frozen, frozen_cost = [], None, {}
    cumulative, eval_seconds = Counter(), Counter()
    result = dict(id=lifecycle, checkpoints=[])
    previous = 0
    for checkpoint in CHECKPOINTS:
        tick = perf_counter()
        cpdir = folder / f'checkpoint_{checkpoint}'
        cpdir.mkdir()
        new_rows, source, branches = acquire_batch(lifecycle, previous, checkpoint, rule, cpdir)
        rows.extend(new_rows)
        current, update = Selector.fit(rows, checkpoint)
        cumulative.update(source_seconds=source['seconds'], branch_seconds=branches['seconds'], fitting_seconds=update['seconds'])
        export_tick = perf_counter()
        save(cpdir / 'selector.json', current.to_payload())
        cumulative['export_seconds'] += perf_counter()-export_tick
        if frozen is None:
            frozen = Selector.from_payload(current.to_payload())
            frozen_cost = dict(cumulative)
        dataset = dict(records=len(rows), training_records=sum(row['episode']%5 != 4 for row in rows),
            heldout_records=sum(row['episode']%5 == 4 for row in rows))
        stage = dict(episodes=checkpoint, source=source, branches=branches, dataset=dataset, update=update,
                     methods={method: dict(games=[]) for method in METHODS})
        save(cpdir / 'learning.json', stage)
        deployed = {method: (Selector.from_payload((frozen if method == 'FROZEN_6' else current).to_payload())
                    if method in ('ONE_STEP', 'FRAGMENT', 'FROZEN_6') else None) for method in METHODS}
        histories = {}
        wiring = dict(pretrigger_prefixes_match=True, committed_lengths_match=True,
                      single_initiations=True, model_uniforms_aligned=True)
        with gzip.open(cpdir / 'evaluation_games.jsonl.gz', 'wt') as output:
            for replica in range(2):
                for qi, query in enumerate(QUERIES):
                    offset = (lifecycle+checkpoint+replica+qi)%len(METHODS)
                    group = {}
                    for method in METHODS[offset:]+METHODS[:offset]:
                        eval_tick = perf_counter()
                        game, raw = evaluate_game(method, deployed[method], rule, lifecycle, replica, query)
                        write_row(output, raw)
                        output.flush()
                        eval_seconds[method] += perf_counter()-eval_tick
                        stage['methods'][method]['games'].append(game)
                        group[method] = (game, raw)
                        history = [(step['board'],step['action'],step['next_board']) for step in raw['episode']['steps']]
                        histories[method, replica, query] = history
                        wiring['committed_lengths_match'] &= game['committed_length_matches']
                        wiring['single_initiations'] &= game['controller_events'] <= 1
                        wiring['model_uniforms_aligned'] &= game['planning_counts']['model_uniform_draws'] == 4*game['steps']
                        print(json.dumps(dict(phase='game', lifecycle=lifecycle, checkpoint=checkpoint, method=method,
                            query=query, replica=replica, score=game['score'], status=game['status'],
                            option=game['selected_option'])), flush=True)
                    h2_steps = group['H2_ONLY'][1]['episode']['steps']
                    trigger = next((i for i,s in enumerate(h2_steps) if s['board'].count(0) <= TRIGGER_EMPTY_CELLS), None)
                    for method, (game, raw) in group.items():
                        if method == 'H2_ONLY':
                            continue
                        if trigger is None:
                            same = histories[method, replica, query] == histories['H2_ONLY', replica, query]
                            same &= game['initiation_step'] is None
                        else:
                            same = histories[method, replica, query][:trigger] == histories['H2_ONLY', replica, query][:trigger]
                            same &= game['initiation_step'] == trigger
                            same &= raw['episode']['steps'][trigger]['board'] == h2_steps[trigger]['board']
                        wiring['pretrigger_prefixes_match'] &= same
        assert all(wiring.values()), wiring
        stage['wiring'] = wiring
        stage['query_response'] = {method: dict(pairs=2, identical_trajectory_pairs=sum(
            histories[method, replica, 'reward'] == histories[method, replica, 'risk_goal'] for replica in range(2)))
            for method in METHODS}
        for method, record in stage['methods'].items():
            costs = dict(evaluation_seconds=eval_seconds[method])
            if method in ('FRAGMENT', 'ONE_STEP'):
                costs.update(cumulative)
            elif method == 'FROZEN_6':
                costs.update(frozen_cost)
            costs['total_seconds'] = sum(costs.values())
            record['costs'] = costs
        stage['phase_seconds'] = perf_counter()-tick
        result['checkpoints'].append(stage)
        result['actual_wall_seconds'] = perf_counter()-started
        save(cpdir / 'checkpoint.json', stage)
        save(folder / 'run.json', result)
        previous = checkpoint
    return result


def snapshot(directory):
    paths = ['scripts/run_controlled_predictive_fragments_v83.py', 'scripts/analyze_controlled_predictive_fragments_v83.py',
             'specs/TERMINATING_POLICY_FRAGMENTS_V83.md']
    paths += [f'src/acfqp/science/controlled_predictive_{name}_v{version}.py' for name, version in (
        ('fragments',83),('fragment_experience',83),('policy_advantage',81),('decision_experience',78),
        ('lifelong',77),('lifelong_experience',77),('lifelong_planner',77),('relational_dynamics',69),
        ('effect_contract',74),('grouped_contract',73),('local_contract',72))]
    paths += ['src/acfqp/domains/standard_2048.py','src/acfqp/domains/g2048.py']
    for relative in paths:
        path = directory/'source'/relative
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT/relative, path)


def run(directory):
    started = perf_counter()
    directory.mkdir(parents=True, exist_ok=False)
    snapshot(directory)
    payload = json.loads(DYNAMICS.read_text())
    save(directory/'supplied_dynamics.json', payload)
    report = dict(schema='acfqp.terminating_fragments.v83', status='running', platform=platform.platform(),
        executable=sys.executable, python=sys.version, inherited_dynamics=str(DYNAMICS),
        settings=dict(lifecycles=[0,1,2], checkpoints=list(CHECKPOINTS), methods=list(METHODS), queries=QUERIES,
            evaluation_replicas=2, source_episodes_per_query=12, branch_replicas=8, options=list(OPTIONS),
            trigger_empty_cells=TRIGGER_EMPTY_CELLS, max_steps=2000, workers=3), lifecycles=[])
    save(directory/'run.json', report)
    with ProcessPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(lifecycle_run, life, directory, payload): life for life in (0,1,2)}
        for future in as_completed(futures):
            report['lifecycles'].append(future.result())
            report['lifecycles'].sort(key=lambda life: life['id'])
            report['actual_wall_seconds'] = perf_counter()-started
            save(directory/'run.json', report)
    report.update(status='complete', actual_wall_seconds=perf_counter()-started)
    save(directory/'run.json', report)
    print(json.dumps(dict(phase='complete', seconds=report['actual_wall_seconds'])), flush=True)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    run(parser.parse_args().output)
