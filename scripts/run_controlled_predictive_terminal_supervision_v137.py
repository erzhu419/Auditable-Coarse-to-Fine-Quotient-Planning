"""Compare terminal supervision and exact one-step replay on retained teachers."""
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
from scripts import run_controlled_predictive_bellman_consequences_v136 as previous
from acfqp.science.controlled_predictive_terminal_supervision_v137 import replay_episode

SOURCE = ROOT/'reports/controlled_predictive_bellman_consequences_v136'
LIVES, REPRESENTATIONS, TEACHER_QUERIES = previous.LIVES, previous.REPRESENTATIONS, previous.TEACHER_QUERIES
QUERIES = {key: previous.QUERIES[key] for key in TEACHER_QUERIES}
ARMS, METHODS = ('TD', 'TERMINAL'), ('TEACHER', 'INITIAL_H2', 'TD', 'TERMINAL')
REPLICAS, MAX_STEPS, WORKERS, BASE = 16, 2000, 4, 137*100000000
save, append, counter_delta = previous.save, previous.append, previous.counter_delta
component_state, leaf_state = previous.component_state, previous.leaf_state


def settings():
    return dict(lifecycles=list(LIVES), representations=list(REPRESENTATIONS),
        teacher_queries=list(TEACHER_QUERIES), queries=QUERIES, arms=list(ARMS),
        methods=list(METHODS), replicas=REPLICAS, max_steps=MAX_STEPS, workers=WORKERS,
        alpha=.0025, passes=1, episode_order='retained_chronological',
        eligible_statuses=['WON', 'LOST'], initial_success=.5, p_four=.1,
        planner_spawn_law='frozen_identified_distribution', version_base=BASE,
        physical_control_games=768, logical_control_rows=1024)


def evaluation_seed(life, replica):
    return BASE+90000000+life*100000+replica


def read_rows(path):
    with gzip.open(path, 'rt') as stream:
        for line in stream:
            yield json.loads(line)


def extract_source(capsule, run, analysis):
    if not (run['status'] == 'complete' and analysis['complete'] and analysis['primary_complete']):
        raise ValueError('V136 must be complete')
    if analysis['costs']['training']['statuses'].get('CUTOFF', 0):
        raise ValueError('V137 requires the observed complete-prefix source, without interleaved cutoffs')
    snapshots = deepcopy(capsule['snapshots'])
    lifecycles = {row['life']: row for row in run['lifecycles']}
    inspected = {(r['life'],r['representation'],r['teacher_query']): r for r in analysis['learners']}
    for source in snapshots:
        source['training_sources'] = {}
        for rep in REPRESENTATIONS:
            source['training_sources'][rep] = {}
            for teacher in TEACHER_QUERIES:
                old = lifecycles[source['life']]['representations'][rep][teacher]
                summary = inspected[(source['life'],rep,teacher)]
                source['training_sources'][rep][teacher] = dict(
                    training_trace=str((SOURCE/old['training_trace']).resolve()),
                    source_transitions=summary['cost']['environment_counts']['sampled_transitions'],
                    source_statuses=deepcopy(summary['cost']['statuses']),
                    source_updates=summary['updates'])
    return dict(schema='acfqp.terminal_supervision.v137.source', snapshots=snapshots,
        inherited_costs=dict(**deepcopy(capsule['inherited_costs']), v136_experiment=deepcopy(analysis['costs'])),
        required_inputs='V134 scalar leaves and V136 retained training trajectories only',
        scope='V136 evaluation predictions and outcomes are never fitting inputs.')


def train_lifecycle(source, directory):
    started = perf_counter(); life = source['life']; folder = directory/f'train_{life}'; folder.mkdir()
    data = dict(life=life, representations={})
    for rep in REPRESENTATIONS:
        data['representations'][rep] = {}
        for teacher in TEACHER_QUERIES:
            parent, leaf, frozen_teacher, loads = previous.load_teacher(source, rep, teacher, folder)
            models = {arm: previous.PolicyComponents(leaf, folder/'build') for arm in ARMS}
            source_ref = source['training_sources'][rep][teacher]
            row = dict(source_ref=deepcopy(source_ref), loads=loads,
                parent_before=leaf_state(parent, True), teacher_before=leaf_state(leaf),
                methods={}, source_counts=dict(episodes=0, transitions=0, eligible_episodes=0,
                    eligible_transitions=0, eligible_updates=0, excluded_episodes=0, excluded_transitions=0),
                excluded=[])
            data['representations'][rep][teacher] = row
            streams = {}
            for arm, model in models.items():
                trace = str((folder/f'{rep}_{teacher}_{arm}.jsonl.gz').relative_to(directory))
                streams[arm] = gzip.open(directory/trace, 'wt')
                row['methods'][arm] = dict(training_trace=trace,
                    initialization=dict(state=component_state(model), counts=dict(model.counts),
                        setup_counts=dict(model.setup_counts), setup_seconds=model.setup_seconds))
            excluded = False
            try:
                for record in read_rows(source_ref['training_trace']):
                    count = len(record['actions']); counts = row['source_counts']
                    counts['episodes'] += 1; counts['transitions'] += count
                    if record['status'] not in ('WON', 'LOST'):
                        if record['status'] != 'ACTIVE' or excluded:
                            raise ValueError('source differs from its retained complete-prefix roster')
                        excluded = True; counts['excluded_episodes'] += 1; counts['excluded_transitions'] += count
                        row['excluded'].append({k: record[k] for k in ('episode','seed','status','start_step','end_step')})
                        continue
                    if excluded:
                        raise ValueError('complete episode follows excluded prefix')
                    counts['eligible_episodes'] += 1; counts['eligible_transitions'] += count
                    counts['eligible_updates'] += count-int(record['status'] == 'WON')
                    for arm, model in models.items():
                        replay = replay_episode(model, record, arm)
                        append(streams[arm], dict(life=life, representation=rep, teacher_query=teacher, **replay))
                        if arm == 'TD' and replay['td_source_comparison']['mismatches']:
                            raise AssertionError('TD replay differs from retained V136 numerical history')
            finally:
                for stream in streams.values(): stream.close()
            for arm, model in models.items():
                if model.updates != row['source_counts']['eligible_updates']:
                    raise AssertionError('eligible updates differ between arms')
                model.freeze(); before = dict(model.counts); path = folder/f'{rep}_{teacher}_{arm}.npz'
                metadata = model.save(path)
                row['methods'][arm].update(final_state=component_state(model), final_counts=dict(model.counts),
                    checkpoint=dict(model_ref=str(path.relative_to(directory)), metadata=metadata,
                        save_counts=counter_delta(model.counts, before), updates=model.updates))
            row.update(parent_after=leaf_state(parent, True), teacher_after=leaf_state(leaf),
                teacher_counts=dict(frozen_teacher.counts))
            save(folder/'lifecycle.json', data)
            print(json.dumps(dict(event='training_pair_complete', life=life, representation=rep,
                teacher_query=teacher, **row['source_counts'])), flush=True)
    data['seconds'] = perf_counter()-started; save(folder/'lifecycle.json', data); return data


def prediction_diagnostic(game, models):
    result = dict(predictions={}, counts={}, before={}, after={})
    for name, model in models.items():
        before = dict(model.counts); result['before'][name] = component_state(model)
        result['predictions'][name] = []
        for step in game['steps']:
            if max(step['afterstate']) >= model.radix: continue
            prediction = model.value(step['afterstate'])
            result['predictions'][name].append({key: prediction[key] for key in ('reward','success')})
        result['counts'][name] = counter_delta(model.counts, before)
        result['after'][name] = component_state(model)
    return result


def full_game(actor, leaf, life, rep, teacher, method, replica, models=None):
    is_teacher = method == 'TEACHER'; initial = models['INITIAL_H2'] if is_teacher else None
    state = lambda: leaf_state(leaf) if is_teacher else component_state(actor)
    before, counts_before = state(), dict(actor.counts)
    zero_before = component_state(initial) if is_teacher else None
    zero_counts = dict(initial.counts) if is_teacher else None
    values, options, seconds = [], [], 0.
    def act(board, step):
        nonlocal seconds
        start = perf_counter()
        choice = actor.choose(board, QUERIES[teacher]) if is_teacher else actor.choose(board, QUERIES[teacher], depth=2)
        seconds += perf_counter()-start
        fields = ('score','value','tail_value') if is_teacher else ('score','value','tail_value','consequences')
        values.append(choice['value'])
        options.append({a: {k: item[k] for k in fields} for a,item in choice['action_values'].items()})
        if is_teacher:
            zero = initial.choose(board, QUERIES[teacher], depth=2)
            signature = lambda selected: {a:(v['afterstate'],v['score'],v['value']) for a,v in selected['action_values'].items()}
            if zero['action'] != choice['action'] or signature(zero) != signature(choice):
                raise AssertionError('initial own-query action values differ from frozen teacher')
        return choice['action']
    game = previous.run_episode(evaluation_seed(life,replica), act, .1, MAX_STEPS)
    result = previous.game_result(game, teacher, counter_delta(actor.counts, counts_before), seconds)
    result.update(model_state_before=before, model_state_after=state())
    row = dict(life=life, representation=rep, teacher_query=teacher, query=teacher, method=method,
        replica=replica, seed=game['seed'], result=result, **previous.compact_trace(game),
        chosen_values=values, action_values=options)
    if is_teacher:
        row['zero_equivalence'] = dict(exact=True, before=zero_before, after=component_state(initial),
            counts=counter_delta(initial.counts, zero_counts))
        row['diagnostic'] = prediction_diagnostic(game, models)
    return row


def evaluate_lifecycle(source, trained, directory):
    started = perf_counter(); life = source['life']; folder = directory/f'eval_{life}'; folder.mkdir()
    trace = str((folder/'control.jsonl.gz').relative_to(directory)); representations = {}
    with gzip.open(directory/trace, 'wt') as output:
        for rep in REPRESENTATIONS:
            representations[rep] = {}
            for teacher in TEACHER_QUERIES:
                parent, leaf, actor, loads = previous.load_teacher(source, rep, teacher, folder)
                initial = previous.PolicyComponents(leaf, folder/'build'); initial.freeze()
                models = dict(INITIAL_H2=initial); model_loads = []
                for arm in ARMS:
                    checkpoint = trained['representations'][rep][teacher]['methods'][arm]['checkpoint']
                    model = previous.PolicyComponents.load(directory/checkpoint['model_ref'], leaf, folder/'build')
                    model.freeze(); models[arm] = model
                    model_loads.append(dict(method=arm, model_ref=checkpoint['model_ref'], state=component_state(model),
                        setup_counts=dict(model.setup_counts), setup_seconds=model.setup_seconds,
                        load_counts=dict(model.load_counts), load_seconds=model.last_load_seconds))
                row = dict(loads=loads, model_loads=model_loads, parent_before=leaf_state(parent, True),
                    teacher_before=leaf_state(leaf), initialization=dict(state=component_state(initial),
                        setup_counts=dict(initial.setup_counts), setup_seconds=initial.setup_seconds))
                representations[rep][teacher] = row
                for replica in range(REPLICAS):
                    append(output, full_game(actor, leaf, life, rep, teacher, 'TEACHER', replica, models))
                for arm in ARMS:
                    for replica in range(REPLICAS):
                        append(output, full_game(models[arm], leaf, life, rep, teacher, arm, replica))
                    output.flush()
                row.update(parent_after=leaf_state(parent, True), teacher_after=leaf_state(leaf),
                    teacher_counts=dict(actor.counts),
                    final_model_states={name: component_state(model) for name,model in models.items()})
                print(json.dumps(dict(event='control_pair_complete', life=life,
                    representation=rep, teacher_query=teacher)), flush=True)
    data = dict(life=life, control_trace=trace, representations=representations, seconds=perf_counter()-started)
    save(folder/'lifecycle.json', data); return data


def snapshot_code(directory):
    importlib.import_module('scripts.analyze_controlled_predictive_terminal_supervision_v137')
    files = {Path(__file__).resolve(), ROOT/'specs/TERMINAL_SUPERVISION_V137.md'}
    for module in list(sys.modules.values()):
        filename = getattr(module, '__file__', None)
        if filename:
            path = Path(filename).resolve()
            if path.is_relative_to(ROOT/'src') or path.is_relative_to(ROOT/'scripts'): files.add(path)
    for name in ('controlled_predictive_ntuple_kernel_v120.cpp','controlled_predictive_contextual_ntuple_v134.cpp',
        'controlled_predictive_frozen_leaf_planning_v135.cpp','controlled_predictive_bellman_consequences_v136.cpp'):
        files.add(ROOT/'src/acfqp/science'/name)
    files.update((ROOT/'tests').glob('*terminal_supervision*v137.py'))
    for path in files:
        target = directory/'source'/path.relative_to(ROOT); target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)


def run(directory):
    directory = directory.resolve(); directory.mkdir(parents=True, exist_ok=False); started = perf_counter()
    read = lambda name: json.loads((SOURCE/name).read_text())
    source = extract_source(read('source_capsule.json'), read('run.json'), read('analysis.json'))
    save(directory/'source_capsule.json', source); snapshot_code(directory)
    data = dict(schema='acfqp.terminal_supervision.v137.run', status='training', settings=settings(),
        inherited_costs=source['inherited_costs'], lifecycles=[], eval_lifecycles=[],
        executable=sys.executable, platform=platform.platform())
    save(directory/'run.json', data)
    with ProcessPoolExecutor(max_workers=WORKERS) as pool:
        tasks = [pool.submit(train_lifecycle,s,directory) for s in source['snapshots']]
        for future in as_completed(tasks):
            data['lifecycles'].append(future.result()); data['lifecycles'].sort(key=lambda r:r['life'])
            save(directory/'run.json', data)
        data['status'] = 'frozen'; save(directory/'frozen_training.json',deepcopy(data)); save(directory/'run.json',data)
        print(json.dumps(dict(event='all_training_frozen')),flush=True)
        trained = {row['life']:row for row in data['lifecycles']}; data['status'] = 'evaluation'; save(directory/'run.json',data)
        tasks = [pool.submit(evaluate_lifecycle,s,trained[s['life']],directory) for s in source['snapshots']]
        for future in as_completed(tasks):
            data['eval_lifecycles'].append(future.result()); data['eval_lifecycles'].sort(key=lambda r:r['life'])
            save(directory/'run.json',data)
    data.update(status='complete',seconds=perf_counter()-started); save(directory/'run.json',data)
    print(json.dumps(dict(status='complete',seconds=data['seconds'])),flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'reports/controlled_predictive_terminal_supervision_v137')
    run(parser.parse_args().output)
