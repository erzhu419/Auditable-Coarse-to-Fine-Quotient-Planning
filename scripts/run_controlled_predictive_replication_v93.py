"""Replicate fixed learners on new histories with equal extra sampling budgets."""
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
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'src'))
from scripts.run_controlled_predictive_fragments_v83 import acquire_batch
from acfqp.science.controlled_predictive_fragments_v83 import (
    FragmentController, OPTIONS, QUERIES, TRIGGER_EMPTY_CELLS, _utility,
)
from acfqp.science.controlled_predictive_joint_fragments_v84 import JointSelector
from acfqp.science.controlled_predictive_continuation_data_v91 import load_batch as load_unary
from acfqp.science.controlled_predictive_paired_continuation_data_v92 import load_batch as load_paired
from acfqp.science.controlled_predictive_paired_correction_v92 import collect_prefixes
from acfqp.science.controlled_predictive_replication_learning_v93 import learn, assert_shared_roots
from acfqp.science.controlled_predictive_replication_budget_v93 import acquire_extra, merge_rows
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics
from acfqp.science import controlled_predictive_lifelong_experience_v77 as experience

DYNAMICS = ROOT / 'reports/controlled_predictive_fragments_v83/supplied_dynamics.json'
LIFECYCLES, CHECKPOINTS = tuple(range(3, 9)), (6, 12)
METHODS = {6: ('H2_ONLY', 'MC', 'V91_DECOMPOSED', 'PAIR_ONLY', 'CORRECTED', 'MC_EXTRA'),
    12: ('H2_ONLY', 'MC', 'V91_DECOMPOSED', 'PAIR_ONLY', 'CORRECTED', 'MC_EXTRA',
         'CORRECTED_FROZEN_6', 'MC_EXTRA_FROZEN_6')}
REPLICAS, PREFIX_REPLICAS, WORKERS = 16, 64, 6


def save(path, value):
    path.write_text(json.dumps(value, allow_nan=False, separators=(',', ':')) + '\n')


def write_row(handle, row):
    handle.write(json.dumps(row, allow_nan=False, separators=(',', ':')) + '\n')


def gate_category(old, new):
    before, after = old not in (None, 'H2'), new not in (None, 'H2')
    if before and after:
        return 'same_fragment' if old == new else 'changed_fragment'
    return 'disabled' if before else 'enabled' if after else 'both_h2'


def evaluate_game(method, selector, rule, life, checkpoint, replica, query, max_steps=2000):
    seed = 9390000 + checkpoint * 10000 + life * 100 + replica
    controller = FragmentController(selector, query, rule, random.Random(seed + 1000000),
        mode='H2_ONLY' if method == 'H2_ONLY' else 'FRAGMENT')
    paths = []

    def act(board, step):
        before = controller.fragment_actions
        action = controller.choose(board, step)
        paths.append('fragment' if controller.fragment_actions > before else 'H2')
        return action

    game = experience.run_episode(seed, act, max_steps=max_steps)
    option, start = controller.selected_option, controller.initiation_step
    budget = int(option.split('_')[1]) if option not in (None, 'H2') else 0
    expected = min(budget, game['steps_count'] - start) if start is not None else 0
    correct = paths == ['fragment' if start is not None and start <= i < start + budget else 'H2'
                        for i in range(game['steps_count'])]
    outcome = [game['return_score'] / 2048, float(game['status'] == 'LOST'), float(game['status'] == 'WON')]
    row = dict(seed=seed, replica=replica, query=query, score=game['return_score'], status=game['status'],
        steps=game['steps_count'], max_rank=max(game['final_board']), utility=_utility(outcome, QUERIES[query]),
        seconds=game['seconds'], environment_counts=game['work'], planning_counts=dict(controller.work),
        selected_option=option, initiation_step=start, fragment_actions=controller.fragment_actions,
        duration_budget=budget, controller_events=len(controller.events),
        selector_checkpoint=selector.checkpoint if selector else None,
        committed_length_matches=correct and controller.fragment_actions == expected)
    return row, dict(method=method, query=query, episode=game,
        controller_events=controller.events, action_paths=paths)


def evaluate_checkpoint(life, checkpoint, folder, deployed, rule, replicas=REPLICAS, max_steps=2000):
    names = METHODS[checkpoint]
    methods = {name: dict(games=[], costs=dict(evaluation_seconds=0.0)) for name in names}
    contrasts = [('CORRECTED', other) for other in
        ('MC', 'MC_EXTRA', 'V91_DECOMPOSED', 'PAIR_ONLY', 'H2_ONLY')]
    contrasts += [('MC_EXTRA', 'MC'), ('MC_EXTRA', 'H2_ONLY'), ('PAIR_ONLY', 'MC')]
    if checkpoint == 12:
        contrasts += [('CORRECTED', 'CORRECTED_FROZEN_6'), ('MC_EXTRA', 'MC_EXTRA_FROZEN_6')]
    changes = {f'{left}_minus_{right}': [] for left, right in contrasts}
    wiring = dict(pretrigger_prefixes_match=True, committed_lengths_match=True,
        single_initiations=True, model_uniforms_aligned=True, same_choice_histories_match=True)
    with gzip.open(folder / 'evaluation_games.jsonl.gz', 'wt') as output:
        for replica in range(replicas):
            for qi, query in enumerate(QUERIES):
                offset = (life + checkpoint + replica + qi) % len(names)
                group, histories = {}, {}
                for method in names[offset:] + names[:offset]:
                    tick = perf_counter()
                    game, raw = evaluate_game(method, deployed[method], rule, life, checkpoint,
                        replica, query, max_steps=max_steps)
                    write_row(output, raw)
                    methods[method]['costs']['evaluation_seconds'] += perf_counter() - tick
                    methods[method]['games'].append(game)
                    group[method] = game, raw
                    histories[method] = [(s['board'], s['action'], s['next_board']) for s in raw['episode']['steps']]
                    wiring['committed_lengths_match'] &= game['committed_length_matches']
                    wiring['single_initiations'] &= game['controller_events'] <= 1
                    wiring['model_uniforms_aligned'] &= game['planning_counts']['model_uniform_draws'] == 4 * game['steps']
                h2_game, h2_raw = group['H2_ONLY']
                steps = h2_raw['episode']['steps']
                trigger = next((i for i, step in enumerate(steps)
                    if step['board'].count(0) <= TRIGGER_EMPTY_CELLS), None)
                for method in names[1:]:
                    game, raw = group[method]
                    if trigger is None:
                        same = histories[method] == histories['H2_ONLY'] and game['initiation_step'] is None
                    else:
                        same = (histories[method][:trigger] == histories['H2_ONLY'][:trigger]
                            and game['initiation_step'] == trigger
                            and raw['episode']['steps'][trigger]['board'] == steps[trigger]['board'])
                    wiring['pretrigger_prefixes_match'] &= same
                for left, right in contrasts:
                    old, new = group[right][0], group[left][0]
                    category = gate_category(old['selected_option'], new['selected_option'])
                    if category in ('both_h2', 'same_fragment'):
                        wiring['same_choice_histories_match'] &= histories[right] == histories[left]
                    changes[f'{left}_minus_{right}'].append(dict(seed=new['seed'], query=query, replica=replica,
                        category=category, old_option=old['selected_option'], new_option=new['selected_option']))
                print(json.dumps(dict(phase='paired_games', lifecycle=life, checkpoint=checkpoint,
                    query=query, replica=replica, scores={name: group[name][0]['score'] for name in names})), flush=True)
    if not all(wiring.values()):
        raise ValueError(f'controller execution mismatch: {wiring}')
    return dict(methods=methods, wiring=wiring, gate_changes=changes)


def root_key(root):
    return root['query'], root['episode'], tuple(root['board'])


def prefix_seed(root, life):
    return (193000000000 + life * 10000000
        + tuple(QUERIES).index(root['query']) * 1000000 + root['episode'] * 1000)


def acquire_prefix_batch(roots, rule, life, folder):
    started = perf_counter()
    pools, logs = {}, []
    ground, planning, outcomes = Counter(), Counter(), Counter()
    trajectories = 0
    with gzip.open(folder / 'training_prefix_games.jsonl.gz', 'wt') as output:
        for root in roots:
            # A censored original root supplies neither learner with a label.
            if root['censored']:
                continue
            prefixes, raw, log = collect_prefixes(root, rule, prefix_seed(root, life), replicas=PREFIX_REPLICAS)
            pools[root_key(root)] = prefixes
            metadata = {key: root[key] for key in ('board', 'query', 'episode')}
            for row in raw:
                write_row(output, dict(root=metadata, **row))
            logs.append(dict(root=metadata, log=log))
            ground.update(log['ground_work'])
            planning.update(log['planning_counts'])
            outcomes.update(log['outcomes'])
            trajectories += log['trajectories']
            print(json.dumps(dict(phase='training_prefix_root', lifecycle=life,
                query=root['query'], episode=root['episode'], transitions=log['ground_work']['sampled_transitions'])), flush=True)
    return pools, dict(roots=logs, ground_work=dict(ground), planning_counts=dict(planning),
        outcomes=dict(outcomes), trajectories=trajectories, seconds=perf_counter() - started)


def acquisition_cost(shared, prefixes=0, extra=0):
    return dict(source_transitions=shared['source'], base_branch_transitions=shared['branches'],
        prefix_transitions=prefixes, extra_terminal_transitions=extra,
        total_training_transitions=shared['source'] + shared['branches'] + prefixes + extra)


def lifecycle_run(life, directory, payload):
    started = perf_counter()
    folder = directory / f'life_{life}'
    folder.mkdir()
    rule = LearnedDynamics.from_payload(payload)
    roots, unary_rows, paired_rows, prefix_pools, extra_blocks = [], [], [], {}, []
    frozen, frozen_costs, cumulative = {}, {}, Counter()
    result = dict(id=life, checkpoints=[])
    previous = 0
    for checkpoint in CHECKPOINTS:
        stage_dir = folder / f'checkpoint_{checkpoint}'
        stage_dir.mkdir()
        _, source, branches = acquire_batch(9300 + life, previous, checkpoint, rule, stage_dir)
        tick = perf_counter()
        unary_roots, new_unary, unary_input = load_unary(stage_dir)
        batch_roots, new_paired, paired_input = load_paired(stage_dir)
        agreement = assert_shared_roots(unary_roots, batch_roots)
        preparation_seconds = perf_counter() - tick
        roots.extend(batch_roots)
        unary_rows.extend(new_unary)
        paired_rows.extend(new_paired)
        pools, prefix_log = acquire_prefix_batch(batch_roots, rule, life, stage_dir)
        prefix_pools.update(pools)
        selectors, paired_models, unary_models, labels, updates = learn(
            roots, unary_rows, paired_rows, prefix_pools, checkpoint)
        for family, models in (('paired', paired_models), ('unary', unary_models)):
            for name, model in models.items():
                save(stage_dir / f'{family}_{name}.json', model.to_payload())
        with gzip.open(stage_dir / 'extra_terminal_games.jsonl.gz', 'wt') as output:
            blocks, extra_log = acquire_extra(batch_roots, rule, life, checkpoint,
                prefix_log['ground_work'].get('sampled_transitions', 0), lambda row: write_row(output, row))
        extra_blocks.extend(blocks)
        extra_rows, extra_merge = merge_rows(roots, extra_blocks, checkpoint)
        selectors['MC_EXTRA'], updates['mc_extra'] = JointSelector.fit(extra_rows, checkpoint)
        labels['MC_EXTRA'] = extra_rows
        for name, selector in selectors.items():
            save(stage_dir / f'{name.lower()}_selector.json', selector.to_payload())
        with gzip.open(stage_dir / 'estimated_rows.jsonl.gz', 'wt') as output:
            for method, rows in labels.items():
                for row in rows:
                    write_row(output, dict(method=method, **row))
        cumulative.update(source=source['work'].get('sampled_transitions', 0),
            branches=branches['work'].get('sampled_transitions', 0),
            prefixes=prefix_log['ground_work'].get('sampled_transitions', 0),
            extra=extra_log['ground_work'].get('sampled_transitions', 0))
        costs = {name: acquisition_cost(cumulative,
            prefixes=cumulative['prefixes'] if name in ('PAIR_ONLY', 'CORRECTED') else 0,
            extra=cumulative['extra'] if name == 'MC_EXTRA' else 0) for name in selectors}
        costs['H2_ONLY'] = acquisition_cost(Counter())
        if checkpoint == 6:
            for name in ('CORRECTED', 'MC_EXTRA'):
                frozen[name + '_FROZEN_6'] = JointSelector.from_payload(selectors[name].to_payload())
                frozen_costs[name + '_FROZEN_6'] = dict(costs[name])
        deployed = dict(H2_ONLY=None, **selectors)
        if checkpoint == 12:
            deployed.update(frozen)
            costs.update(frozen_costs)
        eligible = [root for root in roots if not root['censored']]
        stage = dict(episodes=checkpoint, source_sampling_lifecycle=9300 + life,
            source=source, branches=branches,
            dataset=dict(roots=len(eligible), training_roots=sum(root['episode'] % 5 != 4 for root in eligible),
                heldout_roots=sum(root['episode'] % 5 == 4 for root in eligible), records=4 * len(eligible)),
            input=dict(unary=unary_input, paired=paired_input, agreement=agreement),
            input_preparation_seconds=preparation_seconds, acquisition_prefix=prefix_log,
            acquisition_extra=extra_log, extra_merge=extra_merge, updates=updates, method_acquisition=costs)
        save(stage_dir / 'learning.json', stage)
        stage.update(evaluate_checkpoint(life, checkpoint, stage_dir, deployed, rule))
        result['checkpoints'].append(stage)
        result['actual_wall_seconds'] = perf_counter() - started
        save(stage_dir / 'checkpoint.json', stage)
        save(folder / 'run.json', result)
        previous = checkpoint
    return result


def snapshot(directory):
    paths = ['scripts/run_controlled_predictive_replication_v93.py',
        'scripts/analyze_controlled_predictive_replication_v93.py',
        'scripts/run_controlled_predictive_fragments_v83.py',
        'scripts/analyze_controlled_predictive_evidence_learning_v88.py',
        'specs/INDEPENDENT_HISTORY_REPLICATION_V93.md']
    paths += [f'src/acfqp/science/controlled_predictive_{name}_v{version}.py' for name, version in (
        ('replication_learning', 93), ('replication_budget', 93),
        ('continuation_data', 91), ('continuation_value', 91), ('paired_continuation_data', 92),
        ('paired_continuation_value', 92), ('paired_correction', 92), ('budgeted_fragments', 86),
        ('joint_fragments', 84), ('fragments', 83), ('fragment_experience', 83),
        ('policy_advantage', 81), ('decision_experience', 78), ('lifelong', 77),
        ('lifelong_experience', 77), ('lifelong_planner', 77), ('relational_dynamics', 69),
        ('effect_contract', 74), ('grouped_contract', 73), ('local_contract', 72))]
    paths += ['src/acfqp/domains/standard_2048.py', 'src/acfqp/domains/g2048.py']
    for relative in paths:
        path = directory / 'source' / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, path)


def run(directory):
    started = perf_counter()
    directory.mkdir(parents=True, exist_ok=False)
    snapshot(directory)
    payload = json.loads(DYNAMICS.read_text())
    save(directory / 'supplied_dynamics.json', payload)
    report = dict(schema='acfqp.independent_history_replication.v93', status='running',
        platform=platform.platform(), executable=sys.executable, python=sys.version,
        inherited_dynamics=str(DYNAMICS),
        settings=dict(lifecycles=list(LIFECYCLES), checkpoints=list(CHECKPOINTS),
            methods_by_checkpoint=METHODS, queries=QUERIES, evaluation_replicas=REPLICAS,
            prefix_replicas=PREFIX_REPLICAS, source_episodes_per_query=12, branch_replicas=8,
            max_steps=2000, workers=WORKERS), lifecycles=[])
    save(directory / 'run.json', report)
    with ProcessPoolExecutor(max_workers=WORKERS) as pool:
        futures = [pool.submit(lifecycle_run, life, directory, payload) for life in LIFECYCLES]
        for future in as_completed(futures):
            report['lifecycles'].append(future.result())
            report['lifecycles'].sort(key=lambda row: row['id'])
            report['actual_wall_seconds'] = perf_counter() - started
            save(directory / 'run.json', report)
    report.update(status='complete', actual_wall_seconds=perf_counter() - started)
    save(directory / 'run.json', report)
    print(json.dumps(dict(phase='complete', seconds=report['actual_wall_seconds'])), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    run(parser.parse_args().output)

