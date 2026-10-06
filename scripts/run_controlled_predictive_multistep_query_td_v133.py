"""Compare fixed 32-step and original one-step query TD on new streams."""
import argparse
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
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT/'src'))
from scripts.run_controlled_predictive_policy_consequences_v126 import (
    POLICIES, QUERIES as ALL_QUERIES, save, append, compact_trace, counter_delta, result)
from scripts.run_controlled_predictive_paired_ntuple_v130 import load_parent
from acfqp.science.controlled_predictive_regime_experience_v115 import run_episode
from acfqp.science.controlled_predictive_online_query_td_v131 import QueryTD, TDStream
from acfqp.science.controlled_predictive_multistep_query_td_v133 import MultiStepTDStream

SOURCE = ROOT/'reports/controlled_predictive_td_attribution_v132'
QUERIES = {q: ALL_QUERIES[q] for q in ('risk1', 'risk8')}
PARENTS = dict(risk1='reward', risk8='risk_goal')
LIVES, KINDS, CHECKPOINTS = (0, 1, 2, 3), ('SINGLE', 'MULTI'), (0, 32768, 131072, 524288)
REPLICAS, MAX_STEPS, WORKERS, ALPHA, BASE = 16, 2000, 4, .0025, 133*100000000
HORIZON = 32


def settings():
    return dict(lifecycles=list(LIVES), policies=POLICIES, queries=QUERIES, parents=PARENTS,
        kinds=list(KINDS), checkpoints=list(CHECKPOINTS), transitions_per_learner=CHECKPOINTS[-1],
        replicas=REPLICAS, max_steps=MAX_STEPS, workers=WORKERS, alpha=ALPHA, p_four=.1,
        version_base=BASE, horizon=HORIZON, physical_control_games=896, logical_control_rows=1536)


def train_seed(life, query, episode):
    return BASE+10000000+life*1000000+list(QUERIES).index(query)*500000+episode


def evaluation_seed(life, replica):
    return BASE+90000000+life*100000+replica


def extract_source(previous, analysis):
    if not analysis['complete']: raise ValueError('V132 must be complete')
    return dict(schema='acfqp.multistep_query_td.v133.source',
        snapshots=[{k: deepcopy(r[k]) for k in ('life', 'rule', 'models', 'counts')}
                   for r in previous['snapshots']],
        inherited_costs=dict(**deepcopy(previous['inherited_costs']), v132_experiment=deepcopy(analysis['costs'])),
        required_inputs=dict(SINGLE='identified dynamics, V120 source value, V127 global constant',
            PARENT='identified dynamics, V120 source value, V127 global constant',
            MULTI='identified dynamics, V120 source value, V127 global constant'),
        scope='Historical work is separate; V131 trained parameters and V132 evaluation outcomes are not learning inputs.')


def model_state(model, parent=False):
    if parent:
        return dict(updates=model.updates, readonly=not model.source.weights.flags.writeable)
    return dict(updates=model.updates, readonly=not model.weights.flags.writeable,
        kind=model.kind, offset=model.offset)


def stream_state(stream, kind):
    state = dict(transitions=stream.transitions, episodes_started=stream.episodes_started,
        episodes_completed=stream.episodes_completed, episode=stream.episode, step=stream.step,
        board=None if stream.board is None else list(stream.board),
        pending=None if stream.pending is None else list(stream.pending),
        environment_counts=dict(stream.environment_counts))
    if kind == 'MULTI':
        state.update(queue=stream.queue_state(), target_counts=dict(stream.target_counts))
    return state


def train_lifecycle(source, directory):
    started = perf_counter(); life = source['life']; folder = directory/f'life_{life}'; folder.mkdir()
    data = dict(life=life, queries={})
    for query in QUERIES:
        parent, loads = load_parent(source, query, folder)
        qdata = dict(loads=loads, parent_before=model_state(parent, True), learners={})
        data['queries'][query] = qdata
        for kind in KINDS:
            model = QueryTD(parent, 'PRIOR', folder/'build')
            initialization = dict(setup_counts=dict(model.setup_counts), setup_seconds=model.setup_seconds,
                counts=dict(model.counts), state=model_state(model))
            seed_fn = lambda episode: train_seed(life, query, episode)
            stream = (TDStream(model, seed_fn, MAX_STEPS, .1) if kind == 'SINGLE' else
                MultiStepTDStream(model, seed_fn, horizon=HORIZON, max_steps=MAX_STEPS, p_four=.1))
            name = f'{query}_{kind}'; trace = str((folder/f'{name}_training.jsonl.gz').relative_to(directory))
            learner = dict(initialization=initialization, training_trace=trace, checkpoints=[])
            qdata['learners'][kind] = learner
            with gzip.open(directory/trace, 'wt') as output:
                for age in CHECKPOINTS:
                    for segment in stream.advance_to(age):
                        append(output, dict(life=life, query=query, kind=kind, checkpoint=age, **segment))
                    output.flush()
                    before = dict(model.counts); metadata = model.save(folder/f'{name}_{age}.npz')
                    checkpoint = dict(age=age, model_ref=str((folder/f'{name}_{age}.npz').relative_to(directory)),
                        metadata=metadata, save_counts=counter_delta(model.counts, before),
                        transitions=stream.transitions, updates=model.updates, stream_state=stream_state(stream, kind))
                    learner['checkpoints'].append(checkpoint)
                    save(folder/'lifecycle.json', data)
                    print(json.dumps(dict(event='checkpoint_saved', life=life, query=query, kind=kind,
                        age=age, updates=model.updates, episodes=stream.episodes_completed)), flush=True)
            model.freeze()
            learner.update(final_stream_state=stream_state(stream, kind), final_state=model_state(model),
                final_counts=dict(model.counts))
        qdata['parent_after'] = model_state(parent, True)
    data['seconds'] = perf_counter()-started; save(folder/'lifecycle.json', data); return data


def full_game(model, life, query, method, checkpoint, replica, zeros=None):
    before = model_state(model, method == 'PARENT'); previous = dict(model.counts)
    zeros = {} if zeros is None else zeros
    zero_before = {kind: dict(item.counts) for kind, item in zeros.items()}
    zero_state = {kind: model_state(item) for kind, item in zeros.items()}
    values = []
    def act(board, step):
        choice = model.choose(board, QUERIES[query]); values.append(choice['value'])
        for kind, item in zeros.items():
            check = item.choose(board, QUERIES[query])
            same = check['action'] == choice['action'] and {
                a: (r['afterstate'], r['score'], r['value']) for a, r in choice['action_values'].items()} == {
                a: (r['afterstate'], r['score'], r['value']) for a, r in check['action_values'].items()}
            if not same: raise AssertionError(f'zero-training {kind} differs from PARENT')
        return choice['action']
    game = run_episode(evaluation_seed(life, replica), act, .1, MAX_STEPS)
    row = dict(life=life, query=query, method=method, checkpoint=checkpoint, replica=replica,
        seed=game['seed'], result=result(game, query, policy_counts=counter_delta(model.counts, previous)),
        **compact_trace(game), chosen_values=values)
    row['result'].update(model_state_before=before, model_state_after=model_state(model, method == 'PARENT'))
    if zeros:
        row['zero_equivalence'] = {kind: dict(exact=True, before=zero_state[kind],
            after=model_state(item), counts=counter_delta(item.counts, zero_before[kind]))
            for kind, item in zeros.items()}
    return row


def evaluate_lifecycle(source, trained, directory):
    started = perf_counter(); life = source['life']; folder = directory/f'eval_{life}'; folder.mkdir()
    trace = str((folder/'control.jsonl.gz').relative_to(directory)); queries = {}
    with gzip.open(directory/trace, 'wt') as output:
        for query in QUERIES:
            parent, loads = load_parent(source, query, folder)
            qdata = dict(loads=loads, parent_before=model_state(parent, True), checkpoint_loads=[])
            queries[query] = qdata
            def load(kind, checkpoint):
                model = QueryTD.load(directory/checkpoint['model_ref'], parent, folder/'build'); model.freeze()
                qdata['checkpoint_loads'].append(dict(kind=kind, age=checkpoint['age'], setup_counts=dict(model.setup_counts),
                    setup_seconds=model.setup_seconds, load_counts=dict(model.load_counts),
                    load_seconds=model.last_load_seconds, state=model_state(model)))
                return model
            zeros = {kind: load(kind, trained['queries'][query]['learners'][kind]['checkpoints'][0]) for kind in KINDS}
            for replica in range(REPLICAS):
                append(output, full_game(parent, life, query, 'PARENT', 0, replica, zeros=zeros))
            output.flush(); del zeros
            for kind in KINDS:
                for checkpoint in trained['queries'][query]['learners'][kind]['checkpoints'][1:]:
                    age = checkpoint['age']; model = load(kind, checkpoint)
                    for replica in range(REPLICAS):
                        append(output, full_game(model, life, query, kind, age, replica))
                    output.flush()
                    print(json.dumps(dict(event='control_complete', life=life, query=query, kind=kind, age=age)), flush=True)
            qdata['parent_after'] = model_state(parent, True)
    data = dict(life=life, control_trace=trace, queries=queries, seconds=perf_counter()-started)
    save(folder/'lifecycle.json', data); return data


def snapshot_code(directory):
    importlib.import_module('scripts.analyze_controlled_predictive_multistep_query_td_v133')
    files = {Path(__file__).resolve(), ROOT/'specs/MULTISTEP_QUERY_TD_V133.md'}
    for module in list(sys.modules.values()):
        filename = getattr(module, '__file__', None)
        if filename:
            path = Path(filename).resolve()
            if path.is_relative_to(ROOT/'src') or path.is_relative_to(ROOT/'scripts'): files.add(path)
    files.add(ROOT/'src/acfqp/science/controlled_predictive_ntuple_kernel_v120.cpp')
    files.update((ROOT/'tests').glob('*multistep_query_td*v133.py'))
    for path in files:
        target = directory/'source'/path.relative_to(ROOT); target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)


def run(directory):
    directory = directory.resolve(); started = perf_counter(); directory.mkdir(parents=True, exist_ok=False)
    source = extract_source(json.loads((SOURCE/'source_capsule.json').read_text()), json.loads((SOURCE/'analysis.json').read_text()))
    save(directory/'source_capsule.json', source); snapshot_code(directory)
    data = dict(schema='acfqp.multistep_query_td.v133.run', status='training', settings=settings(),
        inherited_costs=source['inherited_costs'], lifecycles=[], eval_lifecycles=[],
        executable=sys.executable, platform=platform.platform())
    save(directory/'run.json', data)
    with ProcessPoolExecutor(max_workers=WORKERS) as pool:
        tasks = [pool.submit(train_lifecycle, s, directory) for s in source['snapshots']]
        for future in as_completed(tasks):
            data['lifecycles'].append(future.result()); data['lifecycles'].sort(key=lambda r: r['life'])
            save(directory/'run.json', data)
        data['status'] = 'frozen'; save(directory/'frozen_training.json', deepcopy(data)); save(directory/'run.json', data)
        print(json.dumps(dict(event='all_training_frozen')), flush=True)
        trained = {r['life']: r for r in data['lifecycles']}; data['status'] = 'evaluation'; save(directory/'run.json', data)
        tasks = [pool.submit(evaluate_lifecycle, s, trained[s['life']], directory) for s in source['snapshots']]
        for future in as_completed(tasks):
            data['eval_lifecycles'].append(future.result()); data['eval_lifecycles'].sort(key=lambda r: r['life'])
            save(directory/'run.json', data)
    data.update(status='complete', seconds=perf_counter()-started); save(directory/'run.json', data)
    print(json.dumps(dict(status='complete', seconds=data['seconds'])), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'reports/controlled_predictive_multistep_query_td_v133')
    run(parser.parse_args().output)
