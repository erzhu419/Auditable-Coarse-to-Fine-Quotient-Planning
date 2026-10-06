"""Freeze retained first divergences, then measure paired fixed-policy action effects."""
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
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics
from acfqp.science.controlled_predictive_ntuple_td_v120 import NtupleValue
from acfqp.science.controlled_predictive_anchored_success_v127 import choose_gpi
from acfqp.science.controlled_predictive_forced_actions_v128 import (
    board_at_first_divergence, load_anchored_success, run_forced_continuation)

SOURCE = ROOT / 'reports/controlled_predictive_anchored_success_v127'
QUERIES = {q: ALL_QUERIES[q] for q in ('risk1', 'risk8')}
LIVES, RETAINED_REPLICAS, REPLICAS, MAX_STEPS, WORKERS = (0, 1, 2, 3), 8, 16, 2000, 4
BASE = 128 * 100000000


def settings():
    return dict(lifecycles=list(LIVES), queries=QUERIES, policies=POLICIES,
        retained_replicas=RETAINED_REPLICAS, retained_checkpoint=1024,
        replicas=REPLICAS, max_steps=MAX_STEPS, workers=WORKERS,
        version_base=BASE, p_four=.1)


def suffix_seed(root_id, replica):
    return BASE + 90000000 + root_id * 1000 + replica


def extract_source(previous, previous_run, analysis):
    if not analysis['complete'] or previous_run['status'] != 'complete':
        raise ValueError('V128 needs the completed V127 histories and count states')
    lives = {r['life']: r for r in previous_run['lifecycles']}
    snapshots = []
    for old in previous['snapshots']:
        item = {k: deepcopy(old[k]) for k in ('life', 'rule', 'models')}
        item['control_trace'] = str(SOURCE / lives[item['life']]['control_trace'])
        item['counts'] = {}
        for policy in POLICIES:
            checkpoint = next(c for c in lives[item['life']]['policies'][policy]['checkpoints']
                              if c['age'] == 1024)
            item['counts'][policy] = {k: checkpoint[k] for k in
                ('updates', 'successes', 'constant', 'model_bytes')}
            item['counts'][policy]['path'] = str(SOURCE / checkpoint['model_ref'])
        snapshots.append(item)
    return dict(schema='acfqp.forced_actions.v128.source', snapshots=snapshots,
        inherited_costs=dict(**deepcopy(previous['inherited_costs']),
                             v127_processing=deepcopy(analysis['costs'])))


def build_roster(source):
    started = perf_counter(); cases, roots, root_ids = [], [], {}
    counts = Counter()
    for snapshot in sorted(source['snapshots'], key=lambda s: s['life']):
        life = snapshot['life']; rule = LearnedDynamics.from_payload(snapshot['rule'])
        rows = {}
        for row in read_rows(Path(snapshot['control_trace'])):
            if (row['checkpoint'] == 1024 and row['query'] in QUERIES
                    and row['method'] in ('LEARNED_risk_goal', 'CONSTANT_risk_goal')):
                key = row['query'], row['replica'], row['method']
                if key in rows: raise ValueError('duplicate retained V127 case')
                rows[key] = row
        for query in QUERIES:
            for replica in range(RETAINED_REPLICAS):
                left = rows[query, replica, 'LEARNED_risk_goal']
                right = rows[query, replica, 'CONSTANT_risk_goal']
                divergence = board_at_first_divergence(left, right, rule)
                counts.update(divergence['counts'])
                case = dict(case_id=len(cases), life=life, query=query, replica=replica,
                    left_eval_id=left['eval_id'], right_eval_id=right['eval_id'],
                    **divergence, root_id=None)
                if case['diverged']:
                    key = life, tuple(case['board'])
                    if key not in root_ids:
                        root_ids[key] = len(roots)
                        roots.append(dict(root_id=len(roots), life=life, board=case['board'], actions=[]))
                    case['root_id'] = root_ids[key]; root = roots[case['root_id']]
                    root['actions'] = sorted(set(root['actions']) | {case['left_action'], case['right_action']})
                    i = case['index']
                    case['retained_choices'] = {
                        side: dict(action=row['actions'][i], anchor_value=row['chosen_anchor_values'][i],
                            success_probability=row['chosen_success_probabilities'][i],
                            value=row['chosen_values'][i])
                        for side, row in (('LEARNED', left), ('CONSTANT', right))}
                cases.append(case)
    physical = sum(len(root['actions']) for root in roots) * len(POLICIES) * REPLICAS
    logical = sum(case['diverged'] for case in cases) * 2 * len(POLICIES) * REPLICAS
    return dict(schema='acfqp.forced_actions.v128.roster', cases=cases, roots=roots,
        physical_attempts=physical, logical_attempts=logical,
        preparation=dict(prefix_counts=dict(counts), roster_seconds=perf_counter()-started))


def load_source(snapshot, policy, build):
    actor = NtupleValue.load(snapshot['models'][policy]['path'],
                             LearnedDynamics.from_payload(snapshot['rule']), build)
    actor.weights.flags.writeable = False
    if actor.updates != snapshot['models'][policy]['updates']:
        raise ValueError('source scalar checkpoint update count changed')
    return actor


def predict_lifecycle(snapshot, roster, directory):
    started = perf_counter(); life = snapshot['life']; build = directory / f'prep_{life}/build'
    roots = [r for r in roster['roots'] if r['life'] == life]
    cases = [c for c in roster['cases'] if c['life'] == life and c['diverged']]
    model_costs = {}
    for policy in POLICIES:
        actor = load_source(snapshot, policy, build)
        model = load_anchored_success(snapshot['counts'][policy]['path'], actor, POLICIES[policy], build)
        count_state = snapshot['counts'][policy]
        if (model.updates, model.successes) != (count_state['updates'], count_state['successes']):
            raise ValueError('event count state differs from the frozen source capsule')
        before = dict(model.counts)
        for root in roots:
            choice = choose_gpi([model], root['board'], QUERIES['risk1'], mode='LEARNED')
            root.setdefault('predictions', {})[policy] = {
                action: dict(value=row['anchor_value'], score=row['score'],
                    afterstate=row['afterstate'], success_probability=row['success_probability'])
                for action, row in choice['action_values'].items()}
        if policy == 'risk_goal':
            cache = {}
            for case in cases:
                for mode in ('LEARNED', 'CONSTANT'):
                    key = case['root_id'], case['query'], mode
                    if key not in cache:
                        chosen = choose_gpi([model], case['board'], QUERIES[case['query']], mode=mode)
                        cache[key] = {k: chosen[k] for k in
                            ('action', 'anchor_value', 'success_probability', 'value')}
                    if cache[key] != case['retained_choices'][mode]:
                        raise ValueError(f'loaded V127 choice disagrees with retained case {case["case_id"]}: {mode}')
                case['retained_choices_reproduced'] = True
        model_costs[policy] = dict(source_updates_before=actor.updates, source_updates_after=actor.updates,
            count_updates_before=model.updates, count_updates_after=model.updates,
            source_load_counts={k: v for k, v in actor.counts.items() if k.startswith('checkpoint_load')},
            source_load_seconds=actor.last_load_seconds, source_setup_counts=dict(actor.setup_counts),
            source_setup_seconds=actor.setup_seconds, count_load_counts=model.load_counts,
            count_load_seconds=model.last_load_seconds, count_setup_counts=dict(model.setup_counts),
            count_setup_seconds=model.setup_seconds, prediction_counts=counter_delta(model.counts, before),
            constant=model.global_success_rate,
            active_weight_bytes=actor.weights.nbytes + model.visits.nbytes + model.wins.nbytes)
        del model, actor
    return dict(life=life, models=model_costs, seconds=perf_counter()-started)


def forced_row(root, policy, replica, actor):
    game = run_forced_continuation(root['board'], root['forced_action'], actor, POLICIES[policy],
                                   suffix_seed(root['root_id'], replica), MAX_STEPS)
    row = dict(root_id=root['root_id'], life=root['life'], forced_action=root['forced_action'],
        policy=policy, replica=replica, seed=game['seed'],
        result=result(game, policy, policy_counts=game['policy_counts']), **compact_trace(game))
    row['result'].update(source_updates_before=game['source_updates_before'],
                          source_updates_after=game['source_updates_after'])
    return row


def lifecycle_run(snapshot, roots, directory):
    started = perf_counter(); life = snapshot['life']; folder = directory / f'life_{life}'
    folder.mkdir(); actors, model_costs = {}, {}
    for policy in POLICIES:
        actor = load_source(snapshot, policy, folder / 'build'); actors[policy] = actor
        model_costs[policy] = dict(source_updates_before=actor.updates,
            source_load_counts={k: v for k, v in actor.counts.items() if k.startswith('checkpoint_load')},
            source_load_seconds=actor.last_load_seconds, source_setup_counts=dict(actor.setup_counts),
            source_setup_seconds=actor.setup_seconds)
    data = dict(life=life, trace=str((folder / 'continuations.jsonl.gz').relative_to(directory)),
        models=model_costs, games=0, environment_counts=Counter(), policy_counts=Counter(),
        statuses=Counter(), continuation_seconds=0.,
        peak_weight_bytes=sum(a.weights.nbytes for a in actors.values()))
    with gzip.open(directory / data['trace'], 'wt') as stream:
        for root in roots:
            for action in root['actions']:
                for policy in POLICIES:
                    for replica in range(REPLICAS):
                        row = forced_row(dict(root, forced_action=action), policy, replica, actors[policy])
                        append(stream, row); r = row['result']; data['games'] += 1
                        data['environment_counts'].update(r['environment_counts'])
                        data['policy_counts'].update(r['policy_counts']); data['statuses'][r['status']] += 1
                        data['continuation_seconds'] += r['seconds']
            stream.flush(); save(folder / 'lifecycle.json', data)
            print(json.dumps(dict(event='root_complete', life=life, root_id=root['root_id'],
                                  games=data['games'])), flush=True)
    for policy in POLICIES:
        data['models'][policy]['source_updates_after'] = actors[policy].updates
    data['seconds'] = perf_counter()-started; save(folder / 'lifecycle.json', data); return data


def snapshot_code(directory):
    importlib.import_module('scripts.analyze_controlled_predictive_forced_actions_v128')
    files = {Path(__file__).resolve(), ROOT / 'specs/FORCED_ACTIONS_V128.md'}
    for module in list(sys.modules.values()):
        filename = getattr(module, '__file__', None)
        if filename:
            path = Path(filename).resolve()
            if path.is_relative_to(ROOT / 'src') or path.is_relative_to(ROOT / 'scripts'):
                files.add(path)
    files.add(ROOT / 'src/acfqp/science/controlled_predictive_ntuple_kernel_v120.cpp')
    files.add(ROOT / 'src/acfqp/science/controlled_predictive_anchored_success_v127.cpp')
    files.update((ROOT / 'tests').glob('*forced_actions*v128.py'))
    for path in files:
        target = directory / 'source' / path.relative_to(ROOT); target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)


def run(directory):
    directory = directory.resolve(); started = perf_counter(); directory.mkdir(parents=True, exist_ok=False)
    source = extract_source(json.loads((SOURCE / 'source_capsule.json').read_text()),
        json.loads((SOURCE / 'run.json').read_text()), json.loads((SOURCE / 'analysis.json').read_text()))
    save(directory / 'source_capsule.json', source); snapshot_code(directory)
    data = dict(schema='acfqp.forced_actions.v128.run', status='preparing', settings=settings(),
        inherited_costs=source['inherited_costs'], lifecycles=[], executable=sys.executable,
        platform=platform.platform())
    save(directory / 'run.json', data)
    roster = build_roster(source)
    roster['preparation']['lifecycles'] = [predict_lifecycle(s, roster, directory) for s in source['snapshots']]
    roster['preparation']['seconds'] = perf_counter()-started
    save(directory / 'roster.json', roster)
    data.update(status='sampling', preparation=roster['preparation'])
    save(directory / 'run.json', data)
    print(json.dumps(dict(event='roster_frozen', cases=len(roster['cases']), roots=len(roster['roots']),
        physical_attempts=roster['physical_attempts'], logical_attempts=roster['logical_attempts'])), flush=True)
    with ProcessPoolExecutor(max_workers=WORKERS) as pool:
        tasks = [pool.submit(lifecycle_run, s, [r for r in roster['roots'] if r['life'] == s['life']], directory)
                 for s in source['snapshots']]
        for future in as_completed(tasks):
            data['lifecycles'].append(future.result()); data['lifecycles'].sort(key=lambda r: r['life'])
            save(directory / 'run.json', data)
    data.update(status='complete', seconds=perf_counter()-started); save(directory / 'run.json', data)
    print(json.dumps(dict(status='complete', seconds=data['seconds'])), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'reports/controlled_predictive_forced_actions_v128')
    run(parser.parse_args().output)
