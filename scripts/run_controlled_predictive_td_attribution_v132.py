"""Replay frozen risk8 updates and attribute retained action-gap changes."""
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
import gzip
import importlib
import json
import math
from pathlib import Path
import platform
import shutil
import sys
from time import perf_counter

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT/'src'))
from scripts.run_controlled_predictive_policy_consequences_v126 import save, append, counter_delta
from scripts.run_controlled_predictive_paired_ntuple_v130 import load_parent
from scripts.analyze_controlled_predictive_ntuple_learning_v120 import read_rows
from acfqp.science.controlled_predictive_online_query_td_v131 import QueryTD
from acfqp.science.controlled_predictive_forced_actions_v128 import board_at_first_divergence

SOURCE = ROOT/'reports/controlled_predictive_online_query_td_v131'
LIVES, AGES, GROUPS = (0, 1, 2, 3), (131072, 524288), ('FIRST', 'FEATURE')
REPLICAS, WORKERS, QUERY = 16, 4, 'risk8'


def settings():
    return dict(lifecycles=list(LIVES), ages=list(AGES), groups=list(GROUPS), query=QUERY,
        kind='PRIOR', replicas=REPLICAS, workers=WORKERS, alpha=.0025,
        slots=128, replay_transitions_per_life=AGES[1]-AGES[0], new_environment_samples=0)


def extract_source(previous, run, analysis):
    if not analysis['complete'] or run['status'] != 'complete': raise ValueError('V131 must be complete')
    training = {r['life']: r for r in run['lifecycles']}
    evaluation = {r['life']: r for r in run['eval_lifecycles']}
    snapshots = []
    for old in previous['snapshots']:
        row = {k: deepcopy(old[k]) for k in ('life', 'rule', 'models', 'counts')}
        learner = training[row['life']]['queries'][QUERY]['learners']['PRIOR']
        row['checkpoints'] = {str(c['age']): dict(path=str(SOURCE/c['model_ref']),
            updates=c['updates'], stream_state=deepcopy(c['stream_state']))
            for c in learner['checkpoints'] if c['age'] in AGES}
        row['training_trace'] = str(SOURCE/learner['training_trace'])
        row['control_trace'] = str(SOURCE/evaluation[row['life']]['control_trace'])
        snapshots.append(row)
    return dict(schema='acfqp.td_attribution.v132.source', snapshots=snapshots,
        inherited_costs=dict(**deepcopy(previous['inherited_costs']), v131_experiment=deepcopy(analysis['costs'])))


def load_models(source, folder):
    parent, source_load = load_parent(source, QUERY, folder)
    models, loads = [], []
    for age in AGES:
        model = QueryTD.load(source['checkpoints'][str(age)]['path'], parent, folder/'build'); model.freeze()
        if model.updates != source['checkpoints'][str(age)]['updates']: raise ValueError('checkpoint updates changed')
        models.append(model)
        loads.append(dict(age=age, counts=model.load_counts, seconds=model.last_load_seconds,
            setup_counts=dict(model.setup_counts), setup_seconds=model.setup_seconds))
    return models, dict(source=source_load, checkpoints=loads)


def feature_counts(model, afterstate):
    return Counter() if max(afterstate) >= model.radix else Counter(map(int, model.model.feature_indices(afterstate)))


def feature_difference(model, old, new):
    left, right = feature_counts(model, old), feature_counts(model, new)
    return {i: right[i]-left[i] for i in sorted(set(left)|set(right)) if right[i] != left[i]}


def equivalent_d4(left, right):
    board = np.asarray(left).reshape(4, 4); target = np.asarray(right).reshape(4, 4)
    return any(np.array_equal(np.rot90(np.fliplr(board) if reflected else board, turn), target)
        for reflected in (False, True) for turn in range(4))


def probe_prediction(models, board, choices):
    old_action, new_action = (c['action'] for c in choices)
    old, new = (choices[0]['action_values'][a] for a in (old_action, new_action))
    dphi = feature_difference(models[0], old['afterstate'], new['afterstate'])
    goal = models[0].target_query['goal_bonus']; offset = models[0].offset
    base_gap = math.fsum([(new['score']-old['score'])/2048.,
        (goal if max(new['afterstate']) >= models[0].radix else offset)-
        (goal if max(old['afterstate']) >= models[0].radix else offset)])
    features = [dict(address=i, coefficient=c, mid_weight=float(models[0].weights.reshape(-1)[i]),
        final_weight=float(models[1].weights.reshape(-1)[i])) for i, c in dphi.items()]
    result = dict(board=list(board), old_action=old_action, new_action=new_action,
        old_afterstate=old['afterstate'], new_afterstate=new['afterstate'], base_gap=base_gap,
        feature_difference=features, exact_feature_tie=not dphi and base_gap == 0.,
        d4_equivalent=equivalent_d4(old['afterstate'], new['afterstate']))
    for key, model, choice in zip(('mid', 'final'), models, choices):
        rows = choice['action_values']
        result[key] = dict(action=choice['action'], action_values={a: {k: r[k] for k in
            ('afterstate', 'score', 'value', 'raw_value')} for a, r in rows.items()},
            rounded_gap=rows[new_action]['value']-rows[old_action]['value'],
            canonical_gap=math.fsum([base_gap]+[r['coefficient']*r[key+'_weight'] for r in features]))
    result['strict_canonical_flip'] = result['mid']['canonical_gap'] < 0. < result['final']['canonical_gap']
    return result


def advance_recorded(row, index, board, rule, work):
    after, score, changed = rule.swipe(board, row['actions'][index], work)
    cell, rank = row['spawned_cells'][index], row['spawned_ranks'][index]
    if not changed or score != row['scores'][index] or after[cell] != 0 or rank not in (1, 2):
        raise ValueError('retained control prefix disagrees with the identified rule')
    after = list(after); after[cell] = rank; work['recorded_spawns_replayed'] += 1
    return tuple(after)


def first_feature_probe(models, row, work):
    board = tuple(row['initial_board'])
    selection = dict(scanned_steps=0, differing_candidates=[])
    for index, action in enumerate(row['actions']):
        choices = [m.choose(board) for m in models]
        selection['scanned_steps'] += 1
        if choices[0]['action'] != action or choices[0]['value'] != row['chosen_values'][index]:
            raise ValueError('MID model no longer reproduces its retained trajectory')
        if choices[0]['action'] != choices[1]['action']:
            a, b = (choices[0]['action_values'][c['action']]['afterstate'] for c in choices)
            work['feature_difference_checks'] += 1
            difference = feature_difference(models[0], a, b)
            selection['differing_candidates'].append(dict(index=index,
                mid_action=choices[0]['action'], final_action=choices[1]['action'],
                nonzero_features=bool(difference)))
            if difference:
                return index, probe_prediction(models, board, choices), selection
        board = advance_recorded(row, index, board, models[0].rule, work)
    return None, None, selection


def prepare_lifecycle(source, directory):
    started = perf_counter(); life = source['life']; folder = directory/f'panel_{life}'; folder.mkdir()
    models, loads = load_models(source, folder); before = [dict(m.counts) for m in models]
    rows = {(r['checkpoint'], r['replica']): r for r in read_rows(Path(source['control_trace']))
        if r['query'] == QUERY and r['method'] == 'PRIOR' and r['checkpoint'] in AGES}
    if set(rows) != {(a, r) for a in AGES for r in range(REPLICAS)}: raise ValueError('fixed evaluation roster incomplete')
    cases, probes, seen, work = [], [], {}, Counter()
    for group in GROUPS:
        for replica in range(REPLICAS):
            left, right = (rows[a, replica] for a in AGES)
            selection = None
            if group == 'FIRST':
                divergence = board_at_first_divergence(left, right, models[0].rule); work.update(divergence['counts'])
                index, item = divergence['index'], None
                if divergence['diverged']:
                    choices = [m.choose(divergence['board']) for m in models]
                    if (choices[0]['action'], choices[1]['action']) != (divergence['left_action'], divergence['right_action']):
                        raise ValueError('retained first divergence no longer reproduces')
                    item = probe_prediction(models, divergence['board'], choices)
            else:
                index, item, selection = first_feature_probe(models, left, work)
            case = dict(case_id=GROUPS.index(group)*64+life*16+replica, life=life, group=group,
                replica=replica, seed=left['seed'], index=index, available=item is not None,
                local_probe_id=None, selection_trace=selection,
                mid_utility=left['result']['utility'], final_utility=right['result']['utility'])
            if item is not None:
                key = tuple(item['board'])
                if key not in seen:
                    seen[key] = len(probes); probes.append(dict(item, life=life))
                case['local_probe_id'] = seen[key]
            cases.append(case)
    data = dict(life=life, cases=cases, probes=probes, loads=loads, prefix_counts=dict(work),
        prediction_counts=[counter_delta(m.counts, b) for m, b in zip(models, before)],
        seconds=perf_counter()-started)
    save(folder/'lifecycle.json', data); return data


def assemble_roster(prepared):
    cases, probes = [], []
    for life in sorted(prepared, key=lambda r: r['life']):
        offset = len(probes)
        for row in life['probes']:
            probes.append(dict(deepcopy(row), probe_id=len(probes)))
        for row in life['cases']:
            item = {k: deepcopy(v) for k, v in row.items() if k != 'local_probe_id'}
            item['probe_id'] = offset+row['local_probe_id'] if row['available'] else None; cases.append(item)
    return dict(schema='acfqp.td_attribution.v132.roster', cases=sorted(cases, key=lambda c: c['case_id']), probes=probes)


def replay_lifecycle(source, probes, directory):
    from acfqp.science.controlled_predictive_td_attribution_v132 import TDAttributionReplay
    started = perf_counter(); life = source['life']; folder = directory/f'replay_{life}'; folder.mkdir()
    models, loads = load_models(source, folder)
    replay = TDAttributionReplay(models[0], probes, folder/'build')
    trace = str((folder/'segments.jsonl.gz').relative_to(directory)); skipped, transitions, segments = 0, 0, 0
    with gzip.open(directory/trace, 'wt') as output:
        for row in read_rows(Path(source['training_trace'])):
            if row['checkpoint'] != AGES[1]: skipped += len(row['actions']); continue
            if segments == 0:
                state = source['checkpoints'][str(AGES[0])]['stream_state']
                if (row['pending_before'], row['start_board'], row['start_step']) != (state['pending'], state['board'], state['step']):
                    raise ValueError('initial replay pending or board changed')
            result = replay.segment(row); transitions += len(row['actions']); segments += 1
            append(output, dict(life=life, episode=row['episode'], start_step=row['start_step'],
                end_step=row['end_step'], status=row['status'], cumulative_transitions=row['cumulative_transitions'],
                updates_before=row['updates_before'], updates_after=row['updates_after'], **result))
            if segments % 128 == 0:
                output.flush(); print(json.dumps(dict(event='replay_progress', life=life, transitions=transitions)), flush=True)
    if skipped != AGES[0] or transitions != AGES[1]-AGES[0]: raise ValueError('retained training budget changed')
    result = replay.finish(models[1])
    result.update(life=life, trace=trace, loads=loads, prefix_transitions_read=skipped,
        replayed_transitions=transitions, segments=segments, seconds=perf_counter()-started)
    save(folder/'lifecycle.json', result); return result


def snapshot_code(directory):
    importlib.import_module('acfqp.science.controlled_predictive_td_attribution_v132')
    importlib.import_module('scripts.analyze_controlled_predictive_td_attribution_v132')
    files = {Path(__file__).resolve(), ROOT/'specs/TD_ATTRIBUTION_V132.md'}
    for module in list(sys.modules.values()):
        filename = getattr(module, '__file__', None)
        if filename:
            path = Path(filename).resolve()
            if path.is_relative_to(ROOT/'src') or path.is_relative_to(ROOT/'scripts'): files.add(path)
    for name in ('controlled_predictive_ntuple_kernel_v120.cpp', 'controlled_predictive_td_attribution_v132.cpp'):
        files.add(ROOT/'src/acfqp/science'/name)
    files.update((ROOT/'tests').glob('*td_attribution*v132.py'))
    for path in files:
        target = directory/'source'/path.relative_to(ROOT); target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)


def run(directory):
    directory = directory.resolve(); started = perf_counter(); directory.mkdir(parents=True, exist_ok=False)
    source = extract_source(json.loads((SOURCE/'source_capsule.json').read_text()),
        json.loads((SOURCE/'run.json').read_text()), json.loads((SOURCE/'analysis.json').read_text()))
    save(directory/'source_capsule.json', source); snapshot_code(directory)
    data = dict(schema='acfqp.td_attribution.v132.run', status='preparing', settings=settings(),
        inherited_costs=source['inherited_costs'], panel_lifecycles=[], replay_lifecycles=[],
        executable=sys.executable, platform=platform.platform())
    save(directory/'run.json', data)
    with ProcessPoolExecutor(max_workers=WORKERS) as pool:
        tasks = [pool.submit(prepare_lifecycle, s, directory) for s in source['snapshots']]
        for future in as_completed(tasks):
            data['panel_lifecycles'].append(future.result()); data['panel_lifecycles'].sort(key=lambda r: r['life'])
            save(directory/'run.json', data)
        roster = assemble_roster(data['panel_lifecycles']); save(directory/'roster.json', roster)
        data['status'] = 'replaying'; save(directory/'run.json', data)
        print(json.dumps(dict(event='roster_frozen', slots=len(roster['cases']), probes=len(roster['probes']))), flush=True)
        tasks = [pool.submit(replay_lifecycle, s, [p for p in roster['probes'] if p['life'] == s['life']], directory)
            for s in source['snapshots']]
        for future in as_completed(tasks):
            data['replay_lifecycles'].append(future.result()); data['replay_lifecycles'].sort(key=lambda r: r['life'])
            save(directory/'run.json', data)
    data.update(status='complete', seconds=perf_counter()-started); save(directory/'run.json', data)
    print(json.dumps(dict(status='complete', seconds=data['seconds'])), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'reports/controlled_predictive_td_attribution_v132')
    run(parser.parse_args().output)
