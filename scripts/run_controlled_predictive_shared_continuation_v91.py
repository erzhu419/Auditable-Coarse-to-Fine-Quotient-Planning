"""Compare full-return and cross-fitted continuation labels on shared history."""
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
    FragmentController, OPTIONS, QUERIES, TRIGGER_EMPTY_CELLS, _utility,
)
from acfqp.science.controlled_predictive_fragment_experience_v83 import sample_root
from acfqp.science.controlled_predictive_joint_fragments_v84 import JointSelector
from acfqp.science.controlled_predictive_continuation_data_v91 import load_batch, extract_prefix
from acfqp.science.controlled_predictive_continuation_value_v91 import fit_decomposed, compose
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics
from acfqp.science import controlled_predictive_lifelong_experience_v77 as experience

SOURCE = ROOT / 'reports/controlled_predictive_fragments_v83'
CHECKPOINTS = (6, 12)
METHODS = {6: ('H2_ONLY', 'MC', 'DECOMPOSED'),
    12: ('H2_ONLY', 'MC', 'DECOMPOSED', 'MC_FROZEN_6', 'DECOMPOSED_FROZEN_6')}
REPLICAS, VALIDATION_REPLICAS = 16, 16


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
    seed = 9190000 + checkpoint * 10000 + life * 100 + replica
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
    contrasts = [('DECOMPOSED', 'MC')]
    if checkpoint == 12:
        contrasts += [('DECOMPOSED', 'DECOMPOSED_FROZEN_6'), ('MC', 'MC_FROZEN_6')]
    changes = {f'{left}_minus_{right}': [] for left, right in contrasts}
    wiring = dict(pretrigger_prefixes_match=True, committed_lengths_match=True,
        single_initiations=True, model_uniforms_aligned=True, same_choice_histories_match=True)
    validation_roots, missing_roots = [], []
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
                if checkpoint == 12 and replica < 2:
                    if trigger is None:
                        missing_roots.append(dict(life=life, query=query, episode=replica))
                    else:
                        validation_roots.append(dict(life=life, query=query, episode=replica,
                            board=steps[trigger]['board'], source_seed=h2_game['seed'], step=trigger))
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


def validate_roots(roots, missing, folder, rule, deployed, tail_model):
    started = perf_counter()
    save(folder / 'validation_cohort.json', dict(roots=roots, missing_roots=missing))
    records, prediction_work = [], Counter()
    with gzip.open(folder / 'validation_games.jsonl.gz', 'wt') as output:
        for root in roots:
            predictions = {name: model.select(root['board'], root['query'], work=prediction_work)
                           for name, model in deployed.items() if model is not None}
            _, raw, log = sample_root(root, rule, 91000 + root['life'], replicas=VALIDATION_REPLICAS)
            for row in raw:
                write_row(output, dict(root=root, **row))
            reconstruction = {}
            if not log['censored_root']:
                prefixes = {(row['replica'], row['option']): extract_prefix(row) for row in raw}
                for option in OPTIONS[1:]:
                    values, residuals = [], []
                    for replica in range(VALIDATION_REPLICAS):
                        candidate = compose(prefixes[replica, option], tail_model, root['query'], prediction_work)
                        reference = compose(prefixes[replica, 'H2'], tail_model, root['query'], prediction_work)
                        delta = [a - b for a, b in zip(candidate, reference)]
                        values.append(delta)
                        residuals.append([a - b for a, b in zip(delta, log['pair_deltas'][option][replica])])
                    reconstruction[option] = dict(paired_targets=values, paired_residuals=residuals)
            records.append(dict(root=root, log=log, predictions=predictions, reconstruction=reconstruction))
            print(json.dumps(dict(phase='reference_root', lifecycle=root['life'], query=root['query'],
                episode=root['episode'], censored=log['censored_root'],
                transitions=log['ground_work']['sampled_transitions'])), flush=True)
    return dict(roots=records, missing_roots=missing, prediction_work=dict(prediction_work),
                seconds=perf_counter() - started)


def lifecycle_run(life, directory, payload, prior):
    started = perf_counter()
    folder = directory / f'life_{life}'
    folder.mkdir()
    rule = LearnedDynamics.from_payload(payload)
    roots, tails, frozen = [], [], {}
    inherited_source, inherited_branch = Counter(), Counter()
    result = dict(id=life, checkpoints=[])
    for checkpoint in CHECKPOINTS:
        stage_dir = folder / f'checkpoint_{checkpoint}'
        stage_dir.mkdir()
        tick = perf_counter()
        batch_roots, batch_tails, batch_log = load_batch(SOURCE / f'life_{life}' / f'checkpoint_{checkpoint}')
        roots.extend(batch_roots)
        tails.extend(batch_tails)
        preparation_seconds = perf_counter() - tick
        mc_rows = [row for root in roots for row in root['mc_rows']]
        mc, mc_fit = JointSelector.fit(mc_rows, checkpoint)
        decomposed, models, labels, decomp_fit = fit_decomposed(roots, tails, checkpoint)
        save(stage_dir / 'mc_selector.json', mc.to_payload())
        save(stage_dir / 'decomposed_selector.json', decomposed.to_payload())
        for name, model in models.items():
            save(stage_dir / f'tail_{name}.json', model.to_payload())
        with gzip.open(stage_dir / 'decomposed_rows.jsonl.gz', 'wt') as output:
            for row in labels:
                write_row(output, row)
        if checkpoint == 6:
            frozen = dict(MC_FROZEN_6=JointSelector.from_payload(mc.to_payload()),
                DECOMPOSED_FROZEN_6=JointSelector.from_payload(decomposed.to_payload()))
        deployed = dict(H2_ONLY=None, MC=mc, DECOMPOSED=decomposed)
        if checkpoint == 12:
            deployed.update(frozen)
        complete_roots = [root for root in roots if not root['censored']]
        stage = dict(episodes=checkpoint, dataset=dict(roots=len(complete_roots),
            training_roots=sum(root['episode'] % 5 != 4 for root in complete_roots),
            heldout_roots=sum(root['episode'] % 5 == 4 for root in complete_roots), records=len(mc_rows)),
            input_preparation_seconds=preparation_seconds, input=batch_log,
            updates=dict(MC=mc_fit, DECOMPOSED=decomp_fit))
        save(stage_dir / 'learning.json', stage)
        evaluation, validation_roots, missing_roots = evaluate_checkpoint(life, checkpoint, stage_dir, deployed, rule)
        stage.update(evaluation)
        if checkpoint == 12:
            stage['validation'] = validate_roots(validation_roots, missing_roots, stage_dir, rule, deployed, models['full'])
        inherited_stage = next(row for row in prior['checkpoints'] if row['episodes'] == checkpoint)
        inherited_source.update(inherited_stage['source']['work'])
        inherited_branch.update(inherited_stage['branches']['work'])
        result['checkpoints'].append(stage)
        result['inherited'] = dict(source_work=dict(inherited_source), branch_work=dict(inherited_branch),
            source_games=sum(row['source']['games'] for row in prior['checkpoints'] if row['episodes'] <= checkpoint),
            branch_trajectories=sum(row['branches']['trajectories'] for row in prior['checkpoints'] if row['episodes'] <= checkpoint))
        result['actual_wall_seconds'] = perf_counter() - started
        save(stage_dir / 'checkpoint.json', stage)
        save(folder / 'run.json', result)
    return result


def snapshot(directory):
    paths = ['scripts/run_controlled_predictive_shared_continuation_v91.py',
        'scripts/analyze_controlled_predictive_shared_continuation_v91.py',
        'scripts/analyze_controlled_predictive_evidence_learning_v88.py',
        'specs/SHARED_CONTINUATION_FRAGMENTS_V91.md']
    paths += [f'src/acfqp/science/controlled_predictive_{name}_v{version}.py' for name, version in (
        ('continuation_data', 91), ('continuation_value', 91), ('joint_fragments', 84), ('fragments', 83),
        ('fragment_experience', 83), ('policy_advantage', 81), ('decision_experience', 78),
        ('lifelong', 77), ('lifelong_experience', 77), ('lifelong_planner', 77), ('relational_dynamics', 69),
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
    payload = json.loads((SOURCE / 'supplied_dynamics.json').read_text())
    save(directory / 'supplied_dynamics.json', payload)
    previous = json.loads((SOURCE / 'run.json').read_text())
    priors = {row['id']: row for row in previous['lifecycles']}
    report = dict(schema='acfqp.shared_continuation.v91', status='running', platform=platform.platform(),
        executable=sys.executable, python=sys.version, source=str(SOURCE),
        settings=dict(lifecycles=[0, 1, 2], checkpoints=list(CHECKPOINTS), methods_by_checkpoint=METHODS,
            queries=QUERIES, evaluation_replicas=REPLICAS, validation_replicas=VALIDATION_REPLICAS,
            validation_roots_per_query=2, workers=3, max_steps=2000, new_training_transitions=0), lifecycles=[])
    save(directory / 'run.json', report)
    with ProcessPoolExecutor(max_workers=3) as pool:
        futures = [pool.submit(lifecycle_run, life, directory, payload, priors[life]) for life in (0, 1, 2)]
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
