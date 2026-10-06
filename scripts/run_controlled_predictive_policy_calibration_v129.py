"""Fit source-only scalar offsets, freeze, then test paired policy comparison and control."""
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
from scripts.analyze_controlled_predictive_ntuple_learning_v120 import read_rows
from scripts.run_controlled_predictive_forced_actions_v128 import load_source
from acfqp.science.controlled_predictive_regime_experience_v115 import run_episode
from acfqp.science.controlled_predictive_forced_actions_v128 import load_anchored_success, run_forced_continuation

SOURCE = ROOT / 'reports/controlled_predictive_forced_actions_v128'
QUERIES = {q: ALL_QUERIES[q] for q in ('risk1', 'risk8')}
LIVES, REPLICAS, ROOT_REPLICAS, SUFFIX_REPLICAS = (0, 1, 2, 3), 8, 2, 8
ROOT_INDICES, MAX_STEPS, WORKERS, BASE = (128, 512), 2000, 4, 129 * 100000000
METHODS = ('UNCAL_LEARNED', 'CAL_LEARNED', 'UNCAL_CONSTANT', 'CAL_CONSTANT')


def settings():
    return dict(lifecycles=list(LIVES), policies=POLICIES, queries=QUERIES,
        training_games=1024, replicas=REPLICAS, root_replicas=ROOT_REPLICAS,
        suffix_replicas=SUFFIX_REPLICAS, root_indices=list(ROOT_INDICES), methods=list(METHODS),
        max_steps=MAX_STEPS, workers=WORKERS, p_four=.1, version_base=BASE)


def source_seed(life, replica, root=False):
    return BASE + (10000000 if root else 90000000) + life * 100000 + replica


def suffix_seed(root_id, replica):
    return BASE + 50000000 + root_id * 1000 + replica


def extract_source(previous, analysis):
    if not analysis['complete']: raise ValueError('V128 diagnosis must be complete')
    snapshots = []
    for old in previous['snapshots']:
        row = {k: deepcopy(old[k]) for k in ('life', 'rule', 'models', 'counts')}
        row['training_trace'] = str(ROOT / 'reports/controlled_predictive_policy_consequences_v126' /
                                    f'life_{row["life"]}' / 'training.jsonl.gz')
        snapshots.append(row)
    return dict(schema='acfqp.policy_calibration.v129.source', snapshots=snapshots,
        inherited_costs=dict(**deepcopy(previous['inherited_costs']), v128_diagnosis=deepcopy(analysis['costs'])))


def load_models(source, folder):
    models, costs = [], {}
    for policy in POLICIES:
        actor = load_source(source, policy, folder / 'build')
        model = load_anchored_success(source['counts'][policy]['path'], actor, POLICIES[policy], folder / 'build')
        if (model.updates, model.successes) != (source['counts'][policy]['updates'], source['counts'][policy]['successes']):
            raise ValueError('frozen event counts changed')
        costs[policy] = dict(source_updates=actor.updates, count_updates=model.updates, count_successes=model.successes,
            source_load_counts={k: v for k, v in actor.counts.items() if k.startswith('checkpoint_load')},
            source_load_seconds=actor.last_load_seconds, source_setup_counts=dict(actor.setup_counts),
            source_setup_seconds=actor.setup_seconds, count_load_counts=model.load_counts,
            count_load_seconds=model.last_load_seconds, count_setup_counts=dict(model.setup_counts),
            count_setup_seconds=model.setup_seconds)
        models.append(model)
    return models, costs


def model_state(models):
    return [dict(source_updates=m.source.updates, count_updates=m.updates, count_successes=m.successes) for m in models]


def fit_lifecycle(source, directory):
    from acfqp.science.controlled_predictive_policy_calibration_v129 import PolicyOffsetCalibrator
    started = perf_counter(); life = source['life']; folder = directory / f'fit_{life}'; folder.mkdir()
    models, loads = load_models(source, folder); before = model_state(models)
    calibrators = {p: PolicyOffsetCalibrator(m.source, POLICIES[p], folder / 'build') for p, m in zip(POLICIES, models)}
    ordered = dict(zip(POLICIES, models)); episodes = Counter(); replay_counts = Counter(); replay_seconds = 0.
    trace = str((folder / 'fit.jsonl.gz').relative_to(directory))
    with gzip.open(directory / trace, 'wt') as stream:
        for row in read_rows(Path(source['training_trace'])):
            policy = row['policy']; model = ordered[policy]
            if row['episode_index'] != episodes[policy]: raise ValueError('source training episode order changed')
            previous = dict(model.counts); begin = perf_counter(); afterstates = model.replay(row)
            elapsed = perf_counter()-begin; work = counter_delta(model.counts, previous)
            fit = calibrators[policy].fit_episode(afterstates, row['scores'], row['result']['status'])
            append(stream, dict(life=life, policy=policy, episode_index=row['episode_index'], source_seed=row['seed'],
                fit=fit, replay_counts=work, replay_seconds=elapsed))
            episodes[policy] += 1; replay_counts.update(work); replay_seconds += elapsed
            if episodes[policy] % 256 == 0:
                stream.flush(); print(json.dumps(dict(event='fit_block', life=life, policy=policy,
                    episodes=episodes[policy], offset=calibrators[policy].offset)), flush=True)
    if episodes != Counter({p: 1024 for p in POLICIES}): raise ValueError('source fitting corpus incomplete')
    policies = {p: dict(n=c.n, target_sum=c.target_sum, anchor_sum=c.anchor_sum,
        residual_sum=c.residual_sum, offset=c.offset, counts=dict(c.counts),
        setup_counts=dict(c.setup_counts), setup_seconds=c.setup_seconds) for p, c in calibrators.items()}
    data = dict(life=life, trace=trace, policies=policies, loads=loads, episodes=dict(episodes),
        replay_counts=dict(replay_counts), replay_seconds=replay_seconds,
        model_state_before=before, model_state_after=model_state(models), seconds=perf_counter()-started)
    save(folder / 'lifecycle.json', data); return data


def original_game(model, life, policy, replica, root=False):
    actor = model.source; previous = dict(actor.counts); updates = actor.updates
    game = run_episode(source_seed(life, replica, root), lambda board, step: actor.choose(board, POLICIES[policy])['action'], .1, MAX_STEPS)
    method = ('ROOT_' if root else 'FROZEN_') + policy
    row = dict(life=life, policy=policy, query=policy, method=method, replica=replica,
        seed=game['seed'], eval_id=f'{life}/{method}/{replica}',
        result=result(game, policy, policy_counts=counter_delta(actor.counts, previous)), **compact_trace(game))
    row['result'].update(source_updates_before=updates, source_updates_after=actor.updates)
    return row, game


def root_predictions(models, board):
    from acfqp.science.controlled_predictive_policy_calibration_v129 import calibrated_choice
    candidates, predictions, actions = {}, {}, set()
    for query in QUERIES:
        candidates[query] = {}
        for mode in ('LEARNED', 'CONSTANT'):
            choice = calibrated_choice(models, [0., 0.], board, QUERIES[query], mode=mode)
            candidates[query][mode] = choice['per_policy_candidates']
            actions.update(c['action'] for c in choice['per_policy_candidates'])
            if query == 'risk1' and mode == 'LEARNED':
                for policy, rows in zip(POLICIES, choice['per_policy_action_values']):
                    predictions[policy] = {a: dict(value=r['anchor_value'], success_probability=r['success_probability'],
                        score=r['score'], afterstate=r['afterstate']) for a, r in rows.items()}
    return dict(board=list(board), predictions=predictions, candidates=candidates, actions=sorted(actions))


def prepare_lifecycle(source, directory):
    started = perf_counter(); life = source['life']; folder = directory / f'panel_{life}'; folder.mkdir()
    models, loads = load_models(source, folder); state = model_state(models); cases, roots, root_ids = [], [], {}
    before = [dict(m.counts) for m in models]
    trace = str((folder / 'acquisition.jsonl.gz').relative_to(directory))
    with gzip.open(directory / trace, 'wt') as stream:
        for policy, model in zip(POLICIES, models):
            for replica in range(ROOT_REPLICAS):
                row, game = original_game(model, life, policy, replica, root=True); append(stream, row)
                for index in ROOT_INDICES:
                    available = index < game['steps_count']
                    case = dict(life=life, policy=policy, replica=replica, index=index,
                        source_eval_id=row['eval_id'], available=available, board=None, local_root_id=None)
                    if available:
                        board = tuple(game['steps'][index]['board']); case['board'] = list(board)
                        if board not in root_ids:
                            root_ids[board] = len(roots); roots.append(root_predictions(models, board))
                        case['local_root_id'] = root_ids[board]
                    cases.append(case)
    work = Counter()
    for model, previous in zip(models, before): work.update(counter_delta(model.counts, previous))
    data = dict(life=life, trace=trace, cases=cases, roots=roots, loads=loads,
        prediction_counts=dict(work), model_state_before=state, model_state_after=model_state(models), seconds=perf_counter()-started)
    save(folder / 'lifecycle.json', data); return data


def assemble_roster(prepared):
    cases, roots, keys = [], [], {}
    for life in sorted(prepared, key=lambda x: x['life']):
        for original in life['cases']:
            case = {k: deepcopy(v) for k, v in original.items() if k != 'local_root_id'}
            case.update(case_id=len(cases), root_id=None)
            if case['available']:
                key = case['life'], tuple(case['board'])
                if key not in keys:
                    keys[key] = len(roots)
                    roots.append(dict(deepcopy(life['roots'][original['local_root_id']]), root_id=len(roots), life=case['life']))
                case['root_id'] = keys[key]
            cases.append(case)
    return dict(schema='acfqp.policy_calibration.v129.roster', cases=cases, roots=roots,
        physical_attempts=sum(len(r['actions']) for r in roots)*len(POLICIES)*SUFFIX_REPLICAS,
        logical_attempts=sum(len(roots[c['root_id']]['actions']) for c in cases if c['available'])*len(POLICIES)*SUFFIX_REPLICAS)


def forced_row(root, action, policy, replica, actor):
    game = run_forced_continuation(root['board'], action, actor, POLICIES[policy], suffix_seed(root['root_id'], replica), MAX_STEPS)
    row = dict(root_id=root['root_id'], life=root['life'], forced_action=action, policy=policy,
        replica=replica, seed=game['seed'], result=result(game, policy, policy_counts=game['policy_counts']), **compact_trace(game))
    row['result'].update(source_updates_before=game['source_updates_before'], source_updates_after=game['source_updates_after'])
    return row


def control_game(models, offsets, life, query, method, replica):
    from acfqp.science.controlled_predictive_policy_calibration_v129 import calibrated_choice
    calibration, mode = method.split('_', 1); shifts = offsets if calibration == 'CAL' else [0., 0.]
    before = [dict(m.counts) for m in models]; state = model_state(models)
    indices, candidate_actions, values, comparisons, goals = [], [], [], [], []
    def act(board, step):
        choice = calibrated_choice(models, shifts, board, QUERIES[query], mode=mode)
        rows = choice['per_policy_candidates']; indices.append(choice['policy_index'])
        candidate_actions.append([r['action'] for r in rows]); values.append([r['value'] for r in rows])
        comparisons.append([r['comparison_value'] for r in rows]); goals.append([max(r['afterstate']) >= 11 for r in rows])
        return choice['action']
    game = run_episode(source_seed(life, replica), act, .1, MAX_STEPS)
    work = Counter()
    for model, previous in zip(models, before): work.update(counter_delta(model.counts, previous))
    row = dict(life=life, query=query, method=method, policy=None, replica=replica, seed=game['seed'],
        eval_id=f'{life}/{method}/{query}/{replica}', result=result(game, query, learning_counts=dict(work)),
        **compact_trace(game), policy_indices=indices, candidate_actions=candidate_actions,
        candidate_values=values, comparison_values=comparisons, candidate_goals=goals)
    row['result'].update(model_state_before=state, model_state_after=model_state(models),
        controller_counts=dict(candidate_evaluations=2*game['steps_count'], policy_comparisons=game['steps_count'],
            offset_additions=2*game['steps_count']-sum(sum(g) for g in goals)))
    return row


def evaluate_lifecycle(source, offsets, roots, directory):
    started = perf_counter(); life = source['life']; folder = directory / f'eval_{life}'; folder.mkdir()
    models, loads = load_models(source, folder); state = model_state(models)
    forced_trace = str((folder / 'continuations.jsonl.gz').relative_to(directory))
    control_trace = str((folder / 'control.jsonl.gz').relative_to(directory))
    with gzip.open(directory / forced_trace, 'wt') as stream:
        for root in roots:
            for action in root['actions']:
                for policy, model in zip(POLICIES, models):
                    for replica in range(SUFFIX_REPLICAS): append(stream, forced_row(root, action, policy, replica, model.source))
            stream.flush(); print(json.dumps(dict(event='root_complete', life=life, root_id=root['root_id'])), flush=True)
    with gzip.open(directory / control_trace, 'wt') as stream:
        for policy, model in zip(POLICIES, models):
            for replica in range(REPLICAS): append(stream, original_game(model, life, policy, replica)[0])
        shifts = [offsets[p] for p in POLICIES]
        for query in QUERIES:
            for method in METHODS:
                for replica in range(REPLICAS): append(stream, control_game(models, shifts, life, query, method, replica))
                stream.flush(); print(json.dumps(dict(event='control_complete', life=life, query=query, method=method)), flush=True)
    data = dict(life=life, forced_trace=forced_trace, control_trace=control_trace, loads=loads,
        model_state_before=state, model_state_after=model_state(models),
        peak_weight_bytes=sum(m.source.weights.nbytes+m.visits.nbytes+m.wins.nbytes for m in models), seconds=perf_counter()-started)
    save(folder / 'lifecycle.json', data); return data


def snapshot_code(directory):
    importlib.import_module('acfqp.science.controlled_predictive_policy_calibration_v129')
    importlib.import_module('scripts.analyze_controlled_predictive_policy_calibration_v129')
    files = {Path(__file__).resolve(), ROOT / 'specs/POLICY_CALIBRATION_V129.md'}
    for module in list(sys.modules.values()):
        filename = getattr(module, '__file__', None)
        if filename:
            path = Path(filename).resolve()
            if path.is_relative_to(ROOT / 'src') or path.is_relative_to(ROOT / 'scripts'): files.add(path)
    for filename in ('controlled_predictive_ntuple_kernel_v120.cpp', 'controlled_predictive_anchored_success_v127.cpp',
                     'controlled_predictive_policy_calibration_v129.cpp'):
        files.add(ROOT / 'src/acfqp/science' / filename)
    files.update((ROOT / 'tests').glob('*policy_calibration*v129.py'))
    for path in files:
        target = directory / 'source' / path.relative_to(ROOT); target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)


def run(directory):
    directory = directory.resolve(); started = perf_counter(); directory.mkdir(parents=True, exist_ok=False)
    source = extract_source(json.loads((SOURCE / 'source_capsule.json').read_text()), json.loads((SOURCE / 'analysis.json').read_text()))
    save(directory / 'source_capsule.json', source); snapshot_code(directory)
    data = dict(schema='acfqp.policy_calibration.v129.run', status='fitting', settings=settings(),
        inherited_costs=source['inherited_costs'], fit_lifecycles=[], panel_lifecycles=[], lifecycles=[],
        executable=sys.executable, platform=platform.platform())
    save(directory / 'run.json', data)
    with ProcessPoolExecutor(max_workers=WORKERS) as pool:
        for key, function in (('fit_lifecycles', fit_lifecycle), ('panel_lifecycles', prepare_lifecycle)):
            tasks = [pool.submit(function, s, directory) for s in source['snapshots']]
            for future in as_completed(tasks):
                data[key].append(future.result()); data[key].sort(key=lambda x: x['life']); save(directory / 'run.json', data)
            if key == 'fit_lifecycles':
                calibration = dict(schema='acfqp.policy_calibration.v129.frozen',
                    lifecycles=[dict(life=r['life'], offsets={p: r['policies'][p]['offset'] for p in POLICIES}) for r in data[key]])
                save(directory / 'calibration.json', calibration); data['status'] = 'root_acquisition'
                save(directory / 'run.json', data); print(json.dumps(dict(event='calibration_frozen', **calibration)), flush=True)
        roster = assemble_roster(data['panel_lifecycles']); save(directory / 'roster.json', roster)
        data['status'] = 'evaluation'; save(directory / 'run.json', data)
        print(json.dumps(dict(event='roster_frozen', cases=len(roster['cases']), roots=len(roster['roots']), physical_attempts=roster['physical_attempts'])), flush=True)
        offsets = {r['life']: r['offsets'] for r in calibration['lifecycles']}
        tasks = [pool.submit(evaluate_lifecycle, s, offsets[s['life']],
            [r for r in roster['roots'] if r['life'] == s['life']], directory) for s in source['snapshots']]
        for future in as_completed(tasks):
            data['lifecycles'].append(future.result()); data['lifecycles'].sort(key=lambda x: x['life']); save(directory / 'run.json', data)
    data.update(status='complete', seconds=perf_counter()-started); save(directory / 'run.json', data)
    print(json.dumps(dict(status='complete', seconds=data['seconds'])), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'reports/controlled_predictive_policy_calibration_v129')
    run(parser.parse_args().output)
