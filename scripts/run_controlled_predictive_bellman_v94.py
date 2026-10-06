"""Matched full-return and warm-started Bellman H2 value learning."""
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

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'src'))
from acfqp.science.controlled_predictive_fragments_v83 import (
    FragmentController, OPTIONS, QUERIES, TRIGGER_EMPTY_CELLS, _utility,
)
from acfqp.science.controlled_predictive_fragment_experience_v83 import sample_root
from acfqp.science.controlled_predictive_joint_fragments_v84 import JointSelector
from acfqp.science.controlled_predictive_continuation_data_v91 import extract_prefix
from acfqp.science.controlled_predictive_bellman_data_v94 import load_batch
from acfqp.science.controlled_predictive_bellman_value_v94 import fit_models, fit_heads
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics
from acfqp.science import controlled_predictive_lifelong_experience_v77 as experience

SOURCE = ROOT / 'reports/controlled_predictive_replication_v93'
LIFECYCLES, CHECKPOINTS = tuple(range(3, 9)), (6, 12)
VALUE_METHODS = ('MC_TAIL', 'FQE')
METHODS = {6: ('H2_ONLY', 'MC', 'MC_EXTRA', 'V91_DECOMPOSED', 'V92_CORRECTED', 'MC_TAIL', 'FQE'),
    12: ('H2_ONLY', 'MC', 'MC_EXTRA', 'V91_DECOMPOSED', 'V92_CORRECTED', 'MC_TAIL', 'FQE',
         'MC_TAIL_FROZEN_6', 'FQE_FROZEN_6')}
REPLICAS, REFERENCE_REPLICAS, VALIDATION_ROOTS_PER_QUERY, WORKERS = 16, 16, 2, 6
ITERATIONS = 128


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
    seed = 9490000 + checkpoint * 10000 + life * 100 + replica
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
    contrasts = [('FQE', other) for other in
        ('MC_TAIL', 'MC', 'MC_EXTRA', 'H2_ONLY', 'V91_DECOMPOSED', 'V92_CORRECTED')]
    contrasts += [('MC_TAIL', 'V91_DECOMPOSED'), ('MC_TAIL', 'H2_ONLY')]
    if checkpoint == 12:
        contrasts += [(method, method + '_FROZEN_6') for method in VALUE_METHODS]
    validation_roots, missing_roots = [], []
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
                if checkpoint == 12 and replica < VALIDATION_ROOTS_PER_QUERY:
                    metadata = dict(life=life, query=query, episode=replica)
                    if trigger is None:
                        missing_roots.append(metadata)
                    else:
                        validation_roots.append(dict(metadata, board=steps[trigger]['board'],
                            source_seed=h2_game['seed'], step=trigger))
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
    return dict(methods=methods, wiring=wiring, gate_changes=changes), validation_roots, missing_roots



def validation_record(root, raw, terminal_log, predictions, value_models, work):
    prefixes = {(row['option'], row['replica']): extract_prefix(row) for row in raw}
    complete = (set(prefixes) == {(option, replica) for option in OPTIONS for replica in range(REFERENCE_REPLICAS)}
        and all(prefix['full_target'] is not None for prefix in prefixes.values()))
    value_records, completed = [], {}
    for (option, replica), prefix in prefixes.items():
        predicted = {}
        for method, model in value_models.items():
            remaining = (model.predict(prefix['boundary_board'], root['query'], work)
                         if prefix['status'] == 'ACTIVE' else [0.0, 0.0, 0.0])
            predicted[method] = remaining
            completed[method, option, replica] = (np.asarray(prefix['direct']) + remaining).tolist()
        if prefix['status'] == 'ACTIVE' and prefix['full_target'] is not None:
            value_records.append(dict(replica=replica, option=option, terminal=True,
                predictions=predicted, remaining_target=(np.asarray(prefix['full_target']) - prefix['direct']).tolist()))
    reference, reconstruction = {}, []
    if complete:
        for option in OPTIONS[1:]:
            reference[option] = []
            for replica in range(REFERENCE_REPLICAS):
                target = (np.asarray(prefixes[option, replica]['full_target']) - prefixes['H2', replica]['full_target']).tolist()
                reference[option].append(target)
                reconstruction.append(dict(option=option, replica=replica, Y=target,
                    Z={method: (np.asarray(completed[method, option, replica]) - completed[method, 'H2', replica]).tolist()
                       for method in value_models}))
    return dict(root=root, head_predictions=predictions, terminal_log=terminal_log,
        reference_complete=complete, paired_reference=reference, value_records=value_records,
        active_boundaries=sum(prefix['status'] == 'ACTIVE' for prefix in prefixes.values()),
        reconstruction=reconstruction)


def validate_roots(roots, missing, folder, rule, deployed, models):
    started = perf_counter()
    save(folder / 'validation_cohort.json', dict(roots=roots, missing_roots=missing))
    records, work = [], Counter()
    with gzip.open(folder / 'validation_games.jsonl.gz', 'wt') as output:
        for root in roots:
            predictions = {name: selector.select(root['board'], root['query'], work=work)
                           for name, selector in deployed.items() if selector is not None}
            _, raw, log = sample_root(root, rule, 94000 + root['life'], replicas=REFERENCE_REPLICAS)
            for row in raw:
                write_row(output, dict(root=root, **row))
            records.append(validation_record(root, raw, log, predictions,
                {method: family['full'] for method, family in models.items()}, work))
            print(json.dumps(dict(phase='independent_reference', lifecycle=root['life'],
                query=root['query'], episode=root['episode'], complete=records[-1]['reference_complete'],
                transitions=log['ground_work'].get('sampled_transitions', 0))), flush=True)
    return dict(roots=records, missing_roots=missing, prediction_work=dict(work), seconds=perf_counter() - started)


def lifecycle_run(life, directory, payload):
    started = perf_counter()
    folder = directory / f'life_{life}'
    folder.mkdir()
    rule = LearnedDynamics.from_payload(payload)
    prior = json.loads((SOURCE / f'life_{life}' / 'run.json').read_text())
    roots, rows, frozen, frozen_costs = [], [], {}, {}
    result = dict(id=life, checkpoints=[])
    for checkpoint in CHECKPOINTS:
        stage_dir = folder / f'checkpoint_{checkpoint}'
        stage_dir.mkdir()
        source_dir = SOURCE / f'life_{life}' / f'checkpoint_{checkpoint}'
        old_stage = next(stage for stage in prior['checkpoints'] if stage['episodes'] == checkpoint)
        batch_roots, batch_rows, input_log = load_batch(source_dir)
        roots.extend(batch_roots)
        rows.extend(batch_rows)
        print(json.dumps(dict(phase='fit_started', lifecycle=life, checkpoint=checkpoint,
            roots=len(roots), rows=len(rows))), flush=True)
        models, value_fit = fit_models(rows, checkpoint, iterations=ITERATIONS)
        selectors, labels, head_fit = fit_heads(roots, models, checkpoint)
        for family, values in models.items():
            for name, model in values.items():
                save(stage_dir / f'{family.lower()}_{name}.json', model.to_payload())
        for name, selector in selectors.items():
            save(stage_dir / f'{name.lower()}_selector.json', selector.to_payload())
        with gzip.open(stage_dir / 'estimated_rows.jsonl.gz', 'wt') as output:
            for method, values in labels.items():
                for row in values:
                    write_row(output, dict(method=method, **row))
        baseline_paths, deployed = {}, dict(H2_ONLY=None, **selectors)
        costs = {name: dict(old_stage['method_acquisition']['MC']) for name in VALUE_METHODS}
        costs['H2_ONLY'] = dict(old_stage['method_acquisition']['H2_ONLY'])
        for name, old_name in (('MC', 'MC'), ('MC_EXTRA', 'MC_EXTRA'),
                ('V91_DECOMPOSED', 'V91_DECOMPOSED'), ('V92_CORRECTED', 'CORRECTED')):
            path = source_dir / f'{old_name.lower()}_selector.json'
            old_payload = json.loads(path.read_text())
            deployed[name] = JointSelector.from_payload(old_payload)
            save(stage_dir / f'{name.lower()}_selector.json', old_payload)
            baseline_paths[name] = str(path)
            costs[name] = dict(old_stage['method_acquisition'][old_name])
        if checkpoint == 6:
            for name in VALUE_METHODS:
                frozen[name + '_FROZEN_6'] = JointSelector.from_payload(selectors[name].to_payload())
                frozen_costs[name + '_FROZEN_6'] = dict(costs[name])
        else:
            deployed.update(frozen)
            costs.update(frozen_costs)
            for name, selector in frozen.items():
                save(stage_dir / f'{name.lower()}_selector.json', selector.to_payload())
        eligible = [root for root in roots if not root['censored']]
        stage = dict(episodes=checkpoint,
            dataset=dict(roots=len(eligible), training_roots=sum(root['episode'] % 5 != 4 for root in eligible),
                heldout_roots=sum(root['episode'] % 5 == 4 for root in eligible),
                records=4 * len(eligible), bellman_rows=len(rows)), input=input_log,
            inherited_acquisition=dict(source=old_stage['source']['work'], branches=old_stage['branches']['work']),
            inherited_v93_baselines=dict(paths=baseline_paths,
                original_stage_tree_fits=old_stage['updates']['counts']['tree_fits']
                    + old_stage['updates']['mc_extra']['counts']['tree_fits'],
                scope='Historical V93 fits, including its unused PAIR_ONLY head; not rerun.'),
            updates=dict(value=value_fit, heads=head_fit), method_acquisition=costs,
            new_training_environment_transitions=0)
        save(stage_dir / 'learning.json', stage)
        print(json.dumps(dict(phase='fit_complete', lifecycle=life, checkpoint=checkpoint,
            fits=value_fit['counts']['tree_fits'] + head_fit['counts']['tree_fits'])), flush=True)
        evaluation, validation_roots, missing = evaluate_checkpoint(life, checkpoint, stage_dir, deployed, rule)
        stage.update(evaluation)
        if checkpoint == 12:
            stage['validation'] = validate_roots(validation_roots, missing, stage_dir, rule, deployed, models)
        result['checkpoints'].append(stage)
        result['actual_wall_seconds'] = perf_counter() - started
        save(stage_dir / 'checkpoint.json', stage)
        save(folder / 'run.json', result)
    return result


def snapshot(directory):
    paths = ['scripts/run_controlled_predictive_bellman_v94.py',
        'scripts/analyze_controlled_predictive_bellman_v94.py',
        'scripts/analyze_controlled_predictive_evidence_learning_v88.py',
        'specs/SHARED_BELLMAN_VALUE_V94.md']
    paths += [f'src/acfqp/science/controlled_predictive_{name}_v{version}.py' for name, version in (
        ('bellman_data', 94), ('bellman_value', 94), ('continuation_data', 91),
        ('continuation_value', 91), ('paired_continuation_data', 92),
        ('joint_fragments', 84), ('fragments', 83), ('fragment_experience', 83),
        ('policy_advantage', 81), ('decision_experience', 78), ('lifelong', 77),
        ('lifelong_experience', 77), ('lifelong_planner', 77), ('relational_dynamics', 69),
        ('effect_contract', 74), ('grouped_contract', 73), ('local_contract', 72))]
    paths += ['src/acfqp/domains/standard_2048.py', 'src/acfqp/domains/g2048.py', 'src/acfqp/core.py']
    for relative in paths:
        path = directory / 'source' / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, path)


def run(directory):
    started = perf_counter()
    directory.mkdir(parents=True, exist_ok=False)
    snapshot(directory)
    payload = json.loads((SOURCE / 'supplied_dynamics.json').read_text())
    save(directory / 'supplied_dynamics.json', payload)
    report = dict(schema='acfqp.shared_bellman_value.v94', status='running',
        platform=platform.platform(), executable=sys.executable, python=sys.version,
        inherited_data=str(SOURCE),
        settings=dict(lifecycles=list(LIFECYCLES), checkpoints=list(CHECKPOINTS),
            methods_by_checkpoint=METHODS, queries=QUERIES, evaluation_replicas=REPLICAS,
            reference_replicas=REFERENCE_REPLICAS, validation_roots_per_query=VALIDATION_ROOTS_PER_QUERY,
            fqe_iterations=ITERATIONS, source_episodes_per_query=12, branch_replicas=8,
            n_step=16, stride=16, gamma=1.0, initialization='MC_TAIL',
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
