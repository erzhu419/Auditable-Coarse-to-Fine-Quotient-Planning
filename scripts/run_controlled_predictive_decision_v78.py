"""Fixed-budget branch acquisition and decision-based whole-model acceptance."""
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
from acfqp.science.controlled_predictive_lifelong_v77 import Knowledge, POLICIES
from acfqp.science import controlled_predictive_lifelong_experience_v77 as experience
from acfqp.science import controlled_predictive_lifelong_planner_v77 as planner
from acfqp.science.controlled_predictive_decision_experience_v78 import rollout_from_board
from acfqp.science import controlled_predictive_decision_update_v78 as update
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics

SOURCE = ROOT / 'reports/controlled_predictive_lifelong_v77'
METHODS = ('H2_ONLY', 'FROZEN_PLAN', 'FIXED_PLAN', 'MSE_PLAN', 'DECISION_PLAN')
CHECKPOINTS = (39, 75)
LIFECYCLES = (0, 1, 2)
QUERIES = dict(reward=dict(reward_weight=1., failure_penalty=0., goal_bonus=0.),
               risk_goal=dict(reward_weight=1., failure_penalty=4., goal_bonus=4.))


def save(path, value):
    path.write_text(json.dumps(value, allow_nan=False, separators=(',', ':')) + '\n')


def write_raw(handle, value):
    handle.write(json.dumps(value, allow_nan=False, separators=(',', ':')) + '\n')


def scalar(game, query):
    return (query['reward_weight'] * game['return_score'] / 2048
            - query['failure_penalty'] * (game['status'] == 'LOST')
            + query['goal_bonus'] * (game['status'] == 'WON'))


def clone(model, mode=None, checkpoint=None):
    result = Knowledge.from_payload(model.to_payload())
    if mode is not None:
        result.mode = mode
    if checkpoint is not None:
        result.checkpoint = checkpoint
    return result


def select_roots(history, frozen, rule, lifecycle, train_limit=12, validation_limit=8):
    started = perf_counter()
    roots = dict(training=[], validation=[])
    limits = dict(training=train_limit, validation=validation_limit)
    seen = set()
    work = Counter()
    detector = clone(frozen)
    observations = 0
    for row in history:
        episode = row['episode_index']
        stratum = 'validation' if episode % 5 == 4 else 'training'
        if len(roots[stratum]) >= limits[stratum]:
            continue
        steps = row['game']['steps']
        indices = sorted({k * (len(steps)-1) // 3 for k in range(4)})
        for step in indices:
            board = tuple(steps[step]['board'])
            if board in seen:
                continue
            observations += 1
            actions = {}
            for qi, (name, query) in enumerate(QUERIES.items()):
                seed = 780000000 + lifecycle*10000000 + episode*10000 + step*2 + qi
                a = planner.choose(board, query, detector, rule, random.Random(seed), work=work)
                b = planner.choose(board, query, None, rule, random.Random(seed), work=work)
                actions[name] = dict(frozen=a['action'], h2=b['action'])
            if any(a['frozen'] != a['h2'] for a in actions.values()):
                roots[stratum].append(dict(episode=episode, step=step, board=list(board),
                                            detector_actions=actions))
                seen.add(board)
            if len(roots[stratum]) >= limits[stratum]:
                break
    return roots, dict(observations=observations, selected={k: len(v) for k,v in roots.items()},
        planning_counts=dict(work), seconds=perf_counter()-started)


def acquire(roots, rule, lifecycle, stage_index, path):
    started = perf_counter()
    work, policy_work, outcomes = Counter(), Counter(), Counter()
    records, trajectories = [], 0
    with gzip.open(path, 'wt', encoding='utf-8') as handle:
        for ri, root in enumerate(roots):
            _, moves = rule.classify(tuple(root['board']), policy_work)
            for action, _, _ in sorted(moves):
                for policy in POLICIES:
                    for replica in range(2):
                        seed = 7810000000 + lifecycle*10000000 + stage_index*1000000 + ri*1000 + replica
                        def act(board, step):
                            return action if step == 0 else planner.policy_action(board, policy, rule, policy_work)
                        game = rollout_from_board(root['board'], seed, act)
                        labels = [r for r in experience.targets(game, policy, root['episode'], stride=10000)
                                  if r['anchor_step'] == 0]
                        for row in labels:
                            row.update(source='v78_branch', source_step=root['step'])
                        records.extend(labels)
                        trajectories += 1
                        outcomes[game['status']] += 1
                        work.update(game['work'])
                        write_raw(handle, dict(root=root, action=action, policy=policy,
                            replica=replica, game=game, labels=labels))
    return records, dict(roots=len(roots), trajectories=trajectories, records=len(records),
        success_labels=sum(r['target'][2] for r in records),
        failure_labels=sum(r['target'][1] for r in records), outcomes=dict(outcomes),
        work=dict(work), policy_work=dict(policy_work), seconds=perf_counter()-started)


def compare_rollouts(old_roots, new_roots, incumbent, candidate, rule, lifecycle, stage_index, path):
    started = perf_counter()
    work, planning_work, outcomes = Counter(), Counter(), Counter()
    pairs, trajectories = [], 0
    # Deployment predictions never mutate persistent training models or candidate logs.
    models = dict(incumbent=clone(incumbent), candidate=clone(candidate))
    with gzip.open(path, 'wt', encoding='utf-8') as handle:
        for si, (stratum, roots) in enumerate((('old', old_roots), ('new', new_roots))):
            for ri, root in enumerate(roots):
                for query_name, query in QUERIES.items():
                    for replica in range(2):
                        seed = 8820000000 + lifecycle*10000000 + stage_index*1000000 + si*100000 + ri*100 + replica
                        pair = dict(stratum=stratum, query=query_name, replica=replica,
                                    root_index=ri, episode=root['episode'], step=root['step'], seed=seed)
                        for name, model in models.items():
                            model_rng = random.Random(seed + 1000000000000)
                            decisions = []
                            def act(board, step):
                                choice = planner.choose(board, query, model, rule, model_rng, work=planning_work)
                                decisions.append(dict(action=choice['action'], metrics=choice['metrics']))
                                return choice['action']
                            game = rollout_from_board(root['board'], seed, act)
                            pair[name + '_utility'] = scalar(game, query)
                            pair[name + '_first_action'] = decisions[0]['action']
                            work.update(game['work'])
                            outcomes[game['status']] += 1
                            trajectories += 1
                            write_raw(handle, dict(stratum=stratum, root=root, query=query_name,
                                replica=replica, model=name, game=game, decisions=decisions))
                        pairs.append(pair)
    return pairs, dict(trajectories=trajectories, pairs=len(pairs), outcomes=dict(outcomes),
        first_action_disagreements=sum(p['candidate_first_action'] != p['incumbent_first_action'] for p in pairs),
        work=dict(work), planning_counts=dict(planning_work), seconds=perf_counter()-started)


def evaluate_game(method, model, rule, lifecycle, replica, query_name, max_steps=2000):
    seed = 7890000 + lifecycle*100 + replica
    model_rng = random.Random(seed + 1000000)
    counts, decisions = Counter(), []
    before = dict(model.counts) if model else {}
    query = QUERIES[query_name]
    def act(board, step):
        choice = planner.choose(board, query, model, rule, model_rng, work=counts)
        decisions.append(dict(action=choice['action'], metrics=choice['metrics'], value=choice['value']))
        return choice['action']
    game = experience.run_episode(seed, act, max_steps=max_steps)
    row = dict(seed=seed, replica=replica, query=query_name, status=game['status'],
        score=game['return_score'], steps=game['steps_count'], max_rank=max(game['final_board']),
        utility=scalar(game, query), seconds=game['seconds'], environment_counts=game['work'],
        planning_counts=dict(counts), prediction_counts={k: v-before.get(k, 0)
            for k,v in model.counts.items() if v != before.get(k, 0)} if model else {})
    return row, dict(method=method, query=query_name, episode=game, decisions=decisions)


def lifecycle_run(lifecycle, directory, rule, source_run, progress):
    folder = directory / f'life_{lifecycle}'
    folder.mkdir()
    with gzip.open(SOURCE / f'life_{lifecycle}/training_episodes.jsonl.gz', 'rt') as handle:
        history = [json.loads(line) for line in handle]
    history.sort(key=lambda r: r['episode_index'])
    initial_payload = json.loads((SOURCE / f'life_{lifecycle}/checkpoint_15/FROZEN.json').read_text())
    initial = Knowledge.from_payload(initial_payload)
    models = {mode: clone(initial, mode) for mode in ('FROZEN', 'FIXED', 'MSE', 'DECISION')}
    save(folder / 'initial_knowledge.json', initial_payload)
    old, old_selection = select_roots(history[:15], initial, rule, lifecycle, train_limit=0)
    old_roots = old['validation']
    save(folder / 'warmup_validation_roots.json', dict(roots=old_roots, selection=old_selection))
    natural = [record for r in history[:15]
               for record in experience.targets(r['game'], r['policy'], r['episode_index'])]
    probes = []
    result = dict(id=lifecycle, stages=[], warmup_selection=old_selection)
    previous = 15
    cumulative = Counter()
    cumulative['warmup_selection_seconds'] = old_selection['seconds']
    evaluation_seconds, serialization_seconds = Counter(), Counter()
    inherited = next(row for row in source_run['lifecycles'] if row['id'] == lifecycle)
    warmup_source = inherited['checkpoints'][0]['source_summary']
    init_seconds = inherited['checkpoints'][0]['initialization']['seconds']
    for stage_index, checkpoint in enumerate(CHECKPOINTS):
        tick = perf_counter()
        cpdir = folder / f'checkpoint_{checkpoint}'
        cpdir.mkdir()
        new_history = history[previous:checkpoint]
        natural.extend(record for r in new_history
                       for record in experience.targets(r['game'], r['policy'], r['episode_index']))
        roots, selection = select_roots(new_history, initial, rule, lifecycle)
        save(cpdir / 'roots.json', dict(training=roots['training'], new_validation=roots['validation'],
            old_validation=old_roots, selection=selection))
        extra, acquisition = acquire(roots['training'], rule, lifecycle, stage_index,
                                      cpdir / 'training_branches.jsonl.gz')
        probes.extend(extra)
        all_training = natural + probes
        candidate, candidate_log = update.fit_candidate(all_training, checkpoint)
        models['FIXED'], fixed_log = update.refresh_fixed(models['FIXED'], all_training, checkpoint)
        mse_log = update.mse_decision(models['MSE'], candidate, natural, previous)
        pairs, acceptance_work = compare_rollouts(old_roots, roots['validation'], models['DECISION'],
            candidate, rule, lifecycle, stage_index, cpdir / 'acceptance_episodes.jsonl.gz')
        decision_log = update.decision_acceptance(pairs)
        save(cpdir / 'candidate.json', candidate.to_payload())
        save(cpdir / 'acceptance_pairs.json', pairs)
        for mode, log in (('MSE', mse_log), ('DECISION', decision_log)):
            if log['accepted']:
                models[mode] = clone(candidate, mode, checkpoint)
            else:
                models[mode].checkpoint = checkpoint
        models['FROZEN'].checkpoint = checkpoint
        cumulative.update(selection_seconds=selection['seconds'], acquisition_seconds=acquisition['seconds'],
            candidate_fit_seconds=candidate_log['seconds'], fixed_update_seconds=fixed_log['seconds'],
            mse_acceptance_seconds=mse_log['seconds'], decision_rollout_seconds=acceptance_work['seconds'],
            decision_rule_seconds=decision_log['seconds'])
        source_summary = next(row['source_summary'] for row in inherited['checkpoints'] if row['episodes'] == checkpoint)
        stage = dict(episodes=checkpoint, source_summary=source_summary, selection=selection,
            training_branches=acquisition, candidate_log=candidate_log, fixed_log=fixed_log,
            mse_acceptance=mse_log, decision_acceptance=decision_log, acceptance_rollouts=acceptance_work,
            cumulative_new_seconds=dict(cumulative), cumulative_branch_records=len(probes),
            source_records=len(natural), models={}, methods={})
        for mode, model in models.items():
            serial_tick = perf_counter()
            path = cpdir / f'{mode}.json'
            save(path, model.to_payload())
            serialization_seconds[mode] += perf_counter()-serial_tick
            stage['models'][mode] = dict(nodes=sum(len(t['left']) for t in model.trees.values()),
                bytes=path.stat().st_size, checkpoint=model.checkpoint)
        save(cpdir / 'learning.json', stage)
        print(json.dumps(dict(phase='learned', lifecycle=lifecycle, episodes=checkpoint,
            training_roots=len(roots['training']), new_validation_roots=len(roots['validation']),
            branch_transitions=acquisition['work'].get('sampled_transitions', 0),
            acceptance_transitions=acceptance_work['work'].get('sampled_transitions', 0),
            mse_accepted=mse_log['accepted'], decision_accepted=decision_log['accepted'])), flush=True)
        deployed = {m: None if m == 'H2_ONLY' else clone(models[m.split('_')[0]]) for m in METHODS}
        stage['methods'] = {m: dict(games=[]) for m in METHODS}
        with gzip.open(cpdir / 'evaluation_episodes.jsonl.gz', 'wt', encoding='utf-8') as handle:
            for replica in range(2):
                for qi, query in enumerate(QUERIES):
                    offset = (lifecycle + stage_index + replica + qi) % len(METHODS)
                    for method in METHODS[offset:] + METHODS[:offset]:
                        eval_tick = perf_counter()
                        game, raw = evaluate_game(method, deployed[method], rule, lifecycle, replica, query)
                        write_raw(handle, raw)
                        handle.flush()
                        evaluation_seconds[method] += perf_counter()-eval_tick
                        stage['methods'][method]['games'].append(game)
                        print(json.dumps(dict(phase='game', lifecycle=lifecycle, episodes=checkpoint,
                            method=method, query=query, replica=replica, score=game['score'],
                            status=game['status'])), flush=True)
        for method, row in stage['methods'].items():
            mode = method.split('_')[0]
            costs = dict(evaluation_seconds=evaluation_seconds[method])
            if method != 'H2_ONLY':
                costs.update(inherited_source_seconds=warmup_source['seconds'] if mode == 'FROZEN' else source_summary['seconds'],
                    inherited_initial_fit_seconds=init_seconds, serialization_seconds=serialization_seconds[mode])
            if mode in ('FIXED', 'MSE', 'DECISION'):
                costs.update(selection_seconds=cumulative['selection_seconds'],
                             acquisition_seconds=cumulative['acquisition_seconds'])
            if mode == 'FIXED':
                costs['update_seconds'] = cumulative['fixed_update_seconds']
            if mode in ('MSE', 'DECISION'):
                costs['candidate_fit_seconds'] = cumulative['candidate_fit_seconds']
            if mode == 'MSE':
                costs['acceptance_seconds'] = cumulative['mse_acceptance_seconds']
            if mode == 'DECISION':
                costs.update(warmup_selection_seconds=cumulative['warmup_selection_seconds'],
                    acceptance_seconds=cumulative['decision_rollout_seconds'] + cumulative['decision_rule_seconds'])
            costs['total_seconds'] = sum(costs.values())
            row['costs'] = costs
        stage['phase_seconds'] = perf_counter()-tick
        result['stages'].append(stage)
        save(cpdir / 'checkpoint.json', stage)
        progress(result)
        previous, old_roots = checkpoint, roots['validation']
    return result


def snapshot(directory):
    paths = ['scripts/run_controlled_predictive_decision_v78.py',
             'scripts/analyze_controlled_predictive_decision_v78.py',
             'specs/DECISION_DRIVEN_KNOWLEDGE_V78.md']
    paths += [f'src/acfqp/science/controlled_predictive_decision_{name}_v78.py'
              for name in ('experience', 'update')]
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
    source_run = json.loads((SOURCE / 'run.json').read_text())
    rule_payload = json.loads((SOURCE / 'supplied_dynamics.json').read_text())
    save(directory / 'supplied_dynamics.json', rule_payload)
    rule = LearnedDynamics.from_payload(rule_payload)
    report = dict(schema='acfqp.decision_driven_learning.v78', status='running',
        platform=platform.platform(), executable=sys.executable, python=sys.version,
        inherited_source=str(SOURCE), settings=dict(lifecycles=list(LIFECYCLES),
            checkpoints=list(CHECKPOINTS), methods=list(METHODS), queries=QUERIES,
            evaluation_replicas=2, rollout_steps=32, max_episode_steps=2000,
            branch_transition_ceiling=79872), lifecycles=[])
    save(directory / 'run.json', report)
    for lifecycle in LIFECYCLES:
        def progress(partial):
            report['lifecycles'] = [r for r in report['lifecycles'] if r['id'] != lifecycle] + [partial]
            report['actual_wall_seconds'] = perf_counter()-started
            save(directory / 'run.json', report)
        progress(lifecycle_run(lifecycle, directory, rule, source_run, progress))
    report.update(status='complete', actual_wall_seconds=perf_counter()-started)
    save(directory / 'run.json', report)
    print(json.dumps(dict(phase='complete', seconds=report['actual_wall_seconds'])), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    run(parser.parse_args().output)
