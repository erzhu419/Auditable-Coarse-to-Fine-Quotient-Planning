"""Remeasure fixed TRAIN labels without fitting or changing the action gate."""
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
import gzip
import importlib
import json
from pathlib import Path
import shutil
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT/'src'))
from scripts import run_controlled_predictive_shared_local_advantage_v147 as previous
from acfqp.science.controlled_predictive_counterfactual_outcomes_v143 import run_branch
from acfqp.science.controlled_predictive_paired_advantage_v144 import PairedAdvantage
from acfqp.science.controlled_predictive_shared_local_advantage_v147 import SharedLocalAdvantage

SOURCE = ROOT/'reports/controlled_predictive_shared_local_advantage_v147'
OLD_COHORT = ROOT/'reports/controlled_predictive_counterfactual_outcomes_v143/cohort.json'
NEW_COHORT = ROOT/'reports/controlled_predictive_coverage_expansion_v145/cohort.json'
LIVES, QUERIES, METHODS = previous.LIVES, previous.QUERIES, ('ZERO', 'UPDATED', 'SHARED')
BASE, SUFFIXES, MAX_STEPS, WORKERS = 148*100000000, 32, 2000, 4
save, append, leaf_state, load_teacher = previous.save, previous.append, previous.leaf_state, previous.load_teacher


def read(path): return json.loads(Path(path).read_text())


def suffix_seed(life, query, origin, replica, slot, suffix):
    return BASE+life*1000000+list(QUERIES).index(query)*100000+('OLD', 'NEW').index(origin)*50000+replica*10000+slot*100+suffix


def settings():
    return dict(lifecycles=list(LIVES), queries=QUERIES, methods=list(METHODS),
        train_replicas=[0, 1, 2, 3], origins=['OLD', 'NEW'], total_train_roots=256,
        disagreement_roots=173, same_action_roots=83, suffixes_per_root=SUFFIXES,
        paired_records=5536, physical_branches=11072, workers=WORKERS,
        continuation='H2', representation='SINGLE', p_four=.1, max_steps=MAX_STEPS,
        version_base=BASE, new_training_updates=0, full_policy_games=0,
        root_selection='all retained TRAIN action disagreements; same actions retained as exact zeros',
        budget='32 independent fresh suffixes per disagreement; four fixed blocks of eight; no early stopping',
        primary='equal history means over all 16 roots per origin/query/history; disagreement-only secondary',
        cutoff_rule='retain all branches and costs; any cutoff blocks complete-cohort scientific claims',
        diagnostic_policy='fixed models and predictions before acquisition; no refit, model selection or gate change')


def extract_source(capsule, run, analysis):
    if not (run['status'] == 'complete' and analysis['complete'] and analysis['primary_complete']):
        raise ValueError('V147 must be complete before independent label measurement')
    source = deepcopy(capsule)
    source['schema'] = 'acfqp.independent_labels.v148.source'
    source['source_run_ref'] = str(SOURCE/'run.json')
    trained = {row['life']: row for row in run['lifecycles']}
    for snapshot in source['snapshots']:
        snapshot['advantage_models'] = {q: {m: str((SOURCE/trained[snapshot['life']]['queries'][q]['models'][m]['model_ref']).resolve())
            for m in METHODS} for q in QUERIES}
    source['cohort_refs'] = dict(OLD=str(OLD_COHORT), NEW=str(NEW_COHORT))
    source['cost_refs'].append(dict(path=str(SOURCE/'analysis.json'), fields=['costs']))
    return source


def build_cohort(source):
    roots, same, work = [], [], []
    examples = {origin: read(source[key])['examples'] for origin, key in
                [('OLD', 'old_examples_ref'), ('NEW', 'new_examples_ref')]}
    cohorts = {origin: {r['root_id']: r for r in read(path)['roots']} for origin, path in source['cohort_refs'].items()}
    for snapshot in source['snapshots']:
        for query in QUERIES:
            models = {}
            for method, path in snapshot['advantage_models'][query].items():
                cls = PairedAdvantage if method == 'UPDATED' else SharedLocalAdvantage
                model = cls.from_payload(read(path))
                if not model.frozen: raise ValueError('retained advantage model is not frozen')
                models[method] = model
            before = {m: model.state() for m, model in models.items()}
            for origin in ('OLD', 'NEW'):
                for example in examples[origin]:
                    if (example['life'], example['query'], example['split']) != (snapshot['life'], query, 'TRAIN'): continue
                    root = deepcopy(cohorts[origin][example['root_id']])
                    actions = sorted({example['candidate_action'], example['baseline_action']})
                    root.update(origin=origin, example=deepcopy(example), actions=actions,
                        predictions={m: previous.prediction(model, example) for m, model in models.items()},
                        original_suffix_seeds=root['suffix_seeds'],
                        suffix_seeds=[suffix_seed(snapshot['life'], query, origin, example['replica'], example['slot'], s)
                                      for s in range(SUFFIXES)] if len(actions) == 2 else [])
                    (roots if len(actions) == 2 else same).append(root)
            for method, model in models.items():
                if model.state() != before[method]: raise ValueError('prediction modified frozen model')
                work.append(dict(life=snapshot['life'], query=query, method=method,
                    model_ref=snapshot['advantage_models'][query][method], setup_counts=dict(model.setup_counts),
                    counts=dict(model.counts), state_unchanged=True))
    key = lambda r: (r['life'], list(QUERIES).index(r['query']), ('OLD', 'NEW').index(r['origin']), r['replica'], r['slot'])
    roots.sort(key=key); same.sort(key=key)
    if (len(roots), len(same)) != (173, 83): raise ValueError('retained TRAIN roster differs')
    seeds = [seed for r in roots for seed in r['suffix_seeds']]
    old_seeds = {seed for c in cohorts.values() for r in c.values() for seed in r['suffix_seeds']}
    if len(set(seeds)) != len(seeds) or set(seeds) & old_seeds: raise ValueError('suffix seeds overlap')
    return dict(schema='acfqp.independent_labels.v148.cohort', roots=roots, same_action_roots=same,
        excluded_same_action_roots=[r['root_id'] for r in same], prediction_work=work)


def acquire_lifecycle(source, roots, directory):
    started = perf_counter(); life = source['life']; folder = directory/f'acquire_{life}'; folder.mkdir()
    trace = str((folder/'paired_consequences.jsonl.gz').relative_to(directory))
    data = dict(life=life, consequences_trace=trace, queries={})
    with gzip.open(directory/trace, 'wt') as output:
        for query in QUERIES:
            qfolder = folder/query; qfolder.mkdir()
            parent, leaf, teacher, loads = load_teacher(source, 'SINGLE', query, qfolder)
            qroots = [r for r in roots if r['query'] == query]
            qdata = dict(loads=loads, parent_before=leaf_state(parent, True), leaf_before=leaf_state(leaf),
                spawn_probabilities=list(teacher.spawn_probabilities), roots=len(qroots))
            data['queries'][query] = qdata; work, statuses = Counter(), Counter(); branches = 0
            for index, root in enumerate(qroots):
                for suffix, seed in enumerate(root['suffix_seeds']):
                    outcomes = {}
                    for action in root['actions']:
                        branch = run_branch(root['board'], action, teacher, QUERIES[query], seed, MAX_STEPS, .1)
                        outcomes[action] = branch; branches += 1
                        work.update(branch['result']['environment_counts']); statuses[branch['result']['status']] += 1
                    append(output, dict(root_id=root['root_id'], suffix=suffix, seed=seed, continuation='H2', branches=outcomes))
                if (index+1) % 4 == 0:
                    output.flush(); print(json.dumps(dict(event='remeasured_roots', life=life, query=query, roots=index+1, branches=branches)), flush=True)
            qdata.update(physical_branches=branches, paired_records=len(qroots)*SUFFIXES, statuses=dict(statuses),
                environment_counts=dict(work), policy_counts=dict(teacher.counts),
                parent_after=leaf_state(parent, True), leaf_after=leaf_state(leaf))
    data['seconds'] = perf_counter()-started; save(folder/'lifecycle.json', data); return data


def snapshot_code(directory):
    importlib.import_module('scripts.analyze_controlled_predictive_independent_labels_v148')
    files = {Path(__file__).resolve(), ROOT/'specs/INDEPENDENT_LABELS_V148.md'}
    for module in list(sys.modules.values()):
        filename = getattr(module, '__file__', None)
        if filename:
            p = Path(filename).resolve()
            if p.is_relative_to(ROOT/'src') or p.is_relative_to(ROOT/'scripts'): files.add(p)
    for name in ('ntuple_kernel_v120', 'contextual_ntuple_v134', 'frozen_leaf_planning_v135'):
        files.add(ROOT/f'src/acfqp/science/controlled_predictive_{name}.cpp')
    files.update((ROOT/'tests').glob('*independent_labels_v148.py'))
    for p in files:
        target = directory/'source'/p.relative_to(ROOT); target.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(p, target)


def run(directory):
    started = perf_counter(); directory = directory.resolve(); directory.mkdir(parents=True, exist_ok=False)
    source = extract_source(read(SOURCE/'source_capsule.json'), read(SOURCE/'run.json'), read(SOURCE/'analysis.json'))
    cohort = build_cohort(source)
    save(directory/'source_capsule.json', source); save(directory/'cohort.json', cohort); snapshot_code(directory)
    data = dict(schema='acfqp.independent_labels.v148.run', status='frozen', settings=settings(),
        inherited_cost_refs=source['cost_refs'], lifecycles=[])
    save(directory/'frozen_inputs.json', deepcopy(data)); save(directory/'run.json', data)
    with ProcessPoolExecutor(max_workers=WORKERS) as pool:
        data['status'] = 'acquisition'; save(directory/'run.json', data)
        tasks = [pool.submit(acquire_lifecycle, s, [r for r in cohort['roots'] if r['life'] == s['life']], directory)
                 for s in source['snapshots']]
        for future in as_completed(tasks):
            data['lifecycles'].append(future.result()); data['lifecycles'].sort(key=lambda r: r['life']); save(directory/'run.json', data)
    data.update(status='complete', seconds=perf_counter()-started); save(directory/'run.json', data)
    print(json.dumps(dict(status='complete', seconds=data['seconds'])), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'reports/controlled_predictive_independent_labels_v148')
    run(parser.parse_args().output)
