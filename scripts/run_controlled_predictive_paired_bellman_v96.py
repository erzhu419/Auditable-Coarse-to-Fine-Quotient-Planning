"""Learn paired Bellman advantages and evaluate at the fixed V95 interface."""
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
from acfqp.science.controlled_predictive_fragments_v83 import (
    FragmentController, OPTIONS, QUERIES, TRIGGER_EMPTY_CELLS, _utility,
)
from acfqp.science.controlled_predictive_fragment_experience_v83 import sample_root
from acfqp.science.controlled_predictive_bellman_value_v94 import BellmanValue
from acfqp.science.controlled_predictive_direct_value_v95 import DirectSelector
from acfqp.science.controlled_predictive_paired_bellman_data_v96 import load_batch
from acfqp.science.controlled_predictive_paired_bellman_value_v96 import fit_models
from acfqp.science.controlled_predictive_paired_direct_v96 import PairedDirectSelector
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics
from acfqp.science import controlled_predictive_lifelong_experience_v77 as experience

SOURCE = ROOT / 'reports/controlled_predictive_bellman_v94'
BRANCH_SOURCE = ROOT / 'reports/controlled_predictive_replication_v93'
LIFECYCLES, CHECKPOINTS = tuple(range(3, 9)), (12,)
VALUE_METHODS = ('MC_TAIL', 'FQE', 'PAIR_MC', 'PAIR_FQE')
METHODS = {12: ('H2_ONLY',) + tuple(name + '_DIRECT' + suffix
    for suffix in ('', '_FROZEN_6') for name in VALUE_METHODS)}
REPLICAS, PREFIX_REPLICAS, REFERENCE_REPLICAS, VALIDATION_ROOTS_PER_QUERY, WORKERS = 16, 32, 16, 2, 6
ITERATIONS = 128
CONTRASTS = [('PAIR_FQE_DIRECT' + suffix, 'PAIR_MC_DIRECT' + suffix) for suffix in ('', '_FROZEN_6')]
CONTRASTS += [(pair + '_DIRECT' + suffix, unary + '_DIRECT' + suffix)
    for suffix in ('', '_FROZEN_6') for pair, unary in (('PAIR_MC', 'MC_TAIL'), ('PAIR_FQE', 'FQE'))]
CONTRASTS += [(name + '_DIRECT', name + '_DIRECT_FROZEN_6') for name in VALUE_METHODS]
CONTRASTS += [(name + '_DIRECT', 'H2_ONLY') for name in ('PAIR_MC', 'PAIR_FQE')]


def prefix_seed(life, query, replica):
    return 196000000000 + life * 10000000 + tuple(QUERIES).index(query) * 1000000 + replica * 1000


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
    seed = 9690000 + checkpoint * 10000 + life * 100 + replica
    if '_DIRECT' in method:
        selector_type = PairedDirectSelector if method.startswith('PAIR_') else DirectSelector
        selector = selector_type(selector, rule, prefix_seed(life, query, replica), replicas=PREFIX_REPLICAS)
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
    row['candidate_evaluation'] = selector.last_log if '_DIRECT' in method else None
    return row, dict(method=method, query=query, episode=game,
        controller_events=controller.events, action_paths=paths,
        model_prefixes=selector.last_prefixes if '_DIRECT' in method else [])


def evaluate_checkpoint(life, checkpoint, folder, deployed, rule, replicas=REPLICAS, max_steps=2000):
    names = METHODS[checkpoint]
    methods = {name: dict(games=[], costs=dict(evaluation_seconds=0.0)) for name in names}
    contrasts = CONTRASTS
    validation_roots, missing_roots = [], []
    changes = {f'{left}_minus_{right}': [] for left, right in contrasts}
    wiring = dict(pretrigger_prefixes_match=True, committed_lengths_match=True,
        single_initiations=True, model_uniforms_aligned=True, same_choice_histories_match=True,
        simulated_prefixes_paired=True, simulated_work_matches=True)
    with gzip.open(folder / 'evaluation_games.jsonl.gz', 'wt') as output, \
            gzip.open(folder / 'model_prefixes.jsonl.gz', 'wt') as simulated:
        for replica in range(replicas):
            for qi, query in enumerate(QUERIES):
                offset = (life + checkpoint + replica + qi) % len(names)
                group, histories, prefix_histories = {}, {}, {}
                for method in names[offset:] + names[:offset]:
                    tick = perf_counter()
                    game, raw = evaluate_game(method, deployed[method], rule, life, checkpoint,
                        replica, query, max_steps=max_steps)
                    prefix_rows = raw.pop('model_prefixes')
                    if '_DIRECT' in method:
                        prefix_histories[method] = [(prefix['option'], prefix['replica'], prefix['spawn_seed'],
                            prefix['planning_seed'], prefix['steps'], prefix['status']) for prefix in prefix_rows]
                        log = game['candidate_evaluation']
                        if log is not None:
                            wiring['simulated_work_matches'] &= all(log['wiring'].values())
                    for prefix in prefix_rows:
                        write_row(simulated, dict(method=method, query=query, episode=replica, **prefix))
                    write_row(output, raw)
                    methods[method]['costs']['evaluation_seconds'] += perf_counter() - tick
                    methods[method]['games'].append(game)
                    group[method] = game, raw
                    histories[method] = [(s['board'], s['action'], s['next_board']) for s in raw['episode']['steps']]
                    wiring['committed_lengths_match'] &= game['committed_length_matches']
                    wiring['single_initiations'] &= game['controller_events'] <= 1
                    wiring['model_uniforms_aligned'] &= game['planning_counts']['model_uniform_draws'] == 4 * game['steps']
                wiring['simulated_prefixes_paired'] &= all(
                    history == prefix_histories['MC_TAIL_DIRECT'] for history in prefix_histories.values())
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
                            source_seed=h2_game['seed'], step=trigger,
                            predictions={name: group[name][1]['controller_events'][0] for name in names[1:]}))
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


def validate_roots(roots, missing, folder, rule):
    started = perf_counter()
    save(folder / 'validation_cohort.json', dict(roots=roots, missing_roots=missing))
    records = []
    with gzip.open(folder / 'validation_games.jsonl.gz', 'wt') as output:
        for retained in roots:
            root = {key: value for key, value in retained.items() if key != 'predictions'}
            # Selection is the actual natural-game event, fixed before these independent outcomes.
            _, raw, log = sample_root(root, rule, 96000 + root['life'], replicas=REFERENCE_REPLICAS)
            for row in raw:
                write_row(output, dict(root=root, **row))
            complete = (not log['censored_root'] and len(raw) == REFERENCE_REPLICAS * len(OPTIONS)
                and all(row['game']['status'] in ('WON', 'LOST') for row in raw))
            records.append(dict(root=root, predictions=retained['predictions'], terminal_log=log,
                reference_complete=complete, paired_reference=log['pair_deltas']))
            print(json.dumps(dict(phase='independent_reference', lifecycle=root['life'],
                query=root['query'], episode=root['episode'], complete=complete,
                transitions=log['ground_work'].get('sampled_transitions', 0))), flush=True)
    return dict(roots=records, missing_roots=missing, seconds=perf_counter() - started,
                new_selector_calls=0, new_model_transitions=0)


def construct_models(life, folder, rule):
    prior = json.loads((SOURCE / f'life_{life}' / 'run.json').read_text())
    deployed, inherited = {'H2_ONLY': None}, {}
    historical_fits, new_fits, rows, construction = 0, 0, [], []
    history = {name: Counter() for name in ('source', 'branches')}
    previous = 0
    for checkpoint in (6, 12):
        stage_dir = folder / f'checkpoint_{checkpoint}'
        stage_dir.mkdir()
        old = next(stage for stage in prior['checkpoints'] if stage['episodes'] == checkpoint)
        historical_fits += old['updates']['value']['counts']['tree_fits'] + old['updates']['heads']['counts']['tree_fits']
        for name in history:
            history[name].update(old['inherited_acquisition'][name])
        source_dir = BRANCH_SOURCE / f'life_{life}' / f'checkpoint_{checkpoint}'
        roots, batch_rows, data = load_batch(source_dir)
        if any(not previous <= root['episode'] < checkpoint for root in roots):
            raise ValueError('source batch is not the expected incremental episode interval')
        rows.extend(batch_rows)
        models, fit_log = fit_models(rows, checkpoint, iterations=ITERATIONS)
        new_fits += fit_log['counts']['tree_fits']
        record = dict(checkpoint=checkpoint, data=data, fit_log=fit_log)
        construction.append(record)
        save(stage_dir / 'construction.json', record)
        suffix = '' if checkpoint == 12 else '_FROZEN_6'
        for family in VALUE_METHODS:
            name = family + '_DIRECT' + suffix
            if family.startswith('PAIR_'):
                model = models[family]
                if model.checkpoint != checkpoint or model.family != family:
                    raise ValueError('pair model checkpoint or family mismatch')
                payload = model.to_payload()
            else:
                path = SOURCE / f'life_{life}' / f'checkpoint_{checkpoint}' / f'{family.lower()}_full.json'
                payload = json.loads(path.read_text())
                model = BellmanValue.from_payload(payload)
                if model.checkpoint != checkpoint or model.excluded_fold is not None or model.training_method != family:
                    raise ValueError('unary baseline requires its frozen full model')
                inherited[name] = dict(checkpoint=checkpoint, paths={'value': str(path)},
                    training_acquisition=old['method_acquisition'][family])
            deployed[name] = model
            save(stage_dir / f'{name.lower()}_model.json', payload)
        previous = checkpoint
        print(json.dumps(dict(phase='paired_value_fit', lifecycle=life, checkpoint=checkpoint,
            rows=len(rows), tree_fits=fit_log['counts']['tree_fits'])), flush=True)
    return deployed, dict(construction=construction, new_tree_fits=new_fits,
        new_training_environment_transitions=0, inherited_models=inherited,
        inherited_training={name: dict(counts) for name, counts in history.items()},
        historical_v94_tree_fits=historical_fits)


def lifecycle_run(life, directory, payload):
    started = perf_counter()
    folder = directory / f'life_{life}'
    folder.mkdir()
    rule = LearnedDynamics.from_payload(payload)
    deployed, constructed = construct_models(life, folder, rule)
    stage_dir = folder / 'checkpoint_12'
    stage = dict(episodes=12, **constructed)
    save(stage_dir / 'deployment.json', stage)
    evaluation, roots, missing = evaluate_checkpoint(life, 12, stage_dir, deployed, rule)
    stage.update(evaluation)
    stage['validation'] = validate_roots(roots, missing, stage_dir, rule)
    result = dict(id=life, checkpoints=[stage], actual_wall_seconds=perf_counter() - started)
    save(stage_dir / 'checkpoint.json', stage)
    save(folder / 'run.json', result)
    return result


def snapshot(directory):
    paths = ['scripts/run_controlled_predictive_paired_bellman_v96.py',
        'scripts/analyze_controlled_predictive_paired_bellman_v96.py',
        'scripts/analyze_controlled_predictive_direct_value_v95.py',
        'scripts/analyze_controlled_predictive_bellman_v94.py',
        'scripts/analyze_controlled_predictive_evidence_learning_v88.py',
        'specs/PAIRED_BELLMAN_ADVANTAGE_V96.md']
    paths += [f'src/acfqp/science/controlled_predictive_{name}_v{version}.py' for name, version in (
        ('paired_bellman_data', 96), ('paired_bellman_value', 96), ('paired_direct', 96),
        ('paired_continuation_data', 92), ('paired_continuation_value', 92), ('direct_value', 95), ('bellman_value', 94), ('continuation_data', 91),
        ('continuation_value', 91), ('joint_fragments', 84), ('fragments', 83), ('fragment_experience', 83),
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
    report = dict(schema='acfqp.paired_bellman_advantage.v96', status='running',
        platform=platform.platform(), executable=sys.executable, python=sys.version,
        inherited_data=str(BRANCH_SOURCE), inherited_unary_models=str(SOURCE),
        settings=dict(lifecycles=list(LIFECYCLES), checkpoints=list(CHECKPOINTS),
            methods_by_checkpoint=METHODS, contrasts=CONTRASTS, queries=QUERIES,
            evaluation_replicas=REPLICAS, prefix_replicas=PREFIX_REPLICAS,
            reference_replicas=REFERENCE_REPLICAS, validation_roots_per_query=VALIDATION_ROOTS_PER_QUERY,
            horizon=4, n_step=16, iterations=ITERATIONS, model_checkpoints=[6, 12],
            natural_seed_base=9690000, synthetic_seed_base=196000000000, reference_life_base=96000,
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
