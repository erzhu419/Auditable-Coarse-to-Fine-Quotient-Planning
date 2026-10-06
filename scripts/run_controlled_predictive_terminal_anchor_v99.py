"""Test persistent terminal supervision with fresh paired deployment streams."""
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
from acfqp.science.controlled_predictive_terminal_anchor_data_v99 import load_batch
from acfqp.science.controlled_predictive_paired_bellman_value_v96 import PairedBellmanValue
from acfqp.science.controlled_predictive_terminal_anchor_v99 import fit_models, ANCHOR_WEIGHT
from acfqp.science.controlled_predictive_boundary_weighting_v97 import redistribute_weights
from acfqp.science.controlled_predictive_paired_direct_v96 import PairedDirectSelector
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics
from acfqp.science import controlled_predictive_lifelong_experience_v77 as experience

SOURCE = ROOT / 'reports/controlled_predictive_root_coverage_v98'
LIFECYCLES, ALLOCATIONS, BUDGETS = (9, 10), (8, 4), (256000, 512000)
WEIGHTINGS, FAMILIES = ('PAIR', 'BOUNDARY'), ('MC', 'FQE', 'ANCHORED_FQE')
CURRENT_METHODS = tuple(f'R{replicas}_{weight}_{family}_DIRECT'
    for replicas in ALLOCATIONS for weight in WEIGHTINGS for family in FAMILIES)
METHODS = ('H2_ONLY', 'PREFIX_ONLY_DIRECT') + CURRENT_METHODS + tuple(name + '_FROZEN_HALF' for name in CURRENT_METHODS)
REPLICAS, PREFIX_REPLICAS, REFERENCE_REPLICAS, VALIDATION_ROOTS_PER_QUERY, WORKERS = 8, 32, 16, 2, 4
ITERATIONS = 128
CONTRASTS = [(f'R{replicas}_{weight}_ANCHORED_FQE_DIRECT{suffix}', f'R{replicas}_{weight}_{baseline}_DIRECT{suffix}')
    for suffix in ('', '_FROZEN_HALF') for replicas in ALLOCATIONS for weight in WEIGHTINGS for baseline in ('FQE', 'MC')]
CONTRASTS += [(name, name + '_FROZEN_HALF') for name in CURRENT_METHODS]
CONTRASTS += [(f'R{replicas}_{weight}_ANCHORED_FQE_DIRECT{suffix}', 'PREFIX_ONLY_DIRECT')
    for suffix in ('', '_FROZEN_HALF') for replicas in ALLOCATIONS for weight in WEIGHTINGS]


class PrefixOnlyContinuation:
    checkpoint = None

    def predict_pair(self, cboard, rboard, cactive, ractive, query, work=None):
        if work is not None:
            work['prefix_only_zero_predictions'] += 1
        return [0., 0., 0.]


def prefix_seed(life, query, replica):
    return 199000000000 + life * 10000000 + tuple(QUERIES).index(query) * 1000000 + replica * 1000


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
    seed = 9990000 + life * 100 + replica
    if '_DIRECT' in method:
        selector = PairedDirectSelector(selector, rule, prefix_seed(life, query, replica), replicas=PREFIX_REPLICAS)
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
    names = METHODS
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
                    history == prefix_histories['R8_PAIR_FQE_DIRECT'] for history in prefix_histories.values())
                h2_game, h2_raw = group['H2_ONLY']
                steps = h2_raw['episode']['steps']
                trigger = next((i for i, step in enumerate(steps)
                    if step['board'].count(0) <= TRIGGER_EMPTY_CELLS), None)
                if replica < VALIDATION_ROOTS_PER_QUERY:
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
            _, raw, log = sample_root(root, rule, 99000 + root['life'], replicas=REFERENCE_REPLICAS)
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


def construct_allocation(life, replicas, directory, payload):
    started = perf_counter()
    folder = directory / f'life_{life}' / f'replicas_{replicas}'
    folder.mkdir(parents=True, exist_ok=True)
    original = SOURCE / f'life_{life}' / f'replicas_{replicas}'
    prior = json.loads((original / 'run.json').read_text())
    rows, construction, model_metadata = [], [], {}
    new_fits = previous_cursor = 0
    for budget in BUDGETS:
        stage_dir = folder / f'budget_{budget}'
        stage_dir.mkdir()
        prior_stage = next(stage for stage in prior['construction'] if stage['budget'] == budget)
        batch, data = load_batch(original / f'budget_{budget}')
        if data['start_cursor'] != previous_cursor:
            raise ValueError('inherited batches must retain the original incremental roster')
        rows.extend(batch)
        cutoff = prior_stage['episode_cutoff']
        if len(rows) != prior_stage['cumulative_rows'] or data['episode_cutoff'] != cutoff:
            raise ValueError('reconstructed V98 rows do not match the recorded age')
        weighted, weighting = redistribute_weights(rows, cutoff)
        fit_logs = {}
        suffix = '' if budget == BUDGETS[-1] else '_FROZEN_HALF'
        for weight, training_rows in (('PAIR', rows), ('BOUNDARY', weighted)):
            fitted, log = fit_models(training_rows, cutoff, iterations=ITERATIONS)
            fit_logs[weight] = log
            new_fits += log['counts']['tree_fits']
            old_name = f'R{replicas}_{weight}_FQE_DIRECT{suffix}'
            old_path = original / f'budget_{budget}' / f'{old_name.lower()}_model.json'
            old_payload = json.loads(old_path.read_text())
            if (old_payload['checkpoint'] != cutoff or old_payload['family'] != 'PAIR_FQE'
                    or old_payload['training_episodes'] != log['training_episodes']):
                raise ValueError('original FQE must match the same training episodes and model age')
            payloads = {'MC': fitted['PAIR_MC'].to_payload(), 'FQE': old_payload,
                'ANCHORED_FQE': fitted['ANCHORED_FQE'].to_payload()}
            for family, saved in payloads.items():
                method = f'R{replicas}_{weight}_{family}_DIRECT{suffix}'
                metadata = dict(replicas=replicas, budget=budget, episode_cutoff=cutoff,
                    weighting='uniform' if weight == 'PAIR' else 'boundary_0.5',
                    family=saved['family'], source='v98' if family == 'FQE' else 'v99',
                    path=str(stage_dir / f'{method.lower()}_model.json'))
                if family == 'ANCHORED_FQE':
                    saved['anchor_weight'] = ANCHOR_WEIGHT
                # Original FQE payloads are copied unchanged; metadata is separate.
                model_metadata[method] = metadata
                save(Path(metadata['path']), saved)
        record = dict(budget=budget, episode_cutoff=cutoff, data=data, weighting=weighting,
            fit_logs=fit_logs, cumulative_roots=prior_stage['cumulative_roots'],
            cumulative_rows=len(rows), inherited_acquisition=prior_stage['acquisition'])
        construction.append(record)
        save(stage_dir / 'construction.json', record)
        previous_cursor = data['next_cursor']
        print(json.dumps(dict(phase='terminal_anchor_fit', lifecycle=life, replicas=replicas,
            budget=budget, episode_cutoff=cutoff, rows=len(rows), anchor_weight=ANCHOR_WEIGHT,
            tree_fits=sum(log['counts']['tree_fits'] for log in fit_logs.values()))), flush=True)
    result = dict(replicas=replicas, construction=construction, model_metadata=model_metadata,
        new_tree_fits=new_fits, new_training_environment_transitions=0,
        inherited_training_environment_transitions=prior['new_training_environment_transitions'],
        historical_v98_tree_fits=prior['new_tree_fits'], actual_wall_seconds=perf_counter() - started)
    save(folder / 'run.json', result)
    return result


def lifecycle_evaluation(life, directory, payload, allocations):
    started = perf_counter()
    folder = directory / f'life_{life}' / 'evaluation'
    folder.mkdir()
    rule = LearnedDynamics.from_payload(payload)
    metadata = {name: row for allocation in allocations for name, row in allocation['model_metadata'].items()}
    deployed = {'H2_ONLY': None, 'PREFIX_ONLY_DIRECT': PrefixOnlyContinuation()}
    for name in METHODS[2:]:
        saved = json.loads(Path(metadata[name]['path']).read_text())
        model = PairedBellmanValue.from_payload(saved)
        if (model.checkpoint != metadata[name]['episode_cutoff'] or model.family != metadata[name]['family']
                or ('ANCHORED_FQE' in name and saved['anchor_weight'] != ANCHOR_WEIGHT)):
            raise ValueError('deployed model must match its family, anchor and episode cutoff')
        deployed[name] = model
    save(folder / 'deployment.json', dict(model_metadata=metadata, prefix_only_continuation=0))
    evaluation, roots, missing = evaluate_checkpoint(life, BUDGETS[-1], folder, deployed, rule)
    evaluation['model_metadata'] = metadata
    evaluation['validation'] = validate_roots(roots, missing, folder, rule)
    result = dict(id=life, allocations=allocations, evaluation=evaluation,
        evaluation_wall_seconds=perf_counter() - started)
    save(directory / f'life_{life}' / 'run.json', result)
    return result


def snapshot(directory):
    paths = ['scripts/run_controlled_predictive_terminal_anchor_v99.py',
        'scripts/analyze_controlled_predictive_terminal_anchor_v99.py',
        'scripts/analyze_controlled_predictive_bellman_v94.py',
        'scripts/analyze_controlled_predictive_evidence_learning_v88.py',
        'specs/TERMINAL_ANCHOR_V99.md']
    paths += [f'src/acfqp/science/controlled_predictive_{name}_v{version}.py' for name, version in (
        ('terminal_anchor', 99), ('terminal_anchor_data', 99), ('boundary_weighting', 97),
        ('paired_bellman_data', 96), ('paired_bellman_value', 96), ('paired_direct', 96),
        ('paired_continuation_data', 92), ('paired_continuation_value', 92), ('direct_value', 95),
        ('bellman_value', 94), ('continuation_data', 91), ('continuation_value', 91),
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
    report = dict(schema='acfqp.terminal_anchor.v99', status='running',
        platform=platform.platform(), executable=sys.executable, python=sys.version,
        inherited_data=str(SOURCE),
        settings=dict(lifecycles=list(LIFECYCLES), allocations=list(ALLOCATIONS), budgets=list(BUDGETS),
            methods=list(METHODS), contrasts=CONTRASTS, queries=QUERIES,
            evaluation_replicas=REPLICAS, prefix_replicas=PREFIX_REPLICAS,
            reference_replicas=REFERENCE_REPLICAS, validation_roots_per_query=VALIDATION_ROOTS_PER_QUERY,
            horizon=4, n_step=16, iterations=ITERATIONS, anchor_weight=ANCHOR_WEIGHT, boundary_fraction=0.5,
            natural_seed_base=9990000, synthetic_seed_base=199000000000, reference_life_base=99000,
            max_steps=2000, workers=WORKERS), allocations=[], lifecycles=[])
    save(directory / 'run.json', report)
    with ProcessPoolExecutor(max_workers=WORKERS) as pool:
        tasks = {pool.submit(construct_allocation, life, replicas, directory, payload): (life, replicas)
            for life in LIFECYCLES for replicas in ALLOCATIONS}
        collected = {life: [] for life in LIFECYCLES}
        for future in as_completed(tasks):
            life, replicas = tasks[future]
            allocation = future.result()
            collected[life].append(allocation)
            report['allocations'].append(dict(life=life, **allocation))
            save(directory / 'run.json', report)
        evaluations = [pool.submit(lifecycle_evaluation, life, directory, payload,
            sorted(collected[life], key=lambda row: -row['replicas'])) for life in LIFECYCLES]
        for future in as_completed(evaluations):
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

