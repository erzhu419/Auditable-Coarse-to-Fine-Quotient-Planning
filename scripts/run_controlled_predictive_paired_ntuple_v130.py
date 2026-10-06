"""One frozen policy improvement from paired terminal action-gap targets."""
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
import gzip
import importlib
import json
from pathlib import Path
import platform
import shutil
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / 'src'))
from scripts.run_controlled_predictive_policy_consequences_v126 import (
    POLICIES, QUERIES as ALL_QUERIES, save, append, compact_trace, counter_delta, result)
from scripts.run_controlled_predictive_forced_actions_v128 import load_source
from acfqp.science.controlled_predictive_regime_experience_v115 import run_episode
from acfqp.science.controlled_predictive_forced_actions_v128 import run_forced_continuation
from acfqp.science.controlled_predictive_paired_ntuple_v130 import QueryParent, PairResidual

SOURCE = ROOT / 'reports/controlled_predictive_policy_calibration_v129'
QUERIES = {q: ALL_QUERIES[q] for q in ('risk1', 'risk8')}
PARENTS = dict(risk1='reward', risk8='risk_goal')
LIVES, EPISODES, TRAIN_EPISODES, SUFFIX_REPLICAS, REPLICAS = (0, 1, 2, 3), 16, 12, 8, 16
ROOT_INDICES, MAX_STEPS, WORKERS, BASE = (128, 256, 512, 768), 2000, 4, 130 * 100000000
KINDS, METHODS, EPOCHS, RATE = ('PRIOR', 'SCRATCH'), ('PARENT', 'PRIOR', 'SCRATCH'), 20, .1


def settings():
    return dict(lifecycles=list(LIVES), policies=POLICIES, queries=QUERIES, parents=PARENTS,
        episodes=EPISODES, train_episodes=TRAIN_EPISODES, suffix_replicas=SUFFIX_REPLICAS,
        replicas=REPLICAS, root_indices=list(ROOT_INDICES), methods=list(METHODS),
        kinds=list(KINDS), epochs=EPOCHS, rate=RATE, max_steps=MAX_STEPS,
        workers=WORKERS, p_four=.1, version_base=BASE)


def source_seed(life, episode):
    return BASE + 10000000 + life * 100000 + episode


def suffix_seed(root_id, replica):
    return BASE + 50000000 + root_id * 1000 + replica


def evaluation_seed(life, replica):
    return BASE + 90000000 + life * 100000 + replica


def slot_id(life, query, episode, index):
    return life * 128 + list(QUERIES).index(query) * 64 + episode * 4 + ROOT_INDICES.index(index)


def extract_source(previous, analysis):
    if not analysis['complete']: raise ValueError('V129 diagnosis must be complete')
    return dict(schema='acfqp.paired_ntuple.v130.source',
        snapshots=[{k: deepcopy(row[k]) for k in ('life', 'rule', 'models', 'counts')}
                   for row in previous['snapshots']],
        inherited_costs=dict(**deepcopy(previous['inherited_costs']), v129_diagnosis=deepcopy(analysis['costs'])))


def load_parent(source, query, folder):
    policy = PARENTS[query]; actor = load_source(source, policy, folder / 'build')
    parent = QueryParent(actor, POLICIES[policy], QUERIES[query], source['counts'][policy]['constant'])
    costs = dict(source_policy=policy, source_updates=actor.updates,
        load_counts={k: v for k, v in actor.counts.items() if k.startswith('checkpoint_load')},
        load_seconds=actor.last_load_seconds, setup_counts=dict(actor.setup_counts), setup_seconds=actor.setup_seconds)
    return parent, costs


def state(model):
    source = model.source if isinstance(model, QueryParent) else model.parent.source
    return dict(updates=model.updates, source_updates=source.updates,
        source_readonly=not source.weights.flags.writeable,
        residual_readonly=None if isinstance(model, QueryParent) else not model.weights.flags.writeable)


def prediction(choice):
    fields = ('afterstate', 'score', 'value', 'base_value', 'residual', 'anchor_value', 'success_probability')
    return dict(action=choice['action'], action_values={a: {k: deepcopy(row[k]) for k in fields if k in row}
                for a, row in choice['action_values'].items()})


def full_game(model, life, query, method, replica, acquisition=False):
    previous, before = dict(model.counts), state(model)
    values, bases, residuals = [], [], []
    def act(board, step):
        choice = model.choose(board, QUERIES[query]); values.append(choice['value'])
        bases.append(choice.get('base_value', choice['value'])); residuals.append(choice.get('residual', 0.))
        return choice['action']
    seed = source_seed(life, replica) if acquisition else evaluation_seed(life, replica)
    game = run_episode(seed, act, .1, MAX_STEPS)
    row = dict(life=life, query=query, method=method, replica=replica,
        episode=replica if acquisition else None, seed=seed,
        result=result(game, query, policy_counts=counter_delta(model.counts, previous)),
        **compact_trace(game), chosen_values=values, base_values=bases, residual_values=residuals)
    row['result'].update(model_state_before=before, model_state_after=state(model))
    return row, game


def prepare_lifecycle(source, directory):
    started = perf_counter(); life = source['life']; folder = directory / f'acquisition_{life}'; folder.mkdir()
    trace = str((folder / 'games.jsonl.gz').relative_to(directory)); cases, loads, work = [], {}, Counter()
    with gzip.open(directory / trace, 'wt') as stream:
        for query in QUERIES:
            parent, loads[query] = load_parent(source, query, folder)
            for episode in range(EPISODES):
                row, game = full_game(parent, life, query, 'ACQUISITION', episode, acquisition=True); append(stream, row)
                for index in ROOT_INDICES:
                    available = index < game['steps_count']
                    case = dict(root_id=slot_id(life, query, episode, index), life=life, query=query,
                        episode=episode, index=index, split='TRAIN' if episode < TRAIN_EPISODES else 'HOLDOUT',
                        available=available, board=None, parent=None, actions=[])
                    if available:
                        case['board'] = game['steps'][index]['board']
                        before = dict(parent.counts); case['parent'] = prediction(parent.choose(case['board']))
                        work.update(counter_delta(parent.counts, before)); case['actions'] = sorted(case['parent']['action_values'])
                    cases.append(case)
                stream.flush()
            print(json.dumps(dict(event='acquisition_query_complete', life=life, query=query)), flush=True)
    data = dict(life=life, trace=trace, cases=cases, loads=loads,
        root_prediction_counts=dict(work), seconds=perf_counter()-started)
    save(folder / 'lifecycle.json', data); return data


def assemble_roster(prepared):
    cases = sorted([deepcopy(c) for life in prepared for c in life['cases']], key=lambda c: c['root_id'])
    budgets = {split: sum(len(c['actions'])*SUFFIX_REPLICAS for c in cases if c['split'] == split)
               for split in ('TRAIN', 'HOLDOUT')}
    return dict(schema='acfqp.paired_ntuple.v130.roster', cases=cases,
        training_branches=budgets['TRAIN'], heldout_parent_branches=budgets['HOLDOUT'],
        heldout_full_branches=sum(c['available'] and c['split'] == 'HOLDOUT' for c in cases)*SUFFIX_REPLICAS,
        control_games=len(LIVES)*len(QUERIES)*len(METHODS)*REPLICAS)


def forced_row(root, action, replica, model, method):
    before = state(model)
    game = run_forced_continuation(root['board'], action, model, QUERIES[root['query']],
        suffix_seed(root['root_id'], replica), MAX_STEPS)
    row = dict(root_id=root['root_id'], life=root['life'], query=root['query'], split=root['split'],
        forced_action=action, method=method, replica=replica, seed=game['seed'],
        result=result(game, root['query'], policy_counts=game['policy_counts']), **compact_trace(game))
    row['result'].update(model_state_before=before, model_state_after=state(model))
    return row


def scratch_value(action, query):
    return action['score']/2048. + (QUERIES[query]['goal_bonus'] if max(action['afterstate']) >= 11 else 0.)


def pair_labels(root, outcomes):
    reference = root['parent']['action']; values = root['parent']['action_values']; rows = []
    for action in root['actions']:
        if action == reference: continue
        left, right = outcomes[action], outcomes[reference]
        eligible = all(r['result']['status'] in ('WON', 'LOST') for r in left+right)
        gaps = [a['result']['utility']-b['result']['utility'] for a, b in zip(left, right)]
        rows.append(dict(root_id=root['root_id'], life=root['life'], query=root['query'],
            reference_action=reference, action=action, afterstate=values[action]['afterstate'],
            reference_afterstate=values[reference]['afterstate'], eligible=eligible,
            paired_gaps=gaps, target_gap=sum(gaps)/len(gaps) if eligible else None,
            base_gaps=dict(PRIOR=values[action]['value']-values[reference]['value'],
                SCRATCH=scratch_value(values[action], root['query'])-scratch_value(values[reference], root['query']))))
    return rows


def fit_lifecycle(source, roots, directory):
    started = perf_counter(); life = source['life']; folder = directory / f'fit_{life}'; folder.mkdir()
    trace = str((folder / 'branches.jsonl.gz').relative_to(directory))
    epoch_trace = str((folder / 'epochs.jsonl.gz').relative_to(directory))
    labels, frozen_predictions, queries = [], [], {}
    with gzip.open(directory / trace, 'wt') as stream, gzip.open(directory / epoch_trace, 'wt') as epochs:
        for query in QUERIES:
            parent, loads = load_parent(source, query, folder); before = state(parent)
            subset = [r for r in roots if r['query'] == query and r['available']]
            targets = []
            for root in subset:
                if root['split'] != 'TRAIN': continue
                outcomes = {}
                for action in root['actions']:
                    outcomes[action] = []
                    for replica in range(SUFFIX_REPLICAS):
                        row = forced_row(root, action, replica, parent, 'PARENT')
                        append(stream, row); outcomes[action].append(row)
                targets.extend(pair_labels(root, outcomes)); stream.flush()
                print(json.dumps(dict(event='training_root_complete', life=life, query=query, root_id=root['root_id'])), flush=True)
            labels.extend(targets)
            models = {kind: PairResidual(parent, kind, folder / 'build') for kind in KINDS}
            for kind, model in models.items():
                for epoch in range(EPOCHS):
                    previous = dict(model.counts); begin = perf_counter(); squared_error, calls = 0., 0
                    for label in targets:
                        if not label['eligible']: continue
                        fit = model.fit_pair(label['afterstate'], label['reference_afterstate'],
                            label['base_gaps'][kind], label['target_gap'], RATE)
                        squared_error += fit['error']**2; calls += 1
                    append(epochs, dict(life=life, query=query, kind=kind, epoch=epoch,
                        calls=calls, online_squared_error=squared_error,
                        counts=counter_delta(model.counts, previous), seconds=perf_counter()-begin))
                model.weights.flags.writeable = False
            # Freeze predictions before any held-out branch has been sampled.
            for root in subset:
                frozen_predictions.append(dict(root_id=root['root_id'], query=query, split=root['split'],
                    methods=dict(PARENT=root['parent'], **{k: prediction(m.choose(root['board'])) for k, m in models.items()})))
            checkpoints = {kind: model.save(folder / f'{query}_{kind}.npz') for kind, model in models.items()}
            queries[query] = dict(loads=loads, model_state_before=before, model_state_after=state(parent),
                parent_counts=dict(parent.counts), checkpoints=checkpoints,
                learners={kind: dict(counts=dict(m.counts), setup_counts=dict(m.setup_counts),
                    setup_seconds=m.setup_seconds, state=state(m)) for kind, m in models.items()})
            print(json.dumps(dict(event='query_heads_frozen', life=life, query=query,
                labels=len(targets), updates={k: m.updates for k, m in models.items()})), flush=True)
    labels_path = str((folder / 'labels.json').relative_to(directory))
    predictions_path = str((folder / 'predictions.json').relative_to(directory))
    save(directory / labels_path, labels); save(directory / predictions_path, frozen_predictions)
    data = dict(life=life, trace=trace, epoch_trace=epoch_trace, labels=labels_path,
        predictions=predictions_path, queries=queries, seconds=perf_counter()-started)
    save(folder / 'lifecycle.json', data); return data


def evaluate_lifecycle(source, fit, roots, directory):
    started = perf_counter(); life = source['life']; folder = directory / f'eval_{life}'; folder.mkdir()
    trace = str((folder / 'heldout.jsonl.gz').relative_to(directory))
    control_trace = str((folder / 'control.jsonl.gz').relative_to(directory)); queries = {}
    frozen = {row['root_id']: row for row in json.loads((directory / fit['predictions']).read_text())}
    with gzip.open(directory / trace, 'wt') as stream, gzip.open(directory / control_trace, 'wt') as controls:
        for query in QUERIES:
            parent, loads = load_parent(source, query, folder); before = state(parent)
            models = {'PARENT': parent}
            for kind in KINDS:
                model = PairResidual.load(fit['queries'][query]['checkpoints'][kind]['path'], parent, folder / 'build')
                model.weights.flags.writeable = False; models[kind] = model
            for root in roots:
                if root['query'] != query or not root['available'] or root['split'] != 'HOLDOUT': continue
                if any(prediction(m.choose(root['board'])) != frozen[root['root_id']]['methods'][k]
                       for k, m in models.items()):
                    raise ValueError('loaded frozen predictions changed')
                for action in root['actions']:
                    for replica in range(SUFFIX_REPLICAS):
                        append(stream, forced_row(root, action, replica, parent, 'PARENT'))
                action = frozen[root['root_id']]['methods']['PRIOR']['action']
                for replica in range(SUFFIX_REPLICAS):
                    append(stream, forced_row(root, action, replica, models['PRIOR'], 'FULL_UPDATE'))
                stream.flush()
                print(json.dumps(dict(event='heldout_root_complete', life=life, query=query, root_id=root['root_id'])), flush=True)
            for method, model in models.items():
                for replica in range(REPLICAS): append(controls, full_game(model, life, query, method, replica)[0])
                controls.flush()
                print(json.dumps(dict(event='control_complete', life=life, query=query, method=method)), flush=True)
            queries[query] = dict(loads=loads, model_state_before=before, model_state_after=state(parent),
                parent_counts=dict(parent.counts), learners={kind: dict(load_counts=models[kind].load_counts,
                    load_seconds=models[kind].last_load_seconds, setup_counts=dict(models[kind].setup_counts),
                    setup_seconds=models[kind].setup_seconds, counts=dict(models[kind].counts),
                    state=state(models[kind])) for kind in KINDS})
    data = dict(life=life, trace=trace, control_trace=control_trace, queries=queries, seconds=perf_counter()-started)
    save(folder / 'lifecycle.json', data); return data


def snapshot_code(directory):
    importlib.import_module('scripts.analyze_controlled_predictive_paired_ntuple_v130')
    files = {Path(__file__).resolve(), ROOT / 'specs/PAIRED_NTUPLE_V130.md'}
    for module in list(sys.modules.values()):
        filename = getattr(module, '__file__', None)
        if filename:
            path = Path(filename).resolve()
            if path.is_relative_to(ROOT / 'src') or path.is_relative_to(ROOT / 'scripts'): files.add(path)
    for filename in ('controlled_predictive_ntuple_kernel_v120.cpp', 'controlled_predictive_paired_ntuple_v130.cpp'):
        files.add(ROOT / 'src/acfqp/science' / filename)
    files.update((ROOT / 'tests').glob('*paired_ntuple*v130.py'))
    for path in files:
        target = directory / 'source' / path.relative_to(ROOT); target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)


def run(directory):
    directory = directory.resolve(); started = perf_counter(); directory.mkdir(parents=True, exist_ok=False)
    source = extract_source(json.loads((SOURCE / 'source_capsule.json').read_text()), json.loads((SOURCE / 'analysis.json').read_text()))
    save(directory / 'source_capsule.json', source); snapshot_code(directory)
    data = dict(schema='acfqp.paired_ntuple.v130.run', status='acquisition', settings=settings(),
        inherited_costs=source['inherited_costs'], acquisition_lifecycles=[], fit_lifecycles=[], eval_lifecycles=[],
        executable=sys.executable, platform=platform.platform())
    save(directory / 'run.json', data)
    with ProcessPoolExecutor(max_workers=WORKERS) as pool:
        tasks = [pool.submit(prepare_lifecycle, s, directory) for s in source['snapshots']]
        for future in as_completed(tasks):
            data['acquisition_lifecycles'].append(future.result())
            data['acquisition_lifecycles'].sort(key=lambda x: x['life']); save(directory / 'run.json', data)
        roster = assemble_roster(data['acquisition_lifecycles']); save(directory / 'roster.json', roster)
        data['status'] = 'training'; save(directory / 'run.json', data)
        print(json.dumps(dict(event='roster_frozen', **{k: v for k, v in roster.items() if k != 'cases'})), flush=True)
        tasks = [pool.submit(fit_lifecycle, s, [r for r in roster['cases'] if r['life'] == s['life']], directory)
                 for s in source['snapshots']]
        for future in as_completed(tasks):
            data['fit_lifecycles'].append(future.result()); data['fit_lifecycles'].sort(key=lambda x: x['life'])
            save(directory / 'run.json', data)
        data['status'] = 'frozen'; save(directory / 'frozen_heads.json', deepcopy(data)); save(directory / 'run.json', data)
        print(json.dumps(dict(event='all_heads_frozen')), flush=True)
        fits = {r['life']: r for r in data['fit_lifecycles']}
        data['status'] = 'evaluation'; save(directory / 'run.json', data)
        tasks = [pool.submit(evaluate_lifecycle, s, fits[s['life']],
            [r for r in roster['cases'] if r['life'] == s['life']], directory) for s in source['snapshots']]
        for future in as_completed(tasks):
            data['eval_lifecycles'].append(future.result()); data['eval_lifecycles'].sort(key=lambda x: x['life'])
            save(directory / 'run.json', data)
    data.update(status='complete', seconds=perf_counter()-started); save(directory / 'run.json', data)
    print(json.dumps(dict(status='complete', seconds=data['seconds'])), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'reports/controlled_predictive_paired_ntuple_v130')
    run(parser.parse_args().output)
