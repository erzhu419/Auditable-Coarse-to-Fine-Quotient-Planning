"""Learn joint Bellman consequences under fixed H2 policies and reuse queries."""
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
    POLICIES, save, append, compact_trace, counter_delta)
from scripts.run_controlled_predictive_paired_ntuple_v130 import load_parent
from scripts.run_controlled_predictive_contextual_ntuple_v134 import model_state as leaf_state
from acfqp.science.controlled_predictive_regime_experience_v115 import run_episode
from acfqp.science.controlled_predictive_online_query_td_v131 import QueryTD
from acfqp.science.controlled_predictive_contextual_ntuple_v134 import ConditionalQueryTD
from acfqp.science.controlled_predictive_frozen_leaf_planning_v135 import FrozenLeafPlanner
from acfqp.science.controlled_predictive_bellman_consequences_v136 import PolicyComponents, TeacherTDStream

SOURCE = ROOT/'reports/controlled_predictive_frozen_leaf_planning_v135'
LIVES, REPRESENTATIONS, TEACHER_QUERIES = (0, 1, 2, 3), ('SINGLE', 'CAPACITY'), ('risk1', 'risk8')
QUERIES = {f'risk{weight}': dict(reward_weight=1., failure_penalty=float(weight), goal_bonus=float(weight))
    for weight in (1, 2, 6, 8)}
METHODS, CHECKPOINTS = ('TEACHER', 'INITIAL_H2', 'LEARNED_H2'), (0, 524288)
REPLICAS, MAX_STEPS, WORKERS, RATE, BASE = 16, 2000, 4, .0025, 136*100000000


def evaluation_queries(teacher_query):
    return (teacher_query, 'risk2', 'risk6')


def settings():
    return dict(lifecycles=list(LIVES), representations=list(REPRESENTATIONS),
        teacher_queries=list(TEACHER_QUERIES), queries=QUERIES, methods=list(METHODS),
        checkpoints=list(CHECKPOINTS), transitions_per_teacher=CHECKPOINTS[-1],
        replicas=REPLICAS, max_steps=MAX_STEPS, workers=WORKERS, alpha=RATE,
        initial_success=.5, p_four=.1, planner_spawn_law='frozen_identified_distribution',
        version_base=BASE, physical_control_games=1536, logical_control_rows=2304)


def train_seed(life, representation, teacher_query, episode):
    return BASE+10000000+life*2000000+REPRESENTATIONS.index(representation)*1000000+TEACHER_QUERIES.index(teacher_query)*500000+episode


def evaluation_seed(life, replica):
    return BASE+90000000+life*100000+replica


def extract_source(previous, analysis):
    if not (analysis['complete'] and analysis['primary_complete']):
        raise ValueError('V135 must be complete')
    return dict(schema='acfqp.bellman_consequences.v136.source',
        snapshots=[{k: deepcopy(row[k]) for k in ('life', 'rule', 'models', 'counts', 'leaves')}
            for row in previous['snapshots']],
        inherited_costs=dict(**deepcopy(previous['inherited_costs']), v135_experiment=deepcopy(analysis['costs'])),
        required_inputs='V134 final scalar leaves, V135 frozen H2 behavior, identified dynamics, fixed success prior .5',
        scope='Evaluation data are not fitted; each policy-conditioned pair is learned from its new frozen-teacher training stream.')


def component_state(model):
    return dict(updates=model.updates, readonly=not model.weights.flags.writeable,
        parameter_count=int(model.weights.size))


def stream_state(stream):
    return dict(transitions=stream.transitions, episodes_started=stream.episodes_started,
        episodes_completed=stream.episodes_completed, episode=stream.episode, step=stream.step,
        board=None if stream.board is None else list(stream.board),
        pending=None if stream.pending is None else list(stream.pending),
        environment_counts=dict(stream.environment_counts))


def load_teacher(source, representation, teacher_query, folder):
    parent, parent_load = load_parent(source, teacher_query, folder)
    reference = source['leaves'][teacher_query][representation]
    model_class = QueryTD if representation == 'SINGLE' else ConditionalQueryTD
    leaf = model_class.load(reference['model_ref'], parent, folder/'build'); leaf.freeze()
    teacher = FrozenLeafPlanner(leaf, depth=2, build_dir=folder/'build')
    loads = dict(reference=deepcopy(reference), parent=parent_load,
        leaf=dict(setup_counts=dict(leaf.setup_counts), setup_seconds=leaf.setup_seconds,
            load_counts=dict(leaf.load_counts), load_seconds=leaf.last_load_seconds, state=leaf_state(leaf)),
        teacher=dict(setup_counts=dict(teacher.setup_counts), setup_seconds=teacher.setup_seconds,
            spawn_probabilities=list(teacher.spawn_probabilities)))
    return parent, leaf, teacher, loads


def train_lifecycle(source, directory):
    started = perf_counter(); life = source['life']; folder = directory/f'train_{life}'; folder.mkdir()
    data = dict(life=life, representations={})
    for representation in REPRESENTATIONS:
        teachers = {}; data['representations'][representation] = teachers
        for teacher_query in TEACHER_QUERIES:
            parent, leaf, teacher, loads = load_teacher(source, representation, teacher_query, folder)
            model = PolicyComponents(leaf, folder/'build')
            stream = TeacherTDStream(model, teacher,
                lambda episode: train_seed(life, representation, teacher_query, episode), MAX_STEPS, .1)
            trace = str((folder/f'{representation}_{teacher_query}_training.jsonl.gz').relative_to(directory))
            row = dict(loads=loads, parent_before=leaf_state(parent, True), teacher_before=leaf_state(leaf),
                initialization=dict(state=component_state(model), counts=dict(model.counts),
                    setup_counts=dict(model.setup_counts), setup_seconds=model.setup_seconds),
                training_trace=trace, checkpoints=[])
            teachers[teacher_query] = row
            with gzip.open(directory/trace, 'wt') as output:
                for age in CHECKPOINTS:
                    for segment in stream.advance_to(age):
                        append(output, dict(life=life, representation=representation, teacher_query=teacher_query,
                            checkpoint=age, **segment))
                    output.flush()
                    before = dict(model.counts); path = folder/f'{representation}_{teacher_query}_{age}.npz'
                    metadata = model.save(path)
                    row['checkpoints'].append(dict(age=age, model_ref=str(path.relative_to(directory)),
                        metadata=metadata, save_counts=counter_delta(model.counts, before),
                        updates=model.updates, stream_state=stream_state(stream)))
                    save(folder/'lifecycle.json', data)
                    print(json.dumps(dict(event='checkpoint_saved', life=life, representation=representation,
                        teacher_query=teacher_query, age=age, updates=model.updates)), flush=True)
            model.freeze()
            row.update(final_state=component_state(model), final_counts=dict(model.counts),
                final_stream_state=stream_state(stream), teacher_counts=dict(teacher.counts),
                teacher_after=leaf_state(leaf), parent_after=leaf_state(parent, True))
    data['seconds'] = perf_counter()-started; save(folder/'lifecycle.json', data); return data


def game_result(game, query, policy_counts, decision_seconds):
    q = QUERIES[query]
    components = [game['return_score']/2048., float(game['status']=='LOST'), float(game['status']=='WON')]
    return dict(score=game['return_score'], status=game['status'], steps=game['steps_count'],
        components=components, utility=components[0]-q['failure_penalty']*components[1]+q['goal_bonus']*components[2],
        environment_counts=game['work'], policy_counts=policy_counts, learning_counts={},
        seconds=game['seconds'], decision_seconds=decision_seconds)


def prediction_diagnostic(game, initial, final):
    models = dict(INITIAL_H2=initial, LEARNED_H2=final)
    result = dict(predictions={}, counts={}, before={}, after={})
    for name, model in models.items():
        before = dict(model.counts); result['before'][name] = component_state(model)
        result['predictions'][name] = []
        for step in game['steps']:
            if max(step['afterstate']) >= model.radix: continue
            prediction = model.value(step['afterstate'])
            result['predictions'][name].append({key: prediction[key] for key in ('reward', 'success')})
        result['counts'][name] = counter_delta(model.counts, before)
        result['after'][name] = component_state(model)
    return result


def full_game(actor, source_leaf, life, representation, teacher_query, query, method, replica,
              initial=None, final=None):
    is_teacher = method == 'TEACHER'
    state = lambda: leaf_state(source_leaf) if is_teacher else component_state(actor)
    before, counts_before = state(), dict(actor.counts)
    zero_counts = dict(initial.counts) if is_teacher else None
    zero_state = component_state(initial) if is_teacher else None
    values, alternatives, seconds = [], [], 0.
    def act(board, step):
        nonlocal seconds
        started = perf_counter()
        choice = actor.choose(board, QUERIES[teacher_query]) if is_teacher else actor.choose(board, QUERIES[query], depth=2)
        seconds += perf_counter()-started
        fields = ('score', 'value', 'tail_value') if is_teacher else ('score', 'value', 'tail_value', 'consequences')
        values.append(choice['value'])
        alternatives.append({a: {k: value[k] for k in fields} for a, value in choice['action_values'].items()})
        if is_teacher:
            zero = initial.choose(board, QUERIES[teacher_query], depth=2)
            if zero['action'] != choice['action'] or {
                a: (x['afterstate'], x['score'], x['value']) for a, x in zero['action_values'].items()} != {
                a: (x['afterstate'], x['score'], x['value']) for a, x in choice['action_values'].items()}:
                raise AssertionError('zero own-query H2 differs from its frozen teacher')
        return choice['action']
    game = run_episode(evaluation_seed(life, replica), act, .1, MAX_STEPS)
    row = dict(life=life, representation=representation, teacher_query=teacher_query, query=query,
        method=method, replica=replica, seed=game['seed'],
        result=game_result(game, query, counter_delta(actor.counts, counts_before), seconds),
        **compact_trace(game), chosen_values=values, action_values=alternatives)
    row['result'].update(model_state_before=before, model_state_after=state())
    if is_teacher:
        row['zero_equivalence'] = dict(exact=True, before=zero_state, after=component_state(initial),
            counts=counter_delta(initial.counts, zero_counts))
        row['diagnostic'] = prediction_diagnostic(game, initial, final)
    return row


def evaluate_lifecycle(source, trained, directory):
    started = perf_counter(); life = source['life']; folder = directory/f'eval_{life}'; folder.mkdir()
    trace = str((folder/'control.jsonl.gz').relative_to(directory)); representations = {}
    with gzip.open(directory/trace, 'wt') as output:
        for representation in REPRESENTATIONS:
            teachers = {}; representations[representation] = teachers
            for teacher_query in TEACHER_QUERIES:
                parent, leaf, teacher, loads = load_teacher(source, representation, teacher_query, folder)
                checkpoints = trained['representations'][representation][teacher_query]['checkpoints']
                models, model_loads = {}, []
                for method, checkpoint in zip(('INITIAL_H2', 'LEARNED_H2'), checkpoints):
                    model = PolicyComponents.load(directory/checkpoint['model_ref'], leaf, folder/'build'); model.freeze()
                    models[method] = model
                    model_loads.append(dict(method=method, age=checkpoint['age'], model_ref=checkpoint['model_ref'],
                        state=component_state(model), setup_counts=dict(model.setup_counts), setup_seconds=model.setup_seconds,
                        load_counts=dict(model.load_counts), load_seconds=model.last_load_seconds))
                row = dict(loads=loads, model_loads=model_loads, parent_before=leaf_state(parent, True),
                    teacher_before=leaf_state(leaf))
                teachers[teacher_query] = row
                for replica in range(REPLICAS):
                    append(output, full_game(teacher, leaf, life, representation, teacher_query, teacher_query,
                        'TEACHER', replica, initial=models['INITIAL_H2'], final=models['LEARNED_H2']))
                output.flush()
                for method, model in models.items():
                    queries = evaluation_queries(teacher_query)[1:] if method == 'INITIAL_H2' else evaluation_queries(teacher_query)
                    for query in queries:
                        for replica in range(REPLICAS):
                            append(output, full_game(model, leaf, life, representation, teacher_query, query, method, replica))
                        output.flush()
                        print(json.dumps(dict(event='control_complete', life=life, representation=representation,
                            teacher_query=teacher_query, query=query, method=method)), flush=True)
                row.update(parent_after=leaf_state(parent, True), teacher_after=leaf_state(leaf),
                    teacher_counts=dict(teacher.counts),
                    final_model_states={method: component_state(model) for method, model in models.items()})
    data = dict(life=life, control_trace=trace, representations=representations, seconds=perf_counter()-started)
    save(folder/'lifecycle.json', data); return data


def snapshot_code(directory):
    importlib.import_module('scripts.analyze_controlled_predictive_bellman_consequences_v136')
    files = {Path(__file__).resolve(), ROOT/'specs/BELLMAN_CONSEQUENCES_V136.md'}
    for module in list(sys.modules.values()):
        filename = getattr(module, '__file__', None)
        if filename:
            path = Path(filename).resolve()
            if path.is_relative_to(ROOT/'src') or path.is_relative_to(ROOT/'scripts'): files.add(path)
    for name in ('controlled_predictive_ntuple_kernel_v120.cpp', 'controlled_predictive_contextual_ntuple_v134.cpp',
                 'controlled_predictive_frozen_leaf_planning_v135.cpp', 'controlled_predictive_bellman_consequences_v136.cpp'):
        files.add(ROOT/'src/acfqp/science'/name)
    files.update((ROOT/'tests').glob('*bellman_consequences*v136.py'))
    for path in files:
        target = directory/'source'/path.relative_to(ROOT); target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)


def run(directory):
    directory = directory.resolve(); started = perf_counter(); directory.mkdir(parents=True, exist_ok=False)
    read = lambda name: json.loads((SOURCE/name).read_text())
    source = extract_source(read('source_capsule.json'), read('analysis.json'))
    save(directory/'source_capsule.json', source); snapshot_code(directory)
    data = dict(schema='acfqp.bellman_consequences.v136.run', status='training', settings=settings(),
        inherited_costs=source['inherited_costs'], lifecycles=[], eval_lifecycles=[],
        executable=sys.executable, platform=platform.platform())
    save(directory/'run.json', data)
    with ProcessPoolExecutor(max_workers=WORKERS) as pool:
        for future in as_completed([pool.submit(train_lifecycle, s, directory) for s in source['snapshots']]):
            data['lifecycles'].append(future.result()); data['lifecycles'].sort(key=lambda r: r['life'])
            save(directory/'run.json', data)
        data['status'] = 'frozen'; save(directory/'frozen_training.json', deepcopy(data)); save(directory/'run.json', data)
        print(json.dumps(dict(event='all_training_frozen')), flush=True)
        trained = {row['life']: row for row in data['lifecycles']}; data['status'] = 'evaluation'
        save(directory/'run.json', data)
        tasks = [pool.submit(evaluate_lifecycle, s, trained[s['life']], directory) for s in source['snapshots']]
        for future in as_completed(tasks):
            data['eval_lifecycles'].append(future.result()); data['eval_lifecycles'].sort(key=lambda r: r['life'])
            save(directory/'run.json', data)
    data.update(status='complete', seconds=perf_counter()-started); save(directory/'run.json', data)
    print(json.dumps(dict(status='complete', seconds=data['seconds'])), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'reports/controlled_predictive_bellman_consequences_v136')
    run(parser.parse_args().output)
