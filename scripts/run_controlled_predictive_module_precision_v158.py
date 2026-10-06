"""Test fixed label budgets on fresh training and common evaluation suffixes."""
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
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / 'src'))
from scripts import run_controlled_predictive_module_diagnosis_v153 as prior
from acfqp.science.controlled_predictive_module_precision_v158 import (
    build_pairs, freeze_selectors, evaluate)

SOURCE = ROOT / 'reports/controlled_predictive_module_split_half_v157'
BRANCH_SOURCE = ROOT / 'reports/controlled_predictive_module_diagnosis_v153'
LIVES, QUERIES = prior.LIVES, prior.QUERIES
SOURCES, MODES, SPLITS = ('H2', 'LEARN8'), ('H_GATE', 'M_GATE'), ('TRAIN', 'EVAL')
BASE, SUFFIXES, MAX_STEPS, WORKERS = 158 * 100000000, 32, 2000, 4
BUDGETS = (8, 16, 32)
read, save, append = prior.read, prior.save, prior.append
load_teacher, leaf_state, RootConsequences = prior.load_teacher, prior.leaf_state, prior.RootConsequences
run_branch = prior.run_branch


def branch_seed(root, split, suffix):
    return (BASE + 20000000 + SPLITS.index(split) * 10000000 + root['life'] * 1000000
        + list(QUERIES).index(root['query']) * 100000 + SOURCES.index(root['source_method']) * 10000
        + root['slot'] * 100 + suffix)


def branch_roster(roots):
    return [dict(branch_id=f'{r["root_id"]}:{split}:{suffix}:{mode}', root_id=r['root_id'],
        split=split, suffix=suffix, mode=mode, seed=branch_seed(r, split, suffix))
        for split in SPLITS for r in roots for suffix in range(SUFFIXES) for mode in MODES]


def settings():
    return dict(lifecycles=list(LIVES), queries=QUERIES, source_methods=list(SOURCES), roots=64,
        modes=list(MODES), splits=list(SPLITS), suffixes_per_split=SUFFIXES,
        budgets=list(BUDGETS), primary_budget=32, primary_precision_contrast='32-8',
        physical_branches=8192, max_steps=MAX_STEPS, maximum_environment_transitions=16384000,
        p_four=.1, workers=WORKERS, version_base=BASE,
        seeds='BASE+20000000+split_index*10000000+life*1000000+query_index*100000+source_index*10000+slot*100+suffix; modes paired',
        roots_source='all64 unchanged audited V157/V153 roots and frozen OLD cp4 LEARN8',
        intervention='unchanged V153 H_GATE own1 then OLD gate; M_GATE other8 then OLD gate',
        selection='strict positive mean M_GATE-H_GATE utility over TRAIN suffixes 0..n-1; zero rejects',
        freeze='all TRAIN sampling complete and selectors written before any EVAL sampling',
        evaluation='all budgets and OLD/reject/accept use common EVAL suffixes 0..31; no train/eval swap',
        weighting='equal roots within each history then equal four histories; unchanged roots retained',
        primary='n32 GATE utility gain versus OLD/reject/accept; paired n32-minus-n8 precision gain',
        secondary='n8/n16 curve, source and history strata, training diagnostics; no best-budget selection',
        intervals='pointwise normal 95% conditional suffix intervals from per-root paired EVAL32 variances; fixed training decisions, roots and histories',
        incomplete='retain all cutoffs and costs; affected means and intervals incomplete; no replacements',
        acquisition='all32 TRAIN plus all32 EVAL per root; nested views do not multiply physical acquisition',
        new_training_updates=0, stopping='fixed8192 branches; no evaluation-driven extra samples, refit or threshold changes')


def extract_source(directory):
    latest = read(SOURCE / 'source_capsule.json')
    for origin in (SOURCE, BRANCH_SOURCE):
        run, analysis = read(origin / 'run.json'), read(origin / 'analysis.json')
        if not (run['status'] == 'complete' and analysis['complete'] and analysis['primary_complete']):
            raise ValueError('audited V153 and V157 completion required')
    original = read(BRANCH_SOURCE / 'source_capsule.json')
    roots = read(BRANCH_SOURCE / 'frozen_inputs.json')['roots']
    expected = {f'{life}:{query}:{method}:{slot}' for life in LIVES for query in QUERIES
                for method in SOURCES for slot in range(4)}
    if roots != latest['roots'] or len(roots) != 64 or {r['root_id'] for r in roots} != expected:
        raise ValueError('retained root roster differs')
    models = []
    for entry in original['models']:
        path = BRANCH_SOURCE / entry['model_ref']; payload = read(path)
        if not payload['frozen'] or prior.prior.model_state(payload) != entry['frozen_state']:
            raise ValueError('OLD source model differs from frozen checkpoint')
        target = directory / entry['model_ref']; target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        models.append(dict(**{k: deepcopy(entry[k]) for k in ('life','query','checkpoint','duration','model_ref','frozen_state')},
            source_model_ref=str(path), model_bytes=target.stat().st_size))
    if len(models) != 8 or {(m['life'],m['query']) for m in models} != {(l,q) for l in LIVES for q in QUERIES}:
        raise ValueError('eight frozen OLD models required')
    return dict(schema='acfqp.module_precision.v158.source',
        source_run_ref=str(SOURCE / 'run.json'), source_analysis_ref=str(SOURCE / 'analysis.json'),
        source_capsule_ref=str(SOURCE / 'source_capsule.json'),
        branch_source_run_ref=str(BRANCH_SOURCE / 'run.json'),
        branch_source_capsule_ref=str(BRANCH_SOURCE / 'source_capsule.json'),
        branch_frozen_ref=str(BRANCH_SOURCE / 'frozen_inputs.json'),
        roots=deepcopy(roots), snapshots=deepcopy(original['snapshots']), models=models,
        retained_training_cost=deepcopy(latest['retained_training_cost']),
        cost_refs=deepcopy(latest['cost_refs']) + [dict(path=str(SOURCE / 'analysis.json'),fields=['costs'])] +
            [dict(path=str(ROOT / f'reports/v157_runtime_tmp/{name}_checks.json'),fields=['attempts'])
             for name in ('core','runner','analyzer')])


def lifecycle(source, models, roots, split, directory):
    started = perf_counter(); life = source['life']
    folder = directory / split.lower() / f'life_{life}'; folder.mkdir(parents=True)
    bank, parents, leaves, learners = {}, {}, {}, {}
    data = dict(life=life, split=split, teacher_bank={}, models=[])
    for query in QUERIES:
        qfolder = folder / query; qfolder.mkdir()
        parent, leaf, teacher, loads = load_teacher(source, 'SINGLE', query, qfolder)
        bank[query], parents[query], leaves[query] = teacher, parent, leaf
        data['teacher_bank'][query] = dict(loads=loads, parent_before=leaf_state(parent, True), leaf_before=leaf_state(leaf))
        entry = next(m for m in models if (m['life'],m['query']) == (life,query))
        model = RootConsequences.from_payload(read(directory / entry['model_ref'])); learners[query] = model
        data['models'].append(dict(query=query, model_ref=entry['model_ref'], before=model.state(),
            setup_counts=dict(model.setup_counts), setup_seconds=model.setup_seconds))
    trace = folder / 'branches.jsonl.gz'; compact = []
    environment, policy, statuses = Counter(), Counter(), Counter()
    with gzip.open(trace, 'wt') as output:
        for root in roots:
            if root['life'] != life: continue
            for suffix in range(SUFFIXES):
                seed = branch_seed(root, split, suffix)
                for mode in MODES:
                    row = run_branch(root['board'], bank, root['query'], mode, learners[root['query']], seed, MAX_STEPS, .1)
                    row.update(branch_id=f'{root["root_id"]}:{split}:{suffix}:{mode}', root_id=root['root_id'],
                        life=life, source_method=root['source_method'], slot=root['slot'], split=split, suffix=suffix)
                    append(output, row); result = row['result']
                    environment.update(result['environment_counts']); policy.update(result['policy_counts']); statuses[result['status']] += 1
                    compact.append(dict(**{k: row[k] for k in ('branch_id','root_id','life','query','source_method','slot','split','suffix','mode','seed')},
                        **{k: result[k] for k in ('score','steps','status','components')}))
            print(json.dumps(dict(event='root_completed', split=split, life=life, root_id=root['root_id'], branches=64)), flush=True)
    for query in QUERIES:
        data['teacher_bank'][query].update(parent_after=leaf_state(parents[query], True),leaf_after=leaf_state(leaves[query]),total_counts=dict(bank[query].counts))
    for record in data['models']:
        model = learners[record['query']]; record.update(after=model.state(), counts=dict(model.counts))
    save(folder / 'outcomes.json', compact)
    data.update(branch_trace=str(trace.relative_to(directory)),outcomes_ref=str((folder/'outcomes.json').relative_to(directory)),
        physical_branches=len(compact),environment_counts=dict(environment),policy_counts=dict(policy),statuses=dict(statuses),seconds=perf_counter()-started)
    save(folder / 'lifecycle.json', data)
    return data


def sample_phase(split, capsule, directory):
    started = perf_counter(); lifecycles = []
    with ProcessPoolExecutor(max_workers=WORKERS) as pool:
        tasks = [pool.submit(lifecycle, source, capsule['models'], capsule['roots'], split, directory) for source in capsule['snapshots']]
        for task in as_completed(tasks):
            lifecycles.append(task.result()); lifecycles.sort(key=lambda x:x['life'])
            save(directory / f'{split.lower()}_progress.json', dict(split=split,lifecycles=lifecycles))
    return dict(split=split,lifecycles=lifecycles,seconds=perf_counter()-started)


def collect_outcomes(phase, directory):
    return [row for life in phase['lifecycles'] for row in read(directory / life['outcomes_ref'])]


def snapshot_code(directory):
    importlib.import_module('scripts.analyze_controlled_predictive_module_precision_v158')
    files = {Path(__file__).resolve(), ROOT/'specs/MODULE_PRECISION_V158.md', ROOT/'reports/v158_runtime_tmp/run_stage.py'}
    for module in list(sys.modules.values()):
        filename = getattr(module, '__file__', None)
        if filename:
            path = Path(filename).resolve()
            if path.is_relative_to(ROOT/'src') or path.is_relative_to(ROOT/'scripts'): files.add(path)
    for name in ('ntuple_kernel_v120','contextual_ntuple_v134','frozen_leaf_planning_v135'):
        files.add(ROOT/f'src/acfqp/science/controlled_predictive_{name}.cpp')
    files.update((ROOT/'tests').glob('*module_precision*v158.py'))
    for path in files:
        target = directory/'source'/path.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,target)


def run(directory):
    started = perf_counter(); directory = directory.resolve(); directory.mkdir(parents=True, exist_ok=False)
    capsule = extract_source(directory); save(directory/'source_capsule.json',capsule); snapshot_code(directory)
    data = dict(schema='acfqp.module_precision.v158.run',status='frozen',settings=settings(),
        inherited_cost_refs=capsule['cost_refs'],phases={})
    save(directory/'frozen_inputs.json',dict(**deepcopy(data),roots=capsule['roots'],branch_roster=branch_roster(capsule['roots'])))
    save(directory/'run.json',data)
    data['status']='training'; save(directory/'run.json',data)
    data['phases']['TRAIN']=sample_phase('TRAIN',capsule,directory)
    train_pairs=build_pairs(capsule['roots'],collect_outcomes(data['phases']['TRAIN'],directory),'TRAIN')
    save(directory/'train_pairs.json',train_pairs)
    selectors=freeze_selectors(capsule['roots'],train_pairs); save(directory/'frozen_selectors.json',selectors)
    data.update(status='selectors_frozen',selectors_ref='frozen_selectors.json',selectors=len(selectors)); save(directory/'run.json',data)
    data['phases']['EVAL']=sample_phase('EVAL',capsule,directory)
    eval_pairs=build_pairs(capsule['roots'],collect_outcomes(data['phases']['EVAL'],directory),'EVAL')
    save(directory/'eval_pairs.json',eval_pairs)
    rows, summary, comparisons=evaluate(selectors,eval_pairs)
    for name,payload in (('evaluation_rows',rows),('summary',summary),('comparisons',comparisons)): save(directory/f'{name}.json',payload)
    data.update(status='complete',seconds=perf_counter()-started); save(directory/'run.json',data)
    print(json.dumps(dict(status='complete',seconds=data['seconds'])),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'reports/controlled_predictive_module_precision_v158')
    run(parser.parse_args().output)
