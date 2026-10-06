"""Independent fresh-history replication of the fixed R4 uniform-shrink recipe."""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import gzip
import importlib
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
from acfqp.science.controlled_predictive_fragments_v83 import FragmentController, OPTIONS, QUERIES, TRIGGER_EMPTY_CELLS, _utility
from acfqp.science.controlled_predictive_fragment_experience_v83 import sample_root
from acfqp.science.controlled_predictive_candidate_data_v100 import CandidateSelector as PrefixSelector
from acfqp.science.controlled_predictive_root_coverage_v98 import acquire_batch
from acfqp.science.controlled_predictive_fresh_data_v105 import load_batch
from acfqp.science.controlled_predictive_fresh_ranking_v105 import fit_model, CandidateModel, STEPS
from acfqp.science.controlled_predictive_reference_suffix_v104 import audit_reference
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics
from acfqp.science import controlled_predictive_lifelong_experience_v77 as experience

SOURCE = ROOT / 'reports/controlled_predictive_root_coverage_v98'
LIFECYCLES, BUDGETS, WIDTHS = (11, 12, 13, 14), (256000, 512000), (4, 16)
CURRENT = tuple(f'R4_H{hidden}_UNIFORM_SHRINK_DIRECT' for hidden in WIDTHS)
METHODS = ('H2_ONLY', 'PREFIX_ONLY_DIRECT') + CURRENT + tuple(name + '_FROZEN_HALF' for name in CURRENT)
CONTRASTS = [(CURRENT[0] + suffix, CURRENT[1] + suffix) for suffix in ('', '_FROZEN_HALF')]
CONTRASTS += [(name, name + '_FROZEN_HALF') for name in CURRENT]
CONTRASTS += [(name, 'H2_ONLY') for name in CURRENT]
REPLICAS, PREFIX_REPLICAS, REFERENCE_REPLICAS, VALIDATION_ROOTS_PER_QUERY, WORKERS = 8, 32, 32, 8, 4
REFERENCE_LIFE_BASE = 105000


def prefix_seed(life, query, replica):
    return 251000000000 + life * 10000000 + tuple(QUERIES).index(query) * 1000000 + replica * 1000


class CandidateSelector(PrefixSelector):
    def select(self, board, query, allowed=None, work=None):
        result = super().select(board, query, allowed, work)
        if self.model is not None:
            result['score_semantics'] = 'rank_score'
        return result


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
    seed = 10590000 + life * 100 + replica
    if '_DIRECT' in method:
        selector = CandidateSelector(selector, rule, prefix_seed(life, query, replica), replicas=PREFIX_REPLICAS)
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
                    history == prefix_histories['PREFIX_ONLY_DIRECT'] for history in prefix_histories.values())
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


def construct_history(life, directory, payload):
    started = perf_counter()
    folder = directory / f'life_{life}' / 'replicas_4'
    folder.mkdir(parents=True, exist_ok=False)
    rule = LearnedDynamics.from_payload(payload)
    records, construction, metadata = [], [], {}
    cursor = previous = 0
    for budget in BUDGETS:
        stage_dir = folder / f'budget_{budget}'
        stage_dir.mkdir()
        # The inherited acquisition routine also constructs Bellman rows. They
        # are unused here; all their execution time remains in acquisition cost.
        unused_rows, cursor, acquisition = acquire_batch(life, 4, rule, budget - previous, cursor, stage_dir)
        del unused_rows
        save(stage_dir / 'acquisition.json', acquisition)
        batch, data = load_batch(acquisition, stage_dir, rule, life)
        records.extend(batch)
        cutoff = acquisition['episode_cutoff']
        logs = {}
        suffix = '' if budget == BUDGETS[-1] else '_FROZEN_HALF'
        for hidden in WIDTHS:
            model, logs[str(hidden)] = fit_model(records, cutoff, hidden)
            name = f'R4_H{hidden}_UNIFORM_SHRINK_DIRECT{suffix}'
            path = stage_dir / f'{name.lower()}_model.json'
            save(path, model.to_payload())
            metadata[name] = dict(replicas=4, budget=budget, episode_cutoff=cutoff,
                family='UNIFORM_SHRINK', hidden=hidden, parameter_count=hidden * 123, path=str(path))
        coverage = {q: {role: sorted(r['episode'] for r in records if r['query'] == q
            and (r['episode'] % 5 == 4) == (role == 'heldout')) for role in ('training', 'heldout')} for q in QUERIES}
        stage = dict(budget=budget, episode_cutoff=cutoff, acquisition=acquisition, data=data,
            fit_logs=logs, cumulative_roots=coverage, cumulative_root_count=len(records))
        construction.append(stage)
        save(stage_dir / 'construction.json', stage)
        print(json.dumps(dict(phase='fresh_fit', lifecycle=life, budget=budget, roots=len(records),
            transitions=acquisition['used_transitions'], fits=2,
            losses={h: log['models']['UNIFORM_SHRINK']['final_loss'] for h, log in logs.items()})), flush=True)
        previous = budget
    result = dict(replicas=4, construction=construction, model_metadata=metadata,
        new_neural_model_fits=sum(log['counts']['neural_model_fits'] for stage in construction for log in stage['fit_logs'].values()),
        new_training_environment_transitions=sum(stage['acquisition']['used_transitions'] for stage in construction),
        inherited_training_environment_transitions=0, actual_wall_seconds=perf_counter() - started)
    save(folder / 'run.json', result)
    return result


def evaluate_history(life, directory, payload, allocation):
    folder = directory / f'life_{life}' / 'evaluation'
    folder.mkdir()
    rule = LearnedDynamics.from_payload(payload)
    deployed = {'H2_ONLY': None, 'PREFIX_ONLY_DIRECT': None}
    metadata = allocation['model_metadata']
    for name in METHODS[2:]:
        row = metadata[name]
        model = CandidateModel.from_payload(json.loads(Path(row['path']).read_text()))
        if (model.checkpoint != row['episode_cutoff'] or model.family != row['family']
                or model.to_payload()['hidden'] != row['hidden']):
            raise ValueError('deployed scorer differs from its frozen family, width or age')
        deployed[name] = model
    save(folder / 'deployment.json', dict(model_metadata=metadata))
    evaluation, roots, missing = evaluate_checkpoint(life, BUDGETS[-1], folder, deployed, rule)
    evaluation['model_metadata'] = metadata
    save(folder / 'validation_cohort.json', dict(roots=roots, missing_roots=missing))
    evaluation['validation'] = dict(roots=[], missing_roots=missing, new_selector_calls=0, new_model_transitions=0, seconds=0.)
    result = dict(id=life, allocations=[allocation], evaluation=evaluation)
    save(directory / f'life_{life}' / 'run.json', result)
    return result, roots


def reference_job(retained, directory, payload):
    started = perf_counter()
    root = {key: value for key, value in retained.items() if key != 'predictions'}
    folder = directory / f"life_{root['life']}" / 'evaluation' / 'references' / f"{root['query']}_{root['episode']}"
    folder.mkdir(parents=True, exist_ok=False)
    rule = LearnedDynamics.from_payload(payload)
    _, raw, log = sample_root(root, rule, REFERENCE_LIFE_BASE + root['life'], replicas=REFERENCE_REPLICAS)
    checks = audit_reference(root, raw, log, replicas=REFERENCE_REPLICAS, life_base=REFERENCE_LIFE_BASE)
    with gzip.open(folder / 'games.jsonl.gz', 'wt') as handle:
        for row in raw:
            write_row(handle, dict(root=root, block='A' if row['replica'] < 16 else 'B', **row))
    complete = not log['censored_root'] and all(checks.values())
    record = dict(root=root, predictions=retained['predictions'], terminal_log=log,
        reference_complete=complete, paired_reference=log['pair_deltas'], audit=checks,
        seconds=perf_counter() - started)
    save(folder / 'reference.json', record)
    if not all(checks.values()):
        raise ValueError(f'reference execution differs from retained costs or frozen semantics: {checks}')
    return record


def snapshot(directory):
    # Include the actual imported research dependencies, plus the fixed protocol.
    importlib.import_module('scripts.analyze_controlled_predictive_fresh_ranking_v105')
    paths = {Path(__file__).resolve(), ROOT / 'specs/FRESH_RANKING_V105.md'}
    for module in list(sys.modules.values()):
        filename = getattr(module, '__file__', None)
        if filename:
            path = Path(filename).resolve()
            if path.is_relative_to(ROOT / 'src') or path.is_relative_to(ROOT / 'scripts'):
                paths.add(path)
    for source in paths:
        target = directory / 'source' / source.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)


def run(directory):
    started = perf_counter()
    directory.mkdir(parents=True, exist_ok=False)
    snapshot(directory)
    payload = json.loads((SOURCE / 'supplied_dynamics.json').read_text())
    save(directory / 'supplied_dynamics.json', payload)
    report = dict(schema='acfqp.fresh_ranking.v105', status='running', platform=platform.platform(),
        executable=sys.executable, python=sys.version, fixed_dynamics_source=str(SOURCE / 'supplied_dynamics.json'),
        settings=dict(lifecycles=list(LIFECYCLES), allocations=[4], budgets=list(BUDGETS),
            methods=list(METHODS), contrasts=CONTRASTS, queries=QUERIES, evaluation_replicas=REPLICAS,
            prefix_replicas=PREFIX_REPLICAS, reference_replicas=REFERENCE_REPLICAS,
            validation_roots_per_query=VALIDATION_ROOTS_PER_QUERY, horizon=4, optimizer_steps=STEPS,
            feature_dim=121, widths=list(WIDTHS), learning_rate=.01, l2_coefficient=.001/1968, l2_reference_parameters=1968,
            initialization_seed=10001, training_model_prefixes_reused=False, reference_block_size=16,
            natural_seed_base=10590000, training_prefix_seed_base=250000000000,
            synthetic_seed_base=251000000000, reference_life_base=REFERENCE_LIFE_BASE, max_steps=2000, workers=WORKERS),
        allocations=[], lifecycles=[])
    save(directory / 'run.json', report)
    with ProcessPoolExecutor(max_workers=WORKERS) as pool:
        tasks = {pool.submit(construct_history, life, directory, payload): life for life in LIFECYCLES}
        allocations = {}
        for future in as_completed(tasks):
            life = tasks[future]
            allocations[life] = future.result()
            report['allocations'].append(dict(life=life, **allocations[life]))
            save(directory / 'run.json', report)
        tasks = [pool.submit(evaluate_history, life, directory, payload, allocations[life]) for life in LIFECYCLES]
        cohorts = []
        for future in as_completed(tasks):
            lifecycle, roots = future.result()
            report['lifecycles'].append(lifecycle)
            report['lifecycles'].sort(key=lambda row: row['id'])
            cohorts.extend(roots)
            save(directory / 'run.json', report)
        # Every actual natural decision is saved before any independent outcome.
        save(directory / 'validation_cohort.json', dict(roots=cohorts,
            missing_roots=[root for life in report['lifecycles'] for root in life['evaluation']['validation']['missing_roots']]))
        indexed = {life['id']: life for life in report['lifecycles']}
        tasks = [pool.submit(reference_job, root, directory, payload) for root in cohorts]
        completed = 0
        for future in as_completed(tasks):
            record = future.result()
            life = indexed[record['root']['life']]
            life['evaluation']['validation']['roots'].append(record)
            life['evaluation']['validation']['seconds'] += record['seconds']
            life['evaluation']['validation']['roots'].sort(key=lambda row: (row['root']['query'], row['root']['episode']))
            completed += 1
            save(directory / f"life_{life['id']}" / 'run.json', life)
            report['actual_wall_seconds'] = perf_counter() - started
            save(directory / 'run.json', report)
            print(json.dumps(dict(phase='independent_reference', lifecycle=life['id'],
                query=record['root']['query'], episode=record['root']['episode'], completed=completed,
                expected=len(cohorts), complete=record['reference_complete'],
                transitions=record['terminal_log']['ground_work']['sampled_transitions'])), flush=True)
    report.update(status='complete', actual_wall_seconds=perf_counter() - started)
    save(directory / 'run.json', report)
    print(json.dumps(dict(phase='complete', seconds=report['actual_wall_seconds'])), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    run(parser.parse_args().output)
