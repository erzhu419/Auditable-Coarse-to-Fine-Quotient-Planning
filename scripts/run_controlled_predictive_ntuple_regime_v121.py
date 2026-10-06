"""Continue the frozen V120 learner through unannounced B and returning A."""
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
import argparse
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
from scripts.run_controlled_predictive_ntuple_learning_v120 import (
    QUERIES, ALPHA, LIVES, REPLICAS, MAX_STEPS, WORKERS, save, append,
    counter_delta, compact_trace, game_result)
from acfqp.science.controlled_predictive_regime_experience_v115 import run_episode
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics
from acfqp.science.controlled_predictive_ntuple_td_v120 import NtupleValue

SOURCE = ROOT / 'reports/controlled_predictive_ntuple_learning_v120'
PHASES = dict(B=.5, A_RETURN=.1)
CHECKPOINTS, TRAIN_TRANSITIONS, BLOCK_EPISODES = (0, 131072, 524288), 524288, 64
BASE = 121 * 100_000_000


def train_seed(life, query, phase, episode):
    return (BASE + 1_000_000 + life * 10_000_000 + list(QUERIES).index(query) * 4_000_000
        + list(PHASES).index(phase) * 1_000_000 + episode)


def evaluation_seed(life, phase, replica):
    return BASE + 90_000_000 + life * 100000 + list(PHASES).index(phase) * 10000 + replica


def extract_source(previous, previous_capsule):
    snapshots = []
    for source in previous_capsule['snapshots']:
        life = next(row for row in previous['lifecycles'] if row['life'] == source['life'])
        models, costs = {}, {}
        for query, value in life['queries'].items():
            final = next(cp for cp in value['checkpoints'] if cp['episodes'] == 4096)
            models[query] = dict(path=str(SOURCE / final['model_file']), updates=final['updates'],
                nonzero_weights=final['model_metadata']['nonzero_weights'])
            costs[query] = dict(training_blocks=deepcopy(value['training_blocks']),
                setup_counts=deepcopy(value['setup_counts']), setup_seconds=value['setup_seconds'],
                checkpoint_save_counts=dict(sum((Counter(cp['save_counts'])
                    for cp in value['checkpoints']), Counter())),
                checkpoint_save_seconds=sum(cp['save_seconds'] for cp in value['checkpoints']))
        snapshots.append(dict(life=source['life'], rule=deepcopy(source['rule']), models=models))
        # Costs are retained per history/query so prior learning is never called free.
        snapshots[-1]['v120_training_costs'] = costs
    if sorted(row['life'] for row in snapshots) != list(LIVES):
        raise ValueError('V121 requires four V120 final histories')
    return dict(schema='acfqp.ntuple_regime.v121.source', snapshots=snapshots,
        inherited_costs=dict(deterministic_prior=deepcopy(previous['inherited_costs']),
            v120_training=[dict(life=row['life'], queries=row['v120_training_costs'])
                for row in snapshots],
            scope='V120 training, model setup and all saved checkpoints retained separately; '
                'V120 evaluations, H2/MC4 decisions and outer outcomes are not inputs.'))


def snapshot(directory):
    importlib.import_module('scripts.analyze_controlled_predictive_ntuple_regime_v121')
    files = {Path(__file__).resolve(), ROOT / 'specs/NTUPLE_REGIME_V121.md',
        ROOT / 'src/acfqp/science/controlled_predictive_ntuple_kernel_v120.cpp'}
    for module in list(sys.modules.values()):
        filename = getattr(module, '__file__', None)
        if filename:
            path = Path(filename).resolve()
            if path.is_relative_to(ROOT / 'src') or path.is_relative_to(ROOT / 'scripts'):
                files.add(path)
    for path in files:
        target = directory / 'source' / path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)


def td_game(model, life, query, phase, method, *, episode=None,
        transitions_before=0, checkpoint=None, replica=None, max_steps=MAX_STEPS):
    """The actor sees boards and query only; phase controls the environment outside it."""
    training = episode is not None
    seed = (train_seed(life, query, phase, episode) if training
        else evaluation_seed(life, phase, replica))
    q, before = QUERIES[query], dict(model.counts)
    updates_before, pending = model.updates, None
    def act(board, step):
        nonlocal pending
        chosen = model.choose(board, q)
        if training and pending is not None:
            model.update(pending, chosen['value'], ALPHA)
        pending = None if max(chosen['afterstate']) >= model.rule.goal_rank else chosen['afterstate']
        return chosen['action']
    game = run_episode(seed, act, PHASES[phase], max_steps)
    terminal_update = training and game['status'] == 'LOST' and pending is not None
    if terminal_update:
        started = perf_counter(); model.update(pending, -q['failure_penalty'], ALPHA)
        game['seconds'] += perf_counter() - started
    expected = game['steps_count'] - (game['status'] in ('WON', 'CUTOFF')) if training else 0
    if model.updates - updates_before != expected:
        raise AssertionError('TD update count does not match terminal/censoring semantics')
    result = game_result(game, query, counter_delta(model.counts, before))
    result.update(updates_before=updates_before, updates_after=model.updates)
    row = dict(life=life, query=query, phase=phase, method=method, checkpoint=checkpoint,
        replica=replica, seed=seed, max_steps=max_steps, result=result)
    if training:
        row.update(episode_index=episode, transitions_before=transitions_before,
            transitions_after=transitions_before + game['steps_count'],
            terminal_update=terminal_update, censored_last_update=game['status'] == 'CUTOFF',
            analytic_terminal=game['status'] == 'WON')
    else:
        row.update(eval_id=f'{life}/{query}/{phase}/{method}/{checkpoint}/{replica}', reused_from=None)
    return row, dict(**row, **compact_trace(game))


def evaluate(model, life, query, phase, method, checkpoint, stream, reuse=None):
    if reuse is not None:
        rows = deepcopy(reuse)
        for row in rows:
            row['reused_from'] = row['reused_from'] or row['eval_id']
            row.update(method=method, checkpoint=checkpoint,
                eval_id=f'{life}/{query}/{phase}/{method}/{checkpoint}/{row["replica"]}')
        return rows
    rows = []
    for replica in range(REPLICAS):
        row, raw = td_game(model, life, query, phase, method,
            checkpoint=checkpoint, replica=replica)
        rows.append(row); append(stream, raw)
    stream.flush()
    return rows


def make_model(rule, build_dir, method, phase, source_model=None):
    if source_model is None:
        model = NtupleValue(rule, build_dir)
        load_counts, load_seconds, origin = {}, 0., 'implicit_zero'
    else:
        model = NtupleValue.load(source_model['path'], rule, build_dir)
        load_counts = dict(checkpoint_loads=1,
            checkpoint_loaded_parameters=source_model['nonzero_weights'])
        load_seconds = max(0., model.last_load_seconds - model.setup_seconds)
        origin = source_model['path']
        if model.updates != source_model['updates']:
            raise AssertionError('V120 source checkpoint updates do not match retained metadata')
    return model, dict(method=method, phase_origin=phase, origin_ref=origin,
        updates_at_creation=model.updates, setup_counts=dict(model.setup_counts),
        setup_seconds=model.setup_seconds, load_counts=load_counts, load_seconds=load_seconds)


def checkpoint(model, life, query, phase, method, label, transitions,
        model_ref, folder, directory, stream, reuse=None):
    result = dict(label=label, transitions=transitions, updates=model.updates,
        model_ref=model_ref, model_origin=('implicit_zero' if model_ref == 'implicit_zero'
            else 'source_v120' if Path(model_ref).is_absolute() else 'v121'))
    if label and method != 'FROZEN_A':
        path = folder / f'checkpoint_{label}.npz'
        before, started = dict(model.counts), perf_counter()
        metadata = model.save(path)
        result.update(model_ref=str(path.relative_to(directory)), model_origin='v121',
            model_bytes=path.stat().st_size, save_seconds=perf_counter() - started,
            save_counts=counter_delta(model.counts, before), model_metadata=metadata)
    result['evaluations'] = evaluate(model, life, query, phase, method, label, stream, reuse)
    return result


def empty_block(episode, transitions):
    return dict(start=episode, end=episode, transitions_before=transitions,
        transitions_after=transitions, games=0, environment_counts=Counter(),
        learning_counts=Counter(), statuses=Counter(), total_score=0, seconds=0.)


def add_training(block, row):
    result = row['result']
    block['end'] = row['episode_index'] + 1
    block['transitions_after'] = row['transitions_after']
    block['games'] += 1
    block['environment_counts'].update(result['environment_counts'])
    block['learning_counts'].update(result['learning_counts'])
    block['statuses'][result['status']] += 1
    block['total_score'] += result['score']; block['seconds'] += result['seconds']


def train_phase(model, life, query, phase, method, result, folder, directory,
        train_stream, control_stream, persist):
    transitions, episode, next_checkpoint = 0, 0, 1
    block = empty_block(0, 0)
    while transitions < TRAIN_TRANSITIONS:
        row, raw = td_game(model, life, query, phase, method, episode=episode,
            transitions_before=transitions, max_steps=min(MAX_STEPS, TRAIN_TRANSITIONS - transitions))
        if row['result']['steps'] <= 0:
            raise AssertionError('Supported fresh 2048 game must perform an action')
        append(train_stream, raw); add_training(block, row)
        transitions, episode = row['transitions_after'], episode + 1
        crossed = transitions >= CHECKPOINTS[next_checkpoint]
        if episode % BLOCK_EPISODES == 0 or crossed:
            train_stream.flush(); result['training_blocks'].append(block)
            block = empty_block(episode, transitions)
            if crossed:
                result['checkpoints'].append(checkpoint(model, life, query, phase, method,
                    CHECKPOINTS[next_checkpoint], transitions, result['checkpoints'][-1]['model_ref'],
                    folder, directory, control_stream))
                next_checkpoint += 1
            persist()
            print(json.dumps(dict(event='training_block_complete', life=life, query=query,
                phase=phase, method=method, transitions=transitions,
                episodes=episode, updates=model.updates)), flush=True)
    result.update(final_updates=model.updates, final_transitions=transitions, training_episodes=episode)
    persist()


def lifecycle_run(source, directory):
    started = perf_counter()
    folder = directory / f'life_{source["life"]}'; folder.mkdir()
    build_dir = folder / 'build'; build_dir.mkdir()
    lifecycle = dict(life=source['life'], queries={})
    def persist():
        save(folder / 'lifecycle.json', lifecycle)
    for query in QUERIES:
        query_folder = folder / query; query_folder.mkdir()
        rule = LearnedDynamics.from_payload(source['rule'])
        source_model = source['models'][query]
        result = dict(training_trace=str((query_folder / 'training.jsonl.gz').relative_to(directory)),
            control_trace=str((query_folder / 'control.jsonl.gz').relative_to(directory)),
            model_setup=[], phases={})
        lifecycle['queries'][query] = result
        frozen, setup = make_model(rule, build_dir, 'FROZEN_A', 'B', source_model)
        result['model_setup'].append(setup)
        continued, setup = make_model(rule, build_dir, 'CONT', 'B', source_model)
        result['model_setup'].append(setup)
        continued_ref = source_model['path']
        with gzip.open(directory / result['training_trace'], 'wt') as train_stream, \
                gzip.open(directory / result['control_trace'], 'wt') as control_stream:
            for phase, p_four in PHASES.items():
                phase_folder = query_folder / phase; phase_folder.mkdir()
                phase_result = dict(p_four=p_four, methods={})
                result['phases'][phase] = phase_result
                frozen_result = dict(checkpoints=[])
                phase_result['methods']['FROZEN_A'] = frozen_result
                frozen_zero = checkpoint(frozen, source['life'], query, phase, 'FROZEN_A',
                    0, 0, source_model['path'], phase_folder, directory, control_stream)
                frozen_result['checkpoints'].append(frozen_zero)
                for method in ('CONT', 'RESET'):
                    method_folder = phase_folder / method; method_folder.mkdir()
                    if method == 'CONT':
                        model, ref = continued, continued_ref
                    else:
                        model, setup = make_model(rule, build_dir, method, phase)
                        result['model_setup'].append(setup); ref = 'implicit_zero'
                    method_result = dict(training_blocks=[], checkpoints=[])
                    phase_result['methods'][method] = method_result
                    reuse = frozen_zero['evaluations'] if method == 'CONT' and phase == 'B' else None
                    method_result['checkpoints'].append(checkpoint(model, source['life'], query,
                        phase, method, 0, 0, ref, method_folder, directory, control_stream, reuse))
                    persist()
                    train_phase(model, source['life'], query, phase, method, method_result,
                        method_folder, directory, train_stream, control_stream, persist)
                    if method == 'CONT':
                        continued_ref = method_result['checkpoints'][-1]['model_ref']
                    else:
                        del model
        del frozen, continued
    lifecycle['seconds'] = perf_counter() - started; persist()
    return lifecycle


def run(directory):
    started = perf_counter(); directory.mkdir(parents=True, exist_ok=False)
    capsule = extract_source(json.loads((SOURCE / 'run.json').read_text()),
        json.loads((SOURCE / 'source_capsule.json').read_text()))
    save(directory / 'source_capsule.json', capsule); snapshot(directory)
    result = dict(schema='acfqp.ntuple_regime.v121.run', status='running',
        settings=dict(lifecycles=list(LIVES), queries=QUERIES, phases=PHASES,
            checkpoints=list(CHECKPOINTS), train_transitions=TRAIN_TRANSITIONS,
            replicas=REPLICAS, max_steps=MAX_STEPS, workers=WORKERS, alpha=ALPHA,
            block_episodes=BLOCK_EPISODES, version_base=BASE),
        inherited_costs=capsule['inherited_costs'], lifecycles=[],
        executable=sys.executable, platform=platform.platform())
    save(directory / 'run.json', result)
    with ProcessPoolExecutor(max_workers=WORKERS) as pool:
        tasks = [pool.submit(lifecycle_run, source, directory) for source in capsule['snapshots']]
        for future in as_completed(tasks):
            result['lifecycles'].append(future.result())
            result['lifecycles'].sort(key=lambda row: row['life']); save(directory / 'run.json', result)
    result.update(status='complete', seconds=perf_counter() - started)
    save(directory / 'run.json', result)
    print(json.dumps(dict(status='complete', seconds=result['seconds'])), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    run(parser.parse_args().output)
