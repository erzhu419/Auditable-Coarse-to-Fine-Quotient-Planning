"""Observed-context value banks on the frozen V121 B to returning-A stream."""
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
from scripts.run_controlled_predictive_ntuple_regime_v121 import (
    PHASES, CHECKPOINTS, TRAIN_TRANSITIONS, BLOCK_EPISODES, train_seed,
    empty_block, add_training)
from acfqp.science.controlled_predictive_regime_experience_v115 import run_episode, observed_rank
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics
from acfqp.science.controlled_predictive_ntuple_td_v120 import NtupleValue
from acfqp.science.controlled_predictive_ntuple_context_v122 import ContextValueBank

SOURCE = ROOT / 'reports/controlled_predictive_ntuple_regime_v121'
SOURCE_V120 = ROOT / 'reports/controlled_predictive_ntuple_learning_v120'
BASE = 122 * 100_000_000


def evaluation_seed(life, phase, replica):
    return BASE + 90_000_000 + life * 100000 + list(PHASES).index(phase) * 10000 + replica


def source_ranks(path):
    ranks, rows_read = [], 0
    with gzip.open(path, 'rt') as stream:
        for line in stream:
            rows_read += 1
            ranks.extend(json.loads(line)['spawned_ranks'][:256-len(ranks)])
            if len(ranks) == 256:
                return ranks, dict(path=str(path), rows_read=rows_read, retained_ranks=256)
    raise ValueError('V120 training does not contain 256 post-action spawn ranks')


def extract_source(previous, previous_capsule):
    """Reuse only CONT training checkpoints, plus the shared V120 prior."""
    snapshots, costs = [], []
    for source in previous_capsule['snapshots']:
        life = next(row for row in previous['lifecycles'] if row['life'] == source['life'])
        row = dict(life=source['life'], rule=deepcopy(source['rule']),
            models=deepcopy(source['models']), initial_ranks={}, initial_rank_sources={}, continued={})
        life_cost = dict(life=source['life'], queries={})
        for query, value in life['queries'].items():
            path = SOURCE_V120 / f'life_{source["life"]}' / query / 'training.jsonl.gz'
            row['initial_ranks'][query], row['initial_rank_sources'][query] = source_ranks(path)
            row['continued'][query] = {}
            query_cost = dict(model_setup=[deepcopy(item) for item in value['model_setup']
                if item['method'] == 'CONT'], phases={})
            saved_metadata = {cp['model_ref']: cp['model_metadata']
                for phase_value in value['phases'].values()
                for cp in phase_value['methods']['CONT']['checkpoints'] if 'model_metadata' in cp}
            for phase in PHASES:
                continued = value['phases'][phase]['methods']['CONT']
                checkpoints = []
                for cp in continued['checkpoints']:
                    ref = Path(cp['model_ref'])
                    if not ref.is_absolute():
                        ref = SOURCE / ref
                    checkpoints.append(dict(label=cp['label'], transitions=cp['transitions'],
                        updates=cp['updates'], path=str(ref),
                        nonzero_weights=saved_metadata.get(cp['model_ref'], {}).get('nonzero_weights',
                            source['models'][query]['nonzero_weights'])))
                row['continued'][query][phase] = checkpoints
                query_cost['phases'][phase] = dict(training_blocks=deepcopy(continued['training_blocks']),
                    final_updates=continued['final_updates'], final_transitions=continued['final_transitions'],
                    training_episodes=continued['training_episodes'],
                    checkpoint_save_counts=dict(sum((Counter(cp.get('save_counts', {}))
                        for cp in continued['checkpoints']), Counter())),
                    checkpoint_save_seconds=sum(cp.get('save_seconds', 0.) for cp in continued['checkpoints']))
            life_cost['queries'][query] = query_cost
        snapshots.append(row); costs.append(life_cost)
    if sorted(row['life'] for row in snapshots) != list(LIVES):
        raise ValueError('V122 requires four V121 source histories')
    return dict(schema='acfqp.context_bank.v122.source', snapshots=snapshots,
        inherited_costs=dict(shared_v120=deepcopy(previous['inherited_costs']), v121_cont=costs,
            scope='Shared V120 prior and only V121 CONT training/setup/saves; '
                'V121 RESET, outer evaluations and outcomes are excluded.'))


def snapshot(directory):
    importlib.import_module('scripts.analyze_controlled_predictive_context_bank_v122')
    files = {Path(__file__).resolve(), ROOT / 'specs/CONTEXT_BANK_V122.md',
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
    """Infer each spawn from boards before routing; choose before pending TD."""
    training, banked = episode is not None, method == 'BANK'
    seed = (train_seed(life, query, phase, episode) if training
        else evaluation_seed(life, phase, replica))
    q = QUERIES[query]
    before = dict(model.counts) if training or not banked else {}
    setup_before, setup_seconds = dict(model.setup_counts), model.setup_seconds
    updates_before, pending, last_afterstate = model.updates, None, None
    banks, events, skipped = [], [], []
    active_before = model.active_bank_id if banked else None
    obs_before = model.router.observations_seen if banked else None

    def observe(board, index):
        event = model.observe(observed_rank(dict(afterstate=last_afterstate, next_board=board)))
        if event is not None:
            events.append(dict(event, observed_action_index=index))

    def act(board, step):
        nonlocal pending, last_afterstate
        if banked and last_afterstate is not None:
            observe(board, step-1)
        chosen = model.choose(board, q)
        bank_id = chosen['bank_id'] if banked else None
        banks.append(bank_id)
        if training and pending is not None:
            afterstate, origin = pending
            if banked:
                if not model.update_pending(afterstate, origin, chosen['value'], ALPHA):
                    skipped.append(step-1)
            else:
                model.update(afterstate, chosen['value'], ALPHA)
        last_afterstate = chosen['afterstate']
        pending = (None if max(last_afterstate) >= model.rule.goal_rank
            else (last_afterstate, bank_id))
        return chosen['action']

    game = run_episode(seed, act, PHASES[phase], max_steps)
    started = perf_counter()
    if banked and last_afterstate is not None:
        observe(game['final_board'], game['steps_count']-1)
    terminal_attempt = training and game['status'] == 'LOST' and pending is not None
    terminal_update = False
    if terminal_attempt:
        if banked:
            terminal_update = model.update_pending(pending[0], pending[1], -q['failure_penalty'], ALPHA)
            if not terminal_update:
                skipped.append(game['steps_count']-1)
        else:
            model.update(pending[0], -q['failure_penalty'], ALPHA)
            terminal_update = True
    game['seconds'] += perf_counter()-started
    expected = game['steps_count'] - (game['status'] in ('WON', 'CUTOFF')) if training else 0
    if model.updates - updates_before + len(skipped) != expected:
        raise AssertionError('TD count differs from terminal/censoring/context-switch semantics')
    if banked and model.router.observations_seen-obs_before != game['steps_count']:
        raise AssertionError('Every post-action spawn must be observed exactly once')
    result = game_result(game, query, counter_delta(model.counts, before))
    result.update(updates_before=updates_before, updates_after=model.updates,
        setup_counts=counter_delta(model.setup_counts, setup_before),
        setup_seconds=model.setup_seconds-setup_seconds,
        active_bank_before=active_before, active_bank_after=model.active_bank_id if banked else None,
        router_observations_before=obs_before,
        router_observations_after=model.router.observations_seen if banked else None)
    row = dict(life=life, query=query, phase=phase, method=method, checkpoint=checkpoint,
        replica=replica, seed=seed, max_steps=max_steps, result=result)
    if training:
        row.update(episode_index=episode, transitions_before=transitions_before,
            transitions_after=transitions_before + game['steps_count'],
            terminal_update=terminal_update, terminal_update_attempted=terminal_attempt,
            censored_last_update=game['status'] == 'CUTOFF', analytic_terminal=game['status'] == 'WON')
    else:
        row.update(eval_id=f'{life}/{query}/{phase}/{method}/{checkpoint}/{replica}', reused_from=None)
    return row, dict(**row, **compact_trace(game), bank_ids=banks if banked else [],
        final_bank_id=model.active_bank_id if banked else None,
        routing_events=events, cross_context_skips=skipped)


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
        started = perf_counter()
        actor = model.evaluation_copy() if method == 'BANK' else model
        copy_seconds = perf_counter()-started if method == 'BANK' else 0.
        row, raw = td_game(actor, life, query, phase, method, checkpoint=checkpoint, replica=replica)
        row['result']['evaluation_copy_seconds'] = copy_seconds
        # Raw and summary share result until serialized, including the copy work.
        rows.append(row); append(stream, raw)
    stream.flush()
    return rows


def make_model(rule, build_dir, method, phase, source_model):
    model = NtupleValue.load(source_model['path'], rule, build_dir)
    if model.updates != source_model['updates']:
        raise AssertionError('Source checkpoint updates differ from retained metadata')
    return model, dict(method=method, phase_origin=phase, origin_ref=source_model['path'],
        updates_at_creation=model.updates, setup_counts=dict(model.setup_counts),
        setup_seconds=model.setup_seconds, load_counts=dict(checkpoint_loads=1,
            checkpoint_loaded_parameters=source_model['nonzero_weights']),
        load_seconds=max(0., model.last_load_seconds-model.setup_seconds))


def checkpoint(model, life, query, phase, method, label, transitions,
        model_ref, folder, directory, stream, reuse=None):
    result = dict(label=label, transitions=transitions, updates=model.updates,
        model_ref=model_ref, model_origin='v122' if not Path(model_ref).is_absolute() else 'source')
    if method == 'BANK':
        result['bank_manifest'] = model.to_payload()
        if label:
            checkpoint_folder = folder / f'checkpoint_{label}'; checkpoint_folder.mkdir()
            before, started = dict(model.counts), perf_counter()
            manifest = model.save(checkpoint_folder)
            for entry in manifest['model_files']:
                entry['path'] = str(Path(entry['path']).relative_to(directory))
            result.update(model_ref=str((checkpoint_folder / 'manifest.json').relative_to(directory)),
                model_origin='v122', model_bytes=sum(entry['bytes'] for entry in manifest['model_files']),
                save_seconds=perf_counter()-started, save_counts=counter_delta(model.counts, before),
                bank_manifest=manifest)
            save(checkpoint_folder / 'manifest.json', manifest)
    result['evaluations'] = evaluate(model, life, query, phase, method, label, stream, reuse)
    return result


def train_phase(model, life, query, phase, result, folder, directory,
        train_stream, control_stream, persist):
    transitions, episode, next_checkpoint = 0, 0, 1
    block = empty_block(0, 0)
    while transitions < TRAIN_TRANSITIONS:
        row, raw = td_game(model, life, query, phase, 'BANK', episode=episode,
            transitions_before=transitions, max_steps=min(MAX_STEPS, TRAIN_TRANSITIONS-transitions))
        if row['result']['steps'] <= 0:
            raise AssertionError('Supported fresh 2048 game must perform an action')
        append(train_stream, raw); add_training(block, row)
        block.setdefault('setup_counts', Counter()).update(row['result']['setup_counts'])
        block['setup_seconds'] = block.get('setup_seconds', 0.) + row['result']['setup_seconds']
        transitions, episode = row['transitions_after'], episode+1
        crossed = transitions >= CHECKPOINTS[next_checkpoint]
        if episode % BLOCK_EPISODES == 0 or crossed:
            train_stream.flush(); result['training_blocks'].append(block)
            block = empty_block(episode, transitions)
            if crossed:
                result['checkpoints'].append(checkpoint(model, life, query, phase, 'BANK',
                    CHECKPOINTS[next_checkpoint], transitions, result['checkpoints'][-1]['model_ref'],
                    folder, directory, control_stream))
                next_checkpoint += 1
            persist()
            print(json.dumps(dict(event='training_block_complete', life=life, query=query,
                phase=phase, method='BANK', transitions=transitions, episodes=episode,
                updates=model.updates, banks=len(model.banks))), flush=True)
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
        rule, source_model = LearnedDynamics.from_payload(source['rule']), source['models'][query]
        result = dict(training_trace=str((query_folder / 'training.jsonl.gz').relative_to(directory)),
            control_trace=str((query_folder / 'control.jsonl.gz').relative_to(directory)),
            model_setup=[], phases={})
        lifecycle['queries'][query] = result
        frozen, setup = make_model(rule, build_dir, 'FROZEN_A', 'B', source_model)
        result['model_setup'].append(setup)
        initial, setup = make_model(rule, build_dir, 'BANK', 'B', source_model)
        result['model_setup'].append(setup)
        context_started = perf_counter()
        bank = ContextValueBank(initial, source['initial_ranks'][query], build_dir)
        result['context_initialization'] = dict(seconds=perf_counter()-context_started,
            counts=dict(bank.router.counts), source=source['initial_rank_sources'][query],
            router=bank.router.to_payload())
        bank_ref = source_model['path']
        with gzip.open(directory / result['training_trace'], 'wt') as train_stream, \
                gzip.open(directory / result['control_trace'], 'wt') as control_stream:
            for phase, p_four in PHASES.items():
                phase_folder = query_folder / phase; phase_folder.mkdir()
                phase_result = dict(p_four=p_four, methods={})
                result['phases'][phase] = phase_result
                frozen_zero = checkpoint(frozen, source['life'], query, phase, 'FROZEN_A',
                    0, 0, source_model['path'], phase_folder, directory, control_stream)
                phase_result['methods']['FROZEN_A'] = dict(checkpoints=[frozen_zero])
                continued = dict(checkpoints=[], training_reused_from=str(SOURCE), training_blocks=[])
                phase_result['methods']['CONT'] = continued
                for source_cp in source['continued'][query][phase]:
                    if phase == 'B' and source_cp['label'] == 0:
                        actor, reuse = frozen, frozen_zero['evaluations']
                    else:
                        actor, setup = make_model(rule, build_dir, 'CONT', phase, source_cp)
                        result['model_setup'].append(setup); reuse = None
                    continued['checkpoints'].append(checkpoint(actor, source['life'], query, phase,
                        'CONT', source_cp['label'], source_cp['transitions'], source_cp['path'],
                        phase_folder, directory, control_stream, reuse))
                    if actor is not frozen:
                        del actor
                bank_folder = phase_folder / 'BANK'; bank_folder.mkdir()
                bank_result = dict(training_blocks=[], checkpoints=[])
                phase_result['methods']['BANK'] = bank_result
                bank_result['checkpoints'].append(checkpoint(bank, source['life'], query, phase,
                    'BANK', 0, 0, bank_ref, bank_folder, directory, control_stream))
                persist()
                train_phase(bank, source['life'], query, phase, bank_result, bank_folder,
                    directory, train_stream, control_stream, persist)
                bank_ref = bank_result['checkpoints'][-1]['model_ref']
        del initial, frozen, bank
    lifecycle['seconds'] = perf_counter()-started; persist()
    return lifecycle


def run(directory):
    started = perf_counter(); directory.mkdir(parents=True, exist_ok=False)
    capsule = extract_source(json.loads((SOURCE / 'run.json').read_text()),
        json.loads((SOURCE / 'source_capsule.json').read_text()))
    save(directory / 'source_capsule.json', capsule); snapshot(directory)
    result = dict(schema='acfqp.context_bank.v122.run', status='running',
        settings=dict(lifecycles=list(LIVES), queries=QUERIES, phases=PHASES,
            checkpoints=list(CHECKPOINTS), train_transitions=TRAIN_TRANSITIONS,
            replicas=REPLICAS, max_steps=MAX_STEPS, workers=WORKERS, alpha=ALPHA,
            block_episodes=BLOCK_EPISODES, version_base=BASE,
            training_seed_version=121, context_initial_ranks=256, router_method='LIBRARY'),
        inherited_costs=capsule['inherited_costs'], lifecycles=[],
        executable=sys.executable, platform=platform.platform())
    save(directory / 'run.json', result)
    with ProcessPoolExecutor(max_workers=WORKERS) as pool:
        tasks = [pool.submit(lifecycle_run, source, directory) for source in capsule['snapshots']]
        for future in as_completed(tasks):
            result['lifecycles'].append(future.result())
            result['lifecycles'].sort(key=lambda row: row['life']); save(directory / 'run.json', result)
    result.update(status='complete', seconds=perf_counter()-started)
    save(directory / 'run.json', result)
    print(json.dumps(dict(status='complete', seconds=result['seconds'])), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    run(parser.parse_args().output)
