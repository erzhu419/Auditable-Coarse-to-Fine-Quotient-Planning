"""Compare direct control and one extra planning layer on the same frozen values."""
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
from scripts.run_controlled_predictive_contextual_ntuple_v134 import model_state
from acfqp.science.controlled_predictive_regime_experience_v115 import run_episode
from acfqp.science.controlled_predictive_online_query_td_v131 import QueryTD
from acfqp.science.controlled_predictive_contextual_ntuple_v134 import ConditionalQueryTD
from acfqp.science.controlled_predictive_frozen_leaf_planning_v135 import FrozenLeafPlanner

SOURCE = ROOT/'reports/controlled_predictive_contextual_ntuple_v134'
QUERIES = {q: ALL_QUERIES[q] for q in ('risk1', 'risk8')}
PARENTS = dict(risk1='reward', risk8='risk_goal')
LIVES, REPRESENTATIONS, MODES = (0, 1, 2, 3), ('SINGLE', 'CAPACITY'), ('DIRECT', 'H2')
DEPTHS = dict(DIRECT=1, H2=2)
REPLICAS, MAX_STEPS, WORKERS, CHECKPOINT, BASE = 16, 2000, 4, 524288, 135*100000000


def settings():
    return dict(lifecycles=list(LIVES), policies=POLICIES, queries=QUERIES, parents=PARENTS,
        representations=list(REPRESENTATIONS), modes=list(MODES), depths=DEPTHS,
        checkpoint=CHECKPOINT, replicas=REPLICAS, max_steps=MAX_STEPS, workers=WORKERS,
        p_four=.1, planner_spawn_law='frozen_identified_distribution', version_base=BASE,
        physical_control_games=512, new_training_transitions=0)


def evaluation_seed(life, replica):
    return BASE+90000000+life*100000+replica


def extract_source(previous, run, analysis):
    if not (run['status'] == 'complete' and analysis['complete'] and analysis['primary_complete']):
        raise ValueError('V134 must be complete')
    trained = {row['life']: row for row in run['lifecycles']}
    snapshots = []
    for row in previous['snapshots']:
        source = {k: deepcopy(row[k]) for k in ('life', 'rule', 'models', 'counts')}
        source['leaves'] = {}
        for query in QUERIES:
            source['leaves'][query] = {}
            for kind in REPRESENTATIONS:
                checkpoints = trained[source['life']]['queries'][query]['learners'][kind]['checkpoints']
                checkpoint = next(c for c in checkpoints if c['age'] == CHECKPOINT)
                source['leaves'][query][kind] = dict(checkpoint=CHECKPOINT,
                    model_ref=str((SOURCE/checkpoint['model_ref']).resolve()),
                    updates=checkpoint['updates'], parameter_count=checkpoint['metadata']['parameter_count'])
        snapshots.append(source)
    return dict(schema='acfqp.frozen_leaf_planning.v135.source', snapshots=snapshots,
        inherited_costs=dict(**deepcopy(previous['inherited_costs']), v134_experiment=deepcopy(analysis['costs'])),
        required_inputs='V134 final SINGLE/CAPACITY values, their identified dynamics and original query conversion',
        scope='Both representations and all histories are fixed; new evaluation outcomes do not modify or select models.')


def full_game(planner, model, life, query, representation, mode, replica):
    previous, before = dict(planner.counts), model_state(model)
    values, alternatives, decision_seconds = [], [], 0.
    def act(board, step):
        nonlocal decision_seconds
        started = perf_counter(); choice = planner.choose(board, QUERIES[query])
        decision_seconds += perf_counter()-started
        values.append(choice['value'])
        alternatives.append({a: {k: row[k] for k in ('score', 'value', 'tail_value')}
            for a, row in choice['action_values'].items()})
        return choice['action']
    game = run_episode(evaluation_seed(life, replica), act, .1, MAX_STEPS)
    row = dict(life=life, query=query, representation=representation, mode=mode,
        method=f'{representation}_{mode}', checkpoint=CHECKPOINT, replica=replica, seed=game['seed'],
        result=result(game, query, policy_counts=counter_delta(planner.counts, previous)),
        **compact_trace(game), chosen_values=values, action_values=alternatives)
    row['result'].update(model_state_before=before, model_state_after=model_state(model),
        decision_seconds=decision_seconds)
    return row


def evaluate_lifecycle(source, directory):
    started = perf_counter(); life = source['life']; folder = directory/f'life_{life}'; folder.mkdir()
    trace = str((folder/'control.jsonl.gz').relative_to(directory)); queries = {}
    with gzip.open(directory/trace, 'wt') as output:
        for query in QUERIES:
            parent, loads = load_parent(source, query, folder)
            qdata = dict(loads=loads, parent_before=model_state(parent, True), representations={})
            queries[query] = qdata
            for representation in REPRESENTATIONS:
                reference = source['leaves'][query][representation]
                model_class = QueryTD if representation == 'SINGLE' else ConditionalQueryTD
                model = model_class.load(reference['model_ref'], parent, folder/'build'); model.freeze()
                rdata = dict(reference=deepcopy(reference), before=model_state(model), planners={},
                    load_counts=dict(model.load_counts), load_seconds=model.last_load_seconds,
                    setup_counts=dict(model.setup_counts), setup_seconds=model.setup_seconds)
                qdata['representations'][representation] = rdata
                for mode in MODES:
                    planner = FrozenLeafPlanner(model, depth=DEPTHS[mode], build_dir=folder/'build')
                    pdata = dict(setup_counts=dict(planner.setup_counts), setup_seconds=planner.setup_seconds,
                        spawn_probabilities=list(planner.spawn_probabilities), before=model_state(model))
                    rdata['planners'][mode] = pdata
                    for replica in range(REPLICAS):
                        append(output, full_game(planner, model, life, query, representation, mode, replica))
                    output.flush()
                    pdata.update(after=model_state(model), counts=dict(planner.counts))
                    print(json.dumps(dict(event='control_complete', life=life, query=query,
                        representation=representation, mode=mode)), flush=True)
                rdata['after'] = model_state(model)
            qdata['parent_after'] = model_state(parent, True)
    data = dict(life=life, control_trace=trace, queries=queries, seconds=perf_counter()-started)
    save(folder/'lifecycle.json', data); return data


def snapshot_code(directory):
    importlib.import_module('scripts.analyze_controlled_predictive_frozen_leaf_planning_v135')
    files = {Path(__file__).resolve(), ROOT/'specs/FROZEN_LEAF_PLANNING_V135.md'}
    for module in list(sys.modules.values()):
        filename = getattr(module, '__file__', None)
        if filename:
            path = Path(filename).resolve()
            if path.is_relative_to(ROOT/'src') or path.is_relative_to(ROOT/'scripts'): files.add(path)
    for name in ('controlled_predictive_ntuple_kernel_v120.cpp', 'controlled_predictive_contextual_ntuple_v134.cpp',
                 'controlled_predictive_frozen_leaf_planning_v135.cpp'):
        files.add(ROOT/'src/acfqp/science'/name)
    files.update((ROOT/'tests').glob('*frozen_leaf_planning*v135.py'))
    for path in files:
        target = directory/'source'/path.relative_to(ROOT); target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)


def run(directory):
    directory = directory.resolve(); started = perf_counter(); directory.mkdir(parents=True, exist_ok=False)
    read = lambda name: json.loads((SOURCE/name).read_text())
    source = extract_source(read('source_capsule.json'), read('run.json'), read('analysis.json'))
    save(directory/'source_capsule.json', source); snapshot_code(directory)
    data = dict(schema='acfqp.frozen_leaf_planning.v135.run', status='evaluation', settings=settings(),
        inherited_costs=source['inherited_costs'], eval_lifecycles=[],
        executable=sys.executable, platform=platform.platform())
    save(directory/'run.json', data)
    with ProcessPoolExecutor(max_workers=WORKERS) as pool:
        tasks = [pool.submit(evaluate_lifecycle, s, directory) for s in source['snapshots']]
        for future in as_completed(tasks):
            data['eval_lifecycles'].append(future.result()); data['eval_lifecycles'].sort(key=lambda r: r['life'])
            save(directory/'run.json', data)
    data.update(status='complete', seconds=perf_counter()-started); save(directory/'run.json', data)
    print(json.dumps(dict(status='complete', seconds=data['seconds'])), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'reports/controlled_predictive_frozen_leaf_planning_v135')
    run(parser.parse_args().output)
