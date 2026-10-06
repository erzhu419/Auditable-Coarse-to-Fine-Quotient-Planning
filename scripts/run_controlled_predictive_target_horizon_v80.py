"""Matched-observation short versus terminal consequence learning."""
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
from acfqp.science.controlled_predictive_target_horizon_v80 import (
    ConsequenceModel, paired_targets, fit_model,
)
from acfqp.science.controlled_predictive_training_suffix_v80 import complete_training_branch
from acfqp.science import controlled_predictive_lifelong_experience_v77 as experience
from acfqp.science import controlled_predictive_lifelong_planner_v77 as planner
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics

NATURAL = ROOT / 'reports/controlled_predictive_lifelong_v77'
BRANCHES = ROOT / 'reports/controlled_predictive_decision_v78'
CHECKPOINTS = (15, 39, 75)
METHODS = ('H2_ONLY', 'SHORT_PLAN', 'TERMINAL_PLAN', 'SHORT_FROZEN', 'TERMINAL_FROZEN')
SCOPES = ('SHORT', 'TERMINAL')
QUERIES = dict(reward=dict(reward_weight=1., failure_penalty=0., goal_bonus=0.),
               risk_goal=dict(reward_weight=1., failure_penalty=4., goal_bonus=4.))


def save(path, value):
    path.write_text(json.dumps(value, allow_nan=False, separators=(',', ':')) + '\n')


def write_row(handle, row):
    handle.write(json.dumps(row, allow_nan=False, separators=(',', ':')) + '\n')


def dataset_summary(rows, natural_games, branch_games, natural_discarded_records=0):
    return dict(paired_records=len(rows), training_records=sum(r['episode'] % 5 != 4 for r in rows),
        heldout_records=sum(r['episode'] % 5 == 4 for r in rows),
        natural_records=sum(r['source_kind'] == 'natural' for r in rows),
        branch_records=sum(r['source_kind'] == 'branch' for r in rows),
        natural_outcomes=dict(natural_games), branch_outcomes=dict(branch_games),
        censored_games=natural_games['CUTOFF'] + branch_games['CUTOFF'],
        discarded_records=natural_discarded_records + branch_games['CUTOFF'],
        targets={scope: dict(success_labels=sum(r[scope.lower()+'_target'][2] for r in rows),
            failure_labels=sum(r[scope.lower()+'_target'][1] for r in rows),
            failure_values=sorted({r[scope.lower()+'_target'][1] for r in rows}),
            success_values=sorted({r[scope.lower()+'_target'][2] for r in rows})) for scope in SCOPES})


def complete_batch(lifecycle, checkpoint, folder, rule):
    """Only V78 training branches enter this path; acceptance data are separate."""
    started = perf_counter()
    prefix_work, new_work, policy_work, outcomes, prefix_outcomes = (Counter() for _ in range(5))
    rows, trajectories, resumed, restoration_draws = [], 0, 0, 0
    if checkpoint == 15:
        return rows, dict(trajectories=0, resumed=0, prefix_work={}, new_work={}, policy_work={},
                          outcomes={}, prefix_outcomes={}, restoration_random_draws=0, seconds=0.)
    source = BRANCHES / f'life_{lifecycle}/checkpoint_{checkpoint}/training_branches.jsonl.gz'
    with gzip.open(source, 'rt', encoding='utf-8') as inputs, \
         gzip.open(folder / 'training_suffixes.jsonl.gz', 'wt', encoding='utf-8') as outputs:
        for index, line in enumerate(inputs):
            raw = json.loads(line)
            game, log, suffix = complete_training_branch(raw, rule)
            labels, _ = paired_targets(game, raw['policy'], raw['root']['episode'], anchor_only=True)
            for label in labels:
                label.update(source_kind='branch', source_checkpoint=checkpoint, prefix_line=index+1,
                             source_step=raw['root']['step'])
            rows.extend(labels)
            trajectories += 1
            resumed += int(log['resumed'])
            restoration_draws += log['restoration_random_draws']
            prefix_work.update(log['prefix_work'])
            new_work.update(log['new_work'])
            policy_work.update(log['policy_work'])
            outcomes[game['status']] += 1
            prefix_outcomes[raw['game']['status']] += 1
            write_row(outputs, dict(prefix_file=str(source.relative_to(ROOT)), prefix_line=index+1,
                root=raw['root'], action=raw['action'], policy=raw['policy'], replica=raw['replica'],
                suffix=suffix, completion=log, labels=labels))
    return rows, dict(trajectories=trajectories, resumed=resumed, prefix_work=dict(prefix_work),
        new_work=dict(new_work), policy_work=dict(policy_work), outcomes=dict(outcomes),
        prefix_outcomes=dict(prefix_outcomes), restoration_random_draws=restoration_draws,
        records=len(rows), seconds=perf_counter()-started)


def evaluate_game(method, model, rule, lifecycle, replica, query_name, max_steps=2000):
    seed = 8090000 + lifecycle*100 + replica
    model_rng = random.Random(seed + 1000000)
    query = QUERIES[query_name]
    planning_work, decisions = Counter(), []
    before = dict(model.counts) if model else {}
    def act(board, step):
        choice = planner.choose(board, query, model, rule, model_rng, depth=2, work=planning_work)
        decisions.append(dict(action=choice['action'], policy=choice['policy'],
                              metrics=choice['metrics'], value=choice['value']))
        return choice['action']
    game = experience.run_episode(seed, act, max_steps=max_steps)
    utility = (query['reward_weight'] * game['return_score'] / 2048
        - query['failure_penalty'] * (game['status'] == 'LOST')
        + query['goal_bonus'] * (game['status'] == 'WON'))
    row = dict(seed=seed, replica=replica, query=query_name, status=game['status'],
        score=game['return_score'], steps=game['steps_count'], max_rank=max(game['final_board']),
        utility=utility, seconds=game['seconds'], environment_counts=game['work'],
        planning_counts=dict(planning_work), prediction_counts={k: v-before.get(k, 0)
            for k,v in model.counts.items() if v != before.get(k, 0)} if model else {})
    return row, dict(method=method, query=query_name, episode=game, decisions=decisions)


def lifecycle_run(lifecycle, directory, rule, natural_run, branch_run, progress):
    folder = directory / f'life_{lifecycle}'
    folder.mkdir()
    load_tick = perf_counter()
    with gzip.open(NATURAL / f'life_{lifecycle}/training_episodes.jsonl.gz', 'rt') as handle:
        history = sorted((json.loads(line) for line in handle), key=lambda r: r['episode_index'])
    source = next(r for r in natural_run['lifecycles'] if r['id'] == lifecycle)
    branch_source = next(r for r in branch_run['lifecycles'] if r['id'] == lifecycle)
    cumulative = Counter(preparation_seconds=perf_counter()-load_tick)
    fit_seconds, export_seconds, eval_seconds = Counter(), Counter(), Counter()
    natural_outcomes, branch_outcomes = Counter(), Counter()
    rows, frozen, warmup_cost = [], {}, {}
    natural_discarded_records = 0
    result = dict(id=lifecycle, stages=[])
    previous = 0
    with gzip.open(folder / 'paired_rows.jsonl.gz', 'wt', encoding='utf-8') as row_file:
        for stage_index, checkpoint in enumerate(CHECKPOINTS):
            phase_tick = perf_counter()
            cpdir = folder / f'checkpoint_{checkpoint}'
            cpdir.mkdir()
            prep_tick = perf_counter()
            new_rows = []
            for raw in history[previous:checkpoint]:
                labels, label_log = paired_targets(raw['game'], raw['policy'], raw['episode_index'])
                natural_discarded_records += label_log['discarded_records']
                for row in labels:
                    row['source_kind'] = 'natural'
                new_rows.extend(labels)
                natural_outcomes[raw['game']['status']] += 1
            cumulative['preparation_seconds'] += perf_counter()-prep_tick
            branch_rows, completion = complete_batch(lifecycle, checkpoint, cpdir, rule)
            branch_outcomes.update(completion['outcomes'])
            cumulative['suffix_acquisition_seconds'] += completion['seconds']
            new_rows.extend(branch_rows)
            prep_tick = perf_counter()
            rows.extend(new_rows)
            for row in new_rows:
                write_row(row_file, row)
            row_file.flush()
            cumulative['preparation_seconds'] += perf_counter()-prep_tick
            stage = dict(episodes=checkpoint, branch_completion=completion,
                dataset=dataset_summary(rows, natural_outcomes, branch_outcomes, natural_discarded_records), models={}, methods={})
            source_summary = next(r['source_summary'] for r in source['checkpoints'] if r['episodes'] == checkpoint)
            stage['source_summary'] = source_summary
            if checkpoint > 15:
                old = next(r for r in branch_source['stages'] if r['episodes'] == checkpoint)
                cumulative['inherited_branch_seconds'] += old['training_branches']['seconds']
                cumulative['inherited_selection_seconds'] += old['selection']['seconds']
            current = {}
            for scope in SCOPES:
                model, log = fit_model(rows, checkpoint, target_scope=scope)
                current[scope] = model
                fit_seconds[scope] += log['seconds']
                export_tick = perf_counter()
                payload = model.to_payload()
                save(cpdir / f'{scope}.json', payload)
                export_seconds[scope] += perf_counter()-export_tick
                stage['models'][scope] = dict(fit_log=log,
                    nodes=sum(len(tree['left']) for tree in model.trees.values()),
                    bytes=(cpdir / f'{scope}.json').stat().st_size)
                if checkpoint == 15:
                    frozen[scope] = ConsequenceModel.from_payload(payload)
                    warmup_cost[scope] = dict(inherited_natural_seconds=source_summary['seconds'],
                        preparation_seconds=cumulative['preparation_seconds'],
                        fitting_seconds=log['seconds'], export_seconds=export_seconds[scope])
            stage['cumulative_new_seconds'] = dict(cumulative)
            save(cpdir / 'learning.json', stage)
            print(json.dumps(dict(phase='learned', lifecycle=lifecycle, episodes=checkpoint,
                paired_records=len(rows), new_suffix_transitions=completion['new_work'].get('sampled_transitions', 0),
                terminal_success_labels=stage['dataset']['targets']['TERMINAL']['success_labels'],
                branch_outcomes=dict(branch_outcomes))), flush=True)
            deployed = {}
            for method in METHODS:
                if method == 'H2_ONLY':
                    deployed[method] = None
                else:
                    scope, mode = method.split('_')
                    original = frozen[scope] if mode == 'FROZEN' else current[scope]
                    deployed[method] = ConsequenceModel.from_payload(original.to_payload())
                stage['methods'][method] = dict(games=[])
            histories = {}
            with gzip.open(cpdir / 'evaluation_episodes.jsonl.gz', 'wt', encoding='utf-8') as eval_file:
                for replica in range(2):
                    for qi, query in enumerate(QUERIES):
                        offset = (lifecycle+stage_index+replica+qi) % len(METHODS)
                        for method in METHODS[offset:] + METHODS[:offset]:
                            eval_tick = perf_counter()
                            game, raw = evaluate_game(method, deployed[method], rule, lifecycle, replica, query)
                            write_row(eval_file, raw)
                            eval_file.flush()
                            eval_seconds[method] += perf_counter()-eval_tick
                            stage['methods'][method]['games'].append(game)
                            histories[method, replica, query] = [(s['board'], s['action'], s['next_board'])
                                                               for s in raw['episode']['steps']]
                            print(json.dumps(dict(phase='game', lifecycle=lifecycle, episodes=checkpoint,
                                method=method, query=query, replica=replica, score=game['score'],
                                status=game['status'])), flush=True)
            stage['query_response'] = {method: dict(pairs=2, identical_trajectory_pairs=sum(
                histories[method, replica, 'reward'] == histories[method, replica, 'risk_goal']
                for replica in range(2))) for method in METHODS}
            for method, record in stage['methods'].items():
                costs = dict(evaluation_seconds=eval_seconds[method])
                if method != 'H2_ONLY':
                    scope, mode = method.split('_')
                    if mode == 'FROZEN':
                        costs.update(warmup_cost[scope])
                    else:
                        costs.update(inherited_natural_seconds=source_summary['seconds'],
                            inherited_branch_seconds=cumulative['inherited_branch_seconds'],
                            inherited_selection_seconds=cumulative['inherited_selection_seconds'],
                            inherited_detector_fit_seconds=source['checkpoints'][0]['initialization']['seconds'] if checkpoint > 15 else 0.,
                            preparation_seconds=cumulative['preparation_seconds'],
                            suffix_acquisition_seconds=cumulative['suffix_acquisition_seconds'],
                            fitting_seconds=fit_seconds[scope], export_seconds=export_seconds[scope])
                costs['total_seconds'] = sum(costs.values())
                record['costs'] = costs
            stage['phase_seconds'] = perf_counter()-phase_tick
            result['stages'].append(stage)
            save(cpdir / 'checkpoint.json', stage)
            progress(result)
            previous = checkpoint
    return result


def snapshot(directory):
    paths = ['scripts/run_controlled_predictive_target_horizon_v80.py',
             'scripts/analyze_controlled_predictive_target_horizon_v80.py',
             'specs/TARGET_HORIZON_LEARNING_V80.md',
             'src/acfqp/science/controlled_predictive_target_horizon_v80.py',
             'src/acfqp/science/controlled_predictive_training_suffix_v80.py',
             'src/acfqp/science/controlled_predictive_terminal_continuation_v79.py']
    paths += [f'src/acfqp/science/controlled_predictive_lifelong{suffix}_v77.py'
              for suffix in ('', '_experience', '_planner')]
    paths += ['src/acfqp/science/controlled_predictive_relational_dynamics_v69.py',
              'src/acfqp/science/controlled_predictive_effect_contract_v74.py',
              'src/acfqp/science/controlled_predictive_grouped_contract_v73.py',
              'src/acfqp/science/controlled_predictive_local_contract_v72.py',
              'src/acfqp/domains/standard_2048.py', 'src/acfqp/domains/g2048.py']
    for relative in paths:
        target = directory / 'source' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)


def run(directory):
    started = perf_counter()
    directory.mkdir(parents=True, exist_ok=False)
    snapshot(directory)
    natural_run = json.loads((NATURAL / 'run.json').read_text())
    branch_run = json.loads((BRANCHES / 'run.json').read_text())
    payload = json.loads((BRANCHES / 'supplied_dynamics.json').read_text())
    save(directory / 'supplied_dynamics.json', payload)
    rule = LearnedDynamics.from_payload(payload)
    report = dict(schema='acfqp.target_horizon_learning.v80', status='running',
        platform=platform.platform(), python=sys.version, executable=sys.executable,
        inherited_sources=dict(natural=str(NATURAL), training_branches=str(BRANCHES)),
        settings=dict(lifecycles=[0, 1, 2], checkpoints=list(CHECKPOINTS), methods=list(METHODS),
            queries=QUERIES, evaluation_replicas=2, feature_context_horizon=30,
            max_episode_steps=2000, new_branch_transition_ceiling=2700096), lifecycles=[])
    save(directory / 'run.json', report)
    for lifecycle in (0, 1, 2):
        def progress(partial):
            report['lifecycles'] = [r for r in report['lifecycles'] if r['id'] != lifecycle] + [partial]
            report['actual_wall_seconds'] = perf_counter()-started
            save(directory / 'run.json', report)
        progress(lifecycle_run(lifecycle, directory, rule, natural_run, branch_run, progress))
    report.update(status='complete', actual_wall_seconds=perf_counter()-started)
    save(directory / 'run.json', report)
    print(json.dumps(dict(phase='complete', seconds=report['actual_wall_seconds'])), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    run(parser.parse_args().output)
